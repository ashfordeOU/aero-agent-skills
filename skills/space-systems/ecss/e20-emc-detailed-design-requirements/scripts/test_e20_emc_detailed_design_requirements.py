#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.9 detailed
electromagnetic compatibility design requirements.

Exercises scripts/e20_emc_detailed_design_requirements_logic.py (stdlib
unittest, offline). Contract: a requirement kind maps to exactly one
electromagnetic family and an unrecognized kind raises; a limit line is
interpolated in decibels against the base-ten logarithm of frequency,
returns the break-point level at a break point, refuses a frequency
outside the covered range and refuses a malformed line; an emission
level exactly on the interpolated limit is compliant; uncorrelated unit
emissions add as power, so two equal contributors cost about three
decibels and a set of individually compliant units can still put the
shared bus over its limit; the safety margin is the susceptibility
threshold less the environment level, held against the margin the
criticality demands, and a margin landing exactly on that value through
floating-point subtraction is still compliant; an emission family
refuses a safety-margin query and a susceptibility family refuses a
limit-line query; the shielding effectiveness owed is floored at zero;
and the aggregated review is compatible only when every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_emc_detailed_design_requirements_logic as emc  # noqa: E402


CE_LIMIT_LINE = [(1.0e4, 100.0), (1.0e6, 60.0), (1.0e8, 60.0)]


def _clean_design():
    """A detailed design that satisfies every clause 6.3.9 check."""
    return {
        "requirement_kinds": [
            "conducted_emission_power_leads",
            "radiated_susceptibility_electric_field",
            "electrostatic_discharge_immunity",
        ],
        "emissions": [
            {
                "requirement_id": "CE-01",
                "requirement_kind": "conducted_emission_power_leads",
                "frequency_hz": 1.0e5,
                "measured_dbuv": 70.0,
                "limit_points": CE_LIMIT_LINE,
            }
        ],
        "buses": [
            {
                "bus_id": "BUS-A",
                "unit_levels_dbuv": [60.0, 60.0, 54.0],
                "bus_limit_dbuv": 70.0,
            }
        ],
        "susceptibilities": [
            {
                "requirement_id": "RS-01",
                "requirement_kind": "radiated_susceptibility_electric_field",
                "threshold_dbuv": 100.0,
                "environment_dbuv": 80.0,
                "criticality": "mission_critical",
            }
        ],
        "enclosures": [
            {
                "enclosure_id": "ENC-01",
                "external_field_dbuvm": 120.0,
                "internal_allowable_dbuvm": 80.0,
                "achieved_effectiveness_db": 45.0,
            }
        ],
    }


class CategorizeRequirementTest(unittest.TestCase):
    def test_power_lead_emission_is_conducted_emission(self):
        self.assertEqual(
            emc.categorize_emc_requirement("conducted_emission_power_leads"),
            "conducted_emission",
        )

    def test_bus_ripple_is_conducted_susceptibility(self):
        self.assertEqual(
            emc.categorize_emc_requirement(
                "conducted_susceptibility_bus_ripple"
            ),
            "conducted_susceptibility",
        )

    def test_electric_field_emission_is_radiated_emission(self):
        self.assertEqual(
            emc.categorize_emc_requirement("radiated_emission_electric_field"),
            "radiated_emission",
        )

    def test_magnetic_field_susceptibility_is_radiated_susceptibility(self):
        self.assertEqual(
            emc.categorize_emc_requirement(
                "radiated_susceptibility_magnetic_field"
            ),
            "radiated_susceptibility",
        )

    def test_discharge_immunity_is_its_own_family(self):
        self.assertEqual(
            emc.categorize_emc_requirement("electrostatic_discharge_immunity"),
            "esd_immunity",
        )

    def test_every_requirement_kind_lands_in_a_known_family(self):
        for kind in emc.FAMILY_BY_REQUIREMENT_KIND:
            family = emc.categorize_emc_requirement(kind)
            self.assertIsInstance(emc.is_susceptibility_family(family), bool)

    def test_uncategorized_requirement_kind_raises(self):
        with self.assertRaises(ValueError):
            emc.categorize_emc_requirement("thermal_vacuum_soak")

    def test_none_requirement_kind_raises(self):
        with self.assertRaises(ValueError):
            emc.categorize_emc_requirement(None)

    def test_emission_family_is_not_a_susceptibility_family(self):
        self.assertFalse(emc.is_susceptibility_family("conducted_emission"))

    def test_unrecognized_family_raises(self):
        with self.assertRaises(ValueError):
            emc.is_susceptibility_family("acoustic_emission")


class SafetyMarginLookupTest(unittest.TestCase):
    def test_standard_criticality_takes_the_ordinary_margin(self):
        self.assertAlmostEqual(
            emc.required_safety_margin_db(
                "conducted_susceptibility", "standard"
            ),
            6.0,
            places=9,
        )

    def test_safety_critical_takes_the_large_margin(self):
        self.assertAlmostEqual(
            emc.required_safety_margin_db(
                "radiated_susceptibility", "safety_critical"
            ),
            20.0,
            places=9,
        )

    def test_mission_critical_sits_between_the_two(self):
        self.assertGreater(
            emc.required_safety_margin_db("esd_immunity", "mission_critical"),
            emc.required_safety_margin_db("esd_immunity", "standard"),
        )
        self.assertLess(
            emc.required_safety_margin_db("esd_immunity", "mission_critical"),
            emc.required_safety_margin_db("esd_immunity", "safety_critical"),
        )

    def test_emission_family_has_no_safety_margin(self):
        with self.assertRaises(ValueError):
            emc.required_safety_margin_db("radiated_emission", "standard")

    def test_unrecognized_criticality_raises(self):
        with self.assertRaises(ValueError):
            emc.required_safety_margin_db("esd_immunity", "nice_to_have")


class LimitLineTest(unittest.TestCase):
    def test_break_point_returns_its_own_level(self):
        self.assertAlmostEqual(
            emc.limit_level_dbuv(CE_LIMIT_LINE, 1.0e4), 100.0, places=9
        )

    def test_far_break_point_returns_its_own_level(self):
        self.assertAlmostEqual(
            emc.limit_level_dbuv(CE_LIMIT_LINE, 1.0e8), 60.0, places=9
        )

    def test_log_midpoint_is_the_arithmetic_mean_of_the_levels(self):
        # 100 kHz sits one decade above 10 kHz and one decade below
        # 1 MHz, so the limit is exactly halfway between 100 and 60 dB.
        self.assertAlmostEqual(
            emc.limit_level_dbuv(CE_LIMIT_LINE, 1.0e5), 80.0, places=9
        )

    def test_quarter_decade_point_follows_the_logarithm_not_the_frequency(self):
        # A linear-in-frequency read at 500 kHz would give about 62 dB;
        # the logarithmic read is 100 - 40*log10(50) = 32.04 below 100.
        expected = 100.0 - 40.0 * (math.log10(5.0e5) - 4.0) / 2.0
        self.assertAlmostEqual(
            emc.limit_level_dbuv(CE_LIMIT_LINE, 5.0e5), expected, places=9
        )
        self.assertLess(emc.limit_level_dbuv(CE_LIMIT_LINE, 5.0e5), 70.0)

    def test_flat_segment_holds_its_level(self):
        self.assertAlmostEqual(
            emc.limit_level_dbuv(CE_LIMIT_LINE, 1.0e7), 60.0, places=9
        )

    def test_frequency_below_the_line_raises(self):
        with self.assertRaises(ValueError):
            emc.limit_level_dbuv(CE_LIMIT_LINE, 1.0e3)

    def test_frequency_above_the_line_raises(self):
        with self.assertRaises(ValueError):
            emc.limit_level_dbuv(CE_LIMIT_LINE, 1.0e9)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            emc.limit_level_dbuv(CE_LIMIT_LINE, 0.0)

    def test_single_point_line_raises(self):
        with self.assertRaises(ValueError):
            emc.validate_limit_line([(1.0e4, 100.0)])

    def test_non_increasing_frequencies_raise(self):
        with self.assertRaises(ValueError):
            emc.validate_limit_line([(1.0e6, 60.0), (1.0e4, 100.0)])

    def test_repeated_frequency_raises(self):
        with self.assertRaises(ValueError):
            emc.validate_limit_line([(1.0e4, 100.0), (1.0e4, 60.0)])

    def test_non_positive_frequency_in_line_raises(self):
        with self.assertRaises(ValueError):
            emc.validate_limit_line([(0.0, 100.0), (1.0e6, 60.0)])

    def test_valid_line_is_returned_unchanged(self):
        self.assertEqual(
            emc.validate_limit_line(CE_LIMIT_LINE), list(CE_LIMIT_LINE)
        )


class EmissionFindingsTest(unittest.TestCase):
    def _emission(self, **overrides):
        item = {
            "requirement_id": "CE-01",
            "requirement_kind": "conducted_emission_power_leads",
            "frequency_hz": 1.0e5,
            "measured_dbuv": 70.0,
            "limit_points": CE_LIMIT_LINE,
        }
        item.update(overrides)
        return item

    def test_compliant_emission_has_no_finding(self):
        self.assertEqual(emc.emission_findings(self._emission()), [])

    def test_emission_above_the_line_is_reported(self):
        findings = emc.emission_findings(self._emission(measured_dbuv=95.0))
        self.assertEqual(
            findings[0]["issue"], "emission_level_above_limit_line"
        )
        self.assertAlmostEqual(findings[0]["limit_dbuv"], 80.0, places=9)

    def test_emission_exactly_on_the_line_is_compliant(self):
        self.assertEqual(
            emc.emission_findings(self._emission(measured_dbuv=80.0)), []
        )

    def test_same_level_passes_low_and_fails_high(self):
        self.assertEqual(
            emc.emission_findings(
                self._emission(frequency_hz=1.0e4, measured_dbuv=95.0)
            ),
            [],
        )
        self.assertEqual(
            len(
                emc.emission_findings(
                    self._emission(frequency_hz=1.0e7, measured_dbuv=95.0)
                )
            ),
            1,
        )

    def test_susceptibility_kind_in_emission_check_raises(self):
        with self.assertRaises(ValueError):
            emc.emission_findings(
                self._emission(
                    requirement_kind="radiated_susceptibility_electric_field"
                )
            )

    def test_out_of_range_frequency_raises(self):
        with self.assertRaises(ValueError):
            emc.emission_findings(self._emission(frequency_hz=1.0))


class PowerSumTest(unittest.TestCase):
    def test_single_level_sums_to_itself(self):
        self.assertAlmostEqual(emc.power_sum_dbuv([60.0]), 60.0, places=9)

    def test_two_equal_contributors_cost_about_three_decibels(self):
        self.assertAlmostEqual(
            emc.power_sum_dbuv([60.0, 60.0]), 63.0103, places=4
        )

    def test_four_equal_contributors_cost_about_six_decibels(self):
        self.assertAlmostEqual(
            emc.power_sum_dbuv([60.0] * 4), 66.0206, places=4
        )

    def test_power_sum_is_not_a_decibel_addition(self):
        self.assertLess(emc.power_sum_dbuv([60.0, 60.0]), 120.0)

    def test_power_sum_exceeds_the_worst_contributor(self):
        self.assertGreater(emc.power_sum_dbuv([60.0, 54.0]), 60.0)

    def test_a_much_smaller_contributor_barely_moves_the_sum(self):
        self.assertAlmostEqual(
            emc.power_sum_dbuv([60.0, 20.0]), 60.0, places=3
        )

    def test_power_sum_is_order_independent(self):
        self.assertAlmostEqual(
            emc.power_sum_dbuv([40.0, 55.0, 60.0]),
            emc.power_sum_dbuv([60.0, 40.0, 55.0]),
            places=9,
        )

    def test_empty_level_list_raises(self):
        with self.assertRaises(ValueError):
            emc.power_sum_dbuv([])

    def test_bus_inside_limit_has_no_finding(self):
        self.assertEqual(
            emc.bus_emission_findings("BUS-A", [60.0, 60.0], 70.0), []
        )

    def test_individually_compliant_units_can_break_the_bus(self):
        units = [65.0] * 4
        for level in units:
            self.assertLess(level, 68.0)
        findings = emc.bus_emission_findings("BUS-B", units, 68.0)
        self.assertEqual(
            findings[0]["issue"], "aggregated_bus_emission_above_limit"
        )
        self.assertEqual(findings[0]["unit_count"], 4)

    def test_bus_aggregate_exactly_on_limit_is_compliant(self):
        aggregate = emc.power_sum_dbuv([60.0, 60.0])
        self.assertEqual(
            emc.bus_emission_findings("BUS-C", [60.0, 60.0], aggregate), []
        )

    def test_empty_bus_raises(self):
        with self.assertRaises(ValueError):
            emc.bus_emission_findings("BUS-D", [], 70.0)


class SafetyMarginTest(unittest.TestCase):
    def test_margin_is_threshold_less_environment(self):
        self.assertAlmostEqual(
            emc.emc_safety_margin_db(100.0, 80.0), 20.0, places=9
        )

    def test_margin_is_negative_when_environment_exceeds_threshold(self):
        self.assertAlmostEqual(
            emc.emc_safety_margin_db(70.0, 80.0), -10.0, places=9
        )

    def test_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            emc.emc_safety_margin_db("100", 80.0)

    def test_infinite_environment_raises(self):
        with self.assertRaises(ValueError):
            emc.emc_safety_margin_db(100.0, float("inf"))

    def test_nan_threshold_raises(self):
        with self.assertRaises(ValueError):
            emc.emc_safety_margin_db(float("nan"), 80.0)

    def _requirement(self, **overrides):
        item = {
            "requirement_id": "CS-01",
            "requirement_kind": "conducted_susceptibility_bus_ripple",
            "threshold_dbuv": 100.0,
            "environment_dbuv": 80.0,
            "criticality": "standard",
        }
        item.update(overrides)
        return item

    def test_comfortable_margin_has_no_finding(self):
        self.assertEqual(
            emc.susceptibility_findings(self._requirement()), []
        )

    def test_short_margin_is_reported(self):
        findings = emc.susceptibility_findings(
            self._requirement(threshold_dbuv=82.0)
        )
        self.assertEqual(
            findings[0]["issue"], "emc_safety_margin_below_demanded"
        )
        self.assertAlmostEqual(findings[0]["demanded_db"], 6.0, places=9)

    def test_margin_exactly_on_demand_passes_despite_rounding(self):
        # 64.1 dB threshold over a 58.1 dB environment is exactly the
        # 6 dB standard demand, but the subtraction lands a few ULPs low.
        self.assertLess(64.1 - 58.1, 6.0)
        self.assertEqual(
            emc.susceptibility_findings(
                self._requirement(
                    threshold_dbuv=64.1, environment_dbuv=58.1
                )
            ),
            [],
        )

    def test_same_margin_passes_standard_and_fails_safety_critical(self):
        self.assertEqual(
            emc.susceptibility_findings(
                self._requirement(threshold_dbuv=90.0)
            ),
            [],
        )
        self.assertEqual(
            len(
                emc.susceptibility_findings(
                    self._requirement(
                        threshold_dbuv=90.0, criticality="safety_critical"
                    )
                )
            ),
            1,
        )

    def test_emission_kind_in_susceptibility_check_raises(self):
        with self.assertRaises(ValueError):
            emc.susceptibility_findings(
                self._requirement(
                    requirement_kind="conducted_emission_power_leads"
                )
            )

    def test_unrecognized_criticality_in_requirement_raises(self):
        with self.assertRaises(ValueError):
            emc.susceptibility_findings(
                self._requirement(criticality="best_effort")
            )


class ShieldingTest(unittest.TestCase):
    def test_required_effectiveness_is_the_difference(self):
        self.assertAlmostEqual(
            emc.required_shielding_effectiveness_db(120.0, 80.0),
            40.0,
            places=9,
        )

    def test_nothing_is_owed_below_the_allowable(self):
        self.assertAlmostEqual(
            emc.required_shielding_effectiveness_db(60.0, 80.0),
            0.0,
            places=9,
        )

    def test_equal_levels_owe_nothing(self):
        self.assertAlmostEqual(
            emc.required_shielding_effectiveness_db(80.0, 80.0),
            0.0,
            places=9,
        )

    def test_non_finite_external_field_raises(self):
        with self.assertRaises(ValueError):
            emc.required_shielding_effectiveness_db(float("inf"), 80.0)

    def test_boolean_allowable_raises(self):
        with self.assertRaises(ValueError):
            emc.required_shielding_effectiveness_db(120.0, True)

    def test_sufficient_enclosure_has_no_finding(self):
        enclosure = {
            "enclosure_id": "ENC-01",
            "external_field_dbuvm": 120.0,
            "internal_allowable_dbuvm": 80.0,
            "achieved_effectiveness_db": 45.0,
        }
        self.assertEqual(emc.shielding_findings(enclosure), [])

    def test_insufficient_enclosure_is_reported(self):
        enclosure = {
            "enclosure_id": "ENC-02",
            "external_field_dbuvm": 120.0,
            "internal_allowable_dbuvm": 80.0,
            "achieved_effectiveness_db": 20.0,
        }
        findings = emc.shielding_findings(enclosure)
        self.assertEqual(
            findings[0]["issue"], "shielding_effectiveness_below_required"
        )
        self.assertAlmostEqual(findings[0]["required_db"], 40.0, places=9)

    def test_effectiveness_exactly_on_requirement_is_compliant(self):
        enclosure = {
            "enclosure_id": "ENC-03",
            "external_field_dbuvm": 120.0,
            "internal_allowable_dbuvm": 80.0,
            "achieved_effectiveness_db": 40.0,
        }
        self.assertEqual(emc.shielding_findings(enclosure), [])

    def test_zero_effectiveness_passes_when_nothing_is_owed(self):
        enclosure = {
            "enclosure_id": "ENC-04",
            "external_field_dbuvm": 60.0,
            "internal_allowable_dbuvm": 80.0,
            "achieved_effectiveness_db": 0.0,
        }
        self.assertEqual(emc.shielding_findings(enclosure), [])

    def test_negative_achieved_effectiveness_raises(self):
        enclosure = {
            "enclosure_id": "ENC-05",
            "external_field_dbuvm": 120.0,
            "internal_allowable_dbuvm": 80.0,
            "achieved_effectiveness_db": -5.0,
        }
        with self.assertRaises(ValueError):
            emc.shielding_findings(enclosure)


class DesignReviewTest(unittest.TestCase):
    def test_clean_design_is_compatible(self):
        review = emc.emc_design_review(_clean_design())
        self.assertTrue(emc.is_emc_design_compliant(review))
        for key in (
            "family",
            "emission",
            "bus",
            "susceptibility",
            "shielding",
        ):
            self.assertEqual(review[key], [])

    def test_unknown_requirement_kind_is_reported_not_raised(self):
        design = _clean_design()
        design["requirement_kinds"].append("vibration_sine_sweep")
        review = emc.emc_design_review(design)
        self.assertEqual(
            review["family"][0]["issue"], "requirement_kind_in_no_emc_family"
        )
        self.assertFalse(emc.is_emc_design_compliant(review))

    def test_emission_over_the_line_breaks_the_design(self):
        design = _clean_design()
        design["emissions"][0]["measured_dbuv"] = 99.0
        review = emc.emc_design_review(design)
        self.assertEqual(len(review["emission"]), 1)

    def test_bus_aggregate_breaks_the_design(self):
        design = _clean_design()
        design["buses"][0]["bus_limit_dbuv"] = 60.0
        review = emc.emc_design_review(design)
        self.assertEqual(review["bus"][0]["bus"], "BUS-A")

    def test_short_susceptibility_margin_breaks_the_design(self):
        design = _clean_design()
        design["susceptibilities"][0]["environment_dbuv"] = 95.0
        review = emc.emc_design_review(design)
        self.assertEqual(len(review["susceptibility"]), 1)

    def test_thin_enclosure_breaks_the_design(self):
        design = _clean_design()
        design["enclosures"][0]["achieved_effectiveness_db"] = 5.0
        review = emc.emc_design_review(design)
        self.assertEqual(len(review["shielding"]), 1)

    def test_review_does_not_mutate_the_design(self):
        design = _clean_design()
        before = repr(design)
        emc.emc_design_review(design)
        self.assertEqual(repr(design), before)

    def test_review_is_deterministic(self):
        self.assertEqual(
            emc.emc_design_review(_clean_design()),
            emc.emc_design_review(_clean_design()),
        )

    def test_empty_design_is_compatible(self):
        self.assertTrue(
            emc.is_emc_design_compliant(emc.emc_design_review({}))
        )

    def test_bad_emission_input_still_raises_from_the_review(self):
        design = _clean_design()
        design["emissions"][0]["frequency_hz"] = 1.0
        with self.assertRaises(ValueError):
            emc.emc_design_review(design)

    def test_tolerance_is_a_representation_tolerance(self):
        self.assertLess(emc.LIMIT_REL_TOL, 1.0e-6)
        self.assertLess(emc.LIMIT_ABS_TOL_DB, 1.0e-6)
        self.assertTrue(
            math.isclose(
                64.1 - 58.1,
                6.0,
                rel_tol=emc.LIMIT_REL_TOL,
                abs_tol=emc.LIMIT_ABS_TOL_DB,
            )
        )


if __name__ == "__main__":
    unittest.main()

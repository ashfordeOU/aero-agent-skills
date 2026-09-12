#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.8.3 cable and shield
categories.

Exercises scripts/e20_cable_and_shield_categories_logic.py (stdlib
unittest, offline). Contract: a wire kind maps to exactly one harness
category and an unrecognized kind raises; the minimum bundle separation
follows the distance between the two ranks, not the absolute rank, and
a pair with exactly one pyrotechnic run always takes the largest gap
plus a dedicated overshield; a separation landing exactly on the
minimum through floating-point subtraction is still compliant; the
required shield termination style follows the category and the highest
frequency carried, with the threshold itself counting as high
frequency; the pigtail length and the reactance it presents are checked
only where a circumferential termination is required; braid optical
coverage carries a per-category minimum; the transfer-impedance coupled
voltage is impedance per metre times coupled length times disturbing
current against the victim's susceptibility voltage; and the aggregated
review is compliant only when every list is empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_cable_and_shield_categories_logic as cs  # noqa: E402


def _clean_harness():
    """A harness definition that satisfies every clause 6.3.8.3 check."""
    return {
        "runs": [
            {
                "run_id": "W-RF-01",
                "wire_kind": "rf_receive_coax",
                "declared_category": "category_1_very_sensitive",
                "highest_frequency_hz": 2.0e9,
                "declared_termination": cs.TERMINATION_BOTH_ENDS,
                "pigtail_length_m": 0.0,
                "optical_coverage_percent": 95.0,
            },
            {
                "run_id": "W-ANA-01",
                "wire_kind": "low_level_analogue",
                "highest_frequency_hz": 1.0e3,
                "declared_termination": cs.TERMINATION_SOURCE_END,
                "pigtail_length_m": 0.05,
                "optical_coverage_percent": 92.0,
            },
            {
                "run_id": "W-PWR-01",
                "wire_kind": "primary_power_feed",
                "highest_frequency_hz": 1.0e3,
                "declared_termination": cs.TERMINATION_HYBRID,
                "pigtail_length_m": 0.04,
                "optical_coverage_percent": 88.0,
            },
            {
                "run_id": "W-PYR-01",
                "wire_kind": "pyrotechnic_firing",
                "highest_frequency_hz": 1.0e4,
                "declared_termination": cs.TERMINATION_BOTH_ENDS,
                "pigtail_length_m": 0.01,
                "optical_coverage_percent": 97.0,
            },
        ],
        "routed_pairs": [
            {
                "pair_id": "P-ANA-PWR",
                "wire_kind_a": "low_level_analogue",
                "wire_kind_b": "primary_power_feed",
                "separation_m": 0.20,
                "has_dedicated_overshield": False,
            },
            {
                "pair_id": "P-PYR-PWR",
                "wire_kind_a": "pyrotechnic_firing",
                "wire_kind_b": "primary_power_feed",
                "separation_m": 0.35,
                "has_dedicated_overshield": True,
            },
        ],
        "couplings": [
            {
                "victim_id": "W-ANA-01",
                "transfer_impedance_ohm_per_m": 1.0e-3,
                "coupled_length_m": 2.0,
                "disturbing_current_a": 0.5,
                "susceptibility_voltage_v": 5.0e-3,
            }
        ],
    }


class CategorizeCableTest(unittest.TestCase):
    def test_receive_coax_is_very_sensitive(self):
        self.assertEqual(
            cs.categorize_cable("rf_receive_coax"), "category_1_very_sensitive"
        )

    def test_digital_bus_is_sensitive(self):
        self.assertEqual(
            cs.categorize_cable("digital_data_bus"), "category_2_sensitive"
        )

    def test_primary_power_is_noisy(self):
        self.assertEqual(
            cs.categorize_cable("primary_power_feed"), "category_3_noisy"
        )

    def test_transmit_coax_is_very_noisy(self):
        self.assertEqual(
            cs.categorize_cable("rf_transmit_coax"), "category_4_very_noisy"
        )

    def test_firing_line_is_pyrotechnic(self):
        self.assertEqual(
            cs.categorize_cable("pyrotechnic_firing"), cs.PYROTECHNIC_CATEGORY
        )

    def test_every_wire_kind_maps_to_a_ranked_category(self):
        for kind in cs.CATEGORY_BY_WIRE_KIND:
            category = cs.categorize_cable(kind)
            self.assertIn(cs.category_rank(category), (1, 2, 3, 4, 5))

    def test_uncategorized_wire_kind_raises(self):
        with self.assertRaises(ValueError):
            cs.categorize_cable("propellant_heater_tape")

    def test_none_wire_kind_raises(self):
        with self.assertRaises(ValueError):
            cs.categorize_cable(None)

    def test_unrecognized_category_rank_raises(self):
        with self.assertRaises(ValueError):
            cs.category_rank("category_6_unknown")


class SeparationTest(unittest.TestCase):
    def test_same_category_may_share_a_bundle(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                "category_2_sensitive", "category_2_sensitive"
            ),
            0.0,
            places=9,
        )

    def test_one_rank_apart_needs_the_small_gap(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                "category_1_very_sensitive", "category_2_sensitive"
            ),
            0.05,
            places=9,
        )

    def test_two_ranks_apart_needs_the_middle_gap(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                "category_1_very_sensitive", "category_3_noisy"
            ),
            0.15,
            places=9,
        )

    def test_three_ranks_apart_needs_the_largest_gap(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                "category_1_very_sensitive", "category_4_very_noisy"
            ),
            0.30,
            places=9,
        )

    def test_separation_is_symmetric(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                "category_2_sensitive", "category_4_very_noisy"
            ),
            cs.minimum_separation_m(
                "category_4_very_noisy", "category_2_sensitive"
            ),
            places=9,
        )

    def test_pyrotechnic_with_adjacent_rank_still_takes_the_largest_gap(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                cs.PYROTECHNIC_CATEGORY, "category_4_very_noisy"
            ),
            0.30,
            places=9,
        )

    def test_two_pyrotechnic_runs_may_share_a_bundle(self):
        self.assertAlmostEqual(
            cs.minimum_separation_m(
                cs.PYROTECHNIC_CATEGORY, cs.PYROTECHNIC_CATEGORY
            ),
            0.0,
            places=9,
        )

    def test_overshield_required_for_a_mixed_pyrotechnic_pair(self):
        self.assertTrue(
            cs.requires_dedicated_overshield(
                cs.PYROTECHNIC_CATEGORY, "category_2_sensitive"
            )
        )

    def test_overshield_not_required_for_two_pyrotechnic_runs(self):
        self.assertFalse(
            cs.requires_dedicated_overshield(
                cs.PYROTECHNIC_CATEGORY, cs.PYROTECHNIC_CATEGORY
            )
        )

    def test_overshield_rejects_an_unrecognized_category(self):
        with self.assertRaises(ValueError):
            cs.requires_dedicated_overshield("category_9", "category_2_sensitive")

    def test_well_separated_pair_has_no_finding(self):
        pair = {
            "pair_id": "P1",
            "wire_kind_a": "low_level_analogue",
            "wire_kind_b": "primary_power_feed",
            "separation_m": 0.25,
            "has_dedicated_overshield": False,
        }
        self.assertEqual(cs.separation_findings(pair), [])

    def test_close_routed_pair_is_reported(self):
        pair = {
            "pair_id": "P2",
            "wire_kind_a": "low_level_analogue",
            "wire_kind_b": "primary_power_feed",
            "separation_m": 0.02,
            "has_dedicated_overshield": False,
        }
        findings = cs.separation_findings(pair)
        self.assertEqual(findings[0]["issue"], "bundle_separation_below_minimum")
        self.assertAlmostEqual(findings[0]["minimum_m"], 0.15, places=9)

    def test_separation_exactly_on_minimum_passes_despite_rounding(self):
        # Bundle centres measured at 0.29 m and 0.14 m from the tray
        # datum: exactly the 0.15 m minimum, a few ULPs low as a float.
        separation = 0.29 - 0.14
        self.assertLess(separation, 0.15)
        pair = {
            "pair_id": "P3",
            "wire_kind_a": "low_level_analogue",
            "wire_kind_b": "primary_power_feed",
            "separation_m": separation,
            "has_dedicated_overshield": False,
        }
        self.assertEqual(cs.separation_findings(pair), [])

    def test_pyrotechnic_pair_without_overshield_is_reported(self):
        pair = {
            "pair_id": "P4",
            "wire_kind_a": "pyrotechnic_firing",
            "wire_kind_b": "digital_data_bus",
            "separation_m": 0.50,
            "has_dedicated_overshield": False,
        }
        findings = cs.separation_findings(pair)
        self.assertEqual(
            findings[0]["issue"],
            "pyrotechnic_pair_without_dedicated_overshield",
        )

    def test_close_pyrotechnic_pair_reports_both_issues(self):
        pair = {
            "pair_id": "P5",
            "wire_kind_a": "pyrotechnic_firing",
            "wire_kind_b": "digital_data_bus",
            "separation_m": 0.01,
            "has_dedicated_overshield": False,
        }
        self.assertEqual(len(cs.separation_findings(pair)), 2)

    def test_negative_separation_raises(self):
        pair = {
            "pair_id": "P6",
            "wire_kind_a": "digital_data_bus",
            "wire_kind_b": "digital_data_bus",
            "separation_m": -0.1,
            "has_dedicated_overshield": False,
        }
        with self.assertRaises(ValueError):
            cs.separation_findings(pair)

    def test_non_boolean_overshield_flag_raises(self):
        pair = {
            "pair_id": "P7",
            "wire_kind_a": "digital_data_bus",
            "wire_kind_b": "digital_data_bus",
            "separation_m": 0.1,
            "has_dedicated_overshield": "yes",
        }
        with self.assertRaises(ValueError):
            cs.separation_findings(pair)


class TerminationStyleTest(unittest.TestCase):
    def test_high_frequency_run_is_bonded_both_ends(self):
        self.assertEqual(
            cs.required_shield_termination_style(
                "category_2_sensitive", 1.0e7
            ),
            cs.TERMINATION_BOTH_ENDS,
        )

    def test_threshold_frequency_counts_as_high_frequency(self):
        self.assertEqual(
            cs.required_shield_termination_style(
                "category_1_very_sensitive", cs.HIGH_FREQUENCY_THRESHOLD_HZ
            ),
            cs.TERMINATION_BOTH_ENDS,
        )

    def test_low_frequency_sensitive_run_is_source_end_only(self):
        self.assertEqual(
            cs.required_shield_termination_style(
                "category_1_very_sensitive", 1.0e3
            ),
            cs.TERMINATION_SOURCE_END,
        )

    def test_low_frequency_noisy_run_is_hybrid(self):
        self.assertEqual(
            cs.required_shield_termination_style("category_3_noisy", 1.0e3),
            cs.TERMINATION_HYBRID,
        )

    def test_pyrotechnic_run_is_bonded_both_ends_at_any_frequency(self):
        self.assertEqual(
            cs.required_shield_termination_style(cs.PYROTECHNIC_CATEGORY, 1.0),
            cs.TERMINATION_BOTH_ENDS,
        )

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            cs.required_shield_termination_style("category_3_noisy", 0.0)

    def test_unrecognized_category_raises(self):
        with self.assertRaises(ValueError):
            cs.required_shield_termination_style("category_0", 1.0e6)


class PigtailTest(unittest.TestCase):
    def test_inductance_scales_with_length(self):
        self.assertAlmostEqual(
            cs.pigtail_inductance_h(0.05), 5.0e-8, places=12
        )

    def test_zero_length_has_no_inductance(self):
        self.assertAlmostEqual(cs.pigtail_inductance_h(0.0), 0.0, places=15)

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            cs.pigtail_inductance_h(-0.01)

    def test_zero_inductance_per_metre_raises(self):
        with self.assertRaises(ValueError):
            cs.pigtail_inductance_h(0.05, 0.0)

    def test_reactance_is_two_pi_f_l(self):
        expected = 2.0 * math.pi * 1.0e6 * 5.0e-8
        self.assertAlmostEqual(
            cs.pigtail_reactance_ohm(0.05, 1.0e6), expected, places=9
        )

    def test_reactance_rises_with_frequency(self):
        low = cs.pigtail_reactance_ohm(0.05, 1.0e5)
        high = cs.pigtail_reactance_ohm(0.05, 1.0e7)
        self.assertGreater(high, low)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            cs.pigtail_reactance_ohm(0.05, -1.0)


class TerminationFindingsTest(unittest.TestCase):
    def _run(self, **overrides):
        run = {
            "run_id": "W1",
            "wire_kind": "digital_data_bus",
            "highest_frequency_hz": 1.0e6,
            "declared_termination": cs.TERMINATION_BOTH_ENDS,
            "pigtail_length_m": 0.01,
        }
        run.update(overrides)
        return run

    def test_correct_termination_has_no_finding(self):
        self.assertEqual(cs.termination_findings(self._run()), [])

    def test_style_mismatch_is_reported(self):
        findings = cs.termination_findings(
            self._run(declared_termination=cs.TERMINATION_SOURCE_END)
        )
        self.assertEqual(
            findings[0]["issue"], "shield_termination_style_mismatch"
        )
        self.assertEqual(
            findings[0]["required_termination"], cs.TERMINATION_BOTH_ENDS
        )

    def test_long_pigtail_is_reported(self):
        findings = cs.termination_findings(self._run(pigtail_length_m=0.20))
        issues = [f["issue"] for f in findings]
        self.assertIn(
            "pigtail_longer_than_circumferential_allowance", issues
        )

    def test_pigtail_exactly_on_allowance_passes(self):
        self.assertEqual(
            cs.termination_findings(
                self._run(pigtail_length_m=cs.MAX_PIGTAIL_LENGTH_M)
            ),
            [],
        )

    def test_pigtail_reactance_above_allowance_is_reported(self):
        findings = cs.termination_findings(
            self._run(
                highest_frequency_hz=1.0e9,
                pigtail_length_m=0.02,
            )
        )
        issues = [f["issue"] for f in findings]
        self.assertIn("pigtail_reactance_above_allowance", issues)

    def test_low_frequency_run_skips_the_pigtail_checks(self):
        findings = cs.termination_findings(
            self._run(
                wire_kind="low_level_analogue",
                highest_frequency_hz=1.0e3,
                declared_termination=cs.TERMINATION_SOURCE_END,
                pigtail_length_m=0.50,
            )
        )
        self.assertEqual(findings, [])

    def test_unrecognized_declared_style_raises(self):
        with self.assertRaises(ValueError):
            cs.termination_findings(
                self._run(declared_termination="taped_and_left")
            )

    def test_zero_reactance_allowance_raises(self):
        with self.assertRaises(ValueError):
            cs.termination_findings(self._run(max_pigtail_reactance_ohm=0.0))


class CoverageTest(unittest.TestCase):
    def test_very_sensitive_carries_the_tight_minimum(self):
        self.assertAlmostEqual(
            cs.minimum_optical_coverage_percent("category_1_very_sensitive"),
            90.0,
            places=9,
        )

    def test_pyrotechnic_carries_the_tightest_minimum(self):
        self.assertAlmostEqual(
            cs.minimum_optical_coverage_percent(cs.PYROTECHNIC_CATEGORY),
            95.0,
            places=9,
        )

    def test_unrecognized_category_minimum_raises(self):
        with self.assertRaises(ValueError):
            cs.minimum_optical_coverage_percent("category_7")

    def test_covered_braid_has_no_finding(self):
        self.assertEqual(
            cs.coverage_findings("W1", "digital_data_bus", 90.0), []
        )

    def test_thin_braid_is_reported(self):
        findings = cs.coverage_findings("W2", "rf_receive_coax", 80.0)
        self.assertEqual(
            findings[0]["issue"], "braid_optical_coverage_below_minimum"
        )
        self.assertAlmostEqual(findings[0]["minimum_percent"], 90.0, places=9)

    def test_coverage_exactly_on_minimum_passes(self):
        self.assertEqual(
            cs.coverage_findings("W3", "rf_receive_coax", 90.0), []
        )

    def test_same_coverage_passes_one_category_and_fails_another(self):
        self.assertEqual(
            cs.coverage_findings("W4", "digital_data_bus", 87.0), []
        )
        self.assertEqual(
            len(cs.coverage_findings("W5", "rf_receive_coax", 87.0)), 1
        )

    def test_zero_coverage_raises(self):
        with self.assertRaises(ValueError):
            cs.coverage_findings("W6", "digital_data_bus", 0.0)

    def test_coverage_above_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            cs.coverage_findings("W7", "digital_data_bus", 101.0)


class TransferImpedanceTest(unittest.TestCase):
    def test_coupled_voltage_is_impedance_length_current(self):
        self.assertAlmostEqual(
            cs.shield_transfer_coupled_voltage(1.0e-3, 2.0, 3.0),
            6.0e-3,
            places=9,
        )

    def test_zero_length_couples_nothing(self):
        self.assertAlmostEqual(
            cs.shield_transfer_coupled_voltage(1.0e-3, 0.0, 3.0),
            0.0,
            places=12,
        )

    def test_negative_transfer_impedance_raises(self):
        with self.assertRaises(ValueError):
            cs.shield_transfer_coupled_voltage(-1.0e-3, 2.0, 3.0)

    def test_negative_length_raises(self):
        with self.assertRaises(ValueError):
            cs.shield_transfer_coupled_voltage(1.0e-3, -2.0, 3.0)

    def test_negative_current_raises(self):
        with self.assertRaises(ValueError):
            cs.shield_transfer_coupled_voltage(1.0e-3, 2.0, -3.0)

    def test_coupling_inside_budget_has_no_finding(self):
        coupling = {
            "victim_id": "V1",
            "transfer_impedance_ohm_per_m": 1.0e-3,
            "coupled_length_m": 2.0,
            "disturbing_current_a": 0.5,
            "susceptibility_voltage_v": 5.0e-3,
        }
        self.assertEqual(cs.coupling_findings(coupling), [])

    def test_coupling_above_budget_is_reported(self):
        coupling = {
            "victim_id": "V2",
            "transfer_impedance_ohm_per_m": 1.0e-2,
            "coupled_length_m": 3.0,
            "disturbing_current_a": 2.0,
            "susceptibility_voltage_v": 5.0e-3,
        }
        findings = cs.coupling_findings(coupling)
        self.assertEqual(
            findings[0]["issue"], "shield_coupled_voltage_above_susceptibility"
        )
        self.assertAlmostEqual(findings[0]["coupled_v"], 6.0e-2, places=9)

    def test_coupling_exactly_on_budget_passes_despite_rounding(self):
        # 7 mOhm/m over 3 m at 100 mA is exactly the 2.1 mV budget, but
        # the product lands a few ULPs above it.
        self.assertGreater(0.007 * 3.0 * 0.1, 0.0021)
        coupling = {
            "victim_id": "V3",
            "transfer_impedance_ohm_per_m": 0.007,
            "coupled_length_m": 3.0,
            "disturbing_current_a": 0.1,
            "susceptibility_voltage_v": 0.0021,
        }
        self.assertEqual(cs.coupling_findings(coupling), [])

    def test_zero_susceptibility_voltage_raises(self):
        coupling = {
            "victim_id": "V4",
            "transfer_impedance_ohm_per_m": 1.0e-3,
            "coupled_length_m": 2.0,
            "disturbing_current_a": 0.5,
            "susceptibility_voltage_v": 0.0,
        }
        with self.assertRaises(ValueError):
            cs.coupling_findings(coupling)


class HarnessReviewTest(unittest.TestCase):
    def test_clean_harness_is_compliant(self):
        review = cs.harness_review(_clean_harness())
        self.assertTrue(cs.is_harness_compliant(review))
        for key in (
            "category",
            "separation",
            "termination",
            "coverage",
            "coupling",
        ):
            self.assertEqual(review[key], [])

    def test_wrong_declared_category_is_reported(self):
        harness = _clean_harness()
        harness["runs"][0]["declared_category"] = "category_3_noisy"
        review = cs.harness_review(harness)
        self.assertEqual(
            review["category"][0]["issue"],
            "declared_category_does_not_match_wire_kind",
        )
        self.assertFalse(cs.is_harness_compliant(review))

    def test_close_routing_breaks_the_harness(self):
        harness = _clean_harness()
        harness["routed_pairs"][0]["separation_m"] = 0.01
        review = cs.harness_review(harness)
        self.assertEqual(len(review["separation"]), 1)

    def test_missing_pyrotechnic_overshield_breaks_the_harness(self):
        harness = _clean_harness()
        harness["routed_pairs"][1]["has_dedicated_overshield"] = False
        review = cs.harness_review(harness)
        self.assertEqual(
            review["separation"][0]["issue"],
            "pyrotechnic_pair_without_dedicated_overshield",
        )

    def test_wrong_termination_breaks_the_harness(self):
        harness = _clean_harness()
        harness["runs"][1]["declared_termination"] = cs.TERMINATION_BOTH_ENDS
        review = cs.harness_review(harness)
        self.assertEqual(len(review["termination"]), 1)

    def test_thin_braid_breaks_the_harness(self):
        harness = _clean_harness()
        harness["runs"][3]["optical_coverage_percent"] = 90.0
        review = cs.harness_review(harness)
        self.assertEqual(review["coverage"][0]["run"], "W-PYR-01")

    def test_coupling_over_budget_breaks_the_harness(self):
        harness = _clean_harness()
        harness["couplings"][0]["disturbing_current_a"] = 50.0
        review = cs.harness_review(harness)
        self.assertEqual(len(review["coupling"]), 1)

    def test_review_does_not_mutate_the_harness(self):
        harness = _clean_harness()
        before = repr(harness)
        cs.harness_review(harness)
        self.assertEqual(repr(harness), before)

    def test_review_is_deterministic(self):
        self.assertEqual(
            cs.harness_review(_clean_harness()),
            cs.harness_review(_clean_harness()),
        )

    def test_uncategorized_run_in_harness_raises(self):
        harness = _clean_harness()
        harness["runs"][0]["wire_kind"] = "fibre_optic_link"
        with self.assertRaises(ValueError):
            cs.harness_review(harness)

    def test_empty_harness_is_compliant(self):
        review = cs.harness_review({})
        self.assertTrue(cs.is_harness_compliant(review))

    def test_tolerance_is_a_representation_tolerance(self):
        self.assertLess(cs.LIMIT_REL_TOL, 1.0e-6)
        self.assertTrue(
            math.isclose(0.29 - 0.14, 0.15, rel_tol=cs.LIMIT_REL_TOL)
        )


if __name__ == "__main__":
    unittest.main()

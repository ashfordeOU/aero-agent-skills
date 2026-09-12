#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.3.1.3 electromagnetic
interference safety margins.

Exercises
scripts/e20_electromagnetic_interference_safety_margins_logic.py
(stdlib unittest, offline). Contract: a critical point kind maps to
exactly one consequence category and an unrecognized kind raises; the
separation demanded follows the category; a decibel-scale case gives
the difference of the two levels while a linear case uses the
twenty-log law for an amplitude quantity and the ten-log law for a
power quantity; a non-positive linear level raises; the mandatory
operating conditions that no case exercises are reported; the
governing worst case is the smallest margin with ties resolved to the
first case declared; a margin that sits on the requirement to within
the named tolerance is not a finding while a real shortfall is; and
the aggregated review is compliant only when both finding lists are
empty.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electromagnetic_interference_safety_margins_logic as sm  # noqa: E402


def _case(condition, threshold, interference, quantity="voltage", scale="linear"):
    return {
        "condition": condition,
        "quantity": quantity,
        "scale": scale,
        "susceptibility_threshold": threshold,
        "interference_level": interference,
    }


def _full_condition_cases(threshold=1.0, interference=0.01):
    """One case per mandatory operating condition, all comfortably
    clear of the widest separation demanded (40 dB at 1.0 V / 0.01 V)."""
    return [
        _case(condition, threshold, interference)
        for condition in sorted(sm.MANDATORY_OPERATING_CONDITIONS)
    ]


def _clean_point():
    """An ordnance point that satisfies every clause 6.3.1.3 check."""
    return {
        "point_id": "EED-SEP-01",
        "point_kind": "electro_explosive_initiator",
        "cases": _full_condition_cases(),
    }


class CategorizeCriticalPointTest(unittest.TestCase):
    def test_initiator_is_ordnance(self):
        self.assertEqual(
            sm.categorize_critical_point("electro_explosive_initiator"), "ordnance"
        )

    def test_safe_and_arm_line_is_ordnance(self):
        self.assertEqual(
            sm.categorize_critical_point("safe_and_arm_command_line"), "ordnance"
        )

    def test_valve_drive_is_safety_critical(self):
        self.assertEqual(
            sm.categorize_critical_point("propellant_isolation_valve_drive"),
            "safety_critical",
        )

    def test_wheel_command_is_mission_critical(self):
        self.assertEqual(
            sm.categorize_critical_point("reaction_wheel_torque_command"),
            "mission_critical",
        )

    def test_housekeeping_sense_is_non_critical(self):
        self.assertEqual(
            sm.categorize_critical_point("housekeeping_temperature_sense"),
            "non_critical",
        )

    def test_unrecognized_point_kind_raises(self):
        with self.assertRaises(ValueError):
            sm.categorize_critical_point("thermal_blanket_standoff")

    def test_every_declared_kind_categorizes(self):
        kinds = (
            sm.ORDNANCE_POINT_KINDS
            | sm.SAFETY_CRITICAL_POINT_KINDS
            | sm.MISSION_CRITICAL_POINT_KINDS
            | sm.NON_CRITICAL_POINT_KINDS
        )
        for kind in sorted(kinds):
            self.assertIn(sm.categorize_critical_point(kind), sm.REQUIRED_MARGIN_DB)


class RequiredMarginTest(unittest.TestCase):
    def test_ordnance_demands_the_widest_separation(self):
        self.assertAlmostEqual(sm.required_margin_db("ordnance"), 20.0)

    def test_safety_critical_sits_below_ordnance(self):
        self.assertLess(
            sm.required_margin_db("safety_critical"),
            sm.required_margin_db("ordnance"),
        )

    def test_mission_critical_sits_below_safety_critical(self):
        self.assertLess(
            sm.required_margin_db("mission_critical"),
            sm.required_margin_db("safety_critical"),
        )

    def test_non_critical_demands_nothing_above_threshold(self):
        self.assertAlmostEqual(sm.required_margin_db("non_critical"), 0.0)

    def test_unrecognized_category_raises(self):
        with self.assertRaises(ValueError):
            sm.required_margin_db("nice_to_have")


class LevelConversionTest(unittest.TestCase):
    def test_one_microvolt_is_zero_dbuv(self):
        self.assertAlmostEqual(sm.volts_to_dbuv(1.0e-6), 0.0)

    def test_one_volt_is_one_hundred_twenty_dbuv(self):
        self.assertAlmostEqual(sm.volts_to_dbuv(1.0), 120.0)

    def test_dbuv_to_volts_inverts_volts_to_dbuv(self):
        self.assertAlmostEqual(sm.dbuv_to_volts(sm.volts_to_dbuv(0.047)), 0.047)

    def test_negative_dbuv_is_a_valid_level(self):
        self.assertAlmostEqual(sm.dbuv_to_volts(-20.0), 1.0e-7)

    def test_zero_volts_has_no_decibel_representation(self):
        with self.assertRaises(ValueError):
            sm.volts_to_dbuv(0.0)

    def test_negative_volts_raises(self):
        with self.assertRaises(ValueError):
            sm.volts_to_dbuv(-0.5)


class AmplitudeAndPowerMarginTest(unittest.TestCase):
    def test_amplitude_decade_is_twenty_decibels(self):
        self.assertAlmostEqual(sm.amplitude_margin_db(1.0, 0.1), 20.0)

    def test_amplitude_doubling_is_six_decibels(self):
        self.assertAlmostEqual(sm.amplitude_margin_db(2.0, 1.0), 6.020599913279624)

    def test_amplitude_equal_levels_is_zero(self):
        self.assertAlmostEqual(sm.amplitude_margin_db(0.4, 0.4), 0.0)

    def test_amplitude_interference_above_threshold_is_negative(self):
        self.assertLess(sm.amplitude_margin_db(0.1, 1.0), 0.0)

    def test_power_decade_is_ten_decibels(self):
        self.assertAlmostEqual(sm.power_margin_db(1.0e-3, 1.0e-4), 10.0)

    def test_power_law_is_half_the_amplitude_law_for_one_ratio(self):
        self.assertAlmostEqual(
            sm.power_margin_db(9.0, 3.0), sm.amplitude_margin_db(9.0, 3.0) / 2.0
        )

    def test_amplitude_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            sm.amplitude_margin_db(0.0, 0.1)

    def test_amplitude_negative_interference_raises(self):
        with self.assertRaises(ValueError):
            sm.amplitude_margin_db(1.0, -0.1)

    def test_power_zero_interference_raises(self):
        with self.assertRaises(ValueError):
            sm.power_margin_db(1.0, 0.0)

    def test_power_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            sm.power_margin_db(-1.0, 0.1)


class CaseMarginTest(unittest.TestCase):
    def test_linear_voltage_case_uses_amplitude_law(self):
        self.assertAlmostEqual(
            sm.case_margin_db(_case("mode_transition", 1.0, 0.1)), 20.0
        )

    def test_linear_power_case_uses_power_law(self):
        self.assertAlmostEqual(
            sm.case_margin_db(
                _case("mode_transition", 1.0e-3, 1.0e-4, quantity="power")
            ),
            10.0,
        )

    def test_decibel_case_is_the_difference_of_levels(self):
        self.assertAlmostEqual(
            sm.case_margin_db(
                _case("transmitter_keyed", 120.0, 94.0, scale="decibel")
            ),
            26.0,
        )

    def test_decibel_power_case_is_also_the_difference(self):
        self.assertAlmostEqual(
            sm.case_margin_db(
                _case(
                    "transmitter_keyed",
                    -30.0,
                    -70.0,
                    quantity="power",
                    scale="decibel",
                )
            ),
            40.0,
        )

    def test_scale_defaults_to_linear_when_absent(self):
        case = {
            "condition": "all_loads_energised",
            "quantity": "current",
            "susceptibility_threshold": 1.0,
            "interference_level": 0.1,
        }
        self.assertAlmostEqual(sm.case_margin_db(case), 20.0)

    def test_unrecognized_quantity_raises(self):
        with self.assertRaises(ValueError):
            sm.case_margin_db(_case("mode_transition", 1.0, 0.1, quantity="torque"))

    def test_unrecognized_scale_raises(self):
        with self.assertRaises(ValueError):
            sm.case_margin_db(_case("mode_transition", 1.0, 0.1, scale="percent"))

    def test_non_positive_linear_level_raises_through_the_helper(self):
        with self.assertRaises(ValueError):
            sm.case_margin_db(_case("mode_transition", 1.0, 0.0))


class OperatingConditionCoverageTest(unittest.TestCase):
    def test_full_set_leaves_nothing_missing(self):
        self.assertEqual(sm.missing_operating_conditions(_full_condition_cases()), [])

    def test_one_absent_condition_is_reported(self):
        cases = [
            c
            for c in _full_condition_cases()
            if c["condition"] != "transmitter_keyed"
        ]
        self.assertEqual(
            sm.missing_operating_conditions(cases), ["transmitter_keyed"]
        )

    def test_empty_case_list_reports_every_condition(self):
        self.assertEqual(
            sm.missing_operating_conditions([]),
            sorted(sm.MANDATORY_OPERATING_CONDITIONS),
        )

    def test_custom_mandatory_set_is_honoured(self):
        cases = [_case("eclipse_entry", 1.0, 0.01)]
        self.assertEqual(
            sm.missing_operating_conditions(
                cases, {"eclipse_entry", "eclipse_exit"}
            ),
            ["eclipse_exit"],
        )

    def test_empty_mandatory_set_raises(self):
        with self.assertRaises(ValueError):
            sm.missing_operating_conditions(_full_condition_cases(), set())

    def test_extra_conditions_are_not_findings(self):
        cases = _full_condition_cases() + [_case("eclipse_entry", 1.0, 0.01)]
        self.assertEqual(sm.missing_operating_conditions(cases), [])


class WorstCaseMarginTest(unittest.TestCase):
    def test_smallest_margin_governs(self):
        cases = [
            _case("all_loads_energised", 1.0, 0.01),
            _case("transmitter_keyed", 1.0, 0.5),
            _case("mode_transition", 1.0, 0.1),
        ]
        worst = sm.worst_case_margin(cases)
        self.assertEqual(worst["condition"], "transmitter_keyed")
        self.assertAlmostEqual(worst["margin_db"], 6.020599913279624)

    def test_single_case_is_its_own_worst_case(self):
        worst = sm.worst_case_margin([_case("mode_transition", 1.0, 0.1)])
        self.assertEqual(worst["condition"], "mode_transition")
        self.assertAlmostEqual(worst["margin_db"], 20.0)

    def test_tie_resolves_to_the_first_case_declared(self):
        cases = [
            _case("mode_transition", 1.0, 0.1),
            _case("transmitter_keyed", 2.0, 0.2),
        ]
        self.assertEqual(sm.worst_case_margin(cases)["condition"], "mode_transition")

    def test_mixed_scales_compare_on_one_axis(self):
        cases = [
            _case("mode_transition", 120.0, 100.0, scale="decibel"),
            _case("transmitter_keyed", 1.0, 0.5),
        ]
        self.assertEqual(sm.worst_case_margin(cases)["condition"], "transmitter_keyed")

    def test_empty_case_list_raises(self):
        with self.assertRaises(ValueError):
            sm.worst_case_margin([])


class MarginFindingsTest(unittest.TestCase):
    def test_comfortable_ordnance_point_has_no_finding(self):
        self.assertEqual(
            sm.margin_findings("EED-01", "ordnance", _full_condition_cases()), []
        )

    def test_short_ordnance_margin_is_reported(self):
        cases = [_case("transmitter_keyed", 1.0, 0.5)]
        findings = sm.margin_findings("EED-01", "ordnance", cases)
        self.assertEqual(len(findings), 1)
        self.assertEqual(
            findings[0]["issue"], "interference_safety_margin_below_requirement"
        )
        self.assertEqual(findings[0]["condition"], "transmitter_keyed")
        self.assertAlmostEqual(findings[0]["required_margin_db"], 20.0)

    def test_margin_exactly_on_the_requirement_is_not_a_finding(self):
        cases = [_case("mode_transition", 1.0, 0.1)]
        self.assertEqual(sm.margin_findings("EED-01", "ordnance", cases), [])

    def test_representation_error_at_the_boundary_is_absorbed(self):
        # 0.7 V over 0.07 V is exactly a decade, but the quotient is a
        # few units in the last place below ten, so the margin computes
        # just under the 20 dB an ordnance point demands.
        cases = [_case("mode_transition", 0.7, 0.07)]
        raw = sm.case_margin_db(cases[0])
        self.assertLess(raw, 20.0)
        self.assertEqual(sm.margin_findings("EED-01", "ordnance", cases), [])

    def test_a_real_shortfall_survives_the_tolerance(self):
        cases = [_case("mode_transition", 0.7, 0.0701)]
        self.assertEqual(len(sm.margin_findings("EED-01", "ordnance", cases)), 1)

    def test_non_critical_point_fails_only_below_its_threshold(self):
        clear = [_case("mode_transition", 1.0, 0.9)]
        exceeded = [_case("mode_transition", 0.9, 1.0)]
        self.assertEqual(sm.margin_findings("HK-01", "non_critical", clear), [])
        self.assertEqual(len(sm.margin_findings("HK-01", "non_critical", exceeded)), 1)

    def test_every_short_case_is_reported_separately(self):
        cases = [
            _case("transmitter_keyed", 1.0, 0.5),
            _case("mode_transition", 1.0, 0.4),
            _case("all_loads_energised", 1.0, 0.001),
        ]
        self.assertEqual(len(sm.margin_findings("EED-01", "ordnance", cases)), 2)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            sm.margin_findings(
                "EED-01", "ordnance", _full_condition_cases(), tolerance_db=-1.0
            )


class CriticalPointReviewTest(unittest.TestCase):
    def test_clean_point_is_compliant(self):
        review = sm.critical_point_review(_clean_point())
        self.assertEqual(review["coverage"], [])
        self.assertEqual(review["margin"], [])
        self.assertTrue(sm.is_point_compliant(review))

    def test_missing_condition_breaks_coverage_only(self):
        point = _clean_point()
        point["cases"] = [
            c for c in point["cases"] if c["condition"] != "mode_transition"
        ]
        review = sm.critical_point_review(point)
        self.assertEqual(len(review["coverage"]), 1)
        self.assertEqual(review["coverage"][0]["condition"], "mode_transition")
        self.assertEqual(review["margin"], [])
        self.assertFalse(sm.is_point_compliant(review))

    def test_short_margin_breaks_margin_only(self):
        point = _clean_point()
        point["cases"][0]["interference_level"] = 0.5
        review = sm.critical_point_review(point)
        self.assertEqual(review["coverage"], [])
        self.assertEqual(len(review["margin"]), 1)
        self.assertFalse(sm.is_point_compliant(review))

    def test_both_lists_can_be_populated_at_once(self):
        point = _clean_point()
        point["cases"] = [_case("transmitter_keyed", 1.0, 0.5)]
        review = sm.critical_point_review(point)
        self.assertEqual(len(review["coverage"]), 4)
        self.assertEqual(len(review["margin"]), 1)

    def test_unrecognized_kind_raises_in_review(self):
        point = _clean_point()
        point["point_kind"] = "thermal_blanket_standoff"
        with self.assertRaises(ValueError):
            sm.critical_point_review(point)

    def test_empty_case_list_raises_in_review(self):
        point = _clean_point()
        point["cases"] = []
        with self.assertRaises(ValueError):
            sm.critical_point_review(point)

    def test_review_does_not_mutate_input(self):
        point = _clean_point()
        snapshot = [dict(c) for c in point["cases"]]
        sm.critical_point_review(point)
        self.assertEqual(point["cases"], snapshot)

    def test_custom_mandatory_conditions_are_used_by_the_review(self):
        point = _clean_point()
        point["mandatory_conditions"] = {"all_loads_energised"}
        review = sm.critical_point_review(point)
        self.assertEqual(review["coverage"], [])

    def test_summary_names_the_governing_condition(self):
        point = _clean_point()
        point["cases"][0]["interference_level"] = 0.5
        governing = point["cases"][0]["condition"]
        summary = sm.point_margin_summary(point)
        self.assertEqual(summary["category"], "ordnance")
        self.assertAlmostEqual(summary["required_margin_db"], 20.0)
        self.assertEqual(summary["governing_condition"], governing)
        self.assertAlmostEqual(
            summary["worst_case_margin_db"], 20.0 * math.log10(2.0)
        )

    def test_summary_raises_for_an_unrecognized_kind(self):
        point = _clean_point()
        point["point_kind"] = "thermal_blanket_standoff"
        with self.assertRaises(ValueError):
            sm.point_margin_summary(point)


if __name__ == "__main__":
    unittest.main()

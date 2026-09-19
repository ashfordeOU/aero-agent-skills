#!/usr/bin/env python3
"""Gate 3 contract test for e50-failure-modes.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_failure_modes.py
"""

import unittest

from e50_failure_modes_logic import (
    BOTH,
    DOWNLINK,
    MET,
    NOT_MET,
    UNASSESSED,
    UPLINK,
    assess_failure_mode_performance,
    governing_mode,
    margin_meets,
    mode_applies,
    mode_margin_db,
    normalise_modes,
    total_degradation_db,
    uncovered_modes,
    validate_decibels,
    validate_direction,
    validate_mode,
)

SINGLE_TWTA = {
    "name": "twta-single-failure",
    "degradations_db": {"output-power-loss": 3.0},
    "direction": DOWNLINK,
    "recovered_by_redundancy": True,
}
ANTENNA_POINTING = {
    "name": "antenna-pointing-degraded",
    "degradations_db": {"pointing-loss": 1.5, "polarisation-loss": 0.5},
    "direction": BOTH,
    "recovered_by_redundancy": False,
}
UPLINK_RECEIVER = {
    "name": "uplink-receiver-single-failure",
    "degradations_db": {"noise-figure-rise": 1.0},
    "direction": UPLINK,
    "recovered_by_redundancy": True,
}
MODES = (SINGLE_TWTA, ANTENNA_POINTING, UPLINK_RECEIVER)


class TestValidation(unittest.TestCase):
    def test_a_boolean_is_not_a_decibel_figure(self):
        with self.assertRaises(ValueError):
            validate_decibels(True, "margin")

    def test_an_infinite_margin_is_refused(self):
        with self.assertRaises(ValueError):
            validate_decibels(float("inf"), "margin")

    def test_an_unknown_direction_is_refused(self):
        with self.assertRaises(ValueError):
            validate_direction("crosslink")

    def test_a_direction_is_normalised_to_lower_case(self):
        self.assertEqual(validate_direction("  UpLink "), UPLINK)

    def test_a_mode_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_mode({"degradations_db": {"loss": 1.0}})

    def test_a_negative_degradation_is_refused(self):
        with self.assertRaises(ValueError):
            validate_mode({"name": "gain", "degradations_db": {"loss": -1.0}})

    def test_a_non_boolean_redundancy_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_mode(
                {"name": "m", "degradations_db": {}, "recovered_by_redundancy": "yes"}
            )

    def test_a_duplicate_mode_name_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_modes([SINGLE_TWTA, dict(SINGLE_TWTA)])

    def test_modes_come_back_in_name_order(self):
        names = [m["name"] for m in normalise_modes(MODES)]
        self.assertEqual(names, sorted(names))


class TestMargins(unittest.TestCase):
    def test_concurrent_contributors_are_summed(self):
        self.assertAlmostEqual(
            total_degradation_db(ANTENNA_POINTING), 2.0, places=9
        )

    def test_a_mode_with_no_contributor_costs_nothing(self):
        self.assertAlmostEqual(
            total_degradation_db({"name": "nominal", "degradations_db": {}}),
            0.0,
            places=9,
        )

    def test_the_margin_is_the_nominal_less_the_degradation(self):
        self.assertAlmostEqual(mode_margin_db(6.0, SINGLE_TWTA), 3.0, places=9)

    def test_a_margin_exactly_on_the_requirement_is_met(self):
        margin = mode_margin_db(5.0, ANTENNA_POINTING)
        self.assertAlmostEqual(margin, 3.0, places=9)
        self.assertTrue(margin_meets(margin, 3.0))

    def test_a_margin_clearly_under_the_requirement_is_not_met(self):
        self.assertFalse(margin_meets(mode_margin_db(2.0, SINGLE_TWTA), 3.0))

    def test_an_uplink_mode_does_not_apply_to_the_downlink(self):
        self.assertFalse(mode_applies(UPLINK_RECEIVER, DOWNLINK))

    def test_a_both_direction_mode_applies_to_either_link(self):
        self.assertTrue(mode_applies(ANTENNA_POINTING, UPLINK))
        self.assertTrue(mode_applies(ANTENNA_POINTING, DOWNLINK))


class TestGoverningMode(unittest.TestCase):
    def test_the_worst_applicable_mode_governs_the_downlink(self):
        self.assertEqual(governing_mode(6.0, MODES, DOWNLINK), "twta-single-failure")

    def test_the_worst_applicable_mode_governs_the_uplink(self):
        self.assertEqual(
            governing_mode(6.0, MODES, UPLINK), "antenna-pointing-degraded"
        )

    def test_an_empty_mode_list_has_no_governing_mode(self):
        self.assertIsNone(governing_mode(6.0, ()))

    def test_the_largest_single_contributor_does_not_always_govern(self):
        stacked = {
            "name": "stacked-degradation",
            "degradations_db": {"a": 1.4, "b": 1.4, "c": 1.4},
            "direction": DOWNLINK,
        }
        self.assertEqual(
            governing_mode(8.0, (SINGLE_TWTA, stacked), DOWNLINK),
            "stacked-degradation",
        )


class TestCoverage(unittest.TestCase):
    def test_a_required_mode_absent_from_the_budget_is_named(self):
        self.assertEqual(
            uncovered_modes(MODES, ("twta-single-failure", "solar-conjunction")),
            ("solar-conjunction",),
        )

    def test_every_required_mode_present_leaves_nothing_uncovered(self):
        self.assertEqual(uncovered_modes(MODES, ("twta-single-failure",)), ())

    def test_a_blank_required_mode_name_is_refused(self):
        with self.assertRaises(ValueError):
            uncovered_modes(MODES, ("  ",))


class TestAssessment(unittest.TestCase):
    def test_a_budget_covering_every_mode_with_margin_is_compliant(self):
        report = assess_failure_mode_performance(
            8.0, 3.0, MODES, ("twta-single-failure", "antenna-pointing-degraded")
        )
        self.assertEqual(report["verdict"], MET)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["failing_modes"], ())

    def test_an_uncovered_required_mode_makes_the_link_unassessed(self):
        report = assess_failure_mode_performance(
            8.0, 3.0, MODES, ("eclipse-battery-limited",)
        )
        self.assertEqual(report["verdict"], UNASSESSED)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["uncovered_required_modes"], ("eclipse-battery-limited",))

    def test_a_failing_mode_is_named_even_when_nominal_passes(self):
        report = assess_failure_mode_performance(4.0, 3.0, MODES)
        self.assertEqual(report["nominal_mode_grade"], MET)
        self.assertEqual(report["verdict"], NOT_MET)
        self.assertIn("twta-single-failure", report["failing_modes"])

    def test_a_mode_the_direction_excludes_is_not_a_failing_mode(self):
        report = assess_failure_mode_performance(4.0, 3.0, MODES, (), UPLINK)
        self.assertNotIn("twta-single-failure", report["failing_modes"])

    def test_every_declared_mode_is_graded_in_the_report(self):
        report = assess_failure_mode_performance(8.0, 3.0, MODES)
        self.assertEqual(len(report["modes"]), len(MODES))
        self.assertEqual(
            {m["grade"] for m in report["modes"]}, {MET}
        )

    def test_a_mode_landing_exactly_on_the_requirement_grades_as_met(self):
        report = assess_failure_mode_performance(5.0, 3.0, (ANTENNA_POINTING,))
        graded = report["modes"][0]
        self.assertAlmostEqual(graded["margin_db"], 3.0, places=9)
        self.assertEqual(graded["grade"], MET)
        self.assertEqual(report["verdict"], MET)

    def test_the_finding_names_the_reason_the_link_is_not_compliant(self):
        report = assess_failure_mode_performance(4.0, 3.0, MODES)
        self.assertIn("falls short", report["finding"])

    def test_a_non_sequence_mode_list_is_refused(self):
        with self.assertRaises(ValueError):
            assess_failure_mode_performance(8.0, 3.0, "twta-single-failure")


if __name__ == "__main__":
    unittest.main()

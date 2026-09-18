#!/usr/bin/env python3
"""Gate 3 contract test for q6005-active-chip-bondability-test.

Offline, deterministic, stdlib unittest. Exercises the clause 8.3.2
bondability logic: the pull-strength schedule and its interpolation, the
exact-boundary comparison, separation-mode grouping, record normalization,
the lot statistics and the sampling floor.
"""

import math
import unittest

from q6005_active_chip_bondability_test_logic import (
    MEAN_MARGIN_FACTOR,
    MIN_BONDS_TESTED,
    assess_bondability,
    categorize_failure_mode,
    evaluate_bond_test,
    format_bondability_report,
    minimum_pull_force_gf,
    normalize_bond_tests,
    required_mean_pull_force_gf,
    sample_mean,
    sample_standard_deviation,
    validate_bond_test,
)


def pull(**kw):
    entry = {
        "pad_id": "pad-01",
        "wire_diameter_um": 25.0,
        "pull_force_gf": 6.0,
        "failure_mode": "wire-break",
    }
    entry.update(kw)
    return entry


def healthy_lot(count=12):
    return [pull(pad_id="pad-%02d" % i) for i in range(1, count + 1)]


class TestPullStrengthSchedule(unittest.TestCase):
    def test_anchor_diameter_returns_its_own_floor(self):
        self.assertAlmostEqual(minimum_pull_force_gf(25.0), 3.0, places=9)

    def test_smallest_anchor_returns_its_floor(self):
        self.assertAlmostEqual(minimum_pull_force_gf(18.0), 2.0, places=9)

    def test_interpolates_between_two_anchors(self):
        self.assertAlmostEqual(minimum_pull_force_gf(29.0), 3.75, places=9)

    def test_floor_rises_with_diameter(self):
        thin = minimum_pull_force_gf(18.0)
        thick = minimum_pull_force_gf(50.0)
        self.assertGreater(thick, thin)

    def test_diameter_below_span_raises(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf(12.0)

    def test_diameter_above_span_raises(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf(75.0)

    def test_non_numeric_diameter_raises(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_gf("twenty-five")


class TestSeparationModeGrouping(unittest.TestCase):
    def test_wire_break_is_structural(self):
        self.assertEqual(categorize_failure_mode("wire-break"), "structural")

    def test_heel_break_is_structural(self):
        self.assertEqual(categorize_failure_mode("Heel-Break"), "structural")

    def test_pad_lift_is_interface(self):
        self.assertEqual(categorize_failure_mode("pad-lift"), "interface")

    def test_cratering_is_interface(self):
        self.assertEqual(categorize_failure_mode("cratering"), "interface")

    def test_unrecognised_mode_raises(self):
        with self.assertRaises(ValueError):
            categorize_failure_mode("came apart somehow")

    def test_empty_mode_raises(self):
        with self.assertRaises(ValueError):
            categorize_failure_mode("   ")


class TestRecordNormalization(unittest.TestCase):
    def test_valid_record_normalizes(self):
        item = validate_bond_test(pull())
        self.assertEqual(item["pad_id"], "pad-01")
        self.assertEqual(item["mode_group"], "structural")

    def test_missing_pad_id_raises(self):
        with self.assertRaises(ValueError):
            validate_bond_test(pull(pad_id=""))

    def test_negative_force_raises(self):
        with self.assertRaises(ValueError):
            validate_bond_test(pull(pull_force_gf=-1.0))

    def test_boolean_force_raises(self):
        with self.assertRaises(ValueError):
            validate_bond_test(pull(pull_force_gf=True))

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            validate_bond_test(["pad-01", 6.0])

    def test_duplicate_pad_record_raises(self):
        with self.assertRaises(ValueError):
            normalize_bond_tests([pull(), pull()])

    def test_empty_record_set_raises(self):
        with self.assertRaises(ValueError):
            normalize_bond_tests([])


class TestBoundaryComparison(unittest.TestCase):
    def test_reading_exactly_on_the_floor_conforms(self):
        item = validate_bond_test(pull(pull_force_gf=3.0))
        evaluation = evaluate_bond_test(item)
        self.assertTrue(evaluation["force_ok"])
        self.assertAlmostEqual(evaluation["margin_gf"], 0.0, places=9)

    def test_interpolated_floor_hit_exactly_conforms(self):
        item = validate_bond_test(pull(wire_diameter_um=29.0, pull_force_gf=3.75))
        evaluation = evaluate_bond_test(item)
        self.assertTrue(evaluation["force_ok"])
        self.assertAlmostEqual(evaluation["required_gf"], 3.75, places=9)

    def test_reading_well_below_the_floor_fails(self):
        item = validate_bond_test(pull(pull_force_gf=1.0))
        evaluation = evaluate_bond_test(item)
        self.assertFalse(evaluation["force_ok"])
        self.assertFalse(evaluation["conforming"])

    def test_interface_separation_fails_at_any_force(self):
        item = validate_bond_test(pull(pull_force_gf=40.0, failure_mode="pad-lift"))
        evaluation = evaluate_bond_test(item)
        self.assertTrue(evaluation["force_ok"])
        self.assertFalse(evaluation["conforming"])


class TestLotStatistics(unittest.TestCase):
    def test_mean_of_a_reading_set(self):
        self.assertAlmostEqual(sample_mean([2.0, 4.0, 6.0]), 4.0, places=9)

    def test_empty_mean_raises(self):
        with self.assertRaises(ValueError):
            sample_mean([])

    def test_sample_standard_deviation(self):
        self.assertAlmostEqual(
            sample_standard_deviation([1.0, 3.0]), math.sqrt(2.0), places=9
        )

    def test_single_reading_standard_deviation_raises(self):
        with self.assertRaises(ValueError):
            sample_standard_deviation([4.0])

    def test_mean_floor_carries_the_margin_factor(self):
        evaluations = [evaluate_bond_test(item) for item in normalize_bond_tests(healthy_lot(2))]
        self.assertAlmostEqual(
            required_mean_pull_force_gf(evaluations), 3.0 * MEAN_MARGIN_FACTOR, places=9
        )

    def test_mean_floor_of_empty_set_raises(self):
        with self.assertRaises(ValueError):
            required_mean_pull_force_gf([])


class TestLotAssessment(unittest.TestCase):
    def test_healthy_lot_is_bondable(self):
        report = assess_bondability(healthy_lot())
        self.assertTrue(report["bondable"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["bonds_tested"], 12)

    def test_short_sample_is_a_finding(self):
        report = assess_bondability(healthy_lot(4))
        self.assertFalse(report["bondable"])
        self.assertTrue(any("sampling floor" in f for f in report["findings"]))

    def test_one_interface_separation_fails_the_lot(self):
        lot = healthy_lot()
        lot[3] = pull(pad_id="pad-04", pull_force_gf=30.0, failure_mode="cratering")
        report = assess_bondability(lot)
        self.assertFalse(report["bondable"])
        self.assertEqual(report["interface_failures"], ["pad-04"])

    def test_lot_mean_on_its_floor_passes(self):
        lot = [
            pull(pad_id="pad-%02d" % i, pull_force_gf=3.75)
            for i in range(1, MIN_BONDS_TESTED + 1)
        ]
        report = assess_bondability(lot)
        self.assertTrue(report["mean_ok"])
        self.assertAlmostEqual(report["mean_pull_force_gf"], 3.75, places=9)
        self.assertTrue(report["bondable"])

    def test_lot_mean_clearly_under_its_floor_is_a_finding(self):
        lot = [
            pull(pad_id="pad-%02d" % i, pull_force_gf=3.0)
            for i in range(1, MIN_BONDS_TESTED + 1)
        ]
        report = assess_bondability(lot)
        self.assertFalse(report["mean_ok"])
        self.assertTrue(any("mean floor" in f for f in report["findings"]))

    def test_evaluations_are_sorted_by_pad(self):
        report = assess_bondability(healthy_lot())
        pads = [e["pad_id"] for e in report["evaluations"]]
        self.assertEqual(pads, sorted(pads))

    def test_non_integer_sampling_floor_raises(self):
        with self.assertRaises(ValueError):
            assess_bondability(healthy_lot(), minimum_bonds=2.5)

    def test_zero_sampling_floor_raises(self):
        with self.assertRaises(ValueError):
            assess_bondability(healthy_lot(), minimum_bonds=0)


class TestReportRendering(unittest.TestCase):
    def test_report_is_deterministic(self):
        lot = healthy_lot()
        first = format_bondability_report(assess_bondability(lot))
        second = format_bondability_report(assess_bondability(lot))
        self.assertEqual(first, second)
        self.assertIn("BONDABLE", first)

    def test_report_text_lists_findings(self):
        text = format_bondability_report(assess_bondability(healthy_lot(3)))
        self.assertIn("NOT BONDABLE", text)
        self.assertIn("FINDING:", text)


if __name__ == "__main__":
    unittest.main()

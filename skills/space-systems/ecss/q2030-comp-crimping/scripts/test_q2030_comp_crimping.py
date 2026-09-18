#!/usr/bin/env python3
"""Contract test for the complementary crimping requirements leaf."""

import unittest

from q2030_comp_crimping_logic import (
    FORCE_TOLERANCE_N,
    assess_crimp_lot,
    crimp_height_verdict,
    crimp_height_window,
    evaluate_crimp,
    governing_limit,
    grade_pull_sample,
    minimum_pull_force_n,
    normalize_source,
    pull_sample_size,
    tool_calibration_current,
)

FORCE_TABLE = {20: 60.0, 22: 40.0, 24: 25.0, 26: 15.0}


def good_crimp(**overrides):
    record = {
        "id": "C-1",
        "gauge_awg": 22,
        "measured_height_mm": 1.200,
        "nominal_height_mm": 1.200,
        "height_tolerance_mm": 0.030,
        "wires_in_barrel": 1,
        "solder_present": False,
        "contact_has_insulation_support": True,
        "insulation_supported": True,
    }
    record.update(overrides)
    return record


def good_lot(**overrides):
    spec = {
        "crimps": [good_crimp(id="C-1"), good_crimp(id="C-2"), good_crimp(id="C-3")],
        "force_table": FORCE_TABLE,
        "sampling_fraction": 0.10,
        "pull_forces_n": [52.0, 48.5, 61.0],
        "days_since_calibration": 30,
        "calibration_interval_days": 180,
    }
    spec.update(overrides)
    return spec


class TestNormalizeSource(unittest.TestCase):
    def test_canonical_complementary_survives(self):
        self.assertEqual(normalize_source("complementary"), "complementary")

    def test_ecss_alias_folds_to_complementary(self):
        self.assertEqual(normalize_source(" ECSS "), "complementary")

    def test_workmanship_alias_folds_to_delegated(self):
        self.assertEqual(normalize_source("Workmanship"), "delegated")

    def test_underscore_spelling_is_folded(self):
        self.assertEqual(normalize_source("delegated_workmanship"), "delegated")

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            normalize_source("supplier-drawing")

    def test_non_string_source_raises(self):
        with self.assertRaises(ValueError):
            normalize_source(7)


class TestGoverningLimit(unittest.TestCase):
    def test_complementary_value_wins_when_both_present(self):
        result = governing_limit(50.0, 40.0, "min")
        self.assertEqual(result["source"], "complementary")
        self.assertAlmostEqual(result["value"], 50.0, places=9)

    def test_precedence_is_by_source_not_by_tightness(self):
        result = governing_limit(30.0, 40.0, "min")
        self.assertEqual(result["source"], "complementary")
        self.assertAlmostEqual(result["value"], 30.0, places=9)

    def test_looser_complementary_minimum_is_named_a_relaxation(self):
        self.assertTrue(governing_limit(30.0, 40.0, "min")["relaxation"])

    def test_looser_complementary_maximum_is_named_a_relaxation(self):
        self.assertTrue(governing_limit(0.5, 0.2, "max")["relaxation"])

    def test_tighter_complementary_value_is_not_a_relaxation(self):
        self.assertFalse(governing_limit(0.1, 0.2, "max")["relaxation"])

    def test_delegated_value_governs_when_clause_is_silent(self):
        result = governing_limit(None, 40.0, "min")
        self.assertEqual(result["source"], "delegated")

    def test_two_absent_sources_raise(self):
        with self.assertRaises(ValueError):
            governing_limit(None, None, "min")

    def test_unknown_sense_raises(self):
        with self.assertRaises(ValueError):
            governing_limit(1.0, 2.0, "tighter")


class TestCrimpHeightWindow(unittest.TestCase):
    def test_window_brackets_the_nominal(self):
        low, high = crimp_height_window(1.200, 0.030)
        self.assertAlmostEqual(low, 1.170, places=9)
        self.assertAlmostEqual(high, 1.230, places=9)

    def test_tolerance_at_or_above_nominal_raises(self):
        with self.assertRaises(ValueError):
            crimp_height_window(0.030, 0.030)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            crimp_height_window(1.200, -0.010)

    def test_non_numeric_nominal_raises(self):
        with self.assertRaises(ValueError):
            crimp_height_window("1.2", 0.03)


class TestCrimpHeightVerdict(unittest.TestCase):
    def test_nominal_height_is_inside(self):
        self.assertTrue(crimp_height_verdict(1.200, 1.200, 0.030)["inside_window"])

    def test_height_exactly_on_the_upper_edge_is_inside(self):
        verdict = crimp_height_verdict(1.230, 1.200, 0.030)
        self.assertTrue(verdict["inside_window"])
        self.assertAlmostEqual(verdict["deviation_mm"], 0.030, places=9)

    def test_height_exactly_on_the_lower_edge_is_inside(self):
        self.assertTrue(crimp_height_verdict(1.170, 1.200, 0.030)["inside_window"])

    def test_last_place_overshoot_is_still_inside(self):
        self.assertTrue(crimp_height_verdict(1.230 + 1e-12, 1.200, 0.030)["inside_window"])

    def test_clearly_tall_crimp_is_outside(self):
        self.assertFalse(crimp_height_verdict(1.300, 1.200, 0.030)["inside_window"])

    def test_clearly_flat_crimp_is_outside(self):
        self.assertFalse(crimp_height_verdict(1.050, 1.200, 0.030)["inside_window"])


class TestPullForceTable(unittest.TestCase):
    def test_tabulated_gauge_returns_its_minimum(self):
        self.assertAlmostEqual(minimum_pull_force_n(22, FORCE_TABLE), 40.0, places=9)

    def test_untabulated_gauge_raises_rather_than_extrapolating(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_n(21, FORCE_TABLE)

    def test_non_integer_gauge_raises(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_n(22.0, FORCE_TABLE)

    def test_empty_table_raises(self):
        with self.assertRaises(ValueError):
            minimum_pull_force_n(22, {})


class TestPullSampleSize(unittest.TestCase):
    def test_fraction_is_rounded_up(self):
        self.assertEqual(pull_sample_size(41, 0.10, 1), 5)

    def test_exact_fraction_does_not_gain_a_sample(self):
        self.assertEqual(pull_sample_size(40, 0.10, 1), 4)

    def test_floor_applies_to_a_small_lot(self):
        self.assertEqual(pull_sample_size(5, 0.10), 3)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(pull_sample_size(2, 0.10), 2)

    def test_zero_lot_raises(self):
        with self.assertRaises(ValueError):
            pull_sample_size(0, 0.10)

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            pull_sample_size(10, 1.5)


class TestGradePullSample(unittest.TestCase):
    def test_all_pulls_above_minimum_pass(self):
        self.assertTrue(grade_pull_sample([50.0, 45.0], 40.0)["sample_passes"])

    def test_pull_exactly_on_the_minimum_meets_it(self):
        self.assertTrue(grade_pull_sample([40.0], 40.0)["sample_passes"])

    def test_last_place_shortfall_still_meets_the_minimum(self):
        self.assertTrue(grade_pull_sample([40.0 - FORCE_TOLERANCE_N / 2.0], 40.0)["sample_passes"])

    def test_one_low_pull_fails_the_sample(self):
        graded = grade_pull_sample([50.0, 12.0], 40.0)
        self.assertFalse(graded["sample_passes"])
        self.assertEqual(graded["shortfall_count"], 1)

    def test_a_high_mean_does_not_rescue_a_low_pull(self):
        self.assertFalse(grade_pull_sample([90.0, 90.0, 10.0], 40.0)["sample_passes"])

    def test_empty_sample_raises(self):
        with self.assertRaises(ValueError):
            grade_pull_sample([], 40.0)


class TestEvaluateCrimp(unittest.TestCase):
    def test_conforming_crimp_has_no_finding(self):
        self.assertTrue(evaluate_crimp(good_crimp(), FORCE_TABLE)["conforming"])

    def test_out_of_window_height_is_a_finding(self):
        record = evaluate_crimp(good_crimp(measured_height_mm=1.320), FORCE_TABLE)
        self.assertFalse(record["conforming"])

    def test_unqualified_second_wire_is_a_finding(self):
        record = evaluate_crimp(good_crimp(wires_in_barrel=2), FORCE_TABLE)
        self.assertFalse(record["conforming"])

    def test_qualified_multiple_wire_process_is_accepted(self):
        record = evaluate_crimp(
            good_crimp(wires_in_barrel=2, multiple_wire_crimp_qualified=True), FORCE_TABLE
        )
        self.assertTrue(record["conforming"])

    def test_solder_in_the_barrel_is_a_finding(self):
        self.assertFalse(evaluate_crimp(good_crimp(solder_present=True), FORCE_TABLE)["conforming"])

    def test_unengaged_insulation_support_is_a_finding(self):
        record = evaluate_crimp(good_crimp(insulation_supported=False), FORCE_TABLE)
        self.assertFalse(record["conforming"])

    def test_contact_without_support_feature_is_not_penalized(self):
        record = evaluate_crimp(
            good_crimp(contact_has_insulation_support=False, insulation_supported=False),
            FORCE_TABLE,
        )
        self.assertTrue(record["conforming"])

    def test_missing_key_raises(self):
        broken = good_crimp()
        del broken["nominal_height_mm"]
        with self.assertRaises(ValueError):
            evaluate_crimp(broken, FORCE_TABLE)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_crimp(good_crimp(id="  "), FORCE_TABLE)


class TestToolCalibration(unittest.TestCase):
    def test_fresh_tool_is_current(self):
        self.assertTrue(tool_calibration_current(10, 180))

    def test_tool_on_its_interval_day_is_still_current(self):
        self.assertTrue(tool_calibration_current(180, 180))

    def test_lapsed_tool_is_not_current(self):
        self.assertFalse(tool_calibration_current(181, 180))

    def test_negative_age_raises(self):
        with self.assertRaises(ValueError):
            tool_calibration_current(-1, 180)


class TestAssessCrimpLot(unittest.TestCase):
    def test_clean_lot_is_compliant(self):
        report = assess_crimp_lot(good_lot())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])

    def test_governing_minimum_is_the_toughest_gauge_in_the_lot(self):
        spec = good_lot(
            crimps=[good_crimp(id="C-1", gauge_awg=26), good_crimp(id="C-2", gauge_awg=20)],
            pull_forces_n=[70.0, 65.0, 62.0],
        )
        self.assertAlmostEqual(report_minimum(spec), 60.0, places=9)

    def test_short_tensile_sample_is_a_finding(self):
        spec = good_lot(pull_forces_n=[52.0])
        report = assess_crimp_lot(spec)
        self.assertFalse(report["compliant"])

    def test_low_pull_is_a_finding(self):
        report = assess_crimp_lot(good_lot(pull_forces_n=[52.0, 10.0, 61.0]))
        self.assertFalse(report["compliant"])

    def test_lapsed_calibration_is_a_finding(self):
        report = assess_crimp_lot(good_lot(days_since_calibration=400))
        self.assertFalse(report["tool_calibration_current"])
        self.assertFalse(report["compliant"])

    def test_duplicate_crimp_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_crimp_lot(good_lot(crimps=[good_crimp(id="C-1"), good_crimp(id="C-1")]))

    def test_empty_lot_raises(self):
        with self.assertRaises(ValueError):
            assess_crimp_lot(good_lot(crimps=[]))

    def test_missing_spec_key_raises(self):
        spec = good_lot()
        del spec["force_table"]
        with self.assertRaises(ValueError):
            assess_crimp_lot(spec)

    def test_required_sample_count_is_reported(self):
        self.assertEqual(assess_crimp_lot(good_lot())["required_pull_samples"], 3)


def report_minimum(spec):
    return assess_crimp_lot(spec)["pull"]["minimum_force_n"]


if __name__ == "__main__":
    unittest.main()

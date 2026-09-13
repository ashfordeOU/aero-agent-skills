#!/usr/bin/env python3
"""Contract test for the EMC measurement tolerances leaf."""

import unittest

from e2007_emc_measurement_tolerances_logic import (
    AMPLITUDE_TOLERANCE_DB,
    DISTANCE_TOLERANCE_FLOOR_M,
    DISTANCE_TOLERANCE_FRACTION,
    FREQUENCY_TOLERANCE_FRACTION,
    MEASUREMENT_BANDS,
    assess_measurement_campaign,
    check_amplitude_tolerance,
    check_distance_tolerance,
    check_dwell_time,
    check_frequency_tolerance,
    check_scan_step,
    check_uncertainty_budget,
    evaluate_measurement_point,
    measurement_uncertainty_rss,
    percent_deviation,
    select_band,
)


def good_point(**overrides):
    point = {
        "id": "P-100MHz",
        "nominal_frequency_hz": 1.0e8,
        "actual_frequency_hz": 1.0e8,
        "nominal_distance_m": 1.0,
        "actual_distance_m": 1.0,
        "target_amplitude_db": 30.0,
        "actual_amplitude_db": 30.0,
        "dwell_s": 0.5,
    }
    point.update(overrides)
    return point


def sweep():
    return [
        good_point(id="P-1", nominal_frequency_hz=1.0e8, actual_frequency_hz=1.0e8),
        good_point(
            id="P-2", nominal_frequency_hz=1.004e8, actual_frequency_hz=1.004e8
        ),
        good_point(
            id="P-3", nominal_frequency_hz=1.008e8, actual_frequency_hz=1.008e8
        ),
    ]


class TestPercentDeviation(unittest.TestCase):
    def test_positive_deviation(self):
        self.assertAlmostEqual(percent_deviation(1.0, 1.05), 5.0)

    def test_negative_deviation(self):
        self.assertAlmostEqual(percent_deviation(2.0, 1.9), -5.0)

    def test_zero_deviation(self):
        self.assertAlmostEqual(percent_deviation(3.0, 3.0), 0.0)

    def test_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            percent_deviation(0.0, 1.0)

    def test_negative_nominal_raises(self):
        with self.assertRaises(ValueError):
            percent_deviation(-1.0, 1.0)

    def test_non_numeric_actual_raises(self):
        with self.assertRaises(ValueError):
            percent_deviation(1.0, "1.05")


class TestDistanceTolerance(unittest.TestCase):
    def test_nominal_separation_is_within(self):
        result = check_distance_tolerance(1.0, 1.0)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["deviation"], 0.0)

    def test_allowed_band_is_a_fraction_of_nominal(self):
        result = check_distance_tolerance(2.0, 2.0)
        self.assertAlmostEqual(result["allowed"], 2.0 * DISTANCE_TOLERANCE_FRACTION)

    def test_short_separation_uses_the_absolute_floor(self):
        result = check_distance_tolerance(0.1, 0.1)
        self.assertAlmostEqual(result["allowed"], DISTANCE_TOLERANCE_FLOOR_M)

    def test_exact_boundary_survives_float_representation(self):
        result = check_distance_tolerance(1.0, 1.05)
        # the difference lands a few ULPs above the exact 5 % allowance
        self.assertGreater(result["deviation"], 1.0 * DISTANCE_TOLERANCE_FRACTION)
        self.assertTrue(result["within"])

    def test_genuine_overshoot_is_out_of_tolerance(self):
        result = check_distance_tolerance(1.0, 1.2)
        self.assertFalse(result["within"])
        self.assertAlmostEqual(result["percent"], 20.0)

    def test_undershoot_is_symmetric(self):
        self.assertFalse(check_distance_tolerance(1.0, 0.8)["within"])

    def test_zero_separation_raises(self):
        with self.assertRaises(ValueError):
            check_distance_tolerance(1.0, 0.0)

    def test_non_numeric_separation_raises(self):
        with self.assertRaises(ValueError):
            check_distance_tolerance("1 m", 1.0)


class TestFrequencyTolerance(unittest.TestCase):
    def test_exact_tuning_is_within(self):
        result = check_frequency_tolerance(1.0e6, 1.0e6)
        self.assertTrue(result["within"])

    def test_allowed_band_is_a_fraction_of_nominal(self):
        result = check_frequency_tolerance(1.0e6, 1.0e6)
        self.assertAlmostEqual(result["allowed"], 1.0e6 * FREQUENCY_TOLERANCE_FRACTION)

    def test_edge_of_band_is_within(self):
        result = check_frequency_tolerance(1.0e6, 1.02e6)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["percent"], 2.0)

    def test_beyond_band_is_out_of_tolerance(self):
        self.assertFalse(check_frequency_tolerance(1.0e6, 1.05e6)["within"])

    def test_low_side_deviation_is_symmetric(self):
        self.assertFalse(check_frequency_tolerance(1.0e6, 0.95e6)["within"])

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_tolerance(0.0, 1.0)

    def test_non_finite_frequency_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_tolerance(1.0e6, float("inf"))


class TestAmplitudeTolerance(unittest.TestCase):
    def test_on_target_level_is_within(self):
        result = check_amplitude_tolerance(30.0, 30.0)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["allowed"], AMPLITUDE_TOLERANCE_DB)

    def test_level_inside_the_band_is_within(self):
        self.assertTrue(check_amplitude_tolerance(30.0, 31.5)["within"])

    def test_exact_boundary_survives_float_representation(self):
        result = check_amplitude_tolerance(30.2, 32.2)
        # the difference lands a few ULPs above the exact 2 dB allowance
        self.assertGreater(result["deviation"], AMPLITUDE_TOLERANCE_DB)
        self.assertTrue(result["within"])

    def test_level_beyond_the_band_is_out_of_tolerance(self):
        self.assertFalse(check_amplitude_tolerance(30.0, 33.0)["within"])

    def test_low_side_level_is_symmetric(self):
        self.assertFalse(check_amplitude_tolerance(30.0, 27.0)["within"])

    def test_negative_target_level_is_accepted(self):
        self.assertTrue(check_amplitude_tolerance(-6.0, -5.0)["within"])

    def test_tighter_allowance_can_be_imposed(self):
        self.assertFalse(check_amplitude_tolerance(30.0, 31.0, allowed_db=0.5)["within"])

    def test_zero_allowance_raises(self):
        with self.assertRaises(ValueError):
            check_amplitude_tolerance(30.0, 30.0, allowed_db=0.0)

    def test_non_numeric_level_raises(self):
        with self.assertRaises(ValueError):
            check_amplitude_tolerance(30.0, None)


class TestBandSelection(unittest.TestCase):
    def test_band_table_is_contiguous_and_ascending(self):
        for index in range(1, len(MEASUREMENT_BANDS)):
            self.assertAlmostEqual(
                MEASUREMENT_BANDS[index][0], MEASUREMENT_BANDS[index - 1][1]
            )

    def test_low_frequency_band(self):
        band = select_band(100.0)
        self.assertAlmostEqual(band["resolution_bandwidth_hz"], 10.0)
        self.assertAlmostEqual(band["min_dwell_s"], 1.0)

    def test_radio_frequency_band(self):
        band = select_band(1.0e8)
        self.assertAlmostEqual(band["resolution_bandwidth_hz"], 1.0e5)
        self.assertAlmostEqual(band["max_step_fraction"], 0.005)

    def test_microwave_band(self):
        band = select_band(1.2e10)
        self.assertAlmostEqual(band["resolution_bandwidth_hz"], 1.0e6)

    def test_shared_edge_resolves_to_the_lower_band(self):
        self.assertAlmostEqual(select_band(1.0e3)["resolution_bandwidth_hz"], 10.0)

    def test_below_range_raises(self):
        with self.assertRaises(ValueError):
            select_band(10.0)

    def test_above_range_raises(self):
        with self.assertRaises(ValueError):
            select_band(2.0e10)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            select_band(0.0)


class TestScanStep(unittest.TestCase):
    def test_fine_step_is_within(self):
        step = check_scan_step(1.0e8, 1.004e8)
        self.assertTrue(step["within"])
        self.assertAlmostEqual(step["allowed_hz"], 5.0e5)

    def test_step_at_the_allowance_is_within(self):
        self.assertTrue(check_scan_step(1.0e8, 1.005e8)["within"])

    def test_coarse_step_is_out_of_tolerance(self):
        self.assertFalse(check_scan_step(1.0e8, 1.05e8)["within"])

    def test_low_band_allowance_is_looser_in_fraction(self):
        step = check_scan_step(100.0, 100.5)
        self.assertAlmostEqual(step["allowed_hz"], 1.0)
        self.assertTrue(step["within"])

    def test_backward_step_raises(self):
        with self.assertRaises(ValueError):
            check_scan_step(1.0e8, 0.9e8)

    def test_repeated_frequency_raises(self):
        with self.assertRaises(ValueError):
            check_scan_step(1.0e8, 1.0e8)


class TestDwellTime(unittest.TestCase):
    def test_sufficient_dwell_is_within(self):
        self.assertTrue(check_dwell_time(1.0e8, 0.5)["within"])

    def test_dwell_exactly_at_the_requirement_is_within(self):
        result = check_dwell_time(1.0e8, 0.2)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["required_s"], 0.2)

    def test_short_dwell_is_flagged(self):
        self.assertFalse(check_dwell_time(1.0e8, 0.05)["within"])

    def test_low_band_requires_a_longer_dwell(self):
        self.assertFalse(check_dwell_time(100.0, 0.5)["within"])

    def test_zero_dwell_raises(self):
        with self.assertRaises(ValueError):
            check_dwell_time(1.0e8, 0.0)


class TestUncertainty(unittest.TestCase):
    def test_root_sum_square_of_two_terms(self):
        self.assertAlmostEqual(measurement_uncertainty_rss([3.0, 4.0]), 5.0)

    def test_single_term_returns_itself(self):
        self.assertAlmostEqual(measurement_uncertainty_rss([1.5]), 1.5)

    def test_zero_terms_are_allowed_inside_the_list(self):
        self.assertAlmostEqual(measurement_uncertainty_rss([0.0, 2.0]), 2.0)

    def test_empty_term_list_raises(self):
        with self.assertRaises(ValueError):
            measurement_uncertainty_rss([])

    def test_negative_term_raises(self):
        with self.assertRaises(ValueError):
            measurement_uncertainty_rss([1.0, -1.0])

    def test_string_terms_raise(self):
        with self.assertRaises(ValueError):
            measurement_uncertainty_rss("3.0")

    def test_budget_met_exactly_is_within(self):
        result = check_uncertainty_budget([3.0, 4.0], 5.0)
        self.assertTrue(result["within"])
        self.assertAlmostEqual(result["margin_db"], 0.0)

    def test_budget_exceeded_is_flagged(self):
        result = check_uncertainty_budget([3.0, 4.0], 4.0)
        self.assertFalse(result["within"])
        self.assertAlmostEqual(result["margin_db"], -1.0)

    def test_zero_budget_raises(self):
        with self.assertRaises(ValueError):
            check_uncertainty_budget([1.0], 0.0)


class TestMeasurementPoint(unittest.TestCase):
    def test_clean_point_has_no_finding(self):
        record = evaluate_measurement_point(good_point())
        self.assertTrue(record["within_tolerance"])
        self.assertEqual(record["findings"], [])
        self.assertEqual(
            sorted(record["checks"]), ["amplitude", "distance", "dwell", "frequency"]
        )

    def test_mistuned_point_is_flagged(self):
        point = good_point(actual_frequency_hz=1.05e8)
        codes = [f["code"] for f in evaluate_measurement_point(point)["findings"]]
        self.assertIn("frequency-out-of-tolerance", codes)

    def test_misplaced_antenna_is_flagged(self):
        point = good_point(actual_distance_m=1.2)
        codes = [f["code"] for f in evaluate_measurement_point(point)["findings"]]
        self.assertIn("separation-out-of-tolerance", codes)

    def test_level_off_target_is_flagged(self):
        point = good_point(actual_amplitude_db=34.0)
        codes = [f["code"] for f in evaluate_measurement_point(point)["findings"]]
        self.assertIn("amplitude-out-of-tolerance", codes)

    def test_short_dwell_is_flagged(self):
        point = good_point(dwell_s=0.01)
        codes = [f["code"] for f in evaluate_measurement_point(point)["findings"]]
        self.assertIn("dwell-too-short", codes)

    def test_conducted_point_without_separation_is_accepted(self):
        point = good_point()
        del point["nominal_distance_m"]
        del point["actual_distance_m"]
        record = evaluate_measurement_point(point)
        self.assertTrue(record["within_tolerance"])
        self.assertNotIn("distance", record["checks"])

    def test_emission_point_without_amplitude_target_is_accepted(self):
        point = good_point()
        del point["target_amplitude_db"]
        del point["actual_amplitude_db"]
        self.assertTrue(evaluate_measurement_point(point)["within_tolerance"])

    def test_half_declared_separation_raises(self):
        point = good_point()
        del point["actual_distance_m"]
        with self.assertRaises(ValueError):
            evaluate_measurement_point(point)

    def test_half_declared_amplitude_raises(self):
        point = good_point()
        del point["actual_amplitude_db"]
        with self.assertRaises(ValueError):
            evaluate_measurement_point(point)

    def test_half_declared_frequency_raises(self):
        point = good_point()
        del point["actual_frequency_hz"]
        with self.assertRaises(ValueError):
            evaluate_measurement_point(point)

    def test_point_without_any_toleranced_quantity_raises(self):
        with self.assertRaises(ValueError):
            evaluate_measurement_point({"id": "P-empty"})

    def test_dwell_without_frequency_raises(self):
        point = {
            "id": "P-conducted",
            "target_amplitude_db": 30.0,
            "actual_amplitude_db": 30.0,
            "dwell_s": 0.5,
        }
        with self.assertRaises(ValueError):
            evaluate_measurement_point(point)

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            evaluate_measurement_point(good_point(polarisation="vertical"))

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_measurement_point(good_point(id="   "))

    def test_missing_identifier_raises(self):
        point = good_point()
        del point["id"]
        with self.assertRaises(ValueError):
            evaluate_measurement_point(point)

    def test_point_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_measurement_point(["P-100MHz"])


class TestCampaign(unittest.TestCase):
    def test_clean_sweep_is_accepted(self):
        result = assess_measurement_campaign(sweep())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], "within-tolerance")
        self.assertEqual(result["point_count"], 3)
        self.assertEqual(result["step_count"], 2)
        self.assertAlmostEqual(result["conforming_fraction"], 1.0)

    def test_coarse_step_between_points_is_flagged(self):
        points = sweep()
        points[2]["nominal_frequency_hz"] = 1.1e8
        points[2]["actual_frequency_hz"] = 1.1e8
        codes = [f["code"] for f in assess_measurement_campaign(points)["findings"]]
        self.assertIn("scan-step-too-coarse", codes)

    def test_non_ascending_sweep_is_flagged(self):
        points = sweep()
        points[2]["nominal_frequency_hz"] = 1.001e8
        points[2]["actual_frequency_hz"] = 1.001e8
        codes = [f["code"] for f in assess_measurement_campaign(points)["findings"]]
        self.assertIn("sweep-not-ascending", codes)

    def test_point_finding_propagates_to_the_campaign(self):
        points = sweep()
        points[1]["actual_distance_m"] = 1.4
        result = assess_measurement_campaign(points)
        self.assertFalse(result["accepted"])
        self.assertAlmostEqual(result["conforming_fraction"], 2.0 / 3.0)

    def test_uncertainty_budget_is_assessed_when_supplied(self):
        result = assess_measurement_campaign(
            sweep(), uncertainty_terms=[3.0, 4.0], uncertainty_budget_db=5.0
        )
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(result["uncertainty"]["combined_db"], 5.0)

    def test_uncertainty_over_budget_is_flagged(self):
        result = assess_measurement_campaign(
            sweep(), uncertainty_terms=[3.0, 4.0], uncertainty_budget_db=4.0
        )
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("uncertainty-over-budget", codes)

    def test_uncertainty_terms_without_budget_raise(self):
        with self.assertRaises(ValueError):
            assess_measurement_campaign(sweep(), uncertainty_terms=[3.0])

    def test_absent_uncertainty_block_is_none(self):
        self.assertIsNone(assess_measurement_campaign(sweep())["uncertainty"])

    def test_duplicate_point_identifier_raises(self):
        points = sweep()
        points[2]["id"] = "P-1"
        with self.assertRaises(ValueError):
            assess_measurement_campaign(points)

    def test_empty_run_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_campaign([])

    def test_string_run_raises(self):
        with self.assertRaises(ValueError):
            assess_measurement_campaign("P-1")

    def test_findings_carry_code_subject_and_detail(self):
        points = sweep()
        points[1]["actual_amplitude_db"] = 40.0
        for finding in assess_measurement_campaign(points)["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


if __name__ == "__main__":
    unittest.main()

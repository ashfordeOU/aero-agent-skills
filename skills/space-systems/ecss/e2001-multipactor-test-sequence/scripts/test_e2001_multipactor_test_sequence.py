#!/usr/bin/env python3
"""Gate 3 contract test for e2001-multipactor-test-sequence (offline, stdlib)."""

import math
import unittest

from e2001_multipactor_test_sequence_logic import (
    ABS_TOL,
    REL_TOL,
    UNIT_MAGNITUDE,
    check_absolute_limits,
    check_passivity,
    compare_to_reference,
    evaluate_pre_run_sweep,
    evaluate_sweep_point,
    insertion_loss_db,
    return_loss_db,
    validate_frequency_grid,
    vswr_from_reflection,
)

BAND_LOW = 10.0e9
BAND_HIGH = 12.0e9
LIMITS = {"min_return_loss_db": 20.0, "max_insertion_loss_db": 0.5}


def sweep_point(frequency_hz, reflection=0.05, transmission=0.99, **overrides):
    point = {
        "frequency_hz": frequency_hz,
        "reflection_magnitude": reflection,
        "transmission_magnitude": transmission,
        "reference_return_loss_db": return_loss_db(reflection),
        "reference_insertion_loss_db": insertion_loss_db(transmission),
    }
    point.update(overrides)
    return point


def good_record(**overrides):
    record = {
        "sweep": [
            sweep_point(10.0e9),
            sweep_point(10.5e9),
            sweep_point(11.0e9),
            sweep_point(11.5e9),
            sweep_point(12.0e9),
        ],
        "band_low_hz": BAND_LOW,
        "band_high_hz": BAND_HIGH,
        "min_points": 5,
        "tolerance_db": 0.5,
        "limits": dict(LIMITS),
    }
    record.update(overrides)
    return record


class TestFrequencyGrid(unittest.TestCase):
    def test_covering_grid_is_compliant(self):
        grid = validate_frequency_grid(
            [10.0e9, 11.0e9, 12.0e9], BAND_LOW, BAND_HIGH, 3
        )
        self.assertTrue(grid["compliant"])
        self.assertTrue(grid["covers_band"])

    def test_in_band_point_count_is_reported(self):
        grid = validate_frequency_grid(
            [9.0e9, 10.0e9, 11.0e9, 12.0e9, 13.0e9], BAND_LOW, BAND_HIGH, 3
        )
        self.assertEqual(grid["in_band_points"], 3)

    def test_grid_starting_inside_the_band_is_a_finding(self):
        grid = validate_frequency_grid(
            [10.5e9, 11.0e9, 12.0e9], BAND_LOW, BAND_HIGH, 3
        )
        self.assertFalse(grid["compliant"])
        self.assertIn("above the declared band edge", grid["findings"][0])

    def test_grid_ending_inside_the_band_is_a_finding(self):
        grid = validate_frequency_grid(
            [10.0e9, 10.5e9, 11.0e9], BAND_LOW, BAND_HIGH, 3
        )
        self.assertFalse(grid["compliant"])
        self.assertIn("below the declared band edge", grid["findings"][0])

    def test_sparse_grid_is_a_finding_even_when_it_covers_the_band(self):
        grid = validate_frequency_grid([10.0e9, 12.0e9], BAND_LOW, BAND_HIGH, 5)
        self.assertTrue(grid["covers_band"])
        self.assertFalse(grid["compliant"])
        self.assertIn("fewer than the 5 required", grid["findings"][0])

    def test_unordered_grid_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([10.0e9, 12.0e9, 11.0e9], BAND_LOW, BAND_HIGH, 3)

    def test_duplicate_point_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([10.0e9, 10.0e9, 12.0e9], BAND_LOW, BAND_HIGH, 3)

    def test_empty_grid_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([], BAND_LOW, BAND_HIGH, 3)

    def test_non_numeric_point_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([10.0e9, "11 GHz"], BAND_LOW, BAND_HIGH, 2)

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([10.0e9, 12.0e9], BAND_HIGH, BAND_LOW, 2)

    def test_min_points_below_two_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([10.0e9, 12.0e9], BAND_LOW, BAND_HIGH, 1)

    def test_boolean_min_points_raises(self):
        with self.assertRaises(ValueError):
            validate_frequency_grid([10.0e9, 12.0e9], BAND_LOW, BAND_HIGH, True)


class TestReturnLoss(unittest.TestCase):
    def test_tenth_magnitude_is_twenty_db(self):
        self.assertAlmostEqual(return_loss_db(0.1), 20.0, places=9)

    def test_hundredth_magnitude_is_forty_db(self):
        self.assertAlmostEqual(return_loss_db(0.01), 40.0, places=9)

    def test_matched_port_has_unbounded_return_loss(self):
        self.assertTrue(math.isinf(return_loss_db(0.0)))

    def test_total_reflection_is_zero_db(self):
        self.assertAlmostEqual(return_loss_db(1.0), 0.0, places=12)

    def test_magnitude_a_hair_above_unity_is_absorbed_not_rejected(self):
        self.assertAlmostEqual(return_loss_db(1.0 + 1e-13), 0.0, places=12)

    def test_magnitude_clearly_above_unity_raises(self):
        with self.assertRaises(ValueError):
            return_loss_db(1.2)

    def test_negative_magnitude_raises(self):
        with self.assertRaises(ValueError):
            return_loss_db(-0.1)

    def test_non_numeric_magnitude_raises(self):
        with self.assertRaises(ValueError):
            return_loss_db("0.1")

    def test_non_finite_magnitude_raises(self):
        with self.assertRaises(ValueError):
            return_loss_db(float("nan"))


class TestStandingWaveRatio(unittest.TestCase):
    def test_matched_port_is_unity(self):
        self.assertAlmostEqual(vswr_from_reflection(0.0), 1.0, places=12)

    def test_one_third_magnitude_is_two(self):
        self.assertAlmostEqual(vswr_from_reflection(1.0 / 3.0), 2.0, places=9)

    def test_total_reflection_is_unbounded(self):
        self.assertTrue(math.isinf(vswr_from_reflection(1.0)))

    def test_ratio_grows_with_reflection(self):
        self.assertLess(vswr_from_reflection(0.05), vswr_from_reflection(0.2))

    def test_negative_magnitude_raises(self):
        with self.assertRaises(ValueError):
            vswr_from_reflection(-0.01)


class TestInsertionLoss(unittest.TestCase):
    def test_lossless_path_is_zero_db(self):
        self.assertAlmostEqual(insertion_loss_db(1.0), 0.0, places=12)

    def test_half_magnitude_is_about_six_db(self):
        self.assertAlmostEqual(insertion_loss_db(0.5), 6.0206, places=4)

    def test_blocked_path_is_unbounded(self):
        self.assertTrue(math.isinf(insertion_loss_db(0.0)))

    def test_transmission_above_unity_raises(self):
        with self.assertRaises(ValueError):
            insertion_loss_db(1.4)

    def test_boolean_transmission_raises(self):
        with self.assertRaises(ValueError):
            insertion_loss_db(True)


class TestPassivity(unittest.TestCase):
    def test_lossy_point_is_passive(self):
        result = check_passivity(0.1, 0.9)
        self.assertTrue(result["passive"])
        self.assertAlmostEqual(result["power_sum"], 0.82, places=12)
        self.assertAlmostEqual(result["dissipated_fraction"], 0.18, places=12)

    def test_lossless_point_summing_ulps_above_unity_is_passive(self):
        reflection = 0.025
        transmission = math.sqrt(1.0 - reflection * reflection)
        self.assertGreater(reflection ** 2 + transmission ** 2, 1.0)
        result = check_passivity(reflection, transmission)
        self.assertTrue(result["passive"])
        self.assertEqual(result["findings"], [])

    def test_non_passive_point_is_a_finding(self):
        result = check_passivity(0.5, 0.95)
        self.assertFalse(result["passive"])
        self.assertIn("above unity", result["findings"][0])

    def test_fully_reflecting_point_is_passive(self):
        result = check_passivity(1.0, 0.0)
        self.assertTrue(result["passive"])
        self.assertAlmostEqual(result["power_sum"], 1.0, places=12)

    def test_dissipated_fraction_is_never_negative(self):
        result = check_passivity(0.025, math.sqrt(1.0 - 0.025 ** 2))
        self.assertGreaterEqual(result["dissipated_fraction"], 0.0)

    def test_magnitude_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            check_passivity(0.5, 2.0)


class TestReferenceComparison(unittest.TestCase):
    def test_matching_measurement_is_within_tolerance(self):
        result = compare_to_reference(20.0, 20.1, 0.5, "return-loss")
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["deviation_db"], -0.1, places=9)

    def test_deviation_beyond_tolerance_is_a_finding(self):
        result = compare_to_reference(14.0, 20.0, 0.5, "return-loss")
        self.assertFalse(result["compliant"])
        self.assertIn("outside the", result["findings"][0])

    def test_deviation_sign_is_preserved_in_the_finding(self):
        result = compare_to_reference(26.0, 20.0, 0.5, "return-loss")
        self.assertIn("+6.0000 dB", result["findings"][0])

    def test_edge_case_difference_landing_ulps_outside_still_passes(self):
        # 20.3 - 20.0 evaluates to 0.3000000000000007 dB, physically the edge.
        self.assertGreater(20.3 - 20.0, 0.3)
        result = compare_to_reference(20.3, 20.0, 0.3, "return-loss")
        self.assertTrue(result["within_tolerance"])

    def test_two_matched_ports_both_unbounded_agree(self):
        result = compare_to_reference(math.inf, math.inf, 0.5, "return-loss")
        self.assertAlmostEqual(result["deviation_db"], 0.0, places=12)
        self.assertTrue(result["compliant"])

    def test_measured_unbounded_against_finite_reference_is_a_finding(self):
        result = compare_to_reference(math.inf, 20.0, 0.5, "return-loss")
        self.assertFalse(result["compliant"])

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ValueError):
            compare_to_reference(20.0, 20.0, 0.0)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            compare_to_reference(20.0, 20.0, -0.5)

    def test_non_numeric_reference_raises(self):
        with self.assertRaises(ValueError):
            compare_to_reference(20.0, "20 dB", 0.5)


class TestAbsoluteLimits(unittest.TestCase):
    def test_comfortable_point_is_compliant(self):
        result = check_absolute_limits(26.0, 0.2, LIMITS)
        self.assertTrue(result["compliant"])

    def test_point_on_both_limits_is_compliant(self):
        result = check_absolute_limits(20.0, 0.5, LIMITS)
        self.assertTrue(result["compliant"])

    def test_return_loss_below_the_minimum_is_a_finding(self):
        result = check_absolute_limits(12.0, 0.2, LIMITS)
        self.assertFalse(result["return_loss_ok"])
        self.assertIn("below the minimum", result["findings"][0])

    def test_insertion_loss_above_the_maximum_is_a_finding(self):
        result = check_absolute_limits(26.0, 1.4, LIMITS)
        self.assertFalse(result["insertion_loss_ok"])
        self.assertIn("above the maximum", result["findings"][0])

    def test_both_limits_can_fail_together(self):
        result = check_absolute_limits(12.0, 1.4, LIMITS)
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_limit_key_raises(self):
        with self.assertRaises(ValueError):
            check_absolute_limits(26.0, 0.2, {"min_return_loss_db": 20.0})

    def test_non_mapping_limits_raises(self):
        with self.assertRaises(ValueError):
            check_absolute_limits(26.0, 0.2, [20.0, 0.5])

    def test_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            check_absolute_limits(
                26.0, 0.2, {"min_return_loss_db": -20.0, "max_insertion_loss_db": 0.5}
            )


class TestSweepPoint(unittest.TestCase):
    def test_point_reproducing_the_reference_is_compliant(self):
        result = evaluate_sweep_point(sweep_point(11.0e9), 0.5, LIMITS)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["return_loss_db"], 26.0206, places=4)

    def test_standing_wave_ratio_is_reported(self):
        result = evaluate_sweep_point(sweep_point(11.0e9), 0.5, LIMITS)
        self.assertAlmostEqual(result["vswr"], 1.10526, places=4)

    def test_mis_mated_interface_shows_as_a_return_loss_deviation(self):
        point = sweep_point(11.0e9, reflection=0.05)
        point["reflection_magnitude"] = 0.3
        result = evaluate_sweep_point(point, 0.5, LIMITS)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("return-loss" in f for f in result["findings"]))

    def test_findings_carry_the_frequency(self):
        point = sweep_point(11.0e9)
        point["reflection_magnitude"] = 0.3
        result = evaluate_sweep_point(point, 0.5, LIMITS)
        self.assertTrue(result["findings"][0].startswith("1.1e+10 Hz:"))

    def test_lossy_joint_shows_as_an_insertion_loss_deviation(self):
        point = sweep_point(11.0e9)
        point["transmission_magnitude"] = 0.8
        result = evaluate_sweep_point(point, 0.5, LIMITS)
        self.assertTrue(any("insertion-loss" in f for f in result["findings"]))

    def test_missing_point_key_raises(self):
        point = sweep_point(11.0e9)
        del point["reference_return_loss_db"]
        with self.assertRaises(ValueError):
            evaluate_sweep_point(point, 0.5, LIMITS)

    def test_non_mapping_point_raises(self):
        with self.assertRaises(ValueError):
            evaluate_sweep_point([11.0e9], 0.5, LIMITS)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            evaluate_sweep_point(sweep_point(0.0), 0.5, LIMITS)


class TestPreRunSweep(unittest.TestCase):
    def test_good_sweep_is_cleared_to_run(self):
        result = evaluate_pre_run_sweep(good_record())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "CLEARED-TO-RUN")
        self.assertEqual(result["failing_points"], 0)
        self.assertIsNone(result["worst_point_hz"])

    def test_every_point_is_evaluated(self):
        result = evaluate_pre_run_sweep(good_record())
        self.assertEqual(len(result["points"]), 5)

    def test_one_bad_point_holds_the_run(self):
        record = good_record()
        record["sweep"][2]["reflection_magnitude"] = 0.4
        result = evaluate_pre_run_sweep(record)
        self.assertEqual(result["verdict"], "HOLD-BEFORE-RUN")
        self.assertEqual(result["failing_points"], 1)
        self.assertAlmostEqual(result["worst_point_hz"], 11.0e9, places=3)

    def test_short_grid_holds_the_run_on_its_own(self):
        record = good_record(min_points=9)
        result = evaluate_pre_run_sweep(record)
        self.assertEqual(result["verdict"], "HOLD-BEFORE-RUN")
        self.assertFalse(record["sweep"] == [])

    def test_worst_point_is_the_lowest_return_loss(self):
        record = good_record()
        record["sweep"][1]["reflection_magnitude"] = 0.3
        record["sweep"][3]["reflection_magnitude"] = 0.5
        result = evaluate_pre_run_sweep(record)
        self.assertAlmostEqual(result["worst_point_hz"], 11.5e9, places=3)

    def test_empty_sweep_raises(self):
        with self.assertRaises(ValueError):
            evaluate_pre_run_sweep(good_record(sweep=[]))

    def test_missing_record_key_raises(self):
        record = good_record()
        del record["tolerance_db"]
        with self.assertRaises(ValueError):
            evaluate_pre_run_sweep(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            evaluate_pre_run_sweep("sweep")

    def test_constants_are_sane(self):
        self.assertAlmostEqual(UNIT_MAGNITUDE, 1.0, places=12)
        self.assertLess(REL_TOL, 1e-6)
        self.assertGreater(REL_TOL, 0.0)
        self.assertLess(ABS_TOL, 1e-9)
        self.assertGreater(ABS_TOL, 0.0)


if __name__ == "__main__":
    unittest.main()

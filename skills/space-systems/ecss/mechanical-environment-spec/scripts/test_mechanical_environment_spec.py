"""
Gate 3 contract tests — mechanical-environment-spec
ECSS-E-ST-32C clauses 4.2.3-4.2.4

Run: python3 test_mechanical_environment_spec.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from mechanical_environment_spec_logic import (
    compute_grms_from_psd,
    check_random_vibration_coverage,
    check_srs_coverage,
    interpolate_srs_acceleration,
    check_audible_noise_spec,
    compute_overall_spl,
    check_human_vibration_spec,
    check_microgravity_spec,
    check_environment_completeness,
    SpecificationError,
)


class TestGrmsFromPsd(unittest.TestCase):

    def test_flat_psd_grms(self):
        # flat 0.04 g²/Hz over 20-2000 Hz → Grms = sqrt(0.04 * 1980)
        bps = [(20.0, 0.04), (2000.0, 0.04)]
        expected = math.sqrt(0.04 * 1980.0)
        self.assertAlmostEqual(compute_grms_from_psd(bps), expected, places=6)

    def test_rising_slope_psd_grms(self):
        # slope m=1 segment (100, 0.01) → (400, 0.04)
        # area = (0.04*400 - 0.01*100) / (1+1) = 15/2 = 7.5
        bps = [(100.0, 0.01), (400.0, 0.04)]
        expected = math.sqrt(7.5)
        self.assertAlmostEqual(compute_grms_from_psd(bps), expected, places=6)

    def test_minus_one_slope_psd_grms(self):
        # segment where m = -1: area = w1*f1*ln(f2/f1)
        # build breakpoints with slope -1: w2 = w1*(f2/f1)^(-1) → w2 = w1*f1/f2
        f1, w1 = 100.0, 0.04
        f2 = 400.0
        w2 = w1 * f1 / f2  # slope = -1 by construction
        bps = [(f1, w1), (f2, w2)]
        expected_area = w1 * f1 * math.log(f2 / f1)
        expected = math.sqrt(expected_area)
        self.assertAlmostEqual(compute_grms_from_psd(bps), expected, places=6)

    def test_single_breakpoint_raises(self):
        with self.assertRaises(SpecificationError):
            compute_grms_from_psd([(100.0, 0.04)])

    def test_zero_frequency_raises(self):
        with self.assertRaises(SpecificationError):
            compute_grms_from_psd([(0.0, 0.04), (100.0, 0.04)])

    def test_non_ascending_frequencies_raises(self):
        with self.assertRaises(SpecificationError):
            compute_grms_from_psd([(200.0, 0.04), (100.0, 0.04)])

    def test_zero_psd_level_raises(self):
        with self.assertRaises(SpecificationError):
            compute_grms_from_psd([(20.0, 0.0), (2000.0, 0.04)])


class TestRandomVibrationCoverage(unittest.TestCase):

    def test_full_range_coverage_is_compliant(self):
        bps = [(20.0, 0.01), (500.0, 0.04), (2000.0, 0.01)]
        result = check_random_vibration_coverage(bps)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_low_end_gap_reported(self):
        bps = [(50.0, 0.04), (2000.0, 0.04)]
        result = check_random_vibration_coverage(bps)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("lower" in f or "20" in f for f in result["findings"]))

    def test_high_end_gap_reported(self):
        bps = [(20.0, 0.04), (1000.0, 0.04)]
        result = check_random_vibration_coverage(bps)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("2000" in f for f in result["findings"]))

    def test_both_ends_gap_reported(self):
        bps = [(50.0, 0.04), (1000.0, 0.04)]
        result = check_random_vibration_coverage(bps)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)


class TestSrsCoverage(unittest.TestCase):

    def test_full_range_compliant(self):
        bps = [(10.0, 5.0), (100.0, 500.0), (10000.0, 50.0)]
        result = check_srs_coverage(bps)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["q_factor"], 10)

    def test_narrow_range_reported(self):
        bps = [(100.0, 100.0), (5000.0, 200.0)]
        result = check_srs_coverage(bps)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_custom_q_factor_stored(self):
        bps = [(10.0, 5.0), (10000.0, 50.0)]
        result = check_srs_coverage(bps, q=50)
        self.assertEqual(result["q_factor"], 50)

    def test_zero_q_raises(self):
        bps = [(10.0, 5.0), (10000.0, 50.0)]
        with self.assertRaises(SpecificationError):
            check_srs_coverage(bps, q=0)

    def test_negative_q_raises(self):
        bps = [(10.0, 5.0), (10000.0, 50.0)]
        with self.assertRaises(SpecificationError):
            check_srs_coverage(bps, q=-5)


class TestSrsInterpolation(unittest.TestCase):

    def test_at_lower_breakpoint(self):
        bps = [(10.0, 50.0), (100.0, 500.0)]
        self.assertAlmostEqual(interpolate_srs_acceleration(bps, 10.0), 50.0, places=6)

    def test_at_upper_breakpoint(self):
        bps = [(10.0, 50.0), (100.0, 500.0)]
        self.assertAlmostEqual(interpolate_srs_acceleration(bps, 100.0), 500.0, places=6)

    def test_log_log_midpoint_interpolation(self):
        # slope 1 on log-log: (10, 10) → (100, 100); at f=50, acc = 50
        bps = [(10.0, 10.0), (100.0, 100.0)]
        result = interpolate_srs_acceleration(bps, 50.0)
        self.assertAlmostEqual(result, 50.0, places=5)

    def test_flat_segment_interpolation(self):
        bps = [(100.0, 200.0), (1000.0, 200.0)]
        self.assertAlmostEqual(interpolate_srs_acceleration(bps, 500.0), 200.0, places=6)

    def test_out_of_range_below_raises(self):
        bps = [(100.0, 100.0), (1000.0, 200.0)]
        with self.assertRaises(SpecificationError):
            interpolate_srs_acceleration(bps, 50.0)

    def test_out_of_range_above_raises(self):
        bps = [(100.0, 100.0), (1000.0, 200.0)]
        with self.assertRaises(SpecificationError):
            interpolate_srs_acceleration(bps, 2000.0)

    def test_three_segment_srs_midpoint(self):
        # linear on log-log across all segments: (10,10), (100,100), (1000,1000)
        bps = [(10.0, 10.0), (100.0, 100.0), (1000.0, 1000.0)]
        result = interpolate_srs_acceleration(bps, 1000.0)
        self.assertAlmostEqual(result, 1000.0, places=5)


class TestAudibleNoise(unittest.TestCase):

    def test_all_within_limit_is_compliant(self):
        levels = {63.0: 80.0, 125.0: 82.0, 250.0: 85.0, 500.0: 88.0}
        result = check_audible_noise_spec(levels, limit_db=90.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["exceedances"], [])

    def test_exceedance_reported(self):
        levels = {63.0: 80.0, 125.0: 95.0, 250.0: 85.0}
        result = check_audible_noise_spec(levels, limit_db=90.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["exceedances"]), 1)
        self.assertAlmostEqual(result["exceedances"][0]["excess_db"], 5.0, places=3)

    def test_multiple_exceedances_all_reported(self):
        levels = {63.0: 92.0, 125.0: 95.0, 250.0: 85.0}
        result = check_audible_noise_spec(levels, limit_db=90.0)
        self.assertEqual(len(result["exceedances"]), 2)

    def test_invalid_limit_raises(self):
        with self.assertRaises(SpecificationError):
            check_audible_noise_spec({63.0: 80.0}, limit_db=0.0)

    def test_negative_limit_raises(self):
        with self.assertRaises(SpecificationError):
            check_audible_noise_spec({63.0: 80.0}, limit_db=-10.0)


class TestOverallSpl(unittest.TestCase):

    def test_single_band_overall_equals_band_level(self):
        self.assertAlmostEqual(compute_overall_spl([90.0]), 90.0, places=6)

    def test_two_equal_bands_adds_three_db(self):
        result = compute_overall_spl([90.0, 90.0])
        expected = 10.0 * math.log10(2 * 10 ** 9)
        self.assertAlmostEqual(result, expected, places=5)

    def test_empty_list_raises(self):
        with self.assertRaises(SpecificationError):
            compute_overall_spl([])


class TestHumanVibration(unittest.TestCase):

    def test_frequency_in_range_is_compliant(self):
        result = check_human_vibration_spec(freq_hz=10.0, amplitude_g=0.005)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_boundary_frequencies_compliant(self):
        self.assertTrue(check_human_vibration_spec(1.0, 0.001)["compliant"])
        self.assertTrue(check_human_vibration_spec(100.0, 0.001)["compliant"])

    def test_frequency_below_range_flagged(self):
        result = check_human_vibration_spec(freq_hz=0.5, amplitude_g=0.001)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_frequency_above_range_flagged(self):
        result = check_human_vibration_spec(freq_hz=150.0, amplitude_g=0.001)
        self.assertFalse(result["compliant"])

    def test_zero_amplitude_raises(self):
        with self.assertRaises(SpecificationError):
            check_human_vibration_spec(freq_hz=10.0, amplitude_g=0.0)

    def test_negative_amplitude_raises(self):
        with self.assertRaises(SpecificationError):
            check_human_vibration_spec(freq_hz=10.0, amplitude_g=-0.005)


class TestMicrogravitySpec(unittest.TestCase):

    def test_valid_steady_state_only(self):
        result = check_microgravity_spec(steady_state_micro_g=5.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["transient_micro_g"])

    def test_valid_with_transient(self):
        result = check_microgravity_spec(steady_state_micro_g=5.0, transient_micro_g=50.0)
        self.assertTrue(result["compliant"])

    def test_zero_steady_state_flagged(self):
        result = check_microgravity_spec(steady_state_micro_g=0.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_transient_below_steady_state_flagged(self):
        result = check_microgravity_spec(steady_state_micro_g=50.0, transient_micro_g=5.0)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("transposed" in f for f in result["findings"]))

    def test_negative_steady_state_raises(self):
        with self.assertRaises(SpecificationError):
            check_microgravity_spec(steady_state_micro_g=-1.0)

    def test_values_stored_in_result(self):
        result = check_microgravity_spec(steady_state_micro_g=3.0, transient_micro_g=30.0)
        self.assertEqual(result["steady_state_micro_g"], 3.0)
        self.assertEqual(result["transient_micro_g"], 30.0)


class TestEnvironmentCompleteness(unittest.TestCase):

    def test_all_five_types_compliant(self):
        types = [
            "microgravity",
            "audible-noise",
            "human-vibration",
            "random-vibration",
            "shock-response",
        ]
        result = check_environment_completeness(types)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing"], [])

    def test_missing_shock_response(self):
        types = ["microgravity", "audible-noise", "human-vibration", "random-vibration"]
        result = check_environment_completeness(types)
        self.assertFalse(result["compliant"])
        self.assertIn("shock-response", result["missing"])

    def test_multiple_missing_types(self):
        types = ["microgravity"]
        result = check_environment_completeness(types)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["missing"]), 4)

    def test_unknown_type_raises(self):
        with self.assertRaises(SpecificationError):
            check_environment_completeness(["microgravity", "thermal-load"])

    def test_duplicate_types_handled(self):
        types = [
            "microgravity", "microgravity",
            "audible-noise", "human-vibration",
            "random-vibration", "shock-response",
        ]
        result = check_environment_completeness(types)
        self.assertTrue(result["compliant"])

    def test_empty_list_reports_all_missing(self):
        result = check_environment_completeness([])
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["missing"]), 5)


if __name__ == "__main__":
    unittest.main()

"""
Gate 3 contract tests for dynamic-sine-random-shock-test logic.
stdlib unittest only — offline, deterministic.
Run: python3 test_dynamic_sine_random_shock_test.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from dynamic_sine_random_shock_test_logic import (
    apply_notching,
    build_test_summary,
    categorize_test_level,
    categorize_test_type,
    check_notching_justification,
    check_qualification_margin,
    check_srs_compliance,
    compute_grms,
    compute_sweep_rate,
    get_random_test_duration_seconds,
    get_shock_pulse_count,
)


class TestCategorizeTestLevel(unittest.TestCase):
    def test_qualification_normalized(self):
        self.assertEqual(categorize_test_level("qualification"), "qualification")

    def test_acceptance_normalized(self):
        self.assertEqual(categorize_test_level("acceptance"), "acceptance")

    def test_proto_flight_with_hyphen(self):
        self.assertEqual(categorize_test_level("proto-flight"), "proto_flight")

    def test_proto_flight_with_space(self):
        self.assertEqual(categorize_test_level("Proto Flight"), "proto_flight")

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            categorize_test_level("development")


class TestCategorizeTestType(unittest.TestCase):
    def test_sine_sweep_normalized(self):
        self.assertEqual(categorize_test_type("sine_sweep"), "sine_sweep")

    def test_sine_sweep_with_hyphen(self):
        self.assertEqual(categorize_test_type("sine-sweep"), "sine_sweep")

    def test_random_vibration_normalized(self):
        self.assertEqual(categorize_test_type("random vibration"), "random_vibration")

    def test_shock_normalized(self):
        self.assertEqual(categorize_test_type("shock"), "shock")

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_test_type("thermal")


class TestComputeSweepRate(unittest.TestCase):
    def test_one_octave_per_minute(self):
        # 5 Hz to 10 Hz in 1 min → 1 oct/min
        rate = compute_sweep_rate(5.0, 10.0, 1.0)
        self.assertAlmostEqual(rate, 1.0, places=9)

    def test_two_octave_band_two_minutes(self):
        # 10 Hz to 40 Hz = 2 octaves; 2 min → 1 oct/min
        rate = compute_sweep_rate(10.0, 40.0, 2.0)
        self.assertAlmostEqual(rate, 1.0, places=9)

    def test_reverse_sweep_same_rate(self):
        # Sweep from high to low gives same magnitude rate
        rate = compute_sweep_rate(100.0, 5.0, 1.0)
        self.assertAlmostEqual(rate, math.log2(20.0), places=9)

    def test_zero_start_frequency_raises(self):
        with self.assertRaises(ValueError):
            compute_sweep_rate(0.0, 100.0, 1.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            compute_sweep_rate(5.0, 100.0, -1.0)

    def test_equal_frequencies_raises(self):
        with self.assertRaises(ValueError):
            compute_sweep_rate(50.0, 50.0, 1.0)


class TestApplyNotching(unittest.TestCase):
    def test_no_notching_when_response_within_limit(self):
        level, notched = apply_notching(10.0, 50.0, 30.0)
        self.assertFalse(notched)
        self.assertAlmostEqual(level, 10.0)

    def test_notching_applied_when_response_exceeds_limit(self):
        # Predicted response is 100g, limit is 50g → notch by 0.5
        level, notched = apply_notching(20.0, 50.0, 100.0)
        self.assertTrue(notched)
        self.assertAlmostEqual(level, 10.0)

    def test_notching_exact_boundary(self):
        # Predicted exactly equals limit → no notching
        level, notched = apply_notching(5.0, 40.0, 40.0)
        self.assertFalse(notched)
        self.assertAlmostEqual(level, 5.0)

    def test_zero_input_raises(self):
        with self.assertRaises(ValueError):
            apply_notching(0.0, 50.0, 30.0)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            apply_notching(10.0, 0.0, 30.0)

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            apply_notching(10.0, 50.0, 0.0)


class TestComputeGrms(unittest.TestCase):
    def test_single_flat_segment(self):
        # PSD = 1.0 g²/Hz from 20 to 20+1 Hz → Grms = sqrt(1*1) = 1.0
        grms = compute_grms([(20.0, 21.0, 1.0)])
        self.assertAlmostEqual(grms, 1.0, places=9)

    def test_two_segments(self):
        # 0.04 g²/Hz over 20 Hz band + 0.04 g²/Hz over 5 Hz band
        # mean_square = 0.04*20 + 0.04*5 = 0.8 + 0.2 = 1.0 → Grms = 1.0
        grms = compute_grms([(20.0, 40.0, 0.04), (40.0, 45.0, 0.04)])
        self.assertAlmostEqual(grms, 1.0, places=9)

    def test_wider_band_higher_grms(self):
        narrow = compute_grms([(20.0, 30.0, 0.1)])
        wide = compute_grms([(20.0, 120.0, 0.1)])
        self.assertGreater(wide, narrow)

    def test_empty_segments_raises(self):
        with self.assertRaises(ValueError):
            compute_grms([])

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            compute_grms([(-1.0, 10.0, 0.1)])

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            compute_grms([(100.0, 10.0, 0.1)])


class TestCheckSrsCompliance(unittest.TestCase):
    def test_response_below_limit_compliant(self):
        compliant, ratio = check_srs_compliance(80.0, 100.0)
        self.assertTrue(compliant)
        self.assertAlmostEqual(ratio, 0.8)

    def test_response_at_limit_compliant(self):
        compliant, ratio = check_srs_compliance(100.0, 100.0)
        self.assertTrue(compliant)
        self.assertAlmostEqual(ratio, 1.0)

    def test_response_above_limit_not_compliant(self):
        compliant, ratio = check_srs_compliance(150.0, 100.0)
        self.assertFalse(compliant)
        self.assertAlmostEqual(ratio, 1.5)

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            check_srs_compliance(50.0, 0.0)

    def test_negative_response_raises(self):
        with self.assertRaises(ValueError):
            check_srs_compliance(-10.0, 100.0)


class TestCheckQualificationMargin(unittest.TestCase):
    def test_six_db_margin_passes(self):
        # qual = 2*accept → 6.02 dB margin; min = 6 dB
        passes, db = check_qualification_margin(20.0, 10.0, 6.0)
        self.assertTrue(passes)
        self.assertAlmostEqual(db, 20.0 * math.log10(2.0), places=6)

    def test_insufficient_margin_fails(self):
        # qual = 1.1*accept → ~0.83 dB; min = 6 dB → fail
        passes, db = check_qualification_margin(11.0, 10.0, 6.0)
        self.assertFalse(passes)

    def test_zero_accept_level_raises(self):
        with self.assertRaises(ValueError):
            check_qualification_margin(20.0, 0.0, 6.0)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            check_qualification_margin(20.0, 10.0, -1.0)


class TestGetRandomTestDuration(unittest.TestCase):
    def test_qualification_is_120_seconds(self):
        self.assertEqual(get_random_test_duration_seconds("qualification"), 120)

    def test_acceptance_is_60_seconds(self):
        self.assertEqual(get_random_test_duration_seconds("acceptance"), 60)

    def test_proto_flight_is_60_seconds(self):
        self.assertEqual(get_random_test_duration_seconds("proto-flight"), 60)

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            get_random_test_duration_seconds("flight")


class TestGetShockPulseCount(unittest.TestCase):
    def test_qualification_three_pulses(self):
        self.assertEqual(get_shock_pulse_count("qualification"), 3)

    def test_acceptance_two_pulses(self):
        self.assertEqual(get_shock_pulse_count("acceptance"), 2)

    def test_proto_flight_three_pulses(self):
        self.assertEqual(get_shock_pulse_count("proto_flight"), 3)


class TestCheckNotchingJustification(unittest.TestCase):
    def test_notching_without_justification_is_finding(self):
        compliant, finding = check_notching_justification(True, None)
        self.assertFalse(compliant)
        self.assertIsNotNone(finding)

    def test_notching_with_empty_string_is_finding(self):
        compliant, finding = check_notching_justification(True, "")
        self.assertFalse(compliant)
        self.assertIsNotNone(finding)

    def test_notching_with_justification_is_compliant(self):
        compliant, finding = check_notching_justification(
            True, "Response limit from coupled loads analysis"
        )
        self.assertTrue(compliant)
        self.assertIsNone(finding)

    def test_no_notching_no_justification_is_compliant(self):
        compliant, finding = check_notching_justification(False, None)
        self.assertTrue(compliant)
        self.assertIsNone(finding)


class TestBuildTestSummary(unittest.TestCase):
    def test_valid_summary_fields(self):
        summary = build_test_summary("random_vibration", "qualification", ["X", "Y", "Z"], True)
        self.assertEqual(summary["test_type"], "random_vibration")
        self.assertEqual(summary["test_level"], "qualification")
        self.assertEqual(summary["axes"], ("X", "Y", "Z"))
        self.assertTrue(summary["notching_applied"])

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            build_test_summary("acoustic", "qualification", ["X"], False)

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            build_test_summary("shock", "development", ["X"], False)

    def test_empty_axes_raises(self):
        with self.assertRaises(ValueError):
            build_test_summary("shock", "acceptance", [], False)

    def test_notching_flag_stored_as_bool(self):
        summary = build_test_summary("sine_sweep", "acceptance", ["Z"], 0)
        self.assertIs(summary["notching_applied"], False)


if __name__ == "__main__":
    unittest.main()

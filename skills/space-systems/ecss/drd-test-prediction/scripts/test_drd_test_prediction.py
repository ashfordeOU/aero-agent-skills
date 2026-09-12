import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from drd_test_prediction_logic import (
    TestCase,
    BaselinePrediction,
    InstrumentRange,
    validate_test_case,
    scale_prediction,
    compute_abort_threshold,
    check_abort_threshold,
    check_instrument_range,
    compute_correlation_band,
    build_test_prediction,
    LOAD_FACTOR_MAX,
    DEFAULT_ABORT_MARGIN,
    DEFAULT_CORRELATION_BAND_PCT,
)


class TestValidateTestCase(unittest.TestCase):

    def test_valid_case_no_errors(self):
        tc = TestCase("TC-01", 1.25, "Z")
        self.assertEqual(validate_test_case(tc), [])

    def test_zero_load_factor_rejected(self):
        tc = TestCase("TC-02", 0.0, "X")
        codes = [e.code for e in validate_test_case(tc)]
        self.assertIn("INVALID_LOAD_FACTOR", codes)

    def test_negative_load_factor_rejected(self):
        tc = TestCase("TC-03", -0.5, "Y")
        codes = [e.code for e in validate_test_case(tc)]
        self.assertIn("INVALID_LOAD_FACTOR", codes)

    def test_load_factor_exceeds_max_rejected(self):
        tc = TestCase("TC-04", LOAD_FACTOR_MAX + 0.01, "Z")
        codes = [e.code for e in validate_test_case(tc)]
        self.assertIn("LOAD_FACTOR_EXCEEDS_MAX", codes)

    def test_load_factor_at_max_accepted(self):
        tc = TestCase("TC-05", LOAD_FACTOR_MAX, "axial")
        self.assertEqual(validate_test_case(tc), [])

    def test_invalid_direction_rejected(self):
        tc = TestCase("TC-06", 1.0, "diagonal")
        codes = [e.code for e in validate_test_case(tc)]
        self.assertIn("INVALID_DIRECTION", codes)

    def test_valid_lateral_direction(self):
        tc = TestCase("TC-07", 1.5, "lateral")
        self.assertEqual(validate_test_case(tc), [])

    def test_valid_random_direction(self):
        tc = TestCase("TC-08", 1.0, "random")
        self.assertEqual(validate_test_case(tc), [])


class TestScalePrediction(unittest.TestCase):

    def test_unit_factor_returns_base_value(self):
        self.assertAlmostEqual(scale_prediction(100.0, 1.0), 100.0)

    def test_zero_factor_returns_zero(self):
        self.assertAlmostEqual(scale_prediction(50.0, 0.0), 0.0)

    def test_scale_factor_1_5(self):
        self.assertAlmostEqual(scale_prediction(200.0, 1.5), 300.0)

    def test_negative_base_value_scales_correctly(self):
        self.assertAlmostEqual(scale_prediction(-80.0, 2.0), -160.0)

    def test_negative_load_factor_raises(self):
        with self.assertRaises(ValueError):
            scale_prediction(100.0, -0.1)

    def test_small_load_factor(self):
        self.assertAlmostEqual(scale_prediction(400.0, 0.25), 100.0)


class TestAbortThreshold(unittest.TestCase):

    def test_default_margin_applied(self):
        result = compute_abort_threshold(100.0)
        self.assertAlmostEqual(result, 100.0 * DEFAULT_ABORT_MARGIN)

    def test_custom_margin(self):
        result = compute_abort_threshold(50.0, 1.5)
        self.assertAlmostEqual(result, 75.0)

    def test_margin_equal_to_one_raises(self):
        with self.assertRaises(ValueError):
            compute_abort_threshold(100.0, 1.0)

    def test_margin_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_abort_threshold(100.0, 0.9)

    def test_negative_predicted_raises(self):
        with self.assertRaises(ValueError):
            compute_abort_threshold(-10.0)

    def test_check_below_limit_passes(self):
        self.assertTrue(check_abort_threshold(90.0, 120.0))

    def test_check_at_limit_fails(self):
        # equal is NOT strictly below
        self.assertFalse(check_abort_threshold(120.0, 120.0))

    def test_check_above_limit_fails(self):
        self.assertFalse(check_abort_threshold(130.0, 120.0))

    def test_check_zero_abort_limit_raises(self):
        with self.assertRaises(ValueError):
            check_abort_threshold(10.0, 0.0)


class TestInstrumentRange(unittest.TestCase):

    def test_within_range_returns_none(self):
        ir = InstrumentRange("P1", "displacement_mm", 50.0)
        self.assertIsNone(check_instrument_range(40.0, ir))

    def test_at_range_limit_returns_none(self):
        ir = InstrumentRange("P2", "force_N", 1000.0)
        self.assertIsNone(check_instrument_range(1000.0, ir))

    def test_overrange_returns_error(self):
        ir = InstrumentRange("P3", "force_N", 1000.0)
        err = check_instrument_range(1200.0, ir)
        self.assertIsNotNone(err)
        self.assertEqual(err.code, "INSTRUMENT_OVERRANGE")

    def test_overrange_message_contains_point_id(self):
        ir = InstrumentRange("MON-42", "stress_MPa", 300.0)
        err = check_instrument_range(350.0, ir)
        self.assertIn("MON-42", err.message)


class TestCorrelationBand(unittest.TestCase):

    def test_10_pct_band(self):
        lo, hi = compute_correlation_band(100.0)
        self.assertAlmostEqual(lo, 90.0)
        self.assertAlmostEqual(hi, 110.0)

    def test_5_pct_band(self):
        lo, hi = compute_correlation_band(200.0, 5.0)
        self.assertAlmostEqual(lo, 190.0)
        self.assertAlmostEqual(hi, 210.0)

    def test_zero_band_pct_raises(self):
        with self.assertRaises(ValueError):
            compute_correlation_band(100.0, 0.0)

    def test_100_pct_band_raises(self):
        with self.assertRaises(ValueError):
            compute_correlation_band(100.0, 100.0)

    def test_negative_band_pct_raises(self):
        with self.assertRaises(ValueError):
            compute_correlation_band(100.0, -5.0)

    def test_negative_predicted_raises(self):
        with self.assertRaises(ValueError):
            compute_correlation_band(-10.0)

    def test_zero_predicted_gives_zero_band(self):
        lo, hi = compute_correlation_band(0.0)
        self.assertAlmostEqual(lo, 0.0)
        self.assertAlmostEqual(hi, 0.0)


class TestBuildTestPrediction(unittest.TestCase):

    def _standard_inputs(self):
        test_cases = [TestCase("TC-01", 1.25, "Z")]
        base_predictions = [
            BaselinePrediction("P1", "displacement_mm", 8.0),
            BaselinePrediction("P1", "force_N", 500.0),
        ]
        instrument_ranges = [
            InstrumentRange("P1", "displacement_mm", 20.0),
            InstrumentRange("P1", "force_N", 1000.0),
        ]
        return test_cases, base_predictions, instrument_ranges

    def test_valid_build_produces_no_errors(self):
        tc, bp, ir = self._standard_inputs()
        report = build_test_prediction(tc, bp, ir)
        self.assertEqual(report["errors"], [])

    def test_valid_build_contains_case_id(self):
        tc, bp, ir = self._standard_inputs()
        report = build_test_prediction(tc, bp, ir)
        self.assertIn("TC-01", report["results"])

    def test_result_count_matches_base_predictions(self):
        tc, bp, ir = self._standard_inputs()
        report = build_test_prediction(tc, bp, ir)
        self.assertEqual(len(report["results"]["TC-01"]), len(bp))

    def test_predicted_value_is_scaled(self):
        tc, bp, ir = self._standard_inputs()
        report = build_test_prediction(tc, bp, ir)
        pt = report["results"]["TC-01"][0]
        self.assertAlmostEqual(pt.predicted_value, 8.0 * 1.25)

    def test_abort_threshold_applied(self):
        tc, bp, ir = self._standard_inputs()
        report = build_test_prediction(tc, bp, ir)
        pt = report["results"]["TC-01"][0]
        expected = abs(8.0 * 1.25) * DEFAULT_ABORT_MARGIN
        self.assertAlmostEqual(pt.abort_threshold, expected)

    def test_correlation_band_applied(self):
        tc, bp, ir = self._standard_inputs()
        report = build_test_prediction(tc, bp, ir)
        pt = report["results"]["TC-01"][0]
        predicted = abs(8.0 * 1.25)
        lo, hi = compute_correlation_band(predicted)
        self.assertAlmostEqual(pt.correlation_lower, lo)
        self.assertAlmostEqual(pt.correlation_upper, hi)

    def test_invalid_test_case_skipped_from_results(self):
        tc = [TestCase("BAD", 0.0, "Z")]
        bp = [BaselinePrediction("P1", "displacement_mm", 5.0)]
        ir = [InstrumentRange("P1", "displacement_mm", 20.0)]
        report = build_test_prediction(tc, bp, ir)
        self.assertGreater(len(report["errors"]), 0)
        self.assertNotIn("BAD", report["results"])

    def test_missing_instrument_range_flagged(self):
        tc = [TestCase("TC-01", 1.0, "X")]
        bp = [BaselinePrediction("UNMAPPED", "force_N", 100.0)]
        report = build_test_prediction(tc, bp, [])
        codes = [e.code for e in report["errors"]]
        self.assertIn("MISSING_INSTRUMENT_RANGE", codes)

    def test_instrument_overrange_flagged(self):
        # 30.0 * 2.0 = 60.0, instrument max = 50.0
        tc = [TestCase("TC-01", 2.0, "Z")]
        bp = [BaselinePrediction("P1", "displacement_mm", 30.0)]
        ir = [InstrumentRange("P1", "displacement_mm", 50.0)]
        report = build_test_prediction(tc, bp, ir)
        codes = [e.code for e in report["errors"]]
        self.assertIn("INSTRUMENT_OVERRANGE", codes)
        self.assertFalse(report["results"]["TC-01"][0].instrument_ok)

    def test_instrument_within_range_ok(self):
        tc = [TestCase("TC-01", 1.0, "axial")]
        bp = [BaselinePrediction("P1", "stress_MPa", 50.0)]
        ir = [InstrumentRange("P1", "stress_MPa", 200.0)]
        report = build_test_prediction(tc, bp, ir)
        self.assertTrue(report["results"]["TC-01"][0].instrument_ok)

    def test_multiple_test_cases_all_present(self):
        tc = [
            TestCase("TC-01", 1.0, "Z"),
            TestCase("TC-02", 1.5, "lateral"),
        ]
        bp = [BaselinePrediction("P1", "stress_MPa", 50.0)]
        ir = [InstrumentRange("P1", "stress_MPa", 200.0)]
        report = build_test_prediction(tc, bp, ir)
        self.assertIn("TC-01", report["results"])
        self.assertIn("TC-02", report["results"])

    def test_scaling_differs_across_cases(self):
        tc = [
            TestCase("TC-01", 1.0, "Z"),
            TestCase("TC-02", 1.5, "lateral"),
        ]
        bp = [BaselinePrediction("P1", "stress_MPa", 50.0)]
        ir = [InstrumentRange("P1", "stress_MPa", 200.0)]
        report = build_test_prediction(tc, bp, ir)
        pt1 = report["results"]["TC-01"][0]
        pt2 = report["results"]["TC-02"][0]
        self.assertAlmostEqual(pt1.predicted_value, 50.0)
        self.assertAlmostEqual(pt2.predicted_value, 75.0)

    def test_negative_base_value_abort_uses_absolute(self):
        # Negative base (e.g. compressive stress) should still produce a
        # positive abort threshold based on the magnitude
        tc = [TestCase("TC-01", 1.0, "Z")]
        bp = [BaselinePrediction("P1", "stress_MPa", -80.0)]
        ir = [InstrumentRange("P1", "stress_MPa", 200.0)]
        report = build_test_prediction(tc, bp, ir)
        pt = report["results"]["TC-01"][0]
        self.assertGreater(pt.abort_threshold, 0)
        self.assertAlmostEqual(pt.abort_threshold, 80.0 * DEFAULT_ABORT_MARGIN)

    def test_empty_test_cases_returns_empty_results(self):
        report = build_test_prediction([], [], [])
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["results"], {})


if __name__ == "__main__":
    unittest.main()

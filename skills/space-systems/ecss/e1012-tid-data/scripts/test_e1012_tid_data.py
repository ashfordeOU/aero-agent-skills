import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1012_tid_data_logic import (
    interpolate_degradation,
    apply_eldrs_correction,
    apply_lot_margin,
    check_compliance,
    compute_margin_percent,
    predict_tid_degradation,
)


class TestInterpolateDegradation(unittest.TestCase):

    def setUp(self):
        # Leakage current (nA) — increases with dose
        self.leak_data = [(0.0, 1.0), (10.0, 5.0), (50.0, 15.0), (100.0, 30.0)]
        # Gain (hFE) — decreases with dose
        self.gain_data = [(0.0, 200.0), (10.0, 180.0), (50.0, 140.0), (100.0, 80.0)]

    def test_exact_data_point_returns_table_value(self):
        self.assertAlmostEqual(interpolate_degradation(self.leak_data, 10.0), 5.0)

    def test_interpolation_midpoint_between_two_points(self):
        # (10,5) to (50,15): at 30 → frac=0.5 → 5 + 0.5*10 = 10.0
        self.assertAlmostEqual(interpolate_degradation(self.leak_data, 30.0), 10.0)

    def test_interpolation_at_zero_dose(self):
        self.assertAlmostEqual(interpolate_degradation(self.leak_data, 0.0), 1.0)

    def test_interpolation_at_maximum_test_dose(self):
        self.assertAlmostEqual(interpolate_degradation(self.leak_data, 100.0), 30.0)

    def test_decreasing_parameter_interpolation(self):
        # (50,140) to (100,80): at 75 → frac=0.5 → 140 + 0.5*(80-140) = 110.0
        self.assertAlmostEqual(interpolate_degradation(self.gain_data, 75.0), 110.0)

    def test_unsorted_input_is_handled(self):
        unsorted = [(100.0, 30.0), (0.0, 1.0), (50.0, 15.0), (10.0, 5.0)]
        self.assertAlmostEqual(interpolate_degradation(unsorted, 30.0), 10.0)

    def test_dose_beyond_max_raises_value_error(self):
        with self.assertRaises(ValueError):
            interpolate_degradation(self.leak_data, 100.1)

    def test_negative_dose_raises_value_error(self):
        with self.assertRaises(ValueError):
            interpolate_degradation(self.leak_data, -1.0)

    def test_empty_data_raises_value_error(self):
        with self.assertRaises(ValueError):
            interpolate_degradation([], 10.0)


class TestApplyELDRSCorrection(unittest.TestCase):

    def test_increasing_parameter_multiplied_by_factor(self):
        # Leakage = 10 nA, ELDRS factor 2.0 → 20 nA at low dose rate
        self.assertAlmostEqual(apply_eldrs_correction(10.0, 2.0, "increasing"), 20.0)

    def test_decreasing_parameter_divided_by_factor(self):
        # Gain = 80 at high rate; at low rate further degraded → 80/2.0 = 40
        self.assertAlmostEqual(apply_eldrs_correction(80.0, 2.0, "decreasing"), 40.0)

    def test_unity_factor_leaves_value_unchanged(self):
        self.assertAlmostEqual(apply_eldrs_correction(50.0, 1.0, "increasing"), 50.0)

    def test_factor_below_unity_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_eldrs_correction(50.0, 0.9, "increasing")

    def test_invalid_direction_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_eldrs_correction(50.0, 1.5, "lateral")


class TestApplyLotMargin(unittest.TestCase):

    def test_increasing_margin_raises_value(self):
        # 10.0 with 20 % margin → 12.0
        self.assertAlmostEqual(apply_lot_margin(10.0, 0.20, "increasing"), 12.0)

    def test_decreasing_margin_lowers_value(self):
        # 80.0 with 20 % margin → 64.0
        self.assertAlmostEqual(apply_lot_margin(80.0, 0.20, "decreasing"), 64.0)

    def test_zero_margin_leaves_value_unchanged(self):
        self.assertAlmostEqual(apply_lot_margin(50.0, 0.0, "increasing"), 50.0)

    def test_margin_at_unity_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_lot_margin(10.0, 1.0, "increasing")

    def test_negative_margin_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_lot_margin(10.0, -0.1, "increasing")

    def test_invalid_direction_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_lot_margin(10.0, 0.1, "lateral")


class TestCheckCompliance(unittest.TestCase):

    def test_increasing_below_limit_is_compliant(self):
        self.assertTrue(check_compliance(5.0, 10.0, "increasing"))

    def test_increasing_at_limit_is_compliant(self):
        self.assertTrue(check_compliance(10.0, 10.0, "increasing"))

    def test_increasing_above_limit_is_not_compliant(self):
        self.assertFalse(check_compliance(10.1, 10.0, "increasing"))

    def test_decreasing_above_limit_is_compliant(self):
        self.assertTrue(check_compliance(50.0, 30.0, "decreasing"))

    def test_decreasing_at_limit_is_compliant(self):
        self.assertTrue(check_compliance(30.0, 30.0, "decreasing"))

    def test_decreasing_below_limit_is_not_compliant(self):
        self.assertFalse(check_compliance(29.9, 30.0, "decreasing"))

    def test_invalid_direction_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_compliance(5.0, 10.0, "sideways")


class TestComputeMarginPercent(unittest.TestCase):

    def test_increasing_positive_margin(self):
        # predicted=8, limit=10 → (10-8)/10*100 = 20 %
        self.assertAlmostEqual(compute_margin_percent(8.0, 10.0, "increasing"), 20.0)

    def test_increasing_negative_margin_on_exceedance(self):
        # predicted=12, limit=10 → (10-12)/10*100 = -20 %
        self.assertAlmostEqual(compute_margin_percent(12.0, 10.0, "increasing"), -20.0)

    def test_decreasing_positive_margin(self):
        # predicted=50, limit=30 → (50-30)/30*100 ≈ 66.667 %
        self.assertAlmostEqual(
            compute_margin_percent(50.0, 30.0, "decreasing"), 66.6666, places=3
        )

    def test_decreasing_negative_margin_on_exceedance(self):
        # predicted=20, limit=30 → (20-30)/30*100 ≈ -33.333 %
        self.assertAlmostEqual(
            compute_margin_percent(20.0, 30.0, "decreasing"), -33.3333, places=3
        )

    def test_zero_functional_limit_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_margin_percent(5.0, 0.0, "increasing")


class TestPredictTIDDegradation(unittest.TestCase):

    def setUp(self):
        # Leakage current data (nA) — increasing degradation
        self.leak_data = [(0.0, 1.0), (10.0, 5.0), (50.0, 15.0), (100.0, 30.0)]

    def test_returns_all_required_keys(self):
        result = predict_tid_degradation(
            self.leak_data, 75.0, 1.5, 0.20, 60.0, "increasing"
        )
        for key in (
            "interpolated_value",
            "eldrs_corrected_value",
            "lot_adjusted_value",
            "compliance",
            "margin_percent",
            "status",
        ):
            self.assertIn(key, result)

    def test_compliant_case_yields_pass_status(self):
        # At 75 krad: interp=(50→15, 100→30) frac=0.5 → 22.5
        # ELDRS 1.5 → 33.75; lot 20 % → 40.5; limit 60 → PASS
        result = predict_tid_degradation(
            self.leak_data, 75.0, 1.5, 0.20, 60.0, "increasing"
        )
        self.assertTrue(result["compliance"])
        self.assertEqual(result["status"], "PASS")
        self.assertAlmostEqual(result["lot_adjusted_value"], 40.5)
        self.assertGreater(result["margin_percent"], 0.0)

    def test_non_compliant_case_yields_fail_status(self):
        # Steep degradation: (100→80); at 75: 15+0.5*(80-15)=47.5
        # ELDRS 2.0 → 95; lot 30 % → 123.5; limit 60 → FAIL
        steep = [(0.0, 1.0), (10.0, 5.0), (50.0, 15.0), (100.0, 80.0)]
        result = predict_tid_degradation(steep, 75.0, 2.0, 0.30, 60.0, "increasing")
        self.assertFalse(result["compliance"])
        self.assertEqual(result["status"], "FAIL")
        self.assertLess(result["margin_percent"], 0.0)

    def test_pipeline_intermediate_values_are_numerically_consistent(self):
        result = predict_tid_degradation(
            self.leak_data, 75.0, 1.5, 0.20, 60.0, "increasing"
        )
        self.assertAlmostEqual(
            result["eldrs_corrected_value"], result["interpolated_value"] * 1.5
        )
        self.assertAlmostEqual(
            result["lot_adjusted_value"], result["eldrs_corrected_value"] * 1.2
        )

    def test_decreasing_parameter_compliant_case(self):
        # Gain data: at 75 krad gain=110; ELDRS 1.0 (no effect); lot 10 % → 99; limit 60 → PASS
        gain_data = [(0.0, 200.0), (10.0, 180.0), (50.0, 140.0), (100.0, 80.0)]
        result = predict_tid_degradation(
            gain_data, 75.0, 1.0, 0.10, 60.0, "decreasing"
        )
        self.assertTrue(result["compliance"])
        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

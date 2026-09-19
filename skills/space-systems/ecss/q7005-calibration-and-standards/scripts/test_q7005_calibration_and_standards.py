"""Contract test for the IR calibration and standards leaf (stdlib unittest)."""

import unittest

from q7005_calibration_and_standards_logic import (
    MAX_RELATIVE_RESIDUAL,
    MIN_R_SQUARED,
    MIN_STANDARDS,
    RECOVERY_BAND,
    assess_calibration,
    build_calibration,
    coefficient_of_determination,
    invert_calibration,
    least_squares_fit,
    predicted_absorbance,
    residuals,
    validate_standards,
    verify_with_standard,
    working_range,
)

LINEAR = [(1.0, 0.03), (2.0, 0.05), (5.0, 0.11), (10.0, 0.21)]
ORIGIN = [(1.0, 0.02), (2.0, 0.04), (5.0, 0.10)]
BENT = [(1.0, 0.03), (2.0, 0.05), (5.0, 0.11), (10.0, 0.15)]
FALLING = [(1.0, 0.20), (2.0, 0.10), (5.0, 0.02)]


class TestValidateStandards(unittest.TestCase):
    def test_valid_standards_are_sorted(self):
        points = validate_standards([(5.0, 0.11), (1.0, 0.03), (2.0, 0.05)])
        self.assertAlmostEqual(points[0][0], 1.0, places=9)
        self.assertAlmostEqual(points[-1][0], 5.0, places=9)

    def test_non_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_standards("1,0.03")

    def test_malformed_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_standards([(1.0, 0.03, 7.0), (2.0, 0.05), (5.0, 0.11)])

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            validate_standards([(-1.0, 0.03), (2.0, 0.05), (5.0, 0.11)])

    def test_negative_absorbance_raises(self):
        with self.assertRaises(ValueError):
            validate_standards([(1.0, -0.03), (2.0, 0.05), (5.0, 0.11)])

    def test_two_levels_raise_however_many_replicates(self):
        with self.assertRaises(ValueError):
            validate_standards([(1.0, 0.03), (1.0, 0.03), (2.0, 0.05),
                                (2.0, 0.051)])

    def test_exactly_the_minimum_number_of_levels_is_accepted(self):
        points = validate_standards(ORIGIN)
        self.assertEqual(len({p[0] for p in points}), MIN_STANDARDS)

    def test_boolean_mass_is_rejected_not_coerced(self):
        with self.assertRaises(ValueError):
            validate_standards([(True, 0.03), (2.0, 0.05), (5.0, 0.11)])


class TestLeastSquaresFit(unittest.TestCase):
    def test_free_intercept_recovers_the_generating_line(self):
        slope, intercept = least_squares_fit(LINEAR)
        self.assertAlmostEqual(slope, 0.02, places=9)
        self.assertAlmostEqual(intercept, 0.01, places=9)

    def test_forced_origin_gives_a_zero_intercept(self):
        slope, intercept = least_squares_fit(ORIGIN, through_origin=True)
        self.assertAlmostEqual(slope, 0.02, places=9)
        self.assertAlmostEqual(intercept, 0.0, places=9)

    def test_non_boolean_through_origin_raises(self):
        with self.assertRaises(ValueError):
            least_squares_fit(LINEAR, through_origin="yes")

    def test_predicted_absorbance_follows_the_line(self):
        self.assertAlmostEqual(
            predicted_absorbance(0.02, 0.01, 5.0), 0.11, places=9
        )

    def test_residuals_vanish_on_an_exact_line(self):
        for record in residuals(LINEAR, 0.02, 0.01):
            self.assertAlmostEqual(record["residual"], 0.0, places=9)


class TestCoefficientOfDetermination(unittest.TestCase):
    def test_exact_line_explains_everything(self):
        self.assertAlmostEqual(
            coefficient_of_determination(LINEAR, 0.02, 0.01), 1.0, places=9
        )

    def test_bent_response_explains_less(self):
        slope, intercept = least_squares_fit(BENT)
        r2 = coefficient_of_determination(BENT, slope, intercept)
        self.assertLess(r2, MIN_R_SQUARED)

    def test_flat_response_raises(self):
        with self.assertRaises(ValueError):
            coefficient_of_determination(
                [(1.0, 0.05), (2.0, 0.05), (5.0, 0.05)], 0.0, 0.05
            )


class TestBuildCalibration(unittest.TestCase):
    def test_linear_standards_build_an_acceptable_curve(self):
        cal = build_calibration(LINEAR)
        self.assertAlmostEqual(cal["slope"], 0.02, places=9)
        self.assertAlmostEqual(cal["r_squared"], 1.0, places=9)
        self.assertTrue(cal["linear"])
        self.assertEqual(cal["n_levels"], 4)

    def test_bent_standards_fail_the_linearity_grade(self):
        cal = build_calibration(BENT)
        self.assertFalse(cal["linear"])
        self.assertGreater(cal["worst_relative_residual"], MAX_RELATIVE_RESIDUAL)

    def test_falling_response_raises_on_the_slope_sign(self):
        with self.assertRaises(ValueError):
            build_calibration(FALLING)

    def test_working_range_brackets_the_standards(self):
        bounds = working_range(LINEAR, 0.02, 0.01)
        self.assertAlmostEqual(bounds["min_areal_mass"], 1.0, places=9)
        self.assertAlmostEqual(bounds["max_areal_mass"], 10.0, places=9)
        self.assertAlmostEqual(bounds["min_absorbance"], 0.03, places=9)
        self.assertAlmostEqual(bounds["max_absorbance"], 0.21, places=9)

    def test_negative_linearity_threshold_raises(self):
        with self.assertRaises(ValueError):
            build_calibration(LINEAR, min_r_squared=-0.5)

    def test_forced_origin_is_recorded_on_the_curve(self):
        cal = build_calibration(ORIGIN, through_origin=True)
        self.assertTrue(cal["through_origin"])
        self.assertAlmostEqual(cal["intercept"], 0.0, places=9)


class TestInvertCalibration(unittest.TestCase):
    def test_inversion_recovers_a_standard(self):
        cal = build_calibration(LINEAR)
        self.assertAlmostEqual(invert_calibration(cal, 0.11), 5.0, places=9)

    def test_absorbance_at_the_bottom_bound_is_accepted(self):
        cal = build_calibration(LINEAR)
        self.assertAlmostEqual(invert_calibration(cal, 0.03), 1.0, places=9)

    def test_absorbance_at_the_top_bound_is_accepted(self):
        cal = build_calibration(LINEAR)
        self.assertAlmostEqual(invert_calibration(cal, 0.21), 10.0, places=9)

    def test_absorbance_above_the_top_standard_raises(self):
        cal = build_calibration(LINEAR)
        with self.assertRaises(ValueError):
            invert_calibration(cal, 0.40)

    def test_absorbance_below_the_bottom_standard_raises(self):
        cal = build_calibration(LINEAR)
        with self.assertRaises(ValueError):
            invert_calibration(cal, 0.005)

    def test_negative_absorbance_raises(self):
        cal = build_calibration(LINEAR)
        with self.assertRaises(ValueError):
            invert_calibration(cal, -0.01)

    def test_non_calibration_argument_raises(self):
        with self.assertRaises(ValueError):
            invert_calibration({"intercept": 0.01}, 0.11)


class TestVerifyWithStandard(unittest.TestCase):
    def test_full_recovery_is_inside_the_band(self):
        cal = build_calibration(LINEAR)
        out = verify_with_standard(cal, 4.0, 0.09)
        self.assertAlmostEqual(out["recovery_fraction"], 1.0, places=9)
        self.assertTrue(out["within_band"])

    def test_half_recovery_is_outside_the_band(self):
        cal = build_calibration(LINEAR)
        out = verify_with_standard(cal, 4.0, 0.05)
        self.assertAlmostEqual(out["recovery_fraction"], 0.5, places=9)
        self.assertFalse(out["within_band"])

    def test_recovery_exactly_at_the_lower_edge_is_accepted(self):
        cal = build_calibration(LINEAR)
        out = verify_with_standard(cal, 5.0, 0.01 + 0.02 * 4.5)
        self.assertAlmostEqual(out["recovery_fraction"], RECOVERY_BAND[0],
                               places=9)
        self.assertTrue(out["within_band"])

    def test_zero_prepared_mass_raises(self):
        cal = build_calibration(LINEAR)
        with self.assertRaises(ValueError):
            verify_with_standard(cal, 0.0, 0.09)

    def test_inverted_band_raises(self):
        cal = build_calibration(LINEAR)
        with self.assertRaises(ValueError):
            verify_with_standard(cal, 4.0, 0.09, band=(1.2, 0.8))

    def test_malformed_band_raises(self):
        cal = build_calibration(LINEAR)
        with self.assertRaises(ValueError):
            verify_with_standard(cal, 4.0, 0.09, band=(0.9,))


class TestAssessCalibration(unittest.TestCase):
    def test_verified_linear_curve_is_usable(self):
        out = assess_calibration({"standards": LINEAR,
                                  "verification": (4.0, 0.09)})
        self.assertTrue(out["usable"])
        self.assertEqual(out["findings"], [])

    def test_missing_verification_is_a_finding(self):
        out = assess_calibration({"standards": LINEAR})
        self.assertFalse(out["usable"])
        self.assertTrue(any("verification standard" in f for f in out["findings"]))

    def test_bent_curve_reports_the_fit_finding(self):
        out = assess_calibration({"standards": BENT,
                                  "verification": (4.0, 0.09)})
        self.assertTrue(any("not acceptable" in f for f in out["findings"]))

    def test_forced_origin_is_called_out(self):
        out = assess_calibration({"standards": ORIGIN, "through_origin": True,
                                  "verification": (4.0, 0.08)})
        self.assertTrue(any("through the origin" in f for f in out["findings"]))

    def test_failed_recovery_is_a_finding(self):
        out = assess_calibration({"standards": LINEAR,
                                  "verification": (4.0, 0.05)})
        self.assertTrue(any("recovered" in f for f in out["findings"]))

    def test_missing_standards_key_raises(self):
        with self.assertRaises(ValueError):
            assess_calibration({"verification": (4.0, 0.09)})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_calibration(LINEAR)

    def test_malformed_verification_raises(self):
        with self.assertRaises(ValueError):
            assess_calibration({"standards": LINEAR, "verification": (4.0,)})


if __name__ == "__main__":
    unittest.main(verbosity=1)

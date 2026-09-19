"""Contract tests for the clause 5.6.14.6 time correlation logic."""

import math
import unittest

from e50_time_correlation_logic import (
    ACCURACY_EXCEEDED,
    CORRELATED,
    UNDERDETERMINED,
    assess_time_correlation,
    correct_for_light_time,
    drift_uncertainty,
    fit_correlation,
    predict_reference,
    prediction_error_s,
    residual_rms,
    residuals,
    validate_accuracy,
    validate_pairs,
    validity_horizon_s,
)

# A clean set: offset 8 s at epoch, drift 1/128 s per s, no dispersion.
CLEAN = [(0.0, 8.0), (128.0, 137.0), (256.0, 266.0), (384.0, 395.0), (512.0, 524.0)]
# The same span with half-second dispersion on two pairs.
NOISY = [(0.0, 8.0), (128.0, 137.5), (256.0, 266.0), (384.0, 394.5), (512.0, 524.0)]
TWO = [(0.0, 8.0), (512.0, 524.0)]

NOISY_RMS = 0.28284271247460446
NOISY_DRIFT_SE = 0.0009021097956087438


class ValidationTests(unittest.TestCase):
    def test_clean_set_validates(self):
        self.assertEqual(len(validate_pairs(CLEAN)), 5)

    def test_single_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_pairs([(0.0, 8.0)])

    def test_non_increasing_onboard_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_pairs([(0.0, 8.0), (0.0, 9.0)])

    def test_three_element_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_pairs([(0.0, 8.0, 1.0), (1.0, 9.0)])

    def test_boolean_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_pairs([(0.0, True), (1.0, 9.0)])

    def test_infinite_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_pairs([(0.0, float("inf")), (1.0, 9.0)])

    def test_zero_accuracy_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_accuracy(0.0)

    def test_negative_accuracy_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_accuracy(-1.0)


class LightTimeTests(unittest.TestCase):
    def test_correction_shifts_every_reference_time(self):
        shifted = correct_for_light_time(CLEAN, 0.5)
        self.assertAlmostEqual(shifted[0][1], 7.5, places=9)
        self.assertAlmostEqual(shifted[4][1], 523.5, places=9)

    def test_correction_leaves_onboard_time_alone(self):
        shifted = correct_for_light_time(CLEAN, 0.5)
        self.assertAlmostEqual(shifted[3][0], 384.0, places=9)

    def test_correction_is_a_pure_bias_on_the_offset(self):
        plain = fit_correlation(CLEAN)
        shifted = fit_correlation(correct_for_light_time(CLEAN, 0.5))
        self.assertAlmostEqual(shifted["offset_s"], plain["offset_s"] - 0.5, places=9)
        self.assertAlmostEqual(shifted["drift_s_per_s"], plain["drift_s_per_s"], places=12)

    def test_negative_light_time_rejected(self):
        with self.assertRaises(ValueError):
            correct_for_light_time(CLEAN, -0.5)


class FitTests(unittest.TestCase):
    def test_clean_set_recovers_the_offset(self):
        self.assertAlmostEqual(fit_correlation(CLEAN)["offset_s"], 8.0, places=9)

    def test_clean_set_recovers_the_drift(self):
        self.assertAlmostEqual(fit_correlation(CLEAN)["drift_s_per_s"], 0.0078125, places=12)

    def test_epoch_is_the_first_onboard_reading(self):
        self.assertAlmostEqual(fit_correlation(CLEAN)["epoch_s"], 0.0, places=9)

    def test_clean_set_leaves_no_residuals(self):
        fit = fit_correlation(CLEAN)
        self.assertAlmostEqual(residual_rms(residuals(CLEAN, fit)), 0.0, places=9)

    def test_dispersion_shows_in_the_residual_spread(self):
        fit = fit_correlation(NOISY)
        self.assertAlmostEqual(residual_rms(residuals(NOISY, fit)), NOISY_RMS, places=9)

    def test_residual_rms_matches_the_closed_form(self):
        fit = fit_correlation(NOISY)
        self.assertAlmostEqual(
            residual_rms(residuals(NOISY, fit)), math.sqrt(0.08), places=9
        )

    def test_empty_residuals_rejected(self):
        with self.assertRaises(ValueError):
            residual_rms([])

    def test_prediction_follows_the_fitted_line(self):
        fit = fit_correlation(CLEAN)
        self.assertAlmostEqual(predict_reference(fit, 256.0), 266.0, places=9)

    def test_prediction_extrapolates_past_the_last_pair(self):
        fit = fit_correlation(CLEAN)
        self.assertAlmostEqual(predict_reference(fit, 1024.0), 1040.0, places=9)


class UncertaintyTests(unittest.TestCase):
    def test_two_pairs_give_no_drift_uncertainty(self):
        self.assertIsNone(drift_uncertainty(TWO, fit_correlation(TWO)))

    def test_dispersed_set_has_a_drift_standard_error(self):
        fit = fit_correlation(NOISY)
        self.assertAlmostEqual(drift_uncertainty(NOISY, fit), NOISY_DRIFT_SE, places=12)

    def test_clean_set_has_no_drift_uncertainty_to_speak_of(self):
        fit = fit_correlation(CLEAN)
        self.assertAlmostEqual(drift_uncertainty(CLEAN, fit), 0.0, places=12)

    def test_prediction_error_grows_with_elapsed_time(self):
        near = prediction_error_s(NOISY_RMS, NOISY_DRIFT_SE, 0.0)
        far = prediction_error_s(NOISY_RMS, NOISY_DRIFT_SE, 600.0)
        self.assertAlmostEqual(near, NOISY_RMS, places=9)
        self.assertGreater(far, near + 0.5)

    def test_prediction_error_is_undetermined_without_a_drift_error(self):
        self.assertIsNone(prediction_error_s(NOISY_RMS, None, 600.0))

    def test_negative_elapsed_time_rejected(self):
        with self.assertRaises(ValueError):
            prediction_error_s(NOISY_RMS, NOISY_DRIFT_SE, -1.0)


class HorizonTests(unittest.TestCase):
    def test_horizon_is_finite_for_a_dispersed_fit(self):
        horizon = validity_horizon_s(1.0, NOISY_RMS, NOISY_DRIFT_SE)
        self.assertAlmostEqual(horizon, 794.9778297678918, places=6)

    def test_horizon_is_undetermined_without_a_drift_error(self):
        self.assertIsNone(validity_horizon_s(1.0, NOISY_RMS, None))

    def test_exactly_known_drift_never_decays(self):
        self.assertEqual(validity_horizon_s(1.0, 0.25, 0.0), float("inf"))

    def test_fit_already_outside_the_bound_has_no_horizon_left(self):
        self.assertAlmostEqual(validity_horizon_s(0.125, NOISY_RMS, NOISY_DRIFT_SE), 0.0, places=9)

    def test_a_tighter_bound_shortens_the_horizon(self):
        wide = validity_horizon_s(1.0, NOISY_RMS, NOISY_DRIFT_SE)
        tight = validity_horizon_s(0.5, NOISY_RMS, NOISY_DRIFT_SE)
        self.assertGreater(wide, tight + 100.0)


class AssessTests(unittest.TestCase):
    def test_clean_set_inside_the_bound_is_correlated(self):
        result = assess_time_correlation(CLEAN, 1.0)
        self.assertEqual(result["verdict"], CORRELATED)
        self.assertTrue(result["within_accuracy"])

    def test_correlated_set_reports_no_findings(self):
        self.assertEqual(assess_time_correlation(CLEAN, 1.0)["findings"], [])

    def test_two_pairs_are_underdetermined_not_perfect(self):
        result = assess_time_correlation(TWO, 1.0)
        self.assertEqual(result["verdict"], UNDERDETERMINED)
        self.assertFalse(result["within_accuracy"])

    def test_underdetermined_set_explains_the_zero_residuals(self):
        findings = assess_time_correlation(TWO, 1.0)["findings"]
        self.assertTrue(any("zero by" in f and "construction" in f for f in findings))

    def test_underdetermined_set_has_no_horizon(self):
        self.assertIsNone(assess_time_correlation(TWO, 1.0)["validity_horizon_s"])

    def test_dispersion_beyond_the_bound_is_flagged(self):
        result = assess_time_correlation(NOISY, 0.125)
        self.assertEqual(result["verdict"], ACCURACY_EXCEEDED)

    def test_accuracy_failure_offers_both_ways_out(self):
        findings = assess_time_correlation(NOISY, 0.125)["findings"]
        self.assertTrue(any("either the bound is wrong" in f for f in findings))

    def test_recorrelation_interval_is_the_validity_horizon(self):
        result = assess_time_correlation(NOISY, 1.0)
        self.assertAlmostEqual(
            result["recorrelation_interval_s"], result["validity_horizon_s"], places=9
        )

    def test_light_time_is_removed_before_fitting(self):
        result = assess_time_correlation(CLEAN, 1.0, one_way_light_time_s=0.5)
        self.assertAlmostEqual(result["offset_s"], 7.5, places=9)
        self.assertAlmostEqual(result["light_time_applied_s"], 0.5, places=9)

    def test_light_time_larger_than_the_bound_is_called_out(self):
        findings = assess_time_correlation(CLEAN, 1.0, one_way_light_time_s=600.0)["findings"]
        self.assertTrue(any("left uncorrected" in f for f in findings))

    def test_small_light_time_is_applied_without_a_finding(self):
        result = assess_time_correlation(CLEAN, 1.0, one_way_light_time_s=0.5)
        self.assertEqual(result["findings"], [])

    def test_expected_error_is_reported_for_an_elapsed_interval(self):
        result = assess_time_correlation(NOISY, 1.0, elapsed_since_last_s=600.0)
        self.assertAlmostEqual(result["expected_error_s"], 0.8241085898398508, places=9)

    def test_bad_accuracy_bound_rejected(self):
        with self.assertRaises(ValueError):
            assess_time_correlation(CLEAN, 0.0)

    def test_negative_elapsed_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_time_correlation(CLEAN, 1.0, elapsed_since_last_s=-1.0)


if __name__ == "__main__":
    unittest.main()

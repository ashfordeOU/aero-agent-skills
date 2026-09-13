#!/usr/bin/env python3
"""Contract test for the test tolerance and accuracy rules leaf."""

import unittest

from e2008_test_tolerance_and_accuracy_rules_logic import (
    DRIFT_FRACTION,
    GUARD_BAND_RATIO,
    MINIMUM_TEST_ACCURACY_RATIO,
    PRECISION_FRACTION,
    RESOLUTION_FRACTION,
    assess_test_instrumentation,
    check_instrument_precision,
    check_reading_resolution,
    check_set_point_drift,
    evaluate_test_parameter,
    guard_banded_limits,
    required_instrument_precision,
    required_reading_resolution,
    test_accuracy_ratio,
    tolerance_band,
)


def good_parameter(**overrides):
    parameter = {
        "id": "TP-CELL-TEMP",
        "role": "controlled",
        "unit": "degC",
        "nominal": 25.0,
        "upper_tolerance": 2.0,
        "lower_tolerance": 2.0,
        "instrument_uncertainty": 0.4,
        "reading_resolution": 0.1,
        "set_point_drift": 0.5,
    }
    parameter.update(overrides)
    return parameter


def measured_parameter(**overrides):
    parameter = good_parameter(
        id="TP-ILLUMINANCE",
        role="measured",
        unit="W/m2",
        nominal=1367.0,
        upper_tolerance=27.0,
        lower_tolerance=27.0,
        instrument_uncertainty=6.0,
        reading_resolution=1.0,
    )
    del parameter["set_point_drift"]
    parameter.update(overrides)
    return parameter


def instrumentation_list():
    return [good_parameter(id="TP-CELL-TEMP"), measured_parameter()]


class TestToleranceBand(unittest.TestCase):
    def test_symmetric_band_limits(self):
        band = tolerance_band(25.0, 2.0, 2.0)
        self.assertAlmostEqual(band["upper_limit"], 27.0, places=9)
        self.assertAlmostEqual(band["lower_limit"], 23.0, places=9)

    def test_symmetric_band_governing_half_width(self):
        band = tolerance_band(25.0, 2.0, 2.0)
        self.assertAlmostEqual(band["governing_half_width"], 2.0, places=9)
        self.assertFalse(band["asymmetric"])

    def test_asymmetric_band_takes_the_tighter_side(self):
        band = tolerance_band(100.0, 5.0, 1.5)
        self.assertAlmostEqual(band["governing_half_width"], 1.5, places=9)
        self.assertTrue(band["asymmetric"])

    def test_one_sided_band_is_flagged(self):
        band = tolerance_band(10.0, 0.0, 0.8)
        self.assertTrue(band["one_sided"])
        self.assertAlmostEqual(band["governing_half_width"], 0.8, places=9)

    def test_band_width_is_the_sum_of_both_sides(self):
        band = tolerance_band(0.0, 3.0, 1.0)
        self.assertAlmostEqual(band["width"], 4.0, places=9)

    def test_negative_nominal_is_allowed(self):
        band = tolerance_band(-40.0, 2.0, 2.0)
        self.assertAlmostEqual(band["lower_limit"], -42.0, places=9)

    def test_two_zero_sides_raise(self):
        with self.assertRaises(ValueError):
            tolerance_band(25.0, 0.0, 0.0)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            tolerance_band(25.0, -1.0, 2.0)

    def test_non_numeric_nominal_raises(self):
        with self.assertRaises(ValueError):
            tolerance_band("25", 2.0, 2.0)

    def test_boolean_tolerance_raises(self):
        with self.assertRaises(ValueError):
            tolerance_band(25.0, True, 2.0)


class TestRequiredPrecision(unittest.TestCase):
    def test_required_precision_is_a_share_of_the_half_band(self):
        self.assertAlmostEqual(
            required_instrument_precision(3.0), 3.0 * PRECISION_FRACTION, places=9
        )

    def test_minimum_ratio_is_the_reciprocal_of_the_share(self):
        self.assertAlmostEqual(
            MINIMUM_TEST_ACCURACY_RATIO, 1.0 / PRECISION_FRACTION, places=9
        )

    def test_a_tighter_share_may_be_imposed(self):
        self.assertAlmostEqual(
            required_instrument_precision(3.0, 0.1), 0.3, places=9
        )

    def test_zero_half_band_raises(self):
        with self.assertRaises(ValueError):
            required_instrument_precision(0.0)

    def test_share_of_one_raises(self):
        with self.assertRaises(ValueError):
            required_instrument_precision(3.0, 1.0)

    def test_negative_share_raises(self):
        with self.assertRaises(ValueError):
            required_instrument_precision(3.0, -0.2)


class TestAccuracyRatio(unittest.TestCase):
    def test_ratio_is_half_band_over_uncertainty(self):
        self.assertAlmostEqual(test_accuracy_ratio(2.0, 0.5), 4.0, places=9)

    def test_a_coarse_instrument_gives_a_small_ratio(self):
        self.assertAlmostEqual(test_accuracy_ratio(2.0, 4.0), 0.5, places=9)

    def test_zero_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            test_accuracy_ratio(2.0, 0.0)

    def test_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            test_accuracy_ratio(2.0, -0.1)


class TestInstrumentPrecisionCheck(unittest.TestCase):
    def test_a_fine_instrument_is_adequate(self):
        result = check_instrument_precision(2.0, 0.4)
        self.assertTrue(result["adequate"])

    def test_a_coarse_instrument_is_not_adequate(self):
        result = check_instrument_precision(2.0, 1.2)
        self.assertFalse(result["adequate"])

    def test_exactly_one_third_survives_float_representation(self):
        half_width = 3.0
        result = check_instrument_precision(half_width, half_width / 3.0)
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["ratio"], MINIMUM_TEST_ACCURACY_RATIO, places=9)

    def test_margin_is_required_minus_actual(self):
        result = check_instrument_precision(3.0, 0.5)
        self.assertAlmostEqual(
            result["margin"], result["required"] - result["actual"], places=9
        )


class TestReadingResolution(unittest.TestCase):
    def test_required_resolution_is_a_tenth_of_the_half_band(self):
        self.assertAlmostEqual(
            required_reading_resolution(2.0), 2.0 * RESOLUTION_FRACTION, places=9
        )

    def test_a_fine_display_is_adequate(self):
        self.assertTrue(check_reading_resolution(2.0, 0.05)["adequate"])

    def test_a_coarse_display_is_not_adequate(self):
        self.assertFalse(check_reading_resolution(2.0, 0.5)["adequate"])

    def test_exact_resolution_bound_is_adequate(self):
        result = check_reading_resolution(2.0, 2.0 * RESOLUTION_FRACTION)
        self.assertTrue(result["adequate"])

    def test_zero_resolution_raises(self):
        with self.assertRaises(ValueError):
            check_reading_resolution(2.0, 0.0)


class TestSetPointDrift(unittest.TestCase):
    def test_allowed_drift_is_a_share_of_the_half_band(self):
        result = check_set_point_drift(2.0, 0.2)
        self.assertAlmostEqual(result["allowed"], 2.0 * DRIFT_FRACTION, places=9)

    def test_a_steady_set_point_is_adequate(self):
        self.assertTrue(check_set_point_drift(2.0, 0.2)["adequate"])

    def test_a_wandering_set_point_is_not_adequate(self):
        self.assertFalse(check_set_point_drift(2.0, 1.8)["adequate"])

    def test_zero_drift_is_accepted(self):
        self.assertTrue(check_set_point_drift(2.0, 0.0)["adequate"])

    def test_negative_drift_raises(self):
        with self.assertRaises(ValueError):
            check_set_point_drift(2.0, -0.1)


class TestGuardBand(unittest.TestCase):
    def test_a_comfortable_ratio_leaves_the_limits_alone(self):
        band = tolerance_band(25.0, 2.0, 2.0)
        guard = guard_banded_limits(band, 0.2)
        self.assertFalse(guard["applied"])
        self.assertAlmostEqual(guard["accept_upper"], 27.0, places=9)

    def test_the_guard_band_threshold_itself_is_comfortable(self):
        band = tolerance_band(25.0, 2.0, 2.0)
        guard = guard_banded_limits(band, 2.0 / GUARD_BAND_RATIO)
        self.assertFalse(guard["applied"])

    def test_a_marginal_ratio_shrinks_the_window(self):
        band = tolerance_band(25.0, 2.0, 2.0)
        guard = guard_banded_limits(band, 0.6)
        self.assertTrue(guard["applied"])
        self.assertAlmostEqual(guard["accept_upper"], 26.4, places=9)
        self.assertAlmostEqual(guard["accept_lower"], 23.6, places=9)

    def test_an_uncertainty_beyond_the_band_collapses_the_window(self):
        band = tolerance_band(25.0, 0.2, 0.2)
        guard = guard_banded_limits(band, 0.3)
        self.assertTrue(guard["collapsed"])

    def test_an_uncertainty_equal_to_the_band_does_not_collapse_it(self):
        band = tolerance_band(25.0, 0.2, 0.2)
        guard = guard_banded_limits(band, 0.2)
        self.assertFalse(guard["collapsed"])

    def test_band_without_required_keys_raises(self):
        with self.assertRaises(ValueError):
            guard_banded_limits({"nominal": 25.0}, 0.2)

    def test_band_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            guard_banded_limits("25 +/- 2", 0.2)


class TestEvaluateTestParameter(unittest.TestCase):
    def test_a_well_instrumented_parameter_is_acceptable(self):
        record = evaluate_test_parameter(good_parameter())
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["findings"], [])

    def test_a_coarse_instrument_raises_a_precision_finding(self):
        record = evaluate_test_parameter(
            good_parameter(instrument_uncertainty=1.5, set_point_drift=0.0)
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("instrument-precision-insufficient", codes)

    def test_a_coarse_display_raises_a_resolution_finding(self):
        record = evaluate_test_parameter(good_parameter(reading_resolution=1.0))
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("reading-resolution-too-coarse", codes)

    def test_a_wandering_set_point_raises_a_drift_finding(self):
        record = evaluate_test_parameter(good_parameter(set_point_drift=1.9))
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("set-point-drift-excessive", codes)

    def test_a_measured_parameter_needs_no_drift_declaration(self):
        parameter = good_parameter(role="measured")
        del parameter["set_point_drift"]
        record = evaluate_test_parameter(parameter)
        self.assertNotIn("drift", record["checks"])
        self.assertTrue(record["acceptable"])

    def test_a_measured_parameter_declaring_drift_raises(self):
        with self.assertRaises(ValueError):
            evaluate_test_parameter(good_parameter(role="measured"))

    def test_unknown_key_raises(self):
        parameter = good_parameter()
        parameter["calibration_due"] = "2026-12-01"
        with self.assertRaises(ValueError):
            evaluate_test_parameter(parameter)

    def test_missing_required_key_raises(self):
        parameter = good_parameter()
        del parameter["instrument_uncertainty"]
        with self.assertRaises(ValueError):
            evaluate_test_parameter(parameter)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_test_parameter(good_parameter(id="   "))

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            evaluate_test_parameter(good_parameter(role="monitored"))

    def test_parameter_that_is_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            evaluate_test_parameter(["TP-CELL-TEMP"])

    def test_findings_carry_code_subject_and_detail(self):
        record = evaluate_test_parameter(
            good_parameter(instrument_uncertainty=1.5, set_point_drift=0.0)
        )
        for finding in record["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


class TestAssessTestInstrumentation(unittest.TestCase):
    def test_a_sound_list_is_accepted(self):
        report = assess_test_instrumentation(instrumentation_list())
        self.assertTrue(report["accepted"])
        self.assertEqual(report["verdict"], "instrumentation-adequate")

    def test_role_counts_are_reported(self):
        report = assess_test_instrumentation(instrumentation_list())
        self.assertEqual(report["controlled_count"], 1)
        self.assertEqual(report["measured_count"], 1)

    def test_one_bad_parameter_rejects_the_list(self):
        parameters = instrumentation_list()
        parameters[1]["instrument_uncertainty"] = 20.0
        report = assess_test_instrumentation(parameters)
        self.assertFalse(report["accepted"])
        self.assertEqual(report["verdict"], "instrumentation-inadequate")

    def test_conforming_fraction_counts_parameters_not_findings(self):
        parameters = instrumentation_list()
        parameters[1]["instrument_uncertainty"] = 20.0
        report = assess_test_instrumentation(parameters)
        self.assertAlmostEqual(report["conforming_fraction"], 0.5, places=9)

    def test_guard_banded_parameters_are_named(self):
        parameters = instrumentation_list()
        parameters[0]["instrument_uncertainty"] = 0.6
        report = assess_test_instrumentation(parameters)
        self.assertIn("TP-CELL-TEMP", report["guard_banded"])

    def test_duplicate_identifier_raises(self):
        parameters = instrumentation_list()
        parameters[1]["id"] = "TP-CELL-TEMP"
        with self.assertRaises(ValueError):
            assess_test_instrumentation(parameters)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            assess_test_instrumentation([])

    def test_string_list_raises(self):
        with self.assertRaises(ValueError):
            assess_test_instrumentation("TP-CELL-TEMP")


if __name__ == "__main__":
    unittest.main()

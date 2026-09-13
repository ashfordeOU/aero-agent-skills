"""Contract tests for the clause 6.4.3.5.2 pre-irradiation baseline logic."""

import unittest

from e2008_sca_spectral_response_process_logic import (
    DEFAULT_REFERENCE_IRRADIANCE_W_M2,
    DEFAULT_REFERENCE_TEMPERATURE_C,
    MAX_IRRADIANCE_DEVIATION_FRACTION,
    MAX_TEMPERATURE_DEVIATION_C,
    assess_spectral_response_baseline,
    conditions_correctable,
    correct_short_circuit_current_a,
    corrected_reference_current_a,
    evaluate_sample,
    irradiance_deviation_fraction,
    ratio_within_band,
    response_ratio,
    temperature_deviation_c,
    validate_reference_device,
)

BAND = {"ratio_min": 0.95, "ratio_max": 1.05}


def _reference(**overrides):
    device = {
        "id": "REF-AM0-01",
        "isc_a": 0.500,
        "irradiance_w_m2": DEFAULT_REFERENCE_IRRADIANCE_W_M2,
        "temperature_c": DEFAULT_REFERENCE_TEMPERATURE_C,
        "alpha_per_c": 0.0005,
        "calibration_age_days": 120,
        "calibration_interval_days": 365,
        "traceable": True,
    }
    device.update(overrides)
    return device


def _sample(sample_id="SCA-01", isc_a=0.500, **overrides):
    sample = {
        "id": sample_id,
        "isc_a": isc_a,
        "irradiance_w_m2": DEFAULT_REFERENCE_IRRADIANCE_W_M2,
        "temperature_c": DEFAULT_REFERENCE_TEMPERATURE_C,
        "alpha_per_c": 0.0005,
        "before_irradiation": True,
    }
    sample.update(overrides)
    return sample


def _spec(**overrides):
    spec = {
        "reference": _reference(),
        "samples": [_sample("SCA-01", 0.500), _sample("SCA-02", 0.505)],
        "band": dict(BAND),
        "planned_irradiation_ids": ["SCA-01", "SCA-02"],
    }
    spec.update(overrides)
    return spec


class CurrentCorrectionTests(unittest.TestCase):
    def test_reading_at_reference_conditions_is_unchanged(self):
        corrected = correct_short_circuit_current_a(
            0.5, DEFAULT_REFERENCE_IRRADIANCE_W_M2, DEFAULT_REFERENCE_TEMPERATURE_C, 0.0005
        )
        self.assertAlmostEqual(corrected, 0.5, places=9)

    def test_current_scales_inversely_with_bench_irradiance(self):
        corrected = correct_short_circuit_current_a(
            0.25,
            DEFAULT_REFERENCE_IRRADIANCE_W_M2 / 2.0,
            DEFAULT_REFERENCE_TEMPERATURE_C,
            0.0,
        )
        self.assertAlmostEqual(corrected, 0.5, places=9)

    def test_hot_reading_is_corrected_downwards(self):
        hot = correct_short_circuit_current_a(
            0.51, DEFAULT_REFERENCE_IRRADIANCE_W_M2, 45.0, 0.0005
        )
        self.assertAlmostEqual(hot, 0.51 / (1.0 + 0.0005 * 20.0), places=9)

    def test_correction_factor_driven_non_positive_is_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_a(
                0.5, DEFAULT_REFERENCE_IRRADIANCE_W_M2, -2000.0, 0.0005
            )

    def test_zero_irradiance_is_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_a(0.5, 0.0, 25.0, 0.0005)

    def test_boolean_current_is_rejected(self):
        with self.assertRaises(ValueError):
            correct_short_circuit_current_a(True, 1367.0, 25.0, 0.0005)


class ConditionWindowTests(unittest.TestCase):
    def test_deviation_fraction_is_zero_at_reference(self):
        self.assertAlmostEqual(
            irradiance_deviation_fraction(DEFAULT_REFERENCE_IRRADIANCE_W_M2),
            0.0,
            places=9,
        )

    def test_temperature_deviation_is_signless(self):
        self.assertAlmostEqual(temperature_deviation_c(5.0), 20.0, places=9)
        self.assertAlmostEqual(temperature_deviation_c(45.0), 20.0, places=9)

    def test_reading_exactly_on_the_temperature_edge_is_correctable(self):
        edge = DEFAULT_REFERENCE_TEMPERATURE_C + MAX_TEMPERATURE_DEVIATION_C
        self.assertTrue(
            conditions_correctable(DEFAULT_REFERENCE_IRRADIANCE_W_M2, edge)
        )

    def test_reading_far_off_irradiance_is_not_correctable(self):
        far = DEFAULT_REFERENCE_IRRADIANCE_W_M2 * (
            1.0 + 2.0 * MAX_IRRADIANCE_DEVIATION_FRACTION
        )
        self.assertFalse(conditions_correctable(far, DEFAULT_REFERENCE_TEMPERATURE_C))


class RatioBandTests(unittest.TestCase):
    def test_ratio_is_the_quotient_of_the_two_corrected_currents(self):
        self.assertAlmostEqual(response_ratio(0.51, 0.50), 1.02, places=9)

    def test_value_exactly_on_the_lower_edge_is_inside_the_band(self):
        self.assertTrue(ratio_within_band(0.95, 0.95, 1.05))

    def test_value_exactly_on_the_upper_edge_is_inside_the_band(self):
        self.assertTrue(ratio_within_band(1.05, 0.95, 1.05))

    def test_value_below_the_band_is_outside(self):
        self.assertFalse(ratio_within_band(0.80, 0.95, 1.05))

    def test_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            ratio_within_band(1.0, 1.05, 0.95)


class ReferenceDeviceTests(unittest.TestCase):
    def test_in_calibration_reference_raises_no_finding(self):
        device, findings = validate_reference_device(_reference())
        self.assertEqual(findings, [])
        self.assertAlmostEqual(corrected_reference_current_a(device), 0.5, places=9)

    def test_lapsed_calibration_is_a_finding(self):
        _, findings = validate_reference_device(
            _reference(calibration_age_days=400)
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("interval", findings[0])

    def test_untraceable_reference_is_a_finding(self):
        _, findings = validate_reference_device(_reference(traceable=False))
        self.assertTrue(any("traceable" in item for item in findings))

    def test_reference_read_outside_the_window_is_a_finding(self):
        _, findings = validate_reference_device(_reference(temperature_c=90.0))
        self.assertTrue(any("window" in item for item in findings))

    def test_missing_reference_key_is_rejected(self):
        device = _reference()
        del device["alpha_per_c"]
        with self.assertRaises(ValueError):
            validate_reference_device(device)

    def test_empty_reference_id_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_reference_device(_reference(id="   "))

    def test_zero_calibration_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_reference_device(_reference(calibration_interval_days=0))


class SampleEvaluationTests(unittest.TestCase):
    def test_matching_sample_conforms(self):
        record = evaluate_sample(_sample(), 0.5, BAND)
        self.assertTrue(record["conforms"])
        self.assertAlmostEqual(record["response_ratio"], 1.0, places=9)

    def test_weak_sample_is_reported_outside_the_band(self):
        record = evaluate_sample(_sample(isc_a=0.40), 0.5, BAND)
        self.assertFalse(record["within_band"])
        self.assertFalse(record["conforms"])

    def test_post_exposure_reading_is_not_a_baseline(self):
        record = evaluate_sample(_sample(before_irradiation=False), 0.5, BAND)
        self.assertFalse(record["conforms"])
        self.assertTrue(
            any("pre-irradiation" in item for item in record["findings"])
        )

    def test_non_boolean_exposure_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample(_sample(before_irradiation="yes"), 0.5, BAND)


class BaselineAssessmentTests(unittest.TestCase):
    def test_clean_campaign_baseline_is_valid(self):
        result = assess_spectral_response_baseline(_spec())
        self.assertTrue(result["valid"])
        self.assertEqual(result["samples_read"], 2)
        self.assertEqual(result["samples_within_band"], 2)
        self.assertEqual(result["baseline_missing_ids"], [])

    def test_planned_sample_never_read_is_reported(self):
        result = assess_spectral_response_baseline(
            _spec(planned_irradiation_ids=["SCA-01", "SCA-02", "SCA-09"])
        )
        self.assertEqual(result["baseline_missing_ids"], ["SCA-09"])
        self.assertFalse(result["valid"])

    def test_out_of_band_sample_is_counted(self):
        result = assess_spectral_response_baseline(
            _spec(samples=[_sample("SCA-01", 0.500), _sample("SCA-02", 0.300)])
        )
        self.assertEqual(result["samples_outside_band"], 1)
        self.assertFalse(result["valid"])

    def test_duplicate_sample_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_spectral_response_baseline(
                _spec(samples=[_sample("SCA-01"), _sample("SCA-01")])
            )

    def test_empty_sample_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_spectral_response_baseline(_spec(samples=[]))

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_spectral_response_baseline(["reference"])

    def test_planned_ids_default_to_empty(self):
        spec = _spec()
        del spec["planned_irradiation_ids"]
        result = assess_spectral_response_baseline(spec)
        self.assertEqual(result["baseline_missing_ids"], [])
        self.assertTrue(result["valid"])

    def test_lapsed_reference_invalidates_an_otherwise_clean_campaign(self):
        result = assess_spectral_response_baseline(
            _spec(reference=_reference(calibration_age_days=1000))
        )
        self.assertFalse(result["valid"])
        self.assertEqual(result["samples_within_band"], 2)


if __name__ == "__main__":
    unittest.main()

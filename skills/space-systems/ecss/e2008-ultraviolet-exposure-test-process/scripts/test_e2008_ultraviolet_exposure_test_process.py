"""Contract tests for the clause 6.4.3.15.2 ultraviolet intensity process logic."""

import unittest

from e2008_ultraviolet_exposure_test_process_logic import (
    DEFAULT_RADIOMETRY_POLICY,
    INTENSITY_NOT_MEASURED,
    INTENSITY_RECORD_DEFICIENT,
    INTENSITY_RECORD_TRACEABLE,
    PLANCK_CONSTANT_J_S,
    SECONDS_PER_HOUR,
    SPEED_OF_LIGHT_M_S,
    accumulated_dose_j_m2,
    assess_intensity_measurement,
    band_irradiance_w_m2,
    band_photon_flux_per_m2_s,
    beam_non_uniformity,
    calibration_in_date,
    equivalent_sun_hours,
    integrated_photon_fluence_per_m2,
    position_correction_factor,
    sampling_adequate,
    sensor_at_item_position,
    validate_radiometry_policy,
)

# A flat 0.5 W/m2/nm lamp spectrum spanning past the reported band.
FLAT_SPECTRUM = ((190.0, 0.5), (410.0, 0.5))

# A linear ramp, so that band-edge interpolation is visible in the answer.
RAMP_SPECTRUM = ((100.0, 0.0), (500.0, 4.0))

HC_J_M = PLANCK_CONSTANT_J_S * SPEED_OF_LIGHT_M_S


def _policy(**overrides):
    policy = dict(DEFAULT_RADIOMETRY_POLICY)
    policy.update(overrides)
    return policy


def _measurement(**overrides):
    measurement = {
        "spectrum": FLAT_SPECTRUM,
        "sensor_distance_mm": 500.0,
        "item_distance_mm": 500.0,
        "tilt_deg": 0.0,
        "item_plane_readings": (100.0, 98.0, 99.0, 101.0),
        "days_since_calibration": 120.0,
        "sample_count": 48,
    }
    measurement.update(overrides)
    return measurement


def _case(**overrides):
    case = {"duration_s": 360000.0, "measurement": _measurement()}
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_radiometry_policy(DEFAULT_RADIOMETRY_POLICY),
            DEFAULT_RADIOMETRY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiometry_policy("200 to 400 nm")

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiometry_policy(_policy(band_low_nm=400.0, band_high_nm=200.0))

    def test_edge_on_tilt_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiometry_policy(_policy(max_tilt_deg=90.0))

    def test_a_non_uniformity_allowance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiometry_policy(_policy(max_non_uniformity=1.0))

    def test_zero_calibration_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiometry_policy(_policy(calibration_interval_days=0.0))

    def test_fractional_minimum_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_radiometry_policy(_policy(min_samples_per_exposure=24.5))


class BandIntegrationTests(unittest.TestCase):
    def test_a_flat_spectrum_integrates_to_irradiance_times_band_width(self):
        self.assertAlmostEqual(
            _ratio(band_irradiance_w_m2(FLAT_SPECTRUM, 200.0, 400.0), 100.0),
            1.0,
            places=12,
        )

    def test_band_edges_are_interpolated_not_snapped_to_a_sample(self):
        # E(200) = 1.0, E(400) = 3.0, so the band holds 400 W/m2; snapping the
        # edges out to the sampled span would report 800.
        self.assertAlmostEqual(
            _ratio(band_irradiance_w_m2(RAMP_SPECTRUM, 200.0, 400.0), 400.0),
            1.0,
            places=12,
        )

    def test_a_narrower_band_holds_less_of_a_flat_spectrum(self):
        whole = band_irradiance_w_m2(FLAT_SPECTRUM, 200.0, 400.0)
        half = band_irradiance_w_m2(FLAT_SPECTRUM, 200.0, 300.0)
        self.assertAlmostEqual(_ratio(whole, 2.0 * half), 1.0, places=12)

    def test_photon_flux_matches_the_analytic_flat_band_value(self):
        expected = 0.5 * 1.0e-9 * (400.0 * 400.0 - 200.0 * 200.0) / 2.0 / HC_J_M
        self.assertAlmostEqual(
            _ratio(band_photon_flux_per_m2_s(FLAT_SPECTRUM, 200.0, 400.0), expected),
            1.0,
            places=12,
        )

    def test_the_same_watts_carry_more_photons_at_longer_wavelengths(self):
        blue = band_photon_flux_per_m2_s(FLAT_SPECTRUM, 200.0, 300.0)
        near = band_photon_flux_per_m2_s(FLAT_SPECTRUM, 300.0, 400.0)
        self.assertGreater(near, blue)

    def test_a_spectrum_short_of_the_band_rejected(self):
        with self.assertRaises(ValueError):
            band_irradiance_w_m2(((250.0, 0.5), (410.0, 0.5)), 200.0, 400.0)

    def test_non_increasing_wavelengths_rejected(self):
        with self.assertRaises(ValueError):
            band_irradiance_w_m2(((190.0, 0.5), (190.0, 0.5)), 200.0, 400.0)

    def test_a_malformed_spectral_sample_rejected(self):
        with self.assertRaises(ValueError):
            band_irradiance_w_m2(((190.0, 0.5), (410.0,)), 200.0, 400.0)

    def test_a_single_sample_spectrum_rejected(self):
        with self.assertRaises(ValueError):
            band_irradiance_w_m2(((190.0, 0.5),), 200.0, 400.0)

    def test_negative_spectral_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            band_irradiance_w_m2(((190.0, -0.5), (410.0, 0.5)), 200.0, 400.0)

    def test_an_inverted_band_rejected_by_the_integrator(self):
        with self.assertRaises(ValueError):
            band_irradiance_w_m2(FLAT_SPECTRUM, 400.0, 200.0)


class DoseTests(unittest.TestCase):
    def test_accumulated_dose_is_irradiance_times_seconds(self):
        self.assertAlmostEqual(
            _ratio(accumulated_dose_j_m2(100.0, 360000.0), 3.6e7), 1.0, places=12
        )

    def test_one_ultraviolet_sun_for_one_hour_is_one_equivalent_sun_hour(self):
        value = equivalent_sun_hours(
            DEFAULT_RADIOMETRY_POLICY["ultraviolet_sun_irradiance_w_m2"],
            SECONDS_PER_HOUR,
            DEFAULT_RADIOMETRY_POLICY,
        )
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_equivalent_sun_hours_scale_with_the_exposure(self):
        short = equivalent_sun_hours(100.0, 3600.0, DEFAULT_RADIOMETRY_POLICY)
        long_run = equivalent_sun_hours(100.0, 7200.0, DEFAULT_RADIOMETRY_POLICY)
        self.assertAlmostEqual(_ratio(long_run, 2.0 * short), 1.0, places=12)

    def test_photon_fluence_is_flux_times_seconds(self):
        self.assertAlmostEqual(
            _ratio(integrated_photon_fluence_per_m2(2.0e19, 100.0), 2.0e21),
            1.0,
            places=12,
        )

    def test_zero_duration_rejected_by_the_fluence(self):
        with self.assertRaises(ValueError):
            integrated_photon_fluence_per_m2(2.0e19, 0.0)

    def test_zero_irradiance_rejected_by_the_dose(self):
        with self.assertRaises(ValueError):
            accumulated_dose_j_m2(0.0, 3600.0)

    def test_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_dose_j_m2(100.0, True)


class PositionTests(unittest.TestCase):
    def test_a_co_located_sensor_needs_no_correction(self):
        self.assertAlmostEqual(
            position_correction_factor(500.0, 500.0, 0.0), 1.0, places=12
        )

    def test_doubling_the_sensor_distance_quadruples_the_factor(self):
        self.assertAlmostEqual(
            _ratio(position_correction_factor(1000.0, 500.0, 0.0), 4.0),
            1.0,
            places=12,
        )

    def test_a_sixty_degree_tilt_halves_the_factor(self):
        self.assertAlmostEqual(
            position_correction_factor(500.0, 500.0, 60.0), 0.5, places=9
        )

    def test_an_edge_on_tilt_rejected(self):
        with self.assertRaises(ValueError):
            position_correction_factor(500.0, 500.0, 90.0)

    def test_zero_item_distance_rejected(self):
        with self.assertRaises(ValueError):
            position_correction_factor(500.0, 0.0, 0.0)

    def test_a_sensor_on_the_item_plane_passes_the_position_check(self):
        self.assertTrue(sensor_at_item_position(0.0, 0.0, _policy()))

    def test_a_sensor_exactly_at_the_offset_allowance_passes(self):
        policy = _policy()
        self.assertAlmostEqual(10.0, policy["max_position_offset_mm"], places=9)
        self.assertTrue(sensor_at_item_position(10.0, 0.0, policy))

    def test_a_sensor_past_the_offset_allowance_fails(self):
        self.assertFalse(sensor_at_item_position(100.0, 0.0, _policy()))

    def test_a_tilt_past_the_allowance_fails(self):
        self.assertFalse(sensor_at_item_position(0.0, 30.0, _policy()))


class ProvenanceTests(unittest.TestCase):
    def test_a_flat_beam_has_no_non_uniformity(self):
        self.assertAlmostEqual(beam_non_uniformity((100.0, 100.0, 100.0)), 0.0, places=12)

    def test_non_uniformity_is_the_spread_over_the_sum_of_the_extremes(self):
        self.assertAlmostEqual(
            _ratio(beam_non_uniformity((100.0, 50.0)), 50.0 / 150.0), 1.0, places=12
        )

    def test_a_single_item_plane_reading_rejected(self):
        with self.assertRaises(ValueError):
            beam_non_uniformity((100.0,))

    def test_a_zero_item_plane_reading_rejected(self):
        with self.assertRaises(ValueError):
            beam_non_uniformity((100.0, 0.0))

    def test_a_calibration_exactly_at_the_interval_is_in_date(self):
        policy = _policy()
        self.assertTrue(
            calibration_in_date(policy["calibration_interval_days"], policy)
        )

    def test_a_calibration_past_the_interval_is_not_in_date(self):
        self.assertFalse(calibration_in_date(400.0, _policy()))

    def test_a_sample_count_exactly_at_the_floor_is_adequate(self):
        policy = _policy()
        self.assertTrue(
            sampling_adequate(int(policy["min_samples_per_exposure"]), policy)
        )

    def test_a_sample_count_below_the_floor_is_not_adequate(self):
        self.assertFalse(sampling_adequate(4, _policy()))

    def test_a_fractional_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sampling_adequate(24.5, _policy())


class AssessmentTests(unittest.TestCase):
    def test_a_complete_record_is_traceable(self):
        result = assess_intensity_measurement(_case())
        self.assertEqual(result["verdict"], INTENSITY_RECORD_TRACEABLE)
        self.assertEqual(result["findings"], [])

    def test_the_band_irradiance_is_reported(self):
        result = assess_intensity_measurement(_case())
        self.assertAlmostEqual(
            _ratio(result["sensor_irradiance_w_m2"], 100.0), 1.0, places=12
        )

    def test_a_co_located_sensor_reading_stands_as_the_item_plane_value(self):
        result = assess_intensity_measurement(_case())
        self.assertAlmostEqual(
            _ratio(
                result["item_plane_irradiance_w_m2"],
                result["sensor_irradiance_w_m2"],
            ),
            1.0,
            places=12,
        )

    def test_the_accumulated_dose_is_reported(self):
        result = assess_intensity_measurement(_case())
        self.assertAlmostEqual(
            _ratio(result["accumulated_dose_j_m2"], 3.6e7), 1.0, places=12
        )

    def test_the_integrated_photon_fluence_is_the_flux_over_the_exposure(self):
        result = assess_intensity_measurement(_case())
        self.assertAlmostEqual(
            _ratio(
                result["integrated_photon_fluence_per_m2"],
                result["photon_flux_per_m2_s"] * 360000.0,
            ),
            1.0,
            places=12,
        )

    def test_the_equivalent_sun_hours_follow_the_dose(self):
        result = assess_intensity_measurement(_case())
        expected = 3.6e7 / (
            DEFAULT_RADIOMETRY_POLICY["ultraviolet_sun_irradiance_w_m2"]
            * SECONDS_PER_HOUR
        )
        self.assertAlmostEqual(
            _ratio(result["equivalent_sun_hours"], expected), 1.0, places=12
        )

    def test_an_unmeasured_exposure_is_its_own_verdict(self):
        case = _case()
        del case["measurement"]
        result = assess_intensity_measurement(case)
        self.assertEqual(result["verdict"], INTENSITY_NOT_MEASURED)
        self.assertIsNone(result["item_plane_irradiance_w_m2"])

    def test_an_off_position_sensor_is_deficient(self):
        result = assess_intensity_measurement(
            _case(measurement=_measurement(sensor_distance_mm=600.0))
        )
        self.assertEqual(result["verdict"], INTENSITY_RECORD_DEFICIENT)
        self.assertFalse(result["sensor_at_item_position"])
        self.assertEqual(len(result["findings"]), 1)

    def test_an_off_position_reading_is_still_referred_to_the_item_plane(self):
        result = assess_intensity_measurement(
            _case(measurement=_measurement(sensor_distance_mm=1000.0))
        )
        self.assertAlmostEqual(
            _ratio(result["position_correction_factor"], 4.0), 1.0, places=12
        )

    def test_a_non_uniform_beam_is_deficient(self):
        result = assess_intensity_measurement(
            _case(measurement=_measurement(item_plane_readings=(100.0, 50.0)))
        )
        self.assertEqual(result["verdict"], INTENSITY_RECORD_DEFICIENT)
        self.assertEqual(len(result["findings"]), 1)

    def test_an_out_of_date_calibration_is_deficient(self):
        result = assess_intensity_measurement(
            _case(measurement=_measurement(days_since_calibration=400.0))
        )
        self.assertEqual(result["verdict"], INTENSITY_RECORD_DEFICIENT)
        self.assertFalse(result["calibration_in_date"])

    def test_an_under_sampled_exposure_is_deficient(self):
        result = assess_intensity_measurement(
            _case(measurement=_measurement(sample_count=4))
        )
        self.assertEqual(result["verdict"], INTENSITY_RECORD_DEFICIENT)
        self.assertFalse(result["sampling_adequate"])

    def test_every_deficiency_is_reported_not_only_the_first(self):
        result = assess_intensity_measurement(
            _case(
                measurement=_measurement(
                    sensor_distance_mm=600.0,
                    item_plane_readings=(100.0, 50.0),
                    days_since_calibration=400.0,
                    sample_count=4,
                )
            )
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_a_measurement_without_a_spectrum_rejected(self):
        measurement = _measurement()
        del measurement["spectrum"]
        with self.assertRaises(ValueError):
            assess_intensity_measurement(_case(measurement=measurement))

    def test_a_measurement_without_item_plane_readings_rejected(self):
        measurement = _measurement()
        del measurement["item_plane_readings"]
        with self.assertRaises(ValueError):
            assess_intensity_measurement(_case(measurement=measurement))

    def test_a_missing_exposure_duration_rejected(self):
        case = _case()
        del case["duration_s"]
        with self.assertRaises(ValueError):
            assess_intensity_measurement(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_intensity_measurement(["duration_s"])

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_intensity_measurement(_case(measurement=[100.0]))


if __name__ == "__main__":
    unittest.main()

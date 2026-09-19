"""Contract tests for the clause 5.6.11.1 Doppler shift and rate logic."""

import unittest

from e50_doppler_shift_and_doppler_rate_logic import (
    RATE_EXCEEDS_TRACKING,
    SHIFT_EXCEEDS_ACQUISITION,
    WITHIN_CAPABILITY,
    assess_doppler,
    doppler_rate_hz_s,
    doppler_shift_hz,
    max_radial_acceleration_m_s2,
    max_radial_velocity_m_s,
    oscillator_uncertainty_hz,
    required_sweep_range_hz,
    sweep_dwell_time_s,
    total_uncertainty_hz,
    validate_acceleration_m_s2,
    validate_frequency_hz,
    validate_ppm,
    validate_speed_m_s,
)

# A carrier whose wavelength is one metre: one hertz of Doppler per metre per
# second of radial motion, so every expectation below is an exact figure that
# was not produced by the code under test.
UNIT_CARRIER_HZ = 299792458.0
S_BAND_HZ = 2000000000.0
CLOSING_M_S = -7500.0
CLOSING_ACCEL_M_S2 = -20.0
ACQ_HZ = 10000.0
TRACK_HZ_S = 50.0


class ValidationTests(unittest.TestCase):
    def test_zero_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency_hz(0.0)

    def test_negative_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency_hz(-2000000000.0)

    def test_boolean_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency_hz(True)

    def test_text_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency_hz("2.2e9")

    def test_infinite_carrier_rejected(self):
        with self.assertRaises(ValueError):
            validate_frequency_hz(float("inf"))

    def test_superluminal_velocity_rejected(self):
        with self.assertRaises(ValueError):
            validate_speed_m_s(300000000.0)

    def test_negative_velocity_accepted_as_closing(self):
        self.assertAlmostEqual(validate_speed_m_s(-7500.0), -7500.0, places=9)

    def test_nan_acceleration_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceleration_m_s2(float("nan"))

    def test_negative_acceleration_accepted(self):
        self.assertAlmostEqual(validate_acceleration_m_s2(-20.0), -20.0, places=9)

    def test_negative_stability_rejected(self):
        with self.assertRaises(ValueError):
            validate_ppm(-1.0)

    def test_zero_stability_accepted(self):
        self.assertAlmostEqual(validate_ppm(0), 0.0, places=9)


class ShiftTests(unittest.TestCase):
    def test_closing_motion_raises_the_carrier(self):
        self.assertAlmostEqual(doppler_shift_hz(UNIT_CARRIER_HZ, CLOSING_M_S), 7500.0, places=6)

    def test_opening_motion_lowers_the_carrier(self):
        self.assertAlmostEqual(doppler_shift_hz(UNIT_CARRIER_HZ, 7500.0), -7500.0, places=6)

    def test_no_radial_motion_shifts_nothing(self):
        self.assertAlmostEqual(doppler_shift_hz(S_BAND_HZ, 0.0), 0.0, places=9)

    def test_shift_scales_with_the_carrier(self):
        low = doppler_shift_hz(S_BAND_HZ, CLOSING_M_S)
        high = doppler_shift_hz(2.0 * S_BAND_HZ, CLOSING_M_S)
        self.assertAlmostEqual(high, 2.0 * low, places=6)

    def test_shift_scales_with_the_velocity(self):
        slow = doppler_shift_hz(S_BAND_HZ, CLOSING_M_S)
        fast = doppler_shift_hz(S_BAND_HZ, 2.0 * CLOSING_M_S)
        self.assertAlmostEqual(fast, 2.0 * slow, places=6)


class RateTests(unittest.TestCase):
    def test_closing_acceleration_gives_a_rising_rate(self):
        self.assertAlmostEqual(
            doppler_rate_hz_s(UNIT_CARRIER_HZ, CLOSING_ACCEL_M_S2), 20.0, places=6
        )

    def test_opening_acceleration_gives_a_falling_rate(self):
        self.assertAlmostEqual(doppler_rate_hz_s(UNIT_CARRIER_HZ, 20.0), -20.0, places=6)

    def test_no_radial_acceleration_gives_no_rate(self):
        self.assertAlmostEqual(doppler_rate_hz_s(S_BAND_HZ, 0.0), 0.0, places=9)

    def test_rate_scales_with_the_carrier(self):
        low = doppler_rate_hz_s(S_BAND_HZ, CLOSING_ACCEL_M_S2)
        high = doppler_rate_hz_s(3.0 * S_BAND_HZ, CLOSING_ACCEL_M_S2)
        self.assertAlmostEqual(high, 3.0 * low, places=6)


class UncertaintyTests(unittest.TestCase):
    def test_one_part_per_million_of_two_gigahertz(self):
        self.assertAlmostEqual(oscillator_uncertainty_hz(S_BAND_HZ, 1.0), 2000.0, places=6)

    def test_a_perfect_reference_contributes_nothing(self):
        self.assertAlmostEqual(oscillator_uncertainty_hz(S_BAND_HZ, 0.0), 0.0, places=9)

    def test_doppler_and_reference_error_add(self):
        self.assertAlmostEqual(
            total_uncertainty_hz(UNIT_CARRIER_HZ, CLOSING_M_S, 1.0), 7799.792458, places=6
        )

    def test_uncertainty_ignores_the_sign_of_the_motion(self):
        closing = total_uncertainty_hz(UNIT_CARRIER_HZ, CLOSING_M_S, 0.0)
        opening = total_uncertainty_hz(UNIT_CARRIER_HZ, -CLOSING_M_S, 0.0)
        self.assertAlmostEqual(closing, opening, places=6)

    def test_sweep_spans_both_sides_of_nominal(self):
        self.assertAlmostEqual(
            required_sweep_range_hz(UNIT_CARRIER_HZ, CLOSING_M_S, 0.0), 15000.0, places=6
        )

    def test_sweep_dwell_is_span_over_rate(self):
        self.assertAlmostEqual(sweep_dwell_time_s(15000.0, 5000.0), 3.0, places=9)

    def test_zero_sweep_rate_rejected(self):
        with self.assertRaises(ValueError):
            sweep_dwell_time_s(15000.0, 0.0)

    def test_negative_sweep_span_rejected(self):
        with self.assertRaises(ValueError):
            sweep_dwell_time_s(-1.0, 5000.0)


class InverseTests(unittest.TestCase):
    def test_velocity_that_fills_the_acquisition_range(self):
        self.assertAlmostEqual(
            max_radial_velocity_m_s(UNIT_CARRIER_HZ, ACQ_HZ, 0.0), 10000.0, places=6
        )

    def test_reference_error_eats_into_the_tolerable_velocity(self):
        self.assertAlmostEqual(
            max_radial_velocity_m_s(UNIT_CARRIER_HZ, ACQ_HZ, 1.0), 9700.207542, places=6
        )

    def test_reference_error_alone_can_fill_the_range(self):
        self.assertAlmostEqual(
            max_radial_velocity_m_s(UNIT_CARRIER_HZ, 100.0, 1.0), 0.0, places=9
        )

    def test_acceleration_the_loop_can_just_follow(self):
        self.assertAlmostEqual(
            max_radial_acceleration_m_s2(UNIT_CARRIER_HZ, TRACK_HZ_S), 50.0, places=6
        )

    def test_zero_acquisition_range_rejected(self):
        with self.assertRaises(ValueError):
            max_radial_velocity_m_s(UNIT_CARRIER_HZ, 0.0)

    def test_zero_tracking_rate_rejected(self):
        with self.assertRaises(ValueError):
            max_radial_acceleration_m_s2(UNIT_CARRIER_HZ, 0.0)


class AssessTests(unittest.TestCase):
    def test_geometry_inside_both_limits_passes(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        self.assertEqual(result["verdict"], WITHIN_CAPABILITY)
        self.assertTrue(result["shift_within_acquisition"])
        self.assertTrue(result["rate_within_tracking"])

    def test_offset_exactly_on_the_acquisition_range_passes(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, 7500.0, TRACK_HZ_S
        )
        self.assertAlmostEqual(
            result["total_uncertainty_hz"], result["acquisition_range_hz"], places=6
        )
        self.assertEqual(result["verdict"], WITHIN_CAPABILITY)

    def test_rate_exactly_on_the_tracking_limit_passes(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, ACQ_HZ, 20.0
        )
        self.assertAlmostEqual(
            abs(result["doppler_rate_hz_s"]), result["tracking_rate_hz_s"], places=6
        )
        self.assertEqual(result["verdict"], WITHIN_CAPABILITY)

    def test_offset_beyond_the_acquisition_range_fails(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, -20000.0, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        self.assertEqual(result["verdict"], SHIFT_EXCEEDS_ACQUISITION)
        self.assertEqual(result["binding_limit"], "acquisition")

    def test_rate_beyond_the_tracking_limit_fails(self):
        result = assess_doppler(UNIT_CARRIER_HZ, -100.0, -200.0, ACQ_HZ, TRACK_HZ_S)
        self.assertEqual(result["verdict"], RATE_EXCEEDS_TRACKING)
        self.assertEqual(result["binding_limit"], "tracking")

    def test_failing_acquisition_names_the_tolerable_velocity(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, -20000.0, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        self.assertTrue(any("radial velocity" in f for f in result["findings"]))

    def test_a_poor_reference_is_called_out_over_the_doppler(self):
        result = assess_doppler(UNIT_CARRIER_HZ, -100.0, -1.0, 200.0, TRACK_HZ_S, 1.0)
        self.assertTrue(any("better reference" in f for f in result["findings"]))

    def test_failing_tracking_names_the_tolerable_acceleration(self):
        result = assess_doppler(UNIT_CARRIER_HZ, -100.0, -200.0, ACQ_HZ, TRACK_HZ_S)
        self.assertTrue(any("radial acceleration tolerated" in f for f in result["findings"]))

    def test_a_compliant_geometry_reports_no_findings(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        self.assertEqual(result["findings"], [])

    def test_binding_limit_names_the_tighter_of_two_passes(self):
        result = assess_doppler(UNIT_CARRIER_HZ, -100.0, CLOSING_ACCEL_M_S2, ACQ_HZ, 25.0)
        self.assertEqual(result["binding_limit"], "tracking")

    def test_margins_are_carried_in_the_result(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        self.assertAlmostEqual(result["acquisition_margin_hz"], 2500.0, places=6)
        self.assertAlmostEqual(result["tracking_margin_hz_s"], 30.0, places=6)

    def test_sweep_range_is_carried_in_the_result(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        self.assertAlmostEqual(result["required_sweep_range_hz"], 15000.0, places=6)

    def test_stated_tolerable_velocity_actually_fits_the_range(self):
        result = assess_doppler(
            UNIT_CARRIER_HZ, -20000.0, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
        )
        fixed = assess_doppler(
            UNIT_CARRIER_HZ,
            -result["max_radial_velocity_m_s"],
            CLOSING_ACCEL_M_S2,
            ACQ_HZ,
            TRACK_HZ_S,
        )
        self.assertTrue(fixed["shift_within_acquisition"])

    def test_stated_tolerable_acceleration_actually_fits_the_loop(self):
        result = assess_doppler(UNIT_CARRIER_HZ, -100.0, -200.0, ACQ_HZ, TRACK_HZ_S)
        fixed = assess_doppler(
            UNIT_CARRIER_HZ,
            -100.0,
            -result["max_radial_acceleration_m_s2"],
            ACQ_HZ,
            TRACK_HZ_S,
        )
        self.assertTrue(fixed["rate_within_tracking"])

    def test_zero_acquisition_range_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_doppler(UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, 0.0, TRACK_HZ_S)

    def test_zero_tracking_rate_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_doppler(UNIT_CARRIER_HZ, CLOSING_M_S, CLOSING_ACCEL_M_S2, ACQ_HZ, 0.0)

    def test_superluminal_velocity_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_doppler(
                UNIT_CARRIER_HZ, -400000000.0, CLOSING_ACCEL_M_S2, ACQ_HZ, TRACK_HZ_S
            )


if __name__ == "__main__":
    unittest.main()

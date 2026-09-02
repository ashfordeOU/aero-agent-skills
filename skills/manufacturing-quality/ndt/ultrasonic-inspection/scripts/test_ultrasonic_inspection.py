#!/usr/bin/env python3
"""Gate 3 contract test: ultrasonic inspection math.

Exercises scripts/ultrasonic_inspection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - depth from time
of flight (round trip, depth = tof * v / 2), wavelength = v / f,
near-field length N = D^2 / (4 * lambda) for a circular piston,
decibel to amplitude ratio 10^(db / 20), Snell's law refraction angle
for angle-beam probes with total-internal-reflection detection, and
far-field beam-spread half-angle sin(gamma) = 1.22 * lambda / D.

All expected values are hand-computed (see each docstring) and were
checked at authoring time.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ultrasonic_inspection_logic as uil  # noqa: E402


class TimeOfFlightToDepthTest(unittest.TestCase):
    def test_steel_50_us(self):
        # 50 us round trip at 5920 m/s: 50e-6 * 5920 / 2 = 0.148 m (148 mm).
        self.assertAlmostEqual(uil.time_of_flight_to_depth(50e-6, 5920.0), 0.148, places=6)

    def test_water_1_ms(self):
        # 1 ms round trip in water at 1480 m/s: 1e-3 * 1480 / 2 = 0.74 m.
        self.assertAlmostEqual(uil.time_of_flight_to_depth(1e-3, 1480.0), 0.74, places=6)

    def test_zero_tof_is_zero_depth(self):
        self.assertEqual(uil.time_of_flight_to_depth(0.0, 5920.0), 0.0)

    def test_negative_tof_raises(self):
        with self.assertRaises(ValueError):
            uil.time_of_flight_to_depth(-1e-6, 5920.0)

    def test_non_positive_velocity_raises(self):
        with self.assertRaises(ValueError):
            uil.time_of_flight_to_depth(50e-6, 0.0)
        with self.assertRaises(ValueError):
            uil.time_of_flight_to_depth(50e-6, -5920.0)


class WavelengthTest(unittest.TestCase):
    def test_5_mhz_steel_longitudinal(self):
        # 5920 / 5e6 = 1.184e-3 m (1.184 mm).
        self.assertAlmostEqual(uil.wavelength(5e6, 5920.0), 1.184e-3, places=9)

    def test_2_25_mhz_steel_shear(self):
        # 3230 / 2.25e6 = 1.43556e-3 m (1.436 mm).
        self.assertAlmostEqual(uil.wavelength(2.25e6, 3230.0), 1.4356e-3, places=6)

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            uil.wavelength(0.0, 5920.0)
        with self.assertRaises(ValueError):
            uil.wavelength(-5e6, 5920.0)

    def test_non_positive_velocity_raises(self):
        with self.assertRaises(ValueError):
            uil.wavelength(5e6, 0.0)


class NearFieldLengthTest(unittest.TestCase):
    def test_20_mm_diameter_1_mm_wavelength(self):
        # 0.02^2 / (4 * 0.001) = 4e-4 / 4e-3 = 0.1 m (100 mm).
        self.assertAlmostEqual(uil.near_field_length(0.02, 0.001), 0.1, places=6)

    def test_10_mm_diameter_1_mm_wavelength(self):
        # 0.01^2 / (4 * 0.001) = 1e-4 / 4e-3 = 0.025 m (25 mm).
        self.assertAlmostEqual(uil.near_field_length(0.01, 0.001), 0.025, places=6)

    def test_non_positive_diameter_raises(self):
        with self.assertRaises(ValueError):
            uil.near_field_length(0.0, 0.001)

    def test_non_positive_wavelength_raises(self):
        with self.assertRaises(ValueError):
            uil.near_field_length(0.02, 0.0)


class DbToAmplitudeRatioTest(unittest.TestCase):
    def test_6_db_is_about_double_amplitude(self):
        # 10^(6/20) = 10^0.3 = 1.995, the 6 dB drop rule (half echo = 6 dB).
        self.assertAlmostEqual(uil.db_to_amplitude_ratio(6.0), 2.0, places=2)

    def test_20_db_is_ten_times_amplitude(self):
        self.assertAlmostEqual(uil.db_to_amplitude_ratio(20.0), 10.0, places=9)

    def test_minus_6_db_is_about_half_amplitude(self):
        # 10^(-0.3) = 0.501.
        self.assertAlmostEqual(uil.db_to_amplitude_ratio(-6.0), 0.5, places=2)

    def test_40_db_is_hundred_times_amplitude(self):
        self.assertAlmostEqual(uil.db_to_amplitude_ratio(40.0), 100.0, places=9)

    def test_zero_db_is_unity(self):
        self.assertAlmostEqual(uil.db_to_amplitude_ratio(0.0), 1.0, places=9)

    def test_non_finite_db_raises(self):
        with self.assertRaises(ValueError):
            uil.db_to_amplitude_ratio(float("nan"))
        with self.assertRaises(ValueError):
            uil.db_to_amplitude_ratio(float("inf"))


class SnellRefractionAngleTest(unittest.TestCase):
    def test_same_medium_no_bend(self):
        # v2 / v1 = 1, so theta2 = theta1 = 45 degrees exactly.
        self.assertAlmostEqual(uil.snell_refraction_angle(45.0, 5920.0, 5920.0), 45.0, places=6)

    def test_plexiglas_to_steel_shear_30_deg(self):
        # sin(theta2) = 3230 / 2730 * sin(30) = 0.59158; asin = 36.27 deg.
        self.assertAlmostEqual(uil.snell_refraction_angle(30.0, 2730.0, 3230.0), 36.27, places=1)

    def test_velocity_ratio_1_5(self):
        # sin(theta2) = 1.5 * 0.5 = 0.75; asin(0.75) = 48.5904 deg.
        self.assertAlmostEqual(uil.snell_refraction_angle(30.0, 2000.0, 3000.0), 48.5904, places=2)

    def test_total_internal_reflection_raises(self):
        # 2.5 * sin(30) = 1.25 > 1: no refracted shear wave exists.
        with self.assertRaises(ValueError):
            uil.snell_refraction_angle(30.0, 2000.0, 5000.0)

    def test_out_of_range_angle_raises(self):
        with self.assertRaises(ValueError):
            uil.snell_refraction_angle(95.0, 5920.0, 3230.0)
        with self.assertRaises(ValueError):
            uil.snell_refraction_angle(-5.0, 5920.0, 3230.0)

    def test_non_positive_velocity_raises(self):
        with self.assertRaises(ValueError):
            uil.snell_refraction_angle(30.0, 0.0, 3230.0)


class BeamSpreadHalfAngleTest(unittest.TestCase):
    def test_12_2_mm_diameter_1_mm_wavelength(self):
        # sin(gamma) = 1.22 * 0.001 / 0.0122 = 0.1; asin(0.1) = 5.7392 deg.
        self.assertAlmostEqual(uil.beam_spread_half_angle(0.0122, 0.001), 5.7392, places=2)

    def test_24_4_mm_diameter_1_mm_wavelength(self):
        # sin(gamma) = 0.05; asin(0.05) = 2.8660 deg.
        self.assertAlmostEqual(uil.beam_spread_half_angle(0.0244, 0.001), 2.8660, places=2)

    def test_higher_frequency_narrows_beam(self):
        # 5 MHz vs 2.25 MHz on the same 10 mm probe in steel (longitudinal):
        # shorter wavelength, smaller half-angle.
        wide = uil.beam_spread_half_angle(0.01, uil.wavelength(2.25e6, 5920.0))
        narrow = uil.beam_spread_half_angle(0.01, uil.wavelength(5e6, 5920.0))
        self.assertLess(narrow, wide)

    def test_not_directive_raises(self):
        # 1.22 * 0.01 / 0.001 = 12.2 > 1: no directive beam.
        with self.assertRaises(ValueError):
            uil.beam_spread_half_angle(0.001, 0.01)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            uil.beam_spread_half_angle(0.0, 0.001)
        with self.assertRaises(ValueError):
            uil.beam_spread_half_angle(0.01, 0.0)


if __name__ == "__main__":
    unittest.main()

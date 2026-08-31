#!/usr/bin/env python3
"""Gate 3 contract test: inertial navigation error model.

Exercises scripts/inertial_navigation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - Schuler period
T = 2*pi*sqrt(R/g) = 5064 s = 84.4 min at the Earth surface with the
mean Earth radius 6371 km and g0 = 9.80665 m/s^2 (period scales as
sqrt(R)); Schuler frequency 1.2407e-3 rad/s; accelerometer bias
double integration (velocity b*t, position 0.5*b*t^2: 1 mg over 100 s
gives 5 m, 100 ug over 600 s gives 18 m); gyro drift cubic growth
(1/6)*g*eps*t^3: 0.01 deg/h gives 3697 m after one hour, 1 deg/h
369.7 km, navigation-grade 0.001 deg/h 369.7 m; Schuler bounded
offset b*R/g = 649.7 m per mg; Earth-rate components for
gyrocompassing (omega_e*cos(lat), omega_e*sin(lat)), 7.2921159e-5
rad/s total; angle random walk accumulates as arw*sqrt(t); invalid
inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inertial_navigation_logic as ins  # noqa: E402

OMEGA_EARTH = 7.2921159e-5
G0 = 9.80665
R_EARTH = 6371000.0


class SchulerTest(unittest.TestCase):
    def test_period_is_84_minutes(self):
        t = ins.schuler_period()
        self.assertAlmostEqual(t, 5064.4, delta=5.0)
        minutes = t / 60.0
        self.assertGreaterEqual(minutes, 84.0)
        self.assertLessEqual(minutes, 84.8)

    def test_period_scales_with_sqrt_radius(self):
        t1 = ins.schuler_period()
        t4 = ins.schuler_period(r=4.0 * R_EARTH)
        self.assertAlmostEqual(t4, 2.0 * t1, places=9)

    def test_frequency_is_two_pi_over_period(self):
        f = ins.schuler_frequency()
        self.assertAlmostEqual(f, 2.0 * math.pi / ins.schuler_period(), places=12)
        self.assertAlmostEqual(f, 1.2407e-3, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ins.schuler_period(r=0.0)
        with self.assertRaises(ValueError):
            ins.schuler_frequency(g=-9.81)


class DegPerHourConversionTest(unittest.TestCase):
    def test_one_deg_per_hour(self):
        self.assertAlmostEqual(
            ins.deg_per_hour_to_rad_s(1.0), math.pi / 180.0 / 3600.0, places=12
        )
        self.assertAlmostEqual(ins.deg_per_hour_to_rad_s(1.0), 4.8481e-6, places=9)

    def test_zero_drift(self):
        self.assertEqual(ins.deg_per_hour_to_rad_s(0.0), 0.0)

    def test_negative_drift_raises(self):
        with self.assertRaises(ValueError):
            ins.deg_per_hour_to_rad_s(-0.1)


class AccelerometerBiasErrorTest(unittest.TestCase):
    def test_velocity_error_linear_in_time(self):
        self.assertAlmostEqual(ins.accel_bias_velocity_error(1.0e-3, 100.0), 0.1, places=9)
        self.assertAlmostEqual(ins.accel_bias_velocity_error(1.0e-4, 600.0), 0.06, places=9)

    def test_position_error_double_integration(self):
        # 0.5 * b * t^2: 1 mg over 100 s -> 5 m; 100 ug over 600 s -> 18 m.
        self.assertAlmostEqual(ins.accel_bias_position_error(1.0e-3, 100.0), 5.0, places=9)
        self.assertAlmostEqual(ins.accel_bias_position_error(1.0e-4, 600.0), 18.0, places=9)

    def test_zero_bias_is_zero_error(self):
        self.assertEqual(ins.accel_bias_position_error(0.0, 3600.0), 0.0)

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            ins.accel_bias_position_error(1.0e-3, -1.0)
        with self.assertRaises(ValueError):
            ins.accel_bias_velocity_error(1.0e-3, -1.0)


class GyroDriftErrorTest(unittest.TestCase):
    def test_cubic_growth_zero_point_zero_one_deg_per_hour(self):
        # (1/6) * g * eps * t^3 with eps = 0.01 deg/h: ~3697 m after 1 h.
        self.assertAlmostEqual(
            ins.gyro_drift_position_error(0.01, 3600.0), 3696.9, delta=5.0
        )

    def test_one_deg_per_hour_after_one_hour(self):
        self.assertAlmostEqual(
            ins.gyro_drift_position_error(1.0, 3600.0), 369693.0, delta=50.0
        )

    def test_navigation_grade_drift(self):
        # 0.001 deg/h (navigation grade) -> about 370 m after one hour.
        self.assertAlmostEqual(
            ins.gyro_drift_position_error(0.001, 3600.0), 369.7, delta=1.0
        )

    def test_cubic_scaling_with_time(self):
        # Eight times the error when the time doubles.
        x1 = ins.gyro_drift_position_error(0.01, 1800.0)
        x2 = ins.gyro_drift_position_error(0.01, 3600.0)
        self.assertAlmostEqual(x2, 8.0 * x1, places=6)

    def test_zero_drift_is_zero_error(self):
        self.assertEqual(ins.gyro_drift_position_error(0.0, 3600.0), 0.0)

    def test_negative_time_raises(self):
        with self.assertRaises(ValueError):
            ins.gyro_drift_position_error(0.01, -1.0)


class SchulerSteadyStateTest(unittest.TestCase):
    def test_one_mg_bias_offset(self):
        # b * R / g: 1 mg -> about 650 m bounded offset.
        self.assertAlmostEqual(
            ins.schuler_steady_state_error(1.0e-3), 649.7, delta=1.0
        )

    def test_hundred_micro_g_bias_offset(self):
        self.assertAlmostEqual(
            ins.schuler_steady_state_error(1.0e-4), 64.97, delta=0.1
        )

    def test_offset_scales_linear_with_bias(self):
        b1 = ins.schuler_steady_state_error(1.0e-3)
        b2 = ins.schuler_steady_state_error(2.0e-3)
        self.assertAlmostEqual(b2, 2.0 * b1, places=9)

    def test_invalid_radius_raises(self):
        with self.assertRaises(ValueError):
            ins.schuler_steady_state_error(1.0e-3, r=0.0)


class EarthRateComponentTest(unittest.TestCase):
    def test_equator_full_rate_horizontal(self):
        north, up = ins.earth_rate_component(0.0)
        self.assertAlmostEqual(north, OMEGA_EARTH, places=12)
        self.assertAlmostEqual(up, 0.0, places=12)

    def test_pole_full_rate_vertical(self):
        north, up = ins.earth_rate_component(math.pi / 2.0)
        self.assertAlmostEqual(north, 0.0, places=12)
        self.assertAlmostEqual(up, OMEGA_EARTH, places=12)

    def test_forty_five_degrees_splits_rate(self):
        north, up = ins.earth_rate_component(math.pi / 4.0)
        expected = OMEGA_EARTH / math.sqrt(2.0)
        self.assertAlmostEqual(north, expected, places=12)
        self.assertAlmostEqual(up, expected, places=12)

    def test_invalid_latitude_raises(self):
        with self.assertRaises(ValueError):
            ins.earth_rate_component(math.pi / 2.0 + 0.1)


class AngleRandomWalkTest(unittest.TestCase):
    def test_sqrt_time_accumulation(self):
        self.assertAlmostEqual(ins.angle_random_walk_sigma(0.01, 1.0), 0.01, places=12)
        self.assertAlmostEqual(ins.angle_random_walk_sigma(0.01, 4.0), 0.02, places=12)
        self.assertAlmostEqual(ins.angle_random_walk_sigma(0.01, 0.0), 0.0, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ins.angle_random_walk_sigma(-0.01, 1.0)
        with self.assertRaises(ValueError):
            ins.angle_random_walk_sigma(0.01, -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

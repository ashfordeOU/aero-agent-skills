#!/usr/bin/env python3
"""Contract tests for the flight loads survey logic (gate 3).

Exercises every public function in flight_loads_survey_logic.py:
strain from resistance change, calibration slope, measured load,
error percent, dynamic pressure, maneuver lift coefficient and load
factor, feasibility, and survey bookkeeping. Stdlib unittest only,
deterministic, offline.
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import flight_loads_survey_logic as fls


class StrainFromDeltaResistanceTest(unittest.TestCase):
    def test_known_value(self):
        # epsilon = delta_R / (R * GF) = 0.00021 / (120 * 2.1)
        eps = fls.strain_from_delta_resistance(0.00021, 120.0, 2.1)
        self.assertAlmostEqual(eps, 0.00021 / (120.0 * 2.1), places=9)

    def test_compression_negative(self):
        eps = fls.strain_from_delta_resistance(-0.00021, 120.0, 2.1)
        self.assertLess(eps, 0.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fls.strain_from_delta_resistance(0.1, 0.0, 2.1)
        with self.assertRaises(ValueError):
            fls.strain_from_delta_resistance(0.1, 120.0, 0.0)
        with self.assertRaises(ValueError):
            fls.strain_from_delta_resistance(float("nan"), 120.0, 2.1)


class CalibrationFactorTest(unittest.TestCase):
    def test_known_slope(self):
        # Loads 1000, 2000, 3000 N at strains 1e-4, 2e-4, 3e-4 give a
        # through-origin slope of 1e7 N per strain.
        k = fls.calibration_factor([1000.0, 2000.0, 3000.0],
                                   [1e-4, 2e-4, 3e-4])
        self.assertAlmostEqual(k, 1e7, places=1)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            fls.calibration_factor([], [])

    def test_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            fls.calibration_factor([1.0, 2.0], [1.0])

    def test_zero_strain_energy_raises(self):
        with self.assertRaises(ValueError):
            fls.calibration_factor([100.0], [0.0])


class MeasuredLoadTest(unittest.TestCase):
    def test_known_value(self):
        # L = K * (epsilon - epsilon_0) = 1e7 * (5e-4 - 0)
        self.assertAlmostEqual(fls.measured_load(1e7, 5e-4), 5000.0, places=3)

    def test_with_zero_offset(self):
        self.assertAlmostEqual(fls.measured_load(1e7, 6e-4, 1e-4), 5000.0, places=3)

    def test_bad_calibration_raises(self):
        with self.assertRaises(ValueError):
            fls.measured_load(0.0, 1e-4)


class LoadErrorPercentTest(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(fls.load_error_percent(5500.0, 5000.0), 10.0)

    def test_below_prediction_negative(self):
        self.assertAlmostEqual(fls.load_error_percent(4500.0, 5000.0), -10.0)

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            fls.load_error_percent(100.0, 0.0)


class DynamicPressureTest(unittest.TestCase):
    def test_known_value(self):
        # q = 0.5 * 1.225 * 100^2 = 6125 Pa (SKILL.md worked example)
        self.assertAlmostEqual(fls.dynamic_pressure(1.225, 100.0), 6125.0, places=6)

    def test_zero_speed_zero_q(self):
        self.assertEqual(fls.dynamic_pressure(1.225, 0.0), 0.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fls.dynamic_pressure(0.0, 100.0)
        with self.assertRaises(ValueError):
            fls.dynamic_pressure(1.225, -1.0)


class LiftCoefficientAtManeuverTest(unittest.TestCase):
    def test_known_value(self):
        # CL = n * (W/S) / q = 1.8375 * 6000 / 6125 = 1.8
        cl = fls.lift_coefficient_at_maneuver(1.8375, 6000.0, 6125.0)
        self.assertAlmostEqual(cl, 1.8, places=4)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fls.lift_coefficient_at_maneuver(0.0, 6000.0, 6125.0)
        with self.assertRaises(ValueError):
            fls.lift_coefficient_at_maneuver(1.0, 0.0, 6125.0)


class SymmetricManeuverLoadFactorTest(unittest.TestCase):
    def test_known_value(self):
        # n = q * CL / (W/S) = 6125 * 1.8 / 6000 = 1.8375
        n = fls.symmetric_maneuver_load_factor(100.0, 1.225, 6000.0, 1.8)
        self.assertAlmostEqual(n, 1.8375, places=4)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fls.symmetric_maneuver_load_factor(100.0, 1.225, 6000.0, 0.0)


class ManeuverPointFeasibleTest(unittest.TestCase):
    def test_feasible(self):
        # CL required = 1.8 <= cl_max 1.9
        self.assertTrue(fls.maneuver_point_feasible(1.8375, 6000.0, 6125.0, 1.9))

    def test_infeasible(self):
        # CL required = 1.8 > cl_max 1.5
        self.assertFalse(fls.maneuver_point_feasible(1.8375, 6000.0, 6125.0, 1.5))

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fls.maneuver_point_feasible(1.0, 6000.0, 6125.0, 0.0)


class LoadFactorFromMeasuredLoadTest(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(fls.load_factor_from_measured_load(12000.0, 8000.0), 1.5)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            fls.load_factor_from_measured_load(12000.0, 0.0)


class PointInCalibrationRangeTest(unittest.TestCase):
    def test_inclusive_bounds(self):
        self.assertTrue(fls.point_in_calibration_range(5e-4, 5e-4, 9e-4))
        self.assertTrue(fls.point_in_calibration_range(9e-4, 5e-4, 9e-4))
        self.assertFalse(fls.point_in_calibration_range(4e-4, 5e-4, 9e-4))

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            fls.point_in_calibration_range(5e-4, 9e-4, 5e-4)


class SurveyPointOkTest(unittest.TestCase):
    def test_reached_target(self):
        self.assertTrue(fls.survey_point_ok(2.0, 2.0))

    def test_within_tolerance(self):
        self.assertTrue(fls.survey_point_ok(1.95, 2.0, tolerance=0.1))

    def test_below_tolerance_fails(self):
        self.assertFalse(fls.survey_point_ok(1.8, 2.0, tolerance=0.1))

    def test_bad_tolerance_raises(self):
        with self.assertRaises(ValueError):
            fls.survey_point_ok(2.0, 2.0, tolerance=-0.1)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Gate 3 contract test: multi-stage axial compressor design and matching.

stdlib unittest, offline, deterministic. Exercises
scripts/multi_stage_compressor.py against analytic checks:

  overall_pressure_ratio([1.4, 1.4]) = 1.96
  stage_count(10.0, 1.5) = ceil(ln(10)/ln(1.5)) = ceil(5.6789) = 6
  reheat_factor(220000, 200000) = 1.1
  annulus_area(100, 150, 1.2) = 100/(150*1.2) = 0.55556 m^2
  stage_work_distribution(300000, 3, 'rising') = [50000, 100000, 150000]
  corrected_speed(10000, 288.15, 288.15) = 10000 rpm

Run: python3 scripts/test_multi_stage_compressor.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from multi_stage_compressor import (  # noqa: E402
    overall_pressure_ratio,
    stage_count,
    reheat_factor,
    annulus_area,
    stage_work_distribution,
    corrected_speed,
)

T_REF = 288.15


class TestOverallPressureRatio(unittest.TestCase):
    def test_two_stages_product(self):
        self.assertAlmostEqual(overall_pressure_ratio([1.4, 1.4]), 1.96, places=6)

    def test_single_stage(self):
        self.assertEqual(overall_pressure_ratio([1.5]), 1.5)

    def test_three_stages_product(self):
        self.assertAlmostEqual(
            overall_pressure_ratio([1.2, 1.3, 1.4]), 2.184, places=6
        )

    def test_zero_pressure_ratio_raises(self):
        with self.assertRaises(ValueError):
            overall_pressure_ratio([0.0, 1.5])

    def test_unity_stage_raises(self):
        with self.assertRaises(ValueError):
            overall_pressure_ratio([1.0, 1.5])

    def test_negative_entry_raises(self):
        with self.assertRaises(ValueError):
            overall_pressure_ratio([-0.5, 1.5])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            overall_pressure_ratio([])


class TestStageCount(unittest.TestCase):
    def test_single_stage_target(self):
        self.assertEqual(stage_count(1.5, 1.5), 1)

    def test_ten_to_one_five(self):
        self.assertEqual(stage_count(10.0, 1.5), 6)

    def test_exact_two_stages(self):
        self.assertEqual(stage_count(1.44, 1.2), 2)

    def test_forty_at_one_two(self):
        self.assertEqual(stage_count(40.0, 1.2), 21)

    def test_total_unity_raises(self):
        with self.assertRaises(ValueError):
            stage_count(1.0, 1.2)

    def test_stage_unity_raises(self):
        with self.assertRaises(ValueError):
            stage_count(10.0, 1.0)


class TestReheatFactor(unittest.TestCase):
    def test_analytic_one_one(self):
        self.assertAlmostEqual(reheat_factor(220000.0, 200000.0), 1.1, places=6)

    def test_no_reheat_unity(self):
        self.assertEqual(reheat_factor(200000.0, 200000.0), 1.0)

    def test_sanity_ge_one(self):
        self.assertGreaterEqual(reheat_factor(250000.0, 200000.0), 1.0)

    def test_actual_below_ideal_raises(self):
        with self.assertRaises(ValueError):
            reheat_factor(190000.0, 200000.0)

    def test_zero_inputs_raise(self):
        with self.assertRaises(ValueError):
            reheat_factor(0.0, 200000.0)
        with self.assertRaises(ValueError):
            reheat_factor(200000.0, 0.0)


class TestAnnulusArea(unittest.TestCase):
    def test_analytic_area(self):
        self.assertAlmostEqual(
            annulus_area(100.0, 150.0, 1.2), 0.5555556, places=5
        )

    def test_half_square_meter(self):
        self.assertAlmostEqual(annulus_area(50.0, 100.0, 1.0), 0.5, places=6)

    def test_mass_flow_zero_raises(self):
        with self.assertRaises(ValueError):
            annulus_area(0.0, 150.0, 1.2)

    def test_axial_velocity_zero_raises(self):
        with self.assertRaises(ValueError):
            annulus_area(100.0, 0.0, 1.2)

    def test_density_zero_raises(self):
        with self.assertRaises(ValueError):
            annulus_area(100.0, 150.0, 0.0)


class TestStageWorkDistribution(unittest.TestCase):
    def test_equal_scheme(self):
        self.assertEqual(
            stage_work_distribution(300000.0, 3, "equal"),
            [100000.0, 100000.0, 100000.0],
        )

    def test_rising_scheme_analytic(self):
        self.assertEqual(
            stage_work_distribution(300000.0, 3, "rising"),
            [50000.0, 100000.0, 150000.0],
        )

    def test_rising_sum_equals_total(self):
        dist = stage_work_distribution(420000.0, 4, "rising")
        self.assertAlmostEqual(sum(dist), 420000.0, places=6)

    def test_rising_last_stage_highest(self):
        dist = stage_work_distribution(300000.0, 4, "rising")
        self.assertGreater(dist[3], dist[0])

    def test_single_stage_rising(self):
        self.assertEqual(
            stage_work_distribution(150000.0, 1, "rising"), [150000.0]
        )

    def test_zero_stages_raises(self):
        with self.assertRaises(ValueError):
            stage_work_distribution(300000.0, 0, "equal")

    def test_bad_scheme_raises(self):
        with self.assertRaises(ValueError):
            stage_work_distribution(300000.0, 3, "peaked")

    def test_zero_total_work_raises(self):
        with self.assertRaises(ValueError):
            stage_work_distribution(0.0, 3, "equal")


class TestCorrectedSpeed(unittest.TestCase):
    def test_at_reference_temperature(self):
        self.assertEqual(corrected_speed(10000.0, T_REF, T_REF), 10000.0)

    def test_cold_day_higher(self):
        self.assertAlmostEqual(
            corrected_speed(10000.0, T_REF, 240.0), 10957.3, places=1
        )

    def test_hot_day_lower(self):
        self.assertAlmostEqual(
            corrected_speed(12000.0, T_REF, 320.0), 11387.2, places=1
        )

    def test_matches_sqrt_formula(self):
        self.assertAlmostEqual(
            corrected_speed(15000.0, T_REF, 288.15 / 1.21),
            15000.0 * 1.1,
            places=4,
        )

    def test_zero_speed_raises(self):
        with self.assertRaises(ValueError):
            corrected_speed(0.0, T_REF, T_REF)

    def test_zero_reference_temperature_raises(self):
        with self.assertRaises(ValueError):
            corrected_speed(10000.0, 0.0, T_REF)

    def test_zero_actual_temperature_raises(self):
        with self.assertRaises(ValueError):
            corrected_speed(10000.0, T_REF, 0.0)


if __name__ == "__main__":
    unittest.main()

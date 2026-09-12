"""
Tests for local_yielding_and_buckling_functionality_logic.py
ECSS-E-ST-32 clauses 4.3.3 and 4.3.4.
stdlib unittest only; offline, deterministic.
Run: python3 test_local_yielding_and_buckling_functionality.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from local_yielding_and_buckling_functionality_logic import (
    aggregate_buckling_checks,
    buckling_margin_of_safety,
    check_local_yielding,
    check_plate_buckling,
    combined_load_interaction,
    crippling_stress_angle_section,
    plate_buckling_critical_stress,
    von_mises_stress,
)


class TestVonMisesStress(unittest.TestCase):

    def test_pure_axial_x(self):
        # sigma_x=100, sigma_y=0, tau=0 -> sigma_vm = 100
        self.assertAlmostEqual(von_mises_stress(100.0, 0.0, 0.0), 100.0)

    def test_pure_axial_y(self):
        # sigma_x=0, sigma_y=200, tau=0 -> sigma_vm = 200
        self.assertAlmostEqual(von_mises_stress(0.0, 200.0, 0.0), 200.0)

    def test_pure_shear(self):
        # sigma_vm = sqrt(3) * tau for pure shear
        tau = 50.0
        self.assertAlmostEqual(von_mises_stress(0.0, 0.0, tau), math.sqrt(3.0) * tau)

    def test_equal_biaxial(self):
        # sigma_x = sigma_y = 100, tau = 0 -> sigma_vm = 100
        self.assertAlmostEqual(von_mises_stress(100.0, 100.0, 0.0), 100.0)

    def test_equal_opposite_biaxial(self):
        # sigma_x = 100, sigma_y = -100, tau = 0
        # vm = sqrt(100^2 + 100*100 + 100^2) = sqrt(30000)
        expected = math.sqrt(100.0**2 + 100.0 * 100.0 + 100.0**2)
        self.assertAlmostEqual(von_mises_stress(100.0, -100.0, 0.0), expected)


class TestCheckLocalYielding(unittest.TestCase):

    def test_well_below_yield(self):
        result = check_local_yielding(100.0, 400.0)
        self.assertEqual(result["status"], "permissible")
        self.assertAlmostEqual(result["yield_ratio"], 0.25)
        self.assertAlmostEqual(result["margin_of_safety"], 3.0)

    def test_at_yield_boundary(self):
        result = check_local_yielding(400.0, 400.0)
        self.assertEqual(result["status"], "permissible")
        self.assertAlmostEqual(result["yield_ratio"], 1.0)
        self.assertAlmostEqual(result["margin_of_safety"], 0.0)

    def test_above_yield(self):
        result = check_local_yielding(500.0, 400.0)
        self.assertEqual(result["status"], "exceeded")
        self.assertGreater(result["yield_ratio"], 1.0)
        self.assertLess(result["margin_of_safety"], 0.0)

    def test_zero_stress_gives_infinite_margin(self):
        result = check_local_yielding(0.0, 400.0)
        self.assertEqual(result["status"], "permissible")
        self.assertEqual(result["margin_of_safety"], float("inf"))

    def test_invalid_zero_yield_strength(self):
        with self.assertRaises(ValueError):
            check_local_yielding(100.0, 0.0)

    def test_invalid_negative_yield_strength(self):
        with self.assertRaises(ValueError):
            check_local_yielding(100.0, -250.0)

    def test_invalid_negative_stress(self):
        with self.assertRaises(ValueError):
            check_local_yielding(-10.0, 400.0)


class TestPlateBucklingCriticalStress(unittest.TestCase):

    def test_formula_consistency(self):
        # Verify formula is applied correctly against a manual computation
        k, E, nu, t, b = 4.0, 70.0e9, 0.33, 2.0e-3, 0.1
        expected = k * math.pi**2 * E / (12.0 * (1.0 - nu**2)) * (t / b)**2
        self.assertAlmostEqual(
            plate_buckling_critical_stress(k, E, nu, t, b), expected, places=0
        )

    def test_thicker_plate_higher_sigma_cr(self):
        E, nu, b = 70.0e9, 0.3, 0.1
        cr_thin = plate_buckling_critical_stress(4.0, E, nu, 1.0e-3, b)
        cr_thick = plate_buckling_critical_stress(4.0, E, nu, 2.0e-3, b)
        self.assertGreater(cr_thick, cr_thin)

    def test_invalid_k_zero(self):
        with self.assertRaises(ValueError):
            plate_buckling_critical_stress(0.0, 70.0e9, 0.3, 2.0e-3, 0.1)

    def test_invalid_nu_above_half(self):
        with self.assertRaises(ValueError):
            plate_buckling_critical_stress(4.0, 70.0e9, 0.5, 2.0e-3, 0.1)

    def test_invalid_nu_zero(self):
        with self.assertRaises(ValueError):
            plate_buckling_critical_stress(4.0, 70.0e9, 0.0, 2.0e-3, 0.1)

    def test_invalid_thickness_zero(self):
        with self.assertRaises(ValueError):
            plate_buckling_critical_stress(4.0, 70.0e9, 0.3, 0.0, 0.1)

    def test_invalid_width_zero(self):
        with self.assertRaises(ValueError):
            plate_buckling_critical_stress(4.0, 70.0e9, 0.3, 2.0e-3, 0.0)


class TestCheckPlateBuckling(unittest.TestCase):

    def test_stable_plate(self):
        result = check_plate_buckling(200.0e6, 100.0e6)
        self.assertEqual(result["status"], "stable")
        self.assertAlmostEqual(result["margin_of_safety"], 1.0)

    def test_buckled_plate(self):
        result = check_plate_buckling(50.0e6, 100.0e6)
        self.assertEqual(result["status"], "buckled")
        self.assertAlmostEqual(result["margin_of_safety"], -0.5)

    def test_zero_applied_stress_infinite_margin(self):
        ms = buckling_margin_of_safety(100.0e6, 0.0)
        self.assertEqual(ms, float("inf"))

    def test_invalid_negative_applied_stress(self):
        with self.assertRaises(ValueError):
            buckling_margin_of_safety(100.0e6, -10.0e6)

    def test_invalid_zero_critical_stress(self):
        with self.assertRaises(ValueError):
            buckling_margin_of_safety(0.0, 50.0e6)


class TestCombinedLoadInteraction(unittest.TestCase):

    def test_pure_axial_at_half_critical(self):
        # sigma = 0.5 * sigma_cr, tau = 0 -> R = 0.25, MS = 3.0
        result = combined_load_interaction(50.0, 100.0, 0.0, 100.0)
        self.assertEqual(result["status"], "stable")
        self.assertAlmostEqual(result["interaction_index"], 0.25)
        self.assertAlmostEqual(result["margin_of_safety"], 3.0)

    def test_pure_shear_at_critical(self):
        # tau = tau_cr -> R = 1.0, MS = 0
        result = combined_load_interaction(0.0, 100.0, 100.0, 100.0)
        self.assertEqual(result["status"], "stable")
        self.assertAlmostEqual(result["interaction_index"], 1.0)
        self.assertAlmostEqual(result["margin_of_safety"], 0.0)

    def test_combined_buckled(self):
        # sigma = 0.8 * sigma_cr, tau = 0.8 * tau_cr -> R = 0.64+0.64 = 1.28
        result = combined_load_interaction(80.0, 100.0, 80.0, 100.0)
        self.assertEqual(result["status"], "buckled")
        self.assertAlmostEqual(result["interaction_index"], 1.28)

    def test_at_exact_unit_circle(self):
        # Each term = sqrt(0.5)^2 = 0.5, so R = 1.0 exactly
        val = math.sqrt(0.5) * 100.0
        result = combined_load_interaction(val, 100.0, val, 100.0)
        self.assertAlmostEqual(result["interaction_index"], 1.0, places=12)
        self.assertEqual(result["status"], "stable")

    def test_invalid_sigma_cr_axial_zero(self):
        with self.assertRaises(ValueError):
            combined_load_interaction(50.0, 0.0, 10.0, 100.0)

    def test_invalid_tau_cr_zero(self):
        with self.assertRaises(ValueError):
            combined_load_interaction(50.0, 100.0, 10.0, 0.0)

    def test_invalid_negative_applied_shear(self):
        with self.assertRaises(ValueError):
            combined_load_interaction(50.0, 100.0, -10.0, 100.0)


class TestCripplingStress(unittest.TestCase):

    def test_known_ratio(self):
        # t/b = 0.5 -> F_cc = F_tu * 0.5^0.75
        F_tu = 400.0e6
        t, b = 5.0e-3, 10.0e-3
        expected = F_tu * (0.5 ** 0.75)
        self.assertAlmostEqual(crippling_stress_angle_section(F_tu, t, b), expected, places=0)

    def test_unit_ratio(self):
        # t/b = 1.0 (boundary) -> F_cc = F_tu * 1^0.75 = F_tu
        F_tu = 200.0e6
        result = crippling_stress_angle_section(F_tu, 1.0e-2, 1.0e-2)
        self.assertAlmostEqual(result, F_tu)

    def test_ratio_above_one_raises(self):
        with self.assertRaises(ValueError):
            crippling_stress_angle_section(400.0e6, 0.2, 0.1)

    def test_invalid_zero_ftu(self):
        with self.assertRaises(ValueError):
            crippling_stress_angle_section(0.0, 2.0e-3, 10.0e-3)

    def test_invalid_zero_thickness(self):
        with self.assertRaises(ValueError):
            crippling_stress_angle_section(400.0e6, 0.0, 10.0e-3)


class TestAggregateBucklingChecks(unittest.TestCase):

    def test_all_stable(self):
        checks = [
            {"margin_of_safety": 0.5},
            {"margin_of_safety": 1.2},
            {"margin_of_safety": 0.0},
        ]
        result = aggregate_buckling_checks(checks)
        self.assertEqual(result["overall_status"], "all_stable")
        self.assertAlmostEqual(result["governing_margin"], 0.0)
        self.assertEqual(result["n_checks"], 3)
        self.assertEqual(result["n_failures"], 0)

    def test_one_failure(self):
        checks = [
            {"margin_of_safety": 0.5},
            {"margin_of_safety": -0.1},
            {"margin_of_safety": 1.0},
        ]
        result = aggregate_buckling_checks(checks)
        self.assertEqual(result["overall_status"], "has_failures")
        self.assertAlmostEqual(result["governing_margin"], -0.1)
        self.assertEqual(result["n_failures"], 1)

    def test_all_failures(self):
        checks = [{"margin_of_safety": -0.2}, {"margin_of_safety": -0.5}]
        result = aggregate_buckling_checks(checks)
        self.assertEqual(result["overall_status"], "has_failures")
        self.assertEqual(result["n_failures"], 2)
        self.assertAlmostEqual(result["governing_margin"], -0.5)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            aggregate_buckling_checks([])

    def test_single_check_stable(self):
        result = aggregate_buckling_checks([{"margin_of_safety": 2.5}])
        self.assertEqual(result["overall_status"], "all_stable")
        self.assertEqual(result["n_checks"], 1)
        self.assertAlmostEqual(result["governing_margin"], 2.5)


if __name__ == "__main__":
    unittest.main()

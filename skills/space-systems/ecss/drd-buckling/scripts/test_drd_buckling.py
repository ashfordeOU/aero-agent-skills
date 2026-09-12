"""
Offline deterministic unit tests for drd_buckling_logic.py.
Run with: python3 test_drd_buckling.py
Expected output: OK (all tests pass).
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import drd_buckling_logic as logic


class TestCategorizeMember(unittest.TestCase):

    def test_column_accepted(self):
        self.assertEqual(logic.categorize_member("column"), "column")

    def test_flat_plate_accepted(self):
        self.assertEqual(logic.categorize_member("flat_plate"), "flat_plate")

    def test_shell_accepted(self):
        self.assertEqual(logic.categorize_member("shell"), "shell")

    def test_mixed_case_accepted(self):
        self.assertEqual(logic.categorize_member("COLUMN"), "column")

    def test_unknown_geometry_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_member("beam")


class TestEffectiveLengthFactor(unittest.TestCase):

    def test_pin_pin(self):
        self.assertAlmostEqual(logic.effective_length_factor("pin-pin"), 1.0)

    def test_fix_fix(self):
        self.assertAlmostEqual(logic.effective_length_factor("fix-fix"), 0.5)

    def test_fix_free(self):
        self.assertAlmostEqual(logic.effective_length_factor("fix-free"), 2.0)

    def test_fix_pin(self):
        self.assertAlmostEqual(
            logic.effective_length_factor("fix-pin"), 0.6991, places=3
        )

    def test_fix_guided(self):
        self.assertAlmostEqual(logic.effective_length_factor("fix-guided"), 1.0)

    def test_unknown_bc_raises(self):
        with self.assertRaises(ValueError):
            logic.effective_length_factor("roller-pin")


class TestSlendernessRatio(unittest.TestCase):

    def test_basic_value(self):
        # K=1, L=2000, r=10 => KL/r = 200
        self.assertAlmostEqual(logic.slenderness_ratio(1.0, 2000.0, 10.0), 200.0)

    def test_fix_fix_reduces_slenderness(self):
        # K=0.5 halves slenderness
        self.assertAlmostEqual(logic.slenderness_ratio(0.5, 2000.0, 10.0), 100.0)

    def test_zero_r_raises(self):
        with self.assertRaises(ValueError):
            logic.slenderness_ratio(1.0, 1000.0, 0.0)

    def test_zero_L_raises(self):
        with self.assertRaises(ValueError):
            logic.slenderness_ratio(1.0, 0.0, 10.0)


class TestTransitionSlenderness(unittest.TestCase):

    def test_known_value(self):
        # E=70e9 Pa, sigma_y=280e6 Pa => transition = pi*sqrt(2*70e9/280e6) = pi*sqrt(500)
        E, sy = 70e9, 280e6
        expected = math.pi * math.sqrt(2.0 * E / sy)
        self.assertAlmostEqual(logic.transition_slenderness(E, sy), expected, places=4)

    def test_higher_yield_lower_transition(self):
        # Higher yield stress => lower transition slenderness
        t1 = logic.transition_slenderness(70e9, 280e6)
        t2 = logic.transition_slenderness(70e9, 500e6)
        self.assertGreater(t1, t2)

    def test_zero_E_raises(self):
        with self.assertRaises(ValueError):
            logic.transition_slenderness(0.0, 280e6)


class TestEulerCriticalStress(unittest.TestCase):

    def test_known_value(self):
        E = 70e9
        KL_r = 100.0
        expected = math.pi ** 2 * E / KL_r ** 2
        self.assertAlmostEqual(logic.euler_critical_stress(E, KL_r), expected, places=0)

    def test_higher_slenderness_lower_stress(self):
        E = 70e9
        s1 = logic.euler_critical_stress(E, 100.0)
        s2 = logic.euler_critical_stress(E, 200.0)
        self.assertGreater(s1, s2)

    def test_zero_slenderness_raises(self):
        with self.assertRaises(ValueError):
            logic.euler_critical_stress(70e9, 0.0)


class TestJohnsonCriticalStress(unittest.TestCase):

    def test_at_zero_slenderness_equals_yield(self):
        # At KL/r -> near 0, Johnson stress -> sigma_y
        E, sy = 70e9, 280e6
        # Use a very small KL/r (not zero, which raises)
        val = logic.johnson_critical_stress(E, sy, 0.001)
        self.assertAlmostEqual(val, sy, delta=sy * 0.001)

    def test_below_yield(self):
        E, sy = 70e9, 280e6
        KL_r = 50.0
        val = logic.johnson_critical_stress(E, sy, KL_r)
        self.assertLessEqual(val, sy)

    def test_zero_E_raises(self):
        with self.assertRaises(ValueError):
            logic.johnson_critical_stress(0.0, 280e6, 50.0)


class TestSelectColumnFormula(unittest.TestCase):

    def test_long_column_selects_euler(self):
        # KL/r = 200, transition ≈ 70.5 for E=70e9, sy=280e6 => Euler
        E, sy = 70e9, 280e6
        result = logic.select_column_formula(E, sy, 1.0, 2000.0, 10.0)
        self.assertEqual(result["regime"], "euler")

    def test_short_column_selects_johnson(self):
        # KL/r = 30, transition ≈ 70.5 => Johnson
        E, sy = 70e9, 280e6
        result = logic.select_column_formula(E, sy, 1.0, 300.0, 10.0)
        self.assertEqual(result["regime"], "johnson")

    def test_result_contains_sigma_cr(self):
        E, sy = 70e9, 280e6
        result = logic.select_column_formula(E, sy, 1.0, 2000.0, 10.0)
        self.assertIn("sigma_cr", result)
        self.assertGreater(result["sigma_cr"], 0.0)


class TestFlatPlateCriticalStress(unittest.TestCase):

    def test_known_value(self):
        E, nu, t, b, k = 70e9, 0.3, 2e-3, 100e-3, 4.0
        expected = k * math.pi ** 2 * E / (12.0 * (1.0 - nu ** 2)) * (t / b) ** 2
        self.assertAlmostEqual(
            logic.flat_plate_critical_stress(E, nu, t, b, k), expected, places=0
        )

    def test_thicker_plate_higher_stress(self):
        E, nu, b, k = 70e9, 0.3, 100e-3, 4.0
        s1 = logic.flat_plate_critical_stress(E, nu, 2e-3, b, k)
        s2 = logic.flat_plate_critical_stress(E, nu, 4e-3, b, k)
        self.assertGreater(s2, s1)

    def test_invalid_nu_raises(self):
        with self.assertRaises(ValueError):
            logic.flat_plate_critical_stress(70e9, 0.5, 2e-3, 100e-3, 4.0)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            logic.flat_plate_critical_stress(70e9, 0.3, 0.0, 100e-3, 4.0)


class TestApplyKnockdown(unittest.TestCase):

    def test_unit_knockdown_no_change(self):
        self.assertAlmostEqual(logic.apply_knockdown(100.0, 1.0), 100.0)

    def test_knockdown_halves_stress(self):
        self.assertAlmostEqual(logic.apply_knockdown(200.0, 0.5), 100.0)

    def test_zero_knockdown_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_knockdown(100.0, 0.0)

    def test_knockdown_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_knockdown(100.0, 1.01)

    def test_negative_sigma_cr_raises(self):
        with self.assertRaises(ValueError):
            logic.apply_knockdown(-10.0, 0.8)


class TestMarginOfSafety(unittest.TestCase):

    def test_positive_ms_when_cr_exceeds_applied(self):
        ms = logic.margin_of_safety(150.0, 100.0)
        self.assertAlmostEqual(ms, 0.5)

    def test_zero_ms_at_limit(self):
        ms = logic.margin_of_safety(100.0, 100.0)
        self.assertAlmostEqual(ms, 0.0)

    def test_negative_ms_when_applied_exceeds_cr(self):
        ms = logic.margin_of_safety(80.0, 100.0)
        self.assertAlmostEqual(ms, -0.2)

    def test_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            logic.margin_of_safety(100.0, 0.0)


class TestIsBucklingCompliant(unittest.TestCase):

    def test_positive_ms_compliant(self):
        self.assertTrue(logic.is_buckling_compliant(0.5))

    def test_zero_ms_compliant(self):
        self.assertTrue(logic.is_buckling_compliant(0.0))

    def test_negative_ms_not_compliant(self):
        self.assertFalse(logic.is_buckling_compliant(-0.1))


class TestCheckColumn(unittest.TestCase):

    def test_long_euler_column_compliant(self):
        # Al 7075: E=71e9, sy=503e6, pin-pin, L=3m, r=0.015m, sigma_app=10e6, no kd
        result = logic.check_column(
            E=71e9, sigma_y=503e6,
            boundary_condition="pin-pin",
            L=3.0, r=0.015,
            sigma_applied=10e6,
            knockdown=1.0,
        )
        self.assertEqual(result["regime"], "euler")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["K"], 1.0)

    def test_knockdown_can_make_column_fail(self):
        # Deliberately load the column near its critical stress, then knock it down
        E, sy = 71e9, 503e6
        # Choose params so sigma_cr is around 20 MPa
        # Euler: sigma_cr = pi^2*E/(KL/r)^2 => KL/r = pi*sqrt(E/sigma_cr)
        sigma_cr_target = 20e6
        KL_r_needed = math.pi * math.sqrt(E / sigma_cr_target)
        L = KL_r_needed * 0.015  # r=0.015
        result = logic.check_column(
            E=E, sigma_y=sy,
            boundary_condition="pin-pin",
            L=L, r=0.015,
            sigma_applied=18e6,   # just below theoretical
            knockdown=0.8,        # knock-down pushes sigma_cr below applied
        )
        self.assertFalse(result["compliant"])

    def test_fix_fix_lower_K(self):
        r1 = logic.check_column(
            E=71e9, sigma_y=503e6,
            boundary_condition="pin-pin",
            L=2.0, r=0.01,
            sigma_applied=5e6, knockdown=1.0,
        )
        r2 = logic.check_column(
            E=71e9, sigma_y=503e6,
            boundary_condition="fix-fix",
            L=2.0, r=0.01,
            sigma_applied=5e6, knockdown=1.0,
        )
        # fix-fix has lower K => lower KL/r => higher critical stress
        self.assertGreater(r2["sigma_cr_reduced"], r1["sigma_cr_reduced"])

    def test_result_keys_present(self):
        result = logic.check_column(
            E=71e9, sigma_y=503e6,
            boundary_condition="pin-pin",
            L=1.0, r=0.01,
            sigma_applied=1e6,
        )
        for key in ("boundary_condition", "K", "KL_r", "regime",
                    "sigma_cr_theoretical", "knockdown", "sigma_cr_reduced",
                    "sigma_applied", "MS", "compliant"):
            self.assertIn(key, result)


class TestCheckFlatPlate(unittest.TestCase):

    def test_compliant_plate(self):
        result = logic.check_flat_plate(
            E=70e9, nu=0.3, t=3e-3, b=100e-3, k=4.0,
            sigma_applied=10e6, knockdown=1.0,
        )
        self.assertTrue(result["compliant"])

    def test_thin_plate_may_fail(self):
        # Very thin plate (t=0.5 mm) under large load
        result = logic.check_flat_plate(
            E=70e9, nu=0.3, t=0.5e-3, b=100e-3, k=4.0,
            sigma_applied=50e6, knockdown=1.0,
        )
        self.assertFalse(result["compliant"])

    def test_knockdown_reduces_sigma_cr(self):
        r1 = logic.check_flat_plate(
            E=70e9, nu=0.3, t=3e-3, b=100e-3, k=4.0,
            sigma_applied=1e6, knockdown=1.0,
        )
        r2 = logic.check_flat_plate(
            E=70e9, nu=0.3, t=3e-3, b=100e-3, k=4.0,
            sigma_applied=1e6, knockdown=0.7,
        )
        self.assertGreater(r1["sigma_cr_reduced"], r2["sigma_cr_reduced"])


if __name__ == "__main__":
    unittest.main()

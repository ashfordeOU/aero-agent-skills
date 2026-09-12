"""
stdlib unittest for material_strength_modulus_logic.py.
Run: python3 test_material_strength_modulus.py
Must print OK with 10+ tests. Offline, deterministic.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from material_strength_modulus_logic import (
    apply_knockdown_factor,
    categorize_property_source,
    check_basis_requirement,
    check_ftu_fty_ordering,
    check_modulus_consistency,
    compute_shear_modulus,
    margin_of_safety,
    select_allowable_basis,
    tresca_equivalent_stress,
    tresca_yield_check,
    von_mises_equivalent_stress,
    von_mises_yield_check,
)


class TestComputeShearModulus(unittest.TestCase):
    def test_aluminium_alloy_typical_values(self):
        # E=70 GPa, nu=0.33 => G = 70/(2*1.33) ≈ 26.32 GPa
        G = compute_shear_modulus(70e9, 0.33)
        expected = 70e9 / (2.0 * 1.33)
        self.assertAlmostEqual(G, expected, places=0)

    def test_steel_typical_values(self):
        # E=200 GPa, nu=0.30 => G ≈ 76.92 GPa
        G = compute_shear_modulus(200e9, 0.30)
        self.assertAlmostEqual(G, 200e9 / 2.6, places=0)

    def test_titanium_typical_values(self):
        # E=114 GPa, nu=0.34 => G ≈ 42.54 GPa
        G = compute_shear_modulus(114e9, 0.34)
        self.assertAlmostEqual(G, 114e9 / (2.0 * 1.34), places=0)

    def test_invalid_negative_youngs_modulus_raises(self):
        with self.assertRaises(ValueError):
            compute_shear_modulus(-70e9, 0.33)

    def test_invalid_zero_youngs_modulus_raises(self):
        with self.assertRaises(ValueError):
            compute_shear_modulus(0.0, 0.33)

    def test_invalid_poisson_ratio_at_upper_bound_raises(self):
        with self.assertRaises(ValueError):
            compute_shear_modulus(70e9, 0.5)

    def test_invalid_poisson_ratio_at_lower_bound_raises(self):
        with self.assertRaises(ValueError):
            compute_shear_modulus(70e9, -1.0)

    def test_inverse_relation_shear_to_youngs(self):
        # G * 2 * (1 + nu) must recover E
        E, nu = 70e9, 0.33
        G = compute_shear_modulus(E, nu)
        recovered_E = G * 2.0 * (1.0 + nu)
        self.assertAlmostEqual(recovered_E, E, places=1)


class TestCheckModulusConsistency(unittest.TestCase):
    def test_exact_match_is_consistent(self):
        E, nu = 70e9, 0.33
        G = compute_shear_modulus(E, nu)
        ok, rel_err = check_modulus_consistency(E, G, nu)
        self.assertTrue(ok)
        self.assertAlmostEqual(rel_err, 0.0, places=10)

    def test_within_tolerance_passes(self):
        E, nu = 70e9, 0.33
        G_exact = compute_shear_modulus(E, nu)
        G_perturbed = G_exact * 1.01  # 1 % deviation
        ok, rel_err = check_modulus_consistency(E, G_perturbed, nu, tolerance=0.02)
        self.assertTrue(ok)
        self.assertAlmostEqual(rel_err, 0.01, places=6)

    def test_beyond_tolerance_fails(self):
        E, nu = 70e9, 0.33
        G_inconsistent = 30e9  # clearly inconsistent
        ok, rel_err = check_modulus_consistency(E, G_inconsistent, nu, tolerance=0.02)
        self.assertFalse(ok)
        self.assertGreater(rel_err, 0.02)


class TestVonMisesEquivalentStress(unittest.TestCase):
    def test_uniaxial_tension(self):
        # s1=100, s2=s3=0 => sigma_vm = 100
        sigma_vm = von_mises_equivalent_stress(100.0, 0.0, 0.0)
        self.assertAlmostEqual(sigma_vm, 100.0, places=6)

    def test_hydrostatic_state_gives_zero(self):
        # Equal triaxial stresses => zero deviatoric => sigma_vm = 0
        sigma_vm = von_mises_equivalent_stress(100.0, 100.0, 100.0)
        self.assertAlmostEqual(sigma_vm, 0.0, places=6)

    def test_biaxial_equal_opposite_stresses(self):
        # s1=100, s2=-100, s3=0
        # sigma_vm = sqrt(0.5*(40000 + 10000 + 10000)) = sqrt(30000)
        sigma_vm = von_mises_equivalent_stress(100.0, -100.0, 0.0)
        self.assertAlmostEqual(sigma_vm, math.sqrt(30000.0), places=5)

    def test_default_s3_zero_matches_explicit(self):
        sigma_2d = von_mises_equivalent_stress(80.0, 40.0)
        sigma_3d = von_mises_equivalent_stress(80.0, 40.0, 0.0)
        self.assertAlmostEqual(sigma_2d, sigma_3d, places=10)


class TestVonMisesYieldCheck(unittest.TestCase):
    def test_stress_well_below_yield_passes(self):
        passed, sigma_vm, ms = von_mises_yield_check(50.0, 0.0, 0.0, fty=300.0)
        self.assertTrue(passed)
        self.assertAlmostEqual(ms, 300.0 / 50.0 - 1.0, places=6)

    def test_stress_above_yield_fails(self):
        passed, sigma_vm, ms = von_mises_yield_check(400.0, 0.0, 0.0, fty=300.0)
        self.assertFalse(passed)
        self.assertLess(ms, 0.0)

    def test_zero_stress_state_gives_infinite_margin(self):
        passed, sigma_vm, ms = von_mises_yield_check(0.0, 0.0, 0.0, fty=300.0)
        self.assertTrue(passed)
        self.assertEqual(ms, float("inf"))

    def test_invalid_fty_raises(self):
        with self.assertRaises(ValueError):
            von_mises_yield_check(100.0, 0.0, 0.0, fty=-300.0)


class TestTrescaEquivalentStress(unittest.TestCase):
    def test_uniaxial_equals_applied_stress(self):
        sigma_t = tresca_equivalent_stress(100.0, 0.0, 0.0)
        self.assertAlmostEqual(sigma_t, 100.0, places=6)

    def test_biaxial_same_sign_uses_largest_difference(self):
        # s1=100, s2=60, s3=0 => max(40, 60, 100) = 100
        sigma_t = tresca_equivalent_stress(100.0, 60.0, 0.0)
        self.assertAlmostEqual(sigma_t, 100.0, places=6)

    def test_equal_principal_stresses_gives_zero(self):
        sigma_t = tresca_equivalent_stress(50.0, 50.0, 50.0)
        self.assertAlmostEqual(sigma_t, 0.0, places=6)


class TestTrescaYieldCheck(unittest.TestCase):
    def test_below_yield_passes(self):
        passed, sigma_t, ms = tresca_yield_check(50.0, 0.0, 0.0, fty=300.0)
        self.assertTrue(passed)

    def test_above_yield_fails(self):
        passed, sigma_t, ms = tresca_yield_check(400.0, 0.0, 0.0, fty=300.0)
        self.assertFalse(passed)
        self.assertLess(ms, 0.0)

    def test_tresca_more_conservative_than_von_mises(self):
        # Biaxial equal-opposite case: Tresca gives larger equivalent stress
        s1, s2, s3, fty = 100.0, -100.0, 0.0, 250.0
        _, sigma_t, _ = tresca_yield_check(s1, s2, s3, fty)
        _, sigma_vm, _ = von_mises_yield_check(s1, s2, s3, fty)
        self.assertGreaterEqual(sigma_t, sigma_vm)


class TestMarginOfSafety(unittest.TestCase):
    def test_positive_margin(self):
        ms = margin_of_safety(300.0, 200.0)
        self.assertAlmostEqual(ms, 0.5, places=6)

    def test_zero_margin_at_exact_allowable(self):
        ms = margin_of_safety(200.0, 200.0)
        self.assertAlmostEqual(ms, 0.0, places=6)

    def test_negative_margin_when_applied_exceeds_allowable(self):
        ms = margin_of_safety(150.0, 200.0)
        self.assertAlmostEqual(ms, -0.25, places=6)

    def test_invalid_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            margin_of_safety(300.0, 0.0)


class TestFtuFtyOrdering(unittest.TestCase):
    def test_valid_ductile_alloy(self):
        self.assertTrue(check_ftu_fty_ordering(ftu=450.0, fty=300.0))

    def test_invalid_yield_exceeds_ultimate(self):
        self.assertFalse(check_ftu_fty_ordering(ftu=300.0, fty=450.0))

    def test_equal_values_not_valid(self):
        self.assertFalse(check_ftu_fty_ordering(ftu=300.0, fty=300.0))


class TestApplyKnockdownFactor(unittest.TestCase):
    def test_temperature_knockdown_reduces_allowable(self):
        result = apply_knockdown_factor(300.0, 0.9)
        self.assertAlmostEqual(result, 270.0, places=6)

    def test_unity_knockdown_preserves_allowable(self):
        result = apply_knockdown_factor(300.0, 1.0)
        self.assertAlmostEqual(result, 300.0, places=6)

    def test_zero_knockdown_raises(self):
        with self.assertRaises(ValueError):
            apply_knockdown_factor(300.0, 0.0)

    def test_knockdown_above_one_raises(self):
        with self.assertRaises(ValueError):
            apply_knockdown_factor(300.0, 1.05)

    def test_chained_knockdowns_are_multiplicative(self):
        # Two successive knockdowns: 0.9 then 0.95
        result = apply_knockdown_factor(
            apply_knockdown_factor(300.0, 0.9), 0.95
        )
        self.assertAlmostEqual(result, 300.0 * 0.9 * 0.95, places=6)


class TestCategorizePropertySource(unittest.TestCase):
    def test_test_coupon_is_accepted(self):
        self.assertEqual(categorize_property_source("test-coupon"), "accepted")

    def test_material_handbook_is_accepted(self):
        self.assertEqual(categorize_property_source("material-handbook"), "accepted")

    def test_qualification_database_is_accepted(self):
        self.assertEqual(categorize_property_source("qualification-database"), "accepted")

    def test_supplier_datasheet_is_accepted(self):
        self.assertEqual(categorize_property_source("supplier-datasheet"), "accepted")

    def test_vendor_estimate_is_rejected(self):
        self.assertEqual(categorize_property_source("vendor-estimate"), "rejected")

    def test_empty_string_is_rejected(self):
        self.assertEqual(categorize_property_source(""), "rejected")

    def test_unknown_type_is_rejected(self):
        self.assertEqual(categorize_property_source("legacy-data"), "rejected")


class TestAllowableBasisRequirement(unittest.TestCase):
    def test_fracture_critical_requires_a_basis(self):
        self.assertEqual(select_allowable_basis(True), "A-basis")

    def test_non_fracture_critical_requires_b_basis(self):
        self.assertEqual(select_allowable_basis(False), "B-basis")

    def test_a_basis_satisfies_fracture_critical(self):
        ok, required = check_basis_requirement("A-basis", True)
        self.assertTrue(ok)
        self.assertEqual(required, "A-basis")

    def test_b_basis_fails_fracture_critical(self):
        ok, required = check_basis_requirement("B-basis", True)
        self.assertFalse(ok)
        self.assertEqual(required, "A-basis")

    def test_a_basis_also_satisfies_non_fracture_critical(self):
        ok, required = check_basis_requirement("A-basis", False)
        self.assertTrue(ok)

    def test_b_basis_satisfies_non_fracture_critical(self):
        ok, required = check_basis_requirement("B-basis", False)
        self.assertTrue(ok)

    def test_unknown_basis_fails_all_requirements(self):
        ok_fc, _ = check_basis_requirement("mean-value", True)
        ok_nfc, _ = check_basis_requirement("mean-value", False)
        self.assertFalse(ok_fc)
        self.assertFalse(ok_nfc)


if __name__ == "__main__":
    unittest.main()

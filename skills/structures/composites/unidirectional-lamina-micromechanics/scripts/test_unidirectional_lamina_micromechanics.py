"""Contract test for unidirectional-lamina-micromechanics.

Exercises the SKILL.md Workflow steps: step 1 (collect constituent
properties and fiber volume fraction), step 2 (derive the matrix shear
modulus), step 3 (predict E1 and nu12 by the rule of mixtures), step 4
(predict E2 by the Halpin-Tsai closed form), step 5 (predict G12 by the
Halpin-Tsai closed form), step 6 (compute density by the rule of
mixtures), step 7 (verify E2 against the Voigt-Reuss and
Hashin-Shtrikman bound bands), step 8 (verify G12 against the
Voigt-Reuss and Hashin-Shtrikman bound bands, including the xi = 1
identity), and step 9 (the one-shot unidirectional_lamina_constants
report). Pure stdlib unittest, deterministic, offline, no randomness.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unidirectional_lamina_micromechanics_logic import (
    XI_E2,
    XI_G12,
    e1_longitudinal,
    e2_halpin_tsai,
    e2_hashin_shtrikman_bounds,
    e2_reuss_lower,
    e2_voigt_upper,
    g12_halpin_tsai,
    g12_hashin_shtrikman_bounds,
    g12_reuss_lower,
    g12_voigt_upper,
    nu12_major,
    rho_composite,
    shear_modulus_isotropic,
    unidirectional_lamina_constants,
)

E_F = 230.0e9
NU_F = 0.20
E_FT = 20.0e9
G_F = 27.0e9
E_M = 3.5e9
NU_M = 0.35
V_F = 0.60
RHO_F = 1760.0
RHO_M = 1230.0
G_M = 1296296296.2962961


class TestWorkedExample(unittest.TestCase):
    """Step 1-3 of the SKILL.md workflow: constituent inputs, rule-of-mixtures E1 and nu12."""

    def test_e1_rule_of_mixtures(self):
        self.assertAlmostEqual(e1_longitudinal(E_F, E_M, V_F), 139.4e9, delta=1.0)

    def test_nu12_rule_of_mixtures(self):
        self.assertAlmostEqual(nu12_major(NU_F, NU_M, V_F), 0.26, delta=1e-9)

    def test_e1_magnitude_gate(self):
        e1 = e1_longitudinal(E_F, E_M, V_F)
        self.assertTrue(135.0e9 <= e1 <= 145.0e9)

    def test_matrix_shear_derivation_step2(self):
        g_m = shear_modulus_isotropic(E_M, NU_M)
        self.assertAlmostEqual(g_m, 1296296296.2962961, delta=1.0)


class TestHalpinTsaiPredictions(unittest.TestCase):
    """Step 4-5 of the SKILL.md workflow: Halpin-Tsai E2 and G12 predictions."""

    def test_e2_halpin_tsai_worked_value(self):
        e2 = e2_halpin_tsai(E_FT, E_M, V_F)
        self.assertAlmostEqual(e2 / 9578947368.421053, 1.0, delta=1e-6)

    def test_e2_magnitude_gate(self):
        e2 = e2_halpin_tsai(E_FT, E_M, V_F)
        self.assertTrue(8.0e9 <= e2 <= 12.0e9)

    def test_g12_halpin_tsai_worked_value(self):
        g12 = g12_halpin_tsai(G_F, G_M, V_F)
        self.assertAlmostEqual(g12 / 4402037250.138515, 1.0, delta=1e-6)

    def test_g12_magnitude_gate(self):
        g12 = g12_halpin_tsai(G_F, G_M, V_F)
        self.assertTrue(4.0e9 <= g12 <= 6.0e9)

    def test_shape_factor_constants_fixed(self):
        self.assertEqual(XI_E2, 2.0)
        self.assertEqual(XI_G12, 1.0)


class TestDensityStep6(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: density by the rule of mixtures."""

    def test_rho_composite_worked_value(self):
        self.assertAlmostEqual(rho_composite(RHO_F, RHO_M, V_F), 1548.0, delta=1e-9)

    def test_rho_omitted_without_both_densities(self):
        result = unidirectional_lamina_constants(E_F, NU_F, E_FT, G_F, E_M, NU_M, V_F)
        self.assertNotIn("rho", result)

    def test_rho_present_with_both_densities(self):
        result = unidirectional_lamina_constants(
            E_F, NU_F, E_FT, G_F, E_M, NU_M, V_F, rho_f=RHO_F, rho_m=RHO_M)
        self.assertIn("rho", result)
        self.assertAlmostEqual(result["rho"], 1548.0, delta=1e-9)


class TestE2BoundBandStep7(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: verify E2 against the Voigt-Reuss and Hashin-Shtrikman bands."""

    def test_nested_band_ordering_at_worked_vf(self):
        reuss = e2_reuss_lower(E_FT, E_M, V_F)
        hs_lo, hs_hi = e2_hashin_shtrikman_bounds(E_F, NU_F, E_FT, E_M, NU_M, V_F)
        ht = e2_halpin_tsai(E_FT, E_M, V_F)
        voigt = e2_voigt_upper(E_FT, E_M, V_F)
        self.assertLess(reuss, hs_lo)
        self.assertLess(hs_lo, ht)
        self.assertLess(ht, hs_hi)
        self.assertLess(hs_hi, voigt)

    def test_nested_band_worked_values(self):
        self.assertAlmostEqual(e2_reuss_lower(E_FT, E_M, V_F) / 6930693069.30693, 1.0, delta=1e-6)
        hs_lo, hs_hi = e2_hashin_shtrikman_bounds(E_F, NU_F, E_FT, E_M, NU_M, V_F)
        self.assertAlmostEqual(hs_lo / 8821708541.607254, 1.0, delta=1e-6)
        self.assertAlmostEqual(hs_hi / 10939798623.57372, 1.0, delta=1e-6)
        self.assertAlmostEqual(e2_voigt_upper(E_FT, E_M, V_F) / 13.4e9, 1.0, delta=1e-6)

    def test_e2_in_band_sweep(self):
        for v_f in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            lo, hi = e2_hashin_shtrikman_bounds(E_F, NU_F, E_FT, E_M, NU_M, v_f)
            ht = e2_halpin_tsai(E_FT, E_M, v_f)
            self.assertLessEqual(lo, ht)
            self.assertLessEqual(ht, hi)


class TestG12BoundBandStep8(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: verify G12 against the Voigt-Reuss and Hashin-Shtrikman bands."""

    def test_nested_band_ordering_at_worked_vf(self):
        reuss = g12_reuss_lower(G_F, G_M, V_F)
        hs_lo, hs_hi = g12_hashin_shtrikman_bounds(G_F, G_M, V_F)
        ht = g12_halpin_tsai(G_F, G_M, V_F)
        voigt = g12_voigt_upper(G_F, G_M, V_F)
        self.assertLess(reuss, hs_lo)
        self.assertAlmostEqual(hs_lo, ht, delta=1.0)
        self.assertLess(hs_lo, hs_hi)
        self.assertLess(hs_hi, voigt)

    def test_g12_identity_at_worked_vf(self):
        ht = g12_halpin_tsai(G_F, G_M, V_F)
        hs_lo, _ = g12_hashin_shtrikman_bounds(G_F, G_M, V_F)
        closed = G_M * (G_F * (1 + V_F) + G_M * (1 - V_F)) / (G_F * (1 - V_F) + G_M * (1 + V_F))
        self.assertAlmostEqual(ht / hs_lo, 1.0, delta=1e-9)
        self.assertAlmostEqual(ht / closed, 1.0, delta=1e-9)

    def test_g12_identity_across_volume_fractions(self):
        for v_f in (0.3, 0.5, 0.7):
            ht = g12_halpin_tsai(G_F, G_M, v_f)
            hs_lo, _ = g12_hashin_shtrikman_bounds(G_F, G_M, v_f)
            closed = G_M * (G_F * (1 + v_f) + G_M * (1 - v_f)) / (G_F * (1 - v_f) + G_M * (1 + v_f))
            self.assertAlmostEqual(ht / hs_lo, 1.0, delta=1e-9)
            self.assertAlmostEqual(ht / closed, 1.0, delta=1e-9)


class TestDegeneracies(unittest.TestCase):
    """Boundary cases of the rule-of-mixtures and Halpin-Tsai predictions at V_f = 0 and V_f = 1."""

    def test_pure_matrix_degeneracy(self):
        self.assertAlmostEqual(e1_longitudinal(E_F, E_M, 0.0), E_M, delta=1.0)
        self.assertAlmostEqual(nu12_major(NU_F, NU_M, 0.0), NU_M, delta=1e-9)
        self.assertAlmostEqual(e2_halpin_tsai(E_FT, E_M, 0.0), E_M, delta=1.0)
        self.assertAlmostEqual(g12_halpin_tsai(G_F, G_M, 0.0), G_M, delta=1.0)
        self.assertAlmostEqual(rho_composite(RHO_F, RHO_M, 0.0), RHO_M, delta=1e-9)

    def test_pure_matrix_e2_band_closes(self):
        lo, hi = e2_hashin_shtrikman_bounds(E_F, NU_F, E_FT, E_M, NU_M, 0.0)
        self.assertAlmostEqual(lo / E_M, 1.0, delta=1e-9)
        self.assertAlmostEqual(hi / E_M, 1.0, delta=1e-9)

    def test_pure_fiber_degeneracy(self):
        self.assertAlmostEqual(e1_longitudinal(E_F, E_M, 1.0), E_F, delta=1.0)
        self.assertAlmostEqual(nu12_major(NU_F, NU_M, 1.0), NU_F, delta=1e-9)
        self.assertAlmostEqual(e2_halpin_tsai(E_FT, E_M, 1.0), E_FT, delta=1.0)
        self.assertAlmostEqual(g12_halpin_tsai(G_F, G_M, 1.0), G_F, delta=1.0)
        self.assertAlmostEqual(rho_composite(RHO_F, RHO_M, 1.0), RHO_F, delta=1e-9)

    def test_pure_fiber_e2_band_closes_to_a_point(self):
        lo, hi = e2_hashin_shtrikman_bounds(E_F, NU_F, E_FT, E_M, NU_M, 1.0)
        self.assertAlmostEqual(lo / hi, 1.0, delta=1e-9)
        self.assertAlmostEqual(lo / 20758122743.682312, 1.0, delta=1e-6)


class TestIsotropicFiberCollapse(unittest.TestCase):
    """The isotropic-fiber collapse of the transverse relations (an E-glass-style fiber)."""

    def test_isotropic_fiber_matches_classic_single_modulus_form(self):
        e_f_glass = 72.4e9
        nu_f_glass = 0.22
        g_f_glass = e_f_glass / (2.0 * (1.0 + nu_f_glass))
        e2_module = e2_halpin_tsai(e_f_glass, E_M, 0.5)
        mr = e_f_glass / E_M
        eta = (mr - 1.0) / (mr + XI_E2)
        e2_classic = E_M * (1.0 + XI_E2 * eta * 0.5) / (1.0 - eta * 0.5)
        self.assertAlmostEqual(e2_module / e2_classic, 1.0, delta=1e-12)
        g12_module = g12_halpin_tsai(g_f_glass, shear_modulus_isotropic(E_M, NU_M), 0.5)
        self.assertGreater(g12_module, 0.0)


class TestOneShotReportStep9(unittest.TestCase):
    """Step 9 of the SKILL.md workflow: the unidirectional_lamina_constants one-shot report."""

    def test_report_keys_and_values(self):
        result = unidirectional_lamina_constants(
            E_F, NU_F, E_FT, G_F, E_M, NU_M, V_F, rho_f=RHO_F, rho_m=RHO_M)
        expected_keys = {
            "e1", "nu12", "e2", "g12", "e2_reuss", "e2_voigt", "e2_hs_low",
            "e2_hs_up", "g12_reuss", "g12_voigt", "g12_hs_low", "g12_hs_up", "rho",
        }
        self.assertEqual(set(result.keys()), expected_keys)
        self.assertAlmostEqual(result["e1"] / 139.4e9, 1.0, delta=1e-6)
        self.assertAlmostEqual(result["e2"] / 9578947368.421053, 1.0, delta=1e-6)
        self.assertAlmostEqual(result["g12"] / 4402037250.138515, 1.0, delta=1e-6)

    def test_determinism_two_consecutive_calls(self):
        first = unidirectional_lamina_constants(E_F, NU_F, E_FT, G_F, E_M, NU_M, V_F)
        second = unidirectional_lamina_constants(E_F, NU_F, E_FT, G_F, E_M, NU_M, V_F)
        self.assertEqual(first, second)


class TestValueErrorRejections(unittest.TestCase):
    """ValueError rejection of non-physical constituent-property and fiber-volume-fraction inputs."""

    def test_zero_fiber_modulus(self):
        with self.assertRaisesRegex(ValueError, r"fiber modulus E_f must be a positive number, got 0\.0"):
            e1_longitudinal(0.0, E_M, V_F)

    def test_zero_matrix_modulus(self):
        with self.assertRaisesRegex(ValueError, "matrix modulus E_m must be a positive number"):
            e1_longitudinal(E_F, 0.0, V_F)

    def test_volume_fraction_above_one(self):
        with self.assertRaisesRegex(ValueError, r"fiber volume fraction must be in \[0, 1\], got 1\.5"):
            e1_longitudinal(E_F, E_M, 1.5)

    def test_boolean_volume_fraction(self):
        with self.assertRaisesRegex(ValueError, r"fiber volume fraction must be in \[0, 1\], got True"):
            e1_longitudinal(E_F, E_M, True)

    def test_matrix_poisson_at_bound(self):
        with self.assertRaisesRegex(ValueError, r"matrix Poisson ratio nu_m must be in \[0, 0\.5\), got 0\.5"):
            nu12_major(NU_F, 0.5, V_F)

    def test_fiber_poisson_negative(self):
        with self.assertRaisesRegex(ValueError, "fiber major Poisson ratio nu_f must be in"):
            nu12_major(-0.1, NU_M, V_F)

    def test_zero_fiber_transverse_modulus(self):
        with self.assertRaisesRegex(ValueError, r"fiber transverse modulus E_fT must be a positive number, got 0\.0"):
            e2_halpin_tsai(0.0, E_M, V_F)

    def test_zero_matrix_shear_modulus(self):
        with self.assertRaisesRegex(ValueError, r"matrix shear modulus G_m must be a positive number, got 0\.0"):
            g12_halpin_tsai(G_F, 0.0, V_F)

    def test_non_positive_shape_factor(self):
        with self.assertRaisesRegex(ValueError, "shape factor xi must be a positive number"):
            e2_halpin_tsai(E_FT, E_M, V_F, xi=0.0)

    def test_soft_fiber_shear_phase_rejected(self):
        with self.assertRaisesRegex(ValueError, "the fiber must be the stiffer shear phase"):
            g12_hashin_shtrikman_bounds(G_M, G_F, V_F)

    def test_soft_fiber_cross_section_phase_rejected(self):
        with self.assertRaisesRegex(ValueError, "the fiber must be the stiffer cross-section phase"):
            e2_hashin_shtrikman_bounds(E_F, NU_F, E_M, E_M, NU_M, V_F)

    def test_zero_fiber_density_rejected(self):
        with self.assertRaisesRegex(ValueError, "fiber density rho_f must be a positive number"):
            rho_composite(0.0, RHO_M, V_F)

    def test_shear_modulus_isotropic_rejects_bad_modulus(self):
        with self.assertRaisesRegex(ValueError, r"modulus must be a positive number, got 0\.0"):
            shear_modulus_isotropic(0.0, NU_M)

    def test_shear_modulus_isotropic_rejects_bad_poisson(self):
        with self.assertRaisesRegex(ValueError, r"poisson ratio must be in \[0, 0\.5\), got 0\.5"):
            shear_modulus_isotropic(E_M, 0.5)


class TestDeterminismAndNoExactFloatEquality(unittest.TestCase):
    """Determinism and identity checks written tolerant per the exact-float-assert lesson."""

    def test_no_randomness_module_has_no_random_import(self):
        module_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "unidirectional_lamina_micromechanics_logic.py")
        with open(module_path, "r") as f:
            source = f.read()
        self.assertNotIn("import random", source)
        self.assertIn("import math", source)

    def test_e1_isclose_to_rule_of_mixtures_identity(self):
        e1 = e1_longitudinal(E_F, E_M, V_F)
        identity = V_F * E_F + (1.0 - V_F) * E_M
        self.assertTrue(math.isclose(e1, identity, rel_tol=1e-12))


if __name__ == "__main__":
    unittest.main()

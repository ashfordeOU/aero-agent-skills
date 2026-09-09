"""Contract test for honeycomb-core-micromechanics.

Exercises the SKILL.md Workflow steps: step 1 (derive the foil shear
modulus), step 2 (relative density and core density from cell
geometry), step 3 (out-of-plane compressive and shear moduli), step 4
(in-plane cell-wall-bending moduli), step 5 (the one-shot report), and
step 6 (ValueError rejection of non-physical geometry and foil inputs).
Stdlib unittest, offline, deterministic, no RNG. Portable import: locate
the sibling logic module by file path, no machine-local sys.path.
"""

import importlib.util
import math
import os
import unittest

_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
_SPEC = importlib.util.spec_from_file_location(
    "honeycomb_core_micromechanics_logic",
    os.path.join(_SCRIPTS, "honeycomb-core-micromechanics_logic.py"),
)
hc = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(hc)


class TestHoneycombCoreMicromechanics(unittest.TestCase):
    """Worked-example (SKILL.md Case A) asserts, step 1-5 of the workflow."""

    def setUp(self):
        self.e_s = 72.0e9
        self.nu_s = 0.33
        self.rho_s = 2640.0
        self.t_l = 0.02
        self.h_l = 1.0
        self.theta = 30.0
        self.g_s = hc.shear_modulus_isotropic(self.e_s, self.nu_s)

    def test_step1_foil_shear_modulus_derivation(self):
        """Step 1: derive G_s from E_s and nu_s of the isotropic foil."""
        self.assertAlmostEqual(self.g_s, 27067669172.9323, delta=1.0)

    def test_step2_relative_density_worked_example(self):
        """Step 2: relative_density of the regular-hex cell (Case A)."""
        rd = hc.relative_density(self.t_l, self.h_l, self.theta)
        self.assertAlmostEqual(rd, 0.023094010767585, delta=1e-9)
        self.assertTrue(0.02 <= rd <= 0.026)

    def test_step2_core_density_worked_example(self):
        """Step 2: core_density from the foil density and relative density."""
        rho = hc.core_density(self.rho_s, self.t_l, self.h_l, self.theta)
        self.assertAlmostEqual(rho, 60.9681884264245, delta=1e-6)
        self.assertTrue(55.0 <= rho <= 68.0)

    def test_step3_compressive_modulus_worked_example(self):
        """Step 3: compressive_modulus_e3, the stabilized out-of-plane modulus."""
        e3 = hc.compressive_modulus_e3(self.e_s, self.t_l, self.h_l, self.theta)
        self.assertAlmostEqual(e3, 1662768775.26612, delta=1.0)
        self.assertTrue(1.5e9 <= e3 <= 1.8e9)

    def test_step3_out_of_plane_shear_worked_example(self):
        """Step 3: shear_modulus_g13 and shear_modulus_g23 at the regular hex."""
        g13 = hc.shear_modulus_g13(self.g_s, self.t_l, self.h_l, self.theta)
        g23 = hc.shear_modulus_g23(self.g_s, self.t_l, self.h_l, self.theta)
        self.assertAlmostEqual(g13, 312550521.666564, delta=1.0)
        self.assertAlmostEqual(g23, 312550521.666564, delta=1.0)
        self.assertTrue(0.25e9 <= g13 <= 0.40e9)
        self.assertTrue(0.25e9 <= g23 <= 0.40e9)

    def test_step4_inplane_moduli_worked_example(self):
        """Step 4: inplane_modulus_e1/e2 and inplane_shear_modulus_g12."""
        e1 = hc.inplane_modulus_e1(self.e_s, self.t_l, self.h_l, self.theta)
        e2 = hc.inplane_modulus_e2(self.e_s, self.t_l, self.h_l, self.theta)
        g12 = hc.inplane_shear_modulus_g12(self.e_s, self.t_l, self.h_l, self.theta)
        self.assertAlmostEqual(e1, 1330215.0202129, delta=1e-3)
        self.assertAlmostEqual(e2, 1330215.0202129, delta=1e-3)
        self.assertAlmostEqual(g12, 332553.755053225, delta=1e-3)

    def test_step2_regular_hexagon_reduction_identity(self):
        """Step 2 identity: relative_density reduces to (2/sqrt(3)) t/l."""
        for t_l in (0.01, 0.02, 0.05):
            rd = hc.relative_density(t_l, 1.0, 30.0)
            expected = (2.0 / math.sqrt(3.0)) * t_l
            self.assertTrue(math.isclose(rd, expected, rel_tol=1e-9))

    def test_step3_regular_hexagon_shear_reduction_identity(self):
        """Step 3 identity: G13 = G23 = G_s (rho*/rho_s)/2 at the regular hex."""
        for t_l in (0.01, 0.02, 0.05):
            rd = hc.relative_density(t_l, 1.0, 30.0)
            expected = self.g_s * rd / 2.0
            g13 = hc.shear_modulus_g13(self.g_s, t_l, 1.0, 30.0)
            g23 = hc.shear_modulus_g23(self.g_s, t_l, 1.0, 30.0)
            self.assertTrue(math.isclose(g13, expected, rel_tol=1e-9))
            self.assertTrue(math.isclose(g23, expected, rel_tol=1e-9))

    def test_step3_g13_g23_ordering_sweep(self):
        """Step 3 sanity: g13/g23 tracks the closed-form ratio across h/l."""
        theta = 30.0
        theta_rad = math.radians(theta)
        expected_ratios = {
            0.5: 0.375000000,
            0.8: 0.738461538,
            1.0: 1.000000000,
            1.2: 1.270588235,
            1.5: 1.687500000,
            2.0: 2.400000000,
        }
        for h_l, expected in expected_ratios.items():
            g13 = hc.shear_modulus_g13(self.g_s, 0.02, h_l, theta)
            g23 = hc.shear_modulus_g23(self.g_s, 0.02, h_l, theta)
            ratio = g13 / g23
            closed_form = ((h_l ** 2) * (math.cos(theta_rad) ** 2) *
                            (2.0 * h_l + 1.0)) / ((h_l + math.sin(theta_rad)) ** 2)
            self.assertTrue(math.isclose(ratio, closed_form, rel_tol=1e-12))
            self.assertAlmostEqual(ratio, expected, delta=1e-6)
        self.assertTrue(hc.shear_modulus_g13(self.g_s, 0.02, 2.0, theta) >
                         hc.shear_modulus_g23(self.g_s, 0.02, 2.0, theta))
        self.assertTrue(hc.shear_modulus_g13(self.g_s, 0.02, 0.5, theta) <
                         hc.shear_modulus_g23(self.g_s, 0.02, 0.5, theta))

    def test_step4_inplane_isotropy_degeneracy(self):
        """Step 4 identity: E1* = E2* and G12* = E1*/4 at the regular hex."""
        e1 = hc.inplane_modulus_e1(self.e_s, self.t_l, self.h_l, self.theta)
        e2 = hc.inplane_modulus_e2(self.e_s, self.t_l, self.h_l, self.theta)
        g12 = hc.inplane_shear_modulus_g12(self.e_s, self.t_l, self.h_l, self.theta)
        self.assertTrue(math.isclose(e1, e2, rel_tol=1e-9))
        self.assertTrue(math.isclose(g12, e1 / 4.0, rel_tol=1e-9))

    def test_case_b_corpus_geometry(self):
        """Corpus query 1 geometry: the 3.2 mm cell, 0.038 mm foil 5056 core."""
        l = 3.2 / math.sqrt(3.0)
        t_l = 0.038 / l
        rd = hc.relative_density(t_l, 1.0, 30.0)
        self.assertTrue(math.isclose(rd, 0.02375, rel_tol=1e-9))
        e3 = hc.compressive_modulus_e3(self.e_s, t_l, 1.0, 30.0)
        self.assertAlmostEqual(e3, 1710000000.0, delta=1.0)
        rho = hc.core_density(self.rho_s, t_l, 1.0, 30.0)
        self.assertAlmostEqual(rho, 62.7, delta=1e-6)
        g13 = hc.shear_modulus_g13(self.g_s, t_l, 1.0, 30.0)
        g23 = hc.shear_modulus_g23(self.g_s, t_l, 1.0, 30.0)
        self.assertTrue(math.isclose(g13, g23, rel_tol=1e-9))

    def test_case_c_elongated_cell_ordering_and_magnitude(self):
        """Corpus query 2 geometry: 7075 foil, elongated cell h/l = 1.5."""
        e_s, nu_s, rho_s = 71.7e9, 0.33, 2810.0
        g_s = hc.shear_modulus_isotropic(e_s, nu_s)
        g13 = hc.shear_modulus_g13(g_s, 0.02, 1.5, 30.0)
        g23 = hc.shear_modulus_g23(g_s, 0.02, 1.5, 30.0)
        self.assertTrue(math.isclose(g13 / g23, 1.6875, rel_tol=1e-9))
        self.assertGreater(g13, g23)
        e3 = hc.compressive_modulus_e3(e_s, 0.02, 1.5, 30.0)
        self.assertAlmostEqual(e3, 1448860500.53137, delta=1e-3)

    def test_e3_linear_scaling_in_foil_modulus(self):
        """E3 is exactly linear in E_s at fixed geometry (stabilized core)."""
        e3_a = hc.compressive_modulus_e3(self.e_s, self.t_l, self.h_l, self.theta)
        e3_b = hc.compressive_modulus_e3(2.0 * self.e_s, self.t_l, self.h_l, self.theta)
        self.assertTrue(math.isclose(e3_b, 2.0 * e3_a, rel_tol=1e-12))

    def test_step5_one_shot_report_dict(self):
        """Step 5: honeycomb_core_properties reports all eleven keys."""
        d = hc.honeycomb_core_properties(
            self.e_s, self.nu_s, self.rho_s, self.t_l, self.h_l, self.theta)
        expected_keys = {
            "relative_density", "core_density", "e3", "g13", "g23",
            "e1", "e2", "g12", "e3_over_es", "g13_over_gs", "g23_over_gs",
        }
        self.assertEqual(set(d.keys()), expected_keys)
        self.assertEqual(len(d), 11)

    def test_step5_one_shot_report_matches_explicit_gs(self):
        """Step 5: g_s=None derivation matches an explicit shear_modulus_isotropic."""
        d_derived = hc.honeycomb_core_properties(
            self.e_s, self.nu_s, self.rho_s, self.t_l, self.h_l, self.theta)
        d_explicit = hc.honeycomb_core_properties(
            self.e_s, self.nu_s, self.rho_s, self.t_l, self.h_l, self.theta,
            g_s=self.g_s)
        for key in d_derived:
            self.assertTrue(math.isclose(d_derived[key], d_explicit[key],
                                          rel_tol=1e-12))

    def test_step1_shear_modulus_isotropic_worked_value(self):
        """Step 1 worked value: shear_modulus_isotropic(72.0e9, 0.33)."""
        self.assertAlmostEqual(self.g_s, 27067669172.9323, delta=1e-3)

    def test_step6_value_error_t_l_bounds(self):
        """Step 6: ValueError on t/l at 0.0, 1.0 and a boolean."""
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError) as ctx:
                hc.relative_density(bad, 1.0, 30.0)
            self.assertIn("wall thickness to edge-length ratio t/l must be "
                           "in (0, 1)", str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            hc.relative_density(True, 1.0, 30.0)
        self.assertIn("got True", str(ctx.exception))

    def test_step6_value_error_h_l_bounds(self):
        """Step 6: ValueError on h/l at 0.0 and negative."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError) as ctx:
                hc.relative_density(0.02, bad, 30.0)
            self.assertIn("cell aspect ratio h/l must be a positive number",
                           str(ctx.exception))

    def test_step6_value_error_theta_bounds(self):
        """Step 6: ValueError on theta at 0.0, 90.0 and negative degrees."""
        for bad in (0.0, 90.0, -30.0):
            with self.assertRaises(ValueError) as ctx:
                hc.relative_density(0.02, 1.0, bad)
            self.assertIn("cell angle theta must be in (0, 90) degrees",
                           str(ctx.exception))

    def test_step6_value_error_foil_modulus(self):
        """Step 6: ValueError on E_s at 0.0 and a boolean."""
        with self.assertRaises(ValueError) as ctx:
            hc.compressive_modulus_e3(0.0, 0.02, 1.0, 30.0)
        self.assertIn("foil modulus E_s must be a positive number",
                       str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            hc.shear_modulus_isotropic(True, 0.33)
        self.assertIn("got True", str(ctx.exception))

    def test_step6_value_error_poisson_ratio(self):
        """Step 6: ValueError on nu_s at or above 0.5."""
        with self.assertRaises(ValueError) as ctx:
            hc.shear_modulus_isotropic(72.0e9, 0.5)
        self.assertIn("foil Poisson ratio nu_s must be in [0, 0.5)",
                       str(ctx.exception))

    def test_step6_value_error_foil_density(self):
        """Step 6: ValueError on rho_s at 0.0."""
        with self.assertRaises(ValueError) as ctx:
            hc.core_density(0.0, 0.02, 1.0, 30.0)
        self.assertIn("foil density rho_s must be a positive number",
                       str(ctx.exception))

    def test_step6_value_error_explicit_shear_modulus(self):
        """Step 6: ValueError on an explicit g_s at 0.0."""
        with self.assertRaises(ValueError) as ctx:
            hc.shear_modulus_g13(0.0, 0.02, 1.0, 30.0)
        self.assertIn("foil shear modulus G_s must be a positive number",
                       str(ctx.exception))
        with self.assertRaises(ValueError) as ctx:
            hc.honeycomb_core_properties(
                self.e_s, self.nu_s, self.rho_s, self.t_l, self.h_l,
                self.theta, g_s=0.0)
        self.assertIn("foil shear modulus G_s must be a positive number",
                       str(ctx.exception))

    def test_determinism_repeated_calls(self):
        """Determinism: two consecutive one-shot calls return identical dicts."""
        d1 = hc.honeycomb_core_properties(
            self.e_s, self.nu_s, self.rho_s, self.t_l, self.h_l, self.theta)
        d2 = hc.honeycomb_core_properties(
            self.e_s, self.nu_s, self.rho_s, self.t_l, self.h_l, self.theta)
        self.assertEqual(d1, d2)

    def test_no_imports_beyond_math(self):
        """Determinism: the logic module imports only math from stdlib."""
        with open(hc.__file__) as f:
            source = f.read()
        import_lines = [line for line in source.splitlines()
                         if line.startswith("import ") or line.startswith("from ")]
        self.assertEqual(import_lines, ["import math"])


if __name__ == "__main__":
    unittest.main()

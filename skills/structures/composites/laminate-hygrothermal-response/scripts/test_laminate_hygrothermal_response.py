"""Contract test: laminate hygrothermal response (structures/composites).

Offline deterministic stdlib unittest.  Run: python3
scripts/test_laminate_hygrothermal_response.py  (from the leaf dir or
repo root with the full path).  Exits 0 on PASS.

Covers the worked example (T300/5208-style [0/90]s carbon/epoxy), the
exact 2x2 CLT inversion identity for a 0-deg unidirectional laminate,
equilibrium moisture isotherm endpoints, plane-stress Q and Qbar
rotation invariants, cure-cooldown sign, ValueError rejection of
non-physical inputs, determinism, and the one-call convenience dict.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from laminate_hygrothermal_response_logic import (  # noqa: E402
    M_SAT_DEFAULT,
    cte_ppm,
    cure_cooldown_strain,
    equilibrium_moisture_content,
    hygrothermal_strain,
    laminate_cte_cme,
    laminate_hygrothermal_response,
    plane_stress_q,
    qbar,
)


class LaminateHygrothermalResponseContract(unittest.TestCase):
    """Contract checks for the worked example and exact CLT inversion."""

    def setUp(self):
        # T300/5208-style carbon/epoxy ply (material properties are inputs).
        self.e1 = 181e9
        self.e2 = 10.3e9
        self.nu12 = 0.28
        self.g12 = 7.17e9
        self.alpha_1 = -0.3e-6
        self.alpha_2 = 28.1e-6
        self.beta_1 = 0.0
        self.beta_2 = 0.6
        self.t = 0.125e-3
        self.ply0 = {
            "e1": self.e1, "e2": self.e2, "nu12": self.nu12,
            "g12": self.g12, "theta_deg": 0.0, "t": self.t,
            "alpha_1": self.alpha_1, "alpha_2": self.alpha_2,
            "beta_1": self.beta_1, "beta_2": self.beta_2,
        }
        self.ply90 = dict(self.ply0, theta_deg=90.0)
        self.crossply = [self.ply0, self.ply90, self.ply90, self.ply0]

    # ---- plane-stress reduced stiffness Q ---------------------------
    def test_plane_stress_q_worked_values(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        # Real outputs q11 = 181.81e9, q22 = 10.346e9, q66 = g12.
        self.assertAlmostEqual(q["q11"], 181.8e9, delta=0.03e9)
        self.assertAlmostEqual(q["q22"], 10.35e9, delta=0.03e9)
        self.assertEqual(q["q66"], self.g12)

    def test_plane_stress_q12_nu21_symmetry_and_isotropy(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        nu21 = self.nu12 * self.e2 / self.e1
        denom = 1.0 - self.nu12 * nu21
        self.assertAlmostEqual(q["q12"], self.nu12 * self.e2 / denom,
                               delta=1.0)
        self.assertAlmostEqual(q["q12"], nu21 * self.e1 / denom, delta=1.0)
        iso = plane_stress_q(70e9, 70e9, 0.3, 26.9e9)
        expected = 70e9 / (1.0 - 0.09)
        self.assertAlmostEqual(iso["q11"], expected, delta=1.0)
        self.assertAlmostEqual(iso["q12"], 0.3 * expected, delta=1.0)

    def test_plane_stress_nonpositive_moduli_raise(self):
        for bad in ((0.0, self.e2, self.nu12, self.g12),
                    (self.e1, -1.0, self.nu12, self.g12),
                    (self.e1, self.e2, self.nu12, 0.0)):
            with self.assertRaises(ValueError):
                plane_stress_q(*bad)

    def test_plane_stress_nu12nu21_ge_one_raises(self):
        with self.assertRaises(ValueError):
            plane_stress_q(1.0, 1000.0, 0.5, 1.0)  # nu12*nu21 = 250

    # ---- rotated stiffness Qbar -------------------------------------
    def test_qbar_zero_deg_equals_q(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        qb = qbar(q, 0.0)
        for key, qkey in (("qbar11", "q11"), ("qbar22", "q22"),
                          ("qbar12", "q12"), ("qbar66", "q66")):
            self.assertAlmostEqual(qb[key], q[qkey], delta=1.0)
        self.assertAlmostEqual(qb["qbar16"], 0.0, delta=1e-3)
        self.assertAlmostEqual(qb["qbar26"], 0.0, delta=1e-3)

    def test_qbar_90_deg_swaps_and_coupling_zero(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        qb = qbar(q, 90.0)
        self.assertAlmostEqual(qb["qbar11"], q["q22"], delta=1.0)
        self.assertAlmostEqual(qb["qbar22"], q["q11"], delta=1.0)
        self.assertAlmostEqual(qb["qbar12"], q["q12"], delta=1.0)
        self.assertAlmostEqual(qb["qbar66"], q["q66"], delta=1.0)
        self.assertAlmostEqual(qb["qbar16"], 0.0, delta=1e-3)
        self.assertAlmostEqual(qb["qbar26"], 0.0, delta=1e-3)

    def test_qbar_plus_minus_90_identical(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        pos = qbar(q, 90.0)
        neg = qbar(q, -90.0)
        for key in pos:
            self.assertAlmostEqual(pos[key], neg[key], delta=1.0)

    def test_qbar_rotation_trace_invariant_and_45_coupling(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        trace0 = q["q11"] + q["q22"] + 2.0 * q["q12"]
        for angle in (15.0, 30.0, 45.0, 60.0, 75.0):
            qb = qbar(q, angle)
            trace = qb["qbar11"] + qb["qbar22"] + 2.0 * qb["qbar12"]
            self.assertAlmostEqual(trace, trace0, delta=1.0)
        qb45 = qbar(q, 45.0)
        self.assertAlmostEqual(qb45["qbar16"], qb45["qbar26"], delta=1.0)

    def test_qbar_coupling_antisymmetric_in_angle(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        pos = qbar(q, 30.0)
        neg = qbar(q, -30.0)
        self.assertAlmostEqual(pos["qbar16"], -neg["qbar16"], delta=1.0)
        self.assertAlmostEqual(pos["qbar26"], -neg["qbar26"], delta=1.0)

    def test_qbar_nonfinite_angle_raises(self):
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        with self.assertRaises(ValueError):
            qbar(q, float("nan"))

    # ---- exact CLT laminate CTE/CME (2x2 inversion) -----------------
    def test_crossply_alpha_worked_band(self):
        coefs = laminate_cte_cme(self.crossply)
        # Real module output 1.599982e-6/K; spec band 1.55-1.70 ppm.
        self.assertTrue(1.55e-6 <= coefs["alpha_x"] <= 1.70e-6,
                        coefs["alpha_x"])
        self.assertAlmostEqual(coefs["alpha_x"], 1.60e-6, delta=0.02e-6)
        self.assertAlmostEqual(coefs["alpha_x"], coefs["alpha_y"],
                               delta=1e-18)

    def test_crossply_beta_worked_band(self):
        coefs = laminate_cte_cme(self.crossply)
        # Real module output 0.040140 per unit moisture fraction.
        self.assertTrue(0.035 <= coefs["beta_x"] <= 0.045, coefs["beta_x"])
        self.assertAlmostEqual(coefs["beta_x"], 0.040, delta=0.002)
        self.assertAlmostEqual(coefs["beta_x"], coefs["beta_y"],
                               delta=1e-15)

    def test_uni_alpha_x_identity_exact(self):
        # 0-deg unidirectional must return alpha_1 exactly (full 2x2
        # inversion; real output diff from alpha_1 is 0.0).
        uni = [self.ply0, self.ply0, self.ply0, self.ply0]
        coefs = laminate_cte_cme(uni)
        self.assertAlmostEqual(coefs["alpha_x"], self.alpha_1, delta=1e-20)
        self.assertAlmostEqual(coefs["alpha_y"], self.alpha_2, delta=1e-12)

    def test_uni_beta_x_identity(self):
        uni = [self.ply0, self.ply0, self.ply0, self.ply0]
        coefs = laminate_cte_cme(uni)
        self.assertAlmostEqual(coefs["beta_x"], self.beta_1, delta=1e-15)
        self.assertAlmostEqual(coefs["beta_y"], self.beta_2, delta=1e-12)

    def test_uni_45_deg_rotation_identity(self):
        # A single 45-deg ply returns the transformed material coefficient.
        theta = 45.0
        m2 = math.cos(math.radians(theta)) ** 2
        n2 = math.sin(math.radians(theta)) ** 2
        ply45 = dict(self.ply0, theta_deg=theta)
        coefs = laminate_cte_cme([ply45])
        self.assertAlmostEqual(coefs["alpha_x"],
                               self.alpha_1 * m2 + self.alpha_2 * n2,
                               delta=1e-12)
        self.assertAlmostEqual(coefs["beta_x"],
                               self.beta_1 * m2 + self.beta_2 * n2,
                               delta=1e-12)

    def test_weighted_average_formula_matches_direct_sum(self):
        # 1D stiffness-weighted average formula vs direct ply-by-ply
        # sum over the [0/90]s; real value 1.229117e-6/K inside the
        # 0-5 ppm band.  This differs from the exact 1.60 ppm CLT
        # inversion, which is why the exact 2x2 solve is required.
        q = plane_stress_q(self.e1, self.e2, self.nu12, self.g12)
        qb0 = qbar(q, 0.0)
        qb90 = qbar(q, 90.0)
        formula = (qb0["qbar11"] * self.alpha_1
                   + qb90["qbar11"] * self.alpha_2) \
            / (qb0["qbar11"] + qb90["qbar11"])
        num = 0.0
        den = 0.0
        for ply in self.crossply:
            qb = qbar(plane_stress_q(ply["e1"], ply["e2"], ply["nu12"],
                                     ply["g12"]), ply["theta_deg"])
            ax = self.alpha_1 if ply["theta_deg"] == 0.0 else self.alpha_2
            num += qb["qbar11"] * ply["t"] * ax
            den += qb["qbar11"] * ply["t"]
        direct = num / den
        self.assertAlmostEqual(formula, direct, delta=1e-12)
        self.assertTrue(0.0 <= formula <= 5e-6, formula)
        self.assertAlmostEqual(formula, 1.23e-6, delta=0.05e-6)

    def test_laminate_cte_cme_input_validation(self):
        with self.assertRaises(ValueError):
            laminate_cte_cme([])
        for bad_t in (0.0, -1e-4):
            with self.assertRaises(ValueError):
                laminate_cte_cme([dict(self.ply0, t=bad_t)])
        for bad_angle in (95.0, -91.0):
            with self.assertRaises(ValueError):
                laminate_cte_cme([dict(self.ply0, theta_deg=bad_angle)])

    def test_laminate_cte_cme_deterministic(self):
        self.assertEqual(laminate_cte_cme(self.crossply),
                         laminate_cte_cme(self.crossply))

    # ---- equilibrium moisture content --------------------------------
    def test_moisture_worked_value_and_endpoints(self):
        # Real output 0.009 at RH 0.6, m_sat 0.015; endpoints exact.
        self.assertAlmostEqual(equilibrium_moisture_content(0.6, 0.015),
                               0.009, delta=1e-15)
        self.assertEqual(equilibrium_moisture_content(0.0), 0.0)
        self.assertEqual(equilibrium_moisture_content(1.0, 0.015), 0.015)
        self.assertAlmostEqual(equilibrium_moisture_content(0.3), 0.0045,
                               delta=1e-15)

    def test_moisture_rh_outside_unit_range_raises(self):
        with self.assertRaises(ValueError):
            equilibrium_moisture_content(-0.1)
        with self.assertRaises(ValueError):
            equilibrium_moisture_content(1.1)

    def test_moisture_m_sat_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            equilibrium_moisture_content(0.6, 0.0)
        with self.assertRaises(ValueError):
            equilibrium_moisture_content(0.6, -0.01)

    # ---- hygrothermal and cure-cooldown strain ----------------------
    def test_cure_strain_worked_value_and_default_rt(self):
        coefs = laminate_cte_cme(self.crossply)
        # Real output -2.495972e-4 = alpha_x * (21 - 177) K.
        eps = cure_cooldown_strain(coefs["alpha_x"], 177.0, 21.0)
        self.assertAlmostEqual(eps, -2.50e-4, delta=0.05e-4)
        self.assertLess(eps, 0.0)
        self.assertAlmostEqual(eps, cure_cooldown_strain(coefs["alpha_x"],
                                                         177.0),
                               delta=1e-20)

    def test_cure_strain_sign_positive_alpha_cooldown(self):
        # Cooling (delta_t < 0) with positive alpha gives negative strain.
        eps = cure_cooldown_strain(1.0e-6, 200.0, 21.0)
        self.assertAlmostEqual(eps, -179.0e-6, delta=1e-18)
        self.assertLess(eps, 0.0)

    def test_hygrothermal_strain_zero_deltas(self):
        self.assertEqual(hygrothermal_strain(1.6e-6, 0.04, 0.0, 0.0), 0.0)

    def test_hygrothermal_strain_moisture_branch_worked(self):
        # Real output 3.612641e-4 = beta_x * 0.009 (dT = 0 branch).
        eps = hygrothermal_strain(1.6e-6, 0.04014045913085838, 0.0, 0.009)
        self.assertAlmostEqual(eps, 3.6e-4, delta=0.05e-4)

    def test_hygrothermal_strain_combined_worked(self):
        # Real output 1.116670e-4 for dT = -156 K, dM = 0.009.
        eps = hygrothermal_strain(1.5999817321939641e-06,
                                  0.04014045913085838, -156.0, 0.009)
        self.assertAlmostEqual(eps, 1.12e-4, delta=0.05e-4)

    def test_hygrothermal_strain_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            hygrothermal_strain(float("inf"), 0.04, 1.0, 0.01)
        with self.assertRaises(ValueError):
            hygrothermal_strain(1e-6, 0.04, float("nan"), 0.01)

    # ---- reporting helper -------------------------------------------
    def test_cte_ppm_helper(self):
        self.assertAlmostEqual(cte_ppm(1.6e-6), 1.6, delta=1e-12)
        self.assertEqual(cte_ppm(0.0), 0.0)

    # ---- one-call convenience dict ----------------------------------
    def test_convenience_keys_and_worked_values(self):
        result = laminate_hygrothermal_response(
            self.crossply, 0.6, -156.0, m_sat=M_SAT_DEFAULT, t_cure_c=177.0)
        self.assertEqual(
            set(result),
            {"equilibrium_moisture_content", "alpha_x", "alpha_y",
             "beta_x", "beta_y", "hygrothermal_strain_x",
             "hygrothermal_strain_y", "cure_strain_x"})
        self.assertAlmostEqual(result["equilibrium_moisture_content"],
                               0.009, delta=1e-15)
        self.assertAlmostEqual(result["alpha_x"], 1.60e-6, delta=0.02e-6)
        self.assertAlmostEqual(result["beta_x"], 0.040, delta=0.002)
        self.assertAlmostEqual(result["cure_strain_x"], -2.50e-4,
                               delta=0.05e-4)
        self.assertAlmostEqual(result["hygrothermal_strain_x"], 1.12e-4,
                               delta=0.05e-4)
        self.assertAlmostEqual(result["hygrothermal_strain_y"],
                               result["hygrothermal_strain_x"], delta=1e-18)

    def test_convenience_default_delta_m_equals_equilibrium(self):
        with_default = laminate_hygrothermal_response(
            self.crossply, 0.6, -156.0, t_cure_c=177.0)
        with_explicit = laminate_hygrothermal_response(
            self.crossply, 0.6, -156.0, delta_m=0.009, t_cure_c=177.0)
        self.assertAlmostEqual(with_default["equilibrium_moisture_content"],
                               0.009, delta=1e-15)
        self.assertAlmostEqual(with_default["hygrothermal_strain_x"],
                               with_explicit["hygrothermal_strain_x"],
                               delta=1e-20)

    def test_convenience_cure_strain_none_without_cure_temp(self):
        result = laminate_hygrothermal_response(self.crossply, 0.6, -156.0)
        self.assertIsNone(result["cure_strain_x"])

    def test_convenience_raises_on_bad_inputs(self):
        with self.assertRaises(ValueError):
            laminate_hygrothermal_response(self.crossply, 1.5, -156.0)
        with self.assertRaises(ValueError):
            laminate_hygrothermal_response([], 0.6, -156.0)


if __name__ == "__main__":
    unittest.main()

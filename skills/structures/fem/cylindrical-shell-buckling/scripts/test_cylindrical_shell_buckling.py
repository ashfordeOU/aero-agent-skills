"""Offline contract test for cylindrical_shell_buckling_logic.

Deterministic, stdlib-only unittest. Run:

    python3 test_cylindrical_shell_buckling.py

Covers the NASA SP-8007 worked example (aluminum barrel r=1.5 m,
t=0.005 m, E=70 GPa) with the spec magnitude bounds, r/t=100 knockdown
values, monotonicity and unit-interval bounds, ValueError rejection of
non-physical inputs, closed-form identities, the plasticity correction,
determinism, and the assessment dict contract.
"""

import math
import unittest

from cylindrical_shell_buckling_logic import (
    K_AXIAL_A,
    K_AXIAL_B,
    K_BEND_A,
    K_OVAL,
    R_T_LIMIT,
    axial_critical_stress,
    bending_critical_moment,
    curvature_parameter,
    knockdown_axial,
    knockdown_bending,
    ovalization_collapse_moment,
    plasticity_correction,
    shell_buckling_assessment,
)

E = 70e9
R = 1.5
T = 0.005
RT300 = 300.0
PHI_WORKED = 1.0825317547305484
GAMMA_AX_WORKED = 0.4042018933041497
GAMMA_B_WORKED = 0.5166166304165742
SIGMA_WORKED = 57059833.93810246
MCR_WORKED = 2577525.304088723
MOV_WORKED = 2715974.9763419
RT100_AX = 0.5812705470956102
RT100_B = 0.6602761042473819


class TestWorkedExample(unittest.TestCase):
    def test_curvature_parameter_worked(self):
        self.assertAlmostEqual(curvature_parameter(R, T), PHI_WORKED, places=9)

    def test_gamma_axial_worked(self):
        g = knockdown_axial(R, T)
        self.assertAlmostEqual(g, GAMMA_AX_WORKED, places=9)
        self.assertGreater(g, 0.35)
        self.assertLess(g, 0.45)

    def test_gamma_bending_worked(self):
        g = knockdown_bending(R, T)
        self.assertAlmostEqual(g, GAMMA_B_WORKED, places=9)
        self.assertGreater(g, 0.45)
        self.assertLess(g, 0.60)

    def test_sigma_cr_worked(self):
        s = axial_critical_stress(E, T, R)
        self.assertAlmostEqual(s / 1e6, SIGMA_WORKED / 1e6, places=3)
        self.assertGreater(s / 1e6, 50.0)
        self.assertLess(s / 1e6, 65.0)

    def test_m_cr_bending_worked(self):
        m = bending_critical_moment(E, T, R)
        self.assertAlmostEqual(m, MCR_WORKED, delta=10.0)
        self.assertGreater(m, 2.2e6)
        self.assertLess(m, 3.0e6)

    def test_m_ov_worked(self):
        m = ovalization_collapse_moment(E, T, R)
        self.assertAlmostEqual(m, MOV_WORKED, delta=10.0)
        self.assertGreater(m, 2.4e6)
        self.assertLess(m, 3.1e6)

    def test_governing_bifurcation_worked(self):
        out = shell_buckling_assessment(E, T, R)
        self.assertLess(out["m_cr_bending_Nm"], out["m_cr_ovalization_Nm"])
        self.assertEqual(out["governing"], "bifurcation")

    def test_governing_ovalization_rt100(self):
        # r/t = 100: bending knockdown is high (0.660), so ovalization
        # collapse moment governs instead.
        out = shell_buckling_assessment(E, 0.01, 1.0)
        self.assertGreater(out["m_cr_bending_Nm"], out["m_cr_ovalization_Nm"])
        self.assertEqual(out["governing"], "ovalization")

    def test_gamma_rt100_values(self):
        self.assertAlmostEqual(knockdown_axial(1.0, 0.01), RT100_AX, places=9)
        self.assertAlmostEqual(knockdown_bending(1.0, 0.01), RT100_B, places=9)


class TestGammaProperties(unittest.TestCase):
    RT_SERIES = [100.0, 200.0, 300.0, 500.0, 800.0, 1200.0, 1400.0]

    def test_gamma_axial_bounds_unit_interval(self):
        for rt in self.RT_SERIES:
            g = knockdown_axial(math.sqrt(rt), 1.0)
            self.assertGreater(g, 0.0)
            self.assertLess(g, 1.0)

    def test_gamma_bending_bounds_unit_interval(self):
        for rt in self.RT_SERIES:
            g = knockdown_bending(math.sqrt(rt), 1.0)
            self.assertGreater(g, 0.0)
            self.assertLess(g, 1.0)

    def test_gamma_axial_monotonic_decreasing(self):
        values = [knockdown_axial(math.sqrt(rt), 1.0) for rt in self.RT_SERIES]
        for hi, lo in zip(values, values[1:]):
            self.assertGreater(hi, lo)

    def test_gamma_bending_monotonic_decreasing(self):
        values = [knockdown_bending(math.sqrt(rt), 1.0) for rt in self.RT_SERIES]
        for hi, lo in zip(values, values[1:]):
            self.assertGreater(hi, lo)

    def test_gamma_closed_form_exact(self):
        # gamma = 1 - K*(1 - exp(-phi)) exactly for both knockdown factors.
        phi = curvature_parameter(R, T)
        self.assertAlmostEqual(
            knockdown_axial(R, T),
            1.0 - K_AXIAL_A * (1.0 - math.exp(-phi)),
            places=12,
        )
        self.assertAlmostEqual(
            knockdown_bending(R, T),
            1.0 - K_BEND_A * (1.0 - math.exp(-phi)),
            places=12,
        )


class TestValueErrors(unittest.TestCase):
    def test_valueerror_radius_nonpositive(self):
        for fn in (curvature_parameter, knockdown_axial, knockdown_bending):
            with self.assertRaises(ValueError):
                fn(0.0, T)
            with self.assertRaises(ValueError):
                fn(-1.5, T)
        with self.assertRaises(ValueError):
            axial_critical_stress(E, T, 0.0)
        with self.assertRaises(ValueError):
            bending_critical_moment(E, T, -1.0)

    def test_valueerror_thickness_nonpositive(self):
        for fn in (curvature_parameter, knockdown_axial, knockdown_bending):
            with self.assertRaises(ValueError):
                fn(R, 0.0)
            with self.assertRaises(ValueError):
                fn(R, -0.005)
        with self.assertRaises(ValueError):
            axial_critical_stress(E, 0.0, R)

    def test_valueerror_rt_over_limit_geometry(self):
        # r/t = 1600 exceeds the SP-8007 validity guard of 1500.
        with self.assertRaises(ValueError):
            curvature_parameter(1.6, 0.001)
        with self.assertRaises(ValueError):
            knockdown_axial(1.6, 0.001)
        with self.assertRaises(ValueError):
            knockdown_bending(1.6, 0.001)

    def test_valueerror_rt_over_limit_stress_functions(self):
        with self.assertRaises(ValueError):
            axial_critical_stress(E, 0.001, 1.6)
        with self.assertRaises(ValueError):
            bending_critical_moment(E, 0.001, 1.6)
        with self.assertRaises(ValueError):
            ovalization_collapse_moment(E, 0.001, 1.6)
        with self.assertRaises(ValueError):
            shell_buckling_assessment(E, 0.001, 1.6)
        # r/t exactly at the guard limit must also raise (>= R_T_LIMIT).
        with self.assertRaises(ValueError):
            curvature_parameter(R_T_LIMIT, 1.0)


    def test_valueerror_nonpositive_modulus(self):
        for fn in (axial_critical_stress, bending_critical_moment,
                   ovalization_collapse_moment):
            with self.assertRaises(ValueError):
                fn(0.0, T, R)
            with self.assertRaises(ValueError):
                fn(-70e9, T, R)

    def test_valueerror_ovalization_nu_out_of_range(self):
        for nu in (-1.0, 1.0, 1.2, -3.0):
            with self.assertRaises(ValueError):
                ovalization_collapse_moment(E, T, R, nu=nu)

    def test_valueerror_plasticity_nonpositive(self):
        with self.assertRaises(ValueError):
            plasticity_correction(0.0, E, E)
        with self.assertRaises(ValueError):
            plasticity_correction(E, -E, E)
        with self.assertRaises(ValueError):
            plasticity_correction(E, E, 0.0)


class TestIdentities(unittest.TestCase):
    def test_sigma_explicit_gamma_identity(self):
        gamma = 0.45
        expect = K_AXIAL_B * gamma * E * T / R
        self.assertAlmostEqual(axial_critical_stress(E, T, R, gamma=gamma),
                               expect, places=1)

    def test_sigma_default_gamma_matches_internal(self):
        got = axial_critical_stress(E, T, R)
        expect = K_AXIAL_B * knockdown_axial(R, T) * E * T / R
        self.assertAlmostEqual(got, expect, places=1)

    def test_moment_explicit_gamma_identity(self):
        gamma = 0.5
        expect = math.pi * K_AXIAL_B * gamma * E * T**2 * R
        self.assertAlmostEqual(bending_critical_moment(E, T, R, gamma=gamma),
                               expect, places=0)

    def test_moment_default_gamma_matches_internal(self):
        got = bending_critical_moment(E, T, R)
        expect = math.pi * K_AXIAL_B * knockdown_bending(R, T) * E * T**2 * R
        self.assertAlmostEqual(got, expect, places=0)

    def test_ovalization_formula_exact(self):
        nu = 0.33
        expect = K_OVAL * E * R * T**2 / math.sqrt(1.0 - nu**2)
        self.assertAlmostEqual(ovalization_collapse_moment(E, T, R, nu=nu),
                               expect, places=1)


class TestPlasticity(unittest.TestCase):
    def test_plasticity_elastic_equals_one(self):
        self.assertAlmostEqual(plasticity_correction(E, E, E), 1.0, places=12)

    def test_plasticity_half_moduli(self):
        # eta = sqrt((E/2)*(E/2))/E = 0.5
        self.assertAlmostEqual(plasticity_correction(E / 2.0, E / 2.0, E),
                               0.5, places=12)

    def test_plasticity_mixed_moduli(self):
        eta = plasticity_correction(60e9, 45e9, 70e9)
        expect = math.sqrt(60e9 * 45e9) / 70e9
        self.assertAlmostEqual(eta, expect, places=12)
        self.assertGreater(eta, 0.0)
        self.assertLess(eta, 1.0)
        # Scaling all moduli together leaves eta unchanged.
        self.assertAlmostEqual(
            eta, plasticity_correction(6e10, 4.5e10, 7e10), places=12
        )


class TestDeterminismAndAssessment(unittest.TestCase):
    def test_determinism_identical_reruns(self):
        a = shell_buckling_assessment(E, T, R, e_sec_pa=60e9, e_tan_pa=45e9)
        b = shell_buckling_assessment(E, T, R, e_sec_pa=60e9, e_tan_pa=45e9)
        self.assertEqual(a, b)

    def test_assessment_keys_exact(self):
        out = shell_buckling_assessment(E, T, R)
        self.assertEqual(
            list(out.keys()),
            ["radius_to_thickness", "curvature_parameter", "gamma_axial",
             "gamma_bending", "sigma_cr_axial_pa", "m_cr_bending_Nm",
             "m_cr_ovalization_Nm", "governing", "eta_plasticity"],
        )

    def test_assessment_eta_default_none(self):
        self.assertIsNone(shell_buckling_assessment(E, T, R)["eta_plasticity"])

    def test_assessment_eta_provided(self):
        out = shell_buckling_assessment(E, T, R, e_sec_pa=60e9, e_tan_pa=45e9)
        self.assertAlmostEqual(
            out["eta_plasticity"],
            math.sqrt(60e9 * 45e9) / 70e9,
            places=12,
        )

    def test_assessment_roundtrip_matches_direct_calls(self):
        out = shell_buckling_assessment(E, T, R)
        self.assertAlmostEqual(out["radius_to_thickness"], R / T, places=9)
        self.assertAlmostEqual(out["curvature_parameter"],
                               curvature_parameter(R, T), places=12)
        self.assertAlmostEqual(out["gamma_axial"], knockdown_axial(R, T),
                               places=12)
        self.assertAlmostEqual(out["gamma_bending"], knockdown_bending(R, T),
                               places=12)
        self.assertAlmostEqual(out["sigma_cr_axial_pa"],
                               axial_critical_stress(E, T, R), places=1)
        self.assertAlmostEqual(out["m_cr_bending_Nm"],
                               bending_critical_moment(E, T, R), places=0)
        self.assertAlmostEqual(out["m_cr_ovalization_Nm"],
                               ovalization_collapse_moment(E, T, R), places=0)



if __name__ == "__main__":
    unittest.main()

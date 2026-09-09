#!/usr/bin/env python3
"""Contract test for continuous-turbulence-gust-loads (structures/loads).

Exercises the SKILL.md workflow steps against
continuous_turbulence_gust_loads_logic.py: step 1 (von_karman_psd,
dryden_psd, spectrum_psd_ordinates, the turbulence PSD ordinates),
step 2 (rigid_aircraft_response_params, gust_response_transfer_squared,
the rigid-aircraft gust-response transfer function), step 3
(rms_response_ratio, response_psd_ordinates, the response PSD and the
rms-response ratio A), step 4 (rms_load_factor_response, the rms load
response), step 5 (design_incremental_load_factor, the design limit
load factor of the continuous-turbulence design criterion), step 6
(gust_alleviation_factor, equivalent_discrete_gust_velocity, the
equivalent discrete-gust velocity hand-off) and step 7
(continuous_turbulence_report, the one-shot report). Offline,
deterministic, stdlib unittest only. No exact-float equality on any
computed sum or product; every numeric assert is tolerant
(assertAlmostEqual with delta, or math.isclose).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import continuous_turbulence_gust_loads_logic as ctg

RHO = 1.225
V = 154.33
WS = 4800.0
S = 120.0
W = WS * S
CBAR = 3.81
A_LIFT = 5.7
L = 762.0
U_SIGMA = 27.432
G = 9.80665

H_INF = 0.11225096093750002
K_RATE = 1.1008058860777343
Y_C = 5.435197856484374
A_VK = 0.06000490538363879
A_D = 0.0527721846394613
N_LIMIT_VK = 2.646054564483979
N_LIMIT_D = 2.4476465690297022
U_DE_VK = 19.063820591364568
U_DE_D = 16.765953612441937
MU_G = 36.79718848898816
K_G = 0.7692087531874008
DC_PHI = 242.5521332720485

VK_OMEGAS = [2.0 * math.pi / lam for lam in (1000.0, 500.0, 200.0, 100.0, 50.0, 25.0)]
VK_PHI = [28.23049507989389, 9.127652940158693, 1.9968651285963208,
          0.6296425301970892, 0.19837774655453844, 0.062489231858575404]
VK_RPSD = [0.15541916622516297, 0.08698574123506526, 0.02392760963617748,
           0.007832728553613196, 0.0024915873597191056, 0.0007867480180908697]


class WorkedExampleTests(unittest.TestCase):
    """Step 1 to step 7 of the SKILL.md workflow at the worked VB-class
    sea-level condition, asserted within 1e-6 relative of the real
    module outputs quoted in the SKILL.md Worked example section."""

    def test_rms_response_ratio_von_karman(self):
        a = ctg.rms_response_ratio("von-karman", RHO, V, W, S, A_LIFT, L, G)
        self.assertAlmostEqual(a, A_VK, delta=1e-6 * A_VK)

    def test_rms_response_ratio_dryden(self):
        a = ctg.rms_response_ratio("dryden", RHO, V, W, S, A_LIFT, L, G)
        self.assertAlmostEqual(a, A_D, delta=1e-6 * A_D)

    def test_rigid_aircraft_response_params(self):
        p = ctg.rigid_aircraft_response_params(RHO, V, W, S, A_LIFT, G)
        self.assertAlmostEqual(p["h_inf"], H_INF, delta=1e-9)
        self.assertAlmostEqual(p["k_rate"], K_RATE, delta=1e-9)
        y_c = p["k_rate"] * L / V
        self.assertAlmostEqual(y_c, Y_C, delta=1e-9)

    def test_design_incremental_load_factor_von_karman(self):
        delta_n = ctg.design_incremental_load_factor(A_VK, U_SIGMA)
        n_limit = 1.0 + delta_n
        self.assertAlmostEqual(n_limit, N_LIMIT_VK, delta=1e-6)

    def test_design_incremental_load_factor_dryden(self):
        delta_n = ctg.design_incremental_load_factor(A_D, U_SIGMA)
        n_limit = 1.0 + delta_n
        self.assertAlmostEqual(n_limit, N_LIMIT_D, delta=1e-6)


class HandoffReportTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the equivalent discrete-gust
    velocity hand-off report, and step 7, the one-shot report."""

    def test_equivalent_discrete_gust_velocity_von_karman(self):
        delta_n = N_LIMIT_VK - 1.0
        u_de = ctg.equivalent_discrete_gust_velocity(
            delta_n, WS, V, A_LIFT, CBAR, RHO, G)
        self.assertAlmostEqual(u_de, U_DE_VK, delta=1e-6 * U_DE_VK)

    def test_equivalent_discrete_gust_velocity_dryden(self):
        delta_n = N_LIMIT_D - 1.0
        u_de = ctg.equivalent_discrete_gust_velocity(
            delta_n, WS, V, A_LIFT, CBAR, RHO, G)
        self.assertAlmostEqual(u_de, U_DE_D, delta=1e-6 * U_DE_D)

    def test_gust_alleviation_factor_and_mass_ratio(self):
        k_g = ctg.gust_alleviation_factor(WS, CBAR, A_LIFT, RHO, G)
        mu_g = 2.0 * WS / (RHO * CBAR * A_LIFT * G)
        self.assertAlmostEqual(k_g, K_G, delta=1e-9)
        self.assertAlmostEqual(mu_g, MU_G, delta=1e-9)

    def test_one_shot_report_key_set(self):
        report = ctg.continuous_turbulence_report(
            "von-karman", RHO, V, W, S, A_LIFT, L, U_SIGMA, CBAR, G)
        expected_keys = {
            "spectrum", "h_inf", "k_rate", "y_c", "a_ratio",
            "response_factor", "rms_delta_n_at_1mps", "delta_n_limit",
            "n_limit", "u_de_eq_mps_eas", "mu_g", "k_g", "mass_kg",
            "turbulence_psd_ordinates", "response_psd_ordinates",
        }
        self.assertEqual(set(report.keys()), expected_keys)
        self.assertAlmostEqual(report["n_limit"], N_LIMIT_VK, delta=1e-6)
        self.assertAlmostEqual(
            report["u_de_eq_mps_eas"], U_DE_VK, delta=1e-6 * U_DE_VK)

    def test_determinism_of_report(self):
        r1 = ctg.continuous_turbulence_report(
            "von-karman", RHO, V, W, S, A_LIFT, L, U_SIGMA, CBAR, G)
        r2 = ctg.continuous_turbulence_report(
            "von-karman", RHO, V, W, S, A_LIFT, L, U_SIGMA, CBAR, G)
        self.assertEqual(r1, r2)


class TurbulencePsdOrdinateTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the von Karman turbulence PSD
    ordinates and the shared DC ordinate of both spectra."""

    def test_von_karman_psd_ordinates(self):
        ordinates = ctg.spectrum_psd_ordinates("von-karman", VK_OMEGAS, 1.0, L)
        for (omega, phi), expected in zip(ordinates, VK_PHI):
            self.assertAlmostEqual(phi, expected, delta=1e-6 * expected)

    def test_dc_ordinate_shared_by_both_spectra(self):
        phi_vk = ctg.von_karman_psd(0.0, 1.0, L)
        phi_d = ctg.dryden_psd(0.0, 1.0, L)
        self.assertAlmostEqual(phi_vk, DC_PHI, delta=1e-9 * DC_PHI)
        self.assertAlmostEqual(phi_d, DC_PHI, delta=1e-9 * DC_PHI)
        self.assertAlmostEqual(phi_vk, phi_d, delta=1e-9 * DC_PHI)


class ResponsePsdOrdinateTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the von Karman response PSD
    ordinates, the integrand of the A-squared integral."""

    def test_von_karman_response_psd_ordinates(self):
        ordinates = ctg.response_psd_ordinates(
            "von-karman", VK_OMEGAS, RHO, V, W, S, A_LIFT, L, G)
        for (omega, r), expected in zip(ordinates, VK_RPSD):
            self.assertAlmostEqual(r, expected, delta=1e-6 * expected)


class ParsevalClosureTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the Parseval closures of the
    normalized von Karman and Dryden spectra, recomputed in-test by
    quadrature and checked against the analytic closed forms."""

    def test_von_karman_closure_ratio(self):
        closure = ctg.VK_A_EXACT / ctg.VK_A
        self.assertAlmostEqual(closure, 0.9999890060233615, delta=1e-6)
        self.assertAlmostEqual(closure, 1.0, delta=1e-3)

    def test_von_karman_closure_numeric_matches_analytic(self):
        numeric = ctg._integrate_y("von-karman", 0.0) / math.pi
        analytic = ctg.VK_A_EXACT / ctg.VK_A
        self.assertAlmostEqual(numeric, analytic, delta=1e-6 * analytic)

    def test_dryden_closure_numeric(self):
        numeric = ctg._integrate_y("dryden", 0.0) / math.pi
        self.assertAlmostEqual(numeric, 1.0, delta=1e-6)


class DrydenClosedFormIdentityTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the Dryden exact closed-form
    identity A_D^2 = h_inf^2 B(y_c), B(c) = (3c + 2)/(2(1+c)^2), and
    its small-c and large-c response-factor limits."""

    def test_dryden_closed_form_matches_quadrature(self):
        p = ctg.rigid_aircraft_response_params(RHO, V, W, S, A_LIFT, G)
        h_inf = p["h_inf"]
        y_c = p["k_rate"] * L / V
        b = (3.0 * y_c + 2.0) / (2.0 * (1.0 + y_c) ** 2)
        a_closed = math.sqrt(h_inf * h_inf * b)
        a_numeric = ctg.rms_response_ratio("dryden", RHO, V, W, S, A_LIFT, L, G)
        self.assertAlmostEqual(a_closed, a_numeric, delta=1e-9 * a_closed)

    def test_response_factor_limits(self):
        b_small = (3.0 * 1e-6 + 2.0) / (2.0 * (1.0 + 1e-6) ** 2)
        b_large = (3.0 * 1e12 + 2.0) / (2.0 * (1.0 + 1e12) ** 2)
        self.assertAlmostEqual(b_small, 1.0, delta=1e-5)
        self.assertLess(abs(b_large), 1e-9)


class OrderingAndBoundsTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: von Karman carries more
    high-frequency energy than Dryden, so A_vK exceeds A_Dryden by the
    real ratio, and both response ratios sit below the frozen-gust
    bound h_inf."""

    def test_von_karman_exceeds_dryden_by_real_ratio(self):
        ratio = A_VK / A_D
        self.assertAlmostEqual(ratio, 1.13705554912292, delta=1e-6)

    def test_both_below_frozen_bound(self):
        self.assertLess(A_VK, H_INF)
        self.assertLess(A_D, H_INF)


class LinearityAndScalingTests(unittest.TestCase):
    """Step 4 and step 5 of the SKILL.md workflow: rms response scales
    linearly with sigma_w, the limit increment scales linearly with
    U_sigma, and the limit increment equals 2.5 times the rms response
    to the 0.4 U_sigma field."""

    def test_rms_load_factor_response_at_unit_sigma(self):
        self.assertAlmostEqual(
            ctg.rms_load_factor_response(1.0, A_VK), A_VK, delta=1e-12)

    def test_limit_increment_doubles_with_intensity(self):
        n_limit_2x = 1.0 + ctg.design_incremental_load_factor(
            A_VK, 2.0 * U_SIGMA)
        expected = 1.0 + 2.0 * (N_LIMIT_VK - 1.0)
        self.assertAlmostEqual(n_limit_2x, 4.292109128967958, delta=1e-9)
        self.assertAlmostEqual(n_limit_2x, expected, delta=1e-9)

    def test_limit_increment_is_2_5x_the_0_4_field_response(self):
        rms_at_field = ctg.rms_load_factor_response(0.4 * U_SIGMA, A_VK)
        delta_n_limit = N_LIMIT_VK - 1.0
        quotient = delta_n_limit / rms_at_field
        self.assertAlmostEqual(quotient, 2.5, delta=1e-9)


class DeterminismAndGridConvergenceTests(unittest.TestCase):
    """Step 3 and step 7 of the SKILL.md workflow: the fixed
    16384-panel Simpson grid with analytic tails changes every
    internal integral by less than 1e-9 relative when the panel count
    doubles, and repeated calls are byte-identical."""

    def test_grid_convergence_von_karman(self):
        i1 = ctg._integrate_y("von-karman", Y_C)
        i2 = ctg._integrate_y("von-karman", Y_C, n=32768)
        self.assertLess(abs(i2 - i1) / i2, 1e-9)

    def test_grid_convergence_dryden(self):
        i1 = ctg._integrate_y("dryden", Y_C)
        i2 = ctg._integrate_y("dryden", Y_C, n=32768)
        self.assertLess(abs(i2 - i1) / i2, 1e-9)

    def test_repeated_psd_calls_identical(self):
        a1 = ctg.von_karman_psd(0.01, 1.0, L)
        a2 = ctg.von_karman_psd(0.01, 1.0, L)
        self.assertEqual(a1, a2)


class ValueErrorTests(unittest.TestCase):
    """ValueError rejection of non-physical inputs, real message
    prefixes as raised by the public functions."""

    def test_negative_l_rejected(self):
        with self.assertRaisesRegex(ValueError, r"L must be a positive number, got -1\.0"):
            ctg.von_karman_psd(0.01, 1.0, -1.0)

    def test_zero_sigma_w_rejected(self):
        with self.assertRaisesRegex(ValueError, r"sigma_w must be a positive number, got 0\.0"):
            ctg.dryden_psd(0.01, 0.0, L)

    def test_negative_omega_rejected(self):
        with self.assertRaisesRegex(ValueError, r"Omega must be a non-negative number, got -0\.1"):
            ctg.von_karman_psd(-0.1, 1.0, L)

    def test_zero_rho_rejected(self):
        with self.assertRaisesRegex(ValueError, r"rho must be a positive number, got 0\.0"):
            ctg.rigid_aircraft_response_params(0.0, V, W, S, A_LIFT)

    def test_negative_weight_rejected(self):
        with self.assertRaisesRegex(ValueError, r"W must be a positive number, got -576000\.0"):
            ctg.rigid_aircraft_response_params(RHO, V, -W, S, A_LIFT)

    def test_boolean_rho_rejected(self):
        with self.assertRaisesRegex(ValueError, r"rho must be a positive number, got True"):
            ctg.gust_response_transfer_squared(0.1, True, V, W, S, A_LIFT)

    def test_unknown_spectrum_rejected(self):
        with self.assertRaisesRegex(
                ValueError,
                r"spectrum must be 'von-karman' or 'dryden', got 'kolmogorov'"):
            ctg.rms_response_ratio("kolmogorov", RHO, V, W, S, A_LIFT, L)

    def test_zero_l_in_ratio_rejected(self):
        with self.assertRaisesRegex(ValueError, r"L must be a positive number, got 0\.0"):
            ctg.rms_response_ratio("dryden", RHO, V, W, S, A_LIFT, 0.0)

    def test_negative_u_sigma_rejected(self):
        with self.assertRaisesRegex(ValueError, r"U_sigma must be a positive number, got -1\.0"):
            ctg.design_incremental_load_factor(A_VK, -1.0)

    def test_negative_a_ratio_rejected(self):
        with self.assertRaisesRegex(ValueError, r"A must be a non-negative number, got -0\.5"):
            ctg.design_incremental_load_factor(-0.5, U_SIGMA)

    def test_negative_sigma_w_rejected(self):
        with self.assertRaisesRegex(ValueError, r"sigma_w must be a positive number, got -1\.0"):
            ctg.rms_load_factor_response(-1.0, A_VK)

    def test_negative_cbar_rejected(self):
        with self.assertRaisesRegex(ValueError, r"cbar must be a positive number, got -3\.81"):
            ctg.gust_alleviation_factor(WS, -3.81, A_LIFT, RHO)

    def test_zero_delta_n_rejected(self):
        with self.assertRaisesRegex(ValueError, r"delta_n must be a positive number, got 0\.0"):
            ctg.equivalent_discrete_gust_velocity(0.0, WS, V, A_LIFT, CBAR, RHO)

    def test_empty_omega_grid_rejected(self):
        with self.assertRaisesRegex(ValueError, r"omega grid must not be empty"):
            ctg.spectrum_psd_ordinates("von-karman", [], 1.0, L)


if __name__ == "__main__":
    unittest.main()

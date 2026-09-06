"""Contract test for the restrained (non-uniform) torsion leaf (structures/fem/restrained-warping).

Exercises the full SKILL.md workflow: the section fix and open-section
Saint-Venant constant J (step 1), the warping section constants Cw and
the sectorial coordinate at the flange tip (step 2), the decay parameter
k of the non-uniform torsion equation (step 3), the built-in cantilever
response under a tip torque with the twist, twist-rate, bimoment and
torque-partition span profiles (step 4), the fork-supported beam response
under a midspan torque with the symmetric span profiles (step 5), the
warping normal stress at the flange tip (step 6) and the restraint twist
ratios against the free Saint-Venant baseline with determinism (step 7).

Worked-example section (SI): I-beam d = 0.3 m, b = 0.15 m, t_f = 0.01 m,
t_w = 0.006 m, aluminium E = 70 GPa, G = 27 GPa, span L = 3 m. Anchor
values quoted below are real prep outputs and agree with this module.
All asserts are order-safe tolerances (no exact float equality on
computed aggregates). Offline, deterministic, under 20 s.
"""

import hashlib
import math
import unittest

from restrained_warping_logic import (
    fixed_end_bimoment,
    fixed_end_response,
    fixed_end_twist,
    fixed_end_twist_rate,
    fork_bimoment,
    fork_response,
    fork_twist,
    i_section_saint_venant_j,
    i_section_sectorial_max,
    i_section_warping_constant,
    torsion_decay_parameter,
    torque_components,
    warping_stress,
)

D, B, TF, TW = 0.3, 0.15, 0.01, 0.006      # anchor I-beam dims (m)
E, G_MOD = 70e9, 27e9                       # aluminium moduli (Pa)
L = 3.0                                     # span (m)
T_CANT = 500.0                              # cantilever tip torque (N m)
T_FORK = 1000.0                             # fork midspan torque (N m)

J_ANCHOR = 1.2016e-07                       # m^4
CW_ANCHOR = 1.18265625e-07                  # m^6
OM_ANCHOR = 0.010875                        # m^2
K_ANCHOR = 0.626013294436                    # 1/m

Z_ROWS = (0.0, 0.75, 1.5, 2.25, 3.0)
THETA_CANT_ROWS = (0.0, 2.208046e-02, 7.591534e-02, 1.476402e-01, 2.274072e-01)
RATE_CANT_ROWS = (0.0, 5.431743e-02, 8.622829e-02, 1.028972e-01, 1.080666e-01)
B_CANT_ROWS = (-7.622182e02, -4.588543e02, -2.585118e02, -1.162102e02, None)
THETA_FORK_ROWS = (0.0, 3.427006e-02, 5.028300e-02, 3.427006e-02, 0.0)
B_FORK_ROWS = (0.0, 2.638170e02, 5.868658e02, 2.638170e02, 0.0)

J = i_section_saint_venant_j(D, B, TF, TW)
CW = i_section_warping_constant(D, B, TF, TW)
OM = i_section_sectorial_max(D, B, TF)
K = torsion_decay_parameter(E, CW, G_MOD, J)
U = K * L
V = K * L / 2.0


def _rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


class TestSectionConstants(unittest.TestCase):
    """Step 1 (section fix and open-section Saint-Venant constant J) and step 2 (warping section constants) of the SKILL.md workflow."""

    def test_j_anchor(self):
        """The open-section Saint-Venant constant of the anchor I-beam (step 1) is 1.2016e-07 m^4."""
        self.assertTrue(math.isclose(J, J_ANCHOR, rel_tol=1e-9))

    def test_j_rectangle_sum_identity(self):
        """J reproduces the per-rectangle open-section sum (1/3)*sum(b_i*t_i**3) over flange, flange, web (step 1)."""
        h_w = D - 2 * TF
        manual = (B * TF ** 3 + B * TF ** 3 + h_w * TW ** 3) / 3.0
        direct = (2 * B * TF ** 3 + h_w * TW ** 3) / 3.0
        self.assertTrue(math.isclose(J, manual, rel_tol=1e-15))
        self.assertTrue(math.isclose(J, direct, rel_tol=1e-15))

    def test_warping_constant_anchor(self):
        """The warping constant Cw = I_y*h**2/4 of the doubly symmetric I-section (step 2) is 1.18265625e-07 m^6."""
        self.assertTrue(math.isclose(CW, CW_ANCHOR, rel_tol=1e-9))

    def test_warping_constant_sectorial_integral_identity(self):
        """Cw equals the direct sectorial integral t_f*h**2*b**3/24 over the flanges to 1e-20 m^6 (step 2, anchor 1.32e-23)."""
        h = D - TF
        integral = TF * h ** 2 * B ** 3 / 24.0
        self.assertLessEqual(abs(CW - integral), 1e-20)

    def test_sectorial_max_and_modulus(self):
        """The sectorial coordinate at the flange tip (step 2) is 0.010875 m^2 and the sectorial modulus Cw/omega is 1.0875e-05 m^4."""
        self.assertTrue(math.isclose(OM, OM_ANCHOR, rel_tol=1e-9))
        self.assertTrue(math.isclose(CW / OM, 1.0875e-05, rel_tol=1e-9))

    def test_decay_parameter_anchor_and_identity(self):
        """Step 3: the decay parameter k = sqrt(G*J/(E*Cw)) of the non-uniform torsion equation is 0.626013294436 1/m."""
        self.assertTrue(math.isclose(K, K_ANCHOR, rel_tol=1e-6))
        self.assertTrue(math.isclose(K ** 2 * E * CW, G_MOD * J, rel_tol=1e-9))


class TestWarpingNormalStress(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the warping normal stress sigma_w = B*omega_tip/Cw at the flange tip."""

    def test_warping_stress_anchor(self):
        """The flange-tip warping normal stress under the cantilever root bimoment is -70089029.2524 Pa (-70.09 MPa, compression at the positive-omega tip)."""
        sigma = warping_stress(-762.21819312020125, OM_ANCHOR, CW_ANCHOR)
        self.assertTrue(math.isclose(sigma, -70089029.2524, rel_tol=1e-6))

    def test_warping_stress_linear_in_bimoment(self):
        """The warping normal stress is linear in the bimoment: doubling B doubles sigma_w."""
        s1 = warping_stress(300.0, OM, CW)
        s2 = warping_stress(600.0, OM, CW)
        self.assertTrue(math.isclose(s2, 2.0 * s1, rel_tol=1e-12))

    def test_warping_stress_value_errors(self):
        """Non-positive sectorial coordinate or warping constant raise ValueError in the stress step."""
        for bad_om, bad_cw in ((0.0, CW), (-1.0, CW), (OM, 0.0), (OM, -1.0)):
            with self.assertRaises(ValueError):
                warping_stress(100.0, bad_om, bad_cw)


class TestFixedEndResponse(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the built-in cantilever solve: restrained tip twist, twist rate, root bimoment and torque split."""

    def test_fixed_response_core_values(self):
        """The built-in root cuts the tip twist to 0.227407224589 rad against the free Saint-Venant baseline 0.462346500962 rad (twist ratio 0.49185453792)."""
        r = fixed_end_response(T_CANT, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["twist_tip"], 0.227407224589, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["twist_rate_tip"], 0.108066620404, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["free_twist"], 0.462346500962, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["twist_ratio"], 0.49185453792, rel_tol=1e-6))

    def test_fixed_response_ratio_closed_form(self):
        """The cantilever restraint twist ratio equals the closed form 1 - tanh(u)/u with u = k*L."""
        r = fixed_end_response(T_CANT, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["twist_ratio"], 1.0 - math.tanh(U) / U, rel_tol=1e-12))

    def test_fixed_bimoment_root_and_free_tip(self):
        """The root bimoment is -T*tanh(u)/k = -762.21819312 N m^2 and the free tip bimoment vanishes to roundoff."""
        r = fixed_end_response(T_CANT, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["bimoment_root"], -762.21819312, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["bimoment_root"], -T_CANT * math.tanh(U) / K, rel_tol=1e-12))
        self.assertLessEqual(abs(r["bimoment_tip"]), 1e-9)

    def test_fixed_tip_torque_split_closed_forms(self):
        """At the free tip the Saint-Venant share is T*(1 - 1/cosh(u)) = 350.602697909 N m and the warping share T/cosh(u) = 149.397302091 N m."""
        r = fixed_end_response(T_CANT, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["saint_venant_torque_tip"], 350.602697909, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["warping_torque_tip"], 149.397302091, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["saint_venant_torque_tip"], T_CANT * (1.0 - 1.0 / math.cosh(U)), rel_tol=1e-12))
        self.assertTrue(math.isclose(r["warping_torque_tip"], T_CANT / math.cosh(U), rel_tol=1e-12))
        self.assertLessEqual(abs(r["saint_venant_torque_tip"] + r["warping_torque_tip"] - T_CANT), 1e-6)

    def test_fixed_root_torque_split(self):
        """At the built-in root the full torque arrives as warping torque: T_sv = 0 and T_w = 500 N m."""
        r = fixed_end_response(T_CANT, L, G_MOD, J, E, CW)
        self.assertEqual(r["saint_venant_torque_root"], 0.0)
        self.assertEqual(r["warping_torque_root"], T_CANT)

    def test_fixed_span_twist_and_rate_rows(self):
        """The cantilever twist and twist-rate profiles reproduce the five worked-example span rows: zero twist rate at the built-in root, peak 0.108066620404 rad/m at the tip (step 4, within 1e-5 relative)."""
        for z, row in zip(Z_ROWS, THETA_CANT_ROWS):
            got = fixed_end_twist(z, T_CANT, L, G_MOD, J, E, CW)
            self.assertLessEqual(abs(got - row), max(1e-9, 1e-5 * abs(row)))
        for z, row in zip(Z_ROWS, RATE_CANT_ROWS):
            got = fixed_end_twist_rate(z, T_CANT, L, G_MOD, J, E, CW)
            self.assertLessEqual(abs(got - row), max(1e-9, 1e-5 * abs(row)))

    def test_fixed_span_bimoment_and_stress_rows(self):
        """The bimoment decays hyperbolically from the root peak -7.622182e+02 N m^2 and sigma_w = B*omega_tip/Cw matches the anchor rows."""
        for z, row in zip(Z_ROWS, B_CANT_ROWS):
            got_b = fixed_end_bimoment(z, T_CANT, L, G_MOD, J, E, CW)
            got_s = warping_stress(got_b, OM, CW)
            if row is None:
                self.assertLessEqual(abs(got_b), 1e-9)
                self.assertLessEqual(abs(got_s), 1e-3)
            else:
                self.assertLessEqual(abs(got_b - row), 1e-5 * abs(row))
                self.assertLessEqual(abs(got_s - row * OM / CW), 1e-5 * abs(row) * OM / CW)

    def test_torque_components_partition_and_rate_identity(self):
        """The torque partition T_sv + T_w equals the carried torque T at every sampled station and each Saint-Venant share equals G*J*theta'(z) (step 4)."""
        worst = 0.0
        for i in range(501):
            z = L * i / 500.0
            tc = torque_components(z, T_CANT, L, G_MOD, J, E, CW)
            worst = max(worst, abs(tc["T_sv"] + tc["T_w"] - T_CANT))
            self.assertTrue(math.isclose(tc["T_sv"], G_MOD * J * fixed_end_twist_rate(z, T_CANT, L, G_MOD, J, E, CW), rel_tol=1e-9))
        self.assertLessEqual(worst, 1e-9)
        root = torque_components(0.0, T_CANT, L, G_MOD, J, E, CW)
        self.assertEqual(root["T_sv"], 0.0)
        self.assertEqual(root["T_w"], T_CANT)

    def test_fixed_boundary_and_ode_residual(self):
        """The built-in root blocks twist and warping, the free tip bimoment vanishes, and the non-uniform torsion ODE residual stays below 1e-9 absolute over 501 stations."""
        self.assertLessEqual(abs(fixed_end_twist(0.0, T_CANT, L, G_MOD, J, E, CW)), 1e-9)
        self.assertLessEqual(abs(fixed_end_twist_rate(0.0, T_CANT, L, G_MOD, J, E, CW)), 1e-9)
        self.assertLessEqual(abs(fixed_end_bimoment(L, T_CANT, L, G_MOD, J, E, CW)), 1e-9)
        worst = 0.0
        for i in range(501):
            z = L * i / 500.0
            th2 = -fixed_end_bimoment(z, T_CANT, L, G_MOD, J, E, CW) / (E * CW)
            worst = max(worst, abs(E * CW * K ** 2 * th2 - G_MOD * J * th2))
        self.assertLessEqual(worst, 1e-9)

    def test_sigma_root_flange_bending_identity(self):
        """The root flange-tip stress equals E*omega_tip*|theta''(0)|, the flange-bending picture of the bimoment (step 6)."""
        root_b = fixed_end_bimoment(0.0, T_CANT, L, G_MOD, J, E, CW)
        sigma = warping_stress(root_b, OM, CW)
        th2_root = -root_b / (E * CW)
        self.assertTrue(math.isclose(abs(sigma), E * OM * abs(th2_root), rel_tol=1e-6))
        self.assertTrue(math.isclose(sigma, -70089029.2524, rel_tol=1e-6))


class TestForkResponse(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, the fork-supported beam solve: restrained midspan twist, midspan bimoment peak and per-half torque components."""

    def test_fork_response_core_values(self):
        """The collar restraint cuts the midspan twist to 0.0502830037738 rad against the free baseline 0.231173250481 rad (twist ratio 0.217512206405)."""
        r = fork_response(T_FORK, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["twist_mid"], 0.0502830037738, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["free_twist"], 0.231173250481, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["twist_ratio"], 0.217512206405, rel_tol=1e-6))

    def test_fork_response_ratio_closed_form(self):
        """The fork restraint twist ratio equals the closed form 1 - tanh(v)/v with v = k*L/2."""
        r = fork_response(T_FORK, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["twist_ratio"], 1.0 - math.tanh(V) / V, rel_tol=1e-12))

    def test_fork_bimoment_mid_and_fork(self):
        """The midspan bimoment peaks at (T/(2*k))*tanh(v) = 586.865845196 N m^2 and vanishes at the forks (warping free)."""
        r = fork_response(T_FORK, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["bimoment_mid"], 586.865845196, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["bimoment_mid"], (T_FORK / (2.0 * K)) * math.tanh(V), rel_tol=1e-12))
        self.assertEqual(r["bimoment_fork"], 0.0)

    def test_fork_torque_split_per_half(self):
        """Each half carries T/2: at the fork face T_sv = 160.842723176 N m and T_w = 339.157276824 N m; at the collar all warping."""
        r = fork_response(T_FORK, L, G_MOD, J, E, CW)
        self.assertTrue(math.isclose(r["saint_venant_torque_fork"], 160.842723176, rel_tol=1e-6))
        self.assertTrue(math.isclose(r["warping_torque_fork"], 339.157276824, rel_tol=1e-6))
        self.assertLessEqual(abs(r["saint_venant_torque_fork"] + r["warping_torque_fork"] - T_FORK / 2.0), 1e-6)
        self.assertEqual(r["saint_venant_torque_mid"], 0.0)
        self.assertEqual(r["warping_torque_mid"], T_FORK / 2.0)

    def test_fork_span_twist_rows(self):
        """The fork twist profile mirrors across midspan and reproduces the five worked-example rows (step 5)."""
        for z, row in zip(Z_ROWS, THETA_FORK_ROWS):
            got = fork_twist(z, T_FORK, L, G_MOD, J, E, CW)
            self.assertLessEqual(abs(got - row), max(1e-9, 1e-5 * abs(row)))

    def test_fork_span_bimoment_rows(self):
        """The fork bimoment is symmetric about midspan with the 5.868658e+02 N m^2 collar peak and zero at both forks."""
        for z, row in zip(Z_ROWS, B_FORK_ROWS):
            got = fork_bimoment(z, T_FORK, L, G_MOD, J, E, CW)
            self.assertLessEqual(abs(got - row), max(1e-9, 1e-5 * abs(row)))
            if z in (0.0, L):
                self.assertEqual(got, 0.0)

    def test_fork_symmetry_and_mirror_remainder(self):
        """fork_twist(z) equals fork_twist(L - z), the midspan twist rate vanishes and the one-step mirror remainder equals theta''(L/2)*dz**2/2."""
        for z in (0.3, 0.75, 1.2):
            self.assertTrue(math.isclose(fork_twist(z, T_FORK, L, G_MOD, J, E, CW), fork_twist(L - z, T_FORK, L, G_MOD, J, E, CW), rel_tol=1e-9))
            self.assertTrue(math.isclose(fork_bimoment(z, T_FORK, L, G_MOD, J, E, CW), fork_bimoment(L - z, T_FORK, L, G_MOD, J, E, CW), rel_tol=1e-9))
        dz = 0.006
        cd_rate = (fork_twist(L / 2.0 + dz, T_FORK, L, G_MOD, J, E, CW) - fork_twist(L / 2.0 - dz, T_FORK, L, G_MOD, J, E, CW)) / (2.0 * dz)
        self.assertLessEqual(abs(cd_rate), 1e-9)
        remainder = abs(fork_twist(L / 2.0, T_FORK, L, G_MOD, J, E, CW) - fork_twist(L / 2.0 + dz, T_FORK, L, G_MOD, J, E, CW))
        expected = (T_FORK * K / (2.0 * G_MOD * J)) * math.tanh(V) * dz ** 2 / 2.0
        self.assertLessEqual(abs(remainder - expected), 1e-8)

    def test_fork_boundary_and_ode_residual(self):
        """Both forks hold the twist at zero and let the section warp (theta = 0 and bimoment = 0 at z = 0 and z = L), and the fork half-beam ODE residual stays below 1e-9 absolute."""
        self.assertLessEqual(abs(fork_twist(0.0, T_FORK, L, G_MOD, J, E, CW)), 1e-9)
        self.assertLessEqual(abs(fork_bimoment(0.0, T_FORK, L, G_MOD, J, E, CW)), 1e-9)
        self.assertLessEqual(abs(fork_twist(L, T_FORK, L, G_MOD, J, E, CW)), 1e-9)
        self.assertLessEqual(abs(fork_bimoment(L, T_FORK, L, G_MOD, J, E, CW)), 1e-9)
        worst = 0.0
        for i in range(501):
            z = L * i / 500.0
            th2 = -fork_bimoment(z, T_FORK, L, G_MOD, J, E, CW) / (E * CW)
            worst = max(worst, abs(E * CW * K ** 2 * th2 - G_MOD * J * th2))
        self.assertLessEqual(worst, 1e-9)

    def test_fork_midspan_sigma_w(self):
        """The flange-tip warping normal stress at the collar peak is 53964675.4204 Pa (53.96 MPa, step 6)."""
        r = fork_response(T_FORK, L, G_MOD, J, E, CW)
        sigma = warping_stress(r["bimoment_mid"], OM, CW)
        self.assertTrue(math.isclose(sigma, 53964675.4204, rel_tol=1e-6))


class TestRejections(unittest.TestCase):
    """ValueError rejection of non-physical inputs across the module functions."""

    def test_valueerror_section_dimensions(self):
        """Non-positive section dimensions and d <= 2*t_f raise ValueError in the section-constant functions (step 1)."""
        with self.assertRaises(ValueError):
            i_section_saint_venant_j(D, 0.0, TF, TW)
        with self.assertRaises(ValueError):
            i_section_saint_venant_j(D, B, 0.0, TW)
        with self.assertRaises(ValueError):
            i_section_saint_venant_j(D, B, TF, -0.001)
        with self.assertRaises(ValueError):
            i_section_warping_constant(0.25, B, 0.13, TW)
        with self.assertRaises(ValueError):
            i_section_warping_constant(D, B, TF, 0.0)
        with self.assertRaises(ValueError):
            i_section_sectorial_max(0.25, B, 0.13)
        with self.assertRaises(ValueError):
            i_section_sectorial_max(D, B, 0.0)

    def test_valueerror_moduli_and_constants(self):
        """Zero or negative E, G, Cw and J raise ValueError in the decay parameter and span solutions (step 3)."""
        with self.assertRaises(ValueError):
            torsion_decay_parameter(0.0, CW, G_MOD, J)
        with self.assertRaises(ValueError):
            torsion_decay_parameter(E, CW, -27e9, J)
        with self.assertRaises(ValueError):
            torsion_decay_parameter(E, 0.0, G_MOD, J)
        with self.assertRaises(ValueError):
            torsion_decay_parameter(E, CW, G_MOD, 0.0)
        with self.assertRaises(ValueError):
            fixed_end_twist(1.0, T_CANT, L, G_MOD, J, 0.0, CW)
        with self.assertRaises(ValueError):
            fork_bimoment(1.0, T_FORK, L, G_MOD, -1.0, E, CW)

    def test_valueerror_length_and_torque(self):
        """Zero span length and zero torque in the response functions raise ValueError (the twist ratio is undefined)."""
        with self.assertRaises(ValueError):
            fixed_end_twist(1.0, T_CANT, 0.0, G_MOD, J, E, CW)
        with self.assertRaises(ValueError):
            fork_twist(1.0, T_FORK, -3.0, G_MOD, J, E, CW)
        with self.assertRaises(ValueError):
            fixed_end_response(0.0, L, G_MOD, J, E, CW)
        with self.assertRaises(ValueError):
            fork_response(0.0, L, G_MOD, J, E, CW)

    def test_zero_torque_twist_profile_allowed(self):
        """The span twist functions stay defined at zero torque (zero twist), only the response ratios reject it."""
        self.assertEqual(fixed_end_twist(1.5, 0.0, L, G_MOD, J, E, CW), 0.0)
        self.assertEqual(fork_twist(1.5, 0.0, L, G_MOD, J, E, CW), 0.0)

    def test_arity_signature_enforcement(self):
        """Wrong function arity raises TypeError: the warping constant needs the four dims (d, b, t_f, t_w) and the sectorial maximum three."""
        with self.assertRaises(TypeError):
            i_section_warping_constant(D, B)
        with self.assertRaises(TypeError):
            i_section_sectorial_max(D, B)


class TestDeterminism(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the restraint twist ratios and the deterministic contract test run."""

    def test_twist_ratio_quantifies_stiffening(self):
        """The cantilever restraint cuts the twist to 49.2% and the fork collar restraint to 21.8% of the free Saint-Venant twist."""
        rc = fixed_end_response(T_CANT, L, G_MOD, J, E, CW)
        rf = fork_response(T_FORK, L, G_MOD, J, E, CW)
        self.assertLess(rc["twist_tip"], rc["free_twist"])
        self.assertLess(rf["twist_mid"], rf["free_twist"])
        self.assertLess(rf["twist_ratio"], rc["twist_ratio"])

    def test_deterministic_two_runs(self):
        """Two identical runs produce identical bits: the canonical dump sha256 is stable, no RNG involved."""
        def canonical():
            parts = []
            for key in sorted(fixed_end_response(T_CANT, L, G_MOD, J, E, CW)):
                parts.append("%s=%.17g" % (key, fixed_end_response(T_CANT, L, G_MOD, J, E, CW)[key]))
            for key in sorted(fork_response(T_FORK, L, G_MOD, J, E, CW)):
                parts.append("%s=%.17g" % (key, fork_response(T_FORK, L, G_MOD, J, E, CW)[key]))
            for z in (0.0, 0.75, 1.5, 2.25, 3.0):
                parts.append("%.17g" % fixed_end_twist(z, T_CANT, L, G_MOD, J, E, CW))
            return hashlib.sha256("|".join(parts).encode("ascii")).hexdigest()

        first = canonical()
        second = canonical()
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

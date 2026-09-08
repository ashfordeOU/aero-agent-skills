"""Offline contract test for rotorcraft-cyclic-pitch-trim.

Deterministic stdlib unittest, no network, no RNG. Exercises step 1 of the
SKILL.md workflow (fix the advance ratio, inflow ratio, collective, Lock
number and cyclic pitch command operating point), step 2 (coning_angle and
the zero-cyclic and hover cross-leaf coning identities), step 3
(longitudinal_flapping_angle and the tip-path-plane response to the
longitudinal cyclic pitch), step 4 (lateral_flapping_angle and the
coning-coupling identity), step 5 (flap_response_summary one-call
cyclic-forced equilibrium dict), step 6 (cyclic_response_gains, the affine
control-to-flap gains), step 7 (trim_cyclic, the closed-form trim inversion
for a level-disk or prescribed tip-path-plane attitude, and its round trip
through flap_response_summary), step 8 (trim_swashplate_tilt, the ideal
zero-phase swashplate tilt report) and step 9 (the deterministic checks of
this contract test), plus ValueError rejection of every non-physical input
and run-to-run determinism. No exact-float equality asserts on computed
sums; uses assertAlmostEqual and math.isclose throughout.
"""

import math
import unittest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rotorcraft_cyclic_pitch_trim_logic import (  # noqa: E402
    DEG,
    MU_MAX,
    coning_angle,
    longitudinal_flapping_angle,
    lateral_flapping_angle,
    flap_response_summary,
    cyclic_response_gains,
    trim_cyclic,
    trim_swashplate_tilt,
)

MU, LAM, THETA0, GAMMA = 0.3, 0.06, 0.14, 6.0


class TestZeroCyclicCrossLeafIdentity(unittest.TestCase):
    """Step 2, 3 and 4 of the SKILL.md workflow: coning_angle,
    longitudinal_flapping_angle and lateral_flapping_angle at zero cyclic
    reproduce the wave-46 collective-only closed forms exactly."""

    def test_zero_cyclic_summary_matches_wave46_sibling(self):
        s = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertAlmostEqual(s["coning_angle_rad"], 0.054450000000000012, delta=1e-9)
        self.assertAlmostEqual(s["longitudinal_flapping_rad"], -0.079581151832460728, delta=1e-9)
        self.assertAlmostEqual(s["lateral_flapping_rad"], -0.020842105263157901, delta=1e-9)

    def test_zero_cyclic_matches_hand_closed_forms(self):
        # The wave-46 sibling's own printed closed forms, computed here
        # directly (no import of the sibling module) within 1e-12.
        a0_hand = (GAMMA / 2.0) * (THETA0 * (1.0 + MU ** 2) / 4.0 - LAM / 3.0)
        a1s_hand = -4.0 * MU * (2.0 * THETA0 / 3.0 - LAM / 2.0) / (1.0 - MU ** 2 / 2.0)
        b1s_hand = -(4.0 * MU / 3.0) * a0_hand / (1.0 + MU ** 2 / 2.0)
        a0 = coning_angle(MU, LAM, THETA0, GAMMA, 0.0)
        a1s = longitudinal_flapping_angle(MU, LAM, THETA0, 0.0)
        b1s = lateral_flapping_angle(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertAlmostEqual(a0, a0_hand, delta=1e-12)
        self.assertAlmostEqual(a1s, a1s_hand, delta=1e-12)
        self.assertAlmostEqual(b1s, b1s_hand, delta=1e-12)


class TestForwardMapUnderCyclic(unittest.TestCase):
    """Step 2, 3, 4 and 5 of the SKILL.md workflow: the forward map under a
    nonzero cyclic command theta1c = 0.02, theta1s = -0.04."""

    def test_forward_map_worked_values(self):
        s = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.02, -0.04)
        self.assertAlmostEqual(s["coning_angle_rad"], 0.042450000000000009, delta=1e-9)
        self.assertAlmostEqual(s["longitudinal_flapping_rad"], -0.032041884816753921, delta=1e-9)
        self.assertAlmostEqual(s["lateral_flapping_rad"], 0.0037511961722488003, delta=1e-9)


class TestHoverCyclicResponse(unittest.TestCase):
    """Step 1, 2, 3 and 4 of the SKILL.md workflow: the mu = 0.0 hover
    limit of the operating point gives the direct 90-degree cyclic lag."""

    def test_hover_longitudinal_equals_negative_theta1s(self):
        a1s = longitudinal_flapping_angle(0.0, LAM, THETA0, -0.04)
        self.assertAlmostEqual(a1s, 0.040000000000000001, delta=1e-12)

    def test_hover_lateral_equals_theta1c(self):
        b1s = lateral_flapping_angle(0.0, LAM, THETA0, GAMMA, 0.02, -0.04)
        self.assertAlmostEqual(b1s, 0.02, delta=1e-12)

    def test_hover_coning_is_cyclic_free_closed_form(self):
        a0 = coning_angle(0.0, LAM, THETA0, GAMMA, -0.04)
        hand = 0.5 * GAMMA * (THETA0 / 4.0 - LAM / 3.0)
        self.assertAlmostEqual(a0, hand, delta=1e-12)
        self.assertAlmostEqual(a0, 0.045000000000000012, delta=1e-12)

    def test_hover_no_cyclic_trim_probe(self):
        t = trim_cyclic(0.0, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertEqual(t["longitudinal_cyclic_pitch_rad"], 0.0)
        self.assertEqual(t["lateral_cyclic_pitch_rad"], 0.0)


class TestLevelDiskTrim(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: trim_cyclic inverts the equilibrium
    map for the level-disk attitude at cruise, with a round trip through
    flap_response_summary."""

    def test_level_disk_trim_worked_values(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertAlmostEqual(t["longitudinal_cyclic_pitch_rad"], -0.066960352422907488, delta=1e-9)
        self.assertAlmostEqual(t["lateral_cyclic_pitch_rad"], 0.013152878190670913, delta=1e-9)

    def test_level_disk_round_trip(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        s = flap_response_summary(
            MU, LAM, THETA0, GAMMA,
            t["lateral_cyclic_pitch_rad"], t["longitudinal_cyclic_pitch_rad"],
        )
        self.assertAlmostEqual(s["longitudinal_flapping_rad"], 0.0, delta=1e-9)
        self.assertAlmostEqual(s["lateral_flapping_rad"], 0.0, delta=1e-9)


class TestPrescribedAttitudeTrim(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: trim_cyclic at a prescribed relaxed
    aft-tilt attitude, with a round trip."""

    def test_prescribed_trim_worked_values(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, -0.02, 0.0)
        self.assertAlmostEqual(t["longitudinal_cyclic_pitch_rad"], -0.050132158590308368, delta=1e-9)
        self.assertAlmostEqual(t["lateral_cyclic_pitch_rad"], 0.015085302362835404, delta=1e-9)

    def test_prescribed_trim_round_trip(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, -0.02, 0.0)
        s = flap_response_summary(
            MU, LAM, THETA0, GAMMA,
            t["lateral_cyclic_pitch_rad"], t["longitudinal_cyclic_pitch_rad"],
        )
        self.assertAlmostEqual(s["longitudinal_flapping_rad"], -0.02, delta=1e-9)
        self.assertAlmostEqual(s["lateral_flapping_rad"], 0.0, delta=1e-9)


class TestFreeEquilibriumIdentity(unittest.TestCase):
    """Step 6 and 7 of the SKILL.md workflow: trimming to the free-flap
    attitude from cyclic_response_gains needs zero cyclic."""

    def test_free_equilibrium_needs_zero_cyclic(self):
        g = cyclic_response_gains(MU, LAM, THETA0, GAMMA)
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, g["a1s_free"], g["b1s_free"])
        self.assertTrue(math.isclose(t["longitudinal_cyclic_pitch_rad"], 0.0, abs_tol=1e-9))
        self.assertTrue(math.isclose(t["lateral_cyclic_pitch_rad"], 0.0, abs_tol=1e-9))


class TestGainStructure(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: cyclic_response_gains, the affine
    control-to-flap gains of the equilibrium map."""

    def test_gains_worked_values(self):
        g = cyclic_response_gains(MU, LAM, THETA0, GAMMA)
        self.assertAlmostEqual(g["a1s_free"], -0.079581151832460728, delta=1e-9)
        self.assertAlmostEqual(g["b1s_free"], -0.020842105263157901, delta=1e-9)
        self.assertAlmostEqual(g["d_a1s_d_theta1s"], -1.1884816753926701, delta=1e-9)
        self.assertEqual(g["d_a1s_d_theta1c"], 0.0)
        self.assertEqual(g["d_b1s_d_theta1c"], 1.0)
        self.assertAlmostEqual(g["d_b1s_d_theta1s"], -0.11483253588516748, delta=1e-9)

    def test_gains_match_closed_forms(self):
        g = cyclic_response_gains(MU, LAM, THETA0, GAMMA)
        hand_a1s_theta1s = -(1.0 + 3.0 * MU ** 2 / 2.0) / (1.0 - MU ** 2 / 2.0)
        hand_b1s_theta1s = -(2.0 * GAMMA * MU ** 2 / 9.0) / (1.0 + MU ** 2 / 2.0)
        self.assertAlmostEqual(g["d_a1s_d_theta1s"], hand_a1s_theta1s, delta=1e-12)
        self.assertAlmostEqual(g["d_b1s_d_theta1s"], hand_b1s_theta1s, delta=1e-12)
        self.assertAlmostEqual(hand_a1s_theta1s, -1.135 / 0.955, delta=1e-15)
        self.assertAlmostEqual(hand_b1s_theta1s, -0.12 / 1.045, delta=1e-15)

    def test_d_b1s_d_theta1s_zero_at_hover(self):
        g = cyclic_response_gains(0.0, LAM, THETA0, GAMMA)
        self.assertAlmostEqual(g["d_b1s_d_theta1s"], 0.0, delta=1e-15)


class TestOrderingIdentity(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the level-disk longitudinal cyclic
    magnitude sits below the free aft-tilt magnitude at the worked point."""

    def test_level_cyclic_below_free_aft_tilt(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        g = cyclic_response_gains(MU, LAM, THETA0, GAMMA)
        level_mag = abs(t["longitudinal_cyclic_pitch_rad"])
        free_mag = abs(g["a1s_free"])
        self.assertAlmostEqual(level_mag, 0.0669603524, delta=1e-9)
        self.assertAlmostEqual(free_mag, 0.0795811518, delta=1e-9)
        self.assertLess(level_mag, free_mag)


class TestInflowLinearity(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the level-disk trim cyclic pitches
    move linearly with the inflow ratio, matching the closed-form slopes."""

    def test_inflow_two_point_slopes(self):
        t_hi = trim_cyclic(MU, 0.06, THETA0, GAMMA, 0.0, 0.0)
        t_lo = trim_cyclic(MU, 0.05, THETA0, GAMMA, 0.0, 0.0)
        d_theta1s = t_hi["longitudinal_cyclic_pitch_rad"] - t_lo["longitudinal_cyclic_pitch_rad"]
        d_theta1c = t_hi["lateral_cyclic_pitch_rad"] - t_lo["lateral_cyclic_pitch_rad"]
        hand_d_theta1s = 2.0 * MU * 0.01 / (1.0 + 3.0 * MU ** 2 / 2.0)
        hand_d_theta1c = -(2.0 * GAMMA * MU / 9.0) * (1.0 - MU ** 2 / 2.0) * 0.01 \
            / ((1.0 + 3.0 * MU ** 2 / 2.0) * (1.0 + MU ** 2 / 2.0))
        self.assertAlmostEqual(d_theta1s, hand_d_theta1s, delta=1e-12)
        self.assertAlmostEqual(d_theta1c, hand_d_theta1c, delta=1e-12)
        self.assertAlmostEqual(d_theta1s, 0.0052863436123347929, delta=1e-12)
        self.assertAlmostEqual(d_theta1c, -0.0032207069536074918, delta=1e-12)


class TestDegreeOutputs(unittest.TestCase):
    """Step 5 and step 8 of the SKILL.md workflow: the _deg outputs of
    flap_response_summary, trim_cyclic and trim_swashplate_tilt."""

    def test_summary_degree_values(self):
        s = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertAlmostEqual(s["coning_angle_deg"], 3.1197551944873334, delta=1e-9)
        self.assertAlmostEqual(s["longitudinal_flapping_deg"], -4.5596641287897972, delta=1e-9)
        self.assertAlmostEqual(s["lateral_flapping_deg"], -1.1941646677463478, delta=1e-9)
        for rad_key, deg_key in (
            ("coning_angle_rad", "coning_angle_deg"),
            ("longitudinal_flapping_rad", "longitudinal_flapping_deg"),
            ("lateral_flapping_rad", "lateral_flapping_deg"),
        ):
            self.assertAlmostEqual(s[deg_key], s[rad_key] * DEG, delta=1e-12)

    def test_summary_returns_exactly_six_keys(self):
        s = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.02, -0.04)
        self.assertEqual(
            set(s.keys()),
            {
                "coning_angle_rad", "coning_angle_deg",
                "longitudinal_flapping_rad", "longitudinal_flapping_deg",
                "lateral_flapping_rad", "lateral_flapping_deg",
            },
        )
        self.assertAlmostEqual(s["coning_angle_rad"], coning_angle(MU, LAM, THETA0, GAMMA, -0.04), delta=1e-12)
        self.assertAlmostEqual(
            s["longitudinal_flapping_rad"], longitudinal_flapping_angle(MU, LAM, THETA0, -0.04), delta=1e-12
        )
        self.assertAlmostEqual(
            s["lateral_flapping_rad"], lateral_flapping_angle(MU, LAM, THETA0, GAMMA, 0.02, -0.04), delta=1e-12
        )

    def test_trim_degree_values_and_key_discipline(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertAlmostEqual(t["longitudinal_cyclic_pitch_deg"], -3.836545588541195, delta=1e-9)
        self.assertAlmostEqual(t["lateral_cyclic_pitch_deg"], 0.75360440877510981, delta=1e-9)
        self.assertEqual(
            set(t.keys()),
            {
                "longitudinal_cyclic_pitch_rad", "longitudinal_cyclic_pitch_deg",
                "lateral_cyclic_pitch_rad", "lateral_cyclic_pitch_deg",
            },
        )
        self.assertAlmostEqual(t["longitudinal_cyclic_pitch_deg"], t["longitudinal_cyclic_pitch_rad"] * DEG, delta=1e-12)
        self.assertAlmostEqual(t["lateral_cyclic_pitch_deg"], t["lateral_cyclic_pitch_rad"] * DEG, delta=1e-12)

    def test_swashplate_tilt_key_discipline(self):
        sw = trim_swashplate_tilt(MU, LAM, THETA0, GAMMA, 0.0, 0.0)
        self.assertEqual(
            set(sw.keys()),
            {
                "swashplate_longitudinal_tilt_rad", "swashplate_longitudinal_tilt_deg",
                "swashplate_lateral_tilt_rad", "swashplate_lateral_tilt_deg",
                "swashplate_tilt_magnitude_rad", "swashplate_tilt_magnitude_deg",
            },
        )
        self.assertAlmostEqual(sw["swashplate_longitudinal_tilt_rad"], 0.013152878190670913, delta=1e-9)
        self.assertAlmostEqual(sw["swashplate_lateral_tilt_rad"], -0.066960352422907488, delta=1e-9)
        self.assertAlmostEqual(sw["swashplate_tilt_magnitude_rad"], 0.068239922342413314, delta=1e-9)
        self.assertAlmostEqual(
            sw["swashplate_tilt_magnitude_rad"],
            math.hypot(sw["swashplate_longitudinal_tilt_rad"], sw["swashplate_lateral_tilt_rad"]),
            delta=1e-12,
        )
        self.assertAlmostEqual(sw["swashplate_tilt_magnitude_deg"], sw["swashplate_tilt_magnitude_rad"] * DEG, delta=1e-12)


class TestConingDecoupling(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: coning_angle is independent of
    theta1c and depends on theta1s only through the mean-lift term."""

    def test_coning_matches_closed_form_two_theta1s(self):
        a0_neg = coning_angle(MU, LAM, THETA0, GAMMA, -0.04)
        a0_zero = coning_angle(MU, LAM, THETA0, GAMMA, 0.0)
        hand_neg = (GAMMA / 2.0) * (THETA0 * (1.0 + MU ** 2) / 4.0 - LAM / 3.0 + MU * (-0.04) / 3.0)
        hand_zero = (GAMMA / 2.0) * (THETA0 * (1.0 + MU ** 2) / 4.0 - LAM / 3.0)
        self.assertAlmostEqual(a0_neg, hand_neg, delta=1e-12)
        self.assertAlmostEqual(a0_zero, hand_zero, delta=1e-12)
        self.assertAlmostEqual(a0_neg, 0.042450000000000009, delta=1e-9)
        self.assertAlmostEqual(a0_zero, 0.054450000000000012, delta=1e-9)

    def test_coning_takes_no_theta1c_argument(self):
        # coning_angle's signature has no theta1c parameter; calling it
        # with a mismatched arity raises TypeError, confirming the model's
        # theta1c-independence is structural, not incidental.
        with self.assertRaises(TypeError):
            coning_angle(MU, LAM, THETA0, GAMMA, 0.02, -0.04)


class TestFourierSelfConsistency(unittest.TestCase):
    """Step 5 and step 9 of the SKILL.md workflow: an independent
    quadrature of the full moment integrand confirms the closed-form
    equilibrium nulls the steady, cos and sin projections of
    (gamma/2)*M - (beta'' + beta) at the worked point under cyclic."""

    def test_fourier_projections_are_near_zero(self):
        theta1c, theta1s = 0.02, -0.04
        a0 = coning_angle(MU, LAM, THETA0, GAMMA, theta1s)
        a1s = longitudinal_flapping_angle(MU, LAM, THETA0, theta1s)
        b1s = lateral_flapping_angle(MU, LAM, THETA0, GAMMA, theta1c, theta1s)

        n_x, n_psi = 1024, 128
        dx = 1.0 / n_x
        dpsi = 2.0 * math.pi / n_psi

        def moment(psi, beta, beta_p):
            theta = THETA0 + theta1c * math.cos(psi) + theta1s * math.sin(psi)
            total = 0.0
            for i in range(n_x):
                x = (i + 0.5) * dx
                u_t = x + MU * math.sin(psi)
                u_p = LAM + x * beta_p + MU * beta * math.cos(psi)
                total += x * (u_t ** 2 * theta - u_t * u_p) * dx
            return total

        steady = cos_proj = sin_proj = 0.0
        for j in range(n_psi):
            psi = (j + 0.5) * dpsi
            beta = a0 + a1s * math.cos(psi) + b1s * math.sin(psi)
            beta_p = -a1s * math.sin(psi) + b1s * math.cos(psi)
            beta_pp = -(a1s * math.cos(psi) + b1s * math.sin(psi))
            residual = (GAMMA / 2.0) * moment(psi, beta, beta_p) - (beta_pp + beta)
            steady += residual * dpsi
            cos_proj += residual * math.cos(psi) * dpsi
            sin_proj += residual * math.sin(psi) * dpsi

        steady /= (2.0 * math.pi)
        cos_proj /= math.pi
        sin_proj /= math.pi
        self.assertLess(abs(steady), 1e-5)
        self.assertLess(abs(cos_proj), 1e-5)
        self.assertLess(abs(sin_proj), 1e-5)


class TestValueErrors(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fixing the operating point rejects
    every non-physical or non-finite argument with ValueError."""

    def test_mu_negative_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(-0.1, LAM, THETA0, GAMMA, 0.0)

    def test_mu_at_boundary_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU_MAX, LAM, THETA0, GAMMA, 0.0)

    def test_mu_above_boundary_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(1.5, LAM, THETA0, GAMMA, 0.0)

    def test_lam_zero_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, 0.0, THETA0, GAMMA, 0.0)

    def test_lam_negative_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, -0.02, THETA0, GAMMA, 0.0)

    def test_theta0_zero_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, LAM, 0.0, GAMMA, 0.0)

    def test_theta0_negative_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, LAM, -0.1, GAMMA, 0.0)

    def test_gamma_zero_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, LAM, THETA0, 0.0, 0.0)

    def test_gamma_negative_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, LAM, THETA0, -3.0, 0.0)

    def test_theta1s_nan_rejected(self):
        with self.assertRaises(ValueError):
            coning_angle(MU, LAM, THETA0, GAMMA, float("nan"))

    def test_theta1c_inf_rejected(self):
        with self.assertRaises(ValueError):
            lateral_flapping_angle(MU, LAM, THETA0, GAMMA, float("inf"), 0.0)

    def test_a1s_target_nan_rejected(self):
        with self.assertRaises(ValueError):
            trim_cyclic(MU, LAM, THETA0, GAMMA, float("nan"), 0.0)

    def test_mu_zero_is_valid(self):
        # mu = 0.0 is a valid hover-limit input, not rejected.
        a0 = coning_angle(0.0, LAM, THETA0, GAMMA, 0.0)
        self.assertTrue(math.isfinite(a0))

    def test_negative_cyclic_and_target_values_are_valid(self):
        t = trim_cyclic(MU, LAM, THETA0, GAMMA, -0.02, 0.0)
        self.assertTrue(math.isfinite(t["longitudinal_cyclic_pitch_rad"]))
        s = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.02, -0.04)
        self.assertTrue(math.isfinite(s["coning_angle_rad"]))


class TestDeterminism(unittest.TestCase):
    """Step 9 of the SKILL.md workflow: repeated calls with identical
    arguments return bit-identical dicts; no RNG anywhere in the module."""

    def test_summary_is_deterministic(self):
        s1 = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.02, -0.04)
        s2 = flap_response_summary(MU, LAM, THETA0, GAMMA, 0.02, -0.04)
        self.assertEqual(s1, s2)

    def test_trim_is_deterministic(self):
        t1 = trim_cyclic(MU, LAM, THETA0, GAMMA, -0.02, 0.0)
        t2 = trim_cyclic(MU, LAM, THETA0, GAMMA, -0.02, 0.0)
        self.assertEqual(t1, t2)

    def test_module_constants_fixed(self):
        self.assertAlmostEqual(DEG, 180.0 / math.pi, delta=1e-15)
        self.assertEqual(MU_MAX, 1.0)


if __name__ == "__main__":
    unittest.main()

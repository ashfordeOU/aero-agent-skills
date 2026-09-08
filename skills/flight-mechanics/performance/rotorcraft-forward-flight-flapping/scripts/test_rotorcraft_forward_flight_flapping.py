"""Offline contract test for rotorcraft-forward-flight-flapping.

Deterministic stdlib unittest, no network, no RNG. Exercises step 1 of the
SKILL.md workflow (fix the advance ratio, inflow ratio, collective and Lock
number operating point), step 2 (forward_coning_angle and the hover
cross-leaf coning identity), step 3 (longitudinal_flapping_angle and the
tip-path-plane aft tilt at cruise), step 4 (lateral_flapping_angle and the
coning-coupling identity), step 5 (forward_flap_summary one-call
assessment), step 6 (inflow sensitivity of the tip-path-plane tilt) and
step 7 (monotone growth of the flapping angles with advance ratio), plus
ValueError rejection of every non-physical input and run to run
determinism. No exact-float equality asserts on computed sums; uses
assertAlmostEqual and math.isclose throughout.
"""

import math
import unittest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rotorcraft_forward_flight_flapping_logic import (  # noqa: E402
    DEG,
    forward_coning_angle,
    forward_flap_summary,
    lateral_flapping_angle,
    longitudinal_flapping_angle,
)


class TestWorkedExampleConing(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: forward_coning_angle at the cruise
    operating point mu = 0.3, lam = 0.06, theta0 = 0.14, gamma = 6.0."""

    def test_forward_coning_worked_value(self):
        a0 = forward_coning_angle(0.3, 0.06, 0.14, 6.0)
        self.assertAlmostEqual(a0, 0.054450000000000012, delta=1e-9 * abs(a0))

    def test_forward_coning_hover_cross_leaf_identity(self):
        # Hover cross-leaf identity: mu = 0 reduces to the sibling hover
        # coning closed form 0.5 * gamma * (theta0 / 4 - lam / 3), and the
        # forward-flight value at mu = 0.3 exceeds the hover value (the
        # theta0 * mu**2 / 4 dynamic-pressure gain).
        a0_hover = forward_coning_angle(0.0, 0.06, 0.14, 6.0)
        hand = 0.5 * 6.0 * (0.14 / 4.0 - 0.06 / 3.0)
        self.assertAlmostEqual(a0_hover, hand, delta=1e-12)
        self.assertAlmostEqual(a0_hover, 0.045000000000000012, delta=1e-12)
        a0_forward = forward_coning_angle(0.3, 0.06, 0.14, 6.0)
        self.assertGreater(a0_forward, a0_hover)


class TestLongitudinalFlapping(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: longitudinal_flapping_angle, the
    tip-path-plane aft tilt, at cruise."""

    def test_longitudinal_worked_value_and_sign(self):
        a1s = longitudinal_flapping_angle(0.3, 0.06, 0.14)
        self.assertAlmostEqual(a1s, -0.079581151832460728, delta=1e-9 * abs(a1s))
        self.assertLess(a1s, 0.0)

    def test_longitudinal_matches_closed_form(self):
        a1s = longitudinal_flapping_angle(0.3, 0.06, 0.14)
        hand = -4.0 * 0.3 * (2.0 * 0.14 / 3.0 - 0.06 / 2.0) / (1.0 - 0.09 / 2.0)
        self.assertAlmostEqual(a1s, hand, delta=1e-12)

    def test_longitudinal_zero_at_hover(self):
        self.assertEqual(longitudinal_flapping_angle(0.0, 0.06, 0.14), 0.0)

    def test_longitudinal_zero_at_collective_inflow_balance(self):
        # theta0 = 3 * lam / 4 nulls the cos(psi) 1/rev moment exactly.
        a1s = longitudinal_flapping_angle(0.3, 0.06, 0.045)
        self.assertEqual(a1s, 0.0)


class TestLateralFlapping(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: lateral_flapping_angle and the
    coning-coupling identity with forward_coning_angle."""

    def test_lateral_worked_value(self):
        b1s = lateral_flapping_angle(0.3, 0.06, 0.14, 6.0)
        self.assertAlmostEqual(b1s, -0.020842105263157901, delta=1e-9 * abs(b1s))

    def test_lateral_zero_at_hover(self):
        self.assertEqual(lateral_flapping_angle(0.0, 0.06, 0.14, 6.0), 0.0)

    def test_coning_coupling_identity_worked_point(self):
        mu, lam, theta0, gamma = 0.3, 0.06, 0.14, 6.0
        b1s = lateral_flapping_angle(mu, lam, theta0, gamma)
        a0 = forward_coning_angle(mu, lam, theta0, gamma)
        expected = -(4.0 * mu / 3.0) * a0 / (1.0 + mu ** 2 / 2.0)
        self.assertAlmostEqual(b1s, expected, delta=1e-12)

    def test_coning_coupling_identity_other_point(self):
        mu, lam, theta0, gamma = 0.2, 0.07, 0.12, 7.0
        b1s = lateral_flapping_angle(mu, lam, theta0, gamma)
        a0 = forward_coning_angle(mu, lam, theta0, gamma)
        expected = -(4.0 * mu / 3.0) * a0 / (1.0 + mu ** 2 / 2.0)
        self.assertAlmostEqual(b1s, expected, delta=1e-12)


class TestDegreeOutputs(unittest.TestCase):
    """Degree outputs of the summary and their radian-to-degree factor."""

    def test_coning_degrees_worked_value(self):
        a0_deg = forward_coning_angle(0.3, 0.06, 0.14, 6.0) * DEG
        self.assertAlmostEqual(a0_deg, 3.1197551944873334, delta=1e-9 * abs(a0_deg))

    def test_longitudinal_degrees_worked_value(self):
        a1s_deg = longitudinal_flapping_angle(0.3, 0.06, 0.14) * DEG
        self.assertAlmostEqual(a1s_deg, -4.559664128789797, delta=1e-9 * abs(a1s_deg))

    def test_lateral_degrees_worked_value(self):
        b1s_deg = lateral_flapping_angle(0.3, 0.06, 0.14, 6.0) * DEG
        self.assertAlmostEqual(b1s_deg, -1.1941646677463478, delta=1e-9 * abs(b1s_deg))

    def test_degree_conversion_factor_exact(self):
        self.assertAlmostEqual(DEG, 180.0 / math.pi, delta=1e-15)


class TestSummaryOneCall(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: forward_flap_summary, the one-call
    first-harmonic flap equilibrium assessment dict."""

    def test_summary_has_exact_keys(self):
        summary = forward_flap_summary(0.3, 0.06, 0.14, 6.0)
        self.assertEqual(
            set(summary.keys()),
            {
                "coning_angle_rad",
                "coning_angle_deg",
                "longitudinal_flapping_rad",
                "longitudinal_flapping_deg",
                "lateral_flapping_rad",
                "lateral_flapping_deg",
            },
        )

    def test_summary_matches_component_functions(self):
        mu, lam, theta0, gamma = 0.3, 0.06, 0.14, 6.0
        summary = forward_flap_summary(mu, lam, theta0, gamma)
        a0 = forward_coning_angle(mu, lam, theta0, gamma)
        a1s = longitudinal_flapping_angle(mu, lam, theta0)
        b1s = lateral_flapping_angle(mu, lam, theta0, gamma)
        self.assertAlmostEqual(summary["coning_angle_rad"], a0, delta=1e-12)
        self.assertAlmostEqual(summary["longitudinal_flapping_rad"], a1s, delta=1e-12)
        self.assertAlmostEqual(summary["lateral_flapping_rad"], b1s, delta=1e-12)

    def test_summary_deg_matches_rad_times_factor_and_finite(self):
        summary = forward_flap_summary(0.3, 0.06, 0.14, 6.0)
        for rad_key, deg_key in (
            ("coning_angle_rad", "coning_angle_deg"),
            ("longitudinal_flapping_rad", "longitudinal_flapping_deg"),
            ("lateral_flapping_rad", "lateral_flapping_deg"),
        ):
            self.assertAlmostEqual(
                summary[deg_key], summary[rad_key] * DEG, delta=1e-12)
        for value in summary.values():
            self.assertTrue(math.isfinite(value))


class TestInflowSensitivity(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: inflow sensitivity of the
    tip-path-plane tilt, and the exact linearity (odd symmetry) of the
    inflow-induced tilt parts in the inflow ratio lambda."""

    def test_higher_inflow_relaxes_aft_tilt(self):
        mu, theta0, gamma = 0.3, 0.14, 6.0
        a1s_low_lam = longitudinal_flapping_angle(mu, 0.06, theta0)
        a1s_high_lam = longitudinal_flapping_angle(mu, 0.08, theta0)
        self.assertGreater(a1s_high_lam, a1s_low_lam)
        self.assertAlmostEqual(a1s_high_lam, -0.067015706806282729,
                                delta=1e-9 * abs(a1s_high_lam))

    def test_lower_inflow_steepens_aft_tilt(self):
        mu, theta0 = 0.3, 0.14
        a1s_low_lam = longitudinal_flapping_angle(mu, 0.05, theta0)
        self.assertAlmostEqual(a1s_low_lam, -0.085863874345549734,
                                delta=1e-9 * abs(a1s_low_lam))

    def test_a1s_two_point_inflow_linearity(self):
        mu, theta0 = 0.3, 0.14
        d_a1s = (longitudinal_flapping_angle(mu, 0.06, theta0)
                  - longitudinal_flapping_angle(mu, 0.05, theta0))
        expected = 2.0 * mu * (0.06 - 0.05) / (1.0 - mu ** 2 / 2.0)
        self.assertAlmostEqual(d_a1s, expected, delta=1e-12)

    def test_a0_two_point_inflow_linearity(self):
        mu, theta0, gamma = 0.3, 0.14, 6.0
        d_a0 = (forward_coning_angle(mu, 0.06, theta0, gamma)
                 - forward_coning_angle(mu, 0.05, theta0, gamma))
        expected = -(gamma / 6.0) * (0.06 - 0.05)
        self.assertAlmostEqual(d_a0, expected, delta=1e-12)

    def test_b1s_two_point_inflow_linearity(self):
        mu, theta0, gamma = 0.3, 0.14, 6.0
        d_b1s = (lateral_flapping_angle(mu, 0.06, theta0, gamma)
                  - lateral_flapping_angle(mu, 0.05, theta0, gamma))
        expected = (2.0 * mu * gamma / 9.0) * (0.06 - 0.05) / (1.0 + mu ** 2 / 2.0)
        self.assertAlmostEqual(d_b1s, expected, delta=1e-12)


class TestGrowthWithAdvanceRatio(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: monotone growth of the flapping
    angles over the advance ratio, the published few-degree band."""

    def test_longitudinal_magnitude_strictly_increases(self):
        lam, theta0 = 0.06, 0.14
        mus = (0.1, 0.2, 0.3, 0.35)
        mags = [abs(longitudinal_flapping_angle(mu, lam, theta0)) for mu in mus]
        for earlier, later in zip(mags, mags[1:]):
            self.assertLess(earlier, later)
        expected = (0.025460636515912901, 0.051700680272108848,
                    0.079581151832460728, 0.094451841988459836)
        for got, want in zip(mags, expected):
            self.assertAlmostEqual(got, want, delta=1e-9 * want)

    def test_lateral_magnitude_strictly_increases(self):
        lam, theta0, gamma = 0.06, 0.14, 6.0
        mus = (0.1, 0.2, 0.3, 0.35)
        mags = [abs(lateral_flapping_angle(mu, lam, theta0, gamma)) for mu in mus]
        for earlier, later in zip(mags, mags[1:]):
            self.assertLess(earlier, later)
        expected = (0.0061094527363184121, 0.012862745098039217,
                    0.020842105263157901, 0.025444051825677268)
        for got, want in zip(mags, expected):
            self.assertAlmostEqual(got, want, delta=1e-9 * want)


class TestValueErrorRejection(unittest.TestCase):
    """ValueError rejection of every non-physical or non-finite input,
    the eleven anchor cases plus the valid hover-limit boundary."""

    def test_mu_negative_raises(self):
        for mu in (-0.1, -1.0):
            with self.subTest(mu=mu):
                with self.assertRaises(ValueError):
                    longitudinal_flapping_angle(mu, 0.06, 0.14)

    def test_mu_at_or_above_one_raises(self):
        for mu in (1.0, 1.5):
            with self.subTest(mu=mu):
                with self.assertRaises(ValueError):
                    longitudinal_flapping_angle(mu, 0.06, 0.14)

    def test_lam_nonpositive_raises(self):
        for lam in (0.0, -0.02):
            with self.subTest(lam=lam):
                with self.assertRaises(ValueError):
                    longitudinal_flapping_angle(0.3, lam, 0.14)

    def test_theta0_nonpositive_raises(self):
        for theta0 in (0.0, -0.1):
            with self.subTest(theta0=theta0):
                with self.assertRaises(ValueError):
                    longitudinal_flapping_angle(0.3, 0.06, theta0)

    def test_gamma_nonpositive_raises(self):
        for gamma in (0.0, -3.0):
            with self.subTest(gamma=gamma):
                with self.assertRaises(ValueError):
                    lateral_flapping_angle(0.3, 0.06, 0.14, gamma)

    def test_mu_nan_raises(self):
        with self.assertRaises(ValueError):
            longitudinal_flapping_angle(float("nan"), 0.06, 0.14)

    def test_lam_inf_raises(self):
        with self.assertRaises(ValueError):
            forward_coning_angle(0.3, float("inf"), 0.14, 6.0)

    def test_forward_coning_and_summary_reject_bad_inputs(self):
        with self.assertRaises(ValueError):
            forward_coning_angle(-0.1, 0.06, 0.14, 6.0)
        with self.assertRaises(ValueError):
            forward_coning_angle(0.3, 0.0, 0.14, 6.0)
        with self.assertRaises(ValueError):
            forward_coning_angle(0.3, 0.06, 0.0, 6.0)
        with self.assertRaises(ValueError):
            forward_coning_angle(0.3, 0.06, 0.14, 0.0)
        with self.assertRaises(ValueError):
            forward_flap_summary(1.5, 0.06, 0.14, 6.0)

    def test_mu_zero_is_valid_hover_limit(self):
        # mu = 0.0 is a valid hover-limit input, must not raise.
        self.assertEqual(longitudinal_flapping_angle(0.0, 0.06, 0.14), 0.0)


class TestDeterminism(unittest.TestCase):
    """No RNG, no imports beyond math: two identical calls return
    identical bits."""

    def test_summary_and_components_repeatable(self):
        first = forward_flap_summary(0.3, 0.06, 0.14, 6.0)
        second = forward_flap_summary(0.3, 0.06, 0.14, 6.0)
        self.assertEqual(first, second)
        self.assertEqual(
            forward_coning_angle(0.3, 0.06, 0.14, 6.0),
            forward_coning_angle(0.3, 0.06, 0.14, 6.0),
        )
        self.assertEqual(
            longitudinal_flapping_angle(0.3, 0.06, 0.14),
            longitudinal_flapping_angle(0.3, 0.06, 0.14),
        )
        self.assertEqual(
            lateral_flapping_angle(0.3, 0.06, 0.14, 6.0),
            lateral_flapping_angle(0.3, 0.06, 0.14, 6.0),
        )


if __name__ == "__main__":
    unittest.main()

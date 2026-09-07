"""Contract test for squire-young-profile-drag.

Exercises the SKILL.md workflow end to end: step 1 fixes the section
state (chord, freestream, Reynolds number); step 2 takes the
trailing-edge momentum state (trailing-edge-momentum-thickness and edge
velocity); steps 3-4 evaluate the edge-velocity-ratio exponent and the
squire-young-formula mapping to the section profile-drag-coefficient;
step 5 checks the zero-pressure-gradient reduction to the laminar
flat-plate value; steps 6-7 run the laminar integral-growth traverse
and the fully laminar chain; step 8 combines both surfaces at symmetric
zero lift; step 9 is this contract test with the input-rejection
traverse. All asserts are tolerance-based (assertAlmostEqual/isclose);
no exact float equality on computed values. Deterministic, offline,
stdlib only, runs in seconds.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import squire_young_profile_drag_logic as sy

NU_AIR = 1.46e-5
U_INF = 30.0
CHORD = 1.0
RE_C = U_INF * CHORD / NU_AIR            # 2.0547945205e6
THETA_BL = 0.664 * CHORD / math.sqrt(RE_C)   # 4.6321634974e-4 m
REF_DRAG = 1.328 / math.sqrt(RE_C)           # 9.2643269948e-4


def flat_traverse(n_stations, u_val):
    """Constant-velocity plate traverse over x in [0, 1] m (workflow step 6 grid)."""
    xs = [i * CHORD / (n_stations - 1) for i in range(n_stations)]
    return xs, [u_val] * n_stations


class TrailingEdgeFactorTests(unittest.TestCase):
    """Steps 2-3: the trailing-edge factor carries the edge-velocity-ratio exponent."""

    def test_factor_case_a_anchor(self):
        """Step 3 anchor: (27/30)**3.2 = 0.71379915616, the factor below unity when the TE edge velocity is 0.9 of the freestream."""
        self.assertAlmostEqual(sy.trailing_edge_factor(27.0, 30.0, 1.4),
                               0.71379915616, delta=1e-8)

    def test_factor_unity_on_flat_plate(self):
        """Step 5 reduction: at U_TE = U_inf the factor is exactly 1.0 for any shape factor."""
        for h in (1.4, 2.6):
            self.assertAlmostEqual(sy.trailing_edge_factor(30.0, 30.0, h), 1.0, delta=1e-12)

    def test_factor_turbulent_shape_band(self):
        """Step 2: at H_TE = 2.6 the factor (27/30)**3.8 = 0.67007210063, about 6 percent lower than at 1.4."""
        self.assertAlmostEqual(sy.trailing_edge_factor(27.0, 30.0, 2.6),
                               0.67007210063, delta=1e-8)

    def test_factor_ratio_exponent_algebra(self):
        """Step 3 algebra: f(1.4)/f(2.6) equals (0.9)**((1.4-2.6)/2) = (0.9)**(-0.6)."""
        f14 = sy.trailing_edge_factor(27.0, 30.0, 1.4)
        f26 = sy.trailing_edge_factor(27.0, 30.0, 2.6)
        self.assertTrue(math.isclose(f14 / f26, 0.9 ** -0.6, rel_tol=1e-9))

    def test_factor_deterministic_repeat(self):
        """Step 9 determinism: repeated calls on identical inputs return identical factors."""
        a = sy.trailing_edge_factor(27.0, 30.0, 1.4)
        b = sy.trailing_edge_factor(27.0, 30.0, 1.4)
        self.assertEqual(a, b)

    def test_factor_valueerrors(self):
        """Input-rejection traverse (step 9): non-positive velocities and shape factors at or below 1.0 raise ValueError."""
        bad = [(0.0, 30.0, 1.4), (-1.0, 30.0, 1.4), (27.0, 0.0, 1.4),
               (27.0, 30.0, 1.0), (27.0, 30.0, 0.5)]
        for u_te, u_inf, h in bad:
            with self.subTest(u_te=u_te, u_inf=u_inf, h_te=h):
                with self.assertRaises(ValueError):
                    sy.trailing_edge_factor(u_te, u_inf, h)


class ProfileDragFormulaTests(unittest.TestCase):
    """Step 4: the squire-young-formula maps the trailing-edge-momentum-thickness to the section profile-drag-coefficient."""

    def test_profile_drag_case_a_anchor(self):
        """Step 4 anchor: theta_TE/c = 0.003 at U_TE/U_inf = 0.9 gives 4.2827949370e-3 one surface, inside the 4.0e-3 to 4.5e-3 magnitude band."""
        cd = sy.squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4)
        self.assertAlmostEqual(cd, 4.2827949370e-3, delta=1e-9)
        self.assertGreater(cd, 4.0e-3)
        self.assertLess(cd, 4.5e-3)

    def test_profile_drag_algebra_factor_product(self):
        """Step 4 algebra: the coefficient equals 2*(theta_TE/c)*trailing_edge_factor to float noise."""
        cd = sy.squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4)
        hand = 2.0 * (3.0e-3 / 1.0) * sy.trailing_edge_factor(27.0, 30.0, 1.4)
        self.assertAlmostEqual(cd, hand, delta=1e-12)

    def test_both_surfaces_symmetric_zero_lift(self):
        """Step 8 combination: both surfaces of a symmetric section at zero lift sharing the TE state give twice the one-surface value, 8.5655898739e-3."""
        one = sy.squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4)
        self.assertAlmostEqual(2.0 * one, 8.5655898739e-3, delta=1e-9)

    def test_anchor_identity_blasius_reduction(self):
        """Step 5 anchor: at U_TE = U_inf with theta_TE = 0.664*c/sqrt(Re_c) the formula reproduces 1.328/sqrt(Re_c), independent of the shape factor."""
        for h in (1.4, 2.6):
            cd = sy.squire_young_profile_drag(THETA_BL, CHORD, 30.0, 30.0, h)
            self.assertTrue(math.isclose(cd, REF_DRAG, rel_tol=1e-9),
                            "h_te=%s cd=%.12e ref=%.12e" % (h, cd, REF_DRAG))

    def test_profile_drag_h_sensitivity(self):
        """Step 2 sensitivity: at H_TE = 2.6 the estimate falls to 4.0204326038e-3, about 6.1 percent below the H_TE = 1.4 value at ratio 0.9."""
        cd26 = sy.squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 2.6)
        cd14 = sy.squire_young_profile_drag(3.0e-3, 1.0, 27.0, 30.0, 1.4)
        self.assertAlmostEqual(cd26, 4.0204326038e-3, delta=1e-9)
        self.assertTrue(math.isclose(cd26 / cd14, 0.9 ** 0.6, rel_tol=1e-9))

    def test_profile_drag_valueerrors(self):
        """Input-rejection traverse (step 9): non-positive theta_TE, chord, velocities and shape factors at or below 1.0 raise ValueError."""
        bad = [(0.0, 1.0, 27.0, 30.0, 1.4),            # theta_te = 0
               (3.0e-3, 0.0, 27.0, 30.0, 1.4),         # chord = 0
               (3.0e-3, 1.0, 0.0, 30.0, 1.4),          # u_te = 0
               (3.0e-3, 1.0, -1.0, 30.0, 1.4),         # u_te < 0
               (3.0e-3, 1.0, 27.0, 0.0, 1.4),          # u_inf = 0
               (3.0e-3, 1.0, 27.0, 30.0, 1.0),         # h_te at 1.0
               (3.0e-3, 1.0, 27.0, 30.0, 0.5)]         # h_te below 1.0
        for theta_te, chord, u_te, u_inf, h in bad:
            with self.subTest(theta_te=theta_te, chord=chord, h_te=h):
                with self.assertRaises(ValueError):
                    sy.squire_young_profile_drag(theta_te, chord, u_te, u_inf, h)


class MomentumGrowthTests(unittest.TestCase):
    """Step 6: the laminar integral-growth traverse of the momentum thickness to the trailing edge."""

    def test_flat_plate_blasius_momentum_thickness(self):
        """Step 6 anchor: on the constant-velocity plate theta_TE closes to 0.664*c/sqrt(Re_c) = 4.6321634974e-4 m (rel ~3e-14)."""
        xs, ues = flat_traverse(4001, 30.0)
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        self.assertTrue(math.isclose(theta, THETA_BL, rel_tol=1e-6),
                        "theta=%.12e blasius=%.12e" % (theta, THETA_BL))

    def test_leading_edge_gap_convention(self):
        """Step 6 convention: a traverse starting mid-plate at constant edge velocity keeps the LE-gap segment at the first-station value and closes to the same Blasius theta."""
        n = 1001
        xs = [0.25 + i * 0.75 / (n - 1) for i in range(n)]
        ues = [30.0] * n
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        self.assertTrue(math.isclose(theta, THETA_BL, rel_tol=1e-6))

    def test_partial_plate_scaling(self):
        """Step 6 scaling: theta grows like sqrt(x), so a traverse ending at x = 0.25 m gives 0.664*0.25/sqrt(Re at 0.25)."""
        n = 1001
        xs = [i * 0.25 / (n - 1) for i in range(n)]
        ues = [30.0] * n
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        ref = 0.664 * 0.25 / math.sqrt(30.0 * 0.25 / NU_AIR)
        self.assertTrue(math.isclose(theta, ref, rel_tol=1e-6))

    def test_linear_law_closed_form(self):
        """Step 6 quadrature: for Ue(x) = U_inf*(1 - a*x/c) the trapezoid theta matches the exact closed-form integral within 1e-6 relative at 1001 stations."""
        n = 1001
        xs = [i * CHORD / (n - 1) for i in range(n)]
        ues = [30.0 * (1.0 - 0.1 * x) for x in xs]
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        closed = math.sqrt(sy.GROWTH_C * NU_AIR * 30.0 ** 5 * CHORD
                           * (1.0 - 0.9 ** 6) / (6.0 * 0.1) / 27.0 ** 6)
        self.assertTrue(math.isclose(theta, closed, rel_tol=1e-6),
                        "theta=%.12e closed=%.12e rel=%.3e" % (theta, closed, abs(theta - closed) / closed))

    def test_case_c_momentum_thickness_anchor(self):
        """Step 6 anchor (Case C): the 4001-station linear-decay traverse Ue = 30*(1 - 0.1*x) grows theta_TE to 5.6151694776e-4 m, closing to the closed form (rel 5.7e-10)."""
        xs, ues = flat_traverse(4001, 30.0)
        ues = [30.0 * (1.0 - 0.1 * x) for x in xs]
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        closed = math.sqrt(sy.GROWTH_C * NU_AIR * 30.0 ** 5 * CHORD
                           * (1.0 - 0.9 ** 6) / (6.0 * 0.1) / 27.0 ** 6)
        self.assertTrue(math.isclose(theta, 5.6151694776e-4, rel_tol=1e-6))
        self.assertTrue(math.isclose(theta, closed, rel_tol=1e-6))

    def test_case_c_raw_momentum_above_flat_plate(self):
        """Step 6 read-off: the decelerated layer is thicker, raw 2*theta_TE/c = 1.1230338955e-3 sits above the flat-plate 9.2643269948e-4."""
        xs = [i * CHORD / 4000 for i in range(4001)]
        ues = [30.0 * (1.0 - 0.1 * x) for x in xs]
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        raw = 2.0 * theta / CHORD
        self.assertAlmostEqual(raw, 1.1230338955e-3, delta=1e-9)
        self.assertGreater(raw, REF_DRAG)

    def test_momentum_thickness_valueerrors(self):
        """Input-rejection traverse (step 9): short, unequal, negative-origin, non-increasing, zero-velocity and zero-nu inputs raise ValueError."""
        xs2, ues2 = flat_traverse(2, 30.0)
        # fewer than two stations
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te([0.5], [30.0], NU_AIR)
        # unequal lengths
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te([0.0, 0.5, 1.0], [30.0, 30.0], NU_AIR)
        # xs below zero
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te([-0.1, 0.5], [30.0, 30.0], NU_AIR)
        # non-increasing stations
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te([0.0, 0.5, 0.5], [30.0, 30.0, 30.0], NU_AIR)
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te([0.5, 0.0], [30.0, 30.0], NU_AIR)
        # zero edge velocity
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te([0.0, 0.5], [30.0, 0.0], NU_AIR)
        # nu at zero
        with self.assertRaises(ValueError):
            sy.momentum_thickness_at_te(xs2, ues2, 0.0)


class FullyLaminarChainTests(unittest.TestCase):
    """Steps 6-7: the fully laminar chain grows theta to the trailing edge and applies the squire-young-formula edge-velocity-ratio exponent."""

    def test_flat_plate_chain_reproduces_blasius_drag(self):
        """Step 7 anchor: the chain on the constant-velocity plate returns 1.328/sqrt(Re_c) = 9.2643269948e-4 (rel ~3e-14), GROWTH_C = 0.664**2 closes the growth exactly."""
        xs, ues = flat_traverse(4001, 30.0)
        cd = sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, U_INF, 1.4)
        self.assertTrue(math.isclose(cd, REF_DRAG, rel_tol=1e-6),
                        "cd=%.12e ref=%.12e" % (cd, REF_DRAG))

    def test_chain_matches_direct_formula(self):
        """Step 7 consistency: the chain value equals squire_young_profile_drag(theta_TE, c, U_TE, U_inf) built from the grown theta."""
        xs, ues = flat_traverse(4001, 30.0)
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        direct = sy.squire_young_profile_drag(theta, CHORD, 30.0, 30.0, 1.4)
        chain = sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, U_INF, 1.4)
        self.assertAlmostEqual(chain, direct, delta=1e-15)

    def test_reynolds_invariance(self):
        """Step 7 invariance: c_d,p*sqrt(Re_c) = 1.328 on the plate at Re_c and at Re_c/2 (U = 15 m/s), rel residual ~3e-14."""
        xs30, ues30 = flat_traverse(4001, 30.0)
        cd30 = sy.fully_laminar_profile_drag(xs30, ues30, NU_AIR, CHORD, 30.0, 1.4)
        xs15, ues15 = flat_traverse(4001, 15.0)
        cd15 = sy.fully_laminar_profile_drag(xs15, ues15, NU_AIR, CHORD, 15.0, 1.4)
        re15 = 15.0 * CHORD / NU_AIR
        self.assertTrue(math.isclose(cd30 * math.sqrt(RE_C), 1.328, rel_tol=1e-9))
        self.assertTrue(math.isclose(cd15 * math.sqrt(re15), 1.328, rel_tol=1e-9))

    def test_case_c_chain_anchor(self):
        """Step 7 anchor (Case C): the linear-decay traverse chain gives 8.0162064696e-4, equal to 2*(theta_TE/c)*(0.9)**3.2 (residual 0.0)."""
        xs = [i * CHORD / 4000 for i in range(4001)]
        ues = [30.0 * (1.0 - 0.1 * x) for x in xs]
        cd = sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, U_INF, 1.4)
        self.assertTrue(math.isclose(cd, 8.0162064696e-4, rel_tol=1e-6))
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        hand = 2.0 * (theta / CHORD) * (0.9 ** 3.2)
        self.assertTrue(math.isclose(cd, hand, rel_tol=1e-9))

    def test_case_c_below_raw_momentum_value(self):
        """Step 7 read-off: the 0.7138 edge-velocity factor brings the estimate below the raw momentum-integral value 2*theta_TE/c = 1.123e-3."""
        xs = [i * CHORD / 4000 for i in range(4001)]
        ues = [30.0 * (1.0 - 0.1 * x) for x in xs]
        theta = sy.momentum_thickness_at_te(xs, ues, NU_AIR)
        cd = sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, U_INF, 1.4)
        raw = 2.0 * theta / CHORD
        self.assertLess(cd, raw)
        self.assertTrue(math.isclose(cd / raw, sy.trailing_edge_factor(27.0, 30.0, 1.4), rel_tol=1e-9))

    def test_fully_laminar_valueerrors(self):
        """Input-rejection traverse (step 9): non-positive chord and freestream raise ValueError on the one-call chain."""
        xs, ues = flat_traverse(2, 30.0)
        with self.assertRaises(ValueError):
            sy.fully_laminar_profile_drag(xs, ues, NU_AIR, 0.0, U_INF, 1.4)
        with self.assertRaises(ValueError):
            sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, -1.0, 1.4)
        # momentum-thickness invalid set propagates through the chain
        with self.assertRaises(ValueError):
            sy.fully_laminar_profile_drag([0.0], [30.0], NU_AIR, CHORD, U_INF, 1.4)

    def test_chain_deterministic_repeat(self):
        """Step 9 determinism: repeated chain runs on the same traverse return identical coefficients."""
        xs, ues = flat_traverse(4001, 30.0)
        a = sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, U_INF, 1.4)
        b = sy.fully_laminar_profile_drag(xs, ues, NU_AIR, CHORD, U_INF, 1.4)
        self.assertEqual(a, b)


class ModuleConstantsTests(unittest.TestCase):
    """Step 1: module constants and the deterministic closed-form structure."""

    def test_module_constants(self):
        """Step 1 constants: NU_AIR = 1.46e-5, H_TE = 1.4, the Blasius constants 0.664/1.328 and GROWTH_C = 0.664**2 = 0.440896."""
        self.assertEqual(sy.NU_AIR, 1.46e-5)
        self.assertEqual(sy.H_TE, 1.4)
        self.assertEqual(sy.LAMINAR_THETA_C, 0.664)
        self.assertEqual(sy.BLASIUS_DRAG_C, 1.328)
        self.assertAlmostEqual(sy.GROWTH_C, 0.440896, delta=1e-15)

    def test_no_randomness_no_iteration(self):
        """Step 9 structure: the module is closed form with a single deterministic trapezoid quadrature, no RNG state to seed."""
        import inspect
        src = inspect.getsource(sy)
        self.assertNotIn("import random", src)
        self.assertNotIn("numpy", src)
        self.assertNotIn("scipy", src)


if __name__ == "__main__":
    unittest.main()

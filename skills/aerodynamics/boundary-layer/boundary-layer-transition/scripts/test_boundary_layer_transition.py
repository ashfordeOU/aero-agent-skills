"""Contract test for boundary-layer-transition (Thwaites + Michel).

Deterministic, offline, stdlib only. Run with:

    python3 scripts/test_boundary_layer_transition.py

Covers the worked-example anchors (flat plate nu = 1.46e-5 m2/s,
Ue = 30 m/s), the magnitude bounds from the engineering spec, the
validation list (ValueError rejections, flat-plate closed-form
identity, determinism), and the Michel criterion logic.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boundary_layer_transition_logic as blt  # noqa: E402

NU = 1.46e-5
UE = 30.0
SQRT045 = 0.6708203932499369


def _rel_diff(a, b):
    return abs(a - b) / abs(b)


class MomentumThicknessProfileTests(unittest.TestCase):
    """Thwaites integral momentum thickness on a flat plate."""

    def test_flat_plate_theta_matches_closed_form(self):
        # Trapezoid Thwaites integral is exact for constant Ue: theta
        # must match 0.6708 sqrt(Re_x) nu / Ue within 1e-6 relative.
        xs = [0.25, 1.0, 2.0]
        theta = blt.momentum_thickness_profile(xs, [UE, UE, UE], NU)
        for x, t in zip(xs, theta):
            closed = SQRT045 * math.sqrt(UE * x / NU) * NU / UE
            self.assertLess(_rel_diff(t, closed), 1e-6)

    def test_flat_plate_theta_at_1m_anchor(self):
        # Spec worked example: theta ~ 4.680e-4 m at x = 1 m.
        theta = blt.momentum_thickness_profile([0.25, 1.0, 2.0], [UE, UE, UE], NU)
        self.assertLess(_rel_diff(theta[1], 4.680e-4), 1e-3)
        self.assertAlmostEqual(theta[1], 4.679744e-4, delta=1e-8)

    def test_flat_plate_theta_monotonic_increasing(self):
        theta = blt.momentum_thickness_profile([0.25, 1.0, 2.0], [UE, UE, UE], NU)
        for prev, cur in zip(theta, theta[1:]):
            self.assertGreater(cur, prev)

    def test_leading_edge_theta_zero(self):
        # Station at x = 0 has zero accumulated integral, so theta = 0.
        theta = blt.momentum_thickness_profile([0.0, 1.0], [UE, UE], NU)
        self.assertEqual(theta[0], 0.0)
        self.assertGreater(theta[1], 0.0)

    def test_station_grid_valueerrors(self):
        cases = {
            "too_few_stations": ([1.0], [UE]),
            "unequal_lengths": ([0.1, 0.2], [UE]),
            "negative_x": ([-0.1, 0.2], [UE, UE]),
            "decreasing_x": ([0.3, 0.2], [UE, UE]),
            "duplicate_x": ([0.2, 0.2, 0.4], [UE, UE, UE]),
        }
        for name, (xs, ues) in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    blt.momentum_thickness_profile(xs, ues, NU)

    def test_velocity_valueerrors(self):
        for ue in (0.0, -1.0):
            with self.subTest(ue=ue):
                with self.assertRaises(ValueError):
                    blt.momentum_thickness_profile([0.1, 0.2], [ue, ue], NU)

    def test_viscosity_valueerrors(self):
        for nu in (0.0, -1.46e-5):
            with self.subTest(nu=nu):
                with self.assertRaises(ValueError):
                    blt.momentum_thickness_profile([0.1, 0.2], [UE, UE], nu)


class ReThetaProfileTests(unittest.TestCase):
    """Momentum-thickness Reynolds number Re_theta = Ue theta / nu."""

    def test_flat_plate_re_theta_identity(self):
        # Re_theta from the profile must equal 0.6708 sqrt(Re_x).
        xs = [0.25, 1.0, 2.0]
        theta = blt.momentum_thickness_profile(xs, [UE, UE, UE], NU)
        re_theta = blt.re_theta_profile(xs, [UE, UE, UE], theta, NU)
        for x, value in zip(xs, re_theta):
            closed = SQRT045 * math.sqrt(UE * x / NU)
            self.assertLess(_rel_diff(value, closed), 1e-9)
        self.assertAlmostEqual(re_theta[1], 961.5911471340485, delta=1e-6)

    def test_re_theta_profile_valueerrors(self):
        theta = blt.momentum_thickness_profile([0.25, 1.0], [UE, UE], NU)
        with self.assertRaises(ValueError):
            blt.re_theta_profile([0.25, 1.0, 2.0], [UE, UE, UE], theta, NU)
        with self.assertRaises(ValueError):
            blt.re_theta_profile([0.25, 1.0], [UE, UE], theta, 0.0)


class MichelCriterionTests(unittest.TestCase):
    """Michel transition criterion Re_theta,tr = 1.174 (1 + 22400/Re_x)
    Re_x**0.46."""

    def test_michel_threshold_known_value(self):
        # Re_x = 2.0548e6 at x = 1 m, Ue = 30, nu = 1.46e-5.
        self.assertLess(_rel_diff(blt.michel_threshold(2.0548e6), 951.1540249456673), 1e-9)

    def test_michel_criterion_below_false(self):
        self.assertFalse(blt.michel_criterion(2.0548e6, 900.0))

    def test_michel_criterion_equal_true(self):
        threshold = blt.michel_threshold(2.0548e6)
        self.assertTrue(blt.michel_criterion(2.0548e6, threshold))

    def test_michel_criterion_above_true(self):
        self.assertTrue(blt.michel_criterion(2.0548e6, 1000.0))

    def test_michel_criterion_valueerrors(self):
        with self.assertRaises(ValueError):
            blt.michel_criterion(0.0, 100.0)
        with self.assertRaises(ValueError):
            blt.michel_criterion(-2.0548e6, 100.0)
        with self.assertRaises(ValueError):
            blt.michel_criterion(2.0548e6, -1.0)


class TransitionLocationTests(unittest.TestCase):
    """Full sweep: profiles, margins, transition index and interpolation."""

    def test_transition_location_keys(self):
        result = blt.transition_location([0.25, 1.0, 2.0], [UE, UE, UE], NU)
        self.assertEqual(
            set(result.keys()),
            {"theta_list", "re_theta_list", "criterion_margin_list",
             "x_transition", "transition_index", "interp_x_transition"},
        )
        self.assertEqual(len(result["theta_list"]), 3)
        self.assertEqual(len(result["re_theta_list"]), 3)
        self.assertEqual(len(result["criterion_margin_list"]), 3)

    def test_transition_location_station_value_3station(self):
        # x_transition is the first station with margin >= 0, NOT the
        # interpolated crossing: station x = 1.0 while interp ~ 0.839.
        result = blt.transition_location([0.25, 1.0, 2.0], [UE, UE, UE], NU)
        self.assertEqual(result["transition_index"], 1)
        self.assertEqual(result["x_transition"], 1.0)

    def test_transition_location_interp_value_3station(self):
        result = blt.transition_location([0.25, 1.0, 2.0], [UE, UE, UE], NU)
        self.assertAlmostEqual(result["interp_x_transition"], 0.838910245974557, delta=1e-9)
        self.assertNotEqual(result["interp_x_transition"], result["x_transition"])

    def _dense_result(self):
        xs = [0.01 + 0.01 * i for i in range(200)]  # 0.01 to 2.0 m
        return blt.transition_location(xs, [UE] * len(xs), NU)

    def test_transition_location_flat_plate_x_bounds(self):
        # Spec magnitude bound: transition x in 0.6-1.1 m at Ue 30 m/s.
        result = self._dense_result()
        self.assertIsNotNone(result["x_transition"])
        self.assertGreater(result["x_transition"], 0.6)
        self.assertLess(result["x_transition"], 1.1)
        self.assertGreater(result["interp_x_transition"], 0.6)
        self.assertLess(result["interp_x_transition"], 1.1)

    def test_transition_location_flat_plate_re_theta_bounds(self):
        # Spec magnitude bound: Re_theta at the crossing in 800-1100.
        result = self._dense_result()
        i = result["transition_index"]
        self.assertGreater(result["re_theta_list"][i], 800.0)
        self.assertLess(result["re_theta_list"][i], 1100.0)

    def test_transition_location_margin_sign_flip(self):
        result = self._dense_result()
        i = result["transition_index"]
        self.assertLess(result["criterion_margin_list"][i - 1], 0.0)
        self.assertGreaterEqual(result["criterion_margin_list"][i], 0.0)

    def test_transition_location_interp_consistency(self):
        # Interpolated x sits between the bracketing stations and its
        # margins bracket zero.
        xs = [0.25, 1.0, 2.0]
        result = blt.transition_location(xs, [UE, UE, UE], NU)
        i = result["transition_index"]
        interp = result["interp_x_transition"]
        self.assertGreater(interp, xs[i - 1])
        self.assertLess(interp, xs[i])

    def test_transition_location_never_crossed(self):
        # Low speed never reaches the Michel threshold over the body.
        xs = [0.01, 0.02, 0.03, 0.05]
        result = blt.transition_location(xs, [5.0] * len(xs), NU)
        self.assertIsNone(result["x_transition"])
        self.assertIsNone(result["transition_index"])
        self.assertIsNone(result["interp_x_transition"])
        for margin in result["criterion_margin_list"]:
            self.assertLess(margin, 0.0)

    def test_transition_location_first_station_crossed(self):
        # Fully turbulent flow from the first station: interp x is the
        # first station x.
        xs = [1.5, 2.0]
        result = blt.transition_location(xs, [UE, UE], NU)
        self.assertEqual(result["transition_index"], 0)
        self.assertEqual(result["x_transition"], 1.5)
        self.assertEqual(result["interp_x_transition"], 1.5)

    def test_transition_location_valueerror_propagates(self):
        with self.assertRaises(ValueError):
            blt.transition_location([0.1, 0.2], [UE, UE], 0.0)
        with self.assertRaises(ValueError):
            blt.transition_location([0.2, 0.1], [UE, UE], NU)


class FlatPlateTransitionTests(unittest.TestCase):
    """Closed-form flat-plate natural-transition helper."""

    def test_flat_plate_transition_x_bounds(self):
        # Spec magnitude bound: x_tr in 0.6-1.1 m at Ue 30 m/s,
        # nu 1.46e-5 (Re_x,tr ~ 1.7e6).
        x_tr = blt.flat_plate_transition(NU, UE, 2.0)
        self.assertIsNotNone(x_tr)
        self.assertGreater(x_tr, 0.6)
        self.assertLess(x_tr, 1.1)

    def test_flat_plate_transition_x_anchor(self):
        # Real module output on the worked example.
        self.assertAlmostEqual(blt.flat_plate_transition(NU, UE, 2.0), 0.812594, delta=1e-3)

    def test_flat_plate_transition_re_theta_bounds(self):
        # Spec magnitude bound: Re_theta at the crossing in 800-1100.
        x_tr = blt.flat_plate_transition(NU, UE, 2.0)
        re_x = UE * x_tr / NU
        re_theta = SQRT045 * math.sqrt(re_x)
        self.assertGreater(re_theta, 800.0)
        self.assertLess(re_theta, 1100.0)
        self.assertAlmostEqual(re_theta, 866.8167, delta=2.0)

    def test_flat_plate_transition_margin_sign_flip(self):
        # Margin is negative just below x_tr and non-negative at x_tr
        # on the 500-step scan grid.
        x_tr = blt.flat_plate_transition(NU, UE, 2.0)
        dx = (2.0 - 1e-3) / 500.0
        margin_below = SQRT045 * math.sqrt(UE * (x_tr - dx) / NU) - blt.michel_threshold(
            UE * (x_tr - dx) / NU
        )
        margin_at = SQRT045 * math.sqrt(UE * x_tr / NU) - blt.michel_threshold(
            UE * x_tr / NU
        )
        self.assertLess(margin_below, 0.0)
        self.assertGreaterEqual(margin_at, 0.0)

    def test_flat_plate_transition_none_on_short_plate(self):
        # Plate far shorter than the natural-transition distance: no
        # crossing, returns None.
        self.assertIsNone(blt.flat_plate_transition(NU, UE, 0.001))

    def test_flat_plate_transition_valueerrors(self):
        with self.assertRaises(ValueError):
            blt.flat_plate_transition(0.0, UE, 2.0)
        with self.assertRaises(ValueError):
            blt.flat_plate_transition(NU, 0.0, 2.0)
        with self.assertRaises(ValueError):
            blt.flat_plate_transition(NU, UE, 0.0)


class DeterminismTests(unittest.TestCase):
    """Identical inputs give identical outputs (no RNG, no state)."""

    def test_determinism_profile(self):
        xs = [0.25, 1.0, 2.0]
        first = blt.momentum_thickness_profile(xs, [UE, UE, UE], NU)
        second = blt.momentum_thickness_profile(xs, [UE, UE, UE], NU)
        self.assertEqual(first, second)

    def test_determinism_transition_location(self):
        xs = [0.01 + 0.01 * i for i in range(200)]
        first = blt.transition_location(xs, [UE] * len(xs), NU)
        second = blt.transition_location(xs, [UE] * len(xs), NU)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()

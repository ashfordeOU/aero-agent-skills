"""Contract tests for the Clohessy-Wiltshire leaf logic module.

Offline, stdlib only, deterministic. Run from the repo root:

    python3 skills/space-systems/orbit-mechanics/clohessy-wiltshire/scripts/test_clohessy_wiltshire.py

Worked-example anchors (chief a = 6.878e6 m, mu = 3.986004418e14):
mean motion n = 1.106817e-3 rad/s, period 5676.81 s. Deputy state
[x, y, z, x', y', z'] = [1000, 0, 500, 0, -2*n*1000, 0] m, m/s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import clohessy_wiltshire_logic as cw

MU = 3.986004418e14
A_CHIEF = 6.878e6
N_CHIEF = math.sqrt(MU / A_CHIEF**3)  # ~1.106817e-3 rad/s
PERIOD = 2.0 * math.pi / N_CHIEF  # ~5676.81 s
X0 = 1000.0
Z0 = 500.0
STATE_BOUNDED = [X0, 0.0, Z0, 0.0, -2.0 * N_CHIEF * X0, 0.0]
STATE_TARGET_INPLANE = [X0, 0.0, 0.0, 0.0, -2.0 * N_CHIEF * X0, 0.0]
TARGET_ORIGIN = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


class TestMeanMotion(unittest.TestCase):
    def test_worked_example_n(self):
        n = cw.mean_motion(A_CHIEF)
        self.assertAlmostEqual(n, 1.106817e-3, delta=1e-8)

    def test_worked_example_period(self):
        n = cw.mean_motion(A_CHIEF)
        self.assertAlmostEqual(2.0 * math.pi / n, 5676.81, delta=0.5)

    def test_n_matches_sqrt_mu_a3(self):
        n = cw.mean_motion(A_CHIEF)
        self.assertAlmostEqual(n, math.sqrt(MU / A_CHIEF**3), places=15)

    def test_nonpositive_a_raises(self):
        for a in (0.0, -100.0):
            with self.assertRaises(ValueError):
                cw.mean_motion(a)

    def test_nonpositive_mu_raises(self):
        with self.assertRaises(ValueError):
            cw.mean_motion(A_CHIEF, mu=0.0)
        with self.assertRaises(ValueError):
            cw.mean_motion(A_CHIEF, mu=float("nan"))


class TestCwStm(unittest.TestCase):
    def test_identity_at_zero(self):
        stm = cw.cw_stm(N_CHIEF, 0.0)
        worst = max(
            abs(stm[i][j] - (1.0 if i == j else 0.0))
            for i in range(6)
            for j in range(6)
        )
        self.assertLessEqual(worst, 1e-12)

    def test_dimensions_and_rows(self):
        stm = cw.cw_stm(N_CHIEF, PERIOD / 4.0)
        self.assertEqual(len(stm), 6)
        for row in stm:
            self.assertEqual(len(row), 6)

    def test_known_one_orbit_inplane_terms(self):
        stm = cw.cw_stm(N_CHIEF, PERIOD)
        self.assertAlmostEqual(stm[0][0], 1.0, places=9)
        self.assertAlmostEqual(stm[1][0], -12.0 * math.pi, places=9)
        self.assertAlmostEqual(stm[1][5], 0.0, places=9)
        self.assertAlmostEqual(stm[4][4], 1.0, places=9)

    def test_z_block_harmonic_terms(self):
        stm = cw.cw_stm(N_CHIEF, PERIOD / 4.0)
        self.assertAlmostEqual(stm[2][2], math.cos(math.pi / 2.0), places=12)
        self.assertAlmostEqual(stm[2][5], math.sin(math.pi / 2.0) / N_CHIEF, places=9)

    def test_negative_tau_raises(self):
        with self.assertRaises(ValueError):
            cw.cw_stm(N_CHIEF, -1.0)

    def test_nonpositive_n_raises(self):
        with self.assertRaises(ValueError):
            cw.cw_stm(0.0, 10.0)
        with self.assertRaises(ValueError):
            cw.cw_stm(-1.0, 10.0)

    def test_nonfinite_inputs_raise(self):
        with self.assertRaises(ValueError):
            cw.cw_stm(float("nan"), 10.0)
        with self.assertRaises(ValueError):
            cw.cw_stm(N_CHIEF, float("inf"))


class TestPropagate(unittest.TestCase):
    def test_bounded_one_orbit_returns(self):
        s = cw.cw_propagate(STATE_BOUNDED, N_CHIEF, PERIOD)
        self.assertAlmostEqual(s[0], X0, delta=X0 * 0.01)  # x back within 1%
        self.assertAlmostEqual(s[1], 0.0, delta=X0 * 0.01)  # y ~ 0, no drift
        self.assertAlmostEqual(s[2], Z0, delta=Z0 * 0.01)  # z back within 1%
        # quote the real linear-model drift: y(T) ~ 7.3e-13 m
        self.assertLess(abs(s[1]), 1e-6)

    def test_bounded_ten_orbits_no_secular_drift(self):
        s = cw.cw_propagate(STATE_BOUNDED, N_CHIEF, 10.0 * PERIOD)
        self.assertLess(abs(s[1]), 1e-6)
        self.assertAlmostEqual(s[0], X0, delta=X0 * 0.02)

    def test_zero_tau_is_identity_apply(self):
        s = cw.cw_propagate(STATE_BOUNDED, N_CHIEF, 0.0)
        for i in range(6):
            self.assertAlmostEqual(s[i], STATE_BOUNDED[i], places=9)

    def test_z_harmonic_half_orbit_flip(self):
        s = cw.cw_propagate([0.0, 0.0, Z0, 0.0, 0.0, 0.0], N_CHIEF, PERIOD / 2.0)
        self.assertAlmostEqual(s[2], -Z0, delta=1e-6)

    def test_drift_case_grows_linearly(self):
        state_drift = [X0, 0.0, Z0, 0.0, 0.0, 0.0]  # y_dot0 = 0 violates bound
        s1 = cw.cw_propagate(state_drift, N_CHIEF, PERIOD)
        s2 = cw.cw_propagate(state_drift, N_CHIEF, 2.0 * PERIOD)
        # computed anchor: y(T) = -37699.11 m, y(2T) = -75398.22 m
        self.assertAlmostEqual(s1[1], -37699.11, delta=0.05)
        self.assertAlmostEqual(s2[1], -75398.22, delta=0.1)
        self.assertGreater(abs(s1[1]), 1.0e4)  # large along-track drift

    def test_invalid_state_raises(self):
        bad = list(STATE_BOUNDED)
        bad[0] = float("nan")
        with self.assertRaises(ValueError):
            cw.cw_propagate(bad, N_CHIEF, PERIOD)
        with self.assertRaises(ValueError):
            cw.cw_propagate([1.0, 2.0, 3.0], N_CHIEF, PERIOD)

    def test_negative_tau_propagate_raises(self):
        with self.assertRaises(ValueError):
            cw.cw_propagate(STATE_BOUNDED, N_CHIEF, -5.0)


class TestBoundedCondition(unittest.TestCase):
    def test_bounded_state_flagged(self):
        req, flag = cw.bounded_orbit_condition(STATE_BOUNDED, N_CHIEF)
        self.assertTrue(flag)
        self.assertAlmostEqual(req, -2.0 * N_CHIEF * X0, places=9)

    def test_violated_state_flagged_false(self):
        state_drift = [X0, 0.0, Z0, 0.0, 0.0, 0.0]
        _, flag = cw.bounded_orbit_condition(state_drift, N_CHIEF)
        self.assertFalse(flag)

    def test_zero_radial_offset_needs_zero_y_dot(self):
        req, flag = cw.bounded_orbit_condition([0.0, 0.0, Z0, 0.0, 0.0, 0.0], N_CHIEF)
        self.assertTrue(flag)
        self.assertAlmostEqual(req, 0.0, places=12)

    def test_rejects_nonpositive_n(self):
        with self.assertRaises(ValueError):
            cw.bounded_orbit_condition(STATE_BOUNDED, 0.0)


class TestTargeting(unittest.TestCase):
    def test_half_orbit_total_dv_anchor(self):
        dv0, dvf, v0p, vfm, tot = cw.cw_targeting(
            STATE_TARGET_INPLANE, TARGET_ORIGIN, N_CHIEF, PERIOD / 2.0
        )
        # computed anchor: total 1.85735 m/s, order n*|r| ~ 1.11 m/s per km
        self.assertAlmostEqual(tot, 1.85735, delta=1e-3)
        self.assertAlmostEqual(dv0[0], -0.65197, delta=1e-3)
        self.assertAlmostEqual(dv0[1], 0.27670, delta=1e-3)
        self.assertAlmostEqual(dvf[0], -0.65197, delta=1e-3)
        self.assertAlmostEqual(dvf[1], -0.27670, delta=1e-3)
        self.assertAlmostEqual(dv0[2], 0.0, places=9)
        self.assertAlmostEqual(dvf[2], 0.0, places=9)

    def test_half_orbit_dv_order_n_r(self):
        dv0, dvf, _, _, tot = cw.cw_targeting(
            STATE_TARGET_INPLANE, TARGET_ORIGIN, N_CHIEF, PERIOD / 2.0
        )
        per_km = N_CHIEF * X0  # ~1.107 m/s per km radial offset
        self.assertGreater(tot, 0.5 * per_km)
        self.assertLess(tot, 3.0 * per_km)

    def test_one_orbit_targeting_singular_raises(self):
        with self.assertRaises(ValueError):
            cw.cw_targeting(STATE_TARGET_INPLANE, TARGET_ORIGIN, N_CHIEF, PERIOD)

    def test_half_orbit_cross_track_nulling_raises(self):
        with self.assertRaises(ValueError):
            cw.cw_targeting(STATE_BOUNDED, TARGET_ORIGIN, N_CHIEF, PERIOD / 2.0)

    def test_quarter_orbit_3d_targeting_finite(self):
        dv0, dvf, _, _, tot = cw.cw_targeting(STATE_BOUNDED, TARGET_ORIGIN, N_CHIEF, PERIOD / 4.0)
        for c in dv0 + dvf:
            self.assertTrue(math.isfinite(c))
        self.assertGreater(tot, 0.0)

    def test_targeting_short_time_needs_impulse(self):
        _, _, _, _, tot = cw.cw_targeting(
            STATE_TARGET_INPLANE, TARGET_ORIGIN, N_CHIEF, PERIOD / 20.0
        )
        self.assertGreater(tot, 1.0)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            cw.cw_targeting(STATE_TARGET_INPLANE, TARGET_ORIGIN, 0.0, PERIOD / 2.0)
        with self.assertRaises(ValueError):
            cw.cw_targeting(STATE_TARGET_INPLANE, TARGET_ORIGIN, N_CHIEF, 0.0)
        bad = list(STATE_TARGET_INPLANE)
        bad[3] = float("inf")
        with self.assertRaises(ValueError):
            cw.cw_targeting(bad, TARGET_ORIGIN, N_CHIEF, PERIOD / 2.0)


class TestGeometryCheck(unittest.TestCase):
    def test_ok_verdict_clear(self):
        self.assertEqual(cw.relative_orbit_geometry_check([0.0, 0.0, 300.0], 200.0), "ok")

    def test_close_approach_verdict(self):
        self.assertEqual(
            cw.relative_orbit_geometry_check([0.0, 0.0, 100.0], 200.0), "close-approach"
        )

    def test_rejects_bad_min_separation(self):
        with self.assertRaises(ValueError):
            cw.relative_orbit_geometry_check([1.0, 0.0, 0.0], 0.0)

    def test_rejects_short_vector(self):
        with self.assertRaises(ValueError):
            cw.relative_orbit_geometry_check([1.0, 2.0], 5.0)

    def test_rejects_nonfinite_vector(self):
        with self.assertRaises(ValueError):
            cw.relative_orbit_geometry_check([float("nan"), 0.0, 0.0], 5.0)


if __name__ == "__main__":
    unittest.main(verbosity=1)

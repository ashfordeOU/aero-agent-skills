#!/usr/bin/env python3
"""Deterministic contract test for the CMG cluster logic (stdlib only).

Runs offline: python3 test_control_moment_gyro.py -> exit 0.

Covers the worked example (single CMG 50 N m s at 1 rad/s gives 50 N m,
the 4-CMG pyramid at skew 53.13 deg with the steering law for a 20 N m
roll command and its achieved torque, the momentum envelope against the
100 N m s design slew momentum), the geometry conventions, the
Jacobian finite-difference identity, the pseudoinverse steering law
with the null-space term, the singularity measure and verdict bands,
the gimbal rate clip with the saturation flag, and ValueError rejection
of every non-physical input class.
"""

import math
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import control_moment_gyro_logic as cmg


def _norm(v):
    return math.sqrt(sum(c * c for c in v))


def _dot(a, b):
    return sum(ai * bi for ai, bi in zip(a, b))


def _det3(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


class TestSingleCmg(unittest.TestCase):
    """Single CMG torque law and the amplification comparison."""

    def test_single_cmg_torque_worked(self):
        tau = cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, 50.0), 1.0)
        self.assertEqual(tau, (0.0, 50.0, 0.0))
        self.assertAlmostEqual(_norm(tau), 50.0, places=12)

    def test_single_cmg_torque_equation(self):
        # tau = -delta_dot * (g x h); reversing the rate reverses the
        # torque and doubling it doubles the magnitude.
        g = (0.0, 1.0, 0.0)
        h = (50.0, 0.0, 0.0)
        tau = cmg.cmg_torque(g, h, 2.0)
        expected = (-2.0 * (g[1] * h[2] - g[2] * h[1]),
                    -2.0 * (g[2] * h[0] - g[0] * h[2]),
                    -2.0 * (g[0] * h[1] - g[1] * h[0]))
        for got, want in zip(tau, expected):
            self.assertAlmostEqual(got, want, places=12)
        tau_neg = cmg.cmg_torque(g, h, -2.0)
        for got, want in zip(tau_neg, (-c for c in tau)):
            self.assertAlmostEqual(got, want, places=12)
        tau1 = cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 25.0, 0.0), 1.0)
        tau2 = cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 25.0, 0.0), 2.0)
        self.assertAlmostEqual(_norm(tau2), 2.0 * _norm(tau1), places=12)

    def test_torque_amplification_contract(self):
        # CMG 50 N m s at 1 rad/s against a 0.5 kg m^2 wheel at 2 rad/s^2
        # (equal 50 N m s momentum): factor 50. Non-positive inputs and
        # non-finite values are rejected.
        self.assertAlmostEqual(cmg.torque_amplification(50.0, 1.0, 0.5, 2.0),
                               50.0, places=12)
        bad = [(0.0, 1.0, 0.5, 2.0), (50.0, -1.0, 0.5, 2.0),
               (50.0, 1.0, 0.0, 2.0), (50.0, 1.0, 0.5, -2.0),
               (float("nan"), 1.0, 0.5, 2.0), (50.0, 1.0, 0.5, float("inf"))]
        for args in bad:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    cmg.torque_amplification(*args)


class TestPyramidGeometry(unittest.TestCase):
    """Pyramid cluster geometry conventions."""

    def setUp(self):
        self.geom = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 4)

    def test_geometry_units_and_orthogonality(self):
        g_axes, h_dirs = self.geom
        self.assertEqual(len(g_axes), 4)
        self.assertEqual(len(h_dirs), 4)
        for g, h0 in zip(g_axes, h_dirs):
            self.assertAlmostEqual(_norm(g), 1.0, places=12)
            self.assertAlmostEqual(_norm(h0), 1.0, places=12)
            self.assertAlmostEqual(_dot(g, h0), 0.0, places=12)

    def test_geometry_elevation_and_plane(self):
        # Gimbal axes sit at the skew angle above the base plane (the
        # 3-4-5 triangle: cos beta = 3/5, sin beta = 4/5) and the
        # zero-angle momentum directions lie in the base plane.
        g_axes, h_dirs = self.geom
        sin_beta = math.sin(cmg.PYRAMID_SKEW_RADIANS)
        cos_beta = math.cos(cmg.PYRAMID_SKEW_RADIANS)
        self.assertAlmostEqual(sin_beta, 0.8, places=12)
        self.assertAlmostEqual(cos_beta, 0.6, places=12)
        for g, h0 in zip(g_axes, h_dirs):
            self.assertAlmostEqual(g[2], sin_beta, places=12)
            self.assertAlmostEqual(h0[2], 0.0, places=12)

    def test_geometry_four_unit_symmetry(self):
        g_axes, h_dirs = self.geom
        # Radial momentum directions cancel pairwise at zero angle.
        self.assertAlmostEqual(sum(h[0] for h in h_dirs), 0.0, places=12)
        self.assertAlmostEqual(sum(h[1] for h in h_dirs), 0.0, places=12)
        # Gimbal axes cancel in the plane and add along the normal.
        self.assertAlmostEqual(sum(g[0] for g in g_axes), 0.0, places=12)
        self.assertAlmostEqual(sum(g[1] for g in g_axes), 0.0, places=12)
        self.assertAlmostEqual(sum(g[2] for g in g_axes),
                               4.0 * math.sin(cmg.PYRAMID_SKEW_RADIANS),
                               places=12)

    def test_geometry_three_units_and_validation(self):
        g_axes, h_dirs = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 3)
        self.assertEqual(len(g_axes), 3)
        for g, h0 in zip(g_axes, h_dirs):
            self.assertAlmostEqual(_norm(g), 1.0, places=12)
            self.assertAlmostEqual(_dot(g, h0), 0.0, places=12)
        self.assertAlmostEqual(sum(h[0] for h in h_dirs), 0.0, places=12)
        self.assertAlmostEqual(sum(h[1] for h in h_dirs), 0.0, places=12)
        for n in (2, 1, 0, -4):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, n)
        for skew in (0.0, math.pi / 2.0, -0.5, 2.0, float("nan"),
                     float("inf")):
            with self.subTest(skew=skew):
                with self.assertRaises(ValueError):
                    cmg.pyramid_geometry(skew, 4)


class TestClusterMomentumAndEnvelope(unittest.TestCase):
    """Cluster momentum and the momentum envelope."""

    def setUp(self):
        self.geom = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 4)

    def test_cluster_momentum_zero_state(self):
        h = cmg.cluster_momentum((0.0, 0.0, 0.0, 0.0), self.geom)
        for c in h:
            self.assertAlmostEqual(c, 0.0, places=9)

    def test_cluster_momentum_uniform_tilt(self):
        # All four units tilted to the axial extremum: momentum is
        # purely axial with magnitude 4 * h0 * cos(beta) = 120 N m s;
        # the +pi/2 and -pi/2 states are exact mirrors.
        up = cmg.cluster_momentum((-math.pi / 2.0,) * 4, self.geom)
        down = cmg.cluster_momentum((math.pi / 2.0,) * 4, self.geom)
        self.assertAlmostEqual(up[0], 0.0, places=9)
        self.assertAlmostEqual(up[1], 0.0, places=9)
        self.assertAlmostEqual(up[2], 120.0, places=9)
        self.assertAlmostEqual(_norm(up), 120.0, places=9)
        self.assertAlmostEqual(_norm(down), 120.0, places=9)
        for a, b in zip(up, down):
            self.assertAlmostEqual(a, -b, places=12)

    def test_cluster_momentum_validation(self):
        h = cmg.cluster_momentum((0.4, 0.1, -0.3, 0.2), self.geom)
        self.assertAlmostEqual(_norm(h), 30.5893, places=3)
        with self.assertRaises(ValueError):
            cmg.cluster_momentum((0.0, 0.0, 0.0), self.geom)
        with self.assertRaises(ValueError):
            cmg.cluster_momentum((float("nan"), 0.0, 0.0, 0.0), self.geom)
        with self.assertRaises(ValueError):
            cmg.cluster_momentum((0.0, 0.0, 0.0, float("inf")), self.geom)

    def test_momentum_envelope_design_check(self):
        # The envelope must cover the 100 N m s agile slew requirement
        # and the attained 120 N m s uniform state; four units of 50
        # N m s can never exceed 200 N m s.
        env = cmg.momentum_envelope(self.geom, 12)
        self.assertGreaterEqual(env, cmg.DESIGN_SLEW_MOMENTUM_NMS - 1e-9)
        self.assertGreaterEqual(env, 120.0 - 1e-9)
        self.assertLessEqual(env, 200.0 * (1.0 + 1e-12))
        self.assertGreater(env, 150.0)
        for grid in (1, 0, -2):
            with self.subTest(grid=grid):
                with self.assertRaises(ValueError):
                    cmg.momentum_envelope(self.geom, grid)


class TestJacobianAndSingularity(unittest.TestCase):
    """Jacobian, singularity measure and verdict bands."""

    def setUp(self):
        self.geom = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 4)
        self.angles = (0.4, 0.1, -0.3, 0.2)

    def test_jacobian_shape_and_finite_difference(self):
        # J has one column per unit and |d h_cluster / d delta . v|
        # matches |J v| for a small step.
        jac = cmg.jacobian(self.angles, self.geom)
        self.assertEqual(len(jac), 4)
        for col in jac:
            self.assertEqual(len(col), 3)
        step = (0.01, -0.02, 0.015, -0.005)
        eps = 1e-6
        fwd = cmg.cluster_momentum(
            tuple(a + eps * s for a, s in zip(self.angles, step)), self.geom)
        back = cmg.cluster_momentum(
            tuple(a - eps * s for a, s in zip(self.angles, step)), self.geom)
        diff_mag = _norm(tuple((f - b) / (2.0 * eps)
                               for f, b in zip(fwd, back)))
        jv = tuple(sum(col[r] * step[i] for i, col in enumerate(jac))
                   for r in range(3))
        self.assertAlmostEqual(diff_mag, _norm(jv), delta=1e-3)

    def test_singularity_measure_matches_determinant(self):
        # S equals det(J J^T) recomputed by hand from the columns.
        s = cmg.singularity_measure(self.angles, self.geom)
        jac = cmg.jacobian(self.angles, self.geom)
        gram = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        for col in jac:
            for r in range(3):
                for c in range(3):
                    gram[r][c] += col[r] * col[c]
        self.assertAlmostEqual(s, _det3(gram), places=6)

    def test_singularity_measure_worked_nominal(self):
        s = cmg.singularity_measure(self.angles, self.geom)
        self.assertAlmostEqual(s / 3.290303e10, 1.0, delta=1e-6)
        self.assertGreater(s, cmg.SINGULARITY_THRESHOLD)

    def test_singularity_measure_extremes(self):
        # Uniform tilt state: all momenta parallel, det(J J^T) ~ 0.
        # Near the extremum the measure still sits above the floor.
        s_sing = cmg.singularity_measure((math.pi / 2.0,) * 4, self.geom)
        self.assertLess(s_sing, cmg.SINGULAR_DET_TOL)
        s_near = cmg.singularity_measure(
            tuple(math.pi / 2.0 - 0.02 for _ in range(4)), self.geom)
        self.assertAlmostEqual(s_near / 3.598484e7, 1.0, delta=1e-6)
        self.assertLess(s_near, cmg.SINGULARITY_THRESHOLD)
        self.assertGreater(s_near, cmg.SINGULAR_DET_TOL)

    def test_singularity_verdict_bands_and_validation(self):
        self.assertEqual(cmg.singularity_verdict(5.0e9, 1.0e8), "nominal")
        self.assertEqual(cmg.singularity_verdict(3.6e7, 1.0e8),
                         "near singularity")
        self.assertEqual(cmg.singularity_verdict(1.0e-6, 1.0e8), "singular")
        self.assertEqual(cmg.singularity_verdict(-5.0, 1.0e8), "singular")
        self.assertEqual(cmg.singularity_verdict(0.0, 1.0e8), "singular")
        for s, thr in ((float("nan"), 1.0e8), (1.0, 0.0), (1.0, -1.0),
                       (1.0, float("inf"))):
            with self.subTest(s=s, thr=thr):
                with self.assertRaises(ValueError):
                    cmg.singularity_verdict(s, thr)


class TestSteeringLaw(unittest.TestCase):
    """Pseudoinverse steering with the null-space term."""

    def setUp(self):
        self.geom = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 4)
        self.angles = (0.4, 0.1, -0.3, 0.2)
        self.tau = (20.0, 0.0, 0.0)

    def _jac_times(self, vec):
        jac = cmg.jacobian(self.angles, self.geom)
        return tuple(sum(col[r] * vec[i] for i, col in enumerate(jac))
                     for r in range(3))

    def test_steering_worked_rates_and_torque(self):
        rates = cmg.steering_law(self.angles, self.tau, self.geom)
        expected = (0.123865, 0.147094, 0.024835, -0.289952)
        for got, want in zip(rates, expected):
            self.assertAlmostEqual(got, want, delta=1e-5)
        achieved = self._jac_times(rates)
        for got, want in zip(achieved, self.tau):
            self.assertAlmostEqual(got, want, places=9)

    def test_steering_null_space_term(self):
        with_null = cmg.steering_law(self.angles, self.tau, self.geom)
        without = cmg.steering_law(self.angles, self.tau, self.geom,
                                   null_gain=0.0)
        self.assertNotAlmostEqual(_norm(with_null), _norm(without),
                                  places=9)
        # The null term is annihilated by J, so both achieve the command.
        jac = cmg.jacobian(self.angles, self.geom)
        diff = tuple(w - o for w, o in zip(with_null, without))
        jdiff = tuple(sum(col[r] * diff[i] for i, col in enumerate(jac))
                      for r in range(3))
        for c in jdiff:
            self.assertAlmostEqual(c, 0.0, places=9)
        # A zero command leaves pure internal null motion only.
        rates_zero = cmg.steering_law(self.angles, (0.0, 0.0, 0.0),
                                      self.geom)
        self.assertAlmostEqual(_norm(rates_zero), 0.047748, delta=1e-5)
        for c in self._jac_times(rates_zero):
            self.assertAlmostEqual(c, 0.0, places=9)

    def test_steering_error_paths(self):
        # Singular states, mismatched angle counts and non-finite
        # inputs all raise ValueError.
        with self.assertRaises(ValueError):
            cmg.steering_law((math.pi / 2.0,) * 4, self.tau, self.geom)
        with self.assertRaises(ValueError):
            cmg.steering_law((0.4, 0.1, -0.3), self.tau, self.geom)
        with self.assertRaises(ValueError):
            cmg.steering_law(self.angles, (float("nan"), 0.0, 0.0),
                             self.geom)
        with self.assertRaises(ValueError):
            cmg.steering_law((0.4, 0.1, -0.3, float("inf")), self.tau,
                             self.geom)

    def test_three_unit_cluster_steering(self):
        geom3 = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 3)
        angles3 = (0.2, -0.3, 0.4)
        rates = cmg.steering_law(angles3, (10.0, 0.0, 0.0), geom3)
        jac = cmg.jacobian(angles3, geom3)
        achieved = tuple(sum(col[r] * rates[i] for i, col in enumerate(jac))
                         for r in range(3))
        for got, want in zip(achieved, (10.0, 0.0, 0.0)):
            self.assertAlmostEqual(got, want, places=9)


class TestClusterSummary(unittest.TestCase):
    """Full cluster summary: rates, achieved torque, verdict, flags."""

    def setUp(self):
        self.geom = cmg.pyramid_geometry(cmg.PYRAMID_SKEW_RADIANS, 4)
        self.angles = (0.4, 0.1, -0.3, 0.2)

    def test_summary_nominal_worked(self):
        summary = cmg.cmg_cluster_summary(self.angles, (20.0, 0.0, 0.0),
                                          self.geom)
        self.assertEqual(
            set(summary.keys()),
            {"gimbal_rates", "achieved_torque", "singularity",
             "saturated", "margin", "s_measure"})
        self.assertEqual(summary["singularity"], "nominal")
        self.assertFalse(summary["saturated"])
        for got, want in zip(summary["achieved_torque"], (20.0, 0.0, 0.0)):
            self.assertAlmostEqual(got, want, places=9)
        self.assertAlmostEqual(summary["margin"], 329.0303, delta=1e-3)
        for rate in summary["gimbal_rates"]:
            self.assertLessEqual(abs(rate), cmg.MAX_GIMBAL_RATE_RAD_S)

    def test_summary_saturation_clip(self):
        summary = cmg.cmg_cluster_summary(self.angles, (20.0, 0.0, 0.0),
                                          self.geom, max_gimbal_rate=0.1)
        self.assertTrue(summary["saturated"])
        self.assertEqual(summary["singularity"], "nominal")
        for rate in summary["gimbal_rates"]:
            self.assertLessEqual(abs(rate), 0.1 + 1e-12)
        # Clipped torque authority falls short of the 20 N m command.
        self.assertLess(_norm(summary["achieved_torque"]), 20.0 * 0.9)

    def test_summary_near_singularity_state(self):
        angles_near = tuple(math.pi / 2.0 - 0.02 for _ in range(4))
        summary = cmg.cmg_cluster_summary(angles_near, (20.0, 0.0, 0.0),
                                          self.geom)
        self.assertEqual(summary["singularity"], "near singularity")
        self.assertLess(summary["margin"], 1.0)
        self.assertFalse(summary["saturated"])
        for got, want in zip(summary["achieved_torque"], (20.0, 0.0, 0.0)):
            self.assertAlmostEqual(got, want, places=9)

    def test_summary_validation(self):
        with self.assertRaises(ValueError):
            cmg.cmg_cluster_summary(self.angles, (float("nan"), 0.0, 0.0),
                                    self.geom)
        with self.assertRaises(ValueError):
            cmg.cmg_cluster_summary(self.angles, (20.0, 0.0, 0.0), self.geom,
                                    max_gimbal_rate=0.0)
        with self.assertRaises(ValueError):
            cmg.cmg_cluster_summary((math.pi / 2.0,) * 4, (20.0, 0.0, 0.0),
                                    self.geom)


class TestSingleCmgValidation(unittest.TestCase):
    """ValueError rejection of non-physical single-CMG inputs."""

    def test_zero_or_non_finite_inputs_raise(self):
        with self.assertRaises(ValueError):
            cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0)
        with self.assertRaises(ValueError):
            cmg.cmg_torque((float("nan"), 0.0, 0.0), (0.0, 0.0, 50.0), 1.0)
        with self.assertRaises(ValueError):
            cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, float("inf")), 1.0)
        with self.assertRaises(ValueError):
            cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, 50.0), float("nan"))

    def test_gimbal_rate_limit_path(self):
        # A rate above an explicit limit raises; inside the limit the
        # same call is accepted, and bad limits are rejected.
        with self.assertRaises(ValueError):
            cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, 50.0), 3.0,
                           max_gimbal_rate=2.0)
        tau = cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, 50.0), 1.5,
                             max_gimbal_rate=2.0)
        self.assertAlmostEqual(_norm(tau), 75.0, places=12)
        for lim in (-1.0, float("nan")):
            with self.subTest(lim=lim):
                with self.assertRaises(ValueError):
                    cmg.cmg_torque((1.0, 0.0, 0.0), (0.0, 0.0, 50.0), 1.0,
                                   max_gimbal_rate=lim)


class TestModuleConstants(unittest.TestCase):
    """Documented module constants used by the worked example."""

    def test_module_constants(self):
        self.assertEqual(cmg.CMG_MOMENTUM_NMS, 50.0)
        self.assertEqual(cmg.DESIGN_SLEW_MOMENTUM_NMS, 100.0)
        self.assertAlmostEqual(cmg.PYRAMID_SKEW_DEGREES, 53.13, places=2)
        self.assertAlmostEqual(
            cmg.PYRAMID_SKEW_RADIANS, math.atan(4.0 / 3.0), places=12)
        self.assertEqual(cmg.NULL_VECTOR, (0.5, -0.5, 0.5, -0.5))
        self.assertAlmostEqual(_norm(cmg.NULL_VECTOR), 1.0, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)

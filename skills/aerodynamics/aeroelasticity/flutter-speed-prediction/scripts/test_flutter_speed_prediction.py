#!/usr/bin/env python3
"""Gate 3 contract test: flutter speed prediction (classical wing flutter).

Exercises scripts/flutter_speed_prediction_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the binary
bending-torsion typical section with Theodorsen unsteady aerodynamics
(lift-deficiency function C(k) from Bessel J/Y series), the V-g method
(artificial structural damping g, flutter where a mode's g rises through
zero), frequency coalescence near the flutter boundary, and the flutter
margin against the design dive speed in the FAR 25.629 context
(referenced, not reproduced).

Reference case (classic typical section benchmark): mu = 20, a = -0.2,
x_theta = 0.2, r_theta^2 = 0.24, omega_h = 30 rad/s, omega_theta = 50
rad/s, b = 1 m, sea level air. The V-g sweep gives both modes damped
(g < 0) at low speed, the torsion-dominated branch rising through g = 0
at the flutter speed V_F = 88.85 m/s (reduced frequency k_F = 0.462,
omega_F = 41.07 rad/s; V_F/(b omega_theta) = 1.78, the classic typical
section result), the modal frequencies converging strongly near the
flutter boundary (coalescence check), and a static divergence limit at
about 141 m/s where the torsion frequency collapses to zero. With V_D =
80 m/s the flutter margin is 1.111, below the 1.15 clearance practice,
so the section is flagged; with V_D = 70 m/s the margin 1.269 is
acceptable.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flutter_speed_prediction_logic as fsp  # noqa: E402

MU = 20.0
X_THETA = 0.2
R_THETA_SQ = 0.24
OMEGA_H = 30.0
OMEGA_THETA = 50.0
A = -0.2
B = 1.0


class BesselTest(unittest.TestCase):
    def test_known_values(self):
        # Abramowitz and Stegun 9.1.10-9.1.11 reference values
        self.assertAlmostEqual(fsp.bessel_j0(1.0), 0.7651976866, delta=1e-7)
        self.assertAlmostEqual(fsp.bessel_j1(1.0), 0.4400505857, delta=1e-7)
        self.assertAlmostEqual(fsp.bessel_y0(1.0), 0.0882569642, delta=1e-7)
        self.assertAlmostEqual(fsp.bessel_y1(1.0), -0.7812128213, delta=1e-7)
        self.assertAlmostEqual(fsp.bessel_y0(2.0), 0.5103756726, delta=1e-7)
        self.assertAlmostEqual(fsp.bessel_y1(2.0), -0.1070324315, delta=1e-7)


class TheodorsenCTest(unittest.TestCase):
    def test_published_values(self):
        # Theodorsen's tabulated values for the lift-deficiency function
        c01 = fsp.theodorsen_c(0.1)
        self.assertAlmostEqual(c01.real, 0.8319, delta=1e-3)
        self.assertAlmostEqual(c01.imag, -0.1723, delta=1e-3)
        c05 = fsp.theodorsen_c(0.5)
        self.assertAlmostEqual(c05.real, 0.5979, delta=1e-3)
        self.assertAlmostEqual(c05.imag, -0.1507, delta=1e-3)

    def test_limits(self):
        # C -> 1 as k -> 0 (steady flow), C -> 1/2 for high reduced frequency
        self.assertAlmostEqual(fsp.theodorsen_c(1e-6).real, 1.0, delta=1e-4)
        self.assertAlmostEqual(fsp.theodorsen_c(10.0).real, 0.5, delta=1e-2)

    def test_magnitude_never_exceeds_one(self):
        for k in (0.01, 0.1, 0.3, 0.6, 1.0, 2.0, 5.0):
            self.assertLessEqual(abs(fsp.theodorsen_c(k)), 1.0)

    def test_imaginary_part_negative(self):
        for k in (0.01, 0.1, 0.5, 1.0, 5.0):
            self.assertLess(fsp.theodorsen_c(k).imag, 0.0)

    def test_invalid_k_raises(self):
        with self.assertRaises(ValueError):
            fsp.theodorsen_c(0.0)
        with self.assertRaises(ValueError):
            fsp.theodorsen_c(-1.0)


class VgModesTest(unittest.TestCase):
    def test_both_modes_stable_at_low_speed(self):
        # At low speed (high reduced frequency) both modes are damped:
        # negative artificial damping g means the aero adds damping.
        modes = fsp.vg_modes(MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA,
                             A, B, 4.0)
        self.assertEqual(len(modes), 2)
        for m in modes:
            self.assertLess(m["g"], 0.0)
            self.assertGreater(m["omega"], 0.0)
            self.assertGreater(m["v"], 0.0)

    def test_frequencies_near_uncoupled_values_at_high_k(self):
        # At k = 10 the coupling is weak: the modes sit near the uncoupled
        # bending and torsion frequencies, raised by the added inertia.
        modes = fsp.vg_modes(MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA,
                             A, B, 10.0)
        self.assertEqual(len(modes), 2)
        omegas = sorted(m["omega"] for m in modes)
        self.assertTrue(28.0 < omegas[0] < 32.0, omegas)
        self.assertTrue(45.0 < omegas[1] < 60.0, omegas)

    def test_torsion_damping_rises_with_speed(self):
        # The torsion-dominated branch (higher frequency) rises through
        # g = 0 between k = 0.5 and k = 0.4 for the benchmark case.
        g_hi_k = max(m["g"] for m in fsp.vg_modes(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.5))
        g_lo_k = max(m["g"] for m in fsp.vg_modes(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.4))
        self.assertLess(g_hi_k, 0.0)
        self.assertGreater(g_lo_k, 0.0)

    def test_negative_damping_edge(self):
        # Explicit edge: at low speed the required artificial damping is
        # negative for both modes (aerodynamic damping is stabilizing).
        modes = fsp.vg_modes(MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA,
                             A, B, 1.0)
        for m in modes:
            self.assertLess(m["g"], 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fsp.vg_modes(-1.0, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 1.0)
        with self.assertRaises(ValueError):
            fsp.vg_modes(MU, -0.1, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 1.0)
        with self.assertRaises(ValueError):
            fsp.vg_modes(MU, X_THETA, -0.1, OMEGA_H, OMEGA_THETA, A, B, 1.0)
        with self.assertRaises(ValueError):
            fsp.vg_modes(MU, X_THETA, R_THETA_SQ, 0.0, OMEGA_THETA, A, B, 1.0)
        with self.assertRaises(ValueError):
            fsp.vg_modes(MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.0)
        with self.assertRaises(ValueError):
            fsp.vg_modes(MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, "x", B, 1.0)


class VgDampingCrossingTest(unittest.TestCase):
    def test_sweep_shape(self):
        ks = [4.0, 2.0, 1.0, 0.5, 0.4]
        sweep = fsp.vg_damping_crossing(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, ks)
        self.assertEqual(len(sweep), len(ks))
        for k, modes in sweep:
            self.assertEqual(k in ks, True)
            self.assertGreaterEqual(len(modes), 1)

    def test_sweep_torsion_g_crosses_zero(self):
        # The g values of the torsion-dominated branch cross zero as the
        # reduced frequency drops (airspeed rises).
        sweep = fsp.vg_damping_crossing(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B,
            [1.0, 0.5, 0.45, 0.4])
        torsion_g = []
        for _, modes in sweep:
            torsion_g.append(max(m["g"] for m in modes))
        self.assertLess(torsion_g[0], 0.0)
        self.assertGreater(torsion_g[-1], 0.0)
        # the crossing is bracketed by the 0.5 and 0.45 stations
        self.assertLess(torsion_g[1], 0.0)
        self.assertGreater(torsion_g[2], 0.0)


class FlutterSpeedBinaryTest(unittest.TestCase):
    def test_benchmark_flutter_speed(self):
        result = fsp.flutter_speed_binary(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.05, 4.0)
        self.assertIsNotNone(result)
        # classic typical section result: V_F = 88.85 m/s at k_F = 0.462
        self.assertTrue(85.0 <= result["flutter_speed"] <= 93.0,
                        result["flutter_speed"])
        self.assertTrue(39.0 <= result["flutter_frequency"] <= 43.0,
                        result["flutter_frequency"])
        self.assertTrue(0.44 <= result["reduced_frequency"] <= 0.48,
                        result["reduced_frequency"])
        self.assertLess(abs(result["flutter_g"]), 1e-6)
        self.assertEqual(result["critical_mode"], "torsion")
        # normalized classic values
        self.assertTrue(1.70 <= result["flutter_speed"] / (B * OMEGA_THETA) <= 1.85)
        self.assertTrue(0.78 <= result["flutter_frequency"] / OMEGA_THETA <= 0.86)
        # the other (bending-dominated) mode stays near its uncoupled value
        self.assertTrue(28.0 <= result["other_frequency"] <= 32.0,
                        result["other_frequency"])

    def test_no_crossing_within_range(self):
        # Restrict the scan to k >= 0.8 (speeds below the crossing at
        # k = 0.462): no flutter onset is found inside the range.
        result = fsp.flutter_speed_binary(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.8, 4.0)
        self.assertIsNone(result)

    def test_rigid_case_flutters_very_fast(self):
        # Stiffening the section (omega_h = omega_theta = 1e4 rad/s)
        # pushes the flutter speed to extreme values: the aeroelastic
        # interaction is negligible at realistic airspeeds.
        result = fsp.flutter_speed_binary(
            MU, X_THETA, R_THETA_SQ, 1e4, 1e4, A, B, 0.05, 4.0)
        self.assertIsNotNone(result)
        self.assertGreater(result["flutter_speed"], 5000.0)

    def test_deterministic(self):
        r1 = fsp.flutter_speed_binary(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.05, 4.0)
        r2 = fsp.flutter_speed_binary(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.05, 4.0)
        self.assertEqual(r1["flutter_speed"], r2["flutter_speed"])

    def test_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            fsp.flutter_speed_binary(
                MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 2.0, 1.0)
        with self.assertRaises(ValueError):
            fsp.flutter_speed_binary(
                MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.0, 4.0)
        with self.assertRaises(ValueError):
            fsp.flutter_speed_binary(
                MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.05, 4.0,
                n_scan=5)


class FrequencyCoalescenceTest(unittest.TestCase):
    def test_benchmark_coalescence(self):
        result = fsp.frequency_coalescence_check(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.05, 4.0)
        self.assertIsNotNone(result)
        # the modal frequency gap shrinks to about a quarter of its
        # low-speed value as the flutter boundary is approached
        self.assertLess(result["min_gap"], 0.4 * result["low_speed_gap"])
        self.assertTrue(result["coalescing"])
        self.assertTrue(5.0 <= result["min_gap"] <= 12.0, result["min_gap"])
        # the coalescence station sits at or just above the flutter speed
        flutter = fsp.flutter_speed_binary(
            MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 0.05, 4.0)
        self.assertGreaterEqual(result["coalescence_speed"],
                                flutter["flutter_speed"] - 1.0)
        self.assertLess(result["coalescence_speed"], 110.0)

    def test_invalid_range_raises(self):
        with self.assertRaises(ValueError):
            fsp.frequency_coalescence_check(
                MU, X_THETA, R_THETA_SQ, OMEGA_H, OMEGA_THETA, A, B, 1.0, 4.0,
                n_scan=10)


class FlutterMarginTest(unittest.TestCase):
    FLUTTER = 88.8511  # benchmark flutter speed, m/s

    def test_margin_below_required_flags_risk(self):
        # V_D = 80 m/s: margin 1.111 < 1.15 -> not acceptable
        margin, ok = fsp.flutter_margin(self.FLUTTER, 80.0)
        self.assertAlmostEqual(margin, 1.1106, delta=1e-3)
        self.assertFalse(ok)

    def test_margin_above_required_acceptable(self):
        # V_D = 70 m/s: margin 1.269 >= 1.15 -> acceptable
        margin, ok = fsp.flutter_margin(self.FLUTTER, 70.0)
        self.assertAlmostEqual(margin, 1.2693, delta=1e-3)
        self.assertTrue(ok)

    def test_threshold_boundary(self):
        # exactly 1.15 is acceptable (>=)
        margin, ok = fsp.flutter_margin(self.FLUTTER, self.FLUTTER / 1.15)
        self.assertAlmostEqual(margin, 1.15, delta=1e-9)
        self.assertTrue(ok)
        _, ok_low = fsp.flutter_margin(self.FLUTTER, self.FLUTTER / 1.1499)
        self.assertFalse(ok_low)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fsp.flutter_margin(0.0, 80.0)
        with self.assertRaises(ValueError):
            fsp.flutter_margin(88.85, 0.0)
        with self.assertRaises(ValueError):
            fsp.flutter_margin(88.85, 80.0, required=0.9)


class FAR25ContextTest(unittest.TestCase):
    def test_reference_only_constants(self):
        # The clearance practice threshold is a name-level reference to
        # the airworthiness standard, not a reproduction of its text.
        self.assertAlmostEqual(fsp.FLUTTER_MARGIN_REQUIRED, 1.15, delta=1e-12)
        self.assertAlmostEqual(fsp.ISA_SEA_LEVEL_DENSITY, 1.225, delta=1e-12)


if __name__ == "__main__":
    unittest.main(verbosity=2)

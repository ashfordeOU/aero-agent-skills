#!/usr/bin/env python3
"""Gate 3 contract test: 2-DOF modal analysis logic.

Exercises scripts/modal_analysis_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - natural frequencies in
rad/s from det(K - w^2 M) = 0, frequencies in Hz, mode-shape ratios
phi2/phi1 per mode, resonance check of an excitation frequency
against the natural frequencies, and ValueError on invalid inputs.
Physically meaningful check: m1 = m2 = 1 kg, k1 = k2 = 1 N/m gives
the textbook roots w^2 = (3 +- sqrt(5)) / 2 (rad/s)^2, whose modes
move in phase at w1 and out of phase at w2.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import modal_analysis_logic as mod  # noqa: E402

PHI = (1.0 + math.sqrt(5.0)) / 2.0  # golden ratio, 1.6180339887...


class NaturalFrequenciesTest(unittest.TestCase):
    def test_textbook_two_dof_values(self):
        # m1 = m2 = 1 kg, k1 = k2 = 1 N/m: w^4 - 3 w^2 + 1 = 0.
        w = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(
            w[0], math.sqrt((3.0 - math.sqrt(5.0)) / 2.0), delta=1e-9
        )
        self.assertAlmostEqual(
            w[1], math.sqrt((3.0 + math.sqrt(5.0)) / 2.0), delta=1e-9
        )

    def test_decoupled_single_dof_limit(self):
        # k2 = 0 decouples the system: mass 1 on spring k1 gives
        # w = sqrt(k1/m1), mass 2 is free (rigid-body mode at w = 0).
        w = mod.natural_frequencies(4.0, 2.0, 100.0, 0.0)
        self.assertAlmostEqual(w[0], 0.0, delta=1e-9)
        self.assertAlmostEqual(w[1], 5.0, delta=1e-9)

    def test_stiffer_system_raises_frequencies(self):
        # Doubling both spring rates scales every frequency by sqrt(2).
        w_base = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        w_stiff = mod.natural_frequencies(1.0, 1.0, 2.0, 2.0)
        self.assertAlmostEqual(w_stiff[0], math.sqrt(2.0) * w_base[0], delta=1e-9)
        self.assertAlmostEqual(w_stiff[1], math.sqrt(2.0) * w_base[1], delta=1e-9)

    def test_frequencies_hz_divide_by_two_pi(self):
        hz = mod.frequencies_hz(1.0, 1.0, 1.0, 1.0)
        w = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(hz[0], w[0] / (2.0 * math.pi), delta=1e-9)
        self.assertAlmostEqual(hz[1], w[1] / (2.0 * math.pi), delta=1e-9)


class InvalidInputTest(unittest.TestCase):
    def test_nonpositive_mass_raises(self):
        for bad in (0.0, -1.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    mod.natural_frequencies(bad, 1.0, 1.0, 1.0)
                with self.assertRaises(ValueError):
                    mod.natural_frequencies(1.0, bad, 1.0, 1.0)
                with self.assertRaises(ValueError):
                    mod.frequencies_hz(bad, 1.0, 1.0, 1.0)
                with self.assertRaises(ValueError):
                    mod.mode_shapes(1.0, bad, 1.0, 1.0)

    def test_negative_spring_raises(self):
        for bad in (-0.5, -1.0):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    mod.natural_frequencies(1.0, 1.0, bad, 1.0)
                with self.assertRaises(ValueError):
                    mod.natural_frequencies(1.0, 1.0, 1.0, bad)

    def test_fully_unrestrained_system_raises(self):
        with self.assertRaises(ValueError):
            mod.natural_frequencies(1.0, 1.0, 0.0, 0.0)


class ModeShapesTest(unittest.TestCase):
    def test_textbook_mode_shape_ratios(self):
        # phi2/phi1 = (k1+k2 - m1 w^2) / k2: in phase at w1 (ratio
        # +1.618), out of phase at w2 (ratio -0.618).
        shapes = mod.mode_shapes(1.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(shapes[0][1], PHI, delta=1e-9)
        self.assertAlmostEqual(shapes[1][1], 1.0 - PHI, delta=1e-9)

    def test_modes_satisfy_eigenproblem(self):
        # Every mode shape must satisfy (K - w^2 M) phi = 0, i.e.
        # row 1: (k1+k2 - m1 w^2) phi1 - k2 phi2 = 0.
        w = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        for shape, wn in zip(mod.mode_shapes(1.0, 1.0, 1.0, 1.0), w):
            p1, p2 = shape
            self.assertAlmostEqual(
                (2.0 - wn * wn) * p1 - p2, 0.0, delta=1e-9
            )

    def test_decoupled_mode_shapes(self):
        # k2 = 0: the rigid-body mode is [0, 1] (free mass 2), the
        # elastic mode is [1, 0] (mass 1 alone on spring k1).
        shapes = mod.mode_shapes(4.0, 2.0, 100.0, 0.0)
        self.assertAlmostEqual(shapes[0][0], 0.0, delta=1e-9)
        self.assertAlmostEqual(shapes[0][1], 1.0, delta=1e-9)
        self.assertAlmostEqual(shapes[1][0], 1.0, delta=1e-9)
        self.assertAlmostEqual(shapes[1][1], 0.0, delta=1e-9)


class ResonanceCheckTest(unittest.TestCase):
    def test_excitation_inside_band_is_resonance(self):
        w = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        r = mod.resonance_check(0.65, w)  # 3.2% away from w1 = 0.618
        self.assertTrue(r["resonance"])
        self.assertAlmostEqual(r["nearest"], w[0], delta=1e-9)

    def test_excitation_far_from_band_is_not_resonance(self):
        w = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        r = mod.resonance_check(1.0, w)
        self.assertFalse(r["resonance"])
        self.assertAlmostEqual(r["nearest"], w[0], delta=1e-9)

    def test_tight_tolerance_excludes_near_excitation(self):
        w = mod.natural_frequencies(1.0, 1.0, 1.0, 1.0)
        r = mod.resonance_check(0.65, w, tol_frac=0.01)
        self.assertFalse(r["resonance"])

    def test_rigid_body_mode_does_not_resonate(self):
        # w = [0.0, 5.0]; wide band but the only near frequency is the
        # rigid-body zero, which must not flag resonance.
        r = mod.resonance_check(0.1, [0.0, 5.0], tol_frac=0.9)
        self.assertFalse(r["resonance"])
        self.assertAlmostEqual(r["nearest"], 0.0, delta=1e-9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mod.resonance_check(-1.0, [1.0])
        with self.assertRaises(ValueError):
            mod.resonance_check(1.0, [])
        with self.assertRaises(ValueError):
            mod.resonance_check(1.0, [1.0], tol_frac=0.0)
        with self.assertRaises(ValueError):
            mod.resonance_check(1.0, [1.0], tol_frac=1.5)
        with self.assertRaises(ValueError):
            mod.resonance_check(1.0, [-1.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)

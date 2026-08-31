#!/usr/bin/env python3
"""Gate 3 contract test: fatigue crack growth (LEFM, Paris law).

Exercises scripts/crack_growth_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3: mode I stress intensity
factor, Paris da/dN rate, crack growth per cycle, and cycles to grow;
invalid inputs raise ValueError.

UNITS CONVENTION (matches crack_growth_logic.py): sigma and dK in
MPa / MPa*sqrt(m), crack lengths in meters, Paris C in
(m/cycle)*(MPa*sqrt(m))^-m, da/dN in m/cycle. Example anchor:
C=1e-11, m=3, dK=20 MPa*sqrt(m) gives da/dN = 1e-11 * 20**3 =
8e-8 m/cycle; 1000 cycles extends the crack 8e-5 m; a 0.009 m crack
extension takes 112,500 cycles.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import crack_growth_logic as cg  # noqa: E402


class StressIntensityTest(unittest.TestCase):
    def test_anchor_sigma_100mpa_a_10mm(self):
        # Anchor: sigma=100 MPa, a=0.01 m, Y=1.12 -> ~19.85 MPa*sqrt(m).
        k = cg.stress_intensity(100, 0.01)
        self.assertAlmostEqual(
            k, 1.12 * 100 * math.sqrt(math.pi * 0.01), places=6
        )
        self.assertAlmostEqual(k, 19.85, delta=0.01)

    def test_linear_in_stress_and_sqrt_a(self):
        k1 = cg.stress_intensity(50, 0.01)
        k2 = cg.stress_intensity(100, 0.01)
        self.assertAlmostEqual(k1, 0.5 * k2)
        k3 = cg.stress_intensity(100, 0.04)
        self.assertAlmostEqual(k3, 2.0 * k2)

    def test_default_geometry_factor(self):
        self.assertEqual(cg.stress_intensity(100, 0.01, y=1.12),
                         cg.stress_intensity(100, 0.01))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cg.stress_intensity(0.0, 0.01)
        with self.assertRaises(ValueError):
            cg.stress_intensity(-100, 0.01)
        with self.assertRaises(ValueError):
            cg.stress_intensity(100, 0.0)
        with self.assertRaises(ValueError):
            cg.stress_intensity(100, -0.01)
        with self.assertRaises(ValueError):
            cg.stress_intensity(100, 0.01, y=0.0)
        with self.assertRaises(ValueError):
            cg.stress_intensity(100, 0.01, y=-1.12)


class ParisDadNTest(unittest.TestCase):
    def test_anchor_c1e11_m3_dk20mpa(self):
        # Anchor: C=1e-11 (m/cycle)(MPa*sqrt(m))^-3, m=3, dK=20
        # MPa*sqrt(m) -> da/dN = 1e-11 * 20**3 = 8e-8 m/cycle.
        self.assertAlmostEqual(
            cg.paris_dadN(1e-11, 3, 20), 1e-11 * (20) ** 3, places=15
        )
        self.assertAlmostEqual(cg.paris_dadN(1e-11, 3, 20), 8e-8, delta=1e-12)

    def test_exponent_scaling(self):
        # At dK=100 MPa*sqrt(m): m=2 -> 1e-11*1e4 = 1e-7 m/cycle;
        # m=4 -> 1e-11*1e8 = 1e-3 m/cycle (1e4 x the m=2 rate).
        self.assertAlmostEqual(cg.paris_dadN(1e-11, 2, 100), 1e-7)
        self.assertAlmostEqual(cg.paris_dadN(1e-11, 4, 100), 1e-3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cg.paris_dadN(0.0, 3, 20)
        with self.assertRaises(ValueError):
            cg.paris_dadN(-1e-11, 3, 20)
        with self.assertRaises(ValueError):
            cg.paris_dadN(1e-11, 3, 0.0)
        with self.assertRaises(ValueError):
            cg.paris_dadN(1e-11, 3, -20)


class CrackGrowthPerCycleTest(unittest.TestCase):
    def test_block_extension(self):
        # 1000 cycles at 8e-8 m/cycle -> 8e-5 m.
        self.assertAlmostEqual(cg.crack_growth_per_cycle(1e-11, 3, 20, 1000),
                               8e-5, delta=1e-9)

    def test_zero_cycles_no_growth(self):
        self.assertAlmostEqual(cg.crack_growth_per_cycle(1e-11, 3, 20, 0),
                               0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cg.crack_growth_per_cycle(0.0, 3, 20, 100)
        with self.assertRaises(ValueError):
            cg.crack_growth_per_cycle(1e-11, 3, 0.0, 100)
        with self.assertRaises(ValueError):
            cg.crack_growth_per_cycle(1e-11, 3, 20, -1)


class CyclesToGrowTest(unittest.TestCase):
    def test_constant_amplitude_cycles(self):
        # da = 0.009 m at 8e-8 m/cycle -> 112,500 cycles.
        self.assertAlmostEqual(
            cg.cycles_to_grow(1e-11, 3, 20, 0.001, 0.01), 112500, delta=1e-6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cg.cycles_to_grow(0.0, 3, 20, 0.001, 0.01)
        with self.assertRaises(ValueError):
            cg.cycles_to_grow(1e-11, 3, 0.0, 0.001, 0.01)
        with self.assertRaises(ValueError):
            cg.cycles_to_grow(1e-11, 3, 20, 0.01, 0.01)
        with self.assertRaises(ValueError):
            cg.cycles_to_grow(1e-11, 3, 20, 0.02, 0.01)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Gate 3 contract test: bird strike impact analysis (soft-body impact).

Exercises scripts/bird_strike_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3: impact kinetic energy,
specific energy, bird class mass conversion, damage severity and
penetration verdict against a component threshold, and residual
strength fraction after impact; invalid inputs raise ValueError.

UNITS CONVENTION (matches bird_strike_logic.py): mass in kg, velocity
in m/s, energy and threshold in joules. Example anchors: the 4 pound
bird (1.81 kg) at 250 m/s gives 0.5 * 1.81 * 250**2 = 56,562.5 J; the
8 pound bird (3.63 kg) at 250 m/s gives 113,437.5 J, twice the energy;
against a 60 kJ leading edge threshold the severity ratios are 0.94
(no-penetration) and 1.89 (penetration), and the residual strength
fraction after the 8 pound strike is about 0.05.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bird_strike_logic as bs  # noqa: E402


class BirdMassTest(unittest.TestCase):
    def test_4lb_bird(self):
        # 4 lb = 4 * 0.45359237 kg = 1.8144 kg (about 1.81 kg).
        self.assertAlmostEqual(bs.bird_mass_kg(4), 4 * 0.45359237, places=6)
        self.assertAlmostEqual(bs.bird_mass_kg(4), 1.81, delta=0.01)

    def test_8lb_bird(self):
        # 8 lb = 8 * 0.45359237 kg = 3.6287 kg (about 3.63 kg).
        self.assertAlmostEqual(bs.bird_mass_kg(8), 8 * 0.45359237, places=6)
        self.assertAlmostEqual(bs.bird_mass_kg(8), 3.63, delta=0.01)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bs.bird_mass_kg(0.0)
        with self.assertRaises(ValueError):
            bs.bird_mass_kg(-4)


class ImpactEnergyTest(unittest.TestCase):
    def test_anchor_4lb_at_250mps(self):
        # 4 lb bird (1.81 kg) at 250 m/s -> 56,562.5 J.
        self.assertAlmostEqual(
            bs.impact_energy(1.81, 250), 0.5 * 1.81 * 250 ** 2, places=6
        )
        self.assertAlmostEqual(bs.impact_energy(1.81, 250), 56562.5, delta=1e-9)

    def test_anchor_8lb_at_250mps(self):
        # 8 lb bird (3.63 kg) at 250 m/s -> 113,437.5 J.
        self.assertAlmostEqual(
            bs.impact_energy(3.63, 250), 0.5 * 3.63 * 250 ** 2, places=6
        )
        self.assertAlmostEqual(bs.impact_energy(3.63, 250), 113437.5, delta=1e-9)

    def test_linear_in_mass_exact(self):
        # The pound-derived masses are exactly 2:1, so the energy
        # doubles exactly at constant velocity.
        e4 = bs.impact_energy(bs.bird_mass_kg(4), 250)
        e8 = bs.impact_energy(bs.bird_mass_kg(8), 250)
        self.assertAlmostEqual(e8, 2.0 * e4, places=9)

    def test_quadratic_in_velocity(self):
        # Doubling the velocity quadruples the energy.
        e1 = bs.impact_energy(3.63, 100)
        e2 = bs.impact_energy(3.63, 200)
        self.assertAlmostEqual(e2, 4.0 * e1)

    def test_zero_velocity_zero_energy(self):
        self.assertAlmostEqual(bs.impact_energy(1.81, 0.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bs.impact_energy(0.0, 250)
        with self.assertRaises(ValueError):
            bs.impact_energy(-1.81, 250)
        with self.assertRaises(ValueError):
            bs.impact_energy(1.81, -250)


class SpecificEnergyTest(unittest.TestCase):
    def test_anchor_250mps(self):
        # 0.5 * 250**2 = 31,250 J/kg.
        self.assertAlmostEqual(bs.specific_energy(250), 31250.0, places=6)

    def test_zero_velocity_zero(self):
        self.assertAlmostEqual(bs.specific_energy(0.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bs.specific_energy(-250)


class DamageSeverityTest(unittest.TestCase):
    def test_anchor_4lb_vs_60kj(self):
        # 56,562.5 J / 60,000 J = 0.94: under the threshold.
        self.assertAlmostEqual(
            bs.damage_severity_ratio(56562.5, 60000), 56562.5 / 60000, places=6
        )
        self.assertAlmostEqual(bs.damage_severity_ratio(56562.5, 60000), 0.94, delta=0.01)

    def test_anchor_8lb_vs_60kj(self):
        # 113,437.5 J / 60,000 J = 1.89: over the threshold.
        self.assertAlmostEqual(bs.damage_severity_ratio(113437.5, 60000), 1.89, delta=0.01)

    def test_penetration_verdict(self):
        self.assertEqual(bs.penetration_verdict(56562.5, 60000), "no-penetration")
        self.assertEqual(bs.penetration_verdict(113437.5, 60000), "penetration")
        self.assertEqual(bs.penetration_verdict(60000.0, 60000.0), "penetration")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bs.damage_severity_ratio(-1.0, 60000)
        with self.assertRaises(ValueError):
            bs.damage_severity_ratio(100.0, 0.0)
        with self.assertRaises(ValueError):
            bs.damage_severity_ratio(100.0, -60000)
        with self.assertRaises(ValueError):
            bs.penetration_verdict(-1.0, 60000)
        with self.assertRaises(ValueError):
            bs.penetration_verdict(100.0, 0.0)


class ResidualStrengthTest(unittest.TestCase):
    def test_undamaged_full_strength(self):
        self.assertAlmostEqual(bs.residual_strength_fraction(0.0, 60000), 1.0)

    def test_strike_at_threshold_half_strength(self):
        # 1 - 0.5 * 60000 / 60000 = 0.5.
        self.assertAlmostEqual(
            bs.residual_strength_fraction(60000.0, 60000.0), 0.5, places=9
        )

    def test_anchor_8lb_after_strike(self):
        # 1 - 0.5 * 113437.5 / 60000 = 0.0547 (about 0.05).
        self.assertAlmostEqual(
            bs.residual_strength_fraction(113437.5, 60000), 0.0547, delta=1e-3
        )

    def test_twice_threshold_zero_strength(self):
        self.assertAlmostEqual(bs.residual_strength_fraction(120000.0, 60000.0), 0.0)
        self.assertAlmostEqual(bs.residual_strength_fraction(150000.0, 60000.0), 0.0)

    def test_monotonic_degradation(self):
        f0 = bs.residual_strength_fraction(10000.0, 60000.0)
        f1 = bs.residual_strength_fraction(30000.0, 60000.0)
        self.assertGreater(f0, f1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bs.residual_strength_fraction(-1.0, 60000)
        with self.assertRaises(ValueError):
            bs.residual_strength_fraction(100.0, 0.0)
        with self.assertRaises(ValueError):
            bs.residual_strength_fraction(100.0, -60000)


if __name__ == "__main__":
    unittest.main(verbosity=2)

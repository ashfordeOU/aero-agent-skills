#!/usr/bin/env python3
"""Gate 3 contract test: ISA standard atmosphere.

Exercises scripts/isa_atmosphere_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - temperature, pressure,
and density at altitude in the troposphere and lower stratosphere,
sea-level anchor values, and invalid-input handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import isa_atmosphere_logic as isa  # noqa: E402


class SeaLevelTest(unittest.TestCase):
    def test_sea_level_anchors(self):
        temp, press, dens = isa.isa_sea_level()
        self.assertAlmostEqual(temp, 288.15, places=4)
        self.assertAlmostEqual(press, 101325.0, places=1)
        self.assertAlmostEqual(dens, 1.225, delta=1e-3)


class TroposphereTest(unittest.TestCase):
    def test_temperature_lapse(self):
        t = isa.isa_temperature_k(11000.0)
        self.assertAlmostEqual(t, 216.65, places=4)

    def test_mid_troposphere(self):
        t = isa.isa_temperature_k(5000.0)
        self.assertAlmostEqual(t, 255.65, places=4)

    def test_pressure_monotone_decrease(self):
        p0 = isa.isa_pressure_pa(0.0)
        p5 = isa.isa_pressure_pa(5000.0)
        p11 = isa.isa_pressure_pa(11000.0)
        self.assertGreater(p0, p5)
        self.assertGreater(p5, p11)


class StratosphereTest(unittest.TestCase):
    def test_isothermal_layer(self):
        t11 = isa.isa_temperature_k(11000.0)
        t20 = isa.isa_temperature_k(20000.0)
        self.assertAlmostEqual(t20, t11, places=4)

    def test_pressure_continues_decreasing(self):
        p11 = isa.isa_pressure_pa(11000.0)
        p20 = isa.isa_pressure_pa(20000.0)
        self.assertGreater(p11, p20)


class DensityTest(unittest.TestCase):
    def test_density_at_altitude_below_sea_level(self):
        dens = isa.isa_density_kgm3(5000.0)
        self.assertLess(dens, 1.225)
        self.assertGreater(dens, 0.5)


class InvalidInputTest(unittest.TestCase):
    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            isa.isa_temperature_k(-1.0)

    def test_above_20km_raises(self):
        with self.assertRaises(ValueError):
            isa.isa_pressure_pa(20001.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

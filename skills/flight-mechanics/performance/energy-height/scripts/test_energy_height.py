#!/usr/bin/env python3
"""Gate 3 contract test: energy height and specific excess power.

Exercises scripts/energy_height_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (excess power from thrust,
drag, and speed; specific excess power Ps from the excess power over
the weight; kinetic height from the airspeed; energy height from the
altitude and airspeed; speed from a target energy height; zoom climb
gain; speed bleed for an altitude gain; altitude gain from a speed
bleed; invalid inputs raise ValueError).

Anchors:
- excess_power(120000, 90000, 80) = 2,400,000 W
- specific_excess_power(120000, 90000, 80, 600000) = 4.0 m/s
- kinetic_height(80) = 6400 / (2 * 9.80665) = 326.31 m
- energy_height(5000, 80) = 5326.31 m
- speed_from_energy_height(5326.31, 5000) = 80.0 m/s
- zoom_climb_gain(80) = 326.31 m
- speed_after_climb_bleed(100, 100) = sqrt(10000 - 2 * 9.80665 * 100)
- altitude_from_speed_bleed(100, 50) = 7500 / (2 * 9.80665) = 382.39 m
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import energy_height_logic as eh  # noqa: E402


class ExcessPowerTest(unittest.TestCase):
    def test_anchor_excess_power(self):
        self.assertAlmostEqual(eh.excess_power(120000, 90000, 80), 2400000.0)

    def test_zero_drag(self):
        self.assertAlmostEqual(eh.excess_power(50000, 0, 100), 5000000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eh.excess_power(-1, 90000, 80)
        with self.assertRaises(ValueError):
            eh.excess_power(120000, -1, 80)
        with self.assertRaises(ValueError):
            eh.excess_power(120000, 90000, 0)
        with self.assertRaises(ValueError):
            eh.excess_power(120000, 90000, -10)


class SpecificExcessPowerTest(unittest.TestCase):
    def test_anchor_ps(self):
        self.assertAlmostEqual(eh.specific_excess_power(120000, 90000, 80, 600000), 4.0)

    def test_heavier_aircraft_slower_energy_rate(self):
        # Same excess power over twice the weight: half the Ps.
        self.assertAlmostEqual(eh.specific_excess_power(120000, 90000, 80, 1200000), 2.0)

    def test_zero_excess_power(self):
        # Thrust equals drag: Ps is zero, no energy rate.
        self.assertAlmostEqual(eh.specific_excess_power(90000, 90000, 80, 600000), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eh.specific_excess_power(120000, 90000, 80, 0)
        with self.assertRaises(ValueError):
            eh.specific_excess_power(120000, 90000, 80, -600000)
        with self.assertRaises(ValueError):
            eh.specific_excess_power(120000, 90000, 0, 600000)


class KineticHeightTest(unittest.TestCase):
    def test_anchor_kinetic_height(self):
        self.assertAlmostEqual(eh.kinetic_height(80), 6400.0 / (2.0 * eh.G0), places=3)

    def test_zero_speed(self):
        self.assertAlmostEqual(eh.kinetic_height(0), 0.0)

    def test_invalid_speed_raises(self):
        with self.assertRaises(ValueError):
            eh.kinetic_height(-5)


class EnergyHeightTest(unittest.TestCase):
    def test_anchor_energy_height(self):
        self.assertAlmostEqual(eh.energy_height(5000, 80), 5000.0 + 6400.0 / (2.0 * eh.G0), places=3)

    def test_energy_height_is_sum(self):
        # Energy height equals altitude plus kinetic height.
        self.assertAlmostEqual(
            eh.energy_height(3000, 120), 3000.0 + eh.kinetic_height(120), places=3
        )

    def test_invalid_altitude_raises(self):
        with self.assertRaises(ValueError):
            eh.energy_height(-100, 80)


class SpeedFromEnergyHeightTest(unittest.TestCase):
    def test_anchor_round_trip(self):
        he = eh.energy_height(5000, 80)
        self.assertAlmostEqual(eh.speed_from_energy_height(he, 5000), 80.0, places=3)

    def test_zero_kinetic_energy(self):
        self.assertAlmostEqual(eh.speed_from_energy_height(5000, 5000), 0.0)

    def test_energy_height_below_altitude_raises(self):
        with self.assertRaises(ValueError):
            eh.speed_from_energy_height(4000, 5000)
        with self.assertRaises(ValueError):
            eh.speed_from_energy_height(5326.31, -10)


class ZoomClimbTest(unittest.TestCase):
    def test_anchor_zoom_gain(self):
        self.assertAlmostEqual(eh.zoom_climb_gain(80), 6400.0 / (2.0 * eh.G0), places=3)

    def test_zoom_gain_equals_kinetic_height(self):
        self.assertAlmostEqual(eh.zoom_climb_gain(150), eh.kinetic_height(150), places=6)

    def test_invalid_speed_raises(self):
        with self.assertRaises(ValueError):
            eh.zoom_climb_gain(-1)


class ClimbBleedTest(unittest.TestCase):
    def test_anchor_speed_after_bleed(self):
        # From 100 m/s, climbing 100 m: V2 = sqrt(10000 - 2g * 100).
        expected = (10000.0 - 2.0 * eh.G0 * 100.0) ** 0.5
        self.assertAlmostEqual(eh.speed_after_climb_bleed(100, 100), expected, places=6)

    def test_zero_climb_keeps_speed(self):
        self.assertAlmostEqual(eh.speed_after_climb_bleed(100, 0), 100.0)

    def test_insufficient_energy_raises(self):
        with self.assertRaises(ValueError):
            eh.speed_after_climb_bleed(10, 100)
        with self.assertRaises(ValueError):
            eh.speed_after_climb_bleed(100, -10)


class AltitudeFromBleedTest(unittest.TestCase):
    def test_anchor_altitude_from_bleed(self):
        self.assertAlmostEqual(
            eh.altitude_from_speed_bleed(100, 50), 7500.0 / (2.0 * eh.G0), places=3
        )

    def test_no_bleed_no_gain(self):
        self.assertAlmostEqual(eh.altitude_from_speed_bleed(100, 100), 0.0)

    def test_speed_increase_raises(self):
        with self.assertRaises(ValueError):
            eh.altitude_from_speed_bleed(100, 120)
        with self.assertRaises(ValueError):
            eh.altitude_from_speed_bleed(-1, 50)


class EnergyManeuverabilityScenarioTest(unittest.TestCase):
    def test_climb_cruise_trade_round_trip(self):
        # From 200 m/s, climb 500 m, then bleed back down to 200 m/s:
        # the altitude gain recovered matches the 500 m climb.
        v_after = eh.speed_after_climb_bleed(200, 500)
        recovered = eh.altitude_from_speed_bleed(200, v_after)
        self.assertAlmostEqual(recovered, 500.0, places=3)

    def test_zoom_climb_top(self):
        # At 250 m/s from 10,000 m, the zoom top is the energy height.
        top = eh.energy_height(10000, 250)
        self.assertAlmostEqual(top, 10000.0 + eh.kinetic_height(250), places=3)
        self.assertAlmostEqual(eh.speed_from_energy_height(top, 10000), 250.0, places=3)

    def test_ps_is_energy_height_rate(self):
        # Ps equals the rate of change of energy height per second.
        ps = eh.specific_excess_power(150000, 100000, 200, 800000)
        self.assertAlmostEqual(ps, 50000.0 * 200.0 / 800000.0)
        # Energy height one second later, at constant altitude: h_e grows by Ps.
        he_now = eh.energy_height(8000, 200)
        he_later = eh.energy_height(8000, (200.0 ** 2 + 2.0 * eh.G0 * ps) ** 0.5)
        self.assertAlmostEqual(he_later, he_now + ps, places=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

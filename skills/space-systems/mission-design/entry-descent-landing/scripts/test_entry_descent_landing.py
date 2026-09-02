#!/usr/bin/env python3
"""Gate 3 contract test: entry, descent, and landing sizing logic.

Exercises scripts/entry_descent_landing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. Covers the
ballistic coefficient, the steep ballistic entry peak deceleration
g-load, the entry corridor check, the Sutton-Graves stagnation point
convective heat rate and heat load integration, the parachute descent
terminal velocity, and invalid-input edge cases (zero density,
non-positive inputs, massless payload, very high entry speed).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import entry_descent_landing_logic as edl  # noqa: E402


class BallisticCoefficientTest(unittest.TestCase):
    def test_known_value(self):
        # m = 1000 kg, Cd = 1.3, A = 10 m^2 -> beta = 76.92 kg/m^2
        self.assertAlmostEqual(
            edl.ballistic_coefficient(1000.0, 1.3, 10.0), 1000.0 / 13.0
        )

    def test_heavier_mass_raises_beta(self):
        light = edl.ballistic_coefficient(800.0, 1.3, 10.0)
        heavy = edl.ballistic_coefficient(1600.0, 1.3, 10.0)
        self.assertGreater(heavy, light)

    def test_larger_area_lowers_beta(self):
        small = edl.ballistic_coefficient(1000.0, 1.3, 8.0)
        large = edl.ballistic_coefficient(1000.0, 1.3, 16.0)
        self.assertLess(large, small)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            edl.ballistic_coefficient(0.0, 1.3, 10.0)
        with self.assertRaises(ValueError):
            edl.ballistic_coefficient(1000.0, 0.0, 10.0)
        with self.assertRaises(ValueError):
            edl.ballistic_coefficient(1000.0, 1.3, -5.0)


class EntryDecelerationTest(unittest.TestCase):
    def test_mars_style_entry_g_load_band(self):
        # 5500 m/s at -12 deg with 11.1 km scale height: about 10.6 g
        d = edl.entry_deceleration(5500.0, -12.0, 11100.0)
        self.assertAlmostEqual(d["g_load"], 10.62762, places=3)
        self.assertAlmostEqual(d["accel"], 10.62762 * edl.G0, places=2)

    def test_steeper_angle_increases_g_load(self):
        shallow = edl.entry_deceleration(5500.0, -6.0, 11100.0)["g_load"]
        steep = edl.entry_deceleration(5500.0, -12.0, 11100.0)["g_load"]
        self.assertGreater(steep, shallow)

    def test_higher_speed_increases_g_load(self):
        slow = edl.entry_deceleration(5500.0, -12.0, 11100.0)["g_load"]
        fast = edl.entry_deceleration(11000.0, -12.0, 11100.0)["g_load"]
        self.assertGreater(fast, slow)
        self.assertAlmostEqual(fast, 4.0 * slow, places=6)  # V^2 scaling

    def test_very_high_entry_speed_finite(self):
        d = edl.entry_deceleration(20000.0, -15.0, 11100.0)
        self.assertGreater(d["g_load"], 100.0)  # harsh but finite
        self.assertTrue(math.isfinite(d["accel"]))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            edl.entry_deceleration(0.0, -12.0, 11100.0)
        with self.assertRaises(ValueError):
            edl.entry_deceleration(5500.0, 0.0, 11100.0)  # not descending
        with self.assertRaises(ValueError):
            edl.entry_deceleration(5500.0, 5.0, 11100.0)  # positive angle
        with self.assertRaises(ValueError):
            edl.entry_deceleration(5500.0, -90.0, 11100.0)  # boundary
        with self.assertRaises(ValueError):
            edl.entry_deceleration(5500.0, -12.0, 0.0)


class EntryCorridorTest(unittest.TestCase):
    def test_angle_inside_corridor(self):
        c = edl.entry_corridor_check(-8.0, -6.0, -11.5)
        self.assertTrue(c["within"])
        self.assertEqual(c["min"], -6.0)
        self.assertEqual(c["max"], -11.5)

    def test_angle_outside_corridor(self):
        self.assertFalse(edl.entry_corridor_check(-3.0, -6.0, -11.5)["within"])
        self.assertFalse(edl.entry_corridor_check(-14.0, -6.0, -11.5)["within"])

    def test_boundary_angle_counts_inside(self):
        self.assertTrue(edl.entry_corridor_check(-6.0, -6.0, -11.5)["within"])
        self.assertTrue(edl.entry_corridor_check(-11.5, -6.0, -11.5)["within"])

    def test_invalid_bounds_raise(self):
        with self.assertRaises(ValueError):
            edl.entry_corridor_check(-8.0, 0.0, -11.5)
        with self.assertRaises(ValueError):
            edl.entry_corridor_check(-8.0, -6.0, -95.0)
        with self.assertRaises(ValueError):
            edl.entry_corridor_check(-8.0, -11.5, -6.0)  # reversed bounds


class SuttonGravesTest(unittest.TestCase):
    def test_mars_peak_heating_magnitude(self):
        # rho = 2e-4 kg/m^3, V = 4800 m/s, r_n = 1 m -> ~0.29 MW/m^2
        q = edl.sutton_graves_heat_rate(2e-4, 4800.0, nose_radius=1.0)
        self.assertAlmostEqual(q, 286213.29251063656, places=1)

    def test_heat_rate_scales_as_v_cubed(self):
        q1 = edl.sutton_graves_heat_rate(2e-4, 4800.0)
        q2 = edl.sutton_graves_heat_rate(2e-4, 9600.0)
        self.assertAlmostEqual(q2, 8.0 * q1, places=3)

    def test_heat_rate_scales_as_sqrt_rho(self):
        q1 = edl.sutton_graves_heat_rate(2e-4, 4800.0)
        q4 = edl.sutton_graves_heat_rate(8e-4, 4800.0)
        self.assertAlmostEqual(q4, 2.0 * q1, places=3)

    def test_larger_nose_radius_lowers_heat_rate(self):
        sharp = edl.sutton_graves_heat_rate(2e-4, 4800.0, nose_radius=0.5)
        blunt = edl.sutton_graves_heat_rate(2e-4, 4800.0, nose_radius=2.0)
        self.assertLess(blunt, sharp)

    def test_zero_density_gives_zero_heat_rate(self):
        self.assertEqual(edl.sutton_graves_heat_rate(0.0, 4800.0), 0.0)

    def test_very_high_velocity_finite(self):
        q = edl.sutton_graves_heat_rate(1e-3, 20000.0, nose_radius=1.0)
        self.assertGreater(q, 1e6)
        self.assertTrue(math.isfinite(q))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            edl.sutton_graves_heat_rate(-1e-4, 4800.0)
        with self.assertRaises(ValueError):
            edl.sutton_graves_heat_rate(2e-4, 0.0)
        with self.assertRaises(ValueError):
            edl.sutton_graves_heat_rate(2e-4, 4800.0, nose_radius=0.0)
        with self.assertRaises(ValueError):
            edl.sutton_graves_heat_rate(2e-4, 4800.0, k=0.0)


class HeatLoadTest(unittest.TestCase):
    RATES = [1e5, 2.5e5, 3.0e5, 2.5e5, 1.5e5, 5e4]

    def test_rectangle_rule_integral(self):
        total = edl.heat_load(self.RATES, 10.0)
        self.assertAlmostEqual(total, 10.0 * sum(self.RATES), places=6)

    def test_zero_heat_rate_sequence(self):
        self.assertEqual(edl.heat_load([0.0, 0.0, 0.0], 10.0), 0.0)

    def test_longer_pulse_accumulates_more_heat(self):
        short = edl.heat_load(self.RATES, 10.0)
        long_ = edl.heat_load(self.RATES, 60.0)
        self.assertAlmostEqual(long_, 6.0 * short, places=6)

    def test_empty_sequence_raises(self):
        with self.assertRaises(ValueError):
            edl.heat_load([], 10.0)

    def test_non_positive_dt_raises(self):
        with self.assertRaises(ValueError):
            edl.heat_load(self.RATES, 0.0)
        with self.assertRaises(ValueError):
            edl.heat_load(self.RATES, -5.0)

    def test_negative_heat_rate_raises(self):
        with self.assertRaises(ValueError):
            edl.heat_load([1e5, -2e5], 10.0)


class ParachuteTerminalVelocityTest(unittest.TestCase):
    def test_earth_known_value(self):
        # 100 kg, Cd 0.75, S 20 m^2, sea level 1.225 kg/m^3 -> ~10.33 m/s
        v = edl.parachute_terminal_velocity(100.0, 0.75, 20.0, 1.225)
        self.assertAlmostEqual(v, 10.331459123427223, places=6)

    def test_mars_descent_value(self):
        # 600 kg, Cd 0.75, S 110 m^2, rho 0.02, g 3.711 -> ~51.95 m/s
        v = edl.parachute_terminal_velocity(600.0, 0.75, 110.0, 0.02, g=3.711)
        self.assertAlmostEqual(v, 51.95102588889935, places=6)

    def test_larger_canopy_slows_descent(self):
        small = edl.parachute_terminal_velocity(600.0, 0.75, 110.0, 0.02, g=3.711)
        large = edl.parachute_terminal_velocity(600.0, 0.75, 220.0, 0.02, g=3.711)
        self.assertLess(large, small)

    def test_denser_air_slows_descent(self):
        thin = edl.parachute_terminal_velocity(600.0, 0.75, 110.0, 0.01, g=3.711)
        thick = edl.parachute_terminal_velocity(600.0, 0.75, 110.0, 0.02, g=3.711)
        self.assertLess(thick, thin)

    def test_massless_payload_has_zero_terminal_velocity(self):
        self.assertEqual(edl.parachute_terminal_velocity(0.0, 0.75, 110.0, 0.02), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            edl.parachute_terminal_velocity(-10.0, 0.75, 110.0, 0.02)
        with self.assertRaises(ValueError):
            edl.parachute_terminal_velocity(600.0, 0.0, 110.0, 0.02)
        with self.assertRaises(ValueError):
            edl.parachute_terminal_velocity(600.0, 0.75, 0.0, 0.02)
        with self.assertRaises(ValueError):
            edl.parachute_terminal_velocity(600.0, 0.75, 110.0, 0.0)  # no atmosphere
        with self.assertRaises(ValueError):
            edl.parachute_terminal_velocity(600.0, 0.75, 110.0, 0.02, g=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

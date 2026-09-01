#!/usr/bin/env python3
"""Gate 3 contract test: FMS performance computation logic.

Exercises scripts/performance_computation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. Covers the cost
index definition, ECON cruise Mach selection (monotonic in cost index,
zero cost index selects max range, envelope clamps, weight and
altitude effects), the fuel/time trade at fixed distance, step-climb
benefit logic, VNAV top-of-descent with wind correction, ISA helper
sanity, and invalid-input edge cases.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import performance_computation_logic as perf  # noqa: E402


class IsaHelperTest(unittest.TestCase):
    def test_sea_level_values(self):
        self.assertAlmostEqual(perf.isa_temperature_k(0.0), 288.15, places=2)
        self.assertAlmostEqual(perf.isa_density_kgm3(0.0), 1.2250, places=4)
        self.assertAlmostEqual(perf.speed_of_sound_kts(0.0), 661.5, places=1)

    def test_cruise_altitude_values(self):
        self.assertAlmostEqual(perf.isa_temperature_k(35000.0), 218.81, places=1)
        self.assertLess(
            perf.isa_density_kgm3(40000.0), perf.isa_density_kgm3(35000.0)
        )

    def test_tropopause_temperature_floor(self):
        self.assertAlmostEqual(perf.isa_temperature_k(50000.0), 216.65, places=1)

    def test_mach_tas_roundtrip(self):
        tas = 450.0
        mach = perf.mach_from_tas(tas, 35000.0)
        self.assertAlmostEqual(perf.tas_from_mach(mach, 35000.0), tas, places=6)

    def test_nonpositive_tas_raises(self):
        with self.assertRaises(ValueError):
            perf.mach_from_tas(0.0, 35000.0)
        with self.assertRaises(ValueError):
            perf.tas_from_mach(0.0, 35000.0)


class CostIndexTest(unittest.TestCase):
    def test_definition(self):
        self.assertAlmostEqual(perf.cost_index(5000.0, 1.5), 3333.3333, places=3)

    def test_zero_time_cost_gives_zero_index(self):
        self.assertEqual(perf.cost_index(0.0, 1.5), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            perf.cost_index(-100.0, 1.5)
        with self.assertRaises(ValueError):
            perf.cost_index(100.0, 0.0)
        with self.assertRaises(ValueError):
            perf.cost_index(100.0, -1.0)


class EconMachTest(unittest.TestCase):
    def test_zero_cost_index_selects_max_range_speed(self):
        mach = perf.econ_mach_from_cost_index(0.0, 70000.0, 35000.0)
        max_range = perf.mach_from_tas(
            perf.max_range_speed_kts(70000.0, 35000.0), 35000.0
        )
        self.assertAlmostEqual(mach, max_range, places=6)

    def test_econ_increases_with_cost_index(self):
        m0 = perf.econ_mach_from_cost_index(0.0, 70000.0, 35000.0)
        m100 = perf.econ_mach_from_cost_index(100.0, 70000.0, 35000.0)
        m300 = perf.econ_mach_from_cost_index(300.0, 70000.0, 35000.0)
        self.assertGreater(m100, m0)
        self.assertGreater(m300, m100)

    def test_econ_clamped_to_envelope(self):
        self.assertEqual(
            perf.econ_mach_from_cost_index(999.0, 70000.0, 35000.0),
            perf.M_MMO,
        )
        self.assertAlmostEqual(
            perf.econ_mach_from_cost_index(50.0, 70000.0, 25000.0),
            perf.M_MIN,
            places=6,
        )

    def test_heavier_aircraft_fly_faster(self):
        light = perf.econ_mach_from_cost_index(50.0, 60000.0, 35000.0)
        heavy = perf.econ_mach_from_cost_index(50.0, 80000.0, 35000.0)
        self.assertGreater(heavy, light)

    def test_higher_altitude_not_slower(self):
        low = perf.econ_mach_from_cost_index(50.0, 70000.0, 25000.0)
        mid = perf.econ_mach_from_cost_index(50.0, 70000.0, 35000.0)
        high = perf.econ_mach_from_cost_index(50.0, 70000.0, 41000.0)
        self.assertGreaterEqual(mid, low)
        self.assertGreaterEqual(high, mid)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            perf.econ_mach_from_cost_index(-1.0, 70000.0, 35000.0)
        with self.assertRaises(ValueError):
            perf.econ_mach_from_cost_index(50.0, 0.0, 35000.0)
        with self.assertRaises(ValueError):
            perf.econ_mach_from_cost_index(50.0, -100.0, 35000.0)

    def test_summary_fields_consistent(self):
        s = perf.econ_speed_summary(50.0, 70000.0, 35000.0)
        self.assertAlmostEqual(
            s["cost_per_nm_kg"],
            s["fuel_per_nm_kg"] + 50.0 / s["tas_kts"],
            places=6,
        )
        self.assertGreater(s["tas_kts"], 400.0)
        self.assertGreater(s["fuel_per_nm_kg"], 0.0)


class FuelTimeTradeTest(unittest.TestCase):
    def test_faster_speed_saves_time(self):
        t = perf.fuel_time_trade(50.0, 70000.0, 35000.0, 0.80, 0.82, 1000.0)
        self.assertGreater(t["time_saved_h"], 0.0)
        self.assertEqual(t["faster_mach"], 0.82)

    def test_above_max_range_faster_burns_more(self):
        max_range = perf.mach_from_tas(
            perf.max_range_speed_kts(70000.0, 35000.0), 35000.0
        )
        t = perf.fuel_time_trade(
            50.0, 70000.0, 35000.0, max_range + 0.01, max_range + 0.03, 1000.0
        )
        self.assertGreater(t["extra_fuel_kg"], 0.0)

    def test_econ_speed_is_cost_neutral(self):
        econ = perf.econ_mach_from_cost_index(50.0, 70000.0, 35000.0)
        for delta in (-0.005, 0.005):
            t = perf.fuel_time_trade(
                50.0, 70000.0, 35000.0, econ, econ + delta, 1000.0
            )
            self.assertLess(abs(t["cost_delta_kg"]), 2.0, t)

    def test_fuel_scales_with_distance(self):
        t1 = perf.fuel_time_trade(50.0, 70000.0, 35000.0, 0.80, 0.82, 1000.0)
        t2 = perf.fuel_time_trade(50.0, 70000.0, 35000.0, 0.80, 0.82, 2000.0)
        self.assertAlmostEqual(t2["fuel_a_kg"], 2.0 * t1["fuel_a_kg"], places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            perf.fuel_time_trade(50.0, 70000.0, 35000.0, 0.80, 0.80, 1000.0)
        with self.assertRaises(ValueError):
            perf.fuel_time_trade(50.0, 70000.0, 35000.0, 0.80, 0.82, 0.0)
        with self.assertRaises(ValueError):
            perf.fuel_time_trade(-1.0, 70000.0, 35000.0, 0.80, 0.82, 1000.0)
        with self.assertRaises(ValueError):
            perf.fuel_time_trade(50.0, 70000.0, 35000.0, 0.0, 0.82, 1000.0)


class StepClimbTest(unittest.TestCase):
    def test_long_leg_advises_step(self):
        s = perf.step_climb_benefit(70000.0, 35000.0, 39000.0, 2000.0)
        self.assertGreater(s["benefit_kg"], 0.0)
        self.assertTrue(s["step_advised"])
        self.assertEqual(s["climb_penalty_kg"], 0.07 * 4000.0)

    def test_short_leg_rejects_step(self):
        s = perf.step_climb_benefit(70000.0, 35000.0, 39000.0, 800.0)
        self.assertLess(s["benefit_kg"], 0.0)
        self.assertFalse(s["step_advised"])

    def test_higher_altitude_cruise_burns_less(self):
        s = perf.step_climb_benefit(70000.0, 35000.0, 39000.0, 2000.0)
        self.assertLess(s["cruise_fuel_b_kg"], s["cruise_fuel_a_kg"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            perf.step_climb_benefit(70000.0, 39000.0, 35000.0, 2000.0)
        with self.assertRaises(ValueError):
            perf.step_climb_benefit(70000.0, 35000.0, 35000.0, 2000.0)
        with self.assertRaises(ValueError):
            perf.step_climb_benefit(0.0, 35000.0, 39000.0, 2000.0)
        with self.assertRaises(ValueError):
            perf.step_climb_benefit(70000.0, 35000.0, 39000.0, 0.0)
        with self.assertRaises(ValueError):
            perf.step_climb_benefit(70000.0, 35000.0, 39000.0, 2000.0,
                                    climb_fuel_per_ft=0.0)


class TopOfDescentTest(unittest.TestCase):
    def test_no_wind_ground_equals_air(self):
        d = perf.top_of_descent(35000.0, 10000.0, 3.0, 450.0, 0.0)
        self.assertAlmostEqual(d["ground_distance_nm"], d["air_distance_nm"], places=6)

    def test_headwind_lengthens_descent(self):
        d = perf.top_of_descent(35000.0, 10000.0, 3.0, 450.0, 60.0)
        self.assertGreater(d["ground_distance_nm"], d["air_distance_nm"])

    def test_tailwind_shortens_descent(self):
        d = perf.top_of_descent(35000.0, 10000.0, 3.0, 450.0, -60.0)
        self.assertLess(d["ground_distance_nm"], d["air_distance_nm"])

    def test_geometry_values(self):
        d = perf.top_of_descent(35000.0, 10000.0, 3.0, 450.0, 0.0)
        self.assertEqual(d["alt_to_lose_ft"], 25000.0)
        self.assertAlmostEqual(d["air_gradient_ft_per_nm"], 318.44, places=1)
        self.assertAlmostEqual(d["air_distance_nm"], 78.51, places=1)

    def test_no_descent_needed_returns_zero(self):
        d = perf.top_of_descent(10000.0, 10000.0, 3.0, 450.0, 0.0)
        self.assertEqual(d["air_distance_nm"], 0.0)
        self.assertEqual(d["ground_distance_nm"], 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            perf.top_of_descent(35000.0, 10000.0, 0.0, 450.0, 0.0)
        with self.assertRaises(ValueError):
            perf.top_of_descent(35000.0, 10000.0, 3.0, 450.0, 450.0)
        with self.assertRaises(ValueError):
            perf.top_of_descent(35000.0, 10000.0, 3.0, 0.0, 0.0)


class FuelPerNmTest(unittest.TestCase):
    def test_known_cruise_band(self):
        f = perf.fuel_per_nm(70000.0, 35000.0, 450.0)
        self.assertGreater(f, 4.0)
        self.assertLess(f, 8.0)

    def test_minimum_at_max_range_speed(self):
        v_mr = perf.max_range_speed_kts(70000.0, 35000.0)
        f_mr = perf.fuel_per_nm(70000.0, 35000.0, v_mr)
        for v in (v_mr - 40.0, v_mr + 40.0):
            self.assertGreater(perf.fuel_per_nm(70000.0, 35000.0, v), f_mr)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            perf.fuel_per_nm(0.0, 35000.0, 450.0)
        with self.assertRaises(ValueError):
            perf.fuel_per_nm(70000.0, 35000.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

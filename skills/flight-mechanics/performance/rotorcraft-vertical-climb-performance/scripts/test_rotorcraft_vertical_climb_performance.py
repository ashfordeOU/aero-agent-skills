"""Contract test for rotorcraft-vertical-climb-performance.

Deterministic, offline, stdlib unittest. Run from the repo root or the
leaf directory:

    python3 skills/flight-mechanics/performance/rotorcraft-vertical-climb-performance/scripts/test_rotorcraft_vertical_climb_performance.py

Covers the worked example (R = 5.0 m, 2200 kg, sea level, solidity
0.08, Cd0 = 0.012, tip speed 220 m/s, k = 1.15, climb 5 m/s, 600 kW
available) with the spec magnitude bounds, every validation rule from
the spec, the hover round-trip identity, climb induced velocity
monotonicity, the excess-power bracket behavior, determinism, and the
convenience-chain dict contract.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rotorcraft_vertical_climb_performance_logic as rvc

# Worked example inputs.
RADIUS = 5.0
WEIGHT_KG = 2200.0
RHO = 1.225
SOLIDITY = 0.08
CD0 = 0.012
TIP_SPEED = 220.0
K = 1.15
CLIMB_RATE = 5.0
AVAILABLE = 600000.0

# Worked example module outputs (run once, taken as assert targets).
TARGET_THRUST = 21574.63
TARGET_AREA = 78.53981633974483
TARGET_V_H = 10.588725632796958
TARGET_V_I_CLIMB5 = 8.379848828299561
TARGET_PROFILE_POWER = 122934.91876468362
TARGET_CLIMB_POWER = 454899.9998801546
TARGET_HOVER_TOTAL = 385649.9321186603
TARGET_MAX_VC = 13.396996396816053


class TestDiskArea(unittest.TestCase):

    def test_worked_example_area(self):
        self.assertAlmostEqual(rvc.disk_area(RADIUS), TARGET_AREA,
                               places=9)
        self.assertAlmostEqual(rvc.disk_area(RADIUS), math.pi * 25.0,
                               places=12)

    def test_area_scales_with_radius_squared(self):
        self.assertAlmostEqual(rvc.disk_area(4.0) / rvc.disk_area(2.0),
                               4.0, places=12)

    def test_nonpositive_radius_raises(self):
        for bad_radius in (0.0, -1.0, -5.0):
            with self.assertRaises(ValueError):
                rvc.disk_area(bad_radius)


class TestHoverInducedVelocity(unittest.TestCase):

    def test_worked_example_velocity_in_spec_bounds(self):
        v_h = rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA)
        self.assertAlmostEqual(v_h, TARGET_V_H, places=6)
        self.assertTrue(9.5 <= v_h <= 11.5, "v_h outside 9.5-11.5 m/s")

    def test_closed_form_momentum_theory(self):
        v_h = rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA, RHO)
        self.assertAlmostEqual(
            v_h, math.sqrt(TARGET_THRUST / (2.0 * RHO * TARGET_AREA)),
            places=12)

    def test_denser_air_lowers_induced_velocity(self):
        v_lo = rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                          1.0)
        v_hi = rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                          2.0)
        self.assertGreater(v_lo, v_hi)

    def test_nonpositive_inputs_raise(self):
        with self.assertRaises(ValueError):
            rvc.hover_induced_velocity(0.0, TARGET_AREA)
        with self.assertRaises(ValueError):
            rvc.hover_induced_velocity(-100.0, TARGET_AREA)
        with self.assertRaises(ValueError):
            rvc.hover_induced_velocity(TARGET_THRUST, 0.0)
        with self.assertRaises(ValueError):
            rvc.hover_induced_velocity(TARGET_THRUST, -1.0)
        with self.assertRaises(ValueError):
            rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA, 0.0)
        with self.assertRaises(ValueError):
            rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA, -1.225)


class TestClimbInducedVelocity(unittest.TestCase):

    def test_worked_example_climb5_in_spec_bounds(self):
        v_i = rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                         CLIMB_RATE)
        self.assertAlmostEqual(v_i, TARGET_V_I_CLIMB5, places=6)
        self.assertTrue(7.5 <= v_i <= 9.5, "v_i outside 7.5-9.5 m/s")

    def test_climb_induced_velocity_below_hover(self):
        v_h = rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA)
        v_i = rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                         CLIMB_RATE)
        self.assertLess(v_i, v_h)

    def test_monotonic_decrease_with_climb_rate(self):
        v_2 = rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA, 2.0)
        v_10 = rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                          10.0)
        self.assertGreater(v_2, v_10)

    def test_zero_climb_rate_equals_hover_velocity(self):
        v_h = rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA)
        v_0 = rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA, 0.0)
        self.assertAlmostEqual(v_0, v_h, places=12)

    def test_negative_climb_rate_raises(self):
        for bad_rate in (-0.1, -5.0):
            with self.assertRaises(ValueError):
                rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                           bad_rate)

    def test_nonpositive_geometry_raises(self):
        with self.assertRaises(ValueError):
            rvc.climb_induced_velocity(0.0, TARGET_AREA, CLIMB_RATE)
        with self.assertRaises(ValueError):
            rvc.climb_induced_velocity(TARGET_THRUST, 0.0, CLIMB_RATE)
        with self.assertRaises(ValueError):
            rvc.climb_induced_velocity(TARGET_THRUST, TARGET_AREA,
                                       CLIMB_RATE, 0.0)


class TestProfilePower(unittest.TestCase):

    def test_worked_example_profile_in_spec_bounds(self):
        p = rvc.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, TIP_SPEED)
        self.assertAlmostEqual(p, TARGET_PROFILE_POWER, places=3)
        self.assertTrue(100000.0 <= p <= 150000.0,
                        "profile power outside 100000-150000 W")

    def test_cubic_tip_speed_scaling(self):
        p1 = rvc.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, 100.0)
        p2 = rvc.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, 200.0)
        self.assertAlmostEqual(p2 / p1, 8.0, places=9)

    def test_nonpositive_arguments_raise(self):
        with self.assertRaises(ValueError):
            rvc.profile_power(0.0, TARGET_AREA, SOLIDITY, CD0,
                              TIP_SPEED)
        with self.assertRaises(ValueError):
            rvc.profile_power(RHO, 0.0, SOLIDITY, CD0, TIP_SPEED)
        with self.assertRaises(ValueError):
            rvc.profile_power(RHO, TARGET_AREA, 0.0, CD0, TIP_SPEED)
        with self.assertRaises(ValueError):
            rvc.profile_power(RHO, TARGET_AREA, SOLIDITY, 0.0,
                              TIP_SPEED)
        with self.assertRaises(ValueError):
            rvc.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, 0.0)
        with self.assertRaises(ValueError):
            rvc.profile_power(RHO, TARGET_AREA, SOLIDITY, CD0, -220.0)


class TestClimbPower(unittest.TestCase):

    def test_worked_example_climb_power_in_spec_bounds(self):
        p = rvc.climb_power(TARGET_THRUST, CLIMB_RATE,
                            TARGET_V_I_CLIMB5, TARGET_PROFILE_POWER)
        self.assertAlmostEqual(p, TARGET_CLIMB_POWER, places=3)
        self.assertTrue(420000.0 <= p <= 490000.0,
                        "climb power outside 420000-490000 W")

    def test_round_trip_hover_total(self):
        p = rvc.climb_power(TARGET_THRUST, 0.0, TARGET_V_H,
                            TARGET_PROFILE_POWER)
        expected = K * TARGET_THRUST * TARGET_V_H + TARGET_PROFILE_POWER
        self.assertAlmostEqual(p, expected, places=6)
        self.assertAlmostEqual(p, TARGET_HOVER_TOTAL, places=3)
        self.assertTrue(350000.0 <= p <= 430000.0,
                        "hover total outside 350000-430000 W")

    def test_climb_power_increases_with_climb_rate(self):
        p_2 = rvc.climb_power(TARGET_THRUST, 2.0,
                              rvc.climb_induced_velocity(TARGET_THRUST,
                                                         TARGET_AREA,
                                                         2.0),
                              TARGET_PROFILE_POWER)
        p_10 = rvc.climb_power(TARGET_THRUST, 10.0,
                               rvc.climb_induced_velocity(TARGET_THRUST,
                                                          TARGET_AREA,
                                                          10.0),
                               TARGET_PROFILE_POWER)
        self.assertLess(p_2, p_10)

    def test_default_k_matches_module_constant(self):
        p1 = rvc.climb_power(TARGET_THRUST, CLIMB_RATE,
                             TARGET_V_I_CLIMB5, TARGET_PROFILE_POWER)
        p2 = rvc.climb_power(TARGET_THRUST, CLIMB_RATE,
                             TARGET_V_I_CLIMB5, TARGET_PROFILE_POWER,
                             k=rvc.K_DEFAULT)
        self.assertEqual(p1, p2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rvc.climb_power(TARGET_THRUST, -1.0, TARGET_V_I_CLIMB5,
                            TARGET_PROFILE_POWER)
        with self.assertRaises(ValueError):
            rvc.climb_power(TARGET_THRUST, CLIMB_RATE, -0.5,
                            TARGET_PROFILE_POWER)
        with self.assertRaises(ValueError):
            rvc.climb_power(TARGET_THRUST, CLIMB_RATE,
                            TARGET_V_I_CLIMB5, -1.0)
        with self.assertRaises(ValueError):
            rvc.climb_power(TARGET_THRUST, CLIMB_RATE,
                            TARGET_V_I_CLIMB5, TARGET_PROFILE_POWER,
                            k=0.0)
        with self.assertRaises(ValueError):
            rvc.climb_power(TARGET_THRUST, CLIMB_RATE,
                            TARGET_V_I_CLIMB5, TARGET_PROFILE_POWER,
                            k=-1.15)


class TestClimbPowerMargin(unittest.TestCase):

    def test_margin_positive_for_excess_available_power(self):
        margin = rvc.climb_power_margin(AVAILABLE, TARGET_CLIMB_POWER)
        self.assertAlmostEqual(margin, 145100.0, places=1)

    def test_margin_negative_when_required_exceeds_available(self):
        margin = rvc.climb_power_margin(300000.0, TARGET_CLIMB_POWER)
        self.assertLess(margin, 0.0)

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            rvc.climb_power_margin(-1.0, TARGET_CLIMB_POWER)
        with self.assertRaises(ValueError):
            rvc.climb_power_margin(AVAILABLE, -1.0)


class TestMaxVerticalClimbRate(unittest.TestCase):

    def test_worked_example_600kw_in_spec_bounds(self):
        vc = rvc.max_vertical_climb_rate(TARGET_THRUST, TARGET_AREA,
                                         RHO, AVAILABLE,
                                         TARGET_PROFILE_POWER)
        self.assertAlmostEqual(vc, TARGET_MAX_VC, places=3)
        self.assertTrue(11.0 <= vc <= 16.0,
                        "max climb rate outside 11-16 m/s")

    def test_returns_upper_bracket_for_excess_power(self):
        # Above the power required at Vc = 200 m/s (about 5.10 MW for
        # this rotor) the balance never crosses; the bracket bound 200.0
        # is returned without raising.
        vc = rvc.max_vertical_climb_rate(TARGET_THRUST, TARGET_AREA,
                                         RHO, 6.0e6, TARGET_PROFILE_POWER)
        self.assertEqual(vc, 200.0)

    def test_five_megawatt_root_inside_bracket(self):
        # P(200 m/s) = 5.10 MW for this rotor, so 5 MW available still
        # crosses inside the bracket: the exact model returns the root
        # (about 196.0 m/s), not the upper bound.
        vc = rvc.max_vertical_climb_rate(TARGET_THRUST, TARGET_AREA,
                                         RHO, 5.0e6, TARGET_PROFILE_POWER)
        self.assertAlmostEqual(vc, 195.99966522153073, places=3)
        self.assertLess(vc, 200.0)
        self.assertGreater(vc, 190.0)

    def test_below_hover_power_raises(self):
        with self.assertRaises(ValueError):
            rvc.max_vertical_climb_rate(TARGET_THRUST, TARGET_AREA,
                                        RHO, 300000.0,
                                        TARGET_PROFILE_POWER)

    def test_available_equal_to_hover_power_gives_zero(self):
        hover = rvc.climb_power(
            TARGET_THRUST, 0.0,
            rvc.hover_induced_velocity(TARGET_THRUST, TARGET_AREA, RHO),
            TARGET_PROFILE_POWER)
        vc = rvc.max_vertical_climb_rate(TARGET_THRUST, TARGET_AREA,
                                         RHO, hover, TARGET_PROFILE_POWER)
        self.assertAlmostEqual(vc, 0.0, places=9)


class TestVerticalClimbPerformance(unittest.TestCase):

    EXPECTED_KEYS = ["thrust_N", "area_m2", "hover_induced_velocity",
                     "climb_induced_velocity", "profile_power_W",
                     "climb_power_W", "climb_power_margin_W",
                     "max_vertical_climb_rate"]

    def test_dict_contains_exactly_documented_keys(self):
        result = rvc.vertical_climb_performance(
            WEIGHT_KG, RADIUS, available_power=AVAILABLE)
        self.assertEqual(sorted(result.keys()), sorted(self.EXPECTED_KEYS))

    def test_dict_values_match_primitive_functions(self):
        result = rvc.vertical_climb_performance(
            WEIGHT_KG, RADIUS, rho=RHO, solidity=SOLIDITY,
            drag_coefficient=CD0, tip_speed=TIP_SPEED, k=K,
            climb_rate=CLIMB_RATE, available_power=AVAILABLE)
        self.assertAlmostEqual(result["thrust_N"], TARGET_THRUST,
                               places=6)
        self.assertAlmostEqual(result["area_m2"], TARGET_AREA, places=9)
        self.assertAlmostEqual(result["hover_induced_velocity"],
                               TARGET_V_H, places=6)
        self.assertAlmostEqual(result["climb_induced_velocity"],
                               TARGET_V_I_CLIMB5, places=6)
        self.assertAlmostEqual(result["profile_power_W"],
                               TARGET_PROFILE_POWER, places=3)
        self.assertAlmostEqual(result["climb_power_W"],
                               TARGET_CLIMB_POWER, places=3)
        self.assertAlmostEqual(result["climb_power_margin_W"],
                               AVAILABLE - TARGET_CLIMB_POWER, places=3)
        self.assertAlmostEqual(result["max_vertical_climb_rate"],
                               TARGET_MAX_VC, places=3)

    def test_no_available_power_gives_none_fields(self):
        result = rvc.vertical_climb_performance(WEIGHT_KG, RADIUS)
        self.assertEqual(sorted(result.keys()), sorted(self.EXPECTED_KEYS))
        self.assertIsNone(result["climb_power_margin_W"])
        self.assertIsNone(result["max_vertical_climb_rate"])
        self.assertAlmostEqual(result["climb_power_W"],
                               TARGET_CLIMB_POWER, places=3)

    def test_valueerrors_propagate_from_chain(self):
        with self.assertRaises(ValueError):
            rvc.vertical_climb_performance(WEIGHT_KG, -5.0)
        with self.assertRaises(ValueError):
            rvc.vertical_climb_performance(WEIGHT_KG, RADIUS,
                                           climb_rate=-1.0)
        with self.assertRaises(ValueError):
            rvc.vertical_climb_performance(WEIGHT_KG, RADIUS,
                                           available_power=300000.0)


class TestDeterminismAndPurity(unittest.TestCase):

    def test_run_to_run_identical_floats(self):
        a = rvc.vertical_climb_performance(
            WEIGHT_KG, RADIUS, available_power=AVAILABLE)
        b = rvc.vertical_climb_performance(
            WEIGHT_KG, RADIUS, available_power=AVAILABLE)
        self.assertEqual(a, b)

    def test_module_imports_only_stdlib_math(self):
        source_path = os.path.join(os.path.dirname(os.path.abspath(
            __file__)), "rotorcraft_vertical_climb_performance_logic.py")
        with open(source_path) as handle:
            source = handle.read()
        self.assertNotIn("import random", source)
        self.assertNotIn("numpy", source)
        self.assertNotIn("scipy", source)
        self.assertIn("import math", source)


if __name__ == "__main__":
    unittest.main()

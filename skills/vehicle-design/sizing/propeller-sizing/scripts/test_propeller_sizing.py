#!/usr/bin/env python3
"""Gate 3 contract test: propeller sizing.

Exercises scripts/propeller_sizing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the advance ratio from
flight speed, rpm, and diameter; the tip speed and tip Mach check
against the tip Mach limit; the disk loading and power loading; the
static thrust estimate and its power inverse from actuator disk
momentum theory; the diameter from a tip speed limit; the solidity and
activity factor of the blade set; the efficiency versus advance ratio
curve; the ground clearance constraint; the P-factor yawing moment;
and the thrust-versus-power trade in flight. Worked anchors are pinned
and invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import propeller_sizing_logic as psl  # noqa: E402


class AdvanceRatioTest(unittest.TestCase):
    def test_anchor(self):
        # V = 70 m/s, rpm = 2200, D = 2.0 m:
        # J = 70 / (2200 / 60 * 2.0) = 0.9545.
        self.assertAlmostEqual(psl.advance_ratio(70, 2200, 2.0), 0.954545,
                               places=5)

    def test_static_flight_gives_zero(self):
        self.assertEqual(psl.advance_ratio(0, 2200, 2.0), 0.0)

    def test_round_trip(self):
        # Higher speed at fixed rpm and diameter raises J.
        j1 = psl.advance_ratio(70, 2200, 2.0)
        j2 = psl.advance_ratio(90, 2200, 2.0)
        self.assertGreater(j2, j1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.advance_ratio(70, 0, 2.0)      # rpm zero
        with self.assertRaises(ValueError):
            psl.advance_ratio(70, -2200, 2.0)  # rpm negative
        with self.assertRaises(ValueError):
            psl.advance_ratio(70, 2200, 0)     # diameter zero
        with self.assertRaises(ValueError):
            psl.advance_ratio(70, 2200, -2.0)  # diameter negative
        with self.assertRaises(ValueError):
            psl.advance_ratio(-5, 2200, 2.0)   # speed negative


class TipSpeedTest(unittest.TestCase):
    def test_tip_speed_anchor(self):
        # V_tip = pi * 2.0 * 2200 / 60 = 230.38 m/s.
        self.assertAlmostEqual(psl.tip_speed(2200, 2.0), 230.383461,
                               places=5)

    def test_tip_mach_anchor(self):
        self.assertAlmostEqual(psl.tip_mach_number(230.383461, 340.3),
                               0.677001, places=5)

    def test_mach_check_within_limit(self):
        # rpm = 2200, D = 2.0 m at a = 340.3 m/s stays under the 0.85
        # tip Mach limit with about 0.173 margin.
        r = psl.tip_mach_check(2200, 2.0, 340.3, mach_limit=0.85)
        self.assertAlmostEqual(r["tip_speed_mps"], 230.383461, places=5)
        self.assertAlmostEqual(r["tip_mach"], 0.677001, places=5)
        self.assertTrue(r["within_limit"])
        self.assertAlmostEqual(r["margin_mach"], 0.172999, places=5)

    def test_mach_check_exceeded(self):
        # Doubling the diameter doubles the tip speed and the tip Mach,
        # pushing it past the 0.85 limit.
        r = psl.tip_mach_check(2200, 4.0, 340.3, mach_limit=0.85)
        self.assertFalse(r["within_limit"])
        self.assertLess(r["margin_mach"], 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.tip_speed(0, 2.0)
        with self.assertRaises(ValueError):
            psl.tip_speed(2200, 0)
        with self.assertRaises(ValueError):
            psl.tip_mach_number(-1, 340.3)
        with self.assertRaises(ValueError):
            psl.tip_mach_check(2200, 2.0, 340.3, mach_limit=0)  # limit zero


class DiskLoadingTest(unittest.TestCase):
    def test_disk_loading_anchor(self):
        # DL = 4000 / (pi * 2.0^2 / 4) = 1273.24 N/m^2.
        self.assertAlmostEqual(psl.disk_loading(4000, 2.0), 1273.2395,
                               places=3)

    def test_power_loading_anchor(self):
        # PL = 4000 / 150 = 26.667 N per kW.
        self.assertAlmostEqual(psl.power_loading(4000, 150000), 26.666667,
                               places=5)

    def test_larger_disk_lowers_loading(self):
        self.assertLess(psl.disk_loading(4000, 2.6),
                        psl.disk_loading(4000, 2.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.disk_loading(0, 2.0)
        with self.assertRaises(ValueError):
            psl.disk_loading(4000, -2.0)
        with self.assertRaises(ValueError):
            psl.power_loading(4000, 0)


class StaticThrustTest(unittest.TestCase):
    def test_static_thrust_anchor(self):
        # T = (2 * 1.225 * pi * 150000^2)^(1/3) = 5573.99 N.
        self.assertAlmostEqual(psl.static_thrust_estimate(150000, 2.0),
                               5573.99, places=1)

    def test_power_round_trip(self):
        # The power inverse returns the shaft power for the anchor
        # thrust.
        t = psl.static_thrust_estimate(150000, 2.0)
        self.assertAlmostEqual(psl.power_for_static_thrust(t, 2.0),
                               150000.0, places=0)

    def test_larger_disk_gives_more_thrust(self):
        self.assertGreater(psl.static_thrust_estimate(150000, 2.4),
                           psl.static_thrust_estimate(150000, 2.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.static_thrust_estimate(0, 2.0)         # power zero
        with self.assertRaises(ValueError):
            psl.static_thrust_estimate(150000, -2.0)   # diameter negative
        with self.assertRaises(ValueError):
            psl.static_thrust_estimate(150000, 2.0, rho=0)  # density zero
        with self.assertRaises(ValueError):
            psl.power_for_static_thrust(-100, 2.0)     # thrust negative


class TipSpeedLimitTest(unittest.TestCase):
    def test_diameter_anchor(self):
        # D = 250 / (pi * 2200 / 60) = 2.1703 m.
        self.assertAlmostEqual(psl.diameter_from_tip_speed_limit(2200, 250),
                               2.1703, places=3)

    def test_round_trip(self):
        # The diameter from the limit reproduces the tip speed limit.
        d = psl.diameter_from_tip_speed_limit(2200, 250)
        self.assertAlmostEqual(psl.tip_speed(2200, d), 250.0, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.diameter_from_tip_speed_limit(0, 250)
        with self.assertRaises(ValueError):
            psl.diameter_from_tip_speed_limit(2200, 0)


class BladeGeometryTest(unittest.TestCase):
    def test_solidity_anchor(self):
        # sigma = 3 * 0.25 / (pi * 2.0) = 0.11937.
        self.assertAlmostEqual(psl.solidity(3, 0.25, 2.0), 0.119366,
                               places=5)

    def test_activity_factor_anchor(self):
        # AF = 3 * (100000/16) * (0.25/2.0) * (1 - 0.15^4) / 4 = 585.64.
        self.assertAlmostEqual(psl.activity_factor(3, 0.25, 2.0), 585.64,
                               places=1)

    def test_more_blades_raise_loading(self):
        self.assertGreater(psl.solidity(4, 0.25, 2.0),
                           psl.solidity(3, 0.25, 2.0))
        self.assertGreater(psl.activity_factor(4, 0.25, 2.0),
                           psl.activity_factor(3, 0.25, 2.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.solidity(0, 0.25, 2.0)          # blade count zero
        with self.assertRaises(ValueError):
            psl.solidity(3.5, 0.25, 2.0)        # blade count not integer
        with self.assertRaises(ValueError):
            psl.solidity(3, 0, 2.0)             # chord zero
        with self.assertRaises(ValueError):
            psl.solidity(3, 0.25, -2.0)         # diameter negative
        with self.assertRaises(ValueError):
            psl.activity_factor(3, 0.25, 2.0, hub_fraction=0)    # hub zero
        with self.assertRaises(ValueError):
            psl.activity_factor(3, 0.25, 2.0, hub_fraction=1.5)  # hub > 1


class EfficiencyCurveTest(unittest.TestCase):
    def test_design_point_anchor(self):
        self.assertAlmostEqual(
            psl.efficiency_at_advance_ratio(0.9, 0.9, 0.85), 0.85, places=6)

    def test_static_and_twice_design_give_zero(self):
        # J = 0 (static, no useful work) and J = 2 * J_design both give
        # zero efficiency under the parabolic model.
        self.assertEqual(psl.efficiency_at_advance_ratio(0.0, 0.9, 0.85), 0.0)
        self.assertEqual(psl.efficiency_at_advance_ratio(1.8, 0.9, 0.85), 0.0)
        self.assertEqual(psl.efficiency_at_advance_ratio(2.0, 0.9, 0.85), 0.0)

    def test_midpoint_anchor(self):
        # Half the design advance ratio: eta = 0.85 * (1 - 0.25) = 0.6375.
        self.assertAlmostEqual(
            psl.efficiency_at_advance_ratio(0.45, 0.9, 0.85), 0.6375,
            places=6)

    def test_peaks_at_design_point(self):
        eta_off = psl.efficiency_at_advance_ratio(0.5, 0.9, 0.85)
        eta_design = psl.efficiency_at_advance_ratio(0.9, 0.9, 0.85)
        self.assertGreater(eta_design, eta_off)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.efficiency_at_advance_ratio(-0.1, 0.9, 0.85)  # J negative
        with self.assertRaises(ValueError):
            psl.efficiency_at_advance_ratio(0.5, 0, 0.85)     # design J zero
        with self.assertRaises(ValueError):
            psl.efficiency_at_advance_ratio(0.5, 0.9, 1.2)    # eta > 1


class GroundClearanceTest(unittest.TestCase):
    def test_clearance_anchor(self):
        # D = 2.0 m at a hub height of 1.6 m leaves 0.6 m of clearance.
        r = psl.ground_clearance_check(2.0, 1.6, 0.2)
        self.assertAlmostEqual(r["clearance_m"], 0.6, places=6)
        self.assertTrue(r["ok"])

    def test_exceeded_diameter_fails(self):
        # D = 3.0 m at the same hub height leaves 0.1 m, below the
        # 0.2 m minimum.
        r = psl.ground_clearance_check(3.0, 1.6, 0.2)
        self.assertAlmostEqual(r["clearance_m"], 0.1, places=6)
        self.assertFalse(r["ok"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.ground_clearance_check(0, 1.6, 0.2)
        with self.assertRaises(ValueError):
            psl.ground_clearance_check(2.0, 0, 0.2)
        with self.assertRaises(ValueError):
            psl.ground_clearance_check(2.0, 1.6, -0.1)


class PFactorTest(unittest.TestCase):
    def test_p_factor_anchor(self):
        # N_p = 4000 * (2.0 / 4) * sin(10 deg) = 347.30 N m.
        alpha = 10.0 * math.pi / 180.0
        self.assertAlmostEqual(psl.p_factor_moment(4000, 2.0, alpha),
                               347.30, places=1)

    def test_zero_angle_gives_zero(self):
        self.assertEqual(psl.p_factor_moment(4000, 2.0, 0.0), 0.0)

    def test_larger_angle_raises_moment(self):
        a1 = psl.p_factor_moment(4000, 2.0, 5.0 * math.pi / 180.0)
        a2 = psl.p_factor_moment(4000, 2.0, 10.0 * math.pi / 180.0)
        self.assertGreater(a2, a1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.p_factor_moment(0, 2.0, 0.1)
        with self.assertRaises(ValueError):
            psl.p_factor_moment(4000, -2.0, 0.1)
        with self.assertRaises(ValueError):
            psl.p_factor_moment(4000, 2.0, -0.1)  # angle negative
        with self.assertRaises(ValueError):
            psl.p_factor_moment(4000, 2.0, 2.0)   # angle > pi/2


class ThrustPowerTradeTest(unittest.TestCase):
    def test_in_flight_thrust_anchor(self):
        # T = 0.8 * 150000 / 70 = 1714.29 N.
        self.assertAlmostEqual(psl.thrust_from_power_in_flight(150000, 70, 0.8),
                               1714.2857, places=3)

    def test_lower_speed_gives_more_thrust(self):
        self.assertGreater(psl.thrust_from_power_in_flight(150000, 60, 0.8),
                           psl.thrust_from_power_in_flight(150000, 70, 0.8))

    def test_static_thrust_is_maximum(self):
        # The static actuator disk thrust exceeds the in-flight thrust
        # from the same power at cruise speed.
        t_static = psl.static_thrust_estimate(150000, 2.0)
        t_flight = psl.thrust_from_power_in_flight(150000, 70, 0.8)
        self.assertGreater(t_static, t_flight)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            psl.thrust_from_power_in_flight(0, 70, 0.8)
        with self.assertRaises(ValueError):
            psl.thrust_from_power_in_flight(150000, 0, 0.8)  # speed zero
        with self.assertRaises(ValueError):
            psl.thrust_from_power_in_flight(150000, 70, 1.5)  # eta > 1


if __name__ == "__main__":
    unittest.main(verbosity=2)

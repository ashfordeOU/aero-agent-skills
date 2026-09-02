#!/usr/bin/env python3
"""Gate 3 contract test: turboprop cycle and propeller performance.

Exercises scripts/turboprop_cycle_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (propeller Froude efficiency
from flight and slipstream velocity; thrust from shaft power; static
thrust from actuator-disk momentum theory; equivalent shaft power with
jet thrust credit; advance ratio, power and thrust coefficients;
specific fuel consumption on shaft power; overall efficiency; invalid
inputs raise ValueError.

Anchors:
- propeller_efficiency(100, 150) = 0.8 (Froude efficiency at vj = 1.5 vf)
- propeller_efficiency(100, 200) = 2/3 (vj = 2 vf)
- thrust_from_shaft_power(1e6, 100, 0.8) = 8000 N
- static_thrust(1e6, 1.225, 3.0) = 25872.2 N (3 m propeller, sea level)
- equivalent_shaft_power(1e6, 2000, 100, 0.8) = 1.25e6 W
- specific_fuel_consumption(0.05, 1e6) = 0.18 kg/(kW h)
- advance_ratio(80, 1200, 2.5) = 1.6
- power_coefficient(1e6, 1.225, 1200, 2.5) = 1.0449
- thrust_coefficient(8000, 1.225, 1200, 2.5) = 0.4180
- overall_efficiency(0.4, 0.8, 0.98) = 0.3136
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import turboprop_cycle_logic as tp  # noqa: E402


class PropellerEfficiencyTest(unittest.TestCase):
    def test_anchor_vj_1_5_vf(self):
        self.assertAlmostEqual(tp.propeller_efficiency(100, 150), 0.8)

    def test_anchor_vj_2_vf(self):
        self.assertAlmostEqual(tp.propeller_efficiency(100, 200), 2.0 / 3.0)

    def test_anchor_no_acceleration(self):
        self.assertAlmostEqual(tp.propeller_efficiency(100, 100), 1.0)

    def test_anchor_vj_4_vf(self):
        self.assertAlmostEqual(tp.propeller_efficiency(100, 400), 0.4)

    def test_slipstream_faster_lowers_efficiency(self):
        slow = tp.propeller_efficiency(100, 110)
        fast = tp.propeller_efficiency(100, 300)
        self.assertGreater(slow, fast)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.propeller_efficiency(0, 150)
        with self.assertRaises(ValueError):
            tp.propeller_efficiency(-100, 150)
        with self.assertRaises(ValueError):
            tp.propeller_efficiency(100, 50)
        with self.assertRaises(ValueError):
            tp.propeller_efficiency(100, 0)


class ThrustFromShaftPowerTest(unittest.TestCase):
    def test_anchor_cruise_thrust(self):
        self.assertAlmostEqual(tp.thrust_from_shaft_power(1e6, 100, 0.8), 8000.0)

    def test_anchor_second_case(self):
        self.assertAlmostEqual(tp.thrust_from_shaft_power(2e6, 120, 0.85), 14166.6667, places=4)

    def test_more_power_more_thrust(self):
        low = tp.thrust_from_shaft_power(1e6, 100, 0.8)
        high = tp.thrust_from_shaft_power(2e6, 100, 0.8)
        self.assertLess(low, high)

    def test_higher_efficiency_more_thrust(self):
        low = tp.thrust_from_shaft_power(1e6, 100, 0.7)
        high = tp.thrust_from_shaft_power(1e6, 100, 0.9)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.thrust_from_shaft_power(-1e6, 100, 0.8)
        with self.assertRaises(ValueError):
            tp.thrust_from_shaft_power(1e6, 0, 0.8)
        with self.assertRaises(ValueError):
            tp.thrust_from_shaft_power(1e6, 100, 1.5)
        with self.assertRaises(ValueError):
            tp.thrust_from_shaft_power(1e6, 100, 0)


class StaticThrustTest(unittest.TestCase):
    def test_anchor_three_meter_sea_level(self):
        self.assertAlmostEqual(tp.static_thrust(1e6, 1.225, 3.0), 25872.1681, places=2)

    def test_anchor_larger_propeller(self):
        self.assertAlmostEqual(tp.static_thrust(2e6, 1.225, 3.5), 45514.5949, places=2)

    def test_more_power_more_static_thrust(self):
        low = tp.static_thrust(1e6, 1.225, 3.0)
        high = tp.static_thrust(2e6, 1.225, 3.0)
        self.assertLess(low, high)

    def test_static_thrust_greater_than_cruise_thrust(self):
        static = tp.static_thrust(1e6, 1.225, 3.0)
        cruise = tp.thrust_from_shaft_power(1e6, 100, 0.8)
        self.assertGreater(static, cruise)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.static_thrust(-1e6, 1.225, 3.0)
        with self.assertRaises(ValueError):
            tp.static_thrust(1e6, 0, 3.0)
        with self.assertRaises(ValueError):
            tp.static_thrust(1e6, 1.225, 0)


class DiskAreaTest(unittest.TestCase):
    def test_anchor_three_meter(self):
        self.assertAlmostEqual(tp.propeller_disk_area(3.0), 7.0685835)

    def test_area_grows_with_square_of_diameter(self):
        four = tp.propeller_disk_area(4.0)
        two = tp.propeller_disk_area(2.0)
        self.assertAlmostEqual(four, 4.0 * two)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.propeller_disk_area(0)
        with self.assertRaises(ValueError):
            tp.propeller_disk_area(-2.0)


class EquivalentShaftPowerTest(unittest.TestCase):
    def test_anchor_with_jet_credit(self):
        self.assertAlmostEqual(tp.equivalent_shaft_power(1e6, 2000, 100, 0.8), 1.25e6)

    def test_anchor_second_case(self):
        self.assertAlmostEqual(tp.equivalent_shaft_power(2e6, 5000, 120, 0.85), 2705882.3529, places=4)

    def test_no_jet_thrust_returns_shaft_power(self):
        self.assertAlmostEqual(tp.equivalent_shaft_power(1e6, 0, 100, 0.8), 1e6)

    def test_more_jet_thrust_more_esp(self):
        low = tp.equivalent_shaft_power(1e6, 1000, 100, 0.8)
        high = tp.equivalent_shaft_power(1e6, 3000, 100, 0.8)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.equivalent_shaft_power(-1e6, 2000, 100, 0.8)
        with self.assertRaises(ValueError):
            tp.equivalent_shaft_power(1e6, -2000, 100, 0.8)
        with self.assertRaises(ValueError):
            tp.equivalent_shaft_power(1e6, 2000, 0, 0.8)
        with self.assertRaises(ValueError):
            tp.equivalent_shaft_power(1e6, 2000, 100, 1.2)


class SpecificFuelConsumptionTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tp.specific_fuel_consumption(0.05, 1e6), 0.18)

    def test_anchor_second_case(self):
        self.assertAlmostEqual(tp.specific_fuel_consumption(0.12, 2e6), 0.216)

    def test_more_fuel_higher_sfc(self):
        low = tp.specific_fuel_consumption(0.05, 1e6)
        high = tp.specific_fuel_consumption(0.10, 1e6)
        self.assertLess(low, high)

    def test_more_power_lower_sfc(self):
        low = tp.specific_fuel_consumption(0.05, 2e6)
        high = tp.specific_fuel_consumption(0.05, 1e6)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.specific_fuel_consumption(-0.05, 1e6)
        with self.assertRaises(ValueError):
            tp.specific_fuel_consumption(0.05, 0)


class AdvanceRatioTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tp.advance_ratio(80, 1200, 2.5), 1.6)

    def test_anchor_second_case(self):
        self.assertAlmostEqual(tp.advance_ratio(60, 1000, 3.0), 1.2)

    def test_static_zero_advance(self):
        self.assertAlmostEqual(tp.advance_ratio(0, 1200, 2.5), 0.0)

    def test_higher_rpm_lower_advance(self):
        low = tp.advance_ratio(80, 2400, 2.5)
        high = tp.advance_ratio(80, 1200, 2.5)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.advance_ratio(-80, 1200, 2.5)
        with self.assertRaises(ValueError):
            tp.advance_ratio(80, 0, 2.5)
        with self.assertRaises(ValueError):
            tp.advance_ratio(80, 1200, 0)


class PowerCoefficientTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tp.power_coefficient(1e6, 1.225, 1200, 2.5), 1.0448980)

    def test_anchor_second_case(self):
        self.assertAlmostEqual(tp.power_coefficient(1.5e6, 1.0, 1500, 3.0), 0.3950617)

    def test_more_power_higher_coefficient(self):
        low = tp.power_coefficient(1e6, 1.225, 1200, 2.5)
        high = tp.power_coefficient(2e6, 1.225, 1200, 2.5)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.power_coefficient(-1e6, 1.225, 1200, 2.5)
        with self.assertRaises(ValueError):
            tp.power_coefficient(1e6, 0, 1200, 2.5)
        with self.assertRaises(ValueError):
            tp.power_coefficient(1e6, 1.225, 0, 2.5)
        with self.assertRaises(ValueError):
            tp.power_coefficient(1e6, 1.225, 1200, 0)


class ThrustCoefficientTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(tp.thrust_coefficient(8000, 1.225, 1200, 2.5), 0.4179592)

    def test_anchor_second_case(self):
        self.assertAlmostEqual(tp.thrust_coefficient(12000, 1.0, 1500, 3.0), 0.2370370)

    def test_more_thrust_higher_coefficient(self):
        low = tp.thrust_coefficient(4000, 1.225, 1200, 2.5)
        high = tp.thrust_coefficient(12000, 1.225, 1200, 2.5)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.thrust_coefficient(-8000, 1.225, 1200, 2.5)
        with self.assertRaises(ValueError):
            tp.thrust_coefficient(8000, 1.225, 0, 2.5)
        with self.assertRaises(ValueError):
            tp.thrust_coefficient(8000, 1.225, 1200, -2.5)


class OverallEfficiencyTest(unittest.TestCase):
    def test_anchor_with_mechanical(self):
        self.assertAlmostEqual(tp.overall_efficiency(0.4, 0.8, 0.98), 0.3136)

    def test_anchor_default_mechanical(self):
        self.assertAlmostEqual(tp.overall_efficiency(0.35, 0.85), 0.2975)

    def test_all_three_multiply(self):
        self.assertAlmostEqual(tp.overall_efficiency(0.5, 0.8, 0.9), 0.36)

    def test_lower_propeller_efficiency_lower_overall(self):
        low = tp.overall_efficiency(0.4, 0.6)
        high = tp.overall_efficiency(0.4, 0.9)
        self.assertLess(low, high)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tp.overall_efficiency(0, 0.8)
        with self.assertRaises(ValueError):
            tp.overall_efficiency(0.4, 1.5)
        with self.assertRaises(ValueError):
            tp.overall_efficiency(0.4, 0.8, 0)


class TurbopropScenarioTest(unittest.TestCase):
    def test_cruise_powerplant_assessment(self):
        # 3 m propeller at 1200 rpm, 1 MW shaft power, cruise at 100 m/s
        # with slipstream at 150 m/s. Propeller efficiency 0.8, cruise
        # thrust 8000 N, and the residual jet thrust of 2000 N raises
        # the equivalent shaft power to 1.25 MW.
        eta = tp.propeller_efficiency(100, 150)
        thrust = tp.thrust_from_shaft_power(1e6, 100, eta)
        esp = tp.equivalent_shaft_power(1e6, 2000, 100, eta)
        j = tp.advance_ratio(100, 1200, 3.0)
        cp = tp.power_coefficient(1e6, 1.225, 1200, 3.0)
        ct = tp.thrust_coefficient(thrust, 1.225, 1200, 3.0)
        sfc = tp.specific_fuel_consumption(0.05, 1e6)
        self.assertAlmostEqual(eta, 0.8)
        self.assertAlmostEqual(thrust, 8000.0)
        self.assertAlmostEqual(esp, 1.25e6)
        self.assertAlmostEqual(j, 100.0 / (20.0 * 3.0))
        self.assertAlmostEqual(cp, 1e6 / (1.225 * 20 ** 3 * 3 ** 5))
        self.assertAlmostEqual(ct, 8000.0 / (1.225 * 20 ** 2 * 3 ** 4))
        self.assertAlmostEqual(sfc, 0.18)

    def test_static_vs_cruise_thrust_ratio(self):
        # Static thrust from 1 MW on a 3 m propeller at sea level is
        # about 25.9 kN, more than three times the 8 kN cruise thrust at
        # 100 m/s: the propeller is most loaded at the stand.
        static = tp.static_thrust(1e6, 1.225, 3.0)
        cruise = tp.thrust_from_shaft_power(1e6, 100, 0.8)
        self.assertGreater(static / cruise, 3.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

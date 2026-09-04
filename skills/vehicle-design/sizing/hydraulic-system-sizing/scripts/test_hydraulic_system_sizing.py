#!/usr/bin/env python3
"""Gate 3 contract test: aircraft hydraulic system sizing.

Exercises scripts/hydraulic_system_sizing_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3 -
actuator flow from piston area and rod speed, worst-case simultaneous
demand, pump flow with leakage, pump power from pressure and flow over
efficiency, emergency accumulator gas volumes from the adiabatic gas
law with the p1 V1^n = p2 V2^n closure, and reservoir volume from
leakage make-up with margin; non-physical inputs raise ValueError.

Analytic anchors (reference system, 3000 psi):
  actuator flow 0.0025 m2 * 0.30 m/s = 0.00075 m3/s = 45.0 L/min
  4 of 6 simultaneous: 180 L/min; + 15 L/min leakage = 195 L/min
    = 0.00325 m3/s
  pump power 20.6843 MPa * 0.00325 / 0.85 = 79086.9 W = 79.0869 kW
  accumulator ratio (3000/1500)^(1/1.4) = 1.64067, V1 = 1.0/0.64067
    = 1.5609 L, V2 = 2.5609 L, p V^n = 2434.17 both sides (SI units),
    closure_check matches 0.0
  reservoir 15 * 2 * 1.2 = 36.0 L
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hydraulic_system_sizing_logic as hsl  # noqa: E402

# Worked-example reference system (module real outputs as assert targets).
AREA_M2 = 0.0025
SPEED_M_S = 0.30
N_ACTUATORS = 6
N_SIMULTANEOUS = 4
PRESSURE_PSI = 3000.0
LEAKAGE_LPM = 15.0
EFFICIENCY = 0.85
USABLE_L = 1.0
CHARGED_PSI = 3000.0
DEPLETED_PSI = 1500.0


class ActuatorFlowTest(unittest.TestCase):
    def test_worked_example_flow(self):
        # 0.0025 m2 at 0.30 m/s = 45.0 L/min, 0.00075 m3/s
        res = hsl.actuator_flow(AREA_M2, SPEED_M_S)
        self.assertAlmostEqual(res["flow_m3s"], 0.00075, places=9)
        self.assertAlmostEqual(res["flow_lpm"], 45.0, places=6)

    def test_doubling_area_doubles_flow(self):
        res = hsl.actuator_flow(2 * AREA_M2, SPEED_M_S)
        self.assertAlmostEqual(res["flow_lpm"], 90.0, places=6)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            hsl.actuator_flow(0.0, SPEED_M_S)
        with self.assertRaises(ValueError):
            hsl.actuator_flow(AREA_M2, -0.5)

    def test_dict_keys_exact(self):
        self.assertEqual(
            sorted(hsl.actuator_flow(AREA_M2, SPEED_M_S)),
            ["flow_lpm", "flow_m3s"])


class SimultaneousDemandTest(unittest.TestCase):
    def test_four_of_six_demand(self):
        self.assertAlmostEqual(
            hsl.simultaneous_demand(45.0, N_SIMULTANEOUS), 180.0, places=6)

    def test_all_six_demand(self):
        self.assertAlmostEqual(
            hsl.simultaneous_demand(45.0, N_ACTUATORS), 270.0, places=6)

    def test_non_positive_flow_or_count_raises(self):
        with self.assertRaises(ValueError):
            hsl.simultaneous_demand(-45.0, N_SIMULTANEOUS)
        with self.assertRaises(ValueError):
            hsl.simultaneous_demand(45.0, 0)


class PumpFlowTest(unittest.TestCase):
    def test_worked_example_pump_flow(self):
        # 180 + 15 = 195 L/min = 0.00325 m3/s
        res = hsl.pump_flow(45.0, N_ACTUATORS, N_SIMULTANEOUS, LEAKAGE_LPM)
        self.assertAlmostEqual(res["simultaneous_lpm"], 180.0, places=6)
        self.assertAlmostEqual(res["pump_flow_lpm"], 195.0, places=6)
        self.assertAlmostEqual(res["pump_flow_m3s"], 0.00325, places=9)

    def test_zero_leakage_is_simultaneous_demand(self):
        res = hsl.pump_flow(45.0, N_ACTUATORS, N_SIMULTANEOUS, 0.0)
        self.assertAlmostEqual(res["pump_flow_lpm"], 180.0, places=6)
        self.assertAlmostEqual(res["pump_flow_m3s"], 0.003, places=9)

    def test_negative_leakage_raises(self):
        with self.assertRaises(ValueError):
            hsl.pump_flow(45.0, N_ACTUATORS, N_SIMULTANEOUS, -1.0)

    def test_simultaneous_exceeding_actuators_raises(self):
        with self.assertRaises(ValueError):
            hsl.pump_flow(45.0, 4, 5, LEAKAGE_LPM)

    def test_non_positive_actuator_count_raises(self):
        with self.assertRaises(ValueError):
            hsl.pump_flow(45.0, 0, 0, LEAKAGE_LPM)

    def test_dict_keys_exact(self):
        res = hsl.pump_flow(45.0, N_ACTUATORS, N_SIMULTANEOUS)
        self.assertEqual(
            sorted(res),
            ["pump_flow_lpm", "pump_flow_m3s", "simultaneous_lpm"])


class PumpPowerTest(unittest.TestCase):
    def test_worked_example_power(self):
        # 20.6843 MPa * 0.00325 / 0.85 = 79087 W = 79.0869 kW
        res = hsl.pump_power(PRESSURE_PSI, 0.00325, EFFICIENCY)
        self.assertAlmostEqual(res["pressure_pa"], 20684271.0, places=-1)
        self.assertAlmostEqual(res["pressure_mpa"], 20.6843, places=4)
        self.assertAlmostEqual(res["power_w"], 79087.0, delta=1.0)
        self.assertAlmostEqual(res["power_kw"], 79.0869, places=4)

    def test_unit_efficiency_is_pressure_times_flow(self):
        res = hsl.pump_power(PRESSURE_PSI, 0.00325, 1.0)
        self.assertAlmostEqual(res["power_w"], 20684271.0 * 0.00325,
                               places=4)

    def test_half_efficiency_doubles_power(self):
        base = hsl.pump_power(PRESSURE_PSI, 0.00325, 1.0)["power_w"]
        res = hsl.pump_power(PRESSURE_PSI, 0.00325, 0.5)["power_w"]
        self.assertAlmostEqual(res, 2.0 * base, places=4)

    def test_out_of_range_efficiency_raises(self):
        with self.assertRaises(ValueError):
            hsl.pump_power(PRESSURE_PSI, 0.00325, 0.0)
        with self.assertRaises(ValueError):
            hsl.pump_power(PRESSURE_PSI, 0.00325, 1.5)

    def test_non_positive_pressure_or_flow_raises(self):
        with self.assertRaises(ValueError):
            hsl.pump_power(0.0, 0.00325, EFFICIENCY)
        with self.assertRaises(ValueError):
            hsl.pump_power(PRESSURE_PSI, -0.00325, EFFICIENCY)

    def test_dict_keys_exact(self):
        res = hsl.pump_power(PRESSURE_PSI, 0.00325, EFFICIENCY)
        self.assertEqual(
            sorted(res),
            ["power_kw", "power_w", "pressure_mpa", "pressure_pa"])


class AccumulatorVolumesTest(unittest.TestCase):
    def test_worked_example_volumes(self):
        # ratio 1.64067, V1 = 1.0 / 0.64067 = 1.5609 L, V2 = 2.5609 L
        res = hsl.accumulator_volumes(CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        self.assertAlmostEqual(res["charged_gas_volume_l"], 1.5609,
                               places=4)
        self.assertAlmostEqual(res["depleted_gas_volume_l"], 2.5609,
                               places=4)

    def test_closure_matches_zero_on_worked_case(self):
        res = hsl.accumulator_volumes(CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        self.assertAlmostEqual(res["closure_check"], 0.0, delta=1e-9)

    def test_closure_identity_on_second_pair(self):
        # 4000/2000 psi, 2 L usable: p1 V1^n == p2 V2^n to 1e-9 relative
        res = hsl.accumulator_volumes(4000.0, 2000.0, 2.0)
        v1 = res["charged_gas_volume_l"]
        v2 = res["depleted_gas_volume_l"]
        lhs = 4000.0 * hsl.PSI_PA * ((v1 / 1000.0) ** hsl.GAS_ADIABATIC_DEFAULT)
        rhs = 2000.0 * hsl.PSI_PA * ((v2 / 1000.0) ** hsl.GAS_ADIABATIC_DEFAULT)
        self.assertLess(res["closure_check"], 1e-9 * lhs)
        self.assertAlmostEqual(lhs / rhs, 1.0, places=9)

    def test_volumes_differ_by_usable_volume(self):
        res = hsl.accumulator_volumes(4000.0, 2000.0, 2.0)
        self.assertAlmostEqual(
            res["depleted_gas_volume_l"] - res["charged_gas_volume_l"],
            2.0, places=9)

    def test_isothermal_case_n_equal_one(self):
        # n = 1: ratio = p1/p2 = 2, V1 = usable, V2 = 2 * usable
        res = hsl.accumulator_volumes(CHARGED_PSI, DEPLETED_PSI, USABLE_L, 1.0)
        self.assertAlmostEqual(res["charged_gas_volume_l"], 1.0, places=9)
        self.assertAlmostEqual(res["depleted_gas_volume_l"], 2.0, places=9)
        self.assertAlmostEqual(res["closure_check"], 0.0, delta=1e-9)

    def test_depleted_at_or_above_charged_raises(self):
        with self.assertRaises(ValueError):
            hsl.accumulator_volumes(3000.0, 3000.0, USABLE_L)
        with self.assertRaises(ValueError):
            hsl.accumulator_volumes(1500.0, 3000.0, USABLE_L)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            hsl.accumulator_volumes(3000.0, 1500.0, 0.0)
        with self.assertRaises(ValueError):
            hsl.accumulator_volumes(0.0, 1500.0, USABLE_L)
        with self.assertRaises(ValueError):
            hsl.accumulator_volumes(3000.0, 1500.0, USABLE_L, -1.4)

    def test_dict_keys_exact(self):
        res = hsl.accumulator_volumes(CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        self.assertEqual(
            sorted(res),
            ["charged_gas_volume_l", "closure_check",
             "depleted_gas_volume_l"])


class ReservoirVolumeTest(unittest.TestCase):
    def test_worked_example_reservoir(self):
        # 15 L/min * 2 min * 1.2 = 36.0 L
        self.assertAlmostEqual(
            hsl.reservoir_volume(LEAKAGE_LPM, 2.0, 1.2), 36.0, places=6)

    def test_unity_margin_short_hold_is_leakage(self):
        self.assertAlmostEqual(
            hsl.reservoir_volume(LEAKAGE_LPM, 1.0, 1.0), LEAKAGE_LPM,
            places=6)

    def test_margin_below_one_raises(self):
        with self.assertRaises(ValueError):
            hsl.reservoir_volume(LEAKAGE_LPM, 2.0, 0.99)

    def test_non_positive_leakage_or_hold_raises(self):
        with self.assertRaises(ValueError):
            hsl.reservoir_volume(0.0, 2.0, 1.2)
        with self.assertRaises(ValueError):
            hsl.reservoir_volume(LEAKAGE_LPM, -2.0, 1.2)


class SummaryAndDeterminismTest(unittest.TestCase):
    def test_summary_matches_individual_calls(self):
        s = hsl.hydraulic_system_summary(
            AREA_M2, SPEED_M_S, N_ACTUATORS, N_SIMULTANEOUS, PRESSURE_PSI,
            EFFICIENCY, CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        self.assertAlmostEqual(s["flow_lpm"], 45.0, places=6)
        self.assertAlmostEqual(s["simultaneous_lpm"], 180.0, places=6)
        self.assertAlmostEqual(s["pump_flow_lpm"], 195.0, places=6)
        self.assertAlmostEqual(s["pump_flow_m3s"], 0.00325, places=9)
        self.assertAlmostEqual(s["power_kw"], 79.0869, places=4)
        self.assertAlmostEqual(s["charged_gas_volume_l"], 1.5609, places=4)
        self.assertAlmostEqual(s["depleted_gas_volume_l"], 2.5609, places=4)
        self.assertAlmostEqual(s["reservoir_volume_l"], 36.0, places=6)
        self.assertAlmostEqual(s["closure_check"], 0.0, delta=1e-9)

    def test_summary_contains_all_documented_keys(self):
        s = hsl.hydraulic_system_summary(
            AREA_M2, SPEED_M_S, N_ACTUATORS, N_SIMULTANEOUS, PRESSURE_PSI,
            EFFICIENCY, CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        self.assertEqual(len(s), 13)
        self.assertEqual(
            sorted(s),
            ["charged_gas_volume_l", "closure_check",
             "depleted_gas_volume_l", "flow_lpm", "flow_m3s", "power_kw",
             "power_w", "pressure_mpa", "pressure_pa", "pump_flow_lpm",
             "pump_flow_m3s", "reservoir_volume_l", "simultaneous_lpm"])

    def test_deterministic_run_to_run(self):
        # Identical floats run to run: no RNG anywhere in the module.
        a1 = hsl.accumulator_volumes(CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        a2 = hsl.accumulator_volumes(CHARGED_PSI, DEPLETED_PSI, USABLE_L)
        self.assertEqual(a1, a2)
        f1 = hsl.actuator_flow(AREA_M2, SPEED_M_S)
        f2 = hsl.actuator_flow(AREA_M2, SPEED_M_S)
        self.assertEqual(f1, f2)


if __name__ == "__main__":
    unittest.main()

"""Contract tests for spacecraft-battery-sizing (space-systems/subsystems).

Offline, deterministic, stdlib only. Run from the repo root:

    python3 skills/space-systems/subsystems/spacecraft-battery-sizing/scripts/test_spacecraft_battery_sizing.py

Asserts the wave-29 spec worked example (LEO spacecraft, 1200 W eclipse
load for 35 min, DOD limit 0.40, discharge efficiency 0.95, 28 V bus,
3.7 V / 50 Ah Li-ion cells, cell max C-rate 1.0) within the stated
tolerances: 700.0 Wh eclipse energy, 1842.1 Wh required capacity,
65.8 Ah, series 8 / parallel 2 / total 16 cells, 29.6 V pack, 100 Ah
installed, 0.429 C-rate within limit, 12.28 kg mass; the 800 W second
case (466.7 Wh, 1228.1 Wh); the exceed-limit verdict; ceil behavior on
both layout axes; and ValueError rejection of non-physical inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spacecraft_battery_sizing_logic import (  # noqa: E402
    CELL_AMPHOUR,
    CELL_VOLTAGE,
    EFF_DISCHARGE,
    SPEC_ENERGY_WH_KG,
    battery_mass_kg,
    capacity_ah,
    cell_layout,
    discharge_rate_check,
    eclipse_energy_wh,
    required_capacity_wh,
    size_battery,
)

E_WORKED = 1842.1052631578948  # 700.0 / (0.40 * 0.95), exact float chain


class TestEclipseEnergy(unittest.TestCase):
    def test_leo_anchor_700_wh(self):
        self.assertAlmostEqual(eclipse_energy_wh(1200, 2100), 700.0, delta=0.1)

    def test_minute_conversion_scaling(self):
        self.assertAlmostEqual(eclipse_energy_wh(600, 1800), 300.0, delta=0.1)
        self.assertEqual(eclipse_energy_wh(0.0, 2100), 0.0)

    def test_nonphysical_inputs_rejected(self):
        for load in (-1.0,):
            with self.assertRaises(ValueError):
                eclipse_energy_wh(load, 2100)
        for duration in (0.0, -300.0):
            with self.assertRaises(ValueError):
                eclipse_energy_wh(1200, duration)


class TestRequiredCapacity(unittest.TestCase):
    def test_leo_anchor_1842_1_wh(self):
        self.assertAlmostEqual(
            required_capacity_wh(700.0, 0.40, 0.95), 1842.1, delta=0.1)

    def test_default_efficiency_matches_module_constant(self):
        self.assertAlmostEqual(
            required_capacity_wh(700.0, 0.40), E_WORKED, delta=0.1)
        self.assertEqual(EFF_DISCHARGE, 0.95)

    def test_dod_upper_bound_allowed(self):
        self.assertAlmostEqual(
            required_capacity_wh(700.0, 1.0, 0.95), 736.8421, delta=0.1)
        self.assertAlmostEqual(
            required_capacity_wh(700.0, 0.01, 0.95), 73684.2105, delta=1.0)

    def test_energy_round_trip_identity(self):
        dod, eff = 0.40, 0.95
        e = 700.0
        self.assertAlmostEqual(
            required_capacity_wh(e, dod, eff) * dod * eff, e, delta=0.01)

    def test_zero_dod_rejected(self):
        with self.assertRaises(ValueError):
            required_capacity_wh(700.0, 0.0)

    def test_dod_over_one_rejected(self):
        with self.assertRaises(ValueError):
            required_capacity_wh(700.0, 1.2)

    def test_out_of_range_efficiency_rejected(self):
        for eff in (0.0, -0.5, 1.1):
            with self.assertRaises(ValueError):
                required_capacity_wh(700.0, 0.4, eff)

    def test_negative_energy_rejected(self):
        with self.assertRaises(ValueError):
            required_capacity_wh(-100.0, 0.4)


class TestCapacityAh(unittest.TestCase):
    def test_leo_anchor_65_8_ah(self):
        self.assertAlmostEqual(
            capacity_ah(E_WORKED, 28.0), 65.8, delta=0.1)

    def test_bus_round_trip_identity(self):
        wh = E_WORKED
        self.assertAlmostEqual(capacity_ah(wh, 28.0) * 28.0, wh, delta=0.01)
        self.assertEqual(capacity_ah(0.0, 28.0), 0.0)

    def test_nonpositive_bus_voltage_rejected(self):
        with self.assertRaises(ValueError):
            capacity_ah(1000.0, 0.0)
        with self.assertRaises(ValueError):
            capacity_ah(1000.0, -28.0)


class TestCellLayout(unittest.TestCase):
    def test_leo_anchor_series_parallel_total(self):
        layout = cell_layout(E_WORKED, 28.0, 3.7, 50.0)
        self.assertEqual(layout["n_series"], 8)
        self.assertEqual(layout["n_parallel"], 2)
        self.assertEqual(layout["total_cells"], 16)

    def test_leo_anchor_pack_voltage_29_6_v(self):
        layout = cell_layout(E_WORKED, 28.0, 3.7, 50.0)
        self.assertAlmostEqual(
            layout["pack_nominal_voltage"], 29.6, delta=0.01)

    def test_leo_anchor_installed_100_ah(self):
        layout = cell_layout(E_WORKED, 28.0, 3.7, 50.0)
        self.assertAlmostEqual(
            layout["installed_capacity_ah"], 100.0, delta=0.01)

    def test_series_ceil_rounds_up(self):
        # 30 V / 3.7 V = 8.11, ceil gives 9 series cells.
        layout = cell_layout(E_WORKED, 30.0, 3.7, 50.0)
        self.assertEqual(layout["n_series"], 9)
        self.assertAlmostEqual(
            layout["pack_nominal_voltage"], 33.3, delta=0.01)

    def test_parallel_ceil_rounds_up(self):
        # 4000 Wh at 28 V = 142.86 Ah, ceil / 50 Ah gives 3 parallel.
        layout = cell_layout(4000.0, 28.0, 3.7, 50.0)
        self.assertEqual(layout["n_parallel"], 3)
        self.assertEqual(layout["total_cells"], 24)
        self.assertAlmostEqual(
            layout["installed_capacity_ah"], 150.0, delta=0.01)

    def test_exact_multiples_do_not_round_up(self):
        # 2800 Wh at 28 V is exactly 100 Ah, exactly 2 parallel strings.
        layout = cell_layout(2800.0, 28.0, 3.7, 50.0)
        self.assertEqual(layout["n_parallel"], 2)
        self.assertEqual(layout["total_cells"], 16)
        # 8 V / 2 V is exactly 4 series cells.
        exact = cell_layout(2800.0, 8.0, 2.0, 50.0)
        self.assertEqual(exact["n_series"], 4)

    def test_nonpositive_inputs_rejected(self):
        with self.assertRaises(ValueError):
            cell_layout(0.0, 28.0, 3.7, 50.0)
        with self.assertRaises(ValueError):
            cell_layout(E_WORKED, 0.0, 3.7, 50.0)
        with self.assertRaises(ValueError):
            cell_layout(E_WORKED, 28.0, 0.0, 50.0)
        with self.assertRaises(ValueError):
            cell_layout(E_WORKED, 28.0, 3.7, 0.0)
        with self.assertRaises(ValueError):
            cell_layout(-E_WORKED, 28.0, 3.7, 50.0)


class TestDischargeRateCheck(unittest.TestCase):
    def test_leo_anchor_current_and_c_rate(self):
        result = discharge_rate_check(1200.0, 28.0, 100.0, 1.0)
        self.assertAlmostEqual(result["current_A"], 42.86, delta=0.01)
        self.assertAlmostEqual(result["c_rate"], 0.429, delta=0.001)
        self.assertTrue(result["within_limit"])

    def test_800w_50ah_bank_pass(self):
        result = discharge_rate_check(800.0, 28.0, 50.0, 1.0)
        self.assertAlmostEqual(result["c_rate"], 0.57, delta=0.01)
        self.assertTrue(result["within_limit"])

    def test_2000w_50ah_bank_exceeds_limit(self):
        result = discharge_rate_check(2000.0, 28.0, 50.0, 1.0)
        self.assertAlmostEqual(result["c_rate"], 1.43, delta=0.01)
        self.assertFalse(result["within_limit"])

    def test_at_limit_is_within(self):
        # 1400 W at 28 V draws exactly 50 A on a 50 Ah bank, C-rate 1.0.
        result = discharge_rate_check(1400.0, 28.0, 50.0, 1.0)
        self.assertAlmostEqual(result["c_rate"], 1.0, delta=1e-9)
        self.assertTrue(result["within_limit"])

    def test_nonpositive_inputs_rejected(self):
        with self.assertRaises(ValueError):
            discharge_rate_check(0.0, 28.0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            discharge_rate_check(1200.0, 0.0, 100.0, 1.0)
        with self.assertRaises(ValueError):
            discharge_rate_check(1200.0, 28.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            discharge_rate_check(1200.0, 28.0, 100.0, 0.0)


class TestBatteryMass(unittest.TestCase):
    def test_leo_anchor_12_28_kg(self):
        self.assertAlmostEqual(
            battery_mass_kg(E_WORKED, 150.0), 12.28, delta=0.01)
        self.assertEqual(SPEC_ENERGY_WH_KG, 150.0)
        self.assertAlmostEqual(
            battery_mass_kg(E_WORKED), 12.28, delta=0.01)

    def test_custom_density_scaling(self):
        self.assertAlmostEqual(
            battery_mass_kg(E_WORKED, 300.0), 6.14, delta=0.01)

    def test_nonpositive_density_rejected(self):
        with self.assertRaises(ValueError):
            battery_mass_kg(1000.0, 0.0)
        with self.assertRaises(ValueError):
            battery_mass_kg(1000.0, -150.0)
        with self.assertRaises(ValueError):
            battery_mass_kg(-1000.0, 150.0)


class TestSizeBattery(unittest.TestCase):
    def test_leo_worked_example_summary(self):
        result = size_battery(1200.0, 2100.0, 0.40, 28.0)
        self.assertEqual(CELL_VOLTAGE, 3.7)
        self.assertEqual(CELL_AMPHOUR, 50.0)
        self.assertAlmostEqual(
            size_battery(1200.0, 2100.0, 0.40, 28.0, 3.7, 50.0, 1.0)[
                "mass_kg"],
            result["mass_kg"],
            delta=1e-9)
        self.assertAlmostEqual(result["eclipse_energy_wh"], 700.0, delta=0.1)
        self.assertAlmostEqual(
            result["required_capacity_wh"], 1842.1, delta=0.1)
        self.assertAlmostEqual(result["capacity_ah"], 65.8, delta=0.1)
        self.assertEqual(result["n_series"], 8)
        self.assertEqual(result["n_parallel"], 2)
        self.assertEqual(result["total_cells"], 16)
        self.assertAlmostEqual(result["mass_kg"], 12.28, delta=0.01)
        self.assertEqual(result["discharge_verdict"], "within-cell-limit")

    def test_second_case_800w_35min_eclipse(self):
        # 90 min LEO orbit with a 35 min eclipse at 800 W.
        result = size_battery(800.0, 2100.0, 0.40, 28.0)
        self.assertAlmostEqual(result["eclipse_energy_wh"], 466.7, delta=0.1)
        self.assertAlmostEqual(
            result["required_capacity_wh"], 1228.1, delta=0.1)
        self.assertEqual(result["discharge_verdict"], "within-cell-limit")

    def test_exceed_limit_verdict(self):
        # Higher draw outruns a low cell C-rate limit.
        result = size_battery(2000.0, 2100.0, 0.40, 28.0,
                              cell_max_c_rate=0.4)
        self.assertEqual(result["discharge_verdict"], "exceeds-cell-limit")

    def test_invalid_dod_propagates(self):
        with self.assertRaises(ValueError):
            size_battery(1200.0, 2100.0, 0.0, 28.0)
        with self.assertRaises(ValueError):
            size_battery(1200.0, 2100.0, 0.40, 0.0)


if __name__ == "__main__":
    unittest.main()

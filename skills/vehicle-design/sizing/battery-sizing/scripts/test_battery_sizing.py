"""Deterministic contract test for battery sizing (stdlib unittest, offline).

Run: python3 scripts/test_battery_sizing.py
Covers the wave-26 spec worked-example anchors, boundary behavior, and
ValueError rejection of non-physical inputs.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import battery_sizing_logic as b

CELL = dict(voltage_nom_v=3.7, capacity_ah=5.0, r_internal_ohm=0.002,
            v_cutoff_min_v=3.0, max_c_rate=4.0)


class TestRequiredPackEnergy(unittest.TestCase):
    def test_worked_example_78_947_kwh(self):
        v = b.required_pack_energy(50, 0.2)
        self.assertAlmostEqual(v, 50 * 1.2 / (b.DOD_MAX * b.EFF_DISCHARGE), places=6)
        self.assertAlmostEqual(v, 78.94736842105263, places=6)
        self.assertAlmostEqual(round(v, 3), 78.947, places=6)

    def test_no_reserve_and_scaling(self):
        self.assertAlmostEqual(b.required_pack_energy(50, 0.0), 50 / 0.76, places=6)
        self.assertGreater(b.required_pack_energy(50, 0.3),
                           b.required_pack_energy(50, 0.1))

    def test_valueerror_nonpositive_energy(self):
        with self.assertRaises(ValueError):
            b.required_pack_energy(-1, 0.2)
        with self.assertRaises(ValueError):
            b.required_pack_energy(0, 0.2)

    def test_valueerror_negative_reserve(self):
        with self.assertRaises(ValueError):
            b.required_pack_energy(50, -0.1)


class TestSeriesCells(unittest.TestCase):
    def test_worked_example_108(self):
        self.assertEqual(b.series_cells(400, CELL), 108)

    def test_rounding_and_exact_division(self):
        cell = dict(CELL, voltage_nom_v=2.0)
        self.assertEqual(b.series_cells(217, cell), 109)  # 108.5 rounds up
        self.assertEqual(b.series_cells(400, cell), 200)

    def test_valueerror_nonpositive_target(self):
        with self.assertRaises(ValueError):
            b.series_cells(0, CELL)
        with self.assertRaises(ValueError):
            b.series_cells(-400, CELL)

    def test_valueerror_bad_cell_voltage(self):
        cell = dict(CELL, voltage_nom_v=0.0)
        with self.assertRaises(ValueError):
            b.series_cells(400, cell)


class TestParallelCells(unittest.TestCase):
    def test_worked_example_40(self):
        req = b.required_pack_energy(50, 0.2)
        self.assertEqual(b.parallel_cells(req, 108, CELL), 40)

    def test_ceiling_rounds_up(self):
        req = b.required_pack_energy(50, 0.2)
        cell = dict(CELL, capacity_ah=10.0)  # 78947 / (108*3.7*10) = 19.76
        self.assertEqual(b.parallel_cells(req, 108, cell), 20)

    def test_exact_multiple(self):
        self.assertEqual(b.parallel_cells(39.96, 108, CELL), 20)

    def test_valueerrors(self):
        req = b.required_pack_energy(50, 0.2)
        with self.assertRaises(ValueError):
            b.parallel_cells(0, 108, CELL)
        with self.assertRaises(ValueError):
            b.parallel_cells(req, 0, CELL)
        cell = dict(CELL, capacity_ah=0.0)
        with self.assertRaises(ValueError):
            b.parallel_cells(req, 108, cell)


class TestPackEnergy(unittest.TestCase):
    def test_worked_example_79_92_kwh_and_scaling(self):
        self.assertAlmostEqual(b.pack_energy_kwh(108, 40, CELL), 79.92, places=6)
        self.assertAlmostEqual(b.pack_energy_kwh(108, 1, CELL), 1.998, places=6)

    def test_valueerror_nonpositive_counts(self):
        with self.assertRaises(ValueError):
            b.pack_energy_kwh(0, 40, CELL)
        with self.assertRaises(ValueError):
            b.pack_energy_kwh(108, -2, CELL)


class TestEnergyMargin(unittest.TestCase):
    def test_worked_example_pass(self):
        m = b.energy_margin(79.92, 50, 0.2)
        self.assertAlmostEqual(m["usable_kwh"], 60.7392, places=4)
        self.assertAlmostEqual(m["required_kwh"], 60.0, places=6)
        self.assertAlmostEqual(m["margin_kwh"], 0.7392, places=4)
        self.assertGreaterEqual(m["usable_kwh"], 60.0)
        self.assertTrue(m["pass"])

    def test_short_pack_fails_and_valueerror(self):
        m = b.energy_margin(70.0, 50, 0.2)
        self.assertFalse(m["pass"])
        self.assertLess(m["margin_kwh"], 0)
        with self.assertRaises(ValueError):
            b.energy_margin(0, 50, 0.2)


class TestCRateCheck(unittest.TestCase):
    def test_400kw_fails_against_4c(self):
        r = b.c_rate_check(400, 79.92, CELL)
        self.assertAlmostEqual(r["c_rate"], 400 / 79.92, places=6)
        self.assertEqual(round(r["c_rate"], 2), 5.01)
        self.assertEqual(r["limit"], 4.0)
        self.assertFalse(r["pass"])

    def test_300kw_passes(self):
        r = b.c_rate_check(300, 79.92, CELL)
        self.assertEqual(round(r["c_rate"], 2), 3.75)
        self.assertTrue(r["pass"])

    def test_at_limit_passes_and_valueerror(self):
        r = b.c_rate_check(400, 100.0, CELL)  # exactly 4.0 C against the 4 C limit
        self.assertAlmostEqual(r["c_rate"], 4.0, places=6)
        self.assertTrue(r["pass"])
        with self.assertRaises(ValueError):
            b.c_rate_check(0, 79.92, CELL)
        with self.assertRaises(ValueError):
            b.c_rate_check(-400, 79.92, CELL)


class TestVoltageDropCheck(unittest.TestCase):
    def test_worked_example(self):
        r = b.voltage_drop_check(400, 108, 40, CELL, 399.6)
        self.assertAlmostEqual(r["i_total_a"], 1001.0, delta=0.5)
        self.assertAlmostEqual(r["i_branch_a"], 25.0, delta=0.05)
        self.assertAlmostEqual(r["drop_v"], 0.05, places=3)
        self.assertAlmostEqual(r["v_min_cell_v"], 3.65, places=3)
        self.assertGreaterEqual(r["v_min_cell_v"], 3.0)
        self.assertTrue(r["pass"])

    def test_high_resistance_fails_and_parallel_reduces_drop(self):
        cell = dict(CELL, r_internal_ohm=0.05)
        r = b.voltage_drop_check(400, 108, 40, cell, 399.6)
        self.assertFalse(r["pass"])
        self.assertLess(r["v_min_cell_v"], 3.0)
        r1 = b.voltage_drop_check(400, 108, 20, CELL, 399.6)
        r2 = b.voltage_drop_check(400, 108, 40, CELL, 399.6)
        self.assertGreater(r1["drop_v"], r2["drop_v"])

    def test_valueerrors(self):
        with self.assertRaises(ValueError):
            b.voltage_drop_check(0, 108, 40, CELL, 399.6)
        with self.assertRaises(ValueError):
            b.voltage_drop_check(400, 108, 40, CELL, 0)


class TestMassVolumeThermal(unittest.TestCase):
    def test_mass_worked_example(self):
        m = b.mass_estimate(79.92)
        self.assertAlmostEqual(m["cell_mass_kg"], 319.7, places=1)
        self.assertAlmostEqual(m["cell_mass_kg"], 319.68, places=3)
        self.assertAlmostEqual(m["pack_mass_kg"], 444.0, places=6)
        self.assertGreater(m["pack_mass_kg"], m["cell_mass_kg"])

    def test_volume_worked_example_and_valueerrors(self):
        v = b.volume_estimate(79.92)
        self.assertAlmostEqual(v["cell_volume_L"], 145.31, places=1)
        self.assertAlmostEqual(v["pack_volume_L"], 266.4, places=3)
        with self.assertRaises(ValueError):
            b.mass_estimate(0)
        with self.assertRaises(ValueError):
            b.volume_estimate(-5)

    def test_thermal_estimate_and_valueerrors(self):
        self.assertAlmostEqual(b.thermal_estimate(400, 1.0), 20.0, places=6)
        self.assertAlmostEqual(b.thermal_estimate(300, 0.5), 7.5, places=6)
        with self.assertRaises(ValueError):
            b.thermal_estimate(0, 1.0)
        with self.assertRaises(ValueError):
            b.thermal_estimate(400, -1.0)


class TestSizeBattery(unittest.TestCase):
    def test_overall_fail_at_400kw_with_c_rate_reason(self):
        r = b.size_battery(50, 0.2, 400, 400, CELL)
        self.assertFalse(r["verdict"]["pass"])
        self.assertTrue(any("C-rate" in reason for reason in r["verdict"]["reasons"]))

    def test_overall_pass_at_300kw(self):
        r = b.size_battery(50, 0.2, 300, 400, CELL)
        self.assertTrue(r["verdict"]["pass"])
        self.assertEqual(r["verdict"]["reasons"], [])
        self.assertTrue(r["energy"]["pass"])
        self.assertTrue(r["c_rate"]["pass"])
        self.assertTrue(r["voltage_drop"]["pass"])

    def test_output_fields(self):
        r = b.size_battery(50, 0.2, 300, 400, CELL)
        self.assertEqual(r["n_series"], 108)
        self.assertEqual(r["n_parallel"], 40)
        self.assertAlmostEqual(r["pack_energy_kwh"], 79.92, places=6)
        self.assertAlmostEqual(r["e_pack_req_kwh"], 78.947, places=3)
        self.assertAlmostEqual(r["nominal_pack_v"], 399.6, places=6)

    def test_valueerror_zero_mission_energy(self):
        with self.assertRaises(ValueError):
            b.size_battery(0, 0.2, 400, 400, CELL)

    def test_valueerror_bad_cell_keys(self):
        cell = dict(CELL)
        del cell["max_c_rate"]
        with self.assertRaises(ValueError):
            b.size_battery(50, 0.2, 400, 400, cell)
        bad = dict(CELL, chemistry="nmc")
        with self.assertRaises(ValueError):
            b.size_battery(50, 0.2, 400, 400, bad)

    def test_roundtrip_energy_identity(self):
        # A zero-reserve mission must end with usable energy >= mission draw.
        r = b.size_battery(50, 0.0, 100, 400, CELL)
        self.assertGreaterEqual(r["energy"]["usable_kwh"], 50.0)
        self.assertGreaterEqual(r["pack_energy_kwh"], r["e_pack_req_kwh"])


if __name__ == "__main__":
    unittest.main()

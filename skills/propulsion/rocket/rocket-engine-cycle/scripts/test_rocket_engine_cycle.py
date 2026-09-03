"""Contract test for rocket_engine_cycle_logic (rocket-engine-cycle leaf).

Deterministic, offline, stdlib only. Run: python3 test_rocket_engine_cycle.py
"""

import unittest

import rocket_engine_cycle_logic as rec

G0 = rec.G0


class TestPropellantTable(unittest.TestCase):
    def test_propellant_table_values(self):
        self.assertEqual(rec.propellant_pair_properties("LOX/RP-1"),
                         (1140.0, 820.0, 2.56, 300.0))
        self.assertEqual(rec.propellant_pair_properties("LOX/LH2"),
                         (1140.0, 71.0, 5.5, 430.0))
        self.assertEqual(rec.propellant_pair_properties("N2O4/MMH"),
                         (1450.0, 880.0, 1.9, 320.0))
        rho_ox, rho_fuel, r_m, isp = rec.propellant_pair_properties("hydrazine")
        self.assertEqual((rho_ox, rho_fuel, isp), (1010.0, 1010.0, 230.0))
        self.assertIsNone(r_m)

    def test_unknown_propellant_raises(self):
        for bad in ("kerosene", "xenon", "", None):
            with self.assertRaises(ValueError):
                rec.propellant_pair_properties(bad)


class TestMassFlowSplit(unittest.TestCase):
    def test_worked_example_mass_flows(self):
        mdot, mdot_ox, mdot_f = rec.mass_flow_split(1.0e6, 300.0, G0, 2.56)
        self.assertAlmostEqual(mdot, 339.9054043259761, delta=1e-6)
        self.assertAlmostEqual(mdot_ox, 244.42635816699405, delta=1e-6)
        self.assertAlmostEqual(mdot_f, 95.47904615898206, delta=1e-6)

    def test_split_identities(self):
        mdot, mdot_ox, mdot_f = rec.mass_flow_split(2.5e5, 320.0, G0, 1.9)
        self.assertAlmostEqual(mdot_ox + mdot_f, mdot, delta=1e-9)
        self.assertAlmostEqual(mdot_ox / mdot_f, 1.9, delta=1e-9)
        mono_mdot, mono_ox, mono_f = rec.mass_flow_split(1.0e4, 230.0, G0, None)
        self.assertEqual(mono_f, 0.0)
        self.assertAlmostEqual(mono_ox, mono_mdot, delta=1e-12)

    def test_nonpositive_inputs_raise(self):
        for f, isp in ((0.0, 300.0), (-5.0, 300.0), (1.0e6, 0.0),
                       (1.0e6, -300.0), (float("nan"), 300.0),
                       (1.0e6, float("inf"))):
            with self.assertRaises(ValueError):
                rec.mass_flow_split(f, isp, G0, 2.56)
        with self.assertRaises(ValueError):
            rec.mass_flow_split(1.0e6, 300.0, G0, -2.0)


class TestPumpSide(unittest.TestCase):
    def test_pump_discharge_pressure(self):
        self.assertEqual(rec.pump_discharge_pressure(10.0e6, 2.0e6), 12.0e6)
        self.assertEqual(rec.pump_discharge_pressure(3.0e6, 1.0e6), 4.0e6)

    def test_worked_example_pump_powers_within_anchors(self):
        p_ox = rec.pump_power(244.42635816699405, 12.0e6, 0.3e6, 1140.0, 0.7)
        p_f = rec.pump_power(95.47904615898206, 12.0e6, 0.3e6, 820.0, 0.7)
        self.assertAlmostEqual(p_ox, 3583694.7250047997, delta=1e-6)
        self.assertAlmostEqual(p_f, 1946175.6795471953, delta=1e-6)
        self.assertLess(abs(p_ox - 3.6e6) / 3.6e6, 0.10)
        self.assertLess(abs(p_f - 1.95e6) / 1.95e6, 0.10)
        self.assertLess(abs((p_ox + p_f) - 5.5e6) / 5.5e6, 0.10)

    def test_pump_power_scales_with_mass_flow(self):
        p1 = rec.pump_power(50.0, 12.0e6, 0.3e6, 1000.0, 0.7)
        p2 = rec.pump_power(100.0, 12.0e6, 0.3e6, 1000.0, 0.7)
        self.assertAlmostEqual(p2, 2.0 * p1, delta=1e-9)

    def test_pump_power_falls_as_efficiency_rises(self):
        low = rec.pump_power(100.0, 12.0e6, 0.3e6, 1000.0, 0.6)
        high = rec.pump_power(100.0, 12.0e6, 0.3e6, 1000.0, 0.9)
        self.assertLess(high, low)
        self.assertAlmostEqual(low * 0.6, high * 0.9, delta=1e-6)

    def test_pump_power_rejects_nonphysical(self):
        with self.assertRaises(ValueError):
            rec.pump_power(0.0, 12.0e6, 0.3e6, 1000.0, 0.7)
        with self.assertRaises(ValueError):
            rec.pump_power(10.0, 0.0, 0.3e6, 1000.0, 0.7)
        with self.assertRaises(ValueError):
            rec.pump_power(10.0, 12.0e6, 13.0e6, 1000.0, 0.7)
        with self.assertRaises(ValueError):
            rec.pump_power(10.0, 12.0e6, 0.3e6, -1000.0, 0.7)
        for eta in (0.0, 1.5, -0.2, float("nan")):
            with self.assertRaises(ValueError):
                rec.pump_power(10.0, 12.0e6, 0.3e6, 1000.0, eta)


class TestTurbinePower(unittest.TestCase):
    def test_gg_turbine_formula_value(self):
        mdot_gg = 0.03 * 339.9054043259761
        p = rec.turbine_power(mdot_gg, 2000.0, 1200.0, 0.6, 1.2, 8.0e6, 0.2e6)
        self.assertAlmostEqual(p, 6743706.587605928, delta=1e-6)
        self.assertGreater(p, 0.0)

    def test_turbine_power_monotonic_in_eta(self):
        p1 = rec.turbine_power(10.0, 2000.0, 1200.0, 0.5, 1.2, 8.0e6, 0.2e6)
        p2 = rec.turbine_power(10.0, 2000.0, 1200.0, 0.8, 1.2, 8.0e6, 0.2e6)
        self.assertLess(p1, p2)

    def test_turbine_power_rejects_nonphysical(self):
        with self.assertRaises(ValueError):
            rec.turbine_power(0.0, 2000.0, 1200.0, 0.6, 1.2, 8.0e6, 0.2e6)
        with self.assertRaises(ValueError):
            rec.turbine_power(10.0, 2000.0, 1200.0, 0.6, 1.2, 0.2e6, 8.0e6)
        with self.assertRaises(ValueError):
            rec.turbine_power(10.0, 2000.0, 1200.0, 0.6, 1.0, 8.0e6, 0.2e6)
        with self.assertRaises(ValueError):
            rec.turbine_power(10.0, 2000.0, -300.0, 0.6, 1.2, 8.0e6, 0.2e6)
        with self.assertRaises(ValueError):
            rec.turbine_power(10.0, 2000.0, 1200.0, 1.2, 1.2, 8.0e6, 0.2e6)


class TestFeasibility(unittest.TestCase):
    def test_gg_and_staged_feasible_across_range(self):
        for cycle in ("gas-generator", "staged-combustion"):
            for pair in ("LOX/RP-1", "LOX/LH2", "N2O4/MMH"):
                for p_c in (3.0e6, 10.0e6, 25.0e6):
                    ok, reason = rec.cycle_feasibility(cycle, pair, p_c)
                    self.assertTrue(ok, reason)

    def test_expander_rule(self):
        ok, reason = rec.cycle_feasibility("expander", "LOX/RP-1", 10.0e6)
        self.assertFalse(ok)
        self.assertIn("LH2", reason)
        ok, _ = rec.cycle_feasibility("expander", "LOX/LH2", 5.0e6)
        self.assertTrue(ok)
        ok, reason = rec.cycle_feasibility("expander", "LOX/LH2", 12.0e6)
        self.assertFalse(ok)
        self.assertIn("bound", reason)

    def test_pressure_fed_bound(self):
        ok, _ = rec.cycle_feasibility("pressure-fed", "N2O4/MMH", 2.0e6)
        self.assertTrue(ok)
        ok, reason = rec.cycle_feasibility("pressure-fed", "LOX/RP-1", 10.0e6)
        self.assertFalse(ok)
        self.assertIn("heavy", reason)

    def test_monoprop_has_no_drive_gas_split(self):
        for cycle in ("gas-generator", "staged-combustion"):
            ok, reason = rec.cycle_feasibility(cycle, "hydrazine", 2.0e6)
            self.assertFalse(ok)
            self.assertIn("oxidizer/fuel", reason)
        ok, reason = rec.cycle_feasibility("expander", "hydrazine", 2.0e6)
        self.assertFalse(ok)
        self.assertIn("LH2", reason)

    def test_unknown_cycle_raises(self):
        for cycle in ("nuclear-thermal", "electric", ""):
            with self.assertRaises(ValueError):
                rec.cycle_feasibility(cycle, "LOX/RP-1", 10.0e6)

    def test_matrix_is_deterministic(self):
        for cycle in rec.CYCLES:
            for pair in rec.PROPELLANTS:
                for p_c in (1.0e6, 5.0e6, 10.0e6):
                    self.assertEqual(rec.cycle_feasibility(cycle, pair, p_c),
                                     rec.cycle_feasibility(cycle, pair, p_c))


class TestTankMass(unittest.TestCase):
    def test_high_pressure_penalty_is_heavy(self):
        mdot, _, _ = rec.mass_flow_split(1.0e6, 300.0, G0, 2.56)
        bulk = rec.mixture_bulk_density(1140.0, 820.0, 2.56)
        vol = 60.0 * mdot / bulk
        heavy = rec.pressure_fed_tank_mass(12.0e6, vol)
        light = rec.pressure_fed_tank_mass(0.3e6, vol)
        self.assertGreater(heavy, 20.0 * light)
        self.assertAlmostEqual(heavy, 599.5848994585923, delta=1e-6)

    def test_tank_mass_scales_linearly_with_pressure(self):
        m1 = rec.pressure_fed_tank_mass(5.0e6, 10.0)
        m2 = rec.pressure_fed_tank_mass(10.0e6, 10.0)
        self.assertAlmostEqual(m2, 2.0 * m1, delta=1e-9)

    def test_tank_mass_rejects_nonphysical(self):
        for p_tank, vol in ((0.0, 10.0), (-4.0e6, 10.0), (4.0e6, -1.0)):
            with self.assertRaises(ValueError):
                rec.pressure_fed_tank_mass(p_tank, vol)


class TestEngineCycleAnalysis(unittest.TestCase):
    def test_gg_analysis_anchor_and_keys(self):
        r = rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6, "LOX/RP-1")
        for key in ("feasible", "pump_power_total", "turbine_power",
                    "power_balance", "drive_mass_fraction",
                    "tank_mass_penalty", "verdict"):
            self.assertIn(key, r)
        self.assertTrue(r["feasible"])
        self.assertAlmostEqual(r["mdot"], 339.9054043259761, delta=1e-6)
        self.assertAlmostEqual(r["pump_discharge_pressure"], 12.0e6, delta=1e-6)
        self.assertAlmostEqual(r["pump_power_total"], 5529870.404551995, delta=1e-6)
        self.assertAlmostEqual(r["turbine_power"], 6743706.587605928, delta=1e-6)
        self.assertAlmostEqual(r["power_balance"],
                               r["turbine_power"] - r["pump_power_total"],
                               delta=1e-6)
        self.assertGreater(r["power_balance"], 0.0)
        self.assertEqual(r["drive_mass_fraction"], 0.03)
        self.assertIn("surplus", r["verdict"])

    def test_staged_combustion_analysis_surplus(self):
        r = rec.engine_cycle_analysis("staged-combustion", 1.0e6, 10.0e6, "LOX/RP-1")
        self.assertTrue(r["feasible"])
        self.assertGreater(r["power_balance"], 0.0)
        self.assertEqual(r["drive_mass_fraction"], 1.0)

    def test_expander_rp1_analysis_infeasible(self):
        r = rec.engine_cycle_analysis("expander", 1.0e6, 10.0e6, "LOX/RP-1")
        self.assertFalse(r["feasible"])
        self.assertIn("rejected", r["verdict"])

    def test_pressure_fed_low_and_high_cases(self):
        low = rec.engine_cycle_analysis("pressure-fed", 1.0e6, 2.0e6, "N2O4/MMH")
        self.assertTrue(low["feasible"])
        self.assertEqual(low["pump_power_total"], 0.0)
        self.assertEqual(low["turbine_power"], 0.0)
        self.assertEqual(low["tank_pressure"], 4.0e6)
        self.assertGreater(low["tank_mass_penalty"], 0.0)
        self.assertIn("tank", low["verdict"])
        high = rec.engine_cycle_analysis("pressure-fed", 1.0e6, 10.0e6, "LOX/RP-1")
        self.assertFalse(high["feasible"])
        self.assertGreater(high["tank_mass_penalty"],
                           low["tank_mass_penalty"] * 3.0)

    def test_monoprop_pressure_fed_verdict(self):
        r = rec.engine_cycle_analysis("pressure-fed", 5.0e4, 2.0e6, "hydrazine")
        self.assertTrue(r["feasible"])
        self.assertEqual(r["mdot_f"], 0.0)

    def test_analysis_isp_override_changes_mdot(self):
        base = rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6, "LOX/RP-1")
        over = rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6,
                                         "LOX/RP-1", isp=310.0)
        self.assertAlmostEqual(over["mdot"], base["mdot"] * 300.0 / 310.0,
                               delta=1e-9)

    def test_analysis_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", -1.0e6, 10.0e6, "LOX/RP-1")
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", 1.0e6, 0.0, "LOX/RP-1")
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", 1.0e6, float("inf"),
                                      "LOX/RP-1")
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6, "methalox")
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("closed-loop", 1.0e6, 10.0e6, "LOX/RP-1")
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6,
                                      "LOX/RP-1", eta_pump=0.0)
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6,
                                      "LOX/RP-1", eta_turb=1.5)
        with self.assertRaises(ValueError):
            rec.engine_cycle_analysis("gas-generator", 1.0e6, 10.0e6,
                                      "LOX/RP-1", gg_fraction=0.0)


class TestModuleConstants(unittest.TestCase):
    def test_physical_constant_sanity(self):
        self.assertAlmostEqual(G0, 9.80665, delta=1e-9)
        self.assertGreater(rec.EXPANDER_MAX_P_C, rec.PRESSURE_FED_MAX_P_C)
        for value in (rec.PUMP_INLET_PRESSURE, rec.TURBINE_EXIT_PRESSURE,
                      rec.RHO_WALL, rec.SIGMA_WALL):
            self.assertGreater(value, 0.0)


if __name__ == "__main__":
    unittest.main()

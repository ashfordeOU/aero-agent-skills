#!/usr/bin/env python3
"""Gate 3 contract test: bleed air system sizing logic.

Exercises scripts/bleed_air_system_sizing_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3.
Covers the twin-engine transport worked example of the wave-36 spec
(total offtake 1.6679 kg/s, per-engine thermal budget 135775.4 W, duct
diameter 0.0554 m), the offtake and duct-area round-trip identities,
thermal budget scaling with mass flow, the summary fit verdict, dict
key contracts, determinism, and ValueError rejection of non-physical
inputs (negative flows, non-positive mass/temperature/pressure, Mach
outside (0, 1), bleed temperature at or below supply temperature).

Run: python3 scripts/test_bleed_air_system_sizing.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bleed_air_system_sizing_logic as b  # noqa: E402

PACKS = [0.80, 0.80]   # two ECS packs, kg/s each
ANTI_ICE = 0.0179      # wing anti-ice bleed demand, kg/s
TRIM = 0.05            # pressurization trim bleed demand, kg/s
T_BLEED = 450.0        # bleed supply temperature, K


class OfftakeRollupTest(unittest.TestCase):
    def test_worked_example_total_offtake(self):
        # 2*0.80 + 0.0179 + 0.05 = 1.6679 kg/s; per engine 0.83395.
        r = b.total_bleed_offtake(PACKS, ANTI_ICE, TRIM)
        self.assertAlmostEqual(r["total_kg_s"], 1.6679, places=9)
        self.assertAlmostEqual(r["per_engine_kg_s"], 0.83395, places=9)

    def test_offtake_identity_two_per_engine_equals_total(self):
        r = b.total_bleed_offtake(PACKS, ANTI_ICE, TRIM)
        self.assertAlmostEqual(2.0 * r["per_engine_kg_s"], r["total_kg_s"],
                               places=9)

    def test_offtake_keys_exact(self):
        self.assertEqual(
            set(b.total_bleed_offtake([0.5], 0.0, 0.0).keys()),
            {"total_kg_s", "per_engine_kg_s"})

    def test_single_pack_and_no_auxiliaries(self):
        r = b.total_bleed_offtake([0.4], 0.0, 0.0)
        self.assertAlmostEqual(r["total_kg_s"], 0.4, places=12)
        self.assertAlmostEqual(r["per_engine_kg_s"], 0.2, places=12)

    def test_empty_pack_list_rolls_auxiliaries_only(self):
        r = b.total_bleed_offtake([], 0.3, 0.1)
        self.assertAlmostEqual(r["total_kg_s"], 0.4, places=12)

    def test_negative_pack_flow_raises(self):
        with self.assertRaises(ValueError):
            b.total_bleed_offtake([0.8, -0.2], ANTI_ICE, TRIM)

    def test_negative_anti_ice_raises(self):
        with self.assertRaises(ValueError):
            b.total_bleed_offtake(PACKS, -0.01, TRIM)

    def test_negative_trim_raises(self):
        with self.assertRaises(ValueError):
            b.total_bleed_offtake(PACKS, ANTI_ICE, -0.01)


class ThermalBudgetTest(unittest.TestCase):
    def test_worked_example_per_engine_budget(self):
        # 0.83395 * 1005 * (450 - 288) = 135775.4 W (spec 135.8 kW).
        r = b.bleed_thermal_budget(0.83395, T_BLEED)
        self.assertAlmostEqual(r["q_w"], 135775.3995, places=3)
        self.assertAlmostEqual(r["q_w"], 135775.0, delta=0.5)

    def test_worked_example_total_budget(self):
        # 1.6679 * 1005 * 162 = 271550.8 W (spec rounds to 271551 W).
        r = b.bleed_thermal_budget(1.6679, T_BLEED)
        self.assertAlmostEqual(r["q_w"], 271550.799, places=3)
        self.assertAlmostEqual(r["q_w"], 271551.0, delta=0.5)
        # Magnitude bound: 271.6 kW class.
        self.assertLess(abs(r["q_w"] - 271551.0), 1.0)

    def test_budget_doubles_with_mass_flow(self):
        q1 = b.bleed_thermal_budget(0.5, T_BLEED)["q_w"]
        q2 = b.bleed_thermal_budget(1.0, T_BLEED)["q_w"]
        self.assertAlmostEqual(q2, 2.0 * q1, places=9)

    def test_budget_custom_supply_temperature(self):
        # Larger delta-T at fixed flow raises the budget linearly.
        q288 = b.bleed_thermal_budget(1.0, 450.0, 288.0)["q_w"]
        q298 = b.bleed_thermal_budget(1.0, 450.0, 298.0)["q_w"]
        self.assertAlmostEqual(q288 - q298, 1.0 * b.CP_AIR * 10.0, places=6)

    def test_budget_keys_exact(self):
        self.assertEqual(
            set(b.bleed_thermal_budget(1.0, 450.0).keys()),
            {"q_w", "mass_kg_s", "t_bleed_k", "t_supply_k"})

    def test_non_positive_mass_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_thermal_budget(0.0, T_BLEED)
        with self.assertRaises(ValueError):
            b.bleed_thermal_budget(-1.0, T_BLEED)

    def test_bleed_at_or_below_supply_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_thermal_budget(1.0, 288.0)     # equal
        with self.assertRaises(ValueError):
            b.bleed_thermal_budget(1.0, 200.0)     # below


class DuctSizingTest(unittest.TestCase):
    def test_worked_example_duct(self):
        # rho 2.7100 kg/m3, V 127.57 m/s, A 0.002412 m2, D 0.0554 m.
        r = b.bleed_duct_diameter(0.83395, T_BLEED)
        self.assertAlmostEqual(r["density_kg_m3"], 2.7100, places=3)
        self.assertAlmostEqual(r["velocity_m_s"], 127.57, places=2)
        self.assertAlmostEqual(r["area_m2"], 0.002412, places=6)
        self.assertAlmostEqual(r["diameter_m"], 0.0554, delta=1e-3)
        # Inside the spec magnitude bound: 55.4 mm nominal.
        self.assertLess(abs(r["diameter_m"] - 0.0554), 1e-3)

    def test_duct_area_round_trip(self):
        # A == pi * D^2 / 4 within 1e-9.
        r = b.bleed_duct_diameter(0.83395, T_BLEED)
        self.assertAlmostEqual(r["area_m2"],
                               math.pi * r["diameter_m"] ** 2 / 4.0,
                               places=12)

    def test_duct_state_consistency(self):
        # V = mach * a with a = sqrt(gamma R T) and rho = p/(R T).
        r = b.bleed_duct_diameter(0.5, 400.0)
        sonic = math.sqrt(b.GAMMA_AIR * b.R_AIR * 400.0)
        self.assertAlmostEqual(r["velocity_m_s"], b.M_DUCT * sonic, places=9)
        self.assertAlmostEqual(r["density_kg_m3"],
                               b.P_DUCT_DEFAULT / (b.R_AIR * 400.0),
                               places=9)

    def test_duct_area_falls_with_higher_flow_velocity(self):
        # Higher Mach at fixed state gives higher velocity, so a given
        # flow needs less area.
        r1 = b.bleed_duct_diameter(0.5, 400.0, mach=0.3)
        r2 = b.bleed_duct_diameter(0.5, 400.0, mach=0.6)
        self.assertLess(r2["area_m2"], r1["area_m2"])
        self.assertAlmostEqual(r2["area_m2"], r1["area_m2"] / 2.0, places=9)

    def test_duct_keys_exact(self):
        self.assertEqual(
            set(b.bleed_duct_diameter(1.0, 400.0).keys()),
            {"area_m2", "diameter_m", "velocity_m_s", "density_kg_m3"})

    def test_zero_mass_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(0.0, T_BLEED)

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(-0.1, T_BLEED)

    def test_non_positive_temperature_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, 0.0)
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, -300.0)

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, 400.0, p_duct_pa=0.0)
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, 400.0, p_duct_pa=-1.0)

    def test_mach_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, 400.0, mach=0.0)
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, 400.0, mach=1.0)
        with self.assertRaises(ValueError):
            b.bleed_duct_diameter(1.0, 400.0, mach=1.2)


class SummaryTest(unittest.TestCase):
    def test_worked_example_summary_pass(self):
        r = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.06)
        self.assertAlmostEqual(r["total_offtake_kg_s"], 1.6679, places=9)
        self.assertAlmostEqual(r["per_engine_offtake_kg_s"], 0.83395,
                               places=9)
        self.assertAlmostEqual(r["per_engine_thermal_budget_w"],
                               135775.3995, places=3)
        self.assertAlmostEqual(r["total_thermal_budget_w"],
                               271550.799, places=3)
        self.assertAlmostEqual(r["duct_diameter_m"], 0.0554, delta=1e-3)
        self.assertEqual(r["duct_fit_verdict"], "PASS")

    def test_summary_fail_at_tighter_limit(self):
        r = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.05)
        self.assertEqual(r["duct_fit_verdict"], "FAIL")
        self.assertAlmostEqual(r["max_duct_diameter_m"], 0.05, places=12)

    def test_summary_total_budget_twice_per_engine(self):
        r = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.06)
        self.assertAlmostEqual(r["total_thermal_budget_w"],
                               2.0 * r["per_engine_thermal_budget_w"],
                               places=6)

    def test_summary_verdict_boundary_equal_allowed(self):
        # Diameter exactly at the limit is a PASS.
        r = b.bleed_system_summary([0.5, 0.5], 0.0, 0.0, 400.0,
                                   b.bleed_duct_diameter(0.5, 400.0)
                                   ["diameter_m"])
        self.assertEqual(r["duct_fit_verdict"], "PASS")

    def test_summary_dict_keys_exact(self):
        self.assertEqual(
            set(b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED,
                                       0.06).keys()),
            {"total_offtake_kg_s", "per_engine_offtake_kg_s",
             "per_engine_thermal_budget_w", "total_thermal_budget_w",
             "duct_area_m2", "duct_diameter_m", "duct_velocity_m_s",
             "duct_density_kg_m3", "max_duct_diameter_m",
             "duct_fit_verdict"})

    def test_summary_respects_duct_state_overrides(self):
        # Higher duct pressure gives denser air, a smaller duct at the
        # same flow and temperature.
        low = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.06,
                                     p_duct_pa=250000.0)
        high = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.06,
                                      p_duct_pa=350000.0)
        self.assertLess(high["duct_diameter_m"], low["duct_diameter_m"])

    def test_summary_rejects_non_positive_limit(self):
        with self.assertRaises(ValueError):
            b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.0)

    def test_summary_rejects_non_physical_inputs(self):
        with self.assertRaises(ValueError):
            b.bleed_system_summary(PACKS, -0.1, TRIM, T_BLEED, 0.06)
        with self.assertRaises(ValueError):
            b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, 200.0, 0.06)


class DeterminismTest(unittest.TestCase):
    def test_identical_inputs_identical_outputs(self):
        a = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.06)
        c = b.bleed_system_summary(PACKS, ANTI_ICE, TRIM, T_BLEED, 0.06)
        self.assertEqual(a, c)

    def test_defaults_are_module_constants(self):
        self.assertEqual(b.T_SUPPLY_DEFAULT, 288.0)
        self.assertEqual(b.P_DUCT_DEFAULT, 350000.0)
        self.assertEqual(b.M_DUCT, 0.30)
        self.assertEqual(b.CP_AIR, 1005.0)
        self.assertEqual(b.R_AIR, 287.0)
        self.assertEqual(b.GAMMA_AIR, 1.4)


if __name__ == "__main__":
    unittest.main()

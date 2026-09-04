"""Contract test for vehicle-design/sizing/environmental-control-sizing.

Offline, deterministic, stdlib unittest. Run with:
    python3 scripts/test_environmental_control_sizing.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import environmental_control_sizing_logic as ecs


class TestFreshAirFlow(unittest.TestCase):
    """Cabin ventilation fresh air flow from the occupant count."""

    def test_worked_example_values(self):
        result = ecs.fresh_air_flow(189)
        self.assertAlmostEqual(result["flow_kgmin"], 47.25, places=5)
        self.assertAlmostEqual(result["flow_kgs"], 0.7875, places=6)

    def test_linearity_in_occupant_count(self):
        doubled = ecs.fresh_air_flow(378)["flow_kgmin"]
        self.assertAlmostEqual(doubled, 2.0 * ecs.fresh_air_flow(189)["flow_kgmin"],
                               places=9)

    def test_custom_rate_per_occupant(self):
        result = ecs.fresh_air_flow(100, rate_per_occupant=0.5)
        self.assertAlmostEqual(result["flow_kgmin"], 50.0, places=9)
        self.assertAlmostEqual(result["flow_kgs"], 50.0 / 60.0, places=9)

    def test_valueerror_nonpositive_occupants(self):
        for occupants in (0, -5):
            with self.assertRaises(ValueError):
                ecs.fresh_air_flow(occupants)

    def test_valueerror_nonpositive_rate(self):
        for rate in (0.0, -0.1):
            with self.assertRaises(ValueError):
                ecs.fresh_air_flow(100, rate_per_occupant=rate)

    def test_keys_exactly_as_documented(self):
        self.assertEqual(sorted(ecs.fresh_air_flow(100).keys()),
                         ["flow_kgmin", "flow_kgs"])


class TestCabinHeatLoad(unittest.TestCase):
    """Cabin heat load rollup with design margin."""

    def test_worked_example_values(self):
        result = ecs.cabin_heat_load(189, 0.12, 15.0, 12.0, 8.0)
        self.assertAlmostEqual(result["occupant_heat_kw"], 22.68, places=5)
        self.assertAlmostEqual(result["total_heat_kw"], 57.68, places=5)
        self.assertAlmostEqual(result["design_heat_kw"], 63.448, places=4)

    def test_rollup_sum_identity_and_margin_product(self):
        result = ecs.cabin_heat_load(189, 0.12, 15.0, 12.0, 8.0)
        self.assertAlmostEqual(result["total_heat_kw"],
                               189 * 0.12 + 15.0 + 12.0 + 8.0, places=9)
        self.assertAlmostEqual(result["design_heat_kw"],
                               result["total_heat_kw"] * 1.1, places=9)

    def test_margin_scaling_ratio(self):
        base = ecs.cabin_heat_load(189, 0.12, 15.0, 12.0, 8.0, margin=1.1)
        scaled = ecs.cabin_heat_load(189, 0.12, 15.0, 12.0, 8.0, margin=1.5)
        self.assertAlmostEqual(scaled["design_heat_kw"],
                               base["design_heat_kw"] * (1.5 / 1.1), places=9)

    def test_zero_heat_sources_allowed(self):
        result = ecs.cabin_heat_load(10, 0.0, 0.0, 0.0, 0.0)
        self.assertEqual(result["total_heat_kw"], 0.0)
        self.assertEqual(result["design_heat_kw"], 0.0)

    def test_valueerror_nonpositive_occupants_and_margin(self):
        with self.assertRaises(ValueError):
            ecs.cabin_heat_load(0, 0.12, 15.0, 12.0, 8.0)
        for margin in (1.0, 0.9):
            with self.assertRaises(ValueError):
                ecs.cabin_heat_load(189, 0.12, 15.0, 12.0, 8.0, margin=margin)

    def test_valueerror_any_negative_heat_source(self):
        cases = ((-0.1, 15.0, 12.0, 8.0), (0.12, -1.0, 12.0, 8.0),
                 (0.12, 15.0, -1.0, 8.0), (0.12, 15.0, 12.0, -1.0))
        for q, solar, equip, skin in cases:
            with self.assertRaises(ValueError):
                ecs.cabin_heat_load(189, q, solar, equip, skin)

    def test_keys_exactly_as_documented(self):
        self.assertEqual(sorted(ecs.cabin_heat_load(100, 0.1, 1.0, 1.0, 1.0).keys()),
                         ["design_heat_kw", "occupant_heat_kw", "total_heat_kw"])


class TestPackAirflow(unittest.TestCase):
    """Pack cooling airflow and the governing pack flow verdict."""

    def test_worked_example_cooling_dominates(self):
        result = ecs.pack_airflow(63.448)
        self.assertAlmostEqual(result["cooling_flow_kgs"],
                               63.448 / (1.005 * 20.0), places=6)
        self.assertAlmostEqual(result["cooling_flow_kgs"], 3.156617, places=6)
        self.assertTrue(result["cooling_dominates"])
        self.assertAlmostEqual(result["pack_flow_kgs"],
                               result["cooling_flow_kgs"], places=9)

    def test_fresh_flow_dominates_when_larger(self):
        result = ecs.pack_airflow(63.448, fresh_flow_kgs=5.0)
        self.assertAlmostEqual(result["pack_flow_kgs"], 5.0, places=9)
        self.assertFalse(result["cooling_dominates"])

    def test_custom_cp_and_temperature_rise(self):
        result = ecs.pack_airflow(100.0, cp=1.0, dT_supply_k=25.0)
        self.assertAlmostEqual(result["cooling_flow_kgs"], 4.0, places=9)

    def test_valueerror_nonphysical_parameters(self):
        for heat in (0.0, -10.0):
            with self.assertRaises(ValueError):
                ecs.pack_airflow(heat)
        for cp in (0.0, -1.0):
            with self.assertRaises(ValueError):
                ecs.pack_airflow(63.448, cp=cp)
        for dt in (0.0, -2.0):
            with self.assertRaises(ValueError):
                ecs.pack_airflow(63.448, dT_supply_k=dt)
        with self.assertRaises(ValueError):
            ecs.pack_airflow(63.448, fresh_flow_kgs=-0.1)

    def test_keys_exactly_as_documented(self):
        self.assertEqual(sorted(ecs.pack_airflow(63.448).keys()),
                         ["cooling_dominates", "cooling_flow_kgs",
                          "pack_flow_kgs"])


class TestPressurizationSchedule(unittest.TestCase):
    """Cabin pressurization schedule with the differential clamp."""

    def test_39000ft_holds_design_cabin_altitude(self):
        result = ecs.pressurization_schedule(39000.0)
        self.assertFalse(result["differential_limited"])
        self.assertTrue(result["cabin_altitude_held"])
        self.assertEqual(result["cabin_altitude_ft"], 8000.0)
        p_cab = ecs._p_isa(8000.0 * ecs.FT)
        p_amb = ecs._p_isa(39000.0 * ecs.FT)
        self.assertAlmostEqual(result["differential_psi"],
                               (p_cab - p_amb) / ecs.PSI, places=9)
        self.assertAlmostEqual(result["differential_psi"], 8.0619, places=4)

    def test_39000ft_ambient_and_cabin_pressure(self):
        result = ecs.pressurization_schedule(39000.0)
        self.assertAlmostEqual(result["ambient_pressure_pa"] / 1000.0,
                               19.6770, places=3)
        self.assertAlmostEqual(result["cabin_pressure_pa"] / 1000.0,
                               75.2621, places=3)

    def test_50000ft_clamp_binds_and_cabin_altitude_rises(self):
        result = ecs.pressurization_schedule(50000.0)
        self.assertTrue(result["differential_limited"])
        self.assertFalse(result["cabin_altitude_held"])
        self.assertAlmostEqual(result["differential_psi"], 8.9, places=6)
        self.assertAlmostEqual(result["cabin_pressure_pa"],
                               result["ambient_pressure_pa"] + 8.9 * ecs.PSI,
                               places=3)
        self.assertGreater(result["cabin_altitude_ft"], 8000.0)
        self.assertGreater(result["cabin_altitude_ft"], 8800.0)
        self.assertLess(result["cabin_altitude_ft"], 8820.0)

    def test_50000ft_ambient_pressure(self):
        result = ecs.pressurization_schedule(50000.0)
        self.assertAlmostEqual(result["ambient_pressure_pa"] / 1000.0,
                               11.5970, places=3)

    def test_regime_boundary_crossing_is_monotonic(self):
        lo, hi = 35000.0, 52000.0
        while hi - lo > 1.0:
            mid = 0.5 * (lo + hi)
            if ecs.pressurization_schedule(mid)["differential_limited"]:
                hi = mid
            else:
                lo = mid
        below = ecs.pressurization_schedule(hi - 1.0)
        above = ecs.pressurization_schedule(hi + 1.0)
        self.assertFalse(below["differential_limited"])
        self.assertEqual(below["cabin_altitude_ft"], 8000.0)
        self.assertTrue(above["differential_limited"])
        self.assertGreater(above["cabin_altitude_ft"], 8000.0)

    def test_sea_level_holds_design_cabin_with_negative_differential(self):
        result = ecs.pressurization_schedule(0.0)
        self.assertFalse(result["differential_limited"])
        self.assertEqual(result["cabin_altitude_ft"], 8000.0)
        self.assertLess(result["differential_psi"], 0.0)

    def test_custom_design_cabin_altitude_respected(self):
        result = ecs.pressurization_schedule(39000.0, cabin_alt_design_ft=10000.0)
        self.assertFalse(result["differential_limited"])
        self.assertEqual(result["cabin_altitude_ft"], 10000.0)

    def test_lower_differential_limit_binds_earlier(self):
        strict = ecs.pressurization_schedule(39000.0, dP_max_psi=6.0)
        self.assertTrue(strict["differential_limited"])

    def test_valueerror_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            ecs.pressurization_schedule(-100.0)
        with self.assertRaises(ValueError):
            ecs.pressurization_schedule(39000.0, cabin_alt_design_ft=-1.0)
        for dp in (0.0, -1.0):
            with self.assertRaises(ValueError):
                ecs.pressurization_schedule(39000.0, dP_max_psi=dp)

    def test_keys_exactly_as_documented(self):
        self.assertEqual(sorted(ecs.pressurization_schedule(39000.0).keys()),
                         ["ambient_pressure_pa", "cabin_altitude_ft",
                          "cabin_altitude_held", "cabin_pressure_pa",
                          "differential_limited", "differential_psi"])


class TestIsaInternalConsistency(unittest.TestCase):
    """Internal two-layer ISA helpers stay continuous and invertible."""

    def test_tropopause_continuity(self):
        trop = ecs.P0 * (1.0 - ecs.L * ecs.H_TROP / ecs.T0) ** (ecs.G / (ecs.L * ecs.R))
        self.assertAlmostEqual(ecs._p_isa(ecs.H_TROP), trop, places=9)
        self.assertAlmostEqual(ecs._p_isa(ecs.H_TROP), ecs._P_TROP, places=9)

    def test_pressure_roundtrip_both_regions(self):
        for h in (5000.0, 20000.0):
            self.assertAlmostEqual(ecs._h_isa_from_p(ecs._p_isa(h)), h, places=6)

    def test_region_sanity(self):
        self.assertLess(ecs._p_isa(50000.0 * ecs.FT), ecs._P_TROP)
        self.assertGreater(ecs._p_isa(5000.0), ecs._P_TROP)


class TestEcsSummaryAndDeterminism(unittest.TestCase):
    """ecs_summary rollup and run-to-run determinism."""

    def test_summary_combines_all_module_outputs(self):
        fresh = ecs.fresh_air_flow(189)
        heat = ecs.cabin_heat_load(189, 0.12, 15.0, 12.0, 8.0)
        pack = ecs.pack_airflow(heat["design_heat_kw"],
                                fresh_flow_kgs=fresh["flow_kgs"])
        press = ecs.pressurization_schedule(39000.0)
        summary = ecs.ecs_summary(189, q_occupant_kw=0.12, solar_kw=15.0,
                                  equipment_kw=12.0, skin_kw=8.0,
                                  cruise_alt_ft=39000.0)
        for key in list(fresh) + list(heat) + list(pack) + list(press):
            self.assertIn(key, summary)
        self.assertAlmostEqual(summary["design_heat_kw"], 63.448, places=4)
        self.assertAlmostEqual(summary["flow_kgmin"], 47.25, places=5)
        self.assertAlmostEqual(summary["pack_flow_kgs"],
                               summary["cooling_flow_kgs"], places=9)

    def test_determinism_no_rng(self):
        args = (189, 0.25, 0.12, 15.0, 12.0, 8.0, 39000.0)
        kwargs = dict(margin=1.1, cp=1.005, dT_supply_k=20.0,
                      cabin_alt_design_ft=8000.0, dP_max_psi=8.9)
        self.assertEqual(ecs.ecs_summary(*args, **kwargs),
                         ecs.ecs_summary(*args, **kwargs))


if __name__ == "__main__":
    unittest.main()

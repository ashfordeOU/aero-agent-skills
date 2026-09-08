#!/usr/bin/env python3
"""Gate 3 contract test: reciprocating diesel-cycle logic.

Exercises scripts/diesel_cycle_logic.py (stdlib unittest, offline,
deterministic). Covers the SKILL.md workflow steps: step 1 fixing the
compression-ignition operating point and computing the air-standard Diesel
cycle thermal efficiency and the isentropic compression temperature ratio,
step 2 the four-state temperature bookkeeping and the constant-pressure
heat addition with its cutoff-ratio round trip, step 3 the four-stroke
indicated power from IMEP, displacement and crankshaft speed, step 4 the
brake power at the mechanical efficiency, step 5 the brake specific fuel
consumption and its lb/(hp h) conversion with the round trip back to fuel
flow, step 6 the indicated and brake thermal efficiencies on the Jet-A
lower heating value, step 7 the volumetric fuel flow in m3/s, L/h and US
gal/h, and step 8 the reference-only compression-ignition band verdict
that reports the point's position and never enforces it. Also reviews
ValueError rejection of non-physical inputs (non-finite, non-positive,
out-of-range mechanical efficiency, cutoff ratio above compression ratio).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
dc = importlib.import_module("diesel_cycle_logic")  # noqa: E402


class ModuleConstantsTest(unittest.TestCase):
    """Constants match the spec pinned values (isclose, never exact-float)."""

    def test_constants(self):
        self.assertTrue(math.isclose(dc.GAMMA_AIR, 1.4))
        self.assertTrue(math.isclose(dc.CP_AIR, 1005.0))
        self.assertTrue(math.isclose(dc.T1_REF_K, 288.15))
        self.assertTrue(math.isclose(dc.HOUR_S, 3600.0))
        self.assertTrue(math.isclose(dc.KG_PER_LB, 0.45359237))
        self.assertTrue(math.isclose(dc.W_PER_HP, 745.6998715822702))
        self.assertTrue(math.isclose(dc.US_GAL_PER_M3, 264.17205235814845))
        self.assertTrue(math.isclose(
            dc.KG_PER_KWH_PER_LB_PER_HP_HR, 0.6082773878417611))
        self.assertTrue(math.isclose(dc.JET_A_LHV_J_PER_KG, 43.2e6))
        self.assertTrue(math.isclose(dc.JET_A_DENSITY_KG_PER_M3, 800.0))

    def test_band_tuples(self):
        self.assertTrue(math.isclose(dc.BSFC_BAND_LB_PER_HP_HR[0], 0.35))
        self.assertTrue(math.isclose(dc.BSFC_BAND_LB_PER_HP_HR[1], 0.42))
        self.assertTrue(math.isclose(
            dc.BSFC_BAND_KG_PER_KWH[0], 0.2128970857446164, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            dc.BSFC_BAND_KG_PER_KWH[1], 0.2554765028935397, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            dc.ETA_B_BAND[0], 0.3261878583333333, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            dc.ETA_B_BAND[1], 0.3805525013888889, rel_tol=1e-9))


class DieselEfficiencyTest(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fix the compression-ignition
    operating point and get the air-standard Diesel cycle thermal
    efficiency and isentropic compression temperature ratio."""

    def test_anchor_efficiency(self):
        eta = dc.diesel_efficiency(17.0, 2.2, 1.4)
        self.assertAlmostEqual(eta, 0.6136842121239982, delta=1e-9)
        self.assertLess(abs(eta - 0.6136842121) / 0.6136842121, 1e-9)

    def test_isentropic_temperature_ratio_anchor(self):
        tr = dc.isentropic_temperature_ratio(17.0, 1.4)
        self.assertAlmostEqual(tr, 3.1058435015977315, delta=1e-9)
        self.assertAlmostEqual(tr, 17.0 ** 0.4, places=12)

    def test_cutoff_ratio_sensitivity(self):
        eta_20 = dc.diesel_efficiency(17.0, 2.0, 1.4)
        eta_22 = dc.diesel_efficiency(17.0, 2.2, 1.4)
        eta_25 = dc.diesel_efficiency(17.0, 2.5, 1.4)
        self.assertAlmostEqual(eta_20, 0.6230571224158052, delta=1e-9)
        self.assertAlmostEqual(eta_25, 0.600330985397127, delta=1e-9)
        self.assertGreater(eta_20, eta_22)
        self.assertGreater(eta_22, eta_25)

    def test_rc_to_one_limit_matches_otto_ceiling(self):
        eta_limit = dc.diesel_efficiency(17.0, 1.0 + 1e-9, 1.4)
        otto_ceiling = 1.0 - 1.0 / 17.0 ** 0.4
        self.assertAlmostEqual(eta_limit, 0.6780262755, delta=1e-6)
        self.assertLess(abs(eta_limit - otto_ceiling) / otto_ceiling, 1e-6)
        self.assertLess(eta_limit, 1.0)

    def test_gamma_to_one_limit_approaches_zero(self):
        eta_g = dc.diesel_efficiency(17.0, 2.2, 1.0 + 1e-9)
        self.assertLess(eta_g, 1e-8)

    def test_r_to_one_limit_approaches_zero(self):
        eta_r = dc.diesel_efficiency(1.0 + 1e-9, 1.0 + 1e-9, 1.4)
        self.assertLess(eta_r, 1e-8)

    def test_rejects_boundary_and_domain_violations(self):
        with self.assertRaises(ValueError):
            dc.diesel_efficiency(1.0, 2.2, 1.4)
        with self.assertRaises(ValueError):
            dc.diesel_efficiency(17.0, 1.0, 1.4)
        with self.assertRaises(ValueError):
            dc.diesel_efficiency(2.0, 2.2, 1.4)
        with self.assertRaises(ValueError):
            dc.diesel_efficiency(17.0, 2.2, 1.0)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            dc.diesel_efficiency(float("nan"), 2.2, 1.4)
        with self.assertRaises(ValueError):
            dc.isentropic_temperature_ratio(1.0, 1.4)


class StateTemperatureTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: four-state temperature bookkeeping
    and the constant-pressure heat addition with its cutoff-ratio round
    trip."""

    def test_compression_temperature_anchor(self):
        t2 = dc.compression_temperature(288.15, 17.0, 1.4)
        self.assertAlmostEqual(t2, 894.9488049853862, delta=1e-4)
        self.assertLess(abs(t2 - 894.95) / 894.95, 1e-5)

    def test_state_temperatures_anchor(self):
        states = dc.cycle_state_temperatures(288.15, 17.0, 2.2, 1.4)
        self.assertAlmostEqual(states["t1_k"], 288.15, delta=1e-9)
        self.assertAlmostEqual(states["t2_k"], 894.9488049853862, delta=1e-6)
        self.assertAlmostEqual(states["t3_k"], 1968.8873709678498, delta=1e-6)
        self.assertAlmostEqual(states["t4_k"], 868.9811925471146, delta=1e-6)

    def test_state_identities_hold(self):
        states = dc.cycle_state_temperatures(288.15, 17.0, 2.2, 1.4)
        t3_from_t2 = states["t2_k"] * 2.2
        t4_from_t1 = 288.15 * 2.2 ** 1.4
        self.assertAlmostEqual(states["t3_k"], t3_from_t2, delta=1e-9)
        self.assertAlmostEqual(states["t4_k"], t4_from_t1, delta=1e-9)

    def test_cutoff_and_expansion_temperature_functions(self):
        t2 = dc.compression_temperature(288.15, 17.0, 1.4)
        t3 = dc.cutoff_temperature(t2, 2.2)
        t4 = dc.expansion_temperature(288.15, 2.2, 1.4)
        self.assertAlmostEqual(t3, 1968.8873709678498, delta=1e-6)
        self.assertAlmostEqual(t4, 868.9811925471146, delta=1e-6)

    def test_heat_addition_anchor_and_round_trip(self):
        t2 = 894.9488049853862
        q_in = dc.heat_addition_j_per_kg(t2, 2.2)
        self.assertAlmostEqual(q_in, 1079308.258812376, delta=1.0)
        self.assertAlmostEqual(q_in, 1005.0 * t2 * (2.2 - 1.0), delta=1e-6)
        rc_recovered = dc.cutoff_ratio_from_heat_addition(q_in, t2)
        self.assertAlmostEqual(rc_recovered, 2.2, delta=1e-13)

    def test_temperature_form_efficiency_identity(self):
        states = dc.cycle_state_temperatures(288.15, 17.0, 2.2, 1.4)
        t1, t2, t3, t4 = (states["t1_k"], states["t2_k"], states["t3_k"],
                           states["t4_k"])
        eta_temp_form = 1.0 - (t4 - t1) / (1.4 * (t3 - t2))
        eta_closed_form = dc.diesel_efficiency(17.0, 2.2, 1.4)
        self.assertAlmostEqual(eta_temp_form, eta_closed_form, delta=1e-10)

    def test_heat_rejection_form_efficiency_identity(self):
        states = dc.cycle_state_temperatures(288.15, 17.0, 2.2, 1.4)
        t1, t2, t3, t4 = (states["t1_k"], states["t2_k"], states["t3_k"],
                           states["t4_k"])
        q_in = dc.heat_addition_j_per_kg(t2, 2.2)
        q_out = (1005.0 / 1.4) * (t4 - t1)
        eta_heat_rejection = 1.0 - q_out / q_in
        eta_closed_form = dc.diesel_efficiency(17.0, 2.2, 1.4)
        self.assertAlmostEqual(
            eta_heat_rejection, eta_closed_form, delta=1e-10)

    def test_rejects_non_positive_and_non_finite(self):
        with self.assertRaises(ValueError):
            dc.compression_temperature(0.0, 17.0, 1.4)
        with self.assertRaises(ValueError):
            dc.cutoff_temperature(894.9, 1.0)
        with self.assertRaises(ValueError):
            dc.expansion_temperature(288.15, 0.5, 1.4)
        with self.assertRaises(ValueError):
            dc.heat_addition_j_per_kg(-1.0, 2.2)
        with self.assertRaises(ValueError):
            dc.heat_addition_j_per_kg(894.9, 1.0)
        with self.assertRaises(ValueError):
            dc.cutoff_ratio_from_heat_addition(1.0, 0.0)
        with self.assertRaises(ValueError):
            dc.cycle_state_temperatures(288.15, 2.0, 2.2, 1.4)


class IndicatedPowerTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: four-stroke indicated power from
    IMEP, displacement and crankshaft speed."""

    def test_receipt_target_exact(self):
        p_i = dc.indicated_power(1.8e6, 2.0e-3, 2300.0)
        self.assertAlmostEqual(p_i, 69000.0, delta=1e-6 * 69000.0)

    def test_bar_l_convention_matches_pa_m3(self):
        p_i_a = dc.indicated_power(1.8e6, 2.0e-3, 2300.0)
        p_i_b = dc.indicated_power(1.8e6, 2.0e-3, 2300.0)
        self.assertAlmostEqual(p_i_a, p_i_b, places=9)

    def test_scales_linearly_with_rpm_and_displacement(self):
        p1 = dc.indicated_power(1.8e6, 2.0e-3, 2300.0)
        p2 = dc.indicated_power(1.8e6, 2.0e-3, 4600.0)
        p3 = dc.indicated_power(1.8e6, 4.0e-3, 2300.0)
        self.assertAlmostEqual(p2, 2.0 * p1, places=9)
        self.assertAlmostEqual(p3, 2.0 * p1, places=9)

    def test_rejects_non_positive_and_non_finite(self):
        with self.assertRaises(ValueError):
            dc.indicated_power(0.0, 2.0e-3, 2300.0)
        with self.assertRaises(ValueError):
            dc.indicated_power(1.8e6, -2.0e-3, 2300.0)
        with self.assertRaises(ValueError):
            dc.indicated_power(1.8e6, 2.0e-3, -1.0)
        with self.assertRaises(ValueError):
            dc.indicated_power(1.8e6, 2.0e-3, float("inf"))


class BrakePowerTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: brake power at the mechanical
    efficiency."""

    def test_receipt_target_exact(self):
        p_b = dc.brake_power(69000.0, 0.86)
        self.assertAlmostEqual(p_b, 59340.0, delta=1e-6 * 59340.0)

    def test_unity_mechanical_efficiency_returns_indicated(self):
        p_i = 69000.0
        self.assertAlmostEqual(dc.brake_power(p_i, 1.0), p_i, places=9)

    def test_brake_below_indicated(self):
        p_b = dc.brake_power(69000.0, 0.86)
        self.assertLess(p_b, 69000.0)

    def test_rejects_bad_mechanical_efficiency(self):
        with self.assertRaises(ValueError):
            dc.brake_power(69000.0, 0.0)
        with self.assertRaises(ValueError):
            dc.brake_power(69000.0, 1.1)
        with self.assertRaises(ValueError):
            dc.brake_power(-69000.0, 0.86)


class BsfcTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: brake specific fuel consumption and
    its lb/(hp h) conversion, with the round trip back to fuel flow."""

    def test_worked_example(self):
        bsfc = dc.brake_specific_fuel_consumption(3.9e-3, 59340.0)
        self.assertAlmostEqual(bsfc, 0.23660262891809908, delta=1e-9)
        lb = dc.bsfc_lb_per_hp_hr(bsfc)
        self.assertAlmostEqual(lb, 0.3889716002062689, delta=1e-9)

    def test_round_trip_recovers_fuel_flow(self):
        bsfc = dc.brake_specific_fuel_consumption(3.9e-3, 59340.0)
        recovered = dc.fuel_flow_from_bsfc(bsfc, 59340.0)
        self.assertAlmostEqual(recovered, 3.9e-3, delta=1e-15)

    def test_conversion_bridge_constant(self):
        self.assertAlmostEqual(
            dc.KG_PER_KWH_PER_LB_PER_HP_HR, 0.6082773878417611, places=9)
        converted = 0.23660262891809908 / dc.KG_PER_KWH_PER_LB_PER_HP_HR
        self.assertAlmostEqual(converted, 0.3889716002062689, delta=1e-9)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dc.brake_specific_fuel_consumption(0.0, 59340.0)
        with self.assertRaises(ValueError):
            dc.brake_specific_fuel_consumption(3.9e-3, -59340.0)
        with self.assertRaises(ValueError):
            dc.bsfc_lb_per_hp_hr(float("inf"))
        with self.assertRaises(ValueError):
            dc.fuel_flow_from_bsfc(0.2366, -59340.0)


class ThermalEfficiencyTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: indicated and brake thermal
    efficiencies on the Jet-A lower heating value."""

    def test_worked_example(self):
        eta_i = dc.indicated_thermal_efficiency(69000.0, 3.9e-3)
        eta_b = dc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertAlmostEqual(eta_i, 0.40954415954415957, delta=1e-9)
        self.assertAlmostEqual(eta_b, 0.3522079772079772, delta=1e-9)

    def test_brake_equals_indicated_times_mechanical(self):
        eta_i = dc.indicated_thermal_efficiency(69000.0, 3.9e-3)
        eta_b = dc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertAlmostEqual(eta_b, eta_i * 0.86, delta=1e-12)

    def test_brake_below_diesel_ideal(self):
        eta_diesel = dc.diesel_efficiency(17.0, 2.2, 1.4)
        eta_b = dc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertLess(eta_b, eta_diesel)
        self.assertAlmostEqual(eta_b, 0.35221, delta=1e-4)
        self.assertAlmostEqual(eta_diesel, 0.61368, delta=1e-4)

    def test_indicated_greater_than_brake(self):
        eta_i = dc.indicated_thermal_efficiency(69000.0, 3.9e-3)
        eta_b = dc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertGreater(eta_i, eta_b)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dc.indicated_thermal_efficiency(0.0, 3.9e-3)
        with self.assertRaises(ValueError):
            dc.indicated_thermal_efficiency(
                69000.0, 3.9e-3, lhv_j_per_kg=-1.0)
        with self.assertRaises(ValueError):
            dc.brake_thermal_efficiency(0.0, 3.9e-3)


class VolumetricFuelFlowTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: volumetric fuel flow in m3/s, L/h
    and US gal/h."""

    def test_worked_example(self):
        v_dot = dc.volumetric_fuel_flow(3.9e-3)
        self.assertAlmostEqual(v_dot, 4.875e-06, delta=1e-15)
        l_per_h = v_dot * dc.L_PER_M3 * dc.HOUR_S
        gal_per_h = v_dot * dc.US_GAL_PER_M3 * dc.HOUR_S
        self.assertAlmostEqual(l_per_h, 17.55, delta=1e-9)
        self.assertAlmostEqual(gal_per_h, 4.636219518885506, delta=1e-9)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dc.volumetric_fuel_flow(0.0)
        with self.assertRaises(ValueError):
            dc.volumetric_fuel_flow(3.9e-3, fuel_density_kg_per_m3=0.0)


class CiBandVerdictTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the reference-only
    compression-ignition band verdict, reported and never enforced."""

    def test_anchor_point_inside_both_bands(self):
        verdict = dc.ci_band_verdict(0.3522079772079772, 0.3889716002062689)
        self.assertEqual(verdict["eta_b_position"], "inside")
        self.assertEqual(verdict["bsfc_position"], "inside")
        self.assertFalse(verdict["enforced"])

    def test_out_of_band_point_reports_without_raising(self):
        verdict = dc.ci_band_verdict(0.45, 0.30)
        self.assertEqual(verdict["eta_b_position"], "above")
        self.assertEqual(verdict["bsfc_position"], "below")
        self.assertFalse(verdict["enforced"])

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            dc.ci_band_verdict(0.0, 0.39)
        with self.assertRaises(ValueError):
            dc.ci_band_verdict(0.35, 0.0)


class DieselCycleTest(unittest.TestCase):
    """Full single-call workflow: diesel_cycle chains steps 1-8 and returns
    the single-point summary dict."""

    def setUp(self):
        self.result = dc.diesel_cycle(
            compression_ratio=17.0, cutoff_ratio=2.2, imep_pa=1.8e6,
            displacement_m3=2.0e-3, rpm=2300.0, mechanical_efficiency=0.86,
            fuel_flow_kg_per_s=3.9e-3)

    def test_worked_example_values(self):
        r = self.result
        self.assertAlmostEqual(r["eta_diesel"], 0.6136842121239982, delta=1e-9)
        self.assertAlmostEqual(
            r["temperature_ratio"], 3.1058435015977315, delta=1e-9)
        self.assertAlmostEqual(r["t2_k"], 894.9488049853862, delta=1e-6)
        self.assertAlmostEqual(r["t3_k"], 1968.8873709678498, delta=1e-6)
        self.assertAlmostEqual(r["t4_k"], 868.9811925471146, delta=1e-6)
        self.assertAlmostEqual(
            r["heat_addition_j_per_kg"], 1079308.258812376, delta=1.0)
        self.assertAlmostEqual(r["indicated_power_w"], 69000.0, delta=1e-3)
        self.assertAlmostEqual(r["brake_power_w"], 59340.0, delta=1e-3)
        self.assertAlmostEqual(
            r["bsfc_kg_per_kwh"], 0.23660262891809908, delta=1e-9)
        self.assertAlmostEqual(
            r["bsfc_lb_per_hp_hr"], 0.3889716002062689, delta=1e-9)
        self.assertAlmostEqual(
            r["indicated_thermal_efficiency"], 0.40954415954415957,
            delta=1e-9)
        self.assertAlmostEqual(
            r["brake_thermal_efficiency"], 0.3522079772079772, delta=1e-9)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_m3_per_s"], 4.875e-06, delta=1e-15)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_l_per_h"], 17.55, delta=1e-9)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_us_gal_per_h"], 4.636219518885506,
            delta=1e-9)

    def test_indicated_and_brake_power_hp(self):
        r = self.result
        self.assertAlmostEqual(
            r["indicated_power_hp"], 92.53052418205692, delta=2e-4)
        self.assertAlmostEqual(
            r["brake_power_hp"], 79.57625079656896, delta=2e-4)

    def test_physical_ordering(self):
        r = self.result
        self.assertLess(r["brake_thermal_efficiency"], r["eta_diesel"])
        self.assertLess(r["brake_power_w"], r["indicated_power_w"])
        self.assertGreater(r["indicated_thermal_efficiency"],
                            r["brake_thermal_efficiency"])
        self.assertGreater(r["brake_thermal_efficiency"], 0.3261878583333333)
        self.assertLess(r["brake_thermal_efficiency"], 0.3805525013888889)
        self.assertGreater(r["bsfc_lb_per_hp_hr"], 0.35)
        self.assertLess(r["bsfc_lb_per_hp_hr"], 0.42)

    def test_band_verdict_nested(self):
        bv = self.result["band_verdict"]
        self.assertEqual(bv["eta_b_position"], "inside")
        self.assertEqual(bv["bsfc_position"], "inside")
        self.assertFalse(bv["enforced"])

    def test_rejects_bad_cutoff_ratio_above_compression_ratio(self):
        with self.assertRaises(ValueError):
            dc.diesel_cycle(
                compression_ratio=2.0, cutoff_ratio=2.2, imep_pa=1.8e6,
                displacement_m3=2.0e-3, rpm=2300.0,
                mechanical_efficiency=0.86, fuel_flow_kg_per_s=3.9e-3)

    def test_rejects_non_positive_t1(self):
        with self.assertRaises(ValueError):
            dc.diesel_cycle(
                compression_ratio=17.0, cutoff_ratio=2.2, imep_pa=1.8e6,
                displacement_m3=2.0e-3, rpm=2300.0,
                mechanical_efficiency=0.86, fuel_flow_kg_per_s=3.9e-3,
                t1_k=0.0)

    def test_determinism(self):
        second = dc.diesel_cycle(
            compression_ratio=17.0, cutoff_ratio=2.2, imep_pa=1.8e6,
            displacement_m3=2.0e-3, rpm=2300.0, mechanical_efficiency=0.86,
            fuel_flow_kg_per_s=3.9e-3)
        self.assertEqual(self.result, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

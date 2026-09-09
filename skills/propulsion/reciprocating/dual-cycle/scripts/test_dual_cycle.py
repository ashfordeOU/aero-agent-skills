#!/usr/bin/env python3
"""Gate 3 contract test: reciprocating dual-cycle logic.

Exercises scripts/dual_cycle_logic.py (stdlib unittest, offline,
deterministic). Covers the SKILL.md workflow steps: step 1 fixing the
high-speed compression-ignition operating point and computing the
air-standard dual-cycle thermal efficiency and the isentropic compression
temperature ratio, step 2 the five-state temperature bookkeeping and the
mixed constant-volume-then-constant-pressure heat addition and the
constant-volume heat rejection, step 3 the ideal-cycle mean effective
pressure, step 4 the four-stroke indicated power from IMEP, displacement
and crankshaft speed, step 5 the brake power at the mechanical efficiency,
step 6 the brake specific fuel consumption and its lb/(hp h) conversion
with the round trip back to fuel flow, step 7 the indicated and brake
thermal efficiencies on the Jet-A lower heating value, step 8 the
volumetric fuel flow in m3/s, L/h and US gal/h, and step 9 the
reference-only compression-ignition band verdict that reports the point's
position and never enforces it. Also reviews the alpha -> 1 Diesel limit
and rho -> 1 Otto limit identities and ValueError rejection of
non-physical inputs (non-finite, non-positive, out-of-range mechanical
efficiency, cutoff ratio above compression ratio, pressure ratio below 1).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
dcyc = importlib.import_module("dual_cycle_logic")  # noqa: E402


class ModuleConstantsTest(unittest.TestCase):
    """Constants match the spec pinned values (isclose, never exact-float)."""

    def test_constants(self):
        self.assertTrue(math.isclose(dcyc.GAMMA_AIR, 1.4))
        self.assertTrue(math.isclose(dcyc.CP_AIR, 1005.0))
        self.assertTrue(math.isclose(dcyc.T1_REF_K, 288.15))
        self.assertTrue(math.isclose(dcyc.P1_REF_PA, 150000.0))
        self.assertTrue(math.isclose(dcyc.R_AIR_J_PER_KG_K, 287.0))
        self.assertTrue(math.isclose(dcyc.HOUR_S, 3600.0))
        self.assertTrue(math.isclose(dcyc.KG_PER_LB, 0.45359237))
        self.assertTrue(math.isclose(dcyc.W_PER_HP, 745.6998715822702))
        self.assertTrue(math.isclose(dcyc.US_GAL_PER_M3, 264.17205235814845))
        self.assertTrue(math.isclose(
            dcyc.KG_PER_KWH_PER_LB_PER_HP_HR, 0.6082773878417611))
        self.assertTrue(math.isclose(dcyc.JET_A_LHV_J_PER_KG, 43.2e6))
        self.assertTrue(math.isclose(dcyc.JET_A_DENSITY_KG_PER_M3, 800.0))

    def test_band_tuples(self):
        self.assertTrue(math.isclose(dcyc.BSFC_BAND_LB_PER_HP_HR[0], 0.35))
        self.assertTrue(math.isclose(dcyc.BSFC_BAND_LB_PER_HP_HR[1], 0.42))
        self.assertTrue(math.isclose(
            dcyc.BSFC_BAND_KG_PER_KWH[0], 0.2128970857446164, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            dcyc.BSFC_BAND_KG_PER_KWH[1], 0.2554765028935397, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            dcyc.ETA_B_BAND[0], 0.3261878583333333, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            dcyc.ETA_B_BAND[1], 0.3805525013888889, rel_tol=1e-9))


class DualEfficiencyTest(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fix the high-speed
    compression-ignition operating point and get the air-standard dual-cycle
    thermal efficiency and isentropic compression temperature ratio."""

    def test_worked_point_anchor(self):
        eta = dcyc.dual_efficiency(16.0, 1.35, 2.0, 1.4)
        self.assertAlmostEqual(eta, 0.622604338055, delta=1e-6)

    def test_receipt_targets_r17(self):
        self.assertAlmostEqual(
            dcyc.dual_efficiency(17.0, 1.2, 2.2, 1.4), 0.6194912576,
            delta=1e-6)
        self.assertAlmostEqual(
            dcyc.dual_efficiency(17.0, 1.5, 2.2, 1.4), 0.6243368716,
            delta=1e-6)
        self.assertAlmostEqual(
            dcyc.dual_efficiency(17.0, 2.0, 2.2, 1.4), 0.6284415661,
            delta=1e-6)
        self.assertAlmostEqual(
            dcyc.dual_efficiency(17.0, 1.35, 2.0, 1.4), 0.6316460526,
            delta=1e-6)

    def test_isentropic_temperature_ratio_anchor(self):
        tr = dcyc.isentropic_temperature_ratio(16.0, 1.4)
        self.assertAlmostEqual(tr, 3.03143313302, delta=1e-6)
        self.assertAlmostEqual(tr, 16.0 ** 0.4, places=12)

    def test_alpha_to_one_limit_matches_diesel_closed_form(self):
        eta_limit = dcyc.dual_efficiency(17.0, 1.0 + 1e-9, 2.2, 1.4)
        eta_exact = dcyc.dual_efficiency(17.0, 1.0, 2.2, 1.4)
        self.assertAlmostEqual(eta_limit, 0.613684212124, delta=1e-6)
        self.assertAlmostEqual(eta_exact, 0.613684212124, delta=1e-9)

    def test_rho_to_one_limit_matches_otto_ceiling(self):
        eta_limit = dcyc.dual_efficiency(17.0, 1.2, 1.0 + 1e-9, 1.4)
        otto_ceiling = 1.0 - 1.0 / 17.0 ** 0.4
        self.assertAlmostEqual(eta_limit, 0.678026275475, delta=1e-6)
        self.assertLess(abs(eta_limit - otto_ceiling) / otto_ceiling, 1e-6)

    def test_gamma_to_one_limit_approaches_zero(self):
        eta_g = dcyc.dual_efficiency(16.0, 1.35, 2.0, 1.0 + 1e-9)
        self.assertLess(eta_g, 1e-8)

    def test_pressure_ratio_sensitivity_rises_with_alpha(self):
        e1 = dcyc.dual_efficiency(17.0, 1.2, 2.2, 1.4)
        e2 = dcyc.dual_efficiency(17.0, 1.5, 2.2, 1.4)
        e3 = dcyc.dual_efficiency(17.0, 2.0, 2.2, 1.4)
        self.assertLess(e1, e2)
        self.assertLess(e2, e3)

    def test_cutoff_ratio_sensitivity_falls_with_rho(self):
        e1 = dcyc.dual_efficiency(16.0, 1.35, 1.8, 1.4)
        e2 = dcyc.dual_efficiency(16.0, 1.35, 2.0, 1.4)
        e3 = dcyc.dual_efficiency(16.0, 1.35, 2.2, 1.4)
        self.assertGreater(e1, e2)
        self.assertGreater(e2, e3)

    def test_interpolation_ordering_r16(self):
        diesel_bound = dcyc.dual_efficiency(16.0, 1.0, 2.0, 1.4)
        dual_pt = dcyc.dual_efficiency(16.0, 1.35, 2.0, 1.4)
        otto_bound = dcyc.dual_efficiency(16.0, 1.2, 1.0 + 1e-9, 1.4)
        self.assertLess(diesel_bound, dual_pt)
        self.assertLess(dual_pt, otto_bound)

    def test_interpolation_ordering_r17(self):
        diesel_bound = dcyc.dual_efficiency(17.0, 1.0, 2.2, 1.4)
        dual_pt = dcyc.dual_efficiency(17.0, 1.2, 2.2, 1.4)
        otto_bound = dcyc.dual_efficiency(17.0, 1.2, 1.0 + 1e-9, 1.4)
        self.assertLess(diesel_bound, dual_pt)
        self.assertLess(dual_pt, otto_bound)

    def test_rejects_boundary_and_domain_violations(self):
        with self.assertRaises(ValueError):
            dcyc.dual_efficiency(1.0, 1.35, 2.0, 1.4)
        with self.assertRaises(ValueError):
            dcyc.dual_efficiency(17.0, 1.35, 1.0, 1.4)
        with self.assertRaises(ValueError):
            dcyc.dual_efficiency(2.0, 1.35, 2.2, 1.4)
        with self.assertRaises(ValueError):
            dcyc.dual_efficiency(16.0, 0.9, 2.0, 1.4)
        with self.assertRaises(ValueError):
            dcyc.dual_efficiency(17.0, 1.35, 2.0, 1.0)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            dcyc.dual_efficiency(float("nan"), 1.35, 2.0, 1.4)
        with self.assertRaises(ValueError):
            dcyc.isentropic_temperature_ratio(1.0, 1.4)


class StateTemperatureTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: five-state temperature bookkeeping,
    the mixed heat addition (constant-volume then constant-pressure) and the
    constant-volume heat rejection."""

    def test_compression_temperature_anchor(self):
        t2 = dcyc.compression_temperature(288.15, 16.0, 1.4)
        self.assertAlmostEqual(t2, 873.50745728, delta=1e-3)

    def test_state_temperatures_anchor(self):
        states = dcyc.cycle_state_temperatures(288.15, 16.0, 1.35, 2.0, 1.4)
        self.assertAlmostEqual(states["t1_k"], 288.15, delta=1e-9)
        self.assertAlmostEqual(states["t2_k"], 873.50745728, delta=1e-4)
        self.assertAlmostEqual(states["t3_k"], 1179.23506733, delta=1e-4)
        self.assertAlmostEqual(states["t4_k"], 2358.47013466, delta=1e-4)
        self.assertAlmostEqual(states["t5_k"], 1026.58375212, delta=1e-4)

    def test_state_identities_hold(self):
        states = dcyc.cycle_state_temperatures(288.15, 16.0, 1.35, 2.0, 1.4)
        t3_from_t2 = states["t2_k"] * 1.35
        t4_from_t3 = states["t3_k"] * 2.0
        t5_from_t1 = 288.15 * 1.35 * 2.0 ** 1.4
        self.assertAlmostEqual(states["t3_k"], t3_from_t2, delta=1e-9)
        self.assertAlmostEqual(states["t4_k"], t4_from_t3, delta=1e-9)
        self.assertAlmostEqual(states["t5_k"], t5_from_t1, delta=1e-9)

    def test_phase_temperature_functions(self):
        t2 = dcyc.compression_temperature(288.15, 16.0, 1.4)
        t3 = dcyc.cv_phase_temperature(t2, 1.35)
        t4 = dcyc.cp_phase_temperature(t3, 2.0)
        t5 = dcyc.expansion_temperature(288.15, 1.35, 2.0, 1.4)
        self.assertAlmostEqual(t3, 1179.23506733, delta=1e-4)
        self.assertAlmostEqual(t4, 2358.47013466, delta=1e-4)
        self.assertAlmostEqual(t5, 1026.58375212, delta=1e-4)

    def test_heat_addition_anchor_and_round_trip(self):
        t2 = 873.50745728
        q23 = dcyc.cv_heat_addition_j_per_kg(t2, 1.35, 1.4)
        q34 = dcyc.cp_heat_addition_j_per_kg(t2, 1.35, 2.0)
        q_in = dcyc.heat_addition_j_per_kg(t2, 1.35, 2.0, 1.4)
        self.assertAlmostEqual(q23, 219468.748642, delta=1.0)
        self.assertAlmostEqual(q34, 1185131.24266, delta=1.0)
        self.assertAlmostEqual(q_in, 1404599.99131, delta=1.0)
        self.assertAlmostEqual(q_in, q23 + q34, delta=1e-6)
        cv = dcyc.CP_AIR / 1.4
        alpha_round_trip = 1.0 + q23 / (cv * t2)
        rho_round_trip = 1.0 + q34 / (dcyc.CP_AIR * t2 * 1.35)
        self.assertAlmostEqual(alpha_round_trip, 1.35, delta=1e-9)
        self.assertAlmostEqual(rho_round_trip, 2.0, delta=1e-9)

    def test_heat_rejection_anchor(self):
        q_out = dcyc.heat_rejection_j_per_kg(288.15, 1026.58375212, 1.4)
        self.assertAlmostEqual(q_out, 530089.943487, delta=1.0)

    def test_temperature_form_efficiency_identity(self):
        states = dcyc.cycle_state_temperatures(288.15, 16.0, 1.35, 2.0, 1.4)
        q_in = dcyc.heat_addition_j_per_kg(states["t2_k"], 1.35, 2.0, 1.4)
        q_out = dcyc.heat_rejection_j_per_kg(
            states["t1_k"], states["t5_k"], 1.4)
        eta_from_heat = 1.0 - q_out / q_in
        eta_closed_form = dcyc.dual_efficiency(16.0, 1.35, 2.0, 1.4)
        self.assertAlmostEqual(eta_from_heat, eta_closed_form, delta=1e-10)
        q_out_check = (dcyc.CP_AIR / 1.4) * (states["t5_k"] - states["t1_k"])
        self.assertAlmostEqual(q_out, q_out_check, delta=1e-6)

    def test_pv_equals_rt_identity(self):
        r = 287.0
        t2 = 873.50745728
        p1 = 1.5e5
        v1 = r * 288.15 / p1
        v2 = v1 / 16.0
        p2 = p1 * 16.0 ** 1.4
        self.assertAlmostEqual(p2 * v2, r * t2, delta=1e-1)

    def test_rejects_non_positive_and_non_finite(self):
        with self.assertRaises(ValueError):
            dcyc.compression_temperature(0.0, 16.0, 1.4)
        with self.assertRaises(ValueError):
            dcyc.cv_phase_temperature(873.5, 0.5)
        with self.assertRaises(ValueError):
            dcyc.cp_phase_temperature(1179.2, 1.0)
        with self.assertRaises(ValueError):
            dcyc.expansion_temperature(288.15, 1.35, 0.5, 1.4)
        with self.assertRaises(ValueError):
            dcyc.heat_rejection_j_per_kg(1026.6, 288.15, 1.4)
        with self.assertRaises(ValueError):
            dcyc.cycle_state_temperatures(288.15, 2.0, 1.35, 2.2, 1.4)


class MeanEffectivePressureTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: ideal-cycle mean effective
    pressure."""

    def test_anchor(self):
        mep = dcyc.mean_effective_pressure(288.15, 1.5e5, 16.0, 1.35, 2.0)
        self.assertAlmostEqual(mep, 1691937.3034, delta=1.0)

    def test_linear_in_p1(self):
        mep1 = dcyc.mean_effective_pressure(288.15, 1.5e5, 16.0, 1.35, 2.0)
        mep2 = dcyc.mean_effective_pressure(288.15, 3.0e5, 16.0, 1.35, 2.0)
        self.assertAlmostEqual(mep2, 2.0 * mep1, delta=1e-6 * mep2)
        self.assertAlmostEqual(mep2, 3383874.60681, delta=1.0)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dcyc.mean_effective_pressure(288.15, 0.0, 16.0, 1.35, 2.0)
        with self.assertRaises(ValueError):
            dcyc.mean_effective_pressure(0.0, 1.5e5, 16.0, 1.35, 2.0)


class IndicatedPowerTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: four-stroke indicated power from
    IMEP, displacement and crankshaft speed."""

    def test_receipt_target_exact(self):
        p_i = dcyc.indicated_power(1.8e6, 2.0e-3, 2300.0)
        self.assertAlmostEqual(p_i, 69000.0, delta=1e-6 * 69000.0)

    def test_scales_linearly_with_rpm_and_displacement(self):
        p1 = dcyc.indicated_power(1.8e6, 2.0e-3, 2300.0)
        p2 = dcyc.indicated_power(1.8e6, 2.0e-3, 4600.0)
        p3 = dcyc.indicated_power(1.8e6, 4.0e-3, 2300.0)
        self.assertAlmostEqual(p2, 2.0 * p1, places=9)
        self.assertAlmostEqual(p3, 2.0 * p1, places=9)

    def test_rejects_non_positive_and_non_finite(self):
        with self.assertRaises(ValueError):
            dcyc.indicated_power(0.0, 2.0e-3, 2300.0)
        with self.assertRaises(ValueError):
            dcyc.indicated_power(1.8e6, -2.0e-3, 2300.0)
        with self.assertRaises(ValueError):
            dcyc.indicated_power(1.8e6, 2.0e-3, -1.0)
        with self.assertRaises(ValueError):
            dcyc.indicated_power(1.8e6, 2.0e-3, float("inf"))


class BrakePowerTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: brake power at the mechanical
    efficiency."""

    def test_receipt_target_exact(self):
        p_b = dcyc.brake_power(69000.0, 0.86)
        self.assertAlmostEqual(p_b, 59340.0, delta=1e-6 * 59340.0)

    def test_unity_mechanical_efficiency_returns_indicated(self):
        p_i = 69000.0
        self.assertAlmostEqual(dcyc.brake_power(p_i, 1.0), p_i, places=9)

    def test_rejects_bad_mechanical_efficiency(self):
        with self.assertRaises(ValueError):
            dcyc.brake_power(69000.0, 0.0)
        with self.assertRaises(ValueError):
            dcyc.brake_power(69000.0, 1.1)
        with self.assertRaises(ValueError):
            dcyc.brake_power(-69000.0, 0.86)


class BsfcTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: brake specific fuel consumption and
    its lb/(hp h) conversion, with the round trip back to fuel flow."""

    def test_worked_example(self):
        bsfc = dcyc.brake_specific_fuel_consumption(3.9e-3, 59340.0)
        self.assertAlmostEqual(bsfc, 0.236602628918, delta=1e-9)
        lb = dcyc.bsfc_lb_per_hp_hr(bsfc)
        self.assertAlmostEqual(lb, 0.388971600206, delta=1e-9)

    def test_round_trip_recovers_fuel_flow(self):
        bsfc = dcyc.brake_specific_fuel_consumption(3.9e-3, 59340.0)
        recovered = dcyc.fuel_flow_from_bsfc(bsfc, 59340.0)
        self.assertAlmostEqual(recovered, 3.9e-3, delta=1e-15)

    def test_conversion_bridge_constant(self):
        self.assertAlmostEqual(
            dcyc.KG_PER_KWH_PER_LB_PER_HP_HR, 0.6082773878417611, places=9)
        converted = 0.236602628918 / dcyc.KG_PER_KWH_PER_LB_PER_HP_HR
        self.assertAlmostEqual(converted, 0.388971600206, delta=1e-9)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dcyc.brake_specific_fuel_consumption(0.0, 59340.0)
        with self.assertRaises(ValueError):
            dcyc.brake_specific_fuel_consumption(3.9e-3, -59340.0)
        with self.assertRaises(ValueError):
            dcyc.bsfc_lb_per_hp_hr(float("inf"))
        with self.assertRaises(ValueError):
            dcyc.fuel_flow_from_bsfc(0.2366, -59340.0)


class ThermalEfficiencyTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: indicated and brake thermal
    efficiencies on the Jet-A lower heating value."""

    def test_worked_example(self):
        eta_i = dcyc.indicated_thermal_efficiency(69000.0, 3.9e-3)
        eta_b = dcyc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertAlmostEqual(eta_i, 0.409544159544, delta=1e-9)
        self.assertAlmostEqual(eta_b, 0.352207977208, delta=1e-9)

    def test_brake_equals_indicated_times_mechanical(self):
        eta_i = dcyc.indicated_thermal_efficiency(69000.0, 3.9e-3)
        eta_b = dcyc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertAlmostEqual(eta_b, eta_i * 0.86, delta=1e-12)

    def test_brake_below_dual_ideal(self):
        eta_dual = dcyc.dual_efficiency(16.0, 1.35, 2.0, 1.4)
        eta_b = dcyc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertLess(eta_b, eta_dual)
        self.assertAlmostEqual(eta_b, 0.35221, delta=1e-4)
        self.assertAlmostEqual(eta_dual, 0.62260, delta=1e-4)

    def test_indicated_greater_than_brake(self):
        eta_i = dcyc.indicated_thermal_efficiency(69000.0, 3.9e-3)
        eta_b = dcyc.brake_thermal_efficiency(59340.0, 3.9e-3)
        self.assertGreater(eta_i, eta_b)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dcyc.indicated_thermal_efficiency(0.0, 3.9e-3)
        with self.assertRaises(ValueError):
            dcyc.indicated_thermal_efficiency(
                69000.0, 3.9e-3, lhv_j_per_kg=-1.0)
        with self.assertRaises(ValueError):
            dcyc.brake_thermal_efficiency(0.0, 3.9e-3)


class VolumetricFuelFlowTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: volumetric fuel flow in m3/s, L/h
    and US gal/h."""

    def test_worked_example(self):
        v_dot = dcyc.volumetric_fuel_flow(3.9e-3)
        self.assertAlmostEqual(v_dot, 4.875e-06, delta=1e-15)
        l_per_h = v_dot * dcyc.L_PER_M3 * dcyc.HOUR_S
        gal_per_h = v_dot * dcyc.US_GAL_PER_M3 * dcyc.HOUR_S
        self.assertAlmostEqual(l_per_h, 17.55, delta=1e-9)
        self.assertAlmostEqual(gal_per_h, 4.63621951889, delta=1e-9)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            dcyc.volumetric_fuel_flow(0.0)
        with self.assertRaises(ValueError):
            dcyc.volumetric_fuel_flow(3.9e-3, fuel_density_kg_per_m3=0.0)


class CiBandVerdictTest(unittest.TestCase):
    """Step 9 of the SKILL.md workflow: the reference-only
    compression-ignition band verdict, reported and never enforced."""

    def test_anchor_point_inside_both_bands(self):
        verdict = dcyc.ci_band_verdict(0.352207977208, 0.388971600206)
        self.assertEqual(verdict["eta_b_position"], "inside")
        self.assertEqual(verdict["bsfc_position"], "inside")
        self.assertFalse(verdict["enforced"])

    def test_out_of_band_point_reports_without_raising(self):
        verdict = dcyc.ci_band_verdict(0.45, 0.30)
        self.assertEqual(verdict["eta_b_position"], "above")
        self.assertEqual(verdict["bsfc_position"], "below")
        self.assertFalse(verdict["enforced"])

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            dcyc.ci_band_verdict(0.0, 0.39)
        with self.assertRaises(ValueError):
            dcyc.ci_band_verdict(0.35, 0.0)


class DualCycleTest(unittest.TestCase):
    """Full single-call workflow: dual_cycle chains steps 1-9 and returns
    the single-point summary dict."""

    def setUp(self):
        self.result = dcyc.dual_cycle(
            compression_ratio=16.0, pressure_ratio=1.35, cutoff_ratio=2.0,
            imep_pa=1.8e6, displacement_m3=2.0e-3, rpm=2300.0,
            mechanical_efficiency=0.86, fuel_flow_kg_per_s=3.9e-3)

    def test_worked_example_values(self):
        r = self.result
        self.assertAlmostEqual(r["eta_dual"], 0.622604338055, delta=1e-6)
        self.assertAlmostEqual(
            r["temperature_ratio"], 3.03143313302, delta=1e-6)
        self.assertAlmostEqual(r["t2_k"], 873.50745728, delta=1e-3)
        self.assertAlmostEqual(r["t3_k"], 1179.23506733, delta=1e-3)
        self.assertAlmostEqual(r["t4_k"], 2358.47013466, delta=1e-3)
        self.assertAlmostEqual(r["t5_k"], 1026.58375212, delta=1e-3)
        self.assertAlmostEqual(
            r["cv_heat_addition_j_per_kg"], 219468.748642, delta=1.0)
        self.assertAlmostEqual(
            r["cp_heat_addition_j_per_kg"], 1185131.24266, delta=1.0)
        self.assertAlmostEqual(
            r["heat_addition_j_per_kg"], 1404599.99131, delta=1.0)
        self.assertAlmostEqual(
            r["heat_rejection_j_per_kg"], 530089.943487, delta=1.0)
        self.assertAlmostEqual(
            r["mean_effective_pressure_pa"], 1691937.3034, delta=1.0)
        self.assertAlmostEqual(r["indicated_power_w"], 69000.0, delta=1e-3)
        self.assertAlmostEqual(r["brake_power_w"], 59340.0, delta=1e-3)
        self.assertAlmostEqual(
            r["bsfc_kg_per_kwh"], 0.236602628918, delta=1e-9)
        self.assertAlmostEqual(
            r["bsfc_lb_per_hp_hr"], 0.388971600206, delta=1e-9)
        self.assertAlmostEqual(
            r["indicated_thermal_efficiency"], 0.409544159544, delta=1e-9)
        self.assertAlmostEqual(
            r["brake_thermal_efficiency"], 0.352207977208, delta=1e-9)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_m3_per_s"], 4.875e-06, delta=1e-15)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_l_per_h"], 17.55, delta=1e-9)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_us_gal_per_h"], 4.63621951889,
            delta=1e-9)

    def test_indicated_and_brake_power_hp(self):
        r = self.result
        self.assertAlmostEqual(
            r["indicated_power_hp"], 92.5305241821, delta=2e-4)
        self.assertAlmostEqual(
            r["brake_power_hp"], 79.5762507966, delta=2e-4)

    def test_physical_ordering(self):
        r = self.result
        self.assertLess(r["brake_thermal_efficiency"], r["eta_dual"])
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

    def test_does_not_match_diesel_or_otto_sibling_ceilings(self):
        r = self.result
        diesel_bound = dcyc.dual_efficiency(16.0, 1.0, 2.0, 1.4)
        otto_bound = dcyc.dual_efficiency(16.0, 1.35, 1.0 + 1e-9, 1.4)
        self.assertLess(diesel_bound, r["eta_dual"])
        self.assertLess(r["eta_dual"], otto_bound)

    def test_rejects_bad_cutoff_ratio_above_compression_ratio(self):
        with self.assertRaises(ValueError):
            dcyc.dual_cycle(
                compression_ratio=2.0, pressure_ratio=1.35, cutoff_ratio=2.2,
                imep_pa=1.8e6, displacement_m3=2.0e-3, rpm=2300.0,
                mechanical_efficiency=0.86, fuel_flow_kg_per_s=3.9e-3)

    def test_rejects_non_positive_t1_and_p1(self):
        with self.assertRaises(ValueError):
            dcyc.dual_cycle(
                compression_ratio=16.0, pressure_ratio=1.35,
                cutoff_ratio=2.0, imep_pa=1.8e6, displacement_m3=2.0e-3,
                rpm=2300.0, mechanical_efficiency=0.86,
                fuel_flow_kg_per_s=3.9e-3, t1_k=0.0)
        with self.assertRaises(ValueError):
            dcyc.dual_cycle(
                compression_ratio=16.0, pressure_ratio=1.35,
                cutoff_ratio=2.0, imep_pa=1.8e6, displacement_m3=2.0e-3,
                rpm=2300.0, mechanical_efficiency=0.86,
                fuel_flow_kg_per_s=3.9e-3, p1_pa=0.0)

    def test_determinism(self):
        second = dcyc.dual_cycle(
            compression_ratio=16.0, pressure_ratio=1.35, cutoff_ratio=2.0,
            imep_pa=1.8e6, displacement_m3=2.0e-3, rpm=2300.0,
            mechanical_efficiency=0.86, fuel_flow_kg_per_s=3.9e-3)
        self.assertEqual(self.result, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

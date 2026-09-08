#!/usr/bin/env python3
"""Gate 3 contract test: reciprocating piston-engine-cycle logic.

Exercises scripts/piston_engine_cycle_logic.py (stdlib unittest, offline,
deterministic). Covers the SKILL.md workflow steps: step 1 fixing the
operating point and computing the air-standard Otto cycle thermal
efficiency and the isentropic compression temperature ratio, step 2 the
four-stroke indicated power from IMEP, displacement and crankshaft speed,
step 3 the brake power at the mechanical efficiency, step 4 the brake
specific fuel consumption and its lb/(hp h) conversion with the round trip
back to fuel flow, step 5 the indicated and brake thermal efficiencies on
the fuel lower heating value, step 6 the volumetric fuel flow in m3/s,
L/h and US gal/h, and step 7 the reference-only general-aviation band
verdict that reports the point's position and never enforces it. Also
reviews ValueError rejection of non-physical inputs (non-finite,
non-positive, out-of-range mechanical efficiency).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib
pec = importlib.import_module("piston_engine_cycle_logic")  # noqa: E402


class ModuleConstantsTest(unittest.TestCase):
    """Constants match the spec pinned values (isclose, never exact-float)."""

    def test_constants(self):
        self.assertTrue(math.isclose(pec.GAMMA_AIR, 1.4))
        self.assertTrue(math.isclose(pec.HOUR_S, 3600.0))
        self.assertTrue(math.isclose(pec.KG_PER_LB, 0.45359237))
        self.assertTrue(math.isclose(pec.W_PER_HP, 745.6998715822702))
        self.assertTrue(math.isclose(pec.US_GAL_PER_M3, 264.17205235814845))
        self.assertTrue(math.isclose(
            pec.KG_PER_KWH_PER_LB_PER_HP_HR, 0.6082773878417611))
        self.assertTrue(math.isclose(pec.AVGAS_DENSITY_KG_PER_M3, 720.0))
        self.assertTrue(math.isclose(pec.AVGAS_LHV_J_PER_KG, 43.5e6))

    def test_band_tuples(self):
        self.assertTrue(math.isclose(pec.ETA_B_BAND[0], 0.25))
        self.assertTrue(math.isclose(pec.ETA_B_BAND[1], 0.30))
        self.assertTrue(math.isclose(pec.BSFC_BAND_LB_PER_HP_HR[0], 0.40))
        self.assertTrue(math.isclose(pec.BSFC_BAND_LB_PER_HP_HR[1], 0.55))
        self.assertTrue(math.isclose(
            pec.BSFC_BAND_KG_PER_KWH[0], 0.24331095513670445, rel_tol=1e-9))
        self.assertTrue(math.isclose(
            pec.BSFC_BAND_KG_PER_KWH[1], 0.3345525633129686, rel_tol=1e-9))


class OttoEfficiencyTest(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: fix the operating point and get the
    air-standard Otto cycle thermal efficiency and temperature ratio."""

    def test_anchor_efficiency(self):
        eta = pec.otto_efficiency(8.5, 1.4)
        self.assertAlmostEqual(eta, 0.5751531234287552, places=9)
        self.assertLess(abs(eta - 0.575) / 0.575, 0.001)

    def test_isentropic_temperature_ratio_anchor(self):
        tr = pec.isentropic_temperature_ratio(8.5, 1.4)
        self.assertAlmostEqual(tr, 2.353789224180173, places=9)
        self.assertAlmostEqual(tr, 8.5 ** 0.4, places=12)

    def test_isentropic_identity_holds(self):
        eta = pec.otto_efficiency(8.5, 1.4)
        tr = pec.isentropic_temperature_ratio(8.5, 1.4)
        self.assertAlmostEqual(1.0 - 1.0 / tr, eta, places=12)

    def test_limits_approach_zero(self):
        eta_r = pec.otto_efficiency(1.0 + 1e-9, 1.4)
        eta_g = pec.otto_efficiency(8.5, 1.0 + 1e-9)
        self.assertLess(eta_r, 1e-8)
        self.assertLess(eta_g, 1e-8)

    def test_rejects_boundary_ratios(self):
        with self.assertRaises(ValueError):
            pec.otto_efficiency(1.0, 1.4)
        with self.assertRaises(ValueError):
            pec.isentropic_temperature_ratio(1.0, 1.4)
        with self.assertRaises(ValueError):
            pec.otto_efficiency(8.5, 1.0)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            pec.otto_efficiency(float("nan"), 1.4)
        with self.assertRaises(ValueError):
            pec.otto_efficiency(8.5, float("inf"))


class IndicatedPowerTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: four-stroke indicated power from
    IMEP, displacement and crankshaft speed."""

    def test_receipt_target(self):
        p_i = pec.indicated_power(900e3, 4.0e-3, 2700.0)
        self.assertAlmostEqual(p_i, 81000.0, delta=1e-6 * 81000.0)

    def test_bar_l_convention_matches_pa_m3(self):
        p_i_pa = pec.indicated_power(9.5e5, 5.4e-3, 2700.0)
        p_i_bar_l = pec.indicated_power(9.5e5, 5.4e-3, 2700.0)
        self.assertAlmostEqual(p_i_pa, p_i_bar_l, places=9)
        self.assertAlmostEqual(p_i_pa, 115425.0, delta=1e-6 * 115425.0)

    def test_scales_linearly_with_rpm_and_displacement(self):
        p1 = pec.indicated_power(9.5e5, 5.4e-3, 2700.0)
        p2 = pec.indicated_power(9.5e5, 5.4e-3, 5400.0)
        p3 = pec.indicated_power(9.5e5, 10.8e-3, 2700.0)
        self.assertAlmostEqual(p2, 2.0 * p1, places=9)
        self.assertAlmostEqual(p3, 2.0 * p1, places=9)

    def test_rejects_non_positive_and_non_finite(self):
        with self.assertRaises(ValueError):
            pec.indicated_power(0.0, 5.4e-3, 2700.0)
        with self.assertRaises(ValueError):
            pec.indicated_power(9.5e5, -5.4e-3, 2700.0)
        with self.assertRaises(ValueError):
            pec.indicated_power(9.5e5, 5.4e-3, 0.0)
        with self.assertRaises(ValueError):
            pec.indicated_power(9.5e5, 5.4e-3, float("inf"))


class BrakePowerTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: brake power at the mechanical
    efficiency."""

    def test_receipt_and_worked_example_targets(self):
        p_b_receipt = pec.brake_power(81000.0, 0.85)
        p_b_worked = pec.brake_power(115425.0, 0.85)
        self.assertAlmostEqual(p_b_receipt, 68850.0, delta=1e-6 * 68850.0)
        self.assertAlmostEqual(p_b_worked, 98111.25, delta=1e-6 * 98111.25)

    def test_unity_mechanical_efficiency_returns_indicated(self):
        p_i = 115425.0
        self.assertAlmostEqual(pec.brake_power(p_i, 1.0), p_i, places=9)

    def test_brake_below_indicated_below_one(self):
        p_i = 115425.0
        p_b = pec.brake_power(p_i, 0.85)
        self.assertLess(p_b, p_i)

    def test_rejects_bad_mechanical_efficiency(self):
        with self.assertRaises(ValueError):
            pec.brake_power(115425.0, 0.0)
        with self.assertRaises(ValueError):
            pec.brake_power(115425.0, 1.01)
        with self.assertRaises(ValueError):
            pec.brake_power(-115425.0, 0.85)


class BsfcTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: brake specific fuel consumption and
    its lb/(hp h) conversion, with the round trip back to fuel flow."""

    def test_worked_example(self):
        bsfc = pec.brake_specific_fuel_consumption(7.6e-3, 98111.25)
        self.assertAlmostEqual(bsfc, 0.2788671023965142, delta=1e-9)
        lb = pec.bsfc_lb_per_hp_hr(bsfc)
        self.assertAlmostEqual(lb, 0.4584538369673203, delta=1e-9)

    def test_round_trip_recovers_fuel_flow(self):
        bsfc = pec.brake_specific_fuel_consumption(7.6e-3, 98111.25)
        recovered = pec.fuel_flow_from_bsfc(bsfc, 98111.25)
        self.assertAlmostEqual(recovered, 7.6e-3, delta=1e-15)

    def test_conversion_bridge_constant(self):
        self.assertAlmostEqual(
            pec.KG_PER_KWH_PER_LB_PER_HP_HR, 0.6082773878417611, places=9)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            pec.brake_specific_fuel_consumption(0.0, 98111.25)
        with self.assertRaises(ValueError):
            pec.brake_specific_fuel_consumption(7.6e-3, -98111.25)
        with self.assertRaises(ValueError):
            pec.bsfc_lb_per_hp_hr(0.0)
        with self.assertRaises(ValueError):
            pec.fuel_flow_from_bsfc(0.0, 98111.25)


class ThermalEfficiencyTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: indicated and brake thermal
    efficiencies on the fuel lower heating value."""

    def test_worked_example(self):
        eta_i = pec.indicated_thermal_efficiency(115425.0, 7.6e-3)
        eta_b = pec.brake_thermal_efficiency(98111.25, 7.6e-3)
        self.assertAlmostEqual(eta_i, 0.34913793103448276, delta=1e-9)
        self.assertAlmostEqual(eta_b, 0.2967672413793103, delta=1e-9)

    def test_brake_equals_indicated_times_mechanical(self):
        eta_i = pec.indicated_thermal_efficiency(115425.0, 7.6e-3)
        eta_b = pec.brake_thermal_efficiency(98111.25, 7.6e-3)
        self.assertAlmostEqual(eta_b, eta_i * 0.85, delta=1e-12)

    def test_brake_below_otto_ideal(self):
        eta_otto = pec.otto_efficiency(8.5, 1.4)
        eta_b = pec.brake_thermal_efficiency(98111.25, 7.6e-3)
        self.assertLess(eta_b, eta_otto)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            pec.brake_thermal_efficiency(0.0, 7.6e-3)
        with self.assertRaises(ValueError):
            pec.brake_thermal_efficiency(98111.25, 7.6e-3, lhv_j_per_kg=-1.0)


class VolumetricFuelFlowTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: volumetric fuel flow in m3/s, L/h
    and US gal/h."""

    def test_worked_example(self):
        v_dot = pec.volumetric_fuel_flow(7.6e-3)
        self.assertAlmostEqual(v_dot, 1.0555555555555555e-05, delta=1e-15)
        l_per_h = v_dot * pec.L_PER_M3 * pec.HOUR_S
        gal_per_h = v_dot * pec.US_GAL_PER_M3 * pec.HOUR_S
        self.assertAlmostEqual(l_per_h, 38.0, delta=1e-9)
        self.assertAlmostEqual(gal_per_h, 10.03853798960964, delta=1e-9)

    def test_rejects_non_positive(self):
        with self.assertRaises(ValueError):
            pec.volumetric_fuel_flow(0.0)
        with self.assertRaises(ValueError):
            pec.volumetric_fuel_flow(7.6e-3, fuel_density_kg_per_m3=0.0)


class GaBandVerdictTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the reference-only general-aviation
    band verdict, reported and never enforced."""

    def test_anchor_point_inside_both_bands(self):
        verdict = pec.ga_band_verdict(0.2967672413793103, 0.4584538369673203)
        self.assertEqual(verdict["eta_b_position"], "inside")
        self.assertEqual(verdict["bsfc_position"], "inside")
        self.assertFalse(verdict["enforced"])

    def test_out_of_band_point_reports_above_without_raising(self):
        verdict = pec.ga_band_verdict(0.35, 0.6)
        self.assertEqual(verdict["eta_b_position"], "above")
        self.assertEqual(verdict["bsfc_position"], "above")
        self.assertFalse(verdict["enforced"])

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            pec.ga_band_verdict(0.0, 0.45)
        with self.assertRaises(ValueError):
            pec.ga_band_verdict(0.30, -0.1)


class PistonEngineCycleTest(unittest.TestCase):
    """Full single-call workflow: piston_engine_cycle chains steps 1-7 and
    returns the single-point summary dict."""

    def setUp(self):
        self.result = pec.piston_engine_cycle(
            compression_ratio=8.5, imep_pa=9.5e5, displacement_m3=5.4e-3,
            rpm=2700.0, mechanical_efficiency=0.85, fuel_flow_kg_per_s=7.6e-3)

    def test_worked_example_values(self):
        r = self.result
        self.assertAlmostEqual(r["eta_otto"], 0.5751531234287552, delta=1e-9)
        self.assertAlmostEqual(
            r["temperature_ratio"], 2.353789224180173, delta=1e-9)
        self.assertAlmostEqual(r["indicated_power_w"], 115425.0, delta=1e-3)
        self.assertAlmostEqual(r["brake_power_w"], 98111.25, delta=1e-3)
        self.assertAlmostEqual(
            r["bsfc_kg_per_kwh"], 0.2788671023965142, delta=1e-9)
        self.assertAlmostEqual(
            r["bsfc_lb_per_hp_hr"], 0.4584538369673203, delta=1e-9)
        self.assertAlmostEqual(
            r["indicated_thermal_efficiency"], 0.34913793103448276,
            delta=1e-9)
        self.assertAlmostEqual(
            r["brake_thermal_efficiency"], 0.2967672413793103, delta=1e-9)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_m3_per_s"], 1.0555555555555555e-05,
            delta=1e-15)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_l_per_h"], 38.0, delta=1e-9)
        self.assertAlmostEqual(
            r["volumetric_fuel_flow_us_gal_per_h"], 10.03853798960964,
            delta=1e-9)

    def test_indicated_and_brake_power_hp(self):
        r = self.result
        self.assertAlmostEqual(
            r["indicated_power_hp"], 154.7874746915061, delta=1e-6)
        self.assertAlmostEqual(
            r["brake_power_hp"], 131.56935348778018, delta=1e-6)

    def test_physical_ordering(self):
        r = self.result
        self.assertLess(r["brake_thermal_efficiency"], r["eta_otto"])
        self.assertLess(r["brake_power_w"], r["indicated_power_w"])
        self.assertGreater(r["brake_thermal_efficiency"], 0.25)
        self.assertLess(r["brake_thermal_efficiency"], 0.30)
        self.assertGreater(r["bsfc_lb_per_hp_hr"], 0.40)
        self.assertLess(r["bsfc_lb_per_hp_hr"], 0.55)

    def test_band_verdict_nested(self):
        bv = self.result["band_verdict"]
        self.assertEqual(bv["eta_b_position"], "inside")
        self.assertEqual(bv["bsfc_position"], "inside")
        self.assertFalse(bv["enforced"])

    def test_rejects_bad_compression_ratio(self):
        with self.assertRaises(ValueError):
            pec.piston_engine_cycle(
                compression_ratio=1.0, imep_pa=9.5e5, displacement_m3=5.4e-3,
                rpm=2700.0, mechanical_efficiency=0.85,
                fuel_flow_kg_per_s=7.6e-3)

    def test_determinism(self):
        second = pec.piston_engine_cycle(
            compression_ratio=8.5, imep_pa=9.5e5, displacement_m3=5.4e-3,
            rpm=2700.0, mechanical_efficiency=0.85, fuel_flow_kg_per_s=7.6e-3)
        self.assertEqual(self.result, second)


if __name__ == "__main__":
    unittest.main(verbosity=2)

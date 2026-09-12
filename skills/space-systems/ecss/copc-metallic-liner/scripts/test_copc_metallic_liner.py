"""
Offline deterministic tests for copc_metallic_liner_logic.py.
stdlib unittest only — no third-party dependencies.
Run: python3 test_copc_metallic_liner.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from copc_metallic_liner_logic import (
    FATIGUE_SCATTER_FACTOR,
    GEOMETRY_FACTOR_Y,
    MIN_BURST_FACTOR,
    MIN_PROOF_FACTOR,
    assess_copc_metallic,
    categorize_liner_material,
    check_burst_capability,
    check_burst_factor,
    check_fatigue_cycle_budget,
    check_leak_before_burst,
    check_liner_elasticity_at_proof,
    check_liner_margin_at_meop,
    check_proof_factor,
    compute_burst_pressure,
    compute_critical_flaw_depth,
    compute_hoop_stress,
    compute_proof_pressure,
)


# ---------------------------------------------------------------------------
# Liner material categorization
# ---------------------------------------------------------------------------

class TestCategorizeLinerMaterial(unittest.TestCase):
    def test_recognized_aluminum_2219(self):
        self.assertEqual(categorize_liner_material("aluminum_2219"), "aluminum_2219")

    def test_recognized_titanium_6al4v(self):
        self.assertEqual(categorize_liner_material("titanium_6al4v"), "titanium_6al4v")

    def test_recognized_stainless_316l(self):
        self.assertEqual(categorize_liner_material("stainless_316l"), "stainless_316l")

    def test_case_insensitive_uppercased_input(self):
        self.assertEqual(categorize_liner_material("ALUMINUM_2219"), "aluminum_2219")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(categorize_liner_material("  inconel_718  "), "inconel_718")

    def test_unrecognized_material_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_liner_material("unobtainium")

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            categorize_liner_material(42)


# ---------------------------------------------------------------------------
# Pressure factor checks
# ---------------------------------------------------------------------------

class TestPressureFactors(unittest.TestCase):
    def test_proof_pressure_multiplication(self):
        self.assertAlmostEqual(compute_proof_pressure(2.0, 1.15), 2.3, places=12)

    def test_burst_pressure_multiplication(self):
        self.assertAlmostEqual(compute_burst_pressure(2.0, 1.5), 3.0, places=12)

    def test_proof_factor_above_minimum_passes(self):
        result = check_proof_factor(1.15)
        self.assertTrue(result["pass"])
        self.assertEqual(result["shortfall"], 0.0)

    def test_proof_factor_at_minimum_passes(self):
        result = check_proof_factor(MIN_PROOF_FACTOR)
        self.assertTrue(result["pass"])

    def test_proof_factor_below_minimum_fails(self):
        result = check_proof_factor(1.05)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["shortfall"], MIN_PROOF_FACTOR - 1.05, places=12)

    def test_burst_factor_at_minimum_passes(self):
        result = check_burst_factor(MIN_BURST_FACTOR)
        self.assertTrue(result["pass"])

    def test_burst_factor_below_minimum_fails(self):
        result = check_burst_factor(1.2)
        self.assertFalse(result["pass"])
        self.assertGreater(result["shortfall"], 0.0)

    def test_zero_meop_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_pressure(0.0, 1.15)


# ---------------------------------------------------------------------------
# Thin-wall hoop stress computation
# ---------------------------------------------------------------------------

class TestHoopStress(unittest.TestCase):
    def test_thin_wall_formula_value(self):
        # σ = 2.0 MPa × 0.3 m / 0.004 m = 150.0 MPa
        self.assertAlmostEqual(compute_hoop_stress(2.0, 0.3, 0.004), 150.0, places=9)

    def test_proportional_to_pressure(self):
        s1 = compute_hoop_stress(1.0, 0.3, 0.004)
        s2 = compute_hoop_stress(2.0, 0.3, 0.004)
        self.assertAlmostEqual(s2, 2.0 * s1, places=9)

    def test_thin_wall_assumption_violated_raises(self):
        # t/r = 0.02 / 0.1 = 0.2 >= 0.1 → violation
        with self.assertRaises(ValueError):
            compute_hoop_stress(5.0, 0.1, 0.02)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(0.0, 0.3, 0.004)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(2.0, 0.3, 0.0)


# ---------------------------------------------------------------------------
# Liner elasticity at proof pressure
# ---------------------------------------------------------------------------

class TestLinerElasticityAtProof(unittest.TestCase):
    def test_elastic_below_yield_passes(self):
        # 172.5 MPa < 330 MPa → elastic
        result = check_liner_elasticity_at_proof(172.5, 330.0)
        self.assertTrue(result["pass"])
        self.assertGreater(result["margin"], 0.0)

    def test_yielding_above_yield_fails(self):
        # 350 MPa > 330 MPa → yielded
        result = check_liner_elasticity_at_proof(350.0, 330.0)
        self.assertFalse(result["pass"])
        self.assertLess(result["margin"], 0.0)

    def test_stress_exactly_at_yield_fails(self):
        # At yield onset the liner is no longer strictly elastic → fail
        result = check_liner_elasticity_at_proof(330.0, 330.0)
        self.assertFalse(result["pass"])


# ---------------------------------------------------------------------------
# Liner margin of safety at MEOP
# ---------------------------------------------------------------------------

class TestLinerMarginAtMEOP(unittest.TestCase):
    def test_positive_margin_passes(self):
        result = check_liner_margin_at_meop(150.0, 330.0)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin"], 330.0 / 150.0 - 1.0, places=12)

    def test_negative_margin_fails(self):
        result = check_liner_margin_at_meop(400.0, 330.0)
        self.assertFalse(result["pass"])
        self.assertLess(result["margin"], 0.0)


# ---------------------------------------------------------------------------
# Fracture mechanics — critical flaw depth and LBB
# ---------------------------------------------------------------------------

class TestFractureMechanics(unittest.TestCase):
    def test_critical_flaw_depth_formula(self):
        # a_c = (K_Ic / (Y × σ))² / π
        kic, sigma = 50.0, 200.0
        expected = (kic / (GEOMETRY_FACTOR_Y * sigma)) ** 2 / math.pi
        self.assertAlmostEqual(
            compute_critical_flaw_depth(kic, sigma, GEOMETRY_FACTOR_Y), expected, places=12
        )

    def test_critical_flaw_depth_quadruples_when_toughness_doubles(self):
        a1 = compute_critical_flaw_depth(30.0, 150.0)
        a2 = compute_critical_flaw_depth(60.0, 150.0)
        self.assertAlmostEqual(a2, 4.0 * a1, places=10)

    def test_lbb_passes_when_a_c_exceeds_wall_thickness(self):
        # K_Ic = 100 MPa√m, σ = 100 MPa → a_c ≈ 0.254 m >> t = 0.005 m
        result = check_leak_before_burst(100.0, 100.0, 0.005)
        self.assertTrue(result["pass"])
        self.assertGreater(result["a_c_m"], 0.005)
        self.assertGreater(result["margin"], 0.0)

    def test_lbb_fails_when_a_c_below_wall_thickness(self):
        # K_Ic = 20 MPa√m, σ = 500 MPa → a_c ≈ 0.000406 m << t = 0.005 m
        result = check_leak_before_burst(20.0, 500.0, 0.005)
        self.assertFalse(result["pass"])
        self.assertLess(result["a_c_m"], 0.005)
        self.assertLess(result["margin"], 0.0)

    def test_zero_toughness_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_flaw_depth(0.0, 150.0)


# ---------------------------------------------------------------------------
# Fatigue cycle budget
# ---------------------------------------------------------------------------

class TestFatigueCycleBudget(unittest.TestCase):
    def test_sufficient_cycle_budget_passes(self):
        # 500 / 4 = 125 >= 50 design cycles
        result = check_fatigue_cycle_budget(50, 500)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["effective_allowable"], 125.0, places=9)
        self.assertGreaterEqual(result["margin"], 0.0)

    def test_insufficient_cycle_budget_fails(self):
        # 100 / 4 = 25 < 50 design cycles
        result = check_fatigue_cycle_budget(50, 100)
        self.assertFalse(result["pass"])
        self.assertLess(result["margin"], 0.0)

    def test_scatter_factor_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            check_fatigue_cycle_budget(50, 500, scatter_factor=3.9)

    def test_zero_design_cycles_raises(self):
        with self.assertRaises(ValueError):
            check_fatigue_cycle_budget(0, 500)


# ---------------------------------------------------------------------------
# Burst capability
# ---------------------------------------------------------------------------

class TestBurstCapability(unittest.TestCase):
    def test_burst_exceeds_requirement_passes(self):
        result = check_burst_capability(4.0, 3.0)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin"], 4.0 / 3.0 - 1.0, places=12)

    def test_burst_below_requirement_fails(self):
        result = check_burst_capability(2.5, 3.0)
        self.assertFalse(result["pass"])
        self.assertLess(result["margin"], 0.0)

    def test_burst_exactly_at_requirement_passes(self):
        result = check_burst_capability(3.0, 3.0)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin"], 0.0, places=12)


# ---------------------------------------------------------------------------
# Full assessment
# ---------------------------------------------------------------------------

_PASSING_INPUTS: dict = dict(
    liner_material="aluminum_2219",
    meop_mpa=2.0,
    proof_factor=1.15,
    burst_factor=1.50,
    inner_radius_m=0.3,
    liner_thickness_m=0.004,
    liner_yield_stress_mpa=330.0,
    fracture_toughness_mpa_sqrtm=30.0,
    design_cycles=50,
    allowable_cycles=500,
    actual_burst_pressure_mpa=4.0,
)


class TestFullAssessment(unittest.TestCase):
    def test_all_passing_inputs_are_compliant(self):
        result = assess_copc_metallic(**_PASSING_INPUTS)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["liner_material_canonical"], "aluminum_2219")

    def test_low_proof_factor_raises_finding(self):
        result = assess_copc_metallic(**dict(_PASSING_INPUTS, proof_factor=1.05))
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_liner_yields_at_proof_raises_finding(self):
        # Reduce yield stress so liner yields under proof pressure
        result = assess_copc_metallic(**dict(_PASSING_INPUTS, liner_yield_stress_mpa=100.0))
        self.assertFalse(result["compliant"])

    def test_lbb_not_demonstrated_raises_finding(self):
        result = assess_copc_metallic(**dict(_PASSING_INPUTS, fracture_toughness_mpa_sqrtm=5.0))
        self.assertFalse(result["compliant"])

    def test_insufficient_cycle_budget_raises_finding(self):
        # 500 / 4 = 125 < 200 design cycles
        result = assess_copc_metallic(**dict(_PASSING_INPUTS, design_cycles=200))
        self.assertFalse(result["compliant"])

    def test_burst_shortfall_raises_finding(self):
        # Required = 2.0 × 1.5 = 3.0 MPa; actual = 2.5 MPa → fail
        result = assess_copc_metallic(**dict(_PASSING_INPUTS, actual_burst_pressure_mpa=2.5))
        self.assertFalse(result["compliant"])

    def test_unrecognized_material_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_copc_metallic(**dict(_PASSING_INPUTS, liner_material="unobtainium"))

    def test_multiple_failures_all_captured_in_findings(self):
        # Proof factor and burst factor both below minimum
        result = assess_copc_metallic(
            **dict(_PASSING_INPUTS, proof_factor=1.05, burst_factor=1.2)
        )
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)


if __name__ == "__main__":
    unittest.main()

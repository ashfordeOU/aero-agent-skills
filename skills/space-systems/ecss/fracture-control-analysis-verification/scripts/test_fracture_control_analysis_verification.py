"""
Gate 3 contract tests for fracture_control_analysis_verification_logic.

Run with: python3 test_fracture_control_analysis_verification.py

All tests are deterministic, offline, and use stdlib only.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fracture_control_analysis_verification_logic import (
    assess_fracture_control_compliance,
    check_fracture_toughness,
    check_life_factor,
    check_nde_detectability,
    check_residual_strength,
    compute_critical_crack_size,
    compute_stress_intensity,
    paris_law_crack_growth_rate,
    screen_fracture_criticality,
    REQUIRED_LIFE_FACTORS,
)


# ---------------------------------------------------------------------------
# Helper — base passing arguments for the full assessment
# ---------------------------------------------------------------------------

def _passing_kwargs() -> dict:
    return dict(
        part_id="BRACKET-001",
        consequence="loss_of_mission",
        structure_type="unpressurized",
        design_life=5.0,
        analyzed_life=25.0,       # 5× design life → passes 4× requirement
        stress_intensity=30.0,    # MPa√m
        fracture_toughness=50.0,  # KIC = 50 MPa√m
        assumed_flaw_size=0.005,  # m
        nde_detection_limit=0.003,
        residual_strength=150.0,  # MPa
        limit_load=100.0,         # MPa
        safety_factor=1.0,
    )


# ---------------------------------------------------------------------------
# 1. Fracture criticality categorization tests
# ---------------------------------------------------------------------------

class TestScreenFractureCriticality(unittest.TestCase):

    def test_loss_of_mission_is_fracture_critical(self):
        result = screen_fracture_criticality("loss_of_mission")
        self.assertTrue(result["fracture_critical"])
        self.assertEqual(result["category"], "FC")

    def test_loss_of_crew_is_fracture_critical(self):
        result = screen_fracture_criticality("loss_of_crew")
        self.assertTrue(result["fracture_critical"])

    def test_catastrophic_failure_is_fracture_critical(self):
        result = screen_fracture_criticality("catastrophic_failure")
        self.assertTrue(result["fracture_critical"])

    def test_degraded_performance_is_not_fracture_critical(self):
        result = screen_fracture_criticality("degraded_performance")
        self.assertFalse(result["fracture_critical"])
        self.assertEqual(result["category"], "NFC")

    def test_redundant_failure_is_not_fracture_critical(self):
        result = screen_fracture_criticality("redundant_failure")
        self.assertFalse(result["fracture_critical"])

    def test_unrecognised_consequence_raises_value_error(self):
        with self.assertRaises(ValueError):
            screen_fracture_criticality("not_a_real_consequence")

    def test_message_mentions_analysis_required_for_fc(self):
        result = screen_fracture_criticality("loss_of_spacecraft")
        self.assertIn("required", result["message"].lower())

    def test_consequence_preserved_in_result(self):
        result = screen_fracture_criticality("no_effect")
        self.assertEqual(result["consequence"], "no_effect")


# ---------------------------------------------------------------------------
# 2. Life factor verification tests
# ---------------------------------------------------------------------------

class TestCheckLifeFactor(unittest.TestCase):

    def test_unpressurized_passes_at_exactly_4x(self):
        result = check_life_factor(10.0, 40.0, "unpressurized")
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["life_margin"], 0.0, places=5)

    def test_unpressurized_fails_below_4x(self):
        result = check_life_factor(10.0, 39.9, "unpressurized")
        self.assertFalse(result["passes"])

    def test_pressurized_requires_2x_factor(self):
        self.assertEqual(REQUIRED_LIFE_FACTORS["pressurized"], 2.0)

    def test_pressurized_passes_at_exactly_2x(self):
        result = check_life_factor(10.0, 20.0, "pressurized")
        self.assertTrue(result["passes"])

    def test_pressurized_fails_below_2x(self):
        result = check_life_factor(10.0, 19.9, "pressurized")
        self.assertFalse(result["passes"])

    def test_safe_life_requires_4x_factor(self):
        result = check_life_factor(5.0, 20.0, "safe_life")
        self.assertTrue(result["passes"])
        result_fail = check_life_factor(5.0, 19.0, "safe_life")
        self.assertFalse(result_fail["passes"])

    def test_unknown_structure_type_raises(self):
        with self.assertRaises(ValueError):
            check_life_factor(10.0, 40.0, "exotic_alloy")

    def test_zero_design_life_raises(self):
        with self.assertRaises(ValueError):
            check_life_factor(0.0, 40.0, "unpressurized")

    def test_negative_analyzed_life_raises(self):
        with self.assertRaises(ValueError):
            check_life_factor(10.0, -1.0, "unpressurized")

    def test_required_life_computed_correctly(self):
        result = check_life_factor(7.0, 28.0, "unpressurized")
        self.assertAlmostEqual(result["required_life"], 28.0, places=8)


# ---------------------------------------------------------------------------
# 3. Stress intensity factor tests
# ---------------------------------------------------------------------------

class TestComputeStressIntensity(unittest.TestCase):

    def test_formula_with_unit_geometry_factor(self):
        K = compute_stress_intensity(100.0, 0.01, 1.0)
        expected = 100.0 * math.sqrt(math.pi * 0.01)
        self.assertAlmostEqual(K, expected, places=10)

    def test_geometry_factor_scales_k_linearly(self):
        K1 = compute_stress_intensity(100.0, 0.01, 1.0)
        K2 = compute_stress_intensity(100.0, 0.01, 2.0)
        self.assertAlmostEqual(K2, 2.0 * K1, places=10)

    def test_zero_crack_length_gives_zero_K(self):
        self.assertEqual(compute_stress_intensity(100.0, 0.0, 1.0), 0.0)

    def test_negative_crack_length_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity(100.0, -0.005, 1.0)

    def test_negative_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity(-10.0, 0.01, 1.0)

    def test_non_positive_geometry_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity(100.0, 0.01, 0.0)


# ---------------------------------------------------------------------------
# 4. Critical crack size tests
# ---------------------------------------------------------------------------

class TestComputeCriticalCrackSize(unittest.TestCase):

    def test_formula_correctness(self):
        a = compute_critical_crack_size(50.0, 100.0, 1.0)
        expected = (1.0 / math.pi) * (50.0 / 100.0) ** 2
        self.assertAlmostEqual(a, expected, places=12)

    def test_higher_toughness_gives_larger_critical_crack(self):
        a1 = compute_critical_crack_size(50.0, 100.0)
        a2 = compute_critical_crack_size(100.0, 100.0)
        self.assertGreater(a2, a1)

    def test_higher_stress_gives_smaller_critical_crack(self):
        a1 = compute_critical_crack_size(50.0, 100.0)
        a2 = compute_critical_crack_size(50.0, 200.0)
        self.assertLess(a2, a1)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_size(50.0, 0.0)


# ---------------------------------------------------------------------------
# 5. Fracture toughness check tests
# ---------------------------------------------------------------------------

class TestCheckFractureToughness(unittest.TestCase):

    def test_K_below_KIC_passes(self):
        result = check_fracture_toughness(30.0, 50.0)
        self.assertTrue(result["passes"])

    def test_K_above_KIC_fails(self):
        result = check_fracture_toughness(60.0, 50.0)
        self.assertFalse(result["passes"])

    def test_K_equal_KIC_fails(self):
        # Strict inequality: K must be strictly less than KIC
        result = check_fracture_toughness(50.0, 50.0)
        self.assertFalse(result["passes"])

    def test_margin_computed_correctly(self):
        result = check_fracture_toughness(40.0, 50.0)
        expected = round(50.0 / 40.0 - 1.0, 6)
        self.assertAlmostEqual(result["margin"], expected, places=5)

    def test_zero_K_gives_infinite_margin(self):
        result = check_fracture_toughness(0.0, 50.0)
        self.assertTrue(math.isinf(result["margin"]))

    def test_non_positive_KIC_raises(self):
        with self.assertRaises(ValueError):
            check_fracture_toughness(30.0, 0.0)


# ---------------------------------------------------------------------------
# 6. NDE detectability tests
# ---------------------------------------------------------------------------

class TestCheckNdeDetectability(unittest.TestCase):

    def test_flaw_above_limit_is_conservative(self):
        result = check_nde_detectability(0.005, 0.003)
        self.assertTrue(result["conservative"])

    def test_flaw_equal_to_limit_is_conservative(self):
        result = check_nde_detectability(0.003, 0.003)
        self.assertTrue(result["conservative"])

    def test_flaw_below_limit_is_non_conservative(self):
        result = check_nde_detectability(0.001, 0.003)
        self.assertFalse(result["conservative"])

    def test_negative_flaw_size_raises(self):
        with self.assertRaises(ValueError):
            check_nde_detectability(-0.001, 0.003)

    def test_negative_detection_limit_raises(self):
        with self.assertRaises(ValueError):
            check_nde_detectability(0.005, -0.001)


# ---------------------------------------------------------------------------
# 7. Paris law crack growth rate tests
# ---------------------------------------------------------------------------

class TestParisLawCrackGrowthRate(unittest.TestCase):

    def test_basic_computation(self):
        # da/dN = 1e-10 × 20^3 = 8e-7
        rate = paris_law_crack_growth_rate(20.0, 1e-10, 3.0)
        self.assertAlmostEqual(rate, 1e-10 * (20.0 ** 3), places=20)

    def test_zero_delta_K_gives_zero_rate(self):
        self.assertEqual(paris_law_crack_growth_rate(0.0, 1e-10, 3.0), 0.0)

    def test_negative_delta_K_raises(self):
        with self.assertRaises(ValueError):
            paris_law_crack_growth_rate(-5.0, 1e-10, 3.0)

    def test_zero_C_raises(self):
        with self.assertRaises(ValueError):
            paris_law_crack_growth_rate(20.0, 0.0, 3.0)

    def test_negative_m_raises(self):
        with self.assertRaises(ValueError):
            paris_law_crack_growth_rate(20.0, 1e-10, -1.0)

    def test_larger_delta_K_gives_higher_rate(self):
        rate1 = paris_law_crack_growth_rate(10.0, 1e-10, 3.0)
        rate2 = paris_law_crack_growth_rate(20.0, 1e-10, 3.0)
        self.assertGreater(rate2, rate1)


# ---------------------------------------------------------------------------
# 8. Residual strength tests
# ---------------------------------------------------------------------------

class TestCheckResidualStrength(unittest.TestCase):

    def test_residual_above_required_passes(self):
        result = check_residual_strength(150.0, 100.0, 1.0)
        self.assertTrue(result["passes"])

    def test_residual_below_required_fails(self):
        result = check_residual_strength(80.0, 100.0, 1.0)
        self.assertFalse(result["passes"])

    def test_safety_factor_applied_to_limit_load(self):
        # required = 100 × 1.5 = 150; residual = 150 → margin = 0
        result = check_residual_strength(150.0, 100.0, 1.5)
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["margin_of_safety"], 0.0, places=5)

    def test_safety_factor_below_1_raises(self):
        with self.assertRaises(ValueError):
            check_residual_strength(150.0, 100.0, 0.9)

    def test_required_strength_stored_correctly(self):
        result = check_residual_strength(150.0, 80.0, 1.25)
        self.assertAlmostEqual(result["required_strength"], 100.0, places=8)

    def test_negative_limit_load_raises(self):
        with self.assertRaises(ValueError):
            check_residual_strength(150.0, -50.0, 1.0)


# ---------------------------------------------------------------------------
# 9. Full compliance assessment tests
# ---------------------------------------------------------------------------

class TestAssessFractureControlCompliance(unittest.TestCase):

    def test_fully_passing_part_returns_pass(self):
        result = assess_fracture_control_compliance(**_passing_kwargs())
        self.assertEqual(result["overall"], "PASS")

    def test_non_critical_part_returns_not_applicable(self):
        kwargs = _passing_kwargs()
        kwargs["consequence"] = "degraded_performance"
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "NOT_APPLICABLE")

    def test_non_critical_part_skips_checks(self):
        kwargs = _passing_kwargs()
        kwargs["consequence"] = "no_effect"
        result = assess_fracture_control_compliance(**kwargs)
        self.assertNotIn("life_factor", result)

    def test_life_factor_fail_causes_overall_fail(self):
        kwargs = _passing_kwargs()
        kwargs["analyzed_life"] = 10.0  # only 2× → fails 4× requirement
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "FAIL")
        self.assertFalse(result["life_factor"]["passes"])

    def test_fracture_toughness_exceeded_causes_overall_fail(self):
        kwargs = _passing_kwargs()
        kwargs["stress_intensity"] = 60.0  # K > KIC = 50
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "FAIL")
        self.assertFalse(result["fracture_toughness_check"]["passes"])

    def test_non_conservative_flaw_causes_overall_fail(self):
        kwargs = _passing_kwargs()
        kwargs["assumed_flaw_size"] = 0.001  # < nde_detection_limit = 0.003
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "FAIL")
        self.assertFalse(result["nde_detectability"]["conservative"])

    def test_residual_strength_fail_causes_overall_fail(self):
        kwargs = _passing_kwargs()
        kwargs["residual_strength"] = 50.0  # < limit_load = 100
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "FAIL")
        self.assertFalse(result["residual_strength_check"]["passes"])

    def test_part_id_preserved_in_result(self):
        result = assess_fracture_control_compliance(**_passing_kwargs())
        self.assertEqual(result["part_id"], "BRACKET-001")

    def test_pressurized_structure_uses_2x_life_factor(self):
        kwargs = _passing_kwargs()
        kwargs["structure_type"] = "pressurized"
        kwargs["analyzed_life"] = 10.5  # 2.1× → passes 2× for pressurized
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "PASS")

    def test_safety_factor_applied_in_residual_strength_check(self):
        kwargs = _passing_kwargs()
        kwargs["safety_factor"] = 1.5
        kwargs["residual_strength"] = 149.0  # < 100 × 1.5 = 150 → fail
        result = assess_fracture_control_compliance(**kwargs)
        self.assertEqual(result["overall"], "FAIL")


if __name__ == "__main__":
    unittest.main()

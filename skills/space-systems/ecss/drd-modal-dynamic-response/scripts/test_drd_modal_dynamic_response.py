"""
test_drd_modal_dynamic_response.py

stdlib unittest tests for drd_modal_dynamic_response_logic.
Run: python3 test_drd_modal_dynamic_response.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_modal_dynamic_response_logic import (
    assess_mdra_report_fields,
    categorize_mode,
    check_frequency_separation,
    check_fundamental_frequency,
    check_modal_completeness,
    compute_dynamic_amplification_factor,
    compute_effective_mass_fraction,
    compute_modal_participation_factor,
    validate_damping_ratio,
)


# ---------------------------------------------------------------------------
# Fundamental frequency
# ---------------------------------------------------------------------------

class TestFundamentalFrequency(unittest.TestCase):
    def test_passes_when_above_minimum(self):
        result = check_fundamental_frequency(50.0, 40.0)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin_hz"], 10.0)

    def test_fails_when_below_minimum(self):
        result = check_fundamental_frequency(35.0, 40.0)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["margin_hz"], -5.0)

    def test_passes_at_exact_minimum(self):
        result = check_fundamental_frequency(40.0, 40.0)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["margin_hz"], 0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            check_fundamental_frequency(-10.0, 40.0)

    def test_zero_minimum_raises(self):
        with self.assertRaises(ValueError):
            check_fundamental_frequency(50.0, 0.0)

    def test_result_contains_inputs(self):
        result = check_fundamental_frequency(100.0, 80.0)
        self.assertEqual(result["freq_hz"], 100.0)
        self.assertEqual(result["min_freq_hz"], 80.0)


# ---------------------------------------------------------------------------
# Frequency separation
# ---------------------------------------------------------------------------

class TestFrequencySeparation(unittest.TestCase):
    def test_passes_with_sufficient_separation(self):
        result = check_frequency_separation(120.0, 100.0, 0.10)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["separation_ratio"], 0.20)

    def test_fails_with_insufficient_separation(self):
        result = check_frequency_separation(105.0, 100.0, 0.10)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["separation_ratio"], 0.05)

    def test_passes_at_exact_margin(self):
        result = check_frequency_separation(110.0, 100.0, 0.10)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["separation_ratio"], 0.10)

    def test_zero_excitation_freq_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_separation(100.0, 0.0)

    def test_negative_structural_freq_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_separation(-50.0, 100.0)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_separation(100.0, 80.0, -0.1)


# ---------------------------------------------------------------------------
# Effective mass fraction
# ---------------------------------------------------------------------------

class TestEffectiveMassFraction(unittest.TestCase):
    def test_fraction_computed_correctly(self):
        fraction = compute_effective_mass_fraction([30.0, 40.0, 20.0], 100.0)
        self.assertAlmostEqual(fraction, 0.90)

    def test_fraction_above_one_allowed(self):
        fraction = compute_effective_mass_fraction([101.0], 100.0)
        self.assertAlmostEqual(fraction, 1.01)

    def test_negative_mass_entry_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_mass_fraction([-5.0, 50.0], 100.0)

    def test_zero_total_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_effective_mass_fraction([50.0], 0.0)

    def test_non_list_raises(self):
        with self.assertRaises(TypeError):
            compute_effective_mass_fraction(50.0, 100.0)


# ---------------------------------------------------------------------------
# Modal completeness
# ---------------------------------------------------------------------------

class TestModalCompleteness(unittest.TestCase):
    def test_passes_at_threshold(self):
        result = check_modal_completeness(0.90)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["deficit"], 0.0)

    def test_fails_below_threshold(self):
        result = check_modal_completeness(0.85)
        self.assertFalse(result["pass"])
        self.assertAlmostEqual(result["deficit"], 0.05)

    def test_passes_above_threshold(self):
        result = check_modal_completeness(0.95)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["deficit"], 0.0)

    def test_invalid_threshold_zero_raises(self):
        with self.assertRaises(ValueError):
            check_modal_completeness(0.90, threshold=0.0)

    def test_fraction_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            check_modal_completeness(2.0)


# ---------------------------------------------------------------------------
# Mode band assignment
# ---------------------------------------------------------------------------

class TestCategorizeModes(unittest.TestCase):
    def test_rigid_body_mode(self):
        self.assertEqual(categorize_mode(0.05), "rigid-body")

    def test_flexible_mode_low(self):
        self.assertEqual(categorize_mode(10.0), "flexible")

    def test_flexible_mode_at_lower_boundary(self):
        self.assertEqual(categorize_mode(0.1), "flexible")

    def test_high_frequency_mode(self):
        self.assertEqual(categorize_mode(250.0), "high-frequency")

    def test_high_frequency_at_boundary(self):
        self.assertEqual(categorize_mode(200.0), "high-frequency")

    def test_non_positive_freq_raises(self):
        with self.assertRaises(ValueError):
            categorize_mode(0.0)

    def test_inconsistent_cutoffs_raise(self):
        with self.assertRaises(ValueError):
            categorize_mode(50.0, rigid_body_cutoff_hz=300.0, high_freq_cutoff_hz=200.0)


# ---------------------------------------------------------------------------
# Damping ratio validation
# ---------------------------------------------------------------------------

class TestDampingValidation(unittest.TestCase):
    def test_typical_structural_damping_valid(self):
        result = validate_damping_ratio(0.02)
        self.assertTrue(result["valid"])
        self.assertFalse(result["high_damping_warning"])

    def test_high_damping_triggers_warning(self):
        result = validate_damping_ratio(0.10)
        self.assertTrue(result["valid"])
        self.assertTrue(result["high_damping_warning"])

    def test_zero_damping_is_invalid(self):
        result = validate_damping_ratio(0.0)
        self.assertFalse(result["valid"])

    def test_critical_damping_is_invalid(self):
        result = validate_damping_ratio(1.0)
        self.assertFalse(result["valid"])

    def test_overdamped_is_invalid(self):
        result = validate_damping_ratio(1.5)
        self.assertFalse(result["valid"])

    def test_non_numeric_raises(self):
        with self.assertRaises(TypeError):
            validate_damping_ratio("0.02")

    def test_boundary_at_high_damping_threshold(self):
        result = validate_damping_ratio(0.05)
        self.assertTrue(result["valid"])
        self.assertFalse(result["high_damping_warning"])


# ---------------------------------------------------------------------------
# Dynamic amplification factor
# ---------------------------------------------------------------------------

class TestDynamicAmplificationFactor(unittest.TestCase):
    def test_static_case_gives_unity(self):
        daf = compute_dynamic_amplification_factor(0.0, 0.02)
        self.assertAlmostEqual(daf, 1.0, places=6)

    def test_resonance_amplified_by_damping(self):
        zeta = 0.05
        daf = compute_dynamic_amplification_factor(1.0, zeta)
        self.assertAlmostEqual(daf, 1.0 / (2.0 * zeta), places=6)

    def test_high_freq_ratio_attenuates(self):
        daf = compute_dynamic_amplification_factor(10.0, 0.02)
        self.assertLess(daf, 0.02)

    def test_zero_damping_at_resonance_raises(self):
        with self.assertRaises(ZeroDivisionError):
            compute_dynamic_amplification_factor(1.0, 0.0)

    def test_negative_freq_ratio_raises(self):
        with self.assertRaises(ValueError):
            compute_dynamic_amplification_factor(-1.0, 0.02)

    def test_overdamped_raises(self):
        with self.assertRaises(ValueError):
            compute_dynamic_amplification_factor(0.5, 1.2)

    def test_daf_greater_than_one_near_resonance(self):
        daf = compute_dynamic_amplification_factor(0.9, 0.05)
        self.assertGreater(daf, 1.0)


# ---------------------------------------------------------------------------
# Modal participation factor
# ---------------------------------------------------------------------------

class TestModalParticipationFactor(unittest.TestCase):
    def test_uniform_mode_shape(self):
        L = compute_modal_participation_factor([1.0, 1.0, 1.0], [10.0, 10.0, 10.0])
        self.assertAlmostEqual(L, 30.0)

    def test_antisymmetric_mode_cancels(self):
        L = compute_modal_participation_factor([1.0, -1.0], [10.0, 10.0])
        self.assertAlmostEqual(L, 0.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            compute_modal_participation_factor([1.0, 2.0], [10.0])

    def test_empty_vectors_raise(self):
        with self.assertRaises(ValueError):
            compute_modal_participation_factor([], [])

    def test_negative_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_modal_participation_factor([1.0], [-5.0])


# ---------------------------------------------------------------------------
# MDRA report field completeness
# ---------------------------------------------------------------------------

class TestMdraReportFields(unittest.TestCase):
    def test_complete_report_passes(self):
        report = {
            "model_description": "FE model v3",
            "boundary_conditions": "fixed base at interface ring",
            "natural_frequencies": [12.4, 23.1, 41.7],
            "mode_shapes": "stored in FE database",
            "effective_masses": {"X": [45, 20, 8], "Y": [50, 18, 6], "Z": [30, 25, 12]},
            "damping_assumptions": "zeta=0.02 for all modes",
            "dynamic_response_results": "peak accelerations per load case",
            "frequency_separation_margins": "all margins >= 10%",
        }
        result = assess_mdra_report_fields(report)
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_fields"], [])

    def test_incomplete_report_flags_missing(self):
        report = {"model_description": "FE model v3"}
        result = assess_mdra_report_fields(report)
        self.assertFalse(result["complete"])
        self.assertIn("natural_frequencies", result["missing_fields"])
        self.assertIn("effective_masses", result["missing_fields"])

    def test_non_dict_raises(self):
        with self.assertRaises(TypeError):
            assess_mdra_report_fields("not a dict")

    def test_custom_required_fields(self):
        report = {"field_a": 1, "field_b": 2}
        result = assess_mdra_report_fields(
            report, required_fields=["field_a", "field_b", "field_c"]
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing_fields"], ["field_c"])
        self.assertIn("field_a", result["present_fields"])

    def test_present_fields_list_correct(self):
        report = {"model_description": "x", "boundary_conditions": "y"}
        result = assess_mdra_report_fields(report)
        self.assertIn("model_description", result["present_fields"])
        self.assertIn("boundary_conditions", result["present_fields"])


if __name__ == "__main__":
    unittest.main()

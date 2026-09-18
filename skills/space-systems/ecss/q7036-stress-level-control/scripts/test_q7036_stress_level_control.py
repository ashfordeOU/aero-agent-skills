"""Contract tests for the SCC sustained stress level control logic."""

import math
import unittest

from q7036_stress_level_control_logic import (
    LOCAL_TERMS,
    STRESS_TOLERANCE,
    SUSTAINED_TERMS,
    THRESHOLD_FRACTIONS,
    allowable_stress_mpa,
    assess_stress_level,
    concentration_factor,
    margin_ratio,
    normalize_category,
    reduction_options,
    sustained_total_mpa,
    validate_stress,
)


def spec(**overrides):
    base = {
        "id": "bracket-1",
        "resistance_category": "medium",
        "yield_strength_mpa": 400.0,
        "terms": {"applied_sustained_mpa": 120.0, "preload_mpa": 30.0},
    }
    base.update(overrides)
    return base


class ValidationTests(unittest.TestCase):
    def test_category_alias(self):
        self.assertEqual(normalize_category("Susceptible"), "low")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("immune")

    def test_negative_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(-10.0, "applied_sustained_mpa")

    def test_boolean_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(True, "applied_sustained_mpa")

    def test_non_finite_stress_rejected(self):
        with self.assertRaises(ValueError):
            validate_stress(float("nan"), "applied_sustained_mpa")

    def test_concentration_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            concentration_factor(0.8)

    def test_unity_concentration_accepted(self):
        self.assertAlmostEqual(concentration_factor(1.0), 1.0, places=9)

    def test_local_terms_are_a_subset_of_the_sustained_terms(self):
        for name in LOCAL_TERMS:
            self.assertIn(name, SUSTAINED_TERMS)


class TotalStressTests(unittest.TestCase):
    def test_terms_are_summed(self):
        total = sustained_total_mpa({"applied_sustained_mpa": 100.0, "preload_mpa": 40.0})
        self.assertAlmostEqual(total, 140.0, places=9)

    def test_missing_terms_count_as_zero(self):
        self.assertAlmostEqual(sustained_total_mpa({"preload_mpa": 40.0}), 40.0, places=9)

    def test_concentration_raises_the_nominal_terms(self):
        total = sustained_total_mpa({"applied_sustained_mpa": 100.0}, 2.5)
        self.assertAlmostEqual(total, 250.0, places=9)

    def test_local_terms_escape_the_concentration(self):
        total = sustained_total_mpa(
            {"applied_sustained_mpa": 100.0, "forming_residual_mpa": 60.0}, 2.0
        )
        self.assertAlmostEqual(total, 260.0, places=9)

    def test_compressive_residual_is_subtracted(self):
        total = sustained_total_mpa({"applied_sustained_mpa": 100.0}, 1.0, 30.0)
        self.assertAlmostEqual(total, 70.0, places=9)

    def test_compressive_residual_floors_the_total_at_zero(self):
        total = sustained_total_mpa({"applied_sustained_mpa": 100.0}, 1.0, 400.0)
        self.assertAlmostEqual(total, 0.0, places=9)

    def test_unknown_term_rejected(self):
        with self.assertRaises(ValueError):
            sustained_total_mpa({"vibration_peak_mpa": 100.0})

    def test_non_mapping_terms_rejected(self):
        with self.assertRaises(ValueError):
            sustained_total_mpa([100.0, 40.0])

    def test_negative_compressive_residual_rejected(self):
        with self.assertRaises(ValueError):
            sustained_total_mpa({"applied_sustained_mpa": 100.0}, 1.0, -30.0)


class AllowableTests(unittest.TestCase):
    def test_resistant_state_allows_the_largest_fraction(self):
        self.assertAlmostEqual(allowable_stress_mpa("high", 400.0), 300.0, places=9)

    def test_intermediate_state_allows_half_of_yield(self):
        self.assertAlmostEqual(allowable_stress_mpa("medium", 400.0), 200.0, places=9)

    def test_susceptible_state_allows_the_smallest_fraction(self):
        self.assertAlmostEqual(allowable_stress_mpa("low", 400.0), 100.0, places=9)

    def test_fractions_fall_with_resistance(self):
        self.assertGreater(THRESHOLD_FRACTIONS["high"], THRESHOLD_FRACTIONS["medium"])
        self.assertGreater(THRESHOLD_FRACTIONS["medium"], THRESHOLD_FRACTIONS["low"])

    def test_measured_threshold_supersedes_the_fraction(self):
        self.assertAlmostEqual(
            allowable_stress_mpa("low", 400.0, 260.0), 260.0, places=9
        )

    def test_threshold_above_yield_rejected(self):
        with self.assertRaises(ValueError):
            allowable_stress_mpa("high", 400.0, 500.0)

    def test_zero_yield_strength_rejected(self):
        with self.assertRaises(ValueError):
            allowable_stress_mpa("high", 0.0)


class MarginTests(unittest.TestCase):
    def test_half_loaded_part_has_unit_margin(self):
        self.assertAlmostEqual(margin_ratio(100.0, 200.0), 1.0, places=9)

    def test_fully_loaded_part_has_zero_margin(self):
        self.assertAlmostEqual(margin_ratio(200.0, 200.0), 0.0, places=9)

    def test_overloaded_part_has_negative_margin(self):
        self.assertLess(margin_ratio(400.0, 200.0), 0.0)

    def test_unstressed_part_has_infinite_margin(self):
        self.assertTrue(math.isinf(margin_ratio(0.0, 200.0)))

    def test_zero_allowable_rejected(self):
        with self.assertRaises(ValueError):
            margin_ratio(100.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_lightly_loaded_part_is_compliant(self):
        result = assess_stress_level(spec())
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["total_sustained_mpa"], 150.0, places=9)
        self.assertAlmostEqual(result["allowable_mpa"], 200.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_stress_exactly_on_the_allowable_is_compliant(self):
        result = assess_stress_level(
            spec(terms={"applied_sustained_mpa": 200.0}, yield_strength_mpa=400.0)
        )
        self.assertAlmostEqual(result["total_sustained_mpa"], result["allowable_mpa"], places=9)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_ratio"], 0.0, places=9)

    def test_overstressed_part_is_flagged_with_reductions(self):
        result = assess_stress_level(spec(terms={"applied_sustained_mpa": 300.0}))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertTrue(result["reductions"])

    def test_reductions_lead_with_the_largest_contribution(self):
        result = assess_stress_level(
            spec(terms={"applied_sustained_mpa": 90.0, "preload_mpa": 250.0})
        )
        self.assertFalse(result["compliant"])
        self.assertIn("preload", result["reductions"][0])

    def test_susceptible_state_fails_a_load_the_resistant_state_passes(self):
        loads = {"applied_sustained_mpa": 250.0}
        self.assertTrue(
            assess_stress_level(spec(resistance_category="high", terms=loads))["compliant"]
        )
        self.assertFalse(
            assess_stress_level(spec(resistance_category="low", terms=loads))["compliant"]
        )

    def test_measured_threshold_is_reported_as_the_source(self):
        result = assess_stress_level(spec(measured_threshold_mpa=180.0))
        self.assertEqual(result["allowable_source"], "measured-threshold")

    def test_concentration_can_turn_a_pass_into_a_failure(self):
        loads = {"applied_sustained_mpa": 150.0}
        self.assertTrue(assess_stress_level(spec(terms=loads))["compliant"])
        self.assertFalse(
            assess_stress_level(spec(terms=loads, stress_concentration=2.0))["compliant"]
        )

    def test_full_cancellation_is_raised_for_confirmation(self):
        result = assess_stress_level(
            spec(terms={"applied_sustained_mpa": 50.0}, compressive_residual_mpa=90.0)
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("treated layer", result["findings"][0])

    def test_contributions_record_the_concentrated_values(self):
        result = assess_stress_level(
            spec(terms={"applied_sustained_mpa": 100.0}, stress_concentration=1.5)
        )
        self.assertAlmostEqual(result["contributions"]["applied_sustained_mpa"], 150.0, places=9)

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["terms"]
        with self.assertRaises(ValueError):
            assess_stress_level(broken)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_stress_level(spec(id="   "))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_stress_level(["bracket-1"])

    def test_tolerance_is_tight(self):
        self.assertLess(STRESS_TOLERANCE, 1e-6)

    def test_reduction_options_reject_a_non_mapping(self):
        with self.assertRaises(ValueError):
            reduction_options(["contributions"])


if __name__ == "__main__":
    unittest.main()

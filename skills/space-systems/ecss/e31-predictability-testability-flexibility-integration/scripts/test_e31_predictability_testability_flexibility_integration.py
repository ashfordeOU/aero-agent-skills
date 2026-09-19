"""Contract tests for the clauses 4.4.6 to 4.4.8 design-property logic."""

import math
import unittest

from e31_predictability_testability_flexibility_integration_logic import (
    LIMIT_TOLERANCE_K,
    accessibility_findings,
    assess_design_properties,
    bounding_excursion_k,
    combined_uncertainty_k,
    grade_widened_prediction,
    heater_authority_margin,
    reference_point_coverage,
    rss_uncertainty_k,
    validate_heat_paths,
    weighted_characterized_fraction,
    widened_prediction_k,
)

# One dominant measured interface and a scatter of small assumed couplings.
PATHS = [
    {"name": "baseplate-interface", "conductance_w_per_k": 8.0, "characterized": True},
    {"name": "harness-bundle", "conductance_w_per_k": 0.4, "characterized": False},
    {"name": "strut-conduction", "conductance_w_per_k": 0.2, "characterized": False},
]


class HeatPathValidationTests(unittest.TestCase):
    def test_validated_paths_round_trip(self):
        validated = validate_heat_paths(PATHS)
        self.assertEqual(len(validated), 3)
        self.assertAlmostEqual(validated[0]["conductance_w_per_k"], 8.0)

    def test_empty_path_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_heat_paths([])

    def test_zero_conductance_rejected(self):
        with self.assertRaises(ValueError):
            validate_heat_paths([
                {"name": "p", "conductance_w_per_k": 0.0, "characterized": True}
            ])

    def test_missing_characterized_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_heat_paths([{"name": "p", "conductance_w_per_k": 1.0}])

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_heat_paths([
                {"name": "p", "conductance_w_per_k": 1.0, "characterized": "yes"}
            ])

    def test_duplicate_path_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_heat_paths([
                {"name": "p", "conductance_w_per_k": 1.0, "characterized": True},
                {"name": "p", "conductance_w_per_k": 2.0, "characterized": True},
            ])

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_heat_paths([
                {"name": "   ", "conductance_w_per_k": 1.0, "characterized": True}
            ])


class WeightedFractionTests(unittest.TestCase):
    def test_dominant_measured_path_carries_the_fraction(self):
        self.assertAlmostEqual(
            weighted_characterized_fraction(PATHS), 8.0 / 8.6, places=12
        )

    def test_unweighted_count_would_have_read_one_third(self):
        weighted = weighted_characterized_fraction(PATHS)
        unweighted = 1.0 / 3.0
        self.assertGreater(weighted, unweighted)

    def test_many_small_measured_paths_do_not_rescue_a_guessed_main_path(self):
        paths = [
            {"name": "main", "conductance_w_per_k": 8.0, "characterized": False},
            {"name": "m1", "conductance_w_per_k": 0.05, "characterized": True},
            {"name": "m2", "conductance_w_per_k": 0.05, "characterized": True},
            {"name": "m3", "conductance_w_per_k": 0.05, "characterized": True},
        ]
        self.assertLess(weighted_characterized_fraction(paths), 0.02)

    def test_fully_measured_network_is_one(self):
        paths = [
            {"name": "a", "conductance_w_per_k": 1.0, "characterized": True},
            {"name": "b", "conductance_w_per_k": 3.0, "characterized": True},
        ]
        self.assertAlmostEqual(weighted_characterized_fraction(paths), 1.0, places=12)

    def test_fully_assumed_network_is_zero(self):
        paths = [{"name": "a", "conductance_w_per_k": 1.0, "characterized": False}]
        self.assertAlmostEqual(weighted_characterized_fraction(paths), 0.0, places=12)


class UncertaintyTests(unittest.TestCase):
    def test_quadrature_of_three_four(self):
        self.assertAlmostEqual(rss_uncertainty_k([3.0, 4.0]), 5.0, places=12)

    def test_mapping_contributors_accepted(self):
        value = rss_uncertainty_k([{"sigma_k": 3.0}, {"sigma_k": 4.0}])
        self.assertAlmostEqual(value, 5.0, places=12)

    def test_empty_contributor_list_is_zero(self):
        self.assertAlmostEqual(rss_uncertainty_k([]), 0.0)

    def test_negative_contributor_rejected(self):
        with self.assertRaises(ValueError):
            rss_uncertainty_k([3.0, -1.0])

    def test_mapping_without_sigma_rejected(self):
        with self.assertRaises(ValueError):
            rss_uncertainty_k([{"name": "conduction"}])

    def test_bounding_excursion_is_half_range_times_sensitivity(self):
        value = bounding_excursion_k([
            {"sensitivity_k_per_unit": 4.0, "parameter_range": 0.5}
        ])
        self.assertAlmostEqual(value, 1.0, places=12)

    def test_excursion_uses_the_sensitivity_magnitude(self):
        value = bounding_excursion_k([
            {"sensitivity_k_per_unit": -4.0, "parameter_range": 0.5}
        ])
        self.assertAlmostEqual(value, 1.0, places=12)

    def test_excursions_add_rather_than_combining_in_quadrature(self):
        sweeps = [
            {"sensitivity_k_per_unit": 6.0, "parameter_range": 1.0},
            {"sensitivity_k_per_unit": 8.0, "parameter_range": 1.0},
        ]
        self.assertAlmostEqual(bounding_excursion_k(sweeps), 7.0, places=12)

    def test_negative_parameter_range_rejected(self):
        with self.assertRaises(ValueError):
            bounding_excursion_k([
                {"sensitivity_k_per_unit": 4.0, "parameter_range": -0.5}
            ])

    def test_missing_sensitivity_key_rejected(self):
        with self.assertRaises(ValueError):
            bounding_excursion_k([{"parameter_range": 0.5}])

    def test_combination_adds_the_two_kinds(self):
        value = combined_uncertainty_k(
            [3.0, 4.0], [{"sensitivity_k_per_unit": 4.0, "parameter_range": 1.0}]
        )
        self.assertAlmostEqual(value, 7.0, places=12)

    def test_quadrature_alone_understates_a_swept_parameter(self):
        both = combined_uncertainty_k(
            [3.0], [{"sensitivity_k_per_unit": 10.0, "parameter_range": 1.0}]
        )
        self.assertGreater(both, rss_uncertainty_k([3.0, 5.0]))


class WidenedPredictionTests(unittest.TestCase):
    def test_hot_side_widens_upwards(self):
        self.assertAlmostEqual(widened_prediction_k(320.0, 5.0, "hot"), 325.0, places=12)

    def test_cold_side_widens_downwards(self):
        self.assertAlmostEqual(widened_prediction_k(250.0, 5.0, "cold"), 245.0, places=12)

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            widened_prediction_k(320.0, 5.0, "warm")

    def test_cold_widening_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            widened_prediction_k(4.0, 10.0, "cold")

    def test_hot_prediction_inside_the_limit_passes(self):
        result = grade_widened_prediction(320.0, 5.0, 333.15)
        self.assertTrue(result["acceptable"])
        self.assertIsNone(result["finding"])

    def test_hot_prediction_exactly_on_the_limit_passes(self):
        result = grade_widened_prediction(328.15, 5.0, 333.15)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(result["exceedance_k"], 0.0, places=9)

    def test_uncertainty_can_push_a_nominal_pass_over_the_limit(self):
        self.assertTrue(grade_widened_prediction(330.0, 0.0, 333.15)["acceptable"])
        self.assertFalse(grade_widened_prediction(330.0, 10.0, 333.15)["acceptable"])

    def test_cold_prediction_under_the_limit_is_a_finding(self):
        result = grade_widened_prediction(250.0, 20.0, 240.0, "cold")
        self.assertFalse(result["acceptable"])
        self.assertIn("cold", result["finding"])

    def test_non_positive_limit_rejected(self):
        with self.assertRaises(ValueError):
            grade_widened_prediction(320.0, 5.0, 0.0)

    def test_tolerance_is_tight(self):
        self.assertLess(LIMIT_TOLERANCE_K, 1.0e-6)


class HeaterAuthorityTests(unittest.TestCase):
    def test_margin_is_relative_to_what_is_required(self):
        self.assertAlmostEqual(heater_authority_margin(30.0, 24.0), 0.25, places=12)

    def test_exactly_sized_heater_has_no_margin(self):
        self.assertAlmostEqual(heater_authority_margin(24.0, 24.0), 0.0, places=12)

    def test_undersized_heater_reports_a_negative_margin(self):
        self.assertAlmostEqual(heater_authority_margin(18.0, 24.0), -0.25, places=12)

    def test_zero_required_power_rejected(self):
        with self.assertRaises(ValueError):
            heater_authority_margin(30.0, 0.0)

    def test_negative_installed_power_rejected(self):
        with self.assertRaises(ValueError):
            heater_authority_margin(-1.0, 24.0)


class CoverageAndAccessTests(unittest.TestCase):
    def test_full_coverage_reports_no_finding(self):
        result = reference_point_coverage(["trp-a", "trp-b"], ["trp-a", "trp-b"])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=12)
        self.assertEqual(result["findings"], [])

    def test_uninstrumented_reference_point_is_a_finding(self):
        result = reference_point_coverage(["trp-a", "trp-b"], ["trp-a"])
        self.assertEqual(result["uncovered"], ["trp-b"])
        self.assertAlmostEqual(result["coverage_fraction"], 0.5, places=12)

    def test_a_neighbouring_sensor_does_not_cover_the_point(self):
        result = reference_point_coverage(["trp-b"], ["trp-b-adjacent"])
        self.assertEqual(result["uncovered"], ["trp-b"])
        self.assertEqual(result["stray_sensors"], ["trp-b-adjacent"])

    def test_empty_reference_point_list_rejected(self):
        with self.assertRaises(ValueError):
            reference_point_coverage([], ["trp-a"])

    def test_duplicate_reference_point_rejected(self):
        with self.assertRaises(ValueError):
            reference_point_coverage(["trp-a", "trp-a"], ["trp-a"])

    def test_non_string_sensor_rejected(self):
        with self.assertRaises(ValueError):
            reference_point_coverage(["trp-a"], [7])

    def test_reachable_hardware_gives_no_finding(self):
        self.assertEqual(
            accessibility_findings([{"name": "heater-a", "access_after_closeout": False}]),
            [],
        )

    def test_access_after_closeout_is_a_finding(self):
        findings = accessibility_findings([
            {"name": "thermostat-b", "access_after_closeout": True}
        ])
        self.assertEqual(len(findings), 1)
        self.assertIn("close-out", findings[0])

    def test_blocked_removal_is_a_separate_finding(self):
        findings = accessibility_findings([
            {"name": "sensor-c", "access_after_closeout": True, "blocked_by": "antenna"}
        ])
        self.assertEqual(len(findings), 2)

    def test_blank_blocked_by_is_not_a_finding(self):
        findings = accessibility_findings([
            {"name": "sensor-c", "access_after_closeout": False, "blocked_by": "  "}
        ])
        self.assertEqual(findings, [])

    def test_non_boolean_access_flag_rejected(self):
        with self.assertRaises(ValueError):
            accessibility_findings([{"name": "x", "access_after_closeout": 1}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "heat_paths": PATHS,
            "predictability_threshold": 0.9,
            "uncertainty_contributors": [3.0, 4.0],
            "nominal_k": 320.0,
            "limit_k": 333.15,
            "heater_installed_w": 30.0,
            "heater_required_w": 24.0,
            "flexibility_threshold": 0.2,
            "reference_points": ["trp-a", "trp-b"],
            "instrumented_points": ["trp-a", "trp-b"],
            "accessibility_items": [
                {"name": "heater-a", "access_after_closeout": False}
            ],
        }
        spec.update(overrides)
        return spec

    def test_clean_design_is_compliant(self):
        result = assess_design_properties(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_all_four_attributes_are_reported(self):
        result = assess_design_properties(self._spec())
        self.assertTrue(result["predictable"])
        self.assertTrue(result["testable"])
        self.assertTrue(result["flexible"])
        self.assertTrue(result["integrable"])

    def test_guessed_main_interface_fails_predictability(self):
        paths = [dict(PATHS[0], characterized=False)] + list(PATHS[1:])
        result = assess_design_properties(self._spec(heat_paths=paths))
        self.assertFalse(result["predictable"])
        self.assertIn("characterised", result["findings"][0])

    def test_threshold_exactly_met_is_predictable(self):
        fraction = weighted_characterized_fraction(PATHS)
        result = assess_design_properties(self._spec(predictability_threshold=fraction))
        self.assertTrue(result["predictable"])

    def test_swept_parameter_can_break_the_limit(self):
        spec = self._spec(parameter_sensitivities=[
            {"sensitivity_k_per_unit": 20.0, "parameter_range": 1.0}
        ])
        result = assess_design_properties(spec)
        self.assertFalse(result["compliant"])
        self.assertIn("widened", result["grading"]["finding"])

    def test_combined_uncertainty_is_reported(self):
        result = assess_design_properties(self._spec())
        self.assertAlmostEqual(result["combined_uncertainty_k"], 5.0, places=12)

    def test_short_heater_authority_is_a_finding(self):
        result = assess_design_properties(self._spec(heater_installed_w=25.0))
        self.assertFalse(result["flexible"])

    def test_uninstrumented_point_fails_testability(self):
        result = assess_design_properties(self._spec(instrumented_points=["trp-a"]))
        self.assertFalse(result["testable"])
        self.assertFalse(result["compliant"])

    def test_access_finding_fails_integration(self):
        result = assess_design_properties(self._spec(accessibility_items=[
            {"name": "thermostat-b", "access_after_closeout": True}
        ]))
        self.assertFalse(result["integrable"])

    def test_cold_sense_is_graded_on_the_cold_side(self):
        spec = self._spec(nominal_k=253.15, limit_k=243.15, sense="cold")
        self.assertTrue(assess_design_properties(spec)["compliant"])
        spec_tight = self._spec(
            nominal_k=246.0, limit_k=243.15, sense="cold",
            uncertainty_contributors=[6.0],
        )
        self.assertFalse(assess_design_properties(spec_tight)["compliant"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["limit_k"]
        with self.assertRaises(ValueError):
            assess_design_properties(spec)

    def test_threshold_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_properties(self._spec(predictability_threshold=1.5))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_properties(["heat_paths"])

    def test_findings_accumulate_across_attributes(self):
        spec = self._spec(
            heater_installed_w=10.0,
            instrumented_points=[],
            accessibility_items=[{"name": "x", "access_after_closeout": True}],
        )
        result = assess_design_properties(spec)
        self.assertGreaterEqual(len(result["findings"]), 4)
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()

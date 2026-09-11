"""
Gate 3 contract tests for e1012-tid-unc logic.

Run: python3 test_e1012_tid_unc.py
Requires: stdlib only, offline, deterministic. Minimum 10 tests.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_tid_unc_logic import (
    DEFAULT_REQUIRED_RDM,
    SOURCE_ENVIRONMENT_MODEL,
    SOURCE_PART_VARIABILITY,
    SOURCE_SHIELDING_GEOMETRY,
    SOURCE_TEST_CONDITIONS,
    UNCERTAINTY_SOURCES,
    assess_component,
    assess_mission,
    check_rdm,
    combine_uncertainty_factors,
    compute_design_tid,
    compute_rdm,
    resolve_source_category,
    validate_factor,
)


# ---------------------------------------------------------------------------
# resolve_source_category
# ---------------------------------------------------------------------------

class TestResolveSourceCategory(unittest.TestCase):

    def test_canonical_names_pass_through(self):
        for source in UNCERTAINTY_SOURCES:
            self.assertEqual(resolve_source_category(source), source)

    def test_orbit_model_maps_to_environment_model(self):
        self.assertEqual(
            resolve_source_category("orbit_model"), SOURCE_ENVIRONMENT_MODEL
        )

    def test_geometry_maps_to_shielding_geometry(self):
        self.assertEqual(
            resolve_source_category("geometry"), SOURCE_SHIELDING_GEOMETRY
        )

    def test_dose_rate_maps_to_test_conditions(self):
        self.assertEqual(resolve_source_category("dose-rate"), SOURCE_TEST_CONDITIONS)

    def test_part_to_part_maps_to_part_variability(self):
        self.assertEqual(
            resolve_source_category("part to part"), SOURCE_PART_VARIABILITY
        )

    def test_case_insensitive(self):
        self.assertEqual(
            resolve_source_category("  Environment_Model "), SOURCE_ENVIRONMENT_MODEL
        )

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            resolve_source_category("weather")

    def test_non_string_category_raises(self):
        with self.assertRaises(ValueError):
            resolve_source_category(7)

    def test_blank_category_raises(self):
        with self.assertRaises(ValueError):
            resolve_source_category("   ")


# ---------------------------------------------------------------------------
# validate_factor
# ---------------------------------------------------------------------------

class TestValidateFactor(unittest.TestCase):

    def test_unit_factor_allowed(self):
        self.assertEqual(validate_factor(1.0), 1.0)

    def test_factor_above_one_allowed(self):
        self.assertEqual(validate_factor(1.35), 1.35)

    def test_integer_factor_allowed(self):
        self.assertEqual(validate_factor(2), 2.0)

    def test_sub_unity_factor_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(0.9)

    def test_zero_factor_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(0.0)

    def test_non_numeric_factor_raises(self):
        with self.assertRaises(ValueError):
            validate_factor("1.2")

    def test_boolean_factor_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(True)

    def test_error_mentions_source(self):
        with self.assertRaises(ValueError) as ctx:
            validate_factor(0.5, "test_conditions")
        self.assertIn("test_conditions", str(ctx.exception))


# ---------------------------------------------------------------------------
# combine_uncertainty_factors
# ---------------------------------------------------------------------------

class TestCombineFactors(unittest.TestCase):

    def test_product_of_four_sources(self):
        factors = {
            SOURCE_ENVIRONMENT_MODEL: 1.2,
            SOURCE_SHIELDING_GEOMETRY: 1.1,
            SOURCE_TEST_CONDITIONS: 1.05,
            SOURCE_PART_VARIABILITY: 1.3,
        }
        self.assertAlmostEqual(combine_uncertainty_factors(factors), 1.8018, places=9)

    def test_single_factor(self):
        self.assertAlmostEqual(
            combine_uncertainty_factors({SOURCE_ENVIRONMENT_MODEL: 2.0}), 2.0
        )

    def test_all_unit_factors(self):
        factors = {
            SOURCE_ENVIRONMENT_MODEL: 1.0,
            SOURCE_PART_VARIABILITY: 1.0,
        }
        self.assertEqual(combine_uncertainty_factors(factors), 1.0)

    def test_pair_sequence_accepted(self):
        pairs = [(SOURCE_ENVIRONMENT_MODEL, 2.0), (SOURCE_SHIELDING_GEOMETRY, 1.5)]
        self.assertAlmostEqual(combine_uncertainty_factors(pairs), 3.0)

    def test_alias_keys_are_normalised(self):
        factors = {"orbit_model": 2.0, "geometry": 1.5}
        self.assertAlmostEqual(combine_uncertainty_factors(factors), 3.0)

    def test_empty_dict_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors({})

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors([])

    def test_duplicate_source_raises(self):
        # 'orbit_model' and the canonical name are the same category.
        factors = {SOURCE_ENVIRONMENT_MODEL: 1.2, "orbit_model": 1.1}
        with self.assertRaises(ValueError):
            combine_uncertainty_factors(factors)

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors({"weather": 1.2})

    def test_sub_unity_factor_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors({SOURCE_ENVIRONMENT_MODEL: 0.8})

    def test_malformed_pair_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors([(SOURCE_ENVIRONMENT_MODEL,)])

    def test_pairs_of_wrong_length_raise(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors([(SOURCE_ENVIRONMENT_MODEL, 1.2, 3)])

    def test_unsupported_type_raises(self):
        with self.assertRaises(ValueError):
            combine_uncertainty_factors(1.2)


# ---------------------------------------------------------------------------
# compute_design_tid
# ---------------------------------------------------------------------------

class TestComputeDesignTid(unittest.TestCase):

    def test_design_tid_scales_mean_tid(self):
        self.assertAlmostEqual(
            compute_design_tid(10.0, {SOURCE_ENVIRONMENT_MODEL: 2.0}), 20.0
        )

    def test_design_tid_with_multiple_factors(self):
        factors = {
            SOURCE_ENVIRONMENT_MODEL: 1.5,
            SOURCE_SHIELDING_GEOMETRY: 2.0,
            SOURCE_TEST_CONDITIONS: 1.0,
            SOURCE_PART_VARIABILITY: 1.25,
        }
        self.assertAlmostEqual(compute_design_tid(8.0, factors), 30.0, places=9)

    def test_unit_factor_leaves_mean_tid_unchanged(self):
        self.assertAlmostEqual(
            compute_design_tid(12.5, {SOURCE_TEST_CONDITIONS: 1.0}), 12.5
        )

    def test_zero_mean_tid_raises(self):
        with self.assertRaises(ValueError):
            compute_design_tid(0.0, {SOURCE_ENVIRONMENT_MODEL: 1.2})

    def test_negative_mean_tid_raises(self):
        with self.assertRaises(ValueError):
            compute_design_tid(-5.0, {SOURCE_ENVIRONMENT_MODEL: 1.2})

    def test_non_numeric_mean_tid_raises(self):
        with self.assertRaises(ValueError):
            compute_design_tid("ten", {SOURCE_ENVIRONMENT_MODEL: 1.2})

    def test_empty_factors_raise(self):
        with self.assertRaises(ValueError):
            compute_design_tid(10.0, {})


# ---------------------------------------------------------------------------
# compute_rdm
# ---------------------------------------------------------------------------

class TestComputeRdm(unittest.TestCase):

    def test_rdm_is_tolerance_over_design_tid(self):
        self.assertAlmostEqual(compute_rdm(40.0, 20.0), 2.0)

    def test_rdm_below_minimum(self):
        self.assertAlmostEqual(compute_rdm(30.0, 30.0), 1.0)

    def test_rdm_above_minimum(self):
        self.assertAlmostEqual(compute_rdm(75.0, 25.0), 3.0)

    def test_zero_lot_tolerance_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(0.0, 20.0)

    def test_zero_design_tid_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(40.0, 0.0)

    def test_negative_design_tid_raises(self):
        with self.assertRaises(ValueError):
            compute_rdm(40.0, -20.0)


# ---------------------------------------------------------------------------
# check_rdm
# ---------------------------------------------------------------------------

class TestCheckRdm(unittest.TestCase):

    def test_above_minimum_passes(self):
        result = check_rdm(2.5)
        self.assertTrue(result["meets_minimum"])
        self.assertFalse(result["borderline"])

    def test_below_minimum_fails(self):
        result = check_rdm(1.9)
        self.assertFalse(result["meets_minimum"])
        self.assertFalse(result["borderline"])

    def test_exactly_minimum_is_borderline(self):
        result = check_rdm(2.0)
        self.assertTrue(result["meets_minimum"])
        self.assertTrue(result["borderline"])

    def test_custom_minimum(self):
        result = check_rdm(3.0, required_min=3.0)
        self.assertTrue(result["meets_minimum"])
        self.assertTrue(result["borderline"])

    def test_default_minimum_value(self):
        result = check_rdm(5.0)
        self.assertEqual(result["required_min"], DEFAULT_REQUIRED_RDM)

    def test_zero_required_min_raises(self):
        with self.assertRaises(ValueError):
            check_rdm(2.0, required_min=0.0)

    def test_negative_achieved_raises(self):
        with self.assertRaises(ValueError):
            check_rdm(-1.0)


# ---------------------------------------------------------------------------
# assess_component
# ---------------------------------------------------------------------------

class TestAssessComponent(unittest.TestCase):

    def test_passing_component(self):
        result = assess_component(
            "ADC12", 10.0, 40.0, {SOURCE_ENVIRONMENT_MODEL: 1.5}
        )
        self.assertAlmostEqual(result["combined_factor"], 1.5)
        self.assertAlmostEqual(result["design_tid"], 15.0)
        self.assertAlmostEqual(result["achieved_rdm"], 40.0 / 15.0)
        self.assertTrue(result["meets_minimum"])
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["requires_justification"])

    def test_borderline_component(self):
        result = assess_component(
            "FPGA01", 10.0, 40.0, {SOURCE_ENVIRONMENT_MODEL: 2.0}
        )
        self.assertAlmostEqual(result["achieved_rdm"], 2.0)
        self.assertTrue(result["meets_minimum"])
        self.assertTrue(result["borderline"])
        self.assertEqual(result["status"], "PASS")

    def test_failing_component(self):
        result = assess_component(
            "PROM03", 10.0, 40.0, {SOURCE_ENVIRONMENT_MODEL: 3.0}
        )
        self.assertFalse(result["meets_minimum"])
        self.assertEqual(result["status"], "FAIL")

    def test_four_source_component(self):
        factors = {
            SOURCE_ENVIRONMENT_MODEL: 1.2,
            SOURCE_SHIELDING_GEOMETRY: 1.1,
            SOURCE_TEST_CONDITIONS: 1.05,
            SOURCE_PART_VARIABILITY: 1.3,
        }
        result = assess_component("MCU01", 10.0, 40.0, factors)
        self.assertAlmostEqual(result["combined_factor"], 1.8018, places=9)
        self.assertAlmostEqual(result["design_tid"], 18.018, places=9)
        self.assertAlmostEqual(result["achieved_rdm"], 2.22000222000222, places=9)
        self.assertEqual(
            result["categories"], sorted(UNCERTAINTY_SOURCES)
        )

    def test_unit_factor_requires_justification(self):
        result = assess_component(
            "LOGIC1", 5.0, 20.0, {SOURCE_TEST_CONDITIONS: 1.0}
        )
        self.assertTrue(result["requires_justification"])

    def test_categories_are_sorted_and_normalised(self):
        factors = {SOURCE_TEST_CONDITIONS: 1.1, "orbit_model": 1.2}
        result = assess_component("SEN01", 10.0, 60.0, factors)
        self.assertEqual(
            result["categories"], [SOURCE_ENVIRONMENT_MODEL, SOURCE_TEST_CONDITIONS]
        )

    def test_custom_required_minimum_can_fail_a_component(self):
        result = assess_component(
            "COTS1", 10.0, 40.0, {SOURCE_ENVIRONMENT_MODEL: 2.0}, required_min=3.0
        )
        self.assertEqual(result["status"], "FAIL")

    def test_pair_sequence_factors_accepted(self):
        result = assess_component(
            "REG01", 10.0, 40.0, [(SOURCE_ENVIRONMENT_MODEL, 1.5)]
        )
        self.assertAlmostEqual(result["combined_factor"], 1.5)
        self.assertEqual(result["status"], "PASS")

    def test_blank_name_raises(self):
        with self.assertRaises(ValueError):
            assess_component("  ", 10.0, 40.0, {SOURCE_ENVIRONMENT_MODEL: 1.2})

    def test_non_string_name_raises(self):
        with self.assertRaises(ValueError):
            assess_component(123, 10.0, 40.0, {SOURCE_ENVIRONMENT_MODEL: 1.2})

    def test_empty_factors_raise(self):
        with self.assertRaises(ValueError):
            assess_component("X", 10.0, 40.0, {})

    def test_zero_lot_tolerance_raises(self):
        with self.assertRaises(ValueError):
            assess_component("X", 10.0, 0.0, {SOURCE_ENVIRONMENT_MODEL: 1.2})


# ---------------------------------------------------------------------------
# assess_mission
# ---------------------------------------------------------------------------

class TestAssessMission(unittest.TestCase):

    def test_two_passing_components(self):
        components = [
            {"name": "A", "mean_tid": 10.0, "lot_tolerance": 60.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 1.5}},
            {"name": "B", "mean_tid": 8.0, "lot_tolerance": 50.0,
             "factors": {SOURCE_PART_VARIABILITY: 2.0}},
        ]
        summary = assess_mission(components)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["failed"], 0)
        self.assertTrue(summary["all_pass"])

    def test_one_failing_component_breaks_all_pass(self):
        components = [
            {"name": "A", "mean_tid": 10.0, "lot_tolerance": 60.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 1.5}},
            {"name": "B", "mean_tid": 10.0, "lot_tolerance": 30.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 2.0}},
        ]
        summary = assess_mission(components)
        self.assertFalse(summary["all_pass"])
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["results"][1]["status"], "FAIL")

    def test_borderline_count_tracks_exact_minimum(self):
        components = [
            {"name": "A", "mean_tid": 10.0, "lot_tolerance": 40.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 2.0}},
            {"name": "B", "mean_tid": 10.0, "lot_tolerance": 80.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 2.0}},
        ]
        summary = assess_mission(components)
        self.assertEqual(summary["borderline_count"], 1)

    def test_justification_required_lists_names(self):
        components = [
            {"name": "A", "mean_tid": 5.0, "lot_tolerance": 20.0,
             "factors": {SOURCE_TEST_CONDITIONS: 1.0}},
            {"name": "B", "mean_tid": 5.0, "lot_tolerance": 20.0,
             "factors": {SOURCE_TEST_CONDITIONS: 1.2}},
        ]
        summary = assess_mission(components)
        self.assertEqual(summary["justification_required"], ["A"])

    def test_per_component_required_minimum_override(self):
        components = [
            {"name": "COTS1", "mean_tid": 10.0, "lot_tolerance": 40.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 2.0}, "required_min": 3.0},
        ]
        summary = assess_mission(components)
        self.assertEqual(summary["failed"], 1)

    def test_mission_level_required_minimum_applies(self):
        components = [
            {"name": "A", "mean_tid": 10.0, "lot_tolerance": 40.0,
             "factors": {SOURCE_ENVIRONMENT_MODEL: 2.0}},
        ]
        summary = assess_mission(components, required_min=3.0)
        self.assertEqual(summary["failed"], 1)

    def test_empty_component_list_raises(self):
        with self.assertRaises(ValueError):
            assess_mission([])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            assess_mission({"name": "A"})

    def test_non_dict_component_raises(self):
        with self.assertRaises(ValueError):
            assess_mission(["A"])

    def test_missing_factors_key_raises(self):
        with self.assertRaises(ValueError):
            assess_mission([{"name": "A", "mean_tid": 10.0, "lot_tolerance": 40.0}])

    def test_missing_mean_tid_key_raises(self):
        with self.assertRaises(ValueError):
            assess_mission(
                [{"name": "A", "lot_tolerance": 40.0,
                  "factors": {SOURCE_ENVIRONMENT_MODEL: 1.2}}]
            )


if __name__ == "__main__":
    unittest.main()

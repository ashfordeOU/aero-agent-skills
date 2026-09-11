import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1011_params_logic import (
    categorize_parameter,
    check_parameter_set_completeness,
    map_parameter_interrelationships,
    assess_parameter_coverage,
    STANDARD_PARAM_CATEGORIES,
    REQUIRED_CATEGORIES,
)


class TestCategorizeParameter(unittest.TestCase):

    def test_direct_category_match_performance(self):
        self.assertEqual(categorize_parameter("performance"), "performance")

    def test_direct_category_match_workload(self):
        self.assertEqual(categorize_parameter("workload"), "workload")

    def test_direct_category_match_situation_awareness(self):
        self.assertEqual(categorize_parameter("situation_awareness"), "situation_awareness")

    def test_alias_mental_workload(self):
        self.assertEqual(categorize_parameter("mental_workload"), "workload")

    def test_alias_accuracy_maps_to_performance(self):
        self.assertEqual(categorize_parameter("accuracy"), "performance")

    def test_alias_sa_maps_to_situation_awareness(self):
        self.assertEqual(categorize_parameter("sa"), "situation_awareness")

    def test_alias_error_rate_maps_to_human_error(self):
        self.assertEqual(categorize_parameter("error_rate"), "human_error")

    def test_alias_hmi_maps_to_interface(self):
        self.assertEqual(categorize_parameter("hmi"), "interface")

    def test_alias_noise_maps_to_environment(self):
        self.assertEqual(categorize_parameter("noise"), "environment")

    def test_alias_comms_maps_to_communication(self):
        self.assertEqual(categorize_parameter("comms"), "communication")

    def test_leading_trailing_whitespace_stripped(self):
        self.assertEqual(categorize_parameter("  performance  "), "performance")

    def test_case_insensitive_upper(self):
        self.assertEqual(categorize_parameter("WORKLOAD"), "workload")

    def test_case_insensitive_mixed(self):
        self.assertEqual(categorize_parameter("Situation_Awareness"), "situation_awareness")

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_parameter("unknown_xyz_param")

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            categorize_parameter(42)

    def test_all_standard_categories_resolve(self):
        for cat in STANDARD_PARAM_CATEGORIES:
            self.assertEqual(categorize_parameter(cat), cat)


class TestCheckParameterSetCompleteness(unittest.TestCase):

    def _make_params(self, types):
        return [{"name": f"P{i}", "type": t} for i, t in enumerate(types)]

    def test_all_required_categories_no_findings(self):
        params = self._make_params([
            "performance", "workload", "situation_awareness", "human_error"
        ])
        result = check_parameter_set_completeness(params)
        self.assertEqual(result["missing"], set())
        required_findings = [f for f in result["findings"] if "Required HFE category" in f]
        self.assertEqual(required_findings, [])

    def test_missing_workload_flagged(self):
        params = self._make_params(["performance", "situation_awareness", "human_error"])
        result = check_parameter_set_completeness(params)
        self.assertIn("workload", result["missing"])

    def test_missing_performance_flagged(self):
        params = self._make_params(["workload", "situation_awareness", "human_error"])
        result = check_parameter_set_completeness(params)
        self.assertIn("performance", result["missing"])

    def test_empty_list_all_required_missing(self):
        result = check_parameter_set_completeness([])
        self.assertEqual(result["missing"], set(REQUIRED_CATEGORIES))

    def test_unrecognized_type_produces_finding(self):
        params = [{"name": "P1", "type": "nonsense_category_xyz"}]
        result = check_parameter_set_completeness(params)
        self.assertTrue(any("Unrecognized" in f for f in result["findings"]))

    def test_alias_counts_toward_category(self):
        params = self._make_params(["accuracy", "mental_workload", "sa", "error_rate"])
        result = check_parameter_set_completeness(params)
        self.assertEqual(result["missing"], set())

    def test_non_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_parameter_set_completeness("not a list")

    def test_non_dict_element_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_parameter_set_completeness(["string_element"])

    def test_missing_type_field_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_parameter_set_completeness([{"name": "P1", "value": 0.9}])

    def test_optional_categories_do_not_mask_missing_required(self):
        params = self._make_params(["training", "environment", "interface", "communication"])
        result = check_parameter_set_completeness(params)
        self.assertEqual(result["missing"], set(REQUIRED_CATEGORIES))

    def test_covered_set_reflects_resolved_categories(self):
        params = self._make_params(["accuracy", "workload", "human_error", "situation_awareness"])
        result = check_parameter_set_completeness(params)
        self.assertIn("performance", result["covered"])


class TestMapParameterInterrelationships(unittest.TestCase):

    def _make_params(self, types):
        return [{"name": f"P{i}", "type": t} for i, t in enumerate(types)]

    def test_workload_performance_pair_detected(self):
        params = self._make_params(["workload", "performance"])
        result = map_parameter_interrelationships(params)
        self.assertIn(("performance", "workload"), result["pairs"])

    def test_workload_human_error_pair_detected(self):
        params = self._make_params(["workload", "human_error"])
        result = map_parameter_interrelationships(params)
        self.assertIn(("human_error", "workload"), result["pairs"])

    def test_situation_awareness_human_error_pair_detected(self):
        params = self._make_params(["situation_awareness", "human_error"])
        result = map_parameter_interrelationships(params)
        self.assertIn(("human_error", "situation_awareness"), result["pairs"])

    def test_isolated_category_when_no_partner(self):
        params = self._make_params(["training"])
        result = map_parameter_interrelationships(params)
        self.assertIn("training", result["isolated"])

    def test_connected_category_not_in_isolated(self):
        params = self._make_params(["workload", "performance"])
        result = map_parameter_interrelationships(params)
        self.assertNotIn("workload", result["isolated"])
        self.assertNotIn("performance", result["isolated"])

    def test_empty_params_returns_empty(self):
        result = map_parameter_interrelationships([])
        self.assertEqual(result["pairs"], [])
        self.assertEqual(result["isolated"], [])

    def test_unrecognized_type_ignored_in_mapping(self):
        params = [{"name": "P1", "type": "workload"}, {"name": "P2", "type": "??bad??"}]
        result = map_parameter_interrelationships(params)
        self.assertIn("workload", result["isolated"])

    def test_environment_workload_pair_detected(self):
        params = self._make_params(["environment", "workload"])
        result = map_parameter_interrelationships(params)
        self.assertIn(("environment", "workload"), result["pairs"])

    def test_communication_situation_awareness_pair_detected(self):
        params = self._make_params(["communication", "situation_awareness"])
        result = map_parameter_interrelationships(params)
        self.assertIn(("communication", "situation_awareness"), result["pairs"])


class TestAssessParameterCoverage(unittest.TestCase):

    def test_full_phase_coverage_no_findings(self):
        phases = ["nominal", "contingency"]
        params = [
            {"name": "P1", "type": "workload", "phase": "nominal"},
            {"name": "P2", "type": "performance", "phase": "contingency"},
        ]
        result = assess_parameter_coverage(params, phases)
        self.assertEqual(result["uncovered_phases"], [])
        phase_findings = [f for f in result["findings"] if "no HFE parameters" in f]
        self.assertEqual(phase_findings, [])

    def test_uncovered_phase_flagged(self):
        phases = ["nominal", "contingency"]
        params = [{"name": "P1", "type": "workload", "phase": "nominal"}]
        result = assess_parameter_coverage(params, phases)
        self.assertIn("contingency", result["uncovered_phases"])

    def test_uncovered_phase_produces_finding(self):
        phases = ["nominal", "contingency"]
        params = [{"name": "P1", "type": "workload", "phase": "nominal"}]
        result = assess_parameter_coverage(params, phases)
        self.assertTrue(any("contingency" in f for f in result["findings"]))

    def test_no_phase_assignment_produces_finding(self):
        params = [{"name": "P1", "type": "workload"}]
        result = assess_parameter_coverage(params, ["nominal"])
        self.assertTrue(any("no phase assignment" in f for f in result["findings"]))

    def test_unknown_phase_reference_produces_finding(self):
        params = [{"name": "P1", "type": "workload", "phase": "mars_surface"}]
        result = assess_parameter_coverage(params, ["nominal"])
        self.assertTrue(any("unknown phase" in f for f in result["findings"]))

    def test_unknown_phase_does_not_cover_known_phase(self):
        params = [{"name": "P1", "type": "workload", "phase": "mars_surface"}]
        result = assess_parameter_coverage(params, ["nominal"])
        self.assertIn("nominal", result["uncovered_phases"])

    def test_empty_phases_list_no_findings(self):
        params = [{"name": "P1", "type": "workload", "phase": "nominal"}]
        result = assess_parameter_coverage(params, [])
        self.assertEqual(result["uncovered_phases"], [])

    def test_non_list_phases_raises_type_error(self):
        with self.assertRaises(TypeError):
            assess_parameter_coverage([], "nominal")

    def test_phase_coverage_maps_parameter_names(self):
        phases = ["nominal"]
        params = [
            {"name": "Alpha", "type": "workload", "phase": "nominal"},
            {"name": "Beta", "type": "performance", "phase": "nominal"},
        ]
        result = assess_parameter_coverage(params, phases)
        self.assertIn("Alpha", result["phase_coverage"]["nominal"])
        self.assertIn("Beta", result["phase_coverage"]["nominal"])

    def test_multiple_phases_all_covered(self):
        phases = ["nominal", "contingency", "maintenance"]
        params = [
            {"name": "P1", "type": "performance", "phase": "nominal"},
            {"name": "P2", "type": "workload", "phase": "contingency"},
            {"name": "P3", "type": "human_error", "phase": "maintenance"},
        ]
        result = assess_parameter_coverage(params, phases)
        self.assertEqual(result["uncovered_phases"], [])


if __name__ == "__main__":
    unittest.main()

"""
Gate 3 contract tests for e1011_hfe_role_logic.py
ECSS-E-ST-10-11C §4.3.1–4.3.2

Run: python3 test_e1011_hfe_role.py
All tests are deterministic, offline, and stdlib-only.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_hfe_role_logic import (
    REQUIRED_HFE_TASK_CATEGORIES,
    REQUIRED_INTERFACE_DISCIPLINES,
    REQUIRED_LIFECYCLE_PHASES,
    validate_hfe_role_definition,
    validate_hfe_interface,
    check_hfe_task_phase_coverage,
    identify_missing_interfaces,
    score_hfe_role_completeness,
)


class TestValidateHfeRoleDefinition(unittest.TestCase):

    def test_complete_role_definition_is_valid(self):
        role_def = {"tasks": list(REQUIRED_HFE_TASK_CATEGORIES)}
        result = validate_hfe_role_definition(role_def)
        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_categories"], [])
        self.assertEqual(result["findings"], [])

    def test_single_missing_category_is_flagged(self):
        tasks = list(REQUIRED_HFE_TASK_CATEGORIES - {"task_analysis"})
        result = validate_hfe_role_definition({"tasks": tasks})
        self.assertFalse(result["valid"])
        self.assertIn("task_analysis", result["missing_categories"])

    def test_empty_tasks_list_flags_all_required_categories(self):
        result = validate_hfe_role_definition({"tasks": []})
        self.assertFalse(result["valid"])
        self.assertEqual(
            set(result["missing_categories"]), REQUIRED_HFE_TASK_CATEGORIES
        )

    def test_extra_tasks_beyond_required_are_accepted(self):
        tasks = list(REQUIRED_HFE_TASK_CATEGORIES) + ["ergonomic_assessment"]
        result = validate_hfe_role_definition({"tasks": tasks})
        self.assertTrue(result["valid"])
        self.assertEqual(result["missing_categories"], [])

    def test_missing_tasks_key_treats_as_empty(self):
        result = validate_hfe_role_definition({})
        self.assertFalse(result["valid"])
        self.assertEqual(
            set(result["missing_categories"]), REQUIRED_HFE_TASK_CATEGORIES
        )

    def test_non_dict_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_hfe_role_definition(["requirements_definition"])

    def test_tasks_not_a_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_hfe_role_definition({"tasks": "requirements_definition"})

    def test_findings_contain_descriptive_message_for_each_gap(self):
        result = validate_hfe_role_definition({"tasks": []})
        for category in REQUIRED_HFE_TASK_CATEGORIES:
            self.assertTrue(
                any(category in f for f in result["findings"]),
                msg=f"No finding message for missing category '{category}'",
            )


class TestValidateHfeInterface(unittest.TestCase):

    def test_complete_interface_record_is_valid(self):
        iface = {
            "discipline": "systems_engineering",
            "contact": "SE Lead",
            "outputs": ["HFE requirements baseline"],
        }
        result = validate_hfe_interface(iface)
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])

    def test_missing_discipline_field_is_flagged(self):
        iface = {"contact": "SE Lead", "outputs": ["HFE requirements baseline"]}
        result = validate_hfe_interface(iface)
        self.assertFalse(result["valid"])
        self.assertTrue(any("discipline" in f for f in result["findings"]))

    def test_missing_contact_field_is_flagged(self):
        iface = {
            "discipline": "safety",
            "outputs": ["Human error hazard log"],
        }
        result = validate_hfe_interface(iface)
        self.assertFalse(result["valid"])
        self.assertTrue(any("contact" in f for f in result["findings"]))

    def test_empty_outputs_list_is_flagged(self):
        iface = {
            "discipline": "operations",
            "contact": "Ops Manager",
            "outputs": [],
        }
        result = validate_hfe_interface(iface)
        self.assertFalse(result["valid"])
        self.assertTrue(any("outputs" in f.lower() or "output" in f.lower()
                            for f in result["findings"]))

    def test_non_dict_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_hfe_interface("systems_engineering")

    def test_multiple_outputs_accepted(self):
        iface = {
            "discipline": "training",
            "contact": "Training Lead",
            "outputs": ["Training needs analysis", "Learnability report"],
        }
        result = validate_hfe_interface(iface)
        self.assertTrue(result["valid"])


class TestCheckHfeTaskPhaseCoverage(unittest.TestCase):

    def _full_task_list(self):
        return [{"phase": p, "category": "design_support"}
                for p in REQUIRED_LIFECYCLE_PHASES]

    def test_full_lifecycle_coverage_yields_no_uncovered_phases(self):
        result = check_hfe_task_phase_coverage(self._full_task_list())
        self.assertEqual(result["uncovered_phases"], [])
        self.assertEqual(result["invalid_entries"], [])

    def test_missing_phase_is_reported(self):
        tasks = [{"phase": p, "category": "design_support"}
                 for p in REQUIRED_LIFECYCLE_PHASES if p != "phase_a"]
        result = check_hfe_task_phase_coverage(tasks)
        self.assertIn("phase_a", result["uncovered_phases"])

    def test_empty_task_list_flags_all_required_phases(self):
        result = check_hfe_task_phase_coverage([])
        self.assertEqual(
            set(result["uncovered_phases"]), REQUIRED_LIFECYCLE_PHASES
        )

    def test_unrecognised_phase_identifier_is_an_invalid_entry(self):
        tasks = [{"phase": "phase_z", "category": "design_support"}]
        result = check_hfe_task_phase_coverage(tasks)
        self.assertIn(0, result["invalid_entries"])

    def test_task_entry_missing_phase_key_is_an_invalid_entry(self):
        tasks = [{"category": "design_support"}]
        result = check_hfe_task_phase_coverage(tasks)
        self.assertIn(0, result["invalid_entries"])

    def test_non_dict_task_entry_is_an_invalid_entry(self):
        tasks = ["phase_a"]
        result = check_hfe_task_phase_coverage(tasks)
        self.assertIn(0, result["invalid_entries"])

    def test_non_list_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_hfe_task_phase_coverage("phase_a")

    def test_covered_phases_contains_valid_assigned_phases(self):
        tasks = [
            {"phase": "phase_a", "category": "requirements_definition"},
            {"phase": "phase_b", "category": "task_analysis"},
        ]
        result = check_hfe_task_phase_coverage(tasks)
        self.assertIn("phase_a", result["covered_phases"])
        self.assertIn("phase_b", result["covered_phases"])


class TestIdentifyMissingInterfaces(unittest.TestCase):

    def test_all_required_disciplines_present_returns_empty_list(self):
        defined = list(REQUIRED_INTERFACE_DISCIPLINES)
        self.assertEqual(identify_missing_interfaces(defined), [])

    def test_missing_discipline_is_returned(self):
        defined = [d for d in REQUIRED_INTERFACE_DISCIPLINES if d != "safety"]
        result = identify_missing_interfaces(defined)
        self.assertIn("safety", result)

    def test_empty_defined_list_returns_all_required_disciplines(self):
        result = identify_missing_interfaces([])
        self.assertEqual(set(result), REQUIRED_INTERFACE_DISCIPLINES)

    def test_extra_disciplines_beyond_required_are_ignored(self):
        defined = list(REQUIRED_INTERFACE_DISCIPLINES) + ["ergonomics_team"]
        self.assertEqual(identify_missing_interfaces(defined), [])

    def test_non_list_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            identify_missing_interfaces("systems_engineering")

    def test_return_value_is_sorted(self):
        result = identify_missing_interfaces([])
        self.assertEqual(result, sorted(result))


class TestScoreHfeRoleCompleteness(unittest.TestCase):

    def _complete_role_def(self):
        return {"tasks": list(REQUIRED_HFE_TASK_CATEGORIES)}

    def _complete_interfaces(self):
        return list(REQUIRED_INTERFACE_DISCIPLINES)

    def _complete_tasks(self):
        return [{"phase": p, "category": "design_support"}
                for p in REQUIRED_LIFECYCLE_PHASES]

    def test_fully_complete_role_scores_one(self):
        result = score_hfe_role_completeness(
            self._complete_role_def(),
            self._complete_interfaces(),
            self._complete_tasks(),
        )
        self.assertAlmostEqual(result["score"], 1.0)
        self.assertEqual(result["findings"], [])

    def test_partial_role_scores_less_than_one(self):
        partial_role = {"tasks": ["requirements_definition"]}
        result = score_hfe_role_completeness(
            partial_role,
            self._complete_interfaces(),
            self._complete_tasks(),
        )
        self.assertLess(result["score"], 1.0)
        self.assertGreater(len(result["findings"]), 0)

    def test_missing_interfaces_lower_the_score(self):
        result_full = score_hfe_role_completeness(
            self._complete_role_def(),
            self._complete_interfaces(),
            self._complete_tasks(),
        )
        result_partial = score_hfe_role_completeness(
            self._complete_role_def(),
            [],
            self._complete_tasks(),
        )
        self.assertGreater(result_full["score"], result_partial["score"])

    def test_empty_everything_scores_zero(self):
        result = score_hfe_role_completeness({"tasks": []}, [], [])
        self.assertAlmostEqual(result["score"], 0.0)

    def test_findings_aggregate_all_gap_types(self):
        partial_role = {"tasks": []}
        result = score_hfe_role_completeness(partial_role, [], [])
        finding_text = " ".join(result["findings"])
        self.assertIn("task", finding_text.lower())
        self.assertIn("interface", finding_text.lower())
        self.assertIn("phase", finding_text.lower())

    def test_score_is_between_zero_and_one(self):
        partial_role = {"tasks": ["requirements_definition", "task_analysis"]}
        partial_ifaces = ["systems_engineering"]
        partial_tasks = [{"phase": "phase_a", "category": "requirements_definition"}]
        result = score_hfe_role_completeness(partial_role, partial_ifaces, partial_tasks)
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)


if __name__ == "__main__":
    unittest.main()

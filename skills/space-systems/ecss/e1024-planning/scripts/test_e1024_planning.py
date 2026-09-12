"""
test_e1024_planning.py — Offline unittest for e1024_planning_logic.py
ECSS-E-ST-10C §5.1 Interface Management Planning
Run: python3 test_e1024_planning.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1024_planning_logic import (
    validate_imp_fields,
    check_process_completeness,
    check_schedule_coverage,
    check_sep_integration,
    check_responsibility_matrix,
    assess_im_plan,
    REQUIRED_IMP_FIELDS,
    REQUIRED_PROCESS_STEPS,
    REQUIRED_PHASE_COVERAGE,
    INTERFACE_TYPES,
)


def _valid_plan():
    """Return a minimal IMP dict that passes all §5.1 checks."""
    return {
        "name": "Project X IMP",
        "purpose": "Define interface management approach for Project X",
        "scope": "All internal and external spacecraft interfaces",
        "responsibilities": {
            "mechanical": "Systems Engineer A",
            "electrical": "EPS Lead",
            "thermal": "Thermal Engineer",
            "data": "Software Lead",
            "rf": "RF Engineer",
            "software": "Software Lead",
            "operational": "Mission Operations Lead",
        },
        "process_steps": [
            "identify", "document", "review", "approve", "baseline", "control", "verify",
        ],
        "schedule": {
            "A": ["IMP draft issued"],
            "B": ["IMP baseline review", "ICDs issued"],
            "C": ["IMP revision 1", "ICD freeze"],
            "D": ["IMP revision 2", "ICD verification"],
        },
        "sep_reference": "SEP-PX-001 Rev A",
        "sep_im_section": "Section 4.3 Interface Management",
        "listed_as_deliverable": True,
    }


class TestValidateImpFields(unittest.TestCase):

    def test_valid_plan_returns_no_missing_fields(self):
        self.assertEqual(validate_imp_fields(_valid_plan()), [])

    def test_missing_purpose_is_flagged(self):
        plan = _valid_plan()
        del plan["purpose"]
        self.assertIn("purpose", validate_imp_fields(plan))

    def test_missing_sep_reference_is_flagged(self):
        plan = _valid_plan()
        del plan["sep_reference"]
        self.assertIn("sep_reference", validate_imp_fields(plan))

    def test_empty_plan_flags_all_required_fields(self):
        result = validate_imp_fields({})
        self.assertEqual(sorted(result), sorted(REQUIRED_IMP_FIELDS))

    def test_extra_fields_do_not_trigger_findings(self):
        plan = _valid_plan()
        plan["extra_unrequired_field"] = "some value"
        self.assertEqual(validate_imp_fields(plan), [])

    def test_non_dict_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_imp_fields("not a dict")


class TestCheckProcessCompleteness(unittest.TestCase):

    def test_all_steps_present_returns_empty(self):
        self.assertEqual(check_process_completeness(list(REQUIRED_PROCESS_STEPS)), [])

    def test_missing_baseline_step_flagged(self):
        steps = [s for s in REQUIRED_PROCESS_STEPS if s != "baseline"]
        self.assertIn("baseline", check_process_completeness(steps))

    def test_missing_verify_step_flagged(self):
        steps = [s for s in REQUIRED_PROCESS_STEPS if s != "verify"]
        self.assertIn("verify", check_process_completeness(steps))

    def test_empty_step_list_flags_all_required(self):
        result = check_process_completeness([])
        self.assertEqual(sorted(result), sorted(REQUIRED_PROCESS_STEPS))

    def test_step_matching_is_case_insensitive(self):
        steps = [s.upper() for s in REQUIRED_PROCESS_STEPS]
        self.assertEqual(check_process_completeness(steps), [])

    def test_mixed_case_steps_accepted(self):
        steps = ["Identify", "Document", "Review", "Approve", "Baseline", "Control", "Verify"]
        self.assertEqual(check_process_completeness(steps), [])


class TestCheckScheduleCoverage(unittest.TestCase):

    def test_all_required_phases_covered_returns_empty(self):
        schedule = {p: ["milestone-{}".format(p)] for p in REQUIRED_PHASE_COVERAGE}
        self.assertEqual(check_schedule_coverage(schedule), [])

    def test_missing_phase_B_flagged(self):
        schedule = {p: ["m-{}".format(p)] for p in REQUIRED_PHASE_COVERAGE if p != "B"}
        issues = check_schedule_coverage(schedule)
        self.assertTrue(any("B" in issue for issue in issues))

    def test_missing_phase_C_flagged(self):
        schedule = {p: ["m-{}".format(p)] for p in REQUIRED_PHASE_COVERAGE if p != "C"}
        issues = check_schedule_coverage(schedule)
        self.assertTrue(any("C" in issue for issue in issues))

    def test_phase_with_empty_milestone_list_flagged(self):
        schedule = {p: ["m-{}".format(p)] for p in REQUIRED_PHASE_COVERAGE}
        schedule["C"] = []
        issues = check_schedule_coverage(schedule)
        self.assertTrue(any("C" in issue for issue in issues))

    def test_extra_phases_beyond_required_are_allowed(self):
        schedule = {p: ["m-{}".format(p)] for p in REQUIRED_PHASE_COVERAGE}
        schedule["E"] = ["decommission IMP review"]
        self.assertEqual(check_schedule_coverage(schedule), [])

    def test_empty_schedule_flags_all_required_phases(self):
        issues = check_schedule_coverage({})
        self.assertEqual(len(issues), len(REQUIRED_PHASE_COVERAGE))

    def test_non_dict_schedule_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_schedule_coverage("not a dict")


class TestCheckSepIntegration(unittest.TestCase):

    def test_valid_sep_integration_returns_empty(self):
        self.assertEqual(check_sep_integration(_valid_plan()), [])

    def test_empty_sep_reference_flagged(self):
        plan = _valid_plan()
        plan["sep_reference"] = ""
        issues = check_sep_integration(plan)
        self.assertTrue(any("sep_reference" in issue for issue in issues))

    def test_whitespace_only_sep_reference_flagged(self):
        plan = _valid_plan()
        plan["sep_reference"] = "   "
        issues = check_sep_integration(plan)
        self.assertTrue(any("sep_reference" in issue for issue in issues))

    def test_imp_not_listed_as_deliverable_flagged(self):
        plan = _valid_plan()
        plan["listed_as_deliverable"] = False
        issues = check_sep_integration(plan)
        self.assertTrue(any("deliverable" in issue for issue in issues))

    def test_missing_sep_im_section_flagged(self):
        plan = _valid_plan()
        del plan["sep_im_section"]
        issues = check_sep_integration(plan)
        self.assertTrue(any("sep_im_section" in issue for issue in issues))

    def test_absent_listed_as_deliverable_field_flagged(self):
        plan = _valid_plan()
        del plan["listed_as_deliverable"]
        issues = check_sep_integration(plan)
        self.assertTrue(any("listed_as_deliverable" in issue for issue in issues))


class TestCheckResponsibilityMatrix(unittest.TestCase):

    def test_complete_matrix_returns_empty(self):
        self.assertEqual(check_responsibility_matrix(_valid_plan()["responsibilities"]), [])

    def test_missing_rf_owner_flagged(self):
        matrix = _valid_plan()["responsibilities"]
        del matrix["rf"]
        issues = check_responsibility_matrix(matrix)
        self.assertTrue(any("rf" in issue for issue in issues))

    def test_empty_owner_string_flagged(self):
        matrix = _valid_plan()["responsibilities"]
        matrix["thermal"] = ""
        issues = check_responsibility_matrix(matrix)
        self.assertTrue(any("thermal" in issue for issue in issues))

    def test_whitespace_only_owner_flagged(self):
        matrix = _valid_plan()["responsibilities"]
        matrix["software"] = "   "
        issues = check_responsibility_matrix(matrix)
        self.assertTrue(any("software" in issue for issue in issues))

    def test_empty_matrix_flags_all_interface_types(self):
        issues = check_responsibility_matrix({})
        self.assertEqual(len(issues), len(INTERFACE_TYPES))


class TestAssessImPlan(unittest.TestCase):

    def test_valid_plan_is_compliant(self):
        result = assess_im_plan(_valid_plan())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["field_issues"], [])
        self.assertEqual(result["process_issues"], [])
        self.assertEqual(result["schedule_issues"], [])
        self.assertEqual(result["sep_issues"], [])
        self.assertEqual(result["responsibility_issues"], [])

    def test_plan_missing_schedule_field_is_not_compliant(self):
        plan = _valid_plan()
        del plan["schedule"]
        result = assess_im_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertIn("schedule", result["field_issues"])

    def test_plan_with_incomplete_process_is_not_compliant(self):
        plan = _valid_plan()
        plan["process_steps"] = ["identify", "document"]
        result = assess_im_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["process_issues"]), 0)

    def test_plan_with_uncovered_schedule_phase_is_not_compliant(self):
        plan = _valid_plan()
        del plan["schedule"]["B"]
        result = assess_im_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["schedule_issues"]), 0)

    def test_plan_with_sep_not_deliverable_is_not_compliant(self):
        plan = _valid_plan()
        plan["listed_as_deliverable"] = False
        result = assess_im_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["sep_issues"]), 0)

    def test_plan_with_missing_interface_owner_is_not_compliant(self):
        plan = _valid_plan()
        del plan["responsibilities"]["operational"]
        result = assess_im_plan(plan)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["responsibility_issues"]), 0)

    def test_assess_returns_all_expected_keys(self):
        result = assess_im_plan(_valid_plan())
        expected_keys = {
            "field_issues", "process_issues", "schedule_issues",
            "sep_issues", "responsibility_issues", "compliant",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_non_dict_plan_raises_type_error(self):
        with self.assertRaises(TypeError):
            assess_im_plan(["not", "a", "dict"])


if __name__ == "__main__":
    unittest.main()

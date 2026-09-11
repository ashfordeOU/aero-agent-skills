"""
Offline deterministic contract tests for e1011_hcd_planning_logic.

Run:  python3 test_e1011_hcd_planning.py
Must print OK with 10+ passing tests.  No network access, no third-party deps.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_hcd_planning_logic import (
    REQUIRED_ACTIVITIES,
    PROJECT_PHASES,
    VALID_ROLES,
    MANDATORY_ROLE,
    ActivityError,
    ScheduleError,
    ResponsibilityError,
    HCDPlanError,
    validate_activity_list,
    validate_phase,
    validate_schedule_mapping,
    validate_phase_order,
    validate_responsibility_assignment,
    compute_schedule_coverage,
    summarize_plan_completeness,
    validate_hcd_plan,
)

# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

_VALID_SCHEDULE = {
    "context_of_use_analysis": "A",
    "user_requirements_specification": "B",
    "design_solution": "C",
    "evaluation": "D",
    "implementation_verification": "E",
}

_VALID_RESPONSIBILITIES = {
    a: ["hf_specialist", "system_engineer"] for a in REQUIRED_ACTIVITIES
}

_VALID_PLAN = {
    "activities": list(REQUIRED_ACTIVITIES),
    "schedule": _VALID_SCHEDULE,
    "responsibilities": _VALID_RESPONSIBILITIES,
}


# ---------------------------------------------------------------------------
# Activity list tests
# ---------------------------------------------------------------------------

class TestActivityList(unittest.TestCase):

    def test_complete_activity_list_passes(self):
        validate_activity_list(list(REQUIRED_ACTIVITIES))

    def test_missing_one_activity_raises(self):
        incomplete = [a for a in REQUIRED_ACTIVITIES if a != "evaluation"]
        with self.assertRaises(ActivityError):
            validate_activity_list(incomplete)

    def test_empty_activity_list_raises(self):
        with self.assertRaises(ActivityError):
            validate_activity_list([])

    def test_duplicate_activity_raises(self):
        duped = list(REQUIRED_ACTIVITIES) + ["context_of_use_analysis"]
        with self.assertRaises(ActivityError):
            validate_activity_list(duped)

    def test_extra_activity_beyond_required_is_accepted(self):
        extended = list(REQUIRED_ACTIVITIES) + ["stakeholder_review"]
        validate_activity_list(extended)  # no exception

    def test_activity_error_is_subclass_of_hcd_plan_error(self):
        self.assertTrue(issubclass(ActivityError, HCDPlanError))

    def test_activity_error_is_subclass_of_value_error(self):
        self.assertTrue(issubclass(ActivityError, ValueError))


# ---------------------------------------------------------------------------
# Phase validation tests
# ---------------------------------------------------------------------------

class TestPhaseValidation(unittest.TestCase):

    def test_all_valid_phases_accepted(self):
        for phase in PROJECT_PHASES:
            validate_phase(phase)  # must not raise

    def test_unrecognised_phase_letter_raises(self):
        with self.assertRaises(ScheduleError):
            validate_phase("X")

    def test_lowercase_phase_raises(self):
        with self.assertRaises(ScheduleError):
            validate_phase("a")

    def test_empty_string_phase_raises(self):
        with self.assertRaises(ScheduleError):
            validate_phase("")

    def test_numeric_string_not_in_set_raises(self):
        with self.assertRaises(ScheduleError):
            validate_phase("1")

    def test_schedule_error_is_subclass_of_hcd_plan_error(self):
        self.assertTrue(issubclass(ScheduleError, HCDPlanError))


# ---------------------------------------------------------------------------
# Schedule mapping tests
# ---------------------------------------------------------------------------

class TestScheduleMapping(unittest.TestCase):

    def test_valid_schedule_passes(self):
        schedule = {a: "B" for a in REQUIRED_ACTIVITIES}
        validate_schedule_mapping(schedule)

    def test_invalid_phase_in_schedule_raises(self):
        schedule = {"context_of_use_analysis": "Z"}
        with self.assertRaises(ScheduleError):
            validate_schedule_mapping(schedule)

    def test_empty_schedule_passes(self):
        validate_schedule_mapping({})  # nothing to validate — no error


# ---------------------------------------------------------------------------
# Phase order tests
# ---------------------------------------------------------------------------

class TestPhaseOrder(unittest.TestCase):

    def test_strictly_increasing_phase_order_passes(self):
        validate_phase_order(_VALID_SCHEDULE)

    def test_evaluation_before_design_raises(self):
        bad = dict(_VALID_SCHEDULE)
        bad["design_solution"] = "D"
        bad["evaluation"] = "B"
        with self.assertRaises(ScheduleError):
            validate_phase_order(bad)

    def test_requirements_before_context_raises(self):
        bad = {
            "context_of_use_analysis": "C",
            "user_requirements_specification": "A",
        }
        with self.assertRaises(ScheduleError):
            validate_phase_order(bad)

    def test_same_phase_for_constrained_pair_passes(self):
        schedule = {
            "design_solution": "C",
            "evaluation": "C",
        }
        validate_phase_order(schedule)  # equal phases are acceptable

    def test_constraint_skipped_when_activity_absent(self):
        # Only one side of a constraint is present — no error expected
        validate_phase_order({"design_solution": "C"})


# ---------------------------------------------------------------------------
# Responsibility assignment tests
# ---------------------------------------------------------------------------

class TestResponsibilityAssignment(unittest.TestCase):

    def test_valid_single_role_assignment_passes(self):
        responsibilities = {a: ["hf_specialist"] for a in REQUIRED_ACTIVITIES}
        validate_responsibility_assignment(responsibilities)

    def test_empty_role_list_raises(self):
        with self.assertRaises(ResponsibilityError):
            validate_responsibility_assignment({"context_of_use_analysis": []})

    def test_missing_hf_specialist_raises(self):
        with self.assertRaises(ResponsibilityError):
            validate_responsibility_assignment(
                {"context_of_use_analysis": ["project_manager"]}
            )

    def test_unrecognised_role_raises(self):
        with self.assertRaises(ResponsibilityError):
            validate_responsibility_assignment(
                {"context_of_use_analysis": ["hf_specialist", "shadow_analyst"]}
            )

    def test_all_valid_roles_accepted_together(self):
        validate_responsibility_assignment(
            {"context_of_use_analysis": sorted(VALID_ROLES)}
        )

    def test_responsibility_error_is_subclass_of_hcd_plan_error(self):
        self.assertTrue(issubclass(ResponsibilityError, HCDPlanError))


# ---------------------------------------------------------------------------
# Schedule coverage tests
# ---------------------------------------------------------------------------

class TestScheduleCoverage(unittest.TestCase):

    def test_coverage_maps_activity_to_correct_phase(self):
        coverage = compute_schedule_coverage({"context_of_use_analysis": "A"})
        self.assertIn("context_of_use_analysis", coverage["A"])

    def test_empty_schedule_returns_empty_lists_per_phase(self):
        coverage = compute_schedule_coverage({})
        for phase in PROJECT_PHASES:
            self.assertEqual(coverage[phase], [])

    def test_coverage_keys_equal_all_project_phases(self):
        coverage = compute_schedule_coverage(_VALID_SCHEDULE)
        self.assertEqual(set(coverage.keys()), set(PROJECT_PHASES))

    def test_multiple_activities_same_phase_grouped_correctly(self):
        schedule = {
            "context_of_use_analysis": "B",
            "user_requirements_specification": "B",
        }
        coverage = compute_schedule_coverage(schedule)
        self.assertEqual(len(coverage["B"]), 2)


# ---------------------------------------------------------------------------
# Full-plan validation and summary tests
# ---------------------------------------------------------------------------

class TestFullPlanValidation(unittest.TestCase):

    def test_valid_plan_passes_without_exception(self):
        validate_hcd_plan(_VALID_PLAN)

    def test_summary_of_valid_plan_has_no_errors(self):
        summary = summarize_plan_completeness(_VALID_PLAN)
        self.assertEqual(summary["errors"], [])
        self.assertEqual(summary["missing_activities"], [])

    def test_summary_of_valid_plan_reports_correct_activity_count(self):
        summary = summarize_plan_completeness(_VALID_PLAN)
        self.assertEqual(summary["activity_count"], len(REQUIRED_ACTIVITIES))

    def test_summary_of_incomplete_plan_reports_missing_activities(self):
        plan = {
            "activities": ["context_of_use_analysis"],
            "schedule": {"context_of_use_analysis": "A"},
            "responsibilities": {"context_of_use_analysis": ["hf_specialist"]},
        }
        summary = summarize_plan_completeness(plan)
        self.assertGreater(len(summary["missing_activities"]), 0)
        self.assertGreater(len(summary["errors"]), 0)

    def test_summary_phases_used_reflects_schedule(self):
        summary = summarize_plan_completeness(_VALID_PLAN)
        self.assertIn("A", summary["phases_used"])
        self.assertIn("D", summary["phases_used"])

    def test_plan_with_invalid_phase_summary_records_error(self):
        plan = dict(_VALID_PLAN)
        plan["schedule"] = dict(_VALID_SCHEDULE, context_of_use_analysis="Z")
        summary = summarize_plan_completeness(plan)
        self.assertGreater(len(summary["errors"]), 0)

    def test_plan_missing_hf_specialist_summary_records_error(self):
        bad_resp = {a: ["project_manager"] for a in REQUIRED_ACTIVITIES}
        plan = dict(_VALID_PLAN, responsibilities=bad_resp)
        summary = summarize_plan_completeness(plan)
        self.assertGreater(len(summary["errors"]), 0)

    def test_mandatory_role_constant_is_hf_specialist(self):
        self.assertEqual(MANDATORY_ROLE, "hf_specialist")

    def test_required_activities_tuple_has_five_entries(self):
        self.assertEqual(len(REQUIRED_ACTIVITIES), 5)

    def test_project_phases_tuple_has_seven_entries(self):
        self.assertEqual(len(PROJECT_PHASES), 7)


if __name__ == "__main__":
    unittest.main()

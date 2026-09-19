#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-development-plan-data-item.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_development_plan_data_item.py
"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_development_plan_data_item_logic import (  # noqa: E402
    MANDATORY_SECTIONS,
    QUALIFIED,
    UNDER_QUALIFICATION,
    UNQUALIFIED,
    evaluate_development_plan,
    normalize_qualification_state,
    plan_span_days,
    schedule_slack_days,
    validate_organisation,
    validate_schedule,
    validate_tasks,
    validate_tooling,
    within_limit,
)


def base_plan():
    return {
        "organisation": [
            {
                "role": "design-lead",
                "holder": "role holder A",
                "responsibilities": ["device architecture"],
            },
            {
                "role": "verification-lead",
                "holder": "role holder B",
                "responsibilities": ["verification campaign"],
            },
        ],
        "tooling": [
            {
                "id": "schematic-capture",
                "name": "capture suite",
                "version": "3.1",
                "qualification_status": "qualified",
            },
            {
                "id": "thermal-solver",
                "name": "solver",
                "version": "7.0",
                "qualification_status": "qualified",
            },
        ],
        "schedule": [
            {"milestone": "PDR", "day": 60},
            {"milestone": "CDR", "day": 180},
        ],
        "tasks": [
            {
                "id": "T-1",
                "title": "device architecture",
                "owner_role": "design-lead",
                "tools": ["schematic-capture"],
                "start_day": 0,
                "finish_day": 50,
                "milestone": "PDR",
            },
            {
                "id": "T-2",
                "title": "thermal analysis",
                "owner_role": "verification-lead",
                "tools": ["thermal-solver"],
                "start_day": 60,
                "finish_day": 170,
                "milestone": "CDR",
            },
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestQualificationState(unittest.TestCase):
    def test_qualified_passes_through(self):
        self.assertEqual(normalize_qualification_state("qualified"), QUALIFIED)

    def test_spacing_and_case_fold(self):
        self.assertEqual(
            normalize_qualification_state("  Under   Qualification "),
            UNDER_QUALIFICATION,
        )

    def test_not_qualified_folds(self):
        self.assertEqual(normalize_qualification_state("not qualified"), UNQUALIFIED)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_qualification_state("probably fine")

    def test_non_string_state_rejected(self):
        with self.assertRaises(ValueError):
            normalize_qualification_state(None)


class TestOrganisation(unittest.TestCase):
    def test_roster_resolves(self):
        roster = validate_organisation(base_plan()["organisation"])
        self.assertEqual(sorted(roster), ["design-lead", "verification-lead"])

    def test_duplicate_role_rejected(self):
        entries = base_plan()["organisation"]
        entries.append({"role": "design-lead", "responsibilities": ["x"]})
        with self.assertRaises(ValueError):
            validate_organisation(entries)

    def test_role_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_organisation([{"role": "   "}])

    def test_unknown_role_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_organisation([{"role": "a", "grade": "senior"}])

    def test_non_list_organisation_rejected(self):
        with self.assertRaises(ValueError):
            validate_organisation({"role": "a"})


class TestTooling(unittest.TestCase):
    def test_tooling_resolves(self):
        tools = validate_tooling(base_plan()["tooling"])
        self.assertEqual(tools["thermal-solver"]["qualification_status"], QUALIFIED)

    def test_missing_state_defaults_to_unqualified(self):
        tools = validate_tooling([{"id": "t1"}])
        self.assertEqual(tools["t1"]["qualification_status"], UNQUALIFIED)

    def test_duplicate_tool_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_tooling([{"id": "t1"}, {"id": "t1"}])

    def test_tool_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_tooling([{"name": "nameless"}])

    def test_unknown_tool_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_tooling([{"id": "t1", "licence": "site"}])


class TestSchedule(unittest.TestCase):
    def test_schedule_keeps_declared_order(self):
        milestones = validate_schedule(base_plan()["schedule"])
        self.assertEqual([m["milestone"] for m in milestones], ["PDR", "CDR"])

    def test_duplicate_milestone_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"milestone": "PDR", "day": 1}, {"milestone": "PDR", "day": 2}])

    def test_negative_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"milestone": "PDR", "day": -1}])

    def test_missing_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"milestone": "PDR"}])

    def test_boolean_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_schedule([{"milestone": "PDR", "day": True}])


class TestTasks(unittest.TestCase):
    def test_tasks_resolve(self):
        tasks = validate_tasks(base_plan()["tasks"])
        self.assertEqual([t["id"] for t in tasks], ["T-1", "T-2"])

    def test_duplicate_task_id_rejected(self):
        entries = base_plan()["tasks"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_tasks(entries)

    def test_task_without_finish_day_rejected(self):
        entries = base_plan()["tasks"]
        del entries[0]["finish_day"]
        with self.assertRaises(ValueError):
            validate_tasks(entries)

    def test_non_list_tools_rejected(self):
        entries = base_plan()["tasks"]
        entries[0]["tools"] = "schematic-capture"
        with self.assertRaises(ValueError):
            validate_tasks(entries)

    def test_unknown_task_key_rejected(self):
        entries = base_plan()["tasks"]
        entries[0]["effort_hours"] = 10
        with self.assertRaises(ValueError):
            validate_tasks(entries)


class TestSpanAndSlack(unittest.TestCase):
    def test_span_is_first_start_to_last_finish(self):
        tasks = validate_tasks(base_plan()["tasks"])
        self.assertAlmostEqual(plan_span_days(tasks), 170.0, places=12)

    def test_slack_is_last_milestone_minus_last_finish(self):
        plan = base_plan()
        tasks = validate_tasks(plan["tasks"])
        milestones = validate_schedule(plan["schedule"])
        self.assertAlmostEqual(schedule_slack_days(tasks, milestones), 10.0, places=12)

    def test_span_needs_a_task(self):
        with self.assertRaises(ValueError):
            plan_span_days([])

    def test_slack_needs_a_milestone(self):
        tasks = validate_tasks(base_plan()["tasks"])
        with self.assertRaises(ValueError):
            schedule_slack_days(tasks, [])

    def test_within_limit_accepts_an_exact_landing(self):
        self.assertTrue(within_limit(0.1 + 0.2, 0.3))


class TestEvaluatePlan(unittest.TestCase):
    def test_a_coherent_plan_is_complete(self):
        result = evaluate_development_plan(base_plan())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])

    def test_counts_are_reported(self):
        result = evaluate_development_plan(base_plan())
        self.assertEqual(result["role_count"], 2)
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["tool_count"], 2)
        self.assertEqual(result["milestone_count"], 2)

    def test_absent_area_is_reported(self):
        plan = base_plan()
        del plan["tooling"]
        result = evaluate_development_plan(plan)
        self.assertIn("mandatory-section-absent", codes(result))

    def test_empty_area_is_reported(self):
        plan = base_plan()
        plan["organisation"] = []
        result = evaluate_development_plan(plan)
        self.assertIn("mandatory-section-empty", codes(result))

    def test_owner_outside_the_organisation_is_caught(self):
        plan = base_plan()
        plan["tasks"][0]["owner_role"] = "systems-lead"
        result = evaluate_development_plan(plan)
        self.assertIn("task-owner-not-in-organisation", codes(result))

    def test_task_with_no_owner_is_caught(self):
        plan = base_plan()
        plan["tasks"][0]["owner_role"] = ""
        result = evaluate_development_plan(plan)
        self.assertIn("task-without-owner", codes(result))

    def test_undeclared_tool_is_caught(self):
        plan = base_plan()
        plan["tasks"][0]["tools"] = ["spice-deck"]
        result = evaluate_development_plan(plan)
        self.assertIn("task-tool-not-declared", codes(result))

    def test_unqualified_tool_in_use_is_caught(self):
        plan = base_plan()
        plan["tooling"][1]["qualification_status"] = "under qualification"
        result = evaluate_development_plan(plan)
        self.assertIn("task-uses-unqualified-tool", codes(result))

    def test_tool_nobody_uses_is_caught(self):
        plan = base_plan()
        plan["tooling"].append({"id": "spare-tool", "qualification_status": "qualified"})
        result = evaluate_development_plan(plan)
        self.assertIn("tool-not-used-by-any-task", codes(result))

    def test_role_owning_nothing_is_caught(self):
        plan = base_plan()
        plan["organisation"].append(
            {"role": "product-assurance", "responsibilities": ["audits"]}
        )
        result = evaluate_development_plan(plan)
        self.assertIn("role-without-task", codes(result))

    def test_role_without_responsibilities_is_caught(self):
        plan = base_plan()
        plan["organisation"][0]["responsibilities"] = []
        result = evaluate_development_plan(plan)
        self.assertIn("role-without-responsibilities", codes(result))

    def test_task_overrunning_its_milestone_is_caught(self):
        plan = base_plan()
        plan["tasks"][0]["finish_day"] = 90
        result = evaluate_development_plan(plan)
        self.assertIn("task-overruns-its-milestone", codes(result))

    def test_task_finishing_exactly_on_the_milestone_passes(self):
        plan = base_plan()
        plan["tasks"][0]["finish_day"] = 60
        result = evaluate_development_plan(plan)
        self.assertNotIn("task-overruns-its-milestone", codes(result))

    def test_task_pointing_at_an_undeclared_milestone_is_caught(self):
        plan = base_plan()
        plan["tasks"][1]["milestone"] = "QR"
        result = evaluate_development_plan(plan)
        self.assertIn("task-milestone-not-in-schedule", codes(result))

    def test_task_with_no_milestone_is_caught(self):
        plan = base_plan()
        plan["tasks"][1]["milestone"] = ""
        result = evaluate_development_plan(plan)
        self.assertIn("task-without-milestone", codes(result))

    def test_zero_length_task_is_caught(self):
        plan = base_plan()
        plan["tasks"][0]["finish_day"] = plan["tasks"][0]["start_day"]
        result = evaluate_development_plan(plan)
        self.assertIn("task-with-non-positive-duration", codes(result))

    def test_milestones_out_of_order_are_caught(self):
        plan = base_plan()
        plan["schedule"][1]["day"] = 30
        result = evaluate_development_plan(plan)
        self.assertIn("schedule-out-of-order", codes(result))

    def test_span_and_slack_reach_the_result(self):
        result = evaluate_development_plan(base_plan())
        self.assertAlmostEqual(result["span_days"], 170.0, places=12)
        self.assertAlmostEqual(result["slack_days"], 10.0, places=12)

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["budget"] = 1
        with self.assertRaises(ValueError):
            evaluate_development_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_development_plan([("tasks", [])])

    def test_base_plan_is_not_mutated_by_evaluation(self):
        plan = base_plan()
        before = copy.deepcopy(plan)
        evaluate_development_plan(plan)
        self.assertEqual(plan, before)

    def test_every_mandatory_area_is_named(self):
        self.assertEqual(
            sorted(MANDATORY_SECTIONS),
            ["organisation", "schedule", "tasks", "tooling"],
        )


if __name__ == "__main__":
    unittest.main()

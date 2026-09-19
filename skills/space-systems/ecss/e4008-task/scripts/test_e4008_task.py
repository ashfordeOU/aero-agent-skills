#!/usr/bin/env python3
"""Contract test for schedule tasks in an SMP schedule (offline)."""

import copy
import unittest

from e4008_task_logic import (
    FINDING_ACTIVITY_DUPLICATE,
    FINDING_ADVANCES_TIME,
    FINDING_BLOCKING,
    FINDING_ENTRY_UNRESOLVED,
    FINDING_STEP_KIND,
    FINDING_STEP_UNNAMED,
    FINDING_TASK_CYCLE,
    FINDING_TASK_DUPLICATE,
    FINDING_TASK_EMPTY,
    FINDING_TASK_UNNAMED,
    FINDING_TASK_UNRESOLVED,
    STEP_KINDS,
    VERDICT_REJECTED,
    VERDICT_SCHEDULABLE,
    evaluate_task_set,
    execution_order,
    find_invocation_cycles,
    index_tasks,
    invoked_tasks,
    task_steps,
)

TASKS = [
    {
        "name": "sample-housekeeping",
        "steps": [
            {"kind": "activity", "name": "latch-counters"},
            {"kind": "activity", "name": "read-temperatures"},
            {"kind": "task", "target": "publish"},
        ],
    },
    {
        "name": "publish",
        "steps": [{"kind": "activity", "name": "emit-packet"}],
    },
]

ENTRIES = [{"name": "hk-tick", "task": "sample-housekeeping"}]


def _tasks(*extra):
    return copy.deepcopy(TASKS) + [copy.deepcopy(item) for item in extra]


def _codes(result):
    return set(result["finding_codes"])


class IndexTests(unittest.TestCase):
    def test_the_reference_task_set_indexes_cleanly(self):
        index, findings = index_tasks(TASKS)
        self.assertEqual(sorted(index), ["publish", "sample-housekeeping"])
        self.assertEqual(findings, [])

    def test_an_unnamed_task_is_reported(self):
        case = _tasks({"steps": [{"kind": "activity", "name": "x"}]})
        _index, findings = index_tasks(case)
        self.assertEqual(findings[0]["code"], FINDING_TASK_UNNAMED)

    def test_a_duplicate_task_name_is_reported(self):
        case = _tasks(copy.deepcopy(TASKS[1]))
        _index, findings = index_tasks(case)
        self.assertEqual(findings[0]["code"], FINDING_TASK_DUPLICATE)

    def test_an_empty_task_list_raises(self):
        with self.assertRaises(ValueError):
            index_tasks([])

    def test_a_non_list_task_set_raises(self):
        with self.assertRaises(ValueError):
            index_tasks(TASKS[0])

    def test_task_steps_are_returned_in_declared_order(self):
        steps = task_steps(TASKS[0])
        self.assertEqual(steps[0]["name"], "latch-counters")
        self.assertEqual(len(steps), 3)

    def test_invoked_tasks_lists_only_task_steps(self):
        self.assertEqual(invoked_tasks(TASKS[0]), ["publish"])
        self.assertEqual(invoked_tasks(TASKS[1]), [])


class OrderTests(unittest.TestCase):
    def test_a_task_expands_into_a_single_ordered_activity_sequence(self):
        index, _findings = index_tasks(TASKS)
        self.assertEqual(
            execution_order("sample-housekeeping", index),
            [
                "sample-housekeeping/latch-counters",
                "sample-housekeeping/read-temperatures",
                "publish/emit-packet",
            ],
        )

    def test_the_order_follows_the_declared_step_order_not_the_task_names(self):
        case = _tasks()
        case[0]["steps"] = list(reversed(case[0]["steps"]))
        index, _findings = index_tasks(case)
        self.assertEqual(
            execution_order("sample-housekeeping", index)[0], "publish/emit-packet"
        )

    def test_expanding_an_undeclared_task_raises(self):
        index, _findings = index_tasks(TASKS)
        with self.assertRaises(ValueError):
            execution_order("teardown", index)

    def test_expanding_a_cyclic_invocation_raises_instead_of_truncating(self):
        case = _tasks()
        case[1]["steps"].append({"kind": "task", "target": "sample-housekeeping"})
        index, _findings = index_tasks(case)
        with self.assertRaises(ValueError):
            execution_order("sample-housekeeping", index)

    def test_an_unknown_step_kind_raises_during_expansion(self):
        case = _tasks()
        case[1]["steps"] = [{"kind": "event", "name": "emit-packet"}]
        index, _findings = index_tasks(case)
        with self.assertRaises(ValueError):
            execution_order("publish", index)

    def test_an_activity_step_without_a_name_raises_during_expansion(self):
        case = _tasks()
        case[1]["steps"] = [{"kind": "activity"}]
        index, _findings = index_tasks(case)
        with self.assertRaises(ValueError):
            execution_order("publish", index)


class CycleTests(unittest.TestCase):
    def test_an_acyclic_task_set_reports_no_cycle(self):
        index, _findings = index_tasks(TASKS)
        self.assertEqual(find_invocation_cycles(index), [])

    def test_a_two_task_cycle_is_found(self):
        case = _tasks()
        case[1]["steps"].append({"kind": "task", "target": "sample-housekeeping"})
        index, _findings = index_tasks(case)
        self.assertEqual(len(find_invocation_cycles(index)), 1)

    def test_a_self_invoking_task_is_a_cycle(self):
        case = _tasks({"name": "loop", "steps": [{"kind": "task", "target": "loop"}]})
        index, _findings = index_tasks(case)
        self.assertEqual(len(find_invocation_cycles(index)), 1)

    def test_a_three_task_cycle_is_reported_once(self):
        case = [
            {"name": "a", "steps": [{"kind": "task", "target": "b"}]},
            {"name": "b", "steps": [{"kind": "task", "target": "c"}]},
            {"name": "c", "steps": [{"kind": "task", "target": "a"}]},
        ]
        index, _findings = index_tasks(case)
        self.assertEqual(len(find_invocation_cycles(index)), 1)


class TaskSetTests(unittest.TestCase):
    def test_the_reference_task_set_is_schedulable(self):
        result = evaluate_task_set(TASKS, ENTRIES)
        self.assertTrue(result["schedulable"])
        self.assertEqual(result["verdict"], VERDICT_SCHEDULABLE)
        self.assertEqual(result["findings"], [])

    def test_the_execution_order_is_reported_per_task(self):
        result = evaluate_task_set(TASKS, ENTRIES)
        self.assertEqual(result["execution_orders"]["publish"], ["publish/emit-packet"])

    def test_every_step_kind_constant_is_accepted_by_the_checker(self):
        self.assertEqual(sorted(STEP_KINDS), ["activity", "task"])

    def test_an_empty_task_is_a_finding(self):
        case = _tasks({"name": "idle", "steps": []})
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_TASK_EMPTY, _codes(result))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_an_unknown_step_kind_is_a_finding(self):
        case = _tasks()
        case[1]["steps"] = [{"kind": "event", "name": "emit-packet"}]
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_STEP_KIND, _codes(result))

    def test_a_step_without_a_name_is_a_finding(self):
        case = _tasks()
        case[1]["steps"] = [{"kind": "activity"}]
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_STEP_UNNAMED, _codes(result))

    def test_a_repeated_activity_name_inside_one_task_is_a_finding(self):
        case = _tasks()
        case[0]["steps"].append({"kind": "activity", "name": "latch-counters"})
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_ACTIVITY_DUPLICATE, _codes(result))

    def test_an_unresolved_task_invocation_is_a_finding(self):
        case = _tasks()
        case[0]["steps"][2]["target"] = "broadcast"
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_TASK_UNRESOLVED, _codes(result))

    def test_an_invocation_cycle_is_a_finding_and_no_order_is_produced(self):
        case = _tasks()
        case[1]["steps"].append({"kind": "task", "target": "sample-housekeeping"})
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_TASK_CYCLE, _codes(result))
        self.assertEqual(result["execution_orders"], {})

    def test_a_step_that_advances_simulated_time_is_a_finding(self):
        case = _tasks()
        case[1]["steps"][0]["duration_ns"] = 1000
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_ADVANCES_TIME, _codes(result))

    def test_a_zero_duration_step_is_not_a_finding(self):
        case = _tasks()
        case[1]["steps"][0]["duration_ns"] = 0
        result = evaluate_task_set(case, ENTRIES)
        self.assertNotIn(FINDING_ADVANCES_TIME, _codes(result))
        self.assertTrue(result["schedulable"])

    def test_a_non_integer_duration_raises(self):
        case = _tasks()
        case[1]["steps"][0]["duration_ns"] = 1.0
        with self.assertRaises(ValueError):
            evaluate_task_set(case, ENTRIES)

    def test_a_blocking_step_is_a_finding(self):
        case = _tasks()
        case[1]["steps"][0]["blocking"] = True
        result = evaluate_task_set(case, ENTRIES)
        self.assertIn(FINDING_BLOCKING, _codes(result))

    def test_a_schedule_entry_naming_an_undeclared_task_is_a_finding(self):
        result = evaluate_task_set(TASKS, [{"name": "tick", "task": "teardown"}])
        self.assertIn(FINDING_ENTRY_UNRESOLVED, _codes(result))

    def test_a_task_no_entry_reaches_is_reported_without_blocking(self):
        case = _tasks({"name": "teardown", "steps": [{"kind": "activity", "name": "close"}]})
        result = evaluate_task_set(case, ENTRIES)
        self.assertEqual(result["unreachable_tasks"], ["teardown"])
        self.assertTrue(result["schedulable"])

    def test_a_task_reached_only_through_another_task_is_not_unreachable(self):
        result = evaluate_task_set(TASKS, ENTRIES)
        self.assertEqual(result["unreachable_tasks"], [])
        self.assertEqual(result["triggered_tasks"], ["sample-housekeeping"])

    def test_a_non_list_entry_set_raises(self):
        with self.assertRaises(ValueError):
            evaluate_task_set(TASKS, ENTRIES[0])


if __name__ == "__main__":
    unittest.main()

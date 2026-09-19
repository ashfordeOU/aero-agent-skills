#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-design-verification-tasks.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_design_verification_tasks.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_design_verification_tasks_logic import (  # noqa: E402
    CHECKING,
    COMPLETE,
    ENGINEERING,
    IN_PROGRESS,
    TASK_KINDS,
    evaluate_task_set,
    meets_coverage_threshold,
    normalize_status,
    normalize_task_kind,
    order_tasks,
    produced_items,
    unexamined_items,
    validate_tasks,
    verification_coverage,
)


def base_phase():
    return {
        "tasks": [
            {
                "id": "D-1",
                "kind": "design",
                "produces": "architecture-description",
                "evidence": "architecture note issue 2",
                "status": "complete",
            },
            {
                "id": "D-2",
                "kind": "design",
                "produces": "behavioural-model",
                "prerequisites": ["D-1"],
                "evidence": "model release 1.1",
                "status": "complete",
            },
            {
                "id": "V-1",
                "kind": "verification",
                "examines": ["architecture-description"],
                "prerequisites": ["D-1"],
                "evidence": "review minutes",
                "status": "complete",
            },
            {
                "id": "V-2",
                "kind": "verification",
                "examines": ["behavioural-model"],
                "prerequisites": ["D-2"],
                "status": "in progress",
            },
        ],
        "coverage_threshold": 1.0,
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestKindAndStatusFolding(unittest.TestCase):
    def test_design_folds_to_engineering(self):
        self.assertEqual(normalize_task_kind("Design"), ENGINEERING)

    def test_verification_folds_to_checking(self):
        self.assertEqual(normalize_task_kind("Verification Task"), CHECKING)

    def test_underscored_kind_folds(self):
        self.assertEqual(normalize_task_kind("design_task"), ENGINEERING)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_task_kind("procurement")

    def test_blank_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_task_kind("   ")

    def test_two_kinds_are_the_whole_set(self):
        self.assertEqual(len(TASK_KINDS), 2)

    def test_done_folds_to_complete(self):
        self.assertEqual(normalize_status("Done"), COMPLETE)

    def test_in_progress_spellings_fold(self):
        self.assertEqual(normalize_status("In Progress"), IN_PROGRESS)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            normalize_status("waiting on parts")


class TestTaskValidation(unittest.TestCase):
    def test_tasks_resolve_in_declared_order(self):
        tasks = validate_tasks(base_phase()["tasks"])
        self.assertEqual([t["id"] for t in tasks], ["D-1", "D-2", "V-1", "V-2"])

    def test_duplicate_task_id_rejected(self):
        entries = base_phase()["tasks"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_tasks(entries)

    def test_unknown_task_key_rejected(self):
        entries = base_phase()["tasks"]
        entries[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_tasks(entries)

    def test_task_missing_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_tasks([{"id": "D-1"}])

    def test_a_task_that_produces_and_examines_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tasks(
                [
                    {
                        "id": "X-1",
                        "kind": "design",
                        "produces": "netlist",
                        "examines": ["netlist"],
                    }
                ]
            )

    def test_non_list_examines_rejected(self):
        with self.assertRaises(ValueError):
            validate_tasks(
                [{"id": "V-1", "kind": "verification", "examines": "netlist"}]
            )

    def test_repeated_examined_item_counts_once(self):
        tasks = validate_tasks(
            [{"id": "V-1", "kind": "verification", "examines": ["a", "a"]}]
        )
        self.assertEqual(tasks[0]["examines"], ["a"])


class TestPrerequisiteOrdering(unittest.TestCase):
    def test_order_respects_prerequisites(self):
        order = order_tasks(validate_tasks(base_phase()["tasks"]))
        self.assertLess(order.index("D-1"), order.index("V-1"))
        self.assertLess(order.index("D-2"), order.index("V-2"))

    def test_every_task_appears_once_in_the_order(self):
        order = order_tasks(validate_tasks(base_phase()["tasks"]))
        self.assertEqual(sorted(order), ["D-1", "D-2", "V-1", "V-2"])

    def test_prerequisite_cycle_rejected(self):
        tasks = validate_tasks(
            [
                {"id": "A", "kind": "design", "produces": "a", "prerequisites": ["B"]},
                {"id": "B", "kind": "design", "produces": "b", "prerequisites": ["A"]},
            ]
        )
        with self.assertRaises(ValueError):
            order_tasks(tasks)

    def test_self_prerequisite_rejected(self):
        tasks = validate_tasks(
            [{"id": "A", "kind": "design", "produces": "a", "prerequisites": ["A"]}]
        )
        with self.assertRaises(ValueError):
            order_tasks(tasks)

    def test_unknown_prerequisite_rejected(self):
        tasks = validate_tasks(
            [{"id": "A", "kind": "design", "produces": "a", "prerequisites": ["Z"]}]
        )
        with self.assertRaises(ValueError):
            order_tasks(tasks)


class TestCoverageArithmetic(unittest.TestCase):
    def setUp(self):
        self.tasks = validate_tasks(base_phase()["tasks"])

    def test_produced_items_are_the_engineering_outputs(self):
        self.assertEqual(
            produced_items(self.tasks),
            ["architecture-description", "behavioural-model"],
        )

    def test_every_produced_item_is_examined(self):
        self.assertAlmostEqual(verification_coverage(self.tasks), 1.0, places=12)
        self.assertEqual(unexamined_items(self.tasks), [])

    def test_an_unexamined_item_lowers_coverage(self):
        entries = base_phase()["tasks"]
        entries.append({"id": "D-3", "kind": "design", "produces": "timing-budget"})
        tasks = validate_tasks(entries)
        self.assertAlmostEqual(verification_coverage(tasks), 2 / 3, places=12)
        self.assertEqual(unexamined_items(tasks), ["timing-budget"])

    def test_coverage_needs_a_produced_item(self):
        tasks = validate_tasks(
            [{"id": "V-1", "kind": "verification", "examines": ["a"]}]
        )
        with self.assertRaises(ValueError):
            verification_coverage(tasks)

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_coverage_threshold(3 / 4, 0.75))

    def test_a_third_landing_meets_a_third_threshold(self):
        self.assertTrue(meets_coverage_threshold(1 / 3, 1 / 3))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_coverage_threshold(0.74, 0.75))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_coverage_threshold(0.5, 1.5)


class TestEvaluateTaskSet(unittest.TestCase):
    def test_a_coherent_task_set_is_acceptable(self):
        result = evaluate_task_set(base_phase())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_coverage_and_order_reach_the_result(self):
        result = evaluate_task_set(base_phase())
        self.assertAlmostEqual(result["verification_coverage"], 1.0, places=12)
        self.assertEqual(result["task_count"], 4)
        self.assertLess(result["order"].index("D-2"), result["order"].index("V-2"))

    def test_a_threshold_met_exactly_does_not_fail_the_phase(self):
        phase = base_phase()
        phase["tasks"].append(
            {"id": "D-3", "kind": "design", "produces": "timing-budget"}
        )
        phase["tasks"].append(
            {"id": "V-3", "kind": "verification", "examines": ["timing-budget"]}
        )
        phase["coverage_threshold"] = 3 / 3
        result = evaluate_task_set(phase)
        self.assertNotIn("verification-coverage-below-threshold", codes(result))

    def test_an_unexamined_design_item_is_reported(self):
        phase = base_phase()
        phase["tasks"].append(
            {"id": "D-3", "kind": "design", "produces": "timing-budget"}
        )
        result = evaluate_task_set(phase)
        self.assertIn("design-item-not-examined", codes(result))
        self.assertEqual(result["unexamined_items"], ["timing-budget"])

    def test_coverage_below_the_threshold_is_reported(self):
        phase = base_phase()
        phase["tasks"].append(
            {"id": "D-3", "kind": "design", "produces": "timing-budget"}
        )
        result = evaluate_task_set(phase)
        self.assertIn("verification-coverage-below-threshold", codes(result))

    def test_a_checking_task_aimed_at_nothing_produced_is_reported(self):
        phase = base_phase()
        phase["tasks"][3]["examines"] = ["behavioral-model"]
        result = evaluate_task_set(phase)
        self.assertIn("checking-target-not-produced", codes(result))

    def test_an_engineering_task_with_no_design_item_is_reported(self):
        phase = base_phase()
        phase["tasks"][0]["produces"] = ""
        result = evaluate_task_set(phase)
        self.assertIn("engineering-task-without-design-item", codes(result))

    def test_a_checking_task_with_no_target_is_reported(self):
        phase = base_phase()
        phase["tasks"][2]["examines"] = []
        result = evaluate_task_set(phase)
        self.assertIn("checking-task-without-target", codes(result))

    def test_a_complete_task_without_evidence_is_reported(self):
        phase = base_phase()
        phase["tasks"][0]["evidence"] = ""
        result = evaluate_task_set(phase)
        self.assertIn("complete-task-without-evidence", codes(result))

    def test_completion_ahead_of_a_prerequisite_is_reported(self):
        phase = base_phase()
        phase["tasks"][0]["status"] = "in progress"
        result = evaluate_task_set(phase)
        self.assertIn("complete-ahead-of-prerequisite", codes(result))

    def test_unknown_phase_key_rejected(self):
        phase = base_phase()
        phase["budget"] = 1
        with self.assertRaises(ValueError):
            evaluate_task_set(phase)

    def test_missing_tasks_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_task_set({"coverage_threshold": 1.0})

    def test_empty_task_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_task_set({"tasks": []})

    def test_non_mapping_phase_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_task_set([("tasks", [])])


if __name__ == "__main__":
    unittest.main()

"""Contract tests for the clause 7.1.2 hybrid design activity-flow logic."""

import unittest

from q6005_hybrid_design_activity_flow_logic import (
    ACTIVITY_STATES,
    CANONICAL_STAGES,
    assess_design_flow,
    build_flow,
    completion_ratio,
    critical_path,
    earliest_finish_days,
    missing_stages,
    out_of_order_signoffs,
    ready_activities,
    topological_order,
    validate_activity,
)


def _activity(ident, stage, days, preds=(), status="not-started"):
    return {
        "id": ident,
        "stage": stage,
        "duration_days": days,
        "predecessors": list(preds),
        "status": status,
    }


def _full_flow(status="not-started"):
    return [
        _activity("A1", "design-input-review", 5.0, (), status),
        _activity("A2", "preliminary-design", 10.0, ("A1",), status),
        _activity("A3", "materials-and-parts-selection", 8.0, ("A1",), status),
        _activity("A4", "detailed-design", 15.0, ("A2", "A3"), status),
        _activity("A5", "design-analysis", 7.0, ("A4",), status),
        _activity("A6", "design-verification", 6.0, ("A5",), status),
        _activity("A7", "design-review-and-approval", 3.0, ("A6",), status),
    ]


class ValidateActivityTests(unittest.TestCase):
    def test_valid_activity_is_normalized(self):
        record = validate_activity(_activity("A1", "Design-Input-Review", 5, (), "Complete"))
        self.assertEqual(record["stage"], "design-input-review")
        self.assertEqual(record["status"], "complete")
        self.assertEqual(record["predecessors"], ())

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "A1", "stage": "preliminary-design", "duration_days": 2.0})

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("A1", "marketing-review", 5.0))

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("A1", "preliminary-design", 5.0, (), "nearly"))

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("A1", "preliminary-design", -1.0))

    def test_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("A1", "preliminary-design", True))

    def test_self_dependency_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("A1", "preliminary-design", 5.0, ("A1",)))

    def test_repeated_predecessor_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("A2", "preliminary-design", 5.0, ("A1", "A1")))

    def test_empty_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(_activity("  ", "preliminary-design", 5.0))


class BuildFlowTests(unittest.TestCase):
    def test_flow_keyed_by_id(self):
        flow = build_flow(_full_flow())
        self.assertEqual(sorted(flow), ["A1", "A2", "A3", "A4", "A5", "A6", "A7"])

    def test_duplicate_id_rejected(self):
        acts = _full_flow()
        acts.append(_activity("A1", "design-analysis", 2.0))
        with self.assertRaises(ValueError):
            build_flow(acts)

    def test_dangling_predecessor_rejected(self):
        acts = [_activity("A2", "preliminary-design", 5.0, ("A0",))]
        with self.assertRaises(ValueError):
            build_flow(acts)

    def test_empty_flow_rejected(self):
        with self.assertRaises(ValueError):
            build_flow([])


class OrderingTests(unittest.TestCase):
    def test_predecessors_come_first(self):
        order = topological_order(_full_flow())
        self.assertLess(order.index("A1"), order.index("A2"))
        self.assertLess(order.index("A4"), order.index("A5"))
        self.assertEqual(order[-1], "A7")

    def test_order_is_deterministic_for_parallel_tasks(self):
        order = topological_order(_full_flow())
        self.assertLess(order.index("A2"), order.index("A3"))

    def test_cycle_rejected(self):
        acts = [
            _activity("A1", "preliminary-design", 5.0, ("A2",)),
            _activity("A2", "detailed-design", 5.0, ("A1",)),
        ]
        with self.assertRaises(ValueError):
            topological_order(acts)


class StageCoverageTests(unittest.TestCase):
    def test_full_flow_covers_every_stage(self):
        self.assertEqual(missing_stages(_full_flow()), ())

    def test_omitted_stage_is_named(self):
        acts = [a for a in _full_flow() if a["stage"] != "design-verification"]
        acts[-1]["predecessors"] = ["A5"]
        self.assertEqual(missing_stages(acts), ("design-verification",))

    def test_gaps_follow_the_canonical_order(self):
        acts = [_activity("A1", "detailed-design", 5.0)]
        gaps = missing_stages(acts)
        self.assertEqual(gaps, tuple(s for s in CANONICAL_STAGES if s != "detailed-design"))


class ProgressTests(unittest.TestCase):
    def test_only_the_entry_task_is_ready_at_kickoff(self):
        self.assertEqual(ready_activities(_full_flow()), ["A1"])

    def test_two_parallel_tasks_become_ready_together(self):
        acts = _full_flow()
        acts[0]["status"] = "complete"
        self.assertEqual(ready_activities(acts), ["A2", "A3"])

    def test_completed_task_is_not_ready(self):
        acts = _full_flow("complete")
        self.assertEqual(ready_activities(acts), [])

    def test_clean_flow_has_no_out_of_order_signoff(self):
        acts = _full_flow()
        acts[0]["status"] = "complete"
        self.assertEqual(out_of_order_signoffs(acts), [])

    def test_signoff_ahead_of_predecessor_is_exposed(self):
        acts = _full_flow()
        acts[3]["status"] = "complete"
        self.assertIn(("A4", "A2"), out_of_order_signoffs(acts))
        self.assertIn(("A4", "A3"), out_of_order_signoffs(acts))

    def test_completion_ratio_counts_completed_tasks(self):
        acts = _full_flow()
        acts[0]["status"] = "complete"
        self.assertAlmostEqual(completion_ratio(acts), 1.0 / 7.0, places=9)

    def test_completion_ratio_is_one_when_all_complete(self):
        self.assertAlmostEqual(completion_ratio(_full_flow("complete")), 1.0, places=9)


class ScheduleTests(unittest.TestCase):
    def test_earliest_finish_follows_the_longest_input(self):
        finish = earliest_finish_days(_full_flow())
        self.assertAlmostEqual(finish["A1"], 5.0, places=9)
        self.assertAlmostEqual(finish["A3"], 13.0, places=9)
        self.assertAlmostEqual(finish["A4"], 30.0, places=9)

    def test_total_duration_is_the_approval_finish(self):
        path, total = critical_path(_full_flow())
        self.assertAlmostEqual(total, 46.0, places=9)
        self.assertEqual(path[-1], "A7")

    def test_critical_path_runs_through_the_longer_parallel_branch(self):
        path, _ = critical_path(_full_flow())
        self.assertIn("A2", path)
        self.assertNotIn("A3", path)

    def test_zero_duration_task_is_allowed(self):
        acts = _full_flow()
        acts[6]["duration_days"] = 0.0
        _, total = critical_path(acts)
        self.assertAlmostEqual(total, 43.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_finished_flow_is_approved(self):
        result = assess_design_flow({"activities": _full_flow("complete")})
        self.assertTrue(result["design_solution_approved"])
        self.assertEqual(result["findings"], [])

    def test_open_activity_blocks_approval(self):
        result = assess_design_flow({"activities": _full_flow()})
        self.assertFalse(result["design_solution_approved"])
        self.assertEqual(len(result["open_activities"]), 7)

    def test_missing_stage_is_a_finding(self):
        acts = [a for a in _full_flow("complete") if a["stage"] != "design-analysis"]
        acts[-2]["predecessors"] = ["A4"]
        result = assess_design_flow({"activities": acts})
        self.assertIn("design-analysis", result["missing_stages"])
        self.assertFalse(result["design_solution_approved"])

    def test_flow_without_a_terminal_approval_is_a_finding(self):
        acts = _full_flow("complete")
        acts.append(_activity("A8", "detailed-design", 2.0, ("A7",), "complete"))
        result = assess_design_flow({"activities": acts})
        self.assertFalse(result["design_solution_approved"])
        self.assertTrue(any("cannot be approved" in f for f in result["findings"]))

    def test_out_of_order_signoff_is_a_finding(self):
        acts = _full_flow("complete")
        acts[1]["status"] = "in-progress"
        result = assess_design_flow({"activities": acts})
        self.assertTrue(any("ahead of an open predecessor" in f for f in result["findings"]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_flow(["activities"])

    def test_missing_activities_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_design_flow({"tasks": _full_flow()})

    def test_state_vocabulary_is_closed(self):
        self.assertEqual(ACTIVITY_STATES, ("not-started", "in-progress", "complete"))


if __name__ == "__main__":
    unittest.main()

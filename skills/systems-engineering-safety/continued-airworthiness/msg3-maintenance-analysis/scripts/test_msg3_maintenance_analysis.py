"""Contract test for the MSG-3 scheduled maintenance decision logic.

Deterministic, offline, stdlib only. Run with:
    python3 scripts/test_msg3_maintenance_analysis.py
"""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.dirname(os.path.abspath(__file__)),
)
from msg3_maintenance_analysis_logic import (
    HIDDEN_EXPOSURE_FACTOR,
    TASK_CATEGORIES,
    classify_failure,
    interval_verdict,
    run_msg3_analysis,
    select_tasks,
)

F1 = {
    "failure_id": "F1",
    "function": "hydraulic pressure",
    "failure_effect": "pressure loss",
    "evident": False,
    "safety_significant": False,
    "hidden_safety": True,
    "maintenance_opportunity_interval": 3000.0,
    "single_failure_interval": 4000.0,
}
F2 = {
    "failure_id": "F2",
    "function": "cabin lighting",
    "failure_effect": "light loss",
    "evident": True,
    "safety_significant": False,
    "hidden_safety": False,
    "maintenance_opportunity_interval": 6000.0,
    "single_failure_interval": 0.0,
}
F3 = {
    "failure_id": "F3",
    "function": "thrust reverser unlock",
    "failure_effect": "uncommanded reverser deployment",
    "evident": True,
    "safety_significant": True,
    "hidden_safety": False,
    "maintenance_opportunity_interval": 4000.0,
    "single_failure_interval": 0.0,
}


def base_record(**overrides):
    record = dict(F1)
    record.update(overrides)
    return record


class TestClassificationAnchors(unittest.TestCase):
    def test_f1_is_5_hidden_safety(self):
        self.assertEqual(classify_failure(F1)["category"], "5-hidden-safety")

    def test_f1_rationale_mentions_combination(self):
        rationale = classify_failure(F1)["rationale"]
        self.assertIn("combination", rationale)
        self.assertIn("second failure", rationale)

    def test_f2_is_8_evident_economic(self):
        self.assertEqual(classify_failure(F2)["category"], "8-evident-economic")

    def test_f3_is_7_evident_safety(self):
        self.assertEqual(classify_failure(F3)["category"], "7-evident-safety")

    def test_hidden_economic_branch_is_6(self):
        record = base_record(hidden_safety=False)
        self.assertEqual(classify_failure(record)["category"], "6-hidden-economic")

    def test_hidden_direct_safety_maps_to_5(self):
        record = base_record(safety_significant=True, hidden_safety=False)
        self.assertEqual(classify_failure(record)["category"], "5-hidden-safety")

    def test_evident_safety_branch_is_7(self):
        record = base_record(
            evident=True, safety_significant=True, hidden_safety=False
        )
        self.assertEqual(classify_failure(record)["category"], "7-evident-safety")

    def test_evident_economic_branch_is_8(self):
        record = base_record(
            evident=True, safety_significant=False, hidden_safety=False
        )
        self.assertEqual(classify_failure(record)["category"], "8-evident-economic")

    def test_evident_ignores_hidden_flag_for_category(self):
        record = base_record(
            evident=True, safety_significant=False, hidden_safety=True
        )
        self.assertEqual(classify_failure(record)["category"], "8-evident-economic")

    def test_classify_output_keys(self):
        output = classify_failure(F1)
        self.assertEqual(
            set(output.keys()),
            {
                "failure_id",
                "category",
                "evident",
                "safety_significant",
                "hidden_safety",
                "rationale",
            },
        )

    def test_classify_rationale_non_empty_for_all_branches(self):
        records = [
            F1,
            base_record(hidden_safety=False),
            F3,
            base_record(
                evident=True, safety_significant=False, hidden_safety=False
            ),
        ]
        for record in records:
            self.assertTrue(classify_failure(record)["rationale"])


class TestTaskSelection(unittest.TestCase):
    def test_f1_tasks_contain_fc_and_in(self):
        tasks = select_tasks(classify_failure(F1))["task_categories"]
        self.assertIn("FC", tasks)
        self.assertIn("IN", tasks)

    def test_f1_tasks_never_lubrication_only(self):
        tasks = select_tasks(classify_failure(F1))["task_categories"]
        self.assertNotEqual(tasks, ["LU"])
        self.assertIn("VC", tasks)

    def test_f1_rationale_warns_lubrication_alone_insufficient(self):
        rationale = select_tasks(classify_failure(F1))["rationale"]
        self.assertIn("lubrication or servicing task alone is never sufficient", rationale)

    def test_f3_tasks_contain_restoration_or_discard(self):
        tasks = select_tasks(classify_failure(F3))["task_categories"]
        self.assertTrue(("RS" in tasks) or ("DS" in tasks))

    def test_f3_tasks_preventive_set(self):
        self.assertEqual(
            select_tasks(classify_failure(F3))["task_categories"],
            ["IN", "FC", "RS", "DS"],
        )

    def test_f2_tasks_economic_set(self):
        self.assertEqual(
            select_tasks(classify_failure(F2))["task_categories"],
            ["VC", "IN", "FC", "RS", "DS"],
        )

    def test_6_with_hidden_function_uses_fc_in(self):
        cls = classify_failure(base_record(hidden_safety=False))
        self.assertEqual(
            select_tasks(cls, applicable_hidden=True)["task_categories"],
            ["FC", "IN"],
        )

    def test_6_without_hidden_function_uses_vc(self):
        cls = classify_failure(base_record(hidden_safety=False))
        self.assertEqual(
            select_tasks(cls, applicable_hidden=False)["task_categories"],
            ["VC"],
        )

    def test_selection_rationale_non_empty(self):
        for cls in (
            classify_failure(F1),
            classify_failure(F2),
            classify_failure(F3),
            classify_failure(base_record(hidden_safety=False)),
        ):
            self.assertTrue(select_tasks(cls)["rationale"])

    def test_selection_output_keys(self):
        output = select_tasks(classify_failure(F1))
        self.assertEqual(
            set(output.keys()),
            {"failure_id", "category", "task_categories", "rationale"},
        )

    def test_all_task_categories_are_known_codes(self):
        tasks = select_tasks(classify_failure(F1))["task_categories"]
        self.assertTrue(all(t in TASK_CATEGORIES for t in tasks))

    def test_hidden_5_tasks_ordered_highest_value_first(self):
        tasks = select_tasks(classify_failure(F1))["task_categories"]
        self.assertEqual(tasks, ["FC", "IN", "VC"])


class TestIntervalVerdict(unittest.TestCase):
    def test_f1_interval_too_long_with_2000_fh_limit(self):
        cls = classify_failure(F1)
        tasks = select_tasks(cls)
        verdict = interval_verdict(F1, cls, tasks["task_categories"])
        self.assertEqual(verdict["exposure_limit"], 2000.0)
        self.assertEqual(verdict["verdict"], "interval-too-long")
        self.assertEqual(verdict["recommended_interval"], 2000.0)

    def test_exposure_limit_is_half_factor_times_single(self):
        self.assertEqual(HIDDEN_EXPOSURE_FACTOR, 0.5)
        self.assertEqual(0.5 * F1["single_failure_interval"], 2000.0)

    def test_hidden_short_opportunity_is_interval_ok(self):
        record = base_record(
            failure_id="H2",
            maintenance_opportunity_interval=1000.0,
            single_failure_interval=4000.0,
        )
        cls = classify_failure(record)
        tasks = select_tasks(cls)
        verdict = interval_verdict(record, cls, tasks["task_categories"])
        self.assertEqual(verdict["verdict"], "interval-ok")
        self.assertEqual(verdict["exposure_limit"], 2000.0)

    def test_hidden_opportunity_equal_to_limit_is_ok(self):
        record = base_record(
            failure_id="H3",
            maintenance_opportunity_interval=2000.0,
            single_failure_interval=4000.0,
        )
        cls = classify_failure(record)
        verdict = interval_verdict(
            record, cls, select_tasks(cls)["task_categories"]
        )
        self.assertEqual(verdict["verdict"], "interval-ok")

    def test_f2_evident_without_task_interval_not_scoped(self):
        cls = classify_failure(F2)
        verdict = interval_verdict(
            F2, cls, select_tasks(cls)["task_categories"]
        )
        self.assertEqual(verdict["verdict"], "interval-not-scoped")

    def test_f3_evident_safety_without_task_interval_not_scoped(self):
        cls = classify_failure(F3)
        verdict = interval_verdict(
            F3, cls, select_tasks(cls)["task_categories"]
        )
        self.assertEqual(verdict["verdict"], "interval-not-scoped")

    def test_evident_with_task_interval_ok_when_within_limit(self):
        record = dict(F2)
        record["task_interval"] = 8000.0
        cls = classify_failure(record)
        verdict = interval_verdict(
            record, cls, select_tasks(cls)["task_categories"]
        )
        self.assertEqual(verdict["verdict"], "interval-ok")
        self.assertIsNone(verdict["recommended_interval"])

    def test_evident_with_task_interval_too_long_when_exceeded(self):
        record = dict(F3)
        record["task_interval"] = 2500.0
        cls = classify_failure(record)
        verdict = interval_verdict(
            record, cls, select_tasks(cls)["task_categories"]
        )
        self.assertEqual(verdict["verdict"], "interval-too-long")
        self.assertEqual(verdict["recommended_interval"], 2500.0)

    def test_hidden_without_detection_task_not_scoped(self):
        record = base_record(
            failure_id="H4",
            maintenance_opportunity_interval=1000.0,
            single_failure_interval=4000.0,
        )
        cls = classify_failure(record)
        verdict = interval_verdict(record, cls, ["LU", "SV"])
        self.assertEqual(verdict["verdict"], "interval-not-scoped")

    def test_verdict_output_keys(self):
        cls = classify_failure(F1)
        verdict = interval_verdict(
            F1, cls, select_tasks(cls)["task_categories"]
        )
        self.assertEqual(
            set(verdict.keys()),
            {
                "failure_id",
                "exposure_limit",
                "opportunity_interval",
                "verdict",
                "recommended_interval",
            },
        )


class TestValueErrors(unittest.TestCase):
    def test_missing_required_key_raises(self):
        record = dict(F1)
        del record["function"]
        with self.assertRaises(ValueError):
            classify_failure(record)

    def test_missing_failure_effect_raises_in_verdict(self):
        record = dict(F1)
        del record["failure_effect"]
        cls = classify_failure(F1)
        with self.assertRaises(ValueError):
            interval_verdict(record, cls, ["FC"])

    def test_negative_single_failure_interval_raises(self):
        record = base_record(
            single_failure_interval=-1.0, hidden_safety=False
        )
        with self.assertRaises(ValueError):
            classify_failure(record)

    def test_nonpositive_opportunity_on_hidden_raises(self):
        record = base_record(maintenance_opportunity_interval=0.0)
        with self.assertRaises(ValueError):
            classify_failure(record)

    def test_negative_task_interval_raises(self):
        record = dict(F3)
        record["task_interval"] = -500.0
        with self.assertRaises(ValueError):
            interval_verdict(record, classify_failure(record), ["IN"])


class TestRunAnalysis(unittest.TestCase):
    def test_summary_counts_worked_example(self):
        out = run_msg3_analysis([F1, F2, F3])
        summary = out["summary"]
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["hidden_count"], 1)
        self.assertEqual(summary["safety_significant_count"], 1)
        self.assertEqual(summary["interval_too_long_count"], 1)

    def test_results_order_and_categories(self):
        out = run_msg3_analysis([F1, F2, F3])
        self.assertEqual(
            [r["category"] for r in out["results"]],
            ["5-hidden-safety", "8-evident-economic", "7-evident-safety"],
        )

    def test_result_fields_present(self):
        out = run_msg3_analysis([F1, F2, F3])
        for result in out["results"]:
            self.assertIn("failure_id", result)
            self.assertIn("category", result)
            self.assertIn("task_categories", result)
            self.assertIn("verdict", result)
            self.assertIn("recommended_interval", result)

    def test_empty_record_list(self):
        out = run_msg3_analysis([])
        self.assertEqual(out["results"], [])
        self.assertEqual(out["summary"]["total"], 0)


if __name__ == "__main__":
    unittest.main()

"""
Offline deterministic contract tests for e1011_hcd_activities_logic.py.
Run: python3 test_e1011_hcd_activities.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from e1011_hcd_activities_logic import (
    HCDError,
    check_design_coverage,
    check_hcd_activity_completeness,
    evaluate_design_element,
    summarise_hcd_assessment,
    validate_design_element,
    validate_task_entry,
    validate_user_requirement,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task(task_id="T-01", description="Operate hatch", performer="Commander",
          criticality="high", steps=["Open hatch", "Verify seal"]):
    return {
        "task_id": task_id,
        "description": description,
        "performer": performer,
        "criticality": criticality,
        "steps": steps,
    }


def _req(req_id="R-01", source="user", category="safety",
         statement="Hatch shall open within 10 s", priority=1):
    return {
        "req_id": req_id,
        "source": source,
        "category": category,
        "statement": statement,
        "priority": priority,
    }


def _elem(element_id="D-01", description="Quick-release latch",
          addresses=None, rationale="Meets 10 s hatch requirement"):
    return {
        "element_id": element_id,
        "description": description,
        "addresses": addresses if addresses is not None else ["R-01"],
        "rationale": rationale,
    }


def _criterion(criterion_id="C-01", outcome="pass"):
    return {"criterion_id": criterion_id, "outcome": outcome}


# ---------------------------------------------------------------------------
# Task analysis validation
# ---------------------------------------------------------------------------

class TestValidateTaskEntry(unittest.TestCase):

    def test_valid_task_returns_unchanged(self):
        t = _task()
        result = validate_task_entry(t)
        self.assertIs(result, t)

    def test_missing_field_raises(self):
        t = _task()
        del t["performer"]
        with self.assertRaises(HCDError) as ctx:
            validate_task_entry(t)
        self.assertIn("performer", str(ctx.exception))

    def test_invalid_criticality_raises(self):
        t = _task(criticality="extreme")
        with self.assertRaises(HCDError) as ctx:
            validate_task_entry(t)
        self.assertIn("criticality", str(ctx.exception))

    def test_empty_steps_list_raises(self):
        t = _task(steps=[])
        with self.assertRaises(HCDError):
            validate_task_entry(t)

    def test_steps_not_list_raises(self):
        t = _task(steps="open hatch")
        with self.assertRaises(HCDError):
            validate_task_entry(t)

    def test_blank_task_id_raises(self):
        t = _task(task_id="   ")
        with self.assertRaises(HCDError):
            validate_task_entry(t)

    def test_all_criticality_levels_accepted(self):
        for level in ("low", "medium", "high", "critical"):
            result = validate_task_entry(_task(criticality=level))
            self.assertEqual(result["criticality"], level)


# ---------------------------------------------------------------------------
# User/organisational requirement validation
# ---------------------------------------------------------------------------

class TestValidateUserRequirement(unittest.TestCase):

    def test_valid_user_requirement(self):
        r = _req()
        result = validate_user_requirement(r)
        self.assertIs(result, r)

    def test_valid_organisational_requirement(self):
        r = _req(source="organisational", category="organisational")
        result = validate_user_requirement(r)
        self.assertEqual(result["source"], "organisational")

    def test_missing_priority_raises(self):
        r = _req()
        del r["priority"]
        with self.assertRaises(HCDError) as ctx:
            validate_user_requirement(r)
        self.assertIn("priority", str(ctx.exception))

    def test_priority_zero_raises(self):
        r = _req(priority=0)
        with self.assertRaises(HCDError):
            validate_user_requirement(r)

    def test_priority_six_raises(self):
        r = _req(priority=6)
        with self.assertRaises(HCDError):
            validate_user_requirement(r)

    def test_invalid_source_raises(self):
        r = _req(source="contractor")
        with self.assertRaises(HCDError) as ctx:
            validate_user_requirement(r)
        self.assertIn("source", str(ctx.exception))

    def test_invalid_category_raises(self):
        r = _req(category="aesthetic")
        with self.assertRaises(HCDError) as ctx:
            validate_user_requirement(r)
        self.assertIn("category", str(ctx.exception))

    def test_all_priority_values_accepted(self):
        for p in (1, 2, 3, 4, 5):
            result = validate_user_requirement(_req(priority=p))
            self.assertEqual(result["priority"], p)


# ---------------------------------------------------------------------------
# Design element validation
# ---------------------------------------------------------------------------

class TestValidateDesignElement(unittest.TestCase):

    def test_valid_element_returned(self):
        e = _elem()
        result = validate_design_element(e)
        self.assertIs(result, e)

    def test_empty_addresses_list_accepted(self):
        e = _elem(addresses=[])
        result = validate_design_element(e)
        self.assertEqual(result["addresses"], [])

    def test_missing_rationale_raises(self):
        e = _elem()
        del e["rationale"]
        with self.assertRaises(HCDError) as ctx:
            validate_design_element(e)
        self.assertIn("rationale", str(ctx.exception))

    def test_addresses_not_list_raises(self):
        e = _elem(addresses="R-01")
        with self.assertRaises(HCDError):
            validate_design_element(e)


# ---------------------------------------------------------------------------
# Design coverage check
# ---------------------------------------------------------------------------

class TestCheckDesignCoverage(unittest.TestCase):

    def test_full_coverage(self):
        reqs = [_req("R-01"), _req("R-02")]
        elems = [_elem(addresses=["R-01", "R-02"])]
        result = check_design_coverage(reqs, elems)
        self.assertEqual(sorted(result["covered"]), ["R-01", "R-02"])
        self.assertEqual(result["uncovered"], [])
        self.assertAlmostEqual(result["coverage_ratio"], 1.0)

    def test_partial_coverage(self):
        reqs = [_req("R-01"), _req("R-02")]
        elems = [_elem(addresses=["R-01"])]
        result = check_design_coverage(reqs, elems)
        self.assertIn("R-01", result["covered"])
        self.assertIn("R-02", result["uncovered"])
        self.assertAlmostEqual(result["coverage_ratio"], 0.5)

    def test_no_requirements_yields_zero_ratio(self):
        result = check_design_coverage([], [])
        self.assertAlmostEqual(result["coverage_ratio"], 0.0)
        self.assertEqual(result["covered"], [])
        self.assertEqual(result["uncovered"], [])

    def test_no_elements_all_uncovered(self):
        reqs = [_req("R-01"), _req("R-02")]
        result = check_design_coverage(reqs, [])
        self.assertEqual(sorted(result["uncovered"]), ["R-01", "R-02"])
        self.assertAlmostEqual(result["coverage_ratio"], 0.0)


# ---------------------------------------------------------------------------
# Design evaluation
# ---------------------------------------------------------------------------

class TestEvaluateDesignElement(unittest.TestCase):

    def test_all_pass_yields_pass(self):
        e = _elem()
        result = evaluate_design_element(e, [_criterion("C-01", "pass"), _criterion("C-02", "pass")])
        self.assertEqual(result["overall_outcome"], "pass")
        self.assertEqual(result["fail_count"], 0)
        self.assertEqual(result["conditional_count"], 0)

    def test_one_fail_yields_fail(self):
        e = _elem()
        result = evaluate_design_element(e, [_criterion("C-01", "pass"), _criterion("C-02", "fail")])
        self.assertEqual(result["overall_outcome"], "fail")
        self.assertEqual(result["fail_count"], 1)

    def test_conditional_no_fail_yields_conditional(self):
        e = _elem()
        result = evaluate_design_element(e, [_criterion("C-01", "pass"), _criterion("C-02", "conditional")])
        self.assertEqual(result["overall_outcome"], "conditional")
        self.assertEqual(result["conditional_count"], 1)
        self.assertEqual(result["fail_count"], 0)

    def test_fail_overrides_conditional(self):
        e = _elem()
        result = evaluate_design_element(
            e,
            [_criterion("C-01", "conditional"), _criterion("C-02", "fail")],
        )
        self.assertEqual(result["overall_outcome"], "fail")

    def test_empty_criteria_raises(self):
        e = _elem()
        with self.assertRaises(HCDError):
            evaluate_design_element(e, [])

    def test_invalid_outcome_raises(self):
        e = _elem()
        with self.assertRaises(HCDError) as ctx:
            evaluate_design_element(e, [_criterion("C-01", "unknown")])
        self.assertIn("outcome", str(ctx.exception))

    def test_element_id_preserved_in_result(self):
        e = _elem(element_id="D-99")
        result = evaluate_design_element(e, [_criterion()])
        self.assertEqual(result["element_id"], "D-99")


# ---------------------------------------------------------------------------
# HCD activity completeness check
# ---------------------------------------------------------------------------

class TestCheckHCDActivityCompleteness(unittest.TestCase):

    def test_all_four_activities_complete(self):
        log = [
            {"activity_type": "task_analysis", "completed": True},
            {"activity_type": "user_requirements", "completed": True},
            {"activity_type": "design_production", "completed": True},
            {"activity_type": "design_evaluation", "completed": True},
        ]
        result = check_hcd_activity_completeness(log)
        self.assertTrue(result["complete"])
        self.assertEqual(result["absent"], [])

    def test_missing_design_evaluation(self):
        log = [
            {"activity_type": "task_analysis", "completed": True},
            {"activity_type": "user_requirements", "completed": True},
            {"activity_type": "design_production", "completed": True},
        ]
        result = check_hcd_activity_completeness(log)
        self.assertFalse(result["complete"])
        self.assertIn("design_evaluation", result["absent"])

    def test_completed_false_counts_as_absent(self):
        log = [
            {"activity_type": "task_analysis", "completed": False},
            {"activity_type": "user_requirements", "completed": True},
            {"activity_type": "design_production", "completed": True},
            {"activity_type": "design_evaluation", "completed": True},
        ]
        result = check_hcd_activity_completeness(log)
        self.assertFalse(result["complete"])
        self.assertIn("task_analysis", result["absent"])

    def test_empty_log_all_absent(self):
        result = check_hcd_activity_completeness([])
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["absent"]), 4)

    def test_unknown_activity_type_ignored(self):
        log = [
            {"activity_type": "task_analysis", "completed": True},
            {"activity_type": "user_requirements", "completed": True},
            {"activity_type": "design_production", "completed": True},
            {"activity_type": "design_evaluation", "completed": True},
            {"activity_type": "other_activity", "completed": True},
        ]
        result = check_hcd_activity_completeness(log)
        self.assertTrue(result["complete"])


# ---------------------------------------------------------------------------
# Summary assessment
# ---------------------------------------------------------------------------

class TestSummariseHCDAssessment(unittest.TestCase):

    def _eval_result(self, element_id="D-01", overall_outcome="pass"):
        return {
            "element_id": element_id,
            "criteria_results": [],
            "overall_outcome": overall_outcome,
            "fail_count": 1 if overall_outcome == "fail" else 0,
            "conditional_count": 0,
        }

    def test_clean_assessment_passes(self):
        tasks = [_task("T-01")]
        reqs = [_req("R-01")]
        elems = [_elem("D-01", addresses=["R-01"])]
        evals = [self._eval_result("D-01", "pass")]
        result = summarise_hcd_assessment(tasks, reqs, elems, evals)
        self.assertTrue(result["passed"])
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["requirement_count"], 1)
        self.assertEqual(result["design_element_count"], 1)
        self.assertAlmostEqual(result["coverage_ratio"], 1.0)
        self.assertEqual(result["evaluation_fail_count"], 0)

    def test_uncovered_requirement_fails_assessment(self):
        tasks = [_task("T-01")]
        reqs = [_req("R-01"), _req("R-02")]
        elems = [_elem("D-01", addresses=["R-01"])]
        evals = [self._eval_result("D-01", "pass")]
        result = summarise_hcd_assessment(tasks, reqs, elems, evals)
        self.assertFalse(result["passed"])
        self.assertIn("R-02", result["uncovered_requirements"])

    def test_failed_evaluation_fails_assessment(self):
        tasks = [_task("T-01")]
        reqs = [_req("R-01")]
        elems = [_elem("D-01", addresses=["R-01"])]
        evals = [self._eval_result("D-01", "fail")]
        result = summarise_hcd_assessment(tasks, reqs, elems, evals)
        self.assertFalse(result["passed"])
        self.assertEqual(result["evaluation_fail_count"], 1)

    def test_invalid_task_recorded_in_errors(self):
        bad_task = {"task_id": "T-bad", "description": "broken"}
        result = summarise_hcd_assessment([bad_task], [], [], [])
        self.assertFalse(result["passed"])
        self.assertTrue(len(result["task_errors"]) > 0)

    def test_empty_inputs_passes_with_zero_counts(self):
        result = summarise_hcd_assessment([], [], [], [])
        self.assertTrue(result["passed"])
        self.assertEqual(result["task_count"], 0)
        self.assertEqual(result["requirement_count"], 0)
        self.assertEqual(result["design_element_count"], 0)
        self.assertAlmostEqual(result["coverage_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()

import unittest

from e1002_method_general_logic import (
    ALL_METHODS,
    ANALYSIS,
    INSPECTION,
    REVIEW_OF_DESIGN,
    TEST,
    eligible_methods_for_category,
    evaluate_requirement,
    normalize_category,
    normalize_method,
    summarize_plan,
)


class TestNormalizeMethod(unittest.TestCase):
    def test_normalize_method_case_and_space_insensitive(self):
        self.assertEqual(normalize_method("Test"), TEST)
        self.assertEqual(normalize_method("REVIEW OF DESIGN"), REVIEW_OF_DESIGN)
        self.assertEqual(normalize_method("  inspection  "), INSPECTION)

    def test_normalize_method_rejects_unrecognized(self):
        with self.assertRaises(ValueError):
            normalize_method("demonstration")

    def test_normalize_method_rejects_empty(self):
        with self.assertRaises(ValueError):
            normalize_method("")


class TestNormalizeCategory(unittest.TestCase):
    def test_normalize_category_known(self):
        self.assertEqual(normalize_category("Functional"), "functional")

    def test_normalize_category_rejects_unrecognized(self):
        with self.assertRaises(ValueError):
            normalize_category("cosmetic")


class TestEligibleMethodsForCategory(unittest.TestCase):
    def test_workmanship_is_inspection_only(self):
        self.assertEqual(eligible_methods_for_category("workmanship"), (INSPECTION,))

    def test_design_process_is_review_only(self):
        self.assertEqual(
            eligible_methods_for_category("design-process"), (REVIEW_OF_DESIGN,)
        )

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            eligible_methods_for_category("nonexistent")


class TestEvaluateRequirement(unittest.TestCase):
    def test_valid_functional_requirement(self):
        result = evaluate_requirement(
            "REQ-1", "functional", ["test"], "Direct test of the interface at unit level."
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["primary_method"], TEST)

    def test_ineligible_method_for_category_is_flagged(self):
        result = evaluate_requirement(
            "REQ-2", "workmanship", ["test"], "Attempted test of a workmanship item."
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("ineligible method" in e for e in result["errors"]))

    def test_missing_rationale_is_flagged(self):
        result = evaluate_requirement("REQ-3", "functional", ["test"], "")
        self.assertFalse(result["valid"])
        self.assertIn("missing rationale", result["errors"])

    def test_empty_methods_list_raises(self):
        with self.assertRaises(ValueError):
            evaluate_requirement("REQ-4", "functional", [], "some rationale here")

    def test_safety_critical_without_test_is_flagged(self):
        result = evaluate_requirement(
            "REQ-5",
            "safety-critical",
            ["analysis"],
            "Analysis performed using the qualified thermal model.",
        )
        self.assertFalse(result["valid"])
        self.assertTrue(any("must include the test method" in e for e in result["errors"]))

    def test_safety_critical_with_test_is_valid(self):
        result = evaluate_requirement(
            "REQ-6",
            "safety-critical",
            ["test", "analysis"],
            "Test on flight-representative hardware, cross-checked by analysis.",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["primary_method"], TEST)

    def test_precedence_deviation_with_brief_rationale_warns(self):
        result = evaluate_requirement(
            "REQ-7", "physical", ["inspection"], "Visual check."
        )
        self.assertTrue(result["valid"])
        self.assertTrue(len(result["warnings"]) == 1)
        self.assertIn("precedence deviation not justified", result["warnings"][0])

    def test_precedence_deviation_with_adequate_rationale_no_warning(self):
        result = evaluate_requirement(
            "REQ-8",
            "physical",
            ["inspection"],
            "Test is impractical because the surface finish is destroyed by the "
            "test fixture; inspection against the drawing callout is equivalent.",
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["warnings"], [])

    def test_no_precedence_deviation_when_top_method_selected(self):
        result = evaluate_requirement(
            "REQ-9", "physical", ["test"], "Load test to qualification levels."
        )
        self.assertEqual(result["warnings"], [])

    def test_unrecognized_category_raises(self):
        with self.assertRaises(ValueError):
            evaluate_requirement("REQ-10", "bogus", ["test"], "rationale")


class TestSummarizePlan(unittest.TestCase):
    def test_summarize_counts_and_compliance(self):
        plan = [
            {
                "id": "REQ-1",
                "category": "functional",
                "methods": ["test"],
                "rationale": "End-to-end functional test at system level.",
            },
            {
                "id": "REQ-2",
                "category": "workmanship",
                "methods": ["inspection"],
                "rationale": "Visual inspection per workmanship standard.",
            },
            {
                "id": "REQ-3",
                "category": "functional",
                "methods": ["test"],
                "rationale": "",
            },
        ]
        summary = summarize_plan(plan)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["method_counts"][TEST], 2)
        self.assertEqual(summary["method_counts"][INSPECTION], 1)
        self.assertEqual(summary["non_compliant_ids"], ["REQ-3"])
        self.assertFalse(summary["compliant"])

    def test_summarize_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            summarize_plan([])

    def test_all_methods_tuple_is_complete(self):
        self.assertEqual(set(ALL_METHODS), {TEST, ANALYSIS, REVIEW_OF_DESIGN, INSPECTION})


if __name__ == "__main__":
    unittest.main()

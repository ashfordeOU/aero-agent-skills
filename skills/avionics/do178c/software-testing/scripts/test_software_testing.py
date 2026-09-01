#!/usr/bin/env python3
"""Gate 3 contract test: DO-178C requirements-based testing logic.

Runs with the stdlib unittest runner only; fully offline. Exercises
scripts/software_testing_logic.py: test case counts for statement,
decision, and MC/DC coverage, coverage objectives per software level,
and the required test case count for a given boolean condition.
Run: python3 test_software_testing.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import software_testing_logic as stl  # noqa: E402


class StatementCoverageTests(unittest.TestCase):
    def test_statement_needs_one_case(self):
        self.assertEqual(stl.statement_test_cases(), 1)

    def test_statement_count_ignores_term_count(self):
        for n in (1, 2, 3, 7):
            self.assertEqual(stl.test_cases_for_metric("statement", n), 1)


class DecisionCoverageTests(unittest.TestCase):
    def test_decision_needs_two_cases(self):
        self.assertEqual(stl.decision_test_cases(), 2)

    def test_decision_two_outcomes_anchor(self):
        self.assertEqual(stl.test_cases_for_metric("decision", 3), 2)


class McDcCountTests(unittest.TestCase):
    def test_mcdc_three_term_and_needs_four(self):
        # Worked anchor: A AND B AND C -> 4 cases (TTT, FTT, TFT, TTF).
        self.assertEqual(stl.mc_dc_test_cases(3), 4)

    def test_mcdc_four_term_or_needs_five(self):
        # Worked anchor: A OR B OR C OR D -> 5 cases (FFFF, TFFF, ...).
        self.assertEqual(stl.mc_dc_test_cases(4), 5)

    def test_mcdc_single_term_needs_two(self):
        self.assertEqual(stl.mc_dc_test_cases(1), 2)

    def test_mcdc_count_grows_with_terms(self):
        prev = 0
        for n in range(1, 10):
            cur = stl.mc_dc_test_cases(n)
            self.assertGreater(cur, prev)
            prev = cur

    def test_mcdc_metric_helper_matches(self):
        self.assertEqual(stl.test_cases_for_metric("mc/dc", 3), 4)


class RequiredPerDalTests(unittest.TestCase):
    AND3 = ["A", "B", "C"]

    def test_level_a_uses_mcdc_depth(self):
        # Anchor: level A, 3-term AND -> 4 (MC/DC depth, n + 1).
        self.assertEqual(stl.required_test_cases("A", "AND", self.AND3), 4)

    def test_level_b_uses_decision_depth(self):
        # Anchor: level B, 3-term AND -> 2 (decision depth).
        self.assertEqual(stl.required_test_cases("B", "AND", self.AND3), 2)

    def test_level_c_uses_statement_depth(self):
        # Anchor: level C, 3-term AND -> 1 (statement depth).
        self.assertEqual(stl.required_test_cases("C", "AND", self.AND3), 1)

    def test_levels_d_and_e_require_no_structural_cases(self):
        self.assertEqual(stl.required_test_cases("D", "AND", self.AND3), 0)
        self.assertEqual(stl.required_test_cases("E", "OR", self.AND3), 0)

    def test_dal_depth_monotonic(self):
        # A demands >= B demands >= C demands for the same condition.
        counts = [
            stl.required_test_cases(dal, "AND", self.AND3)
            for dal in ("A", "B", "C", "D")
        ]
        self.assertEqual(counts, [4, 2, 1, 0])
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_or_expression_at_level_a(self):
        self.assertEqual(
            stl.required_test_cases("A", "OR", ["P", "Q", "R", "S"]), 5
        )


class CoverageObjectivesTests(unittest.TestCase):
    def test_level_a_objectives(self):
        self.assertEqual(
            stl.coverage_objectives("A"), ("statement", "decision", "mc/dc")
        )

    def test_level_b_objectives(self):
        self.assertEqual(stl.coverage_objectives("B"), ("statement", "decision"))

    def test_level_c_objectives(self):
        self.assertEqual(stl.coverage_objectives("C"), ("statement",))

    def test_levels_d_e_have_no_objectives(self):
        self.assertEqual(stl.coverage_objectives("D"), ())
        self.assertEqual(stl.coverage_objectives("E"), ())

    def test_coverage_depth_strings(self):
        self.assertEqual(stl.coverage_depth("A"), "mc/dc")
        self.assertEqual(stl.coverage_depth("B"), "decision")
        self.assertEqual(stl.coverage_depth("C"), "statement")
        self.assertEqual(stl.coverage_depth("E"), "none")


class VectorGenerationTests(unittest.TestCase):
    def test_and_vectors_all_true_first(self):
        vectors = stl.generate_mc_dc_vectors("AND", ["A", "B", "C"])
        self.assertEqual(len(vectors), 4)
        self.assertTrue(all(vectors[0].values()))

    def test_and_vectors_flip_one_term_each(self):
        vectors = stl.generate_mc_dc_vectors("AND", ["A", "B", "C"])
        for v in vectors[1:]:
            self.assertEqual(sum(1 for x in v.values() if not x), 1)

    def test_and_vectors_outcome_independence(self):
        # Only the all-true vector evaluates true for AND.
        vectors = stl.generate_mc_dc_vectors("AND", ["A", "B", "C"])
        results = [stl.evaluate_expression("AND", v) for v in vectors]
        self.assertEqual(results.count(True), 1)

    def test_or_vectors_all_false_first(self):
        vectors = stl.generate_mc_dc_vectors("OR", ["P", "Q", "R", "S"])
        self.assertEqual(len(vectors), 5)
        self.assertTrue(not any(vectors[0].values()))

    def test_or_vectors_flip_one_term_each(self):
        vectors = stl.generate_mc_dc_vectors("OR", ["P", "Q", "R", "S"])
        for v in vectors[1:]:
            self.assertEqual(sum(1 for x in v.values() if x), 1)

    def test_evaluate_expression_anchors(self):
        self.assertFalse(stl.evaluate_expression("AND", {"A": True, "B": False}))
        self.assertTrue(stl.evaluate_expression("OR", {"A": False, "B": True}))


class ValidationTests(unittest.TestCase):
    def test_invalid_dal_raises(self):
        for dal in ("F", "a", "", None, 1):
            with self.assertRaises(ValueError):
                stl.required_test_cases(dal, "AND", ["A", "B"])
        with self.assertRaises(ValueError):
            stl.coverage_objectives("Z")

    def test_invalid_operator_raises(self):
        for op in ("NAND", "XOR", "", None, 42):
            with self.assertRaises(ValueError):
                stl.validate_operator(op)

    def test_empty_conditions_raise(self):
        with self.assertRaises(ValueError):
            stl.validate_conditions([])
        with self.assertRaises(ValueError):
            stl.generate_mc_dc_vectors("AND", [])
        with self.assertRaises(ValueError):
            stl.required_test_cases("A", "AND", [])

    def test_blank_and_duplicate_conditions_raise(self):
        with self.assertRaises(ValueError):
            stl.validate_conditions(["A", "  "])
        with self.assertRaises(ValueError):
            stl.validate_conditions(["A", "A"])

    def test_zero_terms_raise(self):
        with self.assertRaises(ValueError):
            stl.mc_dc_test_cases(0)
        with self.assertRaises(ValueError):
            stl.mc_dc_test_cases(-3)

    def test_invalid_metric_raises(self):
        for m in ("path", "branch", "mcdc", None):
            with self.assertRaises(ValueError):
                stl.test_cases_for_metric(m, 2)

    def test_non_bool_assignment_raises(self):
        with self.assertRaises(ValueError):
            stl.evaluate_expression("AND", {"A": 1, "B": 0})


if __name__ == "__main__":
    unittest.main()

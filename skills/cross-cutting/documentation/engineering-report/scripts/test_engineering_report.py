#!/usr/bin/env python3
"""Gate 3 contract test: engineering report structure checks.

Exercises scripts/engineering_report_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the report
anatomy verdict (abstract, introduction, method, results, discussion,
conclusion, references), the abstract length pass/fail on the
recommended 150 to 300 word range, the completeness ratio, the units
and uncertainty statement checks, the margin statement check, and the
requirement traceability closure list. Analytic checks:

- sections present [Abstract, Method, Conclusion] -> missing
  [introduction, results, discussion, references] (4 of 7 missing)
- abstract 200 words -> ok; 149 words -> not ok; 301 words -> not ok
- completeness 3 of 4 required -> 0.75; 5 of 7 -> 0.714 (rounded)
- "The load is 125000 N" -> units ok; "The load is 125000" -> not
- "0.025 +/- 0.003" -> uncertainty ok; "0.025" alone -> not
- "Margin of safety 0.25 (ultimate basis): pass" -> margin ok;
  "Margin of safety 0.25" (no basis) -> not
- traced [REQ-1, REQ-3] vs required [REQ-1, REQ-2, REQ-3] ->
  missing [REQ-2]
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engineering_report_logic as erl  # noqa: E402


class RequiredSectionsVerdictTest(unittest.TestCase):
    def test_missing_sections_analytic(self):
        # Present 3 of 7: abstract, method, conclusion. Canonical
        # missing order: introduction, results, discussion, references.
        missing = erl.required_sections_verdict(
            ["Abstract", "Method", "Conclusion"]
        )
        self.assertEqual(
            missing, ["introduction", "results", "discussion", "references"]
        )

    def test_complete_report(self):
        self.assertEqual(
            erl.required_sections_verdict(
                [
                    "abstract",
                    "introduction",
                    "method",
                    "results",
                    "discussion",
                    "conclusion",
                    "references",
                ]
            ),
            [],
        )

    def test_empty_present_misses_all(self):
        self.assertEqual(
            erl.required_sections_verdict([]),
            erl.REQUIRED_SECTIONS,
        )

    def test_matching_is_case_and_space_insensitive(self):
        self.assertEqual(
            erl.required_sections_verdict(
                [" ABSTRACT ", "Introduction", "Method", "Results",
                 "Discussion", "Conclusion", "References"]
            ),
            [],
        )

    def test_extra_sections_ignored(self):
        self.assertEqual(
            erl.required_sections_verdict(
                ["Abstract", "Introduction", "Method", "Results",
                 "Discussion", "Conclusion", "References", "Appendix"]
            ),
            [],
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            erl.required_sections_verdict("abstract")
        with self.assertRaises(ValueError):
            erl.required_sections_verdict(["Abstract", 5])


class AbstractLengthOkTest(unittest.TestCase):
    def test_bounds_analytic(self):
        # Range is 150 to 300 words inclusive.
        self.assertTrue(erl.abstract_length_ok(150))
        self.assertTrue(erl.abstract_length_ok(300))
        self.assertTrue(erl.abstract_length_ok(200))
        self.assertFalse(erl.abstract_length_ok(149))
        self.assertFalse(erl.abstract_length_ok(301))
        self.assertFalse(erl.abstract_length_ok(0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            erl.abstract_length_ok(-5)
        with self.assertRaises(ValueError):
            erl.abstract_length_ok("two hundred")


class ReportCompletenessScoreTest(unittest.TestCase):
    def test_three_of_four(self):
        # 3 of 4 required present -> 0.75
        self.assertAlmostEqual(
            erl.report_completeness_score(
                ["abstract", "method", "conclusion"],
                ["abstract", "introduction", "method", "conclusion"],
            ),
            0.75,
        )

    def test_five_of_seven(self):
        # 5 / 7 = 0.7142857... rounded to 3 decimals -> 0.714
        self.assertEqual(
            erl.report_completeness_score(
                ["abstract", "introduction", "method", "results", "conclusion"],
                erl.REQUIRED_SECTIONS,
            ),
            0.714,
        )

    def test_complete_and_empty(self):
        self.assertEqual(
            erl.report_completeness_score(
                ["a", "b", "c", "d"], ["a", "b", "c", "d"]
            ),
            1.0,
        )
        self.assertEqual(
            erl.report_completeness_score(["x", "y"], ["a", "b", "c"]),
            0.0,
        )

    def test_case_insensitive_match(self):
        # 2 of 3 required present, matched case-insensitively -> 0.667
        self.assertEqual(
            erl.report_completeness_score(
                ["Abstract", "method"], ["abstract", "introduction", "method"]
            ),
            0.667,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            erl.report_completeness_score(["a"], [])
        with self.assertRaises(ValueError):
            erl.report_completeness_score("a", ["a"])
        with self.assertRaises(ValueError):
            erl.report_completeness_score(["a"], ["a", 2])


class UnitsStatementOkTest(unittest.TestCase):
    def test_value_with_unit_passes(self):
        self.assertTrue(erl.units_statement_ok("The load is 125000 N"))
        self.assertTrue(erl.units_statement_ok("The load is 125000 newtons"))
        self.assertTrue(erl.units_statement_ok("Temperature was 298 K"))
        self.assertTrue(erl.units_statement_ok("Pressure is 101325 Pa"))
        self.assertTrue(
            erl.units_statement_ok("The mass is 5 kg and acceleration 9.81 m/s^2")
        )

    def test_value_without_unit_fails(self):
        self.assertFalse(erl.units_statement_ok("The load is 125000"))
        self.assertFalse(erl.units_statement_ok("Speed measured in m/s"))
        self.assertFalse(erl.units_statement_ok(""))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            erl.units_statement_ok(5)


class UncertaintyStatementOkTest(unittest.TestCase):
    def test_marker_with_number_passes(self):
        self.assertTrue(
            erl.uncertainty_statement_ok("The drag coefficient is 0.025 +/- 0.003")
        )
        self.assertTrue(erl.uncertainty_statement_ok("Combined uncertainty 2.1 kg"))
        self.assertTrue(erl.uncertainty_statement_ok("Tolerance is 5 percent"))
        self.assertTrue(erl.uncertainty_statement_ok("plus or minus 5 N"))

    def test_missing_number_or_marker_fails(self):
        self.assertFalse(erl.uncertainty_statement_ok("The drag coefficient is 0.025"))
        self.assertFalse(
            erl.uncertainty_statement_ok("The result is 3.2 with no stated variation")
        )

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            erl.uncertainty_statement_ok(None)


class MarginStatementOkTest(unittest.TestCase):
    def test_margin_with_basis_passes(self):
        self.assertTrue(
            erl.margin_statement_ok("Margin of safety 0.25 (ultimate basis): pass")
        )
        self.assertTrue(erl.margin_statement_ok("The margin is 0.25 with limit basis"))
        self.assertTrue(erl.margin_statement_ok("Margin 0.25 (ultimate basis): fail"))

    def test_missing_basis_or_value_fails(self):
        self.assertFalse(erl.margin_statement_ok("Margin of safety 0.25"))
        self.assertFalse(erl.margin_statement_ok("No margin computed"))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            erl.margin_statement_ok(42)


class TraceabilityVerdictTest(unittest.TestCase):
    def test_missing_id_analytic(self):
        # REQ-2 untraced: missing list is sorted [REQ-2]
        self.assertEqual(
            erl.traceability_verdict(["REQ-1", "REQ-3"], ["REQ-1", "REQ-2", "REQ-3"]),
            ["REQ-2"],
        )

    def test_closed_traceability(self):
        self.assertEqual(
            erl.traceability_verdict(["REQ-1", "REQ-2"], ["REQ-1", "REQ-2"]),
            [],
        )

    def test_extra_traced_ids_ignored(self):
        self.assertEqual(
            erl.traceability_verdict(["REQ-1", "REQ-9"], ["REQ-1"]),
            [],
        )

    def test_unsorted_required_sorted_output(self):
        self.assertEqual(
            erl.traceability_verdict(["REQ-1"], ["REQ-3", "REQ-1"]),
            ["REQ-3"],
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            erl.traceability_verdict("REQ-1", ["REQ-1"])
        with self.assertRaises(ValueError):
            erl.traceability_verdict(["REQ-1"], ["REQ-1", 2])


if __name__ == "__main__":
    unittest.main(verbosity=2)

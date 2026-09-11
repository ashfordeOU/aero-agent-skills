#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-analysis-report-guide (stdlib, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_analysis_report_guide_logic import (  # noqa: E402
    CONCLUSION_VERDICTS, REQUIRED_SECTIONS, analysis_report_review,
    conclusion_supported, input_provenance_violations,
    is_report_usable_as_evidence, missing_sections, tool_qualification_violations,
    uncertainty_violations, validate_verdict,
)


def sections(**over):
    s = {n: "content for %s" % n for n in REQUIRED_SECTIONS}
    s.update(over)
    return s


def report(**over):
    r = {"sections": sections(),
         "inputs": [{"name": "launch load spectrum", "source": "LV user manual 3.2"}],
         "tool": {"name": "FEM-SOLVER", "qualified": True},
         "results": [{"quantity": "peak stress", "value": 180.0,
                      "uncertainty": 10.0, "limit": 250.0}],
         "conclusion_verdict": "requirement_met"}
    r.update(over)
    return r


class VerdictTest(unittest.TestCase):
    def test_every_verdict_validates(self):
        for v in CONCLUSION_VERDICTS:
            self.assertEqual(validate_verdict(v), v)

    def test_unknown_verdict_raises(self):
        with self.assertRaises(ValueError):
            validate_verdict("probably_fine")


class SectionTest(unittest.TestCase):
    def test_complete_report_has_no_missing_sections(self):
        self.assertEqual(missing_sections(report()), [])

    def test_absent_section_is_reported(self):
        s = sections()
        del s["uncertainty"]
        self.assertEqual(missing_sections({"sections": s}), ["uncertainty"])

    def test_blank_section_counts_as_missing(self):
        self.assertEqual(missing_sections({"sections": sections(conclusion=" ")}),
                         ["conclusion"])

    def test_sections_reported_in_declared_order(self):
        s = sections()
        del s["conclusion"]
        del s["objective"]
        self.assertEqual(missing_sections({"sections": s}),
                         ["objective", "conclusion"])


class InputTest(unittest.TestCase):
    def test_sourced_input_is_clean(self):
        self.assertEqual(input_provenance_violations(report()["inputs"]), [])

    def test_unsourced_input_is_reported(self):
        f = input_provenance_violations([{"name": "modulus", "source": ""}])
        self.assertEqual(f[0]["issue"], "input_without_source")

    def test_unnamed_input_raises(self):
        with self.assertRaises(ValueError):
            input_provenance_violations([{"source": "somewhere"}])


class ToolTest(unittest.TestCase):
    def test_qualified_tool_is_clean(self):
        self.assertEqual(tool_qualification_violations(report()), [])

    def test_unnamed_tool_is_reported(self):
        f = tool_qualification_violations({"tool": {"name": ""}})
        self.assertEqual(f[0]["issue"], "tool_not_named")

    def test_unnamed_tool_short_circuits_the_status_check(self):
        self.assertEqual(len(tool_qualification_violations({"tool": {}})), 1)

    def test_unstated_qualification_is_reported(self):
        f = tool_qualification_violations({"tool": {"name": "X"}})
        self.assertEqual(f[0]["issue"], "tool_qualification_unstated")

    def test_unqualified_tool_is_reported(self):
        f = tool_qualification_violations({"tool": {"name": "X", "qualified": False}})
        self.assertEqual(f[0]["issue"], "tool_not_qualified")


class UncertaintyTest(unittest.TestCase):
    def test_result_with_uncertainty_is_clean(self):
        self.assertEqual(uncertainty_violations(report()), [])

    def test_result_without_uncertainty_is_reported(self):
        r = report(results=[{"quantity": "mass", "value": 1.0, "limit": 2.0}])
        self.assertEqual(uncertainty_violations(r)[0]["issue"],
                         "result_without_uncertainty")

    def test_zero_uncertainty_is_allowed(self):
        r = report(results=[{"quantity": "count", "value": 3, "uncertainty": 0,
                             "limit": 5}])
        self.assertEqual(uncertainty_violations(r), [])

    def test_negative_uncertainty_raises(self):
        r = report(results=[{"quantity": "mass", "value": 1.0,
                             "uncertainty": -1.0, "limit": 2.0}])
        with self.assertRaises(ValueError):
            uncertainty_violations(r)

    def test_unnamed_result_raises(self):
        with self.assertRaises(ValueError):
            uncertainty_violations({"results": [{"value": 1.0, "uncertainty": 0.1}]})


class ConclusionTest(unittest.TestCase):
    def test_supported_compliance_claim_passes(self):
        self.assertTrue(conclusion_supported(report()))

    def test_margin_smaller_than_uncertainty_is_unsupported(self):
        r = report(results=[{"quantity": "peak stress", "value": 245.0,
                             "uncertainty": 10.0, "limit": 250.0}])
        self.assertFalse(conclusion_supported(r))

    def test_missing_limit_cannot_support_compliance(self):
        r = report(results=[{"quantity": "x", "value": 1.0, "uncertainty": 0.0}])
        self.assertFalse(conclusion_supported(r))

    def test_non_compliance_conclusion_needs_no_support(self):
        r = report(conclusion_verdict="requirement_not_met",
                   results=[{"quantity": "x", "value": 999.0,
                             "uncertainty": 1.0, "limit": 2.0}])
        self.assertTrue(conclusion_supported(r))

    def test_inconclusive_verdict_needs_no_support(self):
        self.assertTrue(conclusion_supported(report(conclusion_verdict="inconclusive")))


class ReviewTest(unittest.TestCase):
    def test_complete_report_is_usable_as_evidence(self):
        r = analysis_report_review(report())
        self.assertEqual(r["verdict"], "requirement_met")
        self.assertTrue(is_report_usable_as_evidence(r))

    def test_unsupported_conclusion_blocks_use_as_evidence(self):
        rep = report(results=[{"quantity": "s", "value": 249.0,
                               "uncertainty": 5.0, "limit": 250.0}])
        rev = analysis_report_review(rep)
        self.assertIn("conclusion_not_supported_by_results",
                      [f["issue"] for f in rev["findings"]])
        self.assertFalse(is_report_usable_as_evidence(rev))

    def test_missing_section_blocks_use_as_evidence(self):
        s = sections()
        del s["method_and_tool"]
        self.assertFalse(is_report_usable_as_evidence(
            analysis_report_review(report(sections=s))))

    def test_review_does_not_mutate_input(self):
        rep = report()
        before = copy.deepcopy(rep)
        analysis_report_review(rep)
        self.assertEqual(rep, before)

    def test_unknown_verdict_raises_from_the_review(self):
        with self.assertRaises(ValueError):
            analysis_report_review(report(conclusion_verdict="ok"))


if __name__ == "__main__":
    unittest.main()

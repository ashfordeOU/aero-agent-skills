#!/usr/bin/env python3
"""Gate 3 behavior contract for e1002-analysis-report (stdlib, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1002_analysis_report_logic import (  # noqa: E402
    CASE_VERDICTS, analysis_report_verification_review, baseline_violations,
    case_violations, extraneous_cases, is_requirement_verified_by_analysis,
    requirement_verdict, uncovered_cases, validate_case_verdict,
)

BASELINE = "DESIGN-REV-D"
REQUIRED = ["hot_case", "cold_case", "launch_case"]


def cases(**over):
    c = [{"case_id": "hot_case", "verdict": "pass"},
         {"case_id": "cold_case", "verdict": "pass"},
         {"case_id": "launch_case", "verdict": "pass"}]
    return over.get("cases", c)


def report(**over):
    r = {"requirement_id": "R-THERM-1", "model_baseline": BASELINE,
         "cases": cases()}
    r.update(over)
    return r


class VerdictVocabularyTest(unittest.TestCase):
    def test_every_case_verdict_validates(self):
        for v in CASE_VERDICTS:
            self.assertEqual(validate_case_verdict(v), v)

    def test_unknown_case_verdict_raises(self):
        with self.assertRaises(ValueError):
            validate_case_verdict("green")


class CoverageTest(unittest.TestCase):
    def test_full_envelope_coverage_reports_nothing(self):
        self.assertEqual(uncovered_cases(REQUIRED, cases()), [])

    def test_hole_in_the_envelope_is_reported(self):
        partial = [c for c in cases() if c["case_id"] != "cold_case"]
        self.assertEqual(uncovered_cases(REQUIRED, partial), ["cold_case"])

    def test_uncovered_cases_keep_declared_order(self):
        self.assertEqual(uncovered_cases(REQUIRED, []), REQUIRED)

    def test_extra_case_outside_the_envelope_is_reported(self):
        extra = cases() + [{"case_id": "bonus_case", "verdict": "pass"}]
        self.assertEqual(extraneous_cases(REQUIRED, extra), ["bonus_case"])

    def test_matching_matrix_has_no_extraneous_cases(self):
        self.assertEqual(extraneous_cases(REQUIRED, cases()), [])


class BaselineTest(unittest.TestCase):
    def test_matching_baseline_is_clean(self):
        self.assertEqual(baseline_violations(report(), BASELINE), [])

    def test_unstated_baseline_is_reported(self):
        f = baseline_violations(report(model_baseline=""), BASELINE)
        self.assertEqual(f[0]["issue"], "model_baseline_unstated")

    def test_superseded_baseline_is_a_different_finding(self):
        f = baseline_violations(report(), "DESIGN-REV-E")
        self.assertEqual(f[0]["issue"], "model_baseline_superseded")
        self.assertEqual(f[0]["declared"], BASELINE)


class CaseTest(unittest.TestCase):
    def test_cases_with_verdicts_are_clean(self):
        self.assertEqual(case_violations(cases()), [])

    def test_case_without_verdict_is_reported(self):
        f = case_violations([{"case_id": "hot_case"}])
        self.assertEqual(f[0]["issue"], "case_without_verdict")

    def test_not_run_without_reason_is_reported(self):
        f = case_violations([{"case_id": "hot_case", "verdict": "not_run"}])
        self.assertEqual(f[0]["issue"], "case_not_run_without_reason")

    def test_not_run_with_reason_is_clean(self):
        self.assertEqual(case_violations([
            {"case_id": "hot_case", "verdict": "not_run",
             "reason": "enveloped by the launch case"}]), [])

    def test_duplicate_case_id_raises(self):
        with self.assertRaises(ValueError):
            case_violations([{"case_id": "c", "verdict": "pass"},
                             {"case_id": "c", "verdict": "pass"}])

    def test_case_without_id_raises(self):
        with self.assertRaises(ValueError):
            case_violations([{"verdict": "pass"}])


class RollUpTest(unittest.TestCase):
    def test_all_pass_verifies(self):
        self.assertEqual(requirement_verdict(cases()), "pass")

    def test_one_failing_case_fails_the_requirement(self):
        c = cases()
        c[1]["verdict"] = "fail"
        self.assertEqual(requirement_verdict(c), "fail")

    def test_not_run_leaves_it_incomplete(self):
        c = cases()
        c[2]["verdict"] = "not_run"
        self.assertEqual(requirement_verdict(c), "incomplete")

    def test_fail_dominates_not_run(self):
        c = cases()
        c[0]["verdict"] = "not_run"
        c[1]["verdict"] = "fail"
        self.assertEqual(requirement_verdict(c), "fail")

    def test_no_verdicts_raises(self):
        with self.assertRaises(ValueError):
            requirement_verdict([{"case_id": "x"}])


class ReviewTest(unittest.TestCase):
    def test_clean_report_verifies_the_requirement(self):
        r = analysis_report_verification_review(report(), REQUIRED, BASELINE)
        self.assertEqual(r["verdict"], "pass")
        self.assertTrue(is_requirement_verified_by_analysis(r))

    def test_superseded_baseline_blocks_verification(self):
        r = analysis_report_verification_review(report(), REQUIRED, "DESIGN-REV-E")
        self.assertFalse(is_requirement_verified_by_analysis(r))

    def test_envelope_hole_blocks_verification_even_when_cases_pass(self):
        partial = [c for c in cases() if c["case_id"] != "launch_case"]
        r = analysis_report_verification_review(report(cases=partial),
                                                REQUIRED, BASELINE)
        self.assertEqual(r["verdict"], "pass")
        self.assertIn("envelope_case_not_analysed",
                      [f["issue"] for f in r["findings"]])
        self.assertFalse(is_requirement_verified_by_analysis(r))

    def test_report_without_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            analysis_report_verification_review(report(requirement_id=""),
                                                REQUIRED, BASELINE)

    def test_review_does_not_mutate_input(self):
        rep = report()
        before = copy.deepcopy(rep)
        analysis_report_verification_review(rep, REQUIRED, BASELINE)
        self.assertEqual(rep, before)


if __name__ == "__main__":
    unittest.main()

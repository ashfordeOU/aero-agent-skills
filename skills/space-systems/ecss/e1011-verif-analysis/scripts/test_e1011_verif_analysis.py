"""
test_e1011_verif_analysis.py

Offline deterministic contract tests for e1011_verif_analysis_logic.
Run:  python3 test_e1011_verif_analysis.py

stdlib unittest only. No network. No external dependencies.
"""

import unittest
import sys
import os

# Allow running from the scripts directory or from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from e1011_verif_analysis_logic import (
    select_analysis_method,
    score_similarity,
    check_dhm_result,
    check_report_completeness,
    aggregate_findings,
    AnalysisMethod,
    SimilarityClaim,
    DimensionScore,
    DHMResult,
    AnalysisReport,
    Finding,
    VALID_ANALYSIS_METHODS,
    SIMILARITY_DIMENSIONS,
    SIMILARITY_PASS_THRESHOLD,
    DHM_JOINT_ANGLE_MAX_DEG,
    DHM_FORCE_MAX_N,
    DHM_VISUAL_ANGLE_MAX_DEG,
    ANNEX_B_CORE_FIELDS,
)


def _make_perfect_claim(heritage_id="HER-001", target_id="TGT-001") -> SimilarityClaim:
    """Return a similarity claim where all four dimensions score 1.0."""
    return SimilarityClaim(
        heritage_id=heritage_id,
        target_id=target_id,
        dimension_scores=tuple(
            DimensionScore(dimension=d, score=1.0) for d in SIMILARITY_DIMENSIONS
        ),
    )


def _make_dhm_all_pass(scenario_id="SC-001") -> DHMResult:
    """Return a DHM result that satisfies all four acceptance criteria."""
    return DHMResult(
        scenario_id=scenario_id,
        joint_angle_max_deviation_deg=15.0,
        reach_zone_compliant=True,
        max_force_n=100.0,
        visual_angle_max_deg=20.0,
    )


def _make_complete_report(method: str = "task_analysis") -> AnalysisReport:
    """Return an AnalysisReport with all required Annex B core fields populated."""
    fields = {f: f"value-for-{f}" for f in ANNEX_B_CORE_FIELDS}
    fields["method"] = method
    if method == "similarity":
        fields["heritage_reference"] = "HER-001"
    if method == "dhm_simulation":
        fields["dhm_software"] = "DHM-Tool v2.3"
    return AnalysisReport(fields=fields)


# ---------------------------------------------------------------------------
# Tests: select_analysis_method
# ---------------------------------------------------------------------------


class TestSelectAnalysisMethod(unittest.TestCase):

    def test_valid_method_returns_analysis_method(self):
        result = select_analysis_method("task_analysis")
        self.assertIsInstance(result, AnalysisMethod)
        self.assertEqual(result.method_type, "task_analysis")
        self.assertTrue(len(result.description) > 0)

    def test_all_valid_methods_accepted(self):
        for method in VALID_ANALYSIS_METHODS:
            with self.subTest(method=method):
                m = select_analysis_method(method)
                self.assertEqual(m.method_type, method)

    def test_invalid_method_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            select_analysis_method("magic_analysis")
        self.assertIn("magic_analysis", str(ctx.exception))

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            select_analysis_method("")

    def test_dhm_simulation_method_has_description(self):
        m = select_analysis_method("dhm_simulation")
        self.assertIn("digital human model", m.description.lower())


# ---------------------------------------------------------------------------
# Tests: score_similarity
# ---------------------------------------------------------------------------


class TestScoreSimilarity(unittest.TestCase):

    def test_perfect_score_grants_heritage_credit(self):
        claim = _make_perfect_claim()
        score, findings = score_similarity(claim)
        self.assertAlmostEqual(score, 1.0)
        composite = [f for f in findings if "composite" in f.item_id]
        self.assertEqual(len(composite), 1)
        self.assertEqual(composite[0].severity, "pass")

    def test_score_below_threshold_denies_credit(self):
        # All dimensions at 0.5 → composite 0.5 < 0.80
        claim = SimilarityClaim(
            heritage_id="H", target_id="T",
            dimension_scores=tuple(
                DimensionScore(d, 0.5) for d in SIMILARITY_DIMENSIONS
            ),
        )
        score, findings = score_similarity(claim)
        self.assertAlmostEqual(score, 0.5)
        composite = [f for f in findings if "composite" in f.item_id]
        self.assertEqual(composite[0].severity, "fail")

    def test_at_threshold_grants_credit(self):
        claim = SimilarityClaim(
            heritage_id="H", target_id="T",
            dimension_scores=tuple(
                DimensionScore(d, SIMILARITY_PASS_THRESHOLD) for d in SIMILARITY_DIMENSIONS
            ),
        )
        score, findings = score_similarity(claim)
        self.assertAlmostEqual(score, SIMILARITY_PASS_THRESHOLD)
        composite = [f for f in findings if "composite" in f.item_id]
        self.assertEqual(composite[0].severity, "pass")

    def test_missing_dimension_raises_value_error(self):
        # Only supply three of four dimensions
        partial = SimilarityClaim(
            heritage_id="H", target_id="T",
            dimension_scores=(
                DimensionScore("function", 0.9),
                DimensionScore("physical_form", 0.9),
                DimensionScore("environment", 0.9),
                # "user_population" missing
            ),
        )
        with self.assertRaises(ValueError) as ctx:
            score_similarity(partial)
        self.assertIn("user_population", str(ctx.exception))

    def test_invalid_dimension_name_raises_value_error(self):
        claim = SimilarityClaim(
            heritage_id="H", target_id="T",
            dimension_scores=(
                DimensionScore("function", 0.9),
                DimensionScore("physical_form", 0.9),
                DimensionScore("environment", 0.9),
                DimensionScore("unknown_dim", 0.9),
            ),
        )
        with self.assertRaises(ValueError) as ctx:
            score_similarity(claim)
        self.assertIn("unknown_dim", str(ctx.exception))

    def test_score_out_of_range_raises_value_error(self):
        claim = SimilarityClaim(
            heritage_id="H", target_id="T",
            dimension_scores=tuple(
                DimensionScore(d, 1.5 if d == "function" else 0.9)
                for d in SIMILARITY_DIMENSIONS
            ),
        )
        with self.assertRaises(ValueError):
            score_similarity(claim)

    def test_low_dimension_score_produces_fail_finding(self):
        # One dimension at 0.2; others at 1.0
        scores = {d: (0.2 if d == "environment" else 1.0) for d in SIMILARITY_DIMENSIONS}
        claim = SimilarityClaim(
            heritage_id="H", target_id="T",
            dimension_scores=tuple(DimensionScore(d, v) for d, v in scores.items()),
        )
        _, findings = score_similarity(claim)
        env_findings = [f for f in findings if ".environment" in f.item_id]
        self.assertEqual(len(env_findings), 1)
        self.assertEqual(env_findings[0].severity, "fail")


# ---------------------------------------------------------------------------
# Tests: check_dhm_result
# ---------------------------------------------------------------------------


class TestCheckDHMResult(unittest.TestCase):

    def test_all_criteria_pass(self):
        result = _make_dhm_all_pass()
        findings = check_dhm_result(result)
        self.assertEqual(len(findings), 4)
        self.assertTrue(all(f.severity == "pass" for f in findings))

    def test_joint_angle_exceed_limit_fails(self):
        result = DHMResult(
            scenario_id="SC-02",
            joint_angle_max_deviation_deg=DHM_JOINT_ANGLE_MAX_DEG + 5.0,
            reach_zone_compliant=True,
            max_force_n=50.0,
            visual_angle_max_deg=10.0,
        )
        findings = check_dhm_result(result)
        joint_f = [f for f in findings if "joint_angle" in f.item_id]
        self.assertEqual(len(joint_f), 1)
        self.assertEqual(joint_f[0].severity, "fail")

    def test_reach_zone_noncompliant_fails(self):
        result = DHMResult(
            scenario_id="SC-03",
            joint_angle_max_deviation_deg=10.0,
            reach_zone_compliant=False,
            max_force_n=50.0,
            visual_angle_max_deg=10.0,
        )
        findings = check_dhm_result(result)
        reach_f = [f for f in findings if "reach_zone" in f.item_id]
        self.assertEqual(reach_f[0].severity, "fail")

    def test_force_exceed_limit_fails(self):
        result = DHMResult(
            scenario_id="SC-04",
            joint_angle_max_deviation_deg=10.0,
            reach_zone_compliant=True,
            max_force_n=DHM_FORCE_MAX_N + 1.0,
            visual_angle_max_deg=10.0,
        )
        findings = check_dhm_result(result)
        force_f = [f for f in findings if "force" in f.item_id]
        self.assertEqual(force_f[0].severity, "fail")

    def test_visual_angle_exceed_limit_fails(self):
        result = DHMResult(
            scenario_id="SC-05",
            joint_angle_max_deviation_deg=10.0,
            reach_zone_compliant=True,
            max_force_n=50.0,
            visual_angle_max_deg=DHM_VISUAL_ANGLE_MAX_DEG + 0.1,
        )
        findings = check_dhm_result(result)
        vis_f = [f for f in findings if "visual_angle" in f.item_id]
        self.assertEqual(vis_f[0].severity, "fail")

    def test_at_exact_joint_angle_limit_passes(self):
        result = DHMResult(
            scenario_id="SC-06",
            joint_angle_max_deviation_deg=DHM_JOINT_ANGLE_MAX_DEG,
            reach_zone_compliant=True,
            max_force_n=50.0,
            visual_angle_max_deg=10.0,
        )
        findings = check_dhm_result(result)
        joint_f = [f for f in findings if "joint_angle" in f.item_id]
        self.assertEqual(joint_f[0].severity, "pass")

    def test_always_returns_four_findings(self):
        result = _make_dhm_all_pass("SC-07")
        findings = check_dhm_result(result)
        self.assertEqual(len(findings), 4)


# ---------------------------------------------------------------------------
# Tests: check_report_completeness
# ---------------------------------------------------------------------------


class TestCheckReportCompleteness(unittest.TestCase):

    def test_complete_core_report_passes(self):
        report = _make_complete_report("task_analysis")
        findings = check_report_completeness(report, "task_analysis")
        self.assertTrue(any(f.severity == "pass" for f in findings))
        self.assertFalse(any(f.severity == "fail" for f in findings))

    def test_missing_core_field_produces_fail_finding(self):
        fields = {f: "v" for f in ANNEX_B_CORE_FIELDS if f != "recommendation"}
        fields["method"] = "task_analysis"
        report = AnalysisReport(fields=fields)
        findings = check_report_completeness(report, "task_analysis")
        fail_f = [f for f in findings if f.severity == "fail"]
        self.assertEqual(len(fail_f), 1)
        self.assertIn("recommendation", fail_f[0].detail)

    def test_similarity_report_requires_heritage_reference(self):
        # Build a report with core fields only — no heritage_reference
        fields = {f: "v" for f in ANNEX_B_CORE_FIELDS}
        fields["method"] = "similarity"
        report = AnalysisReport(fields=fields)
        findings = check_report_completeness(report, "similarity")
        fail_f = [f for f in findings if f.severity == "fail"]
        field_names = [f.detail for f in fail_f]
        self.assertTrue(any("heritage_reference" in d for d in field_names))

    def test_dhm_report_requires_dhm_software(self):
        fields = {f: "v" for f in ANNEX_B_CORE_FIELDS}
        fields["method"] = "dhm_simulation"
        report = AnalysisReport(fields=fields)
        findings = check_report_completeness(report, "dhm_simulation")
        fail_f = [f for f in findings if f.severity == "fail"]
        self.assertTrue(any("dhm_software" in f.detail for f in fail_f))

    def test_invalid_method_raises_value_error(self):
        report = _make_complete_report("task_analysis")
        with self.assertRaises(ValueError):
            check_report_completeness(report, "not_a_method")


# ---------------------------------------------------------------------------
# Tests: aggregate_findings
# ---------------------------------------------------------------------------


class TestAggregateFindings(unittest.TestCase):

    def test_all_pass_findings_yield_pass_status(self):
        findings = [Finding("a", "pass", "ok"), Finding("b", "pass", "ok")]
        summary = aggregate_findings(findings)
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["fail_count"], 0)
        self.assertEqual(summary["pass_count"], 2)

    def test_any_fail_finding_yields_fail_status(self):
        findings = [
            Finding("a", "pass", "ok"),
            Finding("b", "fail", "bad"),
        ]
        summary = aggregate_findings(findings)
        self.assertEqual(summary["status"], "fail")
        self.assertEqual(summary["fail_count"], 1)

    def test_counts_are_correct(self):
        findings = [
            Finding("a", "pass", ""),
            Finding("b", "warn", ""),
            Finding("c", "fail", ""),
            Finding("d", "fail", ""),
        ]
        summary = aggregate_findings(findings)
        self.assertEqual(summary["pass_count"], 1)
        self.assertEqual(summary["warn_count"], 1)
        self.assertEqual(summary["fail_count"], 2)
        self.assertEqual(summary["total"], 4)

    def test_empty_findings_list_yields_pass(self):
        summary = aggregate_findings([])
        self.assertEqual(summary["status"], "pass")
        self.assertEqual(summary["total"], 0)


if __name__ == "__main__":
    unittest.main()

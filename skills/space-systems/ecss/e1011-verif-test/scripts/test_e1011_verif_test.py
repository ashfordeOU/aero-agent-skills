"""
Gate 3 contract test — e1011-verif-test.
stdlib unittest only; offline, deterministic. Run: python3 test_e1011_verif_test.py
"""

import unittest

from e1011_verif_test_logic import (
    AnnexDEvent,
    HFERequirementError,
    MANDATORY_ANNEX_D_EVENTS,
    OBSERVABLE_METHODS,
    VerificationMethod,
    aggregate_findings,
    check_mandatory_event_coverage,
    compute_compliance_summary,
    evaluate_test_readiness,
    parse_annex_d_event,
    parse_verification_method,
    validate_requirement,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _req(**overrides):
    base = {
        "req_id": "HFE-001",
        "description": "Crew completes nominal docking procedure",
        "method": "D",
        "annex_d_event": "FUNCTIONAL_TASK",
        "status": "PASS",
    }
    base.update(overrides)
    return base


def _full_coverage_reqs():
    """Return a minimal set that covers all five mandatory Annex D events."""
    return [
        _req(req_id="R1", method="D", annex_d_event="FUNCTIONAL_TASK",         status="PASS"),
        _req(req_id="R2", method="T", annex_d_event="ERGONOMIC_ASSESSMENT",     status="PASS"),
        _req(req_id="R3", method="T", annex_d_event="COGNITIVE_WORKLOAD",       status="PASS"),
        _req(req_id="R4", method="T", annex_d_event="DISPLAY_CONTROL_INTERFACE",status="PASS"),
        _req(req_id="R5", method="D", annex_d_event="EMERGENCY_PROCEDURE",      status="PASS"),
    ]


# ---------------------------------------------------------------------------
# parse_verification_method
# ---------------------------------------------------------------------------

class TestParseVerificationMethod(unittest.TestCase):

    def test_parse_test_method(self):
        self.assertEqual(parse_verification_method("T"), VerificationMethod.TEST)

    def test_parse_demonstration_method(self):
        self.assertEqual(parse_verification_method("D"), VerificationMethod.DEMONSTRATION)

    def test_parse_analysis_method(self):
        self.assertEqual(parse_verification_method("A"), VerificationMethod.ANALYSIS)

    def test_parse_inspection_method(self):
        self.assertEqual(parse_verification_method("I"), VerificationMethod.INSPECTION)

    def test_parse_lowercase_is_accepted(self):
        self.assertEqual(parse_verification_method("t"), VerificationMethod.TEST)

    def test_parse_with_whitespace(self):
        self.assertEqual(parse_verification_method("  D  "), VerificationMethod.DEMONSTRATION)

    def test_parse_unknown_code_raises(self):
        with self.assertRaises(HFERequirementError):
            parse_verification_method("X")

    def test_parse_empty_string_raises(self):
        with self.assertRaises(HFERequirementError):
            parse_verification_method("")

    def test_observable_methods_set_contains_t_and_d(self):
        self.assertIn(VerificationMethod.TEST, OBSERVABLE_METHODS)
        self.assertIn(VerificationMethod.DEMONSTRATION, OBSERVABLE_METHODS)
        self.assertNotIn(VerificationMethod.ANALYSIS, OBSERVABLE_METHODS)
        self.assertNotIn(VerificationMethod.INSPECTION, OBSERVABLE_METHODS)


# ---------------------------------------------------------------------------
# parse_annex_d_event
# ---------------------------------------------------------------------------

class TestParseAnnexDEvent(unittest.TestCase):

    def test_parse_functional_task(self):
        self.assertEqual(
            parse_annex_d_event("FUNCTIONAL_TASK"), AnnexDEvent.FUNCTIONAL_TASK
        )

    def test_parse_lowercase_event(self):
        self.assertEqual(
            parse_annex_d_event("ergonomic_assessment"),
            AnnexDEvent.ERGONOMIC_ASSESSMENT,
        )

    def test_parse_emergency_procedure(self):
        self.assertEqual(
            parse_annex_d_event("EMERGENCY_PROCEDURE"),
            AnnexDEvent.EMERGENCY_PROCEDURE,
        )

    def test_parse_unknown_event_raises(self):
        with self.assertRaises(HFERequirementError):
            parse_annex_d_event("MADE_UP_EVENT")

    def test_mandatory_events_all_parseable(self):
        for event in MANDATORY_ANNEX_D_EVENTS:
            result = parse_annex_d_event(event.value)
            self.assertEqual(result, event)


# ---------------------------------------------------------------------------
# validate_requirement
# ---------------------------------------------------------------------------

class TestValidateRequirement(unittest.TestCase):

    def test_valid_demonstration_requirement(self):
        valid, reason = validate_requirement(_req())
        self.assertTrue(valid, reason)

    def test_valid_test_method_with_event(self):
        valid, reason = validate_requirement(_req(method="T", annex_d_event="COGNITIVE_WORKLOAD"))
        self.assertTrue(valid, reason)

    def test_valid_analysis_requires_no_event(self):
        req = _req(method="A")
        req.pop("annex_d_event", None)
        valid, reason = validate_requirement(req)
        self.assertTrue(valid, reason)

    def test_valid_inspection_requires_no_event(self):
        req = _req(method="I")
        req.pop("annex_d_event", None)
        valid, reason = validate_requirement(req)
        self.assertTrue(valid, reason)

    def test_missing_req_id_fails(self):
        req = _req()
        del req["req_id"]
        valid, _ = validate_requirement(req)
        self.assertFalse(valid)

    def test_missing_description_fails(self):
        req = _req()
        del req["description"]
        valid, _ = validate_requirement(req)
        self.assertFalse(valid)

    def test_empty_description_fails(self):
        valid, _ = validate_requirement(_req(description=""))
        self.assertFalse(valid)

    def test_missing_annex_event_for_test_method_fails(self):
        req = _req(method="T")
        req.pop("annex_d_event", None)
        valid, reason = validate_requirement(req)
        self.assertFalse(valid)
        self.assertIn("annex_d_event", reason)

    def test_missing_annex_event_for_demonstration_fails(self):
        req = _req(method="D")
        req.pop("annex_d_event", None)
        valid, reason = validate_requirement(req)
        self.assertFalse(valid)

    def test_invalid_method_fails(self):
        valid, _ = validate_requirement(_req(method="Z"))
        self.assertFalse(valid)

    def test_invalid_annex_d_event_string_fails(self):
        valid, _ = validate_requirement(_req(method="T", annex_d_event="NONSENSE"))
        self.assertFalse(valid)

    def test_invalid_status_fails(self):
        valid, _ = validate_requirement(_req(status="UNKNOWN_STATUS"))
        self.assertFalse(valid)

    def test_pending_status_is_valid(self):
        valid, reason = validate_requirement(_req(status="PENDING"))
        self.assertTrue(valid, reason)

    def test_fail_status_is_valid(self):
        valid, reason = validate_requirement(_req(status="FAIL"))
        self.assertTrue(valid, reason)


# ---------------------------------------------------------------------------
# check_mandatory_event_coverage
# ---------------------------------------------------------------------------

class TestMandatoryEventCoverage(unittest.TestCase):

    def test_full_coverage_returns_empty(self):
        uncovered = check_mandatory_event_coverage(_full_coverage_reqs())
        self.assertEqual(uncovered, [])

    def test_empty_requirements_returns_all_mandatory(self):
        uncovered = check_mandatory_event_coverage([])
        self.assertEqual(len(uncovered), len(MANDATORY_ANNEX_D_EVENTS))

    def test_single_missing_event_detected(self):
        reqs = [r for r in _full_coverage_reqs() if r["annex_d_event"] != "EMERGENCY_PROCEDURE"]
        uncovered = check_mandatory_event_coverage(reqs)
        self.assertIn("EMERGENCY_PROCEDURE", uncovered)

    def test_analysis_method_does_not_count_as_coverage(self):
        reqs = [{
            "req_id": "R1",
            "description": "Ergonomic model analysis",
            "method": "A",
            "annex_d_event": "ERGONOMIC_ASSESSMENT",
            "status": "PASS",
        }]
        uncovered = check_mandatory_event_coverage(reqs)
        self.assertIn("ERGONOMIC_ASSESSMENT", uncovered)

    def test_inspection_method_does_not_count_as_coverage(self):
        reqs = [{
            "req_id": "R1",
            "description": "Cognitive inspection",
            "method": "I",
            "annex_d_event": "COGNITIVE_WORKLOAD",
            "status": "PASS",
        }]
        uncovered = check_mandatory_event_coverage(reqs)
        self.assertIn("COGNITIVE_WORKLOAD", uncovered)

    def test_non_mandatory_event_coverage_does_not_affect_mandatory(self):
        reqs = [_req(method="T", annex_d_event="LABEL_AND_CUE", status="PASS")]
        uncovered = check_mandatory_event_coverage(reqs)
        self.assertEqual(len(uncovered), len(MANDATORY_ANNEX_D_EVENTS))

    def test_result_is_sorted(self):
        uncovered = check_mandatory_event_coverage([])
        self.assertEqual(uncovered, sorted(uncovered))

    def test_duplicate_coverage_does_not_double_count(self):
        reqs = _full_coverage_reqs()
        reqs.append(_req(req_id="R6", method="T", annex_d_event="FUNCTIONAL_TASK", status="PASS"))
        uncovered = check_mandatory_event_coverage(reqs)
        self.assertEqual(uncovered, [])


# ---------------------------------------------------------------------------
# evaluate_test_readiness
# ---------------------------------------------------------------------------

class TestEvaluateTestReadiness(unittest.TestCase):

    def test_all_criteria_met_is_ready(self):
        criteria = [
            {"criterion_id": "RC-1", "description": "Procedures approved", "met": True},
            {"criterion_id": "RC-2", "description": "Fixture calibrated", "met": True},
        ]
        ready, unmet = evaluate_test_readiness(criteria)
        self.assertTrue(ready)
        self.assertEqual(unmet, [])

    def test_single_unmet_criterion_blocks_readiness(self):
        criteria = [
            {"criterion_id": "RC-1", "description": "Procedures approved", "met": True},
            {"criterion_id": "RC-2", "description": "Fixture calibrated", "met": False},
        ]
        ready, unmet = evaluate_test_readiness(criteria)
        self.assertFalse(ready)
        self.assertIn("RC-2", unmet)

    def test_all_unmet_returns_all_ids(self):
        criteria = [
            {"criterion_id": "RC-1", "description": "A", "met": False},
            {"criterion_id": "RC-2", "description": "B", "met": False},
        ]
        ready, unmet = evaluate_test_readiness(criteria)
        self.assertFalse(ready)
        self.assertEqual(set(unmet), {"RC-1", "RC-2"})

    def test_empty_criteria_list_is_ready(self):
        ready, unmet = evaluate_test_readiness([])
        self.assertTrue(ready)
        self.assertEqual(unmet, [])

    def test_missing_met_key_defaults_to_not_met(self):
        criteria = [{"criterion_id": "RC-1", "description": "No met key"}]
        ready, unmet = evaluate_test_readiness(criteria)
        self.assertFalse(ready)
        self.assertIn("RC-1", unmet)


# ---------------------------------------------------------------------------
# compute_compliance_summary
# ---------------------------------------------------------------------------

class TestComplianceSummary(unittest.TestCase):

    def test_all_pass_is_compliant(self):
        reqs = [_req(req_id="R1", status="PASS"), _req(req_id="R2", status="PASS")]
        summary = compute_compliance_summary(reqs)
        self.assertTrue(summary["compliant"])
        self.assertEqual(summary["pass"], 2)
        self.assertEqual(summary["fail"], 0)
        self.assertEqual(summary["pending"], 0)

    def test_one_fail_not_compliant(self):
        reqs = [_req(req_id="R1", status="PASS"), _req(req_id="R2", status="FAIL")]
        summary = compute_compliance_summary(reqs)
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["fail"], 1)

    def test_one_pending_not_compliant(self):
        reqs = [_req(req_id="R1", status="PENDING")]
        summary = compute_compliance_summary(reqs)
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["pending"], 1)

    def test_empty_list_not_compliant(self):
        summary = compute_compliance_summary([])
        self.assertFalse(summary["compliant"])
        self.assertEqual(summary["total"], 0)

    def test_totals_are_accurate(self):
        reqs = [
            _req(req_id="R1", status="PASS"),
            _req(req_id="R2", status="FAIL"),
            _req(req_id="R3", status="PENDING"),
        ]
        summary = compute_compliance_summary(reqs)
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["pass"], 1)
        self.assertEqual(summary["fail"], 1)
        self.assertEqual(summary["pending"], 1)
        self.assertFalse(summary["compliant"])


# ---------------------------------------------------------------------------
# aggregate_findings
# ---------------------------------------------------------------------------

class TestAggregateFindings(unittest.TestCase):

    def test_fully_compliant_set_has_no_structural_or_coverage_findings(self):
        findings = aggregate_findings(_full_coverage_reqs())
        structural = [f for f in findings if f.startswith("[INVALID]") or f.startswith("[COVERAGE]")]
        self.assertEqual(structural, [])

    def test_fail_status_generates_fail_finding(self):
        reqs = [_req(req_id="R1", status="FAIL")]
        findings = aggregate_findings(reqs)
        fail_findings = [f for f in findings if "[FAIL]" in f]
        self.assertTrue(len(fail_findings) > 0)
        self.assertIn("R1", fail_findings[0])

    def test_pending_status_generates_pending_finding(self):
        reqs = [_req(req_id="R1", status="PENDING")]
        findings = aggregate_findings(reqs)
        pending = [f for f in findings if "[PENDING]" in f]
        self.assertTrue(len(pending) > 0)

    def test_missing_annex_event_generates_invalid_finding(self):
        req = _req(method="T")
        req.pop("annex_d_event", None)
        findings = aggregate_findings([req])
        invalid = [f for f in findings if "[INVALID]" in f]
        self.assertTrue(len(invalid) > 0)

    def test_uncovered_mandatory_event_generates_coverage_finding(self):
        reqs = [_req(req_id="R1", method="T", annex_d_event="FUNCTIONAL_TASK", status="PASS")]
        findings = aggregate_findings(reqs)
        coverage = [f for f in findings if "[COVERAGE]" in f]
        self.assertTrue(len(coverage) > 0)

    def test_empty_requirements_returns_only_coverage_findings(self):
        findings = aggregate_findings([])
        invalid = [f for f in findings if "[INVALID]" in f]
        coverage = [f for f in findings if "[COVERAGE]" in f]
        self.assertEqual(invalid, [])
        self.assertEqual(len(coverage), len(MANDATORY_ANNEX_D_EVENTS))

    def test_mixed_issues_all_reported(self):
        reqs = [
            _req(req_id="R1", status="FAIL"),
            _req(req_id="R2", status="PENDING"),
            {"req_id": "R3", "description": "Bad req", "method": "Z", "status": "PASS"},
        ]
        findings = aggregate_findings(reqs)
        tags = {f.split("]")[0].lstrip("[") for f in findings}
        self.assertIn("FAIL", tags)
        self.assertIn("PENDING", tags)
        self.assertIn("INVALID", tags)


if __name__ == "__main__":
    unittest.main()

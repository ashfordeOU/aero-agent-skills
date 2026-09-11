"""
Offline stdlib unittest suite for e1011_assessment_process_logic.
Run: python3 test_e1011_assessment_process.py
Expected output: OK
"""

import unittest

from e1011_assessment_process_logic import (
    AssessmentError,
    AssessmentRecord,
    Finding,
    TechnicalPerformanceMeasure,
    check_finding_closure_valid,
    compute_overall_status,
    evaluate_measure_status,
    generate_annex_c_fields,
    validate_assessment_record,
    validate_finding_status,
    validate_finding_type,
)


# ---------------------------------------------------------------------------
# Finding type validation
# ---------------------------------------------------------------------------

class TestValidateFindingType(unittest.TestCase):

    def test_observation_accepted(self):
        self.assertEqual(validate_finding_type("observation"), "observation")

    def test_action_item_accepted(self):
        self.assertEqual(validate_finding_type("action_item"), "action_item")

    def test_non_conformance_accepted(self):
        self.assertEqual(validate_finding_type("non_conformance"), "non_conformance")

    def test_uppercase_normalised(self):
        self.assertEqual(validate_finding_type("OBSERVATION"), "observation")

    def test_mixed_case_normalised(self):
        self.assertEqual(validate_finding_type("Non_Conformance"), "non_conformance")

    def test_unknown_type_raises(self):
        with self.assertRaises(AssessmentError):
            validate_finding_type("defect")

    def test_empty_string_raises(self):
        with self.assertRaises(AssessmentError):
            validate_finding_type("")


# ---------------------------------------------------------------------------
# Finding status validation
# ---------------------------------------------------------------------------

class TestValidateFindingStatus(unittest.TestCase):

    def test_open_accepted(self):
        self.assertEqual(validate_finding_status("open"), "open")

    def test_closed_accepted(self):
        self.assertEqual(validate_finding_status("closed"), "closed")

    def test_waived_accepted(self):
        self.assertEqual(validate_finding_status("waived"), "waived")

    def test_unknown_status_raises(self):
        with self.assertRaises(AssessmentError):
            validate_finding_status("deferred")


# ---------------------------------------------------------------------------
# TPM evaluation
# ---------------------------------------------------------------------------

class TestEvaluateMeasureStatus(unittest.TestCase):

    def _make_measure(self, current, threshold, threshold_type, unit="kg"):
        return TechnicalPerformanceMeasure(
            measure_id="M1",
            name="Test measure",
            current_value=current,
            threshold_value=threshold,
            threshold_type=threshold_type,
            unit=unit,
        )

    def test_max_nominal_well_below(self):
        m = self._make_measure(50.0, 100.0, "max")
        self.assertEqual(evaluate_measure_status(m), "nominal")

    def test_max_marginal_near_threshold(self):
        # threshold=100, band=10; value=95 is within band => marginal
        m = self._make_measure(95.0, 100.0, "max")
        self.assertEqual(evaluate_measure_status(m), "marginal")

    def test_max_exceeded_above_threshold(self):
        m = self._make_measure(105.0, 100.0, "max")
        self.assertEqual(evaluate_measure_status(m), "exceeded")

    def test_max_exactly_at_threshold_is_marginal(self):
        # value == threshold => within band (band starts at threshold - band)
        m = self._make_measure(100.0, 100.0, "max")
        self.assertEqual(evaluate_measure_status(m), "marginal")

    def test_min_nominal_well_above(self):
        m = self._make_measure(150.0, 100.0, "min")
        self.assertEqual(evaluate_measure_status(m), "nominal")

    def test_min_marginal_near_threshold(self):
        # threshold=100, band=10; value=105 is within band => marginal
        m = self._make_measure(105.0, 100.0, "min")
        self.assertEqual(evaluate_measure_status(m), "marginal")

    def test_min_exceeded_below_threshold(self):
        m = self._make_measure(90.0, 100.0, "min")
        self.assertEqual(evaluate_measure_status(m), "exceeded")

    def test_invalid_threshold_type_raises(self):
        m = self._make_measure(50.0, 100.0, "average")
        with self.assertRaises(AssessmentError):
            evaluate_measure_status(m)


# ---------------------------------------------------------------------------
# Finding closure validity
# ---------------------------------------------------------------------------

class TestCheckFindingClosureValid(unittest.TestCase):

    def _make_finding(self, **kwargs):
        defaults = dict(
            finding_id="F-001",
            finding_type="action_item",
            description="Verify subsystem mass budget.",
            status="open",
            responsible="Systems Team",
            waiver_rationale=None,
        )
        defaults.update(kwargs)
        return Finding(**defaults)

    def test_complete_open_finding_is_valid(self):
        f = self._make_finding(status="open")
        ok, issues = check_finding_closure_valid(f)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_complete_closed_finding_is_valid(self):
        f = self._make_finding(status="closed")
        ok, issues = check_finding_closure_valid(f)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_waived_with_rationale_is_valid(self):
        f = self._make_finding(status="waived", waiver_rationale="Risk accepted by PM.")
        ok, issues = check_finding_closure_valid(f)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_waived_without_rationale_is_invalid(self):
        f = self._make_finding(status="waived", waiver_rationale=None)
        ok, issues = check_finding_closure_valid(f)
        self.assertFalse(ok)
        self.assertTrue(any("rationale" in i for i in issues))

    def test_empty_responsible_is_invalid(self):
        f = self._make_finding(responsible="")
        ok, issues = check_finding_closure_valid(f)
        self.assertFalse(ok)
        self.assertTrue(any("responsible" in i for i in issues))

    def test_empty_description_is_invalid(self):
        f = self._make_finding(description="")
        ok, issues = check_finding_closure_valid(f)
        self.assertFalse(ok)
        self.assertTrue(any("description" in i for i in issues))


# ---------------------------------------------------------------------------
# Overall status computation
# ---------------------------------------------------------------------------

class TestComputeOverallStatus(unittest.TestCase):

    def _finding(self, ftype, status):
        return Finding(
            finding_id="F-X",
            finding_type=ftype,
            description="desc",
            status=status,
            responsible="Team",
        )

    def test_open_non_conformance_yields_non_compliant(self):
        findings = [self._finding("non_conformance", "open")]
        result = compute_overall_status(findings, ["nominal"])
        self.assertEqual(result, "non_compliant")

    def test_exceeded_measure_yields_at_risk(self):
        findings = [self._finding("observation", "closed")]
        result = compute_overall_status(findings, ["exceeded"])
        self.assertEqual(result, "at_risk")

    def test_open_action_item_yields_at_risk(self):
        findings = [self._finding("action_item", "open")]
        result = compute_overall_status(findings, ["nominal"])
        self.assertEqual(result, "at_risk")

    def test_marginal_measure_yields_marginal(self):
        findings = [self._finding("observation", "closed")]
        result = compute_overall_status(findings, ["marginal"])
        self.assertEqual(result, "marginal")

    def test_all_clear_yields_compliant(self):
        findings = [self._finding("observation", "closed")]
        result = compute_overall_status(findings, ["nominal"])
        self.assertEqual(result, "compliant")

    def test_empty_findings_and_measures_yields_compliant(self):
        result = compute_overall_status([], [])
        self.assertEqual(result, "compliant")

    def test_non_compliant_takes_priority_over_exceeded(self):
        findings = [
            self._finding("non_conformance", "open"),
            self._finding("action_item", "open"),
        ]
        result = compute_overall_status(findings, ["exceeded"])
        self.assertEqual(result, "non_compliant")


# ---------------------------------------------------------------------------
# Annex C report generation
# ---------------------------------------------------------------------------

class TestGenerateAnnexCFields(unittest.TestCase):

    def _build_record(self):
        findings = [
            Finding("F-001", "non_conformance", "Mass budget exceeded.", "closed", "SE Team"),
            Finding("F-002", "action_item", "Update FMEA.", "open", "Safety Team"),
        ]
        measures = [
            TechnicalPerformanceMeasure("M1", "Total mass", 450.0, 500.0, "max", "kg"),
        ]
        return AssessmentRecord(
            record_id="AR-001",
            phase="phase_c",
            event_name="PDR",
            event_date="2026-06-01",
            scope_description="Preliminary design review assessment.",
            findings=findings,
            measures=measures,
        )

    def test_required_keys_present(self):
        record = self._build_record()
        fields = generate_annex_c_fields(record, ["nominal"])
        for key in (
            "record_id", "event_name", "event_date", "phase", "scope",
            "total_findings", "open_count", "closed_count", "waived_count",
            "open_finding_ids", "measure_statuses", "overall_status",
        ):
            self.assertIn(key, fields)

    def test_open_count_correct(self):
        record = self._build_record()
        fields = generate_annex_c_fields(record, ["nominal"])
        self.assertEqual(fields["open_count"], 1)

    def test_closed_count_correct(self):
        record = self._build_record()
        fields = generate_annex_c_fields(record, ["nominal"])
        self.assertEqual(fields["closed_count"], 1)

    def test_total_findings_correct(self):
        record = self._build_record()
        fields = generate_annex_c_fields(record, ["nominal"])
        self.assertEqual(fields["total_findings"], 2)

    def test_overall_status_at_risk_from_open_ai(self):
        record = self._build_record()
        fields = generate_annex_c_fields(record, ["nominal"])
        self.assertEqual(fields["overall_status"], "at_risk")

    def test_measure_status_recorded(self):
        record = self._build_record()
        fields = generate_annex_c_fields(record, ["marginal"])
        self.assertEqual(fields["measure_statuses"]["M1"], "marginal")

    def test_mismatched_measure_count_raises(self):
        record = self._build_record()
        with self.assertRaises(AssessmentError):
            generate_annex_c_fields(record, ["nominal", "exceeded"])


# ---------------------------------------------------------------------------
# Record-level validation
# ---------------------------------------------------------------------------

class TestValidateAssessmentRecord(unittest.TestCase):

    def _good_record(self):
        return AssessmentRecord(
            record_id="AR-002",
            phase="phase_b",
            event_name="SRR",
            event_date="2026-03-15",
            scope_description="System requirements review scope.",
        )

    def test_valid_record_returns_no_issues(self):
        record = self._good_record()
        self.assertEqual(validate_assessment_record(record), [])

    def test_empty_record_id_reported(self):
        record = self._good_record()
        record.record_id = ""
        issues = validate_assessment_record(record)
        self.assertTrue(any("record_id" in i for i in issues))

    def test_empty_event_name_reported(self):
        record = self._good_record()
        record.event_name = "   "
        issues = validate_assessment_record(record)
        self.assertTrue(any("event_name" in i for i in issues))

    def test_invalid_date_format_reported(self):
        record = self._good_record()
        record.event_date = "15-03-2026"
        issues = validate_assessment_record(record)
        self.assertTrue(any("event_date" in i for i in issues))

    def test_bad_finding_type_reported(self):
        record = self._good_record()
        record.findings = [
            Finding("F-X", "defect", "desc", "open", "Team")
        ]
        issues = validate_assessment_record(record)
        self.assertTrue(len(issues) > 0)

    def test_waived_finding_without_rationale_reported(self):
        record = self._good_record()
        record.findings = [
            Finding("F-Y", "observation", "desc", "waived", "Team", waiver_rationale=None)
        ]
        issues = validate_assessment_record(record)
        self.assertTrue(any("rationale" in i for i in issues))

    def test_bad_measure_threshold_type_reported(self):
        record = self._good_record()
        record.measures = [
            TechnicalPerformanceMeasure("M9", "Power", 200.0, 250.0, "average", "W")
        ]
        issues = validate_assessment_record(record)
        self.assertTrue(any("threshold_type" in i for i in issues))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract test for the electromagnetic effects verification report leaf."""

import unittest
from datetime import date

from e2007_electromagnetic_effects_verification_report_logic import (
    CRITICALITY_MARGIN_DB,
    DISPOSITIONS,
    EVIDENCE_PREFIX,
    RESULT_STATES,
    VERIFICATION_METHODS,
    assess_verification_report,
    check_traceability,
    compute_corrected_level_db,
    compute_margin_db,
    evaluate_entry,
    evidence_reference_valid,
    margin_verdict,
    normalize_criticality,
    normalize_disposition,
    normalize_method,
    normalize_result,
    parse_report_date,
    required_margin_db,
    summarize_campaign,
    validate_report_entry,
)


def good_entry(**overrides):
    entry = {
        "activity_id": "ACT-010",
        "requirement_id": "EMC-R-010",
        "method": "test",
        "result": "pass",
        "evidence_ref": "TR-2027-014",
        "report_date": "2027-02-11",
        "measurement": {
            "limit_dbuv": 46.0,
            "indicated_dbuv": 30.0,
            "corrections_db": [0.1, 0.2],
            "criticality": "safety-critical",
        },
    }
    entry.update(overrides)
    return entry


def analysis_entry(**overrides):
    entry = {
        "activity_id": "ACT-020",
        "requirement_id": "EMC-R-020",
        "method": "analysis",
        "result": "pass",
        "evidence_ref": "AN-2027-003",
        "report_date": "2027-02-18",
    }
    entry.update(overrides)
    return entry


def good_report(**overrides):
    report = {
        "planned_activities": ["ACT-010", "ACT-020"],
        "entries": [good_entry(), analysis_entry()],
    }
    report.update(overrides)
    return report


class TestNormalizers(unittest.TestCase):
    def test_method_canonical_token(self):
        self.assertEqual(normalize_method("TEST"), "test")

    def test_method_synonym_review_of_design(self):
        self.assertEqual(normalize_method("Review Of Design"), "review-of-design")

    def test_every_method_round_trips(self):
        for method in VERIFICATION_METHODS:
            self.assertEqual(normalize_method(method), method)

    def test_method_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_method("shock")

    def test_method_non_string_raises(self):
        with self.assertRaises(ValueError):
            normalize_method(None)

    def test_result_canonical_token(self):
        self.assertEqual(normalize_result("PASSED"), "pass")

    def test_result_deviation_synonym(self):
        self.assertEqual(
            normalize_result("pass with deviation"), "pass-with-deviation"
        )

    def test_result_not_run_synonym(self):
        self.assertEqual(normalize_result("open"), "not-run")

    def test_every_result_round_trips(self):
        for state in RESULT_STATES:
            self.assertEqual(normalize_result(state), state)

    def test_result_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_result("maybe")

    def test_result_blank_raises(self):
        with self.assertRaises(ValueError):
            normalize_result("  ")

    def test_criticality_canonical_token(self):
        self.assertEqual(
            normalize_criticality("Safety_Critical"), "safety-critical"
        )

    def test_criticality_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_criticality("nice-to-have")

    def test_disposition_canonical_token(self):
        self.assertEqual(normalize_disposition("Accept As Is"), "accept-as-is")

    def test_every_disposition_round_trips(self):
        for disposition in DISPOSITIONS:
            self.assertEqual(normalize_disposition(disposition), disposition)

    def test_disposition_unknown_raises(self):
        with self.assertRaises(ValueError):
            normalize_disposition("ignore")

    def test_parse_report_date_accepts_iso(self):
        self.assertEqual(parse_report_date("2027-02-11"), date(2027, 2, 11))

    def test_parse_report_date_accepts_date(self):
        self.assertEqual(parse_report_date(date(2027, 2, 11)), date(2027, 2, 11))

    def test_parse_report_date_rejects_text(self):
        with self.assertRaises(ValueError):
            parse_report_date("11 Feb 2027")


class TestLevelCorrection(unittest.TestCase):
    def test_no_correction_returns_reading(self):
        self.assertAlmostEqual(compute_corrected_level_db(30.0), 30.0)

    def test_positive_corrections_raise_the_level(self):
        self.assertAlmostEqual(
            compute_corrected_level_db(30.0, [12.5, 1.5]), 44.0
        )

    def test_negative_correction_lowers_the_level(self):
        self.assertAlmostEqual(
            compute_corrected_level_db(40.0, [2.0, -25.0]), 17.0
        )

    def test_integer_terms_are_accepted(self):
        self.assertAlmostEqual(compute_corrected_level_db(30, [2]), 32.0)

    def test_non_numeric_reading_raises(self):
        with self.assertRaises(ValueError):
            compute_corrected_level_db("30 dBuV")

    def test_boolean_reading_raises(self):
        with self.assertRaises(ValueError):
            compute_corrected_level_db(True)

    def test_non_finite_correction_raises(self):
        with self.assertRaises(ValueError):
            compute_corrected_level_db(30.0, [float("nan")])

    def test_string_corrections_raise(self):
        with self.assertRaises(ValueError):
            compute_corrected_level_db(30.0, "12.5")


class TestMargin(unittest.TestCase):
    def test_margin_is_limit_minus_corrected(self):
        self.assertAlmostEqual(compute_margin_db(46.0, 30.3), 15.7)

    def test_negative_margin_when_level_exceeds_limit(self):
        self.assertAlmostEqual(compute_margin_db(40.0, 44.0), -4.0)

    def test_margin_rejects_non_numeric_limit(self):
        with self.assertRaises(ValueError):
            compute_margin_db("40", 30.0)

    def test_required_margin_by_criticality(self):
        self.assertAlmostEqual(required_margin_db("standard"), 0.0)
        self.assertAlmostEqual(required_margin_db("mission-critical"), 3.0)
        self.assertAlmostEqual(required_margin_db("safety-critical"), 6.0)

    def test_criticality_table_is_monotonic(self):
        self.assertLess(
            CRITICALITY_MARGIN_DB["standard"],
            CRITICALITY_MARGIN_DB["mission-critical"],
        )
        self.assertLess(
            CRITICALITY_MARGIN_DB["mission-critical"],
            CRITICALITY_MARGIN_DB["safety-critical"],
        )

    def test_comfortable_margin_passes(self):
        self.assertEqual(margin_verdict(9.0, "safety-critical"), "pass")

    def test_short_margin_fails(self):
        self.assertEqual(margin_verdict(5.5, "safety-critical"), "fail")

    def test_zero_margin_passes_at_standard_criticality(self):
        self.assertEqual(margin_verdict(0.0, "standard"), "pass")

    def test_negative_margin_fails_at_standard_criticality(self):
        self.assertEqual(margin_verdict(-0.5, "standard"), "fail")

    def test_exactly_met_margin_survives_float_representation(self):
        corrected = compute_corrected_level_db(30.0, [0.1, 0.2])
        margin = compute_margin_db(36.3, corrected)
        # the summed decibel terms land a few ULPs short of the exact 6 dB
        self.assertLess(margin, 6.0)
        self.assertEqual(margin_verdict(margin, "safety-critical"), "pass")

    def test_genuine_shortfall_is_not_absorbed(self):
        corrected = compute_corrected_level_db(30.0, [0.1, 0.2])
        margin = compute_margin_db(36.29, corrected)
        self.assertEqual(margin_verdict(margin, "safety-critical"), "fail")

    def test_margin_verdict_rejects_unknown_criticality(self):
        with self.assertRaises(ValueError):
            margin_verdict(6.0, "critical")


class TestEvidenceReference(unittest.TestCase):
    def test_test_report_reference_accepted(self):
        self.assertTrue(evidence_reference_valid("test", "TR-2027-014"))

    def test_analysis_note_reference_accepted(self):
        self.assertTrue(evidence_reference_valid("analysis", "an-2027-003"))

    def test_wrong_family_reference_rejected(self):
        self.assertFalse(evidence_reference_valid("test", "AN-2027-003"))

    def test_blank_reference_rejected(self):
        self.assertFalse(evidence_reference_valid("test", "   "))

    def test_prefix_alone_is_rejected(self):
        self.assertFalse(evidence_reference_valid("test", "TR-"))

    def test_every_method_has_a_prefix(self):
        for method in VERIFICATION_METHODS:
            self.assertIn(method, EVIDENCE_PREFIX)

    def test_non_string_reference_raises(self):
        with self.assertRaises(ValueError):
            evidence_reference_valid("test", 2027)


class TestEntryValidation(unittest.TestCase):
    def test_valid_entry_is_normalized(self):
        record = validate_report_entry(good_entry())
        self.assertEqual(record["activity_id"], "act-010")
        self.assertEqual(record["result"], "pass")
        self.assertAlmostEqual(record["measurement"]["corrected_dbuv"], 30.3)

    def test_validation_is_idempotent(self):
        once = validate_report_entry(good_entry())
        twice = validate_report_entry(once)
        self.assertEqual(once["measurement"]["verdict"], twice["measurement"]["verdict"])
        self.assertEqual(once["activity_id"], twice["activity_id"])

    def test_missing_key_raises(self):
        entry = good_entry()
        del entry["result"]
        with self.assertRaises(ValueError):
            validate_report_entry(entry)

    def test_non_mapping_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_report_entry("ACT-010 pass")

    def test_measurement_without_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_report_entry(
                good_entry(measurement={"indicated_dbuv": 30.0})
            )

    def test_measurement_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_report_entry(good_entry(measurement=[46.0, 30.0]))

    def test_nonconformance_without_id_raises(self):
        with self.assertRaises(ValueError):
            validate_report_entry(
                good_entry(nonconformance={"disposition": "waiver"})
            )

    def test_nonconformance_bad_disposition_raises(self):
        with self.assertRaises(ValueError):
            validate_report_entry(
                good_entry(nonconformance={"id": "NCR-7", "disposition": "shrug"})
            )

    def test_non_string_evidence_raises(self):
        with self.assertRaises(ValueError):
            validate_report_entry(good_entry(evidence_ref=14))

    def test_absent_measurement_is_none(self):
        record = validate_report_entry(analysis_entry())
        self.assertIsNone(record["measurement"])

    def test_default_criticality_is_standard(self):
        record = validate_report_entry(
            good_entry(measurement={"limit_dbuv": 46.0, "indicated_dbuv": 30.0})
        )
        self.assertEqual(record["measurement"]["criticality"], "standard")


class TestEntryEvaluation(unittest.TestCase):
    def test_clean_measured_entry_has_no_finding(self):
        self.assertEqual(evaluate_entry(good_entry())["findings"], [])

    def test_clean_modelled_entry_has_no_finding(self):
        self.assertEqual(evaluate_entry(analysis_entry())["findings"], [])

    def test_not_run_entry_is_flagged(self):
        codes = [
            f["code"] for f in evaluate_entry(good_entry(result="not-run"))["findings"]
        ]
        self.assertIn("activity-not-executed", codes)

    def test_not_run_entry_is_not_also_flagged_for_evidence(self):
        codes = [
            f["code"]
            for f in evaluate_entry(
                good_entry(result="not-run", evidence_ref="")
            )["findings"]
        ]
        self.assertNotIn("evidence-reference-invalid", codes)

    def test_wrong_evidence_family_is_flagged(self):
        codes = [
            f["code"]
            for f in evaluate_entry(good_entry(evidence_ref="AN-2027-003"))["findings"]
        ]
        self.assertIn("evidence-reference-invalid", codes)

    def test_measured_entry_without_data_is_flagged(self):
        entry = good_entry()
        del entry["measurement"]
        codes = [f["code"] for f in evaluate_entry(entry)["findings"]]
        self.assertIn("measured-data-absent", codes)

    def test_modelled_entry_needs_no_measured_data(self):
        codes = [f["code"] for f in evaluate_entry(analysis_entry())["findings"]]
        self.assertNotIn("measured-data-absent", codes)

    def test_recorded_pass_against_short_margin_is_flagged(self):
        entry = good_entry(
            measurement={
                "limit_dbuv": 34.0,
                "indicated_dbuv": 30.0,
                "criticality": "safety-critical",
            }
        )
        codes = [f["code"] for f in evaluate_entry(entry)["findings"]]
        self.assertIn("result-contradicts-measured-margin", codes)

    def test_recorded_fail_against_good_margin_is_flagged(self):
        entry = good_entry(
            result="fail",
            nonconformance={"id": "NCR-7", "disposition": "waiver"},
        )
        codes = [f["code"] for f in evaluate_entry(entry)["findings"]]
        self.assertIn("result-contradicts-measured-margin", codes)

    def test_fail_without_nonconformance_is_flagged(self):
        entry = good_entry(
            result="fail",
            measurement={
                "limit_dbuv": 34.0,
                "indicated_dbuv": 30.0,
                "criticality": "safety-critical",
            },
        )
        codes = [f["code"] for f in evaluate_entry(entry)["findings"]]
        self.assertIn("nonconformance-missing", codes)

    def test_deviation_without_disposition_is_flagged(self):
        entry = good_entry(
            result="pass-with-deviation",
            nonconformance={"id": "NCR-9"},
        )
        codes = [f["code"] for f in evaluate_entry(entry)["findings"]]
        self.assertIn("nonconformance-undispositioned", codes)

    def test_deviation_with_disposition_is_clean(self):
        entry = good_entry(
            result="pass-with-deviation",
            nonconformance={"id": "NCR-9", "disposition": "waiver"},
        )
        self.assertEqual(evaluate_entry(entry)["findings"], [])

    def test_pass_may_carry_a_closed_nonconformance(self):
        entry = good_entry(
            nonconformance={"id": "NCR-3", "disposition": "retest-passed"}
        )
        self.assertEqual(evaluate_entry(entry)["findings"], [])


class TestTraceability(unittest.TestCase):
    def test_complete_campaign_is_traceable(self):
        report = good_report()
        trace = check_traceability(report["planned_activities"], report["entries"])
        self.assertEqual(trace["unreported_activities"], [])
        self.assertEqual(trace["unplanned_entries"], [])
        self.assertAlmostEqual(trace["completeness_fraction"], 1.0)

    def test_unreported_activity_is_listed(self):
        trace = check_traceability(["ACT-010", "ACT-020"], [good_entry()])
        self.assertEqual(trace["unreported_activities"], ["act-020"])
        self.assertAlmostEqual(trace["completeness_fraction"], 0.5)

    def test_unplanned_entry_is_listed(self):
        trace = check_traceability(["ACT-010"], [good_entry(), analysis_entry()])
        self.assertEqual(trace["unplanned_entries"], ["act-020"])

    def test_duplicate_planned_activity_raises(self):
        with self.assertRaises(ValueError):
            check_traceability(["ACT-010", "act-010"], [good_entry()])

    def test_duplicate_entry_raises(self):
        with self.assertRaises(ValueError):
            check_traceability(["ACT-010"], [good_entry(), good_entry()])

    def test_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            check_traceability([], [good_entry()])

    def test_string_plan_raises(self):
        with self.assertRaises(ValueError):
            check_traceability("ACT-010", [good_entry()])


class TestSummary(unittest.TestCase):
    def test_counts_every_state(self):
        summary = summarize_campaign(good_report()["entries"])
        self.assertEqual(summary["entry_count"], 2)
        self.assertEqual(summary["counts"]["pass"], 2)
        self.assertAlmostEqual(summary["pass_fraction"], 1.0)

    def test_open_count_includes_fail_and_not_run(self):
        entries = [
            good_entry(
                result="fail",
                nonconformance={"id": "NCR-7", "disposition": "rework"},
                measurement={
                    "limit_dbuv": 34.0,
                    "indicated_dbuv": 30.0,
                    "criticality": "safety-critical",
                },
            ),
            analysis_entry(result="not-run"),
        ]
        summary = summarize_campaign(entries)
        self.assertEqual(summary["open_count"], 2)
        self.assertAlmostEqual(summary["pass_fraction"], 0.0)

    def test_empty_campaign_raises(self):
        with self.assertRaises(ValueError):
            summarize_campaign([])


class TestReportAssessment(unittest.TestCase):
    def test_clean_report_closes_the_campaign(self):
        result = assess_verification_report(good_report())
        self.assertEqual(result["verdict"], "campaign-closed")
        self.assertTrue(result["closed"])
        self.assertEqual(result["findings"], [])

    def test_unreported_activity_keeps_the_campaign_open(self):
        report = good_report(entries=[good_entry()])
        result = assess_verification_report(report)
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("planned-activity-unreported", codes)
        self.assertFalse(result["closed"])

    def test_entry_outside_the_plan_is_flagged(self):
        report = good_report(planned_activities=["ACT-010"])
        codes = [f["code"] for f in assess_verification_report(report)["findings"]]
        self.assertIn("entry-outside-plan", codes)

    def test_open_failure_keeps_the_campaign_open(self):
        entries = [
            good_entry(
                result="fail",
                nonconformance={"id": "NCR-7", "disposition": "rework"},
                measurement={
                    "limit_dbuv": 34.0,
                    "indicated_dbuv": 30.0,
                    "criticality": "safety-critical",
                },
            ),
            analysis_entry(),
        ]
        result = assess_verification_report(good_report(entries=entries))
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["verdict"], "campaign-open")

    def test_deviation_alone_does_not_hold_the_campaign_open(self):
        entries = [
            good_entry(
                result="pass-with-deviation",
                nonconformance={"id": "NCR-9", "disposition": "waiver"},
            ),
            analysis_entry(),
        ]
        result = assess_verification_report(good_report(entries=entries))
        self.assertTrue(result["closed"])

    def test_report_missing_key_raises(self):
        report = good_report()
        del report["entries"]
        with self.assertRaises(ValueError):
            assess_verification_report(report)

    def test_report_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_verification_report([good_report()])

    def test_report_without_entries_raises(self):
        with self.assertRaises(ValueError):
            assess_verification_report(good_report(entries=[]))

    def test_findings_carry_code_subject_and_detail(self):
        report = good_report(entries=[good_entry(evidence_ref="AN-1")])
        for finding in assess_verification_report(report)["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])

    def test_traceability_block_is_returned(self):
        result = assess_verification_report(good_report())
        self.assertEqual(result["traceability"]["planned_count"], 2)
        self.assertEqual(result["summary"]["entry_count"], 2)


if __name__ == "__main__":
    unittest.main()

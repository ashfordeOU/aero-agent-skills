"""Contract test for the ECSS-E-ST-20-01C clause 8.7 report-content audit."""

import math
import unittest

from e2001_multipactor_test_report_logic import (
    DEFAULT_REQUIRED_MARGIN_DB,
    OUTCOME_EVENT_ABOVE_MARGIN,
    OUTCOME_EVENT_BELOW_MARGIN,
    OUTCOME_MARGIN_DEMONSTRATED,
    OUTCOME_MARGIN_NOT_DEMONSTRATED,
    REQUIRED_SECTIONS,
    assess_test_report,
    audit_report_sections,
    categorize_test_outcome,
    check_evidence_completeness,
    check_nonconformance_dispositions,
    check_procedure_traceability,
    compute_achieved_margin_db,
)

APPROVED_ID = "MPT-PROC-0042"


def good_report(**overrides):
    report = {
        "sections": list(REQUIRED_SECTIONS),
        "procedure_id": APPROVED_ID,
        "operating_power_w": 100.0,
        "max_applied_power_w": 250.0,
        "threshold_power_w": None,
        "required_margin_db": 3.0,
        "deviations": [],
        "credited_methods": ["third-harmonic-monitoring", "electron-probe"],
        "recorded_traces": ["third-harmonic-monitoring", "electron-probe"],
        "nonconformances": [],
    }
    report.update(overrides)
    return report


class AchievedMarginTests(unittest.TestCase):
    def test_doubling_the_power_is_about_three_db(self):
        self.assertAlmostEqual(compute_achieved_margin_db(100.0, 200.0), 3.0102999566, places=9)

    def test_equal_powers_give_zero_margin(self):
        self.assertAlmostEqual(compute_achieved_margin_db(75.0, 75.0), 0.0, places=12)

    def test_four_times_the_power_is_about_six_db(self):
        self.assertAlmostEqual(compute_achieved_margin_db(50.0, 200.0), 6.0205999133, places=9)

    def test_power_below_operating_gives_a_negative_margin(self):
        self.assertLess(compute_achieved_margin_db(100.0, 50.0), 0.0)

    def test_zero_operating_power_raises(self):
        with self.assertRaises(ValueError):
            compute_achieved_margin_db(0.0, 200.0)

    def test_negative_observed_power_raises(self):
        with self.assertRaises(ValueError):
            compute_achieved_margin_db(100.0, -5.0)

    def test_non_numeric_power_raises(self):
        with self.assertRaises(ValueError):
            compute_achieved_margin_db(100.0, "200")

    def test_boolean_power_raises(self):
        with self.assertRaises(ValueError):
            compute_achieved_margin_db(True, 200.0)


class OutcomeCategorizationTests(unittest.TestCase):
    def test_clean_run_above_margin_demonstrates_the_margin(self):
        result = categorize_test_outcome(100.0, 250.0, None, 3.0)
        self.assertEqual(result["outcome"], OUTCOME_MARGIN_DEMONSTRATED)
        self.assertTrue(result["compliant"])
        self.assertTrue(result["margin_is_lower_bound"])

    def test_clean_run_short_of_margin_does_not_demonstrate_it(self):
        result = categorize_test_outcome(100.0, 150.0, None, 3.0)
        self.assertEqual(result["outcome"], OUTCOME_MARGIN_NOT_DEMONSTRATED)
        self.assertFalse(result["compliant"])

    def test_event_above_the_required_margin_is_compliant(self):
        result = categorize_test_outcome(100.0, 400.0, 300.0, 3.0)
        self.assertEqual(result["outcome"], OUTCOME_EVENT_ABOVE_MARGIN)
        self.assertTrue(result["compliant"])
        self.assertTrue(result["event_detected"])
        self.assertFalse(result["margin_is_lower_bound"])

    def test_event_below_the_required_margin_fails(self):
        result = categorize_test_outcome(100.0, 400.0, 120.0, 3.0)
        self.assertEqual(result["outcome"], OUTCOME_EVENT_BELOW_MARGIN)
        self.assertFalse(result["compliant"])

    def test_threshold_exactly_at_the_required_power_is_compliant(self):
        exact = 100.0 * 10.0 ** 0.3
        result = categorize_test_outcome(100.0, 400.0, exact, 3.0)
        self.assertTrue(result["compliant"])

    def test_threshold_one_ulp_under_the_required_power_is_absorbed(self):
        exact = 100.0 * 10.0 ** 0.3
        result = categorize_test_outcome(100.0, 400.0, math.nextafter(exact, 0.0), 3.0)
        self.assertTrue(result["compliant"])

    def test_threshold_clearly_under_the_required_power_still_fails(self):
        exact = 100.0 * 10.0 ** 0.3
        result = categorize_test_outcome(100.0, 400.0, exact * 0.99, 3.0)
        self.assertFalse(result["compliant"])

    def test_threshold_at_the_top_applied_level_is_allowed(self):
        result = categorize_test_outcome(100.0, 250.0, 250.0, 3.0)
        self.assertTrue(result["event_detected"])

    def test_threshold_above_the_top_applied_level_raises(self):
        with self.assertRaises(ValueError):
            categorize_test_outcome(100.0, 250.0, 300.0, 3.0)

    def test_negative_required_margin_raises(self):
        with self.assertRaises(ValueError):
            categorize_test_outcome(100.0, 250.0, None, -1.0)

    def test_zero_applied_power_raises(self):
        with self.assertRaises(ValueError):
            categorize_test_outcome(100.0, 0.0, None, 3.0)

    def test_demonstrated_margin_is_reported_for_a_clean_run(self):
        result = categorize_test_outcome(100.0, 200.0, None, 3.0)
        self.assertAlmostEqual(result["demonstrated_margin_db"], 3.0102999566, places=9)


class SectionAuditTests(unittest.TestCase):
    def test_full_section_list_is_complete(self):
        result = audit_report_sections(list(REQUIRED_SECTIONS))
        self.assertTrue(result["complete"])

    def test_missing_approval_block_is_reported(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "customer-approval-block"]
        result = audit_report_sections(sections)
        self.assertFalse(result["complete"])
        self.assertIn("customer-approval-block", result["missing"])

    def test_missing_threshold_determination_is_reported(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "threshold-determination"]
        result = audit_report_sections(sections)
        self.assertIn("threshold-determination", result["missing"])

    def test_duplicate_section_is_counted_once(self):
        result = audit_report_sections(list(REQUIRED_SECTIONS) + ["achieved-margin"])
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["present"]), len(REQUIRED_SECTIONS))

    def test_extra_annex_is_listed_not_faulted(self):
        result = audit_report_sections(list(REQUIRED_SECTIONS) + ["annex-raw-data"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["extra"], ["annex-raw-data"])

    def test_empty_section_list_reports_every_item_missing(self):
        result = audit_report_sections([])
        self.assertEqual(len(result["missing"]), len(REQUIRED_SECTIONS))

    def test_blank_section_name_raises(self):
        with self.assertRaises(ValueError):
            audit_report_sections(["achieved-margin", ""])

    def test_non_list_sections_raises(self):
        with self.assertRaises(ValueError):
            audit_report_sections({"a": 1})


class TraceabilityTests(unittest.TestCase):
    def test_matching_identifier_with_no_deviation_is_traceable(self):
        result = check_procedure_traceability(APPROVED_ID, APPROVED_ID, [])
        self.assertTrue(result["traceable"])

    def test_identifier_match_ignores_case(self):
        result = check_procedure_traceability(APPROVED_ID.lower(), APPROVED_ID, [])
        self.assertTrue(result["traceable"])

    def test_mismatched_identifier_is_flagged(self):
        result = check_procedure_traceability("MPT-PROC-0099", APPROVED_ID, [])
        self.assertFalse(result["traceable"])
        self.assertTrue(any("approved procedure" in f for f in result["findings"]))

    def test_waived_deviation_stays_traceable(self):
        deviations = [{"id": "DEV-1", "waiver_reference": "WVR-7"}]
        result = check_procedure_traceability(APPROVED_ID, APPROVED_ID, deviations)
        self.assertTrue(result["traceable"])
        self.assertEqual(result["deviation_count"], 1)

    def test_unwaived_deviation_is_flagged(self):
        deviations = [{"id": "DEV-2"}]
        result = check_procedure_traceability(APPROVED_ID, APPROVED_ID, deviations)
        self.assertFalse(result["traceable"])
        self.assertEqual(result["unwaived_deviations"], ["DEV-2"])

    def test_blank_waiver_reference_counts_as_unwaived(self):
        deviations = [{"id": "DEV-3", "waiver_reference": "   "}]
        result = check_procedure_traceability(APPROVED_ID, APPROVED_ID, deviations)
        self.assertEqual(result["unwaived_deviations"], ["DEV-3"])

    def test_deviation_without_an_id_raises(self):
        with self.assertRaises(ValueError):
            check_procedure_traceability(APPROVED_ID, APPROVED_ID, [{"waiver_reference": "W"}])

    def test_non_mapping_deviation_raises(self):
        with self.assertRaises(ValueError):
            check_procedure_traceability(APPROVED_ID, APPROVED_ID, ["DEV-4"])

    def test_empty_reported_identifier_raises(self):
        with self.assertRaises(ValueError):
            check_procedure_traceability("", APPROVED_ID, [])

    def test_non_list_deviations_raises(self):
        with self.assertRaises(ValueError):
            check_procedure_traceability(APPROVED_ID, APPROVED_ID, "DEV-5")


class EvidenceCompletenessTests(unittest.TestCase):
    def test_two_credited_techniques_with_traces_are_complete(self):
        result = check_evidence_completeness(
            ["third-harmonic-monitoring", "electron-probe"],
            ["third-harmonic-monitoring", "electron-probe"],
        )
        self.assertTrue(result["complete"])

    def test_credited_technique_without_a_trace_is_flagged(self):
        result = check_evidence_completeness(
            ["third-harmonic-monitoring", "electron-probe"], ["electron-probe"]
        )
        self.assertFalse(result["complete"])
        self.assertEqual(result["untraced"], ["third-harmonic-monitoring"])

    def test_surplus_trace_is_recorded_not_faulted(self):
        result = check_evidence_completeness(
            ["third-harmonic-monitoring", "electron-probe"],
            ["third-harmonic-monitoring", "electron-probe", "local-pressure-rise"],
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["surplus_traces"], ["local-pressure-rise"])

    def test_single_credited_technique_is_flagged(self):
        result = check_evidence_completeness(["electron-probe"], ["electron-probe"])
        self.assertFalse(result["complete"])
        self.assertTrue(
            any("fewer than two" in f for f in result["findings"])
        )

    def test_trace_matching_ignores_case_and_padding(self):
        result = check_evidence_completeness(
            ["Third-Harmonic-Monitoring", "electron-probe"],
            [" third-harmonic-monitoring ", "ELECTRON-PROBE"],
        )
        self.assertTrue(result["complete"])

    def test_no_traces_at_all_flags_every_credited_technique(self):
        result = check_evidence_completeness(
            ["third-harmonic-monitoring", "electron-probe"], []
        )
        self.assertEqual(len(result["untraced"]), 2)

    def test_empty_credited_list_raises(self):
        with self.assertRaises(ValueError):
            check_evidence_completeness([], ["electron-probe"])

    def test_blank_trace_name_raises(self):
        with self.assertRaises(ValueError):
            check_evidence_completeness(["electron-probe"], [""])


class NonConformanceTests(unittest.TestCase):
    def test_no_non_conformance_is_closed_out(self):
        result = check_nonconformance_dispositions([])
        self.assertTrue(result["closed_out"])
        self.assertEqual(result["raised"], 0)

    def test_disposed_item_is_closed_out(self):
        result = check_nonconformance_dispositions([{"id": "NCR-1", "disposition": "rework"}])
        self.assertTrue(result["closed_out"])
        self.assertEqual(result["dispositions"]["NCR-1"], "rework")

    def test_item_without_a_disposition_stays_open(self):
        result = check_nonconformance_dispositions([{"id": "NCR-2", "disposition": None}])
        self.assertFalse(result["closed_out"])
        self.assertEqual(result["open_items"], ["NCR-2"])

    def test_missing_disposition_key_stays_open(self):
        result = check_nonconformance_dispositions([{"id": "NCR-3"}])
        self.assertEqual(result["open_items"], ["NCR-3"])

    def test_disposition_matching_ignores_case(self):
        result = check_nonconformance_dispositions([{"id": "NCR-4", "disposition": "Use-As-Is"}])
        self.assertEqual(result["dispositions"]["NCR-4"], "use-as-is")

    def test_mixed_open_and_closed_items_are_separated(self):
        result = check_nonconformance_dispositions(
            [{"id": "NCR-5", "disposition": "retest"}, {"id": "NCR-6"}]
        )
        self.assertEqual(result["raised"], 2)
        self.assertEqual(result["open_items"], ["NCR-6"])

    def test_unrecognized_disposition_raises(self):
        with self.assertRaises(ValueError):
            check_nonconformance_dispositions([{"id": "NCR-7", "disposition": "ignore-it"}])

    def test_item_without_an_id_raises(self):
        with self.assertRaises(ValueError):
            check_nonconformance_dispositions([{"disposition": "repair"}])

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            check_nonconformance_dispositions(["NCR-8"])

    def test_non_list_argument_raises(self):
        with self.assertRaises(ValueError):
            check_nonconformance_dispositions("NCR-9")


class ReportAssessmentTests(unittest.TestCase):
    def test_complete_clean_report_is_approvable(self):
        result = assess_test_report(good_report(), APPROVED_ID)
        self.assertTrue(result["approvable"])
        self.assertEqual(result["findings"], [])

    def test_default_required_margin_is_three_db(self):
        self.assertAlmostEqual(DEFAULT_REQUIRED_MARGIN_DB, 3.0, places=12)

    def test_report_citing_the_wrong_procedure_is_not_approvable(self):
        result = assess_test_report(good_report(procedure_id="MPT-PROC-0001"), APPROVED_ID)
        self.assertFalse(result["approvable"])

    def test_report_with_an_open_non_conformance_is_not_approvable(self):
        result = assess_test_report(good_report(nonconformances=[{"id": "NCR-10"}]), APPROVED_ID)
        self.assertFalse(result["approvable"])
        self.assertTrue(any("left open" in f for f in result["findings"]))

    def test_report_short_of_margin_is_not_approvable(self):
        result = assess_test_report(good_report(max_applied_power_w=120.0), APPROVED_ID)
        self.assertFalse(result["approvable"])
        self.assertEqual(result["outcome"]["outcome"], OUTCOME_MARGIN_NOT_DEMONSTRATED)

    def test_report_with_an_event_under_margin_is_not_approvable(self):
        result = assess_test_report(good_report(threshold_power_w=110.0), APPROVED_ID)
        self.assertFalse(result["approvable"])
        self.assertEqual(result["outcome"]["outcome"], OUTCOME_EVENT_BELOW_MARGIN)

    def test_report_with_an_event_above_margin_is_approvable(self):
        result = assess_test_report(
            good_report(max_applied_power_w=400.0, threshold_power_w=320.0), APPROVED_ID
        )
        self.assertTrue(result["approvable"])
        self.assertEqual(result["outcome"]["outcome"], OUTCOME_EVENT_ABOVE_MARGIN)

    def test_report_missing_a_trace_is_not_approvable(self):
        result = assess_test_report(
            good_report(recorded_traces=["electron-probe"]), APPROVED_ID
        )
        self.assertFalse(result["approvable"])

    def test_report_missing_a_section_is_not_approvable(self):
        sections = [s for s in REQUIRED_SECTIONS if s != "deviation-record"]
        result = assess_test_report(good_report(sections=sections), APPROVED_ID)
        self.assertTrue(any("missing report content" in f for f in result["findings"]))

    def test_several_defects_accumulate_findings(self):
        result = assess_test_report(
            good_report(
                procedure_id="MPT-PROC-0002",
                deviations=[{"id": "DEV-9"}],
                nonconformances=[{"id": "NCR-11"}],
                max_applied_power_w=110.0,
            ),
            APPROVED_ID,
        )
        self.assertGreaterEqual(len(result["findings"]), 4)

    def test_report_missing_a_required_key_raises(self):
        report = good_report()
        del report["procedure_id"]
        with self.assertRaises(ValueError):
            assess_test_report(report, APPROVED_ID)

    def test_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            assess_test_report(["sections"], APPROVED_ID)


if __name__ == "__main__":
    unittest.main()

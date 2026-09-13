#!/usr/bin/env python3
"""Gate 3 contract test for the clause 6.4.1 plan-and-report leaf.

stdlib unittest, offline, deterministic. Run:
python3 test_e20_emc_verification_plan_and_report.py
"""

import datetime
import unittest

from e20_emc_verification_plan_and_report_logic import (
    PLAN_SECTIONS,
    REPORT_SECTIONS,
    build_activity_index,
    build_entry_list,
    closure_review,
    coverage_percent,
    governing_entry,
    meets_coverage_target,
    missing_document_sections,
    normalise_plan_activity,
    normalise_report_entry,
    review_verification_documents,
    schedule_findings,
    trace_activities,
)


def activity(ident, share=50.0, method="measurement", day="2026-03-02", req=None):
    return {
        "id": ident,
        "requirement": req or ("REQ-" + ident),
        "method": method,
        "share_percent": share,
        "planned_day": day,
    }


def entry(ident, act, result="compliant", day="2026-03-10", **extra):
    record = {"id": ident, "activity": act, "result": result, "executed_day": day}
    record.update(extra)
    return record


def good_plan():
    return {
        "sections": list(PLAN_SECTIONS),
        "issue_day": "2026-01-05",
        "minimum_lead_days": 30,
        "activities": [
            activity("CE01", share=33.4),
            activity("RE02", share=33.3),
            activity("RS03", share=33.3, method="analysis"),
        ],
    }


def good_report():
    return {
        "sections": list(REPORT_SECTIONS),
        "issue_day": "2026-04-01",
        "data_package_day": "2026-04-15",
        "entries": [
            entry("R-1", "CE01", day="2026-03-10"),
            entry("R-2", "RE02", day="2026-03-11"),
            entry("R-3", "RS03", day="2026-03-12"),
        ],
    }


class PlanActivityNormalisation(unittest.TestCase):
    def test_activity_is_canonicalised(self):
        act = normalise_plan_activity(activity(" CE01 "))
        self.assertEqual(act["id"], "CE01")
        self.assertEqual(act["method"], "measurement")
        self.assertEqual(act["planned_day"], datetime.date(2026, 3, 2))

    def test_share_is_a_float(self):
        act = normalise_plan_activity(activity("CE01", share=25))
        self.assertAlmostEqual(act["share_percent"], 25.0, places=9)

    def test_non_mapping_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(["CE01"])

    def test_empty_activity_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(activity("   "))

    def test_activity_without_requirement_is_rejected(self):
        rec = activity("CE01")
        rec["requirement"] = "  "
        with self.assertRaises(ValueError):
            normalise_plan_activity(rec)

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(activity("CE01", method="hand-waving"))

    def test_share_above_one_hundred_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(activity("CE01", share=120.0))

    def test_negative_share_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(activity("CE01", share=-1.0))

    def test_boolean_share_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(activity("CE01", share=True))

    def test_malformed_planned_day_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_plan_activity(activity("CE01", day="02-03-2026"))

    def test_duplicate_activity_id_is_rejected(self):
        with self.assertRaises(ValueError):
            build_activity_index([activity("CE01"), activity("CE01")])

    def test_empty_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            build_activity_index([])

    def test_missing_activity_list_is_rejected(self):
        with self.assertRaises(ValueError):
            build_activity_index(None)


class ReportEntryNormalisation(unittest.TestCase):
    def test_entry_is_canonicalised(self):
        rec = normalise_report_entry(entry("R-1", "CE01", deviation="DEV-7"))
        self.assertEqual(rec["deviation"], "DEV-7")
        self.assertIsNone(rec["retest_of"])

    def test_unknown_result_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_report_entry(entry("R-1", "CE01", result="probably-fine"))

    def test_entry_without_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_report_entry(entry("R-1", "  "))

    def test_empty_entry_id_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_report_entry(entry("", "CE01"))

    def test_empty_deviation_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_report_entry(entry("R-1", "CE01", deviation="   "))

    def test_self_referential_repeat_is_rejected(self):
        with self.assertRaises(ValueError):
            normalise_report_entry(entry("R-1", "CE01", retest_of="R-1"))

    def test_duplicate_entry_id_is_rejected(self):
        with self.assertRaises(ValueError):
            build_entry_list([entry("R-1", "CE01"), entry("R-1", "RE02")])

    def test_empty_report_is_rejected(self):
        with self.assertRaises(ValueError):
            build_entry_list([])


class DocumentSections(unittest.TestCase):
    def test_complete_plan_has_no_gap(self):
        self.assertEqual(missing_document_sections(list(PLAN_SECTIONS), "plan"), [])

    def test_plan_gap_is_listed_in_required_order(self):
        declared = [s for s in PLAN_SECTIONS if s not in ("verification-matrix", "pass-fail-criteria")]
        self.assertEqual(
            missing_document_sections(declared, "plan"),
            ["verification-matrix", "pass-fail-criteria"],
        )

    def test_report_section_set_is_distinct_from_the_plan_set(self):
        gaps = missing_document_sections(list(PLAN_SECTIONS), "report")
        self.assertEqual(gaps, list(REPORT_SECTIONS))

    def test_section_names_are_case_insensitive(self):
        declared = [s.upper() for s in REPORT_SECTIONS]
        self.assertEqual(missing_document_sections(declared, "report"), [])

    def test_unknown_document_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_document_sections(list(PLAN_SECTIONS), "annex")

    def test_empty_section_name_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_document_sections(list(PLAN_SECTIONS) + ["  "], "plan")

    def test_missing_section_list_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_document_sections(None, "plan")


class Traceability(unittest.TestCase):
    def test_full_pairing_leaves_no_gap(self):
        index = build_activity_index(good_plan()["activities"])
        entries = build_entry_list(good_report()["entries"])
        trace = trace_activities(index, entries)
        self.assertEqual(trace["untraced"], [])
        self.assertEqual(trace["orphan"], [])

    def test_planned_activity_with_no_entry_is_untraced(self):
        index = build_activity_index(good_plan()["activities"])
        entries = build_entry_list([entry("R-1", "CE01"), entry("R-2", "RE02")])
        trace = trace_activities(index, entries)
        self.assertEqual(trace["untraced"], ["RS03"])

    def test_entry_with_no_plan_activity_is_an_orphan(self):
        index = build_activity_index(good_plan()["activities"])
        entries = build_entry_list(good_report()["entries"] + [entry("R-9", "CS99")])
        trace = trace_activities(index, entries)
        self.assertEqual(trace["orphan"], ["R-9"])


class ClosureLogic(unittest.TestCase):
    def test_governing_entry_is_the_latest_execution(self):
        entries = build_entry_list(
            [
                entry("R-1", "CE01", result="non-compliant", day="2026-03-10"),
                entry("R-2", "CE01", day="2026-03-20", retest_of="R-1"),
            ]
        )
        self.assertEqual(governing_entry(entries)["id"], "R-2")

    def test_governing_entry_ties_break_on_identifier(self):
        entries = build_entry_list(
            [entry("R-1", "CE01", day="2026-03-10"), entry("R-2", "CE01", day="2026-03-10")]
        )
        self.assertEqual(governing_entry(entries)["id"], "R-2")

    def test_governing_entry_of_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            governing_entry([])

    def test_repeat_closes_an_earlier_non_compliant_activity(self):
        index = build_activity_index([activity("CE01")])
        entries = build_entry_list(
            [
                entry("R-1", "CE01", result="non-compliant", day="2026-03-10"),
                entry("R-2", "CE01", day="2026-03-20", retest_of="R-1"),
            ]
        )
        trace = trace_activities(index, entries)
        review = closure_review(index, trace["reported"], set(e["id"] for e in entries))
        self.assertEqual(review["closed"], ["CE01"])
        self.assertEqual(review["findings"], [])

    def test_unrepeated_non_compliant_activity_is_a_finding(self):
        index = build_activity_index([activity("CE01")])
        entries = build_entry_list([entry("R-1", "CE01", result="non-compliant")])
        trace = trace_activities(index, entries)
        review = closure_review(index, trace["reported"], set(e["id"] for e in entries))
        self.assertEqual(review["closed"], [])
        self.assertEqual(len(review["findings"]), 1)

    def test_acceptance_with_deviation_needs_a_deviation_record(self):
        index = build_activity_index([activity("CE01")])
        entries = build_entry_list(
            [entry("R-1", "CE01", result="compliant-with-deviation")]
        )
        trace = trace_activities(index, entries)
        review = closure_review(index, trace["reported"], set(e["id"] for e in entries))
        self.assertEqual(review["closed"], [])
        self.assertIn("deviation record", review["findings"][0])

    def test_acceptance_with_a_named_deviation_closes(self):
        index = build_activity_index([activity("CE01")])
        entries = build_entry_list(
            [entry("R-1", "CE01", result="compliant-with-deviation", deviation="DEV-4")]
        )
        trace = trace_activities(index, entries)
        review = closure_review(index, trace["reported"], set(e["id"] for e in entries))
        self.assertEqual(review["closed"], ["CE01"])
        self.assertEqual(review["findings"], [])

    def test_repeat_of_an_unknown_entry_is_a_finding(self):
        index = build_activity_index([activity("CE01")])
        entries = build_entry_list([entry("R-2", "CE01", retest_of="R-0")])
        trace = trace_activities(index, entries)
        review = closure_review(index, trace["reported"], set(e["id"] for e in entries))
        self.assertEqual(len(review["findings"]), 1)


class Coverage(unittest.TestCase):
    def test_share_sum_is_accumulated(self):
        index = build_activity_index(good_plan()["activities"])
        self.assertAlmostEqual(
            coverage_percent(index, ["CE01", "RE02"]), 66.7, places=9
        )

    def test_closed_activity_outside_the_plan_is_rejected(self):
        index = build_activity_index(good_plan()["activities"])
        with self.assertRaises(ValueError):
            coverage_percent(index, ["CS99"])

    def test_decimal_share_sum_just_under_the_target_still_meets_it(self):
        index = build_activity_index(good_plan()["activities"])
        total = coverage_percent(index, ["CE01", "RE02", "RS03"])
        self.assertLess(total, 100.0)
        self.assertTrue(meets_coverage_target(total, 100.0))

    def test_a_genuine_shortfall_does_not_meet_the_target(self):
        self.assertFalse(meets_coverage_target(66.7, 100.0))

    def test_surplus_coverage_meets_the_target(self):
        self.assertTrue(meets_coverage_target(100.0, 95.0))

    def test_non_numeric_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            meets_coverage_target("most of it", 100.0)

    def test_target_outside_the_percentage_range_is_rejected(self):
        with self.assertRaises(ValueError):
            meets_coverage_target(100.0, 101.0)


class Schedule(unittest.TestCase):
    def setUp(self):
        self.entries = build_entry_list(good_report()["entries"])

    def test_ordered_dates_raise_no_finding(self):
        self.assertEqual(
            schedule_findings("2026-01-05", "2026-04-01", self.entries, "2026-04-15", 30),
            [],
        )

    def test_plan_issued_after_the_campaign_is_a_finding(self):
        findings = schedule_findings(
            "2026-03-11", "2026-04-01", self.entries, "2026-04-15", 0
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("after the first activity", findings[0])

    def test_short_plan_lead_is_a_finding(self):
        findings = schedule_findings(
            "2026-03-01", "2026-04-01", self.entries, "2026-04-15", 30
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("day(s) before the first activity", findings[0])

    def test_exact_plan_lead_is_accepted(self):
        findings = schedule_findings(
            "2026-02-08", "2026-04-01", self.entries, "2026-04-15", 30
        )
        self.assertEqual(findings, [])

    def test_report_issued_before_the_last_activity_is_a_finding(self):
        findings = schedule_findings(
            "2026-01-05", "2026-03-11", self.entries, "2026-04-15", 30
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("before the last activity", findings[0])

    def test_report_issued_after_the_data_package_date_is_a_finding(self):
        findings = schedule_findings(
            "2026-01-05", "2026-04-20", self.entries, "2026-04-15", 30
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("data-package", findings[0])

    def test_negative_lead_demand_is_rejected(self):
        with self.assertRaises(ValueError):
            schedule_findings("2026-01-05", "2026-04-01", self.entries, "2026-04-15", -1)

    def test_fractional_lead_demand_is_rejected(self):
        with self.assertRaises(ValueError):
            schedule_findings("2026-01-05", "2026-04-01", self.entries, "2026-04-15", 2.5)

    def test_malformed_issue_date_is_rejected(self):
        with self.assertRaises(ValueError):
            schedule_findings("05/01/2026", "2026-04-01", self.entries, "2026-04-15", 0)

    def test_no_entry_to_place_is_rejected(self):
        with self.assertRaises(ValueError):
            schedule_findings("2026-01-05", "2026-04-01", [], "2026-04-15", 0)


class AggregateReview(unittest.TestCase):
    def test_a_complete_pair_is_compliant(self):
        review = review_verification_documents(good_plan(), good_report(), 100.0)
        self.assertTrue(review["compliant"])
        self.assertEqual(review["closed_activities"], ["CE01", "RE02", "RS03"])
        self.assertTrue(review["coverage_met"])
        self.assertLess(review["coverage_percent"], 100.0)

    def test_a_missing_report_section_breaks_the_pair(self):
        report = good_report()
        report["sections"] = [s for s in REPORT_SECTIONS if s != "evidence-index"]
        review = review_verification_documents(good_plan(), report, 100.0)
        self.assertFalse(review["compliant"])
        self.assertEqual(review["report_section_gaps"], ["evidence-index"])

    def test_an_untraced_activity_breaks_the_pair(self):
        report = good_report()
        report["entries"] = report["entries"][:2]
        review = review_verification_documents(good_plan(), report, 66.0)
        self.assertFalse(review["compliant"])
        self.assertEqual(review["untraced_activities"], ["RS03"])

    def test_an_open_non_compliance_breaks_the_pair(self):
        report = good_report()
        report["entries"][0]["result"] = "non-compliant"
        review = review_verification_documents(good_plan(), report, 66.0)
        self.assertFalse(review["compliant"])
        self.assertEqual(review["closed_activities"], ["RE02", "RS03"])

    def test_coverage_shortfall_alone_breaks_the_pair(self):
        plan = good_plan()
        plan["activities"] = [activity("CE01", share=60.0), activity("RE02", share=30.0)]
        report = good_report()
        report["entries"] = [entry("R-1", "CE01"), entry("R-2", "RE02")]
        review = review_verification_documents(plan, report, 100.0)
        self.assertEqual(review["untraced_activities"], [])
        self.assertEqual(review["closure_findings"], [])
        self.assertEqual(review["schedule_findings"], [])
        self.assertAlmostEqual(review["coverage_percent"], 90.0, places=9)
        self.assertFalse(review["coverage_met"])
        self.assertFalse(review["compliant"])

    def test_the_same_activity_set_meets_a_tailored_lower_target(self):
        plan = good_plan()
        plan["activities"] = [activity("CE01", share=60.0), activity("RE02", share=30.0)]
        report = good_report()
        report["entries"] = [entry("R-1", "CE01"), entry("R-2", "RE02")]
        review = review_verification_documents(plan, report, 90.0)
        self.assertTrue(review["coverage_met"])
        self.assertTrue(review["compliant"])

    def test_non_mapping_document_is_rejected(self):
        with self.assertRaises(ValueError):
            review_verification_documents(good_plan(), ["not", "a", "report"])


if __name__ == "__main__":
    unittest.main()

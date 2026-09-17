#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-Q-ST-60-03C Annex B device assurance report DRD.

Exercises scripts/q6003_device_assurance_report_drd_logic.py (stdlib
unittest, offline). Contract: section coverage, reporting-period
continuity, activity reconciliation against the plan, open-item ageing
against the declared response time, the aggregate disposition, and
ValueError on invalid input.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import q6003_device_assurance_report_drd_logic as rptdrd  # noqa: E402


FULL_REPORT = {key: "content for %s" % key for key in rptdrd.REQUIRED_REPORT_SECTIONS}

PLANNED = ["A1", "A2", "A3"]

CLEAN_STATUSES = {"A1": "completed", "A2": "in-progress", "A3": "not-started"}


def full_spec(**overrides):
    spec = {
        "report": dict(FULL_REPORT),
        "period_start": "2026-03-01",
        "period_end": "2026-03-31",
        "previous_period_end": "2026-02-28",
        "planned_activities": list(PLANNED),
        "reported_statuses": dict(CLEAN_STATUSES),
        "nonconformances": [
            {"item_id": "NCR-1", "raised_on": "2026-03-20", "state": "open"},
            {"item_id": "NCR-2", "raised_on": "2026-01-05", "state": "closed"},
        ],
        "open_actions": [
            {"item_id": "ACT-1", "raised_on": "2026-03-25", "state": "open"},
        ],
        "response_days": 30,
    }
    spec.update(overrides)
    return spec


class ParseDayTest(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(
            rptdrd.parse_day("d", "2026-03-01"), datetime.date(2026, 3, 1)
        )

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 3, 1)
        self.assertEqual(rptdrd.parse_day("d", day), day)

    def test_non_calendar_string_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.parse_day("d", "2026-02-30")

    def test_blank_string_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.parse_day("d", "   ")


class MissingReportSectionsTest(unittest.TestCase):
    def test_complete_report_has_no_missing_sections(self):
        self.assertEqual(rptdrd.missing_report_sections(FULL_REPORT), [])

    def test_blank_body_counts_as_absent(self):
        report = dict(FULL_REPORT)
        report["open-actions"] = "  "
        self.assertEqual(rptdrd.missing_report_sections(report), ["open-actions"])

    def test_empty_report_returns_every_section_in_drd_order(self):
        self.assertEqual(
            rptdrd.missing_report_sections({}), list(rptdrd.REQUIRED_REPORT_SECTIONS)
        )

    def test_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.missing_report_sections("introduction")


class PeriodContinuityTest(unittest.TestCase):
    def test_abutting_periods_are_continuous(self):
        record = rptdrd.period_continuity("2026-03-01", "2026-03-31", "2026-02-28")
        self.assertTrue(record["continuous"])
        self.assertEqual(record["gap_days"], 0)
        self.assertEqual(record["overlap_days"], 0)
        self.assertEqual(record["period_days"], 31)

    def test_first_issue_needs_no_predecessor(self):
        record = rptdrd.period_continuity("2026-03-01", "2026-03-31")
        self.assertTrue(record["continuous"])

    def test_gap_between_reports_counted(self):
        record = rptdrd.period_continuity("2026-03-05", "2026-03-31", "2026-02-28")
        self.assertEqual(record["gap_days"], 4)
        self.assertFalse(record["continuous"])

    def test_overlap_between_reports_counted(self):
        record = rptdrd.period_continuity("2026-02-26", "2026-03-31", "2026-02-28")
        self.assertEqual(record["overlap_days"], 3)
        self.assertFalse(record["continuous"])

    def test_single_day_period_is_one_day_long(self):
        record = rptdrd.period_continuity("2026-03-01", "2026-03-01")
        self.assertEqual(record["period_days"], 1)

    def test_period_ending_before_it_starts_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.period_continuity("2026-03-31", "2026-03-01")

    def test_previous_end_after_this_end_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.period_continuity("2026-03-01", "2026-03-31", "2026-04-30")


class ActivityReconciliationTest(unittest.TestCase):
    def test_clean_report_reconciles(self):
        record = rptdrd.activity_reconciliation(PLANNED, CLEAN_STATUSES)
        self.assertEqual(record["unreported"], [])
        self.assertEqual(record["unplanned"], [])
        self.assertEqual(record["completed"], ["A1"])
        self.assertEqual(record["still_open"], ["A2", "A3"])

    def test_unreported_activity_listed_in_plan_order(self):
        record = rptdrd.activity_reconciliation(PLANNED, {"A2": "completed"})
        self.assertEqual(record["unreported"], ["A1", "A3"])

    def test_activity_outside_the_plan_reported(self):
        statuses = dict(CLEAN_STATUSES)
        statuses["A9"] = "completed"
        record = rptdrd.activity_reconciliation(PLANNED, statuses)
        self.assertEqual(record["unplanned"], ["A9"])

    def test_status_matched_without_case(self):
        record = rptdrd.activity_reconciliation(["A1"], {"A1": " Completed "})
        self.assertEqual(record["completed"], ["A1"])

    def test_descoped_activity_is_neither_open_nor_completed(self):
        record = rptdrd.activity_reconciliation(["A1"], {"A1": "descoped"})
        self.assertEqual(record["still_open"], [])
        self.assertEqual(record["completed"], [])

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.activity_reconciliation(["A1"], {"A1": "nearly-done"})

    def test_duplicate_planned_activity_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.activity_reconciliation(["A1", "A1"], {"A1": "completed"})

    def test_empty_plan_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.activity_reconciliation([], {})


class OverdueItemsTest(unittest.TestCase):
    def test_item_inside_the_response_time_is_not_overdue(self):
        items = [{"item_id": "NCR-1", "raised_on": "2026-03-20", "state": "open"}]
        self.assertEqual(rptdrd.overdue_items(items, "2026-03-31", 30), [])

    def test_item_exactly_on_the_response_time_is_not_overdue(self):
        items = [{"item_id": "NCR-1", "raised_on": "2026-03-01", "state": "open"}]
        self.assertEqual(rptdrd.overdue_items(items, "2026-03-31", 30), [])

    def test_item_one_day_past_the_response_time_is_overdue_by_one(self):
        items = [{"item_id": "NCR-1", "raised_on": "2026-02-28", "state": "open"}]
        record = rptdrd.overdue_items(items, "2026-03-31", 30)
        self.assertEqual(len(record), 1)
        self.assertEqual(record[0]["age_days"], 31)
        self.assertEqual(record[0]["overdue_by_days"], 1)

    def test_closed_item_is_never_aged(self):
        items = [{"item_id": "NCR-2", "raised_on": "2025-01-01", "state": "closed"}]
        self.assertEqual(rptdrd.overdue_items(items, "2026-03-31", 30), [])

    def test_overdue_items_ordered_oldest_first(self):
        items = [
            {"item_id": "NCR-A", "raised_on": "2026-01-31", "state": "open"},
            {"item_id": "NCR-B", "raised_on": "2025-12-31", "state": "open"},
        ]
        record = rptdrd.overdue_items(items, "2026-03-31", 30)
        self.assertEqual([r["item_id"] for r in record], ["NCR-B", "NCR-A"])

    def test_item_raised_after_the_period_closed_raises(self):
        items = [{"item_id": "NCR-1", "raised_on": "2026-04-05", "state": "open"}]
        with self.assertRaises(ValueError):
            rptdrd.overdue_items(items, "2026-03-31", 30)

    def test_negative_response_time_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.overdue_items([], "2026-03-31", -1)

    def test_malformed_item_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.overdue_items([{"item_id": "NCR-1"}], "2026-03-31", 30)


class AggregateVerdictTest(unittest.TestCase):
    def test_clean_report_is_accepted(self):
        verdict = rptdrd.assess_device_assurance_report_drd(full_spec())
        self.assertTrue(verdict["accepted"])
        self.assertEqual(verdict["disposition"], "report-drd-accepted")
        self.assertEqual(verdict["findings"], [])

    def test_known_textbook_case_names_every_finding(self):
        report = dict(FULL_REPORT)
        del report["conclusions"]
        spec = full_spec(
            report=report,
            period_start="2026-03-05",
            reported_statuses={"A1": "completed", "A9": "blocked"},
            nonconformances=[
                {"item_id": "NCR-1", "raised_on": "2025-11-01", "state": "open"}
            ],
        )
        verdict = rptdrd.assess_device_assurance_report_drd(spec)
        self.assertEqual(verdict["disposition"], "report-drd-rework")
        self.assertIn("conclusions", verdict["missing_sections"])
        self.assertEqual(verdict["period"]["gap_days"], 4)
        self.assertEqual(verdict["activities"]["unreported"], ["A2", "A3"])
        self.assertEqual(verdict["activities"]["unplanned"], ["A9"])
        self.assertEqual(len(verdict["overdue_nonconformances"]), 1)
        self.assertGreater(len(verdict["findings"]), 5)

    def test_single_overdue_action_forces_rework(self):
        spec = full_spec(
            open_actions=[
                {"item_id": "ACT-9", "raised_on": "2026-01-01", "state": "open"}
            ]
        )
        verdict = rptdrd.assess_device_assurance_report_drd(spec)
        self.assertFalse(verdict["accepted"])
        self.assertEqual(len(verdict["findings"]), 1)
        self.assertEqual(verdict["overdue_actions"][0]["item_id"], "ACT-9")

    def test_spec_missing_key_raises(self):
        spec = full_spec()
        del spec["response_days"]
        with self.assertRaises(ValueError):
            rptdrd.assess_device_assurance_report_drd(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            rptdrd.assess_device_assurance_report_drd(["report"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

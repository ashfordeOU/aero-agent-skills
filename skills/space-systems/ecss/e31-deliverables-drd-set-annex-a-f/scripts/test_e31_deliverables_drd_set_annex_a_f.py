"""Contract tests for the clause 4.9 and annex A-F deliverable set logic."""

import datetime
import unittest

from e31_deliverables_drd_set_annex_a_f_logic import (
    DRD_SET,
    MILESTONES,
    assess_deliverable_set,
    dependency_findings,
    evaluate_deliverable,
    milestone_findings,
    milestone_rank,
    missing_documents,
    missing_sections,
    required_sections,
    schedule_slack_days,
    validate_date,
    validate_document_key,
)

MILESTONE_DATES = {"pdr": "2026-03-02", "cdr": "2026-09-01", "qr": "2027-02-01"}

PLAN_DATES = {
    "thermal-mathematical-model-specification": "2026-02-01",
    "thermal-interface-control-document": "2026-02-10",
    "thermal-and-geometrical-model-description": "2026-06-01",
    "thermal-analysis-report": "2026-07-01",
    "thermal-balance-test-specification": "2026-08-01",
    "thermal-control-detailed-design-description": "2026-08-15",
}

PLANNED_MILESTONE = {
    "thermal-mathematical-model-specification": "pdr",
    "thermal-interface-control-document": "pdr",
    "thermal-and-geometrical-model-description": "cdr",
    "thermal-analysis-report": "cdr",
    "thermal-balance-test-specification": "cdr",
    "thermal-control-detailed-design-description": "cdr",
}


def _entry(key, sections=None, planned_milestone=None, planned_issue_date=None):
    return {
        "key": key,
        "sections": list(DRD_SET[key]["sections"]) if sections is None else sections,
        "planned_milestone": planned_milestone or PLANNED_MILESTONE[key],
        "planned_issue_date": planned_issue_date or PLAN_DATES[key],
    }


def _full_plan():
    return [_entry(key) for key in sorted(DRD_SET)]


class RegisterTests(unittest.TestCase):
    def test_the_annex_set_holds_six_deliverables(self):
        self.assertEqual(len(DRD_SET), 6)

    def test_annex_letters_run_a_to_f(self):
        self.assertEqual(
            sorted(entry["annex"] for entry in DRD_SET.values()),
            ["A", "B", "C", "D", "E", "F"],
        )

    def test_every_deliverable_owes_at_least_four_sections(self):
        for key, entry in DRD_SET.items():
            self.assertGreaterEqual(len(entry["sections"]), 4, key)

    def test_required_sections_are_returned_for_a_known_key(self):
        self.assertIn("margin-summary", required_sections("thermal-analysis-report"))

    def test_document_key_is_normalised(self):
        self.assertEqual(
            validate_document_key(" Thermal-Analysis-Report "), "thermal-analysis-report"
        )

    def test_unknown_document_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_document_key("thermal-wish-list")

    def test_non_string_document_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_document_key(3)


class MilestoneTests(unittest.TestCase):
    def test_reviews_are_in_chronological_order(self):
        self.assertLess(milestone_rank("pdr"), milestone_rank("cdr"))
        self.assertLess(milestone_rank("cdr"), milestone_rank("qr"))

    def test_milestone_name_is_normalised(self):
        self.assertEqual(milestone_rank(" CDR "), MILESTONES.index("cdr"))

    def test_unknown_milestone_rejected(self):
        with self.assertRaises(ValueError):
            milestone_rank("kick-off")

    def test_deliverable_planned_at_its_own_review_raises_nothing(self):
        self.assertEqual(milestone_findings("thermal-analysis-report", "cdr"), [])

    def test_deliverable_planned_earlier_raises_nothing(self):
        self.assertEqual(milestone_findings("thermal-analysis-report", "pdr"), [])

    def test_deliverable_pushed_to_a_later_review_is_a_finding(self):
        self.assertEqual(len(milestone_findings("thermal-analysis-report", "qr")), 1)


class DateTests(unittest.TestCase):
    def test_iso_string_is_parsed(self):
        self.assertEqual(validate_date("2026-09-01", "d"), datetime.date(2026, 9, 1))

    def test_date_object_passes_through(self):
        day = datetime.date(2026, 9, 1)
        self.assertEqual(validate_date(day, "d"), day)

    def test_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_date(datetime.datetime(2026, 9, 1, 12, 0), "d")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_date("2026-13-45", "d")

    def test_empty_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_date("   ", "d")

    def test_slack_is_whole_days_before_the_review(self):
        self.assertEqual(schedule_slack_days("2026-08-01", "2026-09-01"), 31)

    def test_late_issue_gives_negative_slack(self):
        self.assertEqual(schedule_slack_days("2026-09-15", "2026-09-01"), -14)

    def test_issue_on_the_review_day_gives_zero_slack(self):
        self.assertEqual(schedule_slack_days("2026-09-01", "2026-09-01"), 0)


class CompletenessTests(unittest.TestCase):
    def test_full_plan_misses_no_document(self):
        self.assertEqual(missing_documents(sorted(DRD_SET)), [])

    def test_partial_plan_names_the_absent_documents(self):
        absent = missing_documents(["thermal-analysis-report"])
        self.assertEqual(len(absent), 5)
        self.assertIn("thermal-interface-control-document", absent)

    def test_unknown_key_in_the_plan_rejected(self):
        with self.assertRaises(ValueError):
            missing_documents(["thermal-poster"])

    def test_full_content_misses_no_section(self):
        key = "thermal-balance-test-specification"
        self.assertEqual(missing_sections(key, DRD_SET[key]["sections"]), [])

    def test_absent_section_is_named(self):
        key = "thermal-balance-test-specification"
        partial = [s for s in DRD_SET[key]["sections"] if s != "success-criteria"]
        self.assertEqual(missing_sections(key, partial), ["success-criteria"])

    def test_section_names_are_normalised(self):
        key = "thermal-analysis-report"
        upper = [s.upper() for s in DRD_SET[key]["sections"]]
        self.assertEqual(missing_sections(key, upper), [])

    def test_blank_section_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections("thermal-analysis-report", [" "])


class DependencyTests(unittest.TestCase):
    def test_correct_order_raises_nothing(self):
        self.assertEqual(
            dependency_findings("thermal-analysis-report", PLAN_DATES), []
        )

    def test_report_before_its_model_is_a_finding(self):
        dates = dict(PLAN_DATES, **{"thermal-analysis-report": "2026-05-01"})
        findings = dependency_findings("thermal-analysis-report", dates)
        self.assertEqual(len(findings), 1)

    def test_absent_dependency_is_a_finding(self):
        dates = {k: v for k, v in PLAN_DATES.items()
                 if k != "thermal-and-geometrical-model-description"}
        findings = dependency_findings("thermal-analysis-report", dates)
        self.assertEqual(len(findings), 1)

    def test_root_deliverable_has_no_dependency_finding(self):
        self.assertEqual(
            dependency_findings("thermal-mathematical-model-specification", PLAN_DATES), []
        )

    def test_deliverable_absent_from_its_own_plan_rejected(self):
        dates = {k: v for k, v in PLAN_DATES.items() if k != "thermal-analysis-report"}
        with self.assertRaises(ValueError):
            dependency_findings("thermal-analysis-report", dates)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            dependency_findings("thermal-analysis-report", {})


class DeliverableEvaluationTests(unittest.TestCase):
    def test_nominal_deliverable_is_complete(self):
        record = evaluate_deliverable(
            _entry("thermal-analysis-report"), MILESTONE_DATES, PLAN_DATES
        )
        self.assertTrue(record["complete"])
        self.assertEqual(record["annex"], "C")
        self.assertEqual(record["slack_days"], 62)

    def test_missing_section_fails_the_deliverable(self):
        key = "thermal-analysis-report"
        partial = [s for s in DRD_SET[key]["sections"] if s != "model-uncertainty"]
        record = evaluate_deliverable(
            _entry(key, sections=partial), MILESTONE_DATES, PLAN_DATES
        )
        self.assertFalse(record["complete"])
        self.assertEqual(record["missing_sections"], ["model-uncertainty"])

    def test_late_issue_fails_the_deliverable(self):
        key = "thermal-analysis-report"
        dates = dict(PLAN_DATES, **{key: "2026-10-01"})
        record = evaluate_deliverable(
            _entry(key, planned_issue_date="2026-10-01"), MILESTONE_DATES, dates
        )
        self.assertLess(record["slack_days"], 0)
        self.assertFalse(record["complete"])

    def test_deferred_review_fails_the_deliverable(self):
        record = evaluate_deliverable(
            _entry("thermal-analysis-report", planned_milestone="qr"),
            MILESTONE_DATES, PLAN_DATES,
        )
        self.assertFalse(record["complete"])

    def test_missing_milestone_date_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_deliverable(
                _entry("thermal-analysis-report"), {"pdr": "2026-03-02"}, PLAN_DATES
            )

    def test_missing_entry_key_rejected(self):
        entry = _entry("thermal-analysis-report")
        del entry["sections"]
        with self.assertRaises(ValueError):
            evaluate_deliverable(entry, MILESTONE_DATES, PLAN_DATES)


class AssessmentTests(unittest.TestCase):
    def test_full_plan_is_complete(self):
        result = assess_deliverable_set(
            {"deliverables": _full_plan(), "milestone_dates": MILESTONE_DATES}
        )
        self.assertTrue(result["deliverable_set_complete"])
        self.assertAlmostEqual(result["completeness_fraction"], 1.0, places=12)
        self.assertEqual(result["absent_deliverables"], [])

    def test_absent_deliverable_is_named(self):
        plan = [e for e in _full_plan()
                if e["key"] != "thermal-control-detailed-design-description"]
        result = assess_deliverable_set(
            {"deliverables": plan, "milestone_dates": MILESTONE_DATES}
        )
        self.assertIn(
            "thermal-control-detailed-design-description", result["absent_deliverables"]
        )
        self.assertFalse(result["deliverable_set_complete"])

    def test_tightest_slack_deliverable_is_reported(self):
        plan = _full_plan()
        for entry in plan:
            if entry["key"] == "thermal-control-detailed-design-description":
                entry["planned_issue_date"] = "2026-08-30"
        result = assess_deliverable_set(
            {"deliverables": plan, "milestone_dates": MILESTONE_DATES}
        )
        self.assertEqual(
            result["tightest_slack_deliverable"],
            "thermal-control-detailed-design-description",
        )

    def test_completeness_fraction_counts_against_the_whole_annex_set(self):
        plan = [_entry("thermal-mathematical-model-specification"),
                _entry("thermal-interface-control-document")]
        result = assess_deliverable_set(
            {"deliverables": plan, "milestone_dates": MILESTONE_DATES}
        )
        self.assertAlmostEqual(result["completeness_fraction"], 2.0 / 6.0, places=12)

    def test_duplicate_deliverable_rejected(self):
        plan = _full_plan() + [_entry("thermal-analysis-report")]
        with self.assertRaises(ValueError):
            assess_deliverable_set(
                {"deliverables": plan, "milestone_dates": MILESTONE_DATES}
            )

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_deliverable_set({"deliverables": [], "milestone_dates": MILESTONE_DATES})

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_deliverable_set({"deliverables": _full_plan()})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_deliverable_set(["deliverables"])


if __name__ == "__main__":
    unittest.main()

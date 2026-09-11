#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.2 SE planning.

Exercises scripts/e10_se_planning_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a review milestone id
resolves to its canonical order index and an unrecognized id raises;
a project's planned milestones are flagged for a duplicate id or for
dates that run backwards relative to the canonical review sequence;
a discipline plan is flagged when it has no linked milestone or when
its delivery date is after the milestone date it feeds; a required
discipline with no plan on record is flagged as a coverage gap; and
the aggregated review is compliant only when sequence, integration,
and coverage are all empty.
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_se_planning_logic as se  # noqa: E402


class MilestoneSequenceIndexTest(unittest.TestCase):
    def test_srr_is_first(self):
        self.assertEqual(se.milestone_sequence_index("SRR"), 0)

    def test_ar_is_last(self):
        self.assertEqual(
            se.milestone_sequence_index("AR"), len(se.CANONICAL_MILESTONES) - 1
        )

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            se.milestone_sequence_index("MYSTERY_REVIEW")


class ParsePlanDateTest(unittest.TestCase):
    def test_parses_iso_string(self):
        self.assertEqual(se.parse_plan_date("2027-03-01"), date(2027, 3, 1))

    def test_passes_through_date_instance(self):
        d = date(2027, 3, 1)
        self.assertEqual(se.parse_plan_date(d), d)

    def test_malformed_string_raises(self):
        with self.assertRaises(ValueError):
            se.parse_plan_date("not-a-date")

    def test_non_date_type_raises(self):
        with self.assertRaises(ValueError):
            se.parse_plan_date(20270301)


class ValidateMilestoneOrderTest(unittest.TestCase):
    def test_in_sequence_dates_have_no_violation(self):
        milestones = [
            {"milestone_id": "SRR", "planned_date": "2027-01-10"},
            {"milestone_id": "PDR", "planned_date": "2027-04-10"},
            {"milestone_id": "CDR", "planned_date": "2027-08-10"},
        ]
        self.assertEqual(se.validate_milestone_order(milestones), [])

    def test_out_of_order_dates_flagged(self):
        milestones = [
            {"milestone_id": "SRR", "planned_date": "2027-06-01"},
            {"milestone_id": "PDR", "planned_date": "2027-01-01"},
        ]
        violations = se.validate_milestone_order(milestones)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "milestone_out_of_sequence")
        self.assertEqual(violations[0]["earlier_milestone"], "SRR")
        self.assertEqual(violations[0]["later_milestone"], "PDR")

    def test_duplicate_milestone_flagged(self):
        milestones = [
            {"milestone_id": "SRR", "planned_date": "2027-01-10"},
            {"milestone_id": "SRR", "planned_date": "2027-01-20"},
        ]
        violations = se.validate_milestone_order(milestones)
        self.assertEqual(
            violations, [{"issue": "duplicate_milestone", "milestone": "SRR"}]
        )

    def test_non_consecutive_milestones_still_checked(self):
        # SRR and QR are not consecutive canonical entries, but with PDR/CDR
        # absent the check still walks SRR -> QR and must catch a regression.
        milestones = [
            {"milestone_id": "SRR", "planned_date": "2027-06-01"},
            {"milestone_id": "QR", "planned_date": "2027-01-01"},
        ]
        violations = se.validate_milestone_order(milestones)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "milestone_out_of_sequence")

    def test_unknown_milestone_id_raises(self):
        milestones = [{"milestone_id": "BOGUS", "planned_date": "2027-01-01"}]
        with self.assertRaises(ValueError):
            se.validate_milestone_order(milestones)


class DisciplineIntegrationViolationsTest(unittest.TestCase):
    def setUp(self):
        self.milestones = [
            {"milestone_id": "SRR", "planned_date": "2027-01-10"},
            {"milestone_id": "PDR", "planned_date": "2027-04-10"},
        ]

    def test_on_time_delivery_has_no_violation(self):
        plans = [
            {
                "discipline_id": "verification",
                "contributes_to_milestone": "SRR",
                "delivery_date": "2027-01-05",
            }
        ]
        self.assertEqual(
            se.discipline_integration_violations(plans, self.milestones), []
        )

    def test_delivery_on_milestone_date_has_no_violation(self):
        plans = [
            {
                "discipline_id": "verification",
                "contributes_to_milestone": "SRR",
                "delivery_date": "2027-01-10",
            }
        ]
        self.assertEqual(
            se.discipline_integration_violations(plans, self.milestones), []
        )

    def test_late_delivery_flagged(self):
        plans = [
            {
                "discipline_id": "product_assurance",
                "contributes_to_milestone": "SRR",
                "delivery_date": "2027-02-01",
            }
        ]
        violations = se.discipline_integration_violations(plans, self.milestones)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "late_discipline_input")
        self.assertEqual(violations[0]["discipline"], "product_assurance")

    def test_missing_milestone_linkage_flagged(self):
        plans = [
            {
                "discipline_id": "software_engineering",
                "contributes_to_milestone": "CDR",
                "delivery_date": "2027-06-01",
            }
        ]
        violations = se.discipline_integration_violations(plans, self.milestones)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "missing_milestone_linkage",
                    "discipline": "software_engineering",
                    "target_milestone": "CDR",
                }
            ],
        )


class MissingRequiredDisciplinesTest(unittest.TestCase):
    def test_all_present_returns_empty(self):
        plans = [
            {"discipline_id": discipline, "contributes_to_milestone": "SRR", "delivery_date": "2027-01-01"}
            for discipline in se.REQUIRED_DISCIPLINES
        ]
        self.assertEqual(se.missing_required_disciplines(plans), [])

    def test_missing_discipline_reported_sorted(self):
        plans = [
            {
                "discipline_id": "verification",
                "contributes_to_milestone": "SRR",
                "delivery_date": "2027-01-01",
            }
        ]
        missing = se.missing_required_disciplines(plans)
        self.assertEqual(missing, sorted(se.REQUIRED_DISCIPLINES - {"verification"}))


class SePlanningReviewTest(unittest.TestCase):
    def test_fully_compliant_plan(self):
        se_plan = {
            "milestones": [
                {"milestone_id": "SRR", "planned_date": "2027-01-10"},
                {"milestone_id": "PDR", "planned_date": "2027-04-10"},
            ],
            "discipline_plans": [
                {
                    "discipline_id": discipline,
                    "contributes_to_milestone": "SRR",
                    "delivery_date": "2027-01-01",
                }
                for discipline in se.REQUIRED_DISCIPLINES
            ],
        }
        review = se.se_planning_review(se_plan)
        self.assertEqual(review, {"sequence": [], "integration": [], "coverage": []})
        self.assertTrue(se.is_se_plan_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        se_plan = {
            "milestones": [
                {"milestone_id": "SRR", "planned_date": "2027-06-01"},
                {"milestone_id": "PDR", "planned_date": "2027-01-01"},
            ],
            "discipline_plans": [
                {
                    "discipline_id": "verification",
                    "contributes_to_milestone": "CDR",
                    "delivery_date": "2027-01-01",
                }
            ],
        }
        review = se.se_planning_review(se_plan)
        self.assertTrue(review["sequence"])
        self.assertTrue(review["integration"])
        self.assertTrue(review["coverage"])
        self.assertFalse(se.is_se_plan_compliant(review))

    def test_review_raises_on_unknown_milestone(self):
        se_plan = {
            "milestones": [{"milestone_id": "BOGUS", "planned_date": "2027-01-01"}],
            "discipline_plans": [],
        }
        with self.assertRaises(ValueError):
            se.se_planning_review(se_plan)

    def test_empty_plan_reports_only_coverage_gaps(self):
        review = se.se_planning_review({"milestones": [], "discipline_plans": []})
        self.assertEqual(review["sequence"], [])
        self.assertEqual(review["integration"], [])
        self.assertEqual(len(review["coverage"]), len(se.REQUIRED_DISCIPLINES))
        self.assertFalse(se.is_se_plan_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)

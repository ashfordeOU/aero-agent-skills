#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.2.2 electromagnetic
compatibility control plan delivery.

Exercises scripts/e20_emc_control_plan_delivery_logic.py (stdlib
unittest, offline). Contract: every mandatory plan section belongs to
exactly one group and an unrecognized section raises; a section status
maps to a maturity and an unknown status raises; the completeness index
is the mean maturity over the mandatory set so an undeclared section
drags it down; a plan whose sections are all issued sits exactly at the
hand-over threshold and is not failed by the floating-point mean;
delivery lead time is counted in calendar days against the review and
the data package deadline, with a malformed date raising; every
compatibility requirement traces into a declared, started section; and
the plan is deliverable only when every finding list is empty.
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_emc_control_plan_delivery_logic as cp  # noqa: E402


def _sections(status="approved"):
    return {name: status for name in sorted(cp.MANDATORY_PLAN_SECTIONS)}


def _requirement_map():
    return [
        {"requirement_id": "EMC-R-010", "plan_section": "requirement_and_limit_flowdown"},
        {"requirement_id": "EMC-R-020", "plan_section": "grounding_and_bonding_concept"},
        {"requirement_id": "EMC-R-030", "plan_section": "safety_margin_policy"},
    ]


def _clean_plan():
    return {
        "declared_sections": _sections("approved"),
        "delivery_date": "2027-03-01",
        "review_date": "2027-04-15",
        "requirement_map": _requirement_map(),
    }


class TestSectionCategorization(unittest.TestCase):
    def test_scope_section_is_a_management_section(self):
        self.assertEqual(
            cp.categorize_plan_section("scope_and_applicability"), "management"
        )

    def test_grounding_concept_is_a_design_section(self):
        self.assertEqual(
            cp.categorize_plan_section("grounding_and_bonding_concept"), "design"
        )

    def test_critical_point_list_is_a_verification_section(self):
        self.assertEqual(
            cp.categorize_plan_section("interference_critical_point_list"),
            "verification",
        )

    def test_every_section_lands_in_a_known_group(self):
        groups = {
            cp.categorize_plan_section(s) for s in cp.MANDATORY_PLAN_SECTIONS
        }
        self.assertEqual(groups, {"management", "design", "verification"})

    def test_uncategorized_section_raises(self):
        with self.assertRaises(ValueError):
            cp.categorize_plan_section("thermal_control_concept")

    def test_none_section_raises(self):
        with self.assertRaises(ValueError):
            cp.categorize_plan_section(None)

    def test_plan_carries_twelve_mandatory_sections(self):
        self.assertEqual(len(cp.MANDATORY_PLAN_SECTIONS), 12)


class TestSectionMaturity(unittest.TestCase):
    def test_not_started_has_zero_maturity(self):
        self.assertAlmostEqual(cp.section_maturity("not_started"), 0.0, places=9)

    def test_draft_is_less_mature_than_issued(self):
        self.assertLess(cp.section_maturity("draft"), cp.section_maturity("issued"))

    def test_approved_is_the_top_of_the_scale(self):
        self.assertAlmostEqual(cp.section_maturity("approved"), 1.0, places=9)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            cp.section_maturity("under_discussion")

    def test_maturity_scale_is_monotonic(self):
        ordered = ["not_started", "draft", "issued", "approved"]
        values = [cp.section_maturity(s) for s in ordered]
        self.assertEqual(values, sorted(values))


class TestMissingAndImmature(unittest.TestCase):
    def test_full_plan_has_no_missing_section(self):
        self.assertEqual(cp.missing_plan_sections(_sections()), [])

    def test_absent_section_is_reported(self):
        declared = _sections()
        del declared["safety_margin_policy"]
        self.assertEqual(cp.missing_plan_sections(declared), ["safety_margin_policy"])

    def test_missing_sections_are_sorted(self):
        declared = _sections()
        del declared["safety_margin_policy"]
        del declared["scope_and_applicability"]
        missing = cp.missing_plan_sections(declared)
        self.assertEqual(missing, sorted(missing))
        self.assertEqual(len(missing), 2)

    def test_empty_plan_reports_every_section_missing(self):
        self.assertEqual(len(cp.missing_plan_sections({})), 12)

    def test_unknown_section_in_declaration_raises(self):
        declared = _sections()
        declared["propulsion_concept"] = "approved"
        with self.assertRaises(ValueError):
            cp.missing_plan_sections(declared)

    def test_non_mapping_declaration_raises(self):
        with self.assertRaises(ValueError):
            cp.missing_plan_sections(["scope_and_applicability"])

    def test_issued_sections_are_mature_enough(self):
        self.assertEqual(cp.immature_plan_sections(_sections("issued")), [])

    def test_draft_sections_are_immature(self):
        self.assertEqual(len(cp.immature_plan_sections(_sections("draft"))), 12)

    def test_single_draft_section_is_reported(self):
        declared = _sections("approved")
        declared["predictive_analysis_approach"] = "draft"
        self.assertEqual(
            cp.immature_plan_sections(declared), ["predictive_analysis_approach"]
        )

    def test_raised_minimum_status_reports_issued_sections(self):
        self.assertEqual(
            len(cp.immature_plan_sections(_sections("issued"), "approved")), 12
        )

    def test_unknown_minimum_status_raises(self):
        with self.assertRaises(ValueError):
            cp.immature_plan_sections(_sections(), "finalised")

    def test_unknown_status_in_declaration_raises(self):
        declared = _sections()
        declared["schedule_and_deliverables"] = "nearly_done"
        with self.assertRaises(ValueError):
            cp.immature_plan_sections(declared)


class TestCompletenessIndex(unittest.TestCase):
    def test_fully_approved_plan_scores_one(self):
        self.assertAlmostEqual(
            cp.plan_completeness_index(_sections("approved")), 1.0, places=9
        )

    def test_empty_plan_scores_zero(self):
        self.assertAlmostEqual(cp.plan_completeness_index({}), 0.0, places=9)

    def test_undeclared_section_drags_the_index_down(self):
        declared = _sections("approved")
        del declared["nonconformance_and_waiver_route"]
        self.assertAlmostEqual(
            cp.plan_completeness_index(declared), 11.0 / 12.0, places=9
        )

    def test_all_draft_plan_scores_the_draft_maturity(self):
        self.assertAlmostEqual(
            cp.plan_completeness_index(_sections("draft")), 0.4, places=9
        )

    def test_non_mapping_declaration_raises(self):
        with self.assertRaises(ValueError):
            cp.plan_completeness_index("approved")

    def test_all_issued_plan_sits_one_ulp_below_the_threshold(self):
        """Twelve sections at the issued maturity average to exactly the
        hand-over threshold, but the mean lands one unit in the last
        place low; the comparison absorbs that, the threshold does not
        move."""
        index = cp.plan_completeness_index(_sections("issued"))
        self.assertLess(index, cp.DEFAULT_COMPLETENESS_THRESHOLD)
        self.assertTrue(cp.index_meets_threshold(index))

    def test_real_shortfall_still_fails(self):
        self.assertFalse(cp.index_meets_threshold(0.75))

    def test_comfortable_index_passes(self):
        self.assertTrue(cp.index_meets_threshold(0.95))

    def test_threshold_above_one_raises(self):
        with self.assertRaises(ValueError):
            cp.index_meets_threshold(0.9, 1.4)

    def test_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            cp.index_meets_threshold(0.9, -0.1)

    def test_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            cp.index_meets_threshold(0.9, "0.8")


class TestDeliveryTiming(unittest.TestCase):
    def test_lead_days_between_iso_dates(self):
        self.assertEqual(cp.delivery_lead_days("2027-03-01", "2027-04-15"), 45)

    def test_lead_days_accept_date_objects(self):
        self.assertEqual(
            cp.delivery_lead_days(
                datetime.date(2027, 3, 1), datetime.date(2027, 3, 21)
            ),
            20,
        )

    def test_late_delivery_gives_negative_lead(self):
        self.assertEqual(cp.delivery_lead_days("2027-04-20", "2027-04-15"), -5)

    def test_malformed_date_raises(self):
        with self.assertRaises(ValueError):
            cp.delivery_lead_days("15/04/2027", "2027-04-15")

    def test_non_date_type_raises(self):
        with self.assertRaises(ValueError):
            cp.delivery_lead_days(20270415, "2027-04-15")

    def test_timely_delivery_has_no_finding(self):
        self.assertEqual(cp.delivery_findings("2027-03-01", "2027-04-15"), [])

    def test_delivery_exactly_on_the_deadline_has_no_finding(self):
        self.assertEqual(cp.delivery_findings("2027-03-26", "2027-04-15"), [])

    def test_delivery_inside_the_deadline_is_a_finding(self):
        findings = cp.delivery_findings("2027-04-10", "2027-04-15")
        self.assertTrue(any("data package deadline" in f for f in findings))

    def test_delivery_after_the_review_is_a_finding(self):
        findings = cp.delivery_findings("2027-04-20", "2027-04-15")
        self.assertTrue(any("after the preliminary design review" in f for f in findings))

    def test_negative_lead_requirement_raises(self):
        with self.assertRaises(ValueError):
            cp.delivery_findings("2027-03-01", "2027-04-15", -1)

    def test_non_integer_lead_requirement_raises(self):
        with self.assertRaises(ValueError):
            cp.delivery_findings("2027-03-01", "2027-04-15", 20.5)


class TestTraceability(unittest.TestCase):
    def test_traced_requirements_have_no_finding(self):
        self.assertEqual(
            cp.traceability_findings(_requirement_map(), _sections("approved")), []
        )

    def test_untraced_requirement_is_a_finding(self):
        entries = _requirement_map() + [{"requirement_id": "EMC-R-040"}]
        findings = cp.traceability_findings(entries, _sections("approved"))
        self.assertTrue(any("not traced into any plan section" in f for f in findings))

    def test_requirement_pointing_at_an_undeclared_section_is_a_finding(self):
        declared = _sections("approved")
        del declared["safety_margin_policy"]
        findings = cp.traceability_findings(_requirement_map(), declared)
        self.assertTrue(any("does not declare" in f for f in findings))

    def test_requirement_pointing_at_an_unstarted_section_is_a_finding(self):
        declared = _sections("approved")
        declared["safety_margin_policy"] = "not_started"
        findings = cp.traceability_findings(_requirement_map(), declared)
        self.assertTrue(any("has not been" in f for f in findings))

    def test_requirement_pointing_at_an_unknown_section_raises(self):
        entries = [{"requirement_id": "EMC-R-050", "plan_section": "launch_campaign"}]
        with self.assertRaises(ValueError):
            cp.traceability_findings(entries, _sections("approved"))

    def test_traceability_findings_are_sorted(self):
        entries = [
            {"requirement_id": "EMC-R-200"},
            {"requirement_id": "EMC-R-100"},
        ]
        findings = cp.traceability_findings(entries, _sections("approved"))
        self.assertEqual(findings, sorted(findings))
        self.assertEqual(len(findings), 2)


class TestAggregate(unittest.TestCase):
    def test_clean_plan_is_deliverable(self):
        result = cp.aggregate_control_plan_delivery(_clean_plan())
        self.assertTrue(result["deliverable"])
        self.assertEqual(result["missing_sections"], [])
        self.assertEqual(result["immature_sections"], [])
        self.assertEqual(result["delivery_findings"], [])
        self.assertEqual(result["traceability_findings"], [])
        self.assertAlmostEqual(result["completeness_index"], 1.0, places=9)

    def test_all_issued_plan_is_deliverable_at_the_threshold(self):
        plan = _clean_plan()
        plan["declared_sections"] = _sections("issued")
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertTrue(result["deliverable"])
        self.assertLess(result["completeness_index"], 0.8)

    def test_draft_plan_is_not_deliverable(self):
        plan = _clean_plan()
        plan["declared_sections"] = _sections("draft")
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertFalse(result["deliverable"])
        self.assertEqual(len(result["immature_sections"]), 12)

    def test_missing_section_blocks_delivery(self):
        plan = _clean_plan()
        del plan["declared_sections"]["shielding_and_harness_rules"]
        plan["requirement_map"] = []
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertFalse(result["deliverable"])
        self.assertEqual(result["missing_sections"], ["shielding_and_harness_rules"])

    def test_late_hand_over_blocks_delivery(self):
        plan = _clean_plan()
        plan["delivery_date"] = "2027-04-20"
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertFalse(result["deliverable"])
        self.assertEqual(len(result["delivery_findings"]), 1)

    def test_untraced_requirement_blocks_delivery(self):
        plan = _clean_plan()
        plan["requirement_map"] = plan["requirement_map"] + [
            {"requirement_id": "EMC-R-099"}
        ]
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertFalse(result["deliverable"])
        self.assertEqual(len(result["traceability_findings"]), 1)

    def test_raised_threshold_can_block_an_issued_plan(self):
        plan = _clean_plan()
        plan["declared_sections"] = _sections("issued")
        plan["completeness_threshold"] = 0.95
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertFalse(result["deliverable"])

    def test_shortened_lead_requirement_accepts_a_closer_hand_over(self):
        plan = _clean_plan()
        plan["delivery_date"] = "2027-04-10"
        plan["required_lead_days"] = 3
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertTrue(result["deliverable"])

    def test_plan_without_requirement_map_is_still_reviewable(self):
        plan = _clean_plan()
        del plan["requirement_map"]
        result = cp.aggregate_control_plan_delivery(plan)
        self.assertTrue(result["deliverable"])


if __name__ == "__main__":
    unittest.main()

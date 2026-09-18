"""Contract tests for the clause 5.2.2 category two hybrid manufacturer logic."""

import datetime
import unittest

from q6005_category_two_non_approved_manufacturer_logic import (
    AUDIT_VALIDITY_DAYS,
    CONDITION_WEIGHTS,
    COVERAGE_TOLERANCE,
    JUSTIFICATION_ELEMENTS,
    PROVISIONAL_COVERAGE,
    approved_source_bypass,
    assess_category_two_source,
    audit_condition,
    audit_justification,
    grade_conditions,
    parse_date,
)

ASSESS_DAY = "2026-09-18"

FULL_JUSTIFICATION = dict((element, True) for element in JUSTIFICATION_ELEMENTS)

FULL_CONDITIONS = {
    "manufacturer-audit": {"performed_on": "2025-06-02", "open_major_findings": 0},
    "agreed-validation-programme": {"agreed": True},
    "baselined-process-documentation": {"agreed": True},
    "current-quality-certification": {"valid_until": "2027-05-30"},
    "added-lot-testing": {"agreed": True},
}


def justification_without(*missing):
    data = dict(FULL_JUSTIFICATION)
    for element in missing:
        data[element] = False
    return data


def conditions_without(*dropped):
    data = dict(FULL_CONDITIONS)
    for name in dropped:
        data.pop(name, None)
    return data


def proposal_with(**overrides):
    proposal = {
        "manufacturer": "Thickfilm Hybrids SA",
        "justification": FULL_JUSTIFICATION,
        "approved_sources": [],
        "conditions": FULL_CONDITIONS,
    }
    proposal.update(overrides)
    return proposal


class WeightingTests(unittest.TestCase):
    def test_condition_shares_sum_to_one(self):
        total = sum(weight for _, weight in CONDITION_WEIGHTS)
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_provisional_bound_sits_below_full_coverage(self):
        self.assertLess(PROVISIONAL_COVERAGE, 1.0)

    def test_audit_window_is_a_whole_number_of_days(self):
        self.assertIsInstance(AUDIT_VALIDITY_DAYS, int)


class ParseDateTests(unittest.TestCase):
    def test_iso_string_becomes_a_date(self):
        self.assertEqual(parse_date("2026-09-18"), datetime.date(2026, 9, 18))

    def test_date_instance_passes_through(self):
        day = datetime.date(2024, 7, 4)
        self.assertEqual(parse_date(day), day)

    def test_malformed_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("18.09.2026")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(None)


class JustificationTests(unittest.TestCase):
    def test_complete_justification_is_complete(self):
        audit = audit_justification(FULL_JUSTIFICATION)
        self.assertTrue(audit["complete"])
        self.assertAlmostEqual(audit["completeness"], 1.0, places=9)

    def test_missing_elements_are_named_in_mandated_order(self):
        audit = audit_justification(justification_without("risk-assessment", "technical-necessity"))
        self.assertEqual(audit["missing"], ["technical-necessity", "risk-assessment"])

    def test_completeness_is_the_present_fraction(self):
        audit = audit_justification(justification_without("customer-agreement"))
        self.assertAlmostEqual(
            audit["completeness"],
            (len(JUSTIFICATION_ELEMENTS) - 1) / float(len(JUSTIFICATION_ELEMENTS)),
            places=9,
        )

    def test_absent_justification_rejected(self):
        with self.assertRaises(ValueError):
            audit_justification(None)

    def test_non_mapping_justification_rejected(self):
        with self.assertRaises(ValueError):
            audit_justification(list(JUSTIFICATION_ELEMENTS))

    def test_element_outside_the_mandated_set_rejected(self):
        data = dict(FULL_JUSTIFICATION)
        data["price-comparison"] = True
        with self.assertRaises(ValueError):
            audit_justification(data)


class ApprovedSourceBypassTests(unittest.TestCase):
    def test_no_approved_sources_is_no_bypass(self):
        self.assertEqual(approved_source_bypass(None), [])

    def test_available_source_with_no_reason_is_a_bypass(self):
        sources = [{"name": "Approved Hybrids Ltd", "available": True}]
        self.assertEqual(approved_source_bypass(sources), ["Approved Hybrids Ltd"])

    def test_stated_exclusion_reason_clears_the_bypass(self):
        sources = [
            {"name": "Approved Hybrids Ltd", "available": True, "exclusion_reason": "package outside its scope"}
        ]
        self.assertEqual(approved_source_bypass(sources), [])

    def test_blank_exclusion_reason_does_not_clear_the_bypass(self):
        sources = [{"name": "Approved Hybrids Ltd", "available": True, "exclusion_reason": "   "}]
        self.assertEqual(approved_source_bypass(sources), ["Approved Hybrids Ltd"])

    def test_unavailable_source_is_not_a_bypass(self):
        sources = [{"name": "Approved Hybrids Ltd", "available": False}]
        self.assertEqual(approved_source_bypass(sources), [])

    def test_source_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            approved_source_bypass([{"available": True}])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            approved_source_bypass({"name": "Approved Hybrids Ltd"})


class ConditionAuditTests(unittest.TestCase):
    def test_current_closed_audit_satisfies(self):
        result = audit_condition(
            "manufacturer-audit", {"performed_on": "2025-06-02", "open_major_findings": 0}, ASSESS_DAY
        )
        self.assertTrue(result["satisfied"])

    def test_audit_on_the_last_valid_day_still_satisfies(self):
        last_valid = datetime.date(2026, 9, 18) - datetime.timedelta(days=AUDIT_VALIDITY_DAYS)
        result = audit_condition(
            "manufacturer-audit", {"performed_on": last_valid, "open_major_findings": 0}, ASSESS_DAY
        )
        self.assertTrue(result["satisfied"])
        self.assertEqual(result["age_days"], AUDIT_VALIDITY_DAYS)

    def test_audit_one_day_past_the_window_fails(self):
        stale = datetime.date(2026, 9, 18) - datetime.timedelta(days=AUDIT_VALIDITY_DAYS + 1)
        result = audit_condition("manufacturer-audit", {"performed_on": stale}, ASSESS_DAY)
        self.assertFalse(result["satisfied"])

    def test_open_major_finding_fails_a_current_audit(self):
        result = audit_condition(
            "manufacturer-audit", {"performed_on": "2025-06-02", "open_major_findings": 2}, ASSESS_DAY
        )
        self.assertFalse(result["satisfied"])

    def test_negative_open_finding_count_rejected(self):
        with self.assertRaises(ValueError):
            audit_condition(
                "manufacturer-audit", {"performed_on": "2025-06-02", "open_major_findings": -1}, ASSESS_DAY
            )

    def test_certification_expiring_on_the_assessment_day_still_satisfies(self):
        result = audit_condition("current-quality-certification", {"valid_until": ASSESS_DAY}, ASSESS_DAY)
        self.assertTrue(result["satisfied"])
        self.assertEqual(result["days_remaining"], 0)

    def test_expired_certification_fails(self):
        result = audit_condition(
            "current-quality-certification", {"valid_until": "2026-09-17"}, ASSESS_DAY
        )
        self.assertFalse(result["satisfied"])
        self.assertEqual(result["days_remaining"], -1)

    def test_agreement_conditions_turn_on_the_agreed_flag(self):
        self.assertTrue(audit_condition("added-lot-testing", {"agreed": True}, ASSESS_DAY)["satisfied"])
        self.assertFalse(audit_condition("added-lot-testing", {"agreed": False}, ASSESS_DAY)["satisfied"])

    def test_absent_evidence_is_unmet_not_an_error(self):
        result = audit_condition("agreed-validation-programme", None, ASSESS_DAY)
        self.assertFalse(result["satisfied"])

    def test_unknown_condition_rejected(self):
        with self.assertRaises(ValueError):
            audit_condition("free-samples", {"agreed": True}, ASSESS_DAY)


class GradeConditionsTests(unittest.TestCase):
    def test_full_evidence_gives_full_coverage(self):
        grading = grade_conditions(FULL_CONDITIONS, ASSESS_DAY)
        self.assertTrue(grading["all_met"])
        self.assertAlmostEqual(grading["coverage"], 1.0, places=9)

    def test_no_evidence_gives_zero_coverage(self):
        grading = grade_conditions({}, ASSESS_DAY)
        self.assertAlmostEqual(grading["coverage"], 0.0, places=9)
        self.assertEqual(len(grading["unmet"]), len(CONDITION_WEIGHTS))

    def test_coverage_drops_by_exactly_the_missing_share(self):
        grading = grade_conditions(conditions_without("added-lot-testing"), ASSESS_DAY)
        self.assertAlmostEqual(grading["coverage"], 1.0 - 0.15, places=9)
        self.assertEqual(grading["unmet"], ["added-lot-testing"])

    def test_every_condition_is_graded_even_when_absent(self):
        grading = grade_conditions(None, ASSESS_DAY)
        self.assertEqual(len(grading["audits"]), len(CONDITION_WEIGHTS))

    def test_condition_outside_the_set_rejected(self):
        with self.assertRaises(ValueError):
            grade_conditions({"free-samples": {"agreed": True}}, ASSESS_DAY)

    def test_non_mapping_conditions_rejected(self):
        with self.assertRaises(ValueError):
            grade_conditions(["manufacturer-audit"], ASSESS_DAY)


class AssessmentTests(unittest.TestCase):
    def test_admissible_justification_with_every_condition_is_acceptable(self):
        result = assess_category_two_source(proposal_with(), ASSESS_DAY)
        self.assertEqual(result["disposition"], "acceptable")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_one_open_condition_leaves_the_source_usable_with_actions(self):
        result = assess_category_two_source(
            proposal_with(conditions=conditions_without("added-lot-testing")), ASSESS_DAY
        )
        self.assertEqual(result["disposition"], "acceptable-with-open-actions")
        self.assertTrue(result["justification_admissible"])

    def test_coverage_exactly_on_the_provisional_bound_still_counts(self):
        result = assess_category_two_source(
            proposal_with(conditions=conditions_without("agreed-validation-programme")),
            ASSESS_DAY,
        )
        self.assertAlmostEqual(result["coverage"], PROVISIONAL_COVERAGE, places=9)
        self.assertEqual(result["disposition"], "acceptable-with-open-actions")

    def test_coverage_below_the_bound_is_not_acceptable(self):
        result = assess_category_two_source(
            proposal_with(
                conditions=conditions_without(
                    "agreed-validation-programme", "added-lot-testing"
                )
            ),
            ASSESS_DAY,
        )
        self.assertEqual(result["disposition"], "not-acceptable")

    def test_incomplete_justification_blocks_even_at_full_coverage(self):
        result = assess_category_two_source(
            proposal_with(justification=justification_without("customer-agreement")), ASSESS_DAY
        )
        self.assertEqual(result["disposition"], "not-acceptable")
        self.assertFalse(result["justification_admissible"])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_bypassed_approved_source_blocks_even_at_full_coverage(self):
        result = assess_category_two_source(
            proposal_with(approved_sources=[{"name": "Approved Hybrids Ltd", "available": True}]),
            ASSESS_DAY,
        )
        self.assertEqual(result["disposition"], "not-acceptable")
        self.assertEqual(result["bypassed_approved_sources"], ["Approved Hybrids Ltd"])

    def test_findings_name_each_unmet_condition(self):
        result = assess_category_two_source(
            proposal_with(conditions=conditions_without("added-lot-testing", "agreed-validation-programme")),
            ASSESS_DAY,
        )
        joined = " ".join(result["findings"])
        self.assertIn("added-lot-testing", joined)
        self.assertIn("agreed-validation-programme", joined)

    def test_manufacturer_name_is_carried_through_trimmed(self):
        result = assess_category_two_source(
            proposal_with(manufacturer="  Thickfilm Hybrids SA  "), ASSESS_DAY
        )
        self.assertEqual(result["manufacturer"], "Thickfilm Hybrids SA")

    def test_missing_proposal_key_rejected(self):
        proposal = proposal_with()
        del proposal["justification"]
        with self.assertRaises(ValueError):
            assess_category_two_source(proposal, ASSESS_DAY)

    def test_non_mapping_proposal_rejected(self):
        with self.assertRaises(ValueError):
            assess_category_two_source("Thickfilm Hybrids SA", ASSESS_DAY)

    def test_blank_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            assess_category_two_source(proposal_with(manufacturer="   "), ASSESS_DAY)

    def test_bad_assessment_day_rejected(self):
        with self.assertRaises(ValueError):
            assess_category_two_source(proposal_with(), "some time in autumn")

    def test_coverage_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()

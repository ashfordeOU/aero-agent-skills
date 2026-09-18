"""Contract tests for the clause 6.2.1 form preparation-and-upkeep logic."""

import unittest
from datetime import date

from q6005_identification_form_general_provisions_logic import (
    ACCEPTED_APPROVER_ROLES,
    ALL_CHANGES,
    ALL_ENTRIES,
    DEFAULT_REVIEW_INTERVAL_MONTHS,
    DEFAULT_REVIEW_LEAD_DAYS,
    EDITORIAL_CHANGES,
    MANDATORY_ENTRIES,
    OPTIONAL_ENTRIES,
    PREPARER_ROLE,
    REISSUE_CHANGES,
    VALIDITY_STATES,
    absent_mandatory_entries,
    add_months,
    assess_form_upkeep,
    days_between,
    dominant_change,
    elapsed_review_fraction,
    format_issue,
    next_issue,
    next_review_date,
    normalize_change,
    normalize_entries,
    normalize_token,
    parse_iso_date,
    parse_issue,
    review_state,
    validate_roles,
)


def full_spec(**overrides):
    base = {
        "declared_entries": list(MANDATORY_ENTRIES),
        "preparer_role": "supplier",
        "approver_role": "customer",
        "acceptance_date": "2026-01-15",
        "issue": "2.1",
        "as_of": "2026-06-01",
        "pending_changes": [],
    }
    base.update(overrides)
    return base


class VocabularyTests(unittest.TestCase):
    def test_token_is_trimmed_and_lower_cased(self):
        self.assertEqual(normalize_token(" Supplier ", "preparer role"), "supplier")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("  ", "preparer role")

    def test_entry_vocabulary_partitions(self):
        self.assertEqual(len(ALL_ENTRIES), len(MANDATORY_ENTRIES) + len(OPTIONAL_ENTRIES))
        self.assertEqual(set(MANDATORY_ENTRIES) & set(OPTIONAL_ENTRIES), set())

    def test_change_vocabulary_partitions(self):
        self.assertEqual(len(ALL_CHANGES), len(REISSUE_CHANGES) + len(EDITORIAL_CHANGES))
        self.assertEqual(set(REISSUE_CHANGES) & set(EDITORIAL_CHANGES), set())

    def test_validity_state_vocabulary_is_closed(self):
        self.assertEqual(len(VALIDITY_STATES), 5)
        self.assertIn("reissue-required", VALIDITY_STATES)

    def test_unknown_entry_rejected(self):
        with self.assertRaises(ValueError):
            normalize_entries(["favourite-colour"])

    def test_a_bare_string_is_not_an_entry_sequence(self):
        with self.assertRaises(ValueError):
            normalize_entries("technology-list")

    def test_entries_deduplicated_and_sorted(self):
        got = normalize_entries(["technology-list", "Technology-List", "materials-list"])
        self.assertEqual(got, ["materials-list", "technology-list"])

    def test_unknown_change_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_change("mood-change")


class EntryTests(unittest.TestCase):
    def test_complete_form_has_no_absent_mandatory_entries(self):
        self.assertEqual(absent_mandatory_entries(list(MANDATORY_ENTRIES)), [])

    def test_absent_entries_are_reported_in_vocabulary_order(self):
        declared = [item for item in MANDATORY_ENTRIES if item != "materials-list"]
        self.assertEqual(absent_mandatory_entries(declared), ["materials-list"])

    def test_optional_entry_alone_leaves_every_mandatory_entry_absent(self):
        self.assertEqual(
            len(absent_mandatory_entries(["contact-details"])), len(MANDATORY_ENTRIES)
        )


class RoleTests(unittest.TestCase):
    def test_supplier_prepares_and_customer_accepts(self):
        self.assertEqual(validate_roles("supplier", "customer"), ("supplier", "customer"))

    def test_preparer_role_is_the_supplier(self):
        self.assertEqual(PREPARER_ROLE, "supplier")

    def test_form_prepared_by_the_accepting_party_rejected(self):
        with self.assertRaises(ValueError):
            validate_roles("customer", "customer")

    def test_unaccepted_form_has_no_approver(self):
        self.assertEqual(validate_roles("supplier", None), ("supplier", None))

    def test_a_third_party_cannot_accept_the_form(self):
        with self.assertRaises(ValueError):
            validate_roles("supplier", "test-house")

    def test_procurement_authority_may_accept(self):
        self.assertIn("procurement-authority", ACCEPTED_APPROVER_ROLES)


class IssueTests(unittest.TestCase):
    def test_issue_is_parsed_from_its_identification_string(self):
        self.assertEqual(parse_issue("3.2"), (3, 2))

    def test_issue_below_one_rejected(self):
        with self.assertRaises(ValueError):
            parse_issue("0.4")

    def test_non_numeric_issue_rejected(self):
        with self.assertRaises(ValueError):
            parse_issue("2.a")

    def test_issue_without_a_revision_field_rejected(self):
        with self.assertRaises(ValueError):
            parse_issue("2")

    def test_issue_pair_is_formatted_back(self):
        self.assertEqual(format_issue((4, 0)), "4.0")

    def test_boolean_is_not_an_issue_number(self):
        with self.assertRaises(ValueError):
            format_issue((True, 0))

    def test_technology_change_opens_a_new_issue_and_resets_the_revision(self):
        self.assertEqual(next_issue("2.3", "technology-change"), (3, 0))

    def test_editorial_change_advances_the_revision_only(self):
        self.assertEqual(next_issue("2.3", "document-reformat"), (2, 4))

    def test_no_pending_change_leaves_the_issue_where_it_was(self):
        self.assertEqual(next_issue("2.3", None), (2, 3))

    def test_a_reissue_change_dominates_an_editorial_one(self):
        self.assertEqual(
            dominant_change(["contact-detail-update", "process-change"]),
            "process-change",
        )

    def test_no_pending_change_has_no_dominant_kind(self):
        self.assertIsNone(dominant_change([]))

    def test_a_bare_string_is_not_a_change_sequence(self):
        with self.assertRaises(ValueError):
            dominant_change("process-change")


class DateTests(unittest.TestCase):
    def test_iso_date_is_parsed(self):
        self.assertEqual(parse_iso_date("2026-02-28"), date(2026, 2, 28))

    def test_impossible_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-02-30")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-2-8")

    def test_month_addition_clamps_into_a_shorter_month(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))

    def test_month_addition_rolls_the_year(self):
        self.assertEqual(add_months(date(2026, 11, 15), 3), date(2027, 2, 15))

    def test_negative_month_offset_rejected(self):
        with self.assertRaises(ValueError):
            add_months(date(2026, 1, 1), -1)

    def test_review_date_is_the_interval_after_acceptance(self):
        self.assertEqual(
            next_review_date("2026-01-15", 24).isoformat(), "2028-01-15"
        )

    def test_zero_month_review_interval_rejected(self):
        with self.assertRaises(ValueError):
            next_review_date("2026-01-15", 0)

    def test_day_count_is_signed(self):
        self.assertEqual(days_between("2026-01-01", "2026-01-11"), 10)
        self.assertEqual(days_between("2026-01-11", "2026-01-01"), -10)


class ReviewWindowTests(unittest.TestCase):
    def test_a_fresh_form_is_valid(self):
        state, remaining = review_state("2026-01-15", "2026-06-01", 24, 60)
        self.assertEqual(state, "valid")
        self.assertGreater(remaining, 60)

    def test_inside_the_lead_window_the_review_is_merely_due(self):
        state, remaining = review_state("2026-01-15", "2027-12-15", 24, 60)
        self.assertEqual(state, "review-due")
        self.assertGreaterEqual(remaining, 0)

    def test_the_lead_boundary_itself_counts_as_due(self):
        state, remaining = review_state("2026-01-15", "2027-11-16", 24, 60)
        self.assertEqual(remaining, 60)
        self.assertEqual(state, "review-due")

    def test_past_the_due_date_the_review_is_overdue(self):
        state, remaining = review_state("2026-01-15", "2028-03-01", 24, 60)
        self.assertEqual(state, "review-overdue")
        self.assertLess(remaining, 0)

    def test_negative_lead_window_rejected(self):
        with self.assertRaises(ValueError):
            review_state("2026-01-15", "2026-06-01", 24, -1)

    def test_elapsed_fraction_is_zero_on_the_acceptance_date(self):
        got = elapsed_review_fraction("2026-01-15", "2026-01-15", 24)
        self.assertAlmostEqual(got, 0.0, places=9)

    def test_elapsed_fraction_is_one_on_the_review_date(self):
        got = elapsed_review_fraction("2026-01-15", "2028-01-15", 24)
        self.assertAlmostEqual(got, 1.0, places=9)

    def test_default_upkeep_parameters_are_exposed(self):
        self.assertEqual(DEFAULT_REVIEW_INTERVAL_MONTHS, 24)
        self.assertEqual(DEFAULT_REVIEW_LEAD_DAYS, 60)


class UpkeepAssessmentTests(unittest.TestCase):
    def test_a_complete_accepted_fresh_form_is_clean(self):
        result = assess_form_upkeep(full_spec())
        self.assertEqual(result["validity_state"], "valid")
        self.assertTrue(result["upkeep_clean"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_mandatory_entry_is_a_finding(self):
        declared = [item for item in MANDATORY_ENTRIES if item != "technology-list"]
        result = assess_form_upkeep(full_spec(declared_entries=declared))
        self.assertIn("technology-list", result["absent_mandatory_entries"])
        self.assertFalse(result["upkeep_clean"])

    def test_a_pending_process_change_forces_a_reissue(self):
        result = assess_form_upkeep(full_spec(pending_changes=["process-change"]))
        self.assertEqual(result["validity_state"], "reissue-required")
        self.assertEqual(result["next_issue"], "3.0")

    def test_an_editorial_change_does_not_force_a_reissue(self):
        result = assess_form_upkeep(full_spec(pending_changes=["contact-detail-update"]))
        self.assertEqual(result["validity_state"], "valid")
        self.assertEqual(result["next_issue"], "2.2")

    def test_an_overdue_review_is_reported(self):
        result = assess_form_upkeep(full_spec(as_of="2028-06-01"))
        self.assertEqual(result["validity_state"], "review-overdue")
        self.assertLess(result["days_to_review"], 0)

    def test_a_reissue_outranks_an_overdue_review(self):
        result = assess_form_upkeep(
            full_spec(as_of="2028-06-01", pending_changes=["package-change"])
        )
        self.assertEqual(result["validity_state"], "reissue-required")

    def test_an_unaccepted_form_has_no_review_window(self):
        result = assess_form_upkeep(
            full_spec(approver_role=None, acceptance_date=None)
        )
        self.assertEqual(result["validity_state"], "not-accepted")
        self.assertIsNone(result["next_review_date"])
        self.assertIsNone(result["days_to_review"])

    def test_an_acceptance_date_without_an_accepting_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_form_upkeep(full_spec(approver_role=None))

    def test_an_accepting_role_without_an_acceptance_date_rejected(self):
        with self.assertRaises(ValueError):
            assess_form_upkeep(full_spec(acceptance_date=None))

    def test_the_next_review_date_is_carried_in_the_result(self):
        result = assess_form_upkeep(full_spec())
        self.assertEqual(result["next_review_date"], "2028-01-15")

    def test_a_project_set_interval_moves_the_review_date(self):
        result = assess_form_upkeep(full_spec(review_interval_months=12))
        self.assertEqual(result["next_review_date"], "2027-01-15")

    def test_spec_missing_a_key_rejected(self):
        spec = full_spec()
        del spec["issue"]
        with self.assertRaises(ValueError):
            assess_form_upkeep(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_form_upkeep(["declared_entries"])


if __name__ == "__main__":
    unittest.main()

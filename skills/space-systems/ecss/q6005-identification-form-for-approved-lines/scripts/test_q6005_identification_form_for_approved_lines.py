"""Contract tests for the clause 6.2.2 approved-line form completion logic."""

import unittest
from datetime import date

from q6005_identification_form_for_approved_lines_logic import (
    APPROVAL_TECHNOLOGIES,
    COMPLETION_ROUTES,
    FULL_ENTRIES_ALWAYS,
    LINE_APPROVAL_STATES,
    LIVE_APPROVAL_STATE,
    REDUCED_FORM_ADDITIONS,
    REDUCIBLE_ENTRIES,
    absent_entries,
    approval_in_date,
    approval_window_days,
    assess_approved_line_form,
    completion_route,
    days_of_validity_remaining,
    entries_required_in_full,
    normalize_status,
    normalize_technologies,
    normalize_token,
    parse_iso_date,
    permitted_reduced_entries,
    reduction_permitted,
    required_declared_entries,
    scope_coverage_percent,
    uncovered_technologies,
)

ORDERED = ["thick-film-substrate", "gold-wire-bonding", "seam-welded-package"]

WIDE_SCOPE = [
    "thick-film-substrate",
    "gold-wire-bonding",
    "seam-welded-package",
    "eutectic-die-attach",
]


def full_spec(**overrides):
    base = {
        "line_status": "approved",
        "approval_issue_date": "2025-03-01",
        "approval_expiry_date": "2028-03-01",
        "approval_scope": list(WIDE_SCOPE),
        "requested_technologies": list(ORDERED),
        "order_date": "2026-09-01",
        "declared_entries": list(required_declared_entries(True)),
    }
    base.update(overrides)
    return base


class VocabularyTests(unittest.TestCase):
    def test_token_is_trimmed_and_lower_cased(self):
        self.assertEqual(normalize_token(" Approved ", "line approval state"), "approved")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "line approval state")

    def test_status_vocabulary_is_closed(self):
        self.assertEqual(normalize_status(" Approval-Suspended "), "approval-suspended")
        with self.assertRaises(ValueError):
            normalize_status("provisionally-blessed")

    def test_only_one_state_is_a_live_approval(self):
        self.assertIn(LIVE_APPROVAL_STATE, LINE_APPROVAL_STATES)
        self.assertEqual(LIVE_APPROVAL_STATE, "approved")

    def test_entry_sets_do_not_overlap(self):
        self.assertEqual(set(FULL_ENTRIES_ALWAYS) & set(REDUCIBLE_ENTRIES), set())
        self.assertEqual(set(FULL_ENTRIES_ALWAYS) & set(REDUCED_FORM_ADDITIONS), set())

    def test_completion_route_vocabulary_is_closed(self):
        self.assertEqual(len(COMPLETION_ROUTES), 2)

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            normalize_technologies(["unobtainium-bonding"])

    def test_empty_requested_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_technologies([])

    def test_empty_scope_allowed_when_explicitly_permitted(self):
        self.assertEqual(normalize_technologies([], "approved technology", True), [])

    def test_a_bare_string_is_not_a_technology_sequence(self):
        with self.assertRaises(ValueError):
            normalize_technologies("gold-wire-bonding")

    def test_technologies_deduplicated_and_sorted(self):
        got = normalize_technologies(["gold-wire-bonding", "Gold-Wire-Bonding"])
        self.assertEqual(got, ["gold-wire-bonding"])

    def test_approval_technology_vocabulary_has_no_duplicates(self):
        self.assertEqual(len(set(APPROVAL_TECHNOLOGIES)), len(APPROVAL_TECHNOLOGIES))


class ApprovalWindowTests(unittest.TestCase):
    def test_iso_date_is_parsed(self):
        self.assertEqual(parse_iso_date("2026-09-01"), date(2026, 9, 1))

    def test_impossible_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-13-01")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("01/09/2026")

    def test_window_span_is_a_whole_day_count(self):
        self.assertEqual(approval_window_days("2026-01-01", "2026-01-31"), 30)

    def test_inverted_approval_window_rejected(self):
        with self.assertRaises(ValueError):
            approval_window_days("2028-03-01", "2025-03-01")

    def test_zero_length_approval_window_rejected(self):
        with self.assertRaises(ValueError):
            approval_window_days("2026-01-01", "2026-01-01")

    def test_order_inside_the_window_is_in_date(self):
        self.assertTrue(approval_in_date("2025-03-01", "2028-03-01", "2026-09-01"))

    def test_order_on_the_expiry_date_is_still_in_date(self):
        self.assertTrue(approval_in_date("2025-03-01", "2028-03-01", "2028-03-01"))

    def test_order_before_the_approval_came_into_force_is_not_covered(self):
        self.assertFalse(approval_in_date("2025-03-01", "2028-03-01", "2024-12-01"))

    def test_order_after_expiry_is_not_covered(self):
        self.assertFalse(approval_in_date("2025-03-01", "2028-03-01", "2028-03-02"))

    def test_remaining_validity_is_signed(self):
        self.assertEqual(days_of_validity_remaining("2026-01-31", "2026-01-01"), 30)
        self.assertEqual(days_of_validity_remaining("2026-01-01", "2026-01-31"), -30)


class ScopeTests(unittest.TestCase):
    def test_a_covered_order_has_no_uncovered_technology(self):
        self.assertEqual(uncovered_technologies(ORDERED, WIDE_SCOPE), [])

    def test_a_technology_outside_the_scope_is_reported(self):
        got = uncovered_technologies(ORDERED, ["thick-film-substrate"])
        self.assertEqual(got, ["gold-wire-bonding", "seam-welded-package"])

    def test_a_scope_wider_than_the_order_is_not_a_finding(self):
        self.assertEqual(uncovered_technologies(["gold-wire-bonding"], WIDE_SCOPE), [])

    def test_full_coverage_is_one_hundred_percent(self):
        self.assertAlmostEqual(scope_coverage_percent(ORDERED, WIDE_SCOPE), 100.0, places=9)

    def test_empty_scope_is_zero_percent(self):
        self.assertAlmostEqual(scope_coverage_percent(ORDERED, []), 0.0, places=9)

    def test_partial_coverage_lands_on_the_expected_fraction(self):
        got = scope_coverage_percent(ORDERED, ["thick-film-substrate"])
        self.assertAlmostEqual(got, 100.0 / 3.0, places=9)


class ReductionTests(unittest.TestCase):
    def test_a_live_in_date_full_scope_approval_permits_reduction(self):
        self.assertTrue(reduction_permitted("approved", True, []))

    def test_a_suspended_approval_permits_nothing(self):
        self.assertFalse(reduction_permitted("approval-suspended", True, []))

    def test_a_lapsed_approval_permits_nothing(self):
        self.assertFalse(reduction_permitted("approved", False, []))

    def test_a_partial_scope_match_permits_nothing(self):
        self.assertFalse(reduction_permitted("approved", True, ["gold-wire-bonding"]))

    def test_non_boolean_in_date_rejected(self):
        with self.assertRaises(ValueError):
            reduction_permitted("approved", "yes", [])

    def test_route_follows_the_reduction_decision(self):
        self.assertEqual(completion_route(True), "reduced-completion")
        self.assertEqual(completion_route(False), "full-form-fallback")

    def test_non_boolean_route_input_rejected(self):
        with self.assertRaises(ValueError):
            completion_route("maybe")


class EntrySetTests(unittest.TestCase):
    def test_reduced_route_may_answer_the_reducible_entries_by_reference(self):
        self.assertEqual(permitted_reduced_entries(True), tuple(sorted(REDUCIBLE_ENTRIES)))

    def test_fallback_route_may_reduce_nothing(self):
        self.assertEqual(permitted_reduced_entries(False), ())

    def test_fallback_route_writes_out_the_reducible_entries_too(self):
        in_full = entries_required_in_full(False)
        for item in REDUCIBLE_ENTRIES:
            self.assertIn(item, in_full)

    def test_reduced_route_still_writes_out_the_always_full_entries(self):
        in_full = entries_required_in_full(True)
        for item in FULL_ENTRIES_ALWAYS:
            self.assertIn(item, in_full)
        for item in REDUCIBLE_ENTRIES:
            self.assertNotIn(item, in_full)

    def test_reduced_route_owes_the_approval_traceability_entries(self):
        demanded = required_declared_entries(True)
        for item in REDUCED_FORM_ADDITIONS:
            self.assertIn(item, demanded)

    def test_fallback_route_does_not_owe_the_traceability_entries(self):
        demanded = required_declared_entries(False)
        for item in REDUCED_FORM_ADDITIONS:
            self.assertNotIn(item, demanded)

    def test_absent_entries_are_the_demanded_ones_not_declared(self):
        declared = [item for item in required_declared_entries(True) if item != "materials-list"]
        self.assertEqual(absent_entries(declared, True), ["materials-list"])

    def test_a_bare_string_is_not_a_declared_entry_sequence(self):
        with self.assertRaises(ValueError):
            absent_entries("materials-list", True)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_approved_line_takes_the_reduced_route(self):
        result = assess_approved_line_form(full_spec())
        self.assertEqual(result["completion_route"], "reduced-completion")
        self.assertTrue(result["reduction_permitted"])
        self.assertTrue(result["form_acceptable"])

    def test_a_withdrawn_approval_falls_back_to_the_full_form(self):
        result = assess_approved_line_form(
            full_spec(
                line_status="approval-withdrawn",
                declared_entries=list(required_declared_entries(False)),
            )
        )
        self.assertEqual(result["completion_route"], "full-form-fallback")
        self.assertIsNone(result["approval_window_days"])
        self.assertFalse(result["form_acceptable"])

    def test_a_lapsed_approval_reports_how_long_ago_it_lapsed(self):
        result = assess_approved_line_form(
            full_spec(
                order_date="2028-03-31",
                declared_entries=list(required_declared_entries(False)),
            )
        )
        self.assertFalse(result["approval_in_date"])
        self.assertEqual(result["days_of_validity_remaining"], -30)
        self.assertIn("the approval lapsed 30 days before the order", result["findings"])

    def test_an_order_before_the_approval_is_reported_separately(self):
        result = assess_approved_line_form(
            full_spec(
                order_date="2024-12-01",
                declared_entries=list(required_declared_entries(False)),
            )
        )
        self.assertIn(
            "the order was raised before the approval came into force",
            result["findings"],
        )

    def test_a_partial_scope_match_gives_no_reduction(self):
        result = assess_approved_line_form(
            full_spec(
                approval_scope=["thick-film-substrate"],
                declared_entries=list(required_declared_entries(False)),
            )
        )
        self.assertEqual(result["completion_route"], "full-form-fallback")
        self.assertIn(
            "a partial scope match gives no reduction, so the full form is owed",
            result["findings"],
        )

    def test_a_reduced_form_missing_its_approval_reference_is_a_finding(self):
        declared = [
            item
            for item in required_declared_entries(True)
            if item != "line-approval-reference"
        ]
        result = assess_approved_line_form(full_spec(declared_entries=declared))
        self.assertIn("line-approval-reference", result["absent_entries"])
        self.assertFalse(result["form_acceptable"])

    def test_inverted_approval_window_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_approved_line_form(
                full_spec(
                    approval_issue_date="2028-03-01", approval_expiry_date="2025-03-01"
                )
            )

    def test_result_carries_the_scope_coverage(self):
        result = assess_approved_line_form(full_spec())
        self.assertAlmostEqual(result["scope_coverage_percent"], 100.0, places=9)

    def test_spec_missing_a_key_rejected(self):
        spec = full_spec()
        del spec["order_date"]
        with self.assertRaises(ValueError):
            assess_approved_line_form(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_approved_line_form(["line_status"])

    def test_pending_approval_is_not_a_live_one(self):
        result = assess_approved_line_form(
            full_spec(
                line_status="approval-pending",
                declared_entries=list(required_declared_entries(False)),
            )
        )
        self.assertFalse(result["reduction_permitted"])
        self.assertIn(
            "the line is in state 'approval-pending', so nothing may be answered by reference",
            result["findings"],
        )


if __name__ == "__main__":
    unittest.main()

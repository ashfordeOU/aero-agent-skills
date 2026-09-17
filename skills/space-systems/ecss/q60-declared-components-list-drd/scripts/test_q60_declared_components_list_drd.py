"""Contract tests for the Annex B declared components list data item logic."""

import unittest

from q60_declared_components_list_drd_logic import (
    ALLOWED_TRANSITIONS,
    APPROVAL_STATES,
    COVERAGE_TOLERANCE,
    HEADER_FIELDS,
    LINE_FIELDS,
    approval_profile,
    approval_state_facts,
    assess_declared_components_list_drd,
    evaluate_line,
    line_completeness,
    transition_allowed,
    usable_quantity_fraction,
    validate_document_header,
)


def header(**overrides):
    """Return one complete data item header with optional overrides."""
    base = {
        "document_id": "DCL-PCDU-001",
        "issue": "3",
        "equipment_item": "PCDU-A",
        "issue_date": "2026-04-02",
        "approval_authority": "customer product assurance",
    }
    base.update(overrides)
    return base


def line(**overrides):
    """Return one acceptable list line with optional overrides."""
    base = {
        "line_id": "L001",
        "part_type": "voltage-regulator",
        "manufacturer": "supplier-north",
        "part_number": "VR-4410",
        "quantity": 8,
        "procurement_reference": "PS-4410-B",
        "approval_state": "approved",
    }
    base.update(overrides)
    return base


class HeaderTests(unittest.TestCase):
    def test_complete_header_validates(self):
        validated = validate_document_header(header())
        self.assertEqual(validated["document_id"], "DCL-PCDU-001")

    def test_header_values_are_stripped(self):
        validated = validate_document_header(header(issue="  3  "))
        self.assertEqual(validated["issue"], "3")

    def test_missing_approving_authority_rejected(self):
        incomplete = header()
        del incomplete["approval_authority"]
        with self.assertRaises(ValueError):
            validate_document_header(incomplete)

    def test_blank_document_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_document_header(header(document_id="   "))

    def test_non_mapping_header_rejected(self):
        with self.assertRaises(ValueError):
            validate_document_header(["DCL-PCDU-001"])

    def test_every_named_header_field_is_required(self):
        for field in HEADER_FIELDS:
            incomplete = header()
            del incomplete[field]
            with self.assertRaises(ValueError):
                validate_document_header(incomplete)


class ApprovalStateTests(unittest.TestCase):
    def test_approved_is_decided_and_permits_use(self):
        facts = approval_state_facts("approved")
        self.assertTrue(facts["decided"])
        self.assertTrue(facts["permits_use"])

    def test_rejection_is_a_decision_that_refuses_the_part(self):
        facts = approval_state_facts("rejected")
        self.assertTrue(facts["decided"])
        self.assertFalse(facts["permits_use"])

    def test_under_review_is_not_yet_decided(self):
        self.assertFalse(approval_state_facts("under-review")["decided"])

    def test_state_lookup_is_case_insensitive(self):
        self.assertEqual(approval_state_facts("APPROVED")["state"], "approved")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            approval_state_facts("signed-off-verbally")

    def test_every_known_state_answers_both_facts(self):
        for state in APPROVAL_STATES:
            facts = approval_state_facts(state)
            self.assertIsInstance(facts["decided"], bool)
            self.assertIsInstance(facts["permits_use"], bool)


class TransitionTests(unittest.TestCase):
    def test_review_may_end_in_approval(self):
        self.assertTrue(transition_allowed("under-review", "approved"))

    def test_approval_without_review_is_forbidden(self):
        self.assertFalse(transition_allowed("proposed", "approved"))

    def test_nothing_leaves_a_withdrawn_entry(self):
        self.assertEqual(ALLOWED_TRANSITIONS["withdrawn"], ())
        self.assertFalse(transition_allowed("withdrawn", "under-review"))

    def test_a_refusal_may_be_resubmitted_for_review(self):
        self.assertTrue(transition_allowed("rejected", "under-review"))

    def test_staying_in_one_state_is_allowed(self):
        self.assertTrue(transition_allowed("approved", "approved"))

    def test_unknown_state_in_a_transition_rejected(self):
        with self.assertRaises(ValueError):
            transition_allowed("under-review", "rubber-stamped")


class LineCompletenessTests(unittest.TestCase):
    def test_complete_line_scores_one(self):
        missing, fraction = line_completeness(line())
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_missing_procurement_reference_reported(self):
        incomplete = line()
        del incomplete["procurement_reference"]
        missing, fraction = line_completeness(incomplete)
        self.assertIn("procurement_reference", missing)
        self.assertAlmostEqual(
            fraction, (len(LINE_FIELDS) - 1) / len(LINE_FIELDS), places=9
        )

    def test_blank_string_counts_as_missing(self):
        missing, _ = line_completeness(line(manufacturer="   "))
        self.assertIn("manufacturer", missing)

    def test_none_counts_as_missing(self):
        missing, _ = line_completeness(line(part_number=None))
        self.assertIn("part_number", missing)

    def test_non_mapping_line_rejected(self):
        with self.assertRaises(ValueError):
            line_completeness("L001")


class EvaluateLineTests(unittest.TestCase):
    def test_clean_line_is_accepted(self):
        record = evaluate_line(line())
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["accepted"])

    def test_incomplete_line_is_not_graded_further(self):
        record = evaluate_line(line(quantity=None))
        self.assertEqual(record["disposition"], "record-incomplete")
        self.assertIsNone(record["approval_state"])

    def test_unknown_state_is_its_own_disposition(self):
        record = evaluate_line(line(approval_state="verbally-agreed"))
        self.assertEqual(record["disposition"], "unknown-approval-state")

    def test_forbidden_transition_is_reported(self):
        record = evaluate_line(
            line(previous_approval_state="proposed", approval_state="approved")
        )
        self.assertEqual(record["disposition"], "invalid-transition")

    def test_allowed_transition_still_accepts(self):
        record = evaluate_line(
            line(previous_approval_state="under-review", approval_state="approved")
        )
        self.assertEqual(record["disposition"], "accepted")
        self.assertEqual(record["previous_state"], "under-review")

    def test_conditional_approval_without_conditions_is_blocked(self):
        record = evaluate_line(line(approval_state="approved-with-conditions"))
        self.assertEqual(record["disposition"], "condition-not-recorded")

    def test_conditional_approval_with_conditions_is_accepted(self):
        record = evaluate_line(
            line(
                approval_state="approved-with-conditions",
                conditions="derate the output stage to 60 percent",
            )
        )
        self.assertEqual(record["disposition"], "accepted")

    def test_undecided_entry_is_outstanding_not_refused(self):
        record = evaluate_line(line(approval_state="under-review"))
        self.assertEqual(record["disposition"], "decision-outstanding")

    def test_refusal_and_withdrawal_are_separate_dispositions(self):
        refused = evaluate_line(line(approval_state="rejected"))
        withdrawn = evaluate_line(line(approval_state="withdrawn"))
        self.assertEqual(refused["disposition"], "part-rejected")
        self.assertEqual(withdrawn["disposition"], "part-withdrawn")
        self.assertNotEqual(refused["disposition"], withdrawn["disposition"])

    def test_repeat_of_a_seen_entry_is_a_duplicate(self):
        key = ("voltage-regulator", "supplier-north", "vr-4410")
        record = evaluate_line(line(line_id="L002"), seen_keys={key})
        self.assertEqual(record["disposition"], "duplicate-entry")

    def test_non_positive_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line(line(quantity=0))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_line(line(quantity=True))


class ProfileAndFractionTests(unittest.TestCase):
    def test_profile_counts_each_state(self):
        records = [
            evaluate_line(line()),
            evaluate_line(line(line_id="L002", approval_state="under-review")),
        ]
        profile = approval_profile(records)
        self.assertEqual(profile["approved"], 1)
        self.assertEqual(profile["under-review"], 1)
        self.assertEqual(profile["rejected"], 0)

    def test_fraction_is_weighted_by_quantity_not_by_line_count(self):
        records = [
            evaluate_line(line(quantity=90)),
            evaluate_line(
                line(
                    line_id="L002",
                    part_number="VR-4411",
                    quantity=10,
                    approval_state="under-review",
                )
            ),
        ]
        self.assertAlmostEqual(usable_quantity_fraction(records), 0.9, places=9)

    def test_fraction_is_one_when_every_line_is_accepted(self):
        records = [evaluate_line(line())]
        self.assertAlmostEqual(usable_quantity_fraction(records), 1.0, places=9)

    def test_fraction_rejects_an_empty_record_set(self):
        with self.assertRaises(ValueError):
            usable_quantity_fraction([])

    def test_fraction_rejects_a_record_without_a_disposition(self):
        with self.assertRaises(ValueError):
            usable_quantity_fraction([{"quantity": 4}])

    def test_profile_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            approval_profile("records")


class AssessmentTests(unittest.TestCase):
    def _spec(self, lines=None, **overrides):
        spec = {"header": header(), "lines": [line()] if lines is None else lines}
        spec.update(overrides)
        return spec

    def test_clean_list_releases(self):
        result = assess_declared_components_list_drd(self._spec())
        self.assertEqual(result["verdict"], "release")
        self.assertTrue(result["releasable"])
        self.assertEqual(result["findings"], [])

    def test_outstanding_decision_holds_the_list(self):
        result = assess_declared_components_list_drd(
            self._spec(lines=[line(approval_state="proposed")])
        )
        self.assertEqual(result["verdict"], "hold")
        self.assertEqual(result["findings"][0]["disposition"], "decision-outstanding")

    def test_findings_are_ranked_worst_first(self):
        result = assess_declared_components_list_drd(
            self._spec(
                lines=[
                    line(approval_state="rejected"),
                    line(line_id="L002", part_number="VR-4411", quantity=None),
                ]
            )
        )
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))
        self.assertEqual(result["findings"][0]["disposition"], "record-incomplete")

    def test_duplicate_entry_found_across_lines(self):
        result = assess_declared_components_list_drd(
            self._spec(lines=[line(), line(line_id="L002")])
        )
        dispositions = [entry["disposition"] for entry in result["findings"]]
        self.assertIn("duplicate-entry", dispositions)

    def test_repeated_line_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(
                self._spec(lines=[line(), line(part_number="VR-4411")])
            )

    def test_exactly_met_requirement_releases_nothing_when_findings_remain(self):
        result = assess_declared_components_list_drd(
            self._spec(
                lines=[
                    line(quantity=90),
                    line(
                        line_id="L002",
                        part_number="VR-4411",
                        quantity=10,
                        approval_state="under-review",
                    ),
                ],
                required_usable_fraction=0.9,
            )
        )
        self.assertAlmostEqual(result["usable_quantity_fraction"], 0.9, places=9)
        self.assertEqual(result["verdict"], "hold")

    def test_all_incomplete_list_reports_rather_than_raises(self):
        result = assess_declared_components_list_drd(
            self._spec(lines=[line(quantity=None)])
        )
        self.assertAlmostEqual(result["usable_quantity_fraction"], 0.0, places=9)
        self.assertEqual(result["verdict"], "hold")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)

    def test_missing_lines_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd({"header": header()})

    def test_empty_line_sequence_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(self._spec(lines=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(["header"])

    def test_out_of_range_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(
                self._spec(required_usable_fraction=1.4)
            )

    def test_boolean_required_fraction_rejected(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(
                self._spec(required_usable_fraction=False)
            )


if __name__ == "__main__":
    unittest.main()

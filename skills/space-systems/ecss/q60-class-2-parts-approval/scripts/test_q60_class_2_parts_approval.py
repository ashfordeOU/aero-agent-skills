"""Contract test for the ECSS-Q-ST-60C clause 5.2.4 Class 2 approval leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_2_parts_approval.py
"""

import unittest

from q60_class_2_parts_approval_logic import (
    APPROVAL_VALIDITY_MONTHS,
    GATE_ORDER,
    GOVERNING_GATE,
    PART_STATUSES,
    PROCUREMENT_ROLES,
    PROJECT_GATES,
    REQUIRED_APPROVAL_DOCUMENTS,
    REQUIRED_JUSTIFICATION_FIELDS,
    TARGET_CATEGORY,
    VALIDITY_TOLERANCE,
    approval_is_timely,
    assess_class_2_parts_approval,
    assess_part_approval,
    gate_index,
    governing_gate,
    missing_approval_documents,
    missing_justification_fields,
    normalize_approval,
    normalize_conditions,
    open_conditions,
)


def full_approval(**overrides):
    """An approval carrying everything, granted in good time."""
    approval = {
        "granted_at_gate": "preliminary-design-review",
        "approval_age_months": 6.0,
        "conditional": False,
        "conditions": [],
        "justification_fields": list(REQUIRED_JUSTIFICATION_FIELDS),
        "documents": list(REQUIRED_APPROVAL_DOCUMENTS),
    }
    approval.update(overrides)
    return approval


def proposed_part(**overrides):
    part = {
        "part_number": "rnc55h1002fs",
        "procurement_role": "standard-catalogue-procurement",
        "declared_category": TARGET_CATEGORY,
        "approval": full_approval(),
    }
    part.update(overrides)
    return part


class GateTests(unittest.TestCase):
    def test_the_gate_sequence_has_no_repeated_entry(self):
        self.assertEqual(len(PROJECT_GATES), len(set(PROJECT_GATES)))

    def test_the_gate_order_covers_every_gate(self):
        self.assertEqual(set(GATE_ORDER), set(PROJECT_GATES))

    def test_the_gates_are_indexed_in_the_order_they_occur(self):
        indices = [gate_index(gate) for gate in PROJECT_GATES]
        self.assertEqual(indices, sorted(indices))

    def test_every_procurement_role_names_a_real_gate(self):
        for role in PROCUREMENT_ROLES:
            self.assertIn(governing_gate(role), PROJECT_GATES)

    def test_a_long_lead_part_is_governed_earlier_than_a_catalogue_part(self):
        self.assertLess(
            gate_index(governing_gate("long-lead-procurement")),
            gate_index(governing_gate("standard-catalogue-procurement")),
        )

    def test_an_unknown_procurement_role_is_rejected(self):
        with self.assertRaises(ValueError):
            governing_gate("someone-just-ordered-it")

    def test_an_unknown_gate_is_rejected(self):
        with self.assertRaises(ValueError):
            gate_index("the-weekly-meeting")

    def test_an_approval_at_its_governing_gate_is_timely(self):
        role = "standard-catalogue-procurement"
        self.assertTrue(approval_is_timely(GOVERNING_GATE[role], role))

    def test_an_approval_before_its_governing_gate_is_timely(self):
        self.assertTrue(
            approval_is_timely(
                "preliminary-design-review", "standard-catalogue-procurement"
            )
        )

    def test_an_approval_after_its_governing_gate_is_late(self):
        self.assertFalse(
            approval_is_timely(
                "flight-acceptance-review", "standard-catalogue-procurement"
            )
        )


class JustificationTests(unittest.TestCase):
    def test_a_complete_record_leaves_no_field_missing(self):
        self.assertEqual(
            missing_justification_fields(list(REQUIRED_JUSTIFICATION_FIELDS)), ()
        )

    def test_each_absent_field_is_named_separately(self):
        supplied = list(REQUIRED_JUSTIFICATION_FIELDS[:2])
        missing = missing_justification_fields(supplied)
        self.assertEqual(len(missing), len(REQUIRED_JUSTIFICATION_FIELDS) - 2)

    def test_an_empty_record_is_missing_everything(self):
        self.assertEqual(
            missing_justification_fields([]), REQUIRED_JUSTIFICATION_FIELDS
        )

    def test_a_repeated_field_does_not_count_twice(self):
        supplied = [REQUIRED_JUSTIFICATION_FIELDS[0], REQUIRED_JUSTIFICATION_FIELDS[0]]
        missing = missing_justification_fields(supplied)
        self.assertEqual(len(missing), len(REQUIRED_JUSTIFICATION_FIELDS) - 1)

    def test_an_unknown_field_name_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_justification_fields(["it-seemed-like-a-good-part"])

    def test_a_bare_string_is_not_a_field_list(self):
        with self.assertRaises(ValueError):
            missing_justification_fields(REQUIRED_JUSTIFICATION_FIELDS[0])


class DocumentTests(unittest.TestCase):
    def test_a_complete_submission_leaves_no_document_missing(self):
        self.assertEqual(
            missing_approval_documents(list(REQUIRED_APPROVAL_DOCUMENTS)), ()
        )

    def test_each_absent_document_is_named_separately(self):
        missing = missing_approval_documents([REQUIRED_APPROVAL_DOCUMENTS[0]])
        self.assertEqual(len(missing), len(REQUIRED_APPROVAL_DOCUMENTS) - 1)

    def test_the_document_set_is_separate_from_the_justification_set(self):
        self.assertEqual(
            set(REQUIRED_APPROVAL_DOCUMENTS) & set(REQUIRED_JUSTIFICATION_FIELDS), set()
        )

    def test_an_unknown_document_name_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_approval_documents(["an-email-from-the-supplier"])


class ConditionTests(unittest.TestCase):
    def test_a_closed_condition_is_not_open(self):
        conditions = [{"condition_id": "c1", "closure_record_present": True}]
        self.assertEqual(open_conditions(conditions), ())

    def test_an_unclosed_condition_stays_open(self):
        conditions = [{"condition_id": "c1", "closure_record_present": False}]
        self.assertEqual(open_conditions(conditions), ("c1",))

    def test_every_open_condition_is_named_at_once(self):
        conditions = [
            {"condition_id": "c1", "closure_record_present": False},
            {"condition_id": "c2", "closure_record_present": True},
            {"condition_id": "c3", "closure_record_present": False},
        ]
        self.assertEqual(open_conditions(conditions), ("c1", "c3"))

    def test_a_duplicate_condition_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_conditions(
                [
                    {"condition_id": "c1", "closure_record_present": True},
                    {"condition_id": "c1", "closure_record_present": False},
                ]
            )

    def test_a_condition_without_a_closure_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_conditions([{"condition_id": "c1"}])

    def test_a_conditional_approval_carrying_no_condition_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval(full_approval(conditional=True, conditions=[]))

    def test_conditions_attached_to_an_unconditional_approval_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval(
                full_approval(
                    conditional=False,
                    conditions=[{"condition_id": "c1", "closure_record_present": True}],
                )
            )

    def test_a_negative_approval_age_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval(full_approval(approval_age_months=-1.0))

    def test_a_non_mapping_approval_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval("approved by email")


class PartStatusTests(unittest.TestCase):
    def test_a_complete_timely_approval_releases_the_part(self):
        record = assess_part_approval(proposed_part())
        self.assertEqual(record["status"], "class-2-part-released-for-flight")
        self.assertTrue(record["released"])
        self.assertEqual(record["findings"], [])

    def test_a_part_never_submitted_is_not_approved(self):
        record = assess_part_approval(proposed_part(approval=None))
        self.assertEqual(record["status"], "class-2-part-not-approved")
        self.assertIn(
            "proposed-part-never-submitted-for-approval",
            [f["finding"] for f in record["findings"]],
        )

    def test_a_part_never_submitted_is_missing_the_whole_evidence_set(self):
        record = assess_part_approval(proposed_part(approval=None))
        self.assertEqual(
            record["missing_justification_fields"],
            list(REQUIRED_JUSTIFICATION_FIELDS),
        )
        self.assertEqual(
            record["missing_approval_documents"], list(REQUIRED_APPROVAL_DOCUMENTS)
        )

    def test_an_incomplete_justification_blocks_release(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(
                    justification_fields=list(REQUIRED_JUSTIFICATION_FIELDS[:3])
                )
            )
        )
        self.assertEqual(record["status"], "class-2-part-approval-incomplete")
        self.assertIn(
            "justification-record-incomplete",
            [f["finding"] for f in record["findings"]],
        )

    def test_a_missing_document_blocks_release_on_its_own(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(
                    documents=list(REQUIRED_APPROVAL_DOCUMENTS[:2])
                )
            )
        )
        self.assertEqual(record["status"], "class-2-part-approval-incomplete")
        self.assertIn(
            "approval-document-missing", [f["finding"] for f in record["findings"]]
        )

    def test_an_approval_after_its_governing_gate_blocks_release(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(granted_at_gate="flight-acceptance-review")
            )
        )
        self.assertEqual(record["status"], "class-2-part-approval-incomplete")
        self.assertIn(
            "approval-later-than-governing-gate",
            [f["finding"] for f in record["findings"]],
        )

    def test_a_late_substitution_is_allowed_a_later_gate(self):
        record = assess_part_approval(
            proposed_part(
                procurement_role="late-substitution",
                approval=full_approval(granted_at_gate="qualification-review"),
            )
        )
        self.assertEqual(record["status"], "class-2-part-released-for-flight")

    def test_an_approval_on_the_validity_edge_still_releases(self):
        age = APPROVAL_VALIDITY_MONTHS
        self.assertAlmostEqual(age, APPROVAL_VALIDITY_MONTHS, places=9)
        record = assess_part_approval(
            proposed_part(approval=full_approval(approval_age_months=age))
        )
        self.assertEqual(record["status"], "class-2-part-released-for-flight")

    def test_an_approval_past_its_validity_window_blocks_release(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(
                    approval_age_months=APPROVAL_VALIDITY_MONTHS + 12.0
                )
            )
        )
        self.assertEqual(record["status"], "class-2-part-approval-incomplete")
        self.assertIn(
            "approval-outside-validity-window",
            [f["finding"] for f in record["findings"]],
        )

    def test_a_conditional_approval_with_an_open_condition_releases_nothing(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(
                    conditional=True,
                    conditions=[
                        {"condition_id": "c1", "closure_record_present": False}
                    ],
                )
            )
        )
        self.assertEqual(record["status"], "class-2-part-conditionally-approved")
        self.assertFalse(record["released"])
        self.assertEqual(record["open_conditions"], ["c1"])

    def test_a_conditional_approval_with_every_condition_closed_releases(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(
                    conditional=True,
                    conditions=[
                        {"condition_id": "c1", "closure_record_present": True},
                        {"condition_id": "c2", "closure_record_present": True},
                    ],
                )
            )
        )
        self.assertEqual(record["status"], "class-2-part-released-for-flight")

    def test_a_part_declared_in_another_category_is_not_released_here(self):
        record = assess_part_approval(proposed_part(declared_category="class-3"))
        self.assertEqual(record["status"], "class-2-part-approval-incomplete")
        self.assertIn(
            "declared-category-is-not-the-one-being-released",
            [f["finding"] for f in record["findings"]],
        )

    def test_every_blocking_reason_is_reported_at_once(self):
        record = assess_part_approval(
            proposed_part(
                approval=full_approval(
                    granted_at_gate="flight-acceptance-review",
                    approval_age_months=APPROVAL_VALIDITY_MONTHS + 6.0,
                    documents=[],
                )
            )
        )
        findings = [f["finding"] for f in record["findings"]]
        self.assertIn("approval-later-than-governing-gate", findings)
        self.assertIn("approval-outside-validity-window", findings)
        self.assertIn("approval-document-missing", findings)

    def test_every_status_name_is_one_the_module_publishes(self):
        self.assertIn(assess_part_approval(proposed_part())["status"], PART_STATUSES)
        self.assertIn(
            assess_part_approval(proposed_part(approval=None))["status"], PART_STATUSES
        )

    def test_an_empty_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_approval(proposed_part(part_number="  "))

    def test_a_non_mapping_part_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_part_approval("rnc55h1002fs")


class ProposedListTests(unittest.TestCase):
    def test_a_list_whose_parts_all_cleared_is_releasable(self):
        report = assess_class_2_parts_approval(
            "sat-b",
            [proposed_part(), proposed_part(part_number="cdr02-1n5711")],
        )
        self.assertTrue(report["list_releasable"])
        self.assertEqual(len(report["released_parts"]), 2)
        self.assertEqual(report["blocked_parts"], [])

    def test_one_unsubmitted_part_blocks_the_whole_list(self):
        report = assess_class_2_parts_approval(
            "sat-b",
            [
                proposed_part(),
                proposed_part(part_number="cdr02-1n5711", approval=None),
            ],
        )
        self.assertFalse(report["list_releasable"])
        self.assertEqual(report["blocked_parts"], ["cdr02-1n5711"])

    def test_the_status_counts_add_up_to_the_proposed_list(self):
        parts = [
            proposed_part(),
            proposed_part(part_number="cdr02-1n5711", approval=None),
            proposed_part(
                part_number="cdr03-2n2222",
                approval=full_approval(
                    conditional=True,
                    conditions=[
                        {"condition_id": "c1", "closure_record_present": False}
                    ],
                ),
            ),
        ]
        report = assess_class_2_parts_approval("sat-b", parts)
        self.assertEqual(sum(report["status_counts"].values()), 3)
        self.assertEqual(
            report["status_counts"]["class-2-part-released-for-flight"], 1
        )
        self.assertEqual(report["status_counts"]["class-2-part-not-approved"], 1)
        self.assertEqual(
            report["status_counts"]["class-2-part-conditionally-approved"], 1
        )

    def test_a_repeated_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_parts_approval("sat-b", [proposed_part(), proposed_part()])

    def test_an_empty_proposed_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_parts_approval("sat-b", [])

    def test_an_empty_programme_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_parts_approval("  ", [proposed_part()])

    def test_a_non_sequence_proposed_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_parts_approval("sat-b", {"part_number": "x"})

    def test_tolerance_is_small_enough_to_separate_the_validity_edge(self):
        self.assertLess(VALIDITY_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()

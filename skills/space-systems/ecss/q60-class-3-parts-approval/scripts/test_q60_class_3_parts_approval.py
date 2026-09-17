"""Contract test for the ECSS-Q-ST-60C clause 6.2.4 Class 3 approval leaf.

Offline, deterministic, stdlib unittest.
Run: python3 test_q60_class_3_parts_approval.py
"""

import unittest

from q60_class_3_parts_approval_logic import (
    CUSTOMER_DECISIONS,
    INVOCATION_RULES,
    PART_STATUSES,
    REQUIRED_SUBMISSION_ITEMS,
    RESPONSE_TOLERANCE,
    RESPONSE_WINDOW_WORKING_DAYS,
    TARGET_CATEGORY,
    USABLE_STATUSES,
    assess_class_3_parts_approval,
    assess_proposed_part,
    customer_review_invoked,
    invocation_reasons,
    missing_submission_items,
    normalize_restrictions,
    normalize_submission,
    open_restrictions,
    response_window_elapsed,
)


def full_submission(**overrides):
    """A submission carrying everything, approved outright."""
    submission = {
        "customer_decision": "approved",
        "elapsed_working_days": 8.0,
        "restrictions": [],
        "items": list(REQUIRED_SUBMISSION_ITEMS),
    }
    submission.update(overrides)
    return submission


def proposed_part(**overrides):
    """A proposed part that did invoke a review and cleared it."""
    part = {
        "part_number": "cot31-lm4040",
        "declared_category": TARGET_CATEGORY,
        "invocation_flags": ["part-type-new-to-the-project"],
        "submission": full_submission(),
    }
    part.update(overrides)
    return part


class InvocationTests(unittest.TestCase):
    def test_the_invocation_rule_list_has_no_repeated_entry(self):
        self.assertEqual(len(INVOCATION_RULES), len(set(INVOCATION_RULES)))

    def test_a_part_that_triggered_nothing_does_not_invoke_review(self):
        self.assertFalse(customer_review_invoked([]))

    def test_a_single_triggered_rule_invokes_review(self):
        self.assertTrue(customer_review_invoked([INVOCATION_RULES[0]]))

    def test_every_triggered_rule_is_reported_at_once(self):
        reasons = invocation_reasons([INVOCATION_RULES[2], INVOCATION_RULES[0]])
        self.assertEqual(len(reasons), 2)

    def test_reasons_come_back_in_the_published_rule_order(self):
        reasons = invocation_reasons([INVOCATION_RULES[3], INVOCATION_RULES[1]])
        self.assertEqual(reasons, (INVOCATION_RULES[1], INVOCATION_RULES[3]))

    def test_a_repeated_rule_is_not_counted_twice(self):
        reasons = invocation_reasons([INVOCATION_RULES[0], INVOCATION_RULES[0]])
        self.assertEqual(len(reasons), 1)

    def test_an_unknown_invocation_rule_is_rejected(self):
        with self.assertRaises(ValueError):
            invocation_reasons(["the-buyer-had-a-feeling"])

    def test_a_bare_string_is_not_an_invocation_flag_list(self):
        with self.assertRaises(ValueError):
            invocation_reasons(INVOCATION_RULES[0])


class SubmissionTests(unittest.TestCase):
    def test_a_complete_dossier_leaves_no_item_missing(self):
        self.assertEqual(
            missing_submission_items(list(REQUIRED_SUBMISSION_ITEMS)), ()
        )

    def test_each_absent_item_is_named_separately(self):
        missing = missing_submission_items([REQUIRED_SUBMISSION_ITEMS[0]])
        self.assertEqual(len(missing), len(REQUIRED_SUBMISSION_ITEMS) - 1)

    def test_an_empty_dossier_is_missing_everything(self):
        self.assertEqual(missing_submission_items([]), REQUIRED_SUBMISSION_ITEMS)

    def test_a_repeated_item_does_not_count_twice(self):
        supplied = [REQUIRED_SUBMISSION_ITEMS[0], REQUIRED_SUBMISSION_ITEMS[0]]
        missing = missing_submission_items(supplied)
        self.assertEqual(len(missing), len(REQUIRED_SUBMISSION_ITEMS) - 1)

    def test_an_unknown_submission_item_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_submission_items(["a-phone-call-with-the-customer"])

    def test_an_unknown_customer_decision_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_submission(full_submission(customer_decision="probably-fine"))

    def test_every_published_decision_normalizes(self):
        for decision in CUSTOMER_DECISIONS:
            extra = {}
            if decision == "approved-with-restriction":
                extra["restrictions"] = [
                    {"restriction_id": "r1", "implementation_record_present": True}
                ]
            record = normalize_submission(
                full_submission(customer_decision=decision, **extra)
            )
            self.assertEqual(record["customer_decision"], decision)

    def test_a_negative_elapsed_time_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_submission(full_submission(elapsed_working_days=-1.0))

    def test_a_non_mapping_submission_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_submission("approved verbally")


class ResponseWindowTests(unittest.TestCase):
    def test_a_submission_inside_the_window_has_not_elapsed(self):
        self.assertFalse(response_window_elapsed(1.0))

    def test_a_submission_exactly_on_the_window_edge_has_not_elapsed(self):
        edge = RESPONSE_WINDOW_WORKING_DAYS
        self.assertAlmostEqual(edge, RESPONSE_WINDOW_WORKING_DAYS, places=9)
        self.assertFalse(response_window_elapsed(edge))

    def test_a_submission_well_past_the_window_has_elapsed(self):
        self.assertTrue(response_window_elapsed(RESPONSE_WINDOW_WORKING_DAYS + 10.0))

    def test_the_window_tolerance_is_small_enough_to_separate_the_edge(self):
        self.assertLess(RESPONSE_TOLERANCE, 1e-6)

    def test_a_negative_elapsed_time_is_refused_by_the_window_check(self):
        with self.assertRaises(ValueError):
            response_window_elapsed(-0.5)


class RestrictionTests(unittest.TestCase):
    def test_an_implemented_restriction_is_not_open(self):
        restrictions = [
            {"restriction_id": "r1", "implementation_record_present": True}
        ]
        self.assertEqual(open_restrictions(restrictions), ())

    def test_a_restriction_without_a_record_stays_open(self):
        restrictions = [
            {"restriction_id": "r1", "implementation_record_present": False}
        ]
        self.assertEqual(open_restrictions(restrictions), ("r1",))

    def test_every_open_restriction_is_named_at_once(self):
        restrictions = [
            {"restriction_id": "r1", "implementation_record_present": False},
            {"restriction_id": "r2", "implementation_record_present": True},
            {"restriction_id": "r3", "implementation_record_present": False},
        ]
        self.assertEqual(open_restrictions(restrictions), ("r1", "r3"))

    def test_a_duplicate_restriction_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_restrictions(
                [
                    {"restriction_id": "r1", "implementation_record_present": True},
                    {"restriction_id": "r1", "implementation_record_present": False},
                ]
            )

    def test_a_restriction_without_an_implementation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_restrictions([{"restriction_id": "r1"}])

    def test_a_restricted_approval_carrying_no_restriction_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_submission(
                full_submission(
                    customer_decision="approved-with-restriction", restrictions=[]
                )
            )

    def test_restrictions_attached_to_an_outright_approval_are_rejected(self):
        with self.assertRaises(ValueError):
            normalize_submission(
                full_submission(
                    restrictions=[
                        {"restriction_id": "r1", "implementation_record_present": True}
                    ]
                )
            )


class PartStatusTests(unittest.TestCase):
    def test_a_part_that_invoked_nothing_is_usable_without_a_review(self):
        record = assess_proposed_part(
            proposed_part(invocation_flags=[], submission=None)
        )
        self.assertEqual(
            record["status"], "class-3-part-usable-without-customer-review"
        )
        self.assertTrue(record["usable"])
        self.assertEqual(record["findings"], [])

    def test_a_complete_approved_submission_makes_the_part_usable(self):
        record = assess_proposed_part(proposed_part())
        self.assertEqual(record["status"], "class-3-part-approved-for-use")
        self.assertTrue(record["usable"])
        self.assertEqual(record["findings"], [])

    def test_an_invoked_part_with_no_submission_is_incomplete(self):
        record = assess_proposed_part(proposed_part(submission=None))
        self.assertEqual(record["status"], "class-3-part-submission-incomplete")
        self.assertIn(
            "customer-review-invoked-but-nothing-was-submitted",
            [f["finding"] for f in record["findings"]],
        )

    def test_an_invoked_part_with_no_submission_is_missing_every_item(self):
        record = assess_proposed_part(proposed_part(submission=None))
        self.assertEqual(
            record["missing_submission_items"], list(REQUIRED_SUBMISSION_ITEMS)
        )

    def test_an_approval_on_an_incomplete_dossier_does_not_release_the_part(self):
        record = assess_proposed_part(
            proposed_part(
                submission=full_submission(
                    items=list(REQUIRED_SUBMISSION_ITEMS[:2])
                )
            )
        )
        self.assertEqual(record["status"], "class-3-part-submission-incomplete")
        self.assertFalse(record["usable"])

    def test_customer_silence_inside_the_window_is_pending_not_approval(self):
        record = assess_proposed_part(
            proposed_part(
                submission=full_submission(
                    customer_decision="no-response", elapsed_working_days=5.0
                )
            )
        )
        self.assertEqual(record["status"], "class-3-part-approval-pending-customer")
        self.assertFalse(record["usable"])

    def test_customer_silence_past_the_window_is_still_not_approval(self):
        record = assess_proposed_part(
            proposed_part(
                submission=full_submission(
                    customer_decision="no-response",
                    elapsed_working_days=RESPONSE_WINDOW_WORKING_DAYS + 15.0,
                )
            )
        )
        self.assertEqual(record["status"], "class-3-part-approval-pending-customer")
        self.assertIn(
            "response-window-elapsed-without-a-decision",
            [f["finding"] for f in record["findings"]],
        )

    def test_silence_inside_the_window_raises_no_escalation_finding(self):
        record = assess_proposed_part(
            proposed_part(
                submission=full_submission(
                    customer_decision="no-response", elapsed_working_days=2.0
                )
            )
        )
        self.assertNotIn(
            "response-window-elapsed-without-a-decision",
            [f["finding"] for f in record["findings"]],
        )

    def test_a_refusal_blocks_the_part(self):
        record = assess_proposed_part(
            proposed_part(submission=full_submission(customer_decision="refused"))
        )
        self.assertEqual(record["status"], "class-3-part-refused-by-customer")
        self.assertFalse(record["usable"])

    def test_an_open_restriction_blocks_a_restricted_approval(self):
        record = assess_proposed_part(
            proposed_part(
                submission=full_submission(
                    customer_decision="approved-with-restriction",
                    restrictions=[
                        {"restriction_id": "r1", "implementation_record_present": False}
                    ],
                )
            )
        )
        self.assertEqual(record["status"], "class-3-part-restriction-not-implemented")
        self.assertEqual(record["open_restrictions"], ["r1"])

    def test_a_restricted_approval_with_every_record_in_place_releases(self):
        record = assess_proposed_part(
            proposed_part(
                submission=full_submission(
                    customer_decision="approved-with-restriction",
                    restrictions=[
                        {"restriction_id": "r1", "implementation_record_present": True},
                        {"restriction_id": "r2", "implementation_record_present": True},
                    ],
                )
            )
        )
        self.assertEqual(record["status"], "class-3-part-approved-for-use")

    def test_a_part_declared_in_another_category_is_not_reviewed_here(self):
        record = assess_proposed_part(proposed_part(declared_category="class-2"))
        self.assertIn(
            "declared-category-is-not-the-one-being-reviewed",
            [f["finding"] for f in record["findings"]],
        )
        self.assertFalse(record["usable"])

    def test_every_status_name_is_one_the_module_publishes(self):
        self.assertIn(assess_proposed_part(proposed_part())["status"], PART_STATUSES)
        self.assertIn(
            assess_proposed_part(proposed_part(submission=None))["status"],
            PART_STATUSES,
        )

    def test_the_usable_status_names_are_all_published_statuses(self):
        for status in USABLE_STATUSES:
            self.assertIn(status, PART_STATUSES)

    def test_an_empty_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_proposed_part(proposed_part(part_number="  "))

    def test_a_non_mapping_part_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_proposed_part("cot31-lm4040")


class ProposedListTests(unittest.TestCase):
    def test_a_list_whose_parts_all_cleared_is_usable(self):
        report = assess_class_3_parts_approval(
            "cubesat-c",
            [proposed_part(), proposed_part(part_number="cot32-2n7002")],
        )
        self.assertTrue(report["list_usable"])
        self.assertEqual(len(report["usable_parts"]), 2)
        self.assertEqual(report["blocked_parts"], [])

    def test_one_pending_part_blocks_the_whole_list(self):
        report = assess_class_3_parts_approval(
            "cubesat-c",
            [
                proposed_part(),
                proposed_part(
                    part_number="cot32-2n7002",
                    submission=full_submission(customer_decision="no-response"),
                ),
            ],
        )
        self.assertFalse(report["list_usable"])
        self.assertEqual(report["blocked_parts"], ["cot32-2n7002"])

    def test_the_invoked_fraction_counts_only_the_parts_a_rule_caught(self):
        report = assess_class_3_parts_approval(
            "cubesat-c",
            [
                proposed_part(),
                proposed_part(
                    part_number="cot32-2n7002",
                    invocation_flags=[],
                    submission=None,
                ),
            ],
        )
        self.assertAlmostEqual(report["invoked_fraction"], 0.5, places=9)
        self.assertEqual(report["review_invoked_parts"], ["cot31-lm4040"])

    def test_a_list_nothing_invoked_has_a_zero_invoked_fraction(self):
        report = assess_class_3_parts_approval(
            "cubesat-c",
            [proposed_part(invocation_flags=[], submission=None)],
        )
        self.assertAlmostEqual(report["invoked_fraction"], 0.0, places=9)

    def test_the_status_counts_add_up_to_the_proposed_list(self):
        parts = [
            proposed_part(),
            proposed_part(part_number="cot32-2n7002", submission=None),
            proposed_part(
                part_number="cot33-bav99",
                submission=full_submission(customer_decision="refused"),
            ),
        ]
        report = assess_class_3_parts_approval("cubesat-c", parts)
        self.assertEqual(sum(report["status_counts"].values()), 3)
        self.assertEqual(report["status_counts"]["class-3-part-approved-for-use"], 1)
        self.assertEqual(
            report["status_counts"]["class-3-part-submission-incomplete"], 1
        )
        self.assertEqual(
            report["status_counts"]["class-3-part-refused-by-customer"], 1
        )

    def test_a_repeated_part_number_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_parts_approval(
                "cubesat-c", [proposed_part(), proposed_part()]
            )

    def test_an_empty_proposed_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_parts_approval("cubesat-c", [])

    def test_an_empty_programme_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_parts_approval("  ", [proposed_part()])

    def test_a_non_sequence_proposed_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_parts_approval("cubesat-c", {"part_number": "x"})

    def test_every_finding_carries_the_part_number_it_belongs_to(self):
        report = assess_class_3_parts_approval(
            "cubesat-c", [proposed_part(submission=None)]
        )
        for finding in report["findings"]:
            self.assertEqual(finding["part_number"], "cot31-lm4040")


if __name__ == "__main__":
    unittest.main()

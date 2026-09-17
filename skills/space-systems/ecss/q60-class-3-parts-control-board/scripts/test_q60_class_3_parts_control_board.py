"""Contract tests for the clause 6.1.3 class 3 board approval logic."""

import unittest

from q60_class_3_parts_control_board_logic import (
    APPROVAL_SCOPES,
    BOUND_TOLERANCE,
    CUSTOMER_TRIGGERS,
    DOCKET_READINESS_FLOOR,
    active_triggers,
    approval_defects,
    approval_docket,
    approval_lead_days,
    approval_scopes,
    board_approval_required,
    compile_class_3_board_approval,
    docket_readiness,
    readiness_meets_floor,
    recognised_triggers,
    scope_coverage,
    trigger_defects,
    usage_disposition,
    usage_id,
)


def _trigger(**over):
    base = {
        "trigger": "customer-written-request",
        "active": True,
        "reference": "CUST-LTR-6071-14",
    }
    base.update(over)
    return base


def _approval(**over):
    base = {
        "approval_date": "2026-03-04",
        "board_chair": "parts-board-chair",
        "customer_representative": "customer-parts-delegate",
        "scopes": list(APPROVAL_SCOPES),
        "part_identity": "CAP-TA-6071-B",
    }
    base.update(over)
    return base


def _usage(**over):
    base = {
        "usage_id": "USG-6071-001",
        "triggers": [_trigger()],
        "commitment_date": "2026-04-01",
        "approval": _approval(),
    }
    base.update(over)
    return base


class TriggerTests(unittest.TestCase):
    def test_a_declared_trigger_is_recognised(self):
        self.assertEqual(recognised_triggers(_usage()),
                         ["customer-written-request"])

    def test_a_trigger_reads_case_insensitively(self):
        usage = _usage(triggers=[_trigger(trigger="CUSTOMER-WRITTEN-REQUEST")])
        self.assertEqual(recognised_triggers(usage),
                         ["customer-written-request"])

    def test_an_unknown_trigger_is_not_recognised(self):
        usage = _usage(triggers=[_trigger(trigger="corridor-conversation")])
        self.assertEqual(recognised_triggers(usage), [])

    def test_an_unknown_trigger_is_reported_as_a_defect(self):
        usage = _usage(triggers=[_trigger(trigger="corridor-conversation")])
        self.assertIn("trigger-not-recognised", trigger_defects(usage))

    def test_triggers_come_back_in_report_order(self):
        usage = _usage(triggers=[
            _trigger(trigger="customer-deviation-response"),
            _trigger(trigger="customer-contract-clause"),
        ])
        self.assertEqual(recognised_triggers(usage),
                         ["customer-contract-clause",
                          "customer-deviation-response"])

    def test_a_repeated_trigger_is_counted_once(self):
        usage = _usage(triggers=[_trigger(), _trigger()])
        self.assertEqual(active_triggers(usage), ["customer-written-request"])

    def test_an_inactive_trigger_does_not_convene_the_board(self):
        usage = _usage(triggers=[_trigger(active=False)])
        self.assertEqual(active_triggers(usage), [])

    def test_an_unevidenced_trigger_does_not_convene_the_board(self):
        usage = _usage(triggers=[_trigger(reference="")])
        self.assertEqual(active_triggers(usage), [])

    def test_an_unevidenced_active_trigger_is_reported_as_a_defect(self):
        usage = _usage(triggers=[_trigger(reference=None)])
        self.assertIn("active-trigger-without-reference", trigger_defects(usage))

    def test_a_sound_trigger_list_carries_no_defects(self):
        self.assertEqual(trigger_defects(_usage()), [])

    def test_the_trigger_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            recognised_triggers(_usage(triggers="customer-written-request"))

    def test_a_trigger_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            recognised_triggers(_usage(triggers=["customer-written-request"]))

    def test_every_published_trigger_is_recognised(self):
        usage = _usage(triggers=[_trigger(trigger=name)
                                 for name in CUSTOMER_TRIGGERS])
        self.assertEqual(recognised_triggers(usage), list(CUSTOMER_TRIGGERS))

    def test_a_usage_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            recognised_triggers("USG-6071-001")


class RequirementTests(unittest.TestCase):
    def test_an_active_trigger_convenes_the_board(self):
        self.assertTrue(board_approval_required(_usage()))

    def test_no_trigger_leaves_the_board_out_of_it(self):
        self.assertFalse(board_approval_required(_usage(triggers=[])))

    def test_an_inactive_trigger_leaves_the_board_out_of_it(self):
        usage = _usage(triggers=[_trigger(active=False)])
        self.assertFalse(board_approval_required(usage))

    def test_an_unevidenced_trigger_leaves_the_board_out_of_it(self):
        usage = _usage(triggers=[_trigger(reference="  ")])
        self.assertFalse(board_approval_required(usage))

    def test_an_untriggered_usage_needs_no_approval(self):
        self.assertEqual(usage_disposition(_usage(triggers=[], approval=None)),
                         "board-approval-not-required")


class ScopeTests(unittest.TestCase):
    def test_both_scopes_are_read(self):
        self.assertEqual(approval_scopes(_approval()), list(APPROVAL_SCOPES))

    def test_a_scope_reads_case_insensitively(self):
        approval = _approval(scopes=["PART-SELECTION"])
        self.assertEqual(approval_scopes(approval), ["part-selection"])

    def test_an_unknown_scope_is_left_out(self):
        approval = _approval(scopes=["part-storage"])
        self.assertEqual(approval_scopes(approval), [])

    def test_scopes_come_back_in_report_order(self):
        approval = _approval(scopes=list(reversed(APPROVAL_SCOPES)))
        self.assertEqual(approval_scopes(approval), list(APPROVAL_SCOPES))

    def test_full_scope_coverage_reads_one(self):
        self.assertAlmostEqual(scope_coverage(_approval()), 1.0, places=9)

    def test_one_scope_of_two_reads_a_half(self):
        approval = _approval(scopes=["part-selection"])
        self.assertAlmostEqual(scope_coverage(approval), 0.5, places=9)

    def test_no_scope_reads_zero(self):
        self.assertAlmostEqual(scope_coverage(_approval(scopes=[])), 0.0,
                               places=9)

    def test_the_scope_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            approval_scopes(_approval(scopes="part-selection"))

    def test_an_approval_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            approval_scopes("2026-03-04")


class LeadTimeTests(unittest.TestCase):
    def test_an_approval_before_the_commitment_has_a_positive_lead(self):
        self.assertEqual(approval_lead_days(_usage()), 28)

    def test_an_approval_on_the_commitment_day_has_no_lead(self):
        usage = _usage(commitment_date="2026-03-04")
        self.assertEqual(approval_lead_days(usage), 0)

    def test_an_approval_after_the_commitment_has_a_negative_lead(self):
        usage = _usage(commitment_date="2026-02-25")
        self.assertEqual(approval_lead_days(usage), -7)

    def test_a_malformed_date_is_rejected(self):
        usage = _usage(commitment_date="1 April 2026")
        with self.assertRaises(ValueError):
            approval_lead_days(usage)

    def test_a_missing_date_is_rejected(self):
        usage = _usage(approval=_approval(approval_date=None))
        with self.assertRaises(ValueError):
            approval_lead_days(usage)

    def test_a_usage_without_an_approval_has_no_lead(self):
        with self.assertRaises(ValueError):
            approval_lead_days(_usage(approval=None))


class ApprovalDefectTests(unittest.TestCase):
    def test_a_sound_approval_carries_no_defects(self):
        self.assertEqual(approval_defects(_usage()), [])

    def test_an_absent_approval_is_the_only_defect_reported(self):
        self.assertEqual(approval_defects(_usage(approval=None)),
                         ["approval-record-absent"])

    def test_an_unstated_approval_date_is_a_defect(self):
        usage = _usage(approval=_approval(approval_date=""))
        self.assertIn("approval-date-not-stated", approval_defects(usage))

    def test_an_unstated_commitment_date_is_a_defect(self):
        usage = _usage(commitment_date=None)
        self.assertIn("commitment-date-not-stated", approval_defects(usage))

    def test_an_approval_after_the_commitment_is_a_defect(self):
        usage = _usage(commitment_date="2026-02-25")
        self.assertIn("approval-after-commitment", approval_defects(usage))

    def test_an_approval_on_the_commitment_day_is_not_a_defect(self):
        usage = _usage(commitment_date="2026-03-04")
        self.assertEqual(approval_defects(usage), [])

    def test_an_unnamed_chair_is_a_defect(self):
        usage = _usage(approval=_approval(board_chair="   "))
        self.assertIn("board-chair-not-named", approval_defects(usage))

    def test_an_absent_customer_representative_is_a_defect(self):
        usage = _usage(approval=_approval(customer_representative=None))
        self.assertIn("customer-representative-absent", approval_defects(usage))

    def test_an_approval_covering_only_selection_leaves_usage_unapproved(self):
        usage = _usage(approval=_approval(scopes=["part-selection"]))
        self.assertIn("part-usage-not-approved", approval_defects(usage))

    def test_an_approval_covering_only_usage_leaves_selection_unapproved(self):
        usage = _usage(approval=_approval(scopes=["part-usage"]))
        self.assertIn("part-selection-not-approved", approval_defects(usage))

    def test_an_unidentified_part_is_a_defect(self):
        usage = _usage(approval=_approval(part_identity=""))
        self.assertIn("part-identity-not-stated", approval_defects(usage))

    def test_defects_accumulate(self):
        usage = _usage(approval=_approval(board_chair="",
                                          customer_representative="",
                                          part_identity=""))
        self.assertEqual(len(approval_defects(usage)), 3)


class DispositionTests(unittest.TestCase):
    def test_a_sound_triggered_usage_is_valid(self):
        self.assertEqual(usage_disposition(_usage()), "board-approval-valid")

    def test_a_triggered_usage_with_no_approval_is_missing(self):
        self.assertEqual(usage_disposition(_usage(approval=None)),
                         "board-approval-missing")

    def test_a_triggered_usage_with_a_flawed_approval_is_deficient(self):
        usage = _usage(approval=_approval(customer_representative=None))
        self.assertEqual(usage_disposition(usage), "board-approval-deficient")

    def test_an_untriggered_usage_with_no_approval_still_clears(self):
        usage = _usage(triggers=[_trigger(active=False)], approval=None)
        self.assertEqual(usage_disposition(usage),
                         "board-approval-not-required")

    def test_a_usage_without_an_identifier_gets_a_placeholder(self):
        self.assertEqual(usage_id(_usage(usage_id=None)), "unnamed-usage")


class CompilationTests(unittest.TestCase):
    def test_a_sound_usage_is_cleared(self):
        result = compile_class_3_board_approval(_usage())
        self.assertTrue(result["usage_cleared"])
        self.assertEqual(result["disposition"], "board-approval-valid")

    def test_the_active_triggers_are_reported(self):
        result = compile_class_3_board_approval(_usage())
        self.assertEqual(result["active_triggers"],
                         ["customer-written-request"])

    def test_the_lead_time_is_reported(self):
        result = compile_class_3_board_approval(_usage())
        self.assertEqual(result["approval_lead_days"], 28)

    def test_the_scope_coverage_is_reported(self):
        result = compile_class_3_board_approval(_usage())
        self.assertAlmostEqual(result["approval_scope_coverage"], 1.0, places=9)

    def test_an_untriggered_usage_reports_no_approval_defects(self):
        usage = _usage(triggers=[], approval=None)
        result = compile_class_3_board_approval(usage)
        self.assertEqual(result["approval_defects"], [])
        self.assertTrue(result["usage_cleared"])

    def test_a_deficient_usage_reports_its_defects(self):
        usage = _usage(approval=_approval(part_identity=""))
        result = compile_class_3_board_approval(usage)
        self.assertIn("part-identity-not-stated", result["approval_defects"])
        self.assertFalse(result["usage_cleared"])

    def test_a_malformed_date_leaves_the_lead_unreported(self):
        usage = _usage(commitment_date="1 April 2026")
        result = compile_class_3_board_approval(usage)
        self.assertIsNone(result["approval_lead_days"])

    def test_the_usage_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            compile_class_3_board_approval([_usage()])


class DocketTests(unittest.TestCase):
    def test_a_docket_is_ordered_by_usage_identifier(self):
        usages = [_usage(usage_id="USG-6071-009"),
                  _usage(usage_id="USG-6071-002")]
        docket = approval_docket(usages)
        self.assertEqual([entry["usage"] for entry in docket],
                         ["USG-6071-002", "USG-6071-009"])

    def test_a_cleared_docket_reads_one(self):
        self.assertAlmostEqual(docket_readiness([_usage()]), 1.0, places=9)

    def test_one_deficient_usage_of_two_reads_a_half(self):
        usages = [_usage(usage_id="USG-A"),
                  _usage(usage_id="USG-B", approval=None)]
        self.assertAlmostEqual(docket_readiness(usages), 0.5, places=9)

    def test_untriggered_usages_count_as_cleared(self):
        usages = [_usage(), _usage(usage_id="USG-B", triggers=[],
                                   approval=None)]
        self.assertAlmostEqual(docket_readiness(usages), 1.0, places=9)

    def test_an_empty_docket_is_rejected(self):
        with self.assertRaises(ValueError):
            docket_readiness([])

    def test_a_docket_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            approval_docket(_usage())

    def test_a_cleared_docket_meets_the_floor(self):
        self.assertTrue(readiness_meets_floor(1.0))

    def test_a_readiness_exactly_on_the_floor_meets_it(self):
        self.assertTrue(readiness_meets_floor(DOCKET_READINESS_FLOOR))

    def test_a_half_ready_docket_does_not_meet_the_floor(self):
        self.assertFalse(readiness_meets_floor(0.5))

    def test_a_readiness_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            readiness_meets_floor(1.4)

    def test_a_negative_readiness_is_rejected(self):
        with self.assertRaises(ValueError):
            readiness_meets_floor(-0.2)

    def test_the_floor_is_the_documented_size(self):
        self.assertAlmostEqual(DOCKET_READINESS_FLOOR, 1.0, places=9)

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=1)

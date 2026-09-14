"""Contract tests for the clause 4.5.4 lot-identity traceability logic."""

import unittest

from q6013_class_1_traceability_logic import (
    COMPLETENESS_TOLERANCE,
    EVENT_TYPES,
    assess_traceability,
    backward_trace,
    forward_trace,
    identity_breaks,
    identity_completeness,
    reconcile_quantities,
    validate_chain,
    validate_event,
)

LOT = "LOT-2336-K7"


def event(event_id, event_type, timestamp_h, quantity, **overrides):
    record = {
        "event_id": event_id,
        "type": event_type,
        "timestamp_h": timestamp_h,
        "quantity": quantity,
        "lot_code": LOT,
        "date_code": "2336",
        "coc_reference": "COC-8841",
    }
    record.update(overrides)
    return record


def clean_chain():
    """Receipt of 100, inspected, stored, kitted, 60 installed, 2 scrapped."""
    return [
        event("E1", "receipt", 0.0, 100),
        event("E2", "incoming-inspection", 4.0, 100),
        event("E3", "stores-in", 6.0, 100),
        event("E4", "stores-out", 200.0, 62),
        event("E5", "kitting", 201.0, 62),
        event("E6", "assembly-install", 210.0, 30, board_serial="BRD-001"),
        event("E7", "assembly-install", 214.0, 30, board_serial="BRD-002"),
        event("E8", "scrap", 216.0, 2),
    ]


class ValidateEventTests(unittest.TestCase):
    def test_normalises_a_good_event(self):
        record = validate_event(event("E1", "receipt", 0.0, 100))
        self.assertEqual(record["quantity"], 100)
        self.assertIsNone(record["board_serial"])

    def test_every_declared_type_is_accepted(self):
        for index, event_type in enumerate(EVENT_TYPES):
            extra = {}
            if event_type == "assembly-install":
                extra["board_serial"] = "BRD-009"
            record = validate_event(event("E%d" % index, event_type, 1.0, 5, **extra))
            self.assertEqual(record["type"], event_type)

    def test_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("E1", "shelf-life-extension", 1.0, 5))

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("E1", "receipt", 0.0, 0))

    def test_negative_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("E1", "receipt", -1.0, 5))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("E1", "receipt", 0.0, True))

    def test_install_without_a_board_serial_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("E6", "assembly-install", 10.0, 5))

    def test_board_serial_on_a_non_install_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("E3", "stores-in", 10.0, 5, board_serial="BRD-001"))

    def test_blank_event_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(event("   ", "receipt", 0.0, 5))

    def test_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            validate_event("E1")


class ValidateChainTests(unittest.TestCase):
    def test_chain_is_returned_in_clock_order(self):
        shuffled = list(reversed(clean_chain()))
        ordered = validate_chain(shuffled)
        self.assertEqual([r["event_id"] for r in ordered],
                         ["E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"])

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_chain([])

    def test_duplicate_event_id_rejected(self):
        chain = clean_chain()
        chain.append(event("E3", "stores-in", 300.0, 1))
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_two_receipts_rejected(self):
        chain = clean_chain()
        chain.append(event("E9", "receipt", 500.0, 10))
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_no_receipt_rejected(self):
        chain = [e for e in clean_chain() if e["type"] != "receipt"]
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_event_before_the_receipt_rejected(self):
        chain = clean_chain()
        chain.append(event("E0", "stores-in", 0.0, 100))
        with self.assertRaises(ValueError):
            validate_chain(chain)


class IdentityBreakTests(unittest.TestCase):
    def test_clean_chain_has_no_breaks(self):
        self.assertEqual(identity_breaks(LOT, clean_chain()), [])

    def test_missing_lot_code_is_a_break(self):
        chain = clean_chain()
        chain[3]["lot_code"] = None
        breaks = identity_breaks(LOT, chain)
        self.assertTrue(any("no lot code" in b for b in breaks))

    def test_blank_lot_code_is_a_break(self):
        chain = clean_chain()
        chain[3]["lot_code"] = "  "
        self.assertTrue(identity_breaks(LOT, chain))

    def test_relotted_event_without_cross_reference_is_a_break(self):
        chain = clean_chain()
        chain[5]["lot_code"] = "LOT-REMARKED-9"
        breaks = identity_breaks(LOT, chain)
        self.assertTrue(any("cross-reference" in b for b in breaks))

    def test_relotted_event_with_cross_reference_is_accepted(self):
        chain = clean_chain()
        chain[5]["lot_code"] = "LOT-REMARKED-9"
        chain[5]["cross_reference"] = "XREF-2336-K7"
        self.assertEqual(identity_breaks(LOT, chain), [])

    def test_contradicting_date_code_is_a_break(self):
        chain = clean_chain()
        chain[6]["date_code"] = "2401"
        breaks = identity_breaks(LOT, chain)
        self.assertTrue(any("date code" in b for b in breaks))

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            identity_breaks("  ", clean_chain())


class ReconcileTests(unittest.TestCase):
    def test_clean_chain_balances(self):
        totals = reconcile_quantities(clean_chain())
        self.assertEqual(totals["received"], 100)
        self.assertEqual(totals["installed"], 60)
        self.assertEqual(totals["scrapped"], 2)
        self.assertEqual(totals["remaining"], 38)
        self.assertTrue(totals["balanced"])

    def test_over_issue_is_detected(self):
        chain = clean_chain()
        chain.append(event("E9", "assembly-install", 300.0, 50, board_serial="BRD-003"))
        totals = reconcile_quantities(chain)
        self.assertFalse(totals["balanced"])
        self.assertEqual(totals["over_issued"], 12)

    def test_returns_reduce_the_remainder(self):
        chain = clean_chain()
        chain.append(event("E9", "return-to-supplier", 300.0, 8))
        totals = reconcile_quantities(chain)
        self.assertEqual(totals["returned"], 8)
        self.assertEqual(totals["remaining"], 30)

    def test_stores_movements_do_not_consume_the_lot(self):
        chain = clean_chain()
        chain.append(event("E9", "stores-out", 320.0, 20))
        totals = reconcile_quantities(chain)
        self.assertEqual(totals["consumed"], 62)


class TraceTests(unittest.TestCase):
    def test_forward_trace_lists_every_board(self):
        trace = forward_trace(clean_chain())
        self.assertEqual(trace, {"BRD-001": 30, "BRD-002": 30})

    def test_forward_trace_sums_repeat_installs_on_one_board(self):
        chain = clean_chain()
        chain.append(event("E9", "assembly-install", 300.0, 4, board_serial="BRD-001"))
        self.assertEqual(forward_trace(chain)["BRD-001"], 34)

    def test_backward_trace_returns_the_receipt_identity(self):
        result = backward_trace(LOT, clean_chain(), "BRD-002")
        self.assertEqual(result["lot_id"], LOT)
        self.assertEqual(result["quantity"], 30)
        self.assertEqual(result["coc_reference"], "COC-8841")

    def test_backward_trace_refuses_an_unknown_serial(self):
        with self.assertRaises(ValueError):
            backward_trace(LOT, clean_chain(), "BRD-404")

    def test_backward_trace_refuses_a_blank_serial(self):
        with self.assertRaises(ValueError):
            backward_trace(LOT, clean_chain(), "   ")


class CompletenessTests(unittest.TestCase):
    def test_full_chain_scores_one(self):
        self.assertAlmostEqual(identity_completeness(clean_chain()), 1.0, places=9)

    def test_one_missing_certificate_lowers_the_score(self):
        chain = clean_chain()
        chain[2]["coc_reference"] = None
        self.assertAlmostEqual(identity_completeness(chain), 7.0 / 8.0, places=9)

    def test_two_missing_date_codes_lower_the_score(self):
        chain = clean_chain()
        chain[2]["date_code"] = None
        chain[3]["date_code"] = None
        self.assertAlmostEqual(identity_completeness(chain), 0.75, places=9)


class AssessTraceabilityTests(unittest.TestCase):
    def test_clean_chain_is_traceable(self):
        result = assess_traceability(LOT, clean_chain())
        self.assertTrue(result["traceable"])
        self.assertEqual(result["findings"], [])

    def test_exactly_meeting_the_threshold_passes(self):
        chain = clean_chain()
        chain[2]["coc_reference"] = None
        result = assess_traceability(LOT, chain, required_completeness=7.0 / 8.0)
        self.assertTrue(result["meets_completeness"])

    def test_completeness_tolerance_is_small(self):
        self.assertLess(COMPLETENESS_TOLERANCE, 1e-6)

    def test_short_completeness_is_a_finding(self):
        chain = clean_chain()
        chain[2]["coc_reference"] = None
        result = assess_traceability(LOT, chain, required_completeness=1.0)
        self.assertFalse(result["traceable"])
        self.assertTrue(any("completeness" in f for f in result["findings"]))

    def test_over_issue_is_a_finding(self):
        chain = clean_chain()
        chain.append(event("E9", "assembly-install", 300.0, 60, board_serial="BRD-003"))
        result = assess_traceability(LOT, chain)
        self.assertFalse(result["traceable"])
        self.assertTrue(any("more than" in f for f in result["findings"]))

    def test_identity_break_blocks_traceability(self):
        chain = clean_chain()
        chain[4]["lot_code"] = None
        result = assess_traceability(LOT, chain)
        self.assertFalse(result["traceable"])

    def test_threshold_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability(LOT, clean_chain(), required_completeness=1.5)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability(LOT, clean_chain(), required_completeness=-0.1)

    def test_non_numeric_threshold_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability(LOT, clean_chain(), required_completeness="1.0")

    def test_result_carries_the_forward_trace(self):
        result = assess_traceability(LOT, clean_chain())
        self.assertEqual(sorted(result["forward_trace"]), ["BRD-001", "BRD-002"])


if __name__ == "__main__":
    unittest.main()

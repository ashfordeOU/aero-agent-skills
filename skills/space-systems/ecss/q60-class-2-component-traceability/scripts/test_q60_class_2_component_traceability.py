"""Contract tests for the clause 5.5.4 class 2 traceability logic."""

import unittest

from q60_class_2_component_traceability_logic import (
    CRITICALITY_DEPTHS,
    REQUIRED_RECEIPT_FIELDS,
    STORAGE_LIMIT_DAYS,
    TRACE_DEPTHS,
    TRACE_VERDICTS,
    achieved_depth,
    assess_class_2_traceability,
    backward_trace,
    depth_shortfall,
    forward_trace,
    lot_verdict,
    missing_receipt_fields,
    mixed_bins,
    reconcile_lot,
    required_depth,
    storage_age_days,
    storage_limit_exceeded,
    traceable_share,
    unsourced_consumptions,
)


def _receipt(**over):
    base = {
        "lot_id": "LOT-A",
        "part_number": "LM139J",
        "manufacturer": "Northgate Semiconductor",
        "date_code": "2418",
        "quantity_received": 100,
        "receipt_date": "2026-01-12",
        "certificate_reference": "CoC-8841",
        "bin": "STORE-04",
    }
    base.update(over)
    return base


ISSUES = [
    {"lot_id": "LOT-A", "assembly_id": "ASM-1", "quantity": 30},
    {"lot_id": "LOT-A", "assembly_id": "ASM-2", "quantity": 20},
]

ASSEMBLIES = [
    {"assembly_id": "ASM-1", "consumed_lots": ["LOT-A"]},
    {"assembly_id": "ASM-2", "consumed_lots": ["LOT-A", "LOT-B"]},
]


class DepthTests(unittest.TestCase):
    def test_a_full_receipt_record_reaches_lot_depth(self):
        self.assertEqual(achieved_depth(_receipt()), "lot")

    def test_serial_numbers_for_every_part_reach_serialised_depth(self):
        receipt = _receipt(quantity_received=3,
                           serial_numbers=["S1", "S2", "S3"])
        self.assertEqual(achieved_depth(receipt), "serialised")

    def test_a_partial_serial_list_does_not_reach_serialised_depth(self):
        receipt = _receipt(quantity_received=3, serial_numbers=["S1", "S2"])
        self.assertEqual(achieved_depth(receipt), "lot")

    def test_a_receipt_without_a_certificate_falls_to_date_code_depth(self):
        self.assertEqual(achieved_depth(_receipt(certificate_reference="")),
                         "date-code")

    def test_a_receipt_with_only_a_part_number_falls_further(self):
        self.assertEqual(
            achieved_depth(_receipt(date_code="", certificate_reference="",
                                    lot_id="")),
            "part-number",
        )

    def test_a_receipt_with_nothing_has_no_depth(self):
        self.assertEqual(
            achieved_depth(_receipt(lot_id="", part_number="", date_code="",
                                    certificate_reference="")),
            "none",
        )

    def test_the_receipt_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            achieved_depth("LOT-A")


class RequiredDepthTests(unittest.TestCase):
    def test_a_safety_critical_application_demands_serialised_depth(self):
        self.assertEqual(required_depth("safety-critical"), "serialised")

    def test_a_mission_critical_application_demands_lot_depth(self):
        self.assertEqual(required_depth("mission-critical"), "lot")

    def test_a_non_critical_application_demands_date_code_depth(self):
        self.assertEqual(required_depth("non-critical"), "date-code")

    def test_every_demanded_depth_is_a_known_depth(self):
        self.assertTrue(set(CRITICALITY_DEPTHS.values()) <= set(TRACE_DEPTHS))

    def test_an_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            required_depth("fairly-important")

    def test_a_met_demand_has_no_shortfall(self):
        self.assertEqual(depth_shortfall("lot", "lot"), 0)

    def test_a_deeper_trail_than_demanded_has_no_shortfall(self):
        self.assertEqual(depth_shortfall("serialised", "date-code"), 0)

    def test_a_shallower_trail_reports_its_steps(self):
        self.assertEqual(depth_shortfall("date-code", "serialised"), 2)

    def test_an_unknown_depth_rejected(self):
        with self.assertRaises(ValueError):
            depth_shortfall("vibes", "lot")


class StorageTests(unittest.TestCase):
    def test_storage_age_counts_calendar_days(self):
        self.assertEqual(storage_age_days("2026-01-12", "2026-01-22"), 10)

    def test_a_date_before_the_receipt_rejected(self):
        with self.assertRaises(ValueError):
            storage_age_days("2026-01-12", "2025-12-31")

    def test_a_lot_inside_the_limit_is_not_flagged(self):
        self.assertFalse(storage_limit_exceeded(STORAGE_LIMIT_DAYS - 1))

    def test_a_lot_exactly_on_the_limit_is_not_flagged(self):
        self.assertFalse(storage_limit_exceeded(STORAGE_LIMIT_DAYS))

    def test_a_lot_one_day_past_the_limit_is_flagged(self):
        self.assertTrue(storage_limit_exceeded(STORAGE_LIMIT_DAYS + 1))

    def test_a_negative_age_rejected(self):
        with self.assertRaises(ValueError):
            storage_limit_exceeded(-1)


class ReconciliationTests(unittest.TestCase):
    def test_a_sound_lot_balances(self):
        balance = reconcile_lot(_receipt(), ISSUES)
        self.assertTrue(balance["balanced"])
        self.assertEqual(balance["remaining"], 50)

    def test_scrapped_parts_leave_the_balance(self):
        balance = reconcile_lot(_receipt(), ISSUES,
                                [{"lot_id": "LOT-A", "quantity": 10}])
        self.assertEqual(balance["remaining"], 40)

    def test_issuing_more_than_was_received_is_caught(self):
        balance = reconcile_lot(_receipt(quantity_received=40), ISSUES)
        self.assertFalse(balance["balanced"])
        self.assertLess(balance["remaining"], 0)

    def test_another_lots_issues_are_not_counted(self):
        issues = ISSUES + [{"lot_id": "LOT-B", "assembly_id": "ASM-2",
                            "quantity": 90}]
        self.assertEqual(reconcile_lot(_receipt(), issues)["issued"], 50)

    def test_a_zero_quantity_receipt_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot(_receipt(quantity_received=0), ISSUES)

    def test_issues_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            reconcile_lot(_receipt(), "LOT-A")


class BinTests(unittest.TestCase):
    def test_one_lot_per_bin_is_clean(self):
        receipts = [_receipt(), _receipt(lot_id="LOT-B", bin="STORE-05")]
        self.assertEqual(mixed_bins(receipts), [])

    def test_two_lots_of_one_part_in_one_bin_is_flagged(self):
        receipts = [_receipt(), _receipt(lot_id="LOT-B")]
        flagged = mixed_bins(receipts)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["lots"], ["LOT-A", "LOT-B"])

    def test_two_different_parts_in_one_bin_are_not_flagged(self):
        receipts = [_receipt(), _receipt(lot_id="LOT-B", part_number="AD8021")]
        self.assertEqual(mixed_bins(receipts), [])

    def test_a_receipt_without_a_bin_is_skipped(self):
        receipts = [_receipt(bin=""), _receipt(lot_id="LOT-B", bin="")]
        self.assertEqual(mixed_bins(receipts), [])

    def test_receipts_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            mixed_bins("LOT-A")


class ChainTests(unittest.TestCase):
    def test_an_issued_lot_is_a_sound_consumption(self):
        self.assertEqual(
            unsourced_consumptions(ISSUES,
                                   [{"assembly_id": "ASM-1",
                                     "consumed_lots": ["LOT-A"]}]),
            [],
        )

    def test_a_lot_never_issued_to_the_assembly_is_caught(self):
        broken = unsourced_consumptions(ISSUES, ASSEMBLIES)
        self.assertEqual(broken, [{"assembly_id": "ASM-2", "lot_id": "LOT-B"}])

    def test_an_issue_to_another_assembly_does_not_source_this_one(self):
        broken = unsourced_consumptions(
            [{"lot_id": "LOT-A", "assembly_id": "ASM-1", "quantity": 10}],
            [{"assembly_id": "ASM-9", "consumed_lots": ["LOT-A"]}],
        )
        self.assertEqual(broken, [{"assembly_id": "ASM-9", "lot_id": "LOT-A"}])

    def test_assemblies_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            unsourced_consumptions(ISSUES, "ASM-1")


class TraceTests(unittest.TestCase):
    def test_a_lot_traces_forward_to_every_assembly_it_reached(self):
        self.assertEqual(forward_trace("LOT-A", ASSEMBLIES), ["ASM-1", "ASM-2"])

    def test_a_lot_that_reached_nothing_traces_to_nothing(self):
        self.assertEqual(forward_trace("LOT-Z", ASSEMBLIES), [])

    def test_an_assembly_traces_back_to_every_lot_it_drew_on(self):
        self.assertEqual(backward_trace("ASM-2", ASSEMBLIES), ["LOT-A", "LOT-B"])

    def test_an_unknown_assembly_rejected(self):
        with self.assertRaises(ValueError):
            backward_trace("ASM-9", ASSEMBLIES)

    def test_an_empty_lot_identifier_rejected(self):
        with self.assertRaises(ValueError):
            forward_trace("  ", ASSEMBLIES)


class VerdictTests(unittest.TestCase):
    def _balance(self, **over):
        base = {"lot_id": "LOT-A", "received": 100, "issued": 50,
                "scrapped": 0, "remaining": 50, "balanced": True}
        base.update(over)
        return base

    def test_a_sound_lot_reads_traceable(self):
        self.assertEqual(
            lot_verdict(_receipt(), self._balance(), 0, False, False), "traceable"
        )

    def test_a_lot_with_no_identity_reads_unidentified(self):
        receipt = _receipt(lot_id="", part_number="", date_code="",
                           certificate_reference="")
        self.assertEqual(
            lot_verdict(receipt, self._balance(), 0, False, False), "unidentified"
        )

    def test_a_broken_chain_outranks_an_imbalance(self):
        self.assertEqual(
            lot_verdict(_receipt(), self._balance(balanced=False), 0, False, True),
            "broken-chain",
        )

    def test_an_imbalance_outranks_a_storage_overrun(self):
        self.assertEqual(
            lot_verdict(_receipt(), self._balance(balanced=False), 0, True, False),
            "quantity-imbalance",
        )

    def test_a_storage_overrun_outranks_a_depth_shortfall(self):
        self.assertEqual(
            lot_verdict(_receipt(), self._balance(), 2, True, False),
            "storage-limit-exceeded",
        )

    def test_a_missing_receipt_field_reads_as_an_incomplete_record(self):
        self.assertEqual(
            lot_verdict(_receipt(bin=""), self._balance(), 0, False, False),
            "incomplete-receipt-record",
        )

    def test_a_shallow_trail_reads_as_a_depth_shortfall(self):
        self.assertEqual(
            lot_verdict(_receipt(), self._balance(), 1, False, False),
            "trace-depth-short",
        )

    def test_every_verdict_is_in_the_published_set(self):
        cases = (
            lot_verdict(_receipt(), self._balance(), 0, False, False),
            lot_verdict(_receipt(), self._balance(), 1, False, False),
            lot_verdict(_receipt(), self._balance(balanced=False), 0, False, False),
        )
        for verdict in cases:
            self.assertIn(verdict, TRACE_VERDICTS)

    def test_a_non_integer_shortfall_rejected(self):
        with self.assertRaises(ValueError):
            lot_verdict(_receipt(), self._balance(), 1.0, False, False)


class MissingFieldTests(unittest.TestCase):
    def test_a_complete_record_is_missing_nothing(self):
        self.assertEqual(missing_receipt_fields(_receipt()), [])

    def test_an_empty_field_is_reported(self):
        self.assertEqual(missing_receipt_fields(_receipt(manufacturer="")),
                         ["manufacturer"])

    def test_every_required_field_is_checked(self):
        stripped = {}
        self.assertEqual(sorted(missing_receipt_fields(stripped)),
                         sorted(REQUIRED_RECEIPT_FIELDS))


class ShareTests(unittest.TestCase):
    def test_every_lot_traceable_reads_one(self):
        self.assertAlmostEqual(traceable_share(["traceable", "traceable"]),
                               1.0, places=9)

    def test_no_lot_traceable_reads_zero(self):
        self.assertAlmostEqual(traceable_share(["broken-chain"]), 0.0, places=9)

    def test_half_traceable_reads_a_half(self):
        self.assertAlmostEqual(
            traceable_share(["traceable", "quantity-imbalance"]), 0.5, places=9
        )

    def test_an_empty_verdict_list_rejected(self):
        with self.assertRaises(ValueError):
            traceable_share([])

    def test_an_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            traceable_share(["probably-fine"])


class AssessmentTests(unittest.TestCase):
    def test_a_sound_set_of_lots_comes_out_traceable(self):
        result = assess_class_2_traceability(
            [_receipt()],
            [{"lot_id": "LOT-A", "assembly_id": "ASM-1", "quantity": 30}],
            [{"assembly_id": "ASM-1", "consumed_lots": ["LOT-A"]}],
            (), "mission-critical", "2026-02-01",
        )
        self.assertTrue(result["all_traceable"])
        self.assertAlmostEqual(result["traceable_share"], 1.0, places=9)

    def test_a_safety_critical_application_finds_the_depth_short(self):
        result = assess_class_2_traceability(
            [_receipt()], ISSUES, ASSEMBLIES, (), "safety-critical", "2026-02-01"
        )
        self.assertEqual(result["required_depth"], "serialised")
        self.assertEqual(result["lots"][0]["depth_shortfall"], 1)

    def test_an_unsourced_consumption_is_reported(self):
        result = assess_class_2_traceability(
            [_receipt()], ISSUES, ASSEMBLIES, (), "mission-critical", "2026-02-01"
        )
        self.assertEqual(result["unsourced_consumptions"],
                         [{"assembly_id": "ASM-2", "lot_id": "LOT-B"}])

    def test_a_mixed_bin_is_reported(self):
        result = assess_class_2_traceability(
            [_receipt(), _receipt(lot_id="LOT-B")], [], [], (),
            "mission-critical", "2026-02-01",
        )
        self.assertEqual(len(result["mixed_bins"]), 1)

    def test_a_lot_held_too_long_reads_as_a_storage_overrun(self):
        result = assess_class_2_traceability(
            [_receipt()], [], [], (), "mission-critical", "2029-02-01"
        )
        self.assertEqual(result["lots"][0]["verdict"], "storage-limit-exceeded")

    def test_the_forward_trace_is_carried_per_lot(self):
        result = assess_class_2_traceability(
            [_receipt()], ISSUES, ASSEMBLIES, (), "mission-critical", "2026-02-01"
        )
        self.assertEqual(result["lots"][0]["assemblies_reached"],
                         ["ASM-1", "ASM-2"])

    def test_no_as_of_date_leaves_the_storage_age_unknown(self):
        result = assess_class_2_traceability([_receipt()], [], [], (),
                                             "mission-critical")
        self.assertIsNone(result["lots"][0]["storage_age_days"])
        self.assertFalse(result["lots"][0]["storage_limit_exceeded"])

    def test_an_empty_receipt_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_2_traceability([], [], [], (), "mission-critical")

    def test_receipts_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_class_2_traceability("LOT-A", [], [], (), "mission-critical")


if __name__ == "__main__":
    unittest.main(verbosity=1)

"""Contract tests for the clause 4.5.4 component identity traceability logic."""

import unittest

from q60_class_1_component_traceability_logic import (
    REQUIRED_RECEIPT_FIELDS,
    TRACE_VERDICTS,
    assess_traceability,
    backward_trace,
    forward_trace,
    lot_verdict,
    mixed_bins,
    parse_iso_date,
    reconcile_lot,
    storage_age_days,
    storage_expired,
)


def receipt(**overrides):
    record = {
        "lot_id": "LOT-A",
        "part_number": "rh1020-ccg84b",
        "manufacturer": "Example Semiconductor",
        "date_code": "2336",
        "quantity_received": 50,
        "receipt_date": "2026-01-12",
        "certificate_reference": "CoC-8871",
        "bin": "BIN-04",
        "storage_limit_days": 730,
    }
    record.update(overrides)
    return record


def receipts():
    return [
        receipt(),
        receipt(
            lot_id="LOT-B",
            date_code="2402",
            quantity_received=30,
            bin="BIN-09",
            certificate_reference="CoC-8872",
        ),
    ]


def issues():
    return [
        {"lot_id": "LOT-A", "assembly_id": "ASSY-100", "quantity_issued": 20},
        {"lot_id": "LOT-B", "assembly_id": "ASSY-100", "quantity_issued": 6},
        {"lot_id": "LOT-A", "assembly_id": "ASSY-200", "quantity_issued": 10},
    ]


def assemblies():
    return [
        {"assembly_id": "ASSY-100", "consumed": {"LOT-A": 18, "LOT-B": 6}},
        {"assembly_id": "ASSY-200", "consumed": {"LOT-A": 9}},
    ]


class DateTests(unittest.TestCase):
    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date("2026-01-12").year, 2026)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("12-01-2026")

    def test_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date(20260112)

    def test_storage_age_counts_calendar_days(self):
        self.assertEqual(storage_age_days("2026-01-12", "2026-01-22"), 10)

    def test_as_of_before_receipt_rejected(self):
        with self.assertRaises(ValueError):
            storage_age_days("2026-01-12", "2025-12-31")


class StorageLimitTests(unittest.TestCase):
    def test_a_lot_inside_its_limit_is_not_expired(self):
        self.assertFalse(storage_expired("2026-01-12", "2026-06-12", 730))

    def test_a_lot_exactly_on_its_limit_is_not_expired(self):
        self.assertFalse(storage_expired("2026-01-12", "2026-01-22", 10))

    def test_a_lot_one_day_past_its_limit_is_expired(self):
        self.assertTrue(storage_expired("2026-01-12", "2026-01-23", 10))

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            storage_expired("2026-01-12", "2026-01-22", 0)

    def test_non_integer_limit_rejected(self):
        with self.assertRaises(ValueError):
            storage_expired("2026-01-12", "2026-01-22", "730")


class ReconcileTests(unittest.TestCase):
    def test_a_balanced_lot_reconciles(self):
        result = reconcile_lot(50, 30, 2, 18)
        self.assertTrue(result["balanced"])
        self.assertEqual(result["difference"], 0)

    def test_a_shortfall_is_reported_as_a_negative_difference(self):
        result = reconcile_lot(50, 30, 2, 10)
        self.assertFalse(result["balanced"])
        self.assertEqual(result["difference"], -8)

    def test_an_excess_is_reported_as_a_positive_difference(self):
        result = reconcile_lot(50, 45, 10, 5)
        self.assertEqual(result["difference"], 10)

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot(50, -1, 0, 51)

    def test_zero_received_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot(0, 0, 0, 0)

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_lot(50, True, 0, 49)


class BinTests(unittest.TestCase):
    def test_separate_bins_are_not_mixed(self):
        self.assertEqual(mixed_bins(receipts()), ())

    def test_two_lots_of_one_part_in_one_bin_are_mixed(self):
        records = receipts()
        records[1]["bin"] = "BIN-04"
        mixed = mixed_bins(records)
        self.assertEqual(len(mixed), 1)
        self.assertEqual(mixed[0]["lot_ids"], ("LOT-A", "LOT-B"))

    def test_two_different_parts_in_one_bin_are_not_mixed(self):
        records = receipts()
        records[1]["bin"] = "BIN-04"
        records[1]["part_number"] = "LM139AJ"
        self.assertEqual(mixed_bins(records), ())

    def test_receipts_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            mixed_bins(receipt())

    def test_a_receipt_missing_an_identity_field_is_rejected(self):
        record = receipt()
        del record["certificate_reference"]
        with self.assertRaises(ValueError):
            mixed_bins([record])

    def test_every_required_identity_field_is_enforced(self):
        for field in REQUIRED_RECEIPT_FIELDS:
            record = receipt()
            record[field] = ""
            with self.assertRaises(ValueError):
                mixed_bins([record])


class TraceTests(unittest.TestCase):
    def test_forward_trace_finds_every_assembly(self):
        self.assertEqual(
            forward_trace("LOT-A", assemblies()), ("ASSY-100", "ASSY-200")
        )

    def test_forward_trace_of_an_unused_lot_is_empty(self):
        self.assertEqual(forward_trace("LOT-Z", assemblies()), ())

    def test_backward_trace_finds_every_lot(self):
        self.assertEqual(backward_trace("ASSY-100", assemblies()), ("LOT-A", "LOT-B"))

    def test_backward_trace_of_an_unknown_assembly_rejected(self):
        with self.assertRaises(ValueError):
            backward_trace("ASSY-999", assemblies())

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            forward_trace("   ", assemblies())

    def test_an_assembly_consuming_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            forward_trace("LOT-A", [{"assembly_id": "ASSY-300", "consumed": {}}])

    def test_a_negative_consumed_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            forward_trace(
                "LOT-A", [{"assembly_id": "ASSY-300", "consumed": {"LOT-A": -2}}]
            )


class VerdictTests(unittest.TestCase):
    def test_all_checks_passing_is_traceable(self):
        self.assertEqual(lot_verdict(True, True, True), "traceable")

    def test_a_broken_chain_outranks_an_imbalance(self):
        self.assertEqual(lot_verdict(False, False, True), "broken-chain")

    def test_an_imbalance_is_reported_when_the_chain_holds(self):
        self.assertEqual(lot_verdict(False, True, True), "quantity-imbalance")

    def test_an_expired_lot_with_a_clean_trail(self):
        self.assertEqual(lot_verdict(True, True, False), "storage-limit-exceeded")

    def test_every_verdict_returned_is_a_known_verdict(self):
        for balanced in (True, False):
            for chain in (True, False):
                for storage in (True, False):
                    self.assertIn(lot_verdict(balanced, chain, storage), TRACE_VERDICTS)

    def test_non_boolean_input_rejected(self):
        with self.assertRaises(ValueError):
            lot_verdict(1, True, True)


class AssessTraceabilityTests(unittest.TestCase):
    def test_a_complete_trail_reports_no_findings(self):
        result = assess_traceability(receipts(), issues(), assemblies(), "2026-06-12")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["trail_complete"])

    def test_every_lot_is_traceable_on_a_clean_trail(self):
        result = assess_traceability(receipts(), issues(), assemblies(), "2026-06-12")
        self.assertEqual(result["traceable_lot_count"], result["lot_count"])
        self.assertEqual(result["untraceable_quantity"], 0)

    def test_issued_quantities_are_summed_per_lot(self):
        result = assess_traceability(receipts(), issues(), assemblies(), "2026-06-12")
        lot_a = [lot for lot in result["lots"] if lot["lot_id"] == "LOT-A"][0]
        self.assertEqual(lot_a["quantity_issued"], 30)
        self.assertEqual(lot_a["quantity_remaining"], 20)

    def test_assemblies_reached_are_attached_to_each_lot(self):
        result = assess_traceability(receipts(), issues(), assemblies(), "2026-06-12")
        lot_a = [lot for lot in result["lots"] if lot["lot_id"] == "LOT-A"][0]
        self.assertEqual(lot_a["assemblies_reached"], ("ASSY-100", "ASSY-200"))

    def test_an_assembly_consuming_an_unissued_lot_breaks_the_chain(self):
        broken = assemblies() + [
            {"assembly_id": "ASSY-300", "consumed": {"LOT-B": 4}}
        ]
        result = assess_traceability(receipts(), issues(), broken, "2026-06-12")
        self.assertIn(("ASSY-300", "LOT-B"), result["unsourced_consumption"])
        lot_b = [lot for lot in result["lots"] if lot["lot_id"] == "LOT-B"][0]
        self.assertEqual(lot_b["verdict"], "broken-chain")

    def test_an_issue_from_an_unknown_lot_raises_a_finding(self):
        orphan = issues() + [
            {"lot_id": "LOT-Q", "assembly_id": "ASSY-100", "quantity_issued": 1}
        ]
        result = assess_traceability(receipts(), orphan, assemblies(), "2026-06-12")
        self.assertTrue(
            any("no receipt record owns" in finding for finding in result["findings"])
        )

    def test_a_stores_count_that_does_not_add_up_is_an_imbalance(self):
        records = receipts()
        records[0]["quantity_remaining"] = 5
        result = assess_traceability(records, issues(), assemblies(), "2026-06-12")
        lot_a = [lot for lot in result["lots"] if lot["lot_id"] == "LOT-A"][0]
        self.assertEqual(lot_a["verdict"], "quantity-imbalance")
        self.assertEqual(lot_a["reconciliation"]["difference"], -15)

    def test_scrapped_parts_are_accounted_for(self):
        records = receipts()
        records[0]["quantity_scrapped"] = 2
        records[0]["quantity_remaining"] = 18
        result = assess_traceability(records, issues(), assemblies(), "2026-06-12")
        lot_a = [lot for lot in result["lots"] if lot["lot_id"] == "LOT-A"][0]
        self.assertTrue(lot_a["reconciliation"]["balanced"])

    def test_a_lot_past_its_storage_limit_is_flagged(self):
        records = receipts()
        records[0]["storage_limit_days"] = 30
        result = assess_traceability(records, issues(), assemblies(), "2026-06-12")
        lot_a = [lot for lot in result["lots"] if lot["lot_id"] == "LOT-A"][0]
        self.assertEqual(lot_a["verdict"], "storage-limit-exceeded")
        self.assertFalse(lot_a["within_storage_limit"])

    def test_a_mixed_bin_raises_a_finding(self):
        records = receipts()
        records[1]["bin"] = "BIN-04"
        result = assess_traceability(records, issues(), assemblies(), "2026-06-12")
        self.assertEqual(len(result["mixed_bins"]), 1)
        self.assertFalse(result["trail_complete"])

    def test_two_receipts_owning_one_lot_rejected(self):
        records = receipts()
        records[1]["lot_id"] = "LOT-A"
        records[1]["bin"] = "BIN-11"
        with self.assertRaises(ValueError):
            assess_traceability(records, issues(), assemblies(), "2026-06-12")

    def test_empty_receipt_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability([], issues(), assemblies(), "2026-06-12")

    def test_issues_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            assess_traceability(receipts(), issues()[0], assemblies(), "2026-06-12")

    def test_zero_issue_quantity_rejected(self):
        bad = issues()
        bad[0]["quantity_issued"] = 0
        with self.assertRaises(ValueError):
            assess_traceability(receipts(), bad, assemblies(), "2026-06-12")

    def test_as_of_before_a_receipt_date_rejected(self):
        with self.assertRaises(ValueError):
            assess_traceability(receipts(), issues(), assemblies(), "2025-12-01")


if __name__ == "__main__":
    unittest.main()

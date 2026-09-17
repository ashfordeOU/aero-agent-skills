"""Contract tests for the clause 6.5.4 class 3 component traceability logic."""

import unittest

from q60_class_3_component_traceability_logic import (
    GRANULARITY_ORDER,
    REQUIRED_RECEIPT_FIELDS,
    USAGE_GRANULARITY_FLOOR,
    assembly_verdict,
    assess_class_3_traceability,
    batch_identifier_conflicts,
    chain_granularity,
    custody_chain,
    granularity_shortfall,
    missing_receipt_fields,
    out_of_order_records,
    parse_iso_date,
    receipt_granularity,
    reconcile_receipt,
    required_granularity,
    traceable_share,
    unrecorded_splits,
    unsourced_consumptions,
)


def receipts():
    return [
        {
            "receipt_id": "GR-2026-101",
            "part_number": "LMV321-SOT23",
            "quantity": 50,
            "received_date": "2026-03-02",
            "receipt_batch": "RB-2026-018",
            "date_code": "2412",
            "lot_id": "L-55",
        },
        {
            "receipt_id": "GR-2026-102",
            "part_number": "MMBT3904",
            "quantity": 200,
            "received_date": "2026-04-06",
            "receipt_batch": "RB-2026-019",
            "date_code": "2418",
        },
    ]


def issues():
    return [
        {
            "issue_id": "IS-0001",
            "receipt_id": "GR-2026-101",
            "to_assembly": "PCB-A",
            "quantity": 20,
            "issued_date": "2026-05-04",
        },
        {
            "issue_id": "IS-0002",
            "receipt_id": "GR-2026-102",
            "to_assembly": "PCB-B",
            "quantity": 60,
            "issued_date": "2026-05-11",
        },
    ]


def consumptions():
    return [
        {
            "assembly_id": "PCB-A",
            "receipt_id": "GR-2026-101",
            "quantity": 18,
            "fitted_date": "2026-06-01",
        },
        {
            "assembly_id": "PCB-B",
            "receipt_id": "GR-2026-102",
            "quantity": 55,
            "fitted_date": "2026-06-08",
        },
    ]


class GranularityTests(unittest.TestCase):
    def test_a_full_receipt_record_reaches_lot_identity(self):
        self.assertEqual(receipt_granularity(receipts()[0]), "lot")

    def test_a_receipt_without_a_lot_stops_at_the_receipt_batch(self):
        self.assertEqual(receipt_granularity(receipts()[1]), "receipt-batch")

    def test_a_receipt_with_no_part_number_carries_no_identity(self):
        self.assertEqual(receipt_granularity({"quantity": 5}), "none")

    def test_a_receipt_batch_without_a_date_code_cannot_claim_the_batch_level(self):
        receipt = dict(receipts()[0])
        del receipt["date_code"]
        self.assertEqual(receipt_granularity(receipt), "part-number")

    def test_a_serial_list_covering_the_delivery_reaches_serialised(self):
        receipt = dict(receipts()[0], quantity=3, serial_numbers=["s1", "s2", "s3"])
        self.assertEqual(receipt_granularity(receipt), "serialised")

    def test_a_short_serial_list_does_not_reach_serialised(self):
        receipt = dict(receipts()[0], quantity=3, serial_numbers=["s1", "s2"])
        self.assertEqual(receipt_granularity(receipt), "lot")

    def test_the_granularity_order_runs_coarse_to_fine(self):
        self.assertEqual(GRANULARITY_ORDER[0], "none")
        self.assertEqual(GRANULARITY_ORDER[-1], "serialised")

    def test_a_receipt_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            receipt_granularity("GR-2026-101")


class RequiredFieldTests(unittest.TestCase):
    def test_a_complete_receipt_is_missing_nothing(self):
        self.assertEqual(missing_receipt_fields(receipts()[0]), ())

    def test_an_absent_receipt_batch_is_named(self):
        receipt = dict(receipts()[0])
        del receipt["receipt_batch"]
        self.assertIn("receipt_batch", missing_receipt_fields(receipt))

    def test_a_zero_quantity_counts_as_missing(self):
        receipt = dict(receipts()[0], quantity=0)
        self.assertIn("quantity", missing_receipt_fields(receipt))

    def test_every_expected_field_is_checked(self):
        missing = missing_receipt_fields({})
        self.assertEqual(set(missing), set(REQUIRED_RECEIPT_FIELDS))


class DemandTests(unittest.TestCase):
    def test_flight_critical_demands_a_lot_identity(self):
        self.assertEqual(required_granularity("flight-critical"), "lot")

    def test_development_demands_only_the_part_number(self):
        self.assertEqual(required_granularity("development"), "part-number")

    def test_every_usage_maps_to_a_known_granularity(self):
        for usage in USAGE_GRANULARITY_FLOOR:
            self.assertIn(required_granularity(usage), GRANULARITY_ORDER)

    def test_an_unknown_usage_is_rejected(self):
        with self.assertRaises(ValueError):
            required_granularity("maybe-flight")

    def test_a_shortfall_is_reported_in_whole_steps(self):
        self.assertEqual(granularity_shortfall("date-code", "lot"), 2)

    def test_exceeding_the_demand_is_not_a_negative_shortfall(self):
        self.assertEqual(granularity_shortfall("serialised", "date-code"), 0)

    def test_an_unknown_granularity_is_rejected(self):
        with self.assertRaises(ValueError):
            granularity_shortfall("roughly", "lot")


class BatchIdentityTests(unittest.TestCase):
    def test_one_identifier_over_two_deliveries_is_a_conflict(self):
        records = receipts()
        records[1] = dict(records[1], receipt_batch="RB-2026-018")
        self.assertEqual(batch_identifier_conflicts(records), ("RB-2026-018",))

    def test_the_same_delivery_recorded_twice_is_not_a_conflict(self):
        records = receipts()
        records.append(dict(records[0], receipt_id="GR-2026-101-B"))
        self.assertEqual(batch_identifier_conflicts(records), ())

    def test_a_split_without_a_split_record_is_caught(self):
        records = issues()
        records[0] = dict(records[0], sub_batch="RB-2026-018-A")
        self.assertEqual(unrecorded_splits(records), ("IS-0001",))

    def test_a_split_with_a_split_record_is_accepted(self):
        records = issues()
        records[0] = dict(
            records[0], sub_batch="RB-2026-018-A", split_record="SPL-0007"
        )
        self.assertEqual(unrecorded_splits(records), ())

    def test_an_issue_without_an_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            unrecorded_splits([{"receipt_id": "GR-2026-101"}])


class ChainTests(unittest.TestCase):
    def test_a_complete_chain_reaches_the_receipt(self):
        chain = custody_chain(consumptions()[0], issues(), receipts())
        self.assertTrue(chain["complete"])
        self.assertEqual(chain["stages_reached"][-1], "receipt")
        self.assertIsNone(chain["broken_at"])

    def test_a_chain_with_no_issue_breaks_at_kitting(self):
        chain = custody_chain(consumptions()[0], [], receipts())
        self.assertFalse(chain["complete"])
        self.assertEqual(chain["broken_at"], "kitting")

    def test_a_chain_with_no_receipt_breaks_at_receipt(self):
        chain = custody_chain(consumptions()[0], issues(), [])
        self.assertEqual(chain["broken_at"], "receipt")

    def test_a_broken_chain_delivers_no_identity_at_all(self):
        chain = custody_chain(consumptions()[0], [], receipts())
        self.assertEqual(chain_granularity(chain), "none")

    def test_a_complete_chain_inherits_the_receipt_granularity(self):
        chain = custody_chain(consumptions()[0], issues(), receipts())
        self.assertEqual(chain_granularity(chain), "lot")

    def test_an_unrecorded_re_batch_drops_the_chain_to_the_date_code(self):
        records = issues()
        records[0] = dict(records[0], sub_batch="RB-2026-018-A")
        chain = custody_chain(consumptions()[0], records, receipts())
        self.assertEqual(chain_granularity(chain), "date-code")

    def test_a_consumption_missing_its_assembly_is_rejected(self):
        with self.assertRaises(ValueError):
            custody_chain({"receipt_id": "GR-2026-101"}, issues(), receipts())


class LedgerTests(unittest.TestCase):
    def test_the_ledger_balances_received_against_issued_and_scrapped(self):
        ledger = reconcile_receipt(receipts()[0], issues(), 5)
        self.assertEqual(ledger["received"], 50)
        self.assertEqual(ledger["issued"], 20)
        self.assertEqual(ledger["scrapped"], 5)
        self.assertEqual(ledger["remaining"], 25)

    def test_issuing_more_than_was_received_is_raised_not_reported(self):
        over = [dict(issues()[0], quantity=60)]
        with self.assertRaises(ValueError):
            reconcile_receipt(receipts()[0], over)

    def test_a_negative_scrap_count_is_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_receipt(receipts()[0], issues(), -1)

    def test_a_receipt_without_a_quantity_is_rejected(self):
        receipt = dict(receipts()[0])
        del receipt["quantity"]
        with self.assertRaises(ValueError):
            reconcile_receipt(receipt, issues())

    def test_an_assembly_consuming_an_unissued_receipt_is_named(self):
        offenders = unsourced_consumptions(consumptions(), [issues()[0]])
        self.assertEqual(len(offenders), 1)
        self.assertIn("PCB-B", offenders[0])

    def test_fully_issued_consumption_raises_nothing(self):
        self.assertEqual(unsourced_consumptions(consumptions(), issues()), ())


class DateOrderTests(unittest.TestCase):
    def test_an_issue_dated_after_the_fitting_is_caught(self):
        records = issues()
        records[0] = dict(records[0], issued_date="2026-07-01")
        chain = custody_chain(consumptions()[0], records, receipts())
        breaks = out_of_order_records(chain, consumptions()[0])
        self.assertTrue(any("dated after" in b for b in breaks))

    def test_a_receipt_dated_after_the_fitting_is_caught(self):
        records = receipts()
        records[0] = dict(records[0], received_date="2026-07-01")
        chain = custody_chain(consumptions()[0], issues(), records)
        breaks = out_of_order_records(chain, consumptions()[0])
        self.assertTrue(any("receipt" in b for b in breaks))

    def test_a_chain_in_order_reports_no_break(self):
        chain = custody_chain(consumptions()[0], issues(), receipts())
        self.assertEqual(out_of_order_records(chain, consumptions()[0]), ())

    def test_a_malformed_date_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("02/03/2026", "received_date")


class VerdictTests(unittest.TestCase):
    def test_an_incomplete_chain_is_broken_whatever_it_achieved(self):
        self.assertEqual(assembly_verdict("lot", "lot", False), "broken")

    def test_meeting_the_demand_is_traceable(self):
        self.assertEqual(assembly_verdict("lot", "lot", True), "traceable")

    def test_falling_short_of_the_demand_is_a_shortfall(self):
        self.assertEqual(assembly_verdict("date-code", "lot", True), "shortfall")

    def test_a_non_boolean_completeness_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assembly_verdict("lot", "lot", "yes")

    def test_the_traceable_share_is_exact_and_also_a_fraction(self):
        share = traceable_share(["traceable", "shortfall", "traceable", "broken"])
        self.assertEqual(share["numerator"], 2)
        self.assertEqual(share["denominator"], 4)
        self.assertAlmostEqual(share["fraction"], 0.5, places=9)

    def test_an_empty_verdict_list_divides_by_nothing(self):
        share = traceable_share([])
        self.assertEqual(share["denominator"], 0)
        self.assertAlmostEqual(share["fraction"], 0.0, places=9)

    def test_an_unknown_verdict_is_rejected(self):
        with self.assertRaises(ValueError):
            traceable_share(["mostly-fine"])


class AssessmentTests(unittest.TestCase):
    def test_a_clean_programme_is_traceable(self):
        result = assess_class_3_traceability(
            receipts(), issues(), consumptions(), "flight-non-critical"
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["traceable"])
        self.assertAlmostEqual(result["traceable_share"]["fraction"], 1.0, places=9)

    def test_a_flight_critical_demand_exposes_the_weaker_receipt(self):
        result = assess_class_3_traceability(
            receipts(), issues(), consumptions(), "flight-critical"
        )
        self.assertTrue(any("reaches only receipt-batch" in f for f in result["findings"]))
        self.assertAlmostEqual(result["traceable_share"]["fraction"], 0.5, places=9)

    def test_a_missing_issue_record_breaks_the_chain_and_is_reported_twice(self):
        result = assess_class_3_traceability(
            receipts(), [issues()[0]], consumptions(), "flight-non-critical"
        )
        self.assertTrue(any("no issue record" in f for f in result["findings"]))
        self.assertTrue(any("breaks at kitting" in f for f in result["findings"]))

    def test_a_shared_batch_identifier_is_reported(self):
        records = receipts()
        records[1] = dict(records[1], receipt_batch="RB-2026-018")
        result = assess_class_3_traceability(
            records, issues(), consumptions(), "flight-non-critical"
        )
        self.assertTrue(any("more than one delivery" in f for f in result["findings"]))

    def test_an_unrecorded_split_is_reported(self):
        records = issues()
        records[0] = dict(records[0], sub_batch="RB-2026-018-A")
        result = assess_class_3_traceability(
            receipts(), records, consumptions(), "flight-non-critical"
        )
        self.assertTrue(any("without a split record" in f for f in result["findings"]))

    def test_an_incomplete_receipt_record_is_reported(self):
        records = receipts()
        del records[0]["receipt_batch"]
        result = assess_class_3_traceability(
            records, issues(), consumptions(), "development"
        )
        self.assertTrue(any("is missing receipt_batch" in f for f in result["findings"]))

    def test_the_ledgers_cover_every_receipt(self):
        result = assess_class_3_traceability(
            receipts(), issues(), consumptions(), "flight-non-critical"
        )
        self.assertEqual(len(result["ledgers"]), 2)

    def test_an_unknown_usage_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_traceability(receipts(), issues(), consumptions(), "flighty")

    def test_receipts_that_are_not_a_sequence_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_traceability(
                "GR-2026-101", issues(), consumptions(), "development"
            )


if __name__ == "__main__":
    unittest.main()

"""Contract tests for the clause 4.3.4 pre-cap source inspection logic.

The cases walk the workflow one step at a time: where the witness point sits
relative to the seal, what may run between the two, who is allowed to
witness, the working-day notice arithmetic, the sample a lot owes, the waiver
route for a lot sealed without a witness, and the two-way reconciliation of
ordered lots against inspection records. Each limit is exercised on both
sides, and boundary ratios are compared with a representation-sized tolerance.
"""

import datetime
import unittest

from q60_class_1_precap_source_inspection_logic import (
    RESTRICTED_BETWEEN_INSPECTION_AND_SEAL,
    SAMPLE_TOLERANCE,
    WORKING_WEEKDAYS,
    assess_lot_inspection,
    assess_precap_campaign,
    normalize_token,
    notice_findings,
    parse_iso_date,
    required_sample_size,
    sequence_findings,
    witness_findings,
    working_days_between,
)

FLOW = [
    "die-attach",
    "wire-bond",
    "internal-cleaning",
    "pre-cap-visual-inspection",
    "seal",
    "seal-fine-leak",
    "external-visual",
]


def _policy(**overrides):
    policy = {
        "sample_percent": 10.0,
        "minimum_devices": 5,
        "required_notice_days": 10,
        "non_working_days": [],
    }
    policy.update(overrides)
    return policy


def _lot(**overrides):
    lot = {
        "lot_id": "LOT-A",
        "devices_in_lot": 200,
        "devices_inspected": 20,
        "flow": list(FLOW),
        "inspection_step": "pre-cap-visual-inspection",
        "seal_step": "seal",
        "witness": {
            "name": "source-inspector",
            "organisation": "customer-product-assurance",
            "independent_of_manufacturer": True,
        },
        "notification_date": "2026-03-02",
        "inspection_date": "2026-03-17",
    }
    lot.update(overrides)
    return lot


def _campaign(**overrides):
    campaign = {
        "order_reference": "PO-2026-118",
        "policy": _policy(),
        "ordered_lot_ids": ["LOT-A", "LOT-B"],
        "lots": [_lot(), _lot(lot_id="LOT-B")],
    }
    campaign.update(overrides)
    return campaign


class TokenAndDateTests(unittest.TestCase):
    def test_token_normalised(self):
        self.assertEqual(normalize_token("Pre_Cap Visual", "step"), "pre-cap-visual")

    def test_blank_token_refused(self):
        with self.assertRaises(ValueError):
            normalize_token("  ", "step")

    def test_iso_date_parsed(self):
        self.assertEqual(
            parse_iso_date("2026-03-02", "date"), datetime.date(2026, 3, 2)
        )

    def test_non_calendar_date_refused(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-13-02", "date")


class WorkingDayTests(unittest.TestCase):
    def test_weekend_is_not_a_working_day(self):
        self.assertNotIn(5, WORKING_WEEKDAYS)
        self.assertNotIn(6, WORKING_WEEKDAYS)

    def test_same_day_is_no_notice(self):
        self.assertEqual(working_days_between("2026-03-02", "2026-03-02"), 0)

    def test_one_full_week_counts_five(self):
        self.assertEqual(working_days_between("2026-03-02", "2026-03-09"), 5)

    def test_two_full_weeks_count_ten(self):
        self.assertEqual(working_days_between("2026-03-02", "2026-03-16"), 10)

    def test_declared_non_working_day_removed(self):
        self.assertEqual(
            working_days_between("2026-03-02", "2026-03-09", ["2026-03-04"]), 4
        )

    def test_non_working_day_outside_the_span_ignored(self):
        self.assertEqual(
            working_days_between("2026-03-02", "2026-03-09", ["2026-04-04"]), 5
        )

    def test_inspection_before_notification_refused(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-03-09", "2026-03-02")

    def test_non_collection_holidays_refused(self):
        with self.assertRaises(ValueError):
            working_days_between("2026-03-02", "2026-03-09", "2026-03-04")


class SampleSizeTests(unittest.TestCase):
    def test_percentage_applies_above_the_floor(self):
        self.assertEqual(required_sample_size(200, 10.0, 5), 20)

    def test_floor_applies_below_the_percentage(self):
        self.assertEqual(required_sample_size(20, 10.0, 5), 5)

    def test_partial_device_rounds_up(self):
        self.assertEqual(required_sample_size(101, 10.0, 5), 11)

    def test_product_landing_on_a_whole_number_does_not_round_up(self):
        # 375 * 8.8 / 100 lands a hair above 33 in binary, so a bare ceiling
        # would buy a thirty-fourth device on representation alone.
        self.assertEqual(required_sample_size(375, 8.8, 1), 33)

    def test_clean_product_is_taken_whole(self):
        self.assertEqual(required_sample_size(500, 2.0, 1), 10)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(required_sample_size(3, 100.0, 50), 3)

    def test_percentage_outside_the_range_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(200, 140.0, 5)

    def test_empty_lot_refused(self):
        with self.assertRaises(ValueError):
            required_sample_size(0, 10.0, 5)

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(SAMPLE_TOLERANCE, 1e-6)


class SequenceTests(unittest.TestCase):
    def test_witness_before_the_seal_raises_nothing(self):
        self.assertEqual(sequence_findings(FLOW, "pre-cap-visual-inspection", "seal"), [])

    def test_witness_after_the_seal_reported(self):
        findings = sequence_findings(FLOW, "seal-fine-leak", "seal")
        self.assertTrue(any("after the seal" in f for f in findings))

    def test_witness_on_the_seal_step_reported(self):
        findings = sequence_findings(FLOW, "seal", "seal")
        self.assertTrue(any("the same step" in f for f in findings))

    def test_rework_between_witness_and_seal_reported(self):
        flow = list(FLOW)
        flow.insert(flow.index("seal"), "rework")
        findings = sequence_findings(flow, "pre-cap-visual-inspection", "seal")
        self.assertTrue(any("never witnessed" in f for f in findings))

    def test_benign_step_between_witness_and_seal_accepted(self):
        flow = list(FLOW)
        flow.insert(flow.index("seal"), "lid-preform-load")
        self.assertEqual(sequence_findings(flow, "pre-cap-visual-inspection", "seal"), [])

    def test_restricted_steps_before_the_witness_are_fine(self):
        for token in RESTRICTED_BETWEEN_INSPECTION_AND_SEAL:
            if token in FLOW:
                self.assertLess(
                    FLOW.index(token), FLOW.index("pre-cap-visual-inspection")
                )
        self.assertEqual(sequence_findings(FLOW, "pre-cap-visual-inspection", "seal"), [])

    def test_step_absent_from_the_flow_refused(self):
        with self.assertRaises(ValueError):
            sequence_findings(FLOW, "x-ray", "seal")

    def test_repeated_step_in_the_flow_refused(self):
        with self.assertRaises(ValueError):
            sequence_findings(FLOW + ["seal"], "pre-cap-visual-inspection", "seal")

    def test_empty_flow_refused(self):
        with self.assertRaises(ValueError):
            sequence_findings([], "pre-cap-visual-inspection", "seal")


class WitnessTests(unittest.TestCase):
    def test_independent_witness_raises_nothing(self):
        self.assertEqual(witness_findings(_lot()["witness"]), [])

    def test_manufacturer_inspector_reported(self):
        witness = _lot()["witness"]
        witness["organisation"] = "manufacturer-quality"
        witness["independent_of_manufacturer"] = False
        findings = witness_findings(witness)
        self.assertTrue(any("in-house check" in f for f in findings))

    def test_blank_witness_name_refused(self):
        witness = _lot()["witness"]
        witness["name"] = "  "
        with self.assertRaises(ValueError):
            witness_findings(witness)

    def test_non_boolean_independence_refused(self):
        witness = _lot()["witness"]
        witness["independent_of_manufacturer"] = "yes"
        with self.assertRaises(ValueError):
            witness_findings(witness)

    def test_missing_witness_key_refused(self):
        with self.assertRaises(ValueError):
            witness_findings({"name": "a", "organisation": "b"})


class NoticeTests(unittest.TestCase):
    def test_sufficient_notice_raises_nothing(self):
        record = notice_findings("2026-03-02", "2026-03-16", 10)
        self.assertEqual(record["findings"], [])
        self.assertEqual(record["working_days_given"], 10)

    def test_exactly_the_required_notice_accepted(self):
        record = notice_findings("2026-03-02", "2026-03-16", 10)
        self.assertTrue(record["working_days_given"] >= record["working_days_required"])

    def test_short_notice_reported(self):
        record = notice_findings("2026-03-10", "2026-03-16", 10)
        self.assertTrue(any("short of the 10 required" in f for f in record["findings"]))

    def test_holiday_can_turn_sufficient_notice_short(self):
        record = notice_findings("2026-03-02", "2026-03-16", 10, ["2026-03-05"])
        self.assertEqual(record["working_days_given"], 9)
        self.assertTrue(record["findings"])


class LotRecordTests(unittest.TestCase):
    def test_clean_lot_is_acceptable(self):
        record = assess_lot_inspection(_lot(), _policy())
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["required_sample"], 20)

    def test_undersized_sample_reported(self):
        record = assess_lot_inspection(_lot(devices_inspected=6), _policy())
        self.assertTrue(any("short of the 20" in f for f in record["findings"]))

    def test_more_inspected_than_the_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_inspection(_lot(devices_inspected=500), _policy())

    def test_waived_lot_with_a_full_nonconformance_accepted(self):
        lot = {
            "lot_id": "LOT-C",
            "witnessed": False,
            "nonconformance": {
                "reference": "NCR-441",
                "alternative_route": "destructive-physical-analysis-on-sample",
            },
        }
        record = assess_lot_inspection(lot, _policy())
        self.assertTrue(record["acceptable"])
        self.assertFalse(record["witnessed"])

    def test_waived_lot_without_a_reference_reported(self):
        lot = {
            "lot_id": "LOT-C",
            "witnessed": False,
            "nonconformance": {"alternative_route": "dpa-on-sample"},
        }
        record = assess_lot_inspection(lot, _policy())
        self.assertTrue(any("without a nonconformance reference" in f for f in record["findings"]))

    def test_unwitnessed_lot_with_no_nonconformance_reported(self):
        record = assess_lot_inspection({"lot_id": "LOT-C", "witnessed": False}, _policy())
        self.assertTrue(any("no witnessed pre-cap inspection" in f for f in record["findings"]))

    def test_missing_lot_key_refused(self):
        lot = _lot()
        del lot["witness"]
        with self.assertRaises(ValueError):
            assess_lot_inspection(lot, _policy())

    def test_missing_policy_key_refused(self):
        policy = _policy()
        del policy["required_notice_days"]
        with self.assertRaises(ValueError):
            assess_lot_inspection(_lot(), policy)

    def test_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            assess_lot_inspection(["LOT-A"], _policy())


class CampaignTests(unittest.TestCase):
    def test_clean_campaign_is_complete(self):
        verdict = assess_precap_campaign(_campaign())
        self.assertTrue(verdict["campaign_complete"])
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["witnessed_fraction"], 1.0, places=9)

    def test_lot_with_no_record_reported(self):
        verdict = assess_precap_campaign(_campaign(lots=[_lot()]))
        self.assertEqual(verdict["unreported_lots"], ["LOT-B"])
        self.assertAlmostEqual(verdict["witnessed_fraction"], 0.5, places=9)

    def test_record_for_an_unordered_lot_reported(self):
        verdict = assess_precap_campaign(
            _campaign(ordered_lot_ids=["LOT-A"], lots=[_lot(), _lot(lot_id="LOT-B")])
        )
        self.assertEqual(verdict["surplus_records"], ["LOT-B"])

    def test_every_finding_is_carried_not_only_the_first(self):
        verdict = assess_precap_campaign(
            _campaign(
                lots=[
                    _lot(devices_inspected=6),
                    _lot(lot_id="LOT-B", notification_date="2026-03-12"),
                ]
            )
        )
        self.assertGreaterEqual(len(verdict["findings"]), 2)

    def test_lot_reported_twice_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_campaign(_campaign(lots=[_lot(), _lot()]))

    def test_lot_ordered_twice_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_campaign(_campaign(ordered_lot_ids=["LOT-A", "LOT-A"]))

    def test_empty_order_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_campaign(_campaign(ordered_lot_ids=[]))

    def test_missing_campaign_key_refused(self):
        campaign = _campaign()
        del campaign["policy"]
        with self.assertRaises(ValueError):
            assess_precap_campaign(campaign)

    def test_non_mapping_campaign_refused(self):
        with self.assertRaises(ValueError):
            assess_precap_campaign(["not", "a", "mapping"])

    def test_order_reference_echoed_in_the_record(self):
        verdict = assess_precap_campaign(_campaign())
        self.assertEqual(verdict["order_reference"], "PO-2026-118")

    def test_waived_lot_does_not_count_as_witnessed(self):
        verdict = assess_precap_campaign(
            _campaign(
                lots=[
                    _lot(),
                    {
                        "lot_id": "LOT-B",
                        "witnessed": False,
                        "nonconformance": {
                            "reference": "NCR-441",
                            "alternative_route": "dpa-on-sample",
                        },
                    },
                ]
            )
        )
        self.assertTrue(verdict["campaign_complete"])
        self.assertAlmostEqual(verdict["witnessed_fraction"], 0.5, places=9)


if __name__ == "__main__":
    unittest.main()

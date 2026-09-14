"""Contract tests for the clause 6.3.5 class 3 lot acceptance logic.

The cases follow the workflow one step at a time: the month parsing the age
rests on, the whole-month age itself, each escalation trigger and the way the
strictest one governs, the manufacturer data credit, the per-subgroup
purchaser verdicts on the accept number and the rate together, and the
batch-level disposition. Each limit is exercised on both sides, and the rate
boundary is compared with a tolerance rather than a strict inequality.
"""

import unittest

from q6013_class_3_lot_acceptance_logic import (
    CHANNEL_BASE_ROUTE,
    ROUTES,
    ROUTE_RANK,
    ROUTE_SUBGROUPS,
    SHELF_AGE_LIMIT_MONTHS,
    SUBGROUPS_FULL,
    SUBGROUPS_REDUCED,
    assess_lot_acceptance,
    lot_age_months,
    manufacturer_data_record,
    month_index,
    parse_month,
    purchaser_test_record,
    required_route,
    route_escalations,
)


def _lot(**overrides):
    lot = {
        "lot_reference": "LOT-4471",
        "source_channel": "franchised-distributor",
        "manufacture_month": "2025-06",
        "assessment_month": "2026-04",
        "process_change_notice_open": False,
        "single_point_failure": False,
        "quality_system_certificate": {"reference": "QMS-9001-772", "expiry_month": "2027-01"},
        "manufacturer_data": {
            "reference": "MFG-QCI-8802",
            "issue": "C",
            "covers_month": "2025-06",
        },
        "purchaser_tests": [],
    }
    lot.update(overrides)
    return lot


def _test(subgroup, sample, failures, accept, allowance=100.0):
    return {
        "subgroup": subgroup,
        "sample_size": sample,
        "failures": failures,
        "accept_number": accept,
        "allowable_percent_defective": allowance,
    }


class MonthTests(unittest.TestCase):
    def test_parses_a_well_formed_month(self):
        self.assertEqual(parse_month("manufacture_month", "2025-06"), (2025, 6))

    def test_month_thirteen_rejected(self):
        with self.assertRaises(ValueError):
            parse_month("manufacture_month", "2025-13")

    def test_short_form_rejected(self):
        with self.assertRaises(ValueError):
            parse_month("manufacture_month", "2025-6")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_month("manufacture_month", 202506)

    def test_index_differences_cross_a_year_end(self):
        self.assertEqual(
            month_index((2026, 1)) - month_index((2025, 11)), 2
        )


class AgeTests(unittest.TestCase):
    def test_age_in_whole_months(self):
        self.assertEqual(lot_age_months("2025-06", "2026-04"), 10)

    def test_same_month_is_zero(self):
        self.assertEqual(lot_age_months("2026-04", "2026-04"), 0)

    def test_assessment_before_the_build_rejected(self):
        with self.assertRaises(ValueError):
            lot_age_months("2026-05", "2026-04")

    def test_age_exactly_on_the_limit_does_not_escalate(self):
        escalation = route_escalations(_lot(manufacture_month="2024-04", assessment_month="2026-04"))
        self.assertEqual(escalation["age_months"], SHELF_AGE_LIMIT_MONTHS)
        self.assertTrue(all("shelf-age" not in t["reason"] for t in escalation["triggers"]))

    def test_age_one_month_past_the_limit_escalates(self):
        escalation = route_escalations(_lot(manufacture_month="2024-03", assessment_month="2026-04"))
        self.assertTrue(any("shelf-age" in t["reason"] for t in escalation["triggers"]))


class RoutingTests(unittest.TestCase):
    def test_controlled_channel_stays_on_the_data_route(self):
        self.assertEqual(required_route(_lot())["route"], "manufacturer-standard-data")

    def test_manufacturer_direct_also_stays_on_the_data_route(self):
        self.assertEqual(
            required_route(_lot(source_channel="manufacturer-direct"))["route"],
            "manufacturer-standard-data",
        )

    def test_broker_channel_forces_the_full_campaign(self):
        self.assertEqual(
            required_route(_lot(source_channel="independent-broker"))["route"],
            "full-purchaser-lat",
        )

    def test_open_process_change_notice_forces_the_reduced_campaign(self):
        routing = required_route(_lot(process_change_notice_open=True))
        self.assertEqual(routing["route"], "reduced-purchaser-lat")

    def test_missing_certificate_forces_the_full_campaign(self):
        routing = required_route(_lot(quality_system_certificate=None))
        self.assertEqual(routing["route"], "full-purchaser-lat")

    def test_certificate_expiring_in_the_assessment_month_is_still_live(self):
        routing = required_route(
            _lot(quality_system_certificate={"reference": "QMS-1", "expiry_month": "2026-04"})
        )
        self.assertEqual(routing["route"], "manufacturer-standard-data")

    def test_certificate_expired_the_month_before_is_not_live(self):
        routing = required_route(
            _lot(quality_system_certificate={"reference": "QMS-1", "expiry_month": "2026-03"})
        )
        self.assertEqual(routing["route"], "full-purchaser-lat")

    def test_certificate_without_a_reference_is_not_live(self):
        routing = required_route(
            _lot(quality_system_certificate={"expiry_month": "2027-01"})
        )
        self.assertEqual(routing["route"], "full-purchaser-lat")

    def test_single_point_failure_forces_the_full_campaign(self):
        self.assertEqual(
            required_route(_lot(single_point_failure=True))["route"], "full-purchaser-lat"
        )

    def test_strictest_trigger_governs_and_the_lighter_one_survives(self):
        routing = required_route(_lot(process_change_notice_open=True, single_point_failure=True))
        self.assertEqual(routing["route"], "full-purchaser-lat")
        reasons = [trigger["reason"] for trigger in routing["triggers"]]
        self.assertTrue(any("process change notice" in reason for reason in reasons))

    def test_triggers_are_ordered_lightest_route_first(self):
        routing = required_route(_lot(process_change_notice_open=True, single_point_failure=True))
        ranks = [ROUTE_RANK[trigger["route"]] for trigger in routing["triggers"]]
        self.assertEqual(ranks, sorted(ranks))

    def test_route_names_its_subgroups(self):
        routing = required_route(_lot(source_channel="independent-broker"))
        self.assertEqual(routing["required_subgroups"], list(SUBGROUPS_FULL))

    def test_unknown_channel_rejected(self):
        with self.assertRaises(ValueError):
            required_route(_lot(source_channel="a-friend-of-the-buyer"))

    def test_non_boolean_change_notice_rejected(self):
        with self.assertRaises(ValueError):
            required_route(_lot(process_change_notice_open="no"))

    def test_reduced_subgroups_are_a_subset_of_the_full_set(self):
        self.assertTrue(set(SUBGROUPS_REDUCED).issubset(set(SUBGROUPS_FULL)))

    def test_every_route_has_a_subgroup_entry(self):
        self.assertEqual(set(ROUTE_SUBGROUPS), set(ROUTES))

    def test_every_channel_maps_to_a_known_route(self):
        self.assertTrue(set(CHANNEL_BASE_ROUTE.values()).issubset(set(ROUTES)))


class ManufacturerDataTests(unittest.TestCase):
    def test_complete_report_for_the_build_month_credited(self):
        record = manufacturer_data_record(
            {"reference": "MFG-QCI-8802", "issue": "C", "covers_month": "2025-06"}, "2025-06"
        )
        self.assertTrue(record["credited"])

    def test_report_without_an_issue_not_credited(self):
        record = manufacturer_data_record(
            {"reference": "MFG-QCI-8802", "covers_month": "2025-06"}, "2025-06"
        )
        self.assertFalse(record["credited"])
        self.assertIn("issue", record["missing"])

    def test_report_for_another_build_month_not_credited(self):
        record = manufacturer_data_record(
            {"reference": "MFG-QCI-8802", "issue": "C", "covers_month": "2025-05"}, "2025-06"
        )
        self.assertFalse(record["credited"])

    def test_absent_report_not_credited(self):
        record = manufacturer_data_record(None, "2025-06")
        self.assertFalse(record["credited"])
        self.assertEqual(record["missing"], ["manufacturer_data"])

    def test_non_mapping_report_rejected(self):
        with self.assertRaises(ValueError):
            manufacturer_data_record("MFG-QCI-8802", "2025-06")


class PurchaserCampaignTests(unittest.TestCase):
    def test_all_subgroups_present_and_passing(self):
        record = purchaser_test_record(
            [_test("electrical-end-point", 50, 0, 1), _test("external-visual", 50, 1, 1)],
            SUBGROUPS_REDUCED,
        )
        self.assertTrue(record["accepted"])

    def test_missing_subgroup_is_uncovered(self):
        record = purchaser_test_record(
            [_test("electrical-end-point", 50, 0, 1)], SUBGROUPS_REDUCED
        )
        self.assertFalse(record["accepted"])
        self.assertEqual(record["uncovered"], ["external-visual"])

    def test_failures_over_the_accept_number_reject(self):
        record = purchaser_test_record(
            [_test("electrical-end-point", 50, 2, 1), _test("external-visual", 50, 0, 1)],
            SUBGROUPS_REDUCED,
        )
        self.assertEqual(record["rejecting"], ["electrical-end-point"])

    def test_rate_exactly_on_the_allowance_is_accepted(self):
        record = purchaser_test_record(
            [_test("electrical-end-point", 40, 1, 2, 2.5), _test("external-visual", 40, 0, 2, 2.5)],
            SUBGROUPS_REDUCED,
        )
        observed = record["subgroups"]["electrical-end-point"]["observed_percent_defective"]
        self.assertAlmostEqual(observed, 2.5, places=9)
        self.assertTrue(record["subgroups"]["electrical-end-point"]["within_allowance"])

    def test_rate_over_the_allowance_rejects_even_inside_the_accept_number(self):
        record = purchaser_test_record(
            [_test("electrical-end-point", 20, 1, 2, 2.5), _test("external-visual", 20, 0, 2, 2.5)],
            SUBGROUPS_REDUCED,
        )
        entry = record["subgroups"]["electrical-end-point"]
        self.assertTrue(entry["within_accept_number"])
        self.assertFalse(entry["within_allowance"])
        self.assertFalse(entry["accepted"])

    def test_subgroup_beyond_the_route_is_listed_not_counted(self):
        record = purchaser_test_record(
            [
                _test("electrical-end-point", 50, 0, 1),
                _test("external-visual", 50, 0, 1),
                _test("endurance-life", 20, 0, 0),
            ],
            SUBGROUPS_REDUCED,
        )
        self.assertTrue(record["accepted"])
        self.assertEqual(record["beyond_the_route"], ["endurance-life"])

    def test_duplicate_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_record(
                [_test("external-visual", 50, 0, 1), _test("external-visual", 20, 0, 1)],
                SUBGROUPS_REDUCED,
            )

    def test_unknown_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_record([_test("vibration-shake", 50, 0, 1)], SUBGROUPS_REDUCED)

    def test_failures_exceeding_the_sample_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_record([_test("external-visual", 5, 6, 1)], SUBGROUPS_REDUCED)

    def test_zero_sample_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_record([_test("external-visual", 0, 0, 1)], SUBGROUPS_REDUCED)

    def test_allowance_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            purchaser_test_record([_test("external-visual", 50, 0, 1, 140.0)], SUBGROUPS_REDUCED)

    def test_empty_campaign_leaves_every_subgroup_uncovered(self):
        record = purchaser_test_record(None, SUBGROUPS_FULL)
        self.assertEqual(record["uncovered"], list(SUBGROUPS_FULL))


class AssessmentTests(unittest.TestCase):
    def test_controlled_batch_accepted_on_manufacturer_data(self):
        result = assess_lot_acceptance(_lot())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["disposition"], "accept-lot")
        self.assertEqual(result["route"], "manufacturer-standard-data")
        self.assertEqual(result["findings"], [])

    def test_data_route_without_a_credited_report_holds_the_batch(self):
        result = assess_lot_acceptance(_lot(manufacturer_data=None))
        self.assertFalse(result["accepted"])
        self.assertEqual(result["disposition"], "hold-lot")

    def test_broker_batch_with_the_full_campaign_accepted(self):
        result = assess_lot_acceptance(
            _lot(
                source_channel="independent-broker",
                purchaser_tests=[
                    _test("electrical-end-point", 50, 0, 1),
                    _test("external-visual", 50, 0, 1),
                    _test("mechanical-and-environmental", 22, 0, 0),
                    _test("endurance-life", 22, 0, 0),
                ],
            )
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["route"], "full-purchaser-lat")

    def test_broker_batch_with_no_campaign_holds_on_every_subgroup(self):
        result = assess_lot_acceptance(_lot(source_channel="independent-broker"))
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["campaign"]["uncovered"]), len(SUBGROUPS_FULL))

    def test_manufacturer_data_does_not_fill_an_escalated_subgroup(self):
        result = assess_lot_acceptance(_lot(source_channel="independent-broker"))
        self.assertTrue(result["manufacturer_data"]["credited"])
        self.assertTrue(
            any("the escalation is what put the subgroup there" in f for f in result["findings"])
        )

    def test_aged_batch_moves_to_the_reduced_campaign(self):
        result = assess_lot_acceptance(
            _lot(
                manufacture_month="2023-01",
                purchaser_tests=[
                    _test("electrical-end-point", 50, 0, 1),
                    _test("external-visual", 50, 0, 1),
                ],
            )
        )
        self.assertEqual(result["route"], "reduced-purchaser-lat")
        self.assertTrue(result["accepted"])

    def test_rate_failure_is_reported_separately_from_the_count(self):
        result = assess_lot_acceptance(
            _lot(
                process_change_notice_open=True,
                purchaser_tests=[
                    _test("electrical-end-point", 20, 1, 2, 2.5),
                    _test("external-visual", 20, 0, 2, 2.5),
                ],
            )
        )
        self.assertFalse(result["accepted"])
        self.assertTrue(any("percent defective" in f for f in result["findings"]))

    def test_age_is_reported_with_the_verdict(self):
        self.assertEqual(assess_lot_acceptance(_lot())["age_months"], 10)

    def test_missing_lot_reference_rejected(self):
        lot = _lot()
        del lot["lot_reference"]
        with self.assertRaises(ValueError):
            assess_lot_acceptance(lot)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_acceptance(["not", "a", "mapping"])


if __name__ == "__main__":
    unittest.main()

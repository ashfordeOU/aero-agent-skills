"""Contract tests for the clause 6.3.10 expired stock relifing logic."""

import unittest

from q60_class_3_stock_relifing_logic import (
    PACKAGE_SEALS,
    RELIFE_DISPOSITIONS,
    REQUIRED_LOT_FIELDS,
    assess_relifing_stock,
    campaign_priority,
    effective_grant_days,
    elapsed_storage_days,
    lot_disposition,
    manufacture_date,
    outstanding_evidence,
    owed_relife_tests,
    parse_date_code,
    period_expired,
    relife_grant_days,
    total_life_headroom_days,
)

AS_OF = "2026-06-12"


def lot(**overrides):
    record = {
        "lot_id": "LOT-A",
        "part_number": "rh1020-ccg84b",
        "date_code": "2312",
        "quantity": 50,
        "storage_period_days": 730,
        "relife_cycles_used": 0,
        "package_seal": "dry-pack-sealed",
        "stored_since": "2023-04-01",
        "build_demand": 20,
        "moisture_sensitivity_level": 1,
        "hermetic": False,
        "recorded_results": {
            "external-visual": "pass",
            "solderability-sample": "pass",
        },
    }
    record.update(overrides)
    return record


def stock():
    return [
        lot(),
        lot(
            lot_id="LOT-B",
            date_code="2320",
            quantity=30,
            build_demand=9,
            stored_since="2023-06-01",
        ),
    ]


class DateCodeTests(unittest.TestCase):
    def test_a_four_digit_code_parses_to_year_and_week(self):
        self.assertEqual(parse_date_code("2312"), (2023, 12))

    def test_a_short_code_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("231")

    def test_a_non_numeric_code_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("23AB")

    def test_week_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2300")

    def test_week_fifty_four_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_date_code("2354")

    def test_manufacture_date_is_the_monday_of_that_week(self):
        made = manufacture_date("2312")
        self.assertEqual(made.isoformat(), "2023-03-20")
        self.assertEqual(made.weekday(), 0)

    def test_a_week_the_year_does_not_have_is_rejected(self):
        with self.assertRaises(ValueError):
            manufacture_date("2353")


class TotalLifeTests(unittest.TestCase):
    def test_headroom_is_the_life_left_from_the_manufacture_week(self):
        self.assertEqual(total_life_headroom_days("2312", AS_OF, 5), 645)

    def test_a_part_past_its_total_life_has_no_headroom_rather_than_a_debt(self):
        self.assertEqual(total_life_headroom_days("2312", AS_OF, 2), 0)

    def test_an_as_of_before_manufacture_is_rejected(self):
        with self.assertRaises(ValueError):
            total_life_headroom_days("2312", "2022-01-01", 5)

    def test_a_zero_life_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            total_life_headroom_days("2312", AS_OF, 0)


class StoragePeriodTests(unittest.TestCase):
    def test_elapsed_storage_counts_calendar_days(self):
        self.assertEqual(elapsed_storage_days("2026-01-12", "2026-01-22"), 10)

    def test_a_lot_inside_its_period_is_not_expired(self):
        self.assertFalse(period_expired("2026-01-12", "2026-01-22", 730))

    def test_a_lot_exactly_on_its_period_is_not_expired(self):
        self.assertFalse(period_expired("2026-01-12", "2026-01-22", 10))

    def test_a_lot_one_day_past_its_period_is_expired(self):
        self.assertTrue(period_expired("2026-01-12", "2026-01-23", 10))

    def test_an_as_of_before_the_storage_start_is_rejected(self):
        with self.assertRaises(ValueError):
            elapsed_storage_days("2026-01-12", "2025-12-31")

    def test_a_zero_storage_period_is_rejected(self):
        with self.assertRaises(ValueError):
            period_expired("2026-01-12", "2026-01-22", 0)


class GrantTests(unittest.TestCase):
    def test_the_first_cycle_earns_half_the_issued_period(self):
        self.assertEqual(relife_grant_days(730, 0), 365)

    def test_each_further_cycle_earns_a_smaller_share(self):
        self.assertEqual(relife_grant_days(730, 1), 182)
        self.assertEqual(relife_grant_days(730, 2), 91)

    def test_a_spent_cycle_allowance_earns_nothing(self):
        self.assertEqual(relife_grant_days(730, 3, max_relife_cycles=3), 0)

    def test_a_share_that_does_not_decay_is_rejected(self):
        with self.assertRaises(ValueError):
            relife_grant_days(730, 0, share_numerator=2, share_denominator=2)

    def test_a_negative_cycle_count_is_rejected(self):
        with self.assertRaises(ValueError):
            relife_grant_days(730, -1)

    def test_a_boolean_cycle_count_is_rejected(self):
        with self.assertRaises(ValueError):
            relife_grant_days(730, True)

    def test_the_grant_is_trimmed_to_the_life_that_is_left(self):
        self.assertEqual(effective_grant_days(365, 90), 90)

    def test_a_grant_inside_the_headroom_is_left_alone(self):
        self.assertEqual(effective_grant_days(365, 645), 365)


class OwedEvidenceTests(unittest.TestCase):
    def test_a_sealed_dry_pack_owes_the_base_set(self):
        self.assertEqual(
            owed_relife_tests("dry-pack-sealed", 1),
            ("external-visual", "solderability-sample"),
        )

    def test_an_opened_moisture_sensitive_pack_owes_a_bake(self):
        self.assertIn("moisture-bake", owed_relife_tests("dry-pack-opened", 3))

    def test_an_opened_pack_that_is_not_moisture_sensitive_owes_no_bake(self):
        self.assertNotIn("moisture-bake", owed_relife_tests("dry-pack-opened", 1))

    def test_an_uncontrolled_bag_reopens_electrical_reverification(self):
        self.assertIn(
            "electrical-ambient-reverification",
            owed_relife_tests("uncontrolled-bag", 1),
        )

    def test_a_hermetic_part_owes_a_leak_check(self):
        self.assertIn(
            "fine-and-gross-leak",
            owed_relife_tests("hermetic-tray", 1, hermetic=True),
        )

    def test_an_unknown_package_seal_is_rejected(self):
        with self.assertRaises(ValueError):
            owed_relife_tests("cardboard-box", 1)

    def test_a_moisture_level_outside_the_scale_is_rejected(self):
        with self.assertRaises(ValueError):
            owed_relife_tests("dry-pack-opened", 9)

    def test_every_seal_returns_a_non_empty_owed_set(self):
        for seal in PACKAGE_SEALS:
            self.assertTrue(owed_relife_tests(seal, 3))

    def test_an_owed_test_with_no_record_is_missing_not_a_pass(self):
        split = outstanding_evidence(
            ("external-visual", "solderability-sample"),
            {"external-visual": "pass"},
        )
        self.assertEqual(split["missing"], ("solderability-sample",))
        self.assertEqual(split["failed"], ())

    def test_a_failed_record_is_separated_from_a_missing_one(self):
        split = outstanding_evidence(
            ("external-visual", "solderability-sample"),
            {"external-visual": "fail", "solderability-sample": "pass"},
        )
        self.assertEqual(split["failed"], ("external-visual",))
        self.assertEqual(split["missing"], ())

    def test_an_unknown_result_word_is_rejected(self):
        with self.assertRaises(ValueError):
            outstanding_evidence(("external-visual",), {"external-visual": "maybe"})


class DispositionTests(unittest.TestCase):
    def test_a_lot_still_inside_its_period_needs_no_relife(self):
        self.assertEqual(lot_disposition(False, 365, 645, (), ()), "in-period")

    def test_a_complete_expired_lot_is_granted(self):
        self.assertEqual(lot_disposition(True, 365, 645, (), ()), "relife-granted")

    def test_missing_evidence_makes_the_grant_conditional(self):
        self.assertEqual(
            lot_disposition(True, 365, 645, ("moisture-bake",), ()),
            "relife-conditional",
        )

    def test_a_solderability_failure_goes_to_rescreening(self):
        self.assertEqual(
            lot_disposition(True, 365, 645, (), ("solderability-sample",)),
            "rescreening-referral",
        )

    def test_any_other_failure_scraps_the_lot(self):
        self.assertEqual(
            lot_disposition(True, 365, 645, (), ("fine-and-gross-leak",)), "scrap"
        )

    def test_no_headroom_scraps_the_lot_even_with_clean_evidence(self):
        self.assertEqual(lot_disposition(True, 365, 0, (), ()), "scrap")

    def test_a_spent_grant_scraps_the_lot(self):
        self.assertEqual(lot_disposition(True, 0, 645, (), ()), "scrap")

    def test_every_disposition_returned_is_a_known_disposition(self):
        for expired in (True, False):
            for grant in (0, 365):
                for headroom in (0, 645):
                    self.assertIn(
                        lot_disposition(expired, grant, headroom, (), ()),
                        RELIFE_DISPOSITIONS,
                    )

    def test_a_non_boolean_expiry_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_disposition(1, 365, 645, (), ())


class PriorityTests(unittest.TestCase):
    def test_priority_is_the_demand_one_test_slot_releases(self):
        self.assertAlmostEqual(campaign_priority(20, 2), 10.0, places=9)

    def test_a_wider_owed_set_lowers_the_priority(self):
        self.assertAlmostEqual(campaign_priority(20, 4), 5.0, places=9)

    def test_a_lot_nobody_has_asked_for_scores_zero(self):
        self.assertAlmostEqual(campaign_priority(0, 2), 0.0, places=9)

    def test_a_zero_owed_set_is_rejected(self):
        with self.assertRaises(ValueError):
            campaign_priority(20, 0)


class AssessStockTests(unittest.TestCase):
    def test_a_clean_expired_stock_is_granted_throughout(self):
        result = assess_relifing_stock(stock(), AS_OF)
        self.assertEqual(result["lot_count"], 2)
        for entry in result["lots"]:
            self.assertEqual(entry["disposition"], "relife-granted")
        self.assertTrue(result["stock_clear"])

    def test_the_renewed_period_is_the_trimmed_grant(self):
        result = assess_relifing_stock(stock(), AS_OF)
        first = result["lots"][0]
        self.assertEqual(first["headroom_days"], 645)
        self.assertEqual(first["renewed_period_days"], 365)

    def test_a_lot_inside_its_period_is_left_in_period(self):
        records = stock()
        records[0]["storage_period_days"] = 3650
        result = assess_relifing_stock(records, AS_OF)
        self.assertEqual(result["lots"][0]["disposition"], "in-period")

    def test_a_lot_with_no_life_left_is_scrapped(self):
        result = assess_relifing_stock(stock(), AS_OF, total_life_years=2)
        self.assertEqual(result["scrap_lot_ids"], ("LOT-A", "LOT-B"))

    def test_a_missing_record_becomes_a_finding_and_a_conditional_grant(self):
        records = stock()
        records[0]["recorded_results"] = {"external-visual": "pass"}
        result = assess_relifing_stock(records, AS_OF)
        self.assertEqual(result["lots"][0]["disposition"], "relife-conditional")
        self.assertTrue(
            any("has no record of it" in note for note in result["findings"])
        )

    def test_capacity_is_allocated_to_the_higher_priority_lot_first(self):
        result = assess_relifing_stock(stock(), AS_OF, test_capacity=2)
        self.assertEqual(result["scheduled"], ("LOT-A",))
        self.assertEqual(result["deferred"], ("LOT-B",))
        self.assertEqual(result["capacity_used"], 2)

    def test_ample_capacity_schedules_every_workable_lot(self):
        result = assess_relifing_stock(stock(), AS_OF, test_capacity=10)
        self.assertEqual(set(result["scheduled"]), {"LOT-A", "LOT-B"})
        self.assertEqual(result["deferred"], ())

    def test_demand_coverage_reports_the_share_the_campaign_releases(self):
        result = assess_relifing_stock(stock(), AS_OF, test_capacity=2)
        self.assertEqual(result["demand_total"], 29)
        self.assertEqual(result["demand_covered"], 20)
        self.assertAlmostEqual(result["demand_coverage"], 20 / 29, places=9)

    def test_a_duplicate_lot_id_is_rejected(self):
        records = stock()
        records[1]["lot_id"] = "LOT-A"
        with self.assertRaises(ValueError):
            assess_relifing_stock(records, AS_OF)

    def test_an_empty_stock_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_relifing_stock([], AS_OF)

    def test_every_required_lot_field_is_enforced(self):
        for field in REQUIRED_LOT_FIELDS:
            record = lot()
            record[field] = ""
            with self.assertRaises(ValueError):
                assess_relifing_stock([record], AS_OF)

    def test_demand_larger_than_the_lot_is_rejected(self):
        records = stock()
        records[0]["build_demand"] = 500
        with self.assertRaises(ValueError):
            assess_relifing_stock(records, AS_OF)

    def test_a_spent_cycle_allowance_is_reported_as_a_finding(self):
        records = stock()
        records[0]["relife_cycles_used"] = 3
        result = assess_relifing_stock(records, AS_OF)
        self.assertIn("LOT-A", result["scrap_lot_ids"])
        self.assertTrue(
            any("relife cycles" in note for note in result["findings"])
        )


if __name__ == "__main__":
    unittest.main()

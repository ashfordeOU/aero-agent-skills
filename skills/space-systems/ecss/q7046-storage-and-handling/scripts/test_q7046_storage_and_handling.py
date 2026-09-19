#!/usr/bin/env python3
"""Contract test for fastener storage and handling (offline)."""

import copy
import datetime
import unittest

from q7046_storage_and_handling_logic import (
    ISSUE_QUARANTINE,
    ISSUE_REINSPECT,
    ISSUE_RELEASE,
    ISSUE_REPRESERVE,
    PROTECTIONS,
    STORAGE_CLASSES,
    STORAGE_CONTROLLED,
    STORAGE_UNCONTROLLED,
    assess_storage,
    environment_verdict,
    expiry_date,
    handling_findings,
    life_start_date,
    reinspection_interval_months,
    remaining_life_days,
    shelf_life_months,
)

DATE = datetime.date

GOOD_CASE = {
    "lot_id": "LOT-7046-A",
    "protection": "plated",
    "storage_class": STORAGE_CONTROLLED,
    "manufacture_date": DATE(2025, 1, 15),
    "today": DATE(2026, 1, 15),
    "temperature_c": 20.0,
    "relative_humidity_pct": 40.0,
    "lots_in_container": 1,
    "issue_order": "oldest-first",
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ShelfLifeTests(unittest.TestCase):
    def test_a_controlled_store_always_buys_more_life(self):
        for protection in PROTECTIONS:
            self.assertGreater(
                shelf_life_months(protection, STORAGE_CONTROLLED),
                shelf_life_months(protection, STORAGE_UNCONTROLLED),
            )

    def test_better_protection_buys_more_life_in_one_store(self):
        self.assertGreater(
            shelf_life_months("sealed-desiccated", STORAGE_CONTROLLED),
            shelf_life_months("bare-passivated", STORAGE_CONTROLLED),
        )

    def test_every_combination_has_a_positive_life(self):
        for protection in PROTECTIONS:
            for storage in STORAGE_CLASSES:
                self.assertGreater(shelf_life_months(protection, storage), 0)

    def test_the_reinspection_interval_is_shorter_than_the_life(self):
        for protection in PROTECTIONS:
            for storage in STORAGE_CLASSES:
                self.assertLess(
                    reinspection_interval_months(protection, storage),
                    shelf_life_months(protection, storage),
                )

    def test_unknown_protection_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_months("wrapped-in-a-rag", STORAGE_CONTROLLED)

    def test_unknown_storage_class_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_months("plated", "the-van")


class ExpiryTests(unittest.TestCase):
    def test_expiry_is_the_life_after_manufacture(self):
        self.assertEqual(
            expiry_date(DATE(2025, 1, 15), "plated", STORAGE_CONTROLLED),
            DATE(2030, 1, 15),
        )

    def test_a_month_end_date_clamps_to_the_shorter_month(self):
        self.assertEqual(
            expiry_date(DATE(2025, 1, 31), "bare-passivated", STORAGE_UNCONTROLLED),
            DATE(2025, 7, 31),
        )

    def test_a_february_clamp_lands_on_the_last_valid_day(self):
        self.assertEqual(
            expiry_date(DATE(2024, 8, 31), "bare-passivated", STORAGE_UNCONTROLLED),
            DATE(2025, 2, 28),
        )

    def test_a_breach_restarts_the_clock_rather_than_pausing_it(self):
        clean = expiry_date(DATE(2025, 1, 15), "plated", STORAGE_CONTROLLED)
        breached = expiry_date(
            DATE(2025, 1, 15), "plated", STORAGE_CONTROLLED, DATE(2026, 6, 1)
        )
        self.assertGreater(breached, clean)

    def test_a_breach_before_manufacture_is_rejected(self):
        with self.assertRaises(ValueError):
            life_start_date(DATE(2025, 1, 15), DATE(2024, 12, 1))

    def test_the_clock_runs_from_manufacture_when_the_package_is_intact(self):
        self.assertEqual(life_start_date(DATE(2025, 1, 15)), DATE(2025, 1, 15))

    def test_a_non_date_manufacture_value_is_rejected(self):
        with self.assertRaises(ValueError):
            expiry_date("2025-01-15", "plated", STORAGE_CONTROLLED)


class RemainingLifeTests(unittest.TestCase):
    def test_remaining_life_counts_down(self):
        early = remaining_life_days(
            DATE(2025, 1, 1), "plated", STORAGE_CONTROLLED, DATE(2025, 6, 1)
        )
        later = remaining_life_days(
            DATE(2025, 1, 1), "plated", STORAGE_CONTROLLED, DATE(2026, 6, 1)
        )
        self.assertGreater(early, later)

    def test_remaining_life_is_zero_on_the_expiry_date(self):
        expiry = expiry_date(DATE(2025, 1, 1), "plated", STORAGE_CONTROLLED)
        self.assertEqual(
            remaining_life_days(
                DATE(2025, 1, 1), "plated", STORAGE_CONTROLLED, expiry
            ),
            0,
        )

    def test_remaining_life_goes_negative_past_expiry(self):
        self.assertLess(
            remaining_life_days(
                DATE(2020, 1, 1), "bare-passivated", STORAGE_UNCONTROLLED,
                DATE(2026, 1, 1)
            ),
            0,
        )

    def test_a_date_before_manufacture_is_rejected(self):
        with self.assertRaises(ValueError):
            remaining_life_days(
                DATE(2025, 1, 1), "plated", STORAGE_CONTROLLED, DATE(2024, 1, 1)
            )


class EnvironmentTests(unittest.TestCase):
    def test_a_nominal_controlled_store_is_within_limits(self):
        self.assertTrue(
            environment_verdict(STORAGE_CONTROLLED, 20.0, 40.0)["within_limits"]
        )

    def test_a_value_exactly_on_a_band_edge_is_within_limits(self):
        result = environment_verdict(STORAGE_CONTROLLED, 25.0, 55.0)
        self.assertTrue(result["within_limits"])

    def test_a_hot_store_reports_a_temperature_excursion(self):
        result = environment_verdict(STORAGE_CONTROLLED, 32.0, 40.0)
        self.assertFalse(result["within_limits"])
        self.assertTrue(any("temperature" in e for e in result["excursions"]))

    def test_a_damp_store_reports_a_humidity_excursion(self):
        result = environment_verdict(STORAGE_CONTROLLED, 20.0, 80.0)
        self.assertTrue(any("humidity" in e for e in result["excursions"]))

    def test_an_uncontrolled_store_has_a_wider_band(self):
        self.assertTrue(
            environment_verdict(STORAGE_UNCONTROLLED, 32.0, 70.0)["within_limits"]
        )

    def test_an_impossible_humidity_is_rejected(self):
        with self.assertRaises(ValueError):
            environment_verdict(STORAGE_CONTROLLED, 20.0, 140.0)

    def test_a_non_numeric_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            environment_verdict(STORAGE_CONTROLLED, "cool", 40.0)


class HandlingTests(unittest.TestCase):
    def test_a_single_lot_bin_handled_properly_has_no_findings(self):
        self.assertEqual(
            handling_findings(
                {"lots_in_container": 1, "issue_order": "oldest-first"}
            ),
            [],
        )

    def test_a_mixed_bin_loses_lot_identity(self):
        findings = handling_findings({"lots_in_container": 4})
        self.assertTrue(any("lot identity" in f for f in findings))

    def test_bulk_tipping_is_called_out(self):
        findings = handling_findings({"bulk_tipped": True})
        self.assertTrue(any("flanks" in f for f in findings))

    def test_dissimilar_metals_in_one_container_are_called_out(self):
        findings = handling_findings({"dissimilar_metals_in_container": True})
        self.assertTrue(any("galvanic" in f for f in findings))

    def test_issuing_newest_first_is_called_out(self):
        findings = handling_findings({"issue_order": "newest-first"})
        self.assertTrue(any("oldest-first" in f for f in findings))

    def test_zero_lots_in_a_container_is_rejected(self):
        with self.assertRaises(ValueError):
            handling_findings({"lots_in_container": 0})


class AssessStorageTests(unittest.TestCase):
    def test_a_sound_lot_is_released(self):
        result = assess_storage(GOOD_CASE)
        self.assertEqual(result["disposition"], ISSUE_RELEASE)
        self.assertEqual(result["findings"], [])

    def test_an_expired_lot_is_quarantined(self):
        result = assess_storage(
            _case(protection="bare-passivated",
                  storage_class=STORAGE_UNCONTROLLED,
                  manufacture_date=DATE(2020, 1, 1))
        )
        self.assertEqual(result["disposition"], ISSUE_QUARANTINE)
        self.assertLess(result["remaining_life_days"], 0)

    def test_an_environmental_excursion_calls_for_re_preservation(self):
        result = assess_storage(_case(temperature_c=38.0))
        self.assertEqual(result["disposition"], ISSUE_REPRESERVE)

    def test_a_handling_finding_alone_calls_for_re_inspection(self):
        result = assess_storage(_case(lots_in_container=3))
        self.assertEqual(result["disposition"], ISSUE_REINSPECT)

    def test_a_breach_is_reported_and_moves_the_expiry(self):
        result = assess_storage(_case(package_breach_date=DATE(2025, 6, 1)))
        self.assertTrue(any("breached" in f for f in result["findings"]))
        self.assertEqual(result["expiry_date"], DATE(2030, 6, 1))

    def test_the_reinspection_interval_is_carried_into_the_result(self):
        self.assertEqual(
            assess_storage(GOOD_CASE)["reinspection_interval_months"],
            reinspection_interval_months("plated", STORAGE_CONTROLLED),
        )

    def test_a_case_without_a_lot_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_storage(_case(lot_id="   "))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_storage("bolts in a drawer somewhere")

    def test_a_case_missing_the_manufacture_date_is_rejected(self):
        case = _case()
        del case["manufacture_date"]
        with self.assertRaises(ValueError):
            assess_storage(case)


if __name__ == "__main__":
    unittest.main()

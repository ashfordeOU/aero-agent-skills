"""Contract test for the expiry-date-control leaf (stdlib unittest)."""

import unittest
from datetime import date

from q7022_expiry_date_control_logic import (
    add_months,
    assess_expiry_control,
    assess_item,
    disposition_for,
    effective_expiry,
    item_status,
    nominal_expiry,
    out_of_store_penalty_days,
    remaining_days,
    validate_item,
)


def item(iid="I-1", material="sealant-a", manufactured="2026-01-15",
         shelf_life_months=12, **kw):
    record = {
        "id": iid,
        "material": material,
        "manufactured": manufactured,
        "shelf_life_months": shelf_life_months,
    }
    record.update(kw)
    return record


class TestAddMonths(unittest.TestCase):
    def test_whole_year_lands_on_the_same_day(self):
        self.assertEqual(add_months(date(2026, 1, 15), 12), date(2027, 1, 15))

    def test_month_end_is_clamped_not_rolled(self):
        self.assertEqual(add_months(date(2026, 1, 31), 1), date(2026, 2, 28))

    def test_leap_february_is_clamped_to_the_29th(self):
        self.assertEqual(add_months(date(2028, 1, 31), 1), date(2028, 2, 29))

    def test_crossing_december_increments_the_year(self):
        self.assertEqual(add_months(date(2026, 11, 10), 2), date(2027, 1, 10))

    def test_zero_months_is_the_same_date(self):
        self.assertEqual(add_months(date(2026, 5, 4), 0), date(2026, 5, 4))

    def test_negative_months_raises(self):
        with self.assertRaises(ValueError):
            add_months(date(2026, 1, 1), -1)

    def test_boolean_months_raises(self):
        with self.assertRaises(ValueError):
            add_months(date(2026, 1, 1), True)

    def test_non_date_start_raises(self):
        with self.assertRaises(ValueError):
            add_months("2026-01-01", 1)


class TestValidateItem(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_item(item())
        self.assertEqual(norm["out_of_store_days"], 0)
        self.assertAlmostEqual(norm["out_of_store_factor"], 1.0, places=9)
        self.assertTrue(norm["storage_conformant"])
        self.assertIsNone(norm["extension_approval"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_item(["I-1"])

    def test_zero_shelf_life_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(shelf_life_months=0))

    def test_non_integer_shelf_life_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(shelf_life_months=12.5))

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(out_of_store_factor=0.5))

    def test_negative_out_of_store_days_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(out_of_store_days=-3))

    def test_malformed_manufacture_date_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(manufactured="15-01-2026"))

    def test_empty_material_raises(self):
        with self.assertRaises(ValueError):
            validate_item(item(material="  "))


class TestExpiryArithmetic(unittest.TestCase):
    def test_nominal_expiry_is_manufacture_plus_shelf_life(self):
        self.assertEqual(nominal_expiry(item()), date(2027, 1, 15))

    def test_no_time_outside_the_store_costs_nothing(self):
        self.assertEqual(out_of_store_penalty_days(item(out_of_store_days=20)), 0)

    def test_acceleration_factor_charges_only_the_excess(self):
        self.assertEqual(
            out_of_store_penalty_days(item(out_of_store_days=10, out_of_store_factor=3.0)), 20)

    def test_a_fractional_penalty_rounds_up_to_a_whole_day(self):
        self.assertEqual(
            out_of_store_penalty_days(item(out_of_store_days=3, out_of_store_factor=1.5)), 2)

    def test_penalty_pulls_the_effective_expiry_in(self):
        self.assertEqual(
            effective_expiry(item(out_of_store_days=10, out_of_store_factor=2.0)),
            date(2027, 1, 5))

    def test_an_approved_extension_moves_the_date_out(self):
        self.assertEqual(
            effective_expiry(item(extension_days=90, extension_approval="MRB-2026-114")),
            date(2027, 4, 15))

    def test_an_unapproved_extension_does_not_move_the_date(self):
        self.assertEqual(effective_expiry(item(extension_days=90)), date(2027, 1, 15))

    def test_remaining_days_counts_down_to_the_effective_date(self):
        self.assertEqual(remaining_days(item(), "2027-01-05"), 10)

    def test_remaining_days_goes_negative_past_expiry(self):
        self.assertEqual(remaining_days(item(), "2027-02-14"), -30)


class TestStatusAndDisposition(unittest.TestCase):
    def test_well_inside_the_shelf_life_is_in_date(self):
        self.assertEqual(item_status(item(), "2026-06-01"), "in-date")

    def test_inside_the_alert_window_is_expiring_soon(self):
        self.assertEqual(item_status(item(), "2026-12-20"), "expiring-soon")

    def test_the_expiry_day_itself_is_not_yet_expired(self):
        self.assertEqual(item_status(item(), "2027-01-15"), "expiring-soon")

    def test_the_day_after_expiry_is_expired(self):
        self.assertEqual(item_status(item(), "2027-01-16"), "expired")

    def test_a_storage_non_conformance_overrides_a_valid_date(self):
        self.assertEqual(item_status(item(storage_conformant=False), "2026-06-01"),
                         "storage-non-conformance")

    def test_alert_window_width_changes_the_verdict(self):
        self.assertEqual(item_status(item(), "2026-11-01", alert_window_days=120),
                         "expiring-soon")

    def test_negative_alert_window_raises(self):
        with self.assertRaises(ValueError):
            item_status(item(), "2026-06-01", alert_window_days=-1)

    def test_expired_material_is_quarantined(self):
        self.assertEqual(disposition_for("expired"), "quarantine")

    def test_non_conformant_storage_is_quarantined_pending_review(self):
        self.assertEqual(disposition_for("storage-non-conformance"),
                         "quarantine-pending-review")

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            disposition_for("probably-fine")


class TestAssess(unittest.TestCase):
    def test_item_report_carries_both_dates(self):
        report = assess_item(item(out_of_store_days=10, out_of_store_factor=2.0), "2026-06-01")
        self.assertEqual(report["nominal_expiry"], "2027-01-15")
        self.assertEqual(report["effective_expiry"], "2027-01-05")
        self.assertEqual(report["penalty_days"], 10)

    def test_unapproved_extension_is_a_finding(self):
        report = assess_item(item(extension_days=60), "2026-06-01")
        self.assertEqual(report["granted_extension_days"], 0)
        self.assertEqual(len(report["findings"]), 1)

    def test_holding_lists_the_quarantine_ids(self):
        report = assess_expiry_control(
            [item("I-1"), item("I-2", manufactured="2024-01-15"),
             item("I-3", storage_conformant=False)], "2026-06-01")
        self.assertEqual(sorted(report["quarantine_ids"]), ["I-2", "I-3"])
        self.assertFalse(report["all_issuable"])

    def test_clean_holding_is_all_issuable(self):
        report = assess_expiry_control([item("I-1"), item("I-4")], "2026-06-01")
        self.assertTrue(report["all_issuable"])
        self.assertEqual(report["status_counts"]["in-date"], 2)

    def test_expiring_soon_items_are_listed_separately(self):
        report = assess_expiry_control([item("I-1")], "2026-12-20")
        self.assertEqual(report["expiring_soon_ids"], ["I-1"])
        self.assertTrue(report["all_issuable"])

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_expiry_control([item("I-1"), item("I-1")], "2026-06-01")

    def test_empty_holding_raises(self):
        with self.assertRaises(ValueError):
            assess_expiry_control([], "2026-06-01")

    def test_malformed_review_date_raises(self):
        with self.assertRaises(ValueError):
            assess_expiry_control([item()], "01-06-2026")


if __name__ == "__main__":
    unittest.main()

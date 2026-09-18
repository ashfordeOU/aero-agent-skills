"""Contract tests for the clause 5.2.11.1 recalibration-currency logic."""

import datetime
import unittest

from e2007_measurement_device_calibration_interval_logic import (
    DEVICE_KINDS,
    MAX_INTERVAL_MONTHS,
    STATUS_CURRENT,
    STATUS_DAMAGE_INVALIDATED,
    STATUS_DUE_WITHIN_CAMPAIGN,
    STATUS_EXPIRED,
    add_months,
    assess_device,
    assess_inventory,
    damage_valid_until,
    effective_validity,
    interval_valid_until,
    normalize_device,
    parse_date,
    recalibration_schedule,
    validate_interval_months,
)

TODAY = datetime.date(2026, 9, 18)


def device(**overrides):
    record = {
        "id": "horn-a",
        "kind": "antenna",
        "last_calibration": "2025-06-01",
    }
    record.update(overrides)
    return record


class ParseDateTests(unittest.TestCase):
    def test_date_passes_through(self):
        self.assertEqual(parse_date(datetime.date(2025, 1, 2)), datetime.date(2025, 1, 2))

    def test_iso_string_is_accepted(self):
        self.assertEqual(parse_date("2025-01-02"), datetime.date(2025, 1, 2))

    def test_surrounding_space_is_tolerated(self):
        self.assertEqual(parse_date("  2025-01-02 "), datetime.date(2025, 1, 2))

    def test_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(datetime.datetime(2025, 1, 2, 9, 0))

    def test_blank_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("   ")

    def test_malformed_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("02-01-2025")

    def test_number_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20250102)


class AddMonthsTests(unittest.TestCase):
    def test_plain_anniversary(self):
        self.assertEqual(add_months(datetime.date(2024, 6, 1), 24), datetime.date(2026, 6, 1))

    def test_leap_day_clamps_to_month_end(self):
        self.assertEqual(add_months(datetime.date(2024, 2, 29), 24), datetime.date(2026, 2, 28))

    def test_month_end_clamps(self):
        self.assertEqual(add_months(datetime.date(2023, 1, 31), 1), datetime.date(2023, 2, 28))

    def test_zero_months_is_identity(self):
        self.assertEqual(add_months(datetime.date(2023, 1, 31), 0), datetime.date(2023, 1, 31))

    def test_non_integer_months_rejected(self):
        with self.assertRaises(ValueError):
            add_months(datetime.date(2023, 1, 31), 1.5)

    def test_non_date_rejected(self):
        with self.assertRaises(ValueError):
            add_months("2023-01-31", 1)


class IntervalTests(unittest.TestCase):
    def test_ceiling_is_two_years(self):
        self.assertEqual(MAX_INTERVAL_MONTHS, 24)

    def test_tighter_interval_accepted(self):
        self.assertEqual(validate_interval_months(12), 12)

    def test_looser_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval_months(36)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval_months(0)

    def test_boolean_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval_months(True)

    def test_valid_until_is_the_interval_anniversary(self):
        self.assertEqual(
            interval_valid_until("2025-06-01"), datetime.date(2027, 6, 1)
        )

    def test_tighter_interval_pulls_validity_in(self):
        self.assertEqual(
            interval_valid_until("2025-06-01", 12), datetime.date(2026, 6, 1)
        )


class DamageTests(unittest.TestCase):
    def test_no_damage_gives_no_constraint(self):
        self.assertIsNone(damage_valid_until("2025-06-01", None))

    def test_empty_history_gives_no_constraint(self):
        self.assertIsNone(damage_valid_until("2025-06-01", []))

    def test_damage_before_calibration_is_superseded(self):
        self.assertIsNone(damage_valid_until("2025-06-01", ["2025-01-04"]))

    def test_damage_stops_the_device_the_day_before(self):
        self.assertEqual(
            damage_valid_until("2025-06-01", ["2026-03-10"]), datetime.date(2026, 3, 9)
        )

    def test_earliest_relevant_damage_governs(self):
        self.assertEqual(
            damage_valid_until("2025-06-01", ["2026-05-02", "2026-03-10"]),
            datetime.date(2026, 3, 9),
        )

    def test_damage_on_the_calibration_date_counts(self):
        self.assertEqual(
            damage_valid_until("2025-06-01", ["2025-06-01"]), datetime.date(2025, 5, 31)
        )

    def test_damage_later_than_the_reference_date_rejected(self):
        with self.assertRaises(ValueError):
            damage_valid_until("2025-06-01", ["2027-01-01"], TODAY)

    def test_string_history_rejected(self):
        with self.assertRaises(ValueError):
            damage_valid_until("2025-06-01", "2026-03-10")


class EffectiveValidityTests(unittest.TestCase):
    def test_interval_drives_an_undamaged_device(self):
        valid_until, driver = effective_validity("2025-06-01")
        self.assertEqual(driver, "interval")
        self.assertEqual(valid_until, datetime.date(2027, 6, 1))

    def test_damage_drives_when_it_comes_first(self):
        valid_until, driver = effective_validity("2025-06-01", ["2026-03-10"])
        self.assertEqual(driver, "damage")
        self.assertEqual(valid_until, datetime.date(2026, 3, 9))

    def test_damage_after_the_anniversary_does_not_extend_validity(self):
        valid_until, driver = effective_validity("2025-06-01", ["2027-08-01"])
        self.assertEqual(driver, "interval")
        self.assertEqual(valid_until, datetime.date(2027, 6, 1))


class NormalizeDeviceTests(unittest.TestCase):
    def test_kind_is_case_insensitive(self):
        self.assertEqual(normalize_device(device(kind="Probe"))["kind"], "probe")

    def test_every_governed_kind_is_accepted(self):
        for kind in DEVICE_KINDS:
            self.assertEqual(normalize_device(device(kind=kind))["kind"], kind)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_device(device(kind="spectrum-analyser"))

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            normalize_device(device(serial="A17"))

    def test_missing_key_rejected(self):
        record = device()
        del record["last_calibration"]
        with self.assertRaises(ValueError):
            normalize_device(record)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_device(device(id="  "))

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_device(["horn-a"])


class AssessDeviceTests(unittest.TestCase):
    def test_recent_calibration_is_current(self):
        grading = assess_device(device(last_calibration="2025-06-01"), TODAY)
        self.assertEqual(grading["status"], STATUS_CURRENT)
        self.assertEqual(grading["days_remaining"], 256)

    def test_expired_device_is_caught(self):
        grading = assess_device(device(last_calibration="2024-01-15"), TODAY)
        self.assertEqual(grading["status"], STATUS_EXPIRED)
        self.assertLess(grading["days_remaining"], 0)

    def test_damaged_device_is_invalidated_even_inside_the_interval(self):
        grading = assess_device(
            device(last_calibration="2025-06-01", damage_events=["2026-03-10"]), TODAY
        )
        self.assertEqual(grading["status"], STATUS_DAMAGE_INVALIDATED)
        self.assertEqual(grading["driver"], "damage")

    def test_due_inside_the_window_is_flagged(self):
        grading = assess_device(
            device(last_calibration="2025-06-01"), TODAY, campaign_end="2027-07-01"
        )
        self.assertEqual(grading["status"], STATUS_DUE_WITHIN_CAMPAIGN)
        self.assertFalse(grading["covers_campaign"])

    def test_window_ending_exactly_on_the_due_date_is_covered(self):
        grading = assess_device(
            device(last_calibration="2025-06-01"), TODAY, campaign_end="2027-06-01"
        )
        self.assertEqual(grading["status"], STATUS_CURRENT)
        self.assertTrue(grading["covers_campaign"])

    def test_reference_date_on_the_due_date_is_still_current(self):
        grading = assess_device(
            device(last_calibration="2025-06-01"), datetime.date(2027, 6, 1)
        )
        self.assertEqual(grading["status"], STATUS_CURRENT)
        self.assertEqual(grading["days_remaining"], 0)

    def test_future_calibration_rejected(self):
        with self.assertRaises(ValueError):
            assess_device(device(last_calibration="2027-01-01"), TODAY)

    def test_window_ending_before_the_reference_date_rejected(self):
        with self.assertRaises(ValueError):
            assess_device(device(), TODAY, campaign_end="2026-01-01")


class InventoryTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "devices": [
                device(id="horn-a", last_calibration="2025-06-01"),
                device(id="rod-b", kind="probe", last_calibration="2025-11-20"),
                device(id="flux-c", kind="sensor", last_calibration="2026-02-02"),
            ],
            "reference_date": TODAY,
        }
        spec.update(overrides)
        return spec

    def test_clean_inventory_reports_no_findings(self):
        result = assess_inventory(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["conforming_fraction"], 1.0, places=9)

    def test_schedule_is_ordered_by_due_date(self):
        result = assess_inventory(self._spec())
        self.assertEqual(result["next_due"]["id"], "horn-a")
        dates = [g["valid_until"] for g in result["schedule"]]
        self.assertEqual(dates, sorted(dates))

    def test_expired_device_produces_one_finding(self):
        spec = self._spec()
        spec["devices"][1]["last_calibration"] = "2023-05-05"
        result = assess_inventory(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("rod-b", result["findings"][0])

    def test_damage_finding_names_the_device(self):
        spec = self._spec()
        spec["devices"][2]["damage_events"] = ["2026-04-01"]
        result = assess_inventory(spec)
        self.assertIn("flux-c", result["findings"][0])
        self.assertAlmostEqual(result["conforming_fraction"], 2.0 / 3.0, places=9)

    def test_window_shortfall_is_reported_for_each_device(self):
        result = assess_inventory(self._spec(campaign_end="2028-06-01"))
        self.assertEqual(len(result["findings"]), 3)

    def test_duplicate_identifier_rejected(self):
        spec = self._spec()
        spec["devices"][1]["id"] = "horn-a"
        with self.assertRaises(ValueError):
            assess_inventory(spec)

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_inventory(self._spec(devices=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_inventory(["devices"])

    def test_missing_reference_date_rejected(self):
        spec = self._spec()
        del spec["reference_date"]
        with self.assertRaises(ValueError):
            assess_inventory(spec)

    def test_schedule_helper_rejects_a_mapping(self):
        with self.assertRaises(ValueError):
            recalibration_schedule({"id": "horn-a"}, TODAY)


if __name__ == "__main__":
    unittest.main()

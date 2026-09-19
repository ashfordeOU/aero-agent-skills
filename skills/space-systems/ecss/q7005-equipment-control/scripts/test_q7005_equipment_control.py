"""Contract test for the IR contamination equipment-control leaf (unittest)."""

import datetime
import unittest

from q7005_equipment_control_logic import (
    BLOCKED,
    CLEARED,
    CLEARED_WITH_WATCH,
    KIND_CELL,
    KIND_SAMPLING,
    KIND_SPECTROMETER,
    add_calendar_months,
    audit_equipment_set,
    audit_item,
    blank_fraction,
    calibration_due,
    capability_ratio,
    days_remaining,
    deviation_fraction,
    parse_date,
    resolved_policy,
    validate_item,
)

RUN_DAY = "2026-06-15"


def spectrometer(name="ftir-1", **kw):
    item = {
        "name": name,
        "kind": KIND_SPECTROMETER,
        "last_calibration": "2026-01-10",
        "interval_months": 12,
        "wavenumber_tolerance_per_cm": 2.0,
        "wavenumber_uncertainty_per_cm": 0.25,
    }
    item.update(kw)
    return item


def cell(name="transmission-cell-1", **kw):
    item = {
        "name": name,
        "kind": KIND_CELL,
        "last_calibration": "2026-02-01",
        "interval_months": 12,
        "nominal_pathlength_um": 100.0,
        "measured_pathlength_um": 101.0,
        "blank_level_mg_m2": 0.05,
        "quantitation_limit_mg_m2": 0.40,
    }
    item.update(kw)
    return item


def wipes(name="precleaned-wipes-lot-8", **kw):
    item = {
        "name": name,
        "kind": KIND_SAMPLING,
        "precleaning_certificate": "CERT-4410",
        "lot_release_date": "2026-03-01",
        "shelf_life_months": 12,
        "blank_level_mg_m2": 0.10,
        "quantitation_limit_mg_m2": 0.40,
    }
    item.update(kw)
    return item


class TestParseDate(unittest.TestCase):
    def test_an_iso_string_parses(self):
        self.assertEqual(parse_date("2026-02-28"), datetime.date(2026, 2, 28))

    def test_a_date_object_passes_through(self):
        day = datetime.date(2026, 5, 1)
        self.assertEqual(parse_date(day), day)

    def test_a_malformed_string_raises(self):
        with self.assertRaises(ValueError):
            parse_date("15/06/2026")

    def test_an_impossible_calendar_day_raises(self):
        with self.assertRaises(ValueError):
            parse_date("2026-02-30")


class TestCalendarMonths(unittest.TestCase):
    def test_twelve_months_lands_on_the_same_day_next_year(self):
        self.assertEqual(
            add_calendar_months("2026-01-10", 12), datetime.date(2027, 1, 10)
        )

    def test_a_month_end_clamps_to_the_shorter_month(self):
        self.assertEqual(
            add_calendar_months("2026-01-31", 1), datetime.date(2026, 2, 28)
        )

    def test_a_leap_year_moves_the_end_of_february(self):
        self.assertEqual(
            add_calendar_months("2028-01-31", 1), datetime.date(2028, 2, 29)
        )

    def test_crossing_a_year_boundary_works(self):
        self.assertEqual(
            add_calendar_months("2026-11-30", 3), datetime.date(2027, 2, 28)
        )

    def test_a_zero_interval_raises(self):
        with self.assertRaises(ValueError):
            add_calendar_months("2026-01-10", 0)

    def test_a_fractional_interval_raises(self):
        with self.assertRaises(ValueError):
            add_calendar_months("2026-01-10", 12.5)

    def test_calibration_due_uses_whole_months(self):
        self.assertEqual(
            calibration_due("2026-02-28", 6),
            datetime.date(2026, 8, 28),
        )


class TestDaysRemaining(unittest.TestCase):
    def test_a_future_due_date_leaves_days(self):
        self.assertEqual(days_remaining("2026-06-20", RUN_DAY), 5)

    def test_a_past_due_date_is_negative(self):
        self.assertEqual(days_remaining("2026-06-10", RUN_DAY), -5)

    def test_the_due_day_itself_is_zero(self):
        self.assertEqual(days_remaining(RUN_DAY, RUN_DAY), 0)


class TestRatios(unittest.TestCase):
    def test_capability_is_tolerance_over_uncertainty(self):
        self.assertAlmostEqual(capability_ratio(2.0, 0.25), 8.0, places=9)

    def test_a_zero_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            capability_ratio(2.0, 0.0)

    def test_deviation_is_symmetric_about_nominal(self):
        self.assertAlmostEqual(deviation_fraction(95.0, 100.0), 0.05, places=9)
        self.assertAlmostEqual(deviation_fraction(105.0, 100.0), 0.05, places=9)

    def test_a_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            deviation_fraction(95.0, 0.0)

    def test_blank_fraction_is_blank_over_the_quantitation_limit(self):
        self.assertAlmostEqual(blank_fraction(0.2, 0.4), 0.5, places=9)

    def test_a_zero_quantitation_limit_raises(self):
        with self.assertRaises(ValueError):
            blank_fraction(0.2, 0.0)


class TestPolicy(unittest.TestCase):
    def test_defaults_are_returned_when_nothing_is_passed(self):
        rules = resolved_policy()
        self.assertAlmostEqual(rules["minimum_capability_ratio"], 4.0, places=9)

    def test_a_caller_value_overrides_one_default(self):
        rules = resolved_policy({"minimum_capability_ratio": 10.0})
        self.assertAlmostEqual(rules["minimum_capability_ratio"], 10.0, places=9)
        self.assertAlmostEqual(rules["maximum_blank_fraction"], 0.5, places=9)

    def test_an_unknown_policy_key_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"minimum_capability_ration": 4.0})

    def test_a_negative_watch_window_raises(self):
        with self.assertRaises(ValueError):
            resolved_policy({"watch_window_days": -1})


class TestValidateItem(unittest.TestCase):
    def test_a_valid_spectrometer_normalizes(self):
        norm = validate_item(spectrometer())
        self.assertEqual(norm["name"], "ftir-1")

    def test_an_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_item(spectrometer(kind="microscope"))

    def test_a_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            validate_item(cell(measured_pathlength_um=None))

    def test_an_empty_name_raises(self):
        with self.assertRaises(ValueError):
            validate_item(spectrometer(name="  "))

    def test_a_blank_precleaning_certificate_raises(self):
        with self.assertRaises(ValueError):
            validate_item(wipes(precleaning_certificate="  "))

    def test_a_negative_blank_level_raises(self):
        with self.assertRaises(ValueError):
            validate_item(cell(blank_level_mg_m2=-0.01))


class TestAuditItem(unittest.TestCase):
    def test_a_current_capable_spectrometer_is_cleared(self):
        row = audit_item(spectrometer(), RUN_DAY)
        self.assertEqual(row["verdict"], CLEARED)
        self.assertEqual(row["findings"], [])

    def test_an_expired_calibration_blocks_the_instrument(self):
        row = audit_item(spectrometer(last_calibration="2025-01-10"), RUN_DAY)
        self.assertEqual(row["verdict"], BLOCKED)
        self.assertIn("calibration-expired-before-the-analysis-day",
                      row["findings"])

    def test_a_calibration_expiring_inside_the_window_is_watched(self):
        row = audit_item(spectrometer(last_calibration="2025-07-01"), RUN_DAY)
        self.assertEqual(row["verdict"], CLEARED_WITH_WATCH)
        self.assertEqual(row["findings"], [])

    def test_a_small_tolerance_against_a_large_uncertainty_blocks(self):
        row = audit_item(
            spectrometer(wavenumber_tolerance_per_cm=0.5,
                         wavenumber_uncertainty_per_cm=0.25),
            RUN_DAY,
        )
        self.assertEqual(row["verdict"], BLOCKED)
        self.assertIn("wavenumber-uncertainty-too-large-for-the-tolerance",
                      row["findings"])

    def test_a_ratio_exactly_on_the_floor_is_capable(self):
        row = audit_item(
            spectrometer(wavenumber_tolerance_per_cm=1.0,
                         wavenumber_uncertainty_per_cm=0.25),
            RUN_DAY,
        )
        self.assertAlmostEqual(row["checks"]["capability_ratio"], 4.0, places=9)
        self.assertEqual(row["verdict"], CLEARED)

    def test_a_drifted_cell_pathlength_blocks(self):
        row = audit_item(cell(measured_pathlength_um=120.0), RUN_DAY)
        self.assertEqual(row["verdict"], BLOCKED)
        self.assertIn("cell-pathlength-outside-its-tolerance", row["findings"])

    def test_a_pathlength_exactly_on_the_tolerance_is_accepted(self):
        row = audit_item(cell(measured_pathlength_um=105.0), RUN_DAY)
        self.assertAlmostEqual(
            row["checks"]["pathlength_deviation_fraction"], 0.05, places=9
        )
        self.assertEqual(row["verdict"], CLEARED)

    def test_a_cell_blank_beside_the_quantitation_limit_blocks(self):
        row = audit_item(cell(blank_level_mg_m2=0.35), RUN_DAY)
        self.assertEqual(row["verdict"], BLOCKED)
        self.assertIn("blank-too-large-beside-the-quantitation-limit",
                      row["findings"])

    def test_a_blank_exactly_on_the_permitted_fraction_is_accepted(self):
        row = audit_item(cell(blank_level_mg_m2=0.20), RUN_DAY)
        self.assertAlmostEqual(row["checks"]["blank_fraction"], 0.5, places=9)
        self.assertEqual(row["verdict"], CLEARED)

    def test_a_lot_past_its_shelf_life_blocks(self):
        row = audit_item(wipes(lot_release_date="2024-01-01"), RUN_DAY)
        self.assertEqual(row["verdict"], BLOCKED)
        self.assertIn("consumable-lot-past-its-shelf-life", row["findings"])

    def test_a_current_consumable_lot_is_cleared(self):
        row = audit_item(wipes(), RUN_DAY)
        self.assertEqual(row["verdict"], CLEARED)

    def test_a_tightened_policy_can_block_what_the_default_cleared(self):
        item = spectrometer()
        self.assertEqual(audit_item(item, RUN_DAY)["verdict"], CLEARED)
        self.assertEqual(
            audit_item(item, RUN_DAY, {"minimum_capability_ratio": 20.0})[
                "verdict"
            ],
            BLOCKED,
        )


class TestAuditEquipmentSet(unittest.TestCase):
    def test_a_clean_set_may_proceed(self):
        report = audit_equipment_set([spectrometer(), cell(), wipes()], RUN_DAY)
        self.assertTrue(report["run_may_proceed"])
        self.assertEqual(report["blocked"], [])

    def test_one_blocked_item_stops_the_run(self):
        report = audit_equipment_set(
            [spectrometer(), cell(measured_pathlength_um=130.0)], RUN_DAY
        )
        self.assertFalse(report["run_may_proceed"])
        self.assertEqual(report["blocked"], ["transmission-cell-1"])

    def test_the_kinds_present_are_reported(self):
        report = audit_equipment_set([spectrometer(), wipes()], RUN_DAY)
        self.assertEqual(
            report["kinds_present"], sorted([KIND_SPECTROMETER, KIND_SAMPLING])
        )

    def test_duplicate_equipment_name_raises(self):
        with self.assertRaises(ValueError):
            audit_equipment_set([spectrometer(), spectrometer()], RUN_DAY)

    def test_an_empty_set_raises(self):
        with self.assertRaises(ValueError):
            audit_equipment_set([], RUN_DAY)


if __name__ == "__main__":
    unittest.main()

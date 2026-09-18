"""Contract tests for the ECSS-Q-ST-70-31C paint material batch-control logic."""

import datetime
import unittest

from q7031_paint_material_control_logic import (
    CVCM_LIMIT_PCT,
    DISPOSITIONS,
    EXCURSION_PENALTY_DAYS_PER_KELVIN_HOUR,
    OUTGASSING_TOLERANCE_PCT,
    REQUIRED_TRACEABILITY,
    RETEST_WINDOW_DAYS,
    TML_LIMIT_PCT,
    add_months,
    assess_batch,
    excursion_penalty_days,
    expiry_date,
    missing_traceability,
    parse_date,
    screen_outgassing,
    shelf_life_remaining_days,
)


def record(**overrides):
    base = {
        "batch-number": "PB-4471",
        "manufacture-date": "2026-01-15",
        "certificate-of-conformity": "COC-PB-4471",
        "outgassing-data-reference": "OG-PB-4471",
        "storage-temperature-record": "STORE-LOG-12",
        "manufacture_date": "2026-01-15",
        "shelf_life_months": 12,
        "use_date": "2026-06-15",
        "tml_pct": 0.62,
        "cvcm_pct": 0.03,
        "rml_pct": 0.44,
        "storage_ceiling_c": 25.0,
    }
    base.update(overrides)
    return base


class DateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2026-03-04"), datetime.date(2026, 3, 4))

    def test_date_object_passes_through(self):
        d = datetime.date(2026, 3, 4)
        self.assertEqual(parse_date(d), d)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("15/01/2026")

    def test_impossible_calendar_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2026-02-30")

    def test_month_addition_clamps_into_the_month(self):
        self.assertEqual(add_months("2026-01-31", 1), datetime.date(2026, 2, 28))

    def test_month_addition_crosses_the_year(self):
        self.assertEqual(add_months("2026-11-10", 4), datetime.date(2027, 3, 10))

    def test_negative_months_rejected(self):
        with self.assertRaises(ValueError):
            add_months("2026-01-01", -1)

    def test_expiry_is_manufacture_plus_shelf_life(self):
        self.assertEqual(expiry_date("2026-01-15", 12), datetime.date(2027, 1, 15))


class StorageExcursionTests(unittest.TestCase):
    def test_no_excursions_costs_nothing(self):
        self.assertAlmostEqual(excursion_penalty_days(None, 25.0), 0.0)

    def test_storage_at_the_ceiling_costs_nothing(self):
        self.assertAlmostEqual(
            excursion_penalty_days([{"temperature_c": 25.0, "duration_h": 100.0}], 25.0), 0.0
        )

    def test_penalty_scales_with_kelvin_hours(self):
        got = excursion_penalty_days([{"temperature_c": 35.0, "duration_h": 20.0}], 25.0)
        self.assertAlmostEqual(got, 10.0 * 20.0 * EXCURSION_PENALTY_DAYS_PER_KELVIN_HOUR, places=9)

    def test_penalties_accumulate(self):
        entries = [
            {"temperature_c": 30.0, "duration_h": 10.0},
            {"temperature_c": 45.0, "duration_h": 4.0},
        ]
        expected = (5.0 * 10.0 + 20.0 * 4.0) * EXCURSION_PENALTY_DAYS_PER_KELVIN_HOUR
        self.assertAlmostEqual(excursion_penalty_days(entries, 25.0), expected, places=9)

    def test_cold_storage_is_not_a_penalty(self):
        self.assertAlmostEqual(
            excursion_penalty_days([{"temperature_c": 5.0, "duration_h": 500.0}], 25.0), 0.0
        )

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            excursion_penalty_days([{"temperature_c": 40.0, "duration_h": -1.0}], 25.0)

    def test_excursion_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            excursion_penalty_days([{"temperature_c": 40.0}], 25.0)


class ShelfLifeTests(unittest.TestCase):
    def test_days_remaining_before_expiry(self):
        got = shelf_life_remaining_days("2026-01-15", 12, "2026-12-15")
        self.assertAlmostEqual(got, 31.0)

    def test_zero_days_on_the_expiry_date(self):
        got = shelf_life_remaining_days("2026-01-15", 12, "2027-01-15")
        self.assertAlmostEqual(got, 0.0, places=9)

    def test_expired_batch_returns_negative_days(self):
        got = shelf_life_remaining_days("2026-01-15", 6, "2026-08-15")
        self.assertAlmostEqual(got, -31.0)

    def test_storage_penalty_shortens_the_remaining_life(self):
        entries = [{"temperature_c": 35.0, "duration_h": 100.0}]
        plain = shelf_life_remaining_days("2026-01-15", 12, "2026-12-15")
        hot = shelf_life_remaining_days("2026-01-15", 12, "2026-12-15", entries, 25.0)
        self.assertAlmostEqual(plain - hot, 20.0, places=9)

    def test_use_before_manufacture_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_remaining_days("2026-01-15", 12, "2025-12-01")


class OutgassingTests(unittest.TestCase):
    def test_clean_material_passes(self):
        self.assertTrue(screen_outgassing(0.4, 0.02, 0.3)["overall"])

    def test_exactly_at_the_limits_passes(self):
        got = screen_outgassing(TML_LIMIT_PCT, CVCM_LIMIT_PCT)
        self.assertTrue(got["overall"])

    def test_representation_error_at_the_limit_is_absorbed(self):
        got = screen_outgassing(TML_LIMIT_PCT + OUTGASSING_TOLERANCE_PCT / 2.0, 0.01)
        self.assertTrue(got["tml"])

    def test_condensable_failure_is_reported_alone(self):
        got = screen_outgassing(0.4, 0.25)
        self.assertTrue(got["tml"])
        self.assertFalse(got["cvcm"])
        self.assertFalse(got["overall"])

    def test_total_mass_loss_failure_reported(self):
        self.assertFalse(screen_outgassing(1.4, 0.02)["tml"])

    def test_recovered_above_total_rejected(self):
        with self.assertRaises(ValueError):
            screen_outgassing(0.4, 0.02, 0.9)

    def test_negative_figure_rejected(self):
        with self.assertRaises(ValueError):
            screen_outgassing(-0.1, 0.02)


class TraceabilityTests(unittest.TestCase):
    def test_complete_record_has_nothing_missing(self):
        self.assertEqual(missing_traceability(record()), [])

    def test_absent_item_reported(self):
        spec = record()
        del spec["certificate-of-conformity"]
        self.assertIn("certificate-of-conformity", missing_traceability(spec))

    def test_blank_item_counts_as_missing(self):
        self.assertIn(
            "batch-number", missing_traceability(record(**{"batch-number": "   "}))
        )

    def test_every_required_item_is_checked(self):
        empty = {item: None for item in REQUIRED_TRACEABILITY}
        self.assertEqual(sorted(missing_traceability(empty)), sorted(REQUIRED_TRACEABILITY))


class DispositionTests(unittest.TestCase):
    def test_in_date_traceable_clean_batch_is_released(self):
        out = assess_batch(record())
        self.assertEqual(out["disposition"], "release")
        self.assertEqual(out["findings"], [])

    def test_untraceable_batch_is_rejected(self):
        spec = record()
        del spec["outgassing-data-reference"]
        out = assess_batch(spec)
        self.assertEqual(out["disposition"], "reject")
        self.assertIn("traceability-missing-outgassing-data-reference", out["findings"])

    def test_outgassing_failure_is_rejected(self):
        out = assess_batch(record(cvcm_pct=0.30))
        self.assertEqual(out["disposition"], "reject")
        self.assertIn("outgassing-cvcm-over-limit", out["findings"])

    def test_recently_expired_batch_goes_to_retest(self):
        out = assess_batch(record(use_date="2027-02-01"))
        self.assertEqual(out["disposition"], "retest")
        self.assertIn("shelf-life-expired", out["findings"])

    def test_long_expired_batch_is_rejected(self):
        out = assess_batch(record(use_date="2027-08-01"))
        self.assertEqual(out["disposition"], "reject")

    def test_storage_excursion_alone_forces_retest(self):
        out = assess_batch(
            record(storage_excursions=[{"temperature_c": 40.0, "duration_h": 8.0}])
        )
        self.assertEqual(out["disposition"], "retest")
        self.assertIn("storage-excursion-penalty-applied", out["findings"])

    def test_retest_window_is_a_positive_number_of_days(self):
        self.assertGreater(RETEST_WINDOW_DAYS, 0)

    def test_missing_required_key_rejected(self):
        spec = record()
        del spec["shelf_life_months"]
        with self.assertRaises(ValueError):
            assess_batch(spec)

    def test_every_disposition_is_a_declared_one(self):
        for spec in (record(), record(cvcm_pct=0.5), record(use_date="2027-02-01")):
            self.assertIn(assess_batch(spec)["disposition"], DISPOSITIONS)


if __name__ == "__main__":
    unittest.main()

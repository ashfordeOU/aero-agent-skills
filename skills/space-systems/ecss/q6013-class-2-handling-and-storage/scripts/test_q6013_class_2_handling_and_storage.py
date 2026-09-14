"""Contract tests for the clause 5.4 class 2 handling-and-storage logic."""

import datetime
import math
import unittest

from q6013_class_2_handling_and_storage_logic import (
    BASELINE_MEASURES,
    BOUND_TOLERANCE,
    EDGE_MARGIN_FRACTION,
    ENHANCED_MEASURES,
    assess_class_two_handling_and_storage,
    environment_margin,
    esd_band,
    floor_life_consumed,
    handling_qualification_gaps,
    owed_protection_measures,
    protection_measure_gaps,
    shelf_life_state,
    storage_verdict,
)

ALL_MEASURES = list(BASELINE_MEASURES) + list(ENHANCED_MEASURES)


def _record(**over):
    base = {
        "lot_id": "LOT-2C-0418",
        "withstand_volts": 1500.0,
        "measures_operated": list(BASELINE_MEASURES),
        "temperature_c": 21.0,
        "temperature_limits": (15.0, 25.0),
        "humidity_percent": 45.0,
        "humidity_limits": (30.0, 60.0),
        "entry_date": "2025-01-06",
        "review_date": "2025-06-02",
        "shelf_life_days": 730,
        "reinspection_interval_days": 365,
        "handlers": [
            {"name": "store-operator-a", "qualification_expiry": "2026-01-01"},
        ],
    }
    base.update(over)
    return base


class SensitivityBandTests(unittest.TestCase):
    def test_most_sensitive_band(self):
        self.assertEqual(esd_band(120.0), "0")

    def test_band_edge_belongs_to_the_less_sensitive_band(self):
        self.assertEqual(esd_band(250.0), "1A")

    def test_mid_range_band(self):
        self.assertEqual(esd_band(1500.0), "1C")

    def test_robust_part_lands_in_the_top_band(self):
        self.assertEqual(esd_band(14000.0), "3B")

    def test_negative_withstand_rejected(self):
        with self.assertRaises(ValueError):
            esd_band(-5.0)

    def test_non_numeric_withstand_rejected(self):
        with self.assertRaises(ValueError):
            esd_band("1500")

    def test_boolean_withstand_rejected(self):
        with self.assertRaises(ValueError):
            esd_band(True)


class OwedMeasureTests(unittest.TestCase):
    def test_baseline_measures_apply_to_every_band(self):
        for band in ("0", "1C", "3B"):
            self.assertTrue(set(BASELINE_MEASURES) <= set(owed_protection_measures(band)))

    def test_sensitive_band_owes_the_enhanced_measures(self):
        self.assertTrue(set(ENHANCED_MEASURES) <= set(owed_protection_measures("1A")))

    def test_robust_band_does_not_owe_the_enhanced_measures(self):
        self.assertFalse(set(ENHANCED_MEASURES) & set(owed_protection_measures("2")))

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            owed_protection_measures("4")


class MeasureGapTests(unittest.TestCase):
    def test_a_complete_area_reports_no_gap(self):
        gaps = protection_measure_gaps("0", ALL_MEASURES)
        self.assertEqual(gaps["unmet"], [])
        self.assertEqual(gaps["substituted"], [])

    def test_missing_enhanced_measures_are_named(self):
        gaps = protection_measure_gaps("1A", BASELINE_MEASURES)
        self.assertEqual(sorted(gaps["unmet"]), sorted(ENHANCED_MEASURES))

    def test_measure_names_compare_case_insensitively(self):
        gaps = protection_measure_gaps("2", [m.upper() for m in BASELINE_MEASURES])
        self.assertEqual(gaps["unmet"], [])

    def test_a_recorded_substitution_is_credited(self):
        gaps = protection_measure_gaps(
            "1A",
            BASELINE_MEASURES,
            [{
                "measure": "protected-area-ionizer",
                "substitute": "humidity-held-dissipative-enclosure",
                "approval": "PA-WVR-118",
            }],
        )
        self.assertIn("protected-area-ionizer", gaps["substituted"])
        self.assertNotIn("protected-area-ionizer", gaps["unmet"])

    def test_a_substitution_without_approval_is_refused(self):
        gaps = protection_measure_gaps(
            "1A",
            BASELINE_MEASURES,
            [{
                "measure": "protected-area-ionizer",
                "substitute": "humidity-held-dissipative-enclosure",
            }],
        )
        self.assertIn("protected-area-ionizer", gaps["unmet"])
        self.assertIn("protected-area-ionizer", gaps["rejected_substitutions"])

    def test_a_substitution_naming_itself_is_refused(self):
        gaps = protection_measure_gaps(
            "1A",
            BASELINE_MEASURES,
            [{
                "measure": "protected-area-ionizer",
                "substitute": "Protected-Area-Ionizer",
                "approval": "PA-WVR-119",
            }],
        )
        self.assertIn("protected-area-ionizer", gaps["unmet"])

    def test_substitution_without_a_named_measure_rejected(self):
        with self.assertRaises(ValueError):
            protection_measure_gaps("1A", BASELINE_MEASURES, [{"substitute": "x", "approval": "y"}])

    def test_blank_measure_name_rejected(self):
        with self.assertRaises(ValueError):
            protection_measure_gaps("2", ["   "])


class EnvironmentTests(unittest.TestCase):
    def test_inside_the_band_reads_no_excursion(self):
        reading = environment_margin(21.0, (15.0, 25.0))
        self.assertAlmostEqual(reading["excursion"], 0.0, places=9)
        self.assertTrue(reading["inside"])

    def test_value_exactly_on_the_upper_limit_is_inside(self):
        reading = environment_margin(25.0, (15.0, 25.0))
        self.assertTrue(reading["inside"])
        self.assertAlmostEqual(reading["margin_fraction"], 0.0, places=9)

    def test_value_exactly_on_the_lower_limit_is_inside(self):
        reading = environment_margin(15.0, (15.0, 25.0))
        self.assertTrue(reading["inside"])
        self.assertAlmostEqual(reading["excursion"], 0.0, places=9)

    def test_band_centre_holds_the_full_margin(self):
        reading = environment_margin(20.0, (15.0, 25.0))
        self.assertAlmostEqual(reading["margin_fraction"], 1.0, places=9)

    def test_overshoot_is_positive_and_the_margin_goes_negative(self):
        reading = environment_margin(31.5, (15.0, 25.0))
        self.assertAlmostEqual(reading["excursion"], 6.5, places=9)
        self.assertAlmostEqual(reading["margin_fraction"], -1.3, places=9)

    def test_undershoot_is_negative(self):
        reading = environment_margin(9.0, (15.0, 25.0))
        self.assertAlmostEqual(reading["excursion"], -6.0, places=9)

    def test_degenerate_band_rejected(self):
        with self.assertRaises(ValueError):
            environment_margin(20.0, (20.0, 20.0))

    def test_backwards_limits_rejected(self):
        with self.assertRaises(ValueError):
            environment_margin(20.0, (25.0, 15.0))

    def test_limit_pair_shape_enforced(self):
        with self.assertRaises(ValueError):
            environment_margin(20.0, (15.0,))


class FloorLifeTests(unittest.TestCase):
    def test_unrestricted_level_consumes_nothing(self):
        self.assertAlmostEqual(floor_life_consumed("1", 4000.0), 0.0, places=9)

    def test_half_the_allowance(self):
        self.assertAlmostEqual(floor_life_consumed("3", 84.0), 0.5, places=9)

    def test_exactly_the_allowance_reads_one(self):
        self.assertAlmostEqual(floor_life_consumed("4", 72.0), 1.0, places=9)

    def test_dry_cabinet_hours_pause_the_clock(self):
        self.assertAlmostEqual(floor_life_consumed("3", 168.0, 84.0), 0.5, places=9)

    def test_bake_credit_returns_floor_life(self):
        self.assertAlmostEqual(floor_life_consumed("3", 168.0, 0.0, 126.0), 0.25, places=9)

    def test_level_without_floor_life_is_unbounded_once_exposed(self):
        self.assertTrue(math.isinf(floor_life_consumed("6", 1.0)))

    def test_level_without_floor_life_and_no_exposure_reads_zero(self):
        self.assertAlmostEqual(floor_life_consumed("6", 0.0), 0.0, places=9)

    def test_credits_beyond_the_exposure_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumed("3", 10.0, 6.0, 6.0)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumed("7", 10.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumed("3", -1.0)


class ShelfLifeTests(unittest.TestCase):
    def test_remaining_days_counted_from_entry(self):
        state = shelf_life_state("2025-01-01", "2025-01-31", 365, 365)
        self.assertEqual(state["remaining_days"], 335)
        self.assertFalse(state["expired"])

    def test_expiry_day_reads_zero_and_is_flagged(self):
        state = shelf_life_state("2025-01-01", "2025-01-11", 10, 365)
        self.assertEqual(state["remaining_days"], 0)
        self.assertTrue(state["expires_on_review"])

    def test_expired_lot_reads_negative(self):
        state = shelf_life_state("2025-01-01", "2025-01-21", 10, 365)
        self.assertEqual(state["remaining_days"], -10)
        self.assertTrue(state["expired"])

    def test_date_objects_accepted(self):
        state = shelf_life_state(
            datetime.date(2025, 1, 1), datetime.date(2025, 1, 11), 10, 365
        )
        self.assertEqual(state["remaining_days"], 0)

    def test_reinspection_falls_due_on_the_interval(self):
        state = shelf_life_state("2024-01-01", "2025-01-01", 3650, 366)
        self.assertTrue(state["reinspection_due"])

    def test_a_recorded_inspection_restarts_the_interval(self):
        state = shelf_life_state("2023-01-01", "2025-01-01", 3650, 365, "2024-12-01")
        self.assertFalse(state["reinspection_due"])

    def test_review_before_entry_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_state("2025-02-01", "2025-01-01", 365, 365)

    def test_inspection_before_entry_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_state("2024-01-01", "2025-01-01", 365, 365, "2023-01-01")

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_state("06/01/2025", "2025-01-11", 365, 365)

    def test_zero_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_state("2025-01-01", "2025-01-11", 0, 365)


class HandlerQualificationTests(unittest.TestCase):
    def test_current_qualification_is_no_gap(self):
        self.assertEqual(
            handling_qualification_gaps(
                [{"name": "op-a", "qualification_expiry": "2026-01-01"}], "2025-06-02"
            ),
            [],
        )

    def test_expiry_on_the_review_date_is_still_current(self):
        self.assertEqual(
            handling_qualification_gaps(
                [{"name": "op-a", "qualification_expiry": "2025-06-02"}], "2025-06-02"
            ),
            [],
        )

    def test_lapsed_qualification_is_named(self):
        self.assertEqual(
            handling_qualification_gaps(
                [{"name": "op-b", "qualification_expiry": "2025-06-01"}], "2025-06-02"
            ),
            ["op-b"],
        )

    def test_duplicate_handler_rejected(self):
        with self.assertRaises(ValueError):
            handling_qualification_gaps(
                [
                    {"name": "op-a", "qualification_expiry": "2026-01-01"},
                    {"name": "OP-A", "qualification_expiry": "2026-01-01"},
                ],
                "2025-06-02",
            )

    def test_blank_handler_name_rejected(self):
        with self.assertRaises(ValueError):
            handling_qualification_gaps(
                [{"name": " ", "qualification_expiry": "2026-01-01"}], "2025-06-02"
            )


class VerdictTests(unittest.TestCase):
    def test_no_findings_releases(self):
        self.assertEqual(storage_verdict([]), "released")

    def test_minor_finding_releases_with_actions(self):
        self.assertEqual(
            storage_verdict([{"severity": "minor", "topic": "t", "message": "m"}]),
            "released-with-actions",
        )

    def test_critical_finding_quarantines(self):
        self.assertEqual(
            storage_verdict([{"severity": "critical", "topic": "t", "message": "m"}]),
            "quarantined",
        )

    def test_finding_without_severity_rejected(self):
        with self.assertRaises(ValueError):
            storage_verdict([{"topic": "t"}])


class AssessmentTests(unittest.TestCase):
    def test_compliant_store_releases(self):
        result = assess_class_two_handling_and_storage(_record())
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sensitivity_band"], "1C")

    def test_sensitive_part_in_a_baseline_area_quarantines(self):
        result = assess_class_two_handling_and_storage(_record(withstand_volts=200.0))
        self.assertEqual(result["verdict"], "quarantined")
        self.assertEqual(sorted(result["unmet_measures"]), sorted(ENHANCED_MEASURES))

    def test_a_recorded_substitution_keeps_a_sensitive_lot_released(self):
        result = assess_class_two_handling_and_storage(
            _record(
                withstand_volts=200.0,
                substitutions=[
                    {
                        "measure": "protected-area-ionizer",
                        "substitute": "humidity-held-dissipative-enclosure",
                        "approval": "PA-WVR-118",
                    },
                    {
                        "measure": "periodic-wrist-strap-verification",
                        "substitute": "constant-monitor-footwear-system",
                        "approval": "PA-WVR-119",
                    },
                ],
            )
        )
        self.assertEqual(result["unmet_measures"], [])
        self.assertTrue(result["released"])

    def test_an_unrecorded_substitution_still_quarantines(self):
        result = assess_class_two_handling_and_storage(
            _record(
                withstand_volts=200.0,
                substitutions=[
                    {"measure": "protected-area-ionizer", "substitute": "unlogged-bench"},
                    {
                        "measure": "periodic-wrist-strap-verification",
                        "substitute": "constant-monitor-footwear-system",
                        "approval": "PA-WVR-119",
                    },
                ],
            )
        )
        self.assertEqual(result["verdict"], "quarantined")
        self.assertIn("protected-area-ionizer", result["rejected_substitutions"])

    def test_large_temperature_excursion_is_critical(self):
        result = assess_class_two_handling_and_storage(_record(temperature_c=40.0))
        self.assertEqual(result["verdict"], "quarantined")
        self.assertAlmostEqual(result["temperature"]["excursion"], 15.0, places=9)

    def test_small_humidity_excursion_is_actionable_not_fatal(self):
        result = assess_class_two_handling_and_storage(_record(humidity_percent=65.0))
        self.assertEqual(result["verdict"], "released-with-actions")
        self.assertAlmostEqual(result["humidity"]["excursion"], 5.0, places=9)

    def test_environment_exactly_on_the_limit_is_inside_but_edge_advised(self):
        result = assess_class_two_handling_and_storage(_record(temperature_c=25.0))
        self.assertTrue(result["temperature"]["inside"])
        self.assertAlmostEqual(result["temperature"]["margin_fraction"], 0.0, places=9)
        self.assertEqual(result["verdict"], "released-with-actions")

    def test_edge_threshold_is_the_documented_size(self):
        self.assertAlmostEqual(EDGE_MARGIN_FRACTION, 0.10, places=9)

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)

    def test_expired_shelf_life_quarantines(self):
        result = assess_class_two_handling_and_storage(
            _record(entry_date="2020-01-01", shelf_life_days=365)
        )
        self.assertEqual(result["verdict"], "quarantined")
        self.assertTrue(result["shelf_life"]["expired"])

    def test_floor_life_exceeded_quarantines(self):
        result = assess_class_two_handling_and_storage(
            _record(msl_level="3", hours_open=400.0)
        )
        self.assertEqual(result["verdict"], "quarantined")

    def test_floor_life_exactly_consumed_does_not_quarantine(self):
        result = assess_class_two_handling_and_storage(
            _record(msl_level="3", hours_open=168.0)
        )
        self.assertAlmostEqual(result["floor_life_consumed"], 1.0, places=9)
        self.assertNotEqual(result["verdict"], "quarantined")

    def test_lapsed_handler_on_a_sensitive_lot_is_critical(self):
        result = assess_class_two_handling_and_storage(
            _record(
                withstand_volts=200.0,
                measures_operated=ALL_MEASURES,
                handlers=[{"name": "op-b", "qualification_expiry": "2024-06-01"}],
            )
        )
        self.assertEqual(result["lapsed_handlers"], ["op-b"])
        self.assertEqual(result["verdict"], "quarantined")

    def test_lapsed_handler_on_a_robust_lot_is_actionable(self):
        result = assess_class_two_handling_and_storage(
            _record(handlers=[{"name": "op-b", "qualification_expiry": "2024-06-01"}])
        )
        self.assertEqual(result["verdict"], "released-with-actions")

    def test_findings_are_ranked_critical_first(self):
        result = assess_class_two_handling_and_storage(
            _record(withstand_volts=200.0, humidity_percent=65.0)
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_missing_record_key_rejected(self):
        record = _record()
        del record["humidity_limits"]
        with self.assertRaises(ValueError):
            assess_class_two_handling_and_storage(record)

    def test_blank_lot_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_two_handling_and_storage(_record(lot_id="  "))

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_two_handling_and_storage([_record()])


if __name__ == "__main__":
    unittest.main(verbosity=1)

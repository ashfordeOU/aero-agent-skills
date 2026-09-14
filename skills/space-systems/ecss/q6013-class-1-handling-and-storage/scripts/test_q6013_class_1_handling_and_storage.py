"""Contract tests for the clause 4.4 handling-and-storage logic."""

import datetime
import math
import unittest

from q6013_class_1_handling_and_storage_logic import (
    BASELINE_ESD_CONTROLS,
    BOUND_TOLERANCE,
    ENHANCED_ESD_CONTROLS,
    assess_handling_and_storage,
    environment_excursion,
    floor_life_consumed,
    hbm_sensitivity_band,
    missing_esd_controls,
    required_esd_controls,
    shelf_life_remaining_days,
    solderability_retest_due,
    storage_verdict,
)

ALL_CONTROLS = list(BASELINE_ESD_CONTROLS) + list(ENHANCED_ESD_CONTROLS)


def _record(**over):
    base = {
        "withstand_volts": 1500.0,
        "controls_present": list(BASELINE_ESD_CONTROLS),
        "temperature_c": 21.0,
        "temperature_limits": (15.0, 25.0),
        "humidity_percent": 40.0,
        "humidity_limits": (30.0, 60.0),
        "storage_start": "2025-01-06",
        "review_date": "2025-06-02",
        "shelf_life_days": 730,
        "retest_interval_days": 365,
    }
    base.update(over)
    return base


class SensitivityBandTests(unittest.TestCase):
    def test_most_sensitive_band(self):
        self.assertEqual(hbm_sensitivity_band(150.0), "0")

    def test_band_edge_belongs_to_the_higher_band(self):
        self.assertEqual(hbm_sensitivity_band(250.0), "1A")

    def test_mid_range_band(self):
        self.assertEqual(hbm_sensitivity_band(1500.0), "1C")

    def test_robust_part_lands_in_the_top_band(self):
        self.assertEqual(hbm_sensitivity_band(12000.0), "3B")

    def test_negative_withstand_rejected(self):
        with self.assertRaises(ValueError):
            hbm_sensitivity_band(-10.0)

    def test_non_numeric_withstand_rejected(self):
        with self.assertRaises(ValueError):
            hbm_sensitivity_band("1500")


class ControlSetTests(unittest.TestCase):
    def test_baseline_controls_apply_to_every_band(self):
        for band in ("0", "1C", "3B"):
            self.assertTrue(set(BASELINE_ESD_CONTROLS) <= set(required_esd_controls(band)))

    def test_sensitive_bands_owe_the_enhanced_controls(self):
        self.assertTrue(set(ENHANCED_ESD_CONTROLS) <= set(required_esd_controls("1A")))

    def test_robust_band_does_not_owe_the_enhanced_controls(self):
        self.assertFalse(set(ENHANCED_ESD_CONTROLS) & set(required_esd_controls("2")))

    def test_unknown_band_rejected(self):
        with self.assertRaises(ValueError):
            required_esd_controls("4")

    def test_missing_controls_are_named(self):
        missing = missing_esd_controls("1A", BASELINE_ESD_CONTROLS)
        self.assertEqual(sorted(missing), sorted(ENHANCED_ESD_CONTROLS))

    def test_a_complete_area_reports_nothing_missing(self):
        self.assertEqual(missing_esd_controls("0", ALL_CONTROLS), [])

    def test_control_names_compare_case_insensitively(self):
        upper = [c.upper() for c in BASELINE_ESD_CONTROLS]
        self.assertEqual(missing_esd_controls("2", upper), [])

    def test_blank_control_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_esd_controls("2", ["  "])


class EnvironmentTests(unittest.TestCase):
    def test_inside_the_band_reads_zero(self):
        self.assertAlmostEqual(environment_excursion(21.0, (15.0, 25.0)), 0.0, places=9)

    def test_value_exactly_on_the_upper_limit_is_inside(self):
        self.assertAlmostEqual(environment_excursion(25.0, (15.0, 25.0)), 0.0, places=9)

    def test_value_exactly_on_the_lower_limit_is_inside(self):
        self.assertAlmostEqual(environment_excursion(15.0, (15.0, 25.0)), 0.0, places=9)

    def test_overshoot_is_positive(self):
        self.assertAlmostEqual(environment_excursion(31.5, (15.0, 25.0)), 6.5, places=9)

    def test_undershoot_is_negative(self):
        self.assertAlmostEqual(environment_excursion(9.0, (15.0, 25.0)), -6.0, places=9)

    def test_backwards_limits_rejected(self):
        with self.assertRaises(ValueError):
            environment_excursion(20.0, (25.0, 15.0))

    def test_limit_pair_shape_enforced(self):
        with self.assertRaises(ValueError):
            environment_excursion(20.0, (15.0,))


class FloorLifeTests(unittest.TestCase):
    def test_unrestricted_level_consumes_nothing(self):
        self.assertAlmostEqual(floor_life_consumed("1", 5000.0), 0.0, places=9)

    def test_half_the_allowance(self):
        self.assertAlmostEqual(floor_life_consumed("3", 84.0), 0.5, places=9)

    def test_exactly_the_allowance_reads_one(self):
        self.assertAlmostEqual(floor_life_consumed("4", 72.0), 1.0, places=9)

    def test_bake_credit_returns_floor_life(self):
        self.assertAlmostEqual(floor_life_consumed("3", 168.0, 84.0), 0.5, places=9)

    def test_level_without_floor_life_is_unbounded_once_exposed(self):
        self.assertTrue(math.isinf(floor_life_consumed("6", 1.0)))

    def test_level_without_floor_life_and_no_exposure_reads_zero(self):
        self.assertAlmostEqual(floor_life_consumed("6", 0.0), 0.0, places=9)

    def test_bake_credit_beyond_the_exposure_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumed("3", 10.0, 20.0)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumed("7", 10.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumed("3", -1.0)


class ShelfLifeTests(unittest.TestCase):
    def test_remaining_days_counted_from_storage_entry(self):
        self.assertEqual(
            shelf_life_remaining_days("2025-01-01", "2025-01-31", 365), 335
        )

    def test_expiry_day_reads_zero(self):
        self.assertEqual(shelf_life_remaining_days("2025-01-01", "2025-01-11", 10), 0)

    def test_expired_lot_reads_negative(self):
        self.assertEqual(shelf_life_remaining_days("2025-01-01", "2025-01-21", 10), -10)

    def test_date_objects_accepted(self):
        self.assertEqual(
            shelf_life_remaining_days(
                datetime.date(2025, 1, 1), datetime.date(2025, 1, 11), 10
            ),
            0,
        )

    def test_review_before_entry_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_remaining_days("2025-02-01", "2025-01-01", 365)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_remaining_days("06/01/2025", "2025-01-11", 365)

    def test_zero_shelf_life_rejected(self):
        with self.assertRaises(ValueError):
            shelf_life_remaining_days("2025-01-01", "2025-01-11", 0)

    def test_retest_falls_due_on_the_interval(self):
        self.assertTrue(solderability_retest_due("2024-01-01", "2025-01-01", 365))

    def test_retest_not_yet_due(self):
        self.assertFalse(solderability_retest_due("2024-01-01", "2024-06-01", 365))

    def test_a_recorded_retest_restarts_the_interval(self):
        self.assertFalse(
            solderability_retest_due("2023-01-01", "2025-01-01", 365, "2024-12-01")
        )

    def test_retest_before_storage_entry_rejected(self):
        with self.assertRaises(ValueError):
            solderability_retest_due("2024-01-01", "2025-01-01", 365, "2023-01-01")


class VerdictTests(unittest.TestCase):
    def test_no_findings_releases(self):
        self.assertEqual(storage_verdict([]), "released")

    def test_major_finding_releases_with_actions(self):
        self.assertEqual(
            storage_verdict([{"severity": "major", "topic": "t", "message": "m"}]),
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
        result = assess_handling_and_storage(_record())
        self.assertTrue(result["released"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sensitivity_band"], "1C")

    def test_sensitive_part_in_a_baseline_area_quarantines(self):
        result = assess_handling_and_storage(_record(withstand_volts=200.0))
        self.assertEqual(result["verdict"], "quarantined")
        self.assertEqual(sorted(result["missing_controls"]), sorted(ENHANCED_ESD_CONTROLS))

    def test_large_temperature_excursion_is_critical(self):
        result = assess_handling_and_storage(_record(temperature_c=40.0))
        self.assertEqual(result["verdict"], "quarantined")
        self.assertAlmostEqual(result["temperature_excursion_c"], 15.0, places=9)

    def test_small_humidity_excursion_is_actionable_not_fatal(self):
        result = assess_handling_and_storage(_record(humidity_percent=65.0))
        self.assertEqual(result["verdict"], "released-with-actions")
        self.assertAlmostEqual(result["humidity_excursion_percent"], 5.0, places=9)

    def test_environment_exactly_on_the_limit_stays_released(self):
        result = assess_handling_and_storage(_record(temperature_c=25.0, humidity_percent=60.0))
        self.assertAlmostEqual(result["temperature_excursion_c"], 0.0, places=9)
        self.assertTrue(result["released"])

    def test_expired_shelf_life_quarantines(self):
        result = assess_handling_and_storage(
            _record(storage_start="2020-01-01", shelf_life_days=365)
        )
        self.assertEqual(result["verdict"], "quarantined")
        self.assertLess(result["shelf_life_remaining_days"], 0)

    def test_overdue_retest_is_reported(self):
        result = assess_handling_and_storage(
            _record(storage_start="2023-01-02", review_date="2025-06-02")
        )
        self.assertTrue(result["solderability_retest_due"])
        topics = [f["topic"] for f in result["findings"]]
        self.assertIn("shelf-life", topics)

    def test_floor_life_exceeded_quarantines(self):
        result = assess_handling_and_storage(
            _record(msl_level="3", hours_exposed=200.0)
        )
        self.assertEqual(result["verdict"], "quarantined")

    def test_floor_life_exactly_consumed_does_not_quarantine(self):
        result = assess_handling_and_storage(
            _record(msl_level="3", hours_exposed=168.0)
        )
        self.assertAlmostEqual(result["floor_life_consumed"], 1.0, places=9)
        self.assertNotEqual(result["verdict"], "quarantined")

    def test_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)

    def test_findings_are_ranked_critical_first(self):
        result = assess_handling_and_storage(
            _record(withstand_volts=200.0, humidity_percent=65.0)
        )
        self.assertEqual(result["findings"][0]["severity"], "critical")
        self.assertEqual(result["findings"][-1]["severity"], "major")

    def test_missing_record_key_rejected(self):
        record = _record()
        del record["humidity_limits"]
        with self.assertRaises(ValueError):
            assess_handling_and_storage(record)

    def test_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_handling_and_storage([_record()])


if __name__ == "__main__":
    unittest.main(verbosity=1)

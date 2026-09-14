#!/usr/bin/env python3
"""Contract test for the standard-cell thermal custody check (offline)."""

import copy
import unittest

from e2008_standard_cell_maintenance_logic import (
    DEFAULT_EXPOSURE_POLICY,
    EXPOSURE_MODES,
    EXPOSURE_NONE,
    EXPOSURE_RECALIBRATION,
    EXPOSURE_TOLERATED,
    EXPOSURE_WITHDRAWAL,
    READING_EXCURSION,
    READING_INDETERMINATE,
    READING_WITHIN_LIMIT,
    STANDARD_ROLES,
    VERDICT_RECALIBRATION,
    VERDICT_TOLERATED,
    VERDICT_WITHDRAWN,
    VERDICT_WITHIN_LIMIT,
    assess_standard_cell_maintenance,
    categorize_exposure,
    charged_temperature_c,
    excursion_degree_minutes,
    exposure_by_mode,
    margin_to_ceiling_c,
    normalize_reading,
    peak_temperature_c,
    reading_status,
    validate_exposure_policy,
)

COOL_LOG = [
    {"temperature_c": 22.0, "dwell_minutes": 120.0, "mode": "storage"},
    {"temperature_c": 38.5, "dwell_minutes": 45.0, "mode": "operation"},
    {"temperature_c": 44.0, "dwell_minutes": 10.0, "mode": "operation"},
]

HOT_LOG = [
    {"temperature_c": 22.0, "dwell_minutes": 120.0, "mode": "storage"},
    {"temperature_c": 52.0, "dwell_minutes": 15.0, "mode": "operation"},
]

COOL_CASE = {"role": "working-standard", "readings": COOL_LOG}
HOT_CASE = {"role": "working-standard", "readings": HOT_LOG}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_exposure_policy(DEFAULT_EXPOSURE_POLICY), DEFAULT_EXPOSURE_POLICY
        )

    def test_default_ceiling_is_fifty_degrees(self):
        self.assertAlmostEqual(DEFAULT_EXPOSURE_POLICY["ceiling_c"], 50.0, places=9)

    def test_policy_covers_every_role(self):
        for role in STANDARD_ROLES:
            self.assertIn(role, DEFAULT_EXPOSURE_POLICY["tolerated_degree_minutes"])
            self.assertIn(role, DEFAULT_EXPOSURE_POLICY["withdrawal_degree_minutes"])

    def test_primary_standard_carries_no_budget(self):
        budget = DEFAULT_EXPOSURE_POLICY["tolerated_degree_minutes"]["primary-standard"]
        self.assertAlmostEqual(budget, 0.0, places=9)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_policy("default")

    def test_withdrawal_below_tolerated_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXPOSURE_POLICY)
        broken["withdrawal_degree_minutes"]["working-standard"] = 1.0
        with self.assertRaises(ValueError):
            validate_exposure_policy(broken)

    def test_policy_missing_a_role_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXPOSURE_POLICY)
        del broken["tolerated_degree_minutes"]["primary-standard"]
        with self.assertRaises(ValueError):
            validate_exposure_policy(broken)


class ReadingTests(unittest.TestCase):
    def test_reading_defaults_to_operation_mode(self):
        entry = normalize_reading({"temperature_c": 20.0, "dwell_minutes": 5.0})
        self.assertEqual(entry["mode"], "operation")
        self.assertAlmostEqual(entry["sensor_uncertainty_c"], 0.0, places=9)

    def test_reading_rejects_an_unknown_mode(self):
        with self.assertRaises(ValueError):
            normalize_reading(
                {"temperature_c": 20.0, "dwell_minutes": 5.0, "mode": "transport"}
            )

    def test_reading_rejects_a_negative_dwell(self):
        with self.assertRaises(ValueError):
            normalize_reading({"temperature_c": 20.0, "dwell_minutes": -1.0})

    def test_reading_rejects_a_sub_absolute_zero_temperature(self):
        with self.assertRaises(ValueError):
            normalize_reading({"temperature_c": -400.0, "dwell_minutes": 1.0})

    def test_reading_rejects_a_boolean_temperature(self):
        with self.assertRaises(ValueError):
            normalize_reading({"temperature_c": True, "dwell_minutes": 1.0})

    def test_reading_exactly_on_the_ceiling_is_within_limit(self):
        status = reading_status({"temperature_c": 50.0, "dwell_minutes": 1.0})
        self.assertEqual(status, READING_WITHIN_LIMIT)

    def test_uncertainty_band_crossing_the_ceiling_is_indeterminate(self):
        status = reading_status(
            {
                "temperature_c": 49.5,
                "dwell_minutes": 1.0,
                "sensor_uncertainty_c": 1.0,
            }
        )
        self.assertEqual(status, READING_INDETERMINATE)

    def test_reading_above_the_ceiling_is_an_excursion(self):
        status = reading_status({"temperature_c": 50.4, "dwell_minutes": 1.0})
        self.assertEqual(status, READING_EXCURSION)

    def test_indeterminate_reading_is_charged_at_its_upper_bound(self):
        reading = {
            "temperature_c": 49.5,
            "dwell_minutes": 1.0,
            "sensor_uncertainty_c": 1.0,
        }
        self.assertAlmostEqual(charged_temperature_c(reading), 50.5, places=9)

    def test_indeterminate_reading_can_be_waived_by_policy(self):
        reading = {
            "temperature_c": 49.5,
            "dwell_minutes": 1.0,
            "sensor_uncertainty_c": 1.0,
        }
        charged = charged_temperature_c(reading, None, False)
        self.assertAlmostEqual(charged, 49.5, places=9)


class ExposureTests(unittest.TestCase):
    def test_cool_log_accrues_no_exposure(self):
        self.assertAlmostEqual(excursion_degree_minutes(COOL_LOG), 0.0, places=9)

    def test_hot_log_exposure_is_magnitude_times_dwell(self):
        self.assertAlmostEqual(excursion_degree_minutes(HOT_LOG), 30.0, places=9)

    def test_empty_log_is_rejected(self):
        with self.assertRaises(ValueError):
            excursion_degree_minutes([])

    def test_non_list_log_is_rejected(self):
        with self.assertRaises(ValueError):
            excursion_degree_minutes({"temperature_c": 20.0, "dwell_minutes": 1.0})

    def test_peak_and_margin_agree_with_the_ceiling(self):
        self.assertAlmostEqual(peak_temperature_c(COOL_LOG), 44.0, places=9)
        self.assertAlmostEqual(margin_to_ceiling_c(COOL_LOG), 6.0, places=9)

    def test_margin_goes_negative_once_the_ceiling_is_passed(self):
        self.assertAlmostEqual(margin_to_ceiling_c(HOT_LOG), -2.0, places=9)

    def test_exposure_splits_across_both_modes(self):
        log = [
            {"temperature_c": 55.0, "dwell_minutes": 2.0, "mode": "storage"},
            {"temperature_c": 51.0, "dwell_minutes": 10.0, "mode": "operation"},
        ]
        split = exposure_by_mode(log)
        self.assertEqual(sorted(split), sorted(EXPOSURE_MODES))
        self.assertAlmostEqual(split["storage"], 10.0, places=9)
        self.assertAlmostEqual(split["operation"], 10.0, places=9)


class GradeTests(unittest.TestCase):
    def test_zero_exposure_grades_as_none(self):
        self.assertEqual(
            categorize_exposure(0.0, "working-standard"), EXPOSURE_NONE
        )

    def test_exposure_on_the_budget_edge_is_tolerated(self):
        self.assertEqual(
            categorize_exposure(30.0, "working-standard"), EXPOSURE_TOLERATED
        )

    def test_exposure_past_the_budget_forces_recalibration(self):
        self.assertEqual(
            categorize_exposure(60.0, "working-standard"), EXPOSURE_RECALIBRATION
        )

    def test_gross_exposure_withdraws_the_standard(self):
        self.assertEqual(
            categorize_exposure(400.0, "working-standard"), EXPOSURE_WITHDRAWAL
        )

    def test_primary_standard_has_no_tolerated_band(self):
        self.assertEqual(
            categorize_exposure(0.5, "primary-standard"), EXPOSURE_RECALIBRATION
        )

    def test_grade_rejects_an_unknown_role(self):
        with self.assertRaises(ValueError):
            categorize_exposure(1.0, "spare-cell")

    def test_grade_rejects_a_negative_exposure(self):
        with self.assertRaises(ValueError):
            categorize_exposure(-1.0, "working-standard")


class AssessmentTests(unittest.TestCase):
    def test_cool_working_standard_stays_usable(self):
        result = assess_standard_cell_maintenance(COOL_CASE)
        self.assertEqual(result["verdict"], VERDICT_WITHIN_LIMIT)
        self.assertTrue(result["usable_for_calibration"])
        self.assertEqual(result["findings"], [])

    def test_bounded_excursion_is_tolerated_for_a_working_standard(self):
        result = assess_standard_cell_maintenance(HOT_CASE)
        self.assertEqual(result["verdict"], VERDICT_TOLERATED)
        self.assertTrue(result["usable_for_calibration"])
        self.assertTrue(any("ceiling" in f for f in result["findings"]))

    def test_a_slight_excursion_recalibrates_a_primary_standard(self):
        log = [{"temperature_c": 50.4, "dwell_minutes": 5.0, "mode": "operation"}]
        result = assess_standard_cell_maintenance(
            _case(HOT_CASE, role="primary-standard", readings=log)
        )
        self.assertAlmostEqual(result["excursion_degree_minutes"], 2.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_RECALIBRATION)
        self.assertFalse(result["usable_for_calibration"])
        self.assertTrue(any("no excursion budget" in f for f in result["findings"]))

    def test_the_same_log_grades_harder_for_a_primary_than_a_working_standard(self):
        working = assess_standard_cell_maintenance(HOT_CASE)
        primary = assess_standard_cell_maintenance(
            _case(HOT_CASE, role="primary-standard")
        )
        self.assertEqual(working["verdict"], VERDICT_TOLERATED)
        self.assertEqual(primary["verdict"], VERDICT_WITHDRAWN)

    def test_gross_exposure_withdraws_a_working_standard(self):
        log = [{"temperature_c": 80.0, "dwell_minutes": 30.0, "mode": "storage"}]
        result = assess_standard_cell_maintenance(
            _case(HOT_CASE, readings=log)
        )
        self.assertEqual(result["verdict"], VERDICT_WITHDRAWN)
        self.assertFalse(result["usable_for_calibration"])

    def test_storage_exposure_is_called_out_separately(self):
        log = [{"temperature_c": 53.0, "dwell_minutes": 5.0, "mode": "storage"}]
        result = assess_standard_cell_maintenance(_case(HOT_CASE, readings=log))
        self.assertTrue(any("in storage" in f for f in result["findings"]))
        self.assertAlmostEqual(result["exposure_by_mode"]["storage"], 15.0, places=9)

    def test_indeterminate_reading_is_reported_and_charged(self):
        log = [
            {
                "temperature_c": 49.8,
                "dwell_minutes": 100.0,
                "sensor_uncertainty_c": 0.5,
                "mode": "operation",
            }
        ]
        result = assess_standard_cell_maintenance(_case(HOT_CASE, readings=log))
        self.assertIn(READING_INDETERMINATE, result["reading_statuses"])
        self.assertAlmostEqual(result["excursion_degree_minutes"], 30.0, places=9)
        self.assertTrue(any("indeterminate" in f for f in result["findings"]))

    def test_case_rejects_an_unknown_role(self):
        with self.assertRaises(ValueError):
            assess_standard_cell_maintenance(_case(COOL_CASE, role="reference"))

    def test_case_rejects_a_missing_reading_log(self):
        case = _case(COOL_CASE)
        del case["readings"]
        with self.assertRaises(ValueError):
            assess_standard_cell_maintenance(case)

    def test_case_rejects_a_non_mapping(self):
        with self.assertRaises(ValueError):
            assess_standard_cell_maintenance("working-standard")

    def test_a_tighter_project_ceiling_is_honoured(self):
        result = assess_standard_cell_maintenance(_case(COOL_CASE, ceiling_c=40.0))
        self.assertAlmostEqual(result["ceiling_c"], 40.0, places=9)
        self.assertAlmostEqual(result["excursion_degree_minutes"], 40.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_RECALIBRATION)

    def test_a_hotter_log_never_grades_better_than_a_cooler_one(self):
        cool = assess_standard_cell_maintenance(COOL_CASE)
        hot = assess_standard_cell_maintenance(HOT_CASE)
        self.assertGreater(
            hot["excursion_degree_minutes"], cool["excursion_degree_minutes"] + 1.0
        )
        self.assertLess(hot["margin_to_ceiling_c"], cool["margin_to_ceiling_c"] - 1.0)


if __name__ == "__main__":
    unittest.main()

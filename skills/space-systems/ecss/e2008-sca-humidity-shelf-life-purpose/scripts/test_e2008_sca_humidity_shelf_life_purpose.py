#!/usr/bin/env python3
"""Contract test for the accelerated shelf-life exposure purpose (offline).

This is the gate 3 behaviour contract. Every workflow step of the leaf is
exercised: the acceleration policy validation, the damp-air acceleration
factor, the storage life a planned run is worth, the coating declaration,
the monitoring gap that decides whether the coating is watched at all, and
the verdict a design review reads.
"""

import copy
import unittest

from e2008_sca_humidity_shelf_life_purpose_logic import (
    ACCELERATION_OUT_OF_RANGE,
    COATING_MEASUREMENTS,
    COATING_NOT_MONITORED,
    DEFAULT_SHELF_LIFE_POLICY,
    EXPOSURE_NOT_PLANNED,
    EXPOSURE_NOT_REQUIRED,
    EXPOSURE_REPRESENTS_SHELF_LIFE,
    EXPOSURE_UNDER_SHELF_LIFE,
    acceleration_factor,
    assess_sca_humidity_shelf_life_purpose,
    coating_is_conductive,
    coating_monitoring_gap,
    equivalent_storage_months,
    validate_shelf_life_policy,
)

STORAGE = {"relative_humidity_pct": 40.0, "temperature_c": 20.0}

EXPOSURE = {
    "relative_humidity_pct": 85.0,
    "temperature_c": 45.0,
    "duration_h": 1000.0,
}

MONITORED = list(COATING_MEASUREMENTS) + ["assembly-output-power"]

BASE_CASE = {
    "coverglass_coating": "indium-tin-oxide",
    "required_shelf_life_months": 24.0,
    "storage_environment": dict(STORAGE),
    "planned_exposure": dict(EXPOSURE),
    "monitored_measurements": list(MONITORED),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_shelf_life_policy(DEFAULT_SHELF_LIFE_POLICY),
            DEFAULT_SHELF_LIFE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_shelf_life_policy("default")

    def test_coverage_factor_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHELF_LIFE_POLICY)
        broken["coverage_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_shelf_life_policy(broken)

    def test_acceleration_ceiling_of_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHELF_LIFE_POLICY)
        broken["maximum_acceleration_factor"] = 1.0
        with self.assertRaises(ValueError):
            validate_shelf_life_policy(broken)

    def test_missing_hours_per_month_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHELF_LIFE_POLICY)
        del broken["hours_per_month"]
        with self.assertRaises(ValueError):
            validate_shelf_life_policy(broken)

    def test_zero_doubling_interval_rejected(self):
        broken = copy.deepcopy(DEFAULT_SHELF_LIFE_POLICY)
        broken["temperature_doubling_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_shelf_life_policy(broken)


class AccelerationTests(unittest.TestCase):
    def test_storage_conditions_accelerate_nothing(self):
        exposure = dict(STORAGE, duration_h=100.0)
        self.assertAlmostEqual(
            acceleration_factor(exposure, STORAGE), 1.0, places=9
        )

    def test_one_doubling_interval_warmer_doubles_the_factor(self):
        exposure = {
            "relative_humidity_pct": 40.0,
            "temperature_c": 30.0,
            "duration_h": 100.0,
        }
        self.assertAlmostEqual(
            acceleration_factor(exposure, STORAGE), 2.0, places=9
        )

    def test_double_the_humidity_squares_into_the_factor(self):
        exposure = {
            "relative_humidity_pct": 80.0,
            "temperature_c": 20.0,
            "duration_h": 100.0,
        }
        self.assertAlmostEqual(
            acceleration_factor(exposure, STORAGE), 4.0, places=9
        )

    def test_a_drier_cooler_run_decelerates(self):
        exposure = {
            "relative_humidity_pct": 20.0,
            "temperature_c": 10.0,
            "duration_h": 100.0,
        }
        self.assertLess(acceleration_factor(exposure, STORAGE), 0.5)

    def test_zero_storage_humidity_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor(EXPOSURE, {"relative_humidity_pct": 0.0, "temperature_c": 20.0})

    def test_humidity_above_saturation_rejected(self):
        exposure = dict(EXPOSURE, relative_humidity_pct=140.0)
        with self.assertRaises(ValueError):
            acceleration_factor(exposure, STORAGE)

    def test_non_mapping_exposure_rejected(self):
        with self.assertRaises(ValueError):
            acceleration_factor("85 percent at 45 C", STORAGE)


class EquivalenceTests(unittest.TestCase):
    def test_one_month_of_hours_at_storage_conditions_is_one_month(self):
        exposure = dict(STORAGE, duration_h=730.0)
        result = equivalent_storage_months(exposure, STORAGE)
        self.assertAlmostEqual(result["equivalent_months"], 1.0, places=9)

    def test_the_factor_multiplies_the_elapsed_hours(self):
        exposure = {
            "relative_humidity_pct": 80.0,
            "temperature_c": 20.0,
            "duration_h": 730.0,
        }
        result = equivalent_storage_months(exposure, STORAGE)
        self.assertAlmostEqual(result["equivalent_months"], 4.0, places=9)

    def test_a_longer_run_is_worth_more_storage(self):
        short = equivalent_storage_months(
            dict(EXPOSURE, duration_h=100.0), STORAGE
        )
        long_run = equivalent_storage_months(
            dict(EXPOSURE, duration_h=1000.0), STORAGE
        )
        self.assertGreater(
            long_run["equivalent_months"], short["equivalent_months"]
        )

    def test_zero_duration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_storage_months(dict(EXPOSURE, duration_h=0.0), STORAGE)


class CoatingTests(unittest.TestCase):
    def test_a_transparent_conductive_oxide_is_conductive(self):
        self.assertTrue(coating_is_conductive("indium-tin-oxide"))

    def test_an_anti_reflective_only_coverglass_is_not(self):
        self.assertFalse(coating_is_conductive("anti-reflective-only"))

    def test_an_unknown_coating_is_rejected(self):
        with self.assertRaises(ValueError):
            coating_is_conductive("magnesium-fluoride-stack")


class MonitoringTests(unittest.TestCase):
    def test_a_full_monitoring_set_watches_the_coating(self):
        gap = coating_monitoring_gap(MONITORED)
        self.assertTrue(gap["watches_the_coating"])
        self.assertEqual(gap["missing_coating_measurements"], ())
        self.assertEqual(len(gap["objectives"]), len(COATING_MEASUREMENTS))

    def test_a_missing_coating_measurement_is_named(self):
        gap = coating_monitoring_gap(["coating-sheet-resistance"])
        self.assertFalse(gap["watches_the_coating"])
        self.assertIn(
            "coating-grounding-continuity", gap["missing_coating_measurements"]
        )

    def test_output_power_alone_does_not_watch_the_coating(self):
        gap = coating_monitoring_gap(["assembly-output-power"])
        self.assertFalse(gap["watches_the_coating"])
        self.assertEqual(gap["objectives"], ())

    def test_a_repeated_measurement_is_grouped_once(self):
        gap = coating_monitoring_gap(
            ["coating-sheet-resistance", "coating-sheet-resistance"]
        )
        self.assertEqual(gap["monitored"], ("coating-sheet-resistance",))

    def test_an_unknown_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            coating_monitoring_gap(["coverglass-colour"])

    def test_a_non_collection_monitoring_set_is_rejected(self):
        with self.assertRaises(ValueError):
            coating_monitoring_gap(7)


class VerdictTests(unittest.TestCase):
    def test_a_representative_watched_run_closes_the_purpose(self):
        result = assess_sca_humidity_shelf_life_purpose(BASE_CASE)
        self.assertEqual(result["verdict"], EXPOSURE_REPRESENTS_SHELF_LIFE)
        self.assertTrue(result["justified"])
        self.assertEqual(result["findings"], [])

    def test_a_short_run_falls_under_the_shelf_life(self):
        case = _case(
            BASE_CASE, planned_exposure=dict(EXPOSURE, duration_h=200.0)
        )
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_UNDER_SHELF_LIFE)
        self.assertFalse(result["represents_shelf_life"])

    def test_an_unwatched_coating_is_its_own_verdict(self):
        case = _case(BASE_CASE, monitored_measurements=["assembly-output-power"])
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertEqual(result["verdict"], COATING_NOT_MONITORED)

    def test_an_over_accelerated_run_is_refused_before_anything_else(self):
        case = _case(
            BASE_CASE,
            planned_exposure={
                "relative_humidity_pct": 95.0,
                "temperature_c": 85.0,
                "duration_h": 1000.0,
            },
        )
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertEqual(result["verdict"], ACCELERATION_OUT_OF_RANGE)
        self.assertFalse(result["acceleration_in_range"])

    def test_an_uncoated_coverglass_does_not_earn_the_exposure(self):
        case = _case(BASE_CASE, coverglass_coating="uncoated")
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_NOT_REQUIRED)
        self.assertFalse(result["justified"])

    def test_a_short_required_shelf_life_does_not_earn_it_either(self):
        case = _case(BASE_CASE, required_shelf_life_months=2.0)
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_NOT_REQUIRED)

    def test_a_justified_case_with_no_run_planned_is_distinct(self):
        case = _case(BASE_CASE)
        del case["planned_exposure"]
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_NOT_PLANNED)
        self.assertIsNone(result["equivalent_months"])

    def test_a_shelf_life_exactly_on_the_trigger_earns_the_exposure(self):
        case = _case(BASE_CASE, required_shelf_life_months=6.0)
        result = assess_sca_humidity_shelf_life_purpose(case)
        self.assertTrue(result["justified"])

    def test_the_equivalent_storage_life_is_reported(self):
        result = assess_sca_humidity_shelf_life_purpose(BASE_CASE)
        self.assertAlmostEqual(
            result["required_equivalent_months"], 24.0, places=9
        )
        self.assertGreater(result["equivalent_months"], 30.0)

    def test_a_missing_coating_declaration_stops_the_assessment(self):
        case = _case(BASE_CASE)
        del case["coverglass_coating"]
        with self.assertRaises(ValueError):
            assess_sca_humidity_shelf_life_purpose(case)

    def test_a_missing_storage_environment_stops_the_assessment(self):
        case = _case(BASE_CASE)
        del case["storage_environment"]
        with self.assertRaises(ValueError):
            assess_sca_humidity_shelf_life_purpose(case)

    def test_a_missing_required_shelf_life_stops_the_assessment(self):
        case = _case(BASE_CASE)
        del case["required_shelf_life_months"]
        with self.assertRaises(ValueError):
            assess_sca_humidity_shelf_life_purpose(case)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_humidity_shelf_life_purpose("coverglass in a chamber")


if __name__ == "__main__":
    unittest.main()

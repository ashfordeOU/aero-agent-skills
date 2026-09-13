#!/usr/bin/env python3
"""Contract test for the humidity-test purpose assessment (offline).

This is the gate 3 behaviour contract. Every workflow step of the leaf is
exercised: the per-segment moisture dose, the accumulated ground life,
the feature inventory that turns into objectives, the bounding check on
the planned exposure, and the verdict a design review reads.
"""

import copy
import unittest

from e2008_humidity_test_purpose_logic import (
    COMMON_OBJECTIVE,
    DEFAULT_HUMIDITY_POLICY,
    EXPOSURE_BOUNDS_GROUND_ENVIRONMENT,
    EXPOSURE_NOT_PLANNED,
    EXPOSURE_UNDER_BOUNDS,
    GROUND_PHASES,
    MOISTURE_SENSITIVE_FEATURES,
    TEST_NOT_REQUIRED,
    assess_humidity_test_purpose,
    exposure_bounds_ground_environment,
    ground_environment_dose,
    humidity_test_objectives,
    moisture_sensitive_inventory,
    segment_moisture_dose_h,
    validate_humidity_policy,
)

GROUND_PROFILE = [
    {
        "phase": "storage",
        "relative_humidity_pct": 60.0,
        "temperature_c": 25.0,
        "duration_h": 2000.0,
    },
    {
        "phase": "transport",
        "relative_humidity_pct": 85.0,
        "temperature_c": 35.0,
        "duration_h": 100.0,
    },
    {
        "phase": "launch-site",
        "relative_humidity_pct": 80.0,
        "temperature_c": 30.0,
        "duration_h": 300.0,
    },
]

FEATURES = ("adhesive-bondline", "silver-interconnect-metallization")

BOUNDING_TEST = {
    "relative_humidity_pct": 90.0,
    "temperature_c": 45.0,
    "duration_h": 500.0,
}

BASE_CASE = {
    "assembly_features": FEATURES,
    "ground_profile": GROUND_PROFILE,
    "test_conditions": dict(BOUNDING_TEST),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_humidity_policy(DEFAULT_HUMIDITY_POLICY), DEFAULT_HUMIDITY_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_humidity_policy("default")

    def test_reference_humidity_above_saturation_rejected(self):
        broken = copy.deepcopy(DEFAULT_HUMIDITY_POLICY)
        broken["reference_humidity_ratio"] = 1.4
        with self.assertRaises(ValueError):
            validate_humidity_policy(broken)

    def test_zero_doubling_interval_rejected(self):
        broken = copy.deepcopy(DEFAULT_HUMIDITY_POLICY)
        broken["temperature_doubling_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_humidity_policy(broken)

    def test_coverage_factor_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_HUMIDITY_POLICY)
        broken["coverage_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_humidity_policy(broken)

    def test_missing_dose_trigger_rejected(self):
        broken = copy.deepcopy(DEFAULT_HUMIDITY_POLICY)
        del broken["dose_trigger_h"]
        with self.assertRaises(ValueError):
            validate_humidity_policy(broken)


class SegmentDoseTests(unittest.TestCase):
    def test_reference_conditions_give_the_elapsed_hours(self):
        self.assertAlmostEqual(
            segment_moisture_dose_h(50.0, 25.0, 500.0), 500.0, places=9
        )

    def test_humidity_scales_the_load_linearly(self):
        self.assertAlmostEqual(
            segment_moisture_dose_h(60.0, 25.0, 2000.0), 2400.0, places=9
        )

    def test_ten_kelvin_warmer_doubles_the_load(self):
        cool = segment_moisture_dose_h(85.0, 25.0, 100.0)
        warm = segment_moisture_dose_h(85.0, 35.0, 100.0)
        self.assertAlmostEqual(warm, 2.0 * cool, places=9)

    def test_transport_segment_dose(self):
        self.assertAlmostEqual(
            segment_moisture_dose_h(85.0, 35.0, 100.0), 340.0, places=9
        )

    def test_launch_site_segment_dose(self):
        self.assertAlmostEqual(
            segment_moisture_dose_h(80.0, 30.0, 300.0), 678.8225099391, places=6
        )

    def test_dry_segment_carries_no_load(self):
        self.assertAlmostEqual(
            segment_moisture_dose_h(0.0, 35.0, 500.0), 0.0, places=12
        )

    def test_zero_duration_carries_no_load(self):
        self.assertAlmostEqual(segment_moisture_dose_h(90.0, 45.0, 0.0), 0.0, places=12)

    def test_humidity_above_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            segment_moisture_dose_h(120.0, 25.0, 100.0)

    def test_negative_humidity_rejected(self):
        with self.assertRaises(ValueError):
            segment_moisture_dose_h(-5.0, 25.0, 100.0)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            segment_moisture_dose_h(60.0, -300.0, 100.0)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            segment_moisture_dose_h(60.0, 25.0, -100.0)

    def test_non_numeric_humidity_rejected(self):
        with self.assertRaises(ValueError):
            segment_moisture_dose_h("damp", 25.0, 100.0)


class GroundEnvironmentTests(unittest.TestCase):
    def test_total_dose_is_the_sum_of_the_segments(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        self.assertAlmostEqual(ground["total_dose_h"], 3418.8225099391, places=6)

    def test_worst_conditions_are_taken_across_the_phases(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        self.assertAlmostEqual(ground["worst_relative_humidity_pct"], 85.0, places=9)
        self.assertAlmostEqual(ground["worst_temperature_c"], 35.0, places=9)

    def test_every_segment_is_reported(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        self.assertEqual(len(ground["segments"]), 3)

    def test_phases_covered_are_grouped_without_duplicates(self):
        profile = GROUND_PROFILE + [dict(GROUND_PROFILE[0])]
        ground = ground_environment_dose(profile)
        self.assertEqual(
            ground["phases_covered"], ("launch-site", "storage", "transport")
        )

    def test_a_longer_storage_phase_raises_the_load(self):
        longer = copy.deepcopy(GROUND_PROFILE)
        longer[0]["duration_h"] = 6000.0
        self.assertGreater(
            ground_environment_dose(longer)["total_dose_h"],
            ground_environment_dose(GROUND_PROFILE)["total_dose_h"],
        )

    def test_empty_profile_rejected(self):
        with self.assertRaises(ValueError):
            ground_environment_dose([])

    def test_non_list_profile_rejected(self):
        with self.assertRaises(ValueError):
            ground_environment_dose("stored for a year")

    def test_unknown_ground_phase_rejected(self):
        broken = copy.deepcopy(GROUND_PROFILE)
        broken[0]["phase"] = "on-orbit"
        with self.assertRaises(ValueError):
            ground_environment_dose(broken)

    def test_segment_missing_a_duration_rejected(self):
        broken = copy.deepcopy(GROUND_PROFILE)
        del broken[1]["duration_h"]
        with self.assertRaises(ValueError):
            ground_environment_dose(broken)

    def test_every_declared_phase_name_is_accepted(self):
        profile = [
            {
                "phase": phase,
                "relative_humidity_pct": 50.0,
                "temperature_c": 25.0,
                "duration_h": 10.0,
            }
            for phase in GROUND_PHASES
        ]
        ground = ground_environment_dose(profile)
        self.assertEqual(len(ground["phases_covered"]), len(GROUND_PHASES))


class FeatureInventoryTests(unittest.TestCase):
    def test_declared_features_are_grouped_and_sorted(self):
        self.assertEqual(
            moisture_sensitive_inventory(
                ("silver-interconnect-metallization", "adhesive-bondline")
            ),
            ("adhesive-bondline", "silver-interconnect-metallization"),
        )

    def test_a_repeated_feature_is_counted_once(self):
        self.assertEqual(
            moisture_sensitive_inventory(["adhesive-bondline", "adhesive-bondline"]),
            ("adhesive-bondline",),
        )

    def test_an_assembly_with_no_sensitive_feature_is_empty(self):
        self.assertEqual(moisture_sensitive_inventory([]), ())

    def test_unknown_feature_rejected(self):
        with self.assertRaises(ValueError):
            moisture_sensitive_inventory(["titanium-yoke"])

    def test_non_collection_feature_list_rejected(self):
        with self.assertRaises(ValueError):
            moisture_sensitive_inventory("adhesive-bondline")

    def test_each_feature_contributes_its_own_objective(self):
        objectives = humidity_test_objectives(FEATURES)
        self.assertIn("bondline-adhesion-retention", objectives)
        self.assertIn("interconnect-corrosion-resistance", objectives)

    def test_power_retention_is_always_an_objective_when_any_feature_is_present(self):
        self.assertEqual(humidity_test_objectives(["polyimide-substrate"])[-1],
                         COMMON_OBJECTIVE)

    def test_an_assembly_with_no_sensitive_feature_has_no_objective(self):
        self.assertEqual(humidity_test_objectives([]), ())

    def test_every_recognised_feature_maps_to_an_objective(self):
        objectives = humidity_test_objectives(MOISTURE_SENSITIVE_FEATURES)
        self.assertEqual(len(objectives), len(MOISTURE_SENSITIVE_FEATURES) + 1)


class BoundingTests(unittest.TestCase):
    def test_severe_exposure_bounds_the_ground_life(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        bounds = exposure_bounds_ground_environment(BOUNDING_TEST, ground)
        self.assertTrue(bounds["bounds_environment"])
        self.assertAlmostEqual(bounds["test_dose_h"], 3600.0, places=9)
        self.assertEqual(bounds["findings"], [])

    def test_short_exposure_falls_under_the_accumulated_load(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        bounds = exposure_bounds_ground_environment(
            dict(BOUNDING_TEST, duration_h=240.0), ground
        )
        self.assertFalse(bounds["dose_bounds"])
        self.assertTrue(bounds["humidity_bounds"])
        self.assertEqual(len(bounds["findings"]), 1)

    def test_mild_humidity_is_reported_even_when_the_load_is_met(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        bounds = exposure_bounds_ground_environment(
            {"relative_humidity_pct": 70.0, "temperature_c": 45.0, "duration_h": 1000.0},
            ground,
        )
        self.assertFalse(bounds["humidity_bounds"])
        self.assertTrue(bounds["dose_bounds"])

    def test_cool_exposure_is_reported(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        bounds = exposure_bounds_ground_environment(
            {"relative_humidity_pct": 95.0, "temperature_c": 30.0, "duration_h": 3000.0},
            ground,
        )
        self.assertFalse(bounds["temperature_bounds"])

    def test_coverage_factor_raises_the_load_the_exposure_owes(self):
        policy = copy.deepcopy(DEFAULT_HUMIDITY_POLICY)
        policy["coverage_factor"] = 2.0
        ground = ground_environment_dose(GROUND_PROFILE, policy)
        bounds = exposure_bounds_ground_environment(BOUNDING_TEST, ground, policy)
        self.assertFalse(bounds["dose_bounds"])

    def test_zero_test_duration_rejected(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        with self.assertRaises(ValueError):
            exposure_bounds_ground_environment(dict(BOUNDING_TEST, duration_h=0.0), ground)

    def test_non_mapping_test_conditions_rejected(self):
        ground = ground_environment_dose(GROUND_PROFILE)
        with self.assertRaises(ValueError):
            exposure_bounds_ground_environment("96 hours damp heat", ground)

    def test_ground_result_of_the_wrong_shape_rejected(self):
        with self.assertRaises(ValueError):
            exposure_bounds_ground_environment(BOUNDING_TEST, {"hours": 3400.0})


class PurposeAssessmentTests(unittest.TestCase):
    def test_bounding_exposure_serves_its_purpose(self):
        result = assess_humidity_test_purpose(BASE_CASE)
        self.assertEqual(result["verdict"], EXPOSURE_BOUNDS_GROUND_ENVIRONMENT)
        self.assertTrue(result["justified"])
        self.assertTrue(result["bounds_environment"])
        self.assertEqual(result["findings"], [])

    def test_assessment_names_what_the_exposure_demonstrates(self):
        result = assess_humidity_test_purpose(BASE_CASE)
        self.assertIn("bondline-adhesion-retention", result["objectives"])
        self.assertIn(COMMON_OBJECTIVE, result["objectives"])

    def test_short_exposure_is_under_bounds(self):
        case = _case(BASE_CASE, test_conditions=dict(BOUNDING_TEST, duration_h=240.0))
        result = assess_humidity_test_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_UNDER_BOUNDS)
        self.assertFalse(result["bounds_environment"])
        self.assertTrue(any("moisture load" in f for f in result["findings"]))

    def test_justified_exposure_with_no_plan_is_reported(self):
        case = _case(BASE_CASE)
        del case["test_conditions"]
        result = assess_humidity_test_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_NOT_PLANNED)
        self.assertIsNone(result["bounds_environment"])
        self.assertTrue(any("not yet served" in f for f in result["findings"]))

    def test_assembly_with_no_sensitive_feature_does_not_need_the_exposure(self):
        result = assess_humidity_test_purpose(_case(BASE_CASE, assembly_features=[]))
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)
        self.assertFalse(result["justified"])
        self.assertEqual(result["objectives"], ())

    def test_a_short_dry_ground_life_does_not_trigger_the_exposure(self):
        case = _case(
            BASE_CASE,
            ground_profile=[
                {
                    "phase": "integration",
                    "relative_humidity_pct": 40.0,
                    "temperature_c": 20.0,
                    "duration_h": 100.0,
                }
            ],
        )
        result = assess_humidity_test_purpose(case)
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)
        self.assertTrue(any("trigger" in f for f in result["findings"]))

    def test_ground_load_exactly_on_the_trigger_still_justifies_the_exposure(self):
        case = _case(
            BASE_CASE,
            ground_profile=[
                {
                    "phase": "storage",
                    "relative_humidity_pct": 50.0,
                    "temperature_c": 25.0,
                    "duration_h": DEFAULT_HUMIDITY_POLICY["dose_trigger_h"],
                }
            ],
        )
        result = assess_humidity_test_purpose(case)
        self.assertAlmostEqual(
            result["ground_dose_h"], DEFAULT_HUMIDITY_POLICY["dose_trigger_h"], places=9
        )
        self.assertTrue(result["justified"])

    def test_assessment_reports_the_worst_ground_conditions(self):
        result = assess_humidity_test_purpose(BASE_CASE)
        self.assertAlmostEqual(result["worst_relative_humidity_pct"], 85.0, places=9)
        self.assertAlmostEqual(result["worst_temperature_c"], 35.0, places=9)

    def test_a_longer_coastal_phase_can_push_a_passing_exposure_under_bounds(self):
        longer = copy.deepcopy(GROUND_PROFILE)
        longer[2]["duration_h"] = 3000.0
        result = assess_humidity_test_purpose(_case(BASE_CASE, ground_profile=longer))
        self.assertEqual(result["verdict"], EXPOSURE_UNDER_BOUNDS)

    def test_missing_feature_inventory_rejected(self):
        case = _case(BASE_CASE)
        del case["assembly_features"]
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(case)

    def test_missing_ground_profile_rejected(self):
        case = _case(BASE_CASE)
        del case["ground_profile"]
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(case)

    def test_unknown_feature_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose(
                _case(BASE_CASE, assembly_features=["kapton-tape"])
            )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_humidity_test_purpose("coupon in storage")


if __name__ == "__main__":
    unittest.main()

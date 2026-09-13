#!/usr/bin/env python3
"""Contract test for the solar cell assembly cycling purpose (offline).

This is the gate 3 behaviour contract. Every workflow step of the leaf is
exercised: the policy validation, the eclipse cycle count a year of the
declared orbit imposes, the orbital stress range, the feature inventory
that turns into reliability objectives, the representation check on the
planned run, and the verdict a design review reads.
"""

import copy
import unittest

from e2008_sca_thermal_cycling_purpose_logic import (
    COMMON_OBJECTIVE,
    CYCLING_NOT_PLANNED,
    CYCLING_REPRESENTS_ORBIT_YEAR,
    CYCLING_UNDER_REPRESENTATION,
    DEFAULT_CYCLING_PURPOSE_POLICY,
    TEST_NOT_REQUIRED,
    THERMAL_FATIGUE_FEATURES,
    assess_sca_thermal_cycling_purpose,
    cycling_represents_orbit_year,
    eclipse_cycles_per_year,
    orbital_thermal_stress,
    sca_cycling_objectives,
    thermal_fatigue_inventory,
    validate_cycling_purpose_policy,
)

FEATURES = ("cell-to-interconnect-weld", "coverglass-adhesive-bondline")

MISSION = {
    "orbital_period_min": 96.0,
    "eclipsed_orbit_fraction": 0.62,
    "hot_extreme_c": 70.0,
    "cold_extreme_c": -90.0,
}

REPRESENTATIVE_PLAN = {
    "cycle_count": 4000.0,
    "hot_extreme_c": 80.0,
    "cold_extreme_c": -95.0,
}

BASE_CASE = {
    "assembly_features": FEATURES,
    "mission_orbit": dict(MISSION),
    "test_plan": dict(REPRESENTATIVE_PLAN),
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cycling_purpose_policy(DEFAULT_CYCLING_PURPOSE_POLICY),
            DEFAULT_CYCLING_PURPOSE_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cycling_purpose_policy("default")

    def test_coverage_factor_below_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_PURPOSE_POLICY)
        broken["coverage_factor"] = 0.9
        with self.assertRaises(ValueError):
            validate_cycling_purpose_policy(broken)

    def test_missing_cycle_trigger_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_PURPOSE_POLICY)
        del broken["cycle_trigger"]
        with self.assertRaises(ValueError):
            validate_cycling_purpose_policy(broken)

    def test_zero_minimum_stress_range_rejected(self):
        broken = copy.deepcopy(DEFAULT_CYCLING_PURPOSE_POLICY)
        broken["minimum_stress_range_k"] = 0.0
        with self.assertRaises(ValueError):
            validate_cycling_purpose_policy(broken)


class EclipseCycleTests(unittest.TestCase):
    def test_a_fully_eclipsed_year_counts_every_orbit(self):
        self.assertAlmostEqual(
            eclipse_cycles_per_year(96.0, 1.0), 5475.0, places=9
        )

    def test_the_eclipsed_fraction_scales_the_count(self):
        full = eclipse_cycles_per_year(96.0, 1.0)
        part = eclipse_cycles_per_year(96.0, 0.5)
        self.assertAlmostEqual(part, full * 0.5, places=9)

    def test_a_full_sun_orbit_gives_no_eclipse_cycles(self):
        self.assertAlmostEqual(eclipse_cycles_per_year(96.0, 0.0), 0.0, places=9)

    def test_a_longer_orbit_gives_fewer_cycles(self):
        low = eclipse_cycles_per_year(96.0, 1.0)
        high = eclipse_cycles_per_year(720.0, 1.0)
        self.assertLess(high, low)

    def test_zero_orbital_period_rejected(self):
        with self.assertRaises(ValueError):
            eclipse_cycles_per_year(0.0, 0.5)

    def test_eclipsed_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            eclipse_cycles_per_year(96.0, 1.4)

    def test_non_numeric_period_rejected(self):
        with self.assertRaises(ValueError):
            eclipse_cycles_per_year("96", 0.5)


class StressRangeTests(unittest.TestCase):
    def test_range_is_the_hot_to_cold_swing(self):
        stress = orbital_thermal_stress(70.0, -90.0)
        self.assertAlmostEqual(stress["stress_range_k"], 160.0, places=9)

    def test_inverted_extremes_rejected(self):
        with self.assertRaises(ValueError):
            orbital_thermal_stress(-90.0, 70.0)

    def test_equal_extremes_rejected(self):
        with self.assertRaises(ValueError):
            orbital_thermal_stress(20.0, 20.0)

    def test_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            orbital_thermal_stress(70.0, -300.0)


class InventoryTests(unittest.TestCase):
    def test_declared_features_are_grouped_and_ordered(self):
        self.assertEqual(
            thermal_fatigue_inventory(
                ["coverglass-adhesive-bondline", "cell-to-interconnect-weld"]
            ),
            ("cell-to-interconnect-weld", "coverglass-adhesive-bondline"),
        )

    def test_a_repeated_feature_is_counted_once(self):
        self.assertEqual(
            thermal_fatigue_inventory(
                ["cell-to-interconnect-weld", "cell-to-interconnect-weld"]
            ),
            ("cell-to-interconnect-weld",),
        )

    def test_unknown_feature_rejected(self):
        with self.assertRaises(ValueError):
            thermal_fatigue_inventory(["kapton-tape"])

    def test_non_collection_features_rejected(self):
        with self.assertRaises(ValueError):
            thermal_fatigue_inventory(42)

    def test_every_recognised_feature_maps_to_an_objective(self):
        objectives = sca_cycling_objectives(THERMAL_FATIGUE_FEATURES)
        self.assertEqual(len(objectives), len(THERMAL_FATIGUE_FEATURES) + 1)
        self.assertIn(COMMON_OBJECTIVE, objectives)

    def test_an_empty_inventory_demonstrates_nothing(self):
        self.assertEqual(sca_cycling_objectives([]), ())


class RepresentationTests(unittest.TestCase):
    def setUp(self):
        self.orbit_year = {
            "annual_cycles": 3394.5,
            "hot_extreme_c": 70.0,
            "cold_extreme_c": -90.0,
        }

    def test_a_bounding_plan_represents_the_orbital_year(self):
        result = cycling_represents_orbit_year(
            REPRESENTATIVE_PLAN, self.orbit_year
        )
        self.assertTrue(result["represents_orbit_year"])
        self.assertEqual(result["findings"], [])

    def test_a_plan_exactly_on_the_required_count_represents_it(self):
        plan = dict(REPRESENTATIVE_PLAN, cycle_count=3394.5)
        result = cycling_represents_orbit_year(plan, self.orbit_year)
        self.assertTrue(result["count_represents"])
        self.assertAlmostEqual(result["required_cycles"], 3394.5, places=9)

    def test_too_few_cycles_is_a_finding(self):
        plan = dict(REPRESENTATIVE_PLAN, cycle_count=500.0)
        result = cycling_represents_orbit_year(plan, self.orbit_year)
        self.assertFalse(result["count_represents"])
        self.assertFalse(result["represents_orbit_year"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_plan_that_never_gets_cold_enough_is_a_finding(self):
        plan = dict(REPRESENTATIVE_PLAN, cold_extreme_c=-40.0)
        result = cycling_represents_orbit_year(plan, self.orbit_year)
        self.assertFalse(result["cold_represents"])
        self.assertFalse(result["represents_orbit_year"])

    def test_a_plan_that_never_gets_hot_enough_is_a_finding(self):
        plan = dict(REPRESENTATIVE_PLAN, hot_extreme_c=50.0)
        result = cycling_represents_orbit_year(plan, self.orbit_year)
        self.assertFalse(result["hot_represents"])

    def test_an_inverted_plan_is_rejected(self):
        plan = dict(REPRESENTATIVE_PLAN, hot_extreme_c=-100.0)
        with self.assertRaises(ValueError):
            cycling_represents_orbit_year(plan, self.orbit_year)

    def test_orbit_year_without_annual_cycles_rejected(self):
        with self.assertRaises(ValueError):
            cycling_represents_orbit_year(REPRESENTATIVE_PLAN, {"hot_extreme_c": 70.0})


class VerdictTests(unittest.TestCase):
    def test_a_representative_plan_closes_the_purpose(self):
        result = assess_sca_thermal_cycling_purpose(BASE_CASE)
        self.assertEqual(result["verdict"], CYCLING_REPRESENTS_ORBIT_YEAR)
        self.assertTrue(result["justified"])
        self.assertEqual(result["findings"], [])

    def test_a_short_plan_is_under_representation(self):
        case = _case(
            BASE_CASE, test_plan=dict(REPRESENTATIVE_PLAN, cycle_count=200.0)
        )
        result = assess_sca_thermal_cycling_purpose(case)
        self.assertEqual(result["verdict"], CYCLING_UNDER_REPRESENTATION)
        self.assertTrue(result["justified"])

    def test_a_justified_case_with_no_plan_is_distinct(self):
        case = _case(BASE_CASE)
        del case["test_plan"]
        result = assess_sca_thermal_cycling_purpose(case)
        self.assertEqual(result["verdict"], CYCLING_NOT_PLANNED)
        self.assertIsNone(result["represents_orbit_year"])

    def test_a_full_sun_orbit_does_not_earn_the_cycling(self):
        case = _case(
            BASE_CASE, mission_orbit=dict(MISSION, eclipsed_orbit_fraction=0.0)
        )
        result = assess_sca_thermal_cycling_purpose(case)
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)
        self.assertFalse(result["justified"])

    def test_a_quiet_swing_does_not_earn_the_cycling(self):
        case = _case(
            BASE_CASE,
            mission_orbit=dict(MISSION, hot_extreme_c=5.0, cold_extreme_c=-5.0),
        )
        result = assess_sca_thermal_cycling_purpose(case)
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)

    def test_an_assembly_with_no_sensitive_feature_is_not_required(self):
        case = _case(BASE_CASE, assembly_features=[])
        result = assess_sca_thermal_cycling_purpose(case)
        self.assertEqual(result["verdict"], TEST_NOT_REQUIRED)
        self.assertEqual(result["objectives"], ())

    def test_the_annual_cycle_count_is_reported(self):
        result = assess_sca_thermal_cycling_purpose(BASE_CASE)
        self.assertAlmostEqual(
            result["annual_eclipse_cycles"], 5475.0 * 0.62, places=9
        )

    def test_missing_feature_inventory_rejected(self):
        case = _case(BASE_CASE)
        del case["assembly_features"]
        with self.assertRaises(ValueError):
            assess_sca_thermal_cycling_purpose(case)

    def test_missing_mission_orbit_rejected(self):
        case = _case(BASE_CASE)
        del case["mission_orbit"]
        with self.assertRaises(ValueError):
            assess_sca_thermal_cycling_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_sca_thermal_cycling_purpose("coupon in a chamber")


if __name__ == "__main__":
    unittest.main()

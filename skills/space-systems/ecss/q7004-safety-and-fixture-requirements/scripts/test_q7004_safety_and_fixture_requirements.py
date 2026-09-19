#!/usr/bin/env python3
"""Contract test for the thermal-test safety and fixturing logic (offline)."""

import copy
import math
import unittest

from q7004_safety_and_fixture_requirements_logic import (
    DEFAULT_FIXTURE_POLICY,
    G0_M_PER_S2,
    HAZARD_CRYOGENIC,
    HAZARD_HOT_SURFACE,
    HAZARD_LIFTING,
    HAZARD_STORED_STRAIN,
    HAZARD_VACUUM,
    assess_safety_and_fixturing,
    differential_expansion_strain,
    expansion_strain_margin,
    fixture_load_margin,
    fixture_load_n,
    hazard_groups,
    interlock_clearance_k,
    interlock_setpoint_k,
    touch_safe_cooldown_s,
    validate_fixture_policy,
)

BASE_CASE = {
    "test_min_k": 213.15,
    "test_max_k": 333.15,
    "ambient_k": 293.15,
    "fixture_cte_per_k": 23.0e-6,
    "item_cte_per_k": 16.0e-6,
    "mounted_mass_kg": 18.0,
    "design_load_factor_g": 1.0,
    "fixture_capacity_n": 2000.0,
    "item_damage_limit_k": 360.0,
    "time_constant_s": 900.0,
    "vacuum": False,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_fixture_policy(DEFAULT_FIXTURE_POLICY), DEFAULT_FIXTURE_POLICY
        )

    def test_a_safety_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_FIXTURE_POLICY)
        broken["load_safety_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_fixture_policy(broken)

    def test_a_zero_allowable_strain_rejected(self):
        broken = copy.deepcopy(DEFAULT_FIXTURE_POLICY)
        broken["allowable_strain"] = 0.0
        with self.assertRaises(ValueError):
            validate_fixture_policy(broken)

    def test_inverted_touch_safe_band_rejected(self):
        broken = copy.deepcopy(DEFAULT_FIXTURE_POLICY)
        broken["touch_safe_cold_k"] = 350.0
        with self.assertRaises(ValueError):
            validate_fixture_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_fixture_policy("default")


class ExpansionTests(unittest.TestCase):
    def test_strain_is_the_mismatch_times_the_span(self):
        self.assertAlmostEqual(
            differential_expansion_strain(23.0e-6, 16.0e-6, 120.0),
            7.0e-6 * 120.0,
            places=12,
        )

    def test_matched_coefficients_drive_no_strain(self):
        self.assertAlmostEqual(
            differential_expansion_strain(16.0e-6, 16.0e-6, 200.0), 0.0, places=12
        )

    def test_the_sign_of_the_span_does_not_change_the_strain(self):
        warm = differential_expansion_strain(23.0e-6, 16.0e-6, 120.0)
        cool = differential_expansion_strain(23.0e-6, 16.0e-6, -120.0)
        self.assertAlmostEqual(warm, cool, places=12)

    def test_a_negative_expansion_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            differential_expansion_strain(-23.0e-6, 16.0e-6, 120.0)

    def test_a_non_numeric_span_rejected(self):
        with self.assertRaises(ValueError):
            differential_expansion_strain(23.0e-6, 16.0e-6, "one hundred")

    def test_a_zero_strain_joint_has_unbounded_margin(self):
        self.assertEqual(expansion_strain_margin(0.0), float("inf"))

    def test_a_strain_exactly_on_the_allowable_has_zero_margin(self):
        allowable = DEFAULT_FIXTURE_POLICY["allowable_strain"]
        self.assertAlmostEqual(expansion_strain_margin(allowable), 0.0, places=9)

    def test_a_strain_past_the_allowable_has_negative_margin(self):
        allowable = DEFAULT_FIXTURE_POLICY["allowable_strain"]
        self.assertLess(expansion_strain_margin(4.0 * allowable), 0.0)


class LoadTests(unittest.TestCase):
    def test_the_design_load_carries_the_policy_safety_factor(self):
        expected = (
            18.0 * G0_M_PER_S2 * 1.0 * DEFAULT_FIXTURE_POLICY["load_safety_factor"]
        )
        self.assertAlmostEqual(fixture_load_n(18.0, 1.0), expected, places=9)

    def test_doubling_the_load_factor_doubles_the_load(self):
        single = fixture_load_n(18.0, 1.0)
        double = fixture_load_n(18.0, 2.0)
        self.assertAlmostEqual(double / single, 2.0, places=9)

    def test_a_capacity_exactly_on_the_load_gives_zero_margin(self):
        applied = fixture_load_n(18.0, 1.0)
        self.assertAlmostEqual(
            fixture_load_margin(18.0, 1.0, applied), 0.0, places=9
        )

    def test_an_overloaded_fixture_has_negative_margin(self):
        self.assertLess(fixture_load_margin(180.0, 3.0, 2000.0), 0.0)

    def test_a_zero_mounted_mass_rejected(self):
        with self.assertRaises(ValueError):
            fixture_load_n(0.0, 1.0)

    def test_a_negative_capacity_rejected(self):
        with self.assertRaises(ValueError):
            fixture_load_margin(18.0, 1.0, -5.0)


class InterlockTests(unittest.TestCase):
    def test_the_setpoint_stacks_overshoot_and_guard_band_on_the_limit(self):
        expected = (
            333.15
            + DEFAULT_FIXTURE_POLICY["chamber_overshoot_k"]
            + DEFAULT_FIXTURE_POLICY["interlock_guard_band_k"]
        )
        self.assertAlmostEqual(interlock_setpoint_k(333.15), expected, places=9)

    def test_a_comfortable_damage_limit_clears_the_interlock(self):
        result = interlock_clearance_k(333.15, 360.0)
        self.assertTrue(result["acceptable"])
        self.assertAlmostEqual(
            result["clearance_k"], 360.0 - result["setpoint_k"], places=9
        )

    def test_a_clearance_exactly_on_the_minimum_is_accepted(self):
        setpoint = interlock_setpoint_k(333.15)
        damage = setpoint + DEFAULT_FIXTURE_POLICY["min_interlock_clearance_k"]
        self.assertTrue(interlock_clearance_k(333.15, damage)["acceptable"])

    def test_a_damage_limit_under_the_setpoint_is_not_acceptable(self):
        self.assertFalse(interlock_clearance_k(333.15, 334.0)["acceptable"])

    def test_a_non_numeric_damage_limit_rejected(self):
        with self.assertRaises(ValueError):
            interlock_clearance_k(333.15, "sixty degrees")


class CooldownTests(unittest.TestCase):
    def test_the_wait_follows_the_exponential_decay_of_the_offset(self):
        expected = 900.0 * math.log((333.15 - 293.15) / (318.15 - 293.15))
        self.assertAlmostEqual(
            touch_safe_cooldown_s(900.0, 333.15, 293.15, 318.15), expected, places=9
        )

    def test_one_time_constant_closes_the_offset_by_a_factor_of_e(self):
        ambient = 293.15
        safe = ambient + 1.0
        item = ambient + math.e
        self.assertAlmostEqual(
            touch_safe_cooldown_s(600.0, item, ambient, safe), 600.0, places=9
        )

    def test_an_item_already_touch_safe_needs_no_wait(self):
        self.assertAlmostEqual(
            touch_safe_cooldown_s(900.0, 300.0, 293.15, 318.15), 0.0, places=9
        )

    def test_an_item_exactly_at_the_touch_safe_point_needs_no_wait(self):
        self.assertAlmostEqual(
            touch_safe_cooldown_s(900.0, 318.15, 293.15, 318.15), 0.0, places=9
        )

    def test_the_cold_end_also_produces_a_wait(self):
        self.assertGreater(
            touch_safe_cooldown_s(900.0, 213.15, 293.15, 273.15), 0.0
        )

    def test_a_touch_safe_point_at_ambient_rejected(self):
        with self.assertRaises(ValueError):
            touch_safe_cooldown_s(900.0, 333.15, 293.15, 293.15)

    def test_a_zero_time_constant_rejected(self):
        with self.assertRaises(ValueError):
            touch_safe_cooldown_s(0.0, 333.15, 293.15, 318.15)


class HazardGroupTests(unittest.TestCase):
    def test_a_hot_run_is_grouped_as_a_hot_surface_hazard(self):
        self.assertIn(HAZARD_HOT_SURFACE, hazard_groups(BASE_CASE))

    def test_a_cryogenic_cold_end_adds_its_own_group(self):
        groups = hazard_groups(_case(BASE_CASE, test_min_k=90.0))
        self.assertIn(HAZARD_CRYOGENIC, groups)

    def test_a_vacuum_run_adds_the_vacuum_group(self):
        self.assertIn(HAZARD_VACUUM, hazard_groups(_case(BASE_CASE, vacuum=True)))

    def test_a_heavy_assembly_adds_the_lifting_group(self):
        self.assertIn(
            HAZARD_LIFTING, hazard_groups(_case(BASE_CASE, mounted_mass_kg=60.0))
        )

    def test_a_mismatched_fixture_adds_the_stored_strain_group(self):
        groups = hazard_groups(_case(BASE_CASE, fixture_cte_per_k=200.0e-6))
        self.assertIn(HAZARD_STORED_STRAIN, groups)

    def test_the_groups_are_deduplicated_and_ordered(self):
        groups = hazard_groups(_case(BASE_CASE, test_min_k=90.0, vacuum=True))
        self.assertEqual(list(groups), sorted(set(groups)))

    def test_inverted_test_limits_rejected(self):
        with self.assertRaises(ValueError):
            hazard_groups(_case(BASE_CASE, test_min_k=400.0))


class AssessmentTests(unittest.TestCase):
    def test_the_base_case_is_safe_to_run(self):
        result = assess_safety_and_fixturing(BASE_CASE)
        self.assertTrue(result["safe_to_run"])
        self.assertEqual(result["findings"], [])

    def test_the_span_is_the_difference_of_the_limits(self):
        result = assess_safety_and_fixturing(BASE_CASE)
        self.assertAlmostEqual(result["span_k"], 120.0, places=9)

    def test_a_stiff_mismatched_fixture_is_a_finding(self):
        result = assess_safety_and_fixturing(
            _case(BASE_CASE, fixture_cte_per_k=200.0e-6)
        )
        self.assertFalse(result["safe_to_run"])
        self.assertTrue(any("expansion mismatch" in f for f in result["findings"]))

    def test_an_overloaded_fixture_is_a_finding(self):
        result = assess_safety_and_fixturing(
            _case(BASE_CASE, mounted_mass_kg=400.0, design_load_factor_g=4.0)
        )
        self.assertTrue(any("load margin" in f for f in result["findings"]))

    def test_an_interlock_crowding_the_damage_limit_is_a_finding(self):
        result = assess_safety_and_fixturing(
            _case(BASE_CASE, item_damage_limit_k=336.0)
        )
        self.assertTrue(any("interlock" in f for f in result["findings"]))

    def test_a_vacuum_run_carries_the_venting_duty(self):
        result = assess_safety_and_fixturing(_case(BASE_CASE, vacuum=True))
        self.assertTrue(any("vent to ambient" in d for d in result["duties"]))

    def test_a_cryogenic_run_carries_the_cold_handling_duty(self):
        result = assess_safety_and_fixturing(_case(BASE_CASE, test_min_k=90.0))
        self.assertTrue(any("cryogenic-handling" in d for d in result["duties"]))

    def test_every_assessment_carries_the_access_gating_duty(self):
        result = assess_safety_and_fixturing(BASE_CASE)
        self.assertTrue(any("touch-safe temperature" in d for d in result["duties"]))

    def test_every_assessment_carries_the_preload_recheck_duty(self):
        result = assess_safety_and_fixturing(BASE_CASE)
        self.assertTrue(any("preload" in d for d in result["duties"]))

    def test_both_access_waits_are_reported(self):
        result = assess_safety_and_fixturing(BASE_CASE)
        self.assertGreater(result["hot_access_wait_s"], 0.0)
        self.assertGreater(result["cold_access_wait_s"], 0.0)

    def test_a_case_missing_the_time_constant_rejected(self):
        case = _case(BASE_CASE)
        del case["time_constant_s"]
        with self.assertRaises(ValueError):
            assess_safety_and_fixturing(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_safety_and_fixturing("bolt it down and hope")


if __name__ == "__main__":
    unittest.main()

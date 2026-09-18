#!/usr/bin/env python3
"""Contract test for thermal test specimen preparation (offline)."""

import copy
import math
import unittest

from q7004_specimen_preparation_logic import (
    ACCEPTANCE_VERIFICATION,
    ASSEMBLY,
    DEFAULT_PREPARATION_POLICY,
    ITEM_CATEGORIES,
    MATERIAL,
    MECHANICAL_PART,
    MIN_ONE_TERM_REMOVAL_FRACTION,
    OBJECTIVES,
    PROCESS,
    QUALIFICATION,
    SCREENING,
    bakeout_duration_s,
    conditioning_sequence,
    control_zone_id,
    normalize_zones,
    prepare_specimens,
    sensor_plan,
    specimen_allocation,
    validate_preparation_policy,
)

ZONES = [
    {"id": "baseplate", "mass_kg": 2.4},
    {"id": "cover", "mass_kg": 0.35},
    {"id": "harness-bracket", "mass_kg": 0.08},
]

VACUUM_CASE = {
    "item_category": MATERIAL,
    "objective": QUALIFICATION,
    "destructive_measurement": True,
    "spare_fraction": 0.4,
    "vacuum_run": True,
    "moisture_sensitive": True,
    "instrumented": True,
    "zones": ZONES,
    "half_thickness_m": 1.0e-3,
    "diffusivity_m2_s": 1.0e-12,
    "removal_fraction": 0.9,
}

DRY_CASE = {
    "item_category": ASSEMBLY,
    "objective": SCREENING,
    "destructive_measurement": False,
    "spare_fraction": 0.0,
    "vacuum_run": False,
    "moisture_sensitive": False,
    "instrumented": False,
    "zones": ZONES,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_preparation_policy(DEFAULT_PREPARATION_POLICY),
            DEFAULT_PREPARATION_POLICY,
        )

    def test_policy_covers_every_objective_and_category(self):
        for objective in OBJECTIVES:
            self.assertIn(objective, DEFAULT_PREPARATION_POLICY["cycled_specimens"])
        for category in ITEM_CATEGORIES:
            self.assertIn(category, DEFAULT_PREPARATION_POLICY["reference_specimens"])

    def test_policy_missing_an_objective_rejected(self):
        broken = copy.deepcopy(DEFAULT_PREPARATION_POLICY)
        del broken["cycled_specimens"][SCREENING]
        with self.assertRaises(ValueError):
            validate_preparation_policy(broken)

    def test_policy_with_a_negative_reference_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_PREPARATION_POLICY)
        broken["reference_specimens"][MATERIAL] = -1
        with self.assertRaises(ValueError):
            validate_preparation_policy(broken)

    def test_policy_with_an_absurd_spare_ceiling_rejected(self):
        broken = copy.deepcopy(DEFAULT_PREPARATION_POLICY)
        broken["max_spare_fraction"] = 9.0
        with self.assertRaises(ValueError):
            validate_preparation_policy(broken)


class AllocationTests(unittest.TestCase):
    def test_qualification_material_allocation(self):
        allocation = specimen_allocation(MATERIAL, QUALIFICATION)
        self.assertEqual(allocation["cycled"], 5)
        self.assertEqual(allocation["reference"], 1)
        self.assertEqual(allocation["spare"], 0)
        self.assertEqual(allocation["total"], 6)

    def test_spares_round_up_to_a_whole_specimen(self):
        allocation = specimen_allocation(MATERIAL, QUALIFICATION, spare_fraction=0.1)
        self.assertEqual(allocation["spare"], 1)

    def test_a_forty_percent_spare_fraction_on_five_gives_two(self):
        allocation = specimen_allocation(PROCESS, QUALIFICATION, spare_fraction=0.4)
        self.assertEqual(allocation["spare"], 2)

    def test_screening_allocates_fewer_cycled_specimens_than_qualification(self):
        screening = specimen_allocation(MECHANICAL_PART, SCREENING)["cycled"]
        qualification = specimen_allocation(MECHANICAL_PART, QUALIFICATION)["cycled"]
        self.assertGreater(qualification, screening)

    def test_a_destructive_measurement_keeps_references_separate(self):
        allocation = specimen_allocation(
            MATERIAL, QUALIFICATION, destructive_measurement=True
        )
        self.assertTrue(any("never drawn" in note for note in allocation["notes"]))

    def test_a_destructive_measurement_without_a_reference_is_flagged(self):
        allocation = specimen_allocation(
            ASSEMBLY, QUALIFICATION, destructive_measurement=True
        )
        self.assertTrue(any("no baseline" in note for note in allocation["notes"]))

    def test_a_spare_fraction_above_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            specimen_allocation(MATERIAL, QUALIFICATION, spare_fraction=1.5)

    def test_a_negative_spare_fraction_rejected(self):
        with self.assertRaises(ValueError):
            specimen_allocation(MATERIAL, QUALIFICATION, spare_fraction=-0.1)

    def test_an_unknown_objective_rejected(self):
        with self.assertRaises(ValueError):
            specimen_allocation(MATERIAL, "smoke-run")

    def test_a_non_boolean_destructive_flag_rejected(self):
        with self.assertRaises(ValueError):
            specimen_allocation(MATERIAL, QUALIFICATION, destructive_measurement="yes")

    def test_acceptance_allocation_is_the_smallest(self):
        counts = [specimen_allocation(MATERIAL, o)["cycled"] for o in OBJECTIVES]
        self.assertEqual(
            min(counts), specimen_allocation(MATERIAL, ACCEPTANCE_VERIFICATION)["cycled"]
        )


class ZoneTests(unittest.TestCase):
    def test_zones_come_back_sorted_by_identifier(self):
        ids = [zone["id"] for zone in normalize_zones(ZONES)]
        self.assertEqual(ids, sorted(ids))

    def test_a_duplicate_zone_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_zones(ZONES + [{"id": "cover", "mass_kg": 0.4}])

    def test_a_zone_without_a_mass_rejected(self):
        with self.assertRaises(ValueError):
            normalize_zones([{"id": "cover"}])

    def test_a_zero_mass_zone_rejected(self):
        with self.assertRaises(ValueError):
            normalize_zones([{"id": "cover", "mass_kg": 0.0}])

    def test_an_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_zones([])

    def test_the_heaviest_zone_controls_the_profile(self):
        self.assertEqual(control_zone_id(ZONES), "baseplate")

    def test_a_mass_tie_is_broken_on_the_identifier(self):
        tied = [
            {"id": "beta-panel", "mass_kg": 1.0},
            {"id": "alpha-panel", "mass_kg": 1.0},
        ]
        self.assertEqual(control_zone_id(tied), "alpha-panel")


class SensorPlanTests(unittest.TestCase):
    def test_an_instrumented_unit_gets_a_sensor_per_zone_plus_two(self):
        plan = sensor_plan(ZONES, instrumented=True)
        self.assertEqual(plan["sensor_count"], len(ZONES) + 2)

    def test_the_redundant_sensor_sits_on_the_controlling_zone(self):
        plan = sensor_plan(ZONES, instrumented=True)
        self.assertTrue(
            any("redundant sensor on the controlling zone baseplate" in p
                for p in plan["placement"])
        )

    def test_the_fixture_reference_sensor_is_always_placed(self):
        plan = sensor_plan(ZONES, instrumented=True)
        self.assertTrue(any("fixture" in p for p in plan["placement"]))

    def test_an_uninstrumented_set_falls_back_to_two_fixture_sensors(self):
        plan = sensor_plan(ZONES, instrumented=False)
        self.assertEqual(plan["sensor_count"], 2)
        self.assertFalse(plan["instrumented"])

    def test_a_non_boolean_instrumented_flag_rejected(self):
        with self.assertRaises(ValueError):
            sensor_plan(ZONES, instrumented="yes")


class BakeoutTests(unittest.TestCase):
    def test_duration_matches_the_one_term_slab_solution(self):
        expected = -(4.0 * (1.0e-3 ** 2) / (math.pi ** 2 * 1.0e-12)) * math.log(
            (math.pi ** 2 / 8.0) * 0.1
        )
        self.assertAlmostEqual(
            bakeout_duration_s(1.0e-3, 1.0e-12, 0.9) / expected, 1.0, places=9
        )

    def test_a_thicker_slab_takes_longer(self):
        thin = bakeout_duration_s(1.0e-3, 1.0e-12, 0.9)
        thick = bakeout_duration_s(2.0e-3, 1.0e-12, 0.9)
        self.assertAlmostEqual(thick / thin, 4.0, places=9)

    def test_a_faster_diffusivity_takes_less_time(self):
        slow = bakeout_duration_s(1.0e-3, 1.0e-12, 0.9)
        fast = bakeout_duration_s(1.0e-3, 1.0e-11, 0.9)
        self.assertAlmostEqual(slow / fast, 10.0, places=9)

    def test_a_higher_removal_fraction_takes_longer(self):
        self.assertGreater(
            bakeout_duration_s(1.0e-3, 1.0e-12, 0.99),
            bakeout_duration_s(1.0e-3, 1.0e-12, 0.9),
        )

    def test_complete_removal_rejected(self):
        with self.assertRaises(ValueError):
            bakeout_duration_s(1.0e-3, 1.0e-12, 1.0)

    def test_a_removal_fraction_below_the_model_floor_rejected(self):
        with self.assertRaises(ValueError):
            bakeout_duration_s(1.0e-3, 1.0e-12, MIN_ONE_TERM_REMOVAL_FRACTION - 0.2)

    def test_a_zero_diffusivity_rejected(self):
        with self.assertRaises(ValueError):
            bakeout_duration_s(1.0e-3, 0.0, 0.9)

    def test_a_negative_half_thickness_rejected(self):
        with self.assertRaises(ValueError):
            bakeout_duration_s(-1.0e-3, 1.0e-12, 0.9)

    def test_a_non_numeric_removal_fraction_rejected(self):
        with self.assertRaises(ValueError):
            bakeout_duration_s(1.0e-3, 1.0e-12, "ninety percent")


class ConditioningTests(unittest.TestCase):
    def test_the_baseline_is_recorded_before_cleaning(self):
        steps = conditioning_sequence(DRY_CASE)
        self.assertLess(
            next(i for i, s in enumerate(steps) if "baseline" in s),
            next(i for i, s in enumerate(steps) if s.startswith("clean to the declared")),
        )

    def test_a_vacuum_run_adds_a_bake_out_and_a_dry_hold(self):
        steps = conditioning_sequence(VACUUM_CASE)
        self.assertTrue(any("bake out" in s for s in steps))
        self.assertTrue(any("dry enclosure" in s for s in steps))

    def test_a_dry_ambient_run_skips_the_bake_out(self):
        steps = conditioning_sequence(DRY_CASE)
        self.assertFalse(any("bake out" in s for s in steps))

    def test_mounting_and_sensor_attachment_come_last(self):
        steps = conditioning_sequence(VACUUM_CASE)
        self.assertIn("mount on the fixture", steps[-1])

    def test_a_non_boolean_vacuum_flag_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_sequence(_case(DRY_CASE, vacuum_run="yes"))


class PrepareTests(unittest.TestCase):
    def test_the_vacuum_case_plan_carries_every_part(self):
        plan = prepare_specimens(VACUUM_CASE)
        self.assertEqual(plan["allocation"]["total"], 5 + 1 + 2)
        self.assertEqual(plan["sensor_plan"]["sensor_count"], 5)
        self.assertIsNotNone(plan["bakeout_duration_s"])

    def test_the_vacuum_case_owes_a_mass_end_point(self):
        plan = prepare_specimens(VACUUM_CASE)
        self.assertTrue(any("mass end point" in duty for duty in plan["duties"]))

    def test_every_plan_names_the_controlling_zone(self):
        plan = prepare_specimens(VACUUM_CASE)
        self.assertTrue(any("baseplate" in duty for duty in plan["duties"]))

    def test_the_dry_case_has_no_bake_out_duration(self):
        plan = prepare_specimens(DRY_CASE)
        self.assertIsNone(plan["bakeout_duration_s"])

    def test_an_uninstrumented_set_is_flagged(self):
        plan = prepare_specimens(DRY_CASE)
        self.assertTrue(any("not instrumented" in f for f in plan["findings"]))

    def test_a_vacuum_case_without_diffusion_data_rejected(self):
        case = _case(VACUUM_CASE)
        del case["diffusivity_m2_s"]
        with self.assertRaises(ValueError):
            prepare_specimens(case)

    def test_an_unknown_item_category_rejected(self):
        with self.assertRaises(ValueError):
            prepare_specimens(_case(VACUUM_CASE, item_category="subsystem"))

    def test_a_case_without_zones_rejected(self):
        case = _case(VACUUM_CASE)
        del case["zones"]
        with self.assertRaises(ValueError):
            prepare_specimens(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            prepare_specimens("a coupon set")


if __name__ == "__main__":
    unittest.main()

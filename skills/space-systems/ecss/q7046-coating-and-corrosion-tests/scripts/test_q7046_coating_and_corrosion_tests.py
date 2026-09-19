#!/usr/bin/env python3
"""Contract test for fastener coating and corrosion acceptance (offline)."""

import copy
import unittest

from q7046_coating_and_corrosion_tests_logic import (
    ADHESION_BEND,
    ADHESION_FLAKING,
    ADHESION_INTACT,
    ADHESION_TAPE,
    COATING_TYPES,
    CORROSION_BASE_METAL,
    CORROSION_NONE,
    CORROSION_SACRIFICIAL,
    ENVIRONMENTS,
    MIN_THICKNESS_READINGS,
    RELIEF_BAKE_DURATION_HOURS,
    RELIEF_BAKE_WINDOW_HOURS,
    SACRIFICIAL_TOLERATED_AFTER,
    VERDICT_ACCEPT,
    VERDICT_ADHESION,
    VERDICT_CORROSION,
    VERDICT_INVALID,
    VERDICT_RELIEF,
    VERDICT_THICKNESS,
    adhesion_verdict,
    assess_coating_programme,
    coating_spec,
    corrosion_verdict,
    durability_tests_owed,
    environment_factor,
    relief_bake_verdict,
    required_exposure_hours,
    thickness_verdict,
)

GOOD_CASE = {
    "coating_type": "zinc-nickel-plating",
    "environment": "integration-hall",
    "thickness_readings_um": [6.0, 7.5, 8.0, 9.0],
    "adhesion_method": ADHESION_BEND,
    "adhesion_result": ADHESION_INTACT,
    "exposure_hours_run": 500.0,
    "corrosion_observation": CORROSION_NONE,
    "relief_bake_done": True,
    "relief_bake_delay_hours": 1.0,
    "relief_bake_duration_hours": 24.0,
    "durability_tests_recorded": [
        "coating-thermal-cycling",
        "coating-humidity-exposure",
    ],
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class SpecTests(unittest.TestCase):
    def test_every_coating_has_a_band_with_a_floor_below_its_ceiling(self):
        for name in COATING_TYPES:
            spec = coating_spec(name)
            self.assertLess(spec["thickness_min_um"], spec["thickness_max_um"])

    def test_every_coating_names_an_adhesion_method(self):
        for name in COATING_TYPES:
            self.assertTrue(coating_spec(name)["adhesion_method"])

    def test_conversion_coating_is_thinner_than_a_plated_one(self):
        self.assertLess(
            coating_spec("chromate-conversion")["thickness_max_um"],
            coating_spec("zinc-nickel-plating")["thickness_max_um"],
        )

    def test_unlisted_coating_rejected(self):
        with self.assertRaises(ValueError):
            coating_spec("gold-leaf")


class EnvironmentTests(unittest.TestCase):
    def test_every_environment_has_a_positive_factor(self):
        for name in ENVIRONMENTS:
            self.assertGreater(environment_factor(name), 0.0)

    def test_coastal_site_demands_more_exposure_than_a_clean_room(self):
        self.assertGreater(
            required_exposure_hours("zinc-nickel-plating", "coastal-launch-site"),
            required_exposure_hours("zinc-nickel-plating", "clean-room-storage"),
        )

    def test_required_hours_are_the_base_times_the_factor(self):
        base = coating_spec("silver-plating")["base_exposure_hours"]
        self.assertAlmostEqual(
            required_exposure_hours("silver-plating", "coastal-launch-site"),
            base * environment_factor("coastal-launch-site"),
            places=9,
        )

    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            environment_factor("someones-garage")


class ThicknessTests(unittest.TestCase):
    def test_a_set_inside_the_band_passes(self):
        result = thickness_verdict([6.0, 7.0, 8.0], "zinc-nickel-plating")
        self.assertTrue(result["in_band"])
        self.assertEqual(result["findings"], [])

    def test_a_reading_on_the_floor_is_in_band(self):
        floor = coating_spec("zinc-nickel-plating")["thickness_min_um"]
        result = thickness_verdict([floor, floor + 1.0, floor + 2.0], "zinc-nickel-plating")
        self.assertTrue(result["in_band"])
        self.assertAlmostEqual(result["thinnest_um"], floor, places=9)

    def test_a_reading_on_the_ceiling_is_in_band(self):
        ceiling = coating_spec("zinc-nickel-plating")["thickness_max_um"]
        result = thickness_verdict(
            [ceiling - 2.0, ceiling - 1.0, ceiling], "zinc-nickel-plating"
        )
        self.assertTrue(result["in_band"])
        self.assertAlmostEqual(result["thickest_um"], ceiling, places=9)

    def test_one_thin_reading_fails_even_with_a_healthy_mean(self):
        result = thickness_verdict([2.0, 9.0, 10.0], "zinc-nickel-plating")
        self.assertFalse(result["in_band"])
        self.assertGreater(result["mean_um"], 5.0)

    def test_a_thick_reading_raises_the_thread_fit_risk(self):
        result = thickness_verdict([7.0, 8.0, 20.0], "zinc-nickel-plating")
        self.assertTrue(result["thread_fit_risk"])
        self.assertTrue(any("thread fit" in f for f in result["findings"]))

    def test_too_few_readings_rejected(self):
        with self.assertRaises(ValueError):
            thickness_verdict([7.0] * (MIN_THICKNESS_READINGS - 1), "zinc-nickel-plating")

    def test_a_zero_reading_rejected(self):
        with self.assertRaises(ValueError):
            thickness_verdict([7.0, 0.0, 8.0], "zinc-nickel-plating")

    def test_readings_given_as_a_string_rejected(self):
        with self.assertRaises(ValueError):
            thickness_verdict("7, 8, 9", "zinc-nickel-plating")


class AdhesionTests(unittest.TestCase):
    def test_the_right_method_with_no_detachment_passes(self):
        outcome = adhesion_verdict("zinc-nickel-plating", ADHESION_BEND, ADHESION_INTACT)
        self.assertTrue(outcome["valid"])
        self.assertTrue(outcome["passed"])

    def test_the_wrong_method_invalidates_rather_than_passes(self):
        outcome = adhesion_verdict("zinc-nickel-plating", ADHESION_TAPE, ADHESION_INTACT)
        self.assertFalse(outcome["valid"])
        self.assertFalse(outcome["passed"])

    def test_flaking_by_the_right_method_is_a_failure(self):
        outcome = adhesion_verdict("zinc-nickel-plating", ADHESION_BEND, ADHESION_FLAKING)
        self.assertTrue(outcome["valid"])
        self.assertFalse(outcome["passed"])

    def test_unknown_adhesion_result_rejected(self):
        with self.assertRaises(ValueError):
            adhesion_verdict("zinc-nickel-plating", ADHESION_BEND, "looked-fine")


class CorrosionTests(unittest.TestCase):
    def test_full_exposure_with_no_product_passes(self):
        outcome = corrosion_verdict(
            "zinc-nickel-plating", "integration-hall", 500.0, CORROSION_NONE
        )
        self.assertTrue(outcome["passed"])

    def test_exposure_landing_exactly_on_the_requirement_passes(self):
        required = required_exposure_hours("zinc-nickel-plating", "integration-hall")
        outcome = corrosion_verdict(
            "zinc-nickel-plating", "integration-hall", required, CORROSION_NONE
        )
        self.assertTrue(outcome["exposure_complete"])
        self.assertAlmostEqual(outcome["hours_run"], outcome["required_hours"], places=9)

    def test_short_exposure_fails(self):
        outcome = corrosion_verdict(
            "zinc-nickel-plating", "integration-hall", 200.0, CORROSION_NONE
        )
        self.assertFalse(outcome["passed"])

    def test_base_metal_attack_fails_whenever_it_appears(self):
        outcome = corrosion_verdict(
            "zinc-nickel-plating",
            "integration-hall",
            500.0,
            CORROSION_BASE_METAL,
            observed_at_hours=490.0,
        )
        self.assertFalse(outcome["passed"])

    def test_late_sacrificial_bloom_is_tolerated(self):
        required = required_exposure_hours("zinc-nickel-plating", "integration-hall")
        outcome = corrosion_verdict(
            "zinc-nickel-plating",
            "integration-hall",
            required,
            CORROSION_SACRIFICIAL,
            observed_at_hours=required * 0.9,
        )
        self.assertTrue(outcome["passed"])

    def test_bloom_landing_on_the_tolerance_point_is_tolerated(self):
        required = required_exposure_hours("zinc-nickel-plating", "integration-hall")
        outcome = corrosion_verdict(
            "zinc-nickel-plating",
            "integration-hall",
            required,
            CORROSION_SACRIFICIAL,
            observed_at_hours=required * SACRIFICIAL_TOLERATED_AFTER,
        )
        self.assertTrue(outcome["passed"])

    def test_early_sacrificial_bloom_fails(self):
        required = required_exposure_hours("zinc-nickel-plating", "integration-hall")
        outcome = corrosion_verdict(
            "zinc-nickel-plating",
            "integration-hall",
            required,
            CORROSION_SACRIFICIAL,
            observed_at_hours=required * 0.1,
        )
        self.assertFalse(outcome["passed"])

    def test_a_corrosion_product_without_its_hour_rejected(self):
        with self.assertRaises(ValueError):
            corrosion_verdict(
                "zinc-nickel-plating", "integration-hall", 500.0, CORROSION_SACRIFICIAL
            )

    def test_a_product_seen_after_the_test_ended_rejected(self):
        with self.assertRaises(ValueError):
            corrosion_verdict(
                "zinc-nickel-plating",
                "integration-hall",
                500.0,
                CORROSION_SACRIFICIAL,
                observed_at_hours=900.0,
            )


class ReliefBakeTests(unittest.TestCase):
    def test_a_coating_that_is_not_electrodeposited_owes_no_bake(self):
        outcome = relief_bake_verdict("chromate-conversion")
        self.assertFalse(outcome["required"])
        self.assertTrue(outcome["conforming"])

    def test_an_electrodeposited_coating_with_no_bake_is_non_conforming(self):
        outcome = relief_bake_verdict("zinc-nickel-plating", baked=False)
        self.assertTrue(outcome["required"])
        self.assertFalse(outcome["conforming"])

    def test_a_prompt_full_length_bake_conforms(self):
        outcome = relief_bake_verdict(
            "zinc-nickel-plating",
            baked=True,
            start_delay_hours=2.0,
            duration_hours=24.0,
        )
        self.assertTrue(outcome["conforming"])

    def test_a_bake_starting_on_the_window_edge_conforms(self):
        outcome = relief_bake_verdict(
            "zinc-nickel-plating",
            baked=True,
            start_delay_hours=RELIEF_BAKE_WINDOW_HOURS,
            duration_hours=RELIEF_BAKE_DURATION_HOURS,
        )
        self.assertTrue(outcome["conforming"])

    def test_a_late_bake_is_not_recovered_by_running_longer(self):
        outcome = relief_bake_verdict(
            "zinc-nickel-plating",
            baked=True,
            start_delay_hours=RELIEF_BAKE_WINDOW_HOURS + 6.0,
            duration_hours=72.0,
        )
        self.assertFalse(outcome["conforming"])

    def test_a_short_bake_is_non_conforming(self):
        outcome = relief_bake_verdict(
            "zinc-nickel-plating",
            baked=True,
            start_delay_hours=1.0,
            duration_hours=4.0,
        )
        self.assertFalse(outcome["conforming"])

    def test_a_bake_with_no_duration_rejected(self):
        with self.assertRaises(ValueError):
            relief_bake_verdict(
                "zinc-nickel-plating", baked=True, start_delay_hours=1.0
            )


class DurabilityTests(unittest.TestCase):
    def test_a_lubricated_finish_owes_wear_testing(self):
        owed = durability_tests_owed("dry-film-lubricant", "integration-hall")
        self.assertIn("coating-galling-and-wear", owed)

    def test_a_coastal_site_adds_a_salt_fog_durability_test(self):
        owed = durability_tests_owed("zinc-nickel-plating", "coastal-launch-site")
        self.assertIn("coating-salt-fog-durability", owed)

    def test_the_environment_never_duplicates_a_coating_test(self):
        owed = durability_tests_owed("dry-film-lubricant", "in-orbit-vacuum")
        self.assertEqual(len(owed), len(set(owed)))


class ProgrammeTests(unittest.TestCase):
    def test_a_clean_programme_is_accepted(self):
        self.assertEqual(
            assess_coating_programme(_case())["verdict"], VERDICT_ACCEPT
        )

    def test_a_thin_reading_gives_a_thickness_verdict(self):
        case = _case(thickness_readings_um=[2.0, 7.0, 8.0])
        self.assertEqual(
            assess_coating_programme(case)["verdict"], VERDICT_THICKNESS
        )

    def test_a_wrong_method_invalidates_the_whole_programme(self):
        case = _case(adhesion_method=ADHESION_TAPE)
        self.assertEqual(assess_coating_programme(case)["verdict"], VERDICT_INVALID)

    def test_flaking_gives_an_adhesion_verdict(self):
        case = _case(adhesion_result=ADHESION_FLAKING)
        self.assertEqual(assess_coating_programme(case)["verdict"], VERDICT_ADHESION)

    def test_short_exposure_gives_a_corrosion_verdict(self):
        case = _case(exposure_hours_run=100.0)
        self.assertEqual(assess_coating_programme(case)["verdict"], VERDICT_CORROSION)

    def test_a_missing_relief_bake_gives_a_relief_verdict(self):
        case = _case(relief_bake_done=False)
        self.assertEqual(assess_coating_programme(case)["verdict"], VERDICT_RELIEF)

    def test_outstanding_durability_tests_are_named(self):
        case = _case(durability_tests_recorded=[])
        result = assess_coating_programme(case)
        self.assertTrue(result["durability_tests_outstanding"])
        self.assertTrue(any("companion" in f for f in result["findings"]))

    def test_unlisted_coating_rejected_at_programme_level(self):
        with self.assertRaises(ValueError):
            assess_coating_programme(_case(coating_type="powder-paint"))

    def test_durability_record_given_as_a_string_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_programme(
                _case(durability_tests_recorded="coating-thermal-cycling")
            )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coating_programme("the plating looked shiny")


if __name__ == "__main__":
    unittest.main()

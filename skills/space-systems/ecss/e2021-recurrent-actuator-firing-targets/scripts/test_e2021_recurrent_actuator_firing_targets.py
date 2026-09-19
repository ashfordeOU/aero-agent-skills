#!/usr/bin/env python3
"""Gate 3 contract test for e2021-recurrent-actuator-firing-targets.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2021_recurrent_actuator_firing_targets.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2021_recurrent_actuator_firing_targets_logic import (  # noqa: E402
    DEFAULT_DURATION_FLOOR_S,
    MIN_SEPARATION_RATIO,
    WELL_SEPARATED_RATIO,
    at_least,
    categorize_separation,
    duration_is_floor_driven,
    evaluate_recurrent_firing_targets,
    population_currents,
    recommended_actuation_duration_s,
    required_drive_current_a,
    separation_ratio,
    validate_unit,
    within_limit,
)


def unit(uid, no_fire, all_fire):
    return {"unit_id": uid, "no_fire_a": no_fire, "all_fire_a": all_fire}


def codes(result):
    return sorted(f["code"] for f in result["findings"])


class TestUnitValidation(unittest.TestCase):
    def test_a_good_unit_resolves(self):
        self.assertEqual(validate_unit(unit("SN01", 1.0, 3.0)), ("SN01", 1.0, 3.0))

    def test_unit_id_is_stripped(self):
        self.assertEqual(validate_unit(unit("  SN02 ", 1.0, 3.0))[0], "SN02")

    def test_no_fire_at_or_above_all_fire_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(unit("SN03", 3.0, 3.0))

    def test_blank_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(unit("   ", 1.0, 3.0))

    def test_unknown_unit_key_rejected(self):
        bad = unit("SN04", 1.0, 3.0)
        bad["lot"] = "A"
        with self.assertRaises(ValueError):
            validate_unit(bad)

    def test_missing_unit_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit({"unit_id": "SN05", "no_fire_a": 1.0})

    def test_non_mapping_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit(["SN06", 1.0, 3.0])


class TestPopulation(unittest.TestCase):
    def test_worst_unit_sets_the_published_all_fire(self):
        pop = population_currents(
            [unit("A", 1.0, 3.0), unit("B", 1.2, 3.6), unit("C", 0.9, 3.1)]
        )
        self.assertAlmostEqual(pop["published_all_fire_a"], 3.6, places=12)

    def test_lowest_unit_sets_the_published_no_fire(self):
        pop = population_currents(
            [unit("A", 1.0, 3.0), unit("B", 1.2, 3.6), unit("C", 0.9, 3.1)]
        )
        self.assertAlmostEqual(pop["published_no_fire_a"], 0.9, places=12)

    def test_single_unit_population_is_itself(self):
        pop = population_currents([unit("A", 1.0, 3.0)])
        self.assertEqual(pop["unit_count"], 1)

    def test_empty_population_rejected(self):
        with self.assertRaises(ValueError):
            population_currents([])

    def test_duplicate_unit_id_rejected(self):
        with self.assertRaises(ValueError):
            population_currents([unit("A", 1.0, 3.0), unit("A", 1.1, 3.2)])

    def test_non_sequence_population_rejected(self):
        with self.assertRaises(ValueError):
            population_currents(unit("A", 1.0, 3.0))


class TestSeparation(unittest.TestCase):
    def test_ratio_is_all_fire_over_no_fire(self):
        self.assertAlmostEqual(separation_ratio(3.0, 1.5), 2.0, places=12)

    def test_exactly_at_the_well_separated_bound_is_well_separated(self):
        self.assertEqual(categorize_separation(WELL_SEPARATED_RATIO), "well-separated")

    def test_exactly_at_the_minimum_bound_is_adequate(self):
        self.assertEqual(categorize_separation(MIN_SEPARATION_RATIO), "adequate")

    def test_below_the_minimum_is_insufficient(self):
        self.assertEqual(categorize_separation(1.2), "insufficient")

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            separation_ratio(1.0, 2.0)

    def test_zero_no_fire_rejected(self):
        with self.assertRaises(ValueError):
            separation_ratio(3.0, 0.0)


class TestDriveAndDuration(unittest.TestCase):
    def test_design_factor_scales_the_all_fire(self):
        self.assertAlmostEqual(required_drive_current_a(4.0, 1.5), 6.0, places=12)

    def test_design_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            required_drive_current_a(4.0, 0.9)

    def test_duration_carries_the_margin_factor(self):
        self.assertAlmostEqual(
            recommended_actuation_duration_s(0.5, 2.0, 0.01), 1.0, places=12
        )

    def test_floor_governs_a_very_fast_mechanism(self):
        self.assertAlmostEqual(
            recommended_actuation_duration_s(0.001, 2.0, DEFAULT_DURATION_FLOOR_S),
            DEFAULT_DURATION_FLOOR_S,
            places=12,
        )

    def test_floor_driven_flag_tracks_the_governing_term(self):
        self.assertTrue(duration_is_floor_driven(0.001, 2.0, 0.01))
        self.assertFalse(duration_is_floor_driven(0.5, 2.0, 0.01))

    def test_margin_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            recommended_actuation_duration_s(0.5, 0.5)

    def test_zero_function_time_rejected(self):
        with self.assertRaises(ValueError):
            recommended_actuation_duration_s(0.0)


class TestComparators(unittest.TestCase):
    def test_within_limit_absorbs_representation_error(self):
        self.assertTrue(within_limit(0.1 + 0.2, 0.3))

    def test_within_limit_rejects_a_real_exceedance(self):
        self.assertFalse(within_limit(0.35, 0.3))

    def test_at_least_accepts_an_exact_match(self):
        self.assertTrue(at_least(0.3, 0.1 + 0.2))

    def test_at_least_rejects_a_shortfall(self):
        self.assertFalse(at_least(0.29, 0.3))


class TestEvaluateTargets(unittest.TestCase):
    def base_spec(self):
        return {
            "units": [unit("SN01", 1.0, 3.0), unit("SN02", 1.1, 3.2)],
            "function_time_s": 0.2,
            "target_all_fire_a": 3.5,
            "target_minimum_duration_s": 0.5,
            "drive_capability_a": 6.0,
            "rated_maximum_current_a": 8.0,
        }

    def test_healthy_product_is_recurrent_ready(self):
        result = evaluate_recurrent_firing_targets(self.base_spec())
        self.assertTrue(result["recurrent_ready"])
        self.assertEqual(result["findings"], [])

    def test_published_figures_bound_the_population(self):
        result = evaluate_recurrent_firing_targets(self.base_spec())
        self.assertAlmostEqual(result["published_all_fire_a"], 3.2, places=12)
        self.assertAlmostEqual(result["published_no_fire_a"], 1.0, places=12)

    def test_required_drive_uses_the_worst_unit(self):
        result = evaluate_recurrent_firing_targets(self.base_spec())
        self.assertAlmostEqual(result["required_drive_current_a"], 4.8, places=12)

    def test_narrow_band_population_is_flagged(self):
        spec = self.base_spec()
        spec["units"] = [unit("SN01", 2.6, 3.0)]
        result = evaluate_recurrent_firing_targets(spec)
        self.assertIn("firing-band-too-narrow", codes(result))
        self.assertEqual(result["separation_category"], "insufficient")

    def test_worst_unit_above_the_catalogue_target(self):
        spec = self.base_spec()
        spec["target_all_fire_a"] = 3.0
        result = evaluate_recurrent_firing_targets(spec)
        self.assertIn("all-fire-above-catalogue-target", codes(result))

    def test_catalogue_duration_below_the_recommendation(self):
        spec = self.base_spec()
        spec["target_minimum_duration_s"] = 0.2
        result = evaluate_recurrent_firing_targets(spec)
        self.assertIn("published-duration-below-recommendation", codes(result))

    def test_bus_that_cannot_reach_the_design_current(self):
        spec = self.base_spec()
        spec["drive_capability_a"] = 4.0
        result = evaluate_recurrent_firing_targets(spec)
        self.assertIn("drive-cannot-reach-all-fire", codes(result))

    def test_design_current_over_the_part_rating(self):
        spec = self.base_spec()
        spec["rated_maximum_current_a"] = 4.0
        result = evaluate_recurrent_firing_targets(spec)
        self.assertIn("design-current-over-actuator-rating", codes(result))

    def test_command_shorter_than_the_minimum_actuation(self):
        spec = self.base_spec()
        spec["commanded_duration_s"] = 0.1
        result = evaluate_recurrent_firing_targets(spec)
        self.assertIn("command-shorter-than-minimum-actuation", codes(result))

    def test_command_exactly_at_the_recommendation_passes(self):
        spec = self.base_spec()
        spec["commanded_duration_s"] = result_duration = 0.4
        result = evaluate_recurrent_firing_targets(spec)
        self.assertAlmostEqual(result["recommended_duration_s"], result_duration, places=12)
        self.assertNotIn("command-shorter-than-minimum-actuation", codes(result))

    def test_unknown_spec_key_rejected(self):
        spec = self.base_spec()
        spec["vendor"] = "acme"
        with self.assertRaises(ValueError):
            evaluate_recurrent_firing_targets(spec)

    def test_missing_function_time_rejected(self):
        spec = self.base_spec()
        del spec["function_time_s"]
        with self.assertRaises(ValueError):
            evaluate_recurrent_firing_targets(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_recurrent_firing_targets([("function_time_s", 0.2)])

    def test_negative_drive_capability_rejected(self):
        spec = self.base_spec()
        spec["drive_capability_a"] = -1.0
        with self.assertRaises(ValueError):
            evaluate_recurrent_firing_targets(spec)


if __name__ == "__main__":
    unittest.main()

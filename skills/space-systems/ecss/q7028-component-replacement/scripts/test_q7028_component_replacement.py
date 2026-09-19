"""Contract tests for the component replacement and thermal control logic."""

import math
import unittest

from q7028_component_replacement_logic import (
    MSL_FLOOR_LIFE_HOURS,
    adjacent_exposure_c,
    assess_component_replacement,
    bake_required,
    floor_life_hours,
    neighbours_over_limit,
    peak_temperature_c,
    replacement_allowance,
    require_count,
    require_real,
    time_above_c,
    validate_thermal_profile,
)

# A symmetric removal profile: ambient, a peak, and back to ambient.
PROFILE = [(0.0, 25.0), (10.0, 225.0), (20.0, 25.0)]


class InputValidationTests(unittest.TestCase):
    def test_require_real_returns_float(self):
        self.assertAlmostEqual(require_real("x", 12), 12.0, places=9)

    def test_require_real_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            require_real("x", float("-inf"))

    def test_require_count_rejects_negative(self):
        with self.assertRaises(ValueError):
            require_count("n", -2)

    def test_profile_needs_two_samples(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile([(0.0, 25.0)])

    def test_profile_times_must_increase(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile([(0.0, 25.0), (0.0, 200.0)])

    def test_malformed_profile_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_thermal_profile([(0.0, 25.0), (10.0,)])


class ProfileReadingTests(unittest.TestCase):
    def test_peak_is_the_highest_sample(self):
        self.assertAlmostEqual(peak_temperature_c(PROFILE), 225.0, places=9)

    def test_time_above_interpolates_both_crossings(self):
        self.assertAlmostEqual(time_above_c(PROFILE, 125.0), 10.0, places=9)

    def test_threshold_above_the_peak_gives_zero(self):
        self.assertAlmostEqual(time_above_c(PROFILE, 300.0), 0.0, places=9)

    def test_threshold_below_the_whole_profile_gives_the_full_span(self):
        self.assertAlmostEqual(time_above_c(PROFILE, 0.0), 20.0, places=9)

    def test_threshold_exactly_at_the_peak_counts_the_instant_only(self):
        self.assertAlmostEqual(time_above_c(PROFILE, 225.0), 0.0, places=9)

    def test_a_flat_hold_is_counted_whole(self):
        flat = [(0.0, 200.0), (5.0, 200.0), (10.0, 25.0)]
        self.assertAlmostEqual(time_above_c(flat, 150.0), 5.0 + 5.0 * (50.0 / 175.0),
                               places=9)

    def test_asymmetric_ramp_is_interpolated(self):
        ramp = [(0.0, 25.0), (4.0, 125.0)]
        self.assertAlmostEqual(time_above_c(ramp, 75.0), 2.0, places=9)


class AdjacentExposureTests(unittest.TestCase):
    def test_zero_distance_sees_the_full_peak(self):
        self.assertAlmostEqual(adjacent_exposure_c(225.0, 25.0, 0.0, 5.0), 225.0,
                               places=9)

    def test_one_decay_length_drops_by_e(self):
        value = adjacent_exposure_c(225.0, 25.0, 5.0, 5.0)
        self.assertAlmostEqual(value, 25.0 + 200.0 / math.e, places=9)

    def test_far_neighbour_approaches_ambient(self):
        value = adjacent_exposure_c(225.0, 25.0, 200.0, 5.0)
        self.assertAlmostEqual(value, 25.0, places=9)

    def test_peak_below_ambient_rejected(self):
        with self.assertRaises(ValueError):
            adjacent_exposure_c(20.0, 25.0, 5.0, 5.0)

    def test_zero_decay_length_rejected(self):
        with self.assertRaises(ValueError):
            adjacent_exposure_c(225.0, 25.0, 5.0, 0.0)

    def test_close_hot_neighbour_is_flagged(self):
        exceeded = neighbours_over_limit(
            [{"reference": "C12", "distance_mm": 2.0, "max_temperature_c": 100.0}],
            225.0, 25.0, 5.0,
        )
        self.assertEqual(len(exceeded), 1)
        self.assertEqual(exceeded[0]["reference"], "C12")

    def test_distant_neighbour_is_not_flagged(self):
        exceeded = neighbours_over_limit(
            [{"reference": "R4", "distance_mm": 40.0, "max_temperature_c": 100.0}],
            225.0, 25.0, 5.0,
        )
        self.assertEqual(exceeded, [])

    def test_neighbour_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            neighbours_over_limit([{"reference": "R4"}], 225.0, 25.0, 5.0)

    def test_non_mapping_neighbour_rejected(self):
        with self.assertRaises(ValueError):
            neighbours_over_limit(["R4"], 225.0, 25.0, 5.0)


class MoistureSensitivityTests(unittest.TestCase):
    def test_level_one_is_unlimited(self):
        self.assertIsNone(floor_life_hours(1))

    def test_level_three_floor_life(self):
        self.assertAlmostEqual(floor_life_hours(3), 168.0, places=9)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_hours(9)

    def test_non_integer_level_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_hours(3.0)

    def test_level_one_never_owes_a_bake(self):
        self.assertFalse(bake_required(1, 100000.0)["bake_required"])

    def test_inside_the_floor_life_no_bake(self):
        self.assertFalse(bake_required(3, 100.0)["bake_required"])

    def test_floor_time_exactly_on_the_life_needs_no_bake(self):
        self.assertFalse(bake_required(3, MSL_FLOOR_LIFE_HOURS[3])["bake_required"])

    def test_over_the_floor_life_owes_a_bake(self):
        self.assertTrue(bake_required(3, 400.0)["bake_required"])

    def test_an_already_baked_part_does_not_owe_another(self):
        self.assertFalse(bake_required(3, 400.0, True)["bake_required"])

    def test_non_boolean_baked_flag_rejected(self):
        with self.assertRaises(ValueError):
            bake_required(3, 400.0, "yes")


class AllowanceTests(unittest.TestCase):
    def test_fresh_site_has_room(self):
        self.assertFalse(replacement_allowance(0, 2)["exhausted"])

    def test_last_replacement_is_flagged(self):
        self.assertTrue(replacement_allowance(1, 2)["last_allowed"])

    def test_exhausted_site(self):
        self.assertTrue(replacement_allowance(2, 2)["exhausted"])

    def test_zero_maximum_rejected(self):
        with self.assertRaises(ValueError):
            replacement_allowance(0, 0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "profile": PROFILE,
            "ambient_c": 25.0,
            "laminate_max_temperature_c": 260.0,
            "damage_threshold_c": 200.0,
            "max_time_above_threshold_s": 5.0,
            "decay_length_mm": 5.0,
            "neighbours": [
                {"reference": "R4", "distance_mm": 40.0, "max_temperature_c": 100.0}
            ],
            "replacements_done": 0,
            "max_replacements": 2,
            "msl": 3,
            "floor_hours": 24.0,
        }
        spec.update(overrides)
        return spec

    def test_clean_plan_proceeds(self):
        result = assess_component_replacement(self._spec())
        self.assertEqual(result["verdict"], "proceed")
        self.assertEqual(result["findings"], [])

    def test_peak_over_the_laminate_limit_refuses(self):
        result = assess_component_replacement(
            self._spec(laminate_max_temperature_c=200.0)
        )
        self.assertEqual(result["verdict"], "refuse")

    def test_too_long_above_the_threshold_refuses(self):
        result = assess_component_replacement(
            self._spec(max_time_above_threshold_s=0.5)
        )
        self.assertEqual(result["verdict"], "refuse")

    def test_exhausted_site_refuses(self):
        result = assess_component_replacement(self._spec(replacements_done=2))
        self.assertEqual(result["verdict"], "refuse")

    def test_hot_neighbour_demands_controls(self):
        result = assess_component_replacement(self._spec(neighbours=[
            {"reference": "C12", "distance_mm": 2.0, "max_temperature_c": 100.0}
        ]))
        self.assertEqual(result["verdict"], "proceed-with-controls")
        self.assertEqual(len(result["neighbours_over_limit"]), 1)

    def test_moisture_sensitive_part_demands_a_bake(self):
        result = assess_component_replacement(self._spec(floor_hours=400.0))
        self.assertEqual(result["verdict"], "proceed-with-controls")
        self.assertTrue(result["bake"]["bake_required"])

    def test_last_allowed_replacement_demands_controls(self):
        result = assess_component_replacement(self._spec(replacements_done=1))
        self.assertEqual(result["verdict"], "proceed-with-controls")

    def test_low_preheat_demands_controls(self):
        result = assess_component_replacement(
            self._spec(min_preheat_c=100.0, preheat_c=60.0)
        )
        self.assertTrue(result["preheat_below_minimum"])
        self.assertEqual(result["verdict"], "proceed-with-controls")

    def test_preheat_on_its_minimum_is_accepted(self):
        result = assess_component_replacement(
            self._spec(min_preheat_c=100.0, preheat_c=100.0)
        )
        self.assertFalse(result["preheat_below_minimum"])

    def test_preheat_minimum_without_a_reading_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_replacement(self._spec(min_preheat_c=100.0))

    def test_dwell_above_the_threshold_is_reported(self):
        result = assess_component_replacement(self._spec())
        self.assertAlmostEqual(result["time_above_threshold_s"], 2.5, places=9)

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["neighbours"]
        with self.assertRaises(ValueError):
            assess_component_replacement(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_replacement("profile")


if __name__ == "__main__":
    unittest.main()

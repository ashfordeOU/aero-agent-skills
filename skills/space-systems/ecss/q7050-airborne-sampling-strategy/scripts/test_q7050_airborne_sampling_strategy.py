"""Contract tests for the airborne sampling strategy logic."""

import unittest

from q7050_airborne_sampling_strategy_logic import (
    FLOOR_SAMPLE_VOLUME_L,
    MIN_LOCATIONS,
    MIN_SAMPLE_DURATION_MIN,
    TARGET_PARTICLE_COUNT,
    assess_sampling_strategy,
    location_count_from_area,
    location_count_from_table,
    minimum_sample_volume_l,
    plan_location_sampling,
    sampling_duration_min,
    validate_area_m2,
    validate_flow_rate_lpm,
    validate_limit_per_m3,
)

# A representative area-to-location table supplied by the caller.
TABLE = [(10.0, 2), (25.0, 3), (50.0, 5), (100.0, 8), (400.0, 16)]


class ValidationTests(unittest.TestCase):
    def test_area_is_returned_as_a_float(self):
        self.assertAlmostEqual(validate_area_m2(144), 144.0, places=12)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(0.0)

    def test_boolean_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(True)

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_per_m3(-10.0)

    def test_non_finite_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_limit_per_m3(float("inf"))

    def test_zero_flow_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow_rate_lpm(0.0)

    def test_string_flow_rate_rejected(self):
        with self.assertRaises(ValueError):
            validate_flow_rate_lpm("28.3")


class LocationCountTests(unittest.TestCase):
    def test_square_root_rule_on_a_square_area(self):
        self.assertEqual(location_count_from_area(144.0), 12)

    def test_square_root_rule_rounds_up(self):
        self.assertEqual(location_count_from_area(150.0), 13)

    def test_minimum_applies_to_a_tiny_zone(self):
        self.assertEqual(location_count_from_area(1.0), MIN_LOCATIONS)

    def test_operator_request_can_raise_the_count(self):
        self.assertEqual(location_count_from_area(144.0, 20), 20)

    def test_operator_request_cannot_lower_the_count(self):
        self.assertEqual(location_count_from_area(144.0, 4), 12)

    def test_zero_requested_rejected(self):
        with self.assertRaises(ValueError):
            location_count_from_area(144.0, 0)


class LocationTableTests(unittest.TestCase):
    def test_area_inside_a_band_takes_that_bands_count(self):
        self.assertEqual(location_count_from_table(30.0, TABLE), 5)

    def test_area_exactly_on_a_bound_takes_that_band(self):
        self.assertEqual(location_count_from_table(25.0, TABLE), 3)

    def test_small_area_still_carries_the_minimum(self):
        self.assertGreaterEqual(location_count_from_table(1.0, TABLE), MIN_LOCATIONS)

    def test_area_above_the_table_is_refused(self):
        with self.assertRaises(ValueError):
            location_count_from_table(1000.0, TABLE)

    def test_non_increasing_bounds_rejected(self):
        with self.assertRaises(ValueError):
            location_count_from_table(5.0, [(10.0, 2), (10.0, 3)])

    def test_decreasing_counts_rejected(self):
        with self.assertRaises(ValueError):
            location_count_from_table(5.0, [(10.0, 4), (20.0, 2)])

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            location_count_from_table(5.0, [])


class SampleVolumeTests(unittest.TestCase):
    def test_volume_meets_the_statistical_target(self):
        limit = 29.3
        volume = minimum_sample_volume_l(limit)
        self.assertAlmostEqual(volume * limit / 1000.0, TARGET_PARTICLE_COUNT, places=9)

    def test_a_tighter_limit_needs_more_air(self):
        self.assertGreater(minimum_sample_volume_l(29.3), minimum_sample_volume_l(293.0))

    def test_a_loose_limit_is_held_at_the_floor_volume(self):
        self.assertAlmostEqual(minimum_sample_volume_l(1.0e6), FLOOR_SAMPLE_VOLUME_L, places=9)

    def test_target_count_scales_the_volume(self):
        single = minimum_sample_volume_l(29.3, TARGET_PARTICLE_COUNT)
        double = minimum_sample_volume_l(29.3, TARGET_PARTICLE_COUNT * 2.0)
        self.assertAlmostEqual(double, single * 2.0, places=9)

    def test_zero_target_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sample_volume_l(29.3, 0.0)


class DurationTests(unittest.TestCase):
    def test_duration_is_volume_over_flow(self):
        self.assertAlmostEqual(sampling_duration_min(56.6, 28.3), 2.0, places=9)

    def test_short_sample_is_held_at_the_floor(self):
        self.assertAlmostEqual(
            sampling_duration_min(5.0, 100.0), MIN_SAMPLE_DURATION_MIN, places=9
        )

    def test_duration_exactly_at_the_floor_is_kept(self):
        self.assertAlmostEqual(
            sampling_duration_min(28.3, 28.3), MIN_SAMPLE_DURATION_MIN, places=9
        )

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            sampling_duration_min(0.0, 28.3)

    def test_zero_flow_rejected(self):
        with self.assertRaises(ValueError):
            sampling_duration_min(56.6, 0.0)


class PlanLocationTests(unittest.TestCase):
    def test_air_drawn_matches_duration_times_flow(self):
        record = plan_location_sampling(29.3, 28.3)
        self.assertAlmostEqual(
            record["air_drawn_l"], record["duration_min"] * record["flow_rate_lpm"], places=9
        )

    def test_no_floor_is_applied_for_a_tight_limit(self):
        record = plan_location_sampling(29.3, 28.3)
        self.assertFalse(record["volume_floor_applied"])
        self.assertFalse(record["duration_floor_applied"])

    def test_volume_floor_is_reported(self):
        record = plan_location_sampling(1.0e6, 28.3)
        self.assertTrue(record["volume_floor_applied"])

    def test_duration_floor_is_reported(self):
        record = plan_location_sampling(3520.0, 28.3)
        self.assertTrue(record["duration_floor_applied"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "area_m2": 144.0,
            "limit_per_m3": 29.3,
            "flow_rate_lpm": 28.3,
            "flow_rate_band": (25.0, 30.0),
        }
        spec.update(overrides)
        return spec

    def test_a_sound_strategy_is_acceptable(self):
        result = assess_sampling_strategy(self._spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["locations"], 12)

    def test_zone_air_is_per_location_air_times_locations(self):
        result = assess_sampling_strategy(self._spec())
        self.assertAlmostEqual(
            result["zone_air_l"], result["air_per_location_l"] * result["locations"], places=9
        )

    def test_zone_duration_scales_with_locations(self):
        result = assess_sampling_strategy(self._spec())
        self.assertAlmostEqual(
            result["zone_duration_min"], result["duration_min"] * result["locations"], places=9
        )

    def test_flow_rate_outside_the_calibrated_band_is_flagged(self):
        result = assess_sampling_strategy(self._spec(flow_rate_lpm=50.0))
        self.assertTrue(any("calibrated band" in f for f in result["findings"]))

    def test_duration_floor_is_raised_as_a_finding(self):
        result = assess_sampling_strategy(self._spec(limit_per_m3=3520.0))
        self.assertTrue(any("duration is held at" in f for f in result["findings"]))

    def test_volume_floor_is_raised_as_a_finding(self):
        result = assess_sampling_strategy(self._spec(limit_per_m3=1.0e6))
        self.assertTrue(any("volume is held at" in f for f in result["findings"]))

    def test_an_operator_cut_to_the_location_count_is_flagged(self):
        result = assess_sampling_strategy(self._spec(requested_locations=4))
        self.assertEqual(result["locations"], 12)
        self.assertTrue(any("derived count stands" in f for f in result["findings"]))

    def test_an_operator_increase_is_honoured_silently(self):
        result = assess_sampling_strategy(self._spec(requested_locations=20))
        self.assertEqual(result["locations"], 20)
        self.assertEqual(result["findings"], [])

    def test_a_supplied_table_overrides_the_square_root_rule(self):
        result = assess_sampling_strategy(self._spec(area_m2=30.0, location_table=TABLE))
        self.assertEqual(result["derived_locations"], 5)

    def test_inverted_flow_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_sampling_strategy(self._spec(flow_rate_band=(30.0, 25.0)))

    def test_malformed_flow_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_sampling_strategy(self._spec(flow_rate_band=(28.3,)))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["limit_per_m3"]
        with self.assertRaises(ValueError):
            assess_sampling_strategy(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_sampling_strategy(["area_m2"])


if __name__ == "__main__":
    unittest.main()

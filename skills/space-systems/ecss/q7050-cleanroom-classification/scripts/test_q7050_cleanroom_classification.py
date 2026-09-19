"""Contract tests for the cleanroom airborne particle qualification logic."""

import math
import unittest

from q7050_cleanroom_classification_logic import (
    CONCENTRATION_TOLERANCE,
    DEFAULT_REFERENCE_SIZE_UM,
    LOOSE_CLASS_INTERVAL_DAYS,
    MIN_SAMPLE_TIME_S,
    MIN_SAMPLE_VOLUME_L,
    TIGHT_CLASS_INTERVAL_DAYS,
    assess_cleanroom_qualification,
    grade_location,
    limit_concentration,
    location_concentration,
    minimum_sample_locations,
    requalification_interval_days,
    sampling_time_s,
    single_sample_volume_l,
    validate_class,
    validate_size_um,
)

LOCATION_TABLE = [(50.0, 2), (200.0, 3), (600.0, 6)]


class ValidationTests(unittest.TestCase):
    def test_class_returns_float(self):
        self.assertAlmostEqual(validate_class(5), 5.0, places=12)

    def test_class_below_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_class(0.5)

    def test_class_above_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_class(11)

    def test_boolean_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_class(True)

    def test_size_must_be_positive(self):
        with self.assertRaises(ValueError):
            validate_size_um(0.0)

    def test_size_must_be_numeric(self):
        with self.assertRaises(ValueError):
            validate_size_um("0.5")


class LimitConcentrationTests(unittest.TestCase):
    def test_anchor_size_gives_the_class_decade(self):
        value = limit_concentration(5, DEFAULT_REFERENCE_SIZE_UM)
        self.assertAlmostEqual(value, 100000.0, places=6)

    def test_limit_falls_with_particle_size(self):
        fine = limit_concentration(5, 0.1)
        coarse = limit_concentration(5, 5.0)
        self.assertGreater(fine, coarse * 100.0)

    def test_one_class_step_is_a_decade(self):
        five = limit_concentration(5, 0.5)
        six = limit_concentration(6, 0.5)
        self.assertAlmostEqual(six / five, 10.0, places=9)

    def test_half_micrometre_limit_for_class_five(self):
        independent = 1.0e5 * math.exp(2.08 * math.log(0.1 / 0.5))
        self.assertAlmostEqual(limit_concentration(5, 0.5), independent, places=6)

    def test_non_positive_exponent_rejected(self):
        with self.assertRaises(ValueError):
            limit_concentration(5, 0.5, exponent=0.0)


class SamplePlanTests(unittest.TestCase):
    def test_square_root_rule_rounds_up(self):
        self.assertEqual(minimum_sample_locations(90.0), 10)

    def test_square_root_rule_exact_square(self):
        self.assertEqual(minimum_sample_locations(100.0), 10)

    def test_tiny_room_still_needs_one_location(self):
        self.assertEqual(minimum_sample_locations(0.5), 1)

    def test_table_entry_wins_when_supplied(self):
        self.assertEqual(minimum_sample_locations(180.0, LOCATION_TABLE), 3)

    def test_table_lower_band_is_used_for_a_small_room(self):
        self.assertEqual(minimum_sample_locations(40.0, LOCATION_TABLE), 2)

    def test_area_beyond_the_table_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sample_locations(900.0, LOCATION_TABLE)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sample_locations(0.0)

    def test_malformed_table_entry_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sample_locations(10.0, [(50.0, 0)])


class SampleSizingTests(unittest.TestCase):
    def test_volume_collects_the_required_particle_count(self):
        volume = single_sample_volume_l(2000.0, 20.0, 2.0)
        self.assertAlmostEqual(volume, 10.0, places=9)

    def test_tighter_limit_demands_a_larger_sample(self):
        tight = single_sample_volume_l(1000.0)
        loose = single_sample_volume_l(10000.0)
        self.assertGreater(tight, loose)

    def test_volume_floor_applies_to_a_dirty_room(self):
        self.assertAlmostEqual(
            single_sample_volume_l(1.0e7), MIN_SAMPLE_VOLUME_L, places=9
        )

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            single_sample_volume_l(0.0)

    def test_sampling_time_follows_volume_and_flow(self):
        self.assertAlmostEqual(sampling_time_s(56.6, 28.3, 1.0), 120.0, places=9)

    def test_minimum_sampling_time_applies(self):
        self.assertAlmostEqual(sampling_time_s(2.0, 28.3), MIN_SAMPLE_TIME_S, places=9)

    def test_zero_flow_rate_rejected(self):
        with self.assertRaises(ValueError):
            sampling_time_s(10.0, 0.0)


class LocationGradingTests(unittest.TestCase):
    def test_concentration_is_counts_per_cubic_metre(self):
        self.assertAlmostEqual(location_concentration(50.0, 1000.0), 50.0, places=9)

    def test_smaller_sample_raises_the_concentration(self):
        self.assertAlmostEqual(location_concentration(50.0, 500.0), 100.0, places=9)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            location_concentration(-1.0, 100.0)

    def test_zero_volume_rejected(self):
        with self.assertRaises(ValueError):
            location_concentration(10.0, 0.0)

    def test_clean_location_is_acceptable(self):
        record = grade_location(
            {"id": "L1", "volume_l": 28.3, "counts": {0.5: 50.0}},
            {0.5: 3515.3},
            10.0,
        )
        self.assertTrue(record["acceptable"])
        self.assertTrue(record["per_size"][0.5]["within_limit"])

    def test_location_at_the_limit_is_within_it(self):
        measured = location_concentration(100.0, 28.3)
        record = grade_location(
            {"id": "L2", "volume_l": 28.3, "counts": {0.5: 100.0}},
            {0.5: measured},
            10.0,
        )
        self.assertAlmostEqual(
            record["per_size"][0.5]["measured_per_m3"], measured, places=9
        )
        self.assertTrue(record["within_limits"])

    def test_dirty_location_is_not_acceptable(self):
        record = grade_location(
            {"id": "L3", "volume_l": 28.3, "counts": {0.5: 500000.0}},
            {0.5: 3515.3},
            10.0,
        )
        self.assertFalse(record["within_limits"])
        self.assertFalse(record["acceptable"])

    def test_short_sample_volume_is_not_acceptable(self):
        record = grade_location(
            {"id": "L4", "volume_l": 5.0, "counts": {0.5: 5.0}},
            {0.5: 3515.3},
            10.0,
        )
        self.assertTrue(record["within_limits"])
        self.assertFalse(record["volume_sufficient"])
        self.assertFalse(record["acceptable"])

    def test_missing_limit_for_a_reported_size_rejected(self):
        with self.assertRaises(ValueError):
            grade_location(
                {"id": "L5", "volume_l": 28.3, "counts": {5.0: 1.0}},
                {0.5: 3515.3},
                10.0,
            )

    def test_location_without_counts_rejected(self):
        with self.assertRaises(ValueError):
            grade_location({"id": "L6", "volume_l": 28.3, "counts": {}}, {0.5: 1.0}, 1.0)

    def test_location_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            grade_location({"id": "L7", "volume_l": 28.3}, {0.5: 1.0}, 1.0)


class IntervalTests(unittest.TestCase):
    def test_tight_class_is_requalified_sooner(self):
        self.assertAlmostEqual(
            requalification_interval_days(5), float(TIGHT_CLASS_INTERVAL_DAYS), places=9
        )

    def test_loose_class_gets_the_longer_interval(self):
        self.assertAlmostEqual(
            requalification_interval_days(7), float(LOOSE_CLASS_INTERVAL_DAYS), places=9
        )

    def test_interval_rejects_an_impossible_class(self):
        with self.assertRaises(ValueError):
            requalification_interval_days(0)


class QualificationTests(unittest.TestCase):
    def _locations(self, count=3, volume=28.3, particles=50.0):
        return [
            {"id": "L%d" % i, "volume_l": volume, "counts": {0.5: particles}}
            for i in range(1, count + 1)
        ]

    def _spec(self, **overrides):
        spec = {
            "area_m2": 180.0,
            "iso_class": 5,
            "reference_sizes_um": [0.5],
            "flow_rate_lpm": 28.3,
            "locations": self._locations(),
            "facility_interval_days": 183.0,
            "location_table": LOCATION_TABLE,
        }
        spec.update(overrides)
        return spec

    def test_compliant_campaign_qualifies_the_room(self):
        result = assess_cleanroom_qualification(self._spec())
        self.assertTrue(result["qualified"])
        self.assertEqual(result["findings"], [])

    def test_sample_plan_is_reported(self):
        result = assess_cleanroom_qualification(self._spec())
        self.assertEqual(result["required_locations"], 3)
        independent = 20.0 / (1.0e5 * math.exp(2.08 * math.log(0.2))) * 1000.0
        self.assertAlmostEqual(result["single_sample_volume_l"], independent, places=9)

    def test_sampling_time_never_drops_below_the_floor(self):
        result = assess_cleanroom_qualification(self._spec())
        self.assertAlmostEqual(result["sampling_time_s"], MIN_SAMPLE_TIME_S, places=9)

    def test_too_few_locations_is_a_finding(self):
        result = assess_cleanroom_qualification(self._spec(locations=self._locations(2)))
        self.assertFalse(result["qualified"])
        self.assertIn("sample locations", result["findings"][0])

    def test_one_dirty_location_fails_the_room(self):
        locations = self._locations()
        locations[1] = {"id": "HOT", "volume_l": 28.3, "counts": {0.5: 900000.0}}
        result = assess_cleanroom_qualification(self._spec(locations=locations))
        self.assertFalse(result["qualified"])
        self.assertTrue(any("HOT" in f for f in result["findings"]))

    def test_short_volume_location_is_a_finding(self):
        locations = self._locations()
        locations[0] = {"id": "SHORT", "volume_l": 1.0, "counts": {0.5: 1.0}}
        result = assess_cleanroom_qualification(self._spec(locations=locations))
        self.assertTrue(any("SHORT" in f for f in result["findings"]))

    def test_lapsed_facility_interval_is_a_finding(self):
        result = assess_cleanroom_qualification(self._spec(facility_interval_days=365.0))
        self.assertFalse(result["qualified"])
        self.assertTrue(any("re-qualifies" in f for f in result["findings"]))

    def test_facility_interval_exactly_at_the_limit_passes(self):
        interval = requalification_interval_days(5)
        result = assess_cleanroom_qualification(self._spec(facility_interval_days=interval))
        self.assertAlmostEqual(result["facility_interval_days"], interval, places=9)
        self.assertTrue(result["qualified"])

    def test_two_reference_sizes_both_carry_limits(self):
        result = assess_cleanroom_qualification(
            self._spec(
                reference_sizes_um=[0.5, 5.0],
                locations=[
                    {"id": "L%d" % i, "volume_l": 700.0, "counts": {0.5: 50.0, 5.0: 1.0}}
                    for i in range(1, 4)
                ],
            )
        )
        self.assertEqual(len(result["limits_per_m3"]), 2)
        self.assertTrue(result["qualified"])

    def test_tighter_class_demands_a_larger_sample(self):
        loose = assess_cleanroom_qualification(self._spec())
        tight = assess_cleanroom_qualification(self._spec(iso_class=4))
        self.assertGreater(tight["single_sample_volume_l"], loose["single_sample_volume_l"])

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["flow_rate_lpm"]
        with self.assertRaises(ValueError):
            assess_cleanroom_qualification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanroom_qualification(["area_m2"])

    def test_empty_reference_size_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanroom_qualification(self._spec(reference_sizes_um=[]))

    def test_tolerance_is_a_representation_allowance_only(self):
        self.assertAlmostEqual(CONCENTRATION_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main()

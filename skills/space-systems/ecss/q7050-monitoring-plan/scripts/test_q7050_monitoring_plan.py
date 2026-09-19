"""Contract tests for the particle contamination monitoring plan logic."""

import unittest

from q7050_monitoring_plan_logic import (
    BASE_INTERVAL_DAYS,
    CRITICALITY_FACTORS,
    METHODS,
    MIN_LOCATIONS,
    MIN_OCCURRENCES,
    assess_monitoring_plan,
    build_plan,
    interval_days,
    location_count,
    occurrences,
    plan_totals,
    plan_zone,
    validate_area_m2,
    validate_campaign_days,
    validate_criticality,
    validate_identifier,
    validate_method,
)


class ValidationTests(unittest.TestCase):
    def test_identifier_is_stripped(self):
        self.assertEqual(validate_identifier("  ISO7-BAY  "), "ISO7-BAY")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(7)

    def test_zero_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(0.0)

    def test_boolean_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_area_m2(True)

    def test_method_is_normalised(self):
        self.assertEqual(validate_method(" Tape-Lift "), "tape-lift")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_method("swab")

    def test_criticality_is_normalised(self):
        self.assertEqual(validate_criticality("CRITICAL"), "critical")

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_criticality("urgent")

    def test_negative_campaign_rejected(self):
        with self.assertRaises(ValueError):
            validate_campaign_days(-5.0)


class LocationCountTests(unittest.TestCase):
    def test_square_area_gives_its_root(self):
        self.assertEqual(location_count(100.0), 10)

    def test_non_square_area_rounds_up(self):
        self.assertEqual(location_count(24.0), 5)

    def test_exact_square_does_not_round_up(self):
        self.assertEqual(location_count(16.0), 4)

    def test_tiny_zone_still_carries_the_minimum(self):
        self.assertEqual(location_count(1.0), MIN_LOCATIONS)

    def test_operator_request_can_only_increase_the_count(self):
        self.assertEqual(location_count(100.0, 14), 14)
        self.assertEqual(location_count(100.0, 3), 10)

    def test_zero_requested_locations_rejected(self):
        with self.assertRaises(ValueError):
            location_count(100.0, 0)

    def test_non_integer_request_rejected(self):
        with self.assertRaises(ValueError):
            location_count(100.0, 4.5)


class IntervalTests(unittest.TestCase):
    def test_routine_interval_is_the_base_period(self):
        self.assertAlmostEqual(
            interval_days("airborne-count", "routine"), BASE_INTERVAL_DAYS["airborne-count"]
        )

    def test_criticality_shortens_the_interval(self):
        base = interval_days("surface-fallout", "routine")
        hot = interval_days("surface-fallout", "critical")
        self.assertAlmostEqual(hot * CRITICALITY_FACTORS["critical"], base, places=9)

    def test_interval_is_floored_at_one_day(self):
        self.assertAlmostEqual(interval_days("surface-fallout", "critical"), 3.5)
        self.assertGreaterEqual(interval_days("airborne-count", "critical"), 1.0)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            interval_days("swab", "routine")


class OccurrenceTests(unittest.TestCase):
    def test_exact_multiple_counts_both_ends(self):
        self.assertEqual(occurrences(30.0, 30.0), 2)

    def test_campaign_shorter_than_the_interval_gives_one(self):
        self.assertEqual(occurrences(7.0, 30.0), 1)

    def test_partial_interval_is_not_counted_twice(self):
        self.assertEqual(occurrences(35.0, 30.0), 2)

    def test_three_intervals_give_four_occurrences(self):
        self.assertEqual(occurrences(90.0, 30.0), 4)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            occurrences(30.0, 0.0)

    def test_non_numeric_interval_rejected(self):
        with self.assertRaises(ValueError):
            occurrences(30.0, "30")


class PlanZoneTests(unittest.TestCase):
    def _zone(self, **overrides):
        zone = {
            "zone_id": "ISO7-INTEGRATION",
            "area_m2": 144.0,
            "iso_class": 7,
            "methods": ["airborne-count", "surface-fallout"],
            "criticality": "elevated",
        }
        zone.update(overrides)
        return zone

    def test_one_entry_per_method(self):
        entries = plan_zone(self._zone(), 60.0)
        self.assertEqual(len(entries), 2)
        self.assertEqual([e["method"] for e in entries], ["airborne-count", "surface-fallout"])

    def test_duplicate_method_is_collapsed(self):
        entries = plan_zone(
            self._zone(methods=["airborne-count", "airborne-count"]), 60.0
        )
        self.assertEqual(len(entries), 1)

    def test_locations_come_from_the_floor_area(self):
        entries = plan_zone(self._zone(), 60.0)
        self.assertEqual(entries[0]["locations"], 12)

    def test_samples_are_locations_times_occurrences(self):
        entry = plan_zone(self._zone(), 60.0)[0]
        self.assertEqual(entry["samples"], entry["locations"] * entry["occurrences"])

    def test_missing_zone_key_rejected(self):
        zone = self._zone()
        del zone["criticality"]
        with self.assertRaises(ValueError):
            plan_zone(zone, 60.0)

    def test_non_sequence_methods_rejected(self):
        with self.assertRaises(ValueError):
            plan_zone(self._zone(methods="airborne-count"), 60.0)

    def test_non_mapping_zone_rejected(self):
        with self.assertRaises(ValueError):
            plan_zone(["ISO7"], 60.0)


class PlanTotalsTests(unittest.TestCase):
    def test_totals_sum_the_entries(self):
        entries = [
            {"method": "airborne-count", "samples": 10},
            {"method": "tape-lift", "samples": 4},
        ]
        totals = plan_totals(entries)
        self.assertEqual(totals["total_samples"], 14)
        self.assertEqual(totals["per_method"]["tape-lift"], 4)

    def test_every_method_appears_in_the_breakdown(self):
        totals = plan_totals([])
        self.assertEqual(set(totals["per_method"]), set(METHODS))

    def test_malformed_entry_rejected(self):
        with self.assertRaises(ValueError):
            plan_totals([{"method": "tape-lift"}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "campaign_days": 180.0,
            "zones": [
                {
                    "zone_id": "ISO7-INTEGRATION",
                    "area_m2": 144.0,
                    "iso_class": 7,
                    "methods": ["airborne-count", "surface-fallout"],
                    "criticality": "elevated",
                },
                {
                    "zone_id": "ISO5-OPTICS",
                    "area_m2": 36.0,
                    "iso_class": 5,
                    "methods": ["airborne-count", "surface-fallout", "tape-lift"],
                    "criticality": "critical",
                },
            ],
        }
        spec.update(overrides)
        return spec

    def test_a_sound_plan_reports_complete(self):
        result = assess_monitoring_plan(self._spec())
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["zone_count"], 2)

    def test_entry_count_is_the_sum_of_the_methods(self):
        result = assess_monitoring_plan(self._spec())
        self.assertEqual(len(result["entries"]), 5)

    def test_duplicate_zone_is_flagged(self):
        spec = self._spec()
        spec["zones"].append(dict(spec["zones"][0]))
        result = assess_monitoring_plan(spec)
        self.assertTrue(any("more than once" in f for f in result["findings"]))

    def test_zone_with_no_method_is_flagged(self):
        spec = self._spec()
        spec["zones"][0]["methods"] = []
        result = assess_monitoring_plan(spec)
        self.assertFalse(result["complete"])
        self.assertTrue(any("no monitoring method" in f for f in result["findings"]))

    def test_declared_class_without_air_counting_is_flagged(self):
        spec = self._spec()
        spec["zones"][0]["methods"] = ["surface-fallout"]
        result = assess_monitoring_plan(spec)
        self.assertTrue(any("no airborne counting" in f for f in result["findings"]))

    def test_single_occurrence_method_is_flagged(self):
        spec = self._spec(campaign_days=5.0)
        result = assess_monitoring_plan(spec)
        self.assertTrue(any("a trend needs at least %d" % MIN_OCCURRENCES in f
                            for f in result["findings"]))

    def test_total_samples_match_the_entries(self):
        result = assess_monitoring_plan(self._spec())
        self.assertEqual(
            result["total_samples"], sum(e["samples"] for e in result["entries"])
        )

    def test_longer_campaign_never_reduces_the_sample_count(self):
        short = assess_monitoring_plan(self._spec(campaign_days=90.0))
        long_run = assess_monitoring_plan(self._spec(campaign_days=360.0))
        self.assertGreater(long_run["total_samples"], short["total_samples"])

    def test_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring_plan(self._spec(zones=[]))

    def test_missing_key_rejected(self):
        spec = self._spec()
        del spec["campaign_days"]
        with self.assertRaises(ValueError):
            assess_monitoring_plan(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring_plan(["zones"])

    def test_build_plan_requires_zones(self):
        with self.assertRaises(ValueError):
            build_plan([], 30.0)


if __name__ == "__main__":
    unittest.main()

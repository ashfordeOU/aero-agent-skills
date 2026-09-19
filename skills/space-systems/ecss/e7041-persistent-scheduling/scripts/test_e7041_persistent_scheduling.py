"""Contract tests for the clause 6.22.5 persistent scheduling logic."""

import unittest

from e7041_persistent_scheduling_logic import (
    UNLIMITED_REPEATS,
    load_schedule,
    normalise_activity,
    project_schedule_over_orbits,
    release_count,
    release_orbits,
    residual_schedule,
)


def activity(request_id, first_orbit, angle, persistent, **extra):
    item = {
        "request_id": request_id,
        "first_orbit": first_orbit,
        "angle_degrees": angle,
        "persistent": persistent,
    }
    item.update(extra)
    return item


class ActivityValidationTests(unittest.TestCase):
    def test_persistent_activity_defaults_to_every_orbit(self):
        loaded = normalise_activity(activity("beacon", 4, 90.0, True), 0)
        self.assertEqual(loaded["orbit_interval"], 1)
        self.assertEqual(loaded["repeats"], UNLIMITED_REPEATS)

    def test_one_shot_activity_has_no_repeat_interval(self):
        loaded = normalise_activity(activity("burn", 4, 90.0, False), 0)
        self.assertEqual(loaded["orbit_interval"], 0)
        self.assertEqual(loaded["repeats"], 1)

    def test_non_boolean_persistence_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_activity(activity("beacon", 4, 90.0, "yes"), 0)

    def test_zero_orbit_interval_is_refused_for_a_persistent_activity(self):
        with self.assertRaises(ValueError):
            normalise_activity(activity("beacon", 4, 90.0, True, orbit_interval=0), 0)

    def test_one_shot_activity_declaring_repeats_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_activity(activity("burn", 4, 90.0, False, repeats=5), 0)

    def test_angle_outside_a_revolution_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_activity(activity("beacon", 4, 360.0, True), 0)

    def test_negative_first_orbit_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_activity(activity("beacon", -1, 90.0, True), 0)

    def test_blank_request_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_activity(activity("  ", 4, 90.0, True), 0)

    def test_non_mapping_activity_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_activity(["beacon"], 0)


class ScheduleLoadTests(unittest.TestCase):
    def test_schedule_is_ordered_by_first_orbit_then_angle(self):
        loaded = load_schedule(
            [
                activity("late", 6, 10.0, False),
                activity("early-high", 4, 300.0, False),
                activity("early-low", 4, 20.0, False),
            ]
        )
        self.assertEqual(
            [a["request_id"] for a in loaded], ["early-low", "early-high", "late"]
        )

    def test_duplicate_request_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            load_schedule(
                [activity("beacon", 4, 10.0, True), activity("beacon", 5, 20.0, True)]
            )

    def test_non_sequence_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            load_schedule({"beacon": 1})


class ReleaseTests(unittest.TestCase):
    def test_persistent_activity_releases_every_orbit_of_the_sweep(self):
        loaded = load_schedule([activity("beacon", 4, 90.0, True)])[0]
        self.assertEqual(release_orbits(loaded, 4, 4), (4, 5, 6, 7))

    def test_repeat_interval_thins_the_releases(self):
        loaded = load_schedule(
            [activity("survey", 4, 90.0, True, orbit_interval=3)]
        )[0]
        self.assertEqual(release_orbits(loaded, 4, 7), (4, 7, 10))

    def test_repeat_limit_stops_the_activity(self):
        loaded = load_schedule([activity("survey", 4, 90.0, True, repeats=2)])[0]
        self.assertEqual(release_orbits(loaded, 4, 9), (4, 5))

    def test_one_shot_activity_releases_once(self):
        loaded = load_schedule([activity("burn", 5, 90.0, False)])[0]
        self.assertEqual(release_orbits(loaded, 4, 6), (5,))

    def test_activity_after_the_sweep_never_releases(self):
        loaded = load_schedule([activity("burn", 40, 90.0, False)])[0]
        self.assertEqual(release_orbits(loaded, 4, 6), ())

    def test_release_count_matches_the_orbit_list(self):
        loaded = load_schedule([activity("beacon", 4, 90.0, True)])[0]
        self.assertEqual(release_count(loaded, 4, 5), 5)

    def test_zero_length_sweep_is_refused(self):
        loaded = load_schedule([activity("beacon", 4, 90.0, True)])[0]
        with self.assertRaises(ValueError):
            release_orbits(loaded, 4, 0)


class ResidualTests(unittest.TestCase):
    def test_one_shot_activity_is_consumed_by_its_release(self):
        loaded = load_schedule([activity("burn", 5, 90.0, False)])
        self.assertEqual(residual_schedule(loaded, 4, 6), ())

    def test_unreleased_one_shot_activity_stays_in_the_schedule(self):
        loaded = load_schedule([activity("burn", 40, 90.0, False)])
        self.assertEqual(residual_schedule(loaded, 4, 6), ("burn",))

    def test_unlimited_persistent_activity_never_leaves_the_schedule(self):
        loaded = load_schedule([activity("beacon", 4, 90.0, True)])
        self.assertEqual(residual_schedule(loaded, 4, 99), ("beacon",))

    def test_exhausted_persistent_activity_leaves_the_schedule(self):
        loaded = load_schedule([activity("survey", 4, 90.0, True, repeats=2)])
        self.assertEqual(residual_schedule(loaded, 4, 9), ())


class ProjectionTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "activities": [
                activity("beacon", 4, 90.0, True),
                activity("survey", 4, 200.0, True, orbit_interval=2, repeats=3),
                activity("burn", 6, 30.0, False),
            ],
            "start_orbit": 4,
            "orbit_count": 6,
        }
        spec.update(overrides)
        return spec

    def test_persistent_and_one_shot_activities_are_separated(self):
        result = project_schedule_over_orbits(self._spec())
        self.assertEqual(result["persistent_activities"], ("beacon", "survey"))
        self.assertEqual(result["one_shot_activities"], ("burn",))

    def test_each_activity_reports_its_release_orbits(self):
        result = project_schedule_over_orbits(self._spec())
        self.assertEqual(result["releases"]["beacon"], (4, 5, 6, 7, 8, 9))
        self.assertEqual(result["releases"]["survey"], (4, 6, 8))
        self.assertEqual(result["releases"]["burn"], (6,))

    def test_total_releases_are_summed(self):
        result = project_schedule_over_orbits(self._spec())
        self.assertEqual(result["total_releases"], 10)

    def test_residual_schedule_holds_only_the_unlimited_activity(self):
        result = project_schedule_over_orbits(self._spec())
        self.assertEqual(result["residual_schedule"], ("beacon",))
        self.assertEqual(result["residual_occupancy"], 1)
        self.assertFalse(result["schedule_drains"])

    def test_a_one_shot_only_schedule_drains(self):
        spec = self._spec(activities=[activity("burn", 6, 30.0, False)])
        result = project_schedule_over_orbits(spec)
        self.assertTrue(result["schedule_drains"])

    def test_activity_outside_the_sweep_is_flagged(self):
        spec = self._spec(
            activities=[activity("late-burn", 90, 30.0, False)], orbit_count=3
        )
        result = project_schedule_over_orbits(spec)
        self.assertTrue(any("never releases" in f for f in result["findings"]))

    def test_repeat_interval_longer_than_the_sweep_is_flagged(self):
        spec = self._spec(
            activities=[activity("annual", 4, 30.0, True, orbit_interval=50)],
            orbit_count=6,
        )
        result = project_schedule_over_orbits(spec)
        self.assertTrue(any("longer than" in f for f in result["findings"]))

    def test_last_orbit_of_the_sweep_is_reported(self):
        result = project_schedule_over_orbits(self._spec())
        self.assertEqual(result["last_orbit"], 9)

    def test_empty_schedule_is_refused(self):
        with self.assertRaises(ValueError):
            project_schedule_over_orbits(self._spec(activities=[]))

    def test_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["orbit_count"]
        with self.assertRaises(ValueError):
            project_schedule_over_orbits(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            project_schedule_over_orbits(["activities"])


if __name__ == "__main__":
    unittest.main()

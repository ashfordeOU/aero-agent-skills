"""Contract tests for the clause 6.22.7.1 position-based sub-schedule model."""

import unittest

from e7041_position_based_sub_schedules_logic import (
    DEFAULT_SUB_SCHEDULE,
    FULL_REVOLUTION_DEG,
    assess_sub_schedule_model,
    forward_arc_deg,
    membership_findings,
    next_release,
    normalize_position_deg,
    partition_by_sub_schedule,
    release_permitted,
    resolve_capability,
    resolve_sub_schedule,
    validate_activity,
)

SUPPORTED = {"supported": True, "sub_schedules": {"routine": True, "eclipse": False}}
UNSUPPORTED = {"supported": False}


def activity(activity_id="a1", sub_schedule="routine", position=45.0):
    record = {"activity_id": activity_id, "release_position_deg": position}
    if sub_schedule is not None:
        record["sub_schedule"] = sub_schedule
    return record


class CapabilityTests(unittest.TestCase):
    def test_supported_capability_is_canonicalized(self):
        resolved = resolve_capability(SUPPORTED)
        self.assertTrue(resolved["supported"])
        self.assertEqual(sorted(resolved["sub_schedules"]), ["eclipse", "routine"])

    def test_unsupported_capability_yields_one_default(self):
        resolved = resolve_capability(UNSUPPORTED)
        self.assertEqual(list(resolved["sub_schedules"]), [DEFAULT_SUB_SCHEDULE])

    def test_resolving_a_resolved_capability_is_stable(self):
        once = resolve_capability(UNSUPPORTED)
        self.assertEqual(resolve_capability(once), once)

    def test_supported_capability_without_declarations_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capability({"supported": True, "sub_schedules": {}})

    def test_unsupported_capability_declaring_names_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capability({"supported": False, "sub_schedules": {"routine": True}})

    def test_missing_supported_flag_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capability({"sub_schedules": {"routine": True}})

    def test_non_boolean_enabled_flag_rejected(self):
        with self.assertRaises(ValueError):
            resolve_capability({"supported": True, "sub_schedules": {"routine": "yes"}})


class MembershipTests(unittest.TestCase):
    def test_declared_sub_schedule_resolves_to_itself(self):
        self.assertEqual(resolve_sub_schedule(activity(), SUPPORTED), "routine")

    def test_undeclared_sub_schedule_rejected(self):
        with self.assertRaises(ValueError):
            resolve_sub_schedule(activity(sub_schedule="ghost"), SUPPORTED)

    def test_activity_without_a_sub_schedule_rejected_when_supported(self):
        with self.assertRaises(ValueError):
            resolve_sub_schedule(activity(sub_schedule=None), SUPPORTED)

    def test_activity_without_a_sub_schedule_falls_to_default(self):
        self.assertEqual(
            resolve_sub_schedule(activity(sub_schedule=None), UNSUPPORTED),
            DEFAULT_SUB_SCHEDULE,
        )

    def test_named_sub_schedule_rejected_when_unsupported(self):
        with self.assertRaises(ValueError):
            resolve_sub_schedule(activity(sub_schedule="routine"), UNSUPPORTED)

    def test_explicit_default_accepted_when_unsupported(self):
        self.assertEqual(
            resolve_sub_schedule(activity(sub_schedule=DEFAULT_SUB_SCHEDULE), UNSUPPORTED),
            DEFAULT_SUB_SCHEDULE,
        )

    def test_activity_is_normalized_with_its_home(self):
        record = validate_activity(activity(position=-15.0), SUPPORTED)
        self.assertAlmostEqual(record["release_position_deg"], 345.0, places=9)
        self.assertEqual(record["sub_schedule"], "routine")

    def test_activity_missing_position_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"activity_id": "a1", "sub_schedule": "routine"}, SUPPORTED)


class PartitionTests(unittest.TestCase):
    def test_every_declared_sub_schedule_appears(self):
        partition = partition_by_sub_schedule([activity()], SUPPORTED)
        self.assertEqual(sorted(partition), ["eclipse", "routine"])
        self.assertEqual(partition["eclipse"], [])

    def test_activities_land_in_exactly_one_sub_schedule(self):
        partition = partition_by_sub_schedule(
            [activity("a1"), activity("a2", "eclipse"), activity("a3")], SUPPORTED
        )
        self.assertEqual(partition["routine"], ["a1", "a3"])
        self.assertEqual(partition["eclipse"], ["a2"])

    def test_duplicate_activity_id_rejected(self):
        with self.assertRaises(ValueError):
            partition_by_sub_schedule([activity("a1"), activity("a1", "eclipse")], SUPPORTED)

    def test_unsupported_service_collects_everything_in_the_default(self):
        partition = partition_by_sub_schedule(
            [activity("a1", None), activity("a2", None)], UNSUPPORTED
        )
        self.assertEqual(partition[DEFAULT_SUB_SCHEDULE], ["a1", "a2"])

    def test_non_sequence_activities_rejected(self):
        with self.assertRaises(ValueError):
            partition_by_sub_schedule({"a1": 1}, SUPPORTED)


class MembershipFindingTests(unittest.TestCase):
    def test_empty_declared_sub_schedule_is_reported(self):
        findings = membership_findings([activity()], SUPPORTED)
        self.assertTrue(any("holds no activity" in note for note in findings))

    def test_fully_loaded_partition_has_no_findings(self):
        findings = membership_findings([activity("a1"), activity("a2", "eclipse")], SUPPORTED)
        self.assertEqual(findings, [])

    def test_same_activity_in_two_sub_schedules_is_reported(self):
        findings = membership_findings(
            [activity("a1"), activity("a1", "eclipse")], SUPPORTED
        )
        self.assertTrue(any("membership is exclusive" in note for note in findings))

    def test_undeclared_home_is_reported_not_raised(self):
        findings = membership_findings(
            [activity("a1"), activity("a2", "ghost"), activity("a3", "eclipse")], SUPPORTED
        )
        self.assertTrue(any("undeclared sub-schedule" in note for note in findings))


class ReleaseGatingTests(unittest.TestCase):
    def test_enabled_schedule_and_sub_schedule_permits_release(self):
        self.assertTrue(release_permitted(True, "routine", SUPPORTED))

    def test_disabled_sub_schedule_blocks_release(self):
        self.assertFalse(release_permitted(True, "eclipse", SUPPORTED))

    def test_disabled_schedule_blocks_an_enabled_sub_schedule(self):
        self.assertFalse(release_permitted(False, "routine", SUPPORTED))

    def test_undeclared_sub_schedule_rejected_in_gating(self):
        with self.assertRaises(ValueError):
            release_permitted(True, "ghost", SUPPORTED)

    def test_non_boolean_schedule_state_rejected(self):
        with self.assertRaises(ValueError):
            release_permitted("on", "routine", SUPPORTED)


class NextReleaseTests(unittest.TestCase):
    def test_nearest_position_ahead_wins(self):
        result = next_release(
            [activity("a1", "routine", 100.0), activity("a2", "routine", 40.0)],
            SUPPORTED, 10.0,
        )
        self.assertEqual(result["activity_id"], "a2")

    def test_search_wraps_past_the_revolution_boundary(self):
        result = next_release(
            [activity("a1", "routine", 5.0), activity("a2", "routine", 300.0)],
            SUPPORTED, 350.0,
        )
        self.assertEqual(result["activity_id"], "a1")

    def test_activity_in_a_disabled_sub_schedule_is_skipped(self):
        result = next_release(
            [activity("a1", "eclipse", 20.0), activity("a2", "routine", 200.0)],
            SUPPORTED, 10.0,
        )
        self.assertEqual(result["activity_id"], "a2")

    def test_nothing_releases_while_the_schedule_is_disabled(self):
        self.assertIsNone(
            next_release([activity("a1", "routine", 20.0)], SUPPORTED, 10.0, False)
        )

    def test_arc_ahead_is_measured_forward(self):
        result = next_release([activity("a1", "routine", 20.0)], SUPPORTED, 350.0)
        self.assertAlmostEqual(result["arc_ahead_deg"], 30.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_activity_total_counts_the_partition(self):
        result = assess_sub_schedule_model(
            {"capability": SUPPORTED,
             "activities": [activity("a1"), activity("a2", "eclipse")]}
        )
        self.assertEqual(result["activity_total"], 2)

    def test_blocked_sub_schedule_is_reported(self):
        result = assess_sub_schedule_model(
            {"capability": SUPPORTED,
             "activities": [activity("a1"), activity("a2", "eclipse")]}
        )
        self.assertEqual(result["blocked_sub_schedules"], ["eclipse"])
        self.assertTrue(any("cannot be released" in note for note in result["findings"]))

    def test_disabled_schedule_blocks_every_loaded_sub_schedule(self):
        result = assess_sub_schedule_model(
            {"capability": SUPPORTED, "schedule_enabled": False,
             "activities": [activity("a1"), activity("a2", "eclipse")]}
        )
        self.assertEqual(result["blocked_sub_schedules"], ["eclipse", "routine"])

    def test_next_release_reported_when_a_position_is_given(self):
        result = assess_sub_schedule_model(
            {"capability": SUPPORTED, "activities": [activity("a1", "routine", 30.0)],
             "current_position_deg": 10.0}
        )
        self.assertEqual(result["next_release"]["activity_id"], "a1")

    def test_next_release_omitted_without_a_position(self):
        result = assess_sub_schedule_model(
            {"capability": SUPPORTED, "activities": [activity("a1")]}
        )
        self.assertIsNone(result["next_release"])

    def test_unsupported_service_reports_one_sub_schedule(self):
        result = assess_sub_schedule_model(
            {"capability": UNSUPPORTED, "activities": [activity("a1", None)]}
        )
        self.assertFalse(result["supported"])
        self.assertEqual(list(result["sub_schedules"]), [DEFAULT_SUB_SCHEDULE])

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_sub_schedule_model({"capability": SUPPORTED})

    def test_position_wrapping_is_consistent_with_the_arc(self):
        self.assertAlmostEqual(
            forward_arc_deg(0.0, normalize_position_deg(FULL_REVOLUTION_DEG + 45.0)),
            45.0, places=9,
        )


if __name__ == "__main__":
    unittest.main()

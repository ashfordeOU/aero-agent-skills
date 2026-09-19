"""Contract tests for the clause 6.22.8.1 position-based scheduling-group model."""

import unittest

from e7041_position_based_scheduling_groups_logic import (
    FULL_REVOLUTION_DEG,
    UNGROUPED,
    assess_group_model,
    blocking_gates,
    cross_partition,
    forward_arc_deg,
    group_census,
    normalize_position_deg,
    release_permitted,
    releasable_in_order,
    resolve_group,
    resolve_group_capability,
    spanning_groups,
    validate_activity,
)

CAPABILITY = {"supported": True, "groups": {"payload": True, "comms": False, "spare": True}}
NO_GROUPS = {"supported": False}
SUBS = {"routine": True, "eclipse": False}


def activity(activity_id="a1", sub_schedule="routine", group="payload", position=45.0):
    return {"activity_id": activity_id, "sub_schedule": sub_schedule,
            "group": group, "release_position_deg": position}


def population():
    return [
        activity("a1", "routine", "payload", 30.0),
        activity("a2", "eclipse", "payload", 90.0),
        activity("a3", "routine", "comms", 150.0),
        activity("a4", "routine", None, 300.0),
        activity("a5", "eclipse", "comms", 210.0),
    ]


class CapabilityTests(unittest.TestCase):
    def test_supported_capability_is_canonicalized(self):
        resolved = resolve_group_capability(CAPABILITY)
        self.assertTrue(resolved["supported"])
        self.assertEqual(sorted(resolved["groups"]), ["comms", "payload", "spare"])

    def test_unsupported_capability_declares_no_groups(self):
        self.assertEqual(resolve_group_capability(NO_GROUPS)["groups"], {})

    def test_resolving_a_resolved_capability_is_stable(self):
        once = resolve_group_capability(CAPABILITY)
        self.assertEqual(resolve_group_capability(once), once)

    def test_supported_capability_without_groups_rejected(self):
        with self.assertRaises(ValueError):
            resolve_group_capability({"supported": True, "groups": {}})

    def test_unsupported_capability_declaring_groups_rejected(self):
        with self.assertRaises(ValueError):
            resolve_group_capability({"supported": False, "groups": {"payload": True}})

    def test_non_boolean_group_flag_rejected(self):
        with self.assertRaises(ValueError):
            resolve_group_capability({"supported": True, "groups": {"payload": "on"}})


class MembershipTests(unittest.TestCase):
    def test_declared_group_resolves_to_itself(self):
        self.assertEqual(resolve_group(activity(), CAPABILITY), "payload")

    def test_ungrouped_activity_resolves_to_none(self):
        self.assertIsNone(resolve_group(activity(group=None), CAPABILITY))

    def test_undeclared_group_rejected(self):
        with self.assertRaises(ValueError):
            resolve_group(activity(group="ghost"), CAPABILITY)

    def test_group_named_without_support_rejected(self):
        with self.assertRaises(ValueError):
            resolve_group(activity(), NO_GROUPS)

    def test_ungrouped_activity_is_fine_without_support(self):
        self.assertIsNone(resolve_group(activity(group=None), NO_GROUPS))

    def test_activity_is_normalized_with_both_homes(self):
        record = validate_activity(activity(position=-30.0), CAPABILITY, SUBS)
        self.assertAlmostEqual(record["release_position_deg"], 330.0, places=9)
        self.assertEqual(record["sub_schedule"], "routine")
        self.assertEqual(record["group"], "payload")

    def test_undeclared_sub_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(activity(sub_schedule="ghost"), CAPABILITY, SUBS)

    def test_activity_missing_position_rejected(self):
        bad = activity()
        del bad["release_position_deg"]
        with self.assertRaises(ValueError):
            validate_activity(bad, CAPABILITY, SUBS)


class PartitionTests(unittest.TestCase):
    def test_census_covers_every_declared_group(self):
        census = group_census(population(), CAPABILITY, SUBS)
        self.assertEqual(census["spare"], [])
        self.assertEqual(census["payload"], ["a1", "a2"])

    def test_census_collects_the_ungrouped_remainder(self):
        self.assertEqual(group_census(population(), CAPABILITY, SUBS)[UNGROUPED], ["a4"])

    def test_duplicate_activity_id_rejected(self):
        with self.assertRaises(ValueError):
            group_census(population() + [activity("a1")], CAPABILITY, SUBS)

    def test_cross_partition_keeps_the_two_partitions_independent(self):
        matrix = cross_partition(population(), CAPABILITY, SUBS)
        self.assertEqual(matrix[("routine", "payload")], ["a1"])
        self.assertEqual(matrix[("eclipse", "payload")], ["a2"])

    def test_cross_partition_keys_the_ungrouped_bucket(self):
        matrix = cross_partition(population(), CAPABILITY, SUBS)
        self.assertEqual(matrix[("routine", UNGROUPED)], ["a4"])

    def test_group_spanning_sub_schedules_is_detected(self):
        self.assertEqual(spanning_groups(population(), CAPABILITY, SUBS)["payload"],
                         ["eclipse", "routine"])

    def test_group_inside_one_sub_schedule_is_not_spanning(self):
        single = [activity("a1", "routine", "comms", 10.0),
                  activity("a2", "routine", "comms", 20.0)]
        self.assertEqual(spanning_groups(single, CAPABILITY, SUBS), {})


class GateTests(unittest.TestCase):
    def test_all_three_gates_open_permits_release(self):
        self.assertTrue(release_permitted(True, True, True))

    def test_shut_group_blocks_release(self):
        self.assertFalse(release_permitted(True, True, False))

    def test_shut_sub_schedule_blocks_release(self):
        self.assertFalse(release_permitted(True, False, True))

    def test_shut_schedule_blocks_release(self):
        self.assertFalse(release_permitted(False, True, True))

    def test_non_boolean_gate_rejected(self):
        with self.assertRaises(ValueError):
            release_permitted(True, "yes", True)

    def test_blocking_gates_names_the_group(self):
        record = validate_activity(activity("a3", "routine", "comms"), CAPABILITY, SUBS)
        self.assertEqual(blocking_gates(record, True, SUBS, CAPABILITY["groups"]), ["group"])

    def test_blocking_gates_names_both_shut_gates(self):
        record = validate_activity(activity("a2", "eclipse", "comms"), CAPABILITY, SUBS)
        self.assertEqual(blocking_gates(record, True, SUBS, CAPABILITY["groups"]),
                         ["sub-schedule", "group"])

    def test_blocking_gates_is_empty_when_all_open(self):
        record = validate_activity(activity("a1", "routine", "payload"), CAPABILITY, SUBS)
        self.assertEqual(blocking_gates(record, True, SUBS, CAPABILITY["groups"]), [])

    def test_ungrouped_activity_is_not_gated_by_a_group(self):
        record = validate_activity(activity("a4", "routine", None), CAPABILITY, SUBS)
        self.assertEqual(blocking_gates(record, True, SUBS, CAPABILITY["groups"]), [])

    def test_undeclared_sub_schedule_rejected_in_gating(self):
        record = {"activity_id": "a9", "sub_schedule": "ghost", "group": None}
        with self.assertRaises(ValueError):
            blocking_gates(record, True, SUBS, CAPABILITY["groups"])


class OrderTests(unittest.TestCase):
    def test_releasable_order_follows_the_forward_arc(self):
        order = releasable_in_order(population(), CAPABILITY, SUBS, 0.0)
        self.assertEqual(order, ["a1", "a4"])

    def test_releasable_order_wraps_past_the_revolution_boundary(self):
        order = releasable_in_order(population(), CAPABILITY, SUBS, 290.0)
        self.assertEqual(order, ["a4", "a1"])

    def test_nothing_is_releasable_while_the_schedule_is_disabled(self):
        self.assertEqual(
            releasable_in_order(population(), CAPABILITY, SUBS, 0.0, schedule_enabled=False), []
        )

    def test_forward_arc_agrees_with_the_wrapped_position(self):
        self.assertAlmostEqual(
            forward_arc_deg(10.0, normalize_position_deg(FULL_REVOLUTION_DEG + 40.0)),
            30.0, places=9,
        )


class AssessmentTests(unittest.TestCase):
    def base(self, **extra):
        spec = {"capability": CAPABILITY, "sub_schedules": SUBS, "activities": population()}
        spec.update(extra)
        return spec

    def test_empty_declared_group_is_reported(self):
        result = assess_group_model(self.base())
        self.assertTrue(any("holds no activity" in note for note in result["findings"]))

    def test_ungrouped_remainder_is_reported(self):
        result = assess_group_model(self.base())
        self.assertTrue(any("belong to no scheduling group" in note
                            for note in result["findings"]))

    def test_multiply_gated_activity_is_reported(self):
        result = assess_group_model(self.base())
        self.assertTrue(any("held by 2 gates" in note for note in result["findings"]))

    def test_spanning_group_is_reported(self):
        result = assess_group_model(self.base())
        self.assertTrue(any("spans sub-schedules" in note for note in result["findings"]))

    def test_blocked_map_names_the_gate_per_activity(self):
        result = assess_group_model(self.base())
        self.assertEqual(result["blocked"]["a3"], ["group"])

    def test_releasable_order_reported_with_a_position(self):
        result = assess_group_model(self.base(current_position_deg=0.0))
        self.assertEqual(result["releasable_order"], ["a1", "a4"])

    def test_releasable_order_omitted_without_a_position(self):
        self.assertIsNone(assess_group_model(self.base())["releasable_order"])

    def test_service_without_group_support_reports_no_groups(self):
        result = assess_group_model(
            {"capability": NO_GROUPS, "sub_schedules": SUBS,
             "activities": [activity("a1", "routine", None, 10.0)]}
        )
        self.assertFalse(result["supported"])
        self.assertEqual(result["groups"], {})

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_model({"capability": CAPABILITY, "sub_schedules": SUBS})

    def test_empty_sub_schedule_declaration_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_model(self.base(sub_schedules={}))


if __name__ == "__main__":
    unittest.main()

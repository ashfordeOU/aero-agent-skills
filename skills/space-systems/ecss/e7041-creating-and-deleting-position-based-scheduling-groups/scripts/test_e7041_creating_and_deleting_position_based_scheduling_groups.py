"""Contract tests for the clause 6.22.8.2 scheduling-group lifecycle logic."""

import unittest

from e7041_creating_and_deleting_position_based_scheduling_groups_logic import (
    ACTIONS,
    FULL_REVOLUTION_DEG,
    REJECTION_REASONS,
    apply_group_instructions,
    assess_group_lifecycle,
    capacity_remaining,
    cascade_census,
    normalize_position_deg,
    validate_activities,
    validate_instruction,
    validate_registry,
)


def registry(max_groups=4, comms_enabled=False, supported=True):
    return {
        "supported": supported,
        "max_groups": max_groups,
        "groups": {"payload": False, "comms": comms_enabled},
    }


def activities():
    return [
        {"activity_id": "a1", "sub_schedule": "routine", "group": "payload",
         "release_position_deg": 20.0},
        {"activity_id": "a2", "sub_schedule": "eclipse", "group": "payload",
         "release_position_deg": 120.0},
        {"activity_id": "a3", "sub_schedule": "routine", "group": "comms",
         "release_position_deg": 200.0},
        {"activity_id": "a4", "sub_schedule": "routine", "group": None,
         "release_position_deg": 300.0},
    ]


def create(name):
    return {"action": "create", "group": name}


def delete(name):
    return {"action": "delete", "group": name}


class RegistryValidationTests(unittest.TestCase):
    def test_registry_is_returned_validated(self):
        checked = validate_registry(registry())
        self.assertEqual(sorted(checked["groups"]), ["comms", "payload"])
        self.assertEqual(checked["max_groups"], 4)

    def test_registry_without_a_limit_is_allowed(self):
        self.assertIsNone(validate_registry(registry(max_groups=None))["max_groups"])

    def test_registry_over_its_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_registry(registry(max_groups=1))

    def test_negative_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_registry(registry(max_groups=-1))

    def test_unsupported_registry_holding_groups_rejected(self):
        with self.assertRaises(ValueError):
            validate_registry(registry(supported=False))

    def test_non_boolean_group_flag_rejected(self):
        bad = registry()
        bad["groups"]["payload"] = "off"
        with self.assertRaises(ValueError):
            validate_registry(bad)

    def test_missing_supported_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_registry({"groups": {}})


class ActivityValidationTests(unittest.TestCase):
    def test_activities_are_normalized_and_ordered(self):
        records = validate_activities(activities(), registry())
        positions = [rec["release_position_deg"] for rec in records]
        self.assertEqual(positions, sorted(positions))

    def test_position_is_wrapped(self):
        raw = activities()
        raw[0]["release_position_deg"] = -20.0
        records = validate_activities(raw, registry())
        wrapped = [rec for rec in records if rec["activity_id"] == "a1"][0]
        self.assertAlmostEqual(wrapped["release_position_deg"], 340.0, places=9)

    def test_activity_in_an_undeclared_group_rejected(self):
        raw = activities()
        raw[0]["group"] = "ghost"
        with self.assertRaises(ValueError):
            validate_activities(raw, registry())

    def test_duplicate_activity_id_rejected(self):
        raw = activities() + [dict(activities()[0])]
        with self.assertRaises(ValueError):
            validate_activities(raw, registry())

    def test_ungrouped_activity_is_accepted(self):
        records = validate_activities(activities(), registry())
        self.assertIsNone([rec for rec in records if rec["activity_id"] == "a4"][0]["group"])


class InstructionValidationTests(unittest.TestCase):
    def test_action_is_normalized(self):
        self.assertEqual(validate_instruction({"action": " Delete ", "group": "g"})["action"],
                         "delete")

    def test_unknown_action_rejected(self):
        with self.assertRaises(ValueError):
            validate_instruction({"action": "rename", "group": "g"})

    def test_blank_group_rejected(self):
        with self.assertRaises(ValueError):
            validate_instruction({"action": "create", "group": "  "})

    def test_declared_actions_are_exactly_two(self):
        self.assertEqual(set(ACTIONS), {"create", "delete"})


class CapacityAndCensusTests(unittest.TestCase):
    def test_capacity_remaining_counts_the_registry(self):
        self.assertEqual(capacity_remaining(registry()), 2)

    def test_capacity_remaining_is_none_without_a_limit(self):
        self.assertIsNone(capacity_remaining(registry(max_groups=None)))

    def test_cascade_census_breaks_down_by_sub_schedule(self):
        self.assertEqual(cascade_census(activities(), registry(), "payload"),
                         {"routine": 1, "eclipse": 1})

    def test_cascade_census_of_an_empty_group_is_empty(self):
        reg = registry()
        reg["groups"]["spare"] = False
        self.assertEqual(cascade_census(activities(), reg, "spare"), {})


class CreationTests(unittest.TestCase):
    def test_creating_a_new_group_adds_it_disabled(self):
        out = apply_group_instructions(registry(), activities(), [create("spare")])
        self.assertIn("spare", out["registry_after"]["groups"])
        self.assertFalse(out["registry_after"]["groups"]["spare"])

    def test_creating_an_existing_group_rejected(self):
        out = apply_group_instructions(registry(), activities(), [create("payload")])
        self.assertEqual(out["rejected"][0]["reason"], "group-already-exists")

    def test_creation_does_not_touch_the_activities(self):
        out = apply_group_instructions(registry(), activities(), [create("spare")])
        self.assertEqual(len(out["activities_after"]), 4)

    def test_group_limit_is_consumed_across_the_request(self):
        out = apply_group_instructions(
            registry(max_groups=3), activities(), [create("spare"), create("extra")]
        )
        self.assertEqual(len(out["created"]), 1)
        self.assertEqual(out["rejected"][0]["reason"], "group-limit-reached")

    def test_unlimited_registry_accepts_many_creations(self):
        out = apply_group_instructions(
            registry(max_groups=None), activities(), [create("g1"), create("g2"), create("g3")]
        )
        self.assertEqual(len(out["created"]), 3)

    def test_creation_rejected_without_group_support(self):
        out = apply_group_instructions(
            {"supported": False, "groups": {}, "max_groups": None},
            [], [create("spare")]
        )
        self.assertEqual(out["rejected"][0]["reason"], "groups-not-supported")


class DeletionTests(unittest.TestCase):
    def test_deleting_a_disabled_group_removes_it(self):
        out = apply_group_instructions(registry(), activities(), [delete("payload")])
        self.assertNotIn("payload", out["registry_after"]["groups"])

    def test_deleting_an_enabled_group_rejected(self):
        out = apply_group_instructions(
            registry(comms_enabled=True), activities(), [delete("comms")]
        )
        self.assertEqual(out["rejected"][0]["reason"], "group-enabled")
        self.assertIn("comms", out["registry_after"]["groups"])

    def test_deleting_an_unknown_group_rejected(self):
        out = apply_group_instructions(registry(), activities(), [delete("ghost")])
        self.assertEqual(out["rejected"][0]["reason"], "unknown-group")

    def test_deletion_takes_the_group_activities_with_it(self):
        out = apply_group_instructions(registry(), activities(), [delete("payload")])
        self.assertEqual(out["deleted"][0]["activities_discarded"], 2)
        self.assertEqual([rec["activity_id"] for rec in out["activities_after"]],
                         ["a3", "a4"])

    def test_deletion_leaves_ungrouped_activities_alone(self):
        out = apply_group_instructions(registry(), activities(), [delete("payload")])
        self.assertIn("a4", [rec["activity_id"] for rec in out["activities_after"]])

    def test_deletion_returns_capacity_to_the_registry(self):
        out = apply_group_instructions(registry(max_groups=2), activities(),
                                       [delete("payload"), create("spare")])
        self.assertEqual(len(out["created"]), 1)
        self.assertEqual(out["rejected"], [])

    def test_create_then_delete_in_one_request_leaves_no_group(self):
        out = apply_group_instructions(registry(), activities(),
                                       [create("spare"), delete("spare")])
        self.assertNotIn("spare", out["registry_after"]["groups"])
        self.assertEqual(len(out["deleted"]), 1)


class RequestHandlingTests(unittest.TestCase):
    def test_one_bad_instruction_does_not_withdraw_the_others(self):
        out = apply_group_instructions(
            registry(), activities(), [delete("ghost"), create("spare")]
        )
        self.assertEqual(len(out["created"]), 1)
        self.assertEqual(len(out["rejected"]), 1)

    def test_malformed_instruction_is_rejected_on_its_own(self):
        out = apply_group_instructions(
            registry(), activities(), [{"action": "rename", "group": "payload"}, create("spare")]
        )
        self.assertEqual(out["rejected"][0]["reason"], "malformed-instruction")
        self.assertEqual(len(out["created"]), 1)

    def test_rejection_carries_the_instruction_index(self):
        out = apply_group_instructions(
            registry(), activities(), [create("spare"), delete("ghost")]
        )
        self.assertEqual(out["rejected"][0]["index"], 1)

    def test_every_rejection_reason_is_declared(self):
        out = apply_group_instructions(
            registry(comms_enabled=True), activities(),
            [create("payload"), delete("ghost"), delete("comms")]
        )
        for entry in out["rejected"]:
            self.assertIn(entry["reason"], REJECTION_REASONS)

    def test_empty_request_rejected(self):
        with self.assertRaises(ValueError):
            apply_group_instructions(registry(), activities(), [])

    def test_input_registry_is_not_mutated(self):
        reg = registry()
        apply_group_instructions(reg, activities(), [delete("payload")])
        self.assertIn("payload", reg["groups"])


class AssessmentTests(unittest.TestCase):
    def base(self, **extra):
        spec = {"registry": registry(), "activities": activities(),
                "instructions": [create("spare")]}
        spec.update(extra)
        return spec

    def test_creation_is_reported_as_empty_and_disabled(self):
        result = assess_group_lifecycle(self.base())
        self.assertTrue(any("created empty and disabled" in note
                            for note in result["findings"]))

    def test_cascade_discard_is_reported_with_its_sub_schedules(self):
        result = assess_group_lifecycle(self.base(instructions=[delete("payload")]))
        self.assertTrue(any("discarded 2 activity(ies) from 2 sub-schedule(s)" in note
                            for note in result["findings"]))

    def test_census_is_taken_before_the_deletion(self):
        result = assess_group_lifecycle(self.base(instructions=[delete("payload")]))
        self.assertEqual(result["cascade_census_before"]["payload"],
                         {"routine": 1, "eclipse": 1})

    def test_activity_counts_bracket_the_request(self):
        result = assess_group_lifecycle(self.base(instructions=[delete("payload")]))
        self.assertEqual(result["activities_before"], 4)
        self.assertEqual(result["activities_after"], 2)
        self.assertEqual(sorted(result["discarded"]), ["a1", "a2"])

    def test_rejected_instruction_is_reported_as_partial(self):
        result = assess_group_lifecycle(
            self.base(instructions=[delete("ghost"), create("spare")])
        )
        self.assertTrue(any("rest of the request" in note for note in result["findings"]))

    def test_reaching_the_group_limit_is_reported(self):
        result = assess_group_lifecycle(
            self.base(registry=registry(max_groups=3), instructions=[create("spare")])
        )
        self.assertEqual(result["capacity_remaining"], 0)
        self.assertTrue(any("group limit is reached" in note for note in result["findings"]))

    def test_unsupported_service_reports_every_instruction_rejected(self):
        result = assess_group_lifecycle(
            {"registry": {"supported": False, "groups": {}, "max_groups": None},
             "activities": [], "instructions": [create("spare")]}
        )
        self.assertTrue(any("no scheduling-group support" in note
                            for note in result["findings"]))

    def test_missing_spec_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_group_lifecycle({"registry": registry(), "activities": activities()})

    def test_position_wrapping_is_shared_with_the_schedule_model(self):
        self.assertAlmostEqual(normalize_position_deg(FULL_REVOLUTION_DEG + 12.0), 12.0,
                               places=9)


if __name__ == "__main__":
    unittest.main()

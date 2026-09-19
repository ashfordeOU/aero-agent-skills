"""Contract tests for the clause 6.22.8.3 scheduling enable and disable logic."""

import unittest

from e7041_enabling_and_disabling_position_based_scheduling_logic import (
    GROUP_ACTIONS,
    MAX_GROUP_CAPACITY,
    activity_release_gate,
    apply_group_command,
    assess_scheduling_control,
    build_control_state,
    partition_activities,
    set_service_enabled,
    validate_group_id,
)


class GroupIdentifierTests(unittest.TestCase):
    def test_first_group_identifier_is_one(self):
        self.assertEqual(validate_group_id(1, 8), 1)

    def test_identifier_at_the_capacity_is_accepted(self):
        self.assertEqual(validate_group_id(8, 8), 8)

    def test_zero_addresses_no_group_and_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group_id(0, 8)

    def test_identifier_past_the_capacity_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group_id(9, 8)

    def test_boolean_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group_id(True, 8)

    def test_capacity_beyond_the_model_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_group_id(1, MAX_GROUP_CAPACITY + 1)


class ControlStateTests(unittest.TestCase):
    def test_declared_groups_start_disabled(self):
        state = build_control_state([1, 2, 3])
        self.assertEqual(state["groups"], {1: False, 2: False, 3: False})

    def test_service_gate_defaults_closed(self):
        self.assertFalse(build_control_state([1])["service_enabled"])

    def test_preset_enabled_groups_are_honoured(self):
        state = build_control_state([1, 2], enabled_groups=[2])
        self.assertTrue(state["groups"][2])
        self.assertFalse(state["groups"][1])

    def test_duplicate_group_declaration_is_refused(self):
        with self.assertRaises(ValueError):
            build_control_state([1, 1])

    def test_preset_enable_of_an_undeclared_group_is_refused(self):
        with self.assertRaises(ValueError):
            build_control_state([1], enabled_groups=[4])

    def test_groups_without_the_group_capability_are_refused(self):
        with self.assertRaises(ValueError):
            build_control_state([1], group_capability=False)

    def test_non_boolean_service_flag_is_refused(self):
        with self.assertRaises(ValueError):
            build_control_state([1], service_enabled=1)


class ServiceGateTests(unittest.TestCase):
    def test_opening_a_closed_service_gate_moves_it(self):
        state, moved = set_service_enabled(build_control_state([1]), True)
        self.assertTrue(state["service_enabled"])
        self.assertEqual(moved, 1)

    def test_reopening_an_open_service_gate_moves_nothing(self):
        state, _ = set_service_enabled(build_control_state([1]), True)
        state, moved = set_service_enabled(state, True)
        self.assertEqual(moved, 0)

    def test_setting_the_service_gate_leaves_the_source_state_alone(self):
        original = build_control_state([1])
        set_service_enabled(original, True)
        self.assertFalse(original["service_enabled"])

    def test_non_boolean_service_target_is_refused(self):
        with self.assertRaises(ValueError):
            set_service_enabled(build_control_state([1]), "on")


class GroupCommandTests(unittest.TestCase):
    def setUp(self):
        self.state = build_control_state([1, 2, 3])

    def test_enable_opens_the_named_group_gates(self):
        state, report = apply_group_command(self.state, "enable", [1, 3])
        self.assertTrue(state["groups"][1])
        self.assertTrue(state["groups"][3])
        self.assertFalse(state["groups"][2])
        self.assertEqual(report["gates_moved"], 2)

    def test_disable_closes_an_open_group_gate(self):
        state, _ = apply_group_command(self.state, "enable", [2])
        state, report = apply_group_command(state, "disable", [2])
        self.assertFalse(state["groups"][2])
        self.assertEqual(report["gates_moved"], 1)

    def test_repeating_an_enable_is_idempotent(self):
        state, _ = apply_group_command(self.state, "enable", [1])
        _, report = apply_group_command(state, "enable", [1])
        self.assertEqual(report["gates_moved"], 0)
        self.assertTrue(report["fully_accepted"])

    def test_duplicate_identifiers_in_one_command_collapse(self):
        _, report = apply_group_command(self.state, "enable", [2, 2, 2])
        self.assertEqual(report["accepted"], (2,))
        self.assertEqual(report["gates_moved"], 1)

    def test_undeclared_group_is_rejected_without_stopping_the_rest(self):
        state, report = apply_group_command(self.state, "enable", [1, 7])
        self.assertTrue(state["groups"][1])
        self.assertEqual(report["accepted"], (1,))
        self.assertEqual(len(report["rejected"]), 1)
        self.assertFalse(report["fully_accepted"])

    def test_empty_identifier_set_is_refused(self):
        with self.assertRaises(ValueError):
            apply_group_command(self.state, "enable", [])

    def test_unknown_action_is_refused(self):
        with self.assertRaises(ValueError):
            apply_group_command(self.state, "suspend", [1])

    def test_group_command_without_the_group_capability_is_refused(self):
        flat = build_control_state([], group_capability=False)
        with self.assertRaises(ValueError):
            apply_group_command(flat, "enable", [1])

    def test_the_two_actions_are_the_only_ones_offered(self):
        self.assertEqual(GROUP_ACTIONS, ("enable", "disable"))


class ReleaseGateTests(unittest.TestCase):
    def test_both_gates_open_releases_the_activity(self):
        state = build_control_state([1], service_enabled=True, enabled_groups=[1])
        self.assertTrue(activity_release_gate(state, 1)["releasable"])

    def test_closed_service_gate_holds_an_enabled_group(self):
        state = build_control_state([1], enabled_groups=[1])
        gate = activity_release_gate(state, 1)
        self.assertFalse(gate["releasable"])
        self.assertTrue(gate["group_gate"])

    def test_closed_group_gate_holds_an_enabled_service(self):
        state = build_control_state([1], service_enabled=True)
        gate = activity_release_gate(state, 1)
        self.assertFalse(gate["releasable"])
        self.assertTrue(gate["service_gate"])

    def test_ungrouped_subservice_needs_only_the_service_gate(self):
        state = build_control_state([], service_enabled=True, group_capability=False)
        self.assertTrue(activity_release_gate(state)["releasable"])

    def test_group_on_an_ungrouped_subservice_is_refused(self):
        state = build_control_state([], group_capability=False)
        with self.assertRaises(ValueError):
            activity_release_gate(state, 1)

    def test_missing_group_on_a_grouped_subservice_is_refused(self):
        state = build_control_state([1], service_enabled=True)
        with self.assertRaises(ValueError):
            activity_release_gate(state, None)


class PartitionTests(unittest.TestCase):
    def test_activities_split_across_the_two_hold_reasons(self):
        state = build_control_state([1, 2], service_enabled=True, enabled_groups=[1])
        parts = partition_activities(
            state,
            [{"id": "a", "group": 1}, {"id": "b", "group": 2}],
        )
        self.assertEqual(parts["released"], ("a",))
        self.assertEqual(parts["held_by_group"], ("b",))
        self.assertEqual(parts["held_by_service"], ())

    def test_closed_service_gate_holds_everything(self):
        state = build_control_state([1], enabled_groups=[1])
        parts = partition_activities(state, [{"id": "a", "group": 1}])
        self.assertEqual(parts["held_by_service"], ("a",))

    def test_activity_without_an_identifier_is_refused(self):
        state = build_control_state([1], service_enabled=True, enabled_groups=[1])
        with self.assertRaises(ValueError):
            partition_activities(state, [{"group": 1}])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "declared_groups": [1, 2, 3],
            "activities": [
                {"id": "a", "group": 1},
                {"id": "b", "group": 2},
                {"id": "c", "group": 3},
            ],
            "commands": [
                {"target": "service", "enable": True},
                {"target": "groups", "action": "enable", "groups": [1, 2]},
            ],
        }
        spec.update(over)
        return spec

    def test_nominal_sequence_releases_the_enabled_groups(self):
        result = assess_scheduling_control(self._spec())
        self.assertEqual(result["released"], ("a", "b"))
        self.assertEqual(result["held_by_group"], ("c",))
        self.assertEqual(result["enabled_group_count"], 2)

    def test_schedule_content_survives_a_disable(self):
        spec = self._spec(
            commands=[
                {"target": "service", "enable": True},
                {"target": "groups", "action": "enable", "groups": [1, 2, 3]},
                {"target": "service", "enable": False},
            ]
        )
        result = assess_scheduling_control(spec)
        self.assertEqual(result["schedule_retained"], 3)
        self.assertEqual(result["released"], ())
        self.assertEqual(len(result["held_by_service"]), 3)

    def test_rejected_group_is_reported_as_a_finding(self):
        spec = self._spec(
            commands=[
                {"target": "service", "enable": True},
                {"target": "groups", "action": "enable", "groups": [1, 9]},
            ]
        )
        result = assess_scheduling_control(spec)
        self.assertFalse(result["clean"])
        self.assertTrue(any("group 9" in f for f in result["findings"]))

    def test_gate_moves_are_counted_across_the_run(self):
        result = assess_scheduling_control(self._spec())
        self.assertEqual(result["gates_moved"], 3)

    def test_unknown_command_target_is_refused(self):
        with self.assertRaises(ValueError):
            assess_scheduling_control(self._spec(commands=[{"target": "orbit"}]))

    def test_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["activities"]
        with self.assertRaises(ValueError):
            assess_scheduling_control(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_scheduling_control(["declared_groups"])


if __name__ == "__main__":
    unittest.main()

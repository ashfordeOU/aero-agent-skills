"""Contract tests for the clause 6.22.6.3 execution function control logic."""

import unittest

from e7041_controlling_the_position_based_schedule_execution_logic import (
    COMMAND_ADVANCE,
    COMMAND_DISABLE,
    COMMAND_ENABLE,
    COMMAND_RESET,
    MISSED_DISCARD,
    MISSED_RELEASE_LATE,
    SUPPORTED_COMMANDS,
    apply_command,
    due_activities,
    initial_state,
    position_degrees,
    run_execution_control,
)


def activity(request_id, orbit, angle):
    return {"request_id": request_id, "orbit_number": orbit, "angle_degrees": angle}


ACTIVITIES = [
    activity("beacon", 20, 45.0),
    activity("burn", 20, 180.0),
    activity("survey", 21, 10.0),
]


class StateTests(unittest.TestCase):
    def test_state_holds_the_activities_in_position_order(self):
        state = initial_state(True, ACTIVITIES, (20, 0.0))
        self.assertEqual(
            [a["request_id"] for a in state["activities"]],
            ["beacon", "burn", "survey"],
        )

    def test_non_boolean_enable_flag_is_refused(self):
        with self.assertRaises(ValueError):
            initial_state("on", ACTIVITIES, (20, 0.0))

    def test_duplicate_request_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            initial_state(
                True, [activity("beacon", 20, 10.0), activity("beacon", 21, 10.0)],
                (20, 0.0),
            )

    def test_angle_outside_a_revolution_is_refused(self):
        with self.assertRaises(ValueError):
            initial_state(True, [activity("beacon", 20, 360.0)], (20, 0.0))

    def test_malformed_position_is_refused(self):
        with self.assertRaises(ValueError):
            initial_state(True, ACTIVITIES, (20,))

    def test_position_folds_into_degrees_flown(self):
        self.assertAlmostEqual(position_degrees((20, 45.0)), 7245.0, places=9)


class DueTests(unittest.TestCase):
    def test_nothing_is_due_before_the_first_activity(self):
        state = initial_state(True, ACTIVITIES, (20, 0.0))
        self.assertEqual(due_activities(state, (20, 10.0)), ())

    def test_an_activity_at_the_current_position_is_due(self):
        state = initial_state(True, ACTIVITIES, (20, 0.0))
        due = due_activities(state, (20, 45.0))
        self.assertEqual([a["request_id"] for a in due], ["beacon"])

    def test_everything_behind_the_position_is_due(self):
        state = initial_state(True, ACTIVITIES, (20, 0.0))
        due = due_activities(state, (21, 90.0))
        self.assertEqual(
            [a["request_id"] for a in due], ["beacon", "burn", "survey"]
        )


class CommandTests(unittest.TestCase):
    def _state(self, enabled=True):
        return initial_state(enabled, ACTIVITIES, (20, 0.0))

    def test_enable_sets_the_function_enabled(self):
        state, effect = apply_command(self._state(False), {"command": COMMAND_ENABLE})
        self.assertTrue(state["enabled"])
        self.assertEqual(effect["note"], "")

    def test_enabling_an_enabled_function_is_noted_and_harmless(self):
        state, effect = apply_command(self._state(True), {"command": COMMAND_ENABLE})
        self.assertTrue(state["enabled"])
        self.assertIn("already enabled", effect["note"])

    def test_disable_sets_the_function_disabled(self):
        state, _ = apply_command(self._state(True), {"command": COMMAND_DISABLE})
        self.assertFalse(state["enabled"])

    def test_reset_empties_the_schedule_without_changing_the_enable_state(self):
        state, effect = apply_command(self._state(True), {"command": COMMAND_RESET})
        self.assertEqual(state["activities"], ())
        self.assertEqual(effect["cleared"], 3)
        self.assertTrue(state["enabled"])

    def test_advance_releases_the_due_activities_when_enabled(self):
        state, effect = apply_command(
            self._state(True), {"command": COMMAND_ADVANCE, "position": (20, 200.0)}
        )
        self.assertEqual(effect["released"], ("beacon", "burn"))
        self.assertEqual(
            [a["request_id"] for a in state["activities"]], ["survey"]
        )

    def test_advance_releases_nothing_when_disabled(self):
        state, effect = apply_command(
            self._state(False), {"command": COMMAND_ADVANCE, "position": (20, 200.0)}
        )
        self.assertEqual(effect["released"], ())
        self.assertEqual(effect["missed"], ("beacon", "burn"))

    def test_discarded_missed_activities_leave_the_schedule(self):
        state, _ = apply_command(
            self._state(False),
            {"command": COMMAND_ADVANCE, "position": (20, 200.0)},
            MISSED_DISCARD,
        )
        self.assertEqual([a["request_id"] for a in state["activities"]], ["survey"])

    def test_late_release_disposition_keeps_missed_activities(self):
        state, _ = apply_command(
            self._state(False),
            {"command": COMMAND_ADVANCE, "position": (20, 200.0)},
            MISSED_RELEASE_LATE,
        )
        self.assertEqual(
            [a["request_id"] for a in state["activities"]],
            ["beacon", "burn", "survey"],
        )

    def test_advancing_backwards_is_refused(self):
        state = initial_state(True, ACTIVITIES, (21, 0.0))
        with self.assertRaises(ValueError):
            apply_command(state, {"command": COMMAND_ADVANCE, "position": (20, 0.0)})

    def test_advance_without_a_position_is_refused(self):
        with self.assertRaises(ValueError):
            apply_command(self._state(True), {"command": COMMAND_ADVANCE})

    def test_unknown_command_is_refused(self):
        with self.assertRaises(ValueError):
            apply_command(self._state(True), {"command": "suspend"})

    def test_unknown_missed_disposition_is_refused(self):
        with self.assertRaises(ValueError):
            apply_command(
                self._state(True), {"command": COMMAND_ENABLE}, "park-it"
            )

    def test_four_control_commands_are_supported(self):
        self.assertEqual(len(SUPPORTED_COMMANDS), 4)
        self.assertIn(COMMAND_RESET, SUPPORTED_COMMANDS)


class RunTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "enabled": False,
            "activities": ACTIVITIES,
            "position": (20, 0.0),
            "commands": [
                {"command": COMMAND_ENABLE},
                {"command": COMMAND_ADVANCE, "position": (20, 200.0)},
                {"command": COMMAND_ADVANCE, "position": (21, 30.0)},
            ],
        }
        spec.update(overrides)
        return spec

    def test_an_enabled_run_releases_everything_in_order(self):
        result = run_execution_control(self._spec())
        self.assertEqual(
            result["released_activities"], ("beacon", "burn", "survey")
        )
        self.assertEqual(result["pending_activities"], ())

    def test_a_run_that_empties_the_schedule_is_flagged(self):
        result = run_execution_control(self._spec())
        self.assertTrue(any("empty schedule" in f for f in result["findings"]))

    def test_activities_passed_while_disabled_are_reported_missed(self):
        spec = self._spec(
            commands=[
                {"command": COMMAND_ADVANCE, "position": (20, 200.0)},
                {"command": COMMAND_ENABLE},
                {"command": COMMAND_ADVANCE, "position": (21, 30.0)},
            ]
        )
        result = run_execution_control(spec)
        self.assertEqual(result["missed_activities"], ("beacon", "burn"))
        self.assertEqual(result["released_activities"], ("survey",))

    def test_missed_activities_raise_a_finding(self):
        spec = self._spec(
            commands=[{"command": COMMAND_ADVANCE, "position": (20, 200.0)}]
        )
        result = run_execution_control(spec)
        self.assertFalse(result["clean_run"])
        self.assertTrue(any("while the execution function was disabled" in f
                            for f in result["findings"]))

    def test_late_release_disposition_adds_its_own_finding(self):
        spec = self._spec(
            missed_disposition=MISSED_RELEASE_LATE,
            commands=[{"command": COMMAND_ADVANCE, "position": (20, 200.0)}],
        )
        result = run_execution_control(spec)
        self.assertTrue(any("out of position" in f for f in result["findings"]))
        self.assertEqual(result["pending_count"], 3)

    def test_reset_in_the_middle_of_a_run_drops_the_later_releases(self):
        spec = self._spec(
            commands=[
                {"command": COMMAND_ENABLE},
                {"command": COMMAND_RESET},
                {"command": COMMAND_ADVANCE, "position": (21, 30.0)},
            ]
        )
        result = run_execution_control(spec)
        self.assertEqual(result["released_activities"], ())
        self.assertEqual(result["pending_count"], 0)

    def test_the_final_position_is_reported(self):
        result = run_execution_control(self._spec())
        self.assertEqual(result["position"], (21, 30.0))

    def test_missing_spec_key_is_refused(self):
        spec = self._spec()
        del spec["commands"]
        with self.assertRaises(ValueError):
            run_execution_control(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            run_execution_control(["commands"])

    def test_non_sequence_command_list_is_refused(self):
        with self.assertRaises(ValueError):
            run_execution_control(self._spec(commands={"command": COMMAND_ENABLE}))


if __name__ == "__main__":
    unittest.main()

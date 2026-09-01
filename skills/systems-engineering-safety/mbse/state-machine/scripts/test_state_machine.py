#!/usr/bin/env python3
"""Gate 3 contract test: SysML state machine behavior modeling.

Exercises scripts/state_machine_logic.py (stdlib unittest, offline).
Contract: fire picks a guard-enabled transition and records the actions;
a false guard blocks the transition; two enabled transitions on one
event raise TransitionConflictError unless one carries priority;
simulate produces the full firing trace; reachable_states finds every
reachable state and unreachable_states its complement; malformed
machines raise MachineError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_machine_logic as sm  # noqa: E402


def door_machine():
    return sm.validate_machine(
        {
            "states": ["Closed", "Open", "Moving", "Failed"],
            "initial": "Closed",
            "transitions": [
                {"from": "Closed", "event": "open_cmd", "guard": "power_ok",
                 "action": ["energize_actuator"], "to": "Moving"},
                {"from": "Moving", "event": "reach_end",
                 "action": ["deenergize_actuator"], "to": "Open"},
                {"from": "Open", "event": "close_cmd", "guard": "power_ok",
                 "to": "Moving"},
                {"from": "Moving", "event": "jam",
                 "action": ["set_fault_flag"], "to": "Failed"},
            ],
        }
    )


class FireTest(unittest.TestCase):
    def test_unguarded_transition_fires_and_records_action(self):
        m = door_machine()
        nxt, actions, fired = sm.fire(m, "Moving", "reach_end", {})
        self.assertTrue(fired)
        self.assertEqual(nxt, "Open")
        self.assertEqual(actions, ["deenergize_actuator"])

    def test_guard_false_blocks_transition(self):
        m = door_machine()
        nxt, actions, fired = sm.fire(m, "Closed", "open_cmd", {"power_ok": False})
        self.assertFalse(fired)
        self.assertEqual(nxt, "Closed")
        self.assertEqual(actions, [])

    def test_guard_true_enables_transition(self):
        m = door_machine()
        nxt, _, fired = sm.fire(m, "Closed", "open_cmd", {"power_ok": True})
        self.assertTrue(fired)
        self.assertEqual(nxt, "Moving")

    def test_unknown_event_leaves_state_unchanged(self):
        m = door_machine()
        nxt, actions, fired = sm.fire(m, "Open", "hover", {})
        self.assertFalse(fired)
        self.assertEqual(nxt, "Open")
        self.assertEqual(actions, [])

    def test_two_enabled_transitions_raise_conflict(self):
        m = sm.validate_machine(
            {
                "states": ["Idle", "Up", "Down"],
                "initial": "Idle",
                "transitions": [
                    {"from": "Idle", "event": "cmd", "guard": "both", "to": "Up"},
                    {"from": "Idle", "event": "cmd", "guard": "both", "to": "Down"},
                ],
            }
        )
        with self.assertRaises(sm.TransitionConflictError):
            sm.fire(m, "Idle", "cmd", {"both": True})

    def test_priority_resolves_conflict(self):
        m = sm.validate_machine(
            {
                "states": ["Idle", "Up", "Down"],
                "initial": "Idle",
                "transitions": [
                    {"from": "Idle", "event": "cmd", "guard": "both", "to": "Up"},
                    {"from": "Idle", "event": "cmd", "guard": "both",
                     "priority": True, "to": "Down"},
                ],
            }
        )
        nxt, _, fired = sm.fire(m, "Idle", "cmd", {"both": True})
        self.assertTrue(fired)
        self.assertEqual(nxt, "Down")


class SimulateTest(unittest.TestCase):
    def test_trace_follows_expected_sequence(self):
        m = door_machine()
        events = ["open_cmd", "reach_end", "close_cmd", "jam"]
        context = {"power_ok": True}
        trace = sm.simulate(m, "Closed", events, context)
        self.assertEqual(trace[0][0], "Closed")
        self.assertEqual(trace[0][3], "Moving")
        self.assertEqual(trace[1][3], "Open")
        self.assertEqual(trace[2][3], "Moving")
        self.assertEqual(trace[3][3], "Failed")
        self.assertEqual(trace[1][2], ["deenergize_actuator"])

    def test_blocked_event_stays_in_state(self):
        m = door_machine()
        trace = sm.simulate(m, "Closed", ["open_cmd"], {"power_ok": False})
        self.assertEqual(trace[0][3], "Closed")


class ReachabilityTest(unittest.TestCase):
    def test_all_states_reachable(self):
        m = door_machine()
        self.assertEqual(
            sm.reachable_states(m, "Closed"),
            {"Closed", "Moving", "Open", "Failed"},
        )
        self.assertEqual(sm.unreachable_states(m, "Closed"), [])

    def test_orphan_state_reported_unreachable(self):
        m = sm.validate_machine(
            {
                "states": ["A", "B", "Orphan"],
                "initial": "A",
                "transitions": [{"from": "A", "event": "go", "to": "B"}],
            }
        )
        self.assertEqual(sm.unreachable_states(m, "A"), ["Orphan"])


class ValidationTest(unittest.TestCase):
    def test_unknown_transition_target_raises(self):
        with self.assertRaises(sm.MachineError):
            sm.validate_machine(
                {
                    "states": ["A"],
                    "initial": "A",
                    "transitions": [{"from": "A", "event": "go", "to": "Ghost"}],
                }
            )

    def test_unknown_initial_state_raises(self):
        with self.assertRaises(sm.MachineError):
            sm.validate_machine(
                {"states": ["A"], "initial": "Ghost", "transitions": []}
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

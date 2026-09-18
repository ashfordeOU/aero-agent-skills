"""Contract tests for the clause 5.2.2.4 effect-on-receipt verification."""

import copy
import unittest

from e5053_effect_on_receipt_logic import (
    apply_sequence,
    assess_effect_on_receipt,
    build_transition_table,
    coverage_gaps,
    determinism_conflicts,
    discard_inconsistencies,
    reachable_states,
    unreachable_states,
    validate_arrival_sets,
    validate_initial_state,
    validate_name_set,
    validate_transition,
    validate_transitions,
)

STATES = ("closed", "open", "draining")
PRIMITIVES = ("T-Connect.indication", "T-Data.indication", "T-Release.indication")

BASE_TRANSITIONS = [
    {
        "state": "closed",
        "primitive": "T-Connect.indication",
        "next_state": "open",
        "action": "accept the association and admit data",
    },
    {
        "state": "open",
        "primitive": "T-Data.indication",
        "next_state": "open",
        "action": "deliver the unit to the local user",
    },
    {
        "state": "open",
        "primitive": "T-Release.indication",
        "next_state": "draining",
        "action": "stop admitting new units and flush the queue",
    },
    {
        "state": "draining",
        "primitive": "T-Data.indication",
        "next_state": "draining",
        "action": "drop the late unit",
        "discard": True,
    },
]

ARRIVALS = {
    "closed": ["T-Connect.indication"],
    "open": ["T-Data.indication", "T-Release.indication"],
    "draining": ["T-Data.indication"],
}


def spec(**overrides):
    base = {
        "states": list(STATES),
        "initial_state": "closed",
        "primitives": list(PRIMITIVES),
        "arrival_sets": copy.deepcopy(ARRIVALS),
        "transitions": copy.deepcopy(BASE_TRANSITIONS),
    }
    base.update(overrides)
    return base


def table(raw=None):
    return build_transition_table(
        validate_transitions(copy.deepcopy(raw or BASE_TRANSITIONS), STATES, PRIMITIVES)
    )


class NameSetTests(unittest.TestCase):
    def test_names_are_stripped(self):
        self.assertEqual(validate_name_set([" open "], "states"), ("open",))

    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError):
            validate_name_set(["open", "open"], "states")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            validate_name_set([], "primitives")

    def test_initial_state_must_be_declared(self):
        with self.assertRaises(ValueError):
            validate_initial_state("limbo", STATES)

    def test_initial_state_returned(self):
        self.assertEqual(validate_initial_state(" closed ", STATES), "closed")


class ArrivalSetTests(unittest.TestCase):
    def test_absent_sets_default_to_the_catalogue(self):
        resolved = validate_arrival_sets(None, STATES, PRIMITIVES)
        self.assertEqual(resolved["open"], PRIMITIVES)

    def test_declared_set_overrides_the_default(self):
        resolved = validate_arrival_sets(ARRIVALS, STATES, PRIMITIVES)
        self.assertEqual(resolved["closed"], ("T-Connect.indication",))

    def test_undeclared_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival_sets({"limbo": ["T-Data.indication"]}, STATES, PRIMITIVES)

    def test_undeclared_primitive_rejected(self):
        with self.assertRaises(ValueError):
            validate_arrival_sets({"open": ["T-Ghost.indication"]}, STATES, PRIMITIVES)

    def test_repeated_primitive_is_collapsed(self):
        resolved = validate_arrival_sets(
            {"open": ["T-Data.indication", "T-Data.indication"]}, STATES, PRIMITIVES
        )
        self.assertEqual(resolved["open"], ("T-Data.indication",))


class TransitionValidationTests(unittest.TestCase):
    def test_valid_transition_normalises(self):
        entry = validate_transition(BASE_TRANSITIONS[0], STATES, PRIMITIVES)
        self.assertEqual(entry["next_state"], "open")
        self.assertFalse(entry["discard"])

    def test_missing_action_rejected(self):
        bad = dict(BASE_TRANSITIONS[0])
        del bad["action"]
        with self.assertRaises(ValueError):
            validate_transition(bad, STATES, PRIMITIVES)

    def test_undeclared_destination_rejected(self):
        bad = dict(BASE_TRANSITIONS[0], next_state="limbo")
        with self.assertRaises(ValueError):
            validate_transition(bad, STATES, PRIMITIVES)

    def test_undeclared_primitive_rejected(self):
        bad = dict(BASE_TRANSITIONS[0], primitive="T-Ghost.indication")
        with self.assertRaises(ValueError):
            validate_transition(bad, STATES, PRIMITIVES)

    def test_non_boolean_discard_rejected(self):
        bad = dict(BASE_TRANSITIONS[0], discard="yes")
        with self.assertRaises(ValueError):
            validate_transition(bad, STATES, PRIMITIVES)

    def test_empty_transition_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_transitions([], STATES, PRIMITIVES)


class TableTests(unittest.TestCase):
    def test_table_is_keyed_on_state_and_primitive(self):
        built = table()
        self.assertIn(("open", "T-Data.indication"), built)
        self.assertEqual(len(built), 4)

    def test_agreeing_duplicate_is_not_a_conflict(self):
        raw = copy.deepcopy(BASE_TRANSITIONS)
        raw.append(copy.deepcopy(BASE_TRANSITIONS[1]))
        self.assertEqual(determinism_conflicts(table(raw)), [])

    def test_disagreeing_entries_are_a_conflict(self):
        raw = copy.deepcopy(BASE_TRANSITIONS)
        raw.append(dict(BASE_TRANSITIONS[1], next_state="draining"))
        conflicts = determinism_conflicts(table(raw))
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["primitive"], "T-Data.indication")

    def test_clean_table_has_no_conflict(self):
        self.assertEqual(determinism_conflicts(table()), [])


class CoverageTests(unittest.TestCase):
    def test_declared_arrivals_are_all_handled(self):
        arrivals = validate_arrival_sets(ARRIVALS, STATES, PRIMITIVES)
        self.assertEqual(coverage_gaps(arrivals, table()), [])

    def test_unhandled_arrival_is_a_gap(self):
        arrivals = validate_arrival_sets(None, STATES, PRIMITIVES)
        gaps = coverage_gaps(arrivals, table())
        self.assertIn(("closed", "T-Data.indication"), gaps)

    def test_discard_leaving_the_state_is_inconsistent(self):
        raw = copy.deepcopy(BASE_TRANSITIONS)
        raw[3] = dict(raw[3], next_state="closed")
        entries = validate_transitions(raw, STATES, PRIMITIVES)
        self.assertEqual(len(discard_inconsistencies(entries)), 1)

    def test_discard_in_place_is_consistent(self):
        entries = validate_transitions(copy.deepcopy(BASE_TRANSITIONS), STATES, PRIMITIVES)
        self.assertEqual(discard_inconsistencies(entries), [])


class ReachabilityTests(unittest.TestCase):
    def test_all_states_reachable_from_the_initial_state(self):
        self.assertEqual(reachable_states("closed", table()), set(STATES))

    def test_orphan_state_is_reported(self):
        raw = copy.deepcopy(BASE_TRANSITIONS[:2])
        self.assertEqual(unreachable_states(STATES, "closed", table(raw)), ("draining",))

    def test_initial_state_is_always_reachable(self):
        self.assertIn("closed", reachable_states("closed", {}))


class ReplayTests(unittest.TestCase):
    def test_sequence_walks_to_the_expected_state(self):
        result = apply_sequence(table(), "closed", ["T-Connect.indication", "T-Release.indication"])
        self.assertEqual(result["final_state"], "draining")
        self.assertEqual(result["steps"], 2)

    def test_trace_records_every_step(self):
        result = apply_sequence(table(), "closed", ["T-Connect.indication"])
        self.assertEqual(result["trace"][0]["from_state"], "closed")
        self.assertEqual(result["trace"][0]["to_state"], "open")

    def test_empty_sequence_stays_in_the_initial_state(self):
        self.assertEqual(apply_sequence(table(), "closed", [])["final_state"], "closed")

    def test_unhandled_primitive_refused(self):
        with self.assertRaises(ValueError):
            apply_sequence(table(), "closed", ["T-Data.indication"])

    def test_ambiguous_key_refused_during_replay(self):
        raw = copy.deepcopy(BASE_TRANSITIONS)
        raw.append(dict(BASE_TRANSITIONS[0], next_state="draining"))
        with self.assertRaises(ValueError):
            apply_sequence(table(raw), "closed", ["T-Connect.indication"])

    def test_non_sequence_replay_rejected(self):
        with self.assertRaises(ValueError):
            apply_sequence(table(), "closed", "T-Data.indication".split(".")[0])


class AssessmentTests(unittest.TestCase):
    def test_clean_specification_is_compliant(self):
        result = assess_effect_on_receipt(spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_counts_are_reported(self):
        result = assess_effect_on_receipt(spec())
        self.assertEqual(result["transition_count"], 4)
        self.assertEqual(result["key_count"], 4)

    def test_missing_handling_is_a_finding(self):
        result = assess_effect_on_receipt(spec(arrival_sets=None))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("declares no handling" in f for f in result["findings"]))

    def test_ambiguous_effect_is_a_finding(self):
        raw = copy.deepcopy(BASE_TRANSITIONS)
        raw.append(dict(BASE_TRANSITIONS[1], next_state="draining"))
        result = assess_effect_on_receipt(spec(transitions=raw))
        self.assertTrue(any("ambiguous" in f for f in result["findings"]))

    def test_moving_discard_is_a_finding(self):
        raw = copy.deepcopy(BASE_TRANSITIONS)
        raw[3] = dict(raw[3], next_state="closed")
        result = assess_effect_on_receipt(spec(transitions=raw))
        self.assertTrue(any("leaves the state unchanged" in f for f in result["findings"]))

    def test_orphan_state_is_a_finding(self):
        raw = copy.deepcopy(BASE_TRANSITIONS[:2])
        arrivals = {"closed": ["T-Connect.indication"], "open": ["T-Data.indication"], "draining": []}
        result = assess_effect_on_receipt(spec(transitions=raw, arrival_sets=arrivals))
        self.assertTrue(any("not reachable" in f for f in result["findings"]))

    def test_replay_is_carried_in_the_result(self):
        result = assess_effect_on_receipt(spec(replay_sequence=["T-Connect.indication"]))
        self.assertEqual(result["replay"]["final_state"], "open")

    def test_no_replay_requested_leaves_it_absent(self):
        self.assertIsNone(assess_effect_on_receipt(spec())["replay"])

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["initial_state"]
        with self.assertRaises(ValueError):
            assess_effect_on_receipt(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_effect_on_receipt(["states"])


if __name__ == "__main__":
    unittest.main()

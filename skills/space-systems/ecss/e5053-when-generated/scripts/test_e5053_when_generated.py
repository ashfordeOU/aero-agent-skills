"""Contract tests for the clause 5.2.2.3 when-generated subclause evaluation."""

import copy
import unittest

from e5053_when_generated_logic import (
    ORIGINATING_EVENT_KINDS,
    assess_when_generated,
    build_generation_map,
    find_nondeterminism,
    guarded_keys,
    normalize_guard,
    terminal_state_violations,
    unreachable_primitives,
    unused_events,
    validate_name_set,
    validate_rule,
    validate_rules,
    validate_terminal_states,
)

STATES = ("closed", "open", "shut-down")
EVENTS = ("send-request", "unit-arrival", "retry-timer-expiry")
PRIMITIVES = ("T-Data.request", "T-Data.indication", "T-Data.confirm")

BASE_RULES = [
    {
        "primitive": "T-Data.request",
        "state": "open",
        "event": "send-request",
        "event_kind": "upper-layer-request",
    },
    {
        "primitive": "T-Data.indication",
        "state": "open",
        "event": "unit-arrival",
        "event_kind": "protocol-data-unit-arrival",
    },
    {
        "primitive": "T-Data.confirm",
        "state": "open",
        "event": "retry-timer-expiry",
        "event_kind": "timer-expiry",
    },
]


def spec(**overrides):
    base = {
        "states": list(STATES),
        "events": list(EVENTS),
        "primitives": list(PRIMITIVES),
        "terminal_states": ["shut-down"],
        "rules": copy.deepcopy(BASE_RULES),
    }
    base.update(overrides)
    return base


class NameSetTests(unittest.TestCase):
    def test_names_are_stripped_and_ordered(self):
        self.assertEqual(validate_name_set([" open ", "closed"], "states"), ("open", "closed"))

    def test_duplicate_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_name_set(["open", "open"], "states")

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_name_set([], "states")

    def test_non_text_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_name_set([3], "states")


class TerminalStateTests(unittest.TestCase):
    def test_absent_terminal_set_is_empty(self):
        self.assertEqual(validate_terminal_states(None, STATES), ())

    def test_terminal_state_must_be_declared(self):
        with self.assertRaises(ValueError):
            validate_terminal_states(["nowhere"], STATES)

    def test_repeat_is_collapsed(self):
        self.assertEqual(validate_terminal_states(["open", "open"], STATES), ("open",))


class GuardTests(unittest.TestCase):
    def test_absent_guard_is_empty_text(self):
        self.assertEqual(normalize_guard(None), "")

    def test_guard_is_case_and_space_folded(self):
        self.assertEqual(normalize_guard("  Window   OPEN "), "window open")

    def test_non_text_guard_rejected(self):
        with self.assertRaises(ValueError):
            normalize_guard(7)


class RuleValidationTests(unittest.TestCase):
    def test_valid_rule_normalises(self):
        rule = validate_rule(BASE_RULES[0], STATES, EVENTS, PRIMITIVES)
        self.assertEqual(rule["primitive"], "T-Data.request")
        self.assertEqual(rule["guard"], "")

    def test_undeclared_primitive_rejected(self):
        bad = dict(BASE_RULES[0], primitive="T-Ghost.request")
        with self.assertRaises(ValueError):
            validate_rule(bad, STATES, EVENTS, PRIMITIVES)

    def test_undeclared_state_rejected(self):
        bad = dict(BASE_RULES[0], state="limbo")
        with self.assertRaises(ValueError):
            validate_rule(bad, STATES, EVENTS, PRIMITIVES)

    def test_undeclared_event_rejected(self):
        bad = dict(BASE_RULES[0], event="thunder")
        with self.assertRaises(ValueError):
            validate_rule(bad, STATES, EVENTS, PRIMITIVES)

    def test_event_kind_outside_the_closed_set_rejected(self):
        bad = dict(BASE_RULES[0], event_kind="vibes")
        with self.assertRaises(ValueError):
            validate_rule(bad, STATES, EVENTS, PRIMITIVES)

    def test_every_declared_event_kind_is_accepted(self):
        for kind in ORIGINATING_EVENT_KINDS:
            rule = dict(BASE_RULES[0], event_kind=kind)
            self.assertEqual(
                validate_rule(rule, STATES, EVENTS, PRIMITIVES)["event_kind"], kind
            )

    def test_non_mapping_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_rule(["T-Data.request"], STATES, EVENTS, PRIMITIVES)

    def test_empty_rule_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_rules([], STATES, EVENTS, PRIMITIVES)


class GenerationMapTests(unittest.TestCase):
    def _rules(self, raw):
        return validate_rules(raw, STATES, EVENTS, PRIMITIVES)

    def test_map_is_keyed_on_state_and_event(self):
        gmap = build_generation_map(self._rules(BASE_RULES))
        self.assertIn(("open", "send-request"), gmap)
        self.assertEqual(len(gmap), 3)

    def test_two_unguarded_rules_on_one_key_are_nondeterministic(self):
        raw = copy.deepcopy(BASE_RULES)
        raw.append(dict(BASE_RULES[0], primitive="T-Data.confirm"))
        conflicts = find_nondeterminism(build_generation_map(self._rules(raw)))
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["state"], "open")

    def test_distinct_guards_resolve_the_key(self):
        raw = copy.deepcopy(BASE_RULES)
        raw[0] = dict(raw[0], guard="window open")
        raw.append(dict(BASE_RULES[0], primitive="T-Data.confirm", guard="window closed"))
        gmap = build_generation_map(self._rules(raw))
        self.assertEqual(find_nondeterminism(gmap), [])
        self.assertIn(("open", "send-request"), guarded_keys(gmap))

    def test_identical_guards_do_not_resolve_the_key(self):
        raw = copy.deepcopy(BASE_RULES)
        raw[0] = dict(raw[0], guard="Window Open")
        raw.append(dict(BASE_RULES[0], primitive="T-Data.confirm", guard="  window   open"))
        conflicts = find_nondeterminism(build_generation_map(self._rules(raw)))
        self.assertEqual(len(conflicts), 1)

    def test_one_guarded_and_one_unguarded_rule_is_still_ambiguous(self):
        raw = copy.deepcopy(BASE_RULES)
        raw.append(dict(BASE_RULES[0], primitive="T-Data.confirm", guard="window open"))
        conflicts = find_nondeterminism(build_generation_map(self._rules(raw)))
        self.assertEqual(len(conflicts), 1)


class CoverageTests(unittest.TestCase):
    def _rules(self, raw):
        return validate_rules(raw, STATES, EVENTS, PRIMITIVES)

    def test_primitive_without_a_rule_is_unreachable(self):
        rules = self._rules(BASE_RULES[:2])
        self.assertEqual(unreachable_primitives(PRIMITIVES, rules), ("T-Data.confirm",))

    def test_fully_covered_catalogue_has_no_unreachable_primitive(self):
        self.assertEqual(unreachable_primitives(PRIMITIVES, self._rules(BASE_RULES)), ())

    def test_event_no_rule_consumes_is_reported(self):
        rules = self._rules(BASE_RULES[:2])
        self.assertEqual(unused_events(EVENTS, rules), ("retry-timer-expiry",))

    def test_terminal_state_rule_is_reported(self):
        raw = copy.deepcopy(BASE_RULES)
        raw[2] = dict(raw[2], state="shut-down")
        violations = terminal_state_violations(self._rules(raw), ("shut-down",))
        self.assertEqual(len(violations), 1)

    def test_no_terminal_violation_when_nothing_is_terminal(self):
        self.assertEqual(terminal_state_violations(self._rules(BASE_RULES), ()), [])


class AssessmentTests(unittest.TestCase):
    def test_clean_specification_is_compliant(self):
        result = assess_when_generated(spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_counts_are_reported(self):
        result = assess_when_generated(spec())
        self.assertEqual(result["rule_count"], 3)
        self.assertEqual(result["key_count"], 3)

    def test_unreachable_primitive_is_a_finding(self):
        result = assess_when_generated(spec(rules=copy.deepcopy(BASE_RULES[:2])))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("can never be issued" in f for f in result["findings"]))

    def test_unused_event_is_a_finding(self):
        result = assess_when_generated(spec(rules=copy.deepcopy(BASE_RULES[:2])))
        self.assertTrue(any("no generation rule consumes it" in f for f in result["findings"]))

    def test_nondeterminism_is_a_finding(self):
        raw = copy.deepcopy(BASE_RULES)
        raw.append(dict(BASE_RULES[0], primitive="T-Data.confirm"))
        result = assess_when_generated(spec(rules=raw))
        self.assertTrue(any("no distinguishing guard" in f for f in result["findings"]))

    def test_terminal_state_generation_is_a_finding(self):
        raw = copy.deepcopy(BASE_RULES)
        raw[2] = dict(raw[2], state="shut-down")
        result = assess_when_generated(spec(rules=raw))
        self.assertTrue(any("terminal state" in f for f in result["findings"]))

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["events"]
        with self.assertRaises(ValueError):
            assess_when_generated(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_when_generated(["states"])

    def test_terminal_state_outside_the_state_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_when_generated(spec(terminal_states=["nowhere"]))


if __name__ == "__main__":
    unittest.main()

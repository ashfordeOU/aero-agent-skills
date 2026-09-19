"""Contract test for the event-action function-enable leaf (stdlib unittest)."""

import unittest

from e7041_enable_the_event_action_function_logic import (
    APID_MAX,
    FINDING_DEFINITION_UNCHANGED,
    FINDING_FUNCTION_ALREADY_DISABLED,
    FINDING_FUNCTION_ALREADY_ENABLED,
    FINDING_NOTHING_ARMED,
    FINDING_STAGED_WHILE_DISABLED,
    FINDING_STATUS_NOT_PRESERVED,
    FINDING_UNKNOWN_DEFINITION,
    REQUEST_DISABLE_DEFINITION,
    REQUEST_DISABLE_FUNCTION,
    REQUEST_ENABLE_DEFINITION,
    REQUEST_ENABLE_FUNCTION,
    apply_request,
    assess_function_enabling,
    check_statuses_preserved,
    effective_armed,
    function_toggle_round_trip,
    new_function_state,
    run_requests,
    status_snapshot,
)

SAFE = (17, 4001)
WARM = (17, 4002)
DUMP = (18, 4001)
KEYS = [SAFE, WARM, DUMP]


def fn(name):
    return {"request": name}


def defn(name, key):
    return {"request": name, "key": key}


def findings_of(result):
    return [f["finding"] for f in result["findings"]]


class TestStateConstruction(unittest.TestCase):
    def test_a_new_state_is_disabled_with_nothing_armed(self):
        state = new_function_state(KEYS)
        self.assertFalse(state["function_enabled"])
        self.assertEqual(effective_armed(state), [])

    def test_the_armed_set_can_be_given_at_construction(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE, DUMP])
        self.assertEqual(effective_armed(state), [SAFE, DUMP])

    def test_an_empty_table_raises(self):
        with self.assertRaises(ValueError):
            new_function_state([])

    def test_a_repeated_key_raises(self):
        with self.assertRaises(ValueError):
            new_function_state([SAFE, SAFE])

    def test_an_armed_key_outside_the_table_raises(self):
        with self.assertRaises(ValueError):
            new_function_state(KEYS, armed_keys=[(19, 1)])

    def test_a_malformed_key_raises(self):
        with self.assertRaises(ValueError):
            new_function_state([(APID_MAX + 1, 1)])

    def test_a_key_that_is_not_a_pair_raises(self):
        with self.assertRaises(ValueError):
            new_function_state([4001])


class TestRequestValidation(unittest.TestCase):
    def test_an_unknown_request_raises(self):
        with self.assertRaises(ValueError):
            apply_request(new_function_state(KEYS), {"request": "reset-function"})

    def test_a_definition_request_without_a_key_raises(self):
        with self.assertRaises(ValueError):
            apply_request(
                new_function_state(KEYS), {"request": REQUEST_ENABLE_DEFINITION}
            )

    def test_a_function_request_naming_a_definition_raises(self):
        with self.assertRaises(ValueError):
            apply_request(
                new_function_state(KEYS),
                {"request": REQUEST_ENABLE_FUNCTION, "key": SAFE},
            )

    def test_a_definition_key_that_is_not_a_pair_raises(self):
        with self.assertRaises(ValueError):
            apply_request(
                new_function_state(KEYS),
                {"request": REQUEST_ENABLE_DEFINITION, "key": 4001},
            )

    def test_requests_must_be_a_list(self):
        with self.assertRaises(ValueError):
            run_requests(new_function_state(KEYS), fn(REQUEST_ENABLE_FUNCTION))

    def test_apply_request_needs_a_state(self):
        with self.assertRaises(ValueError):
            apply_request({"function_enabled": True}, fn(REQUEST_ENABLE_FUNCTION))


class TestFunctionSwitch(unittest.TestCase):
    def test_enabling_the_function_enables_it(self):
        state = new_function_state(KEYS)
        apply_request(state, fn(REQUEST_ENABLE_FUNCTION))
        self.assertTrue(state["function_enabled"])

    def test_enabling_an_already_enabled_function_is_reported_and_harmless(self):
        state = new_function_state(KEYS, function_enabled=True)
        findings = apply_request(state, fn(REQUEST_ENABLE_FUNCTION))
        self.assertEqual(
            [f["finding"] for f in findings], [FINDING_FUNCTION_ALREADY_ENABLED]
        )
        self.assertTrue(state["function_enabled"])

    def test_disabling_an_already_disabled_function_is_reported(self):
        state = new_function_state(KEYS)
        findings = apply_request(state, fn(REQUEST_DISABLE_FUNCTION))
        self.assertEqual(
            [f["finding"] for f in findings], [FINDING_FUNCTION_ALREADY_DISABLED]
        )

    def test_disabling_the_function_arms_nothing_effectively(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE])
        apply_request(state, fn(REQUEST_DISABLE_FUNCTION))
        self.assertEqual(effective_armed(state), [])


class TestStatusesArePreserved(unittest.TestCase):
    def test_disabling_the_function_leaves_the_per_definition_statuses_alone(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE, WARM])
        before = status_snapshot(state)
        apply_request(state, fn(REQUEST_DISABLE_FUNCTION))
        self.assertEqual(status_snapshot(state), before)

    def test_the_armed_set_comes_back_when_the_function_returns(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE, WARM])
        run_requests(
            state, [fn(REQUEST_DISABLE_FUNCTION), fn(REQUEST_ENABLE_FUNCTION)]
        )
        self.assertEqual(effective_armed(state), [SAFE, WARM])

    def test_a_deliberately_disarmed_definition_stays_disarmed_across_the_toggle(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE, WARM])
        run_requests(
            state,
            [
                defn(REQUEST_DISABLE_DEFINITION, WARM),
                fn(REQUEST_DISABLE_FUNCTION),
                fn(REQUEST_ENABLE_FUNCTION),
            ],
        )
        self.assertEqual(effective_armed(state), [SAFE])

    def test_the_round_trip_proves_the_statuses_survived(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE])
        proof = function_toggle_round_trip(state)
        self.assertTrue(proof["preserved"])
        self.assertEqual(proof["breaches"], [])

    def test_the_round_trip_leaves_the_function_switch_where_it_found_it(self):
        state = new_function_state(KEYS, armed_keys=[SAFE])
        function_toggle_round_trip(state)
        self.assertFalse(state["function_enabled"])

    def test_a_changed_status_between_two_snapshots_is_a_breach(self):
        breaches = check_statuses_preserved({SAFE: True}, {SAFE: False})
        self.assertEqual(breaches[0]["finding"], FINDING_STATUS_NOT_PRESERVED)
        self.assertTrue(breaches[0]["before"])
        self.assertFalse(breaches[0]["after"])

    def test_two_snapshots_are_needed_to_compare(self):
        with self.assertRaises(ValueError):
            check_statuses_preserved({SAFE: True}, [SAFE])


class TestDefinitionSwitch(unittest.TestCase):
    def test_a_definition_can_be_armed_while_the_function_is_disabled(self):
        state = new_function_state(KEYS)
        findings = apply_request(state, defn(REQUEST_ENABLE_DEFINITION, SAFE))
        self.assertTrue(state["definitions"][SAFE])
        self.assertIn(
            FINDING_STAGED_WHILE_DISABLED, [f["finding"] for f in findings]
        )

    def test_a_staged_definition_releases_as_soon_as_the_function_returns(self):
        state = new_function_state(KEYS)
        run_requests(
            state,
            [defn(REQUEST_ENABLE_DEFINITION, SAFE), fn(REQUEST_ENABLE_FUNCTION)],
        )
        self.assertEqual(effective_armed(state), [SAFE])

    def test_arming_an_already_armed_definition_is_reported(self):
        state = new_function_state(KEYS, function_enabled=True, armed_keys=[SAFE])
        findings = apply_request(state, defn(REQUEST_ENABLE_DEFINITION, SAFE))
        self.assertEqual(
            [f["finding"] for f in findings], [FINDING_DEFINITION_UNCHANGED]
        )

    def test_a_request_for_a_definition_the_table_lacks_is_reported(self):
        state = new_function_state(KEYS)
        findings = apply_request(state, defn(REQUEST_ENABLE_DEFINITION, (19, 9)))
        self.assertEqual(
            [f["finding"] for f in findings], [FINDING_UNKNOWN_DEFINITION]
        )
        self.assertNotIn((19, 9), state["definitions"])


class TestAssessment(unittest.TestCase):
    def test_a_straightforward_arming_sequence_is_clean(self):
        report = assess_function_enabling(
            KEYS,
            [
                defn(REQUEST_ENABLE_DEFINITION, SAFE),
                defn(REQUEST_ENABLE_DEFINITION, WARM),
                fn(REQUEST_ENABLE_FUNCTION),
            ],
        )
        self.assertEqual(report["armed"], [SAFE, WARM])
        self.assertEqual(report["armed_count"], 2)
        self.assertTrue(report["statuses_survive_a_function_toggle"])

    def test_an_enabled_function_with_nothing_armed_is_reported(self):
        report = assess_function_enabling(KEYS, [fn(REQUEST_ENABLE_FUNCTION)])
        self.assertIn(FINDING_NOTHING_ARMED, findings_of(report))
        self.assertEqual(report["armed"], [])

    def test_every_finding_carries_the_index_of_the_request_that_raised_it(self):
        report = assess_function_enabling(
            KEYS,
            [fn(REQUEST_ENABLE_FUNCTION), fn(REQUEST_ENABLE_FUNCTION),
             defn(REQUEST_ENABLE_DEFINITION, SAFE)],
        )
        repeated = [
            f for f in report["findings"]
            if f["finding"] == FINDING_FUNCTION_ALREADY_ENABLED
        ]
        self.assertEqual(repeated[0]["index"], 1)

    def test_the_report_names_every_definition_and_its_status(self):
        report = assess_function_enabling(
            KEYS, [defn(REQUEST_ENABLE_DEFINITION, DUMP)]
        )
        self.assertEqual(report["definition_count"], 3)
        self.assertTrue(report["definition_statuses"][DUMP])
        self.assertFalse(report["definition_statuses"][SAFE])

    def test_a_disabled_function_arms_nothing_however_many_definitions_are_on(self):
        report = assess_function_enabling(
            KEYS, [defn(REQUEST_ENABLE_DEFINITION, SAFE)], function_enabled=False
        )
        self.assertFalse(report["function_enabled"])
        self.assertEqual(report["armed"], [])


if __name__ == "__main__":
    unittest.main()

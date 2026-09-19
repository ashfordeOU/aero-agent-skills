"""Contract test for the e7041 disable-the-event-action-function leaf."""

import unittest

from e7041_disable_the_event_action_function_logic import (
    DISPATCHED,
    FUNCTION_DISABLED,
    FUNCTION_ENABLED,
    WITHHELD_DEFINITION_OFF,
    WITHHELD_FUNCTION_OFF,
    WITHHELD_NO_DEFINITION,
    apply_disable_function,
    assess_disable_function_request,
    definition_key,
    dispatch_decision,
    enable_state_snapshot,
    enable_states_preserved,
    validate_definition,
    validate_state,
    validate_store,
)


def definition(apid="APID-12", event="EV-BATT-LOW", enabled=True, action="TC-LOAD-SHED"):
    return {
        "application_process_id": apid,
        "event_definition_id": event,
        "enabled": enabled,
        "action_id": action,
    }


def state(status=FUNCTION_ENABLED):
    return {
        "function_status": status,
        "definitions": [
            definition(),
            definition("APID-12", "EV-TEMP-HIGH", False, "TC-HEATER-OFF"),
            definition("APID-31", "EV-SUN-LOSS", True, "TC-SAFE-MODE"),
        ],
    }


def occurrence(apid="APID-12", event="EV-BATT-LOW"):
    return {"application_process_id": apid, "event_definition_id": event}


class TestStateValidation(unittest.TestCase):
    def test_a_valid_state_normalizes(self):
        normalized = validate_state(state())
        self.assertEqual(normalized["function_status"], FUNCTION_ENABLED)
        self.assertEqual(len(normalized["definitions"]), 3)

    def test_an_unknown_function_status_raises(self):
        with self.assertRaises(ValueError):
            validate_state({"function_status": "standby", "definitions": []})

    def test_a_non_mapping_state_raises(self):
        with self.assertRaises(ValueError):
            validate_state(["function_status"])

    def test_a_definition_with_a_blank_event_id_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(event="   "))

    def test_a_definition_without_an_action_raises(self):
        record = definition()
        del record["action_id"]
        with self.assertRaises(ValueError):
            validate_definition(record)

    def test_a_non_boolean_enable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(enabled="on"))

    def test_a_duplicate_event_identity_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition(), definition()])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_the_definition_key_joins_process_and_event(self):
        self.assertEqual(definition_key("APID-12", "EV-BATT-LOW"), "APID-12/EV-BATT-LOW")


class TestTransition(unittest.TestCase):
    def test_the_function_status_reaches_disabled(self):
        self.assertEqual(
            apply_disable_function(state())["function_status"], FUNCTION_DISABLED
        )

    def test_the_definition_store_survives_the_transition(self):
        self.assertEqual(len(apply_disable_function(state())["definitions"]), 3)

    def test_every_enable_flag_is_preserved(self):
        before = enable_state_snapshot(state())
        after = enable_state_snapshot(apply_disable_function(state()))
        self.assertEqual(before, after)
        self.assertTrue(enable_states_preserved(before, after)["preserved"])

    def test_a_moved_enable_flag_is_reported(self):
        before = {"APID-12/EV-BATT-LOW": True}
        after = {"APID-12/EV-BATT-LOW": False}
        result = enable_states_preserved(before, after)
        self.assertFalse(result["preserved"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_dropped_definition_is_reported(self):
        result = enable_states_preserved({"APID-12/EV-BATT-LOW": True}, {})
        self.assertFalse(result["preserved"])

    def test_disabling_an_already_disabled_function_changes_nothing(self):
        result = assess_disable_function_request(state(FUNCTION_DISABLED))
        self.assertTrue(result["accepted"])
        self.assertTrue(result["already_disabled"])
        self.assertFalse(result["changed"])

    def test_disabling_an_enabled_function_is_a_change(self):
        result = assess_disable_function_request(state())
        self.assertTrue(result["changed"])
        self.assertEqual(result["function_status"], FUNCTION_DISABLED)


class TestDispatch(unittest.TestCase):
    def test_an_enabled_definition_dispatches_while_the_function_is_on(self):
        decision = dispatch_decision(state(), occurrence())
        self.assertTrue(decision["dispatched"])
        self.assertEqual(decision["reason"], DISPATCHED)

    def test_the_function_status_withholds_an_enabled_definition(self):
        decision = dispatch_decision(state(FUNCTION_DISABLED), occurrence())
        self.assertFalse(decision["dispatched"])
        self.assertEqual(decision["reason"], WITHHELD_FUNCTION_OFF)

    def test_a_disabled_definition_withholds_for_its_own_reason(self):
        decision = dispatch_decision(state(), occurrence("APID-12", "EV-TEMP-HIGH"))
        self.assertEqual(decision["reason"], WITHHELD_DEFINITION_OFF)

    def test_an_unbound_event_has_no_action(self):
        decision = dispatch_decision(state(), occurrence("APID-99", "EV-NONE"))
        self.assertEqual(decision["reason"], WITHHELD_NO_DEFINITION)
        self.assertIsNone(decision["action_id"])

    def test_the_event_is_still_reported_while_the_function_is_off(self):
        decision = dispatch_decision(state(FUNCTION_DISABLED), occurrence())
        self.assertTrue(decision["reported"])

    def test_a_non_mapping_occurrence_raises(self):
        with self.assertRaises(ValueError):
            dispatch_decision(state(), ["APID-12"])


class TestRequestHandling(unittest.TestCase):
    def test_the_enabled_definitions_are_still_listed_after_the_disable(self):
        result = assess_disable_function_request(state())
        self.assertEqual(
            result["enabled_definition_ids"],
            ["APID-12/EV-BATT-LOW", "APID-31/EV-SUN-LOSS"],
        )

    def test_no_replayed_occurrence_dispatches_after_the_disable(self):
        result = assess_disable_function_request(
            state(), [occurrence(), occurrence("APID-31", "EV-SUN-LOSS")]
        )
        self.assertEqual(len(result["dispatch_replays"]), 2)
        self.assertFalse(any(r["dispatched"] for r in result["dispatch_replays"]))
        self.assertEqual(result["findings"], [])

    def test_the_request_is_accepted_and_preserving(self):
        result = assess_disable_function_request(state())
        self.assertTrue(result["accepted"])
        self.assertTrue(result["preserved"])

    def test_an_empty_store_disables_cleanly(self):
        result = assess_disable_function_request(
            {"function_status": FUNCTION_ENABLED, "definitions": []}
        )
        self.assertEqual(result["enabled_definition_ids"], [])
        self.assertEqual(result["findings"], [])

    def test_an_invalid_state_raises_before_any_transition(self):
        broken = state()
        broken["definitions"][0]["enabled"] = 1
        with self.assertRaises(ValueError):
            assess_disable_function_request(broken)


if __name__ == "__main__":
    unittest.main()

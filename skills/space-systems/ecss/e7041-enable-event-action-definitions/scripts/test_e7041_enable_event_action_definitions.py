"""Contract test for the e7041 enable-event-action-definitions leaf."""

import unittest

from e7041_enable_event_action_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_PARTIAL,
    ACCEPTANCE_REJECTED,
    FUNCTION_DISABLED,
    FUNCTION_ENABLED,
    OUTCOME_ALREADY_ENABLED,
    OUTCOME_ENABLED,
    OUTCOME_UNKNOWN,
    apply_enable_definitions,
    assess_enable_request,
    enabled_definition_ids,
    resolve_instructions,
    validate_definition,
    validate_request,
    validate_state,
    validate_store,
)


def definition(apid="APID-12", event="EV-BATT-LOW", enabled=False, action="TC-LOAD-SHED"):
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


def instruction(apid="APID-12", event="EV-BATT-LOW"):
    return {"application_process_id": apid, "event_definition_id": event}


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_state_normalizes(self):
        normalized = validate_state(state())
        self.assertEqual(len(normalized["definitions"]), 3)
        self.assertEqual(normalized["function_status"], FUNCTION_ENABLED)

    def test_a_duplicate_event_identity_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition(), definition()])

    def test_a_non_boolean_enable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(enabled="off"))

    def test_a_definition_without_an_action_raises(self):
        record = definition()
        del record["action_id"]
        with self.assertRaises(ValueError):
            validate_definition(record)

    def test_an_unknown_function_status_raises(self):
        with self.assertRaises(ValueError):
            validate_state({"function_status": "armed", "definitions": []})


class TestRequestValidation(unittest.TestCase):
    def test_an_ordered_instruction_list_is_preserved(self):
        instructions = validate_request(
            [instruction("APID-31", "EV-SUN-LOSS"), instruction()]
        )
        self.assertEqual(
            [i["key"] for i in instructions],
            ["APID-31/EV-SUN-LOSS", "APID-12/EV-BATT-LOW"],
        )

    def test_an_empty_instruction_list_raises(self):
        with self.assertRaises(ValueError):
            validate_request([])

    def test_a_repeated_identity_raises(self):
        with self.assertRaises(ValueError):
            validate_request([instruction(), instruction()])

    def test_a_pair_form_instruction_is_accepted(self):
        instructions = validate_request([("APID-12", "EV-BATT-LOW")])
        self.assertEqual(instructions[0]["key"], "APID-12/EV-BATT-LOW")

    def test_an_instruction_missing_the_event_half_raises(self):
        with self.assertRaises(ValueError):
            validate_request([{"application_process_id": "APID-12"}])

    def test_an_instruction_missing_the_process_half_raises(self):
        with self.assertRaises(ValueError):
            validate_request([{"event_definition_id": "EV-BATT-LOW"}])

    def test_a_mapping_request_yields_its_instruction_list(self):
        instructions = validate_request({"instructions": [instruction()]})
        self.assertEqual(len(instructions), 1)

    def test_a_non_list_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request("APID-12/EV-BATT-LOW")


class TestResolution(unittest.TestCase):
    def test_a_held_identity_resolves(self):
        resolution = resolve_instructions(state(), [instruction()])
        self.assertEqual(resolution["known"], ["APID-12/EV-BATT-LOW"])
        self.assertEqual(resolution["unknown"], [])

    def test_an_unheld_identity_is_carried_not_dropped(self):
        resolution = resolve_instructions(state(), [instruction("APID-99", "EV-GHOST")])
        self.assertEqual(resolution["unknown"], ["APID-99/EV-GHOST"])

    def test_a_mixed_request_splits_in_order(self):
        resolution = resolve_instructions(
            state(), [instruction(), instruction("APID-99", "EV-GHOST")]
        )
        self.assertEqual(resolution["known"], ["APID-12/EV-BATT-LOW"])
        self.assertEqual(resolution["unknown"], ["APID-99/EV-GHOST"])


class TestApplication(unittest.TestCase):
    def test_a_resolved_instruction_enables_its_definition(self):
        applied = apply_enable_definitions(state(), [instruction()])
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_ENABLED)
        self.assertIn("APID-12/EV-BATT-LOW", enabled_definition_ids(applied["state"]))

    def test_an_already_enabled_definition_is_accepted_unchanged(self):
        applied = apply_enable_definitions(
            state(), [instruction("APID-31", "EV-SUN-LOSS")]
        )
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_ALREADY_ENABLED)
        self.assertFalse(applied["outcomes"][0]["changed"])

    def test_an_unknown_instruction_gets_its_own_outcome(self):
        applied = apply_enable_definitions(
            state(), [instruction("APID-99", "EV-GHOST")]
        )
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_UNKNOWN)

    def test_untargeted_definitions_keep_their_flag(self):
        applied = apply_enable_definitions(state(), [instruction()])
        self.assertEqual(
            enabled_definition_ids(applied["state"]),
            ["APID-12/EV-BATT-LOW", "APID-31/EV-SUN-LOSS"],
        )

    def test_the_source_state_is_not_mutated(self):
        original = state()
        apply_enable_definitions(original, [instruction()])
        self.assertFalse(original["definitions"][0]["enabled"])


class TestRequestHandling(unittest.TestCase):
    def test_a_fully_resolvable_request_is_accepted(self):
        result = assess_enable_request(
            state(), [instruction(), instruction("APID-12", "EV-TEMP-HIGH")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["applied_ids"]), 2)

    def test_a_mixed_request_is_partially_accepted(self):
        result = assess_enable_request(
            state(), [instruction(), instruction("APID-99", "EV-GHOST")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_PARTIAL)
        self.assertEqual(result["applied_ids"], ["APID-12/EV-BATT-LOW"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_wholly_unresolvable_request_is_rejected(self):
        result = assess_enable_request(
            state(),
            [instruction("APID-99", "EV-GHOST"), instruction("APID-98", "EV-PHANTOM")],
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["applied_ids"], [])
        self.assertEqual(len(result["findings"]), 2)

    def test_an_already_enabled_target_is_listed_as_unchanged(self):
        result = assess_enable_request(
            state(), [instruction("APID-31", "EV-SUN-LOSS")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["unchanged_ids"], ["APID-31/EV-SUN-LOSS"])
        self.assertEqual(result["applied_ids"], [])

    def test_the_function_status_is_untouched_when_it_is_off(self):
        result = assess_enable_request(state(FUNCTION_DISABLED), [instruction()])
        self.assertEqual(result["function_status"], FUNCTION_DISABLED)
        self.assertIn("APID-12/EV-BATT-LOW", result["enabled_ids"])
        self.assertEqual(result["findings"], [])

    def test_the_function_status_is_untouched_when_it_is_on(self):
        result = assess_enable_request(state(), [instruction()])
        self.assertEqual(result["function_status"], FUNCTION_ENABLED)

    def test_an_empty_request_raises_before_anything_is_applied(self):
        with self.assertRaises(ValueError):
            assess_enable_request(state(), [])

    def test_a_repeated_identity_raises_before_anything_is_applied(self):
        with self.assertRaises(ValueError):
            assess_enable_request(state(), [instruction(), instruction()])

    def test_an_invalid_store_raises_before_anything_is_applied(self):
        broken = state()
        broken["definitions"][0]["action_id"] = ""
        with self.assertRaises(ValueError):
            assess_enable_request(broken, [instruction()])

    def test_the_outcome_order_follows_the_request_order(self):
        result = assess_enable_request(
            state(),
            [instruction("APID-31", "EV-SUN-LOSS"), instruction("APID-99", "EV-GHOST"),
             instruction()],
        )
        self.assertEqual(
            [o["key"] for o in result["outcomes"]],
            ["APID-31/EV-SUN-LOSS", "APID-99/EV-GHOST", "APID-12/EV-BATT-LOW"],
        )


if __name__ == "__main__":
    unittest.main()

"""Contract test for the e7041 disable-event-action-definitions leaf."""

import unittest

from e7041_disable_event_action_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_PARTIAL,
    ACCEPTANCE_REJECTED,
    FUNCTION_DISABLED,
    FUNCTION_ENABLED,
    OUTCOME_ALREADY_DISABLED,
    OUTCOME_DISABLED,
    OUTCOME_UNKNOWN,
    action_is_withheld,
    apply_disable_definitions,
    assess_disable_request,
    deletable_definition_ids,
    resolve_instructions,
    store_membership,
    validate_definition,
    validate_request,
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
            definition("APID-12", "EV-TEMP-HIGH", True, "TC-HEATER-OFF"),
            definition("APID-31", "EV-SUN-LOSS", False, "TC-SAFE-MODE"),
        ],
    }


def instruction(apid="APID-12", event="EV-BATT-LOW"):
    return {"application_process_id": apid, "event_definition_id": event}


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_state_normalizes(self):
        self.assertEqual(len(validate_state(state())["definitions"]), 3)

    def test_a_duplicate_event_identity_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition(), definition()])

    def test_a_non_boolean_enable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(enabled=1))

    def test_a_definition_with_a_blank_action_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(action="  "))

    def test_an_unknown_function_status_raises(self):
        with self.assertRaises(ValueError):
            validate_state({"function_status": "paused", "definitions": []})


class TestRequestValidation(unittest.TestCase):
    def test_instruction_order_is_preserved(self):
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
        self.assertEqual(
            validate_request([("APID-12", "EV-BATT-LOW")])[0]["key"],
            "APID-12/EV-BATT-LOW",
        )

    def test_a_three_element_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_request([("APID-12", "EV-BATT-LOW", "extra")])

    def test_a_non_list_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request({"instructions": "APID-12"})


class TestResolution(unittest.TestCase):
    def test_a_held_identity_resolves(self):
        resolution = resolve_instructions(state(), [instruction()])
        self.assertEqual(resolution["known"], ["APID-12/EV-BATT-LOW"])

    def test_an_unheld_identity_is_carried(self):
        resolution = resolve_instructions(state(), [instruction("APID-99", "EV-GHOST")])
        self.assertEqual(resolution["unknown"], ["APID-99/EV-GHOST"])


class TestApplication(unittest.TestCase):
    def test_a_resolved_instruction_clears_the_flag(self):
        applied = apply_disable_definitions(state(), [instruction()])
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_DISABLED)
        self.assertIn("APID-12/EV-BATT-LOW", deletable_definition_ids(applied["state"]))

    def test_an_already_disabled_definition_is_accepted_unchanged(self):
        applied = apply_disable_definitions(
            state(), [instruction("APID-31", "EV-SUN-LOSS")]
        )
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_ALREADY_DISABLED)
        self.assertFalse(applied["outcomes"][0]["changed"])

    def test_an_unknown_instruction_gets_its_own_outcome(self):
        applied = apply_disable_definitions(state(), [instruction("APID-99", "EV-X")])
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_UNKNOWN)

    def test_the_definition_stays_in_the_store(self):
        applied = apply_disable_definitions(state(), [instruction()])
        self.assertEqual(len(applied["state"]["definitions"]), 3)
        self.assertEqual(store_membership(applied["state"]), store_membership(state()))

    def test_the_action_binding_survives_the_disable(self):
        applied = apply_disable_definitions(state(), [instruction()])
        self.assertEqual(applied["state"]["definitions"][0]["action_id"], "TC-LOAD-SHED")

    def test_the_source_state_is_not_mutated(self):
        original = state()
        apply_disable_definitions(original, [instruction()])
        self.assertTrue(original["definitions"][0]["enabled"])


class TestWithholding(unittest.TestCase):
    def test_an_enabled_definition_under_an_enabled_function_is_not_withheld(self):
        verdict = action_is_withheld(state(), "APID-12", "EV-BATT-LOW")
        self.assertFalse(verdict["withheld"])
        self.assertTrue(verdict["reported"])

    def test_a_disabled_definition_withholds_its_action(self):
        verdict = action_is_withheld(state(), "APID-31", "EV-SUN-LOSS")
        self.assertTrue(verdict["withheld"])

    def test_the_event_is_still_reported_when_the_action_is_withheld(self):
        verdict = action_is_withheld(state(), "APID-31", "EV-SUN-LOSS")
        self.assertTrue(verdict["reported"])
        self.assertEqual(verdict["action_id"], "TC-SAFE-MODE")

    def test_an_unheld_identity_reports_as_not_held(self):
        verdict = action_is_withheld(state(), "APID-99", "EV-GHOST")
        self.assertFalse(verdict["held"])
        self.assertIsNone(verdict["action_id"])

    def test_a_disabled_function_withholds_an_enabled_definition(self):
        verdict = action_is_withheld(state(FUNCTION_DISABLED), "APID-12", "EV-BATT-LOW")
        self.assertTrue(verdict["withheld"])


class TestRequestHandling(unittest.TestCase):
    def test_a_fully_resolvable_request_is_accepted(self):
        result = assess_disable_request(
            state(), [instruction(), instruction("APID-12", "EV-TEMP-HIGH")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["applied_ids"]), 2)

    def test_a_mixed_request_is_partially_accepted(self):
        result = assess_disable_request(
            state(), [instruction(), instruction("APID-99", "EV-GHOST")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_PARTIAL)
        self.assertEqual(result["applied_ids"], ["APID-12/EV-BATT-LOW"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_wholly_unresolvable_request_is_rejected(self):
        result = assess_disable_request(
            state(),
            [instruction("APID-99", "EV-GHOST"), instruction("APID-98", "EV-PHANTOM")],
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["applied_ids"], [])

    def test_the_store_membership_is_unchanged_by_a_disable(self):
        result = assess_disable_request(state(), [instruction()])
        self.assertEqual(
            result["store_membership"],
            ["APID-12/EV-BATT-LOW", "APID-12/EV-TEMP-HIGH", "APID-31/EV-SUN-LOSS"],
        )

    def test_a_disable_makes_the_definition_deletable(self):
        result = assess_disable_request(state(), [instruction()])
        self.assertIn("APID-12/EV-BATT-LOW", result["deletable_ids"])

    def test_the_function_status_is_untouched(self):
        result = assess_disable_request(state(FUNCTION_DISABLED), [instruction()])
        self.assertEqual(result["function_status"], FUNCTION_DISABLED)
        self.assertEqual(result["findings"], [])

    def test_disabling_every_definition_leaves_the_function_on(self):
        result = assess_disable_request(
            state(),
            [
                instruction(),
                instruction("APID-12", "EV-TEMP-HIGH"),
                instruction("APID-31", "EV-SUN-LOSS"),
            ],
        )
        self.assertEqual(result["function_status"], FUNCTION_ENABLED)
        self.assertEqual(len(result["deletable_ids"]), 3)

    def test_an_empty_request_raises_before_anything_is_applied(self):
        with self.assertRaises(ValueError):
            assess_disable_request(state(), [])

    def test_a_repeated_identity_raises_before_anything_is_applied(self):
        with self.assertRaises(ValueError):
            assess_disable_request(state(), [instruction(), instruction()])

    def test_an_invalid_store_raises_before_anything_is_applied(self):
        broken = state()
        broken["definitions"][1]["enabled"] = "yes"
        with self.assertRaises(ValueError):
            assess_disable_request(broken, [instruction()])


if __name__ == "__main__":
    unittest.main()

"""Contract test for the e7041 delete-event-action-definitions leaf."""

import unittest

from e7041_delete_event_action_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_PARTIAL,
    ACCEPTANCE_REJECTED,
    FUNCTION_DISABLED,
    FUNCTION_ENABLED,
    OUTCOME_DELETED,
    OUTCOME_STILL_ENABLED,
    OUTCOME_UNKNOWN,
    apply_delete_definitions,
    assess_delete_request,
    categorize_instructions,
    freed_capacity,
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


def state(status=FUNCTION_ENABLED, capacity=6):
    return {
        "function_status": status,
        "capacity": capacity,
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
        normalized = validate_state(state())
        self.assertEqual(len(normalized["definitions"]), 3)
        self.assertEqual(normalized["capacity"], 6)

    def test_a_duplicate_event_identity_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition(), definition()])

    def test_a_definition_without_an_action_raises(self):
        record = definition()
        del record["action_id"]
        with self.assertRaises(ValueError):
            validate_definition(record)

    def test_a_non_boolean_enable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(definition(enabled=0))

    def test_a_capacity_below_the_store_size_raises(self):
        with self.assertRaises(ValueError):
            validate_state(state(capacity=2))

    def test_an_unknown_function_status_raises(self):
        with self.assertRaises(ValueError):
            validate_state({"function_status": "idle", "definitions": []})


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

    def test_a_blank_process_half_raises(self):
        with self.assertRaises(ValueError):
            validate_request([instruction(apid="   ")])


class TestCategorization(unittest.TestCase):
    def test_a_disabled_held_definition_is_deletable(self):
        groups = categorize_instructions(state(), [instruction()])
        self.assertEqual(groups["deletable"], ["APID-12/EV-BATT-LOW"])

    def test_an_enabled_held_definition_is_not_deletable(self):
        groups = categorize_instructions(
            state(), [instruction("APID-12", "EV-TEMP-HIGH")]
        )
        self.assertEqual(groups["still_enabled"], ["APID-12/EV-TEMP-HIGH"])
        self.assertEqual(groups["deletable"], [])

    def test_an_unheld_identity_lands_in_its_own_group(self):
        groups = categorize_instructions(state(), [instruction("APID-99", "EV-GHOST")])
        self.assertEqual(groups["unknown"], ["APID-99/EV-GHOST"])

    def test_the_three_groups_partition_the_request(self):
        groups = categorize_instructions(
            state(),
            [
                instruction(),
                instruction("APID-12", "EV-TEMP-HIGH"),
                instruction("APID-99", "EV-GHOST"),
            ],
        )
        total = (
            len(groups["deletable"]) + len(groups["still_enabled"]) + len(groups["unknown"])
        )
        self.assertEqual(total, len(groups["requested"]))


class TestApplication(unittest.TestCase):
    def test_a_deletable_definition_leaves_the_store(self):
        applied = apply_delete_definitions(state(), [instruction()])
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_DELETED)
        self.assertEqual(len(applied["state"]["definitions"]), 2)

    def test_the_action_binding_goes_with_the_definition(self):
        applied = apply_delete_definitions(state(), [instruction()])
        self.assertNotIn(
            "TC-LOAD-SHED",
            [record["action_id"] for record in applied["state"]["definitions"]],
        )

    def test_an_enabled_definition_survives_the_refusal_untouched(self):
        applied = apply_delete_definitions(
            state(), [instruction("APID-12", "EV-TEMP-HIGH")]
        )
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_STILL_ENABLED)
        self.assertEqual(len(applied["state"]["definitions"]), 3)
        self.assertTrue(applied["state"]["definitions"][1]["enabled"])

    def test_an_unheld_identity_gets_its_own_outcome(self):
        applied = apply_delete_definitions(state(), [instruction("APID-99", "EV-X")])
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_UNKNOWN)
        self.assertEqual(len(applied["state"]["definitions"]), 3)

    def test_one_refusal_does_not_stop_the_rest(self):
        applied = apply_delete_definitions(
            state(),
            [instruction("APID-12", "EV-TEMP-HIGH"), instruction()],
        )
        self.assertEqual(
            [o["outcome"] for o in applied["outcomes"]],
            [OUTCOME_STILL_ENABLED, OUTCOME_DELETED],
        )

    def test_the_source_state_is_not_mutated(self):
        original = state()
        apply_delete_definitions(original, [instruction()])
        self.assertEqual(len(original["definitions"]), 3)

    def test_freed_capacity_counts_the_removed_definitions(self):
        applied = apply_delete_definitions(
            state(), [instruction(), instruction("APID-31", "EV-SUN-LOSS")]
        )
        self.assertEqual(freed_capacity(state(), applied["state"]), 2)


class TestRequestHandling(unittest.TestCase):
    def test_a_fully_deletable_request_is_accepted(self):
        result = assess_delete_request(
            state(), [instruction(), instruction("APID-31", "EV-SUN-LOSS")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["freed_capacity"], 2)

    def test_a_partly_refused_request_is_partially_accepted(self):
        result = assess_delete_request(
            state(), [instruction(), instruction("APID-12", "EV-TEMP-HIGH")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_PARTIAL)
        self.assertEqual(result["refused_enabled_ids"], ["APID-12/EV-TEMP-HIGH"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_wholly_refused_request_is_rejected(self):
        result = assess_delete_request(
            state(),
            [instruction("APID-12", "EV-TEMP-HIGH"), instruction("APID-99", "EV-X")],
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["deleted_ids"], [])
        self.assertEqual(len(result["findings"]), 2)

    def test_an_unheld_identity_is_never_reported_as_deleted(self):
        result = assess_delete_request(state(), [instruction("APID-99", "EV-GHOST")])
        self.assertEqual(result["deleted_ids"], [])
        self.assertEqual(result["unknown_ids"], ["APID-99/EV-GHOST"])

    def test_the_surviving_store_is_listed_in_store_order(self):
        result = assess_delete_request(state(), [instruction()])
        self.assertEqual(
            result["surviving_ids"], ["APID-12/EV-TEMP-HIGH", "APID-31/EV-SUN-LOSS"]
        )

    def test_the_function_status_is_untouched(self):
        result = assess_delete_request(state(FUNCTION_DISABLED), [instruction()])
        self.assertEqual(result["function_status"], FUNCTION_DISABLED)

    def test_a_disabled_function_does_not_make_an_enabled_definition_deletable(self):
        result = assess_delete_request(
            state(FUNCTION_DISABLED), [instruction("APID-12", "EV-TEMP-HIGH")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)

    def test_an_empty_request_raises_before_anything_is_deleted(self):
        with self.assertRaises(ValueError):
            assess_delete_request(state(), [])

    def test_a_repeated_identity_raises_before_anything_is_deleted(self):
        with self.assertRaises(ValueError):
            assess_delete_request(state(), [instruction(), instruction()])

    def test_an_invalid_store_raises_before_anything_is_deleted(self):
        broken = state()
        broken["definitions"][0]["action_id"] = ""
        with self.assertRaises(ValueError):
            assess_delete_request(broken, [instruction()])


if __name__ == "__main__":
    unittest.main()

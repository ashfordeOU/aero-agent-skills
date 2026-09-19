"""Contract test for the e7041 add-event-action-definitions leaf."""

import unittest

from e7041_add_event_action_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_PARTIAL,
    ACCEPTANCE_REJECTED,
    EVENT_ACTION_SERVICE_TYPE,
    FUNCTION_ENABLED,
    OUTCOME_ADDED,
    OUTCOME_CAPACITY,
    OUTCOME_DUPLICATE,
    action_is_recursive,
    apply_add_definitions,
    assess_add_request,
    remaining_capacity,
    validate_action,
    validate_definition,
    validate_request,
    validate_state,
    validate_store,
)


def action(request_id="TC-LOAD-SHED", service_type=8, subtype=1):
    return {
        "request_id": request_id,
        "service_type": service_type,
        "message_subtype": subtype,
    }


def definition(apid="APID-12", event="EV-BATT-LOW", enabled=False, act=None):
    return {
        "application_process_id": apid,
        "event_definition_id": event,
        "enabled": enabled,
        "action": act if act is not None else action(),
    }


def state(capacity=5):
    return {
        "function_status": FUNCTION_ENABLED,
        "capacity": capacity,
        "definitions": [
            definition(),
            definition("APID-12", "EV-TEMP-HIGH", True, action("TC-HEATER-OFF")),
        ],
    }


def instruction(apid="APID-31", event="EV-SUN-LOSS", enabled=False, act=None):
    return {
        "application_process_id": apid,
        "event_definition_id": event,
        "enabled": enabled,
        "action": act if act is not None else action("TC-SAFE-MODE"),
    }


class TestActionValidation(unittest.TestCase):
    def test_a_valid_action_normalizes(self):
        normalized = validate_action(action(), "APID-12/EV-BATT-LOW")
        self.assertEqual(normalized["service_type"], 8)

    def test_a_non_mapping_action_raises(self):
        with self.assertRaises(ValueError):
            validate_action(["TC-LOAD-SHED"], "APID-12/EV-BATT-LOW")

    def test_an_action_without_a_request_id_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action(request_id=""), "APID-12/EV-BATT-LOW")

    def test_a_non_integer_service_type_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action(service_type="8"), "APID-12/EV-BATT-LOW")

    def test_a_boolean_message_subtype_raises(self):
        with self.assertRaises(ValueError):
            validate_action(action(subtype=True), "APID-12/EV-BATT-LOW")

    def test_a_management_action_is_recognised_as_recursive(self):
        self.assertTrue(
            action_is_recursive(action(service_type=EVENT_ACTION_SERVICE_TYPE))
        )

    def test_an_ordinary_action_is_not_recursive(self):
        self.assertFalse(action_is_recursive(action()))


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_state_normalizes(self):
        normalized = validate_state(state())
        self.assertEqual(len(normalized["definitions"]), 2)
        self.assertEqual(normalized["capacity"], 5)

    def test_a_duplicate_identity_in_the_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store([definition(), definition()])

    def test_a_definition_without_an_action_raises(self):
        record = definition()
        del record["action"]
        with self.assertRaises(ValueError):
            validate_definition(record)

    def test_a_capacity_below_the_store_size_raises(self):
        with self.assertRaises(ValueError):
            validate_state(state(capacity=1))

    def test_a_negative_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_state(state(capacity=-1))

    def test_an_unbounded_store_reports_no_remaining_capacity_figure(self):
        self.assertIsNone(remaining_capacity(state(capacity=None)))

    def test_a_bounded_store_reports_its_free_slots(self):
        self.assertEqual(remaining_capacity(state()), 3)


class TestRequestValidation(unittest.TestCase):
    def test_an_ordered_instruction_list_is_preserved(self):
        instructions = validate_request(
            [instruction(), instruction("APID-44", "EV-GYRO-FAIL")]
        )
        self.assertEqual(
            [i["key"] for i in instructions],
            ["APID-31/EV-SUN-LOSS", "APID-44/EV-GYRO-FAIL"],
        )

    def test_an_empty_instruction_list_raises(self):
        with self.assertRaises(ValueError):
            validate_request([])

    def test_a_repeated_identity_raises(self):
        with self.assertRaises(ValueError):
            validate_request([instruction(), instruction()])

    def test_an_instruction_binding_a_management_action_raises(self):
        with self.assertRaises(ValueError):
            validate_request(
                [instruction(act=action("TC-EA-DELETE", EVENT_ACTION_SERVICE_TYPE))]
            )

    def test_an_instruction_without_an_event_half_raises(self):
        raw = instruction()
        del raw["event_definition_id"]
        with self.assertRaises(ValueError):
            validate_request([raw])

    def test_a_new_definition_defaults_to_disabled(self):
        raw = instruction()
        del raw["enabled"]
        self.assertFalse(validate_request([raw])[0]["enabled"])

    def test_a_non_boolean_enable_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request([instruction(enabled="yes")])


class TestApplication(unittest.TestCase):
    def test_a_new_identity_is_added(self):
        applied = apply_add_definitions(state(), [instruction()])
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_ADDED)
        self.assertEqual(len(applied["state"]["definitions"]), 3)

    def test_a_duplicate_identity_is_refused_not_overwritten(self):
        applied = apply_add_definitions(
            state(), [instruction("APID-12", "EV-BATT-LOW", act=action("TC-OTHER"))]
        )
        self.assertEqual(applied["outcomes"][0]["outcome"], OUTCOME_DUPLICATE)
        self.assertEqual(
            applied["state"]["definitions"][0]["action"]["request_id"], "TC-LOAD-SHED"
        )

    def test_capacity_refuses_the_instruction_that_overflows(self):
        applied = apply_add_definitions(
            state(capacity=3),
            [instruction(), instruction("APID-44", "EV-GYRO-FAIL")],
        )
        self.assertEqual(
            [o["outcome"] for o in applied["outcomes"]],
            [OUTCOME_ADDED, OUTCOME_CAPACITY],
        )

    def test_capacity_is_counted_against_the_working_copy(self):
        applied = apply_add_definitions(
            state(capacity=4),
            [
                instruction(),
                instruction("APID-44", "EV-GYRO-FAIL"),
                instruction("APID-55", "EV-RW-SAT"),
            ],
        )
        self.assertEqual(
            [o["outcome"] for o in applied["outcomes"]],
            [OUTCOME_ADDED, OUTCOME_ADDED, OUTCOME_CAPACITY],
        )

    def test_an_unbounded_store_admits_everything(self):
        applied = apply_add_definitions(
            state(capacity=None),
            [instruction(), instruction("APID-44", "EV-GYRO-FAIL")],
        )
        self.assertTrue(all(o["added"] for o in applied["outcomes"]))

    def test_the_source_state_is_not_mutated(self):
        original = state()
        apply_add_definitions(original, [instruction()])
        self.assertEqual(len(original["definitions"]), 2)


class TestRequestHandling(unittest.TestCase):
    def test_a_fully_admissible_request_is_accepted(self):
        result = assess_add_request(
            state(), [instruction(), instruction("APID-44", "EV-GYRO-FAIL")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["store_size"], 4)

    def test_a_partly_duplicate_request_is_partially_accepted(self):
        result = assess_add_request(
            state(), [instruction(), instruction("APID-12", "EV-BATT-LOW")]
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_PARTIAL)
        self.assertEqual(result["duplicate_ids"], ["APID-12/EV-BATT-LOW"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_wholly_duplicate_request_is_rejected(self):
        result = assess_add_request(
            state(),
            [
                instruction("APID-12", "EV-BATT-LOW"),
                instruction("APID-12", "EV-TEMP-HIGH"),
            ],
        )
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["added_ids"], [])

    def test_a_full_store_rejects_the_whole_request(self):
        result = assess_add_request(state(capacity=2), [instruction()])
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertEqual(result["refused_for_capacity_ids"], ["APID-31/EV-SUN-LOSS"])

    def test_an_admitted_definition_lands_disabled_by_default(self):
        result = assess_add_request(state(), [instruction()])
        self.assertNotIn("APID-31/EV-SUN-LOSS", result["enabled_ids"])

    def test_an_instruction_may_ask_for_an_enabled_definition(self):
        result = assess_add_request(state(), [instruction(enabled=True)])
        self.assertIn("APID-31/EV-SUN-LOSS", result["enabled_ids"])

    def test_the_remaining_capacity_is_reported_after_the_add(self):
        result = assess_add_request(state(), [instruction()])
        self.assertEqual(result["remaining_capacity"], 2)

    def test_the_outcome_order_follows_the_request_order(self):
        result = assess_add_request(
            state(),
            [instruction("APID-44", "EV-GYRO-FAIL"), instruction()],
        )
        self.assertEqual(
            [o["key"] for o in result["outcomes"]],
            ["APID-44/EV-GYRO-FAIL", "APID-31/EV-SUN-LOSS"],
        )

    def test_a_recursive_action_raises_before_anything_is_added(self):
        with self.assertRaises(ValueError):
            assess_add_request(
                state(),
                [instruction(act=action("TC-EA-ADD", EVENT_ACTION_SERVICE_TYPE))],
            )

    def test_an_empty_request_raises_before_anything_is_added(self):
        with self.assertRaises(ValueError):
            assess_add_request(state(), [])


if __name__ == "__main__":
    unittest.main()

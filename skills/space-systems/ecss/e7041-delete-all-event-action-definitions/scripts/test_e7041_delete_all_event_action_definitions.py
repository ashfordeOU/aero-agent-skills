"""Contract test for the e7041 delete-all-event-action-definitions leaf."""

import unittest

from e7041_delete_all_event_action_definitions_logic import (
    ACCEPTANCE_ACCEPTED,
    ACCEPTANCE_REJECTED,
    FUNCTION_DISABLED,
    FUNCTION_ENABLED,
    PRECONDITION_MET,
    REFUSAL_FUNCTION_ENABLED,
    apply_delete_all,
    assess_delete_all_request,
    clearance_precondition,
    released_action_bindings,
    store_is_empty,
    validate_definition,
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


def state(status=FUNCTION_DISABLED, capacity=6):
    return {
        "function_status": status,
        "capacity": capacity,
        "definitions": [
            definition(),
            definition("APID-12", "EV-TEMP-HIGH", True, "TC-HEATER-OFF"),
            definition("APID-31", "EV-SUN-LOSS", False, "TC-SAFE-MODE"),
        ],
    }


def empty_state(status=FUNCTION_DISABLED):
    return {"function_status": status, "capacity": 6, "definitions": []}


class TestStateValidation(unittest.TestCase):
    def test_a_valid_state_normalizes(self):
        normalized = validate_state(state())
        self.assertEqual(len(normalized["definitions"]), 3)
        self.assertEqual(normalized["function_status"], FUNCTION_DISABLED)

    def test_a_missing_function_status_raises(self):
        with self.assertRaises(ValueError):
            validate_state({"definitions": []})

    def test_an_unknown_function_status_raises(self):
        with self.assertRaises(ValueError):
            validate_state({"function_status": "cleared", "definitions": []})

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
            validate_definition(definition(enabled="no"))

    def test_a_capacity_below_the_store_size_raises(self):
        with self.assertRaises(ValueError):
            validate_state(state(capacity=2))

    def test_a_negative_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_state(state(capacity=-3))

    def test_an_unbounded_capacity_is_accepted(self):
        self.assertIsNone(validate_state(state(capacity=None))["capacity"])


class TestPrecondition(unittest.TestCase):
    def test_an_enabled_function_blocks_the_clearance(self):
        precondition = clearance_precondition(state(FUNCTION_ENABLED))
        self.assertFalse(precondition["admissible"])
        self.assertEqual(precondition["reason"], REFUSAL_FUNCTION_ENABLED)

    def test_the_refusal_names_the_command_that_has_to_come_first(self):
        precondition = clearance_precondition(state(FUNCTION_ENABLED))
        self.assertIn("disable", precondition["required_action"])

    def test_a_disabled_function_admits_the_clearance(self):
        precondition = clearance_precondition(state())
        self.assertTrue(precondition["admissible"])
        self.assertEqual(precondition["reason"], PRECONDITION_MET)
        self.assertIsNone(precondition["required_action"])

    def test_an_enabled_function_blocks_an_empty_store_too(self):
        self.assertFalse(clearance_precondition(empty_state(FUNCTION_ENABLED))["admissible"])

    def test_applying_the_clearance_under_an_enabled_function_raises(self):
        with self.assertRaises(ValueError):
            apply_delete_all(state(FUNCTION_ENABLED))


class TestClearance(unittest.TestCase):
    def test_the_store_is_emptied_completely(self):
        after = apply_delete_all(state())
        self.assertEqual(after["definitions"], [])
        self.assertTrue(store_is_empty(after))

    def test_an_individually_enabled_definition_is_not_spared(self):
        result = assess_delete_all_request(state())
        self.assertEqual(result["removed_enabled_ids"], ["APID-12/EV-TEMP-HIGH"])
        self.assertEqual(result["surviving_ids"], [])

    def test_every_action_binding_leaves_with_its_definition(self):
        after = apply_delete_all(state())
        self.assertEqual(
            released_action_bindings(state(), after),
            ["TC-LOAD-SHED", "TC-HEATER-OFF", "TC-SAFE-MODE"],
        )

    def test_the_function_status_is_carried_across_unchanged(self):
        self.assertEqual(apply_delete_all(state())["function_status"], FUNCTION_DISABLED)

    def test_the_declared_capacity_survives_the_clearance(self):
        self.assertEqual(apply_delete_all(state())["capacity"], 6)

    def test_the_source_state_is_not_mutated(self):
        original = state()
        apply_delete_all(original)
        self.assertEqual(len(original["definitions"]), 3)


class TestRequestHandling(unittest.TestCase):
    def test_a_clearance_under_a_disabled_function_is_accepted(self):
        result = assess_delete_all_request(state())
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertTrue(result["precondition_met"])
        self.assertEqual(result["findings"], [])

    def test_a_clearance_under_an_enabled_function_is_rejected(self):
        result = assess_delete_all_request(state(FUNCTION_ENABLED))
        self.assertEqual(result["acceptance"], ACCEPTANCE_REJECTED)
        self.assertFalse(result["precondition_met"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_refused_clearance_returns_the_store_untouched(self):
        result = assess_delete_all_request(state(FUNCTION_ENABLED))
        self.assertEqual(len(result["state"]["definitions"]), 3)
        self.assertEqual(
            result["surviving_ids"],
            ["APID-12/EV-BATT-LOW", "APID-12/EV-TEMP-HIGH", "APID-31/EV-SUN-LOSS"],
        )
        self.assertFalse(result["changed"])

    def test_a_refused_clearance_frees_nothing(self):
        result = assess_delete_all_request(state(FUNCTION_ENABLED))
        self.assertEqual(result["freed_capacity"], 0)
        self.assertEqual(result["removed_ids"], [])

    def test_an_accepted_clearance_frees_every_slot_it_held(self):
        result = assess_delete_all_request(state())
        self.assertEqual(result["freed_capacity"], 3)
        self.assertEqual(len(result["removed_ids"]), 3)

    def test_an_accepted_clearance_releases_every_action_binding(self):
        result = assess_delete_all_request(state())
        self.assertEqual(len(result["released_action_ids"]), 3)

    def test_an_empty_store_is_an_accepted_no_change(self):
        result = assess_delete_all_request(empty_state())
        self.assertEqual(result["acceptance"], ACCEPTANCE_ACCEPTED)
        self.assertFalse(result["changed"])
        self.assertEqual(result["freed_capacity"], 0)
        self.assertEqual(result["findings"], [])

    def test_the_function_status_is_not_moved_by_an_accepted_clearance(self):
        result = assess_delete_all_request(state())
        self.assertEqual(result["function_status"], FUNCTION_DISABLED)

    def test_an_invalid_store_raises_before_the_precondition_is_judged(self):
        broken = state()
        broken["definitions"][2]["action_id"] = "  "
        with self.assertRaises(ValueError):
            assess_delete_all_request(broken)

    def test_a_non_mapping_state_raises(self):
        with self.assertRaises(ValueError):
            assess_delete_all_request(["function_status"])


if __name__ == "__main__":
    unittest.main()

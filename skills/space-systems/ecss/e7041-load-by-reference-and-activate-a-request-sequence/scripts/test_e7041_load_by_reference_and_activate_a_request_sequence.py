"""Contract test for the e7041 load-by-reference-and-activate leaf."""

import unittest

from e7041_load_by_reference_and_activate_a_request_sequence_logic import (
    REFUSAL_COPY_CHECKSUM_MISMATCH,
    REFUSAL_DESTINATION_EXECUTING,
    REFUSAL_DESTINATION_UNDER_LOAD,
    REFUSAL_EMPTY_SOURCE,
    REFUSAL_NO_FREE_SLOT,
    REFUSAL_UNKNOWN_DESTINATION,
    REFUSAL_UNRESOLVED_REFERENCE,
    STEP_ACTIVATE,
    STEP_LOAD,
    STEP_RESOLVE,
    STEP_VERIFY,
    VERDICT_LOADED_AND_ACTIVATED,
    VERDICT_REFUSED,
    apply_load_and_activate,
    assess_load_and_activate,
    executing_count,
    failing_step,
    find_slot,
    landed_checksum,
    resolve_reference,
    step_refusals,
    validate_engine,
    validate_repository,
    validate_repository_entry,
    validate_request,
    validate_slot,
    validate_store,
)


def entry(reference="SEQ-SAFEHOLD", request_count=6, checksum=2048):
    return {
        "reference": reference,
        "request_count": request_count,
        "checksum": checksum,
    }


def repository():
    return [
        entry("SEQ-SAFEHOLD", 6, 2048),
        entry("SEQ-DEORBIT", 12, 771),
        entry("SEQ-STUB", 0, 0),
    ]


def slot(sid="RS-1", load_state="empty", execution_state="inactive",
         request_count=0, body_checksum=0):
    return {
        "id": sid,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "body_checksum": body_checksum,
    }


def store():
    return [
        slot("RS-1"),
        slot("RS-2", "loaded", "inactive", 3, 55),
        slot("RS-3", "loaded", "executing", 9, 400),
    ]


def request(reference="SEQ-SAFEHOLD", destination_id="RS-1", **kw):
    call = {"reference": reference, "destination_id": destination_id}
    call.update(kw)
    return call


def engine(capacity=3):
    return {"concurrent_capacity": capacity}


class TestValidation(unittest.TestCase):
    def test_a_valid_repository_entry_normalizes(self):
        record = validate_repository_entry(entry())
        self.assertEqual(record["request_count"], 6)

    def test_a_non_mapping_repository_entry_raises(self):
        with self.assertRaises(ValueError):
            validate_repository_entry("SEQ-SAFEHOLD")

    def test_a_duplicate_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_repository([entry("SEQ-A"), entry("SEQ-A")])

    def test_a_negative_source_checksum_raises(self):
        with self.assertRaises(ValueError):
            validate_repository_entry(entry(checksum=-1))

    def test_a_valid_slot_normalizes(self):
        self.assertEqual(validate_slot(slot())["load_state"], "empty")

    def test_an_unknown_slot_load_state_raises(self):
        with self.assertRaises(ValueError):
            validate_slot(slot(load_state="warm"))

    def test_an_empty_slot_carrying_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_slot(slot(request_count=4))

    def test_a_slot_executing_while_not_loaded_raises(self):
        with self.assertRaises(ValueError):
            validate_slot(slot(load_state="under-load", execution_state="executing"))

    def test_a_duplicate_slot_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store([slot("RS-1"), slot("RS-1")])

    def test_a_request_without_a_destination_raises(self):
        with self.assertRaises(ValueError):
            validate_request({"reference": "SEQ-SAFEHOLD"})

    def test_a_request_with_a_blank_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(reference="  "))

    def test_a_capacity_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_engine({"concurrent_capacity": 0})


class TestResolution(unittest.TestCase):
    def test_a_held_reference_resolves(self):
        self.assertEqual(resolve_reference(repository(), "SEQ-DEORBIT")["request_count"], 12)

    def test_an_absent_reference_does_not_resolve(self):
        self.assertIsNone(resolve_reference(repository(), "SEQ-GHOST"))

    def test_a_held_slot_is_found(self):
        self.assertEqual(find_slot(store(), "RS-2")["request_count"], 3)

    def test_an_absent_slot_is_not_found(self):
        self.assertIsNone(find_slot(store(), "RS-9"))

    def test_a_clean_copy_lands_on_the_source_checksum(self):
        self.assertEqual(landed_checksum(entry(), validate_request(request())), 2048)

    def test_a_stated_landed_checksum_overrides_the_clean_assumption(self):
        call = validate_request(request(landed_checksum=7))
        self.assertEqual(landed_checksum(entry(), call), 7)


class TestStepRefusals(unittest.TestCase):
    def test_a_clean_request_raises_no_refusal(self):
        self.assertIsNone(failing_step(step_refusals(repository(), store(), request(), engine())))

    def test_an_unresolvable_reference_fails_at_resolve(self):
        refusals = step_refusals(repository(), store(), request(reference="SEQ-GHOST"), engine())
        self.assertEqual(failing_step(refusals), STEP_RESOLVE)
        self.assertEqual(refusals[STEP_RESOLVE][0]["code"], REFUSAL_UNRESOLVED_REFERENCE)

    def test_an_empty_source_body_fails_at_resolve(self):
        refusals = step_refusals(repository(), store(), request(reference="SEQ-STUB"), engine())
        self.assertEqual(refusals[STEP_RESOLVE][0]["code"], REFUSAL_EMPTY_SOURCE)

    def test_an_unresolvable_reference_stops_before_the_load_step(self):
        refusals = step_refusals(repository(), store(), request(reference="SEQ-GHOST"), engine())
        self.assertEqual(refusals[STEP_LOAD], [])

    def test_an_absent_destination_fails_at_load(self):
        refusals = step_refusals(repository(), store(), request(destination_id="RS-9"), engine())
        self.assertEqual(refusals[STEP_LOAD][0]["code"], REFUSAL_UNKNOWN_DESTINATION)

    def test_an_executing_destination_is_never_loaded_over(self):
        refusals = step_refusals(repository(), store(), request(destination_id="RS-3"), engine())
        self.assertIn(REFUSAL_DESTINATION_EXECUTING,
                      [item["code"] for item in refusals[STEP_LOAD]])

    def test_a_destination_under_load_is_refused(self):
        slots = store()
        slots[0]["load_state"] = "under-load"
        refusals = step_refusals(repository(), slots, request(), engine())
        self.assertIn(REFUSAL_DESTINATION_UNDER_LOAD,
                      [item["code"] for item in refusals[STEP_LOAD]])

    def test_a_damaged_copy_fails_at_verify(self):
        refusals = step_refusals(repository(), store(), request(landed_checksum=99), engine())
        self.assertEqual(failing_step(refusals), STEP_VERIFY)
        self.assertEqual(refusals[STEP_VERIFY][0]["code"], REFUSAL_COPY_CHECKSUM_MISMATCH)

    def test_a_damaged_copy_is_caught_before_activation(self):
        refusals = step_refusals(repository(), store(), request(landed_checksum=99), engine())
        self.assertEqual(refusals[STEP_ACTIVATE], [])

    def test_a_full_engine_fails_at_activate(self):
        refusals = step_refusals(repository(), store(), request(), engine(capacity=1))
        self.assertEqual(failing_step(refusals), STEP_ACTIVATE)
        self.assertEqual(refusals[STEP_ACTIVATE][0]["code"], REFUSAL_NO_FREE_SLOT)


class TestApply(unittest.TestCase):
    def test_the_body_lands_in_the_named_slot(self):
        updated = apply_load_and_activate(store(), request(), validate_repository_entry(entry()))
        self.assertEqual(updated[0]["request_count"], 6)
        self.assertEqual(updated[0]["load_state"], "loaded")

    def test_the_slot_starts_executing_at_the_first_request(self):
        updated = apply_load_and_activate(store(), request(), validate_repository_entry(entry()))
        self.assertEqual(updated[0]["execution_state"], "executing")
        self.assertEqual(updated[0]["next_request_index"], 1)

    def test_the_slot_records_where_the_body_came_from(self):
        updated = apply_load_and_activate(store(), request(), validate_repository_entry(entry()))
        self.assertEqual(updated[0]["loaded_from"], "SEQ-SAFEHOLD")

    def test_the_other_slots_are_untouched(self):
        updated = apply_load_and_activate(store(), request(), validate_repository_entry(entry()))
        self.assertEqual(updated[1]["request_count"], 3)

    def test_loading_into_an_absent_slot_raises(self):
        with self.assertRaises(ValueError):
            apply_load_and_activate(store(), request(destination_id="RS-9"),
                                    validate_repository_entry(entry()))


class TestAssessment(unittest.TestCase):
    def test_a_clean_request_is_accepted(self):
        result = assess_load_and_activate(repository(), store(), request(), engine())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], VERDICT_LOADED_AND_ACTIVATED)

    def test_an_accepted_request_completes_every_step(self):
        result = assess_load_and_activate(repository(), store(), request(), engine())
        self.assertEqual(result["steps_completed"],
                         [STEP_RESOLVE, STEP_LOAD, STEP_VERIFY, STEP_ACTIVATE])

    def test_an_accepted_request_raises_no_notification(self):
        result = assess_load_and_activate(repository(), store(), request(), engine())
        self.assertIsNone(result["notification"])

    def test_an_accepted_request_carries_the_loaded_length(self):
        result = assess_load_and_activate(repository(), store(), request(), engine())
        self.assertEqual(result["loaded_request_count"], 6)

    def test_a_refusal_names_the_step_that_failed(self):
        result = assess_load_and_activate(repository(), store(), request(landed_checksum=99), engine())
        self.assertEqual(result["verdict"], VERDICT_REFUSED)
        self.assertEqual(result["notification"]["failing_step"], STEP_VERIFY)

    def test_a_verify_failure_rolls_the_load_back(self):
        result = assess_load_and_activate(repository(), store(), request(landed_checksum=99), engine())
        self.assertTrue(result["rolled_back"])
        self.assertEqual(result["resulting_store"][0]["load_state"], "empty")

    def test_an_activation_failure_rolls_the_load_back(self):
        result = assess_load_and_activate(repository(), store(), request(), engine(capacity=1))
        self.assertTrue(result["rolled_back"])
        self.assertEqual(result["resulting_store"][0]["request_count"], 0)

    def test_a_resolve_failure_needs_no_rollback(self):
        result = assess_load_and_activate(repository(), store(), request(reference="SEQ-GHOST"), engine())
        self.assertFalse(result["rolled_back"])

    def test_every_refusal_leaves_the_store_unchanged(self):
        result = assess_load_and_activate(repository(), store(), request(destination_id="RS-3"), engine())
        self.assertTrue(result["store_unchanged"])
        self.assertEqual(result["resulting_store"][2]["request_count"], 9)

    def test_an_acceptance_raises_the_running_total(self):
        result = assess_load_and_activate(repository(), store(), request(), engine())
        self.assertEqual(result["executing_after"], 2)

    def test_a_refusal_does_not_raise_the_running_total(self):
        result = assess_load_and_activate(repository(), store(), request(reference="SEQ-GHOST"), engine())
        self.assertEqual(result["executing_after"], 1)

    def test_the_findings_match_the_refusals(self):
        result = assess_load_and_activate(repository(), store(), request(destination_id="RS-9"), engine())
        self.assertEqual(len(result["findings"]), len(result["refusals"]))

    def test_every_refusal_carries_its_step(self):
        result = assess_load_and_activate(repository(), store(), request(), engine(capacity=1))
        self.assertEqual(result["refusals"][0]["step"], STEP_ACTIVATE)

    def test_an_invalid_store_raises_before_any_decision(self):
        slots = store()
        slots[0]["load_state"] = "molten"
        with self.assertRaises(ValueError):
            assess_load_and_activate(repository(), slots, request(), engine())

    def test_executing_count_reads_the_store(self):
        self.assertEqual(executing_count(store()), 1)


if __name__ == "__main__":
    unittest.main()

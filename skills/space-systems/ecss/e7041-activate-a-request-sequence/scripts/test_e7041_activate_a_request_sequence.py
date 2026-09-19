"""Contract test for the e7041 activate-a-request-sequence leaf."""

import unittest

from e7041_activate_a_request_sequence_logic import (
    REFUSAL_ALREADY_EXECUTING,
    REFUSAL_CHECKSUM_MISMATCH,
    REFUSAL_NOT_FULLY_LOADED,
    REFUSAL_NO_FREE_SLOT,
    REFUSAL_UNKNOWN_SEQUENCE,
    VERDICT_ACTIVATED,
    VERDICT_REFUSED,
    activation_refusals,
    apply_activation,
    assess_activation,
    body_is_intact,
    executing_count,
    find_sequence,
    validate_engine,
    validate_sequence,
    validate_store,
)


def sequence(sid="RS-DEPLOY", load_state="loaded", execution_state="inactive",
             request_count=4, stored=4711, body=4711):
    return {
        "id": sid,
        "load_state": load_state,
        "execution_state": execution_state,
        "request_count": request_count,
        "stored_checksum": stored,
        "body_checksum": body,
    }


def store():
    return [
        sequence("RS-DEPLOY"),
        sequence("RS-SAFE", request_count=7, stored=91, body=91),
        sequence("RS-PARTIAL", load_state="under-load", request_count=2,
                 stored=0, body=0),
    ]


def engine(capacity=2):
    return {"concurrent_capacity": capacity}


class TestValidation(unittest.TestCase):
    def test_a_valid_sequence_normalizes(self):
        record = validate_sequence(sequence())
        self.assertEqual(record["id"], "RS-DEPLOY")
        self.assertEqual(record["request_count"], 4)

    def test_a_non_mapping_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence("RS-DEPLOY")

    def test_a_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(sid="   "))

    def test_an_unknown_load_state_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="half-loaded"))

    def test_an_unknown_execution_state_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(execution_state="paused"))

    def test_a_loaded_sequence_with_no_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(request_count=0))

    def test_an_empty_sequence_carrying_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(load_state="empty", request_count=3))

    def test_executing_while_not_loaded_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(
                sequence(load_state="under-load", execution_state="executing")
            )

    def test_a_negative_request_count_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(request_count=-1))

    def test_a_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence("RS-A"), sequence("RS-A")])

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([]), [])

    def test_a_non_list_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store(sequence())

    def test_a_zero_capacity_engine_raises(self):
        with self.assertRaises(ValueError):
            validate_engine({"concurrent_capacity": 0})

    def test_a_non_integer_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_engine({"concurrent_capacity": "two"})


class TestLookupAndIntegrity(unittest.TestCase):
    def test_a_held_sequence_is_found(self):
        self.assertEqual(find_sequence(store(), "RS-SAFE")["request_count"], 7)

    def test_an_absent_sequence_is_not_found(self):
        self.assertIsNone(find_sequence(store(), "RS-GHOST"))

    def test_a_matching_checksum_is_intact(self):
        self.assertTrue(body_is_intact(sequence()))

    def test_a_drifted_checksum_is_not_intact(self):
        self.assertFalse(body_is_intact(sequence(stored=4711, body=4712)))

    def test_executing_count_reads_the_engine_not_the_request(self):
        records = store()
        records[0]["execution_state"] = "executing"
        self.assertEqual(executing_count(records), 1)


class TestRefusals(unittest.TestCase):
    def test_a_clean_activation_has_no_refusal(self):
        self.assertEqual(activation_refusals(store(), "RS-DEPLOY", engine()), [])

    def test_an_unknown_identifier_is_refused_alone(self):
        refusals = activation_refusals(store(), "RS-GHOST", engine())
        self.assertEqual([item["code"] for item in refusals],
                         [REFUSAL_UNKNOWN_SEQUENCE])

    def test_a_sequence_under_load_is_refused(self):
        refusals = activation_refusals(store(), "RS-PARTIAL", engine())
        self.assertIn(REFUSAL_NOT_FULLY_LOADED, [item["code"] for item in refusals])

    def test_a_running_sequence_cannot_be_activated_again(self):
        records = store()
        records[0]["execution_state"] = "executing"
        refusals = activation_refusals(records, "RS-DEPLOY", engine())
        self.assertIn(REFUSAL_ALREADY_EXECUTING, [item["code"] for item in refusals])

    def test_a_corrupt_body_is_refused_before_release(self):
        records = store()
        records[0]["body_checksum"] = 9999
        refusals = activation_refusals(records, "RS-DEPLOY", engine())
        self.assertIn(REFUSAL_CHECKSUM_MISMATCH, [item["code"] for item in refusals])

    def test_a_full_engine_refuses_a_further_activation(self):
        records = store()
        records[1]["execution_state"] = "executing"
        refusals = activation_refusals(records, "RS-DEPLOY", engine(capacity=1))
        self.assertIn(REFUSAL_NO_FREE_SLOT, [item["code"] for item in refusals])

    def test_capacity_is_not_charged_twice_to_a_running_sequence(self):
        records = store()
        records[0]["execution_state"] = "executing"
        codes = [
            item["code"]
            for item in activation_refusals(records, "RS-DEPLOY", engine(capacity=1))
        ]
        self.assertNotIn(REFUSAL_NO_FREE_SLOT, codes)

    def test_several_refusals_are_all_reported(self):
        records = store()
        records[2]["body_checksum"] = 5
        refusals = activation_refusals(records, "RS-PARTIAL", engine())
        codes = [item["code"] for item in refusals]
        self.assertIn(REFUSAL_NOT_FULLY_LOADED, codes)
        self.assertIn(REFUSAL_CHECKSUM_MISMATCH, codes)


class TestApply(unittest.TestCase):
    def test_activation_marks_the_sequence_executing(self):
        updated = apply_activation(store(), "RS-DEPLOY")
        self.assertEqual(updated[0]["execution_state"], "executing")

    def test_activation_starts_at_the_first_request(self):
        updated = apply_activation(store(), "RS-DEPLOY")
        self.assertEqual(updated[0]["next_request_index"], 1)

    def test_activation_leaves_the_other_sequences_alone(self):
        updated = apply_activation(store(), "RS-DEPLOY")
        self.assertEqual(updated[1]["execution_state"], "inactive")

    def test_activating_an_absent_sequence_raises(self):
        with self.assertRaises(ValueError):
            apply_activation(store(), "RS-GHOST")


class TestAssessment(unittest.TestCase):
    def test_a_clean_request_is_accepted(self):
        result = assess_activation(store(), "RS-DEPLOY", engine())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["verdict"], VERDICT_ACTIVATED)

    def test_an_accepted_request_raises_no_notification(self):
        result = assess_activation(store(), "RS-DEPLOY", engine())
        self.assertIsNone(result["notification"])

    def test_a_refused_request_names_the_sequence_and_the_reason(self):
        result = assess_activation(store(), "RS-GHOST", engine())
        self.assertEqual(result["verdict"], VERDICT_REFUSED)
        self.assertEqual(result["notification"]["sequence_id"], "RS-GHOST")
        self.assertIn(REFUSAL_UNKNOWN_SEQUENCE, result["notification"]["codes"])

    def test_a_refusal_leaves_the_store_unchanged(self):
        result = assess_activation(store(), "RS-PARTIAL", engine())
        self.assertTrue(result["store_unchanged"])
        self.assertEqual(result["resulting_store"][2]["execution_state"], "inactive")

    def test_an_acceptance_increments_the_running_total(self):
        result = assess_activation(store(), "RS-DEPLOY", engine())
        self.assertEqual(result["executing_after"], 1)

    def test_a_refusal_does_not_change_the_running_total(self):
        result = assess_activation(store(), "RS-GHOST", engine())
        self.assertEqual(result["executing_after"], 0)

    def test_every_refusal_detail_reaches_the_findings(self):
        records = store()
        records[2]["body_checksum"] = 5
        result = assess_activation(records, "RS-PARTIAL", engine())
        self.assertEqual(len(result["findings"]), len(result["refusals"]))

    def test_an_invalid_store_raises_before_any_decision(self):
        broken = store()
        broken[0]["load_state"] = "molten"
        with self.assertRaises(ValueError):
            assess_activation(broken, "RS-SAFE", engine())


if __name__ == "__main__":
    unittest.main()

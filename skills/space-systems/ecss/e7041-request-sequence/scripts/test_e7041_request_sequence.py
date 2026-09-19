"""Contract test for the e7041 request-sequence structure and lifecycle leaf."""

import unittest

from e7041_request_sequence_logic import (
    MAX_PAYLOAD_OCTETS,
    OUTCOME_COMPLETED,
    OUTCOME_STOPPED,
    REQUEST_HEADER_OCTETS,
    STATE_ABORTED,
    STATE_ABSENT,
    STATE_EXECUTING,
    STATE_LOADED,
    apply_transition,
    assess_sequence,
    execute_sequence,
    is_self_referencing,
    sequence_fits,
    sequence_size_octets,
    transition_is_allowed,
    validate_request,
    validate_sequence,
    validate_store,
)


def request(service_type=8, subtype=1, payload=10, app="APP-AOCS", target=None):
    record = {
        "application_id": app,
        "service_type": service_type,
        "subtype": subtype,
        "payload_octets": payload,
    }
    if target is not None:
        record["target_sequence_id"] = target
    return record


def sequence(sid="RS-SAFE", requests=None, state=STATE_LOADED):
    return {
        "id": sid,
        "requests": requests if requests is not None else [request(), request(3, 5, 20)],
        "state": state,
    }


class TestRequestValidation(unittest.TestCase):
    def test_a_valid_request_normalizes_and_carries_its_size(self):
        record = validate_request(request(payload=10), "RS-SAFE", 0)
        self.assertEqual(record["size_octets"], 10 + REQUEST_HEADER_OCTETS)

    def test_a_non_mapping_request_raises(self):
        with self.assertRaises(ValueError):
            validate_request(["APP-AOCS"], "RS-SAFE", 0)

    def test_a_zero_service_type_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(service_type=0), "RS-SAFE", 0)

    def test_a_service_type_above_the_field_width_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(service_type=256), "RS-SAFE", 0)

    def test_a_payload_at_the_packet_limit_is_accepted(self):
        record = validate_request(request(payload=MAX_PAYLOAD_OCTETS), "RS-SAFE", 0)
        self.assertEqual(record["payload_octets"], MAX_PAYLOAD_OCTETS)

    def test_a_payload_past_the_packet_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(payload=MAX_PAYLOAD_OCTETS + 1), "RS-SAFE", 0)

    def test_a_blank_application_id_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(app=" "), "RS-SAFE", 0)

    def test_a_boolean_subtype_raises(self):
        with self.assertRaises(ValueError):
            validate_request(request(subtype=True), "RS-SAFE", 0)


class TestSelfReference(unittest.TestCase):
    def test_a_sequencing_request_aimed_at_its_own_sequence_is_self_referencing(self):
        record = validate_request(request(21, 1, 4, target="RS-SAFE"), "RS-SAFE", 0)
        self.assertTrue(is_self_referencing(record, "RS-SAFE"))

    def test_a_sequencing_request_aimed_at_another_sequence_is_not(self):
        record = validate_request(request(21, 1, 4, target="RS-OTHER"), "RS-SAFE", 0)
        self.assertFalse(is_self_referencing(record, "RS-SAFE"))

    def test_a_non_sequencing_request_naming_the_sequence_is_not(self):
        record = validate_request(request(8, 1, 4, target="RS-SAFE"), "RS-SAFE", 0)
        self.assertFalse(is_self_referencing(record, "RS-SAFE"))

    def test_a_sequence_holding_a_self_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(requests=[request(21, 2, 4, target="RS-SAFE")]))


class TestSequenceValidation(unittest.TestCase):
    def test_a_valid_sequence_normalizes(self):
        record = validate_sequence(sequence())
        self.assertEqual(record["id"], "RS-SAFE")
        self.assertEqual(record["request_count"], 2)

    def test_a_sequence_with_no_requests_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(requests=[]))

    def test_a_non_list_request_body_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence({"id": "RS-SAFE", "requests": "one request"})

    def test_a_blank_sequence_id_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(sid=""))

    def test_an_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_sequence(sequence(state="parked"))

    def test_the_held_order_is_preserved(self):
        record = validate_sequence(
            sequence(requests=[request(3, 5, 20), request(8, 1, 10)])
        )
        self.assertEqual([r["service_type"] for r in record["requests"]], [3, 8])

    def test_the_size_sums_every_held_request_with_its_header(self):
        self.assertEqual(sequence_size_octets(sequence()), 10 + 20 + 2 * REQUEST_HEADER_OCTETS)


class TestStoreAndCapacity(unittest.TestCase):
    def test_a_store_inside_its_capacity_normalizes(self):
        store = validate_store([sequence()], 1000)
        self.assertEqual(store["used_octets"], 42)
        self.assertEqual(store["free_octets"], 958)

    def test_a_duplicate_sequence_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence(), sequence()], 1000)

    def test_a_store_over_its_declared_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store([sequence()], 10)

    def test_a_store_exactly_at_its_capacity_is_accepted(self):
        store = validate_store([sequence()], 42)
        self.assertEqual(store["free_octets"], 0)

    def test_a_sequence_exactly_filling_the_free_space_fits(self):
        store = validate_store([sequence()], 100)
        self.assertTrue(sequence_fits(store, 58))

    def test_a_sequence_one_octet_over_the_free_space_does_not_fit(self):
        store = validate_store([sequence()], 100)
        self.assertFalse(sequence_fits(store, 59))

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store([], 500)["used_octets"], 0)


class TestLifecycle(unittest.TestCase):
    def test_an_absent_sequence_can_be_loaded(self):
        self.assertTrue(transition_is_allowed(STATE_ABSENT, STATE_LOADED))

    def test_a_loaded_sequence_can_start_executing(self):
        self.assertTrue(transition_is_allowed(STATE_LOADED, STATE_EXECUTING))

    def test_an_absent_sequence_cannot_start_executing(self):
        self.assertFalse(transition_is_allowed(STATE_ABSENT, STATE_EXECUTING))

    def test_an_executing_sequence_cannot_be_unloaded(self):
        self.assertFalse(transition_is_allowed(STATE_EXECUTING, STATE_ABSENT))

    def test_an_executing_sequence_can_abort(self):
        self.assertEqual(apply_transition(STATE_EXECUTING, STATE_ABORTED), STATE_ABORTED)

    def test_an_illegal_transition_raises(self):
        with self.assertRaises(ValueError):
            apply_transition(STATE_ABSENT, STATE_ABORTED)

    def test_an_unknown_state_in_a_transition_raises(self):
        with self.assertRaises(ValueError):
            transition_is_allowed("parked", STATE_LOADED)


class TestExecution(unittest.TestCase):
    def test_a_clean_run_issues_every_request_in_order(self):
        result = execute_sequence(sequence())
        self.assertEqual(result["outcome"], OUTCOME_COMPLETED)
        self.assertEqual(result["issued"], [0, 1])
        self.assertIsNone(result["stopped_at"])

    def test_a_clean_run_leaves_the_sequence_loaded(self):
        self.assertEqual(execute_sequence(sequence())["end_state"], STATE_LOADED)

    def test_a_failing_request_stops_the_run_at_its_index(self):
        result = execute_sequence(sequence(), failing_indices=[1])
        self.assertEqual(result["outcome"], OUTCOME_STOPPED)
        self.assertEqual(result["stopped_at"], 1)

    def test_a_stopped_run_does_not_issue_the_rest(self):
        record = sequence(requests=[request(), request(3, 5), request(8, 2)])
        result = execute_sequence(record, failing_indices=[1])
        self.assertEqual(result["issued"], [0])
        self.assertEqual(result["remaining"], 2)

    def test_a_stopped_run_reports_one_finding(self):
        result = execute_sequence(sequence(), failing_indices=[0])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["end_state"], STATE_ABORTED)

    def test_only_the_first_failure_matters(self):
        record = sequence(requests=[request(), request(3, 5), request(8, 2)])
        result = execute_sequence(record, failing_indices=[2, 1])
        self.assertEqual(result["stopped_at"], 1)

    def test_a_sequence_that_is_not_loaded_cannot_be_run(self):
        with self.assertRaises(ValueError):
            execute_sequence(sequence(state=STATE_EXECUTING))

    def test_a_negative_failing_index_raises(self):
        with self.assertRaises(ValueError):
            execute_sequence(sequence(), failing_indices=[-1])


class TestAssessment(unittest.TestCase):
    def test_a_well_formed_sequence_with_room_is_acceptable(self):
        store = validate_store([], 1000)
        result = assess_sequence(sequence(), store)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["runnable"])

    def test_a_sequence_whose_identifier_is_held_is_refused(self):
        store = validate_store([sequence()], 1000)
        result = assess_sequence(sequence(), store)
        self.assertFalse(result["acceptable"])

    def test_a_sequence_too_large_for_the_free_space_is_refused(self):
        store = validate_store([], 20)
        result = assess_sequence(sequence(), store)
        self.assertFalse(result["acceptable"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_sequence_assessed_without_a_store_is_structure_only(self):
        result = assess_sequence(sequence())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["size_octets"], 42)

    def test_an_aborted_sequence_is_not_runnable(self):
        self.assertFalse(assess_sequence(sequence(state=STATE_ABORTED))["runnable"])


if __name__ == "__main__":
    unittest.main()

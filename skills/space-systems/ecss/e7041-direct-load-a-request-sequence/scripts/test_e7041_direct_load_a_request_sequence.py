"""Contract test for the e7041 direct-load-a-request-sequence leaf."""

import unittest

from e7041_direct_load_a_request_sequence_logic import (
    LOAD_ACCEPTED,
    LOAD_REFUSED,
    MAX_PAYLOAD_OCTETS,
    REASON_ALREADY_HELD,
    REASON_EMPTY_BODY,
    REASON_INSUFFICIENT_CAPACITY,
    REASON_MALFORMED_REQUEST,
    REASON_SELF_REFERENCE,
    REQUEST_HEADER_OCTETS,
    direct_load_sequence,
    grade_carried_body,
    load_fits,
    request_is_acceptable,
    validate_load_request,
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


def body():
    return [request(), request(3, 5, 20)]


def load(sid="RS-SAFE", requests=None):
    return {"sequence_id": sid, "requests": body() if requests is None else requests}


def store(capacity=1000, held=None):
    return validate_store(held if held is not None else {}, capacity)


def occupied(capacity=1000):
    return validate_store({"RS-HELD": {"size_octets": 100, "request_count": 4}}, capacity)


class TestRequestGrading(unittest.TestCase):
    def test_a_well_formed_request_is_acceptable(self):
        graded = request_is_acceptable(request(), "RS-SAFE")
        self.assertTrue(graded["acceptable"])
        self.assertEqual(graded["size_octets"], 10 + REQUEST_HEADER_OCTETS)

    def test_a_non_mapping_request_is_refused_without_raising(self):
        graded = request_is_acceptable(["APP-AOCS"], "RS-SAFE")
        self.assertFalse(graded["acceptable"])

    def test_a_missing_application_identifier_is_refused(self):
        record = request()
        del record["application_id"]
        self.assertFalse(request_is_acceptable(record, "RS-SAFE")["acceptable"])

    def test_a_service_type_outside_the_field_is_refused(self):
        self.assertFalse(request_is_acceptable(request(service_type=0), "RS-SAFE")["acceptable"])

    def test_a_payload_at_the_packet_limit_is_accepted(self):
        graded = request_is_acceptable(request(payload=MAX_PAYLOAD_OCTETS), "RS-SAFE")
        self.assertTrue(graded["acceptable"])

    def test_a_payload_past_the_packet_limit_is_refused(self):
        graded = request_is_acceptable(request(payload=MAX_PAYLOAD_OCTETS + 1), "RS-SAFE")
        self.assertFalse(graded["acceptable"])

    def test_a_request_targeting_its_own_sequence_is_flagged(self):
        graded = request_is_acceptable(request(21, 1, 4, target="RS-SAFE"), "RS-SAFE")
        self.assertTrue(graded["self_reference"])

    def test_a_request_targeting_another_sequence_is_not_flagged(self):
        graded = request_is_acceptable(request(21, 1, 4, target="RS-OTHER"), "RS-SAFE")
        self.assertFalse(graded["self_reference"])


class TestStoreValidation(unittest.TestCase):
    def test_an_empty_store_has_all_its_capacity_free(self):
        self.assertEqual(store(500)["free_octets"], 500)

    def test_a_held_sequence_consumes_capacity(self):
        self.assertEqual(occupied(1000)["free_octets"], 900)

    def test_a_store_over_its_declared_capacity_raises(self):
        with self.assertRaises(ValueError):
            occupied(50)

    def test_a_store_exactly_at_its_capacity_is_accepted(self):
        self.assertEqual(occupied(100)["free_octets"], 0)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store([], 500)

    def test_a_held_sequence_with_a_zero_size_raises(self):
        with self.assertRaises(ValueError):
            validate_store({"RS-HELD": {"size_octets": 0, "request_count": 1}}, 500)

    def test_a_negative_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store({}, -1)


class TestLoadRequestValidation(unittest.TestCase):
    def test_a_valid_load_request_normalizes(self):
        parsed = validate_load_request(load())
        self.assertEqual(parsed["sequence_id"], "RS-SAFE")
        self.assertEqual(len(parsed["requests"]), 2)

    def test_a_non_mapping_load_raises(self):
        with self.assertRaises(ValueError):
            validate_load_request(["RS-SAFE"])

    def test_a_blank_sequence_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_load_request(load(""))

    def test_a_load_with_no_request_list_raises(self):
        with self.assertRaises(ValueError):
            validate_load_request({"sequence_id": "RS-SAFE"})


class TestBodyGrading(unittest.TestCase):
    def test_a_clean_body_is_acceptable_and_sized_with_headers(self):
        graded = grade_carried_body("RS-SAFE", body())
        self.assertTrue(graded["acceptable"])
        self.assertEqual(graded["size_octets"], 10 + 20 + 2 * REQUEST_HEADER_OCTETS)

    def test_an_empty_body_is_refused(self):
        graded = grade_carried_body("RS-SAFE", [])
        self.assertFalse(graded["acceptable"])
        self.assertIn(REASON_EMPTY_BODY, graded["reasons"])

    def test_one_malformed_request_fails_the_whole_body(self):
        graded = grade_carried_body("RS-SAFE", [request(), request(service_type=0)])
        self.assertFalse(graded["acceptable"])
        self.assertIn(REASON_MALFORMED_REQUEST, graded["reasons"])

    def test_a_self_referencing_body_is_refused(self):
        graded = grade_carried_body("RS-SAFE", [request(21, 2, 4, target="RS-SAFE")])
        self.assertFalse(graded["acceptable"])
        self.assertIn(REASON_SELF_REFERENCE, graded["reasons"])

    def test_the_finding_names_the_offending_position(self):
        graded = grade_carried_body("RS-SAFE", [request(), request(service_type=0)])
        self.assertTrue(graded["findings"][0].startswith("request 1:"))

    def test_the_request_count_is_the_carried_count(self):
        self.assertEqual(grade_carried_body("RS-SAFE", body())["request_count"], 2)


class TestCapacityFit(unittest.TestCase):
    def test_a_load_exactly_filling_the_free_space_fits(self):
        self.assertTrue(load_fits(occupied(142), 42))

    def test_a_load_one_octet_over_the_free_space_does_not_fit(self):
        self.assertFalse(load_fits(occupied(142), 43))

    def test_a_negative_load_size_raises(self):
        with self.assertRaises(ValueError):
            load_fits(store(), -1)


class TestDirectLoad(unittest.TestCase):
    def test_a_clean_load_is_accepted_and_holds_the_sequence(self):
        result = direct_load_sequence(store(), load())
        self.assertEqual(result["verdict"], LOAD_ACCEPTED)
        self.assertIn("RS-SAFE", result["store"]["sequences"])
        self.assertTrue(result["store_changed"])

    def test_a_clean_load_spends_exactly_the_loaded_size(self):
        result = direct_load_sequence(store(1000), load())
        self.assertEqual(result["loaded_size_octets"], 42)
        self.assertEqual(result["store"]["free_octets"], 958)

    def test_the_carried_order_becomes_the_held_count(self):
        result = direct_load_sequence(store(), load(requests=[request(), request(3, 5), request(8, 2)]))
        self.assertEqual(result["store"]["sequences"]["RS-SAFE"]["request_count"], 3)

    def test_a_load_over_a_held_identifier_is_refused(self):
        held = validate_store({"RS-SAFE": {"size_octets": 40, "request_count": 2}}, 1000)
        result = direct_load_sequence(held, load())
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertIn(REASON_ALREADY_HELD, result["reasons"])

    def test_a_refused_load_leaves_the_store_untouched(self):
        held = validate_store({"RS-SAFE": {"size_octets": 40, "request_count": 2}}, 1000)
        result = direct_load_sequence(held, load())
        self.assertFalse(result["store_changed"])
        self.assertEqual(result["store"]["free_octets"], 960)

    def test_an_empty_body_is_refused(self):
        result = direct_load_sequence(store(), load(requests=[]))
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertIn(REASON_EMPTY_BODY, result["reasons"])

    def test_one_bad_request_fails_the_whole_load(self):
        result = direct_load_sequence(store(), load(requests=[request(), request(subtype=0)]))
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertFalse(result["store_changed"])

    def test_a_load_larger_than_the_free_space_is_refused(self):
        result = direct_load_sequence(store(20), load())
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertIn(REASON_INSUFFICIENT_CAPACITY, result["reasons"])

    def test_a_load_exactly_filling_the_store_is_accepted(self):
        result = direct_load_sequence(store(42), load())
        self.assertEqual(result["verdict"], LOAD_ACCEPTED)
        self.assertEqual(result["store"]["free_octets"], 0)

    def test_a_self_referencing_load_is_refused(self):
        result = direct_load_sequence(store(), load(requests=[request(21, 1, 4, target="RS-SAFE")]))
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertIn(REASON_SELF_REFERENCE, result["reasons"])

    def test_a_load_naming_another_sequence_is_accepted(self):
        result = direct_load_sequence(store(), load(requests=[request(21, 1, 4, target="RS-OTHER")]))
        self.assertEqual(result["verdict"], LOAD_ACCEPTED)

    def test_several_refusal_reasons_are_all_reported(self):
        held = validate_store({"RS-SAFE": {"size_octets": 40, "request_count": 2}}, 1000)
        result = direct_load_sequence(held, load(requests=[request(subtype=0)]))
        self.assertIn(REASON_ALREADY_HELD, result["reasons"])
        self.assertIn(REASON_MALFORMED_REQUEST, result["reasons"])

    def test_a_second_load_of_a_different_sequence_stacks(self):
        first = direct_load_sequence(store(1000), load())
        second = direct_load_sequence(first["store"], load("RS-DEORBIT"))
        self.assertEqual(second["verdict"], LOAD_ACCEPTED)
        self.assertEqual(second["store"]["used_octets"], 84)


if __name__ == "__main__":
    unittest.main()

"""Contract test for the e7041 load-a-request-sequence-by-reference leaf."""

import unittest

from e7041_load_a_request_sequence_by_reference_logic import (
    LOAD_ACCEPTED,
    LOAD_REFUSED,
    MAX_PAYLOAD_OCTETS,
    ORIGIN_BY_REFERENCE,
    REASON_ALREADY_HELD,
    REASON_AMBIGUOUS_REFERENCE,
    REASON_EMPTY_CONTENT,
    REASON_INSUFFICIENT_CAPACITY,
    REASON_MALFORMED_REQUEST,
    REASON_SELF_REFERENCE,
    REASON_UNREADABLE_SOURCE,
    REASON_UNRESOLVED_REFERENCE,
    REQUEST_HEADER_OCTETS,
    grade_resolved_content,
    load_fits,
    load_sequence_by_reference,
    request_is_acceptable,
    resolve_reference,
    validate_load_request,
    validate_repository,
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


def content():
    return [request(), request(3, 5, 20)]


def repository(entries=None):
    if entries is not None:
        return entries
    return [{"reference": "REPO/SAFE-V4", "content": content(), "readable": True}]


def load(sid="RS-SAFE", reference="REPO/SAFE-V4", declared=None):
    record = {"sequence_id": sid, "reference": reference}
    if declared is not None:
        record["declared_size_octets"] = declared
    return record


def store(capacity=1000, held=None):
    return validate_store(held if held is not None else {}, capacity)


class TestRepositoryValidation(unittest.TestCase):
    def test_a_valid_repository_normalizes(self):
        sources = validate_repository(repository())
        self.assertEqual(sources[0]["reference"], "REPO/SAFE-V4")

    def test_a_non_list_repository_raises(self):
        with self.assertRaises(ValueError):
            validate_repository({"reference": "REPO/SAFE-V4"})

    def test_an_entry_without_a_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_repository([{"content": content()}])

    def test_a_non_list_content_field_raises(self):
        with self.assertRaises(ValueError):
            validate_repository([{"reference": "REPO/X", "content": "one request"}])

    def test_a_non_boolean_readable_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_repository([{"reference": "REPO/X", "content": [], "readable": "yes"}])


class TestReferenceResolution(unittest.TestCase):
    def test_a_held_reference_resolves_to_one_source(self):
        resolution = resolve_reference(repository(), "REPO/SAFE-V4")
        self.assertTrue(resolution["resolved"])
        self.assertEqual(resolution["match_count"], 1)

    def test_a_dangling_reference_does_not_resolve(self):
        resolution = resolve_reference(repository(), "REPO/GHOST")
        self.assertFalse(resolution["resolved"])
        self.assertEqual(resolution["reason"], REASON_UNRESOLVED_REFERENCE)

    def test_an_ambiguous_reference_is_refused(self):
        entries = repository() + repository()
        resolution = resolve_reference(entries, "REPO/SAFE-V4")
        self.assertFalse(resolution["resolved"])
        self.assertEqual(resolution["reason"], REASON_AMBIGUOUS_REFERENCE)
        self.assertEqual(resolution["match_count"], 2)

    def test_an_unreadable_source_is_refused(self):
        entries = [{"reference": "REPO/SAFE-V4", "content": content(), "readable": False}]
        resolution = resolve_reference(entries, "REPO/SAFE-V4")
        self.assertEqual(resolution["reason"], REASON_UNREADABLE_SOURCE)

    def test_a_source_with_no_content_at_all_is_unreadable(self):
        entries = [{"reference": "REPO/SAFE-V4", "readable": True}]
        self.assertEqual(
            resolve_reference(entries, "REPO/SAFE-V4")["reason"], REASON_UNREADABLE_SOURCE
        )

    def test_a_blank_reference_raises(self):
        with self.assertRaises(ValueError):
            resolve_reference(repository(), "  ")


class TestResolvedRequestGrading(unittest.TestCase):
    def test_a_well_formed_request_is_acceptable(self):
        graded = request_is_acceptable(request(), "RS-SAFE")
        self.assertTrue(graded["acceptable"])
        self.assertEqual(graded["size_octets"], 10 + REQUEST_HEADER_OCTETS)

    def test_a_non_mapping_request_is_refused_without_raising(self):
        self.assertFalse(request_is_acceptable("APP-AOCS", "RS-SAFE")["acceptable"])

    def test_a_subtype_outside_the_field_is_refused(self):
        self.assertFalse(request_is_acceptable(request(subtype=300), "RS-SAFE")["acceptable"])

    def test_a_payload_at_the_packet_limit_is_accepted(self):
        self.assertTrue(
            request_is_acceptable(request(payload=MAX_PAYLOAD_OCTETS), "RS-SAFE")["acceptable"]
        )

    def test_a_payload_past_the_packet_limit_is_refused(self):
        self.assertFalse(
            request_is_acceptable(request(payload=MAX_PAYLOAD_OCTETS + 1), "RS-SAFE")["acceptable"]
        )

    def test_a_request_targeting_its_own_sequence_is_flagged(self):
        self.assertTrue(
            request_is_acceptable(request(21, 3, 4, target="RS-SAFE"), "RS-SAFE")["self_reference"]
        )

    def test_a_request_targeting_another_sequence_is_not_flagged(self):
        self.assertFalse(
            request_is_acceptable(request(21, 3, 4, target="RS-OTHER"), "RS-SAFE")["self_reference"]
        )


class TestContentGrading(unittest.TestCase):
    def test_clean_content_is_acceptable_and_sized_with_headers(self):
        graded = grade_resolved_content("RS-SAFE", content())
        self.assertTrue(graded["acceptable"])
        self.assertEqual(graded["size_octets"], 10 + 20 + 2 * REQUEST_HEADER_OCTETS)

    def test_empty_content_is_refused(self):
        graded = grade_resolved_content("RS-SAFE", [])
        self.assertEqual(graded["reasons"], [REASON_EMPTY_CONTENT])

    def test_one_malformed_request_fails_the_whole_content(self):
        graded = grade_resolved_content("RS-SAFE", [request(), request(service_type=0)])
        self.assertFalse(graded["acceptable"])
        self.assertIn(REASON_MALFORMED_REQUEST, graded["reasons"])

    def test_self_referencing_content_is_refused(self):
        graded = grade_resolved_content("RS-SAFE", [request(21, 1, 4, target="RS-SAFE")])
        self.assertIn(REASON_SELF_REFERENCE, graded["reasons"])

    def test_the_finding_names_the_offending_position(self):
        graded = grade_resolved_content("RS-SAFE", [request(), request(subtype=0)])
        self.assertTrue(graded["findings"][0].startswith("request 1:"))


class TestStoreAndFit(unittest.TestCase):
    def test_an_empty_store_has_all_its_capacity_free(self):
        self.assertEqual(store(500)["free_octets"], 500)

    def test_a_store_over_its_declared_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store({"RS-HELD": {"size_octets": 100, "request_count": 2}}, 50)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store([], 500)

    def test_content_exactly_filling_the_free_space_fits(self):
        self.assertTrue(load_fits(store(42), 42))

    def test_content_one_octet_over_the_free_space_does_not_fit(self):
        self.assertFalse(load_fits(store(42), 43))


class TestLoadRequestValidation(unittest.TestCase):
    def test_a_valid_load_request_normalizes(self):
        parsed = validate_load_request(load())
        self.assertEqual(parsed["reference"], "REPO/SAFE-V4")
        self.assertIsNone(parsed["declared_size_octets"])

    def test_a_load_without_a_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_load_request({"sequence_id": "RS-SAFE"})

    def test_a_non_mapping_load_raises(self):
        with self.assertRaises(ValueError):
            validate_load_request(["RS-SAFE"])

    def test_a_negative_declared_size_raises(self):
        with self.assertRaises(ValueError):
            validate_load_request(load(declared=-1))


class TestLoadByReference(unittest.TestCase):
    def test_a_clean_load_is_accepted_and_holds_the_sequence(self):
        result = load_sequence_by_reference(store(), repository(), load())
        self.assertEqual(result["verdict"], LOAD_ACCEPTED)
        self.assertIn("RS-SAFE", result["store"]["sequences"])

    def test_a_loaded_sequence_records_the_source_it_came_from(self):
        result = load_sequence_by_reference(store(), repository(), load())
        entry = result["store"]["sequences"]["RS-SAFE"]
        self.assertEqual(entry["origin"], ORIGIN_BY_REFERENCE)
        self.assertEqual(entry["source_reference"], "REPO/SAFE-V4")

    def test_a_clean_load_spends_exactly_the_resolved_size(self):
        result = load_sequence_by_reference(store(1000), repository(), load())
        self.assertEqual(result["loaded_size_octets"], 42)
        self.assertEqual(result["store"]["free_octets"], 958)

    def test_a_dangling_reference_refuses_the_load(self):
        result = load_sequence_by_reference(store(), repository(), load(reference="REPO/GHOST"))
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertIn(REASON_UNRESOLVED_REFERENCE, result["reasons"])
        self.assertFalse(result["store_changed"])

    def test_an_ambiguous_reference_refuses_the_load(self):
        result = load_sequence_by_reference(store(), repository() + repository(), load())
        self.assertIn(REASON_AMBIGUOUS_REFERENCE, result["reasons"])

    def test_a_load_over_a_held_identifier_is_refused(self):
        held = validate_store({"RS-SAFE": {"size_octets": 40, "request_count": 2}}, 1000)
        result = load_sequence_by_reference(held, repository(), load())
        self.assertIn(REASON_ALREADY_HELD, result["reasons"])
        self.assertFalse(result["store_changed"])

    def test_the_capacity_check_uses_the_resolved_size_not_the_declared_one(self):
        result = load_sequence_by_reference(store(20), repository(), load(declared=1))
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertIn(REASON_INSUFFICIENT_CAPACITY, result["reasons"])

    def test_content_exactly_filling_the_store_is_accepted(self):
        result = load_sequence_by_reference(store(42), repository(), load())
        self.assertEqual(result["verdict"], LOAD_ACCEPTED)
        self.assertEqual(result["store"]["free_octets"], 0)

    def test_malformed_resolved_content_refuses_the_whole_load(self):
        entries = [{"reference": "REPO/SAFE-V4", "content": [request(), request(subtype=0)]}]
        result = load_sequence_by_reference(store(), entries, load())
        self.assertEqual(result["verdict"], LOAD_REFUSED)
        self.assertFalse(result["store_changed"])

    def test_empty_resolved_content_refuses_the_load(self):
        entries = [{"reference": "REPO/SAFE-V4", "content": []}]
        result = load_sequence_by_reference(store(), entries, load())
        self.assertIn(REASON_EMPTY_CONTENT, result["reasons"])

    def test_self_referencing_resolved_content_refuses_the_load(self):
        entries = [{"reference": "REPO/SAFE-V4", "content": [request(21, 2, 4, target="RS-SAFE")]}]
        result = load_sequence_by_reference(store(), entries, load())
        self.assertIn(REASON_SELF_REFERENCE, result["reasons"])

    def test_an_unresolved_reference_reports_before_grading_content(self):
        held = validate_store({"RS-SAFE": {"size_octets": 40, "request_count": 2}}, 1000)
        result = load_sequence_by_reference(held, repository(), load(reference="REPO/GHOST"))
        self.assertIn(REASON_ALREADY_HELD, result["reasons"])
        self.assertIn(REASON_UNRESOLVED_REFERENCE, result["reasons"])
        self.assertFalse(result["resolved"])

    def test_the_same_source_can_load_a_second_sequence(self):
        first = load_sequence_by_reference(store(1000), repository(), load())
        second = load_sequence_by_reference(first["store"], repository(), load("RS-SAFE-B"))
        self.assertEqual(second["verdict"], LOAD_ACCEPTED)
        self.assertEqual(second["store"]["used_octets"], 84)


if __name__ == "__main__":
    unittest.main()

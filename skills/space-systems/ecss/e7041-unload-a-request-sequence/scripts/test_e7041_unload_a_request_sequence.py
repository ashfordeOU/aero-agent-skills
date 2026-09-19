"""Contract test for the e7041 unload-a-request-sequence leaf."""

import unittest

from e7041_unload_a_request_sequence_logic import (
    REASON_EXECUTING,
    REASON_NOT_HELD,
    STATE_ABORTED,
    STATE_EXECUTING,
    STATE_LOADED,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    VERDICT_REJECTED,
    identifier_is_free,
    released_capacity,
    sequence_is_unloadable,
    unload_sequences,
    validate_held_sequence,
    validate_store,
    validate_unload_request,
)


def held(size=100, count=4, state=STATE_LOADED):
    return {"size_octets": size, "request_count": count, "state": state}


def store(capacity=1000, sequences=None):
    if sequences is None:
        sequences = {
            "RS-SAFE": held(100, 4),
            "RS-DEORBIT": held(250, 9),
            "RS-RUNNING": held(60, 3, STATE_EXECUTING),
        }
    return validate_store(sequences, capacity)


class TestHeldSequenceValidation(unittest.TestCase):
    def test_a_valid_held_sequence_normalizes(self):
        record = validate_held_sequence("RS-SAFE", held())
        self.assertEqual(record["size_octets"], 100)
        self.assertEqual(record["state"], STATE_LOADED)

    def test_a_non_mapping_held_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_held_sequence("RS-SAFE", [100])

    def test_a_zero_size_held_sequence_raises(self):
        with self.assertRaises(ValueError):
            validate_held_sequence("RS-SAFE", held(size=0))

    def test_a_boolean_size_raises(self):
        with self.assertRaises(ValueError):
            validate_held_sequence("RS-SAFE", held(size=True))

    def test_an_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_held_sequence("RS-SAFE", held(state="parked"))

    def test_a_held_sequence_defaults_to_loaded(self):
        record = validate_held_sequence("RS-SAFE", {"size_octets": 10, "request_count": 1})
        self.assertEqual(record["state"], STATE_LOADED)


class TestStoreValidation(unittest.TestCase):
    def test_a_store_sums_what_it_holds(self):
        self.assertEqual(store()["used_octets"], 410)

    def test_a_store_reports_its_free_capacity(self):
        self.assertEqual(store(1000)["free_octets"], 590)

    def test_a_store_over_its_declared_capacity_raises(self):
        with self.assertRaises(ValueError):
            store(100)

    def test_a_store_exactly_at_its_capacity_is_accepted(self):
        self.assertEqual(store(410)["free_octets"], 0)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store([], 500)

    def test_an_empty_store_is_valid(self):
        self.assertEqual(validate_store({}, 500)["used_octets"], 0)


class TestUnloadRequestValidation(unittest.TestCase):
    def test_a_bare_identifier_is_accepted(self):
        self.assertEqual(validate_unload_request("RS-SAFE"), ["RS-SAFE"])

    def test_a_list_of_identifiers_is_accepted(self):
        self.assertEqual(
            validate_unload_request(["RS-SAFE", "RS-DEORBIT"]), ["RS-SAFE", "RS-DEORBIT"]
        )

    def test_a_mapping_request_yields_its_identifier_list(self):
        self.assertEqual(validate_unload_request({"sequence_ids": ["RS-SAFE"]}), ["RS-SAFE"])

    def test_an_empty_request_raises(self):
        with self.assertRaises(ValueError):
            validate_unload_request([])

    def test_a_repeated_name_raises(self):
        with self.assertRaises(ValueError):
            validate_unload_request(["RS-SAFE", "RS-SAFE"])

    def test_a_blank_name_raises(self):
        with self.assertRaises(ValueError):
            validate_unload_request(["  "])

    def test_the_named_order_is_preserved(self):
        self.assertEqual(
            validate_unload_request(["RS-DEORBIT", "RS-SAFE"]), ["RS-DEORBIT", "RS-SAFE"]
        )


class TestPerNameDecision(unittest.TestCase):
    def test_a_loaded_sequence_is_unloadable(self):
        outcome = sequence_is_unloadable(store(), "RS-SAFE")
        self.assertTrue(outcome["unloadable"])
        self.assertEqual(outcome["released_octets"], 100)

    def test_an_absent_sequence_is_refused_not_a_no_op(self):
        outcome = sequence_is_unloadable(store(), "RS-GHOST")
        self.assertFalse(outcome["unloadable"])
        self.assertEqual(outcome["reason"], REASON_NOT_HELD)

    def test_an_executing_sequence_is_refused(self):
        outcome = sequence_is_unloadable(store(), "RS-RUNNING")
        self.assertFalse(outcome["unloadable"])
        self.assertEqual(outcome["reason"], REASON_EXECUTING)

    def test_an_aborted_sequence_is_unloadable(self):
        current = store(1000, {"RS-STOPPED": held(80, 2, STATE_ABORTED)})
        self.assertTrue(sequence_is_unloadable(current, "RS-STOPPED")["unloadable"])

    def test_a_refused_name_releases_nothing(self):
        self.assertEqual(sequence_is_unloadable(store(), "RS-RUNNING")["released_octets"], 0)

    def test_a_blank_name_raises(self):
        with self.assertRaises(ValueError):
            sequence_is_unloadable(store(), " ")

    def test_released_capacity_sums_only_the_unloadable_names(self):
        self.assertEqual(
            released_capacity(store(), ["RS-SAFE", "RS-RUNNING", "RS-GHOST"]), 100
        )


class TestUnload(unittest.TestCase):
    def test_a_single_clean_unload_is_accepted(self):
        result = unload_sequences(store(), "RS-SAFE")
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["unloaded"], ["RS-SAFE"])

    def test_an_unload_releases_exactly_the_space_it_occupied(self):
        current = store(1000)
        result = unload_sequences(current, "RS-SAFE")
        self.assertEqual(result["released_octets"], 100)
        self.assertEqual(result["store"]["free_octets"], current["free_octets"] + 100)

    def test_the_identifier_is_free_afterwards(self):
        result = unload_sequences(store(), "RS-SAFE")
        self.assertTrue(identifier_is_free(result["store"], "RS-SAFE"))

    def test_the_identifier_is_not_free_before(self):
        self.assertFalse(identifier_is_free(store(), "RS-SAFE"))

    def test_the_other_sequences_survive(self):
        result = unload_sequences(store(), "RS-SAFE")
        self.assertIn("RS-DEORBIT", result["store"]["sequences"])
        self.assertIn("RS-RUNNING", result["store"]["sequences"])

    def test_unloading_an_absent_sequence_is_rejected(self):
        result = unload_sequences(store(), "RS-GHOST")
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertFalse(result["store_changed"])

    def test_unloading_an_executing_sequence_is_rejected(self):
        result = unload_sequences(store(), "RS-RUNNING")
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertIn("RS-RUNNING", result["store"]["sequences"])

    def test_a_mixed_unload_is_partially_accepted(self):
        result = unload_sequences(store(), ["RS-SAFE", "RS-RUNNING"])
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["unloaded"], ["RS-SAFE"])
        self.assertEqual(result["refused"], ["RS-RUNNING"])

    def test_a_mixed_unload_releases_only_the_accepted_space(self):
        result = unload_sequences(store(1000), ["RS-SAFE", "RS-RUNNING", "RS-GHOST"])
        self.assertEqual(result["released_octets"], 100)
        self.assertEqual(result["store"]["used_octets"], 310)

    def test_every_refused_name_is_reported(self):
        result = unload_sequences(store(), ["RS-SAFE", "RS-RUNNING", "RS-GHOST"])
        self.assertEqual(len(result["findings"]), 2)

    def test_unloading_everything_unloadable_empties_the_used_space_it_can(self):
        result = unload_sequences(store(1000), ["RS-SAFE", "RS-DEORBIT"])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["store"]["used_octets"], 60)

    def test_a_repeated_name_raises(self):
        with self.assertRaises(ValueError):
            unload_sequences(store(), ["RS-SAFE", "RS-SAFE"])

    def test_an_empty_unload_request_raises(self):
        with self.assertRaises(ValueError):
            unload_sequences(store(), [])

    def test_a_second_unload_of_the_same_name_is_rejected(self):
        first = unload_sequences(store(), "RS-SAFE")
        second = unload_sequences(first["store"], "RS-SAFE")
        self.assertEqual(second["verdict"], VERDICT_REJECTED)
        self.assertEqual(second["released_octets"], 0)

    def test_every_name_gets_its_own_outcome(self):
        result = unload_sequences(store(), ["RS-SAFE", "RS-GHOST"])
        self.assertEqual(len(result["outcomes"]), 2)

    def test_the_capacity_is_unchanged_by_an_unload(self):
        result = unload_sequences(store(1000), "RS-SAFE")
        self.assertEqual(result["store"]["capacity_octets"], 1000)


if __name__ == "__main__":
    unittest.main()

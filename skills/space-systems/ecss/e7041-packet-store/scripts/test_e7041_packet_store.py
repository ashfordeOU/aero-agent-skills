"""Contract test for the packet store leaf (stdlib unittest)."""

import unittest

from e7041_packet_store_logic import (
    OUTCOME_DISCARDED_OPEN_RETRIEVAL,
    OUTCOME_DISCARDED_STORAGE_DISABLED,
    OUTCOME_DISCARDED_STORE_FULL,
    OUTCOME_STORED,
    OUTCOME_STORED_AFTER_OVERWRITE,
    STORAGE_DISABLED,
    STORAGE_ENABLED,
    STORE_TYPE_BOUNDED,
    STORE_TYPE_CIRCULAR,
    advance_retrieval,
    assess_packet_store_set,
    close_retrieval,
    create_store,
    fill_fraction,
    free_octets,
    is_full,
    open_retrieval,
    packet_fits_in_capacity,
    report_store_status,
    set_storage_state,
    store_packet,
    store_packets,
    used_octets,
    validate_packet,
    validate_store_definition,
)


def definition(store_id="PS-1", store_type=STORE_TYPE_BOUNDED, capacity=400, **kw):
    record = {"id": store_id, "type": store_type, "capacity_octets": capacity}
    record.update(kw)
    return record


def packet(packet_id="P-1", size=100):
    return {"id": packet_id, "size_octets": size}


def filled(store_type=STORE_TYPE_BOUNDED, capacity=400, size=100, count=4):
    store = create_store(definition(store_type=store_type, capacity=capacity))
    store, _ = store_packets(
        store, [packet("P-%d" % n, size) for n in range(1, count + 1)]
    )
    return store


class TestDefinitionValidation(unittest.TestCase):
    def test_unknown_store_type_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(definition(store_type="ring-buffer"))

    def test_empty_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(definition(""))

    def test_zero_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(definition(capacity=0))

    def test_boolean_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(definition(capacity=True))

    def test_unknown_storage_state_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(definition(storage_state="paused"))

    def test_storage_defaults_to_enabled(self):
        self.assertEqual(
            validate_store_definition(definition())["storage_state"], STORAGE_ENABLED
        )

    def test_zero_size_packet_raises(self):
        with self.assertRaises(ValueError):
            validate_packet(packet(size=0))

    def test_packet_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_packet(["P-1", 100])


class TestOccupancy(unittest.TestCase):
    def test_new_store_is_empty(self):
        store = create_store(definition())
        self.assertEqual(used_octets(store), 0)
        self.assertEqual(free_octets(store), 400)
        self.assertFalse(is_full(store))

    def test_stored_packets_occupy_their_size(self):
        store, outcomes = store_packets(
            create_store(definition()), [packet("P-1", 100), packet("P-2", 250)]
        )
        self.assertEqual([o["outcome"] for o in outcomes], [OUTCOME_STORED] * 2)
        self.assertEqual(used_octets(store), 350)
        self.assertEqual(free_octets(store), 50)

    def test_fill_fraction_is_exact_when_the_store_is_full(self):
        store = filled()
        self.assertAlmostEqual(fill_fraction(store), 1.0, places=9)
        self.assertTrue(is_full(store))

    def test_fill_fraction_of_an_empty_store_is_zero(self):
        self.assertAlmostEqual(fill_fraction(create_store(definition())), 0.0, places=9)

    def test_a_packet_larger_than_the_capacity_never_fits(self):
        store = create_store(definition(capacity=200))
        self.assertFalse(packet_fits_in_capacity(store, packet(size=201)))
        with self.assertRaises(ValueError):
            store_packet(store, packet(size=201))

    def test_a_packet_exactly_the_capacity_fits(self):
        store = create_store(definition(capacity=200))
        self.assertTrue(packet_fits_in_capacity(store, packet(size=200)))
        store, outcome = store_packet(store, packet(size=200))
        self.assertEqual(outcome, OUTCOME_STORED)
        self.assertTrue(is_full(store))


class TestStorageState(unittest.TestCase):
    def test_disabled_store_discards_without_storing(self):
        store = create_store(definition(storage_state=STORAGE_DISABLED))
        store, outcome = store_packet(store, packet())
        self.assertEqual(outcome, OUTCOME_DISCARDED_STORAGE_DISABLED)
        self.assertEqual(used_octets(store), 0)
        self.assertEqual(store["discarded_count"], 1)

    def test_disabling_storage_keeps_the_content(self):
        store = filled(count=2)
        store = set_storage_state(store, STORAGE_DISABLED)
        self.assertEqual(used_octets(store), 200)
        store, outcome = store_packet(store, packet("P-9"))
        self.assertEqual(outcome, OUTCOME_DISCARDED_STORAGE_DISABLED)
        self.assertEqual(used_octets(store), 200)

    def test_re_enabling_storage_accepts_again(self):
        store = set_storage_state(
            create_store(definition(storage_state=STORAGE_DISABLED)), STORAGE_ENABLED
        )
        store, outcome = store_packet(store, packet())
        self.assertEqual(outcome, OUTCOME_STORED)

    def test_unknown_storage_state_raises(self):
        with self.assertRaises(ValueError):
            set_storage_state(create_store(definition()), "standby")


class TestBoundedStore(unittest.TestCase):
    def test_full_bounded_store_keeps_the_oldest_and_loses_the_newest(self):
        store = filled(STORE_TYPE_BOUNDED)
        store, outcome = store_packet(store, packet("P-NEW"))
        self.assertEqual(outcome, OUTCOME_DISCARDED_STORE_FULL)
        status = report_store_status(store)
        self.assertEqual(status["oldest_packet_id"], "P-1")
        self.assertEqual(status["newest_packet_id"], "P-4")
        self.assertEqual(status["discarded_count"], 1)
        self.assertEqual(status["overwritten_count"], 0)

    def test_a_bounded_store_takes_a_packet_that_still_fits(self):
        store = filled(STORE_TYPE_BOUNDED, capacity=450)
        store, outcome = store_packet(store, packet("P-5", 50))
        self.assertEqual(outcome, OUTCOME_STORED)
        self.assertTrue(is_full(store))


class TestCircularStore(unittest.TestCase):
    def test_full_circular_store_overwrites_the_oldest(self):
        store = filled(STORE_TYPE_CIRCULAR)
        store, outcome = store_packet(store, packet("P-NEW"))
        self.assertEqual(outcome, OUTCOME_STORED_AFTER_OVERWRITE)
        status = report_store_status(store)
        self.assertEqual(status["oldest_packet_id"], "P-2")
        self.assertEqual(status["newest_packet_id"], "P-NEW")
        self.assertEqual(status["overwritten_count"], 1)
        self.assertEqual(status["packet_count"], 4)

    def test_a_large_packet_overwrites_as_many_as_it_needs(self):
        store = filled(STORE_TYPE_CIRCULAR)
        store, outcome = store_packet(store, packet("P-BIG", 250))
        self.assertEqual(outcome, OUTCOME_STORED_AFTER_OVERWRITE)
        status = report_store_status(store)
        self.assertEqual(status["oldest_packet_id"], "P-4")
        self.assertEqual(status["overwritten_count"], 3)
        self.assertEqual(status["packet_count"], 2)

    def test_the_two_types_lose_opposite_ends_of_the_record(self):
        bounded, _ = store_packet(filled(STORE_TYPE_BOUNDED), packet("P-NEW"))
        circular, _ = store_packet(filled(STORE_TYPE_CIRCULAR), packet("P-NEW"))
        self.assertEqual(report_store_status(bounded)["newest_packet_id"], "P-4")
        self.assertEqual(report_store_status(circular)["newest_packet_id"], "P-NEW")
        self.assertEqual(report_store_status(bounded)["oldest_packet_id"], "P-1")
        self.assertEqual(report_store_status(circular)["oldest_packet_id"], "P-2")


class TestOpenRetrieval(unittest.TestCase):
    def test_overwrite_is_blocked_by_an_unread_open_retrieval(self):
        store = open_retrieval(filled(STORE_TYPE_CIRCULAR))
        store, outcome = store_packet(store, packet("P-NEW"))
        self.assertEqual(outcome, OUTCOME_DISCARDED_OPEN_RETRIEVAL)
        status = report_store_status(store)
        self.assertEqual(status["packet_count"], 4)
        self.assertEqual(status["oldest_packet_id"], "P-1")
        self.assertEqual(status["overwritten_count"], 0)
        self.assertEqual(status["discarded_count"], 1)

    def test_overwrite_resumes_over_packets_the_ground_already_has(self):
        store = advance_retrieval(open_retrieval(filled(STORE_TYPE_CIRCULAR)), 2)
        store, outcome = store_packet(store, packet("P-NEW"))
        self.assertEqual(outcome, OUTCOME_STORED_AFTER_OVERWRITE)
        self.assertEqual(report_store_status(store)["oldest_packet_id"], "P-2")
        self.assertEqual(store["open_retrieval_index"], 1)

    def test_closing_the_retrieval_frees_the_content_for_overwrite(self):
        store = close_retrieval(open_retrieval(filled(STORE_TYPE_CIRCULAR)))
        store, outcome = store_packet(store, packet("P-NEW"))
        self.assertEqual(outcome, OUTCOME_STORED_AFTER_OVERWRITE)
        self.assertFalse(report_store_status(store)["open_retrieval"])

    def test_opening_a_second_retrieval_raises(self):
        store = open_retrieval(filled(STORE_TYPE_CIRCULAR))
        with self.assertRaises(ValueError):
            open_retrieval(store)

    def test_closing_without_an_open_retrieval_raises(self):
        with self.assertRaises(ValueError):
            close_retrieval(filled(STORE_TYPE_CIRCULAR))

    def test_advancing_past_the_content_raises(self):
        store = open_retrieval(filled(STORE_TYPE_CIRCULAR))
        with self.assertRaises(ValueError):
            advance_retrieval(store, 5)

    def test_an_open_retrieval_does_not_affect_a_bounded_store(self):
        store = open_retrieval(filled(STORE_TYPE_BOUNDED))
        store, outcome = store_packet(store, packet("P-NEW"))
        self.assertEqual(outcome, OUTCOME_DISCARDED_STORE_FULL)


class TestStoreSet(unittest.TestCase):
    def test_traffic_is_routed_to_the_named_store(self):
        result = assess_packet_store_set(
            [definition("PS-A", STORE_TYPE_BOUNDED, 400),
             definition("PS-B", STORE_TYPE_CIRCULAR, 200)],
            [
                {"store_id": "PS-A", "packet": packet("A-1", 100)},
                {"store_id": "PS-B", "packet": packet("B-1", 100)},
            ],
        )
        self.assertEqual(result["stores"][0]["packet_count"], 1)
        self.assertEqual(result["stores"][1]["packet_count"], 1)
        self.assertTrue(result["lossless"])

    def test_losses_are_counted_across_the_set(self):
        result = assess_packet_store_set(
            [definition("PS-A", STORE_TYPE_BOUNDED, 200),
             definition("PS-B", STORE_TYPE_CIRCULAR, 200)],
            [
                {"store_id": "PS-A", "packet": packet("A-1", 100)},
                {"store_id": "PS-A", "packet": packet("A-2", 100)},
                {"store_id": "PS-A", "packet": packet("A-3", 100)},
                {"store_id": "PS-B", "packet": packet("B-1", 100)},
                {"store_id": "PS-B", "packet": packet("B-2", 100)},
                {"store_id": "PS-B", "packet": packet("B-3", 100)},
            ],
        )
        self.assertFalse(result["lossless"])
        self.assertEqual(result["lost_packet_count"], 2)
        self.assertEqual(result["outcomes"][2]["outcome"], OUTCOME_DISCARDED_STORE_FULL)
        self.assertEqual(
            result["outcomes"][5]["outcome"], OUTCOME_STORED_AFTER_OVERWRITE
        )

    def test_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            assess_packet_store_set([definition("PS-A"), definition("PS-A")], [])

    def test_traffic_for_an_unknown_store_raises(self):
        with self.assertRaises(ValueError):
            assess_packet_store_set(
                [definition("PS-A")], [{"store_id": "PS-Z", "packet": packet()}]
            )

    def test_empty_definition_list_raises(self):
        with self.assertRaises(ValueError):
            assess_packet_store_set([], [])


if __name__ == "__main__":
    unittest.main()

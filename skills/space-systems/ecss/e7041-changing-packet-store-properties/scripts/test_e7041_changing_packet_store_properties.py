"""Contract test for the changing-packet-store-properties leaf (stdlib unittest)."""

import unittest

from e7041_changing_packet_store_properties_logic import (
    ACCEPTED,
    ALLOCATION_BLOCK_OCTETS,
    CAPACITY_MIN_OCTETS,
    REASON_CAPACITY_BELOW_OCCUPANCY,
    REASON_CAPACITY_NOT_BLOCK_ALIGNED,
    REASON_CAPACITY_OUT_OF_RANGE,
    REASON_MEMORY_POOL_EXHAUSTED,
    REASON_NOTHING_WOULD_CHANGE,
    REASON_RETRIEVAL_OPEN,
    REASON_STORAGE_ENABLED,
    REASON_TYPE_CHANGE_NEEDS_EMPTY_STORE,
    REASON_UNKNOWN_PACKET_STORE,
    REJECTED,
    STORE_TYPE_BOUNDED,
    STORE_TYPE_CIRCULAR,
    apply_property_changes,
    assess_property_change,
    normalize_store_table,
    pool_committed_octets,
    report_store_table,
    validate_change_item,
    validate_packet_store,
    validate_store_type,
)

POOL = 1048576


def store(store_id="PS-A", **kwargs):
    base = {
        "store_id": store_id,
        "capacity_octets": 8192,
        "occupancy_octets": 0,
        "store_type": STORE_TYPE_BOUNDED,
        "virtual_channel": 1,
        "storage_enabled": False,
        "retrieval_open": False,
    }
    base.update(kwargs)
    return base


class TestValidation(unittest.TestCase):
    def test_store_type_is_normalized_to_lower_case(self):
        self.assertEqual(validate_store_type("Circular"), STORE_TYPE_CIRCULAR)

    def test_unknown_store_type_raises(self):
        with self.assertRaises(ValueError):
            validate_store_type("ring-buffer")

    def test_empty_store_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(store_id="   "))

    def test_capacity_not_block_aligned_raises_in_the_table(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(capacity_octets=8193))

    def test_occupancy_above_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(occupancy_octets=9000))

    def test_boolean_storage_state_is_required(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(storage_enabled="off"))

    def test_duplicate_store_identifier_raises(self):
        with self.assertRaises(ValueError):
            normalize_store_table([store(), store()])

    def test_change_naming_no_property_raises(self):
        with self.assertRaises(ValueError):
            validate_change_item({"store_id": "PS-A"})

    def test_change_item_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_change_item(["PS-A", 4096])

    def test_change_keeps_only_the_named_properties(self):
        change = validate_change_item({"store_id": "PS-A", "virtual_channel": 7})
        self.assertEqual(sorted(change), ["store_id", "virtual_channel"])


class TestPreconditions(unittest.TestCase):
    def test_change_is_refused_while_storage_is_enabled(self):
        status, reason = assess_property_change(
            validate_packet_store(store(storage_enabled=True)),
            {"store_id": "PS-A", "virtual_channel": 7},
            POOL,
            0,
        )
        self.assertEqual(status, REJECTED)
        self.assertEqual(reason, REASON_STORAGE_ENABLED)

    def test_change_is_refused_while_a_retrieval_is_open(self):
        status, reason = assess_property_change(
            validate_packet_store(store(retrieval_open=True)),
            {"store_id": "PS-A", "virtual_channel": 7},
            POOL,
            0,
        )
        self.assertEqual(reason, REASON_RETRIEVAL_OPEN)

    def test_storage_state_is_reported_before_the_open_retrieval(self):
        status, reason = assess_property_change(
            validate_packet_store(store(storage_enabled=True, retrieval_open=True)),
            {"store_id": "PS-A", "virtual_channel": 7},
            POOL,
            0,
        )
        self.assertEqual(reason, REASON_STORAGE_ENABLED)

    def test_a_change_that_changes_nothing_is_rejected(self):
        status, reason = assess_property_change(
            validate_packet_store(store()),
            {"store_id": "PS-A", "virtual_channel": 1},
            POOL,
            0,
        )
        self.assertEqual(reason, REASON_NOTHING_WOULD_CHANGE)


class TestCapacityChange(unittest.TestCase):
    def test_growing_an_empty_store_is_accepted(self):
        table, disp = apply_property_changes(
            [store()], [{"store_id": "PS-A", "capacity_octets": 16384}], POOL
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(table["PS-A"]["capacity_octets"], 16384)
        self.assertEqual(disp[0]["properties_changed"], ["capacity_octets"])

    def test_shrinking_below_the_octets_held_is_rejected(self):
        table, disp = apply_property_changes(
            [store(occupancy_octets=6000)],
            [{"store_id": "PS-A", "capacity_octets": 4096}],
            POOL,
        )
        self.assertEqual(disp[0]["reason"], REASON_CAPACITY_BELOW_OCCUPANCY)
        self.assertEqual(table["PS-A"]["capacity_octets"], 8192)

    def test_shrinking_to_exactly_the_octets_held_is_accepted(self):
        table, disp = apply_property_changes(
            [store(occupancy_octets=4096)],
            [{"store_id": "PS-A", "capacity_octets": 4096}],
            POOL,
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(table["PS-A"]["capacity_octets"], 4096)

    def test_capacity_that_is_not_a_whole_block_is_rejected(self):
        _, disp = apply_property_changes(
            [store()],
            [{"store_id": "PS-A", "capacity_octets": ALLOCATION_BLOCK_OCTETS * 4 + 1}],
            POOL,
        )
        self.assertEqual(disp[0]["reason"], REASON_CAPACITY_NOT_BLOCK_ALIGNED)

    def test_capacity_below_the_configured_minimum_is_rejected(self):
        _, disp = apply_property_changes(
            [store()],
            [{"store_id": "PS-A", "capacity_octets": CAPACITY_MIN_OCTETS // 2}],
            POOL,
        )
        self.assertEqual(disp[0]["reason"], REASON_CAPACITY_OUT_OF_RANGE)

    def test_growth_past_the_memory_pool_is_rejected(self):
        _, disp = apply_property_changes(
            [store("PS-A", capacity_octets=8192), store("PS-B", capacity_octets=8192)],
            [{"store_id": "PS-A", "capacity_octets": 16384}],
            16384,
        )
        self.assertEqual(disp[0]["reason"], REASON_MEMORY_POOL_EXHAUSTED)

    def test_a_table_overcommitting_the_pool_raises(self):
        with self.assertRaises(ValueError):
            apply_property_changes([store(capacity_octets=8192)], [], 4096)


class TestTypeAndChannelChange(unittest.TestCase):
    def test_type_change_needs_an_empty_store(self):
        _, disp = apply_property_changes(
            [store(occupancy_octets=1024)],
            [{"store_id": "PS-A", "store_type": STORE_TYPE_CIRCULAR}],
            POOL,
        )
        self.assertEqual(disp[0]["reason"], REASON_TYPE_CHANGE_NEEDS_EMPTY_STORE)

    def test_type_change_on_an_empty_store_is_accepted(self):
        table, disp = apply_property_changes(
            [store()],
            [{"store_id": "PS-A", "store_type": STORE_TYPE_CIRCULAR}],
            POOL,
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(table["PS-A"]["store_type"], STORE_TYPE_CIRCULAR)

    def test_restating_the_current_type_on_a_full_store_is_not_a_type_change(self):
        _, disp = apply_property_changes(
            [store(occupancy_octets=1024)],
            [{"store_id": "PS-A", "store_type": STORE_TYPE_BOUNDED,
              "virtual_channel": 9}],
            POOL,
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(disp[0]["properties_changed"], ["virtual_channel"])

    def test_virtual_channel_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_change_item({"store_id": "PS-A", "virtual_channel": 64})


class TestRequestHandling(unittest.TestCase):
    def test_unknown_packet_store_is_rejected(self):
        _, disp = apply_property_changes(
            [store()], [{"store_id": "PS-Z", "virtual_channel": 3}], POOL
        )
        self.assertEqual(disp[0]["reason"], REASON_UNKNOWN_PACKET_STORE)

    def test_one_rejected_change_does_not_abandon_the_rest(self):
        table, disp = apply_property_changes(
            [store("PS-A"), store("PS-B")],
            [
                {"store_id": "PS-Z", "virtual_channel": 3},
                {"store_id": "PS-B", "virtual_channel": 5},
            ],
            POOL,
        )
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertEqual(table["PS-B"]["virtual_channel"], 5)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            apply_property_changes([store()], {"store_id": "PS-A"}, POOL)

    def test_two_properties_change_in_one_item(self):
        table, disp = apply_property_changes(
            [store()],
            [{"store_id": "PS-A", "capacity_octets": 4096, "virtual_channel": 2}],
            POOL,
        )
        self.assertEqual(
            disp[0]["properties_changed"], ["capacity_octets", "virtual_channel"]
        )
        self.assertEqual(table["PS-A"]["capacity_octets"], 4096)
        self.assertEqual(table["PS-A"]["virtual_channel"], 2)


class TestReport(unittest.TestCase):
    def test_report_is_sorted_and_counts_the_pool(self):
        table = normalize_store_table(
            [store("PS-B"), store("PS-A", capacity_octets=4096)]
        )
        report = report_store_table(table, POOL)
        self.assertEqual([e["store_id"] for e in report["packet_stores"]],
                         ["PS-A", "PS-B"])
        self.assertEqual(report["pool_committed_octets"], 12288)
        self.assertEqual(report["pool_free_octets"], POOL - 12288)

    def test_fill_fraction_of_a_half_full_store(self):
        table = normalize_store_table([store(occupancy_octets=4096)])
        report = report_store_table(table, POOL)
        self.assertAlmostEqual(
            report["packet_stores"][0]["fill_fraction"], 0.5, places=9
        )

    def test_an_enabled_store_is_not_changeable_now(self):
        table = normalize_store_table([store(storage_enabled=True)])
        report = report_store_table(table, POOL)
        self.assertFalse(report["packet_stores"][0]["changeable_now"])

    def test_pool_committed_octets_sums_the_table(self):
        table = normalize_store_table([store("PS-A"), store("PS-B")])
        self.assertEqual(pool_committed_octets(table), 16384)


if __name__ == "__main__":
    unittest.main()

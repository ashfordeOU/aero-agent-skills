"""Contract test for the storage control processing logic leaf (stdlib unittest)."""

import unittest

from e7041_storage_control_processing_logic import (
    APPLICATION_PROCESS_DISABLED,
    DISCARDED_FULL,
    NOT_SELECTED,
    REPORT_LARGER_THAN_CAPACITY,
    STORAGE_DISABLED,
    STORED,
    STORED_OVERWRITING,
    STORE_TYPE_BOUNDED,
    STORE_TYPE_CIRCULAR,
    normalize_store_states,
    occupancy_octets,
    offer_report_to_store,
    process_report_stream,
    route_report,
    selecting_packet_stores,
    selection_covers,
    validate_report,
    validate_store_state,
)

ENABLED = [10, 11]


def report(apid=10, service_type=3, message_subtype=25, size_octets=1000):
    return {
        "apid": apid,
        "service_type": service_type,
        "message_subtype": message_subtype,
        "size_octets": size_octets,
    }


def state(store_id="PS-A", **kwargs):
    base = {
        "store_id": store_id,
        "capacity_octets": 4096,
        "store_type": STORE_TYPE_BOUNDED,
        "storage_enabled": True,
        "records": [],
    }
    base.update(kwargs)
    return base


DEFS = {"PS-A": [(10, 3, 25)], "PS-B": [(10, None, None)]}


class TestValidation(unittest.TestCase):
    def test_report_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_report([10, 3, 25])

    def test_zero_sized_report_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(size_octets=0))

    def test_boolean_application_process_raises(self):
        with self.assertRaises(ValueError):
            validate_report(report(apid=True))

    def test_unknown_packet_store_type_raises(self):
        with self.assertRaises(ValueError):
            validate_store_state(state(store_type="ring"))

    def test_content_larger_than_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store_state(state(capacity_octets=1024, records=[1000, 1000]))

    def test_duplicate_packet_store_raises(self):
        with self.assertRaises(ValueError):
            normalize_store_states([state(), state()])

    def test_malformed_selection_raises(self):
        with self.assertRaises(ValueError):
            selection_covers((10, 3), validate_report(report()))

    def test_empty_report_stream_raises(self):
        with self.assertRaises(ValueError):
            process_report_stream([], DEFS, [state()], ENABLED)


class TestSelection(unittest.TestCase):
    def test_a_specific_selection_matches_only_its_report(self):
        rep = validate_report(report())
        self.assertTrue(selection_covers((10, 3, 25), rep))
        self.assertFalse(selection_covers((10, 3, 26), rep))

    def test_an_application_process_wildcard_matches_every_report(self):
        rep = validate_report(report(service_type=9, message_subtype=1))
        self.assertTrue(selection_covers((10, None, None), rep))

    def test_selected_twice_by_one_store_names_that_store_once(self):
        definitions = {"PS-A": [(10, None, None), (10, 3, 25)]}
        self.assertEqual(
            selecting_packet_stores(definitions, validate_report(report())),
            ["PS-A"],
        )

    def test_two_stores_selecting_one_report_are_both_named(self):
        self.assertEqual(
            selecting_packet_stores(DEFS, validate_report(report())),
            ["PS-A", "PS-B"],
        )

    def test_an_unselected_report_names_no_store(self):
        self.assertEqual(
            selecting_packet_stores(DEFS, validate_report(report(apid=11))), []
        )


class TestOfferToStore(unittest.TestCase):
    def test_a_report_that_fits_is_stored(self):
        working = validate_store_state(state())
        outcome, evicted = offer_report_to_store(working, validate_report(report()))
        self.assertEqual(outcome, STORED)
        self.assertEqual(evicted, 0)
        self.assertEqual(occupancy_octets(working), 1000)

    def test_a_disabled_store_discards_without_touching_its_content(self):
        working = validate_store_state(state(storage_enabled=False, records=[500]))
        outcome, _ = offer_report_to_store(working, validate_report(report()))
        self.assertEqual(outcome, STORAGE_DISABLED)
        self.assertEqual(working["records"], [500])

    def test_a_full_bounded_store_discards_the_new_report(self):
        working = validate_store_state(
            state(capacity_octets=1024, records=[1000])
        )
        outcome, _ = offer_report_to_store(
            working, validate_report(report(size_octets=500))
        )
        self.assertEqual(outcome, DISCARDED_FULL)
        self.assertEqual(working["records"], [1000])

    def test_a_full_circular_store_evicts_its_oldest_records(self):
        working = validate_store_state(
            state(store_type=STORE_TYPE_CIRCULAR, capacity_octets=1024,
                  records=[400, 400])
        )
        outcome, evicted = offer_report_to_store(
            working, validate_report(report(size_octets=500))
        )
        self.assertEqual(outcome, STORED_OVERWRITING)
        self.assertEqual(evicted, 1)
        self.assertEqual(working["records"], [400, 500])

    def test_a_report_filling_the_store_exactly_is_stored_without_eviction(self):
        working = validate_store_state(state(capacity_octets=1024))
        outcome, evicted = offer_report_to_store(
            working, validate_report(report(size_octets=1024))
        )
        self.assertEqual(outcome, STORED)
        self.assertEqual(evicted, 0)

    def test_a_report_larger_than_the_store_is_a_sizing_error(self):
        working = validate_store_state(
            state(store_type=STORE_TYPE_CIRCULAR, capacity_octets=1024)
        )
        outcome, evicted = offer_report_to_store(
            working, validate_report(report(size_octets=2000))
        )
        self.assertEqual(outcome, REPORT_LARGER_THAN_CAPACITY)
        self.assertEqual(evicted, 0)

    def test_the_sizing_error_is_named_before_the_disabled_state(self):
        working = validate_store_state(
            state(capacity_octets=1024, storage_enabled=False)
        )
        outcome, _ = offer_report_to_store(
            working, validate_report(report(size_octets=2000))
        )
        self.assertEqual(outcome, REPORT_LARGER_THAN_CAPACITY)


class TestRouteReport(unittest.TestCase):
    def test_a_report_is_stored_into_every_selecting_store(self):
        table = normalize_store_states([state("PS-A"), state("PS-B")])
        result = route_report(report(), DEFS, table, ENABLED)
        self.assertEqual(result["stored_copies"], 2)
        self.assertEqual(result["selected_store_count"], 2)

    def test_a_silenced_application_process_stores_nothing_anywhere(self):
        table = normalize_store_states([state("PS-A"), state("PS-B")])
        result = route_report(report(), DEFS, table, [11])
        self.assertEqual(result["stored_copies"], 0)
        self.assertFalse(result["application_process_storage_enabled"])
        self.assertEqual(
            {d["disposition"] for d in result["dispositions"]},
            {APPLICATION_PROCESS_DISABLED},
        )
        self.assertEqual(occupancy_octets(table["PS-A"]), 0)

    def test_an_unselected_report_carries_the_report_level_reason(self):
        table = normalize_store_states([state("PS-A"), state("PS-B")])
        result = route_report(report(apid=11), DEFS, table, ENABLED)
        self.assertTrue(result["not_selected"])
        self.assertEqual(result["report_level_reason"], NOT_SELECTED)

    def test_one_disabled_store_does_not_stop_the_other_copy(self):
        table = normalize_store_states(
            [state("PS-A", storage_enabled=False), state("PS-B")]
        )
        result = route_report(report(), DEFS, table, ENABLED)
        self.assertEqual(result["stored_copies"], 1)
        self.assertEqual(result["dispositions"][0]["disposition"], STORAGE_DISABLED)
        self.assertEqual(result["dispositions"][1]["disposition"], STORED)

    def test_a_definition_naming_a_store_outside_the_table_raises(self):
        table = normalize_store_states([state("PS-A")])
        with self.assertRaises(ValueError):
            route_report(report(), DEFS, table, ENABLED)

    def test_storage_enabled_list_must_be_a_collection(self):
        table = normalize_store_states([state("PS-A"), state("PS-B")])
        with self.assertRaises(ValueError):
            route_report(report(), DEFS, table, 10)


class TestReportStream(unittest.TestCase):
    def test_a_stream_accumulates_octets_in_both_stores(self):
        result = process_report_stream(
            [report(), report()], DEFS, [state("PS-A"), state("PS-B")], ENABLED
        )
        self.assertEqual(result["copies_stored"], 4)
        self.assertEqual(result["packet_stores"][0]["occupancy_octets"], 2000)

    def test_a_bounded_store_stops_and_a_circular_store_keeps_going(self):
        definitions = {"PS-A": [(10, None, None)], "PS-B": [(10, None, None)]}
        states = [
            state("PS-A", capacity_octets=1024),
            state("PS-B", capacity_octets=1024, store_type=STORE_TYPE_CIRCULAR),
        ]
        result = process_report_stream(
            [report(size_octets=600)] * 3, definitions, states, ENABLED
        )
        self.assertEqual(result["packet_stores"][0]["record_count"], 1)
        self.assertEqual(result["packet_stores"][1]["record_count"], 1)
        self.assertEqual(result["records_evicted"], 2)

    def test_reports_stored_nowhere_are_counted(self):
        result = process_report_stream(
            [report(), report(apid=11)], DEFS, [state("PS-A"), state("PS-B")],
            ENABLED,
        )
        self.assertEqual(result["reports_stored_nowhere"], 1)

    def test_fill_fraction_of_a_quarter_full_store(self):
        result = process_report_stream(
            [report(size_octets=1024)],
            {"PS-A": [(10, None, None)]},
            [state("PS-A", capacity_octets=4096)],
            ENABLED,
        )
        self.assertAlmostEqual(
            result["packet_stores"][0]["fill_fraction"], 0.25, places=9
        )


if __name__ == "__main__":
    unittest.main()

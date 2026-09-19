"""Contract test for the storage-control definitions leaf (stdlib unittest)."""

import unittest

from e7041_storage_control_definitions_logic import (
    ACCEPTED,
    MAX_DEFINITIONS_PER_PACKET_STORE,
    REASON_ADDED_ABSORBING,
    REASON_COVERED_BY_WIDER,
    REASON_DUPLICATE_DEFINITION,
    REASON_NOT_HELD,
    REASON_PER_STORE_CAPACITY,
    REASON_UNKNOWN_APPLICATION_PROCESS,
    REASON_UNKNOWN_PACKET_STORE,
    REJECTED,
    add_definitions,
    covers,
    definition_key,
    delete_definitions,
    empty_definition_store,
    normalize_definition_store,
    packet_stores_receiving,
    report_definition_store,
    selection_sort_key,
    storage_multiplicity,
    validate_definition,
)

STORES = ["PS-LONG", "PS-RING"]
APIDS = [10, 11, 12]


def defn(store_id="PS-LONG", apid=10, service_type=3, message_subtype=25):
    return {
        "store_id": store_id,
        "apid": apid,
        "service_type": service_type,
        "message_subtype": message_subtype,
    }


def added(items, base=None):
    return add_definitions(
        base if base is not None else empty_definition_store(),
        STORES,
        APIDS,
        items,
    )


class TestValidation(unittest.TestCase):
    def test_definition_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_definition(["PS-LONG", 10, 3, 25])

    def test_subtype_without_report_type_raises(self):
        with self.assertRaises(ValueError):
            validate_definition({"store_id": "PS-LONG", "apid": 10,
                                 "message_subtype": 25})

    def test_blank_packet_store_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(defn(store_id="  "))

    def test_application_process_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(defn(apid=2048))

    def test_boolean_report_type_raises(self):
        with self.assertRaises(ValueError):
            validate_definition(defn(service_type=True))

    def test_wildcard_definition_normalizes_both_levels_to_none(self):
        key = definition_key(validate_definition({"store_id": "PS-LONG",
                                                  "apid": 11}))
        self.assertEqual(key, (11, None, None))

    def test_empty_packet_store_list_raises(self):
        with self.assertRaises(ValueError):
            add_definitions(empty_definition_store(), [], APIDS, [defn()])

    def test_empty_declared_application_process_list_raises(self):
        with self.assertRaises(ValueError):
            add_definitions(empty_definition_store(), STORES, [], [defn()])


class TestCoverage(unittest.TestCase):
    def test_application_process_wildcard_covers_a_specific_report(self):
        self.assertTrue(covers((10, None, None), (10, 3, 25)))

    def test_report_type_wildcard_covers_its_subtypes_only(self):
        self.assertTrue(covers((10, 3, None), (10, 3, 25)))
        self.assertFalse(covers((10, 3, None), (10, 5, 25)))

    def test_a_specific_selection_covers_only_itself(self):
        self.assertTrue(covers((10, 3, 25), (10, 3, 25)))
        self.assertFalse(covers((10, 3, 25), (10, 3, 26)))

    def test_selections_of_other_application_processes_are_untouched(self):
        self.assertFalse(covers((10, None, None), (11, 3, 25)))

    def test_selection_sort_key_puts_the_wildcard_first(self):
        keys = sorted([(10, 3, 25), (10, None, None), (10, 3, None)],
                      key=selection_sort_key)
        self.assertEqual(keys[0], (10, None, None))


class TestAddDefinitions(unittest.TestCase):
    def test_a_definition_makes_its_packet_store_receive_the_report(self):
        store, disp = added([defn()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(packet_stores_receiving(store, 10, 3, 25), ["PS-LONG"])

    def test_unknown_packet_store_is_rejected(self):
        store, disp = added([defn(store_id="PS-GHOST")])
        self.assertEqual(disp[0]["reason"], REASON_UNKNOWN_PACKET_STORE)
        self.assertEqual(store, {})

    def test_undeclared_application_process_is_rejected(self):
        _, disp = added([defn(apid=99)])
        self.assertEqual(disp[0]["reason"], REASON_UNKNOWN_APPLICATION_PROCESS)

    def test_duplicate_definition_in_the_same_store_is_rejected(self):
        _, disp = added([defn(), defn()])
        self.assertEqual(disp[1]["reason"], REASON_DUPLICATE_DEFINITION)

    def test_the_same_selection_in_two_stores_is_two_copies_not_a_duplicate(self):
        store, disp = added([defn(), defn(store_id="PS-RING")])
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertEqual(storage_multiplicity(store, 10, 3, 25), 2)

    def test_a_wider_definition_absorbs_the_narrower_ones_it_covers(self):
        store, _ = added([defn(), defn(message_subtype=26)])
        store, disp = added([{"store_id": "PS-LONG", "apid": 10,
                              "service_type": 3}], base=store)
        self.assertEqual(disp[0]["reason"], REASON_ADDED_ABSORBING)
        self.assertEqual(disp[0]["absorbed"], [(10, 3, 25), (10, 3, 26)])
        self.assertEqual(len(store["PS-LONG"]), 1)

    def test_a_narrower_definition_under_a_wider_one_is_rejected(self):
        store, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        _, disp = added([defn()], base=store)
        self.assertEqual(disp[0]["reason"], REASON_COVERED_BY_WIDER)

    def test_one_rejected_definition_does_not_abandon_the_rest(self):
        store, disp = added([defn(store_id="PS-GHOST"), defn(apid=11)])
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertEqual(packet_stores_receiving(store, 11, 3, 25), ["PS-LONG"])

    def test_per_store_capacity_is_a_rejection_not_an_exception(self):
        items = [
            defn(message_subtype=n)
            for n in range(1, MAX_DEFINITIONS_PER_PACKET_STORE + 2)
        ]
        store, disp = added(items)
        self.assertEqual(disp[-1]["reason"], REASON_PER_STORE_CAPACITY)
        self.assertEqual(len(store["PS-LONG"]), MAX_DEFINITIONS_PER_PACKET_STORE)

    def test_an_absorbing_add_is_not_charged_against_capacity(self):
        items = [
            defn(message_subtype=n)
            for n in range(1, MAX_DEFINITIONS_PER_PACKET_STORE + 1)
        ]
        store, _ = added(items)
        store, disp = added([{"store_id": "PS-LONG", "apid": 10,
                              "service_type": 3}], base=store)
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(len(store["PS-LONG"]), 1)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            added(defn())


class TestDeleteDefinitions(unittest.TestCase):
    def test_deleting_a_definition_stops_that_store_receiving_it(self):
        store, _ = added([defn(), defn(store_id="PS-RING")])
        store, disp = delete_definitions(store, [defn()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(packet_stores_receiving(store, 10, 3, 25), ["PS-RING"])

    def test_deleting_an_absent_definition_is_rejected(self):
        _, disp = delete_definitions(empty_definition_store(), [defn()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_HELD)

    def test_deleting_the_narrower_form_of_a_wider_definition_is_rejected(self):
        store, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        _, disp = delete_definitions(store, [defn()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_HELD)

    def test_emptying_a_store_removes_it_from_the_definition_store(self):
        store, _ = added([defn()])
        store, _ = delete_definitions(store, [defn()])
        self.assertEqual(store, {})


class TestReport(unittest.TestCase):
    def test_report_lists_packet_stores_in_order(self):
        store, _ = added([defn(store_id="PS-RING"), defn()])
        report = report_definition_store(store)
        self.assertEqual([e["store_id"] for e in report["packet_stores"]],
                         ["PS-LONG", "PS-RING"])

    def test_report_names_selections_held_by_more_than_one_store(self):
        store, _ = added([defn(), defn(store_id="PS-RING"),
                          defn(message_subtype=26)])
        report = report_definition_store(store)
        self.assertEqual(report["selections_held_by_more_than_one_store"],
                         [(10, 3, 25)])

    def test_an_empty_definition_store_selects_nothing(self):
        report = report_definition_store(empty_definition_store())
        self.assertTrue(report["selects_nothing"])
        self.assertEqual(report["definition_total"], 0)

    def test_normalize_returns_an_independent_copy(self):
        source = {"PS-LONG": [(10, 3, 25)]}
        copy = normalize_definition_store(source)
        copy["PS-LONG"].add((10, 3, 26))
        self.assertEqual(source["PS-LONG"], [(10, 3, 25)])

    def test_a_malformed_selection_tuple_raises(self):
        with self.assertRaises(ValueError):
            normalize_definition_store({"PS-LONG": [(10, 3)]})

    def test_unreceived_report_gives_an_empty_store_list(self):
        store, _ = added([defn()])
        self.assertEqual(packet_stores_receiving(store, 10, 5, 1), [])
        self.assertEqual(storage_multiplicity(store, 10, 5, 1), 0)


if __name__ == "__main__":
    unittest.main()

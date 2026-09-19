"""Contract test for the housekeeping report storage-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_housekeeping_parameter_report_storage_logic import (
    ACCEPTED,
    MAX_STRUCTURES_PER_APPLICATION_PROCESS,
    REASON_ALREADY_STORED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_NO_HOUSEKEEPING_DEFINITIONS,
    REASON_STRUCTURE_CAPACITY,
    REASON_STRUCTURE_NOT_DEFINED,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_UNKNOWN_PACKET_STORE,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    add_housekeeping_storage_selections,
    delete_housekeeping_storage_selections,
    empty_configuration,
    is_structure_stored,
    normalize_configuration,
    normalize_defined_structures,
    packet_stores_storing_structure,
    prune_stale_selections,
    report_configuration,
    stale_selections,
    validate_structure_selection,
)

STORES = ["PS-LONG", "PS-RING"]
DEFINED = {10: [1, 2, 3], 11: [1, 7]}


def sel(store_id="PS-LONG", apid=10, structure_id=1):
    return {"store_id": store_id, "apid": apid, "structure_id": structure_id}


def added(items, base=None, defined=None, stores=None):
    return add_housekeeping_storage_selections(
        base if base is not None else empty_configuration(),
        stores if stores is not None else STORES,
        defined if defined is not None else DEFINED,
        items,
    )


class TestValidation(unittest.TestCase):
    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_structure_selection(["PS-LONG", 10, 1])

    def test_selection_without_a_packet_store_raises(self):
        with self.assertRaises(ValueError):
            validate_structure_selection({"apid": 10, "structure_id": 1})

    def test_structure_identifier_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_structure_selection(sel(structure_id=0))

    def test_boolean_structure_identifier_raises(self):
        with self.assertRaises(ValueError):
            validate_structure_selection(sel(structure_id=True))

    def test_a_selection_without_a_structure_is_the_wildcard(self):
        normalized = validate_structure_selection({"store_id": "PS-LONG",
                                                   "apid": 10})
        self.assertIsNone(normalized["structure_id"])

    def test_definitions_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            normalize_defined_structures([[10, [1]]])

    def test_definitions_out_of_range_raise(self):
        with self.assertRaises(ValueError):
            normalize_defined_structures({10: [256]})

    def test_empty_packet_store_list_raises(self):
        with self.assertRaises(ValueError):
            added([sel()], stores=[])

    def test_wildcard_and_explicit_structures_together_raise(self):
        bad = {"PS-LONG": {10: {"all_structures": True, "structure_ids": [1]}}}
        with self.assertRaises(ValueError):
            normalize_configuration(bad)

    def test_normalize_returns_an_independent_copy(self):
        source = {"PS-LONG": {10: {"structure_ids": [1]}}}
        copy = normalize_configuration(source)
        copy["PS-LONG"][10]["structure_ids"].add(2)
        self.assertEqual(source["PS-LONG"][10]["structure_ids"], [1])


class TestAddSelections(unittest.TestCase):
    def test_a_defined_structure_is_stored_after_the_add(self):
        config, disp = added([sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_structure_stored(config, "PS-LONG", 10, 1))

    def test_an_undefined_structure_is_rejected(self):
        config, disp = added([sel(structure_id=9)])
        self.assertEqual(disp[0]["reason"], REASON_STRUCTURE_NOT_DEFINED)
        self.assertEqual(config, {})

    def test_the_same_identifier_under_another_process_is_a_different_report(self):
        config, disp = added([sel(apid=11, structure_id=7)])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_structure_stored(config, "PS-LONG", 10, 7))

    def test_a_process_with_no_housekeeping_definitions_is_rejected(self):
        _, disp = added([sel(apid=12)])
        self.assertEqual(disp[0]["reason"], REASON_NO_HOUSEKEEPING_DEFINITIONS)

    def test_unknown_packet_store_is_rejected(self):
        _, disp = added([sel(store_id="PS-GHOST")])
        self.assertEqual(disp[0]["reason"], REASON_UNKNOWN_PACKET_STORE)

    def test_duplicate_structure_is_rejected_as_already_stored(self):
        _, disp = added([sel(), sel()])
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_STORED)

    def test_the_wildcard_stores_every_structure_of_that_process(self):
        config, disp = added([{"store_id": "PS-LONG", "apid": 10}])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_structure_stored(config, "PS-LONG", 10, 3))

    def test_the_wildcard_clears_the_explicit_structures_it_subsumes(self):
        config, _ = added([sel(), sel(structure_id=2)])
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}], base=config)
        self.assertEqual(config["PS-LONG"][10]["structure_ids"], set())

    def test_a_structure_under_an_existing_wildcard_is_rejected(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        _, disp = added([sel()], base=config)
        self.assertEqual(disp[0]["reason"], REASON_SUBSUMED_BY_WILDCARD)

    def test_the_same_structure_in_two_stores_is_two_copies(self):
        config, _ = added([sel(), sel(store_id="PS-RING")])
        self.assertEqual(packet_stores_storing_structure(config, 10, 1),
                         ["PS-LONG", "PS-RING"])

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = added([sel(structure_id=9), sel(structure_id=2)])
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertTrue(is_structure_stored(config, "PS-LONG", 10, 2))

    def test_structure_capacity_is_a_rejection_not_an_exception(self):
        defined = {10: list(range(1, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2))}
        items = [
            sel(structure_id=n)
            for n in range(1, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2)
        ]
        config, disp = added(items, defined=defined)
        self.assertEqual(disp[-1]["reason"], REASON_STRUCTURE_CAPACITY)
        self.assertEqual(len(config["PS-LONG"][10]["structure_ids"]),
                         MAX_STRUCTURES_PER_APPLICATION_PROCESS)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            added(sel())


class TestDeleteSelections(unittest.TestCase):
    def test_deleting_a_structure_stops_that_store_holding_it(self):
        config, _ = added([sel(), sel(structure_id=2)])
        config, disp = delete_housekeeping_storage_selections(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_structure_stored(config, "PS-LONG", 10, 1))
        self.assertTrue(is_structure_stored(config, "PS-LONG", 10, 2))

    def test_deleting_an_absent_structure_is_rejected(self):
        _, disp = delete_housekeeping_storage_selections(
            empty_configuration(), [sel()]
        )
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_the_wildcard_cannot_be_partially_deleted(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        _, disp = delete_housekeeping_storage_selections(config, [sel()])
        self.assertEqual(disp[0]["reason"],
                         REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)

    def test_deleting_the_whole_entry_clears_the_wildcard(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        config, disp = delete_housekeeping_storage_selections(
            config, [{"store_id": "PS-LONG", "apid": 10}]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(config, {})


class TestStaleSelections(unittest.TestCase):
    def test_a_deleted_structure_leaves_a_stale_selection(self):
        config, _ = added([sel(structure_id=3), sel(structure_id=1)])
        self.assertEqual(stale_selections(config, {10: [1, 2]}),
                         [("PS-LONG", 10, 3)])

    def test_a_live_configuration_has_no_stale_selections(self):
        config, _ = added([sel()])
        self.assertEqual(stale_selections(config, DEFINED), [])

    def test_the_wildcard_never_goes_stale(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        self.assertEqual(stale_selections(config, {10: [1]}), [])

    def test_pruning_removes_the_stale_selection_and_keeps_the_rest(self):
        config, _ = added([sel(structure_id=3), sel(structure_id=1)])
        config, removed = prune_stale_selections(config, {10: [1, 2]})
        self.assertEqual(removed, [("PS-LONG", 10, 3)])
        self.assertTrue(is_structure_stored(config, "PS-LONG", 10, 1))
        self.assertFalse(is_structure_stored(config, "PS-LONG", 10, 3))

    def test_pruning_the_last_structure_drops_the_packet_store(self):
        config, _ = added([sel(structure_id=3)])
        config, removed = prune_stale_selections(config, {10: [1]})
        self.assertEqual(len(removed), 1)
        self.assertEqual(config, {})


class TestReport(unittest.TestCase):
    def test_report_is_sorted_by_store_and_process(self):
        config, _ = added([sel(store_id="PS-RING", apid=11, structure_id=7),
                           sel()])
        report = report_configuration(config)
        self.assertEqual([e["store_id"] for e in report["packet_stores"]],
                         ["PS-LONG", "PS-RING"])

    def test_report_names_structures_held_by_more_than_one_store(self):
        config, _ = added([sel(), sel(store_id="PS-RING"), sel(structure_id=2)])
        report = report_configuration(config)
        self.assertEqual(report["structures_stored_by_more_than_one_store"],
                         [(10, 1)])

    def test_an_empty_configuration_stores_nothing(self):
        report = report_configuration(empty_configuration())
        self.assertTrue(report["stores_nothing"])
        self.assertEqual(report["packet_store_count"], 0)

    def test_report_counts_the_structures_of_each_process(self):
        config, _ = added([sel(), sel(structure_id=2)])
        report = report_configuration(config)
        entry = report["packet_stores"][0]["application_processes"][0]
        self.assertEqual(entry["structure_count"], 2)
        self.assertEqual(entry["structure_ids"], [1, 2])


if __name__ == "__main__":
    unittest.main()

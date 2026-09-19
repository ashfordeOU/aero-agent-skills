"""Contract test for the diagnostic report storage-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_diagnostic_parameter_report_storage_logic import (
    ACCEPTED,
    MAX_STRUCTURES_PER_APPLICATION_PROCESS,
    REASON_ALREADY_STORED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_NO_DIAGNOSTIC_DEFINITIONS,
    REASON_STRUCTURE_CAPACITY,
    REASON_STRUCTURE_NOT_DEFINED,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_UNKNOWN_PACKET_STORE,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    VERDICT_NEVER_FILLS,
    VERDICT_OVER_BUDGET,
    VERDICT_WITHIN_BUDGET,
    add_diagnostic_storage_selections,
    assess_storage_budget,
    delete_diagnostic_storage_selections,
    dormant_selections,
    empty_configuration,
    normalize_configuration,
    normalize_defined_structures,
    report_configuration,
    selected_structures,
    store_octet_rate,
    structure_octet_rate,
    time_to_fill_seconds,
    validate_structure_selection,
)

STORES = ["PS-LONG", "PS-RING"]
DEFINED = {
    10: {
        1: {"collection_interval_s": 0.5, "report_size_octets": 512,
            "generation_enabled": True},
        2: {"collection_interval_s": 2.0, "report_size_octets": 256,
            "generation_enabled": True},
        3: {"collection_interval_s": 4.0, "report_size_octets": 128,
            "generation_enabled": False},
    },
    11: {
        1: {"collection_interval_s": 8.0, "report_size_octets": 64,
            "generation_enabled": True},
    },
}


def sel(store_id="PS-LONG", apid=10, structure_id=1):
    return {"store_id": store_id, "apid": apid, "structure_id": structure_id}


def added(items, base=None, defined=None, stores=None):
    return add_diagnostic_storage_selections(
        base if base is not None else empty_configuration(),
        stores if stores is not None else STORES,
        defined if defined is not None else DEFINED,
        items,
    )


def store(store_id="PS-LONG", capacity_octets=4096):
    return {"store_id": store_id, "capacity_octets": capacity_octets}


class TestValidation(unittest.TestCase):
    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_structure_selection(["PS-LONG", 10, 1])

    def test_selection_without_a_packet_store_raises(self):
        with self.assertRaises(ValueError):
            validate_structure_selection({"apid": 10, "structure_id": 1})

    def test_structure_identifier_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_structure_selection(sel(structure_id=256))

    def test_a_selection_without_a_structure_is_the_wildcard(self):
        self.assertIsNone(
            validate_structure_selection({"store_id": "PS-LONG",
                                          "apid": 10})["structure_id"]
        )

    def test_a_zero_collection_interval_raises(self):
        with self.assertRaises(ValueError):
            normalize_defined_structures(
                {10: {1: {"collection_interval_s": 0.0,
                          "report_size_octets": 16}}}
            )

    def test_a_boolean_report_size_raises(self):
        with self.assertRaises(ValueError):
            normalize_defined_structures(
                {10: {1: {"collection_interval_s": 1.0,
                          "report_size_octets": True}}}
            )

    def test_wildcard_and_explicit_structures_together_raise(self):
        with self.assertRaises(ValueError):
            normalize_configuration(
                {"PS-LONG": {10: {"all_structures": True, "structure_ids": [1]}}}
            )

    def test_normalize_returns_an_independent_copy(self):
        source = {"PS-LONG": {10: {"structure_ids": [1]}}}
        copy = normalize_configuration(source)
        copy["PS-LONG"][10]["structure_ids"].add(2)
        self.assertEqual(source["PS-LONG"][10]["structure_ids"], [1])


class TestAddAndDelete(unittest.TestCase):
    def test_a_defined_structure_is_selected_after_the_add(self):
        config, disp = added([sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(selected_structures(config, DEFINED, "PS-LONG"),
                         [(10, 1)])

    def test_an_undefined_structure_is_rejected(self):
        config, disp = added([sel(structure_id=9)])
        self.assertEqual(disp[0]["reason"], REASON_STRUCTURE_NOT_DEFINED)
        self.assertEqual(config, {})

    def test_a_process_with_no_diagnostic_definitions_is_rejected(self):
        _, disp = added([sel(apid=12)])
        self.assertEqual(disp[0]["reason"], REASON_NO_DIAGNOSTIC_DEFINITIONS)

    def test_unknown_packet_store_is_rejected(self):
        _, disp = added([sel(store_id="PS-GHOST")])
        self.assertEqual(disp[0]["reason"], REASON_UNKNOWN_PACKET_STORE)

    def test_duplicate_structure_is_rejected_as_already_stored(self):
        _, disp = added([sel(), sel()])
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_STORED)

    def test_the_wildcard_resolves_to_every_defined_structure(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        self.assertEqual(selected_structures(config, DEFINED, "PS-LONG"),
                         [(10, 1), (10, 2), (10, 3)])

    def test_a_structure_under_an_existing_wildcard_is_rejected(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        _, disp = added([sel()], base=config)
        self.assertEqual(disp[0]["reason"], REASON_SUBSUMED_BY_WILDCARD)

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = added([sel(structure_id=9), sel(structure_id=2)])
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertEqual(selected_structures(config, DEFINED, "PS-LONG"),
                         [(10, 2)])

    def test_structure_capacity_is_a_rejection_not_an_exception(self):
        defined = {
            10: {
                n: {"collection_interval_s": 1.0, "report_size_octets": 16}
                for n in range(1, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2)
            }
        }
        items = [
            sel(structure_id=n)
            for n in range(1, MAX_STRUCTURES_PER_APPLICATION_PROCESS + 2)
        ]
        config, disp = added(items, defined=defined)
        self.assertEqual(disp[-1]["reason"], REASON_STRUCTURE_CAPACITY)
        self.assertEqual(len(config["PS-LONG"][10]["structure_ids"]),
                         MAX_STRUCTURES_PER_APPLICATION_PROCESS)

    def test_deleting_a_structure_removes_it_from_the_selection(self):
        config, _ = added([sel(), sel(structure_id=2)])
        config, disp = delete_diagnostic_storage_selections(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(selected_structures(config, DEFINED, "PS-LONG"),
                         [(10, 2)])

    def test_deleting_an_absent_structure_is_rejected(self):
        _, disp = delete_diagnostic_storage_selections(
            empty_configuration(), [sel()]
        )
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_the_wildcard_cannot_be_partially_deleted(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        _, disp = delete_diagnostic_storage_selections(config, [sel()])
        self.assertEqual(disp[0]["reason"],
                         REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            added(sel())


class TestRateModel(unittest.TestCase):
    def test_a_structure_rate_is_size_over_interval(self):
        self.assertAlmostEqual(
            structure_octet_rate(DEFINED[10][1]), 1024.0, places=9
        )

    def test_a_structure_that_is_not_generated_costs_nothing(self):
        self.assertAlmostEqual(
            structure_octet_rate(DEFINED[10][3]), 0.0, places=9
        )

    def test_store_rate_adds_its_selections(self):
        config, _ = added([sel(), sel(structure_id=2)])
        self.assertAlmostEqual(
            store_octet_rate(config, DEFINED, "PS-LONG"), 1152.0, places=9
        )

    def test_a_store_with_no_selections_has_no_rate(self):
        config, _ = added([sel()])
        self.assertAlmostEqual(
            store_octet_rate(config, DEFINED, "PS-RING"), 0.0, places=9
        )

    def test_time_to_fill_is_capacity_over_rate(self):
        self.assertAlmostEqual(time_to_fill_seconds(4096, 1024.0), 4.0, places=9)

    def test_a_store_taking_nothing_never_fills(self):
        self.assertIsNone(time_to_fill_seconds(4096, 0.0))

    def test_a_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            time_to_fill_seconds(4096, -1.0)


class TestBudgetAndDormancy(unittest.TestCase):
    def test_a_fast_selection_fills_before_the_retrieval_period(self):
        config, _ = added([sel()])
        result = assess_storage_budget(config, DEFINED, [store()], 60.0)
        entry = result["packet_stores"][0]
        self.assertAlmostEqual(entry["time_to_fill_s"], 4.0, places=9)
        self.assertEqual(entry["verdict"], VERDICT_OVER_BUDGET)
        self.assertEqual(result["stores_over_budget"], ["PS-LONG"])

    def test_a_slow_selection_survives_the_retrieval_period(self):
        config, _ = added([sel(apid=11)])
        result = assess_storage_budget(config, DEFINED, [store()], 60.0)
        entry = result["packet_stores"][0]
        self.assertAlmostEqual(entry["time_to_fill_s"], 512.0, places=9)
        self.assertEqual(entry["verdict"], VERDICT_WITHIN_BUDGET)

    def test_an_unselected_store_never_fills(self):
        config, _ = added([sel()])
        result = assess_storage_budget(config, DEFINED, [store("PS-RING")], 60.0)
        self.assertEqual(result["packet_stores"][0]["verdict"],
                         VERDICT_NEVER_FILLS)
        self.assertIsNone(result["packet_stores"][0]["time_to_fill_s"])

    def test_a_dormant_structure_is_named_and_not_priced(self):
        config, _ = added([sel(structure_id=3)])
        result = assess_storage_budget(config, DEFINED, [store()], 60.0)
        self.assertAlmostEqual(result["packet_stores"][0]["octet_rate"], 0.0,
                               places=9)
        self.assertEqual(result["dormant_selections"], [("PS-LONG", 10, 3)])

    def test_the_wildcard_prices_only_the_generated_structures(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10}])
        result = assess_storage_budget(config, DEFINED, [store()], 60.0)
        self.assertAlmostEqual(result["packet_stores"][0]["octet_rate"],
                               1152.0, places=9)
        self.assertEqual(result["packet_stores"][0]["selection_count"], 3)

    def test_a_configuration_with_nothing_dormant_reports_none(self):
        config, _ = added([sel()])
        self.assertEqual(dormant_selections(config, DEFINED), [])

    def test_budget_needs_at_least_one_packet_store(self):
        config, _ = added([sel()])
        with self.assertRaises(ValueError):
            assess_storage_budget(config, DEFINED, [], 60.0)

    def test_two_stores_are_priced_independently_and_sorted(self):
        config, _ = added([sel(), sel(store_id="PS-RING", apid=11)])
        result = assess_storage_budget(
            config, DEFINED, [store("PS-RING", 8192), store("PS-LONG")], 60.0
        )
        self.assertEqual([e["store_id"] for e in result["packet_stores"]],
                         ["PS-LONG", "PS-RING"])
        self.assertAlmostEqual(result["packet_stores"][1]["time_to_fill_s"],
                               1024.0, places=9)


class TestReport(unittest.TestCase):
    def test_report_is_sorted_by_store(self):
        config, _ = added([sel(store_id="PS-RING", apid=11), sel()])
        report = report_configuration(config)
        self.assertEqual([e["store_id"] for e in report["packet_stores"]],
                         ["PS-LONG", "PS-RING"])

    def test_an_empty_configuration_stores_nothing(self):
        report = report_configuration(empty_configuration())
        self.assertTrue(report["stores_nothing"])
        self.assertEqual(report["packet_store_count"], 0)

    def test_report_lists_the_structure_identifiers_in_order(self):
        config, _ = added([sel(structure_id=2), sel()])
        report = report_configuration(config)
        self.assertEqual(
            report["packet_stores"][0]["application_processes"][0]
            ["structure_ids"],
            [1, 2],
        )


if __name__ == "__main__":
    unittest.main()

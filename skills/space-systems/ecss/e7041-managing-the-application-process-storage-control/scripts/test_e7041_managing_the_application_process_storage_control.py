"""Contract test for the application-process storage-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_application_process_storage_control_logic import (
    ACCEPTED,
    MAX_APPLICATION_PROCESSES_PER_STORE,
    MAX_SUBTYPES_PER_SERVICE_TYPE,
    REASON_ALREADY_STORED,
    REASON_APPLICATION_PROCESS_NOT_CONTROLLED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_SUBTYPE_CAPACITY,
    REASON_UNKNOWN_PACKET_STORE,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    add_storage_selections,
    apply_storage_control_requests,
    delete_storage_selections,
    empty_configuration,
    is_report_stored,
    normalize_configuration,
    packet_stores_storing,
    report_configuration,
    validate_application_process,
    validate_selection,
)

STORES = ["PS-LONG", "PS-RING"]
CONTROLLED = [10, 11, 12]


def sel(store_id="PS-LONG", apid=10, service_type=3, message_subtype=25):
    return {
        "store_id": store_id,
        "apid": apid,
        "service_type": service_type,
        "message_subtype": message_subtype,
    }


def added(items, base=None, stores=None, controlled=None):
    return add_storage_selections(
        base if base is not None else empty_configuration(),
        stores if stores is not None else STORES,
        controlled if controlled is not None else CONTROLLED,
        items,
    )


class TestValidation(unittest.TestCase):
    def test_controlled_application_process_recognised(self):
        self.assertTrue(validate_application_process(10, CONTROLLED))

    def test_uncontrolled_application_process_recognised(self):
        self.assertFalse(validate_application_process(99, CONTROLLED))

    def test_application_process_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process(2048, CONTROLLED)

    def test_empty_controlled_set_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process(10, [])

    def test_subtype_without_report_type_raises(self):
        with self.assertRaises(ValueError):
            validate_selection({"store_id": "PS-LONG", "apid": 10,
                                "message_subtype": 25})

    def test_selection_without_a_packet_store_raises(self):
        with self.assertRaises(ValueError):
            validate_selection({"apid": 10, "service_type": 3})

    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_selection(["PS-LONG", 10, 3, 25])

    def test_report_type_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_selection(sel(service_type=0))

    def test_empty_packet_store_list_raises(self):
        with self.assertRaises(ValueError):
            added([sel()], stores=[])


class TestNormalizeConfiguration(unittest.TestCase):
    def test_empty_configuration_stores_nothing(self):
        self.assertEqual(normalize_configuration(empty_configuration()), {})

    def test_wildcard_and_explicit_report_types_together_raise(self):
        bad = {"PS-LONG": {10: {"all_report_types": True,
                                "service_types": {3: {"all_subtypes": True}}}}}
        with self.assertRaises(ValueError):
            normalize_configuration(bad)

    def test_wildcard_and_explicit_subtypes_together_raise(self):
        bad = {"PS-LONG": {10: {"service_types": {
            3: {"all_subtypes": True, "message_subtypes": [25]}}}}}
        with self.assertRaises(ValueError):
            normalize_configuration(bad)

    def test_normalize_returns_an_independent_copy(self):
        source = {"PS-LONG": {10: {"service_types": {
            3: {"message_subtypes": [25]}}}}}
        copy = normalize_configuration(source)
        copy["PS-LONG"][10]["service_types"][3]["message_subtypes"].add(26)
        self.assertEqual(
            source["PS-LONG"][10]["service_types"][3]["message_subtypes"], [25]
        )

    def test_non_mapping_configuration_raises(self):
        with self.assertRaises(ValueError):
            normalize_configuration(["PS-LONG"])


class TestAddSelections(unittest.TestCase):
    def test_a_selection_makes_its_store_hold_the_report(self):
        config, disp = added([sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_report_stored(config, "PS-LONG", 10, 3, 25))

    def test_the_other_store_is_untouched_by_the_selection(self):
        config, _ = added([sel()])
        self.assertFalse(is_report_stored(config, "PS-RING", 10, 3, 25))

    def test_unknown_packet_store_is_rejected(self):
        config, disp = added([sel(store_id="PS-GHOST")])
        self.assertEqual(disp[0]["reason"], REASON_UNKNOWN_PACKET_STORE)
        self.assertEqual(config, {})

    def test_uncontrolled_application_process_is_rejected(self):
        _, disp = added([sel(apid=99)])
        self.assertEqual(disp[0]["reason"],
                         REASON_APPLICATION_PROCESS_NOT_CONTROLLED)

    def test_duplicate_selection_is_rejected_as_already_stored(self):
        _, disp = added([sel(), sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_STORED)

    def test_report_type_wildcard_subsumes_a_later_subtype(self):
        config, disp = added(
            [{"store_id": "PS-LONG", "apid": 10, "service_type": 3}, sel()]
        )
        self.assertEqual(disp[1]["reason"], REASON_SUBSUMED_BY_WILDCARD)
        self.assertTrue(is_report_stored(config, "PS-LONG", 10, 3, 26))

    def test_application_process_wildcard_replaces_explicit_entries(self):
        config, _ = added([sel()])
        config, disp = added([{"store_id": "PS-LONG", "apid": 10}], base=config)
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(config["PS-LONG"][10]["service_types"], {})
        self.assertTrue(is_report_stored(config, "PS-LONG", 10, 5, 4))

    def test_the_same_selection_in_two_stores_is_two_copies(self):
        config, disp = added([sel(), sel(store_id="PS-RING")])
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertEqual(packet_stores_storing(config, 10, 3, 25),
                         ["PS-LONG", "PS-RING"])

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = added([sel(store_id="PS-GHOST"), sel(apid=11)])
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertTrue(is_report_stored(config, "PS-LONG", 11, 3, 25))

    def test_subtype_capacity_is_a_rejection_not_an_exception(self):
        items = [
            sel(message_subtype=n)
            for n in range(1, MAX_SUBTYPES_PER_SERVICE_TYPE + 2)
        ]
        _, disp = added(items)
        self.assertEqual(disp[-1]["reason"], REASON_SUBTYPE_CAPACITY)
        self.assertEqual(
            sum(1 for d in disp if d["status"] == ACCEPTED),
            MAX_SUBTYPES_PER_SERVICE_TYPE,
        )

    def test_application_process_capacity_is_per_packet_store(self):
        controlled = list(range(1, MAX_APPLICATION_PROCESSES_PER_STORE + 2))
        items = [{"store_id": "PS-LONG", "apid": a} for a in controlled]
        items.append({"store_id": "PS-RING", "apid": controlled[-1]})
        config, disp = added(items, controlled=controlled)
        self.assertEqual(disp[-2]["status"], REJECTED)
        self.assertEqual(disp[-1]["status"], ACCEPTED)
        self.assertEqual(len(config["PS-LONG"]),
                         MAX_APPLICATION_PROCESSES_PER_STORE)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            added(sel())


class TestDeleteSelections(unittest.TestCase):
    def test_deleting_a_subtype_stops_that_store_holding_it(self):
        config, _ = added([sel(), sel(message_subtype=26)])
        config, disp = delete_storage_selections(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_report_stored(config, "PS-LONG", 10, 3, 25))
        self.assertTrue(is_report_stored(config, "PS-LONG", 10, 3, 26))

    def test_deleting_one_store_leaves_the_other_copy(self):
        config, _ = added([sel(), sel(store_id="PS-RING")])
        config, _ = delete_storage_selections(config, [sel()])
        self.assertEqual(packet_stores_storing(config, 10, 3, 25), ["PS-RING"])

    def test_deleting_the_last_entry_removes_the_packet_store_key(self):
        config, _ = added([sel()])
        config, _ = delete_storage_selections(config, [{"store_id": "PS-LONG",
                                                        "apid": 10}])
        self.assertEqual(config, {})

    def test_deleting_an_absent_selection_is_rejected(self):
        _, disp = delete_storage_selections(empty_configuration(), [sel()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_a_wildcard_cannot_be_partially_deleted(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10,
                            "service_type": 3}])
        _, disp = delete_storage_selections(config, [sel()])
        self.assertEqual(disp[0]["reason"],
                         REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)

    def test_deleting_the_report_type_clears_its_wildcard(self):
        config, _ = added([{"store_id": "PS-LONG", "apid": 10,
                            "service_type": 3}])
        config, disp = delete_storage_selections(
            config, [{"store_id": "PS-LONG", "apid": 10, "service_type": 3}]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_report_stored(config, "PS-LONG", 10, 3, 25))


class TestReportAndRequests(unittest.TestCase):
    def test_report_is_sorted_at_every_level(self):
        config, _ = added(
            [
                sel(store_id="PS-RING", apid=12, service_type=5,
                    message_subtype=4),
                sel(message_subtype=26),
                sel(message_subtype=25),
            ]
        )
        report = report_configuration(config)
        self.assertEqual([e["store_id"] for e in report["packet_stores"]],
                         ["PS-LONG", "PS-RING"])
        self.assertEqual(
            report["packet_stores"][0]["application_processes"][0]
            ["report_types"][0]["message_subtypes"],
            [25, 26],
        )

    def test_empty_report_says_it_stores_nothing(self):
        report = report_configuration(empty_configuration())
        self.assertTrue(report["stores_nothing"])
        self.assertEqual(report["packet_store_count"], 0)

    def test_request_sequence_counts_rejections(self):
        result = apply_storage_control_requests(
            empty_configuration(),
            STORES,
            CONTROLLED,
            [
                {"operation": "add", "items": [sel(), sel(apid=99)]},
                {"operation": "delete", "items": [sel(message_subtype=26)]},
            ],
        )
        self.assertEqual(result["rejected_total"], 2)
        self.assertTrue(
            is_report_stored(result["configuration"], "PS-LONG", 10, 3, 25)
        )

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            apply_storage_control_requests(
                empty_configuration(), STORES, CONTROLLED,
                [{"operation": "purge"}]
            )

    def test_empty_request_list_raises(self):
        with self.assertRaises(ValueError):
            apply_storage_control_requests(
                empty_configuration(), STORES, CONTROLLED, []
            )

    def test_a_report_no_store_selects_gives_an_empty_store_list(self):
        config, _ = added([sel()])
        self.assertEqual(packet_stores_storing(config, 10, 5, 1), [])


if __name__ == "__main__":
    unittest.main()

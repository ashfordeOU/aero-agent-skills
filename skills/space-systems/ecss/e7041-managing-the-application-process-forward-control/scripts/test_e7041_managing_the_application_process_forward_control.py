"""Contract test for the application-process forward-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_application_process_forward_control_logic import (
    ACCEPTED,
    MAX_APPLICATION_PROCESSES,
    MAX_SUBTYPES_PER_SERVICE_TYPE,
    REASON_ALREADY_FORWARDED,
    REASON_APPLICATION_PROCESS_NOT_CONTROLLED,
    REASON_NOT_IN_CONFIGURATION,
    REASON_SUBSUMED_BY_WILDCARD,
    REASON_SUBTYPE_CAPACITY,
    REASON_WILDCARD_NOT_PARTIALLY_DELETABLE,
    REJECTED,
    add_forward_selections,
    apply_forward_control_requests,
    delete_forward_selections,
    empty_configuration,
    is_report_forwarded,
    normalize_configuration,
    report_configuration,
    validate_application_process,
    validate_selection,
)

CONTROLLED = [10, 11, 12]


def sel(apid=10, service_type=3, message_subtype=25):
    return {"apid": apid, "service_type": service_type, "message_subtype": message_subtype}


class TestValidation(unittest.TestCase):
    def test_controlled_application_process_recognised(self):
        self.assertTrue(validate_application_process(10, CONTROLLED))

    def test_uncontrolled_application_process_recognised(self):
        self.assertFalse(validate_application_process(99, CONTROLLED))

    def test_application_process_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process(2048, CONTROLLED)

    def test_boolean_application_process_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process(True, CONTROLLED)

    def test_empty_controlled_set_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process(10, [])

    def test_subtype_without_report_type_raises(self):
        with self.assertRaises(ValueError):
            validate_selection({"apid": 10, "message_subtype": 25})

    def test_selection_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_selection([10, 3, 25])

    def test_report_type_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_selection(sel(service_type=0))

    def test_wildcard_selection_normalizes_to_none(self):
        norm = validate_selection({"apid": 11})
        self.assertIsNone(norm["service_type"])
        self.assertIsNone(norm["message_subtype"])


class TestNormalizeConfiguration(unittest.TestCase):
    def test_empty_configuration_forwards_nothing(self):
        self.assertEqual(normalize_configuration(empty_configuration()), {})

    def test_wildcard_and_explicit_report_types_together_raise(self):
        bad = {10: {"all_report_types": True, "service_types": {3: {"all_subtypes": True}}}}
        with self.assertRaises(ValueError):
            normalize_configuration(bad)

    def test_wildcard_and_explicit_subtypes_together_raise(self):
        bad = {
            10: {
                "service_types": {
                    3: {"all_subtypes": True, "message_subtypes": [25]}
                }
            }
        }
        with self.assertRaises(ValueError):
            normalize_configuration(bad)

    def test_normalize_returns_an_independent_copy(self):
        source = {10: {"service_types": {3: {"message_subtypes": [25]}}}}
        copy = normalize_configuration(source)
        copy[10]["service_types"][3]["message_subtypes"].add(26)
        self.assertEqual(source[10]["service_types"][3]["message_subtypes"], [25])

    def test_non_mapping_configuration_raises(self):
        with self.assertRaises(ValueError):
            normalize_configuration([10])


class TestAddSelections(unittest.TestCase):
    def test_specific_subtype_is_forwarded_after_add(self):
        config, disp = add_forward_selections(empty_configuration(), CONTROLLED, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertTrue(is_report_forwarded(config, 10, 3, 25))

    def test_unrelated_subtype_stays_unforwarded(self):
        config, _ = add_forward_selections(empty_configuration(), CONTROLLED, [sel()])
        self.assertFalse(is_report_forwarded(config, 10, 3, 26))

    def test_uncontrolled_application_process_is_rejected(self):
        config, disp = add_forward_selections(
            empty_configuration(), CONTROLLED, [sel(apid=99)]
        )
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[0]["reason"], REASON_APPLICATION_PROCESS_NOT_CONTROLLED)
        self.assertEqual(config, {})

    def test_duplicate_subtype_is_rejected_as_already_forwarded(self):
        config, disp = add_forward_selections(
            empty_configuration(), CONTROLLED, [sel(), sel()]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(disp[1]["reason"], REASON_ALREADY_FORWARDED)

    def test_report_type_wildcard_subsumes_a_later_subtype(self):
        config, disp = add_forward_selections(
            empty_configuration(),
            CONTROLLED,
            [{"apid": 10, "service_type": 3}, sel()],
        )
        self.assertEqual(disp[1]["reason"], REASON_SUBSUMED_BY_WILDCARD)
        self.assertTrue(is_report_forwarded(config, 10, 3, 25))
        self.assertTrue(is_report_forwarded(config, 10, 3, 26))

    def test_application_process_wildcard_replaces_explicit_entries(self):
        config, _ = add_forward_selections(empty_configuration(), CONTROLLED, [sel()])
        config, disp = add_forward_selections(config, CONTROLLED, [{"apid": 10}])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(config[10]["service_types"], {})
        self.assertTrue(is_report_forwarded(config, 10, 5, 4))

    def test_one_rejected_item_does_not_abandon_the_rest(self):
        config, disp = add_forward_selections(
            empty_configuration(), CONTROLLED, [sel(apid=99), sel(apid=11)]
        )
        self.assertEqual(disp[0]["status"], REJECTED)
        self.assertEqual(disp[1]["status"], ACCEPTED)
        self.assertTrue(is_report_forwarded(config, 11, 3, 25))

    def test_subtype_capacity_is_a_rejection_not_an_exception(self):
        items = [
            sel(message_subtype=n)
            for n in range(1, MAX_SUBTYPES_PER_SERVICE_TYPE + 2)
        ]
        _, disp = add_forward_selections(empty_configuration(), CONTROLLED, items)
        self.assertEqual(disp[-1]["reason"], REASON_SUBTYPE_CAPACITY)
        self.assertEqual(
            sum(1 for d in disp if d["status"] == ACCEPTED),
            MAX_SUBTYPES_PER_SERVICE_TYPE,
        )

    def test_application_process_capacity_is_enforced(self):
        controlled = list(range(1, MAX_APPLICATION_PROCESSES + 2))
        items = [{"apid": a} for a in controlled]
        config, disp = add_forward_selections(empty_configuration(), controlled, items)
        self.assertEqual(len(config), MAX_APPLICATION_PROCESSES)
        self.assertEqual(disp[-1]["status"], REJECTED)

    def test_items_must_be_a_list(self):
        with self.assertRaises(ValueError):
            add_forward_selections(empty_configuration(), CONTROLLED, sel())


class TestDeleteSelections(unittest.TestCase):
    def test_deleting_a_subtype_stops_forwarding_it(self):
        config, _ = add_forward_selections(
            empty_configuration(), CONTROLLED, [sel(), sel(message_subtype=26)]
        )
        config, disp = delete_forward_selections(config, [sel()])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_report_forwarded(config, 10, 3, 25))
        self.assertTrue(is_report_forwarded(config, 10, 3, 26))

    def test_deleting_an_application_process_removes_everything_under_it(self):
        config, _ = add_forward_selections(
            empty_configuration(),
            CONTROLLED,
            [sel(), sel(service_type=5, message_subtype=4)],
        )
        config, disp = delete_forward_selections(config, [{"apid": 10}])
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertEqual(config, {})

    def test_deleting_an_absent_selection_is_rejected(self):
        _, disp = delete_forward_selections(empty_configuration(), [sel()])
        self.assertEqual(disp[0]["reason"], REASON_NOT_IN_CONFIGURATION)

    def test_a_wildcard_cannot_be_partially_deleted(self):
        config, _ = add_forward_selections(
            empty_configuration(), CONTROLLED, [{"apid": 10, "service_type": 3}]
        )
        _, disp = delete_forward_selections(config, [sel()])
        self.assertEqual(disp[0]["reason"], REASON_WILDCARD_NOT_PARTIALLY_DELETABLE)

    def test_deleting_the_report_type_clears_its_wildcard(self):
        config, _ = add_forward_selections(
            empty_configuration(), CONTROLLED, [{"apid": 10, "service_type": 3}]
        )
        config, disp = delete_forward_selections(
            config, [{"apid": 10, "service_type": 3}]
        )
        self.assertEqual(disp[0]["status"], ACCEPTED)
        self.assertFalse(is_report_forwarded(config, 10, 3, 25))


class TestReportAndRequests(unittest.TestCase):
    def test_report_is_sorted_at_every_level(self):
        config, _ = add_forward_selections(
            empty_configuration(),
            CONTROLLED,
            [
                sel(apid=12, service_type=5, message_subtype=4),
                sel(apid=10, message_subtype=26),
                sel(apid=10, message_subtype=25),
            ],
        )
        report = report_configuration(config)
        self.assertEqual(
            [e["apid"] for e in report["application_processes"]], [10, 12]
        )
        self.assertEqual(
            report["application_processes"][0]["report_types"][0]["message_subtypes"],
            [25, 26],
        )

    def test_empty_report_says_it_forwards_nothing(self):
        report = report_configuration(empty_configuration())
        self.assertTrue(report["forwards_nothing"])
        self.assertEqual(report["application_process_count"], 0)

    def test_request_sequence_counts_rejections(self):
        result = apply_forward_control_requests(
            empty_configuration(),
            CONTROLLED,
            [
                {"operation": "add", "items": [sel(), sel(apid=99)]},
                {"operation": "delete", "items": [sel(message_subtype=26)]},
            ],
        )
        self.assertEqual(result["rejected_total"], 2)
        self.assertTrue(is_report_forwarded(result["configuration"], 10, 3, 25))

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            apply_forward_control_requests(
                empty_configuration(), CONTROLLED, [{"operation": "purge"}]
            )

    def test_empty_request_list_raises(self):
        with self.assertRaises(ValueError):
            apply_forward_control_requests(empty_configuration(), CONTROLLED, [])


if __name__ == "__main__":
    unittest.main()

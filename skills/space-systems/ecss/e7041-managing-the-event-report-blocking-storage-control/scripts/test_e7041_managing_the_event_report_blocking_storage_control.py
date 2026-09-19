"""Contract test for the event-report-blocking-storage-control leaf (stdlib unittest)."""

import unittest

from e7041_managing_the_event_report_blocking_storage_control_logic import (
    APID_IDLE,
    EVENT_ID_MAX,
    apply_instruction,
    apply_request,
    assess_event_report_blocking_storage_control,
    blocked_set,
    blocked_total,
    cross_store_census,
    grade_instruction,
    is_storage_blocked,
    report_blocking_configuration,
    storage_disposition,
    validate_application_process_id,
    validate_event_catalogue,
    validate_event_definition,
    validate_event_definition_id,
    validate_packet_store,
    validate_packet_stores,
)


def store(store_id="PS-A", **kw):
    record = {
        "store_id": store_id,
        "application_process_ids": [10, 11],
        "supports_event_blocking": True,
        "blocked_capacity": 4,
        "blocked": {},
    }
    record.update(kw)
    return record


def event(eid=100, apid=10, **kw):
    record = {
        "event_definition_id": eid,
        "application_process_id": apid,
        "severity": "low",
        "retention_mandatory": False,
    }
    record.update(kw)
    return record


def instruction(operation="add", store_id="PS-A", apid=10, eid=100):
    return {
        "operation": operation,
        "store_id": store_id,
        "application_process_id": apid,
        "event_definition_id": eid,
    }


CATALOGUE = [
    event(100, 10),
    event(101, 10, severity="high"),
    event(102, 10, retention_mandatory=True),
    event(200, 11),
]


class TestIdentifierValidation(unittest.TestCase):
    def test_idle_application_process_id_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(APID_IDLE)

    def test_out_of_range_application_process_id_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(4096)

    def test_boolean_application_process_id_raises(self):
        with self.assertRaises(ValueError):
            validate_application_process_id(True)

    def test_zero_event_definition_id_raises(self):
        with self.assertRaises(ValueError):
            validate_event_definition_id(0)

    def test_top_event_definition_id_is_accepted(self):
        self.assertEqual(validate_event_definition_id(EVENT_ID_MAX), EVENT_ID_MAX)


class TestEventDefinitions(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_event_definition(
            {"event_definition_id": 5, "application_process_id": 10}
        )
        self.assertEqual(norm["severity"], "informative")
        self.assertFalse(norm["retention_mandatory"])

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_event_definition(event(100, 10, severity="catastrophic"))

    def test_non_boolean_retention_flag_raises(self):
        with self.assertRaises(ValueError):
            validate_event_definition(event(100, 10, retention_mandatory="yes"))

    def test_duplicate_definition_for_same_process_raises(self):
        with self.assertRaises(ValueError):
            validate_event_catalogue([event(100, 10), event(100, 10)])

    def test_same_identifier_for_two_processes_is_two_definitions(self):
        catalogue = validate_event_catalogue([event(100, 10), event(100, 11)])
        self.assertEqual(len(catalogue), 2)

    def test_empty_catalogue_raises(self):
        with self.assertRaises(ValueError):
            validate_event_catalogue([])


class TestPacketStoreValidation(unittest.TestCase):
    def test_empty_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(""))

    def test_no_served_processes_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(application_process_ids=[]))

    def test_duplicate_served_process_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(application_process_ids=[10, 10]))

    def test_blocking_an_unserved_process_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(blocked={12: [100]}))

    def test_blocked_set_over_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(
                store(blocked_capacity=1, blocked={10: [100, 101]})
            )

    def test_negative_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(blocked_capacity=-1))

    def test_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_stores([store("PS-A"), store("PS-A")])


class TestDisposition(unittest.TestCase):
    def test_empty_configuration_retains_everything(self):
        stores = validate_packet_stores([store()])
        self.assertEqual(
            storage_disposition(stores["PS-A"], {"event_definition_id": 100,
                                                 "application_process_id": 10}),
            "retained",
        )

    def test_blocked_identifier_is_dropped(self):
        stores = validate_packet_stores([store(blocked={10: [100]})])
        self.assertEqual(
            storage_disposition(stores["PS-A"], {"event_definition_id": 100,
                                                 "application_process_id": 10}),
            "dropped",
        )

    def test_block_is_per_application_process(self):
        stores = validate_packet_stores([store(blocked={10: [100]})])
        self.assertTrue(is_storage_blocked(stores["PS-A"], 10, 100))
        self.assertFalse(is_storage_blocked(stores["PS-A"], 11, 100))

    def test_store_without_blocking_support_retains_everything(self):
        stores = validate_packet_stores(
            [store(supports_event_blocking=False, blocked={})]
        )
        self.assertEqual(
            storage_disposition(stores["PS-A"], {"event_definition_id": 100,
                                                 "application_process_id": 10}),
            "retained",
        )

    def test_arrival_from_unserved_process_raises(self):
        stores = validate_packet_stores([store()])
        with self.assertRaises(ValueError):
            storage_disposition(
                stores["PS-A"],
                {"event_definition_id": 100, "application_process_id": 12},
            )


class TestInstructionGrading(unittest.TestCase):
    def setUp(self):
        self.stores = validate_packet_stores([store()])
        self.catalogue = validate_event_catalogue(CATALOGUE)

    def test_plain_add_is_accepted(self):
        accepted, reason = grade_instruction(
            instruction(), self.stores, self.catalogue
        )
        self.assertTrue(accepted)
        self.assertEqual(reason, "blocked-for-storage")

    def test_unknown_store_is_refused(self):
        accepted, reason = grade_instruction(
            instruction(store_id="PS-Z"), self.stores, self.catalogue
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "unknown-packet-store")

    def test_unknown_event_definition_is_refused(self):
        accepted, reason = grade_instruction(
            instruction(eid=999), self.stores, self.catalogue
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "unknown-event-definition")

    def test_unserved_application_process_is_refused(self):
        accepted, reason = grade_instruction(
            instruction(apid=12), self.stores, self.catalogue
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "application-process-not-served-by-store")

    def test_retention_mandatory_event_is_refused(self):
        accepted, reason = grade_instruction(
            instruction(eid=102), self.stores, self.catalogue
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "event-definition-is-retention-mandatory")

    def test_already_blocked_add_is_refused(self):
        stores = validate_packet_stores([store(blocked={10: [100]})])
        accepted, reason = grade_instruction(instruction(), stores, self.catalogue)
        self.assertFalse(accepted)
        self.assertEqual(reason, "already-blocked")

    def test_delete_of_unblocked_identifier_is_refused(self):
        accepted, reason = grade_instruction(
            instruction("delete"), self.stores, self.catalogue
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "not-currently-blocked")

    def test_capacity_refusal(self):
        stores = validate_packet_stores(
            [store(blocked_capacity=1, blocked={10: [101]})]
        )
        accepted, reason = grade_instruction(instruction(), stores, self.catalogue)
        self.assertFalse(accepted)
        self.assertEqual(reason, "blocked-set-capacity-exceeded")

    def test_store_without_configuration_is_refused(self):
        stores = validate_packet_stores([store(supports_event_blocking=False)])
        accepted, reason = grade_instruction(instruction(), stores, self.catalogue)
        self.assertFalse(accepted)
        self.assertEqual(reason, "store-has-no-event-report-storage-control")

    def test_unknown_operation_raises(self):
        with self.assertRaises(ValueError):
            grade_instruction(
                {
                    "operation": "toggle",
                    "store_id": "PS-A",
                    "application_process_id": 10,
                    "event_definition_id": 100,
                },
                self.stores,
                self.catalogue,
            )

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            grade_instruction(
                {"operation": "add", "store_id": "PS-A"},
                self.stores,
                self.catalogue,
            )


class TestApplication(unittest.TestCase):
    def setUp(self):
        self.stores = validate_packet_stores([store()])
        self.catalogue = validate_event_catalogue(CATALOGUE)

    def test_accepted_add_changes_the_configuration(self):
        apply_instruction(instruction(), self.stores, self.catalogue)
        self.assertEqual(blocked_set(self.stores["PS-A"], 10), [100])

    def test_refused_add_leaves_the_configuration_alone(self):
        apply_instruction(instruction(eid=102), self.stores, self.catalogue)
        self.assertEqual(blocked_set(self.stores["PS-A"], 10), [])

    def test_delete_empties_the_entry(self):
        apply_instruction(instruction(), self.stores, self.catalogue)
        apply_instruction(instruction("delete"), self.stores, self.catalogue)
        self.assertEqual(blocked_total(self.stores["PS-A"]), 0)

    def test_one_refusal_does_not_void_the_rest(self):
        results = apply_request(
            [instruction(eid=102), instruction(eid=100), instruction(eid=101)],
            self.stores,
            self.catalogue,
        )
        self.assertEqual([r["accepted"] for r in results], [False, True, True])
        self.assertEqual(blocked_set(self.stores["PS-A"], 10), [100, 101])

    def test_report_is_sorted_and_carries_totals(self):
        apply_request(
            [instruction(eid=101), instruction(eid=100)],
            self.stores,
            self.catalogue,
        )
        report = report_blocking_configuration(self.stores)
        self.assertEqual(report[0]["store_id"], "PS-A")
        self.assertEqual(
            report[0]["entries"][0]["blocked_event_definition_ids"], [100, 101]
        )
        self.assertEqual(report[0]["blocked_total"], 2)

    def test_non_sequence_request_raises(self):
        with self.assertRaises(ValueError):
            apply_request(instruction(), self.stores, self.catalogue)


class TestCrossStoreCensus(unittest.TestCase):
    def test_blocked_in_one_of_two_stores_is_still_retrievable(self):
        stores = validate_packet_stores(
            [store("PS-A", blocked={10: [100]}), store("PS-B")]
        )
        catalogue = validate_event_catalogue(CATALOGUE)
        self.assertEqual(cross_store_census(stores, catalogue), [])

    def test_blocked_everywhere_is_reported(self):
        stores = validate_packet_stores(
            [store("PS-A", blocked={10: [100]}), store("PS-B", blocked={10: [100]})]
        )
        catalogue = validate_event_catalogue(CATALOGUE)
        census = cross_store_census(stores, catalogue)
        self.assertEqual(len(census), 1)
        self.assertEqual(census[0]["event_definition_id"], 100)
        self.assertEqual(census[0]["store_ids"], ["PS-A", "PS-B"])

    def test_store_without_blocking_support_keeps_the_event_retrievable(self):
        stores = validate_packet_stores(
            [
                store("PS-A", blocked={10: [100]}),
                store("PS-B", supports_event_blocking=False),
            ]
        )
        catalogue = validate_event_catalogue(CATALOGUE)
        self.assertEqual(cross_store_census(stores, catalogue), [])


class TestAssessment(unittest.TestCase):
    def test_clean_run_reports_no_findings(self):
        report = assess_event_report_blocking_storage_control(
            {
                "packet_stores": [store("PS-A"), store("PS-B")],
                "event_definitions": CATALOGUE,
                "instructions": [instruction(eid=100)],
            }
        )
        self.assertTrue(report["clean"])
        self.assertEqual(report["accepted_count"], 1)
        self.assertEqual(report["rejected_count"], 0)

    def test_refusal_and_census_both_reach_the_findings(self):
        report = assess_event_report_blocking_storage_control(
            {
                "packet_stores": [store("PS-A")],
                "event_definitions": CATALOGUE,
                "instructions": [instruction(eid=102), instruction(eid=100)],
            }
        )
        self.assertFalse(report["clean"])
        self.assertEqual(report["rejected_count"], 1)
        self.assertEqual(len(report["unretrievable_events"]), 1)
        self.assertEqual(len(report["findings"]), 2)

    def test_arrivals_are_graded_against_the_resulting_configuration(self):
        report = assess_event_report_blocking_storage_control(
            {
                "packet_stores": [store("PS-A")],
                "event_definitions": CATALOGUE,
                "instructions": [instruction(eid=100)],
                "arrivals": [
                    {"store_id": "PS-A", "application_process_id": 10,
                     "event_definition_id": 100},
                    {"store_id": "PS-A", "application_process_id": 10,
                     "event_definition_id": 101},
                ],
            }
        )
        self.assertEqual(
            [d["disposition"] for d in report["dispositions"]],
            ["dropped", "retained"],
        )

    def test_arrival_naming_unknown_store_raises(self):
        with self.assertRaises(ValueError):
            assess_event_report_blocking_storage_control(
                {
                    "packet_stores": [store("PS-A")],
                    "event_definitions": CATALOGUE,
                    "arrivals": [{"store_id": "PS-Z", "application_process_id": 10,
                                  "event_definition_id": 100}],
                }
            )

    def test_missing_spec_key_raises(self):
        with self.assertRaises(ValueError):
            assess_event_report_blocking_storage_control({"packet_stores": [store()]})

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_event_report_blocking_storage_control([store()])


if __name__ == "__main__":
    unittest.main()

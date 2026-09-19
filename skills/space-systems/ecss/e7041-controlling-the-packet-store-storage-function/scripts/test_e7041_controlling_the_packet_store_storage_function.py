"""Contract test for the e7041 packet-store storage-function control leaf."""

import unittest

from e7041_controlling_the_packet_store_storage_function_logic import (
    COMMAND_ADD_TYPES,
    COMMAND_DELETE_TYPES,
    COMMAND_DISABLE,
    COMMAND_ENABLE,
    OUTCOME_APPLIED,
    OUTCOME_NO_CHANGE,
    OUTCOME_REJECTED_UNKNOWN_STORE,
    OUTCOME_REJECTED_UNKNOWN_TYPE,
    STORAGE_OFF,
    STORAGE_ON,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    add_report_types,
    apply_commands,
    assess_storage_control,
    delete_report_types,
    set_storage_status,
    storage_control_configuration,
    validate_command,
    validate_packet_store,
    validate_store_set,
)


def store(store_id="PS-SCIENCE", status=STORAGE_OFF, types=("TM-3-25", "TM-5-1")):
    return {"id": store_id, "storage_status": status, "report_types": list(types)}


def stores():
    return [
        store("PS-SCIENCE", STORAGE_OFF, ("TM-3-25",)),
        store("PS-EVENTS", STORAGE_ON, ("TM-5-1", "TM-5-2")),
        store("PS-DIAG", STORAGE_OFF, ()),
    ]


def command(action=COMMAND_ENABLE, ids=("PS-SCIENCE",), **kw):
    record = {"action": action, "store_ids": list(ids)}
    record.update(kw)
    return record


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_store_normalizes(self):
        record = validate_packet_store(store())
        self.assertEqual(record["id"], "PS-SCIENCE")
        self.assertEqual(record["report_types"], ["TM-3-25", "TM-5-1"])

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store("PS-SCIENCE")

    def test_an_empty_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(store_id="   "))

    def test_an_unknown_storage_status_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(status="paused"))

    def test_a_repeated_report_type_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(types=("TM-3-25", "TM-3-25")))

    def test_a_store_with_no_report_types_is_valid(self):
        self.assertEqual(validate_packet_store(store(types=()))["report_types"], [])

    def test_a_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store_set([store("PS-A"), store("PS-A")])

    def test_the_store_set_keeps_declaration_order(self):
        state = validate_store_set(stores())
        self.assertEqual(state["order"], ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"])


class TestCommandValidation(unittest.TestCase):
    def test_a_valid_enable_command_normalizes(self):
        request = validate_command(command())
        self.assertEqual(request["action"], COMMAND_ENABLE)
        self.assertEqual(request["store_ids"], ["PS-SCIENCE"])

    def test_an_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(action="freeze-storage"))

    def test_a_command_naming_no_store_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(ids=()))

    def test_a_command_naming_a_store_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(ids=("PS-A", "PS-A")))

    def test_an_add_types_command_without_types_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(action=COMMAND_ADD_TYPES, report_types=[]))

    def test_an_enable_command_carrying_report_types_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(report_types=["TM-3-25"]))


class TestStorageSwitching(unittest.TestCase):
    def test_enabling_an_off_store_applies(self):
        result = set_storage_status(store(status=STORAGE_OFF), STORAGE_ON)
        self.assertTrue(result["changed"])
        self.assertEqual(result["outcome"], OUTCOME_APPLIED)
        self.assertEqual(result["store"]["storage_status"], STORAGE_ON)

    def test_enabling_an_already_on_store_is_accepted_and_changes_nothing(self):
        result = set_storage_status(store(status=STORAGE_ON), STORAGE_ON)
        self.assertFalse(result["changed"])
        self.assertEqual(result["outcome"], OUTCOME_NO_CHANGE)

    def test_disabling_an_on_store_applies(self):
        result = set_storage_status(store(status=STORAGE_ON), STORAGE_OFF)
        self.assertEqual(result["store"]["storage_status"], STORAGE_OFF)

    def test_an_unknown_target_state_raises(self):
        with self.assertRaises(ValueError):
            set_storage_status(store(), "standby")


class TestReportTypeLists(unittest.TestCase):
    def test_adding_a_new_type_applies(self):
        result = add_report_types(store(types=("TM-3-25",)), ["TM-5-1"])
        self.assertEqual(result["added"], ["TM-5-1"])
        self.assertEqual(result["store"]["report_types"], ["TM-3-25", "TM-5-1"])

    def test_adding_a_type_already_held_changes_nothing(self):
        result = add_report_types(store(types=("TM-3-25",)), ["TM-3-25"])
        self.assertEqual(result["added"], [])
        self.assertEqual(result["outcome"], OUTCOME_NO_CHANGE)
        self.assertEqual(result["already_present"], ["TM-3-25"])

    def test_deleting_a_held_type_applies(self):
        result = delete_report_types(store(types=("TM-3-25", "TM-5-1")), ["TM-3-25"])
        self.assertEqual(result["removed"], ["TM-3-25"])
        self.assertEqual(result["store"]["report_types"], ["TM-5-1"])

    def test_deleting_a_type_not_held_is_rejected_for_that_type(self):
        result = delete_report_types(store(types=("TM-3-25",)), ["TM-9-9"])
        self.assertEqual(result["missing"], ["TM-9-9"])
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_UNKNOWN_TYPE)
        self.assertEqual(result["store"]["report_types"], ["TM-3-25"])

    def test_a_mixed_delete_removes_what_it_can(self):
        result = delete_report_types(store(types=("TM-3-25", "TM-5-1")),
                                     ["TM-3-25", "TM-9-9"])
        self.assertEqual(result["removed"], ["TM-3-25"])
        self.assertEqual(result["missing"], ["TM-9-9"])

    def test_a_report_type_list_is_never_duplicated_by_an_add(self):
        result = add_report_types(store(types=("TM-3-25",)),
                                  ["TM-5-1", "TM-3-25"])
        self.assertEqual(result["store"]["report_types"], ["TM-3-25", "TM-5-1"])


class TestPartialFailure(unittest.TestCase):
    def test_an_unknown_store_fails_for_that_store_alone(self):
        run = apply_commands(stores(),
                             [command(ids=("PS-SCIENCE", "PS-GHOST", "PS-DIAG"))])
        outcomes = [entry["outcome"] for entry in run["steps"][0]["results"]]
        self.assertEqual(outcomes[1], OUTCOME_REJECTED_UNKNOWN_STORE)
        self.assertEqual(outcomes[0], OUTCOME_APPLIED)
        self.assertEqual(outcomes[2], OUTCOME_APPLIED)

    def test_the_known_stores_are_still_switched_on(self):
        run = apply_commands(stores(), [command(ids=("PS-GHOST", "PS-DIAG"))])
        self.assertEqual(
            run["state"]["stores"]["PS-DIAG"]["storage_status"], STORAGE_ON
        )

    def test_every_rejection_is_notified(self):
        run = apply_commands(stores(), [command(ids=("PS-GHOST",))])
        self.assertEqual(len(run["steps"][0]["findings"]), 1)

    def test_a_non_list_command_sequence_raises(self):
        with self.assertRaises(ValueError):
            apply_commands(stores(), command())


class TestConfigurationReport(unittest.TestCase):
    def test_the_report_covers_every_store_in_order(self):
        state = validate_store_set(stores())
        report = storage_control_configuration(state)
        self.assertEqual(report["store_count"], 3)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"],
        )

    def test_the_storing_total_counts_only_stores_switched_on(self):
        state = validate_store_set(stores())
        self.assertEqual(storage_control_configuration(state)["storing_count"], 1)

    def test_each_entry_carries_its_report_type_count(self):
        state = validate_store_set(stores())
        entries = storage_control_configuration(state)["entries"]
        self.assertEqual(entries[1]["report_type_count"], 2)
        self.assertEqual(entries[2]["report_type_count"], 0)


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_sequence_is_accepted(self):
        result = assess_storage_control(
            stores(),
            [
                command(COMMAND_ADD_TYPES, ("PS-DIAG",), report_types=["TM-3-25"]),
                command(COMMAND_ENABLE, ("PS-DIAG",)),
            ],
        )
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_an_unknown_store_makes_the_run_partially_rejected(self):
        result = assess_storage_control(stores(), [command(ids=("PS-GHOST",))])
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["rejected"], [(COMMAND_ENABLE, "PS-GHOST")])

    def test_a_report_type_change_does_not_stop_a_running_store(self):
        result = assess_storage_control(
            stores(),
            [command(COMMAND_ADD_TYPES, ("PS-EVENTS",), report_types=["TM-5-4"])],
        )
        entry = result["configuration"]["entries"][1]
        self.assertEqual(entry["storage_status"], STORAGE_ON)
        self.assertIn("TM-5-4", entry["report_types"])

    def test_deleting_an_absent_type_is_counted_as_a_rejection(self):
        result = assess_storage_control(
            stores(),
            [command(COMMAND_DELETE_TYPES, ("PS-SCIENCE",),
                     report_types=["TM-9-9"])],
        )
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_disable_then_enable_leaves_the_store_on(self):
        result = assess_storage_control(
            stores(),
            [command(COMMAND_DISABLE, ("PS-EVENTS",)),
             command(COMMAND_ENABLE, ("PS-EVENTS",))],
        )
        self.assertEqual(
            result["configuration"]["entries"][1]["storage_status"], STORAGE_ON
        )
        self.assertTrue(result["accepted"])

    def test_an_empty_command_sequence_leaves_the_configuration_intact(self):
        result = assess_storage_control(stores(), [])
        self.assertEqual(result["configuration"]["storing_count"], 1)
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)

    def test_an_invalid_store_set_raises_before_any_command_runs(self):
        broken = stores()
        broken[0]["storage_status"] = "paused"
        with self.assertRaises(ValueError):
            assess_storage_control(broken, [command()])


if __name__ == "__main__":
    unittest.main()

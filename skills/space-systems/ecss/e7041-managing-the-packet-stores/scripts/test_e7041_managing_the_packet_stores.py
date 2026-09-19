"""Contract test for the e7041 packet-store management leaf."""

import unittest

from e7041_managing_the_packet_stores_logic import (
    COMMAND_CHANGE_CHANNEL,
    COMMAND_CHANGE_TYPE,
    COMMAND_CREATE,
    COMMAND_DELETE,
    COMMAND_RESIZE,
    OUTCOME_APPLIED,
    OUTCOME_NO_CHANGE,
    OUTCOME_REJECTED_BELOW_OCCUPANCY,
    OUTCOME_REJECTED_BUDGET,
    OUTCOME_REJECTED_DUPLICATE_STORE,
    OUTCOME_REJECTED_NOT_EMPTY,
    OUTCOME_REJECTED_NOT_QUIESCENT,
    OUTCOME_REJECTED_UNKNOWN_CHANNEL,
    OUTCOME_REJECTED_UNKNOWN_STORE,
    STORAGE_OFF,
    STORAGE_ON,
    STORE_TYPE_BOUNDED,
    STORE_TYPE_CIRCULAR,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    allocated_octets,
    apply_commands,
    assess_packet_store_management,
    budget_headroom,
    configuration_report,
    is_quiescent,
    validate_command,
    validate_configuration,
    validate_store_definition,
)

BUDGET = 100000


def store(store_id="PS-SCIENCE", store_type=STORE_TYPE_BOUNDED, capacity=20000,
          occupied=0, channel=1, storage=STORAGE_OFF, retrieval=False):
    return {
        "id": store_id,
        "store_type": store_type,
        "capacity_octets": capacity,
        "occupied_octets": occupied,
        "virtual_channel": channel,
        "storage_status": storage,
        "retrieval_engaged": retrieval,
    }


def configuration(stores=None, budget=BUDGET, channels=(0, 1, 2, 3)):
    if stores is None:
        stores = [
            store("PS-SCIENCE", STORE_TYPE_BOUNDED, 20000, 8000, 1),
            store("PS-EVENTS", STORE_TYPE_CIRCULAR, 10000, 0, 2,
                  storage=STORAGE_ON),
            store("PS-DIAG", STORE_TYPE_BOUNDED, 5000, 500, 2, retrieval=True),
        ]
    return {
        "stores": stores,
        "memory_budget_octets": budget,
        "virtual_channels": list(channels),
    }


def command(action=COMMAND_RESIZE, store_id="PS-SCIENCE", **kw):
    record = {"action": action, "store_id": store_id}
    record.update(kw)
    return record


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_store_normalizes(self):
        record = validate_store_definition(store())
        self.assertEqual(record["capacity_octets"], 20000)
        self.assertEqual(record["occupied_octets"], 0)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition("PS-SCIENCE")

    def test_a_zero_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(store(capacity=0))

    def test_an_unknown_store_type_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(store(store_type="ring"))

    def test_occupancy_above_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(store(capacity=100, occupied=200))

    def test_a_boolean_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(store(capacity=True))

    def test_a_negative_virtual_channel_raises(self):
        with self.assertRaises(ValueError):
            validate_store_definition(store(channel=-1))


class TestConfigurationValidation(unittest.TestCase):
    def test_a_valid_configuration_normalizes(self):
        state = validate_configuration(configuration())
        self.assertEqual(state["order"], ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"])

    def test_a_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_configuration(configuration([store("PS-A"), store("PS-A")]))

    def test_an_over_allocated_budget_raises(self):
        with self.assertRaises(ValueError):
            validate_configuration(configuration(budget=1000))

    def test_a_store_on_a_channel_the_craft_lacks_raises(self):
        with self.assertRaises(ValueError):
            validate_configuration(configuration([store(channel=9)]))

    def test_an_empty_virtual_channel_list_raises(self):
        with self.assertRaises(ValueError):
            validate_configuration(configuration(channels=()))

    def test_a_repeated_virtual_channel_raises(self):
        with self.assertRaises(ValueError):
            validate_configuration(configuration(channels=(0, 1, 1)))

    def test_the_allocated_total_sums_the_capacities(self):
        state = validate_configuration(configuration())
        self.assertEqual(allocated_octets(state), 35000)

    def test_the_headroom_is_the_budget_less_the_allocation(self):
        state = validate_configuration(configuration())
        self.assertEqual(budget_headroom(state), 65000)


class TestCommandValidation(unittest.TestCase):
    def test_a_valid_create_normalizes(self):
        request = validate_command(
            command(COMMAND_CREATE, "PS-NEW", store_type=STORE_TYPE_BOUNDED,
                    capacity_octets=1000, virtual_channel=0)
        )
        self.assertEqual(request["capacity_octets"], 1000)

    def test_a_create_without_a_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_command(
                command(COMMAND_CREATE, "PS-NEW", store_type=STORE_TYPE_BOUNDED,
                        virtual_channel=0)
            )

    def test_a_resize_without_a_capacity_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(COMMAND_RESIZE))

    def test_an_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(action="rename-packet-store"))

    def test_a_command_without_a_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_command({"action": COMMAND_DELETE})


class TestQuiescence(unittest.TestCase):
    def test_a_store_off_and_unread_is_quiescent(self):
        self.assertTrue(is_quiescent(store()))

    def test_a_storing_store_is_not_quiescent(self):
        self.assertFalse(is_quiescent(store(storage=STORAGE_ON)))

    def test_a_store_being_read_is_not_quiescent(self):
        self.assertFalse(is_quiescent(store(retrieval=True)))


class TestCreate(unittest.TestCase):
    def test_a_create_within_budget_applies(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CREATE, "PS-NEW", store_type=STORE_TYPE_CIRCULAR,
                     capacity_octets=5000, virtual_channel=0)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_APPLIED)
        self.assertIn("PS-NEW", run["state"]["order"])

    def test_a_create_reusing_an_identity_is_refused(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CREATE, "PS-EVENTS", store_type=STORE_TYPE_BOUNDED,
                     capacity_octets=100, virtual_channel=0)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_DUPLICATE_STORE)

    def test_a_create_past_the_budget_is_refused(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CREATE, "PS-HUGE", store_type=STORE_TYPE_BOUNDED,
                     capacity_octets=90000, virtual_channel=0)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_BUDGET)

    def test_a_create_on_a_channel_the_craft_lacks_is_refused(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CREATE, "PS-NEW", store_type=STORE_TYPE_BOUNDED,
                     capacity_octets=100, virtual_channel=9)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_UNKNOWN_CHANNEL)

    def test_a_created_store_starts_switched_off_and_empty(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CREATE, "PS-NEW", store_type=STORE_TYPE_BOUNDED,
                     capacity_octets=100, virtual_channel=0)],
        )
        created = run["state"]["stores"]["PS-NEW"]
        self.assertEqual(created["storage_status"], STORAGE_OFF)
        self.assertEqual(created["occupied_octets"], 0)


class TestDelete(unittest.TestCase):
    def test_a_quiescent_store_is_deleted(self):
        run = apply_commands(configuration(), [command(COMMAND_DELETE)])
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_APPLIED)
        self.assertNotIn("PS-SCIENCE", run["state"]["order"])

    def test_deleting_a_storing_store_is_refused(self):
        run = apply_commands(
            configuration(), [command(COMMAND_DELETE, "PS-EVENTS")]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_NOT_QUIESCENT)

    def test_deleting_a_store_that_holds_data_is_reported(self):
        run = apply_commands(configuration(), [command(COMMAND_DELETE)])
        self.assertEqual(run["steps"][0]["result"]["lost_octets"], 8000)
        self.assertEqual(len(run["steps"][0]["findings"]), 1)

    def test_deleting_a_store_frees_its_budget(self):
        run = apply_commands(configuration(), [command(COMMAND_DELETE)])
        self.assertEqual(allocated_octets(run["state"]), 15000)

    def test_deleting_an_unknown_store_is_refused(self):
        run = apply_commands(configuration(), [command(COMMAND_DELETE, "PS-GHOST")])
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_UNKNOWN_STORE)


class TestResize(unittest.TestCase):
    def test_a_resize_within_budget_and_occupancy_applies(self):
        run = apply_commands(
            configuration(), [command(COMMAND_RESIZE, capacity_octets=30000)]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_APPLIED)
        self.assertEqual(
            run["state"]["stores"]["PS-SCIENCE"]["capacity_octets"], 30000
        )

    def test_a_resize_below_the_current_occupancy_is_refused(self):
        run = apply_commands(
            configuration(), [command(COMMAND_RESIZE, capacity_octets=100)]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_BELOW_OCCUPANCY)

    def test_a_resize_exactly_to_the_occupancy_is_allowed(self):
        run = apply_commands(
            configuration(), [command(COMMAND_RESIZE, capacity_octets=8000)]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_APPLIED)

    def test_a_resize_past_the_budget_is_refused(self):
        run = apply_commands(
            configuration(), [command(COMMAND_RESIZE, capacity_octets=99000)]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_BUDGET)

    def test_a_resize_to_the_same_capacity_changes_nothing(self):
        run = apply_commands(
            configuration(), [command(COMMAND_RESIZE, capacity_octets=20000)]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_NO_CHANGE)

    def test_a_resize_on_a_store_being_read_is_refused(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_RESIZE, "PS-DIAG", capacity_octets=6000)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_NOT_QUIESCENT)


class TestRetypeAndChannel(unittest.TestCase):
    def test_retyping_a_quiescent_empty_store_applies(self):
        stores = [store("PS-EMPTY", STORE_TYPE_BOUNDED, 1000, 0, 0)]
        run = apply_commands(
            configuration(stores),
            [command(COMMAND_CHANGE_TYPE, "PS-EMPTY",
                     store_type=STORE_TYPE_CIRCULAR)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_APPLIED)

    def test_retyping_a_store_that_holds_packets_is_refused(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CHANGE_TYPE, store_type=STORE_TYPE_CIRCULAR)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_NOT_EMPTY)

    def test_retyping_to_the_same_type_changes_nothing(self):
        stores = [store("PS-EMPTY", STORE_TYPE_BOUNDED, 1000, 0, 0)]
        run = apply_commands(
            configuration(stores),
            [command(COMMAND_CHANGE_TYPE, "PS-EMPTY",
                     store_type=STORE_TYPE_BOUNDED)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"], OUTCOME_NO_CHANGE)

    def test_moving_a_quiescent_store_to_another_channel_applies(self):
        run = apply_commands(
            configuration(), [command(COMMAND_CHANGE_CHANNEL, virtual_channel=3)]
        )
        self.assertEqual(run["state"]["stores"]["PS-SCIENCE"]["virtual_channel"], 3)

    def test_moving_a_store_to_a_channel_the_craft_lacks_is_refused(self):
        run = apply_commands(
            configuration(), [command(COMMAND_CHANGE_CHANNEL, virtual_channel=9)]
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_UNKNOWN_CHANNEL)

    def test_moving_a_storing_store_is_refused(self):
        run = apply_commands(
            configuration(),
            [command(COMMAND_CHANGE_CHANNEL, "PS-EVENTS", virtual_channel=3)],
        )
        self.assertEqual(run["steps"][0]["result"]["outcome"],
                         OUTCOME_REJECTED_NOT_QUIESCENT)


class TestConfigurationReport(unittest.TestCase):
    def test_the_report_covers_every_store_in_order(self):
        state = validate_configuration(configuration())
        report = configuration_report(state)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"],
        )

    def test_the_report_carries_the_budget_figures(self):
        state = validate_configuration(configuration())
        report = configuration_report(state)
        self.assertEqual(report["allocated_octets"], 35000)
        self.assertEqual(report["free_octets"], 65000)

    def test_the_budget_utilisation_is_the_allocated_share(self):
        state = validate_configuration(configuration())
        report = configuration_report(state)
        self.assertAlmostEqual(report["budget_utilisation"], 0.35, places=9)

    def test_a_full_budget_reports_a_utilisation_of_one(self):
        stores = [store("PS-ALL", STORE_TYPE_BOUNDED, 1000, 0, 0)]
        state = validate_configuration(configuration(stores, budget=1000))
        report = configuration_report(state)
        self.assertAlmostEqual(report["budget_utilisation"], 1.0, places=9)
        self.assertEqual(report["free_octets"], 0)

    def test_each_entry_says_whether_the_store_is_quiescent(self):
        state = validate_configuration(configuration())
        entries = configuration_report(state)["entries"]
        self.assertTrue(entries[0]["quiescent"])
        self.assertFalse(entries[1]["quiescent"])
        self.assertFalse(entries[2]["quiescent"])


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_sequence_is_accepted(self):
        result = assess_packet_store_management(
            configuration(),
            [command(COMMAND_RESIZE, capacity_octets=30000),
             command(COMMAND_CHANGE_CHANNEL, virtual_channel=3)],
        )
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_refused_command_makes_the_run_partially_rejected(self):
        result = assess_packet_store_management(
            configuration(), [command(COMMAND_DELETE, "PS-EVENTS")]
        )
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["rejected"], [(COMMAND_DELETE, "PS-EVENTS")])

    def test_a_refusal_does_not_stop_the_next_command(self):
        result = assess_packet_store_management(
            configuration(),
            [command(COMMAND_DELETE, "PS-EVENTS"),
             command(COMMAND_RESIZE, capacity_octets=30000)],
        )
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(
            result["report"]["entries"][0]["capacity_octets"], 30000
        )

    def test_a_delete_then_create_reuses_the_freed_budget(self):
        result = assess_packet_store_management(
            configuration(),
            [command(COMMAND_DELETE),
             command(COMMAND_CREATE, "PS-NEW", store_type=STORE_TYPE_CIRCULAR,
                     capacity_octets=80000, virtual_channel=0)],
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(result["report"]["allocated_octets"], 95000)

    def test_every_refusal_is_notified(self):
        result = assess_packet_store_management(
            configuration(),
            [command(COMMAND_CHANGE_TYPE, store_type=STORE_TYPE_CIRCULAR),
             command(COMMAND_RESIZE, "PS-DIAG", capacity_octets=6000)],
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_an_empty_command_sequence_leaves_the_configuration_intact(self):
        result = assess_packet_store_management(configuration(), [])
        self.assertEqual(result["report"]["store_count"], 3)
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)

    def test_an_invalid_configuration_raises_before_any_command_runs(self):
        broken = configuration()
        broken["stores"][0]["store_type"] = "ring"
        with self.assertRaises(ValueError):
            assess_packet_store_management(broken, [command(COMMAND_DELETE)])


if __name__ == "__main__":
    unittest.main()

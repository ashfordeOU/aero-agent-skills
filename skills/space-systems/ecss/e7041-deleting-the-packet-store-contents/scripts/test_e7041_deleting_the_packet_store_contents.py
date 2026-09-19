"""Contract test for the e7041 packet-store content deletion leaf."""

import unittest

from e7041_deleting_the_packet_store_contents_logic import (
    OUTCOME_DELETED,
    OUTCOME_DELETED_CLAMPED,
    OUTCOME_NOTHING_TO_DELETE,
    OUTCOME_REJECTED_RANGE_RETRIEVAL,
    OUTCOME_REJECTED_UNKNOWN_STORE,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    apply_commands,
    assess_content_deletion,
    content_report,
    delete_contents,
    deletion_candidates,
    occupied_octets,
    oldest_storage_time,
    protected_by_open_retrieval,
    validate_command,
    validate_packet_store,
    validate_store_set,
)

TIMES = (100.0, 200.0, 300.0, 400.0)


def store(store_id="PS-SCIENCE", times=TIMES, cursor=None, range_active=False,
          size=64):
    record = {
        "id": store_id,
        "packets": [
            {"id": "PKT-%d" % (i + 1), "storage_time": t, "size_octets": size}
            for i, t in enumerate(times)
        ],
        "range_retrieval_active": range_active,
    }
    if cursor is not None:
        record["open_retrieval_cursor"] = cursor
    return record


def stores():
    return [
        store("PS-SCIENCE"),
        store("PS-EVENTS", cursor=300.0),
        store("PS-DIAG", range_active=True),
    ]


def command(ids=("PS-SCIENCE",), up_to=250.0):
    return {"store_ids": list(ids), "up_to_time": up_to}


class TestValidation(unittest.TestCase):
    def test_a_valid_store_normalizes(self):
        record = validate_packet_store(store())
        self.assertEqual(len(record["packets"]), 4)
        self.assertIsNone(record["open_retrieval_cursor"])

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store("PS-SCIENCE")

    def test_packets_out_of_storage_order_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(times=(400.0, 100.0)))

    def test_a_repeated_packet_id_raises(self):
        record = store()
        record["packets"][2]["id"] = "PKT-1"
        with self.assertRaises(ValueError):
            validate_packet_store(record)

    def test_a_zero_size_packet_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(size=0))

    def test_both_retrieval_kinds_at_once_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(cursor=200.0, range_active=True))

    def test_a_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store_set([store("PS-A"), store("PS-A")])

    def test_a_command_without_a_time_raises(self):
        with self.assertRaises(ValueError):
            validate_command({"store_ids": ["PS-A"]})

    def test_a_negative_deletion_time_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(up_to=-1.0))

    def test_a_boolean_deletion_time_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(up_to=True))

    def test_a_command_naming_a_store_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(ids=("PS-A", "PS-A")))

    def test_a_command_naming_no_store_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(ids=()))


class TestSelection(unittest.TestCase):
    def test_the_cut_is_inclusive_of_the_named_time(self):
        candidates = deletion_candidates(store(), 200.0)
        self.assertEqual([p["id"] for p in candidates], ["PKT-1", "PKT-2"])

    def test_a_time_before_everything_held_selects_nothing(self):
        self.assertEqual(deletion_candidates(store(), 10.0), [])

    def test_a_time_past_everything_held_selects_all_of_it(self):
        self.assertEqual(len(deletion_candidates(store(), 900.0)), 4)

    def test_the_occupied_octets_sum_the_content(self):
        self.assertEqual(occupied_octets(store()), 256)

    def test_the_oldest_time_is_the_first_packet_held(self):
        self.assertAlmostEqual(oldest_storage_time(store()), 100.0, places=9)

    def test_an_empty_store_has_no_oldest_time(self):
        self.assertIsNone(oldest_storage_time(store(times=())))


class TestDeletion(unittest.TestCase):
    def test_a_plain_deletion_removes_the_selected_packets(self):
        result = delete_contents(store(), 250.0)
        self.assertEqual(result["outcome"], OUTCOME_DELETED)
        self.assertEqual(result["deleted_ids"], ["PKT-1", "PKT-2"])
        self.assertEqual(result["retained_count"], 2)

    def test_a_deletion_frees_the_octets_it_removed(self):
        result = delete_contents(store(), 250.0)
        self.assertEqual(result["freed_octets"], 128)

    def test_a_deletion_moves_the_oldest_storage_time_forward(self):
        result = delete_contents(store(), 250.0)
        self.assertAlmostEqual(result["oldest_storage_time"], 300.0, places=9)

    def test_a_time_older_than_everything_held_deletes_nothing(self):
        result = delete_contents(store(), 10.0)
        self.assertEqual(result["outcome"], OUTCOME_NOTHING_TO_DELETE)
        self.assertEqual(result["retained_count"], 4)

    def test_a_time_past_the_newest_packet_empties_the_store(self):
        result = delete_contents(store(), 900.0)
        self.assertEqual(result["retained_count"], 0)
        self.assertIsNone(result["oldest_storage_time"])

    def test_a_time_exactly_on_the_newest_packet_empties_the_store(self):
        result = delete_contents(store(), 400.0)
        self.assertEqual(result["retained_count"], 0)

    def test_a_range_retrieval_refuses_the_deletion_outright(self):
        result = delete_contents(store(range_active=True), 250.0)
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_RANGE_RETRIEVAL)
        self.assertEqual(result["retained_count"], 4)


class TestOpenRetrievalClamp(unittest.TestCase):
    def test_an_open_retrieval_clamps_the_cut_to_its_cursor(self):
        result = delete_contents(store(cursor=200.0), 350.0)
        self.assertEqual(result["outcome"], OUTCOME_DELETED_CLAMPED)
        self.assertEqual(result["deleted_ids"], ["PKT-1"])
        self.assertTrue(result["clamped"])

    def test_a_cut_below_the_cursor_is_not_clamped(self):
        result = delete_contents(store(cursor=300.0), 200.0)
        self.assertEqual(result["outcome"], OUTCOME_DELETED)
        self.assertFalse(result["clamped"])
        self.assertEqual(result["deleted_count"], 2)

    def test_a_packet_exactly_on_the_cursor_is_kept(self):
        result = delete_contents(store(cursor=300.0), 300.0)
        self.assertEqual(result["deleted_ids"], ["PKT-1", "PKT-2"])
        self.assertTrue(result["clamped"])

    def test_the_protected_packets_start_at_the_cursor(self):
        protected = protected_by_open_retrieval(store(cursor=300.0))
        self.assertEqual([p["id"] for p in protected], ["PKT-3", "PKT-4"])

    def test_a_store_with_no_open_retrieval_protects_nothing(self):
        self.assertEqual(protected_by_open_retrieval(store()), [])

    def test_a_cursor_before_everything_held_blocks_the_whole_deletion(self):
        result = delete_contents(store(cursor=50.0), 900.0)
        self.assertEqual(result["deleted_count"], 0)
        self.assertTrue(result["clamped"])
        self.assertEqual(result["outcome"], OUTCOME_NOTHING_TO_DELETE)


class TestPartialFailure(unittest.TestCase):
    def test_an_unknown_store_fails_for_that_store_alone(self):
        run = apply_commands(stores(), [command(("PS-GHOST", "PS-SCIENCE"))])
        outcomes = [entry["outcome"] for entry in run["steps"][0]["results"]]
        self.assertEqual(outcomes[0], OUTCOME_REJECTED_UNKNOWN_STORE)
        self.assertEqual(outcomes[1], OUTCOME_DELETED)

    def test_a_refused_store_does_not_stop_the_others(self):
        run = apply_commands(stores(), [command(("PS-DIAG", "PS-SCIENCE"))])
        self.assertEqual(run["steps"][0]["results"][1]["deleted_count"], 2)

    def test_every_refusal_is_notified(self):
        run = apply_commands(stores(), [command(("PS-GHOST", "PS-DIAG"))])
        self.assertEqual(len(run["steps"][0]["findings"]), 2)

    def test_a_non_list_command_sequence_raises(self):
        with self.assertRaises(ValueError):
            apply_commands(stores(), command())


class TestContentReport(unittest.TestCase):
    def test_the_report_covers_every_store_in_order(self):
        state = validate_store_set(stores())
        report = content_report(state)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"],
        )

    def test_the_held_packet_total_sums_the_entries(self):
        state = validate_store_set(stores())
        self.assertEqual(content_report(state)["held_packet_count"], 12)

    def test_an_entry_carries_its_occupied_octets(self):
        state = validate_store_set(stores())
        self.assertEqual(content_report(state)["entries"][0]["occupied_octets"], 256)


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_deletion_is_accepted(self):
        result = assess_content_deletion([store("PS-SCIENCE")], [command()])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["deleted_count"], 2)

    def test_a_range_busy_store_makes_the_run_partially_rejected(self):
        result = assess_content_deletion(stores(), [command(("PS-DIAG",))])
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["rejected"], ["PS-DIAG"])

    def test_a_clamped_deletion_is_accepted_with_a_finding(self):
        result = assess_content_deletion(stores(), [command(("PS-EVENTS",), 350.0)])
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["findings"]), 1)

    def test_the_freed_octets_add_up_across_the_named_stores(self):
        result = assess_content_deletion(
            stores(), [command(("PS-SCIENCE", "PS-EVENTS"), 250.0)]
        )
        self.assertEqual(result["freed_octets"], 256)

    def test_two_deletions_in_a_row_leave_the_store_empty(self):
        result = assess_content_deletion(
            [store("PS-SCIENCE")], [command(up_to=250.0), command(up_to=900.0)]
        )
        self.assertEqual(result["report"]["held_packet_count"], 0)
        self.assertEqual(result["deleted_count"], 4)

    def test_an_empty_command_sequence_leaves_the_content_intact(self):
        result = assess_content_deletion(stores(), [])
        self.assertEqual(result["report"]["held_packet_count"], 12)
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)

    def test_an_invalid_store_set_raises_before_any_deletion(self):
        broken = stores()
        broken[0]["packets"][0]["size_octets"] = 0
        with self.assertRaises(ValueError):
            assess_content_deletion(broken, [command()])


if __name__ == "__main__":
    unittest.main()

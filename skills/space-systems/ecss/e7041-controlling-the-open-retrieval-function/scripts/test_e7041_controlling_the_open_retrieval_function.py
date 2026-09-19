"""Contract test for the e7041 open-retrieval control leaf."""

import unittest

from e7041_controlling_the_open_retrieval_function_logic import (
    COMMAND_ABORT,
    COMMAND_RESUME,
    COMMAND_START,
    COMMAND_SUSPEND,
    OUTCOME_APPLIED,
    OUTCOME_NO_CHANGE,
    OUTCOME_REJECTED_ALREADY_OPEN,
    OUTCOME_REJECTED_NOT_IN_PROGRESS,
    OUTCOME_REJECTED_NOT_SUSPENDED,
    OUTCOME_REJECTED_RANGE_RETRIEVAL,
    OUTCOME_REJECTED_UNKNOWN_STORE,
    RETRIEVAL_INACTIVE,
    RETRIEVAL_IN_PROGRESS,
    RETRIEVAL_SUSPENDED,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    abort_open_retrieval,
    apply_commands,
    assess_open_retrieval_control,
    cursor_index,
    open_retrieval_report,
    overwrite_protection,
    pending_packets,
    resume_open_retrieval,
    start_open_retrieval,
    suspend_open_retrieval,
    validate_command,
    validate_packet_store,
    validate_store_set,
)

TIMES = (100.0, 200.0, 300.0, 400.0)


def packets(times=TIMES):
    return [
        {"id": "PKT-%d" % (i + 1), "storage_time": t} for i, t in enumerate(times)
    ]


def store(store_id="PS-SCIENCE", state=RETRIEVAL_INACTIVE, cursor=None,
          by_range=False, times=TIMES):
    record = {
        "id": store_id,
        "packets": packets(times),
        "open_retrieval_state": state,
        "by_time_range_active": by_range,
    }
    if cursor is not None:
        record["cursor_time"] = cursor
    return record


def stores():
    return [
        store("PS-SCIENCE"),
        store("PS-EVENTS", RETRIEVAL_IN_PROGRESS, cursor=200.0),
        store("PS-DIAG", by_range=True),
    ]


def command(action=COMMAND_START, ids=("PS-SCIENCE",), **kw):
    record = {"action": action, "store_ids": list(ids)}
    record.update(kw)
    return record


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_store_normalizes(self):
        record = validate_packet_store(store())
        self.assertEqual(record["id"], "PS-SCIENCE")
        self.assertEqual(len(record["packets"]), 4)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store("PS-SCIENCE")

    def test_packets_out_of_storage_order_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(times=(300.0, 100.0)))

    def test_a_repeated_packet_id_raises(self):
        record = store()
        record["packets"][1]["id"] = "PKT-1"
        with self.assertRaises(ValueError):
            validate_packet_store(record)

    def test_a_negative_storage_time_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(times=(-1.0,)))

    def test_an_unknown_retrieval_state_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(state="draining"))

    def test_an_open_retrieval_without_a_cursor_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(state=RETRIEVAL_IN_PROGRESS))

    def test_a_cursor_without_an_open_retrieval_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(cursor=100.0))

    def test_both_retrieval_kinds_at_once_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(
                store(state=RETRIEVAL_IN_PROGRESS, cursor=100.0, by_range=True)
            )

    def test_a_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store_set([store("PS-A"), store("PS-A")])


class TestCommandValidation(unittest.TestCase):
    def test_a_valid_start_normalizes(self):
        request = validate_command(command(retrieval_start_time=150))
        self.assertAlmostEqual(request["retrieval_start_time"], 150.0, places=9)

    def test_a_start_without_a_start_time_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command())

    def test_an_abort_carrying_a_start_time_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(COMMAND_ABORT, retrieval_start_time=10))

    def test_a_boolean_start_time_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(retrieval_start_time=True))

    def test_a_command_naming_a_store_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(COMMAND_ABORT, ids=("PS-A", "PS-A")))

    def test_an_unknown_action_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(action="rewind-open-retrieval"))


class TestCursorPlacement(unittest.TestCase):
    def test_the_cursor_lands_on_the_first_packet_at_or_after_the_time(self):
        self.assertEqual(cursor_index(store(), 250.0), 2)

    def test_a_start_time_exactly_on_a_packet_includes_that_packet(self):
        self.assertEqual(cursor_index(store(), 200.0), 1)

    def test_a_start_time_before_everything_skips_nothing(self):
        self.assertEqual(cursor_index(store(), 0.0), 0)

    def test_a_start_time_past_everything_skips_all_of_it(self):
        self.assertEqual(cursor_index(store(), 999.0), 4)


class TestStart(unittest.TestCase):
    def test_a_start_on_an_idle_store_applies(self):
        result = start_open_retrieval(store(), 250.0)
        self.assertEqual(result["outcome"], OUTCOME_APPLIED)
        self.assertEqual(result["store"]["open_retrieval_state"],
                         RETRIEVAL_IN_PROGRESS)
        self.assertEqual(result["skipped_count"], 2)
        self.assertEqual(result["pending_count"], 2)

    def test_a_start_past_everything_held_is_accepted_and_yields_nothing_yet(self):
        result = start_open_retrieval(store(), 999.0)
        self.assertEqual(result["outcome"], OUTCOME_APPLIED)
        self.assertEqual(result["pending_count"], 0)

    def test_a_second_start_on_an_open_store_is_refused(self):
        result = start_open_retrieval(
            store(state=RETRIEVAL_IN_PROGRESS, cursor=200.0), 100.0
        )
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_ALREADY_OPEN)

    def test_a_start_on_a_suspended_store_is_refused(self):
        result = start_open_retrieval(
            store(state=RETRIEVAL_SUSPENDED, cursor=200.0), 100.0
        )
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_ALREADY_OPEN)

    def test_a_start_on_a_store_in_a_range_retrieval_is_refused(self):
        result = start_open_retrieval(store(by_range=True), 100.0)
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_RANGE_RETRIEVAL)
        self.assertEqual(result["store"]["open_retrieval_state"],
                         RETRIEVAL_INACTIVE)


class TestSuspendResumeAbort(unittest.TestCase):
    def test_suspending_a_running_retrieval_applies(self):
        result = suspend_open_retrieval(
            store(state=RETRIEVAL_IN_PROGRESS, cursor=200.0)
        )
        self.assertEqual(result["store"]["open_retrieval_state"],
                         RETRIEVAL_SUSPENDED)

    def test_suspending_an_idle_store_is_refused(self):
        result = suspend_open_retrieval(store())
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_NOT_IN_PROGRESS)

    def test_resuming_a_suspended_retrieval_keeps_its_cursor(self):
        result = resume_open_retrieval(
            store(state=RETRIEVAL_SUSPENDED, cursor=200.0)
        )
        self.assertEqual(result["store"]["open_retrieval_state"],
                         RETRIEVAL_IN_PROGRESS)
        self.assertAlmostEqual(result["store"]["cursor_time"], 200.0, places=9)

    def test_resuming_a_running_retrieval_is_refused(self):
        result = resume_open_retrieval(
            store(state=RETRIEVAL_IN_PROGRESS, cursor=200.0)
        )
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_NOT_SUSPENDED)

    def test_aborting_a_running_retrieval_clears_the_cursor(self):
        result = abort_open_retrieval(
            store(state=RETRIEVAL_IN_PROGRESS, cursor=200.0)
        )
        self.assertEqual(result["store"]["open_retrieval_state"],
                         RETRIEVAL_INACTIVE)
        self.assertIsNone(result["store"]["cursor_time"])

    def test_aborting_a_suspended_retrieval_applies(self):
        result = abort_open_retrieval(
            store(state=RETRIEVAL_SUSPENDED, cursor=200.0)
        )
        self.assertEqual(result["outcome"], OUTCOME_APPLIED)

    def test_aborting_an_idle_store_is_accepted_with_no_change(self):
        result = abort_open_retrieval(store())
        self.assertEqual(result["outcome"], OUTCOME_NO_CHANGE)
        self.assertFalse(result["changed"])


class TestOverwriteProtection(unittest.TestCase):
    def test_an_idle_store_protects_nothing(self):
        protection = overwrite_protection(store())
        self.assertFalse(protection["protected"])
        self.assertEqual(protection["protected_count"], 0)

    def test_a_running_retrieval_protects_from_its_cursor_forward(self):
        protection = overwrite_protection(
            store(state=RETRIEVAL_IN_PROGRESS, cursor=200.0)
        )
        self.assertTrue(protection["protected"])
        self.assertEqual(protection["protected_count"], 3)
        self.assertAlmostEqual(protection["protected_from"], 200.0, places=9)

    def test_a_suspended_retrieval_still_protects_its_packets(self):
        protection = overwrite_protection(
            store(state=RETRIEVAL_SUSPENDED, cursor=300.0)
        )
        self.assertTrue(protection["protected"])
        self.assertEqual(protection["protected_count"], 2)

    def test_the_pending_packets_start_at_the_cursor(self):
        pending = pending_packets(store(state=RETRIEVAL_IN_PROGRESS, cursor=300.0))
        self.assertEqual([p["id"] for p in pending], ["PKT-3", "PKT-4"])


class TestPartialFailure(unittest.TestCase):
    def test_an_unknown_store_fails_for_that_store_alone(self):
        run = apply_commands(
            stores(),
            [command(COMMAND_ABORT, ("PS-GHOST", "PS-EVENTS"))],
        )
        outcomes = [entry["outcome"] for entry in run["steps"][0]["results"]]
        self.assertEqual(outcomes[0], OUTCOME_REJECTED_UNKNOWN_STORE)
        self.assertEqual(outcomes[1], OUTCOME_APPLIED)

    def test_every_refusal_is_notified(self):
        run = apply_commands(
            stores(), [command(COMMAND_SUSPEND, ("PS-SCIENCE", "PS-GHOST"))]
        )
        self.assertEqual(len(run["steps"][0]["findings"]), 2)

    def test_a_non_list_command_sequence_raises(self):
        with self.assertRaises(ValueError):
            apply_commands(stores(), command(COMMAND_ABORT))


class TestReport(unittest.TestCase):
    def test_the_report_covers_every_store_in_order(self):
        state = validate_store_set(stores())
        report = open_retrieval_report(state)
        self.assertEqual(report["store_count"], 3)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"],
        )

    def test_the_open_total_counts_running_and_suspended_stores(self):
        state = validate_store_set(stores())
        self.assertEqual(open_retrieval_report(state)["open_count"], 1)

    def test_an_entry_carries_the_range_retrieval_flag(self):
        state = validate_store_set(stores())
        self.assertTrue(open_retrieval_report(state)["entries"][2][
            "by_time_range_active"])


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_start_is_accepted(self):
        result = assess_open_retrieval_control(
            stores(), [command(retrieval_start_time=150.0)]
        )
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_start_on_a_range_busy_store_is_partially_rejected(self):
        result = assess_open_retrieval_control(
            stores(), [command(ids=("PS-DIAG",), retrieval_start_time=150.0)]
        )
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["rejected"], [(COMMAND_START, "PS-DIAG")])

    def test_a_suspended_store_raises_a_protection_finding(self):
        result = assess_open_retrieval_control(
            stores(), [command(COMMAND_SUSPEND, ("PS-EVENTS",))]
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["report"]["suspended_count"], 1)

    def test_a_start_suspend_resume_abort_cycle_returns_to_idle(self):
        result = assess_open_retrieval_control(
            stores(),
            [
                command(COMMAND_START, ("PS-SCIENCE",), retrieval_start_time=100.0),
                command(COMMAND_SUSPEND, ("PS-SCIENCE",)),
                command(COMMAND_RESUME, ("PS-SCIENCE",)),
                command(COMMAND_ABORT, ("PS-SCIENCE",)),
            ],
        )
        entry = result["report"]["entries"][0]
        self.assertEqual(entry["open_retrieval_state"], RETRIEVAL_INACTIVE)
        self.assertIsNone(entry["cursor_time"])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)

    def test_an_abort_repeated_after_a_lost_acknowledgement_is_not_a_fault(self):
        result = assess_open_retrieval_control(
            stores(),
            [command(COMMAND_ABORT, ("PS-EVENTS",)),
             command(COMMAND_ABORT, ("PS-EVENTS",))],
        )
        self.assertEqual(result["rejected_count"], 0)
        self.assertEqual(result["steps"][1]["results"][0]["outcome"],
                         OUTCOME_NO_CHANGE)

    def test_an_empty_command_sequence_leaves_the_state_intact(self):
        result = assess_open_retrieval_control(stores(), [])
        self.assertEqual(result["report"]["open_count"], 1)

    def test_an_invalid_store_set_raises_before_any_command_runs(self):
        broken = stores()
        broken[0]["open_retrieval_state"] = "draining"
        with self.assertRaises(ValueError):
            assess_open_retrieval_control(broken, [command(COMMAND_ABORT)])


if __name__ == "__main__":
    unittest.main()

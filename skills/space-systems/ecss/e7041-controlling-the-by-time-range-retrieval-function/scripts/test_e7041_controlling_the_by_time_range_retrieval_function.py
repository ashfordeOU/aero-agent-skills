"""Contract test for the e7041 by-time-range retrieval control leaf."""

import unittest

from e7041_controlling_the_by_time_range_retrieval_function_logic import (
    COMMAND_ABORT,
    COMMAND_START,
    COVERAGE_BOTH_GAPS,
    COVERAGE_COMPLETE,
    COVERAGE_EMPTY,
    COVERAGE_LEADING_GAP,
    COVERAGE_TRAILING_GAP,
    OUTCOME_APPLIED,
    OUTCOME_NO_CHANGE,
    OUTCOME_REJECTED_ALREADY_RUNNING,
    OUTCOME_REJECTED_OPEN_RETRIEVAL,
    OUTCOME_REJECTED_UNKNOWN_STORE,
    RETRIEVAL_INACTIVE,
    RETRIEVAL_IN_PROGRESS,
    VERDICT_ACCEPTED,
    VERDICT_PARTIAL,
    abort_range_retrieval,
    apply_commands,
    assess_coverage,
    assess_range_retrieval_control,
    held_span,
    range_retrieval_report,
    select_packets,
    start_range_retrieval,
    validate_command,
    validate_packet_store,
    validate_store_set,
    validate_time_range,
)

TIMES = (100.0, 200.0, 300.0, 400.0)


def store(store_id="PS-SCIENCE", state=RETRIEVAL_INACTIVE, open_active=False,
          times=TIMES):
    return {
        "id": store_id,
        "packets": [
            {"id": "PKT-%d" % (i + 1), "storage_time": t}
            for i, t in enumerate(times)
        ],
        "range_retrieval_state": state,
        "open_retrieval_active": open_active,
    }


def stores():
    return [
        store("PS-SCIENCE"),
        store("PS-EVENTS", RETRIEVAL_IN_PROGRESS),
        store("PS-DIAG", open_active=True),
    ]


def command(action=COMMAND_START, ids=("PS-SCIENCE",), **kw):
    record = {"action": action, "store_ids": list(ids)}
    record.update(kw)
    return record


class TestTimeRange(unittest.TestCase):
    def test_an_ordered_window_normalizes(self):
        window = validate_time_range(100, 400)
        self.assertAlmostEqual(window["requested_span"], 300.0, places=9)

    def test_an_inverted_window_raises(self):
        with self.assertRaises(ValueError):
            validate_time_range(400.0, 100.0)

    def test_a_zero_width_window_raises(self):
        with self.assertRaises(ValueError):
            validate_time_range(200.0, 200.0)

    def test_a_non_numeric_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_time_range("100", 400.0)

    def test_a_boolean_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_time_range(True, 400.0)

    def test_a_negative_bound_raises(self):
        with self.assertRaises(ValueError):
            validate_time_range(-1.0, 400.0)


class TestStoreValidation(unittest.TestCase):
    def test_a_valid_store_normalizes(self):
        record = validate_packet_store(store())
        self.assertEqual(record["id"], "PS-SCIENCE")
        self.assertEqual(len(record["packets"]), 4)

    def test_a_non_mapping_store_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_store(["PS-SCIENCE"])

    def test_packets_out_of_storage_order_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(store(times=(400.0, 100.0)))

    def test_both_retrieval_kinds_at_once_raise(self):
        with self.assertRaises(ValueError):
            validate_packet_store(
                store(state=RETRIEVAL_IN_PROGRESS, open_active=True)
            )

    def test_a_duplicate_store_id_raises(self):
        with self.assertRaises(ValueError):
            validate_store_set([store("PS-A"), store("PS-A")])

    def test_an_empty_store_spans_nothing(self):
        self.assertIsNone(held_span(store(times=())))


class TestCommandValidation(unittest.TestCase):
    def test_a_valid_start_normalizes(self):
        request = validate_command(command(from_time=100, to_time=400))
        self.assertAlmostEqual(request["window"]["to_time"], 400.0, places=9)

    def test_a_start_without_a_window_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command())

    def test_an_abort_carrying_a_window_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(COMMAND_ABORT, from_time=1.0, to_time=2.0))

    def test_a_command_naming_a_store_twice_raises(self):
        with self.assertRaises(ValueError):
            validate_command(command(COMMAND_ABORT, ids=("PS-A", "PS-A")))


class TestSelection(unittest.TestCase):
    def test_both_bounds_are_inclusive(self):
        selected = select_packets(store(), 100.0, 400.0)
        self.assertEqual(len(selected), 4)

    def test_a_packet_exactly_on_the_lower_bound_is_selected(self):
        selected = select_packets(store(), 200.0, 350.0)
        self.assertEqual([p["id"] for p in selected], ["PKT-2", "PKT-3"])

    def test_a_packet_exactly_on_the_upper_bound_is_selected(self):
        selected = select_packets(store(), 150.0, 300.0)
        self.assertEqual([p["id"] for p in selected], ["PKT-2", "PKT-3"])

    def test_a_window_between_two_packets_selects_nothing(self):
        self.assertEqual(select_packets(store(), 210.0, 290.0), [])


class TestCoverage(unittest.TestCase):
    def test_a_window_inside_the_held_span_is_complete(self):
        result = assess_coverage(store(), 150.0, 350.0)
        self.assertEqual(result["coverage"], COVERAGE_COMPLETE)
        self.assertEqual(result["packet_count"], 2)

    def test_a_window_reaching_before_the_oldest_packet_has_a_leading_gap(self):
        result = assess_coverage(store(), 10.0, 250.0)
        self.assertEqual(result["coverage"], COVERAGE_LEADING_GAP)
        self.assertTrue(result["leading_gap"])
        self.assertFalse(result["trailing_gap"])

    def test_a_window_reaching_past_the_newest_packet_has_a_trailing_gap(self):
        result = assess_coverage(store(), 250.0, 900.0)
        self.assertEqual(result["coverage"], COVERAGE_TRAILING_GAP)

    def test_a_window_wider_than_the_store_has_both_gaps(self):
        result = assess_coverage(store(), 10.0, 900.0)
        self.assertEqual(result["coverage"], COVERAGE_BOTH_GAPS)
        self.assertEqual(result["packet_count"], 4)

    def test_a_window_with_nothing_in_it_is_empty_not_a_failure(self):
        result = assess_coverage(store(), 210.0, 290.0)
        self.assertEqual(result["coverage"], COVERAGE_EMPTY)
        self.assertEqual(result["packet_count"], 0)
        self.assertIsNone(result["covered_from"])

    def test_the_covered_span_is_measured_on_the_packets_not_the_request(self):
        result = assess_coverage(store(), 10.0, 900.0)
        self.assertAlmostEqual(result["covered_span"], 300.0, places=9)
        self.assertAlmostEqual(result["requested_span"], 890.0, places=9)

    def test_a_window_touching_only_the_oldest_packet_is_covered(self):
        result = assess_coverage(store(), 50.0, 100.0)
        self.assertEqual(result["packet_count"], 1)
        self.assertAlmostEqual(result["covered_span"], 0.0, places=9)


class TestStartAndAbort(unittest.TestCase):
    def test_a_start_on_an_idle_store_applies(self):
        result = start_range_retrieval(store(), 150.0, 350.0)
        self.assertEqual(result["outcome"], OUTCOME_APPLIED)
        self.assertEqual(result["store"]["range_retrieval_state"],
                         RETRIEVAL_IN_PROGRESS)

    def test_a_second_start_on_a_running_store_is_refused(self):
        result = start_range_retrieval(
            store(state=RETRIEVAL_IN_PROGRESS), 150.0, 350.0
        )
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_ALREADY_RUNNING)

    def test_a_start_on_a_store_with_an_open_retrieval_is_refused(self):
        result = start_range_retrieval(store(open_active=True), 150.0, 350.0)
        self.assertEqual(result["outcome"], OUTCOME_REJECTED_OPEN_RETRIEVAL)
        self.assertEqual(result["store"]["range_retrieval_state"],
                         RETRIEVAL_INACTIVE)

    def test_a_start_on_an_empty_window_is_still_accepted(self):
        result = start_range_retrieval(store(), 210.0, 290.0)
        self.assertEqual(result["outcome"], OUTCOME_APPLIED)
        self.assertEqual(result["coverage"]["coverage"], COVERAGE_EMPTY)

    def test_aborting_a_running_retrieval_clears_the_window(self):
        running = start_range_retrieval(store(), 150.0, 350.0)["store"]
        result = abort_range_retrieval(running)
        self.assertEqual(result["store"]["range_retrieval_state"],
                         RETRIEVAL_INACTIVE)
        self.assertIsNone(result["store"]["window"])

    def test_aborting_an_idle_store_is_accepted_with_no_change(self):
        result = abort_range_retrieval(store())
        self.assertEqual(result["outcome"], OUTCOME_NO_CHANGE)


class TestPartialFailure(unittest.TestCase):
    def test_an_unknown_store_fails_for_that_store_alone(self):
        run = apply_commands(
            stores(),
            [command(ids=("PS-GHOST", "PS-SCIENCE"), from_time=100.0,
                     to_time=400.0)],
        )
        outcomes = [entry["outcome"] for entry in run["steps"][0]["results"]]
        self.assertEqual(outcomes[0], OUTCOME_REJECTED_UNKNOWN_STORE)
        self.assertEqual(outcomes[1], OUTCOME_APPLIED)

    def test_every_refusal_is_notified(self):
        run = apply_commands(
            stores(),
            [command(ids=("PS-EVENTS",), from_time=100.0, to_time=400.0)],
        )
        self.assertEqual(len(run["steps"][0]["findings"]), 1)

    def test_a_non_list_command_sequence_raises(self):
        with self.assertRaises(ValueError):
            apply_commands(stores(), command(COMMAND_ABORT))


class TestReport(unittest.TestCase):
    def test_the_report_covers_every_store_in_order(self):
        state = validate_store_set(stores())
        report = range_retrieval_report(state)
        self.assertEqual(
            [entry["id"] for entry in report["entries"]],
            ["PS-SCIENCE", "PS-EVENTS", "PS-DIAG"],
        )

    def test_the_running_total_counts_only_engaged_stores(self):
        state = validate_store_set(stores())
        self.assertEqual(range_retrieval_report(state)["running_count"], 1)

    def test_an_idle_store_reports_no_window(self):
        state = validate_store_set(stores())
        self.assertIsNone(range_retrieval_report(state)["entries"][0]["from_time"])


class TestFullAssessment(unittest.TestCase):
    def test_a_clean_start_is_accepted(self):
        result = assess_range_retrieval_control(
            stores(), [command(from_time=150.0, to_time=350.0)]
        )
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_start_on_an_open_retrieval_store_is_partially_rejected(self):
        result = assess_range_retrieval_control(
            stores(),
            [command(ids=("PS-DIAG",), from_time=150.0, to_time=350.0)],
        )
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["rejected"], [(COMMAND_START, "PS-DIAG")])

    def test_a_partly_covered_window_is_accepted_with_a_finding(self):
        result = assess_range_retrieval_control(
            stores(), [command(from_time=10.0, to_time=900.0)]
        )
        self.assertTrue(result["accepted"])
        self.assertEqual(len(result["findings"]), 1)

    def test_an_empty_window_is_accepted_with_a_finding(self):
        result = assess_range_retrieval_control(
            stores(), [command(from_time=210.0, to_time=290.0)]
        )
        self.assertTrue(result["accepted"])
        self.assertIn("no packets", result["findings"][0])

    def test_a_start_then_abort_returns_the_store_to_idle(self):
        result = assess_range_retrieval_control(
            stores(),
            [
                command(from_time=150.0, to_time=350.0),
                command(COMMAND_ABORT, ("PS-SCIENCE",)),
            ],
        )
        self.assertEqual(result["report"]["entries"][0]["range_retrieval_state"],
                         RETRIEVAL_INACTIVE)

    def test_an_empty_command_sequence_leaves_the_state_intact(self):
        result = assess_range_retrieval_control(stores(), [])
        self.assertEqual(result["report"]["running_count"], 1)

    def test_an_invalid_store_set_raises_before_any_command_runs(self):
        broken = stores()
        broken[0]["range_retrieval_state"] = "paused"
        with self.assertRaises(ValueError):
            assess_range_retrieval_control(broken, [command(COMMAND_ABORT)])


if __name__ == "__main__":
    unittest.main()

"""Contract test for the OBCP tracing leaf (stdlib unittest)."""

import unittest

from e7041_tracing_logic import (
    FINDING_GRANULARITY_OMITS_EVENTS,
    FINDING_OLDEST_RECORDS_DROPPED,
    FINDING_TIME_WENT_BACKWARDS,
    FINDING_TRACE_STARTED_MID_RUN,
    FINDING_TRACING_DISABLED,
    FINDING_TRACING_STOPPED_AT_BRIM,
    FINDING_UNLOADED_PROCEDURE,
    LEVEL_BLOCK,
    LEVEL_PROCEDURE,
    LEVEL_STEP,
    OVERFLOW_DROP_OLDEST,
    OVERFLOW_STOP_TRACING,
    apply_capacity,
    assess_tracing,
    is_reconstructable,
    level_rank,
    normalise_configuration,
    normalise_event,
    selected_events,
    trace_coverage,
    trace_run,
)


def run_of(count, level=LEVEL_STEP, start_time=0.0):
    return [
        {"event_id": "S-%d" % i, "level": level, "time_s": start_time + i}
        for i in range(count)
    ]


def mixed_run():
    return [
        {"event_id": "ENTER", "level": LEVEL_PROCEDURE, "time_s": 0.0},
        {"event_id": "B-1", "level": LEVEL_BLOCK, "time_s": 1.0},
        {"event_id": "S-1", "level": LEVEL_STEP, "time_s": 2.0},
        {"event_id": "S-2", "level": LEVEL_STEP, "time_s": 3.0},
        {"event_id": "LEAVE", "level": LEVEL_PROCEDURE, "time_s": 4.0},
    ]


def config(**overrides):
    base = {"procedure_id": "OBCP-THERMAL-SAFE", "enabled": True}
    base.update(overrides)
    return base


def findings_of(result):
    return [f["finding"] for f in result["findings"]]


class TestLevels(unittest.TestCase):
    def test_levels_run_from_coarse_to_fine(self):
        self.assertLess(level_rank(LEVEL_PROCEDURE), level_rank(LEVEL_BLOCK))
        self.assertLess(level_rank(LEVEL_BLOCK), level_rank(LEVEL_STEP))

    def test_an_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            level_rank("statement")


class TestConfiguration(unittest.TestCase):
    def test_a_minimal_configuration_defaults_to_step_granularity(self):
        normalised = normalise_configuration(config())
        self.assertEqual(normalised["granularity"], LEVEL_STEP)
        self.assertEqual(normalised["overflow"], OVERFLOW_DROP_OLDEST)

    def test_a_configuration_without_a_procedure_id_raises(self):
        with self.assertRaises(ValueError):
            normalise_configuration({"enabled": True})

    def test_a_zero_capacity_buffer_raises(self):
        with self.assertRaises(ValueError):
            normalise_configuration(config(capacity=0))

    def test_an_unknown_overflow_policy_raises(self):
        with self.assertRaises(ValueError):
            normalise_configuration(config(overflow="wrap-around-twice"))

    def test_a_negative_switch_on_index_raises(self):
        with self.assertRaises(ValueError):
            normalise_configuration(config(enabled_from_index=-1))

    def test_an_event_without_an_identifier_raises(self):
        with self.assertRaises(ValueError):
            normalise_event({"level": LEVEL_STEP, "time_s": 1.0}, 0)

    def test_an_event_with_a_negative_time_raises(self):
        with self.assertRaises(ValueError):
            normalise_event({"event_id": "S-1", "time_s": -1.0}, 0)


class TestGranularity(unittest.TestCase):
    def test_step_granularity_admits_every_level(self):
        chosen = selected_events(normalise_configuration(config()), mixed_run())
        self.assertEqual(len(chosen), 5)

    def test_procedure_granularity_admits_only_procedure_events(self):
        chosen = selected_events(
            normalise_configuration(config(granularity=LEVEL_PROCEDURE)), mixed_run()
        )
        self.assertEqual([e["event_id"] for e in chosen], ["ENTER", "LEAVE"])

    def test_a_coarse_granularity_is_reported_as_omitting_events(self):
        trace = trace_run(config(granularity=LEVEL_BLOCK), mixed_run())
        self.assertIn(FINDING_GRANULARITY_OMITS_EVENTS, findings_of(trace))

    def test_step_granularity_omits_nothing_and_says_so(self):
        trace = trace_run(config(), mixed_run())
        self.assertNotIn(FINDING_GRANULARITY_OMITS_EVENTS, findings_of(trace))


class TestCapacity(unittest.TestCase):
    def test_a_run_inside_capacity_is_kept_whole(self):
        fitted = apply_capacity(list(range(4)), 8, OVERFLOW_DROP_OLDEST)
        self.assertEqual(fitted["retained"], [0, 1, 2, 3])
        self.assertEqual(fitted["lost"], 0)
        self.assertFalse(fitted["overflowed"])

    def test_dropping_the_oldest_keeps_the_end_of_the_run(self):
        fitted = apply_capacity(list(range(6)), 3, OVERFLOW_DROP_OLDEST)
        self.assertEqual(fitted["retained"], [3, 4, 5])
        self.assertEqual(fitted["lost"], 3)

    def test_stopping_at_the_brim_keeps_the_start_of_the_run(self):
        fitted = apply_capacity(list(range(6)), 3, OVERFLOW_STOP_TRACING)
        self.assertEqual(fitted["retained"], [0, 1, 2])
        self.assertEqual(fitted["lost"], 3)

    def test_a_non_positive_capacity_raises(self):
        with self.assertRaises(ValueError):
            apply_capacity([1, 2], 0, OVERFLOW_DROP_OLDEST)


class TestTraceRun(unittest.TestCase):
    def test_tracing_off_leaves_no_records(self):
        trace = trace_run(config(enabled=False), run_of(3))
        self.assertEqual(trace["records"], [])
        self.assertEqual(findings_of(trace), [FINDING_TRACING_DISABLED])

    def test_an_empty_run_raises(self):
        with self.assertRaises(ValueError):
            trace_run(config(), [])

    def test_records_are_numbered_in_order_and_carry_the_procedure(self):
        trace = trace_run(config(), run_of(3))
        self.assertEqual([r["sequence"] for r in trace["records"]], [0, 1, 2])
        self.assertEqual(trace["records"][0]["procedure_id"], "OBCP-THERMAL-SAFE")

    def test_switching_tracing_on_mid_run_is_reported(self):
        trace = trace_run(config(enabled_from_index=2), run_of(5))
        self.assertIn(FINDING_TRACE_STARTED_MID_RUN, findings_of(trace))
        self.assertEqual(trace["records"][0]["event_id"], "S-2")

    def test_a_wrapped_buffer_reports_the_dropped_records(self):
        trace = trace_run(config(capacity=2), run_of(5))
        self.assertIn(FINDING_OLDEST_RECORDS_DROPPED, findings_of(trace))
        self.assertEqual(trace["lost"], 3)

    def test_stopping_at_the_brim_is_a_different_finding(self):
        trace = trace_run(
            config(capacity=2, overflow=OVERFLOW_STOP_TRACING), run_of(5)
        )
        self.assertIn(FINDING_TRACING_STOPPED_AT_BRIM, findings_of(trace))

    def test_a_backwards_record_time_is_a_finding(self):
        events = run_of(3)
        events[2]["time_s"] = 0.5
        trace = trace_run(config(), events)
        self.assertIn(FINDING_TIME_WENT_BACKWARDS, findings_of(trace))


class TestCoverageAndReconstruction(unittest.TestCase):
    def test_a_full_trace_covers_the_whole_run(self):
        events = run_of(4)
        trace = trace_run(config(), events)
        self.assertAlmostEqual(trace_coverage(trace, events), 1.0, places=9)
        self.assertTrue(is_reconstructable(trace, events))

    def test_a_wrapped_trace_covers_only_part_of_the_run(self):
        events = run_of(4)
        trace = trace_run(config(capacity=2), events)
        self.assertAlmostEqual(trace_coverage(trace, events), 0.5, places=9)
        self.assertFalse(is_reconstructable(trace, events))

    def test_a_trace_that_stopped_early_is_not_reconstructable_either(self):
        events = run_of(4)
        trace = trace_run(config(capacity=2, overflow=OVERFLOW_STOP_TRACING), events)
        self.assertFalse(is_reconstructable(trace, events))

    def test_an_empty_trace_is_not_reconstructable(self):
        events = run_of(4)
        trace = trace_run(config(enabled=False), events)
        self.assertFalse(is_reconstructable(trace, events))

    def test_coverage_of_an_empty_run_raises(self):
        trace = trace_run(config(), run_of(2))
        with self.assertRaises(ValueError):
            trace_coverage(trace, [])


class TestAssessment(unittest.TestCase):
    def test_a_clean_trace_reports_no_findings(self):
        events = run_of(4)
        report = assess_tracing(config(), events, loaded_procedures=["OBCP-THERMAL-SAFE"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["record_count"], 4)
        self.assertTrue(report["reconstructable"])

    def test_tracing_a_procedure_that_is_not_loaded_is_a_finding(self):
        report = assess_tracing(config(), run_of(2), loaded_procedures=["OBCP-OTHER"])
        self.assertIn(FINDING_UNLOADED_PROCEDURE, findings_of(report))

    def test_the_loaded_list_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            assess_tracing(config(), run_of(2), loaded_procedures="OBCP-THERMAL-SAFE")

    def test_a_short_buffer_shows_up_as_lost_records_and_reduced_coverage(self):
        events = run_of(8)
        report = assess_tracing(config(capacity=4), events)
        self.assertEqual(report["lost"], 4)
        self.assertAlmostEqual(report["coverage"], 0.5, places=9)


if __name__ == "__main__":
    unittest.main()

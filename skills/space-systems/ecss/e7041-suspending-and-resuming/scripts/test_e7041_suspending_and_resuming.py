"""Contract test for the OBCP suspend/resume leaf (stdlib unittest)."""

import unittest

from e7041_suspending_and_resuming_logic import (
    EVENT_COMPLETE_STEP,
    EVENT_RESUME,
    EVENT_START_STEP,
    EVENT_SUSPEND,
    HOLD_NOT_HELD,
    HOLD_OVER_LIMIT,
    HOLD_WITHIN_LIMIT,
    OUTCOME_REFUSED_ALREADY_SUSPENDED,
    OUTCOME_REFUSED_NO_STEP_IN_PROGRESS,
    OUTCOME_REFUSED_NOT_RUNNING,
    OUTCOME_REFUSED_NOT_SUSPENDED,
    OUTCOME_REFUSED_STEP_ALREADY_IN_PROGRESS,
    OUTCOME_REFUSED_SUSPEND_ALREADY_PENDING,
    OUTCOME_RESUMED,
    OUTCOME_STEP_COMPLETED,
    OUTCOME_STEP_STARTED,
    OUTCOME_SUSPEND_PENDING,
    OUTCOME_SUSPEND_TOOK_EFFECT,
    OUTCOME_SUSPENDED,
    OUTCOME_TERMINATED,
    OUTCOME_TERMINATED_BEFORE_SUSPEND,
    STATE_RUNNING,
    STATE_SUSPEND_PENDING,
    STATE_SUSPENDED,
    STATE_TERMINATED,
    apply_events,
    assess_hold,
    complete_step,
    create_instance,
    hold_duration,
    is_held,
    owns_engine_slot,
    report_instance,
    request_resume,
    request_suspend,
    start_step,
    validate_instance,
    validate_state,
)


def instance(step_count=5):
    return create_instance("OBCP-1", step_count)


def mid_step(step_count=5):
    working, _ = start_step(instance(step_count))
    return working


class TestInstanceValidation(unittest.TestCase):
    def test_instance_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            validate_instance(["OBCP-1"])

    def test_zero_step_count_raises(self):
        with self.assertRaises(ValueError):
            create_instance("OBCP-1", 0)

    def test_an_empty_id_raises(self):
        with self.assertRaises(ValueError):
            create_instance("", 5)

    def test_an_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_state("paused")

    def test_a_hold_with_a_step_in_progress_raises(self):
        broken = instance()
        broken["state"] = STATE_SUSPENDED
        broken["held_since"] = 0
        broken["step_in_progress"] = True
        with self.assertRaises(ValueError):
            validate_instance(broken)

    def test_a_hold_with_no_start_time_raises(self):
        broken = instance()
        broken["state"] = STATE_SUSPENDED
        with self.assertRaises(ValueError):
            validate_instance(broken)

    def test_a_step_pointer_past_the_procedure_raises(self):
        broken = instance(3)
        broken["current_step"] = 9
        with self.assertRaises(ValueError):
            validate_instance(broken)


class TestSuspendAtABoundary(unittest.TestCase):
    def test_a_hold_between_steps_lands_at_once(self):
        working, outcome = request_suspend(instance(), 100)
        self.assertEqual(outcome, OUTCOME_SUSPENDED)
        self.assertEqual(working["state"], STATE_SUSPENDED)
        self.assertTrue(is_held(working))

    def test_a_hold_mid_step_waits_for_the_boundary(self):
        working, outcome = request_suspend(mid_step(), 100)
        self.assertEqual(outcome, OUTCOME_SUSPEND_PENDING)
        self.assertEqual(working["state"], STATE_SUSPEND_PENDING)
        self.assertFalse(is_held(working))

    def test_the_pending_hold_lands_when_the_step_completes(self):
        working, _ = request_suspend(mid_step(), 100)
        working, outcome = complete_step(working, 140)
        self.assertEqual(outcome, OUTCOME_SUSPEND_TOOK_EFFECT)
        self.assertEqual(working["state"], STATE_SUSPENDED)
        self.assertEqual(working["held_at_step"], 2)

    def test_the_hold_records_the_step_it_landed_on(self):
        working, _ = request_suspend(instance(), 100)
        self.assertEqual(working["held_at_step"], 1)

    def test_holding_a_held_procedure_is_refused_not_ignored(self):
        working, _ = request_suspend(instance(), 100)
        working, outcome = request_suspend(working, 120)
        self.assertEqual(outcome, OUTCOME_REFUSED_ALREADY_SUSPENDED)

    def test_a_second_pending_hold_is_refused(self):
        working, _ = request_suspend(mid_step(), 100)
        working, outcome = request_suspend(working, 110)
        self.assertEqual(outcome, OUTCOME_REFUSED_SUSPEND_ALREADY_PENDING)

    def test_holding_a_finished_procedure_is_refused(self):
        working = mid_step(1)
        working, _ = complete_step(working, 50)
        working, outcome = request_suspend(working, 60)
        self.assertEqual(working["state"], STATE_TERMINATED)
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_RUNNING)


class TestLateSuspend(unittest.TestCase):
    def test_a_hold_on_the_last_step_arrives_too_late(self):
        working = mid_step(1)
        working, _ = request_suspend(working, 10)
        working, outcome = complete_step(working, 20)
        self.assertEqual(outcome, OUTCOME_TERMINATED_BEFORE_SUSPEND)
        self.assertEqual(working["state"], STATE_TERMINATED)

    def test_a_procedure_that_ran_out_is_not_reported_as_held(self):
        working = mid_step(1)
        working, _ = request_suspend(working, 10)
        working, _ = complete_step(working, 20)
        self.assertFalse(is_held(working))

    def test_a_last_step_with_no_pending_hold_just_terminates(self):
        working = mid_step(1)
        working, outcome = complete_step(working, 20)
        self.assertEqual(outcome, OUTCOME_TERMINATED)


class TestResume(unittest.TestCase):
    def test_a_release_carries_on_from_the_held_step(self):
        working = mid_step(5)
        working, _ = complete_step(working, 10)
        working, _ = start_step(working)
        working, _ = complete_step(working, 20)
        working, _ = request_suspend(working, 30)
        held_at = working["current_step"]
        working, outcome = request_resume(working, 90)
        self.assertEqual(outcome, OUTCOME_RESUMED)
        self.assertEqual(working["current_step"], held_at)
        self.assertNotEqual(working["current_step"], 1)

    def test_releasing_a_running_procedure_is_refused(self):
        working, outcome = request_resume(instance(), 10)
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_SUSPENDED)

    def test_releasing_a_pending_hold_is_refused(self):
        working, _ = request_suspend(mid_step(), 100)
        working, outcome = request_resume(working, 110)
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_SUSPENDED)

    def test_a_release_counts_and_accumulates_the_hold(self):
        working, _ = request_suspend(instance(), 100)
        working, _ = request_resume(working, 160)
        self.assertEqual(working["resume_count"], 1)
        self.assertEqual(working["total_held_seconds"], 60)

    def test_a_release_before_the_hold_began_raises(self):
        working, _ = request_suspend(instance(), 100)
        with self.assertRaises(ValueError):
            request_resume(working, 40)

    def test_repeated_holds_accumulate_their_time(self):
        working, _ = request_suspend(instance(), 100)
        working, _ = request_resume(working, 130)
        working, _ = request_suspend(working, 200)
        working, _ = request_resume(working, 250)
        self.assertEqual(working["total_held_seconds"], 80)
        self.assertEqual(working["resume_count"], 2)


class TestEngineSlotAndSteps(unittest.TestCase):
    def test_a_held_procedure_keeps_its_engine_slot(self):
        working, _ = request_suspend(instance(), 100)
        self.assertTrue(owns_engine_slot(working))

    def test_a_finished_procedure_gives_its_slot_back(self):
        working = mid_step(1)
        working, _ = complete_step(working, 10)
        self.assertFalse(owns_engine_slot(working))

    def test_starting_a_step_twice_is_refused(self):
        working, outcome = start_step(mid_step())
        self.assertEqual(outcome, OUTCOME_REFUSED_STEP_ALREADY_IN_PROGRESS)

    def test_starting_a_step_on_a_held_procedure_is_refused(self):
        working, _ = request_suspend(instance(), 100)
        working, outcome = start_step(working)
        self.assertEqual(outcome, OUTCOME_REFUSED_NOT_RUNNING)

    def test_completing_a_step_that_never_started_is_refused(self):
        working, outcome = complete_step(instance(), 10)
        self.assertEqual(outcome, OUTCOME_REFUSED_NO_STEP_IN_PROGRESS)

    def test_a_step_start_is_reported(self):
        working, outcome = start_step(instance())
        self.assertEqual(outcome, OUTCOME_STEP_STARTED)

    def test_a_plain_step_completion_advances_the_pointer(self):
        working, outcome = complete_step(mid_step(), 10)
        self.assertEqual(outcome, OUTCOME_STEP_COMPLETED)
        self.assertEqual(working["current_step"], 2)


class TestHoldLimit(unittest.TestCase):
    def test_a_short_hold_is_within_the_limit(self):
        working, _ = request_suspend(instance(), 100)
        result = assess_hold(working, 150, 600)
        self.assertEqual(result["disposition"], HOLD_WITHIN_LIMIT)
        self.assertEqual(result["remaining_seconds"], 550)

    def test_a_hold_exactly_at_the_limit_is_still_within_it(self):
        working, _ = request_suspend(instance(), 100)
        result = assess_hold(working, 700, 600)
        self.assertEqual(result["disposition"], HOLD_WITHIN_LIMIT)

    def test_a_hold_past_the_limit_is_a_finding(self):
        working, _ = request_suspend(instance(), 100)
        result = assess_hold(working, 900, 600)
        self.assertEqual(result["disposition"], HOLD_OVER_LIMIT)
        self.assertTrue(result["owns_engine_slot"])

    def test_a_running_procedure_is_not_held(self):
        result = assess_hold(instance(), 100, 600)
        self.assertEqual(result["disposition"], HOLD_NOT_HELD)
        self.assertEqual(result["held_seconds"], 0)

    def test_hold_duration_of_a_running_procedure_is_zero(self):
        self.assertEqual(hold_duration(instance(), 500), 0)

    def test_a_zero_hold_limit_raises(self):
        working, _ = request_suspend(instance(), 100)
        with self.assertRaises(ValueError):
            assess_hold(working, 200, 0)


class TestSequences(unittest.TestCase):
    def test_events_must_be_a_list(self):
        with self.assertRaises(ValueError):
            apply_events(instance(), EVENT_SUSPEND)

    def test_an_unknown_event_raises(self):
        with self.assertRaises(ValueError):
            apply_events(instance(), [{"event": "reboot", "at": 1}])

    def test_a_sequence_going_backwards_in_time_raises(self):
        with self.assertRaises(ValueError):
            apply_events(
                instance(),
                [{"event": EVENT_START_STEP, "at": 100},
                 {"event": EVENT_COMPLETE_STEP, "at": 40}],
            )

    def test_a_hold_and_release_round_trip_is_all_accepted(self):
        working, results = apply_events(
            instance(3),
            [
                {"event": EVENT_START_STEP, "at": 0},
                {"event": EVENT_SUSPEND, "at": 5},
                {"event": EVENT_COMPLETE_STEP, "at": 10},
                {"event": EVENT_RESUME, "at": 70},
                {"event": EVENT_START_STEP, "at": 71},
                {"event": EVENT_COMPLETE_STEP, "at": 80},
            ],
        )
        self.assertTrue(all(r["accepted"] for r in results))
        self.assertEqual(working["state"], STATE_RUNNING)
        self.assertEqual(working["current_step"], 3)
        self.assertEqual(working["total_held_seconds"], 60)

    def test_a_refusal_in_a_sequence_is_marked_and_the_run_continues(self):
        working, results = apply_events(
            instance(3),
            [{"event": EVENT_RESUME, "at": 0},
             {"event": EVENT_START_STEP, "at": 1}],
        )
        self.assertFalse(results[0]["accepted"])
        self.assertTrue(results[1]["accepted"])

    def test_the_report_names_the_held_step_and_progress(self):
        working, _ = apply_events(
            instance(4),
            [
                {"event": EVENT_START_STEP, "at": 0},
                {"event": EVENT_COMPLETE_STEP, "at": 10},
                {"event": EVENT_SUSPEND, "at": 20},
            ],
        )
        report = report_instance(working, 80)
        self.assertTrue(report["held"])
        self.assertEqual(report["held_at_step"], 2)
        self.assertEqual(report["current_hold_seconds"], 60)
        self.assertAlmostEqual(report["progress_fraction"], 0.25, places=9)

    def test_a_finished_procedure_reports_full_progress(self):
        working = mid_step(1)
        working, _ = complete_step(working, 10)
        report = report_instance(working)
        self.assertAlmostEqual(report["progress_fraction"], 1.0, places=9)
        self.assertEqual(report["steps_remaining"], 0)


if __name__ == "__main__":
    unittest.main()

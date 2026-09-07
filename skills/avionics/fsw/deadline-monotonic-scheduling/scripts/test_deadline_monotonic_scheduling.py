"""Contract test: avionics/fsw/deadline-monotonic-scheduling (wave-45).

Deterministic, offline, stdlib unittest.  The test docstrings name the
SKILL.md workflow steps each test exercises: step 1 the task-set
assembly and validation of the {name, C, T, D, J} dicts, step 2 the
deadline-monotonic priority assignment (shorter-deadline order, stable
ties), step 3 the context utilization, step 4 the jitter-aware
fixed-point response-time iteration converged against each per-task
deadline (constrained-deadline first-job completion), step 5 the
arbitrary-deadline busy-period job scan, step 6 the release-jitter
recomputation against the zero-jitter baseline, step 7 the feasible
verdict of the whole set, step 8 the deterministic contract test run
under both interpreters.

Runs via `python3 scripts/test_deadline_monotonic_scheduling.py` and
exits 0.  Numeric asserts are tolerance-based throughout (the
exact-float lesson: the pyenv hook interpreter sums Neumaier-accurate
while /usr/bin/python3 3.9.6 does not, so no exact equality on
computed aggregates; assertAlmostEqual/isclose everywhere).
"""

import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deadline_monotonic_scheduling_logic as dms


def task(name, c, t, d, j=0.0):
    """One {name, C, T, D, J} task dict in ms, the step 1 shape."""
    return {"name": name, "C": c, "T": t, "D": d, "J": j}


SET_A = [  # step 1 worked task set A, deadlines 10, 20, 25, 60 ascending
    task("flight-control", 2.0, 10.0, 10.0, j=4.0),
    task("guidance", 1.0, 20.0, 20.0),
    task("navigation", 4.0, 40.0, 25.0),
    task("mission-recording", 18.0, 30.0, 60.0),
]
SET_A_NOJITTER = [dict(t, J=0.0) for t in SET_A]  # step 6 baseline


def implicit(name_prefix, pairs):
    """Implicit-deadline task set (D = T, J = 0) from (C, T) pairs, the
    step 4 equivalence shape."""
    return [task("%s%d" % (name_prefix, i), c, t, t)
            for i, (c, t) in enumerate(pairs)]


class TaskSetAssemblyTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: task-set assembly as {name, C,
    T, D, J} dicts in one time unit, with J and name optional."""

    def test_defaults_jitter_and_utilization_shape(self):
        """Step 1: a task without J defaults to J 0.0 and utilization
        sums C/T over the dicts."""
        t = {"name": "a", "C": 2.0, "T": 10.0, "D": 10.0}
        self.assertAlmostEqual(dms.utilization([t]), 0.2, delta=1e-9)

    def test_utilization_empty_list_raises(self):
        """Step 1: an empty task list cannot be admitted."""
        with self.assertRaises(ValueError):
            dms.utilization([])

    def test_utilization_missing_deadline_key_raises(self):
        """Step 1: a dict without the D key is rejected."""
        with self.assertRaises(ValueError):
            dms.utilization([{"name": "x", "C": 1.0, "T": 10.0}])

    def test_utilization_non_positive_execution_raises(self):
        """Step 1: a zero or boolean C carries no positive execution."""
        for bad in (0.0, -1.0, True):
            with self.assertRaises(ValueError):
                dms.utilization([task("x", bad, 10.0, 10.0)])

    def test_utilization_non_positive_period_raises(self):
        """Step 1: a zero, negative or boolean T has no release rhythm."""
        for bad in (0.0, -1.0, True):
            with self.assertRaises(ValueError):
                dms.utilization([task("x", 1.0, bad, 10.0)])

    def test_utilization_non_positive_deadline_raises(self):
        """Step 1: a zero or boolean D cannot bound a response."""
        for bad in (0.0, -1.0, True):
            with self.assertRaises(ValueError):
                dms.utilization([task("x", 1.0, 10.0, bad)])

    def test_utilization_negative_or_boolean_jitter_raises(self):
        """Step 1: a negative or boolean release jitter J is rejected."""
        for bad in (-1.0, True):
            with self.assertRaises(ValueError):
                dms.utilization([task("x", 1.0, 10.0, 10.0, j=bad)])

    def test_utilization_non_numeric_and_malformed_raise(self):
        """Step 1: non-numeric values and non-dict entries are rejected."""
        for bad in ([task("x", "a", 10.0, 10.0)],
                    [task("x", 1.0, 10.0, 10.0, j="big")],
                    ["not-a-dict"],
                    [(1.0, 10.0, 10.0)]):
            with self.assertRaises(ValueError):
                dms.utilization(bad)


class DeadlineMonotonicOrderTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the deadline-monotonic priority
    assignment, shorter deadline higher priority with stable ties."""

    def test_dm_priority_order_keeps_set_a_as_given(self):
        """Step 2 shorter-deadline order: set A's deadlines already
        ascend 10, 20, 25, 60, so dm_priority_order keeps the list."""
        ordered = dms.dm_priority_order(SET_A)
        names = [t["name"] for t in ordered]
        self.assertEqual(names, ["flight-control", "guidance",
                                 "navigation", "mission-recording"])
        ds = [t["D"] for t in ordered]
        self.assertTrue(all(ds[i] <= ds[i + 1] for i in range(len(ds) - 1)))

    def test_dm_priority_order_sorts_by_shorter_deadline(self):
        """Step 2: a shuffled set is returned with the shortest deadline
        first, e.g. the 25 ms-deadline navigation above the 60 ms one."""
        shuffled = [SET_A[3], SET_A[2], SET_A[1], SET_A[0]]
        ordered = dms.dm_priority_order(shuffled)
        self.assertEqual(ordered[0]["name"], "flight-control")
        self.assertEqual(ordered[3]["name"], "mission-recording")

    def test_dm_priority_order_stable_equal_deadlines(self):
        """Step 2 stable ties: equal deadlines keep their input order."""
        tasks = [task("first", 1.0, 10.0, 5.0),
                 task("second", 1.0, 10.0, 5.0)]
        ordered = dms.dm_priority_order([tasks[1], tasks[0]])
        self.assertEqual([t["name"] for t in ordered], ["second", "first"])

    def test_dm_priority_order_returns_copies_no_mutation(self):
        """Step 2: dm_priority_order returns full five-key copies and
        never mutates the input task dicts."""
        before = [dict(t) for t in SET_A]
        ordered = dms.dm_priority_order(SET_A)
        self.assertEqual(sorted(ordered[0].keys()),
                         ["C", "D", "J", "T", "name"])
        self.assertEqual(SET_A, before)

    def test_dm_priority_order_shares_task_validation(self):
        """Step 2: dm_priority_order applies the same step 1 ValueError
        rejection of an empty list and a missing D key."""
        with self.assertRaises(ValueError):
            dms.dm_priority_order([])
        with self.assertRaises(ValueError):
            dms.dm_priority_order([{"name": "x", "C": 1.0, "T": 1.0}])


class ContextUtilizationTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the context utilization U = sum
    of C/T, reported but never a verdict when deadlines differ."""

    def test_utilization_set_a_point_ninety_five(self):
        """Step 3: set A closes at utilization 0.95 (2/10 + 1/20 + 4/40
        + 18/30), under the U <= 1 line."""
        self.assertAlmostEqual(dms.utilization(SET_A), 0.95, delta=1e-9)

    def test_utilization_heavy_over_subscribed(self):
        """Step 3: the C 22 variant of set A runs at utilization
        1.083333 > 1, an over-subscribed processor."""
        heavy = [dict(t) for t in SET_A]
        heavy[3] = task("mission-recording", 22.0, 30.0, 60.0)
        self.assertAlmostEqual(dms.utilization(heavy), 1.083333,
                               delta=1e-5)

    def test_utilization_any_order(self):
        """Step 3: utilization is order independent over the task list."""
        self.assertAlmostEqual(dms.utilization(list(reversed(SET_A))),
                               dms.utilization(SET_A), delta=1e-9)


class ConstrainedDeadlineIterationTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the jitter-aware fixed-point
    response-time iteration converged against each per-task deadline;
    the constrained-deadline task needs only its first-job completion."""

    def test_navigation_response_nine_against_deadline_twenty_five(self):
        """Step 4 iteration: navigation (T 40, D 25) closes at 9.0 ms,
        at most its constrained 25 ms deadline, with flight-control's
        4 ms release jitter counted in the interference terms."""
        self.assertAlmostEqual(dms.response_time(SET_A, 2), 9.0,
                               delta=1e-9)

    def test_full_set_a_responses_inside_their_deadlines(self):
        """Step 4: set A responses [2.0, 3.0, 9.0, 32.0] each sit at
        most its own deadline [10, 20, 25, 60]."""
        r = dms.dm_response_times(SET_A)
        for got, d in zip(r["response_times"], (10.0, 20.0, 25.0, 60.0)):
            self.assertIsNotNone(got)
            self.assertTrue(got <= d + 1e-9)

    def test_implicit_deadline_equivalence_sibling_set_a(self):
        """Step 4 equivalence: with D = T and J = 0 everywhere the
        iteration reproduces the pack sibling's classic responses
        [1.0, 2.0, 6.0] on [(1, 3), (1, 4), (2, 8)]."""
        sib = implicit("a", [(1.0, 3.0), (1.0, 4.0), (2.0, 8.0)])
        r = dms.dm_response_times(sib)
        for got, want in zip(r["response_times"], (1.0, 2.0, 6.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertTrue(r["feasible"])

    def test_implicit_deadline_equivalence_sibling_set_c(self):
        """Step 4 equivalence: the same identity on [(1, 5), (1, 6),
        (2, 10)] gives [1.0, 2.0, 4.0], feasible True."""
        sib = implicit("c", [(1.0, 5.0), (1.0, 6.0), (2.0, 10.0)])
        r = dms.dm_response_times(sib)
        for got, want in zip(r["response_times"], (1.0, 2.0, 4.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertTrue(r["feasible"])

    def test_implicit_deadline_oversubscribed_sibling_set_b(self):
        """Step 4 divergence: the over-subscribed [(2, 3), (2, 5),
        (2, 7)] gives [2.0, None, None], feasible False, the second
        iterate crossing its own deadline."""
        sib = implicit("b", [(2.0, 3.0), (2.0, 5.0), (2.0, 7.0)])
        r = dms.dm_response_times(sib)
        self.assertEqual(r["response_times"], [2.0, None, None])
        self.assertFalse(r["feasible"])

    def test_single_task_response_equals_execution(self):
        """Step 4 closed form: a lone task responds in exactly its
        execution, 3.0 ms for (C 3, T 10, D 7), feasible."""
        one = [task("only", 3.0, 10.0, 7.0)]
        self.assertAlmostEqual(dms.response_time(one, 0), 3.0, delta=1e-9)
        self.assertTrue(dms.feasible(one))

    def test_single_task_execution_past_deadline_is_none(self):
        """Step 4 divergence verdict: C 3 against D 2 makes the first
        iterate itself cross the deadline, so response_time reports
        None and the set is infeasible."""
        one = [task("only", 3.0, 10.0, 2.0)]
        self.assertIsNone(dms.response_time(one, 0))
        self.assertFalse(dms.feasible(one))

    def test_single_task_doubled_execution_stays_exact(self):
        """Step 4 closed form: doubling C doubles the single-task
        response exactly while it stays within D (R = C either way)."""
        for c in (3.0, 6.0):
            self.assertAlmostEqual(
                dms.response_time([task("only", c, 10.0, 7.0)], 0),
                c, delta=1e-9)


class ArbitraryDeadlineScanTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the arbitrary-deadline
    busy-period job scan when a first-job completion past T_i makes
    later jobs queue."""

    def test_mission_recording_response_thirty_two(self):
        """Step 5: mission-recording (T 30, D 60, jittered hp) closes at
        32.0 ms, and its first-job completion 32.0 > T 30 opens the
        queueing regime, so the busy-period job scan runs."""
        self.assertAlmostEqual(dms.response_time(SET_A, 3), 32.0,
                               delta=1e-9)

    def test_busy_period_completions_and_stop_rule(self):
        """Step 5 scan: completions w(0..3) = 32.0, 62.0, 91.0, 114.0
        ms with job responses 32.0, 32.0, 31.0, 24.0; w(3) = 114.0 <=
        4 * T = 120.0 terminates the scan at the exact max 32.0."""
        rows = dms._busy_period_table(SET_A, 3)
        self.assertEqual([q for q, _, _ in rows], [0, 1, 2, 3])
        for (_, wq, resp), want_w, want_r in zip(
                rows, (32.0, 62.0, 91.0, 114.0), (32.0, 32.0, 31.0, 24.0)):
            self.assertAlmostEqual(wq, want_w, delta=1e-9)
            self.assertAlmostEqual(resp, want_r, delta=1e-9)
        self.assertLessEqual(rows[-1][1], 4 * 30.0 + 1e-9)

    def test_no_jitter_stays_out_of_queueing_regime(self):
        """Step 5 contrast: with J 0 everywhere the first-job completion
        is exactly 30.0 = T, no job ever queues, and the response is
        30.0 ms without any job scan."""
        self.assertAlmostEqual(dms.response_time(SET_A_NOJITTER, 3),
                               30.0, delta=1e-9)
        self.assertEqual(len(dms._busy_period_table(SET_A_NOJITTER, 3)), 1)

    def test_queued_job_strictly_the_worst_case(self):
        """Step 5 worst-job identity: with navigation C = 5 the
        mission-recording completions become 33.0, 64.0, 94.0, 119.0
        ms, responses 33.0, 34.0, 34.0, 29.0, so the exact worst 34.0
        ms is held by a queued job, strictly above the first-job
        completion 33.0 ms."""
        variant = [dict(t) for t in SET_A]
        variant[2] = task("navigation", 5.0, 40.0, 25.0)
        rows = dms._busy_period_table(variant, 3)
        for (_, wq, resp), want_w, want_r in zip(
                rows, (33.0, 64.0, 94.0, 119.0), (33.0, 34.0, 34.0, 29.0)):
            self.assertAlmostEqual(wq, want_w, delta=1e-9)
            self.assertAlmostEqual(resp, want_r, delta=1e-9)
        self.assertAlmostEqual(max(r[2] for r in rows), 34.0, delta=1e-9)
        self.assertAlmostEqual(dms.response_time(variant, 3), 34.0,
                               delta=1e-9)

    def test_queued_worst_variant_navigation_still_admitted(self):
        """Step 5 mixed verdict: the C = 5 navigation task itself closes
        at 10.0 ms against D 25, so the heavier task hurts the tasks
        below it, not itself."""
        variant = [dict(t) for t in SET_A]
        variant[2] = task("navigation", 5.0, 40.0, 25.0)
        self.assertAlmostEqual(dms.response_time(variant, 2), 10.0,
                               delta=1e-9)

    def test_over_subscribed_busy_period_never_ends(self):
        """Step 5 divergence: at C 22 the mission-recording busy period
        never ends (U 1.083 > 1), a queued job response crosses D 60
        and dm_response_times reports [2.0, 3.0, 9.0, None], feasible
        False; the scan terminates through the deadline crossing, not
        through an infinite loop (MAX_BUSY_PERIOD_JOBS cap)."""
        heavy = [dict(t) for t in SET_A]
        heavy[3] = task("mission-recording", 22.0, 30.0, 60.0)
        r = dms.dm_response_times(heavy)
        self.assertEqual(r["response_times"], [2.0, 3.0, 9.0, None])
        self.assertFalse(r["feasible"])
        self.assertIsNone(dms.response_time(heavy, 3))


class ReleaseJitterRecomputationTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the release-jitter recomputation
    against the zero-jitter baseline isolates the jitter cost."""

    def test_jitter_inflation_is_one_extra_preemption(self):
        """Step 6 recomputation: navigation closes at 9.0 ms with the
        4 ms flight-control release jitter and at 7.0 ms without it, so
        the jitter costs exactly 2.0 ms = C_0, one extra preemption
        counted by ceil((R + 4)/10) at the converged R."""
        with_j = dms.response_time(SET_A, 2)
        without_j = dms.response_time(SET_A_NOJITTER, 2)
        self.assertAlmostEqual(with_j, 9.0, delta=1e-9)
        self.assertAlmostEqual(without_j, 7.0, delta=1e-9)
        self.assertAlmostEqual(with_j - without_j, 2.0, delta=1e-9)

    def test_own_jitter_does_not_change_own_response(self):
        """Step 6 identity: a task's own J enters no interference count,
        so flight-control closes at its C 2.0 either way."""
        self.assertAlmostEqual(dms.response_time(SET_A, 0), 2.0,
                               delta=1e-9)
        self.assertAlmostEqual(dms.response_time(SET_A_NOJITTER, 0),
                               2.0, delta=1e-9)

    def test_jitter_can_open_the_queueing_regime(self):
        """Step 6 regime contrast: with the 4 ms jitter the
        mission-recording first-job completion 32.0 ms passes T 30 and
        jobs queue, while the zero-jitter baseline stays at 30.0 ms
        with no queueing at all."""
        with_j = dms.response_time(SET_A, 3)
        without_j = dms.response_time(SET_A_NOJITTER, 3)
        self.assertAlmostEqual(with_j, 32.0, delta=1e-9)
        self.assertAlmostEqual(without_j, 30.0, delta=1e-9)


class FeasibleVerdictTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the feasible verdict of the
    whole deadline-monotonic-ordered set."""

    def test_set_a_feasible_verdict_and_names(self):
        """Step 7 verdict: dm_response_times(SET_A) returns names and
        response_times in priority order, feasible True at utilization
        0.95, every response at most its own deadline."""
        r = dms.dm_response_times(SET_A)
        self.assertEqual(r["names"], ["flight-control", "guidance",
                                      "navigation", "mission-recording"])
        for got, want in zip(r["response_times"], (2.0, 3.0, 9.0, 32.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertTrue(r["feasible"])
        self.assertAlmostEqual(r["utilization"], 0.95, delta=1e-9)

    def test_feasible_convenience_matches_verdict(self):
        """Step 7 convenience: feasible(SET_A) is True and feasible of
        the over-subscribed C 22 variant is False."""
        heavy = [dict(t) for t in SET_A]
        heavy[3] = task("mission-recording", 22.0, 30.0, 60.0)
        self.assertTrue(dms.feasible(SET_A))
        self.assertFalse(dms.feasible(heavy))

    def test_order_validation_of_analysis_functions(self):
        """Step 2 guard: response_time, dm_response_times and feasible
        all reject a list whose deadlines are not non-decreasing, e.g.
        period-ordered set A (60 ms before 25 ms), with the
        sort-with-dm_priority_order-first message."""
        rm_ordered = [SET_A[0], SET_A[1], SET_A[3], SET_A[2]]
        for fn in (lambda ts: dms.response_time(ts, 0),
                   dms.dm_response_times,
                   dms.feasible):
            with self.assertRaisesRegex(
                    ValueError,
                    "deadline-monotonic priority order"):
                fn(rm_ordered)

    def test_index_out_of_range_and_type(self):
        """Step 4 guard: response_time raises for an index outside
        [0, len(tasks)) on the four-task set."""
        for idx in (-1, 4, 7):
            with self.assertRaises(ValueError):
                dms.response_time(SET_A, idx)


class OrderingIsTheAnalysisTests(unittest.TestCase):
    """Step 2 contrast: the same four tasks are feasible in
    deadline-monotonic order and infeasible in period (RM) order; the
    period-ordered hp sets are driven through the module's completion
    solver as the RM-order diagnostic."""

    def test_period_order_makes_navigation_diverge(self):
        """Step 2 diagnostic: under period order 10, 20, 30, 40 the
        navigation task sits below mission-recording and its second
        iterate 30.0 crosses D 25, so its completion is None, while
        flight-control, guidance and mission-recording close at 2.0,
        3.0 and 26.0 ms."""
        rm_ordered = [SET_A[0], SET_A[1], SET_A[3], SET_A[2]]
        ts = dms._norm_tasks(rm_ordered)
        self.assertAlmostEqual(dms._completion(ts, 0, 0), 2.0, delta=1e-9)
        self.assertAlmostEqual(dms._completion(ts, 1, 0), 3.0, delta=1e-9)
        self.assertAlmostEqual(dms._completion(ts, 2, 0), 26.0, delta=1e-9)
        self.assertIsNone(dms._completion(ts, 3, 0))

    def test_deadline_order_is_the_feasible_one(self):
        """Step 2 verdict contrast: the deadline-monotonic order of the
        same tasks is feasible with navigation at 9.0 <= 25, where the
        period order above diverges to None."""
        self.assertTrue(dms.feasible(SET_A))
        self.assertAlmostEqual(dms.response_time(SET_A, 2), 9.0,
                               delta=1e-9)


class ModuleDisciplineTests(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the deterministic contract test
    run and module discipline (constants, imports, determinism)."""

    def test_module_constants_and_imports(self):
        """Step 8 discipline: MAX_RTA_ITERATIONS fixed at 100,
        MAX_BUSY_PERIOD_JOBS at 1000, and the module imports nothing
        beyond math."""
        self.assertEqual(dms.MAX_RTA_ITERATIONS, 100)
        self.assertEqual(dms.MAX_BUSY_PERIOD_JOBS, 1000)
        src = inspect.getsource(dms)
        imports = [line.strip() for line in src.splitlines()
                   if line.strip().startswith(("import ", "from "))]
        self.assertEqual(imports, ["import math"])

    def test_deterministic_outputs_run_to_run(self):
        """Step 8 determinism: identical outputs run to run, no
        randomness anywhere in the analysis."""
        r1 = dms.dm_response_times(SET_A)
        r2 = dms.dm_response_times(SET_A)
        self.assertEqual(r1, r2)

    def test_real_value_error_messages(self):
        """Steps 1-4 real messages: empty list, non-DM order, C = 0,
        J = -1, missing D and index out of range raise with the pinned
        text."""
        cases = [
            ([], "task list must be a non-empty list"),
            ([SET_A[1], SET_A[0]], "sort with dm_priority_order first"),
            ([task("x", 0.0, 10.0, 10.0)], "C must be a positive number"),
            ([task("x", 1.0, 10.0, 10.0, j=-1.0)],
             "J must be a non-negative number"),
            ([{"name": "x", "C": 1.0, "T": 10.0}], r"missing key\(s\) D"),
        ]
        for bad, msg in cases:
            with self.assertRaisesRegex(ValueError, msg):
                dms.dm_response_times(bad)
        with self.assertRaisesRegex(ValueError, "index out of range"):
            dms.response_time(SET_A, 4)


if __name__ == "__main__":
    unittest.main()

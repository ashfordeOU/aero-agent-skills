"""Offline contract test for shared-resource-access-control (avionics/fsw).

Deterministic stdlib unittest, no network, no RNG. Covers the spec
anchors: priority ceilings R1 3 / R2 2, the blocking truth table
T1 0.6 / T2 0.7 / T3 0.0, fixed-point response times with blocking
T1 1.6 / T2 3.7 / T3 7.0 within 1e-9, the empty-lock identity (zero
blocking, response times equal the plain fixed-point analysis
T1 1.0 / T2 3.0 / T3 7.0), the ceiling-rule boundary, blocking-driven
infeasibility, the exact dict keys, ValueError rejection of
non-physical inputs, and run-to-run determinism.

Run offline: python3 scripts/test_shared_resource_access_control.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shared_resource_access_control_logic as sra

# Spec anchor task set: T1 highest priority (3), T3 lowest (1).
TASKS = [
    {"name": "T1", "C": 1, "T": 5, "priority": 3},
    {"name": "T2", "C": 2, "T": 10, "priority": 2},
    {"name": "T3", "C": 3, "T": 20, "priority": 1},
]
# Spec anchor locks: R1 ceiling 3 (T1, T3), R2 ceiling 2 (T2, T3).
LOCKS = [
    {"resource": "R1", "task": "T1", "cs": 0.5},
    {"resource": "R1", "task": "T3", "cs": 0.6},
    {"resource": "R2", "task": "T2", "cs": 0.8},
    {"resource": "R2", "task": "T3", "cs": 0.7},
]


class TestPriorityCeiling(unittest.TestCase):
    """Ceiling = highest priority among the tasks that lock a resource."""

    def test_anchor_ceiling_r1(self):
        self.assertEqual(sra.priority_ceiling(TASKS, LOCKS)["R1"], 3)

    def test_anchor_ceiling_r2(self):
        self.assertEqual(sra.priority_ceiling(TASKS, LOCKS)["R2"], 2)

    def test_resource_ceiling_anchor_values(self):
        self.assertEqual(sra.resource_ceiling(TASKS, LOCKS, "R1"), 3)
        self.assertEqual(sra.resource_ceiling(TASKS, LOCKS, "R2"), 2)

    def test_ceiling_map_keys_are_resources(self):
        self.assertEqual(set(sra.priority_ceiling(TASKS, LOCKS)),
                         {"R1", "R2"})

    def test_dict_keyed_tasks_agree_with_list_form(self):
        as_dict = {t["name"]: t for t in TASKS}
        self.assertEqual(sra.priority_ceiling(as_dict, LOCKS),
                         sra.priority_ceiling(TASKS, LOCKS))


class TestBlockingTruthTable(unittest.TestCase):
    """PCP ceiling rule: longest cs of a lower task on a ceiling-qualifying
    resource; at most one such section can block the task."""

    def test_blocking_t1_anchor(self):
        # T3's 0.6 cs on R1 (ceiling 3 >= prio 3) blocks T1; T2's 0.8 on
        # R2 (ceiling 2 < prio 3) and T3's 0.7 on R2 do not.
        self.assertAlmostEqual(
            sra.worst_case_blocking("T1", TASKS, LOCKS), 0.6, delta=1e-12)

    def test_blocking_t2_anchor(self):
        # T3's 0.7 cs on R2 (ceiling 2 >= prio 2) blocks T2.
        self.assertAlmostEqual(
            sra.worst_case_blocking("T2", TASKS, LOCKS), 0.7, delta=1e-12)

    def test_blocking_t3_anchor_zero(self):
        # T3 is the lowest-priority task: no lower-priority task exists.
        self.assertEqual(sra.worst_case_blocking("T3", TASKS, LOCKS), 0.0)

    def test_blocking_map_matches_anchor(self):
        blocking = sra.blocking_times(TASKS, LOCKS)
        for name, expected in (("T1", 0.6), ("T2", 0.7), ("T3", 0.0)):
            self.assertAlmostEqual(blocking[name], expected, delta=1e-12)

    def test_blocking_non_negative_for_every_task(self):
        for name in ("T1", "T2", "T3"):
            self.assertGreaterEqual(
                sra.worst_case_blocking(name, TASKS, LOCKS), 0.0)

    def test_ceiling_below_priority_contributes_nothing(self):
        # T2 (prio 2) alone locks R2: ceiling 2 < T1's prio 3, so T2's
        # 0.8 cs on R2 must not appear in T1's blocking at all.
        tasks = [{"name": "T1", "C": 1, "T": 5, "priority": 3},
                 {"name": "T2", "C": 2, "T": 10, "priority": 2}]
        locks = [{"resource": "R2", "task": "T2", "cs": 0.8}]
        self.assertEqual(sra.worst_case_blocking("T1", tasks, locks), 0.0)
        self.assertEqual(sra.worst_case_blocking("T2", tasks, locks), 0.0)

    def test_equal_priority_lock_does_not_block(self):
        # Blocking only comes from strictly lower-priority tasks.
        tasks = [{"name": "T1", "C": 1, "T": 5, "priority": 4},
                 {"name": "T2", "C": 1, "T": 10, "priority": 4}]
        locks = [{"resource": "R", "task": "T1", "cs": 0.3},
                 {"resource": "R", "task": "T2", "cs": 0.9}]
        self.assertEqual(sra.worst_case_blocking("T1", tasks, locks), 0.0)
        self.assertEqual(sra.worst_case_blocking("T2", tasks, locks), 0.0)


class TestResponseTimeWithBlocking(unittest.TestCase):
    """Fixed point R_i = C_i + B_i + sum hp ceil(R_i / T_j) * C_j."""

    def test_rta_t1_anchor(self):
        # 1 + 0.6 = 1.6, no higher-priority task.
        self.assertAlmostEqual(
            sra.response_time_with_blocking("T1", TASKS, LOCKS), 1.6,
            delta=1e-9)

    def test_rta_t2_anchor(self):
        # 2 + 0.7 + ceil(R / 5) * 1 converges to 3.7.
        self.assertAlmostEqual(
            sra.response_time_with_blocking("T2", TASKS, LOCKS), 3.7,
            delta=1e-9)

    def test_rta_t3_anchor(self):
        # 3 + 0 + ceil(R / 5) + 2 * ceil(R / 10) converges to 7.0.
        self.assertAlmostEqual(
            sra.response_time_with_blocking("T3", TASKS, LOCKS), 7.0,
            delta=1e-9)

    def test_empty_locks_equal_plain_rta(self):
        # Zero blocking turns the analysis into plain response-time
        # analysis: 1.0 / 3.0 / 7.0 for the anchor tasks. T3's plain
        # fixed point is 7.0 (3 -> 6 -> 7), identical to the with-lock
        # value because T3's blocking is zero.
        result = sra.rta_with_blocking_feasibility(TASKS, [])
        for name, expected in (("T1", 1.0), ("T2", 3.0), ("T3", 7.0)):
            self.assertAlmostEqual(result["response_times"][name], expected,
                                   delta=1e-9)
            self.assertEqual(result["blocking"][name], 0.0)

    def test_blocking_never_shrinks_response_time(self):
        # Adding resources can only add blocking, so every response
        # time with locks is at least the plain value.
        plain = sra.rta_with_blocking_feasibility(TASKS, [])
        with_locks = sra.rta_with_blocking_feasibility(TASKS, LOCKS)
        for name in ("T1", "T2", "T3"):
            self.assertGreaterEqual(
                with_locks["response_times"][name],
                plain["response_times"][name])

    def test_t1_blocking_term_exact(self):
        # T1 with blocking (1.6) is exactly plain RTA (1.0) plus 0.6.
        plain = sra.rta_with_blocking_feasibility(TASKS, [])["response_times"]
        blocked = sra.response_time_with_blocking("T1", TASKS, LOCKS)
        self.assertAlmostEqual(blocked - plain["T1"], 0.6, delta=1e-12)


class TestFeasibility(unittest.TestCase):
    """Verdict: feasible iff every response time is at most its period."""

    def test_anchor_feasible_true(self):
        result = sra.rta_with_blocking_feasibility(TASKS, LOCKS)
        self.assertTrue(result["feasible"])

    def test_anchor_response_times_within_periods(self):
        result = sra.rta_with_blocking_feasibility(TASKS, LOCKS)
        for name, period in (("T1", 5), ("T2", 10), ("T3", 20)):
            self.assertLessEqual(result["response_times"][name], period)

    def test_result_dict_keys_exact(self):
        result = sra.rta_with_blocking_feasibility(TASKS, LOCKS)
        self.assertEqual(set(result), {"blocking", "response_times",
                                       "feasible"})
        self.assertEqual(list(result["blocking"]), ["T1", "T2", "T3"])
        self.assertEqual(list(result["response_times"]), ["T1", "T2", "T3"])

    def test_overloaded_set_infeasible(self):
        # Higher-priority demand 1/2 + 2/3 > 1: T3's response time
        # grows without bound and the set is infeasible.
        tasks = [{"name": "T1", "C": 1, "T": 2, "priority": 3},
                 {"name": "T2", "C": 2, "T": 3, "priority": 2},
                 {"name": "T3", "C": 1, "T": 4, "priority": 1}]
        result = sra.rta_with_blocking_feasibility(tasks, [])
        self.assertFalse(result["feasible"])
        self.assertGreater(result["response_times"]["T3"], 4)

    def test_blocking_can_break_schedulability(self):
        # T1 with C 1, T 1.8 is feasible alone (R = 1.0) but T2's 1.0
        # critical section on a ceiling-2 resource pushes R1 to 2.0.
        tasks = [{"name": "T1", "C": 1, "T": 1.8, "priority": 2},
                 {"name": "T2", "C": 1, "T": 6, "priority": 1}]
        locks = [{"resource": "R", "task": "T1", "cs": 0.2},
                 {"resource": "R", "task": "T2", "cs": 1.0}]
        self.assertTrue(
            sra.rta_with_blocking_feasibility(tasks, [])["feasible"])
        self.assertFalse(
            sra.rta_with_blocking_feasibility(tasks, locks)["feasible"])


class TestValueErrors(unittest.TestCase):
    """Non-physical inputs raise ValueError from every entry point."""

    def test_non_positive_execution_time(self):
        bad = {"name": "T1", "C": 0, "T": 5, "priority": 3}
        with self.assertRaises(ValueError):
            sra.blocking_times([bad], [])
        with self.assertRaises(ValueError):
            sra.rta_with_blocking_feasibility([bad], [])

    def test_non_positive_period(self):
        bad = {"name": "T1", "C": 1, "T": -2, "priority": 3}
        with self.assertRaises(ValueError):
            sra.priority_ceiling([bad], LOCKS)
        with self.assertRaises(ValueError):
            sra.response_time_with_blocking("T1", [bad], LOCKS)

    def test_execution_time_exceeds_period(self):
        bad = {"name": "T1", "C": 6, "T": 5, "priority": 3}
        for fn in (sra.priority_ceiling, sra.blocking_times,
                   sra.rta_with_blocking_feasibility):
            with self.assertRaises(ValueError):
                fn([bad], LOCKS)

    def test_negative_critical_section(self):
        locks = [{"resource": "R1", "task": "T1", "cs": -0.5}]
        for fn in (sra.priority_ceiling, sra.blocking_times,
                   sra.rta_with_blocking_feasibility):
            with self.assertRaises(ValueError):
                fn(TASKS, locks)
        with self.assertRaises(ValueError):
            sra.worst_case_blocking("T1", TASKS, locks)

    def test_unknown_task_reference_in_lock(self):
        locks = [{"resource": "R1", "task": "T9", "cs": 0.5}]
        for fn in (sra.priority_ceiling, sra.blocking_times,
                   sra.rta_with_blocking_feasibility):
            with self.assertRaises(ValueError):
                fn(TASKS, locks)
        with self.assertRaises(ValueError):
            sra.response_time_with_blocking("T1", TASKS, locks)

    def test_empty_task_set(self):
        for fn in (sra.priority_ceiling, sra.blocking_times,
                   sra.rta_with_blocking_feasibility):
            with self.assertRaises(ValueError):
                fn([], LOCKS)

    def test_empty_lock_list_for_ceiling(self):
        # A ceiling is undefined when nothing is locked; blocking and
        # response-time functions accept the empty list (zero blocking).
        with self.assertRaises(ValueError):
            sra.priority_ceiling(TASKS, [])
        with self.assertRaises(ValueError):
            sra.resource_ceiling(TASKS, [], "R1")
        self.assertEqual(sra.blocking_times(TASKS, [])["T1"], 0.0)

    def test_duplicate_task_names(self):
        tasks = [{"name": "T1", "C": 1, "T": 5, "priority": 3},
                 {"name": "T1", "C": 2, "T": 10, "priority": 2}]
        with self.assertRaises(ValueError):
            sra.blocking_times(tasks, [])

    def test_unknown_task_and_resource_lookup(self):
        with self.assertRaises(ValueError):
            sra.worst_case_blocking("T9", TASKS, LOCKS)
        with self.assertRaises(ValueError):
            sra.resource_ceiling(TASKS, LOCKS, "R9")

    def test_malformed_and_boolean_entries(self):
        with self.assertRaises(ValueError):
            sra.blocking_times(["not-a-dict"], [])
        with self.assertRaises(ValueError):
            sra.blocking_times([{"name": "T1", "C": 1, "T": 5}], [])
        with self.assertRaises(ValueError):
            sra.priority_ceiling(TASKS, [{"resource": "R", "task": "T1"}])
        with self.assertRaises(ValueError):
            sra.rta_with_blocking_feasibility(
                [{"name": "T1", "C": True, "T": 5, "priority": 3}], [])
        with self.assertRaises(ValueError):
            sra.priority_ceiling(TASKS, [{"resource": "R", "task": "T1",
                                          "cs": True}])


class TestDeterminism(unittest.TestCase):
    """Identical outputs run to run, keys in documented order."""

    def test_two_runs_identical(self):
        first = sra.rta_with_blocking_feasibility(TASKS, LOCKS)
        second = sra.rta_with_blocking_feasibility(TASKS, LOCKS)
        self.assertEqual(first, second)
        self.assertEqual(sra.priority_ceiling(TASKS, LOCKS),
                         sra.priority_ceiling(TASKS, LOCKS))

    def test_single_task_closed_form(self):
        tasks = [{"name": "T1", "C": 2, "T": 7, "priority": 1}]
        result = sra.rta_with_blocking_feasibility(tasks, [])
        self.assertEqual(result["response_times"]["T1"], 2.0)
        self.assertTrue(result["feasible"])
        tasks[0]["T"] = 1.5  # C 2 > T 1.5 is rejected, C == T is not
        tasks[0]["C"] = 1.5
        result = sra.rta_with_blocking_feasibility(tasks, [])
        self.assertAlmostEqual(result["response_times"]["T1"], 1.5,
                               delta=1e-12)


if __name__ == "__main__":
    unittest.main()

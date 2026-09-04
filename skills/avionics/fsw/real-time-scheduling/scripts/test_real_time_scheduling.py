"""Offline contract test for real-time-scheduling (avionics/fsw).

Deterministic stdlib unittest, no network, no RNG. Covers the spec
anchors: Liu-Layland bounds U_rm(2/3/4), the three worked task sets
A = [(1,3),(1,4),(2,8)], B = [(2,3),(2,5),(2,7)], C = [(1,5),(1,6),
(2,10)], an RM-infeasible / EDF-feasible-only set D, ValueError
rejection of empty and non-physical task lists, utilization
monotonicity, the convenience dict keys, and run-to-run determinism.

Run offline: python3 scripts/test_real_time_scheduling.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import real_time_scheduling_logic as rts

# Spec worked task sets: (C, T) pairs, implicit deadline D = T.
SET_A = [(1, 3), (1, 4), (2, 8)]
SET_B = [(2, 3), (2, 5), (2, 7)]
SET_C = [(1, 5), (1, 6), (2, 10)]
# RM-infeasible (task 2 response time crosses its period) yet
# U = 0.8 + 1.2/7 ~ 0.9714 <= 1, so EDF-feasible-only.
SET_D = [(4, 5), (1.2, 7)]

LL_ANCHORS = {2: 0.828427, 3: 0.779763, 4: 0.756828}


class TestLiuLaylandBound(unittest.TestCase):
    """Liu-Layland sufficient utilization bound anchors."""

    def test_ll_bound_2_anchor(self):
        self.assertAlmostEqual(rts.liu_layland_bound(2), LL_ANCHORS[2],
                               delta=1e-5)

    def test_ll_bound_3_anchor(self):
        self.assertAlmostEqual(rts.liu_layland_bound(3), LL_ANCHORS[3],
                               delta=1e-5)

    def test_ll_bound_4_anchor(self):
        self.assertAlmostEqual(rts.liu_layland_bound(4), LL_ANCHORS[4],
                               delta=1e-5)

    def test_ll_bound_single_task_one(self):
        # U_rm(1) = 1: one task may use the whole processor.
        self.assertAlmostEqual(rts.liu_layland_bound(1), 1.0, delta=1e-12)
        self.assertAlmostEqual(rts.liu_layland_bound(1.0), 1.0, delta=1e-12)

    def test_ll_bound_invalid_n_raises_value_error(self):
        for bad in (0, -3, 2.5, "three", True):
            with self.assertRaises(ValueError):
                rts.liu_layland_bound(bad)


class TestValidation(unittest.TestCase):
    """ValueError rejection of empty and non-physical task lists."""

    def test_empty_task_list_raises_everywhere(self):
        for fn in (rts.utilization, rts.rm_ub_feasible,
                   rts.rm_response_times, rts.rm_feasible,
                   rts.edf_feasible, rts.scheduling_summary):
            with self.assertRaises(ValueError):
                fn([])

    def test_non_positive_execution_time_raises(self):
        for bad in (0, -1, -0.5):
            with self.assertRaises(ValueError):
                rts.utilization([(bad, 10), (1, 5)])

    def test_non_positive_period_raises(self):
        for bad in (0, -2):
            with self.assertRaises(ValueError):
                rts.rm_feasible([(1, 5), (1, bad)])

    def test_invalid_entries_raise(self):
        with self.assertRaises(ValueError):
            rts.utilization([(1, 2, 3)])          # not a (C, T) pair
        with self.assertRaises(ValueError):
            rts.rm_response_times(["not-a-task"])  # not a pair at all
        with self.assertRaises(ValueError):
            rts.edf_feasible([("a", 2), (1, 5)])   # non-numeric C
        with self.assertRaises(ValueError):
            rts.utilization([(True, 2)])           # bool is not a time


class TestWorkedSetA(unittest.TestCase):
    """Set A = [(1,3),(1,4),(2,8)]: RTA beats the utilization bound."""

    def test_set_a_utilization_anchor(self):
        self.assertAlmostEqual(rts.utilization(SET_A), 0.8333333333333333,
                               delta=1e-9)

    def test_set_a_rm_ub_inconclusive(self):
        # U 0.8333 > U_rm(3) 0.7798, so the bound test is inconclusive.
        self.assertFalse(rts.rm_ub_feasible(SET_A))

    def test_set_a_edf_feasible(self):
        self.assertTrue(rts.edf_feasible(SET_A))

    def test_set_a_response_times_anchor(self):
        times = rts.rm_response_times(SET_A)
        if times is None:
            self.fail("set A response times must converge")
        for r, expected in zip(times, (1, 2, 6)):
            self.assertAlmostEqual(r, expected, delta=1e-9)
            self.assertEqual(r, round(r))  # integral for integer input

    def test_set_a_rm_exact_feasible(self):
        self.assertTrue(rts.rm_feasible(SET_A))

    def test_set_a_summary_verdict_inconclusive_exact(self):
        summary = rts.scheduling_summary(SET_A)
        self.assertFalse(summary["rm_ub_verdict"])
        self.assertTrue(summary["rm_exact_feasible"])
        self.assertTrue(summary["edf_feasible"])
        self.assertEqual(summary["verdict"],
                         "RM-exact-feasible (UB inconclusive)")


class TestWorkedSetB(unittest.TestCase):
    """Set B = [(2,3),(2,5),(2,7)]: U > 1, RTA diverges, infeasible."""

    def test_set_b_utilization_anchor(self):
        self.assertAlmostEqual(rts.utilization(SET_B), 1.3523809523809525,
                               delta=1e-9)
        self.assertGreater(rts.utilization(SET_B), 1.0)

    def test_set_b_edf_infeasible(self):
        self.assertFalse(rts.edf_feasible(SET_B))

    def test_set_b_rta_divergence_returns_none(self):
        self.assertIsNone(rts.rm_response_times(SET_B))

    def test_set_b_rm_infeasible(self):
        self.assertFalse(rts.rm_feasible(SET_B))

    def test_set_b_summary_verdict_rm_infeasible(self):
        summary = rts.scheduling_summary(SET_B)
        self.assertFalse(summary["edf_feasible"])
        self.assertIsNone(summary["rm_exact_response_times"])
        self.assertEqual(summary["verdict"], "RM-infeasible")


class TestWorkedSetC(unittest.TestCase):
    """Set C = [(1,5),(1,6),(2,10)]: RM guaranteed by the utilization bound."""

    def test_set_c_utilization_anchor(self):
        self.assertAlmostEqual(rts.utilization(SET_C), 0.5666666666666667,
                               delta=1e-9)

    def test_set_c_rm_ub_guaranteed(self):
        # U 0.5667 <= U_rm(3) 0.7798: sufficient test passes.
        self.assertTrue(rts.rm_ub_feasible(SET_C))

    def test_set_c_response_times_anchor(self):
        times = rts.rm_response_times(SET_C)
        if times is None:
            self.fail("set C response times must converge")
        for r, expected in zip(times, (1, 2, 4)):
            self.assertAlmostEqual(r, expected, delta=1e-9)

    def test_set_c_rm_feasible(self):
        self.assertTrue(rts.rm_feasible(SET_C))

    def test_set_c_summary_verdict_guaranteed_by_ub(self):
        summary = rts.scheduling_summary(SET_C)
        self.assertTrue(summary["rm_ub_verdict"])
        self.assertEqual(summary["verdict"], "RM-guaranteed-by-UB")


class TestEdfFeasibleOnly(unittest.TestCase):
    """Set D = [(4,5),(1.2,7)]: EDF works where exact RM analysis fails."""

    def test_set_d_utilization_below_one(self):
        self.assertAlmostEqual(rts.utilization(SET_D), 0.9714285714285714,
                               delta=1e-9)
        self.assertLessEqual(rts.utilization(SET_D), 1.0)

    def test_set_d_edf_feasible(self):
        self.assertTrue(rts.edf_feasible(SET_D))

    def test_set_d_rm_analysis_fails_and_verdict(self):
        # Task 2 response time crosses its period: exact analysis
        # terminates as infeasible and the verdict is EDF-feasible-only.
        self.assertIsNone(rts.rm_response_times(SET_D))
        self.assertFalse(rts.rm_feasible(SET_D))
        summary = rts.scheduling_summary(SET_D)
        self.assertFalse(summary["rm_exact_feasible"])
        self.assertTrue(summary["edf_feasible"])
        self.assertEqual(summary["verdict"], "EDF-feasible-only")


class TestSingleTaskBehavior(unittest.TestCase):
    """Single-task closed forms: R = C, feasible iff C <= T."""

    def test_single_task_response_time_equals_execution(self):
        self.assertEqual(rts.rm_response_times([(2.0, 10)]), [2.0])
        self.assertTrue(rts.rm_feasible([(2.0, 10)]))
        self.assertAlmostEqual(rts.utilization([(2.0, 10)]), 0.2,
                               delta=1e-12)

    def test_single_task_deadline_miss_infeasible(self):
        # C > T: response time cannot fit the period, EDF also fails.
        self.assertIsNone(rts.rm_response_times([(12, 10)]))
        self.assertFalse(rts.rm_feasible([(12, 10)]))
        self.assertFalse(rts.edf_feasible([(12, 10)]))


class TestPropertiesAndSummary(unittest.TestCase):
    """Utilization monotonicity, EDF boundary, dict keys, determinism."""

    def test_adding_task_raises_utilization(self):
        base = [(1, 10), (1, 20)]
        extended = base + [(1, 10)]
        self.assertGreater(rts.utilization(extended), rts.utilization(base))

    def test_doubling_c_doubles_contribution(self):
        before = rts.utilization([(1, 10), (2, 5)])
        after = rts.utilization([(2, 10), (2, 5)])
        # Doubling the first task's C adds exactly 0.1 to the total.
        self.assertAlmostEqual(after - before, 0.1, delta=1e-12)
        self.assertAlmostEqual(
            rts.utilization([(4, 10)]) / rts.utilization([(2, 10)]),
            2.0, delta=1e-12)

    def test_edf_feasible_at_unit_utilization(self):
        tasks = [(1, 2), (1, 2)]  # U = 1.0 exactly: EDF schedulable.
        self.assertAlmostEqual(rts.utilization(tasks), 1.0, delta=1e-12)
        self.assertTrue(rts.edf_feasible(tasks))

    def test_summary_contains_exact_keys(self):
        summary = rts.scheduling_summary(SET_A)
        self.assertEqual(
            set(summary.keys()),
            {"utilization", "n_tasks", "liu_layland_bound",
             "rm_ub_verdict", "rm_exact_response_times",
             "rm_exact_feasible", "edf_feasible", "verdict"},
        )
        self.assertEqual(summary["n_tasks"], 3)
        self.assertAlmostEqual(summary["liu_layland_bound"],
                               LL_ANCHORS[3], delta=1e-5)

    def test_determinism_identical_outputs(self):
        self.assertEqual(rts.scheduling_summary(SET_A),
                         rts.scheduling_summary(SET_A))
        self.assertEqual(rts.rm_response_times(SET_A),
                         rts.rm_response_times(SET_A))
        self.assertEqual(rts.scheduling_summary(SET_B),
                         rts.scheduling_summary(SET_B))


if __name__ == "__main__":
    unittest.main(verbosity=2)

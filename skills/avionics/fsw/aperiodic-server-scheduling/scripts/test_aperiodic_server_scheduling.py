"""Contract test: avionics/fsw/aperiodic-server-scheduling (wave-44).

Deterministic, offline, stdlib unittest. The test docstrings name the
SKILL.md workflow steps each test exercises: step 1 the periodic
baseline feasibility check, step 2 the aperiodic load reduction, step 3
the server budget sizing, step 4 the response-time analysis with the
inserted budget, step 5 the server placement scan, step 6 the
worst-case aperiodic response bound, step 7 the polling-server,
deferrable-server and sporadic-server phase comparison, step 8 the
capacity-loss wait and replenishment arithmetic, step 9 the
deterministic contract test run.

Runs via `python3 scripts/test_aperiodic_server_scheduling.py` and
exits 0. Numeric asserts are tolerance-based throughout (the
exact-float lesson: the pyenv hook interpreter sums Neumaier-accurate
while /usr/bin/python3 3.9.6 does not, so no exact equality on computed
aggregates).
"""

import inspect
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aperiodic_server_scheduling_logic as sched

A = [(1, 5), (2, 10), (3, 25)]  # periodic task set A, ms, RM order
STREAMS_A = [(1.0, 20.0), (2.0, 40.0)]  # event streams E1, E2, ms
STREAMS_B = [(1.0, 20.0), (2.0, 40.0), (3.0, 12.5)]  # + telemetry stream


class PeriodicBaselineTests(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the periodic baseline feasibility
    check over the (C, T) task set."""

    def test_periodic_utilization_set_a(self):
        """Step 1 baseline utilization: 1/5 + 2/10 + 3/25 = 0.52."""
        self.assertAlmostEqual(sched.periodic_utilization(A), 0.52, delta=1e-9)

    def test_periodic_utilization_empty_list_raises(self):
        """A task set with no tasks cannot be admitted."""
        with self.assertRaises(ValueError):
            sched.periodic_utilization([])

    def test_periodic_utilization_zero_execution_raises(self):
        """A (0, T) task has no positive worst-case execution."""
        with self.assertRaises(ValueError):
            sched.periodic_utilization([(0, 5)])

    def test_periodic_utilization_zero_period_raises(self):
        """A (C, 0) task has no release rhythm."""
        with self.assertRaises(ValueError):
            sched.periodic_utilization([(1, 0)])

    def test_periodic_utilization_malformed_entry_raises(self):
        """Malformed and boolean task entries are rejected."""
        for bad in [("a", 5), (1,), (1, 2, 3), (True, 5), (1, True)]:
            with self.assertRaises(ValueError):
                sched.periodic_utilization([bad])


class AperiodicLoadTests(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the aperiodic load reduction of
    the (s, a) event streams into the load utilization."""

    def test_aperiodic_utilization_streams_a(self):
        """Step 2 load utilization of E1 and E2: 1/20 + 2/40 = 0.1."""
        self.assertAlmostEqual(sched.aperiodic_utilization(STREAMS_A), 0.1,
                               delta=1e-9)

    def test_aperiodic_utilization_empty_is_zero(self):
        """An empty stream list carries zero aperiodic load, exactly."""
        self.assertEqual(sched.aperiodic_utilization([]), 0.0)

    def test_aperiodic_utilization_doubled_executions(self):
        """Doubling every worst-case execution s doubles the load."""
        doubled = [(2.0, 20.0), (4.0, 40.0)]
        self.assertAlmostEqual(
            sched.aperiodic_utilization(doubled),
            2 * sched.aperiodic_utilization(STREAMS_A), delta=1e-9)

    def test_aperiodic_utilization_invalid_raises(self):
        """Zero or negative s and a cannot form an event stream."""
        for bad in [(0.0, 5.0), (1.0, 0.0), (-1.0, 5.0), (1.0, -5.0),
                    (True, 5.0)]:
            with self.assertRaises(ValueError):
                sched.aperiodic_utilization([bad])


class ServerSizingTests(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the server budget sizing from the
    load utilization U_s = u_a + margin with C_s = U_s * T_s."""

    def test_server_parameters_nominal(self):
        """Step 3 sizing at u_a 0.1, T_s 25 ms, margin 0.02 gives the
        3 ms capacity at utilization 0.12, the sized server budget."""
        p = sched.server_parameters(0.1, 25, 0.02)
        self.assertEqual(p["period"], 25)
        self.assertAlmostEqual(p["capacity"], 3.0, delta=1e-3)
        self.assertAlmostEqual(p["utilization"], 0.12, delta=1e-9)

    def test_server_parameters_round_trip(self):
        """Capacity over period recovers the utilization exactly."""
        p = sched.server_parameters(0.1, 25, 0.02)
        self.assertAlmostEqual(p["capacity"] / p["period"], 0.12, delta=1e-9)

    def test_server_parameters_doubled_period(self):
        """Doubling T_s at fixed U_s doubles C_s, utilization invariant:
        6.0 ms at T_s 50 against 3.0 ms at T_s 25."""
        p_small = sched.server_parameters(0.1, 25, 0.02)
        p_large = sched.server_parameters(0.1, 50, 0.02)
        self.assertAlmostEqual(p_large["capacity"], 6.0, delta=1e-3)
        self.assertAlmostEqual(p_large["utilization"], 0.12, delta=1e-9)
        self.assertAlmostEqual(p_large["capacity"],
                               2 * p_small["capacity"], delta=1e-9)

    def test_server_parameters_invalid_raises(self):
        """Negative load or margin, zero period, utilization above 1 and
        zero capacity are all rejected."""
        for args in [(-0.1, 25, 0.0), (0.1, 0, 0.02), (0.1, 25, -0.01),
                     (1.0, 25, 0.1), (0.0, 25, 0.0)]:
            with self.assertRaises(ValueError):
                sched.server_parameters(*args)


class SingleJobResponseTests(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the polling-server,
    deferrable-server and sporadic-server phase comparison for a single
    job with an empty queue and an available budget."""

    def test_polling_phase_zero_serves_immediately(self):
        """Step 7 polling at phase 0.0, the job arrives exactly at a poll
        instant, response equals C_a = 2 ms."""
        self.assertAlmostEqual(
            sched.polling_server_response(25, 3, 2, 0.0), 2.0, delta=1e-9)

    def test_polling_phase_linearity(self):
        """Step 7 polling waits for the next poll after a missed poll
        instant: (25 - phase) + 2 is 14.5 ms at phase 12.5 and 3.0 ms at
        phase 24.0."""
        self.assertAlmostEqual(
            sched.polling_server_response(25, 3, 2, 12.5), 14.5, delta=1e-9)
        self.assertAlmostEqual(
            sched.polling_server_response(25, 3, 2, 24.0), 3.0, delta=1e-9)

    def test_deferrable_phase_independent(self):
        """Step 7 deferrable capacity preservation: 2.0 ms at every phase
        0.0, 12.5 and 24.0, serving the mid-period arrival 14.5 ms sooner
        than the polling server."""
        for phase in (0.0, 12.5, 24.0):
            self.assertAlmostEqual(
                sched.deferrable_server_response(25, 3, 2, phase), 2.0,
                delta=1e-9)

    def test_sporadic_phase_independent(self):
        """Step 7 sporadic budget never forfeited on idleness: 2.0 ms at
        every phase 0.0, 12.5 and 24.0."""
        for phase in (0.0, 12.5, 24.0):
            self.assertAlmostEqual(
                sched.sporadic_server_response(25, 3, 2, phase), 2.0,
                delta=1e-9)

    def test_single_job_response_validation_raises(self):
        """Step 7 ValueErrors: T_s 0, C_a 0, C_a above C_s, negative
        phase and phase at T_s are rejected by every response function."""
        with self.assertRaises(ValueError):
            sched.polling_server_response(0, 3, 2, 0.0)
        with self.assertRaises(ValueError):
            sched.polling_server_response(25, 3, 0, 0.0)
        with self.assertRaises(ValueError):
            sched.polling_server_response(25, 3, 4, 0.0)
        with self.assertRaises(ValueError):
            sched.polling_server_response(25, 3, 2, -0.5)
        with self.assertRaises(ValueError):
            sched.polling_server_response(25, 3, 2, 25.0)
        with self.assertRaises(ValueError):
            sched.deferrable_server_response(25, 3, 0, 0.0)
        with self.assertRaises(ValueError):
            sched.sporadic_server_response(25, 3, 2, 25.0)


class AperiodicBoundTests(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the worst-case aperiodic response
    bound of a burst, k = ceil(demand / C_s) windows of service."""

    def test_single_job_bound(self):
        """Step 6 bound of a single 2 ms job at T_s 25 is T_s + C_a,
        27.0 ms, the polling worst case approached as the phase tends to
        0 from above."""
        self.assertAlmostEqual(
            sched.aperiodic_response_bound(25, 3, 2.0), 27.0, delta=1e-9)

    def test_exact_multiple_ladder(self):
        """Step 6 burst demands 3, 6, 9 ms give 28, 53, 78 ms; each extra
        full budget of demand adds exactly one server period of 25 ms."""
        bounds = [sched.aperiodic_response_bound(25, 3, d)
                  for d in (3.0, 6.0, 9.0)]
        for got, want in zip(bounds, (28.0, 53.0, 78.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(bounds[2] - bounds[1], 25.0, delta=1e-9)

    def test_bound_monotone_and_period_scaling(self):
        """Step 6 bound 77.0 ms at demand 8 above 53.0 at demand 6, and
        halving T_s to 10 ms cuts the single-job bound to 12.0 ms."""
        self.assertAlmostEqual(
            sched.aperiodic_response_bound(25, 3, 8.0), 77.0, delta=1e-9)
        self.assertAlmostEqual(
            sched.aperiodic_response_bound(10, 3, 2.0), 12.0, delta=1e-9)

    def test_bound_invalid_raises(self):
        """Step 6 rejects non-positive demand, capacity and period."""
        with self.assertRaises(ValueError):
            sched.aperiodic_response_bound(25, 3, 0.0)
        with self.assertRaises(ValueError):
            sched.aperiodic_response_bound(25, 0, 2.0)
        with self.assertRaises(ValueError):
            sched.aperiodic_response_bound(0, 3, 2.0)


class ReplenishmentTests(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the capacity-loss wait and
    replenishment arithmetic after a full-budget consumption."""

    def test_aligned_consumption_wait(self):
        """Step 8 consumption [0, 3] aligned to a period start waits 22 ms
        for polling, deferrable and sporadic alike."""
        for kind in ("polling", "deferrable", "sporadic"):
            self.assertAlmostEqual(
                sched.replenishment_wait(kind, 25, 0, 3), 22.0, delta=1e-9)

    def test_mid_period_consumption_wait(self):
        """Step 8 consumption [17, 20]: polling and deferrable wait 5 ms
        for the next poll and period start at 25, while sporadic waits
        22 ms, T_s minus the length, independent of start."""
        self.assertAlmostEqual(
            sched.replenishment_wait("polling", 25, 17, 20), 5.0, delta=1e-9)
        self.assertAlmostEqual(
            sched.replenishment_wait("deferrable", 25, 17, 20), 5.0,
            delta=1e-9)
        self.assertAlmostEqual(
            sched.replenishment_wait("sporadic", 25, 17, 20), 22.0,
            delta=1e-9)
        self.assertAlmostEqual(
            sched.replenishment_wait("sporadic", 25, 0, 3), 22.0, delta=1e-9)

    def test_boundary_ending_consumption_wait(self):
        """Step 8 consumption [22, 25] ending exactly on the boundary:
        polling and deferrable wait 0.0, sporadic still waits 22 ms for
        its replenishment at 22 + 25 = 47."""
        self.assertAlmostEqual(
            sched.replenishment_wait("polling", 25, 22, 25), 0.0, delta=1e-9)
        self.assertAlmostEqual(
            sched.replenishment_wait("deferrable", 25, 22, 25), 0.0,
            delta=1e-9)
        self.assertAlmostEqual(
            sched.replenishment_wait("sporadic", 25, 22, 25), 22.0,
            delta=1e-9)

    def test_replenishment_validation_raises(self):
        """Step 8 ValueErrors: bad kind, negative start, end equal to
        start and a consumption longer than T_s."""
        with self.assertRaises(ValueError):
            sched.replenishment_wait("periodic", 25, 0, 3)
        with self.assertRaises(ValueError):
            sched.replenishment_wait("polling", 25, -1, 3)
        with self.assertRaises(ValueError):
            sched.replenishment_wait("deferrable", 25, 3, 3)
        with self.assertRaises(ValueError):
            sched.replenishment_wait("sporadic", 25, 0, 30)


class ResponseTimeAnalysisTests(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the response-time analysis with
    the server budget inserted at a priority slot, tasks below the
    budget gaining ceil(R_i / T_s) * C_s interference."""

    def test_srt_above_index_zero_set_a(self):
        """Step 4 slot 0, the budget above every task: server response
        3.0 ms and augmented task responses [4.0, 7.0, 10.0], each within
        its 5, 10, 25 ms implicit deadline."""
        r = sched.server_response_times(A, sched.server_parameters(0.1, 25, 0.02), 0)
        self.assertAlmostEqual(r["server_response_time"], 3.0, delta=1e-9)
        for got, want in zip(r["task_response_times"], (4.0, 7.0, 10.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertTrue(r["feasible"])
        self.assertAlmostEqual(r["total_utilization"], 0.64, delta=1e-9)

    def test_srt_above_index_bottom_is_plain_baseline(self):
        """Step 4 slot n, the budget below every task, reproduces the
        plain periodic baseline [1.0, 3.0, 7.0] with server response
        10.0 ms."""
        r = sched.server_response_times(A, sched.server_parameters(0.1, 25, 0.02),
                                        len(A))
        for got, want in zip(r["task_response_times"], (1.0, 3.0, 7.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(r["server_response_time"], 10.0, delta=1e-9)

    def test_srt_slot_scan_server_responses(self):
        """Step 4 slot scan over 0..3: the server response rises 3.0,
        4.0, 7.0, 10.0 as the insertion index moves down while the
        periodic responses fall back to the plain baseline."""
        server = sched.server_parameters(0.1, 25, 0.02)
        for idx, want in enumerate((3.0, 4.0, 7.0, 10.0)):
            r = sched.server_response_times(A, server, idx)
            self.assertAlmostEqual(r["server_response_time"], want, delta=1e-9)
        bottom = sched.server_response_times(A, server, 3)["task_response_times"]
        for got, want in zip(bottom, (1.0, 3.0, 7.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)

    def test_srt_diverged_task_returns_none(self):
        """Step 4 a diverged task reports a None entry and the slot is
        infeasible: set B budget 10 ms at slot 0 blows the 5 ms and 10 ms
        task deadlines, tasks [None, None, 24.0]."""
        server = sched.server_parameters(0.34, 25, 0.06)
        r = sched.server_response_times(A, server, 0)
        self.assertIsNone(r["task_response_times"][0])
        self.assertIsNone(r["task_response_times"][1])
        self.assertAlmostEqual(r["task_response_times"][2], 24.0, delta=1e-9)
        self.assertFalse(r["feasible"])

    def test_srt_validation_raises(self):
        """Step 4 ValueErrors: empty task list, capacity above period and
        above_index outside [0, len(tasks)] are rejected."""
        server_ok = {"capacity": 3.0, "period": 25.0}
        with self.assertRaises(ValueError):
            sched.server_response_times([], server_ok, 0)
        with self.assertRaises(ValueError):
            sched.server_response_times(A, {"capacity": 30.0, "period": 25.0}, 0)
        with self.assertRaises(ValueError):
            sched.server_response_times(A, server_ok, -1)
        with self.assertRaises(ValueError):
            sched.server_response_times(A, server_ok, len(A) + 1)


class PlacementTests(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the server placement scan, which
    returns the highest feasible insertion index or raises the
    no-feasible-slot verdict."""

    def test_place_server_set_a_top_slot(self):
        """Step 5 placement on set A with the light 0.10 event load: the
        3 ms budget fits at the top, insertion_index 0, server response
        3.0 ms and tasks closing at [4.0, 7.0, 10.0]."""
        p = sched.place_server(A, sched.server_parameters(0.1, 25, 0.02))
        self.assertEqual(p["insertion_index"], 0)
        self.assertTrue(p["feasible"])
        self.assertAlmostEqual(p["server_response_time"], 3.0, delta=1e-9)
        for got, want in zip(p["task_response_times"], (4.0, 7.0, 10.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(p["total_utilization"], 0.64, delta=1e-9)

    def test_place_server_set_b_middle_slot(self):
        """Step 5 placement on set B with the heavy 0.34 event load: the
        10 ms budget must sit below the 5 ms and 10 ms tasks,
        insertion_index 2, server response 18.0 ms, tasks [1.0, 3.0,
        24.0] and total utilization 0.92."""
        server = sched.server_parameters(0.34, 25, 0.06)
        p = sched.place_server(A, server)
        self.assertEqual(p["insertion_index"], 2)
        self.assertTrue(p["feasible"])
        self.assertAlmostEqual(p["server_response_time"], 18.0, delta=1e-9)
        for got, want in zip(p["task_response_times"], (1.0, 3.0, 24.0)):
            self.assertAlmostEqual(got, want, delta=1e-9)
        self.assertAlmostEqual(p["total_utilization"], 0.92, delta=1e-9)

    def test_place_server_set_b_low_slots_infeasible(self):
        """Step 5 slots 0 and 1 of set B are infeasible before the scan
        reaches slot 2: the heavy budget preempting the fast tasks blows
        their deadlines (None entries)."""
        server = sched.server_parameters(0.34, 25, 0.06)
        for idx in (0, 1):
            r = sched.server_response_times(A, server, idx)
            self.assertFalse(r["feasible"])
            self.assertIsNotNone(r["server_response_time"])
            self.assertIsNone(r["task_response_times"][idx])

    def test_place_server_no_slot_raises(self):
        """Step 5 no-feasible-slot verdict: u_a + margin 0.9 on set A
        (capacity 22.5 ms) leaves every one of the 4 priority slots
        infeasible, so place_server raises."""
        with self.assertRaises(ValueError) as ctx:
            sched.place_server(A, sched.server_parameters(0.9, 25, 0.0))
        self.assertIn("4 priority slots", str(ctx.exception))


class ModuleDisciplineTests(unittest.TestCase):
    """Step 9 of the SKILL.md workflow: the deterministic contract test
    run and module discipline (constant cap, imports, determinism)."""

    def test_module_constants_and_imports(self):
        """Step 9 module discipline: MAX_RTA_ITERATIONS fixed at 100 and
        the module imports nothing beyond math."""
        self.assertEqual(sched.MAX_RTA_ITERATIONS, 100)
        src = inspect.getsource(sched)
        imports = [line.strip() for line in src.splitlines()
                   if line.strip().startswith(("import ", "from "))]
        self.assertEqual(imports, ["import math"])

    def test_deterministic_outputs(self):
        """Step 9 identical outputs run to run: the placement and bound
        verdicts repeat exactly with no randomness."""
        first = sched.place_server(A, sched.server_parameters(0.1, 25, 0.02))
        second = sched.place_server(A, sched.server_parameters(0.1, 25, 0.02))
        self.assertEqual(first, second)
        self.assertEqual(sched.aperiodic_response_bound(25, 3, 8.0),
                         sched.aperiodic_response_bound(25, 3, 8.0))


if __name__ == "__main__":
    unittest.main()

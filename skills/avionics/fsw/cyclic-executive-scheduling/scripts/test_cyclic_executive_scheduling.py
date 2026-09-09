"""Contract test for cyclic-executive-scheduling.

Exercises the SKILL.md Workflow steps in order: step 2 (hyperperiod and
period gcd), step 3 (utilization), step 4 (admissible frame lengths, the
frame-fit rule), step 5 (frame loads and the capacity-feasible subset),
step 6 (the constructive frame table with jobs, load and slack), step 7
(the full cyclic_executive_report and the feasible convenience check),
and step 1 (task dict validation and ValueError rejection of malformed
task lists). Stdlib unittest, offline, deterministic, no randomness.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cyclic_executive_scheduling_logic import (
    TOL,
    admissible_frame_lengths,
    cyclic_executive_report,
    feasible,
    feasible_frame_lengths,
    frame_loads,
    frame_table,
    hyperperiod,
    max_frame_load,
    period_gcd,
    utilization,
)

SET_A = [
    {"name": "flight-control", "C": 3, "T": 25},
    {"name": "guidance", "C": 4, "T": 50},
    {"name": "health-monitor", "C": 5, "T": 100},
]
SET_B = [
    {"name": "flight-control", "C": 8, "T": 25},
    {"name": "guidance", "C": 9, "T": 50},
    {"name": "health-monitor", "C": 10, "T": 100},
]
SET_C = [
    {"name": "flight-control", "C": 3, "T": 25},
    {"name": "display", "C": 8, "T": 40},
]


class TestHyperperiodAndGcd(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: hyperperiod and period gcd."""

    def test_set_a_hyperperiod(self):
        self.assertEqual(hyperperiod(SET_A), 100)

    def test_period_gcd_of_sets_a_and_c(self):
        self.assertEqual(period_gcd(SET_A), 25)
        self.assertEqual(period_gcd(SET_C), 5)

    def test_coprime_hyperperiod_identity(self):
        coprime = [{"C": 1, "T": 3}, {"C": 1, "T": 4}, {"C": 1, "T": 5}]
        self.assertEqual(hyperperiod(coprime), 60)
        self.assertEqual(period_gcd(coprime), 1)
        self.assertEqual(hyperperiod(coprime), 3 * 4 * 5)


class TestUtilization(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the necessary-condition utilization."""

    def test_set_a_utilization(self):
        self.assertTrue(math.isclose(utilization(SET_A), 0.25, rel_tol=1e-6))

    def test_set_b_utilization(self):
        self.assertTrue(math.isclose(utilization(SET_B), 0.6, rel_tol=1e-6))

    def test_set_c_utilization(self):
        self.assertTrue(math.isclose(utilization(SET_C), 0.32, rel_tol=1e-6))


class TestAdmissibleFrameLengths(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the frame-fit rule for admissible f."""

    def test_set_a_admissible(self):
        self.assertEqual(admissible_frame_lengths(SET_A), [5, 25])

    def test_admissible_boundary_sets(self):
        self.assertEqual(admissible_frame_lengths(SET_B), [25])
        self.assertEqual(admissible_frame_lengths(SET_C), [])

    def test_every_admissible_divides_every_period(self):
        for f in admissible_frame_lengths(SET_A):
            for task in SET_A:
                self.assertEqual(task["T"] % f, 0)

    def test_single_task_min_admissible(self):
        one = [{"C": 1, "T": 6}]
        self.assertEqual(admissible_frame_lengths(one), [1, 2, 3, 6])


class TestFrameLoadsAndCapacity(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: per-frame loads and capacity feasibility."""

    def test_set_a_frame_loads_at_25(self):
        self.assertEqual(frame_loads(SET_A, 25), [12, 3, 7, 3])

    def test_set_a_capacity_check_at_5_and_25(self):
        self.assertEqual(max_frame_load(SET_A, 5), 12)
        self.assertGreater(max_frame_load(SET_A, 5), 5)
        self.assertEqual(max_frame_load(SET_A, 25), 12)
        self.assertLessEqual(max_frame_load(SET_A, 25), 25)

    def test_feasible_frame_lengths_across_sets(self):
        self.assertEqual(feasible_frame_lengths(SET_A), [25])
        self.assertEqual(feasible_frame_lengths(SET_B), [])
        self.assertEqual(feasible_frame_lengths(SET_C), [])

    def test_single_task_idle_frames(self):
        one = [{"C": 3, "T": 25}]
        loads = frame_loads(one, 5)
        self.assertEqual(loads, [3, 0, 0, 0, 0])


class TestFrameTable(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the constructive frame table."""

    def test_set_a_frame_table_rows(self):
        table = frame_table(SET_A, 25)
        row0 = table[0]
        self.assertEqual(row0["jobs"], ["flight-control", "guidance", "health-monitor"])
        self.assertEqual(row0["load"], 12)
        self.assertEqual(row0["slack"], 13)
        row2 = table[2]
        self.assertEqual(row2["jobs"], ["flight-control", "guidance"])
        self.assertEqual(row2["load"], 7)
        self.assertEqual(row2["slack"], 18)

    def test_set_a_frame_table_slacks_and_boundaries(self):
        table = frame_table(SET_A, 25)
        slacks = [row["slack"] for row in table]
        self.assertEqual(slacks, [13, 22, 18, 22])
        for j, row in enumerate(table):
            self.assertEqual(row["start_ms"], j * 25)
            self.assertEqual(row["end_ms"], (j + 1) * 25)

    def test_idle_frame_has_no_jobs_and_full_slack(self):
        one = [{"C": 3, "T": 25}]
        table = frame_table(one, 5)
        self.assertEqual(table[1]["jobs"], [])
        self.assertEqual(table[1]["slack"], 5)

    def test_hyperperiod_load_and_slack_identities(self):
        table = frame_table(SET_A, 25)
        total_load = sum(row["load"] for row in table)
        total_slack = sum(row["slack"] for row in table)
        total_jobs = sum(len(row["jobs"]) for row in table)
        expected_load = sum(task["C"] * (hyperperiod(SET_A) // task["T"]) for task in SET_A)
        expected_jobs = sum(hyperperiod(SET_A) // task["T"] for task in SET_A)
        self.assertEqual(total_load, expected_load)
        self.assertEqual(total_load, 25)
        self.assertTrue(math.isclose(hyperperiod(SET_A) * utilization(SET_A), total_load, abs_tol=1e-9))
        self.assertEqual(total_jobs, 7)
        self.assertEqual(total_jobs, expected_jobs)
        self.assertEqual(total_slack, 75)
        self.assertEqual(total_slack, len(table) * 25 - total_load)


class TestReportAndFeasible(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the full report and the feasible check."""

    def test_set_a_report_fields(self):
        report = cyclic_executive_report(SET_A)
        self.assertEqual(report["hyperperiod"], 100)
        self.assertEqual(report["period_gcd"], 25)
        self.assertEqual(report["max_execution_time"], 5)
        self.assertTrue(math.isclose(report["utilization"], 0.25, rel_tol=1e-6))
        self.assertEqual(report["admissible_frame_lengths"], [5, 25])
        self.assertEqual(report["feasible_frame_lengths"], [25])
        self.assertEqual(report["verdict"], "FITS")
        self.assertIsNone(report["reject_reason"])
        self.assertEqual(report["frame_length"], 25)
        self.assertEqual(report["frame_count"], 4)
        self.assertEqual(report["max_frame_load"], 12)
        self.assertEqual(report["min_slack"], 13)
        self.assertIsNotNone(report["frame_table"])

    def test_set_b_report_capacity_rejection_necessary_not_sufficient(self):
        report = cyclic_executive_report(SET_B)
        self.assertEqual(report["admissible_frame_lengths"], [25])
        self.assertEqual(report["feasible_frame_lengths"], [])
        self.assertEqual(report["verdict"], "no-admissible-frame")
        self.assertEqual(report["reject_reason"], "capacity")
        self.assertIsNone(report["frame_length"])
        self.assertIsNone(report["frame_count"])
        self.assertIsNone(report["max_frame_load"])
        self.assertIsNone(report["min_slack"])
        self.assertIsNone(report["frame_table"])
        self.assertLessEqual(report["utilization"], 1.0)

    def test_set_c_report_frame_fit_rejection(self):
        report = cyclic_executive_report(SET_C)
        self.assertEqual(report["period_gcd"], 5)
        self.assertEqual(report["max_execution_time"], 8)
        self.assertEqual(report["admissible_frame_lengths"], [])
        self.assertEqual(report["verdict"], "no-admissible-frame")
        self.assertEqual(report["reject_reason"], "frame-fit")

    def test_feasible_reduction_and_determinism(self):
        self.assertTrue(feasible(SET_A))
        self.assertFalse(feasible(SET_B))
        self.assertFalse(feasible(SET_C))
        report1 = cyclic_executive_report(SET_A)
        report2 = cyclic_executive_report(SET_A)
        self.assertEqual(report1, report2)

    def test_tol_constant(self):
        self.assertAlmostEqual(TOL, 1e-12, delta=1e-20)


class TestValueErrors(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: task dict validation and rejection."""

    def test_empty_list(self):
        with self.assertRaises(ValueError):
            hyperperiod([])

    def test_non_dict_entry(self):
        with self.assertRaises(ValueError):
            hyperperiod([1, 2])

    def test_missing_key(self):
        with self.assertRaises(ValueError):
            hyperperiod([{"C": 1}])

    def test_invalid_c_values(self):
        for bad in ({"C": True, "T": 5}, {"C": 1.5, "T": 5}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    hyperperiod([bad])

    def test_invalid_t_values(self):
        for bad in ({"C": 1, "T": 0}, {"C": 1, "T": -5}):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    hyperperiod([bad])

    def test_frame_length_not_dividing_period(self):
        with self.assertRaises(ValueError):
            frame_loads([{"C": 1, "T": 25}], 7)

    def test_invalid_frame_length(self):
        for bad_f in (0, 2.5):
            with self.subTest(bad_f=bad_f):
                with self.assertRaises(ValueError):
                    frame_loads([{"C": 1, "T": 25}], bad_f)

    def test_all_functions_validate_empty(self):
        for fn in (
            period_gcd,
            utilization,
            admissible_frame_lengths,
            feasible_frame_lengths,
            cyclic_executive_report,
            feasible,
        ):
            with self.assertRaises(ValueError):
                fn([])


if __name__ == "__main__":
    unittest.main()

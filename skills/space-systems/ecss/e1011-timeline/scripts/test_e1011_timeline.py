"""
Gate 3 contract tests for e1011-timeline.
stdlib unittest, deterministic, offline.  Run: python3 test_e1011_timeline.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1011_timeline_logic import (
    TimelineEntry,
    ValidationResult,
    validate_entry,
    compute_workload_index,
    check_workload_constraints,
    check_concurrent_tasks,
    check_rest_periods,
    validate_timeline,
    WORKLOAD_LEVEL_LOW,
    WORKLOAD_LEVEL_MEDIUM,
    WORKLOAD_LEVEL_HIGH,
    MAX_WORKLOAD_INDEX,
    MAX_CONCURRENT_TASKS,
    MIN_REST_DURATION_MINUTES,
    HIGH_DEMAND_CLUSTER_THRESHOLD,
)


def _entry(task_id, start, duration, level=WORKLOAD_LEVEL_LOW, crew=1):
    return TimelineEntry(
        task_id=task_id,
        description="test task",
        start_minute=start,
        duration_minutes=duration,
        workload_level=level,
        crew_count=crew,
    )


# ---------------------------------------------------------------------------
# Entry structural validation
# ---------------------------------------------------------------------------

class TestValidateEntry(unittest.TestCase):

    def test_valid_entry_passes(self):
        e = _entry("T1", 0, 60, WORKLOAD_LEVEL_MEDIUM)
        r = validate_entry(e)
        self.assertTrue(r.passed)
        self.assertEqual(r.findings, [])

    def test_zero_duration_fails(self):
        e = _entry("T1", 0, 0)
        r = validate_entry(e)
        self.assertFalse(r.passed)
        self.assertTrue(any("duration" in f for f in r.findings))

    def test_negative_duration_fails(self):
        e = _entry("T1", 0, -10)
        r = validate_entry(e)
        self.assertFalse(r.passed)

    def test_negative_start_fails(self):
        e = _entry("T1", -1, 60)
        r = validate_entry(e)
        self.assertFalse(r.passed)
        self.assertTrue(any("start_minute" in f for f in r.findings))

    def test_unknown_workload_level_fails(self):
        e = _entry("T1", 0, 60, "extreme")
        r = validate_entry(e)
        self.assertFalse(r.passed)
        self.assertTrue(any("workload_level" in f for f in r.findings))

    def test_zero_crew_count_fails(self):
        e = TimelineEntry("T1", "x", 0, 60, WORKLOAD_LEVEL_LOW, crew_count=0)
        r = validate_entry(e)
        self.assertFalse(r.passed)
        self.assertTrue(any("crew_count" in f for f in r.findings))


# ---------------------------------------------------------------------------
# Workload index computation
# ---------------------------------------------------------------------------

class TestComputeWorkloadIndex(unittest.TestCase):

    def test_single_high_task_full_window(self):
        entries = [_entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH)]
        self.assertAlmostEqual(compute_workload_index(entries, 0, 60), 3.0)

    def test_single_low_task_full_window(self):
        entries = [_entry("T1", 0, 60, WORKLOAD_LEVEL_LOW)]
        self.assertAlmostEqual(compute_workload_index(entries, 0, 60), 1.0)

    def test_partial_overlap_half_window(self):
        # High task occupies first 30 min of a 60-min window → 3 * 30/60 = 1.5
        entries = [_entry("T1", 0, 30, WORKLOAD_LEVEL_HIGH)]
        self.assertAlmostEqual(compute_workload_index(entries, 0, 60), 1.5)

    def test_no_overlap_returns_zero(self):
        entries = [_entry("T1", 120, 60, WORKLOAD_LEVEL_HIGH)]
        self.assertAlmostEqual(compute_workload_index(entries, 0, 60), 0.0)

    def test_two_concurrent_medium_tasks(self):
        # 2 * 2 * 60 / 60 = 4.0
        entries = [
            _entry("T1", 0, 60, WORKLOAD_LEVEL_MEDIUM),
            _entry("T2", 0, 60, WORKLOAD_LEVEL_MEDIUM),
        ]
        self.assertAlmostEqual(compute_workload_index(entries, 0, 60), 4.0)

    def test_invalid_window_raises_value_error(self):
        entries = [_entry("T1", 0, 60)]
        with self.assertRaises(ValueError):
            compute_workload_index(entries, 0, 0)

    def test_entry_overlapping_window_boundary(self):
        # Task starts at minute 30, duration 60 → occupies [30, 90]
        # Window [0, 60]: overlap = [30, 60] = 30 min; high → 3 * 30/60 = 1.5
        entries = [_entry("T1", 30, 60, WORKLOAD_LEVEL_HIGH)]
        self.assertAlmostEqual(compute_workload_index(entries, 0, 60), 1.5)


# ---------------------------------------------------------------------------
# Workload constraint checks
# ---------------------------------------------------------------------------

class TestCheckWorkloadConstraints(unittest.TestCase):

    def test_empty_timeline_passes(self):
        r = check_workload_constraints([])
        self.assertTrue(r.passed)

    def test_single_high_task_at_limit_passes(self):
        # index = 3.0 == MAX_WORKLOAD_INDEX (not strictly greater) → passes
        entries = [_entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH)]
        r = check_workload_constraints(entries)
        self.assertTrue(r.passed)

    def test_two_concurrent_high_tasks_fails(self):
        # index = 6.0 > 3.0 → violation
        entries = [
            _entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH),
            _entry("T2", 0, 60, WORKLOAD_LEVEL_HIGH),
        ]
        r = check_workload_constraints(entries)
        self.assertFalse(r.passed)
        self.assertGreater(len(r.findings), 0)

    def test_sequential_high_tasks_pass(self):
        entries = [
            _entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH),
            _entry("T2", 60, 60, WORKLOAD_LEVEL_HIGH),
        ]
        r = check_workload_constraints(entries)
        self.assertTrue(r.passed)


# ---------------------------------------------------------------------------
# Concurrent task checks
# ---------------------------------------------------------------------------

class TestCheckConcurrentTasks(unittest.TestCase):

    def test_empty_timeline_passes(self):
        r = check_concurrent_tasks([])
        self.assertTrue(r.passed)

    def test_at_concurrent_limit_passes(self):
        entries = [
            _entry("T1", 0, 60),
            _entry("T2", 0, 60),
            _entry("T3", 0, 60),
        ]
        r = check_concurrent_tasks(entries)
        self.assertTrue(r.passed)

    def test_exceeds_concurrent_limit_fails(self):
        entries = [
            _entry("T1", 0, 60),
            _entry("T2", 0, 60),
            _entry("T3", 0, 60),
            _entry("T4", 0, 60),  # 4th simultaneous task violates limit of 3
        ]
        r = check_concurrent_tasks(entries)
        self.assertFalse(r.passed)
        self.assertGreater(len(r.findings), 0)

    def test_sequential_tasks_always_pass(self):
        entries = [
            _entry("T1", 0, 60),
            _entry("T2", 60, 60),
            _entry("T3", 120, 60),
            _entry("T4", 180, 60),
        ]
        r = check_concurrent_tasks(entries)
        self.assertTrue(r.passed)

    def test_end_and_start_same_minute_not_concurrent(self):
        # T1 ends at minute 60; T4 starts at minute 60 → should not be concurrent
        entries = [
            _entry("T1", 0, 60),
            _entry("T2", 0, 60),
            _entry("T3", 0, 60),
            _entry("T4", 60, 60),  # replaces the group, must not trigger violation
        ]
        r = check_concurrent_tasks(entries)
        self.assertTrue(r.passed)


# ---------------------------------------------------------------------------
# Rest period checks
# ---------------------------------------------------------------------------

class TestCheckRestPeriods(unittest.TestCase):

    def test_empty_timeline_passes(self):
        r = check_rest_periods([])
        self.assertTrue(r.passed)

    def test_no_high_demand_windows_passes(self):
        entries = [_entry("T1", 0, 60, WORKLOAD_LEVEL_LOW)]
        r = check_rest_periods(entries)
        self.assertTrue(r.passed)

    def test_adequate_rest_between_clusters_passes(self):
        # Cluster 1: high task 0-60 min (index 3.0 > 2.5 threshold)
        # Gap: 60-540 min = 480 min == MIN_REST_DURATION_MINUTES → passes
        # Cluster 2: high task 540-600 min
        entries = [
            _entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH),
            _entry("T2", 540, 60, WORKLOAD_LEVEL_HIGH),
        ]
        r = check_rest_periods(entries)
        self.assertTrue(r.passed)

    def test_insufficient_rest_between_clusters_fails(self):
        # Cluster 1: high task 0-60 min
        # Gap: 60-120 min = 60 min << 480 min minimum → violation
        # Cluster 2: high task 120-180 min
        entries = [
            _entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH),
            _entry("T2", 120, 60, WORKLOAD_LEVEL_HIGH),
        ]
        r = check_rest_periods(entries)
        self.assertFalse(r.passed)
        self.assertGreater(len(r.findings), 0)

    def test_single_high_demand_cluster_passes(self):
        # Only one cluster → no gap to measure → passes
        entries = [_entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH)]
        r = check_rest_periods(entries)
        self.assertTrue(r.passed)


# ---------------------------------------------------------------------------
# Full timeline validation
# ---------------------------------------------------------------------------

class TestValidateTimeline(unittest.TestCase):

    def test_empty_timeline_passes(self):
        r = validate_timeline([])
        self.assertTrue(r.passed)
        self.assertEqual(r.findings, [])

    def test_valid_mixed_timeline_passes(self):
        entries = [
            _entry("T1", 0, 30, WORKLOAD_LEVEL_LOW),
            _entry("T2", 30, 30, WORKLOAD_LEVEL_MEDIUM),
            _entry("T3", 60, 60, WORKLOAD_LEVEL_LOW),
        ]
        r = validate_timeline(entries)
        self.assertTrue(r.passed)

    def test_structural_error_short_circuits(self):
        # Negative duration → structural error stops further checks
        entries = [_entry("T1", 0, -5, WORKLOAD_LEVEL_LOW)]
        r = validate_timeline(entries)
        self.assertFalse(r.passed)
        self.assertGreater(len(r.findings), 0)

    def test_workload_violation_surfaces_in_full_validation(self):
        entries = [
            _entry("T1", 0, 60, WORKLOAD_LEVEL_HIGH),
            _entry("T2", 0, 60, WORKLOAD_LEVEL_HIGH),
        ]
        r = validate_timeline(entries)
        self.assertFalse(r.passed)


if __name__ == "__main__":
    unittest.main()

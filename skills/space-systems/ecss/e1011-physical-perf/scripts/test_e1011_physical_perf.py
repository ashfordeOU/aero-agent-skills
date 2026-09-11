import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1011_physical_perf_logic import (
    WorkloadCategory,
    categorize_workload,
    continuous_duration_limit,
    required_recovery,
    check_work_bout,
    check_schedule,
)


class TestCategorizeWorkload(unittest.TestCase):

    def test_rest_zero(self):
        self.assertEqual(categorize_workload(0), WorkloadCategory.REST)

    def test_rest_upper_boundary(self):
        self.assertEqual(categorize_workload(64), WorkloadCategory.REST)

    def test_light_at_lower_boundary(self):
        self.assertEqual(categorize_workload(65), WorkloadCategory.LIGHT)

    def test_light_mid(self):
        self.assertEqual(categorize_workload(120), WorkloadCategory.LIGHT)

    def test_moderate(self):
        self.assertEqual(categorize_workload(200), WorkloadCategory.MODERATE)

    def test_heavy(self):
        self.assertEqual(categorize_workload(350), WorkloadCategory.HEAVY)

    def test_very_heavy(self):
        self.assertEqual(categorize_workload(500), WorkloadCategory.VERY_HEAVY)

    def test_very_heavy_at_threshold(self):
        self.assertEqual(categorize_workload(415), WorkloadCategory.VERY_HEAVY)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            categorize_workload(-1)


class TestContinuousDurationLimit(unittest.TestCase):

    def test_light_limit(self):
        self.assertEqual(continuous_duration_limit(WorkloadCategory.LIGHT), 480)

    def test_moderate_limit(self):
        self.assertEqual(continuous_duration_limit(WorkloadCategory.MODERATE), 120)

    def test_heavy_limit(self):
        self.assertEqual(continuous_duration_limit(WorkloadCategory.HEAVY), 45)

    def test_very_heavy_limit(self):
        self.assertEqual(continuous_duration_limit(WorkloadCategory.VERY_HEAVY), 20)


class TestRequiredRecovery(unittest.TestCase):

    def test_rest_no_recovery(self):
        self.assertEqual(required_recovery(WorkloadCategory.REST, 60), 0.0)

    def test_light_recovery(self):
        self.assertAlmostEqual(required_recovery(WorkloadCategory.LIGHT, 60), 15.0)

    def test_moderate_recovery(self):
        self.assertAlmostEqual(required_recovery(WorkloadCategory.MODERATE, 60), 30.0)

    def test_heavy_recovery_scales_with_duration(self):
        self.assertAlmostEqual(required_recovery(WorkloadCategory.HEAVY, 30), 30.0)
        self.assertAlmostEqual(required_recovery(WorkloadCategory.HEAVY, 45), 45.0)

    def test_very_heavy_recovery(self):
        self.assertAlmostEqual(required_recovery(WorkloadCategory.VERY_HEAVY, 20), 40.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            required_recovery(WorkloadCategory.LIGHT, -5)


class TestCheckWorkBout(unittest.TestCase):

    def test_moderate_within_limit_passes(self):
        r = check_work_bout(200, 90)
        self.assertTrue(r.compliant)
        self.assertEqual(r.category, WorkloadCategory.MODERATE)

    def test_moderate_exceeds_limit_fails(self):
        r = check_work_bout(200, 150)
        self.assertFalse(r.compliant)
        self.assertEqual(len(r.violations), 1)

    def test_heavy_at_limit_passes(self):
        r = check_work_bout(350, 45)
        self.assertTrue(r.compliant)

    def test_very_heavy_exceeds_limit_fails(self):
        r = check_work_bout(500, 25)
        self.assertFalse(r.compliant)

    def test_required_recovery_in_result(self):
        r = check_work_bout(350, 30)
        self.assertAlmostEqual(r.required_recovery_min, 30.0)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            check_work_bout(-10, 30)

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            check_work_bout(200, 0)

    def test_light_long_bout_passes(self):
        r = check_work_bout(100, 480)
        self.assertTrue(r.compliant)

    def test_light_over_limit_fails(self):
        r = check_work_bout(100, 481)
        self.assertFalse(r.compliant)


class TestCheckSchedule(unittest.TestCase):

    def test_valid_simple_schedule_passes(self):
        schedule = [
            {"type": "work", "metabolic_rate_w": 200, "duration_min": 90},
            {"type": "rest", "metabolic_rate_w": 20,  "duration_min": 45},
            {"type": "work", "metabolic_rate_w": 200, "duration_min": 90},
        ]
        r = check_schedule(schedule)
        self.assertTrue(r.compliant)

    def test_insufficient_recovery_fails(self):
        schedule = [
            {"type": "work", "metabolic_rate_w": 350, "duration_min": 30},
            {"type": "rest", "metabolic_rate_w": 20,  "duration_min": 5},
            {"type": "work", "metabolic_rate_w": 350, "duration_min": 30},
        ]
        r = check_schedule(schedule)
        self.assertFalse(r.compliant)

    def test_daily_moderate_limit_exceeded(self):
        # 3 × 90 min = 270 min > 240 min daily MODERATE cap
        schedule = [
            {"type": "work", "metabolic_rate_w": 200, "duration_min": 90},
            {"type": "rest", "metabolic_rate_w": 20,  "duration_min": 60},
            {"type": "work", "metabolic_rate_w": 200, "duration_min": 90},
            {"type": "rest", "metabolic_rate_w": 20,  "duration_min": 60},
            {"type": "work", "metabolic_rate_w": 200, "duration_min": 90},
        ]
        r = check_schedule(schedule)
        self.assertFalse(r.compliant)
        self.assertTrue(any("MODERATE" in v for v in r.violations))

    def test_daily_totals_returned(self):
        schedule = [
            {"type": "work", "metabolic_rate_w": 200, "duration_min": 60},
        ]
        r = check_schedule(schedule)
        self.assertAlmostEqual(r.daily_totals["MODERATE"], 60.0)

    def test_rest_only_schedule_passes(self):
        schedule = [
            {"type": "rest", "metabolic_rate_w": 20, "duration_min": 480},
        ]
        r = check_schedule(schedule)
        self.assertTrue(r.compliant)

    def test_empty_schedule_raises(self):
        with self.assertRaises(ValueError):
            check_schedule([])

    def test_invalid_segment_type_raises(self):
        with self.assertRaises(ValueError):
            check_schedule([{"type": "break", "metabolic_rate_w": 100, "duration_min": 30}])

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            check_schedule([{"type": "work", "metabolic_rate_w": 200, "duration_min": -10}])

    def test_exact_recovery_boundary_passes(self):
        # HEAVY 30 min needs exactly 30 min recovery; give exactly 30
        schedule = [
            {"type": "work", "metabolic_rate_w": 350, "duration_min": 30},
            {"type": "rest", "metabolic_rate_w": 20,  "duration_min": 30},
            {"type": "work", "metabolic_rate_w": 350, "duration_min": 30},
        ]
        r = check_schedule(schedule)
        self.assertTrue(r.compliant)

    def test_split_rest_accumulates(self):
        # Two rest segments totalling 30 min satisfy a 30 min recovery need
        schedule = [
            {"type": "work", "metabolic_rate_w": 350, "duration_min": 30},
            {"type": "rest", "metabolic_rate_w": 20,  "duration_min": 15},
            {"type": "rest", "metabolic_rate_w": 10,  "duration_min": 15},
            {"type": "work", "metabolic_rate_w": 350, "duration_min": 30},
        ]
        r = check_schedule(schedule)
        self.assertTrue(r.compliant)


if __name__ == "__main__":
    unittest.main()

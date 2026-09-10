#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-03C clause 5.5.4 equipment
thermal tests.

Exercises scripts/e1003_eq_thermal_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - test type is
thermal_vacuum only when the unit is vacuum-exposed, otherwise
thermal_at_mission_pressure; a plateau is stable only once a
contiguous run of readings covers the full required dwell window
within tolerance, not merely on first touching the target;
functional/performance verification is mandatory at the first and
last cycle and its absence blocks completion even when the plateau is
thermally stable; the overall test verdict requires the right test
type, the full required cycle count, and every cycle complete.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1003_eq_thermal_logic as th  # noqa: E402


class SelectTestTypeTest(unittest.TestCase):
    def test_vacuum_exposed_is_thermal_vacuum(self):
        self.assertEqual(th.select_test_type(True), "thermal_vacuum")

    def test_not_vacuum_exposed_is_mission_pressure(self):
        self.assertEqual(th.select_test_type(False), "thermal_at_mission_pressure")


class BuildCyclePlanTest(unittest.TestCase):
    def test_valid_plan(self):
        plan = th.build_cycle_plan("qualification", 60, -20, 3, 4, 4)
        self.assertEqual(plan["campaign"], "qualification")
        self.assertEqual(plan["num_cycles"], 4)

    def test_unknown_campaign_raises(self):
        with self.assertRaises(ValueError):
            th.build_cycle_plan("burn-in", 60, -20, 3, 4, 4)

    def test_hot_not_above_cold_raises(self):
        with self.assertRaises(ValueError):
            th.build_cycle_plan("acceptance", 10, 10, 3, 4, 4)

    def test_non_positive_tolerance_raises(self):
        with self.assertRaises(ValueError):
            th.build_cycle_plan("acceptance", 60, -20, 0, 4, 4)

    def test_non_positive_dwell_raises(self):
        with self.assertRaises(ValueError):
            th.build_cycle_plan("acceptance", 60, -20, 3, 0, 4)

    def test_zero_cycles_raises(self):
        with self.assertRaises(ValueError):
            th.build_cycle_plan("acceptance", 60, -20, 3, 4, 0)


class FindStableWindowTest(unittest.TestCase):
    def test_finds_first_run_meeting_required_length(self):
        readings = [30, 30, 61, 60, 59, 60, 60]
        # target 60, tolerance 2, need 3 in a row -> indices 2,3,4 (61,60,59) ok
        self.assertEqual(th.find_stable_window(readings, 60, 2, 3), 2)

    def test_touching_target_once_is_not_enough(self):
        readings = [30, 60, 30, 30]
        self.assertIsNone(th.find_stable_window(readings, 60, 1, 2))

    def test_run_broken_by_out_of_tolerance_reading_restarts_count(self):
        readings = [60, 60, 30, 60, 60, 60]
        self.assertEqual(th.find_stable_window(readings, 60, 1, 3), 3)

    def test_no_run_returns_none(self):
        readings = [10, 20, 30]
        self.assertIsNone(th.find_stable_window(readings, 60, 1, 2))

    def test_non_positive_required_samples_raises(self):
        with self.assertRaises(ValueError):
            th.find_stable_window([60, 60], 60, 1, 0)


class PlateauStableTest(unittest.TestCase):
    def test_true_when_window_found(self):
        self.assertTrue(th.plateau_stable([60, 60, 60], 60, 1, 3))

    def test_false_when_no_window(self):
        self.assertFalse(th.plateau_stable([60, 30, 60], 60, 1, 2))


class FunctionalCheckRequiredTest(unittest.TestCase):
    def test_first_cycle_required(self):
        self.assertTrue(th.functional_check_required(0, 4))

    def test_last_cycle_required(self):
        self.assertTrue(th.functional_check_required(3, 4))

    def test_middle_cycle_not_required(self):
        self.assertFalse(th.functional_check_required(1, 4))

    def test_single_cycle_plan_first_is_last(self):
        self.assertTrue(th.functional_check_required(0, 1))

    def test_out_of_range_index_raises(self):
        with self.assertRaises(ValueError):
            th.functional_check_required(4, 4)

    def test_zero_num_cycles_raises(self):
        with self.assertRaises(ValueError):
            th.functional_check_required(0, 0)


class EvaluateCycleTest(unittest.TestCase):
    def setUp(self):
        self.plan = th.build_cycle_plan("acceptance", 60, -20, 2, 4, 3)

    def test_first_cycle_complete_with_stable_plateaus_and_functional_pass(self):
        result = th.evaluate_cycle(
            self.plan, 0,
            cold_readings=[-20, -20, -20],
            hot_readings=[60, 60, 60],
            required_samples=3,
            functional_hot_passed=True,
            functional_cold_passed=True,
        )
        self.assertTrue(result["functional_required"])
        self.assertTrue(result["complete"])

    def test_first_cycle_incomplete_when_functional_missing(self):
        result = th.evaluate_cycle(
            self.plan, 0,
            cold_readings=[-20, -20, -20],
            hot_readings=[60, 60, 60],
            required_samples=3,
            functional_hot_passed=None,
            functional_cold_passed=None,
        )
        self.assertFalse(result["complete"])

    def test_middle_cycle_complete_without_functional_data(self):
        result = th.evaluate_cycle(
            self.plan, 1,
            cold_readings=[-20, -20, -20],
            hot_readings=[60, 60, 60],
            required_samples=3,
        )
        self.assertFalse(result["functional_required"])
        self.assertTrue(result["complete"])

    def test_incomplete_when_plateau_not_stable(self):
        result = th.evaluate_cycle(
            self.plan, 1,
            cold_readings=[-20, 0, -20],
            hot_readings=[60, 60, 60],
            required_samples=3,
        )
        self.assertFalse(result["cold_stable"])
        self.assertFalse(result["complete"])


class EvaluateThermalTestTest(unittest.TestCase):
    def setUp(self):
        self.plan = th.build_cycle_plan("acceptance", 60, -20, 2, 4, 2)

    def _complete_cycle(self, index):
        return th.evaluate_cycle(
            self.plan, index,
            cold_readings=[-20, -20, -20],
            hot_readings=[60, 60, 60],
            required_samples=3,
            functional_hot_passed=True,
            functional_cold_passed=True,
        )

    def test_passes_with_matching_type_full_cycles_and_all_complete(self):
        cycles = [self._complete_cycle(0), self._complete_cycle(1)]
        verdict = th.evaluate_thermal_test(False, "thermal_at_mission_pressure", self.plan, cycles)
        self.assertEqual(verdict["test_type"], "thermal_at_mission_pressure")
        self.assertTrue(verdict["type_ok"])
        self.assertTrue(verdict["count_ok"])
        self.assertEqual(verdict["incomplete_cycles"], [])
        self.assertTrue(verdict["passed"])

    def test_fails_on_test_type_mismatch(self):
        cycles = [self._complete_cycle(0), self._complete_cycle(1)]
        verdict = th.evaluate_thermal_test(True, "thermal_at_mission_pressure", self.plan, cycles)
        self.assertFalse(verdict["type_ok"])
        self.assertFalse(verdict["passed"])

    def test_fails_on_missing_cycle_count(self):
        cycles = [self._complete_cycle(0)]
        verdict = th.evaluate_thermal_test(False, "thermal_at_mission_pressure", self.plan, cycles)
        self.assertFalse(verdict["count_ok"])
        self.assertFalse(verdict["passed"])

    def test_fails_and_lists_incomplete_cycle(self):
        incomplete_last = th.evaluate_cycle(
            self.plan, 1,
            cold_readings=[-20, -20, -20],
            hot_readings=[60, 60, 60],
            required_samples=3,
            functional_hot_passed=False,
            functional_cold_passed=True,
        )
        cycles = [self._complete_cycle(0), incomplete_last]
        verdict = th.evaluate_thermal_test(False, "thermal_at_mission_pressure", self.plan, cycles)
        self.assertEqual(verdict["incomplete_cycles"], [1])
        self.assertFalse(verdict["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

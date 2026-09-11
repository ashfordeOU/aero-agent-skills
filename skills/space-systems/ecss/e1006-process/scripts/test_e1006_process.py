#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5 TS establishment process.

Exercises scripts/e1006_process_logic.py (stdlib unittest, offline).
Contract: all ten task IDs (F1.1–F1.10) are recognized; unknown IDs
raise ValueError; phase_0 contains F1.1–F1.4 and phase_a contains
F1.5–F1.10; F1.1 has no prerequisites, each downstream task requires
its predecessor(s), and F1.9 requires all of F1.6, F1.7, and F1.8;
prerequisites_met returns True only when all prerequisites are in the
completed set; blocking_tasks returns only the outstanding ones;
phase_complete returns True only when every task in the phase is done
and raises on an unknown phase name; iteration_complete is True at zero
open changes and raises on a negative count; ts_establishment_status
aggregates all checks and sets overall_ready only when both phases are
done and every decomposition level has converged.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1006_process_logic as pr  # noqa: E402


class TaskValidationTest(unittest.TestCase):
    def test_all_ten_tasks_recognized(self):
        for tid in ["F1.1", "F1.2", "F1.3", "F1.4", "F1.5",
                    "F1.6", "F1.7", "F1.8", "F1.9", "F1.10"]:
            pr.validate_task_id(tid)  # must not raise

    def test_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            pr.validate_task_id("F1.99")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            pr.validate_task_id("")


class TaskPhaseTest(unittest.TestCase):
    def test_f1_1_is_phase_0(self):
        self.assertEqual(pr.task_phase("F1.1"), pr.PHASE_0)

    def test_f1_4_is_phase_0(self):
        self.assertEqual(pr.task_phase("F1.4"), pr.PHASE_0)

    def test_f1_5_is_phase_a(self):
        self.assertEqual(pr.task_phase("F1.5"), pr.PHASE_A)

    def test_f1_10_is_phase_a(self):
        self.assertEqual(pr.task_phase("F1.10"), pr.PHASE_A)

    def test_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            pr.task_phase("F2.1")


class TaskPrerequisitesTest(unittest.TestCase):
    def test_f1_1_has_no_prerequisites(self):
        self.assertEqual(pr.task_prerequisites("F1.1"), [])

    def test_f1_2_requires_f1_1(self):
        self.assertIn("F1.1", pr.task_prerequisites("F1.2"))

    def test_f1_5_requires_f1_4(self):
        self.assertIn("F1.4", pr.task_prerequisites("F1.5"))

    def test_f1_9_requires_f1_6_f1_7_f1_8(self):
        prereqs = pr.task_prerequisites("F1.9")
        self.assertIn("F1.6", prereqs)
        self.assertIn("F1.7", prereqs)
        self.assertIn("F1.8", prereqs)

    def test_f1_10_requires_f1_9(self):
        self.assertIn("F1.9", pr.task_prerequisites("F1.10"))


class PrerequisitesMetTest(unittest.TestCase):
    def test_f1_1_always_ready_with_empty_completed(self):
        self.assertTrue(pr.prerequisites_met("F1.1", []))

    def test_f1_2_ready_when_f1_1_complete(self):
        self.assertTrue(pr.prerequisites_met("F1.2", ["F1.1"]))

    def test_f1_2_not_ready_when_f1_1_missing(self):
        self.assertFalse(pr.prerequisites_met("F1.2", []))

    def test_f1_9_ready_when_all_three_prereqs_complete(self):
        self.assertTrue(pr.prerequisites_met("F1.9", ["F1.6", "F1.7", "F1.8"]))

    def test_f1_9_not_ready_when_only_f1_6_complete(self):
        self.assertFalse(pr.prerequisites_met("F1.9", ["F1.6"]))


class BlockingTasksTest(unittest.TestCase):
    def test_no_blockers_for_f1_1(self):
        self.assertEqual(pr.blocking_tasks("F1.1", []), [])

    def test_f1_3_blocked_when_f1_2_missing(self):
        blockers = pr.blocking_tasks("F1.3", ["F1.1"])
        self.assertIn("F1.2", blockers)

    def test_f1_3_not_blocked_when_f1_2_complete(self):
        self.assertEqual(pr.blocking_tasks("F1.3", ["F1.1", "F1.2"]), [])

    def test_f1_9_lists_only_missing_prereqs(self):
        # F1.6 done; F1.7 and F1.8 still outstanding
        blockers = pr.blocking_tasks("F1.9", ["F1.6"])
        self.assertIn("F1.7", blockers)
        self.assertIn("F1.8", blockers)
        self.assertNotIn("F1.6", blockers)


class PhaseCompleteTest(unittest.TestCase):
    def test_phase_0_complete_when_all_four_done(self):
        self.assertTrue(pr.phase_complete(pr.PHASE_0, ["F1.1", "F1.2", "F1.3", "F1.4"]))

    def test_phase_0_incomplete_when_f1_4_missing(self):
        self.assertFalse(pr.phase_complete(pr.PHASE_0, ["F1.1", "F1.2", "F1.3"]))

    def test_phase_a_complete_when_all_six_done(self):
        self.assertTrue(
            pr.phase_complete(pr.PHASE_A, ["F1.5", "F1.6", "F1.7", "F1.8", "F1.9", "F1.10"])
        )

    def test_phase_a_incomplete_when_f1_10_missing(self):
        self.assertFalse(
            pr.phase_complete(pr.PHASE_A, ["F1.5", "F1.6", "F1.7", "F1.8", "F1.9"])
        )

    def test_unknown_phase_name_raises(self):
        with self.assertRaises(ValueError):
            pr.phase_complete("phase_b", [])


class IterationCompleteTest(unittest.TestCase):
    def test_zero_open_changes_is_complete(self):
        self.assertTrue(pr.iteration_complete(0))

    def test_nonzero_open_changes_is_not_complete(self):
        self.assertFalse(pr.iteration_complete(3))

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            pr.iteration_complete(-1)


class TsEstablishmentStatusTest(unittest.TestCase):
    _ALL = [
        "F1.1", "F1.2", "F1.3", "F1.4",
        "F1.5", "F1.6", "F1.7", "F1.8", "F1.9", "F1.10",
    ]

    def test_overall_ready_when_all_complete_and_all_levels_converged(self):
        status = pr.ts_establishment_status(self._ALL, {"L1": 0, "L2": 0})
        self.assertTrue(status["overall_ready"])
        self.assertTrue(status["phase_0_complete"])
        self.assertTrue(status["phase_a_complete"])
        self.assertTrue(status["all_levels_converged"])
        self.assertEqual(status["unconverged_levels"], [])
        self.assertEqual(status["missing_tasks"], [])

    def test_not_ready_when_phase_a_incomplete(self):
        completed = ["F1.1", "F1.2", "F1.3", "F1.4"]
        status = pr.ts_establishment_status(completed, {"L1": 0})
        self.assertFalse(status["overall_ready"])
        self.assertTrue(status["phase_0_complete"])
        self.assertFalse(status["phase_a_complete"])

    def test_not_ready_when_level_not_converged(self):
        status = pr.ts_establishment_status(self._ALL, {"L1": 2, "L2": 0})
        self.assertFalse(status["overall_ready"])
        self.assertFalse(status["all_levels_converged"])
        self.assertIn("L1", status["unconverged_levels"])
        self.assertNotIn("L2", status["unconverged_levels"])

    def test_missing_tasks_listed_correctly(self):
        status = pr.ts_establishment_status(["F1.1"], {})
        self.assertIn("F1.2", status["missing_tasks"])
        self.assertNotIn("F1.1", status["missing_tasks"])

    def test_negative_open_change_count_raises(self):
        with self.assertRaises(ValueError):
            pr.ts_establishment_status(self._ALL, {"L1": -1})

    def test_empty_decomp_dict_treated_as_converged(self):
        status = pr.ts_establishment_status(self._ALL, {})
        self.assertTrue(status["all_levels_converged"])
        self.assertEqual(status["unconverged_levels"], [])


if __name__ == "__main__":
    unittest.main()

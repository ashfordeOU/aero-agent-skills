#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C per-phase SE task overview.

Exercises scripts/e10_phase_task_overview_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the generic task
list spans phases 0 through F with fixed tasks per phase; each task's
status is done/waived/open, never both done and waived; phase-exit
readiness requires no open task, with the open ones listed; unknown
phases and unknown tasks raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_phase_task_overview_logic as pt  # noqa: E402


class TasksForTest(unittest.TestCase):
    def test_all_seven_phases(self):
        for phase in ("0", "A", "B", "C", "D", "E", "F"):
            with self.subTest(phase=phase):
                self.assertTrue(len(pt.tasks_for(phase)) >= 2)

    def test_phase_d_tasks(self):
        self.assertEqual(
            pt.tasks_for("D"),
            ("qualification test execution", "acceptance test execution", "as-built documentation"),
        )

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            pt.tasks_for("Z")


class TaskStatusTest(unittest.TestCase):
    def test_done_task(self):
        self.assertEqual(
            pt.task_status("B", "interface definition", ["interface definition"], []),
            "done",
        )

    def test_waived_task(self):
        self.assertEqual(
            pt.task_status("B", "interface definition", [], ["interface definition"]),
            "waived",
        )

    def test_open_task(self):
        self.assertEqual(
            pt.task_status("B", "interface definition", [], []),
            "open",
        )

    def test_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            pt.task_status("B", "not a real task", [], [])

    def test_done_and_waived_raises(self):
        with self.assertRaises(ValueError):
            pt.task_status(
                "B", "interface definition",
                ["interface definition"], ["interface definition"],
            )


class PhaseTaskRegisterTest(unittest.TestCase):
    def test_register_order_and_status(self):
        register = pt.phase_task_register(
            "0", ["mission needs capture"], ["feasibility assessment"],
        )
        self.assertEqual(
            register,
            [
                ("mission needs capture", "done"),
                ("feasibility assessment", "waived"),
                ("top-level requirement drafting", "open"),
            ],
        )


class PhaseExitReadyTest(unittest.TestCase):
    def test_ready_when_all_done_or_waived(self):
        ready, open_tasks = pt.phase_exit_ready(
            "F", ["disposal execution"], ["close-out reporting"],
        )
        self.assertTrue(ready)
        self.assertEqual(open_tasks, [])

    def test_not_ready_lists_open_tasks(self):
        ready, open_tasks = pt.phase_exit_ready("F", ["disposal execution"], [])
        self.assertFalse(ready)
        self.assertEqual(open_tasks, ["close-out reporting"])

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            pt.phase_exit_ready("Z", [], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

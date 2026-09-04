#!/usr/bin/env python3
"""Gate 3 contract test: test-point-matrix-design.

Exercises scripts/point_matrix_design_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - build_test_matrix
expands the altitude, speed, weight, and configuration sweeps into the
full grid in deterministic altitude-major order; add_repeat_points marks
every repeat_interval-th point; sequence_for_efficiency groups by
configuration of first appearance, then altitude, then speed;
steady_state_check flags the points outside the tolerance band. All
expected values are hand-computed analytic results.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import point_matrix_design_logic as tpm  # noqa: E402


class BuildTestMatrixTest(unittest.TestCase):
    def test_analytic_grid(self):
        # Two altitudes x two speeds x one weight x two configurations
        # is 8 points. Grid order is altitude-major, then speed, then
        # weight, then configuration: tp1 is the first altitude, first
        # speed, first weight, first configuration.
        out = tpm.build_test_matrix(
            altitudes=[10000, 20000],
            speeds=[120, 140],
            weights=[50000],
            configurations=["clean", "flaps-15"],
        )
        self.assertEqual(out["count"], 8)
        pts = out["points"]
        self.assertEqual(
            [(p["id"], p["altitude"], p["speed"], p["weight"],
              p["configuration"]) for p in pts],
            [
                ("tp1", 10000, 120, 50000, "clean"),
                ("tp2", 10000, 120, 50000, "flaps-15"),
                ("tp3", 10000, 140, 50000, "clean"),
                ("tp4", 10000, 140, 50000, "flaps-15"),
                ("tp5", 20000, 120, 50000, "clean"),
                ("tp6", 20000, 120, 50000, "flaps-15"),
                ("tp7", 20000, 140, 50000, "clean"),
                ("tp8", 20000, 140, 50000, "flaps-15"),
            ],
        )
        self.assertTrue(all(p["repeat"] is False for p in pts))

    def test_analytic_single_point(self):
        out = tpm.build_test_matrix(
            altitudes=[10000], speeds=[120], weights=[50000],
            configurations=["clean"],
        )
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["points"][0]["id"], "tp1")
        self.assertEqual(out["points"][0]["configuration"], "clean")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([], [120], [50000], ["clean"])  # empty alt
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [], [50000], ["clean"])  # empty speed
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [120], [], ["clean"])  # empty weight
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [120], [50000], [])  # empty configs
        with self.assertRaises(ValueError):
            tpm.build_test_matrix("10000", [120], [50000], ["clean"])
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], ["fast"], [50000], ["clean"])
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [True], [50000], ["clean"])  # bool
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([-500], [120], [50000], ["clean"])
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [0], [50000], ["clean"])  # zero speed
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [120], [0], ["clean"])  # zero weight
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [120], [50000], [""])  # blank label
        with self.assertRaises(ValueError):
            tpm.build_test_matrix([10000], [120], [50000], [7])


class AddRepeatPointsTest(unittest.TestCase):
    def setUp(self):
        self.grid = tpm.build_test_matrix(
            altitudes=[10000, 20000],
            speeds=[120, 140],
            weights=[50000],
            configurations=["clean", "flaps-15"],
        )["points"]

    def test_analytic_every_third(self):
        # 8 points, interval 3: exactly tp3 and tp6 are repeats.
        out = tpm.add_repeat_points(self.grid, 3)
        repeats = [p["id"] for p in out if p["repeat"]]
        self.assertEqual(repeats, ["tp3", "tp6"])
        self.assertEqual(len(out), 8)

    def test_analytic_interval_two(self):
        out = tpm.add_repeat_points(self.grid[:5], 2)
        repeats = [p["id"] for p in out if p["repeat"]]
        self.assertEqual(repeats, ["tp2", "tp4"])

    def test_input_not_modified(self):
        tpm.add_repeat_points(self.grid, 3)
        self.assertTrue(all(p["repeat"] is False for p in self.grid))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpm.add_repeat_points([], 3)  # empty points
        with self.assertRaises(ValueError):
            tpm.add_repeat_points(self.grid, 1)  # interval 1
        with self.assertRaises(ValueError):
            tpm.add_repeat_points(self.grid, 0)
        with self.assertRaises(ValueError):
            tpm.add_repeat_points(self.grid, 2.5)  # not an int
        with self.assertRaises(ValueError):
            tpm.add_repeat_points(self.grid, True)  # bool interval
        with self.assertRaises(ValueError):
            tpm.add_repeat_points([{"repeat": False}], 3)  # no id
        with self.assertRaises(ValueError):
            tpm.add_repeat_points([{"id": "tp1"}], 3)  # no repeat key
        with self.assertRaises(ValueError):
            tpm.add_repeat_points(
                [
                    {"id": "tp1", "repeat": False},
                    {"id": "tp1", "repeat": False},
                ],
                3,
            )  # duplicate id
        with self.assertRaises(ValueError):
            tpm.add_repeat_points(["not-a-dict"], 3)


class SequenceForEfficiencyTest(unittest.TestCase):
    def test_analytic_group_order(self):
        # First appearance order is flaps-15 (a), then clean (b): the
        # flaps-15 group flies first, sorted by altitude then speed,
        # then the clean group.
        points = [
            {"id": "a", "configuration": "flaps-15",
             "altitude": 20000, "speed": 140},
            {"id": "b", "configuration": "clean",
             "altitude": 10000, "speed": 120},
            {"id": "c", "configuration": "flaps-15",
             "altitude": 10000, "speed": 140},
            {"id": "d", "configuration": "clean",
             "altitude": 20000, "speed": 120},
        ]
        out = tpm.sequence_for_efficiency(points)
        self.assertEqual([p["id"] for p in out], ["c", "a", "b", "d"])

    def test_stable_ties_keep_input_order(self):
        # Identical configuration, altitude, and speed keep input order.
        points = [
            {"id": "x", "configuration": "clean",
             "altitude": 10000, "speed": 120},
            {"id": "y", "configuration": "clean",
             "altitude": 10000, "speed": 120},
        ]
        out = tpm.sequence_for_efficiency(points)
        self.assertEqual([p["id"] for p in out], ["x", "y"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpm.sequence_for_efficiency([])  # empty
        with self.assertRaises(ValueError):
            tpm.sequence_for_efficiency(["not-a-dict"])
        with self.assertRaises(ValueError):
            tpm.sequence_for_efficiency(
                [{"id": "a", "altitude": 10000, "speed": 120}]
            )  # missing configuration
        with self.assertRaises(ValueError):
            tpm.sequence_for_efficiency(
                [{"id": "a", "configuration": 5,
                  "altitude": 10000, "speed": 120}]
            )  # numeric configuration
        with self.assertRaises(ValueError):
            tpm.sequence_for_efficiency(
                [{"id": "a", "configuration": "clean",
                  "altitude": True, "speed": 120}]
            )  # bool altitude
        with self.assertRaises(ValueError):
            tpm.sequence_for_efficiency(
                [{"id": "a", "configuration": "clean", "altitude": 10000}]
            )  # missing speed


class SteadyStateCheckTest(unittest.TestCase):
    def setUp(self):
        self.grid = tpm.build_test_matrix(
            altitudes=[10000, 20000],
            speeds=[120, 140],
            weights=[50000],
            configurations=["clean"],
        )["points"]

    def test_analytic_invalid_point(self):
        # Tolerances: altitude 100, speed 2, weight 200. tp1 holds
        # exactly; tp2 is 2 knots off, which is inside the band; tp3 is
        # inside; tp4 is 1000 pounds off, outside the band.
        out = tpm.steady_state_check(
            self.grid,
            {"altitude": 100, "speed": 2, "weight": 200},
            {
                "tp1": {"altitude": 10000, "speed": 120, "weight": 50000},
                "tp2": {"altitude": 10000, "speed": 142, "weight": 50000},
                "tp3": {"altitude": 20000, "speed": 118, "weight": 50000},
                "tp4": {"altitude": 20000, "speed": 140, "weight": 49000},
            },
        )
        self.assertEqual(out["valid"], ["tp1", "tp2", "tp3"])
        self.assertEqual(out["invalid"], ["tp4"])
        self.assertEqual(out["verdict"], "invalid-points")

    def test_analytic_all_valid(self):
        planned = {
            p["id"]: {
                "altitude": p["altitude"],
                "speed": p["speed"],
                "weight": p["weight"],
            }
            for p in self.grid
        }
        out = tpm.steady_state_check(
            self.grid,
            {"altitude": 50, "speed": 1, "weight": 100},
            planned,
        )
        self.assertEqual(out["invalid"], [])
        self.assertEqual(out["verdict"], "all-valid")

    def test_invalid_inputs_raise(self):
        good = {
            p["id"]: {"altitude": p["altitude"], "speed": p["speed"],
                      "weight": p["weight"]}
            for p in self.grid
        }
        with self.assertRaises(ValueError):
            tpm.steady_state_check([], {"altitude": 1, "speed": 1,
                                        "weight": 1}, {})  # empty points
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid, {"altitude": 1, "speed": 1}, good
            )  # missing tolerance key
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid,
                {"altitude": -1, "speed": 1, "weight": 1},
                good,
            )  # negative tolerance
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid,
                {"altitude": True, "speed": 1, "weight": 1},
                good,
            )  # bool tolerance
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid,
                {"altitude": 1, "speed": 1, "weight": 1},
                {"tp1": {"altitude": 1, "speed": 1, "weight": 1}},
            )  # reading missing for a point
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid,
                {"altitude": 1, "speed": 1, "weight": 1},
                dict(good, tp99={"altitude": 1, "speed": 1, "weight": 1}),
            )  # unknown point id
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid,
                {"altitude": 1, "speed": 1, "weight": 1},
                {"tp1": 42},
            )  # reading not a dict
        with self.assertRaises(ValueError):
            tpm.steady_state_check(
                self.grid,
                {"altitude": 1, "speed": 1, "weight": 1},
                {"tp1": {"altitude": "high", "speed": 1, "weight": 1}},
            )  # non-numeric reading


class TestPointMatrixScenarioTest(unittest.TestCase):
    def test_analytic_scenario(self):
        # Full contract scenario: a 2 x 2 x 1 x 2 grid of 8 points,
        # repeats every 3rd point, efficiency sequencing, and one point
        # outside the steady state tolerance band.
        grid = tpm.build_test_matrix(
            altitudes=[10000, 20000],
            speeds=[120, 140],
            weights=[50000],
            configurations=["clean", "flaps-15"],
        )["points"]
        self.assertEqual(grid[0]["id"], "tp1")

        marked = tpm.add_repeat_points(grid, 3)
        self.assertEqual(
            [p["id"] for p in marked if p["repeat"]], ["tp3", "tp6"]
        )

        # Clean appears first in the grid, so the sequenced order is
        # clean at 10000 (tp1, tp3), clean at 20000 (tp5, tp7), then
        # flaps-15 (tp2, tp4, tp6, tp8); the repeats survive.
        seq = tpm.sequence_for_efficiency(marked)
        self.assertEqual(
            [p["id"] for p in seq],
            ["tp1", "tp3", "tp5", "tp7", "tp2", "tp4", "tp6", "tp8"],
        )
        self.assertEqual(seq[1]["repeat"], True)
        self.assertEqual(seq[6]["repeat"], True)

        obs = {}
        for p in grid:
            obs[p["id"]] = {
                "altitude": p["altitude"],
                "speed": p["speed"],
                "weight": p["weight"],
            }
        obs["tp4"]["weight"] = 48900  # 1100 pounds off, outside band
        check = tpm.steady_state_check(
            grid, {"altitude": 100, "speed": 2, "weight": 200}, obs
        )
        self.assertEqual(check["invalid"], ["tp4"])
        self.assertEqual(check["verdict"], "invalid-points")


if __name__ == "__main__":
    unittest.main(verbosity=2)

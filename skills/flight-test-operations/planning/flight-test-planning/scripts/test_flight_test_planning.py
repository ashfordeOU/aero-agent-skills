#!/usr/bin/env python3
"""Gate 3 contract test: flight-test-planning.

Exercises scripts/flight_test_planning_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - build_up_order
sorts test points by risk ascending with stable ties and flags
prerequisites that are not part of the point set; instrumentation_complete
returns the missing instruments and the completeness verdict;
test_matrix_complete checks that every objective has a covering point;
go_no_gate returns GO only when all four checks pass. All expected
values are hand-computed analytic results.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flight_test_planning_logic as ftp  # noqa: E402


class BuildUpOrderTest(unittest.TestCase):
    def test_analytic_order(self):
        # Risks 3, 1, 2 sort to risk 1, 2, 3: p1 first, then p3,
        # then p2; both prereqs exist, so no flags and verdict ok.
        points = [
            {"id": "p2", "risk": 3, "prerequisites": ["p1"]},
            {"id": "p1", "risk": 1, "prerequisites": []},
            {"id": "p3", "risk": 2, "prerequisites": ["p1"]},
        ]
        out = ftp.build_up_order(points)
        self.assertEqual([p["id"] for p in out["ordered"]], ["p1", "p3", "p2"])
        self.assertEqual(out["missing_prerequisites"], [])
        self.assertEqual(out["verdict"], "ok")

    def test_analytic_missing_prerequisite(self):
        # p4 depends on p7, which is not in the set: flagged, and the
        # verdict becomes missing-prerequisites.
        points = [
            {"id": "p1", "risk": 1, "prerequisites": []},
            {"id": "p4", "risk": 4, "prerequisites": ["p7"]},
        ]
        out = ftp.build_up_order(points)
        self.assertEqual([p["id"] for p in out["ordered"]], ["p1", "p4"])
        self.assertEqual(
            out["missing_prerequisites"], [{"point": "p4", "missing": ["p7"]}]
        )
        self.assertEqual(out["verdict"], "missing-prerequisites")

    def test_stable_ties_keep_input_order(self):
        # Equal risks keep the input order, so the result is
        # deterministic.
        points = [
            {"id": "t1", "risk": 2, "prerequisites": []},
            {"id": "t2", "risk": 2, "prerequisites": []},
            {"id": "t3", "risk": 1, "prerequisites": []},
        ]
        out = ftp.build_up_order(points)
        self.assertEqual([p["id"] for p in out["ordered"]], ["t3", "t1", "t2"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftp.build_up_order([])  # empty list
        with self.assertRaises(ValueError):
            ftp.build_up_order(["not-a-dict"])  # non-dict point
        with self.assertRaises(ValueError):
            ftp.build_up_order([{"risk": 1, "prerequisites": []}])  # no id
        with self.assertRaises(ValueError):
            ftp.build_up_order(
                [
                    {"id": "p1", "risk": 1, "prerequisites": []},
                    {"id": "p1", "risk": 2, "prerequisites": []},
                ]
            )  # duplicate id
        with self.assertRaises(ValueError):
            ftp.build_up_order(
                [{"id": "p1", "risk": -1, "prerequisites": []}]
            )  # negative risk
        with self.assertRaises(ValueError):
            ftp.build_up_order(
                [{"id": "p1", "risk": True, "prerequisites": []}]
            )  # bool risk
        with self.assertRaises(ValueError):
            ftp.build_up_order(
                [{"id": "p1", "risk": 1, "prerequisites": "p2"}]
            )  # prerequisites not a list


class InstrumentationCompleteTest(unittest.TestCase):
    def test_analytic_missing_one_sensor(self):
        # Four required, three provided: exactly "strain gauge" is
        # missing, so the verdict is incomplete.
        required = ["airspeed probe", "alpha vane", "accelerometer", "strain gauge"]
        provided = ["airspeed probe", "alpha vane", "accelerometer"]
        out = ftp.instrumentation_complete(required, provided)
        self.assertEqual(out["missing"], ["strain gauge"])
        self.assertEqual(out["verdict"], "incomplete")

    def test_analytic_complete(self):
        required = ["airspeed probe", "alpha vane"]
        out = ftp.instrumentation_complete(required, required)
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["verdict"], "complete")

    def test_whitespace_stripped_before_match(self):
        out = ftp.instrumentation_complete(
            ["airspeed probe"], ["  airspeed probe  "]
        )
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["verdict"], "complete")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftp.instrumentation_complete([], ["airspeed probe"])  # empty required
        with self.assertRaises(ValueError):
            ftp.instrumentation_complete("airspeed probe", ["airspeed probe"])
        with self.assertRaises(ValueError):
            ftp.instrumentation_complete(["airspeed probe"], 42)  # not a list
        with self.assertRaises(ValueError):
            ftp.instrumentation_complete(["airspeed probe", 7], ["airspeed probe"])


class TestMatrixCompleteTest(unittest.TestCase):
    def test_analytic_missing_one_objective(self):
        # Three objectives, two covering points: exactly
        # climb-performance is uncovered, so the verdict is incomplete.
        objectives = ["stall-behavior", "flutter-clearance", "climb-performance"]
        points = [
            {"id": "tp1", "covers": ["stall-behavior"]},
            {"id": "tp2", "covers": ["flutter-clearance"]},
        ]
        out = ftp.test_matrix_complete(points, objectives)
        self.assertEqual(out["uncovered"], ["climb-performance"])
        self.assertEqual(out["coverage"]["stall-behavior"], ["tp1"])
        self.assertEqual(out["coverage"]["climb-performance"], [])
        self.assertEqual(out["verdict"], "incomplete")

    def test_analytic_complete(self):
        objectives = ["stall-behavior", "flutter-clearance", "climb-performance"]
        points = [
            {"id": "tp1", "covers": ["stall-behavior"]},
            {"id": "tp2", "covers": ["flutter-clearance"]},
            {"id": "tp3", "covers": ["climb-performance"]},
        ]
        out = ftp.test_matrix_complete(points, objectives)
        self.assertEqual(out["uncovered"], [])
        self.assertEqual(out["coverage"]["climb-performance"], ["tp3"])
        self.assertEqual(out["verdict"], "complete")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftp.test_matrix_complete([], ["stall-behavior"])  # empty points
        with self.assertRaises(ValueError):
            ftp.test_matrix_complete([{"id": "tp1", "covers": []}], [])  # no objectives
        with self.assertRaises(ValueError):
            ftp.test_matrix_complete(
                [{"id": "tp1", "covers": ["stall-behavior"]}],
                ["stall-behavior", 3],  # non-string objective
            )
        with self.assertRaises(ValueError):
            ftp.test_matrix_complete(
                [
                    {"id": "tp1", "covers": ["stall-behavior"]},
                    {"id": "tp1", "covers": ["flutter-clearance"]},
                ],
                ["stall-behavior", "flutter-clearance"],  # duplicate point id
            )
        with self.assertRaises(ValueError):
            ftp.test_matrix_complete(
                [{"id": "tp1", "covers": "stall-behavior"}],
                ["stall-behavior"],  # covers not a list
            )


class GoNoGateTest(unittest.TestCase):
    def test_analytic_one_false_blocks(self):
        # One false check (instrumentation_ok) forces NO-GO and names
        # the blocker.
        out = ftp.go_no_gate(True, True, False, True)
        self.assertFalse(out["go"])
        self.assertEqual(out["blockers"], ["instrumentation_ok"])
        self.assertEqual(out["verdict"], "NO-GO")

    def test_analytic_all_true_goes(self):
        out = ftp.go_no_gate(True, True, True, True)
        self.assertTrue(out["go"])
        self.assertEqual(out["blockers"], [])
        self.assertEqual(out["verdict"], "GO")

    def test_multiple_blockers_listed_in_order(self):
        out = ftp.go_no_gate(False, False, True, True)
        self.assertFalse(out["go"])
        self.assertEqual(out["blockers"], ["weather_ok", "aircraft_ready"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftp.go_no_gate("yes", True, True, True)  # not a bool
        with self.assertRaises(ValueError):
            ftp.go_no_gate(True, 1, True, True)  # int not a bool
        with self.assertRaises(ValueError):
            ftp.go_no_gate(True, True, None, True)  # None not a bool


class FlightTestPlanScenarioTest(unittest.TestCase):
    def test_analytic_scenario(self):
        # Full contract scenario: a small point list with known order,
        # one missing sensor, one uncovered objective, and one false
        # gate input.
        points = [
            {"id": "p2", "risk": 3, "prerequisites": ["p1"]},
            {"id": "p1", "risk": 1, "prerequisites": []},
            {"id": "p3", "risk": 2, "prerequisites": ["p1"]},
        ]
        order = ftp.build_up_order(points)
        self.assertEqual([p["id"] for p in order["ordered"]], ["p1", "p3", "p2"])

        inst = ftp.instrumentation_complete(
            ["airspeed probe", "alpha vane", "accelerometer", "strain gauge"],
            ["airspeed probe", "alpha vane", "accelerometer"],
        )
        self.assertEqual(inst["missing"], ["strain gauge"])
        self.assertEqual(inst["verdict"], "incomplete")

        matrix = ftp.test_matrix_complete(
            [
                {"id": "tp1", "covers": ["stall-behavior"]},
                {"id": "tp2", "covers": ["flutter-clearance"]},
            ],
            ["stall-behavior", "flutter-clearance", "climb-performance"],
        )
        self.assertEqual(matrix["uncovered"], ["climb-performance"])
        self.assertEqual(matrix["verdict"], "incomplete")

        gate = ftp.go_no_gate(True, True, False, True)
        self.assertFalse(gate["go"])
        self.assertEqual(gate["blockers"], ["instrumentation_ok"])
        self.assertEqual(gate["verdict"], "NO-GO")


if __name__ == "__main__":
    unittest.main(verbosity=2)

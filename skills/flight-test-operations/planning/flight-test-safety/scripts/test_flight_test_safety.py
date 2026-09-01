#!/usr/bin/env python3
"""Gate 3 contract test: flight-test-safety.

Exercises scripts/flight_test_safety_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - assess_risks
scores hazards on the severity by likelihood matrix and names the
high-risk set; envelope_violations flags every test point outside the
speed or load factor limits; procedure_coverage returns the emergency
conditions with no procedure; safety_pilot_assignment returns the
unassigned duties; go_no_go returns GO only when every criterion
passes; mitigation_gaps returns the risks with no mitigation. All
expected values are hand-computed analytic results.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flight_test_safety_logic as fts  # noqa: E402


class AssessRisksTest(unittest.TestCase):
    def test_analytic_levels(self):
        # h1: 4 x 2 = 8 (medium), h2: 5 x 4 = 20 (high), h3: 1 x 1 = 1
        # (low); only h2 is high risk, so the verdict is
        # high-risk-present.
        hazards = [
            {"id": "h1", "severity": 4, "likelihood": 2},
            {"id": "h2", "severity": 5, "likelihood": 4},
            {"id": "h3", "severity": 1, "likelihood": 1},
        ]
        out = fts.assess_risks(hazards)
        self.assertEqual(out["hazards"][0]["level"], "medium")
        self.assertEqual(out["hazards"][0]["index"], 8)
        self.assertEqual(out["hazards"][1]["level"], "high")
        self.assertEqual(out["hazards"][1]["index"], 20)
        self.assertEqual(out["hazards"][2]["level"], "low")
        self.assertEqual(out["high_risk"], ["h2"])
        self.assertEqual(out["verdict"], "high-risk-present")

    def test_analytic_boundaries(self):
        # 3 x 2 = 6 is medium (>= 6), 5 x 3 = 15 is high (>= 15),
        # 2 x 2 = 4 is low.
        hazards = [
            {"id": "a", "severity": 3, "likelihood": 2},
            {"id": "b", "severity": 5, "likelihood": 3},
            {"id": "c", "severity": 2, "likelihood": 2},
        ]
        out = fts.assess_risks(hazards)
        self.assertEqual([h["level"] for h in out["hazards"]], ["medium", "high", "low"])
        self.assertEqual(out["high_risk"], ["b"])

    def test_analytic_all_low(self):
        # 1 x 1, 2 x 1, 1 x 2 are all below the medium threshold.
        hazards = [
            {"id": "x", "severity": 1, "likelihood": 1},
            {"id": "y", "severity": 2, "likelihood": 1},
            {"id": "z", "severity": 1, "likelihood": 2},
        ]
        out = fts.assess_risks(hazards)
        self.assertEqual(out["high_risk"], [])
        self.assertEqual(out["verdict"], "all-low-or-medium")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.assess_risks([])  # empty list
        with self.assertRaises(ValueError):
            fts.assess_risks([42])  # non-dict hazard
        with self.assertRaises(ValueError):
            fts.assess_risks([{"severity": 4, "likelihood": 2}])  # no id
        with self.assertRaises(ValueError):
            fts.assess_risks(
                [
                    {"id": "h1", "severity": 4, "likelihood": 2},
                    {"id": "h1", "severity": 3, "likelihood": 2},
                ]
            )  # duplicate id
        with self.assertRaises(ValueError):
            fts.assess_risks([{"id": "h1", "severity": 0, "likelihood": 2}])  # too low
        with self.assertRaises(ValueError):
            fts.assess_risks([{"id": "h1", "severity": 6, "likelihood": 2}])  # too high
        with self.assertRaises(ValueError):
            fts.assess_risks([{"id": "h1", "severity": 4, "likelihood": 5.5}])  # float
        with self.assertRaises(ValueError):
            fts.assess_risks([{"id": "h1", "severity": True, "likelihood": 2}])  # bool
        with self.assertRaises(ValueError):
            fts.assess_risks([{"id": "h1", "severity": 4}])  # missing likelihood


class EnvelopeViolationsTest(unittest.TestCase):
    LIMITS = {"v_min": 100, "v_max": 200, "n_min": -1.0, "n_max": 3.5}

    def test_analytic_violations(self):
        # p1 is inside; p2 exceeds v_max (250 > 200); p3 exceeds n_max
        # (4.0 > 3.5). Violations sort by point then limit.
        points = [
            {"id": "p1", "speed": 150, "load_factor": 2.0},
            {"id": "p2", "speed": 250, "load_factor": 1.0},
            {"id": "p3", "speed": 120, "load_factor": 4.0},
        ]
        out = fts.envelope_violations(self.LIMITS, points)
        self.assertEqual(
            out["violations"],
            [
                {"point": "p2", "limit": "v_max", "value": 250, "bound": 200},
                {"point": "p3", "limit": "n_max", "value": 4.0, "bound": 3.5},
            ],
        )
        self.assertEqual(out["verdict"], "limit-violations")

    def test_analytic_boundary_inside(self):
        # Points exactly on the limits are inside the envelope.
        points = [
            {"id": "p1", "speed": 100, "load_factor": -1.0},
            {"id": "p2", "speed": 200, "load_factor": 3.5},
        ]
        out = fts.envelope_violations(self.LIMITS, points)
        self.assertEqual(out["violations"], [])
        self.assertEqual(out["verdict"], "within-envelope")

    def test_analytic_speed_floor_violation(self):
        points = [{"id": "p1", "speed": 80, "load_factor": 1.0}]
        out = fts.envelope_violations(self.LIMITS, points)
        self.assertEqual(
            out["violations"],
            [{"point": "p1", "limit": "v_min", "value": 80, "bound": 100}],
        )
        self.assertEqual(out["verdict"], "limit-violations")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.envelope_violations("limits", [])  # limits not a dict
        with self.assertRaises(ValueError):
            fts.envelope_violations({"v_min": 100}, [])  # missing limit key
        with self.assertRaises(ValueError):
            fts.envelope_violations(
                {"v_min": "a", "v_max": 200, "n_min": -1, "n_max": 3}, []
            )  # non-numeric limit
        with self.assertRaises(ValueError):
            fts.envelope_violations(
                {"v_min": 200, "v_max": 100, "n_min": -1, "n_max": 3}, []
            )  # inverted v limits
        with self.assertRaises(ValueError):
            fts.envelope_violations(
                {"v_min": 100, "v_max": 200, "n_min": 3, "n_max": -1}, []
            )  # inverted n limits
        with self.assertRaises(ValueError):
            fts.envelope_violations(self.LIMITS, [])  # empty points
        with self.assertRaises(ValueError):
            fts.envelope_violations(self.LIMITS, ["not-a-dict"])  # non-dict point
        with self.assertRaises(ValueError):
            fts.envelope_violations(self.LIMITS, [{"speed": 150, "load_factor": 1.0}])  # no id
        with self.assertRaises(ValueError):
            fts.envelope_violations(
                self.LIMITS,
                [
                    {"id": "p1", "speed": 150, "load_factor": 1.0},
                    {"id": "p1", "speed": 160, "load_factor": 1.0},
                ],
            )  # duplicate id
        with self.assertRaises(ValueError):
            fts.envelope_violations(
                self.LIMITS, [{"id": "p1", "speed": "fast", "load_factor": 1.0}]
            )  # non-numeric speed
        with self.assertRaises(ValueError):
            fts.envelope_violations(
                self.LIMITS, [{"id": "p1", "speed": 150, "load_factor": True}]
            )  # bool load factor


class ProcedureCoverageTest(unittest.TestCase):
    LIBRARY = {
        "engine failure": ["fly best glide speed", "secure the engine"],
        "hydraulic loss": ["pump the gear manually"],
    }

    def test_analytic_missing_one_condition(self):
        # Three required conditions, two procedures: exactly "cabin
        # smoke" is missing, so the verdict is incomplete.
        required = ["engine failure", "hydraulic loss", "cabin smoke"]
        out = fts.procedure_coverage(required, self.LIBRARY)
        self.assertEqual(out["missing"], ["cabin smoke"])
        self.assertEqual(out["verdict"], "incomplete")

    def test_analytic_complete(self):
        required = ["engine failure", "hydraulic loss"]
        out = fts.procedure_coverage(required, self.LIBRARY)
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["verdict"], "complete")

    def test_whitespace_stripped_before_match(self):
        out = fts.procedure_coverage(["  engine failure "], self.LIBRARY)
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["verdict"], "complete")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.procedure_coverage([], self.LIBRARY)  # empty required
        with self.assertRaises(ValueError):
            fts.procedure_coverage("engine failure", self.LIBRARY)  # not a list
        with self.assertRaises(ValueError):
            fts.procedure_coverage([""], self.LIBRARY)  # blank condition
        with self.assertRaises(ValueError):
            fts.procedure_coverage(["engine failure"], {})  # empty library
        with self.assertRaises(ValueError):
            fts.procedure_coverage(["engine failure"], ["engine failure"])  # not a dict
        with self.assertRaises(ValueError):
            fts.procedure_coverage(["engine failure"], {"": ["step one"]})  # blank key
        with self.assertRaises(ValueError):
            fts.procedure_coverage(
                ["engine failure"], {"engine failure": "fly best glide speed"}
            )  # steps not a list
        with self.assertRaises(ValueError):
            fts.procedure_coverage(["engine failure"], {"engine failure": []})  # empty steps
        with self.assertRaises(ValueError):
            fts.procedure_coverage(
                ["engine failure"], {"engine failure": ["fly best glide speed", 5]}
            )  # non-string step


class SafetyPilotAssignmentTest(unittest.TestCase):
    REQUIRED = ["monitor envelope limits", "call out exceedances", "execute the abort"]

    def test_analytic_missing_one_duty(self):
        # Two of three duties assigned: exactly "execute the abort" is
        # missing, so the verdict is missing-duties.
        assigned = ["monitor envelope limits", "call out exceedances"]
        out = fts.safety_pilot_assignment(self.REQUIRED, assigned)
        self.assertEqual(out["missing"], ["execute the abort"])
        self.assertEqual(out["verdict"], "missing-duties")

    def test_analytic_covered(self):
        out = fts.safety_pilot_assignment(self.REQUIRED, self.REQUIRED)
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["verdict"], "covered")

    def test_whitespace_stripped_before_match(self):
        out = fts.safety_pilot_assignment(
            ["monitor envelope limits"], ["  monitor envelope limits  "]
        )
        self.assertEqual(out["missing"], [])
        self.assertEqual(out["verdict"], "covered")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.safety_pilot_assignment([], ["monitor envelope limits"])  # empty required
        with self.assertRaises(ValueError):
            fts.safety_pilot_assignment(self.REQUIRED, "monitor envelope limits")  # not a list
        with self.assertRaises(ValueError):
            fts.safety_pilot_assignment(["monitor envelope limits", 7], [])  # non-string
        with self.assertRaises(ValueError):
            fts.safety_pilot_assignment(["monitor envelope limits"], [""])  # blank duty


class GoNoGoTest(unittest.TestCase):
    def test_analytic_one_failed_criterion(self):
        # One failed criterion (aircraft readiness) forces NO-GO and
        # names the failure.
        criteria = [
            {"name": "weather", "passed": True},
            {"name": "aircraft readiness", "passed": False},
            {"name": "safety review", "passed": True},
        ]
        out = fts.go_no_go(criteria)
        self.assertFalse(out["go"])
        self.assertEqual(out["failed"], ["aircraft readiness"])
        self.assertEqual(out["verdict"], "NO-GO")

    def test_analytic_all_pass(self):
        criteria = [
            {"name": "weather", "passed": True},
            {"name": "aircraft readiness", "passed": True},
        ]
        out = fts.go_no_go(criteria)
        self.assertTrue(out["go"])
        self.assertEqual(out["failed"], [])
        self.assertEqual(out["verdict"], "GO")

    def test_failed_list_keeps_input_order(self):
        out = fts.go_no_go(
            [
                {"name": "weather", "passed": False},
                {"name": "aircraft readiness", "passed": False},
            ]
        )
        self.assertEqual(out["failed"], ["weather", "aircraft readiness"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.go_no_go([])  # empty criteria
        with self.assertRaises(ValueError):
            fts.go_no_go(["weather"])  # non-dict criterion
        with self.assertRaises(ValueError):
            fts.go_no_go([{"passed": True}])  # missing name
        with self.assertRaises(ValueError):
            fts.go_no_go([{"name": "", "passed": True}])  # blank name
        with self.assertRaises(ValueError):
            fts.go_no_go(
                [
                    {"name": "weather", "passed": True},
                    {"name": "weather", "passed": False},
                ]
            )  # duplicate name
        with self.assertRaises(ValueError):
            fts.go_no_go([{"name": "weather", "passed": "yes"}])  # not a bool
        with self.assertRaises(ValueError):
            fts.go_no_go([{"name": "weather", "passed": 1}])  # int not a bool


class MitigationGapsTest(unittest.TestCase):
    def test_analytic_unmitigated(self):
        # r2 has no mitigation entry: it is the only unmitigated risk.
        risks = ["r1", "r2", "r3"]
        mitigations = {
            "r1": ["add a second safety pilot"],
            "r3": ["limit the maneuver to 0.8 g"],
        }
        out = fts.mitigation_gaps(risks, mitigations)
        self.assertEqual(out["unmitigated"], ["r2"])
        self.assertEqual(out["verdict"], "unmitigated-risks")

    def test_analytic_all_mitigated(self):
        risks = ["r1", "r2"]
        mitigations = {"r1": ["add a second safety pilot"], "r2": ["move the test point"]}
        out = fts.mitigation_gaps(risks, mitigations)
        self.assertEqual(out["unmitigated"], [])
        self.assertEqual(out["verdict"], "all-mitigated")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fts.mitigation_gaps([], {})  # empty risks
        with self.assertRaises(ValueError):
            fts.mitigation_gaps("r1", {})  # risks not a list
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1", ""], {})  # blank risk id
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1"], ["add a second safety pilot"])  # not a dict
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1"], {"r9": ["limit the maneuver"]})  # unknown risk
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1"], {"r1": "add a second safety pilot"})  # not a list
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1"], {"r1": []})  # empty mitigations
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1"], {"r1": ["add a second safety pilot", 3]})  # non-string
        with self.assertRaises(ValueError):
            fts.mitigation_gaps(["r1"], {"r1": [""]})  # blank mitigation


class FlightTestSafetyScenarioTest(unittest.TestCase):
    def test_analytic_scenario(self):
        # Full contract scenario: one high-risk hazard, one envelope
        # violation, one missing procedure, one missing duty, one failed
        # criterion, and one unmitigated risk.
        risks = fts.assess_risks(
            [
                {"id": "over-speed", "severity": 4, "likelihood": 3},
                {"id": "flutter-onset", "severity": 5, "likelihood": 2},
                {"id": "hard-landing", "severity": 4, "likelihood": 4},
            ]
        )
        self.assertEqual(risks["high_risk"], ["hard-landing"])
        self.assertEqual(risks["verdict"], "high-risk-present")

        envelope = fts.envelope_violations(
            {"v_min": 90, "v_max": 220, "n_min": -1.5, "n_max": 3.0},
            [
                {"id": "tp1", "speed": 120, "load_factor": 1.0},
                {"id": "tp2", "speed": 240, "load_factor": 0.5},
            ],
        )
        self.assertEqual(
            envelope["violations"],
            [{"point": "tp2", "limit": "v_max", "value": 240, "bound": 220}],
        )
        self.assertEqual(envelope["verdict"], "limit-violations")

        procedures = fts.procedure_coverage(
            ["engine failure", "cabin fire"],
            {"engine failure": ["fly best glide speed", "secure the engine"]},
        )
        self.assertEqual(procedures["missing"], ["cabin fire"])
        self.assertEqual(procedures["verdict"], "incomplete")

        duties = fts.safety_pilot_assignment(
            ["monitor envelope limits", "call out exceedances", "execute the abort"],
            ["monitor envelope limits", "call out exceedances", "execute the abort"],
        )
        self.assertEqual(duties["missing"], [])
        self.assertEqual(duties["verdict"], "covered")

        gate = fts.go_no_go(
            [
                {"name": "weather", "passed": True},
                {"name": "emergency procedures", "passed": False},
                {"name": "safety review", "passed": True},
            ]
        )
        self.assertFalse(gate["go"])
        self.assertEqual(gate["failed"], ["emergency procedures"])
        self.assertEqual(gate["verdict"], "NO-GO")

        mitigations = fts.mitigation_gaps(
            ["hard-landing", "over-speed"],
            {"hard-landing": ["practice go-arounds"]},
        )
        self.assertEqual(mitigations["unmitigated"], ["over-speed"])
        self.assertEqual(mitigations["verdict"], "unmitigated-risks")


if __name__ == "__main__":
    unittest.main(verbosity=2)

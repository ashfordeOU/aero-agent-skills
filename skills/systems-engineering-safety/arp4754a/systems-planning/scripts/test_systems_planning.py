#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A systems development planning.

Exercises scripts/systems_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — failure-condition severity maps
to FDAL; item IDAL is the highest FDAL among implemented functions; the
planning artifact set covers certification plan, system development plan,
and safety assessment plan; safety assessment depth scales with DAL.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import systems_logic as sysl  # noqa: E402


class FdalTest(unittest.TestCase):
    def test_severity_maps_to_fdal(self):
        cases = [
            ("Catastrophic", "A"),
            ("Hazardous", "B"),
            ("Major", "C"),
            ("Minor", "D"),
            ("No safety effect", "E"),
        ]
        for severity, expected in cases:
            with self.subTest(severity=severity):
                self.assertEqual(sysl.fdal_from_severity(severity), expected)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            sysl.fdal_from_severity("Negligible")


class IdalTest(unittest.TestCase):
    def test_idal_is_highest_fdal(self):
        self.assertEqual(sysl.idal_for_item(["C", "A"]), "A")
        self.assertEqual(sysl.idal_for_item(["D"]), "D")
        self.assertEqual(sysl.idal_for_item(["E", "E"]), "E")
        self.assertEqual(sysl.idal_for_item(["C", "C", "D"]), "C")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            sysl.idal_for_item([])

    def test_invalid_fdal_raises(self):
        with self.assertRaises(ValueError):
            sysl.idal_for_item(["F"])


class PlanningArtifactsTest(unittest.TestCase):
    def test_cert_program_plan_set(self):
        arts = sysl.planning_artifacts_required(safety_significant=True)
        for required in (
            "certification-plan",
            "system-development-plan",
            "safety-assessment-plan",
        ):
            self.assertIn(required, arts)

    def test_no_safety_significant_drops_safety_plan(self):
        arts = sysl.planning_artifacts_required(safety_significant=False)
        self.assertNotIn("safety-assessment-plan", arts)
        self.assertIn("certification-plan", arts)

    def test_safety_depth_scales_with_dal(self):
        for dal, expected in [
            ("A", "full"), ("B", "full"), ("C", "full"),
            ("D", "baseline"), ("E", "baseline"),
        ]:
            with self.subTest(dal=dal):
                self.assertEqual(sysl.safety_assessment_depth(dal), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)

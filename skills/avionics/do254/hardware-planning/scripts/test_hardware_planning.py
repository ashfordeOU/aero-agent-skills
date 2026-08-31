#!/usr/bin/env python3
"""Gate 3 contract test: DO-254 hardware design assurance planning.

Exercises scripts/hardware_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — AEH simple/complex
classification and the planning artifact set per class.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hardware_logic as hw  # noqa: E402


class AeHClassificationTest(unittest.TestCase):
    def test_programmable_logic_is_complex(self):
        self.assertEqual(
            hw.classify_aeh(
                has_programmable_logic=True,
                has_internal_state=False,
                fully_verifiable_from_top_data=True,
                safety_significant=False,
            ),
            "complex",
        )

    def test_internal_state_is_complex(self):
        self.assertEqual(
            hw.classify_aeh(
                has_programmable_logic=False,
                has_internal_state=True,
                fully_verifiable_from_top_data=True,
                safety_significant=False,
            ),
            "complex",
        )

    def test_not_fully_verifiable_is_complex(self):
        self.assertEqual(
            hw.classify_aeh(
                has_programmable_logic=False,
                has_internal_state=False,
                fully_verifiable_from_top_data=False,
                safety_significant=False,
            ),
            "complex",
        )

    def test_safety_significant_is_complex(self):
        self.assertEqual(
            hw.classify_aeh(
                has_programmable_logic=False,
                has_internal_state=False,
                fully_verifiable_from_top_data=True,
                safety_significant=True,
            ),
            "complex",
        )

    def test_simple_only_when_all_clear(self):
        self.assertEqual(
            hw.classify_aeh(
                has_programmable_logic=False,
                has_internal_state=False,
                fully_verifiable_from_top_data=True,
                safety_significant=False,
            ),
            "simple",
        )


class PlanningArtifactsTest(unittest.TestCase):
    def test_complex_full_process(self):
        arts = hw.planning_artifacts("complex")
        for required in (
            "phac",
            "requirements-capture",
            "detailed-design",
            "verification",
            "configuration-management",
            "process-assurance",
        ):
            self.assertIn(required, arts)

    def test_simple_reduced_process(self):
        arts = hw.planning_artifacts("simple")
        self.assertNotIn("phac", arts)
        self.assertIn("hardware-plan", arts)
        self.assertIn("verification", arts)

    def test_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            hw.planning_artifacts("hypercomplex")


if __name__ == "__main__":
    unittest.main(verbosity=2)

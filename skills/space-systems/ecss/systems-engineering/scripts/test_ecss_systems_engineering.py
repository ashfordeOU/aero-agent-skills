#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C systems engineering.

Exercises scripts/ecss_systems_engineering_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the lifecycle
spans phases 0 through F with fixed names; each phase maps to its
review gates (MDR, PRR/SRR, PDR, CDR, QR/AR/FRR, CRR/ER, none at F);
phase-exit readiness requires all assigned reviews complete with the
missing ones listed; unknown phases raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ecss_systems_engineering_logic as ecl  # noqa: E402


class PhaseNameTest(unittest.TestCase):
    def test_all_seven_phase_names(self):
        cases = [
            ("0", "mission analysis and feasibility"),
            ("A", "feasibility"),
            ("B", "preliminary definition"),
            ("C", "detailed definition"),
            ("D", "qualification and production"),
            ("E", "utilization"),
            ("F", "disposal"),
        ]
        for phase, expected in cases:
            with self.subTest(phase=phase):
                self.assertEqual(ecl.phase_name(phase), expected)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ecl.phase_name("Z")


class ReviewsTest(unittest.TestCase):
    def test_reviews_per_phase(self):
        cases = [
            ("0", ["MDR"]),
            ("A", ["PRR", "SRR"]),
            ("B", ["PDR"]),
            ("C", ["CDR"]),
            ("D", ["QR", "AR", "FRR"]),
            ("E", ["CRR", "ER"]),
            ("F", []),
        ]
        for phase, expected in cases:
            with self.subTest(phase=phase):
                self.assertEqual(ecl.reviews_for(phase), expected)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ecl.reviews_for("Z")

    def test_phase_gate_map_returns_tuple(self):
        self.assertEqual(
            ecl.phase_gate_map("D"),
            ("qualification and production", ["QR", "AR", "FRR"]),
        )


class GateReadyTest(unittest.TestCase):
    def test_gate_ready_when_all_reviews_complete(self):
        self.assertEqual(ecl.gate_ready("B", ["PDR"]), (True, []))

    def test_gate_not_ready_lists_missing(self):
        ready, missing = ecl.gate_ready("B", [])
        self.assertFalse(ready)
        self.assertEqual(missing, ["PDR"])

    def test_partial_reviews_at_phase_d(self):
        ready, missing = ecl.gate_ready("D", ["QR", "AR"])
        self.assertFalse(ready)
        self.assertEqual(missing, ["FRR"])

    def test_disposal_phase_has_no_gate_reviews(self):
        self.assertEqual(ecl.gate_ready("F", []), (True, []))

    def test_extra_completed_reviews_do_not_fail(self):
        self.assertEqual(ecl.gate_ready("B", ["PDR", "CDR"]), (True, []))

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ecl.gate_ready("Z", ["PDR"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A FTA/FMEA analysis.

Exercises scripts/fta_fmea_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the analysis set scales
with assurance level (FTA/FMEA always, CCA at A/B); minimal cut sets
derive from AND/OR gate structures (OR unions, AND cartesian-product);
cut-set probabilities sanity-check against the top event probability;
FMEA severities map to levels A-E; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fta_fmea_logic as fta  # noqa: E402


class AnalysisSetTest(unittest.TestCase):
    def test_full_set_at_levels_a_and_b(self):
        for level in ("A", "B"):
            with self.subTest(level=level):
                analyses = fta.analysis_set_for_level(level)
                self.assertIn("FTA", analyses)
                self.assertIn("FMEA", analyses)
                self.assertIn("CCA", analyses)

    def test_reduced_set_at_lower_levels(self):
        for level in ("C", "D", "E"):
            with self.subTest(level=level):
                analyses = fta.analysis_set_for_level(level)
                self.assertIn("FTA", analyses)
                self.assertIn("FMEA", analyses)
                self.assertNotIn("CCA", analyses)

    def test_invalid_level_raises(self):
        for bad in ("F", "a", "", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    fta.analysis_set_for_level(bad)


class CutSetTest(unittest.TestCase):
    def test_single_or_gate(self):
        structure = {"top": {"op": "OR", "children": ["a", "b"]}}
        self.assertEqual(
            fta.minimal_cut_sets(structure, "top"),
            [frozenset({"a"}), frozenset({"b"})],
        )

    def test_single_and_gate(self):
        structure = {"top": {"op": "AND", "children": ["a", "b"]}}
        self.assertEqual(
            fta.minimal_cut_sets(structure, "top"),
            [frozenset({"a", "b"})],
        )

    def test_or_of_ands(self):
        structure = {
            "top": {"op": "OR", "children": ["x", "y"]},
            "x": {"op": "AND", "children": ["a", "b"]},
            "y": {"op": "AND", "children": ["c", "d"]},
        }
        self.assertEqual(
            fta.minimal_cut_sets(structure, "top"),
            [frozenset({"a", "b"}), frozenset({"c", "d"})],
        )

    def test_and_of_ors(self):
        structure = {
            "top": {"op": "AND", "children": ["x", "y"]},
            "x": {"op": "OR", "children": ["a", "b"]},
            "y": {"op": "OR", "children": ["c", "d"]},
        }
        self.assertEqual(
            fta.minimal_cut_sets(structure, "top"),
            [
                frozenset({"a", "c"}),
                frozenset({"a", "d"}),
                frozenset({"b", "c"}),
                frozenset({"b", "d"}),
            ],
        )

    def test_and_dedupes_repeated_children(self):
        structure = {"top": {"op": "AND", "children": ["a", "a"]}}
        self.assertEqual(
            fta.minimal_cut_sets(structure, "top"),
            [frozenset({"a"})],
        )

    def test_top_as_basic_event(self):
        self.assertEqual(fta.minimal_cut_sets({}, "e1"), [frozenset({"e1"})])

    def test_missing_child_key_raises(self):
        structure = {"top": {"op": "AND"}}
        with self.assertRaises(ValueError):
            fta.minimal_cut_sets(structure, "top")

    def test_unknown_op_raises(self):
        structure = {"top": {"op": "XOR", "children": ["a", "b"]}}
        with self.assertRaises(ValueError):
            fta.minimal_cut_sets(structure, "top")

    def test_cycle_raises(self):
        structure = {"top": {"op": "AND", "children": ["top"]}}
        with self.assertRaises(ValueError):
            fta.minimal_cut_sets(structure, "top")


class ProbabilityTest(unittest.TestCase):
    def test_cut_set_probability_is_product(self):
        probs = {"a": 0.1, "b": 0.2, "c": 0.5}
        self.assertAlmostEqual(
            fta.cut_set_probability(frozenset({"a", "b", "c"}), probs), 0.01
        )

    def test_missing_event_raises(self):
        with self.assertRaises(ValueError):
            fta.cut_set_probability(frozenset({"a", "z"}), {"a": 0.1})


class SanityTest(unittest.TestCase):
    def test_sane_when_all_below_top_probability(self):
        cut_sets = [frozenset({"a"}), frozenset({"b"})]
        probs = {"a": 0.01, "b": 0.02}
        self.assertEqual(fta.cut_set_sanity(cut_sets, probs, top_prob=0.05), [])

    def test_flags_cut_sets_above_top_probability(self):
        cut_sets = [frozenset({"a"}), frozenset({"b"})]
        probs = {"a": 0.1, "b": 0.02}
        flagged = fta.cut_set_sanity(cut_sets, probs, top_prob=0.05)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0][0], frozenset({"a"}))
        self.assertAlmostEqual(flagged[0][1], 0.1)


class SeverityTest(unittest.TestCase):
    def test_severity_maps_to_level(self):
        cases = [
            ("Catastrophic", "A"),
            ("Hazardous", "B"),
            ("Major", "C"),
            ("Minor", "D"),
            ("No safety effect", "E"),
        ]
        for severity, expected in cases:
            with self.subTest(severity=severity):
                self.assertEqual(fta.fmea_severity_level(severity), expected)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            fta.fmea_severity_level("Inconvenient")


if __name__ == "__main__":
    unittest.main(verbosity=2)

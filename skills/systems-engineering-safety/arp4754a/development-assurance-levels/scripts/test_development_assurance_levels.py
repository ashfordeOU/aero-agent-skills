#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A development assurance levels.

Exercises scripts/development_assurance_levels_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 - the
severity-to-DAL mapping returns A through E for the five severity
categories, the reverse lookup and rank helpers agree with the mapping,
the DAL propagation check rejects an item DAL lower than its function
DAL, the independence alternative is honored only with a validated
independence argument, the assignment record pins the FDAL and initial
IDAL, and invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import development_assurance_levels_logic as dal  # noqa: E402


class SeverityToDalTest(unittest.TestCase):
    def test_full_mapping(self):
        # A = Catastrophic down to E = No safety effect.
        self.assertEqual(dal.dal_from_severity("Catastrophic"), "A")
        self.assertEqual(dal.dal_from_severity("Hazardous"), "B")
        self.assertEqual(dal.dal_from_severity("Major"), "C")
        self.assertEqual(dal.dal_from_severity("Minor"), "D")
        self.assertEqual(dal.dal_from_severity("No safety effect"), "E")

    def test_reverse_mapping(self):
        self.assertEqual(dal.severity_from_dal("A"), "Catastrophic")
        self.assertEqual(dal.severity_from_dal("B"), "Hazardous")
        self.assertEqual(dal.severity_from_dal("C"), "Major")
        self.assertEqual(dal.severity_from_dal("D"), "Minor")
        self.assertEqual(dal.severity_from_dal("E"), "No safety effect")

    def test_unknown_severity_raises(self):
        for bad in ("Severe", "catastrophic", "", None, 3, "F"):
            with self.assertRaises(ValueError):
                dal.dal_from_severity(bad)
            with self.assertRaises(ValueError):
                dal.severity_rank(bad)

    def test_unknown_dal_raises(self):
        for bad in ("F", "AA", "a", "", None, 1):
            with self.assertRaises(ValueError):
                dal.severity_from_dal(bad)
            with self.assertRaises(ValueError):
                dal.dal_index(bad)


class RankTest(unittest.TestCase):
    def test_severity_rank_anchors(self):
        # 5 = most severe down to 1 = no safety effect.
        self.assertEqual(dal.severity_rank("Catastrophic"), 5)
        self.assertEqual(dal.severity_rank("Hazardous"), 4)
        self.assertEqual(dal.severity_rank("Major"), 3)
        self.assertEqual(dal.severity_rank("Minor"), 2)
        self.assertEqual(dal.severity_rank("No safety effect"), 1)

    def test_dal_index_anchors(self):
        # A = highest assurance down to E = 1.
        self.assertEqual(dal.dal_index("A"), 5)
        self.assertEqual(dal.dal_index("B"), 4)
        self.assertEqual(dal.dal_index("C"), 3)
        self.assertEqual(dal.dal_index("D"), 2)
        self.assertEqual(dal.dal_index("E"), 1)


class PropagationTest(unittest.TestCase):
    def test_item_at_or_above_function_passes(self):
        self.assertTrue(dal.validate_dal_propagation("A", "A"))
        self.assertTrue(dal.validate_dal_propagation("B", "B"))
        self.assertTrue(dal.validate_dal_propagation("C", "A"))
        self.assertTrue(dal.validate_dal_propagation("B", "A"))
        self.assertTrue(dal.validate_dal_propagation("E", "A"))

    def test_item_below_function_raises(self):
        # An item DAL lower than the function DAL is a violation.
        with self.assertRaises(ValueError):
            dal.validate_dal_propagation("A", "C")
        with self.assertRaises(ValueError):
            dal.validate_dal_propagation("B", "D")
        with self.assertRaises(ValueError):
            dal.validate_dal_propagation("C", "E")

    def test_unknown_levels_raise(self):
        with self.assertRaises(ValueError):
            dal.validate_dal_propagation("F", "A")
        with self.assertRaises(ValueError):
            dal.validate_dal_propagation("A", "F")
        with self.assertRaises(ValueError):
            dal.validate_dal_propagation("A", 3)


class IndependenceTest(unittest.TestCase):
    def test_no_reduction_needs_no_justification(self):
        self.assertTrue(
            dal.independence_justifies_lower_item_dal("A", "A", False))
        self.assertTrue(
            dal.independence_justifies_lower_item_dal("C", "A", False))

    def test_lower_item_dal_requires_independence(self):
        # Without a validated independence argument the reduction fails.
        self.assertFalse(
            dal.independence_justifies_lower_item_dal("A", "C", False))
        self.assertFalse(
            dal.independence_justifies_lower_item_dal("B", "D", False))
        # With independence established the reduction is accepted.
        self.assertTrue(
            dal.independence_justifies_lower_item_dal("A", "C", True))
        self.assertTrue(
            dal.independence_justifies_lower_item_dal("B", "D", True))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dal.independence_justifies_lower_item_dal("A", "C", "yes")
        with self.assertRaises(ValueError):
            dal.independence_justifies_lower_item_dal("A", "C", 1)
        with self.assertRaises(ValueError):
            dal.independence_justifies_lower_item_dal("F", "A", True)


class AssignmentTest(unittest.TestCase):
    def test_catastrophic_function_anchor(self):
        # Autopilot loss of all pitch authority rates catastrophic,
        # FDAL A, items start at IDAL A.
        record = dal.assurance_assignment(
            "Autopilot", "Loss of all pitch authority", "Catastrophic")
        self.assertEqual(record["function"], "Autopilot")
        self.assertEqual(record["failure_condition"],
                         "Loss of all pitch authority")
        self.assertEqual(record["severity"], "Catastrophic")
        self.assertEqual(record["fdal"], "A")
        self.assertEqual(record["idal"], "A")
        self.assertTrue(record["propagation_ok"])
        self.assertFalse(record["independence_established"])

    def test_hazardous_function_anchor(self):
        record = dal.assurance_assignment(
            "Thrust Reverser", "Inadvertent deployment in flight",
            "Hazardous")
        self.assertEqual(record["fdal"], "B")
        self.assertEqual(record["idal"], "B")
        self.assertTrue(record["propagation_ok"])

    def test_no_safety_effect_anchor(self):
        record = dal.assurance_assignment(
            "Cabin Lighting", "Loss of cabin lighting", "Minor")
        self.assertEqual(record["fdal"], "D")
        record = dal.assurance_assignment(
            "Cabin Lighting", "Slight flicker", "No safety effect")
        self.assertEqual(record["fdal"], "E")

    def test_independence_flag_recorded(self):
        record = dal.assurance_assignment(
            "Autopilot", "Loss of all pitch authority", "Catastrophic",
            independence_established=True)
        self.assertTrue(record["independence_established"])
        self.assertEqual(record["idal"], "A")  # initial IDAL unchanged

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dal.assurance_assignment("", "Loss of all pitch authority",
                                     "Catastrophic")
        with self.assertRaises(ValueError):
            dal.assurance_assignment("Autopilot", "  ", "Catastrophic")
        with self.assertRaises(ValueError):
            dal.assurance_assignment("Autopilot", "Loss of all pitch",
                                     "Severe")
        with self.assertRaises(ValueError):
            dal.assurance_assignment("Autopilot", "Loss of all pitch",
                                     "Catastrophic", independence_established="yes")


if __name__ == "__main__":
    unittest.main(verbosity=2)

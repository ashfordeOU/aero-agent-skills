#!/usr/bin/env python3
"""Gate 3 contract test: N2 interface diagram.

Exercises scripts/n2_diagram_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (NxN interface matrix from
the element list and interface pairs; interface count per element
from row and column sums; total interface entries; missing data
links against a required pair list; isolated elements; ASCII
rendering; invalid inputs raise ValueError).

Anchors:
- build_matrix(["A","B","C"], [("A","B"),("B","C"),("A","C")]) =
  [[0,1,1],[0,0,1],[0,0,0]]
- interface_counts: A = 2, B = 2, C = 2 (each touches two interfaces)
- total_interfaces = 3
- duplicate pair ("A","B") twice gives cell [0][1] = 2 and counts
  A = 2, B = 2, C = 0
- missing_links with required [("C","A")] returns [("C","A")]
- isolated_elements(["A","B","D"], interfaces [("A","B")]) = ["D"]
- render_matrix output contains every element name and cell digit
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import n2_diagram_logic as n2d  # noqa: E402


class BuildMatrixTest(unittest.TestCase):
    def test_anchor_matrix(self):
        matrix = n2d.build_matrix(["A", "B", "C"], [("A", "B"), ("B", "C"), ("A", "C")])
        self.assertEqual(matrix, [[0, 1, 1], [0, 0, 1], [0, 0, 0]])

    def test_duplicate_pairs_count(self):
        # Two interface entries on the same pair accumulate in the cell.
        matrix = n2d.build_matrix(["A", "B"], [("A", "B"), ("A", "B")])
        self.assertEqual(matrix[0][1], 2)
        self.assertEqual(matrix[1][0], 0)

    def test_empty_interfaces_zero_matrix(self):
        matrix = n2d.build_matrix(["A", "B", "C"], [])
        self.assertEqual(matrix, [[0, 0, 0], [0, 0, 0], [0, 0, 0]])

    def test_self_interface_raises(self):
        with self.assertRaises(ValueError):
            n2d.build_matrix(["A", "B"], [("A", "A")])

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            n2d.build_matrix(["A", "B"], [("A", "Z")])
        with self.assertRaises(ValueError):
            n2d.build_matrix(["A", "B"], [("Z", "A")])

    def test_empty_elements_raises(self):
        with self.assertRaises(ValueError):
            n2d.build_matrix([], [("A", "B")])

    def test_duplicate_elements_raises(self):
        with self.assertRaises(ValueError):
            n2d.build_matrix(["A", "A"], [("A", "B")])

    def test_non_string_element_raises(self):
        with self.assertRaises(ValueError):
            n2d.build_matrix(["A", 1], [("A", "B")])


class InterfaceCountsTest(unittest.TestCase):
    def test_anchor_counts(self):
        matrix = n2d.build_matrix(["A", "B", "C"], [("A", "B"), ("B", "C"), ("A", "C")])
        counts = n2d.interface_counts(["A", "B", "C"], matrix)
        self.assertEqual(counts, {"A": 2, "B": 2, "C": 2})

    def test_duplicate_pair_counts(self):
        # Two entries A to B: A counts 2 (outgoing), B counts 2 (incoming).
        matrix = n2d.build_matrix(["A", "B"], [("A", "B"), ("A", "B")])
        counts = n2d.interface_counts(["A", "B"], matrix)
        self.assertEqual(counts, {"A": 2, "B": 2})

    def test_isolated_element_zero_count(self):
        matrix = n2d.build_matrix(["A", "B", "D"], [("A", "B")])
        counts = n2d.interface_counts(["A", "B", "D"], matrix)
        self.assertEqual(counts, {"A": 1, "B": 1, "D": 0})

    def test_invalid_matrix_raises(self):
        with self.assertRaises(ValueError):
            n2d.interface_counts(["A", "B"], [[0, 1]])
        with self.assertRaises(ValueError):
            n2d.interface_counts(["A", "B"], [[0, -1], [0, 0]])
        with self.assertRaises(ValueError):
            n2d.interface_counts(["A", "B"], [[0, "x"], [0, 0]])


class TotalInterfacesTest(unittest.TestCase):
    def test_anchor_total(self):
        matrix = n2d.build_matrix(["A", "B", "C"], [("A", "B"), ("B", "C"), ("A", "C")])
        self.assertEqual(n2d.total_interfaces(["A", "B", "C"], matrix), 3)

    def test_empty_total_zero(self):
        matrix = n2d.build_matrix(["A", "B"], [])
        self.assertEqual(n2d.total_interfaces(["A", "B"], matrix), 0)

    def test_duplicate_total(self):
        matrix = n2d.build_matrix(["A", "B"], [("A", "B"), ("A", "B")])
        self.assertEqual(n2d.total_interfaces(["A", "B"], matrix), 2)


class MissingLinksTest(unittest.TestCase):
    def test_anchor_missing(self):
        matrix = n2d.build_matrix(["A", "B", "C"], [("A", "B"), ("B", "C"), ("A", "C")])
        missing = n2d.missing_links(["A", "B", "C"], matrix, [("C", "A")])
        self.assertEqual(missing, [("C", "A")])

    def test_all_required_present(self):
        matrix = n2d.build_matrix(["A", "B"], [("A", "B")])
        missing = n2d.missing_links(["A", "B"], matrix, [("A", "B")])
        self.assertEqual(missing, [])

    def test_no_required_pairs(self):
        matrix = n2d.build_matrix(["A", "B"], [("A", "B")])
        self.assertEqual(n2d.missing_links(["A", "B"], matrix, []), [])

    def test_missing_raises_unknown_element(self):
        matrix = n2d.build_matrix(["A", "B"], [("A", "B")])
        with self.assertRaises(ValueError):
            n2d.missing_links(["A", "B"], matrix, [("A", "Z")])


class IsolatedElementsTest(unittest.TestCase):
    def test_anchor_isolated(self):
        matrix = n2d.build_matrix(["A", "B", "D"], [("A", "B")])
        self.assertEqual(n2d.isolated_elements(["A", "B", "D"], matrix), ["D"])

    def test_no_isolated_elements(self):
        matrix = n2d.build_matrix(["A", "B"], [("A", "B")])
        self.assertEqual(n2d.isolated_elements(["A", "B"], matrix), [])

    def test_all_isolated(self):
        matrix = n2d.build_matrix(["A", "B"], [])
        self.assertEqual(n2d.isolated_elements(["A", "B"], matrix), ["A", "B"])


class RenderMatrixTest(unittest.TestCase):
    def test_render_has_header(self):
        matrix = n2d.build_matrix(["A", "B", "C"], [("A", "B"), ("B", "C"), ("A", "C")])
        text = n2d.render_matrix(["A", "B", "C"], matrix)
        self.assertIn("A", text)
        self.assertIn("B", text)
        self.assertIn("C", text)

    def test_render_rows_and_cells(self):
        matrix = n2d.build_matrix(["A", "B"], [("A", "B")])
        text = n2d.render_matrix(["A", "B"], matrix)
        lines = text.splitlines()
        self.assertEqual(len(lines), 3)  # header plus two element rows
        self.assertIn("1", lines[1])  # row A carries the A to B link


class FcsScenarioTest(unittest.TestCase):
    """Flight control system functions with one missing feedback link."""

    ELEMENTS = ["pilot-input", "flight-control-computer", "sensor", "air-data", "actuator"]

    INTERFACES = [
        ("sensor", "flight-control-computer"),
        ("air-data", "flight-control-computer"),
        ("pilot-input", "flight-control-computer"),
        ("flight-control-computer", "actuator"),
    ]

    def test_fcs_matrix_cells(self):
        matrix = n2d.build_matrix(self.ELEMENTS, self.INTERFACES)
        self.assertEqual(len(matrix), 5)
        # sensor (2) to flight-control-computer (1)
        self.assertEqual(matrix[2][1], 1)
        # air-data (3) to flight-control-computer (1)
        self.assertEqual(matrix[3][1], 1)
        # pilot-input (0) to flight-control-computer (1)
        self.assertEqual(matrix[0][1], 1)
        # flight-control-computer (1) to actuator (4)
        self.assertEqual(matrix[1][4], 1)
        # actuator has no modeled outgoing link
        self.assertEqual(matrix[4], [0, 0, 0, 0, 0])

    def test_fcs_interface_counts(self):
        matrix = n2d.build_matrix(self.ELEMENTS, self.INTERFACES)
        counts = n2d.interface_counts(self.ELEMENTS, matrix)
        self.assertEqual(counts["flight-control-computer"], 4)  # 3 in, 1 out
        self.assertEqual(counts["sensor"], 1)
        self.assertEqual(counts["air-data"], 1)
        self.assertEqual(counts["pilot-input"], 1)
        self.assertEqual(counts["actuator"], 1)
        self.assertEqual(n2d.total_interfaces(self.ELEMENTS, matrix), 4)

    def test_fcs_missing_feedback_link(self):
        matrix = n2d.build_matrix(self.ELEMENTS, self.INTERFACES)
        required = [("actuator", "flight-control-computer"), ("sensor", "flight-control-computer")]
        missing = n2d.missing_links(self.ELEMENTS, matrix, required)
        self.assertEqual(missing, [("actuator", "flight-control-computer")])

    def test_fcs_no_isolated(self):
        matrix = n2d.build_matrix(self.ELEMENTS, self.INTERFACES)
        self.assertEqual(n2d.isolated_elements(self.ELEMENTS, matrix), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

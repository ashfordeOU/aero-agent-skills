#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex H function tree DRD.

Exercises scripts/e10_function_tree_drd_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a function name
is valid only when it opens with a bare action verb and an empty or
non-string name raises; a function tree must have exactly one top
function (node with parent_id None), every non-root parent reference
must resolve to an existing node, and every node must be reachable
from the top function or the tree is rejected as structurally
invalid; a full assessment flags a decomposition step that produces
only one child, an elementary (leaf) function missing a requirement
trace or an allocation, and a function name reused elsewhere in the
tree; a report with no findings is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_function_tree_drd_logic as ft  # noqa: E402


def make_compliant_tree():
    return [
        {"id": "F0", "parent_id": None, "name": "provide electrical power"},
        {
            "id": "F1",
            "parent_id": "F0",
            "name": "generate power",
            "requirements": ["REQ-01"],
            "allocated_to": "solar-array",
        },
        {
            "id": "F2",
            "parent_id": "F0",
            "name": "distribute power",
            "requirements": ["REQ-02"],
            "allocated_to": "pdu",
        },
    ]


class CheckFunctionNamingTest(unittest.TestCase):
    def test_bare_verb_passes(self):
        self.assertTrue(ft.check_function_naming("provide power"))

    def test_gerund_fails(self):
        self.assertFalse(ft.check_function_naming("providing power"))

    def test_unrecognized_verb_fails(self):
        self.assertFalse(ft.check_function_naming("does power"))

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            ft.check_function_naming("")

    def test_non_string_name_raises(self):
        with self.assertRaises(ValueError):
            ft.check_function_naming(None)


class ValidateIdsUniqueTest(unittest.TestCase):
    def test_unique_ids_pass(self):
        nodes = [{"id": "F0"}, {"id": "F1"}]
        self.assertEqual(ft.validate_ids_unique(nodes), ["F0", "F1"])

    def test_duplicate_id_raises(self):
        nodes = [{"id": "F0"}, {"id": "F0"}]
        with self.assertRaises(ValueError):
            ft.validate_ids_unique(nodes)


class FindRootTest(unittest.TestCase):
    def test_single_root_found(self):
        nodes = [{"id": "F0", "parent_id": None}, {"id": "F1", "parent_id": "F0"}]
        self.assertEqual(ft.find_root(nodes), "F0")

    def test_no_root_raises(self):
        nodes = [{"id": "F0", "parent_id": "F1"}, {"id": "F1", "parent_id": "F0"}]
        with self.assertRaises(ValueError):
            ft.find_root(nodes)

    def test_multiple_roots_raises(self):
        nodes = [{"id": "F0", "parent_id": None}, {"id": "F1", "parent_id": None}]
        with self.assertRaises(ValueError):
            ft.find_root(nodes)


class ValidateParentRefsTest(unittest.TestCase):
    def test_resolvable_parent_passes(self):
        nodes = [{"id": "F0", "parent_id": None}, {"id": "F1", "parent_id": "F0"}]
        ft.validate_parent_refs(nodes, "F0")  # no raise

    def test_dangling_parent_raises(self):
        nodes = [{"id": "F0", "parent_id": None}, {"id": "F1", "parent_id": "F9"}]
        with self.assertRaises(ValueError):
            ft.validate_parent_refs(nodes, "F0")


class ValidateTreeStructureTest(unittest.TestCase):
    def test_empty_tree_raises(self):
        with self.assertRaises(ValueError):
            ft.validate_tree_structure([])

    def test_disconnected_branch_raises(self):
        nodes = [
            {"id": "F0", "parent_id": None},
            {"id": "F1", "parent_id": "F2"},
            {"id": "F2", "parent_id": "F1"},
        ]
        with self.assertRaises(ValueError):
            ft.validate_tree_structure(nodes)

    def test_valid_tree_returns_root_and_children(self):
        nodes = make_compliant_tree()
        root_id, children_index = ft.validate_tree_structure(nodes)
        self.assertEqual(root_id, "F0")
        self.assertEqual(sorted(children_index["F0"]), ["F1", "F2"])


class AssessFunctionTreeTest(unittest.TestCase):
    def test_compliant_tree_has_no_findings(self):
        report = ft.assess_function_tree(make_compliant_tree())
        self.assertEqual(report["root_id"], "F0")
        self.assertEqual(report["leaf_ids"], ["F1", "F2"])
        self.assertEqual(report["findings"], [])
        self.assertTrue(ft.is_function_tree_compliant(report))

    def test_single_child_decomposition_flagged(self):
        nodes = [
            {"id": "F0", "parent_id": None, "name": "provide power"},
            {
                "id": "F1",
                "parent_id": "F0",
                "name": "generate power",
                "requirements": ["REQ-01"],
                "allocated_to": "solar-array",
            },
        ]
        report = ft.assess_function_tree(nodes)
        issues = [f["issue"] for f in report["findings"]]
        self.assertIn("single_child_decomposition", issues)

    def test_missing_requirement_trace_flagged(self):
        nodes = make_compliant_tree()
        del nodes[1]["requirements"]
        report = ft.assess_function_tree(nodes)
        self.assertIn(
            {"issue": "missing_requirement_trace", "function_id": "F1"},
            report["findings"],
        )

    def test_missing_allocation_flagged(self):
        nodes = make_compliant_tree()
        nodes[2]["allocated_to"] = None
        report = ft.assess_function_tree(nodes)
        self.assertIn(
            {"issue": "missing_allocation", "function_id": "F2"}, report["findings"]
        )

    def test_naming_violation_flagged(self):
        nodes = make_compliant_tree()
        nodes[1]["name"] = "generating power"
        report = ft.assess_function_tree(nodes)
        issues = [f["issue"] for f in report["findings"]]
        self.assertIn("naming_violation", issues)
        self.assertFalse(ft.is_function_tree_compliant(report))

    def test_duplicate_function_name_flagged(self):
        nodes = make_compliant_tree()
        nodes[2]["name"] = "generate power"
        report = ft.assess_function_tree(nodes)
        issues = [f["issue"] for f in report["findings"]]
        self.assertIn("duplicate_function_name", issues)

    def test_malformed_name_raises(self):
        nodes = make_compliant_tree()
        nodes[1]["name"] = ""
        with self.assertRaises(ValueError):
            ft.assess_function_tree(nodes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

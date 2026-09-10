#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C specification tree check.

Exercises scripts/e10_spec_tree_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a specification tree mirrors
the product tree with one spec per node, support specs included; the
tree is consistent only when there are no orphan specs (spec node not in
the product tree), no duplicate specs (more than one spec per node), no
missing specs (product-tree node with no spec), and no parent-link
mismatches (spec's declared parent differs from the product tree's
actual parent for that node).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_spec_tree_logic as st  # noqa: E402


PRODUCT_TREE = {
    "spacecraft": None,
    "platform": "spacecraft",
    "payload": "spacecraft",
    "gse": "spacecraft",
}

CONSISTENT_SPECS = [
    {"node": "spacecraft", "spec_id": "TS-000", "parent": None},
    {"node": "platform", "spec_id": "TS-100", "parent": "spacecraft"},
    {"node": "payload", "spec_id": "TS-200", "parent": "spacecraft"},
    {"node": "gse", "spec_id": "TS-900", "parent": "spacecraft"},
]


class OrphanSpecsTest(unittest.TestCase):
    def test_no_orphans_when_all_nodes_known(self):
        self.assertEqual(st.orphan_specs(PRODUCT_TREE, CONSISTENT_SPECS), [])

    def test_orphan_reported(self):
        specs = CONSISTENT_SPECS + [
            {"node": "not-in-tree", "spec_id": "TS-999", "parent": "spacecraft"},
        ]
        orphans = st.orphan_specs(PRODUCT_TREE, specs)
        self.assertEqual([s["node"] for s in orphans], ["not-in-tree"])


class DuplicateSpecNodesTest(unittest.TestCase):
    def test_no_duplicates(self):
        self.assertEqual(st.duplicate_spec_nodes(CONSISTENT_SPECS), [])

    def test_duplicate_reported_once_first_seen_order(self):
        specs = CONSISTENT_SPECS + [
            {"node": "platform", "spec_id": "TS-101", "parent": "spacecraft"},
        ]
        self.assertEqual(st.duplicate_spec_nodes(specs), ["platform"])


class MissingSpecNodesTest(unittest.TestCase):
    def test_no_missing_when_fully_covered(self):
        self.assertEqual(st.missing_spec_nodes(PRODUCT_TREE, CONSISTENT_SPECS), [])

    def test_missing_reported_in_tree_order(self):
        specs = [s for s in CONSISTENT_SPECS if s["node"] != "gse"]
        self.assertEqual(st.missing_spec_nodes(PRODUCT_TREE, specs), ["gse"])


class ParentMismatchesTest(unittest.TestCase):
    def test_no_mismatches_when_parents_match(self):
        self.assertEqual(st.parent_mismatches(PRODUCT_TREE, CONSISTENT_SPECS), [])

    def test_mismatch_reported(self):
        specs = [dict(s) for s in CONSISTENT_SPECS]
        specs[2]["parent"] = "platform"  # payload's spec wrongly parented under platform
        mismatches = st.parent_mismatches(PRODUCT_TREE, specs)
        self.assertEqual(mismatches, [("payload", "platform", "spacecraft")])

    def test_orphan_and_duplicate_nodes_skipped(self):
        specs = CONSISTENT_SPECS + [
            {"node": "platform", "spec_id": "TS-101", "parent": "wrong-parent"},
            {"node": "not-in-tree", "spec_id": "TS-999", "parent": "wrong-parent"},
        ]
        self.assertEqual(st.parent_mismatches(PRODUCT_TREE, specs), [])


class TreeConsistentTest(unittest.TestCase):
    def test_consistent_tree(self):
        consistent, violations = st.tree_consistent(PRODUCT_TREE, CONSISTENT_SPECS)
        self.assertTrue(consistent)
        self.assertEqual(
            violations,
            {"orphans": [], "duplicates": [], "missing": [], "parent_mismatches": []},
        )

    def test_inconsistent_tree_lists_every_violation_kind(self):
        specs = [
            {"node": "spacecraft", "spec_id": "TS-000", "parent": None},
            {"node": "platform", "spec_id": "TS-100", "parent": "spacecraft"},
            {"node": "platform", "spec_id": "TS-101", "parent": "wrong-parent"},
            {"node": "not-in-tree", "spec_id": "TS-999", "parent": "spacecraft"},
        ]
        consistent, violations = st.tree_consistent(PRODUCT_TREE, specs)
        self.assertFalse(consistent)
        self.assertEqual(violations["duplicates"], ["platform"])
        self.assertEqual([s["node"] for s in violations["orphans"]], ["not-in-tree"])
        self.assertEqual(sorted(violations["missing"]), ["gse", "payload"])
        self.assertEqual(violations["parent_mismatches"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)

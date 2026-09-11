#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §8.2.8 requirement-set
completeness assessment.

Exercises scripts/e1006_char_completeness_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 -- the tree builder
rejects an empty node list, a duplicate node ID, and a parent_id that
does not resolve; find_leaf_nodes returns only bottom-level nodes;
check_completeness marks a leaf covered only by a direct trace to that
leaf (not to its parent); a requirement with an empty or fully-invalid
trace list is flagged as an orphan; a trace to a nonexistent node is
recorded as an invalid trace pair; is_complete is True only when all
three finding lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1006_char_completeness_logic as cc  # noqa: E402


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _node(node_id, parent_id=None):
    return {"node_id": node_id, "parent_id": parent_id}


def _req(req_id, trace_to=None):
    return {"req_id": req_id, "trace_to": trace_to or []}


# ---------------------------------------------------------------------------
# tree building
# ---------------------------------------------------------------------------

class BuildTreeTest(unittest.TestCase):
    def test_empty_node_list_raises(self):
        with self.assertRaises(ValueError):
            cc.check_completeness([], [])

    def test_duplicate_node_id_raises(self):
        nodes = [_node("A"), _node("A")]
        with self.assertRaises(ValueError):
            cc.check_completeness(nodes, [])

    def test_unknown_parent_id_raises(self):
        nodes = [_node("A", parent_id="GHOST")]
        with self.assertRaises(ValueError):
            cc.check_completeness(nodes, [])

    def test_blank_node_id_raises(self):
        nodes = [_node("")]
        with self.assertRaises(ValueError):
            cc.check_completeness(nodes, [])


# ---------------------------------------------------------------------------
# leaf detection
# ---------------------------------------------------------------------------

class FindLeafNodesTest(unittest.TestCase):
    def test_single_node_is_leaf(self):
        tree = cc._build_tree([_node("ROOT")])
        self.assertEqual(cc.find_leaf_nodes(tree), ["ROOT"])

    def test_parent_is_not_leaf(self):
        tree = cc._build_tree([_node("ROOT"), _node("CHILD", parent_id="ROOT")])
        leaves = cc.find_leaf_nodes(tree)
        self.assertNotIn("ROOT", leaves)
        self.assertIn("CHILD", leaves)

    def test_two_siblings_both_leaves(self):
        nodes = [
            _node("ROOT"),
            _node("L1", parent_id="ROOT"),
            _node("L2", parent_id="ROOT"),
        ]
        tree = cc._build_tree(nodes)
        leaves = cc.find_leaf_nodes(tree)
        self.assertCountEqual(leaves, ["L1", "L2"])

    def test_deep_tree_only_bottom_leaf(self):
        nodes = [_node("A"), _node("B", parent_id="A"), _node("C", parent_id="B")]
        tree = cc._build_tree(nodes)
        self.assertEqual(cc.find_leaf_nodes(tree), ["C"])


# ---------------------------------------------------------------------------
# check_completeness — happy paths
# ---------------------------------------------------------------------------

class CompleteAssessmentTest(unittest.TestCase):
    def test_single_node_tree_covered(self):
        nodes = [_node("F1")]
        reqs = [_req("REQ-1", ["F1"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertTrue(result.is_complete)
        self.assertEqual(result.uncovered_leaves, [])
        self.assertEqual(result.orphan_requirements, [])
        self.assertEqual(result.invalid_traces, [])

    def test_all_leaves_covered_is_complete(self):
        nodes = [
            _node("ROOT"),
            _node("F1", parent_id="ROOT"),
            _node("F2", parent_id="ROOT"),
        ]
        reqs = [
            _req("REQ-1", ["F1"]),
            _req("REQ-2", ["F2"]),
        ]
        result = cc.check_completeness(nodes, reqs)
        self.assertTrue(result.is_complete)

    def test_multiple_requirements_covering_same_leaf_is_complete(self):
        nodes = [_node("ROOT"), _node("F1", parent_id="ROOT")]
        reqs = [_req("REQ-1", ["F1"]), _req("REQ-2", ["F1"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertTrue(result.is_complete)

    def test_no_requirements_and_no_leaves_raises(self):
        with self.assertRaises(ValueError):
            cc.check_completeness([], [])


# ---------------------------------------------------------------------------
# check_completeness — gap detection
# ---------------------------------------------------------------------------

class UncoveredLeafTest(unittest.TestCase):
    def test_single_node_tree_uncovered(self):
        nodes = [_node("F1")]
        result = cc.check_completeness(nodes, [])
        self.assertFalse(result.is_complete)
        self.assertIn("F1", result.uncovered_leaves)

    def test_one_leaf_uncovered_out_of_two(self):
        nodes = [
            _node("ROOT"),
            _node("F1", parent_id="ROOT"),
            _node("F2", parent_id="ROOT"),
        ]
        reqs = [_req("REQ-1", ["F1"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertFalse(result.is_complete)
        self.assertIn("F2", result.uncovered_leaves)
        self.assertNotIn("F1", result.uncovered_leaves)

    def test_multiple_leaves_all_uncovered(self):
        nodes = [
            _node("ROOT"),
            _node("F1", parent_id="ROOT"),
            _node("F2", parent_id="ROOT"),
            _node("F3", parent_id="ROOT"),
        ]
        result = cc.check_completeness(nodes, [])
        self.assertFalse(result.is_complete)
        self.assertCountEqual(result.uncovered_leaves, ["F1", "F2", "F3"])

    def test_trace_to_parent_does_not_cover_leaf(self):
        nodes = [
            _node("ROOT"),
            _node("F1", parent_id="ROOT"),
        ]
        reqs = [_req("REQ-1", ["ROOT"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertIn("F1", result.uncovered_leaves)
        self.assertFalse(result.is_complete)

    def test_deep_tree_only_leaf_coverage_counts(self):
        nodes = [
            _node("A"),
            _node("B", parent_id="A"),
            _node("C", parent_id="B"),
        ]
        reqs = [_req("REQ-1", ["C"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertTrue(result.is_complete)


# ---------------------------------------------------------------------------
# check_completeness — orphan requirements
# ---------------------------------------------------------------------------

class OrphanRequirementTest(unittest.TestCase):
    def test_requirement_with_empty_trace_is_orphan(self):
        nodes = [_node("F1")]
        reqs = [_req("REQ-ORPHAN", []), _req("REQ-GOOD", ["F1"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertIn("REQ-ORPHAN", result.orphan_requirements)
        self.assertNotIn("REQ-GOOD", result.orphan_requirements)

    def test_requirement_with_all_invalid_traces_is_orphan(self):
        nodes = [_node("F1")]
        reqs = [_req("REQ-X", ["GHOST1", "GHOST2"]), _req("REQ-GOOD", ["F1"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertIn("REQ-X", result.orphan_requirements)

    def test_requirement_with_partial_valid_trace_is_not_orphan(self):
        nodes = [_node("F1")]
        reqs = [_req("REQ-PARTIAL", ["F1", "GHOST"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertNotIn("REQ-PARTIAL", result.orphan_requirements)


# ---------------------------------------------------------------------------
# check_completeness — invalid trace references
# ---------------------------------------------------------------------------

class InvalidTraceTest(unittest.TestCase):
    def test_trace_to_nonexistent_node_recorded(self):
        nodes = [_node("F1")]
        reqs = [_req("REQ-1", ["GHOST"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertIn(("REQ-1", "GHOST"), result.invalid_traces)

    def test_valid_trace_not_in_invalid_list(self):
        nodes = [_node("F1")]
        reqs = [_req("REQ-1", ["F1"])]
        result = cc.check_completeness(nodes, reqs)
        self.assertEqual(result.invalid_traces, [])


# ---------------------------------------------------------------------------
# check_completeness — mixed findings
# ---------------------------------------------------------------------------

class MixedFindingsTest(unittest.TestCase):
    def test_all_three_finding_types_reported_together(self):
        nodes = [
            _node("ROOT"),
            _node("F1", parent_id="ROOT"),
            _node("F2", parent_id="ROOT"),
        ]
        reqs = [
            _req("REQ-COVERS-F1", ["F1"]),
            _req("REQ-ORPHAN", []),
            _req("REQ-BAD-TRACE", ["DOES_NOT_EXIST"]),
        ]
        result = cc.check_completeness(nodes, reqs)
        self.assertFalse(result.is_complete)
        self.assertIn("F2", result.uncovered_leaves)
        self.assertIn("REQ-ORPHAN", result.orphan_requirements)
        self.assertIn(("REQ-BAD-TRACE", "DOES_NOT_EXIST"), result.invalid_traces)


if __name__ == "__main__":
    unittest.main(verbosity=2)

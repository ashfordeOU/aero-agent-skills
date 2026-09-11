#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-spec-tree-drd (stdlib unittest, offline)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_spec_tree_drd_logic import (  # noqa: E402
    LEVEL_OF_KIND, SPEC_KINDS, assess_spec_tree, build_children,
    find_root, flowdown_violations, is_spec_tree_compliant, level_of,
    level_violations, product_coverage_violations, unreachable_specs,
    validate_parent_refs, validate_spec_kind, validate_unique_ids,
)


def spec(sid, parent, kind, node, flow=None):
    return {"spec_id": sid, "parent_id": parent, "kind": kind,
            "specifies": node, "flowdown_from": flow if flow else parent}


def good_tree():
    return [
        spec("SYS-SPEC", None, "system", "SAT"),
        spec("AOCS-SPEC", "SYS-SPEC", "subsystem", "AOCS"),
        spec("EPS-SPEC", "SYS-SPEC", "subsystem", "EPS"),
        spec("RW-SPEC", "AOCS-SPEC", "equipment", "RW"),
    ]


GOOD_NODES = ["SAT", "AOCS", "EPS", "RW"]


class KindTest(unittest.TestCase):
    def test_every_declared_kind_has_a_level(self):
        for k in SPEC_KINDS:
            self.assertIn(k, LEVEL_OF_KIND)

    def test_levels_descend_by_one(self):
        self.assertEqual(level_of("system"), 0)
        self.assertEqual(level_of("subsystem"), 1)
        self.assertEqual(level_of("equipment"), 2)

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_spec_kind("module")


class StructureTest(unittest.TestCase):
    def test_unique_ids_returns_them_in_order(self):
        self.assertEqual(validate_unique_ids(good_tree())[0], "SYS-SPEC")

    def test_duplicate_id_raises(self):
        t = good_tree() + [spec("RW-SPEC", "AOCS-SPEC", "equipment", "RW2")]
        with self.assertRaises(ValueError):
            validate_unique_ids(t)

    def test_missing_spec_id_raises(self):
        with self.assertRaises(ValueError):
            validate_unique_ids([{"parent_id": None, "kind": "system"}])

    def test_single_root_found(self):
        self.assertEqual(find_root(good_tree()), "SYS-SPEC")

    def test_two_roots_raise(self):
        t = good_tree() + [spec("OTHER", None, "system", "OTHER")]
        with self.assertRaises(ValueError):
            find_root(t)

    def test_no_root_raises(self):
        t = [spec("A", "B", "subsystem", "X"), spec("B", "A", "subsystem", "Y")]
        with self.assertRaises(ValueError):
            find_root(t)

    def test_unknown_parent_raises(self):
        t = good_tree() + [spec("Z-SPEC", "NOPE", "equipment", "Z")]
        ids = [s["spec_id"] for s in t]
        with self.assertRaises(ValueError):
            validate_parent_refs(t, ids)

    def test_children_index_lists_direct_children(self):
        idx = build_children(good_tree())
        self.assertEqual(sorted(idx["SYS-SPEC"]), ["AOCS-SPEC", "EPS-SPEC"])
        self.assertEqual(idx["RW-SPEC"], [])

    def test_detached_branch_is_unreachable(self):
        t = good_tree()
        t.append(spec("X1", "X2", "equipment", "X1N"))
        t.append(spec("X2", "X1", "subsystem", "X2N"))
        idx = build_children(t)
        self.assertEqual(sorted(unreachable_specs(t, "SYS-SPEC", idx)), ["X1", "X2"])

    def test_connected_tree_has_nothing_unreachable(self):
        t = good_tree()
        self.assertEqual(unreachable_specs(t, "SYS-SPEC", build_children(t)), [])


class ContentTest(unittest.TestCase):
    def test_level_skip_is_reported(self):
        t = good_tree()
        t.append(spec("PART-SPEC", "SYS-SPEC", "part", "P1"))
        issues = [f["issue"] for f in level_violations(t)]
        self.assertIn("level_skip", issues)

    def test_root_that_is_not_system_level_is_reported(self):
        t = [spec("SUB", None, "subsystem", "AOCS")]
        self.assertEqual(level_violations(t)[0]["issue"], "root_not_system_level")

    def test_clean_tree_has_no_level_findings(self):
        self.assertEqual(level_violations(good_tree()), [])

    def test_unspecified_product_node_is_reported(self):
        v = product_coverage_violations(good_tree(), GOOD_NODES + ["GNSS"])
        self.assertIn({"node": "GNSS", "issue": "unspecified_product"}, v)

    def test_product_specified_twice_is_reported(self):
        t = good_tree() + [spec("RW-SPEC-2", "AOCS-SPEC", "equipment", "RW")]
        issues = [f["issue"] for f in product_coverage_violations(t, GOOD_NODES)]
        self.assertIn("multiply_specified_product", issues)

    def test_specification_naming_no_product_is_reported(self):
        t = good_tree()
        t[3]["specifies"] = ""
        issues = [f["issue"] for f in product_coverage_violations(t, GOOD_NODES)]
        self.assertIn("no_product_node", issues)

    def test_missing_flowdown_link_is_reported(self):
        t = good_tree()
        t[1]["flowdown_from"] = None
        issues = [f["issue"] for f in flowdown_violations(t, "SYS-SPEC")]
        self.assertIn("no_flowdown_link", issues)

    def test_flowdown_pointing_away_from_parent_is_reported(self):
        t = good_tree()
        t[3]["flowdown_from"] = "EPS-SPEC"
        issues = [f["issue"] for f in flowdown_violations(t, "SYS-SPEC")]
        self.assertIn("flowdown_parent_mismatch", issues)

    def test_root_needs_no_flowdown_link(self):
        self.assertEqual(flowdown_violations(good_tree(), "SYS-SPEC"), [])


class AssessmentTest(unittest.TestCase):
    def test_clean_tree_is_compliant(self):
        r = assess_spec_tree(good_tree(), GOOD_NODES)
        self.assertEqual(r["root_id"], "SYS-SPEC")
        self.assertTrue(is_spec_tree_compliant(r))

    def test_gap_makes_it_non_compliant(self):
        r = assess_spec_tree(good_tree(), GOOD_NODES + ["TTC"])
        self.assertFalse(is_spec_tree_compliant(r))

    def test_empty_tree_raises(self):
        with self.assertRaises(ValueError):
            assess_spec_tree([], GOOD_NODES)

    def test_structural_defect_raises_rather_than_reporting(self):
        t = good_tree() + [spec("SYS-SPEC", "AOCS-SPEC", "equipment", "DUP")]
        with self.assertRaises(ValueError):
            assess_spec_tree(t, GOOD_NODES)

    def test_assessment_does_not_mutate_input(self):
        t = good_tree()
        before = [dict(s) for s in t]
        assess_spec_tree(t, GOOD_NODES)
        self.assertEqual(t, before)


if __name__ == "__main__":
    unittest.main()

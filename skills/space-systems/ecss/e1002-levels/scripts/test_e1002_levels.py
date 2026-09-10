#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.3 verification
levels.

Exercises scripts/e1002_levels_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the equipment -> subsystem
-> element -> segment -> system hierarchy is fixed and ordered; a
product tree is validated for unknown levels, missing parents, and
parents that are not strictly above their child; a single-component
requirement is assigned its component's level; a multi-component
(interface) requirement is assigned the level of the closest common
ancestor; the level matrix covers every requirement id with no
duplicates; and a level cannot be reported ready to close while a
requirement at or beneath it is unverified.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_levels_logic as lv  # noqa: E402


# Product tree used across tests:
#   SYS (system)
#     SEG-A (segment, parent SYS)
#       ELE-1 (element, parent SEG-A)
#         SUB-1 (subsystem, parent ELE-1)
#           EQ-1 (equipment, parent SUB-1)
#           EQ-2 (equipment, parent SUB-1)
#         SUB-2 (subsystem, parent ELE-1)
#           EQ-3 (equipment, parent SUB-2)
TREE = {
    "SYS": {"level": "system", "parent": None},
    "SEG-A": {"level": "segment", "parent": "SYS"},
    "ELE-1": {"level": "element", "parent": "SEG-A"},
    "SUB-1": {"level": "subsystem", "parent": "ELE-1"},
    "SUB-2": {"level": "subsystem", "parent": "ELE-1"},
    "EQ-1": {"level": "equipment", "parent": "SUB-1"},
    "EQ-2": {"level": "equipment", "parent": "SUB-1"},
    "EQ-3": {"level": "equipment", "parent": "SUB-2"},
}


class LevelIndexTest(unittest.TestCase):
    def test_bottom_up_order(self):
        self.assertEqual(
            [lv.level_index(level) for level in lv.LEVELS],
            [0, 1, 2, 3, 4],
        )

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            lv.level_index("assembly")


class ValidateProductTreeTest(unittest.TestCase):
    def test_valid_tree_has_no_violations(self):
        self.assertEqual(lv.validate_product_tree(TREE), [])

    def test_unknown_level_flagged(self):
        tree = dict(TREE, BAD={"level": "assembly", "parent": "SUB-1"})
        violations = lv.validate_product_tree(tree)
        self.assertEqual(
            [v for v in violations if v["id"] == "BAD"],
            [{"id": "BAD", "issue": "unknown_level", "detail": "assembly"}],
        )

    def test_missing_parent_flagged(self):
        tree = dict(TREE, ORPHAN={"level": "equipment", "parent": "NOPE"})
        violations = lv.validate_product_tree(tree)
        self.assertIn(
            {"id": "ORPHAN", "issue": "missing_parent", "detail": "NOPE"},
            violations,
        )

    def test_parent_not_above_flagged(self):
        tree = dict(TREE, BACKWARDS={"level": "system", "parent": "EQ-1"})
        violations = lv.validate_product_tree(tree)
        self.assertIn(
            {"id": "BACKWARDS", "issue": "parent_not_above", "detail": "EQ-1"},
            violations,
        )

    def test_does_not_mutate_input(self):
        before = {cid: dict(node) for cid, node in TREE.items()}
        lv.validate_product_tree(TREE)
        self.assertEqual(TREE, before)


class AncestryChainTest(unittest.TestCase):
    def test_chain_to_root(self):
        self.assertEqual(
            lv.ancestry_chain("EQ-1", TREE),
            ["EQ-1", "SUB-1", "ELE-1", "SEG-A", "SYS"],
        )

    def test_root_chain_is_itself(self):
        self.assertEqual(lv.ancestry_chain("SYS", TREE), ["SYS"])

    def test_unknown_component_raises(self):
        with self.assertRaises(ValueError):
            lv.ancestry_chain("NOPE", TREE)

    def test_cycle_raises(self):
        cyclic = {
            "A": {"level": "equipment", "parent": "B"},
            "B": {"level": "subsystem", "parent": "A"},
        }
        with self.assertRaises(ValueError):
            lv.ancestry_chain("A", cyclic)


class RequirementLevelTest(unittest.TestCase):
    def test_component_level(self):
        self.assertEqual(lv.requirement_level("EQ-1", TREE), "equipment")

    def test_unknown_component_raises(self):
        with self.assertRaises(ValueError):
            lv.requirement_level("NOPE", TREE)


class CommonAncestorLevelTest(unittest.TestCase):
    def test_siblings_under_same_subsystem(self):
        self.assertEqual(
            lv.common_ancestor_level(["EQ-1", "EQ-2"], TREE),
            "subsystem",
        )

    def test_cousins_under_different_subsystems(self):
        self.assertEqual(
            lv.common_ancestor_level(["EQ-1", "EQ-3"], TREE),
            "element",
        )

    def test_ancestor_descendant_pair_uses_ancestors_own_level(self):
        self.assertEqual(
            lv.common_ancestor_level(["EQ-1", "SUB-1"], TREE),
            "subsystem",
        )

    def test_empty_components_raises(self):
        with self.assertRaises(ValueError):
            lv.common_ancestor_level([], TREE)

    def test_disconnected_components_raise(self):
        disjoint = dict(TREE, ISOLATED={"level": "equipment", "parent": None})
        with self.assertRaises(ValueError):
            lv.common_ancestor_level(["EQ-1", "ISOLATED"], disjoint)


class AssignRequirementLevelTest(unittest.TestCase):
    def test_single_component_requirement(self):
        requirement = {"id": "REQ-001", "components": ["EQ-1"]}
        self.assertEqual(lv.assign_requirement_level(requirement, TREE), "equipment")

    def test_interface_requirement(self):
        requirement = {"id": "REQ-002", "components": ["EQ-1", "EQ-3"]}
        self.assertEqual(lv.assign_requirement_level(requirement, TREE), "element")

    def test_no_components_raises(self):
        with self.assertRaises(ValueError):
            lv.assign_requirement_level({"id": "REQ-003", "components": []}, TREE)


class BuildLevelMatrixTest(unittest.TestCase):
    REQUIREMENTS = [
        {"id": "REQ-001", "components": ["EQ-1"]},
        {"id": "REQ-002", "components": ["EQ-1", "EQ-2"]},
        {"id": "REQ-003", "components": ["SYS"]},
    ]

    def test_matrix_order_and_content(self):
        matrix = lv.build_level_matrix(self.REQUIREMENTS, TREE)
        self.assertEqual(
            matrix,
            [
                {"id": "REQ-001", "level": "equipment"},
                {"id": "REQ-002", "level": "subsystem"},
                {"id": "REQ-003", "level": "system"},
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            lv.build_level_matrix(self.REQUIREMENTS + [self.REQUIREMENTS[0]], TREE)

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            lv.build_level_matrix([{"components": ["EQ-1"]}], TREE)

    def test_does_not_mutate_input(self):
        before = [dict(r) for r in self.REQUIREMENTS]
        lv.build_level_matrix(self.REQUIREMENTS, TREE)
        self.assertEqual(self.REQUIREMENTS, before)


class LevelGapsTest(unittest.TestCase):
    def test_detects_gap(self):
        matrix = [{"id": "REQ-001", "level": "equipment"}]
        self.assertEqual(
            lv.level_gaps(["REQ-001", "REQ-002"], matrix),
            ["REQ-002"],
        )

    def test_no_gap(self):
        matrix = [{"id": "REQ-001", "level": "equipment"}]
        self.assertEqual(lv.level_gaps(["REQ-001"], matrix), [])


class LevelClosureTest(unittest.TestCase):
    MATRIX = [
        {"id": "REQ-EQ", "level": "equipment"},
        {"id": "REQ-SUB", "level": "subsystem"},
        {"id": "REQ-SYS", "level": "system"},
    ]

    def test_requirements_at_or_below_subsystem(self):
        self.assertEqual(
            lv.requirements_at_or_below("subsystem", self.MATRIX),
            ["REQ-EQ", "REQ-SUB"],
        )

    def test_blocking_requirements_lists_unverified(self):
        self.assertEqual(
            lv.blocking_requirements("subsystem", self.MATRIX, verified_ids={"REQ-EQ"}),
            ["REQ-SUB"],
        )

    def test_level_not_ready_when_lower_level_open(self):
        self.assertFalse(
            lv.level_ready_to_close("subsystem", self.MATRIX, verified_ids={"REQ-SUB"})
        )

    def test_level_ready_when_all_at_or_below_verified(self):
        self.assertTrue(
            lv.level_ready_to_close(
                "subsystem", self.MATRIX, verified_ids={"REQ-EQ", "REQ-SUB"}
            )
        )

    def test_system_close_requires_every_requirement(self):
        self.assertFalse(
            lv.level_ready_to_close(
                "system", self.MATRIX, verified_ids={"REQ-EQ", "REQ-SUB"}
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

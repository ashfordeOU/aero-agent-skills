#!/usr/bin/env python3
"""Offline, deterministic unittest for e10_config_content_logic.py."""

import unittest

from e10_config_content_logic import (
    cyclic_nodes,
    dangling_parents,
    configuration_content_complete,
    invalid_precedence_nodes,
    leaf_nodes,
    leaf_nodes_without_function,
    nodes_missing_design_definition,
    orphan_function_allocations,
    precedence_cycle,
    unallocated_functions,
)


VALID_TREE = {
    "spacecraft": None,
    "platform": "spacecraft",
    "payload": "spacecraft",
    "power-unit": "platform",
    "sensor-head": "payload",
}


class DanglingParentsTests(unittest.TestCase):
    def test_flags_parent_outside_tree(self):
        tree = {"spacecraft": None, "platform": "phantom-node"}
        self.assertEqual(dangling_parents(tree), ["platform"])

    def test_empty_for_valid_tree(self):
        self.assertEqual(dangling_parents(VALID_TREE), [])

    def test_rejects_non_dict_input(self):
        with self.assertRaises(TypeError):
            dangling_parents(["not", "a", "dict"])


class CyclicNodesTests(unittest.TestCase):
    def test_detects_self_cycle(self):
        tree = {"a": "a"}
        self.assertEqual(cyclic_nodes(tree), ["a"])

    def test_detects_multi_node_cycle(self):
        tree = {"a": "b", "b": "c", "c": "a"}
        self.assertEqual(sorted(cyclic_nodes(tree)), ["a", "b", "c"])

    def test_empty_for_acyclic_tree(self):
        self.assertEqual(cyclic_nodes(VALID_TREE), [])

    def test_dangling_parent_not_reported_as_cycle(self):
        tree = {"a": "phantom"}
        self.assertEqual(cyclic_nodes(tree), [])


class LeafNodesTests(unittest.TestCase):
    def test_identifies_non_parent_nodes(self):
        self.assertEqual(
            sorted(leaf_nodes(VALID_TREE)),
            sorted(["power-unit", "sensor-head"]),
        )


class FunctionAllocationTests(unittest.TestCase):
    def test_unallocated_functions_reported(self):
        functions = {"power-generation": "power-unit", "attitude-sensing": None}
        self.assertEqual(unallocated_functions(functions), ["attitude-sensing"])

    def test_orphan_function_allocation_reported(self):
        functions = {"power-generation": "power-unit", "thermal-control": "ghost-node"}
        self.assertEqual(
            orphan_function_allocations(VALID_TREE, functions), ["thermal-control"]
        )

    def test_leaf_nodes_without_function_reported(self):
        functions = {"power-generation": "power-unit"}
        self.assertEqual(
            leaf_nodes_without_function(VALID_TREE, functions), ["sensor-head"]
        )

    def test_leaf_nodes_without_function_empty_when_fully_covered(self):
        functions = {
            "power-generation": "power-unit",
            "signal-acquisition": "sensor-head",
        }
        self.assertEqual(leaf_nodes_without_function(VALID_TREE, functions), [])


class DesignDefinitionTests(unittest.TestCase):
    def test_missing_design_definition_reported(self):
        definitions = {
            "spacecraft": True,
            "platform": True,
            "payload": False,
            "power-unit": True,
        }
        self.assertEqual(
            nodes_missing_design_definition(VALID_TREE, definitions),
            ["payload", "sensor-head"],
        )

    def test_empty_when_every_node_has_a_definition(self):
        definitions = {node: True for node in VALID_TREE}
        self.assertEqual(nodes_missing_design_definition(VALID_TREE, definitions), [])


class PrecedenceTests(unittest.TestCase):
    def test_invalid_precedence_reports_bad_key(self):
        precedence = {"phantom-node": []}
        self.assertEqual(
            invalid_precedence_nodes(VALID_TREE, precedence), [("phantom-node", None)]
        )

    def test_invalid_precedence_reports_bad_prerequisite(self):
        precedence = {"platform": ["phantom-prereq"]}
        self.assertEqual(
            invalid_precedence_nodes(VALID_TREE, precedence),
            [("platform", "phantom-prereq")],
        )

    def test_invalid_precedence_empty_when_all_nodes_real(self):
        precedence = {"platform": ["power-unit"], "payload": ["sensor-head"]}
        self.assertEqual(invalid_precedence_nodes(VALID_TREE, precedence), [])

    def test_precedence_cycle_detected(self):
        precedence = {"a": ["b"], "b": ["c"], "c": ["a"]}
        cycle = precedence_cycle(precedence)
        self.assertEqual(set(cycle), {"a", "b", "c"})

    def test_precedence_cycle_empty_when_acyclic(self):
        precedence = {"platform": ["power-unit"], "power-unit": []}
        self.assertEqual(precedence_cycle(precedence), [])


class ConfigurationContentCompleteTests(unittest.TestCase):
    def test_complete_when_every_element_is_consistent(self):
        functions = {
            "power-generation": "power-unit",
            "signal-acquisition": "sensor-head",
        }
        definitions = {node: True for node in VALID_TREE}
        precedence = {"platform": ["power-unit"], "payload": ["sensor-head"]}
        complete, issues = configuration_content_complete(
            VALID_TREE, functions, definitions, precedence
        )
        self.assertTrue(complete)
        for finding in issues.values():
            self.assertEqual(finding, [])

    def test_incomplete_aggregates_every_finding_category(self):
        tree = {"a": None, "b": "a"}
        functions = {"f1": None, "f2": "ghost-node"}
        definitions = {"a": True}
        precedence = {"a": ["ghost-node"]}
        complete, issues = configuration_content_complete(tree, functions, definitions, precedence)
        self.assertFalse(complete)
        self.assertEqual(issues["unallocated_functions"], ["f1"])
        self.assertEqual(issues["orphan_function_allocations"], ["f2"])
        self.assertEqual(issues["nodes_missing_design_definition"], ["b"])
        self.assertEqual(issues["invalid_precedence_nodes"], [("a", "ghost-node")])

    def test_rejects_non_dict_function_tree(self):
        with self.assertRaises(TypeError):
            configuration_content_complete(VALID_TREE, None, {}, {})


if __name__ == "__main__":
    unittest.main()

"""Contract test for goal_structuring_notation_logic (GSN safety arguments).

Deterministic, offline, stdlib unittest. Covers the wave-26 spec worked
example anchors: the valid argument, the removed-solution unsupported-leaf
case, the supported-by cycle case, the away-goal justification rule, argument
metrics, dangling ids, skeleton instantiation, and ValueError rejection of
unknown node types, unsupported edge kinds, duplicate ids and empty node
lists.

Run from the leaf directory:

    python3 scripts/test_goal_structuring_notation.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import goal_structuring_notation_logic as gsn
from goal_structuring_notation_logic import (
    REQUIRE_AWAY_JUSTIFICATION,
    argument_metrics,
    detect_cycles,
    instantiate_skeleton,
    leaf_goals,
    node_map,
    support_coverage,
    top_goals,
    unsupported_leaves,
    validate_argument,
    validate_ids,
)

TOP_TEXT = "the flight control system is acceptably safe to operate"
STRATEGY_TEXT = "argument over the safety assessment evidence"


def worked_example():
    """The spec worked example: FCS safety argument with three evidence nodes."""
    nodes = [
        {"id": "G1", "type": "goal", "text": TOP_TEXT},
        {"id": "S1", "type": "strategy", "text": STRATEGY_TEXT},
        {"id": "G2", "type": "goal",
         "text": "all catastrophic failure conditions meet the 1e-9 target"},
        {"id": "G3", "type": "goal",
         "text": "all hazardous failure conditions meet the 1e-7 target"},
        {"id": "G4", "type": "goal",
         "text": "development assurance evidence exists"},
        {"id": "Sn1", "type": "solution", "text": "SSA report FCS-1"},
        {"id": "Sn2", "type": "solution", "text": "FHA worksheet rev C"},
        {"id": "Sn3", "type": "solution", "text": "DAL assignment record"},
        {"id": "C1", "type": "context", "text": "certification basis FAR-25"},
    ]
    edges = [
        {"from": "G1", "to": "S1", "kind": "supported-by"},
        {"from": "S1", "to": "G2", "kind": "supported-by"},
        {"from": "S1", "to": "G3", "kind": "supported-by"},
        {"from": "S1", "to": "G4", "kind": "supported-by"},
        {"from": "Sn1", "to": "G2", "kind": "supported-by"},
        {"from": "Sn2", "to": "G3", "kind": "supported-by"},
        {"from": "Sn3", "to": "G4", "kind": "supported-by"},
        {"from": "C1", "to": "G1", "kind": "in-context-of"},
    ]
    return nodes, edges


def without_node(nodes, edges, node_id):
    """Return copies of the graph with node_id and its edges removed."""
    kept = [n for n in nodes if n["id"] != node_id]
    kept_edges = [e for e in edges
                  if e["from"] != node_id and e["to"] != node_id]
    return kept, kept_edges


def away_example():
    """Worked example with G4 marked away (support deferred)."""
    nodes, edges = worked_example()
    away = []
    for node in nodes:
        if node["id"] == "G4":
            node = dict(node)
            node["away"] = True
        away.append(node)
    return away, edges


class WorkedExampleValidityTests(unittest.TestCase):
    """The valid worked example anchors."""

    def test_worked_example_valid_argument(self):
        nodes, edges = worked_example()
        result = validate_argument(nodes, edges)
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["coverage"], 1.0)

    def test_worked_example_structure(self):
        nodes, edges = worked_example()
        self.assertEqual(top_goals(nodes, edges), ["G1"])
        self.assertEqual(leaf_goals(nodes, edges), ["G2", "G3", "G4"])
        self.assertEqual(unsupported_leaves(nodes, edges), [])
        self.assertEqual(validate_ids(nodes, edges), [])
        self.assertEqual(detect_cycles(nodes, edges), [])

    def test_worked_example_metrics(self):
        nodes, edges = worked_example()
        metrics = argument_metrics(nodes, edges)
        self.assertEqual(metrics["node_count"], 9)
        self.assertEqual(metrics["goal_count"], 4)
        self.assertEqual(metrics["strategy_count"], 1)
        self.assertEqual(metrics["solution_count"], 3)
        self.assertEqual(metrics["context_count"], 1)
        self.assertEqual(metrics["depth"], 3)
        self.assertEqual(metrics["evidence_types"], {"SSA": 1, "FHA": 1})


class UnsupportedLeafTests(unittest.TestCase):
    """The removed-solution unsupported-leaf case."""

    def test_removed_solution_leaf_unsupported_and_invalid(self):
        nodes, edges = without_node(*worked_example(), "Sn1")
        self.assertEqual(unsupported_leaves(nodes, edges), ["G2"])
        result = validate_argument(nodes, edges)
        self.assertFalse(result["valid"])
        self.assertTrue(any("G2" in issue and "unsupported leaf" in issue
                            for issue in result["issues"]))
        self.assertAlmostEqual(result["coverage"], 2.0 / 3.0)

    def test_removed_two_solutions_two_unsupported(self):
        nodes, edges = without_node(*worked_example(), "Sn1")
        nodes, edges = without_node(nodes, edges, "Sn2")
        self.assertEqual(unsupported_leaves(nodes, edges), ["G2", "G3"])
        self.assertAlmostEqual(support_coverage(nodes, edges), 1.0 / 3.0)


class CycleDetectionTests(unittest.TestCase):
    """Cycle detection over supported-by edges."""

    def test_supported_by_cycle_detected(self):
        nodes, edges = worked_example()
        extra = [{"id": "S2", "type": "strategy",
                  "text": "argument over the catastrophic failure analysis"}]
        cycles = detect_cycles(nodes + extra, edges + [
            {"from": "G2", "to": "S2", "kind": "supported-by"},
            {"from": "S2", "to": "G2", "kind": "supported-by"},
        ])
        self.assertEqual(len(cycles), 1)
        cycle = cycles[0]
        self.assertEqual(cycle[0], "G2")
        self.assertEqual(cycle[-1], "G2")
        self.assertIn("S2", cycle)

    def test_supported_by_cycle_invalidates_argument(self):
        nodes, edges = worked_example()
        extra = [{"id": "S2", "type": "strategy", "text": "cycle strategy"}]
        result = validate_argument(nodes + extra, edges + [
            {"from": "G2", "to": "S2", "kind": "supported-by"},
            {"from": "S2", "to": "G2", "kind": "supported-by"},
        ])
        self.assertFalse(result["valid"])
        self.assertTrue(any("cycle" in issue for issue in result["issues"]))

    def test_self_loop_cycle_detected(self):
        nodes, edges = worked_example()
        cycles = detect_cycles(nodes, edges + [
            {"from": "G2", "to": "G2", "kind": "supported-by"},
        ])
        self.assertEqual(len(cycles), 1)
        self.assertEqual(cycles[0], ["G2", "G2"])

    def test_context_and_assumption_edges_do_not_form_argument_cycles(self):
        nodes, edges = worked_example()
        extra = [
            {"from": "C1", "to": "G1", "kind": "in-context-of"},
            {"from": "G1", "to": "C1", "kind": "in-context-of"},
            {"from": "G1", "to": "S1", "kind": "assumption-of"},
            {"from": "S1", "to": "G1", "kind": "assumption-of"},
        ]
        self.assertEqual(detect_cycles(nodes, edges + extra), [])

    def test_cycle_kind_parameter_scopes_detection(self):
        nodes, edges = worked_example()
        extra = [
            {"from": "C1", "to": "G1", "kind": "in-context-of"},
            {"from": "G1", "to": "C1", "kind": "in-context-of"},
        ]
        cycles = detect_cycles(nodes, edges + extra, kind="in-context-of")
        self.assertEqual(len(cycles), 1)
        self.assertIn("C1", cycles[0])


class AwayGoalTests(unittest.TestCase):
    """The away-goal justification rule (REQUIRE_AWAY_JUSTIFICATION)."""

    def test_away_goal_without_justification_is_issue(self):
        nodes, edges = away_example()
        result = validate_argument(nodes, edges)
        self.assertFalse(result["valid"])
        self.assertTrue(any("G4" in issue and "away goal" in issue
                            for issue in result["issues"]))

    def test_away_goal_justification_clears_issue(self):
        nodes, edges = away_example()
        nodes = nodes + [{"id": "J1", "type": "justification",
                          "text": "the DAL record is the certified artifact"}]
        edges = edges + [{"from": "J1", "to": "G4",
                          "kind": "assumption-of"}]
        result = validate_argument(nodes, edges)
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])

    def test_away_justification_any_edge_kind_counts(self):
        nodes, edges = away_example()
        nodes = nodes + [{"id": "J1", "type": "justification",
                          "text": "the DAL record is the certified artifact"}]
        edges = edges + [{"from": "J1", "to": "G4",
                          "kind": "in-context-of"}]
        self.assertTrue(validate_argument(nodes, edges)["valid"])

    def test_away_leaf_without_solution_unsupported_and_coverage(self):
        nodes, edges = away_example()
        nodes, edges = without_node(nodes, edges, "Sn3")
        self.assertEqual(unsupported_leaves(nodes, edges), ["G4"])
        self.assertAlmostEqual(support_coverage(nodes, edges), 2.0 / 3.0)

    def test_away_leaf_justified_is_supported(self):
        nodes, edges = away_example()
        nodes, edges = without_node(nodes, edges, "Sn3")
        nodes = nodes + [{"id": "J1", "type": "justification",
                          "text": "the DAL record is the certified artifact"}]
        edges = edges + [{"from": "J1", "to": "G4",
                          "kind": "assumption-of"}]
        self.assertEqual(unsupported_leaves(nodes, edges), [])
        self.assertEqual(support_coverage(nodes, edges), 1.0)
        self.assertTrue(validate_argument(nodes, edges)["valid"])

    def test_away_rule_off_allows_unjustified_away_goal(self):
        nodes, edges = away_example()
        nodes, edges = without_node(nodes, edges, "Sn3")
        saved = gsn.REQUIRE_AWAY_JUSTIFICATION
        gsn.REQUIRE_AWAY_JUSTIFICATION = False
        try:
            self.assertEqual(unsupported_leaves(nodes, edges), [])
            self.assertEqual(support_coverage(nodes, edges), 1.0)
            self.assertTrue(validate_argument(nodes, edges)["valid"])
        finally:
            gsn.REQUIRE_AWAY_JUSTIFICATION = saved

    def test_away_rule_constant_defaults_to_true(self):
        self.assertTrue(REQUIRE_AWAY_JUSTIFICATION)


class MetricsTests(unittest.TestCase):
    """Depth and evidence tally on deeper and partial graphs."""

    def test_metrics_depth_five_level_chain(self):
        nodes = [
            {"id": "G1", "type": "goal", "text": "top claim"},
            {"id": "S1", "type": "strategy", "text": "first strategy"},
            {"id": "G2", "type": "goal", "text": "mid goal"},
            {"id": "S2", "type": "strategy", "text": "second strategy"},
            {"id": "G3", "type": "goal", "text": "leaf claim"},
            {"id": "Sn1", "type": "solution", "text": "SSA report FCS-9"},
        ]
        edges = [
            {"from": "G1", "to": "S1", "kind": "supported-by"},
            {"from": "S1", "to": "G2", "kind": "supported-by"},
            {"from": "G2", "to": "S2", "kind": "supported-by"},
            {"from": "S2", "to": "G3", "kind": "supported-by"},
            {"from": "Sn1", "to": "G3", "kind": "supported-by"},
        ]
        self.assertEqual(argument_metrics(nodes, edges)["depth"], 5)
        self.assertTrue(validate_argument(nodes, edges)["valid"])

    def test_metrics_depth_zero_without_solutions(self):
        nodes, edges = worked_example()
        for solution in ("Sn1", "Sn2", "Sn3"):
            nodes, edges = without_node(nodes, edges, solution)
        self.assertEqual(argument_metrics(nodes, edges)["depth"], 0)
        self.assertEqual(argument_metrics(nodes, edges)["solution_count"], 0)

    def test_metrics_evidence_types_extra_keywords_case_insensitive(self):
        nodes, edges = worked_example()
        extra = [
            {"id": "Sn4", "type": "solution",
             "text": "test report of the bench run"},
            {"id": "Sn5", "type": "solution",
             "text": "analysis summary of the hazard log"},
            {"id": "Sn6", "type": "solution", "text": "ssa report rev B"},
        ]
        tally = argument_metrics(nodes + extra, edges)["evidence_types"]
        self.assertEqual(tally["SSA"], 2)
        self.assertEqual(tally["test"], 1)
        self.assertEqual(tally["analysis"], 1)
        self.assertNotIn("DAL", tally)


class DanglingIdTests(unittest.TestCase):
    """Dangling references are issues, never exceptions."""

    def test_dangling_from_and_to_reported(self):
        nodes, edges = worked_example()
        issues = validate_ids(nodes, edges + [
            {"from": "Ghost", "to": "G1", "kind": "supported-by"},
            {"from": "G1", "to": "Phantom", "kind": "supported-by"},
        ])
        self.assertTrue(any("Ghost" in issue for issue in issues))
        self.assertTrue(any("Phantom" in issue for issue in issues))

    def test_dangling_edge_invalidates_argument(self):
        nodes, edges = worked_example()
        result = validate_argument(nodes, edges + [
            {"from": "Ghost", "to": "G1", "kind": "supported-by"},
        ])
        self.assertFalse(result["valid"])
        self.assertTrue(any("dangling" in issue for issue in result["issues"]))


class StructureRuleTests(unittest.TestCase):
    """Single top goal, decomposed strategies, node map."""

    def test_two_top_goals_invalid(self):
        nodes = [
            {"id": "G1", "type": "goal", "text": "flight control claim"},
            {"id": "S1", "type": "strategy",
             "text": "argument over FCS evidence"},
            {"id": "G2", "type": "goal", "text": "FCS leaf claim"},
            {"id": "G5", "type": "goal", "text": "brake system claim"},
            {"id": "S5", "type": "strategy",
             "text": "argument over brake evidence"},
            {"id": "G6", "type": "goal", "text": "brake leaf claim"},
            {"id": "Sn1", "type": "solution", "text": "SSA report FCS-1"},
            {"id": "Sn5", "type": "solution", "text": "SSA report BRK-1"},
        ]
        edges = [
            {"from": "G1", "to": "S1", "kind": "supported-by"},
            {"from": "S1", "to": "G2", "kind": "supported-by"},
            {"from": "Sn1", "to": "G2", "kind": "supported-by"},
            {"from": "G5", "to": "S5", "kind": "supported-by"},
            {"from": "S5", "to": "G6", "kind": "supported-by"},
            {"from": "Sn5", "to": "G6", "kind": "supported-by"},
        ]
        self.assertEqual(top_goals(nodes, edges), ["G1", "G5"])
        result = validate_argument(nodes, edges)
        self.assertFalse(result["valid"])
        self.assertTrue(any("top goal" in issue for issue in result["issues"]))

    def test_undecomposed_strategy_invalid(self):
        nodes = [
            {"id": "G1", "type": "goal", "text": "top claim"},
            {"id": "S1", "type": "strategy",
             "text": "strategy with no sub-goals"},
        ]
        edges = [{"from": "G1", "to": "S1", "kind": "supported-by"}]
        result = validate_argument(nodes, edges)
        self.assertFalse(result["valid"])
        self.assertTrue(any("not decomposed" in issue
                            for issue in result["issues"]))

    def test_node_map_roundtrip(self):
        nodes, _ = worked_example()
        mapping = node_map(nodes)
        self.assertEqual(len(mapping), 9)
        for node in nodes:
            self.assertIs(mapping[node["id"]], node)


class SkeletonTests(unittest.TestCase):
    """Skeleton instantiation and the attach-solutions workflow."""

    CLAIMS = [
        "all catastrophic failure conditions meet the 1e-9 target",
        "all hazardous failure conditions meet the 1e-7 target",
        "development assurance evidence exists",
    ]

    def test_skeleton_structure_and_texts(self):
        nodes, edges = instantiate_skeleton(TOP_TEXT, STRATEGY_TEXT,
                                            self.CLAIMS)
        self.assertEqual([n["id"] for n in nodes],
                         ["G1", "S1", "G2", "G3", "G4"])
        self.assertEqual([n["type"] for n in nodes],
                         ["goal", "strategy", "goal", "goal", "goal"])
        self.assertEqual(edges, [
            {"from": "G1", "to": "S1", "kind": "supported-by"},
            {"from": "S1", "to": "G2", "kind": "supported-by"},
            {"from": "S1", "to": "G3", "kind": "supported-by"},
            {"from": "S1", "to": "G4", "kind": "supported-by"},
        ])
        self.assertEqual(nodes[0]["text"], TOP_TEXT)
        self.assertEqual(nodes[2]["text"], self.CLAIMS[0])

    def test_skeleton_validation_flags_unsupported_leaves(self):
        nodes, edges = instantiate_skeleton(TOP_TEXT, STRATEGY_TEXT,
                                            self.CLAIMS)
        result = validate_argument(nodes, edges)
        self.assertFalse(result["valid"])
        self.assertEqual(result["coverage"], 0.0)
        self.assertEqual(unsupported_leaves(nodes, edges),
                         ["G2", "G3", "G4"])

    def test_skeleton_round_trip_with_solutions_valid(self):
        nodes, edges = instantiate_skeleton(TOP_TEXT, STRATEGY_TEXT,
                                            self.CLAIMS)
        solutions = [
            {"id": "Sn1", "type": "solution", "text": "SSA report FCS-1"},
            {"id": "Sn2", "type": "solution", "text": "FHA worksheet rev C"},
            {"id": "Sn3", "type": "solution", "text": "DAL assignment record"},
        ]
        edges = edges + [
            {"from": "Sn1", "to": "G2", "kind": "supported-by"},
            {"from": "Sn2", "to": "G3", "kind": "supported-by"},
            {"from": "Sn3", "to": "G4", "kind": "supported-by"},
        ]
        result = validate_argument(nodes + solutions, edges)
        self.assertTrue(result["valid"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["coverage"], 1.0)

    def test_skeleton_rejects_empty_texts(self):
        with self.assertRaises(ValueError):
            instantiate_skeleton("", STRATEGY_TEXT, self.CLAIMS)
        with self.assertRaises(ValueError):
            instantiate_skeleton(TOP_TEXT, "", self.CLAIMS)
        with self.assertRaises(ValueError):
            instantiate_skeleton(TOP_TEXT, STRATEGY_TEXT, [""])


class InputValidationTests(unittest.TestCase):
    """ValueError rejection of malformed input."""

    def test_unknown_node_type_raises(self):
        nodes, edges = worked_example()
        bad = nodes + [{"id": "X1", "type": "evidence", "text": "nope"}]
        with self.assertRaises(ValueError):
            validate_argument(bad, edges)

    def test_unsupported_edge_kind_raises(self):
        nodes, edges = worked_example()
        bad = edges + [{"from": "G1", "to": "S1", "kind": "supports"}]
        with self.assertRaises(ValueError):
            validate_argument(nodes, bad)

    def test_duplicate_node_id_raises(self):
        nodes, edges = worked_example()
        dup = nodes + [dict(nodes[0])]
        with self.assertRaises(ValueError):
            validate_argument(dup, edges)

    def test_empty_node_list_raises_everywhere(self):
        with self.assertRaises(ValueError):
            node_map([])
        with self.assertRaises(ValueError):
            validate_argument([], [])
        with self.assertRaises(ValueError):
            detect_cycles([], [])
        with self.assertRaises(ValueError):
            unsupported_leaves([], [])
        with self.assertRaises(ValueError):
            argument_metrics([], [])


if __name__ == "__main__":
    unittest.main()

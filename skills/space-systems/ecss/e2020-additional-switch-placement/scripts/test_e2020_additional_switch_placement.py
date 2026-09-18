#!/usr/bin/env python3
"""Contract test for the additional switch placement (offline)."""

import copy
import unittest

from e2020_additional_switch_placement_logic import (
    ADVISORY_SINGLE_CANDIDATE,
    ADVISORY_WHOLE_LINE,
    DEFAULT_LINE_NODES,
    DEFAULT_MAIN_SWITCH_NODE,
    DEFAULT_PLACEMENT_POLICY,
    FINDING_NOT_MOUNTABLE,
    FINDING_NOT_POWER_SYSTEM_SIDE,
    FINDING_SEPARATION,
    FINDING_STUB,
    VERDICT_NO_PLACEMENT,
    VERDICT_RECOMMENDED,
    acceptable_placements,
    assess_placement,
    de_energised_length_m,
    energised_stub_length_m,
    find_node,
    is_power_system_side,
    line_length_m,
    recommend_switch_placement,
    separation_m,
    validate_line_topology,
    validate_node,
    validate_placement_policy,
)

SOURCE_NODE = "power-system-output-connector"
BULKHEAD_NODE = "power-system-bulkhead-feedthrough"
BRANCH_NODE = "harness-branch-node"
SPLICE_NODE = "mid-harness-splice"
BRACKET_NODE = "load-connector-bracket"


def _nodes():
    return [copy.deepcopy(row) for row in DEFAULT_LINE_NODES]


def _policy(**overrides):
    rules = copy.deepcopy(DEFAULT_PLACEMENT_POLICY)
    rules.update(overrides)
    return rules


class NodeValidationTests(unittest.TestCase):
    def test_default_node_validates(self):
        row = validate_node(DEFAULT_LINE_NODES[0])
        self.assertEqual(row["id"], SOURCE_NODE)

    def test_node_missing_a_figure_rejected(self):
        row = copy.deepcopy(DEFAULT_LINE_NODES[1])
        del row["mountable"]
        with self.assertRaises(ValueError):
            validate_node(row)

    def test_non_boolean_mountable_rejected(self):
        row = copy.deepcopy(DEFAULT_LINE_NODES[1])
        row["mountable"] = "yes"
        with self.assertRaises(ValueError):
            validate_node(row)

    def test_negative_distance_rejected(self):
        row = copy.deepcopy(DEFAULT_LINE_NODES[1])
        row["distance_from_source_m"] = -0.2
        with self.assertRaises(ValueError):
            validate_node(row)

    def test_blank_node_id_rejected(self):
        row = copy.deepcopy(DEFAULT_LINE_NODES[1])
        row["id"] = "  "
        with self.assertRaises(ValueError):
            validate_node(row)

    def test_non_mapping_node_rejected(self):
        with self.assertRaises(ValueError):
            validate_node("bulkhead")


class TopologyValidationTests(unittest.TestCase):
    def test_default_topology_validates(self):
        rows = validate_line_topology(DEFAULT_LINE_NODES)
        self.assertEqual(len(rows), len(DEFAULT_LINE_NODES))

    def test_repeated_node_id_rejected(self):
        rows = _nodes()
        rows[2]["id"] = rows[1]["id"]
        with self.assertRaises(ValueError):
            validate_line_topology(rows)

    def test_first_node_away_from_the_source_rejected(self):
        rows = _nodes()
        rows[0]["distance_from_source_m"] = 0.4
        with self.assertRaises(ValueError):
            validate_line_topology(rows)

    def test_unordered_topology_rejected(self):
        rows = _nodes()
        rows[1], rows[2] = rows[2], rows[1]
        with self.assertRaises(ValueError):
            validate_line_topology(rows)

    def test_two_nodes_at_one_distance_rejected(self):
        rows = _nodes()
        rows[2]["distance_from_source_m"] = rows[1]["distance_from_source_m"]
        with self.assertRaises(ValueError):
            validate_line_topology(rows)

    def test_single_node_topology_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_topology([_nodes()[0]])

    def test_mapping_instead_of_a_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_line_topology(_nodes()[0])

    def test_unknown_node_id_rejected(self):
        with self.assertRaises(ValueError):
            find_node(DEFAULT_LINE_NODES, "no-such-node")


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_validates(self):
        rules = validate_placement_policy(DEFAULT_PLACEMENT_POLICY)
        self.assertAlmostEqual(rules["max_energised_stub_m"], 1.50, places=12)

    def test_policy_missing_a_figure_rejected(self):
        rules = _policy()
        del rules["min_separation_m"]
        with self.assertRaises(ValueError):
            validate_placement_policy(rules)

    def test_non_boolean_side_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_placement_policy(_policy(require_power_system_side="always"))

    def test_negative_minimum_separation_rejected(self):
        with self.assertRaises(ValueError):
            validate_placement_policy(_policy(min_separation_m=-0.1))

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_placement_policy(1.5)


class GeometryTests(unittest.TestCase):
    def test_line_length_is_the_last_node_distance(self):
        self.assertAlmostEqual(line_length_m(DEFAULT_LINE_NODES), 4.10, places=9)

    def test_energised_stub_is_the_node_distance(self):
        self.assertAlmostEqual(
            energised_stub_length_m(DEFAULT_LINE_NODES, BRANCH_NODE), 1.20, places=9
        )

    def test_the_source_node_leaves_no_stub(self):
        self.assertAlmostEqual(
            energised_stub_length_m(DEFAULT_LINE_NODES, SOURCE_NODE), 0.0, places=12
        )

    def test_stub_and_de_energised_length_add_to_the_line(self):
        total = line_length_m(DEFAULT_LINE_NODES)
        for row in DEFAULT_LINE_NODES:
            stub = energised_stub_length_m(DEFAULT_LINE_NODES, row["id"])
            covered = de_energised_length_m(DEFAULT_LINE_NODES, row["id"])
            self.assertAlmostEqual(stub + covered, total, places=9)

    def test_de_energised_length_falls_as_the_switch_moves_downstream(self):
        near = de_energised_length_m(DEFAULT_LINE_NODES, SOURCE_NODE)
        far = de_energised_length_m(DEFAULT_LINE_NODES, BRACKET_NODE)
        self.assertGreater(near, far)

    def test_separation_is_the_absolute_distance_to_the_main_switch(self):
        self.assertAlmostEqual(
            separation_m(DEFAULT_LINE_NODES, BRANCH_NODE, DEFAULT_MAIN_SWITCH_NODE),
            1.90,
            places=9,
        )

    def test_separation_downstream_of_the_main_switch_is_positive(self):
        self.assertAlmostEqual(
            separation_m(DEFAULT_LINE_NODES, BRACKET_NODE, DEFAULT_MAIN_SWITCH_NODE),
            0.70,
            places=9,
        )

    def test_upstream_node_reads_as_power_system_side(self):
        self.assertTrue(
            is_power_system_side(DEFAULT_LINE_NODES, BULKHEAD_NODE, DEFAULT_MAIN_SWITCH_NODE)
        )

    def test_downstream_node_does_not_read_as_power_system_side(self):
        self.assertFalse(
            is_power_system_side(DEFAULT_LINE_NODES, BRACKET_NODE, DEFAULT_MAIN_SWITCH_NODE)
        )

    def test_the_main_switch_node_is_not_its_own_power_system_side(self):
        self.assertFalse(
            is_power_system_side(
                DEFAULT_LINE_NODES, DEFAULT_MAIN_SWITCH_NODE, DEFAULT_MAIN_SWITCH_NODE
            )
        )


class PlacementAssessmentTests(unittest.TestCase):
    def test_the_source_node_is_acceptable(self):
        result = assess_placement(DEFAULT_LINE_NODES, SOURCE_NODE)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_the_source_node_de_energises_the_whole_line(self):
        result = assess_placement(DEFAULT_LINE_NODES, SOURCE_NODE)
        self.assertAlmostEqual(result["de_energised_fraction"], 1.0, places=9)
        self.assertTrue(any(ADVISORY_WHOLE_LINE in a for a in result["advisories"]))

    def test_a_harness_splice_cannot_carry_a_switch(self):
        result = assess_placement(DEFAULT_LINE_NODES, SPLICE_NODE)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any(FINDING_NOT_MOUNTABLE in f for f in result["findings"]))

    def test_a_node_past_the_main_switch_is_on_the_wrong_side(self):
        result = assess_placement(DEFAULT_LINE_NODES, BRACKET_NODE)
        self.assertFalse(result["power_system_side"])
        self.assertTrue(
            any(FINDING_NOT_POWER_SYSTEM_SIDE in f for f in result["findings"])
        )

    def test_a_long_stub_is_a_finding(self):
        result = assess_placement(DEFAULT_LINE_NODES, BRANCH_NODE, policy=_policy(max_energised_stub_m=0.5))
        self.assertFalse(result["stub_within_limit"])
        self.assertTrue(any(FINDING_STUB in f for f in result["findings"]))

    def test_a_short_separation_is_a_finding(self):
        result = assess_placement(
            DEFAULT_LINE_NODES, BRANCH_NODE, policy=_policy(min_separation_m=2.0)
        )
        self.assertFalse(result["separation_within_limit"])
        self.assertTrue(any(FINDING_SEPARATION in f for f in result["findings"]))

    def test_a_stub_exactly_on_the_limit_is_accepted(self):
        result = assess_placement(
            DEFAULT_LINE_NODES, BRANCH_NODE, policy=_policy(max_energised_stub_m=1.20)
        )
        self.assertAlmostEqual(result["stub_slack_m"], 0.0, places=9)
        self.assertTrue(result["stub_within_limit"])

    def test_a_separation_exactly_on_the_minimum_is_accepted(self):
        result = assess_placement(
            DEFAULT_LINE_NODES, BRANCH_NODE, policy=_policy(min_separation_m=1.90)
        )
        self.assertAlmostEqual(result["separation_slack_m"], 0.0, places=9)
        self.assertTrue(result["separation_within_limit"])

    def test_relaxing_the_side_rule_accepts_a_downstream_node(self):
        strict = assess_placement(DEFAULT_LINE_NODES, BRACKET_NODE, policy=_policy(max_energised_stub_m=4.5))
        loose = assess_placement(
            DEFAULT_LINE_NODES,
            BRACKET_NODE,
            policy=_policy(max_energised_stub_m=4.5, require_power_system_side=False),
        )
        self.assertFalse(strict["acceptable"])
        self.assertTrue(loose["acceptable"])


class RecommendationTests(unittest.TestCase):
    def test_the_shortest_stub_node_is_recommended(self):
        result = recommend_switch_placement()
        self.assertEqual(result["verdict"], VERDICT_RECOMMENDED)
        self.assertEqual(result["recommended_node"], SOURCE_NODE)

    def test_acceptable_nodes_are_listed_shortest_stub_first(self):
        result = recommend_switch_placement()
        stubs = [
            energised_stub_length_m(DEFAULT_LINE_NODES, node)
            for node in result["acceptable_nodes"]
        ]
        self.assertEqual(stubs, sorted(stubs))

    def test_the_helper_agrees_with_the_recommendation(self):
        listed = acceptable_placements(DEFAULT_LINE_NODES)
        result = recommend_switch_placement()
        self.assertEqual([g["node_id"] for g in listed], result["acceptable_nodes"])

    def test_the_main_switch_node_is_never_offered(self):
        result = recommend_switch_placement()
        self.assertNotIn(DEFAULT_MAIN_SWITCH_NODE, result["acceptable_nodes"])
        self.assertEqual(len(result["assessments"]), len(DEFAULT_LINE_NODES) - 1)

    def test_a_tighter_separation_drops_the_nearest_candidate(self):
        loose = recommend_switch_placement()
        tight = recommend_switch_placement(policy=_policy(min_separation_m=2.0))
        self.assertIn(BRANCH_NODE, loose["acceptable_nodes"])
        self.assertNotIn(BRANCH_NODE, tight["acceptable_nodes"])

    def test_a_tight_stub_limit_leaves_one_node_and_an_advisory(self):
        result = recommend_switch_placement(policy=_policy(max_energised_stub_m=0.20))
        self.assertEqual(result["acceptable_nodes"], [SOURCE_NODE])
        self.assertTrue(any(ADVISORY_SINGLE_CANDIDATE in a for a in result["advisories"]))

    def test_an_unreachable_separation_leaves_no_placement(self):
        result = recommend_switch_placement(policy=_policy(min_separation_m=5.0))
        self.assertEqual(result["verdict"], VERDICT_NO_PLACEMENT)
        self.assertIsNone(result["recommended_node"])
        self.assertTrue(result["findings"])

    def test_relaxing_the_side_rule_widens_the_candidate_set(self):
        strict = recommend_switch_placement(policy=_policy(max_energised_stub_m=4.5))
        loose = recommend_switch_placement(
            policy=_policy(max_energised_stub_m=4.5, require_power_system_side=False)
        )
        self.assertGreater(len(loose["acceptable_nodes"]), len(strict["acceptable_nodes"]))

    def test_the_recommendation_carries_the_line_length_and_main_switch(self):
        result = recommend_switch_placement()
        self.assertAlmostEqual(result["line_length_m"], 4.10, places=9)
        self.assertEqual(result["main_switch_node"], DEFAULT_MAIN_SWITCH_NODE)

    def test_the_recommended_node_has_the_shortest_stub_of_the_accepted(self):
        result = recommend_switch_placement()
        chosen = result["recommended_assessment"]["energised_stub_m"]
        for node in result["acceptable_nodes"]:
            self.assertLessEqual(
                chosen, energised_stub_length_m(DEFAULT_LINE_NODES, node)
            )

    def test_recommendation_rejects_a_broken_topology(self):
        rows = _nodes()
        rows[0]["distance_from_source_m"] = 0.9
        with self.assertRaises(ValueError):
            recommend_switch_placement(topology=rows)

    def test_recommendation_rejects_a_broken_policy(self):
        with self.assertRaises(ValueError):
            recommend_switch_placement(policy=_policy(max_energised_stub_m=-1.0))

    def test_recommendation_rejects_an_unknown_main_switch_node(self):
        with self.assertRaises(ValueError):
            recommend_switch_placement(main_switch_node_id="no-such-node")


if __name__ == "__main__":
    unittest.main()

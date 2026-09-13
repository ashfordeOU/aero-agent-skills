#!/usr/bin/env python3
"""Gate 3 contract test for e2006-unintended-tether-conductive-paths.

stdlib unittest, offline, deterministic. Run:
python3 test_e2006_unintended_tether_conductive_paths.py
"""

import unittest

import e2006_unintended_tether_conductive_paths_logic as logic


def base_edges(**over):
    edges = {
        "e-tether": {
            "id": "e-tether",
            "from": "source-terminal",
            "to": "tether-far-end",
            "resistance_ohm": 5.0,
            "role": "intended",
        },
        "e-contactor": {
            "id": "e-contactor",
            "from": "tether-far-end",
            "to": "return-terminal",
            "resistance_ohm": 1.0,
            "role": "intended",
        },
        "e-reel": {
            "id": "e-reel",
            "from": "source-terminal",
            "to": "deployer-chassis",
            "resistance_ohm": 1.0e6,
            "role": "parasitic",
            "hardware": "reel-drum",
            "min_isolation_ohm": 1.0e5,
        },
        "e-chassis-frame": {
            "id": "e-chassis-frame",
            "from": "deployer-chassis",
            "to": "structure-frame",
            "resistance_ohm": 1.0e6,
            "role": "parasitic",
            "hardware": "deployer-chassis",
            "min_isolation_ohm": 1.0e5,
        },
        "e-frame-return": {
            "id": "e-frame-return",
            "from": "structure-frame",
            "to": "return-terminal",
            "resistance_ohm": 1.0e6,
            "role": "parasitic",
            "hardware": "structure-frame",
            "min_isolation_ohm": 1.0e5,
        },
    }
    for key, patch in over.items():
        edges[key].update(patch)
    return [edges[k] for k in sorted(edges)]


def base_config(**over):
    cfg = {
        "source": "source-terminal",
        "sink": "return-terminal",
        "allowed_shunted_fraction": 0.01,
        "edges": base_edges(),
    }
    cfg.update(over)
    return cfg


class TestHardwareCategorization(unittest.TestCase):
    def test_reel_drum_is_state_dependent(self):
        self.assertEqual(
            logic.categorize_bypass_hardware("reel-drum"), "state-dependent-contact"
        )

    def test_latch_pin_is_state_dependent(self):
        self.assertEqual(
            logic.categorize_bypass_hardware("latch-pin"), "state-dependent-contact"
        )

    def test_harness_shield_is_a_permanent_bond(self):
        self.assertEqual(logic.categorize_bypass_hardware("harness-shield"), "permanent-bond")

    def test_structure_frame_is_a_permanent_bond(self):
        self.assertEqual(logic.categorize_bypass_hardware("structure-frame"), "permanent-bond")

    def test_hardware_is_case_and_space_insensitive(self):
        self.assertEqual(
            logic.categorize_bypass_hardware(" Guide-Roller "), "state-dependent-contact"
        )

    def test_unknown_hardware_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_bypass_hardware("thruster-valve")

    def test_non_string_hardware_raises(self):
        with self.assertRaises(ValueError):
            logic.categorize_bypass_hardware(None)


class TestGraphConstruction(unittest.TestCase):
    def test_graph_indexes_every_edge(self):
        adjacency, index = logic.build_graph(base_edges())
        self.assertEqual(len(index), 5)
        self.assertIn("source-terminal", adjacency)
        self.assertEqual(len(adjacency["source-terminal"]), 2)

    def test_parasitic_edge_gets_a_contact_family(self):
        _, index = logic.build_graph(base_edges())
        self.assertEqual(index["e-reel"]["contact_family"], "state-dependent-contact")

    def test_intended_edge_has_no_hardware_key(self):
        _, index = logic.build_graph(base_edges())
        self.assertNotIn("hardware", index["e-tether"])

    def test_empty_edge_list_raises(self):
        with self.assertRaises(ValueError):
            logic.build_graph([])

    def test_edges_not_a_list_raises(self):
        with self.assertRaises(ValueError):
            logic.build_graph({"id": "e1"})

    def test_edge_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.build_graph(["e-tether"])

    def test_duplicate_edge_id_raises(self):
        edges = base_edges()
        edges.append(dict(edges[0]))
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_duplicate_route_between_same_nodes_raises(self):
        edges = base_edges()
        edges.append(
            {
                "id": "e-shadow",
                "from": "return-terminal",
                "to": "tether-far-end",
                "resistance_ohm": 2.0,
                "role": "parasitic",
                "hardware": "harness-shield",
                "min_isolation_ohm": 1.0,
            }
        )
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_self_loop_raises(self):
        edges = base_edges(**{"e-tether": {"to": "source-terminal"}})
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_missing_edge_id_raises(self):
        edges = base_edges()
        del edges[0]["id"]
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_bad_role_raises(self):
        edges = base_edges(**{"e-tether": {"role": "maybe"}})
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_negative_resistance_raises(self):
        edges = base_edges(**{"e-tether": {"resistance_ohm": -1.0}})
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_parasitic_edge_with_unknown_hardware_raises(self):
        edges = base_edges(**{"e-reel": {"hardware": "gyroscope"}})
        with self.assertRaises(ValueError):
            logic.build_graph(edges)

    def test_missing_node_name_raises(self):
        edges = base_edges(**{"e-tether": {"from": ""}})
        with self.assertRaises(ValueError):
            logic.build_graph(edges)


class TestPathEnumeration(unittest.TestCase):
    def test_two_paths_are_found(self):
        adjacency, _ = logic.build_graph(base_edges())
        paths = logic.enumerate_paths(adjacency, "source-terminal", "return-terminal")
        self.assertEqual(len(paths), 2)

    def test_intended_path_is_the_short_one(self):
        adjacency, index = logic.build_graph(base_edges())
        paths = logic.enumerate_paths(adjacency, "source-terminal", "return-terminal")
        intended = [p for p in paths if logic.categorize_path(p, index) == "intended"]
        self.assertEqual(len(intended), 1)
        self.assertEqual(len(intended[0]), 2)

    def test_bypass_path_crosses_three_parasitic_edges(self):
        adjacency, index = logic.build_graph(base_edges())
        paths = logic.enumerate_paths(adjacency, "source-terminal", "return-terminal")
        bypass = [p for p in paths if logic.categorize_path(p, index) == "bypass"]
        self.assertEqual(len(bypass), 1)
        self.assertEqual(len(bypass[0]), 3)

    def test_unknown_source_raises(self):
        adjacency, _ = logic.build_graph(base_edges())
        with self.assertRaises(ValueError):
            logic.enumerate_paths(adjacency, "battery-bus", "return-terminal")

    def test_unknown_sink_raises(self):
        adjacency, _ = logic.build_graph(base_edges())
        with self.assertRaises(ValueError):
            logic.enumerate_paths(adjacency, "source-terminal", "antenna-boom")

    def test_same_source_and_sink_raises(self):
        adjacency, _ = logic.build_graph(base_edges())
        with self.assertRaises(ValueError):
            logic.enumerate_paths(adjacency, "source-terminal", "source-terminal")

    def test_disconnected_graph_yields_no_path(self):
        edges = [
            {"id": "a", "from": "n1", "to": "n2", "resistance_ohm": 1.0, "role": "intended"},
            {"id": "b", "from": "n3", "to": "n4", "resistance_ohm": 1.0, "role": "intended"},
        ]
        adjacency, _ = logic.build_graph(edges)
        self.assertEqual(logic.enumerate_paths(adjacency, "n1", "n4"), [])


class TestPathArithmetic(unittest.TestCase):
    def test_path_resistance_is_a_series_sum(self):
        _, index = logic.build_graph(base_edges())
        self.assertAlmostEqual(
            logic.path_resistance_ohm(["e-tether", "e-contactor"], index), 6.0, places=9
        )

    def test_unknown_edge_in_path_raises(self):
        _, index = logic.build_graph(base_edges())
        with self.assertRaises(ValueError):
            logic.path_resistance_ohm(["e-ghost"], index)

    def test_empty_path_raises(self):
        _, index = logic.build_graph(base_edges())
        with self.assertRaises(ValueError):
            logic.path_resistance_ohm([], index)

    def test_shunted_fraction_of_equal_legs_is_half(self):
        self.assertAlmostEqual(logic.shunted_fraction(6.0, 6.0), 0.5, places=9)

    def test_shunted_fraction_of_a_high_resistance_bypass_is_small(self):
        self.assertAlmostEqual(logic.shunted_fraction(6.0, 594.0), 0.01, places=12)

    def test_shunted_fraction_rejects_two_zero_legs(self):
        with self.assertRaises(ValueError):
            logic.shunted_fraction(0.0, 0.0)

    def test_shunted_fraction_rejects_negative_resistance(self):
        with self.assertRaises(ValueError):
            logic.shunted_fraction(6.0, -1.0)

    def test_categorize_path_rejects_unknown_edge(self):
        _, index = logic.build_graph(base_edges())
        with self.assertRaises(ValueError):
            logic.categorize_path(["e-ghost"], index)


class TestToleranceHelpers(unittest.TestCase):
    def test_within_limit_below(self):
        self.assertTrue(logic.within_limit(0.009, 0.01))

    def test_within_limit_absorbs_float_sum_at_boundary(self):
        self.assertTrue(logic.within_limit(0.1 + 0.2, 0.3))

    def test_within_limit_rejects_real_exceedance(self):
        self.assertFalse(logic.within_limit(0.0101, 0.01))

    def test_at_least_absorbs_float_sum_at_boundary(self):
        self.assertTrue(logic.at_least(0.3, 0.1 + 0.2))

    def test_at_least_rejects_real_shortfall(self):
        self.assertFalse(logic.at_least(9.0e4, 1.0e5))


class TestIsolationFloor(unittest.TestCase):
    def test_healthy_isolation_has_no_finding(self):
        _, index = logic.build_graph(base_edges())
        self.assertEqual(logic.evaluate_isolation(index), [])

    def test_sub_floor_isolation_is_flagged(self):
        _, index = logic.build_graph(base_edges(**{"e-reel": {"resistance_ohm": 1.0e3}}))
        findings = logic.evaluate_isolation(index)
        self.assertEqual(len(findings), 1)
        self.assertIn("isolation floor", findings[0])

    def test_isolation_exactly_at_the_floor_passes(self):
        _, index = logic.build_graph(base_edges(**{"e-reel": {"resistance_ohm": 1.0e5}}))
        self.assertEqual(logic.evaluate_isolation(index), [])

    def test_missing_floor_is_a_finding_not_a_pass(self):
        edges = base_edges()
        for edge in edges:
            if edge["id"] == "e-reel":
                del edge["min_isolation_ohm"]
        _, index = logic.build_graph(edges)
        findings = logic.evaluate_isolation(index)
        self.assertEqual(len(findings), 1)
        self.assertIn("no isolation-resistance minimum", findings[0])

    def test_zero_floor_raises(self):
        _, index = logic.build_graph(base_edges(**{"e-reel": {"min_isolation_ohm": 0.0}}))
        with self.assertRaises(ValueError):
            logic.evaluate_isolation(index)

    def test_intended_edges_are_not_checked_against_a_floor(self):
        _, index = logic.build_graph(base_edges(**{"e-tether": {"resistance_ohm": 0.0}}))
        self.assertEqual(logic.evaluate_isolation(index), [])


class TestCircuitAssessment(unittest.TestCase):
    def test_well_isolated_circuit_is_compliant(self):
        report = logic.assess_conductive_paths(base_config())
        self.assertTrue(report["compliant"], report["findings"])
        self.assertAlmostEqual(report["intended_resistance_ohm"], 6.0, places=9)
        self.assertEqual(report["intended_path_count"], 1)
        self.assertEqual(len(report["bypasses"]), 1)

    def test_bypass_fraction_is_reported(self):
        report = logic.assess_conductive_paths(base_config())
        self.assertAlmostEqual(
            report["bypasses"][0]["shunted_fraction"], 6.0 / 3000006.0, places=12
        )

    def test_bypass_hardware_is_listed(self):
        report = logic.assess_conductive_paths(base_config())
        self.assertEqual(
            report["bypasses"][0]["hardware"],
            ["deployer-chassis", "reel-drum", "structure-frame"],
        )

    def test_low_resistance_bypass_is_flagged(self):
        edges = base_edges(
            **{
                "e-reel": {"resistance_ohm": 1.0, "min_isolation_ohm": 0.5},
                "e-chassis-frame": {"resistance_ohm": 1.0, "min_isolation_ohm": 0.5},
                "e-frame-return": {"resistance_ohm": 1.0, "min_isolation_ohm": 0.5},
            }
        )
        report = logic.assess_conductive_paths(base_config(edges=edges))
        self.assertFalse(report["compliant"])
        self.assertEqual(len(report["bypass_findings"]), 1)
        self.assertAlmostEqual(report["bypasses"][0]["shunted_fraction"], 6.0 / 9.0, places=9)

    def test_small_fraction_does_not_excuse_sub_floor_isolation(self):
        report = logic.assess_conductive_paths(
            base_config(edges=base_edges(**{"e-reel": {"resistance_ohm": 1.0e3}}))
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["bypass_findings"], [])
        self.assertEqual(len(report["isolation_findings"]), 1)

    def test_fraction_exactly_at_the_allowance_is_compliant(self):
        edges = [
            {
                "id": "e-a",
                "from": "source-terminal",
                "to": "tether-far-end",
                "resistance_ohm": 0.1,
                "role": "intended",
            },
            {
                "id": "e-b",
                "from": "tether-far-end",
                "to": "return-terminal",
                "resistance_ohm": 0.2,
                "role": "intended",
            },
            {
                "id": "e-braid",
                "from": "source-terminal",
                "to": "return-terminal",
                "resistance_ohm": 29.7,
                "role": "parasitic",
                "hardware": "harness-shield",
                "min_isolation_ohm": 1.0,
            },
        ]
        report = logic.assess_conductive_paths(base_config(edges=edges))
        self.assertGreater(report["bypasses"][0]["shunted_fraction"], 0.01)
        self.assertTrue(report["compliant"], report["findings"])

    def test_fraction_genuinely_over_the_allowance_fails(self):
        edges = [
            {
                "id": "e-a",
                "from": "source-terminal",
                "to": "tether-far-end",
                "resistance_ohm": 0.1,
                "role": "intended",
            },
            {
                "id": "e-b",
                "from": "tether-far-end",
                "to": "return-terminal",
                "resistance_ohm": 0.2,
                "role": "intended",
            },
            {
                "id": "e-braid",
                "from": "source-terminal",
                "to": "return-terminal",
                "resistance_ohm": 25.0,
                "role": "parasitic",
                "hardware": "harness-shield",
                "min_isolation_ohm": 1.0,
            },
        ]
        report = logic.assess_conductive_paths(base_config(edges=edges))
        self.assertFalse(report["compliant"])
        self.assertIn("shunts", report["bypass_findings"][0])

    def test_circuit_without_an_intended_leg_raises(self):
        edges = base_edges(
            **{
                "e-tether": {"role": "parasitic", "hardware": "guide-roller", "min_isolation_ohm": 1.0},
                "e-contactor": {"role": "parasitic", "hardware": "latch-pin", "min_isolation_ohm": 1.0},
            }
        )
        with self.assertRaises(ValueError):
            logic.assess_conductive_paths(base_config(edges=edges))

    def test_unconnected_terminals_raise(self):
        edges = [
            {"id": "a", "from": "source-terminal", "to": "n2", "resistance_ohm": 1.0, "role": "intended"},
            {"id": "b", "from": "n3", "to": "return-terminal", "resistance_ohm": 1.0, "role": "intended"},
        ]
        with self.assertRaises(ValueError):
            logic.assess_conductive_paths(base_config(edges=edges))

    def test_config_not_a_mapping_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_conductive_paths("tether-circuit")

    def test_non_string_source_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_conductive_paths(base_config(source=7))

    def test_allowed_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_conductive_paths(base_config(allowed_shunted_fraction=1.5))

    def test_zero_allowed_fraction_raises(self):
        with self.assertRaises(ValueError):
            logic.assess_conductive_paths(base_config(allowed_shunted_fraction=0.0))

    def test_default_allowance_applies_when_absent(self):
        cfg = base_config()
        del cfg["allowed_shunted_fraction"]
        report = logic.assess_conductive_paths(cfg)
        self.assertTrue(report["compliant"], report["findings"])


if __name__ == "__main__":
    unittest.main()

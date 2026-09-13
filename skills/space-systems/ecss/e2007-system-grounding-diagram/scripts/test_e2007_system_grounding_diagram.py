#!/usr/bin/env python3
"""Gate 3 contract test for e2007-system-grounding-diagram.

Offline, deterministic, stdlib unittest. Exercises topology construction and
its error paths, vehicle-reference resolution, lowest-resistance return-path
tracing, isolation checking, independent-loop counting, the ground-support-
equipment domain crossing and the aggregate clause 4.2.10.2 verdict.
"""

import unittest

import e2007_system_grounding_diagram_logic as logic


def nominal_nodes():
    return [
        {
            "id": "vehicle-ground-reference",
            "domain": "flight-segment",
            "grounding": "single-point-grounded",
            "is_reference": True,
        },
        {
            "id": "power-conditioning-unit",
            "domain": "flight-segment",
            "grounding": "single-point-grounded",
        },
        {
            "id": "telemetry-encoder",
            "domain": "flight-segment",
            "grounding": "single-point-grounded",
        },
        {
            "id": "reaction-wheel-assembly",
            "domain": "flight-segment",
            "grounding": "multipoint-grounded",
        },
        {
            "id": "detector-head",
            "domain": "flight-segment",
            "grounding": "isolated",
        },
        {
            "id": "checkout-rack",
            "domain": "ground-support-equipment",
            "grounding": "multipoint-grounded",
        },
    ]


def nominal_links():
    return [
        {
            "a": "vehicle-ground-reference",
            "b": "power-conditioning-unit",
            "category": "dedicated-ground-conductor",
            "resistance_mohm": 4.0,
        },
        {
            "a": "vehicle-ground-reference",
            "b": "telemetry-encoder",
            "category": "dedicated-ground-conductor",
            "resistance_mohm": 3.0,
        },
        {
            "a": "vehicle-ground-reference",
            "b": "reaction-wheel-assembly",
            "category": "structure-bond",
            "resistance_mohm": 1.5,
        },
        {
            "a": "power-conditioning-unit",
            "b": "detector-head",
            "category": "mounting-isolator",
        },
        {
            "a": "vehicle-ground-reference",
            "b": "checkout-rack",
            "category": "umbilical-ground-interface",
            "resistance_mohm": 2.0,
        },
    ]


def nominal_topology():
    return logic.build_topology(nominal_nodes(), nominal_links())


class TestNormalizeToken(unittest.TestCase):
    def test_canonicalizes_case_and_whitespace(self):
        self.assertEqual(
            logic.normalize_token(
                "  Single-Point-Grounded ", logic.GROUNDING_CATEGORIES, "grounding"
            ),
            "single-point-grounded",
        )

    def test_rejects_uncategorized_token(self):
        with self.assertRaises(ValueError):
            logic.normalize_token("chassis-tied", logic.GROUNDING_CATEGORIES, "grounding")

    def test_rejects_non_string(self):
        with self.assertRaises(ValueError):
            logic.normalize_token(7, logic.NODE_DOMAINS, "node domain")

    def test_rejects_empty_string(self):
        with self.assertRaises(ValueError):
            logic.normalize_token("   ", logic.LINK_CATEGORIES, "link category")


class TestBuildTopology(unittest.TestCase):
    def test_builds_expected_node_and_link_counts(self):
        topology = nominal_topology()
        self.assertEqual(len(topology["nodes"]), 6)
        self.assertEqual(len(topology["links"]), 5)

    def test_mounting_isolator_is_not_conductive(self):
        topology = nominal_topology()
        isolators = [l for l in topology["links"] if l["category"] == "mounting-isolator"]
        self.assertEqual(len(isolators), 1)
        self.assertFalse(isolators[0]["conductive"])
        self.assertIsNone(isolators[0]["resistance_mohm"])
        self.assertEqual(topology["adjacency"]["detector-head"], [])

    def test_conductive_link_appears_in_both_directions(self):
        topology = nominal_topology()
        neighbours = dict(topology["adjacency"]["reaction-wheel-assembly"])
        self.assertIn("vehicle-ground-reference", neighbours)
        self.assertAlmostEqual(neighbours["vehicle-ground-reference"], 1.5)

    def test_rejects_duplicate_node_id(self):
        nodes = nominal_nodes()
        nodes.append(dict(nodes[1]))
        with self.assertRaises(ValueError):
            logic.build_topology(nodes, nominal_links())

    def test_rejects_link_endpoint_not_on_diagram(self):
        links = nominal_links()
        links.append(
            {
                "a": "vehicle-ground-reference",
                "b": "star-tracker",
                "category": "structure-bond",
                "resistance_mohm": 1.0,
            }
        )
        with self.assertRaises(ValueError):
            logic.build_topology(nominal_nodes(), links)

    def test_rejects_self_link(self):
        links = nominal_links()
        links.append(
            {
                "a": "telemetry-encoder",
                "b": "telemetry-encoder",
                "category": "structure-bond",
                "resistance_mohm": 1.0,
            }
        )
        with self.assertRaises(ValueError):
            logic.build_topology(nominal_nodes(), links)

    def test_rejects_negative_resistance(self):
        links = nominal_links()
        links[0]["resistance_mohm"] = -0.5
        with self.assertRaises(ValueError):
            logic.build_topology(nominal_nodes(), links)

    def test_rejects_non_numeric_resistance(self):
        links = nominal_links()
        links[0]["resistance_mohm"] = "4 mohm"
        with self.assertRaises(ValueError):
            logic.build_topology(nominal_nodes(), links)

    def test_rejects_boolean_resistance(self):
        links = nominal_links()
        links[0]["resistance_mohm"] = True
        with self.assertRaises(ValueError):
            logic.build_topology(nominal_nodes(), links)

    def test_rejects_infinite_resistance(self):
        links = nominal_links()
        links[0]["resistance_mohm"] = float("inf")
        with self.assertRaises(ValueError):
            logic.build_topology(nominal_nodes(), links)

    def test_rejects_uncategorized_grounding(self):
        nodes = nominal_nodes()
        nodes[1]["grounding"] = "floating-ish"
        with self.assertRaises(ValueError):
            logic.build_topology(nodes, nominal_links())

    def test_rejects_uncategorized_domain(self):
        nodes = nominal_nodes()
        nodes[5]["domain"] = "hangar"
        with self.assertRaises(ValueError):
            logic.build_topology(nodes, nominal_links())

    def test_rejects_empty_node_sequence(self):
        with self.assertRaises(ValueError):
            logic.build_topology([], [])

    def test_rejects_non_mapping_node_record(self):
        with self.assertRaises(ValueError):
            logic.build_topology(["vehicle-ground-reference"], [])

    def test_rejects_node_without_id(self):
        nodes = nominal_nodes()
        del nodes[2]["id"]
        with self.assertRaises(ValueError):
            logic.build_topology(nodes, nominal_links())


class TestReferenceResolution(unittest.TestCase):
    def test_returns_the_flagged_reference(self):
        self.assertEqual(
            logic.resolve_reference_node(nominal_topology()), "vehicle-ground-reference"
        )

    def test_raises_when_no_reference_is_flagged(self):
        nodes = nominal_nodes()
        nodes[0]["is_reference"] = False
        with self.assertRaises(ValueError):
            logic.resolve_reference_node(logic.build_topology(nodes, nominal_links()))

    def test_raises_when_two_references_are_flagged(self):
        nodes = nominal_nodes()
        nodes[2]["is_reference"] = True
        with self.assertRaises(ValueError):
            logic.resolve_reference_node(logic.build_topology(nodes, nominal_links()))


class TestPathTracing(unittest.TestCase):
    def test_direct_path_resistance(self):
        traced = logic.lowest_resistance_path(
            nominal_topology(), "power-conditioning-unit", "vehicle-ground-reference"
        )
        self.assertIsNotNone(traced)
        self.assertAlmostEqual(traced[0], 4.0)
        self.assertEqual(traced[1][0], "power-conditioning-unit")
        self.assertEqual(traced[1][-1], "vehicle-ground-reference")

    def test_prefers_the_lower_resistance_of_two_routes(self):
        links = nominal_links()
        links.append(
            {
                "a": "power-conditioning-unit",
                "b": "reaction-wheel-assembly",
                "category": "structure-bond",
                "resistance_mohm": 0.5,
            }
        )
        topology = logic.build_topology(nominal_nodes(), links)
        traced = logic.lowest_resistance_path(
            topology, "power-conditioning-unit", "vehicle-ground-reference"
        )
        self.assertAlmostEqual(traced[0], 2.0)
        self.assertIn("reaction-wheel-assembly", traced[1])

    def test_returns_none_for_an_isolated_unit(self):
        self.assertIsNone(
            logic.lowest_resistance_path(
                nominal_topology(), "detector-head", "vehicle-ground-reference"
            )
        )

    def test_zero_resistance_to_itself(self):
        traced = logic.lowest_resistance_path(
            nominal_topology(), "telemetry-encoder", "telemetry-encoder"
        )
        self.assertAlmostEqual(traced[0], 0.0)
        self.assertEqual(traced[1], ["telemetry-encoder"])

    def test_raises_for_unknown_node_id(self):
        with self.assertRaises(ValueError):
            logic.lowest_resistance_path(
                nominal_topology(), "sun-sensor", "vehicle-ground-reference"
            )


class TestLoopCounting(unittest.TestCase):
    def test_tree_topology_has_no_independent_loop(self):
        self.assertEqual(logic.count_independent_loops(nominal_topology()), 0)

    def test_redundant_strap_creates_one_loop(self):
        links = nominal_links()
        links.append(
            {
                "a": "power-conditioning-unit",
                "b": "telemetry-encoder",
                "category": "structure-bond",
                "resistance_mohm": 0.9,
            }
        )
        topology = logic.build_topology(nominal_nodes(), links)
        self.assertEqual(logic.count_independent_loops(topology), 1)

    def test_two_redundant_straps_create_two_loops(self):
        links = nominal_links()
        links.append(
            {
                "a": "power-conditioning-unit",
                "b": "telemetry-encoder",
                "category": "structure-bond",
                "resistance_mohm": 0.9,
            }
        )
        links.append(
            {
                "a": "power-conditioning-unit",
                "b": "reaction-wheel-assembly",
                "category": "structure-bond",
                "resistance_mohm": 0.9,
            }
        )
        topology = logic.build_topology(nominal_nodes(), links)
        self.assertEqual(logic.count_independent_loops(topology), 2)

    def test_raises_for_unknown_node_in_selection(self):
        with self.assertRaises(ValueError):
            logic.count_independent_loops(nominal_topology(), ["sun-sensor"])

    def test_raises_on_empty_selection(self):
        with self.assertRaises(ValueError):
            logic.count_independent_loops(nominal_topology(), [])


class TestUnitReturns(unittest.TestCase):
    def test_nominal_diagram_has_no_unit_finding(self):
        topology = nominal_topology()
        results = logic.evaluate_unit_returns(topology, "vehicle-ground-reference")
        self.assertEqual(len(results), 5)
        self.assertTrue(all(entry["compliant"] for entry in results))

    def test_flags_return_path_resistance_exceeded(self):
        links = nominal_links()
        links[2]["resistance_mohm"] = 4.0
        topology = logic.build_topology(nominal_nodes(), links)
        results = logic.evaluate_unit_returns(topology, "vehicle-ground-reference")
        wheel = [r for r in results if r["id"] == "reaction-wheel-assembly"][0]
        self.assertIn("return-path-resistance-exceeded", wheel["findings"])
        self.assertAlmostEqual(wheel["allowance_mohm"], 2.5)

    def test_flags_missing_return_path(self):
        links = [l for l in nominal_links() if l["b"] != "telemetry-encoder"]
        topology = logic.build_topology(nominal_nodes(), links)
        results = logic.evaluate_unit_returns(topology, "vehicle-ground-reference")
        encoder = [r for r in results if r["id"] == "telemetry-encoder"][0]
        self.assertIn("no-return-path-to-vehicle-reference", encoder["findings"])
        self.assertIsNone(encoder["path_resistance_mohm"])

    def test_flags_an_isolated_unit_that_is_actually_bonded(self):
        links = nominal_links()
        links[3] = {
            "a": "power-conditioning-unit",
            "b": "detector-head",
            "category": "structure-bond",
            "resistance_mohm": 0.4,
        }
        topology = logic.build_topology(nominal_nodes(), links)
        results = logic.evaluate_unit_returns(topology, "vehicle-ground-reference")
        head = [r for r in results if r["id"] == "detector-head"][0]
        self.assertIn("isolated-unit-conductively-bonded", head["findings"])

    def test_summed_path_exactly_at_the_allowance_is_compliant(self):
        nodes = nominal_nodes()
        for suffix in ("a", "b", "c"):
            nodes.append(
                {
                    "id": "relay-bracket-%s" % suffix,
                    "domain": "flight-segment",
                    "grounding": "single-point-grounded",
                }
            )
        links = nominal_links()
        links.append(
            {
                "a": "vehicle-ground-reference",
                "b": "relay-bracket-a",
                "category": "dedicated-ground-conductor",
                "resistance_mohm": 0.3,
            }
        )
        links.append(
            {
                "a": "relay-bracket-a",
                "b": "relay-bracket-b",
                "category": "dedicated-ground-conductor",
                "resistance_mohm": 7.9,
            }
        )
        links.append(
            {
                "a": "relay-bracket-b",
                "b": "relay-bracket-c",
                "category": "dedicated-ground-conductor",
                "resistance_mohm": 1.8,
            }
        )
        topology = logic.build_topology(nodes, links)
        traced = logic.lowest_resistance_path(
            topology, "relay-bracket-c", "vehicle-ground-reference"
        )
        self.assertAlmostEqual(traced[0], 10.0)
        # The summed route lands a few units in the last place above the 10.0
        # allowance although it physically meets it; the comparison tolerance
        # absorbs the representation error without moving the allowance.
        self.assertGreater(traced[0], 10.0)
        results = logic.evaluate_unit_returns(topology, "vehicle-ground-reference")
        bracket = [r for r in results if r["id"] == "relay-bracket-c"][0]
        self.assertEqual(bracket["findings"], [])
        self.assertTrue(bracket["compliant"])

    def test_tolerance_does_not_widen_the_allowance(self):
        self.assertTrue(logic._within(10.0, 10.0))
        self.assertFalse(logic._within(10.001, 10.0))
        self.assertFalse(logic._within(2.5001, 2.5))


class TestSinglePointLoops(unittest.TestCase):
    def test_nominal_single_point_domain_is_loop_free(self):
        verdict = logic.detect_single_point_loops(
            nominal_topology(), "vehicle-ground-reference"
        )
        self.assertEqual(verdict["loop_count"], 0)
        self.assertEqual(verdict["findings"], [])

    def test_flags_a_loop_closed_by_a_redundant_strap(self):
        links = nominal_links()
        links.append(
            {
                "a": "power-conditioning-unit",
                "b": "telemetry-encoder",
                "category": "structure-bond",
                "resistance_mohm": 0.9,
            }
        )
        topology = logic.build_topology(nominal_nodes(), links)
        verdict = logic.detect_single_point_loops(topology, "vehicle-ground-reference")
        self.assertEqual(verdict["loop_count"], 1)
        self.assertIn("ground-loop-in-single-point-domain", verdict["findings"])


class TestDomainCrossing(unittest.TestCase):
    def test_nominal_crossing_is_single_and_designated(self):
        verdict = logic.check_domain_crossing(nominal_topology())
        self.assertEqual(verdict["crossing_count"], 1)
        self.assertEqual(verdict["designated_crossing_count"], 1)
        self.assertEqual(verdict["findings"], [])

    def test_flags_a_diagram_without_ground_support_equipment(self):
        nodes = [n for n in nominal_nodes() if n["id"] != "checkout-rack"]
        links = [l for l in nominal_links() if l["b"] != "checkout-rack"]
        verdict = logic.check_domain_crossing(logic.build_topology(nodes, links))
        self.assertIn("ground-support-equipment-not-on-diagram", verdict["findings"])

    def test_flags_a_second_crossing_to_facility_earth(self):
        nodes = nominal_nodes()
        links = nominal_links()
        links.append(
            {
                "a": "checkout-rack",
                "b": "reaction-wheel-assembly",
                "category": "umbilical-ground-interface",
                "resistance_mohm": 3.0,
            }
        )
        verdict = logic.check_domain_crossing(logic.build_topology(nodes, links))
        self.assertEqual(verdict["crossing_count"], 2)
        self.assertIn(
            "multiple-ground-support-equipment-crossings", verdict["findings"]
        )

    def test_flags_an_undesignated_crossing_category(self):
        links = nominal_links()
        links[4]["category"] = "structure-bond"
        verdict = logic.check_domain_crossing(
            logic.build_topology(nominal_nodes(), links)
        )
        self.assertIn("undesignated-domain-crossing-bond", verdict["findings"])

    def test_flags_ground_support_equipment_with_no_crossing(self):
        links = [l for l in nominal_links() if l["b"] != "checkout-rack"]
        verdict = logic.check_domain_crossing(
            logic.build_topology(nominal_nodes(), links)
        )
        self.assertEqual(verdict["crossing_count"], 0)
        self.assertIn("no-umbilical-ground-interface", verdict["findings"])


class TestAssessment(unittest.TestCase):
    def test_nominal_diagram_is_compliant(self):
        report = logic.assess_grounding_diagram(nominal_nodes(), nominal_links())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["reference"], "vehicle-ground-reference")
        self.assertEqual(report["conductive_link_count"], 4)

    def test_aggregates_findings_from_every_check(self):
        nodes = nominal_nodes()
        links = nominal_links()
        links[2]["resistance_mohm"] = 9.0
        links.append(
            {
                "a": "power-conditioning-unit",
                "b": "telemetry-encoder",
                "category": "structure-bond",
                "resistance_mohm": 0.9,
            }
        )
        links.append(
            {
                "a": "checkout-rack",
                "b": "telemetry-encoder",
                "category": "structure-bond",
                "resistance_mohm": 1.0,
            }
        )
        report = logic.assess_grounding_diagram(nodes, links)
        self.assertFalse(report["compliant"])
        joined = " | ".join(report["findings"])
        self.assertIn("return-path-resistance-exceeded", joined)
        self.assertIn("ground-loop-in-single-point-domain", joined)
        self.assertIn("multiple-ground-support-equipment-crossings", joined)
        self.assertIn("undesignated-domain-crossing-bond", joined)

    def test_assessment_propagates_input_defects(self):
        nodes = nominal_nodes()
        nodes[0]["is_reference"] = False
        with self.assertRaises(ValueError):
            logic.assess_grounding_diagram(nodes, nominal_links())


class TestSummary(unittest.TestCase):
    def test_summary_reports_verdict_and_counts(self):
        report = logic.assess_grounding_diagram(nominal_nodes(), nominal_links())
        text = logic.summarize_assessment(report)
        self.assertIn("COMPLIANT", text)
        self.assertIn("vehicle-ground-reference", text)
        self.assertIn("6 node(s)", text)

    def test_summary_rejects_a_non_report(self):
        with self.assertRaises(ValueError):
            logic.summarize_assessment({"nodes": 3})


if __name__ == "__main__":
    unittest.main()

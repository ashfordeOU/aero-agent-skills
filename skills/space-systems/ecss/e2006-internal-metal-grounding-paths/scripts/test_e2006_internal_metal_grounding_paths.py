#!/usr/bin/env python3
"""Gate 3 contract test for e2006-internal-metal-grounding-paths.

Stdlib unittest, offline, deterministic. Run:
    python3 test_e2006_internal_metal_grounding_paths.py
"""

import math
import unittest

from e2006_internal_metal_grounding_paths_logic import (
    FAMILY_ROUTE_CAP_OHM,
    GROUNDING_REFERENCE,
    MAX_ROUTES_PER_ITEM,
    REQUIRED_INDEPENDENT_ROUTES,
    assess_internal_grounding,
    assess_item_grounding,
    categorize_internal_item,
    family_route_cap,
    max_independent_routes,
    route_resistance,
    route_within_cap,
    routes_are_independent,
    summarize_assessment,
    validate_route,
    validate_segment,
)


def seg(seg_id, ohm, node=GROUNDING_REFERENCE, kind="bond-strap"):
    return {
        "id": seg_id,
        "kind": kind,
        "resistance_ohm": ohm,
        "downstream_node": node,
    }


def route(route_id, segments):
    return {"id": route_id, "segments": segments}


class TestCategorizeInternalItem(unittest.TestCase):
    def test_harness_shield_is_shield_family(self):
        self.assertEqual(categorize_internal_item("harness-shield"), "shield")

    def test_backshell_is_enclosure_family(self):
        self.assertEqual(categorize_internal_item("connector-backshell"), "enclosure")

    def test_internal_bracket_is_structure_family(self):
        self.assertEqual(categorize_internal_item("internal-bracket"), "structure")

    def test_kind_is_case_and_space_insensitive(self):
        self.assertEqual(categorize_internal_item("  Equipment-Enclosure "), "enclosure")

    def test_uncategorized_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_internal_item("mystery-widget")

    def test_blank_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_internal_item("   ")

    def test_non_string_kind_raises(self):
        with self.assertRaises(ValueError):
            categorize_internal_item(17)


class TestFamilyRouteCap(unittest.TestCase):
    def test_shield_cap_matches_table(self):
        self.assertAlmostEqual(family_route_cap("shield"), FAMILY_ROUTE_CAP_OHM["shield"])

    def test_structure_cap_is_looser_than_shield(self):
        self.assertGreater(family_route_cap("structure"), family_route_cap("shield"))

    def test_unknown_family_raises(self):
        with self.assertRaises(ValueError):
            family_route_cap("plumbing")

    def test_non_string_family_raises(self):
        with self.assertRaises(ValueError):
            family_route_cap(None)


class TestValidateSegment(unittest.TestCase):
    def test_normalizes_kind_and_id(self):
        norm = validate_segment(
            {"id": " s1 ", "kind": "Bond-Strap", "resistance_ohm": 2}
        )
        self.assertEqual(norm["id"], "s1")
        self.assertEqual(norm["kind"], "bond-strap")
        self.assertAlmostEqual(norm["resistance_ohm"], 2.0)

    def test_defaults_downstream_node_to_reference(self):
        norm = validate_segment({"id": "s1", "kind": "fastener-bond", "resistance_ohm": 0.001})
        self.assertEqual(norm["downstream_node"], GROUNDING_REFERENCE)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_segment(["s1", 0.001])

    def test_blank_id_raises(self):
        with self.assertRaises(ValueError):
            validate_segment({"id": "", "kind": "bond-strap", "resistance_ohm": 0.001})

    def test_unrecognized_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_segment({"id": "s1", "kind": "duct-tape", "resistance_ohm": 0.001})

    def test_non_numeric_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_segment({"id": "s1", "kind": "bond-strap", "resistance_ohm": "low"})

    def test_boolean_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_segment({"id": "s1", "kind": "bond-strap", "resistance_ohm": True})

    def test_negative_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_segment({"id": "s1", "kind": "bond-strap", "resistance_ohm": -0.001})

    def test_non_finite_resistance_raises(self):
        with self.assertRaises(ValueError):
            validate_segment(
                {"id": "s1", "kind": "bond-strap", "resistance_ohm": float("inf")}
            )

    def test_blank_downstream_node_raises(self):
        with self.assertRaises(ValueError):
            validate_segment(
                {
                    "id": "s1",
                    "kind": "bond-strap",
                    "resistance_ohm": 0.001,
                    "downstream_node": "  ",
                }
            )


class TestRouteResistance(unittest.TestCase):
    def test_sums_segment_resistances(self):
        total = route_resistance([seg("a", 0.002), seg("b", 0.003)])
        self.assertAlmostEqual(total, 0.005)

    def test_single_segment_route(self):
        self.assertAlmostEqual(route_resistance([seg("a", 0.004)]), 0.004)

    def test_zero_resistance_weld_allowed(self):
        self.assertAlmostEqual(
            route_resistance([seg("w", 0.0, kind="structural-weld")]), 0.0
        )

    def test_empty_route_raises(self):
        with self.assertRaises(ValueError):
            route_resistance([])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            route_resistance("a,b")

    def test_repeated_segment_raises(self):
        with self.assertRaises(ValueError):
            route_resistance([seg("a", 0.002), seg("a", 0.002)])


class TestValidateRoute(unittest.TestCase):
    def test_collects_segment_ids_and_total(self):
        norm = validate_route(route("r1", [seg("a", 0.002), seg("b", 0.003)]))
        self.assertEqual(norm["segment_ids"], frozenset({"a", "b"}))
        self.assertAlmostEqual(norm["resistance_ohm"], 0.005)

    def test_reference_endpoint_is_not_a_tie_point(self):
        norm = validate_route(route("r1", [seg("a", 0.002)]))
        self.assertEqual(norm["tie_points"], frozenset())

    def test_intermediate_node_becomes_tie_point(self):
        norm = validate_route(
            route("r1", [seg("a", 0.002, node="bracket-7"), seg("b", 0.002)])
        )
        self.assertEqual(norm["tie_points"], frozenset({"bracket-7"}))

    def test_non_mapping_route_raises(self):
        with self.assertRaises(ValueError):
            validate_route([seg("a", 0.002)])

    def test_blank_route_id_raises(self):
        with self.assertRaises(ValueError):
            validate_route({"id": "  ", "segments": [seg("a", 0.002)]})

    def test_route_without_segments_raises(self):
        with self.assertRaises(ValueError):
            validate_route({"id": "r1", "segments": []})


class TestRouteWithinCap(unittest.TestCase):
    def test_comfortably_below_cap(self):
        self.assertTrue(route_within_cap(0.004, 0.010))

    def test_exactly_on_cap(self):
        self.assertTrue(route_within_cap(0.010, 0.010))

    def test_float_sum_a_few_ulps_over_cap_is_still_compliant(self):
        total = route_resistance([seg("a", 0.0008), seg("b", 0.0041), seg("c", 0.0051)])
        self.assertGreater(total, 0.010)
        self.assertTrue(route_within_cap(total, 0.010))

    def test_genuine_exceedance_is_rejected(self):
        self.assertFalse(route_within_cap(0.0101, 0.010))


class TestRouteIndependence(unittest.TestCase):
    def setUp(self):
        self.r1 = validate_route(route("r1", [seg("a", 0.002)]))
        self.r2 = validate_route(route("r2", [seg("b", 0.002)]))

    def test_disjoint_routes_are_independent(self):
        self.assertTrue(routes_are_independent(self.r1, self.r2))

    def test_shared_segment_breaks_independence(self):
        shared = validate_route(route("r3", [seg("a", 0.002), seg("c", 0.001)]))
        self.assertFalse(routes_are_independent(self.r1, shared))

    def test_shared_tie_point_breaks_independence(self):
        left = validate_route(route("r4", [seg("d", 0.002, node="bracket-7"), seg("e", 0.001)]))
        right = validate_route(route("r5", [seg("f", 0.002, node="bracket-7"), seg("g", 0.001)]))
        self.assertFalse(routes_are_independent(left, right))

    def test_same_route_is_not_independent_of_itself(self):
        self.assertFalse(routes_are_independent(self.r1, self.r1))


class TestMaxIndependentRoutes(unittest.TestCase):
    def test_no_routes_gives_zero(self):
        self.assertEqual(max_independent_routes([]), 0)

    def test_one_route_gives_one(self):
        routes = [validate_route(route("r1", [seg("a", 0.002)]))]
        self.assertEqual(max_independent_routes(routes), 1)

    def test_two_disjoint_routes_give_two(self):
        routes = [
            validate_route(route("r1", [seg("a", 0.002)])),
            validate_route(route("r2", [seg("b", 0.002)])),
        ]
        self.assertEqual(max_independent_routes(routes), 2)

    def test_three_straps_on_one_bracket_give_one(self):
        routes = [
            validate_route(route("r%d" % i, [seg("s%d" % i, 0.002, node="bracket-7"), seg("t%d" % i, 0.001)]))
            for i in range(3)
        ]
        self.assertEqual(max_independent_routes(routes), 1)

    def test_mixed_set_finds_the_independent_pair(self):
        routes = [
            validate_route(route("r1", [seg("a", 0.002, node="bracket-7"), seg("z1", 0.001)])),
            validate_route(route("r2", [seg("b", 0.002, node="bracket-7"), seg("z2", 0.001)])),
            validate_route(route("r3", [seg("c", 0.002)])),
        ]
        self.assertEqual(max_independent_routes(routes), 2)

    def test_too_many_routes_raises(self):
        routes = [
            validate_route(route("r%d" % i, [seg("s%d" % i, 0.001)]))
            for i in range(MAX_ROUTES_PER_ITEM + 1)
        ]
        with self.assertRaises(ValueError):
            max_independent_routes(routes)


class TestAssessItemGrounding(unittest.TestCase):
    def test_two_independent_routes_are_compliant(self):
        item = {
            "id": "shield-12",
            "kind": "harness-shield",
            "routes": [
                route("r1", [seg("a", 0.003, kind="shield-pigtail")]),
                route("r2", [seg("b", 0.004, kind="backshell-termination")]),
            ],
        }
        result = assess_item_grounding(item)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["independent_route_count"], REQUIRED_INDEPENDENT_ROUTES)
        self.assertEqual(result["findings"], [])

    def test_single_route_item_is_flagged(self):
        item = {
            "id": "bracket-3",
            "kind": "internal-bracket",
            "routes": [route("r1", [seg("a", 0.005, kind="fastener-bond")])],
        }
        result = assess_item_grounding(item)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["independent_route_count"], 1)
        self.assertIn("clause 9.2.2", " ".join(result["findings"]))

    def test_shared_bracket_pseudo_redundancy_is_flagged(self):
        item = {
            "id": "enclosure-9",
            "kind": "equipment-enclosure",
            "routes": [
                route("r1", [seg("a", 0.002, node="bracket-7"), seg("c", 0.001)]),
                route("r2", [seg("b", 0.002, node="bracket-7"), seg("d", 0.001)]),
            ],
        }
        result = assess_item_grounding(item)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["usable_route_count"], 2)
        self.assertEqual(result["independent_route_count"], 1)
        self.assertIn("independent", " ".join(result["findings"]))

    def test_over_resistance_route_does_not_supply_redundancy(self):
        item = {
            "id": "shield-4",
            "kind": "harness-shield",
            "routes": [
                route("r1", [seg("a", 0.003, kind="shield-pigtail")]),
                route("r2", [seg("b", 0.050, kind="shield-pigtail")]),
            ],
        }
        result = assess_item_grounding(item)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["usable_route_count"], 1)
        self.assertTrue(any("above the" in f for f in result["findings"]))

    def test_every_route_over_cap_reports_no_usable_route(self):
        item = {
            "id": "shield-5",
            "kind": "harness-shield",
            "routes": [
                route("r1", [seg("a", 0.9, kind="shield-pigtail")]),
                route("r2", [seg("b", 0.8, kind="shield-pigtail")]),
            ],
        }
        result = assess_item_grounding(item)
        self.assertEqual(result["independent_route_count"], 0)
        self.assertTrue(any("no usable grounding route" in f for f in result["findings"]))

    def test_boundary_route_total_stays_compliant(self):
        item = {
            "id": "shield-6",
            "kind": "harness-shield",
            "routes": [
                route(
                    "r1",
                    [
                        seg("a", 0.0008, kind="shield-pigtail"),
                        seg("b", 0.0041, kind="bond-strap"),
                        seg("c", 0.0051, kind="bond-strap"),
                    ],
                ),
                route("r2", [seg("d", 0.004, kind="backshell-termination")]),
            ],
        }
        result = assess_item_grounding(item)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["usable_route_count"], 2)

    def test_structure_family_gets_the_looser_cap(self):
        item = {
            "id": "panel-2",
            "kind": "internal-panel",
            "routes": [
                route("r1", [seg("a", 0.020, kind="fastener-bond")]),
                route("r2", [seg("b", 0.018, kind="structural-weld")]),
            ],
        }
        result = assess_item_grounding(item)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["cap_ohm"], FAMILY_ROUTE_CAP_OHM["structure"])

    def test_cap_override_tightens_the_screen(self):
        item = {
            "id": "panel-3",
            "kind": "internal-panel",
            "routes": [
                route("r1", [seg("a", 0.020, kind="fastener-bond")]),
                route("r2", [seg("b", 0.018, kind="structural-weld")]),
            ],
        }
        result = assess_item_grounding(item, caps={"structure": 0.005})
        self.assertFalse(result["compliant"])
        self.assertEqual(result["usable_route_count"], 0)

    def test_non_positive_cap_override_raises(self):
        item = {
            "id": "panel-4",
            "kind": "internal-panel",
            "routes": [route("r1", [seg("a", 0.002)])],
        }
        with self.assertRaises(ValueError):
            assess_item_grounding(item, caps={"structure": 0.0})

    def test_non_mapping_cap_override_raises(self):
        item = {
            "id": "panel-5",
            "kind": "internal-panel",
            "routes": [route("r1", [seg("a", 0.002)])],
        }
        with self.assertRaises(ValueError):
            assess_item_grounding(item, caps=[("structure", 0.01)])

    def test_uncategorized_item_kind_raises(self):
        with self.assertRaises(ValueError):
            assess_item_grounding({"id": "x", "kind": "gizmo", "routes": []})

    def test_blank_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_item_grounding({"id": " ", "kind": "internal-bracket", "routes": []})

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            assess_item_grounding(["internal-bracket"])

    def test_routes_not_a_list_raises(self):
        with self.assertRaises(ValueError):
            assess_item_grounding(
                {"id": "b1", "kind": "internal-bracket", "routes": "r1"}
            )

    def test_duplicate_route_id_raises(self):
        item = {
            "id": "b2",
            "kind": "internal-bracket",
            "routes": [route("r1", [seg("a", 0.002)]), route("r1", [seg("b", 0.002)])],
        }
        with self.assertRaises(ValueError):
            assess_item_grounding(item)

    def test_item_with_no_routes_reports_zero_independent(self):
        result = assess_item_grounding(
            {"id": "b3", "kind": "internal-bracket", "routes": []}
        )
        self.assertEqual(result["independent_route_count"], 0)
        self.assertFalse(result["compliant"])


class TestAssessInternalGrounding(unittest.TestCase):
    def _good_item(self, item_id):
        return {
            "id": item_id,
            "kind": "harness-shield",
            "routes": [
                route(item_id + "-r1", [seg(item_id + "-a", 0.003, kind="shield-pigtail")]),
                route(item_id + "-r2", [seg(item_id + "-b", 0.004, kind="backshell-termination")]),
            ],
        }

    def test_all_compliant_campaign(self):
        report = assess_internal_grounding([self._good_item("s1"), self._good_item("s2")])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["item_count"], 2)
        self.assertEqual(report["non_compliant_items"], [])

    def test_one_bad_item_fails_the_campaign(self):
        bad = {
            "id": "s3",
            "kind": "harness-shield",
            "routes": [route("s3-r1", [seg("s3-a", 0.003, kind="shield-pigtail")])],
        }
        report = assess_internal_grounding([self._good_item("s1"), bad])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_items"], ["s3"])

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_internal_grounding([])

    def test_non_list_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_internal_grounding({"id": "s1"})

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            assess_internal_grounding([self._good_item("s1"), self._good_item("s1")])


class TestSummarizeAssessment(unittest.TestCase):
    def test_compliant_summary_text(self):
        report = assess_internal_grounding(
            [
                {
                    "id": "s1",
                    "kind": "harness-shield",
                    "routes": [
                        route("r1", [seg("a", 0.003, kind="shield-pigtail")]),
                        route("r2", [seg("b", 0.004, kind="backshell-termination")]),
                    ],
                }
            ]
        )
        text = summarize_assessment(report)
        self.assertIn("COMPLIANT", text)
        self.assertIn("1 item(s)", text)

    def test_non_compliant_summary_counts_findings(self):
        report = assess_internal_grounding(
            [
                {
                    "id": "s1",
                    "kind": "harness-shield",
                    "routes": [route("r1", [seg("a", 0.003, kind="shield-pigtail")])],
                }
            ]
        )
        self.assertIn("NON-COMPLIANT", summarize_assessment(report))

    def test_summary_of_non_report_raises(self):
        with self.assertRaises(ValueError):
            summarize_assessment({"compliant": True})


class TestDeterminism(unittest.TestCase):
    def test_repeated_assessment_is_identical(self):
        item = {
            "id": "s1",
            "kind": "harness-shield",
            "routes": [
                route("r1", [seg("a", 0.003, kind="shield-pigtail")]),
                route("r2", [seg("b", 0.004, kind="backshell-termination")]),
            ],
        }
        first = assess_item_grounding(item)
        second = assess_item_grounding(item)
        self.assertEqual(first, second)

    def test_caps_table_values_are_finite_and_positive(self):
        for family, cap in FAMILY_ROUTE_CAP_OHM.items():
            self.assertTrue(math.isfinite(cap), family)
            self.assertGreater(cap, 0.0, family)


if __name__ == "__main__":
    unittest.main()

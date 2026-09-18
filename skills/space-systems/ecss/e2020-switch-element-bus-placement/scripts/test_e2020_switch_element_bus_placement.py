#!/usr/bin/env python3
"""Contract test for the switching element bus placement leaf (offline)."""

import copy
import unittest

from e2020_switch_element_bus_placement_logic import (
    DEFAULT_MAX_LIVE_STUB_M,
    ELEMENT_KINDS,
    EXPOSED_KINDS,
    PLACEMENT_COMPLIANT,
    PLACEMENT_NON_COMPLIANT,
    RAIL_ENERGISED,
    RAIL_LOAD,
    RAIL_RETURN,
    assess_switch_placement,
    bypass_feeds_downstream,
    exposed_live_interfaces,
    isolated_when_open,
    isolation_coverage_fraction,
    live_stub_length_m,
    live_when_open,
    load_index,
    protected_elements,
    switch_on_energised_rail,
    switching_element_index,
    validate_chain,
)

BUS_SIDE_CHAIN = [
    {"id": "main-bus-a", "kind": "main-bus", "rail": RAIL_ENERGISED},
    {"id": "lcl-pass-fet", "kind": "switching-element", "rail": RAIL_ENERGISED},
    {"id": "lcl-shunt", "kind": "current-sensor", "rail": RAIL_ENERGISED},
    {"id": "out-connector", "kind": "connector", "rail": RAIL_ENERGISED},
    {"id": "feed-harness", "kind": "harness", "rail": RAIL_ENERGISED, "length_m": 1.8},
    {"id": "unit-load", "kind": "load", "rail": RAIL_LOAD},
    {"id": "return-harness", "kind": "harness", "rail": RAIL_RETURN, "length_m": 1.8},
    {"id": "bus-return-a", "kind": "bus-return", "rail": RAIL_RETURN},
]

RETURN_SIDE_CHAIN = [
    {"id": "main-bus-a", "kind": "main-bus", "rail": RAIL_ENERGISED},
    {"id": "lcl-shunt", "kind": "current-sensor", "rail": RAIL_ENERGISED},
    {"id": "out-connector", "kind": "connector", "rail": RAIL_ENERGISED},
    {"id": "feed-harness", "kind": "harness", "rail": RAIL_ENERGISED, "length_m": 1.8},
    {"id": "unit-load", "kind": "load", "rail": RAIL_LOAD},
    {"id": "lcl-pass-fet", "kind": "switching-element", "rail": RAIL_RETURN},
    {"id": "return-harness", "kind": "harness", "rail": RAIL_RETURN, "length_m": 1.8},
    {"id": "bus-return-a", "kind": "bus-return", "rail": RAIL_RETURN},
]


def _chain(source=None, **replacements):
    chain = copy.deepcopy(source if source is not None else BUS_SIDE_CHAIN)
    for element_id, patch in replacements.items():
        for element in chain:
            if element["id"].replace("-", "_") == element_id:
                element.update(patch)
    return chain


def _branch(**overrides):
    branch = {"branch_id": "pcdu-branch-07", "chain": copy.deepcopy(BUS_SIDE_CHAIN)}
    branch.update(overrides)
    return branch


class ChainValidationTests(unittest.TestCase):
    def test_a_well_formed_chain_is_returned_in_order(self):
        elements = validate_chain(BUS_SIDE_CHAIN)
        self.assertEqual(elements[0]["kind"], "main-bus")
        self.assertEqual(elements[-1]["kind"], "bus-return")
        self.assertEqual(len(elements), len(BUS_SIDE_CHAIN))

    def test_an_empty_chain_is_refused(self):
        with self.assertRaises(ValueError):
            validate_chain([])

    def test_a_chain_that_is_not_a_sequence_is_refused(self):
        with self.assertRaises(ValueError):
            validate_chain("main-bus")

    def test_a_chain_shorter_than_three_elements_is_refused(self):
        with self.assertRaises(ValueError):
            validate_chain(
                [
                    {"id": "main-bus-a", "kind": "main-bus", "rail": RAIL_ENERGISED},
                    {"id": "bus-return-a", "kind": "bus-return", "rail": RAIL_RETURN},
                ]
            )

    def test_an_unknown_element_kind_is_refused(self):
        chain = _chain()
        chain[2]["kind"] = "magic-box"
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_an_unknown_rail_is_refused(self):
        chain = _chain()
        chain[2]["rail"] = "middle"
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_a_duplicate_element_id_is_refused(self):
        chain = _chain()
        chain[3]["id"] = chain[2]["id"]
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_a_nameless_element_is_refused(self):
        chain = _chain()
        chain[2]["id"] = "   "
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_a_negative_harness_length_is_refused(self):
        chain = _chain()
        chain[4]["length_m"] = -0.2
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_two_switching_elements_are_refused(self):
        chain = _chain()
        chain[2]["kind"] = "switching-element"
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_a_chain_that_does_not_start_at_the_main_bus_is_refused(self):
        chain = _chain()[1:]
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_an_energised_element_after_the_load_is_refused(self):
        chain = _chain()
        chain[6]["rail"] = RAIL_ENERGISED
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_a_crossing_element_that_is_not_the_load_is_refused(self):
        chain = _chain()
        chain[5]["kind"] = "filter"
        chain.append({"id": "extra-load", "kind": "load", "rail": RAIL_RETURN})
        with self.assertRaises(ValueError):
            validate_chain(chain)

    def test_the_element_kind_and_exposed_vocabularies_agree(self):
        for kind in EXPOSED_KINDS:
            self.assertIn(kind, ELEMENT_KINDS)


class PlacementGeometryTests(unittest.TestCase):
    def test_a_bus_side_switch_sits_on_the_energised_rail(self):
        self.assertTrue(switch_on_energised_rail(BUS_SIDE_CHAIN))

    def test_a_return_side_switch_does_not(self):
        self.assertFalse(switch_on_energised_rail(RETURN_SIDE_CHAIN))

    def test_the_switch_index_precedes_the_load_when_placed_on_the_bus_side(self):
        self.assertLess(
            switching_element_index(BUS_SIDE_CHAIN), load_index(BUS_SIDE_CHAIN)
        )

    def test_the_switch_index_follows_the_load_on_the_return_side(self):
        self.assertGreater(
            switching_element_index(RETURN_SIDE_CHAIN), load_index(RETURN_SIDE_CHAIN)
        )

    def test_only_the_bus_interface_stays_live_behind_a_bus_side_switch(self):
        self.assertEqual(
            live_when_open(BUS_SIDE_CHAIN), ("main-bus-a", "lcl-pass-fet")
        )

    def test_everything_up_to_the_load_stays_live_behind_a_return_side_switch(self):
        live = live_when_open(RETURN_SIDE_CHAIN)
        self.assertIn("unit-load", live)
        self.assertIn("feed-harness", live)

    def test_live_and_isolated_sets_partition_the_chain(self):
        for chain in (BUS_SIDE_CHAIN, RETURN_SIDE_CHAIN):
            live = set(live_when_open(chain))
            isolated = set(isolated_when_open(chain))
            self.assertEqual(live & isolated, set())
            self.assertEqual(len(live) + len(isolated), len(chain))

    def test_the_protected_set_excludes_the_bus_ends_and_the_switch_itself(self):
        protected = protected_elements(BUS_SIDE_CHAIN)
        self.assertNotIn("main-bus-a", protected)
        self.assertNotIn("bus-return-a", protected)
        self.assertNotIn("lcl-pass-fet", protected)
        self.assertIn("unit-load", protected)


class CoverageTests(unittest.TestCase):
    def test_a_bus_side_switch_covers_every_protected_element(self):
        self.assertAlmostEqual(
            isolation_coverage_fraction(BUS_SIDE_CHAIN), 1.0, places=9
        )

    def test_a_return_side_switch_covers_almost_nothing(self):
        self.assertAlmostEqual(
            isolation_coverage_fraction(RETURN_SIDE_CHAIN), 1.0 / 5.0, places=9
        )

    def test_coverage_never_leaves_the_unit_interval(self):
        for chain in (BUS_SIDE_CHAIN, RETURN_SIDE_CHAIN):
            coverage = isolation_coverage_fraction(chain)
            self.assertGreaterEqual(coverage, 0.0)
            self.assertLessEqual(coverage, 1.0)

    def test_no_reachable_interface_is_live_behind_a_bus_side_switch(self):
        self.assertEqual(exposed_live_interfaces(BUS_SIDE_CHAIN), ())

    def test_the_connector_and_harness_are_live_behind_a_return_side_switch(self):
        exposed = exposed_live_interfaces(RETURN_SIDE_CHAIN)
        self.assertIn("out-connector", exposed)
        self.assertIn("feed-harness", exposed)

    def test_the_live_stub_is_empty_behind_a_bus_side_switch(self):
        self.assertAlmostEqual(live_stub_length_m(BUS_SIDE_CHAIN), 0.0, places=9)

    def test_the_live_stub_carries_the_feed_harness_on_the_return_side(self):
        self.assertAlmostEqual(live_stub_length_m(RETURN_SIDE_CHAIN), 1.8, places=9)


class BypassFeedTests(unittest.TestCase):
    def test_no_feeds_means_no_offenders(self):
        self.assertEqual(bypass_feeds_downstream(BUS_SIDE_CHAIN, None), ())

    def test_a_feed_landing_downstream_of_the_switch_is_named(self):
        feeds = [{"id": "cross-strap-b", "injects_at": "out-connector"}]
        self.assertEqual(
            bypass_feeds_downstream(BUS_SIDE_CHAIN, feeds), ("cross-strap-b",)
        )

    def test_a_feed_landing_upstream_of_the_switch_is_not_an_offender(self):
        feeds = [{"id": "cross-strap-b", "injects_at": "main-bus-a"}]
        self.assertEqual(bypass_feeds_downstream(BUS_SIDE_CHAIN, feeds), ())

    def test_a_feed_pointing_at_an_unknown_node_is_refused(self):
        feeds = [{"id": "cross-strap-b", "injects_at": "nowhere"}]
        with self.assertRaises(ValueError):
            bypass_feeds_downstream(BUS_SIDE_CHAIN, feeds)

    def test_a_feed_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            bypass_feeds_downstream(BUS_SIDE_CHAIN, ["cross-strap-b"])


class AssessmentTests(unittest.TestCase):
    def test_a_bus_side_branch_is_compliant(self):
        result = assess_switch_placement(_branch())
        self.assertEqual(result["verdict"], PLACEMENT_COMPLIANT)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["branch_id"], "pcdu-branch-07")

    def test_a_return_side_branch_is_not_compliant(self):
        result = assess_switch_placement(
            _branch(chain=copy.deepcopy(RETURN_SIDE_CHAIN))
        )
        self.assertEqual(result["verdict"], PLACEMENT_NON_COMPLIANT)
        self.assertFalse(result["switch_on_energised_rail"])
        self.assertTrue(any("energised main bus side" in f for f in result["findings"]))

    def test_a_return_side_branch_reports_the_load_still_tied_to_the_bus(self):
        result = assess_switch_placement(
            _branch(chain=copy.deepcopy(RETURN_SIDE_CHAIN))
        )
        self.assertTrue(any("downstream of the load" in f for f in result["findings"]))

    def test_a_switch_behind_the_output_connector_leaves_it_live(self):
        chain = copy.deepcopy(BUS_SIDE_CHAIN)
        chain[1], chain[3] = chain[3], chain[1]
        result = assess_switch_placement(_branch(chain=chain))
        self.assertEqual(result["verdict"], PLACEMENT_NON_COMPLIANT)
        self.assertIn("out-connector", result["exposed_live_interfaces"])

    def test_a_long_live_stub_is_measured_against_the_declared_limit(self):
        chain = copy.deepcopy(BUS_SIDE_CHAIN)
        chain.insert(1, {"id": "bus-stub", "kind": "harness", "rail": RAIL_ENERGISED, "length_m": 0.4})
        result = assess_switch_placement(_branch(chain=chain, max_live_stub_m=0.25))
        self.assertAlmostEqual(result["live_stub_length_m"], 0.4, places=9)
        self.assertTrue(any("harness stub" in f for f in result["findings"]))

    def test_a_stub_exactly_at_the_limit_is_accepted(self):
        chain = copy.deepcopy(BUS_SIDE_CHAIN)
        chain.insert(
            1,
            {"id": "bus-stub", "kind": "harness", "rail": RAIL_ENERGISED, "length_m": DEFAULT_MAX_LIVE_STUB_M},
        )
        result = assess_switch_placement(_branch(chain=chain))
        self.assertAlmostEqual(
            result["live_stub_length_m"], DEFAULT_MAX_LIVE_STUB_M, places=9
        )
        self.assertFalse(any("harness stub" in f for f in result["findings"]))

    def test_a_downstream_bypass_feed_defeats_an_otherwise_correct_placement(self):
        result = assess_switch_placement(
            _branch(bypass_feeds=[{"id": "cross-strap-b", "injects_at": "feed-harness"}])
        )
        self.assertEqual(result["verdict"], PLACEMENT_NON_COMPLIANT)
        self.assertEqual(result["bypass_feeds_downstream"], ("cross-strap-b",))

    def test_a_branch_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_switch_placement(BUS_SIDE_CHAIN)

    def test_a_negative_stub_limit_is_refused(self):
        with self.assertRaises(ValueError):
            assess_switch_placement(_branch(max_live_stub_m=-1.0))

    def test_the_assessment_does_not_mutate_the_caller_chain(self):
        branch = _branch()
        before = copy.deepcopy(branch)
        assess_switch_placement(branch)
        self.assertEqual(branch, before)


if __name__ == "__main__":
    unittest.main()

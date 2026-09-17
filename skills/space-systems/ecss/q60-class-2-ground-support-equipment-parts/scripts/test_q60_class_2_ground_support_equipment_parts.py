"""Contract tests for the clause 5.1.5 Class 2 ground support equipment parts logic."""

import unittest

from q60_class_2_ground_support_equipment_parts_logic import (
    CLOSURE_TOLERANCE,
    DIRECT_SOURCING_OBLIGATIONS,
    IDENTITY_FLOOR_OBLIGATIONS,
    INDIRECT_SOURCING_OBLIGATIONS,
    IN_SCOPE_STATUSES,
    MANDATORY_PART_ATTRIBUTES,
    OBSERVING_OBLIGATIONS,
    assess_gse_parts_control,
    boundary_status,
    connection_path,
    evaluate_gse_part,
    inherited_obligations,
    obligation_closure,
    obligation_tier,
    validate_node_id,
    validate_topology,
)


def topology(**overrides):
    """Return a representative Class 2 bench, with optional node overrides."""
    bench = {
        "umbilical": {"kind": "flight-interface", "feeds": []},
        "driver": {"kind": "bench-node", "feeds": ["umbilical"]},
        "psu": {"kind": "bench-node", "feeds": ["driver"]},
        "opto": {"kind": "isolation-stage", "qualified": True, "feeds": ["driver"]},
        "logger": {"kind": "bench-node", "feeds": ["opto"]},
        "series-r": {"kind": "isolation-stage", "qualified": False, "feeds": ["driver"]},
        "monitor": {"kind": "bench-node", "feeds": ["series-r"]},
        "fuse": {"kind": "protective-element", "verified": True, "feeds": ["driver"]},
        "heater": {"kind": "bench-node", "feeds": ["fuse"]},
        "crowbar": {"kind": "protective-element", "verified": False, "feeds": ["driver"]},
        "pump": {"kind": "bench-node", "feeds": ["crowbar"]},
        "rack-fan": {"kind": "bench-node", "feeds": []},
    }
    bench.update(overrides)
    return bench


def part(**overrides):
    """Return one fully evidenced direct sourcing bench part."""
    base = {
        "part_id": "G001",
        "part_number": "LM117H",
        "node_id": "driver",
        "can_drive_flight_side": True,
        "evidence_held": list(DIRECT_SOURCING_OBLIGATIONS),
    }
    base.update(overrides)
    return base


class ValidateNodeIdTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_node_id("  driver "), "driver")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_id("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_id(7)


class TopologyValidationTests(unittest.TestCase):
    def test_representative_bench_validates(self):
        validated = validate_topology(topology())
        self.assertEqual(validated["driver"]["feeds"], ("umbilical",))

    def test_empty_topology_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology({})

    def test_unknown_node_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(spare={"kind": "mystery-box", "feeds": []}))

    def test_node_without_a_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(spare={"feeds": []}))

    def test_dangling_downstream_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(spare={"kind": "bench-node", "feeds": ["ghost"]}))

    def test_self_feeding_node_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(spare={"kind": "bench-node", "feeds": ["spare"]}))

    def test_flight_interface_feeding_onward_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(umbilical={"kind": "flight-interface", "feeds": ["driver"]}))

    def test_isolation_stage_must_declare_qualification(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(opto={"kind": "isolation-stage", "feeds": ["driver"]}))

    def test_protective_element_must_declare_verification(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(fuse={"kind": "protective-element", "feeds": ["driver"]}))

    def test_bench_without_a_flight_interface_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology({"a": {"kind": "bench-node", "feeds": []}})

    def test_looping_bench_is_refused_rather_than_walked(self):
        looped = topology(
            driver={"kind": "bench-node", "feeds": ["umbilical", "psu"]},
            psu={"kind": "bench-node", "feeds": ["driver"]},
        )
        with self.assertRaises(ValueError):
            validate_topology(looped)

    def test_duplicate_feed_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(topology(psu={"kind": "bench-node", "feeds": ["driver", "driver"]}))

    def test_non_mapping_topology_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology(["driver"])


class ConnectionPathTests(unittest.TestCase):
    def test_part_on_the_connector_is_one_hop_away(self):
        self.assertEqual(connection_path(topology(), "driver"), ("driver", "umbilical"))

    def test_chain_is_walked_rather_than_eyeballed(self):
        self.assertEqual(
            connection_path(topology(), "psu"), ("psu", "driver", "umbilical")
        )

    def test_qualified_isolation_breaks_the_chain(self):
        self.assertEqual(connection_path(topology(), "logger"), ())

    def test_ignoring_the_break_shows_the_chain_was_there(self):
        self.assertEqual(
            connection_path(topology(), "logger", through_qualified_isolation=True),
            ("logger", "opto", "driver", "umbilical"),
        )

    def test_unconnected_part_has_no_chain_either_way(self):
        self.assertEqual(connection_path(topology(), "rack-fan"), ())
        self.assertEqual(
            connection_path(topology(), "rack-fan", through_qualified_isolation=True), ()
        )

    def test_part_at_an_unknown_node_rejected(self):
        with self.assertRaises(ValueError):
            connection_path(topology(), "not-on-the-bench")

    def test_alternative_open_route_beats_a_qualified_stage(self):
        bench = topology(
            logger={"kind": "bench-node", "feeds": ["opto", "psu"]},
        )
        self.assertEqual(
            connection_path(bench, "logger"), ("logger", "psu", "driver", "umbilical")
        )


class BoundaryStatusTests(unittest.TestCase):
    def test_connector_part_is_direct(self):
        status, hops, _, _ = boundary_status(topology(), "driver")
        self.assertEqual(status, "direct")
        self.assertEqual(hops, 1)

    def test_part_further_back_is_indirect_not_exempt(self):
        status, hops, _, _ = boundary_status(topology(), "psu")
        self.assertEqual(status, "indirect")
        self.assertEqual(hops, 2)

    def test_qualified_isolation_puts_the_part_outside(self):
        status, _, _, _ = boundary_status(topology(), "logger")
        self.assertEqual(status, "isolated")
        self.assertNotIn(status, IN_SCOPE_STATUSES)

    def test_rack_part_was_never_inside(self):
        status, hops, path, _ = boundary_status(topology(), "rack-fan")
        self.assertEqual(status, "outside-boundary")
        self.assertIsNone(hops)
        self.assertEqual(path, ())

    def test_unqualified_stage_is_reported_and_not_credited(self):
        status, _, _, flags = boundary_status(topology(), "monitor")
        self.assertEqual(status, "indirect")
        self.assertEqual(flags["unqualified_isolation"], ("series-r",))

    def test_verified_protection_is_flagged(self):
        _, _, _, flags = boundary_status(topology(), "heater")
        self.assertTrue(flags["verified_protection"])
        self.assertFalse(flags["unverified_protection"])

    def test_unverified_protection_is_flagged_separately(self):
        _, _, _, flags = boundary_status(topology(), "pump")
        self.assertTrue(flags["unverified_protection"])
        self.assertFalse(flags["verified_protection"])


class ObligationTests(unittest.TestCase):
    def test_direct_sourcing_part_owes_the_full_set(self):
        self.assertEqual(
            inherited_obligations("direct", True), DIRECT_SOURCING_OBLIGATIONS
        )

    def test_indirect_sourcing_part_owes_one_rung_less(self):
        self.assertEqual(
            inherited_obligations("indirect", True), INDIRECT_SOURCING_OBLIGATIONS
        )

    def test_observing_part_still_owes_identity_and_lot(self):
        self.assertEqual(inherited_obligations("direct", False), OBSERVING_OBLIGATIONS)

    def test_verified_protection_credits_exactly_one_rung(self):
        self.assertEqual(
            inherited_obligations("direct", True, verified_protection=True),
            INDIRECT_SOURCING_OBLIGATIONS,
        )

    def test_credit_never_drops_below_the_identity_floor(self):
        self.assertEqual(
            inherited_obligations("indirect", True, verified_protection=True),
            IDENTITY_FLOOR_OBLIGATIONS,
        )
        self.assertEqual(
            inherited_obligations("direct", False, verified_protection=True),
            IDENTITY_FLOOR_OBLIGATIONS,
        )

    def test_out_of_scope_part_raises_no_obligations(self):
        self.assertEqual(inherited_obligations("isolated", True), ())
        self.assertIsNone(obligation_tier("outside-boundary", True))

    def test_non_boolean_drive_capability_rejected(self):
        with self.assertRaises(ValueError):
            obligation_tier("direct", "yes")


class EvaluatePartTests(unittest.TestCase):
    def test_incomplete_record_is_not_a_scope_decision(self):
        record = evaluate_gse_part(part(part_number=None), topology())
        self.assertEqual(record["status"], "record-incomplete")
        self.assertEqual(record["findings"], ("record-incomplete",))
        self.assertFalse(record["in_scope"])

    def test_completeness_counts_the_mandatory_attributes(self):
        record = evaluate_gse_part(part(part_number="  "), topology())
        expected = (len(MANDATORY_PART_ATTRIBUTES) - 1) / len(MANDATORY_PART_ATTRIBUTES)
        self.assertAlmostEqual(record["completeness"], expected, places=9)

    def test_fully_evidenced_connector_part_has_no_finding(self):
        record = evaluate_gse_part(part(), topology())
        self.assertEqual(record["findings"], ())
        self.assertEqual(record["open_items"], ())
        self.assertTrue(record["in_scope"])

    def test_evidence_matching_ignores_case_and_padding(self):
        record = evaluate_gse_part(
            part(evidence_held=["  PART-Approval ", "LOT-TRACEABILITY", "Derating-Evidence", "handling-and-storage-record"]),
            topology(),
        )
        self.assertEqual(record["open_items"], ())

    def test_missing_evidence_becomes_an_open_item(self):
        record = evaluate_gse_part(part(evidence_held=["part-approval"]), topology())
        self.assertIn("derating-evidence", record["open_items"])
        self.assertIn("open-obligations", record["findings"])

    def test_isolated_part_raises_nothing_and_is_not_a_finding(self):
        record = evaluate_gse_part(
            part(part_id="G009", node_id="logger", evidence_held=[]), topology()
        )
        self.assertEqual(record["status"], "isolated")
        self.assertEqual(record["obligations"], ())
        self.assertEqual(record["findings"], ())

    def test_unqualified_stage_keeps_the_part_in_scope_and_is_its_own_finding(self):
        record = evaluate_gse_part(
            part(
                part_id="G010",
                node_id="monitor",
                evidence_held=list(INDIRECT_SOURCING_OBLIGATIONS),
            ),
            topology(),
        )
        self.assertTrue(record["in_scope"])
        self.assertEqual(record["open_items"], ())
        self.assertEqual(record["findings"], ("unqualified-isolation-stage",))

    def test_unverified_protection_earns_no_credit(self):
        record = evaluate_gse_part(
            part(part_id="G011", node_id="pump", evidence_held=[]), topology()
        )
        self.assertEqual(record["obligations"], INDIRECT_SOURCING_OBLIGATIONS)
        self.assertEqual(record["protection"], "unverified")
        self.assertIn("unverified-protective-element", record["findings"])

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_gse_part(["G001"], topology())

    def test_string_evidence_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_gse_part(part(evidence_held="part-approval"), topology())


class ClosureTests(unittest.TestCase):
    def test_out_of_scope_parts_neither_help_nor_hurt(self):
        records = [
            evaluate_gse_part(part(evidence_held=["part-approval"]), topology()),
            evaluate_gse_part(
                part(part_id="G002", node_id="rack-fan", evidence_held=[]), topology()
            ),
        ]
        closure, raised, open_count = obligation_closure(records)
        self.assertEqual(raised, len(DIRECT_SOURCING_OBLIGATIONS))
        self.assertEqual(open_count, 3)
        self.assertAlmostEqual(closure, 0.25, places=9)

    def test_bench_with_nothing_in_scope_is_fully_closed(self):
        records = [
            evaluate_gse_part(
                part(part_id="G003", node_id="rack-fan", evidence_held=[]), topology()
            )
        ]
        self.assertAlmostEqual(obligation_closure(records)[0], 1.0, places=9)

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            obligation_closure("records")


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {"topology": topology(), "parts": [part()]}
        base.update(overrides)
        return base

    def test_clean_bench_is_accepted(self):
        result = assess_gse_parts_control(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["in_scope_parts"], ("G001",))

    def test_closure_landing_exactly_on_the_requirement_is_not_a_shortfall(self):
        spec = self._spec(
            parts=[part(evidence_held=list(DIRECT_SOURCING_OBLIGATIONS[:3]))],
            required_closure=0.75,
        )
        result = assess_gse_parts_control(spec)
        self.assertAlmostEqual(result["closure_fraction"], 0.75, places=9)
        self.assertAlmostEqual(
            result["closure_fraction"], result["required_closure"], places=9
        )
        self.assertTrue(result["meets_required_closure"])

    def test_open_item_holds_the_bench_even_at_the_required_closure(self):
        spec = self._spec(
            parts=[part(evidence_held=list(DIRECT_SOURCING_OBLIGATIONS[:3]))],
            required_closure=0.75,
        )
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["verdict"], "hold")

    def test_findings_are_ranked_worst_first(self):
        spec = self._spec(
            parts=[
                part(part_id="G020", node_id="pump", evidence_held=[]),
                part(part_id="G021", part_number=None),
            ]
        )
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["findings"][0]["finding"], "record-incomplete")
        self.assertEqual(result["findings"][0]["part_id"], "G021")

    def test_governing_part_carries_the_most_open_items(self):
        spec = self._spec(
            parts=[
                part(part_id="G030", evidence_held=["part-approval"]),
                part(part_id="G031", node_id="psu", evidence_held=list(INDIRECT_SOURCING_OBLIGATIONS[:2])),
            ]
        )
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["governing_part"], "G030")

    def test_duplicate_part_on_the_bench_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(self._spec(parts=[part(), part()]))

    def test_empty_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(self._spec(parts=[]))

    def test_missing_topology_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control({"parts": [part()]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(["topology"])

    def test_out_of_range_required_closure_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(self._spec(required_closure=1.5))

    def test_boolean_required_closure_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(self._spec(required_closure=True))

    def test_tolerance_is_declared_and_small(self):
        self.assertGreater(CLOSURE_TOLERANCE, 0.0)
        self.assertLess(CLOSURE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()

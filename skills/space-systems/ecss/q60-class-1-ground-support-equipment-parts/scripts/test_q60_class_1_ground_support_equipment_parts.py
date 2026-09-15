"""Contract tests for the clause 4.1.5 ground support equipment parts logic."""

import unittest

from q60_class_1_ground_support_equipment_parts_logic import (
    CLOSURE_TOLERANCE,
    MANDATORY_PART_ATTRIBUTES,
    MAX_PATH_NODES,
    OBSERVING_OBLIGATIONS,
    SOURCING_OBLIGATIONS,
    assess_gse_parts_control,
    connection_path,
    evaluate_part,
    inherited_obligations,
    obligation_closure,
    qualified_isolation_on_path,
    unqualified_isolation_on_path,
    validate_node_id,
    validate_topology,
)

FULL_EVIDENCE = list(SOURCING_OBLIGATIONS)


def chain(qualified=None):
    """Return a bench topology: driver -> optional isolation -> umbilical -> flight."""
    nodes = [
        {"node_id": "UMBILICAL", "kind": "bench-node", "downstream": "FLIGHT-CONN"},
        {"node_id": "FLIGHT-CONN", "kind": "flight-interface", "downstream": None},
    ]
    if qualified is None:
        nodes.insert(0, {"node_id": "DRIVER", "kind": "bench-node", "downstream": "UMBILICAL"})
    else:
        nodes.insert(0, {"node_id": "ISO", "kind": "isolation-stage",
                         "downstream": "UMBILICAL", "qualified": qualified})
        nodes.insert(0, {"node_id": "DRIVER", "kind": "bench-node", "downstream": "ISO"})
    nodes.append({"node_id": "FAN-RAIL", "kind": "bench-node", "downstream": None})
    return nodes


def part(**overrides):
    """Return one connected sourcing part with full evidence."""
    base = {
        "part_id": "P001",
        "part_number": "LM317",
        "node_id": "DRIVER",
        "can_drive_flight_side": True,
        "evidence": list(FULL_EVIDENCE),
    }
    base.update(overrides)
    return base


class ValidateNodeIdTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_node_id("  DRIVER "), "DRIVER")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_id("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_id(7)


class ValidateTopologyTests(unittest.TestCase):
    def test_valid_topology_indexes_every_node(self):
        topology = validate_topology(chain())
        self.assertEqual(len(topology), 4)

    def test_dangling_downstream_reference_rejected(self):
        nodes = chain()
        nodes[0]["downstream"] = "NOWHERE"
        with self.assertRaises(ValueError):
            validate_topology(nodes)

    def test_repeated_node_identifier_rejected(self):
        nodes = chain()
        nodes.append(dict(nodes[0]))
        with self.assertRaises(ValueError):
            validate_topology(nodes)

    def test_unknown_node_kind_rejected(self):
        nodes = chain()
        nodes[0]["kind"] = "mystery-box"
        with self.assertRaises(ValueError):
            validate_topology(nodes)

    def test_flight_interface_may_not_feed_onward(self):
        nodes = chain()
        nodes[2]["downstream"] = "FAN-RAIL"
        with self.assertRaises(ValueError):
            validate_topology(nodes)

    def test_isolation_stage_without_a_qualification_flag_rejected(self):
        nodes = chain(qualified=True)
        del nodes[1]["qualified"]
        with self.assertRaises(ValueError):
            validate_topology(nodes)

    def test_topology_without_a_flight_interface_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology([{"node_id": "A", "kind": "bench-node", "downstream": None}])

    def test_empty_topology_rejected(self):
        with self.assertRaises(ValueError):
            validate_topology([])


class ConnectionPathTests(unittest.TestCase):
    def test_path_runs_from_the_part_node_to_the_flight_interface(self):
        topology = validate_topology(chain())
        self.assertEqual(
            connection_path("DRIVER", topology), ("DRIVER", "UMBILICAL", "FLIGHT-CONN")
        )

    def test_path_terminating_off_the_flight_side_is_still_returned(self):
        topology = validate_topology(chain())
        self.assertEqual(connection_path("FAN-RAIL", topology), ("FAN-RAIL",))

    def test_loop_in_the_topology_is_refused(self):
        nodes = [
            {"node_id": "A", "kind": "bench-node", "downstream": "B"},
            {"node_id": "B", "kind": "bench-node", "downstream": "A"},
            {"node_id": "FLIGHT-CONN", "kind": "flight-interface", "downstream": None},
        ]
        topology = validate_topology(nodes)
        with self.assertRaises(ValueError):
            connection_path("A", topology)

    def test_node_outside_the_topology_rejected(self):
        topology = validate_topology(chain())
        with self.assertRaises(ValueError):
            connection_path("GHOST", topology)

    def test_path_bound_is_a_topology_guard_not_a_bench_limit(self):
        self.assertGreater(MAX_PATH_NODES, 8)


class IsolationCreditTests(unittest.TestCase):
    def test_qualified_stage_is_credited(self):
        topology = validate_topology(chain(qualified=True))
        path = connection_path("DRIVER", topology)
        self.assertEqual(qualified_isolation_on_path(path, topology), "ISO")

    def test_unqualified_stage_earns_no_credit(self):
        topology = validate_topology(chain(qualified=False))
        path = connection_path("DRIVER", topology)
        self.assertIsNone(qualified_isolation_on_path(path, topology))

    def test_unqualified_stage_is_still_reported(self):
        topology = validate_topology(chain(qualified=False))
        path = connection_path("DRIVER", topology)
        self.assertEqual(unqualified_isolation_on_path(path, topology), ("ISO",))

    def test_empty_path_rejected(self):
        topology = validate_topology(chain())
        with self.assertRaises(ValueError):
            qualified_isolation_on_path((), topology)


class InheritedObligationsTests(unittest.TestCase):
    def test_a_sourcing_part_owes_the_full_set(self):
        self.assertEqual(inherited_obligations(True), SOURCING_OBLIGATIONS)

    def test_an_observing_part_owes_a_reduced_set(self):
        self.assertEqual(inherited_obligations(False), OBSERVING_OBLIGATIONS)

    def test_the_reduced_set_is_a_subset_of_the_full_one(self):
        self.assertTrue(set(OBSERVING_OBLIGATIONS) < set(SOURCING_OBLIGATIONS))

    def test_non_boolean_drive_flag_rejected(self):
        with self.assertRaises(ValueError):
            inherited_obligations("yes")


class EvaluatePartTests(unittest.TestCase):
    def test_connected_part_with_full_evidence_is_closed(self):
        record = evaluate_part(part(), validate_topology(chain()))
        self.assertEqual(record["disposition"], "in-scope-closed")
        self.assertTrue(record["directly_connected"])
        self.assertEqual(record["hops_to_flight_interface"], 2)

    def test_incomplete_record_is_not_a_scope_decision(self):
        incomplete = part()
        del incomplete["node_id"]
        record = evaluate_part(incomplete, validate_topology(chain()))
        self.assertEqual(record["disposition"], "record-incomplete")
        self.assertFalse(record["in_scope"])
        expected = (len(MANDATORY_PART_ATTRIBUTES) - 1) / len(MANDATORY_PART_ATTRIBUTES)
        self.assertAlmostEqual(record["completeness"], expected, places=9)

    def test_part_on_an_undeclared_node_is_named(self):
        record = evaluate_part(part(node_id="GHOST"), validate_topology(chain()))
        self.assertEqual(record["disposition"], "unknown-node")

    def test_qualified_isolation_takes_the_part_out_of_scope(self):
        record = evaluate_part(part(), validate_topology(chain(qualified=True)))
        self.assertEqual(record["disposition"], "out-of-scope")
        self.assertFalse(record["in_scope"])

    def test_unqualified_isolation_leaves_the_part_in_scope(self):
        record = evaluate_part(part(), validate_topology(chain(qualified=False)))
        self.assertTrue(record["in_scope"])
        self.assertEqual(record["unqualified_isolation"], ("ISO",))

    def test_rack_internal_part_never_reaches_the_flight_side(self):
        record = evaluate_part(part(node_id="FAN-RAIL"), validate_topology(chain()))
        self.assertEqual(record["disposition"], "out-of-scope")

    def test_missing_evidence_is_named_item_by_item(self):
        record = evaluate_part(
            part(evidence=["part-approval"]), validate_topology(chain())
        )
        self.assertEqual(record["disposition"], "obligations-open")
        self.assertEqual(
            record["missing_obligations"],
            tuple(n for n in SOURCING_OBLIGATIONS if n != "part-approval"),
        )

    def test_evidence_matching_ignores_case_and_padding(self):
        record = evaluate_part(
            part(evidence=[" Part-Approval ", "LOT-TRACEABILITY", "derating-evidence",
                           "handling-and-storage-record"]),
            validate_topology(chain()),
        )
        self.assertEqual(record["missing_obligations"], ())

    def test_observing_part_is_not_asked_for_derating_evidence(self):
        record = evaluate_part(
            part(can_drive_flight_side=False, evidence=list(OBSERVING_OBLIGATIONS)),
            validate_topology(chain()),
        )
        self.assertEqual(record["disposition"], "in-scope-closed")

    def test_non_sequence_evidence_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_part(part(evidence="part-approval"), validate_topology(chain()))

    def test_empty_topology_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_part(part(), {})


class ObligationClosureTests(unittest.TestCase):
    def test_all_evidence_held_closes_fully(self):
        topology = validate_topology(chain())
        records = [evaluate_part(part(), topology)]
        self.assertAlmostEqual(obligation_closure(records), 1.0, places=9)

    def test_partial_evidence_gives_the_counted_fraction(self):
        topology = validate_topology(chain())
        records = [evaluate_part(part(evidence=["part-approval", "lot-traceability"]), topology)]
        self.assertAlmostEqual(obligation_closure(records), 2 / 4, places=9)

    def test_out_of_scope_parts_do_not_dilute_the_fraction(self):
        topology = validate_topology(chain())
        records = [
            evaluate_part(part(evidence=["part-approval", "lot-traceability"]), topology),
            evaluate_part(part(part_id="P002", node_id="FAN-RAIL"), topology),
        ]
        self.assertAlmostEqual(obligation_closure(records), 2 / 4, places=9)

    def test_a_bench_with_nothing_in_scope_is_closed_by_definition(self):
        topology = validate_topology(chain())
        records = [evaluate_part(part(node_id="FAN-RAIL"), topology)]
        self.assertAlmostEqual(obligation_closure(records), 1.0, places=9)

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            obligation_closure("records")


class AssessGsePartsControlTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "nodes": chain(),
            "parts": [part()],
            "required_closure": 1.0,
        }
        base.update(overrides)
        return base

    def test_clean_bench_is_accepted(self):
        result = assess_gse_parts_control(self._spec())
        self.assertEqual(result["verdict"], "accept")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["parts_in_scope"], ("P001",))

    def test_open_obligation_holds_the_bench(self):
        spec = self._spec(parts=[part(evidence=["part-approval"])])
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["verdict"], "hold")
        self.assertEqual(result["governing_part"], "P001")

    def test_unqualified_isolation_raises_its_own_finding(self):
        spec = self._spec(nodes=chain(qualified=False))
        result = assess_gse_parts_control(spec)
        dispositions = [entry["disposition"] for entry in result["findings"]]
        self.assertIn("isolation-not-qualified", dispositions)

    def test_qualified_isolation_leaves_a_clean_bench(self):
        spec = self._spec(nodes=chain(qualified=True), parts=[part(evidence=[])])
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["parts_in_scope"], ())
        self.assertEqual(result["verdict"], "accept")

    def test_findings_are_ranked_with_the_worst_first(self):
        incomplete = part(part_id="P000")
        del incomplete["part_number"]
        spec = self._spec(parts=[part(evidence=["part-approval"]), incomplete])
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["findings"][0]["disposition"], "record-incomplete")

    def test_governing_part_is_the_one_with_most_open_obligations(self):
        spec = self._spec(
            parts=[
                part(part_id="P001", evidence=list(SOURCING_OBLIGATIONS[:3])),
                part(part_id="P002", evidence=["part-approval"]),
            ]
        )
        result = assess_gse_parts_control(spec)
        self.assertEqual(result["governing_part"], "P002")

    def test_requirement_met_exactly_is_not_a_shortfall(self):
        result = assess_gse_parts_control(self._spec())
        self.assertAlmostEqual(
            result["obligation_closure"], result["required_closure"], places=9
        )
        self.assertEqual(result["verdict"], "accept")

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(CLOSURE_TOLERANCE, 1e-6)

    def test_missing_parts_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control({"nodes": chain()})

    def test_empty_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(self._spec(parts=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(["nodes"])

    def test_out_of_range_required_closure_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_parts_control(self._spec(required_closure=-0.2))


if __name__ == "__main__":
    unittest.main()

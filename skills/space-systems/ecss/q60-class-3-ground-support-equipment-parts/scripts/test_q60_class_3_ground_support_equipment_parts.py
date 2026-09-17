"""Contract tests for the clause 6.1.5 Class 3 ground support equipment scope logic."""

import unittest

from q60_class_3_ground_support_equipment_parts_logic import (
    CLOSURE_TOLERANCE,
    FLIGHT_INTERFACE,
    INHERITED_OBLIGATIONS,
    QUALIFICATION_STATES,
    assess_class_3_gse_part_scope,
    build_topology,
    connection_path,
    control_boundary,
    normalise_qualification_state,
    obligation_closure,
    part_obligation_gaps,
    stage_breaks_chain,
    validate_node_id,
)

ALL_CLOSED = list(INHERITED_OBLIGATIONS)


def part(part_id, connects_to, closed=ALL_CLOSED):
    """Return one ground support equipment part mapping."""
    entry = {"part_id": part_id, "connects_to": connects_to}
    if closed is not None:
        entry["obligations_closed"] = list(closed)
    return entry


def stage(stage_id, connects_to, state="qualified"):
    """Return one isolation stage mapping."""
    return {
        "stage_id": stage_id,
        "connects_to": connects_to,
        "qualification_state": state,
    }


class NodeIdTests(unittest.TestCase):
    def test_surrounding_space_is_stripped(self):
        self.assertEqual(validate_node_id("  DRV-1 "), "DRV-1")

    def test_blank_node_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_id("  ")

    def test_non_string_node_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_id(None)


class QualificationStateTests(unittest.TestCase):
    def test_state_lookup_ignores_case(self):
        self.assertEqual(normalise_qualification_state("QUALIFIED"), "qualified")

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            normalise_qualification_state("probably-fine")

    def test_only_a_qualified_stage_breaks_the_chain(self):
        self.assertTrue(stage_breaks_chain("qualified"))

    def test_unqualified_stage_does_not_break_the_chain(self):
        self.assertFalse(stage_breaks_chain("unqualified"))

    def test_unassessed_stage_does_not_break_the_chain(self):
        self.assertFalse(stage_breaks_chain("not-assessed"))

    def test_every_known_state_answers_a_boolean(self):
        for state in QUALIFICATION_STATES:
            self.assertIsInstance(stage_breaks_chain(state), bool)


class TopologyTests(unittest.TestCase):
    def test_parts_and_stages_are_indexed(self):
        parts, stages = build_topology(
            [part("P1", FLIGHT_INTERFACE)], [stage("S1", FLIGHT_INTERFACE)]
        )
        self.assertEqual(sorted(parts), ["P1"])
        self.assertEqual(sorted(stages), ["S1"])

    def test_repeated_part_rejected(self):
        with self.assertRaises(ValueError):
            build_topology(
                [part("P1", FLIGHT_INTERFACE), part("P1", FLIGHT_INTERFACE)], []
            )

    def test_repeated_stage_rejected(self):
        with self.assertRaises(ValueError):
            build_topology(
                [part("P1", "S1")],
                [stage("S1", FLIGHT_INTERFACE), stage("S1", FLIGHT_INTERFACE)],
            )

    def test_node_used_as_both_part_and_stage_rejected(self):
        with self.assertRaises(ValueError):
            build_topology([part("X1", FLIGHT_INTERFACE)], [stage("X1", FLIGHT_INTERFACE)])

    def test_empty_part_set_rejected(self):
        with self.assertRaises(ValueError):
            build_topology([], [])

    def test_non_sequence_stages_rejected(self):
        with self.assertRaises(ValueError):
            build_topology([part("P1", FLIGHT_INTERFACE)], "S1")

    def test_part_without_a_connection_rejected(self):
        with self.assertRaises(ValueError):
            build_topology([{"part_id": "P1"}], [])


class ConnectionPathTests(unittest.TestCase):
    def test_direct_part_reaches_the_interface(self):
        parts, stages = build_topology([part("P1", FLIGHT_INTERFACE)], [])
        walk = connection_path("P1", parts, stages)
        self.assertEqual(walk["outcome"], "reaches-flight-interface")
        self.assertEqual(walk["hops"], 1)

    def test_chained_parts_count_their_hops(self):
        parts, stages = build_topology(
            [part("P1", "P2"), part("P2", FLIGHT_INTERFACE)], []
        )
        walk = connection_path("P1", parts, stages)
        self.assertEqual(walk["hops"], 2)

    def test_qualified_stage_breaks_the_chain(self):
        parts, stages = build_topology(
            [part("P1", "S1")], [stage("S1", FLIGHT_INTERFACE)]
        )
        walk = connection_path("P1", parts, stages)
        self.assertEqual(walk["outcome"], "isolated")
        self.assertEqual(walk["broken_by"], "S1")

    def test_unqualified_stage_is_walked_through(self):
        parts, stages = build_topology(
            [part("P1", "S1")], [stage("S1", FLIGHT_INTERFACE, "unqualified")]
        )
        walk = connection_path("P1", parts, stages)
        self.assertEqual(walk["outcome"], "reaches-flight-interface")

    def test_unassessed_stage_is_walked_through(self):
        parts, stages = build_topology(
            [part("P1", "S1")], [stage("S1", FLIGHT_INTERFACE, "not-assessed")]
        )
        walk = connection_path("P1", parts, stages)
        self.assertEqual(walk["outcome"], "reaches-flight-interface")

    def test_looping_topology_rejected(self):
        parts, stages = build_topology([part("P1", "P2"), part("P2", "P1")], [])
        with self.assertRaises(ValueError):
            connection_path("P1", parts, stages)

    def test_chain_ending_nowhere_is_dangling(self):
        parts, stages = build_topology([part("P1", "GHOST")], [])
        walk = connection_path("P1", parts, stages)
        self.assertEqual(walk["outcome"], "dangling")

    def test_unknown_start_part_rejected(self):
        parts, stages = build_topology([part("P1", FLIGHT_INTERFACE)], [])
        with self.assertRaises(ValueError):
            connection_path("P9", parts, stages)

    def test_alternate_interface_name_is_honoured(self):
        parts, stages = build_topology([part("P1", "umbilical-face")], [])
        walk = connection_path("P1", parts, stages, flight_interface="umbilical-face")
        self.assertEqual(walk["outcome"], "reaches-flight-interface")


class BoundaryTests(unittest.TestCase):
    def test_boundary_separates_isolated_from_connected(self):
        parts, stages = build_topology(
            [part("P1", FLIGHT_INTERFACE), part("P2", "S1")],
            [stage("S1", FLIGHT_INTERFACE)],
        )
        records = control_boundary(parts, stages)
        inside = [r["part_id"] for r in records if r["in_control_boundary"]]
        self.assertEqual(inside, ["P1"])

    def test_unassessed_stage_on_the_path_is_recorded(self):
        parts, stages = build_topology(
            [part("P1", "S1")], [stage("S1", FLIGHT_INTERFACE, "not-assessed")]
        )
        records = control_boundary(parts, stages)
        self.assertEqual(records[0]["unassessed_stages_on_path"], ("S1",))

    def test_records_are_ordered_by_part_identifier(self):
        parts, stages = build_topology(
            [part("P9", FLIGHT_INTERFACE), part("P1", FLIGHT_INTERFACE)], []
        )
        records = control_boundary(parts, stages)
        self.assertEqual([r["part_id"] for r in records], ["P1", "P9"])

    def test_empty_part_index_rejected(self):
        with self.assertRaises(ValueError):
            control_boundary({}, {})


class ObligationTests(unittest.TestCase):
    def test_full_record_leaves_nothing_open(self):
        closed, open_names = part_obligation_gaps(
            {"part_id": "P1", "obligations_closed": ALL_CLOSED}
        )
        self.assertEqual(open_names, ())
        self.assertEqual(len(closed), len(INHERITED_OBLIGATIONS))

    def test_absent_record_opens_every_obligation(self):
        closed, open_names = part_obligation_gaps({"part_id": "P1", "obligations_closed": None})
        self.assertEqual(closed, ())
        self.assertEqual(open_names, INHERITED_OBLIGATIONS)

    def test_partial_record_names_what_is_left(self):
        _closed, open_names = part_obligation_gaps(
            {"part_id": "P1", "obligations_closed": [INHERITED_OBLIGATIONS[0]]}
        )
        self.assertEqual(len(open_names), len(INHERITED_OBLIGATIONS) - 1)

    def test_unknown_obligation_rejected(self):
        with self.assertRaises(ValueError):
            part_obligation_gaps({"part_id": "P1", "obligations_closed": ["vibe-check"]})

    def test_non_mapping_part_rejected(self):
        with self.assertRaises(ValueError):
            part_obligation_gaps(["P1"])

    def test_closure_counts_only_in_boundary_parts(self):
        parts, stages = build_topology(
            [part("P1", FLIGHT_INTERFACE), part("P2", "S1", closed=[])],
            [stage("S1", FLIGHT_INTERFACE)],
        )
        records = control_boundary(parts, stages)
        self.assertAlmostEqual(obligation_closure(records, parts), 1.0, places=9)

    def test_closure_is_a_ratio_over_the_whole_boundary(self):
        parts, stages = build_topology(
            [
                part("P1", FLIGHT_INTERFACE),
                part("P2", FLIGHT_INTERFACE, closed=[]),
            ],
            [],
        )
        records = control_boundary(parts, stages)
        self.assertAlmostEqual(obligation_closure(records, parts), 0.5, places=9)

    def test_closure_without_a_boundary_rejected(self):
        parts, stages = build_topology([part("P1", "S1")], [stage("S1", FLIGHT_INTERFACE)])
        records = control_boundary(parts, stages)
        with self.assertRaises(ValueError):
            obligation_closure(records, parts)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        base = {
            "parts": [part("P1", FLIGHT_INTERFACE), part("P2", "P1")],
            "stages": [],
        }
        base.update(overrides)
        return base

    def test_clean_bench_confirms_the_scope(self):
        result = assess_class_3_gse_part_scope(self._spec())
        self.assertTrue(result["scope_confirmed"])
        self.assertEqual(result["verdict"], "control-scope-confirmed")

    def test_governing_part_is_the_one_closest_to_the_hardware(self):
        result = assess_class_3_gse_part_scope(self._spec())
        self.assertEqual(result["governing_part"], "P1")

    def test_part_behind_a_qualified_stage_is_out_of_the_boundary(self):
        spec = self._spec(
            parts=[part("P1", FLIGHT_INTERFACE), part("P2", "S1", closed=[])],
            stages=[stage("S1", FLIGHT_INTERFACE)],
        )
        result = assess_class_3_gse_part_scope(spec)
        self.assertEqual(result["control_boundary"], ("P1",))

    def test_part_behind_an_unqualified_stage_stays_inside(self):
        spec = self._spec(
            parts=[part("P1", FLIGHT_INTERFACE), part("P2", "S1")],
            stages=[stage("S1", FLIGHT_INTERFACE, "unqualified")],
        )
        result = assess_class_3_gse_part_scope(spec)
        self.assertEqual(sorted(result["control_boundary"]), ["P1", "P2"])

    def test_unassessed_stage_raises_its_own_finding(self):
        spec = self._spec(
            parts=[part("P1", "S1")],
            stages=[stage("S1", FLIGHT_INTERFACE, "not-assessed")],
        )
        result = assess_class_3_gse_part_scope(spec)
        dispositions = {f["disposition"] for f in result["findings"]}
        self.assertIn("isolation-stage-not-assessed", dispositions)

    def test_connected_part_without_a_record_is_a_finding(self):
        spec = self._spec(
            parts=[part("P1", FLIGHT_INTERFACE), part("P2", "P1", closed=None)]
        )
        result = assess_class_3_gse_part_scope(spec)
        dispositions = {f["disposition"] for f in result["findings"]}
        self.assertIn("no-obligation-record", dispositions)

    def test_open_obligations_are_named(self):
        spec = self._spec(
            parts=[
                part("P1", FLIGHT_INTERFACE),
                part("P2", "P1", closed=[INHERITED_OBLIGATIONS[0]]),
            ]
        )
        result = assess_class_3_gse_part_scope(spec)
        detail = [f for f in result["findings"] if f["disposition"] == "obligations-open"]
        self.assertTrue(detail and INHERITED_OBLIGATIONS[1] in detail[0]["detail"])

    def test_dangling_chain_is_reported(self):
        spec = self._spec(parts=[part("P1", FLIGHT_INTERFACE), part("P2", "GHOST")])
        result = assess_class_3_gse_part_scope(spec)
        dispositions = {f["disposition"] for f in result["findings"]}
        self.assertIn("dangling-connection", dispositions)

    def test_findings_are_ranked_worst_first(self):
        spec = self._spec(
            parts=[
                part("P1", FLIGHT_INTERFACE, closed=[]),
                part("P2", "GHOST"),
            ]
        )
        result = assess_class_3_gse_part_scope(spec)
        severities = [f["severity"] for f in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_bench_reaching_nothing_is_rejected(self):
        spec = self._spec(
            parts=[part("P1", "S1")], stages=[stage("S1", FLIGHT_INTERFACE)]
        )
        with self.assertRaises(ValueError):
            assess_class_3_gse_part_scope(spec)

    def test_looping_bench_is_rejected(self):
        spec = self._spec(parts=[part("P1", "P2"), part("P2", "P1")])
        with self.assertRaises(ValueError):
            assess_class_3_gse_part_scope(spec)

    def test_exactly_met_closure_sits_on_the_agreed_level(self):
        spec = self._spec(
            parts=[
                part("P1", FLIGHT_INTERFACE),
                part("P2", FLIGHT_INTERFACE, closed=[]),
            ],
            required_closure=0.5,
        )
        result = assess_class_3_gse_part_scope(spec)
        self.assertAlmostEqual(result["obligation_closure"], 0.5, places=9)
        self.assertAlmostEqual(result["required_closure"], 0.5, places=9)

    def test_tolerance_is_representation_sized_only(self):
        self.assertLess(CLOSURE_TOLERANCE, 1e-6)

    def test_missing_stages_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_gse_part_scope({"parts": [part("P1", FLIGHT_INTERFACE)]})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_gse_part_scope(["parts"])

    def test_out_of_range_required_closure_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_gse_part_scope(self._spec(required_closure=-0.2))

    def test_boolean_required_closure_rejected(self):
        with self.assertRaises(ValueError):
            assess_class_3_gse_part_scope(self._spec(required_closure=False))


if __name__ == "__main__":
    unittest.main()

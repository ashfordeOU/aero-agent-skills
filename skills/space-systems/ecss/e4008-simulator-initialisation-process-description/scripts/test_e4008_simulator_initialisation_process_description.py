#!/usr/bin/env python3
"""Contract test for the initialisation process description of 4.4.3 (offline)."""

import copy
import unittest

from e4008_simulator_initialisation_process_description_logic import (
    NORMATIVE_ITEMS,
    PHASE_KINDS,
    REQUIRED_PRECEDENCES,
    TERMINAL_KIND,
    check_precedence,
    duplicate_phase_ids,
    evaluate_initialisation_description,
    is_legal_identifier,
    kind_positions,
    normalize_phases,
    order_violations,
    topological_order,
    unknown_dependencies,
    validate_phase,
)


def _phase(identifier, kind, depends_on=(), **extra):
    phase = {
        "id": identifier,
        "kind": kind,
        "entry_condition": "the previous phase reported complete",
        "exit_condition": "every %s activity reported done" % kind,
        "depends_on": list(depends_on),
    }
    phase.update(extra)
    return phase


DESCRIPTION = {
    "ordered": True,
    "phases": [
        _phase("create", "instance-creation"),
        _phase("link", "link-resolution", ["create"]),
        _phase("configure", "field-configuration", ["link"]),
        _phase("register", "entry-point-registration", ["configure"]),
        _phase("initialise", "instance-initialisation", ["register"]),
        _phase("arm", "schedule-arming", ["initialise"]),
        _phase(
            "standby",
            "standby-declaration",
            ["arm"],
            standby_state="standby, waiting for the first run command",
        ),
    ],
}


def _description(**overrides):
    description = copy.deepcopy(DESCRIPTION)
    description.update(overrides)
    return description


def _without(kind):
    description = copy.deepcopy(DESCRIPTION)
    description["phases"] = [p for p in description["phases"] if p["kind"] != kind]
    return description


def _item(result, identifier):
    for entry in result["items"]:
        if entry["item"] == identifier:
            return entry
    raise AssertionError("item %s not graded" % identifier)


class PhaseValidationTests(unittest.TestCase):
    def test_a_well_formed_phase_normalizes(self):
        phase = validate_phase(DESCRIPTION["phases"][0])
        self.assertEqual(phase["id"], "create")
        self.assertEqual(phase["kind"], "instance-creation")

    def test_every_declared_kind_is_accepted(self):
        for kind in PHASE_KINDS:
            self.assertEqual(validate_phase(_phase("p", kind))["kind"], kind)

    def test_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase("p", "warm-up"))

    def test_an_illegal_phase_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase("1st", "instance-creation"))

    def test_a_self_dependency_rejected(self):
        with self.assertRaises(ValueError):
            validate_phase(_phase("create", "instance-creation", ["create"]))

    def test_a_non_sequence_dependency_list_rejected(self):
        broken = _phase("create", "instance-creation")
        broken["depends_on"] = "link"
        with self.assertRaises(ValueError):
            validate_phase(broken)

    def test_a_hyphenated_identifier_is_legal(self):
        self.assertTrue(is_legal_identifier("create-instances"))

    def test_an_empty_identifier_is_not_legal(self):
        self.assertFalse(is_legal_identifier(""))

    def test_an_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phases([])


class DependencyTests(unittest.TestCase):
    def test_a_clean_description_has_no_duplicate_ids(self):
        self.assertEqual(duplicate_phase_ids(normalize_phases(DESCRIPTION["phases"])), [])

    def test_a_repeated_id_is_reported(self):
        phases = DESCRIPTION["phases"] + [_phase("create", "supporting-activity")]
        self.assertEqual(duplicate_phase_ids(normalize_phases(phases)), ["create"])

    def test_a_dependency_on_an_absent_phase_is_reported(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[1]["depends_on"] = ["bootstrap"]
        self.assertEqual(
            unknown_dependencies(normalize_phases(phases)), ["link -> bootstrap"]
        )

    def test_the_dependency_order_is_produced(self):
        topology = topological_order(normalize_phases(DESCRIPTION["phases"]))
        self.assertEqual(topology["cycle"], [])
        self.assertEqual(topology["order"][0], "create")
        self.assertEqual(topology["order"][-1], "standby")

    def test_a_dependency_cycle_blocks_the_order(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[0]["depends_on"] = ["standby"]
        topology = topological_order(normalize_phases(phases))
        self.assertIsNone(topology["order"])
        self.assertIn("create", topology["cycle"])

    def test_a_forward_dependency_is_an_order_violation(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[0]["depends_on"] = ["link"]
        violations = order_violations(normalize_phases(phases))
        self.assertEqual(len(violations), 1)
        self.assertIn("create", violations[0])

    def test_a_clean_description_has_no_order_violations(self):
        self.assertEqual(order_violations(normalize_phases(DESCRIPTION["phases"])), [])


class PrecedenceTests(unittest.TestCase):
    def test_kind_positions_record_first_and_last(self):
        positions = kind_positions(normalize_phases(DESCRIPTION["phases"]))
        self.assertEqual(positions["instance-creation"], {"first": 0, "last": 0})

    def test_a_repeated_kind_widens_its_span(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases.insert(3, _phase("create_late", "instance-creation"))
        positions = kind_positions(normalize_phases(phases))
        self.assertEqual(positions["instance-creation"]["last"], 3)

    def test_every_required_precedence_holds_in_the_clean_description(self):
        phases = normalize_phases(DESCRIPTION["phases"])
        for before, after in REQUIRED_PRECEDENCES:
            satisfied, finding = check_precedence(phases, before, after)
            self.assertTrue(satisfied, finding)

    def test_a_missing_earlier_kind_fails_the_precedence(self):
        phases = normalize_phases(_without("instance-creation")["phases"])
        satisfied, finding = check_precedence(
            phases, "instance-creation", "link-resolution"
        )
        self.assertFalse(satisfied)
        self.assertIn("no instance-creation phase", finding)

    def test_a_missing_later_kind_fails_the_precedence(self):
        phases = normalize_phases(_without("link-resolution")["phases"])
        satisfied, _finding = check_precedence(
            phases, "instance-creation", "link-resolution"
        )
        self.assertFalse(satisfied)

    def test_a_swapped_pair_fails_the_precedence(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[0], phases[1] = phases[1], phases[0]
        phases[0]["depends_on"] = []
        phases[1]["depends_on"] = []
        satisfied, _finding = check_precedence(
            normalize_phases(phases), "instance-creation", "link-resolution"
        )
        self.assertFalse(satisfied)


class DescriptionEvaluationTests(unittest.TestCase):
    def test_a_complete_description_satisfies_all_eleven_items(self):
        result = evaluate_initialisation_description(DESCRIPTION)
        self.assertEqual(result["satisfied"], 11)
        self.assertEqual(result["required"], len(NORMATIVE_ITEMS))
        self.assertEqual(result["verdict"], "description-complete")

    def test_every_normative_item_is_graded_exactly_once(self):
        result = evaluate_initialisation_description(DESCRIPTION)
        graded = [entry["item"] for entry in result["items"]]
        self.assertEqual(sorted(graded), sorted(NORMATIVE_ITEMS))

    def test_the_standby_state_is_reported(self):
        result = evaluate_initialisation_description(DESCRIPTION)
        self.assertIn("standby", result["standby_state"])

    def test_an_unordered_description_fails_the_sequence_item(self):
        result = evaluate_initialisation_description(_description(ordered=False))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])

    def test_a_single_phase_description_fails_the_sequence_item(self):
        result = evaluate_initialisation_description(
            _description(phases=[DESCRIPTION["phases"][-1]])
        )
        self.assertFalse(_item(result, NORMATIVE_ITEMS[0])["satisfied"])

    def test_a_repeated_identifier_fails_the_uniqueness_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases.insert(1, _phase("create", "supporting-activity"))
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[1])["satisfied"])

    def test_a_missing_entry_condition_fails_its_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[2]["entry_condition"] = "  "
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[2])["satisfied"])
        self.assertTrue(_item(result, NORMATIVE_ITEMS[3])["satisfied"])

    def test_a_missing_exit_condition_fails_its_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        del phases[4]["exit_condition"]
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[3])["satisfied"])

    def test_an_unknown_dependency_fails_its_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[3]["depends_on"] = ["bootstrap"]
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[4])["satisfied"])

    def test_a_dependency_cycle_fails_the_consistency_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[0]["depends_on"] = ["arm"]
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[5])["satisfied"])
        self.assertIsNone(result["dependency_order"])

    def test_creation_after_linking_fails_its_precedence_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases.insert(2, _phase("create_late", "instance-creation"))
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[6])["satisfied"])

    def test_configuration_before_linking_fails_its_precedence_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[1], phases[2] = phases[2], phases[1]
        phases[1]["depends_on"] = []
        phases[2]["depends_on"] = []
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[7])["satisfied"])

    def test_registration_before_configuration_fails_its_precedence_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[2], phases[3] = phases[3], phases[2]
        phases[2]["depends_on"] = []
        phases[3]["depends_on"] = []
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[8])["satisfied"])

    def test_arming_before_initialisation_fails_its_precedence_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases[4], phases[5] = phases[5], phases[4]
        phases[4]["depends_on"] = []
        phases[5]["depends_on"] = []
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[9])["satisfied"])

    def test_a_process_not_ending_in_standby_fails_the_terminal_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases.append(_phase("cleanup", "supporting-activity", ["standby"]))
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[10])["satisfied"])

    def test_a_terminal_phase_without_a_named_state_fails_the_terminal_item(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        del phases[-1]["standby_state"]
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertFalse(_item(result, NORMATIVE_ITEMS[10])["satisfied"])
        self.assertIsNone(result["standby_state"])

    def test_a_supporting_activity_does_not_disturb_the_precedences(self):
        phases = copy.deepcopy(DESCRIPTION["phases"])
        phases.insert(1, _phase("load_datasets", "supporting-activity", ["create"]))
        result = evaluate_initialisation_description(_description(phases=phases))
        self.assertTrue(result["complete"])

    def test_the_terminal_kind_constant_matches_the_declared_phase(self):
        self.assertEqual(DESCRIPTION["phases"][-1]["kind"], TERMINAL_KIND)

    def test_a_non_boolean_ordered_flag_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_initialisation_description(_description(ordered="yes"))

    def test_a_non_mapping_description_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_initialisation_description("create")

    def test_a_description_without_phases_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_initialisation_description({"ordered": True})


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract test for the solar cell assembly source control drawing (offline)."""

import copy
import unittest

from e2008_solar_cell_assembly_drawing_logic import (
    CITATION_GOVERNING,
    CITATION_ISSUE_STATES,
    CITATION_OFF_ISSUE,
    CITATION_VOID,
    INTERFACE_AMBIGUOUS,
    INTERFACE_CONTROLLED,
    INTERFACE_UNCONTROLLED,
    INTERFACE_UNDER_COVERED,
    MIN_BOND_COVERAGE,
    REQUIRED_LAYER_ROLES,
    SCA_DRAWING_NOT_RELEASABLE,
    SCA_DRAWING_OPEN_ITEMS,
    SCA_DRAWING_RELEASABLE,
    STACK_ORDER,
    TERMINAL_POLARITIES,
    assess_solar_cell_assembly_drawing,
    cited_drawing_standing,
    controlled_interface_share,
    grade_interface,
    layer_stack,
    terminal_identification,
)

LAYERS = [
    {"role": "coverglass", "item": "CMG-100", "thickness_um": 100.0},
    {"role": "coverglass-adhesive", "item": "ADH-55", "thickness_um": 50.0},
    {"role": "solar-cell", "item": "CELL-3J", "thickness_um": 150.0},
    {"role": "rear-adhesive", "item": "ADH-77", "thickness_um": 60.0},
]

INTERFACES = [
    "coverglass-to-coverglass-adhesive",
    "coverglass-adhesive-to-solar-cell",
    "solar-cell-to-rear-adhesive",
]

BOND_CONTROLS = [
    {"interface": INTERFACES[0], "agent": "ADH-55", "thickness_um": 50.0, "coverage": 0.98},
    {"interface": INTERFACES[1], "agent": "ADH-55", "thickness_um": 50.0, "coverage": 0.97},
    {"interface": INTERFACES[2], "agent": "ADH-77", "thickness_um": 60.0, "coverage": 0.96},
]

TERMINALS = [
    {"terminal": "TB-P", "polarity": "positive", "marked": True},
    {"terminal": "TB-N", "polarity": "negative", "marked": True},
]

CITATIONS = [
    {
        "constituent": "bare-solar-cell",
        "drawing": "BSC-4004",
        "issue_state": "released",
        "cited_issue": "C",
        "released_issue": "C",
    },
    {
        "constituent": "coverglass",
        "drawing": "CMG-5005",
        "issue_state": "released",
        "cited_issue": "A",
        "released_issue": "A",
    },
]

CLEAN_SPEC = {
    "drawing": "SCA-SCD-0002",
    "layers": LAYERS,
    "bond_controls": BOND_CONTROLS,
    "terminals": TERMINALS,
    "citations": CITATIONS,
}


def _spec(**overrides):
    item = copy.deepcopy(CLEAN_SPEC)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


class LayerStackTests(unittest.TestCase):
    def test_a_clean_stack_implies_one_interface_between_each_pair(self):
        result = layer_stack(LAYERS)
        self.assertEqual(result["interfaces"], INTERFACES)
        self.assertEqual(result["findings"], [])

    def test_the_stack_totals_its_layer_thicknesses(self):
        self.assertAlmostEqual(
            layer_stack(LAYERS)["total_thickness_um"], 360.0, places=9
        )

    def test_a_stack_drawn_outer_face_inward_is_in_order(self):
        self.assertTrue(layer_stack(LAYERS)["ordered"])

    def test_a_stack_out_of_order_is_a_different_assembly(self):
        shuffled = [LAYERS[2], LAYERS[0], LAYERS[1], LAYERS[3]]
        result = layer_stack(shuffled)
        self.assertFalse(result["ordered"])
        self.assertTrue(any("outer face inward" in f for f in result["findings"]))

    def test_a_stack_missing_a_required_role_is_reported(self):
        without_cell = [item for item in LAYERS if item["role"] != "solar-cell"]
        result = layer_stack(without_cell)
        self.assertEqual(result["missing_roles"], ["solar-cell"])

    def test_every_required_role_is_looked_for(self):
        result = layer_stack([LAYERS[3]])
        self.assertEqual(sorted(result["missing_roles"]), sorted(REQUIRED_LAYER_ROLES))

    def test_a_single_layer_stack_implies_no_interface(self):
        result = layer_stack([LAYERS[2]])
        self.assertEqual(result["interfaces"], [])
        self.assertTrue(any("no bonded interface" in f for f in result["findings"]))

    def test_a_repeated_layer_role_is_rejected(self):
        with self.assertRaises(ValueError):
            layer_stack(LAYERS + [copy.deepcopy(LAYERS[0])])

    def test_an_unknown_layer_role_is_rejected(self):
        with self.assertRaises(ValueError):
            layer_stack([{"role": "paint", "item": "X", "thickness_um": 1.0}])

    def test_a_zero_thickness_layer_is_rejected(self):
        bad = copy.deepcopy(LAYERS)
        bad[0]["thickness_um"] = 0.0
        with self.assertRaises(ValueError):
            layer_stack(bad)

    def test_an_empty_stack_is_rejected(self):
        with self.assertRaises(ValueError):
            layer_stack([])

    def test_every_declared_stack_role_is_placeable(self):
        for role in STACK_ORDER:
            result = layer_stack([{"role": role, "item": "X", "thickness_um": 10.0}])
            self.assertEqual(result["roles"], [role])


class InterfaceControlTests(unittest.TestCase):
    def test_one_bond_control_controls_the_joint(self):
        result = grade_interface(INTERFACES[0], BOND_CONTROLS)
        self.assertEqual(result["state"], INTERFACE_CONTROLLED)
        self.assertTrue(result["controlled"])

    def test_a_joint_with_no_bond_control_is_uncontrolled(self):
        records = [r for r in BOND_CONTROLS if r["interface"] != INTERFACES[1]]
        result = grade_interface(INTERFACES[1], records)
        self.assertEqual(result["state"], INTERFACE_UNCONTROLLED)
        self.assertFalse(result["controlled"])

    def test_two_bond_controls_leave_the_supplier_to_choose(self):
        records = copy.deepcopy(BOND_CONTROLS)
        records.append(dict(BOND_CONTROLS[0], agent="ADH-99"))
        result = grade_interface(INTERFACES[0], records)
        self.assertEqual(result["state"], INTERFACE_AMBIGUOUS)
        self.assertFalse(result["controlled"])

    def test_a_bond_exactly_on_the_coverage_floor_is_a_bond(self):
        records = [dict(BOND_CONTROLS[0], coverage=MIN_BOND_COVERAGE)]
        result = grade_interface(INTERFACES[0], records)
        self.assertAlmostEqual(result["coverage"], MIN_BOND_COVERAGE, places=9)
        self.assertEqual(result["state"], INTERFACE_CONTROLLED)

    def test_a_bond_under_the_coverage_floor_does_not_control_the_joint(self):
        records = [dict(BOND_CONTROLS[0], coverage=0.60)]
        result = grade_interface(INTERFACES[0], records)
        self.assertEqual(result["state"], INTERFACE_UNDER_COVERED)
        self.assertFalse(result["controlled"])

    def test_controls_naming_other_joints_are_ignored(self):
        result = grade_interface(INTERFACES[2], BOND_CONTROLS)
        self.assertEqual(len(result["controls"]), 1)
        self.assertEqual(result["controls"][0]["agent"], "ADH-77")

    def test_a_coverage_above_the_whole_joint_is_rejected(self):
        records = [dict(BOND_CONTROLS[0], coverage=1.4)]
        with self.assertRaises(ValueError):
            grade_interface(INTERFACES[0], records)

    def test_a_zero_coverage_bond_is_rejected(self):
        records = [dict(BOND_CONTROLS[0], coverage=0.0)]
        with self.assertRaises(ValueError):
            grade_interface(INTERFACES[0], records)

    def test_a_bond_control_missing_a_key_is_rejected(self):
        records = [{"interface": INTERFACES[0], "agent": "ADH-55", "coverage": 0.98}]
        with self.assertRaises(ValueError):
            grade_interface(INTERFACES[0], records)

    def test_a_blank_interface_name_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_interface("  ", BOND_CONTROLS)


class TerminalTests(unittest.TestCase):
    def test_both_polarities_identified_and_marked_is_clean(self):
        result = terminal_identification(TERMINALS)
        self.assertTrue(result["identified"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_polarity_is_reported(self):
        result = terminal_identification([TERMINALS[0]])
        self.assertEqual(result["missing_polarities"], ["negative"])
        self.assertFalse(result["identified"])

    def test_two_terminals_of_one_polarity_leave_the_connection_open(self):
        records = TERMINALS + [
            {"terminal": "TB-P2", "polarity": "positive", "marked": True}
        ]
        result = terminal_identification(records)
        self.assertEqual(result["duplicated_polarities"], ["positive"])
        self.assertFalse(result["identified"])

    def test_a_listed_but_unmarked_terminal_is_an_open_item_not_a_gap(self):
        records = copy.deepcopy(TERMINALS)
        records[1]["marked"] = False
        result = terminal_identification(records)
        self.assertEqual(result["unmarked"], ["TB-N"])
        self.assertTrue(result["identified"])

    def test_every_declared_polarity_is_looked_for(self):
        result = terminal_identification([])
        self.assertEqual(sorted(result["missing_polarities"]), sorted(TERMINAL_POLARITIES))

    def test_an_unknown_polarity_is_rejected(self):
        with self.assertRaises(ValueError):
            terminal_identification(
                [{"terminal": "TB-X", "polarity": "either", "marked": True}]
            )

    def test_a_non_boolean_mark_is_rejected(self):
        with self.assertRaises(ValueError):
            terminal_identification(
                [{"terminal": "TB-P", "polarity": "positive", "marked": "yes"}]
            )


class CitationTests(unittest.TestCase):
    def test_a_released_drawing_cited_at_its_released_issue_governs(self):
        result = cited_drawing_standing(CITATIONS[0])
        self.assertEqual(result["standing"], CITATION_GOVERNING)
        self.assertEqual(result["findings"], [])

    def test_a_draft_citation_controls_nothing(self):
        item = dict(CITATIONS[0], issue_state="draft")
        self.assertEqual(cited_drawing_standing(item)["standing"], CITATION_VOID)

    def test_a_cancelled_citation_controls_nothing(self):
        item = dict(CITATIONS[0], issue_state="cancelled")
        self.assertEqual(cited_drawing_standing(item)["standing"], CITATION_VOID)

    def test_a_superseded_citation_leaves_a_step_to_disposition(self):
        item = dict(CITATIONS[0], issue_state="superseded", released_issue="D")
        self.assertEqual(cited_drawing_standing(item)["standing"], CITATION_OFF_ISSUE)

    def test_a_citation_at_an_unreleased_issue_is_off_issue(self):
        item = dict(CITATIONS[0], cited_issue="B")
        self.assertEqual(cited_drawing_standing(item)["standing"], CITATION_OFF_ISSUE)

    def test_every_declared_issue_state_resolves(self):
        for state in CITATION_ISSUE_STATES:
            item = dict(CITATIONS[0], issue_state=state)
            self.assertIn(
                cited_drawing_standing(item)["standing"],
                (CITATION_GOVERNING, CITATION_OFF_ISSUE, CITATION_VOID),
            )

    def test_an_unknown_issue_state_is_rejected(self):
        with self.assertRaises(ValueError):
            cited_drawing_standing(dict(CITATIONS[0], issue_state="pending"))


class ControlShareTests(unittest.TestCase):
    def test_a_fully_controlled_stack_scores_one(self):
        graded = [grade_interface(i, BOND_CONTROLS) for i in INTERFACES]
        self.assertAlmostEqual(controlled_interface_share(graded), 1.0, places=9)

    def test_one_uncontrolled_joint_of_three_scores_two_thirds(self):
        records = [r for r in BOND_CONTROLS if r["interface"] != INTERFACES[1]]
        graded = [grade_interface(i, records) for i in INTERFACES]
        self.assertAlmostEqual(controlled_interface_share(graded), 2.0 / 3.0, places=9)

    def test_a_stack_with_no_joint_scores_nothing(self):
        self.assertAlmostEqual(controlled_interface_share([]), 0.0, places=9)

    def test_a_non_sequence_grading_is_rejected(self):
        with self.assertRaises(ValueError):
            controlled_interface_share({"interface": INTERFACES[0]})


class AssemblyDrawingTests(unittest.TestCase):
    def test_a_complete_assembly_drawing_is_releasable(self):
        result = assess_solar_cell_assembly_drawing(_spec())
        self.assertEqual(result["verdict"], SCA_DRAWING_RELEASABLE)
        self.assertAlmostEqual(result["interface_control_share"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_an_uncontrolled_joint_stops_the_release(self):
        records = [r for r in BOND_CONTROLS if r["interface"] != INTERFACES[1]]
        result = assess_solar_cell_assembly_drawing(_spec(bond_controls=records))
        self.assertEqual(result["uncontrolled_interfaces"], [INTERFACES[1]])
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_a_doubly_controlled_joint_stops_the_release(self):
        records = copy.deepcopy(BOND_CONTROLS)
        records.append(dict(BOND_CONTROLS[0], agent="ADH-99"))
        result = assess_solar_cell_assembly_drawing(_spec(bond_controls=records))
        self.assertEqual(result["ambiguous_interfaces"], [INTERFACES[0]])
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_a_bond_under_its_coverage_floor_stops_the_release(self):
        records = copy.deepcopy(BOND_CONTROLS)
        records[2]["coverage"] = 0.40
        result = assess_solar_cell_assembly_drawing(_spec(bond_controls=records))
        self.assertEqual(result["under_covered_interfaces"], [INTERFACES[2]])
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_a_bond_control_naming_a_joint_this_stack_lacks_stops_the_release(self):
        records = copy.deepcopy(BOND_CONTROLS)
        records.append(
            {
                "interface": "coverglass-to-solar-cell",
                "agent": "ADH-55",
                "thickness_um": 50.0,
                "coverage": 0.98,
            }
        )
        result = assess_solar_cell_assembly_drawing(_spec(bond_controls=records))
        self.assertEqual(result["stray_bond_controls"], ["coverglass-to-solar-cell"])
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_a_stack_out_of_order_stops_the_release(self):
        shuffled = [LAYERS[1], LAYERS[0], LAYERS[2], LAYERS[3]]
        result = assess_solar_cell_assembly_drawing(_spec(layers=shuffled))
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_a_missing_terminal_polarity_stops_the_release(self):
        result = assess_solar_cell_assembly_drawing(_spec(terminals=[TERMINALS[0]]))
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_an_unmarked_terminal_releases_only_against_open_items(self):
        records = copy.deepcopy(TERMINALS)
        records[0]["marked"] = False
        result = assess_solar_cell_assembly_drawing(_spec(terminals=records))
        self.assertEqual(result["verdict"], SCA_DRAWING_OPEN_ITEMS)

    def test_a_void_citation_stops_the_release(self):
        records = copy.deepcopy(CITATIONS)
        records[0]["issue_state"] = "draft"
        result = assess_solar_cell_assembly_drawing(_spec(citations=records))
        self.assertEqual(result["void_citations"], ["bare-solar-cell"])
        self.assertEqual(result["verdict"], SCA_DRAWING_NOT_RELEASABLE)

    def test_an_off_issue_citation_releases_only_against_open_items(self):
        records = copy.deepcopy(CITATIONS)
        records[1]["cited_issue"] = "B"
        result = assess_solar_cell_assembly_drawing(_spec(citations=records))
        self.assertEqual(result["off_issue_citations"], ["coverglass"])
        self.assertEqual(result["verdict"], SCA_DRAWING_OPEN_ITEMS)

    def test_a_control_share_exactly_on_its_threshold_is_met(self):
        result = assess_solar_cell_assembly_drawing(
            _spec(required_interface_control_share=1.0)
        )
        self.assertAlmostEqual(result["interface_control_share"], 1.0, places=9)
        self.assertEqual(result["verdict"], SCA_DRAWING_RELEASABLE)

    def test_a_control_share_under_its_threshold_is_reported(self):
        records = [r for r in BOND_CONTROLS if r["interface"] != INTERFACES[1]]
        result = assess_solar_cell_assembly_drawing(_spec(bond_controls=records))
        self.assertAlmostEqual(
            result["interface_control_share"], 2.0 / 3.0, places=9
        )
        self.assertTrue(
            any("controlled interface share" in f for f in result["findings"])
        )

    def test_a_constituent_cited_twice_is_rejected(self):
        records = copy.deepcopy(CITATIONS)
        records.append(copy.deepcopy(CITATIONS[0]))
        with self.assertRaises(ValueError):
            assess_solar_cell_assembly_drawing(_spec(citations=records))

    def test_an_assembly_drawing_citing_nothing_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_cell_assembly_drawing(_spec(citations=[]))

    def test_a_threshold_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_cell_assembly_drawing(
                _spec(required_interface_control_share=-0.2)
            )

    def test_a_spec_missing_its_terminals_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_cell_assembly_drawing(_spec(terminals=None))

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_cell_assembly_drawing([CLEAN_SPEC])


if __name__ == "__main__":
    unittest.main(verbosity=1)

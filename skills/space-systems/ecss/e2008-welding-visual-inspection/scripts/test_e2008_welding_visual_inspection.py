#!/usr/bin/env python3
"""Contract test for the drawing-led weld inspection (offline)."""

import copy
import unittest

from e2008_welding_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_WELDING_ALLOWANCES,
    INSPECTION_INCOMPLETE,
    REJECT,
    REWORK,
    STRING_TERMINATION,
    TERMINAL,
    assess_weld,
    assess_weld_location,
    inspect_welding,
    validate_control_drawing,
    validate_welding_allowances,
    weld_geometry,
)


def _spec(location_id="LOC-001", location_type=STRING_TERMINATION, **overrides):
    entry = {
        "location_id": location_id,
        "location_type": location_type,
        "required_weld_count": 4,
        "position_tolerance_mm": 0.30,
        "nugget_diameter_min_mm": 0.80,
        "nugget_diameter_max_mm": 1.20,
    }
    entry.update(overrides)
    return entry


def _weld(weld_id="W-1", **overrides):
    record = {
        "weld_id": weld_id,
        "offset_x_mm": 0.0,
        "offset_y_mm": 0.0,
        "nugget_diameter_mm": 1.00,
        "cracked": False,
        "expelled": False,
        "discoloured": False,
    }
    record.update(overrides)
    return record


def _welds(how_many, **overrides):
    return [_weld("W-%d" % n, **overrides) for n in range(1, how_many + 1)]


def _location(location_id="LOC-001", welds=None):
    return {
        "location_id": location_id,
        "welds": _welds(4) if welds is None else welds,
    }


def _drawing(locations=None, revision="C"):
    return {
        "drawing_id": "ACD-7741",
        "revision": revision,
        "locations": locations if locations is not None else [_spec()],
    }


def _clean_assembly(how_many, revision="C"):
    specs = [_spec("LOC-%03d" % n) for n in range(1, how_many + 1)]
    records = [_location("LOC-%03d" % n) for n in range(1, how_many + 1)]
    assembly = {
        "assembly_id": "PVA-11",
        "drawing_revision": revision,
        "locations": records,
    }
    return assembly, _drawing(specs, revision=revision)


class AllowanceValidationTests(unittest.TestCase):
    def test_default_allowances_validate(self):
        self.assertIs(
            validate_welding_allowances(DEFAULT_WELDING_ALLOWANCES),
            DEFAULT_WELDING_ALLOWANCES,
        )

    def test_non_mapping_allowances_refused(self):
        with self.assertRaises(ValueError):
            validate_welding_allowances("default")

    def test_missing_fraction_refused(self):
        broken = copy.deepcopy(DEFAULT_WELDING_ALLOWANCES)
        del broken["max_expelled_weld_fraction"]
        with self.assertRaises(ValueError):
            validate_welding_allowances(broken)

    def test_fraction_above_one_refused(self):
        broken = copy.deepcopy(DEFAULT_WELDING_ALLOWANCES)
        broken["max_discoloured_weld_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_welding_allowances(broken)

    def test_zero_sound_weld_reserve_refused(self):
        broken = copy.deepcopy(DEFAULT_WELDING_ALLOWANCES)
        broken["min_sound_welds"] = 0
        with self.assertRaises(ValueError):
            validate_welding_allowances(broken)

    def test_cracked_allowance_above_expelled_allowance_refused(self):
        broken = copy.deepcopy(DEFAULT_WELDING_ALLOWANCES)
        broken["max_cracked_weld_fraction"] = 0.5
        with self.assertRaises(ValueError):
            validate_welding_allowances(broken)

    def test_rework_margin_below_one_refused(self):
        broken = copy.deepcopy(DEFAULT_WELDING_ALLOWANCES)
        broken["rework_margin_factor"] = 0.4
        with self.assertRaises(ValueError):
            validate_welding_allowances(broken)


class ControlDrawingTests(unittest.TestCase):
    def test_a_valid_drawing_indexes_by_location(self):
        specs = validate_control_drawing(_drawing())
        self.assertEqual(sorted(specs), ["LOC-001"])

    def test_drawing_without_a_revision_refused(self):
        drawing = _drawing()
        drawing["revision"] = ""
        with self.assertRaises(ValueError):
            validate_control_drawing(drawing)

    def test_drawing_with_no_locations_refused(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(_drawing(locations=[]))

    def test_duplicate_drawing_location_refused(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(_drawing([_spec(), _spec()]))

    def test_unknown_location_type_refused(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(_drawing([_spec(location_type="busbar")]))

    def test_terminal_location_type_accepted(self):
        specs = validate_control_drawing(
            _drawing([_spec("LOC-009", location_type=TERMINAL)])
        )
        self.assertEqual(specs["LOC-009"]["location_type"], TERMINAL)

    def test_inverted_nugget_band_refused(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(
                _drawing([_spec(nugget_diameter_min_mm=1.4)])
            )

    def test_zero_position_tolerance_refused(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(_drawing([_spec(position_tolerance_mm=0.0)]))

    def test_zero_required_weld_count_refused(self):
        with self.assertRaises(ValueError):
            validate_control_drawing(_drawing([_spec(required_weld_count=0)]))


class WeldGeometryTests(unittest.TestCase):
    def test_offset_is_the_root_sum_square_of_the_components(self):
        geometry = weld_geometry(
            _weld(offset_x_mm=0.12, offset_y_mm=0.16), _spec()
        )
        self.assertAlmostEqual(geometry["position_offset_mm"], 0.20, places=9)
        self.assertTrue(geometry["within_position_tolerance"])

    def test_an_offset_exactly_on_the_tolerance_is_inside_it(self):
        geometry = weld_geometry(
            _weld(offset_x_mm=0.18, offset_y_mm=0.24), _spec()
        )
        self.assertAlmostEqual(geometry["position_offset_mm"], 0.30, places=9)
        self.assertAlmostEqual(geometry["offset_ratio"], 1.0, places=9)
        self.assertTrue(geometry["within_position_tolerance"])

    def test_a_diameter_on_the_band_floor_is_not_undersized(self):
        geometry = weld_geometry(_weld(nugget_diameter_mm=0.80), _spec())
        self.assertFalse(geometry["undersized"])
        self.assertFalse(geometry["oversized"])

    def test_a_diameter_below_the_band_is_undersized(self):
        geometry = weld_geometry(_weld(nugget_diameter_mm=0.70), _spec())
        self.assertTrue(geometry["undersized"])

    def test_a_diameter_above_the_band_is_oversized(self):
        geometry = weld_geometry(_weld(nugget_diameter_mm=1.35), _spec())
        self.assertTrue(geometry["oversized"])

    def test_non_positive_diameter_refused(self):
        with self.assertRaises(ValueError):
            weld_geometry(_weld(nugget_diameter_mm=0.0), _spec())

    def test_non_numeric_offset_refused(self):
        with self.assertRaises(ValueError):
            weld_geometry(_weld(offset_x_mm="near"), _spec())

    def test_weld_without_an_id_refused(self):
        with self.assertRaises(ValueError):
            weld_geometry(_weld(weld_id=" "), _spec())


class WeldDispositionTests(unittest.TestCase):
    def test_a_weld_on_the_drawing_accepts(self):
        result = assess_weld(_weld(), _spec())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["sound"])
        self.assertEqual(result["findings"], [])

    def test_an_undersized_nugget_rejects(self):
        result = assess_weld(_weld(nugget_diameter_mm=0.60), _spec())
        self.assertEqual(result["verdict"], REJECT)
        self.assertFalse(result["sound"])

    def test_an_oversized_nugget_reworks(self):
        result = assess_weld(_weld(nugget_diameter_mm=1.30), _spec())
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["sound"])

    def test_a_cracked_nugget_rejects(self):
        result = assess_weld(_weld(cracked=True), _spec())
        self.assertEqual(result["verdict"], REJECT)
        self.assertFalse(result["sound"])
        self.assertIn("cracked", result["conditions"])

    def test_expulsion_reworks(self):
        result = assess_weld(_weld(expelled=True), _spec())
        self.assertEqual(result["verdict"], REWORK)

    def test_discoloration_alone_does_not_move_the_weld_verdict(self):
        result = assess_weld(_weld(discoloured=True), _spec())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["conditions"], ["discoloured"])

    def test_an_offset_inside_the_rework_margin_reworks(self):
        result = assess_weld(_weld(offset_x_mm=0.45), _spec())
        self.assertEqual(result["verdict"], REWORK)

    def test_an_offset_past_the_rework_margin_rejects(self):
        result = assess_weld(_weld(offset_x_mm=0.90), _spec())
        self.assertEqual(result["verdict"], REJECT)

    def test_non_boolean_condition_flag_refused(self):
        with self.assertRaises(ValueError):
            assess_weld(_weld(cracked="yes"), _spec())


class WeldLocationTests(unittest.TestCase):
    def test_a_full_clean_location_accepts(self):
        result = assess_weld_location(_location(), _spec())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["welds_present"], 4)
        self.assertEqual(result["sound_weld_count"], 4)
        self.assertEqual(result["missing_weld_count"], 0)
        self.assertEqual(result["findings"], [])

    def test_a_short_weld_population_reworks_and_is_counted(self):
        result = assess_weld_location(_location(welds=_welds(3)), _spec())
        self.assertEqual(result["verdict"], REWORK)
        self.assertEqual(result["missing_weld_count"], 1)

    def test_more_welds_than_the_drawing_carries_refused(self):
        with self.assertRaises(ValueError):
            assess_weld_location(_location(welds=_welds(5)), _spec())

    def test_duplicate_weld_ids_refused(self):
        with self.assertRaises(ValueError):
            assess_weld_location(
                _location(welds=[_weld("W-1"), _weld("W-1")]), _spec()
            )

    def test_welds_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            assess_weld_location({"location_id": "LOC-001", "welds": "four"}, _spec())

    def test_a_single_cracked_nugget_takes_the_location_out(self):
        welds = _welds(4)
        welds[0]["cracked"] = True
        result = assess_weld_location(_location(welds=welds), _spec())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["condition_counts"]["cracked"], 1)
        self.assertEqual(result["not_accepted_weld_ids"], ["W-1"])

    def test_discoloration_inside_the_allowance_accepts(self):
        welds = _welds(4)
        welds[0]["discoloured"] = True
        result = assess_weld_location(_location(welds=welds), _spec())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["condition_fractions"]["discoloured"], 0.25, places=9)

    def test_discoloration_past_the_allowance_reworks(self):
        welds = _welds(4)
        for weld in welds[:2]:
            weld["discoloured"] = True
        result = assess_weld_location(_location(welds=welds), _spec())
        self.assertEqual(result["verdict"], REWORK)

    def test_too_few_sound_welds_left_rejects(self):
        welds = _welds(4)
        welds[0]["nugget_diameter_mm"] = 0.5
        welds[1]["nugget_diameter_mm"] = 0.5
        welds[2]["nugget_diameter_mm"] = 0.5
        result = assess_weld_location(_location(welds=welds), _spec())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["sound_weld_count"], 1)
        self.assertTrue(any("in reserve" in f for f in result["findings"]))

    def test_a_location_with_no_sound_weld_left_names_the_open_path(self):
        welds = _welds(4, cracked=True)
        result = assess_weld_location(_location(welds=welds), _spec())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["sound_weld_count"], 0)
        self.assertTrue(any("no current path" in f for f in result["findings"]))

    def test_the_reserve_never_exceeds_what_the_drawing_calls_for(self):
        spec = _spec(required_weld_count=1)
        result = assess_weld_location(_location(welds=_welds(1)), spec)
        self.assertEqual(result["verdict"], ACCEPT)


class AssemblyRollupTests(unittest.TestCase):
    def test_a_clean_assembly_accepts(self):
        assembly, drawing = _clean_assembly(20)
        result = inspect_welding(assembly, drawing)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["weld_count"], 80)
        self.assertEqual(result["sound_weld_count"], 80)
        self.assertEqual(result["affected_location_count"], 0)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 1.0, places=9)

    def test_one_affected_location_stays_inside_the_assembly_allowance(self):
        assembly, drawing = _clean_assembly(20)
        assembly["locations"][3]["welds"][0]["nugget_diameter_mm"] = 1.30
        result = inspect_welding(assembly, drawing)
        self.assertEqual(result["verdict"], REWORK)
        self.assertEqual(result["affected_location_count"], 1)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 0.0, places=9)

    def test_the_assembly_allowance_bites_once_it_is_exceeded(self):
        assembly, drawing = _clean_assembly(20)
        for index in range(4):
            assembly["locations"][index]["welds"][0]["discoloured"] = True
            assembly["locations"][index]["welds"][1]["discoloured"] = True
        result = inspect_welding(assembly, drawing)
        self.assertEqual(result["affected_location_count"], 4)
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("rework margin of" in f for f in result["findings"]))

    def test_an_undeclared_welded_location_is_refused(self):
        assembly, drawing = _clean_assembly(3)
        assembly["locations"].append(_location("LOC-099"))
        with self.assertRaises(ValueError):
            inspect_welding(assembly, drawing)

    def test_a_drawing_location_with_no_record_leaves_the_assembly_open(self):
        assembly, drawing = _clean_assembly(20)
        assembly["locations"] = assembly["locations"][:18]
        result = inspect_welding(assembly, drawing)
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["uninspected_location_ids"], ["LOC-019", "LOC-020"])
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_a_mismatched_drawing_revision_is_refused(self):
        assembly, drawing = _clean_assembly(3)
        assembly["drawing_revision"] = "B"
        with self.assertRaises(ValueError):
            inspect_welding(assembly, drawing)

    def test_a_duplicate_location_record_is_refused(self):
        assembly, drawing = _clean_assembly(3)
        assembly["locations"].append(_location("LOC-001"))
        with self.assertRaises(ValueError):
            inspect_welding(assembly, drawing)

    def test_a_rejected_location_names_itself(self):
        assembly, drawing = _clean_assembly(20)
        assembly["locations"][7]["welds"][0]["cracked"] = True
        result = inspect_welding(assembly, drawing)
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_location_ids"], ["LOC-008"])
        self.assertEqual(result["disposition_counts"][REJECT], 1)
        self.assertEqual(result["disposition_counts"][ACCEPT], 19)

    def test_non_mapping_assembly_refused(self):
        drawing = _drawing()
        with self.assertRaises(ValueError):
            inspect_welding("PVA-11", drawing)

    def test_locations_not_a_list_refused(self):
        drawing = _drawing()
        with self.assertRaises(ValueError):
            inspect_welding(
                {
                    "assembly_id": "PVA-11",
                    "drawing_revision": "C",
                    "locations": "one",
                },
                drawing,
            )

    def test_the_report_carries_the_drawing_it_answered_to(self):
        assembly, drawing = _clean_assembly(2)
        result = inspect_welding(assembly, drawing)
        self.assertEqual(result["drawing_id"], "ACD-7741")
        self.assertEqual(result["drawing_revision"], "C")
        self.assertEqual(result["declared_location_count"], 2)


if __name__ == "__main__":
    unittest.main()

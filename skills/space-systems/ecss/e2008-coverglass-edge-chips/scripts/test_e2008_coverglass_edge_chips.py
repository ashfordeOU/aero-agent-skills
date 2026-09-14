#!/usr/bin/env python3
"""Contract test for the coverglass edge chip limits (offline)."""

import copy
import unittest

from e2008_coverglass_edge_chips_logic import (
    ACCEPT,
    COVERGLASS_EDGES,
    CORNER_CHIP,
    CORNER_CLAUSE_ROUTE,
    DEFAULT_EDGE_CHIP_CRITERIA,
    EDGE_CHIP,
    GLASS_ACCEPTED,
    GLASS_REFERRED,
    GLASS_REJECTED,
    LENGTH_EDGE_A,
    REFER,
    REJECT,
    WIDTH_EDGE_A,
    aperture_encroachment_mm,
    assess_coverglass_edge_chips,
    assess_edge_chip,
    edge_length_mm,
    face_area_lost_mm2,
    locate_edge_chip,
    validate_coverglass_geometry,
    validate_edge_chip_criteria,
)

GEOMETRY = {
    "length_mm": 42.0,
    "width_mm": 42.0,
    "thickness_um": 100.0,
    "overhang_mm": 0.5,
}


def _chip(**overrides):
    chip = {
        "id": "G1",
        "edge": LENGTH_EDGE_A,
        "position_mm": 10.0,
        "run_mm": 2.0,
        "face_projection_mm": 0.15,
    }
    chip.update(overrides)
    return chip


def _glass(chips=None, **overrides):
    glass = {
        "coverglass_id": "CG-001",
        "geometry": copy.deepcopy(GEOMETRY),
        "chips": copy.deepcopy(chips) if chips else [],
    }
    glass.update(overrides)
    return glass


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_edge_chip_criteria(DEFAULT_EDGE_CHIP_CRITERIA),
            DEFAULT_EDGE_CHIP_CRITERIA,
        )

    def test_clause_ceiling_is_a_quarter_millimetre(self):
        self.assertAlmostEqual(
            DEFAULT_EDGE_CHIP_CRITERIA["max_face_projection_mm"], 0.25, places=9
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_edge_chip_criteria("default")

    def test_missing_projection_ceiling_rejected(self):
        broken = dict(DEFAULT_EDGE_CHIP_CRITERIA)
        del broken["max_face_projection_mm"]
        with self.assertRaises(ValueError):
            validate_edge_chip_criteria(broken)

    def test_run_fraction_above_one_rejected(self):
        broken = dict(DEFAULT_EDGE_CHIP_CRITERIA, max_run_fraction_of_edge=1.3)
        with self.assertRaises(ValueError):
            validate_edge_chip_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_EDGE_CHIP_CRITERIA, run_review_factor=0.7)
        with self.assertRaises(ValueError):
            validate_edge_chip_criteria(broken)

    def test_non_integer_count_allowance_rejected(self):
        broken = dict(DEFAULT_EDGE_CHIP_CRITERIA, max_chips_per_edge=2.5)
        with self.assertRaises(ValueError):
            validate_edge_chip_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_geometry_derives_perimeter_and_areas(self):
        resolved = validate_coverglass_geometry(GEOMETRY)
        self.assertAlmostEqual(resolved["perimeter_mm"], 168.0, places=9)
        self.assertAlmostEqual(resolved["face_area_mm2"], 1764.0, places=9)
        self.assertAlmostEqual(resolved["aperture_area_mm2"], 41.0 * 41.0, places=9)

    def test_overhang_that_swallows_the_aperture_rejected(self):
        broken = dict(GEOMETRY, overhang_mm=25.0)
        with self.assertRaises(ValueError):
            validate_coverglass_geometry(broken)

    def test_non_positive_thickness_rejected(self):
        broken = dict(GEOMETRY, thickness_um=0.0)
        with self.assertRaises(ValueError):
            validate_coverglass_geometry(broken)

    def test_non_mapping_geometry_rejected(self):
        with self.assertRaises(ValueError):
            validate_coverglass_geometry("42x42")

    def test_edge_length_follows_the_named_edge(self):
        narrow = dict(GEOMETRY, width_mm=20.0)
        self.assertAlmostEqual(edge_length_mm(LENGTH_EDGE_A, narrow), 42.0, places=9)
        self.assertAlmostEqual(edge_length_mm(WIDTH_EDGE_A, narrow), 20.0, places=9)

    def test_unknown_edge_rejected(self):
        with self.assertRaises(ValueError):
            edge_length_mm("bevel", GEOMETRY)

    def test_every_named_edge_resolves(self):
        for edge in COVERGLASS_EDGES:
            self.assertGreater(edge_length_mm(edge, GEOMETRY), 1.0)


class PlacementTests(unittest.TestCase):
    def test_mid_edge_chip_is_an_edge_chip(self):
        placement = locate_edge_chip(_chip(), GEOMETRY)
        self.assertEqual(placement["zone"], EDGE_CHIP)

    def test_chip_starting_at_a_corner_takes_a_corner(self):
        placement = locate_edge_chip(_chip(position_mm=0.0), GEOMETRY)
        self.assertEqual(placement["zone"], CORNER_CHIP)

    def test_chip_ending_at_a_corner_takes_a_corner(self):
        placement = locate_edge_chip(_chip(position_mm=40.0, run_mm=2.0), GEOMETRY)
        self.assertEqual(placement["zone"], CORNER_CHIP)
        self.assertAlmostEqual(placement["distance_to_corner_mm"], 0.0, places=9)

    def test_chip_longer_than_its_edge_rejected(self):
        with self.assertRaises(ValueError):
            locate_edge_chip(_chip(position_mm=40.0, run_mm=5.0), GEOMETRY)

    def test_zero_run_rejected(self):
        with self.assertRaises(ValueError):
            locate_edge_chip(_chip(run_mm=0.0), GEOMETRY)

    def test_negative_position_rejected(self):
        with self.assertRaises(ValueError):
            locate_edge_chip(_chip(position_mm=-1.0), GEOMETRY)

    def test_non_mapping_chip_rejected(self):
        with self.assertRaises(ValueError):
            locate_edge_chip("edge chip", GEOMETRY)


class GeometryHelperTests(unittest.TestCase):
    def test_face_area_lost_is_the_triangle_of_run_and_projection(self):
        self.assertAlmostEqual(face_area_lost_mm2(2.0, 0.15), 0.15, places=9)

    def test_face_area_lost_rejects_a_non_positive_projection(self):
        with self.assertRaises(ValueError):
            face_area_lost_mm2(2.0, 0.0)

    def test_projection_inside_the_overhang_reaches_no_aperture(self):
        self.assertAlmostEqual(
            aperture_encroachment_mm(0.3, GEOMETRY), 0.0, places=9
        )

    def test_projection_exactly_on_the_overhang_reaches_no_aperture(self):
        self.assertAlmostEqual(
            aperture_encroachment_mm(0.5, GEOMETRY), 0.0, places=9
        )

    def test_projection_past_the_overhang_stands_over_the_aperture(self):
        self.assertAlmostEqual(
            aperture_encroachment_mm(0.7, GEOMETRY), 0.2, places=9
        )


class ChipDispositionTests(unittest.TestCase):
    def test_shallow_mid_edge_chip_accepted(self):
        result = assess_edge_chip(_chip(), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_projection_exactly_on_the_quarter_millimetre_still_accepts(self):
        result = assess_edge_chip(_chip(face_projection_mm=0.25), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(result["projection_margin_mm"], 0.0, places=9)

    def test_projection_past_the_ceiling_but_inside_the_overhang_is_referred(self):
        result = assess_edge_chip(_chip(face_projection_mm=0.4), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)
        self.assertAlmostEqual(result["aperture_encroachment_mm"], 0.0, places=9)

    def test_projection_over_the_aperture_rejects(self):
        result = assess_edge_chip(_chip(face_projection_mm=0.7), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)
        self.assertAlmostEqual(result["aperture_encroachment_mm"], 0.2, places=9)

    def test_the_same_projection_is_graded_against_the_declared_overhang(self):
        tight = dict(GEOMETRY, overhang_mm=0.3)
        on_wide = assess_edge_chip(_chip(face_projection_mm=0.4), GEOMETRY)
        on_tight = assess_edge_chip(_chip(face_projection_mm=0.4), tight)
        self.assertEqual(on_wide["disposition"], REFER)
        self.assertEqual(on_tight["disposition"], REJECT)

    def test_long_run_along_the_edge_is_referred(self):
        result = assess_edge_chip(_chip(run_mm=5.0), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)

    def test_very_long_run_along_the_edge_rejects(self):
        result = assess_edge_chip(_chip(run_mm=9.0), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_run_allowance_scales_with_the_edge_it_sits_on(self):
        narrow = dict(GEOMETRY, width_mm=20.0)
        on_long = assess_edge_chip(_chip(run_mm=3.0), narrow)
        on_short = assess_edge_chip(
            _chip(edge=WIDTH_EDGE_A, position_mm=5.0, run_mm=3.0), narrow
        )
        self.assertEqual(on_long["disposition"], ACCEPT)
        self.assertEqual(on_short["disposition"], REFER)

    def test_a_chip_that_takes_a_corner_is_routed_to_the_corner_clause(self):
        result = assess_edge_chip(_chip(position_mm=0.0), GEOMETRY)
        self.assertEqual(result["zone"], CORNER_CHIP)
        self.assertEqual(result["routed_to"], CORNER_CLAUSE_ROUTE)
        self.assertEqual(result["disposition"], REFER)

    def test_missing_projection_rejected(self):
        chip = _chip()
        del chip["face_projection_mm"]
        with self.assertRaises(ValueError):
            assess_edge_chip(chip, GEOMETRY)

    def test_negative_projection_rejected(self):
        with self.assertRaises(ValueError):
            assess_edge_chip(_chip(face_projection_mm=-0.1), GEOMETRY)


class GlassRollupTests(unittest.TestCase):
    def test_clean_glass_is_accepted(self):
        result = assess_coverglass_edge_chips(_glass([_chip()]))
        self.assertEqual(result["verdict"], GLASS_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_worst_chip_sets_the_glass_verdict(self):
        result = assess_coverglass_edge_chips(
            _glass(
                [
                    _chip(),
                    _chip(id="G2", position_mm=20.0, face_projection_mm=0.9),
                ]
            )
        )
        self.assertEqual(result["verdict"], GLASS_REJECTED)
        self.assertEqual(result["not_accepted_ids"], ["G2"])

    def test_deepest_projection_is_reported_for_the_glass(self):
        result = assess_coverglass_edge_chips(
            _glass(
                [
                    _chip(),
                    _chip(id="G2", position_mm=20.0, face_projection_mm=0.22),
                ]
            )
        )
        self.assertAlmostEqual(result["deepest_projection_mm"], 0.22, places=9)

    def test_cumulative_face_area_catches_individually_clean_chips(self):
        criteria = dict(
            DEFAULT_EDGE_CHIP_CRITERIA, max_cumulative_face_area_fraction=1e-5
        )
        result = assess_coverglass_edge_chips(_glass([_chip()]), criteria)
        self.assertEqual(result["chips"][0]["disposition"], ACCEPT)
        self.assertAlmostEqual(result["face_area_lost_mm2"], 0.15, places=9)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_cumulative_run_along_the_perimeter_is_enforced(self):
        chips = [
            _chip(id="G%d" % index, edge=edge, position_mm=5.0, run_mm=2.0)
            for index, edge in enumerate(COVERGLASS_EDGES[:3])
        ]
        result = assess_coverglass_edge_chips(_glass(chips))
        for chip in result["chips"]:
            self.assertEqual(chip["disposition"], ACCEPT)
        self.assertAlmostEqual(result["cumulative_run_mm"], 6.0, places=9)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_too_many_chips_on_one_edge_is_referred(self):
        chips = [
            _chip(id="G1", position_mm=2.0),
            _chip(id="G2", position_mm=12.0),
            _chip(id="G3", position_mm=22.0),
        ]
        result = assess_coverglass_edge_chips(_glass(chips))
        self.assertEqual(result["chips_per_edge"][LENGTH_EDGE_A], 3)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_too_many_chips_on_one_glass_is_referred(self):
        chips = []
        for index, edge in enumerate(COVERGLASS_EDGES):
            chips.append(_chip(id="G%da" % index, edge=edge, position_mm=4.0))
            if index < 1:
                chips.append(_chip(id="G%db" % index, edge=edge, position_mm=14.0))
        result = assess_coverglass_edge_chips(_glass(chips))
        self.assertEqual(len(result["chips"]), 5)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_chips_closer_than_the_separation_are_reported_as_a_pair(self):
        chips = [
            _chip(id="G1", position_mm=5.0, run_mm=2.0),
            _chip(id="G2", position_mm=7.5, run_mm=2.0),
        ]
        result = assess_coverglass_edge_chips(_glass(chips))
        self.assertEqual(result["clustered_chip_pairs"], 1)
        self.assertEqual(result["verdict"], GLASS_REFERRED)

    def test_chips_on_different_edges_are_never_a_pair(self):
        chips = [
            _chip(id="G1", edge=COVERGLASS_EDGES[0], position_mm=5.0),
            _chip(id="G2", edge=COVERGLASS_EDGES[1], position_mm=5.0),
        ]
        result = assess_coverglass_edge_chips(_glass(chips))
        self.assertEqual(result["clustered_chip_pairs"], 0)
        self.assertEqual(result["verdict"], GLASS_ACCEPTED)

    def test_corner_taking_chips_are_listed_for_the_corner_clause(self):
        result = assess_coverglass_edge_chips(
            _glass([_chip(id="G1", position_mm=0.0), _chip(id="G2", position_mm=20.0)])
        )
        self.assertEqual(result["routed_to_corner_clause"], ["G1"])

    def test_duplicate_chip_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_edge_chips(
                _glass([_chip(id="D"), _chip(id="D", position_mm=20.0)])
            )

    def test_glass_without_an_id_rejected(self):
        glass = _glass([_chip()])
        glass["coverglass_id"] = "   "
        with self.assertRaises(ValueError):
            assess_coverglass_edge_chips(glass)

    def test_non_list_chip_collection_rejected(self):
        glass = _glass()
        glass["chips"] = _chip()
        with self.assertRaises(ValueError):
            assess_coverglass_edge_chips(glass)

    def test_glass_with_no_chips_is_accepted(self):
        result = assess_coverglass_edge_chips(_glass())
        self.assertEqual(result["verdict"], GLASS_ACCEPTED)
        self.assertAlmostEqual(result["deepest_projection_mm"], 0.0, places=9)

    def test_input_is_not_mutated_by_the_screen(self):
        glass = _glass([_chip(), _chip(id="G2", position_mm=25.0)])
        before = copy.deepcopy(glass)
        assess_coverglass_edge_chips(glass)
        self.assertEqual(glass, before)


if __name__ == "__main__":
    unittest.main()

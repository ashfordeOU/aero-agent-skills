"""Contract tests for the part placement and build orientation logic."""

import copy
import math
import unittest

from q7080_part_placement_and_orientation_logic import (
    DEFAULT_SELF_SUPPORT_ANGLE_DEG,
    assess_placement,
    blade_skew_deg,
    bonded_span_mm,
    build_height_mm,
    critical_axis_angle_deg,
    evaluate_candidate,
    facet_inclination_deg,
    long_axis_deg,
    oriented_extents,
    residual_stress_index,
    rotate_vector,
    score_candidate,
    select_orientation,
    unit_vector,
    unsupported_area_mm2,
    unsupported_facets,
    validate_bbox,
    validate_orientation,
)

BBOX = (120.0, 40.0, 30.0)
DIAGONAL = 0.7071067811865476

FACETS = [
    {"id": "under", "normal": (0.0, 0.0, -1.0), "area_mm2": 400.0},
    {"id": "top", "normal": (0.0, 0.0, 1.0), "area_mm2": 400.0},
    {"id": "wall", "normal": (0.0, -1.0, 0.0), "area_mm2": 200.0},
    {"id": "chamfer", "normal": (0.0, -DIAGONAL, -DIAGONAL), "area_mm2": 100.0,
     "critical": True},
]

CANDIDATES = [
    {"id": "flat", "tilt_deg": 0.0, "rotation_deg": 0.0},
    {"id": "rot-90", "tilt_deg": 0.0, "rotation_deg": 90.0},
]


def spec(candidates=None, **extra):
    base = {
        "bbox_mm": BBOX,
        "facets": copy.deepcopy(FACETS),
        "candidates": copy.deepcopy(CANDIDATES if candidates is None else candidates),
        "critical_axis": (1.0, 0.0, 0.0),
        "envelope_height_mm": 300.0,
        "min_critical_axis_angle_deg": 30.0,
        "self_support_angle_deg": DEFAULT_SELF_SUPPORT_ANGLE_DEG,
        "recoater_travel_deg": 0.0,
        "min_blade_skew_deg": 20.0,
        "reference_area_mm2": 1000.0,
        "reference_height_mm": 100.0,
        "reference_span_mm": 100.0,
        "weights": {"support": 1.0, "height": 1.0, "stress": 1.0},
    }
    base.update(extra)
    return base


class ValidationTests(unittest.TestCase):
    def test_bbox_returned_as_floats(self):
        self.assertEqual(validate_bbox((120, 40, 30)), (120.0, 40.0, 30.0))

    def test_zero_bbox_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_bbox((120.0, 0.0, 30.0))

    def test_malformed_bbox_rejected(self):
        with self.assertRaises(ValueError):
            validate_bbox((120.0, 40.0))

    def test_candidate_normalised(self):
        self.assertEqual(validate_orientation(CANDIDATES[1]), ("rot-90", 0.0, 90.0))

    def test_candidate_without_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_orientation({"tilt_deg": 0.0})

    def test_tilt_outside_half_turn_rejected(self):
        with self.assertRaises(ValueError):
            validate_orientation({"id": "x", "tilt_deg": 200.0})

    def test_zero_length_vector_rejected(self):
        with self.assertRaises(ValueError):
            unit_vector((0.0, 0.0, 0.0))

    def test_two_component_vector_rejected(self):
        with self.assertRaises(ValueError):
            unit_vector((1.0, 0.0))

    def test_rotation_preserves_unit_length(self):
        rotated = rotate_vector((0.0, -DIAGONAL, -DIAGONAL), 37.0, 24.0)
        self.assertAlmostEqual(math.sqrt(sum(c * c for c in rotated)), 1.0, places=9)


class GeometryTests(unittest.TestCase):
    def test_unrotated_extents_are_the_bbox(self):
        ex, ey, ez = oriented_extents(BBOX, 0.0, 0.0)
        self.assertAlmostEqual(ex, 120.0, places=9)
        self.assertAlmostEqual(ey, 40.0, places=9)
        self.assertAlmostEqual(ez, 30.0, places=9)

    def test_quarter_turn_swaps_the_plane_axes(self):
        ex, ey, _ = oriented_extents(BBOX, 0.0, 90.0)
        self.assertAlmostEqual(ex, 40.0, places=9)
        self.assertAlmostEqual(ey, 120.0, places=9)

    def test_tilt_raises_the_build_height(self):
        self.assertAlmostEqual(
            build_height_mm(BBOX, 30.0, 0.0), 40.0 * 0.5 + 30.0 * math.cos(math.radians(30.0)),
            places=9,
        )

    def test_standing_the_part_up_uses_its_length(self):
        self.assertAlmostEqual(build_height_mm(BBOX, 90.0, 90.0), 120.0, places=9)

    def test_bonded_span_is_the_longer_plane_extent(self):
        self.assertAlmostEqual(bonded_span_mm(BBOX, 0.0, 0.0), 120.0, places=9)

    def test_standing_the_part_up_shrinks_the_bonded_span(self):
        self.assertAlmostEqual(bonded_span_mm(BBOX, 90.0, 90.0), 40.0, places=9)


class FacetTests(unittest.TestCase):
    def test_flat_underside_lies_on_the_plate(self):
        self.assertAlmostEqual(facet_inclination_deg((0.0, 0.0, -1.0), 0.0, 0.0), 0.0, places=9)

    def test_vertical_wall_is_upright(self):
        self.assertAlmostEqual(facet_inclination_deg((0.0, -1.0, 0.0), 0.0, 0.0), 90.0, places=9)

    def test_chamfer_sits_on_the_self_supporting_angle(self):
        self.assertAlmostEqual(
            facet_inclination_deg((0.0, -DIAGONAL, -DIAGONAL), 0.0, 0.0), 45.0, places=9
        )

    def test_only_the_underside_needs_support_when_flat(self):
        found = unsupported_facets(FACETS, 0.0, 0.0)
        self.assertEqual([record["facet"] for record in found], ["under"])

    def test_support_area_is_the_sum_of_those_facets(self):
        self.assertAlmostEqual(unsupported_area_mm2(FACETS, 0.0, 0.0), 400.0, places=9)

    def test_facet_exactly_on_the_angle_is_self_supporting(self):
        self.assertNotIn("chamfer", [r["facet"] for r in unsupported_facets(FACETS, 0.0, 0.0)])

    def test_tilting_drops_the_chamfer_below_the_angle(self):
        found = unsupported_facets(FACETS, 30.0, 0.0)
        chamfer = [record for record in found if record["facet"] == "chamfer"]
        self.assertEqual(len(chamfer), 1)
        self.assertAlmostEqual(chamfer[0]["inclination_deg"], 15.0, places=9)
        self.assertTrue(chamfer[0]["critical"])

    def test_up_facing_surfaces_never_need_support(self):
        self.assertNotIn("top", [r["facet"] for r in unsupported_facets(FACETS, 0.0, 0.0)])

    def test_empty_facet_list_rejected(self):
        with self.assertRaises(ValueError):
            unsupported_facets([], 0.0, 0.0)

    def test_facet_without_area_rejected(self):
        with self.assertRaises(ValueError):
            unsupported_facets([{"normal": (0.0, 0.0, -1.0)}], 0.0, 0.0)

    def test_self_support_angle_outside_quadrant_rejected(self):
        with self.assertRaises(ValueError):
            unsupported_facets(FACETS, 0.0, 0.0, 120.0)


class AxisAndStressTests(unittest.TestCase):
    def test_in_plane_axis_is_square_to_the_build_direction(self):
        self.assertAlmostEqual(critical_axis_angle_deg((1.0, 0.0, 0.0), 0.0, 0.0), 90.0, places=9)

    def test_standing_the_part_up_aligns_the_axis_with_the_build(self):
        self.assertAlmostEqual(critical_axis_angle_deg((1.0, 0.0, 0.0), 90.0, 90.0), 0.0, places=9)

    def test_stress_index_closed_form(self):
        self.assertAlmostEqual(residual_stress_index(120.0, 30.0, 100.0, 100.0), 1.56, places=9)

    def test_taller_build_raises_the_stress_index(self):
        low = residual_stress_index(120.0, 30.0, 100.0, 100.0)
        high = residual_stress_index(120.0, 90.0, 100.0, 100.0)
        self.assertAlmostEqual(high - low, 1.2 * 0.6, places=9)

    def test_zero_span_rejected(self):
        with self.assertRaises(ValueError):
            residual_stress_index(0.0, 30.0, 100.0, 100.0)

    def test_long_axis_follows_the_plate_rotation(self):
        self.assertAlmostEqual(long_axis_deg(BBOX, 90.0), 90.0, places=9)

    def test_long_axis_turns_with_a_deep_part(self):
        self.assertAlmostEqual(long_axis_deg((40.0, 120.0, 30.0), 0.0), 90.0, places=9)

    def test_edge_square_to_the_blade_is_the_safe_case(self):
        self.assertAlmostEqual(blade_skew_deg(0.0, 90.0), 90.0, places=9)

    def test_edge_along_the_blade_has_no_skew(self):
        self.assertAlmostEqual(blade_skew_deg(90.0, 90.0), 0.0, places=9)

    def test_skew_wraps_at_a_half_turn(self):
        self.assertAlmostEqual(blade_skew_deg(170.0, 10.0), 20.0, places=9)


class SelectionTests(unittest.TestCase):
    def test_candidate_record_carries_every_measure(self):
        record = evaluate_candidate(CANDIDATES[0], spec())
        self.assertAlmostEqual(record["support_area_mm2"], 400.0, places=9)
        self.assertAlmostEqual(record["build_height_mm"], 30.0, places=9)
        self.assertAlmostEqual(record["blade_skew_deg"], 90.0, places=9)

    def test_score_is_the_weighted_sum(self):
        record = evaluate_candidate(CANDIDATES[0], spec())
        self.assertAlmostEqual(score_candidate(record, spec()), 0.4 + 0.3 + 1.56, places=9)

    def test_negative_weight_rejected(self):
        record = evaluate_candidate(CANDIDATES[0], spec())
        with self.assertRaises(ValueError):
            score_candidate(record, spec(weights={"support": -1.0}))

    def test_equal_scores_break_towards_the_first_identifier(self):
        result = assess_placement(spec())
        self.assertEqual(result["selected"]["id"], "flat")

    def test_support_on_a_critical_surface_rejects_the_candidate(self):
        result = assess_placement(
            spec(candidates=[{"id": "tilt-30", "tilt_deg": 30.0, "rotation_deg": 0.0}])
        )
        self.assertIsNone(result["selected"])
        self.assertTrue(any("marked critical" in v
                            for entry in result["rejected"] for v in entry["violations"]))

    def test_axis_aligned_with_the_build_rejects_the_candidate(self):
        result = assess_placement(
            spec(candidates=[{"id": "upright", "tilt_deg": 90.0, "rotation_deg": 90.0}])
        )
        self.assertIsNone(result["selected"])
        self.assertTrue(any("critical axis" in v
                            for entry in result["rejected"] for v in entry["violations"]))

    def test_part_taller_than_the_envelope_rejects_the_candidate(self):
        result = assess_placement(
            spec(candidates=[{"id": "upright", "tilt_deg": 90.0, "rotation_deg": 90.0}],
                 envelope_height_mm=50.0, min_critical_axis_angle_deg=0.0)
        )
        self.assertIsNone(result["selected"])
        self.assertTrue(any("envelope" in v
                            for entry in result["rejected"] for v in entry["violations"]))

    def test_upright_candidate_survives_when_the_axis_limit_allows_it(self):
        result = assess_placement(
            spec(candidates=[{"id": "upright", "tilt_deg": 90.0, "rotation_deg": 90.0}],
                 min_critical_axis_angle_deg=0.0)
        )
        self.assertEqual(result["selected"]["id"], "upright")

    def test_no_feasible_candidate_is_reported(self):
        result = assess_placement(
            spec(candidates=[{"id": "tilt-30", "tilt_deg": 30.0, "rotation_deg": 0.0}])
        )
        self.assertFalse(result["placeable"])
        self.assertIn("no candidate orientation satisfies the hard constraints",
                      result["findings"])

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            select_orientation([], spec())


class AssessmentTests(unittest.TestCase):
    def test_selected_orientation_reports_its_support_burden(self):
        result = assess_placement(spec())
        self.assertTrue(result["placeable"])
        self.assertTrue(any("needs support" in f for f in result["findings"]))

    def test_blade_skew_finding_raised_for_an_edge_along_the_blade(self):
        result = assess_placement(spec(candidates=[CANDIDATES[1]]))
        self.assertEqual(result["selected"]["id"], "rot-90")
        self.assertTrue(any("recoater blade line" in f for f in result["findings"]))

    def test_safe_skew_raises_no_blade_finding(self):
        result = assess_placement(spec(candidates=[CANDIDATES[0]]))
        self.assertFalse(any("recoater blade line" in f for f in result["findings"]))

    def test_duplicate_candidate_id_rejected(self):
        duplicated = [CANDIDATES[0], dict(CANDIDATES[1], id="flat")]
        with self.assertRaises(ValueError):
            assess_placement(spec(candidates=duplicated))

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_placement(spec(candidates=[]))

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["critical_axis"]
        with self.assertRaises(ValueError):
            assess_placement(broken)

    def test_every_candidate_is_recorded(self):
        result = assess_placement(spec())
        self.assertEqual([record["id"] for record in result["records"]], ["flat", "rot-90"])


if __name__ == "__main__":
    unittest.main(verbosity=1)

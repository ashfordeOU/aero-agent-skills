#!/usr/bin/env python3
"""Contract test for the coverglass flatness or bow leaf (offline)."""

import copy
import unittest

from e2008_coverglass_flatness_or_bow_logic import (
    FLATNESS_ACCEPTED,
    FLATNESS_NOT_ACCEPTED,
    MIN_GRID_POINTS,
    MIN_REFERENCE_FLAT_RATIO,
    MIN_RESOLUTION_RATIO,
    MIN_SPAN_COVERAGE,
    SHAPE_BOW,
    SHAPE_WAVINESS,
    SHAPE_WITHIN_NOISE,
    assess_flatness,
    best_fit_plane,
    deflection_per_span,
    departure_shape,
    fringe_deflection_um,
    grid_reaches_the_rim,
    grid_span_mm,
    maximum_deflection_um,
    missing_evidence,
    normalized_points,
    peak_to_valley_um,
    plane_residuals_um,
    reference_flat_adequate,
    resolution_adequate,
)

SPAN_MM = 40.0
AXIS = (0.0, 20.0, 40.0)


def _dome_grid(centre_um=0.0, rim_um=6.0):
    """Nine points on a paraboloid: the rim sits high, the middle low."""
    corner_radius_squared = 2.0 * 20.0 ** 2
    points = []
    for x in AXIS:
        for y in AXIS:
            radius_squared = (x - 20.0) ** 2 + (y - 20.0) ** 2
            points.append(
                {
                    "x_mm": x,
                    "y_mm": y,
                    "height_um": centre_um
                    + rim_um * radius_squared / corner_radius_squared,
                }
            )
    return tuple(points)


def _dish_grid(rim_um=6.0):
    """Nine points on the inverted paraboloid: the middle sits high."""
    return tuple(
        {
            "x_mm": point["x_mm"],
            "y_mm": point["y_mm"],
            "height_um": rim_um - point["height_um"],
        }
        for point in _dome_grid(rim_um=rim_um)
    )


def _wavy_grid():
    """Nine points alternating either side of the mean height."""
    heights = (6.0, 2.0, 6.0, 2.0, 6.0, 2.0, 6.0, 2.0, 6.0)
    points = []
    index = 0
    for x in AXIS:
        for y in AXIS:
            points.append({"x_mm": x, "y_mm": y, "height_um": heights[index]})
            index += 1
    return tuple(points)


def _tilted_grid():
    """Nine points on a perfect plane, tilted on the datum."""
    return tuple(
        {"x_mm": x, "y_mm": y, "height_um": 1.0 + 0.05 * x + 0.02 * y}
        for x in AXIS
        for y in AXIS
    )


BASE_CASE = {
    "grid_points": _dome_grid(),
    "specimen_span_mm": SPAN_MM,
    "deflection_limit_um": 10.0,
    "instrument_resolution_um": 0.1,
    "reference_flatness_um": 0.5,
    "clamped": False,
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class FringeTests(unittest.TestCase):
    def test_one_fringe_is_half_a_wavelength_of_gap(self):
        self.assertAlmostEqual(fringe_deflection_um(1.0, 632.8), 0.3164, places=9)

    def test_no_fringes_means_no_gap(self):
        self.assertAlmostEqual(fringe_deflection_um(0.0, 632.8), 0.0, places=12)

    def test_the_gap_scales_with_the_fringe_count(self):
        self.assertAlmostEqual(
            fringe_deflection_um(8.0, 546.1),
            8.0 * fringe_deflection_um(1.0, 546.1),
            places=12,
        )

    def test_a_negative_fringe_count_is_refused(self):
        with self.assertRaises(ValueError):
            fringe_deflection_um(-2.0, 632.8)

    def test_a_zero_wavelength_is_refused(self):
        with self.assertRaises(ValueError):
            fringe_deflection_um(4.0, 0.0)


class GridTests(unittest.TestCase):
    def test_a_mapping_grid_and_a_triple_grid_reduce_alike(self):
        mapping = _dome_grid()
        triples = tuple(
            (point["x_mm"], point["y_mm"], point["height_um"]) for point in mapping
        )
        self.assertEqual(normalized_points(mapping), normalized_points(triples))

    def test_the_grid_span_is_its_bounding_box(self):
        self.assertEqual(grid_span_mm(_dome_grid()), (40.0, 40.0))

    def test_a_full_grid_reaches_the_rim(self):
        self.assertTrue(grid_reaches_the_rim(_dome_grid(), SPAN_MM))

    def test_a_grid_landing_on_the_coverage_share_still_reaches(self):
        reach = MIN_SPAN_COVERAGE * SPAN_MM
        centred = tuple(
            {"x_mm": x, "y_mm": y, "height_um": 3.0}
            for x in (0.0, reach / 2.0, reach)
            for y in (0.0, reach / 2.0, reach)
        )
        self.assertTrue(grid_reaches_the_rim(centred, SPAN_MM))

    def test_a_grid_that_samples_only_the_middle_does_not_reach(self):
        middle = tuple(
            {"x_mm": x, "y_mm": y, "height_um": 3.0}
            for x in (15.0, 20.0, 25.0)
            for y in (15.0, 20.0, 25.0)
        )
        self.assertFalse(grid_reaches_the_rim(middle, SPAN_MM))

    def test_an_empty_grid_is_refused(self):
        with self.assertRaises(ValueError):
            normalized_points(())

    def test_a_negative_gap_height_is_refused(self):
        with self.assertRaises(ValueError):
            normalized_points(({"x_mm": 0.0, "y_mm": 0.0, "height_um": -1.0},))

    def test_a_two_element_point_is_refused(self):
        with self.assertRaises(ValueError):
            normalized_points(((0.0, 0.0),))


class DeflectionTests(unittest.TestCase):
    def test_the_maximum_deflection_is_the_largest_gap(self):
        self.assertAlmostEqual(maximum_deflection_um(_dome_grid()), 6.0, places=12)

    def test_the_peak_to_valley_spans_the_whole_map(self):
        self.assertAlmostEqual(peak_to_valley_um(_dome_grid()), 6.0, places=12)

    def test_an_offset_map_keeps_its_spread_but_not_its_maximum(self):
        raised = _dome_grid(centre_um=2.0)
        self.assertAlmostEqual(maximum_deflection_um(raised), 8.0, places=12)
        self.assertAlmostEqual(peak_to_valley_um(raised), 6.0, places=12)

    def test_the_span_normalised_deflection_is_micrometres_per_millimetre(self):
        self.assertAlmostEqual(deflection_per_span(6.0, SPAN_MM), 0.15, places=12)

    def test_a_zero_span_cannot_normalise_a_deflection(self):
        with self.assertRaises(ValueError):
            deflection_per_span(6.0, 0.0)


class PlaneTests(unittest.TestCase):
    def test_a_tilted_plane_is_recovered_exactly(self):
        a, b, c = best_fit_plane(_tilted_grid())
        self.assertAlmostEqual(a, 0.05, places=9)
        self.assertAlmostEqual(b, 0.02, places=9)
        self.assertAlmostEqual(c, 1.0, places=9)

    def test_removing_the_plane_leaves_a_tilted_flat_article_with_nothing(self):
        for residual in plane_residuals_um(_tilted_grid()):
            self.assertAlmostEqual(residual, 0.0, places=9)

    def test_collinear_points_determine_no_plane(self):
        line = tuple(
            {"x_mm": x, "y_mm": 0.0, "height_um": 1.0 + 0.1 * x}
            for x in (0.0, 10.0, 20.0, 30.0)
        )
        with self.assertRaises(ValueError):
            best_fit_plane(line)

    def test_two_points_cannot_determine_a_plane(self):
        with self.assertRaises(ValueError):
            best_fit_plane(
                (
                    {"x_mm": 0.0, "y_mm": 0.0, "height_um": 1.0},
                    {"x_mm": 1.0, "y_mm": 1.0, "height_um": 2.0},
                )
            )

    def test_a_dome_leaves_a_real_residual_after_the_plane_comes_out(self):
        residuals = plane_residuals_um(_dome_grid())
        self.assertGreater(max(residuals) - min(residuals), 1.0)


class ShapeTests(unittest.TestCase):
    def test_a_dome_is_a_bow(self):
        self.assertEqual(departure_shape(_dome_grid()), SHAPE_BOW)

    def test_a_dish_is_a_bow_too(self):
        self.assertEqual(departure_shape(_dish_grid()), SHAPE_BOW)

    def test_a_dome_straddles_zero_once_the_plane_comes_out(self):
        residuals = plane_residuals_um(_dome_grid())
        self.assertGreater(max(residuals), 0.0)
        self.assertLess(min(residuals), 0.0)

    def test_an_alternating_map_is_waviness(self):
        self.assertEqual(departure_shape(_wavy_grid()), SHAPE_WAVINESS)

    def test_a_tilted_flat_article_has_no_departure_shape(self):
        self.assertEqual(departure_shape(_tilted_grid()), SHAPE_WITHIN_NOISE)

    def test_an_empty_map_is_refused(self):
        with self.assertRaises(ValueError):
            departure_shape(())

    def test_a_two_point_map_cannot_carry_a_shape(self):
        with self.assertRaises(ValueError):
            departure_shape(
                (
                    {"x_mm": 0.0, "y_mm": 0.0, "height_um": 1.0},
                    {"x_mm": 1.0, "y_mm": 1.0, "height_um": 2.0},
                )
            )

    def test_a_non_numeric_height_is_refused(self):
        with self.assertRaises(ValueError):
            departure_shape(
                ({"x_mm": 0.0, "y_mm": 0.0, "height_um": "flat"},) * 3
            )


class MarginTests(unittest.TestCase):
    def test_a_departure_well_above_the_probe_resolution_is_adequate(self):
        self.assertTrue(resolution_adequate(6.0, 0.1))

    def test_a_departure_landing_on_the_resolution_ratio_is_adequate(self):
        self.assertTrue(resolution_adequate(MIN_RESOLUTION_RATIO * 0.1, 0.1))

    def test_a_departure_near_the_probe_resolution_is_not_adequate(self):
        self.assertFalse(resolution_adequate(0.3, 0.1))

    def test_a_datum_much_flatter_than_the_article_is_adequate(self):
        self.assertTrue(reference_flat_adequate(6.0, 0.5))

    def test_a_datum_landing_on_the_ratio_is_adequate(self):
        self.assertTrue(
            reference_flat_adequate(MIN_REFERENCE_FLAT_RATIO * 0.5, 0.5)
        )

    def test_a_datum_as_rough_as_the_article_is_not_adequate(self):
        self.assertFalse(reference_flat_adequate(6.0, 5.0))

    def test_a_zero_resolution_probe_is_refused(self):
        with self.assertRaises(ValueError):
            resolution_adequate(6.0, 0.0)


class EvidenceTests(unittest.TestCase):
    def test_a_complete_record_is_missing_nothing(self):
        self.assertEqual(missing_evidence(BASE_CASE), ())

    def test_a_record_without_a_limit_is_incomplete(self):
        case = _case()
        del case["deflection_limit_um"]
        self.assertEqual(missing_evidence(case), ("deflection_limit_um",))

    def test_missing_evidence_stops_the_assessment(self):
        case = _case()
        del case["reference_flatness_um"]
        with self.assertRaises(ValueError):
            assess_flatness(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_flatness("dome")


class AssessmentTests(unittest.TestCase):
    def test_a_sound_record_is_accepted(self):
        result = assess_flatness(BASE_CASE)
        self.assertEqual(result["verdict"], FLATNESS_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_the_reported_maximum_is_the_largest_measured_gap(self):
        result = assess_flatness(BASE_CASE)
        self.assertAlmostEqual(result["maximum_deflection_um"], 6.0, places=12)

    def test_the_shape_is_reported_beside_the_maximum(self):
        self.assertEqual(assess_flatness(BASE_CASE)["departure_shape"], SHAPE_BOW)
        wavy = assess_flatness(_case(grid_points=_wavy_grid()))
        self.assertEqual(wavy["departure_shape"], SHAPE_WAVINESS)

    def test_a_clamped_article_is_a_finding(self):
        result = assess_flatness(_case(clamped=True))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertTrue(any("clamped" in f for f in result["findings"]))

    def test_a_sparse_grid_is_a_finding(self):
        sparse = _dome_grid()[:4]
        result = assess_flatness(_case(grid_points=sparse))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertTrue(any("departure map carries" in f for f in result["findings"]))
        self.assertLess(result["grid_point_count"], MIN_GRID_POINTS)

    def test_a_grid_that_never_reached_the_rim_is_a_finding(self):
        middle = tuple(
            {"x_mm": x, "y_mm": y, "height_um": 6.0}
            for x in (15.0, 20.0, 25.0)
            for y in (15.0, 20.0, 25.0)
        )
        result = assess_flatness(_case(grid_points=middle))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertTrue(any("largest at the rim" in f for f in result["findings"]))

    def test_a_coarse_probe_is_a_finding(self):
        result = assess_flatness(_case(instrument_resolution_um=2.0))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertTrue(any("probe" in f for f in result["findings"]))

    def test_a_rough_reference_flat_is_a_finding(self):
        result = assess_flatness(_case(reference_flatness_um=4.0))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertTrue(any("datum" in f for f in result["findings"]))

    def test_a_deflection_over_the_drawing_limit_is_a_finding(self):
        result = assess_flatness(_case(deflection_limit_um=3.0))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertTrue(any("drawing allows" in f for f in result["findings"]))

    def test_a_deflection_landing_on_the_drawing_limit_is_accepted(self):
        result = assess_flatness(_case(deflection_limit_um=6.0))
        self.assertEqual(result["verdict"], FLATNESS_ACCEPTED)

    def test_a_tilted_but_flat_article_carries_no_residual_shape(self):
        result = assess_flatness(
            _case(grid_points=_tilted_grid(), deflection_limit_um=10.0)
        )
        self.assertEqual(result["departure_shape"], SHAPE_WITHIN_NOISE)
        self.assertAlmostEqual(result["residual_peak_to_valley_um"], 0.0, places=9)

    def test_several_defects_are_all_reported_not_just_the_first(self):
        result = assess_flatness(
            _case(clamped=True, deflection_limit_um=1.0, reference_flatness_um=5.0)
        )
        self.assertEqual(result["verdict"], FLATNESS_NOT_ACCEPTED)
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()

"""Contract tests for the clause 7.5.19 bare-cell flatness test.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a grid that never reached
the whole face, a datum that has to absorb fixture tilt before any
deviation is read, the shape the residuals describe, and a deviation taken
against the tighter of the two declared allowances.
"""

import math
import unittest

from e2008_bare_cell_flatness_test_logic import (
    ABSOLUTE_ALLOWANCE,
    CELL_EXCEEDS_FLATNESS_LIMIT,
    CELL_REFERRED_FOR_REVIEW,
    CELL_WITHIN_FLATNESS_LIMIT,
    CONCAVE,
    CONVEX,
    DEFAULT_FLATNESS_CRITERIA,
    DIAGONAL_SHARE_ALLOWANCE,
    FLATNESS_NOT_ESTABLISHED,
    IRREGULAR,
    assess_bare_cell_flatness,
    bow_direction,
    fit_reference_plane,
    governing_flatness_limit_um,
    grid_coverage,
    plane_tilt_um,
    residual_profile,
    validate_cell_outline,
    validate_flatness_criteria,
    validate_height_grid,
)

LENGTH_MM = 40.0
WIDTH_MM = 80.0
XS = (0.0, 20.0, 40.0)
YS = (0.0, 40.0, 80.0)


def _criteria(**overrides):
    criteria = dict(DEFAULT_FLATNESS_CRITERIA)
    criteria.update(overrides)
    return criteria


def _outline(**overrides):
    outline = {"length_mm": LENGTH_MM, "width_mm": WIDTH_MM, "thickness_um": 150.0}
    outline.update(overrides)
    return outline


def _grid(centre_um=0.0, tilt_x=0.0, tilt_y=0.0):
    """Nine stations over the whole face, with an optional centre bump."""
    points = []
    for x in XS:
        for y in YS:
            height = tilt_x * x + tilt_y * y
            if x == XS[1] and y == YS[1]:
                height += centre_um
            points.append({"x_mm": x, "y_mm": y, "height_um": height})
    return points


def _case(**overrides):
    case = {
        "cell_id": "bc-flat-01",
        "outline": _outline(),
        "height_grid": _grid(),
        "measurement_method": "non-contact profilometer, cell free on three supports",
    }
    case.update(overrides)
    return case


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_flatness_criteria(DEFAULT_FLATNESS_CRITERIA),
            DEFAULT_FLATNESS_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_flatness_criteria("max_flatness_deviation_mm")

    def test_a_span_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_flatness_criteria(_criteria(min_span_fraction=1.4))

    def test_a_review_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_flatness_criteria(_criteria(flatness_review_factor=0.8))

    def test_a_grid_point_floor_below_three_rejected(self):
        with self.assertRaises(ValueError):
            validate_flatness_criteria(_criteria(min_grid_points=2))

    def test_a_non_boolean_quadrant_rule_rejected(self):
        with self.assertRaises(ValueError):
            validate_flatness_criteria(_criteria(require_all_quadrants="yes"))


class OutlineTests(unittest.TestCase):
    def test_the_diagonal_is_derived_from_the_outline(self):
        resolved = validate_cell_outline(_outline())
        self.assertAlmostEqual(
            resolved["diagonal_mm"], math.hypot(LENGTH_MM, WIDTH_MM), places=9
        )

    def test_a_zero_length_outline_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_outline(_outline(length_mm=0.0))

    def test_a_non_mapping_outline_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_outline("40 by 80")


class GridValidationTests(unittest.TestCase):
    def test_a_full_grid_is_read_back(self):
        readings = validate_height_grid(_grid(), _outline())
        self.assertEqual(len(readings), 9)

    def test_an_empty_grid_rejected(self):
        with self.assertRaises(ValueError):
            validate_height_grid([], _outline())

    def test_a_station_off_the_cell_rejected(self):
        with self.assertRaises(ValueError):
            validate_height_grid(
                [{"x_mm": 50.0, "y_mm": 10.0, "height_um": 0.0}], _outline()
            )

    def test_a_repeated_station_rejected(self):
        points = _grid()
        points.append({"x_mm": 0.0, "y_mm": 0.0, "height_um": 12.0})
        with self.assertRaises(ValueError):
            validate_height_grid(points, _outline())

    def test_a_non_finite_height_rejected(self):
        points = _grid()
        points[0]["height_um"] = float("nan")
        with self.assertRaises(ValueError):
            validate_height_grid(points, _outline())


class CoverageTests(unittest.TestCase):
    def test_a_full_face_grid_covers_the_cell(self):
        coverage = grid_coverage(_grid(), _outline())
        self.assertTrue(coverage["full_area"])
        self.assertEqual(coverage["quadrants_sampled"], 4)
        self.assertAlmostEqual(coverage["span_x_fraction"], 1.0, places=12)

    def test_too_few_stations_is_a_coverage_gap(self):
        points = [
            {"x_mm": 0.0, "y_mm": 0.0, "height_um": 0.0},
            {"x_mm": 40.0, "y_mm": 0.0, "height_um": 0.0},
            {"x_mm": 0.0, "y_mm": 80.0, "height_um": 0.0},
            {"x_mm": 40.0, "y_mm": 80.0, "height_um": 0.0},
        ]
        coverage = grid_coverage(points, _outline())
        self.assertFalse(coverage["full_area"])
        self.assertEqual(coverage["reading_count"], 4)

    def test_a_grid_short_in_one_direction_is_a_coverage_gap(self):
        points = []
        for x in (0.0, 10.0, 20.0):
            for y in YS:
                points.append({"x_mm": x, "y_mm": y, "height_um": 0.0})
        coverage = grid_coverage(points, _outline())
        self.assertFalse(coverage["full_area"])
        self.assertAlmostEqual(coverage["span_x_fraction"], 0.5, places=12)

    def test_an_unsampled_quadrant_is_a_coverage_gap(self):
        points = []
        for x in XS:
            for y in (0.0, 10.0, 20.0):
                points.append({"x_mm": x, "y_mm": y, "height_um": 0.0})
        coverage = grid_coverage(points, _outline())
        self.assertEqual(coverage["quadrants_sampled"], 2)
        self.assertFalse(coverage["full_area"])


class PlaneTests(unittest.TestCase):
    def test_a_flat_cell_leaves_no_residual(self):
        plane = fit_reference_plane(_grid(), _outline())
        profile = residual_profile(plane)
        self.assertAlmostEqual(profile["peak_to_valley_um"], 0.0, places=9)

    def test_a_tilted_but_flat_cell_is_still_flat(self):
        plane = fit_reference_plane(_grid(tilt_x=3.0, tilt_y=2.0), _outline())
        profile = residual_profile(plane)
        self.assertAlmostEqual(profile["peak_to_valley_um"], 0.0, places=6)
        self.assertAlmostEqual(plane["slope_x_um_per_mm"], 3.0, places=9)

    def test_the_fixture_tilt_is_reported_rather_than_hidden(self):
        plane = fit_reference_plane(_grid(tilt_x=3.0, tilt_y=2.0), _outline())
        self.assertAlmostEqual(
            plane_tilt_um(plane, _outline()),
            math.hypot(3.0, 2.0) * math.hypot(LENGTH_MM, WIDTH_MM),
            places=6,
        )

    def test_the_deviation_does_not_move_when_the_cell_is_tilted(self):
        level = residual_profile(fit_reference_plane(_grid(60.0), _outline()))
        tilted = residual_profile(
            fit_reference_plane(_grid(60.0, tilt_x=3.0, tilt_y=2.0), _outline())
        )
        self.assertAlmostEqual(
            level["peak_to_valley_um"], tilted["peak_to_valley_um"], places=6
        )

    def test_a_bump_shows_as_a_one_sided_residual(self):
        profile = residual_profile(fit_reference_plane(_grid(60.0), _outline()))
        self.assertAlmostEqual(profile["peak_to_valley_um"], 60.0, places=9)
        self.assertGreater(profile["max_above_um"], 0.0)
        self.assertLess(profile["max_below_um"], 0.0)

    def test_collinear_stations_determine_no_plane(self):
        points = [
            {"x_mm": 0.0, "y_mm": 0.0, "height_um": 0.0},
            {"x_mm": 20.0, "y_mm": 0.0, "height_um": 1.0},
            {"x_mm": 40.0, "y_mm": 0.0, "height_um": 2.0},
        ]
        with self.assertRaises(ValueError):
            fit_reference_plane(points, _outline())

    def test_two_stations_are_not_a_plane(self):
        points = [
            {"x_mm": 0.0, "y_mm": 0.0, "height_um": 0.0},
            {"x_mm": 40.0, "y_mm": 80.0, "height_um": 2.0},
        ]
        with self.assertRaises(ValueError):
            fit_reference_plane(points, _outline())


class ShapeTests(unittest.TestCase):
    def test_a_raised_centre_reads_as_convex(self):
        plane = fit_reference_plane(_grid(60.0), _outline())
        self.assertEqual(bow_direction(plane, _outline())["shape"], CONVEX)

    def test_a_sunken_centre_reads_as_concave(self):
        plane = fit_reference_plane(_grid(-60.0), _outline())
        self.assertEqual(bow_direction(plane, _outline())["shape"], CONCAVE)

    def test_a_bow_below_the_signature_band_is_not_named(self):
        plane = fit_reference_plane(_grid(60.0), _outline())
        shape = bow_direction(plane, _outline(), _criteria(bow_signature_fraction=0.9))
        self.assertEqual(shape["shape"], IRREGULAR)

    def test_a_grid_that_never_reached_the_middle_names_no_shape(self):
        points = [
            {"x_mm": 0.0, "y_mm": 0.0, "height_um": 0.0},
            {"x_mm": 40.0, "y_mm": 0.0, "height_um": 4.0},
            {"x_mm": 0.0, "y_mm": 80.0, "height_um": 6.0},
            {"x_mm": 40.0, "y_mm": 80.0, "height_um": 1.0},
            {"x_mm": 20.0, "y_mm": 0.0, "height_um": 9.0},
            {"x_mm": 20.0, "y_mm": 80.0, "height_um": 3.0},
        ]
        shape = bow_direction(fit_reference_plane(points, _outline()), _outline())
        self.assertEqual(shape["shape"], IRREGULAR)
        self.assertEqual(shape["inner_station_count"], 0)


class LimitTests(unittest.TestCase):
    def test_the_diagonal_share_governs_a_small_cell(self):
        limit = governing_flatness_limit_um(_outline())
        self.assertEqual(limit["source"], DIAGONAL_SHARE_ALLOWANCE)
        self.assertAlmostEqual(
            limit["limit_um"], 1.2 * math.hypot(LENGTH_MM, WIDTH_MM), places=9
        )

    def test_the_absolute_allowance_governs_a_large_cell(self):
        limit = governing_flatness_limit_um(_outline(length_mm=80.0, width_mm=80.0))
        self.assertEqual(limit["source"], ABSOLUTE_ALLOWANCE)
        self.assertAlmostEqual(limit["limit_um"], 120.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_a_flat_cell_is_inside_its_limit(self):
        result = assess_bare_cell_flatness(_case())
        self.assertEqual(result["verdict"], CELL_WITHIN_FLATNESS_LIMIT)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["peak_to_valley_um"], 0.0, places=9)

    def test_a_moderate_bow_is_accepted_and_its_shape_named(self):
        result = assess_bare_cell_flatness(_case(height_grid=_grid(60.0)))
        self.assertEqual(result["verdict"], CELL_WITHIN_FLATNESS_LIMIT)
        self.assertEqual(result["shape"], CONVEX)
        self.assertGreater(result["margin_um"], 0.0)

    def test_a_cell_exactly_on_its_limit_is_admitted(self):
        limit = governing_flatness_limit_um(_outline())["limit_um"]
        result = assess_bare_cell_flatness(_case(height_grid=_grid(limit)))
        self.assertEqual(result["verdict"], CELL_WITHIN_FLATNESS_LIMIT)
        self.assertAlmostEqual(result["margin_um"], 0.0, places=9)

    def test_a_cell_past_the_limit_is_referred(self):
        result = assess_bare_cell_flatness(_case(height_grid=_grid(130.0)))
        self.assertEqual(result["verdict"], CELL_REFERRED_FOR_REVIEW)
        self.assertTrue(result["findings"])

    def test_a_badly_bowed_cell_exceeds_the_limit(self):
        result = assess_bare_cell_flatness(_case(height_grid=_grid(-400.0)))
        self.assertEqual(result["verdict"], CELL_EXCEEDS_FLATNESS_LIMIT)
        self.assertEqual(result["shape"], CONCAVE)

    def test_a_cell_grazing_its_limit_raises_an_advisory(self):
        result = assess_bare_cell_flatness(_case(height_grid=_grid(100.0)))
        self.assertEqual(result["verdict"], CELL_WITHIN_FLATNESS_LIMIT)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_advisory_does_not_move_the_verdict(self):
        result = assess_bare_cell_flatness(_case(height_grid=_grid(100.0)))
        self.assertEqual(result["verdict"], CELL_WITHIN_FLATNESS_LIMIT)
        self.assertLess(result["limit_used_fraction"], 1.0)

    def test_a_part_face_grid_establishes_no_flatness(self):
        points = []
        for x in (0.0, 10.0, 20.0):
            for y in (0.0, 20.0, 40.0):
                points.append({"x_mm": x, "y_mm": y, "height_um": 0.0})
        result = assess_bare_cell_flatness(_case(height_grid=points))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_missing_measurement_method_establishes_no_flatness(self):
        result = assess_bare_cell_flatness(_case(measurement_method="   "))
        self.assertEqual(result["verdict"], FLATNESS_NOT_ESTABLISHED)

    def test_the_governing_limit_travels_with_the_verdict(self):
        result = assess_bare_cell_flatness(_case())
        self.assertEqual(result["limit_source"], DIAGONAL_SHARE_ALLOWANCE)
        self.assertAlmostEqual(
            result["diagonal_mm"], math.hypot(LENGTH_MM, WIDTH_MM), places=9
        )

    def test_a_blank_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_flatness(_case(cell_id="  "))

    def test_a_missing_height_grid_rejected(self):
        case = _case()
        del case["height_grid"]
        with self.assertRaises(ValueError):
            assess_bare_cell_flatness(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_flatness(["cell_id"])


if __name__ == "__main__":
    unittest.main()

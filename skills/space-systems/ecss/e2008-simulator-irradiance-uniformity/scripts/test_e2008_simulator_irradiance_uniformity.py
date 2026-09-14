"""Contract tests for the clause 10.1.2 simulator irradiance uniformity check.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused policy, an
unnominated or unnamed test plane, a map too thin or too bunched to
support a figure, a point that fell off the plane, and a spread wider than
the measurement was quoted at.
"""

import unittest

from e2008_simulator_irradiance_uniformity_logic import (
    DEFAULT_UNIFORMITY_POLICY,
    OUTSIDE_DECLARED_BANDS,
    PLANE_SAMPLING_INSUFFICIENT,
    TEST_PLANE_NOT_DECLARED,
    UNIFORMITY_OUT_OF_LIMIT,
    UNIFORMITY_WITHIN_LIMIT,
    assess_irradiance_uniformity,
    extreme_points,
    mean_irradiance_w_m2,
    point_inside_plane,
    points_outside_plane,
    sample_points,
    sampled_coverage_fraction,
    sampling_findings,
    spatial_non_uniformity_percent,
    uniformity_category,
    validate_sample_point,
    validate_test_plane,
    validate_uniformity_policy,
)

PLANE_WIDTH_MM = 400.0
PLANE_HEIGHT_MM = 400.0

_GRID_READINGS = (
    1376.0,
    1379.0,
    1375.0,
    1380.0,
    1382.0,
    1378.0,
    1374.0,
    1377.0,
    1372.0,
)


def _policy(**overrides):
    policy = dict(DEFAULT_UNIFORMITY_POLICY)
    policy.update(overrides)
    return policy


def _plane(**overrides):
    plane = {
        "designation": "TP-3 simulator test plane",
        "width_mm": PLANE_WIDTH_MM,
        "height_mm": PLANE_HEIGHT_MM,
    }
    plane.update(overrides)
    return plane


def _grid(readings=_GRID_READINGS, span_mm=PLANE_WIDTH_MM):
    points = []
    coords = (0.0, span_mm / 2.0, span_mm)
    index = 0
    for y_mm in coords:
        for x_mm in coords:
            points.append(
                {
                    "id": "p%02d" % (index + 1),
                    "x_mm": x_mm,
                    "y_mm": y_mm,
                    "irradiance_w_m2": readings[index],
                }
            )
            index += 1
    return points


def _case(**overrides):
    case = {"test_plane": _plane(), "sample_points": _grid()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_uniformity_policy(DEFAULT_UNIFORMITY_POLICY),
            DEFAULT_UNIFORMITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy("max_non_uniformity_percent")

    def test_a_hundred_per_cent_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(max_non_uniformity_percent=120.0))

    def test_a_three_point_sampling_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(min_sample_points=3))

    def test_a_boolean_sampling_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(min_sample_points=True))

    def test_coverage_above_the_whole_plane_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(_policy(min_coverage_fraction=1.4))

    def test_bands_out_of_order_rejected(self):
        with self.assertRaises(ValueError):
            validate_uniformity_policy(
                _policy(uniformity_bands_percent=(5.0, 2.0, 10.0))
            )


class TestPlaneTests(unittest.TestCase):
    def test_a_nominated_plane_validates(self):
        checked = validate_test_plane(_plane())
        self.assertEqual(checked["designation"], "TP-3 simulator test plane")
        self.assertAlmostEqual(checked["area_mm2"], 160000.0, places=9)

    def test_non_mapping_plane_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_plane("TP-3")

    def test_a_zero_width_plane_rejected(self):
        with self.assertRaises(ValueError):
            validate_test_plane(_plane(width_mm=0.0))

    def test_a_blank_designation_survives_validation(self):
        self.assertEqual(validate_test_plane(_plane(designation="  "))["designation"], "")


class SamplePointTests(unittest.TestCase):
    def test_a_point_is_read_back(self):
        checked = validate_sample_point(_grid()[4])
        self.assertEqual(checked["id"], "p05")
        self.assertAlmostEqual(checked["irradiance_w_m2"], 1382.0, places=9)

    def test_a_blank_point_id_rejected(self):
        point = _grid()[0]
        point["id"] = " "
        with self.assertRaises(ValueError):
            validate_sample_point(point)

    def test_a_negative_reading_rejected(self):
        point = _grid()[0]
        point["irradiance_w_m2"] = -1376.0
        with self.assertRaises(ValueError):
            validate_sample_point(point)

    def test_a_boolean_coordinate_rejected(self):
        point = _grid()[0]
        point["x_mm"] = True
        with self.assertRaises(ValueError):
            validate_sample_point(point)

    def test_a_duplicate_point_id_rejected(self):
        points = _grid()
        points[3]["id"] = "p01"
        with self.assertRaises(ValueError):
            sample_points(points)

    def test_an_empty_map_rejected(self):
        with self.assertRaises(ValueError):
            sample_points([])

    def test_a_point_on_the_plane_corner_is_inside(self):
        corner = {
            "id": "corner",
            "x_mm": PLANE_WIDTH_MM,
            "y_mm": PLANE_HEIGHT_MM,
            "irradiance_w_m2": 1376.0,
        }
        self.assertTrue(point_inside_plane(corner, _plane()))

    def test_a_point_beyond_the_plane_is_named(self):
        points = sample_points(_grid())
        stray = dict(points[0])
        stray["id"] = "stray"
        stray["x_mm"] = PLANE_WIDTH_MM + 25.0
        self.assertEqual(
            points_outside_plane(list(points) + [stray], _plane()), ("stray",)
        )


class UniformityFigureTests(unittest.TestCase):
    def test_the_spread_is_taken_extreme_to_extreme(self):
        points = sample_points(_grid())
        expected = (1382.0 - 1372.0) / (1382.0 + 1372.0) * 100.0
        self.assertAlmostEqual(
            spatial_non_uniformity_percent(points), expected, places=9
        )

    def test_a_perfectly_flat_plane_spreads_nothing(self):
        points = sample_points(_grid(readings=(1367.0,) * 9))
        self.assertAlmostEqual(
            spatial_non_uniformity_percent(points), 0.0, places=12
        )

    def test_a_two_per_cent_plane_reads_two_per_cent(self):
        readings = (980.0,) + (1000.0,) * 7 + (1020.0,)
        points = sample_points(_grid(readings=readings))
        self.assertAlmostEqual(
            spatial_non_uniformity_percent(points), 2.0, places=9
        )

    def test_a_scatter_figure_would_have_hidden_the_worst_pair(self):
        readings = (1000.0,) * 8 + (1120.0,)
        points = sample_points(_grid(readings=readings))
        self.assertGreater(spatial_non_uniformity_percent(points), 5.0)

    def test_the_brightest_and_dimmest_points_are_named(self):
        points = sample_points(_grid())
        brightest, dimmest = extreme_points(points)
        self.assertEqual(brightest, "p05")
        self.assertEqual(dimmest, "p09")

    def test_the_mean_is_reported_beside_the_spread(self):
        points = sample_points(_grid())
        self.assertAlmostEqual(
            mean_irradiance_w_m2(points), sum(_GRID_READINGS) / 9.0, places=9
        )

    def test_a_full_grid_covers_the_whole_plane(self):
        points = sample_points(_grid())
        self.assertAlmostEqual(
            sampled_coverage_fraction(points, _plane()), 1.0, places=9
        )

    def test_a_bunched_grid_covers_a_quarter(self):
        points = sample_points(_grid(span_mm=PLANE_WIDTH_MM / 2.0))
        self.assertAlmostEqual(
            sampled_coverage_fraction(points, _plane()), 0.25, places=9
        )

    def test_an_empty_sequence_has_no_spread_to_take(self):
        with self.assertRaises(ValueError):
            spatial_non_uniformity_percent([])


class CategoryTests(unittest.TestCase):
    def test_a_tight_plane_lands_in_the_first_band(self):
        self.assertEqual(uniformity_category(1.4), "band-1")

    def test_a_figure_exactly_on_a_band_edge_stays_in_that_band(self):
        self.assertEqual(uniformity_category(2.0), "band-1")

    def test_a_middling_plane_lands_in_the_second_band(self):
        self.assertEqual(uniformity_category(4.5), "band-2")

    def test_a_plane_wider_than_every_band_is_marked_outside(self):
        self.assertEqual(uniformity_category(14.0), OUTSIDE_DECLARED_BANDS)

    def test_a_negative_figure_rejected(self):
        with self.assertRaises(ValueError):
            uniformity_category(-1.0)


class SamplingFindingTests(unittest.TestCase):
    def test_a_full_grid_raises_no_sampling_finding(self):
        points = sample_points(_grid())
        self.assertEqual(sampling_findings(points, _plane()), ())

    def test_a_thin_map_is_named_as_thin(self):
        points = sample_points(_grid()[:5])
        findings = sampling_findings(points, _plane())
        self.assertTrue(any("sampling policy" in finding for finding in findings))

    def test_a_bunched_map_is_named_as_short_on_coverage(self):
        points = sample_points(_grid(span_mm=PLANE_WIDTH_MM / 2.0))
        findings = sampling_findings(points, _plane())
        self.assertTrue(any("span" in finding for finding in findings))


class AssessmentTests(unittest.TestCase):
    def test_a_uniform_plane_is_within_limit(self):
        result = assess_irradiance_uniformity(_case())
        self.assertEqual(result["verdict"], UNIFORMITY_WITHIN_LIMIT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["sample_count"], 9)

    def test_an_unnominated_plane_closes_the_assessment(self):
        case = _case()
        del case["test_plane"]
        result = assess_irradiance_uniformity(case)
        self.assertEqual(result["verdict"], TEST_PLANE_NOT_DECLARED)
        self.assertTrue(result["findings"])

    def test_an_unnamed_plane_closes_the_assessment(self):
        result = assess_irradiance_uniformity(
            _case(test_plane=_plane(designation="   "))
        )
        self.assertEqual(result["verdict"], TEST_PLANE_NOT_DECLARED)

    def test_a_thin_map_stops_before_a_figure_is_quoted(self):
        result = assess_irradiance_uniformity(_case(sample_points=_grid()[:6]))
        self.assertEqual(result["verdict"], PLANE_SAMPLING_INSUFFICIENT)
        self.assertIsNone(result["non_uniformity_percent"])

    def test_a_bunched_map_stops_before_a_figure_is_quoted(self):
        result = assess_irradiance_uniformity(
            _case(sample_points=_grid(span_mm=PLANE_WIDTH_MM / 2.0))
        )
        self.assertEqual(result["verdict"], PLANE_SAMPLING_INSUFFICIENT)

    def test_a_plane_over_the_limit_names_both_extreme_points(self):
        readings = (940.0,) + (1000.0,) * 7 + (1060.0,)
        result = assess_irradiance_uniformity(
            _case(sample_points=_grid(readings=readings))
        )
        self.assertEqual(result["verdict"], UNIFORMITY_OUT_OF_LIMIT)
        self.assertIn(result["brightest_point_id"], result["findings"][0])
        self.assertIn(result["dimmest_point_id"], result["findings"][0])

    def test_a_plane_exactly_on_the_limit_is_admitted(self):
        readings = (980.0,) + (1000.0,) * 7 + (1020.0,)
        result = assess_irradiance_uniformity(
            _case(sample_points=_grid(readings=readings))
        )
        self.assertEqual(result["verdict"], UNIFORMITY_WITHIN_LIMIT)
        self.assertAlmostEqual(result["non_uniformity_percent"], 2.0, places=9)

    def test_a_plane_grazing_the_limit_raises_an_advisory(self):
        readings = (982.0,) + (1000.0,) * 7 + (1018.0,)
        result = assess_irradiance_uniformity(
            _case(sample_points=_grid(readings=readings))
        )
        self.assertEqual(result["verdict"], UNIFORMITY_WITHIN_LIMIT)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_comfortable_plane_raises_no_advisory(self):
        result = assess_irradiance_uniformity(_case())
        self.assertEqual(result["advisories"], [])

    def test_the_band_travels_with_the_verdict(self):
        result = assess_irradiance_uniformity(_case())
        self.assertEqual(result["uniformity_band"], "band-1")

    def test_a_missing_point_set_rejected(self):
        case = _case()
        del case["sample_points"]
        with self.assertRaises(ValueError):
            assess_irradiance_uniformity(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_irradiance_uniformity(["test_plane"])


if __name__ == "__main__":
    unittest.main()

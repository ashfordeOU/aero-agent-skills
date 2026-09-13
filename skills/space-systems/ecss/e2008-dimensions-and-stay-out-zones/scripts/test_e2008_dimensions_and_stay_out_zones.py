#!/usr/bin/env python3
"""Contract test for coupon dimensions and stay-out zones (offline)."""

import copy
import math
import unittest

from e2008_dimensions_and_stay_out_zones_logic import (
    DIMENSION_ABOVE,
    DIMENSION_BELOW,
    DIMENSION_WITHIN,
    GEOMETRY_ACCEPTED,
    GEOMETRY_REJECTED,
    ZONE_CLEAR,
    ZONE_CLEARANCE_SHORT,
    ZONE_INTRUDED,
    check_coupon_dimensions,
    check_dimension,
    check_stay_out_zones,
    check_standoff_features,
    edge_margin_zones,
    inspect_coupon_geometry,
    intrusion_depth_mm,
    rectangle_clearance_mm,
    rectangle_overlap_area_mm2,
)

DIMENSION_SPEC = {
    "width": {"nominal_mm": 80.0, "plus_tolerance_mm": 0.2, "minus_tolerance_mm": 0.2},
    "height": {"nominal_mm": 60.0, "plus_tolerance_mm": 0.2, "minus_tolerance_mm": 0.2},
    "thickness": {"nominal_mm": 2.0, "plus_tolerance_mm": 0.1, "minus_tolerance_mm": 0.05},
}

MEASURED = {"width": 80.05, "height": 59.95, "thickness": 2.02}

HARNESS_CORRIDOR = {
    "id": "harness-corridor",
    "x_mm": 0.0,
    "y_mm": 25.0,
    "width_mm": 80.0,
    "height_mm": 6.0,
}

CLEAR_CELL = {"id": "cell-a1", "x_mm": 5.0, "y_mm": 5.0, "width_mm": 40.0, "height_mm": 15.0}
INTRUDING_CELL = {
    "id": "cell-b1",
    "x_mm": 5.0,
    "y_mm": 22.0,
    "width_mm": 40.0,
    "height_mm": 5.0,
}
TOUCHING_CELL = {
    "id": "cell-c1",
    "x_mm": 5.0,
    "y_mm": 20.0,
    "width_mm": 40.0,
    "height_mm": 5.0,
}

STANDOFF_HEIGHT_SPEC = {
    "nominal_mm": 3.0,
    "plus_tolerance_mm": 0.05,
    "minus_tolerance_mm": 0.05,
}

STANDOFF = {
    "id": "standoff-1",
    "height_mm": 3.02,
    "footprint": {"x_mm": 70.0, "y_mm": 5.0, "width_mm": 4.0, "height_mm": 4.0},
}


def _with(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


class DimensionTests(unittest.TestCase):
    def test_a_measurement_inside_the_band_is_within_tolerance(self):
        result = check_dimension("width", 80.0, 0.2, 0.2, 80.05)
        self.assertEqual(result["verdict"], DIMENSION_WITHIN)
        self.assertAlmostEqual(result["deviation_mm"], 0.05, places=9)
        self.assertAlmostEqual(result["utilisation"], 0.25, places=9)

    def test_a_measurement_exactly_on_the_upper_limit_is_within_tolerance(self):
        result = check_dimension("width", 80.0, 0.2, 0.2, 80.2)
        self.assertAlmostEqual(result["measured_mm"], result["upper_limit_mm"], places=9)
        self.assertAlmostEqual(result["utilisation"], 1.0, places=9)
        self.assertTrue(result["within_tolerance"])

    def test_a_measurement_exactly_on_the_lower_limit_is_within_tolerance(self):
        result = check_dimension("width", 80.0, 0.2, 0.2, 79.8)
        self.assertAlmostEqual(result["measured_mm"], result["lower_limit_mm"], places=9)
        self.assertTrue(result["within_tolerance"])

    def test_an_oversize_coupon_is_above_the_upper_limit(self):
        result = check_dimension("width", 80.0, 0.2, 0.2, 80.6)
        self.assertEqual(result["verdict"], DIMENSION_ABOVE)
        self.assertFalse(result["within_tolerance"])

    def test_an_undersize_coupon_is_below_the_lower_limit(self):
        result = check_dimension("width", 80.0, 0.2, 0.2, 79.1)
        self.assertEqual(result["verdict"], DIMENSION_BELOW)

    def test_an_asymmetric_band_uses_the_side_the_deviation_falls_on(self):
        result = check_dimension("thickness", 2.0, 0.1, 0.05, 1.975)
        self.assertAlmostEqual(result["utilisation"], 0.5, places=9)
        self.assertTrue(result["within_tolerance"])

    def test_a_measurement_on_the_nominal_uses_no_tolerance(self):
        result = check_dimension("width", 80.0, 0.2, 0.2, 80.0)
        self.assertAlmostEqual(result["utilisation"], 0.0, places=12)

    def test_a_dimension_with_no_tolerance_band_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("width", 80.0, 0.0, 0.0, 80.0)

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("width", 80.0, -0.2, 0.2, 80.0)

    def test_a_lower_limit_below_zero_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("thickness", 2.0, 0.1, 2.5, 2.0)

    def test_an_unnamed_dimension_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("", 80.0, 0.2, 0.2, 80.0)

    def test_a_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            check_dimension("width", 80.0, 0.2, 0.2, "80.05 mm")


class CouponDimensionTests(unittest.TestCase):
    def test_a_coupon_inside_every_band_passes(self):
        report = check_coupon_dimensions(DIMENSION_SPEC, MEASURED)
        self.assertTrue(report["within_tolerance"])
        self.assertEqual(report["out_of_tolerance"], [])
        self.assertEqual(report["findings"], [])

    def test_the_tightest_dimension_governs_and_ties_break_on_the_name(self):
        report = check_coupon_dimensions(DIMENSION_SPEC, MEASURED)
        self.assertEqual(report["governing_dimension"], "height")

    def test_one_bad_dimension_fails_the_coupon(self):
        report = check_coupon_dimensions(
            DIMENSION_SPEC, _with(MEASURED, thickness=2.3)
        )
        self.assertFalse(report["within_tolerance"])
        self.assertEqual(report["out_of_tolerance"], ["thickness"])
        self.assertEqual(report["governing_dimension"], "thickness")

    def test_a_dimension_never_measured_rejected(self):
        measured = copy.deepcopy(MEASURED)
        del measured["thickness"]
        with self.assertRaises(ValueError):
            check_coupon_dimensions(DIMENSION_SPEC, measured)

    def test_a_measurement_with_no_drawing_entry_rejected(self):
        with self.assertRaises(ValueError):
            check_coupon_dimensions(DIMENSION_SPEC, _with(MEASURED, diagonal=100.0))

    def test_an_empty_spec_rejected(self):
        with self.assertRaises(ValueError):
            check_coupon_dimensions({}, MEASURED)


class RectangleTests(unittest.TestCase):
    def test_disjoint_rectangles_share_no_area(self):
        self.assertAlmostEqual(
            rectangle_overlap_area_mm2(CLEAR_CELL, HARNESS_CORRIDOR), 0.0, places=12
        )

    def test_an_intruding_feature_shares_area_with_the_zone(self):
        self.assertAlmostEqual(
            rectangle_overlap_area_mm2(INTRUDING_CELL, HARNESS_CORRIDOR), 80.0, places=9
        )

    def test_touching_rectangles_share_no_area(self):
        self.assertAlmostEqual(
            rectangle_overlap_area_mm2(TOUCHING_CELL, HARNESS_CORRIDOR), 0.0, places=12
        )

    def test_clearance_is_the_axis_gap_when_the_offset_is_on_one_axis(self):
        self.assertAlmostEqual(
            rectangle_clearance_mm(CLEAR_CELL, HARNESS_CORRIDOR), 5.0, places=9
        )

    def test_clearance_of_a_touching_feature_is_zero(self):
        self.assertAlmostEqual(
            rectangle_clearance_mm(TOUCHING_CELL, HARNESS_CORRIDOR), 0.0, places=9
        )

    def test_clearance_on_a_diagonal_is_the_corner_distance(self):
        corner = {"id": "pad", "x_mm": 85.0, "y_mm": 35.0, "width_mm": 5.0, "height_mm": 5.0}
        self.assertAlmostEqual(
            rectangle_clearance_mm(corner, HARNESS_CORRIDOR),
            math.hypot(5.0, 4.0),
            places=9,
        )

    def test_intrusion_depth_is_the_shortest_way_out(self):
        self.assertAlmostEqual(
            intrusion_depth_mm(INTRUDING_CELL, HARNESS_CORRIDOR), 2.0, places=9
        )

    def test_intrusion_depth_of_a_clear_feature_is_zero(self):
        self.assertAlmostEqual(
            intrusion_depth_mm(CLEAR_CELL, HARNESS_CORRIDOR), 0.0, places=12
        )

    def test_a_rectangle_with_no_width_rejected(self):
        with self.assertRaises(ValueError):
            rectangle_overlap_area_mm2(_with(CLEAR_CELL, width_mm=0.0), HARNESS_CORRIDOR)

    def test_a_rectangle_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            rectangle_clearance_mm("cell-a1", HARNESS_CORRIDOR)


class EdgeMarginTests(unittest.TestCase):
    def test_a_margin_builds_four_border_bands(self):
        zones = edge_margin_zones(80.0, 60.0, 2.0)
        self.assertEqual(len(zones), 4)
        self.assertEqual(
            sorted(z["id"] for z in zones),
            [
                "edge-margin-bottom",
                "edge-margin-left",
                "edge-margin-right",
                "edge-margin-top",
            ],
        )

    def test_the_bands_do_not_overlap_each_other(self):
        zones = edge_margin_zones(80.0, 60.0, 2.0)
        for i, first in enumerate(zones):
            for second in zones[i + 1:]:
                self.assertAlmostEqual(
                    rectangle_overlap_area_mm2(first, second), 0.0, places=12
                )

    def test_a_margin_that_consumes_the_coupon_rejected(self):
        with self.assertRaises(ValueError):
            edge_margin_zones(80.0, 60.0, 40.0)

    def test_a_zero_margin_rejected(self):
        with self.assertRaises(ValueError):
            edge_margin_zones(80.0, 60.0, 0.0)


class StayOutZoneTests(unittest.TestCase):
    def test_a_clear_layout_reports_no_breach(self):
        report = check_stay_out_zones([HARNESS_CORRIDOR], [CLEAR_CELL])
        self.assertTrue(report["clear"])
        self.assertEqual(report["pairs"][0]["verdict"], ZONE_CLEAR)
        self.assertEqual(report["findings"], [])

    def test_an_intruding_feature_is_reported_with_its_depth(self):
        report = check_stay_out_zones([HARNESS_CORRIDOR], [INTRUDING_CELL])
        self.assertFalse(report["clear"])
        self.assertEqual(report["pairs"][0]["verdict"], ZONE_INTRUDED)
        self.assertAlmostEqual(report["pairs"][0]["intrusion_depth_mm"], 2.0, places=9)

    def test_a_touching_feature_clears_a_zero_minimum(self):
        report = check_stay_out_zones([HARNESS_CORRIDOR], [TOUCHING_CELL])
        self.assertAlmostEqual(report["pairs"][0]["clearance_mm"], 0.0, places=9)
        self.assertEqual(report["pairs"][0]["verdict"], ZONE_CLEAR)

    def test_a_touching_feature_fails_a_positive_minimum(self):
        report = check_stay_out_zones([HARNESS_CORRIDOR], [TOUCHING_CELL], 0.5)
        self.assertEqual(report["pairs"][0]["verdict"], ZONE_CLEARANCE_SHORT)
        self.assertFalse(report["clear"])

    def test_a_feature_exactly_on_the_minimum_clearance_passes(self):
        report = check_stay_out_zones([HARNESS_CORRIDOR], [CLEAR_CELL], 5.0)
        self.assertAlmostEqual(report["pairs"][0]["clearance_mm"], 5.0, places=9)
        self.assertEqual(report["pairs"][0]["verdict"], ZONE_CLEAR)

    def test_every_feature_is_tested_against_every_zone(self):
        report = check_stay_out_zones(
            edge_margin_zones(80.0, 60.0, 2.0), [CLEAR_CELL, TOUCHING_CELL]
        )
        self.assertEqual(len(report["pairs"]), 8)

    def test_duplicate_zone_identifiers_rejected(self):
        with self.assertRaises(ValueError):
            check_stay_out_zones(
                [HARNESS_CORRIDOR, copy.deepcopy(HARNESS_CORRIDOR)], [CLEAR_CELL]
            )

    def test_an_unnamed_feature_rejected(self):
        with self.assertRaises(ValueError):
            check_stay_out_zones([HARNESS_CORRIDOR], [_with(CLEAR_CELL, id="")])

    def test_an_empty_zone_list_rejected(self):
        with self.assertRaises(ValueError):
            check_stay_out_zones([], [CLEAR_CELL])

    def test_a_negative_minimum_clearance_rejected(self):
        with self.assertRaises(ValueError):
            check_stay_out_zones([HARNESS_CORRIDOR], [CLEAR_CELL], -1.0)


class StandoffTests(unittest.TestCase):
    def test_a_standoff_inside_its_height_band_passes(self):
        report = check_standoff_features([STANDOFF], STANDOFF_HEIGHT_SPEC)
        self.assertTrue(report["heights_within_tolerance"])
        self.assertEqual(report["findings"], [])

    def test_a_tall_standoff_is_reported(self):
        report = check_standoff_features(
            [_with(STANDOFF, height_mm=3.2)], STANDOFF_HEIGHT_SPEC
        )
        self.assertFalse(report["heights_within_tolerance"])
        self.assertTrue(any("stands" in f for f in report["findings"]))

    def test_a_standoff_footprint_inside_a_zone_is_reported(self):
        footprint = {"x_mm": 10.0, "y_mm": 26.0, "width_mm": 4.0, "height_mm": 4.0}
        report = check_standoff_features(
            [_with(STANDOFF, footprint=footprint)],
            STANDOFF_HEIGHT_SPEC,
            [HARNESS_CORRIDOR],
        )
        self.assertFalse(report["zone_report"]["clear"])

    def test_duplicate_standoff_identifiers_rejected(self):
        with self.assertRaises(ValueError):
            check_standoff_features(
                [STANDOFF, copy.deepcopy(STANDOFF)], STANDOFF_HEIGHT_SPEC
            )

    def test_a_standoff_without_a_footprint_rejected(self):
        broken = copy.deepcopy(STANDOFF)
        del broken["footprint"]
        with self.assertRaises(ValueError):
            check_standoff_features([broken], STANDOFF_HEIGHT_SPEC)

    def test_an_empty_standoff_list_rejected(self):
        with self.assertRaises(ValueError):
            check_standoff_features([], STANDOFF_HEIGHT_SPEC)


class CouponGeometryTests(unittest.TestCase):
    def _case(self, **overrides):
        case = {
            "dimension_spec": copy.deepcopy(DIMENSION_SPEC),
            "measured_dimensions": copy.deepcopy(MEASURED),
            "stay_out_zones": [copy.deepcopy(HARNESS_CORRIDOR)],
            "features": [copy.deepcopy(CLEAR_CELL)],
            "standoffs": [copy.deepcopy(STANDOFF)],
            "standoff_height_spec": copy.deepcopy(STANDOFF_HEIGHT_SPEC),
            "minimum_clearance_mm": 1.0,
        }
        case.update(overrides)
        return case

    def test_a_conforming_coupon_is_accepted(self):
        report = inspect_coupon_geometry(self._case())
        self.assertEqual(report["verdict"], GEOMETRY_ACCEPTED)
        self.assertEqual(report["findings"], [])

    def test_an_out_of_tolerance_dimension_rejects_the_coupon(self):
        report = inspect_coupon_geometry(
            self._case(measured_dimensions=_with(MEASURED, width=80.6))
        )
        self.assertEqual(report["verdict"], GEOMETRY_REJECTED)
        self.assertIn("width", report["dimensions"]["out_of_tolerance"])

    def test_an_intruding_feature_rejects_the_coupon(self):
        report = inspect_coupon_geometry(self._case(features=[INTRUDING_CELL]))
        self.assertEqual(report["verdict"], GEOMETRY_REJECTED)
        self.assertFalse(report["zone_report"]["clear"])

    def test_an_edge_margin_adds_border_zones_to_the_check(self):
        report = inspect_coupon_geometry(self._case(edge_margin_mm=2.0))
        zones = {pair["zone"] for pair in report["zone_report"]["pairs"]}
        self.assertIn("edge-margin-left", zones)
        self.assertIn("harness-corridor", zones)

    def test_a_feature_inside_the_edge_margin_rejects_the_coupon(self):
        intruder = {
            "id": "cell-edge",
            "x_mm": 0.5,
            "y_mm": 5.0,
            "width_mm": 10.0,
            "height_mm": 5.0,
        }
        report = inspect_coupon_geometry(
            self._case(edge_margin_mm=2.0, features=[intruder], standoffs=[])
        )
        self.assertEqual(report["verdict"], GEOMETRY_REJECTED)

    def test_features_with_no_declared_zone_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_geometry(self._case(stay_out_zones=[], standoffs=[]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_geometry("coupon-01")

    def test_a_short_standoff_rejects_the_coupon(self):
        report = inspect_coupon_geometry(
            self._case(standoffs=[_with(STANDOFF, height_mm=2.8)])
        )
        self.assertEqual(report["verdict"], GEOMETRY_REJECTED)
        self.assertFalse(report["standoff_report"]["heights_within_tolerance"])


if __name__ == "__main__":
    unittest.main()

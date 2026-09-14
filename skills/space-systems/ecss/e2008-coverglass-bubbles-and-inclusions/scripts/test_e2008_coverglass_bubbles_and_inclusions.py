#!/usr/bin/env python3
"""Contract test for the coverglass bubble and inclusion screen (offline)."""

import copy
import math
import unittest

from e2008_coverglass_bubbles_and_inclusions_logic import (
    ACCEPT,
    BUBBLE,
    CLAUSE_PROJECTED_AREA_CAP_MM2,
    DEFAULT_INCLUSION_ALLOWANCES,
    INCLUSION,
    INSPECTION_INCOMPLETE,
    REJECT,
    REVIEW,
    active_aperture,
    assess_coverglass_inclusions,
    edge_separation_mm,
    equivalent_diameter_mm,
    group_adjacent_features,
    inspect_coverglass_bubbles_and_inclusions,
    measure_feature,
    projected_area_mm2,
    screen_coverglass_features,
    validate_coverglass_aperture,
    validate_inclusion_allowances,
)

CAP = CLAUSE_PROJECTED_AREA_CAP_MM2


def _geometry(**overrides):
    record = {
        "coverglass_type": "CMX-100",
        "width_mm": 40.0,
        "height_mm": 20.0,
        "edge_exclusion_mm": 0.5,
    }
    record.update(overrides)
    return record


def _unit_geometry(**overrides):
    """A coverglass whose active aperture is exactly one square centimetre."""
    record = {
        "coverglass_type": "CMX-100",
        "width_mm": 12.0,
        "height_mm": 12.0,
        "edge_exclusion_mm": 1.0,
    }
    record.update(overrides)
    return record


def _feature(area_mm2=0.005, x_mm=5.0, y_mm=5.0, kind=BUBBLE,
             distance_from_edge_mm=3.0):
    return {
        "kind": kind,
        "projected_area_mm2": area_mm2,
        "x_mm": x_mm,
        "y_mm": y_mm,
        "distance_from_edge_mm": distance_from_edge_mm,
    }


def _spread(how_many, area_mm2=CAP, pitch_mm=0.5):
    return [
        _feature(area_mm2, x_mm=pitch_mm * (n + 1), y_mm=6.0)
        for n in range(how_many)
    ]


def _coverglass(coverglass_id="CG-001", **overrides):
    record = {
        "coverglass_id": coverglass_id,
        "coverglass_type": "CMX-100",
        "features": [],
    }
    record.update(overrides)
    return record


def _lot(how_many, declared=None):
    return {
        "lot_id": "CGL-52",
        "declared_coverglass_count": declared if declared is not None else how_many,
        "coverglasses": [_coverglass("CG-%03d" % n) for n in range(1, how_many + 1)],
    }


class AllowanceValidationTests(unittest.TestCase):
    def test_default_allowances_validate(self):
        self.assertIs(
            validate_inclusion_allowances(DEFAULT_INCLUSION_ALLOWANCES),
            DEFAULT_INCLUSION_ALLOWANCES,
        )

    def test_the_default_cap_is_two_hundredths_of_a_square_millimetre(self):
        self.assertAlmostEqual(
            DEFAULT_INCLUSION_ALLOWANCES["max_feature_projected_area_mm2"],
            0.02,
            places=12,
        )

    def test_non_mapping_allowances_refused(self):
        with self.assertRaises(ValueError):
            validate_inclusion_allowances(0.02)

    def test_a_non_positive_cap_refused(self):
        broken = copy.deepcopy(DEFAULT_INCLUSION_ALLOWANCES)
        broken["max_feature_projected_area_mm2"] = 0.0
        with self.assertRaises(ValueError):
            validate_inclusion_allowances(broken)

    def test_a_total_area_fraction_above_one_refused(self):
        broken = copy.deepcopy(DEFAULT_INCLUSION_ALLOWANCES)
        broken["max_total_area_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_inclusion_allowances(broken)

    def test_a_review_margin_below_one_refused(self):
        broken = copy.deepcopy(DEFAULT_INCLUSION_ALLOWANCES)
        broken["review_margin_factor"] = 0.9
        with self.assertRaises(ValueError):
            validate_inclusion_allowances(broken)

    def test_a_method_that_cannot_resolve_below_the_cap_refused(self):
        broken = copy.deepcopy(DEFAULT_INCLUSION_ALLOWANCES)
        broken["min_resolvable_area_mm2"] = 0.05
        with self.assertRaises(ValueError):
            validate_inclusion_allowances(broken)

    def test_a_negative_merge_separation_refused(self):
        broken = copy.deepcopy(DEFAULT_INCLUSION_ALLOWANCES)
        broken["merge_separation_mm"] = -0.01
        with self.assertRaises(ValueError):
            validate_inclusion_allowances(broken)


class ApertureTests(unittest.TestCase):
    def test_a_valid_geometry_returns_itself(self):
        geometry = _geometry()
        self.assertIs(validate_coverglass_aperture(geometry), geometry)

    def test_a_geometry_without_a_type_refused(self):
        with self.assertRaises(ValueError):
            validate_coverglass_aperture(_geometry(coverglass_type=" "))

    def test_a_non_positive_width_refused(self):
        with self.assertRaises(ValueError):
            validate_coverglass_aperture(_geometry(width_mm=0.0))

    def test_a_band_that_consumes_the_coverglass_refused(self):
        with self.assertRaises(ValueError):
            validate_coverglass_aperture(_geometry(edge_exclusion_mm=10.0))

    def test_the_aperture_is_the_coverglass_less_the_band(self):
        aperture = active_aperture(_geometry())
        self.assertAlmostEqual(aperture["active_area_mm2"], 741.0, places=9)

    def test_the_unit_geometry_is_one_square_centimetre(self):
        aperture = active_aperture(_unit_geometry())
        self.assertAlmostEqual(aperture["active_area_mm2"], 100.0, places=9)


class ProjectedAreaTests(unittest.TestCase):
    def test_a_measured_area_is_taken_as_given(self):
        self.assertAlmostEqual(
            projected_area_mm2(_feature(0.004)), 0.004, places=12
        )

    def test_a_diameter_projects_a_circle(self):
        area = projected_area_mm2(
            {"kind": INCLUSION, "diameter_mm": 0.1}
        )
        self.assertAlmostEqual(area, math.pi * 0.01 / 4.0, places=12)

    def test_two_axes_project_an_ellipse(self):
        area = projected_area_mm2(
            {"kind": BUBBLE, "major_axis_mm": 0.2, "minor_axis_mm": 0.1}
        )
        self.assertAlmostEqual(area, math.pi * 0.02 / 4.0, places=12)

    def test_equal_axes_agree_with_the_diameter_form(self):
        by_axes = projected_area_mm2(
            {"kind": BUBBLE, "major_axis_mm": 0.1, "minor_axis_mm": 0.1}
        )
        by_diameter = projected_area_mm2({"kind": BUBBLE, "diameter_mm": 0.1})
        self.assertAlmostEqual(by_axes, by_diameter, places=12)

    def test_a_feature_measured_no_way_refused(self):
        with self.assertRaises(ValueError):
            projected_area_mm2({"kind": BUBBLE})

    def test_a_feature_measured_two_ways_refused(self):
        with self.assertRaises(ValueError):
            projected_area_mm2(
                {"kind": BUBBLE, "diameter_mm": 0.1, "projected_area_mm2": 0.01}
            )

    def test_swapped_axes_refused(self):
        with self.assertRaises(ValueError):
            projected_area_mm2(
                {"kind": BUBBLE, "major_axis_mm": 0.1, "minor_axis_mm": 0.2}
            )

    def test_an_unknown_feature_kind_refused(self):
        with self.assertRaises(ValueError):
            projected_area_mm2({"kind": "streak", "diameter_mm": 0.1})

    def test_a_non_mapping_feature_refused(self):
        with self.assertRaises(ValueError):
            projected_area_mm2("a bubble")

    def test_a_feature_below_the_resolution_of_the_method_refused(self):
        with self.assertRaises(ValueError):
            projected_area_mm2(_feature(1e-8))

    def test_the_equivalent_diameter_round_trips(self):
        diameter = equivalent_diameter_mm(CAP)
        back = math.pi * diameter * diameter / 4.0
        self.assertAlmostEqual(back, CAP, places=12)

    def test_a_zero_area_has_no_equivalent_diameter(self):
        with self.assertRaises(ValueError):
            equivalent_diameter_mm(0.0)


class GroupingTests(unittest.TestCase):
    def test_features_far_apart_stay_apart(self):
        measured = [
            measure_feature(_feature(0.004, 2.0, 5.0), _geometry()),
            measure_feature(_feature(0.004, 9.0, 5.0), _geometry()),
        ]
        groups = group_adjacent_features(measured)
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["member_count"], 1)
        self.assertFalse(groups[0]["merged"])

    def test_the_edge_separation_is_rim_to_rim_not_centre_to_centre(self):
        first = measure_feature(_feature(CAP, 5.0, 5.0), _geometry())
        second = measure_feature(_feature(CAP, 5.2, 5.0), _geometry())
        gap = edge_separation_mm(first, second)
        self.assertAlmostEqual(
            gap, 0.2 - equivalent_diameter_mm(CAP), places=12
        )

    def test_two_close_features_read_as_one(self):
        measured = [
            measure_feature(_feature(0.012, 5.0, 5.0), _geometry()),
            measure_feature(_feature(0.012, 5.15, 5.0), _geometry()),
        ]
        groups = group_adjacent_features(measured)
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]["merged"])
        self.assertAlmostEqual(groups[0]["projected_area_mm2"], 0.024, places=12)

    def test_a_chain_of_three_is_one_group(self):
        measured = [
            measure_feature(_feature(0.008, 5.00, 5.0), _geometry()),
            measure_feature(_feature(0.008, 5.15, 5.0), _geometry()),
            measure_feature(_feature(0.008, 5.30, 5.0), _geometry()),
        ]
        groups = group_adjacent_features(measured)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["member_count"], 3)

    def test_a_group_reports_the_kinds_it_holds(self):
        measured = [
            measure_feature(_feature(0.008, 5.00, 5.0, BUBBLE), _geometry()),
            measure_feature(_feature(0.008, 5.15, 5.0, INCLUSION), _geometry()),
        ]
        groups = group_adjacent_features(measured)
        self.assertEqual(groups[0]["kinds"], [BUBBLE, INCLUSION])

    def test_measured_features_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            group_adjacent_features("one bubble")

    def test_band_features_never_reach_the_grouping(self):
        screen = screen_coverglass_features(
            [_feature(CAP, 5.0, 5.0, BUBBLE, 0.1)], _geometry()
        )
        self.assertEqual(screen["edge_band_count"], 1)
        self.assertEqual(screen["group_count"], 0)
        self.assertAlmostEqual(screen["total_projected_area_mm2"], 0.0, places=12)

    def test_a_feature_on_the_band_edge_is_graded(self):
        screen = screen_coverglass_features(
            [_feature(0.004, 5.0, 5.0, BUBBLE, 0.5)], _geometry()
        )
        self.assertEqual(screen["edge_band_count"], 0)
        self.assertEqual(screen["graded_feature_count"], 1)

    def test_features_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            screen_coverglass_features("two bubbles", _geometry())


class SingleCoverglassTests(unittest.TestCase):
    def test_a_clear_coverglass_is_accepted(self):
        result = assess_coverglass_inclusions(_coverglass(), _geometry())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["examined"])
        self.assertEqual(result["findings"], [])

    def test_a_feature_that_lands_on_the_cap_is_accepted(self):
        record = _coverglass(features=[_feature(CAP, 5.0, 5.0)])
        result = assess_coverglass_inclusions(record, _geometry())
        self.assertAlmostEqual(
            result["screen"]["largest_projected_area_mm2"], CAP, places=12
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_feature_past_the_cap_goes_to_review(self):
        record = _coverglass(features=[_feature(0.025, 5.0, 5.0)])
        result = assess_coverglass_inclusions(record, _geometry())
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(any("past the" in f for f in result["findings"]))

    def test_a_feature_far_past_the_cap_is_rejected(self):
        record = _coverglass(features=[_feature(0.050, 5.0, 5.0)])
        result = assess_coverglass_inclusions(record, _geometry())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_cluster_under_the_cap_individually_still_breaches_it(self):
        record = _coverglass(
            features=[
                _feature(0.012, 5.00, 5.0),
                _feature(0.012, 5.15, 5.0),
            ]
        )
        result = assess_coverglass_inclusions(record, _geometry())
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(
            any("each is under it alone" in f for f in result["findings"])
        )

    def test_the_same_pair_set_far_apart_is_accepted(self):
        record = _coverglass(
            features=[
                _feature(0.012, 5.0, 5.0),
                _feature(0.012, 12.0, 5.0),
            ]
        )
        result = assess_coverglass_inclusions(record, _geometry())
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_summed_area_on_the_allowance_is_accepted(self):
        record = _coverglass(features=_spread(10))
        result = assess_coverglass_inclusions(record, _unit_geometry())
        self.assertAlmostEqual(
            result["screen"]["total_area_fraction"],
            DEFAULT_INCLUSION_ALLOWANCES["max_total_area_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_features_each_under_the_cap_can_still_lose_too_much_aperture(self):
        record = _coverglass(features=_spread(12))
        result = assess_coverglass_inclusions(record, _unit_geometry())
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(
            any("no single one is over the cap" in f for f in result["findings"])
        )

    def test_far_too_much_summed_area_is_rejected(self):
        record = _coverglass(features=_spread(20))
        result = assess_coverglass_inclusions(record, _unit_geometry())
        self.assertEqual(result["verdict"], REJECT)

    def test_an_oversize_feature_in_the_band_does_not_take_the_part_out(self):
        record = _coverglass(features=[_feature(0.050, 5.0, 5.0, BUBBLE, 0.1)])
        result = assess_coverglass_inclusions(record, _geometry())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(any("rather than graded" in f for f in result["findings"]))

    def test_a_coverglass_of_another_type_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_inclusions(
                _coverglass(coverglass_type="CMG-50"), _geometry()
            )

    def test_a_record_without_an_id_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_inclusions(_coverglass(coverglass_id=""), _geometry())

    def test_a_non_mapping_record_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_inclusions("CG-001", _geometry())

    def test_an_absent_feature_list_is_not_an_empty_one(self):
        result = assess_coverglass_inclusions(
            _coverglass(features=None), _geometry()
        )
        self.assertFalse(result["examined"])
        self.assertIsNone(result["screen"])
        self.assertTrue(any("not an empty one" in f for f in result["findings"]))

    def test_the_part_report_carries_the_cap_it_answered_to(self):
        result = assess_coverglass_inclusions(_coverglass(), _geometry())
        self.assertAlmostEqual(result["projected_area_cap_mm2"], CAP, places=12)


class LotRollupTests(unittest.TestCase):
    def test_a_clear_lot_is_accepted_and_complete(self):
        result = inspect_coverglass_bubbles_and_inclusions(_lot(40), _geometry())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_one_bad_coverglass_names_itself(self):
        lot = _lot(40)
        lot["coverglasses"][2]["features"] = [_feature(0.050, 5.0, 5.0)]
        result = inspect_coverglass_bubbles_and_inclusions(lot, _geometry())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["CG-003"])
        self.assertEqual(result["affected_count"], 1)

    def test_too_many_affected_coverglasses_take_the_lot_out(self):
        lot = _lot(20)
        for record in lot["coverglasses"][:6]:
            record["features"] = [_feature(0.050, 5.0, 5.0)]
        result = inspect_coverglass_bubbles_and_inclusions(lot, _geometry())
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("lot allowance" in f or "review margin" in f
                for f in result["findings"])
        )

    def test_the_remaining_lot_allowance_is_reported(self):
        result = inspect_coverglass_bubbles_and_inclusions(_lot(20), _geometry())
        self.assertAlmostEqual(result["affected_allowance"], 1.0, places=9)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 1.0, places=9)

    def test_an_unexamined_coverglass_leaves_the_lot_open(self):
        lot = _lot(10)
        lot["coverglasses"][4]["features"] = None
        result = inspect_coverglass_bubbles_and_inclusions(lot, _geometry())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["unexamined_coverglass_ids"], ["CG-005"])

    def test_a_short_record_set_leaves_the_lot_open(self):
        result = inspect_coverglass_bubbles_and_inclusions(
            _lot(8, declared=10), _geometry()
        )
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_more_records_than_declared_refused(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_bubbles_and_inclusions(_lot(6, declared=5), _geometry())

    def test_duplicate_coverglass_ids_refused(self):
        lot = _lot(4)
        lot["coverglasses"][3]["coverglass_id"] = "CG-001"
        with self.assertRaises(ValueError):
            inspect_coverglass_bubbles_and_inclusions(lot, _geometry())

    def test_a_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_bubbles_and_inclusions("CGL-52", _geometry())

    def test_coverglasses_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_bubbles_and_inclusions(
                {
                    "lot_id": "CGL-52",
                    "declared_coverglass_count": 3,
                    "coverglasses": "three",
                },
                _geometry(),
            )

    def test_a_non_integer_declared_count_refused(self):
        lot = _lot(3)
        lot["declared_coverglass_count"] = "three"
        with self.assertRaises(ValueError):
            inspect_coverglass_bubbles_and_inclusions(lot, _geometry())

    def test_the_lot_report_carries_the_cap_and_its_equivalent_diameter(self):
        result = inspect_coverglass_bubbles_and_inclusions(_lot(5), _geometry())
        self.assertAlmostEqual(result["projected_area_cap_mm2"], CAP, places=12)
        self.assertAlmostEqual(
            result["cap_equivalent_diameter_mm"],
            math.sqrt(4.0 * CAP / math.pi),
            places=12,
        )
        self.assertEqual(result["inspected_count"], 5)


if __name__ == "__main__":
    unittest.main()

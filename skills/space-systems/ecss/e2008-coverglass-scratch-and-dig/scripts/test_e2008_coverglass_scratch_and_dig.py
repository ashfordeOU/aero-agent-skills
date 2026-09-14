#!/usr/bin/env python3
"""Contract test for the coverglass scratch and dig screen (offline)."""

import copy
import unittest

from e2008_coverglass_scratch_and_dig_logic import (
    ACCEPT,
    DEFAULT_SCRATCH_DIG_MARGINS,
    DIG,
    INSPECTION_INCOMPLETE,
    REJECT,
    REVIEW,
    SCRATCH,
    assess_coverglass_scratch_and_dig,
    dig_grade_from_diameter,
    drawing_limits,
    inspect_coverglass_scratch_and_dig,
    measure_feature,
    parse_scratch_dig_designation,
    screen_surface_features,
    scratch_grade_from_width,
    validate_source_control_drawing,
)


def _drawing(**overrides):
    record = {
        "drawing_id": "SCD-CG-1188",
        "revision": "C",
        "designation": "60-40",
        "scratch_unit_mm": 0.001,
        "dig_unit_mm": 0.01,
        "aperture_reference_mm": 40.0,
        "edge_exclusion_mm": 0.5,
        "aggregate_scratch_length_fraction": 0.25,
        "dig_concentration_factor": 2.0,
    }
    record.update(overrides)
    return record


def _scratch(width_mm=0.02, length_mm=2.0, distance_from_edge_mm=5.0):
    return {
        "kind": SCRATCH,
        "width_mm": width_mm,
        "length_mm": length_mm,
        "distance_from_edge_mm": distance_from_edge_mm,
    }


def _dig(diameter_mm=0.10, distance_from_edge_mm=5.0):
    return {
        "kind": DIG,
        "diameter_mm": diameter_mm,
        "distance_from_edge_mm": distance_from_edge_mm,
    }


def _coverglass(coverglass_id="CG-001", **overrides):
    record = {
        "coverglass_id": coverglass_id,
        "drawing_id": "SCD-CG-1188",
        "drawing_revision": "C",
        "features": [],
    }
    record.update(overrides)
    return record


def _lot(how_many, declared=None):
    return {
        "lot_id": "CGL-77",
        "declared_coverglass_count": declared if declared is not None else how_many,
        "coverglasses": [_coverglass("CG-%03d" % n) for n in range(1, how_many + 1)],
    }


class DesignationTests(unittest.TestCase):
    def test_a_dashed_designation_splits_into_two_grades(self):
        self.assertEqual(
            parse_scratch_dig_designation("60-40"),
            {"scratch_grade": 60, "dig_grade": 40},
        )

    def test_a_slashed_designation_is_read_the_same_way(self):
        self.assertEqual(
            parse_scratch_dig_designation("80/50"),
            {"scratch_grade": 80, "dig_grade": 50},
        )

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(
            parse_scratch_dig_designation("  20 - 10 "),
            {"scratch_grade": 20, "dig_grade": 10},
        )

    def test_a_single_number_is_not_a_designation(self):
        with self.assertRaises(ValueError):
            parse_scratch_dig_designation("60")

    def test_a_zero_grade_is_refused(self):
        with self.assertRaises(ValueError):
            parse_scratch_dig_designation("60-0")

    def test_a_non_text_designation_is_refused(self):
        with self.assertRaises(ValueError):
            parse_scratch_dig_designation(6040)


class DrawingValidationTests(unittest.TestCase):
    def test_a_valid_drawing_yields_its_two_grades(self):
        self.assertEqual(
            validate_source_control_drawing(_drawing()),
            {"scratch_grade": 60, "dig_grade": 40},
        )

    def test_a_missing_drawing_is_refused_rather_than_defaulted(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(None)

    def test_a_drawing_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(_drawing(drawing_id=" "))

    def test_a_drawing_without_a_revision_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(_drawing(revision=""))

    def test_a_drawing_without_an_aperture_reference_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(_drawing(aperture_reference_mm=0.0))

    def test_more_summed_scratch_than_aperture_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(
                _drawing(aggregate_scratch_length_fraction=1.4)
            )

    def test_an_exclusion_band_that_consumes_the_aperture_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(_drawing(edge_exclusion_mm=25.0))

    def test_a_negative_exclusion_band_is_refused(self):
        with self.assertRaises(ValueError):
            validate_source_control_drawing(_drawing(edge_exclusion_mm=-1.0))


class DrawingLimitTests(unittest.TestCase):
    def test_the_grades_resolve_into_millimetres_through_the_units(self):
        limits = drawing_limits(_drawing())
        self.assertAlmostEqual(limits["max_scratch_width_mm"], 0.060, places=9)
        self.assertAlmostEqual(limits["max_dig_diameter_mm"], 0.40, places=9)

    def test_the_aggregate_scratch_allowance_follows_the_aperture(self):
        limits = drawing_limits(_drawing())
        self.assertAlmostEqual(limits["max_summed_scratch_length_mm"], 10.0, places=9)

    def test_the_dig_concentration_allowance_scales_with_the_aperture(self):
        limits = drawing_limits(_drawing())
        self.assertAlmostEqual(limits["max_summed_dig_grade"], 160.0, places=9)

    def test_a_different_unit_moves_the_millimetre_limit_not_the_grade(self):
        limits = drawing_limits(_drawing(dig_unit_mm=0.02))
        self.assertAlmostEqual(limits["max_dig_grade"], 40.0, places=9)
        self.assertAlmostEqual(limits["max_dig_diameter_mm"], 0.80, places=9)

    def test_a_measured_width_converts_to_the_scratch_grade(self):
        self.assertAlmostEqual(
            scratch_grade_from_width(0.060, _drawing()), 60.0, places=9
        )

    def test_a_measured_diameter_converts_to_the_dig_grade(self):
        self.assertAlmostEqual(
            dig_grade_from_diameter(0.40, _drawing()), 40.0, places=9
        )

    def test_a_zero_width_is_not_a_scratch(self):
        with self.assertRaises(ValueError):
            scratch_grade_from_width(0.0, _drawing())

    def test_a_negative_diameter_is_refused(self):
        with self.assertRaises(ValueError):
            dig_grade_from_diameter(-0.1, _drawing())


class FeatureMeasurementTests(unittest.TestCase):
    def test_a_scratch_carries_its_grade_and_its_length(self):
        measured = measure_feature(_scratch(0.02, 3.0), _drawing())
        self.assertAlmostEqual(measured["grade"], 20.0, places=9)
        self.assertAlmostEqual(measured["length_mm"], 3.0, places=9)
        self.assertTrue(measured["within_grade_limit"])

    def test_a_feature_that_lands_on_the_drawing_limit_is_within_it(self):
        measured = measure_feature(_dig(0.40), _drawing())
        self.assertAlmostEqual(measured["grade"], 40.0, places=9)
        self.assertTrue(measured["within_grade_limit"])

    def test_an_unknown_feature_kind_is_refused(self):
        with self.assertRaises(ValueError):
            measure_feature({"kind": "chip", "diameter_mm": 0.1}, _drawing())

    def test_a_non_mapping_feature_is_refused(self):
        with self.assertRaises(ValueError):
            measure_feature("a scratch", _drawing())

    def test_a_scratch_without_a_width_is_refused(self):
        with self.assertRaises(ValueError):
            measure_feature({"kind": SCRATCH, "length_mm": 2.0}, _drawing())

    def test_a_dig_without_a_diameter_is_refused(self):
        with self.assertRaises(ValueError):
            measure_feature({"kind": DIG}, _drawing())

    def test_a_scratch_longer_than_the_aperture_is_refused(self):
        with self.assertRaises(ValueError):
            measure_feature(_scratch(0.02, 400.0), _drawing())

    def test_a_feature_in_the_edge_band_is_outside_the_aperture(self):
        measured = measure_feature(_dig(0.1, 0.2), _drawing())
        self.assertFalse(measured["in_active_aperture"])

    def test_a_feature_on_the_band_edge_is_inside_the_aperture(self):
        measured = measure_feature(_dig(0.1, 0.5), _drawing())
        self.assertTrue(measured["in_active_aperture"])

    def test_features_not_a_list_are_refused(self):
        with self.assertRaises(ValueError):
            screen_surface_features("one scratch", _drawing())

    def test_the_two_kinds_are_summed_apart(self):
        screen = screen_surface_features(
            [_scratch(), _scratch(), _dig(), _dig(), _dig()], _drawing()
        )
        self.assertEqual(screen["scratch_count"], 2)
        self.assertEqual(screen["dig_count"], 3)
        self.assertEqual(screen["edge_band_count"], 0)

    def test_band_features_are_kept_out_of_both_aggregate_sums(self):
        screen = screen_surface_features(
            [_scratch(0.06, 2.0, 0.1), _dig(0.4, 0.1)], _drawing()
        )
        self.assertEqual(screen["edge_band_count"], 2)
        self.assertAlmostEqual(screen["weighted_scratch_length_mm"], 0.0, places=12)
        self.assertAlmostEqual(screen["summed_dig_grade"], 0.0, places=12)


class SingleCoverglassTests(unittest.TestCase):
    def test_an_unmarked_coverglass_is_accepted(self):
        result = assess_coverglass_scratch_and_dig(_coverglass(), _drawing())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["examined"])
        self.assertEqual(result["findings"], [])

    def test_a_scratch_at_the_drawing_limit_is_accepted(self):
        record = _coverglass(features=[_scratch(0.060, 2.0)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertAlmostEqual(result["screen"]["worst_scratch_grade"], 60.0, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_dig_past_the_limit_goes_to_review(self):
        record = _coverglass(features=[_dig(0.50)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(any("the drawing fixes" in f for f in result["findings"]))

    def test_a_dig_far_past_the_limit_is_rejected(self):
        record = _coverglass(features=[_dig(1.00)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_wide_scratch_past_the_review_margin_is_rejected(self):
        record = _coverglass(features=[_scratch(0.150, 2.0)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_summed_scratch_length_on_the_allowance_is_accepted(self):
        record = _coverglass(features=[_scratch(0.060, 2.0) for _ in range(5)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertAlmostEqual(
            result["screen"]["weighted_scratch_length_mm"], 10.0, places=9
        )
        self.assertEqual(result["verdict"], ACCEPT)

    def test_individually_acceptable_scratches_can_still_fail_together(self):
        record = _coverglass(features=[_scratch(0.060, 2.0) for _ in range(6)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(
            any("within its own limit" in f for f in result["findings"])
        )

    def test_far_too_much_summed_scratch_is_rejected(self):
        record = _coverglass(features=[_scratch(0.060, 2.0) for _ in range(10)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], REJECT)

    def test_a_dig_grade_sum_on_the_allowance_is_accepted(self):
        record = _coverglass(features=[_dig(0.10) for _ in range(16)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertAlmostEqual(result["screen"]["summed_dig_grade"], 160.0, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_crowded_digs_inside_their_own_limit_go_to_review(self):
        record = _coverglass(features=[_dig(0.10) for _ in range(20)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], REVIEW)
        self.assertTrue(any("the digs sum to grade" in f for f in result["findings"]))

    def test_an_oversize_feature_in_the_edge_band_does_not_take_the_part_out(self):
        record = _coverglass(features=[_dig(1.00, 0.1)])
        result = assess_coverglass_scratch_and_dig(record, _drawing())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(
            any("rather than graded" in f for f in result["findings"])
        )

    def test_a_part_built_to_another_drawing_is_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig(
                _coverglass(drawing_id="SCD-CG-9000"), _drawing()
            )

    def test_a_superseded_drawing_revision_is_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig(
                _coverglass(drawing_revision="B"), _drawing()
            )

    def test_a_record_without_an_id_is_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig(_coverglass(coverglass_id=""), _drawing())

    def test_a_non_mapping_record_is_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig("CG-001", _drawing())

    def test_an_absent_feature_list_is_not_an_empty_one(self):
        result = assess_coverglass_scratch_and_dig(
            _coverglass(features=None), _drawing()
        )
        self.assertFalse(result["examined"])
        self.assertIsNone(result["screen"])
        self.assertTrue(
            any("not an empty one" in f for f in result["findings"])
        )

    def test_the_part_report_names_the_drawing_it_was_graded_to(self):
        result = assess_coverglass_scratch_and_dig(_coverglass(), _drawing())
        self.assertEqual(result["drawing_id"], "SCD-CG-1188")
        self.assertEqual(result["revision"], "C")
        self.assertEqual(result["designation"], "60-40")


class MarginValidationTests(unittest.TestCase):
    def test_non_mapping_margins_refused(self):
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig(_coverglass(), _drawing(), 1.5)

    def test_a_review_margin_below_one_refused(self):
        broken = copy.deepcopy(DEFAULT_SCRATCH_DIG_MARGINS)
        broken["review_margin_factor"] = 0.8
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig(_coverglass(), _drawing(), broken)

    def test_an_affected_fraction_above_one_refused(self):
        broken = copy.deepcopy(DEFAULT_SCRATCH_DIG_MARGINS)
        broken["max_affected_coverglass_fraction"] = 1.5
        with self.assertRaises(ValueError):
            assess_coverglass_scratch_and_dig(_coverglass(), _drawing(), broken)


class LotRollupTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted_and_complete(self):
        result = inspect_coverglass_scratch_and_dig(_lot(40), _drawing())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_one_marked_part_names_itself(self):
        lot = _lot(40)
        lot["coverglasses"][2]["features"] = [_dig(1.00)]
        result = inspect_coverglass_scratch_and_dig(lot, _drawing())
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["CG-003"])
        self.assertEqual(result["affected_count"], 1)

    def test_too_many_marked_parts_take_the_lot_out(self):
        lot = _lot(20)
        for record in lot["coverglasses"][:6]:
            record["features"] = [_dig(1.00)]
        result = inspect_coverglass_scratch_and_dig(lot, _drawing())
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("lot allowance" in f or "review margin" in f
                for f in result["findings"])
        )

    def test_the_remaining_lot_allowance_is_reported(self):
        result = inspect_coverglass_scratch_and_dig(_lot(20), _drawing())
        self.assertAlmostEqual(result["affected_allowance"], 1.0, places=9)
        self.assertAlmostEqual(result["remaining_affected_allowance"], 1.0, places=9)

    def test_an_unexamined_part_leaves_the_lot_open(self):
        lot = _lot(10)
        lot["coverglasses"][4]["features"] = None
        result = inspect_coverglass_scratch_and_dig(lot, _drawing())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["unexamined_coverglass_ids"], ["CG-005"])

    def test_a_short_record_set_leaves_the_lot_open(self):
        result = inspect_coverglass_scratch_and_dig(_lot(8, declared=10), _drawing())
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("wrong population" in f for f in result["findings"]))

    def test_more_records_than_declared_refused(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_scratch_and_dig(_lot(6, declared=5), _drawing())

    def test_duplicate_coverglass_ids_refused(self):
        lot = _lot(4)
        lot["coverglasses"][3]["coverglass_id"] = "CG-001"
        with self.assertRaises(ValueError):
            inspect_coverglass_scratch_and_dig(lot, _drawing())

    def test_a_non_mapping_lot_refused(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_scratch_and_dig("CGL-77", _drawing())

    def test_coverglasses_not_a_list_refused(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_scratch_and_dig(
                {
                    "lot_id": "CGL-77",
                    "declared_coverglass_count": 3,
                    "coverglasses": "three",
                },
                _drawing(),
            )

    def test_a_non_integer_declared_count_refused(self):
        lot = _lot(3)
        lot["declared_coverglass_count"] = "three"
        with self.assertRaises(ValueError):
            inspect_coverglass_scratch_and_dig(lot, _drawing())

    def test_the_lot_report_carries_the_limits_it_answered_to(self):
        result = inspect_coverglass_scratch_and_dig(_lot(5), _drawing())
        self.assertEqual(result["designation"], "60-40")
        self.assertAlmostEqual(result["max_scratch_width_mm"], 0.060, places=9)
        self.assertAlmostEqual(result["max_dig_diameter_mm"], 0.40, places=9)
        self.assertEqual(result["inspected_count"], 5)


if __name__ == "__main__":
    unittest.main()

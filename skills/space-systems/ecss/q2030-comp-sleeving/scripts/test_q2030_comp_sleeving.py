#!/usr/bin/env python3
"""Contract test for the complementary insulation-sleeving leaf."""

import unittest

from q2030_comp_sleeving_logic import (
    assess_sleeving,
    clearance_to_feature_mm,
    covers_span,
    evaluate_sleeve,
    installed_length_mm,
    recovered_inside_diameter_mm,
    required_cut_length_mm,
    select_sleeve,
    sleeve_grips,
    sleeve_slides_on,
)


def good_sleeve(**overrides):
    record = {
        "id": "S-1",
        "supplied_id_mm": 4.8,
        "recovery_ratio": 2.0,
        "largest_path_diameter_mm": 4.0,
        "smallest_gripped_diameter_mm": 2.6,
        "grip_margin": 0.05,
        "span_mm": 10.0,
        "overlap_each_end_mm": 2.0,
        "cut_length_mm": 16.0,
        "longitudinal_shrinkage": 0.10,
        "sleeve_end_position_mm": 3.0,
        "restricted_feature_position_mm": 5.0,
        "minimum_feature_clearance_mm": 0.5,
        "opaque": False,
        "joint_inspection_recorded": True,
    }
    record.update(overrides)
    return record


class TestRecoveredDiameter(unittest.TestCase):
    def test_two_to_one_sleeve_halves_its_bore(self):
        self.assertAlmostEqual(recovered_inside_diameter_mm(4.8, 2.0), 2.4, places=9)

    def test_three_to_one_sleeve_recovers_further(self):
        self.assertAlmostEqual(recovered_inside_diameter_mm(6.0, 3.0), 2.0, places=9)

    def test_unity_ratio_recovers_nothing(self):
        self.assertAlmostEqual(recovered_inside_diameter_mm(4.8, 1.0), 4.8, places=9)

    def test_ratio_below_unity_raises(self):
        with self.assertRaises(ValueError):
            recovered_inside_diameter_mm(4.8, 0.9)

    def test_non_numeric_diameter_raises(self):
        with self.assertRaises(ValueError):
            recovered_inside_diameter_mm("4.8", 2.0)


class TestSlideAndGrip(unittest.TestCase):
    def test_sleeve_wider_than_the_path_slides_on(self):
        self.assertTrue(sleeve_slides_on(4.8, 4.0))

    def test_sleeve_exactly_on_the_path_diameter_slides_on(self):
        self.assertTrue(sleeve_slides_on(4.0, 4.0))

    def test_sleeve_narrower_than_the_path_does_not_slide_on(self):
        self.assertFalse(sleeve_slides_on(3.5, 4.0))

    def test_recovered_sleeve_below_the_margin_grips(self):
        self.assertTrue(sleeve_grips(2.4, 2.6, 0.05))

    def test_recovered_sleeve_exactly_on_the_margin_grips(self):
        self.assertTrue(sleeve_grips(2.6 * 0.95, 2.6, 0.05))

    def test_recovered_sleeve_above_the_gripped_diameter_does_not_grip(self):
        self.assertFalse(sleeve_grips(2.9, 2.6, 0.05))

    def test_grip_margin_of_one_raises(self):
        with self.assertRaises(ValueError):
            sleeve_grips(2.4, 2.6, 1.0)

    def test_zero_gripped_diameter_raises(self):
        with self.assertRaises(ValueError):
            sleeve_grips(2.4, 0.0, 0.05)


class TestSelectSleeve(unittest.TestCase):
    def test_workable_sleeve_is_selectable(self):
        self.assertTrue(select_sleeve(good_sleeve())["selectable"])

    def test_sleeve_too_narrow_to_fit_over_the_backshell_is_rejected(self):
        result = select_sleeve(good_sleeve(supplied_id_mm=3.6))
        self.assertFalse(result["slides_on"])
        self.assertFalse(result["selectable"])

    def test_sleeve_that_cannot_close_down_is_rejected(self):
        result = select_sleeve(good_sleeve(recovery_ratio=1.2))
        self.assertFalse(result["grips"])

    def test_both_failures_are_reported_separately(self):
        result = select_sleeve(
            good_sleeve(supplied_id_mm=3.6, recovery_ratio=1.05, smallest_gripped_diameter_mm=2.0)
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_selection_key_raises(self):
        spec = good_sleeve()
        del spec["recovery_ratio"]
        with self.assertRaises(ValueError):
            select_sleeve(spec)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            select_sleeve(["4.8"])


class TestCutLength(unittest.TestCase):
    def test_cut_length_carries_both_overlaps(self):
        self.assertAlmostEqual(required_cut_length_mm(10.0, 2.0, 0.0), 14.0, places=9)

    def test_longitudinal_shrinkage_uprates_the_cut(self):
        self.assertAlmostEqual(required_cut_length_mm(10.0, 2.0, 0.30), 20.0, places=9)

    def test_installed_length_loses_the_shrinkage(self):
        self.assertAlmostEqual(installed_length_mm(20.0, 0.30), 14.0, places=9)

    def test_cut_and_installed_are_inverses(self):
        cut = required_cut_length_mm(12.0, 1.5, 0.12)
        self.assertAlmostEqual(installed_length_mm(cut, 0.12), 15.0, places=9)

    def test_negative_overlap_raises(self):
        with self.assertRaises(ValueError):
            required_cut_length_mm(10.0, -1.0, 0.0)

    def test_full_shrinkage_raises(self):
        with self.assertRaises(ValueError):
            required_cut_length_mm(10.0, 2.0, 1.0)


class TestCoversSpan(unittest.TestCase):
    def test_generous_sleeve_covers_the_span(self):
        self.assertTrue(covers_span(16.0, 10.0, 2.0))

    def test_sleeve_exactly_long_enough_covers_the_span(self):
        self.assertTrue(covers_span(14.0, 10.0, 2.0))

    def test_last_place_shortfall_still_covers_the_span(self):
        self.assertTrue(covers_span(14.0 - 1e-12, 10.0, 2.0))

    def test_short_sleeve_does_not_cover_the_span(self):
        self.assertFalse(covers_span(11.0, 10.0, 2.0))

    def test_zero_installed_length_raises(self):
        with self.assertRaises(ValueError):
            covers_span(0.0, 10.0, 2.0)


class TestClearance(unittest.TestCase):
    def test_clearance_is_the_gap_to_the_feature(self):
        self.assertAlmostEqual(clearance_to_feature_mm(3.0, 5.0), 2.0, places=9)

    def test_sleeve_past_the_feature_gives_a_negative_clearance(self):
        self.assertAlmostEqual(clearance_to_feature_mm(6.0, 5.0), -1.0, places=9)

    def test_non_numeric_position_raises(self):
        with self.assertRaises(ValueError):
            clearance_to_feature_mm("3", 5.0)


class TestEvaluateSleeve(unittest.TestCase):
    def test_conforming_sleeve_has_no_finding(self):
        self.assertTrue(evaluate_sleeve(good_sleeve())["conforming"])

    def test_required_cut_length_is_reported(self):
        self.assertAlmostEqual(
            evaluate_sleeve(good_sleeve())["required_cut_length_mm"], 14.0 / 0.90, places=9
        )

    def test_short_cut_length_is_a_finding(self):
        result = evaluate_sleeve(good_sleeve(cut_length_mm=13.0))
        self.assertFalse(result["covers_span"])
        self.assertFalse(result["conforming"])

    def test_sleeve_crowding_a_restricted_feature_is_a_finding(self):
        result = evaluate_sleeve(good_sleeve(sleeve_end_position_mm=4.8))
        self.assertFalse(result["conforming"])

    def test_opaque_sleeve_without_an_inspection_record_is_a_finding(self):
        result = evaluate_sleeve(good_sleeve(opaque=True, joint_inspection_recorded=False))
        self.assertFalse(result["conforming"])

    def test_opaque_sleeve_with_an_inspection_record_is_accepted(self):
        result = evaluate_sleeve(good_sleeve(opaque=True, joint_inspection_recorded=True))
        self.assertTrue(result["conforming"])

    def test_unselectable_sleeve_carries_its_selection_finding(self):
        result = evaluate_sleeve(good_sleeve(supplied_id_mm=3.6))
        self.assertFalse(result["conforming"])

    def test_missing_record_key_raises(self):
        record = good_sleeve()
        del record["span_mm"]
        with self.assertRaises(ValueError):
            evaluate_sleeve(record)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_sleeve(good_sleeve(id="   "))


class TestAssessSleeving(unittest.TestCase):
    def test_clean_set_is_compliant(self):
        report = assess_sleeving([good_sleeve(id="S-1"), good_sleeve(id="S-2")])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["conforming_count"], 2)

    def test_one_bad_sleeve_fails_the_set(self):
        report = assess_sleeving([good_sleeve(id="S-1"), good_sleeve(id="S-2", cut_length_mm=12.0)])
        self.assertFalse(report["compliant"])
        self.assertEqual(report["conforming_count"], 1)

    def test_duplicate_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_sleeving([good_sleeve(id="S-1"), good_sleeve(id="S-1")])

    def test_empty_set_raises(self):
        with self.assertRaises(ValueError):
            assess_sleeving([])

    def test_string_set_raises(self):
        with self.assertRaises(ValueError):
            assess_sleeving("S-1")

    def test_findings_are_carried_up(self):
        report = assess_sleeving([good_sleeve(id="S-1", cut_length_mm=12.0)])
        self.assertTrue(report["findings"])


if __name__ == "__main__":
    unittest.main()

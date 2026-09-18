#!/usr/bin/env python3
"""Contract test for machining and finishing allowance rules (offline)."""

import copy
import unittest

from q7080_machining_and_finishing_logic import (
    PROCESS_REACHES_INTERNAL,
    PROCESS_REMOVES_STOCK,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVIEW,
    assess_machining_plan,
    bore_after_finishing,
    grade_finishing,
    grade_stock_allowance,
    required_stock_mm,
    wall_after_machining,
)

GOOD_CASE = {
    "surface_rz_um": 120.0,
    "subsurface_defect_depth_um": 80.0,
    "distortion_mm": 0.30,
    "fixture_uncertainty_mm": 0.05,
    "minimum_cut_mm": 0.20,
    "declared_stock_mm": 1.00,
    "finishing_process": "abrasive-flow",
    "surface_location": "external",
    "finishing_passes": 3,
    "finishing_per_pass_um": 15.0,
    "finishing_allowance_um": 60.0,
    "as_built_wall_mm": 3.20,
    "machined_sides": 2,
    "minimum_wall_mm": 0.80,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class RequiredStockTests(unittest.TestCase):
    def test_terms_add_into_one_required_depth(self):
        value = required_stock_mm(120.0, 80.0, 0.30, 0.05, 0.20)
        self.assertAlmostEqual(value, 0.75, places=9)

    def test_micrometre_terms_are_converted_to_millimetres(self):
        value = required_stock_mm(1000.0, 0.0, 0.0, 0.0, 0.10)
        self.assertAlmostEqual(value, 1.10, places=9)

    def test_deeper_subsurface_layer_needs_more_stock(self):
        shallow = required_stock_mm(120.0, 40.0, 0.30, 0.05, 0.20)
        deep = required_stock_mm(120.0, 240.0, 0.30, 0.05, 0.20)
        self.assertAlmostEqual(deep - shallow, 0.20, places=9)

    def test_zero_minimum_cut_rejected(self):
        with self.assertRaises(ValueError):
            required_stock_mm(120.0, 80.0, 0.30, 0.05, 0.0)

    def test_negative_distortion_rejected(self):
        with self.assertRaises(ValueError):
            required_stock_mm(120.0, 80.0, -0.30, 0.05, 0.20)

    def test_non_numeric_roughness_rejected(self):
        with self.assertRaises(ValueError):
            required_stock_mm("120", 80.0, 0.30, 0.05, 0.20)


class StockAllowanceTests(unittest.TestCase):
    def test_sufficient_stock_accepts(self):
        result = grade_stock_allowance(1.00, 0.75)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertAlmostEqual(result["margin_mm"], 0.25, places=9)

    def test_stock_exactly_on_the_requirement_accepts(self):
        required = required_stock_mm(120.0, 80.0, 0.30, 0.05, 0.20)
        result = grade_stock_allowance(0.75, required)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_short_stock_rejects(self):
        result = grade_stock_allowance(0.60, 0.75)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("as-built surface layer" in t for t in result["findings"]))

    def test_grossly_excessive_stock_is_a_review(self):
        result = grade_stock_allowance(3.00, 0.75)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_excess_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_stock_allowance(1.00, 0.75, excess_factor=0.5)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            grade_stock_allowance(1.00, 0.0)


class FinishingTests(unittest.TestCase):
    def test_removal_is_passes_times_per_pass(self):
        result = grade_finishing("abrasive-flow", "external", 3, 15.0, 60.0)
        self.assertAlmostEqual(result["removal_um"], 45.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_removal_exactly_on_the_allowance_accepts(self):
        result = grade_finishing("abrasive-flow", "external", 4, 15.0, 60.0)
        self.assertAlmostEqual(result["removal_um"], 60.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_removal_over_the_allowance_rejects(self):
        result = grade_finishing("abrasive-flow", "external", 3, 15.0, 30.0)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_tumbling_cannot_reach_an_internal_surface(self):
        result = grade_finishing("vibratory-tumbling", "internal", 2, 5.0, 60.0)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertFalse(PROCESS_REACHES_INTERNAL["vibratory-tumbling"])

    def test_abrasive_flow_does_reach_an_internal_surface(self):
        result = grade_finishing("abrasive-flow", "internal", 2, 5.0, 60.0)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_peening_removes_no_stock(self):
        result = grade_finishing("shot-peen", "external", 2, 0.0, 0.0)
        self.assertAlmostEqual(result["removal_um"], 0.0, places=9)
        self.assertFalse(PROCESS_REMOVES_STOCK["shot-peen"])

    def test_peening_with_declared_removal_is_a_review(self):
        result = grade_finishing("shot-peen", "external", 2, 10.0, 60.0)
        self.assertEqual(result["verdict"], VERDICT_REVIEW)

    def test_zero_passes_remove_nothing(self):
        result = grade_finishing("abrasive-flow", "external", 0, 15.0, 0.0)
        self.assertAlmostEqual(result["removal_um"], 0.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_unknown_process_rejected(self):
        with self.assertRaises(ValueError):
            grade_finishing("laser-polish", "external", 2, 10.0, 60.0)

    def test_negative_pass_count_rejected(self):
        with self.assertRaises(ValueError):
            grade_finishing("abrasive-flow", "external", -1, 10.0, 60.0)

    def test_unknown_surface_location_rejected(self):
        with self.assertRaises(ValueError):
            grade_finishing("abrasive-flow", "edge", 2, 10.0, 60.0)


class WallTests(unittest.TestCase):
    def test_both_sides_take_machining_and_finishing_stock(self):
        result = wall_after_machining(3.20, 1.00, 45.0, 2, 0.80)
        self.assertAlmostEqual(result["removal_per_side_mm"], 1.045, places=9)
        self.assertAlmostEqual(result["remaining_wall_mm"], 1.11, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_one_machined_side_leaves_more_wall(self):
        result = wall_after_machining(3.20, 1.00, 45.0, 1, 0.80)
        self.assertAlmostEqual(result["remaining_wall_mm"], 2.155, places=9)

    def test_wall_below_the_minimum_rejects(self):
        result = wall_after_machining(3.20, 1.00, 45.0, 2, 1.50)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_wall_consumed_entirely_rejects(self):
        result = wall_after_machining(2.00, 1.00, 45.0, 2, 0.50)
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertTrue(any("whole" in text for text in result["findings"]))

    def test_more_than_two_machined_sides_of_one_wall_rejected(self):
        with self.assertRaises(ValueError):
            wall_after_machining(3.20, 1.00, 45.0, 3, 0.80)

    def test_zero_as_built_wall_rejected(self):
        with self.assertRaises(ValueError):
            wall_after_machining(0.0, 1.00, 45.0, 2, 0.80)


class BoreTests(unittest.TestCase):
    def test_removal_opens_the_bore_on_both_sides(self):
        result = bore_after_finishing(5.00, 45.0, 0.10)
        self.assertAlmostEqual(result["growth_mm"], 0.09, places=9)
        self.assertAlmostEqual(result["final_bore_mm"], 5.09, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_growth_exactly_on_the_tolerance_accepts(self):
        result = bore_after_finishing(5.00, 50.0, 0.10)
        self.assertAlmostEqual(result["growth_mm"], 0.10, places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)

    def test_growth_past_the_tolerance_rejects(self):
        result = bore_after_finishing(5.00, 45.0, 0.05)
        self.assertEqual(result["verdict"], VERDICT_REJECT)

    def test_zero_bore_rejected(self):
        with self.assertRaises(ValueError):
            bore_after_finishing(0.0, 45.0, 0.10)


class AssessMachiningPlanTests(unittest.TestCase):
    def test_compliant_plan_accepts_with_no_findings(self):
        result = assess_machining_plan(_case())
        self.assertEqual(result["verdict"], VERDICT_ACCEPT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["driving_quantities"], [])

    def test_required_stock_is_reported(self):
        result = assess_machining_plan(_case())
        self.assertAlmostEqual(result["required_stock_mm"], 0.75, places=9)

    def test_short_stock_drives_the_verdict(self):
        result = assess_machining_plan(_case(declared_stock_mm=0.50))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("stock", result["driving_quantities"])

    def test_wall_drives_the_verdict_when_stock_eats_it(self):
        result = assess_machining_plan(_case(as_built_wall_mm=2.10))
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("wall", result["driving_quantities"])

    def test_internal_feature_is_graded_on_bore_growth_too(self):
        result = assess_machining_plan(
            _case(
                surface_location="internal",
                bore_mm=5.00,
                bore_upper_tolerance_mm=0.05,
            )
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("bore", result["driving_quantities"])

    def test_external_feature_carries_no_bore_record(self):
        result = assess_machining_plan(_case())
        self.assertIsNone(result["bore"])

    def test_unreachable_internal_finishing_drives_the_verdict(self):
        result = assess_machining_plan(
            _case(
                surface_location="internal",
                finishing_process="vibratory-tumbling",
                bore_mm=5.00,
                bore_upper_tolerance_mm=0.50,
            )
        )
        self.assertEqual(result["verdict"], VERDICT_REJECT)
        self.assertIn("finishing", result["driving_quantities"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_machining_plan("abrasive-flow")


if __name__ == "__main__":
    unittest.main()

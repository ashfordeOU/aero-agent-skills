"""
Offline stdlib unittest for overwrap_inspection_logic.py.
Run: python3 test_overwrap_inspection.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from overwrap_inspection_logic import (
    categorize_defect,
    select_ndt_method,
    assess_coverage,
    evaluate_defect_list,
    determine_inspection_result,
    InspectionError,
    COVERAGE_THRESHOLD_PCT,
    KNOWN_DEFECT_TYPES,
    KNOWN_OVERWRAP_TYPES,
)


class TestCategorizeDefect(unittest.TestCase):

    def test_void_within_acceptable_limit(self):
        self.assertEqual(categorize_defect("void", 2.0), "acceptable")

    def test_void_at_acceptable_boundary(self):
        self.assertEqual(categorize_defect("void", 3.0), "acceptable")

    def test_void_in_monitor_band(self):
        self.assertEqual(categorize_defect("void", 5.0), "monitor")

    def test_void_above_monitor_limit(self):
        self.assertEqual(categorize_defect("void", 15.0), "rejectable")

    def test_delamination_acceptable(self):
        self.assertEqual(categorize_defect("delamination", 4.9), "acceptable")

    def test_delamination_rejectable(self):
        self.assertEqual(categorize_defect("delamination", 25.0), "rejectable")

    def test_surface_scratch_at_boundary(self):
        self.assertEqual(categorize_defect("surface_scratch", 1.0), "acceptable")

    def test_surface_scratch_monitor(self):
        self.assertEqual(categorize_defect("surface_scratch", 3.0), "monitor")

    def test_fiber_breakage_zero_size_acceptable(self):
        self.assertEqual(categorize_defect("fiber_breakage", 0.0), "acceptable")

    def test_fiber_breakage_above_zero_is_monitor(self):
        self.assertEqual(categorize_defect("fiber_breakage", 1.5), "monitor")

    def test_inclusion_rejectable(self):
        self.assertEqual(categorize_defect("inclusion", 9.0), "rejectable")

    def test_unknown_defect_type_raises(self):
        with self.assertRaises(InspectionError):
            categorize_defect("crack", 1.0)

    def test_negative_size_raises(self):
        with self.assertRaises(InspectionError):
            categorize_defect("void", -0.1)

    def test_all_known_types_accepted(self):
        for dtype in KNOWN_DEFECT_TYPES:
            result = categorize_defect(dtype, 0.0)
            self.assertIn(result, {"acceptable", "monitor", "rejectable"})


class TestSelectNDTMethod(unittest.TestCase):

    def test_void_in_cfrp_includes_ultrasonic(self):
        methods = select_ndt_method("void", "cfrp")
        self.assertIn("ultrasonic", methods)

    def test_void_in_gfrp_includes_radiography(self):
        methods = select_ndt_method("void", "gfrp")
        self.assertIn("radiography", methods)

    def test_delamination_in_aramid_includes_thermography(self):
        methods = select_ndt_method("delamination", "aramid")
        self.assertIn("thermography", methods)

    def test_surface_scratch_is_visual_only(self):
        for mat in KNOWN_OVERWRAP_TYPES:
            methods = select_ndt_method("surface_scratch", mat)
            self.assertEqual(methods, ["visual"])

    def test_inclusion_in_gfrp_is_radiography_only(self):
        methods = select_ndt_method("inclusion", "gfrp")
        self.assertEqual(methods, ["radiography"])

    def test_inclusion_in_cfrp_includes_radiography_and_ultrasonic(self):
        methods = select_ndt_method("inclusion", "cfrp")
        self.assertIn("radiography", methods)
        self.assertIn("ultrasonic", methods)

    def test_fiber_breakage_cfrp_includes_visual_and_ultrasonic(self):
        methods = select_ndt_method("fiber_breakage", "cfrp")
        self.assertIn("visual", methods)
        self.assertIn("ultrasonic", methods)

    def test_unknown_overwrap_type_raises(self):
        with self.assertRaises(InspectionError):
            select_ndt_method("void", "carbon_steel")

    def test_unknown_defect_type_raises(self):
        with self.assertRaises(InspectionError):
            select_ndt_method("microcrack", "cfrp")

    def test_returns_list(self):
        result = select_ndt_method("void", "cfrp")
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)


class TestAssessCoverage(unittest.TestCase):

    def test_full_coverage_is_adequate(self):
        result = assess_coverage(100.0, 100.0)
        self.assertTrue(result["coverage_adequate"])
        self.assertAlmostEqual(result["coverage_pct"], 100.0)

    def test_coverage_below_threshold_is_inadequate(self):
        result = assess_coverage(90.0, 100.0)
        self.assertFalse(result["coverage_adequate"])
        self.assertAlmostEqual(result["coverage_pct"], 90.0)

    def test_coverage_exactly_at_threshold_is_adequate(self):
        result = assess_coverage(COVERAGE_THRESHOLD_PCT, 100.0)
        self.assertTrue(result["coverage_adequate"])

    def test_zero_inspected_area_is_inadequate(self):
        result = assess_coverage(0.0, 100.0)
        self.assertFalse(result["coverage_adequate"])
        self.assertAlmostEqual(result["coverage_pct"], 0.0)

    def test_zero_total_area_raises(self):
        with self.assertRaises(InspectionError):
            assess_coverage(0.0, 0.0)

    def test_negative_total_area_raises(self):
        with self.assertRaises(InspectionError):
            assess_coverage(50.0, -10.0)

    def test_inspected_exceeds_total_raises(self):
        with self.assertRaises(InspectionError):
            assess_coverage(110.0, 100.0)

    def test_negative_inspected_area_raises(self):
        with self.assertRaises(InspectionError):
            assess_coverage(-5.0, 100.0)

    def test_partial_coverage_fraction(self):
        result = assess_coverage(50.0, 200.0)
        self.assertAlmostEqual(result["coverage_pct"], 25.0)
        self.assertFalse(result["coverage_adequate"])


class TestEvaluateDefectList(unittest.TestCase):

    def test_empty_list_returns_accept(self):
        result = evaluate_defect_list([])
        self.assertEqual(result["status"], "accept")
        self.assertEqual(result["defects"], [])

    def test_all_acceptable_defects_returns_accept(self):
        defects = [
            {"type": "void", "size_mm": 1.0},
            {"type": "delamination", "size_mm": 2.0},
        ]
        result = evaluate_defect_list(defects)
        self.assertEqual(result["status"], "accept")

    def test_one_monitor_defect_returns_conditional(self):
        defects = [{"type": "void", "size_mm": 5.0}]
        result = evaluate_defect_list(defects)
        self.assertEqual(result["status"], "conditional")

    def test_one_rejectable_defect_returns_reject(self):
        defects = [{"type": "void", "size_mm": 20.0}]
        result = evaluate_defect_list(defects)
        self.assertEqual(result["status"], "reject")

    def test_reject_takes_precedence_over_monitor(self):
        defects = [
            {"type": "void", "size_mm": 5.0},   # monitor
            {"type": "delamination", "size_mm": 30.0},  # rejectable
        ]
        result = evaluate_defect_list(defects)
        self.assertEqual(result["status"], "reject")

    def test_defect_categories_recorded_per_entry(self):
        defects = [
            {"type": "void", "size_mm": 1.0},
            {"type": "void", "size_mm": 15.0},
        ]
        result = evaluate_defect_list(defects)
        cats = [d["category"] for d in result["defects"]]
        self.assertIn("acceptable", cats)
        self.assertIn("rejectable", cats)

    def test_malformed_entry_missing_size_raises(self):
        with self.assertRaises(InspectionError):
            evaluate_defect_list([{"type": "void"}])

    def test_malformed_entry_missing_type_raises(self):
        with self.assertRaises(InspectionError):
            evaluate_defect_list([{"size_mm": 1.0}])

    def test_non_dict_entry_raises(self):
        with self.assertRaises(InspectionError):
            evaluate_defect_list(["void"])


class TestDetermineInspectionResult(unittest.TestCase):

    def test_pass_with_acceptable_defects_and_full_coverage(self):
        defects = [{"type": "void", "size_mm": 1.0}]
        result = determine_inspection_result(defects, 98.0, 100.0)
        self.assertEqual(result["overall_result"], "pass")

    def test_fail_with_rejectable_defect_and_adequate_coverage(self):
        defects = [{"type": "delamination", "size_mm": 30.0}]
        result = determine_inspection_result(defects, 98.0, 100.0)
        self.assertEqual(result["overall_result"], "fail")

    def test_conditional_pass_with_monitor_defect_and_adequate_coverage(self):
        defects = [{"type": "void", "size_mm": 5.0}]
        result = determine_inspection_result(defects, 98.0, 100.0)
        self.assertEqual(result["overall_result"], "conditional-pass")

    def test_incomplete_when_coverage_below_threshold(self):
        defects = []
        result = determine_inspection_result(defects, 80.0, 100.0)
        self.assertEqual(result["overall_result"], "incomplete")

    def test_incomplete_takes_precedence_over_rejectable(self):
        defects = [{"type": "delamination", "size_mm": 30.0}]
        result = determine_inspection_result(defects, 50.0, 100.0)
        self.assertEqual(result["overall_result"], "incomplete")

    def test_pass_with_no_defects_and_exact_coverage_threshold(self):
        result = determine_inspection_result([], COVERAGE_THRESHOLD_PCT, 100.0)
        self.assertEqual(result["overall_result"], "pass")

    def test_result_contains_coverage_key(self):
        result = determine_inspection_result([], 100.0, 100.0)
        self.assertIn("coverage", result)
        self.assertIn("coverage_pct", result["coverage"])

    def test_result_contains_defect_summary_key(self):
        result = determine_inspection_result([], 100.0, 100.0)
        self.assertIn("defect_summary", result)

    def test_invalid_coverage_propagates_error(self):
        with self.assertRaises(InspectionError):
            determine_inspection_result([], 0.0, 0.0)


if __name__ == "__main__":
    unittest.main()

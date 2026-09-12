"""
Gate 3 contract tests for drd_stress_strength_logic.
stdlib unittest only. Offline, deterministic.
Run: python3 test_drd_stress_strength.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_stress_strength_logic import (
    analyse_element,
    apply_factor_of_safety,
    build_margin_summary,
    categorize_element,
    categorize_load_case,
    check_drd_completeness,
    check_negative_margins,
    compute_margin_of_safety,
    validate_allowable,
    DEFAULT_FOS,
    REQUIRED_DRD_SECTIONS,
    VALID_ELEMENT_TYPES,
    VALID_LOAD_TYPES,
)


class TestComputeMarginOfSafety(unittest.TestCase):

    def test_positive_margin(self):
        self.assertAlmostEqual(compute_margin_of_safety(200.0, 100.0), 1.0)

    def test_zero_margin_boundary(self):
        self.assertAlmostEqual(compute_margin_of_safety(100.0, 100.0), 0.0)

    def test_negative_margin(self):
        self.assertAlmostEqual(compute_margin_of_safety(80.0, 100.0), -0.2)

    def test_zero_design_load_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, 0.0)

    def test_negative_design_load_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, -5.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 100.0)

    def test_fractional_margin(self):
        mos = compute_margin_of_safety(150.0, 100.0)
        self.assertAlmostEqual(mos, 0.5)


class TestApplyFactorOfSafety(unittest.TestCase):

    def test_standard_ultimate_fos(self):
        self.assertAlmostEqual(apply_factor_of_safety(100.0, 1.25), 125.0)

    def test_unity_fos(self):
        self.assertAlmostEqual(apply_factor_of_safety(200.0, 1.0), 200.0)

    def test_zero_fos_raises(self):
        with self.assertRaises(ValueError):
            apply_factor_of_safety(100.0, 0.0)

    def test_negative_fos_raises(self):
        with self.assertRaises(ValueError):
            apply_factor_of_safety(100.0, -1.25)

    def test_negative_limit_load_raises(self):
        with self.assertRaises(ValueError):
            apply_factor_of_safety(-50.0, 1.25)

    def test_zero_limit_load_returns_zero(self):
        self.assertAlmostEqual(apply_factor_of_safety(0.0, 1.25), 0.0)


class TestCategorizeElement(unittest.TestCase):

    def test_metallic_accepted(self):
        self.assertEqual(categorize_element("metallic"), "metallic")

    def test_composite_accepted(self):
        self.assertEqual(categorize_element("composite"), "composite")

    def test_bonded_joint_accepted(self):
        self.assertEqual(categorize_element("bonded_joint"), "bonded_joint")

    def test_welded_joint_accepted(self):
        self.assertEqual(categorize_element("welded_joint"), "welded_joint")

    def test_fastener_accepted(self):
        self.assertEqual(categorize_element("fastener"), "fastener")

    def test_unrecognized_element_raises(self):
        with self.assertRaises(ValueError):
            categorize_element("wooden_panel")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_element("")


class TestCategorizeLoadCase(unittest.TestCase):

    def test_limit_accepted(self):
        self.assertEqual(categorize_load_case("limit"), "limit")

    def test_yield_accepted(self):
        self.assertEqual(categorize_load_case("yield"), "yield")

    def test_ultimate_accepted(self):
        self.assertEqual(categorize_load_case("ultimate"), "ultimate")

    def test_unrecognized_load_raises(self):
        with self.assertRaises(ValueError):
            categorize_load_case("extreme")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_load_case("")


class TestValidateAllowable(unittest.TestCase):

    def test_valid_metallic_ultimate(self):
        val = validate_allowable(350.0, "metallic", "ultimate")
        self.assertEqual(val, 350.0)

    def test_valid_composite_yield(self):
        val = validate_allowable(200.0, "composite", "yield")
        self.assertEqual(val, 200.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(0.0, "metallic", "yield")

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(-10.0, "fastener", "limit")

    def test_invalid_element_type_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(100.0, "ceramic", "limit")

    def test_invalid_load_type_raises(self):
        with self.assertRaises(ValueError):
            validate_allowable(100.0, "metallic", "fatigue")


class TestCheckNegativeMargins(unittest.TestCase):

    def test_detects_negative_margin(self):
        table = {"E1": 0.15, "E2": -0.05, "E3": 0.0}
        failing = check_negative_margins(table)
        self.assertIn("E2", failing)

    def test_does_not_flag_positive_margin(self):
        table = {"E1": 0.15, "E2": 0.02}
        failing = check_negative_margins(table)
        self.assertEqual(failing, [])

    def test_does_not_flag_zero_margin(self):
        # Zero MoS is marginal but not negative; not a finding here.
        table = {"E1": 0.0}
        failing = check_negative_margins(table)
        self.assertEqual(failing, [])

    def test_all_negative(self):
        table = {"E1": -0.1, "E2": -0.3}
        failing = check_negative_margins(table)
        self.assertEqual(set(failing), {"E1", "E2"})

    def test_empty_table(self):
        self.assertEqual(check_negative_margins({}), [])


class TestCheckDRDCompleteness(unittest.TestCase):

    def test_all_sections_present(self):
        missing = check_drd_completeness(list(REQUIRED_DRD_SECTIONS))
        self.assertEqual(missing, [])

    def test_detects_missing_conclusions(self):
        partial = [s for s in REQUIRED_DRD_SECTIONS if s != "conclusions"]
        missing = check_drd_completeness(partial)
        self.assertIn("conclusions", missing)

    def test_detects_missing_margins_of_safety(self):
        partial = [s for s in REQUIRED_DRD_SECTIONS if s != "margins_of_safety"]
        missing = check_drd_completeness(partial)
        self.assertIn("margins_of_safety", missing)

    def test_empty_list_flags_all(self):
        missing = check_drd_completeness([])
        self.assertEqual(len(missing), len(REQUIRED_DRD_SECTIONS))

    def test_extra_sections_ignored(self):
        sections = list(REQUIRED_DRD_SECTIONS) + ["appendix_a", "appendix_b"]
        missing = check_drd_completeness(sections)
        self.assertEqual(missing, [])


class TestAnalyseElement(unittest.TestCase):

    def test_passing_single_load_case(self):
        load_cases = [
            {"load_type": "ultimate", "applied_stress": 100.0,
             "allowable_stress": 200.0, "fos": 1.25},
        ]
        result = analyse_element("SPAR_01", "metallic", load_cases)
        self.assertEqual(result["overall"], "pass")
        self.assertGreater(result["results"][0]["mos"], 0.0)

    def test_failing_single_load_case(self):
        # design_stress = 200 × 1.25 = 250 > allowable 200 → MoS < 0
        load_cases = [
            {"load_type": "ultimate", "applied_stress": 200.0,
             "allowable_stress": 200.0, "fos": 1.25},
        ]
        result = analyse_element("SPAR_02", "metallic", load_cases)
        self.assertEqual(result["overall"], "fail")
        self.assertLess(result["results"][0]["mos"], 0.0)

    def test_worst_case_governs_overall(self):
        # yield load case passes; ultimate load case fails
        load_cases = [
            {"load_type": "yield", "applied_stress": 50.0,
             "allowable_stress": 200.0, "fos": 1.0},
            {"load_type": "ultimate", "applied_stress": 180.0,
             "allowable_stress": 200.0, "fos": 1.25},
        ]
        result = analyse_element("PANEL_01", "composite", load_cases)
        self.assertEqual(result["overall"], "fail")

    def test_default_fos_applied_when_omitted(self):
        load_cases = [
            {"load_type": "ultimate", "applied_stress": 100.0,
             "allowable_stress": 200.0},
        ]
        result = analyse_element("RIB_01", "metallic", load_cases)
        expected_design = 100.0 * DEFAULT_FOS["ultimate"]
        expected_mos = round((200.0 / expected_design) - 1.0, 6)
        self.assertAlmostEqual(result["results"][0]["mos"], expected_mos)

    def test_invalid_element_type_raises(self):
        with self.assertRaises(ValueError):
            analyse_element("X", "unknown_material", [
                {"load_type": "limit", "applied_stress": 10.0,
                 "allowable_stress": 20.0, "fos": 1.0}
            ])

    def test_invalid_load_type_raises(self):
        with self.assertRaises(ValueError):
            analyse_element("X", "metallic", [
                {"load_type": "crash", "applied_stress": 10.0,
                 "allowable_stress": 20.0, "fos": 1.0}
            ])

    def test_result_contains_expected_keys(self):
        load_cases = [
            {"load_type": "limit", "applied_stress": 50.0,
             "allowable_stress": 100.0, "fos": 1.0},
        ]
        result = analyse_element("BRACKET_01", "fastener", load_cases)
        for key in ("element_id", "element_type", "results", "overall"):
            self.assertIn(key, result)
        for key in ("load_type", "design_stress", "allowable_stress", "mos", "status"):
            self.assertIn(key, result["results"][0])


class TestBuildMarginSummary(unittest.TestCase):

    def test_summary_contains_all_elements(self):
        analyses = [
            {"element_id": "E1", "element_type": "metallic",
             "results": [{"mos": 0.2, "status": "pass"}], "overall": "pass"},
            {"element_id": "E2", "element_type": "composite",
             "results": [{"mos": -0.05, "status": "fail"}], "overall": "fail"},
        ]
        summary, failing = build_margin_summary(analyses)
        self.assertIn("E1", summary)
        self.assertIn("E2", summary)

    def test_failing_list_correct(self):
        analyses = [
            {"element_id": "E1", "element_type": "metallic",
             "results": [{"mos": 0.2, "status": "pass"}], "overall": "pass"},
            {"element_id": "E2", "element_type": "composite",
             "results": [{"mos": -0.05, "status": "fail"}], "overall": "fail"},
        ]
        _, failing = build_margin_summary(analyses)
        self.assertIn("E2", failing)
        self.assertNotIn("E1", failing)

    def test_minimum_mos_selected(self):
        analyses = [
            {"element_id": "E1", "element_type": "metallic",
             "results": [{"mos": 0.4, "status": "pass"},
                         {"mos": 0.1, "status": "pass"}],
             "overall": "pass"},
        ]
        summary, _ = build_margin_summary(analyses)
        self.assertAlmostEqual(summary["E1"], 0.1)

    def test_empty_analyses_returns_empty(self):
        summary, failing = build_margin_summary([])
        self.assertEqual(summary, {})
        self.assertEqual(failing, [])

    def test_element_with_no_results_skipped(self):
        analyses = [
            {"element_id": "E1", "element_type": "metallic",
             "results": [], "overall": "pass"},
        ]
        summary, _ = build_margin_summary(analyses)
        self.assertNotIn("E1", summary)


class TestConstantsIntegrity(unittest.TestCase):

    def test_default_fos_ultimate_is_1_25(self):
        self.assertAlmostEqual(DEFAULT_FOS["ultimate"], 1.25)

    def test_required_sections_non_empty(self):
        self.assertGreater(len(REQUIRED_DRD_SECTIONS), 0)

    def test_valid_element_types_non_empty(self):
        self.assertGreater(len(VALID_ELEMENT_TYPES), 0)

    def test_valid_load_types_contains_three(self):
        self.assertEqual(len(VALID_LOAD_TYPES), 3)


if __name__ == "__main__":
    unittest.main()

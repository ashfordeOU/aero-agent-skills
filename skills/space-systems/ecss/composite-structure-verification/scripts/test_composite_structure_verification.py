"""
Gate 3 contract tests for composite-structure-verification.
stdlib unittest only — offline, deterministic. 10+ tests.
Run: python3 test_composite_structure_verification.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from composite_structure_verification_logic import (
    check_allowable_basis,
    check_knock_down_factors,
    check_failure_mode_coverage,
    check_environment_conditioning,
    check_ndt_coverage,
    check_test_pyramid,
    run_composite_verification,
    REQUIRED_FAILURE_MODES,
    MANDATORY_TEST_LEVELS,
)


# ---------------------------------------------------------------------------
# allowable basis
# ---------------------------------------------------------------------------

class TestAllowableBasis(unittest.TestCase):

    def test_a_basis_for_primary_passes(self):
        allowables = [{"id": "AL-01", "basis": "A_basis", "structure_category": "primary"}]
        result = check_allowable_basis(allowables)
        self.assertTrue(result["pass"])
        self.assertEqual(result["findings"], [])

    def test_b_basis_for_redundant_passes(self):
        allowables = [{"id": "AL-02", "basis": "B_basis", "structure_category": "secondary"}]
        result = check_allowable_basis(allowables)
        self.assertTrue(result["pass"])

    def test_b_basis_for_primary_fails(self):
        allowables = [{"id": "AL-03", "basis": "B_basis", "structure_category": "primary"}]
        result = check_allowable_basis(allowables)
        self.assertFalse(result["pass"])
        self.assertTrue(any("A_basis" in f["issue"] for f in result["findings"]))

    def test_missing_basis_field_fails(self):
        allowables = [{"id": "AL-04", "structure_category": "secondary"}]
        result = check_allowable_basis(allowables)
        self.assertFalse(result["pass"])
        self.assertTrue(any("not specified" in f["issue"] for f in result["findings"]))

    def test_invalid_basis_string_fails(self):
        allowables = [{"id": "AL-05", "basis": "mean_value", "structure_category": "secondary"}]
        result = check_allowable_basis(allowables)
        self.assertFalse(result["pass"])
        self.assertTrue(any("invalid allowable basis" in f["issue"] for f in result["findings"]))

    def test_empty_list_passes(self):
        result = check_allowable_basis([])
        self.assertTrue(result["pass"])

    def test_non_list_raises(self):
        with self.assertRaises(TypeError):
            check_allowable_basis("not-a-list")


# ---------------------------------------------------------------------------
# knock-down factors
# ---------------------------------------------------------------------------

class TestKnockDownFactors(unittest.TestCase):

    def test_all_three_kdfs_present_passes(self):
        allowables = [{"id": "KD-01", "knock_down_factors": ["temperature", "moisture", "scatter"]}]
        result = check_knock_down_factors(allowables)
        self.assertTrue(result["pass"])

    def test_missing_moisture_kdf_fails(self):
        allowables = [{"id": "KD-02", "knock_down_factors": ["temperature", "scatter"]}]
        result = check_knock_down_factors(allowables)
        self.assertFalse(result["pass"])
        self.assertTrue(any("moisture" in f["issue"] for f in result["findings"]))

    def test_missing_scatter_kdf_fails(self):
        allowables = [{"id": "KD-03", "knock_down_factors": ["temperature", "moisture"]}]
        result = check_knock_down_factors(allowables)
        self.assertFalse(result["pass"])
        self.assertTrue(any("scatter" in f["issue"] for f in result["findings"]))

    def test_no_kdfs_fails_with_all_three_missing(self):
        allowables = [{"id": "KD-04", "knock_down_factors": []}]
        result = check_knock_down_factors(allowables)
        self.assertFalse(result["pass"])
        issue = result["findings"][0]["issue"]
        for factor in ["temperature", "moisture", "scatter"]:
            self.assertIn(factor, issue)


# ---------------------------------------------------------------------------
# failure mode coverage
# ---------------------------------------------------------------------------

class TestFailureModeCoverage(unittest.TestCase):

    def test_all_four_modes_passes(self):
        modes = ["fiber_failure", "matrix_cracking", "delamination", "interlaminar_shear"]
        result = check_failure_mode_coverage(modes)
        self.assertTrue(result["pass"])

    def test_missing_delamination_fails(self):
        modes = ["fiber_failure", "matrix_cracking", "interlaminar_shear"]
        result = check_failure_mode_coverage(modes)
        self.assertFalse(result["pass"])
        self.assertTrue(any("delamination" in f["issue"] for f in result["findings"]))

    def test_unrecognized_mode_label_flagged(self):
        modes = list(REQUIRED_FAILURE_MODES) + ["buckling"]
        result = check_failure_mode_coverage(modes)
        self.assertFalse(result["pass"])
        self.assertTrue(any("unrecognized" in f["issue"] for f in result["findings"]))

    def test_empty_list_fails_with_all_modes_missing(self):
        result = check_failure_mode_coverage([])
        self.assertFalse(result["pass"])
        issues = " ".join(f["issue"] for f in result["findings"])
        for mode in REQUIRED_FAILURE_MODES:
            self.assertIn(mode, issues)


# ---------------------------------------------------------------------------
# environment conditioning
# ---------------------------------------------------------------------------

class TestEnvironmentConditioning(unittest.TestCase):

    def test_matching_conditioning_passes(self):
        articles = [{
            "id": "TA-01",
            "conditioning_state": "hot_wet",
            "design_env_condition": "hot_wet",
        }]
        result = check_environment_conditioning(articles)
        self.assertTrue(result["pass"])

    def test_conditioning_mismatch_fails(self):
        articles = [{
            "id": "TA-02",
            "conditioning_state": "room_temperature_dry",
            "design_env_condition": "hot_wet",
        }]
        result = check_environment_conditioning(articles)
        self.assertFalse(result["pass"])
        self.assertTrue(any("mismatch" in f["issue"] for f in result["findings"]))

    def test_invalid_conditioning_state_fails(self):
        articles = [{
            "id": "TA-03",
            "conditioning_state": "ambient",
            "design_env_condition": "hot_wet",
        }]
        result = check_environment_conditioning(articles)
        self.assertFalse(result["pass"])
        self.assertTrue(any("not in valid set" in f["issue"] for f in result["findings"]))

    def test_missing_design_env_fails(self):
        articles = [{"id": "TA-04", "conditioning_state": "hot_wet"}]
        result = check_environment_conditioning(articles)
        self.assertFalse(result["pass"])
        self.assertTrue(any("design_env_condition not specified" in f["issue"]
                            for f in result["findings"]))


# ---------------------------------------------------------------------------
# NDT coverage
# ---------------------------------------------------------------------------

class TestNdtCoverage(unittest.TestCase):

    def test_primary_part_fully_covered_passes(self):
        parts = [{"id": "P-01", "category": "primary"}]
        ndt = [{"part_id": "P-01", "method": "ultrasonic_c_scan", "critical_defect_size_mm": 1.0}]
        result = check_ndt_coverage(ndt, parts)
        self.assertTrue(result["pass"])

    def test_primary_part_missing_from_ndt_plan_fails(self):
        parts = [{"id": "P-02", "category": "primary"}]
        ndt = []
        result = check_ndt_coverage(ndt, parts)
        self.assertFalse(result["pass"])
        self.assertTrue(any("no NDT plan entry" in f["issue"] for f in result["findings"]))

    def test_invalid_ndt_method_fails(self):
        parts = [{"id": "P-03", "category": "primary"}]
        ndt = [{"part_id": "P-03", "method": "visual_only", "critical_defect_size_mm": 2.0}]
        result = check_ndt_coverage(ndt, parts)
        self.assertFalse(result["pass"])
        self.assertTrue(any("not in approved set" in f["issue"] for f in result["findings"]))

    def test_missing_critical_defect_size_fails(self):
        parts = [{"id": "P-04", "category": "secondary"}]
        ndt = [{"part_id": "P-04", "method": "thermography"}]
        result = check_ndt_coverage(ndt, parts)
        self.assertFalse(result["pass"])
        self.assertTrue(any("critical_defect_size_mm" in f["issue"] for f in result["findings"]))

    def test_tertiary_part_not_required_in_ndt_passes(self):
        parts = [{"id": "P-05", "category": "tertiary"}]
        ndt = []
        result = check_ndt_coverage(ndt, parts)
        self.assertTrue(result["pass"])

    def test_unknown_category_flagged(self):
        parts = [{"id": "P-06", "category": "cosmetic"}]
        ndt = []
        result = check_ndt_coverage(ndt, parts)
        self.assertFalse(result["pass"])
        self.assertTrue(any("unknown structure category" in f["issue"] for f in result["findings"]))


# ---------------------------------------------------------------------------
# test pyramid
# ---------------------------------------------------------------------------

class TestTestPyramid(unittest.TestCase):

    def test_coupon_and_component_present_passes(self):
        articles = [
            {"id": "T-01", "test_level": "coupon"},
            {"id": "T-02", "test_level": "component"},
        ]
        result = check_test_pyramid(articles)
        self.assertTrue(result["pass"])
        self.assertIn("coupon", result["levels_present"])
        self.assertIn("component", result["levels_present"])

    def test_all_four_levels_passes(self):
        articles = [
            {"test_level": "coupon"},
            {"test_level": "element"},
            {"test_level": "sub_component"},
            {"test_level": "component"},
        ]
        result = check_test_pyramid(articles)
        self.assertTrue(result["pass"])

    def test_missing_component_level_fails(self):
        articles = [{"test_level": "coupon"}, {"test_level": "element"}]
        result = check_test_pyramid(articles)
        self.assertFalse(result["pass"])
        self.assertTrue(any("component" in f["issue"] for f in result["findings"]))

    def test_missing_coupon_level_fails(self):
        articles = [{"test_level": "component"}]
        result = check_test_pyramid(articles)
        self.assertFalse(result["pass"])
        self.assertTrue(any("coupon" in f["issue"] for f in result["findings"]))

    def test_unknown_level_label_ignored_in_mandatory_check(self):
        articles = [
            {"test_level": "coupon"},
            {"test_level": "prototype"},
            {"test_level": "component"},
        ]
        result = check_test_pyramid(articles)
        self.assertTrue(result["pass"])
        self.assertNotIn("prototype", result["levels_present"])


# ---------------------------------------------------------------------------
# top-level run_composite_verification
# ---------------------------------------------------------------------------

class TestRunCompositeVerification(unittest.TestCase):

    def _good_spec(self):
        return {
            "allowables": [
                {
                    "id": "A1",
                    "basis": "A_basis",
                    "structure_category": "primary",
                    "knock_down_factors": ["temperature", "moisture", "scatter"],
                },
                {
                    "id": "A2",
                    "basis": "B_basis",
                    "structure_category": "secondary",
                    "knock_down_factors": ["temperature", "moisture", "scatter"],
                },
            ],
            "failure_modes_analyzed": [
                "fiber_failure", "matrix_cracking", "delamination", "interlaminar_shear"
            ],
            "test_articles": [
                {
                    "id": "TA1",
                    "test_level": "coupon",
                    "conditioning_state": "hot_wet",
                    "design_env_condition": "hot_wet",
                },
                {
                    "id": "TA2",
                    "test_level": "component",
                    "conditioning_state": "hot_wet",
                    "design_env_condition": "hot_wet",
                },
            ],
            "ndt_plan": [
                {
                    "part_id": "PP1",
                    "method": "ultrasonic_c_scan",
                    "critical_defect_size_mm": 1.5,
                },
            ],
            "structure_parts": [
                {"id": "PP1", "category": "primary"},
            ],
        }

    def test_full_compliant_spec_passes(self):
        result = run_composite_verification(self._good_spec())
        self.assertTrue(result["pass"])
        for name, check in result["checks"].items():
            self.assertTrue(check["pass"], f"check '{name}' failed: {check['findings']}")

    def test_invalid_spec_type_raises(self):
        with self.assertRaises(TypeError):
            run_composite_verification("bad input")

    def test_non_compliant_allowable_basis_fails_overall(self):
        spec = self._good_spec()
        spec["allowables"][0]["basis"] = "B_basis"
        result = run_composite_verification(spec)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["allowable_basis"]["pass"])

    def test_missing_failure_mode_fails_overall(self):
        spec = self._good_spec()
        spec["failure_modes_analyzed"] = ["fiber_failure", "matrix_cracking"]
        result = run_composite_verification(spec)
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["failure_mode_coverage"]["pass"])

    def test_empty_spec_fails_on_failure_modes_and_pyramid(self):
        result = run_composite_verification({})
        self.assertFalse(result["pass"])
        self.assertFalse(result["checks"]["failure_mode_coverage"]["pass"])
        self.assertFalse(result["checks"]["test_pyramid"]["pass"])


if __name__ == "__main__":
    unittest.main()

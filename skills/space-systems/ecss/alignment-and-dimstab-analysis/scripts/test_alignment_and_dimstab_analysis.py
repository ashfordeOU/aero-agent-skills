#!/usr/bin/env python3
"""Gate 3 contract tests for alignment_and_dimstab_analysis_logic.
stdlib unittest only — offline, deterministic.
Run: python3 test_alignment_and_dimstab_analysis.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import alignment_and_dimstab_analysis_logic as logic


class TestCategorizeContributor(unittest.TestCase):

    def test_manufacturing_tolerance_is_systematic(self):
        self.assertEqual(logic.categorize_contributor("manufacturing_tolerance"), "systematic")

    def test_thermo_elastic_is_random(self):
        self.assertEqual(logic.categorize_contributor("thermo_elastic"), "random")

    def test_hygrothermal_is_random(self):
        self.assertEqual(logic.categorize_contributor("hygrothermal"), "random")

    def test_load_induced_is_random(self):
        self.assertEqual(logic.categorize_contributor("load_induced"), "random")

    def test_creep_is_random(self):
        self.assertEqual(logic.categorize_contributor("creep"), "random")

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.categorize_contributor("vibration_induced")


class TestThermoElasticDeformation(unittest.TestCase):

    def test_basic_calculation(self):
        # α=2e-6 /K, L=1.0 m, ΔT=100 K → ΔL = 2e-4 m
        result = logic.thermo_elastic_deformation(2e-6, 1.0, 100.0)
        self.assertAlmostEqual(result, 2e-4, places=10)

    def test_zero_delta_T_gives_zero(self):
        result = logic.thermo_elastic_deformation(5e-6, 2.0, 0.0)
        self.assertEqual(result, 0.0)

    def test_negative_delta_T_returns_absolute_value(self):
        result = logic.thermo_elastic_deformation(2e-6, 1.0, -100.0)
        self.assertAlmostEqual(result, 2e-4, places=10)

    def test_negative_cte_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.thermo_elastic_deformation(-1e-6, 1.0, 50.0)

    def test_zero_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.thermo_elastic_deformation(2e-6, 0.0, 50.0)

    def test_negative_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.thermo_elastic_deformation(2e-6, -1.0, 50.0)


class TestHygrothermalDeformation(unittest.TestCase):

    def test_basic_calculation(self):
        # CME=0.3e-3, Δm=0.01 kg/kg, L=0.5 m → ΔL = 1.5e-6 m
        result = logic.hygrothermal_deformation(0.3e-3, 0.5, 0.01)
        self.assertAlmostEqual(result, 1.5e-6, places=12)

    def test_zero_moisture_gives_zero(self):
        result = logic.hygrothermal_deformation(0.3e-3, 1.0, 0.0)
        self.assertEqual(result, 0.0)

    def test_negative_cme_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.hygrothermal_deformation(-0.1e-3, 1.0, 0.01)

    def test_zero_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.hygrothermal_deformation(0.3e-3, 0.0, 0.01)

    def test_negative_moisture_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.hygrothermal_deformation(0.3e-3, 1.0, -0.005)


class TestLateralDeformationToArcsec(unittest.TestCase):

    def test_known_value(self):
        # ΔL=0.001 m, L=1.0 m → θ=atan(0.001) rad ≈ 0.057296 deg → 206.26 arcsec
        result = logic.lateral_deformation_to_arcsec(0.001, 1.0)
        expected = math.degrees(math.atan(0.001)) * 3600.0
        self.assertAlmostEqual(result, expected, places=6)

    def test_zero_deformation_gives_zero(self):
        result = logic.lateral_deformation_to_arcsec(0.0, 1.0)
        self.assertAlmostEqual(result, 0.0, places=10)

    def test_zero_baseline_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.lateral_deformation_to_arcsec(0.001, 0.0)

    def test_negative_deformation_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.lateral_deformation_to_arcsec(-0.001, 1.0)


class TestCombineAlignmentBudget(unittest.TestCase):

    def test_systematic_only(self):
        contributors = [
            {"source_type": "manufacturing_tolerance", "value_arcsec": 10.0},
            {"source_type": "manufacturing_tolerance", "value_arcsec": 5.0},
        ]
        result = logic.combine_alignment_budget(contributors)
        self.assertAlmostEqual(result["systematic_sum"], 15.0)
        self.assertAlmostEqual(result["random_rss"], 0.0)
        self.assertAlmostEqual(result["total"], 15.0)

    def test_random_only_rss(self):
        # 3-4-5 right triangle: sqrt(9+16) = 5
        contributors = [
            {"source_type": "thermo_elastic", "value_arcsec": 3.0},
            {"source_type": "hygrothermal", "value_arcsec": 4.0},
        ]
        result = logic.combine_alignment_budget(contributors)
        self.assertAlmostEqual(result["random_rss"], 5.0, places=10)
        self.assertAlmostEqual(result["systematic_sum"], 0.0)
        self.assertAlmostEqual(result["total"], 5.0, places=10)

    def test_mixed_systematic_and_random(self):
        # mfg=10, thermo=3, hygro=4 → total = 10 + sqrt(9+16) = 15
        contributors = [
            {"source_type": "manufacturing_tolerance", "value_arcsec": 10.0},
            {"source_type": "thermo_elastic", "value_arcsec": 3.0},
            {"source_type": "hygrothermal", "value_arcsec": 4.0},
        ]
        result = logic.combine_alignment_budget(contributors)
        self.assertAlmostEqual(result["total"], 15.0, places=10)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.combine_alignment_budget([])

    def test_negative_value_raises_value_error(self):
        with self.assertRaises(ValueError):
            logic.combine_alignment_budget(
                [{"source_type": "thermo_elastic", "value_arcsec": -1.0}]
            )

    def test_all_random_types_accepted(self):
        contributors = [
            {"source_type": "thermo_elastic", "value_arcsec": 1.0},
            {"source_type": "hygrothermal", "value_arcsec": 1.0},
            {"source_type": "load_induced", "value_arcsec": 1.0},
            {"source_type": "creep", "value_arcsec": 1.0},
        ]
        result = logic.combine_alignment_budget(contributors)
        self.assertAlmostEqual(result["random_rss"], 2.0, places=10)  # sqrt(4)


class TestAlignmentBudgetViolations(unittest.TestCase):

    def _contributors(self):
        return [
            {"source_type": "manufacturing_tolerance", "value_arcsec": 5.0},
            {"source_type": "thermo_elastic", "value_arcsec": 3.0},
        ]

    def test_compliant_interface_returns_empty(self):
        # total = 5 + 3 = 8 <= 20
        violations = logic.alignment_budget_violations("IF-01", self._contributors(), 20.0)
        self.assertEqual(violations, [])

    def test_budget_exceeded_returns_violation(self):
        # total = 5 + 3 = 8 > 6
        violations = logic.alignment_budget_violations("IF-02", self._contributors(), 6.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "alignment_budget_exceeded")
        self.assertEqual(violations[0]["interface"], "IF-02")
        self.assertAlmostEqual(violations[0]["margin_arcsec"], 6.0 - 8.0, places=10)

    def test_none_budget_returns_missing_requirement_violation(self):
        violations = logic.alignment_budget_violations("IF-03", self._contributors(), None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_or_invalid_alignment_budget")

    def test_zero_budget_returns_invalid_budget_violation(self):
        violations = logic.alignment_budget_violations("IF-04", self._contributors(), 0.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_or_invalid_alignment_budget")

    def test_is_element_compliant_true_for_empty_list(self):
        self.assertTrue(logic.is_element_compliant([]))

    def test_is_element_compliant_false_for_violation(self):
        self.assertFalse(logic.is_element_compliant([{"issue": "something"}]))


class TestCheckThermalCaseCoverage(unittest.TestCase):

    def test_all_cases_present_returns_covered(self):
        result = logic.check_thermal_case_coverage(
            ["hot_case", "cold_case", "eclipse", "nominal"]
        )
        self.assertTrue(result["covered"])
        self.assertEqual(result["missing"], [])

    def test_eclipse_missing_returns_not_covered(self):
        result = logic.check_thermal_case_coverage(["hot_case", "cold_case"])
        self.assertFalse(result["covered"])
        self.assertIn("eclipse", result["missing"])

    def test_all_cases_missing_returns_three_missing(self):
        result = logic.check_thermal_case_coverage(["nominal"])
        self.assertFalse(result["covered"])
        self.assertEqual(len(result["missing"]), 3)

    def test_empty_set_reports_all_missing(self):
        result = logic.check_thermal_case_coverage([])
        self.assertFalse(result["covered"])
        self.assertEqual(sorted(result["missing"]), ["cold_case", "eclipse", "hot_case"])

    def test_missing_list_is_sorted(self):
        result = logic.check_thermal_case_coverage(["hot_case"])
        self.assertEqual(result["missing"], sorted(result["missing"]))


class TestDimStabViolations(unittest.TestCase):

    def _base_params(self):
        return dict(
            cte_per_K=2e-6,
            length_m=1.0,
            delta_T_K=100.0,
            cme=0.3e-3,
            delta_moisture=0.01,
            allowable_delta_m=1e-3,
        )

    def test_compliant_element_returns_empty(self):
        # te = 2e-6 * 1.0 * 100 = 2e-4
        # hy = 0.3e-3 * 0.01 * 1.0 = 3e-6
        # total = 2.03e-4 <= 1e-3 → compliant
        p = self._base_params()
        violations = logic.dimstab_violations("BEAM-01", **p)
        self.assertEqual(violations, [])

    def test_exceeded_allowable_returns_violation(self):
        p = self._base_params()
        p["allowable_delta_m"] = 1e-5  # too tight
        violations = logic.dimstab_violations("BEAM-02", **p)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "dimstab_allowable_exceeded")
        self.assertLess(violations[0]["margin_m"], 0)

    def test_none_allowable_returns_missing_requirement(self):
        p = self._base_params()
        p["allowable_delta_m"] = None
        violations = logic.dimstab_violations("BEAM-03", **p)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_or_invalid_dimstab_allowable")

    def test_zero_allowable_returns_invalid_requirement(self):
        p = self._base_params()
        p["allowable_delta_m"] = 0.0
        violations = logic.dimstab_violations("BEAM-04", **p)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_or_invalid_dimstab_allowable")

    def test_violation_reports_te_and_hy_components(self):
        p = self._base_params()
        p["allowable_delta_m"] = 1e-5
        violations = logic.dimstab_violations("BEAM-05", **p)
        v = violations[0]
        expected_te = logic.thermo_elastic_deformation(p["cte_per_K"], p["length_m"], p["delta_T_K"])
        expected_hy = logic.hygrothermal_deformation(p["cme"], p["length_m"], p["delta_moisture"])
        self.assertAlmostEqual(v["thermo_elastic_delta_m"], expected_te, places=12)
        self.assertAlmostEqual(v["hygrothermal_delta_m"], expected_hy, places=12)
        self.assertAlmostEqual(v["total_delta_m"], expected_te + expected_hy, places=12)

    def test_zero_moisture_change_uses_only_thermo_elastic(self):
        p = self._base_params()
        p["delta_moisture"] = 0.0
        p["allowable_delta_m"] = 1e-5  # tight so we get a violation with components
        violations = logic.dimstab_violations("BEAM-06", **p)
        v = violations[0]
        self.assertAlmostEqual(v["hygrothermal_delta_m"], 0.0)
        expected_te = logic.thermo_elastic_deformation(p["cte_per_K"], p["length_m"], p["delta_T_K"])
        self.assertAlmostEqual(v["total_delta_m"], expected_te, places=12)


if __name__ == "__main__":
    unittest.main()

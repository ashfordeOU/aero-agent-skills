"""
Gate-3 contract tests for e1012_dose_effects_logic.
Offline, deterministic, stdlib unittest only.
Run: python3 test_e1012_dose_effects.py
"""

import unittest
from e1012_dose_effects_logic import (
    apply_dose_margin,
    check_dose_tolerance,
    check_parametric_degradation,
    check_functional_degradation,
    assess_component,
    DEFAULT_RADIATION_DESIGN_MARGIN,
)


class TestApplyDoseMargin(unittest.TestCase):

    def test_standard_margin_applied(self):
        result = apply_dose_margin(10.0)
        self.assertAlmostEqual(result, 20.0)

    def test_custom_margin(self):
        result = apply_dose_margin(5.0, radiation_design_margin=3.0)
        self.assertAlmostEqual(result, 15.0)

    def test_zero_dose_yields_zero(self):
        result = apply_dose_margin(0.0)
        self.assertAlmostEqual(result, 0.0)

    def test_negative_dose_raises(self):
        with self.assertRaises(ValueError):
            apply_dose_margin(-1.0)

    def test_zero_margin_raises(self):
        with self.assertRaises(ValueError):
            apply_dose_margin(10.0, radiation_design_margin=0.0)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            apply_dose_margin(10.0, radiation_design_margin=-2.0)


class TestCheckDoseTolerance(unittest.TestCase):

    def test_component_passes_margin(self):
        result = check_dose_tolerance(10.0, 25.0)
        self.assertTrue(result["margin_met"])
        self.assertAlmostEqual(result["required_tolerance_krad"], 20.0)
        self.assertAlmostEqual(result["achieved_margin_ratio"], 2.5)

    def test_component_fails_margin(self):
        result = check_dose_tolerance(10.0, 15.0)
        self.assertFalse(result["margin_met"])
        self.assertAlmostEqual(result["required_tolerance_krad"], 20.0)

    def test_exact_margin_boundary_passes(self):
        result = check_dose_tolerance(10.0, 20.0)
        self.assertTrue(result["margin_met"])

    def test_zero_predicted_dose_gives_inf_ratio(self):
        result = check_dose_tolerance(0.0, 5.0)
        self.assertTrue(result["margin_met"])
        self.assertEqual(result["achieved_margin_ratio"], float("inf"))

    def test_negative_component_tolerance_raises(self):
        with self.assertRaises(ValueError):
            check_dose_tolerance(10.0, -1.0)

    def test_custom_rdm_applied(self):
        result = check_dose_tolerance(10.0, 25.0, radiation_design_margin=3.0)
        self.assertFalse(result["margin_met"])
        self.assertAlmostEqual(result["required_tolerance_krad"], 30.0)


class TestCheckParametricDegradation(unittest.TestCase):

    def test_within_limit(self):
        result = check_parametric_degradation("gain", 100.0, 115.0, 0.20)
        self.assertTrue(result["within_limit"])
        self.assertAlmostEqual(result["change_fraction"], 0.15)

    def test_exceeds_limit(self):
        result = check_parametric_degradation("leakage_current", 1.0, 1.5, 0.30)
        self.assertFalse(result["within_limit"])
        self.assertAlmostEqual(result["change_fraction"], 0.50)

    def test_at_exact_limit_passes(self):
        result = check_parametric_degradation("vth", 2.0, 2.4, 0.20)
        self.assertTrue(result["within_limit"])
        self.assertAlmostEqual(result["change_fraction"], 0.20)

    def test_negative_degradation_uses_abs(self):
        result = check_parametric_degradation("gain", 100.0, 85.0, 0.20)
        self.assertTrue(result["within_limit"])
        self.assertAlmostEqual(result["change_fraction"], 0.15)

    def test_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            check_parametric_degradation("param", 0.0, 1.0, 0.10)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            check_parametric_degradation("param", 1.0, 1.1, -0.05)


class TestCheckFunctionalDegradation(unittest.TestCase):

    def test_functional_pass_recorded(self):
        result = check_functional_degradation("U1", True, 20.0)
        self.assertTrue(result["functionally_passes"])
        self.assertEqual(result["component_id"], "U1")
        self.assertAlmostEqual(result["required_tolerance_krad"], 20.0)

    def test_functional_fail_recorded(self):
        result = check_functional_degradation("U2", False, 30.0)
        self.assertFalse(result["functionally_passes"])


class TestAssessComponent(unittest.TestCase):

    def test_fully_compliant_component(self):
        pc = check_parametric_degradation("gain", 100.0, 108.0, 0.20)
        result = assess_component("R1", 10.0, 25.0, parametric_checks=[pc],
                                  functional_pass=True)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_fails_dose_margin(self):
        result = assess_component("C1", 10.0, 15.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("C1", result["findings"][0])

    def test_fails_parametric_limit(self):
        pc = check_parametric_degradation("leakage", 1.0, 2.0, 0.50)
        result = assess_component("Q1", 10.0, 25.0, parametric_checks=[pc],
                                  functional_pass=True)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["parametric_findings"]), 1)

    def test_fails_functional(self):
        result = assess_component("U3", 10.0, 25.0, functional_pass=False)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("functional" in f for f in result["findings"]))

    def test_no_parametric_checks_is_valid(self):
        result = assess_component("U4", 5.0, 15.0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["parametric_findings"], [])

    def test_default_rdm_constant(self):
        self.assertEqual(DEFAULT_RADIATION_DESIGN_MARGIN, 2.0)

    def test_multiple_parametric_failures_all_reported(self):
        pc1 = check_parametric_degradation("gain", 100.0, 60.0, 0.20)
        pc2 = check_parametric_degradation("vth", 1.0, 2.0, 0.20)
        result = assess_component("U5", 10.0, 25.0, parametric_checks=[pc1, pc2])
        self.assertEqual(len(result["parametric_findings"]), 2)
        self.assertFalse(result["compliant"])


if __name__ == "__main__":
    unittest.main()

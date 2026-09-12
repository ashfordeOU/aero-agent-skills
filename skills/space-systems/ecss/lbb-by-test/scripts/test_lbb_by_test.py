"""
Gate 3 contract tests for lbb_by_test_logic.py.
stdlib unittest only — offline, deterministic.
Run: python3 test_lbb_by_test.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import lbb_by_test_logic as logic


class TestCheckLbbCondition(unittest.TestCase):

    def test_lbb_met_when_through_wall_shorter_than_critical(self):
        self.assertTrue(logic.check_lbb_condition(50.0, 20.0))

    def test_lbb_not_met_when_through_wall_equals_critical(self):
        self.assertFalse(logic.check_lbb_condition(30.0, 30.0))

    def test_lbb_not_met_when_through_wall_longer_than_critical(self):
        self.assertFalse(logic.check_lbb_condition(25.0, 40.0))

    def test_check_lbb_condition_raises_on_zero_critical(self):
        with self.assertRaises(ValueError):
            logic.check_lbb_condition(0.0, 10.0)

    def test_check_lbb_condition_raises_on_zero_through_wall(self):
        with self.assertRaises(ValueError):
            logic.check_lbb_condition(20.0, 0.0)


class TestComputeLbbMargin(unittest.TestCase):

    def test_margin_above_one_when_lbb_condition_met(self):
        margin = logic.compute_lbb_margin(60.0, 30.0)
        self.assertAlmostEqual(margin, 2.0)
        self.assertGreater(margin, 1.0)

    def test_margin_exactly_one_at_boundary(self):
        margin = logic.compute_lbb_margin(25.0, 25.0)
        self.assertAlmostEqual(margin, 1.0)

    def test_margin_below_one_when_condition_not_met(self):
        margin = logic.compute_lbb_margin(15.0, 30.0)
        self.assertAlmostEqual(margin, 0.5)
        self.assertLess(margin, 1.0)

    def test_margin_raises_on_zero_through_wall(self):
        with self.assertRaises(ValueError):
            logic.compute_lbb_margin(40.0, 0.0)


class TestCheckPressureFactors(unittest.TestCase):

    def test_burst_and_proof_both_pass(self):
        result = logic.check_pressure_factors(30.0, 12.0, 10.0)
        self.assertAlmostEqual(result["burst_factor"], 3.0)
        self.assertAlmostEqual(result["proof_factor"], 1.2)
        self.assertTrue(result["burst_factor_ok"])
        self.assertTrue(result["proof_factor_ok"])

    def test_burst_factor_fails_below_1_5(self):
        result = logic.check_pressure_factors(14.0, 10.0, 10.0)
        self.assertFalse(result["burst_factor_ok"])
        self.assertTrue(result["proof_factor_ok"])

    def test_proof_factor_fails_below_1_0(self):
        result = logic.check_pressure_factors(20.0, 9.0, 10.0)
        self.assertFalse(result["proof_factor_ok"])

    def test_burst_factor_exactly_at_limit_passes(self):
        result = logic.check_pressure_factors(15.0, 10.0, 10.0)
        self.assertTrue(result["burst_factor_ok"])

    def test_pressure_factors_raise_on_zero_meop(self):
        with self.assertRaises(ValueError):
            logic.check_pressure_factors(20.0, 10.0, 0.0)


class TestEvaluateSpecimen(unittest.TestCase):

    def test_coupon_not_adequate_for_system_lbb(self):
        result = logic.evaluate_specimen("coupon", 1.0)
        self.assertFalse(result["adequate"])
        self.assertTrue(any("coupon" in n.lower() for n in result["notes"]))

    def test_sub_scale_adequate_at_fifty_percent(self):
        result = logic.evaluate_specimen("sub-scale", 0.5)
        self.assertTrue(result["adequate"])

    def test_sub_scale_not_adequate_below_fifty_percent(self):
        result = logic.evaluate_specimen("sub-scale", 0.4)
        self.assertFalse(result["adequate"])

    def test_full_scale_always_adequate(self):
        result = logic.evaluate_specimen("full-scale", 1.0)
        self.assertTrue(result["adequate"])

    def test_specimen_raises_on_unknown_type(self):
        with self.assertRaises(ValueError):
            logic.evaluate_specimen("prototype", 1.0)

    def test_specimen_raises_on_zero_scale_factor(self):
        with self.assertRaises(ValueError):
            logic.evaluate_specimen("sub-scale", 0.0)


class TestEstimateCyclesToLeak(unittest.TestCase):

    def test_cycles_computed_correctly(self):
        cycles = logic.estimate_cycles_to_leak(
            initial_flaw_depth_mm=1.0,
            wall_thickness_mm=5.0,
            crack_growth_rate_mm_per_cycle=0.001,
        )
        self.assertAlmostEqual(cycles, 4000.0)

    def test_raises_when_initial_flaw_equals_wall_thickness(self):
        with self.assertRaises(ValueError):
            logic.estimate_cycles_to_leak(5.0, 5.0, 0.001)

    def test_raises_when_initial_flaw_exceeds_wall_thickness(self):
        with self.assertRaises(ValueError):
            logic.estimate_cycles_to_leak(6.0, 5.0, 0.001)

    def test_raises_on_zero_crack_growth_rate(self):
        with self.assertRaises(ValueError):
            logic.estimate_cycles_to_leak(1.0, 5.0, 0.0)


class TestValidateLbbInputs(unittest.TestCase):

    def _base_params(self):
        return {
            "critical_crack_length_mm": 50.0,
            "through_wall_crack_length_mm": 20.0,
            "wall_thickness_mm": 5.0,
            "burst_pressure_mpa": 30.0,
            "proof_pressure_mpa": 12.0,
            "meop_mpa": 10.0,
            "test_specimen_type": "full-scale",
        }

    def test_valid_params_does_not_raise(self):
        logic.validate_lbb_inputs(self._base_params())

    def test_missing_key_raises(self):
        params = self._base_params()
        del params["meop_mpa"]
        with self.assertRaises(ValueError):
            logic.validate_lbb_inputs(params)

    def test_non_positive_crack_length_raises(self):
        params = self._base_params()
        params["critical_crack_length_mm"] = -5.0
        with self.assertRaises(ValueError):
            logic.validate_lbb_inputs(params)

    def test_invalid_specimen_type_raises(self):
        params = self._base_params()
        params["test_specimen_type"] = "sample"
        with self.assertRaises(ValueError):
            logic.validate_lbb_inputs(params)


class TestAssessLbbDemonstration(unittest.TestCase):

    def _passing_params(self):
        return {
            "critical_crack_length_mm": 50.0,
            "through_wall_crack_length_mm": 20.0,
            "wall_thickness_mm": 5.0,
            "burst_pressure_mpa": 18.0,
            "proof_pressure_mpa": 11.0,
            "meop_mpa": 10.0,
            "test_specimen_type": "full-scale",
            "scale_factor": 1.0,
        }

    def test_full_assessment_passes_valid_scenario(self):
        result = logic.assess_lbb_demonstration(self._passing_params())
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_full_assessment_fails_when_lbb_condition_not_met(self):
        params = self._passing_params()
        params["through_wall_crack_length_mm"] = 60.0
        result = logic.assess_lbb_demonstration(params)
        self.assertFalse(result["passed"])
        self.assertTrue(any("LBB condition" in f for f in result["findings"]))

    def test_full_assessment_fails_when_burst_factor_too_low(self):
        params = self._passing_params()
        params["burst_pressure_mpa"] = 12.0
        result = logic.assess_lbb_demonstration(params)
        self.assertFalse(result["passed"])
        self.assertTrue(any("Burst pressure factor" in f for f in result["findings"]))

    def test_full_assessment_includes_cycle_estimate_when_inputs_provided(self):
        params = self._passing_params()
        params["initial_flaw_depth_mm"] = 1.0
        params["crack_growth_rate_mm_per_cycle"] = 0.001
        result = logic.assess_lbb_demonstration(params)
        self.assertIn("estimated_cycles_to_leak", result)
        self.assertAlmostEqual(result["estimated_cycles_to_leak"], 4000.0)

    def test_full_assessment_coupon_specimen_fails_adequacy(self):
        params = self._passing_params()
        params["test_specimen_type"] = "coupon"
        result = logic.assess_lbb_demonstration(params)
        self.assertFalse(result["passed"])
        self.assertTrue(any("specimen" in f.lower() for f in result["findings"]))

    def test_lbb_margin_reported_in_result(self):
        params = self._passing_params()
        result = logic.assess_lbb_demonstration(params)
        self.assertAlmostEqual(result["lbb_margin"], 50.0 / 20.0, places=3)

    def test_sub_scale_specimen_passes_at_fifty_percent(self):
        params = self._passing_params()
        params["test_specimen_type"] = "sub-scale"
        params["scale_factor"] = 0.5
        result = logic.assess_lbb_demonstration(params)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()

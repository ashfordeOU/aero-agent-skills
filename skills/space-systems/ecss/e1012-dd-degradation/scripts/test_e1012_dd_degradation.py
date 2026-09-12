"""
Gate 3 contract tests for e1012-dd-degradation logic.
Run: python3 test_e1012_dd_degradation.py
"""

import math
import unittest

from e1012_dd_degradation_logic import (
    apply_margin,
    assess_dd_degradation,
    check_dd_compliance,
    compute_degraded_fraction,
)


class TestPowerLawModel(unittest.TestCase):
    def test_zero_ddd_gives_unit_fraction(self):
        result = compute_degraded_fraction("power_law", {"alpha": 0.5, "beta": 1.0}, 0.0)
        self.assertAlmostEqual(result, 1.0)

    def test_power_law_known_value(self):
        # 1 - 0.1 * 10^1.0 = 1 - 1.0 = 0.0
        result = compute_degraded_fraction("power_law", {"alpha": 0.1, "beta": 1.0}, 10.0)
        self.assertAlmostEqual(result, 0.0)

    def test_power_law_partial_degradation(self):
        # 1 - 0.05 * 4^0.5 = 1 - 0.05 * 2 = 0.90
        result = compute_degraded_fraction("power_law", {"alpha": 0.05, "beta": 0.5}, 4.0)
        self.assertAlmostEqual(result, 0.90, places=10)

    def test_power_law_missing_alpha_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("power_law", {"beta": 1.0}, 5.0)

    def test_power_law_negative_alpha_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("power_law", {"alpha": -0.1, "beta": 1.0}, 5.0)


class TestExponentialModel(unittest.TestCase):
    def test_zero_ddd_gives_unit_fraction(self):
        result = compute_degraded_fraction("exponential", {"k": 0.3}, 0.0)
        self.assertAlmostEqual(result, 1.0)

    def test_exponential_known_value(self):
        # exp(-0.2 * 5) = exp(-1) ≈ 0.36788
        result = compute_degraded_fraction("exponential", {"k": 0.2}, 5.0)
        self.assertAlmostEqual(result, math.exp(-1.0), places=10)

    def test_exponential_missing_k_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("exponential", {}, 5.0)

    def test_exponential_negative_k_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("exponential", {"k": -0.1}, 5.0)


class TestTabularModel(unittest.TestCase):
    def _params(self):
        return {
            "ddd_points": [0.0, 1e10, 2e10, 5e10],
            "fraction_points": [1.0, 0.90, 0.80, 0.60],
        }

    def test_tabular_exact_first_point(self):
        result = compute_degraded_fraction("tabular", self._params(), 0.0)
        self.assertAlmostEqual(result, 1.0)

    def test_tabular_exact_last_point(self):
        result = compute_degraded_fraction("tabular", self._params(), 5e10)
        self.assertAlmostEqual(result, 0.60)

    def test_tabular_interpolation_midpoint(self):
        # midpoint between 1e10 (0.90) and 2e10 (0.80) → 0.85
        result = compute_degraded_fraction("tabular", self._params(), 1.5e10)
        self.assertAlmostEqual(result, 0.85, places=10)

    def test_tabular_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("tabular", self._params(), 6e10)

    def test_tabular_below_range_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("tabular", self._params(), -1.0)

    def test_tabular_mismatched_lengths_raises(self):
        params = {"ddd_points": [0.0, 1e10], "fraction_points": [1.0]}
        with self.assertRaises(ValueError):
            compute_degraded_fraction("tabular", params, 0.5e10)


class TestUnknownModel(unittest.TestCase):
    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("polynomial", {"a": 1.0}, 5.0)


class TestNegativeDDD(unittest.TestCase):
    def test_negative_ddd_raises_power_law(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("power_law", {"alpha": 0.1, "beta": 1.0}, -1.0)

    def test_negative_ddd_raises_exponential(self):
        with self.assertRaises(ValueError):
            compute_degraded_fraction("exponential", {"k": 0.1}, -0.5)


class TestApplyMargin(unittest.TestCase):
    def test_unit_margin_is_identity(self):
        self.assertAlmostEqual(apply_margin(0.80, 1.0), 0.80)

    def test_margin_reduces_fraction(self):
        # 0.80 / 2.0 = 0.40
        self.assertAlmostEqual(apply_margin(0.80, 2.0), 0.40)

    def test_zero_margin_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(0.80, 0.0)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            apply_margin(0.80, -1.0)


class TestCheckDDCompliance(unittest.TestCase):
    def test_compliant_case(self):
        result = check_dd_compliance(
            "Q1", "exponential", {"k": 0.01}, ddd=10.0,
            min_fraction=0.80, margin_factor=1.0,
        )
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])
        self.assertAlmostEqual(result["degraded_fraction"], math.exp(-0.1), places=10)

    def test_non_compliant_case(self):
        # exp(-0.5 * 10) = exp(-5) ≈ 0.0067; / 2.0 ≈ 0.0034 < 0.70
        result = check_dd_compliance(
            "Q2", "exponential", {"k": 0.5}, ddd=10.0,
            min_fraction=0.70, margin_factor=2.0,
        )
        self.assertFalse(result["compliant"])
        self.assertIsNotNone(result["finding"])

    def test_result_keys_present(self):
        result = check_dd_compliance(
            "Q3", "power_law", {"alpha": 0.01, "beta": 1.0}, ddd=5.0,
            min_fraction=0.80,
        )
        for key in (
            "component_id", "ddd", "degraded_fraction",
            "margin_adjusted_fraction", "min_fraction",
            "margin_factor", "compliant", "finding",
        ):
            self.assertIn(key, result)

    def test_default_margin_is_one(self):
        result = check_dd_compliance(
            "Q4", "power_law", {"alpha": 0.0, "beta": 1.0}, ddd=100.0,
            min_fraction=0.50,
        )
        self.assertEqual(result["margin_factor"], 1.0)
        self.assertAlmostEqual(
            result["margin_adjusted_fraction"], result["degraded_fraction"]
        )


class TestAssessDDDegradation(unittest.TestCase):
    def _records(self):
        return [
            {
                "component_id": "SOL-01",
                "model": "power_law",
                "params": {"alpha": 0.05, "beta": 0.5},
                "ddd": 9.0,
                "min_fraction": 0.80,
                "margin_factor": 1.5,
            },
            {
                "component_id": "OPT-02",
                "model": "exponential",
                "params": {"k": 0.02},
                "ddd": 20.0,
                "min_fraction": 0.60,
                "margin_factor": 2.0,
            },
        ]

    def test_assess_returns_one_result_per_record(self):
        results = assess_dd_degradation(self._records())
        self.assertEqual(len(results), 2)

    def test_assess_component_ids_preserved(self):
        results = assess_dd_degradation(self._records())
        ids = [r["component_id"] for r in results]
        self.assertIn("SOL-01", ids)
        self.assertIn("OPT-02", ids)

    def test_empty_records_raises(self):
        with self.assertRaises(ValueError):
            assess_dd_degradation([])

    def test_missing_model_key_raises(self):
        bad = [{"component_id": "X", "ddd": 1.0, "min_fraction": 0.8,
                "params": {"k": 0.01}}]
        with self.assertRaises(ValueError):
            assess_dd_degradation(bad)

    def test_missing_ddd_raises(self):
        bad = [{"component_id": "X", "model": "exponential",
                "params": {"k": 0.01}, "min_fraction": 0.8}]
        with self.assertRaises(ValueError):
            assess_dd_degradation(bad)

    def test_missing_min_fraction_raises(self):
        bad = [{"component_id": "X", "model": "exponential",
                "params": {"k": 0.01}, "ddd": 5.0}]
        with self.assertRaises(ValueError):
            assess_dd_degradation(bad)

    def test_sol01_solar_cell_compliant(self):
        # alpha=0.05, beta=0.5, ddd=9 → 1 - 0.05*3 = 0.85; /1.5 = 0.5667 < 0.80 → non-compliant
        results = assess_dd_degradation(self._records())
        sol = next(r for r in results if r["component_id"] == "SOL-01")
        self.assertAlmostEqual(sol["degraded_fraction"], 0.85, places=10)
        self.assertAlmostEqual(sol["margin_adjusted_fraction"], 0.85 / 1.5, places=10)
        self.assertFalse(sol["compliant"])

    def test_opt02_optocoupler_result(self):
        # exp(-0.02*20)=exp(-0.4)≈0.6703; /2.0≈0.3352 < 0.60 → non-compliant
        results = assess_dd_degradation(self._records())
        opt = next(r for r in results if r["component_id"] == "OPT-02")
        self.assertAlmostEqual(opt["degraded_fraction"], math.exp(-0.4), places=10)
        self.assertAlmostEqual(opt["margin_adjusted_fraction"], math.exp(-0.4) / 2.0, places=10)
        self.assertFalse(opt["compliant"])

    def test_always_compliant_with_zero_degradation(self):
        records = [{
            "component_id": "IDEAL",
            "model": "power_law",
            "params": {"alpha": 0.0, "beta": 1.0},
            "ddd": 1e12,
            "min_fraction": 0.99,
            "margin_factor": 1.0,
        }]
        results = assess_dd_degradation(records)
        self.assertTrue(results[0]["compliant"])


if __name__ == "__main__":
    unittest.main()

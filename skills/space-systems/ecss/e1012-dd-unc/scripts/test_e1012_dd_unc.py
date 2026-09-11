"""
test_e1012_dd_unc.py

Offline deterministic unit tests for e1012_dd_unc_logic.
Run: python3 test_e1012_dd_unc.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_dd_unc_logic import (
    COMBINATION_METHODS,
    DEFAULT_REQUIRED_MARGIN,
    MANDATORY_SOURCES,
    assemble_uncertainty_budget,
    check_margin,
    check_required_sources,
    combine_factors,
    compute_design_fluence,
    compute_multiplicative_factor,
    compute_rss_factor,
    normalize_source_factors,
    validate_factor,
)


def full_budget(**overrides):
    """The four mandatory sources with a simple, readable factor set."""
    factors = {
        "environment_model": 2.0,
        "niel_scaling": 1.5,
        "shielding_transport": 1.2,
        "device_response": 1.5,
    }
    factors.update(overrides)
    return factors


class TestConstants(unittest.TestCase):

    def test_four_mandatory_sources(self):
        self.assertEqual(len(MANDATORY_SOURCES), 4)
        self.assertIn("environment_model", MANDATORY_SOURCES)
        self.assertIn("niel_scaling", MANDATORY_SOURCES)
        self.assertIn("shielding_transport", MANDATORY_SOURCES)
        self.assertIn("device_response", MANDATORY_SOURCES)

    def test_two_combination_methods(self):
        self.assertEqual(set(COMBINATION_METHODS), {"multiplicative", "rss"})

    def test_default_required_margin_is_two(self):
        self.assertEqual(DEFAULT_REQUIRED_MARGIN, 2.0)


class TestValidateFactor(unittest.TestCase):

    def test_accepts_one(self):
        self.assertEqual(validate_factor(1.0, "niel_scaling"), 1.0)

    def test_accepts_above_one(self):
        self.assertEqual(validate_factor(3.25, "niel_scaling"), 3.25)

    def test_accepts_integer(self):
        self.assertEqual(validate_factor(2, "niel_scaling"), 2.0)

    def test_below_one_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(0.9, "niel_scaling")

    def test_zero_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(0.0, "niel_scaling")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(-2.0, "niel_scaling")

    def test_non_numeric_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_factor("2.0", "niel_scaling")

    def test_none_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_factor(None, "niel_scaling")

    def test_bool_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_factor(True, "niel_scaling")

    def test_nan_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(float("nan"), "niel_scaling")

    def test_infinite_raises(self):
        with self.assertRaises(ValueError):
            validate_factor(float("inf"), "niel_scaling")


class TestNormalizeSourceFactors(unittest.TestCase):

    def test_returns_float_copy(self):
        normalized = normalize_source_factors({"niel_scaling": 2})
        self.assertEqual(normalized, {"niel_scaling": 2.0})

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            normalize_source_factors({"cosmic_rays": 2.0})

    def test_non_dict_raises_type_error(self):
        with self.assertRaises(TypeError):
            normalize_source_factors(["environment_model"])

    def test_empty_dict_raises(self):
        with self.assertRaises(ValueError):
            normalize_source_factors({})

    def test_invalid_factor_propagates(self):
        with self.assertRaises(ValueError):
            normalize_source_factors({"environment_model": 0.5})


class TestCheckRequiredSources(unittest.TestCase):

    def test_complete_budget_has_no_missing(self):
        self.assertEqual(check_required_sources(full_budget()), [])

    def test_reports_missing_sources_sorted(self):
        missing = check_required_sources({"environment_model": 2.0})
        self.assertEqual(
            missing, ["device_response", "niel_scaling", "shielding_transport"]
        )

    def test_empty_budget_reports_all_four(self):
        self.assertEqual(check_required_sources({}), sorted(MANDATORY_SOURCES))

    def test_non_dict_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_required_sources(None)


class TestCombineFactors(unittest.TestCase):

    def test_multiplicative_product(self):
        # 2.0 * 1.5 * 1.2 * 1.5 = 5.4
        self.assertAlmostEqual(compute_multiplicative_factor(full_budget()), 5.4)

    def test_multiplicative_single_factor_is_itself(self):
        self.assertAlmostEqual(
            compute_multiplicative_factor({"niel_scaling": 1.7}), 1.7
        )

    def test_multiplicative_all_unity_is_one(self):
        factors = {s: 1.0 for s in MANDATORY_SOURCES}
        self.assertAlmostEqual(compute_multiplicative_factor(factors), 1.0)

    def test_rss_single_factor_is_itself(self):
        self.assertAlmostEqual(compute_rss_factor({"niel_scaling": 2.0}), 2.0)

    def test_rss_two_factors(self):
        # 1 + sqrt(1^2 + 1^2) = 1 + sqrt(2)
        factors = {"environment_model": 2.0, "niel_scaling": 2.0}
        self.assertAlmostEqual(compute_rss_factor(factors), 1.0 + math.sqrt(2.0))

    def test_rss_all_unity_is_one(self):
        factors = {s: 1.0 for s in MANDATORY_SOURCES}
        self.assertAlmostEqual(compute_rss_factor(factors), 1.0)

    def test_rss_never_below_largest_factor(self):
        factors = full_budget()
        self.assertGreaterEqual(
            compute_rss_factor(factors), max(factors.values()) - 1e-12
        )

    def test_rss_less_than_multiplicative_for_spread_factors(self):
        factors = full_budget()
        self.assertLess(
            compute_rss_factor(factors), compute_multiplicative_factor(factors)
        )

    def test_combine_factors_dispatches_multiplicative(self):
        self.assertAlmostEqual(
            combine_factors(full_budget(), "multiplicative"), 5.4
        )

    def test_combine_factors_dispatches_rss(self):
        self.assertAlmostEqual(
            combine_factors(full_budget(), "rss"), compute_rss_factor(full_budget())
        )

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            combine_factors(full_budget(), "product")

    def test_non_dict_raises_type_error(self):
        with self.assertRaises(TypeError):
            combine_factors(2.0, "rss")


class TestComputeDesignFluence(unittest.TestCase):

    def test_multiplies_nominal_by_factor(self):
        self.assertAlmostEqual(compute_design_fluence(1e10, 2.0), 2e10)

    def test_unity_factor_leaves_nominal_unchanged(self):
        self.assertAlmostEqual(compute_design_fluence(3e11, 1.0), 3e11)

    def test_zero_nominal_raises(self):
        with self.assertRaises(ValueError):
            compute_design_fluence(0.0, 2.0)

    def test_negative_nominal_raises(self):
        with self.assertRaises(ValueError):
            compute_design_fluence(-1.0, 2.0)

    def test_non_numeric_nominal_raises_type_error(self):
        with self.assertRaises(TypeError):
            compute_design_fluence("1e10", 2.0)

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            compute_design_fluence(1e10, 0.5)


class TestCheckMargin(unittest.TestCase):

    def test_pass_with_comfortable_margin(self):
        result = check_margin(1e11, 2e10, required_margin=2.0)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["margin_factor"], 5.0)
        self.assertFalse(result["shortfall"])

    def test_exactly_at_required_margin_passes(self):
        result = check_margin(4e10, 2e10, required_margin=2.0)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["margin_factor"], 2.0)

    def test_margin_below_required_fails_even_though_above_one(self):
        # 1.5 * design -> device survives but without the required margin
        result = check_margin(3e10, 2e10, required_margin=2.0)
        self.assertEqual(result["status"], "fail")
        self.assertTrue(result["shortfall"])
        self.assertGreater(result["margin_factor"], 1.0)

    def test_device_below_design_fluence_fails(self):
        result = check_margin(1e10, 2e10)
        self.assertEqual(result["status"], "fail")
        self.assertLess(result["margin_factor"], 1.0)

    def test_default_required_margin_applied(self):
        result = check_margin(1e11, 1e10)
        self.assertEqual(result["required_margin"], DEFAULT_REQUIRED_MARGIN)

    def test_zero_withstand_raises(self):
        with self.assertRaises(ValueError):
            check_margin(0.0, 1e10)

    def test_zero_design_raises(self):
        with self.assertRaises(ValueError):
            check_margin(1e10, 0.0)

    def test_non_numeric_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_margin(None, 1e10)

    def test_required_margin_below_one_raises(self):
        with self.assertRaises(ValueError):
            check_margin(1e10, 1e10, required_margin=0.5)

    def test_result_keys(self):
        result = check_margin(1e10, 1e10)
        self.assertEqual(
            set(result.keys()),
            {"status", "margin_factor", "required_margin", "shortfall"},
        )


class TestAssembleUncertaintyBudget(unittest.TestCase):

    def test_complete_budget_passes(self):
        report = assemble_uncertainty_budget(
            nominal_fluence=1e10,
            source_factors=full_budget(),
            method="multiplicative",
            withstand_fluence=1e12,
            required_margin=2.0,
        )
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["missing_sources"], [])
        self.assertAlmostEqual(report["combined_factor"], 5.4)
        self.assertAlmostEqual(report["design_fluence"], 5.4e10, delta=1e-3)
        self.assertFalse(report["shortfall"])

    def test_incomplete_budget_raises(self):
        with self.assertRaises(ValueError):
            assemble_uncertainty_budget(
                nominal_fluence=1e10,
                source_factors={"environment_model": 2.0},
                method="multiplicative",
                withstand_fluence=1e12,
            )

    def test_rss_method_gives_smaller_design_fluence(self):
        multi = assemble_uncertainty_budget(
            nominal_fluence=1e10,
            source_factors=full_budget(),
            method="multiplicative",
            withstand_fluence=1e12,
        )
        rss = assemble_uncertainty_budget(
            nominal_fluence=1e10,
            source_factors=full_budget(),
            method="rss",
            withstand_fluence=1e12,
        )
        self.assertLess(rss["design_fluence"], multi["design_fluence"])

    def test_margin_shortfall_surfaces_as_fail(self):
        # design = 1e10 * 5.4 = 5.4e10; withstand 7e10 -> margin 1.30 < 2.0
        report = assemble_uncertainty_budget(
            nominal_fluence=1e10,
            source_factors=full_budget(),
            method="multiplicative",
            withstand_fluence=7e10,
            required_margin=2.0,
        )
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["shortfall"])

    def test_bad_method_raises(self):
        with self.assertRaises(ValueError):
            assemble_uncertainty_budget(
                nominal_fluence=1e10,
                source_factors=full_budget(),
                method="linear",
                withstand_fluence=1e12,
            )

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            assemble_uncertainty_budget(
                nominal_fluence=1e10,
                source_factors=full_budget(cosmic_rays=2.0),
                method="multiplicative",
                withstand_fluence=1e12,
            )

    def test_non_dict_factors_raise_type_error(self):
        with self.assertRaises(TypeError):
            assemble_uncertainty_budget(
                nominal_fluence=1e10,
                source_factors=[2.0, 2.0],
                method="multiplicative",
                withstand_fluence=1e12,
            )

    def test_report_keys_and_normalized_sources(self):
        report = assemble_uncertainty_budget(
            nominal_fluence=1e10,
            source_factors=full_budget(),
            method="rss",
            withstand_fluence=1e12,
        )
        self.assertEqual(
            set(report.keys()),
            {
                "sources",
                "missing_sources",
                "method",
                "combined_factor",
                "nominal_fluence",
                "design_fluence",
                "withstand_fluence",
                "required_margin",
                "margin_factor",
                "status",
                "shortfall",
            },
        )
        self.assertEqual(set(report["sources"]), set(MANDATORY_SOURCES))

    def test_all_unity_factors_reproduce_nominal_as_design_fluence(self):
        report = assemble_uncertainty_budget(
            nominal_fluence=2.5e10,
            source_factors={s: 1.0 for s in MANDATORY_SOURCES},
            method="multiplicative",
            withstand_fluence=1e12,
        )
        self.assertAlmostEqual(report["design_fluence"], 2.5e10)
        self.assertAlmostEqual(report["combined_factor"], 1.0)


if __name__ == "__main__":
    unittest.main()

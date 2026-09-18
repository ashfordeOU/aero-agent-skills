#!/usr/bin/env python3
"""Contract test for dimensional inspection of built parts (offline)."""

import copy
import unittest

from q7080_dimensional_inspection_logic import (
    CAPABLE,
    CONDITIONAL,
    CONFORMING,
    DEFAULT_DIMENSIONAL_POLICY,
    FEATURE_CRITICALITIES,
    INDETERMINATE,
    NON_CONFORMING,
    NOT_CAPABLE,
    STAGES,
    assess_dimensional_inspection,
    capability_category,
    capability_ratio,
    centred_capability_index,
    evaluate_feature,
    expanded_uncertainty_mm,
    guarded_limits_mm,
    inspection_scope,
    process_capability_index,
    reduced_check_allowed,
    tolerance_band_mm,
    validate_dimensional_policy,
)

BORE = {
    "name": "interface-bore-diameter",
    "criticality": "interface",
    "lower_limit_mm": 19.95,
    "upper_limit_mm": 20.05,
    "repeatability_mm": 0.002,
    "reproducibility_mm": 0.0015,
    "measured_mm": 20.01,
    "process_mean_mm": 20.0,
    "process_sigma_mm": 0.01,
}

SHELL = {
    "name": "as-built-shell-thickness",
    "criticality": "standard",
    "lower_limit_mm": 1.8,
    "upper_limit_mm": 2.2,
    "repeatability_mm": 0.01,
    "reproducibility_mm": 0.008,
    "measured_mm": 2.0,
    "process_mean_mm": 2.0,
    "process_sigma_mm": 0.04,
}


def _feature(base, **overrides):
    feature = copy.deepcopy(base)
    feature.update(overrides)
    return feature


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_dimensional_policy(DEFAULT_DIMENSIONAL_POLICY),
            DEFAULT_DIMENSIONAL_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_dimensional_policy("default")

    def test_unordered_capability_thresholds_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIMENSIONAL_POLICY)
        broken["conditional_ratio"] = 0.05
        with self.assertRaises(ValueError):
            validate_dimensional_policy(broken)

    def test_sample_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIMENSIONAL_POLICY)
        broken["production_sample_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_dimensional_policy(broken)

    def test_unknown_always_measured_entry_rejected(self):
        broken = copy.deepcopy(DEFAULT_DIMENSIONAL_POLICY)
        broken["always_measured"] = ("cosmetic",)
        with self.assertRaises(ValueError):
            validate_dimensional_policy(broken)


class BandAndUncertaintyTests(unittest.TestCase):
    def test_band_is_the_limit_difference(self):
        self.assertAlmostEqual(tolerance_band_mm(19.95, 20.05), 0.1, places=9)

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            tolerance_band_mm(20.05, 19.95)

    def test_uncertainty_combines_in_quadrature(self):
        value = expanded_uncertainty_mm(0.003, 0.004)
        self.assertAlmostEqual(value, 0.01, places=9)

    def test_uncharacterized_measurement_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty_mm(0.0, 0.0)

    def test_negative_repeatability_rejected(self):
        with self.assertRaises(ValueError):
            expanded_uncertainty_mm(-0.001, 0.002)

    def test_ratio_is_uncertainty_over_band(self):
        self.assertAlmostEqual(capability_ratio(0.01, 0.1), 0.1, places=9)

    def test_ratio_on_the_capable_bound_is_still_capable(self):
        ratio = capability_ratio(0.01, 0.1)
        self.assertAlmostEqual(ratio, DEFAULT_DIMENSIONAL_POLICY["capable_ratio"], places=9)
        self.assertEqual(capability_category(ratio), CAPABLE)

    def test_middling_ratio_is_conditional(self):
        self.assertEqual(capability_category(0.2), CONDITIONAL)

    def test_wide_ratio_is_not_capable(self):
        self.assertEqual(capability_category(0.4), NOT_CAPABLE)

    def test_zero_band_ratio_rejected(self):
        with self.assertRaises(ValueError):
            capability_ratio(0.01, 0.0)


class GuardBandTests(unittest.TestCase):
    def test_guard_band_pulls_both_limits_in(self):
        low, high = guarded_limits_mm(19.95, 20.05, 0.01)
        self.assertAlmostEqual(low, 19.96, places=9)
        self.assertAlmostEqual(high, 20.04, places=9)

    def test_uncertainty_consuming_the_band_rejected(self):
        with self.assertRaises(ValueError):
            guarded_limits_mm(19.95, 20.05, 0.06)

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            guarded_limits_mm(19.95, 20.05, -0.001)


class CapabilityIndexTests(unittest.TestCase):
    def test_spread_index_uses_six_sigma(self):
        self.assertAlmostEqual(process_capability_index(1.8, 2.2, 0.04), 400.0 / 240.0, places=9)

    def test_centred_index_penalizes_an_offset_mean(self):
        centred = centred_capability_index(1.8, 2.2, 2.0, 0.04)
        offset = centred_capability_index(1.8, 2.2, 2.1, 0.04)
        self.assertAlmostEqual(centred, 200.0 / 120.0, places=9)
        self.assertLess(offset, centred)

    def test_zero_sigma_rejected(self):
        with self.assertRaises(ValueError):
            centred_capability_index(1.8, 2.2, 2.0, 0.0)


class FeatureTests(unittest.TestCase):
    def test_in_band_feature_conforms(self):
        result = evaluate_feature(BORE)
        self.assertEqual(result["verdict"], CONFORMING)
        self.assertEqual(result["capability"], CAPABLE)

    def test_value_in_the_guard_band_is_indeterminate(self):
        result = evaluate_feature(_feature(BORE, measured_mm=20.0495))
        self.assertEqual(result["verdict"], INDETERMINATE)
        self.assertTrue(any("guard band" in f for f in result["findings"]))

    def test_value_outside_the_drawing_is_non_conforming(self):
        result = evaluate_feature(_feature(BORE, measured_mm=20.12))
        self.assertEqual(result["verdict"], NON_CONFORMING)

    def test_missing_measurement_leaves_the_feature_open(self):
        feature = _feature(BORE)
        del feature["measured_mm"]
        result = evaluate_feature(feature)
        self.assertEqual(result["verdict"], INDETERMINATE)
        self.assertIsNone(result["measured_mm"])

    def test_unnamed_feature_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_feature(_feature(BORE, name="  "))

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_feature(_feature(BORE, criticality="quite-important"))

    def test_every_criticality_name_is_evaluable(self):
        for criticality in FEATURE_CRITICALITIES:
            result = evaluate_feature(_feature(BORE, criticality=criticality))
            self.assertEqual(result["criticality"], criticality)


class ScopeTests(unittest.TestCase):
    def test_first_article_measures_everything(self):
        scope = inspection_scope([BORE, SHELL], "first-article")
        self.assertEqual(scope["measured"], [BORE["name"], SHELL["name"]])
        self.assertAlmostEqual(scope["measured_fraction"], 1.0, places=9)

    def test_production_keeps_interface_features(self):
        scope = inspection_scope([BORE, SHELL], "production")
        self.assertIn(BORE["name"], scope["measured"])

    def test_capable_standard_feature_earns_a_reduced_check(self):
        decision = reduced_check_allowed(SHELL)
        self.assertTrue(decision["allowed"])
        scope = inspection_scope([BORE, SHELL], "production")
        self.assertIn(SHELL["name"], scope["reduced"])

    def test_uncapable_standard_feature_stays_measured(self):
        weak = _feature(SHELL, process_sigma_mm=0.09)
        decision = reduced_check_allowed(weak)
        self.assertFalse(decision["allowed"])
        scope = inspection_scope([BORE, weak], "production")
        self.assertIn(weak["name"], scope["measured"])

    def test_feature_without_demonstrated_capability_stays_measured(self):
        blind = _feature(SHELL)
        del blind["process_sigma_mm"]
        decision = reduced_check_allowed(blind)
        self.assertFalse(decision["allowed"])
        self.assertIn("first article", decision["reason"])

    def test_capability_exactly_on_the_threshold_earns_the_reduction(self):
        band = SHELL["upper_limit_mm"] - SHELL["lower_limit_mm"]
        sigma = (band / 2.0) / (3.0 * DEFAULT_DIMENSIONAL_POLICY["reduced_check_cpk"])
        on_bound = _feature(SHELL, process_sigma_mm=sigma)
        cpk = reduced_check_allowed(on_bound)["cpk"]
        self.assertAlmostEqual(
            cpk, DEFAULT_DIMENSIONAL_POLICY["reduced_check_cpk"], places=9
        )
        self.assertTrue(reduced_check_allowed(on_bound)["allowed"])

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            inspection_scope([BORE], "shipping")

    def test_empty_feature_list_rejected(self):
        with self.assertRaises(ValueError):
            inspection_scope([], "first-article")


class AssessmentTests(unittest.TestCase):
    def test_clean_first_article_is_conforming(self):
        result = assess_dimensional_inspection(
            {"stage": "first-article", "features": [BORE, SHELL]}
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "dimensionally-conforming")
        self.assertEqual(len(result["features"]), 2)

    def test_out_of_limit_feature_fails_the_part(self):
        result = assess_dimensional_inspection(
            {
                "stage": "first-article",
                "features": [_feature(BORE, measured_mm=20.4), SHELL],
            }
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "dimensionally-non-conforming")
        self.assertIn(BORE["name"], result["non_conforming"])

    def test_blind_instrument_leaves_the_part_open(self):
        blunt = _feature(BORE, repeatability_mm=0.02, reproducibility_mm=0.015)
        result = assess_dimensional_inspection(
            {"stage": "first-article", "features": [blunt]}
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "dimensionally-open")
        self.assertIn(blunt["name"], result["not_capable"])

    def test_production_stage_skips_reduced_features(self):
        result = assess_dimensional_inspection(
            {"stage": "production", "features": [BORE, SHELL]}
        )
        measured_names = [f["name"] for f in result["features"]]
        self.assertIn(BORE["name"], measured_names)
        self.assertNotIn(SHELL["name"], measured_names)

    def test_every_stage_name_is_assessable(self):
        for stage in STAGES:
            result = assess_dimensional_inspection(
                {"stage": stage, "features": [BORE, SHELL]}
            )
            self.assertEqual(result["stage"], stage)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_dimensional_inspection("first-article")

    def test_case_without_features_rejected(self):
        with self.assertRaises(ValueError):
            assess_dimensional_inspection({"stage": "first-article", "features": []})


if __name__ == "__main__":
    unittest.main()

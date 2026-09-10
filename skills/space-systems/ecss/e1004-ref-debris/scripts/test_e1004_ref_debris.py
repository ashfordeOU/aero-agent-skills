#!/usr/bin/env python3
"""Offline unit tests for e1004_ref_debris_logic (ECSS-E-ST-10-04C
Annex J reference-data leaf). stdlib unittest, deterministic, no
network."""

import unittest

from e1004_ref_debris_logic import (
    MODELS,
    applicability_gaps,
    applicable_models,
    classify_object_family,
    cross_check_reported_flux,
    is_model_applicable,
    model_names,
    recommend_model,
    uncertainty_bounds,
)


class TestModelNames(unittest.TestCase):
    def test_model_names_matches_registry(self):
        self.assertEqual(model_names(), sorted(MODELS))

    def test_model_names_is_sorted(self):
        names = model_names()
        self.assertEqual(names, sorted(names))


class TestClassifyObjectFamily(unittest.TestCase):
    def test_meteoroid_accepted(self):
        self.assertEqual(classify_object_family("meteoroid"), "meteoroid")

    def test_debris_accepted(self):
        self.assertEqual(classify_object_family("debris"), "debris")

    def test_unknown_family_rejected(self):
        with self.assertRaises(ValueError):
            classify_object_family("asteroid")

    def test_empty_family_rejected(self):
        with self.assertRaises(ValueError):
            classify_object_family("")


class TestApplicabilityGaps(unittest.TestCase):
    def test_fully_applicable_case_has_no_gaps(self):
        gaps = applicability_gaps("ordem", "debris", 500.0, 2020, 0.01)
        self.assertEqual(gaps, {})
        self.assertTrue(is_model_applicable(gaps))

    def test_family_mismatch_flagged(self):
        gaps = applicability_gaps("ordem", "meteoroid", 500.0, 2020, 0.01)
        self.assertIn("family", gaps)
        self.assertNotIn("altitude_km", gaps)
        self.assertFalse(is_model_applicable(gaps))

    def test_altitude_out_of_range_flagged(self):
        gaps = applicability_gaps("ordem", "debris", 36000.0, 2020, 0.01)
        self.assertIn("altitude_km", gaps)
        self.assertEqual(gaps["altitude_km"][0], 36000.0)
        self.assertEqual(gaps["altitude_km"][1], (200.0, 2000.0))

    def test_epoch_out_of_range_flagged(self):
        gaps = applicability_gaps("ordem", "debris", 500.0, 1980, 0.01)
        self.assertIn("epoch_year", gaps)

    def test_diameter_out_of_range_flagged(self):
        gaps = applicability_gaps("ordem", "debris", 500.0, 2020, 5.0)
        self.assertIn("diameter_m", gaps)

    def test_multiple_gaps_reported_together(self):
        gaps = applicability_gaps("ordem", "meteoroid", 36000.0, 1980, 5.0)
        self.assertEqual(
            set(gaps.keys()), {"family", "altitude_km", "epoch_year", "diameter_m"}
        )

    def test_boundary_values_are_applicable(self):
        gaps = applicability_gaps("ordem", "debris", 200.0, 1990, 1e-5)
        self.assertEqual(gaps, {})
        gaps_hi = applicability_gaps("ordem", "debris", 2000.0, 2035, 1.0)
        self.assertEqual(gaps_hi, {})

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            applicability_gaps("bumper", "debris", 500.0, 2020, 0.01)


class TestApplicableModels(unittest.TestCase):
    def test_leo_debris_case_lists_ordem_and_master(self):
        result = applicable_models("debris", 500.0, 2020, 0.01)
        self.assertEqual(result, ["master", "ordem"])

    def test_geo_debris_case_lists_only_master(self):
        result = applicable_models("debris", 36000.0, 2020, 0.01)
        self.assertEqual(result, ["master"])

    def test_meteoroid_case_lists_grun_only(self):
        result = applicable_models("meteoroid", 500.0, 2020, 0.01)
        self.assertEqual(result, ["grun_interplanetary"])

    def test_no_registered_model_covers_case(self):
        result = applicable_models("debris", 500.0, 1970, 0.01)
        self.assertEqual(result, [])

    def test_unrecognized_family_raises(self):
        with self.assertRaises(ValueError):
            applicable_models("asteroid", 500.0, 2020, 0.01)


class TestRecommendModel(unittest.TestCase):
    def test_recommends_lower_uncertainty_model_when_both_applicable(self):
        result = recommend_model("debris", 500.0, 2020, 0.01)
        self.assertEqual(result, "ordem")

    def test_recommends_only_applicable_model(self):
        result = recommend_model("debris", 36000.0, 2020, 0.01)
        self.assertEqual(result, "master")

    def test_no_coverage_raises(self):
        with self.assertRaises(ValueError):
            recommend_model("debris", 500.0, 1970, 0.01)


class TestUncertaintyBounds(unittest.TestCase):
    def test_bounds_scale_by_uncertainty_factor(self):
        low, high = uncertainty_bounds("ordem", 10.0)
        self.assertAlmostEqual(low, 5.0)
        self.assertAlmostEqual(high, 20.0)

    def test_zero_flux_gives_zero_bounds(self):
        low, high = uncertainty_bounds("master", 0.0)
        self.assertEqual((low, high), (0.0, 0.0))

    def test_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            uncertainty_bounds("ordem", -1.0)

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            uncertainty_bounds("bumper", 1.0)


class TestCrossCheckReportedFlux(unittest.TestCase):
    def test_applicable_case_returns_bounds_and_no_issue(self):
        result = cross_check_reported_flux("ordem", "debris", 500.0, 2020, 0.01, 4.0)
        self.assertIsNone(result["issue"])
        self.assertAlmostEqual(result["uncertainty_low"], 2.0)
        self.assertAlmostEqual(result["uncertainty_high"], 8.0)

    def test_out_of_envelope_case_flags_issue_with_gaps(self):
        result = cross_check_reported_flux("ordem", "debris", 36000.0, 2020, 0.01, 4.0)
        self.assertEqual(result["issue"], "reported_flux_outside_model_envelope")
        self.assertIn("altitude_km", result["gaps"])

    def test_family_mismatch_flags_issue(self):
        result = cross_check_reported_flux("grun_interplanetary", "debris", 500.0, 2020, 0.01, 1.0)
        self.assertEqual(result["issue"], "reported_flux_outside_model_envelope")
        self.assertIn("family", result["gaps"])


if __name__ == "__main__":
    unittest.main()

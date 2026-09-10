#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex G (informative)
reference atmosphere data.

Exercises scripts/e1004_ref_atmosphere_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a cataloged
model's altitude range is looked up correctly and an unrecognized
model raises; altitude-in-range checks reject a negative altitude;
body lookup raises for an unrecognized body; model selection applies
the purpose-driven preference order for Earth and always returns the
GRAM-class model for a non-Earth body, raising when no cataloged model
covers the combination; required-input gaps are reported per model;
the Earth altitude-regime classification returns the correct band and
raises for a negative altitude; and the aggregate review reports a
coverage finding or per-input findings without raising, while still
raising for structurally invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_ref_atmosphere_logic as atmo  # noqa: E402


class ModelAltitudeRangeTest(unittest.TestCase):
    def test_nrlmsise00_range(self):
        self.assertEqual(atmo.model_altitude_range("nrlmsise00"), (0.0, 1000.0))

    def test_jb2006_range(self):
        self.assertEqual(atmo.model_altitude_range("jb2006"), (120.0, 1000.0))

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            atmo.model_altitude_range("mystery-model")


class IsAltitudeInRangeTest(unittest.TestCase):
    def test_within_range_true(self):
        self.assertTrue(atmo.is_altitude_in_range("nrlmsise00", 400.0))

    def test_below_jb2006_floor_false(self):
        self.assertFalse(atmo.is_altitude_in_range("jb2006", 50.0))

    def test_above_range_false(self):
        self.assertFalse(atmo.is_altitude_in_range("nrlmsise00", 5000.0))

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            atmo.is_altitude_in_range("nrlmsise00", -1.0)

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            atmo.is_altitude_in_range("mystery-model", 400.0)


class ModelsForBodyTest(unittest.TestCase):
    def test_earth_models(self):
        self.assertEqual(
            atmo.models_for_body("earth"), ["earth_gram", "jb2006", "nrlmsise00"]
        )

    def test_mars_models(self):
        self.assertEqual(atmo.models_for_body("mars"), ["mars_gram"])

    def test_unknown_body_raises(self):
        with self.assertRaises(ValueError):
            atmo.models_for_body("pluto")


class SelectAtmosphereModelTest(unittest.TestCase):
    def test_earth_drag_prediction_prefers_jb2006(self):
        self.assertEqual(
            atmo.select_atmosphere_model("earth", 400.0, atmo.DRAG_PREDICTION), "jb2006"
        )

    def test_earth_drag_prediction_falls_back_below_jb2006_floor(self):
        self.assertEqual(
            atmo.select_atmosphere_model("earth", 90.0, atmo.DRAG_PREDICTION), "nrlmsise00"
        )

    def test_earth_density_reference_prefers_nrlmsise00(self):
        self.assertEqual(
            atmo.select_atmosphere_model("earth", 300.0, atmo.DENSITY_REFERENCE),
            "nrlmsise00",
        )

    def test_earth_full_profile_uses_earth_gram(self):
        self.assertEqual(
            atmo.select_atmosphere_model("earth", 300.0, atmo.FULL_PROFILE), "earth_gram"
        )

    def test_non_earth_body_uses_gram_regardless_of_purpose(self):
        self.assertEqual(
            atmo.select_atmosphere_model("mars", 50.0, atmo.DRAG_PREDICTION), "mars_gram"
        )

    def test_no_coverage_raises(self):
        with self.assertRaises(ValueError):
            atmo.select_atmosphere_model("earth", 5000.0, atmo.DRAG_PREDICTION)

    def test_unrecognized_purpose_raises(self):
        with self.assertRaises(ValueError):
            atmo.select_atmosphere_model("earth", 400.0, "guesswork")

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            atmo.select_atmosphere_model("earth", -10.0, atmo.DRAG_PREDICTION)


class ModelInputGapsTest(unittest.TestCase):
    def test_no_gaps_when_all_provided(self):
        provided = {"f10_7_solar_flux", "ap_geomagnetic_index", "day_of_year", "local_solar_time"}
        self.assertEqual(atmo.model_input_gaps("nrlmsise00", provided), [])

    def test_reports_missing_inputs_sorted(self):
        gaps = atmo.model_input_gaps("jb2006", {"f10_7_solar_flux"})
        self.assertEqual(gaps, ["day_of_year", "dst_geomagnetic_index", "s10_7_solar_index"])

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            atmo.model_input_gaps("mystery-model", set())


class ClassifyAltitudeRegimeTest(unittest.TestCase):
    def test_surface_is_troposphere(self):
        self.assertEqual(atmo.classify_altitude_regime(0.0), "troposphere")

    def test_boundary_is_next_regime(self):
        self.assertEqual(atmo.classify_altitude_regime(12.0), "stratosphere")

    def test_high_altitude_is_exosphere(self):
        self.assertEqual(atmo.classify_altitude_regime(50000.0), "exosphere")

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            atmo.classify_altitude_regime(-5.0)


class AtmosphereModelReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        provided = {"f10_7_solar_flux", "s10_7_solar_index", "dst_geomagnetic_index", "day_of_year"}
        review = atmo.atmosphere_model_review("earth", 400.0, atmo.DRAG_PREDICTION, provided)
        self.assertEqual(review, {"model_id": "jb2006", "issues": []})
        self.assertTrue(atmo.is_atmosphere_review_compliant(review))

    def test_missing_inputs_flagged(self):
        review = atmo.atmosphere_model_review("earth", 400.0, atmo.DRAG_PREDICTION, set())
        self.assertEqual(review["model_id"], "jb2006")
        self.assertEqual(len(review["issues"]), 4)
        self.assertFalse(atmo.is_atmosphere_review_compliant(review))

    def test_no_coverage_reported_not_raised(self):
        review = atmo.atmosphere_model_review("earth", 5000.0, atmo.DRAG_PREDICTION, set())
        self.assertIsNone(review["model_id"])
        self.assertEqual(review["issues"][0]["issue"], "no_model_coverage")
        self.assertFalse(atmo.is_atmosphere_review_compliant(review))

    def test_unrecognized_body_raises(self):
        with self.assertRaises(ValueError):
            atmo.atmosphere_model_review("pluto", 400.0, atmo.DRAG_PREDICTION, set())

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            atmo.atmosphere_model_review("earth", -1.0, atmo.DRAG_PREDICTION, set())


if __name__ == "__main__":
    unittest.main(verbosity=2)

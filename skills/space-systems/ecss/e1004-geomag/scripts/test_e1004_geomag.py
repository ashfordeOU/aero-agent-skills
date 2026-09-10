#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 5.2 geomagnetic
field model selection, IGRF epoch/secular-variation handling, and
B,L field logic.

Exercises scripts/e1004_geomag_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the geomagnetic model is
selected from the orbit's geocentric distance regime (internal-only
at or below the internal/external threshold distance, internal plus
external above it); a target date is within IGRF validity when it is
at or before the latest published epoch (interpolation) or within the
secular-variation extrapolation limit after it; secular variation
scales the epoch field value by its rate over the elapsed time; the
dipole B,L equatorial field scales the adjusted equatorial field by
l_shell ** -3; a case is compliant only when its declared model
matches the regime's required model and its target date is within
epoch validity; the assessment record covers every case with no
duplicates and is reported all-compliant only when every case is
compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_geomag_logic as gl  # noqa: E402


class ClassifyFieldRegimeTest(unittest.TestCase):
    def test_at_or_below_threshold_is_internal_only(self):
        self.assertEqual(gl.classify_field_regime(1.2), "internal_only")
        self.assertEqual(
            gl.classify_field_regime(gl.INTERNAL_EXTERNAL_THRESHOLD_RE),
            "internal_only",
        )

    def test_above_threshold_is_internal_plus_external(self):
        self.assertEqual(
            gl.classify_field_regime(8.0), "internal_plus_external"
        )

    def test_non_positive_distance_raises(self):
        with self.assertRaises(ValueError):
            gl.classify_field_regime(0.0)
        with self.assertRaises(ValueError):
            gl.classify_field_regime(-1.0)


class SelectGeomagModelTest(unittest.TestCase):
    def test_internal_only_model(self):
        self.assertEqual(
            gl.select_geomag_model("internal_only"),
            gl.MODEL_BY_REGIME["internal_only"],
        )

    def test_internal_plus_external_model(self):
        self.assertEqual(
            gl.select_geomag_model("internal_plus_external"),
            gl.MODEL_BY_REGIME["internal_plus_external"],
        )

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            gl.select_geomag_model("deep_space")


class NearestIgrfEpochTest(unittest.TestCase):
    def test_exact_epoch_returns_itself(self):
        self.assertEqual(gl.nearest_igrf_epoch(2020.0), 2020.0)

    def test_between_epochs_returns_lower_epoch(self):
        self.assertEqual(gl.nearest_igrf_epoch(2022.5), 2020.0)

    def test_before_earliest_epoch_raises(self):
        with self.assertRaises(ValueError):
            gl.nearest_igrf_epoch(1850.0)


class IsWithinIgrfValidityTest(unittest.TestCase):
    def test_at_or_before_latest_epoch_is_valid(self):
        self.assertTrue(gl.is_within_igrf_validity(2020.0))
        self.assertTrue(gl.is_within_igrf_validity(gl.IGRF_LATEST_EPOCH_YEAR))

    def test_within_extrapolation_limit_is_valid(self):
        self.assertTrue(
            gl.is_within_igrf_validity(
                gl.IGRF_LATEST_EPOCH_YEAR + gl.IGRF_SV_EXTRAPOLATION_LIMIT_YEARS
            )
        )

    def test_beyond_extrapolation_limit_is_invalid(self):
        self.assertFalse(
            gl.is_within_igrf_validity(
                gl.IGRF_LATEST_EPOCH_YEAR + gl.IGRF_SV_EXTRAPOLATION_LIMIT_YEARS + 1.0
            )
        )

    def test_before_earliest_epoch_raises(self):
        with self.assertRaises(ValueError):
            gl.is_within_igrf_validity(1800.0)


class ApplySecularVariationTest(unittest.TestCase):
    def test_scales_field_value_by_elapsed_time(self):
        self.assertAlmostEqual(gl.apply_secular_variation(30000.0, -20.0, 0.0), 30000.0)
        self.assertAlmostEqual(gl.apply_secular_variation(30000.0, -20.0, 3.0), 29940.0)

    def test_negative_delta_years_raises(self):
        with self.assertRaises(ValueError):
            gl.apply_secular_variation(30000.0, -20.0, -1.0)


class EquatorialFieldAtLTest(unittest.TestCase):
    def test_l_one_returns_surface_field(self):
        self.assertAlmostEqual(gl.equatorial_field_at_l(1.0, 30000.0), 30000.0)

    def test_higher_l_reduces_field(self):
        self.assertAlmostEqual(gl.equatorial_field_at_l(2.0, 30000.0), 30000.0 / 8.0)

    def test_non_positive_l_shell_raises(self):
        with self.assertRaises(ValueError):
            gl.equatorial_field_at_l(0.0, 30000.0)
        with self.assertRaises(ValueError):
            gl.equatorial_field_at_l(-3.0, 30000.0)


class AssessGeomagCaseTest(unittest.TestCase):
    def test_compliant_internal_only_case(self):
        case = {
            "id": "GEOMAG-001",
            "geocentric_distance_re": 1.5,
            "target_year": 2022.0,
            "declared_model": gl.MODEL_BY_REGIME["internal_only"],
            "epoch_b0": 30000.0,
            "secular_variation_rate": -20.0,
            "l_shell": 2.0,
        }
        result = gl.assess_geomag_case(case)
        self.assertEqual(result["regime"], "internal_only")
        self.assertTrue(result["model_ok"])
        self.assertTrue(result["epoch_valid"])
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["adjusted_b0"], 29960.0)
        self.assertAlmostEqual(result["b_at_l"], 29960.0 / 8.0)

    def test_noncompliant_when_internal_only_used_at_high_distance(self):
        case = {
            "id": "GEOMAG-002",
            "geocentric_distance_re": 8.0,
            "target_year": 2022.0,
            "declared_model": gl.MODEL_BY_REGIME["internal_only"],
            "epoch_b0": 30000.0,
            "secular_variation_rate": -20.0,
        }
        result = gl.assess_geomag_case(case)
        self.assertEqual(result["regime"], "internal_plus_external")
        self.assertFalse(result["model_ok"])
        self.assertFalse(result["compliant"])

    def test_noncompliant_when_epoch_beyond_extrapolation_limit(self):
        case = {
            "id": "GEOMAG-003",
            "geocentric_distance_re": 1.5,
            "target_year": gl.IGRF_LATEST_EPOCH_YEAR
            + gl.IGRF_SV_EXTRAPOLATION_LIMIT_YEARS
            + 2.0,
            "declared_model": gl.MODEL_BY_REGIME["internal_only"],
            "epoch_b0": 30000.0,
            "secular_variation_rate": -20.0,
        }
        result = gl.assess_geomag_case(case)
        self.assertFalse(result["epoch_valid"])
        self.assertFalse(result["compliant"])

    def test_case_without_l_shell_omits_b_at_l(self):
        case = {
            "id": "GEOMAG-004",
            "geocentric_distance_re": 1.5,
            "target_year": 2022.0,
            "declared_model": gl.MODEL_BY_REGIME["internal_only"],
            "epoch_b0": 30000.0,
            "secular_variation_rate": -20.0,
        }
        result = gl.assess_geomag_case(case)
        self.assertNotIn("b_at_l", result)

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            gl.assess_geomag_case({
                "geocentric_distance_re": 1.5,
                "target_year": 2022.0,
                "declared_model": gl.MODEL_BY_REGIME["internal_only"],
                "epoch_b0": 30000.0,
                "secular_variation_rate": -20.0,
            })


class BuildGeomagAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "GEOMAG-001",
            "geocentric_distance_re": 1.5,
            "target_year": 2022.0,
            "declared_model": "IGRF-class internal field model",
            "epoch_b0": 30000.0,
            "secular_variation_rate": -20.0,
        },
        {
            "id": "GEOMAG-002",
            "geocentric_distance_re": 8.0,
            "target_year": 2022.0,
            "declared_model": "IGRF-class internal field model",
            "epoch_b0": 30000.0,
            "secular_variation_rate": -20.0,
        },
    ]

    def test_record_order_and_status(self):
        record = gl.build_geomag_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "GEOMAG-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "GEOMAG-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            gl.build_geomag_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        gl.build_geomag_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = gl.build_geomag_assessment(BuildGeomagAssessmentTest.CASES)
        self.assertEqual(gl.noncompliant_items(record), ["GEOMAG-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = gl.build_geomag_assessment([BuildGeomagAssessmentTest.CASES[0]])
        self.assertTrue(gl.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = gl.build_geomag_assessment(BuildGeomagAssessmentTest.CASES)
        self.assertFalse(gl.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)

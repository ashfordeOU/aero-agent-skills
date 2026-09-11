"""
Offline unit tests for e1012_bio_margins_logic.
Anchor: ECSS-E-ST-10C §5.5.5 — biological effects margin philosophy.

Run: python3 test_e1012_bio_margins.py
Expected output: OK
"""

import sys
import os
import unittest

# Allow running from any working directory.
sys.path.insert(0, os.path.dirname(__file__))

from e1012_bio_margins_logic import (
    RADIATION, PHYSIOLOGICAL, ATMOSPHERIC, THERMAL, ACOUSTIC,
    COMPLIANT, EXCEEDANCE, LIMIT_UNSET, INVALID_STRESSOR,
    MARGIN_FACTORS,
    Stressor, Finding,
    get_margin_factor,
    apply_margin,
    assess_stressor,
    assess_bio_margins,
    is_mission_compliant,
    summarize_findings,
)


class TestMarginFactors(unittest.TestCase):

    def test_radiation_factor_is_one_point_five(self):
        self.assertAlmostEqual(get_margin_factor(RADIATION), 1.5)

    def test_physiological_factor_is_one_point_two_five(self):
        self.assertAlmostEqual(get_margin_factor(PHYSIOLOGICAL), 1.25)

    def test_atmospheric_factor_is_one_point_two_five(self):
        self.assertAlmostEqual(get_margin_factor(ATMOSPHERIC), 1.25)

    def test_thermal_factor_is_one_point_two_five(self):
        self.assertAlmostEqual(get_margin_factor(THERMAL), 1.25)

    def test_acoustic_factor_is_one_point_two_five(self):
        self.assertAlmostEqual(get_margin_factor(ACOUSTIC), 1.25)

    def test_unknown_stressor_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_margin_factor("biological_unknown")

    def test_empty_string_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_margin_factor("")


class TestApplyMargin(unittest.TestCase):

    def test_basic_multiplication(self):
        self.assertAlmostEqual(apply_margin(100.0, 1.5), 150.0)

    def test_zero_exposure_yields_zero(self):
        self.assertAlmostEqual(apply_margin(0.0, 1.5), 0.0)

    def test_fractional_exposure(self):
        self.assertAlmostEqual(apply_margin(40.0, 1.25), 50.0)

    def test_negative_exposure_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_margin(-1.0, 1.5)

    def test_margin_factor_below_one_raises_value_error(self):
        with self.assertRaises(ValueError):
            apply_margin(10.0, 0.9)

    def test_margin_factor_exactly_one_is_allowed(self):
        self.assertAlmostEqual(apply_margin(50.0, 1.0), 50.0)


class TestAssessStressor(unittest.TestCase):

    def test_compliant_radiation_stressor(self):
        s = Stressor("GCR dose", RADIATION, 200.0, 400.0)
        # margined = 200 * 1.5 = 300 <= 400
        f = assess_stressor(s)
        self.assertEqual(f.status, COMPLIANT)
        self.assertAlmostEqual(f.margined_exposure, 300.0)
        self.assertAlmostEqual(f.margin_factor, 1.5)

    def test_exceedance_radiation_stressor(self):
        s = Stressor("SPE dose", RADIATION, 300.0, 400.0)
        # margined = 300 * 1.5 = 450 > 400
        f = assess_stressor(s)
        self.assertEqual(f.status, EXCEEDANCE)
        self.assertAlmostEqual(f.margined_exposure, 450.0)

    def test_compliant_physiological_stressor(self):
        s = Stressor("Bone density loss", PHYSIOLOGICAL, 2.0, 3.0)
        # margined = 2.0 * 1.25 = 2.5 <= 3.0
        f = assess_stressor(s)
        self.assertEqual(f.status, COMPLIANT)
        self.assertAlmostEqual(f.margined_exposure, 2.5)

    def test_exceedance_physiological_stressor(self):
        s = Stressor("Muscle atrophy", PHYSIOLOGICAL, 3.0, 3.5)
        # margined = 3.0 * 1.25 = 3.75 > 3.5
        f = assess_stressor(s)
        self.assertEqual(f.status, EXCEEDANCE)

    def test_limit_unset_returns_limit_unset_status(self):
        s = Stressor("CO2 concentration", ATMOSPHERIC, 0.5, None)
        f = assess_stressor(s)
        self.assertEqual(f.status, LIMIT_UNSET)
        self.assertIsNone(f.allowable_limit)
        self.assertAlmostEqual(f.margined_exposure, 0.625)

    def test_invalid_stressor_type_returns_invalid_status(self):
        s = Stressor("Unknown stressor", "unknown_type", 10.0, 20.0)
        f = assess_stressor(s)
        self.assertEqual(f.status, INVALID_STRESSOR)
        self.assertAlmostEqual(f.margin_factor, 0.0)

    def test_margined_exposure_equal_to_limit_is_compliant(self):
        # Boundary: margined == limit should be COMPLIANT (not EXCEEDANCE)
        s = Stressor("Thermal delta-T", THERMAL, 8.0, 10.0)
        # margined = 8.0 * 1.25 = 10.0 == limit
        f = assess_stressor(s)
        self.assertEqual(f.status, COMPLIANT)
        self.assertAlmostEqual(f.margined_exposure, 10.0)

    def test_acoustic_stressor_uses_correct_factor(self):
        s = Stressor("Habitat noise", ACOUSTIC, 60.0, 85.0)
        # margined = 60 * 1.25 = 75 <= 85
        f = assess_stressor(s)
        self.assertAlmostEqual(f.margin_factor, 1.25)
        self.assertEqual(f.status, COMPLIANT)


class TestAssessBioMargins(unittest.TestCase):

    def test_multiple_stressors_returns_one_finding_each(self):
        stressors = [
            Stressor("GCR", RADIATION, 100.0, 200.0),
            Stressor("Microgravity", PHYSIOLOGICAL, 1.0, 2.0),
            Stressor("O2 partial pressure", ATMOSPHERIC, 20.0, 30.0),
        ]
        findings = assess_bio_margins(stressors)
        self.assertEqual(len(findings), 3)

    def test_empty_stressor_list_returns_empty_findings(self):
        self.assertEqual(assess_bio_margins([]), [])


class TestMissionCompliance(unittest.TestCase):

    def test_all_compliant_returns_true(self):
        stressors = [
            Stressor("GCR", RADIATION, 100.0, 200.0),
            Stressor("Noise", ACOUSTIC, 50.0, 80.0),
        ]
        findings = assess_bio_margins(stressors)
        self.assertTrue(is_mission_compliant(findings))

    def test_one_exceedance_returns_false(self):
        stressors = [
            Stressor("GCR", RADIATION, 200.0, 200.0),
            # margined = 200 * 1.5 = 300 > 200
        ]
        findings = assess_bio_margins(stressors)
        self.assertFalse(is_mission_compliant(findings))

    def test_limit_unset_returns_false(self):
        stressors = [Stressor("CO2", ATMOSPHERIC, 0.5, None)]
        findings = assess_bio_margins(stressors)
        self.assertFalse(is_mission_compliant(findings))

    def test_empty_findings_returns_true(self):
        self.assertTrue(is_mission_compliant([]))


class TestSummarizeFindings(unittest.TestCase):

    def test_summary_counts_by_status(self):
        stressors = [
            Stressor("GCR", RADIATION, 100.0, 200.0),    # COMPLIANT
            Stressor("SPE", RADIATION, 280.0, 200.0),     # EXCEEDANCE (420 > 200)
            Stressor("CO2", ATMOSPHERIC, 0.5, None),      # LIMIT_UNSET
            Stressor("Noise", "bad_type", 50.0, 80.0),   # INVALID_STRESSOR
        ]
        findings = assess_bio_margins(stressors)
        summary = summarize_findings(findings)
        self.assertEqual(summary[COMPLIANT], 1)
        self.assertEqual(summary[EXCEEDANCE], 1)
        self.assertEqual(summary[LIMIT_UNSET], 1)
        self.assertEqual(summary[INVALID_STRESSOR], 1)

    def test_all_compliant_summary(self):
        stressors = [
            Stressor("GCR", RADIATION, 50.0, 200.0),
            Stressor("Noise", ACOUSTIC, 40.0, 80.0),
        ]
        summary = summarize_findings(assess_bio_margins(stressors))
        self.assertEqual(summary[COMPLIANT], 2)
        self.assertEqual(summary[EXCEEDANCE], 0)


if __name__ == "__main__":
    unittest.main()

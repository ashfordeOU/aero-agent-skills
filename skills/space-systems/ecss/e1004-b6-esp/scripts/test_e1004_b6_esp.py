#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.6 Emission of Solar
Protons (ESP) worst-case fluence spectra.

Exercises scripts/e1004_b6_esp_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the confidence-level scale
factor is 1.0 at the 50% baseline, grows monotonically as confidence
approaches 100%, and raises outside [50, 99]; the duration scale factor
is 1.0 at one year, grows monotonically with duration, and raises for a
non-positive duration; an integral fluence threshold outside the
model's supported energy set raises; a fluence spectrum covers every
supported threshold and strictly decreases with increasing energy; a
case is compliant only when its confidence level meets the required
worst-case threshold, and a below-threshold case is flagged rather than
silently accepted.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b6_esp_logic as esp  # noqa: E402


class ConfidenceScaleFactorTest(unittest.TestCase):
    def test_baseline_confidence_is_unity(self):
        self.assertAlmostEqual(esp.confidence_scale_factor(50.0), 1.0)

    def test_higher_confidence_gives_larger_factor(self):
        low = esp.confidence_scale_factor(80.0)
        high = esp.confidence_scale_factor(95.0)
        self.assertGreater(high, low)
        self.assertGreater(low, esp.confidence_scale_factor(50.0))

    def test_monotonic_across_supported_range(self):
        levels = [50.0, 60.0, 70.0, 80.0, 90.0, 95.0, 99.0]
        factors = [esp.confidence_scale_factor(level) for level in levels]
        self.assertEqual(factors, sorted(factors))
        self.assertTrue(all(b > a for a, b in zip(factors, factors[1:])))

    def test_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            esp.confidence_scale_factor(49.9)

    def test_above_maximum_raises(self):
        with self.assertRaises(ValueError):
            esp.confidence_scale_factor(99.1)


class DurationScaleFactorTest(unittest.TestCase):
    def test_one_year_is_unity(self):
        self.assertAlmostEqual(esp.duration_scale_factor(1.0), 1.0)

    def test_longer_duration_gives_larger_factor(self):
        self.assertGreater(esp.duration_scale_factor(7.0), esp.duration_scale_factor(1.0))
        self.assertGreater(esp.duration_scale_factor(15.0), esp.duration_scale_factor(7.0))

    def test_sub_linear_growth(self):
        # Sub-linear: doubling duration less than doubles the factor.
        factor_1 = esp.duration_scale_factor(1.0)
        factor_2 = esp.duration_scale_factor(2.0)
        self.assertLess(factor_2 / factor_1, 2.0)

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            esp.duration_scale_factor(0.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            esp.duration_scale_factor(-3.0)


class IntegralFluenceAboveTest(unittest.TestCase):
    def test_baseline_case_matches_reference_table(self):
        fluence = esp.integral_fluence_above(10.0, 1.0, 50.0)
        self.assertAlmostEqual(fluence, esp.BASELINE_ANNUAL_FLUENCE_CM2[10.0])

    def test_scales_up_with_duration_and_confidence(self):
        baseline = esp.integral_fluence_above(10.0, 1.0, 50.0)
        scaled = esp.integral_fluence_above(10.0, 7.0, 95.0)
        self.assertGreater(scaled, baseline)

    def test_unsupported_threshold_raises(self):
        with self.assertRaises(ValueError):
            esp.integral_fluence_above(17.5, 1.0, 90.0)


class FluenceSpectrumTest(unittest.TestCase):
    def test_covers_every_reference_energy(self):
        spectrum = esp.fluence_spectrum(1.0, 90.0)
        self.assertEqual(set(spectrum.keys()), set(esp.REFERENCE_ENERGIES_MEV))

    def test_strictly_decreasing_with_energy(self):
        spectrum = esp.fluence_spectrum(5.0, 95.0)
        self.assertTrue(esp.is_spectrum_monotonic_decreasing(spectrum))

    def test_non_monotonic_spectrum_detected(self):
        broken = {1.0: 10.0, 10.0: 20.0, 100.0: 5.0}
        self.assertFalse(esp.is_spectrum_monotonic_decreasing(broken))


class MeetsWorstCaseConfidenceTest(unittest.TestCase):
    def test_meets_default_threshold(self):
        self.assertTrue(esp.meets_worst_case_confidence(90.0))
        self.assertTrue(esp.meets_worst_case_confidence(95.0))

    def test_below_default_threshold(self):
        self.assertFalse(esp.meets_worst_case_confidence(80.0))

    def test_custom_required_threshold(self):
        self.assertTrue(esp.meets_worst_case_confidence(85.0, required_confidence_pct=80.0))
        self.assertFalse(esp.meets_worst_case_confidence(85.0, required_confidence_pct=90.0))


class AssessEspCaseTest(unittest.TestCase):
    def test_compliant_case(self):
        case = {
            "case_id": "battery-1",
            "mission_duration_years": 5.0,
            "confidence_pct": 95.0,
        }
        result = esp.assess_esp_case(case)
        self.assertEqual(result["case_id"], "battery-1")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(set(result["spectrum"].keys()), set(esp.REFERENCE_ENERGIES_MEV))

    def test_below_worst_case_confidence_flagged(self):
        case = {
            "case_id": "battery-2",
            "mission_duration_years": 5.0,
            "confidence_pct": 75.0,
        }
        result = esp.assess_esp_case(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(
            result["findings"][0]["issue"],
            "confidence_level_below_worst_case_threshold",
        )

    def test_custom_required_confidence_pct(self):
        case = {
            "case_id": "battery-3",
            "mission_duration_years": 1.0,
            "confidence_pct": 80.0,
            "required_confidence_pct": 75.0,
        }
        result = esp.assess_esp_case(case)
        self.assertTrue(result["compliant"])

    def test_invalid_confidence_raises(self):
        case = {
            "case_id": "battery-4",
            "mission_duration_years": 1.0,
            "confidence_pct": 10.0,
        }
        with self.assertRaises(ValueError):
            esp.assess_esp_case(case)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C SEP peak flux (JPL-type models).

Exercises scripts/e1004_sep_peakflux_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - peak-flux
applicability, energy-channel selection, worst-case integral peak
flux, worst-case window classification, overall verdict, and
ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_sep_peakflux_logic as pf  # noqa: E402


class PeakFluxApplicableTest(unittest.TestCase):
    def test_see_rate_worst_case_applicable(self):
        self.assertTrue(pf.peak_flux_applicable("see-rate-worst-case"))

    def test_total_fluence_degradation_not_applicable(self):
        self.assertFalse(pf.peak_flux_applicable("total-fluence-degradation"))

    def test_total_ionizing_dose_not_applicable(self):
        self.assertFalse(pf.peak_flux_applicable("total-ionizing-dose"))

    def test_case_insensitive(self):
        self.assertTrue(pf.peak_flux_applicable("SEE-RATE-WORST-CASE"))

    def test_all_purposes_covered(self):
        expected = {
            "see-rate-worst-case",
            "single-event-upset-worst-case",
            "single-event-latchup-worst-case",
            "total-fluence-degradation",
            "total-ionizing-dose",
        }
        self.assertEqual(set(pf.ANALYSIS_PURPOSES), expected)

    def test_unknown_purpose_raises(self):
        with self.assertRaises(ValueError):
            pf.peak_flux_applicable("total-dose-margin")
        with self.assertRaises(ValueError):
            pf.peak_flux_applicable(5)


class SelectEnergyChannelTest(unittest.TestCase):
    def test_exact_channel_match(self):
        self.assertEqual(pf.select_energy_channel(10), 10)

    def test_rounds_up_to_next_channel(self):
        self.assertEqual(pf.select_energy_channel(5), 10)
        self.assertEqual(pf.select_energy_channel(31), 60)

    def test_lowest_channel_for_small_threshold(self):
        self.assertEqual(pf.select_energy_channel(0.5), 1)

    def test_highest_channel_at_max(self):
        self.assertEqual(pf.select_energy_channel(150), 150)

    def test_threshold_above_max_raises(self):
        with self.assertRaises(ValueError):
            pf.select_energy_channel(200)

    def test_non_positive_threshold_raises(self):
        with self.assertRaises(ValueError):
            pf.select_energy_channel(0)
        with self.assertRaises(ValueError):
            pf.select_energy_channel(-10)

    def test_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            pf.select_energy_channel("10")
        with self.assertRaises(ValueError):
            pf.select_energy_channel(True)


class IntegralPeakFluxTest(unittest.TestCase):
    def test_flux_at_reference_energy_equals_A(self):
        self.assertAlmostEqual(pf.integral_peak_flux(90, 10.0), 1.0e3)
        self.assertAlmostEqual(pf.integral_peak_flux(95, 10.0), 3.0e3)
        self.assertAlmostEqual(pf.integral_peak_flux(99, 10.0), 1.0e4)

    def test_flux_decreases_with_energy(self):
        low = pf.integral_peak_flux(95, 10.0)
        high = pf.integral_peak_flux(95, 100.0)
        self.assertGreater(low, high)

    def test_flux_increases_with_confidence_level(self):
        f90 = pf.integral_peak_flux(90, 30.0)
        f95 = pf.integral_peak_flux(95, 30.0)
        f99 = pf.integral_peak_flux(99, 30.0)
        self.assertLess(f90, f95)
        self.assertLess(f95, f99)

    def test_unsupported_confidence_level_raises(self):
        with self.assertRaises(ValueError):
            pf.integral_peak_flux(80, 10.0)

    def test_non_positive_energy_raises(self):
        with self.assertRaises(ValueError):
            pf.integral_peak_flux(90, 0)
        with self.assertRaises(ValueError):
            pf.integral_peak_flux(90, -5)


class WorstCaseWindowCheckTest(unittest.TestCase):
    def test_short_window_categorized_as_peak_window(self):
        result = pf.worst_case_window_check(2.0)
        self.assertEqual(result["window_class"], "short-duration-peak-window")

    def test_boundary_24_hours_is_peak_window(self):
        result = pf.worst_case_window_check(24.0)
        self.assertEqual(result["window_class"], "short-duration-peak-window")

    def test_long_window_needs_fluence_model(self):
        result = pf.worst_case_window_check(24.01)
        self.assertEqual(result["window_class"], "exceeds-peak-window-use-fluence-model")

    def test_non_positive_duration_raises(self):
        with self.assertRaises(ValueError):
            pf.worst_case_window_check(0)
        with self.assertRaises(ValueError):
            pf.worst_case_window_check(-1)


class PeakfluxWorstCaseVerdictTest(unittest.TestCase):
    def test_applicable_short_window_ready(self):
        verdict = pf.peakflux_worst_case_verdict(
            "see-rate-worst-case", 95, 20, 6.0
        )
        self.assertTrue(verdict["applicable"])
        self.assertEqual(verdict["energy_channel_mev"], 30)
        self.assertEqual(verdict["status"], "peak-flux-worst-case-ready")
        self.assertIsNotNone(verdict["peak_flux"])

    def test_not_applicable_redirects_to_fluence_model(self):
        verdict = pf.peakflux_worst_case_verdict(
            "total-fluence-degradation", 95, 20, 6.0
        )
        self.assertFalse(verdict["applicable"])
        self.assertIsNone(verdict["energy_channel_mev"])
        self.assertIsNone(verdict["peak_flux"])
        self.assertEqual(verdict["status"], "use-sep-fluence-model-9-2-2-2")

    def test_applicable_but_window_too_long(self):
        verdict = pf.peakflux_worst_case_verdict(
            "single-event-upset-worst-case", 99, 10, 48.0
        )
        self.assertTrue(verdict["applicable"])
        self.assertEqual(verdict["status"], "window-too-long-use-fluence-model")

    def test_known_textbook_case(self):
        # A latchup-sensitive device with a 12 MeV SEE threshold, worst
        # case quoted at 99% confidence over a 3-hour peak window: rounds
        # up to the 30 MeV channel and stays inside the peak-flux window.
        verdict = pf.peakflux_worst_case_verdict(
            "single-event-latchup-worst-case", 99, 12, 3.0
        )
        self.assertEqual(verdict["energy_channel_mev"], 30)
        self.assertEqual(verdict["status"], "peak-flux-worst-case-ready")
        expected_flux = pf.integral_peak_flux(99, 30)
        self.assertAlmostEqual(verdict["peak_flux"], expected_flux)

    def test_invalid_purpose_raises(self):
        with self.assertRaises(ValueError):
            pf.peakflux_worst_case_verdict("unknown-purpose", 95, 10, 6.0)

    def test_invalid_confidence_level_raises_when_applicable(self):
        with self.assertRaises(ValueError):
            pf.peakflux_worst_case_verdict("see-rate-worst-case", 80, 10, 6.0)

    def test_invalid_duration_raises(self):
        with self.assertRaises(ValueError):
            pf.peakflux_worst_case_verdict("see-rate-worst-case", 95, 10, -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

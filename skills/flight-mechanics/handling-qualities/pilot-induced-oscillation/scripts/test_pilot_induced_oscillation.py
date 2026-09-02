#!/usr/bin/env python3
"""Gate 3 contract test: pilot-induced oscillation categorization and
phase-lag risk.

Exercises scripts/pilot_induced_oscillation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the category
assignment returns Category I/II/III for the linear, rate-limited, and
nonlinear response cases, the phase-lag risk check returns the
low/medium/high band with the phase margin and equivalent time delay
for worked cases, the boundary delays are pinned (0.10 s medium,
0.20 s medium, above 0.20 s high), the suppression measure selection
follows the causes present, and invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pilot_induced_oscillation_logic as pio  # noqa: E402


class CategorizePioTest(unittest.TestCase):
    def test_linear_response_is_category_i(self):
        self.assertEqual(pio.categorize_pio(False, False), "Category I")

    def test_rate_limited_actuators_are_category_ii(self):
        self.assertEqual(pio.categorize_pio(True, False), "Category II")

    def test_nonlinear_response_is_category_iii(self):
        self.assertEqual(pio.categorize_pio(True, True), "Category III")
        self.assertEqual(pio.categorize_pio(False, True), "Category III")

    def test_invalid_flags_raise(self):
        with self.assertRaises(ValueError):
            pio.categorize_pio("yes", False)
        with self.assertRaises(ValueError):
            pio.categorize_pio(True, 1)
        with self.assertRaises(ValueError):
            pio.categorize_pio(None, None)


class PhaseLagRiskTest(unittest.TestCase):
    def test_equivalent_time_delay_worked_cases(self):
        # tau_e = |lag| / (360 * f).
        self.assertAlmostEqual(pio.equivalent_time_delay(-45.0, 1.0),
                               0.125, places=6)
        self.assertAlmostEqual(pio.equivalent_time_delay(-90.0, 2.0),
                               0.125, places=6)
        self.assertAlmostEqual(pio.equivalent_time_delay(-30.0, 2.0),
                               0.0416667, places=6)

    def test_phase_margin_worked_cases(self):
        # margin = 180 + lag for the negative lag.
        self.assertAlmostEqual(pio.phase_margin(-45.0), 135.0, places=6)
        self.assertAlmostEqual(pio.phase_margin(-120.0), 60.0, places=6)
        self.assertAlmostEqual(pio.phase_margin(-160.0), 20.0, places=6)

    def test_risk_bands_worked_cases(self):
        band, margin, tau = pio.phase_lag_risk(-30.0, 2.0)
        self.assertEqual(band, "low")
        self.assertAlmostEqual(margin, 150.0, places=6)
        self.assertAlmostEqual(tau, 0.0416667, places=6)
        band, margin, tau = pio.phase_lag_risk(-60.0, 1.0)
        self.assertEqual(band, "medium")
        self.assertAlmostEqual(margin, 120.0, places=6)
        self.assertAlmostEqual(tau, 0.1666667, places=6)
        band, margin, tau = pio.phase_lag_risk(-100.0, 1.0)
        self.assertEqual(band, "high")
        self.assertAlmostEqual(margin, 80.0, places=6)
        self.assertAlmostEqual(tau, 0.2777778, places=6)

    def test_risk_band_boundaries(self):
        # 0.10 s exactly is medium; 0.20 s exactly is medium; above is
        # high; below 0.10 s is low.
        self.assertEqual(pio.phase_lag_risk(-36.0, 1.0)[0], "medium")
        self.assertEqual(pio.phase_lag_risk(-72.0, 1.0)[0], "medium")
        self.assertEqual(pio.phase_lag_risk(-72.1, 1.0)[0], "high")
        self.assertEqual(pio.phase_lag_risk(-35.9, 1.0)[0], "low")

    def test_invalid_loop_data_raises(self):
        # Phase lag must be a number in (-180, 0).
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(0.0, 1.0)
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(-180.0, 1.0)
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(45.0, 1.0)
        with self.assertRaises(ValueError):
            pio.phase_lag_risk("laggy", 1.0)
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(True, 1.0)
        # Frequency must be positive.
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(-45.0, 0.0)
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(-45.0, -1.0)
        with self.assertRaises(ValueError):
            pio.phase_lag_risk(-45.0, "one")
        # The helpers share the same validation.
        with self.assertRaises(ValueError):
            pio.equivalent_time_delay(-200.0, 1.0)
        with self.assertRaises(ValueError):
            pio.phase_margin(-200.0)
        with self.assertRaises(ValueError):
            pio.phase_margin(0.0)


class SuppressionMeasuresTest(unittest.TestCase):
    def test_no_measures_for_low_risk_clean_loop(self):
        self.assertEqual(
            pio.suppression_measures(-30.0, 2.0), [])

    def test_high_lag_adds_gain_and_phase_compensation(self):
        measures = pio.suppression_measures(-100.0, 1.0)
        self.assertEqual(len(measures), 1)
        self.assertIn("phase lead", measures[0])
        self.assertIn("loop gain", measures[0])

    def test_rate_limiting_measure(self):
        measures = pio.suppression_measures(-30.0, 2.0,
                                            rate_limiting=True)
        self.assertIn("actuator rate limit", measures[0])

    def test_sensitivity_measure(self):
        measures = pio.suppression_measures(-30.0, 2.0,
                                            high_sensitivity=True)
        self.assertIn("control sensitivity", measures[0])

    def test_structural_filter_measure(self):
        measures = pio.suppression_measures(-30.0, 2.0,
                                            structural_filter=True)
        self.assertIn("notch filter", measures[0])

    def test_nonlinear_control_logic_measure(self):
        measures = pio.suppression_measures(-30.0, 2.0,
                                            nonlinear=True)
        self.assertIn("control logic", measures[0])

    def test_all_causes_stack(self):
        measures = pio.suppression_measures(
            -100.0, 1.0, rate_limiting=True, high_sensitivity=True,
            structural_filter=True, nonlinear=True)
        self.assertEqual(len(measures), 5)
        self.assertIn("phase lead", measures[0])
        self.assertIn("actuator rate limit", measures[1])
        self.assertIn("control sensitivity", measures[2])
        self.assertIn("notch filter", measures[3])
        self.assertIn("control logic", measures[4])

    def test_invalid_flags_raise(self):
        with self.assertRaises(ValueError):
            pio.suppression_measures(-30.0, 2.0, rate_limiting="yes")
        with self.assertRaises(ValueError):
            pio.suppression_measures(-30.0, 2.0, nonlinear=1)
        with self.assertRaises(ValueError):
            pio.suppression_measures(0.0, 2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

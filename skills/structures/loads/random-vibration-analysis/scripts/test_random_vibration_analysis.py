#!/usr/bin/env python3
"""Gate 3 contract test: random vibration analysis (structures/loads).

Exercises scripts/random_vibration_analysis_logic.py (stdlib unittest,
offline, deterministic). Contract: SDOF transmissibility
|H(f)|^2 = 1 / ((1 - r^2)^2 + (2*zeta*r)^2) with r = f/f_n, response
PSD G_out(f) = |H(f)|^2 * G_in(f), the Miles closed-form RMS
sigma = sqrt((pi/2) * f_n * Q * G_in(f_n)) with Q = 1/(2*zeta), the
trapezoidal numerical integral of G_out(f) over a supplied spectrum,
the 3-sigma peak, and the equivalent static load factor n_eq = 3*sigma.

Reference values are hand-computed analytic results; invalid inputs
raise ValueError. Worked example: f_n = 40 Hz, zeta = 0.05 (Q = 10),
flat input G = 0.01 g^2/Hz over 20-500 Hz.

Hand calc:
  Q       = 1 / (2 * 0.05) = 10
  sigma   = sqrt((pi/2) * 40 * 10 * 0.01) = sqrt(6.2831853) = 2.5066 g_rms
  3-sigma = 7.52 g
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random_vibration_analysis_logic as rv  # noqa: E402

# Contract-case constants (worked example in SKILL.md).
FN = 40.0          # natural frequency, Hz
ZETA = 0.05        # damping ratio
Q_REF = 10.0       # amplification factor at resonance
G_FLAT = 0.01      # flat input PSD level, g^2/Hz
F_LO = 20.0        # input band lower edge, Hz
F_HI = 500.0       # input band upper edge, Hz
SIGMA_REF = 2.5066   # hand-calc Miles RMS, g_rms
PEAK_3SIGMA_REF = 7.52  # hand-calc 3-sigma peak, g


def flat_band(step, level=G_FLAT, f_lo=F_LO, f_hi=F_HI):
    """Uniform grid spectrum on [f_lo, f_hi] at a constant level."""
    n = int(round((f_hi - f_lo) / step)) + 1
    return [(f_lo + i * step, level) for i in range(n)]


class WorkedExampleTest(unittest.TestCase):
    """The SKILL.md worked example: 40 Hz, Q = 10, 0.01 g^2/Hz flat."""

    def test_miles_sigma_matches_hand_calc(self):
        self.assertLess(abs(rv.miles_sigma(FN, ZETA, G_FLAT) - SIGMA_REF)
                        / SIGMA_REF, 0.01)

    def test_miles_sigma_exact_analytic_value(self):
        # sqrt((pi/2) * 40 * 10 * 0.01) = sqrt(6.2831853) = 2.5066283.
        expected = math.sqrt((math.pi / 2.0) * FN * Q_REF * G_FLAT)
        self.assertAlmostEqual(rv.miles_sigma(FN, ZETA, G_FLAT), expected,
                               places=12)

    def test_three_sigma_level_matches_hand_calc(self):
        # 3 * 2.5066 = 7.5199 ~ 7.52 g, within 1% of the hand calc.
        peak = rv.peak_three_sigma(SIGMA_REF)
        self.assertLess(abs(peak - PEAK_3SIGMA_REF) / PEAK_3SIGMA_REF, 0.01)

    def test_equivalent_static_load_factor_is_three_sigma(self):
        # n_eq = 3 * sigma: the 3-sigma level expressed in g.
        self.assertAlmostEqual(
            rv.equivalent_static_load_factor(SIGMA_REF),
            3.0 * SIGMA_REF, places=12)

    def test_quality_factor_matches_hand_calc(self):
        self.assertAlmostEqual(rv.quality_factor(ZETA), Q_REF, places=12)

    def test_quality_factor_identity(self):
        # Q = 1 / (2*zeta), so 2*zeta*Q = 1 for any valid zeta.
        for z in (0.005, 0.02, 0.05, 0.2, 0.7, 0.99):
            self.assertAlmostEqual(2.0 * z * rv.quality_factor(z), 1.0,
                                   places=12)

    def test_numerical_cross_check_within_few_percent_of_miles(self):
        # Flat 0.01 g^2/Hz band 20-500 Hz at 2 Hz resolution: the
        # trapezoidal integral of G_out reproduces the Miles value
        # within a few percent (the small deficit is the input band
        # truncation below 20 Hz, far from the resonance at 40 Hz).
        sigma_num = rv.numerical_sigma(flat_band(2.0), FN, ZETA)
        sigma_miles = rv.miles_sigma(FN, ZETA, G_FLAT)
        self.assertLess(abs(sigma_num / sigma_miles - 1.0), 0.03)

    def test_numerical_with_one_hz_grid_matches_module_report(self):
        # The module __main__ report value for the 20-500 Hz band at
        # 1 Hz resolution: 2.4577 g_rms (about 2% below Miles).
        sigma_num = rv.numerical_sigma(flat_band(1.0), FN, ZETA)
        self.assertLess(abs(sigma_num - 2.4577) / 2.4577, 0.002)

    def test_miles_round_trip_recovers_input_psd(self):
        # sigma^2 = (pi/2)*f_n*Q*G inverts to G = sigma^2 / ((pi/2)*f_n*Q).
        sigma = rv.miles_sigma(FN, ZETA, G_FLAT)
        recovered = sigma * sigma / ((math.pi / 2.0) * FN * Q_REF)
        self.assertAlmostEqual(recovered, G_FLAT, places=12)

    def test_zero_input_psd_gives_zero_rms(self):
        self.assertEqual(rv.miles_sigma(FN, ZETA, 0.0), 0.0)
        self.assertEqual(rv.numerical_sigma(flat_band(2.0, level=0.0),
                                            FN, ZETA), 0.0)


class TransmissibilityTest(unittest.TestCase):
    def test_transmissibility_squared_at_resonance_is_q_squared(self):
        # |H(f_n)|^2 = 1 / (2*zeta)^2 = Q^2 = 100 for zeta = 0.05.
        self.assertAlmostEqual(
            rv.transmissibility_squared(FN, FN, ZETA), Q_REF ** 2, places=10)

    def test_transmissibility_at_resonance_is_q(self):
        self.assertAlmostEqual(
            rv.transmissibility(FN, FN, ZETA), Q_REF, places=10)

    def test_transmissibility_at_dc_is_unity(self):
        # At f = 0 the acceleration ratio |H| = 1 (rigid body, no
        # relative amplification of a static input).
        self.assertAlmostEqual(rv.transmissibility_squared(0.0, FN, ZETA),
                               1.0, places=10)
        self.assertAlmostEqual(rv.transmissibility(0.0, FN, ZETA), 1.0,
                               places=10)

    def test_high_frequency_rolloff_is_fourth_power(self):
        # Far above resonance |H|^2 ~ (f_n/f)^4: at f = 20*f_n that is
        # 1/160000 (the (2*zeta*r)^2 term is negligible against
        # (1-r^2)^2, contributing under 0.5%).
        f = 20.0 * FN
        expected = 1.0 / ((1.0 - 400.0) ** 2 + (2.0 * ZETA * 20.0) ** 2)
        self.assertAlmostEqual(
            rv.transmissibility_squared(f, FN, ZETA), expected, places=12)
        self.assertLess(abs(expected - (FN / f) ** 4) / (FN / f) ** 4, 0.01)

    def test_transmissibility_is_positive(self):
        for f in (0.0, 1.0, 10.0, FN, 2.0 * FN, 500.0):
            self.assertGreater(rv.transmissibility_squared(f, FN, ZETA), 0.0)

    def test_damped_resonance_frequency(self):
        # Peak of |H(f)|^2 at f_n*sqrt(1 - 2*zeta^2) = 39.8999 Hz.
        expected = FN * math.sqrt(1.0 - 2.0 * ZETA * ZETA)
        self.assertAlmostEqual(
            rv.damped_resonance_frequency(FN, ZETA), expected, places=12)

    def test_response_psd_peaks_near_the_damped_resonance(self):
        # The dominant response frequency is below f_n by 2*zeta^2.
        self.assertLess(rv.damped_resonance_frequency(FN, ZETA), FN)
        self.assertGreater(rv.damped_resonance_frequency(FN, ZETA),
                           FN * (1.0 - 0.01))

    def test_heavy_damping_has_no_amplification_peak(self):
        # For zeta >= 1/sqrt(2) |H(f)|^2 is monotone decreasing from 1.
        self.assertEqual(rv.damped_resonance_frequency(FN, 0.9), 0.0)
        self.assertLess(rv.transmissibility_squared(FN, FN, 0.9), 1.0)

    def test_invalid_inputs_raise_value_error(self):
        for f in (-1.0, -FN):
            with self.assertRaises(ValueError):
                rv.transmissibility_squared(f, FN, ZETA)
        for fn in (0.0, -40.0):
            with self.assertRaises(ValueError):
                rv.transmissibility_squared(40.0, fn, ZETA)
        with self.assertRaises(ValueError):
            rv.transmissibility_squared(40.0, FN, None)
        with self.assertRaises(ValueError):
            rv.transmissibility_squared(40.0, FN, "high")


class ResponsePsdTest(unittest.TestCase):
    def test_response_psd_at_resonance_amplifies_by_q_squared(self):
        points = rv.response_psd([(20.0, G_FLAT), (FN, G_FLAT),
                                  (500.0, G_FLAT)], FN, ZETA)
        g_out_fn = dict(points)[FN]
        self.assertAlmostEqual(g_out_fn, G_FLAT * Q_REF ** 2, places=10)

    def test_response_psd_off_resonance_is_barely_amplified(self):
        points = rv.response_psd([(20.0, G_FLAT)], FN, ZETA)
        # At f = 20 Hz, r = 0.5: |H|^2 = 1/(0.5625 + 0.0025) = 1.7699.
        expected = G_FLAT / (0.5625 + 0.0025)
        self.assertAlmostEqual(points[0][1], expected, places=10)

    def test_response_psd_preserves_grid_and_is_nonnegative(self):
        spec = flat_band(5.0)
        out = rv.response_psd(spec, FN, ZETA)
        self.assertEqual(len(out), len(spec))
        for (f_in, _), (f_out, g_out) in zip(spec, out):
            self.assertEqual(f_in, f_out)
            self.assertGreaterEqual(g_out, 0.0)

    def test_response_psd_with_zero_input_is_zero(self):
        out = rv.response_psd([(20.0, 0.0), (40.0, 0.0)], FN, ZETA)
        for _, g_out in out:
            self.assertEqual(g_out, 0.0)

    def test_invalid_spectra_raise_value_error(self):
        for spec in ([], None, [(20.0, -0.01), (40.0, 0.01)],
                     [(-20.0, 0.01), (40.0, 0.01)],
                     [(40.0, 0.01), (20.0, 0.01)],
                     [("a", 0.01), (40.0, 0.01)],
                     [20.0, 40.0]):
            with self.assertRaises(ValueError):
                rv.response_psd(spec, FN, ZETA)


class NumericalIntegrationTest(unittest.TestCase):
    def test_sigma_scales_with_sqrt_of_input_level(self):
        # Doubling the flat input PSD multiplies sigma by sqrt(2).
        s1 = rv.numerical_sigma(flat_band(2.0, level=0.01), FN, ZETA)
        s2 = rv.numerical_sigma(flat_band(2.0, level=0.02), FN, ZETA)
        self.assertAlmostEqual(s2 / s1, math.sqrt(2.0), places=6)

    def test_miles_sigma_scales_with_sqrt_of_input_level(self):
        self.assertAlmostEqual(
            rv.miles_sigma(FN, ZETA, 0.04) / rv.miles_sigma(FN, ZETA, 0.01),
            2.0, places=12)

    def test_miles_sigma_scales_with_sqrt_of_frequency(self):
        # Four times the natural frequency at fixed Q doubles sigma.
        self.assertAlmostEqual(
            rv.miles_sigma(4.0 * FN, ZETA, G_FLAT)
            / rv.miles_sigma(FN, ZETA, G_FLAT),
            2.0, places=12)

    def test_higher_damping_reduces_sigma(self):
        # Q halves from zeta 0.05 to 0.10, so sigma drops by sqrt(2).
        self.assertAlmostEqual(
            rv.miles_sigma(FN, 0.10, G_FLAT)
            / rv.miles_sigma(FN, 0.05, G_FLAT),
            1.0 / math.sqrt(2.0), places=12)

    def test_finite_band_integral_is_below_miles(self):
        # The 20-500 Hz band truncates the low-frequency tail below
        # 20 Hz, so the numerical value sits slightly under Miles.
        sigma_num = rv.numerical_sigma(flat_band(0.5), FN, ZETA)
        self.assertLess(sigma_num, rv.miles_sigma(FN, ZETA, G_FLAT))
        self.assertGreater(sigma_num, 0.95 * rv.miles_sigma(FN, ZETA, G_FLAT))

    def test_integration_needs_at_least_two_points(self):
        with self.assertRaises(ValueError):
            rv.numerical_sigma([(20.0, G_FLAT)], FN, ZETA)
        with self.assertRaises(ValueError):
            rv.numerical_sigma([], FN, ZETA)

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            rv.numerical_sigma(flat_band(2.0), 0.0, ZETA)
        with self.assertRaises(ValueError):
            rv.numerical_sigma(flat_band(2.0), FN, 1.0)
        with self.assertRaises(ValueError):
            rv.numerical_sigma(flat_band(2.0), FN, -0.05)


class InterpolationTest(unittest.TestCase):
    def test_exact_at_spectrum_point(self):
        spec = [(20.0, 0.005), (40.0, 0.01), (500.0, 0.001)]
        self.assertAlmostEqual(rv.interpolate_psd(spec, 40.0), 0.01,
                               places=12)

    def test_linear_between_points(self):
        spec = [(20.0, 0.0), (60.0, 0.02)]
        self.assertAlmostEqual(rv.interpolate_psd(spec, 40.0), 0.01,
                               places=12)

    def test_outside_coverage_returns_none(self):
        spec = [(20.0, 0.01), (500.0, 0.01)]
        self.assertIsNone(rv.interpolate_psd(spec, 10.0))
        self.assertIsNone(rv.interpolate_psd(spec, 600.0))

    def test_single_point_spectrum(self):
        spec = [(40.0, 0.01)]
        self.assertAlmostEqual(rv.interpolate_psd(spec, 40.0), 0.01,
                               places=12)
        self.assertIsNone(rv.interpolate_psd(spec, 41.0))


class AnalysisDictTest(unittest.TestCase):
    def setUp(self):
        self.result = rv.random_vibration_analysis(FN, ZETA, flat_band(2.0))

    def test_required_keys_present(self):
        for key in ("sigma_rms_g", "psd_response_points", "f_n", "q",
                    "dominant_response_frequency"):
            self.assertIn(key, self.result)

    def test_analysis_reports_inputs(self):
        self.assertEqual(self.result["f_n"], FN)
        self.assertAlmostEqual(self.result["q"], Q_REF, places=12)
        self.assertAlmostEqual(self.result["zeta"], ZETA, places=12)
        self.assertAlmostEqual(self.result["dominant_response_frequency"],
                               FN * math.sqrt(1.0 - 2.0 * ZETA * ZETA),
                               places=10)

    def test_analysis_miles_matches_direct_call(self):
        # Flat input: the dict's Miles sigma equals the closed form with
        # the interpolated level at f_n.
        self.assertAlmostEqual(self.result["sigma_miles_g"],
                               rv.miles_sigma(FN, ZETA, G_FLAT), places=10)

    def test_analysis_peak_and_neq_are_three_sigma(self):
        self.assertAlmostEqual(self.result["peak_3sigma_g"],
                               3.0 * self.result["sigma_rms_g"], places=12)
        self.assertAlmostEqual(self.result["n_eq_g"],
                               self.result["peak_3sigma_g"], places=12)

    def test_analysis_worked_example_3sigma_peak(self):
        # 3 * 2.4577 (1 Hz grid) = 7.37 g numerical; the Miles-based
        # screening level is 3 * 2.5066 = 7.52 g.
        res = rv.random_vibration_analysis(FN, ZETA, flat_band(1.0))
        self.assertLess(abs(3.0 * res["sigma_miles_g"] - PEAK_3SIGMA_REF)
                        / PEAK_3SIGMA_REF, 0.01)
        self.assertLess(abs(res["peak_3sigma_g"] - 3.0 * 2.4577), 0.01)

    def test_analysis_none_miles_when_fn_outside_band(self):
        # Natural frequency above the input band: no Miles value, the
        # numerical integral still returns the off-resonance response.
        spec = [(20.0, G_FLAT), (30.0, G_FLAT)]
        res = rv.random_vibration_analysis(40.0, ZETA, spec)
        self.assertIsNone(res["sigma_miles_g"])
        self.assertGreater(res["sigma_rms_g"], 0.0)

    def test_analysis_single_point_spectrum_raises(self):
        with self.assertRaises(ValueError):
            rv.random_vibration_analysis(FN, ZETA, [(20.0, G_FLAT)])

    def test_analysis_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            rv.random_vibration_analysis(0.0, ZETA, flat_band(2.0))
        with self.assertRaises(ValueError):
            rv.random_vibration_analysis(FN, 0.0, flat_band(2.0))
        with self.assertRaises(ValueError):
            rv.random_vibration_analysis(FN, 1.5, flat_band(2.0))
        with self.assertRaises(ValueError):
            rv.random_vibration_analysis(FN, ZETA,
                                         [(20.0, -0.01), (40.0, 0.01)])
        with self.assertRaises(ValueError):
            rv.random_vibration_analysis(FN, ZETA, [])

    def test_peak_and_neq_reject_negative_sigma(self):
        with self.assertRaises(ValueError):
            rv.peak_three_sigma(-1.0)
        with self.assertRaises(ValueError):
            rv.equivalent_static_load_factor(-1.0)
        with self.assertRaises(ValueError):
            rv.peak_three_sigma(None)


if __name__ == "__main__":
    unittest.main()

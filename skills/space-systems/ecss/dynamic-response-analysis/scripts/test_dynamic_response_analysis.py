"""
Contract tests for dynamic_response_analysis_logic.py.

Run: python3 test_dynamic_response_analysis.py
Expects: OK on stdout (stdlib unittest, offline, deterministic).
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import dynamic_response_analysis_logic as dra


class TestDynamicAmplificationFactor(unittest.TestCase):

    def test_daf_static_excitation_is_unity(self):
        """DAF at f=0 (static limit) must equal 1.0 for any damping."""
        result = dra.dynamic_amplification_factor(fn_hz=100.0, f_hz=0.0, damping_ratio=0.05)
        self.assertAlmostEqual(result, 1.0, places=10)

    def test_daf_at_resonance_equals_half_over_damping(self):
        """At resonance (r=1), DAF = 1/(2*zeta)."""
        zeta = 0.05
        result = dra.dynamic_amplification_factor(fn_hz=100.0, f_hz=100.0, damping_ratio=zeta)
        expected = 1.0 / (2.0 * zeta)  # = 10.0
        self.assertAlmostEqual(result, expected, places=8)

    def test_daf_high_frequency_approaches_zero(self):
        """At very high tuning ratio (r >> 1), DAF approaches 0."""
        result = dra.dynamic_amplification_factor(fn_hz=10.0, f_hz=10000.0, damping_ratio=0.05)
        self.assertLess(result, 0.001)

    def test_daf_invalid_zero_natural_frequency(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.dynamic_amplification_factor(fn_hz=0.0, f_hz=50.0, damping_ratio=0.05)

    def test_daf_invalid_negative_excitation_frequency(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.dynamic_amplification_factor(fn_hz=100.0, f_hz=-1.0, damping_ratio=0.05)

    def test_daf_invalid_damping_zero(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.dynamic_amplification_factor(fn_hz=100.0, f_hz=50.0, damping_ratio=0.0)

    def test_daf_invalid_damping_one(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.dynamic_amplification_factor(fn_hz=100.0, f_hz=50.0, damping_ratio=1.0)


class TestSinePeakResponse(unittest.TestCase):

    def test_peak_response_at_resonance(self):
        """Peak response at resonance = static * DAF = static / (2*zeta)."""
        static = 100.0
        zeta = 0.05
        fn = 100.0
        result = dra.sine_peak_response(static, fn_hz=fn, f_hz=fn, damping_ratio=zeta)
        expected = static / (2.0 * zeta)
        self.assertAlmostEqual(result, expected, places=6)

    def test_peak_response_static_case(self):
        """With f_exc=0 the dynamic response equals the static response."""
        static = 50.0
        result = dra.sine_peak_response(static, fn_hz=200.0, f_hz=0.0, damping_ratio=0.03)
        self.assertAlmostEqual(result, static, places=10)

    def test_peak_response_negative_static_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.sine_peak_response(-10.0, fn_hz=100.0, f_hz=50.0, damping_ratio=0.05)


class TestMilesEquation(unittest.TestCase):

    def test_rms_known_value(self):
        """
        fn=100 Hz, zeta=0.05 → Q=10, PSD=0.1 g^2/Hz.
        RMS = sqrt(pi/2 * 100 * 10 * 0.1) = sqrt(pi*50) ≈ 12.5331 g.
        """
        fn = 100.0
        zeta = 0.05
        psd = 0.1
        expected = math.sqrt((math.pi / 2.0) * fn * (1.0 / (2.0 * zeta)) * psd)
        result = dra.miles_rms_acceleration(fn, zeta, psd)
        self.assertAlmostEqual(result, expected, places=8)

    def test_3sigma_is_three_times_rms(self):
        fn = 80.0
        zeta = 0.03
        psd = 0.04
        rms = dra.miles_rms_acceleration(fn, zeta, psd)
        sigma3 = dra.miles_3sigma_acceleration(fn, zeta, psd)
        self.assertAlmostEqual(sigma3, 3.0 * rms, places=10)

    def test_rms_scales_with_sqrt_fn(self):
        """Doubling fn (all else equal) should multiply RMS by sqrt(2)."""
        zeta = 0.05
        psd = 0.1
        rms1 = dra.miles_rms_acceleration(100.0, zeta, psd)
        rms2 = dra.miles_rms_acceleration(200.0, zeta, psd)
        self.assertAlmostEqual(rms2 / rms1, math.sqrt(2.0), places=8)

    def test_rms_invalid_zero_psd(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.miles_rms_acceleration(100.0, 0.05, 0.0)

    def test_rms_invalid_negative_fn(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.miles_rms_acceleration(-50.0, 0.05, 0.1)


class TestSrsHalfSine(unittest.TestCase):

    def test_srs_residual_region(self):
        """tau=0.1 < 0.5: SRS ≈ 2*pi*0.1*A = 0.6283*A."""
        A = 10.0
        D = 0.001  # s → fn*D = 100*0.001 = 0.1
        result = dra.srs_half_sine_peak(fn_hz=100.0, pulse_amplitude_g=A, pulse_duration_s=D)
        expected = 2.0 * math.pi * 0.1 * A
        self.assertAlmostEqual(result, expected, places=8)

    def test_srs_primary_region_tau_2_gives_amplitude(self):
        """tau=2: sin(pi*2)=0 → SRS = min(A*(1+0), 2A) = A."""
        A = 20.0
        fn = 100.0
        D = 0.02  # fn*D = 2.0
        result = dra.srs_half_sine_peak(fn_hz=fn, pulse_amplitude_g=A, pulse_duration_s=D)
        self.assertAlmostEqual(result, A, places=8)

    def test_srs_primary_region_tau_1p5_gives_2A(self):
        """tau=1.5: |sin(pi*1.5)|=1 → primary=2A; min(2A, 2A)=2A."""
        A = 15.0
        fn = 100.0
        D = 0.015  # fn*D = 1.5
        result = dra.srs_half_sine_peak(fn_hz=fn, pulse_amplitude_g=A, pulse_duration_s=D)
        self.assertAlmostEqual(result, 2.0 * A, places=8)

    def test_srs_transitional_region(self):
        """tau=0.75: SRS = 2*A*sin(pi*0.75) = 2*A*sin(135°) = 2*A*(sqrt(2)/2) = A*sqrt(2)."""
        A = 10.0
        fn = 100.0
        D = 0.0075  # fn*D = 0.75
        result = dra.srs_half_sine_peak(fn_hz=fn, pulse_amplitude_g=A, pulse_duration_s=D)
        expected = 2.0 * A * math.sin(math.pi * 0.75)
        self.assertAlmostEqual(result, expected, places=8)

    def test_srs_bounded_by_2A(self):
        """SRS must never exceed 2*A regardless of tau."""
        A = 5.0
        for fn in [50.0, 100.0, 200.0, 500.0]:
            for D in [0.001, 0.005, 0.01, 0.02]:
                result = dra.srs_half_sine_peak(fn_hz=fn, pulse_amplitude_g=A, pulse_duration_s=D)
                self.assertLessEqual(result, 2.0 * A + 1e-10, msg=f"fn={fn}, D={D}")

    def test_srs_invalid_zero_amplitude(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.srs_half_sine_peak(fn_hz=100.0, pulse_amplitude_g=0.0, pulse_duration_s=0.01)

    def test_srs_invalid_zero_duration(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.srs_half_sine_peak(fn_hz=100.0, pulse_amplitude_g=10.0, pulse_duration_s=0.0)


class TestCategorizeLoad(unittest.TestCase):

    def test_all_valid_types_accepted(self):
        for load in ("sine", "random", "shock", "transient"):
            self.assertEqual(dra.categorize_load(load), load)

    def test_case_insensitive_matching(self):
        self.assertEqual(dra.categorize_load("SINE"), "sine")
        self.assertEqual(dra.categorize_load("Random"), "random")
        self.assertEqual(dra.categorize_load("SHOCK"), "shock")

    def test_whitespace_stripped(self):
        self.assertEqual(dra.categorize_load("  random  "), "random")

    def test_unrecognized_type_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.categorize_load("acoustic")

    def test_empty_string_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.categorize_load("")


class TestAnalysisSummary(unittest.TestCase):

    def test_sine_summary_keys_and_values(self):
        result = dra.analysis_summary(
            fn_hz=100.0, damping_ratio=0.05, load_type="sine",
            f_exc_hz=100.0, static_response=10.0
        )
        self.assertEqual(result["load_type"], "sine")
        self.assertIn("daf", result)
        self.assertIn("peak_response", result)
        # at resonance, peak = static / (2*zeta)
        self.assertAlmostEqual(result["peak_response"], 10.0 / (2 * 0.05), places=6)

    def test_random_summary_keys_and_values(self):
        result = dra.analysis_summary(
            fn_hz=100.0, damping_ratio=0.05, load_type="random",
            psd_g2_per_hz=0.1
        )
        self.assertEqual(result["load_type"], "random")
        self.assertIn("rms_g", result)
        self.assertIn("sigma3_g", result)
        self.assertAlmostEqual(result["sigma3_g"], 3.0 * result["rms_g"], places=10)

    def test_shock_summary_keys_and_values(self):
        result = dra.analysis_summary(
            fn_hz=100.0, damping_ratio=0.05, load_type="shock",
            pulse_amplitude_g=20.0, pulse_duration_s=0.01
        )
        self.assertEqual(result["load_type"], "shock")
        self.assertIn("tau", result)
        self.assertIn("srs_g", result)
        self.assertAlmostEqual(result["tau"], 1.0, places=10)

    def test_transient_summary_returns_note(self):
        result = dra.analysis_summary(
            fn_hz=100.0, damping_ratio=0.05, load_type="transient"
        )
        self.assertEqual(result["load_type"], "transient")
        self.assertIn("note", result)

    def test_sine_missing_kwargs_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.analysis_summary(fn_hz=100.0, damping_ratio=0.05, load_type="sine")

    def test_random_missing_psd_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.analysis_summary(fn_hz=100.0, damping_ratio=0.05, load_type="random")

    def test_shock_missing_kwargs_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.analysis_summary(fn_hz=100.0, damping_ratio=0.05, load_type="shock")

    def test_unrecognized_load_type_raises(self):
        with self.assertRaises(dra.AnalysisInputError):
            dra.analysis_summary(fn_hz=100.0, damping_ratio=0.05, load_type="quasi-static")


if __name__ == "__main__":
    unittest.main()

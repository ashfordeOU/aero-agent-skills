"""Contract test for fir_filter_design_logic (wave-31 leaf).

Deterministic stdlib unittest, offline. Runs with:

    python3 scripts/test_fir_filter_design.py

and must exit 0. Asserts the spec worked-example anchors for a Hamming
windowed-sinc lowpass at fs = 1000 Hz, fc = 100 Hz, N = 101 taps (DC
gain 1.0, gain 1.00319 at 50 Hz, gain 0.50039 at the cutoff, gains
below 0.01 at 150 Hz and below 0.001 at 300 Hz, group delay 50.0
samples, steady-state cosine amplitude 1.00319), window formulas and
symmetry, exact convenience-dict keys, ValueError rejection of every
non-physical input in the spec validation list, direct-convolution
round trips, the design self-check, and run-to-run determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fir_filter_design_logic import (  # noqa: E402
    WINDOWS,
    design_check,
    design_lowpass,
    filter_signal,
    gain_at,
    group_delay_samples,
    ideal_lowpass_taps,
    magnitude_response_db,
    window_coefficients,
)

FS = 1000.0
FC = 100.0
N = 101
COEFFS = design_lowpass(FC, FS, N, "hamming")["coefficients"]


class TestWindows(unittest.TestCase):
    def test_window_anchor_values(self):
        self.assertEqual(window_coefficients("rectangular", 3), [1.0, 1.0, 1.0])
        for w, expected in ((window_coefficients("hann", 3), (0.0, 1.0, 0.0)),
                            (window_coefficients("hamming", 3), (0.08, 1.0, 0.08)),
                            (window_coefficients("blackman", 3), (0.0, 1.0, 0.0))):
            for got, want in zip(w, expected):
                self.assertAlmostEqual(got, want, places=12)
        for window in WINDOWS:  # single-tap edge: the center limit value
            self.assertEqual(window_coefficients(window, 1), [1.0])

    def test_hamming_window_symmetric(self):
        w = window_coefficients("hamming", N)
        for n in range(N):
            self.assertAlmostEqual(w[n], w[N - 1 - n], places=12)

    def test_window_rejects_bad_inputs(self):
        for window in ("kaiser", "bartlett", "", "HAMMING"):
            with self.assertRaises(ValueError):
                window_coefficients(window, 101)
        for bad_n in (0, -3, 2.5, 101.0):
            with self.assertRaises(ValueError):
                window_coefficients("hamming", bad_n)


class TestIdealTaps(unittest.TestCase):
    def test_center_tap_limit_value(self):
        taps = ideal_lowpass_taps(FC, FS, N)
        self.assertAlmostEqual(taps[50], 2.0 * FC / FS, places=12)
        self.assertEqual(len(taps), N)

    def test_ideal_rejects_non_physical(self):
        for fc in (0.0, -100.0):
            with self.assertRaises(ValueError):
                ideal_lowpass_taps(fc, FS, N)
        for fs in (0.0, -1000.0):
            with self.assertRaises(ValueError):
                ideal_lowpass_taps(FC, fs, N)
        for fc in (500.0, 600.0, 1000.0):  # at or above Nyquist
            with self.assertRaises(ValueError):
                ideal_lowpass_taps(fc, FS, N)
        with self.assertRaises(ValueError):
            ideal_lowpass_taps(FC, FS, 0)


class TestDesignLowpass(unittest.TestCase):
    def test_convenience_dict_exact_keys(self):
        d = design_lowpass(FC, FS, N, "hamming")
        self.assertEqual(
            set(d.keys()),
            {"coefficients", "num_taps", "cutoff_hz", "sample_rate_hz",
             "window", "group_delay_samples", "dc_gain"},
        )
        self.assertEqual(d["num_taps"], N)
        self.assertEqual(d["cutoff_hz"], FC)
        self.assertEqual(d["sample_rate_hz"], FS)
        self.assertEqual(d["window"], "hamming")

    def test_dc_gain_normalized(self):
        d = design_lowpass(FC, FS, N, "hamming")
        self.assertAlmostEqual(d["dc_gain"], 1.0, places=9)
        self.assertAlmostEqual(sum(d["coefficients"]), 1.0, places=9)

    def test_coefficient_symmetry_linear_phase(self):
        for n in range(N):
            self.assertAlmostEqual(COEFFS[n], COEFFS[N - 1 - n], places=12)

    def test_group_delay_field(self):
        self.assertEqual(design_lowpass(FC, FS, N)["group_delay_samples"], 50.0)

    def test_even_taps_rejected(self):
        for bad_n in (100, 102, 2):
            with self.assertRaises(ValueError):
                design_lowpass(FC, FS, bad_n, "hamming")

    def test_unknown_window_rejected(self):
        with self.assertRaises(ValueError):
            design_lowpass(FC, FS, N, "kaiser")

    def test_non_physical_design_inputs_rejected(self):
        with self.assertRaises(ValueError):
            design_lowpass(0.0, FS, N)
        with self.assertRaises(ValueError):
            design_lowpass(FC, -1.0, N)
        with self.assertRaises(ValueError):
            design_lowpass(500.0, FS, N)  # cutoff at Nyquist
        with self.assertRaises(ValueError):
            design_lowpass(FC, FS, 0)

    def test_single_tap_design(self):
        for window in WINDOWS:
            d = design_lowpass(FC, FS, 1, window)
            self.assertAlmostEqual(d["coefficients"][0], 1.0, places=12)
            self.assertEqual(d["group_delay_samples"], 0.0)

    def test_all_windows_design_deterministic(self):
        for window in WINDOWS:
            d1 = design_lowpass(FC, FS, 51, window)
            d2 = design_lowpass(FC, FS, 51, window)
            self.assertAlmostEqual(d1["dc_gain"], 1.0, places=9)
            self.assertEqual(len(d1["coefficients"]), 51)
            for n in range(51):
                self.assertAlmostEqual(
                    d1["coefficients"][n], d1["coefficients"][50 - n], places=12)
            self.assertEqual(d1["coefficients"], d2["coefficients"])  # no RNG


class TestWorkedExample(unittest.TestCase):
    def test_dc_gain_and_group_delay_anchors(self):
        self.assertAlmostEqual(gain_at(COEFFS, 0.0, FS), 1.0, places=6)
        self.assertEqual(group_delay_samples(N), 50.0)

    def test_passband_50hz_in_bounds(self):
        g = gain_at(COEFFS, 50.0, FS)
        self.assertAlmostEqual(g, 1.00319, delta=5e-4)
        self.assertTrue(0.98 <= g <= 1.02)

    def test_cutoff_100hz_about_minus_6db(self):
        g = gain_at(COEFFS, 100.0, FS)
        self.assertAlmostEqual(g, 0.50039, delta=5e-4)
        self.assertTrue(0.45 <= g <= 0.55)
        self.assertAlmostEqual(magnitude_response_db(COEFFS, 100.0, FS),
                               -6.0138, delta=5e-3)

    def test_stopband_150hz(self):
        g = gain_at(COEFFS, 150.0, FS)
        self.assertAlmostEqual(g, 0.000975, delta=5e-4)
        self.assertLess(g, 0.01)

    def test_stopband_300hz(self):
        g = gain_at(COEFFS, 300.0, FS)
        self.assertAlmostEqual(g, 0.000263, delta=5e-5)
        self.assertLess(g, 0.001)

    def test_cosine_steady_state_amplitude(self):
        x = [math.cos(2.0 * math.pi * 50.0 * n / FS) for n in range(400)]
        y = filter_signal(COEFFS, x)
        steady = max(abs(v) for v in y[250:350])  # after the 50-sample delay
        self.assertAlmostEqual(steady, 1.00319, delta=1e-3)
        self.assertTrue(0.95 <= steady <= 1.05)


class TestMagnitudeResponse(unittest.TestCase):
    def test_db_matches_linear_gain(self):
        for f in (37.3, 100.0, 200.0, 499.0):
            expected = 20.0 * math.log10(gain_at(COEFFS, f, FS))
            self.assertAlmostEqual(magnitude_response_db(COEFFS, f, FS),
                                   expected, places=10)

    def test_dc_magnitude_is_zero_db(self):
        self.assertAlmostEqual(magnitude_response_db(COEFFS, 0.0, FS), 0.0,
                               places=10)

    def test_nyquist_probe_allowed(self):
        g = gain_at(COEFFS, FS / 2.0, FS)
        self.assertGreaterEqual(g, 0.0)
        self.assertLess(g, 1.0)

    def test_magnitude_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            magnitude_response_db(COEFFS, 100.0, -1.0)
        with self.assertRaises(ValueError):
            magnitude_response_db(COEFFS, -1.0, FS)
        with self.assertRaises(ValueError):
            magnitude_response_db(COEFFS, 501.0, FS)  # above Nyquist
        with self.assertRaises(ValueError):
            magnitude_response_db([], 100.0, FS)
        with self.assertRaises(ValueError):
            gain_at(COEFFS, 100.0, 0.0)

    def test_delay_free_filter_zero_hz_equals_dc_gain(self):
        self.assertEqual(gain_at([1.0], 0.0, FS), sum([1.0]))


class TestGroupDelay(unittest.TestCase):
    def test_values_and_validation(self):
        self.assertEqual(group_delay_samples(1), 0.0)
        self.assertEqual(group_delay_samples(11), 5.0)
        self.assertEqual(group_delay_samples(101), 50.0)
        for bad in (0, -2, 2.5, 101.0):
            with self.assertRaises(ValueError):
                group_delay_samples(bad)


class TestFilterSignal(unittest.TestCase):
    def test_identity_and_output_length(self):
        x = [1.0, -2.0, 3.5, 0.25]
        self.assertEqual(filter_signal([1.0], x), x)
        for length in (1, 7, 400):  # output length always equals input
            xlen = [1.0] * length
            self.assertEqual(len(filter_signal(COEFFS, xlen)), length)

    def test_impulse_response_equals_coefficients(self):
        x = [1.0] + [0.0] * 200
        y = filter_signal(COEFFS, x)
        for k, b in enumerate(COEFFS):
            self.assertAlmostEqual(y[k], b, places=12)
        for k in range(N, 201):
            self.assertEqual(y[k], 0.0)

    def test_dc_steady_state(self):
        x = [5.0] * 400
        y = filter_signal(COEFFS, x)
        for v in y[100:]:
            self.assertAlmostEqual(v, 5.0, places=3)

    def test_rejects_empty_inputs(self):
        with self.assertRaises(ValueError):
            filter_signal([], [1.0, 2.0])
        with self.assertRaises(ValueError):
            filter_signal(COEFFS, [])

    def test_round_trip_10hz_sine_preserved(self):
        x = [math.sin(2.0 * math.pi * 10.0 * n / FS) for n in range(1000)]
        y = filter_signal(COEFFS, x)
        amplitude = max(abs(v) for v in y[100:])
        self.assertTrue(0.95 <= amplitude <= 1.05)


class TestDesignCheck(unittest.TestCase):
    def test_work_example_anchors(self):
        chk = design_check(COEFFS, FC, FS)
        self.assertAlmostEqual(chk["dc_gain"], 1.0, places=6)
        self.assertAlmostEqual(chk["cutoff_gain_db"], -6.0138, delta=5e-3)
        self.assertAlmostEqual(chk["stopband_gain_db"], -65.144, delta=5e-3)
        self.assertAlmostEqual(chk["stopband_attenuation_db"], 65.144,
                               delta=5e-3)
        self.assertGreater(chk["stopband_attenuation_db"], 40.0)

    def test_attenuation_is_dc_level_minus_stopband(self):
        chk = design_check(COEFFS, 50.0, FS)  # stopband probe at 100 Hz
        dc_db = 20.0 * math.log10(chk["dc_gain"])
        self.assertAlmostEqual(chk["stopband_attenuation_db"],
                               dc_db - chk["stopband_gain_db"], places=9)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            design_check([], FC, FS)
        with self.assertRaises(ValueError):
            design_check(COEFFS, -1.0, FS)
        with self.assertRaises(ValueError):
            design_check(COEFFS, FC, 0.0)
        with self.assertRaises(ValueError):  # 2*fc probe above Nyquist
            design_check(COEFFS, 300.0, FS)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Gate 3 contract test: power spectral density logic (Welch method).

Exercises scripts/power_spectral_density_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3 -
Hann window weights, the internal iterative radix-2 Cooley-Tukey
transform, the one-sided density-scaled periodogram (DC and Nyquist
bins not doubled), the Welch averaged periodogram PSD with its
frequency axis, the equivalent noise bandwidth, the integrated total
power, the convenience summary dict, and ValueError rejection of
non-physical inputs.

Analytic anchors (fs = 1024 Hz, M = 256, Hann window, 50% overlap,
8192-sample record, exactly 63 segments):
  hann_window(256) sums to 128.0 (M/2) with sum of squares 96.0 (3M/8)
  ENBW = 1024 * 96 / 128^2 = 6.0 Hz
  60 Hz sine (bin 15), amplitude A = 1: peak density 0.083333333 =
    A^2 / (2 ENBW) to 1e-6 relative; integrated power 0.500000000 =
    A^2 / 2
  amplitude A = 0.5: peak density 0.020833333, exactly one quarter
  DC and Nyquist bins are not doubled: a constant record and a
    (-1)^n record each integrate to their mean square with P[0] and
    P[M/2] at the undoubled value 0.166666667
  tone plus seeded Gaussian noise (variance 0.2, sigma 0.447, seed 21):
    peak density about 0.0841 vs noise floor about 5.7e-4, SNR ~150,
    bit-identical on re-run (fixed seed)
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import power_spectral_density_logic as psdl  # noqa: E402

FS = 1024.0
M = 256
DF = FS / M  # 4.0 Hz per bin
N = 8192


def sine_wave(amp, freq, n, fs):
    """n samples of amp * sin(2 pi freq t) at sample rate fs."""
    return [amp * math.sin(2.0 * math.pi * freq * i / fs) for i in range(n)]


SINE_A1 = sine_wave(1.0, 60.0, N, FS)
SINE_A05 = sine_wave(0.5, 60.0, N, FS)
WIN = psdl.hann_window(M)


def seeded_noisy_tone(seed=21):
    """60 Hz tone amplitude 1 plus seeded Gaussian noise, variance 0.2."""
    rng = random.Random(seed)
    noise = [rng.gauss(0.0, math.sqrt(0.2)) for _ in range(N)]
    return [a + b for a, b in zip(SINE_A1, noise)]


class HannWindowTest(unittest.TestCase):
    def test_window_length_and_symmetry(self):
        w = psdl.hann_window(M)
        self.assertEqual(len(w), M)
        # Periodic Hann symmetry: w[n] == w[M - n] for n = 1..M - 1,
        # with the peak at n = M/2 and near-zero endpoints.
        for n in range(1, M):
            self.assertAlmostEqual(w[n], w[M - n], places=12)
        self.assertAlmostEqual(w[0], 0.0, places=12)
        self.assertAlmostEqual(w[M // 2], 1.0, places=12)

    def test_window_sum_m_over_two(self):
        # Sum about M/2 = 128.0 for M = 256 (even M, cosine terms cancel).
        self.assertAlmostEqual(sum(WIN), 128.0, places=9)

    def test_window_sum_of_squares_3m_over_8(self):
        # Sum of squares about 3M/8 = 96.0 for M = 256.
        self.assertAlmostEqual(sum(v * v for v in WIN), 96.0, places=9)

    def test_window_small_m_anchor(self):
        # w[n] = 0.5 - 0.5 cos(pi n / 2) for m = 4: [0.0, 0.5, 1.0, 0.5].
        w = psdl.hann_window(4)
        for got, want in zip(w, [0.0, 0.5, 1.0, 0.5]):
            self.assertAlmostEqual(got, want, places=12)

    def test_window_rejects_bad_m(self):
        with self.assertRaises(ValueError):
            psdl.hann_window(0)
        with self.assertRaises(ValueError):
            psdl.hann_window(-8)
        with self.assertRaises(TypeError):
            psdl.hann_window(2.5)
        with self.assertRaises(TypeError):
            psdl.hann_window("256")


class EquivalentNoiseBwTest(unittest.TestCase):
    def test_enbw_hann256_is_six_hz(self):
        # ENBW = 1024 * 96 / 128^2 = 6.0 Hz.
        self.assertAlmostEqual(psdl.equivalent_noise_bw(WIN, FS), 6.0, places=9)

    def test_enbw_formula_identity_manual(self):
        s = sum(WIN)
        s2 = sum(v * v for v in WIN)
        self.assertAlmostEqual(
            psdl.equivalent_noise_bw(WIN, FS), FS * s2 / (s * s), places=12
        )

    def test_enbw_rectangular_window(self):
        # Unit rectangular window of length M: ENBW = fs * M / M^2 = fs / M.
        rect = [1.0] * M
        self.assertAlmostEqual(psdl.equivalent_noise_bw(rect, FS), 4.0, places=12)

    def test_enbw_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            psdl.equivalent_noise_bw(WIN, 0.0)
        with self.assertRaises(ValueError):
            psdl.equivalent_noise_bw(WIN, -1.0)
        with self.assertRaises(ValueError):
            psdl.equivalent_noise_bw([0.0, 0.0], FS)  # zero window sum
        with self.assertRaises(ValueError):
            psdl.equivalent_noise_bw([], FS)
        with self.assertRaises(TypeError):
            psdl.equivalent_noise_bw([1.0, "x"], FS)


class FftInternalTest(unittest.TestCase):
    def test_fft_matches_definition(self):
        # Radix-2 internal transform must equal the transform definition.
        seq = [0.5, 1.5, -1.0, 0.25, 2.0, -0.75, 1.0, 0.125]
        got = psdl._fft(seq)
        for k in range(8):
            want = sum(
                seq[n] * complex(
                    math.cos(-2.0 * math.pi * k * n / 8),
                    math.sin(-2.0 * math.pi * k * n / 8),
                )
                for n in range(8)
            )
            self.assertAlmostEqual(got[k].real, want.real, places=12)
            self.assertAlmostEqual(got[k].imag, want.imag, places=12)

    def test_fft_impulse_all_ones(self):
        xf = psdl._fft([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        for z in xf:
            self.assertAlmostEqual(z.real, 1.0, places=12)
            self.assertAlmostEqual(z.imag, 0.0, places=12)

    def test_fft_hermitian_symmetry_real_input(self):
        seq = [0.5, 1.5, -1.0, 0.25, 2.0, -0.75, 1.0, 0.125]
        xf = psdl._fft(seq)
        for k in range(1, 8):
            self.assertAlmostEqual(xf[k].real, xf[8 - k].real, places=12)
            self.assertAlmostEqual(xf[k].imag, -xf[8 - k].imag, places=12)

    def test_fft_rejects_bad_lengths(self):
        for bad in ([1.0, 2.0, 3.0], [1.0] * 6, []):
            with self.assertRaises(ValueError):
                psdl._fft(bad)


class PeriodogramTest(unittest.TestCase):
    def test_one_sided_axis_length_and_frequencies(self):
        freqs, p = psdl.periodogram(sine_wave(1.0, 60.0, M, FS), FS, WIN)
        self.assertEqual(len(freqs), M // 2 + 1)
        self.assertEqual(len(p), M // 2 + 1)
        self.assertAlmostEqual(freqs[0], 0.0, places=12)
        self.assertAlmostEqual(freqs[-1], FS / 2, places=12)
        self.assertAlmostEqual(freqs[15], 60.0, places=12)

    def test_sine_peak_density_anchor(self):
        # A = 1 tone on bin 15: peak density A^2 / (2 ENBW) = 1/12.
        freqs, p = psdl.periodogram(sine_wave(1.0, 60.0, M, FS), FS, WIN)
        self.assertAlmostEqual(p[15], 1.0 / 12.0, places=12)
        self.assertEqual(max(range(len(p)), key=lambda k: p[k]), 15)

    def test_sine_integrated_power_anchor(self):
        _, p = psdl.periodogram(sine_wave(1.0, 60.0, M, FS), FS, WIN)
        self.assertAlmostEqual(sum(p) * DF, 0.5, places=12)  # A^2 / 2

    def test_amplitude_quarter_law(self):
        # A = 0.5 tone: peak is exactly one quarter of the A = 1 peak.
        _, p1 = psdl.periodogram(sine_wave(1.0, 60.0, M, FS), FS, WIN)
        _, ph = psdl.periodogram(sine_wave(0.5, 60.0, M, FS), FS, WIN)
        self.assertAlmostEqual(ph[15], 0.0208333333333, places=12)
        self.assertAlmostEqual(p1[15] / ph[15], 4.0, places=9)

    def test_dc_bin_not_doubled(self):
        # Constant segment: P[0] = c^2 (sum w)^2 / (fs sum w^2), undoubled,
        # and the record integrates to its mean square c^2 = 1.
        _, p = psdl.periodogram([1.0] * M, FS, WIN)
        undoubled = (sum(WIN) ** 2) / (FS * sum(v * v for v in WIN))
        self.assertAlmostEqual(p[0], undoubled, places=12)
        self.assertNotAlmostEqual(p[0], 2.0 * undoubled, places=9)
        self.assertAlmostEqual(sum(p) * DF, 1.0, places=9)

    def test_nyquist_bin_not_doubled(self):
        # (-1)^n segment: the Nyquist bin keeps |X[M/2]|^2 / (fs sum w^2)
        # with no factor 2; total power equals the mean square A^2 = 1.
        nyq = [math.cos(math.pi * n) for n in range(M)]
        _, p = psdl.periodogram(nyq, FS, WIN)
        undoubled = (sum(WIN) ** 2) / (FS * sum(v * v for v in WIN))
        self.assertAlmostEqual(p[M // 2], undoubled, places=12)
        self.assertNotAlmostEqual(p[M // 2], 2.0 * undoubled, places=9)
        self.assertAlmostEqual(sum(p) * DF, 1.0, places=9)

    def test_periodogram_rejects_bad_inputs(self):
        seg = sine_wave(1.0, 60.0, M, FS)
        with self.assertRaises(ValueError):
            psdl.periodogram(seg[:255], FS, WIN)  # not a power of two
        with self.assertRaises(ValueError):
            psdl.periodogram(seg, FS, psdl.hann_window(128))  # window mismatch
        with self.assertRaises(ValueError):
            psdl.periodogram(seg, 0.0, WIN)
        with self.assertRaises(ValueError):
            psdl.periodogram(seg, -5.0, WIN)
        with self.assertRaises(ValueError):
            psdl.periodogram([], FS, WIN)


class WelchPsdTest(unittest.TestCase):
    def test_segment_count_and_mean_of_periodograms(self):
        # (8192 - 256) / 128 + 1 = 63 segments at default 50% overlap.
        freqs, psd = psdl.welch_psd(SINE_A1, FS, M)
        starts = list(range(0, N - M + 1, M // 2))
        self.assertEqual(len(starts), 63)
        manual = [0.0] * (M // 2 + 1)
        for start in starts:
            _, p = psdl.periodogram(SINE_A1[start:start + M], FS, WIN)
            for k, pk in enumerate(p):
                manual[k] += pk
        for k in range(len(manual)):
            self.assertAlmostEqual(psd[k], manual[k] / 63.0, places=10)
        self.assertEqual(len(freqs), M // 2 + 1)

    def test_freqs_axis_spacing(self):
        freqs, _ = psdl.welch_psd(SINE_A1, FS, M)
        self.assertEqual(len(freqs), 129)
        self.assertAlmostEqual(freqs[0], 0.0, places=12)
        self.assertAlmostEqual(freqs[1] - freqs[0], 4.0, places=12)
        self.assertAlmostEqual(freqs[-1], 512.0, places=12)

    def test_sine_peak_and_power_8192(self):
        freqs, psd = psdl.welch_psd(SINE_A1, FS, M)
        peak_idx = max(range(len(psd)), key=lambda k: psd[k])
        self.assertEqual(peak_idx, 15)
        self.assertAlmostEqual(freqs[peak_idx], 60.0, places=12)
        self.assertAlmostEqual(psd[15], 1.0 / 12.0, places=12)  # A^2 / (2 ENBW)
        self.assertAlmostEqual(sum(psd) * DF, 0.5, places=12)  # A^2 / 2

    def test_amplitude_quarter_law(self):
        _, psd1 = psdl.welch_psd(SINE_A1, FS, M)
        _, psdh = psdl.welch_psd(SINE_A05, FS, M)
        self.assertAlmostEqual(max(psdh), 0.0208333333333, places=12)
        self.assertAlmostEqual(max(psd1) / max(psdh), 4.0, places=9)
        self.assertAlmostEqual(sum(psdh) * DF, 0.125, places=12)  # A^2 / 2

    def test_dc_record_mean_square(self):
        _, psd = psdl.welch_psd([1.0] * N, FS, M)
        self.assertAlmostEqual(psd[0], (sum(WIN) ** 2) / (FS * 96.0), places=12)
        self.assertAlmostEqual(sum(psd) * DF, 1.0, places=9)  # mean square

    def test_zero_overlap_ok(self):
        # overlap = 0.0 slides by seg_len: 32 segments, same total power.
        _, psd = psdl.welch_psd(SINE_A1, FS, M, overlap=0.0)
        self.assertEqual(len(psd), 129)
        self.assertAlmostEqual(sum(psd) * DF, 0.5, places=9)

    def test_deterministic_repeat_calls(self):
        _, a = psdl.welch_psd(SINE_A1, FS, M)
        _, b = psdl.welch_psd(SINE_A1, FS, M)
        self.assertEqual(a, b)

    def test_seeded_noise_reproducible(self):
        # A fixed seed must regenerate an identical PSD on a fresh record.
        rec1 = seeded_noisy_tone(seed=21)
        rec2 = seeded_noisy_tone(seed=21)
        _, p1 = psdl.welch_psd(rec1, FS, M)
        _, p2 = psdl.welch_psd(rec2, FS, M)
        self.assertEqual(p1, p2)

    def test_seeded_noise_peak_floor_snr(self):
        # Tone A = 1 plus variance-0.2 noise, seed 21: peak ~0.0841 at
        # 60 Hz, off-peak floor ~5.7e-4, SNR ~150 (spec magnitude bound).
        freqs, psd = psdl.welch_psd(seeded_noisy_tone(seed=21), FS, M)
        peak_idx = max(range(len(psd)), key=lambda k: psd[k])
        peak = psd[peak_idx]
        floor = max(v for k, v in enumerate(psd) if abs(k - peak_idx) > 3)
        self.assertEqual(peak_idx, 15)
        self.assertGreater(peak, 0.0835)     # within a few % of A^2/(2 ENBW)
        self.assertLess(peak, 0.0855)
        self.assertGreater(floor, 4.0e-4)
        self.assertLess(floor, 7.0e-4)       # white level 2 var / fs ~3.9e-4
        self.assertGreater(peak / floor, 120.0)
        self.assertLess(peak / floor, 180.0)
        self.assertAlmostEqual(freqs[peak_idx], 60.0, places=9)

    def test_welch_rejects_bad_seg_len(self):
        for bad in (255, 300, 1, 0, 100):
            with self.assertRaises(ValueError):
                psdl.welch_psd(SINE_A1, FS, bad)

    def test_welch_rejects_bad_fs_overlap_and_short_record(self):
        with self.assertRaises(ValueError):
            psdl.welch_psd(SINE_A1, 0.0, M)
        with self.assertRaises(ValueError):
            psdl.welch_psd(SINE_A1, -1.0, M)
        for bad_overlap in (-0.1, 1.0, 1.5):
            with self.assertRaises(ValueError):
                psdl.welch_psd(SINE_A1, FS, M, overlap=bad_overlap)
        with self.assertRaises(ValueError):
            psdl.welch_psd([0.5] * 100, FS, M)  # shorter than seg_len
        with self.assertRaises(ValueError):
            psdl.welch_psd([], FS, M)


class TotalPowerTest(unittest.TestCase):
    def test_total_power_sum_times_df(self):
        _, p = psdl.periodogram(sine_wave(1.0, 60.0, M, FS), FS, WIN)
        self.assertAlmostEqual(psdl.psd_total_power(p, DF), sum(p) * DF, places=12)

    def test_total_power_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            psdl.psd_total_power([1.0, 2.0], 0.0)
        with self.assertRaises(ValueError):
            psdl.psd_total_power([1.0, 2.0], -1.0)
        with self.assertRaises(ValueError):
            psdl.psd_total_power([], DF)
        with self.assertRaises(TypeError):
            psdl.psd_total_power([1.0, "x"], DF)


class PsdSummaryTest(unittest.TestCase):
    def test_summary_keys_and_values(self):
        s = psdl.psd_summary(SINE_A1, FS, M)
        self.assertEqual(
            set(s.keys()),
            {"freqs", "psd", "enbw_hz", "df_hz", "total_power",
             "peak_density", "peak_freq_hz"},
        )
        _, psd = psdl.welch_psd(SINE_A1, FS, M)
        self.assertEqual(s["psd"], psd)
        self.assertAlmostEqual(s["enbw_hz"], 6.0, places=9)
        self.assertAlmostEqual(s["df_hz"], 4.0, places=12)
        self.assertAlmostEqual(s["total_power"], 0.5, places=12)
        self.assertAlmostEqual(s["peak_density"], 1.0 / 12.0, places=12)
        self.assertAlmostEqual(s["peak_freq_hz"], 60.0, places=9)

    def test_summary_propagates_valueerrors(self):
        with self.assertRaises(ValueError):
            psdl.psd_summary(SINE_A1, FS, 300)       # not a power of two
        with self.assertRaises(ValueError):
            psdl.psd_summary(SINE_A1, 0.0, M)        # fs <= 0
        with self.assertRaises(ValueError):
            psdl.psd_summary(SINE_A1, FS, M, overlap=1.5)
        with self.assertRaises(ValueError):
            psdl.psd_summary([0.5] * 100, FS, M)     # short record


if __name__ == "__main__":
    unittest.main(verbosity=2)

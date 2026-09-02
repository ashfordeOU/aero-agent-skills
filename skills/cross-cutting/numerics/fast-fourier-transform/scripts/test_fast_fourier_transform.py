#!/usr/bin/env python3
"""Gate 3 contract test: fast Fourier transform logic.

Exercises scripts/fast_fourier_transform_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the O(N^2)
discrete Fourier transform by definition, the radix-2 Cooley-Tukey
fast Fourier transform, the inverse FFT, the magnitude, phase, and
power spectra, Parseval energy conservation, and ValueError on empty
input or non-power-of-two radix-2 lengths.

Analytic anchors (exact for small N):
  dft([1, 2, 3, 4]) = [10, -2+2j, -2, -2-2j]
  fft([1, 0, 0, 0]) = [1, 1, 1, 1]        (impulse gives all ones)
  ifft([1, 1, 1, 1]) = [1, 0, 0, 0]
  ifft(fft(x)) == x for any power-of-two length (round trip)
  sin(pi*n/2) with N=8: |X[2]| = |X[6]| = 4 = N/2, phase -pi/2 at
    bin 2 and +pi/2 at bin 6
  parseval_ratio(x) = 1.0 (sum |x|^2 = (1/N) sum |X|^2)
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fast_fourier_transform_logic as fftl  # noqa: E402

SINE8 = [math.sin(math.pi * n / 2) for n in range(8)]
COS8 = [math.cos(math.pi * n / 2) for n in range(8)]
SEQ8 = [0.5, 1.5, -1.0, 0.25, 2.0, -0.75, 1.0, 0.125]


class DftTest(unittest.TestCase):
    def test_impulse_gives_all_ones(self):
        # X[k] = sum_n x[n] exp(-2 pi i k n / 4) with x = [1, 0, 0, 0]
        # leaves only the n = 0 term: every bin equals 1.
        X = fftl.dft([1, 0, 0, 0])
        self.assertEqual(len(X), 4)
        for z in X:
            self.assertAlmostEqual(z.real, 1.0, places=12)
            self.assertAlmostEqual(z.imag, 0.0, places=12)

    def test_ramp4_exact_anchor(self):
        # Hand computed: X = [10, -2+2i, -2, -2-2i].
        X = fftl.dft([1, 2, 3, 4])
        expected = [10 + 0j, -2 + 2j, -2 + 0j, -2 - 2j]
        for got, want in zip(X, expected):
            self.assertAlmostEqual(got.real, want.real, places=12)
            self.assertAlmostEqual(got.imag, want.imag, places=12)

    def test_linearity(self):
        # dft(a + b) = dft(a) + dft(b) entrywise.
        a = SEQ8
        b = list(reversed(SEQ8))
        summed = fftl.dft([x + y for x, y in zip(a, b)])
        direct = [x + y for x, y in zip(fftl.dft(a), fftl.dft(b))]
        for got, want in zip(summed, direct):
            self.assertAlmostEqual(got.real, want.real, places=12)
            self.assertAlmostEqual(got.imag, want.imag, places=12)

    def test_empty_raises_valueerror(self):
        with self.assertRaises(ValueError):
            fftl.dft([])

    def test_non_numeric_raises_typeerror(self):
        with self.assertRaises(TypeError):
            fftl.dft([1, "two", 3])


class FftTest(unittest.TestCase):
    def test_impulse_gives_all_ones(self):
        X = fftl.fft([1, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(len(X), 8)
        for z in X:
            self.assertAlmostEqual(z.real, 1.0, places=12)
            self.assertAlmostEqual(z.imag, 0.0, places=12)

    def test_ramp4_matches_dft_anchor(self):
        X = fftl.fft([1, 2, 3, 4])
        expected = [10 + 0j, -2 + 2j, -2 + 0j, -2 - 2j]
        for got, want in zip(X, expected):
            self.assertAlmostEqual(got.real, want.real, places=12)
            self.assertAlmostEqual(got.imag, want.imag, places=12)

    def test_matches_dft_for_power_of_two(self):
        X_fft = fftl.fft(SEQ8)
        X_dft = fftl.dft(SEQ8)
        for got, want in zip(X_fft, X_dft):
            self.assertAlmostEqual(got.real, want.real, places=12)
            self.assertAlmostEqual(got.imag, want.imag, places=12)

    def test_hermitian_symmetry_for_real_input(self):
        # Real input: X[k] = conj(X[N-k]).
        X = fftl.fft(SEQ8)
        for k in range(1, 8):
            self.assertAlmostEqual(X[k].real, X[8 - k].real, places=12)
            self.assertAlmostEqual(X[k].imag, -X[8 - k].imag, places=12)

    def test_non_power_of_two_raises(self):
        for bad in ([1, 2, 3], [1, 2, 3, 4, 5, 6], []):
            with self.assertRaises(ValueError):
                fftl.fft(bad)


class IfftTest(unittest.TestCase):
    def test_inverse_of_ones_is_impulse(self):
        x = fftl.ifft([1, 1, 1, 1])
        expected = [1, 0, 0, 0]
        for got, want in zip(x, expected):
            self.assertAlmostEqual(got.real, want, places=12)
            self.assertAlmostEqual(got.imag, 0.0, places=12)

    def test_roundtrip_n4(self):
        x = [1, 2, 3, 4]
        back = fftl.ifft(fftl.fft(x))
        for got, want in zip(back, x):
            self.assertAlmostEqual(got.real, want, places=12)
            self.assertAlmostEqual(got.imag, 0.0, places=12)

    def test_roundtrip_n8(self):
        back = fftl.ifft(fftl.fft(SEQ8))
        for got, want in zip(back, SEQ8):
            self.assertAlmostEqual(got.real, want, places=12)
            self.assertAlmostEqual(got.imag, 0.0, places=12)

    def test_inverse_fft_matches_inverse_definition(self):
        # ifft(X)[n] = (1/N) sum_k X[k] exp(+2 pi i k n / N).
        X = fftl.fft(SEQ8)
        n = 8
        for idx in range(n):
            s = 0j
            for k, z in enumerate(X):
                s += z * _twiddle_plus(idx, k, n)
            self.assertAlmostEqual(s.real / n, fftl.ifft(X)[idx].real, places=12)
            self.assertAlmostEqual(s.imag / n, fftl.ifft(X)[idx].imag, places=12)

    def test_non_power_of_two_raises(self):
        with self.assertRaises(ValueError):
            fftl.ifft([1, 2, 3, 4, 5])
        with self.assertRaises(ValueError):
            fftl.ifft([])


def _twiddle_plus(n_idx, k_idx, n):
    """exp(+2 pi i k n_idx / N) via Euler's formula (math only)."""
    theta = 2.0 * math.pi * k_idx * n_idx / n
    return complex(math.cos(theta), math.sin(theta))


class SpectrumTest(unittest.TestCase):
    def test_sine_peaks_at_signal_bins(self):
        # sin(pi n/2) is bin 2 of N=8: |X[2]| = |X[6]| = N/2 = 4.
        mag = fftl.magnitude_spectrum(SINE8)
        self.assertAlmostEqual(mag[2], 4.0, places=12)
        self.assertAlmostEqual(mag[6], 4.0, places=12)
        for k in (0, 1, 3, 4, 5, 7):
            self.assertLess(mag[k], 1e-12)

    def test_sine_phase_at_signal_bins(self):
        phase = fftl.phase_spectrum(SINE8)
        self.assertAlmostEqual(phase[2], -math.pi / 2, places=12)
        self.assertAlmostEqual(phase[6], math.pi / 2, places=12)

    def test_cosine_phase_zero_at_signal_bin(self):
        phase = fftl.phase_spectrum(COS8)
        self.assertAlmostEqual(phase[2], 0.0, places=12)

    def test_magnitude_equals_abs_of_dft(self):
        # The dispatcher must agree with the plain DFT definition.
        mag = fftl.magnitude_spectrum(SEQ8)
        dft_mag = [abs(z) for z in fftl.dft(SEQ8)]
        for got, want in zip(mag, dft_mag):
            self.assertAlmostEqual(got, want, places=12)

    def test_spectrum_works_for_non_power_of_two(self):
        # N=6 has no radix-2 path: the dispatcher falls back to dft.
        x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        mag = fftl.magnitude_spectrum(x)
        self.assertEqual(len(mag), 6)
        for got, want in zip(mag, [abs(z) for z in fftl.dft(x)]):
            self.assertAlmostEqual(got, want, places=12)

    def test_power_spectrum_energy(self):
        # (1/N) sum |X|^2 equals the time-domain energy.
        energy = sum(v * v for v in [1, 2, 3, 4])
        self.assertAlmostEqual(sum(fftl.power_spectrum([1, 2, 3, 4])) / 4, energy, places=12)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            fftl.magnitude_spectrum([])
        with self.assertRaises(ValueError):
            fftl.phase_spectrum([])


class ParsevalTest(unittest.TestCase):
    def test_ratio_one_for_ramp4(self):
        self.assertAlmostEqual(fftl.parseval_ratio([1, 2, 3, 4]), 1.0, places=12)

    def test_ratio_one_for_real_n8(self):
        self.assertAlmostEqual(fftl.parseval_ratio(SEQ8), 1.0, places=12)

    def test_ratio_one_for_complex_input(self):
        z = [1 + 2j, -0.5 + 1j, 0.25 - 0.75j, 2 + 0.5j, -1 + 1.5j, 0.5j, 1 - 1j, -2 - 0.25j]
        self.assertAlmostEqual(fftl.parseval_ratio(z), 1.0, places=12)

    def test_all_zero_signal_ratio_one(self):
        self.assertEqual(fftl.parseval_ratio([0.0, 0.0, 0.0, 0.0]), 1.0)

    def test_energy_check_on_non_power_of_two(self):
        self.assertAlmostEqual(fftl.parseval_ratio([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), 1.0, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Contract test for digital_filter_design_logic (wave-28 leaf).

Deterministic stdlib unittest, offline. Runs with:

    python3 scripts/test_digital_filter_design.py

and must exit 0. Asserts the spec worked-example anchors: prewarp
649.8393 at fs 1000 Hz and fc 100 Hz, order-2 poles -0.7071068 +/-
0.7071068j, -3.0103 dB at the cutoff, near-unity passband gain at 10
Hz, strong attenuation at 400 Hz, DC steady state of a constant
input, highpass passband and attenuation anchors, Schur-Jury
stability verdicts, and ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from digital_filter_design_logic import (  # noqa: E402
    TOL_3DB,
    analog_scale,
    apply_filter,
    bilinear_pole,
    butterworth_poles,
    design_highpass,
    design_lowpass,
    filter_design_checks,
    freq_response_db,
    prewarp,
)

FS = 1000.0
FC = 100.0
CUTOFF_DB = 3.0103


def _magnitude_db_lp_analytic(f, fc, fs, order):
    """Closed-form warped-analog Butterworth magnitude in dB (lowpass)."""
    ratio = math.tan(math.pi * f / fs) / math.tan(math.pi * fc / fs)
    return 10.0 * math.log10(1.0 / (1.0 + ratio ** (2 * order)))


def _magnitude_db_hp_analytic(f, fc, fs, order):
    """Closed-form warped-analog Butterworth magnitude in dB (highpass)."""
    ratio = math.tan(math.pi * fc / fs) / math.tan(math.pi * f / fs)
    return 10.0 * math.log10(1.0 / (1.0 + ratio ** (2 * order)))


class TestPrewarp(unittest.TestCase):
    """Prewarped analog cutoff from the bilinear transform."""

    def test_prewarp_worked_example(self):
        # fs 1000 Hz, fc 100 Hz: 2000*tan(0.1*pi) = 649.8393
        omega_a = prewarp(FC, FS)
        self.assertAlmostEqual(omega_a, 649.8393924658126, places=9)
        self.assertLess(abs(omega_a - 649.8393), 1e-3)
        self.assertAlmostEqual(omega_a, 2000.0 * math.tan(0.1 * math.pi),
                               places=12)

    def test_prewarp_valueerrors(self):
        for fs, fc in ((0.0, 100.0), (-100.0, 50.0), (1000.0, 0.0),
                       (1000.0, -5.0), (1000.0, 500.0), (1000.0, 600.0)):
            with self.assertRaises(ValueError):
                prewarp(fc, fs)


class TestButterworthPoles(unittest.TestCase):
    """Normalized unit-circle LHP pole placement."""

    def test_poles_order1(self):
        poles = butterworth_poles(1)
        self.assertEqual(len(poles), 1)
        self.assertAlmostEqual(poles[0].real, -1.0, places=12)
        self.assertAlmostEqual(poles[0].imag, 0.0, places=12)

    def test_poles_order2_worked_example(self):
        poles = butterworth_poles(2)
        self.assertEqual(len(poles), 2)
        p_plus = poles[0]
        p_minus = poles[1]
        self.assertAlmostEqual(p_plus.real, -0.7071067811865475, places=9)
        self.assertAlmostEqual(p_plus.imag, 0.7071067811865476, places=9)
        self.assertAlmostEqual(p_minus.real, -0.7071067811865475, places=9)
        self.assertAlmostEqual(p_minus.imag, -0.7071067811865476, places=9)
        self.assertAlmostEqual(p_plus.real, -math.sqrt(2.0) / 2.0, places=12)

    def test_poles_order3_symmetry(self):
        poles = butterworth_poles(3)
        self.assertEqual(len(poles), 3)
        for pole in poles:
            self.assertLess(pole.real, 0.0)
            self.assertAlmostEqual(abs(pole), 1.0, places=12)
        reals = sorted(p.real for p in poles)
        self.assertAlmostEqual(reals[0], -1.0, places=12)
        self.assertAlmostEqual(reals[1], -0.5, places=9)
        # conjugate pair present
        pair = sorted(p.imag for p in poles)
        self.assertAlmostEqual(pair[0] + pair[2], 0.0, places=12)

    def test_poles_valueerrors(self):
        for order in (0, -1, 11):
            with self.assertRaises(ValueError):
                butterworth_poles(order)


class TestBilinearMapping(unittest.TestCase):
    """Bilinear pole map and analog scaling."""

    def test_bilinear_pole_stability_radius(self):
        # negative real s maps strictly inside the unit circle
        z = bilinear_pole(-649.8393924658126, 1000.0)
        self.assertLess(abs(z), 1.0)
        self.assertAlmostEqual(z.real, 0.5095254494944288, places=12)
        self.assertAlmostEqual(z.imag, 0.0, places=12)
        # imaginary s (frequency axis) maps onto the unit circle
        z_jw = bilinear_pole(1j * 649.8393924658126, 1000.0)
        self.assertAlmostEqual(abs(z_jw), 1.0, places=12)

    def test_bilinear_pole_valueerror(self):
        with self.assertRaises(ValueError):
            bilinear_pole(-1.0, 0.0)

    def test_analog_scale(self):
        scaled = analog_scale([-0.7071067811865475 + 0.7071067811865476j],
                              100.0)
        self.assertAlmostEqual(abs(scaled[0]), 100.0, places=9)
        with self.assertRaises(ValueError):
            analog_scale([-1.0], 0.0)


class TestLowpassDesign(unittest.TestCase):
    """Butterworth lowpass design and magnitude response anchors."""

    def setUp(self):
        self.b, self.a = design_lowpass(FS, FC, 2)

    def test_coefficient_shapes(self):
        self.assertEqual(len(self.b), 3)
        self.assertEqual(len(self.a), 3)
        self.assertEqual(self.a[0], 1.0)
        b4, a4 = design_lowpass(FS, FC, 4)
        self.assertEqual(len(b4), 5)
        self.assertEqual(len(a4), 5)
        self.assertEqual(a4[0], 1.0)

    def test_cutoff_gain_3db(self):
        gain = freq_response_db(self.b, self.a, FC, FS)
        self.assertAlmostEqual(gain, -3.0102999566398125, places=9)
        self.assertLessEqual(abs(gain + CUTOFF_DB), TOL_3DB)

    def test_passband_gain_10hz(self):
        gain = freq_response_db(self.b, self.a, 10.0, FS)
        self.assertGreater(gain, -0.02)
        self.assertLess(gain, 0.02)
        self.assertAlmostEqual(gain, _magnitude_db_lp_analytic(10.0, FC, FS, 2),
                               places=6)

    def test_attenuation_400hz(self):
        gain = freq_response_db(self.b, self.a, 400.0, FS)
        self.assertAlmostEqual(gain, -39.05845638466505, places=9)
        self.assertLess(gain, -30.0)
        # deterministic on repeat
        self.assertEqual(gain, freq_response_db(self.b, self.a, 400.0, FS))
        self.assertAlmostEqual(gain,
                               _magnitude_db_lp_analytic(400.0, FC, FS, 2),
                               places=6)

    def test_steady_state_dc_gain_unity(self):
        y = apply_filter(self.b, self.a, [5.0] * 400)
        self.assertEqual(len(y), 400)
        for sample in y[-50:]:
            self.assertLessEqual(abs(sample - 5.0), 0.001)

    def test_design_checks_lowpass(self):
        checks = filter_design_checks(self.b, self.a, FS, FC, "lowpass")
        self.assertAlmostEqual(checks["cutoff_gain_db"], -3.0102999566398125,
                               places=9)
        self.assertAlmostEqual(checks["reference_gain_db"], 0.0, places=6)
        self.assertTrue(checks["passband_ok"])
        self.assertTrue(checks["stable"])
        self.assertTrue(checks["verdict"].startswith("PASS"))

    def test_order1_lowpass(self):
        b1, a1 = design_lowpass(FS, FC, 1)
        self.assertEqual(len(b1), 2)
        gain = freq_response_db(b1, a1, FC, FS)
        self.assertAlmostEqual(gain, -3.0102999566398125, places=9)
        y = apply_filter(b1, a1, [7.0] * 300)
        for sample in y[-30:]:
            self.assertLessEqual(abs(sample - 7.0), 0.001)

    def test_order4_design_and_stability(self):
        b4, a4 = design_lowpass(FS, FC, 4)
        gain = freq_response_db(b4, a4, FC, FS)
        self.assertLessEqual(abs(gain + CUTOFF_DB), TOL_3DB)
        checks = filter_design_checks(b4, a4, FS, FC, "lowpass")
        self.assertTrue(checks["stable"])

    def test_lowpass_valueerrors(self):
        for order in (0, 9):
            with self.assertRaises(ValueError):
                design_lowpass(FS, FC, order)
        for fs, fc in ((0.0, 100.0), (1000.0, 500.0)):
            with self.assertRaises(ValueError):
                design_lowpass(fs, fc, 2)


class TestHighpassDesign(unittest.TestCase):
    """Butterworth highpass design and magnitude response anchors."""

    def setUp(self):
        self.b, self.a = design_highpass(FS, FC, 2)

    def test_cutoff_gain_3db(self):
        gain = freq_response_db(self.b, self.a, FC, FS)
        self.assertAlmostEqual(gain, -3.01029995663981, places=9)
        self.assertLessEqual(abs(gain + CUTOFF_DB), TOL_3DB)

    def test_passband_400hz(self):
        gain = freq_response_db(self.b, self.a, 400.0, FS)
        self.assertAlmostEqual(gain, -0.0005394679472332699, places=9)
        self.assertLess(abs(gain), 0.05)
        self.assertEqual(gain, freq_response_db(self.b, self.a, 400.0, FS))

    def test_numerator_alternating_signs(self):
        # b_k = K*C(2,k)*(-1)^k must alternate, positive at k = 0
        self.assertGreater(self.b[0], 0.0)
        self.assertLess(self.b[1], 0.0)
        self.assertGreater(self.b[2], 0.0)

    def test_attenuation_floor(self):
        # An order-2 Butterworth highpass at fc/2 = 50 Hz attenuates only
        # 12.72 dB; the -15 dB floor is genuinely reached at fc/4 = 25 Hz,
        # which is what the contract asserts (documented in the SKILL body).
        gain_50 = freq_response_db(self.b, self.a, 50.0, FS)
        self.assertAlmostEqual(gain_50, -12.721074240850836, places=9)
        self.assertAlmostEqual(gain_50,
                               _magnitude_db_hp_analytic(50.0, FC, FS, 2),
                               places=6)
        gain_25 = freq_response_db(self.b, self.a, 25.0, FS)
        self.assertLess(gain_25, -15.0)
        self.assertAlmostEqual(gain_25, -24.646598985972837, places=9)

    def test_reference_gain_near_nyquist(self):
        checks = filter_design_checks(self.b, self.a, FS, FC, "highpass")
        self.assertAlmostEqual(checks["reference_gain_db"], 0.0, places=6)
        self.assertTrue(checks["passband_ok"])
        self.assertTrue(checks["stable"])
        self.assertTrue(checks["verdict"].startswith("PASS"))
        gain = freq_response_db(self.b, self.a, FS / 2.0 - 1.0, FS)
        self.assertLess(abs(gain), 0.05)

    def test_highpass_2hz_cutoff_50hz_channel(self):
        # corpus-task scenario: 2 Hz cutoff, 50 Hz accelerometer channel
        b2, a2 = design_highpass(50.0, 2.0, 2)
        self.assertEqual(len(b2), 3)
        self.assertEqual(a2[0], 1.0)
        gain_cut = freq_response_db(b2, a2, 2.0, 50.0)
        self.assertLessEqual(abs(gain_cut + CUTOFF_DB), TOL_3DB)
        gain_near_nyquist = freq_response_db(b2, a2, 24.0, 50.0)
        self.assertLess(abs(gain_near_nyquist), 0.05)

    def test_highpass_valueerrors(self):
        for order in (0, 9):
            with self.assertRaises(ValueError):
                design_highpass(FS, FC, order)
        for fs, fc in ((-1.0, 100.0), (1000.0, 500.0)):
            with self.assertRaises(ValueError):
                design_highpass(fs, fc, 2)


class TestApplyFilter(unittest.TestCase):
    """Direct-form difference equation application."""

    def test_identity_roundtrip(self):
        x = [1.0, -2.0, 0.5, 3.25, 0.0, 9.0]
        y = apply_filter([1.0], [1.0], x)
        self.assertEqual(y, x)

    def test_impulse_response_sanity(self):
        b, a = design_lowpass(FS, FC, 2)
        x = [1.0] + [0.0] * 99
        y = apply_filter(b, a, x)
        self.assertEqual(len(y), len(x))
        # first output sample is b[0]*x[0] under zero initial conditions
        self.assertAlmostEqual(y[0], b[0], places=12)
        # impulse response of a stable filter decays
        self.assertLess(abs(y[-1]), 1e-6)

    def test_apply_filter_valueerrors(self):
        b, a = design_lowpass(FS, FC, 2)
        with self.assertRaises(ValueError):
            apply_filter(b, a, [])
        with self.assertRaises(ValueError):
            apply_filter(b, a, [1.0, float("nan")])
        with self.assertRaises(ValueError):
            apply_filter(b, a, [1.0, float("inf")])
        with self.assertRaises(ValueError):
            apply_filter(b, a, "signal")
        with self.assertRaises(ValueError):
            apply_filter(b, a, [1.0, "a"])


class TestChecksAndValueErrors(unittest.TestCase):
    """Design-verification verdicts and input rejection."""

    def test_checks_detect_unstable_denominator(self):
        # z^2 - 2z + 0.99 has a root at z = 1.1, outside the unit circle
        b = [1.0, 0.0, 0.0]
        a = [1.0, -2.0, 0.99]
        checks = filter_design_checks(b, a, FS, FC, "lowpass")
        self.assertIs(checks["stable"], False)
        self.assertTrue(checks["verdict"].startswith("FAIL"))

    def test_checks_stability_not_checked_above_order4(self):
        b6, a6 = design_lowpass(FS, FC, 6)
        checks = filter_design_checks(b6, a6, FS, FC, "lowpass")
        self.assertIsNone(checks["stable"])
        self.assertTrue(checks["passband_ok"])
        self.assertTrue(checks["verdict"].startswith("PASS"))

    def test_checks_valueerrors(self):
        b, a = design_lowpass(FS, FC, 2)
        with self.assertRaises(ValueError):
            filter_design_checks(b, a, FS, FC, "bandpass")
        with self.assertRaises(ValueError):
            filter_design_checks(b, a, 1.5, 0.4, "lowpass")
        with self.assertRaises(ValueError):
            filter_design_checks([1.0, 2.0], [1.0], FS, FC, "lowpass")
        with self.assertRaises(ValueError):
            filter_design_checks(b, a, FS, 500.0, "lowpass")

    def test_freq_response_db_valueerrors(self):
        b, a = design_lowpass(FS, FC, 2)
        for freq in (0.0, -10.0, 500.0, 600.0):
            with self.assertRaises(ValueError):
                freq_response_db(b, a, freq, FS)


if __name__ == "__main__":
    unittest.main()

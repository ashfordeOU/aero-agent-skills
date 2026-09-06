"""Contract test: bandpass and bandstop Butterworth IIR filter design.

Covers the SKILL.md workflow end to end: step 1 fixes the design
inputs (sample rate, band edges, prototype order, prototype cutoff),
step 2 computes the substitution parameters alpha and kappa with the
center frequency, step 3 builds the digital Butterworth lowpass
prototype and checks its -3.0103 dB point, step 4 runs the bandpass or
bandstop design from the digital frequency transformation, step 5
verifies the design with the band-edge gain checks and the stability
evidence from the u-plane pole preimages, step 6 probes the magnitude
response in dB including the exact null floors, and step 7 filters a
deterministic three-tone test signal and checks the structural DC and
Nyquist behavior of the coefficient vectors. All numeric asserts are
tolerance-based; exact equality is used only for literal constants
(lengths, a[0], bitwise determinism within one interpreter).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandpass_bandstop_filter_design as m

FS = 1000.0
LO = 150.0
HI = 300.0
ORD = 2
EDGE_DB = -3.010299956640  # target edge gain, 20*log10(1/sqrt(2))


def _three_tone_signal(n_samples=2000):
    """Unit-amplitude sines at 50, 220 and 470 Hz, phases 0.3, 1.1, 2.2."""
    tones = [(50.0, 0.3), (220.0, 1.1), (470.0, 2.2)]
    return [sum(math.sin(2.0 * math.pi * f * n / 1000.0 + ph)
                for f, ph in tones) for n in range(n_samples)]


def _tail_gain(y, freq_hz, start=1000):
    """Quadrature projection gain over the settled 1 s tail window."""
    c = 0.0
    s = 0.0
    for n in range(start, 2000):
        w = 2.0 * math.pi * freq_hz * n / 1000.0
        c += y[n] * math.cos(w)
        s += y[n] * math.sin(w)
    return 2.0 / 1000.0 * math.sqrt(c * c + s * s)


class TestPrototype(unittest.TestCase):
    """Workflow step 3: the digital Butterworth lowpass prototype."""

    def test_prototype_order2_closed_form(self):
        # Order-2 prototype at 250 Hz on fs = 1000 takes the closed form
        # B = K*(1+u)^2, A = 1 + 0.171572875254*u^2 with a[0] = 1.
        b_p, a_p = m._lowpass_prototype(2, 250.0, 1000.0)
        self.assertEqual(len(b_p), 3)
        self.assertEqual(len(a_p), 3)
        self.assertEqual(a_p[0], 1.0)
        for k, expected in enumerate([0.292893218813, 0.585786437627,
                                      0.292893218813]):
            self.assertAlmostEqual(b_p[k], expected, delta=1e-9)
        self.assertAlmostEqual(a_p[2], 0.171572875254, delta=1e-9)
        self.assertAlmostEqual(a_p[1], 0.0, delta=1e-12)

    def test_prototype_3db_point(self):
        # The prototype's 3 dB point at 250 Hz measures -3.010299957 dB.
        b_p, a_p = m._lowpass_prototype(2, 250.0, 1000.0)
        gain = m.frequency_response_db(b_p, a_p, 250.0, 1000.0)
        self.assertAlmostEqual(gain, -3.010299957, delta=1e-6)
        self.assertAlmostEqual(gain, EDGE_DB, delta=1e-6)

    def test_prototype_magnitude_identity(self):
        # The closed-form identity |H|^2 = 1/(1 + tan^4(pi/4)) = 1/2
        # holds at the 250 Hz prototype cutoff.
        b_p, a_p = m._lowpass_prototype(2, 250.0, 1000.0)
        mag = m._response_mag(b_p, a_p, -2.0 * math.pi * 250.0 / 1000.0)
        self.assertAlmostEqual(mag * mag, 0.5, delta=1e-12)
        self.assertAlmostEqual(mag, 1.0 / math.sqrt(2.0), delta=1e-9)

    def test_prototype_unity_dc(self):
        # Unity DC gain: the 1 Hz probe reads 0.000000000 dB.
        b_p, a_p = m._lowpass_prototype(2, 250.0, 1000.0)
        self.assertAlmostEqual(m.frequency_response_db(b_p, a_p, 1.0,
                                                       1000.0), 0.0,
                               delta=1e-6)

    def test_prototype_valueerrors(self):
        # Non-physical prototype orders and cutoffs raise ValueError.
        for order in (0, 9, 2.5):
            with self.assertRaises(ValueError):
                m._lowpass_prototype(order, 250.0, 1000.0)
        for pc in (-5.0, 0.0, 600.0):
            with self.assertRaises(ValueError):
                m._lowpass_prototype(2, pc, 1000.0)


class TestSubstitutionParameters(unittest.TestCase):
    """Workflow step 2: the closed-form transformation parameters."""

    def test_parameters_anchor(self):
        alpha, kappa_bp, kappa_bs = m.band_transform_parameters(
            150.0, 300.0, 250.0, 1000.0)
        self.assertAlmostEqual(alpha, 0.175570504585, delta=1e-9)
        self.assertAlmostEqual(kappa_bp, 1.962610505505, delta=1e-9)
        self.assertAlmostEqual(kappa_bs, 0.509525449494, delta=1e-9)

    def test_kappa_reciprocal_at_canonical_prototype(self):
        # At the fs/4 prototype tan(wc/2) = 1, so kappa_bp * kappa_bs = 1.
        _, kappa_bp, kappa_bs = m.band_transform_parameters(
            150.0, 300.0, 250.0, 1000.0)
        self.assertAlmostEqual(kappa_bp * kappa_bs, 1.0, delta=1e-9)

    def test_substitutions_coincide_at_canonical_prototype(self):
        # The bandpass and bandstop c1, c2 agree within 1e-12 at the
        # canonical prototype (the real structural anchor of the shared
        # denominator).
        alpha, kappa_bp, _ = m.band_transform_parameters(
            150.0, 300.0, 250.0, 1000.0)
        c1_bp = 2.0 * alpha * kappa_bp / (kappa_bp + 1.0)
        c2_bp = (kappa_bp - 1.0) / (kappa_bp + 1.0)
        _, _, kappa_bs = m.band_transform_parameters(
            150.0, 300.0, 250.0, 1000.0)
        c1_bs = 2.0 * alpha / (kappa_bs + 1.0)
        c2_bs = (1.0 - kappa_bs) / (1.0 + kappa_bs)
        self.assertAlmostEqual(c1_bp, c1_bs, delta=1e-12)
        self.assertAlmostEqual(c2_bp, c2_bs, delta=1e-12)
        self.assertAlmostEqual(c1_bp, 0.232616819602, delta=1e-9)
        self.assertAlmostEqual(c2_bp, 0.324919696233, delta=1e-9)

    def test_center_frequency_anchor(self):
        # Center 221.911501 Hz equals fs*arccos(alpha)/(2*pi) and lies
        # inside the band; the alpha factor depends only on the two band
        # edges.
        center = m.center_frequency_hz(150.0, 300.0, 1000.0)
        self.assertAlmostEqual(center, 221.911501, delta=1e-6)
        alpha = m.band_transform_parameters(150.0, 300.0, 250.0,
                                            1000.0)[0]
        self.assertAlmostEqual(center, 1000.0 * math.acos(alpha) /
                               (2.0 * math.pi), delta=1e-6)
        self.assertGreater(center, 150.0)
        self.assertLess(center, 300.0)

    def test_parameters_valueerrors(self):
        # Non-physical band edges and prototype cutoffs raise ValueError
        # from band_transform_parameters, and non-physical bands raise
        # from center_frequency_hz (which has no prototype-cutoff
        # argument).
        band_cases = [(-1000.0, 150.0, 300.0, 250.0, 1000.0),
                      (1000.0, 0.0, 300.0, 250.0, 1000.0),
                      (1000.0, 300.0, 300.0, 250.0, 1000.0),
                      (1000.0, 150.0, 500.0, 250.0, 1000.0),
                      (1000.0, 150.0, 300.0, -5.0, 1000.0),
                      (1000.0, 150.0, 300.0, 600.0, 1000.0)]
        for fs, low, high, pc, _ in band_cases:
            with self.assertRaises(ValueError):
                m.band_transform_parameters(low, high, pc, fs)
        for fs, low, high, _, _ in band_cases[:4]:
            with self.assertRaises(ValueError):
                m.center_frequency_hz(low, high, fs)


class TestBandDesign(unittest.TestCase):
    """Workflow steps 4 and 5: coefficient vectors and their checks."""

    def setUp(self):
        self.b_bp, self.a_bp = m.bandpass_design(FS, LO, HI, ORD)
        self.b_bs, self.a_bs = m.bandstop_design(FS, LO, HI, ORD)

    def test_bandpass_coefficients_anchor(self):
        # Order-2 prototype gives len-5 vectors; b matches the exact-null
        # pattern [s, 0, -2s, 0, s] with interior coefficients below 1e-12
        # and a[0] == 1.
        self.assertEqual(len(self.b_bp), 5)
        self.assertEqual(len(self.a_bp), 5)
        self.assertEqual(self.a_bp[0], 1.0)
        for k, expected in enumerate([0.131106439917, 0.0, -0.262212879833,
                                      0.0, 0.131106439917]):
            self.assertAlmostEqual(self.b_bp[k], expected, delta=1e-9)
        self.assertLess(abs(self.b_bp[1]), 1e-12)
        self.assertLess(abs(self.b_bp[3]), 1e-12)
        for k, expected in enumerate([1.0, -0.482430732520, 0.810055809342,
                                      -0.226875551364, 0.272214937925]):
            self.assertAlmostEqual(self.a_bp[k], expected, delta=1e-9)

    def test_bandstop_coefficients_anchor(self):
        # The bandstop numerator is symmetric with zeros on the unit
        # circle at the notch center, and at the canonical prototype the
        # bandstop shares the bandpass denominator to 1e-12 (even
        # prototype order, zero linear coefficient).
        for k, expected in enumerate([0.505001029046, -0.354653141942,
                                      1.072268689175, -0.354653141942,
                                      0.505001029046]):
            self.assertAlmostEqual(self.b_bs[k], expected, delta=1e-9)
        self.assertAlmostEqual(self.b_bs[0], self.b_bs[4], delta=1e-15)
        self.assertAlmostEqual(self.b_bs[1], self.b_bs[3], delta=1e-15)
        for k in range(5):
            self.assertAlmostEqual(self.a_bs[k], self.a_bp[k], delta=1e-12)

    def test_band_edge_gains(self):
        # Both band edges sit at -3.0103 dB for the bandpass AND the
        # bandstop, within 1e-6 dB of 20*log10(1/sqrt(2)).
        for bb, aa in ((self.b_bp, self.a_bp), (self.b_bs, self.a_bs)):
            low_gain = m.frequency_response_db(bb, aa, LO, FS)
            high_gain = m.frequency_response_db(bb, aa, HI, FS)
            self.assertAlmostEqual(low_gain, EDGE_DB, delta=1e-6)
            self.assertAlmostEqual(high_gain, EDGE_DB, delta=1e-6)
            self.assertAlmostEqual(low_gain, -3.010299957, delta=1e-6)
            self.assertAlmostEqual(high_gain, -3.010299957, delta=1e-6)

    def test_bandpass_center_peak(self):
        # The bandpass peaks with unity gain at the center frequency
        # 221.911501 Hz.
        center = m.center_frequency_hz(LO, HI, FS)
        self.assertAlmostEqual(center, 221.911501, delta=1e-6)
        self.assertAlmostEqual(m.frequency_response_db(self.b_bp,
                                                       self.a_bp, center,
                                                       FS), 0.0, delta=1e-6)

    def test_band_edge_checks_pass(self):
        # The band-edge gain checks verdict PASS for both types, with the
        # bandpass extra holding the center gain and the bandstop extra
        # holding the near-DC / near-Nyquist pair.
        chk = m.band_edge_checks(self.b_bp, self.a_bp, FS, LO, HI,
                                 "bandpass")
        self.assertEqual(chk["verdict"], "PASS")
        self.assertTrue(chk["low_edge_ok"] and chk["high_edge_ok"])
        self.assertTrue(chk["passband_ok"])
        self.assertAlmostEqual(chk["target_db"], -3.010299956639812,
                               delta=1e-12)
        self.assertLess(abs(chk["low_edge_db"] - EDGE_DB), 1e-6)
        self.assertLess(abs(chk["high_edge_db"] - EDGE_DB), 1e-6)
        self.assertAlmostEqual(chk["extra"], 0.0, delta=1e-9)
        chk_bs = m.band_edge_checks(self.b_bs, self.a_bs, FS, LO, HI,
                                    "bandstop")
        self.assertEqual(chk_bs["verdict"], "PASS")
        self.assertAlmostEqual(chk_bs["extra"][0], 0.0, delta=1e-9)
        self.assertAlmostEqual(chk_bs["extra"][1], 0.0, delta=1e-9)

    def test_bandstop_unity_reference_gains(self):
        # The bandstop passes DC and Nyquist with gain 1: probes at
        # 1e-9 Hz and fs/2 - 1e-9 Hz stay within 0.001 dB of 0.
        self.assertAlmostEqual(m.frequency_response_db(self.b_bs,
                                                       self.a_bs, 1e-9,
                                                       FS), 0.0, delta=0.001)
        self.assertAlmostEqual(m.frequency_response_db(self.b_bs,
                                                       self.a_bs,
                                                       FS / 2.0 - 1e-9,
                                                       FS), 0.0, delta=0.001)

    def test_bandstop_notch_null(self):
        # The notch center null measures below -200 dB (float floor of
        # the exact on-circle zero pair, anchor -317.064274 dB).
        center = m.center_frequency_hz(LO, HI, FS)
        notch = m.frequency_response_db(self.b_bs, self.a_bs, center, FS)
        self.assertLess(notch, -200.0)

    def test_bandpass_stopband_null_floors(self):
        # The 1 Hz out-of-band probe reads about -96.4 dB and the exact
        # Nyquist null at fs/2 reads below -200 dB (float floor, anchor
        # -665.052919 dB; the exact unit-circle point is a valid probe).
        self.assertLess(m.frequency_response_db(self.b_bp, self.a_bp, 1.0,
                                                FS), -60.0)
        nyquist = m.frequency_response_db(self.b_bp, self.a_bp, FS / 2.0,
                                          FS)
        self.assertLess(nyquist, -200.0)
        self.assertAlmostEqual(m.frequency_response_db(self.b_bp,
                                                       self.a_bp, 1.0,
                                                       FS),
                               -96.432009245, delta=1e-4)

    def test_uplane_poles_stability(self):
        # All four u-plane poles lie outside the unit circle (magnitudes
        # 1.354030645 and 1.415518434, pairs each), identical for the
        # bandpass and the bandstop; equivalently the z-plane poles
        # z = 1/u (0.706454947 and 0.738535722, pairs) lie strictly
        # inside the unit circle.
        for ftype in ("bandpass", "bandstop"):
            mags = m._uplane_poles(FS, LO, HI, ORD, ftype)
            self.assertEqual(len(mags), 4)
            for mag in mags:
                self.assertGreater(mag, 1.0 + 1e-9)
                self.assertLess(1.0 / mag, 1.0 - 1e-9)
            self.assertAlmostEqual(mags[0], 1.354030645, delta=1e-6)
            self.assertAlmostEqual(mags[1], 1.354030645, delta=1e-6)
            self.assertAlmostEqual(mags[2], 1.415518434, delta=1e-6)
            self.assertAlmostEqual(mags[3], 1.415518434, delta=1e-6)
        z_sorted = sorted(1.0 / mag for mag in mags)
        self.assertAlmostEqual(z_sorted[0], 0.706454947, delta=1e-6)
        self.assertAlmostEqual(z_sorted[2], 0.738535722, delta=1e-6)

    def test_reciprocal_convention_rejected(self):
        # The reciprocal-convention filter (N and D lists swapped, which
        # keeps the identical |H(e^jw)| on the unit circle) mirrors the
        # poles outside the unit circle and must be rejected: its
        # constant-input recursion diverges instead of settling.
        b_swapped = list(reversed(self.b_bp))
        a_swapped = list(reversed(self.a_bp))
        same = m.frequency_response_db(b_swapped, a_swapped, 200.0, FS)
        proper = m.frequency_response_db(self.b_bp, self.a_bp, 200.0, FS)
        self.assertAlmostEqual(same, proper, delta=1e-9)
        y = m.apply_filter(b_swapped, a_swapped, [1.0] * 1200)
        tail_max = max(abs(v) for v in y[1000:])
        self.assertGreater(tail_max, 1e6)

    def test_prototype_cutoff_invariance(self):
        # With the edges fixed at 150/300 Hz, prototype cutoffs of 200 Hz
        # and 125 Hz keep both band-edge gains at -3.0103 dB for the
        # bandpass and the bandstop while the coefficient vectors differ
        # from the canonical fs/4 design.
        for pc in (200.0, 125.0):
            b_alt, a_alt = m.bandpass_design(FS, LO, HI, ORD, pc)
            self.assertNotEqual(b_alt, self.b_bp)
            self.assertAlmostEqual(m.frequency_response_db(b_alt, a_alt,
                                                           LO, FS),
                                   -3.010299957, delta=1e-6)
            self.assertAlmostEqual(m.frequency_response_db(b_alt, a_alt,
                                                           HI, FS),
                                   -3.010299957, delta=1e-6)
            c_alt, d_alt = m.bandstop_design(FS, LO, HI, ORD, pc)
            self.assertNotEqual(c_alt, self.b_bs)
            self.assertAlmostEqual(m.frequency_response_db(c_alt, d_alt,
                                                           LO, FS),
                                   -3.010299957, delta=1e-6)
            self.assertAlmostEqual(m.frequency_response_db(c_alt, d_alt,
                                                           HI, FS),
                                   -3.010299957, delta=1e-6)

    def test_order1_bandpass(self):
        # An order-1 prototype (2 poles, len-3 vectors) also lands both
        # edges at -3.010299957 dB.
        b1, a1 = m.bandpass_design(FS, LO, HI, 1)
        self.assertEqual(len(b1), 3)
        self.assertEqual(len(a1), 3)
        self.assertEqual(a1[0], 1.0)
        self.assertAlmostEqual(m.frequency_response_db(b1, a1, LO, FS),
                               -3.010299957, delta=1e-6)
        self.assertAlmostEqual(m.frequency_response_db(b1, a1, HI, FS),
                               -3.010299957, delta=1e-6)

    def test_default_prototype_cutoff(self):
        # The default prototype cutoff is fs/4, the canonical bilinear
        # image of the unit-cutoff analog prototype.
        b_def, a_def = m.bandpass_design(FS, LO, HI, ORD)
        b_ex, a_ex = m.bandpass_design(FS, LO, HI, ORD, FS / 4.0)
        self.assertEqual(b_def, b_ex)
        self.assertEqual(a_def, a_ex)

    def test_determinism_bitwise(self):
        # Two identical design calls are bitwise identical, and the
        # module imports only math and cmath (no RNG, no external
        # libraries).
        b1, a1 = m.bandpass_design(FS, LO, HI, ORD)
        b2, a2 = m.bandpass_design(FS, LO, HI, ORD)
        self.assertEqual(b1, b2)
        self.assertEqual(a1, a2)
        with open(os.path.abspath(m.__file__)) as src:
            source = src.read()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                self.assertIn(stripped.split()[1], ("math", "cmath"))

    def test_design_valueerrors(self):
        # The full ValueError set of the design entry points: fs <= 0,
        # low <= 0, low >= high, high at fs/2, order outside 1..8 and
        # prototype_cutoff_hz outside (0, fs/2).
        bad_cases = [
            (-1000.0, 150.0, 300.0, ORD, None),
            (FS, 0.0, 300.0, ORD, None),
            (FS, 300.0, 300.0, ORD, None),
            (FS, 150.0, 500.0, ORD, None),
            (FS, 150.0, 300.0, 0, None),
            (FS, 150.0, 300.0, 9, None),
            (FS, 150.0, 300.0, ORD, -5.0),
            (FS, 150.0, 300.0, ORD, 600.0),
        ]
        for fs, low, high, order, pc in bad_cases:
            with self.assertRaises(ValueError):
                m.bandpass_design(fs, low, high, order, pc)
            with self.assertRaises(ValueError):
                m.bandstop_design(fs, low, high, order, pc)


class TestSignalWorkflow(unittest.TestCase):
    """Workflow steps 6 and 7: magnitude probes and the filtered signal."""

    def setUp(self):
        self.b_bp, self.a_bp = m.bandpass_design(FS, LO, HI, ORD)
        self.b_bs, self.a_bs = m.bandstop_design(FS, LO, HI, ORD)
        self.x = _three_tone_signal()

    def test_bandpass_signal_tone_gains(self):
        # The measured per-tone gains of the filtered three-tone record
        # reproduce the designed |H| at each tone within 1e-9 relative:
        # the 220 Hz tone passes above -1 dB and the 50 Hz and 470 Hz
        # tones sit below -15 dB.
        y = m.apply_filter(self.b_bp, self.a_bp, self.x)
        for freq_hz, expected_db in ((50.0, -27.704403), (220.0, -0.000001),
                                     (470.0, -43.350723)):
            measured = _tail_gain(y, freq_hz)
            mag = m._response_mag(self.b_bp, self.a_bp,
                                  -2.0 * math.pi * freq_hz / 1000.0)
            self.assertAlmostEqual(measured / mag, 1.0, delta=1e-9)
            self.assertAlmostEqual(20.0 * math.log10(measured),
                                   expected_db, delta=0.001)
        g220 = 20.0 * math.log10(_tail_gain(y, 220.0))
        g50 = 20.0 * math.log10(_tail_gain(y, 50.0))
        g470 = 20.0 * math.log10(_tail_gain(y, 470.0))
        self.assertGreater(g220, -1.0)
        self.assertLess(g50, -15.0)
        self.assertLess(g470, -15.0)

    def test_bandstop_signal_tone_gains(self):
        # The bandstop passes the 50 Hz and 470 Hz tones above -0.1 dB
        # and rejects the in-notch 220 Hz tone below -40 dB, with the
        # measured gains reproducing |H| to 1e-9 relative.
        y = m.apply_filter(self.b_bs, self.a_bs, self.x)
        for freq_hz, expected_db in ((50.0, -0.007374), (220.0, -65.084990),
                                     (470.0, -0.000201)):
            measured = _tail_gain(y, freq_hz)
            mag = m._response_mag(self.b_bs, self.a_bs,
                                  -2.0 * math.pi * freq_hz / 1000.0)
            self.assertAlmostEqual(measured / mag, 1.0, delta=1e-9)
            self.assertAlmostEqual(20.0 * math.log10(measured),
                                   expected_db, delta=0.001)
        g220 = 20.0 * math.log10(_tail_gain(y, 220.0))
        self.assertLess(g220, -40.0)
        self.assertGreater(20.0 * math.log10(_tail_gain(y, 50.0)), -0.1)
        self.assertGreater(20.0 * math.log10(_tail_gain(y, 470.0)), -0.1)

    def test_bandpass_structural_nulls(self):
        # A constant input through the bandpass settles to a tail RMS
        # below 1e-9 (exact DC null) and an alternating (+1/-1) input to
        # a tail RMS below 1e-9 (exact Nyquist null).
        y = m.apply_filter(self.b_bp, self.a_bp, [1.0] * 2000)
        tail = y[1000:2000]
        self.assertLess(math.sqrt(sum(v * v for v in tail) / 1000.0), 1e-9)
        alt = [1.0 if n % 2 == 0 else -1.0 for n in range(2000)]
        y2 = m.apply_filter(self.b_bp, self.a_bp, alt)
        tail2 = y2[1000:2000]
        self.assertLess(math.sqrt(sum(v * v for v in tail2) / 1000.0), 1e-9)

    def test_bandstop_structural_unity(self):
        # A constant input through the bandstop settles to tail mean and
        # RMS equal to 1.0 within 1e-9 (unity DC gain) and an
        # alternating input to a tail RMS equal to 1.0 within 1e-9
        # (unity Nyquist gain).
        y = m.apply_filter(self.b_bs, self.a_bs, [1.0] * 2000)
        tail = y[1000:2000]
        self.assertAlmostEqual(sum(tail) / 1000.0, 1.0, delta=1e-9)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in tail) / 1000.0),
                               1.0, delta=1e-9)
        alt = [1.0 if n % 2 == 0 else -1.0 for n in range(2000)]
        y2 = m.apply_filter(self.b_bs, self.a_bs, alt)
        tail2 = y2[1000:2000]
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in tail2) / 1000.0),
                               1.0, delta=1e-9)


class TestValidation(unittest.TestCase):
    """Workflow steps 1 and 6: input validation of the public API."""

    def test_frequency_response_probe_valueerrors(self):
        # Probes outside (0, fs/2] and non-positive fs raise ValueError.
        b, a = m.bandpass_design(FS, LO, HI, ORD)
        for probe in (0.0, 600.0, -10.0):
            with self.assertRaises(ValueError):
                m.frequency_response_db(b, a, probe, FS)
        with self.assertRaises(ValueError):
            m.frequency_response_db(b, a, 200.0, 0.0)

    def test_band_edge_checks_ftype_valueerror(self):
        # Unknown filter types such as 'notch' raise ValueError.
        b, a = m.bandpass_design(FS, LO, HI, ORD)
        with self.assertRaises(ValueError):
            m.band_edge_checks(b, a, FS, LO, HI, "notch")

    def test_apply_filter_valueerrors(self):
        # Empty sample lists, non-finite samples and mismatched or empty
        # coefficient vectors raise ValueError.
        b, a = m.bandpass_design(FS, LO, HI, ORD)
        with self.assertRaises(ValueError):
            m.apply_filter(b, a, [])
        with self.assertRaises(ValueError):
            m.apply_filter(b, a, [1.0, float("nan")])
        with self.assertRaises(ValueError):
            m.apply_filter(b, a, [1.0, float("inf")])
        with self.assertRaises(ValueError):
            m.apply_filter([], a, [1.0, 2.0])
        with self.assertRaises(ValueError):
            m.apply_filter(b, [1.0, 2.0], [1.0, 2.0])

    def test_filter_roundtrip_length_and_finite(self):
        # apply_filter preserves the input length and returns finite
        # samples for a bounded input.
        y = m.apply_filter(*m.bandpass_design(FS, LO, HI, ORD),
                           samples=_three_tone_signal(500))
        self.assertEqual(len(y), 500)
        for v in y:
            self.assertTrue(math.isfinite(v))


if __name__ == "__main__":
    unittest.main()

"""Contract test for the fir-bandpass-bandstop-filter-design leaf
(cross-cutting/numerics): linear-phase FIR highpass, bandpass and
bandstop tap sets by the windowed-sinc method with spectral inversion
and cosine frequency translation of the windowed-sinc lowpass prototype.

Every method names the SKILL.md workflow step it exercises: step 1 the
design-input fixing, step 2 the windowed prototype build, step 3 the
raw-construction translate-invert step, step 4 the unity passband gain
normalization, step 5 the band-edge verification against the
-6.020599913279624 dB midpoint target, and step 6 the probe, group delay
and direct-form filter step. Worked anchors are real module outputs at
the spec geometries: design_highpass(100, 1000, 101, "hamming"),
design_bandpass(200, 800, 4000, 101, "hamming") and
design_bandstop(200, 800, 4000, 101, "hamming"). All numeric asserts are
tolerance-based (assertAlmostEqual delta or abs bounds); no exact float
equality on computed sums, so the suite passes identically under
/usr/bin/python3 (3.9.6) and the pyenv 3.13.12 hook interpreter.
"""

import ast
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fir_bandpass_bandstop_filter_design_logic as fmod

TARGET_DB = -6.020599913279624  # 20*log10(0.5), the FIR midpoint target
LEVEL_3DB = -3.010299956639813  # 20*log10(1/sqrt(2)), IIR-sibling level


def db(coeff, freq_hz, sample_rate_hz):
    """Shortcut to the magnitude response in dB (workflow step 5/6)."""
    return fmod.magnitude_response_db(coeff, freq_hz, sample_rate_hz)


def crossing_hz(coeff, sample_rate_hz, lo, hi, level=LEVEL_3DB):
    """Locate the frequency where the magnitude response crosses level dB
    inside [lo, hi] by sign bisection (the response is monotone across
    the worked transition bands). Returns the crossing frequency."""
    fa = db(coeff, lo, sample_rate_hz) - level
    fb = db(coeff, hi, sample_rate_hz) - level
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        fm = db(coeff, mid, sample_rate_hz) - level
        if (fm > 0.0) == (fa > 0.0):
            lo, fa = mid, fm
        else:
            hi, fb = mid, fm
    return 0.5 * (lo + hi)


def tone_gain(coeff, sample_rate_hz, freq_hz, tail_start, tail_end,
              phase=1.1):
    """Amplitude of the freq_hz component in the filtered single-tone
    record by quadrature projection over the settled integer-cycle tail
    (workflow step 6, the direct-form filter identity)."""
    x = [math.sin(2.0 * math.pi * freq_hz * n / sample_rate_hz + phase)
         for n in range(tail_end)]
    y = fmod.filter_signal(coeff, x)
    count = tail_end - tail_start
    s = 0.0
    c = 0.0
    for n in range(tail_start, tail_end):
        s += y[n] * math.sin(2.0 * math.pi * freq_hz * n / sample_rate_hz)
        c += y[n] * math.cos(2.0 * math.pi * freq_hz * n / sample_rate_hz)
    return math.sqrt((2.0 * s / count) ** 2 + (2.0 * c / count) ** 2)


class FirBandDesignTest(unittest.TestCase):
    """Worked-geometry anchors of the three design functions."""

    def setUp(self):
        self.hp = fmod.design_highpass(100, 1000, 101, "hamming")
        self.bp = fmod.design_bandpass(200, 800, 4000, 101, "hamming")
        self.bs = fmod.design_bandstop(200, 800, 4000, 101, "hamming")
        self.hp_c = self.hp["coefficients"]
        self.bp_c = self.bp["coefficients"]
        self.bs_c = self.bs["coefficients"]

    def test_highpass_dict_shape_and_anchor_taps(self):
        """Workflow step 1 (design-input fixing) and step 4 (unity
        passband gain normalization): the highpass spectral-inversion
        design returns exactly the seven documented keys and the worked
        Hamming tap anchors at the 100 Hz, 1000 Hz, 101-tap geometry."""
        self.assertEqual(
            set(self.hp.keys()),
            {"coefficients", "num_taps", "cutoff_hz", "sample_rate_hz",
             "window", "group_delay_samples", "nyquist_gain"})
        c = self.hp_c
        self.assertEqual(len(c), 101)
        self.assertAlmostEqual(c[50], 0.800131546113, delta=1e-9)
        self.assertAlmostEqual(c[49], -0.186958764181, delta=1e-9)
        self.assertAlmostEqual(c[51], -0.186958764181, delta=1e-9)
        self.assertAlmostEqual(c[48], -0.150841106810, delta=1e-9)
        self.assertAlmostEqual(c[1], 0.000308982598, delta=1e-9)
        self.assertAlmostEqual(c[2], 0.000527514464, delta=1e-9)
        self.assertAlmostEqual(c[0], 0.0, delta=1e-9)

    def test_highpass_unity_nyquist_gain_and_group_delay(self):
        """Workflow step 4 (unity passband gain normalization) and the
        group delay identity: the highpass Nyquist reference gain is
        1.0 within 1e-12 (anchor 1.000000000000000) and the constant
        group delay is (101 - 1)/2 = 50.0 samples from the symmetric tap
        set (workflow step 6)."""
        self.assertAlmostEqual(self.hp["nyquist_gain"], 1.0, delta=1e-12)
        self.assertEqual(self.hp["group_delay_samples"], 50.0)
        self.assertAlmostEqual(
            fmod.gain_at(self.hp_c, 500.0, 1000.0), 1.0, delta=1e-12)

    def test_highpass_edge_midpoint_null_and_passband_probes(self):
        """Workflow step 5 (band-edge verification) at the FIR midpoint
        target: the measured 100 Hz edge gain is -6.013188638 dB within
        1e-6 dB and within 0.1 dB of the -6.020599913279624 dB target;
        the spectral-inversion DC null floor reads -56.644897249 dB
        below -40 dB; the 50 Hz probe -55.337139253 dB; the passband
        probes read +0.009876223 dB at 150 Hz, -0.000850773 dB at 300 Hz
        and -0.000006122 dB at 480 Hz."""
        edge = db(self.hp_c, 100, 1000)
        self.assertAlmostEqual(edge, -6.013188638, delta=1e-6)
        self.assertLess(abs(edge - TARGET_DB), 0.1)
        dc = db(self.hp_c, 0, 1000)
        self.assertAlmostEqual(dc, -56.644897249, delta=1e-3)
        self.assertLess(dc, -40.0)
        self.assertAlmostEqual(db(self.hp_c, 50, 1000),
                               -55.337139253, delta=1e-3)
        self.assertAlmostEqual(db(self.hp_c, 150, 1000),
                               0.009876223, delta=1e-3)
        self.assertAlmostEqual(db(self.hp_c, 300, 1000),
                               -0.000850773, delta=1e-3)
        self.assertAlmostEqual(db(self.hp_c, 480, 1000),
                               -0.000006122, delta=1e-3)

    def test_highpass_three_db_crossing_above_cutoff(self):
        """Where the Butterworth -3.010299956640 dB level genuinely
        sits: for the highpass it is crossed at 103.994 Hz, strictly
        above the requested 100 Hz cutoff, and the requested edge gain
        differs from -3.010299956640 dB by more than 1 dB (the edge is
        on the -6.020599913 dB midpoint, workflow step 5)."""
        x = crossing_hz(self.hp_c, 1000, 100, 150)
        self.assertAlmostEqual(x, 103.994, delta=0.05)
        self.assertGreater(x, 100.0)
        self.assertGreater(abs(db(self.hp_c, 100, 1000) - LEVEL_3DB), 1.0)

    def test_bandpass_dict_shape_center_and_anchor_taps(self):
        """Workflow step 3 (raw-construction translate-invert) and step 4
        (unity passband gain normalization): the bandpass cosine
        frequency translation returns exactly the nine documented keys
        with center_frequency_hz = 500.0 = (200 + 800)/2 and the worked
        Hamming tap anchors at the 200 to 800 Hz, 4000 Hz, 101-tap
        geometry, including the w0*M = 12.5*pi structural zeros at
        offsets +-2 and the outer taps."""
        self.assertEqual(
            set(self.bp.keys()),
            {"coefficients", "num_taps", "low_cutoff_hz",
             "high_cutoff_hz", "center_frequency_hz", "sample_rate_hz",
             "window", "group_delay_samples", "center_gain"})
        self.assertAlmostEqual(self.bp["center_frequency_hz"], 500.0,
                               delta=1e-9)
        c = self.bp_c
        self.assertAlmostEqual(c[50], 0.299984336175, delta=1e-9)
        self.assertAlmostEqual(c[49], 0.204171360832, delta=1e-9)
        self.assertAlmostEqual(c[51], 0.204171360832, delta=1e-9)
        self.assertAlmostEqual(c[48], 0.0, delta=1e-9)
        self.assertAlmostEqual(c[52], 0.0, delta=1e-9)
        self.assertAlmostEqual(c[1], -0.000662242631, delta=1e-9)
        self.assertAlmostEqual(c[2], -0.000651902497, delta=1e-9)
        self.assertAlmostEqual(c[3], -0.000132065332, delta=1e-9)
        self.assertAlmostEqual(c[0], 0.0, delta=1e-9)

    def test_bandpass_center_gain_unity_at_center_frequency(self):
        """Workflow step 4 (unity passband gain normalization): the
        bandpass center reference gain is 1.0 within 1e-12 (anchor
        1.000000000000000) and the center probe measures
        +0.000000000 dB, the passband gain normalized to exactly 1 at
        the center frequency of the translated prototype."""
        self.assertAlmostEqual(self.bp["center_gain"], 1.0, delta=1e-12)
        self.assertAlmostEqual(db(self.bp_c, 500, 4000), 0.0, delta=1e-6)

    def test_bandpass_edges_at_midpoint_target(self):
        """Workflow step 5 (band-edge verification): the measured
        bandpass edge gains are -5.995505518 dB at 200 Hz and
        -6.018418812 dB at 800 Hz (each within 1e-6 dB) and both sit
        within 0.1 dB of the -6.020599913279624 dB gain-0.5 midpoint
        target of the windowed-sinc band-edge geometry."""
        self.assertAlmostEqual(db(self.bp_c, 200, 4000),
                               -5.995505518, delta=1e-6)
        self.assertAlmostEqual(db(self.bp_c, 800, 4000),
                               -6.018418812, delta=1e-6)
        self.assertLess(abs(db(self.bp_c, 200, 4000) - TARGET_DB), 0.1)
        self.assertLess(abs(db(self.bp_c, 800, 4000) - TARGET_DB), 0.1)

    def test_bandpass_stopband_and_passband_probes(self):
        """Workflow step 6 (probe step): the cosine-sum magnitude
        response in dB at the stopband probes of the worked bandpass,
        window-ripple floors limited by the prototype stopband response
        at the translated image frequencies (DC -50.065791442, 100 Hz
        -62.087519915, 1000 Hz -57.420533724, 1200 Hz -61.325771718,
        1600 Hz -65.756900774 and Nyquist -66.996568467 dB) and the
        passband probe -0.002015073 dB at 400 Hz."""
        for freq_hz, anchor in ((0, -50.065791442), (100, -62.087519915),
                                (1000, -57.420533724),
                                (1200, -61.325771718),
                                (1600, -65.756900774),
                                (2000, -66.996568467)):
            self.assertAlmostEqual(db(self.bp_c, freq_hz, 4000), anchor,
                                   delta=1e-3)
        self.assertAlmostEqual(db(self.bp_c, 400, 4000),
                               -0.002015073, delta=1e-3)

    def test_bandpass_three_db_crossings_strictly_inside(self):
        """Where the -3.010299956640 dB level genuinely sits: the
        bandpass crossings at 215.960 and 784.004 Hz lie strictly
        between the requested 200 and 800 Hz edges, while both requested
        edge gains differ from -3.010299956640 dB by more than 1 dB
        (workflow step 5 band-edge verification)."""
        lo_x = crossing_hz(self.bp_c, 4000, 200, 500)
        hi_x = crossing_hz(self.bp_c, 4000, 500, 800)
        self.assertAlmostEqual(lo_x, 215.960, delta=0.05)
        self.assertAlmostEqual(hi_x, 784.004, delta=0.05)
        self.assertGreater(lo_x, 200.0)
        self.assertLess(hi_x, 800.0)
        self.assertGreater(abs(db(self.bp_c, 200, 4000) - LEVEL_3DB), 1.0)
        self.assertGreater(abs(db(self.bp_c, 800, 4000) - LEVEL_3DB), 1.0)

    def test_bandstop_dict_shape_and_anchor_taps(self):
        """Workflow step 3 (raw-construction translate-invert) and step 4
        (unity passband gain normalization): the bandstop spectral
        inversion of the translated bandpass returns exactly the nine
        documented keys and the worked Hamming tap anchors (center tap
        0.697809868401 = one minus the bandpass center tap to scale,
        neighbors -0.203543185312, outer taps +0.000660205105,
        +0.000649896784 and +0.000131659006) at the notch geometry."""
        self.assertEqual(
            set(self.bs.keys()),
            {"coefficients", "num_taps", "low_cutoff_hz",
             "high_cutoff_hz", "center_frequency_hz", "sample_rate_hz",
             "window", "group_delay_samples", "dc_gain"})
        c = self.bs_c
        self.assertAlmostEqual(c[50], 0.697809868401, delta=1e-9)
        self.assertAlmostEqual(c[49], -0.203543185312, delta=1e-9)
        self.assertAlmostEqual(c[51], -0.203543185312, delta=1e-9)
        self.assertAlmostEqual(c[48], 0.0, delta=1e-9)
        self.assertAlmostEqual(c[52], 0.0, delta=1e-9)
        self.assertAlmostEqual(c[1], 0.000660205105, delta=1e-9)
        self.assertAlmostEqual(c[2], 0.000649896784, delta=1e-9)
        self.assertAlmostEqual(c[3], 0.000131659006, delta=1e-9)

    def test_bandstop_dc_gain_unity_and_edge_midpoint(self):
        """Workflow step 4 (unity passband gain normalization) and step 5
        (band-edge verification): the bandstop DC reference gain is 1.0
        within 1e-12 and the measured notch-band edge gains are
        -6.073441862 dB at 200 Hz and -6.050454002 dB at 800 Hz (each
        within 1e-6 dB), both within 0.1 dB of the -6.020599913279624 dB
        midpoint target; the Nyquist passband gain -0.031101109 dB stays
        within 0.1 dB of 0 (the notch complement is not perfect)."""
        self.assertAlmostEqual(self.bs["dc_gain"], 1.0, delta=1e-12)
        self.assertAlmostEqual(db(self.bs_c, 200, 4000),
                               -6.073441862, delta=1e-6)
        self.assertAlmostEqual(db(self.bs_c, 800, 4000),
                               -6.050454002, delta=1e-6)
        self.assertLess(abs(db(self.bs_c, 200, 4000) - TARGET_DB), 0.1)
        self.assertLess(abs(db(self.bs_c, 800, 4000) - TARGET_DB), 0.1)
        self.assertLess(abs(db(self.bs_c, 2000, 4000)), 0.1)

    def test_bandstop_passband_notch_and_null_probes(self):
        """Workflow step 6 (probe step): the bandstop passband probes
        read -0.000000000 dB at DC and -0.031101109 dB at Nyquist
        (unity passband with small notch-complement droop), -0.020390713
        dB at 100 Hz and -0.034678594 dB at 1200 Hz, while the in-notch
        probe -74.933184863 dB at 400 Hz and the notch center null
        -85.671233701 dB at 500 Hz (the float floor of the imperfect
        complement) sit far below -60 dB."""
        self.assertAlmostEqual(db(self.bs_c, 0, 4000), 0.0, delta=1e-6)
        self.assertAlmostEqual(db(self.bs_c, 2000, 4000),
                               -0.031101109, delta=1e-6)
        self.assertAlmostEqual(db(self.bs_c, 100, 4000),
                               -0.020390713, delta=1e-3)
        self.assertAlmostEqual(db(self.bs_c, 1200, 4000),
                               -0.034678594, delta=1e-3)
        self.assertAlmostEqual(db(self.bs_c, 400, 4000),
                               -74.933184863, delta=1e-3)
        self.assertLess(db(self.bs_c, 500, 4000), -60.0)
        self.assertAlmostEqual(db(self.bs_c, 500, 4000),
                               -85.671233701, delta=1e-3)

    def test_bandstop_three_db_shoulders_strictly_outside(self):
        """Where the -3.010299956640 dB level genuinely sits: the
        bandstop notch shoulders at 183.781 and 816.188 Hz lie strictly
        outside the 200 to 800 Hz notch band, and both requested edge
        gains differ from -3.010299956640 dB by more than 1 dB
        (workflow step 5 band-edge verification)."""
        lo_x = crossing_hz(self.bs_c, 4000, 100, 200)
        hi_x = crossing_hz(self.bs_c, 4000, 800, 1000)
        self.assertAlmostEqual(lo_x, 183.781, delta=0.05)
        self.assertAlmostEqual(hi_x, 816.188, delta=0.05)
        self.assertLess(lo_x, 200.0)
        self.assertGreater(hi_x, 800.0)
        self.assertGreater(abs(db(self.bs_c, 200, 4000) - LEVEL_3DB), 1.0)
        self.assertGreater(abs(db(self.bs_c, 800, 4000) - LEVEL_3DB), 1.0)

    def test_band_edge_checks_verdicts_all_pass(self):
        """Workflow step 5 (band-edge verification): band_edge_checks on
        the three worked designs returns verdict PASS with target_db
        exactly the module constant -6.020599913279624, low_edge_ok and
        high_edge_ok True (edges within 0.1 dB of the midpoint), the
        bandstop extra a (dc_db, nyquist_db) pair, and the highpass
        high_edge_ok True with high_edge_db None."""
        for ftype, coeff, fs, lo, hi in (
                ("highpass", self.hp_c, 1000, 100, None),
                ("bandpass", self.bp_c, 4000, 200, 800),
                ("bandstop", self.bs_c, 4000, 200, 800)):
            chk = fmod.band_edge_checks(coeff, ftype, fs, lo, hi)
            self.assertEqual(chk["verdict"], "PASS")
            self.assertAlmostEqual(chk["target_db"], TARGET_DB, delta=1e-12)
            self.assertTrue(chk["low_edge_ok"])
            self.assertTrue(chk["high_edge_ok"])
            self.assertTrue(chk["passband_ok"])
        chk_hp = fmod.band_edge_checks(self.hp_c, "highpass", 1000, 100)
        self.assertIsNone(chk_hp["high_edge_db"])
        self.assertTrue(chk_hp["high_edge_ok"])
        chk_bs = fmod.band_edge_checks(self.bs_c, "bandstop", 4000, 200,
                                       800)
        self.assertIsInstance(chk_bs["extra"], tuple)
        self.assertEqual(len(chk_bs["extra"]), 2)

    def test_band_edge_checks_valueerror_calls(self):
        """Workflow step 5 guard rails: band_edge_checks raises
        ValueError for the unknown ftype 'notch', for ftype 'highpass'
        with high_cutoff_hz = 300 (the highpass has a single edge), for
        a band ftype with high_cutoff_hz None, and for invalid edges."""
        with self.assertRaises(ValueError):
            fmod.band_edge_checks(self.bp_c, "notch", 4000, 200, 800)
        with self.assertRaises(ValueError):
            fmod.band_edge_checks(self.hp_c, "highpass", 1000, 100, 300)
        with self.assertRaises(ValueError):
            fmod.band_edge_checks(self.bp_c, "bandpass", 4000, 200)
        with self.assertRaises(ValueError):
            fmod.band_edge_checks(self.bp_c, "bandstop", 4000, 800, 200)
        with self.assertRaises(ValueError):
            fmod.band_edge_checks(self.hp_c, "highpass", 1000, 0)

    def test_window_coefficients_anchor_values(self):
        """Workflow step 2 (the windowed prototype build): the four
        window weight sets share the cosine denominator num_taps - 1,
        are symmetric about the center tap, evaluate to exactly 1.0 at
        the center (cos(pi) = -1), and give the classical endpoint
        values (Hamming 0.08, Hann and Blackman 0.0)."""
        for win in ("rectangular", "hann", "hamming", "blackman"):
            w = fmod.window_coefficients(win, 101)
            self.assertEqual(len(w), 101)
            self.assertAlmostEqual(w[50], 1.0, delta=1e-12)
            for n in range(101):
                self.assertAlmostEqual(w[n], w[100 - n], delta=1e-12)
        rect = fmod.window_coefficients("rectangular", 101)
        self.assertTrue(all(abs(v - 1.0) < 1e-15 for v in rect))
        self.assertAlmostEqual(fmod.window_coefficients("hamming", 101)[0],
                               0.08, delta=1e-12)
        self.assertAlmostEqual(fmod.window_coefficients("hann", 101)[0],
                               0.0, delta=1e-12)
        self.assertAlmostEqual(
            fmod.window_coefficients("blackman", 101)[0], 0.0, delta=1e-12)
        self.assertEqual(fmod.window_coefficients("hamming", 1), [1.0])

    def test_window_coefficients_and_taps_valueerrors(self):
        """Workflow step 1 guard rails: unknown window names and
        num_taps below 1 raise ValueError in window_coefficients."""
        for bad in ("bartlett", "kaiser", "rect"):
            with self.assertRaises(ValueError):
                fmod.window_coefficients(bad, 101)
        with self.assertRaises(ValueError):
            fmod.window_coefficients("hamming", 0)

    def test_ideal_lowpass_taps_center_limit_and_values(self):
        """Workflow step 2 (the windowed prototype build): the ideal
        lowpass impulse response carries the center limit
        h_lp[M] = wc/pi = 2*fc/fs = 0.15 at the 300 Hz prototype cutoff
        and the sine form sin(wc*(n - M))/(pi*(n - M)) off center;
        nonphysical cutoffs, sample rates and tap counts raise
        ValueError."""
        taps = fmod.ideal_lowpass_taps(300, 4000, 101)
        self.assertAlmostEqual(taps[50], 0.15, delta=1e-12)
        wc = 2.0 * math.pi * 300.0 / 4000.0
        self.assertAlmostEqual(taps[49],
                               math.sin(-wc) / (-math.pi), delta=1e-12)
        self.assertAlmostEqual(taps[0],
                               math.sin(wc * -50.0) / (math.pi * -50.0),
                               delta=1e-12)
        for args in ((300, 0, 101), (300, -1000, 101), (0, 4000, 101),
                     (300, -1, 101), (2001, 4000, 101), (300, 4000, 0)):
            with self.assertRaises(ValueError):
                fmod.ideal_lowpass_taps(*args)

    def test_design_functions_reject_nonphysical_inputs(self):
        """Workflow step 1 (design-input fixing) guard rails: every
        design function raises ValueError on fs <= 0, zero or out-of-band
        cutoffs, low >= high, high >= fs/2, even or zero num_taps, and
        unknown window names."""
        for fn in (fmod.design_highpass,):
            for args in ((-1000, 100, 101, "hamming"),
                         (0, 100, 101, "hamming"),
                         (1000, 0, 101, "hamming"),
                         (1000, 600, 101, "hamming"),
                         (1000, 100, 100, "hamming"),
                         (1000, 100, 2, "hamming"),
                         (1000, 100, 0, "hamming"),
                         (1000, 100, 101, "bartlett")):
                with self.assertRaises(ValueError):
                    fn(*args)
        for fn in (fmod.design_bandpass, fmod.design_bandstop):
            for args in ((200, 800, -1000, 101, "hamming"),
                         (200, 800, 0, 101, "hamming"),
                         (0, 800, 4000, 101, "hamming"),
                         (400, 400, 4000, 101, "hamming"),
                         (800, 200, 4000, 101, "hamming"),
                         (200, 2000, 4000, 101, "hamming"),
                         (200, 800, 4000, 100, "hamming"),
                         (200, 800, 4000, 0, "hamming"),
                         (200, 800, 4000, 101, "bartlett")):
                with self.assertRaises(ValueError):
                    fn(*args)
        with self.assertRaises(ValueError):
            fmod.design_bandpass(200, None, 4000, 101, "hamming")

    def test_num_taps_one_degenerate_and_three_symmetric(self):
        """Workflow step 1 degenerate sanity: num_taps = 1 returns the
        single tap [1.0] for all three ftypes (the window is [1.0] and
        every design normalizes to the unit tap) and num_taps = 3
        designs run and stay symmetric about the center index."""
        for d in (fmod.design_highpass(100, 1000, 1, "hamming"),
                  fmod.design_bandpass(200, 800, 4000, 1, "hamming"),
                  fmod.design_bandstop(200, 800, 4000, 1, "hamming")):
            self.assertEqual(d["coefficients"], [1.0])
            self.assertEqual(d["group_delay_samples"], 0.0)
        for d in (fmod.design_highpass(100, 1000, 3, "hamming"),
                  fmod.design_bandpass(200, 800, 4000, 3, "hamming"),
                  fmod.design_bandstop(200, 800, 4000, 3, "hamming")):
            c = d["coefficients"]
            self.assertEqual(len(c), 3)
            self.assertAlmostEqual(c[0], c[2], delta=1e-12)

    def test_gain_and_db_probe_valueerrors_and_consistency(self):
        """Workflow step 6 (probe step): probes outside [0, fs/2] on an
        fs = 1000 design (-1 Hz and 600 Hz), a non-positive sample rate
        and an empty coefficient list raise ValueError, and
        magnitude_response_db equals 20*log10(gain_at) at every probe of
        the worked designs (real difference 0.0 dB at 400 Hz)."""
        for freq_hz in (-1, 600):
            with self.assertRaises(ValueError):
                fmod.gain_at(self.hp_c, freq_hz, 1000)
            with self.assertRaises(ValueError):
                fmod.magnitude_response_db(self.hp_c, freq_hz, 1000)
            with self.assertRaises(ValueError):
                fmod.magnitude_response_db(self.bp_c, freq_hz, 1000)
        with self.assertRaises(ValueError):
            fmod.gain_at([], 100, 1000)
        with self.assertRaises(ValueError):
            fmod.magnitude_response_db([], 100, 1000)
        with self.assertRaises(ValueError):
            fmod.gain_at(self.hp_c, 100, 0)
        for coeff, fs in ((self.hp_c, 1000), (self.bp_c, 4000),
                          (self.bs_c, 4000)):
            for freq_hz in (0.0, 100.0, 400.0, fs / 2.0):
                expected = 20.0 * math.log10(
                    fmod.gain_at(coeff, freq_hz, fs))
                self.assertAlmostEqual(
                    fmod.magnitude_response_db(coeff, freq_hz, fs),
                    expected, delta=1e-9)

    def test_dc_and_nyquist_probes_of_worked_designs(self):
        """Workflow step 6 (probe step): the 0 Hz and fs/2 probes are
        valid and the null floors are finite: the bandpass DC and
        Nyquist floors and the highpass DC floor all read below -40 dB
        while the bandstop DC and Nyquist gains stay above -0.1 dB."""
        self.assertLess(db(self.bp_c, 0, 4000), -40.0)
        self.assertLess(db(self.bp_c, 2000, 4000), -40.0)
        self.assertLess(db(self.hp_c, 0, 1000), -40.0)
        self.assertGreater(db(self.bs_c, 0, 4000), -0.1)
        self.assertGreater(db(self.bs_c, 2000, 4000), -0.1)
        self.assertAlmostEqual(fmod.gain_at(self.hp_c, 500, 1000), 1.0,
                               delta=1e-12)

    def test_group_delay_samples_identity(self):
        """Workflow step 6 (the group delay of the symmetric tap set):
        group_delay_samples returns the constant (num_taps - 1)/2
        samples for every odd tap count and raises ValueError below one
        tap."""
        self.assertEqual(fmod.group_delay_samples(101), 50.0)
        self.assertEqual(fmod.group_delay_samples(1), 0.0)
        self.assertEqual(fmod.group_delay_samples(3), 1.0)
        for nt in (0, -3):
            with self.assertRaises(ValueError):
                fmod.group_delay_samples(nt)

    def test_filter_signal_valueerrors(self):
        """Workflow step 6 guard rails: filter_signal raises ValueError
        on an empty sample list, a non-finite sample entry, an empty
        coefficient list and a non-finite coefficient entry."""
        with self.assertRaises(ValueError):
            fmod.filter_signal(self.bp_c, [])
        with self.assertRaises(ValueError):
            fmod.filter_signal(self.bp_c, [1.0, float("nan"), 2.0])
        with self.assertRaises(ValueError):
            fmod.filter_signal([], [1.0, 2.0])
        with self.assertRaises(ValueError):
            fmod.filter_signal([1.0, float("inf")], [1.0, 2.0])

    def test_filter_signal_impulse_round_trip(self):
        """Workflow step 6 (the direct-form filter): an impulse through
        filter_signal reproduces the designed coefficient vector exactly
        (max error 0.0, exact by construction) for the highpass,
        bandpass and bandstop tap sets."""
        impulse = [1.0] + [0.0] * 100
        for coeff in (self.hp_c, self.bp_c, self.bs_c):
            out = fmod.filter_signal(coeff, impulse)
            self.assertEqual(len(out), 101)
            self.assertEqual(max(abs(out[n] - coeff[n])
                                 for n in range(101)), 0.0)

    def test_filter_signal_constant_input_settle(self):
        """Workflow step 6 (the direct-form filter): a constant 5.0
        input settles over the settled tail to 5.000000000 through the
        bandstop (unity DC gain within 1e-6), to a tail mean of
        -1.569208e-02 through the bandpass (the DC stopband,
        -50.065791442 dB times 5.0, magnitude below 0.05) and to
        7.357413e-03 through the highpass (the spectral-inversion DC
        null floor)."""
        const5 = [5.0] * 2000
        tail = 1000
        bs_tail = fmod.filter_signal(self.bs_c, const5)[tail:]
        self.assertAlmostEqual(sum(bs_tail) / len(bs_tail), 5.0,
                               delta=1e-6)
        bp_tail = fmod.filter_signal(self.bp_c, const5)[tail:]
        self.assertLess(abs(sum(bp_tail) / len(bp_tail)), 0.05)
        hp_tail = fmod.filter_signal(self.hp_c, const5)[tail:]
        self.assertLess(abs(sum(hp_tail) / len(hp_tail)), 0.05)

    def test_filter_signal_alternating_input_settle(self):
        """Workflow step 6 (the direct-form filter): an alternating
        +5/-5 input settles through the bandpass to a tail RMS of
        4.468601e-04 relative to 5.0 (the Nyquist stopband,
        -66.996568467 dB) and through the bandstop to 0.996425755
        relative (the near-unity Nyquist gain)."""
        alt = [5.0 if n % 2 == 0 else -5.0 for n in range(2000)]
        bp_out = fmod.filter_signal(self.bp_c, alt)[1000:]
        rms_rel = math.sqrt(sum(v * v for v in bp_out) / len(bp_out)) / 5.0
        self.assertAlmostEqual(rms_rel, 4.468601e-04, delta=1e-6)
        bs_out = fmod.filter_signal(self.bs_c, alt)[1000:]
        rms_rel_bs = math.sqrt(sum(v * v for v in bs_out)
                               / len(bs_out)) / 5.0
        self.assertAlmostEqual(rms_rel_bs, 0.996425755, delta=1e-6)

    def test_tone_identity_bandpass(self):
        """Workflow step 6 (the probe-filter step): the three-tone record
        at 100, 400 and 1200 Hz through filter_signal reproduces the
        designed |H| at each tone by quadrature projection over the
        settled integer-cycle tail within 1e-9 relative; the 400 Hz
        passband tone gain sits above -1 dB while the 100 Hz and 1200 Hz
        stopband tones sit below -40 dB (anchors -62.088 and -61.326
        dB)."""
        tail = (1000, 5000)
        cases = ((100, -40.0, True), (400, -1.0, False),
                 (1200, -40.0, True))
        for freq_hz, threshold_db, must_be_below in cases:
            measured = tone_gain(self.bp_c, 4000, freq_hz, tail[0],
                                 tail[1])
            expected = fmod.gain_at(self.bp_c, freq_hz, 4000)
            self.assertLess(abs(measured - expected) / expected, 1e-9)
            measured_db = 20.0 * math.log10(measured)
            if must_be_below:
                self.assertLess(measured_db, threshold_db)
            else:
                self.assertGreater(measured_db, threshold_db)

    def test_tone_identity_bandstop(self):
        """Workflow step 6 (the probe-filter step): the three-tone record
        at 100, 500 and 1200 Hz reproduces the designed bandstop |H| at
        each tone within 1e-9 relative; the 500 Hz in-notch tone gain
        sits below -40 dB (anchor -85.671 dB, the float floor of the
        imperfect notch complement) while the 100 Hz and 1200 Hz
        passband tones sit above -0.5 dB."""
        tail = (1000, 5000)
        cases = ((100, -0.5, False), (500, -40.0, True),
                 (1200, -0.5, False))
        for freq_hz, threshold_db, must_be_below in cases:
            measured = tone_gain(self.bs_c, 4000, freq_hz, tail[0],
                                 tail[1])
            expected = fmod.gain_at(self.bs_c, freq_hz, 4000)
            self.assertLess(abs(measured - expected) / expected, 1e-9)
            measured_db = 20.0 * math.log10(measured)
            if must_be_below:
                self.assertLess(measured_db, threshold_db)
            else:
                self.assertGreater(measured_db, threshold_db)

    def test_tone_identity_highpass(self):
        """Workflow step 6 (the probe-filter step): the two-tone record
        at 20 and 300 Hz (fs = 1000) reproduces the designed highpass
        |H| within 1e-9 relative; the 300 Hz passband tone sits above
        -1 dB while the 20 Hz tone measures 0.001513484842 against |H|
        0.001513484842, below -40 dB (anchor -56.400 dB)."""
        tail = (1000, 2000)
        cases = ((20, -40.0, True), (300, -1.0, False))
        for freq_hz, threshold_db, must_be_below in cases:
            measured = tone_gain(self.hp_c, 1000, freq_hz, tail[0],
                                 tail[1])
            expected = fmod.gain_at(self.hp_c, freq_hz, 1000)
            self.assertLess(abs(measured - expected) / expected, 1e-9)
            measured_db = 20.0 * math.log10(measured)
            if must_be_below:
                self.assertLess(measured_db, threshold_db)
            else:
                self.assertGreater(measured_db, threshold_db)
        self.assertAlmostEqual(fmod.gain_at(self.hp_c, 20, 1000),
                               0.001513484842, delta=1e-12)

    def test_determinism_bitwise_identical_designs(self):
        """Workflow determinism: two identical calls to each design
        function are bitwise identical (plain row-by-row cosine-sum
        accumulation, no RNG anywhere), so the module is reproducible
        run to run."""
        for fn, args in ((fmod.design_highpass, (100, 1000, 101,
                                                 "hamming")),
                         (fmod.design_bandpass, (200, 800, 4000, 101,
                                                 "hamming")),
                         (fmod.design_bandstop, (200, 800, 4000, 101,
                                                 "hamming"))):
            d1 = fn(*args)
            d2 = fn(*args)
            self.assertEqual(d1["coefficients"], d2["coefficients"])
            for key in d1:
                if isinstance(d1[key], list):
                    self.assertEqual(d1[key], d2[key])
                else:
                    self.assertEqual(d1[key], d2[key])

    def test_module_imports_only_math(self):
        """Workflow purity: the logic module is pure Python stdlib whose
        only import is math, so the windowed-sinc designs are
        deterministic and offline with no external processes."""
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "fir_bandpass_bandstop_filter_design_logic.py")
        with open(logic_path, "r") as handle:
            tree = ast.parse(handle.read())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module is not None:
                    imports.add(node.module)
        self.assertEqual(imports, {"math"})

    def test_raw_construction_recovery_identities(self):
        """Workflow step 3 (the raw-construction translate-invert step)
        and step 4 (unity passband gain normalization): rebuilding the
        window, the windowed prototype p[n], the three raw tap sets and
        the passband scale G with math only recovers the normalized taps
        (max |b[n]*G - raw[n]| below 1e-9 for every worked design), and
        the bandstop complement identity b_bs_raw[n] + b_bp_raw[n] =
        w[n]*delta[n - M] holds elementwise below 1e-9."""
        n_taps = 101
        m = 50.0
        w = [0.54 - 0.46 * math.cos(2.0 * math.pi * n / 100.0)
             for n in range(n_taps)]

        def proto(fc, fs):
            wc = 2.0 * math.pi * fc / fs
            out = []
            for n in range(n_taps):
                d = float(n) - m
                if d == 0.0:
                    out.append(wc / math.pi)
                else:
                    out.append(math.sin(wc * d) / (math.pi * d))
            return [w[n] * out[n] for n in range(n_taps)]

        def cos_sum(taps, freq_hz, fs):
            total = 0.0
            for n in range(n_taps):
                total += taps[n] * math.cos(
                    2.0 * math.pi * freq_hz / fs * (float(n) - m))
            return total

        hp_p = proto(100, 1000)
        hp_raw = [(w[n] if float(n) == m else 0.0) - hp_p[n]
                  for n in range(n_taps)]
        g_hp = abs(cos_sum(hp_raw, 500, 1000))
        for n in range(n_taps):
            self.assertLess(abs(self.hp_c[n] * g_hp - hp_raw[n]), 1e-9)

        fc_proto = 300.0
        w0 = 2.0 * math.pi * 500.0 / 4000.0
        bp_p = proto(fc_proto, 4000)
        bp_raw = [2.0 * bp_p[n] * math.cos(w0 * (float(n) - m))
                  for n in range(n_taps)]
        g_bp = abs(cos_sum(bp_raw, 500, 4000))
        for n in range(n_taps):
            self.assertLess(abs(self.bp_c[n] * g_bp - bp_raw[n]), 1e-9)

        bs_raw = [((w[n] if float(n) == m else 0.0)
                   - 2.0 * bp_p[n] * math.cos(w0 * (float(n) - m)))
                  for n in range(n_taps)]
        g_bs = abs(cos_sum(bs_raw, 0, 4000))
        for n in range(n_taps):
            self.assertLess(abs(self.bs_c[n] * g_bs - bs_raw[n]), 1e-9)
        for n in range(n_taps):
            delta_center = 1.0 if float(n) == m else 0.0
            self.assertLess(abs(bs_raw[n] + bp_raw[n]
                                - w[n] * delta_center), 1e-9)

    def test_symmetry_of_all_worked_designs(self):
        """Workflow step 2 symmetry: the windowed taps stay symmetric
        about the integer center index M = 50 (max |b[n] - b[100 - n]|
        below 1e-12; real anchors 1.4e-17 highpass and 2.8e-17 bandpass
        and bandstop), the linear-phase property that fixes the constant
        group delay."""
        for coeff in (self.hp_c, self.bp_c, self.bs_c):
            worst = max(abs(coeff[n] - coeff[100 - n])
                        for n in range(101))
            self.assertLess(worst, 1e-12)

    def test_window_trade_at_bandpass_geometry(self):
        """Workflow step 1 window selection: at the bandpass geometry the
        Hann and Blackman edge gains stay within 0.1 dB of the
        -6.020599913 dB midpoint target and the rectangular lower edge
        within 0.4 dB (anchor -5.701966 dB, the largest image-leakage
        bias), while the 1200 Hz stopband probe orders rectangular
        -38.919 dB above hamming -61.326 dB above hann -85.570 dB above
        blackman -94.916 dB (each within 0.5 dB of its anchor)."""
        probes = {}
        for win in ("rectangular", "hann", "hamming", "blackman"):
            d = fmod.design_bandpass(200, 800, 4000, 101, win)
            probes[win] = (db(d["coefficients"], 200, 4000),
                           db(d["coefficients"], 1200, 4000))
        self.assertLess(abs(probes["hann"][0] - TARGET_DB), 0.1)
        self.assertLess(abs(probes["blackman"][0] - TARGET_DB), 0.1)
        self.assertAlmostEqual(probes["rectangular"][0], -5.701966,
                               delta=0.4)
        self.assertAlmostEqual(probes["rectangular"][1], -38.919,
                               delta=0.5)
        self.assertAlmostEqual(probes["hamming"][1], -61.326, delta=0.5)
        self.assertAlmostEqual(probes["hann"][1], -85.570, delta=0.5)
        self.assertAlmostEqual(probes["blackman"][1], -94.916, delta=0.5)
        self.assertLess(probes["hamming"][1], probes["rectangular"][1])
        self.assertLess(probes["hann"][1], probes["hamming"][1])
        self.assertLess(probes["blackman"][1], probes["hann"][1])


if __name__ == "__main__":
    unittest.main()

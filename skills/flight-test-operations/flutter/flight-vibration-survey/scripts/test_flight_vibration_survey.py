"""Offline deterministic contract test: flight-vibration-survey leaf.

Run: python3 scripts/test_flight_vibration_survey.py
Covers the worked example of the spec (rotor 5 Hz, 1000 Hz sampling,
12-rev window N = 2400, sines 0.15 g at 1P + 0.06 g at 2P + 0.08 g at
4P), the synchronous DFT exact-order recovery to 1e-6, the
total-RMS equals RSS-of-orders identity, windowed RMS, verdict logic,
leakage rejection of off-order tones, ValueError rejection of
non-physical inputs, the documented summary key set and run-to-run
determinism. Pure stdlib, no network, deterministic.
"""

import math
import unittest

import flight_vibration_survey_logic as fvs

RATE_HZ = 1000.0
ROTOR_HZ = 5.0
M_REVS = 12
N_WINDOW = int(round(M_REVS * RATE_HZ / ROTOR_HZ))  # 2400 samples


def make_record(order_amps, n_samples=N_WINDOW, rate_hz=RATE_HZ,
                rotor_hz=ROTOR_HZ, phase=0.7):
    """Deterministic multi-order sine record in g. order_amps maps
    integer order p to its amplitude; each tone carries phase p*phase.
    """
    return [sum(amp * math.cos(
        2.0 * math.pi * order * rotor_hz * k / rate_hz + phase * order)
        for order, amp in order_amps.items())
        for k in range(n_samples)]


WORKED_AMPS = {1: 0.15, 2: 0.06, 4: 0.08}
WORKED_SIGNAL = make_record(WORKED_AMPS)


class FlightVibrationSurveyContract(unittest.TestCase):
    """Contract tests for the in-flight vibration survey reduction."""

    # --- exact-order recovery -------------------------------------------------

    def test_1p_single_tone_recovers_amplitude(self):
        sig = make_record({1: 0.15})
        self.assertAlmostEqual(
            fvs.order_amplitude(sig, RATE_HZ, ROTOR_HZ, 1, M_REVS),
            0.15, places=6)

    def test_2p_single_tone_recovers_amplitude(self):
        sig = make_record({2: 0.06})
        self.assertAlmostEqual(
            fvs.order_amplitude(sig, RATE_HZ, ROTOR_HZ, 2, M_REVS),
            0.06, places=6)

    def test_4p_single_tone_recovers_amplitude(self):
        sig = make_record({4: 0.08})
        self.assertAlmostEqual(
            fvs.order_amplitude(sig, RATE_HZ, ROTOR_HZ, 4, M_REVS),
            0.08, places=6)

    def test_multi_order_recovery_all_orders(self):
        for order, amp in WORKED_AMPS.items():
            self.assertAlmostEqual(
                fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                    order, M_REVS),
                amp, places=6,
                msg="order %d amplitude not recovered" % order)

    def test_recovery_is_phase_invariant(self):
        sig_a = make_record(WORKED_AMPS, phase=0.1)
        sig_b = make_record(WORKED_AMPS, phase=2.1)
        for order in (1, 2, 4):
            a = fvs.order_amplitude(sig_a, RATE_HZ, ROTOR_HZ, order, M_REVS)
            b = fvs.order_amplitude(sig_b, RATE_HZ, ROTOR_HZ, order, M_REVS)
            self.assertAlmostEqual(a, WORKED_AMPS[order], places=6)
            self.assertAlmostEqual(b, WORKED_AMPS[order], places=6)

    # --- total RMS and the RSS identity ---------------------------------------

    def test_total_rms_single_tone_identity(self):
        sig = make_record({3: 0.1})
        self.assertAlmostEqual(fvs.total_rms(sig), 0.1 / math.sqrt(2.0),
                               places=6)

    def test_total_rms_multi_order_0p12748(self):
        self.assertAlmostEqual(fvs.total_rms(WORKED_SIGNAL), 0.12748,
                               delta=1e-5)

    def test_rss_equals_total_rms_identity(self):
        amps = {p: fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ, p,
                                       M_REVS)
                for p in (1, 2, 4)}
        self.assertAlmostEqual(fvs.rss_of_orders(amps),
                               fvs.total_rms(WORKED_SIGNAL), places=6)

    def test_rss_known_value_0p12748(self):
        # sqrt((0.15^2 + 0.06^2 + 0.08^2) / 2) = sqrt(0.01625)
        rss = fvs.rss_of_orders({1: 0.15, 2: 0.06, 4: 0.08})
        self.assertAlmostEqual(rss, 0.12748, delta=1e-5)
        self.assertAlmostEqual(rss * rss, 0.01625, places=6)

    # --- windowed RMS ----------------------------------------------------------

    def test_windowed_rms_single_window_matches_total(self):
        levels = fvs.windowed_rms(WORKED_SIGNAL, RATE_HZ, 2.4)
        self.assertEqual(len(levels), 1)
        self.assertAlmostEqual(levels[0], fvs.total_rms(WORKED_SIGNAL),
                               places=6)

    def test_windowed_rms_two_half_windows(self):
        # Each 1.2 s window holds 6 integer revolutions of every tone, so
        # each window RMS equals the full-record value.
        levels = fvs.windowed_rms(WORKED_SIGNAL, RATE_HZ, 1.2)
        self.assertEqual(len(levels), 2)
        for level in levels:
            self.assertAlmostEqual(level, 0.12748, delta=1e-4)

    def test_windowed_rms_partial_trailing_window_dropped(self):
        long_sig = make_record(WORKED_AMPS, n_samples=2500)
        levels = fvs.windowed_rms(long_sig, RATE_HZ, 0.6)
        # 4 full 600-sample windows; the partial [2400:2500] is dropped.
        self.assertEqual(len(levels), 4)
        for level in levels:
            self.assertAlmostEqual(level, 0.12748, delta=1e-3)

    # --- verdict logic ---------------------------------------------------------

    def test_vibration_verdict_pass_margin_0p150(self):
        vv = fvs.vibration_verdict(fvs.total_rms(WORKED_SIGNAL), 0.15)
        self.assertAlmostEqual(vv["margin"], 0.150163, places=4)
        self.assertEqual(round(vv["margin"], 3), 0.150)
        self.assertTrue(vv["pass"])

    def test_vibration_verdict_fail_negative_margin(self):
        vv = fvs.vibration_verdict(0.20, 0.15)
        self.assertAlmostEqual(vv["margin"], -0.333333, places=5)
        self.assertFalse(vv["pass"])

    def test_vibration_verdict_at_limit_zero_margin_passes(self):
        vv = fvs.vibration_verdict(0.15, 0.15)
        self.assertEqual(vv["margin"], 0.0)
        self.assertTrue(vv["pass"])

    def test_trim_verdict_needs_trim_minus_0p500(self):
        tv = fvs.trim_verdict(0.15, 0.10)
        self.assertAlmostEqual(tv["margin"], -0.500000, places=6)
        self.assertTrue(tv["needs_trim"])

    def test_trim_verdict_within_limit(self):
        tv = fvs.trim_verdict(0.08, 0.10)
        self.assertAlmostEqual(tv["margin"], 0.200000, places=6)
        self.assertFalse(tv["needs_trim"])

    def test_trim_verdict_at_limit_no_trim(self):
        tv = fvs.trim_verdict(0.10, 0.10)
        self.assertEqual(tv["margin"], 0.0)
        self.assertFalse(tv["needs_trim"])

    # --- survey summary --------------------------------------------------------

    def test_survey_summary_worked_example(self):
        sm = fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                          [1, 2, 4], M_REVS, 0.15, 0.10)
        for order, amp in WORKED_AMPS.items():
            self.assertAlmostEqual(sm["order_amplitudes_g"][order], amp,
                                   places=6)
        self.assertAlmostEqual(sm["total_rms_g"], 0.12748, delta=1e-5)
        self.assertAlmostEqual(sm["rss_of_orders_g"], sm["total_rms_g"],
                               places=6)
        self.assertAlmostEqual(sm["vibration_verdict"]["margin"], 0.150163,
                               places=4)
        self.assertTrue(sm["vibration_verdict"]["pass"])
        self.assertAlmostEqual(sm["trim_verdict"]["margin"], -0.500000,
                               places=6)
        self.assertTrue(sm["trim_verdict"]["needs_trim"])

    def test_survey_summary_documented_keys(self):
        sm = fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                          [1, 2, 4], M_REVS, 0.15, 0.10)
        self.assertEqual(
            set(sm.keys()),
            {"order_amplitudes_g", "total_rms_g", "rss_of_orders_g",
             "vibration_verdict", "trim_verdict"})

    def test_survey_summary_requires_order_1(self):
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                         [2, 4], M_REVS, 0.15, 0.10)

    def test_survey_summary_short_record_valueerror(self):
        short = make_record(WORKED_AMPS, n_samples=N_WINDOW - 1)
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(short, RATE_HZ, ROTOR_HZ,
                                         [1, 2, 4], M_REVS, 0.15, 0.10)

    # --- leakage ---------------------------------------------------------------

    def test_leakage_2p5_tone_absent_from_order_bins(self):
        # A 2.5P tone (bin-centered in the 12-rev window) must not appear
        # in any integer-order bin: orthogonality keeps it at the DFT
        # numerical floor, far below the sidelobe level.
        sig = make_record({2.5: 0.1})
        for order in range(1, 9):
            amp = fvs.order_amplitude(sig, RATE_HZ, ROTOR_HZ, order, M_REVS)
            self.assertLess(amp, 1e-6,
                            "2.5P tone leaked into order %d" % order)

    def test_leakage_non_bin_centered_tone_below_sidelobe(self):
        # A 2.3P tone sits between DFT bins; its leakage into the
        # integer-order bins must stay below the rectangular-window
        # sidelobe envelope (worst case about 0.22 relative amplitude),
        # so 0.1 g cannot read above 0.05 g in any order bin.
        sig = make_record({2.3: 0.1})
        for order in range(1, 9):
            amp = fvs.order_amplitude(sig, RATE_HZ, ROTOR_HZ, order, M_REVS)
            self.assertLess(amp, 0.05,
                            "2.3P tone leaked into order %d: %g g" %
                            (order, amp))
        # The tone itself is present in the record energy; 2.3P spans
        # 27.6 cycles of the 12-rev window, so its windowed RMS sits
        # close to (not exactly at) A / sqrt(2).
        self.assertAlmostEqual(fvs.total_rms(sig), 0.1 / math.sqrt(2.0),
                               delta=1e-3)

    # --- determinism -----------------------------------------------------------

    def test_determinism_repeat_runs_identical(self):
        first = fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                             [1, 2, 4], M_REVS, 0.15, 0.10)
        second = fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ,
                                              ROTOR_HZ, [1, 2, 4], M_REVS,
                                              0.15, 0.10)
        self.assertEqual(first, second)
        a = fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ, 1, M_REVS)
        b = fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ, 1, M_REVS)
        self.assertEqual(a, b)

    # --- integer-rev window convention ----------------------------------------

    def test_window_rounding_convention_uses_integer_n(self):
        # N = round(1 * 10 / 3) = 3 samples: the order DFT runs over
        # exactly 3 samples, so a constant record reads zero at order 1.
        sig = make_record({1: 0.0}, n_samples=3, rate_hz=10.0, rotor_hz=3.0)
        amp = fvs.order_amplitude(sig, 10.0, 3.0, 1, 1)
        self.assertAlmostEqual(amp, 0.0, places=9)
        with self.assertRaises(ValueError):
            fvs.order_amplitude([1.0, 1.0], 10.0, 3.0, 1, 1)

    # --- ValueError rejections -------------------------------------------------

    def test_valueerror_empty_samples(self):
        with self.assertRaises(ValueError):
            fvs.order_amplitude([], RATE_HZ, ROTOR_HZ, 1, M_REVS)
        with self.assertRaises(ValueError):
            fvs.total_rms([])
        with self.assertRaises(ValueError):
            fvs.windowed_rms([], RATE_HZ, 1.0)
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary([], RATE_HZ, ROTOR_HZ, [1], M_REVS,
                                         0.15, 0.10)

    def test_valueerror_nonpositive_sample_rate(self):
        for rate in (0.0, -100.0):
            with self.assertRaises(ValueError):
                fvs.order_amplitude(WORKED_SIGNAL, rate, ROTOR_HZ, 1, M_REVS)
        with self.assertRaises(ValueError):
            fvs.windowed_rms(WORKED_SIGNAL, 0.0, 1.0)

    def test_valueerror_nonpositive_rotor_hz(self):
        for rotor in (0.0, -5.0):
            with self.assertRaises(ValueError):
                fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, rotor, 1, M_REVS)
            with self.assertRaises(ValueError):
                fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, rotor,
                                             [1], M_REVS, 0.15, 0.10)

    def test_valueerror_order_below_one(self):
        for order in (0, -1, -4):
            with self.assertRaises(ValueError):
                fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ, order,
                                    M_REVS)
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                         [1, 0], M_REVS, 0.15, 0.10)

    def test_valueerror_m_revs_below_one(self):
        for m in (0, -2):
            with self.assertRaises(ValueError):
                fvs.order_amplitude(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ, 1, m)
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                         [1], 0, 0.15, 0.10)

    def test_valueerror_nonpositive_limits(self):
        for limit in (0.0, -0.15):
            with self.assertRaises(ValueError):
                fvs.vibration_verdict(0.1, limit)
            with self.assertRaises(ValueError):
                fvs.trim_verdict(0.1, limit)
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                         [1], M_REVS, 0.0, 0.10)
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                         [1], M_REVS, 0.15, 0.0)
        # Negative measured levels and amplitudes are unphysical too.
        with self.assertRaises(ValueError):
            fvs.vibration_verdict(-0.1, 0.15)
        with self.assertRaises(ValueError):
            fvs.trim_verdict(-0.1, 0.10)

    def test_valueerror_windowed_rms_bad_window(self):
        with self.assertRaises(ValueError):
            fvs.windowed_rms(WORKED_SIGNAL, RATE_HZ, 0.0)
        with self.assertRaises(ValueError):
            fvs.windowed_rms(WORKED_SIGNAL, -1.0, 1.0)

    def test_valueerror_rss_empty_dict(self):
        with self.assertRaises(ValueError):
            fvs.rss_of_orders({})

    def test_valueerror_survey_empty_orders(self):
        with self.assertRaises(ValueError):
            fvs.vibration_survey_summary(WORKED_SIGNAL, RATE_HZ, ROTOR_HZ,
                                         [], M_REVS, 0.15, 0.10)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Contract test: shock response spectrum (structures/loads).

Exercises scripts/shock_response_spectrum_logic.py (stdlib unittest,
offline, deterministic).  Model: SDOF oscillators at a frequency grid
and fixed damping, base-excited by a half-sine or decaying-sine
acceleration pulse, integrated with fixed-step RK4
(dt = min(1/(fn*50), T/200)) over the excitation support; the SRS
ordinate is the peak pseudo acceleration wn^2 * max|x| of the forced
response.

Worked example: half-sine 10 g (98.0665 m/s2), 10 ms, Q 10, grid
[5..1000] Hz.  Exact module values (recorded for determinism asserts):

    5 Hz     3.032667 m/s2 = 0.309246 g
    80 Hz   161.437325 m/s2 = 16.462026 g   (grid maximum)
    1000 Hz  99.158608 m/s2 = 10.111364 g

Spec anchors: 5 Hz within 10% and within 0.05 g of 0.31 g; maximum
frequency in [60, 100] Hz with peak within 10% of 16.5 g; 1000 Hz
within 10% of 10.1 g; monotonic 20 Hz < 80 Hz and 500 Hz < 80 Hz.

Decaying-sine case: 10 g, T 10 ms, tau 30 ms, Q 10.  Exact module
values: maximum at 100 Hz, 350.878246 m/s2 = 35.779624 g (finite;
maximum frequency in [70, 130] Hz).

Invalid inputs (zero or negative amplitude, zero or negative pulse
duration, q <= 0.5, empty grid, non-positive frequencies, unknown pulse
type, non-positive decay tau, bad sdof_peak arguments) raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shock_response_spectrum_logic as srs  # noqa: E402

# Contract-case constants (worked example in SKILL.md).
AMPLITUDE_G = 10.0
AMPLITUDE = AMPLITUDE_G * srs.G      # 10 g in m/s2
PULSE_T = 0.010                      # 10 ms pulse duration
TAU = 0.030                          # decaying-sine decay constant
GRID = [5, 10, 20, 30, 40, 50, 60, 80, 100, 150, 200, 300, 500, 1000]
Q = srs.Q_DEFAULT

# Exact module values (deterministic), used for places-based asserts.
P5_G = 0.309246          # 5 Hz ordinate, g
P5_MS2 = 3.032667        # 5 Hz ordinate, m/s2
P80_G = 16.462026        # 80 Hz ordinate, g (grid maximum)
P80_MS2 = 161.437325     # 80 Hz ordinate, m/s2
P1000_G = 10.111364      # 1000 Hz ordinate, g
P1000_MS2 = 99.158608    # 1000 Hz ordinate, m/s2
D100_G = 35.779624       # decaying-sine 100 Hz ordinate, g (maximum)


def curve_entry(curve, freq):
    """Return the SRS curve entry dict for a given frequency."""
    return next(e for e in curve if e["freq_hz"] == freq)


class BaseAccelTest(unittest.TestCase):
    """The analytic base acceleration histories."""

    def test_half_sine_mid_pulse_is_amplitude(self):
        self.assertEqual(srs.base_accel(PULSE_T / 2.0, "half-sine",
                                        AMPLITUDE, PULSE_T, TAU),
                         AMPLITUDE)

    def test_half_sine_quarter_pulse_value(self):
        expected = AMPLITUDE * math.sin(math.pi / 4.0)
        self.assertAlmostEqual(srs.base_accel(PULSE_T / 4.0, "half-sine",
                                              AMPLITUDE, PULSE_T, TAU),
                               expected, places=9)

    def test_half_sine_zero_outside_pulse(self):
        for t in (-PULSE_T, 0.0, PULSE_T, 2.0 * PULSE_T, 1.0):
            self.assertEqual(srs.base_accel(t, "half-sine", AMPLITUDE,
                                            PULSE_T, TAU), 0.0)

    def test_decaying_sine_matches_formula(self):
        t = 0.0025  # quarter input period, sine equal to one
        expected = AMPLITUDE * math.exp(-t / TAU)
        self.assertAlmostEqual(srs.base_accel(t, "decaying-sine",
                                              AMPLITUDE, PULSE_T, TAU),
                               expected, places=9)

    def test_decaying_sine_envelope_decays(self):
        # At t = 5*tau the envelope is exp(-5) of the peak.
        t = 5.0 * TAU
        peak_mag = max(abs(srs.base_accel(k * 0.0001, "decaying-sine",
                                          AMPLITUDE, PULSE_T, TAU))
                       for k in range(300))
        self.assertLess(abs(srs.base_accel(t, "decaying-sine", AMPLITUDE,
                                           PULSE_T, TAU)),
                        peak_mag * math.exp(-4.0))

    def test_decaying_sine_negative_time_zero(self):
        self.assertEqual(srs.base_accel(-1.0, "decaying-sine", AMPLITUDE,
                                        PULSE_T, TAU), 0.0)

    def test_invalid_pulse_type_raises(self):
        with self.assertRaises(ValueError):
            srs.base_accel(0.001, "triangular", AMPLITUDE, PULSE_T, TAU)


class HalfSineWorkedExampleTest(unittest.TestCase):
    """The half-sine 10 g, 10 ms, Q 10 SRS contract."""

    @classmethod
    def setUpClass(cls):
        cls.curve = srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, GRID, Q)

    def test_5hz_anchor_and_deterministic_value(self):
        # Anchor checks: within 0.05 g and within 10% of 0.31 g, plus the
        # module's own deterministic value (RK4 value depends on dt).
        g = curve_entry(self.curve, 5.0)["peak_g"]
        self.assertLess(abs(g - 0.31), 0.05)
        self.assertLess(abs(g - 0.31) / 0.31, 0.10)
        self.assertAlmostEqual(g, P5_G, places=5)
        self.assertAlmostEqual(curve_entry(self.curve, 5.0)["peak_ms2"],
                               P5_MS2, places=4)

    def test_slow_oscillator_response_below_input(self):
        # A 5 Hz oscillator is slow relative to the 10 ms pulse.
        self.assertLess(curve_entry(self.curve, 5.0)["peak_g"], 1.0)

    def test_maximum_frequency_band_and_anchor_value(self):
        mx = srs.max_response(self.curve)
        self.assertGreaterEqual(mx["freq_hz"], 60.0)
        self.assertLessEqual(mx["freq_hz"], 100.0)
        self.assertLess(abs(mx["peak_g"] - 16.5) / 16.5, 0.10)
        self.assertAlmostEqual(mx["peak_g"], P80_G, places=5)
        self.assertAlmostEqual(mx["peak_ms2"], P80_MS2, places=3)

    def test_1000hz_anchor_and_deterministic_value(self):
        # High-frequency asymptote approaches the input amplitude.
        g = curve_entry(self.curve, 1000.0)["peak_g"]
        self.assertLess(abs(g - 10.1) / 10.1, 0.10)
        self.assertAlmostEqual(g, P1000_G, places=5)
        self.assertAlmostEqual(curve_entry(self.curve, 1000.0)["peak_ms2"],
                               P1000_MS2, places=4)

    def test_monotonic_20hz_below_80hz(self):
        g20 = curve_entry(self.curve, 20.0)["peak_g"]
        g80 = curve_entry(self.curve, 80.0)["peak_g"]
        self.assertLess(g20, g80)

    def test_monotonic_500hz_below_80hz(self):
        g500 = curve_entry(self.curve, 500.0)["peak_g"]
        g80 = curve_entry(self.curve, 80.0)["peak_g"]
        self.assertLess(g500, g80)

    def test_curve_is_deterministic(self):
        again = srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, GRID, Q)
        self.assertEqual([e["peak_ms2"] for e in self.curve],
                         [e["peak_ms2"] for e in again])

    def test_max_response_returns_peak_entry(self):
        mx = srs.max_response(self.curve)
        self.assertEqual(mx["peak_ms2"],
                         max(e["peak_ms2"] for e in self.curve))
        self.assertAlmostEqual(mx["peak_g"] * srs.G, mx["peak_ms2"],
                               places=6)

    def test_curve_entries_keys_and_g_units(self):
        for entry in self.curve:
            self.assertEqual(set(entry.keys()),
                             {"freq_hz", "peak_ms2", "peak_g"})
            self.assertAlmostEqual(entry["peak_g"] * srs.G,
                                   entry["peak_ms2"], places=6)
            self.assertGreater(entry["peak_ms2"], 0.0)

    def test_less_damping_raises_resonant_peak(self):
        # Q 5 (more damping) must amplify the 80 Hz region less than Q 10.
        q5 = srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, GRID, q=5.0)
        g80_q5 = curve_entry(q5, 80.0)["peak_g"]
        g80_q10 = curve_entry(self.curve, 80.0)["peak_g"]
        self.assertLess(g80_q5, g80_q10)
        # With less damping the maximum stays at 80 Hz on this grid.
        self.assertEqual(srs.max_response(q5)["freq_hz"], 80.0)

    def test_half_sine_sdof_peak_round_trip(self):
        # srs_curve at 1000 Hz equals a direct sdof_peak integration.
        wn = 2.0 * math.pi * 1000.0
        zeta = 1.0 / (2.0 * Q)
        dt = min(1.0 / (1000.0 * 50.0), PULSE_T / 200.0)
        peak = srs.sdof_peak(
            wn, zeta,
            lambda t: srs.base_accel(t, "half-sine", AMPLITUDE, PULSE_T,
                                     TAU),
            PULSE_T, dt)
        self.assertAlmostEqual(peak, P1000_MS2, places=3)


class DecayingSineTest(unittest.TestCase):
    """The decaying-sine 10 g, 10 ms, tau 30 ms, Q 10 contract."""

    @classmethod
    def setUpClass(cls):
        cls.curve = srs.srs_curve("decaying-sine", AMPLITUDE, PULSE_T,
                                  GRID, Q, decay_tau_s=TAU)

    def test_maximum_frequency_band_and_exact_value(self):
        # The decaying sine drives the 1/T = 100 Hz oscillator hardest.
        mx = srs.max_response(self.curve)
        self.assertGreaterEqual(mx["freq_hz"], 70.0)
        self.assertLessEqual(mx["freq_hz"], 130.0)
        self.assertEqual(mx["freq_hz"], 100.0)
        self.assertAlmostEqual(mx["peak_g"], D100_G, places=5)

    def test_peak_finite_and_positive(self):
        mx = srs.max_response(self.curve)
        self.assertTrue(math.isfinite(mx["peak_g"]))
        self.assertGreater(mx["peak_g"], 0.0)
        self.assertLess(mx["peak_g"], 1000.0)

    def test_resonant_buildup_exceeds_input_amplitude(self):
        # At resonance the decaying sine builds up well past the 10 g
        # input amplitude (Q 10 amplification over the decay tail).
        g100 = curve_entry(self.curve, 100.0)["peak_g"]
        self.assertGreater(g100, 2.0 * AMPLITUDE_G)

    def test_decaying_default_tau_is_three_times_pulse(self):
        defaulted = srs.srs_curve("decaying-sine", AMPLITUDE, PULSE_T,
                                  GRID, Q)
        explicit = srs.srs_curve("decaying-sine", AMPLITUDE, PULSE_T,
                                 GRID, Q, decay_tau_s=3.0 * PULSE_T)
        self.assertEqual([e["peak_ms2"] for e in defaulted],
                         [e["peak_ms2"] for e in explicit])

    def test_half_sine_unaffected_by_decay_tau_argument(self):
        with_tau = srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, GRID, Q,
                                 decay_tau_s=TAU)
        without = srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, GRID, Q)
        self.assertEqual([e["peak_ms2"] for e in with_tau],
                         [e["peak_ms2"] for e in without])


class ValidationTest(unittest.TestCase):
    """ValueError rejection of non-physical inputs."""

    def test_nonpositive_amplitude_raises(self):
        for bad_a in (0.0, -1.0, -98.0):
            with self.assertRaises(ValueError):
                srs.srs_curve("half-sine", bad_a, PULSE_T, GRID, Q)

    def test_nonpositive_pulse_duration_raises(self):
        for bad_t in (0.0, -0.01):
            with self.assertRaises(ValueError):
                srs.srs_curve("half-sine", AMPLITUDE, bad_t, GRID, Q)

    def test_quality_factor_below_half_raises(self):
        for bad_q in (0.2, 0.5):
            with self.assertRaises(ValueError):
                srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, GRID, bad_q)

    def test_empty_grid_raises(self):
        with self.assertRaises(ValueError):
            srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, [], Q)

    def test_nonpositive_grid_frequency_raises(self):
        for bad_grid in ([5.0, -3.0], [0.0]):
            with self.assertRaises(ValueError):
                srs.srs_curve("half-sine", AMPLITUDE, PULSE_T, bad_grid, Q)

    def test_unknown_pulse_type_raises(self):
        with self.assertRaises(ValueError):
            srs.srs_curve("triangular", AMPLITUDE, PULSE_T, GRID, Q)

    def test_decaying_zero_tau_raises(self):
        with self.assertRaises(ValueError):
            srs.srs_curve("decaying-sine", AMPLITUDE, PULSE_T, GRID, Q,
                          decay_tau_s=0.0)

    def test_sdof_peak_invalid_arguments_raise(self):
        for bad_wn in (0.0, -5.0):
            with self.assertRaises(ValueError):
                srs.sdof_peak(bad_wn, 0.05, lambda t: 0.0, 1.0, 1e-3)
        for bad_zeta in (0.0, 1.0, 1.5, -0.1):
            with self.assertRaises(ValueError):
                srs.sdof_peak(10.0, bad_zeta, lambda t: 0.0, 1.0, 1e-3)
        for bad_time in (0.0, -1.0):
            with self.assertRaises(ValueError):
                srs.sdof_peak(10.0, 0.05, lambda t: 0.0, bad_time, 1e-3)
        for bad_dt in (0.0, -1e-4):
            with self.assertRaises(ValueError):
                srs.sdof_peak(10.0, 0.05, lambda t: 0.0, 1.0, bad_dt)

    def test_max_response_empty_curve_raises(self):
        with self.assertRaises(ValueError):
            srs.max_response([])


if __name__ == "__main__":
    unittest.main()

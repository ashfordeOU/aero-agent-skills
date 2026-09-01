#!/usr/bin/env python3
"""Gate 3 contract test: structural coupling test (flight-test-operations).

Exercises scripts/structural_coupling_test_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - gain margin and
phase margin from the measured amplitude and phase response, the
PASS/FAIL margin verdict against the 6 dB and 45 degree criteria,
frequency response interpolation and crossing detection helpers, the
response-derived margin helpers, and the excitation frequency sweep
planning helper; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import structural_coupling_test_logic as sct  # noqa: E402


class GainMarginTest(unittest.TestCase):
    def test_anchor_gain_margin(self):
        self.assertAlmostEqual(sct.gain_margin(-9.0), 9.0)

    def test_margin_equal_to_criterion(self):
        self.assertAlmostEqual(sct.gain_margin(-6.0), 6.0)

    def test_positive_amplitude_gives_negative_margin(self):
        self.assertAlmostEqual(sct.gain_margin(3.0), -3.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sct.gain_margin(None)
        with self.assertRaises(ValueError):
            sct.gain_margin("abc")
        with self.assertRaises(ValueError):
            sct.gain_margin(float("nan"))
        with self.assertRaises(ValueError):
            sct.gain_margin(float("inf"))


class PhaseMarginTest(unittest.TestCase):
    def test_anchor_phase_margin(self):
        self.assertAlmostEqual(sct.phase_margin(-135.0), 45.0)

    def test_at_negative_one_eighty(self):
        self.assertAlmostEqual(sct.phase_margin(-180.0), 0.0)

    def test_negative_margin(self):
        self.assertAlmostEqual(sct.phase_margin(-200.0), -20.0)

    def test_leading_phase(self):
        self.assertAlmostEqual(sct.phase_margin(-90.0), 90.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sct.phase_margin(None)
        with self.assertRaises(ValueError):
            sct.phase_margin("abc")
        with self.assertRaises(ValueError):
            sct.phase_margin(float("inf"))


class MarginVerdictTest(unittest.TestCase):
    def test_pass_both_margins_met(self):
        v = sct.margin_verdict(9.0, 50.0)
        self.assertEqual(v["verdict"], "PASS")
        self.assertAlmostEqual(v["gain_margin_db"], 9.0)
        self.assertAlmostEqual(v["phase_margin_deg"], 50.0)

    def test_pass_exactly_at_criteria(self):
        v = sct.margin_verdict(6.0, 45.0)
        self.assertEqual(v["verdict"], "PASS")

    def test_fail_gain_short(self):
        self.assertEqual(sct.margin_verdict(5.9, 50.0)["verdict"], "FAIL")

    def test_fail_phase_short(self):
        self.assertEqual(sct.margin_verdict(9.0, 44.9)["verdict"], "FAIL")

    def test_fail_both_short(self):
        v = sct.margin_verdict(-3.0, -20.0)
        self.assertEqual(v["verdict"], "FAIL")
        self.assertAlmostEqual(v["gain_margin_db"], -3.0)
        self.assertAlmostEqual(v["phase_margin_deg"], -20.0)

    def test_custom_limits(self):
        v = sct.margin_verdict(9.0, 50.0, 8.0, 40.0)
        self.assertEqual(v["verdict"], "PASS")
        self.assertAlmostEqual(v["gain_limit_db"], 8.0)
        self.assertAlmostEqual(v["phase_limit_deg"], 40.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sct.margin_verdict(None, 50.0)
        with self.assertRaises(ValueError):
            sct.margin_verdict(9.0, 50.0, 0.0, 45.0)
        with self.assertRaises(ValueError):
            sct.margin_verdict(9.0, 50.0, 6.0, -1.0)
        with self.assertRaises(ValueError):
            sct.margin_verdict(9.0, "abc", 6.0, 45.0)


class InterpolateResponseTest(unittest.TestCase):
    FREQS = [10.0, 20.0, 30.0]
    MAGS = [0.0, -10.0, -20.0]

    def test_anchor_interpolation(self):
        self.assertAlmostEqual(
            sct.interpolate_response(self.FREQS, self.MAGS, 25.0), -15.0
        )

    def test_lower_endpoint(self):
        self.assertAlmostEqual(
            sct.interpolate_response([10.0, 20.0], [0.0, -6.0], 10.0), 0.0
        )

    def test_upper_endpoint(self):
        self.assertAlmostEqual(
            sct.interpolate_response([10.0, 20.0], [0.0, -6.0], 20.0), -6.0
        )

    def test_exact_sample_point(self):
        self.assertAlmostEqual(
            sct.interpolate_response(self.FREQS, self.MAGS, 20.0), -10.0
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sct.interpolate_response(self.FREQS, self.MAGS, 9.9)
        with self.assertRaises(ValueError):
            sct.interpolate_response(self.FREQS, self.MAGS, 30.1)
        with self.assertRaises(ValueError):
            sct.interpolate_response([20.0, 10.0], [0.0, -6.0], 15.0)
        with self.assertRaises(ValueError):
            sct.interpolate_response([10.0, 10.0], [0.0, -6.0], 10.0)
        with self.assertRaises(ValueError):
            sct.interpolate_response([10.0], [0.0], 10.0)
        with self.assertRaises(ValueError):
            sct.interpolate_response([10.0, 20.0], [0.0], 15.0)
        with self.assertRaises(ValueError):
            sct.interpolate_response([0.0, 20.0], [0.0, -6.0], 10.0)
        with self.assertRaises(ValueError):
            sct.interpolate_response(self.FREQS, self.MAGS, float("nan"))


class CrossingFrequencyTest(unittest.TestCase):
    FREQS = [1.0, 2.0, 4.0]
    PHASE = [-100.0, -150.0, -200.0]

    def test_anchor_phase_crossing(self):
        f = sct.phase_crossing_frequency(self.FREQS, self.PHASE, -180.0)
        self.assertAlmostEqual(f, 3.2)

    def test_no_phase_crossing_returns_none(self):
        f = sct.phase_crossing_frequency([1.0, 2.0, 4.0], [-100.0, -150.0, -170.0])
        self.assertIsNone(f)

    def test_exact_phase_crossing_hit(self):
        f = sct.phase_crossing_frequency([1.0, 2.0], [-180.0, -190.0], -180.0)
        self.assertAlmostEqual(f, 1.0)

    def test_anchor_gain_crossing(self):
        f = sct.gain_crossing_frequency(self.FREQS, [3.0, 1.0, -2.0], 0.0)
        self.assertAlmostEqual(f, 2.6666666666666665)

    def test_gain_crossing_custom_target(self):
        f = sct.gain_crossing_frequency(self.FREQS, [3.0, 1.0, -2.0], 2.0)
        self.assertAlmostEqual(f, 1.5)

    def test_no_gain_crossing_returns_none(self):
        f = sct.gain_crossing_frequency(self.FREQS, [3.0, 2.0, 1.0], 0.0)
        self.assertIsNone(f)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sct.phase_crossing_frequency([1.0, 2.0], [-100.0], -180.0)
        with self.assertRaises(ValueError):
            sct.phase_crossing_frequency([2.0, 1.0], [-100.0, -150.0], -180.0)
        with self.assertRaises(ValueError):
            sct.gain_crossing_frequency([1.0, 2.0], [3.0, "abc"], 0.0)


class ResponseMarginTest(unittest.TestCase):
    FREQS = [1.0, 2.0, 4.0]
    MAGS = [-5.0, -8.0, -12.0]
    PHASE = [-100.0, -150.0, -200.0]

    def test_anchor_gain_margin_from_response(self):
        gm = sct.gain_margin_from_response(self.FREQS, self.MAGS, self.PHASE)
        self.assertAlmostEqual(gm, 10.4)

    def test_gain_margin_none_without_phase_crossing(self):
        gm = sct.gain_margin_from_response(
            self.FREQS, self.MAGS, [-100.0, -120.0, -140.0]
        )
        self.assertIsNone(gm)

    def test_anchor_phase_margin_from_response(self):
        pm = sct.phase_margin_from_response(
            self.FREQS, [5.0, 1.0, -2.0], [-100.0, -140.0, -170.0]
        )
        self.assertAlmostEqual(pm, 30.0)

    def test_phase_margin_none_without_gain_crossing(self):
        pm = sct.phase_margin_from_response(
            self.FREQS, [5.0, 3.0, 2.0], self.PHASE
        )
        self.assertIsNone(pm)


class ExcitationFrequenciesTest(unittest.TestCase):
    def test_anchor_one_decade_ten_per_decade(self):
        freqs = sct.excitation_frequencies(10.0, 100.0, 10.0)
        self.assertEqual(len(freqs), 11)
        self.assertAlmostEqual(freqs[0], 10.0)
        self.assertAlmostEqual(freqs[-1], 100.0)
        self.assertAlmostEqual(freqs[3], 10.0 * 10 ** (3 / 10.0), delta=0.01)
        self.assertTrue(all(freqs[i] < freqs[i + 1] for i in range(len(freqs) - 1)))

    def test_three_decades_five_per_decade(self):
        freqs = sct.excitation_frequencies(1.0, 1000.0, 5.0)
        self.assertEqual(len(freqs), 16)
        self.assertAlmostEqual(freqs[0], 1.0)
        self.assertAlmostEqual(freqs[-1], 1000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sct.excitation_frequencies(0.0, 100.0, 10.0)
        with self.assertRaises(ValueError):
            sct.excitation_frequencies(100.0, 10.0, 10.0)
        with self.assertRaises(ValueError):
            sct.excitation_frequencies(10.0, 100.0, 0.0)
        with self.assertRaises(ValueError):
            sct.excitation_frequencies(10.0, 100.0, -2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

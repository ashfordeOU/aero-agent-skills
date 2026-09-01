#!/usr/bin/env python3
"""Gate 3 contract test: Bode frequency-response design.

Exercises scripts/frequency_response_design_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3: magnitude and
phase of a transfer function at s = j*w, gain crossover and phase
crossover frequencies, gain margin and phase margin, the closed-loop
stability verdict from the margins, margin trends against gain K, and
ValueError on invalid inputs.

Worked anchors for the canonical plant G(s) = K/(s(s+1)(s+2)) with
num = [K], den = [1, 3, 2, 0]:
  at w = 1, K = 2:   |G| = 2/sqrt(10) ~= 0.63246, phase = -161.565 deg
  phase crossover:   w_pc = sqrt(2) ~= 1.41421356 rad/s
  K = 2:             gain margin 3.0 (9.5424 dB), phase margin 32.61 deg
  K = 6:             gain margin 0 dB, phase margin 0 deg (marginal)
  K = 8:             gain margin -2.50 dB (unstable)
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import frequency_response_design_logic as fr  # noqa: E402

K2_NUM = [2.0]
DEN = [1.0, 3.0, 2.0, 0.0]  # s^3 + 3s^2 + 2s + 0 = s(s+1)(s+2)


class FrequencyResponseTest(unittest.TestCase):
    def test_magnitude_anchor_w1(self):
        # |G(j*1)| = 2/sqrt(10) for G = 2/(s(s+1)(s+2))
        self.assertAlmostEqual(
            fr.magnitude(K2_NUM, DEN, 1.0), 2.0 / math.sqrt(10.0), delta=1e-9
        )

    def test_magnitude_db_anchor_w1(self):
        # 20*log10(2/sqrt(10)) = -3.9794 dB
        self.assertAlmostEqual(
            fr.magnitude_db(K2_NUM, DEN, 1.0), 20.0 * math.log10(2.0 / math.sqrt(10.0)),
            delta=1e-9,
        )

    def test_phase_anchor_w1(self):
        # phase = -90 - atan(1) - atan(0.5) = -161.565 deg
        expected = -90.0 - math.degrees(math.atan(1.0)) - math.degrees(math.atan(0.5))
        self.assertAlmostEqual(fr.phase_deg(K2_NUM, DEN, 1.0), expected, delta=1e-9)

    def test_frequency_response_dict_fields(self):
        r = fr.frequency_response(K2_NUM, DEN, 1.0)
        self.assertEqual(r["omega"], 1.0)
        self.assertAlmostEqual(r["magnitude"], 2.0 / math.sqrt(10.0), delta=1e-9)
        self.assertAlmostEqual(r["magnitude_db"], -3.9794, delta=1e-3)
        self.assertAlmostEqual(r["phase_deg"], -161.565, delta=1e-3)

    def test_magnitude_falls_with_frequency(self):
        # Monotone fall of |G| for the canonical type-1 plant
        m1 = fr.magnitude(K2_NUM, DEN, 0.5)
        m2 = fr.magnitude(K2_NUM, DEN, 1.0)
        m3 = fr.magnitude(K2_NUM, DEN, 5.0)
        self.assertGreater(m1, m2)
        self.assertGreater(m2, m3)


class CrossoverFrequencyTest(unittest.TestCase):
    def test_phase_crossover_anchor_sqrt2(self):
        # atan(w) + atan(w/2) = 90 deg -> w^2/2 = 1 -> w = sqrt(2)
        self.assertAlmostEqual(
            fr.phase_crossover_frequency(K2_NUM, DEN), math.sqrt(2.0), delta=1e-6
        )

    def test_gain_crossover_anchor(self):
        # K = 2: u^3 + 5u^2 + 4u = 4 with u = w^2 -> w ~= 0.74935 rad/s
        w = fr.gain_crossover_frequency(K2_NUM, DEN)
        self.assertGreater(w, 0.74)
        self.assertLess(w, 0.76)
        # Definition check: |G(j*w_gc)| = 1 exactly at the returned point
        self.assertAlmostEqual(fr.magnitude(K2_NUM, DEN, w), 1.0, delta=1e-6)

    def test_gain_crossover_coincides_at_marginal_gain(self):
        # K = 6: gain crossover meets phase crossover at w = sqrt(2)
        w = fr.gain_crossover_frequency([6.0], DEN)
        self.assertAlmostEqual(w, math.sqrt(2.0), delta=1e-6)


class MarginsTest(unittest.TestCase):
    def test_gain_margin_anchor_k2(self):
        # |G(j*sqrt(2))| = K/6 = 1/3 -> gain margin 3.0 = 9.5424 dB
        m = fr.margins(K2_NUM, DEN)
        self.assertAlmostEqual(m["gain_margin"], 3.0, delta=1e-6)
        self.assertAlmostEqual(m["gain_margin_db"], 20.0 * math.log10(3.0), delta=1e-6)
        self.assertTrue(m["gain_margin_ok"])

    def test_phase_margin_anchor_k2(self):
        # PM = 180 + phase(w_gc), phase(w_gc) ~= -147.39 deg -> ~32.6 deg
        m = fr.margins(K2_NUM, DEN)
        self.assertGreater(m["phase_margin"], 32.0)
        self.assertLess(m["phase_margin"], 33.5)
        self.assertTrue(m["phase_margin_ok"])

    def test_margins_monotone_trend_with_gain(self):
        # Raising K lowers gain margin and phase margin monotonically
        dbs = []
        pms = []
        for K in (1.0, 2.0, 6.0, 8.0):
            m = fr.margins([K], DEN)
            dbs.append(m["gain_margin_db"])
            pms.append(m["phase_margin"])
        for a, b in zip(dbs, dbs[1:]):
            self.assertLess(b, a)
        for a, b in zip(pms, pms[1:]):
            self.assertLess(b, a)

    def test_no_phase_crossover_reports_infinite_gain_margin(self):
        # G = 1/(s(s+2)): phase reaches -180 only at infinity
        m = fr.margins([1.0], [1.0, 2.0, 0.0])
        self.assertTrue(math.isinf(m["phase_crossover_frequency"]))
        self.assertTrue(math.isinf(m["gain_margin"]))
        self.assertTrue(math.isinf(m["gain_margin_db"]))


class StabilityVerdictTest(unittest.TestCase):
    def test_stable_k2(self):
        v = fr.stability_verdict(K2_NUM, DEN)
        self.assertTrue(v["stable"])
        self.assertAlmostEqual(v["gain_margin_db"], 9.5424, delta=1e-3)
        self.assertIn("stable", v["reason"])

    def test_stable_k1(self):
        self.assertTrue(fr.stability_verdict([1.0], DEN)["stable"])

    def test_marginal_k6_not_stable(self):
        # K = 6 is the ultimate gain: poles on the imaginary axis
        v = fr.stability_verdict([6.0], DEN)
        self.assertFalse(v["stable"])
        self.assertAlmostEqual(v["gain_margin_db"], 0.0, delta=1e-4)
        self.assertIn("marginal", v["reason"])

    def test_unstable_k8(self):
        v = fr.stability_verdict([8.0], DEN)
        self.assertFalse(v["stable"])
        self.assertLess(v["gain_margin_db"], 0.0)
        self.assertIn("unstable", v["reason"])

    def test_verdict_consistency_with_margins(self):
        # The verdict fields mirror the margins computation
        v = fr.stability_verdict(K2_NUM, DEN)
        m = fr.margins(K2_NUM, DEN)
        self.assertAlmostEqual(v["gain_margin_db"], m["gain_margin_db"], delta=1e-9)
        self.assertAlmostEqual(v["phase_margin"], m["phase_margin"], delta=1e-9)
        self.assertAlmostEqual(
            v["gain_crossover_frequency"], m["gain_crossover_frequency"], delta=1e-9
        )
        self.assertAlmostEqual(
            v["phase_crossover_frequency"], m["phase_crossover_frequency"], delta=1e-9
        )


class ValidationTest(unittest.TestCase):
    def test_empty_numerator_raises(self):
        with self.assertRaises(ValueError):
            fr.frequency_response([], DEN, 1.0)
        with self.assertRaises(ValueError):
            fr.margins([], DEN)

    def test_empty_denominator_raises(self):
        with self.assertRaises(ValueError):
            fr.frequency_response(K2_NUM, [], 1.0)
        with self.assertRaises(ValueError):
            fr.stability_verdict(K2_NUM, [])

    def test_zero_leading_coefficient_raises(self):
        with self.assertRaises(ValueError):
            fr.magnitude_db([0.0, 2.0], DEN, 1.0)

    def test_non_numeric_coefficient_raises(self):
        with self.assertRaises(ValueError):
            fr.frequency_response(["two"], DEN, 1.0)

    def test_negative_omega_raises(self):
        with self.assertRaises(ValueError):
            fr.frequency_response(K2_NUM, DEN, -1.0)

    def test_singular_at_origin_raises(self):
        # Type-1 plant has a pole at s = 0; G(j*0) is undefined
        with self.assertRaises(ValueError):
            fr.frequency_response(K2_NUM, DEN, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

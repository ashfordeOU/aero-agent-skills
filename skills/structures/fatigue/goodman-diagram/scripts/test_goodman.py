#!/usr/bin/env python3
"""Gate 3 contract test: mean-stress fatigue correction logic.

Exercises scripts/goodman_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - modified Goodman
Sa = Se * (1 - Sm / Sut), Gerber Sa = Se * (1 - (Sm / Sut)**2),
Soderberg Sa = Se * (1 - Sm / Sy), cycle conversion
Sm = (Smax + Smin) / 2 and Sa = (Smax - Smin) / 2, stress ratio
R = Smin / Smax, and the infinite-life verdict at a (Sm, Sa) design
point. Known case: Se = 200 MPa, Sut = 600 MPa, Sy = 450 MPa,
Sm = 100 MPa gives Goodman Sa = 200 * (1 - 1/6) = 166.666... MPa,
Gerber Sa = 200 * (1 - 1/36) = 194.444... MPa, Soderberg
Sa = 200 * (1 - 2/9) = 155.555... MPa.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import goodman_logic as gd  # noqa: E402

SE = 200.0  # MPa, endurance limit
SUT = 600.0  # MPa, ultimate strength
SY = 450.0  # MPa, yield strength
SM = 100.0  # MPa, mean stress

GOODMAN_EXPECTED = 1000.0 / 6.0  # 166.666...
GERBER_EXPECTED = 7000.0 / 36.0  # 194.444...
SODERBERG_EXPECTED = 1400.0 / 9.0  # 155.555...


class AllowableAmplitudeTest(unittest.TestCase):
    def test_goodman_known_case(self):
        # 200 * (1 - 100/600) = 200 * 5/6 = 166.666...
        got = gd.goodman_allowable(SE, SUT, SM)
        self.assertAlmostEqual(got, GOODMAN_EXPECTED, places=9)

    def test_gerber_known_case(self):
        # 200 * (1 - (100/600)**2) = 200 * 35/36 = 194.444...
        got = gd.gerber_allowable(SE, SUT, SM)
        self.assertAlmostEqual(got, GERBER_EXPECTED, places=9)

    def test_soderberg_known_case(self):
        # 200 * (1 - 100/450) = 200 * 7/9 = 155.555...
        got = gd.soderberg_allowable(SE, SUT, SY, SM)
        self.assertAlmostEqual(got, SODERBERG_EXPECTED, places=9)

    def test_criteria_order(self):
        # Same input: Soderberg most conservative, Gerber least.
        g = gd.goodman_allowable(SE, SUT, SM)
        ger = gd.gerber_allowable(SE, SUT, SM)
        sod = gd.soderberg_allowable(SE, SUT, SY, SM)
        self.assertLess(sod, g)
        self.assertLess(g, ger)

    def test_zero_mean_stress_equals_endurance_limit(self):
        # Fully reversed cycle (Sm = 0): every criterion returns Se.
        self.assertAlmostEqual(gd.goodman_allowable(SE, SUT, 0.0), SE, places=9)
        self.assertAlmostEqual(gd.gerber_allowable(SE, SUT, 0.0), SE, places=9)
        self.assertAlmostEqual(gd.soderberg_allowable(SE, SUT, SY, 0.0), SE, places=9)

    def test_non_positive_allowable_at_ultimate_intercept(self):
        # Sm = Sut: the Goodman line hits zero.
        got = gd.goodman_allowable(SE, SUT, SUT * 0.999999)
        self.assertGreater(got, 0.0)
        self.assertAlmostEqual(
            gd.goodman_allowable(SE, SUT, SUT), 0.0, places=9
        )

    def test_bad_allowables_raise(self):
        with self.assertRaises(ValueError):
            gd.goodman_allowable(-SE, SUT, SM)
        with self.assertRaises(ValueError):
            gd.gerber_allowable(SE, 0.0, SM)
        with self.assertRaises(ValueError):
            gd.soderberg_allowable(SE, SUT, -SY, SM)

    def test_negative_mean_raises(self):
        with self.assertRaises(ValueError):
            gd.goodman_allowable(SE, SUT, -10.0)


class CycleConversionTest(unittest.TestCase):
    def test_mean_and_amplitude(self):
        # Smax = 300, Smin = 100: Sm = 200, Sa = 100.
        sm, sa = gd.mean_and_amplitude(300.0, 100.0)
        self.assertAlmostEqual(sm, 200.0, places=9)
        self.assertAlmostEqual(sa, 100.0, places=9)

    def test_fully_reversed_cycle(self):
        # Smax = 100, Smin = -100: Sm = 0, Sa = 100, R = -1.
        sm, sa = gd.mean_and_amplitude(100.0, -100.0)
        self.assertAlmostEqual(sm, 0.0, places=9)
        self.assertAlmostEqual(sa, 100.0, places=9)
        self.assertAlmostEqual(gd.stress_ratio(100.0, -100.0), -1.0, places=9)

    def test_stress_ratio_known_case(self):
        # R = Smin / Smax = 100 / 300 = 1/3.
        self.assertAlmostEqual(gd.stress_ratio(300.0, 100.0), 1.0 / 3.0, places=9)

    def test_degenerate_cycle_raises(self):
        with self.assertRaises(ValueError):
            gd.mean_and_amplitude(50.0, 50.0)
        with self.assertRaises(ValueError):
            gd.stress_ratio(0.0, 5.0)


class InfiniteLifeCheckTest(unittest.TestCase):
    def test_pass_case(self):
        # Applied amplitude 100 below every allowable at Sm = 100.
        # Cycle extrema Smax = Sm + Sa = 200, Smin = Sm - Sa = 0, so
        # R = Smin / Smax = 0.
        report = gd.infinite_life_check(SE, SUT, SY, SM, 100.0)
        self.assertTrue(report["pass"])
        self.assertEqual(report["governing_criterion"], "soderberg")
        for criterion in ("goodman", "gerber", "soderberg"):
            self.assertTrue(report["criteria"][criterion]["pass"])
        self.assertAlmostEqual(report["stress_ratio"], 0.0, places=9)

    def test_fail_case(self):
        # Applied amplitude 160 exceeds the Soderberg allowable 155.56.
        report = gd.infinite_life_check(SE, SUT, SY, SM, 160.0)
        self.assertFalse(report["pass"])
        self.assertFalse(report["criteria"]["soderberg"]["pass"])
        self.assertTrue(report["criteria"]["goodman"]["pass"])
        self.assertTrue(report["criteria"]["gerber"]["pass"])
        self.assertEqual(report["governing_criterion"], "soderberg")

    def test_allowables_inside_report(self):
        report = gd.infinite_life_check(SE, SUT, SY, SM, 150.0)
        self.assertAlmostEqual(
            report["criteria"]["goodman"]["allowable_amplitude"],
            GOODMAN_EXPECTED,
            places=9,
        )
        self.assertAlmostEqual(
            report["criteria"]["gerber"]["allowable_amplitude"],
            GERBER_EXPECTED,
            places=9,
        )
        self.assertAlmostEqual(
            report["criteria"]["soderberg"]["allowable_amplitude"],
            SODERBERG_EXPECTED,
            places=9,
        )
        self.assertAlmostEqual(
            report["criteria"]["goodman"]["margin"], GOODMAN_EXPECTED - 150.0, places=9
        )

    def test_json_report_round_trip(self):
        report = gd.infinite_life_check(SE, SUT, SY, SM, 120.0)
        payload = gd.report_json(report)
        loaded = json.loads(payload)
        self.assertEqual(loaded["pass"], report["pass"])
        self.assertEqual(loaded["governing_criterion"], "soderberg")


class HaighDiagramTest(unittest.TestCase):
    def test_sample_points(self):
        sms = gd.haigh_diagram_sample(SE, SUT, SY, n=5)
        self.assertEqual(len(sms), 5)
        self.assertAlmostEqual(sms[0], 0.0, places=9)

    def test_points_align_with_allowables(self):
        sms = gd.haigh_diagram_sample(SE, SUT, SY, n=4)
        data = gd.haigh_diagram_points(SE, SUT, SY, sms)
        self.assertEqual(len(data["mean_stress"]), 4)
        for i, sm in enumerate(sms):
            self.assertAlmostEqual(
                data["goodman"][i], gd.goodman_allowable(SE, SUT, sm), places=9
            )
            self.assertAlmostEqual(
                data["gerber"][i], gd.gerber_allowable(SE, SUT, sm), places=9
            )
            self.assertAlmostEqual(
                data["soderberg"][i], gd.soderberg_allowable(SE, SUT, SY, sm), places=9
            )

    def test_few_sample_points_raise(self):
        with self.assertRaises(ValueError):
            gd.haigh_diagram_sample(SE, SUT, SY, n=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""Gate 3 contract test: creep and stress rupture of metallic materials.

Exercises scripts/creep_rupture_logic.py (stdlib unittest, offline).
Contract: Norton steady-state creep rate from stress and temperature,
the Larson-Miller parameter and rupture life, the Monkman-Grant rupture
life from the minimum creep rate, accumulated creep strain over the
service time, the time to a target creep strain, and the design margin
check against a required life with the governing verdict; every
non-physical input raises ValueError.

Anchors (default alloy, sigma = 300 MPa = 3.0e8 Pa, T = 873.15 K):
- eps_dot = 1.2698242552930268e-09 1/s
- LMP = 20689.272471682023
- t_r = 4954.282695382218 h (LMP route) and 4953.97580096727 h
  (Monkman-Grant route), agreeing within 0.1 percent
- t_1pct = 7875105.518198173 s = 2187.5293106106037 h
- 1000 h required: margin_rupture 3.954, margin_creep 1.188, governing
  creep, verdict PASS
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import creep_rupture_logic as cr  # noqa: E402

SIGMA = 3.0e8  # 300 MPa in Pa
T600 = 873.15  # 600 C in K
T650 = 923.15  # 650 C in K
HOUR_S = 3600.0


class WorkedExampleTest(unittest.TestCase):
    def test_anchor_creep_rate(self):
        rate = cr.norton_creep_rate(SIGMA, T600)
        self.assertAlmostEqual(rate, 1.2698242552930268e-09, places=14)

    def test_anchor_larson_miller_parameter(self):
        self.assertAlmostEqual(cr.larson_miller_parameter(SIGMA), 20689.272471682023, places=4)

    def test_anchor_rupture_life_hours(self):
        self.assertAlmostEqual(cr.rupture_life_hours(SIGMA, T600), 4954.282695382218, places=3)

    def test_anchor_time_to_one_percent(self):
        rate = cr.norton_creep_rate(SIGMA, T600)
        self.assertAlmostEqual(cr.time_to_creep_strain(0.01, rate), 7875105.518198173, places=1)
        self.assertAlmostEqual(cr.time_to_creep_strain(0.01, rate) / HOUR_S,
                               2187.5293106106037, places=3)

    def test_anchor_monkman_grant_matches_lmp(self):
        # The two rupture-life routes agree within 0.1 percent by
        # construction of the reference typicals.
        rate = cr.norton_creep_rate(SIGMA, T600)
        mg = cr.monkman_grant_life(rate)
        lmp_life = cr.rupture_life_hours(SIGMA, T600)
        self.assertAlmostEqual(mg / lmp_life, 1.0, delta=0.001)

    def test_anchor_accumulated_strain_1000h(self):
        rate = cr.norton_creep_rate(SIGMA, T600)
        self.assertAlmostEqual(cr.creep_strain_accumulated(rate, 1000.0 * HOUR_S),
                               0.004571367319054896, places=8)

    def test_anchor_margin_1000h(self):
        m = cr.creep_margin(1000.0 * HOUR_S, SIGMA, T600)
        self.assertAlmostEqual(m["margin_rupture"], 3.9542826953822177, places=3)
        self.assertAlmostEqual(m["margin_creep"], 1.1875293106106035, places=3)
        self.assertEqual(m["governing"], "creep")
        self.assertEqual(m["verdict"], "PASS")


class NortonCreepRateTest(unittest.TestCase):
    def test_rate_rises_with_stress(self):
        rates = [cr.norton_creep_rate(s * 1.0e6, T600) for s in (100.0, 200.0, 300.0, 400.0, 500.0)]
        for lo, hi in zip(rates, rates[1:]):
            self.assertLess(lo, hi)

    def test_rate_rises_with_temperature(self):
        cold = cr.norton_creep_rate(SIGMA, 823.15)
        hot = cr.norton_creep_rate(SIGMA, T650)
        self.assertGreater(hot, cold)

    def test_custom_material_dict_overrides_a(self):
        # Halving A halves the rate at fixed n, Q.
        base = cr.norton_creep_rate(SIGMA, T600)
        half = cr.norton_creep_rate(SIGMA, T600, {"norton_a": 1.0e-47})
        self.assertAlmostEqual(half / base, 0.5, places=12)

    def test_valueerror_nonpositive_stress(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cr.norton_creep_rate(bad, T600)

    def test_valueerror_nonpositive_temperature(self):
        for bad in (0.0, -273.0):
            with self.assertRaises(ValueError):
                cr.norton_creep_rate(SIGMA, bad)

    def test_valueerror_unknown_material(self):
        with self.assertRaises(ValueError):
            cr.norton_creep_rate(SIGMA, T600, "titanium-6al-4v")

    def test_valueerror_negative_stress_exponent(self):
        with self.assertRaises(ValueError):
            cr.norton_creep_rate(SIGMA, T600, {"norton_n": -1.0})


class LarsonMillerTest(unittest.TestCase):
    def test_lmp_falls_as_stress_rises(self):
        lmps = [cr.larson_miller_parameter(s * 1.0e6) for s in (100.0, 200.0, 300.0, 400.0, 500.0)]
        for lo, hi in zip(lmps, lmps[1:]):
            self.assertGreater(lo, hi)

    def test_valueerror_nonpositive_stress(self):
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                cr.larson_miller_parameter(bad)


class RuptureLifeTest(unittest.TestCase):
    def test_life_falls_as_stress_rises(self):
        lives = [cr.rupture_life_hours(s * 1.0e6, T600)
                 for s in (100.0, 200.0, 300.0, 400.0, 500.0)]
        for lo, hi in zip(lives, lives[1:]):
            self.assertGreater(lo, hi)

    def test_life_falls_as_temperature_rises(self):
        cool = cr.rupture_life_hours(SIGMA, 823.15)
        hot = cr.rupture_life_hours(SIGMA, T650)
        self.assertGreater(cool, hot)

    def test_roundtrip_rupture_life_from_lmp(self):
        # t_r from LMP is exactly 10 ** (LMP / T - C).
        lmp = cr.larson_miller_parameter(SIGMA)
        expected = 10.0 ** (lmp / T600 - 20.0)
        self.assertAlmostEqual(cr.rupture_life_from_lmp(lmp, T600, 20.0), expected, places=10)

    def test_valueerror_rupture_life_from_lmp(self):
        lmp = cr.larson_miller_parameter(SIGMA)
        for bad_temp in (0.0, -10.0):
            with self.assertRaises(ValueError):
                cr.rupture_life_from_lmp(lmp, bad_temp, 20.0)
        with self.assertRaises(ValueError):
            cr.rupture_life_from_lmp(lmp, T600, 0.0)
        with self.assertRaises(ValueError):
            cr.rupture_life_from_lmp(lmp, T600, -5.0)

    def test_valueerror_rupture_life_inputs(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                cr.rupture_life_hours(bad, T600)
            with self.assertRaises(ValueError):
                cr.rupture_life_hours(SIGMA, bad)


class MonkmanGrantTest(unittest.TestCase):
    def test_mg_life_falls_as_rate_rises(self):
        lives = [cr.monkman_grant_life(r) for r in (1.0e-12, 1.0e-11, 1.0e-10, 1.0e-9, 1.0e-8)]
        for lo, hi in zip(lives, lives[1:]):
            self.assertGreater(lo, hi)

    def test_mg_matches_log_formula(self):
        # log10(t_r) + m * log10(eps_per_hour) = C_mg by construction.
        rate = 1.0e-9
        life = cr.monkman_grant_life(rate)
        residual = math_log10(life) + 1.0 * math_log10(rate * 3600.0)
        self.assertAlmostEqual(residual, -1.645, places=6)

    def test_valueerror_nonpositive_rate(self):
        for bad in (0.0, -1.0e-9):
            with self.assertRaises(ValueError):
                cr.monkman_grant_life(bad)


class AccumulatedStrainTest(unittest.TestCase):
    def test_strain_linear_in_time(self):
        rate = 1.0e-9
        t1 = cr.creep_strain_accumulated(rate, 1000.0)
        t2 = cr.creep_strain_accumulated(rate, 2000.0)
        self.assertAlmostEqual(t2, 2.0 * t1, places=12)

    def test_zero_time_zero_strain(self):
        self.assertEqual(cr.creep_strain_accumulated(1.0e-9, 0.0), 0.0)

    def test_valueerror_inputs(self):
        with self.assertRaises(ValueError):
            cr.creep_strain_accumulated(0.0, 100.0)
        with self.assertRaises(ValueError):
            cr.creep_strain_accumulated(-1.0e-9, 100.0)
        with self.assertRaises(ValueError):
            cr.creep_strain_accumulated(1.0e-9, -5.0)


class TimeToStrainTest(unittest.TestCase):
    def test_time_inversely_proportional_to_rate(self):
        t_fast = cr.time_to_creep_strain(0.01, 2.0e-9)
        t_slow = cr.time_to_creep_strain(0.01, 1.0e-9)
        self.assertAlmostEqual(t_fast * 2.0, t_slow, places=6)

    def test_valueerror_inputs(self):
        with self.assertRaises(ValueError):
            cr.time_to_creep_strain(0.0, 1.0e-9)
        with self.assertRaises(ValueError):
            cr.time_to_creep_strain(-0.01, 1.0e-9)
        with self.assertRaises(ValueError):
            cr.time_to_creep_strain(0.01, 0.0)
        with self.assertRaises(ValueError):
            cr.time_to_creep_strain(0.01, -1.0e-9)


class CreepMarginTest(unittest.TestCase):
    def test_fail_when_required_life_exceeds_rupture(self):
        m = cr.creep_margin(20000.0 * HOUR_S, SIGMA, T600)
        self.assertEqual(m["verdict"], "FAIL")
        self.assertEqual(m["governing"], "creep")
        self.assertLess(m["margin_rupture"], 0.0)
        self.assertLess(m["margin_creep"], 0.0)

    def test_fail_at_650c_1000h(self):
        # Hotter operating point shortens both the 1 percent strain time
        # and the rupture life well below the required life.
        m = cr.creep_margin(1000.0 * HOUR_S, SIGMA, T650)
        self.assertEqual(m["verdict"], "FAIL")
        self.assertLess(m["rupture_life_h"], 1000.0)
        self.assertLess(m["time_to_1pct_h"], 1000.0)

    def test_low_stress_governing_creep_pass(self):
        m = cr.creep_margin(1000.0 * HOUR_S, 1.5e8, T600)
        self.assertEqual(m["verdict"], "PASS")
        # Time to 1 percent strain is reached well before rupture, so
        # the creep margin governs.
        self.assertEqual(m["governing"], "creep")
        self.assertLess(m["margin_creep"], m["margin_rupture"])

    def test_rupture_governs_with_short_life_material(self):
        # A material master curve with a lower lm_a gives a rupture life
        # shorter than the time to 1 percent strain: rupture governs.
        m = cr.creep_margin(1000.0 * HOUR_S, SIGMA, T600, {"lm_a": 34700.0})
        self.assertEqual(m["governing"], "rupture")
        self.assertLess(m["rupture_life_h"], m["time_to_1pct_h"])

    def test_valueerror_inputs(self):
        with self.assertRaises(ValueError):
            cr.creep_margin(0.0, SIGMA, T600)
        with self.assertRaises(ValueError):
            cr.creep_margin(1000.0, -1.0, T600)
        with self.assertRaises(ValueError):
            cr.creep_margin(1000.0, SIGMA, 0.0)
        with self.assertRaises(ValueError):
            cr.creep_margin(1000.0, SIGMA, T600, "not-a-material")


def math_log10(x):
    import math
    return math.log10(x)


if __name__ == "__main__":
    unittest.main(verbosity=2)

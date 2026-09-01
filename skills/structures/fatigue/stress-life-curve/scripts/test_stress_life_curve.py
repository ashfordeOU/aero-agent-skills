#!/usr/bin/env python3
"""Gate 3 contract test: stress-life (S-N) fatigue analysis logic.

Exercises scripts/stress_life_curve_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - Basquin
S = A * N**b, life prediction N = (S / A)**(1 / b), log-log least
squares fit of (N, S) test points, endurance limit at the runout
threshold Se = A * runout_cycles**b, and the highest runout stress
level read off test data. Known anchors: A = 1000 MPa, b = -0.1
gives S(1e5) = 316.227766..., S(1e7) = 199.526231..., life at
S = 300 MPa of 169350.9... cycles, and Se = 199.526231... MPa at a
1e7-cycle runout threshold.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stress_life_curve_logic as slc  # noqa: E402

A = 1000.0  # MPa, fatigue strength coefficient (stress at N = 1)
B = -0.1  # fatigue strength exponent


class BasquinStressTest(unittest.TestCase):
    def test_stress_at_1e5_cycles_anchor(self):
        # 1000 * 1e5**-0.1 = 1000 / sqrt(10) = 316.227766...
        got = slc.basquin_stress(A, B, 1e5)
        self.assertAlmostEqual(got, 316.2277660168379, places=9)

    def test_stress_at_1e4_cycles_anchor(self):
        # 1000 * 1e4**-0.1 = 1000 / 10**0.4 = 398.107...
        got = slc.basquin_stress(A, B, 1e4)
        self.assertAlmostEqual(got, 398.1071705534972, places=9)

    def test_stress_monotone_decreasing_with_life(self):
        # b < 0: longer life allows only lower stress amplitude.
        self.assertGreater(slc.basquin_stress(A, B, 1e5),
                           slc.basquin_stress(A, B, 1e6))
        self.assertGreater(slc.basquin_stress(A, B, 1e6),
                           slc.basquin_stress(A, B, 1e7))

    def test_stress_value_error_negative_life(self):
        with self.assertRaises(ValueError):
            slc.basquin_stress(A, B, -1.0)

    def test_stress_value_error_nonpositive_coefficient(self):
        with self.assertRaises(ValueError):
            slc.basquin_stress(0.0, B, 1e5)


class BasquinLifeTest(unittest.TestCase):
    def test_life_at_300_mpa_anchor(self):
        # (300 / 1000)**(1 / -0.1) = 0.3**-10 = 169350.878...
        got = slc.basquin_life(A, B, 300.0)
        self.assertAlmostEqual(got, 169350.87808430294, places=6)

    def test_life_round_trip_with_stress(self):
        # Life at the stress the curve assigns to N = 1e5 recovers 1e5.
        s = slc.basquin_stress(A, B, 1e5)
        self.assertAlmostEqual(slc.basquin_life(A, B, s), 1e5, places=6)

    def test_life_grows_as_stress_drops(self):
        # Trend property: lower amplitude, longer life.
        low = slc.basquin_life(A, B, 300.0)
        high = slc.basquin_life(A, B, 400.0)
        self.assertGreater(low, high)

    def test_life_value_error_nonpositive_stress(self):
        with self.assertRaises(ValueError):
            slc.basquin_life(A, B, 0.0)

    def test_life_value_error_zero_exponent(self):
        with self.assertRaises(ValueError):
            slc.basquin_life(A, 0.0, 300.0)


class FitBasquinTest(unittest.TestCase):
    def test_fit_recovers_generating_curve_exact_points(self):
        # Three exact points on A = 1000, b = -0.1.
        points = [(1e3, 501.1872336272722),
                  (1e4, 398.1071705534972),
                  (1e5, 316.2277660168379)]
        a_fit, b_fit = slc.fit_basquin(points)
        self.assertAlmostEqual(a_fit, A, places=6)
        self.assertAlmostEqual(b_fit, B, places=9)

    def test_fit_scattered_data_approximates_line(self):
        # Small scatter around the generating line still recovers it.
        points = [(1e3, 501.2), (1e4, 397.5), (1e5, 317.1),
                  (5e5, 268.0), (2e6, 234.0)]
        a_fit, b_fit = slc.fit_basquin(points)
        self.assertAlmostEqual(a_fit, A, delta=40.0)
        self.assertAlmostEqual(b_fit, B, delta=0.02)

    def test_fit_requires_two_points(self):
        with self.assertRaises(ValueError):
            slc.fit_basquin([(1e4, 398.1)])

    def test_fit_rejects_nonpositive_stress(self):
        with self.assertRaises(ValueError):
            slc.fit_basquin([(1e3, 501.2), (1e4, -10.0)])

    def test_fit_rejects_identical_lives(self):
        with self.assertRaises(ValueError):
            slc.fit_basquin([(1e4, 398.1), (1e4, 316.2)])


class EnduranceLimitTest(unittest.TestCase):
    def test_endurance_limit_anchor_at_1e7_runout(self):
        # Se = 1000 * 1e7**-0.1 = 199.526231...
        got = slc.endurance_limit(A, B, 1e7)
        self.assertAlmostEqual(got, 199.52623149688797, places=9)

    def test_endurance_limit_higher_for_shorter_runout(self):
        # A shorter runout threshold admits a higher stress.
        self.assertGreater(slc.endurance_limit(A, B, 1e6),
                           slc.endurance_limit(A, B, 1e7))

    def test_endurance_limit_value_error_nonpositive_runout(self):
        with self.assertRaises(ValueError):
            slc.endurance_limit(A, B, 0.0)

    def test_runout_stress_level_reads_off_data(self):
        # Highest stress whose test life reached the 1e7 threshold.
        data = [(1e5, 316.2), (1e6, 251.2), (1e7, 199.5), (2e7, 199.5)]
        self.assertAlmostEqual(slc.runout_stress_level(data, 1e7), 199.5,
                               places=9)

    def test_runout_stress_level_no_runout_raises(self):
        # No point reached 1e7 cycles: no endurance limit is defined.
        data = [(1e4, 398.1), (1e5, 316.2), (1e6, 251.2)]
        with self.assertRaises(ValueError):
            slc.runout_stress_level(data, 1e7)

    def test_runout_stress_level_value_error_bad_threshold(self):
        with self.assertRaises(ValueError):
            slc.runout_stress_level([(1e7, 199.5)], -1e7)


if __name__ == "__main__":
    unittest.main()

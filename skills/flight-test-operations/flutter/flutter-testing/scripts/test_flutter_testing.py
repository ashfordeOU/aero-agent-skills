#!/usr/bin/env python3
"""Gate 3 contract test: flutter testing.

Exercises scripts/flutter_testing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the required flutter
speed is V_F_required = margin_factor * V_D (default 1.2); the
flutter speed comes from the linear least squares fit of damping
versus test speed extrapolated to the zero crossing; the frequency
separation check is |f1 - f2| / mean >= min_frac (default 0.10);
the flutter margin ratio is V_F_measured / V_D passing at >= 1.2 per
the FAR 25.629 context; the damping margin passes when the damping
at the maximum test speed stays >= 0.03. Invalid inputs raise
ValueError.

Hand-computed values:
- V_D = 200 -> V_F_required = 1.2 * 200 = 240.0 m/s; V_D = 180 with
  margin factor 1.15 -> 207.0 m/s.
- speeds [100, 110, 120, 130], dampings [0.08, 0.05, 0.02, -0.01]:
  n = 4, sum_x = 460, sum_y = 0.14, sum_xx = 53400,
  sum_xy = 14.6; denom = 4*53400 - 460^2 = 2000;
  m = (4*14.6 - 460*0.14)/2000 = -6/2000 = -0.003;
  b = (0.14 + 0.003*460)/4 = 1.52/4 = 0.38;
  V_F = -0.38 / -0.003 = 126.6667 m/s.
- speeds [200, 210, 220], dampings [0.06, 0.03, 0.0]:
  n = 3, sum_x = 630, sum_y = 0.09, sum_xx = 132500,
  sum_xy = 18.3; denom = 3*132500 - 630^2 = 600;
  m = (3*18.3 - 630*0.09)/600 = -1.8/600 = -0.003;
  b = (0.09 + 0.003*630)/3 = 1.98/3 = 0.66;
  V_F = -0.66 / -0.003 = 220.0 m/s.
- f1 = 10, f2 = 12: separation = 2/11 = 0.1818 >= 0.10 -> pass;
  f1 = 10, f2 = 11: separation = 1/10.5 = 0.09524 < 0.10 -> fail;
  f1 = 9.5, f2 = 10.5: separation = 1.0/10.0 = 0.10 exactly -> pass.
- V_F = 240, V_D = 200: ratio = 1.2 -> pass; V_F = 230: ratio = 1.15
  -> fail; V_F = 300: ratio = 1.5 -> pass.
- damping 0.05 vs min 0.03 -> pass; 0.03 -> pass (boundary);
  0.02 -> fail; -0.01 -> fail.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flutter_testing_logic as ftl  # noqa: E402


class RequiredFlutterSpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # V_D = 200 m/s -> V_F_required = 1.2 * 200 = 240.0 m/s
        self.assertAlmostEqual(ftl.required_flutter_speed(200), 240.0)
        # V_D = 180 m/s, margin factor 1.15 -> 207.0 m/s
        self.assertAlmostEqual(
            ftl.required_flutter_speed(180, margin_factor=1.15), 207.0
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftl.required_flutter_speed(0)
        with self.assertRaises(ValueError):
            ftl.required_flutter_speed(-50)
        with self.assertRaises(ValueError):
            ftl.required_flutter_speed(200, margin_factor=0)
        with self.assertRaises(ValueError):
            ftl.required_flutter_speed(200, margin_factor=-1.2)


class FlutterSpeedFromDampingTest(unittest.TestCase):
    def test_analytic_zero_crossing(self):
        # m = -0.003, b = 0.38 -> V_F = 126.6667 m/s
        v_f = ftl.flutter_speed_from_damping(
            [100, 110, 120, 130], [0.08, 0.05, 0.02, -0.01]
        )
        self.assertAlmostEqual(v_f, 126.66666666666667, places=4)

    def test_analytic_exact_point_on_trend(self):
        # m = -0.003, b = 0.66 -> V_F = 220.0 m/s (last point sits on
        # the zero crossing)
        v_f = ftl.flutter_speed_from_damping(
            [200, 210, 220], [0.06, 0.03, 0.0]
        )
        self.assertAlmostEqual(v_f, 220.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftl.flutter_speed_from_damping([], [])
        with self.assertRaises(ValueError):
            ftl.flutter_speed_from_damping([100, 110], [0.05])
        with self.assertRaises(ValueError):
            ftl.flutter_speed_from_damping([100], [0.05])
        with self.assertRaises(ValueError):
            ftl.flutter_speed_from_damping([100, 130, 120], [0.05, 0.02, 0.04])
        with self.assertRaises(ValueError):
            ftl.flutter_speed_from_damping([100, 110], [0.02, 0.04])


class FrequencySeparationTest(unittest.TestCase):
    def test_analytic_separated(self):
        # |12 - 10| / 11 = 0.18182 >= 0.10 -> pass
        out = ftl.frequency_separation(10, 12)
        self.assertAlmostEqual(out["separation"], 2.0 / 11.0, places=5)
        self.assertTrue(out["pass"])

    def test_analytic_coalescing(self):
        # |11 - 10| / 10.5 = 0.09524 < 0.10 -> fail (coalescence risk)
        out = ftl.frequency_separation(10, 11)
        self.assertAlmostEqual(out["separation"], 1.0 / 10.5, places=5)
        self.assertFalse(out["pass"])

    def test_analytic_boundary(self):
        # |10.5 - 9.5| / 10.0 = 0.10 exactly -> pass (>= min)
        out = ftl.frequency_separation(9.5, 10.5)
        self.assertAlmostEqual(out["separation"], 0.10, places=6)
        self.assertTrue(out["pass"])

    def test_stricter_minimum_fails(self):
        # separation 0.18182 < 0.20 -> fail under the stricter minimum
        out = ftl.frequency_separation(10, 12, min_frac=0.20)
        self.assertFalse(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftl.frequency_separation(0, 10)
        with self.assertRaises(ValueError):
            ftl.frequency_separation(10, -5)
        with self.assertRaises(ValueError):
            ftl.frequency_separation(10, 12, min_frac=0)
        with self.assertRaises(ValueError):
            ftl.frequency_separation(10, 12, min_frac=-0.1)


class FlutterMarginRatioTest(unittest.TestCase):
    def test_analytic_boundary_pass(self):
        # V_F = 240, V_D = 200 -> ratio 1.2 -> pass (>= 1.2)
        out = ftl.flutter_margin_ratio(240, 200)
        self.assertAlmostEqual(out["ratio"], 1.2)
        self.assertTrue(out["pass"])

    def test_analytic_below_margin_fails(self):
        # V_F = 230, V_D = 200 -> ratio 1.15 < 1.2 -> fail
        out = ftl.flutter_margin_ratio(230, 200)
        self.assertAlmostEqual(out["ratio"], 1.15)
        self.assertFalse(out["pass"])

    def test_analytic_comfortable_margin(self):
        # V_F = 300, V_D = 200 -> ratio 1.5 -> pass
        out = ftl.flutter_margin_ratio(300, 200)
        self.assertAlmostEqual(out["ratio"], 1.5)
        self.assertTrue(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftl.flutter_margin_ratio(240, 0)
        with self.assertRaises(ValueError):
            ftl.flutter_margin_ratio(-100, 200)
        with self.assertRaises(ValueError):
            ftl.flutter_margin_ratio(240, 200, required_ratio=0)


class DampingMarginTest(unittest.TestCase):
    def test_analytic_above_minimum(self):
        # damping 0.05 >= 0.03 -> pass
        out = ftl.damping_margin(0.05)
        self.assertTrue(out["pass"])

    def test_analytic_boundary(self):
        # damping 0.03 == minimum -> pass (>=)
        out = ftl.damping_margin(0.03)
        self.assertTrue(out["pass"])

    def test_analytic_below_minimum_fails(self):
        # damping 0.02 < 0.03 -> fail
        out = ftl.damping_margin(0.02)
        self.assertFalse(out["pass"])

    def test_negative_damping_fails(self):
        # negative damping means the mode already fluttered
        out = ftl.damping_margin(-0.01)
        self.assertFalse(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ftl.damping_margin(0.05, min_damping=0)
        with self.assertRaises(ValueError):
            ftl.damping_margin(0.05, min_damping=-0.03)


if __name__ == "__main__":
    unittest.main(verbosity=2)

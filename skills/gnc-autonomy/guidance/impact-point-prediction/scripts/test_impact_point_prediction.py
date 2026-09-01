#!/usr/bin/env python3
"""Gate 3 contract test: ballistic impact point prediction.

Exercises scripts/impact_point_prediction_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the flat earth
vacuum ballistic model: range R = v0^2 * sin(2*theta0) / g in m, time
of flight T = 2 * v0 * sin(theta0) / g in s, peak height
hp = (v0 * sin(theta0))^2 / (2*g) in m, impact coordinates from launch
position and heading, first-order range and time sensitivity to launch
condition errors, the bundled impact_point_prediction dict, and
ValueError on non-numeric or out-of-range inputs.

Analytic anchor (v0 = 100 m/s, theta0 = 45 deg, g = 9.81 m/s^2):
  R      = 10000 * sin(90 deg) / 9.81       = 1019.367991845056 m
  T      = 200 * sin(45 deg) / 9.81          = 14.416040391163 s
  hp     = 5000 / 19.62                      = 254.841997961264 m
  dR/dv0 = 200 / 9.81                        = 20.387359836901 m/(m/s)
  dR/dtheta0 = 20000 * cos(90 deg) / 9.81    = 0 m/rad
  dT/dv0 = 2 * sin(45 deg) / 9.81            = 0.144160403912 s/(m/s)
  delta_R (dv0 = 1 m/s)                      = 20.387359836901 m
  delta_T (dv0 = 1 m/s)                      = 0.144160403912 s
Asserted with places=4. Units: m, s, rad, m/s, m/s^2.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import impact_point_prediction_logic as ipp  # noqa: E402

G = 9.81
V0 = 100.0
TH45 = math.pi / 4.0
TH30 = math.pi / 6.0
TH60 = math.pi / 3.0

R45_REF = 1019.367991845056
T45_REF = 14.416040391163
H45_REF = 254.841997961264
DR_DV0_REF = 20.387359836901
DT_DV0_REF = 0.144160403912
IMP30_X_REF = 882.798576742547
IMP30_Y_REF = 509.683995922528


class RangeTest(unittest.TestCase):
    def test_analytic_anchor_45_deg(self):
        self.assertAlmostEqual(
            ipp.range_flat_earth(V0, TH45, G), R45_REF, places=4
        )

    def test_maximum_at_45_deg(self):
        best_angle = max(
            range(5, 90, 5),
            key=lambda a: ipp.range_flat_earth(V0, math.radians(a), G),
        )
        self.assertEqual(best_angle, 45)
        r40 = ipp.range_flat_earth(V0, math.radians(40), G)
        r45 = ipp.range_flat_earth(V0, TH45, G)
        r50 = ipp.range_flat_earth(V0, math.radians(50), G)
        self.assertGreater(r45, r40)
        self.assertGreater(r45, r50)

    def test_symmetric_about_45_deg(self):
        self.assertAlmostEqual(
            ipp.range_flat_earth(V0, TH30, G),
            ipp.range_flat_earth(V0, TH60, G),
            places=4,
        )

    def test_quadratic_in_speed(self):
        r100 = ipp.range_flat_earth(V0, TH45, G)
        r200 = ipp.range_flat_earth(200.0, TH45, G)
        self.assertAlmostEqual(r200 / r100, 4.0, places=4)

    def test_shallow_throw_matches_formula(self):
        small = 1e-3
        got = ipp.range_flat_earth(V0, small, G)
        want = V0 * V0 * math.sin(2.0 * small) / G
        self.assertAlmostEqual(got, want, places=6)

    def test_zero_speed_raises(self):
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(0.0, TH45, G)

    def test_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(-10.0, TH45, G)

    def test_zero_angle_raises(self):
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(V0, 0.0, G)

    def test_vertical_angle_raises(self):
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(V0, math.pi / 2.0, G)

    def test_negative_gravity_raises(self):
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(V0, TH45, -G)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            ipp.range_flat_earth("fast", TH45, G)
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(V0, "steep", G)
        with self.assertRaises(ValueError):
            ipp.range_flat_earth(V0, TH45, "heavy")


class TimeOfFlightTest(unittest.TestCase):
    def test_analytic_anchor_45_deg(self):
        self.assertAlmostEqual(ipp.time_of_flight(V0, TH45, G), T45_REF, places=4)

    def test_increases_with_angle(self):
        t30 = ipp.time_of_flight(V0, TH30, G)
        t45 = ipp.time_of_flight(V0, TH45, G)
        t60 = ipp.time_of_flight(V0, TH60, G)
        self.assertGreater(t45, t30)
        self.assertGreater(t60, t45)

    def test_linear_in_speed(self):
        t100 = ipp.time_of_flight(V0, TH45, G)
        t200 = ipp.time_of_flight(200.0, TH45, G)
        self.assertAlmostEqual(t200 / t100, 2.0, places=4)


class PeakHeightTest(unittest.TestCase):
    def test_analytic_anchor_45_deg(self):
        self.assertAlmostEqual(ipp.peak_height(V0, TH45, G), H45_REF, places=4)

    def test_scales_with_speed_squared(self):
        h100 = ipp.peak_height(V0, TH45, G)
        h200 = ipp.peak_height(200.0, TH45, G)
        self.assertAlmostEqual(h200 / h100, 4.0, places=4)


class ImpactPointTest(unittest.TestCase):
    def test_heading_zero_along_x(self):
        rng = ipp.range_flat_earth(V0, TH45, G)
        xf, yf = ipp.impact_point(0.0, 0.0, V0, TH45, 0.0, G)
        self.assertAlmostEqual(xf, rng, places=4)
        self.assertAlmostEqual(yf, 0.0, places=4)

    def test_heading_ninety_along_y(self):
        rng = ipp.range_flat_earth(V0, TH45, G)
        xf, yf = ipp.impact_point(0.0, 0.0, V0, TH45, math.pi / 2.0, G)
        self.assertAlmostEqual(xf, 0.0, places=4)
        self.assertAlmostEqual(yf, rng, places=4)

    def test_analytic_anchor_heading_30(self):
        xf, yf = ipp.impact_point(0.0, 0.0, V0, TH45, math.pi / 6.0, G)
        self.assertAlmostEqual(xf, IMP30_X_REF, places=4)
        self.assertAlmostEqual(yf, IMP30_Y_REF, places=4)

    def test_launch_offset_translates(self):
        xf0, yf0 = ipp.impact_point(0.0, 0.0, V0, TH45, math.pi / 6.0, G)
        xf, yf = ipp.impact_point(100.0, 50.0, V0, TH45, math.pi / 6.0, G)
        self.assertAlmostEqual(xf, xf0 + 100.0, places=4)
        self.assertAlmostEqual(yf, yf0 + 50.0, places=4)

    def test_non_numeric_heading_raises(self):
        with self.assertRaises(ValueError):
            ipp.impact_point(0.0, 0.0, V0, TH45, "north", G)


class RangeSensitivityTest(unittest.TestCase):
    def test_analytic_anchor_45_deg(self):
        s = ipp.range_sensitivity(V0, TH45, G)
        self.assertAlmostEqual(s["dR_dv0"], DR_DV0_REF, places=4)
        self.assertAlmostEqual(s["dR_dtheta0"], 0.0, places=4)

    def test_angle_sensitivity_positive_below_45(self):
        s = ipp.range_sensitivity(V0, TH30, G)
        self.assertGreater(s["dR_dtheta0"], 0.0)

    def test_angle_sensitivity_negative_above_45(self):
        s = ipp.range_sensitivity(V0, TH60, G)
        self.assertLess(s["dR_dtheta0"], 0.0)


class ImpactErrorTest(unittest.TestCase):
    def test_analytic_anchor_speed_error(self):
        e = ipp.impact_error(V0, TH45, 1.0, 0.0, G)
        self.assertAlmostEqual(e["delta_range"], DR_DV0_REF, places=4)
        self.assertAlmostEqual(e["delta_time"], DT_DV0_REF, places=4)

    def test_angle_error_zero_at_45_deg(self):
        e = ipp.impact_error(V0, TH45, 0.0, 0.01, G)
        self.assertAlmostEqual(e["delta_range"], 0.0, places=4)
        self.assertGreater(e["delta_time"], 0.0)

    def test_angle_error_at_30_deg(self):
        e = ipp.impact_error(V0, TH30, 0.0, 0.01, G)
        dR_dtheta0 = ipp.range_sensitivity(V0, TH30, G)["dR_dtheta0"]
        self.assertAlmostEqual(e["delta_range"], dR_dtheta0 * 0.01, places=4)

    def test_error_accumulates_linearly(self):
        e = ipp.impact_error(V0, TH30, 2.0, 0.005, G)
        self.assertAlmostEqual(
            e["delta_range"], e["dR_v0"] + e["dR_theta"], places=6
        )
        self.assertAlmostEqual(
            e["delta_time"], e["dT_v0"] + e["dT_theta"], places=6
        )

    def test_time_error_grows_with_angle(self):
        e30 = ipp.impact_error(V0, TH30, 1.0, 0.0, G)
        e60 = ipp.impact_error(V0, TH60, 1.0, 0.0, G)
        self.assertGreater(e60["delta_time"], e30["delta_time"])


class ImpactPointPredictionBundleTest(unittest.TestCase):
    def test_bundle_fields_match_individual_functions(self):
        b = ipp.impact_point_prediction(0.0, 0.0, V0, TH45, 0.0, G)
        self.assertAlmostEqual(b["range"], ipp.range_flat_earth(V0, TH45, G), places=4)
        self.assertAlmostEqual(
            b["time_of_flight"], ipp.time_of_flight(V0, TH45, G), places=4
        )
        self.assertAlmostEqual(b["peak_height"], ipp.peak_height(V0, TH45, G), places=4)
        xf, yf = ipp.impact_point(0.0, 0.0, V0, TH45, 0.0, G)
        self.assertAlmostEqual(b["impact_x"], xf, places=4)
        self.assertAlmostEqual(b["impact_y"], yf, places=4)
        self.assertEqual(b["v0"], V0)
        self.assertEqual(b["theta0"], TH45)
        self.assertEqual(b["g"], G)

    def test_bundle_keys(self):
        b = ipp.impact_point_prediction(0.0, 0.0, V0, TH45, 0.0, G)
        self.assertEqual(
            sorted(b.keys()),
            [
                "g",
                "heading",
                "impact_x",
                "impact_y",
                "peak_height",
                "range",
                "theta0",
                "time_of_flight",
                "v0",
            ],
        )

    def test_bundle_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ipp.impact_point_prediction(0.0, 0.0, -1.0, TH45, 0.0, G)


if __name__ == "__main__":
    unittest.main(verbosity=2)

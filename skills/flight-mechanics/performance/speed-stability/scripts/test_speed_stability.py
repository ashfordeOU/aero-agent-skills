"""Contract test for the speed-stability leaf (flight-mechanics/performance).

Offline deterministic stdlib unittest. Runs via:
    python3 scripts/test_speed_stability.py
and exits 0.

Approved wave-27 spec adaptation (ops correction, recorded here): the
analytic slope uses the exact derivative coefficient 4 on the induced
term, dT/dv = cd0 * rho * v * S - 4 * k * W**2 / (rho * v**3 * S), so
its zero coincides with the closed-form v_md; the worked example
asserts v_md within 0.01 of 110.17 m/s (exact module value
110.1675939), margin at 80 m/s of -30.17 m/s, verdicts unstable at
80 m/s and stable at 130 m/s. All other spec numbers stay as written.
"""

import math
import unittest

import speed_stability_logic as ssl

W = 600000.0          # aircraft weight, N
S = 120.0             # reference wing area, m^2
RHO = 1.225           # sea level air density, kg/m^3
CD0 = 0.02            # zero lift drag coefficient
E = 0.8               # Oswald span efficiency
AR = 9.0              # aspect ratio
K = 1.0 / (math.pi * E * AR)  # induced drag factor

V_MD = 110.16759391644432  # exact module closed form for the example


class TestInducedFactor(unittest.TestCase):
    def test_induced_factor_value(self):
        self.assertAlmostEqual(K, 0.04420970641441537, places=12)

    def test_induced_factor_matches_module(self):
        self.assertAlmostEqual(ssl._induced_factor(E, AR), K, places=15)


class TestMinDragSpeed(unittest.TestCase):
    def test_closed_form_exact(self):
        expected = math.sqrt(2.0 * W / (RHO * S)) * (K / CD0) ** 0.25
        got = ssl.min_drag_speed(W, S, RHO, CD0, K)
        self.assertAlmostEqual(got, expected, places=9)

    def test_worked_example_value(self):
        v_md = ssl.min_drag_speed(W, S, RHO, CD0, K)
        self.assertAlmostEqual(v_md, V_MD, places=9)
        self.assertLess(abs(v_md - 110.17), 0.01)

    def test_module_value_within_tolerance_of_110_17(self):
        v_md = ssl.min_drag_speed(W, S, RHO, CD0, K)
        self.assertAlmostEqual(v_md, 110.17, delta=0.01)


class TestDerivative(unittest.TestCase):
    def test_zero_of_derivative_on_vmd(self):
        slope = ssl.d_thrust_dv(V_MD, W, S, RHO, CD0, K)
        self.assertLess(abs(slope), 1e-6)

    def test_derivative_negative_on_back_side_at_80(self):
        self.assertLess(ssl.d_thrust_dv(80.0, W, S, RHO, CD0, K), 0.0)

    def test_derivative_positive_on_front_side_at_130(self):
        self.assertGreater(ssl.d_thrust_dv(130.0, W, S, RHO, CD0, K), 0.0)

    def test_derivative_finite_difference_at_80(self):
        h = 0.5
        analytic = ssl.d_thrust_dv(80.0, W, S, RHO, CD0, K)
        fd = (ssl.thrust_required(80.0 + h, W, S, RHO, CD0, K)
              - ssl.thrust_required(80.0 - h, W, S, RHO, CD0, K)) / (2.0 * h)
        self.assertAlmostEqual(fd, analytic, delta=abs(analytic) * 1e-3)

    def test_derivative_finite_difference_at_130(self):
        h = 0.5
        analytic = ssl.d_thrust_dv(130.0, W, S, RHO, CD0, K)
        fd = (ssl.thrust_required(130.0 + h, W, S, RHO, CD0, K)
              - ssl.thrust_required(130.0 - h, W, S, RHO, CD0, K)) / (2.0 * h)
        self.assertAlmostEqual(fd, analytic, delta=abs(analytic) * 1e-3)


class TestVerdicts(unittest.TestCase):
    def test_verdict_unstable_at_80(self):
        self.assertEqual(
            ssl.speed_stability_verdict(80.0, W, S, RHO, CD0, K), "unstable")

    def test_verdict_stable_at_130(self):
        self.assertEqual(
            ssl.speed_stability_verdict(130.0, W, S, RHO, CD0, K), "stable")

    def test_verdict_neutral_at_vmd(self):
        self.assertEqual(
            ssl.speed_stability_verdict(V_MD, W, S, RHO, CD0, K), "neutral")

    def test_verdict_boundary_below_vmd_unstable(self):
        self.assertEqual(
            ssl.speed_stability_verdict(0.999 * V_MD, W, S, RHO, CD0, K),
            "unstable")

    def test_verdict_boundary_above_vmd_stable(self):
        self.assertEqual(
            ssl.speed_stability_verdict(1.001 * V_MD, W, S, RHO, CD0, K),
            "stable")


class TestMargins(unittest.TestCase):
    def test_margin_at_80(self):
        m = ssl.margin_to_back_side(80.0, W, S, RHO, CD0, K)
        self.assertTrue(m["unstable_below"])
        self.assertAlmostEqual(m["margin_ms"], 80.0 - V_MD, places=9)
        self.assertAlmostEqual(m["margin_ms"], -30.17, delta=0.01)

    def test_margin_at_130(self):
        m = ssl.margin_to_back_side(130.0, W, S, RHO, CD0, K)
        self.assertFalse(m["unstable_below"])
        self.assertAlmostEqual(m["margin_ms"], 130.0 - V_MD, places=9)

    def test_margin_at_vmd_is_boundary(self):
        m = ssl.margin_to_back_side(V_MD, W, S, RHO, CD0, K)
        self.assertFalse(m["unstable_below"])
        self.assertAlmostEqual(m["margin_ms"], 0.0, places=9)

    def test_margin_returns_vmd_key(self):
        m = ssl.margin_to_back_side(90.0, W, S, RHO, CD0, K)
        self.assertAlmostEqual(m["v_md"], V_MD, places=9)


class TestThrustCurve(unittest.TestCase):
    def test_thrust_at_vmd_equals_twice_parasite(self):
        q = 0.5 * RHO * V_MD ** 2
        t = ssl.thrust_required(V_MD, W, S, RHO, CD0, K)
        self.assertAlmostEqual(t, 2.0 * CD0 * q * S, places=6)

    def test_parasite_equals_induced_at_vmd(self):
        q = 0.5 * RHO * V_MD ** 2
        parasite = CD0 * q * S
        induced = K * W ** 2 / (q * S)
        self.assertAlmostEqual(parasite, induced, places=6)

    def test_thrust_rises_as_speed_falls_on_back_side(self):
        t80 = ssl.thrust_required(80.0, W, S, RHO, CD0, K)
        t90 = ssl.thrust_required(90.0, W, S, RHO, CD0, K)
        t100 = ssl.thrust_required(100.0, W, S, RHO, CD0, K)
        self.assertGreater(t80, t90)
        self.assertGreater(t90, t100)


class TestAnalyze(unittest.TestCase):
    SPEEDS = [45.0, 60.0, 80.0, 100.0, 130.0]

    def test_analyze_output_structure(self):
        r = ssl.analyze(W, S, RHO, CD0, E, AR, self.SPEEDS)
        self.assertAlmostEqual(r["v_md_ms"], V_MD, places=9)
        self.assertEqual(len(r["trim_classifications"]), len(self.SPEEDS))
        self.assertEqual(len(r["margins"]), len(self.SPEEDS))
        for c in r["trim_classifications"]:
            self.assertEqual(sorted(c.keys()), ["dT_dv", "speed", "verdict"])
        for m in r["margins"]:
            self.assertEqual(sorted(m.keys()),
                             ["margin_ms", "unstable_below", "v_md"])

    def test_analyze_classifies_spec_speeds(self):
        r = ssl.analyze(W, S, RHO, CD0, E, AR, self.SPEEDS)
        verdicts = [c["verdict"] for c in r["trim_classifications"]]
        self.assertEqual(verdicts,
                         ["unstable", "unstable", "unstable", "unstable",
                          "stable"])

    def test_analyze_curve_25_points_bounded(self):
        r = ssl.analyze(W, S, RHO, CD0, E, AR, self.SPEEDS)
        curve = r["curve"]
        self.assertEqual(len(curve), 25)
        self.assertAlmostEqual(curve[0]["speed"], 0.5 * V_MD, places=9)
        self.assertAlmostEqual(curve[-1]["speed"], 1.5 * V_MD, places=9)

    def test_analyze_curve_minimum_at_vmd(self):
        r = ssl.analyze(W, S, RHO, CD0, E, AR, self.SPEEDS)
        argmin = min(range(25),
                     key=lambda i: r["curve"][i]["thrust_required_N"])
        self.assertLess(abs(r["curve"][argmin]["speed"] - V_MD), 3.0)

    def test_analyze_curve_monotonic_on_stable_branch(self):
        r = ssl.analyze(W, S, RHO, CD0, E, AR, self.SPEEDS)
        thrusts = [p["thrust_required_N"] for p in r["curve"]]
        speeds = [p["speed"] for p in r["curve"]]
        for i in range(1, 25):
            if speeds[i] > V_MD:
                self.assertGreater(thrusts[i], thrusts[i - 1])


class TestValueErrors(unittest.TestCase):
    def test_weight_zero_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(0.0, S, RHO, CD0, E, AR, [80.0])

    def test_wing_area_zero_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, 0.0, RHO, CD0, E, AR, [80.0])

    def test_rho_zero_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, 0.0, CD0, E, AR, [80.0])

    def test_cd0_zero_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, RHO, 0.0, E, AR, [80.0])

    def test_oswald_e_over_one_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, RHO, CD0, 1.1, AR, [80.0])

    def test_oswald_e_zero_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, RHO, CD0, 0.0, AR, [80.0])

    def test_aspect_ratio_zero_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, RHO, CD0, E, 0.0, [80.0])

    def test_empty_trim_list_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, RHO, CD0, E, AR, [])

    def test_nonpositive_trim_speed_rejected(self):
        with self.assertRaises(ValueError):
            ssl.analyze(W, S, RHO, CD0, E, AR, [80.0, -5.0])

    def test_helper_valueerrors(self):
        with self.assertRaises(ValueError):
            ssl.thrust_required(80.0, W, S, 0.0, CD0, K)
        with self.assertRaises(ValueError):
            ssl.thrust_required(80.0, W, S, RHO, 0.0, K)
        with self.assertRaises(ValueError):
            ssl.d_thrust_dv(0.0, W, S, RHO, CD0, K)
        with self.assertRaises(ValueError):
            ssl.min_drag_speed(0.0, S, RHO, CD0, K)
        with self.assertRaises(ValueError):
            ssl.speed_stability_verdict(80.0, W, 0.0, RHO, CD0, K)
        with self.assertRaises(ValueError):
            ssl.margin_to_back_side(80.0, W, S, RHO, CD0, 0.0)


class TestConstants(unittest.TestCase):
    def test_g0_standard_gravity(self):
        self.assertEqual(ssl.G0, 9.80665)


if __name__ == "__main__":
    unittest.main()

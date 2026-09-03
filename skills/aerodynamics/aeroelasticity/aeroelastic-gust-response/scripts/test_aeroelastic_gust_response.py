"""Contract tests for aeroelastic_gust_response_logic (stdlib unittest)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aeroelastic_gust_response_logic import (
    wagner_coefficients, kussner_coefficients, gust_angle_time,
    lag_state_derivatives, lift_from_lag_states, quasi_steady_peak_lift,
    dynamic_magnification_factor, peak_load_verdict, gust_response_history,
    WAGNER_A1, WAGNER_B1, WAGNER_A2, WAGNER_B2,
    KUSSNER_A1, KUSSNER_B1, KUSSNER_A2, KUSSNER_B2,
)

PI = math.pi

# Worked example typical section (transport wing representation).
# c = 2 m, m_s = 300 kg/m, I_theta = 40 kg m^2/m, elastic axis e = 0.2
# (20 percent chord, forward of the aerodynamic center), uncoupled
# plunge ~2 Hz and pitch ~5 Hz, V = 100 m/s, rho = 1.225 kg/m^3.
P = dict(V=100.0, c=2.0, rho=1.225, m_s=300.0, I_theta=40.0,
         k_h=300.0 * (2.0 * PI * 2.0) ** 2,
         k_theta=40.0 * (2.0 * PI * 5.0) ** 2, e=0.2)
L_QS = quasi_steady_peak_lift(P["rho"], P["V"], P["c"], 15.0)  # 11545.35


def wagner_phi(s):
    """Closed-form Wagner function from the module coefficients."""
    return 1.0 - WAGNER_A1 * math.exp(-WAGNER_B1 * s) \
        - WAGNER_A2 * math.exp(-WAGNER_B2 * s)


def kussner_phi(s):
    """Closed-form Kussner function from the module coefficients."""
    return 1.0 - KUSSNER_A1 * math.exp(-KUSSNER_B1 * s) \
        - KUSSNER_A2 * math.exp(-KUSSNER_B2 * s)


def lag_step_ratio(t, alpha0=0.05, dt=1e-4):
    """Pure-aero Wagner step: ratio L(t)/L_qs(alpha0) via lag RK4."""
    V, c, rho = P["V"], P["c"], P["rho"]
    x1 = x2 = 0.0
    n = int(round(t / dt))
    for _ in range(n):
        d1, d2, _, _ = lag_state_derivatives(alpha0, x1, x2, 0.0, 0.0, 0.0,
                                             V, c)
        m1, m2, _, _ = lag_state_derivatives(
            alpha0, x1 + 0.5 * dt * d1, x2 + 0.5 * dt * d2, 0.0, 0.0, 0.0,
            V, c)
        m3, m4, _, _ = lag_state_derivatives(
            alpha0, x1 + 0.5 * dt * m1, x2 + 0.5 * dt * m2, 0.0, 0.0, 0.0,
            V, c)
        k1b, k2b, _, _ = lag_state_derivatives(
            alpha0, x1 + dt * m3, x2 + dt * m4, 0.0, 0.0, 0.0, V, c)
        x1 += dt / 6.0 * (d1 + 2.0 * m1 + 2.0 * m3 + k1b)
        x2 += dt / 6.0 * (d2 + 2.0 * m2 + 2.0 * m4 + k2b)
    L = lift_from_lag_states(alpha0, x1, x2, 0.0, 0.0, 0.0, rho, V, c)
    return L / quasi_steady_peak_lift(rho, V, c, alpha0 * V)


class TestIndicialCoefficients(unittest.TestCase):
    def test_wagner_coefficients_module_values(self):
        w = wagner_coefficients()
        self.assertAlmostEqual(w["A1"], 0.165)
        self.assertAlmostEqual(w["b1"], 0.0455)
        self.assertAlmostEqual(w["A2"], 0.335)
        self.assertAlmostEqual(w["b2"], 0.3)

    def test_kussner_coefficients_module_values(self):
        k = kussner_coefficients()
        self.assertAlmostEqual(k["A1"], 0.5)
        self.assertAlmostEqual(k["b1"], 0.13)
        self.assertAlmostEqual(k["A2"], 0.5)
        self.assertAlmostEqual(k["b2"], 1.0)

    def test_wagner_step_limits(self):
        self.assertAlmostEqual(wagner_phi(0.0), 0.5, places=12)
        self.assertGreaterEqual(wagner_phi(200.0), 0.999)

    def test_kussner_sharp_edge_limits(self):
        self.assertAlmostEqual(kussner_phi(0.0), 0.0, places=12)
        self.assertGreaterEqual(kussner_phi(200.0), 0.999)
        self.assertAlmostEqual(kussner_phi(1.0), 0.3770, delta=0.01)


class TestGustAngle(unittest.TestCase):
    def test_gust_angle_endpoints_and_peak(self):
        s_g = 25.0
        self.assertEqual(gust_angle_time(15.0, 100.0, s_g, 0.0), 0.0)
        self.assertEqual(gust_angle_time(15.0, 100.0, s_g, s_g), 0.0)
        self.assertAlmostEqual(gust_angle_time(15.0, 100.0, s_g,
                                               s_g / 2.0), 0.15)
        self.assertEqual(gust_angle_time(15.0, 100.0, s_g, 2.0 * s_g), 0.0)

    def test_gust_angle_shape_mid_gradient(self):
        # One-minus-cosine at s_g/4: (1 - cos(pi/2))/2 = 0.5 of peak.
        self.assertAlmostEqual(gust_angle_time(15.0, 100.0, 4.0, 1.0),
                               0.075)

    def test_gust_angle_validation(self):
        with self.assertRaises(ValueError):
            gust_angle_time(-1.0, 100.0, 25.0, 1.0)
        with self.assertRaises(ValueError):
            gust_angle_time(15.0, 0.0, 25.0, 1.0)
        with self.assertRaises(ValueError):
            gust_angle_time(15.0, 100.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            gust_angle_time(15.0, 100.0, 25.0, float("nan"))


class TestLagStepResponse(unittest.TestCase):
    """Anchor: a step in effective angle with no gust starts at about
    0.5 of the quasi-steady lift (Wagner phi(0) = 0.5) and converges to
    the full value over a long time."""

    def test_step_initial_lift_about_half(self):
        self.assertAlmostEqual(lag_step_ratio(1e-4), 0.5, delta=0.01)
        self.assertAlmostEqual(lag_step_ratio(1e-3), 0.5, delta=0.03)

    def test_step_matches_wagner_closed_form(self):
        for t in (0.05, 0.1, 0.3):
            s = 2.0 * P["V"] * t / P["c"]
            self.assertAlmostEqual(lag_step_ratio(t), wagner_phi(s),
                                   delta=0.02)

    def test_step_converges_to_full_value(self):
        ratio = lag_step_ratio(2.0)
        self.assertGreaterEqual(ratio, 0.97)
        self.assertLessEqual(ratio, 1.01)


class TestLiftKernel(unittest.TestCase):
    def test_fully_developed_states_give_quasi_steady(self):
        # All lags saturated: total angle 0.05 + 0.10 gives full lift.
        L = lift_from_lag_states(0.05, 0.05, 0.05, 0.10, 0.10, 0.10,
                                 P["rho"], P["V"], P["c"])
        self.assertAlmostEqual(L, 2.0 * PI * P["rho"] * P["V"] ** 2
                               * P["c"] / 2.0 * 0.15, places=3)

    def test_kussner_channel_starts_at_zero(self):
        # Sharp-edge gust angle with zero lag states: zero gust lift.
        L = lift_from_lag_states(0.0, 0.0, 0.0, 0.15, 0.0, 0.0,
                                 P["rho"], P["V"], P["c"])
        self.assertAlmostEqual(L, 0.0, places=9)


class TestReferenceMetrics(unittest.TestCase):
    def test_quasi_steady_peak_lift_formula(self):
        self.assertAlmostEqual(L_QS, 11545.35, places=1)
        half = quasi_steady_peak_lift(P["rho"], P["V"], P["c"], 7.5)
        self.assertAlmostEqual(2.0 * half, L_QS, places=6)

    def test_dynamic_magnification_factor_basic(self):
        self.assertAlmostEqual(dynamic_magnification_factor(8000.0,
                                                             L_QS),
                               8000.0 / L_QS)
        with self.assertRaises(ValueError):
            dynamic_magnification_factor(1.0, 0.0)

    def test_peak_load_verdict_pass(self):
        verdict, margin = peak_load_verdict(6901.0, 8000.0)
        self.assertEqual(verdict, "PASS")
        self.assertAlmostEqual(margin, 8000.0 / 6901.0 - 1.0, places=6)
        self.assertGreater(margin, 0.0)

    def test_peak_load_verdict_fail(self):
        verdict, margin = peak_load_verdict(6901.0, 6000.0)
        self.assertEqual(verdict, "FAIL")
        self.assertLess(margin, 0.0)

    def test_peak_load_verdict_boundary(self):
        self.assertEqual(peak_load_verdict(6901.0, 6901.0),
                         ("PASS", 0.0))


class TestGustResponseHistory(unittest.TestCase):
    def run_history(self, w_g=15.0, H=25.0, t_max=2.5, **over):
        params = dict(P)
        params.update(over)
        return gust_response_history(params, w_g, H, 5e-4, t_max)

    def test_history_lengths_consistent(self):
        r = self.run_history()
        self.assertEqual(len(r["t"]), len(r["h"]))
        self.assertEqual(len(r["t"]) - 1, len(r["lift"]))
        self.assertEqual(r["n_steps"], 5000)

    def test_worked_example_peak_and_dmf(self):
        # H = 25 m one-minus-cosine gust, w_g = 15 m/s. Real computed
        # values: peak |L| = 6901 N/m, DMF = 0.60 relative to the rigid
        # quasi-steady peak 11545 N/m (peak at t = 0.135 s).
        r = self.run_history()
        dmf = dynamic_magnification_factor(r["peak_lift"], L_QS)
        self.assertAlmostEqual(r["peak_lift"], 6901.0, delta=70.0)
        self.assertAlmostEqual(dmf, 0.5977, delta=0.02)
        self.assertLess(r["peak_time"], 0.25)

    def test_response_stays_in_linear_regime(self):
        r = self.run_history()
        self.assertLess(max(abs(x) for x in r["theta"]), 0.1)
        self.assertLess(max(abs(x) for x in r["h"]), 0.3)

    def test_long_gradient_dmf_approaches_quasi_static(self):
        # H = 200 m: DMF -> 0.837, the static aeroelastic ratio for the
        # forward elastic axis (e = 0.2), 1/(1 + q) with
        # q = (0.25 - e) c 2 pi rho V^2 b / k_theta = 0.195.
        r = self.run_history(H=200.0)
        dmf = dynamic_magnification_factor(r["peak_lift"], L_QS)
        self.assertGreaterEqual(dmf, 0.78)
        self.assertLessEqual(dmf, 0.88)

    def test_long_gradient_dmf_approaches_one_no_alleviation(self):
        # Elastic axis at the aerodynamic center (e = 0.25): no static
        # aeroelastic alleviation, so a very long gradient approaches a
        # dynamic magnification factor of ~1.0.
        r = self.run_history(H=200.0, e=0.25)
        dmf = dynamic_magnification_factor(r["peak_lift"], L_QS)
        self.assertGreaterEqual(dmf, 0.93)
        self.assertLessEqual(dmf, 1.05)

    def test_dmf_increases_monotonically_with_gradient(self):
        # Documented direction for this flexible section: longer
        # gradient approaches the quasi-steady peak, so DMF rises with
        # H toward the static ratio (the rigid-load-factor 'shorter
        # gust, larger DMF' behavior belongs to the discrete-gust load
        # method of the structures loads sibling).
        dmf_short = dynamic_magnification_factor(
            self.run_history(H=2.0)["peak_lift"], L_QS)
        dmf_mid = dynamic_magnification_factor(
            self.run_history(H=25.0)["peak_lift"], L_QS)
        dmf_long = dynamic_magnification_factor(
            self.run_history(H=200.0)["peak_lift"], L_QS)
        self.assertLess(dmf_short, dmf_mid)
        self.assertLess(dmf_mid, dmf_long)

    def test_peak_load_verdict_against_worked_example(self):
        r = self.run_history()
        self.assertEqual(peak_load_verdict(r["peak_lift"], 8000.0)[0],
                         "PASS")
        self.assertEqual(peak_load_verdict(r["peak_lift"], 6500.0)[0],
                         "FAIL")

    def test_no_gust_quiescent_state(self):
        r = self.run_history(w_g=0.0, H=25.0, t_max=1.0)
        self.assertLess(max(abs(x) for x in r["h"]), 1e-9)
        self.assertLess(max(abs(x) for x in r["lift"]), 1e-6)

    def test_linear_scaling_with_gust_velocity(self):
        peak15 = self.run_history(w_g=15.0, H=25.0)["peak_lift"]
        peak7 = self.run_history(w_g=7.5, H=25.0)["peak_lift"]
        self.assertAlmostEqual(peak15 / peak7, 2.0, delta=0.01)


class TestValidation(unittest.TestCase):
    def run_history(self, **over):
        params = dict(P)
        params.update(over)
        return gust_response_history(params, 15.0, 25.0, 5e-4, 2.0)

    def test_valueerror_nonpositive_speed(self):
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                self.run_history(V=bad)

    def test_valueerror_nonpositive_chord(self):
        for bad in (0.0, -2.0):
            with self.assertRaises(ValueError):
                self.run_history(c=bad)

    def test_valueerror_nonpositive_mass_stiffness(self):
        with self.assertRaises(ValueError):
            self.run_history(m_s=0.0)
        with self.assertRaises(ValueError):
            self.run_history(I_theta=-1.0)
        with self.assertRaises(ValueError):
            self.run_history(k_h=0.0)
        with self.assertRaises(ValueError):
            self.run_history(k_theta=-5.0)
        with self.assertRaises(ValueError):
            self.run_history(rho=0.0)

    def test_valueerror_negative_gust_velocity(self):
        with self.assertRaises(ValueError):
            gust_response_history(P, -1.0, 25.0, 5e-4, 2.0)

    def test_valueerror_nonpositive_gradient_step_tmax(self):
        with self.assertRaises(ValueError):
            gust_response_history(P, 15.0, 0.0, 5e-4, 2.0)
        with self.assertRaises(ValueError):
            gust_response_history(P, 15.0, 25.0, 0.0, 2.0)
        with self.assertRaises(ValueError):
            gust_response_history(P, 15.0, 25.0, 5e-4, -1.0)

    def test_valueerror_nonfinite_input(self):
        with self.assertRaises(ValueError):
            self.run_history(V=float("nan"))
        with self.assertRaises(ValueError):
            self.run_history(k_h=float("inf"))

    def test_valueerror_elastic_axis_out_of_range(self):
        for bad in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                self.run_history(e=bad)

    def test_valueerror_missing_param_key(self):
        params = dict(P)
        del params["k_h"]
        with self.assertRaises(ValueError):
            gust_response_history(params, 15.0, 25.0, 5e-4, 2.0)

    def test_valueerror_negative_peak_in_verdict(self):
        with self.assertRaises(ValueError):
            peak_load_verdict(-1.0, 100.0)


if __name__ == "__main__":
    unittest.main()

"""Contract test for the smith-predictor leaf.

Exercises the SKILL.md Workflow steps 1-8: fixing the plant and
controller (step 1), the sampled recurrence and delay-line length
(step 2), the delay-free companion simulation (step 3), the
predictor-compensated loop and its compensated error (step 4), the
conventional loop at the same given gains (step 5), the step-response
metrics of both loops (step 6), the predictor delay-shift identity
(step 7), and this deterministic contract test itself (step 8).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import smith_predictor_logic as sp


def y_at(result, t_value, dt=sp.SAMPLE_DT):
    idx = round(t_value / dt)
    return result["y"][idx]


class TestRecurrenceAndDelayLine(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the sampled first-order lag
    recurrence and the integer delay-line length."""

    def test_recurrence_coefficients(self):
        a, b = sp.first_order_lag_recurrence(1.0, 1.0, 0.01)
        self.assertAlmostEqual(a, 0.990049834, delta=1e-9)
        self.assertAlmostEqual(b, 0.009950166, delta=1e-9)

    def test_coefficient_sum_identity(self):
        a, b = sp.first_order_lag_recurrence(1.0, 1.0, 0.01)
        self.assertAlmostEqual(a + b, 1.0, delta=1e-12)

    def test_dc_gain_identity(self):
        a, b = sp.first_order_lag_recurrence(1.0, 1.0, 0.01)
        self.assertAlmostEqual(b / (1.0 - a), 1.0, delta=1e-9)

    def test_delay_steps_worked(self):
        self.assertEqual(sp.delay_steps(2.0, 0.01), 200)
        self.assertEqual(sp.delay_steps(5.0, 0.01), 500)
        self.assertEqual(sp.delay_steps(0.0, 0.01), 0)

    def test_recurrence_value_errors(self):
        with self.assertRaises(ValueError):
            sp.first_order_lag_recurrence(0.0, 1.0, 0.01)
        with self.assertRaises(ValueError):
            sp.first_order_lag_recurrence(1.0, 0.0, 0.01)
        with self.assertRaises(ValueError):
            sp.first_order_lag_recurrence(1.0, 1.0, 0.0)

    def test_delay_steps_value_errors(self):
        with self.assertRaises(ValueError):
            sp.delay_steps(-0.1, 0.01)
        with self.assertRaises(ValueError):
            sp.delay_steps(2.5, 1.0)
        with self.assertRaises(ValueError):
            sp.delay_steps(0.0, 0.0)

    def test_pi_output_value_errors(self):
        with self.assertRaises(ValueError):
            sp.pi_output(0.1, 0.0, 0.01, 0.0, 0.5)
        with self.assertRaises(ValueError):
            sp.pi_output(0.1, 0.0, 0.01, 0.5, -0.1)
        with self.assertRaises(ValueError):
            sp.pi_output(0.1, 0.0, 0.0, 0.5, 0.5)

    def test_pi_output_step(self):
        u, integral_next = sp.pi_output(1.0, 0.0, 0.01, 0.5, 0.5)
        self.assertAlmostEqual(integral_next, 0.01, delta=1e-12)
        self.assertAlmostEqual(u, 0.5 * 1.0 + 0.5 * 0.01, delta=1e-12)


class TestDelayFreeCompanion(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the delay-free companion
    simulation the predictor loop must reproduce after the dead time."""

    def setUp(self):
        self.df = sp.simulate_closed_loop(dead_time=0.0, predictor=False)

    def test_matches_closed_form(self):
        max_err = 0.0
        for t, y in zip(self.df["t"], self.df["y"]):
            closed_form = 1.0 - math.exp(-sp.CL_POLE_RATE * t)
            max_err = max(max_err, abs(y - closed_form))
        self.assertLess(max_err, 5e-3)

    def test_delay_free_metrics(self):
        metrics = self.df["metrics"]
        self.assertAlmostEqual(metrics["overshoot_pct"], 0.0, delta=1e-6)
        self.assertAlmostEqual(metrics["settling_time"], 7.83, delta=0.02)

    def test_delay_free_settling_theory(self):
        theory = 2.0 * math.log(50.0)
        self.assertAlmostEqual(self.df["metrics"]["settling_time"], theory, delta=0.02)


class TestPredictorLoopWorkedTheta2(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the predictor-compensated loop
    at the worked dead time theta = 2.0 s, run on the delay-free plant
    model held in the delay line and subtracted from the measured
    output to form the predictor feedback signal."""

    def setUp(self):
        self.res = sp.simulate_closed_loop(dead_time=2.0, predictor=True)

    def test_zero_overshoot(self):
        self.assertAlmostEqual(self.res["metrics"]["overshoot_pct"], 0.0, delta=1e-6)

    def test_settling_time(self):
        self.assertAlmostEqual(self.res["metrics"]["settling_time"], 9.83, delta=0.02)

    def test_final_deviation(self):
        self.assertLess(self.res["metrics"]["final_deviation"], 1e-9)

    def test_sample_values(self):
        self.assertAlmostEqual(y_at(self.res, 4.0), 0.633527, delta=1e-5)
        self.assertAlmostEqual(y_at(self.res, 8.0), 0.950313, delta=1e-5)
        self.assertAlmostEqual(y_at(self.res, 12.0), 0.993245, delta=1e-5)
        self.assertAlmostEqual(y_at(self.res, 20.0), 0.999875, delta=1e-5)

    def test_monotone_response(self):
        y = self.res["y"]
        for k in range(1, len(y)):
            self.assertGreaterEqual(y[k] + 1e-9, y[k - 1])


class TestConventionalLoopWorkedTheta2(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the conventional loop at the
    SAME given gains as the predictor loop, isolating the effect of
    removing the predictor structure."""

    def setUp(self):
        self.res = sp.simulate_closed_loop(dead_time=2.0, predictor=False)

    def test_overshoot_and_peak_time(self):
        self.assertAlmostEqual(self.res["metrics"]["overshoot_pct"], 50.212, delta=0.01)
        self.assertAlmostEqual(self.res["metrics"]["peak_time"], 6.00, delta=0.02)

    def test_settling_time(self):
        self.assertAlmostEqual(self.res["metrics"]["settling_time"], 25.82, delta=0.02)

    def test_final_deviation(self):
        self.assertAlmostEqual(self.res["metrics"]["final_deviation"], 0.000022, delta=1e-4)

    def test_sample_values(self):
        self.assertAlmostEqual(y_at(self.res, 4.0), 1.002158, delta=1e-5)
        self.assertAlmostEqual(y_at(self.res, 8.0), 1.165740, delta=1e-5)
        self.assertAlmostEqual(y_at(self.res, 12.0), 0.841161, delta=1e-5)
        self.assertAlmostEqual(y_at(self.res, 20.0), 0.946013, delta=1e-5)

    def test_degrades_versus_predictor(self):
        predictor = sp.simulate_closed_loop(dead_time=2.0, predictor=True)
        self.assertGreater(
            self.res["metrics"]["overshoot_pct"], predictor["metrics"]["overshoot_pct"]
        )
        self.assertGreater(
            self.res["metrics"]["settling_time"], predictor["metrics"]["settling_time"]
        )


class TestRobustnessTheta5(unittest.TestCase):
    """Steps 4 and 5 of the SKILL.md workflow repeated at the
    robustness dead time theta = 5.0 s: the predictor loop still
    reproduces the delay-free response while the conventional loop at
    the same given gains diverges."""

    def test_predictor_loop_theta5(self):
        res = sp.simulate_closed_loop(dead_time=5.0, predictor=True)
        self.assertAlmostEqual(res["metrics"]["overshoot_pct"], 0.0, delta=1e-6)
        self.assertAlmostEqual(res["metrics"]["settling_time"], 12.83, delta=0.02)
        self.assertAlmostEqual(y_at(res, 6.0), 0.395100, delta=1e-5)
        self.assertAlmostEqual(y_at(res, 10.0), 0.918155, delta=1e-5)
        self.assertAlmostEqual(y_at(res, 20.0), 0.999442, delta=1e-5)
        self.assertAlmostEqual(y_at(res, 40.0), 1.000000, delta=1e-5)

    def test_conventional_loop_theta5_diverges(self):
        res = sp.simulate_closed_loop(dead_time=5.0, predictor=False)
        self.assertIsNone(res["metrics"]["settling_time"])
        self.assertAlmostEqual(res["metrics"]["overshoot_pct"], 2182.315, delta=0.01)
        self.assertAlmostEqual(res["metrics"]["final_deviation"], 11.909619, delta=1e-3)

    def test_conventional_loop_theta5_growing_oscillation(self):
        res = sp.simulate_closed_loop(dead_time=5.0, predictor=False)
        y10 = abs(y_at(res, 10.0))
        y6 = abs(y_at(res, 6.0))
        y40 = y_at(res, 40.0)
        y20 = y_at(res, 20.0)
        self.assertGreater(y10, y6)
        self.assertLess(y40, y20)


class TestPredictorDelayShiftIdentity(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the predictor delay-shift
    identity, the discrete witness that the dead time left the
    characteristic equation."""

    def setUp(self):
        self.df = sp.simulate_closed_loop(dead_time=0.0, predictor=False)

    def test_theta2_delay_shift(self):
        sp2 = sp.simulate_closed_loop(dead_time=2.0, predictor=True)
        max_err = sp.delay_shift_max_error(sp2["y"], self.df["y"], 200)
        self.assertLess(max_err, 1e-9)

    def test_theta5_delay_shift(self):
        sp5 = sp.simulate_closed_loop(dead_time=5.0, predictor=True)
        max_err = sp.delay_shift_max_error(sp5["y"], self.df["y"], 500)
        self.assertLess(max_err, 1e-9)

    def test_compensated_error_matches_delay_free_error(self):
        sp2 = sp.simulate_closed_loop(dead_time=2.0, predictor=True)
        max_err = 0.0
        for e_comp, e_df in zip(sp2["controller_error"], self.df["controller_error"]):
            max_err = max(max_err, abs(e_comp - e_df))
        self.assertLess(max_err, 1e-9)

    def test_delay_shift_value_errors(self):
        with self.assertRaises(ValueError):
            sp.delay_shift_max_error([1.0, 2.0], [1.0], 0)
        with self.assertRaises(ValueError):
            sp.delay_shift_max_error([1.0, 2.0], [1.0, 2.0], 5)


class TestZeroDelayCollapse(unittest.TestCase):
    """Step 4 of the SKILL.md workflow at theta = 0: the predictor
    feedback signal vanishes and the predictor loop collapses onto the
    delay-free companion."""

    def test_zero_delay_matches_companion(self):
        df = sp.simulate_closed_loop(dead_time=0.0, predictor=False)
        sp0 = sp.simulate_closed_loop(dead_time=0.0, predictor=True)
        max_err = 0.0
        for y_a, y_b in zip(sp0["y"], df["y"]):
            max_err = max(max_err, abs(y_a - y_b))
        self.assertLess(max_err, 1e-9)


class TestStepMetricsAndSteadyState(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the step-response metrics of
    both loops, including the steady-state final deviation."""

    def test_step_metrics_empty_series(self):
        with self.assertRaises(ValueError):
            sp.step_metrics([], [])

    def test_step_metrics_basic(self):
        t = [0.0, 1.0, 2.0, 3.0]
        y = [0.0, 0.5, 1.0, 1.0]
        metrics = sp.step_metrics(t, y, reference=1.0, band=0.02)
        self.assertAlmostEqual(metrics["overshoot_pct"], 0.0, delta=1e-9)
        self.assertEqual(metrics["peak_time"], 2.0)

    def test_predictor_steady_state_below_conventional(self):
        pred = sp.simulate_closed_loop(dead_time=2.0, predictor=True)
        conv = sp.simulate_closed_loop(dead_time=2.0, predictor=False)
        self.assertLess(pred["metrics"]["final_deviation"], 1e-6)
        self.assertLess(conv["metrics"]["final_deviation"], 1e-4)


class TestDeterminism(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: the deterministic contract
    test confirms identical outputs run to run under the fixed module
    constants, no randomness anywhere."""

    def test_repeat_run_identical(self):
        res1 = sp.simulate_closed_loop(dead_time=2.0, predictor=True)
        res2 = sp.simulate_closed_loop(dead_time=2.0, predictor=True)
        self.assertEqual(res1["y"], res2["y"])
        self.assertEqual(res1["d_steps"], res2["d_steps"])

    def test_simulate_value_error(self):
        with self.assertRaises(ValueError):
            sp.simulate_closed_loop(sim_time=0.0)

    def test_module_constants(self):
        self.assertEqual(sp.PLANT_GAIN_K, 1.0)
        self.assertEqual(sp.PLANT_TAU, 1.0)
        self.assertEqual(sp.WORKED_THETA, 2.0)
        self.assertEqual(sp.ROBUST_THETA, 5.0)
        self.assertEqual(sp.CONTROLLER_KP, 0.5)
        self.assertEqual(sp.CONTROLLER_KI, 0.5)
        self.assertEqual(sp.SAMPLE_DT, 0.01)
        self.assertEqual(sp.SIM_TIME, 60.0)


if __name__ == "__main__":
    unittest.main()

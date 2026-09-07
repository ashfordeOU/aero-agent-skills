"""Contract test for the l1-adaptive-control leaf (gnc-autonomy/control).

Deterministic, offline, stdlib unittest. Run from the repo root:

    python3 skills/gnc-autonomy/control/l1-adaptive-control/scripts/test_l1_adaptive_control.py

The test exercises the SKILL.md workflow end to end: step 1 fixes the
loop data (design pole a_m, effectiveness b, reference gain b_m, command
r, disturbance d, step dt, adaptation rate gamma, filter bandwidth
omega_c, projection bound sigma_b, run length); step 2 sanity-checks the
projection-based-adaptation-law pieces and the low-pass filter step;
step 3 forms the design-frame lumped uncertainty with sigma_true and
checks the L1 admissibility products; step 4 runs the closed loop with
simulate, which propagates the state-predictor against the plant and
drives the low-pass-filtered projection adaptation law on the prediction
error; step 5 checks the transient bound of the tracking error against
the certified bound E_BOUND; step 6 reads the convergence_report verdict
from the tail metrics; step 7 cross-checks the reference-model, filter
and no-adaptation closed forms; step 8 confirms determinism and the
ValueError rejection of non-physical inputs. All numeric asserts on
computed sums are tolerance based (assertAlmostEqual/math.isclose);
exact equality is reserved for literal constants and round-trips exact
by construction. No RNG, no network, no external processes.
"""

import math
import os
import unittest

import l1_adaptive_control_logic as m

# Worked scenario constants (spec): a_m = -1.0, b = 2.0, b_m = 1.0,
# r = 1.0, x0 = 0.0, d = 1.0, dt = 0.01, gamma = 10.0, omega_c = 10.0,
# sigma_b = 2.0, a_p = -0.5, steps = 6000.
A_M = m.A_M
B = m.B
B_M = m.B_M
R = m.R
X0 = m.X0
D = m.D
DT = m.DT
GAMMA = m.GAMMA
OMEGA_C = m.OMEGA_C
SIGMA_B = m.SIGMA_B
PLANT_A = m.PLANT_A
STEPS = m.N_STEPS

# Worked-example real module anchors (prep values, tolerance asserted).
X_FINAL = 0.999999958694
SIGMA_HAT_FINAL = 1.249999983204
NU_FINAL = 1.250000018748
U_FINAL = -0.750000018748
SIGMA_IDEAL = 1.249999989673
MAX_ABS_TRACK = 0.5607716796
MAX_ABS_PRED = 0.4359531903
E_BOUND = 0.75
TAIL_ABS_PRED = 5.604354e-07
TAIL_DRIFT = 5.604354e-08


def worked_run(steps=STEPS):
    """Default worked-scenario simulate run (step 4 of the workflow)."""
    return m.simulate(plant_a=PLANT_A, a_m=A_M, b=B, b_m=B_M, r=R, x0=X0,
                      d=D, dt=DT, gamma=GAMMA, omega_c=OMEGA_C,
                      sigma_b=SIGMA_B, steps=steps)


def _isclose(a, b, rel_tol=1e-6):
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=1e-12)


class TestProjection(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, the projection-based-adaptation-law
    boundary behavior, is exercised here: interior directions pass, an
    outward direction at a bound is zeroed, an inward direction passes."""

    def test_projection_interior_direction_passes(self):
        self.assertEqual(m.projection(1.0, -0.5), -0.5)
        self.assertEqual(m.projection(0.5, 0.3), 0.3)
        self.assertEqual(m.projection(0.0, -0.25), -0.25)

    def test_projection_upper_bound_inward_passes_outward_zero(self):
        self.assertEqual(m.projection(2.0, -0.5), -0.5)
        self.assertEqual(m.projection(2.0, 0.5), 0.0)

    def test_projection_lower_bound_inward_passes_outward_zero(self):
        self.assertEqual(m.projection(-2.0, 0.5), 0.5)
        self.assertEqual(m.projection(-2.0, -0.5), 0.0)

    def test_projection_validation_raises(self):
        with self.assertRaises(ValueError):
            m.projection(1.0, -0.5, sigma_b=0.0)
        with self.assertRaises(ValueError):
            m.projection(3.0, -0.5)


class TestAdaptiveUpdate(unittest.TestCase):
    """Step 2 of the workflow: the clamped Euler projection step of the
    projection-based-adaptation-law keeps sigma_hat inside the bound."""

    def test_adaptive_update_clamped_to_sigma_b_exact(self):
        # raw = 1.9 - 0.1*10*(-0.2) = 2.1, clamped to exactly SIGMA_B = 2.0.
        self.assertEqual(m.adaptive_update(1.9, -0.2, 10.0, 0.1), SIGMA_B)

    def test_adaptive_update_interior_step_exact(self):
        # raw = 0.0 - 0.1*10*(-0.2) = 0.2, interior, passes unchanged.
        self.assertEqual(m.adaptive_update(0.0, -0.2, 10.0, 0.1), 0.2)

    def test_adaptive_update_default_rate_drives_estimate(self):
        # sigma_hat_new = sigma_hat - dt*gamma*pred_err = 1.0 + 0.01*10*0.05.
        self.assertAlmostEqual(m.adaptive_update(1.0, -0.05),
                               1.005, delta=1e-12)

    def test_adaptive_update_invalid_raises(self):
        with self.assertRaises(ValueError):
            m.adaptive_update(0.0, -0.2, gamma=-1.0)
        with self.assertRaises(ValueError):
            m.adaptive_update(0.0, -0.2, dt=0.0)
        with self.assertRaises(ValueError):
            m.adaptive_update(0.0, float("nan"))


class TestFilterAndControl(unittest.TestCase):
    """Step 2 of the workflow: the low-pass filter step C(s) = omega_c /
    (s + omega_c) on the adaptive signal and the control law."""

    def test_filter_step_euler_values_and_validation(self):
        # nu_next = 0 + 0.01*10*(1 - 0) = 0.1; from nu = 1 toward 0.5.
        self.assertAlmostEqual(m.filter_step(0.0, 1.0), 0.1, delta=1e-12)
        self.assertAlmostEqual(m.filter_step(1.0, 0.5),
                               1.0 + DT * OMEGA_C * (0.5 - 1.0),
                               delta=1e-12)
        with self.assertRaises(ValueError):
            m.filter_step(0.0, 1.0, omega_c=0.0)
        with self.assertRaises(ValueError):
            m.filter_step(0.0, 1.0, dt=0.0)

    def test_control_output_rule_and_validation(self):
        # u = (-a_m/b)*r - nu = 0.5 - nu.
        self.assertAlmostEqual(m.control_output(0.0), 0.5, delta=1e-12)
        self.assertAlmostEqual(m.control_output(0.75), -0.25, delta=1e-12)
        with self.assertRaises(ValueError):
            m.control_output(0.0, b=0.0)

    def test_plant_step_euler_value_and_validation(self):
        # x_next = 0 + 0.01*(-0.5*0 + 2*u + 2*1); with u = 0.5: 0.03.
        self.assertAlmostEqual(m.plant_step(0.0, 0.5), 0.03, delta=1e-12)
        with self.assertRaises(ValueError):
            m.plant_step(0.0, 0.5, dt=-1.0)
        with self.assertRaises(ValueError):
            m.plant_step(float("inf"), 0.5)

    def test_predictor_step_euler_value_and_validation(self):
        # xh_next = 0 + 0.01*(-1*0 + 2*(u + sigma_hat)); u = 0.5, sh = 0.1.
        self.assertAlmostEqual(m.predictor_step(0.0, 0.5, 0.1),
                               0.012, delta=1e-12)
        with self.assertRaises(ValueError):
            m.predictor_step(0.0, 0.5, 0.1, dt=0.0)

    def test_reference_step_euler_value_and_validation(self):
        # xm_next = 0 + 0.01*(-1*0 + 1*1) = 0.01.
        self.assertAlmostEqual(m.reference_step(0.0), 0.01, delta=1e-12)
        with self.assertRaises(ValueError):
            m.reference_step(0.0, a_m=0.0)
        with self.assertRaises(ValueError):
            m.reference_step(0.0, a_m=0.5)
        with self.assertRaises(ValueError):
            m.reference_step(0.0, dt=0.0)

    def test_sigma_true_lumped_uncertainty(self):
        # sigma_true(x) = (a_p - a_m)*x/b + d = 0.25*x + 1.0.
        self.assertAlmostEqual(m.sigma_true(0.0), 1.0, delta=1e-12)
        self.assertAlmostEqual(m.sigma_true(1.0), 1.25, delta=1e-12)
        with self.assertRaises(ValueError):
            m.sigma_true(0.0, b=0.0)


class TestWorkedExample(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, the closed-loop simulate run that
    propagates the state-predictor against the truth plant while the
    low-pass-filtered projection adaptation law estimates the lumped
    uncertainty, is exercised by these methods."""

    def test_worked_example_finals_within_tolerance(self):
        res = worked_run()
        self.assertTrue(_isclose(res["x"][-1], X_FINAL))
        self.assertTrue(_isclose(res["sigma_hat"][-1], SIGMA_HAT_FINAL))
        self.assertTrue(_isclose(res["nu"][-1], NU_FINAL))
        self.assertTrue(_isclose(res["u"][-1], U_FINAL))
        self.assertTrue(_isclose(m.sigma_ideal(res["x"][-1]), SIGMA_IDEAL))

    def test_worked_example_final_errors_small(self):
        res = worked_run()
        self.assertLess(abs(res["track_err"][-1]), 1e-3)   # -4.130627e-08
        self.assertLess(abs(res["pred_err"][-1]), 1e-3)    # 4.151e-08

    def test_worked_example_equilibrium_residual(self):
        res = worked_run()
        residual = abs(PLANT_A * res["x"][-1] + B * res["u"][-1] + B * D)
        self.assertLess(residual, 1e-6)                    # 1.684e-08
        u_eq = -(PLANT_A * res["x"][-1] + B * D) / B
        self.assertTrue(_isclose(res["u"][-1], u_eq, rel_tol=1e-4))

    def test_worked_example_transient_metrics(self):
        # Step 5 of the workflow: the transient bound of the tracking
        # error, max |e| = 0.5607716796 at k = 43, sits below the
        # certified scenario bound E_BOUND = 0.75 (the
        # guaranteed-transient-response verdict).
        res = worked_run()
        self.assertTrue(_isclose(res["max_abs_track"], MAX_ABS_TRACK,
                                 rel_tol=1e-3))
        self.assertLess(res["max_abs_track"], E_BOUND)
        self.assertTrue(_isclose(res["max_abs_pred"], MAX_ABS_PRED,
                                 rel_tol=1e-3))
        self.assertAlmostEqual(res["max_abs_sigma"], SIGMA_B,
                               delta=1e-12)

    def test_projection_engagement_count_and_steps(self):
        # The projection clamps sigma_hat to the sigma_b = 2.0 bound on
        # exactly 7 consecutive steps, k = 67..73, during the ramp.
        res = worked_run()
        self.assertEqual(res["proj_active"], 7)
        clamped = []
        for k in range(STEPS):
            raw = res["sigma_hat"][k] - DT * GAMMA * res["pred_err"][k]
            if raw > SIGMA_B or raw < -SIGMA_B:
                clamped.append(k)
        self.assertEqual(clamped, list(range(67, 74)))

    def test_worked_example_histories_seeded_and_length(self):
        res = worked_run()
        n = STEPS + 1
        self.assertEqual(len(res["x"]), n)
        self.assertEqual(len(res["xm"]), n)
        self.assertEqual(len(res["xh"]), n)
        self.assertEqual(len(res["u"]), n)
        self.assertEqual(len(res["sigma_hat"]), n)
        self.assertEqual(len(res["nu"]), n)
        self.assertEqual(len(res["pred_err"]), n)
        self.assertEqual(len(res["track_err"]), n)
        self.assertEqual(res["x"][0], X0)
        self.assertEqual(res["xh"][0], X0)
        self.assertEqual(res["xm"][0], X0)
        self.assertEqual(res["u"][0], 0.5)       # k_g*r at index 0
        self.assertEqual(res["sigma_hat"][0], 0.0)
        self.assertEqual(res["nu"][0], 0.0)
        self.assertEqual(res["pred_err"][0], 0.0)
        self.assertEqual(res["track_err"][0], 0.0)

    def test_settling_milestones(self):
        # x stays within 1e-3 of 1 permanently from k = 2211 and the
        # prediction error stays below 1e-4 permanently from k = 3065
        # (allow +/- 20 steps on both milestones).
        res = worked_run()
        x = res["x"]
        kx = len(x) - 1
        while kx > 0 and abs(x[kx - 1] - 1.0) < 1e-3:
            kx -= 1
        self.assertLessEqual(abs(kx - 2211), 20)
        pe = res["pred_err"]
        kt = len(pe) - 1
        while kt > 0 and abs(pe[kt - 1]) < 1e-4:
            kt -= 1
        self.assertLessEqual(abs(kt - 3065), 20)


class TestConvergenceVerdict(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, the convergence_report verdict
    from the tail metrics, is exercised here."""

    def test_verdict_converged_with_criteria(self):
        res = worked_run()
        converged, criteria = m.convergence_report(res)
        self.assertTrue(converged)
        self.assertTrue(_isclose(criteria["tail_abs_pred"], TAIL_ABS_PRED,
                                 rel_tol=0.1))
        self.assertLess(criteria["tail_abs_pred"], 1e-4)
        self.assertLess(criteria["tail_sigma_drift"], 1e-6)
        self.assertAlmostEqual(criteria["tail_sigma_drift"], TAIL_DRIFT,
                               delta=TAIL_DRIFT * 0.5)
        self.assertLess(criteria["sigma_dev"], 0.05)   # 6.469695e-09
        self.assertTrue(_isclose(criteria["sigma_ideal"], SIGMA_IDEAL))

    def test_verdict_not_converged_without_adaptation(self):
        # With gamma = 0 the estimator is inert, the plant goes to the
        # wrong equilibrium x = 6 and the verdict must be False.
        res = m.simulate(gamma=0.0)
        converged, criteria = m.convergence_report(res)
        self.assertFalse(converged)
        self.assertGreater(criteria["tail_abs_pred"], 1e-4)
        self.assertGreater(abs(res["track_err"][-1] - 5.0), 0.0)


class TestClosedFormIdentities(unittest.TestCase):
    """Step 7 of the SKILL.md workflow, the closed-form cross-checks of
    the Euler marches, is exercised here."""

    def test_reference_model_closed_form_identity(self):
        # xm[k] = 1 - 0.99^k reproduces the Euler reference-model march
        # to float precision at every checked index.
        res = worked_run()
        for k in (0, 1, 100, 1000, 3000, 6000):
            self.assertAlmostEqual(res["xm"][k],
                                   m.reference_closed_form(k),
                                   delta=1e-12)
            self.assertAlmostEqual(res["xm"][k], 1.0 - 0.99 ** k,
                                   delta=1e-12)

    def test_filter_closed_form_identity(self):
        # Marching the low-pass filter from nu0 = 0 under the constant
        # input sigma_hat = 1 gives nu_k = 1 - 0.9^k exactly.
        nu = 0.0
        history = [nu]
        for _ in range(5000):
            nu = m.filter_step(nu, 1.0)
            history.append(nu)
        for k in (1, 10, 100, 1000, 4999):
            self.assertAlmostEqual(history[k], 1.0 - 0.9 ** k,
                                   delta=1e-12)
            self.assertAlmostEqual(
                history[k], m.filter_closed_form(0.0, 1.0, OMEGA_C, DT, k),
                delta=1e-12)

    def test_no_adaptation_guard_closed_form(self):
        # With gamma = 0 the plant march matches 6*(1 - 0.995^k) within
        # 1e-9 and the tracking error settles at 5.0: without the
        # low-pass-filtered adaptation the plant converges to the wrong
        # equilibrium x = 6.
        res = m.simulate(gamma=0.0)
        for k in (100, 1000, 3000, 6000):
            self.assertAlmostEqual(res["x"][k],
                                   m.no_adaptation_closed_form(k),
                                   delta=1e-9)
        self.assertAlmostEqual(res["x"][-1], 6.0, delta=1e-6)
        self.assertLess(abs(res["track_err"][-1] - 5.0), 1e-3)

    def test_reference_loop_stability_identity(self):
        # The linearized (x, nu) reference loop at perfect adaptation
        # has trace a_p - omega_c = -10.5 and determinant -a_m*omega_c
        # = 10.0: stable signs (trace < 0, det > 0) for omega_c > a_hi.
        trace = PLANT_A - OMEGA_C
        det = -A_M * OMEGA_C
        self.assertAlmostEqual(trace, -10.5, delta=1e-12)
        self.assertAlmostEqual(det, 10.0, delta=1e-12)
        self.assertLess(trace, 0.0)
        self.assertGreater(det, 0.0)
        self.assertGreater(OMEGA_C, m.A_HI)

    def test_l1_norm_admissibility_identity(self):
        # Step 3 of the workflow: the numerical integral of the filtered
        # plant impulse response g(t) = b*omega_c/(omega_c - 1)*(e^-t -
        # e^(-omega_c*t)) equals b/|a_m| = 2.0 within 1e-4, and the
        # admissibility products (a_p - a_m)/|a_m| = 0.5 (worked) and
        # (a_hi - a_m)/|a_m| = 0.75 (prior corner) both sit below 1.
        def impulse(t):
            return (B * OMEGA_C / (OMEGA_C - 1.0) *
                    (math.exp(-t) - math.exp(-OMEGA_C * t)))

        h = 1e-4
        n = int(20.0 / h)
        integral = sum(impulse((i + 0.5) * h) for i in range(n)) * h
        self.assertAlmostEqual(integral, B / abs(A_M), delta=1e-4)
        self.assertLess((PLANT_A - A_M) / abs(A_M), 1.0)   # 0.5
        self.assertLess((m.A_HI - A_M) / abs(A_M), 1.0)    # 0.75


class TestTradeoffStudies(unittest.TestCase):
    """Steps 4 and 5 of the SKILL.md workflow applied to the guard runs:
    the slow-filter tradeoff and the adaptation-rate study of the
    guaranteed-transient-response bound."""

    def test_slow_filter_tradeoff(self):
        # At omega_c = 0.5 rad/s the loop still converges but max |track
        # error| = 1.555849 is more than 2.5x the omega_c = 10 value
        # 0.560772: the filter bandwidth sets the transient bound.
        res = m.simulate(omega_c=0.5)
        converged, _ = m.convergence_report(res)
        self.assertTrue(converged)
        self.assertTrue(_isclose(res["max_abs_track"], 1.555849,
                                 rel_tol=1e-2))
        self.assertGreater(res["max_abs_track"], 2.5 * 0.560772)

    def test_adaptation_rate_study_converges_and_monotone(self):
        # Every rate in (10, 40, 160, 1000) converges (tail |xt| below
        # 1e-4) and max |track error| decreases monotonically with the
        # rate: 0.5607716796, 0.3349860564, 0.2049952822, 0.1595401164.
        anchors = [0.5607716796, 0.3349860564, 0.2049952822, 0.1595401164]
        maxima = []
        for gamma in (10.0, 40.0, 160.0, 1000.0):
            res = m.simulate(gamma=gamma)
            self.assertLess(res["tail_abs_pred"], 1e-4)
            maxima.append(res["max_abs_track"])
        for got, anchor in zip(maxima, anchors):
            self.assertTrue(_isclose(got, anchor, rel_tol=1e-3))
        self.assertTrue(all(b < a for a, b in zip(maxima, maxima[1:])))
        # The 4x rate step from 10 to 40 cuts the transient bound by
        # 40.26 percent (more than 20 percent).
        cut = 1.0 - maxima[1] / maxima[0]
        self.assertGreater(cut, 0.20)


class TestDeterminismAndPurity(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: identical inputs reproduce
    bitwise-identical histories and the module stays pure stdlib."""

    def test_simulate_determinism_bitwise(self):
        first = worked_run()
        second = worked_run()
        self.assertEqual(first["x"], second["x"])
        self.assertEqual(first["sigma_hat"], second["sigma_hat"])
        self.assertEqual(first["u"], second["u"])

    def test_logic_module_pure_stdlib_no_rng(self):
        logic_path = os.path.join(os.path.dirname(__file__),
                                  "l1_adaptive_control_logic.py")
        with open(logic_path) as fh:
            source = fh.read()
        self.assertNotIn("import random", source)
        self.assertNotIn("random.", source)
        self.assertNotIn("numpy", source)
        self.assertNotIn("import scipy", source)


class TestSimulateValidation(unittest.TestCase):
    """Step 8 of the workflow: non-physical scenario inputs are rejected
    with ValueError before any state is marched."""

    def test_simulate_invalid_a_m_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(a_m=0.0)
        with self.assertRaises(ValueError):
            m.simulate(a_m=0.5)

    def test_simulate_invalid_scenario_raises(self):
        with self.assertRaises(ValueError):
            m.simulate(gamma=-1.0)
        with self.assertRaises(ValueError):
            m.simulate(omega_c=0.0)
        with self.assertRaises(ValueError):
            m.simulate(sigma_b=0.0)
        with self.assertRaises(ValueError):
            m.simulate(b=0.0)
        with self.assertRaises(ValueError):
            m.simulate(dt=0.0)
        with self.assertRaises(ValueError):
            m.simulate(dt=-0.01)
        with self.assertRaises(ValueError):
            m.simulate(steps=1)
        with self.assertRaises(ValueError):
            m.simulate(plant_a=float("nan"))


if __name__ == "__main__":
    unittest.main()

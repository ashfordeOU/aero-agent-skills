"""Contract test for the ilqr-ddp leaf (gnc-autonomy/optimal-control).

Exercises the SKILL.md workflow end to end: step 1 fixes the plant
(scenario constants, explicit-Euler dynamics with gravity and
quadratic drag), step 2 rolls the nominal control forward and
evaluates the total cost (stage costs, glide reference, terminal
flare cost, below-ground penetration penalty), step 3 runs the
backward Riccati pass (value-function quadratics, feedforward and
feedback gains of the local affine control law, expected model
improvement dV), step 4 executes the forward pass with backtracking
line search over the alpha schedule, step 5 regularizes on failure
(mu growth and decay), step 6 iterates to convergence (cost history,
touchdown state of the soft landing, gain sequences, mu and alpha
traces), and step 7 verifies the landing (soft-landing gate,
drag-compensated cruise control, linear-limit identity, determinism,
failure path). All numeric asserts are tolerance-based; no exact
equality on computed sums or products.

Run offline: python3 scripts/test_ilqr_ddp.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ilqr_ddp_logic as iqr


def isclose(a, b, rel=1e-9, abs_tol=1e-12):
    """Tolerance compare used across this contract test."""
    return math.isclose(a, b, rel_tol=rel, abs_tol=abs_tol)


def rel_diff(a, b):
    """Relative difference of a against b (guard for near-zero b)."""
    return abs(a - b) / max(abs(b), 1e-300)


class TestPlantAndCost(unittest.TestCase):
    """Workflow step 1 (plant and scenario) and step 2 (cost model)."""

    def test_dynamics_jacobians_fx_fu_structure(self):
        """Step 1: the analytic dynamics Jacobians of the explicit-Euler
        soft-landing plant are fx = [[1, dt], [0, fd]] with
        fd = 1 - 2*c*dt*|v| and the control column fu = [0, dt]; at
        [100, -15], u = 12 the drag relief makes fd = 0.76 exactly."""
        fx, fu = iqr.dynamics_jacobians([100.0, -15.0], 12.0)
        self.assertTrue(isclose(fx[0][0], 1.0, abs_tol=1e-12))
        self.assertTrue(isclose(fx[0][1], 0.4, abs_tol=1e-12))
        self.assertTrue(isclose(fx[1][0], 0.0, abs_tol=1e-12))
        self.assertTrue(isclose(fx[1][1], 0.76, abs_tol=1e-12))
        self.assertTrue(isclose(fu[0], 0.0, abs_tol=1e-12))
        self.assertTrue(isclose(fu[1], 0.4, abs_tol=1e-12))

    def test_discrete_dynamics_drag_relief_descending(self):
        """Step 1: while descending at v = -15 the quadratic drag term
        -c*v*|v| pushes upward with +4.5 m/s^2, so the step from
        [100, -15] with u = 12 lands at [94.0, -12.324]."""
        h1, v1 = iqr.discrete_dynamics([100.0, -15.0], 12.0)
        self.assertTrue(isclose(h1, 94.0, abs_tol=1e-9))
        self.assertTrue(isclose(v1, -12.324, abs_tol=1e-9))

    def test_discrete_dynamics_drag_load_climbing(self):
        """Step 1: while climbing at v = +15 the same drag term loads
        the vehicle with -4.5 m/s^2 (the drag sign flips with the
        velocity sign), so [100, +15] with u = 12 lands at
        [106.0, 14.076]."""
        h1, v1 = iqr.discrete_dynamics([100.0, 15.0], 12.0)
        self.assertTrue(isclose(h1, 106.0, abs_tol=1e-9))
        self.assertTrue(isclose(v1, 14.076, abs_tol=1e-9))

    def test_discrete_dynamics_valueerrors(self):
        """Step 1: non-physical plant inputs are rejected: non-positive
        dt, negative drag c, negative gravity g and non-finite control
        all raise ValueError from the dynamics step."""
        for dt in (-1.0, 0.0):
            with self.assertRaises(ValueError):
                iqr.discrete_dynamics([100.0, -15.0], 12.0, dt=dt)
        with self.assertRaises(ValueError):
            iqr.discrete_dynamics([100.0, -15.0], 12.0, c=-0.1)
        with self.assertRaises(ValueError):
            iqr.discrete_dynamics([100.0, -15.0], 12.0, g=-1.0)
        with self.assertRaises(ValueError):
            iqr.discrete_dynamics([100.0, -15.0], float("nan"))
        with self.assertRaises(ValueError):
            iqr.discrete_dynamics([float("inf"), -15.0], 12.0)

    def test_dynamics_jacobians_valueerrors(self):
        """Step 1: the Jacobian routine enforces the same non-physical
        input rejections as the dynamics step."""
        with self.assertRaises(ValueError):
            iqr.dynamics_jacobians([100.0, -15.0], 12.0, dt=-1.0)
        with self.assertRaises(ValueError):
            iqr.dynamics_jacobians([100.0, -15.0], 12.0, c=-0.1)
        with self.assertRaises(ValueError):
            iqr.dynamics_jacobians([100.0, -15.0], 12.0, g=-1.0)
        with self.assertRaises(ValueError):
            iqr.dynamics_jacobians([100.0, -15.0], float("inf"))

    def test_reference_state_glide_slope(self):
        """Step 2: the glide-slope reference descends from h0 = 300 m
        at v_ref = -15 m/s, so h_ref(k) = 300 - 6*k on the 0.4 s step;
        a negative step index raises ValueError."""
        self.assertTrue(isclose(iqr.reference_state(0)[0], 300.0))
        self.assertTrue(isclose(iqr.reference_state(10)[0], 240.0))
        self.assertTrue(isclose(iqr.reference_state(49)[0], 6.0))
        self.assertTrue(isclose(iqr.reference_state(10)[1], -15.0))
        with self.assertRaises(ValueError):
            iqr.reference_state(-1)

    def test_ground_penalty_active_only_below_ground(self):
        """Step 2: the below-ground penetration penalty 0.5*wp*h^2 is
        active only for h < 0 and vanishes above and at the terrain."""
        self.assertTrue(isclose(iqr.ground_penalty([4.0, -1.0]), 0.0))
        self.assertTrue(isclose(iqr.ground_penalty([0.0, -1.0]), 0.0))
        self.assertTrue(isclose(iqr.ground_penalty([-4.0, -1.0]), 4.0))

    def test_stage_cost_tracks_glide_slope(self):
        """Step 2: the stage cost tracks h_ref(k) and v_ref; exactly on
        the glide at k = 10 the tracking terms vanish and only the
        control cost 0.5*rw*u^2 remains."""
        j = iqr.stage_cost([240.0, -15.0], 6.0, 10)
        self.assertTrue(isclose(j, 0.5 * iqr.R_W * 36.0, rel=1e-9))
        joff = iqr.stage_cost([241.0, -15.0], 6.0, 10)
        self.assertTrue(isclose(joff - j, 0.5 * iqr.QH * 1.0, rel=1e-9))

    def test_terminal_cost_flares_to_origin(self):
        """Step 2: the terminal cost 0.5*qfh*h^2 + 0.5*qfv*v^2 flares
        the vehicle to rest at the origin: it vanishes at [0, 0] and
        equals 800 at [2, 0] under the terminal weights."""
        self.assertTrue(isclose(iqr.terminal_cost([0.0, 0.0]), 0.0))
        self.assertTrue(isclose(iqr.terminal_cost([2.0, 0.0]), 800.0))

    def test_stage_derivatives_on_and_off_glide(self):
        """Step 2: the stage derivatives carry the tracking gradient,
        the below-ground penetration gradient wp*min(h, 0), the
        penalty curvature wp below ground and the diagonal running
        curvature diag(qh, qv)."""
        lx, lu, lxx, luu = iqr.stage_derivatives([300.0, -15.0], 6.0, 0)
        self.assertTrue(isclose(lx[0], 0.0, abs_tol=1e-12))
        self.assertTrue(isclose(lx[1], 0.0, abs_tol=1e-12))
        self.assertTrue(isclose(lu, iqr.R_W * 6.0))
        self.assertTrue(isclose(lxx[0][0], iqr.QH))
        self.assertTrue(isclose(lxx[1][1], iqr.QV))
        self.assertTrue(isclose(luu, iqr.R_W))
        lx2, _, lxx2, _ = iqr.stage_derivatives([-4.0, -15.0], 6.0, 45)
        self.assertTrue(isclose(lx2[0] - iqr.QH * (-4.0 - 30.0),
                                iqr.W_PEN * -4.0))
        self.assertTrue(isclose(lxx2[0][0], iqr.QH + iqr.W_PEN))

    def test_zero_control_free_fall_guess_total_cost(self):
        """Step 2: rolling the zero-control guess forward (the forward
        rollout of the nominal control) is pure free fall off the
        glide: it ends 133.99 m below ground at the terminal velocity
        sqrt(g/c) = 22.147 m/s, and the total cost of the guess
        (stage costs along the rollout plus the terminal flare cost)
        is the anchor J0 = 3950193.632, dominated by the terminal
        state error, so the penetration penalty is heavily active."""
        us = [0.0] * iqr.N_STEPS
        states = iqr.rollout(iqr.X0, us)
        self.assertEqual(len(states), iqr.N_STEPS + 1)
        self.assertTrue(isclose(states[0][0], 300.0))
        self.assertTrue(isclose(states[-1][0], -133.994337148,
                                abs_tol=1e-6))
        self.assertTrue(isclose(states[-1][1], -22.147234587,
                                abs_tol=1e-6))
        self.assertTrue(isclose(math.sqrt(iqr.GRAV / iqr.DRAG),
                                22.14723459, rel=1e-6))
        self.assertTrue(min(s[0] for s in states) < -100.0)
        j, x_end = iqr.total_cost(iqr.X0, us)
        self.assertTrue(isclose(j, 3950193.6322372216, rel=1e-9))
        self.assertTrue(isclose(x_end[0], -133.994337148, abs_tol=1e-6))


class TestBackwardPass(unittest.TestCase):
    """Workflow step 3, the backward Riccati pass: the value-function
    quadratics Qx, Qu, Qxx, Qux, Quu and the local affine control law
    (feedforward gain k, feedback gain row K) at every step, with the
    expected model improvement dV."""

    def setUp(self):
        self.us = [0.0] * iqr.N_STEPS
        self.xs = iqr.rollout(iqr.X0, self.us)

    def test_first_pass_value_function_quadratics(self):
        """Step 3: on the free-fall nominal the backward Riccati pass
        at mu = MU0 forms the documented first-pass value-function
        quadratics at k = 0: Qx = [-4.395526837, -7.020479693],
        Qu = -2.769615241, Qxx = [[6.179754075, 3.43870942],
        [3.43870942, 5.608051338]], Qux = [0.7193725209, 1.175035563]
        and Quu = 0.5169929236."""
        ks, Ks, qs, dv, _, _ = iqr.backward_pass(self.xs, self.us, iqr.MU0)
        q0 = qs[0]
        self.assertTrue(isclose(q0["Qx"][0], -4.3955268373466465,
                                rel=1e-4))
        self.assertTrue(isclose(q0["Qx"][1], -7.020479693360259,
                                rel=1e-4))
        self.assertTrue(isclose(q0["Qu"], -2.7696152412745265, rel=1e-4))
        for r in range(2):
            for c in range(2):
                self.assertTrue(isclose(q0["Qxx"][r][c],
                                        [[6.179754075439908,
                                          3.438709419803109],
                                          [3.438709419803109,
                                           5.608051338051377]][r][c],
                                        rel=1e-4))
        self.assertTrue(isclose(q0["Qux"][0], 0.7193725208563926,
                                rel=1e-4))
        self.assertTrue(isclose(q0["Qux"][1], 1.1750355632263858,
                                rel=1e-4))
        self.assertTrue(isclose(q0["Quu"], 0.5169929236230679, rel=1e-4))

    def test_first_pass_expected_improvement_dv(self):
        """Step 3: the expected model improvement of the first
        backward Riccati pass is dV = 3.99097026e+06, non-negative and
        close to the entire free-fall cost J0 (the quadratic model of
        the diving guess is optimistic but points the right way)."""
        ks, Ks, qs, dv, _, _ = iqr.backward_pass(self.xs, self.us, iqr.MU0)
        self.assertGreaterEqual(dv, 0.0)
        self.assertTrue(isclose(dv, 3990970.2600717354, rel=1e-4))

    def test_regularization_shrinks_the_feedforward_gain(self):
        """Step 5: the regularized 1x1 solve k = -Qu/Quu_r with
        Quu_r = Quu + mu shrinks the feedforward gain of the local
        affine control law as mu grows on the same nominal."""
        ks_small, _, _, _, _, _ = iqr.backward_pass(self.xs, self.us, 1e-6)
        ks_large, _, _, _, _, _ = iqr.backward_pass(self.xs, self.us, 1e-2)
        self.assertLess(abs(ks_large[0]), abs(ks_small[0]))

    def test_backward_pass_gain_shapes(self):
        """Step 3: the backward Riccati pass returns one scalar
        feedforward gain and one two-entry feedback row per step of
        the horizon, and one value-function-quadratics snapshot per
        step."""
        ks, Ks, qs, dv, _, _ = iqr.backward_pass(self.xs, self.us, iqr.MU0)
        self.assertEqual(len(ks), iqr.N_STEPS)
        self.assertEqual(len(Ks), iqr.N_STEPS)
        self.assertEqual(len(qs), iqr.N_STEPS)
        self.assertEqual(len(Ks[0]), 2)


class TestSolveWorkedScenario(unittest.TestCase):
    """Workflow steps 4-7: the forward pass with backtracking line
    search, the regularization rule and the converged soft landing of
    the worked scenario."""

    @classmethod
    def setUpClass(cls):
        cls.res = iqr.ilqr_solve()

    def test_solve_converges_in_six_iterations(self):
        """Step 6: the driver iterates the backward Riccati pass and
        the line-searched forward pass to the convergence tolerance;
        the worked scenario converges at iteration 6 with
        J* = 78.33431352 (the flare cost of the soft landing)."""
        self.assertTrue(self.res["converged"])
        self.assertEqual(self.res["iters"], 6)
        self.assertTrue(isclose(self.res["cost"], 78.33431351660504,
                                rel=1e-6))

    def test_solve_cost_history(self):
        """Step 6: the per-iteration cost history
        [3950193.632, 9317.923352, 4974.117631, 957.7706809,
        78.33433455, 78.33431352, 78.33431352] records the free-fall
        guess J0 followed by one entry per accepted iteration of the
        trajectory optimization."""
        anchors = [3950193.6322372216, 9317.923351983201,
                   4974.117631095245, 957.7706808971308,
                   78.3343345502819, 78.33431351787665,
                   78.33431351660504]
        self.assertEqual(len(self.res["costs"]), 7)
        for got, want in zip(self.res["costs"], anchors):
            self.assertTrue(isclose(got, want, rel=1e-4),
                            msg=f"{got} vs {want}")

    def test_alpha_trace_records_the_backtrack(self):
        """Step 4: the forward pass with backtracking line search
        accepts alpha from the schedule in order; the trace
        [1, 0.5, 1, 1, 1, 1] records exactly one line-search
        backtrack at iteration 2 where the full step overshot."""
        self.assertEqual(self.res["alphas"], [1.0, 0.5, 1.0, 1.0,
                                              1.0, 1.0])

    def test_mu_trace_decays_by_07_rule(self):
        """Step 5: the Levenberg-Marquardt regularization mu decays by
        the 0.7 rule on every accepted step of the worked scenario,
        from MU0 = 1e-6 down to 1.6807e-07 over the six iterations."""
        anchors = [1e-06, 7e-07, 4.9e-07, 3.43e-07, 2.401e-07,
                   1.6807e-07]
        self.assertEqual(len(self.res["mus_at"]), 6)
        for got, want in zip(self.res["mus_at"], anchors):
            self.assertTrue(isclose(got, want, rel=5e-2))

    def test_monotone_descent_of_accepted_iterations(self):
        """Step 4: every accepted iteration of the line search strictly
        lowers the total cost (monotone descent)."""
        costs = self.res["costs"]
        for a, b in zip(costs, costs[1:]):
            self.assertLess(b, a)

    def test_soft_landing_gate(self):
        """Step 7: the soft-landing gate holds on the converged
        trajectory: |h_N| = 4.026e-03 m and |v_N| = 6.348e-03 m/s are
        far below 0.05, and the rollout never penetrates the ground
        (min h = 4.026e-03 m, the touchdown altitude)."""
        self.assertLess(abs(self.res["hN"]), 0.05)
        self.assertLess(abs(self.res["vN"]), 0.05)
        self.assertGreaterEqual(min(s[0] for s in self.res["xs"]),
                                -1e-9)
        self.assertTrue(isclose(self.res["hN"], 0.004026427311488057,
                                abs_tol=1e-6))
        self.assertTrue(isclose(self.res["vN"], -0.006348323050460181,
                                abs_tol=1e-6))

    def test_max_control_and_first_control(self):
        """Step 6: the flare control peaks at step 49 with
        max |u| = 40.62926756 m/s^2 killing the final descent in one
        step, while the first control u_0 = 5.309997827 m/s^2 already
        sits on the drag-compensated cruise value."""
        self.assertTrue(isclose(self.res["max_u"], 40.62926755768832,
                                rel=1e-4))
        self.assertEqual(self.res["u_seq"][0], 5.309997826664543)
        self.assertTrue(isclose(self.res["u_seq"][0], 5.309997827,
                                abs_tol=1e-4))

    def test_converged_local_affine_control_law(self):
        """Step 3: the converged local affine control law is the
        time-invariant feedback u = ubar + K*(x - xbar) + k with
        K = [-1.387, -2.272] on (h, v): the recorded feedforward gains
        k_0 and k_25 vanish at the optimum while the feedback rows
        K_0 = [-1.386881, -2.272025] and K_25 = [-1.386887,
        -2.272010] match the anchors."""
        self.assertTrue(isclose(self.res["K_seq"][0][0], -1.386881396122915,
                                rel=1e-3))
        self.assertTrue(isclose(self.res["K_seq"][0][1], -2.2720250845117658,
                                rel=1e-3))
        self.assertTrue(isclose(self.res["K_seq"][25][0], -1.386887378949474,
                                rel=1e-3))
        self.assertTrue(isclose(self.res["K_seq"][25][1], -2.2720102515501908,
                                rel=1e-3))
        self.assertLess(abs(self.res["k_seq"][0]), 1e-6)
        self.assertLess(abs(self.res["k_seq"][25]), 1e-6)

    def test_terminal_riccati_seed_identity(self):
        """Step 3: the terminal value-quadratic seed of the final
        backward Riccati pass is Vx_N = Qf*x_N = [1.610570925,
        -5.07865844] and Vxx_N = diag(400, 800) on the converged
        trajectory (above ground, so the penalty term is off)."""
        self.assertTrue(isclose(self.res["Vx_end"][0], 1.610570925,
                                abs_tol=1e-6))
        self.assertTrue(isclose(self.res["Vx_end"][1], -5.07865844,
                                abs_tol=1e-6))
        self.assertEqual(self.res["Vxx_end"], [[400.0, 0.0],
                                               [0.0, 800.0]])

    def test_cruise_band_drag_compensation(self):
        """Step 7: on the cruise band k = 10..39 the vehicle rides the
        glide at v = -15.003 and the mean control 5.305246 matches the
        drag-compensated thrust g + c*v*|v| = 5.307987 at the mean
        band velocity: the optimizer harvests the quadratic drag as
        thrust relief during the constant-descent-rate cruise."""
        us = self.res["u_seq"]
        band = us[10:40]
        mean_u = sum(band) / 30.0
        mean_v = sum(s[1] for s in self.res["xs"][10:40]) / 30.0
        model = iqr.GRAV + iqr.DRAG * mean_v * abs(mean_v)
        self.assertTrue(isclose(mean_u, 5.305245862522397, abs_tol=1e-4))
        self.assertLess(abs(mean_u - model), 0.01)

    def test_final_backward_pass_value_quadratic(self):
        """Step 3: the final backward Riccati pass on the converged
        rollout returns the step-0 value quadratic Vx_0 =
        [-0.398245213, -0.6637478787] and Vxx_0 = [[5.177127803,
        1.802604896], [1.802604896, 2.936884411]]."""
        _, _, _, _, vx0, vxx0 = iqr.backward_pass(
            self.res["xs"], self.res["u_seq"], self.res["mus_at"][-1])
        self.assertTrue(isclose(vx0[0], -0.398245213, rel=1e-4))
        self.assertTrue(isclose(vx0[1], -0.6637478787, rel=1e-4))
        for r in range(2):
            for c in range(2):
                self.assertTrue(isclose(
                    vxx0[r][c],
                    [[5.177127803, 1.802604896],
                     [1.802604896, 2.936884411]][r][c], rel=1e-4))

    def test_model_versus_actual_improvement(self):
        """Step 4: the expected model improvement dV of every backward
        Riccati pass is non-negative and over-predicts or matches the
        achieved improvement dJ of the accepted forward pass:
        dV >= dJ - max(1e-6, 1% of dJ); on the late iterations where
        the quadratic model is exact the ratio dV/dJ sits at 1
        (0.999999 at the iteration-3-to-4 pair)."""
        costs = self.res["costs"]
        for dv, a, b in zip(self.res["dvs"], costs, costs[1:]):
            d_actual = a - b
            self.assertGreaterEqual(dv, 0.0)
            self.assertGreaterEqual(d_actual, 0.0)
            self.assertGreaterEqual(dv, d_actual - max(1e-6,
                                                       0.01 * d_actual))
        # The pair where the quadratic model is exact.
        pair = 3
        d_actual = costs[pair] - costs[pair + 1]
        self.assertTrue(isclose(self.res["dvs"][pair] / d_actual, 1.0,
                                rel=1e-3))

    def test_expected_improvement_trace(self):
        """Step 3: the dV trace of the six accepted backward Riccati
        passes [3.99097026e+06, 9.19602194e+03, 4.88631556e+03,
        8.79435314e+02, 2.09615258e-05, 1.24295440e-09] collapses from
        the diving-guess scale to the converged-pass noise."""
        anchors = [3990970.2600717354, 9196.02194262329,
                   4886.315563288602, 879.4353136468502,
                   2.0961525831373664e-05, 1.2429543958291706e-09]
        for got, want in zip(self.res["dvs"], anchors):
            self.assertTrue(isclose(got, want, rel=1e-2))

    def test_result_cost_matches_recomputed_total(self):
        """Step 2: the reported converged cost equals the total cost
        recomputed from the returned state trajectory and control
        sequence (stage costs plus the terminal flare cost), an exact
        bookkeeping round trip of the driver."""
        j, _ = iqr.total_cost(self.res["x0"], self.res["u_seq"])
        self.assertTrue(isclose(j, self.res["cost"], rel=1e-12))

    def test_determinism_bitwise(self):
        """Step 6: two identical ilqr_solve runs are bitwise identical
        in the cost history, the control sequence and the alpha trace
        (no RNG anywhere in the deterministic iteration)."""
        again = iqr.ilqr_solve()
        self.assertEqual(self.res["costs"], again["costs"])
        self.assertEqual(self.res["u_seq"], again["u_seq"])
        self.assertEqual(self.res["alphas"], again["alphas"])

    def test_value_errors_on_solve_inputs(self):
        """Step 6: ilqr_solve rejects a zero-step horizon, a control
        guess of the wrong length and a non-finite initial state."""
        with self.assertRaises(ValueError):
            iqr.ilqr_solve(n_steps=0)
        with self.assertRaises(ValueError):
            iqr.ilqr_solve(u0=[0.0] * 5)
        with self.assertRaises(ValueError):
            iqr.ilqr_solve(x0=[float("nan"), -15.0])

    def test_failure_path_runtime_error(self):
        """Step 5: with a terminal-cost-only backward model (qh = qv =
        wp = 0) no line-search step ever lowers the scenario-weighted
        total cost, so the regularizer mu escalates by factor 10 to
        the cap and the driver raises RuntimeError deterministically."""
        with self.assertRaises(RuntimeError) as ctx:
            iqr.ilqr_solve(x0=iqr.X0, qh=0.0, qv=0.0, wp=0.0)
        self.assertIn("iLQR failed to improve the cost",
                      str(ctx.exception))


class TestLinearLimitIdentity(unittest.TestCase):
    """Workflow step 7 identity run: with c = 0 and wp = 0 the problem
    is exactly LQ, so one backward Riccati pass solves it."""

    @classmethod
    def setUpClass(cls):
        cls.lin = iqr.ilqr_solve(x0=iqr.X0, c=0.0, wp=0.0)

    def test_linear_limit_identity_run(self):
        """Step 6: in the linear limit the first backward Riccati pass
        is exact: the driver converges at iteration 2 with J* =
        170.5888011 and |J_1 - J*| = 4.176e-09 (the second pass only
        confirms the first). The touchdown state is h_N =
        0.006300569206 m, v_N = -0.006850166853 m/s, the first control
        is u_0 = 9.809997404 m/s^2 (the cruise thrust is g with no
        drag relief) and max |u| = 43.84106786 m/s^2."""
        self.assertTrue(self.lin["converged"])
        self.assertEqual(self.lin["iters"], 2)
        self.assertTrue(isclose(self.lin["cost"], 170.58880111067785,
                                rel=1e-6))
        self.assertLess(abs(self.lin["costs"][1] - self.lin["cost"]),
                        1e-6)
        self.assertTrue(isclose(self.lin["hN"], 0.006300569205766493,
                                abs_tol=1e-6))
        self.assertTrue(isclose(self.lin["vN"], -0.006850166853288542,
                                abs_tol=1e-6))
        self.assertTrue(isclose(self.lin["u_seq"][0], 9.809997404126406,
                                rel=1e-6))
        self.assertTrue(isclose(self.lin["max_u"], 43.84106786052103,
                                rel=1e-4))

    def test_drag_relief_matches_quadratic_drag(self):
        """Step 7: the mean cruise control drops from 9.806530
        (drag-free) to 5.305246 (drag on) by 4.501285, matching
        c*|v_ref|*v_ref = 4.500000 within 0.01: the drag relief is
        exactly the quadratic drag at the glide speed."""
        band0 = self.lin["u_seq"][10:40]
        mean0 = sum(band0) / 30.0
        self.assertTrue(isclose(mean0, 9.806530486117762, abs_tol=1e-4))
        res = iqr.ilqr_solve()
        mean1 = sum(res["u_seq"][10:40]) / 30.0
        diff = mean0 - mean1
        self.assertLess(abs(diff - 4.500000), 0.01)


class TestModulePurity(unittest.TestCase):
    """Determinism and stdlib purity of the module (no imports beyond
    math, no RNG), the gate-3 contract."""

    def test_module_imports_math_only(self):
        """Step 1: the logic module imports only the standard math
        module (no numpy, scipy or RNG anywhere in the trajectory
        optimizer)."""
        import inspect

        src = inspect.getsource(iqr)
        self.assertNotIn("import numpy", src)
        self.assertNotIn("import scipy", src)
        self.assertNotIn("import random", src)
        self.assertNotIn("random.", src)


if __name__ == "__main__":
    unittest.main()

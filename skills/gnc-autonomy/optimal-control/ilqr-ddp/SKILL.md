---
name: ilqr-ddp
description: "Use when you must run iterative LQR / differential dynamic programming (ilqr-ddp) on a nonlinear discrete-time system: roll the nominal control forward through the two-state soft-landing dynamics under gravity and quadratic drag, run the backward Riccati pass that forms the value-function quadratics Qx, Qu, Qxx, Qux, Quu and the local affine control law u = ubar + K(x - xbar) + k at each step, and execute the forward pass with backtracking line search and regularization until the total cost converges. Produces the converged control sequence, the touchdown state of the constant-descent-rate landing, the feedforward and feedback gain sequences, the per-iteration cost, alpha and mu traces, and the model-versus-actual improvement comparison gating the optimal soft-landing trajectory. Trigger: ilqr-ddp, differential dynamic programming, iterative LQR, backward Riccati pass, local affine control law, forward rollout, nonlinear soft-landing flare."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: optimal-control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: optimal-control
  tags: [ilqr-ddp, differential-dynamic-programming, iterative-lqr, backward-riccati-pass, forward-rollout, local-affine-control-law]
  version: 0.1.0
  author: Aero Agent Skills
---

# Iterative LQR / Differential Dynamic Programming (gnc-autonomy/optimal-control/ilqr-ddp)

Use when you must run iterative LQR / differential dynamic programming
(ilqr-ddp) on a nonlinear discrete-time system: forward rollout of the
nominal control, a backward Riccati pass forming the value-function
quadratics and the local affine control law at every step, and a
forward pass with backtracking line search and Levenberg-Marquardt
regularization until the total cost converges. The canonical plant is
the two-state vertical soft-landing system (altitude h in m, velocity
v in m/s, positive up) under gravity and quadratic drag, control u the
thrust acceleration in m/s^2, explicit-Euler discretized; the scenario
is a constant-descent-rate glide at -15 m/s from 300 m down to a flare
that brings the vehicle to rest at the origin. This leaf fills the
algorithm class between the linear infinite-horizon gain design of
gnc-autonomy/optimal-control/lqr-design, the linear finite-horizon
quadratic-program step of gnc-autonomy/optimal-control/
model-predictive-control and the pseudospectral external-tool workflow
of gnc-autonomy/optimal-control/dymos-trajectory: a deterministic
stdlib trajectory optimizer for a nonlinear plant with no external
solver. It pairs with gnc-autonomy/optimal-control/bang-bang-control
(analytic minimum-time alternative for the double integrator) and the
static objective minimizers under cross-cutting/numerics/
optimization-algorithms, whose design objectives carry no dynamics
rollout.

## Domain quick reference

- Plant (explicit Euler, state [h, v], control u): h+ = h + dt*v,
  v+ = v + dt*(u - g - c*v*|v|). The drag term -c*v*|v| opposes the
  motion: descending (v < 0) it pushes up with c*v^2.
- Glide reference at step k: h_ref(k) = h0 + v_ref*dt*k at the
  constant descent rate v_ref = -15 m/s.
- Stage cost: l_k = 0.5*qh*(h - h_ref(k))^2 + 0.5*qv*(v - v_ref)^2 +
  0.5*rw*u^2 + pen(x), pen(x) = 0.5*wp*min(h, 0)^2 (below-ground
  penetration, active only under h = 0).
- Terminal cost: lf = 0.5*qfh*h^2 + 0.5*qfv*v^2 + pen(x), the flare
  to rest at the origin.
- Dynamics Jacobians at the rollout point: fx = [[1, dt], [0, fd]]
  with fd = 1 - 2*c*dt*|v|, control column fu = [0, dt].
- Backward Riccati step with Vx = [p, q], Vxx = [[a, b], [b, d]] from
  step k+1: Qx = lx + fx^T*Vx, Qu = lu + dt*q,
  Qxx = [[qh + a, e12], [e12, qv + e22]] with e12 = dt*a + fd*b,
  e22 = dt*e12 + fd*(dt*b + fd*d), Qux = [dt*b,
  dt*(dt*b + fd*d)], Quu = luu + dt^2*d. Regularized 1x1 solve with
  Quu_r = Quu + mu: k = -Qu/Quu_r (feedforward), K = -Qux/Quu_r
  (feedback row on h and v); value recursion uses the unregularized
  Quu; the expected model improvement is dV = -sum_k 0.5*Qu_k*k_k.
- Policy of the forward pass: u_k = ubar_k + K_k*(x_k - xbar_k) +
  alpha*k_k, stepped by the exact nonlinear dynamics; line search
  accepts the first alpha in [1, 0.5, 0.25, ...] that lowers the
  total cost (monotone descent), mu *= 0.7 on acceptance and mu *= 10
  on failure up to the cap where the driver raises RuntimeError.
- Convergence: |dJ| <= TOL*(1 + |J|) after an accepted iteration.
- Scenario constants: DT = 0.4 s, N = 50 steps (T = 20 s), g = 9.81
  m/s^2, c = 0.02 1/m, h0 = 300 m, v_ref = -15 m/s, Q = diag(1, 2),
  R = 0.05, Qf = diag(400, 800), wp = 0.5. SI units throughout.
- ARP4754A frames the certification context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the plant and the scenario: the module constants (dt = 0.4 s,
   N = 50 steps, gravity g, drag c, the glide h0 and v_ref, and the
   cost weights), then step the explicit-Euler dynamics with
   discrete_dynamics and check the Jacobians with
   dynamics_jacobians.
2. Roll the nominal control forward through the nonlinear plant with
   rollout, and evaluate the total cost of the rollout with
   total_cost over the stage costs (stage_cost, ground_penalty,
   reference_state) plus the terminal flare cost (terminal_cost).
   The default guess is the zero-control free fall, J0 = 3950193.632.
3. Run the backward Riccati pass with backward_pass: from the
   terminal value-quadratic seed Vx_N = Qf*x_N, Vxx_N = diag(qfh,
   qfv) it forms the per-step value-function quadratics Qx, Qu, Qxx,
   Qux, Quu, solves the regularized 1x1 gain system for the local
   affine control law (feedforward gain k, feedback gain row K) and
   returns the expected model improvement dV with the step-0 value
   quadratic Vx_0, Vxx_0.
4. Execute the forward pass with backtracking line search with
   forward_pass: try alpha in ALPHAS in order and accept the first
   alpha whose rollout total cost falls below the previous cost
   (monotone descent).
5. Regularize on failure: when no line-search step improves the
   total cost, grow the Levenberg-Marquardt regularization mu by
   factor 10 and repeat the backward Riccati pass; on acceptance
   decay mu by 0.7 floored at mu_min. Reaching the mu cap raises
   RuntimeError.
6. Iterate to convergence with ilqr_solve: repeat steps 3 to 5 until
   the relative cost change meets the tolerance, then read the
   converged control sequence u_0..u_{N-1} and state trajectory, the
   touchdown state of the soft landing, the per-step feedforward and
   feedback gain sequences, and the per-iteration cost, alpha, mu and
   dV traces.
7. Verify the landing: check the soft-landing gate (|h_N| and |v_N|
   below 0.05 m and m/s, trajectory never below ground), the
   drag-compensated cruise control on the glide band, the converged
   affine gains, the linear-limit identity at c = 0, wp = 0, run
   determinism and the failure path, then run the contract test.

## Worked example

Constant-descent-rate soft landing: x0 = [300, -15] on the glide,
zero-control free-fall guess. J0 = 3950193.632; the guess ends at
h = -133.994337 m, v = -22.147235 m/s (the terminal velocity
sqrt(g/c) = 22.14723459 m/s), 133.99 m below ground.

- Iteration trace: 3950193.632 -> 9317.923352 (alpha 1.0) ->
  4974.117631 (alpha 0.5: the line search backtracks) -> 957.7706809
  -> 78.33433455 -> 78.33431352 -> 78.33431352 (converged at
  iteration 6). Alphas [1, 0.5, 1, 1, 1, 1]; mu decays by the 0.7
  rule: [1e-06, 7e-07, 4.9e-07, 3.43e-07, 2.401e-07, 1.6807e-07].
- Model versus actual: iter 0 -> 1 dV = 3.99097026e+06 vs dJ =
  3.94087571e+06 (optimistic quadratic model over the diving guess,
  yet alpha 1.0 improves); iter 3 -> 4 dV = 8.79435314e+02 vs dJ =
  8.79436346e+02 (the model becomes exact, ratio 0.999999); the later
  pairs sit at ratios 0.9966 and 0.9775 at the 1e-5 and 1e-9 scales.
- Converged trajectory samples (k, h, v, u, h_ref): k = 0 (300.0000,
  -15.0000, 5.3100, 300.0000), k = 10 (240.0000, -15.0000, 5.3100,
  240.0000), k = 25 (149.9994, -15.0005, 5.3093, 150.0000), k = 35
  (89.9902, -15.0080, 5.2987, 90.0000), k = 45 (29.8345, -15.1351,
  5.1214, 30.0000), k = 49 (5.5536, -13.8739, 40.6293, 6.0000). The
  vehicle rides the glide to within millimeters through k = 45 with
  the drag-compensated cruise thrust u = 5.31 m/s^2 (g + c*v*|v| =
  9.81 - 4.5: drag relief of 4.5 m/s^2), then flares at k = 49 with
  u = 40.62926756 m/s^2, killing the last 13.87 m/s in one step.
- Touchdown: h_N = 0.004026427311 m, v_N = -0.00634832305 m/s
  (|h_N| = 4.026e-03 m, |v_N| = 6.348e-03 m/s); min h on the rollout
  is 4.026e-03 m: the trajectory never penetrates the ground. First
  control u_0 = 5.309997827 m/s^2; cruise band k = 10..39 mean
  u = 5.305246 vs g + c*v*|v| = 5.307987 at the mean band velocity
  -15.003355 (within 0.01).
- Converged local affine control law: k_0 = 7.252901285e-09 (zero at
  the optimum), K_0 = [-1.386881, -2.272025] on (h, v); k_25 =
  -1.428178568e-08, K_25 = [-1.386887, -2.272010]. The feedback row
  is essentially constant along the glide.
- Backward-pass quadratics on the free-fall guess at mu = 1e-6
  (k = 0): Qx = [-4.395526837, -7.020479693], Qu = -2.769615241,
  Qxx = [[6.179754075, 3.43870942], [3.43870942, 5.608051338]],
  Qux = [0.7193725209, 1.175035563], Quu = 0.5169929236. Final
  backward pass on the converged rollout: Vx_0 = [-0.398245213,
  -0.6637478787], Vxx_0 = [[5.177127803, 1.802604896],
  [1.802604896, 2.936884411]]; terminal seed Vx_N = Qf*x_N =
  [1.610570925, -5.07865844], Vxx_N = diag(400, 800).
- Linear-limit identity (c = 0, wp = 0): the problem is exactly LQ,
  converged at iterations = 2 with J* = 170.5888011 and |J_1 - J*| =
  4.176e-09; touchdown h_N = 0.006300569206 m, v_N =
  -0.006850166853 m/s; u_0 = 9.809997404 m/s^2 (cruise thrust is g
  with no drag relief); max |u| = 43.84106786 m/s^2. The mean cruise
  control drops from 9.806530 (c = 0) to 5.305246 (c = 0.02), a
  difference of 4.501285 that matches c*|v_ref|*v_ref = 4.500000
  within 0.01.
- Failure path: ilqr_solve with qh = 0.0, qv = 0.0, wp = 0.0
  (terminal cost only) raises RuntimeError("iLQR failed to improve
  the cost") once the regularizer reaches mu_max = 1e6.

## Verification

- Deterministic checks (contract test): dynamics_jacobians
  ([100.0, -15.0], 12.0) = ([[1, 0.4], [0, 0.76]], [0, 0.4]);
  discrete_dynamics([100, -15], 12) = [94.0, -12.324] (drag +4.5
  m/s^2 while descending) and ([100, +15], 12) = [106.0, 14.076]
  (drag -4.5 m/s^2 while climbing).
- Worked scenario: converged = True, iterations = 6, J* =
  78.33431352; soft-landing gate |h_N| = 4.026e-03 m < 0.05 m,
  |v_N| = 6.348e-03 m/s < 0.05 m/s, min h >= -1e-9 m; max |u| =
  40.62926756 at step 49; u_0 = 5.309997827 within 1e-4; K_0 and
  K_25 within 1e-3 per entry of the anchors; |k_0|, |k_25| < 1e-6.
- Linear-limit identity: ilqr_solve(x0, c = 0.0, wp = 0.0) returns
  converged = True at iterations = 2 with J* = 170.5888011 and
  |J_1 - J*| < 1e-6.
- ValueErrors: n_steps = 0 and a wrong-length u0 on ilqr_solve;
  non-finite x0; dt at -1.0 and 0.0, c at -0.1, g at -1.0 and a
  non-finite control on discrete_dynamics; k = -1 on
  reference_state.
- Failure path: ilqr_solve(x0, qh = 0.0, qv = 0.0, wp = 0.0) raises
  RuntimeError deterministically.
- Determinism: two identical runs are bitwise identical in costs,
  u_seq and alphas; stdlib math only, no RNG, no external processes.
- Run the contract test offline under both interpreters:
  python3 scripts/test_ilqr_ddp.py and the pyenv 3.13 hook
  interpreter (35 tests, all tolerance-based).

## Related leaves

- gnc-autonomy/optimal-control/lqr-design: the linear infinite-horizon
  algebraic gain design this leaf does not compute.
- gnc-autonomy/optimal-control/lqg-design: the dual-estimator
  output-feedback design this leaf does not compute.
- gnc-autonomy/optimal-control/model-predictive-control: the linear
  receding-horizon constrained step this leaf does not compute.
- gnc-autonomy/optimal-control/dymos-trajectory: the pseudospectral
  external-tool transcription this leaf does not compute.
- gnc-autonomy/optimal-control/bang-bang-control: the analytic
  minimum-time command this leaf does not compute.
- cross-cutting/numerics/optimization-algorithms: static design
  objective minimizers whose objectives carry no dynamics rollout.

## Pitfalls

- Reading the quoted k = 0 value-function quadratics (Qx =
  [-4.395526837, ...]) as the output of the FINAL backward pass: they
  are the first-pass quadratics on the free-fall guess (whose nominal
  ends below ground), reproduced by backward_pass on the zero-control
  rollout at mu = MU0; the converged pass outputs Vx_0 = [-0.398..., ]
  and the near-zero feedforward gains. The module reproduces both
  sets exactly; check which nominal a backward pass ran on before
  quoting its quadratics.
- Expecting dV/dJ to sit at 1 on every late iteration: the quadratic
  model is exact only where the pass magnitude is meaningful (ratio
  0.999999 at the iter-3-to-4 pair); at the 1e-5 and 1e-9 scales the
  ratios read 0.9966 and 0.9775, dominated by last-ulp noise. The
  contract asserts the exact pair and the inequality dV >= dJ - 1%
  slack on every pair.
- Treating the backward-pass weights as the acceptance weights: the
  run's qh/qv/rw/qfh/qfv/wp shape the backward quadratic model only,
  while the line-search acceptance cost and the reported cost history
  are the scenario-weighted total cost (the pinned total_cost /
  forward_pass signatures carry no weight parameters). This split is
  what makes the terminal-cost-only failure run deterministic.
- Forgetting the below-ground terms: the penetration penalty
  gradient wp*min(h, 0) enters Qx and the terminal seed when the
  nominal ends below ground (the free-fall guess ends at
  h = -133.994 m), while the penalty curvature is absent from the
  Qxx recursion per the pinned formula; both choices reproduce the
  documented anchors.
- Expecting alpha = 1 always: the dive-then-flare problem backtracks
  once (alpha 0.5 at iteration 2); the alpha trace is part of the
  deliverable, not a fixed step.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ilqr_ddp.py

35 tests covering: the explicit-Euler dynamics and Jacobians with
drag sign flip and ValueError rejections; the glide reference, stage,
terminal and penetration costs; the free-fall guess rollout and its
total cost J0; the backward Riccati pass value-function quadratics on
the free-fall guess and the value quadratic of the converged rollout;
the regularized gain solve; the worked-scenario convergence (6
iterations, cost history, alpha and mu traces, monotone descent, the
soft-landing gate, the cruise-band drag compensation, the converged
local affine control law, the model-versus-actual improvement
comparison, bitwise determinism); the linear-limit identity run; and
the deterministic failure path RuntimeError. Must pass under both
python3 and the pyenv 3.13 hook interpreter; all asserts are
tolerance-based.

## Compliance

- Standards referenced, not reproduced: ARP4754A (SAE, proprietary)
  frames the certification context; the iLQR/DDP relations above are
  standard engineering methodology, summary-only per
  standards-map.yaml. No standard text is reproduced.
- compliance: STANDARDS-REF, gated: false.

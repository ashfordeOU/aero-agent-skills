# Wave-44 leaf spec: ilqr-ddp (gnc-autonomy, optimal-control pack)

- Path: skills/gnc-autonomy/optimal-control/ilqr-ddp/
- Pack: optimal-control (present siblings bang-bang-control,
  dymos-trajectory, lqg-design, lqr-design, model-predictive-control;
  adjacent fence in cross-cutting/numerics/optimization-algorithms,
  whose static design-objective minimizers never touch a dynamics
  rollout).
- Provenance: wave-44 leaf-plan lines 92-100 (probe task-7 rank 1):
  "iterative LQR / differential dynamic programming for nonlinear
  discrete-time systems - forward rollout, backward Riccati pass (Qx,
  Qu, Qxx, Qxu, Quu), local affine control law, forward pass with
  backtracking line search/regularization; lqr-design infinite-horizon
  linear scalar-input only, MPC linear receding-horizon QP only, dymos
  pseudospectral external-tool only, optimization-algorithms static
  design objectives only (all quoted); arp4754a; magnitude L - largest
  leaf of the wave". Corpus tokens of the leaf:
  ilqr-ddp, differential-dynamic-programming, iterative-lqr,
  backward-riccati-pass.
- Claim fences (quoted from the sibling frontmatter and body at prep;
  none of them iterates an open-loop trajectory of a nonlinear
  discrete-time system through backward value-function quadratics):
  - lqr-design (this pack) OWNS the infinite-horizon Riccati design of
    a LINEAR scalar-input plant: its description reads "Use when you
    must design an LQR state-feedback gain matrix for a scalar-input
    two-state system such as spacecraft attitude control: solve the
    algebraic Riccati equation for the cost weights, compute the gain
    matrix, verify closed-loop stability of the regulated system",
    and its quick reference fixes the canonical plant as the linear
    form A = [[0, 1], [0, -a]] with the gain K = R^-1 B' P from the
    algebraic Riccati equation A'P + PA - P B R^-1 B' P + Q = 0: one
    static gain vector, time-invariant, no horizon, no rollout, no
    iteration. This leaf quotes no algebraic Riccati equation and
    produces no single steady gain vector; its Riccati-like object is
    the per-step backward pass of the finite-horizon value quadratic.
  - lqg-design (this pack) OWNS the linear-quadratic-Gaussian
    output-feedback compensator "for a two-state system whose state is
    not fully measurable: solve the regulator algebraic Riccati
    equation ... solve the filter (Kalman) algebraic Riccati equation
    ... assemble the dynamic output-feedback compensator ... verify
    the separation principle": two static ARE solutions, no trajectory
    iteration. This leaf is deterministic full-state trajectory
    optimization; no estimator, no compensator, no separation verdict.
  - model-predictive-control (this pack) OWNS the LINEAR receding-
    horizon QP: its description reads "design a model predictive
    control (MPC) receding horizon controller for a linear discrete
    time system such as a double integrator: choose the finite horizon
    quadratic cost with prediction horizon and control horizon,
    enforce input constraints and state constraints", producing "the
    first optimal control move from the small dense quadratic program"
    at each closed-loop step. This leaf is open-loop trajectory
    optimization of a NONLINEAR plant (quadratic drag term in the
    velocity channel), with no prediction-horizon QP, no active-set
    step, no constraint handling, and no receding-horizon loop.
  - dymos-trajectory (this pack) OWNS the pseudospectral EXTERNAL-TOOL
    workflow: its description reads "setting up and assessing
    pseudospectral trajectory optimization with Dymos: plan optimal-
    control problems as phases with collocation nodes", through
    scripts/dymos_logic.py on a Dymos installation. This leaf is pure
    stdlib discrete-time iteration with no external solver, no phase
    transcription, no collocation nodes and no Dymos.
  - bang-bang-control (this pack) OWNS the analytic time-optimal
    double-integrator command: switching curve, T* = 2*sqrt(d/a),
    closed-form rest-to-rest profile under a hard input limit. This
    leaf minimizes a running quadratic cost over a fixed horizon and
    never computes a switch point or a minimum-time maneuver.
  - optimization-algorithms (cross-cutting, adjacent fence) OWNS
    static unconstrained design-objective minimization: golden-section
    search, Newton on the derivative, gradient descent with Armijo
    backtracking, Nelder-Mead on a "scalar or multivariate design
    objective". Its objectives have no dynamics, no step index and no
    rollout; this leaf's cost is a functional of a 50-step trajectory
    whose stationarity is enforced by the backward pass, not a
    pointwise objective.
  Whole-tree greps at prep: the four distinctive tokens ilqr-ddp,
  differential-dynamic-programming, iterative-lqr and
  backward-riccati-pass each return ZERO hits in eval/hit1-corpus.yaml
  (grep count 0 per token), ZERO hits across skills/ and eval/
  (whole-tree grep count 0), and ZERO hits in the wave44-specs files
  written so far. GENUINE gnc-autonomy gap (fresh probe task-7 rank 1,
  GO): no leaf runs a nonlinear finite-horizon trajectory optimizer
  with a backward Riccati pass and a line-searched forward pass; this
  is the missing algorithm class between the linear infinite-horizon
  Riccati gain (lqr-design), the linear finite-horizon QP
  (model-predictive-control) and the pseudospectral external tool
  (dymos-trajectory).
- Standards id: arp4754a (reference-only, present in standards-map.yaml
  at line 38; SAE ARP is proprietary, name + paraphrase only, no
  reproduced text). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Run iterative LQR / differential dynamic programming (ilqr-ddp) on a
NONLINEAR discrete-time system in the exact form the leaf plan
mandates: the two-state vertical soft-landing plant (altitude h in m,
velocity v in m/s, positive up) under gravity and quadratic drag, with
control u the thrust acceleration in m/s^2 and the explicit Euler
discretization h+ = h + dt*v, v+ = v + dt*(u - g - c*v*|v|), the
drag opposing the motion. The scenario is a constant-descent-rate
soft landing: the stage cost tracks the glide slope h_ref(k) =
h0 + v_ref*dt*k at the constant descent rate v_ref = -15 m/s from
h0 = 300 m, the terminal cost flares the vehicle to rest at the
origin, and a quadratic below-ground penetration penalty
0.5*wp*min(h, 0)^2 keeps iterates above the terrain. The optimizer
iterates: (1) a forward rollout of the nominal control through the
nonlinear dynamics; (2) a backward Riccati pass from the terminal
value quadratic that forms, at every step, the value-function
quadratics Qx, Qu, Qxx, Qux, Quu of the local cost-to-go and the
local affine control law u = ubar + K*(x - xbar) + k, where k is the
feedforward gain and K the state-feedback gain row; (3) a forward
pass that rolls the affine policy forward with backtracking line
search over alpha in [1, 0.5, 0.25, ...] accepting the first alpha
that lowers the total cost, backed by Levenberg-Marquardt
regularization (mu added to Quu) that grows by factor 10 and repeats
the backward pass whenever no line-search step improves the cost,
until the total cost converges at the stated relative tolerance.
Produces the converged open-loop control sequence u_0..u_{N-1} and
state trajectory of the landing, the touchdown state (soft-landing
gate), the per-step feedforward and feedback gain sequences of the
converged local affine control law, the value-function quadratics of
the final backward pass, the per-iteration cost, alpha and mu traces,
the expected-model-improvement dV against the achieved improvement,
and the terminal value-quadratic seed, in SI units, that gate the
optimal soft-landing trajectory of the nonlinear plant. Does NOT do:
the infinite-horizon algebraic Riccati equation and the single gain
vector of a linear scalar-input plant (lqr-design); the dual-ARE
linear-quadratic-Gaussian compensator and separation principle
(lqg-design); a linear receding-horizon quadratic program with
prediction horizon, control horizon or active-set constraint handling
(model-predictive-control); pseudospectral phase transcription with
collocation nodes through an external tool (dymos-trajectory); the
time-optimal bang-bang switching curve of the double integrator
(bang-bang-control); or static golden-section, Newton, gradient or
simplex minimization of a design objective (optimization-algorithms).
Deterministic, offline, stdlib math only: explicit scalar arithmetic
(2 states, 1 input), no numpy, no scipy, no RNG, no external
processes.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes, no external solvers. Deterministic: plain explicit scalar
arithmetic in the pinned order below, no generator-sum float
reassociation. Module name ilqr_ddp.

Module constants (pin exactly; the worked scenario):
- DT = 0.4 (step, s), N_STEPS = 50 (horizon; T = 20 s),
  GRAV = 9.81 (m/s^2), DRAG = 0.02 (1/m),
  H0 = 300.0 (m), V_REF = -15.0 (m/s), X0 = [300.0, -15.0].
- QH = 1.0, QV = 2.0 (running state weights), R_W = 0.05 (control
  weight), QFH = 400.0, QFV = 800.0 (terminal weights),
  W_PEN = 0.5 (penetration penalty weight).
- MU0 = 1e-6 (initial regularization), MU_MIN = 1e-12,
  MU_MAX = 1e6 (cap; reaching it raises RuntimeError),
  ALPHAS = [1/2^i for i in 0..20], MAX_ITER = 150,
  TOL = 1e-7 (relative cost-change tolerance).

Plant and cost conventions (pin exactly; every function below derives
from these):
- Dynamics (explicit Euler, state [h, v], control u):
  h+ = h + dt*v; v+ = v + dt*(u - g - c*v*|v|). The drag term
  -c*v*|v| opposes the motion: descending (v < 0) it pushes up.
- Glide-slope reference at step k: h_ref(k) = h0 + v_ref*dt*k,
  v_ref(k) = v_ref (constant descent rate).
- Stage cost at step k: l_k = 0.5*qh*(h - h_ref(k))^2 +
  0.5*qv*(v - v_ref)^2 + 0.5*rw*u^2 + pen(x_k) with pen(x) =
  0.5*wp*min(h, 0)^2 (below-ground penetration, active only below
  h = 0). Terminal cost lf = 0.5*qfh*h^2 + 0.5*qfv*v^2 + pen(x) at
  x_N: the flare to rest at the origin.
- Dynamics Jacobians (analytic, evaluated at the rollout point):
  fx = [[1, dt], [0, fd]] with fd = 1 - 2*c*dt*|v| (the partial of
  -c*v*|v| in v), fu = [0, dt] (column).
- Stage derivatives at (x_k, u_k): lx = [qh*(h - h_ref) + wp*hn,
  qv*(v - v_ref)] with hn = min(h, 0); lu = rw*u;
  lxx = [[qh + (wp if h < 0 else 0), 0], [0, qv]]; luu = rw.
- Terminal seed of the backward pass at step N (x_N above ground in
  the converged run, so the penalty term is off there): Vx = [qfh*h_N,
  qfv*v_N] (= Qf*x_N), Vxx = diag(qfh, qfv).
- Backward Riccati step at index k (all scalar arithmetic; Vx = [p,
  q], Vxx = [[a, b], [b, d]] from step k+1):
  Qx = [lx0 + p, lx1 + dt*p + fd*q]       (fx^T Vx with fx^T = [[1,
  0], [dt, fd]])
  Qu = lu + dt*q
  Qxx = [[qh + a, e12], [e12, qv + e22]] with e12 = dt*a + fd*b and
  e22 = dt*e12 + fd*(dt*b + fd*d)
  Qux = [dt*b, dt*(dt*b + fd*d)]          (fu^T Vxx fx, a 1x2 row)
  Quu = luu + dt*dt*d                     (a scalar, rw > 0 so
  positive definite)
  Regularized 1x1 solve with Quu_r = Quu + mu:
  k = -Qu/Quu_r (feedforward gain), K = [-Qux0/Quu_r, -Qux1/Quu_r]
  (feedback gain row on h and v).
  Value updates with the UNregularized Quu:
  Vx = Qx + K^T*(Quu*k + Qu) + Qux^T*k
  Vxx = symmetrize(Qxx + Quu*K^T*K + K^T*Qux + Qux^T*K) by averaging
  off-diagonal pairs.
  The expected model improvement of the pass is
  dV = -sum_k 0.5*Qu_k*k_k (>= 0).
- Forward pass (policy rollout): from x0, u_k = ubar_k + K_k*(x_k -
  xbar_k) + alpha*k_k with xbar, ubar the current nominal rollout;
  state stepped by the exact nonlinear dynamics. Total cost of a
  rollout: sum of stage costs over k = 0..N-1 plus the terminal cost.
- Line search: try alpha in ALPHAS in order; accept the FIRST alpha
  with J(alpha) < J_prev. If none improves, mu *= 10 and the backward
  pass repeats (up to the mu cap; at the cap the driver raises
  RuntimeError). On acceptance mu *= 0.7 (floored at MU_MIN). Every
  accepted step strictly lowers J (monotone descent).
- Convergence: |dJ| <= TOL*(1 + |J_new|) after an accepted iteration
  declares convergence; the result records the iteration count.
  Iteration budget MAX_ITER.

Functions (public API, 12):
- discrete_dynamics(state, u, dt=DT, g=GRAV, c=DRAG) -> [h1, v1].
  ValueError if dt non-finite or <= 0, g non-finite or < 0, c
  non-finite or < 0, or any of h, v, u non-finite.
- dynamics_jacobians(state, u, dt=DT, g=GRAV, c=DRAG) -> (fx, fu)
  as pinned above; same ValueErrors as discrete_dynamics.
- reference_state(k, h0=H0, v_ref=V_REF, dt=DT) -> [h_ref(k),
  v_ref]. ValueError if k < 0.
- ground_penalty(state, wp=W_PEN) -> 0.5*wp*min(h, 0)^2.
- stage_cost(state, u, k, qh=QH, qv=QV, rw=R_W, wp=W_PEN) -> scalar.
- terminal_cost(state, qfh=QFH, qfv=QFV, wp=W_PEN) -> scalar.
- stage_derivatives(state, u, k, qh=QH, qv=QV, rw=R_W, wp=W_PEN) ->
  (lx, lu, lxx, luu) as pinned above.
- total_cost(x0, u_seq, dt=DT, g=GRAV, c=DRAG, wp=W_PEN) ->
  (J, x_end).
- rollout(x0, u_seq, dt=DT, g=GRAV, c=DRAG) -> list of N+1 states.
- forward_pass(x0, u_seq, xbar, k_seq, K_seq, alpha, dt=DT, g=GRAV,
  c=DRAG, wp=W_PEN) -> (J, states, controls) of the affine-policy
  rollout.
- backward_pass(xs, us, mu, dt=DT, g=GRAV, c=DRAG, qh=QH, qv=QV,
  rw=R_W, qfh=QFH, qfv=QFV, wp=W_PEN) -> (k_seq, K_seq, qs, dV,
  Vx_0, Vxx_0) with qs[k] the (Qx, Qu, Qxx, Qux, Quu) snapshot of
  step k and Vx_0, Vxx_0 the value quadratic at step 0.
- ilqr_solve(x0=X0, u0=None, dt=DT, g=GRAV, c=DRAG, n_steps=N_STEPS,
  qh=QH, qv=QV, rw=R_W, qfh=QFH, qfv=QFV, wp=W_PEN,
  max_iter=MAX_ITER, tol=TOL, mu0=MU0, mu_min=MU_MIN,
  mu_max=MU_MAX) -> result dict with keys x0, u_seq, xs, cost,
  costs (J0 plus one entry per accepted iteration), iters,
  converged, alphas, mus_at, dvs, k_seq, K_seq, q_first, Vx_end,
  Vxx_end, max_u, u0, hN, vN, min_v. Default u0 is the zero-control
  free-fall guess. ValueError if n_steps < 1, u0 length != n_steps,
  or any x0 entry non-finite. RuntimeError if the regularizer reaches
  mu_max without an improving step ("iLQR failed to improve the
  cost").

Private helper (module-internal): _hneg(h) returning min(h, 0) as a
float. Explicit scalar arithmetic throughout; no matrix library.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- fx structure: dynamics_jacobians([100.0, -15.0], 12.0) equals
  ([[1, 0.4], [0, 0.76]], [0, 0.4]) at the scenario dt = 0.4 (real
  anchor, exact to 0.000e+00): fd = 1 - 2*0.02*0.4*15 = 0.76.
- discrete_dynamics spot checks: ([100, -15], 12) -> [94.0, -12.324]
  (drag +4.5 m/s^2 upward while descending) and ([100, +15], 12) ->
  [106.0, 14.076] (drag -4.5 m/s^2 while climbing): the drag sign
  flips with the velocity sign (real anchor).
- Terminal Riccati seed: Vx_N = Qf*x_N = [1.610570925, -5.07865844]
  and Vxx_N = diag(400, 800) on the converged trajectory (real
  anchor; x_N is above ground, penalty off).
- Drag compensation closed form: steady descent at velocity v needs
  u = g + c*v*|v|; on the converged cruise band k = 10..39 the mean
  control 5.305246 equals g + c*v*|v| = 5.307987 at the mean band
  velocity -15.003355 within 0.01 (real anchor). Against the
  drag-free run (c = 0) the mean cruise control drops by 4.501285,
  matching c*|v_ref|*v_ref = 4.500000 within 0.01: the drag relief
  is exactly the quadratic drag at the glide speed.
- Linear-limit identity: with c = 0 AND wp = 0 the problem is exactly
  LQ (quadratic cost on affine dynamics), so the first backward pass
  is exact: ilqr_solve(x0, c=0.0, wp=0.0) returns converged=True at
  iterations = 2 with |J_1 - J*| = 4.176e-09 (real anchor; the
  second iteration only confirms the first).
- Model-versus-actual improvement: the dV of every backward pass is
  non-negative and over-predicts or matches the achieved improvement;
  the ratio dV/dJ_actual sits at 1.000001 on the late iterations
  where the quadratic model is exact (real anchors below in the
  worked example).
- Soft-landing gate: |h_N| = 4.026e-03 m and |v_N| = 6.348e-03 m/s,
  min h over the converged rollout 4.026e-03 m (never below ground);
  assert |h_N| < 0.05 m, |v_N| < 0.05 m/s, min h >= -1e-9 m.
- Monotone descent: every accepted iteration strictly lowers J (real
  anchor True).
- Backtracking event: the alpha trace [1, 0.5, 1, 1, 1, 1] records
  one line-search backtrack at iteration 2 (real anchor).
- Regularization trace: mu decays by the 0.7 rule from 1e-6 to
  1.6807e-07 over the six accepted iterations (real anchor).
- Determinism: two identical ilqr_solve runs are bitwise identical in
  costs, u_seq and alphas (real anchor True).
- ValueErrors across the module: n_steps = 0 and u0 of length 5 on
  ilqr_solve; a non-finite x0 entry; dt at -1.0 and 0.0, c at -0.1,
  g at -1.0 and a non-finite u on discrete_dynamics; k = -1 on
  reference_state.
- Failure path: ilqr_solve(x0, qh=0.0, qv=0.0, wp=0.0) (terminal
  cost only, no running state cost) raises RuntimeError("iLQR failed
  to improve the cost") after the regularizer reaches mu_max = 1e6
  (real anchor, deterministic).
- Determinism; no imports beyond math; no RNG anywhere.

## Worked example

Scenario (all values below are REAL outputs of the prep anchor
/tmp/w44spec/anchor_ilqr.py, stdlib math, exit 0, all checks passed):
dt = 0.4 s, N = 50 steps (20 s horizon), g = 9.81 m/s^2, c = 0.02
1/m (terminal velocity sqrt(g/c) = 22.14723459 m/s, so |v_ref| = 15
m/s is 67.7% of it). The glide slope descends from h0 = 300 m at the
constant rate v_ref = -15 m/s and the vehicle starts ON the glide at
x0 = [300, -15]. Cost weights Q = diag(1, 2), R = 0.05, Qf =
diag(400, 800), below-ground penalty weight 0.5. The initial guess is
the zero-control rollout: pure free fall off the glide. J0 =
3950193.632, and the free-fall rollout ends at h = -133.994337 m,
v = -22.147235 m/s (133.99 m below ground, min h on the guess
-133.994 m), so the penetration penalty is heavily active in the
guess.

- Iteration trace: J0 = 3950193.632 -> 9317.923352 (alpha 1.0) ->
  4974.117631 (alpha 0.5: the line search backtracks) -> 957.7706809
  (alpha 1.0) -> 78.33433455 -> 78.33431352 -> 78.33431352
  (converged at iteration 6; J0/J* = 5.043e+04). The alphas of the
  accepted iterations are [1, 0.5, 1, 1, 1, 1] and the mu values at
  acceptance decay by the 0.7 rule: [1e-06, 7e-07, 4.9e-07,
  3.43e-07, 2.401e-07, 1.6807e-07]. Every accepted iteration lowers
  J (monotone descent True).
- Model-versus-actual improvement (the line-search diagnostic):
  iter 0 -> 1: dV_pred = 3.99097026e+06 vs dJ_actual = 3.94087571e+06
  (the quadratic model over the diving free-fall guess is optimistic,
  yet alpha 1.0 still improves); iter 1 -> 2: dV_pred = 9.19602194e+03
  vs dJ_actual = 4.34380572e+03 (twofold over-prediction, and the
  line search backtracks to alpha 0.5); iter 2 -> 3: 4.88631556e+03
  vs 4.01634695e+03; iter 3 -> 4: 8.79435314e+02 vs 8.79436346e+02
  (the model becomes exact); iter 4 -> 5: 2.09615258e-05 vs
  2.10324052e-05; iter 5 -> 6: 1.24295440e-09 vs 1.27161570e-09.
- Converged trajectory (the constant-descent-rate landing): the
  vehicle rides the glide slope at h = h_ref to within millimeters
  through k = 45 (h = 29.8345 vs h_ref = 30.0000 at k = 45), holding
  v = -15.0001 m/s with the cruise control u = 5.3100 m/s^2 (the
  drag-compensated thrust g + c*v*|v| = 9.81 - 4.5 = 5.31: drag
  relief of c*v^2 = 4.5 m/s^2 against the drag-free 9.81); the flare
  starts at k = 48 (u = 8.4396) and peaks at k = 49 with u =
  40.6293 m/s^2, killing the last 13.87 m/s of descent in one step
  (max |u| = 40.62926756 m/s^2 at step 49). Touchdown: h_N =
  0.004026427311 m, v_N = -0.00634832305 m/s (|h_N| = 4.026e-03 m,
  |v_N| = 6.348e-03 m/s), and min h over the converged rollout is
  4.026e-03 m: the trajectory never penetrates the ground. Full
  converged samples (k, h, v, u, h_ref): k = 0 (300.0000, -15.0000,
  5.3100, 300.0000), k = 10 (240.0000, -15.0000, 5.3100, 240.0000),
  k = 20 (179.9999, -15.0001, 5.3098, 180.0000), k = 25 (149.9994,
  -15.0005, 5.3093, 150.0000), k = 30 (119.9976, -15.0019, 5.3072,
  120.0000), k = 35 (89.9902, -15.0080, 5.2987, 90.0000), k = 40
  (59.9597, -15.0329, 5.2634, 60.0000), k = 45 (29.8345, -15.1351,
  5.1214, 30.0000), k = 48 (11.6199, -15.1658, 8.4396, 12.0000),
  k = 49 (5.5536, -13.8739, 40.6293, 6.0000). Cruise band k = 10..39:
  mean u = 5.305246 vs the drag-compensation model g + c*v*|v| =
  5.307987 at the mean band velocity -15.003355 (within 0.01). The
  first control is u_0 = 5.309997827 m/s^2.
- Converged local affine control law (the leaf-plan deliverable):
  at k = 0, feedforward k_0 = 7.252901285e-09 (zero at the optimum,
  as expected) and feedback K_0 = [-1.386881e+00, -2.272025e+00] on
  (h, v); at k = 25, k_25 = -1.428178568e-08 and K_25 =
  [-1.386887e+00, -2.272010e+00]. The feedback row is essentially
  constant along the glide: the converged policy is the time-invariant
  affine law u = ubar + K*(x - xbar) with K = [-1.387, -2.272] on the
  altitude error and the velocity error.
- Value-function quadratics at k = 0 of the final backward pass (real
  anchor): Qx = [-4.395526837, -7.020479693], Qu = -2.769615241,
  Qxx = [[6.179754075, 3.43870942], [3.43870942, 5.608051338]],
  Qux = [0.7193725209, 1.175035563], Quu = 0.5169929236. Backward
  pass output at k = 0: Vx_0 = [-0.398245213, -0.6637478787],
  Vxx_0 = [[5.177127803, 1.802604896], [1.802604896, 2.936884411]].
  Terminal Riccati seed at k = N: Vx_N = Qf*x_N = [1.610570925,
  -5.07865844], Vxx_N = diag(400, 800).
- Linear-limit identity run (c = 0, wp = 0): converged at iterations
  = 2 with J* = 170.5888011; J after iteration 1 is 170.5888011 and
  |J_1 - J*| = 4.176e-09: one backward pass solves the LQ problem
  exactly and the driver needs only a confirming second pass. The
  drag-free terminal state is h_N = 0.006300569206 m, v_N =
  -0.006850166853 m/s, u_0 = 9.809997404 m/s^2 (the cruise thrust is
  g, no drag relief) and max |u| = 43.84106786 m/s^2.
- Drag sensitivity: the mean cruise control drops from 9.806530
  (c = 0) to 5.305246 (c = 0.02), a difference of -4.501285 that
  matches c*|v_ref|*v_ref = -4.500000 within 0.01: the optimizer
  harvests exactly the quadratic drag as thrust relief during the
  constant-descent-rate cruise.
- Determinism: a second identical run is bitwise identical in costs,
  u_seq and alphas (True).
- Failure path (deterministic): ilqr_solve(x0, qh = 0.0, qv = 0.0,
  wp = 0.0) (terminal cost only, no running state cost) raises
  RuntimeError("iLQR failed to improve the cost") after the
  regularizer reaches mu_max = 1e6.
Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w44spec/anchor_ilqr.py (stdlib math, exit 0).

## Validation list (contract test must include)

- dynamics_jacobians([100.0, -15.0], 12.0) equals ([[1, 0.4], [0,
  0.76]], [0, 0.4]) within 1e-12; discrete_dynamics([100, -15], 12)
  = [94.0, -12.324] and ([100, +15], 12) = [106.0, 14.076] within
  1e-9 (the drag relief while descending is 4.5 m/s^2, the drag load
  while climbing is -4.5 m/s^2).
- Terminal seed identity: Vx_N = [qfh*h_N, qfv*v_N] = [1.610570925,
  -5.07865844] within 1e-6 and Vxx_N = diag(400, 800) exactly, with
  h_N = 0.004026427311 and v_N = -0.00634832305 within 1e-6 on the
  converged rollout.
- Worked scenario: converged=True, iterations = 6, J* = 78.33431352
  within 1e-6 relative; cost history [3950193.632, 9317.923352,
  4974.117631, 957.7706809, 78.33433455, 78.33431352, 78.33431352]
  within 0.01% relative per entry (assert with isclose or delta,
  NEVER exact equality); alpha trace [1, 0.5, 1, 1, 1, 1]; mu trace
  within 5% of [1e-06, 7e-07, 4.9e-07, 3.43e-07, 2.401e-07,
  1.6807e-07] where comparable.
- Model-versus-actual improvements within 1% where the model is
  exact: iter 3 -> 4 anchors 8.79435314e+02 and 8.79436346e+02; on
  every iteration dV_pred >= dJ_actual - max(1e-6, 0.01*|dJ|) and
  both non-negative; dV_pred/dJ_actual within 1.0001 of 1 at
  iterations 3 through 6.
- Soft-landing gate: |h_N| < 0.05 m (anchor 4.026e-03 m), |v_N| <
  0.05 m/s (anchor 6.348e-03 m/s), min h over the converged rollout
  >= -1e-9 m (anchor 4.026e-03 m); max |u| = 40.62926756 within 0.01
  at step 49; u_0 = 5.309997827 within 1e-4.
- Cruise band k = 10..39: mean u = 5.305246 within 0.01 of the
  drag-compensation model g + c*v*|v| = 5.307987 at mean v =
  -15.003355; the drag-free mean cruise is 9.806530 and the
  difference 4.501285 matches c*|v_ref|*v_ref = 4.500000 within
  0.01.
- Converged local affine control law: K_0 = [-1.386881e+00,
  -2.272025e+00] within 1e-3 per entry and K_25 = [-1.386887e+00,
  -2.272010e+00] within 1e-3; |k_0| and |k_25| below 1e-6 (anchors
  7.252901285e-09 and -1.428178568e-08).
- Value-function quadratics at k = 0 of the final backward pass
  within 1e-4 relative per entry: Qx = [-4.395526837,
  -7.020479693], Qu = -2.769615241, Qxx = [[6.179754075,
  3.43870942], [3.43870942, 5.608051338]], Qux = [0.7193725209,
  1.175035563], Quu = 0.5169929236; backward pass output Vx_0 =
  [-0.398245213, -0.6637478787] and Vxx_0 = [[5.177127803,
  1.802604896], [1.802604896, 2.936884411]] within 1e-4 relative.
- Linear-limit identity: ilqr_solve(x0, c = 0.0, wp = 0.0) returns
  converged=True at iterations = 2 with |J_1 - J*| < 1e-6 (anchor
  4.176e-09) and J* = 170.5888011 within 1e-6 relative; h_N =
  0.006300569206, v_N = -0.006850166853 within 1e-6.
- Determinism: two identical runs bitwise identical in costs, u_seq
  and alphas; no imports beyond math; no RNG.
- Monotone descent: costs strictly decrease at every accepted
  iteration of the worked scenario.
- ValueErrors: ilqr_solve with n_steps = 0 and with u0 of length 5;
  ilqr_solve with a non-finite x0 entry; discrete_dynamics with dt at
  -1.0 and 0.0, c at -0.1, g at -1.0 and a non-finite control;
  reference_state(-1).
- Failure path: ilqr_solve(x0, qh = 0.0, qv = 0.0, wp = 0.0) raises
  RuntimeError("iLQR failed to improve the cost") (deterministic,
  mu reaches mu_max = 1e6).
- Run the contract test under both python3 (3.9.x) and the pyenv
  3.13 hook interpreter; all asserts above are tolerance-based and
  must hold on both.

## Corpus fragment (eval/hit1-wave44-ilqr-ddp.yaml)

Query 1 (copy verbatim):
  "run iterative LQR (ilqr-ddp) on the nonlinear discrete-time
  soft-landing dynamics under gravity and quadratic drag: roll the
  nominal control forward, run the backward Riccati pass that forms
  the value-function quadratics Qx, Qu, Qxx, Qux, Quu and the local
  affine control law at each step, and execute the forward pass with
  backtracking line search until the total cost converges"
  intent: "gnc-autonomy; ilqr-ddp differential dynamic programming on
  nonlinear discrete-time dynamics: forward rollout, backward Riccati
  pass with the value-function quadratics and the local affine
  control law, forward pass with backtracking line search to
  convergence"
  expected_skill: "gnc-autonomy/optimal-control/ilqr-ddp"
Query 2 (copy verbatim):
  "compute the iterative-lqr backward-riccati-pass gains and the
  converged feedforward control of the differential-dynamic-
  programming constant-descent-rate soft landing with drag, and check
  the touchdown state, the gain sequences and the cost history
  against the documented landing trajectory"
  intent: "gnc-autonomy; iterative-lqr backward-riccati-pass and
  differential-dynamic-programming gain sequences with the converged
  feedforward control, touchdown state and cost history of the
  nonlinear soft-landing trajectory"
  expected_skill: "gnc-autonomy/optimal-control/ilqr-ddp"
Task ids: w44-ilqr-ddp-1 and -2. Prep grep: ilqr-ddp,
differential-dynamic-programming, iterative-lqr and
backward-riccati-pass appear in NO existing eval/hit1-corpus.yaml
task (grep count 0 per token), in NO skill file (whole-tree count 0)
and in NO wave44-specs file written so far; the lqr-design and
lqg-design tasks route on the algebraic Riccati equation solutions
and the gain vector or the two-ARE compensator, the MPC tasks route
on the receding-horizon QP first move with prediction and control
horizons, the dymos tasks route on pseudospectral phase convergence
with collocation nodes, the bang-bang tasks route on the switching
curve and minimum-time maneuver, and the optimization-algorithms
tasks route on static golden-section, gradient, Newton or simplex
minimization, so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run iterative LQR /
differential dynamic programming (ilqr-ddp) on a nonlinear discrete-
time system:" and include the outputs in the Claim. First tag:
ilqr-ddp. Additional tags ONLY: differential-dynamic-programming,
iterative-lqr, backward-riccati-pass, forward-rollout,
local-affine-control-law. NEVER single generic words (control,
optimal, trajectory, landing, flare, drag, rollout, rollout pass,
gain, cost, value, convergence, iteration, horizon, dynamics,
nonlinear, discrete alone) and NEVER the sibling-owned compounds:
linear-quadratic-regulator, riccati, gain-matrix, state-feedback,
closed-loop-stability, control-effort, spacecraft-attitude-control,
algebraic-riccati-equation (lqr-design, which owns the plain riccati
tag and the infinite-horizon algebraic equation); linear-quadratic-
gaussian, output-feedback-compensator, separation-principle,
filter-riccati-gain, compensator-transfer-function, regulator-riccati
(lqg-design); model-predictive-control, mpc, receding-horizon,
quadratic-cost, constraint-handling, double-integrator (model-
predictive-control, which owns the plain double-integrator tag for
its LINEAR plant); trajectory-optimization, optimal-control, dymos,
pseudospectral, phase, convergence, collocation, launch-ascent,
bounds (dymos-trajectory, which owns the plain optimal-control and
convergence tags); bang-bang-control, time-optimal-control,
switching-curve, minimum-time-maneuver, rest-to-rest-slew,
bounded-input-control (bang-bang-control); golden-section-search,
gradient-descent, nelder-mead, newton-method, line-search,
unconstrained-minimum (optimization-algorithms). 50-150 words,
<=1000 chars, no em dash, no content-policy sweep term, action verb
present. Recommended wording (outputs in Claim order): "Use when you
must run iterative LQR / differential dynamic programming (ilqr-ddp)
on a nonlinear discrete-time system: roll the nominal control forward
through the two-state soft-landing dynamics with gravity and
quadratic drag, run the backward Riccati pass that forms the
value-function quadratics Qx, Qu, Qxx, Qux, Quu and the local affine
control law u = ubar + K (x - xbar) + k at every step, and execute
the forward pass with backtracking line search and regularization
until the total cost converges. Produces the converged control
sequence, the touchdown state of the constant-descent-rate
landing, the feedforward and feedback gain sequences, the
per-iteration cost, alpha and mu traces, and the model-versus-actual
improvement comparison that gate the optimal soft-landing trajectory
of the nonlinear plant. Trigger: ilqr-ddp, differential dynamic
programming, iterative LQR, backward Riccati pass, local affine
control law, forward rollout, nonlinear soft-landing flare." The
sibling phrase triggers "algebraic Riccati
equation", "gain vector", "state feedback", "receding horizon",
"quadratic program", "pseudospectral", "collocation", "Dymos",
"switching curve", "minimum time", "golden section", "gradient
descent", "Nelder-Mead" and "Newton method" must not appear as
routing keywords; "backward Riccati pass" is the leaf's own identity
and must stay, referring only to the per-step finite-horizon pass,
never to an algebraic equation.

FORBIDDEN TOKENS (belong to siblings): algebraic Riccati equation,
infinite horizon, gain vector, state feedback, closed loop stability,
control effort (lqr-design); output feedback compensator, separation
principle, regulator Riccati, filter Riccati gain (lqg-design);
receding horizon, quadratic program, prediction horizon, control
horizon, input constraints, active set, the tag double-integrator
(model-predictive-control); pseudospectral, collocation, phase,
delta-v, launch ascent, Dymos (dymos-trajectory); switching curve,
minimum time maneuver, rest to rest (bang-bang-control); golden
section, gradient descent, Nelder-Mead, Newton method, the tag
line-search (optimization-algorithms). The outputs of this leaf are
the Qx, Qu, Qxx, Qux, Quu quadratics of the backward Riccati pass,
the local affine control law gains and the converged trajectory of
the nonlinear landing plant; no output is an algebraic Riccati
equation, a receding-horizon QP, a pseudospectral collocation or a
golden-section minimum.

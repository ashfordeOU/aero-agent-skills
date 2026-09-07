# Wave-45 leaf spec: l1-adaptive-control (gnc-autonomy, control pack)

- Path: skills/gnc-autonomy/control/l1-adaptive-control/
- Pack: control (present siblings adaptive-control,
  control-allocation, digital-control-design, frequency-response-design,
  gain-scheduling, lead-lag-compensation, observer-design,
  pid-control-design, python-control-design, root-locus-design,
  state-space-analysis; no sibling in the pack or anywhere else in the
  tree runs an L1 adaptive architecture: zero-owner greps at prep and
  re-verified at spec time over the whole skills/ tree return 0 hits
  for `l1[- ]adaptive` and `state predictor`).
- Provenance: wave-45 recon receipt task-6 GO 2, lines 102-144 (rank 2
  of 4 GO): "L1 adaptive control for a first-order uncertain plant:
  state predictor x_hat_dot = a_m x_hat + b (u + sigma_hat),
  projection-based adaptive law on the prediction error, control with
  the low-pass filter C(s) = omega_c / (s + omega_c) on the adaptive
  signal. Equation family: predictor plus projection adaptation plus
  first-order low-pass filter. Source: Cao and Hovakimyan, L1 Adaptive
  Control Theory: Guaranteed Robustness with Fast Adaptation, SIAM,
  2010". Corpus tokens of the leaf (receipt gate f):
  l1-adaptive-control, state-predictor, low-pass-filtered-adaptation,
  projection-based-adaptation-law, guaranteed-transient-response.
- Claim fences (quoted from the sibling frontmatter and body at prep,
  re-verified at spec time; the nearest owner, the MRAC sibling,
  fences out the L1 architecture, which is the exact gap this leaf
  closes):
  - adaptive-control (this pack) OWNS first-order MRAC: its
    frontmatter description reads "Use when you must design and
    simulate a model-reference adaptive controller (MRAC) for a
    first-order plant with an unknown plant coefficient: run the
    reference model from the command, form the control as the sum of a
    state-feedback term and a feedforward term with adaptive gains,
    update the gains online with the gradient (Lyapunov-motivated)
    adaptation law scaled by the tracking error, and assess convergence
    of the tracking error and of the gains toward the
    ideal-cancellation values". Its body pins the architecture
    (lines 25-28): "the control is the sum of a state-feedback term
    theta_x * x and a feedforward term theta_r * r with gains that
    adapt online, and the adaptation is the gradient (Lyapunov-
    motivated) law driven by the tracking error e = x - xm", and its
    adaptation rule (lines 56-58) is the gradient update on the
    TRACKING error: "theta_x_new = theta_x - gamma_x * e * x * dt and
    theta_r_new = theta_r - gamma_r * e * r * dt". Its scope note
    (lines 38-39) admits "single input, no noise, no disturbance,
    sign of the control effectiveness known positive, a_p unknown".
    There is no state predictor, no prediction error, no projection
    operator, no low-pass filter on the control channel and no
    transient-bound claim anywhere in its model, workflow, worked
    example or pitfalls; the leaf plan quote in the receipt (b) is
    verbatim from that description and the body never mentions L1.
  - The other ten control-pack leaves own fixed-gain or
    known-parameter design for plants whose coefficient is known
    (pid-control-design, lead-lag-compensation, root-locus-design,
    frequency-response-design, digital-control-design,
    python-control-design), gain scheduling over operating points
    (gain-scheduling), actuator distribution (control-allocation),
    observer design (observer-design) and eigenvalue/observability
    analysis of known plants (state-space-analysis): none estimates
    an unknown coefficient or disturbance online.
  Whole-tree greps at prep and spec time: l1-adaptive-control,
  state-predictor, low-pass-filtered-adaptation,
  projection-based-adaptation-law and guaranteed-transient-response
  each return ZERO hits in eval/hit1-corpus.yaml (grep count 0 per
  token), ZERO hits across skills/ and eval/ (whole-tree count 0), and
  no wave45-specs file written so far carries the leaf name. GENUINE
  gnc-autonomy gap (fresh probe task-6 GO 2): no leaf runs the L1
  architecture (state predictor plus projection-based adaptation on
  the prediction error plus the low-pass-filtered adaptive signal with
  a guaranteed transient response), the algorithm class between the
  MRAC gradient law on the tracking error (adaptive-control) and the
  fixed-gain designs of the rest of the pack.
- Standards id: arp4754a (reference-only, present in standards-map.yaml
  at line 38, grep-verified at spec time; SAE ARP is proprietary, name
  plus paraphrase only, no reproduced text). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Design and simulate an L1 adaptive control (L1-adaptive-control) law,
after Cao and Hovakimyan (L1 Adaptive Control Theory, SIAM 2010, scalar
chapter-2 architecture, sigma-only specialization), for a first-order
plant whose coefficient a_p is unknown to the controller and that is
hit by an unknown constant matched disturbance. The simulator's truth
plant is x_dot = a_p*x + b*u + b*d (a_p = -0.5, b = 2, d = 1; the
controller knows only the design pole a_m = -1, the effectiveness b and
the prior a_p in [-1.0, -0.25]); the controller closes the loop with
(1) a state predictor xh_dot = a_m*xh + b*(u + sigma_hat) run from the
same initial state as the plant; (2) a projection-based adaptive law on
the prediction error xt = xh - x that estimates the lumped matched
uncertainty sigma_true(x) = (a_p - a_m)*x/b + d inside the interval
[-sigma_b, sigma_b] with sigma_b = 2.0; (3) a low-pass filter
C(s) = omega_c/(s + omega_c) with omega_c = 10 rad/s on the adaptive
signal, and (4) the control u = k_g*r - nu, k_g = -a_m/b = 0.5, where nu
is the filtered adaptive signal and the reference model
xm_dot = a_m*xm + b_m*r (b_m = 1) sets the command response. Discrete
closed-form Euler updates, fixed step dt = 0.01 s, deterministic, no
RNG. Produces the tracking-error history e = x - xm and its transient
bound verdict (max |e| below the certified scenario bound), the
prediction-error history, the sigma_hat and filtered-signal histories,
the projection engagement count, the final cancellation check
(sigma_hat_final against sigma_ideal, u_final against the -0.75
equilibrium) and the convergence verdict that gate an L1 adaptive
control assessment. The coefficient mismatch is admissible in the L1
sense: with the plant written x_dot = a_m*x + b*(u + sigma_true) the
uncertainty has Lipschitz constant L = (a_p - a_m)/b in x and the
scalar L1-norm condition ||C(s)*(s - a_m)^-1*b||_L1 * L < 1 reduces to
(a_p - a_m)/|a_m| < 1, 0.5 at the worked plant and 0.75 at the prior
corner. Does NOT do: the model-reference/gradient MRAC law with
adaptive gains theta_x, theta_r updated on the tracking error
(adaptive-control); any fixed-gain or known-parameter loop design of
the pack (pid-control-design, lead-lag-compensation, root-locus-design,
frequency-response-design, digital-control-design,
python-control-design); gain scheduling over operating points
(gain-scheduling); distributing a scalar command across redundant
effectors (control-allocation); reconstructing unmeasured states
(observer-design); eigenvalue, controllability or observability
analysis of a known plant (state-space-analysis). Deterministic,
offline, stdlib math only: explicit scalar arithmetic (1 state, 1
input), no numpy, no scipy, no RNG, no external processes.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes, no external solvers. Deterministic: plain explicit scalar
arithmetic in the pinned order below. Module name l1_adaptive_control.
Histories are seeded with the initial values at index 0 and have length
steps + 1, so history[k] is the value at time k*dt (after k advances);
this makes the closed-form identities below exact per index.

Module constants (pin exactly; the worked scenario):
- A_M = -1.0 (design model pole, a_m < 0), B = 2.0 (control
  effectiveness, known positive), B_M = 1.0 (reference input gain,
  unit DC: b_m = -a_m), R = 1.0 (constant command), X0 = 0.0 (initial
  state of plant, predictor and reference model).
- DT = 0.01 (step, s), GAMMA = 10.0 (adaptation rate),
  OMEGA_C = 10.0 (filter bandwidth, rad/s), SIGMA_B = 2.0 (projection
  bound), D = 1.0 (unknown constant matched disturbance),
  A_LO = -1.0, A_HI = -0.25 (prior bounds on a_p),
  PLANT_A = -0.5 (TRUE plant coefficient, simulator secret),
  N_STEPS = 6000 (run length, 60 s), TAIL = 1000 (verdict tail
  window in steps).
- Derived: KG = -A_M / B = 0.5 (feedforward gain for unit DC command
  tracking), SIGMA_MISMATCH = (PLANT_A - A_M) / B = 0.25 (the
  x-coupling of sigma_true).

Defining relations (pin exactly; every function below derives from
these):
- Reference model: xm_dot = a_m*xm + b_m*r; Euler step
  xm_next = xm + dt*(a_m*xm + b_m*r). With a_m = -1, b_m = 1 the
  model settles at b_m*r/(-a_m) = 1.
- Truth plant (simulator only): x_dot = a_p*x + b*u + b*d; Euler step
  x_next = x + dt*(a_p*x + b*u + b*d). The disturbance is matched
  (enters scaled by b), so in the design frame the plant reads
  x_dot = a_m*x + b*(u + sigma_true) with sigma_true(x) =
  (a_p - a_m)*x/b + d = 0.25*x + 1.0 at the worked plant.
- State predictor (receipt anchor equation):
  xh_dot = a_m*xh + b*(u + sigma_hat); Euler step
  xh_next = xh + dt*(a_m*xh + b*(u + sigma_hat)).
- Prediction error: xt = xh - x.
- Projection-based adaptive law on the prediction error:
  sigma_hat_dot = gamma*Proj(sigma_hat, -xt) with the projection onto
  [-sigma_b, sigma_b]. Discrete implementation (the projection of the
  Euler step onto the interval, guaranteed |sigma_hat| <= sigma_b for
  every step): raw = sigma_hat - dt*gamma*xt, then
  sigma_hat_new = clamp(raw, -sigma_b, sigma_b), i.e.
  max(-sigma_b, min(sigma_b, raw)).
- L1 low-pass filter on the adaptive signal, C(s) = omega_c/(s +
  omega_c): nu_dot = omega_c*(sigma_hat - nu); Euler step
  nu_next = nu + dt*omega_c*(sigma_hat - nu).
- L1 control law: u = k_g*r - nu with k_g = -a_m/b = 0.5 (the
  unfiltered feedforward for unit DC tracking plus the filtered
  cancellation of the estimate).
- L1 admissibility of the scenario: ||C(s)*(s - a_m)^-1*b||_L1 =
  b/|a_m| = 2.0 for every first-order C(s) with unit DC gain (the
  filter does not shrink the L1 norm of the plant transfer), so the
  scalar L1-norm condition with L = (a_p - a_m)/b requires
  (a_p - a_m)/|a_m| < 1: 0.5 at the worked a_p = -0.5, 0.75 at the
  prior corner a_p = a_hi = -0.25. An open-loop-unstable mismatch
  (a_p = 1 with a_m = -1, b = 2) violates the condition and the
  sigma_hat estimator resonator then destabilizes the closed loop,
  which is why the worked scenario keeps a_p < 0.
- Reference-loop stability identity (perfect adaptation, sigma_hat =
  sigma_true): the linearized (x, nu) pair has trace a_p - omega_c and
  determinant -a_m*omega_c; at the worked values trace = -10.5 < 0 and
  det = 10.0 > 0 (stable for every omega_c > 0 when a_p < 0).
- Pinned Euler ordering per step k (states x, xh, xm, sigma_hat, nu at
  the beginning of the step): (1) sample prediction error xt = xh - x;
  (2) update the adaptive estimate with the projection law; (3) advance
  the low-pass filter on the UPDATED sigma_hat; (4) form the control
  u = k_g*r - nu; (5) advance plant, predictor and reference model by
  dt; (6) append the post-advance histories. This documented ordering
  is what makes the discrete prediction-error pair contract at
  |lambda| = sqrt(1 + a_m*dt) = 0.9949874 per step for every
  adaptation rate (the discrete fast-adaptation robustness property
  verified below).

Functions (public API, 14):
- projection(sigma_hat, d, sigma_b=SIGMA_B) -> float. Continuous
  projection convention: returns d when sigma_hat is strictly interior,
  or at a bound with d pointing inward (sigma_hat*d <= 0 at the bound);
  returns 0.0 when sigma_hat is at a bound and d points outward.
  ValueError if sigma_b <= 0 or |sigma_hat| > sigma_b.
- adaptive_update(sigma_hat, pred_err, gamma=GAMMA, dt=DT,
  sigma_b=SIGMA_B) -> float. Clamped Euler projection step:
  clamp(sigma_hat - dt*gamma*pred_err, -sigma_b, sigma_b). ValueError
  if gamma < 0, dt <= 0, sigma_b <= 0, or non-finite arguments.
- filter_step(nu, sigma_hat, omega_c=OMEGA_C, dt=DT) -> float. Euler
  step of nu_dot = omega_c*(sigma_hat - nu). ValueError if omega_c <= 0,
  dt <= 0, or non-finite arguments.
- control_output(nu, r=R, a_m=A_M, b=B) -> float. u = (-a_m/b)*r - nu.
  ValueError if b == 0 or non-finite arguments.
- plant_step(x, u, plant_a=PLANT_A, b=B, d=D, dt=DT) -> float. Euler
  step of x_dot = a_p*x + b*u + b*d. ValueError if dt <= 0 or
  non-finite arguments.
- predictor_step(xh, u, sigma_hat, a_m=A_M, b=B, dt=DT) -> float.
  Euler step of xh_dot = a_m*xh + b*(u + sigma_hat). ValueError if
  dt <= 0 or non-finite arguments.
- reference_step(xm, r=R, a_m=A_M, b_m=B_M, dt=DT) -> float. Euler
  step of xm_dot = a_m*xm + b_m*r. ValueError if a_m >= 0, dt <= 0, or
  non-finite arguments.
- sigma_true(x, plant_a=PLANT_A, a_m=A_M, b=B, d=D) -> float. The
  lumped matched uncertainty (a_p - a_m)*x/b + d. Simulator
  bookkeeping only; never an input to the controller.
- simulate(plant_a=PLANT_A, a_m=A_M, b=B, b_m=B_M, r=R, x0=X0, d=D,
  dt=DT, gamma=GAMMA, omega_c=OMEGA_C, sigma_b=SIGMA_B,
  steps=N_STEPS) -> result dict with keys x, xm, xh, u, sigma_hat,
  nu, pred_err, track_err (each a list of length steps + 1, seeded
  with the initial value at index 0; u seeded with the initial control
  k_g*r), proj_active (count of steps whose raw adaptation step was
  clamped), max_abs_track, max_abs_pred, max_abs_sigma, tail_abs_pred
  (max |xt| over the last TAIL steps) and tail_sigma_drift. ValueError
  if a_m >= 0, b == 0, dt <= 0, gamma < 0, omega_c <= 0, sigma_b <= 0,
  steps < 2, or any non-finite scenario value.
- sigma_ideal(x_final, plant_a=PLANT_A, a_m=A_M, b=B, d=D) -> float.
  The ideal cancellation value (a_p - a_m)*x_final/b + d at the
  settled state; assessment target only, never an input to the
  controller (mirrors ideal_gains of the MRAC sibling leaf).
- reference_closed_form(k, r=R, a_m=A_M, b_m=B_M, dt=DT) -> float.
  (b_m*r/(-a_m))*(1 - (1 + a_m*dt)^k), the closed form of the Euler
  reference-model march from a zero initial state.
- filter_closed_form(nu0, sigma_const, omega_c, dt, k) -> float.
  sigma_const + (nu0 - sigma_const)*(1 - omega_c*dt)^k, the exact
  Euler march of the filter under constant input sigma_const.
- no_adaptation_closed_form(k, x0=X0, plant_a=PLANT_A, b=B, d=D,
  dt=DT) -> float. x_star - (x_star - x0)*(1 + a_p*dt)^k with
  x_star = -(b*k_g*r + b*d)/a_p = 6.0: the plant march with sigma_hat
  identically zero (u = k_g*r constant), converging to the WRONG
  equilibrium.
- convergence_report(res, plant_a=PLANT_A, a_m=A_M, b=B, d=D) ->
  (converged, criteria dict). converged is True iff
  res["tail_abs_pred"] < 1e-4 AND res["tail_sigma_drift"] < 1e-6 AND
  |res["sigma_hat"][-1] - sigma_ideal(res["x"][-1])| < 0.05. The
  criteria dict carries tail_abs_pred, tail_sigma_drift, sigma_dev and
  sigma_ideal. The transient-bound verdict is separate: the run's
  max_abs_track must sit below the certified scenario bound E_BOUND =
  0.75 (real anchor 0.5607716796, margin 1.34x; the bound is the
  scenario constant the contract test asserts, not a module output).

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- Reference-model identity: xm[k] equals 1 - 0.99^k at every k in
  (0, 1, 100, 1000, 3000, 6000) within 1e-12 (the Euler march
  reproduces the closed form to float precision; real anchor True).
- Filter identity: marching filter_step from nu0 = 0 under the
  constant input sigma_hat = 1 reproduces nu_k = 1 - 0.9^k at k in
  (1, 10, 100, 1000, 4999) within 1e-12 (real anchor True).
- Projection unit behavior: interior direction passes unchanged;
  at +sigma_b an inward direction passes and an outward direction
  returns 0.0; at -sigma_b an outward direction returns 0.0;
  adaptive_update(1.9, -0.2, gamma = 10, dt = 0.1) returns exactly
  SIGMA_B = 2.0 and adaptive_update(0.0, -0.2, gamma = 10,
  dt = 0.1) returns exactly 0.2 (real anchors True).
- L1-norm identity: the numerical integral of the filtered plant
  impulse response g(t) = b*omega_c/(omega_c - 1)*(e^-t - e^-wc*t) at
  omega_c = 10 equals b/|a_m| = 2.0 within 1e-4 (numerical value
  2.0000000038, real anchor); the admissibility products
  (a_p - a_m)/|a_m| = 0.5 (worked) and (a_hi - a_m)/|a_m| = 0.75
  (prior corner) both sit below 1.
- Reference-loop identity: trace = a_p - omega_c = -10.5 and
  determinant = -a_m*omega_c = 10.0 exactly (real anchor True).
- No-adaptation guard: with gamma = 0 the plant march equals
  no_adaptation_closed_form(k) = 6*(1 - 0.995^k) at k in
  (100, 1000, 3000, 6000) within 1e-9, and the tracking error settles
  at 5.0 (the plant goes to the wrong equilibrium x = 6 without
  adaptation; real anchors True).
- Slow-filter tradeoff: at omega_c = 0.5 rad/s the loop still
  converges but max |track error| = 1.555849 is 2.77x the omega_c = 10
  value 0.560772 (the filter bandwidth sets the achievable transient
  bound; real anchor).
- Adaptation-rate study (fast-adaptation robustness): at gamma in
  (10, 40, 160, 1000) every run converges (tail |xt| below 1e-4) and
  max |track error| decreases monotonically: 0.5607716796,
  0.3349860564, 0.2049952822, 0.1595401164 (real anchors; the 4x rate
  step from 10 to 40 cuts the transient bound by 40.26 percent).
- Determinism: two identical simulate runs are bitwise identical in x,
  sigma_hat and u (real anchor True).
- No imports beyond math; no RNG anywhere.

## Worked example

Scenario (all values below are REAL outputs of the prep anchor
/tmp/w45spec/anchor_l1_adaptive_control.py, stdlib math, exit 0, all
identity checks passed, byte-identical under /usr/bin/python3 3.9.6 and
~/.pyenv/versions/3.13.12/bin/python3): a_m = -1.0, b = 2.0, b_m = 1.0,
r = 1.0, x0 = 0.0, dt = 0.01 s. The plant coefficient a_p = -0.5 is
unknown to the controller (prior [-1.0, -0.25]: the plant is LESS
damped than the design model assumes) and an unknown constant matched
disturbance d = 1.0 acts on it; the estimator must cancel the lumped
uncertainty sigma_true(x) = 0.25*x + 1.0. Adaptation rate gamma = 10.0,
filter omega_c = 10.0 rad/s (C(s) = 10/(s + 10)), projection bound
sigma_b = 2.0, k_g = 0.5, run for 6000 steps (60 s). The equilibrium is
x* = 1 (both the plant and the reference model settle at the unit
command), sigma_ideal = 1.25, u* = -0.75: the control goes NEGATIVE to
hold the plant against the disturbance while tracking r.

- Transient (the guaranteed-transient-response story): the plant races
  ahead of the reference model while sigma_hat ramps (at t = 0 the
  plant accelerates at b*(u + d) = 2*1.5 = 3 m/s^2 against the model's
  b_m*r = 1 m/s^2), the tracking error peaks at max |e| =
  0.5607716796 at k = 43 (t = 0.43 s, x = 0.9116690512 vs xm =
  0.3508973716), the control swings to its most negative value
  u = -1.4394547881 at k = 82 (t = 0.82 s) to arrest the overshoot,
  and the plant overshoots to x = 1.1374400036 at k = 200 (t = 2.00 s,
  xm = 0.8660203251, e = +0.2714196785) before the damped settling.
  The prediction error peaks at max |xt| = 0.4359531903 at k = 36
  (t = 0.36 s). The projection clamps sigma_hat to its sigma_b = 2.0
  bound on exactly 7 consecutive steps, k = 67..73 (t = 0.67 to
  0.73 s), while the raw adaptation step would overshoot the interval;
  max |sigma_hat| over the run is 2.0000000000 (bound value).
- Settling: x stays within 1e-3 of 1 from k = 2211 (t = 22.11 s) and
  the prediction error stays below 1e-4 permanently from k = 3065
  (t = 30.65 s). Samples (k, t, x, xm, e): k = 100 (1.00 s,
  0.4904796820, 0.6339676587, -1.434880e-01), k = 300 (3.00 s,
  0.9913721769, 0.9509591059, +4.041307e-02), k = 1000 (10.00 s,
  0.9818672877, 0.9999568288, -1.809e-02), k = 3000 (30.00 s,
  0.9998807895, 1.0000000000, -1.192e-04), k = 5000 (50.00 s,
  0.9999993843, 1.0000000000, -6.157e-07).
- Final state (the assert targets): x_final = 0.999999958694, xm_final
  = 1.000000000000 (the reference settles at 1), track error e_final =
  -4.130627e-08, prediction error xt_final = 4.151048e-08, sigma_hat
  final = 1.249999983204 against sigma_true(x_final) = 1.249999989673
  (the estimate converged to the lumped uncertainty), nu_final =
  1.250000018748, u_final = -0.750000018748 with the equilibrium
  residual a_p*x + b*u + b*d = -1.684e-08 (the control holds the plant
  at x = 1 against the disturbance, exactly like u* = -0.75).
- Verdict: converged = True on all three criteria with margin: tail
  (last 1000 steps, t = 50 to 60 s) max |xt| = 5.604354e-07 below the
  1e-4 threshold, tail sigma_hat drift = 5.604354e-08 below 1e-6, and
  |sigma_hat_final - sigma_ideal| = 6.469695e-09 below 0.05, with
  sigma_ideal = 1.249999989673. Transient-bound verdict: max |track
  error| = 0.5607716796 below the certified scenario bound E_BOUND =
  0.75.
- u equilibrium identity: -(a_p*x_final + b*d)/b = -0.750000010327,
  matching u_final to 3e-8 (the target -0.75).
- Guard runs (deterministic): with gamma = 0 the plant ignores the
  disturbance estimate entirely and converges to the WRONG equilibrium
  x = 6.0: x(6000) = 6.0000000000, tracking error e(6000) =
  5.0000000000, and the march matches the closed form 6*(1 - 0.995^k)
  at every checked k within 1e-9. With the slow filter omega_c = 0.5
  rad/s the loop still converges (converged = True) but the transient
  bound degrades to max |e| = 1.555849 (2.77x the omega_c = 10 run).
- Adaptation-rate study: max |track error| = 0.5607716796 at
  gamma = 10, 0.3349860564 at gamma = 40, 0.2049952822 at
  gamma = 160, 0.1595401164 at gamma = 1000 (monotone decrease: the
  faster the estimator, the tighter the transient bound, L1's
  fast-adaptation property), with tail |xt| = 5.604e-07, 6.360e-09,
  3.326e-11 and 1.003e-12 respectively (every rate converges).
- Determinism: a second identical run is bitwise identical in x,
  sigma_hat and u (True).
Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w45spec/anchor_l1_adaptive_control.py (stdlib math, exit 0).

## Validation list (contract test must include)

- Reference-model identity: xm[k] = 1 - 0.99^k within 1e-12 at k in
  (0, 1, 100, 1000, 3000, 6000).
- Filter identity: marching the filter from nu0 = 0 under constant
  sigma_hat = 1 gives 1 - 0.9^k within 1e-12 at k in (1, 10, 100,
  1000, 4999).
- Projection behavior: projection(1.0, -0.5) == -0.5; at the bounds an
  inward direction passes and an outward direction returns 0.0;
  adaptive_update(1.9, -0.2, 10.0, 0.1) == SIGMA_B == 2.0 exactly and
  adaptive_update(0.0, -0.2, 10.0, 0.1) == 0.2 exactly.
- Worked scenario finals within 1e-6 relative (assert with isclose,
  NEVER exact equality on computed sums): x_final = 0.999999958694,
  sigma_hat_final = 1.249999983204, nu_final = 1.250000018748,
  u_final = -0.750000018748, sigma_ideal = 1.249999989673; |e_final| =
  4.130627e-08 < 1e-3 and |xt_final| = 4.151048e-08 < 1e-3; the
  equilibrium residual |a_p*x_final + b*u_final + b*d| = 1.684e-08 <
  1e-6; the u-equilibrium identity value -0.750000010327 within 1e-4.
- Transient metrics: max_abs_track = 0.5607716796 within 1e-3 relative
  AND below the certified transient bound E_BOUND = 0.75; max_abs_pred
  = 0.4359531903 within 1e-3 relative; max_abs_sigma = 2.0 exactly;
  proj_active == 7 and the clamp steps are k = 67..73.
- Verdict: convergence_report returns converged True with
  tail_abs_pred = 5.604354e-07 within 10 percent (below 1e-4),
  tail_sigma_drift = 5.604354e-08 (below 1e-6) and sigma_dev =
  6.469695e-09 (below 0.05).
- Settling milestones: x within 1e-3 of 1 from k = 2211 onward and
  |xt| below 1e-4 from k = 3065 onward (allow +/- 20 steps).
- No-adaptation guard: simulate(gamma = 0.0) matches 6*(1 - 0.995^k)
  within 1e-9 at k in (100, 1000, 3000, 6000) and |e(6000) - 5.0| <
  1e-3 (without adaptation the plant converges to the wrong
  equilibrium x = 6, tracking error 5).
- Slow-filter tradeoff: simulate(omega_c = 0.5) converges (verdict
  True) with max_abs_track = 1.555849 within 1 percent, which is more
  than 2.5x the omega_c = 10 value 0.560772.
- Adaptation-rate study: simulate at gamma in (10, 40, 160, 1000)
  converges at every rate (tail_abs_pred < 1e-4 with anchors 5.604e-07,
  6.360e-09, 3.326e-11, 1.003e-12) and max_abs_track is strictly
  decreasing across the four rates (anchors 0.5607716796,
  0.3349860564, 0.2049952822, 0.1595401164), with the 10 to 40 step
  cutting the transient bound by more than 20 percent (real: 40.26).
- L1-norm identity: the numerical integral of
  g(t) = b*omega_c/(omega_c - 1)*(e^-t - e^-10t) over 20 s at 1e-4 s
  resolution equals b/|a_m| = 2.0 within 1e-4 (numeric 2.0000000038);
  the admissibility products (a_p - a_m)/|a_m| = 0.5 (worked) and
  (a_hi - a_m)/|a_m| = 0.75 (prior corner) are both below 1.
- Reference-loop identity: trace = a_p - omega_c = -10.5 and
  determinant = -a_m*omega_c = 10.0 within 1e-12, both satisfying the
  stability signs (trace < 0, det > 0) with omega_c > a_hi.
- Determinism: two identical simulate runs are bitwise identical in x,
  sigma_hat and u; the module imports nothing beyond math; no RNG.
- ValueErrors across the module: simulate with a_m = 0.0, gamma = -1.0,
  omega_c = 0.0, sigma_b = 0.0, b = 0.0, dt = 0.0, steps = 1; a
  non-finite scenario value; plant_step with dt = -1.0 and with a
  non-finite state; predictor_step, filter_step and reference_step
  with dt = 0.0; adaptive_update with dt = 0.0, gamma = -1.0 and a
  non-finite pred_err; control_output with b = 0.0; projection with
  sigma_b = 0.0.
- Run the contract test under BOTH interpreters (/usr/bin/python3
  3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3). All asserts above
  are tolerance-based (assertAlmostEqual/math.isclose) and must hold
  on both; the prep anchor output is byte-identical on both
  interpreters.

## Corpus fragment (eval/hit1-wave45-l1-adaptive-control.yaml)

Query 1 (copy verbatim from the receipt gate e):
  "design an l1-adaptive-control law for the first order plant with
  unknown coefficient: run the state-predictor and the
  low-pass-filtered projection adaptation law and report the tracking
  error"
  intent: "gnc-autonomy; l1-adaptive-control state-predictor law with
  the low-pass-filtered projection-based-adaptation-law on the
  prediction error of a first-order plant with unknown coefficient,
  reporting the tracking error"
  expected_skill: "gnc-autonomy/control/l1-adaptive-control"
Query 2 (copy verbatim from the receipt gate e):
  "run the l1-adaptive-control simulation: propagate the
  state-predictor with the low-pass-filtered adaptation term and the
  projection based adaptation law and verify the transient bound of
  the tracking error"
  intent: "gnc-autonomy; l1-adaptive-control simulation propagating
  the state-predictor with the low-pass-filtered-adaptation term and
  the projection-based-adaptation-law, verifying the
  guaranteed-transient-response bound of the tracking error"
  expected_skill: "gnc-autonomy/control/l1-adaptive-control"
Task ids: w45-l1-adaptive-control-1 and -2. Prep grep (re-verified at
spec time): l1-adaptive-control, state-predictor,
low-pass-filtered-adaptation, projection-based-adaptation-law and
guaranteed-transient-response appear in NO existing eval/hit1-corpus
.yaml task (grep count 0 per token), in NO skill file (whole-tree
count 0, receipt gate a) and in NO wave45-specs file written so far;
the adaptive-control MRAC tasks route on the mrac /
model-reference-adaptive / gradient adaptation-law tokens and the
existing corpus theft audit is 0 of 1238 reroutes (receipt gate e),
so the queries above are collision-free.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must design and simulate an
l1-adaptive-control law for a first-order plant with an unknown
coefficient:" and include the outputs in the Claim. First tag:
l1-adaptive-control. Additional tags EXACTLY as the receipt gate (f)
lists them: state-predictor, low-pass-filtered-adaptation,
projection-based-adaptation-law, guaranteed-transient-response.
NEVER single generic words (control, adaptive, adaptation, filter,
predictor, prediction, plant, disturbance, tracking, transient,
projection, coefficient alone) and NEVER the sibling-owned compounds:
mrac, model-reference-adaptive, adaptive-control (the sibling's own
name tag), adaptation-law, tracking-error (adaptive-control owns the
plain adaptation-law and tracking-error tags, the reference-model
gradient architecture with the theta_x / theta_r adaptive gains and
the Lyapunov-motivated update on the tracking error); and none of the
pack's fixed-gain vocabulary: pid, lead-lag, root-locus, gain-margin,
phase-margin, bode, nyquist, gain-scheduling, control-allocation,
observer-gain, controllability, observability (the ten fixed-gain and
analysis siblings). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term, action verb present. Recommended wording
(outputs in Claim order): "Use when you must design and simulate an
l1-adaptive-control law for a first-order plant with an unknown
coefficient: run the state-predictor from the design model, drive the
projection-based-adaptation-law with the prediction error, pass the
adaptive signal through the low-pass filter omega_c/(s + omega_c) and
form the control as the feedforward minus the filtered estimate.
Produces the tracking-error and prediction-error time histories, the
sigma_hat and filtered-signal histories, the projection engagement,
the convergence verdict and the certified transient-bound check that
gate an L1 adaptive control assessment. Trigger: l1-adaptive-control,
state-predictor, low-pass-filtered-adaptation,
projection-based-adaptation-law, guaranteed-transient-response." The
sibling phrase triggers "model-reference adaptive", "MRAC", "gradient
adaptation law", "adaptive gains", "reference model tracking" and
"ideal-cancellation gains" must not appear as routing keywords; the
state predictor and the projection law on the prediction error are
this leaf's own identity and must stay, always referring to the L1
architecture, never to a gradient gain update.

FORBIDDEN TOKENS (belong to siblings): mrac, model-reference
adaptive, model reference, gradient adaptation law, Lyapunov-
motivated, adaptive gains, the tags adaptation-law and tracking-error
(adaptive-control); pid, lead-lag, root locus, gain margin, phase
margin, Bode, Nyquist, compensator (pid-control-design,
lead-lag-compensation, root-locus-design, frequency-response-design,
digital-control-design); gain scheduling, scheduling variable
(gain-scheduling); control allocation, redundancy (control-
allocation); observer gain, Luenberger, Kalman filter gain
(observer-design); controllability, observability, eigenvalues
(state-space-analysis). The outputs of this leaf are the state-
predictor histories, the projection-based sigma_hat estimate, the
low-pass-filtered adaptive signal, the tracking-error and
prediction-error histories and the transient-bound verdict of the
L1 loop; no output is an MRAC gain vector, a fixed-gain compensator,
a scheduled gain or an observer gain.

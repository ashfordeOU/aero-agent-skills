---
name: l1-adaptive-control
description: "Use when you must design and simulate an l1-adaptive-control law for a first-order plant with an unknown coefficient: run the state-predictor from the design model, drive the projection-based-adaptation-law with the prediction error, pass the adaptive signal through the low-pass filter omega_c/(s + omega_c) and form the control as the feedforward minus the filtered estimate. Produces the tracking-error and prediction-error time histories, the sigma_hat and filtered-signal histories, the projection engagement, the convergence verdict and the certified transient-bound check that gate an L1 adaptive control assessment. Trigger: l1-adaptive-control, state-predictor, low-pass-filtered-adaptation, projection-based-adaptation-law, guaranteed-transient-response."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: control
  tags: [l1-adaptive-control, state-predictor, low-pass-filtered-adaptation, projection-based-adaptation-law, guaranteed-transient-response]
  version: 0.1.0
  author: AeroSkills
---

# L1 Adaptive Control (gnc-autonomy/control/l1-adaptive-control)

Use when the task is designing and simulating an L1 adaptive control
law, after Cao and Hovakimyan (L1 Adaptive Control Theory, SIAM 2010,
scalar chapter-2 sigma-only specialization), for a first-order plant
whose coefficient a_p is unknown to the controller and that is hit by
an unknown constant matched disturbance. The controller closes the loop
with a state predictor run from the design model, a projection-based
adaptation law on the prediction error that estimates the lumped
matched uncertainty inside a bounded interval, a low-pass filter
C(s) = omega_c/(s + omega_c) on the adaptive signal, and the control u
= k_g*r - nu against a reference model that sets the command response.
This leaf implements the closed loop in pure Python, stdlib only,
deterministic, discrete-time Euler integration, and reports the
tracking-error and prediction-error histories, the sigma_hat and
filtered-signal histories, the projection engagement, the convergence
verdict and the certified transient-bound check. It pairs with
gnc-autonomy/control/adaptive-control (the architecture that replaces
the state predictor with a gradient update of two gains on the tracking
error) and with gnc-autonomy/control/control-allocation for spreading
the scalar command across redundant effectors; the fixed-gain design
leaves of the control pack cover plants whose coefficient is known.
Scope: single input, deterministic, no noise, constant matched
disturbance, sign of the control effectiveness known positive, a_p
unknown inside a bounded prior.

## Domain quick reference

- Reference model: xm_dot = a_m*xm + b_m*r with a_m < 0; the model
  settles at b_m*r/(-a_m) = 1 for the unit command. Euler step: xm_next
  = xm + dt*(a_m*xm + b_m*r).
- Truth plant (simulator only): x_dot = a_p*x + b*u + b*d, a_p = -0.5
  unknown to the controller, d = 1.0 the unknown constant matched
  disturbance. In the design frame the plant reads x_dot = a_m*x +
  b*(u + sigma_true) with the lumped uncertainty sigma_true(x) = (a_p -
  a_m)*x/b + d = 0.25*x + 1.0.
- State predictor: xh_dot = a_m*xh + b*(u + sigma_hat), run from the
  same initial state as the plant. Prediction error: xt = xh - x.
- Projection-based adaptation law on the prediction error: sigma_hat_dot
  = gamma*Proj(sigma_hat, -xt), projection onto [-sigma_b, sigma_b].
  Discrete clamped Euler step: raw = sigma_hat - dt*gamma*xt, then
  clamp to [-sigma_b, sigma_b], so |sigma_hat| <= sigma_b every step.
- Low-pass filter on the adaptive signal, C(s) = omega_c/(s + omega_c):
  nu_dot = omega_c*(sigma_hat - nu); Euler step nu_next = nu +
  dt*omega_c*(sigma_hat - nu).
- Control law: u = k_g*r - nu with k_g = -a_m/b = 0.5, the unfiltered
  feedforward for unit DC tracking minus the filtered cancellation
  estimate. The equilibrium control is negative: u* = -0.75 holds the
  plant at x = 1 against the disturbance.
- Histories are seeded at index 0 with the initial values and have
  length steps + 1: history[k] is the value at time k*dt (after k
  advances). Per step the loop samples the prediction error, updates
  sigma_hat, advances the filter on the updated estimate, forms the
  control, advances plant, predictor and reference model, then appends.
- L1 admissibility of the scenario: ||C(s)*(s - a_m)^-1*b||_L1 =
  b/|a_m| = 2.0 for every first-order C(s) with unit DC gain, so the
  scalar L1-norm condition with Lipschitz constant L = (a_p - a_m)/b
  reduces to (a_p - a_m)/|a_m| < 1: 0.5 at the worked plant, 0.75 at
  the prior corner a_p = -0.25. An open-loop-unstable mismatch
  violates the condition and the estimator resonator destabilizes the
  loop; the worked scenario keeps a_p < 0.
- Reference-loop stability identity at perfect adaptation: the
  linearized (x, nu) pair has trace a_p - omega_c = -10.5 and
  determinant -a_m*omega_c = 10.0 (stable for every omega_c > 0 when
  a_p < 0). The discrete prediction-error pair contracts at |lambda| =
  sqrt(1 + a_m*dt) = 0.9949874 per step for every adaptation rate.
- ARP4754A frames the development assurance context for the airborne
  function that hosts the adaptive loop; the relations above are
  standard L1 adaptive control methodology, summary-only.

## Workflow

1. Fix the loop data: design pole a_m (negative), control effectiveness
   b, reference gain b_m, command r, initial state x0, disturbance d,
   step dt, adaptation rate gamma, filter bandwidth omega_c, projection
   bound sigma_b, prior bounds a_lo..a_hi on the unknown plant
   coefficient, and the run length in steps.
2. Sanity-check the pieces with single steps before the full run:
   projection boundary behavior and adaptive_update clamping of the
   projection-based-adaptation-law, filter_step (the low-pass filter
   C(s) = omega_c/(s + omega_c)), plant_step, predictor_step,
   reference_step and control_output (u = k_g*r - nu).
3. Form the design-frame lumped uncertainty with sigma_true(x)
   (simulator bookkeeping only, never an input to the controller) to
   see what the estimator must cancel, and confirm L1 admissibility:
   the product (a_hi - a_m)/|a_m| below 1 and the reference-loop
   stability signs trace = a_p - omega_c < 0, determinant
   -a_m*omega_c > 0.
4. Run the closed loop with simulate(...): read the x, xh, xm state
   histories, the sigma_hat and nu (filtered-signal) histories, the u
   history, pred_err = xh - x and track_err = x - xm, proj_active,
   max_abs_track, max_abs_pred, max_abs_sigma, tail_abs_pred and
   tail_sigma_drift.
5. Check the transient-bound verdict of the tracking error: max_abs_track
   must sit below the certified scenario bound E_BOUND = 0.75 (the
   guaranteed-transient-response check of the run).
6. Read the convergence verdict with convergence_report(res):
   converged True when the tail |xt| stays below 1e-4, the tail
   sigma_hat drift below 1e-6, and the final sigma_hat within 0.05 of
   sigma_ideal(x_final), the ideal cancellation value at the settled
   state (assessment target, never an input to the controller).
7. Cross-check the marches against the closed forms:
   reference_closed_form against the xm history, filter_closed_form
   against a constant-input filter march, no_adaptation_closed_form
   against a gamma-0 run (the plant goes to the wrong equilibrium x =
   6 without adaptation).
8. Confirm the deterministic checks: rerun for bitwise-identical
   histories, reject every non-physical input with ValueError, and run
   the contract test scripts/test_l1_adaptive_control.py.

## Worked example

Scenario: a_m = -1.0, b = 2.0, b_m = 1.0, r = 1.0, x0 = 0.0, dt = 0.01
s. The plant coefficient a_p = -0.5 is unknown to the controller (prior
[-1.0, -0.25]: the plant is less damped than the design model assumes)
and an unknown constant matched disturbance d = 1.0 acts on it, so the
estimator must cancel sigma_true(x) = 0.25*x + 1.0. Adaptation rate
gamma = 10.0, filter omega_c = 10.0 rad/s (C(s) = 10/(s + 10)),
projection bound sigma_b = 2.0, k_g = 0.5, run for 6000 steps (60 s).
The plant and the reference model both settle at x = 1, sigma_ideal =
1.25, u* = -0.75. Real module outputs (stdlib math, exit 0):

- Transient: the plant races ahead of the reference model while
  sigma_hat ramps; the tracking error peaks at max |e| = 0.5607716796
  at k = 43 (t = 0.43 s, x = 0.9116690512 vs xm = 0.3508973716), the
  control swings to its most negative u = -1.4394547881 at k = 82 to
  arrest the overshoot, the plant overshoots to x = 1.1374400036 at
  k = 200 (xm = 0.8660203251, e = +0.2714196785), and the prediction
  error peaks at max |xt| = 0.4359531903 just after t = 0.36 s. The
  projection clamps sigma_hat to the sigma_b = 2.0 bound on exactly 7
  consecutive steps, k = 67..73, and max |sigma_hat| over the run is
  2.0000000000 (the bound value).
- Settling: x stays within 1e-3 of 1 permanently from k = 2211 and the
  prediction error stays below 1e-4 permanently from k = 3064. Samples
  (k, x, xm, e): k = 100 (0.4904796820, 0.6339676587, -1.435e-01),
  k = 300 (0.9913721769, 0.9509591059, +4.041e-02), k = 1000
  (0.9818672877, 0.9999568288, -1.809e-02), k = 3000 (0.9998807895,
  1.0000000000, -1.192e-04), k = 5000 (0.9999993843, 1.0000000000,
  -6.157e-07).
- Final state: x_final = 0.9999999587, xm_final = 1.0000000000 (the
  reference settles at 1), e_final = -4.13e-08, xt_final = 4.10e-08,
  sigma_hat_final = 1.2499999832 against sigma_true(x_final) =
  1.2499999897, nu_final = 1.2500000187, u_final = -0.7500000187 with
  the equilibrium residual a_p*x + b*u + b*d = -1.68e-08: the control
  holds the plant at x = 1 against the disturbance, exactly like u* =
  -0.75.
- Verdict: converged True on all three criteria: tail (last 1000
  steps, t = 50 to 60 s) max |xt| = 5.604e-07 below the 1e-4
  threshold, tail sigma_hat drift = 5.604e-08 below 1e-6, and sigma_dev
  = |sigma_hat_final - sigma_ideal| = 6.47e-09 below 0.05. Transient
  verdict: max |e| = 0.5607716796 below the certified bound E_BOUND =
  0.75 (margin 1.34x).
- Guard runs: with gamma = 0 the plant ignores the disturbance estimate
  and converges to the wrong equilibrium x = 6.0 (e(6000) = 5.0,
  march matches 6*(1 - 0.995^k) to 1e-9); with the slow filter
  omega_c = 0.5 rad/s the loop still converges but the transient bound
  degrades to max |e| = 1.555849 (2.77x the omega_c = 10 run).
- Adaptation-rate study: max |track error| = 0.5607716796 at
  gamma = 10, 0.3349860564 at 40, 0.2049952822 at 160, 0.1595401164 at
  1000 (monotone decrease: the faster the estimator, the tighter the
  transient bound), with tail |xt| = 5.60e-07, 6.33e-09, 3.33e-11 and
  1.00e-12 respectively (every rate converges). Determinism: a second
  identical run is bitwise identical in x, sigma_hat and u.

## Verification

- Confirm the projection unit behavior: interior directions pass,
  inward directions at a bound pass, outward directions at a bound
  return 0.0; adaptive_update(1.9, -0.2, 10.0, 0.1) returns exactly
  SIGMA_B = 2.0 and adaptive_update(0.0, -0.2, 10.0, 0.1) returns 0.2.
- Confirm the worked scenario: x_final = 0.9999999587, sigma_hat_final
  = 1.2499999832, nu_final = 1.2500000187, u_final = -0.7500000187,
  final errors below 1e-3, equilibrium residual below 1e-6, proj_active
  = 7 with the clamp steps exactly k = 67..73, and max_abs_track =
  0.5607716796 below E_BOUND = 0.75.
- Confirm convergence_report returns converged True with the tail
  criteria from the verdict above.
- Confirm the closed forms: the xm history matches 1 - 0.99^k within
  1e-12, a constant-input filter march matches 1 - 0.9^k within 1e-12,
  and a gamma-0 plant march matches 6*(1 - 0.995^k) within 1e-9.
- Confirm the reference-loop identity trace = -10.5, det = 10.0 and the
  L1-norm integral of the filtered impulse response equals b/|a_m| =
  2.0 within 1e-4, with both admissibility products below 1.
- Confirm every non-physical input raises ValueError: a_m >= 0, b == 0,
  dt <= 0, gamma < 0, omega_c <= 0, sigma_b <= 0, steps < 2, non-finite
  values across the module.
- Run the contract test offline: python3
  scripts/test_l1_adaptive_control.py (34 tests, deterministic).

## Pitfalls

- Reading the transient verdict from the wrong metric: the certified
  bound E_BOUND = 0.75 applies to max |e| over the whole run
  (0.5607716796), not to the tail; the tail metrics feed the separate
  convergence verdict, and the two must not be conflated.
- Running too few steps: x settles within 1e-3 of 1 only from about
  k = 2211 and the prediction error clears 1e-4 only from about
  k = 3065, so a short run reads a premature verdict.
- Zero adaptation: with gamma = 0 the plant converges to the wrong
  equilibrium x = 6.0 with tracking error 5.0; the projection-based
  adaptation law is what cancels the lumped disturbance.
- Slow filter bandwidth: omega_c sets the achievable transient bound;
  at omega_c = 0.5 rad/s max |e| = 1.555849 is 2.77x the omega_c = 10
  value, so a very slow filter defeats the transient guarantee.
- Open-loop-unstable mismatch: an a_p >= 0 plant violates the scalar
  L1-norm admissibility condition (a_p - a_m)/|a_m| < 1 and the
  estimator resonator destabilizes the loop; keep the worked scenario
  inside the stable prior.
- sigma_ideal and sigma_true are assessment/simulator values only:
  feeding the true lumped uncertainty back into the controller defeats
  the adaptive purpose (the controller sees only the plant state and
  the prediction error).
- Updating order: the filter must advance on the freshly updated
  sigma_hat before the control is formed; the documented Euler ordering
  is what drives the discrete prediction-error pair contraction at
  |lambda| = 0.9949874 per step.

## Related leaves

- gnc-autonomy/control/adaptive-control: the architecture that replaces
  the state predictor and the projection law with a gradient update of
  two adaptive gains driven by the tracking error of a first-order
  plant, the closest sibling in the pack.
- gnc-autonomy/control/control-allocation: distributing the scalar
  command across redundant effectors once the loop closes.
- gnc-autonomy/control/state-space-analysis: eigenvalue and
  controllability analysis of plants with known parameters, the
  fixed-gain counterpart to online adaptation.
- gnc-autonomy/control/observer-design: reconstructing unmeasured
  states when the adaptive loop cannot measure its state directly.
- gnc-autonomy/control/python-control-design: scripted fixed-gain loop
  design for known plants, the alternative when no online estimation
  is needed.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_l1_adaptive_control.py

The test covers the worked example contract (finals x_final,
sigma_hat_final, nu_final, u_final and sigma_ideal within 1e-6
relative, final errors below 1e-3, equilibrium residual below 1e-6,
transient metrics max_abs_track = 0.5607716796 below E_BOUND = 0.75
and max_abs_pred = 0.4359531903, proj_active = 7 with clamp steps
k = 67..73, history seeding and lengths), the convergence verdict with
its tail criteria, the settling milestones from k = 2211 and k = 3065,
the reference-model, filter and no-adaptation closed-form identities,
the slow-filter tradeoff at omega_c = 0.5, the adaptation-rate study
over (10, 40, 160, 1000), the L1-norm admissibility integral and the
reference-loop stability identity, the projection unit behavior with
the exact bound anchors, bitwise determinism, module purity (no RNG,
stdlib only) and ValueError rejection of non-physical and non-finite
inputs across the module. All numeric asserts are tolerance based and
pass under both /usr/bin/python3 and the pyenv 3.13 hook interpreter.

## Compliance

- Standards referenced, not reproduced: ARP4754A frames development
  assurance for the aircraft functions that host adaptive loops; the L1
  equations above are standard adaptive control methodology after Cao
  and Hovakimyan (SIAM 2010), summary-only per standards-map.yaml,
  reference-only: true.
- compliance: STANDARDS-REF, gated: false.

---
name: adaptive-control
description: "Use when you must design and simulate a model-reference adaptive controller (MRAC) for a first-order plant with an unknown plant coefficient: run the reference model from the command, form the control as the sum of a state-feedback term and a feedforward term with adaptive gains, update the gains online with the gradient (Lyapunov-motivated) adaptation law scaled by the tracking error, and assess convergence of the tracking error and of the gains toward the ideal-cancellation values. Produces the error history, the gain histories and the convergence verdict that gate an adaptive control assessment. Trigger: adaptive-control, mrac, model-reference-adaptive, adaptation-law, tracking-error, unknown-plant."
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
  tags: [adaptive-control, mrac, model-reference-adaptive, adaptation-law, tracking-error]
  version: 0.1.0
  author: Aero Agent Skills
---

# Model-Reference Adaptive Control (gnc-autonomy/control/adaptive-control)

Use when the task is designing and simulating a model-reference adaptive
controller (MRAC) for a first-order plant whose coefficient a_p is
unknown to the designer: the plant is commanded to track the state of a
stable reference model, the control is the sum of a state-feedback term
theta_x * x and a feedforward term theta_r * r with gains that adapt
online, and the adaptation is the gradient (Lyapunov-motivated) law
driven by the tracking error e = x - xm. This leaf implements the
closed loop in pure Python, stdlib only, deterministic, discrete-time
Euler integration, and reports the error history, the gain histories,
and the convergence verdict. It pairs with
gnc-autonomy/control/control-allocation for distributing the scalar
adaptive command across redundant effectors, and with
gnc-autonomy/control/state-space-analysis for the known-parameter
fixed-gain analysis; the fixed-gain design leaves of the control pack
cover the case where a_p is known and no online adaptation is needed.
Scope: single input, no noise, no disturbance, sign of the control
effectiveness known positive, a_p unknown.

## Domain quick reference

- Reference model: xm_dot = a_m * xm + b_m * r with a_m < 0 (stable,
  the model settles at b_m * r / (-a_m)). Discrete Euler step: xm_next
  = xm + dt * (a_m * xm + b_m * r).
- Plant (unknown a_p, known b_p with sign positive): x_dot = a_p * x +
  b_p * u. Discrete Euler step: x_next = x + dt * (a_p * x + b_p * u).
- Control law: u = theta_x * x + theta_r * r. The state-feedback term
  cancels and reshapes the plant pole, the feedforward term sets the DC
  gain.
- Tracking error: e = x - xm, the plant state minus the reference model
  state.
- Ideal cancellation gains: theta_x_star = (a_m - a_p) / b_p and
  theta_r_star = b_m / b_p. At these gains the closed loop reads x_dot
  = a_m * x + b_m * r, identical to the reference model.
- Adaptation law (discrete gradient rule, error = x - xm):
  theta_x_new = theta_x - gamma_x * e * x * dt and theta_r_new =
  theta_r - gamma_r * e * r * dt. Lyapunov motivated: with the sign of
  b_p known positive the update drives the quadratic tracking
  Lyapunov function down, e goes to zero, and the gains settle at the
  ideal-cancellation values.
- Convergence verdict (simulate): converged is True when the max abs
  tracking error over the last 200 steps is below 1e-4 and both final
  gains sit within 0.05 of their ideal values.
- Simulation convention: plant and reference model both start at x0
  with zero initial gains; each step applies the control from the
  current gains, advances both states by dt, then samples the error and
  state after the advance and updates the gains (documented Euler
  ordering that drives the gains to the ideal values).
- Reference-model identity for a zero initial state: xm_k = (b_m /
  (-a_m)) * r * (1 - (1 + a_m * dt)^k), the closed form that the Euler
  march reproduces to float precision.
- ARP4754A frames the development assurance context for the airborne
  function that hosts the adaptive loop; the relations above are
  standard adaptive control methodology, summary-only.

## Workflow

1. Fix the loop data: reference model a_m (negative), b_m; plant bounds
   a_p (unknown) and b_p (nonzero, sign positive); dt; adaptation rates
   gamma_x and gamma_r; command r; initial state x0; step count.
2. Compute the ideal cancellation gains with ideal_gains(a_p, b_p, a_m,
   b_m); they are the assessment target the adaptive gains should reach,
   not an input to the controller.
3. Sanity-check one step of each piece with reference_step, plant_step,
   and control_output before the full run.
4. Run the closed loop with simulate(plant_a, plant_b, model_a, model_b,
   dt, gamma_x, gamma_r, command, x0, steps): read the six histories,
   error_final, max_abs_error, and the converged verdict.
5. Quantify the tail with gain_convergence_report: final gains, signed
   deviations from ideal, and the tracking RMSE over the last 500 steps.
6. Run the instability guard cross-check: simulate with gamma 0 and a
   nonzero x0 on an unstable plant; the growing state proves the
   adaptation is what stabilizes the converged run.
7. Confirm the deterministic checks with the contract test
   scripts/test_adaptive_control.py.

## Worked example

Reference model a_m = -1.0, b_m = 1.0. Plant a_p = 1.0 (open-loop
unstable), b_p = 2.0. dt = 0.01, gamma_x = gamma_r = 10.0, command =
1.0, x0 = 0.0, run for 3000 steps (the strict verdict tail clears at
about 2070 steps, so the example uses 3000 steps; at 2000 steps the
softer bounds below already hold with error 5.1e-5 and gains
-0.99201 / 0.49197).

- Ideal gains: theta_x_star = (-1.0 - 1.0) / 2.0 = -1.0 exactly and
  theta_r_star = 0.5 exactly.
- Reference model settles at b_m * r / (-a_m) = 1.0: xm_final =
  1.0000000000 after 3000 Euler steps (1 - 0.99^3000).
- Final adaptive gains from the module: theta_x_final = -0.9919931
  (deviation 0.00801 from -1.0, inside the -1.1 to -0.9 band and the
  0.05 tolerance) and theta_r_final = 0.4919924 (deviation 0.00801
  from 0.5, inside the 0.45 to 0.55 band).
- Tracking: error_final = 2.95e-7 (below the 1e-3 bound), max abs
  error over the last 200 steps = 8.4e-7 (below the 1e-4 verdict
  tolerance); x_final = 1.0000003, inside 0.99 to 1.01. The largest
  error of the whole run is 0.3016 during the early transient.
- Control at the equilibrium: u_final = -0.5000010, which cancels the
  unstable pole (a_p * x + b_p * u = 1.0 - 1.0 = 0).
- Verdict: converged = True; tracking RMSE over the last 500 steps =
  1.38e-6 (gain_convergence_report).
- Instability guard: same plant with gamma 0 and x0 = 1.0 gives |x| =
  144.8 at step 500 (the open loop grows as 1.01^k), so the adaptation
  is doing the stabilization in the converged run.
- Determinism: identical inputs reproduce the identical histories.

## Verification

- Confirm ideal_gains(1.0, 2.0, -1.0, 1.0) returns theta_x_star -1.0
  and theta_r_star 0.5 exactly.
- Confirm the worked example run (3000 steps) reports converged True
  with error_final below 1e-3, x_final in 0.99 to 1.01, theta_x_final
  in -1.1 to -0.9, and theta_r_final in 0.45 to 0.55.
- Confirm the no-adaptation instability guard: gamma 0 with an unstable
  plant and x0 = 1.0 grows past |x| = 10 by step 500, and gamma 0 keeps
  the gains constant everywhere.
- Confirm the closed-form reference identity: the xm history from a
  zero-state run matches (b_m / -a_m) * r * (1 - (1 + a_m * dt)^k).
- Confirm every non-physical input raises ValueError: model_a >= 0,
  dt <= 0, steps < 2, gamma_x < 0, gamma_r < 0, plant_b == 0.
- Run the contract test offline: python3
  scripts/test_adaptive_control.py (33 tests, deterministic).

## Pitfalls

- Running too few steps and reading the verdict: the strict convergence tail
  clears at about 2070 steps for the worked example (the last-200-step error
  and gain tolerances); at 2000 steps the softer bounds already hold, so the
  converged verdict is run-length dependent.
- Zero adaptation on an unstable plant: with gamma = 0 the open loop grows
  (|x| = 144.8 at step 500 from x0 = 1.0 on the a_p = 1.0 plant), which is
  the intended instability guard - do not expect convergence without the
  adaptation law.
- Flipping the sign of b_p: the Lyapunov-motivated law assumes the sign of
  the control effectiveness is known positive; a wrong sign assumption turns
  the gradient update into a destabilizing one (the leaf records
  sign-positive as a scope condition).
- Mixing up the update ordering: each step applies the control from the
  current gains, advances both states by dt, then samples the error and
  updates the gains; this documented Euler ordering is what drives the gains
  to the ideal values.
- Ideal gains are the target, not an input: ideal_gains(a_p, b_p, a_m, b_m)
  computes theta_x_star = (a_m - a_p)/b_p and theta_r_star = b_m/b_p for
  assessment; feeding them back into the controller defeats the adaptive
  purpose.
- model_a >= 0, dt <= 0, steps < 2, negative gamma and plant_b == 0 raise
  ValueError.

## Related leaves

- gnc-autonomy/control/control-allocation: distributing the scalar
  adaptive command across redundant effectors once the loop closes.
- gnc-autonomy/control/state-space-analysis: eigenvalue and
  controllability analysis of plants with known parameters, the
  fixed-gain counterpart to online adaptation.
- gnc-autonomy/control/observer-design: reconstructing unmeasured
  states when the adaptive loop cannot measure its state directly.
- gnc-autonomy/control/python-control-design: scripted fixed-gain loop
  design for known plants, the alternative when no adaptation is
  needed.
- gnc-autonomy/control/frequency-response-design: classical
  frequency-domain design for known plants in the same pack.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_adaptive_control.py

The test covers the worked example contract (ideal gains exact,
converged True at 3000 steps, gain bands, tracking error bound, final
state window, last-200 error window, u_final at the -0.5 equilibrium),
the 2000-step soft bounds, the no-adaptation instability guard, the
gamma 0 gain-constancy check, reference-model Euler values and the
closed-form identity, the exact adaptation rule and its zero and
negative rate cases, gain convergence report values, and ValueError
rejection of a non-stable reference model, non-positive dt, too few
steps, negative adaptation rates, and zero plant control effectiveness.

## Compliance

- Standards referenced, not reproduced: ARP4754A frames development
  assurance for the aircraft functions that host adaptive loops; the
  MRAC equations above are standard adaptive control methodology,
  summary-only per standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.

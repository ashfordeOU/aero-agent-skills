---
name: alpha-beta-filter
description: "Use when you must design and run an alpha-beta tracking filter for a constant-velocity target in SI units: predict the target position and velocity at the next sample time, form the residual from a noisy position measurement, apply the alpha and beta gain update to track position and velocity, and select the steady-state alpha and beta gains from the smoothing factor and the target maneuverability index. Produces the predicted and updated position and velocity, the residual sequence, and the tracking error metrics that gate a target tracking assessment. Trigger: alpha beta filter, tracking filter, constant velocity target, steady state gains, smoothing factor, maneuverability index, position tracking, velocity tracking."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: estimation-filtering
  tags: [alpha-beta-filter, alpha-beta, tracking-filter, constant-velocity-target, position-tracking, velocity-tracking, steady-state-gains, smoothing-factor, maneuverability-index, target-tracking]
  version: 0.1.0
  author: Aero Agent Skills
---

# Alpha-Beta Filter (gnc-autonomy/estimation-filtering/alpha-beta-filter)

Use when the task is an alpha-beta tracking filter for a
constant-velocity target: predicted position and velocity, the
alpha-beta gain update from a noisy position measurement, and the
steady-state gain selection from the smoothing factor and the
maneuverability index.

## Domain quick reference

- Target model: constant velocity between samples. State is
  (position x, velocity v); each sample interval dt in seconds.
- Predict step: x_pred = x + dt * v and v_pred = v; the velocity
  persists and the position advances by dt * v.
- Residual: r = z - x_pred, the difference between the noisy
  position measurement z and the predicted position.
- Update step: x_new = x_pred + alpha * r and
  v_new = v_pred + (beta / dt) * r. alpha weights the position
  correction, beta weights the velocity correction; both gains are
  dimensionless constants.
- Gain ranges: stable for 0 <= alpha < 2 and
  0 <= beta < 4 - 2*alpha. With alpha = 1 and beta = 1 the updated
  position equals the raw measurement, so the filter tracks the
  measurement exactly.
- Steady-state gains from the smoothing factor (Benedict-Bordner,
  critical damping): beta = alpha^2 / (2 - alpha) for alpha in
  (0, 2). Smaller alpha smooths more and lags a maneuvering target;
  larger alpha tracks faster and passes more measurement noise.
- Steady-state gains from the maneuverability index (Kalata
  tracking index): lambda = sigma_w * dt^2 / sigma_v, formed from
  the target process noise sigma_w, the sample interval dt, and the
  measurement noise sigma_v. The critical-damping gains follow the
  radical closed forms in the logic module; lambda -> 0 gives
  gains (0, 0) and lambda -> infinity gives gains tending to (1, 2).
- Tracking error metrics: root-mean-square error and maximum
  absolute error between the true and estimated position sequences.
- Units: position in the tracked unit (meters), velocity in unit
  per second (m/s), dt in seconds, gains dimensionless.
- ARP4754A (reference-only) frames development assurance for
  aircraft systems; the alpha-beta filter is common tracking-filter
  knowledge (Kalata, Benedict and Bordner).

## Workflow

1. Set the sample interval dt and the target model: constant
   velocity between measurements.
2. Choose the gains. Either pick the smoothing factor alpha and
   derive beta with steady_state_gains(alpha), or form the
   maneuverability index lambda = sigma_w * dt^2 / sigma_v and
   derive both gains with gains_from_tracking_index(lambda).
3. Predict with predict(x, v, dt); confirm the position advanced
   by dt * v and the velocity held.
4. Compute the residual with residual(z, x_pred) and apply the
   update with update(x_pred, v_pred, z, dt, alpha, beta), which
   returns the residual, updated position, and updated velocity.
5. Run the full cycle with step(x, v, z, dt, alpha, beta), or
   filter a whole measurement batch with run_tracker(measurements,
   dt, alpha, beta, x0, v0) and inspect the position, velocity,
   residual, and predicted-position trajectories.
6. Assess the result with tracking_errors(true_positions,
   estimates); compare the RMSE and maximum error against the
   measurement-noise level.
7. For stateful use, keep a TrackFilter instance and call its
   step(z) method per measurement; the filter holds x, v, and the
   last residual.

## Pitfalls

- Using gains outside the stable region; alpha >= 2 or
  beta >= 4 - 2*alpha makes the filter diverge, so the module
  raises ValueError.
- Confusing the smoothing factor with the maneuverability index;
  alpha is a dimensionless gain in (0, 2), lambda = sigma_w * dt^2
  / sigma_v is a noise ratio, and the two connect through the
  steady-state gain formulas.
- Feeding a non-positive sample interval dt; the module raises
  ValueError, and a zero dt makes the velocity correction blow up.
- Forgetting the dt factor in the velocity update; the residual
  is divided by dt so the velocity unit stays unit per second.
- Expecting the filtered position to equal the measurement; with
  alpha < 1 the filter lags the measurement by design and trades
  lag against noise smoothing.
- Mixing units in one state; positions and velocities must share
  one unit set (meters and meters per second).

## Behavior contract (gate 3)

The predict, residual, update, batch tracker, steady-state gain
selection, tracking error metrics, and the stateful TrackFilter are
exercised by the gate 3 contract test:
scripts/test_alpha_beta_filter.py against
scripts/alpha_beta_filter_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_alpha_beta_filter.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.

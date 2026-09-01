---
name: kalman-filter-design
description: "Use when you must design or run a discrete-time Kalman filter for single-axis state estimation in SI units: predict the state and its error covariance through the dynamics model, compute the innovation and innovation variance, calculate the Kalman gain, and correct the state and covariance from a noisy measurement. Produces the predicted and corrected states, the error covariance, the Kalman gain, and the innovation sequence that gate a navigation or estimation assessment. Trigger: kalman filter, state estimation, kalman gain, innovation variance, error covariance, process noise, measurement noise, estimator design, sensor fusion, recursive least squares."
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
  subdomain: navigation
  tags: [kalman-filter-design, discrete-time-filter, single-axis-estimation, state-estimation, kalman-gain, innovation-variance, error-covariance, process-noise, measurement-noise, estimator-design]
  version: 0.1.0
  author: AeroSkills
---

# Kalman Filter Design (gnc-autonomy/navigation/kalman-filter-design)

Use when the task is discrete-time Kalman filter design for a single
axis: predict step, innovation, Kalman gain, and corrected state and
covariance from noisy measurements.

## Domain quick reference

- Scalar linear model: x_k = f * x_(k-1) + w_k with process noise
  w ~ N(0, q), and measurement z_k = h * x_k + v_k with measurement
  noise v ~ N(0, r).
- Predict step: x_pred = f * x_prev and p_pred = f^2 * p_prev + q;
  the predicted covariance grows by the process noise each step.
- Innovation: y = z - h * x_pred, the measurement residual the
  filter weights.
- Innovation variance: S = h^2 * p_pred + r, the expected residual
  energy from predicted covariance plus measurement noise.
- Kalman gain: K = h * p_pred / S, dimensionless, in [0, 1/h] for
  h > 0; K rises as measurements get trusted more (small r) and
  falls as the process noise is trusted more (large q).
- Corrected state and covariance: x_new = x_pred + K * y and
  p_new = (1 - K * h) * p_pred; the covariance shrinks with every
  update and re-grows with every predict.
- Steady state: with f = 1 and h = 1 the predicted covariance
  converges to the positive root of P = P - P^2/(P + 1) + q, and
  the a-posteriori covariance settles below it.
- Units: x and z in the tracked unit (meters for a position),
  covariances p, q, r in the unit squared (m^2), gain dimensionless,
  angles in radians when the state is an angle.
- ARP4754A (reference-only) frames development assurance for
  aircraft systems; the Kalman filter is common estimation-theory
  knowledge (Gelb, Brown and Hwang).

## Workflow

1. Write the model: dynamics f, measurement h, process noise q, and
   measurement noise r, all in consistent SI units.
2. Predict with predict(x_prev, p_prev, f, q); confirm the
   covariance grew by q.
3. Compute the innovation with innovation(z, x_pred, h) and the
   innovation variance with innovation_variance(p_pred, h, r).
4. Compute the gain with kalman_gain(p_pred, h, r); check it lies
   in [0, 1/h].
5. Correct with update(x_pred, p_pred, z, h, r), which returns the
   innovation, innovation variance, gain, corrected state, and
   corrected covariance in one dict.
6. Run the full cycle with kalman_step(x, p, z, f=1.0, h=1.0,
   q=0.0, r=1.0), or filter a whole measurement batch with
   run_filter(measurements, x0, p0, ...) and inspect the state,
   covariance, and innovation trajectories.
7. Size the steady-state behavior with steady_state_covariance(f, h,
   q, r); compare the batch end-state covariance against it.

## Pitfalls

- Confusing the a-priori and a-posteriori covariances: the DARE root
  from steady_state_covariance is the predicted-covariance level;
  the corrected covariance after each update settles below it.
- Feeding a zero measurement noise r; the innovation variance
  collapses and the gain saturates, so the module raises ValueError
  for r <= 0.
- Using negative process noise q to model drift; q must be >= 0,
  and a negative value raises ValueError.
- Neglecting units: mixing meters and kilometers in one state keeps
  the gain correct only by luck, and covariance squares the unit.
- Treating the innovation as the error of the filter; the innovation
  is the residual the filter weights, not the estimation error.
- Reusing one gain for every step; the gain changes as the
  covariance evolves, so recompute it from the current p_pred.

## Behavior contract (gate 3)

The predict, innovation, gain, update, batch filter, and
steady-state logic is exercised by the gate 3 contract test:
scripts/test_kalman_filter_design.py against
scripts/kalman_filter_design_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_kalman_filter_design.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.

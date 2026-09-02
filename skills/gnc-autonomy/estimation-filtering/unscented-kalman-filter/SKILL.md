---
name: unscented-kalman-filter
description: "Use when you must estimate the state of a nonlinear system with an unscented Kalman filter: generate sigma points from the state mean and covariance with the scaled unscented transform, propagate each point through the nonlinear dynamics, compute the weighted predicted mean and covariance, form the innovation covariance and the cross covariance, calculate the Kalman gain, and correct the state and covariance from a nonlinear measurement. Produces the predicted and corrected states, the state covariance, the innovation covariance, the Kalman gain, and the NEES consistency metric that gate a nonlinear estimation assessment. Trigger: unscented kalman filter, sigma points, scaled unscented transform, innovation covariance, kalman gain, nonlinear state estimation, nees."
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
  tags: [unscented-kalman-filter, sigma-points, nonlinear-estimation, scaled-unscented-transform, state-prediction, measurement-update, innovation-covariance, nees, bearing-range-tracking]
  version: 0.1.0
  author: Aero Agent Skills
---

# Unscented Kalman Filter (gnc-autonomy/estimation-filtering/unscented-kalman-filter)

Use when the task is nonlinear state estimation with an unscented
Kalman filter: sigma-point generation through the scaled unscented
transform, propagation of the points through nonlinear dynamics, the
weighted predict, the innovation covariance and Kalman gain from a
nonlinear measurement, and the NEES consistency check.

The UKF is the sigma-point cousin of the linear Kalman filter
(navigation/kalman-filter-design) and of the alpha-beta tracker
(estimation-filtering/alpha-beta-filter): it keeps the predict-update
loop but replaces analytic Jacobians with a deterministic sample of
points, so it works for strongly nonlinear dynamics and measurement
models with no differentiation.

## Domain quick reference

- State model: x in R^n with mean x and covariance P. The process is
  x_(k+1) = f(x_k) + w_k with dynamics noise w ~ N(0, Q); the
  measurement is z_k = h(x_k) + v_k with sensor noise v ~ N(0, R).
  Both f and h may be nonlinear.
- Sigma points: 2n + 1 points X_i sampled deterministically from the
  current (x, P). X_0 = x; X_i = x + gamma * col_i(L) for i = 1..n;
  X_(n+i) = x - gamma * col_i(L), where L is the lower Cholesky
  factor of P (L L^T = P) and gamma = sqrt(n + lambda).
- Scaled unscented transform (Van der Merwe): lambda = alpha^2 * (n +
  kappa) - n with spread alpha in (0, 1], secondary scale kappa, and
  prior knowledge beta (beta = 2 is optimal for Gaussian states).
- Weights: wm_0 = lambda / (n + lambda); wc_0 = wm_0 + (1 - alpha^2
  + beta); wm_i = wc_i = 1 / (2 * (n + lambda)) for i = 1..2n. The
  mean weights sum to 1; the covariance weights carry the beta term.
- Predict: propagate every point through f, then x_pred = sum_i wm_i
  f(X_i) and P_pred = sum_i wc_i (f(X_i) - x_pred)(...)^T + Q. For a
  linear f this reproduces the Kalman predict exactly.
- Update: propagate through h to get the predicted measurements Z_i,
  form the innovation covariance S = sum_i wc_i (Z_i - z_mean)(...)^T
  + R and the cross covariance P_xz = sum_i wc_i (X_i - x)(Z_i -
  z_mean)^T, then K = P_xz S^-1, x_new = x_pred + K (z - z_mean) and
  P_new = P_pred - K S K^T.
- NEES: normalized estimation error squared, (x_est - x_true)^T
  P_est^-1 (x_est - x_true). Its expected value is n for a consistent
  filter; averaged over many Monte Carlo runs NEES should sit near n
  (well above n means overconfident, far below means pessimistic).
- Units: state and measurement in consistent SI units; covariances
  P, Q, R in the unit squared; angles in radians.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the unscented transform is common estimation-theory
  knowledge (Julier and Uhlmann; Wan and Van der Merwe).

## Workflow

1. Write the model: dynamics f(point), measurement h(point), the
   dynamics noise covariance Q, the sensor noise covariance R, and
   the initial mean x0 and covariance P0.
2. Choose the transform parameters: alpha near 1e-3 for Gaussian
   states (larger alpha spreads the points), beta = 2, kappa = 0.
3. Generate the sigma points with generate_sigma_points(x, P, alpha,
   beta, kappa) and confirm the weighted mean and covariance of the
   points reproduce x and P with weighted_moments.
4. Predict with predict(x, P, f, Q, alpha, beta, kappa); confirm the
   covariance grew by Q and the mean advanced through f.
5. Update with update(x, P, z, h, R, alpha, beta, kappa); the call
   returns the corrected state, corrected covariance, predicted
   measurement mean, innovation covariance S, and gain K.
6. For a measurement batch, keep a UKFFilter instance and call
   step(z) per measurement; the filter holds x, P, the last
   innovation, S, and K.
7. Assess consistency with nees(x_est, P_est, x_true) against the
   true state; compare the mean NEES to the state dimension n.

## Sigma-point math

The scaled unscented transform replaces the Jacobian of the extended
Kalman filter with a deterministic sample. Given (x, P):

1. lambda = alpha^2 * (n + kappa) - n and gamma = sqrt(n + lambda).
2. L = chol(P) with L L^T = P; the sigma points are x plus and minus
   gamma times each column of L.
3. Each point is pushed through the nonlinear function (f or h); the
   weighted mean and weighted covariance of the transformed points
   approximate the true mean and covariance of the transformed random
   variable to third order for Gaussian inputs, with the beta term
   tuning the fourth-order moment error.

The same machinery serves both steps: the predict uses f on the state
points, the update uses h on the same state points to form the
predicted measurements and the cross covariance that builds the gain.

## Tuning guidance

- alpha controls the spread of the points around the mean. Very small
  alpha (1e-3) keeps the points close and is standard for Gaussian
  states; larger alpha covers heavy-tailed states but loses accuracy.
- beta = 2 minimizes the fourth-order error for Gaussian states; use
  beta = 0 for other distributions (the beta term only touches wc_0).
- kappa is a secondary scaling that guards against a non-positive
  definite (n + lambda) when alpha is small; kappa = 0 or 3 - n is
  common. A zero or negative (n + lambda) raises ValueError.
- Q and R are the honest uncertainty budgets: too small a Q makes the
  filter overconfident (NEES well above n) and slow to react; too
  large a Q makes it noisy and pessimistic (NEES far below n).
- For strongly nonlinear measurement models, prefer small alpha with
  the exact nonlinear h over an extended-Kalman linearization; the
  UKF carries the full nonlinearity in the sampled points.
- If the innovation covariance S comes out non-positive definite, the
  state covariance P has likely collapsed; re-inflate P or raise Q.

## Pitfalls

- Confusing the UKF with the linear Kalman filter: the UKF needs no
  Jacobians, but it does need the exact nonlinear f and h callables
  and the noise covariances Q and R in the same state units.
- Using an indefinite or negative covariance P; the Cholesky factor
  raises ValueError, and the sigma points are undefined for such P.
- Forgetting the beta term in wc_0; the covariance reconstruction
  then mis-states the spread and NEES drifts.
- Expecting the mean of transformed points to equal f(mean); for
  nonlinear f the unscented mean is the weighted point mean, not the
  function of the mean.
- Feeding measurement noise R that is too small relative to the true
  sensor noise; the gain over-trusts the measurement and the
  corrected covariance understates the error.
- Treating NEES from a single run as proof of consistency; NEES is a
  random quantity and only its Monte Carlo average near n is
  meaningful.

## Behavior contract (gate 3)

The sigma-point generation, weight computation, predict, update,
innovation covariance, gain, NEES, and the stateful UKFFilter are
exercised by the gate 3 contract test:
scripts/test_unscented_kalman_filter.py against
scripts/unscented_kalman_filter_logic.py (stdlib unittest, offline,
deterministic). The test covers moment reconstruction of the sigma
points, symmetry about the mean, exact agreement with the linear
Kalman filter for linear models, and convergence of a full
bearing/range tracking run on a constant-velocity target.
Run:
python3 scripts/test_unscented_kalman_filter.py

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.

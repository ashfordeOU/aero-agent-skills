---
name: rts-smoother
description: "Use when you must run a fixed-interval Rauch-Tung-Striebel (RTS) smoother over a stored forward Kalman-filter output for a discrete constant-velocity model in SI units: propagate the position and velocity state with the constant-velocity transition matrix, run the linear forward pass that stores the predicted and filtered means and covariances at every step, then execute the backward recursion with the smoother gain to combine each filtered estimate with the future measurements. Produces the smoothed state history, the smoother gains, the smoothed covariance history and the covariance reduction verdict that gate offline trajectory reconstruction and post-processing of navigation data. Trigger: rts smoother, rauch-tung-striebel, fixed-interval smoothing, backward pass, smoothed state, offline trajectory reconstruction, post-processing navigation data, constant-velocity model."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: estimation-filtering
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: estimation-filtering
  tags: [rts-smoother, rauch-tung-striebel, fixed-interval-smoothing, backward-pass, smoothed-state, offline-trajectory-reconstruction, post-processing-navigation-data, constant-velocity-model]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rauch-Tung-Striebel Smoother (gnc-autonomy/estimation-filtering/rts-smoother)

Use when the task is fixed-interval smoothing of a stored forward
Kalman-filter history: a constant-velocity forward pass produces the
predicted and filtered means and covariances at every measurement
epoch, and the Rauch-Tung-Striebel (RTS) backward recursion then
refines each filtered estimate with the measurements that came after
it, giving the optimal smoothed state that uses all measurements, past
and future. This leaf implements that pair in pure Python, stdlib
only, deterministic and offline. It is the offline batch complement to
gnc-autonomy/navigation/kalman-filter-design (the forward filter whose
stored outputs feed the smoother) and pairs with
gnc-autonomy/estimation-filtering/extended-kalman-filter and
gnc-autonomy/estimation-filtering/unscented-kalman-filter on the
nonlinear side. It never touches the live navigation state: smoothing
is post-processing only, distinct from the cheap online tracking of
alpha-beta-filter and the attitude fusion of complementary-filter, and
it does not smooth raw flight-test traces with moving averages
(flight-test-operations/planning/flight-test-data-reduction owns that).

## Domain quick reference

- State x = [position, velocity] in SI units (m, m/s). Constant-
  velocity transition F = [[1, dt], [0, 1]] over the step dt (s),
  measurement model H = [[1, 0]], measurement noise variance r (m2).
- Discrete process noise: Q = q * [[dt^4/4, dt^3/2], [dt^3/2, dt^2]]
  where q is the continuous acceleration noise intensity (m2/s3).
- Forward predict: x_pred = F x_filt, P_pred = F P_filt F^T + Q.
- Forward update: innovation y = z - H x_pred, innovation variance
  S = H P_pred H^T + r, gain K = P_pred H^T / S (2x1), x_filt =
  x_pred + K y, and the Joseph-form covariance P_filt = (I - K H)
  P_pred (I - K H)^T + K r K^T.
- RTS backward recursion, k = n-2 down to 0, initialized at the last
  step with the filtered mean and covariance: smoother gain K_k =
  P_filt[k] F^T (P_pred[k+1])^-1 (2x2 inverse), then x_s[k] =
  x_filt[k] + K_k (x_s[k+1] - x_pred[k+1]) and P_s[k] = P_filt[k] +
  K_k (P_s[k+1] - P_pred[k+1]) K_k^T.
- Boundary identity: at the final step the smoothed state and
  covariance equal the filtered values; every smoothed position
  variance sits at or below the filtered one, the fixed-interval
  smoothing benefit.
- Units are SI throughout; the algorithms above are standard linear
  estimation methodology, summary-only.

## Workflow

1. Gather the stored measurement list (position samples), the model
   parameters dt, q, r, and the prior state x0 with covariance P0.
   dt must be positive, q non-negative, r positive, x0 length 2, P0
   2x2, and at least two measurements present.
2. Run forward_kalman(measurements, dt, q, r, x0, p0). It returns one
   record per step with x_pred, P_pred, x_filt, P_filt, the
   innovation and its variance; each record also carries the step dt
   so the smoother can rebuild the transition matrix.
3. Inspect the forward history, for example the last filtered state
   and covariance, to confirm the filter behaved before smoothing.
4. Run rts_smooth(fwd_results). It returns (smoothed_states,
   smoothed_covs, gains): three lists of length n; gains[k] is the 2x2
   smoother gain leaving step k and the final entry is a zero
   placeholder.
5. Quantify the benefit with smoother_reduction(fwd_results,
   smoothed_covs), which returns max_reduction (largest relative drop
   in position variance), all_reduced and boundary_matches.
6. Report the smoothed position and velocity history with the reduced
   covariance for the offline trajectory reconstruction or navigation
   data post-processing task; keep the live filter untouched.
7. Confirm the deterministic checks with the contract test
   scripts/test_rts_smoother.py.

## Worked example

dt = 1 s, q = 0.1 m2/s3, r = 25 m2, x0 = [0.0, 5.0] m, P0 =
diag(100, 10), with the 10 position samples [2.1, 6.8, 11.9, 16.4,
21.2, 26.5, 30.9, 36.2, 41.4, 45.8] m.

- Forward filtered at the last step k=9: position 45.8108 m, velocity
  4.8570 m/s, position variance 8.8487, velocity variance 0.5941.
- Innovation variance runs from 135.025 (first step) down to 38.697
  at the final step as the filter converges.
- Smoothed at k=0: position 2.2080 m, velocity 4.8275 m/s. The
  forward filtered position at k=0 was 2.6369 m, so the backward pass
  has pulled the start of the track onto the data line.
- Smoothed at k=4: position 21.5444 m, velocity 4.8439 m/s, with
  smoothed variances 2.7726 and 0.3326, both clearly below the
  filtered values 12.7131 and 1.8860 at k=4.
- Smoother gain at k=0: about [0.9983, 0.0034]^T; the smoothed state
  at k=9 equals the filtered state at k=9 exactly.
- Covariance verdict: all_reduced True, boundary_matches True,
  max_reduction about 0.78.

## Verification

- Confirm forward_kalman on the worked example returns the k=9
  anchors (45.8108, 4.8570, 8.8487, 0.5941) within 0.01 and that
  rts_smooth returns the k=0 and k=4 anchors (2.2080, 4.8275,
  21.5444, 4.8439, 2.7726, 0.3326) within 0.01.
- Confirm the boundary identity: the smoothed state and covariance at
  the last step equal the filtered values within 1e-12.
- Confirm the covariance reduction verdict: every smoothed position
  variance at or below the filtered value, boundary_matches True.
- Structural identity: smoothing a perfectly noiseless
  constant-velocity ramp (measurements 5*k for k = 0..9, exact model
  q = 0, initial state on the ramp at the epoch before the first
  sample) returns smoothed velocities within 1e-9 of 5.0 m/s at every
  step. With process noise q = 0.1 an off-ramp initial state is a
  legitimate prior inconsistency, so the exact-model ramp is the
  identity check.
- Confirm every non-physical input raises ValueError: dt 0 or
  negative, q negative, r 0, fewer than two measurements, x0 not
  length 2, P0 not 2x2, and a singular 2x2 inversion.
- Run the contract test offline: python3
  scripts/test_rts_smoother.py (34 tests, deterministic).

## Related leaves

- gnc-autonomy/navigation/kalman-filter-design: the forward discrete
  Kalman filter whose stored outputs this smoother consumes.
- gnc-autonomy/estimation-filtering/extended-kalman-filter and
  gnc-autonomy/estimation-filtering/unscented-kalman-filter:
  nonlinear forward filtering that the linear RTS recursion does not
  cover.
- gnc-autonomy/estimation-filtering/alpha-beta-filter and
  gnc-autonomy/estimation-filtering/complementary-filter: cheap
  online tracking and attitude fusion, the real-time alternatives to
  batch smoothing.
- flight-test-operations/planning/flight-test-data-reduction:
  moving-average smoothing of raw flight-test traces, a different
  smoothing task with no state model.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rts_smoother.py

The test covers the 2x2 matrix helpers (multiplication, add, sub,
scale, transpose, inverse with singular rejection), the forward
filter record structure, the worked-example anchors at k=9, k=4 and
the final-step innovation variance 38.697, the smoothed anchors at
k=0 and k=4, the smoothed-below-filtered covariance comparison at
k=4, the boundary identity, the smoother gain anchor at k=0, the
covariance reduction verdict, the noiseless-ramp identity at q = 0,
and ValueError rejection of every non-physical input. It runs in well
under a second.

## Compliance

- ARP4754A frames the development-assurance context for navigation
  estimation software; it is referenced, not reproduced, and the
  estimation relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

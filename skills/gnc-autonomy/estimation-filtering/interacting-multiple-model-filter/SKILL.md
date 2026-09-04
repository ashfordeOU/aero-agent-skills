---
name: interacting-multiple-model-filter
description: "Use when you must track a maneuvering target with an interacting multiple model filter: run a two-mode IMM bank of constant velocity (CV) and constant acceleration (CA) Kalman filters per planar axis, mix the mode-conditioned estimates through the Markov mode-transition probabilities, refresh mode probabilities from innovation likelihoods, and combine the per-mode estimates into the mixed state estimate. Produces mode probabilities that gate maneuver detection, per-mode estimates, the combined estimate and position error history on a scripted maneuvering track. Hand-coded stdlib matrices, deterministic, offline. Trigger: interacting multiple model filter, imm filter, mode probability, Markov mode switching, maneuvering target tracking."
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
  tags: [interacting-multiple-model-filter, imm-filter, mode-probability, markov-mode-switching, maneuvering-target-tracking, cv-ca-filter-bank, model-likelihood-update, mixed-state-estimate]
  version: 0.1.0
  author: AeroSkills
---

# Interacting Multiple Model Filter (gnc-autonomy/estimation-filtering/interacting-multiple-model-filter)

Use when the task is maneuvering-target tracking with an interacting
multiple model (IMM) filter: a two-mode bank of Kalman filters, one
constant-velocity (CV) and one constant-acceleration (CA), that interact
through the Markov mode-transition probabilities each cycle. This leaf
implements the IMM cycle (mix, predict, update, mode-probability refresh,
combine) in pure Python, stdlib only, with the standard per-axis planar
simplification: each planar axis runs its own 2-state CV or 3-state CA
filter and both axes share one mode-probability vector. It pairs with
gnc-autonomy/navigation/kalman-filter-design and the single-model filters
of the estimation-filtering pack for the mode-conditioned core.

## Domain quick reference

- Mode 1 CV, state [p, v]: F_cv = [[1, DT], [0, 1]], Q_cv = q_cv *
  [[DT^3/3, DT^2/2], [DT^2/2, DT]] with q_cv = 1.0 m2/s3.
- Mode 2 CA, state [p, v, a]: F_ca = [[1, DT, 0.5 DT^2], [0, 1, DT],
  [0, 0, 1]], Q_ca = q_ca * [[DT^5/20, DT^4/8, DT^3/6], [DT^4/8,
  DT^3/3, DT^2/2], [DT^3/6, DT^2/2, DT]] with q_ca = 2.0. DT = 1.0 s.
- Measurement: position only, H = [1, 0] or [1, 0, 0], r = 25.0 m2
  (sigma 5 m). Markov transition Pi = [[0.95, 0.05], [0.05, 0.95]].
- Mode prediction: c_j = sum_i pi_ij * mu_i and mixing weights
  mu_ij = pi_ij * mu_i / c_j; the mixed prior of mode j is
  x0_j = sum_i mu_ij * x_i with the interaction spread term in the
  covariance.
- Mode likelihood: L = exp(-0.5 * innovation^2 / s) / sqrt(2 pi s) with
  s = H P H^T + r; mode update mu_new_j = L_j c_j / sum_k L_k c_k.
- Combined estimate: x_combined = sum_j mu_j * x_j per axis (CV padded
  with zero acceleration); both planar axes multiply their per-mode
  likelihoods into one joint per-mode likelihood per cycle.
- All matrix arithmetic is hand coded stdlib, 2x2 and 3x3 only; no numpy.

## Workflow

1. Generate the deterministic maneuvering truth track with
   make_maneuvering_track (100 m/s along x, then ay = 20 m/s2 for 25 s
   from t = 50 s) or pass any scripted position list.
2. Start the bank with run_imm_track: both axes anchor on the first
   measurement with MU0 = [0.95, 0.05] and the documented initial
   covariances.
3. When a distinct prior per mode exists, form the common interacting
   prior with mix_initial(mu, x_ests, p_ests, pi).
4. Inside each cycle imm_step mixes the mode-conditioned priors per mode
   (CV projected from CA, CA padded from CV), calls kalman_predict and
   kalman_update on each axis, refreshes the shared probabilities with
   mode_update, and returns the combined estimate.
5. Read mode_probability_ca = mu_hist[t][1] to gate maneuver detection:
   a rise above 0.8 within a few seconds of onset flags the maneuver.
6. Compare the combined estimate against the truth positions; a
   single-mode CV run on the same track quantifies the tracking loss the
   CA mode removes.
7. Confirm the deterministic checks with the contract test
   scripts/test_interacting_multiple_model_filter.py.

## Worked example

Scripted 100 s track, lateral acceleration 20 m/s2 on y from t = 50 s.
Module outputs (real, deterministic):

- Mode probability of the CA mode: 0.108 before the maneuver (t = 50),
  rising to 0.972 at t = 52, 0.859 at t = 53 (above 0.8 within 3 s of
  onset, the detection gate) and 0.999 at t = 54. After the coast starts
  (t > 75) it relaxes back toward the CV mode (0.108 at t = 99).
- IMM combined position RMS error over the maneuver window t in [50, 75]:
  4.44 m (gate: below 15 m). The largest combined error is 12.91 m at
  t = 53, during the CA-mode takeover transient.
- A single CV-only filter on the same track peaks at 76.04 m position
  error (t = 60), well above the 60 m gate: the accel model is what the
  IMM adds.
- The CV velocity estimate on the straight x leg converges to the true
  100 m/s within 1e-3 by t = 16 s.
- Mode probabilities sum to 1.0 at every step (max deviation 2e-16) and
  the combined estimate equals the mu-weighted sum of the per-mode
  estimates at the final step to 1e-12.

## Verification

- Confirm kalman_update returns the documented 5-tuple and that a
  non-positive r, a malformed matrix dimension, or a mode-probability
  vector that does not sum to 1 raises ValueError.
- Confirm the mode likelihood is positive, mode_update keeps the
  probabilities in [0, 1] summing to 1, and mix_initial recovers the
  input prior when the two mode-conditioned priors are identical.
- Confirm run_imm_track is deterministic (two runs, identical outputs),
  mu_ca > 0.8 by t = 53, IMM RMS position error below 15 m in the
  maneuver window, CV-only error above 60 m somewhere in the window, and
  the combined estimate matches the mu-weighted per-mode sum.
- Run the contract test offline: python3
  scripts/test_interacting_multiple_model_filter.py (35 tests,
  deterministic, exit 0).

## Pitfalls

- Gating maneuver detection on the wrong window: mode_probability_ca rises
  above 0.8 within about 3 s of maneuver onset (0.972 at t = 52 for the
  worked example) and relaxes back after the coast starts; sample mu_hist
  around the onset, not at the end of the track.
- Comparing a single-mode CV filter against the IMM without the same track:
  the CV-only filter peaks at 76.04 m error on the maneuvering track while
  the IMM combined RMS stays below 15 m in the window - the accel model is
  what the IMM adds.
- Forgetting the mode probability normalization: mode probabilities must sum
  to 1.0 at every step (max deviation 2e-16 in the test) and a
  mode-probability vector that does not sum to 1 raises ValueError.
- Reading the combined estimate without the per-mode split: the combined
  estimate equals the mu-weighted sum of the per-mode estimates (CV padded
  with zero acceleration), verified to 1e-12 at the final step.
- Per-axis filters share one mode-probability vector per cycle, and both
  planar axes multiply their per-mode likelihoods into one joint likelihood;
  do not refresh the probabilities per axis independently.

## Related leaves

- gnc-autonomy/navigation/kalman-filter-design: the single-model Kalman
  filter that is the mode-conditioned core of each bank member.
- gnc-autonomy/estimation-filtering/alpha-beta-filter: the fixed-gain
  single-model tracker, a cheaper alternative for benign targets.
- gnc-autonomy/estimation-filtering/extended-kalman-filter: nonlinear
  measurement extension when the position-only linear model is not
  enough.
- gnc-autonomy/navigation/inertial-navigation: the propagation context
  (state transition and process noise) the bank filters assume.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_interacting_multiple_model_filter.py

The test covers the mixing equations and their normalization, the CV and
CA prediction kinematics, the scalar position update and likelihood, the
mode update formula, the single-cycle dict contract, the analytic track
points, and the full-track worked example: mu_ca above 0.8 within 3 s of
maneuver onset, IMM RMS position error below 15 m in the maneuver window,
CV-only error above 60 m, probability normalization at every step, the
final mu-weighted combination identity, straight-leg velocity convergence
within 1e-3 by t = 20 s, determinism, and ValueError rejection of
malformed dimensions, non-positive r and invalid probabilities.

## Compliance

- Standards referenced, not reproduced: ARP4754A frames the
  certification context for GNC estimation functions; the IMM relations
  above are standard engineering methodology (Bar-Shalom style
  interacting multiple model), summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-32 leaf spec: interacting-multiple-model-filter (gnc-autonomy, estimation-filtering pack)

- Path: skills/gnc-autonomy/estimation-filtering/interacting-multiple-model-filter/
- Pack: estimation-filtering. Siblings: alpha-beta-filter,
  complementary-filter, extended-kalman-filter, unscented-kalman-filter,
  particle-filter, rts-smoother (all single-model filters).
- Standards id: arp4754a (reference-only; pack convention for GNC
  leaves). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Run an interacting multiple model (IMM) filter for maneuvering-target
tracking: mix the mode-conditioned state estimates with the Markov
mode-transition probabilities, run a bank of Kalman filters (one per
mode, constant-velocity and constant-acceleration), update the mode
probabilities from the innovation likelihoods, and combine the
mode-conditioned estimates into the mixed state estimate. Produces the
mode probabilities, the per-mode estimates, the combined estimate and
the position error history that gate a maneuvering-target tracking
assessment.

Does NOT do: a single-model Kalman filter (kalman-filter-design and the
estimation-filtering pack own the single-model filters); ARP4761A
Markov reliability analysis (systems-engineering-safety/arp4761a/
markov-analysis owns continuous-time Markov chain state probabilities
for failure states - a different domain that shares the word
"Markov"); particle filtering (particle-filter); smoothing over a batch
(rts-smoother).

## Model (implement exactly)

Two-mode IMM: mode 1 = constant velocity (CV), mode 2 = constant
acceleration (CA).  Planar tracking with the standard per-axis
simplification: each axis (x and y) is filtered independently with its
own 2-state (CV) or 3-state (CA) filter and the SAME mode
probabilities on both axes (equal-axis planar tracker).  All matrix
arithmetic is hand-coded stdlib (no numpy); 2x2 and 3x3 only.

Model constants (module level):
- DT = 1.0 (s).
- CV transition F_cv = [[1, DT], [0, 1]].
- CA transition F_ca = [[1, DT, 0.5*DT**2], [0, 1, DT], [0, 0, 1]].
- Process noise: Q_cv = q_cv * [[DT**3/3, DT**2/2], [DT**2/2, DT]]
  with q_cv = 1.0 (m2/s3); Q_ca = q_ca * [[DT**5/20, DT**4/8,
  DT**3/6], [DT**4/8, DT**3/3, DT**2/2], [DT**3/6, DT**2/2, DT]]
  with q_ca = 2.0.
- Measurement H = [1, 0] (CV) / [1, 0, 0] (CA), position-only,
  measurement noise r = 25.0 (m2, sigma 5 m).
- Markov transition Pi = [[0.95, 0.05], [0.05, 0.95]].

Functions (pure stdlib, deterministic; no RNG in the filter - the
scripted truth trajectory is fixed):

- mix_initial(mu, x_ests, p_ests, pi) -> (mixed_x, mixed_p) per the
  IMM mixing equations (mode-conditioned mixing with c_j =
  sum_i pi_ij*mu_i and mu_ij = pi_ij*mu_i/c_j; mixed state = sum_i
  mu_ij*x_i; mixed covariance via the standard interaction).
- kalman_predict(x, p, f, q) -> (x_pred, p_pred).
- kalman_update(x, p, z, h, r) -> (x_upd, p_upd, innovation,
  innovation_cov_s, likelihood) with likelihood = exp(-0.5 *
  innovation^2 / s) / sqrt(2*pi*s).
- mode_update(mu, c, likelihoods) -> mu_new_j = likelihood_j * c_j /
  sum_k likelihood_k * c_k.
- imm_step(mu, x_cv, p_cv, x_ca, p_ca, z, pi, f_cv, q_cv, f_ca,
  q_ca, r) -> dict {mu_new, x_cv, p_cv, x_ca, p_ca, x_combined,
  p_combined} where x_combined = sum_j mu_j * x_j (per axis).
- run_imm_track(truth_positions) -> dict {mu_hist, combined_pos_hist,
  cv_pos_hist, ca_pos_hist} over the scripted track with
  mode_probability_ca = mu_hist[1].

Track generator (deterministic, no RNG):
- make_maneuvering_track() -> list of positions (m) at DT = 1 s for
  100 s: x starts at 0 with vx = 100 m/s for t < 50 s; from t = 50 s
  a lateral acceleration ay = 20 m/s2 is applied for 25 s (t in
  [50, 75)); after t = 75 s constant velocity again.  Positions are
  computed analytically: px(t) = 100*t; py(t) = 0 for t <= 50; py(t)
  = 0.5*20*(t-50)^2 for 50 < t <= 75; py(t) = 0.5*20*25^2 + 500*(t-75)
  for t > 75 (velocity at t=75 is 20*25 = 500 m/s).  Position noise is
  NOT added to the truth (the measurement noise enters through the
  filter's r); the filter receives z = truth position (the
  measurement model handles the noise statistics).  Deterministic.

ALL functions deterministic; run_imm_track loops 100 steps of the
fixed track.

## Worked example

Run run_imm_track on the scripted track.  Take your module's real
outputs as assert targets, then check the bounds:
- The CA-mode probability mu_ca rises above 0.8 within 3 s of the
  maneuver onset (by t = 53 s, mu_ca > 0.8).
- The IMM combined position RMS error across the maneuver window
  (t in [50, 75]) is below 15 m.
- A single CV-only Kalman filter (run the same track through only the
  CV mode) has position error exceeding 60 m at some point in the
  maneuver window.
- The mode probabilities sum to 1.0 at every step (within 1e-9).
- The combined estimate equals the mu-weighted sum of the per-mode
  estimates at the final step (to 1e-6).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- Mixing normalization: mode probabilities sum to 1.0 after mixing.
- Kalman update identity on a straight track: with zero acceleration
  the CV filter's velocity estimate converges to the true 100 m/s
  within 1e-3 by t = 20 s.
- Likelihood is positive and the mode update keeps probabilities in
  [0,1] summing to 1.
- CA-mode detection: mu_ca > 0.8 within 3 s of maneuver onset.
- Error bound: IMM RMS position error < 15 m in the maneuver window;
  CV-only error > 60 m at some point.
- Determinism: identical outputs on two runs (no RNG in the filter).
- ValueErrors on malformed matrix dimensions or non-positive r.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-interacting-multiple-model-filter.yaml)

Query 1 (copy verbatim):
  "track a maneuvering target with an interacting multiple model filter bank of constant velocity and constant acceleration Kalman filters and report the mode probabilities"
  intent: "gnc-autonomy; IMM filter for maneuvering target tracking"
  expected_skill: "gnc-autonomy/estimation-filtering/interacting-multiple-model-filter"
Query 2 (copy verbatim):
  "combine the mode-conditioned estimates of a Markov mode-switched filter bank with the innovation likelihood mode update for target tracking"
  intent: "gnc-autonomy; IMM mixing and mode probability update"
  expected_skill: "gnc-autonomy/estimation-filtering/interacting-multiple-model-filter"
Task ids: w32-interacting-multiple-model-filter-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must track a maneuvering target
with an interacting multiple model filter:" and include the outputs in
the Claim. First tag: interacting-multiple-model-filter. Additional
tags ONLY: imm-filter, mode-probability, markov-mode-switching,
maneuvering-target-tracking, cv-ca-filter-bank,
model-likelihood-update, mixed-state-estimate. NEVER single generic
words (filter, kalman, tracking, target, mode, model). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): alpha-beta gains, smoothing
factor, maneuverability index (alpha-beta-filter); sigma points,
unscented transform (unscented-kalman-filter); particle weights,
resampling (particle-filter); RTS smoother, backward pass
(rts-smoother); CTMC, state transition rate, availability, MTTF
(arp4761a/markov-analysis - never use bare "Markov analysis" without
the filter context).  Pair "Markov" only with "mode-switched filter
bank".

Tags: [interacting-multiple-model-filter, imm-filter,
mode-probability, markov-mode-switching, maneuvering-target-tracking,
cv-ca-filter-bank, model-likelihood-update, mixed-state-estimate]

Sibling-citation lines for Related leaves:
gnc-autonomy/estimation-filtering/kalman-filter-design (the single-
model filter), gnc-autonomy/estimation-filtering/alpha-beta-filter,
gnc-autonomy/estimation-filtering/extended-kalman-filter,
gnc-autonomy/navigation/inertial-navigation.

Ledger Standard: arp4754a.

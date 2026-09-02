---
name: particle-filter
description: "Use when you must estimate the state of a nonlinear or non-Gaussian system with a bootstrap particle filter: draw an initial particle ensemble from a Gaussian prior, propagate the particles through a constant-velocity or random-walk motion model with additive Gaussian process noise, weight them with a Gaussian measurement likelihood, normalize the importance weights, track the effective sample size, and trigger systematic resampling when the effective sample size drops below half the particle count. Produces the per-step posterior mean and standard deviation, the effective sample size, the resampling flags, and the final ensemble for every measurement, which gate a nonlinear and multimodal tracking assessment. Trigger: particle filter, sequential Monte Carlo, SIR, bootstrap filter, resampling, effective sample size, importance weights, nonlinear estimation, non-Gaussian posterior, multimodal likelihood."
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
  tags: [particle-filter, sampling-importance-resampling, sequential-monte-carlo, bootstrap-filter, systematic-resampling, effective-sample-size, importance-weights, non-gaussian-posterior, nonlinear-state-estimation, multimodal-tracking]
  version: 0.1.0
  author: AeroSkills
---

# Particle Filter (gnc-autonomy/estimation-filtering/particle-filter)

Use when the task is nonlinear or non-Gaussian state estimation with a
bootstrap particle filter (sampling importance resampling, SIR): a
random ensemble of particles approximates the full posterior, so
bimodal likelihoods, heavy-tailed process noise, and sign ambiguity are
represented exactly, without the Gaussian closure that the Kalman
family (navigation/kalman-filter-design, estimation-filtering/
extended-kalman-filter, estimation-filtering/unscented-kalman-filter)
is forced to make. The alpha-beta tracker
(estimation-filtering/alpha-beta-filter) is the fixed-gain alternative
for linear constant-velocity problems where a full posterior is not
needed. This leaf implements the bootstrap recursion in pure Python
stdlib: predict, Gaussian-likelihood weight update, normalization,
effective-sample-size monitoring, and systematic resampling, all
seeded for exact reproducibility.

## Domain quick reference

- State model: scalar position x with additive process noise, measured
  through a possibly nonlinear function h. The recursion is
  p(x_k | z_1:k) proportional to p(z_k | x_k) * integral of
  p(x_k | x_(k-1)) p(x_(k-1) | z_1:k-1) over x_(k-1). Particles carry
  this distribution as a weighted sample, so no Gaussian assumption
  enters.
- Motion model (constant velocity with noise): x_(k+1) = x_k + v * dt
  + w_k with w ~ N(0, process_std^2). v = 0 reduces the model to a
  random walk. Each particle is pushed through the same model, which
  spreads the ensemble by process_std per step.
- Measurement model: z_k = h(x_k) + v_k with v ~ N(0, meas_std^2).
  The identity h(x) = x is a direct position measurement; h(x) = x^2
  is a squared-range sensor whose likelihood has two modes at
  x = +/- sqrt(z).
- Likelihood weight update: w_i <- w_i * exp(-0.5 * ((z - h(x_i)) /
  meas_std)^2), the Gaussian density without its constant factor.
  Weights come out unnormalized.
- Normalization: w_i <- w_i / sum(w). The weighted mean
  sum(w_i x_i) / sum(w_i) is the minimum mean square error estimate
  and the weighted standard deviation is the honest posterior spread,
  which stays wide across a bimodal posterior instead of collapsing to
  one mode.
- Effective sample size: ESS = (sum w)^2 / sum(w^2), which equals
  1 / sum(w^2) for normalized weights. ESS runs from 1 (all mass on
  one particle) to n (uniform). When ESS drops below n / 2 the
  ensemble is degenerate: most particles carry negligible weight and
  the estimate is carried by a handful of survivors.
- Systematic resampling: draw one uniform start u0 in [0, 1/n), then
  copy particle j as the i-th child when the cumulative weight CDF
  satisfies CDF(j-1) < u0 + i/n <= CDF(j). The children carry equal
  weights 1/n. Stratified, so it adds less variance than plain
  multinomial resampling and every stratum is represented.
- Bootstrap SIR step: predict, update weights, normalize, record the
  estimate, resample only when ESS < n / 2. Resampling every step is
  unnecessary; conditional resampling preserves diversity while the
  posterior is healthy.
- Monte Carlo error falls like 1 / sqrt(n): n = 5000 gives posterior
  statistics accurate to roughly 1 to 2 percent of the true spread,
  and n = 10^4 to 10^5 is used for rare-event or high-dimensional
  problems. n must scale with the state dimension; scalar problems
  need only thousands.
- Units are SI throughout (m, m/s, s); the noise standard deviations
  are in state and measurement units.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the bootstrap filter is common estimation-theory knowledge
  (Gordon, Salmond and Smith 1993; Doucet, de Freitas and Gordon).

## Workflow

1. Write the scenario: measurement list z_k, sample time dt, the
   constant-velocity term v (0.0 for a pure random walk), the process
   noise standard deviation, the measurement noise standard deviation,
   and the Gaussian prior (mean, std) at the first step.
2. Draw the initial ensemble with initialize_particles(n,
   prior_mean, prior_std, rng); every particle is an independent draw
   from N(mean, std) and the weights start equal at 1/n.
3. Predict: advance every particle through the motion model with
   predict_particles(particles, dt, process_std, rng, velocity=v).
   Each particle becomes its old value plus v * dt plus a Gaussian
   process-noise draw, so the ensemble mean drifts and its spread
   grows.
4. Update: fold the measurement in with update_weights(particles,
   weights, z, meas_std, h=measurement_fn), which multiplies every
   weight by the Gaussian likelihood of the residual. Pass h only for
   a nonlinear sensor; the default is the identity position
   measurement. The returned weights are unnormalized.
5. Normalize with normalize_weights(weights) so the weights sum to 1,
   then form the posterior mean and standard deviation with
   particle_filter_estimate(particles, weights).
6. Monitor degeneracy with effective_sample_size(weights); when ESS
   drops below n / 2, resample with systematic_resample(particles,
   weights, rng), which returns a fresh ensemble with equal weights
   1/n and no loss of posterior fidelity.
7. For a whole measurement batch, run_particle_filter(measurements,
   dt, n, prior, process_std, meas_std, seed, velocity=v) performs the
   full loop and returns one record per step with the mean, the
   standard deviation, the effective sample size, and the resampling
   flag, plus the final ensemble.
8. Confirm the deterministic checks with the contract test
   scripts/test_particle_filter.py.

## Worked example

Constant-velocity target at 1.0 m/s with direct position measurements:
v = 1.0 m/s, dt = 1 s, prior N(0, 5 m), process noise std 0.5 m,
measurement noise std 1.0 m, n = 5000 particles, filter seed 7
(measurement noise draws use their own fixed seed 26). The target
starts at x = 0 and the truth at step k is k meters.

Run:

    rng = random.Random(26)
    truth = [1.0 * k for k in range(20)]
    z = [t + rng.gauss(0.0, 1.0) for t in truth]
    res = run_particle_filter(z, 1.0, 5000, (0.0, 5.0), 0.5, 1.0, 7,
                              velocity=1.0)

Selected steps (mean of the posterior against the truth):

| k | truth (m) | z (m) | estimate (m) | std (m) | resampled |
|---|---|---|---|---|---|
| 0 | 0.00 | -0.01 | 0.050 | 0.992 | yes |
| 5 | 5.00 | 5.60 | 5.809 | 0.614 | no |
| 10 | 10.00 | 8.37 | 9.096 | 0.622 | yes |
| 13 | 13.00 | 12.91 | 12.735 | 0.619 | yes |
| 15 | 15.00 | 13.54 | 14.557 | 0.619 | no |
| 17 | 17.00 | 16.96 | 16.871 | 0.620 | yes |
| 19 | 19.00 | 18.73 | 19.004 | 0.614 | no |

The prior uncertainty of 5 m collapses in a few steps and the
posterior standard deviation settles near 0.62 m, the information
balance between the 0.5 m process noise and the 1.0 m measurement
noise. From step 13 on the estimate stays within 0.5 m of the truth
(largest error over steps 13 to 19 is 0.44 m) and the terminal
estimate at step 19 is 19.004 m, an error of 0.004 m against the true
19.0 m. Resampling fires on 6 of the 20 steps whenever the effective
sample size dips below 2500, then the ensemble returns to equal
weights. ESS runs between roughly 1300 and 4250.

Multimodal case that a Gaussian filter cannot represent: a squared
-range sensor h(x) = x^2 observes a target that starts at x0 = +4.0 m
and recedes at v = 0.4 m/s (process std 0.1 m, measurement std 1.5
on the squared range, prior split between the +4 and -4 corridors,
2000 particles per corridor, measurement seed 5, filter seed 3). The
first echo near z = 14.2 fits both corridors: the posterior standard
deviation stays near 3.7 m and the mass on the positive corridor is
about 0.36, so both hypotheses survive. An EKF linearized about x = 0
has Jacobian dh/dx = 2x = 0 there and would not move; a UKF forced to
one mode must guess the sign. As the target recedes the squared range
grows like (4 + 0.4 t)^2, the mirror corridor loses likelihood, and by
step 2 more than 99.9% of the weight sits on the true corridor. The
run ends at step 9 with the estimate 7.604 m against the truth 7.60 m.

## Verification

- Confirm the worked example numbers exactly: the step-19 estimate is
  19.0039 m against truth 19.0 m, and every step from 13 on is within
  0.5 m of the truth for the fixed seeds above.
- Confirm the deterministic checks: initialize_particles reproduces
  the prior mean and std for a large sample; predict advances the mean
  by v * dt; the process noise widens the cloud by process_std;
  update_weights at the exact measurement keeps weight 1.0 and at one
  measurement-noise sigma multiplies by exp(-0.5).
- Confirm the bimodal contract: with the range-squared sensor the
  early posterior keeps both sign modes (std above 2 m, corridor mass
  between 0.2 and 0.8) and the late posterior concentrates on the true
  corridor (mass above 0.999).
- Confirm the resampling trigger: the resampled flag is True exactly
  when the effective sample size is below n / 2, and resampling always
  returns equal weights 1/n.
- Confirm ValueError rejection of non-physical inputs: n <= 0,
  negative prior/process/measurement standard deviations, dt <= 0,
  empty particle or weight lists, mismatched particle and weight array
  lengths, negative weights, and a collapsed (zero-total) posterior.
- Confirm run-to-run reproducibility: the same seed returns identical
  estimate trajectories.
- Run the contract test offline: python3
  scripts/test_particle_filter.py (34 tests, deterministic).

## Related leaves

- navigation/kalman-filter-design: the linear Gaussian filter; the
  analytic optimum when the model is linear and the posterior Gaussian.
- estimation-filtering/extended-kalman-filter: Jacobian-linearized
  filter for mildly nonlinear models with a unimodal posterior; the
  particle filter removes the linearization and the unimodality.
- estimation-filtering/unscented-kalman-filter: sigma-point filter for
  nonlinear models; like the EKF it still closes the posterior in one
  Gaussian, so bimodal likelihoods are out of scope.
- estimation-filtering/alpha-beta-filter: fixed-gain tracker for
  linear constant-velocity problems, the cheapest alternative when no
  full posterior is required.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_particle_filter.py

The test covers Gaussian prior initialization and its moments,
constant-velocity drift and random-walk spread, the hand-computed
Gaussian likelihood weights and the zero-measurement-noise limit, the
bimodal range-squared likelihood, normalization, effective sample
size, systematic resampling (equal weights, dominance of heavy
particles, weighted-mean preservation, seeded determinism), the
weighted mean and standard deviation, the worked-example convergence
(20 step run at 1.0 m/s, seed 7, final error 0.004 m), the
resampling-trigger consistency, run-to-run reproducibility, the
bimodal corridor scenario that keeps both modes alive and then
concentrates on the true corridor, and ValueError rejection of all
non-physical inputs.

## Compliance

- ARP4754A is proprietary (SAE); name and paraphrase only per
  standards-map.yaml, reference-only: true.
- compliance: STANDARDS-REF, gated: false.

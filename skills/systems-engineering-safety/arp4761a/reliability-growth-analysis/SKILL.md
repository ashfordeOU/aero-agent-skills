---
name: reliability-growth-analysis
description: 'Use when you must determine whether a system failure rate is improving over development or field test time: fit the Duane growth slope by ordinary least squares of the log cumulative failure rate on log cumulative time, fit the Crow-AMSAA power-law process shape beta by deterministic MLE bisection, and read the growth verdict off the fitted shape against the 1.0 boundary. Produces the duane-growth-slope, the amsaa-shape-beta with the lambda scale, the fitted current-mtbf under both estimators, the projected-mtbf at a target cumulative test time, and the improving, hpp-constant or degrading verdict that decides whether continued testing or a corrective redesign is warranted. Trigger: reliability growth analysis, duane-growth-slope, amsaa-shape-beta, growth-verdict, test-time-projection, fitted current-mtbf, power-law process, cumulative test time.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: arp4761a
  reference-only: true
gated: false
domain: systems-engineering-safety
pack: arp4761a
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: systems-engineering-safety
  subdomain: arp4761a
  tags:
  - reliability-growth-analysis
  - duane-growth-slope
  - amsaa-shape-beta
  - growth-verdict
  - test-time-projection
  version: 0.1.0
  author: AeroSkills
---

# Reliability Growth Analysis (systems-engineering-safety/arp4761a/reliability-growth-analysis)

Use when the question is whether a system failure rate is improving,
constant, or degrading over development or field test time, answered by
fitting a reliability growth model to the ordered cumulative failure
times. This leaf fits the Duane plot by OLS as the quick graphical
check and the Crow-AMSAA power-law process (the MIL-HDBK-189 method,
named and paraphrased, no verbatim text) by MLE as the reference
estimator, then projects the fitted MTBF forward and inverts the
projection for the test hours at which a target MTBF is reached. It
pairs with the constant-rate sibling arp4761a/failure-rate-estimation,
whose point estimate and statistical bounds assume the rate does not
change over the exposure; that leaf deliberately excludes any trend
fit, which is the whole claim here. Field event review against
predicted rates belongs to continued-airworthiness/in-service-safety-
assessment and the post-implementation rollup to
arp4761a/ssa-closure; this leaf never consumes a safety objective and
never runs fault tree, Markov, or RBD math.

## Domain quick reference

- Inputs: ordered cumulative failure times t_1 through t_N from a
  time-truncated development or field test with truncation time T
  (total_time). Every failure time must be below T, positive, and
  non-decreasing.
- Power-law process mean: E[N(t)] = lambda * t**beta, the Crow-AMSAA
  model. beta below 1 drives the instantaneous rate down over time
  (improving), beta above 1 drives it up (degrading), beta at 1 keeps
  it constant.
- Duane plot: cumulative point i is (t_i, i) with cumulative failure
  rate i / t_i. OLS of ln(i / t_i) on ln(t_i) over the N failure-event
  points gives the slope and intercept; under the power-law process the
  cumulative rate is lambda * t**(beta - 1), so the Duane slope equals
  beta - 1 and the intercept equals ln(lambda). beta_duane = slope + 1,
  and a negative slope is the growth signature.
- Instantaneous intensity and MTBF: the instantaneous failure intensity
  is lambda * beta * t**(beta - 1), so the instantaneous MTBF is its
  reciprocal. At the truncation time the AMSAA current MTBF collapses to
  the standard form T / (N * beta_hat).
- AMSAA MLE: with S = sum over failures of ln(T / t_i), the
  profile-likelihood equation is N / beta_hat = S, with the closed form
  beta_hat = N / S. This module solves it by deterministic bisection of
  g(beta) = N / beta - S on the fixed bracket [1e-6, 10.0] to 1e-12,
  capped at 200 passes, and lambda_hat = N / T**beta_hat. The bisection
  root matches N / S within 1e-9 on every spec anchor.
- Duane current MTBF at evaluation time t:
  exp(-intercept) / (beta_duane * t**(beta_duane - 1)).
- Projection: the fitted process reaches
  current_mtbf * (tau / T)**(1 - beta) at tau cumulative test hours,
  which grows with tau while beta stays below 1.
- Verdict boundary at exactly 1.0: beta below 1 improving, beta equal
  to 1.0 hpp-constant (the constant-rate homogeneous process of the
  failure-rate-estimation sibling), beta above 1 degrading. When the
  Duane and AMSAA betas disagree about the side of 1.0, the AMSAA MLE
  governs the verdict.
- Module constants: MIN_FAILURES = 2, BISECT_LO = 1e-6, BISECT_HI =
  10.0, BISECT_TOL = 1e-12, BISECT_MAX_ITER = 200.

## Workflow

1. Assemble the ordered failure times and fix the truncation time: the
   cumulative failure times fail_times and the total_time T of the
   time-truncated test, with at least MIN_FAILURES = 2 events and every
   failure time positive and below T.
2. Quick Duane growth check: run duane_fit(fail_times, evaluation_time
   = T) for the growth slope, the intercept, beta_duane and the fitted
   current_mtbf of the line at T. A negative slope with beta_duane
   below 1 is the improving signature; pass no evaluation_time to read
   the line at the last failure time instead.
3. Crow-AMSAA MLE fit: run amsaa_mle(fail_times, T) for beta_hat
   (deterministic bisection of the MLE equation on the fixed bracket),
   lambda_hat, the standard current_mtbf T / (N * beta_hat) and the
   bisection_iterations count. Cross-check the root against the closed
   form N / S.
4. Growth verdict: run growth_verdict(beta) with the AMSAA beta_hat
   (or beta_duane for the quick check) and read improving, hpp-constant
   or degrading off the exact 1.0 boundary. The AMSAA MLE governs when
   the two estimators disagree about the side.
5. MTBF projection: run projected_mtbf(target_time, T, N, beta_hat) for
   the MTBF the fitted process reaches at a future cumulative test
   time; at target_time equal to T it returns the current MTBF exactly.
6. Test-hours inversion: run test_hours_to_target_mtbf(target_mtbf, T,
   N, beta_hat) for the cumulative test hours tau at which the fitted
   MTBF equals the target. Requires beta_hat below 1.0; a degrading or
   constant fitted shape means the target is unreachable by continued
   testing. Round-trip tau back through projected_mtbf to confirm the
   target.
7. Contract confirmation: run the deterministic contract test
   python3 scripts/test_reliability_growth_analysis.py (35 tests,
   offline) to confirm the anchors, identities and rejection behavior.

## Worked example

Time-truncated development test: T = 8000 h with N = 6 failures at
fail_times = [200, 420, 800, 1500, 3000, 5000] h. The inter-failure
gaps grow, an improving system.

- duane_fit(fail_times, evaluation_time = 8000.0): slope =
  -0.465700634065, intercept = -2.63108358662, beta_duane =
  0.534299365935, current_mtbf = 1708.25187489 h. The negative slope is
  the Duane growth signature.
- amsaa_mle(fail_times, 8000.0): S = 12.0634793832, beta_hat =
  0.497379804338 found by bisection in 43 passes and matching the
  closed form N / S to 5.21e-13, lambda_hat = 0.0686804475182,
  current_mtbf = 2680.71466051 h (8000 / (6 * 0.497379804338)). Both
  estimators place beta below 1: improving.
- growth_verdict(0.497379804338): {"beta": 0.497379804338, "verdict":
  "improving"}.
- projected_mtbf(12000.0, 8000.0, 6, 0.497379804338) = 3286.68144148
  h, the MTBF the fitted process reaches at 12,000 cumulative test
  hours.
- test_hours_to_target_mtbf(5000.0, 8000.0, 6, 0.497379804338) =
  27650.7080495 cumulative test hours to a 5000 h target MTBF;
  projecting back to that tau returns 5000.0 within 1e-6 (round-trip
  identity).

Contrast degrading set: fail_times = [500, 800, 1050, 1250, 1400,
1500] h with T = 1600 h. amsaa_mle gives beta_hat = 2.20390414872 and
current_mtbf = 120.997397651 h; duane_fit gives slope = 0.595086501988
and beta_duane = 1.595086501988; growth_verdict reads degrading. The
positive Duane slope and beta above 1 flag wear-out style data, and
more testing under this model never reaches a target MTBF.

## Verification

- duane_fit on the worked improving set returns slope -0.465700634065
  and beta_duane 0.534299365935 within 1e-9 and current_mtbf
  1708.25187489 h within 1e-3, matching the spec anchors.
- amsaa_mle on the same set returns beta_hat 0.497379804338 within 1e-9
  of both the spec anchor and the closed form N / S, lambda_hat
  0.0686804475182 within 1e-9, and current_mtbf 2680.71466051 h within
  1e-3.
- Identity checks hold: lambda_hat * T**beta_hat equals N; current_mtbf
  * N * beta_hat equals T; projected_mtbf at target_time equal to
  total_time returns current_mtbf exactly; the test-hours inversion
  round-trips through projected_mtbf back to the target MTBF.
- Verdict thresholds sit at exactly 1.0: 0.7 improving, 1.0
  hpp-constant, 1.3 degrading, with dict keys exactly beta and verdict.
- Non-physical inputs raise ValueError: fewer than two failures, a
  zero or negative failure time, decreasing failure times, a failure
  time at or above the truncation time, a non-positive total_time or
  evaluation_time, an evaluation_time below the last failure time,
  all-equal failure times (zero ln-time variance), an AMSAA MLE root
  outside the fixed bracket, a test-hours inversion with beta at or
  above 1.0, and non-positive targets.
- The workflow is deterministic: repeated runs return bit-identical
  dicts and the bisection returns the same root on every run.

## Related leaves

- systems-engineering-safety/arp4761a/failure-rate-estimation: the
  constant-rate sibling; point estimate and statistical bounds of a
  rate that does not change over the exposure, plus fixed-rate test
  planning. Use it when the growth hypothesis has been rejected, never
  for trend or slope questions.
- systems-engineering-safety/continued-airworthiness/in-service-safety-
  assessment: field review of observed event rates against predicted
  rates from the safety objective, with trend entering only as a
  routing direction, no growth-curve fit.
- systems-engineering-safety/arp4761a/ssa-closure: rolls post-
  implementation predicted probabilities up against per-severity
  targets and does not consume observed fleet data.
- systems-engineering-safety/arp4761a/reliability-block-diagram,
  systems-engineering-safety/arp4761a/markov-analysis and
  systems-engineering-safety/arp4761a/fta-fmea: downstream consumers
  that take rates as inputs; this leaf does not run their math.

## Contract test

Run offline and deterministic:

    python3 scripts/test_reliability_growth_analysis.py

The 35 unittest methods exercise every SKILL.md workflow step: the
quick Duane growth check (worked improving and degrading slopes,
beta_duane, current MTBF, evaluation-time default, exact result keys),
the Crow-AMSAA MLE fit (worked beta, lambda and current MTBF, bisection
against the closed form, the 43-pass convergence, scale and current
MTBF identities, the degrading set), the growth verdict branches, the
MTBF projection (anchor value, exact return at the truncation time,
monotonicity), the test-hours inversion (anchor value, round trip,
below-current target), and the ValueError rejection list plus
bit-identical determinism.

## Compliance

- Standards referenced, not reproduced: ARP4761A frames the system
  safety assessment context (reference-only per standards-map.yaml) and
  the Crow-AMSAA method is the MIL-HDBK-189 reliability-growth
  procedure, named and paraphrased here with no verbatim standard text.
- compliance: STANDARDS-REF, gated: false. The model is the power-law
  NHPP with no covariate or repair-content term; trend analysis only,
  no interval estimates on the growth parameters.

## Pitfalls

- Reading the Duane slope as the shape: the Duane slope equals beta -
  1, so beta_duane = slope + 1. Quoting the worked slope -0.4657 as
  beta would understate the fitted shape (the true beta_duane is
  0.5343) and can flip the verdict side in marginal cases.
- Inverting the projection on a degrading or constant fit: a beta at or
  above 1.0 means the instantaneous rate is not falling, so no amount
  of continued testing reaches the target MTBF under the fitted model;
  the test-hours inversion raises ValueError and the correct action is
  a corrective redesign, not more test time.
- Trusting the Duane verdict when the estimators disagree: the OLS fit
  on the cumulative points is the quick graphical check and the AMSAA
  MLE is the reference estimator, so when the two betas sit on
  different sides of 1.0 the AMSAA MLE governs the verdict.
- Forgetting the evaluation time in duane_fit: current_mtbf is read
  off the fitted line at evaluation_time, which defaults to the last
  failure time, not the truncation time. On the worked set the line
  value at 5000 h differs from the value at the 8000 h truncation, so
  pass evaluation_time = T explicitly for the current MTBF.
- Treating the test as failure-truncated: the estimators here consume
  the truncation time T and reject any failure time at or above it; a
  failure-time-truncated campaign with the last event at T needs the
  failure-truncated form, not a silent re-labeling.
- Claiming a fixed-rate result from growth data: a beta clearly below
  1.0 invalidates the constant-rate assumption of the
  failure-rate-estimation sibling; its point-estimate and bounds
  workflow only applies once the growth verdict lands on hpp-constant.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_reliability_growth_analysis.py

The test must pass with exit 0. It covers the spec worked anchors
(Duane slope and beta_duane, AMSAA beta_hat and lambda_hat, both
current MTBF values, the projected MTBF at 12,000 h, the test-hours
inversion to 27,650.7 h, the degrading-set beta 2.20390414872), the
closed-form and identity checks (bisection root against N / S, lambda
scale identity, current MTBF identity, projection round trips), the
improving and degrading verdict branches at the exact 1.0 boundary, and
ValueError rejection of every non-physical input in the validation
list, all deterministic across repeated runs.

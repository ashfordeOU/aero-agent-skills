---
name: maintainability-prediction
description: 'Use when you must roll LRU-level failure rates and repair-task times into a system maintainability prediction: compute the failure-rate-weighted MTTR as the lambda-weighted mean of the per-LRU mean repair times, build the lognormal repair-time model on the failure-rate-weighted median t50, derive the t50 and t95 repair-time percentiles with the Acklam inverse normal quantile, and pass or fail the predicted t95 against the maximum-repair-time requirement with the margin. Produces the weighted MTTR, the t50 and t95 repair times with the lognormal sigma, the verdict and margin, and the per-LRU expected-downtime rollup. Trigger: maintainability prediction, failure-rate-weighted mttr, mttr rollup, mean time to repair, lognormal repair-time model, repair-time percentile, t95 repair time, maximum-repair-time requirement.'
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
  - maintainability-prediction
  - failure-rate-weighted-mttr
  - lognormal-repair-time
  - repair-time-percentile
  - maximum-repair-time-requirement
  version: 0.1.0
  author: AeroSkills
---

# Maintainability Prediction (systems-engineering-safety/arp4761a/maintainability-prediction)

Use when the question is how long a fleet of line-replaceable units
(LRUs) takes to repair, answered from the per-LRU failure rates and
repair-task times. This leaf rolls the LRU-level inputs into the
failure-rate-weighted mean time to repair, builds the lognormal
repair-time model on the failure-rate-weighted median repair time
t50, derives the t50 and t95 repair-time percentiles with the
embedded Acklam inverse normal quantile, and passes or fails the
predicted t95 against the 2 h maximum-repair-time requirement with
the margin. It pairs with the same-pack sibling
systems-engineering-safety/arp4761a/markov-analysis, whose two-state
model takes the repair rate mu (per hour) as a given input and never
derives it from repair-task times: this leaf is exactly that
derivation, so mu = 1/MTTR turns the per-LRU downtime rollup into a
checkable steady-state input for the quantitative safety case. The
lognormal sigma is an engineering input chosen from fleet data or
the documented default, never fitted by this leaf.

## Domain quick reference

- Inputs: items as a list of (lambda_i, mttr_s_i) tuples, lambda_i
  the per-hour failure rate and mttr_s_i the LRU mean or median
  repair time in seconds. Repair times and MTTR are in seconds;
  failure rates are per hour.
- Failure-rate-weighted MTTR (the classic rollup): sum(lambda_i *
  mttr_s_i) / sum(lambda_i), the lambda-weighted arithmetic mean of
  the per-LRU mean repair times. Equal rates collapse it to the plain
  arithmetic mean.
- Failure-rate-weighted median t50: exp(sum(lambda_i * ln(mttr_s_i))
  / sum(lambda_i)), the lambda-weighted geometric mean of the per-LRU
  median repair times. This t50 is the median parameter of the system
  lognormal repair-time model and always sits below the weighted MTTR
  for any positive spread.
- Lognormal repair-time model: t_p = t50 * exp(sigma * z_p) with z_p
  the standard normal quantile and sigma the log-space spread
  (REPAIR_TIME_SIGMA_DEFAULT = 0.5 typical for avionics and
  mechanical LRUs when fleet data is absent). t50 = t50 exactly at
  p = 0.5 (z = 0); sigma = 0 collapses every percentile onto the
  median.
- Acklam inverse normal quantile: z_p computed with the published
  coefficient sets, the central polynomial between the tail split at
  P_LOW = 0.02425 and its mirror, the tail rational form outside,
  and one refinement step through math.erfc. normal_quantile(0.5) =
  0.0 exactly and normal_quantile(0.95) = 1.6448536269514726.
- Verdict: PASS when t95 <= MAX_REPAIR_TIME_LIMIT_S (7200.0 s, the
  documented 2 h maximum-repair-time requirement, boundary
  inclusive), else FAIL; margin_s = limit - t95, non-negative on
  PASS, the negative shortfall on FAIL.
- Expected-downtime rollup over an exposure: per-LRU downtime D_i =
  lambda_i * exposure_hours * (mttr_s_i / 3600.0) hours, total the
  sum, expected unavailability = total / exposure_hours. This is the
  small-unavailability approximation: it reproduces the
  markov-analysis two-state steady state lambda/(lambda + mu) with
  mu = 1/MTTR_h only in the limit lambda * MTTR_h << 1; the exact
  two-state value is the markov-analysis function's job.
- Module constants: MAX_REPAIR_TIME_LIMIT_S = 7200.0,
  REPAIR_TIME_SIGMA_DEFAULT = 0.5, SECONDS_PER_HOUR = 3600.0.

## Workflow

1. Assemble the LRU fleet: the items list of per-LRU failure rates
   lambda_i (per hour) and repair times mttr_s_i (seconds), one
   (lambda, mttr_s) pair per LRU, each positive.
2. Failure-rate-weighted MTTR rollup: run
   failure_rate_weighted_mttr(items) for the lambda-weighted
   arithmetic mean of the per-LRU mean repair times, the headline
   system MTTR in seconds (and hours).
3. Failure-rate-weighted t50 median parameter: run
   failure_rate_weighted_median(items) for the lambda-weighted
   geometric mean of the per-LRU median repair times, the t50 median
   of the system lognormal repair-time model. Confirm t50 sits below
   the MTTR of step 2.
4. Normal quantile: run normal_quantile(p) for the z_p behind every
   repair-time percentile (Acklam inverse normal CDF, deterministic,
   math.erfc refinement).
5. Repair-time percentiles: choose the lognormal sigma (fleet-data
   value or REPAIR_TIME_SIGMA_DEFAULT = 0.5) and run
   lognormal_percentile(t50, sigma, 0.95) for the t95 repair-time
   percentile and lognormal_percentile(t50, sigma, 0.5) for the t50
   identity.
6. Maximum-repair-time verdict: run maintainability_verdict(t95,
   requirement_limit = MAX_REPAIR_TIME_LIMIT_S) for the PASS or FAIL
   verdict and margin_s against the 2 h maximum-repair-time
   requirement (7200.0 s). A negative margin is the shortfall that
   must be closed by faster repairs or a lower spread.
7. Expected-downtime rollup: run lru_downtime_rollup(items,
   exposure_hours) for the per-LRU expected downtime hours, the total
   over the exposure, and the expected unavailability that gate the
   maintainability input to the system safety case.
8. Contract confirmation: run the deterministic contract test
   python3 scripts/test_maintainability_prediction.py (35 tests,
   offline) to confirm the anchors, identities and rejections.

## Worked example

Wide-spread 5-LRU fleet (rates per hour, median repair times in
seconds): electro-hydraulic actuator 4.0e-5 and 5400, servo control
electronics 1.2e-5 and 9000, rate sensor unit 8.0e-6 and 2700, power
drive unit 2.0e-5 and 10800, control surface position sensor 6.0e-6
and 3600. Total rate 8.6e-5 per hour.

- failure_rate_weighted_mttr = 6781.3953 s (1.8837 h): the high-rate
  1.5 h and 3.0 h LRUs dominate the arithmetic rollup.
- failure_rate_weighted_median t50 = 6209.6647 s (1.7249 h), below
  the MTTR as the lognormal median must sit under the arithmetic
  mean.
- With sigma = 0.6: t95 = lognormal_percentile(6209.6647, 0.6, 0.95)
  = 16660.1405 s (4.6278 h), verdict FAIL against the 7200 s (2 h)
  requirement with margin_s = -9460.1405 s: 95 percent of repairs
  would exceed the 2 h maximum-repair-time limit.
- Sensitivity: with sigma = 0.3 the same fleet gives t95 =
  10171.2283 s, still FAIL; the verdict flips only below sigma =
  0.089962 (ln(7200.0 / t50) / normal_quantile(0.95)), where t95 =
  7200.0000 s and the verdict reads PASS with margin 0.0, showing how
  narrow the repair-time spread must be for this fleet to satisfy a
  2 h t95 limit.
- Downtime rollup over 4000 flight hours: per-LRU downtime hours
  [0.2400, 0.1200, 0.0240, 0.2400, 0.0240], total 0.6480 h,
  expected unavailability 1.62e-4, consistent with sum(lambda *
  MTTR_h) = 8.6e-5 * 1.8837 = 1.62e-4 and with the two-state steady
  state when mu = 1/MTTR in the small-product limit.

Compact 4-LRU fleet (PASS case under the default sigma): servo
actuator 3.0e-5 and 1440, controller unit 1.5e-5 and 2160, sensor
module 9.0e-6 and 1800, power supply 1.2e-5 and 2880. Total rate
6.6e-5 per hour.

- failure_rate_weighted_mttr = 1914.5455 s (0.5318 h); t50 =
  1846.4220 s (0.5129 h).
- With sigma = REPAIR_TIME_SIGMA_DEFAULT = 0.5: t95 =
  lognormal_percentile(1846.4220, 0.5, 0.95) = 4202.4871 s (1.1674
  h), verdict PASS with margin_s = +2997.5129 s: the 2 h requirement
  is met with margin.

Quantile anchors: normal_quantile(0.5) = 0.0 exactly;
normal_quantile(0.95) = 1.6448536269514726 (matches the published
Acklam value to 1e-15); t50 identity lognormal_percentile(6210.0,
0.6, 0.5) = 6210.0 exactly.

## Verification

- failure_rate_weighted_mttr returns 6781.3953 s on the wide fleet
  and 1914.5455 s on the compact fleet within 1e-3; equal rates
  return the plain arithmetic mean (5400.0 s on the 3600/7200 pair).
- failure_rate_weighted_median returns 6209.6647 s (wide) and
  1846.4220 s (compact) within 1e-3 and, with equal rates, the
  geometric mean sqrt(3600.0 * 7200.0) within 1e-9; t50 < MTTR on
  both fleets.
- normal_quantile(0.5) is 0.0 exactly and normal_quantile(0.95) is
  1.6448536269514726 within 1e-12; the tail split at P_LOW =
  0.02425 stays finite and monotone.
- lognormal_percentile(6209.6647, 0.6, 0.95) = 16660.1405 s within
  1e-2; the t50 identity holds exactly at p = 0.5; sigma = 0
  collapses every percentile onto the median; percentiles grow
  monotonically in both p and sigma.
- maintainability_verdict(16660.1405) = FAIL with margin -9460.1405 s
  within 1e-2, maintainability_verdict(4202.4871) = PASS with margin
  +2997.5129 s within 1e-2, the boundary t95 = 7200.0 s passes with
  margin 0.0, and a custom limit is honored.
- lru_downtime_rollup(wide, 4000.0) returns per-LRU hours [0.24,
  0.12, 0.024, 0.24, 0.024], total 0.648 h and expected
  unavailability 1.62e-4 within the spec tolerances.
- Non-physical inputs raise ValueError across the module: empty
  items, zero or negative rates, all-zero total rate, zero or
  negative repair times, zero or negative exposure, p at 0 or 1,
  zero or negative median, negative sigma, non-positive t95 and
  non-positive requirement limit.
- All functions are deterministic: repeated calls return bit-identical
  results and every dict carries exactly the documented keys.

## Related leaves

- systems-engineering-safety/arp4761a/markov-analysis: the same-pack
  quantitative-safety sibling that consumes the repair rate mu per
  hour as a given input; this leaf derives mu = 1/MTTR from
  repair-task times, the derivation markov-analysis never performs.
- systems-engineering-safety/arp4761a/fault-tree-uncertainty-
  analysis: its embedded normal quantile serves epistemic uncertainty
  on fault tree output, never repair-time percentiles.
- systems-engineering-safety/arp4761a/operating-support-hazard-
  analysis: maintenance enters there as a hazard source scored on the
  risk matrix, with no repair-task times.
- systems-engineering-safety/continued-airworthiness/msg3-maintenance-
  analysis: scheduled maintenance task-category selection and interval
  assignment, not time-to-repair statistics.
- vehicle-design/cost-estimation/life-cycle-cost: consumes MTTR only
  as a dollar-valued input to operating and support cost.
- cross-cutting/numerics/probability-distributions and cross-cutting/
  numerics/descriptive-statistics: fit distributions to a data sample
  and return empirical sample percentiles; this leaf neither fits a
  lognormal to data nor reports sample statistics.
- avionics/flight-management/rnp-anp-containment: its 95th percentile
  is a navigation-error containment bound, unrelated to repair time.

## Contract test

Run offline and deterministic:

    python3 scripts/test_maintainability_prediction.py

The 35 unittest methods exercise every SKILL.md workflow step: the
fleet assembly (step 1), the failure-rate-weighted MTTR rollup
(step 2, worked anchors 6781.3953 and 1914.5455 s and the
equal-rates arithmetic-mean identity), the failure-rate-weighted t50
median parameter (step 3, anchors 6209.6647 and 1846.4220 s, the
geometric-mean identity and t50 below MTTR), the Acklam normal
quantile (step 4, exact 0.0 at p = 0.5, the published 1.6448536269514726
anchor, monotonicity across the tail switch and symmetry), the
lognormal t50 and t95 repair-time percentiles (step 5, anchors
16660.1405 and 4202.4871 s, the t50 identity, sigma-zero collapse,
monotonicity in p and sigma), the maximum-repair-time verdict
(step 6, FAIL and PASS margins, the inclusive 7200 s boundary, a
custom limit and the flip-sigma boundary construction), the per-LRU
expected-downtime rollup (step 7, the wide-fleet anchor and the
rate-times-MTTR product identity), the full ValueError rejection
list, and bit-identical determinism with exact dict keys (step 8).

## Compliance

- Standards referenced, not reproduced: ARP4761A frames the system
  safety assessment context (reference-only per standards-map.yaml);
  the failure-rate-weighted rollup and lognormal repair-time model
  are standard maintainability engineering methodology,
  summary-only, no verbatim standard text.
- The Acklam inverse normal quantile is the published numerical
  method (Wichura-style rational approximation with coefficient
  sets), implemented from the public algorithm, not from any standard
  document.
- compliance: STANDARDS-REF, gated: false. The lognormal sigma is an
  engineering input chosen from fleet data or REPAIR_TIME_SIGMA_DEFAULT,
  never estimated by this leaf.

## Pitfalls

- Treating the lognormal median as the mean: the repair-time model is
  lognormal on the weighted median t50, so the headline system MTTR
  (6781.3953 s on the wide fleet) always exceeds the t50 parameter
  (6209.6647 s). Feeding the MTTR in as the lognormal median shifts
  every percentile up and can flip a PASS to a FAIL.
- Judging the requirement on the MTTR: the verdict runs on the t95
  repair-time percentile against the 2 h limit, never on the mean.
  The wide fleet looks moderate at 1.88 h mean yet fails hard with a
  4.63 h t95; 95 percent of repairs is the requirement metric.
- Quoting the requirement as a fixed number without the boundary
  convention: the verdict is inclusive at the boundary, t95 = 7200.0 s
  exactly is PASS with margin 0.0, and the flip sigma is solved from
  ln(7200.0 / t50) / normal_quantile(0.95), not guessed.
- Mixing units: failure rates are per hour while repair times are in
  seconds, so the weighted MTTR comes out in seconds and must be
  divided by SECONDS_PER_HOUR before it becomes the mu = 1/MTTR_h
  input to the two-state model or the downtime product lambda *
  exposure * MTTR_h.
- Reading the downtime rollup as exact unavailability: the rollup
  total over exposure hours is the small-product approximation
  lambda * MTTR_h; it equals the markov-analysis steady-state value
  only when lambda * MTTR_h << 1, and the exact two-state number is
  that leaf's function.
- Inventing a sigma from the data: this leaf never fits the lognormal
  to a repair-time sample; sigma is chosen from fleet data or the
  documented default 0.5, and the spread assumption drives the t95
  verdict as the 0.6-versus-0.3 wide-fleet comparison shows.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_maintainability_prediction.py

The test must pass with exit 0. It covers the spec worked anchors
(weighted MTTR 6781.3953 and 1914.5455 s, weighted median t50
6209.6647 and 1846.4220 s, t95 16660.1405 s at sigma 0.6 and
4202.4871 s at the default sigma, FAIL margin -9460.1405 s, PASS
margin +2997.5129 s, rollup total 0.648 h at 1.62e-4), the identity
and closed-form checks (equal-rates arithmetic and geometric means,
exact normal_quantile(0.5) = 0.0, the published 0.95 quantile, the
t50 percentile identity, sigma-zero collapse, the rate-times-MTTR
product identity and the flip-sigma boundary), the inclusive 7200 s
verdict boundary, the full ValueError rejection list for every
non-physical input, exact documented dict keys, and bit-identical
determinism across repeated calls.

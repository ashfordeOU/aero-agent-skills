# Wave-41 leaf spec: maintainability-prediction (arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/maintainability-prediction/
- Pack: arp4761a (verified present at prep with 18 leaves, no
  maintainability leaf among them; leaf absent confirmed by
  ls skills/systems-engineering-safety/arp4761a/ plus git grep
  'maintainability|mttr|mean time to repair' across skills/, which hits
  only vehicle-design/cost-estimation/life-cycle-cost/SKILL.md and a
  space-systems/ecss software-verification test script).
- Fences read at prep (claims quoted verbatim from their SKILL.md files):
  - markov-analysis (same pack, the quantitative-safety sibling this leaf
    derives from): frontmatter claims it "compute[s] continuous time
    Markov chain state probabilities from the transition rate matrix,
    evaluate[s] two-state failure and repair availability ... derive[s]
    the non-repairable failure probability and the mean time to failure";
    its domain reference states "Two-state failure and repair model:
    P_failed(t) = lam/(lam+mu) * (1 - exp(-(lam+mu) t)); steady state
    unavailability is lam/(lam+mu) and availability is mu/(lam+mu)". Its
    logic validates the repair side with _require_positive(mu, "repair
    rate mu") and its module docstring calls mu "the repair rate, per
    hour": mu is a GIVEN INPUT, never derived from repair-task times, and
    no MTTR, repair-time distribution or percentile function exists in
    that leaf. The failure-rate-weighted MTTR and lognormal repair-time
    percentiles of this spec are exactly the derivation markov-analysis
    never performs.
  - fault-tree-uncertainty-analysis (same pack): claims it converts
    "each basic-event lognormal error factor to a lognormal sigma with
    the 90 percent normal quantile" for tree-probability epistemic
    confidence bands: its embedded normal quantile serves FTA
    uncertainty, never repair-time percentiles.
  - operating-support-hazard-analysis (same pack): claims it identifies
    "hazards from operational scenarios and maintenance tasks" and that
    "a maintenance task is critical when it involves an unacceptable
    hazard": maintenance enters as a HAZARD source scored on the risk
    matrix, no repair-task times anywhere.
  - msg3-maintenance-analysis (continued-airworthiness pack): claims it
    "categorize[s] each failure mode ... select[s] the applicable
    scheduled maintenance task categories ... assign[s] the interval
    verdict", and its body states "It is the decision logic for scheduled
    maintenance task selection, not a reliability calculation": task
    selection and intervals, no time-to-repair statistics.
  - vehicle-design/cost-estimation/life-cycle-cost: claims cost drivers
    include "reliability (MTBF) and maintainability (MTTR)": MTTR enters
    only as a dollar-valued input to O&S cost, never computed or
    rolled up.
  - cross-cutting/numerics/probability-distributions: fits normal,
    lognormal, exponential and Weibull parameters FROM a data sample
    (pdf/cdf/quantile of a fitted law); owns the bare lognormal-fitting
    token, not a failure-rate-weighted repair-time model.
  - cross-cutting/numerics/descriptive-statistics: empirical sample
    percentiles by linear interpolation ("no distribution fitting");
  - avionics/flight-management/rnp-anp-containment: "ANP is the 95th
    percentile lateral" navigation-error bound, 2 * sigma_lateral_m.
    Whole-tree greps at prep: no leaf anywhere computes a failure-rate-
    weighted MTTR, a repair-time lognormal, or a t95 repair time.
    GENUINE gap: the arp4761a pack quantifies failure probability and
    takes repair rate mu as input (markov-analysis) but nothing derives
    the repair side of the maintainability story from per-LRU repair
    times.
- Standards id: arp4761a (reference-only, exists in standards-map.yaml).
  Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Roll line-replaceable-unit (LRU) failure rates and repair-task times into
a system maintainability prediction: compute the failure-rate-weighted
MTTR as the lambda-weighted arithmetic mean of the per-LRU mean repair
times, build the lognormal repair-time model on the failure-rate-weighted
median repair time t50 (the lambda-weighted geometric mean), and derive
the t50 and t95 repair-time percentiles as t_p = t50 * exp(sigma * z_p)
with z_p from the embedded Acklam inverse normal quantile, all pure
stdlib and deterministic; finally pass or fail the predicted t95 against
a maximum-repair-time requirement with the margin reported. This is the
repair-side derivation markov-analysis never performs: that leaf takes
the repair rate mu (per hour) as a given input and never derives it from
repair-task times, so pairing this rollup with the markov-analysis
two-state model gives mu = 1/MTTR and a checkable steady-state
unavailability lambda/(lambda + mu) only as the small-product limit of
the per-LRU downtime rollup. Produces the system failure-rate-weighted
MTTR, the t50 and t95 repair times with the assumed lognormal sigma, the
PASS/FAIL verdict with margin against the maximum-repair-time
requirement, and an optional per-LRU expected-downtime rollup over an
exposure interval that gate the maintainability input to the system
safety and availability case. Does NOT do: Markov chains, state
probabilities, availability at mission time or MTTF from rates
(markov-analysis); FTA uncertainty bands or error-factor lognormals
(fault-tree-uncertainty-analysis); maintenance-task hazard scoring
(operating-support-hazard-analysis); MSG-3 task-category selection and
interval determination (msg3-maintenance-analysis); cost modeling that
consumes MTTR as a dollar driver (life-cycle-cost); fitting a lognormal
to a data sample or generic sample percentiles (probability-
distributions, descriptive-statistics). Deterministic core only; the
lognormal sigma is an engineering input chosen from fleet data or the
documented default, never estimated by this leaf.

## Model (implement exactly)

Functions (pure stdlib, math only). Repair times and MTTR are in
SECONDS; failure rates are per hour. Items are lists of (lambda_i,
mttr_s_i) tuples, lambda_i the per-hour failure rate and mttr_s_i the
LRU mean or median repair time in seconds.
- failure_rate_weighted_mttr(items) -> float sum(lambda_i * mttr_s_i) /
  sum(lambda_i), the lambda-weighted arithmetic mean of the per-LRU mean
  repair times (the classic failure-rate-weighted MTTR rollup). ValueError
  if items is empty, any lambda_i <= 0, any mttr_s_i <= 0, or the total
  rate is 0.
- failure_rate_weighted_median(items) -> float exp(sum(lambda_i *
  ln(mttr_s_i)) / sum(lambda_i)), the lambda-weighted geometric mean of
  the per-LRU median repair times, used as the t50 (median) parameter of
  the system lognormal repair-time model. ValueErrors as above.
- normal_quantile(p) -> float z_p, Acklam's inverse normal CDF with the
  published coefficient sets (a1..a6, b1..b5 for the central region,
  c1..c6, d1..d4 for the tails split at P_LOW = 0.02425) and the single
  refinement step x = x - u / (1 + x * u / 2) with u = e * sqrt(2 pi) *
  exp(x^2 / 2) and e = 0.5 * erfc(-x / sqrt(2)) - p, computed with
  stdlib math.erfc; deterministic. ValueError if p is not strictly
  inside (0, 1). normal_quantile(0.5) returns 0.0 exactly and
  normal_quantile(0.95) = 1.6448536269514726 on IEEE-754 doubles.
- lognormal_percentile(mttr_median, sigma, p) -> float mttr_median *
  exp(sigma * normal_quantile(p)), the p-th percentile of the lognormal
  repair-time model with median mttr_median and log-space spread sigma;
  t50 = mttr_median exactly when p = 0.5 (z = 0, identity). ValueError if
  mttr_median <= 0, sigma < 0 (sigma = 0 collapses every percentile to
  the median) or p outside (0, 1).
- maintainability_verdict(t95, requirement_limit =
  MAX_REPAIR_TIME_LIMIT_S) -> dict {"verdict", "t95_s", "limit_s",
  "margin_s"} with verdict "PASS" when t95 <= requirement_limit
  (inclusive at the boundary) else "FAIL", and margin_s = limit_s -
  t95_s (non-negative on PASS, negative shortfall on FAIL). ValueError if
  t95 <= 0 or requirement_limit <= 0.
- lru_downtime_rollup(items, exposure_hours) -> dict
  {"per_lru_downtime_hours", "total_downtime_hours",
  "expected_unavailability"}: per-LRU expected downtime D_i =
  lambda_i * exposure_hours * (mttr_s_i / 3600.0) hours (the product
  lambda * exposure * mean repair time in hours), total the sum, and
  expected_unavailability = total / exposure_hours. Documented as the
  small-unavailability approximation that reproduces the markov-analysis
  steady-state unavailability lambda/(lambda + mu) when mu = 1/MTTR_h
  only in the limit lambda * MTTR_h << 1; the exact two-state value is
  the markov-analysis function's job. ValueError if exposure_hours <= 0
  or any item fails the positivity checks.
Module constants: MAX_REPAIR_TIME_LIMIT_S = 7200.0 (the documented 2 h
maximum-repair-time requirement, applied to t95), REPAIR_TIME_SIGMA_DEFAULT
= 0.5 (typical lognormal spread for avionics and mechanical LRU repair
times when fleet data is absent), SECONDS_PER_HOUR = 3600.0.

Identity to test: equal rates give plain means (weighted MTTR =
arithmetic mean, weighted median = geometric mean of the two medians);
t50 identity lognormal_percentile(m, sigma, 0.5) == m exactly for any
sigma; verdict boundary inclusive (t95 == 7200.0 is PASS with margin 0);
sigma = 0 makes every percentile equal the median; MTTR > t50 for any
sigma > 0 (arithmetic mean exceeds the median of the lognormal).

## Worked example

Run your module and take the real outputs as assert targets; the anchors
below were produced by running the prep anchor script
/tmp/w41spec/anchor_maintainability.py (prep-verified by stdlib math).

Wide-spread fleet (5 LRUs, rates per hour and median repair times in
seconds):
- LRU 1 electro-hydraulic actuator: lambda 4.0e-5 /h, median 5400 s
  (1.5 h)
- LRU 2 servo control electronics: lambda 1.2e-5 /h, median 9000 s
  (2.5 h)
- LRU 3 rate sensor unit: lambda 8.0e-6 /h, median 2700 s (0.75 h)
- LRU 4 power drive unit: lambda 2.0e-5 /h, median 10800 s (3.0 h)
- LRU 5 control surface position sensor: lambda 6.0e-6 /h, median
  3600 s (1.0 h)
Total rate 8.6e-5 /h. failure_rate_weighted_mttr = 6781.3953 s (1.8837
h): the high-rate 1.5 h and 3.0 h LRUs dominate the arithmetic rollup.
failure_rate_weighted_median t50 = 6209.6647 s (1.7249 h), below the
MTTR as the lognormal median must sit under the arithmetic mean. With
the assumed lognormal sigma 0.6: t95 = lognormal_percentile(6209.6647,
0.6, 0.95) = 16660.1405 s (4.6278 h), verdict FAIL against the 7200 s
(2 h) requirement with margin_s = -9460.1405 s: 95% of repairs would
exceed the 2 h maximum-repair-time limit, so the requirement is not met.
Sensitivity: with sigma 0.3 the same fleet gives t95 = 10171.2283 s,
still FAIL; the verdict flips only below sigma 0.089962 (t95 =
7200.000000 s, PASS with margin 0.0 at the flip), showing how narrow the
repair-time spread must be for this fleet to satisfy a 2 h t95 limit.
Downtime rollup over exposure 4000 flight hours:
per_lru_downtime_hours [0.2400, 0.1200, 0.0240, 0.2400, 0.0240],
total 0.648000 h, expected_unavailability 1.62e-4, consistent with
sum(lambda * MTTR_h) = 8.6e-5 * 1.8837 = 1.62e-4 and with the
markov-analysis steady-state unavailability when mu = 1/MTTR in the
small-product limit.

Compact fleet (4 LRUs, PASS case with the default sigma):
- LRU A servo actuator: lambda 3.0e-5 /h, median 1440 s (0.4 h)
- LRU B controller unit: lambda 1.5e-5 /h, median 2160 s (0.6 h)
- LRU C sensor module: lambda 9.0e-6 /h, median 1800 s (0.5 h)
- LRU D power supply: lambda 1.2e-5 /h, median 2880 s (0.8 h)
Total rate 6.6e-5 /h. MTTR = 1914.5455 s (0.5318 h), t50 = 1846.4220 s
(0.5129 h). With sigma = REPAIR_TIME_SIGMA_DEFAULT = 0.5: t95 =
4202.4871 s (1.1674 h), verdict PASS with margin_s = +2997.5129 s: the
requirement is met with margin.

Quantile anchors: normal_quantile(0.5) = 0.0 exactly; normal_quantile
(0.95) = 1.6448536269514726 (matches the published Acklam value to 1e-15);
t50 identity lognormal_percentile(6210.0, 0.6, 0.5) = 6210.0 exactly.

## Validation list (contract test must include)

- failure_rate_weighted_mttr on the 5-LRU wide fleet = 6781.3953 s
  within 1e-3; on the 4-LRU compact fleet = 1914.5455 s within 1e-3.
- failure_rate_weighted_median t50 = 6209.6647 s (wide) and 1846.4220 s
  (compact) within 1e-3; t50 < MTTR on both fleets (lognormal median
  under the arithmetic mean).
- Equal-rate identity: failure_rate_weighted_mttr([(1e-5, 3600.0),
  (1e-5, 7200.0)]) = 5400.0 s and failure_rate_weighted_median = 5091.17
  s within 1e-9 of math.sqrt(3600.0 * 7200.0) (geometric mean when rates
  are equal).
- normal_quantile(0.5) = 0.0 exactly; normal_quantile(0.95) =
  1.6448536269514726 within 1e-12; normal_quantile(0.97575) at the tail
  switch boundary returns a finite monotone value; ValueError at p = 0,
  p = 1 and outside.
- lognormal_percentile(6209.6647, 0.6, 0.95) = 16660.1405 s within 1e-2;
  t50 identity: lognormal_percentile(6210.0, 0.6, 0.5) = 6210.0 exactly
  (within 1e-12); sigma = 0 collapses every percentile to the median;
  monotone increasing in p; monotone increasing in sigma.
- maintainability_verdict(16660.1405) = FAIL with margin_s = -9460.1405
  s within 1e-2; maintainability_verdict(4202.4871) = PASS with margin_s
  = +2997.5129 s within 1e-2; inclusive boundary:
  maintainability_verdict(7200.0) = PASS with margin_s = 0.0; custom
  limit honored (for example 10800.0 with t95 16660.1405 still FAIL).
- lru_downtime_rollup(wide fleet, 4000.0): per-lru [0.24, 0.12, 0.024,
  0.24, 0.024] within 1e-6, total 0.648 h within 1e-6,
  expected_unavailability 1.62e-4 within 1e-8.
- ValueErrors across the module: empty items; zero, negative or all-zero
  rates; zero or negative mttr; zero or negative exposure; p at 0 and 1;
  median 0; negative sigma; t95 0 and negative; requirement_limit 0.
- Determinism: identical outputs across repeated calls; dict keys
  exactly as documented in every returned dict.
- A step-3 verdict flip check: at sigma = ln(7200.0 / 6209.6647) /
  normal_quantile(0.95) = 0.089962 the wide fleet yields t95 =
  7200.000000 s, PASS with margin 0.0 within 1e-6.

## Corpus fragment (eval/hit1-wave41-maintainability-prediction.yaml)

Query 1 (copy verbatim):
  "roll the LRU failure rates and median repair times into the failure-rate-weighted mean time to repair and check the lognormal t95 repair time against the two hour maximum-repair-time requirement"
  intent: "systems-engineering-safety; failure-rate-weighted MTTR rollup and lognormal t95 repair-time verdict against the maximum-repair-time requirement"
  expected_skill: "systems-engineering-safety/arp4761a/maintainability-prediction"
Query 2 (copy verbatim):
  "predict the system maintainability from the line replaceable unit failure rates and repair times: compute the failure-rate-weighted mttr and the t50 and t95 repair-time percentiles of the lognormal repair-time model for the repair-time-limit verdict"
  intent: "systems-engineering-safety; failure-rate-weighted mttr with lognormal t50 and t95 repair-time percentiles for the maximum-repair-time verdict"
  expected_skill: "systems-engineering-safety/arp4761a/maintainability-prediction"
Task ids: w41-maintainability-prediction-1 and -2. Corpus prep greps:
eval/hit1-corpus.yaml (1119 tasks) contains no query with mttr, mean
time to repair, repair-time percentile or t95; the existing markov tasks
route on "failure and repair rates", the msg3 tasks on task categories
and intervals, and the t3 future-pin ("plan an engine-overhaul
checklist", teardown/inspection/assembly gates) stays pinned to
manufacturing-quality/as9100/quality until an MRO skill publishes, which
this leaf is not. Queries above are collision-free: no existing leaf
description or tag carries mttr, repair-time-percentile or
maximum-repair-time tokens.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must roll LRU-level failure rates
and repair-task times into a system maintainability prediction:" and
include the outputs in the Claim (weighted MTTR, t50 and t95 repair
times, verdict against the maximum-repair-time requirement). First tag:
maintainability-prediction. Additional tags ONLY:
failure-rate-weighted-mttr, lognormal-repair-time, repair-time-
percentile, maximum-repair-time-requirement. NEVER single generic words
(maintenance, repair, time, downtime, failure, prediction, requirement,
rate, percentile). 50-150 words, <=1000 chars, no em dash and
no banned content words, action verb present.

FORBIDDEN TOKENS (belong to siblings): markov-chain, state-probability,
transition-rate, repair-rate, mean-time-to-failure, absorbing-state,
availability, k-out-of-n (markov-analysis); error-factor, confidence-
band, fussell-vesely, tree-probability (fault-tree-uncertainty-analysis);
maintenance-hazard, ground-operations-hazard, risk-matrix, hazard-log,
critical-task (operating-support-hazard-analysis); msg-3, maintenance-
steering-group, task-category-selection, hidden-failure, evident-
failure, interval-determination (msg3-maintenance-analysis);
learning-curve, discounting, cost-estimation, o-and-s (life-cycle-cost);
distribution-fitting, goodness-of-fit, weibull, kolmogorov-smirnov,
quantile-estimation (probability-distributions); sample-statistics,
five-number-summary, interquartile-range (descriptive-statistics);
containment-bound, lateral-navigation-error (rnp-anp-containment).

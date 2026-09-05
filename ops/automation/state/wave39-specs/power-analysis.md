# Wave-39 leaf spec: power-analysis (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/power-analysis/
- Pack: numerics. Closest siblings: hypothesis-testing (NHST only:
  statistic, degrees of freedom, p-value, verdict; no beta, no sample-size
  solver), proportion-confidence-interval (interval estimation; its normal
  quantile helper is a sibling technique, not a claim), rank-based-
  hypothesis-testing, confidence-interval-estimation,
  manufacturing-quality/as9100/acceptance-sampling and variables-
  acceptance-sampling (lot-disposition plans with AQL and code letters,
  NOT test power), monte-carlo-sampling (owns the generic "sample size"
  trigger token). Whole-tree greps at prep: "statistical power", "power
  analysis", "type II error" = 0 owning hits in skills/. GENUINE CC gap
  (fresh probe).
- Standards id: naca-tr-824 (reference-only). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Determine the sample size and the statistical power of a planned test:
compute the minimum sample size per group for a two-sample pooled
z-based comparison at a given significance level, power and effect size
with n >= 2 * sigma^2 * (z_(1-alpha/2) + z_(1-beta))^2 / delta^2 (and the
one-sample and one-sample-proportion variants), round up to whole groups,
and evaluate the achieved power at the rounded sample size. Produces the
sample size per group, the total sample size and the achieved power that
gate qualification-test planning and experiment sizing. Does NOT do:
running hypothesis tests (hypothesis-testing); confidence intervals
(confidence-interval-estimation, proportion-confidence-interval);
lot-disposition acceptance sampling (manufacturing-quality).

## Model (implement exactly)

Functions (pure stdlib, self-contained - no cross-leaf imports):
- normal_quantile(q) -> standard normal quantile via the documented
  Acklam rational approximation (as used by proportion-confidence-
  interval); ValueError if q outside (0, 1).
- normal_survival(z) -> 1 - Phi(z) via the standard normal CDF (erf-based
  or the documented approximation).
- sample_size_two_sample_pooled(delta, sigma, alpha=0.05, power=0.8) ->
  integer n per group: ceil(2 * sigma^2 * (z_(1-alpha/2) +
  z_(1-beta))^2 / delta^2); ValueError if delta <= 0, sigma <= 0, alpha
  or power outside (0, 1), power >= 1 - alpha.
- sample_size_one_sample(delta, sigma, alpha=0.05, power=0.8) -> integer
  n: ceil(sigma^2 * (z_(1-alpha/2) + z_(1-beta))^2 / delta^2).
- sample_size_one_sample_proportion(p0, p1, alpha=0.05, power=0.8) ->
  integer n: ceil([z_(1-alpha/2) * sqrt(p0*(1-p0)) + z_(1-beta) *
  sqrt(p1*(1-p1))]^2 / (p1 - p0)^2); ValueError if p0 or p1 outside
  (0, 1) or p1 == p0.
- achieved_power_two_sample_pooled(n_per_group, delta, sigma, alpha=0.05)
  -> float power = 1 - Phi(z_(1-alpha/2) - delta * sqrt(n / (2 * sigma^2)));
  ValueError as above with n < 2.
- power_report(...) -> dict with keys n_per_group, n_total, achieved_power.
Module constants: none magic.

Identity to test: the required sample size grows as the effect size
shrinks (n ~ 1/delta^2); the achieved power at the computed n is at least
the target power; higher alpha or higher target power raises n;
the two-sample pooled n is exactly double the one-sample n at the same
inputs.

## Worked example

Two-sample pooled: delta = 0.5 * sigma (effect size 0.5), alpha = 0.05
two-sided, power 0.8:
- z_(1-alpha/2) = 1.9600, z_(1-beta) = 0.8416.
- n = 2 * (1.9600 + 0.8416)^2 / 0.25 = 62.79 -> 63 per group
  (126 total).
One-sample proportion: p0 = 0.30, p1 = 0.50, alpha 0.05, power 0.8:
- n = [1.960 * sqrt(0.21) + 0.842 * sqrt(0.25)]^2 / 0.04 = 43.5 -> 44.
Achieved power at 63 per group (delta 0.5 sigma): 1 - Phi(1.960 -
0.5 * sqrt(63/2)) = 1 - Phi(-0.846) = 0.8013.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (the normal quantiles and the formula
evaluations were independently checked at prep).

## Validation list (contract test must include)

- normal_quantile(0.975) = 1.9600 within 1e-3; normal_quantile(0.8) =
  0.8416 within 1e-3.
- Two-sample n = 63 per group (126 total) at delta = 0.5 sigma; achieved
  power at 63 at least 0.80.
- One-sample n is half the two-sample n at identical inputs (rounding
  aside).
- Proportion n = 44 at p0 0.30, p1 0.50; achieved power at 63 per group
  0.8013 within 0.002.
- Monotonicity: n(delta = 0.25 sigma) > n(delta = 0.5 sigma);
  n(power 0.9) > n(power 0.8).
- ValueErrors: delta 0, sigma 0, alpha 0 or 1, power 1, p1 == p0,
  n < 2 in achieved power.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-power-analysis.yaml)

Query 1 (copy verbatim):
  "power analysis minimum sample size per group to detect a half sigma shift at eighty percent power and alpha zero point zero five"
  intent: "cross-cutting; statistical power and sample size determination"
  expected_skill: "cross-cutting/numerics/power-analysis"
Query 2 (copy verbatim):
  "sample size determination with the type-two-error point two and the effect size for the two-sample comparison"
  intent: "cross-cutting; required sample size from alpha, power and effect size"
  expected_skill: "cross-cutting/numerics/power-analysis"
Task ids: w39-power-analysis-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine the sample size or the
statistical power of a planned comparison:" and include the outputs in the
Claim. First tag: power-analysis. Additional tags ONLY: sample-size-
determination, type-ii-error, effect-size, minimum-sample-size,
achieved-power. NEVER single generic words (power, analysis, sample,
size, test, statistics) and NEVER the bare token sample-size (owned by
monte-carlo-sampling) or power-spectral-density family tokens. 50-150
words, <=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): p-value, t-test, anova,
hypothesis-testing (hypothesis-testing); confidence-interval (interval
leaves); acceptance-sampling, aql (manufacturing-quality); monte-carlo.

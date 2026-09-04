---
name: confidence-interval-estimation
description: "Use when you must estimate a confidence interval for a sample statistic: the Student t interval for a sample mean, the pooled or Welch-Satterthwaite interval for a difference of means, and the chi-square interval for the variance and standard deviation of a measured or production batch, each at a stated confidence level. Quantiles come from in-leaf inversion: the two-sided t quantile by bisection on the regularized incomplete beta relation and the chi-square quantile by lower incomplete gamma inversion, pure Python stdlib. Produces interval bounds, standard error, degrees of freedom, and quantiles as keyed dicts for measurement, drag-count, and production statistics. Trigger: t confidence interval, chi square variance interval, mean difference interval, quantile inversion, small sample statistics, interval estimation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [confidence-interval-estimation, t-confidence-interval, chi-square-variance-interval, mean-difference-interval, quantile-inversion, small-sample-statistics, interval-estimation]
  version: 0.1.0
  author: AeroSkills
---

# Confidence Interval Estimation (cross-cutting/numerics/confidence-interval-estimation)

Use when you must estimate a parametric confidence interval for a sample
statistic: the exact small-sample t interval around a measured mean, the
pooled or Welch interval around a difference of means (configuration A
versus B, batch versus batch), and the chi-square interval around a
variance or standard deviation of a production batch, all at a stated
confidence level. This leaf implements the interval counterpart to the
hypothesis-testing verdict layer: every quantile comes from the module's
own inversion machinery (two-sided t quantile by bisection on the
regularized incomplete beta identity, chi-square quantile by bisection on
the lower incomplete gamma function), pure Python stdlib with no external
statistics packages. It pairs with cross-cutting/numerics/hypothesis-testing
for the verdict on the same data: the interval that excludes zero is the
verdict that rejects.

## Domain quick reference

- Conventions: level is the two-sided confidence level (0.95 for 95%),
  alpha = 1 - level. Sample x of size n, mean xbar, sample standard
  deviation s with the n-1 denominator.
- Mean interval: xbar +/- t_{1-alpha/2, n-1} * s / sqrt(n).
- Difference of means: (m1 - m2) +/- t_{1-alpha/2, df} * se, with the
  pooled standard error se = sp * sqrt(1/n1 + 1/n2), pooled variance
  sp^2 = ((n1-1)s1^2 + (n2-1)s2^2) / (n1+n2-2) and df = n1+n2-2 for
  equal_var True; the Welch standard error
  se = sqrt(s1^2/n1 + s2^2/n2) with the Welch-Satterthwaite df for
  equal_var False.
- Variance interval: [(n-1)s^2 / chi2_{1-alpha/2, n-1},
  (n-1)s^2 / chi2_{alpha/2, n-1}], with chi2_{p, df} the quantile of the
  chi-square distribution at probability p; the sigma interval is the
  square root of each variance bound.
- Quantile machinery: t_ppf_two_sided(level, df) targets the CDF value
  p = (1 + level)/2 (the t_{1-alpha/2} tail point) and bisects the
  identity P(T <= t) = 1 - 0.5 * I_x(df/2, 1/2) with
  x = df/(df + t^2); chi2_ppf(p, df) bisects P(df/2, x/2), the
  regularized lower incomplete gamma at x/2. Both bisections run to an
  absolute tolerance of 1e-9 on the quantile. Regularized incomplete
  beta and lower incomplete gamma are implemented in-leaf (Lentz
  continued fraction and series).
- NACA-TR-824 frames the statistical-methods context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. State the quantity of interest (mean, difference of means, variance
   or standard deviation) and fix the two-sided confidence level,
   default 0.95.
2. For a single measured sample x, call confidence_interval_mean(x,
   level) and read lower and upper, with the standard error, df and t
   quantile in the returned dict.
3. For configuration A versus B, call
   confidence_interval_mean_difference(a, b, level, equal_var) with
   equal_var True for the pooled interval or False for the Welch
   interval; the sign of the pair (mean_diff, lower, upper) tells the
   direction and magnitude of the difference.
4. For a variance or standard deviation of a production batch, call
   confidence_interval_variance(x, level) and read lower/upper for the
   variance and sigma_lower/sigma_upper for the standard deviation.
5. When the interval excludes zero, the difference is significant at
   the same level (interval/verdict duality with the sibling
   hypothesis-testing leaf).
6. Format any of the builder dicts with interval_summary for the
   rounded bound pair, width and a text line.
7. Confirm the deterministic checks with the contract test
   scripts/test_confidence_interval_estimation.py.

## Worked example

Drag-count samples a = [267, 261, 263, 258, 262] and
b = [273, 271, 268, 275, 270] (n = 5 each; the hypothesis-testing
sibling's data).

- t quantiles: t_ppf_two_sided(0.95, 4) = 2.776445;
  t_ppf_two_sided(0.95, 8) = 2.306004.
- chi2 quantiles at df = 4: chi2_ppf(0.025, 4) = 0.484419;
  chi2_ppf(0.975, 4) = 11.143287.
- Mean interval of a at 95%: xbar = 262.2, s = 3.2711, se = 1.4629,
  df = 4, bounds [258.1384, 266.2616].
- Pooled difference interval at 95%: mean_diff = -9.2, se = 1.8974,
  df = 8, bounds [-13.5753, -4.8247]. The interval excludes 0,
  consistent with the sibling's reject verdict on the same data
  (the duality check).
- Welch difference interval at 95%: df = 7.7244 (Welch-Satterthwaite),
  bounds [-13.6027, -4.7973].
- Variance interval of a at 95%: variance = 10.7, df = 4, bounds
  [3.8409, 88.3533]; sigma bounds [1.9598, 9.3996].

## Verification

- Confirm the quantile anchors to 1e-4: t(0.975, 4) = 2.776445,
  t(0.975, 8) = 2.306004, chi2(0.025, 4) = 0.484419,
  chi2(0.975, 4) = 11.143287, and the two-sided level-0.95 t quantile
  equals the one-sided p = 0.975 t quantile.
- Confirm the worked bounds: mean CI of a within [258.1384, 266.2616],
  pooled difference CI within [-13.5753, -4.8247] (excludes 0),
  variance CI within [3.8409, 88.3533], sigma CI within
  [1.9598, 9.3996].
- Confirm a seeded normal sample gives a mean interval that contains the
  true mean, larger levels give wider intervals, and larger n at equal
  variance gives narrower intervals.
- Confirm every call is deterministic run to run and each builder dict
  carries exactly the documented keys.
- Confirm ValueError rejection of level outside (0, 1), df below 1,
  chi2 probability outside [0, 1], empty samples and single-observation
  samples, and reversed interval bounds.
- Run the contract test offline: python3
  scripts/test_confidence_interval_estimation.py (31 tests,
  deterministic, no network).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the verdict sibling on the
  same data; the interval excluding zero and the reject verdict are the
  same statement in two forms (duality).
- cross-cutting/numerics/descriptive-statistics: the mean, standard
  deviation and variance inputs this leaf consumes.
- cross-cutting/numerics/uncertainty-propagation: the expanded-uncertainty
  propagation route built from the partial derivatives of the measurement
  model, the standard choice for indirect measurements rather than direct
  sample statistics.
- cross-cutting/numerics/monte-carlo-sampling: intervals read directly
  from the spread of many generated draws of a stochastic model, the
  sampling-based alternative for non-parametric cases.
- cross-cutting/numerics/probability-distributions: distribution
  characterization and fitting context for the underlying model.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_confidence_interval_estimation.py

The test covers the worked quantile anchors and interval bounds above
(t and chi2 to 1e-4, intervals to 1e-4), the mean/pooled/Welch/variance
interval builders on the drag-count data, the pooled interval excluding
zero (duality), the sigma square-root relation, the symmetric-about-the-
statistic identity, level and sample-size monotonicity, seeded
normal-sample coverage of the true mean, variance and difference,
determinism, the exact key sets of every builder dict, the
interval_summary rounding contract, and ValueError rejection of
non-physical levels, df, probabilities, empty and single-observation
samples and reversed bounds. Runs in well under a second.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames the
  statistical-methods convention; the t, Welch and chi-square interval
  relations above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

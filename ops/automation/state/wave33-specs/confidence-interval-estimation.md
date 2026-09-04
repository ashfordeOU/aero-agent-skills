# Wave-33 leaf spec: confidence-interval-estimation (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/confidence-interval-estimation/
- Pack: numerics. Sibling scope check: hypothesis-testing owns the
  accept/reject verdict layer (t/f/chi2 CDFs, p-values, verdicts; its
  logic has NO ppf and no interval builder); monte-carlo-sampling
  confidence_interval = empirical percentiles of simulated draws;
  descriptive-statistics explicitly claims no distribution fitting;
  uncertainty-propagation = GUM expanded uncertainty from sensitivity
  coefficients. This leaf owns parametric confidence-interval
  ESTIMATION (the interval counterpart to hypothesis-testing's
  verdicts).
- Standards id: naca-tr-824 (reference-only; numerics convention).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Estimate exact small-sample parametric confidence intervals for sample
statistics: the t-interval for a mean, the pooled or Welch interval for
a difference of means, and the chi-square interval for a variance, via
the leaf's own quantile inversions (t ppf through beta-quantile
inversion, chi2 ppf through lower-incomplete-gamma inversion). Produces
the interval bounds at the requested confidence level for measurement
and production statistics.

Does NOT do: p-values / reject-null verdicts (hypothesis-testing);
empirical percentile intervals of Monte Carlo draws (monte-carlo-
sampling); GUM expanded uncertainty (uncertainty-propagation); summary
statistics (descriptive-statistics); distribution fitting
(probability-distributions).

## Model (implement exactly)

Conventions: confidence level alpha (two-sided, e.g. 0.95). Sample x of
size n, mean xbar, sample standard deviation s (n-1 denominator).
- Mean interval: xbar +/- t_{1-alpha/2, n-1} * s / sqrt(n).
- Difference of means: (m1 - m2) +/- t_{1-alpha/2, df} * se, where the
  pooled se = sp * sqrt(1/n1 + 1/n2), sp^2 = ((n1-1)s1^2 + (n2-1)s2^2)
  / (n1+n2-2), df = n1+n2-2 (equal_var True); the Welch se =
  sqrt(s1^2/n1 + s2^2/n2), df via the Welch-Satterthwaite equation
  (equal_var False).
- Variance interval: [(n-1)s^2 / chi2_{1-alpha/2, n-1},
  (n-1)s^2 / chi2_{alpha/2, n-1}]; the sigma interval is the square
  root of each bound.

Quantile machinery (pure stdlib):
- t_ppf(p, df): invert the t CDF by bisection on the regularized
  incomplete beta I_x(df/2, 1/2) relation for the t distribution
  (two-sided p mapping: p_tail = (1-p)/2 etc. - implement the standard
  identity and document it; verify against the worked quantiles).
- chi2_ppf(p, df): invert the chi2 CDF by bisection using the
  lower-incomplete-gamma regularized function P(df/2, x/2).
- Regularized incomplete beta and lower incomplete gamma implemented
  in-leaf with continued fractions or series (pure stdlib); the
  bisection target tolerance 1e-9.

Functions (pure stdlib):

- t_ppf_two_sided(level, df) -> the two-sided quantile t_{1-alpha/2,
  df} for alpha = 1 - level. ValueError on level outside (0,1),
  df < 1.
- chi2_ppf(p, df) -> quantile. ValueError on p outside [0,1], df < 1.
- confidence_interval_mean(x, level=0.95) -> dict {mean, se, df,
  t_quantile, lower, upper}.
- confidence_interval_mean_difference(a, b, level=0.95,
  equal_var=True) -> dict {mean_diff, se, df, t_quantile, lower,
  upper}.
- confidence_interval_variance(x, level=0.95) -> dict {variance,
  df, chi2_lower, chi2_upper, lower, upper, sigma_lower, sigma_upper}.
- interval_summary(...) -> dict of the requested interval.

## Worked example

Shared drag-count anchors (the hypothesis-testing sibling's data):
a = [267, 261, 263, 258, 262] (n=5, xbar=262.2, s about 3.2711),
b = [273, 271, 268, 275, 270] (n=5).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- t_ppf_two_sided(0.95, 4) about 2.776445; t(0.975, 8) about 2.306004.
- chi2_ppf(0.025, 4) about 0.484419; chi2_ppf(0.975, 4) about
  11.143287.
- Mean CI of a at 95%: [258.1384, 266.2616].
- Difference CI (pooled): [-13.5753, -4.8247] (excludes 0 - consistent
  with the sibling's p = 0.00127 reject; the duality check).
- Variance CI: [3.8409, 88.3533]; sigma CI [1.9598, 9.3996].

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: level outside (0,1); df < 1; empty samples; sample
  variance zero with n=1.
- Quantile anchors: t(0.975,4) about 2.776445; t(0.975,8) about
  2.306004; chi2(0.025,4) about 0.484419; chi2(0.975,4) about
  11.143287 (all to 1e-4).
- Interval anchors: the worked-case bounds above.
- Duality: the pooled difference interval excludes 0 (consistent with
  the reject verdict of the sibling hypothesis test on the same data).
- Coverage sanity: for a normal sample the interval contains the true
  mean (seeded test); larger level gives wider intervals; larger n
  gives narrower intervals.
- Determinism: identical outputs run-to-run.
- Convenience dicts contain exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-confidence-interval-estimation.yaml)

Query 1 (copy verbatim):
  "compute the t distribution confidence interval for the mean of a measured drag count sample at 95 percent confidence"
  intent: "cross-cutting; t-interval for a sample mean at a confidence level"
  expected_skill: "cross-cutting/numerics/confidence-interval-estimation"
Query 2 (copy verbatim):
  "estimate the chi square confidence interval for the variance and standard deviation of a production measurement batch"
  intent: "cross-cutting; chi-square variance/standard-deviation confidence interval"
  expected_skill: "cross-cutting/numerics/confidence-interval-estimation"
Task ids: w33-confidence-interval-estimation-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate a confidence interval
for a sample statistic:" and include the outputs in the Claim. First
tag: confidence-interval-estimation. Additional tags ONLY:
t-confidence-interval, chi-square-variance-interval,
mean-difference-interval, quantile-inversion, small-sample-statistics,
interval-estimation. NEVER single generic words (confidence, interval,
mean, variance, statistic, sample, test, p-value). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): p-value, reject null,
significance level, t-test, hypothesis verdict (hypothesis-testing);
Monte Carlo, empirical percentile, simulation draws (monte-carlo-
sampling); combined uncertainty, sensitivity coefficient, GUM
(uncertainty-propagation); probability density function, distribution
fitting (probability-distributions). The tokens "confidence interval",
"quantile inversion", "interval estimation" are this leaf's own.

Tags: [confidence-interval-estimation, t-confidence-interval,
chi-square-variance-interval, mean-difference-interval,
quantile-inversion, small-sample-statistics, interval-estimation]

Sibling-citation lines for Related leaves:
cross-cutting/numerics/hypothesis-testing (the verdict sibling on the
same data; interval/verdict duality),
cross-cutting/numerics/descriptive-statistics,
cross-cutting/numerics/uncertainty-propagation.

Ledger Standard: naca-tr-824.

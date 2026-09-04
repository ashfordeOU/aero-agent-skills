---
name: probability-distributions
description: "Use when you must fit and characterize a standard probability distribution for aerospace engineering data analysis: estimate the normal, lognormal, exponential, and Weibull distribution parameters from a univariate sample, evaluate the pdf, cdf, quantile, reliability, and hazard functions, score the fit with the chi-square and Kolmogorov-Smirnov goodness-of-fit statistics, and report percentiles plus reliability at a target time. Produces the fitted parameter dict, the fit-quality verdict, and the quantile and reliability values that gate the statistical characterization of scatter data such as loads, life, failure times, and tolerances. Trigger: probability distribution fitting, weibull fit, lognormal, exponential fit, goodness of fit, kolmogorov smirnov, chi-square fit test, quantile estimation, reliability at time, hazard function, parameter estimation."
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
  tags: [probability-distributions, weibull-fit, lognormal, exponential-fit, goodness-of-fit, kolmogorov-smirnov, chi-square-fit-test, quantile-estimation, reliability-at-time, hazard-function, parameter-estimation]
  version: 0.1.0
  author: AeroSkills
---

# Probability Distributions (cross-cutting/numerics/probability-distributions)

Use when the task is fitting and characterizing a standard probability
distribution for aerospace engineering data analysis: estimating the
normal, lognormal, exponential, and Weibull parameters from a univariate
sample of scatter data, evaluating the pdf, cdf, quantile, reliability,
and hazard functions, and scoring the fitted model with the chi-square
and Kolmogorov-Smirnov statistics. This leaf implements the standard
closed-form distribution model layer in pure Python, stdlib only. It
pairs with cross-cutting/numerics/monte-carlo-sampling (draw samples
from the fitted distributions for a study) and
cross-cutting/numerics/uncertainty-propagation (feed the fitted
distributions into a GUM sensitivity analysis); the manufacturing side,
process control over time, belongs to manufacturing-quality/as9100/
statistical-process-control.

## Domain quick reference

- Normal fit: mu = mean(x), sigma = sample standard deviation (ddof 1).
  Density 1/(sigma sqrt(2 pi)) exp(-(x - mu)^2 / (2 sigma^2)); cdf
  0.5 (1 + erf((x - mu) / (sigma sqrt(2)))).
- Normal quantile: mu + sigma z(p), with z(p) from the Acklam rational
  approximation of the standard normal inverse cdf (module coefficients,
  error near 1e-9).
- Lognormal fit: fit the normal to ln(x); mu_ln and sigma_ln are the
  mean and sample standard deviation of the logged data. Quantile:
  exp(mu_ln + sigma_ln z(p)).
- Exponential fit: rate = 1 / mean(x). Cdf 1 - exp(-rate x); quantile
  -ln(1 - p) / rate; reliability exp(-rate t); hazard rate (constant).
- Weibull MLE: shape k solves 1/k = sum(x^k ln x) / sum(x^k) -
  mean(ln x), by bisection on k in [WEIBULL_K_MIN, WEIBULL_K_MAX] to
  WEIBULL_TOL; scale lambda = (mean(x^k))^(1/k). Cdf
  1 - exp(-(x / lambda)^k); quantile lambda (-ln(1 - p))^(1/k);
  reliability exp(-(t / lambda)^k); hazard
  (k / lambda) (t / lambda)^(k - 1), increasing when k > 1.
- Reliability R(t) = 1 - cdf(t) for every model; hazard h(t) = pdf(t) /
  R(t) where no closed form applies.
- Chi-square gof: fixed-width bins over the data range, expected counts
  from the fitted cdf, bins with expected below MIN_EXP merged; df =
  cells after merging minus one; verdict PASS when the statistic is at
  most the alpha 0.05 critical value CRIT_CHI2 for that df.
- Kolmogorov-Smirnov gof: D = max |empirical cdf - fitted cdf| over the
  sorted sample; verdict PASS when D <= KS_CRIT_COEF / sqrt(n), the
  large-sample 5% approximation.
- NACA TR-824 frames the statistical data analysis context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Collect the univariate scatter sample, for example time to event in
   hours, and choose the candidate distribution from the failure or
   scatter physics.
2. Fit the model with fit_distribution(data, dist) and read the params
   dict (normal {mu, sigma}, lognormal {mu_ln, sigma_ln}, exponential
   {rate}, weibull {shape, scale}).
3. Score the fit with chi2_gof(data, dist, params, bins=8) for the
   (statistic, df, verdict) tuple and ks_gof(data, dist, params) for
   (D, verdict); a verdict of PASS on both supports the chosen model.
4. Characterize the distribution: quantile(p, dist, params) for the 5,
   50, and 95 percent quantiles and cdf(x, dist, params) for exceedance
   probabilities.
5. Report the reliability and hazard at the target time t with
   reliability(t, dist, params) and hazard(t, dist, params); for the
   Weibull, k > 1 flags wear-out behavior with a rising hazard.
6. Run the whole sequence in one call with summarize(data, dist, target)
   for the parameter dict, both gof verdicts, the percentiles, and the
   reliability at target.
7. Confirm the deterministic checks with the contract test
   scripts/test_probability_distributions.py.

## Worked example

Sample S = [100, 200, 300, 400, 500] hours, time to event scatter.

- Exponential fit on S: rate = 1/300 = 0.0033333 per hour, so
  quantile(0.5) = -ln(0.5) / rate = 207.944 hours and reliability(300)
  = exp(-1) = 0.367879. The exponential hazard is constant at 0.0033333.
- Normal fit on S: mu = 300, sigma = 158.1139 (sample standard
  deviation, ddof 1). cdf(300) = 0.5 exactly and quantile(cdf(400)) =
  400.0000001, the round trip to within 1e-6.
- Weibull fit on S: shape k = 2.294, scale lambda = 339.429, median
  quantile(0.5) = 289.305 with cdf(median) = 0.5. Because k > 1 the
  hazard rises from 0.00139 at 100 h to 0.01115 at 500 h, wear-out
  behavior.
- Lognormal fit on exp([0, 0.5, 1, 1.5, 2]): mu_ln = 1.0,
  sigma_ln = 0.790569 and quantile(0.5) = e = 2.71828, the lognormal
  median.
- Goodness of fit: ks_gof on S against the fitted normal returns
  D = 0.13646 with a PASS verdict; chi2_gof needs enough cells after
  merging for a verdict, so the contract test runs it on a 60 point
  probability-grid sample where it returns stat = 0.90566, df = 6,
  verdict PASS against the 12.59 critical value.

## Pitfalls

- Fitting lifetime distributions to non-positive data: the
  exponential, Weibull, and lognormal fits require positive samples,
  and fewer than 3 points, non-finite entries, a zero sample standard
  deviation, p outside [0, 1], and t or x outside the positive domain
  all raise ValueError.
- Running chi2_gof on too few points: the post-merge degrees of freedom
  can fall outside the critical table, as it does for the 5 point
  sample (ValueError); the 60 point probability-grid sample is the one
  with enough cells (stat = 0.90566, df = 6 against 12.59).
- Trusting a ks_gof PASS without fitting the model first: the verdict
  is computed against the leaf's fitted parameters, and a clearly wrong
  model (an arithmetic sequence against an exponential fit) returns
  FAIL.
- Reading the lognormal median from mu_ln alone: on exp([0, 0.5, 1,
  1.5, 2]) the fit returns mu_ln = 1.0, sigma_ln = 0.790569, and the
  median is quantile(0.5) = e = 2.71828, not mu_ln itself.
- Treating a fitted exponential as capturing the trend: its hazard is
  constant (0.0033333), while a Weibull fit with k = 2.294 > 1 shows
  wear-out with the hazard rising from 0.00139 to 0.01115 over the
  sample - the exponential hides the shape.
- Mixing ddof conventions in the normal fit: sigma = 158.1139 is the
  sample standard deviation with ddof 1, so population-scale (ddof 0)
  expectations misread every quantile.

## Verification

- Confirm the exponential anchors on S: quantile(0.5) equals
  300 ln(2) = 207.944 within 1e-6 and reliability(300) equals exp(-1)
  within 1e-12.
- Confirm the normal anchors on S: mu = 300, sigma = 158.1139,
  cdf(300) = 0.5, and quantile(cdf(x)) round trips within 1e-6.
- Confirm the lognormal anchors on the exp([0, 0.5, 1, 1.5, 2]) sample:
  mu_ln = 1.0, sigma_ln = 0.790569, median quantile e.
- Confirm Weibull cdf(quantile(0.5)) = 0.5 and the k > 1 rising hazard.
- Confirm ks_gof returns a PASS for the fitted model and a FAIL for a
  clearly wrong model (arithmetic sequence against an exponential fit).
- Confirm chi2_gof df and verdict from the real module output on the
  60 point grid sample, and the ValueError when the post-merge df falls
  outside the critical table (as it does for the 5 point sample).
- Confirm ValueError rejection of fewer than 3 points, non-finite or
  non-positive data for lognormal/exponential/weibull, zero sample
  standard deviation, p outside [0, 1], and t or x outside the positive
  domain of a lifetime distribution.
- Run the contract test offline: python3
  scripts/test_probability_distributions.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/monte-carlo-sampling: draw samples from the
  fitted distributions and histogram the outputs of a study.
- cross-cutting/numerics/uncertainty-propagation: use the fitted
  distributions as the inputs of a GUM sensitivity analysis.
- cross-cutting/numerics/least-squares-regression: the paired
  measurement model layer, a straight line fit, for scatter data.
- manufacturing-quality/as9100/statistical-process-control: the process
  side, control charts over time, after the distribution layer.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_probability_distributions.py

The test covers the worked-example anchors (exponential rate 1/300 with
median 207.944 and reliability(300) = exp(-1), normal mu 300 and sigma
158.1139 with cdf(mu) = 0.5 and quantile round trips, lognormal mu_ln
1.0 and sigma_ln 0.790569 with median e, Weibull cdf(median) = 0.5 and
rising hazard), pdf and hazard values, chi-square and Kolmogorov-Smirnov
verdicts including a wrong-model FAIL, the summarize report, and
ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named only as
  the statistical data analysis context; all relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-39 leaf spec: poisson-confidence-interval (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/poisson-confidence-interval/
- Pack: numerics. Closest siblings: proportion-confidence-interval
  (Wilson and Clopper-Pearson intervals for a binomial PROPORTION from
  successes over trials - no rate or exposure term), confidence-interval-
  estimation (confidence_interval_mean with t, mean_difference pooled and
  Welch, variance with chi2 - no count or rate interval), probability-
  distributions (fits no discrete distribution), hypothesis-testing.
  Whole-tree greps at prep: a Poisson rate interval from a count over an
  exposure is computed by no leaf; manufacturing-quality attribute-control-
  charts uses the Poisson NORMAL APPROXIMATION for c-chart and u-chart
  control limits only (different estimator, different pack). GENUINE CC
  gap (fresh probe; mirrors wave-38 proportion-confidence-interval for
  count data).
- Standards id: naca-tr-824 (reference-only). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compute an exact confidence interval for a Poisson rate from a total event
count over an exposure: form the rate estimate lambda_hat = k / T, compute
the exact Garwood-style interval from the chi-square relation with the
lower bound chi2(2k, alpha/2) / (2T) and the upper bound chi2(2k + 2,
1 - alpha/2) / (2T) (equivalently gamma quantiles), and report the normal
approximation (k +/- z * sqrt(k)) / T as the large-count cross-check.
Produces the rate estimate, the exact lower and upper bounds per exposure
unit and the approximation check that gate defect-rate claims. Does NOT do:
proportion intervals (proportion-confidence-interval); t or variance
intervals (confidence-interval-estimation); c-chart or u-chart control
limits (manufacturing-quality attribute-control-charts).

## Model (implement exactly)

Functions (pure stdlib, self-contained - no cross-leaf imports):
- poisson_rate(count, exposure) -> lambda_hat = k / T; ValueError if count
  < 0 or not an integer, exposure <= 0.
- chi_square_quantile(df, q) -> the q quantile of the chi-square
  distribution with df degrees of freedom computed by inverting the
  regularized lower incomplete gamma survival function (bisection on the
  documented CDF, tolerance 1e-9, df a positive integer); ValueError if q
  outside (0, 1) or df < 1.
- poisson_confidence_interval(count, exposure, confidence_level=0.95) ->
  dict with keys rate, lower, upper, method ("exact-poisson"); the exact
  bounds as above; count 0 gives lower 0.0. ValueError as above and if
  confidence_level outside (0, 1).
- normal_approximation_interval(count, exposure, confidence_level=0.95) ->
  dict with keys rate, lower, upper, method ("normal-approximation") using
  the standard normal quantile (Acklam or bisection on the normal CDF);
  count 0 gives lower 0.0.
Module constants: none magic (incomplete gamma and normal CDF helpers are
self-contained in the leaf).

Identity to test: the exact interval at count 0 has lower bound 0 and a
positive upper bound; the exact upper bound exceeds the normal-approx
upper bound at small counts and the two converge as the count grows; the
rate estimate lies inside the exact interval; doubling the exposure halves
the rate and tightens the interval (bounds scale as 1/T).

## Worked example

k = 12 defects, T = 240 flight cycles, 95 percent level:
- rate = 12/240 = 0.05 per cycle.
- exact lower = chi2(24, 0.025) / 480 = 12.401 / 480 = 0.02584.
- exact upper = chi2(26, 0.975) / 480 = 41.923 / 480 = 0.08734.
- normal approx = (12 +/- 1.960 * sqrt(12)) / 240 = [0.0217, 0.0783].
k = 0, T = 100:
- exact interval = [0, chi2(2, 0.975) / 200] = [0, 7.378 / 200] =
  [0, 0.0369].
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (chi-square quantiles independently
evaluated at prep).

## Validation list (contract test must include)

- rate 0.05; exact lower 0.02584 within 1e-4; exact upper 0.08734 within
  1e-4.
- Normal approx bounds 0.0217 and 0.0783 within 2e-3.
- count 0, T 100: lower 0.0, upper 0.0369 within 2e-4.
- Identity: rate inside the exact interval; the exact interval contains
  the normal interval at count 12 (upper exact above upper approx).
- Convergence: at k = 200, T = 4000 the exact and normal upper bounds
  agree within 5 percent.
- ValueErrors: count -1, count 2.5, exposure 0, confidence level 0 or 1.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-poisson-confidence-interval.yaml)

Query 1 (copy verbatim):
  "compute the poisson-confidence-interval for the twelve defects observed over the two hundred forty flight cycles"
  intent: "cross-cutting; exact Poisson rate confidence interval"
  expected_skill: "cross-cutting/numerics/poisson-confidence-interval"
Query 2 (copy verbatim):
  "exact poisson rate confidence bound for the defect counts per inspection unit with the garwood chi-square relation"
  intent: "cross-cutting; count-rate interval estimation"
  expected_skill: "cross-cutting/numerics/poisson-confidence-interval"
Task ids: w39-poisson-confidence-interval-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute a confidence interval for
a Poisson rate from a count over an exposure:" and include the outputs in
the Claim. First tag: poisson-confidence-interval. Additional tags ONLY:
count-rate-interval, defect-rate-estimation, garwood-exact-interval,
poisson-rate-ci. NEVER single generic words (poisson, confidence,
interval, rate, count, defects). 50-150 words, <=1000 chars, no em dash,
no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): t-confidence-interval,
chi-square-variance-interval, mean-difference-interval (confidence-
interval-estimation); wilson-score-interval, clopper-pearson-interval,
proportion (proportion-confidence-interval); c-chart, u-chart,
control-limits (attribute-control-charts); distribution-fit
(probability-distributions).

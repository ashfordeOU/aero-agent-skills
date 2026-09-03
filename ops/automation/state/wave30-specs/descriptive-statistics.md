# Wave-30 leaf spec: descriptive-statistics (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/descriptive-statistics/
- Pack: numerics (dense pack: convergence-verification, cross-correlation-
  analysis, digital-filter-design, eigenvalue-decomposition, fast-fourier-
  transform, finite-difference-derivatives, hypothesis-testing, interpolation,
  least-squares-regression, matrix-operations, monte-carlo-sampling,
  numerical-integration, ode-solvers, optimization-algorithms,
  probability-distributions, quaternion-algebra, root-finding,
  uncertainty-propagation).
- Standards ids: naca-tr-824 (reference-only; cross-cutting numerics family
  convention id used by the numerics pack). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Summarize a sample of engineering measurements with descriptive statistics:
compute the arithmetic mean, median, range, sample and population variance
and standard deviation, the quartiles and interquartile range by linear
interpolation, the five-number summary, the coefficient of variation, and
flag outliers by the 1.5-IQR rule. Produces the location, spread, and outlier
report that gate a first look at any measured data set.

Does NOT do: fit probability distributions or estimate their parameters
(probability-distributions owns normal, lognormal, exponential, Weibull
fitting); run significance tests on samples (hypothesis-testing owns t, F,
chi-square tests); fit lines or curves to data (least-squares-regression owns
the straight-line fit; interpolation owns table interpolation); estimate the
distribution of an output by Monte Carlo (monte-carlo-sampling owns seeded
sampling); compute control-chart statistics for production processes
(manufacturing-quality statistical-process-control owns X-bar/R and Cp/Cpk).
Pure sample summary only: no model, no inference, no sampling.

## Model (implement exactly)

Module constants:
- IQR_FACTOR = 1.5 (outlier rule factor).
- (no RNG; inputs are full samples).

Functions (pure stdlib; a sample is a list of floats, at least 1 element for
location measures):
- mean(sample) -> float; ValueError on empty.
- median(sample) -> float; ValueError on empty (sorted; even count averages
  the two middle values).
- data_range(sample) -> float: max - min; ValueError on empty.
- variance(sample, ddof=1) -> float: sum((x - mean)^2) / (n - ddof).
  ValueError if empty or n - ddof <= 0.
- std_dev(sample, ddof=1) -> sqrt of variance.
- percentile(sorted_sample, p) -> float: LINEAR interpolation between closest
  ranks: rank = p * (n - 1); lower index floor, upper ceil; value = lower +
  (upper - lower) * fraction. ValueError if p outside [0, 1] or empty.
- quartiles(sample) -> dict {q1, q2, q3} via percentile on the sorted sample
  at 0.25, 0.5, 0.75.
- interquartile_range(sample) -> q3 - q1.
- five_number_summary(sample) -> dict {min, q1, median, q3, max}.
- coefficient_of_variation(sample) -> float: std (ddof=1) / mean (fraction,
  not percent). ValueError if mean == 0 (report as division guard) or sample
  too small (n < 2 raises via variance ddof).
- outlier_indices_iqr(sample) -> list of ints: indices (original order) whose
  value is < q1 - IQR_FACTOR * iqr or > q3 + IQR_FACTOR * iqr.
- summary(sample) -> dict: {n, mean, median, min, max, range, sample_variance,
  sample_std, q1, q3, iqr, five_number_summary, coefficient_of_variation,
  outlier_indices, outlier_values}. ValueErrors propagate.

## Worked example

Sample: [2, 4, 4, 4, 5, 5, 7, 9].

Deterministic anchors (EXACT for most; assert within 1e-9 relative):
- mean = 5.0 exactly; median = 4.5 exactly (even count); range = 7.0.
- sample variance = 32/7 = 4.5714285714; sample std = 2.1380899353.
- population variance (ddof=0) = 4.0 exactly; population std = 2.0 exactly.
- q1 = 4.0, q3 = 5.5 (linear interpolation as defined), iqr = 1.5.
- five-number summary {2, 4, 4.5, 5.5, 9}.
- outliers: lower fence 4 - 1.5*1.5 = 1.75, upper fence 5.5 + 2.25 = 7.75;
  indices of 9 only (value 9) -> [7]. (2 is NOT an outlier: 2 > 1.75.)
- coefficient of variation = 2.13809 / 5 = 0.42762.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError on empty sample for all measures; variance/std with n = 1
  (ddof=1) raises; percentile p outside [0,1] raises; cv on zero mean raises.
- Single-element sample: mean/median == the value, range == 0.
- Even/odd median behavior (odd sample [1,2,3] median 2 exactly).
- Outlier boundary: value exactly AT the fence is NOT flagged (use 7.75 case
  from a crafted sample).
- Determinism; no RNG.

## Corpus fragment (eval/hit1-wave30-descriptive-statistics.yaml)

Forbidden tokens (siblings): t-test, p-value, chi-square, regression,
slope, intercept, monte-carlo, distribution-fit, weibull, control-chart,
cpk. Distinctive tokens ONLY: descriptive-statistics, summary-statistics,
five-number-summary, interquartile-range, coefficient-of-variation.

Query 1: "Run descriptive-statistics on a set of measured samples: give the
five-number-summary, interquartile-range, and sample standard deviation"
(id w30-descriptive-statistics-1).
Query 2: "Flag outliers in a data set with the 1.5 interquartile-range rule
and report the coefficient-of-variation" (id w30-descriptive-statistics-2).
intent: "cross-cutting; sample summary statistics and outlier flagging".

## Description/tag guidance

Description opens "Use when you must summarize a sample of engineering
measurements with descriptive statistics:" and lists the outputs in the
Claim. First tag: descriptive-statistics. Additional tags:
summary-statistics, five-number-summary, interquartile-range,
coefficient-of-variation. NEVER use bare mean/median/std/variance/statistics
as tags (they steal corpus tasks). 50-150 words, <=1000 chars, no em dash, no
"classified".

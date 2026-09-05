# Wave-39 leaf spec: chi-square-goodness-of-fit (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/chi-square-goodness-of-fit/
- Pack: numerics. Closest siblings: hypothesis-testing (chi2 test of
  independence for 2-D contingency tables only: chi2_independence computes
  the statistic, degrees of freedom and one-tailed p for association, not
  model fit), probability-distributions (its chi2_gof is scoped to fitting
  a continuous distribution among normal, lognormal, exponential, weibull
  and bins raw floats; it cannot test user-supplied observed versus
  expected counts and raises on post-merge degrees of freedom outside its
  small embedded critical table), least-squares-regression and multiple-
  linear-regression (R2 prose only). Whole-tree greps at prep: a one-D
  categorical goodness-of-fit test with an exact p-value = 0 owners.
  GENUINE CC gap (fresh probe).
- Standards id: naca-tr-824 (reference-only; numerics-pack convention).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Test whether observed counts in k categories fit a stated model with the
chi-square goodness-of-fit statistic: compute stat = sum((O_i - E_i)^2 /
E_i) over the categories, set the degrees of freedom to k - 1 - m (m =
number of parameters estimated from the data, default 0), compute the
one-tailed p-value from the chi-square survival function (regularized
lower incomplete gamma), and return the verdict against a significance
level. Produces the statistic, degrees of freedom, p-value and verdict
that gate categorical model checks such as uniform defect counts or
Poisson count fits. Does NOT do: chi-square test of independence for
contingency tables (hypothesis-testing); continuous-distribution fit
scoring (probability-distributions).

## Model (implement exactly)

Functions (pure stdlib, self-contained - no cross-leaf imports):
- chi_square_gof_statistic(observed, expected) -> float
  sum((O_i - E_i)^2 / E_i); ValueError if lengths differ, observed
  negative, any expected <= 0, fewer than 2 categories, non-finite.
- goodness_of_fit_p_value(statistic, degrees_freedom) -> float: the
  survival probability P(chi2_df > statistic) computed as
  1 - regularized_lower_incomplete_gamma(df/2, stat/2) with the standard
  series for x < a + 1 and the continued-fraction evaluation otherwise.
  ValueError if statistic < 0 or degrees_freedom < 1.
- chi_square_goodness_of_fit(observed, expected, alpha=0.05) -> dict with
  keys statistic, df, p_value, verdict ("reject" when p <= alpha else
  "fail-to-reject"); ValueError if alpha outside (0, 1).
- Optional merge flag: when merge_small_expected True, categories whose
  expected count is below 1 are merged with the next category before the
  statistic is computed (documented in the body).
Module constants: none magic; the incomplete gamma uses the standard
series/continued-fraction split at x = a + 1.

Identity to test: observed equal to expected gives statistic 0 and p = 1;
doubling all observed and expected counts doubles the statistic for a
fixed relative deviation; the statistic is invariant to scaling both
observed and expected by a positive constant when expected is scaled too
(relative-fit property); p decreases as the statistic grows at fixed df.

## Worked example

Uniform check, 7 days, total 300 defects, expected 300/7 = 42.857 each,
observed [50, 42, 38, 45, 43, 40, 42]:
- statistic = 2.0734, df = 6, p = 0.913 -> fail-to-reject at 0.05
  (defect counts consistent with a uniform daily rate).
Skewed set [60, 30, 25, 20, 18, 15, 12] (total 180, expected 25.714):
- statistic = 61.81, df = 6, p = 1.93e-11 -> reject.
Small two-bin example: observed [8, 2] vs expected [5, 5] gives
statistic 3.6, df 1, p = 0.0578 (fail-to-reject at 0.05).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (the uniform and skewed statistics were
independently evaluated at prep).

## Validation list (contract test must include)

- Uniform example: statistic 2.073 within 0.01, df 6, p 0.913 within
  0.005, verdict fail-to-reject.
- Skewed example: statistic 61.8 within 0.3, p below 1e-9, verdict
  reject.
- Two-bin example [8, 2] vs [5, 5]: statistic 3.6, df 1, p 0.0578 within
  1e-3 (fail-to-reject at 0.05, reject at 0.10 boundary documented).
- observed == expected: statistic 0, p 1.0.
- ValueErrors: length mismatch, negative observed, zero expected, one
  category, alpha 0 or 1, negative statistic.
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-chi-square-goodness-of-fit.yaml)

Query 1 (copy verbatim):
  "run a chi-square-goodness-of-fit test on the observed defect counts over seven days against the uniform expected count per day"
  intent: "cross-cutting; categorical goodness of fit with exact p-value"
  expected_skill: "cross-cutting/numerics/chi-square-goodness-of-fit"
Query 2 (copy verbatim):
  "chi-square goodness of fit statistic for the observed versus the expected poisson counts per inspection unit"
  intent: "cross-cutting; count-data model fit test"
  expected_skill: "cross-cutting/numerics/chi-square-goodness-of-fit"
Task ids: w39-chi-square-goodness-of-fit-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must test whether observed counts fit a
stated categorical model:" and include the outputs in the Claim. First tag:
chi-square-goodness-of-fit. Additional tags ONLY: categorical-model-test,
observed-versus-expected, count-data-model-fit, goodness-of-fit-p-value.
NEVER single generic words (chi, square, goodness, fit, test, counts,
categories, model). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): chi-square-test-of-independence,
contingency-table, association (hypothesis-testing); distribution-fit,
kolmogorov-smirnov, weibull-fit (probability-distributions); r-squared,
least-squares (regression leaves).

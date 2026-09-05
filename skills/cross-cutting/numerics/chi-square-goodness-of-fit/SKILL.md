---
name: chi-square-goodness-of-fit
description: "Use when you must test whether observed counts fit a stated categorical model: the chi-square goodness-of-fit statistic as the sum of the squared observed-minus-expected gaps over expected counts, the degrees of freedom k minus 1 minus estimated parameters, and the one-tailed p-value from the chi-square survival function via its own regularized lower incomplete gamma, returning the reject or fail-to-reject verdict at a stated significance level. Produces the statistic, degrees of freedom, p-value and verdict that gate model checks such as uniform defect counts per day or Poisson counts per inspection unit. Trigger: chi-square goodness of fit, observed versus expected counts, categorical model fit, count data fit, goodness-of-fit p-value."
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
  tags: [chi-square-goodness-of-fit, categorical-model-test, observed-versus-expected, count-data-model-fit, goodness-of-fit-p-value]
  version: 0.1.0
  author: AeroSkills
---

# Chi-square Goodness-of-Fit (cross-cutting/numerics/chi-square-goodness-of-fit)

Use when the task is to test whether observed counts in k categories fit a
stated categorical model: deciding whether per-day defect counts follow a
uniform rate, whether Poisson count data per inspection unit follow a
fitted mean, or whether any observed-versus-expected count table is
consistent with the model that produced the expected counts. This leaf
computes the chi-square goodness-of-fit statistic, sets the degrees of
freedom to k - 1 - m (m parameters estimated from the data, 0 by
default), evaluates the one-tailed p-value from the chi-square survival
function with its own self-contained regularized lower incomplete gamma
(series branch for x < a + 1, continued-fraction branch otherwise), and
returns the reject or fail-to-reject verdict at a stated significance
level. Pure Python stdlib, no sibling imports. It is the one-dimensional
categorical model-fit layer: the leaf that owns significance tests for
counts arranged in a two-way table is hypothesis-testing, and the leaf
that scores parametric continuous distributions from raw floats is
probability-distributions; this leaf is the only one that tests
user-supplied observed counts against user-supplied expected counts with
an exact p-value.

## Domain quick reference

- Chi-square goodness-of-fit statistic: stat = sum over the categories of
  (O_i - E_i)^2 / E_i, with O_i the observed count and E_i the expected
  count of category i under the stated model.
- Degrees of freedom: df = k - 1 - m, where k is the number of categories
  and m the number of parameters estimated from the data (0 default).
  Seven categories with no estimated parameters give df = 6.
- One-tailed p-value: p = P(chi2_df > stat) = 1 - P(df/2, stat/2), where
  P is the regularized lower incomplete gamma, series-evaluated when
  x = stat/2 is below a + 1 = df/2 + 1 and continued-fraction evaluated
  otherwise so very small survival probabilities keep their precision.
- Verdict: reject when p <= alpha, fail-to-reject otherwise, alpha the
  stated significance level (0.05 default).
- Expected-count merging: a category whose expected count falls below 1
  folds into the next category, or into the previous one when it is the
  final category, before the statistic is computed (optional flag).
- Small expected counts understate the validity of the chi-square
  approximation; merging keeps every expected count at or above 1.
- Scaling law: multiplying both the observed and the expected counts by
  one positive constant c multiplies the statistic by exactly c, so the
  per-category relative gap O_i/E_i is invariant under a common scale
  change. Spec note: this is the relative-fit scaling law the doubling
  identity states; a common scale change grows the evidence base, it does
  not leave the statistic unchanged.
- Standards context: NACA-TR-824 frames the numerical-methods background;
  the relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the count-data test point: the observed counts per category, the
   expected counts from the stated categorical model, the significance
   level alpha (0.05 default), the number of parameters estimated from
   the data m (0 default), and whether the expected-count traverse must
   merge categories whose expected count falls below 1.
2. Expected-count traverse: when merging is requested, run
   merge_small_expected_categories on the observed and expected counts so
   each deficient category folds into the next category, or into the
   previous one when it is the final category.
3. Statistic traverse: chi_square_gof_statistic(observed, expected)
   returns the sum of the squared observed-minus-expected gaps over the
   expected counts; a perfect model fit gives statistic 0.
4. Degrees-of-freedom bookkeeping: df = k - 1 - m, with k the number of
   categories after any merging and m the estimated-parameter count; the
   default m = 0 leaves df = k - 1, and df below 1 raises ValueError.
5. p-value traverse: goodness_of_fit_p_value(statistic, df) returns the
   one-tailed survival probability of the chi-square law at the
   statistic, evaluated through the module's own
   regularized_lower_incomplete_gamma with the series branch for x below
   a + 1 and the continued-fraction branch otherwise.
6. Verdict bookkeeping: chi_square_goodness_of_fit wraps steps 2 to 5
   and returns the fit report dict with keys statistic, df, p_value and
   verdict; the verdict is reject when p_value is at or below alpha and
   fail-to-reject otherwise.
7. Uniform-model check: confirm the worked-example anchors below against
   the spec-prep bounds before quoting a verdict.
8. Verification run: execute python3 scripts/test_chi_square_goodness_
   of_fit.py (35 tests, deterministic, offline).

## Worked example

Uniform check: total 300 defects over 7 days, expected 300/7 = 42.857
per day, observed [50, 42, 38, 45, 43, 40, 42].

- Statistic traverse: stat = 2.0733 (spec-prep anchor 2.0734 within
  0.01), so the per-day relative gaps are mild.
- Degrees-of-freedom bookkeeping: df = 7 - 1 - 0 = 6.
- p-value traverse: p = 0.91283 (anchor 0.913 within 0.005).
- Verdict bookkeeping at alpha 0.05: fail-to-reject, the defect counts
  are consistent with a uniform daily rate.

Skewed set [60, 30, 25, 20, 18, 15, 12], total 180, expected 25.714:

- Statistic: 61.8111 (anchor 61.81 within 0.3), df = 6.
- p-value: 1.93e-11, below the 1e-9 prep bound.
- Verdict at alpha 0.05: reject the uniform model.

Two-bin boundary [8, 2] versus [5, 5]:

- Statistic: 3.6, df = 1, p = 0.05778 (anchor 0.0578 within 1e-3).
- Verdict: fail-to-reject at alpha 0.05, reject at alpha 0.10, the
  p-value sitting between the two significance levels.

Merged example [1, 9, 6] versus [0.5, 10, 5]:

- Expected-count traverse folds the first category into the second,
  giving observed [10, 6] and expected [10.5, 5]; df drops from 2 to 1
  and the statistic is 0.2238.

## Verification

- Confirm chi_square_gof_statistic([50, 42, 38, 45, 43, 40, 42],
  [42.857] * 7) returns 2.0733, within 0.01 of 2.0734, and that the
  skewed set returns 61.8111, within 0.3 of 61.81.
- Confirm observed counts equal to the expected counts give statistic 0
  and p = 1.0 exactly, and that doubling both the observed and the
  expected counts doubles the statistic at a fixed relative deviation.
- Confirm goodness_of_fit_p_value(3.6, 1) returns 0.05778, matching
  erfc(sqrt(1.8)) to eight decimals, and that the p-value falls as the
  statistic grows at fixed df.
- Confirm the gamma anchors: P(1, 1) = 1 - 1/e and P(0.5, x) =
  erf(sqrt(x)) on both the series and the continued-fraction branches.
- Confirm chi_square_goodness_of_fit returns exactly the statistic, df,
  p_value and verdict keys and is deterministic across identical calls.
- Confirm ValueError rejection of length mismatches, negative observed
  counts, non-positive or non-finite expected counts, fewer than two
  categories, negative or non-finite statistics, degrees of freedom below
  1, alpha outside (0, 1) and df below 1 after subtracting estimated
  parameters.
- Run the contract test offline: python3
  scripts/test_chi_square_goodness_of_fit.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the leaf that owns
  significance tests for counts arranged in a two-way table; it does not
  test observed-versus-expected categorical model fit.
- cross-cutting/numerics/probability-distributions: parametric continuous
  distribution scoring from raw floats, the sibling that handles the
  continuous fit side this leaf does not cover.
- cross-cutting/numerics/fisher-exact-test: exact test for small two-way
  count tables, an alternative when expected counts are too small for
  the chi-square approximation.
- cross-cutting/numerics/confidence-interval-estimation: the interval
  view of the same count data, complementary to a reject or fail-to-
  reject verdict.

## Pitfalls

- Quoting the statistic without the degrees of freedom: the p-value
  traverse needs df = k - 1 - m, and the same statistic at a different
  df gives a different survival probability, so a naked statistic
  carries no verdict.
- Forgetting the estimated-parameter count: when the expected counts
  come from a model fit to the data (one Poisson mean estimated from the
  observed counts), df is k - 2, not k - 1, and the extra degree of
  freedom inflates the p-value.
- Merging after computing the statistic: the expected-count traverse must
  fold small-expected categories before the statistic traverse, and the
  degrees of freedom follow the merged category count.
- Testing two-way table association here: counts arranged in a table with
  row and column structure belong to the hypothesis-testing leaf; this
  leaf tests one-dimensional observed-versus-expected model fit.
- Reading the verdict without the significance level: the two-bin example
  fails to reject at 0.05 yet rejects at 0.10, so every verdict must name
  its alpha.
- Treating a common scale change as neutral: doubling both the observed
  and the expected counts doubles the statistic, which is the relative-
  fit scaling law, not an invariance of the statistic itself.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_chi_square_goodness_of_fit.py

The test covers the worked-example anchors (uniform defect counts
statistic 2.0733 with p-value 0.91283 and df 6, skewed counts statistic
61.8111 with a survival probability below 1e-9, the two-bin statistic 3.6
with p-value 0.05778), the perfect-fit zero statistic and unit p-value
identity, the hand recomputation of the statistic, the doubling and
common-scale relative-fit scaling laws, the expected-count traverse and
its degrees-of-freedom effect, the estimated-parameter degrees-of-freedom
bookkeeping, the gamma closed forms on the series and continued-fraction
branches with the branch-boundary continuity, the p-value trend, the
reject and fail-to-reject verdicts with the 0.05 to 0.10 boundary, the
exact report dict keys, determinism, and every ValueError guard from the
validation list.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 is a public-domain
  NACA technical report framing the numerical-methods context; the
  chi-square goodness-of-fit relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-38 leaf spec: proportion-confidence-interval (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/proportion-confidence-interval/
- Pack: numerics. Closest siblings: confidence-interval-estimation
  (Student t interval for a sample MEAN, pooled/Welch difference of means,
  chi-square interval for a VARIANCE - the leaf's claim explicitly names
  those three and has zero proportion-family content), hypothesis-testing
  (tests), descriptive-statistics (sample stats), probability-distributions
  (distribution math). Whole-tree grep: "Wilson score", "Clopper-Pearson",
  "proportion confidence", "binomial proportion" = ZERO owning hits
  (gnss-raim-fde uses "Wilson-Hilferty" only as a chi-square quantile
  approximation citation, no function). ZERO owners of the binomial
  proportion interval family. GENUINE CC gap (fresh probe).
- Standards id: naca-tr-824 (reference-only; numerics sibling convention).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Estimate a confidence interval for a binomial proportion from attribute
data: compute the Wilson score interval with its continuity-corrected
variant, compute the exact Clopper-Pearson interval by inverting the
binomial tail (regularized incomplete beta), and compute the confidence
interval for the difference of two proportions. Produces the interval
bounds by each method, the interval width, and the method recommendation
that gate attribute-data claims. Does NOT do: t interval for a mean or
variance interval (confidence-interval-estimation); hypothesis tests on
proportions (hypothesis-testing).

## Model (implement exactly)

Conventions: k successes in n trials; confidence level cl in (0, 1)
(default 0.95); z = normal quantile for the two-sided level (in-leaf
Acklam or a bisection on the normal CDF; 1.959964 for 0.95). All bounds
in [0, 1].

Wilson score interval:
- center = (phat + z^2/(2n)) / (1 + z^2/n)
- half_width = z * sqrt(phat*(1-phat)/n + z^2/(4n^2)) / (1 + z^2/n)
- bounds = center +/- half_width, clamped to [0, 1].
- Continuity-corrected Wilson (optional function): apply the standard
  continuity correction terms.

Clopper-Pearson exact interval:
- lower = inverse of the regularized incomplete beta I_p(k, n-k+1) =
  alpha/2; upper = inverse of I_p(k+1, n-k) = 1 - alpha/2, with the
  documented endpoint handling (k=0 lower 0, k=n upper 1).
- Implement the regularized incomplete beta and its inverse by bisection
  in-leaf (same pattern as confidence-interval-estimation).

Two-proportion difference:
- Wilson-style or normal-approximation interval for p1 - p2:
  diff +/- z * sqrt(phat1*(1-phat1)/n1 + phat2*(1-phat2)/n2)
  (documented normal-approximation model).

Functions (pure stdlib):
- normal_quantile(p) -> float (in-leaf; p in (0, 1)).
- wilson_score_interval(k, n, cl=0.95) -> dict {lower, upper, width}.
  ValueErrors: k outside [0, n], n <= 0, cl outside (0, 1).
- wilson_score_cc_interval(k, n, cl=0.95) -> dict (continuity-corrected).
- regularized_incomplete_beta(a, b, x) -> float (in-leaf).
- beta_quantile(a, b, q) -> float (bisection, tolerance 1e-10).
- clopper_pearson_interval(k, n, cl=0.95) -> dict {lower, upper, width}.
- two_proportion_diff_interval(k1, n1, k2, n2, cl=0.95) -> dict {diff,
  lower, upper, width}.
Identity to test: Wilson and Clopper-Pearson intervals contain phat; the
Wilson interval of 0 successes has lower 0; the interval width shrinks as
n grows at fixed phat; the Clopper-Pearson interval is wider than or equal
to the Wilson interval at small n (exactness).

## Worked example

Verified at prep (cl = 0.95, z = 1.959964):
- k = 12, n = 400 (phat 0.03): Wilson = [0.017243, 0.051699];
  Clopper-Pearson = [0.015596, 0.051817].
- k = 0, n = 30: Wilson = [0.0, 0.113513]; Clopper-Pearson = [0.0,
  0.115703] (rule of three check: upper near 0.1157).
- k = 30, n = 30: Wilson = [0.886487, 1.0]; Clopper-Pearson =
  [0.884297, 1.0].
- Two-proportion diff for k1 = 5, n1 = 100, k2 = 1, n2 = 100: diff 0.04,
  width = 1.959964 * sqrt(0.000475 + 0.000099) = 1.959964 * 0.023958 =
  0.04696 -> interval [-0.00696, 0.08696] (computed at prep; assert the
  width within 1e-3).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the closed-form Wilson formulas and
the exact beta inversion (independently evaluated by the anchor script at
prep).

## Validation list (contract test must include)

- Wilson anchor bounds within 1e-4 of [0.01724, 0.05170] for 12/400 and
  [0.0, 0.11351] for 0/30.
- Clopper-Pearson anchors within 1e-4 (0.01560 lower, 0.05182 upper for
  12/400; 0.11570 upper for 0/30).
- Interval contains phat for both methods at several (k, n).
- Width shrinks with larger n at fixed phat.
- Two-proportion width anchor within 1e-3.
- ValueErrors for k outside [0, n], n <= 0, cl outside (0, 1).
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-proportion-confidence-interval.yaml)

Query 1 (copy verbatim):
  "compute the wilson-score-interval and the clopper-pearson-interval for a binomial proportion from k successes in n trials"
  intent: "cross-cutting; binomial proportion confidence intervals"
  expected_skill: "cross-cutting/numerics/proportion-confidence-interval"
Query 2 (copy verbatim):
  "estimate the two-proportion difference interval for attribute data with zero failures in the sample"
  intent: "cross-cutting; difference of proportions interval"
  expected_skill: "cross-cutting/numerics/proportion-confidence-interval"
Task ids: w38-proportion-confidence-interval-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate a confidence interval
for a binomial proportion:" and include the outputs in the Claim. First
tag: proportion-confidence-interval. Additional tags ONLY: wilson-score-
interval, clopper-pearson-interval, binomial-proportion, exact-confidence-
bound, two-proportion-difference. NEVER single generic words (proportion,
interval, confidence, binomial, sample, bound). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): Student t interval for a mean,
chi-square interval for the variance, Welch-Satterthwaite (confidence-
interval-estimation); hypothesis test verdict, p-value significance
(hypothesis-testing).

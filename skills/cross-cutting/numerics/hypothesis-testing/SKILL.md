---
name: hypothesis-testing
description: "Use when you must run significance tests on aerospace engineering data: the one-sample and two-sample Student t tests (pooled and Welch), the paired t test, the two-variance F test, the chi-square test of independence, and the one-way ANOVA F test, computing each statistic, its degrees of freedom, and its p-value from the incomplete beta and gamma functions and returning the reject-null or fail-to-reject verdict at a stated significance level. Produces the statistic, df, p-value, and verdict that gate the data-comparison conclusion for test versus baseline, batch versus batch, or configuration A versus B. Trigger: hypothesis testing, student t test, welch test, paired t test, ANOVA, F test for variances, chi-square test of independence, p-value, reject null hypothesis."
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
  tags: [hypothesis-testing, student-t-test, welch-test, paired-t-test, anova, f-test-for-variances, chi-square-test-of-independence, p-value, significance-level, reject-null-hypothesis, drag-counts-comparison, configuration-difference-significance]
  version: 0.1.0
  author: Aero Agent Skills
---

# Hypothesis Testing (cross-cutting/numerics/hypothesis-testing)

Use when the task is to run significance tests on aerospace engineering
measured data: deciding whether a test article configuration differs
from a baseline, whether two production batches agree, or whether
configuration A drag counts differ from configuration B. This leaf
implements the standard null-hypothesis significance tests (Student t,
Welch, paired t, two-variance F, chi-square test of independence, one-way
ANOVA) in pure Python, stdlib only, with every p-value computed from the
module's own regularized incomplete beta and lower incomplete gamma
implementations (Lentz continued fraction and series). It pairs with
cross-cutting/numerics/probability-distributions to check the normality
assumption before a t test and with least-squares-regression to compare
fits; it is the significance-test layer, not a fitting, sampling, or
process-monitoring layer.

## Domain quick reference

- Regularized incomplete beta I_x(a, b): Lentz continued fraction,
  ITMAX = 200, EPS = 3e-12, with the symmetry I_x(a, b) = 1 - I_(1-x)(b, a).
- Regularized lower incomplete gamma P(a, x): series for x < a + 1,
  continued fraction for the complement otherwise, normalized by
  math.lgamma. P(1, 1) = 1 - e^-1 and P(0.5, x) = erf(sqrt(x)).
- t two-sided p-value: I_(df/(df + t^2))(df/2, 1/2) on |t|; one-sided p
  is half of the two-sided p.
- F upper-tail p-value: I_(df2/(df2 + df1 f))(df2/2, df1/2).
- chi2 cdf: P(df/2, x/2).
- One-sample t: stat = (mean - mu0) / (s / sqrt(n)), df = n - 1.
- Two-sample pooled t: s_p^2 = ((n1-1)s1^2 + (n2-1)s2^2) / (n1 + n2 - 2),
  stat = (m1 - m2) / (s_p sqrt(1/n1 + 1/n2)), df = n1 + n2 - 2; Welch
  uses the Satterthwaite df instead.
- Paired t: one-sample t on the differences d = a - b against 0, df = n - 1.
- Two-variance F: stat = s_max^2 / s_min^2 (>= 1 by swapping), two-sided
  p = 2 * min(upper-tail, 1 - upper-tail) capped at 1.0.
- chi2 independence: stat = sum (O - E)^2 / E over rows x cols, E =
  row_total * col_total / n, df = (r - 1)(c - 1); valid only when every
  expected count is at least 1.
- One-way ANOVA: F = (SS_between / (k - 1)) / (SS_within / (N - k)),
  p from the F upper tail; for two groups F equals the pooled t squared.
- Verdicts: reject-null when p <= alpha, else fail-to-reject, alpha
  default ALPHA = 0.05.
- NACA-TR-824 frames the statistical analysis context for flight data;
  the relations above are standard engineering methodology, summary-only.

## Workflow

1. State the comparison question and pick the test: one-sample t when a
   measured mean is checked against a reference value mu0
   (t_test_1samp), two-sample t when two independent groups are compared
   (t_test_2samp, pooled with equal_var True, Welch with equal_var
   False), paired t when measurements come in pairs such as before and
   after (t_test_paired).
2. Check the variance question with f_test_variances when the spread of
   two batches must be compared, and the normality assumption with the
   probability-distributions leaf before small-sample t tests.
3. For counted data in a contingency table, run the chi-square test of
   independence with chi2_independence and inspect the returned expected
   table.
4. For three or more groups, run the one-way ANOVA across the batches
   with anova_oneway.
5. Confirm the p-values are computed by the module's own incomplete beta
   and gamma functions, then read each verdict against the stated alpha.
6. Collect several test results with summarize for one combined note
   listing which tests reject the null.
7. Confirm the deterministic checks with the contract test
   scripts/test_hypothesis_testing.py.

## Worked example

Config A drag counts a = [267, 261, 263, 258, 262] versus config B
b = [273, 271, 268, 275, 270], classic small samples.

- Pooled two-sample t: stat = -4.849, df = 8, p = 0.00127, so p < 0.01
  and the verdict is reject-null at alpha 0.05: the configurations
  differ. Mean of a (262.2) is below mean of b (271.4).
- Welch on the same data: df = 7.724 (below 8), p = 0.00141, same
  reject-null verdict.
- Paired test on c = [1.0, 2.0, 1.5, 2.0, 1.8] and
  d = [1.1, 2.1, 1.6, 2.2, 1.9]: differences all +0.1, stat = -6.0,
  p = 0.00388, reject-null at 0.05.
- Identity: the pooled t stat squared (-4.849^2 = 23.511) equals the
  one-way ANOVA F for the same two groups, and the two-sided p values
  match to 1e-9.
- F test for variances on identical data (a vs a): stat = 1.0, p = 1.0,
  fail-to-reject.
- chi2 independence on the perfectly independent table [[10, 20],
  [30, 60]]: stat = 0, p = 1.0, fail-to-reject; on [[15, 15], [5, 25]]:
  stat = 7.5, df = 1, p = 0.00617, reject-null.
- One-sample t on S = [100, 200, 300, 400, 500] against mu0 = 300:
  stat = 0, p = 1.0, fail-to-reject; against mu0 = 100: stat = 2.828,
  p = 0.0474, reject-null at 0.05.
- Cross-checks: t_cdf(0, 10) = 1.0, t_cdf(1e6, 10) ~ 0, and
  chi2_cdf(0, 5) = 0.0.

## Verification

- Confirm t_test_2samp on the drag counts returns df 8, p < 0.01 and
  reject-null, and that the Welch df is below 8 with the same verdict.
- Confirm the paired test on the constant +0.1 differences rejects at
  alpha 0.05.
- Confirm t_test_2samp stat squared equals the anova_oneway F on the
  same two groups and the two-sided p values agree within 1e-9.
- Confirm f_test_variances(a, a) returns stat 1.0 and p 1.0.
- Confirm chi2_independence returns p 1.0 on the perfectly independent
  table and p < 0.05 on the dependent table.
- Confirm t_test_1samp(S, 300) returns stat 0 and p 1.0.
- Confirm ValueError on fewer than 2 points (3 for variance tests and
  ANOVA), length-mismatched paired inputs, non-finite values, zero
  variance in a one-sample test, zero row or column totals, expected
  counts below 1, non-rectangular tables, and alpha outside (0, 1).
- Run the contract test offline: python3
  scripts/test_hypothesis_testing.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/least-squares-regression: fit comparisons that
  consume the same data-comparison conclusions.
- cross-cutting/numerics/monte-carlo-sampling: distribution of test
  statistics under simulated scatter, the sampling layer above this one.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hypothesis_testing.py

The test covers the worked-example anchors (drag count comparison with
pooled and Welch t tests, paired constant-shift rejection, the
t-squared equals ANOVA F identity, F on identical data, the chi2
independence tables, the centered one-sample anchor), special-function
values including the erf and exponential identities, the beta symmetry,
boundary and degenerate verdicts, and ValueError rejection of
non-physical inputs.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames flight data
  statistical analysis; the significance test relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

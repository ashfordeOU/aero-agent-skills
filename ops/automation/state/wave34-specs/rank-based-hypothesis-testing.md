# Wave-34 leaf spec: rank-based-hypothesis-testing (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/rank-based-hypothesis-testing/
- Pack: numerics. Closest siblings: hypothesis-testing (PARAMETRIC
  tests: one/two-sample t, pooled and Welch, paired t, F for
  variances, chi-square independence, one-way ANOVA; checks the
  normality assumption), confidence-interval-estimation (intervals),
  probability-distributions (distributions and quantiles),
  descriptive-statistics (sample moments). This leaf owns
  DISTRIBUTION-FREE two-sample and paired location tests that remain
  valid when normality fails: Wilcoxon rank-sum (Mann-Whitney U),
  Wilcoxon signed-rank, sign test, each with normal-approximation
  p-values, continuity correction and verdict at alpha. No function
  overlap.
- Standards id: naca-tr-824 (numerics pack convention; reference-only).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Run rank-based (nonparametric) hypothesis tests for location: the
Wilcoxon rank-sum test (Mann-Whitney U) comparing two independent
samples, the Wilcoxon signed-rank test for paired data, and the sign
test, each with exact rank sums, the normal-approximation z with
continuity correction, the two-sided p-value and the reject/accept
verdict at a chosen alpha. Produces the test statistics, z, p-value
and verdict that remain valid when the normality assumption of the
parametric sibling fails.

Does NOT do: parametric t/F/ANOVA/chi-square tests and normality
checking (hypothesis-testing owns the parametric family); confidence
intervals (confidence-interval-estimation); distribution quantiles
(probability-distributions); descriptive moments
(descriptive-statistics).

## Model (implement exactly)

Conventions: two-sided tests with the default alpha 0.05. Ties are
resolved by average ranks (state it). The normal approximation uses
the standard error of the rank-sum statistic with the continuity
correction 0.5.

Wilcoxon rank-sum (Mann-Whitney U):
- Merge the two samples, rank all observations (average ranks for
  ties). R1 = sum of ranks of sample 1.
- U = R1 - n1 (n1 + 1)/2 (equivalently U = n1 n2 + n1(n1+1)/2 - R1
  when using the other orientation; state the convention and keep it
  consistent: U = R1 - n1(n1+1)/2 with sample 1 as the x sample,
  matching the worked example below).
- Mean mu_U = n1 n2 / 2; sd_U = sqrt(n1 n2 (n1 + n2 + 1) / 12);
  z = (U - mu_U +- 0.5)/sd_U with the continuity correction toward
  zero (U < mu_U adds 0.5; U > mu_U subtracts 0.5).
- Two-sided p = 2 * (1 - Phi(|z|)); Phi via math.erf.

Wilcoxon signed-rank (paired):
- Differences d_i = x_i - y_i; drop zeros; rank the absolute
  differences (average ranks for ties). W = sum of signed ranks (the
  ranks of positive differences minus the ranks of negative
  differences; state the convention).
- Mean mu_W = 0; sd_W = sqrt(n (n + 1) (2n + 1) / 6); z = (W -
  sign(W) * 0.5)/sd_W; p two-sided as above.

Sign test (paired):
- Count positives n+ among nonzero differences; n = n+ + n-;
  z = (n+ - n/2 +- 0.5)/sqrt(n/4) with continuity correction;
  p two-sided as above (binomial normal approximation).

Functions (pure stdlib):
- _normal_cdf(z) -> Phi(z) = 0.5 (1 + erf(z / sqrt(2))).
- _rank_values(values) -> average ranks list.
- wilcoxon_rank_sum(x, y, alpha = 0.05) -> dict {n1, n2, r1, u,
  mu_u, sd_u, z, p_value, reject}. ValueErrors: fewer than 2
  observations per sample; alpha <= 0 or >= 1.
- wilcoxon_signed_rank(x, y, alpha = 0.05) -> dict {n, w, sd_w, z,
  p_value, reject}. ValueErrors: fewer than 2 nonzero differences;
  length mismatch.
- sign_test(x, y, alpha = 0.05) -> dict {n_pos, n_neg, n, z,
  p_value, reject}. ValueErrors: length mismatch, no nonzero
  differences.
- rank_test_summary(test, x, y, alpha = 0.05) -> dict dispatching to
  one of the three by the test string ("rank-sum", "signed-rank",
  "sign") with the chosen test's outputs. ValueError on unknown test.

Identity to test: the rank-sum U of identical samples equals n1 n2/2
when ranks interleave evenly; z = 0 and p = 1 for exactly identical
values (all ties -> average ranks equal -> U = n1 n2/2). Signed-rank
W = 0 and p = 1 for a perfectly symmetric paired sample.

## Worked example

Reference (verified at prep):
- Rank-sum: two finish-roughness batches x = [0.82, 0.79, 0.85, 0.80,
  0.83] vs y = [0.96, 1.02, 0.94, 0.98, 0.99], alpha 0.05. Merged
  ranks give R1 = 15.0 (x occupies the five lowest), U = 15.0 -
  5*6/2 = 0.0, mu_U = 12.5, sd_U = sqrt(25 * 11 / 12) = 4.787,
  z = (0 - 12.5 + 0.5)/4.787 = -2.5067, p = 0.01219, reject True.
- Signed-rank: paired series (6 each) giving W = -21.0, sd_W =
  sqrt(6*7*13/6) = 9.539, z = -2.1490 (with continuity correction
  toward zero: (-21 + 0.5)/9.539), p = 0.03164, reject at 0.05.
- Sign test: e.g. 8 positive of 10 differences: z = (8 - 5 - 0.5)/
  sqrt(10/4) = 2.5/1.581 = 1.5811, p = 0.1138, accept at 0.05.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds above. If a value falls outside its bound, your
implementation has a bug: find it before writing tests. In the SKILL.md
worked example show your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: fewer than 2 per sample; alpha out of (0, 1); length
  mismatch; no nonzero differences; unknown test name.
- Rank-sum worked case: R1 = 15.0, U = 0.0, z = -2.5067, p = 0.01219,
  reject True; a clearly separated reversed case gives reject True in
  the other direction (z positive).
- Identical samples: U = n1 n2/2, z ~ 0, p ~ 1 (within 1e-6), reject
  False.
- Ties: [1, 2, 3] vs [1, 2, 3] identical values exercise average
  ranks (p ~ 1).
- Signed-rank worked case: W = -21.0, z = -2.1490, p = 0.03164,
  reject True; symmetric paired sample gives W = 0, p = 1.
- Sign test: 8/10 positives z 1.5811 p 0.1138 accept; 10/10
  positives z ~ 3.0 p ~ 0.0027 reject (hand check the approximation).
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-rank-based-hypothesis-testing.yaml)

Query 1 (copy verbatim):
  "run the wilcoxon rank sum test between two independent samples and return the U statistic, z score and p value without a normality assumption"
  intent: "cross-cutting; Wilcoxon rank-sum Mann-Whitney U nonparametric two sample test"
  expected_skill: "cross-cutting/numerics/rank-based-hypothesis-testing"
Query 2 (copy verbatim):
  "compute the wilcoxon signed rank test and the sign test on paired measurements with continuity correction and the reject verdict"
  intent: "cross-cutting; Wilcoxon signed-rank and sign test paired nonparametric tests"
  expected_skill: "cross-cutting/numerics/rank-based-hypothesis-testing"
Task ids: w34-rank-based-hypothesis-testing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compare two samples without
relying on the normality assumption:" and include the outputs in the
Claim. First tag: rank-based-hypothesis-testing. Additional tags ONLY:
wilcoxon-rank-sum-test, mann-whitney-u-test, wilcoxon-signed-rank-test,
sign-test, normality-free-comparison, two-sample-rank-test. NEVER
single generic words (rank, test, hypothesis, sample, wilcoxon,
median). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): t-test, ANOVA, F-test,
chi-square, pooled variance, Welch (hypothesis-testing owns the
parametric family); confidence interval (confidence-interval-
estimation); normal distribution quantile (probability-distributions).
The words "Wilcoxon", "rank-sum", "Mann-Whitney", "signed-rank",
"sign test", "nonparametric" are this leaf's own.

Tags: [rank-based-hypothesis-testing, wilcoxon-rank-sum-test,
mann-whitney-u-test, wilcoxon-signed-rank-test, sign-test,
normality-free-comparison, two-sample-rank-test]

Sibling-citation lines for Related leaves:
cross-cutting/numerics/hypothesis-testing (the parametric sibling;
boundary: t/F/ANOVA vs distribution-free ranks),
cross-cutting/numerics/descriptive-statistics (moments and ordering
context),
cross-cutting/numerics/probability-distributions (normal quantile
context for the approximation).

Ledger Standard: naca-tr-824.

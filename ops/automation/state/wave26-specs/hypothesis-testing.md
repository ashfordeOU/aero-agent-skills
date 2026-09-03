# Wave-26 leaf spec: hypothesis-testing (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/hypothesis-testing/
- Pack: numerics (siblings: probability-distributions,
  monte-carlo-sampling, least-squares-regression)
- Standards ids: naca-tr-824  (Ledger Standard: naca-tr-824)
- Family: cross-cutting

## Claim

Run the standard significance tests for aerospace engineering data
comparisons: one-sample and two-sample Student t tests (pooled and
Welch), the paired t test, the two-variance F test, the chi-square
test of independence on a contingency table, and the one-way ANOVA F
test; compute each test statistic, its degrees of freedom, and its
p-value from the incomplete beta and incomplete gamma functions, and
return the verdict against a stated significance level. Produces the
statistic, df, p-value, and accept/reject verdict per test that gate
the data-comparison conclusion (test vs baseline, batch vs batch,
configuration A vs B).

Does NOT do: fit distributions or run goodness-of-fit
(probability-distributions owns fitting and KS/chi2 fit tests), sample
or simulate (monte-carlo-sampling), fit lines or curves
(least-squares-regression), or monitor a process with control charts
(manufacturing-quality as9100 statistical-process-control owns SPC
charting). This leaf is the null-hypothesis significance-test layer.

## Model (implement exactly)

Special functions (implement in the module, small and documented):
- regularized incomplete beta I_x(a, b) via the continued fraction
  (Lentz algorithm, module constants ITMAX = 200, EPS = 3e-12) with
  the standard symmetry I_x(a,b) = 1 - I_(1-x)(b,a); ValueError on
  a <= 0 or b <= 0 or x outside [0, 1].
- regularized lower incomplete gamma P(a, x) via the series for
  x < a + 1 and the continued fraction otherwise (module constants
  ITMAX = 200, EPS = 3e-12); use math.lgamma for normalization.
- t_cdf(t, df): two-tailed p = I_(df/(df + t^2))(df/2, 1/2) (valid for
  t^2; take |t|), one-tailed p = p_two / 2.
- f_cdf(f, df1, df2): p = I_(df2/(df2 + df1 f))(df2/2, df1/2) (right
  tail as needed).
- chi2_cdf(x, df): P(df/2, x/2).
Tests:
- t_test_1samp(data, mu0, alternative="two-sided") -> dict {stat, df,
  p, verdict}: stat = (mean - mu0) / (s / sqrt(n)); df = n - 1.
- t_test_2samp(a, b, equal_var=True) -> dict: pooled
  s_p^2 = ((n1-1)s1^2 + (n2-1)s2^2) / (n1 + n2 - 2); stat =
  (m1 - m2) / (s_p sqrt(1/n1 + 1/n2)); df = n1 + n2 - 2; Welch
  (equal_var False): Satterthwaite df.
- t_test_paired(a, b) -> dict: one-sample t on the differences d = a-b
  against 0; df = n - 1; ValueError on length mismatch.
- f_test_variances(a, b) -> dict {stat = s1^2/s2^2 (>= 1 by swapping),
  df1, df2, p two-sided, verdict}: two-sided p = 2 * min(F_cdf, 1 -
  F_cdf) capped at 1.0.
- chi2_independence(table) -> dict {stat, df, p, verdict, expected
  table}: standard (O - E)^2 / E over rows x cols; df = (r-1)(c-1);
  ValueError when any expected count < 1 (test not valid) or the table
  is not rectangular.
- anova_oneway(groups) -> dict {stat, df_between, df_within, p,
  verdict}: standard between/within sums of squares.
- all verdicts use alpha (default 0.05) as an input parameter (module
  default ALPHA = 0.05): verdict "reject-null" when p <= alpha else
  "fail-to-reject".
- summarize(results) -> dict with per-test rows and a combined note
  listing which tests reject at alpha.
ValueError on: data with < 2 points (or < 3 for variance/ANOVA),
length mismatch in paired test, zero variance in one-sample test
(after guard, allow zero with a documented degenerate verdict for the
two-sample test only when both variances are zero), non-finite values,
table with a zero row or column total, alpha outside (0, 1).

## Worked example

1. Two-sample t, equal variance, classic small samples
   a = [267.0, 261.0, 263.0, 258.0, 262.0] (drag counts, config A),
   b = [273.0, 271.0, 268.0, 275.0, 270.0] (config B): the module
   returns stat, df 8, p < 0.01 (builder runs the module and asserts
   the real outputs; also assert mean_a < mean_b and p < 0.05 so the
   verdict is reject-null: the configs differ).
2. Welch on the same data: df lower than 8, same reject verdict.
3. Paired: c = [1.0, 2.0, 1.5, 2.0, 1.8], d = [1.1, 2.1, 1.6, 2.2,
   1.9]: differences all +0.1 -> t large, reject-null at 0.05.
4. Identities: t_test_2samp equal_var on two groups of a one-way
   anova gives stat^2 == anova stat (within float tolerance), and the
   two-sided p values match (assert within 1e-9); f_test_variances on
   a and a (same data) returns stat 1.0 and p 1.0.
5. chi2_independence on the perfectly independent 2x2 table
   [[10, 20], [30, 60]] returns p 1.0 (stat 0) and verdict
   fail-to-reject; on [[15, 15], [5, 25]] p < 0.05 (assert the real
   module p and the reject verdict).
6. t_test_1samp on S = [100.0, 200.0, 300.0, 400.0, 500.0] against
   mu0 = 300 returns stat 0 and p 1.0 (fail-to-reject).
7. t_cdf cross-checks: t_cdf(0, 10) = 1.0; t_cdf(1e6, 10) ~ 0.0;
   chi2_cdf(0, 5) = 0.0.
8. ValueError on length-mismatched paired inputs and on a non-finite
   value.
Keep at least 20 test methods (special-function values, every test
family, Welch vs pooled, identities, table edge cases, verdicts,
ValueErrors).

## Corpus tasks (ids w26-hypothesis-testing-1/2)

Distinctive tokens: hypothesis testing, student t test, welch test,
paired t test, ANOVA, F test for variances, chi-square test of
independence, p-value, significance level, reject null hypothesis,
drag counts comparison, configuration difference significance. Avoid:
weibull fit / goodness of fit / KS test (probability-distributions),
control chart / SPC (manufacturing), monte carlo (sampling sibling),
linear regression (sibling).

1. "compare the measured drag counts of configuration A and B with the
   two sample t test: report the test statistic, degrees of freedom,
   p-value, and whether the difference is significant at the 0.05
   level"
2. "run the one way ANOVA across the three batches of test data and
   the chi-square test of independence on the defect contingency table,
   then return the p-values and the reject or fail to reject verdicts"

## SKILL body notes

Pair with probability-distributions (check the normality assumption
before a t test), least-squares-regression (compare fits), and the
flight test data reduction leaves that consume significance verdicts.
All p-values are computed by the module's own incomplete beta/gamma
implementations; no external statistics package. Compliance:
naca-tr-824 referenced by name only (reference-only).

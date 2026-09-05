# Wave-39 leaf spec: kruskal-wallis-test (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/kruskal-wallis-test/
- Pack: numerics. Closest siblings: rank-based-hypothesis-testing (exports
  exactly three tests: wilcoxon_rank_sum for two independent samples,
  wilcoxon_signed_rank for paired samples, sign_test; its dispatcher
  accepts only rank-sum, signed-rank and sign; its trigger fences
  two-sample rank tests), hypothesis-testing (parametric one-way ANOVA
  with the F upper tail; no rank-based k-sample analog), runs-test,
  grubbs-outlier-test, probability-distributions. Whole-tree greps at
  prep: "kruskal" = 0 hits in skills/. The k >= 3 rank-based analog of
  ANOVA is absent while the parametric ANOVA is owned (sibling asymmetry,
  same pattern class as wave-39 propeller-range). GENUINE CC gap (fresh
  probe).
- Standards id: naca-tr-824 (reference-only). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compare three or more independent groups without the normality assumption
with the Kruskal-Wallis test: merge all observations, rank them with
average ranks for ties, compute the H statistic H = (12 / (N * (N + 1))) *
sum(R_i^2 / n_i) - 3 * (N + 1), apply the ties correction
H' = H / (1 - sum((t^3 - t) / (N^3 - N))), compute the p-value from the
chi-square survival function with k - 1 degrees of freedom, and return the
verdict against a significance level. Produces H, the ties-corrected H',
the degrees of freedom, the p-value, the per-group rank sums and the
verdict that gate multi-group comparisons of non-normal data. Does NOT do:
two-sample rank tests (rank-based-hypothesis-testing); parametric ANOVA or
F tests (hypothesis-testing).

## Model (implement exactly)

Functions (pure stdlib, self-contained - no cross-leaf imports):
- rank_data(values) -> list of average ranks for ties (the rank of each
  observation within the merged sample).
- kruskal_wallis_h(groups) -> float H; ValueError if fewer than 3 groups,
  any group has fewer than 2 observations, non-finite values.
- ties_correction(groups) -> float denominator 1 - sum((t^3 - t)/(N^3 -
  N)); returns 1.0 when no ties.
- kruskal_wallis_p_value(h_corrected, group_count) -> float: survival
  probability P(chi2_(k-1) > H') via the regularized lower incomplete
  gamma; ValueError if h_corrected < 0 or group_count < 3.
- kruskal_wallis_test(groups, alpha=0.05) -> dict with keys h, h_corrected,
  df, p_value, verdict, group_rank_sums; ValueError if alpha outside
  (0, 1).
Module constants: none magic; incomplete gamma via the standard
series/continued-fraction pair.

Identity to test: all groups identical gives H = 0 and p = 1; perfect
separation of three groups of three observations gives H = 7.2 (df 2, p
0.027); a single tied pair lowers H by the ties correction denominator;
H is invariant to a monotone transform of the data (rank invariance).

## Worked example

Three groups of three: x = [2.1, 2.2, 2.3], y = [2.9, 3.0, 3.1],
z = [3.7, 3.8, 3.9]:
- merged ranks: x gets ranks 1-3 (sum 6), y ranks 4-6 (sum 15),
  z ranks 7-9 (sum 24); N = 9.
- H = (12 / 90) * (36/3 + 225/3 + 576/3) - 30 = 7.2; df = 2;
  p = 0.0273 -> reject at 0.05.
- No ties, so h_corrected = 7.2.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (direct evaluation of the H formula and the
chi-square survival function).

## Validation list (contract test must include)

- H = 7.2 within 1e-9 on the worked example; df 2; p 0.0273 within 1e-3;
  verdict reject at 0.05.
- All-identical groups: H = 0, p = 1.0, fail-to-reject.
- Ties: group values [1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4] produce ties
  and a correction factor below 1; h_corrected <= h.
- Rank invariance: multiplying every value by 10 leaves H unchanged.
- Group rank sums: x sum 6, y sum 15, z sum 24 on the worked example.
- ValueErrors: 2 groups, a group with a single observation, non-finite
  values, alpha 0 or 1.
- Determinism; report dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-kruskal-wallis-test.yaml)

Query 1 (copy verbatim):
  "run a kruskal-wallis-test comparing the surface roughness of the four coating batches without the normality assumption"
  intent: "cross-cutting; rank-based k-sample significance test"
  expected_skill: "cross-cutting/numerics/kruskal-wallis-test"
Query 2 (copy verbatim):
  "compute the kruskal wallis h-statistic and its significance for the three process temperature settings"
  intent: "cross-cutting; H statistic with ties correction"
  expected_skill: "cross-cutting/numerics/kruskal-wallis-test"
Task ids: w39-kruskal-wallis-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compare three or more independent
groups without the normality assumption:" and include the outputs in the
Claim. First tag: kruskal-wallis-test. Additional tags ONLY: h-statistic,
nonparametric-anova, rank-based-multi-group, distribution-free-k-sample.
NEVER single generic words (kruskal, wallis, rank, test, groups, medians,
nonparametric). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): wilcoxon-rank-sum-test,
mann-whitney-u-test, signed-rank, sign-test, two-sample-rank-test
(rank-based-hypothesis-testing); anova, f-test, t-test (hypothesis-
testing).

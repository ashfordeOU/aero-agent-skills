---
name: kruskal-wallis-test
description: "Use when you must compare three or more independent groups without the normality assumption: run the Kruskal-Wallis test by merging all observations, assigning average ranks for ties, computing the H statistic, applying the ties correction denominator, evaluating the p-value from the chi-square survival function with k minus 1 degrees of freedom, and returning the verdict at the chosen significance level. Produces H, the ties-corrected H, degrees of freedom, p-value, per-group rank sums and the gate verdict for non-normal group data. Trigger: kruskal wallis test, h-statistic, distribution-free k sample significance, rank-based multi-group comparison, chi-square survival p-value, coating batch roughness, process temperature settings."
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
  tags: [kruskal-wallis-test, h-statistic, nonparametric-anova, rank-based-multi-group, distribution-free-k-sample]
  version: 0.1.0
  author: Aero Agent Skills
---

# Kruskal-Wallis Test (cross-cutting/numerics/kruskal-wallis-test)

Use when the task is a distribution-free comparison of three or more
independent groups, the rank-based counterpart of the parametric
one-way location comparison: merge all observations, rank them with
average ranks for ties, form the H statistic, correct it for ties, and
convert it to a p-value through the chi-square survival function. This
leaf implements the standard Kruskal-Wallis method in pure Python,
stdlib only, with its own regularized lower incomplete gamma pair for
the chi-square survival (no sibling imports). It pairs with
cross-cutting/numerics/rank-based-hypothesis-testing, which owns paired
and two independent-group comparisons, and with
cross-cutting/numerics/hypothesis-testing, which owns the parametric
location and scale tests this leaf does not need.

## Domain quick reference

- Ranks: merge the N observations of all groups and rank the merged
  sample; equal observations share the average of the rank positions
  they occupy (average ranks for ties).
- H statistic: H = (12 / (N (N + 1))) sum_i(R_i^2 / n_i) - 3 (N + 1),
  where R_i is the sum of the ranks of group i and n_i its size. H = 0
  when all groups are identical.
- Ties correction: with tie runs of size t the denominator is C = 1 -
  sum((t^3 - t) / (N^3 - N)); C = 1.0 when there are no ties, and the
  corrected statistic is H' = H / C, so ties move H upward.
- Degrees of freedom: df = k - 1 for k groups.
- p-value: p = P(chi2_(k-1) > H'), the survival function evaluated as
  the regularized upper incomplete gamma Q(df / 2, H' / 2), computed
  with the standard series and continued-fraction pair.
- Verdict: reject when p <= alpha, fail to reject otherwise; alpha
  defaults to 0.05 and must lie in (0, 1).
- All quantities are pure floats; the module is deterministic and
  offline.
- NACA-TR-824 frames the statistical data-analysis context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Collect the groups: assemble the k >= 3 independent samples of
   finite measurements (group collection); every group needs at least
   two observations, and the significance level alpha must lie in
   (0, 1).
2. Rank the merged sample: concatenate all groups and assign average
   ranks for ties with rank_data (rank assignment step).
3. Compute the H statistic with kruskal_wallis_h, which returns the
   uncorrected H of the formula above (H statistic computation step).
4. Apply the ties correction: read the denominator C from
   ties_correction and form h_corrected = H / C (ties correction step;
   C = 1.0 leaves H unchanged).
5. Convert to significance: kruskal_wallis_p_value(h_corrected,
   group_count) evaluates the chi-square survival with df =
   group_count - 1 through the self-contained incomplete gamma pair
   (significance conversion step).
6. Read the verdict report: kruskal_wallis_test(groups, alpha) returns
   the dict with keys h, h_corrected, df, p_value, verdict and
   group_rank_sums, where verdict is reject when p_value <= alpha
   (verdict report step).
7. Confirm the deterministic checks with the contract test run:
   python3 scripts/test_kruskal_wallis_test.py (contract test step).

## Worked example

Three groups of three, x = [2.1, 2.2, 2.3], y = [2.9, 3.0, 3.1],
z = [3.7, 3.8, 3.9], alpha 0.05 (module outputs shown):

- Merged ranks: x takes ranks 1 to 3 (sum 6), y ranks 4 to 6 (sum 15),
  z ranks 7 to 9 (sum 24); N = 9, no ties.
- H = (12 / 90) (36/3 + 225/3 + 576/3) - 30 = 7.200000000000003,
  within 1e-9 of 7.2; ties_correction returns C = 1.0, so
  h_corrected = 7.200000000000003.
- df = 2; p_value = 0.027323722447292528 from the chi-square survival
  (matches exp(-3.6), the exact df-2 survival at H = 7.2).
- Verdict: reject at 0.05; group_rank_sums [6.0, 15.0, 24.0].

A tied comparison, groups [1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4]:
values 2 and 3 both recur, C = 0.9833333333333333 below 1, H =
1.4222222222222243, h_corrected = 1.4463276836158214 (H divided by C),
p_value = 0.4852146824247665, verdict fail to reject at 0.05.

## Pitfalls

- Correcting ties the wrong direction: the model divides H by C =
  1 - sum((t^3 - t) / (N^3 - N)) with C below 1 when ties exist, so
  the corrected statistic rises above the raw H; multiplying by C
  instead would understate the separation.
- Forgetting average ranks: tied observations must share the mean of
  their rank block, not arbitrary distinct integers, or H and the
  p-value drift.
- Using the leaf on designs it does not own: paired measurements and
  two independent-group comparisons belong to
  cross-cutting/numerics/rank-based-hypothesis-testing, and parametric
  location and scale tests belong to
  cross-cutting/numerics/hypothesis-testing.
- Reading a group rank sum as a mean: group_rank_sums lists the raw
  sums of average ranks per group in input order, and the sums always
  total N (N + 1) / 2 whether ties are present or not.
- Passing undersized input: fewer than 3 groups, a group with a single
  observation, non-finite values, a negative corrected statistic, or
  alpha outside (0, 1) all raise ValueError.
- Treating the p-value as exact for small samples: the p-value comes
  from the chi-square survival approximation with df = k - 1, exact
  for the worked example but asymptotic for very small group sizes.

## Verification

- Confirm kruskal_wallis_h on the worked example returns
  7.200000000000003, within 1e-9 of 7.2, and kruskal_wallis_test
  returns df 2, p_value 0.027323722447292528 (within 1e-3 of 0.0273),
  verdict reject at 0.05 and group_rank_sums [6.0, 15.0, 24.0].
- Confirm all-identical groups return H = 0.0, p_value 1.0 and verdict
  fail to reject, with the zero correction denominator handled.
- Confirm the tied example gives C = 0.9833333333333333 below 1 and
  h_corrected = h / C above the raw H.
- Confirm rank invariance: multiplying every observation by 10 leaves
  H unchanged because only the rank assignment feeds the statistic.
- Confirm every undersized, non-finite and out-of-range input raises
  ValueError, and that repeated calls return identical reports.
- Run the contract test offline: python3
  scripts/test_kruskal_wallis_test.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/rank-based-hypothesis-testing: paired and two
  independent-group location tests, the k = 2 family this leaf does
  not cover.
- cross-cutting/numerics/hypothesis-testing: the parametric one-way
  location comparison and scale tests for normal data.
- cross-cutting/numerics/runs-test: randomness and sequence structure
  checks on a single sample.
- cross-cutting/numerics/grubbs-outlier-test: single-outlier detection
  on grouped or pooled measurements.
- cross-cutting/numerics/probability-distributions: the distributions
  behind the survival-function context.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_kruskal_wallis_test.py

The test covers the worked-example contract (H within 1e-9 of 7.2,
df 2, p_value 0.027323722447292528 within 1e-3 of 0.0273, verdict
reject at 0.05, per-group rank sums 6, 15, 24), the chi-square survival
anchor exp(-3.6) at df 2, average-rank assignment for ties, the ties
correction denominator and the h_corrected = H / C identity,
all-identical groups with H = 0 and p = 1, rank invariance under
monotone transforms, the rank-sum total identity N (N + 1) / 2, report
dict keys and determinism, and ValueError rejection of two groups, a
single-observation group, non-finite values, negative corrected
statistics, and alpha outside (0, 1).

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 is a public-domain
  NACA technical report; the Kruskal-Wallis relations above are
  standard engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

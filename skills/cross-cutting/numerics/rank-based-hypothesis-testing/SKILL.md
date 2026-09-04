---
name: rank-based-hypothesis-testing
description: "Use when you must compare two samples without relying on the normality assumption: run the Wilcoxon rank-sum test (Mann-Whitney U) on two independent samples, the Wilcoxon signed-rank test and the sign test on paired measurements, using average ranks for ties, exact rank sums, the normal approximation z with the 0.5 continuity correction toward zero, the two-sided p-value from the standard normal CDF, and the reject or accept verdict at a chosen alpha. Produces the test statistic, z, p-value and verdict that remain valid when the normality assumption of the parametric sibling fails. Trigger: wilcoxon rank sum test, mann-whitney u test, wilcoxon signed rank test, sign test, nonparametric paired comparison, two sample rank test, continuity correction, distribution-free location test."
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
  tags: [rank-based-hypothesis-testing, wilcoxon-rank-sum-test, mann-whitney-u-test, wilcoxon-signed-rank-test, sign-test, normality-free-comparison, two-sample-rank-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rank-Based Hypothesis Testing (cross-cutting/numerics/rank-based-hypothesis-testing)

Use when the task is a distribution-free location comparison that must
stay valid when the normality assumption of the parametric sibling
fails: the Wilcoxon rank-sum test (Mann-Whitney U) for two independent
samples, the Wilcoxon signed-rank test and the sign test for paired
data. This leaf ranks the observations, applies the normal
approximation with the 0.5 continuity correction toward zero, and
returns the statistic, z, two-sided p-value and the reject or accept
verdict at the chosen alpha. It pairs with
cross-cutting/numerics/hypothesis-testing, which owns the parametric
family of location and scale tests, and with the distribution and
descriptive-moment context leaves.

## Domain quick reference

- Rank-sum (Mann-Whitney U): merge the samples, rank all observations
  with average ranks for ties, R1 = sum of ranks of sample 1.
  U = R1 - n1 (n1 + 1) / 2 (the other orientation is n1 n2 +
  n1 (n1 + 1) / 2 - R1; sample 1 is the x sample here).
  Mean mu_U = n1 n2 / 2, sd_U = sqrt(n1 n2 (n1 + n2 + 1) / 12),
  z = (U - mu_U +/- 0.5) / sd_U with the correction toward zero.
- Signed-rank (paired): differences d_i = x_i - y_i, zeros dropped,
  absolute differences ranked with average ranks for ties. W = sum of
  positive-difference ranks minus sum of negative-difference ranks.
  mu_W = 0, sd_W = sqrt(n (n + 1) (2 n + 1) / 6), z = (W -
  sign(W) * 0.5) / sd_W.
- Sign test (paired): n+ = positive differences among n nonzero ones;
  z = (n+ - n/2 +/- 0.5) / sqrt(n/4) with the correction toward zero.
- Two-sided p = 2 (1 - Phi(|z|)) with Phi(z) = 0.5 (1 + erf(z /
  sqrt(2))) from math.erf; verdict reject when p <= alpha.
- Default alpha 0.05; pure stdlib, deterministic, offline.

## Workflow

1. Decide the design: two independent samples (wilcoxon_rank_sum) or
   paired measurements (wilcoxon_signed_rank for magnitudes with
   signs, sign_test for signs only).
2. Pick alpha (default 0.05, must lie in (0, 1)).
3. Call the chosen function on the raw samples; every function returns
   a dict with the exact keys of the spec.
4. Read z and p_value for the effect direction and size, reject for
   the verdict.
5. For a uniform report use rank_test_summary("rank-sum" |
   "signed-rank" | "sign", x, y, alpha), which dispatches to the same
   three functions.
6. Confirm the deterministic checks with the contract test
   scripts/test_rank_based_hypothesis_testing.py.

## Worked example

Finish-roughness batches x = [0.82, 0.79, 0.85, 0.80, 0.83] vs y =
[0.96, 1.02, 0.94, 0.98, 0.99], alpha 0.05: the x values occupy the
five lowest merged ranks, so wilcoxon_rank_sum returns r1 = 15.0,
u = 0.0, mu_u = 12.5, sd_u = 4.7871, z = -2.5067, p_value = 0.01219,
reject True.

Paired series (1.0, 1.1) to (6.0, 6.6) with all differences negative:
wilcoxon_signed_rank returns n = 6, w = -21.0, sd_w = 9.5394 (sqrt of
6 * 7 * 13 / 6), z = -2.1490, p_value = 0.03164, reject True at 0.05.

Sign test with 8 positive of 10 differences: sign_test returns
n_pos = 8, n_neg = 2, n = 10, z = 1.5811, p_value = 0.11385, reject
False. With 10 of 10 positive it returns z = 2.8461, p_value =
0.00443, reject True (the continuity-corrected approximation region
hand checks to z near 3 and p near 0.003).

## Verification

- Confirm wilcoxon_rank_sum(x, y) above returns r1 15.0, u 0.0,
  z -2.5067, p 0.01219 and reject True; swapping the samples mirrors z
  positive with the same p.
- Confirm identical samples return u = n1 n2 / 2, z = 0.0 and
  p = 1.0 within 1e-6, reject False; symmetric paired data give
  w = 0.0, p = 1.0.
- Confirm tied values share average ranks: [1, 2, 3] vs [1, 2, 3] and
  the tied-magnitude signed-rank case both return the averaged
  statistics.
- Confirm every non-physical input raises ValueError: fewer than 2
  observations per rank-sum sample, alpha outside (0, 1), paired
  length mismatch, fewer than 2 nonzero signed-rank differences, no
  nonzero sign-test differences, and an unknown test name in
  rank_test_summary.
- Run the contract test offline: python3
  scripts/test_rank_based_hypothesis_testing.py (33 tests,
  deterministic).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the parametric sibling
  (boundary: parametric location tests against this leaf's
  distribution-free ranks).
- cross-cutting/numerics/descriptive-statistics: moments and ordering
  context for the samples being compared.
- cross-cutting/numerics/probability-distributions: normal CDF and
  quantile context for the approximation used here.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rank_based_hypothesis_testing.py

The test covers the worked-example anchors for all three tests
(rank-sum r1 15.0 / u 0.0 / z -2.5067 / p 0.01219; signed-rank
w -21.0 / z -2.1490 / p 0.03164; sign test z 1.5811 / p 0.11385),
reversed and all-positive/all-negative rejection directions, the
identical-sample and symmetric-pair identities (z 0, p 1), average-rank
tie handling, zero-difference dropping, exact dict keys, run-to-run
determinism, dispatch via rank_test_summary, and ValueError rejection
of every non-physical input listed in Verification.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named as the
  numerics-pack reference; the rank procedures above are standard
  statistical methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

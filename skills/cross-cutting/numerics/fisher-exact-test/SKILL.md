---
name: fisher-exact-test
description: "Use when you must test a 2x2 contingency table with small expected counts: run the exact Fisher test under the fixed-margin null, compute the hypergeometric probability of the observed table, enumerate every table with the same margins, sum the one-tailed and two-tailed exact p-values, compute the odds ratio with the Haldane-Anscombe zero-cell correction, and return the small-expected-count verdict that recommends the exact test over the large-sample approximation. Produces p_obs, p_one_tail, p_two_tail, direction, odds ratio and the verdict. Trigger: fisher exact test, 2x2 contingency table, hypergeometric tail probability, small expected count, two by two table, odds ratio, exact independence test."
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
  tags: [fisher-exact-test, two-by-two-contingency, hypergeometric-exact-p, small-expected-count, exact-independence-test, odds-ratio]
  version: 0.1.0
  author: AeroSkills
---

# Fisher Exact Test (cross-cutting/numerics/fisher-exact-test)

Use when you must test a 2x2 contingency table whose expected cell
counts are small (below 5), where the large-sample approximation is
unreliable: the exact Fisher test conditions on the fixed row and
column margins and works directly from the hypergeometric distribution
of the top-left cell, so the p-values are exact at any sample size.
This leaf computes the observed table probability, enumerates every
table with the same margins, sums the one-tailed and two-tailed exact
p-values, forms the odds ratio with the Haldane-Anscombe zero-cell
correction, and returns the small-expected-count verdict that gates the
independence conclusion. Pure Python stdlib (math.comb), offline and
deterministic. It pairs with cross-cutting/numerics/hypothesis-testing
for the large-sample verdict on the same tables and with
cross-cutting/numerics/probability-distributions for the hypergeometric
family context.

## Domain quick reference

- Convention: table [[a, b], [c, d]] with row margins a+b and c+d,
  column margins a+c and b+d and total n = a+b+c+d. Under the fixed-
  margin null the top-left count follows the hypergeometric
  distribution: P(a) = C(a+b, a) * C(c+d, c) / C(n, a+c), with
  C = math.comb.
- Enumeration: every table with the same margins has a top-left count
  a' in [max(0, (a+c) - (c+d)), min(a+b, a+c)]; the worked example has
  seven feasible tables, a' = 1..7, and their probabilities sum to 1.
- Direction and one-tailed p: direction is "low" when the odds ratio
  is below 1 (small top-left counts are the more extreme direction),
  "high" when above 1, "symmetric" when equal to 1. p_one_tail sums
  table probabilities with a' <= a_obs (low), a' >= a_obs (high), and
  the common sum in the symmetric case.
- Two-tailed p: p_two_tail sums every table probability <= p_obs (the
  documented two-sided definition), so it is always >= p_one_tail.
- Odds ratio: (a*d) / (b*c); a zero cell makes the raw ratio 0 or
  infinite, so any zero cell triggers the Haldane-Anscombe correction,
  +0.5 added to every cell before forming the ratio.
- Small-count verdict: the minimum expected cell count under
  independence is min over the four cells of row_total * col_total / n;
  below 5 the verdict is "exact-test-recommended", otherwise
  "chi-square-adequate".
- NACA-TR-824 is the numerics sibling standards reference; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Arrange the two groups and two outcomes as a 2x2 table
   [[a, b], [c, d]] with non-negative integer counts and confirm the
   margins (a+b, c+d) and (a+c, b+d).
2. Get the probability of the observed table under the null with
   hypergeometric_p(a, b, c, d); this is p_obs.
3. See how many tables the margins admit with enumerate_tables(a, b,
   c, d): the a' values and the margin-preserving tuples.
4. Run the exact test with fisher_exact_p_value(a, b, c, d): read the
   dict {p_obs, p_one_tail, p_two_tail, direction} and use p_two_tail
   for the two-sided significance conclusion, or p_one_tail for a
   directional claim on the side the odds ratio points to.
5. Quantify the association with odds_ratio(a, b, c, d); the
   Haldane-Anscombe correction keeps zero-cell tables finite.
6. Gate the method choice with small_count_verdict(a, b, c, d): when
   the minimum expected cell count is below 5, report the exact
   p-values rather than the large-sample approximation.
7. Confirm the deterministic checks with the contract test
   scripts/test_fisher_exact_test.py.

## Worked example

Table [[2, 6], [5, 1]] (row margins 8 and 6, column margins 7 and 7,
n = 14), the wave-38 anchor:

- hypergeometric_p(2, 6, 5, 1) = 0.048951, the observed table
  probability (168 / 3432 = 28 * 6 / C(14, 7)).
- enumerate_tables(2, 6, 5, 1) returns 7 tables with a' = 1..7 and
  preserved margins; the full probability mass sums to 1.0.
- fisher_exact_p_value(2, 6, 5, 1) returns p_obs 0.048951, direction
  "low" (odds ratio 0.0667 < 1), p_one_tail = P(a' <= 2) = 0.051282
  (0.002331 + 0.048951) and p_two_tail = 0.102564, the sum of the four
  tables with probability <= p_obs (a' in {1, 2, 6, 7}).
- odds_ratio(2, 6, 5, 1) = 0.066667 = 2/30, no zero cells so the raw
  ratio stands.
- small_count_verdict(2, 6, 5, 1) reports min_expected 3.0 (the
  bottom-row cells carry 6*7/14 = 3.0, the smallest of the four; the
  top row carries 8*7/14 = 4.0) and verdict "exact-test-recommended".
- The identity table [[2, 2], [2, 2]] gives odds ratio 1.0 and
  direction "symmetric", with p_one_tail 0.757143 (53/70) and both
  tail directions equal.

## Verification

- Confirm hypergeometric_p(2, 6, 5, 1) returns 0.048951 and that the
  seven-table probability mass sums to 1.0.
- Confirm fisher_exact_p_value(2, 6, 5, 1) returns p_one_tail 0.051282
  and p_two_tail 0.102564 within 1e-4, direction "low", and that the
  mirrored table [[6, 2], [1, 5]] gives direction "high" with the same
  p-values.
- Confirm odds_ratio(2, 6, 5, 1) returns 0.066667, the identity table
  [[2, 2], [2, 2]] returns 1.0, and zero-cell tables return the
  Haldane-Anscombe corrected value.
- Confirm small_count_verdict(2, 6, 5, 1) returns min_expected 3.0
  with verdict "exact-test-recommended", while a large-count table
  such as [[40, 60], [60, 40]] returns "chi-square-adequate".
- Confirm p_two_tail >= p_one_tail across a spread of tables, and that
  a table at the extreme end of its direction has p_one_tail == p_obs.
- Confirm every negative cell raises ValueError from each function and
  that a non-positive table total raises ValueError from
  small_count_verdict.
- Run the contract test offline: python3
  scripts/test_fisher_exact_test.py (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the large-sample
  independence test for tables whose expected counts are not small,
  the complement verdict layer for the same 2x2 data.
- cross-cutting/numerics/probability-distributions: the hypergeometric
  family behind the exact p-values and its moments.
- cross-cutting/numerics/rank-based-hypothesis-testing: distribution-
  free alternatives for ordinal and non-normal comparisons.
- cross-cutting/numerics/grubbs-outlier-test: exact small-sample
  reasoning applied to outlier detection rather than tables.
- cross-cutting/numerics/proportion-confidence-interval: attribute-
  data rate bounds at a stated confidence level, the estimation side
  of the same pass-fail data.

## Pitfalls

- Doubling the one-tailed p for a two-sided test: the documented
  two-sided definition sums every table probability <= p_obs (0.102564
  in the worked example); twice the one-tailed p is a different,
  conservative convention and can disagree with this value.
- Trusting the large-sample verdict near 5: min_expected < 5 means the
  exact test is recommended, and the threshold sits exactly at the
  boundary of common textbook guidance; report the exact p-values when
  the verdict says so.
- Letting a zero cell collapse the odds ratio: the raw (a*d)/(b*c)
  becomes 0 or division by zero; apply the +0.5-per-cell Haldane-
  Anscombe correction and report that the correction was used.
- Summing the one-tailed p on the wrong side: direction is read from
  the odds ratio (low means small a' is the extreme side), so a
  directional claim must sum a' <= a_obs or a' >= a_obs accordingly;
  the data decide the side, not the label of the claim.
- Quoting p_obs as the significance: p_obs (0.048951) is the mass of
  one table only and understates the evidence; the significance
  conclusion uses p_two_tail (0.102564) against the level.
- Reading the minimum expected count from the top row only: with
  unequal row margins the smallest expected cell can sit in the other
  row (6*7/14 = 3.0, not the top-row 8*7/14 = 4.0); take the minimum
  over all four cells.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fisher_exact_test.py

The test covers the worked-example anchors (p_obs 0.048951, one-tailed
p 0.051282, two-tailed p 0.102564, odds ratio 0.066667, seven tables
with a' = 1..7, minimum expected count 3.0 with the exact-test-
recommended verdict), the large-count chi-square-adequate verdict, the
symmetric identity table with odds ratio 1.0, high- and low-direction
tails on mirrored tables, the p_two_tail >= p_one_tail ordering across
tables, the extreme-table identity p_one_tail == p_obs in both
directions, the documented two-tailed selection rule, exact dict keys,
the Haldane-Anscombe zero-cell corrections, alternative value
validation, and ValueError rejection of negative cells and non-positive
totals.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 is the numerics
  pack reference standard; the hypergeometric and odds-ratio relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

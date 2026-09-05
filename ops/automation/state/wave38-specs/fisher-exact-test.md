# Wave-38 leaf spec: fisher-exact-test (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/fisher-exact-test/
- Pack: numerics. Closest siblings: hypothesis-testing (chi-square test
  of independence for 2x2 and larger contingency tables - the LARGE-SAMPLE
  approximation; its claim has zero exact/hypergeometric content),
  rank-based-hypothesis-testing, runs-test, grubbs-outlier-test, gage-rr-
  anova, proportion-confidence-interval (wave-38 sibling), probability-
  distributions. Whole-tree grep: "fisher exact", "hypergeometric
  tail", "2x2 table" = ZERO owning hits (hypothesis-testing owns chi-
  square independence only). ZERO owners of the exact small-sample
  contingency test. GENUINE CC gap (fresh probe; weakest-accepted tier,
  disclosed - same tier as wave-37 grubbs/gage-rr).
- Standards id: naca-tr-824 (reference-only; numerics sibling convention).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Run the exact Fisher test on a 2x2 contingency table when expected counts
are small: compute the hypergeometric probability of the observed table
under the fixed-margin null, enumerate all tables with the same margins,
sum the one-tailed and two-tailed exact p-values, compute the odds ratio,
and return the independence verdict against the chi-square large-sample
approximation. Produces the observed table probability, the one- and
two-tailed p-values, the odds ratio, and the small-count verdict that gate
the significance conclusion. Does NOT do: chi-square test of independence
(hypothesis-testing); proportion confidence intervals (proportion-
confidence-interval).

## Model (implement exactly)

Conventions: a 2x2 table [[a, b], [c, d]] with fixed row and column
margins. Under the null the count in the top-left cell follows the
hypergeometric distribution: P(a) = C(a+b, a) * C(c+d, c) / C(n, a+c)
with n = a+b+c+d (C = math.comb).

Functions (pure stdlib):
- hypergeometric_p(a, b, c, d) -> float.
- enumerate_tables(a, b, c, d) -> list of (a', b', c', d') with the same
  margins (a' from max(0, a+c - (c+d)) to min(a+b, a+c)).
- fisher_exact_p_value(a, b, c, d, alternative="two-sided") -> dict
  {p_obs, p_one_tail, p_two_tail, direction}: p_obs is the probability of
  the observed table; direction is "low" when the observed odds ratio < 1
  (small top-left count is the more extreme direction) and "high" when the
  odds ratio > 1; p_one_tail sums table probabilities with a' <= a_obs
  (low direction) or a' >= a_obs (high direction); when the odds ratio
  equals 1 both directions give the same sum and direction is "symmetric";
  p_two_tail sums all table probabilities <= p_obs (the documented
  two-sided definition). ValueErrors: any negative cell.
- odds_ratio(a, b, c, d) -> float: (a*d)/(b*c); handle a zero cell by
  the Haldane-Anscombe correction (+0.5 to every cell, documented).
- small_count_verdict(a, b, c, d) -> dict {min_expected, verdict}:
  min expected cell count under independence; verdict "exact-test-
  recommended" when min_expected < 5 else "chi-square-adequate".
  ValueError: non-positive n.
Identity to test: p_obs of the observed table is 1.0 when the table is
the most extreme possible in its direction; the two-tailed p is >= the
one-tailed p; odds_ratio of a table with b*c = a*d is 1.0.

## Worked example

Verified at prep: table [[2, 6], [5, 1]] (row margins 8 and 6, column
margins 7 and 7, n = 14):
- p_obs = 0.048951.
- Direction: odds ratio 0.0667 < 1 -> "low"; p_one_tail = P(a' <= 2) =
  0.048951 + 0.002331 = 0.051282.
- p_two_tail (all tables with probability <= p_obs) = 0.1025641.
- odds_ratio = (2*1)/(6*5) = 0.06667 (raw); corrected (Haldane) with the
  zero-cell adjustment documented.
- min expected count = (7*8)/14 = 4.0 -> verdict
  "exact-test-recommended" (below 5).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the hypergeometric enumeration
(independently evaluated by the anchor script at prep). Note: the
two-tailed definition (sum all table probabilities <= p_obs) is the
documented model; assert that definition.

## Validation list (contract test must include)

- hypergeometric_p on the worked example = 0.048951 within 1e-6.
- enumerate_tables on the worked example produces exactly the feasible
  a' values (a' = 1..7, 7 tables; assert the count and the margin
  preservation).
- one-tailed p 0.051282 within 1e-4; two-tailed p 0.102564 within 1e-4.
- odds_ratio = 0.06667 within 1e-4; the identity table [[2,2],[2,2]]
  gives odds ratio 1.0.
- min expected count 4.0 -> exact-test-recommended.
- A large-count table (e.g. [[40, 60], [60, 40]]) gives the chi-square-
  adequate verdict.
- ValueErrors: negative cells.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave38-fisher-exact-test.yaml)

Query 1 (copy verbatim):
  "run the fisher-exact-test on a 2x2 contingency table whose expected count is below 5 and report the exact two-tailed p-value"
  intent: "cross-cutting; exact small-sample contingency test"
  expected_skill: "cross-cutting/numerics/fisher-exact-test"
Query 2 (copy verbatim):
  "compute the hypergeometric-tail-probability and odds ratio for a two-by-two table with fixed margins"
  intent: "cross-cutting; hypergeometric exact probability and odds ratio"
  expected_skill: "cross-cutting/numerics/fisher-exact-test"
Task ids: w38-fisher-exact-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must test a 2x2 contingency table with
small expected counts:" and include the outputs in the Claim. First tag:
fisher-exact-test. Additional tags ONLY: two-by-two-contingency,
hypergeometric-exact-p, small-expected-count, exact-independence-test,
odds-ratio. NEVER single generic words (fisher, exact, table, test,
contingency, p-value). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): chi-square test of independence,
chi-square statistic (hypothesis-testing); proportion interval (proportion-
confidence-interval).

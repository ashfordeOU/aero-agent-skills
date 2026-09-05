# Wave-39 leaf spec: exact-binomial-test (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/exact-binomial-test/
- Pack: numerics. Closest siblings: proportion-confidence-interval
  (Wilson and Clopper-Pearson INTERVALS for an observed proportion - tail
  inversion, not a hypothesis test against a null p0), rank-based-
  hypothesis-testing (its sign_test is paired data and uses the binomial
  NORMAL APPROXIMATION with a continuity correction, no exact binomial
  tail), hypothesis-testing, fisher-exact-test (needs a 2 x 2 table with
  two samples). Whole-tree greps at prep: a significance test of an
  observed k-of-n count against a hypothesized p0 with the exact binomial
  tail = 0 owners. GENUINE CC gap (fresh probe).
- Standards id: naca-tr-824 (reference-only). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Test an observed count against a hypothesized proportion with the exact
binomial distribution: compute the probability of k or fewer successes in
n trials under the null p0 with P(X <= k) = sum of the binomial tail
terms, form the exact two-sided p-value as the sum of the lower and upper
tail masses (with the documented doubling or symmetric-tail convention)
plus an optional mid-p variant, and provide the normal approximation with
the continuity correction as a large-sample cross-check. Produces the
exact p-value, the one-sided and two-sided verdicts against a
significance level, and the small-count recommendation that gate
attribute-data significance claims. Does NOT do: confidence intervals for
a proportion (proportion-confidence-interval); paired sign tests
(rank-based-hypothesis-testing); 2 x 2 contingency exact tests
(fisher-exact-test).

## Model (implement exactly)

Functions (pure stdlib, self-contained - no cross-leaf imports):
- binomial_probability(k, n, p) -> C(n, k) * p^k * (1-p)^(n-k) via
  math.comb; ValueError if k outside [0, n] or not an integer, n < 1,
  p outside (0, 1).
- binomial_cdf(k, n, p) -> P(X <= k) = sum of binomial_probability over
  0..k.
- binomial_exact_test(k, n, p0, alternative="two-sided",
  midp=False) -> dict with keys p_lower_tail, p_upper_tail, p_value,
  direction, midp_applied: the one-sided p in the observed direction, the
  two-sided p as the doubled one-sided mass capped at 1 (documented
  convention, mirroring the sign-test family) and the mid-p variant
  p_mid = p_two_sided - p_obs when midp is True. ValueError if k outside
  [0, n] or not an integer, p0 outside (0, 1), alternative not in
  ("two-sided", "less", "greater").
- binomial_normal_approximation(k, n, p0) -> dict with keys z, p_value
  (two-sided): z = (k - n*p0 - 0.5*correction) / sqrt(n*p0*(1-p0)) with
  the continuity correction applied toward the null mean.
- small_count_recommendation(n, p0) -> dict with keys min_expected,
  verdict: min_expected = n * min(p0, 1 - p0);
  verdict "exact-test-recommended" when min_expected < 5 else
  "normal-approximation-adequate".
Module constants: none magic.

Identity to test: p0 = 0.5 with k = n/2 gives the largest p-value; the
two-sided p is at least the one-sided p and at most 1; the normal
approximation approaches the exact p as n grows; the CDF at k = n is 1.

## Worked example

n = 40, k = 8, p0 = 0.30:
- P(X <= 8) = 0.1110 (exact binomial lower tail).
- Direction less; two-sided p = 2 * 0.1110 = 0.2220 (capped at 1);
  fail-to-reject at 0.05.
n = 20, k = 2, p0 = 0.30:
- P(X <= 2) = 0.0355; one-sided less rejects at 0.05.
Normal cross-check on n = 40, k = 8, p0 = 0.3: mean 12, sd 2.898,
z = (8 - 12 + 0.5)/2.898 = -1.208, two-sided p = 0.227.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (the binomial tail sums and the normal
approximation were independently evaluated at prep).

## Validation list (contract test must include)

- binomial_cdf(8, 40, 0.3) = 0.1110 within 1e-3; p_two_sided 0.2220
  within 2e-3, fail-to-reject at 0.05.
- binomial_cdf(2, 20, 0.3) = 0.0355 within 1e-3; less alternative
  rejects at 0.05.
- Normal approximation z = -1.208 within 0.01 and p 0.227 within 0.005.
- p0 = 0.5, n = 10, k = 5: p_two_sided = 1.0 (most central count).
- cdf at k = n equals 1.0; binomial_probability sums to 1 over k.
- small_count_recommendation: n = 20, p0 = 0.3 -> min_expected 6,
  adequate; n = 10, p0 = 0.05 -> min_expected 0.5,
  exact-test-recommended.
- ValueErrors: k 41 with n 40, k 2.5, n 0, p0 0 or 1, bad alternative.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave39-exact-binomial-test.yaml)

Query 1 (copy verbatim):
  "run the exact binomial test whether the eight successes in forty trials support the pass rate of zero point three"
  intent: "cross-cutting; exact binomial significance of k of n against p zero"
  expected_skill: "cross-cutting/numerics/exact-binomial-test"
Query 2 (copy verbatim):
  "binomial significance test of the observed defect fraction against the hypothesized p zero with the exact tail probability"
  intent: "cross-cutting; binomial tail p-value for a single proportion"
  expected_skill: "cross-cutting/numerics/exact-binomial-test"
Task ids: w39-exact-binomial-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must test an observed count against a
hypothesized proportion:" and include the outputs in the Claim. First
tag: exact-binomial-test. Additional tags ONLY: single-proportion-test,
binomial-tail-p-value, k-of-n-significance, mid-p-binomial. NEVER single
generic words (binomial, exact, test, proportion, count, significance).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): clopper-pearson-interval,
wilson-score-interval, confidence-interval (proportion-confidence-
interval); sign-test, paired (rank-based-hypothesis-testing);
fisher-exact-test, 2x2-contingency; chi-square.

---
name: exact-binomial-test
description: "Use when you must test an observed count against a hypothesized proportion: compute the exact binomial tail probability of k or fewer successes in n trials under a null proportion p zero, form the two-sided p-value by doubling the one-sided tail mass capped at one with an optional mid-p variant and a continuity-corrected normal cross-check, and decide the verdict against a significance level. Produces the exact p-value, the lower and upper tail masses, the observed direction, and the small-count recommendation that gate attribute-data significance claims. Trigger: exact binomial test, binomial tail probability, k of n successes, single proportion significance, mid p correction, attribute data significance."
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
  tags: [exact-binomial-test, single-proportion-test, binomial-tail-p-value, k-of-n-significance, mid-p-binomial]
  version: 0.1.0
  author: AeroSkills
---

# Exact Binomial Test (cross-cutting/numerics/exact-binomial-test)

Use when the task is a significance test of an observed count against a
hypothesized proportion: does k successes in n trials support a null pass
rate or defect rate p zero? This leaf computes the exact binomial tail
P(X <= k) under the null, forms the one-sided and two-sided p-values with
the documented doubling convention (capped at one) plus the optional mid-p
variant, cross-checks with the normal approximation carrying the
continuity correction, and returns the small-count recommendation that
gates attribute-data significance claims. It is pure Python, stdlib only
(math.comb, math.erfc), deterministic, with no RNG. It pairs with the
sibling numerics leaves: interval estimation of the same proportion is
cross-cutting/numerics/proportion-confidence-interval, parametric verdicts
on continuous samples are cross-cutting/numerics/hypothesis-testing, and
two-sample table tests are cross-cutting/numerics/fisher-exact-test.

## Domain quick reference

- Single-outcome mass: P(X = k) = C(n, k) * p0^k * (1 - p0)^(n - k),
  computed with math.comb (binomial_probability).
- Lower tail: P(X <= k) = sum over j = 0..k of C(n, j) * p0^j *
  (1 - p0)^(n - j) (binomial_cdf), exactly 1.0 when k equals n.
- Observed direction: "less" when k sits at or below the null mean n*p0,
  "greater" otherwise.
- One-sided p-value: the lower tail for the less alternative, the upper
  tail P(X >= k) = 1 - P(X <= k - 1) for the greater alternative.
- Two-sided p-value: the observed-direction one-sided mass doubled and
  capped at 1, the doubling convention shared with the nonparametric
  two-sided family; any one-sided mass at or above one half therefore
  reports exactly 1.0.
- Mid-p variant: p_mid = p_two_sided - P(X = k) for the two-sided case,
  and the one-sided p minus half of P(X = k) for a one-sided case, the
  standard relaxation of the conservative doubling (assumption recorded
  here; the module applies it only when midp is True).
- Normal cross-check: mean n*p0, standard deviation sqrt(n*p0*(1 - p0)),
  continuity correction moving the count half a step toward the null mean
  (k + 0.5 below the mean, k - 0.5 above), z = (k_c - mean) / sd, and the
  two-sided normal p = 2 * (1 - Phi(|z|)) from math.erfc.
- Small-count rule: min_expected = n * min(p0, 1 - p0); below 5 the
  verdict is exact-test-recommended, otherwise
  normal-approximation-adequate.
- Identities: p0 = 0.5 with k = n/2 is the most central count and gives a
  two-sided p of exactly 1.0; the CDF at k = n is 1.0; the masses sum to 1
  over k; the normal approximation approaches the exact p as n grows.

## Workflow

1. Fix the inputs: observed successes k, trial count n, hypothesized null
   proportion p0, the alternative (two-sided, less or greater) and the
   significance level alpha (0.05 by default).
2. Tail-mass traverse: binomial_probability returns the single-outcome
   mass P(X = k) and binomial_cdf returns the cumulative lower tail
   P(X <= k).
3. Exact-test traverse: binomial_exact_test(k, n, p0, alternative)
   returns the verdict dict with the exact keys p_lower_tail, p_upper_tail,
   p_value, direction and midp_applied, the two-sided p_value doubling the
   observed-direction one-sided mass and capping at 1.
4. Mid-p traverse: rerun binomial_exact_test with midp True to relax the
   conservative doubling by the probability of the observed count.
5. Normal cross-check traverse: binomial_normal_approximation(k, n, p0)
   returns the dict with z (continuity correction toward the null mean)
   and the two-sided normal p_value for large samples.
6. Small-count traverse: small_count_recommendation(n, p0) returns
   min_expected and the verdict that gates the exact tail against the
   approximation for attribute data.
7. Verdict bookkeeping: compare the p_value against alpha and record
   reject or fail-to-reject at the chosen significance level.
8. Verification run: confirm the anchors and guards with the contract
   test, python3 scripts/test_exact_binomial_test.py (35 tests,
   deterministic, offline).

## Worked example

n = 40, k = 8, p0 = 0.30. Module outputs (contract test anchors in
parentheses):

- Lower tail: binomial_cdf(8, 40, 0.3) = 0.11100917524979735 (within 1e-3
  of 0.1110).
- Exact test: p_lower_tail 0.11100917524979735, p_upper_tail
  0.9447171128462573, p_value 0.2220183504995947 (within 2e-3 of 0.2220),
  direction less, fail-to-reject at the 0.05 significance level; the
  two-sided p is exactly twice the 0.1110 lower tail, uncapped.
- Mid-p variant: 0.1662920624035401, the doubled 0.2220 minus the observed
  mass P(X = 8) = 0.0557262880960546.
- Normal cross-check: mean 12, sd sqrt(8.4) = 2.898275, z =
  (8 - 12 + 0.5) / 2.898275 = -1.20761472884912 (within 0.01 of -1.208),
  two-sided p 0.22719549110006437 (within 0.005 of 0.227).
- n = 20, k = 2, p0 = 0.30: binomial_cdf(2, 20, 0.3) =
  0.03548313229846864 (within 1e-3 of 0.0355) and the less alternative
  p_value rejects at 0.05.
- Upper-side example: n = 40, k = 16 sits above the null mean 12, so the
  direction is greater, the upper tail is 0.11514665058139029 and the
  doubled two-sided p_value is 0.23029330116278057.
- Small count: n = 20, p0 = 0.30 gives min_expected 6.0 and
  normal-approximation-adequate; n = 10, p0 = 0.05 gives min_expected 0.5
  and exact-test-recommended.

## Verification

- Confirm binomial_cdf(8, 40, 0.3) returns 0.11100917524979735 and
  binomial_exact_test(8, 40, 0.3) returns p_value 0.2220183504995947 with
  direction less, failing to reject at 0.05.
- Confirm binomial_exact_test(2, 20, 0.3, alternative="less") rejects at
  0.05 with p_value 0.03548313229846864.
- Confirm binomial_normal_approximation(8, 40, 0.3) returns z
  -1.20761472884912 and p_value 0.22719549110006437.
- Confirm the most central count p0 = 0.5, n = 10, k = 5 gives a two-sided
  p_value of exactly 1.0, and the mid-p variant 0.75390625.
- Confirm binomial_cdf(k = n) returns exactly 1.0 and the
  binomial_probability masses sum to 1 over k.
- Confirm small_count_recommendation(20, 0.3) returns min_expected 6.0
  with the adequate verdict and small_count_recommendation(10, 0.05)
  returns 0.5 with exact-test-recommended.
- Confirm the normal approximation error at n = 400 is below half the
  error at n = 40 for the same count share (convergence with n).
- Confirm every non-physical input raises ValueError: k 41 with n 40, k
  -1, k 2.5, n 0, a fractional n, p0 or p exactly 0 or 1, p outside
  (0, 1), and an alternative outside two-sided, less and greater.
- Run the contract test offline: python3 scripts/test_exact_binomial_test.py
  (35 tests, deterministic).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the verdict workflow for
  continuous-sample comparisons without an exact count tail.
- cross-cutting/numerics/proportion-confidence-interval: interval
  estimation for a proportion, the estimation counterpart of this test.
- cross-cutting/numerics/rank-based-hypothesis-testing: nonparametric
  alternatives that rank the observations instead of counting successes.
- cross-cutting/numerics/fisher-exact-test: exact tests on contingency
  tables built from two samples, with no single-count null-proportion
  input.

## Pitfalls

- Running the normal approximation on small expected counts: when
  min_expected falls below 5 the exact tail is required; run the
  small-count traverse first and honor the exact-test-recommended verdict
  for attribute data.
- Forgetting the doubling cap: doubling a one-sided mass at or above one
  half caps at 1.0, so the most central count, p0 = 0.5 with k = n/2,
  reports a two-sided p_value of exactly 1.0, not 1.25.
- Reporting a mid-p value without its flag: the mid-p variant subtracts
  the observed mass from the doubled two-sided p (and half of it from a
  one-sided p), so it is always below the conservative value and the
  midp_applied key must be reported with it.
- Confusing the direction with the alternative: direction records where k
  sits relative to the null mean n*p0 (less at or below, greater above),
  while the alternative parameter chooses which tail forms the one-sided
  p-value; a count above the mean still gives a large less p-value.
- Pointing the continuity correction the wrong way: the half step moves
  toward the null mean, so z uses k + 0.5 below the mean and k - 0.5
  above it.
- Feeding boundary proportions: p0 exactly 0 or 1 is non-physical for a
  test of the open interval (0, 1) and raises ValueError, and the observed
  count must be an integer inside [0, n].
- Forgetting the edge counts: k = 0 gives an upper tail of exactly 1.0 and
  k = n gives a lower tail of exactly 1.0; both are valid test inputs, not
  errors.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_exact_binomial_test.py

The test covers the worked-example anchors (lower tail 0.1110 and two-sided
p 0.2220 for eight successes in forty trials against p zero 0.30, 0.0355
for two in twenty, z -1.208 with p 0.227), the doubling and cap identities
at the most central count, the direction semantics for counts above the
null mean, the mid-p identities for the two-sided and one-sided variants,
the continuity-correction z formula on both sides of the mean, the
large-sample convergence of the normal approximation, the small-count
verdicts at and around the 5 boundary, the distribution identities (CDF at
k = n exactly 1, masses summing to 1, edge counts k = 0 and k = n, single
trial), the exact dict keys and determinism, and every ValueError guard
from the validation list.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames the statistical
  methodology context; the exact binomial tail relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

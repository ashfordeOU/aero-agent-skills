---
name: proportion-confidence-interval
description: "Use when you must estimate a confidence interval for a binomial proportion: compute the Wilson score interval and its continuity-corrected variant, compute the exact Clopper-Pearson interval by inverting the binomial tail through an in-leaf regularized incomplete beta, and compute the confidence interval for the difference of two proportions from attribute data at a stated confidence level. Produces the lower and upper bounds by each method, the interval width, and the method recommendation that gates pass-rate, yield, and fraction-defective claims. Trigger: wilson score interval, clopper pearson interval, binomial proportion confidence bound, exact proportion interval, two proportion difference, pass fail rate."
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
  tags: [proportion-confidence-interval, wilson-score-interval, clopper-pearson-interval, binomial-proportion, exact-confidence-bound, two-proportion-difference]
  version: 0.1.0
  author: AeroSkills
---

# Proportion Confidence Interval (cross-cutting/numerics/proportion-confidence-interval)

Use when you must estimate a confidence interval for a binomial
proportion from attribute data (pass-fail, go-no-go, defect counts):
the Wilson score interval, its continuity-corrected variant, the exact
Clopper-Pearson interval computed by inverting the binomial tail through
an in-leaf regularized incomplete beta, and the normal-approximation
interval for the difference of two proportions. All quantiles and beta
values come from the module's own inversion machinery, pure Python
stdlib with no external statistics packages. It pairs with
cross-cutting/numerics/confidence-interval-estimation for intervals on
continuous measurements and with cross-cutting/numerics/hypothesis-testing
for the verdict layer on the same attribute data.

## Domain quick reference

- Conventions: k successes in n trials, confidence level cl in (0, 1)
  (default 0.95), z = normal_quantile((1 + cl) / 2) computed in-leaf
  (1.959964 for 0.95). All single-proportion bounds live in [0, 1].
- Wilson score interval: center = (phat + z^2 / (2n)) / (1 + z^2 / n),
  half-width = z * sqrt(phat(1 - phat) / n + z^2 / (4n^2)) /
  (1 + z^2 / n), bounds = center +/- half-width with k = 0 forcing lower
  0 and k = n forcing upper 1. Good default for most attribute claims.
- Continuity-corrected Wilson: the Newcombe form, which moves the
  interval outward by the 1/(2n) correction term; it is always at least
  as wide as the plain Wilson interval and keeps the same endpoints at
  k = 0 and k = n.
- Clopper-Pearson exact interval: lower solves I_p(k, n - k + 1) =
  alpha / 2 and upper solves I_p(k + 1, n - k) = 1 - alpha / 2, where
  I_p is the regularized incomplete beta evaluated in-leaf with the
  symmetry transform (below the crossover (a + 1) / (a + b + 2) use
  betacf(a, b, x) / a, at or above it use 1 - bt * betacf(b, a, 1 - x) /
  b) and inverted by bisection to 1e-10. k = 0 gives lower 0 and k = n
  gives upper 1 by endpoint handling.
- Two-proportion difference (normal approximation): diff = p1 - p2 with
  standard error sqrt(p1(1 - p1) / n1 + p2(1 - p2) / n2); the interval
  is diff +/- z * se and the reported width is the margin z * se of the
  worked example.
- The Clopper-Pearson interval is exact but conservative (guaranteed
  coverage at or above the level); Wilson is approximate with good
  coverage that is closer to nominal, so Wilson is the default and
  Clopper-Pearson the audit-grade check.
- NACA TR-824 frames the aeronautics numerics context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. State the attribute data: k successes in n trials (or the defect
   count for a fraction-defective claim) and the confidence level cl.
2. Compute the Wilson score interval with wilson_score_interval(k, n,
   cl) as the default estimate for the proportion.
3. If the sample is small or the claim is audit-grade, cross-check with
   the exact clopper_pearson_interval(k, n, cl) and report the exact
   bound when it differs materially.
4. When a continuity correction is wanted for conservatism near the
   edges, run wilson_score_cc_interval(k, n, cl) alongside the plain
   Wilson interval.
5. For a difference between two groups (configuration A versus B,
   batch versus batch), run two_proportion_diff_interval(k1, n1, k2,
   n2, cl) and report diff, the bounds, and the width.
6. Form the method recommendation: Wilson for the default gate,
   Clopper-Pearson when the claim must hold at the stated confidence,
   and the two-proportion interval when the comparison is the claim.
7. Confirm every result with the deterministic checks and the contract
   test scripts/test_proportion_confidence_interval.py.

## Worked example

Attribute data with 12 successes in 400 trials at cl = 0.95
(phat = 0.03), module output in brackets:

- Wilson: [0.017243, 0.051699], width 0.034456; a 95% claim on the
  pass rate of 3% runs from 1.72% to 5.17%.
- Clopper-Pearson: [0.015596, 0.051817], width 0.036222; the exact
  interval is wider, as expected at finite n.
- Zero-success edge: k = 0, n = 30 gives Wilson [0.0, 0.113513] and
  Clopper-Pearson [0.0, 0.115703]; the Clopper-Pearson upper obeys the
  rule of three: 1 - 0.025^(1/30) = 0.1157.
- All-success edge: k = 30, n = 30 gives Wilson [0.886487, 1.0] and
  Clopper-Pearson [0.884297, 1.0].
- Two-proportion: k1 = 5, n1 = 100 versus k2 = 1, n2 = 100 gives diff
  0.04, width 0.046957 and interval [-0.006957, 0.086957]; the interval
  contains zero, so the 5% versus 1% observed rates are not separated
  at 95% confidence with these sample sizes.

## Verification

- Confirm wilson_score_interval(12, 400) returns lower 0.017243 and
  upper 0.051699, within 1e-4 of the spec anchors.
- Confirm clopper_pearson_interval(12, 400) returns lower 0.015596 and
  upper 0.051817, and clopper_pearson_interval(0, 30) upper 0.115703.
- Confirm both intervals contain phat = k / n at several (k, n), and
  that the width shrinks as n grows at fixed phat.
- Confirm the two-proportion width for (5, 100) versus (1, 100) is
  0.04696 within 1e-3.
- Confirm k outside [0, n], n <= 0 and cl outside (0, 1) raise
  ValueError in every interval function.
- Confirm the dict keys are exactly lower/upper/width (plus diff for
  the two-proportion function) and that every bound stays in [0, 1]
  for the single-proportion methods.
- Run the contract test offline: python3
  scripts/test_proportion_confidence_interval.py (35 tests,
  deterministic, under 1 second).

## Related leaves

- cross-cutting/numerics/confidence-interval-estimation: parametric
  intervals for a mean, a difference of means and a variance from
  continuous measurement data.
- cross-cutting/numerics/hypothesis-testing: significance tests that
  consume the same attribute data and produce the verdict layer.
- cross-cutting/numerics/descriptive-statistics: the sample statistics
  (counts, rates) that feed the proportion intervals.
- cross-cutting/numerics/probability-distributions: binomial and beta
  distribution context behind the inversion methods.

## Pitfalls

- Reporting a Wald interval for a small or edge sample: the
  normal-approximation (Wald) interval phat +/- z * sqrt(phat(1 -
  phat) / n) collapses to a point at k = 0 or k = n and is badly
  anti-conservative at small n; the Wilson interval in this leaf does
  not have that failure and is the default.
- Quoting the continuity-corrected Wilson interval without saying so:
  the Newcombe form is visibly wider than the plain Wilson interval
  (0/30 upper 0.1413 versus 0.1135), so mixing the two variants in one
  report inflates or deflates the claim silently.
- Treating Clopper-Pearson as the tightest bound: it is exact in
  coverage but conservative, so its width at small n can exceed the
  Wilson width by a wide margin (3/7 gives lower 0.099 versus 0.158);
  pick it for guaranteed coverage, not for tightness.
- Reading a difference-of-proportions interval that straddles zero as a
  verdict: a 95% interval containing zero means the observed rates are
  not separated at that level, but the verdict layer belongs to
  cross-cutting/numerics/hypothesis-testing, not to this leaf.
- Forgetting the k = 0 and k = n endpoint handling: the incomplete beta
  inversion is degenerate at the edges, so the module forces lower 0 at
  k = 0 and upper 1 at k = n; without it the exact interval would
  misreport a zero-failure claim.
- Inverting the beta without the symmetry transform: a continued
  fraction run only in one direction loses accuracy above the crossover
  (a + 1) / (a + b + 2) and the Clopper-Pearson upper bounds drift;
  the transform branch is required for the exact bounds.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_proportion_confidence_interval.py

The test covers the spec anchors (Wilson 12/400 [0.017243, 0.051699],
0/30 [0.0, 0.113513], 30/30 [0.886487, 1.0]; Clopper-Pearson 12/400
[0.015596, 0.051817], 0/30 [0.0, 0.115703], 30/30 [0.884297, 1.0];
two-proportion diff 0.04 with width 0.04696), phat containment, width
shrinkage with n, the closed-form Wilson center identity, the exact
binomial-tail inversion identity for Clopper-Pearson, beta symmetry
across the crossover, the rule-of-three bound, convergence of
Clopper-Pearson to Wilson at large n, dict key contracts, determinism,
and ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the aeronautics
  numerics reference id per standards-map.yaml; the interval relations
  above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

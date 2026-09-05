---
name: poisson-confidence-interval
description: "Use when you must compute a confidence interval for a Poisson rate from a count over an exposure: estimate the rate lambda_hat = k / T, form the exact Garwood interval from in-leaf chi-square quantiles with lower bound chi2(2k, alpha/2)/(2T) and upper bound chi2(2k+2, 1-alpha/2)/(2T), and report the normal approximation as the large-count cross-check. Produces the rate estimate, the exact lower and upper bounds per exposure unit, the approximation bounds, and the containment verdict that gates defect-rate and rare-event claims. Trigger: poisson rate confidence interval, defect count per flight cycle, garwood exact bound, count rate interval, rare event rate claim."
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
  tags: [poisson-confidence-interval, count-rate-interval, defect-rate-estimation, garwood-exact-interval, poisson-rate-ci]
  version: 0.1.0
  author: AeroSkills
---

# Poisson Confidence Interval (cross-cutting/numerics/poisson-confidence-interval)

Use when you must compute an exact confidence interval for a Poisson
rate from a total event count over an exposure: k defects, failures or
rare events observed over T flight cycles, test hours or inspection
units, giving the Garwood exact interval from the chi-square relation
and the normal approximation as the large-count cross-check. All
chi-square and normal quantiles come from the module's own inversion
machinery, pure Python stdlib with no external statistics packages. It
pairs with cross-cutting/numerics/proportion-confidence-interval for
success-over-trials attribute data (no exposure term) and with
cross-cutting/numerics/hypothesis-testing for the verdict layer on the
same count data.

## Domain quick reference

- Conventions: k events over exposure T, confidence level cl in (0, 1)
  (default 0.95), alpha = 1 - cl. The rate estimate is
  lambda_hat = k / T per exposure unit.
- Chi-square quantile: chi2(df, q) is the value x with
  P(chi-square with df degrees of freedom <= x) = q. The module
  evaluates the chi-square CDF as the regularized lower incomplete
  gamma P(df / 2, x / 2), computed by power series below the crossover
  x < a + 1 and by a Lentz continued fraction of the survival function
  above it, and inverts by bisection to tolerance 1e-9.
- Exact Garwood interval: lower = chi2(2k, alpha / 2) / (2T),
  upper = chi2(2k + 2, 1 - alpha / 2) / (2T), per exposure unit. A
  zero count gives lower 0.0 because the df = 0 quantile is degenerate;
  the upper still uses df = 2.
- Normal approximation: bounds (k +/- z * sqrt(k)) / T with
  z = normal_quantile((1 + cl) / 2) (1.959964 at 0.95), the Wald form
  that gates large-count claims.
- Small-count behavior: at k = 12 the exact upper bound exceeds the
  normal upper bound and the exact interval is the wider one, while
  the two upper bounds converge as the count grows (within 5 percent
  by k = 200). The Garwood interval is exact but not centered, so the
  lower-side comparison depends on the case; the conservative widening
  is on the upper bound and in total width.
- Exposure scaling: both bounds scale as 1 / T, so doubling the
  exposure halves the rate and tightens every bound by exactly two.
- NACA TR-824 frames the aeronautics numerics context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. State the count and exposure: total events k (defects, failures)
   over exposure T (flight cycles, test hours, inspection units), and
   confirm the rate estimate lambda_hat = k / T with
   poisson_rate(k, T).
2. Choose the confidence level cl (default 0.95) and split the
   two-sided tail: alpha = 1 - cl with alpha / 2 on each side for the
   chi-square quantiles.
3. Invert the chi-square CDF: chi_square_quantile(df, q) bisects the
   regularized lower incomplete gamma survival function P(df / 2, x /
   2) to tolerance 1e-9, called with df = 2k at q = alpha / 2 and with
   df = 2k + 2 at q = 1 - alpha / 2; a zero count skips the degenerate
   df = 0 lower quantile and reports lower bound 0.
4. Form the exact Garwood interval with poisson_confidence_interval(k,
   T, cl): lower = chi2(2k, alpha / 2) / (2T), upper = chi2(2k + 2,
   1 - alpha / 2) / (2T), method "exact-poisson", and check the rate
   estimate lies inside the bounds.
5. Run the normal approximation cross-check with
   normal_approximation_interval(k, T, cl): bounds (k +/- z * sqrt(k))
   / T with z = normal_quantile((1 + cl) / 2), method
   "normal-approximation".
6. Report the rate estimate, both intervals, the containment verdict
   and the convergence note: the exact upper bound exceeds the normal
   upper bound at small counts and the two agree within 5 percent by
   k = 200, so gate the defect-rate claim on the exact bounds.

## Worked example

k = 12 defects over T = 240 flight cycles at cl = 0.95, module output
in brackets:

- Rate estimate: lambda_hat = 12 / 240 = 0.05 per cycle
  (poisson_rate(12, 240) = 0.05).
- Chi-square quantiles: chi2(24, 0.025) = 12.401 and chi2(26, 0.975) =
  41.923, inverted by bisection of the incomplete gamma survival
  function.
- Exact Garwood interval: lower = 12.401 / 480 = 0.025836, upper =
  41.923 / 480 = 0.087340, method "exact-poisson".
- Normal approximation: (12 +/- 1.959964 * sqrt(12)) / 240 gives
  [0.021710, 0.078290], method "normal-approximation".
- Zero-count edge: k = 0, T = 100 gives exact [0.0, 0.036889] (upper
  from chi2(2, 0.975) / 200 = 7.378 / 200).
- Convergence: k = 200, T = 4000 gives exact upper 0.057430 against
  normal upper 0.056930, about 0.9 percent apart, inside the 5 percent
  bound.

## Verification

- Confirm poisson_rate(12, 240) returns 0.05 exactly and that the
  exact interval rate key is the same estimate.
- Confirm poisson_confidence_interval(12, 240) returns lower 0.025836
  and upper 0.087340, within 1e-4 of the spec anchors 0.02584 and
  0.08734.
- Confirm normal_approximation_interval(12, 240) returns lower 0.021710
  and upper 0.078290, within 2e-3 of the anchors 0.0217 and 0.0783.
- Confirm poisson_confidence_interval(0, 100) returns lower 0.0 and
  upper 0.036889, within 2e-4 of the anchor 0.0369, and that the
  zero-count upper bound is positive.
- Confirm the rate estimate lies inside the exact interval and that
  doubling the exposure halves the rate and halves every bound.
- Confirm the exact upper bound exceeds the normal upper bound at
  count 12 with the exact width larger, and that at k = 200, T = 4000
  the two upper bounds agree within 5 percent. The Garwood interval is
  not centered, so at count 12 the exact lower bound 0.025836 sits
  above the normal lower bound 0.021710; the guaranteed widening is on
  the upper side and in total width, which is the check this leaf
  asserts (assumption recorded against the wave-39 spec containment
  bullet, which lists only the upper-side relation in its
  parenthetical).
- Confirm chi_square_quantile(2, 0.5) reproduces the closed form
  -2 * ln(0.5) to 1e-9 and that chi2(1, 0.5) is 0.454936.
- Confirm every dict carries exactly the keys rate, lower, upper,
  method with the documented method string, and that repeated runs are
  deterministic.
- Confirm ValueError rejection: negative or fractional count, zero or
  negative exposure, confidence level at or outside (0, 1), df below 1
  or fractional, and q at or outside (0, 1).
- Run the contract test offline: python3
  scripts/test_poisson_confidence_interval.py (33 tests,
  deterministic, under 1 second).

## Related leaves

- cross-cutting/numerics/confidence-interval-estimation: t and
  variance intervals for continuous measurements, no count or rate
  term.
- cross-cutting/numerics/proportion-confidence-interval: Wilson and
  exact intervals for a success-over-trials fraction, no exposure
  term.
- cross-cutting/numerics/hypothesis-testing: significance tests that
  consume the same count data and produce the verdict layer.
- manufacturing-quality/as9100/attribute-control-charts: normal
  approximation chart limits for attribute data in a different pack
  and estimator family.

## Pitfalls

- Quoting the normal approximation for a small count: the Wald form
  understates the upper risk badly at low k (12/240 upper 0.0783
  against the exact 0.0873) and collapses to a point at k = 0, so the
  exact Garwood bound is the gate for rare-event claims.
- Forgetting the exposure: a count without the exposure T is
  meaningless for a rate claim, and both bounds scale as 1 / T, so
  quoting k = 12 "defects per 240 cycles" as 12 per cycle inflates
  the rate 240-fold.
- Reading the two-sided split backwards: the lower bound needs the
  alpha / 2 quantile at df = 2k and the upper bound the
  1 - alpha / 2 quantile at df = 2k + 2; swapping the tail sides or
  the degree-of-freedom shift moves both bounds off the stated level.
- Assuming the exact interval contains the normal interval: the
  Garwood interval is not centered, and at count 12 its lower bound
  0.02584 sits above the normal lower 0.02171 while only the upper
  bound and total width widen; the honest claim is exactness of
  coverage, not symmetric containment.
- Treating chi2(2k, alpha / 2) as a table lookup with the wrong tail:
  chi2(24, 0.025) is 12.401, not the 39.364 upper-tail value, and the
  misread interval shrinks to nothing on the lower side.
- Hand-rolling the quantile without the survival function: the
  chi-square quantile needs the inverse of P(df / 2, x / 2), which the
  in-leaf bisection computes to 1e-9; a rough normal shortcut breaks
  the small-count anchors.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_poisson_confidence_interval.py

The test covers the spec anchors (exact 12/240 lower 0.02584 and upper
0.08734 within 1e-4, normal 12/240 0.0217 and 0.0783 within 2e-3,
zero-count 0/100 upper 0.0369 within 2e-4), chi-square quantile
anchors and the df = 2 closed form, rate containment, exposure
scaling, the upper-bound widening and the 5 percent convergence at
k = 200, dict key and method string contracts, determinism, and
ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is the aeronautics
  numerics reference id per standards-map.yaml; the Poisson interval
  relations above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

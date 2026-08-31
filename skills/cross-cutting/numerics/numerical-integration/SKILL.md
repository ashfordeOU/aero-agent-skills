---
name: numerical-integration
description: "Use when you must integrate a function numerically: select the composite trapezoid rule, the composite Simpson rule, or Gauss-Legendre quadrature for the integrand, compute the integral estimate, and estimate the error with Richardson extrapolation of the trapezoid rule. Produces the integral estimate, the chosen method with its justification, and the error estimate that gate quantitative analysis of smooth, endpoint-singular, and high-degree integrands. Trigger: numerical integration, trapezoid rule, simpson rule, gauss legendre, quadrature, error estimate, definite integral."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [numerical-integration, trapezoid-rule, simpson-rule, gauss-legendre, quadrature, error-estimate, richardson-extrapolation, definite-integral]
  version: 0.1.0
  author: AeroSkills
---

# Numerical Integration (cross-cutting/numerics/numerical-integration)

Use when the task is integrating a function numerically: choosing the
quadrature method, computing the integral estimate, and reporting the
error estimate for the trapezoid rule.

## Domain quick reference

- Composite trapezoid rule: I = (b-a)/(2n) * (f(a) + f(b) + 2 *
  sum_{i=1}^{n-1} f(a + i h)) with h = (b-a)/n. Error scales with
  h^2; cheap, robust, and the right default for an arbitrary or
  noisy integrand.
- Composite Simpson rule: I = (b-a)/(3n) * (f(a) + f(b) + 4 *
  sum_odd + 2 * sum_even), n even. Error scales with h^4; exact for
  polynomials of degree <= 3, so it beats trapezoid on smooth
  integrands with a mild endpoint cost.
- Gauss-Legendre quadrature: I = (b-a)/2 * sum w_i f((b-a)/2 x_i +
  (a+b)/2) with fixed nodes and weights on [-1, 1], n in {2, 3, 4,
  5}. The n-point rule is exact for polynomials of degree <= 2n - 1;
  one short call resolves a smooth integrand that a composite rule
  would need many panels for.
- Error estimate: the trapezoid error scales with h^2, so combining
  the n and 2n estimates gives, to leading order,
  error(2n) = abs(I_2n - I_n) / 3 (Richardson extrapolation). Use it
  to pick n: refine until the estimate is below the tolerance.
- Method selection: trapezoid for arbitrary or noisy integrands and
  error estimation; Simpson for smooth integrands when n must stay
  moderate; Gauss-Legendre for smooth integrands when a single high
  degree of exactness matters and the integrand is cheap to
  evaluate.
- All functions are deterministic and stdlib-only; no network, no
  third-party numerical libraries.
- Textbook anchor: the composite rules and Gauss-Legendre tables are
  the classical numerical-analysis results (Abramowitz and Stegun,
  25.4); integral of x^2 on [0, 2] = 8/3 = 2.6666666667 and integral
  of sin(x) on [0, pi] = 2.0 are the hand-computed checks.

## Workflow

1. Collect the integrand f, the interval [a, b], and the target
   tolerance.
2. Select the method: trapezoid, Simpson, or Gauss-Legendre per the
   integrand shape (smooth vs noisy, degree of exactness needed).
3. Compute the estimate with trapezoid, simpson, or gauss_legendre.
4. Estimate the error with error_estimate_trapezoid and refine n
   until the estimate is below the tolerance.
5. Report the estimate, the method, and the error estimate together.

## Pitfalls

- Using Simpson with an odd n: the composite Simpson rule requires
  an even number of subintervals; an odd n raises, never silently
  drops a panel.
- Using a non-integer n: n must be an int; a float like 2.5 raises,
  never truncates.
- Refining without an error estimate: error_estimate_trapezoid gives
  the leading-order error for free; pick n against the tolerance
  instead of guessing.
- Expecting Gauss-Legendre to accept any n: only n in {2, 3, 4, 5}
  are in the fixed node table; other counts raise.
- Treating a single Gauss-Legendre call as a composite rule: it is
  one high-accuracy sample, exact for low-degree polynomials, not a
  convergence sequence.

## Behavior contract (gate 3)

The composite trapezoid rule, composite Simpson rule, Gauss-Legendre
quadrature, and the Richardson error estimate logic is exercised by
the gate 3 contract test: scripts/test_numerical_integration.py
against scripts/numerical_integration_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_numerical_integration.py

## Compliance

- Standards referenced, not reproduced: NACA TR-824 anchors the
  compressible-flow tables that these quadrature rules support;
  the rules themselves are classical numerical-analysis methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: finite-difference-derivatives
description: "Use when you must compute numerical derivatives of a function or of tabulated data with finite difference formulas: choose between the forward, backward, and central difference stencils, size the step h, compute the second derivative with the centered three point stencil, and differentiate evenly spaced tabulated data with one sided differences at the boundaries. Produces the first and second derivative estimates and the tabulated derivative values that gate the differentiation step. Trigger: finite difference, central difference, forward difference, backward difference, step size, truncation error, second derivative, tabulated data."
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
  tags: [finite-difference, central-difference, forward-difference, backward-difference, truncation-error, step-size, second-derivative, tabulated-data]
  version: 0.1.0
  author: AeroSkills
---

# Finite Difference Derivatives (cross-cutting/numerics/finite-difference-derivatives)

Use when the task is computing numerical derivatives with finite
difference stencils: first derivatives of a function by forward,
backward, or central differences, the second derivative by the
centered three point stencil, and derivatives of evenly spaced
tabulated data with one sided differences at the boundaries.

## Domain quick reference

- Forward difference: f'(x) ~= (f(x + h) - f(x)) / h, one sided
  stencil with truncation error O(h).
- Backward difference: f'(x) ~= (f(x) - f(x - h)) / h, one sided
  stencil with truncation error O(h).
- Central difference: f'(x) ~= (f(x + h) - f(x - h)) / (2 h), the
  centered stencil with truncation error O(h^2); exact for
  quadratics.
- Second derivative: f''(x) ~= (f(x + h) - 2 f(x) + f(x - h)) / h^2,
  the centered three point stencil, error O(h^2).
- Tabulated data: the centered stencil at interior points, the
  forward stencil at the first point, and the backward stencil at
  the last point; the x values must be evenly spaced.
- Step sizing: halving h halves the error of the one sided stencils
  and quarters the error of the centered stencils, until roundoff
  from the h^2 divisions takes over; the step must stay strictly
  positive.

## Workflow

1. Decide which derivative and which stencil: one sided when the
   derivative sits at a boundary, centered when interior accuracy
   matters.
2. Pick the step h: small enough for a small truncation error, large
   enough to keep roundoff away from the division by h.
3. Compute the first derivative with forward_difference,
   backward_difference, or central_difference(f, x, h).
4. Compute the second derivative with second_central_difference.
5. For tabulated data, pass xs and ys to tabulated_derivative and
   read the derivative at each point before gating the step.

## Pitfalls

- Using a zero or negative step: the stencils raise ValueError; a
  step of zero divides by nothing.
- Choosing the centered stencil at a domain boundary: it samples
  f(x - h) outside the domain; use the one sided stencil there.
- Expecting the forward stencil to match the centered accuracy: the
  one sided error is O(h), the centered error is O(h^2).
- Shrinking h without bound: roundoff grows as h shrinks; the
  centered stencil on sin reaches its best accuracy near h = 1e-5
  for double precision.
- Feeding unevenly spaced tabulated data: tabulated_derivative
  raises ValueError; resample to even spacing first.
- Confusing this leaf with the convergence-verification leaf:
  Richardson extrapolation, the grid convergence index, and mesh
  refinement studies belong to convergence-verification; this leaf
  computes plain stencil derivatives.

## Behavior contract (gate 3)

The stencil and tabulated-data logic is exercised by the gate 3
contract test: scripts/test_finite_difference_derivatives.py against
scripts/finite_difference_derivatives_logic.py (stdlib unittest,
offline). Run:

python3 scripts/test_finite_difference_derivatives.py

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. Finite difference stencils are
  generic numerical methodology, not RTCA or SAE content; summary
  and formulas only.
- compliance: STANDARDS-REF, gated: false.

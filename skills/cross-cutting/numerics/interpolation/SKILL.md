---
name: interpolation
description: "Use when you must estimate a value between the tabulated points of an aerospace data table: interpolate linearly between two adjacent data points, perform piecewise linear interpolation over a whole table, build a natural cubic spline through the data points and evaluate it at an intermediate abscissa, extend beyond the table ends with the boundary behavior, and validate that the table is sorted and well formed before the lookup. Produces the interpolated value, the spline coefficients, and the bracketing segment that gate the table lookup step. Trigger: linear interpolation, cubic spline, piecewise linear, table lookup, spline coefficients."
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
  tags: [linear-interpolation, piecewise-linear, cubic-spline, natural-cubic-spline, table-lookup, data-table, spline-coefficients, tabular-data, boundary-extrapolation, aerodynamic-data-table, interpolated-value]
  version: 0.1.0
  author: Aero Agent Skills
---

# Table Interpolation (cross-cutting/numerics/interpolation)

Use when the task is estimating a value between the tabulated points
of an aerospace data table: linear interpolation on one segment,
piecewise linear interpolation over the whole table, the natural
cubic spline through the data points, and boundary extrapolation.

## Domain quick reference

- Linear interpolation on one segment:
  y = y0 + (y1 - y0) * (x - x0) / (x1 - x0). The result lies on the
  straight line through (x0, y0) and (x1, y1); at x = x0 it returns
  y0 and at x = x1 it returns y1. The same formula extends the line
  beyond the segment when x is outside [x0, x1].
- Piecewise linear table interpolation: locate the bracketing segment
  with a binary search, apply the linear formula on that segment only.
  The result is continuous and monotone between knots: it never
  overshoots the neighboring table values.
- Natural cubic spline: the piecewise cubic that passes through every
  knot, is twice differentiable at the knots, and has zero second
  derivative at both ends (m0 = m[n-1] = 0). The interior second
  derivatives m[1..n-2] solve a tridiagonal linear system, solved
  with the Thomas algorithm.
- Spline segment evaluation on [x[i], x[i+1]] with h = x[i+1] - x[i]:
  S(x) = m[i] * (x[i+1] - x)^3 / (6 h)
       + m[i+1] * (x - x[i])^3 / (6 h)
       + (y[i] / h - m[i] * h / 6) * (x[i+1] - x)
       + (y[i+1] / h - m[i+1] * h / 6) * (x - x[i]).
- Extrapolation: linear tables extend with the end segment slope; the
  spline extends with the end segment polynomial. Both require the
  explicit extrapolate flag, and both degrade quickly far from the
  table, the spline faster than the line.
- Table requirements: at least 2 points, xs and ys of equal length,
  every value finite, xs strictly increasing. Tables of lift
  coefficient versus angle of attack, drag polar points, and
  atmosphere profiles are the classic aerospace use.
- Method choice: linear interpolation preserves monotonicity and
  never oscillates; the natural spline is smoother but can overshoot
  between knots, and it does not reproduce a quadratic function
  exactly because its end second derivatives are forced to zero.
- Sanity checks: the interpolant reproduces the table exactly at the
  knots; linear and spline results agree at the knots and stay close
  in the interior for well-behaved tables.

## Workflow

1. Validate the table with validate_table: at least 2 points, equal
   lengths, finite values, strictly increasing xs. A sorted table is
   the precondition for the binary search.
2. Choose the method: piecewise linear when monotonicity matters or
   the data are noisy; the natural cubic spline when a smooth curve
   through the knots is wanted.
3. For one segment, interpolate with linear_interpolate(x, x0, y0,
   x1, y1); for a whole table use interpolate_linear(xs, ys, x).
4. For the spline, either call interpolate_cubic(xs, ys, x) directly
   or split the steps: natural_cubic_spline_coefficients to get the
   second derivatives, then cubic_spline_evaluate(xs, ys, m, x).
5. Handle the boundaries: pass extrapolate=True only when a value
   beyond the table ends is genuinely needed, and prefer linear
   extrapolation over spline extrapolation far outside the table.
6. Verify the result: the value at any knot equals the table value,
   and for interior points the linear and spline results should agree
   closely on smooth data before the lookup result is used.

## Pitfalls

- Querying outside the table without the extrapolate flag: both
  interpolate_linear and cubic_spline_evaluate raise ValueError; pass
  extrapolate=True deliberately, never to silence the error.
- Feeding an unsorted table: the binary search returns the wrong
  segment and the value is silently wrong; validate_table raises on
  non-increasing xs.
- Trusting spline overshoot: the natural spline can exceed the local
  table range between knots, especially near steep steps; linear
  interpolation never does. Check the spline value against the
  neighboring knots before using it.
- Expecting the natural spline to reproduce smooth functions: it
  reproduces the knots exactly but a quadratic sampled at 4 points
  gives interior second derivatives of 2.4, not 2; do not demand
  exactness away from the knots.
- Extrapolating far beyond the table: a cubic continues to grow or
  fall steeply; linear extension with the end slope is the safer
  boundary behavior for design margins.
- Degenerate segments: a repeated x value divides by zero in the
  linear formula; validate_table rejects repeated abscissas.
- Confusing this leaf with finite-difference-derivatives:
  derivatives of tabulated data belong to that leaf, interpolated
  values between tabulated points belong here.
- Confusing interpolation with least-squares-regression: regression
  fits a model to scattered data, interpolation passes exactly
  through the given points.

## Behavior contract (gate 3)

The interpolation math is exercised by the gate 3 contract test:
scripts/test_interpolation.py against scripts/interpolation_logic.py
(stdlib unittest, offline, 42 cases). Run:

python3 scripts/test_interpolation.py

## Compliance

- NACA Report 824 (Summary of Airfoil Data) is US government work,
  public domain, and the pack anchor for tabulated aerodynamic data
  per standards-map.yaml; it is referenced, not reproduced. Table
  interpolation is generic numerical methodology, summary and
  formulas only.
- compliance: STANDARDS-REF, gated: false.

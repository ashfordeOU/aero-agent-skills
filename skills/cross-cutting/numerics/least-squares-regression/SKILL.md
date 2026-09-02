---
name: least-squares-regression
description: "Use when you must fit a straight line to paired measurements by ordinary least squares: compute the slope and intercept of the best fit, the residual standard deviation, and the coefficient of determination, and predict the response at a new input. Produces the fit coefficients, the goodness of fit, and the residual scatter that gate whether the linear model is adequate for the analysis. Trigger: least squares, linear regression, best fit line, slope, intercept, residual standard deviation, coefficient of determination, r squared, prediction."
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
  tags: [least-squares-regression, linear-regression, best-fit-line, slope, intercept, residual-standard-deviation, coefficient-of-determination, r-squared, prediction, goodness-of-fit]
  version: 0.1.0
  author: Aero Agent Skills
---
# Least Squares Regression (cross-cutting/numerics/least-squares-regression)

Use when the task is fitting a straight line to paired measurements by
ordinary least squares: slope and intercept, residual standard
deviation, coefficient of determination, and prediction at a new
input.

## Domain quick reference

- The fitted model is y = a + b*x with n paired samples (x_i, y_i),
  n >= 3 so the residual standard deviation has at least one degree
  of freedom.
- Slope b = Sxy / Sxx with Sxx = sum((x-xbar)**2) and
  Sxy = sum((x-xbar)*(y-ybar)); intercept a = ybar - b*xbar.
- Residuals r_i = y_i - (a + b*x_i) give SSE = sum(r_i**2); the
  residual standard deviation is s = sqrt(SSE / (n - 2)), with n - 2
  degrees of freedom for the two estimated parameters.
- Coefficient of determination r**2 = 1 - SSE / SST with
  SST = sum((y-ybar)**2), dimensionless in [0, 1].
- Prediction at a new input: y = a + b*x.

## Workflow

1. Collect the paired measurements (x, y).
2. Fit the line with linear_fit(xs, ys) -> (slope, intercept).
3. Quantify the scatter with residual_std(xs, ys, a, b).
4. Assess the model with r_squared(xs, ys, a, b).
5. Predict at a new input with predict(x, a, b); use fit_report for
   the one-shot summary before gating the analysis.

## Pitfalls

- Fitting with fewer than three points: the residual standard
  deviation needs at least one degree of freedom; the logic raises
  ValueError.
- Zero variance in x (Sxx == 0): the slope is undefined; the logic
  raises ValueError.
- Constant response (SST == 0): r**2 is undefined; the logic raises
  ValueError.
- Reporting s as the standard deviation of the data instead of the
  residual scatter around the fitted line: they are different
  quantities.
- Extrapolating far outside the sampled x range without saying so:
  the fit is only evidence inside the measured domain.

## Behavior contract (gate 3)

The fit, residual, and goodness-of-fit logic is exercised by the gate
3 contract test: scripts/test_least_squares.py against
scripts/least_squares_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_least_squares.py

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. Least squares regression is generic
  numerical methodology, not RTCA or SAE content; summary and
  formulas only.
- compliance: STANDARDS-REF, gated: false.

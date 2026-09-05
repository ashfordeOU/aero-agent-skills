---
name: multiple-linear-regression
description: "Use when you must fit a multiple linear regression model: solve the normal equations for the partial-regression-coefficient vector from two or more predictors, compute each coefficient-standard-error with the two-sided p-value of its t statistic, the overall regression-f-test p-value, R-squared and adjusted-r-squared, and the variance-inflation-factor multicollinearity-check for every predictor, then predict the response at a new design point. Produces the coefficient vector, diagnostic table and prediction that gate whether the linear model explains the data. Trigger: multiple-linear-regression, variance-inflation-factor, adjusted-r-squared, partial-regression-coefficient, regression-f-test, coefficient-standard-error, multicollinearity-check."
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
  tags: [multiple-linear-regression, variance-inflation-factor, adjusted-r-squared, partial-regression-coefficient, regression-f-test, coefficient-standard-error, multicollinearity-check]
  version: 0.1.0
  author: AeroSkills
---

# Multiple Linear Regression (cross-cutting/numerics/multiple-linear-regression)

Use when you must fit a multiple linear regression model to engineering
data with two or more predictors: solve the normal equations for the
coefficient vector, form the coefficient standard errors and
per-coefficient t statistics with two-sided p-values, run the overall
regression F test, and check each predictor with the variance inflation
factor before predicting at a new design point. Pure Python, stdlib
only. It pairs with cross-cutting/numerics/matrix-operations for the
standalone linear solve, with cross-cutting/numerics/least-squares-
regression for the single-predictor straight-line special case, and
with cross-cutting/numerics/hypothesis-testing for the standalone test
library.

## Domain quick reference

- Model: y = b0 + b1*x1 + ... + bp*xp over n rows and p predictors; the
  fit always carries an intercept column of ones internally, so p + 1
  coefficients come out and n > p + 1 rows are required for a positive
  residual degree of freedom n - p - 1.
- Normal equations: (X^T X) b = X^T y, where X is the design matrix with
  the leading ones column. Solved by Gaussian elimination with partial
  pivoting; (X^T X)^-1 is formed by Gauss-Jordan elimination for the
  standard errors.
- Goodness of fit: RSS = sum of squared residuals, TSS = sum of squared
  deviations of y from its mean, R2 = 1 - RSS/TSS, adjusted R2 =
  1 - (1 - R2) * (n - 1)/(n - p - 1), sigma2 = RSS/(n - p - 1).
- Coefficient standard errors: se(b_j) = sqrt(sigma2 * [(X^T X)^-1]_jj)
  from the inverse diagonal; t_j = b_j/se(b_j); the two-sided p-value
  comes from the regularized incomplete beta identity for Student t with
  n - p - 1 degrees of freedom (in-leaf, no scipy).
- Regression F test: F = ((TSS - RSS)/p) / (RSS/(n - p - 1)) on p and
  n - p - 1 degrees of freedom; the p-value comes from the incomplete
  beta identity for the F distribution (in-leaf).
- Variance inflation factor: VIF(j) = 1/(1 - R2_j) with R2_j from
  regressing predictor j on all other predictors with an intercept;
  VIF above 10 flags a multicollinearity concern, and a single-predictor
  model has VIF 1.0 by convention.
- Prediction: y_new = b0 + sum(b_j * x_new_j) at a new design point.
- Non-physical inputs raise ValueError: empty or ragged X, non-numeric
  entries, an X/y length mismatch, n <= p + 1, a constant response, and
  singular (rank-deficient) designs.

## Workflow

1. Assemble the predictor matrix X (n rows of p predictors, p >= 2 for
   the multiple case) and the response y, and confirm n > p + 1.
2. Optionally preview the layout with design_matrix(X), which returns
   the rows with the leading ones column.
3. Fit with ols_fit(X, y), which returns the dict with coef, rss, r2,
   adjusted_r2, sigma2, coef_se, t_stats, p_values, f_stat, f_p_value,
   residuals and fitted.
4. Screen the predictors with variance_inflation_factor(X, j) for each
   j; flag any value above 10 before reading individual coefficient
   p-values.
5. Predict the response at the new design point with predict(coef,
   x_new), passing the predictors only.
6. Confirm the deterministic checks with the contract test
   scripts/test_multiple_linear_regression.py.

## Worked example

Worked data from the leaf spec (n = 6): x1 = 1..6, x2 = 2,3,5,7,11,13,
y = 5,7,9,13,15,19. Real module outputs:

- Coefficients: coef = [1.9141104, 2.1042945, 0.3006135] (intercept,
  x1, x2); the coefficient of x1 dominates because x1 and y both rise
  with the row index.
- Goodness of fit: R2 = 0.98670, adjusted R2 = 0.97784, sigma2 =
  0.61759, RSS = 1.85276; the residuals sum to 1e-16 (intercept present).
- Diagnostics: coef_se = [0.9243, 1.0491, 0.4460], t = [2.0708, 2.0058,
  0.6740], two-sided p = [0.1301, 0.1386, 0.5486].
- Overall F: F = 111.3046 on (2, 3) degrees of freedom, p = 0.00153;
  the model is significant overall even though x2 alone is not.
- Multicollinearity: VIF(x1) = VIF(x2) = 31.19 (the two predictors
  correlate at r2 0.9679 by construction), far above the 10 flag, so
  the individual coefficient p-values must not be over-read.
- Prediction: predict(coef, [7, 15]) = 21.1534.

## Verification

- Confirm ols_fit(X, y) on the worked data returns coef within 1e-6 of
  the values above, R2 0.9867 and adjusted R2 0.9778 within 1e-4.
- Confirm t = [2.0708, 2.0058, 0.6740] within 1e-3 and both VIF values
  31.19 within 0.1; the exact p-values are leaf outputs and must lie in
  (0, 1).
- Confirm predict at (7, 15) equals 21.153 within 1e-3.
- Confirm the single-predictor reduction matches the closed-form slope
  Sxy/Sxx and intercept ybar - slope*xbar, and that adjusted R2 <= R2.
- Confirm every non-physical input raises ValueError: X/y length
  mismatch, n <= p + 1, non-numeric entries, empty X, ragged rows, a
  constant response, and a singular collinear design.
- Run the deterministic contract test offline: python3
  scripts/test_multiple_linear_regression.py (35 tests).

## Related leaves

- cross-cutting/numerics/least-squares-regression: the single-predictor
  straight-line fit that is the p = 1 special case of this method.
- cross-cutting/numerics/hypothesis-testing: the standalone t/F/
  chi-square test library for the test statistics this leaf reports.
- cross-cutting/numerics/matrix-operations: direct linear solves and
  inversions for the linear algebra underneath.
- vehicle-design/mdo/surrogate-modeling: the MDO response-surface
  application built from regression machinery, adjacent but distinct
  from the general method with coefficient tests owned here.

## Pitfalls

- Reading coefficient p-values under multicollinearity: x1 and x2 in
  the worked example give VIF 31.19 each, and the individual t
  p-values are all above 0.13 while the overall F test is significant
  at p = 0.0015; screen VIF before interpreting any single coefficient.
- Fitting with too few rows: n <= p + 1 leaves no residual degrees of
  freedom, so sigma2 and every standard error are undefined; the logic
  raises ValueError and the data must be extended.
- Reporting R2 without the penalty: R2 can only rise when a predictor
  is added, so adjusted R2 (0.97784 against 0.98670 here) is the
  honest figure for comparing models with different p.
- Ignoring the intercept column in the standard errors: se(b_j) needs
  the full (X^T X)^-1 diagonal including the ones column, not a
  predictor-only moment matrix.
- Predicting far outside the sampled predictor region: the linear fit
  is evidence only inside the measured domain, and extrapolation of a
  collinear model compounds the coefficient uncertainty.
- Confusing the overall F test with the per-coefficient tests: F asks
  whether all coefficients are jointly zero, t asks about one
  coefficient with the others present, and the two can disagree.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_multiple_linear_regression.py

The test covers the worked-example anchors (coefficients, R2, adjusted
R2, sigma2, RSS, standard errors, t statistics, prediction), the p and
F p-value unit-interval bounds, the F-statistic identity, residual-sum
and fitted-value round trips, the VIF anchors and identities, the
single-predictor closed-form reduction, ValueError rejection of every
non-physical input, and run-to-run determinism.

## Compliance

- NACA Report 824 is US government work (public domain) and the numerics
  pack anchor per standards-map.yaml; the relations above are standard
  engineering methodology, summary-only. Standards are referenced, not
  reproduced.
- compliance: STANDARDS-REF, gated: false.

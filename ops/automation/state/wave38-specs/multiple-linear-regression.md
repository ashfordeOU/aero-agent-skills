# Wave-38 leaf spec: multiple-linear-regression (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/multiple-linear-regression/
- Pack: numerics. Closest siblings: least-squares-regression (single-
  predictor straight-line fit: slope, intercept, residual std dev, r2),
  hypothesis-testing (t/F/chi-square tests), matrix-operations (linear
  solve), interpolation, surrogate-modeling (vehicle-design mdo: builds a
  QUADRATIC ridge-regularized response surface as an MDO surrogate - an
  application; the parent OLS method with diagnostics is unowned).
  Whole-tree grep: "multiple regression", "variance inflation",
  "adjusted R", "partial regression" = ZERO owning hits (least-squares-
  regression is single-predictor only, verified). ZERO owners of the
  multi-predictor OLS method. GENUINE CC gap (fresh probe; adjacency to
  surrogate-modeling disclosed - that leaf owns the MDO quadratic-RSM
  application, this leaf owns the general method with coefficient tests).
- Standards id: naca-tr-824 (reference-only; numerics sibling convention).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Fit a multiple linear regression model to engineering data with two or
more predictors: solve the normal equations for the coefficient vector,
compute the coefficient standard errors, per-coefficient t statistics and
p-values, the overall regression F statistic and p-value, the R-squared
and adjusted R-squared, the variance inflation factor for each predictor,
and predict the response at a new design point. Produces the coefficient
vector, the diagnostic table, and the prediction that gate whether the
linear model explains the data. Does NOT do: single-predictor straight-line
fit (least-squares-regression); quadratic response-surface surrogate
building for MDO (surrogate-modeling); hypothesis-test library functions
(hypothesis-testing).

## Model (implement exactly)

Conventions: X is a matrix of n rows by p columns (predictors only); the
model always includes an intercept column of ones internally. y is the
response list of length n. n > p required (overdetermined). Solve the
normal equations (X^T X) b = X^T y by Gaussian elimination with partial
pivoting (in-leaf, no numpy).

Functions (pure stdlib):
- design_matrix(X) -> list of rows with a leading 1 column.
- ols_fit(X, y) -> dict {coef (length p+1, intercept first), rss, r2,
  adjusted_r2, sigma2, coef_se, t_stats, p_values, f_stat, f_p_value,
  residuals, fitted}: R2 = 1 - RSS/TSS; adjusted = 1 - (1-R2)*(n-1)/
  (n - p - 1); sigma2 = RSS/(n - p - 1); se from the diagonal of
  (X^T X)^-1 times sigma2 (invert by Gauss-Jordan in-leaf); t = coef/se;
  p-values from the two-sided t survival via the regularized incomplete
  beta (implement in-leaf, bisection on the incomplete beta relation as in
  confidence-interval-estimation); F = ((TSS - RSS)/(p)) / (RSS/(n-p-1));
  F p-value from the incomplete beta.
- variance_inflation_factor(X, j) -> float: 1/(1 - R2_j) where R2_j comes
  from regressing predictor j on all other predictors (with intercept).
- predict(coef, x_new) -> float.
ValueErrors: X and y length mismatch, n <= p + 1, non-numeric entries,
empty X.

Identity to test: with one predictor the OLS coefficient matches the
single-predictor formulas (slope = Sxy/Sxx); adjusted R2 <= R2; VIF of a
single-predictor model is 1.0 (no other predictors to regress on -> return
1.0); residuals sum to (near) zero when an intercept is present.

## Worked example

Verified at prep (n = 6, predictors x1 = 1..6, x2 = 2,3,5,7,11,13,
y = 5,7,9,13,15,19):
- coef = [1.9141, 2.1043, 0.3006] (intercept, x1, x2).
- r2 = 0.98670, adjusted_r2 = 0.97784, sigma2 = 0.61759, RSS = 1.8528.
- coef_se = [0.9243, 1.0491, 0.4460]; t = [2.0708, 2.0058, 0.6740].
- VIF(x1) = VIF(x2) = 31.19 (x1 and x2 correlate r2 0.9679).
- predict at x1 = 7, x2 = 15: 21.153.
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds from the normal-equation solve (independently
evaluated by the anchor script at prep). The exact p-values are the leaf's
own outputs within the incomplete-beta implementation; assert the t and F
statistics (not p) to the anchors above and only bound p in (0, 1).

## Validation list (contract test must include)

- ols_fit anchor: coef within 1e-6, r2 0.9867 within 1e-4, adjusted
  0.9778 within 1e-4.
- t statistics 2.071 / 2.006 / 0.674 within 1e-3.
- VIF 31.19 within 0.1 for both predictors (they are collinear by
  construction); VIF of a one-predictor model returns 1.0.
- predict at (7, 15) = 21.153 within 1e-3.
- Single-predictor identity: matches slope/intercept formulas.
- adjusted R2 <= R2; residuals sum near zero.
- ValueErrors for rank-deficient (n <= p+1) and mismatched input.
- Determinism.

## Corpus fragment (eval/hit1-wave38-multiple-linear-regression.yaml)

Query 1 (copy verbatim):
  "fit a multiple-linear-regression with two predictors and report the partial-regression-coefficient t-test and variance-inflation-factor"
  intent: "cross-cutting; multi-predictor OLS with coefficient diagnostics"
  expected_skill: "cross-cutting/numerics/multiple-linear-regression"
Query 2 (copy verbatim):
  "compute the adjusted-r-squared and the overall regression F p-value for a three-predictor linear model"
  intent: "cross-cutting; regression goodness of fit and F test"
  expected_skill: "cross-cutting/numerics/multiple-linear-regression"
Task ids: w38-multiple-linear-regression-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must fit a multiple linear regression
model:" and include the outputs in the Claim. First tag:
multiple-linear-regression. Additional tags ONLY: variance-inflation-
factor, adjusted-r-squared, partial-regression-coefficient, regression-f-
test, coefficient-standard-error, multicollinearity-check. NEVER single
generic words (regression, fit, predictor, coefficient, model, statistics).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): slope and intercept of a straight
line, single predictor (least-squares-regression); quadratic basis, ridge
regularization, response surface, radial basis (surrogate-modeling); t
test, ANOVA (hypothesis-testing).

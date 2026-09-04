---
name: surrogate-modeling
description: "Use when you must build and validate an approximation model of an expensive aerospace analysis from sampled design data: assemble the full quadratic basis, fit a ridge-regularized quadratic response surface, fit a Gaussian radial basis function interpolant, predict the response at new design points, run a leave-one-out cross validation on both models, and recommend the surrogate with the lower estimated prediction error. Produces the fitted coefficients or weights, the cross-validation and in-sample quality metrics (rmse, max absolute error, r2), and the model recommendation that gates replacing the expensive analysis inside a multidisciplinary optimization loop. Trigger: surrogate model, metamodel, response surface, radial basis function, kriging alternative, leave one out cross validation, approximation model, prediction error."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: mdo
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: mdo
  tags: [surrogate-modeling, response-surface, radial-basis-function, leave-one-out-cross-validation, approximation-model, metamodel-fitting, prediction-error-estimation, kriging-alternative]
  version: 0.1.0
  author: Aero Agent Skills
---

# Surrogate Modeling (vehicle-design/mdo/surrogate-modeling)

Use when the task is building and validating an approximation model
(surrogate or metamodel) of an expensive aerospace analysis: fitting a
quadratic response surface and a Gaussian radial basis function (RBF)
interpolant to the input-output samples produced by a design of
experiments, predicting the response at new design points, and
estimating the prediction error of each model with a leave-one-out
cross validation before one of them replaces the expensive analysis
inside a multidisciplinary optimization loop. This leaf implements the
fit, prediction and validation layer in pure Python stdlib. It pairs
with vehicle-design/mdo/design-of-experiments, which produces the
sample plan this leaf fits, and
vehicle-design/mdo/multidisciplinary-optimization, which consumes the
recommended surrogate in the loop. It does not create the sample plan,
close the coupled loop, fit a best-fit line to paired measurements
(cross-cutting least-squares-regression), or do generic 1-D table
interpolation (cross-cutting interpolation). The kriging variant is a
related method this leaf does not implement: the Gaussian RBF here is
the deterministic interpolant alternative, fitted without kriging's
stochastic error model.

## Domain quick reference

- Quadratic basis for a d-dimensional point x, ordered linear terms
  first, then squares, then cross terms:
  b(x) = [1, x_0, ..., x_{d-1}, x_0^2, ..., x_{d-1}^2, x_0 x_1, x_0 x_2,
  ...]. Length m = (d + 1)(d + 2) / 2 (6 for d = 2). The coefficient
  vector follows this order, so for d = 2 the intercept is c[0], the
  linear terms c[1] and c[2], the squares c[3] and c[4], and the cross
  term c[5].
- Quadratic response surface: with Phi the n by m design matrix of
  basis rows, fit the ridge-regularized normal equations
  (Phi^T Phi + ridge I) c = Phi^T y, ridge = 1e-10 by default, solved
  by Gaussian elimination with partial pivoting. Predict with
  y_hat(x) = c . b(x).
- Gaussian RBF kernel: K(xi, xj) = exp(-eps * ||xi - xj||^2) with the
  width parameter eps, default 0.5. The RBF interpolant solves
  K w = y with K_ij = K(x_i, x_j) and predicts
  y_hat(x) = sum_i w_i K(x_i, x). Interpolation is exact at the
  training samples when the kernel matrix is nonsingular, which
  requires distinct sample rows.
- Leave-one-out cross validation: for each sample i, refit on all rows
  except i and predict row i. The error list feeds
  RMSE = sqrt(mean(e_i^2)) and max_abs = max(e_i); these estimate the
  prediction error of the surrogate away from its training points.
- In-sample quality: RMSE and max_abs on the training data plus
  r2 = 1 - SS_res / SS_tot (a zero-variance response reports r2 = 1.0
  when the fit is exact).
- Recommendation: compare the two leave-one-out RMSE values and pick
  the lower one; exact ties break to the quadratic model (module
  constant TIE_BREAK = "quadratic").
- FAR-25 and CS-25 set the certification context (the analyses that
  the surrogate replaces feed loads and structural margin checks); the
  response surface and RBF methods are standard statistical
  approximation methodology, summary only.

## Workflow

1. Collect the input-output samples (X rows, y responses) from the DOE
   leaf, with more samples than the m = (d + 1)(d + 2) / 2 quadratic
   basis terms; fit_quadratic raises ValueError with the count message
   when n < m.
2. Fit the quadratic response surface with fit_quadratic(X, y) and the
   RBF interpolant with fit_rbf(X, y) at the default eps 0.5.
3. Predict at the untried design points with predict_quadratic(coeffs,
   x) and predict_rbf(weights, X, x).
4. Estimate the prediction error of each model with
   loo_cross_validation(X, y, fit_quadratic) and
   loo_cross_validation(X, y, fit_rbf), which return the per-fold
   errors, the RMSE, and the max absolute error.
5. Check the in-sample fit with model_quality(X, y, fitter) for rmse,
   max_abs, and r2 on the full data.
6. Choose the surrogate with recommend_model(X, y), which compares the
   leave-one-out RMSE values and returns the table and the best model.
7. Assemble the study with surrogate_report(X, y, labels, new_points),
   which bundles the fitted coefficients and weights, the quality
   metrics, the leave-one-out results, the recommendation, and the
   predictions at the requested new points.
8. Confirm the deterministic checks with the contract test
   scripts/test_surrogate_modeling.py.

## Worked example

Deterministic analytic target f(x1, x2) = 1 + 2 x1 + 3 x2 + 4 x1^2 -
x1 x2 + 0.5 x2^2 (a pure quadratic) on the 9-point grid with x1, x2
in {-1, 0, 1}.

- Coefficient recovery: fit_quadratic returns the coefficient vector
  [1, 2, 3, 4, 0.5, -1] to within 1.7e-10, so every coefficient is
  recovered within 1e-6. This anchors the solver and the basis
  ordering: c[3] = 4 is the x1^2 square, c[4] = 0.5 the x2^2 square,
  c[5] = -1 the x1 x2 cross term.
- Prediction: predict_quadratic at (0.5, -0.5) returns 1.8750000,
  matching 1 + 1 - 1.5 + 1 + 0.25 + 0.125 = 1.875 within 1e-6.
- RBF interpolation: fit_rbf on the same 9 points at eps 0.5 returns
  weights whose predictions at every sample match y to within 4e-15;
  the K w = y solve is exact to machine precision.
- Model selection on pure quadratic data: the quadratic leave-one-out
  RMSE is 3.5e-10 against 2.81 for the RBF, so recommend_model returns
  "quadratic".
- Nonlinear demonstration: the mild nonlinear target g = f + 0.3
  sin(2 x1) is sampled on the 27-run deterministic DOE set with x1 at
  nine levels across [-1, 1] and x2 in {-1, 0, 1}. Assumption
  recorded: the spec's three-level grid {-1, 0, 1} cannot demonstrate
  the RBF advantage because sin(2 x1) at those three abscissae equals
  sin(2) * x1 exactly, so the sine is absorbed by the linear term of
  the quadratic basis; sampling the sine direction at nine levels makes
  the residual pattern genuinely non-quadratic. On that set the
  quadratic leave-one-out RMSE is 0.0839 and the RBF leave-one-out
  RMSE is 0.00728, so recommend_model returns "rbf": the RBF
  generalizes better than the quadratic to untried points when the
  underlying response is non-quadratic.


## Pitfalls

- Fitting with fewer samples than basis terms: the quadratic basis
  has m = (d + 1)(d + 2) / 2 terms and fit_quadratic raises
  ValueError (with the count) when n < m; the DOE must supply more
  samples than terms.
- Trusting in-sample error as prediction error: RMSE on the training
  data measures fit, not generalization - the model choice must use
  the leave-one-out RMSE, which is why recommend_model compares the
  LOO values and the quadratic wins on pure-quadratic data while
  RBF wins on the nonlinear 27-run set.
- Assuming the RBF is better because it interpolates: exact
  interpolation at the samples (4e-15 in the worked example) is not
  accuracy at untried points; the LOO comparison decides.
- Misreading the coefficient order: the basis is ordered linear
  terms, then squares, then cross terms, so for d = 2 the intercept
  is c[0], the linear terms c[1] and c[2], the squares c[3] and
  c[4], and the cross term c[5].
- Forgetting the ridge term and its limits: the quadratic fit uses
  ridge = 1e-10 by default on the normal equations; a singular
  matrix raises ValueError rather than returning a degenerate fit.
- Using the surrogate outside its training region: the models
  predict at new design points but carry no extrapolation guarantee,
  and duplicate or ragged sample rows break the RBF kernel solve.
## Verification

- Deterministic: the module uses only float arithmetic with no random
  draws, so every fit, prediction, metric, and recommendation is
  reproducible run to run.
- Coefficient recovery: fit_quadratic on the 9-point grid reproduces
  [1, 2, 3, 4, 0.5, -1] within 1e-6, and predict_quadratic at
  (0.5, -0.5) reproduces 1.875 within 1e-6.
- RBF exactness: predict_rbf at every training sample of the 9-point
  grid matches the sample value within 1e-6.
- Selection behavior: recommend_model returns "quadratic" on the pure
  quadratic data and "rbf" on the nonlinear 27-run data, matching the
  leave-one-out RMSE comparison with ties broken to "quadratic".
- Rejection: ValueError on an empty X, ragged rows, len(X) != len(y),
  non-finite values, eps <= 0, fewer samples than the quadratic basis
  terms (the message carries the count), a singular matrix, and
  dimension or coefficient-count mismatches at predict time.
- Run the contract test offline: python3
  skills/vehicle-design/mdo/surrogate-modeling/scripts/test_surrogate_modeling.py
  (35 tests, deterministic, exit 0 in under a second).

## Related leaves

- vehicle-design/mdo/design-of-experiments: produces the coded sample
  plan (factorial, latin hypercube, central composite) whose runs this
  leaf fits.
- vehicle-design/mdo/multidisciplinary-optimization: consumes the
  recommended surrogate inside the coupling loop once the prediction
  error estimate is acceptable.
- cross-cutting/numerics/least-squares-regression: the univariate
  best-fit line for paired measurements, the single-variable special
  case of fitting.
- cross-cutting/numerics/interpolation: 1-D table interpolation
  between tabulated points, distinct from multidimensional surrogate
  prediction.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/vehicle-design/mdo/surrogate-modeling/scripts/test_surrogate_modeling.py

The test covers the dense solver identity and singularity rejection,
the quadratic basis ordering, exact coefficient recovery on the
9-point grid within 1e-6, the analytic prediction 1.875 at
(0.5, -0.5), exact RBF interpolation, the leave-one-out error
structure and RMSE formula, the RBF beating the quadratic leave-one-out
RMSE on the nonlinear 27-run target, the in-sample quality metrics
with r2, both recommendation branches and the tie-break rule, the
surrogate_report assembly, and every ValueError rejection case.
35 tests, deterministic, PASS in under a second.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the quadratic
  response surface and Gaussian RBF methods are common statistical
  approximation methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-26 leaf spec: surrogate-modeling (vehicle-design, mdo pack)

- Path: skills/vehicle-design/mdo/surrogate-modeling/
- Pack: mdo (existing siblings: design-of-experiments,
  multidisciplinary-optimization)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: vehicle-design

## Claim

Build and validate an approximation model (metamodel / surrogate) of
an expensive aerospace analysis from design-of-experiments samples:
fit a quadratic response surface and a Gaussian radial basis function
(RBF) interpolant to the sampled input-output data, predict the
response at new design points, run a leave-one-out cross-validation to
estimate the prediction error of each model, and recommend the better
surrogate for the design space. Produces the fitted coefficients or
weights, the cross-validation error metrics, and the model
recommendation that gate replacing the expensive analysis inside a
multidisciplinary optimization loop.

Does NOT do: create the sample plan (design-of-experiments owns full
and fractional factorials, latin hypercube, and central composite
designs and returns the runs this leaf fits), run the coupled MDO loop
(multidisciplinary-optimization owns the fixed-point iteration that
can consume the surrogate), fit a single straight line to paired
measurements (cross-cutting least-squares-regression), or do generic
1-D interpolation (cross-cutting interpolation). This leaf is the
multidimensional metamodel fit, prediction, and validation layer.

## Model (implement exactly)

Linear algebra: implement a small dense solver in the module:
- solve_linear(A, b) via Gaussian elimination with partial pivoting
  (list-of-lists floats); ValueError on a singular matrix after
  pivoting (near-singular handled by the ridge terms before the
  solve).
- mat_mul, mat_transpose, mat_inv_3x3 not needed beyond the solver.
Basis and fits:
- poly_basis_quadratic(x) -> list: full quadratic basis for dimension
  d: [1, x_0..x_{d-1}, x_i * x_j for i <= j] (order: squares first
  then cross terms, documented so tests can index coefficients).
- fit_quadratic(X, y, ridge=1e-10) -> coeffs: assemble the design
  matrix Phi (n x m), solve (Phi^T Phi + ridge I) c = Phi^T y.
- predict_quadratic(coeffs, x) -> float dot(coeffs, basis(x)).
- rbf_kernel(xi, xj, eps) -> exp(-eps * ||xi - xj||^2).
- fit_rbf(X, y, eps=0.5) -> weights: solve K w = y with K_ij =
  rbf_kernel(x_i, x_j).
- predict_rbf(weights, X, x, eps) -> float sum w_i K(x_i, x).
- loo_cross_validation(X, y, fitter, **kw) -> dict {errors (list),
  rmse, max_abs}: for each i, fit on all rows except i and predict
  row i.
- model_quality(X, y, fitter, **kw) -> dict {rmse, max_abs, r2} on
  the full data (in-sample).
- recommend_model(X, y) -> dict {quadratic: loo rmse, rbf: loo rmse,
  best ("quadratic" | "rbf"), table}: compares the leave-one-out RMSE
  values; ties break to "quadratic" (module constant TIE_BREAK =
  "quadratic").
- surrogate_report(X, y, labels=None) -> dict assembling the fitted
  models, the LOO table, the recommendation, and predictions at a
  requested new point list (input new_points).
ValueError on: empty X, ragged rows (dimension mismatch), len(X) !=
len(y), non-finite values, eps <= 0, fewer samples than basis terms
for the quadratic fit (n < m raises with the count message).

## Worked example

Deterministic analytic target f(x1, x2) = 1 + 2 x1 + 3 x2 + 4 x1^2
- x1 x2 + 0.5 x2^2 (a pure quadratic).
1. Sample the 9-point grid x1, x2 in {-1, 0, 1} (noise-free):
   fit_quadratic recovers the exact coefficients (assert each within
   1e-6 of the analytic values; this anchors the solver and the basis
   ordering).
2. predict_quadratic at (0.5, -0.5) matches the analytic value 1 + 1
   - 1.5 + 1 + 0.25 + 0.125 = 1.875 (compute and assert within 1e-6).
3. fit_rbf on the same 9 points with eps 0.5 interpolates exactly:
   predict_rbf at each sample returns the sample y within 1e-6; the
   weights solve is exact.
4. Add a mild nonlinear target g = f + 0.3 * sin(2 x1) sampled on the
   same grid: loo_cross_validation returns a smaller RMSE for the RBF
   than the quadratic (assert rbf_rmse < quadratic_rmse with the real
   module outputs; sin makes the residual pattern non-quadratic).
5. recommend_model on the pure quadratic data returns "quadratic"
   (or the tie-break); on the nonlinear data returns "rbf" (assert
   the real outputs).
6. ValueError on X with 2 rows for the quadratic fit (needs at least
   6 basis terms for d = 2), on ragged rows, and on eps 0.
Keep at least 18 test methods (solver identity A x = b on a known
system, basis ordering, quadratic recovery, RBF interpolation,
predictions at interior points, LOO and quality metrics, model
recommendation branches, ValueErrors).

## Corpus tasks (ids w26-surrogate-modeling-1/2)

Distinctive tokens: surrogate model, metamodel, response surface,
radial basis function, kriging alternative, leave one out cross
validation, approximation model, expensive analysis replacement, fit
from doe samples, prediction error. Avoid: doe matrix / factorial /
latin hypercube design (design-of-experiments), mdo fixed point loop
(multidisciplinary-optimization), linear regression best fit line
(cross-cutting least-squares-regression), 1-D interpolation
(cross-cutting interpolation).

1. "fit a response surface surrogate to the 25 aerodynamic analysis
   samples from the DOE: build the quadratic model and the radial
   basis function model, run the leave one out cross validation, and
   recommend the better approximation for the MDO loop"
2. "replace the expensive structural analysis with an RBF metamodel
   fitted on the latin hypercube samples and report the cross
   validation prediction error at the new design points"

## SKILL body notes

Pair with design-of-experiments (produces the sample plan), and
multidisciplinary-optimization (consumes the surrogate in the loop);
cite cross-cutting least-squares-regression and interpolation as the
univariate siblings. The kriging variant is named in the body as the
related method this leaf does not implement (RBF is the deterministic
interpolant). Standards referenced not reproduced.

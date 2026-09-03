"""surrogate_modeling_logic.py - deterministic surrogate (metamodel) fitting.

Pure Python stdlib module for the vehicle-design/mdo/surrogate-modeling
leaf skill. Builds an approximation model of an expensive aerospace
analysis from sampled input-output data: a ridge-regularized quadratic
response surface and a Gaussian radial basis function (RBF) interpolant,
with leave-one-out cross validation, in-sample quality metrics, and a
model recommendation.

Every function is deterministic: no random draws, no external
dependencies, float arithmetic only. Non-physical or malformed inputs
raise ValueError with a count-carrying message where relevant.

Basis ordering contract (documented so tests can index coefficients):
poly_basis_quadratic returns, for an input point x of dimension d,
    [1, x_0, ..., x_{d-1}, x_0^2, ..., x_{d-1}^2, x_0*x_1, x_0*x_2, ...]
so the linear terms come first, then the squares, then the cross terms
x_i * x_j for i < j in lexicographic order. The basis length is
m = (d + 1) * (d + 2) / 2, which is 6 for d = 2.
"""

import math

# Module constants (documented, no magic numbers in the code).
RIDGE_DEFAULT = 1e-10   # diagonal ridge added to the quadratic normal equations
RBF_EPS_DEFAULT = 0.5   # default Gaussian kernel width parameter
TIE_BREAK = "quadratic"  # recommend_model tie-break preference
SINGULAR_TOL = 1e-12     # pivot threshold for the dense solver


def _check_finite(values, what):
    """Raise ValueError if any value in the flat iterable is not finite."""
    for v in values:
        if not math.isfinite(float(v)):
            raise ValueError("%s contains a non-finite value" % what)


def _validate_dataset(X, y=None):
    """Validate the sample set X and optional response y.

    Returns (n, d): row count and column count. Raises ValueError on an
    empty X, empty or ragged rows, non-finite entries, and a length
    mismatch between X and y.
    """
    if not X:
        raise ValueError("X must not be empty")
    n = len(X)
    d = None
    for i, row in enumerate(X):
        if not row:
            raise ValueError("X row %d is empty" % i)
        if d is None:
            d = len(row)
        elif len(row) != d:
            raise ValueError(
                "ragged X rows: row 0 has %d columns but row %d has %d"
                % (d, i, len(row))
            )
        _check_finite(row, "X")
    if d is None or d == 0:
        raise ValueError("X must have at least one column")
    if y is not None:
        if len(y) != n:
            raise ValueError(
                "len(X) = %d does not match len(y) = %d" % (n, len(y))
            )
        _check_finite(y, "y")
    return n, d


def _validate_point(x, d, what):
    """Validate a single prediction point against a reference dimension."""
    if not x:
        raise ValueError("%s point must not be empty" % what)
    _check_finite(x, what)
    if len(x) != d:
        raise ValueError(
            "%s point has %d columns but the model expects %d"
            % (what, len(x), d)
        )


def solve_linear(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting.

    A is a square list-of-lists of floats, b a matching-length list.
    Returns the solution x as a list of floats. Raises ValueError on a
    non-square or ragged A, a length mismatch in b, non-finite input,
    or a singular matrix (pivot below SINGULAR_TOL after pivoting).
    """
    if not A:
        raise ValueError("solve_linear: empty system")
    n = len(A)
    if len(b) != n:
        raise ValueError(
            "solve_linear: len(A) = %d does not match len(b) = %d"
            % (n, len(b))
        )
    for row in A:
        if len(row) != n:
            raise ValueError("solve_linear: A must be square")
        _check_finite(row, "A")
    _check_finite(b, "b")
    # Augmented matrix, one row per equation, b in the last column.
    aug = [list(map(float, A[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        pivot_row = max(
            range(col, n), key=lambda r: abs(aug[r][col])
        )
        if abs(aug[pivot_row][col]) <= SINGULAR_TOL:
            raise ValueError("solve_linear: singular matrix")
        if pivot_row != col:
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pivot
            if factor != 0.0:
                for c in range(col, n + 1):
                    aug[r][c] -= factor * aug[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = aug[i][n]
        for j in range(i + 1, n):
            s -= aug[i][j] * x[j]
        x[i] = s / aug[i][i]
    return x


def poly_basis_quadratic(x):
    """Return the full quadratic basis row for the point x.

    Order: [1, x_0..x_{d-1}, x_i^2 (squares), x_i * x_j for i < j
    (cross terms)]. Length m = (d + 1) * (d + 2) / 2. Raises ValueError
    on an empty point or non-finite entries.
    """
    if not x:
        raise ValueError("poly_basis_quadratic: input point must not be empty")
    _check_finite(x, "basis input")
    d = len(x)
    basis = [1.0]
    basis += [float(v) for v in x]
    basis += [float(v) * float(v) for v in x]  # squares first
    for i in range(d):                          # then cross terms i < j
        for j in range(i + 1, d):
            basis.append(float(x[i]) * float(x[j]))
    return basis


def _dot(a, b):
    """Scalar product of two equal-length numeric sequences."""
    return sum(float(ai) * float(bi) for ai, bi in zip(a, b))


def fit_quadratic(X, y, ridge=RIDGE_DEFAULT):
    """Fit the ridge-regularized quadratic response surface.

    Assembles the design matrix Phi (n x m) from poly_basis_quadratic
    and solves (Phi^T Phi + ridge I) c = Phi^T y for the coefficients.
    Returns the coefficient list ordered as the basis. Raises ValueError
    when the sample count is below the m basis terms, when ridge is
    negative, or on any malformed input.
    """
    n, d = _validate_dataset(X, y)
    m = (d + 1) * (d + 2) // 2
    if n < m:
        raise ValueError(
            "fit_quadratic: %d samples is fewer than the %d quadratic "
            "basis terms for %d dimensions" % (n, m, d)
        )
    if not math.isfinite(float(ridge)) or ridge < 0.0:
        raise ValueError("fit_quadratic: ridge must be a non-negative finite number")
    phi = [poly_basis_quadratic(row) for row in X]
    ata = [[0.0] * m for _ in range(m)]
    atb = [0.0] * m
    for k, row in enumerate(phi):
        yk = float(y[k])
        for i in range(m):
            atb[i] += row[i] * yk
            ata[i][i] += row[i] * row[i]
            for j in range(i + 1, m):
                ata[i][j] += row[i] * row[j]
    for i in range(m):
        for j in range(i + 1, m):
            ata[j][i] = ata[i][j]
        ata[i][i] += float(ridge)
    return solve_linear(ata, atb)


def predict_quadratic(coeffs, x):
    """Predict the quadratic response at x: dot(coeffs, basis(x))."""
    if not coeffs:
        raise ValueError("predict_quadratic: empty coefficient list")
    _check_finite(coeffs, "coefficients")
    basis = poly_basis_quadratic(x)
    if len(basis) != len(coeffs):
        raise ValueError(
            "predict_quadratic: basis has %d terms but %d coefficients "
            "were given" % (len(basis), len(coeffs))
        )
    return _dot(coeffs, basis)


def rbf_kernel(xi, xj, eps):
    """Gaussian radial basis kernel exp(-eps * ||xi - xj||^2)."""
    if not math.isfinite(float(eps)) or float(eps) <= 0.0:
        raise ValueError("rbf_kernel: eps must be a positive finite number")
    if len(xi) != len(xj):
        raise ValueError(
            "rbf_kernel: center has %d columns but the point has %d"
            % (len(xi), len(xj))
        )
    _check_finite(xi, "kernel center")
    _check_finite(xj, "kernel point")
    dist2 = sum((float(a) - float(b)) ** 2 for a, b in zip(xi, xj))
    return math.exp(-float(eps) * dist2)


def fit_rbf(X, y, eps=RBF_EPS_DEFAULT):
    """Fit the Gaussian RBF interpolant: solve K w = y.

    K_ij = rbf_kernel(x_i, x_j) with the given eps. Returns the weight
    list. Raises ValueError on malformed input or a singular kernel
    (for example duplicated sample rows).
    """
    n, _ = _validate_dataset(X, y)
    if not math.isfinite(float(eps)) or float(eps) <= 0.0:
        raise ValueError("fit_rbf: eps must be a positive finite number")
    kernel = [
        [rbf_kernel(X[i], X[j], eps) for j in range(n)]
        for i in range(n)
    ]
    return solve_linear(kernel, list(y))


def predict_rbf(weights, X, x, eps=RBF_EPS_DEFAULT):
    """Predict with the RBF model: sum_i w_i * K(x_i, x)."""
    n, d = _validate_dataset(X, None)
    if len(weights) != n:
        raise ValueError(
            "predict_rbf: %d weights given for %d sample centers"
            % (len(weights), n)
        )
    _check_finite(weights, "RBF weights")
    if not math.isfinite(float(eps)) or float(eps) <= 0.0:
        raise ValueError("predict_rbf: eps must be a positive finite number")
    _validate_point(x, d, "prediction")
    return sum(
        float(wi) * rbf_kernel(X[i], x, eps) for i, wi in enumerate(weights)
    )


def _fold_predict(fitter, kw, Xtr, ytr, xrow):
    """Fit on a training fold and predict one held-out row.

    Supports the module fit functions fit_quadratic and fit_rbf, and as
    a documented extension any fitter returning an object with a
    predict(x) method.
    """
    if fitter is fit_quadratic:
        coeffs = fit_quadratic(Xtr, ytr, **kw)
        return predict_quadratic(coeffs, xrow)
    if fitter is fit_rbf:
        weights = fit_rbf(Xtr, ytr, **kw)
        eps = kw.get("eps", RBF_EPS_DEFAULT)
        return predict_rbf(weights, Xtr, xrow, eps)
    model = fitter(Xtr, ytr, **kw)
    if callable(getattr(model, "predict", None)):
        return model.predict(xrow)
    raise ValueError(
        "fitter must be fit_quadratic, fit_rbf, or return an object "
        "with a predict(x) method"
    )


def loo_cross_validation(X, y, fitter, **kw):
    """Leave-one-out cross validation of a fitter on (X, y).

    For each row i, fits on all rows except i and predicts row i.
    Returns {"errors": list of absolute errors, "rmse": float,
    "max_abs": float}. fitter is fit_quadratic or fit_rbf (extra
    keyword arguments such as ridge or eps are forwarded).
    """
    n, _ = _validate_dataset(X, y)
    errors = []
    for i in range(n):
        Xtr = X[:i] + X[i + 1:]
        ytr = y[:i] + y[i + 1:]
        pred = _fold_predict(fitter, kw, Xtr, ytr, X[i])
        errors.append(abs(pred - float(y[i])))
    rmse = math.sqrt(sum(e * e for e in errors) / n)
    return {"errors": errors, "rmse": rmse, "max_abs": max(errors)}


def _predict_all(X, y, fitter, kw):
    """Predict every training row with a fitter trained on the full data."""
    return [_fold_predict(fitter, kw, X, y, X[i]) for i in range(len(X))]


def model_quality(X, y, fitter, **kw):
    """In-sample quality metrics of a fitter on the full data.

    Returns {"rmse": float, "max_abs": float, "r2": float} with
    r2 = 1 - SS_res / SS_tot; a zero-variance response reports r2 = 1.0
    when the fit is exact.
    """
    n, _ = _validate_dataset(X, y)
    ymean = sum(float(v) for v in y) / n
    preds = _predict_all(X, y, fitter, kw)
    ss_res = 0.0
    ss_tot = 0.0
    max_abs = 0.0
    for i in range(n):
        resid = float(y[i]) - preds[i]
        ss_res += resid * resid
        max_abs = max(max_abs, abs(resid))
        dev = float(y[i]) - ymean
        ss_tot += dev * dev
    rmse = math.sqrt(ss_res / n)
    if ss_tot > 0.0:
        r2 = 1.0 - ss_res / ss_tot
    else:
        r2 = 1.0 if ss_res <= SINGULAR_TOL else 0.0
    return {"rmse": rmse, "max_abs": max_abs, "r2": r2}


def recommend_model(X, y):
    """Compare quadratic and RBF surrogates by leave-one-out RMSE.

    Returns {"quadratic": loo rmse, "rbf": loo rmse, "best": name,
    "table": [two per-model rows]}. Ties break to the module constant
    TIE_BREAK ("quadratic").
    """
    q_loo = loo_cross_validation(X, y, fit_quadratic, ridge=RIDGE_DEFAULT)
    r_loo = loo_cross_validation(X, y, fit_rbf, eps=RBF_EPS_DEFAULT)
    quad_rmse = q_loo["rmse"]
    rbf_rmse = r_loo["rmse"]
    best = TIE_BREAK if quad_rmse <= rbf_rmse else "rbf"
    table = [
        {"model": "quadratic", "loo_rmse": quad_rmse,
         "max_abs": q_loo["max_abs"]},
        {"model": "rbf", "loo_rmse": rbf_rmse, "max_abs": r_loo["max_abs"]},
    ]
    return {
        "quadratic": quad_rmse,
        "rbf": rbf_rmse,
        "best": best,
        "table": table,
    }


def surrogate_report(X, y, labels=None, new_points=None):
    """Assemble the full surrogate study: fits, metrics, recommendation.

    Returns a dict with the fitted quadratic coefficients and RBF
    weights under "models", the in-sample quality under "quality", the
    leave-one-out results under "loo", the recommend_model verdict
    under "recommendation", the optional dimension "labels", and, when
    new_points is given, per-model predictions under "predictions".
    """
    _validate_dataset(X, y)
    if labels is not None:
        if len(labels) != len(X[0]):
            raise ValueError(
                "%d labels given for %d design variables"
                % (len(labels), len(X[0]))
            )
    coeffs = fit_quadratic(X, y)
    weights = fit_rbf(X, y)
    report = {
        "models": {
            "quadratic": {"coeffs": coeffs},
            "rbf": {"weights": weights},
        },
        "quality": {
            "quadratic": model_quality(X, y, fit_quadratic),
            "rbf": model_quality(X, y, fit_rbf),
        },
        "loo": {
            "quadratic": loo_cross_validation(X, y, fit_quadratic),
            "rbf": loo_cross_validation(X, y, fit_rbf),
        },
        "recommendation": recommend_model(X, y),
        "labels": labels,
    }
    if new_points is not None:
        points = [list(p) for p in new_points]
        for p in points:
            _validate_point(p, len(X[0]), "new")
        report["predictions"] = {
            "points": points,
            "quadratic": [predict_quadratic(coeffs, p) for p in points],
            "rbf": [predict_rbf(weights, X, p) for p in points],
        }
    return report

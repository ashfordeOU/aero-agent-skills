"""Multiple linear regression by the normal equations, pure stdlib.

Fits y = b0 + b1*x1 + ... + bp*xp to n rows of p predictors (p >= 2 for
the multiple-predictor case; p = 1 reduces to ordinary least squares),
always including an intercept column of ones internally. The normal
equations (X^T X) b = X^T y are solved by Gaussian elimination with
partial pivoting, (X^T X)^-1 is formed by Gauss-Jordan elimination for
the coefficient standard errors, and the two-sided t p-values and the
overall F p-value come from an in-leaf regularized incomplete beta
function. No numpy/scipy, no network, no RNG.

Conventions: X holds predictors only (n rows, p columns); y is the
response list of length n; the model needs n > p + 1 so the error
degrees of freedom n - p - 1 are positive. Non-physical inputs raise
ValueError: empty or ragged X, non-numeric entries, an X/y length
mismatch, n <= p + 1, a constant response, and singular systems.

Functions:
    design_matrix(X)
    ols_fit(X, y)
    variance_inflation_factor(X, j)
    predict(coef, x_new)
"""

import math

# Module constants for the linear algebra and special-function machinery.
CF_MAX_ITER = 200       # continued fraction iteration cap
CF_EPS = 3e-12          # continued fraction convergence criterion
FPMIN = 1e-300          # underflow floor for Lentz division guards
PIVOT_TOL = 1e-300      # pivot below which a system is treated as singular
BETA_HALF = 0.5         # second beta parameter of the t CDF identity
VIF_EPS = 1e-12         # r2_j within this of 1 means perfect collinearity


def _finite_number(value, message):
    """Return float(value) or raise ValueError for non-finite input."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError(message)
    return number


def _numeric_matrix(X):
    """Return X as rows of finite floats; ValueError on empty/ragged/bad."""
    if not isinstance(X, (list, tuple)) or len(X) == 0:
        raise ValueError("X must be a non-empty sequence of rows")
    rows = []
    width = None
    for row in X:
        if not isinstance(row, (list, tuple)):
            raise ValueError("each row of X must be a sequence of numbers")
        values = [_finite_number(v, "X entries must be finite numbers")
                  for v in row]
        if width is None:
            width = len(values)
        elif len(values) != width:
            raise ValueError("all rows of X must have the same length")
        rows.append(values)
    if width == 0:
        raise ValueError("X must contain at least one predictor column")
    return rows


def _numeric_response(y):
    """Return y as a list of finite floats; ValueError on empty or bad."""
    if not isinstance(y, (list, tuple)) or len(y) == 0:
        raise ValueError("y must be a non-empty sequence of numbers")
    return [_finite_number(v, "y entries must be finite numbers") for v in y]


def design_matrix(X):
    """Augment each predictor row with a leading intercept column of ones.

    Returns a new list of rows [1.0, x1, ..., xp]; the input X is
    validated and the original rows are left untouched.
    """
    rows = _numeric_matrix(X)
    return [[1.0] + row for row in rows]


def _transpose(matrix):
    """Transpose a rectangular list-of-lists matrix."""
    return [list(col) for col in zip(*matrix)]


def _mat_mul(a, b):
    """Product of two list-of-lists matrices."""
    bt = _transpose(b)
    return [[sum(x * y for x, y in zip(row, col)) for col in bt]
            for row in a]


def _mat_vec_mul(a, v):
    """Product of a matrix and a column vector."""
    return [sum(x * y for x, y in zip(row, v)) for row in a]


def _solve_linear(A, b):
    """Solve A x = b by Gaussian elimination with partial pivoting.

    A square singular system raises ValueError.
    """
    n = len(A)
    aug = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < PIVOT_TOL:
            raise ValueError("singular system: the design is rank deficient")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pv
            if factor != 0.0:
                aug[r] = [x - factor * p for x, p in zip(aug[r], aug[col])]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        total = aug[i][n] - sum(aug[i][j] * x[j] for j in range(i + 1, n))
        x[i] = total / aug[i][i]
    return x


def _invert_matrix(A):
    """Invert a square matrix by Gauss-Jordan with partial pivoting."""
    n = len(A)
    if n == 0:
        raise ValueError("cannot invert an empty matrix")
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
           for i, row in enumerate(A)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < PIVOT_TOL:
            raise ValueError("singular matrix: not invertible")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        aug[col] = [v / divisor for v in aug[col]]
        for r in range(n):
            if r != col:
                factor = aug[r][col]
                if factor != 0.0:
                    aug[r] = [x - factor * p
                              for x, p in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


# ---------------------------------------------------------------------------
# Regularized incomplete beta (the t and F survival layers, in-leaf).
# ---------------------------------------------------------------------------

def _betacf(a, b, x):
    """Lentz continued fraction for the incomplete beta ratio I_x(a, b)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, CF_MAX_ITER + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < CF_EPS:
            break
    return h


def _betai(a, b, x):
    """Regularized incomplete beta I_x(a, b) on [0, 1]."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def _t_p_value(t, df):
    """Two-sided p-value of a t statistic with df error degrees of freedom.

    From I_x(df/2, 1/2) with x = df / (df + t^2), the survival of |t|.
    """
    t = abs(float(t))
    x = df / (df + t * t)
    return _betai(BETA_HALF * df, BETA_HALF, x)


def _f_p_value(f, df1, df2):
    """Upper-tail p-value of an F statistic with df1, df2 degrees of freedom."""
    f = float(f)
    x = (df1 * f) / (df1 * f + df2)
    return 1.0 - _betai(BETA_HALF * df1, BETA_HALF * df2, x)


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def ols_fit(X, y):
    """Fit the multiple linear model y = b0 + sum(bj*xj) by normal equations.

    Returns a dict with keys: coef (length p + 1, intercept first), rss,
    r2, adjusted_r2, sigma2, coef_se, t_stats, p_values, f_stat,
    f_p_value, residuals, fitted. ValueError for non-physical inputs:
    empty or ragged X, non-numeric entries, an X/y length mismatch, and
    n <= p + 1 (no residual degrees of freedom left).
    """
    rows = _numeric_matrix(X)
    response = _numeric_response(y)
    n = len(rows)
    p = len(rows[0])
    if len(response) != n:
        raise ValueError("X and y must have the same number of rows")
    if n <= p + 1:
        raise ValueError("need more than p + 1 = %d rows for %d predictors"
                         % (p + 1, p))
    design = [[1.0] + row for row in rows]
    xt = _transpose(design)
    xtx = _mat_mul(xt, design)
    xty = _mat_vec_mul(xt, response)
    coef = _solve_linear(xtx, xty)
    inv_xtx = _invert_matrix(xtx)
    fitted = _mat_vec_mul(design, coef)
    residuals = [yi - fi for yi, fi in zip(response, fitted)]
    rss = sum(r * r for r in residuals)
    mean_y = sum(response) / n
    tss = sum((yi - mean_y) ** 2 for yi in response)
    if tss == 0.0:
        raise ValueError("constant response: total sum of squares is zero")
    r2 = 1.0 - rss / tss
    df_error = n - p - 1
    adjusted_r2 = 1.0 - (1.0 - r2) * (n - 1) / df_error
    sigma2 = rss / df_error
    if sigma2 == 0.0:
        raise ValueError("zero residual variance: the fit is exact")
    coef_se = [math.sqrt(sigma2 * inv_xtx[i][i]) for i in range(p + 1)]
    t_stats = [coef[i] / coef_se[i] for i in range(p + 1)]
    p_values = [_t_p_value(t_stats[i], df_error) for i in range(p + 1)]
    f_stat = ((tss - rss) / p) / (rss / df_error)
    f_p_value = _f_p_value(f_stat, p, df_error)
    return {
        "coef": coef,
        "rss": rss,
        "r2": r2,
        "adjusted_r2": adjusted_r2,
        "sigma2": sigma2,
        "coef_se": coef_se,
        "t_stats": t_stats,
        "p_values": p_values,
        "f_stat": f_stat,
        "f_p_value": f_p_value,
        "residuals": residuals,
        "fitted": fitted,
    }


def variance_inflation_factor(X, j):
    """VIF of predictor j: 1 / (1 - R2_j), R2_j from regressing column j
    on the other predictors with an intercept.

    A single-predictor model has no other column to regress on and
    returns 1.0. Perfect collinearity (R2_j within VIF_EPS of 1) and an
    out-of-range j raise ValueError.
    """
    rows = _numeric_matrix(X)
    p = len(rows[0])
    if isinstance(j, bool) or not isinstance(j, int):
        raise ValueError("j must be an integer predictor index")
    if not 0 <= j < p:
        raise ValueError("predictor index j out of range for p = %d" % p)
    if p == 1:
        return 1.0
    others = [[v for k, v in enumerate(row) if k != j] for row in rows]
    target = [row[j] for row in rows]
    r2_j = ols_fit(others, target)["r2"]
    if r2_j >= 1.0 - VIF_EPS:
        raise ValueError("perfect collinearity: predictor %d is a linear "
                         "combination of the others" % j)
    return 1.0 / (1.0 - r2_j)


def predict(coef, x_new):
    """Evaluate the fitted model at a new design point (predictors only).

    coef holds p + 1 entries (intercept first); x_new must hold the p
    predictor values. Length mismatch or non-numeric input raises
    ValueError.
    """
    if not isinstance(coef, (list, tuple)):
        raise ValueError("coef must be a sequence of numbers")
    if not isinstance(x_new, (list, tuple)):
        raise ValueError("x_new must be a sequence of predictor values")
    coefficients = [_finite_number(c, "coef entries must be finite numbers")
                    for c in coef]
    point = [_finite_number(v, "x_new entries must be finite numbers")
             for v in x_new]
    if len(point) != len(coefficients) - 1:
        raise ValueError("x_new needs one value per predictor "
                         "(got %d, need %d)"
                         % (len(point), len(coefficients) - 1))
    return coefficients[0] + sum(c * x
                                 for c, x in zip(coefficients[1:], point))

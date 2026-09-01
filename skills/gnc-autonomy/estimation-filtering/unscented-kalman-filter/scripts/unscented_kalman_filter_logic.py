"""Unscented Kalman Filter (UKF) core: sigma-point nonlinear state estimation.

Pure Python standard library only (no numpy, no network). All linear
algebra is list-based: vectors are lists of floats, matrices are lists
of rows (lists of floats). The implementation follows the Van der Merwe
scaled unscented transform (Wan and Van der Merwe, 2000/2001): a set of
2n + 1 sigma points is drawn from the state mean and covariance, each
point is propagated through the nonlinear dynamics and measurement
functions, and the weighted sample mean and covariance reconstruct the
posterior moments.

Deterministic: no random numbers, no external state, results depend
only on the inputs and the tuning parameters.

Public API
----------
generate_sigma_points(x, P, alpha, beta, kappa)
sigma_point_weights(n, alpha, beta, kappa)
weighted_moments(points, wm, wc, x_ref)
predict(x, P, f, Q, alpha, beta, kappa)
update(x, P, z, h, R, alpha, beta, kappa)
nees(x_est, P_est, x_true)
UKFFilter                 (stateful convenience wrapper)
constant_velocity_dynamics(x, dt)
bearing_range_measurement(x)
"""

import math

# ---------------------------------------------------------------------------
# List-based vector and matrix helpers
# ---------------------------------------------------------------------------


def vec_add(a, b):
    """Element-wise sum of two vectors."""
    return [ai + bi for ai, bi in zip(a, b)]


def vec_sub(a, b):
    """Element-wise difference a - b of two vectors."""
    return [ai - bi for ai, bi in zip(a, b)]


def vec_scale(a, s):
    """Scale every element of vector a by scalar s."""
    return [ai * s for ai in a]


def vec_dot(a, b):
    """Dot product of two vectors."""
    return sum(ai * bi for ai, bi in zip(a, b))


def mat_scale(m, s):
    """Scale every element of matrix m by scalar s."""
    return [[v * s for v in row] for row in m]


def mat_add(m1, m2):
    """Element-wise sum of two matrices of equal shape."""
    return [[a + b for a, b in zip(r1, r2)] for r1, r2 in zip(m1, m2)]


def mat_transpose(m):
    """Transpose of matrix m (list of rows)."""
    if not m:
        return []
    return [[m[i][j] for i in range(len(m))] for j in range(len(m[0]))]


def mat_mul(m1, m2):
    """Matrix product m1 @ m2 for compatible shapes."""
    t2 = mat_transpose(m2)
    return [[vec_dot(row, col) for col in t2] for row in m1]


def mat_vec_mul(m, v):
    """Matrix times column vector: m @ v as a vector."""
    return [vec_dot(row, v) for row in m]


def outer(a, b):
    """Outer product a * b^T as a matrix."""
    return [[ai * bj for bj in b] for ai in a]


def cholesky_lower(p):
    """Lower-triangular Cholesky factor L with L L^T = P.

    P must be symmetric positive definite. Returns a new matrix; raises
    ValueError if a pivot is non-positive (numerically indefinite P).
    """
    n = len(p)
    l = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = p[i][j] - sum(l[i][k] * l[j][k] for k in range(j))
            if i == j:
                if s <= 0.0:
                    raise ValueError(
                        "covariance not positive definite at pivot %d" % i
                    )
                l[i][j] = math.sqrt(s)
            else:
                l[i][j] = s / l[j][j]
    return l


def mat_inv(m):
    """Inverse of square matrix m by Gauss-Jordan elimination with
    partial pivoting. Raises ValueError when singular."""
    n = len(m)
    if n == 0:
        raise ValueError("empty matrix")
    aug = [row[:] + [1.0 if i == j else 0.0 for j in range(n)]
           for i, row in enumerate(m)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-300:
            raise ValueError("matrix is singular")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        d = aug[col][col]
        aug[col] = [v / d for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor != 0.0:
                aug[r] = [vr - factor * vc
                          for vr, vc in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def mat_trace(m):
    """Trace of square matrix m."""
    return sum(m[i][i] for i in range(len(m)))


# ---------------------------------------------------------------------------
# Scaled unscented transform: sigma points and weights
# ---------------------------------------------------------------------------


def sigma_point_weights(n, alpha, beta, kappa):
    """Mean (wm) and covariance (wc) weights for 2n+1 sigma points.

    Scaled unscented transform parameters:
      lambda_ = alpha^2 * (n + kappa) - n
      wm[0]   = lambda_ / (n + lambda_)
      wc[0]   = wm[0] + (1 - alpha^2 + beta)
      wm[i]   = wc[i] = 1 / (2 * (n + lambda_))   for i = 1..2n

    Returns (wm, wc, gamma) where gamma = sqrt(n + lambda_) is the
    sigma-point spread factor applied to the covariance columns.
    """
    lam = alpha * alpha * (n + kappa) - n
    denom = n + lam
    wm = [lam / denom]
    wc = [lam / denom + (1.0 - alpha * alpha + beta)]
    w_rest = 1.0 / (2.0 * denom)
    for _ in range(2 * n):
        wm.append(w_rest)
        wc.append(w_rest)
    gamma = math.sqrt(denom)
    return wm, wc, gamma


def generate_sigma_points(x, p, alpha, beta, kappa):
    """Return the 2n+1 sigma points around mean x with covariance p.

    X[0] = x
    X[i]     = x + gamma * col_i(L)   for i = 1..n
    X[n + i] = x - gamma * col_i(L)   for i = 1..n

    where L is the lower Cholesky factor of p (L L^T = p) and col_i(L)
    is the i-th column. The pair (i, n+i) is symmetric about x.
    """
    n = len(x)
    wm, wc, gamma = sigma_point_weights(n, alpha, beta, kappa)
    del wm, wc  # weights are computed separately by callers
    l = cholesky_lower(p)
    cols = [[l[i][j] for i in range(n)] for j in range(n)]
    points = [x[:]]
    for j in range(n):
        points.append(vec_add(x, vec_scale(cols[j], gamma)))
    for j in range(n):
        points.append(vec_sub(x, vec_scale(cols[j], gamma)))
    return points


def weighted_moments(points, wm, wc, x_ref=None):
    """Weighted mean and covariance of sigma points.

    mean = sum_i wm[i] * points[i]
    cov  = sum_i wc[i] * (points[i] - mean) (points[i] - mean)^T

    When x_ref is given the covariance is computed about x_ref instead
    of the weighted mean (used for the cross covariance in update).
    Returns (mean, cov).
    """
    n = len(points[0])
    mean = [0.0] * n
    for w, pt in zip(wm, points):
        mean = vec_add(mean, vec_scale(pt, w))
    center = x_ref if x_ref is not None else mean
    cov = [[0.0] * n for _ in range(n)]
    for w, pt in zip(wc, points):
        d = vec_sub(pt, center)
        cov = mat_add(cov, mat_scale(outer(d, d), w))
    return mean, cov


# ---------------------------------------------------------------------------
# UKF predict and update
# ---------------------------------------------------------------------------


def predict(x, p, f, q, alpha=1e-3, beta=2.0, kappa=0.0):
    """UKF predict step through nonlinear dynamics f.

    f(point) returns the propagated sigma point (a list). The predicted
    mean and covariance are the weighted moments of the propagated
    points plus the dynamics noise covariance q:
      x_pred = sum_i wm[i] * f(X[i])
      P_pred = sum_i wc[i] (f(X[i]) - x_pred)(...)^T + q

    Returns (x_pred, P_pred).
    """
    n = len(x)
    wm, wc, _ = sigma_point_weights(n, alpha, beta, kappa)
    points = generate_sigma_points(x, p, alpha, beta, kappa)
    prop = [f(pt) for pt in points]
    x_pred, p_pred = weighted_moments(prop, wm, wc)
    p_pred = mat_add(p_pred, q)
    return x_pred, p_pred


def update(x, p, z, h, r, alpha=1e-3, beta=2.0, kappa=0.0):
    """UKF update step through nonlinear measurement function h.

    h(point) returns the predicted measurement vector for one sigma
    point. Steps:
      Z_i    = h(X_i)                      predicted measurements
      z_mean = sum_i wm[i] Z_i
      S      = sum_i wc[i] (Z_i - z_mean)(...)^T + r   innovation cov
      P_xz   = sum_i wc[i] (X_i - x)(Z_i - z_mean)^T    cross cov
      K      = P_xz S^-1                                Kalman gain
      x_new  = x + K (z - z_mean)
      P_new  = P - K S K^T

    Returns (x_new, P_new, z_mean, S, K).
    """
    n = len(x)
    m = len(z)
    wm, wc, _ = sigma_point_weights(n, alpha, beta, kappa)
    points = generate_sigma_points(x, p, alpha, beta, kappa)
    z_points = [h(pt) for pt in points]
    z_mean, s = weighted_moments(z_points, wm, wc)
    s = mat_add(s, r)
    p_xz = [[0.0] * m for _ in range(n)]
    for w, xp, zp in zip(wc, points, z_points):
        dx = vec_sub(xp, x)
        dz = vec_sub(zp, z_mean)
        for i in range(n):
            for j in range(m):
                p_xz[i][j] += w * dx[i] * dz[j]
    s_inv = mat_inv(s)
    k = mat_mul(p_xz, s_inv)
    innov = vec_sub(z, z_mean)
    x_new = vec_add(x, mat_vec_mul(k, innov))
    # Joseph-free Joseph form: P_new = P - K S K^T (standard UKF)
    p_new = mat_sub(p, mat_mul(mat_mul(k, s), mat_transpose(k)))
    return x_new, p_new, z_mean, s, k


def mat_sub(a, b, negate=False):
    """Element-wise difference a - b (or b - a when negate=True)."""
    if negate:
        return [[b_ - a_ for a_, b_ in zip(ra, rb)] for ra, rb in zip(a, b)]
    return [[a_ - b_ for a_, b_ in zip(ra, rb)] for ra, rb in zip(a, b)]


def nees(x_est, p_est, x_true):
    """Normalized estimation error squared (NEES) consistency metric.

    NEES = (x_est - x_true)^T P_est^-1 (x_est - x_true).

    For a consistent filter the expected value is the state dimension
    n; averaged over many Monte Carlo runs NEES should sit near n
    (overly optimistic if far above, pessimistic if far below).
    """
    d = vec_sub(x_est, x_true)
    return vec_dot(d, mat_vec_mul(mat_inv(p_est), d))


# ---------------------------------------------------------------------------
# Convenience stateful filter
# ---------------------------------------------------------------------------


class UKFFilter(object):
    """Stateful UKF: hold x and P, step through measurements.

    f and h are callables with signatures f(point) and h(point);
    q and r are the dynamics and sensor noise covariance matrices.
    """

    def __init__(self, x0, p0, f, h, q, r,
                 alpha=1e-3, beta=2.0, kappa=0.0):
        self.x = [float(v) for v in x0]
        self.p = [row[:] for row in p0]
        self.f = f
        self.h = h
        self.q = [row[:] for row in q]
        self.r = [row[:] for row in r]
        self.alpha = alpha
        self.beta = beta
        self.kappa = kappa
        self.innovation = None
        self.s = None
        self.k = None

    def predict(self):
        """Advance the state through the dynamics model."""
        self.x, self.p = predict(
            self.x, self.p, self.f, self.q,
            self.alpha, self.beta, self.kappa,
        )
        return self.x, self.p

    def update(self, z):
        """Correct the state with measurement z."""
        self.x, self.p, z_mean, self.s, self.k = update(
            self.x, self.p, z, self.h, self.r,
            self.alpha, self.beta, self.kappa,
        )
        self.innovation = [zi - zmi for zi, zmi in zip(z, z_mean)]
        return self.x, self.p

    def step(self, z):
        """Predict then update with measurement z."""
        self.predict()
        return self.update(z)


# ---------------------------------------------------------------------------
# Example models: constant-velocity dynamics and bearing/range measurement
# ---------------------------------------------------------------------------


def constant_velocity_dynamics(x, dt=1.0):
    """Constant-velocity dynamics on state (px, py, vx, vy).

    Position advances by velocity times dt; velocity is unchanged.
    """
    px, py, vx, vy = x
    return [px + dt * vx, py + dt * vy, vx, vy]


def bearing_range_measurement(x):
    """Nonlinear measurement: range and bearing from state (px, py, ...).

    range  = sqrt(px^2 + py^2)
    bearing = atan2(py, px)

    Only the first two state elements are observed; the mapping is
    nonlinear in the state, which is why a sigma-point filter is used.
    """
    px, py = x[0], x[1]
    rng = math.sqrt(px * px + py * py)
    brg = math.atan2(py, px)
    return [rng, brg]

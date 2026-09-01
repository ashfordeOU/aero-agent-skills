#!/usr/bin/env python3
"""Extended Kalman Filter (EKF) core: Jacobian-linearized nonlinear estimation.

Pure Python standard library only (no numpy, no network). Vectors are
lists of floats, matrices are lists of rows (lists of floats). The EKF
linearizes the nonlinear dynamics f and the measurement model h about
the current estimate with the Jacobians F and H (computed here by
central finite differences), then runs the standard Kalman predict and
update recursion:

  predict:  x_pred = f(x);         P_pred = F P F^T + Q
  update:   y = z - h(x_pred);     S = H P H^T + R
            K = P H^T S^-1;        x_new = x_pred + K y
            P_new = (I - K H) P

Deterministic: no random numbers, no external state; results depend
only on the inputs and the finite-difference step eps.

Public API
----------
vec_add, vec_sub, vec_scale, vec_dot
mat_add, mat_sub, mat_scale, mat_transpose, mat_identity
mat_vec_mul, mat_mul, mat_inverse
jacobian, jacobian_f, jacobian_h
ekf_predict, ekf_update
EKFFilter                 (stateful convenience wrapper)
run_ekf
constant_velocity_dynamics, bearing_range_measurement
scalar_nonlinear_dynamics, scalar_nonlinear_measurement
"""

import math

# ---------------------------------------------------------------------------
# Vector and matrix helpers (list based)
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


def mat_add(a, b):
    """Element-wise sum of two matrices."""
    return [[ai + bi for ai, bi in zip(ra, rb)] for ra, rb in zip(a, b)]


def mat_sub(a, b):
    """Element-wise difference a - b of two matrices."""
    return [[ai - bi for ai, bi in zip(ra, rb)] for ra, rb in zip(a, b)]


def mat_transpose(m):
    """Matrix transpose; m is a list of rows."""
    if not m:
        return []
    return [[m[i][j] for i in range(len(m))] for j in range(len(m[0]))]


def mat_identity(n):
    """n x n identity matrix."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def mat_vec_mul(m, v):
    """Matrix m times vector v."""
    return [sum(mi[j] * v[j] for j in range(len(v))) for mi in m]


def mat_mul(a, b):
    """Matrix product a * b (a is k x n, b is n x m)."""
    bt = mat_transpose(b)
    return [[vec_dot(ra, cb) for cb in bt] for ra in a]


def mat_inverse(m):
    """Matrix inverse by Gauss-Jordan elimination with partial pivoting.

    m must be a non-empty square matrix of numbers. A numerically zero
    pivot (exactly 0.0 or below 1e-300 in absolute value) raises
    ValueError: the matrix is singular.
    """
    n = len(m)
    if n == 0 or any(len(row) != n for row in m):
        raise ValueError("matrix must be non-empty and square")
    aug = [
        row[:] + [1.0 if i == j else 0.0 for j in range(n)]
        for i, row in enumerate(m)
    ]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-300:
            raise ValueError("singular matrix (zero pivot at column %d)" % col)
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        aug[col] = [v / pv for v in aug[col]]
        for r in range(n):
            if r == col:
                continue
            factor = aug[r][col]
            if factor != 0.0:
                aug[r] = [a - factor * b for a, b in zip(aug[r], aug[col])]
    return [row[n:] for row in aug]


def _trace(m):
    """Trace of a square matrix (test helper)."""
    return sum(m[i][i] for i in range(len(m)))


# ---------------------------------------------------------------------------
# Numeric Jacobians (central finite differences)
# ---------------------------------------------------------------------------


def jacobian(f, x, eps=1e-6):
    """Numeric Jacobian of f at x by central finite differences.

    f may return a scalar or a vector; the result is an (m x n) matrix
    where m is the output dimension and n = len(x).
    """
    n = len(x)
    fx = f(x)
    scalar_out = isinstance(fx, (int, float))
    m = 1 if scalar_out else len(fx)
    J = [[0.0] * n for _ in range(m)]
    for j in range(n):
        xp = list(x)
        xm = list(x)
        xp[j] += eps
        xm[j] -= eps
        fp = f(xp)
        fm = f(xm)
        if scalar_out:
            J[0][j] = (fp - fm) / (2.0 * eps)
        else:
            for i in range(m):
                J[i][j] = (fp[i] - fm[i]) / (2.0 * eps)
    return J


def jacobian_f(f, x, eps=1e-6):
    """State-transition Jacobian F of the dynamics f at x."""
    return jacobian(f, x, eps)


def jacobian_h(h, x, eps=1e-6):
    """Measurement Jacobian H of the model h at x."""
    return jacobian(h, x, eps)


# ---------------------------------------------------------------------------
# EKF predict and update
# ---------------------------------------------------------------------------


def _as_vector(v):
    """Accept a bare number as a one-element vector."""
    if isinstance(v, (int, float)):
        return [float(v)]
    return [float(vi) for vi in v]


def ekf_predict(x, P, f, Q, eps=1e-6):
    """EKF predict step.

    x: state vector; P: state covariance; f: nonlinear dynamics
    callable; Q: dynamics noise covariance. Computes F = jacobian_f(f,
    x), x_pred = f(x), P_pred = F P F^T + Q. Returns a dict with keys
    x, P, F.
    """
    F = jacobian_f(f, x, eps)
    x_pred = _as_vector(f(x))
    P_pred = mat_add(mat_mul(mat_mul(F, P), mat_transpose(F)), Q)
    return {"x": x_pred, "P": P_pred, "F": F}


def ekf_update(x, P, z, h, R, eps=1e-6):
    """EKF update step at the predicted state.

    x: predicted state; P: predicted covariance; z: measurement (scalar
    or vector); h: nonlinear measurement callable; R: sensor noise
    covariance. Computes H = jacobian_h(h, x), the innovation
    y = z - h(x), the innovation covariance S = H P H^T + R, the gain
    K = P H^T S^-1, then x_new = x + K y and P_new = (I - K H) P. A
    singular S raises ValueError (increase R or check the measurement
    model). Returns a dict with keys x, P, y, S, K, H.
    """
    H = jacobian_h(h, x, eps)
    hx = _as_vector(h(x))
    z = _as_vector(z)
    y = vec_sub(z, hx)
    S = mat_add(mat_mul(mat_mul(H, P), mat_transpose(H)), R)
    try:
        S_inv = mat_inverse(S)
    except ValueError:
        raise ValueError(
            "innovation covariance S is singular; increase R or check the "
            "measurement model"
        ) from None
    K = mat_mul(mat_mul(P, mat_transpose(H)), S_inv)
    x_new = vec_add(x, mat_vec_mul(K, y))
    KH = mat_mul(K, H)
    P_new = mat_mul(mat_sub(mat_identity(len(x)), KH), P)
    return {"x": x_new, "P": P_new, "y": y, "S": S, "K": K, "H": H}


# ---------------------------------------------------------------------------
# Stateful filter and batch runner
# ---------------------------------------------------------------------------


class EKFFilter(object):
    """Stateful EKF: predict then update once per measurement step.

    Holds the current state x and covariance P, plus the last
    innovation y, innovation covariance S, and gain K for inspection.
    """

    def __init__(self, x0, P0, f, h, Q, R, eps=1e-6):
        self.x = [float(v) for v in x0]
        self.P = [row[:] for row in P0]
        self.f = f
        self.h = h
        self.Q = Q
        self.R = R
        self.eps = eps
        self.innovation = None
        self.S = None
        self.K = None

    def step(self, z):
        """Run one predict-update cycle with measurement z."""
        pred = ekf_predict(self.x, self.P, self.f, self.Q, self.eps)
        upd = ekf_update(pred["x"], pred["P"], z, self.h, self.R, self.eps)
        self.x = upd["x"]
        self.P = upd["P"]
        self.innovation = upd["y"]
        self.S = upd["S"]
        self.K = upd["K"]
        return self.x


def run_ekf(zs, x0, P0, f, h, Q, R, eps=1e-6):
    """Run the EKF over a measurement batch.

    zs: iterable of measurements. Returns a list with one dict per
    step: keys x, P, y, S, K (the state and covariance after that
    step's update).
    """
    filt = EKFFilter(x0, P0, f, h, Q, R, eps)
    out = []
    for z in zs:
        filt.step(z)
        out.append(
            {
                "x": filt.x,
                "P": filt.P,
                "y": filt.innovation,
                "S": filt.S,
                "K": filt.K,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Example models (deterministic, offline)
# ---------------------------------------------------------------------------


def constant_velocity_dynamics(x, dt):
    """Constant-velocity kinematics: x = [px, py, vx, vy]."""
    px, py, vx, vy = x
    return [px + vx * dt, py + vy * dt, vx, vy]


def bearing_range_measurement(x):
    """Nonlinear range/bearing measurement of x = [px, py, vx, vy].

    Returns [range, bearing] with bearing in radians via atan2.
    """
    px, py = x[0], x[1]
    return [math.hypot(px, py), math.atan2(py, px)]


def scalar_nonlinear_dynamics(x):
    """Scalar nonlinear drift: x_(k+1) = x + 0.1 * sin(x)."""
    return [x[0] + 0.1 * math.sin(x[0])]


def scalar_nonlinear_measurement(x):
    """Scalar quadratic measurement: z = x^2 / 4."""
    return [x[0] * x[0] / 4.0]

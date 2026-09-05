"""Loosely coupled INS/GNSS error-state integration filter logic (wave-40 leaf).

Pure stdlib implementation of the 5-state horizontal-plane error-state
(psi-angle) integration filter. State vector
x = [dr_N, dr_E, dv_N, dv_E, dpsi]: north position error (m), east
position error (m), north velocity error (m/s), east velocity error
(m/s), heading error about the vertical (rad). The INS provides the
navigation solution and the filter estimates the error of that
solution, correcting it at each GNSS position fix.

Continuous psi-angle error model for level flight with horizontal
specific force (f_N, f_E), vertical channel nulled:

  dr_dot_N = dv_N
  dr_dot_E = dv_E
  dv_dot_N = f_E * dpsi
  dv_dot_E = -f_N * dpsi
  dpsi_dot = 0

Standard engineering method (Gelb; Brown and Hwang style error-state
filtering, ARP4754A reference-only). Deterministic, no RNG, stdlib
only.
"""

import math

# State dimension of the error-state filter.
STATE_SIZE = 5

# 5x5 identity used by the predict and update covariance recursions.
IDENTITY_5 = [
    [1.0, 0.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 1.0],
]

# Determinant floor below which a 2x2 matrix is treated as singular.
TWO_BY_TWO_DET_FLOOR = 1e-12


def _is_flat(row_or_matrix):
    """True when the operand is a flat vector rather than a list of lists."""
    return not isinstance(row_or_matrix[0], list)


def mat_mul(a, b):
    """Multiply matrices a (m x n) and b (n x p).

    A flat list operand is treated as a column vector: a flat b is an
    n x 1 column and a flat a is an m x 1 column. The product of a
    matrix with a flat right operand is returned as a flat list.
    Raises ValueError when the inner dimensions do not agree.
    """
    a_flat = _is_flat(a)
    b_flat = _is_flat(b)
    a_mat = [[v] for v in a] if a_flat else a
    b_mat = [[v] for v in b] if b_flat else b
    rows_a, cols_a = len(a_mat), len(a_mat[0])
    rows_b, cols_b = len(b_mat), len(b_mat[0])
    if cols_a != rows_b:
        raise ValueError(
            "mat_mul shape mismatch: inner dimensions %d and %d differ"
            % (cols_a, rows_b)
        )
    out = [
        [sum(a_mat[i][k] * b_mat[k][j] for k in range(cols_a))
         for j in range(cols_b)]
        for i in range(rows_a)
    ]
    if b_flat:
        return [row[0] for row in out]
    return out


def mat_add(a, b):
    """Element-wise matrix sum of two identically shaped operands.

    Flat lists of equal length are summed element-wise and returned as
    a flat list. Raises ValueError on a shape mismatch.
    """
    a_flat = _is_flat(a)
    b_flat = _is_flat(b)
    if a_flat != b_flat:
        raise ValueError("mat_add shape mismatch: mixed flat and matrix operands")
    if a_flat:
        if len(a) != len(b):
            raise ValueError(
                "mat_add shape mismatch: lengths %d and %d differ" % (len(a), len(b))
            )
        return [a[i] + b[i] for i in range(len(a))]
    if len(a) != len(b) or (len(a) and len(a[0]) != len(b[0])):
        raise ValueError("mat_add shape mismatch: operand shapes differ")
    return [
        [a[i][j] + b[i][j] for j in range(len(a[0]))]
        for i in range(len(a))
    ]


def mat_transpose(a):
    """Transpose matrix a; a flat list is treated as a column vector
    and transposes into a single-row matrix."""
    if _is_flat(a):
        return [list(a)]
    return [list(col) for col in zip(*a)]


def mat_scale(c, a):
    """Scale every entry of matrix or flat vector a by the scalar c,
    preserving the operand shape."""
    if _is_flat(a):
        return [c * v for v in a]
    return [[c * v for v in row] for row in a]


def mat_inverse_2x2(m):
    """Inverse of a 2x2 matrix [[a, b], [c, d]] via the determinant.

    Raises ValueError when the absolute determinant falls below 1e-12.
    """
    if len(m) != 2 or len(m[0]) != 2 or len(m[1]) != 2:
        raise ValueError("mat_inverse_2x2 requires a 2x2 matrix")
    a, b = m[0][0], m[0][1]
    c, d = m[1][0], m[1][1]
    det = a * d - b * c
    if abs(det) < TWO_BY_TWO_DET_FLOOR:
        raise ValueError(
            "mat_inverse_2x2 singular: |det| = %.3e below floor" % abs(det)
        )
    return [[d / det, -b / det], [-c / det, a / det]]


def error_state_matrix(f_north_m_s2, f_east_m_s2):
    """Continuous 5x5 error-state matrix F of the psi-angle model.

    Row order dr_N, dr_E, dv_N, dv_E, dpsi. With f_E the specific
    force on the east axis the dv_N row couples dpsi through f_E, and
    with f_N on the north axis the dv_E row couples dpsi through -f_N.
    """
    return [
        [0.0, 0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 0.0, f_east_m_s2],
        [0.0, 0.0, 0.0, 0.0, -f_north_m_s2],
        [0.0, 0.0, 0.0, 0.0, 0.0],
    ]


def state_transition_matrix(f_north_m_s2, f_east_m_s2, dt_s):
    """First-order discrete 5x5 state transition matrix Phi = I + F*dt.

    Valid for small dt relative to the dynamics time scale; the model
    is documented as a first-order Euler discretization. Raises
    ValueError when dt_s is not positive.
    """
    if dt_s <= 0.0:
        raise ValueError("state_transition_matrix: dt_s must be positive")
    f = error_state_matrix(f_north_m_s2, f_east_m_s2)
    return [
        [IDENTITY_5[i][j] + f[i][j] * dt_s for j in range(STATE_SIZE)]
        for i in range(STATE_SIZE)
    ]


def predict_step(x, p, phi, q):
    """One predict step: x_next = Phi x, P_next = Phi P Phi^T + Q.

    x is the flat 5-state error vector, p, phi and q are 5x5
    matrices. Raises ValueError when x is not length 5 or p or q are
    not 5x5.
    """
    if len(x) != STATE_SIZE:
        raise ValueError(
            "predict_step: x must be length %d, got %d" % (STATE_SIZE, len(x))
        )
    for name, m in (("p", p), ("q", q), ("phi", phi)):
        if len(m) != STATE_SIZE or any(len(row) != STATE_SIZE for row in m):
            raise ValueError(
                "predict_step: %s must be %dx%d" % (name, STATE_SIZE, STATE_SIZE)
            )
    x_next = mat_mul(phi, x)
    p_next = mat_add(
        mat_mul(mat_mul(phi, p), mat_transpose(phi)), q
    )
    return x_next, p_next


def _check_update_shapes(x, p, z, h, r):
    """Shape guards shared by the measurement update entry points."""
    if len(x) != STATE_SIZE:
        raise ValueError(
            "measurement_update: x must be length %d, got %d"
            % (STATE_SIZE, len(x))
        )
    if len(p) != STATE_SIZE or any(len(row) != STATE_SIZE for row in p):
        raise ValueError(
            "measurement_update: p must be %dx%d" % (STATE_SIZE, STATE_SIZE)
        )
    if len(z) != 2:
        raise ValueError("measurement_update: z must be length 2")
    if len(h) != 2 or any(len(row) != STATE_SIZE for row in h):
        raise ValueError("measurement_update: h must be 2x%d" % STATE_SIZE)
    if len(r) != 2 or any(len(row) != 2 for row in r):
        raise ValueError("measurement_update: r must be 2x2")


def measurement_update(x, p, z, h, r):
    """Kalman measurement update with a 2-channel GNSS position fix.

    z is the length-2 measurement of the north and east position
    errors, h the 2x5 observation matrix (position-error channels), r
    the 2x2 measurement noise. Implements the standard update

      innovation = z - H x
      S = H P H^T + R
      K = P H^T S^-1
      x_new = x + K * innovation
      P_new = (I - K H) P   (plain form)

    Returns (x_new, p_new, innovation, kalman_gain) with kalman_gain
    the 5x2 gain matrix. Raises ValueError on any shape mismatch.
    """
    _check_update_shapes(x, p, z, h, r)
    innovation = [
        z[j] - sum(h[j][k] * x[k] for k in range(STATE_SIZE))
        for j in range(2)
    ]
    hp = mat_mul(h, p)  # 2x5
    s = mat_add(mat_mul(hp, mat_transpose(h)), r)  # 2x2
    s_inv = mat_inverse_2x2(s)
    kalman_gain = mat_mul(mat_mul(p, mat_transpose(h)), s_inv)  # 5x2
    x_new = mat_add(x, mat_mul(kalman_gain, innovation))
    kh = mat_mul(kalman_gain, h)  # 5x5
    p_new = mat_mul(mat_add(IDENTITY_5, mat_scale(-1.0, kh)), p)
    return x_new, p_new, innovation, kalman_gain


def _diagonal(values):
    """Build a square diagonal matrix from a flat list of values."""
    n = len(values)
    return [[values[i] if i == j else 0.0 for j in range(n)] for i in range(n)]


def run_ins_gnss_profile(
    dt_s,
    f_north_m_s2,
    f_east_m_s2,
    initial_error,
    gnss_times,
    p0,
    q,
    r,
    noise_free_innovations=True,
):
    """Run the error-state filter over a level-flight profile.

    Propagates the true INS error with the same state transition
    matrix, predicts the filter between the GNSS fixes, and applies a
    noise-free GNSS position observation z = [dr_N_true, dr_E_true] at
    every listed time. Returns

      {"updates": [(t, innovation_N, innovation_E, est_dr_N,
                    est_dr_E), ...],
       "final_estimate": x,
       "final_true": x_true}

    Deterministic: all arithmetic is float64 closed form with no RNG,
    so two runs return identical dicts. Stochastic measurement noise
    is out of scope, so noise_free_innovations=False raises
    ValueError.
    """
    if not noise_free_innovations:
        raise ValueError(
            "run_ins_gnss_profile: only noise-free innovations are "
            "implemented (stochastic draws are out of scope)"
        )
    if dt_s <= 0.0:
        raise ValueError("run_ins_gnss_profile: dt_s must be positive")
    if len(initial_error) != STATE_SIZE:
        raise ValueError(
            "run_ins_gnss_profile: initial_error must be length %d"
            % STATE_SIZE
        )
    if not gnss_times:
        raise ValueError("run_ins_gnss_profile: gnss_times must not be empty")
    phi = state_transition_matrix(f_north_m_s2, f_east_m_s2, dt_s)
    h = [[1.0, 0.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0, 0.0]]
    x_true = list(initial_error)
    x_est = [0.0] * STATE_SIZE
    p = [row[:] for row in p0]
    times = sorted(set(round(t, 9) for t in gnss_times))
    updates = []
    horizon = times[-1]
    steps = int(round(horizon / dt_s))
    for k in range(1, steps + 1):
        t = round(k * dt_s, 9)
        x_true = mat_mul(phi, x_true)
        x_est, p = predict_step(x_est, p, phi, q)
        if t in times:
            z = x_true[:2]
            x_est, p, innovation, _ = measurement_update(x_est, p, z, h, r)
            updates.append(
                (t, innovation[0], innovation[1], x_est[0], x_est[1])
            )
    return {"updates": updates, "final_estimate": x_est, "final_true": x_true}


def worked_example_profile():
    """Default worked-example profile of the SKILL.md (dt = 1 s, level
    flight accelerating north with f_N = 2 m/s^2, f_E = 0).

    True initial INS error [50, -30, 5, -2, 0.02], filter started at
    zero with P0 = diag(1000, 1000, 100, 100, 0.01), Q =
    diag(0.01, 0.01, 0.01, 0.01, 1e-6), R = diag(1, 1), and GNSS
    fixes at t = 10, 20, ..., 60 s.
    """
    return run_ins_gnss_profile(
        dt_s=1.0,
        f_north_m_s2=2.0,
        f_east_m_s2=0.0,
        initial_error=[50.0, -30.0, 5.0, -2.0, 0.02],
        gnss_times=[10.0, 20.0, 30.0, 40.0, 50.0, 60.0],
        p0=_diagonal([1000.0, 1000.0, 100.0, 100.0, 0.01]),
        q=_diagonal([0.01, 0.01, 0.01, 0.01, 1e-6]),
        r=_diagonal([1.0, 1.0]),
    )

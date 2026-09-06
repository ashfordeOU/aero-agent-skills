#!/usr/bin/env python3
"""LQG output-feedback compensator design for the canonical two-state plant.

For a continuous-time scalar-input two-state system whose measured output
is only the first (position-like) state, this module composes the two
algebraic Riccati solutions into a dynamic output-feedback compensator and
verifies the separation principle on the assembled loop. The plant family is
the canonical damped double integrator used across the gnc-autonomy control
leaves: A = [[0, 1], [0, -a]] with damping a >= 0, input B = [0, 1] (scalar
acceleration-like control on the rate state) and measured output C = [1, 0]
(y = x1). Pure stdlib, deterministic.

Regulator side: minimize J = integral(x'Qx + u'Ru) with Q = diag(q1, q2),
R = r > 0; the stabilizing solution P of the algebraic Riccati equation
A'P + PA - P B R^-1 B' P + Q = 0 gives u = -K x with K = [p2/r, p3/r].

Filter side: with process noise covariance Qw = diag(w1, w2) and measurement
noise variance Rw = rv > 0, the estimator gain L = [s1/rv, s2/rv] follows from
the stabilizing solution S of the dual (filter) algebraic Riccati equation
A S + S A' - S C' Rw^-1 C S + Qw = 0. The (2,2) entry reduces to a monotone
scalar equation in s2 solved in closed form at a = 0 and by bisection at
a > 0 (spec filter_riccati).

Compensator: the output-feedback law x_hat' = A x_hat + B u + L (y - C x_hat),
u = -K x_hat closes to the state-space realization (Ac, Bc, Cc, Dc) with
Ac = A - B K - L C. The separation verdict checks that the closed-loop
eigenvalues of the 4x4 plant-plus-compensator loop are the union, with
multiplicity, of the regulator poles det(sI - (A - B K)) and the estimator
poles det(sI - (A - L C)); the verdict polynomial comes from the
Faddeev-LeVerrier trace recursion.

Unit convention (SI, stated once): x1 is a position-like state in m (or rad),
x2 its rate in m/s (or rad/s), u an acceleration-like control in m/s^2 (or
rad/s^2), y the measured position-like state. Q = diag(q1, q2), R = r,
Qw = diag(w1, w2) and Rw = rv sit in the consistent squared units so both
Riccati equations are dimensionless.

Validation shared by every function: A must be the canonical [[0, 1], [0, -a]]
with a >= 0, B must be [0, 1], C must be [1, 0], Q and Qw must be diagonal 2x2
with q1, q2 >= 0, w1 >= 0, R and Rw must be > 0, w2 must be > 0 (noise on the
driven state; without it the double integrator admits no stabilizing filter),
and K and L must be length-2. Anything else raises ValueError.

Reference note: ARP4754A (standards-map.yaml, reference-only) frames
development assurance for aircraft systems; the Riccati and separation
mathematics is common control-theory knowledge, summary only.
"""

import math

_TOL = 1e-9
_BISECT_REL_TOL = 1e-15
_SEP_TOL = 1e-9
_MAX_BISECT_ITERS = 200


# --------------------------------------------------------------------------
# Validation helpers (shared ValueError contract)
# --------------------------------------------------------------------------

def _canonical_damping(A):
    """Validate A = [[0, 1], [0, -a]] and return the damping a >= 0.

    Accepts list or tuple rows, converts to float, rejects non-canonical
    entries and negative damping with ValueError.
    """
    if not (isinstance(A, (list, tuple)) and len(A) == 2 and
            all(isinstance(row, (list, tuple)) and len(row) == 2 for row in A)):
        raise ValueError("A must be a 2x2 matrix, got %r" % (A,))
    try:
        a00, a01 = float(A[0][0]), float(A[0][1])
        a10, a11 = float(A[1][0]), float(A[1][1])
    except (TypeError, ValueError):
        raise ValueError("A entries must be numeric, got %r" % (A,))
    if abs(a00) > _TOL or abs(a01 - 1.0) > _TOL or abs(a10) > _TOL:
        raise ValueError(
            "A must be of the canonical [[0, 1], [0, -a]] family, got %r" % (A,))
    a = -a11
    if a < -_TOL:
        raise ValueError("damping a = -A[1][1] must be >= 0, got %g" % (a,))
    return max(a, 0.0)


def _unit_vector(v, name, one_index):
    """Validate a unit vector v (length 2, one entry 1, the other 0).

    Returns the two floats. one_index selects which entry must equal 1,
    so B = [0, 1] passes one_index 1 and C = [1, 0] passes one_index 0.
    """
    if not (isinstance(v, (list, tuple)) and len(v) == 2):
        raise ValueError("%s must be a length-2 vector, got %r" % (name, v))
    try:
        v0, v1 = float(v[0]), float(v[1])
    except (TypeError, ValueError):
        raise ValueError("%s entries must be numeric, got %r" % (name, v))
    if one_index == 1:
        ok = abs(v0) <= _TOL and abs(v1 - 1.0) <= _TOL
    else:
        ok = abs(v0 - 1.0) <= _TOL and abs(v1) <= _TOL
    if not ok:
        raise ValueError("%s must be %s, got %r"
                         % (name, "[0, 1]" if one_index else "[1, 0]", v))
    return v0, v1


def _diag_weights(M, name, low_ok):
    """Validate a diagonal 2x2 weight matrix M = diag(m1, m2).

    Returns (m1, m2) as floats. low_ok is a bool pair (first, second) that
    says whether the corresponding weight may be zero: Q and Qw allow the
    first weight zero but demand the second strictly positive, R and Rw are
    scalar. Any off-diagonal entry or negative weight raises ValueError.
    """
    if not (isinstance(M, (list, tuple)) and len(M) == 2 and
            all(isinstance(row, (list, tuple)) and len(row) == 2 for row in M)):
        raise ValueError("%s must be a 2x2 matrix, got %r" % (name, M))
    try:
        m00, m01 = float(M[0][0]), float(M[0][1])
        m10, m11 = float(M[1][0]), float(M[1][1])
    except (TypeError, ValueError):
        raise ValueError("%s entries must be numeric, got %r" % (name, M))
    if abs(m01) > _TOL or abs(m10) > _TOL:
        raise ValueError(
            "%s must be diagonal for the canonical closed form, got %r"
            % (name, M))
    if m00 < -_TOL:
        raise ValueError("%s first weight must be >= 0, got %g" % (name, m00))
    if m11 < -_TOL:
        raise ValueError("%s second weight must be >= 0, got %g" % (name, m11))
    if not low_ok[1] and m11 <= _TOL:
        raise ValueError(
            "%s second weight must be > 0 (noise on the driven state), got %g"
            % (name, m11))
    return max(m00, 0.0), max(m11, 0.0)


def _positive_scalar(v, name):
    """Validate a strictly positive scalar v and return it as float."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be a positive scalar, got %r" % (name, v))
    if f <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, f))
    return f


def _gain_vector(K, name):
    """Validate a length-2 gain vector K or L and return its floats."""
    if not (isinstance(K, (list, tuple)) and len(K) == 2):
        raise ValueError("%s must be a length-2 gain vector, got %r" % (name, K))
    try:
        k0, k1 = float(K[0]), float(K[1])
    except (TypeError, ValueError):
        raise ValueError("%s entries must be numeric, got %r" % (name, K))
    return k0, k1


# --------------------------------------------------------------------------
# Regulator side: algebraic Riccati solution and gain
# --------------------------------------------------------------------------

def regulator_riccati(A, B, Q, R):
    """Solve the regulator ARE and return (P, K) for the canonical plant.

    The exact scalar reduction of A'P + PA - P B R^-1 B' P + Q = 0 used by
    the lqr-design sibling (valid for any a >= 0):
        p2 = sqrt(r q1)
        p3 = r (-a + sqrt(a^2 + (2 p2 + q2) / r))
        p1 = a p2 + p2 p3 / r
    Returns P = [[p1, p2], [p2, p3]] and K = [k1, k2] = [p2 / r, p3 / r]
    with u = -K x. Validation: A canonical with a >= 0, B = [0, 1],
    Q = diag(q1, q2) with q1, q2 >= 0, R > 0; else ValueError.
    """
    a = _canonical_damping(A)
    _unit_vector(B, "B", 1)
    q1, q2 = _diag_weights(Q, "Q", (True, True))
    r = _positive_scalar(R, "R")
    p2 = math.sqrt(r * q1)
    p3 = r * (-a + math.sqrt(a * a + (2.0 * p2 + q2) / r))
    p1 = a * p2 + p2 * p3 / r
    return [[p1, p2], [p2, p3]], [p2 / r, p3 / r]


# --------------------------------------------------------------------------
# Filter side: dual (Kalman) algebraic Riccati solution and gain
# --------------------------------------------------------------------------

def _filter_s2_residual(u, a, rv, w1, w2):
    """Left side of the monotone scalar filter equation at u >= 0.

    f(u) = u^2 + 2 a^2 rv u + 2 a u sqrt(rv (2 u + w1)) - rv w2, the (2,2)
    entry of the filter ARE written out for the canonical family. Strictly
    increasing in u for u >= 0 when a >= 0, and f(0) = -rv w2 < 0.
    """
    return (u * u + 2.0 * a * a * rv * u
            + 2.0 * a * u * math.sqrt(rv * (2.0 * u + w1)) - rv * w2)


def filter_s2_bisection(a, rv, w1, w2):
    """Root of the filter scalar equation on (0, sqrt(rv w2)] by bisection.

    Unique root of the monotone left side (a > 0, or the degenerate a = 0
    case where the root is sqrt(rv w2)); bracket [0, sqrt(rv w2)] with
    f(0) < 0 and f(sqrt(rv w2)) >= 0. Converges to 1e-15 relative
    (at most _MAX_BISECT_ITERS halvings). All arguments validated by the
    caller; used directly by filter_riccati at a > 0 and exposed so the
    contract test can force the branch at a = 0.
    """
    hi = math.sqrt(rv * w2)
    lo = 0.0
    for _ in range(_MAX_BISECT_ITERS):
        mid = 0.5 * (lo + hi)
        if hi - lo <= _BISECT_REL_TOL * abs(mid):
            return mid
        if _filter_s2_residual(mid, a, rv, w1, w2) < 0.0:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def filter_riccati(A, C, Qw, Rw):
    """Solve the filter (Kalman) ARE and return (S, L) for the canonical pair.

    Dual scalar reduction of A S + S A' - S C' Rw^-1 C S + Qw = 0 with
    C = [1, 0]. The (1,1) entry gives s1 = sqrt(rv (2 s2 + w1)); the (1,2)
    entry gives s3 = a s2 + s1 s2 / rv; the (2,2) entry is the monotone
    scalar equation solved for s2 in closed form, sqrt(rv w2), at a = 0 and
    by bisection (filter_s2_bisection) otherwise. Returns S = [[s1, s2],
    [s2, s3]] and the Kalman gain L = [l1, l2] = [s1 / rv, s2 / rv], under
    which the estimation error follows e' = (A - L C) e. Validation: A
    canonical with a >= 0,
    C = [1, 0], Qw = diag(w1, w2) with w1 >= 0 and w2 > 0, Rw > 0; else
    ValueError.
    """
    a = _canonical_damping(A)
    _unit_vector(C, "C", 0)
    w1, w2 = _diag_weights(Qw, "Qw", (True, False))
    rv = _positive_scalar(Rw, "Rw")
    if a == 0.0:
        s2 = math.sqrt(rv * w2)
    else:
        s2 = filter_s2_bisection(a, rv, w1, w2)
    s1 = math.sqrt(rv * (2.0 * s2 + w1))
    s3 = a * s2 + s1 * s2 / rv
    return [[s1, s2], [s2, s3]], [s1 / rv, s2 / rv]


# --------------------------------------------------------------------------
# Compensator assembly, separation verdict, transfer function
# --------------------------------------------------------------------------

def _mat_mul(X, Y):
    """Multiply two square matrices given as lists of lists."""
    n = len(X)
    return [[sum(X[i][k] * Y[k][j] for k in range(n)) for j in range(n)]
            for i in range(n)]


def _mat_trace(M):
    """Trace of a square matrix given as a list of lists."""
    return sum(M[i][i] for i in range(len(M)))


def _charpoly_faddeev_leverrier(M):
    """Characteristic polynomial det(sI - M), Faddeev-LeVerrier recursion.

    Coefficients high to low: p(s) = s^n - c1 s^(n-1) - ... - cn with
    B0 = I, Bk = M B(k-1) - ck I and ck = tr(M B(k-1)) / k. Exact in real
    arithmetic up to floating-point round off.
    """
    n = len(M)
    coeffs = [1.0]
    prev = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for k in range(1, n + 1):
        mb = _mat_mul(M, prev)
        ck = _mat_trace(mb) / k
        coeffs.append(-ck)
        prev = [[mb[i][j] - (ck if i == j else 0.0) for j in range(n)]
                for i in range(n)]
    return coeffs


def _poly_mul(p, q):
    """Multiply two polynomials given high-to-low coefficient lists."""
    out = [0.0] * (len(p) + len(q) - 1)
    for i, pi in enumerate(p):
        for j, qj in enumerate(q):
            out[i + j] += pi * qj
    return out


def compensator_realization(A, B, C, K, L):
    """Assemble the dynamic output-feedback compensator (Ac, Bc, Cc, Dc).

    The estimator x_hat' = A x_hat + B u + L (y - C x_hat) with u = -K x_hat
    closes to Ac = A - B K - L C = [[-l1, 1], [-k1 - l2, -a - k2]],
    Bc = L, Cc = -K and Dc = 0, so u = Cc x_hat + Dc y. These four matrices
    are what flight software integrates. Validation: A canonical with a >= 0,
    B = [0, 1], C = [1, 0], K and L length-2; else ValueError.
    """
    a = _canonical_damping(A)
    _unit_vector(B, "B", 1)
    _unit_vector(C, "C", 0)
    k1, k2 = _gain_vector(K, "K")
    l1, l2 = _gain_vector(L, "L")
    ac = [[-l1, 1.0], [-k1 - l2, -a - k2]]
    return ac, [l1, l2], [-k1, -k2], 0.0


def separation_verdict(A, B, C, K, L):
    """Verify the separation principle on the plant-plus-compensator loop.

    Assembles the 4x4 closed loop Acl = [[A, -B K], [L C, A - B K - L C]] in
    the (x, x_hat) coordinates, computes its characteristic polynomial by the
    Faddeev-LeVerrier trace recursion and compares it coefficient by
    coefficient with the product of the regulator polynomial
    det(sI - (A - B K)) = s^2 + (a + k2) s + k1 and the estimator polynomial
    det(sI - (A - L C)) = s^2 + (a + l1) s + (a l1 + l2). Returns
    {"regulator_polynomial": [1, a + k2, k1], "estimator_polynomial":
    [1, a + l1, a l1 + l2], "closed_loop_polynomial": [4 coeffs],
    "product_polynomial": [4 coeffs], "max_abs_diff": float,
    "separated": bool} with "separated" True when max_abs_diff < 1e-9.
    Both quadratic factors have positive coefficients for valid inputs, so a
    separated verdict implies all four closed-loop eigenvalues lie in the
    open left half plane.
    """
    a = _canonical_damping(A)
    _unit_vector(B, "B", 1)
    _unit_vector(C, "C", 0)
    k1, k2 = _gain_vector(K, "K")
    l1, l2 = _gain_vector(L, "L")
    # 4x4 closed loop [[A, -B K], [L C, A - B K - L C]]
    ac00, ac01 = -l1, 1.0
    ac10, ac11 = -k1 - l2, -a - k2
    acl = [[0.0, 1.0, 0.0, 0.0],
           [0.0, -a, -k1, -k2],
           [l1, 0.0, ac00, ac01],
           [l2, 0.0, ac10, ac11]]
    reg_poly = [1.0, a + k2, k1]
    est_poly = [1.0, a + l1, a * l1 + l2]
    closed = _charpoly_faddeev_leverrier(acl)
    product = _poly_mul(reg_poly, est_poly)
    max_abs_diff = max(abs(cp - pp) for cp, pp in zip(closed, product))
    return {
        "regulator_polynomial": reg_poly,
        "estimator_polynomial": est_poly,
        "closed_loop_polynomial": closed,
        "product_polynomial": product,
        "max_abs_diff": max_abs_diff,
        "separated": max_abs_diff < _SEP_TOL,
    }


def compensator_transfer_function(Ac, Bc, Cc):
    """Reduce the compensator to G_c(s) = Cc (sI - Ac)^-1 Bc as (num, den).

    From the 2x2 adjugate, den = [1, -tr(Ac), det(Ac)] (monic) and the
    numerator is degree <= 1 with num_1 = c1 b1 + c2 b2 and
    num_0 = -c1 b1 m11 + c1 b2 m01 + c2 b1 m10 - c2 b2 m00 for
    Ac = [[m00, m01], [m10, m11]], Bc = [b1, b2], Cc = [c1, c2]. Returns
    ([num_1, num_0], [1, -tr, det]). Validation: Ac a numeric 2x2 matrix,
    Bc and Cc numeric length-2; else ValueError.
    """
    if not (isinstance(Ac, (list, tuple)) and len(Ac) == 2 and
            all(isinstance(row, (list, tuple)) and len(row) == 2 for row in Ac)):
        raise ValueError("Ac must be a 2x2 matrix, got %r" % (Ac,))
    try:
        m00, m01 = float(Ac[0][0]), float(Ac[0][1])
        m10, m11 = float(Ac[1][0]), float(Ac[1][1])
    except (TypeError, ValueError):
        raise ValueError("Ac entries must be numeric, got %r" % (Ac,))
    b1, b2 = _gain_vector(Bc, "Bc")
    c1, c2 = _gain_vector(Cc, "Cc")
    num_1 = c1 * b1 + c2 * b2
    num_0 = (-c1 * b1 * m11 + c1 * b2 * m01
             + c2 * b1 * m10 - c2 * b2 * m00)
    den = [1.0, -(m00 + m11), m00 * m11 - m01 * m10]
    return [num_1, num_0], den

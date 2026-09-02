#!/usr/bin/env python3
"""LQR design logic (paraphrase, common control-theory knowledge).

For a continuous-time scalar-input two-state system in the canonical
form x' = A x + B u with A = [[0, 1], [0, -a]] (double integrator with
damping a >= 0), B = [0, 1], LQR minimizes the quadratic cost
J = integral(x' Q x + u' R u) with Q = diag(q1, q2), R = r > 0. The
optimal state feedback is u = -K x with K = R^-1 B' P, where P is the
symmetric stabilizing solution of the algebraic Riccati equation
A'P + PA - P B R^-1 B' P + Q = 0.

Unit convention (SI, stated once, used everywhere in this module):
state x1 is an angle in rad, state x2 an angular rate in rad/s, and the
scalar control u a torque in N m. The weights then carry q1 in 1/rad^2,
q2 in 1/(rad/s)^2, and R in 1/(N m)^2 so the running cost x'Qx + u'Ru
is dimensionless. The closed-form solution below is exact for the
canonical family; it is not a contraction iteration.

The ARE reduces to three independent scalar equations. With
P = [[p1, p2], [p2, p3]] and the fact that B R^-1 B' P touches only the
second column of P:
  (1,1)  -p2^2 / r + q1 = 0              -> p2 = sqrt(r q1)
  (1,2)  p1 - a p2 - p2 p3 / r = 0       -> p1 = a p2 + p2 p3 / r
  (2,2)  2 p2 - 2 a p3 - p3^2 / r + q2 = 0
         -> p3 = r (-a + sqrt(a^2 + (2 p2 + q2) / r))   (positive root)

Reference note: ARP4754A (standards-map.yaml, gated, reference-only)
frames development assurance for aircraft systems; the Riccati
mathematics is common knowledge and is only summarized here.
"""

import math

_TOL = 1e-9


def _check_scalar_input_2state(A, B):
    """Validate the canonical scalar-input two-state structure.

    Returns the damping a = -A[1][1] (>= 0). Raises ValueError on
    non-2x2 A, non-length-2 B, non-canonical entries, or negative
    damping.
    """
    if not (isinstance(A, (list, tuple)) and len(A) == 2 and
            all(isinstance(row, (list, tuple)) and len(row) == 2 for row in A)):
        raise ValueError("A must be a 2x2 matrix, got %r" % (A,))
    if not (isinstance(B, (list, tuple)) and len(B) == 2):
        raise ValueError("B must be a length-2 vector, got %r" % (B,))
    try:
        a00, a01 = float(A[0][0]), float(A[0][1])
        a10, a11 = float(A[1][0]), float(A[1][1])
        b0, b1 = float(B[0]), float(B[1])
    except (TypeError, ValueError):
        raise ValueError("A and B entries must be numeric, got %r, %r" % (A, B))
    if abs(a00) > _TOL or abs(a01 - 1.0) > _TOL or abs(a10) > _TOL:
        raise ValueError(
            "A must have the canonical form [[0, 1], [0, -a]], got %r" % (A,))
    if abs(b0) > _TOL or abs(b1 - 1.0) > _TOL:
        raise ValueError("B must be [0, 1], got %r" % (B,))
    a = -a11
    if a < -_TOL:
        raise ValueError("damping a = -A[1][1] must be >= 0, got %g" % (a,))
    return max(a, 0.0)


def _check_q(Q):
    """Validate Q = diag(q1, q2), positive semidefinite.

    Returns (q1, q2) clamped at zero. Raises ValueError otherwise.
    """
    if not (isinstance(Q, (list, tuple)) and len(Q) == 2 and
            all(isinstance(row, (list, tuple)) and len(row) == 2 for row in Q)):
        raise ValueError("Q must be a 2x2 matrix, got %r" % (Q,))
    try:
        q00, q01 = float(Q[0][0]), float(Q[0][1])
        q10, q11 = float(Q[1][0]), float(Q[1][1])
    except (TypeError, ValueError):
        raise ValueError("Q entries must be numeric, got %r" % (Q,))
    if abs(q01) > _TOL or abs(q10) > _TOL:
        raise ValueError(
            "Q must be diagonal for the canonical closed form, got %r" % (Q,))
    if q00 < -_TOL or q11 < -_TOL:
        raise ValueError(
            "Q must be positive semidefinite (q1 >= 0, q2 >= 0), got %r" % (Q,))
    return max(q00, 0.0), max(q11, 0.0)


def _check_r(R):
    """Validate R > 0 (scalar). Returns the float R."""
    try:
        r = float(R)
    except (TypeError, ValueError):
        raise ValueError("R must be a positive scalar, got %r" % (R,))
    if r <= 0.0:
        raise ValueError("R must be > 0, got %g" % (r,))
    return r


def riccati_gain(A, B, Q, R):
    """Solve the algebraic Riccati equation for the canonical system.

    Returns the symmetric 2x2 stabilizing solution P as a list of
    lists [[p1, p2], [p2, p3]]. Validation: A = [[0,1],[0,-a]] with
    a >= 0, B = [0, 1], Q = diag(q1, q2) with q1, q2 >= 0, R > 0;
    anything else raises ValueError. Units per the module convention
    (q1 in 1/rad^2, q2 in 1/(rad/s)^2, R in 1/(N m)^2).
    """
    a = _check_scalar_input_2state(A, B)
    q1, q2 = _check_q(Q)
    r = _check_r(R)
    p2 = math.sqrt(r * q1)
    p3 = r * (-a + math.sqrt(a * a + (2.0 * p2 + q2) / r))
    p1 = a * p2 + p2 * p3 / r
    return [[p1, p2], [p2, p3]]


def gain_matrix(P, B, R):
    """Compute the state-feedback gain K = R^-1 B' P.

    Returns [k1, k2] for the canonical system (B = [0, 1], R > 0, P a
    symmetric 2x2 matrix). Raises ValueError on invalid inputs.
    """
    if not (isinstance(P, (list, tuple)) and len(P) == 2 and
            all(isinstance(row, (list, tuple)) and len(row) == 2 for row in P)):
        raise ValueError("P must be a 2x2 matrix, got %r" % (P,))
    try:
        p00, p01 = float(P[0][0]), float(P[0][1])
        p10, p11 = float(P[1][0]), float(P[1][1])
    except (TypeError, ValueError):
        raise ValueError("P entries must be numeric, got %r" % (P,))
    if abs(p01 - p10) > _TOL:
        raise ValueError("P must be symmetric, got %r" % (P,))
    if not (isinstance(B, (list, tuple)) and len(B) == 2):
        raise ValueError("B must be a length-2 vector, got %r" % (B,))
    try:
        b0, b1 = float(B[0]), float(B[1])
    except (TypeError, ValueError):
        raise ValueError("B entries must be numeric, got %r" % (B,))
    if abs(b0) > _TOL or abs(b1 - 1.0) > _TOL:
        raise ValueError("B must be [0, 1], got %r" % (B,))
    r = _check_r(R)
    return [p01 / r, p11 / r]


def _poles2(trace, det):
    """Poles of s^2 - trace s + det = 0 as [(re, im), (re, im)]."""
    disc = trace * trace - 4.0 * det
    if disc >= 0.0:
        s = math.sqrt(disc)
        return [((trace + s) / 2.0, 0.0), ((trace - s) / 2.0, 0.0)]
    s = math.sqrt(-disc)
    return [(trace / 2.0, s / 2.0), (trace / 2.0, -s / 2.0)]


def closed_loop_stable(A, B, K):
    """Check closed-loop stability of A - B K (2x2).

    A 2x2 matrix is stable (both eigenvalues with negative real part)
    exactly when trace < 0 and determinant > 0. Returns
    {"stable": bool, "poles": [(re, im), (re, im)]}. A and B must be
    canonical (A = [[0,1],[0,-a]], a >= 0; B = [0, 1]) and K a
    length-2 gain vector; otherwise ValueError.
    """
    a = _check_scalar_input_2state(A, B)
    if not (isinstance(K, (list, tuple)) and len(K) == 2):
        raise ValueError("K must be a length-2 gain vector, got %r" % (K,))
    try:
        k1, k2 = float(K[0]), float(K[1])
    except (TypeError, ValueError):
        raise ValueError("K entries must be numeric, got %r" % (K,))
    # A - B K = [[0, 1], [-k1, -a - k2]]
    trace = -a - k2
    det = k1
    stable = trace < 0.0 and det > 0.0
    return {"stable": stable, "poles": _poles2(trace, det)}


def cost_weight_guide(q1, q2, r):
    """Return a note string on the Q/R weighting trade.

    Higher Q relative to R raises the gain magnitude and settling
    speed; higher R relative to Q gentles the control and slows
    regulation. q1, q2 >= 0 and r > 0, else ValueError. Weights in the
    module SI convention.
    """
    try:
        q1f, q2f, rf = float(q1), float(q2), float(r)
    except (TypeError, ValueError):
        raise ValueError("q1, q2, r must be numeric, got %r, %r, %r" % (q1, q2, r))
    if q1f < -_TOL or q2f < -_TOL:
        raise ValueError("q1 and q2 must be >= 0, got %g, %g" % (q1f, q2f))
    if rf <= 0.0:
        raise ValueError("r must be > 0, got %g" % (rf,))
    ratio = (max(q1f, 0.0) + max(q2f, 0.0)) / rf
    if ratio > 10.0:
        regime = "state-error dominated: expect aggressive regulation with large gains"
    elif ratio < 0.1:
        regime = "control-effort dominated: expect gentle regulation with small gains"
    else:
        regime = "balanced: state error and control effort weighted comparably"
    return (
        "Q penalizes state error (q1 on the position-like state, q2 on the "
        "rate state); R penalizes control effort. Higher Q relative to R "
        "raises the gain magnitude and settling speed; higher R relative to "
        "Q gentles the control and slows regulation. Current weights: " +
        regime + "."
    )

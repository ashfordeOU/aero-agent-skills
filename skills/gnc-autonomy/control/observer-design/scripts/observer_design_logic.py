#!/usr/bin/env python3
"""Full-order Luenberger state observer design (linear time-invariant, SI).

Paraphrase of the classical state observer design methodology as common
control-theory knowledge. For the continuous-time plant

  x_dot = A x + B u,   y = C x

with x in R^n and a single measured output y in R, the full-order
observer is

  x_hat_dot = A x_hat + B u + L (y - C x_hat)

and the estimation error e = x - x_hat obeys

  e_dot = (A - L C) e.

The estimator gain L is chosen by pole placement: the error dynamics
eigenvalues eig(A - L C) are placed at the desired observer poles. The
Ackermann formula builds L from the observability matrix

  O = [C; C A; ...; C A^(n-1)]

and the desired characteristic polynomial phi(s) = prod_i (s - p_i):
L = phi(A) O^{-1} e_n, with e_n the last unit vector. The system must
be observable, rank(O) = n. By the separation principle the closed
loop under u = -K x_hat has spectrum eig(A - B K) union eig(A - L C);
the closed-loop matrix is block upper triangular and its characteristic
polynomial factors into the controller and observer polynomials.

The characteristic polynomial is computed by the Faddeev-LeVerrier
algorithm and Hurwitz stability by the Routh array. All functions are
pure, stdlib-only, and raise ValueError on invalid input. Units: SI
(matrix entries dimensionless as required by the model, poles in rad/s,
settling time in seconds).

Reference note: ARP4754A (standards-map.yaml, gated, reference-only)
frames development assurance for aircraft systems and DO-178C frames
the flight software that hosts the observer; the observer design
equations themselves are common knowledge and are only summarized
here.
"""

import math

_TOL = 1e-9


def _matrix(M, name):
    """Validate and cast a matrix to a rectangular list of lists of float.

    Raises ValueError when M is not a non-empty list of rows, the rows
    are not equal-length lists, or an entry is not numeric.
    """
    if not isinstance(M, (list, tuple)) or len(M) == 0:
        raise ValueError("%s must be a non-empty list of rows" % (name,))
    out = []
    width = None
    for i, row in enumerate(M):
        if not isinstance(row, (list, tuple)) or len(row) == 0:
            raise ValueError(
                "%s row %d must be a non-empty list" % (name, i)
            )
        if width is None:
            width = len(row)
        elif len(row) != width:
            raise ValueError(
                "%s rows must be rectangular, row %d has %d entries, "
                "expected %d" % (name, i, len(row), width)
            )
        cast = []
        for v in row:
            try:
                cast.append(float(v))
            except (TypeError, ValueError):
                raise ValueError(
                    "%s entry %r is not numeric" % (name, v)
                )
        out.append(cast)
    return out


def _check_square(A, name="A"):
    """Validate a square matrix; return the validated copy and its size."""
    A = _matrix(A, name)
    n = len(A)
    if len(A[0]) != n:
        raise ValueError("%s must be square, got %d x %d" % (name, n, len(A[0])))
    return A, n


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _mat_add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _mat_sub(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))] for i in range(len(A))]


def _mat_scale(A, s):
    return [[A[i][j] * s for j in range(len(A[0]))] for i in range(len(A))]


def _mat_mul(A, B):
    m, k, n = len(A), len(A[0]), len(B[0])
    if len(B) != k:
        raise ValueError("matrix product dimension mismatch %d x %d times %d x %d"
                         % (m, k, len(B), n))
    return [
        [sum(A[i][t] * B[t][j] for t in range(k)) for j in range(n)]
        for i in range(m)
    ]


def _mat_trace(A):
    return sum(A[i][i] for i in range(len(A)))


def _max_abs(M):
    return max(abs(v) for row in M for v in row) if M else 0.0


def _rank(M):
    """Rank by Gaussian elimination with partial pivoting (relative tol)."""
    A = [row[:] for row in _matrix(M, "matrix")]
    rows, cols = len(A), len(A[0])
    scale = max(1.0, _max_abs(A))
    rank = 0
    for col in range(cols):
        pivot = None
        best = 0.0
        for r in range(rank, rows):
            v = abs(A[r][col])
            if v > best:
                best = v
                pivot = r
        if pivot is None or best <= _TOL * scale:
            continue
        A[rank], A[pivot] = A[pivot], A[rank]
        pv = A[rank][col]
        for r in range(rank + 1, rows):
            f = A[r][col] / pv
            if abs(f) > _TOL:
                for c in range(col, cols):
                    A[r][c] -= f * A[rank][c]
        rank += 1
    return rank


def _inverse(M):
    """Matrix inverse by Gauss-Jordan with partial pivoting.

    Raises ValueError when the matrix is singular.
    """
    A = [row[:] for row in _matrix(M, "matrix")]
    n = len(A)
    if len(A[0]) != n:
        raise ValueError("inverse requires a square matrix, got %d x %d"
                         % (n, len(A[0])))
    aug = [A[i] + [1.0 if j == i else 0.0 for j in range(n)] for i in range(n)]
    scale = max(1.0, _max_abs(A))
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= _TOL * scale:
            raise ValueError("matrix is singular, inverse undefined")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        for c in range(2 * n):
            aug[col][c] /= pv
        for r in range(n):
            if r == col:
                continue
            f = aug[r][col]
            if abs(f) > _TOL:
                for c in range(2 * n):
                    aug[r][c] -= f * aug[col][c]
    return [row[n:] for row in aug]


def _poly_mul(p, q):
    """Multiply two polynomials given as coefficient lists (high to low)."""
    out = [0.0] * (len(p) + len(q) - 1)
    for i, a in enumerate(p):
        for j, b in enumerate(q):
            out[i + j] += a * b
    return out


def _poly_from_poles(poles):
    """Coefficients [1, a1, ..., an] of phi(s) = prod_i (s - p_i).

    Poles may be complex (conjugate pairs for a real plant); the
    coefficients are then complex-valued and the arithmetic downstream
    stays complex until the real gain is extracted.
    """
    poly = [1.0]
    for p in poles:
        poly = _poly_mul(poly, [1.0, -complex(p)])
    return poly


def _poly_eval_matrix(A, coeffs):
    """Evaluate M^n + a1 M^(n-1) + ... + an I by Horner.

    coeffs = [1, a1, ..., an] for an n x n matrix M = A.
    """
    n = len(A)
    if len(coeffs) != n + 1:
        raise ValueError("expected %d coefficients for an %d x %d matrix"
                         % (n + 1, n, n))
    R = _mat_add(A, _mat_scale(_identity(n), coeffs[1]))
    for k in range(2, n + 1):
        R = _mat_add(_mat_mul(R, A), _mat_scale(_identity(n), coeffs[k]))
    return R


def observability_matrix(A, C):
    """Observability matrix O = [C; C A; ...; C A^(n-1)] (list of lists).

    A must be n x n and C must have n columns; C may have any number of
    rows, so the stacked matrix is (r*n) x n. Raises ValueError on
    dimension or numeric errors.
    """
    A, n = _check_square(A, "A")
    C = _matrix(C, "C")
    if len(C[0]) != n:
        raise ValueError(
            "C must have %d columns to match A, got %d" % (n, len(C[0]))
        )
    rows = []
    power = [row[:] for row in C]  # C A^k, starts at C A^0
    for _k in range(n):
        rows.extend(power)
        power = _mat_mul(power, A)
    return rows


def is_observable(A, C):
    """Observability verdict: rank(O) == n (full column rank)."""
    A, n = _check_square(A, "A")
    C = _matrix(C, "C")
    if len(C[0]) != n:
        raise ValueError(
            "C must have %d columns to match A, got %d" % (n, len(C[0]))
        )
    O = observability_matrix(A, C)
    return _rank(O) == n


def observer_gain_ackermann(A, C, poles):
    """Full-order observer gain L by the Ackermann formula.

    L = phi(A) O^{-1} e_n, with phi(s) = prod_i (s - p_i) built from the
    desired observer poles and O the observability matrix. Requires a
    single measured output row (C is 1 x n) so O is square n x n.

    Raises ValueError when A is not square, C is not a single row with n
    columns, the pole count differs from n, a pole has non-negative real
    part (observer poles must lie in the open left half plane), or the
    pair (A, C) is not observable.
    """
    A, n = _check_square(A, "A")
    C = _matrix(C, "C")
    if len(C) != 1 or len(C[0]) != n:
        raise ValueError(
            "Ackermann observer gain needs a single output row C (1 x %d), "
            "got %d x %d" % (n, len(C), len(C[0]))
        )
    if len(poles) != n:
        raise ValueError(
            "need exactly %d observer poles for an %d-state system, got %d"
            % (n, n, len(poles))
        )
    poles_f = []
    for p in poles:
        try:
            pf = complex(p)
        except (TypeError, ValueError):
            raise ValueError("observer pole %r is not numeric" % (p,))
        if pf.real >= 0.0:
            raise ValueError(
                "observer poles must be strictly stable (negative real "
                "part), got %s" % (pf,)
            )
        poles_f.append(pf)
    O = observability_matrix(A, C)
    if _rank(O) != n:
        raise ValueError(
            "system (A, C) is not observable: rank(O) = %d < n = %d"
            % (_rank(O), n)
        )
    phi = _poly_from_poles(poles_f)
    phiA = _poly_eval_matrix(A, phi)
    Oinv = _inverse(O)
    P = _mat_mul(phiA, Oinv)
    gain = []
    for i in range(n):
        v = P[i][n - 1]
        if abs(v.imag) > 1e-9:
            raise ValueError(
                "complex observer gain %s: the pole set must be real or "
                "come in conjugate pairs for a real plant" % (v,)
            )
        gain.append(v.real)
    return gain


def characteristic_polynomial(A):
    """Characteristic polynomial det(sI - A) by Faddeev-LeVerrier.

    Returns [1, c1, ..., cn] for s^n + c1 s^(n-1) + ... + cn.
    """
    A, n = _check_square(A, "A")
    coeffs = [1.0]
    B = [row[:] for row in A]
    for k in range(1, n + 1):
        ck = -_mat_trace(B) / float(k)
        coeffs.append(ck)
        if k < n:
            B = _mat_mul(A, _mat_add(B, _mat_scale(_identity(n), ck)))
    return coeffs


def is_hurwitz(coeffs):
    """Hurwitz stability verdict by the Routh array.

    coeffs = [1, c1, ..., cn] of the characteristic polynomial. Returns
    True when every first-column entry of the Routh array is strictly
    positive (all roots in the open left half plane), False otherwise,
    including marginally stable and unstable polynomials.
    """
    a = [float(c) for c in coeffs]
    n = len(a) - 1
    if n < 1:
        return True
    if any(c <= 0.0 for c in a[1:]):
        return False
    rows = [a[1::2], a[2::2]]
    while len(rows[-1]) > 1:
        prev, cur = rows[-2], rows[-1]
        if abs(cur[0]) <= _TOL:
            return False
        rows.append([
            (prev[0] * cur[j + 1] - prev[j + 1] * cur[0]) / cur[0]
            for j in range(len(cur) - 1)
        ])
    first_col = [r[0] for r in rows if r]
    return all(v > 0.0 for v in first_col)


def error_dynamics(A, C, L):
    """Observer error dynamics bundle for a computed gain L.

    Returns {'matrix': A - L C (list of lists), 'char_poly':
    characteristic polynomial coefficients, 'stable': Hurwitz verdict}.
    Raises ValueError on dimension errors; the gain vector L must have
    one entry per state.
    """
    A, n = _check_square(A, "A")
    C = _matrix(C, "C")
    if len(C[0]) != n:
        raise ValueError(
            "C must have %d columns to match A, got %d" % (n, len(C[0]))
        )
    if len(L) != n:
        raise ValueError(
            "observer gain must have %d entries, got %d" % (n, len(L))
        )
    L = [float(v) for v in L]
    LC = [[L[i] * C[0][j] for j in range(n)] for i in range(n)]
    M = _mat_sub(A, LC)
    cp = characteristic_polynomial(M)
    return {"matrix": M, "char_poly": cp, "stable": is_hurwitz(cp)}


def separation_closed_loop(A, B, C, K, L):
    """Separation principle check for output feedback u = -K x_hat.

    With x_dot = (A - B K) x + B K e and e_dot = (A - L C) e, the closed
    loop is block upper triangular [[A - B K, B K], [0, A - L C]], so its
    characteristic polynomial factors into the controller polynomial and
    the observer polynomial. Returns {'controller_poly': ...,
    'observer_poly': ..., 'closed_loop_poly': ..., 'factorizes': bool}.

    B must be an n x 1 column, K a 1 x n row (or an n-list), C a 1 x n
    row, L an n-list. Raises ValueError on dimension errors.
    """
    A, n = _check_square(A, "A")
    B = _matrix(B, "B")
    C = _matrix(C, "C")
    if len(B) != n or len(B[0]) != 1:
        raise ValueError("B must be an %d x 1 column, got %d x %d"
                         % (n, len(B), len(B[0])))
    if len(C) != 1 or len(C[0]) != n:
        raise ValueError("C must be a 1 x %d row, got %d x %d"
                         % (n, len(C), len(C[0])))
    K = [float(v) for v in K]
    if len(K) != n:
        raise ValueError("controller gain K must have %d entries, got %d"
                         % (n, len(K)))
    if len(L) != n:
        raise ValueError("observer gain L must have %d entries, got %d"
                         % (n, len(L)))
    BK = [[B[i][0] * K[j] for j in range(n)] for i in range(n)]
    LC = [[L[i] * C[0][j] for j in range(n)] for i in range(n)]
    M_ctrl = _mat_sub(A, BK)
    M_obs = _mat_sub(A, LC)
    big = []
    for i in range(n):
        big.append(M_ctrl[i] + BK[i])
    for i in range(n):
        big.append([0.0] * n + M_obs[i])
    ctrl_poly = characteristic_polynomial(M_ctrl)
    obs_poly = characteristic_polynomial(M_obs)
    big_poly = characteristic_polynomial(big)
    prod = _poly_mul(ctrl_poly, obs_poly)
    factorizes = len(prod) == len(big_poly) and all(
        abs(prod[i] - big_poly[i]) <= 1e-6 * max(1.0, abs(big_poly[i]))
        for i in range(len(big_poly))
    )
    return {
        "controller_poly": ctrl_poly,
        "observer_poly": obs_poly,
        "closed_loop_poly": big_poly,
        "factorizes": factorizes,
    }


def settling_time(poles):
    """2% settling time t_s = 4 / sigma in s.

    sigma is the minimum distance of the observer poles from the
    imaginary axis, sigma = min_i |Re(p_i)|. Raises ValueError when any
    pole has non-negative real part (the observer would not converge) or
    a pole is non-numeric.
    """
    if not poles:
        raise ValueError("need at least one observer pole")
    sigma = math.inf
    for p in poles:
        try:
            pf = complex(p)
        except (TypeError, ValueError):
            raise ValueError("observer pole %r is not numeric" % (p,))
        if pf.real >= 0.0:
            raise ValueError(
                "observer poles must be strictly stable, got %s" % (pf,)
            )
        sigma = min(sigma, abs(pf.real))
    if sigma <= _TOL:
        raise ValueError("observer poles must be off the imaginary axis")
    return 4.0 / sigma

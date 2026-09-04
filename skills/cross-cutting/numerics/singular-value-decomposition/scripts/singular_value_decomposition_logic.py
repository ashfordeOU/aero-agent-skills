"""Singular value decomposition by one-sided Jacobi rotations (stdlib only).

Deterministic, offline SVD of a general real rectangular matrix A (m x n)
using the one-sided Jacobi method: repeatedly rotate pairs of columns of the
working matrix until they are orthogonal, accumulating the right factor.
Returns the economy form A = U diag(s) Vh with U m x r, s length r and
Vh r x n where r = min(m, n).

Also provides the 2-norm condition number, the numerical rank at a relative
tolerance, and the Moore-Penrose inverse computed from the SVD factors.

Pure Python standard library, no RNG, deterministic run to run.
"""

import math

SVD_TOL = 1e-14
SVD_MAX_SWEEPS = 60
RANK_REL_TOL = 1e-12


def _is_number(x):
    """Return True for int or float entries, excluding booleans."""
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _validate(A):
    """Validate A as a non-empty rectangular list of numeric rows.

    Raises ValueError for an empty matrix, ragged rows or non-numeric
    entries. Returns (m, n).
    """
    if not isinstance(A, (list, tuple)) or len(A) == 0:
        raise ValueError("matrix must be a non-empty list of rows")
    n = len(A[0])
    if n == 0:
        raise ValueError("matrix rows must not be empty")
    for row in A:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError("matrix rows must all have the same length")
        for entry in row:
            if not _is_number(entry):
                raise ValueError("matrix entries must be numeric")
    return len(A), n


def _transpose(M):
    """Return the transpose of a list-of-lists matrix."""
    return [[M[i][j] for i in range(len(M))] for j in range(len(M[0]))]


def _pair_stats(B, m, p, q):
    """Return alpha, beta, gamma of column pair (p, q) of B (m rows)."""
    alpha = 0.0
    beta = 0.0
    gamma = 0.0
    for i in range(m):
        bp = B[i][p]
        bq = B[i][q]
        alpha += bp * bp
        beta += bq * bq
        gamma += bp * bq
    return alpha, beta, gamma


def _jacobi_rotation(alpha, beta, gamma):
    """Return (c, s) of the Jacobi rotation zeroing the pair correlation.

    Uses zeta = (beta - alpha) / (2 gamma) and the numerically stable form
    t = sign(zeta) / (|zeta| + sqrt(1 + zeta^2)) with t = 1 at zeta = 0.
    """
    zeta = (beta - alpha) / (2.0 * gamma)
    if zeta >= 0.0:
        t = 1.0 / (zeta + math.sqrt(1.0 + zeta * zeta))
    else:
        t = -1.0 / (-zeta + math.sqrt(1.0 + zeta * zeta))
    c = 1.0 / math.sqrt(1.0 + t * t)
    s = c * t
    return c, s


def _rotate_columns(B, V, m, n, p, q, c, s):
    """Rotate column pair (p, q) of B (m x n) and of V (n x n) by (c, s)."""
    for i in range(m):
        bp = B[i][p]
        bq = B[i][q]
        B[i][p] = c * bp - s * bq
        B[i][q] = s * bp + c * bq
    for j in range(n):
        vp = V[j][p]
        vq = V[j][q]
        V[j][p] = c * vp - s * vq
        V[j][q] = s * vp + c * vq


def _svd_tall(A, tol, max_sweeps):
    """One-sided Jacobi SVD for a tall or square matrix (m >= n).

    Returns (u, s, vh): economy U m x n, s length n descending, Vh n x n.
    """
    m, n = _validate(A)
    B = [list(map(float, row)) for row in A]
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    for _ in range(max_sweeps):
        changed = False
        for p in range(n):
            for q in range(p + 1, n):
                alpha, beta, gamma = _pair_stats(B, m, p, q)
                scale = alpha * beta
                if scale == 0.0:
                    continue
                if abs(gamma) > tol * math.sqrt(scale):
                    c, s = _jacobi_rotation(alpha, beta, gamma)
                    _rotate_columns(B, V, m, n, p, q, c, s)
                    changed = True
        if not changed:
            break
    s = [0.0] * n
    u = [[0.0] * n for _ in range(m)]
    for j in range(n):
        norm = 0.0
        for i in range(m):
            norm += B[i][j] * B[i][j]
        s[j] = math.sqrt(norm)
        if s[j] > 0.0:
            for i in range(m):
                u[i][j] = B[i][j] / s[j]
    order = sorted(range(n), key=lambda j: s[j], reverse=True)
    s = [s[j] for j in order]
    u = [[u[i][j] for j in order] for i in range(m)]
    vh = [[V[i][order[j]] for i in range(n)] for j in range(n)]
    return u, s, vh


def _reconstruction_residual(A, u, s, vh):
    """Return the Frobenius norm of A - U diag(s) Vh (economy form)."""
    m = len(A)
    r = len(s)
    n = len(vh[0])
    total = 0.0
    for i in range(m):
        for j in range(n):
            rec = 0.0
            for k in range(r):
                rec += u[i][k] * s[k] * vh[k][j]
            diff = A[i][j] - rec
            total += diff * diff
    return math.sqrt(total)


def svd_jacobi(A, tol=SVD_TOL, max_sweeps=SVD_MAX_SWEEPS):
    """Return the economy SVD dict {u, s, vh, reconstruction_residual}.

    A = U diag(s) Vh with U m x r, s length r = min(m, n) descending and
    Vh r x n. Wide matrices (m < n) are solved on A^T and the factors are
    swapped back. Raises ValueError for empty, ragged or non-numeric input.
    """
    m, n = _validate(A)
    if m < n:
        ut, s, vht = _svd_tall(_transpose(A), tol, max_sweeps)
        u = _transpose(vht)
        vh = _transpose(ut)
    else:
        u, s, vh = _svd_tall(A, tol, max_sweeps)
    residual = _reconstruction_residual(A, u, s, vh)
    return {"u": u, "s": s, "vh": vh, "reconstruction_residual": residual}


def condition_number(s):
    """Return the 2-norm condition number s_max / s_min.

    Returns inf when the smallest singular value is zero. Raises ValueError
    on an empty list or any negative singular value.
    """
    if not isinstance(s, (list, tuple)) or len(s) == 0:
        raise ValueError("singular values list must not be empty")
    if any(sj < 0.0 for sj in s):
        raise ValueError("singular values must be non-negative")
    s_min = min(s)
    if s_min == 0.0:
        return float("inf")
    return max(s) / s_min


def numerical_rank(s, rel_tol=RANK_REL_TOL):
    """Return the count of singular values above rel_tol * s_max.

    Raises ValueError on an empty singular values list.
    """
    if not isinstance(s, (list, tuple)) or len(s) == 0:
        raise ValueError("singular values list must not be empty")
    s_max = max(s)
    if s_max == 0.0:
        return 0
    return sum(1 for sj in s if sj > rel_tol * s_max)


def moore_penrose_inverse(A, rel_tol=RANK_REL_TOL):
    """Return the Moore-Penrose inverse V diag(1/s_j) U^T of A.

    The reciprocal is taken only for singular values above rel_tol * s_max;
    the others contribute zero. Raises ValueError for empty or ragged input.
    """
    m, n = _validate(A)
    svd = svd_jacobi(A)
    s = svd["s"]
    u = svd["u"]
    vh = svd["vh"]
    r = len(s)
    s_max = max(s) if s else 0.0
    pinv = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            acc = 0.0
            for k in range(r):
                if s[k] > rel_tol * s_max:
                    acc += vh[k][i] * (1.0 / s[k]) * u[j][k]
            pinv[i][j] = acc
    return pinv


def svd_report(A, tol=SVD_TOL, max_sweeps=SVD_MAX_SWEEPS, rel_tol=RANK_REL_TOL):
    """Return one dict with all SVD outputs for A.

    Keys: u, s, vh, reconstruction_residual, condition_number,
    numerical_rank, moore_penrose_inverse.
    """
    svd = svd_jacobi(A, tol, max_sweeps)
    rank = numerical_rank(svd["s"], rel_tol)
    pinv = moore_penrose_inverse(A, rel_tol)
    return {
        "u": svd["u"],
        "s": svd["s"],
        "vh": svd["vh"],
        "reconstruction_residual": svd["reconstruction_residual"],
        "condition_number": condition_number(svd["s"]),
        "numerical_rank": rank,
        "moore_penrose_inverse": pinv,
    }

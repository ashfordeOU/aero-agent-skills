#!/usr/bin/env python3
"""Eigenvalue decomposition (stdlib only, offline).

Implements eigenvalue and eigenvector computation for dense square
matrices with only the Python standard library:

- power_iteration: the dominant eigenvalue-eigenvector pair of a
  general square matrix by repeated multiplication and unit 2-norm
  normalization, with the Rayleigh quotient as the eigenvalue
  estimate and a convergence check on its change between iterates.
- deflate: rank-one subtraction A - lambda * v v^T that removes an
  already-found pair so the next power iteration yields the next
  dominant eigenvalue.
- power_spectrum: k dominant pairs of a general square matrix by
  power iteration with deflation between pairs.
- jacobi_eigen: the full spectrum of a real symmetric matrix by the
  Jacobi eigenvalue algorithm, sweeping off-diagonal pairs with plane
  rotations until the off-diagonal sum of squares falls below the
  sweep convergence tolerance.
- residual_norm: the maximum absolute residual ||A v - lambda v||_inf
  that verifies a returned pair.

No third-party imports (no numpy); only the Python standard library.
All functions are deterministic, validate their inputs, and raise
ValueError with a clear message on invalid arguments.

Worked anchors (verified by scripts/test_eigenvalue_logic.py):
- Power iteration: A = [[2, 0], [0, 1]] has dominant eigenvalue 2.0
  with eigenvector [1, 0]; the Rayleigh quotient sequence 1.5, 1.8,
  1.95, ... converges to 2.0.
- Deflation: subtracting 2.0 * [1, 0][1, 0]^T from [[2, 0], [0, 1]]
  gives [[0, 0], [0, 1]], whose dominant eigenvalue 1.0 is the
  second eigenvalue of A.
- Jacobi: A = [[2, 1], [1, 2]] has eigenvalues 3.0 and 1.0 with
  unit-norm eigenvectors [0.707, 0.707] and [0.707, -0.707]; the
  residual A v - lambda v is zero to machine precision.
- Jacobi 3x3: A = [[4, 1, 1], [1, 4, 1], [1, 1, 4]] has eigenvalues
  6.0, 3.0, 3.0 (6.0 for the all-ones vector).
"""

import math


def _as_square_float_matrix(A, what="A"):
    """Validate a square numeric matrix; return n and float rows.

    A must be a non-empty square list of lists (or tuple of tuples)
    whose entries are real numbers (int or float, not bool). Raises
    ValueError with a clear message otherwise. Rows are copied so the
    caller's matrix is never mutated.
    """
    if not isinstance(A, (list, tuple)) or len(A) == 0:
        raise ValueError("%s must be a non-empty list of rows" % what)
    n = len(A)
    out = []
    for i, row in enumerate(A):
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError(
                "%s must be square: row %d has length %d, expected %d"
                % (what, i, len(row) if isinstance(row, (list, tuple)) else -1, n)
            )
        frow = []
        for j, v in enumerate(row):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise ValueError(
                    "%s[%d][%d] must be a real number, got %r" % (what, i, j, v)
                )
            frow.append(float(v))
        out.append(frow)
    return n, out


def _as_float_vector(v, n, what="v"):
    """Validate a vector of length n; return floats."""
    if not isinstance(v, (list, tuple)) or len(v) != n:
        raise ValueError("%s must be a sequence of length %d" % (what, n))
    out = []
    for i, x in enumerate(v):
        if isinstance(x, bool) or not isinstance(x, (int, float)):
            raise ValueError("%s[%d] must be a real number, got %r" % (what, i, x))
        out.append(float(x))
    return out


def _norm2(v):
    """Euclidean (2-)norm of a vector."""
    return math.sqrt(sum(x * x for x in v))


def _mat_vec(A, v):
    """Matrix-vector product A v for a float matrix and float vector."""
    return [sum(A[i][j] * v[j] for j in range(len(v))) for i in range(len(A))]


def _unit(v):
    """Normalize a vector to unit 2-norm; raise on the zero vector."""
    nrm = _norm2(v)
    if nrm == 0.0:
        raise ValueError("cannot normalize the zero vector")
    return [x / nrm for x in v]


def residual_norm(A, v, lam):
    """Maximum absolute residual ||A v - lambda v||_inf of a pair.

    Returns max_i |sum_j A[i][j] * v[j] - lam * v[i]|, the natural
    check that (lam, v) is an eigenvalue-eigenvector pair. For a
    unit-norm v this is the absolute defect of the pair; a value at
    machine-epsilon scale confirms the pair, a larger value means
    the iteration did not converge or the wrong method was used.
    Raises ValueError for invalid inputs.

    Worked anchor: A = [[2, 0], [0, 1]] with v = [1, 0] and
    lam = 2.0 gives 0.0; with lam = 1.0 it gives 1.0.
    """
    n, M = _as_square_float_matrix(A)
    vv = _as_float_vector(v, n)
    if isinstance(lam, bool) or not isinstance(lam, (int, float)):
        raise ValueError("lam must be a real number, got %r" % (lam,))
    lf = float(lam)
    Av = _mat_vec(M, vv)
    worst = 0.0
    for i in range(n):
        r = abs(Av[i] - lf * vv[i])
        worst = max(worst, r)
    return worst


def power_iteration(A, tol=1e-10, max_iter=1000, v0=None):
    """Dominant eigenvalue-eigenvector pair of a square matrix.

    Power iteration with unit 2-norm normalization: v is repeatedly
    multiplied by A and renormalized, and the Rayleigh quotient
    lam = v^T A v (v unit norm) estimates the dominant eigenvalue.
    Converges when the pair residual ||A v - lam v||_inf falls at or
    below tol; the change in the Rayleigh quotient between iterates
    is the standard monitor but is not used alone as the stop, since
    the quotient converges quadratically while the eigenvector
    converges only linearly. Raises RuntimeError when the iteration
    does not converge within max_iter.

    Returns (lam, v) where lam is the largest-magnitude eigenvalue
    and v its unit-norm eigenvector. Raises ValueError for invalid
    inputs. v0 defaults to the all-ones vector; pass a custom v0
    when the default is orthogonal to the dominant eigenspace. A v0
    that lies exactly in another eigenspace returns that pair
    instead (the iteration cannot leave the eigenspace).

    Worked anchor: A = [[2, 0], [0, 1]] converges to lam = 2.0 and
    v = [1, 0]; the quotient sequence 1.5, 1.8, 1.95, ... settles on
    2.0.
    """
    n, M = _as_square_float_matrix(A)
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or tol <= 0:
        raise ValueError("tol must be a positive real number")
    if isinstance(max_iter, bool) or not isinstance(max_iter, int) or max_iter < 1:
        raise ValueError("max_iter must be a positive integer")
    if v0 is None:
        v0 = [1.0] * n
    v = _unit(_as_float_vector(v0, n))
    for _ in range(max_iter):
        Av = _mat_vec(M, v)
        lam = sum(v[i] * Av[i] for i in range(n))  # Rayleigh quotient
        res = max(abs(Av[i] - lam * v[i]) for i in range(n))
        if res <= tol:
            return lam, v
        v = _unit(Av)
    raise RuntimeError(
        "power_iteration did not converge within %d iterations" % max_iter
    )


def deflate(A, lam, v):
    """Deflate a found pair out of a matrix: A - lam * v v^T.

    For a unit-norm eigenvector v with eigenvalue lam, the rank-one
    subtraction A - lam * v v^T leaves every other eigenvalue and
    eigenvector unchanged and moves lam to zero, so power iteration
    on the deflated matrix yields the next dominant eigenvalue.
    Returns a new list-of-lists float matrix; the input is not
    mutated. Raises ValueError for invalid inputs.
    """
    n, M = _as_square_float_matrix(A)
    if isinstance(lam, bool) or not isinstance(lam, (int, float)):
        raise ValueError("lam must be a real number, got %r" % (lam,))
    vv = _as_float_vector(v, n)
    lf = float(lam)
    return [
        [M[i][j] - lf * vv[i] * vv[j] for j in range(n)] for i in range(n)
    ]


def _mixed_start(n):
    """Deterministic start vector with distinct entries.

    Returns [1.0, 1.37, 1.74, ...]. The distinct entries avoid the
    all-ones start being exactly orthogonal to an eigenvector of a
    deflated matrix, which would freeze power iteration in the wrong
    eigenspace (for example on [[0.5, -0.5], [-0.5, 0.5]] the
    all-ones vector is the zero-eigenvalue eigenvector).
    """
    return [1.0 + 0.37 * i for i in range(n)]


def power_spectrum(A, count=2, tol=1e-10, max_iter=1000):
    """The count largest-magnitude eigenvalue-eigenvector pairs.

    Runs power_iteration for the dominant pair, then deflates that
    pair out and repeats, returning a list of (lam, v) pairs in
    descending order of magnitude. Each run uses a deterministic
    mixed start vector (not the all-ones vector) so that deflated
    matrices whose eigenvectors sit on coordinate axes are still
    searched from every eigenspace. Raises ValueError for invalid
    inputs or when count is out of range.

    Worked anchor: A = [[2, 0], [0, 1]] with count=2 returns
    [(2.0, [1, 0]), (1.0, [0, 1])].
    """
    n, M = _as_square_float_matrix(A)
    if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= n:
        raise ValueError("count must be an integer in 1..%d" % n)
    pairs = []
    work = M
    for _ in range(count):
        lam, v = power_iteration(work, tol=tol, max_iter=max_iter, v0=_mixed_start(n))
        pairs.append((lam, v))
        work = deflate(work, lam, v)
    return pairs


def _is_symmetric(M, n):
    """True when M is symmetric to within 1e-10 times the largest entry."""
    scale = max(1.0, max(abs(M[i][j]) for i in range(n) for j in range(n)))
    for i in range(n):
        for j in range(i + 1, n):
            if abs(M[i][j] - M[j][i]) > 1e-10 * scale:
                return False
    return True


def jacobi_eigen(A, tol=1e-12, max_sweeps=100):
    """Full spectrum of a real symmetric matrix by the Jacobi method.

    Cyclic Jacobi: each sweep visits every off-diagonal pair (p, q)
    and applies a plane rotation that zeroes M[p][q]. The rotation
    angle satisfies tan(2*theta) = 2*M[p][q] / (M[q][q] - M[p][p]);
    rotations accumulate in V so its columns are the eigenvectors.
    Converges when the off-norm, the square root of
    the sum of squared off-diagonal entries, falls at or below tol.

    Returns (eigenvalues, eigenvectors): eigenvalues sorted in
    descending order, eigenvectors as the matching columns of V,
    each of unit 2-norm. Raises ValueError for invalid, non-square,
    or non-symmetric input, and RuntimeError when the sweeps do not
    converge within max_sweeps.

    Worked anchors: [[2, 1], [1, 2]] gives eigenvalues 3.0, 1.0 with
    unit eigenvectors [0.707, 0.707] and [0.707, -0.707]; the 3x3
    [[4, 1, 1], [1, 4, 1], [1, 1, 4]] gives 6.0, 3.0, 3.0.
    """
    n, M = _as_square_float_matrix(A)
    if isinstance(tol, bool) or not isinstance(tol, (int, float)) or tol <= 0:
        raise ValueError("tol must be a positive real number")
    if isinstance(max_sweeps, bool) or not isinstance(max_sweeps, int) or max_sweeps < 1:
        raise ValueError("max_sweeps must be a positive integer")
    if n == 1:
        return [M[0][0]], [[1.0]]
    if not _is_symmetric(M, n):
        raise ValueError("jacobi_eigen requires a symmetric matrix")

    # V accumulates the plane rotations; its columns end as eigenvectors.
    V = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

    def off_norm():
        return math.sqrt(
            sum(M[i][j] * M[i][j] for i in range(n) for j in range(n) if i != j)
        )

    for _ in range(max_sweeps):
        if off_norm() <= tol:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(M[p][q]) <= tol:
                    continue
                # Rotation angle from tan(2*theta) = 2*M[p][q]/(M[q][q]-M[p][p]);
                # t = tan(theta), c = cos(theta), s = sin(theta).
                theta = (M[q][q] - M[p][p]) / (2.0 * M[p][q])
                if theta == 0.0:
                    t = 1.0
                else:
                    t = 1.0 / (abs(theta) + math.sqrt(theta * theta + 1.0))
                c = 1.0 / math.sqrt(t * t + 1.0)
                s = t * c
                app = M[p][p]
                aqq = M[q][q]
                apq = M[p][q]
                # Rotation J = [[c, -s], [s, c]] on rows/cols (p, q):
                # A' = J^T A J, so the diagonal entries become
                # A'[p][p] = c^2 app + 2 s c apq + s^2 aqq and
                # A'[q][q] = s^2 app - 2 s c apq + c^2 aqq.
                M[p][p] = c * c * app + 2.0 * s * c * apq + s * s * aqq
                M[q][q] = s * s * app - 2.0 * s * c * apq + c * c * aqq
                M[p][q] = 0.0
                M[q][p] = 0.0
                # Update the remaining entries of rows/columns p and q.
                for k in range(n):
                    if k == p or k == q:
                        continue
                    akp = M[k][p]
                    akq = M[k][q]
                    M[k][p] = c * akp + s * akq
                    M[k][q] = -s * akp + c * akq
                    M[p][k] = M[k][p]
                    M[q][k] = M[k][q]
                # Accumulate the rotation into V (columns are eigenvectors):
                # V' = V J, so column p gains s * column q and column q
                # loses s * column p.
                for k in range(n):
                    vkp = V[k][p]
                    vkq = V[k][q]
                    V[k][p] = c * vkp + s * vkq
                    V[k][q] = -s * vkp + c * vkq
    if off_norm() > tol:
        raise RuntimeError(
            "jacobi_eigen did not converge within %d sweeps" % max_sweeps
        )

    eigenvalues = [M[i][i] for i in range(n)]
    eigenvectors = [[V[i][j] for i in range(n)] for j in range(n)]  # columns
    order = sorted(range(n), key=lambda i: eigenvalues[i], reverse=True)
    return (
        [eigenvalues[i] for i in order],
        [_unit(eigenvectors[i]) for i in order],
    )

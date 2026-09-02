#!/usr/bin/env python3
"""Dense matrix operations (stdlib only, offline).

Implements Gaussian elimination with partial pivoting for the dense
square linear system A x = b, plus the determinant, the matrix
inverse, and singularity detection built on the same elimination.
No third-party imports (no numpy); only the Python standard library.

All functions are deterministic, validate their inputs, and raise
ValueError with a clear message on invalid arguments.

Worked anchors (verified by scripts/test_matrix_operations.py):
- Solve: A = [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]], b = [8, -11, -3]
  gives x = [2, 3, -1] exactly (residual 0.0).
- Determinant: A = [[1, 2, 3], [0, 1, 4], [5, 6, 0]] gives det = 1.0;
  the 2x2 [[4, 7], [2, 6]] gives det = 10.0.
- Inverse: A = [[4, 7], [2, 6]] gives A**-1 = [[0.6, -0.7],
  [-0.2, 0.4]] and A * A**-1 = identity.
- Singularity: [[1, 2], [2, 4]] is singular (det 0.0, no inverse,
  no unique solution); [[1, 2], [3, 4]] is not (det -2.0).
- Partial pivoting rescues [[0, 1], [1, 0]]: the pivot search swaps
  the rows so the zero entry is never used as a pivot.
"""


def _as_float_matrix(A, what="A"):
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


def _as_float_vector(b, n, what="b"):
    """Validate a right-hand-side vector of length n; return floats."""
    if not isinstance(b, (list, tuple)) or len(b) != n:
        raise ValueError("%s must be a sequence of length %d" % (what, n))
    out = []
    for i, v in enumerate(b):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("%s[%d] must be a real number, got %r" % (what, i, v))
        out.append(float(v))
    return out


def _pivot_tol(A):
    """Absolute pivot tolerance: 1e-12 times the largest entry magnitude.

    Entries at or below this magnitude are treated as zero pivots, so
    the singular verdict is scale-aware: [[1, 2], [2, 4]] is flagged
    while [[1e6, 2e6], [3e6, 4e6]] is not.
    """
    scale = max(abs(v) for row in A for v in row)
    return 1e-12 * max(1.0, scale)


def solve(A, b):
    """Solve the dense square system A x = b by Gaussian elimination
    with partial pivoting.

    Returns the solution x as a list of n floats. The pivot search
    picks the largest-magnitude entry in the current column at or
    below the diagonal and swaps it into the pivot position, which
    keeps the elimination stable and avoids dividing by zero entries.
    Raises ValueError when the matrix is singular (a pivot at or
    below the tolerance) or the inputs are invalid.

    Worked anchor: A = [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]],
    b = [8, -11, -3] gives x = [2, 3, -1]; the residual
    A x - b is zero to machine precision.
    """
    n, M = _as_float_matrix(A)
    rhs = _as_float_vector(b, n)
    aug = [M[i] + [rhs[i]] for i in range(n)]
    tol = _pivot_tol(M)
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(aug[i][k]))
        if abs(aug[p][k]) <= tol:
            raise ValueError(
                "matrix is singular: zero pivot at column %d; no unique solution" % k
            )
        if p != k:
            aug[k], aug[p] = aug[p], aug[k]
        pivot = aug[k][k]
        for i in range(k + 1, n):
            factor = aug[i][k] / pivot
            if factor != 0.0:
                for j in range(k, n + 1):
                    aug[i][j] -= factor * aug[k][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (aug[i][n] - sum(aug[i][j] * x[j] for j in range(i + 1, n))) / aug[i][i]
    return x


def determinant(A):
    """Determinant of a dense square matrix by elimination with
    partial pivoting.

    The determinant is the product of the pivots times (-1) to the
    power of the number of row swaps. Returns 0.0 when the matrix is
    singular instead of raising, which is the standard singularity
    signal. Raises ValueError for invalid inputs.

    Worked anchors: A = [[1, 2, 3], [0, 1, 4], [5, 6, 0]] gives 1.0
    (one swap flips the sign of the pivot product 5 * 1 * -0.2);
    [[4, 7], [2, 6]] gives 10.0; [[1, 2], [2, 4]] gives 0.0.
    """
    n, M = _as_float_matrix(A)
    tol = _pivot_tol(M)
    swaps = 0
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(M[i][k]))
        if abs(M[p][k]) <= tol:
            return 0.0
        if p != k:
            M[k], M[p] = M[p], M[k]
            swaps += 1
        pivot = M[k][k]
        for i in range(k + 1, n):
            factor = M[i][k] / pivot
            if factor != 0.0:
                for j in range(k, n):
                    M[i][j] -= factor * M[k][j]
    det = 1.0
    for k in range(n):
        det *= M[k][k]
    return -det if swaps % 2 else det


def inverse(A):
    """Inverse of a dense square matrix by Gauss-Jordan elimination
    with partial pivoting on the augmented block [A | I].

    Returns the inverse as a list of n lists of n floats. Raises
    ValueError when the matrix is singular (no inverse exists) or the
    inputs are invalid.

    Worked anchor: A = [[4, 7], [2, 6]] gives
    [[0.6, -0.7], [-0.2, 0.4]]; A times the result is the identity
    to machine precision.
    """
    n, M = _as_float_matrix(A)
    aug = [M[i] + [1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    tol = _pivot_tol(M)
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(aug[i][k]))
        if abs(aug[p][k]) <= tol:
            raise ValueError(
                "matrix is singular: zero pivot at column %d; no inverse exists" % k
            )
        if p != k:
            aug[k], aug[p] = aug[p], aug[k]
        pivot = aug[k][k]
        aug[k] = [v / pivot for v in aug[k]]
        for i in range(n):
            if i == k:
                continue
            factor = aug[i][k]
            if factor != 0.0:
                for j in range(2 * n):
                    aug[i][j] -= factor * aug[k][j]
    return [row[n:] for row in aug]


def is_singular(A, tol=None):
    """Singularity detection for a dense square matrix.

    Runs the same elimination as solve and reports whether any pivot
    falls at or below the tolerance (default: 1e-12 times the largest
    entry magnitude). Returns True for a singular matrix, False
    otherwise. Never raises for a singular matrix; raises ValueError
    only for invalid inputs.

    Worked anchors: [[1, 2], [2, 4]] (proportional rows) is singular;
    [[1, 2], [3, 4]] with det -2.0 is not.
    """
    n, M = _as_float_matrix(A)
    if tol is not None:
        if isinstance(tol, bool) or not isinstance(tol, (int, float)) or tol <= 0:
            raise ValueError("tol must be a positive real number")
        pivot_tol = float(tol)
    else:
        pivot_tol = _pivot_tol(M)
    for k in range(n):
        p = max(range(k, n), key=lambda i: abs(M[i][k]))
        if abs(M[p][k]) <= pivot_tol:
            return True
        if p != k:
            M[k], M[p] = M[p], M[k]
        pivot = M[k][k]
        for i in range(k + 1, n):
            factor = M[i][k] / pivot
            if factor != 0.0:
                for j in range(k, n):
                    M[i][j] -= factor * M[k][j]
    return False


def residual_norm(A, b, x):
    """Maximum absolute residual ||A x - b||_inf of a candidate solve.

    Returns max_i |sum_j A[i][j] * x[j] - b[i]|, the natural check
    that a returned x actually solves A x = b. Raises ValueError for
    invalid inputs. Worked anchor: for A = [[2, 1, -1], [-3, -1, 2],
    [-2, 1, 2]], b = [8, -11, -3] and x = [2, 3, -1] the residual is
    0.0; for x = [0, 0, 0] it is 11.0.
    """
    n, M = _as_float_matrix(A)
    rhs = _as_float_vector(b, n)
    xv = _as_float_vector(x, n, "x")
    worst = 0.0
    for i in range(n):
        r = abs(sum(M[i][j] * xv[j] for j in range(n)) - rhs[i])
        worst = max(worst, r)
    return worst

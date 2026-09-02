#!/usr/bin/env python3
"""State-space control analysis logic (stdlib only, no numpy).

Analyzes a linear time-invariant system in state-space representation

    x_dot = A x + B u
    y = C x + D u

where A is the n x n system matrix, B is n x m, C is p x n. This module
computes, with the standard library alone:

- matrix rank by Gaussian elimination (used for the controllability and
  observability tests),
- the controllability matrix [B AB A^2B ... A^(n-1)B] and the
  observability matrix [C; CA; CA^2; ...; CA^(n-1)],
- controllability and observability verdicts from those ranks,
- the eigenvalues of a 2x2 system matrix via the characteristic
  polynomial lambda^2 - tr(A) lambda + det(A) = 0, solved by hand with
  the quadratic formula,
- the stability verdict (all eigenvalue real parts < 0),
- the state transition matrix Phi(t) = exp(A t) for 2x2 A via the
  Cayley-Hamilton expansion Phi = alpha0 I + alpha1 A,
- the controller and observer canonical forms for 2x2 controllable
  systems, built from the characteristic polynomial coefficients.

This is generic state-space control methodology, not RTCA or SAE
content; ARP4754A is referenced only as the development-assurance
context for control law work (standards-map.yaml).

Conventions: matrices are lists of rows (lists of floats). B is a
column matrix (n x 1) and C is a row matrix (1 x n); the helpers accept
the general m-input / p-output shapes for the rank tests.
"""

import cmath
import math


def _require_square(A, name="A"):
    """Raise ValueError unless A is a non-empty square matrix of rows."""
    if not isinstance(A, list) or len(A) == 0:
        raise ValueError("%s must be a non-empty list of rows" % name)
    n = len(A)
    for i, row in enumerate(A):
        if not isinstance(row, list) or len(row) != n:
            raise ValueError(
                "%s must be square: row %d has length %d, expected %d"
                % (name, i, len(row), n)
            )


def _require_matrix(M, name="M"):
    """Raise ValueError unless M is a non-empty rectangular matrix."""
    if not isinstance(M, list) or len(M) == 0:
        raise ValueError("%s must be a non-empty list of rows" % name)
    ncols = len(M[0])
    for i, row in enumerate(M):
        if not isinstance(row, list) or len(row) != ncols:
            raise ValueError(
                "%s rows must be equal length: row %d has %d columns, expected %d"
                % (name, i, len(row), ncols)
            )
    if ncols == 0:
        raise ValueError("%s must have at least one column" % name)


def mat_mul(A, B):
    """Matrix product A * B (A is k x n, B is n x m)."""
    _require_matrix(A, "A")
    _require_matrix(B, "B")
    n = len(A[0])
    if len(B) != n:
        raise ValueError(
            "mat_mul: A has %d columns but B has %d rows" % (n, len(B))
        )
    return [
        [sum(A[i][k] * B[k][j] for k in range(n)) for j in range(len(B[0]))]
        for i in range(len(A))
    ]


def matrix_rank(M, tol=1e-9):
    """Rank of M by Gaussian elimination with partial pivoting.

    Operates on a working copy: for each column, the row with the
    largest absolute entry at or below the current pivot row is swapped
    in, then multiples of the pivot row eliminate the entries below.
    A pivot is counted only when its absolute value exceeds
    tol * max(1.0, max absolute entry of the whole matrix), which keeps
    the test scale-independent.
    """
    _require_matrix(M, "M")
    work = [list(row) for row in M]
    rows = len(work)
    cols = len(work[0])
    if rows == 0 or cols == 0:
        return 0
    scale = max(1.0, max(abs(v) for row in work for v in row))
    threshold = tol * scale
    rank = 0
    pivot_col = 0
    for pivot_row in range(rows):
        if pivot_col >= cols:
            break
        best = pivot_row
        best_abs = abs(work[pivot_row][pivot_col])
        for r in range(pivot_row + 1, rows):
            a = abs(work[r][pivot_col])
            if a > best_abs:
                best = r
                best_abs = a
        if best_abs <= threshold:
            pivot_col += 1
            continue
        if best != pivot_row:
            work[pivot_row], work[best] = work[best], work[pivot_row]
        piv = work[pivot_row][pivot_col]
        for r in range(pivot_row + 1, rows):
            factor = work[r][pivot_col] / piv
            if factor == 0.0:
                continue
            for c in range(pivot_col, cols):
                work[r][c] -= factor * work[pivot_row][c]
        rank += 1
        pivot_col += 1
    return rank


def _block_matrix(blocks):
    """Stack row blocks; each block is a list of rows."""
    out = []
    for block in blocks:
        _require_matrix(block, "block")
        out.extend(block)
    return out


def controllability_matrix(A, B):
    """Controllability matrix [B AB A^2B ... A^(n-1)B], n x (n*m).

    For an n-state system with m inputs the matrix has n rows and
    n*m columns. A ValueError is raised when A is not square or B does
    not have n rows.
    """
    _require_square(A, "A")
    _require_matrix(B, "B")
    n = len(A)
    if len(B) != n:
        raise ValueError(
            "controllability_matrix: A is %dx%d but B has %d rows"
            % (n, n, len(B))
        )
    power = [list(row) for row in B]
    cols = [list(row) for row in B]
    for _ in range(n - 1):
        power = mat_mul(A, power)
        cols = [cols[i] + power[i] for i in range(n)]
    return cols


def observability_matrix(A, C):
    """Observability matrix [C; CA; CA^2; ...; CA^(n-1)], (p*n) x n.

    For an n-state system with p outputs the matrix has p*n rows and
    n columns. A ValueError is raised when A is not square or C does
    not have n columns.
    """
    _require_square(A, "A")
    _require_matrix(C, "C")
    n = len(A)
    if len(C[0]) != n:
        raise ValueError(
            "observability_matrix: A is %dx%d but C has %d columns"
            % (n, n, len(C[0]))
        )
    power = [list(row) for row in C]
    blocks = [list(row) for row in C]
    for _ in range(n - 1):
        power = mat_mul(power, A)
        blocks.extend(list(row) for row in power)
    return blocks


def is_controllable(A, B, tol=1e-9):
    """True when rank([B AB ... A^(n-1)B]) == n (n states)."""
    _require_square(A, "A")
    _require_matrix(B, "B")
    n = len(A)
    if len(B) != n:
        raise ValueError("is_controllable: B must have %d rows" % n)
    return matrix_rank(controllability_matrix(A, B), tol) == n


def is_observable(A, C, tol=1e-9):
    """True when rank([C; CA; ...; CA^(n-1)]) == n (n states)."""
    _require_square(A, "A")
    _require_matrix(C, "C")
    n = len(A)
    if len(C[0]) != n:
        raise ValueError("is_observable: C must have %d columns" % n)
    return matrix_rank(observability_matrix(A, C), tol) == n


def eigenvalues_2x2(A):
    """Eigenvalues of a 2x2 matrix via the characteristic polynomial.

    The characteristic polynomial of a 2x2 A is

        lambda^2 - tr(A) lambda + det(A) = 0,

    solved by hand with the quadratic formula:

        lambda = (tr(A) +- sqrt(tr(A)^2 - 4 det(A))) / 2.

    Returns a list of two complex numbers (Python complex, so a real
    pair comes back with zero imaginary parts). Raises ValueError for
    any other size.
    """
    _require_square(A, "A")
    if len(A) != 2:
        raise ValueError(
            "eigenvalues_2x2: expected a 2x2 matrix, got %dx%d" % (len(A), len(A[0]))
        )
    trace = A[0][0] + A[1][1]
    det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    disc = trace * trace - 4.0 * det
    root = cmath.sqrt(complex(disc, 0.0))
    return [(trace + root) / 2.0, (trace - root) / 2.0]


def is_stable(A, tol=1e-12):
    """True when every eigenvalue of A has real part < 0.

    For a 2x2 system matrix the eigenvalues come from the
    characteristic polynomial; for larger matrices the eigenvalues are
    not available in this stdlib implementation and a ValueError is
    raised. tol is the margin below zero that counts as unstable.
    """
    _require_square(A, "A")
    if len(A) != 2:
        raise ValueError(
            "is_stable: eigenvalue-based stability is implemented for 2x2 "
            "matrices only, got %dx%d" % (len(A), len(A[0]))
        )
    return all(lamb.real < -tol for lamb in eigenvalues_2x2(A))


def stability_report(A, tol=1e-12):
    """Eigenvalues plus the stability verdict for a 2x2 system matrix.

    Returns dict with 'eigenvalues' (list of complex) and 'stable'
    (bool: all real parts < 0). A zero real part is marginal and
    counts as not stable.
    """
    _require_square(A, "A")
    values = eigenvalues_2x2(A)
    return {"eigenvalues": values, "stable": all(v.real < -tol for v in values)}


def _cayley_hamilton_coeffs(lamb1, lamb2, t):
    """Coefficients alpha0, alpha1 of exp(A t) = alpha0 I + alpha1 A.

    Distinct eigenvalues: exp(lamb1 t) = alpha0 + alpha1 lamb1 and
    exp(lamb2 t) = alpha0 + alpha1 lamb2, a 2x2 linear system solved
    by hand. Repeated eigenvalue lamb: alpha1 = t exp(lamb t) and
    alpha0 = exp(lamb t) - lamb alpha1 (derivative of the first
    equation with respect to the eigenvalue).
    """
    e1 = cmath.exp(lamb1 * t)
    if abs(lamb1 - lamb2) > 1e-12:
        e2 = cmath.exp(lamb2 * t)
        alpha1 = (e1 - e2) / (lamb1 - lamb2)
        alpha0 = e1 - alpha1 * lamb1
    else:
        alpha1 = t * e1
        alpha0 = e1 - lamb1 * alpha1
    return alpha0, alpha1


def state_transition_matrix(A, t):
    """State transition matrix Phi(t) = exp(A t) for a 2x2 matrix A.

    Uses the Cayley-Hamilton expansion Phi = alpha0 I + alpha1 A where
    the coefficients follow from the eigenvalues (see
    _cayley_hamilton_coeffs). Works for distinct real, repeated real,
    and complex-conjugate eigenvalue pairs; complex intermediate
    arithmetic collapses to a real matrix, returned as floats.
    """
    _require_square(A, "A")
    if len(A) != 2:
        raise ValueError(
            "state_transition_matrix: implemented for 2x2 matrices only, "
            "got %dx%d" % (len(A), len(A[0]))
        )
    lamb1, lamb2 = eigenvalues_2x2(A)
    alpha0, alpha1 = _cayley_hamilton_coeffs(lamb1, lamb2, t)
    phi = [
        [alpha0 + alpha1 * A[0][0], alpha1 * A[0][1]],
        [alpha1 * A[1][0], alpha0 + alpha1 * A[1][1]],
    ]
    # Collapse tiny imaginary residue from complex arithmetic.
    out = []
    for row in phi:
        out.append([v.real if abs(v.imag) < 1e-9 * max(1.0, abs(v)) else v for v in row])
    return out


def controller_canonical_form(A, B):
    """Controller canonical form (A_c, B_c) for a 2x2 controllable pair.

    With the characteristic polynomial lambda^2 + a1 lambda + a0, the
    controller canonical pair is

        A_c = [[0, 1], [-a0, -a1]],  B_c = [[0], [1]],

    where a0 = det(A) and a1 = -tr(A) (coefficients recovered from the
    eigenvalues of A). The pair shares A's characteristic polynomial.
    Raises ValueError when the system is not controllable or not 2x2.
    """
    _require_square(A, "A")
    _require_matrix(B, "B")
    if len(A) != 2:
        raise ValueError(
            "controller_canonical_form: implemented for 2x2 matrices only, "
            "got %dx%d" % (len(A), len(A[0]))
        )
    if not is_controllable(A, B):
        raise ValueError("controller_canonical_form: the (A, B) pair is not controllable")
    a0 = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    a1 = -(A[0][0] + A[1][1])
    return [[0.0, 1.0], [-a0, -a1]], [[0.0], [1.0]]


def observer_canonical_form(A, C):
    """Observer canonical form (A_o, C_o) for a 2x2 observable pair.

    The observer (dual) canonical pair transposes the controller
    canonical A and carries C_o = [1, 0]:

        A_o = [[0, -a0], [1, -a1]],  C_o = [1, 0],

    again with a0 = det(A) and a1 = -tr(A). Raises ValueError when the
    system is not observable or not 2x2.
    """
    _require_square(A, "A")
    _require_matrix(C, "C")
    if len(A) != 2:
        raise ValueError(
            "observer_canonical_form: implemented for 2x2 matrices only, "
            "got %dx%d" % (len(A), len(A[0]))
        )
    if not is_observable(A, C):
        raise ValueError("observer_canonical_form: the (A, C) pair is not observable")
    a0 = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    a1 = -(A[0][0] + A[1][1])
    return [[0.0, -a0], [1.0, -a1]], [1.0, 0.0]


def analysis_report(A, B, C, t=None):
    """One-shot report for a 2x2 state-space model.

    Returns dict with controllability and observability verdicts, the
    eigenvalue list, the stability verdict, and (when t is given) the
    state transition matrix at time t. Convenience wrapper over the
    individual functions above.
    """
    _require_square(A, "A")
    if len(A) != 2:
        raise ValueError("analysis_report: implemented for 2x2 models only")
    report = {
        "controllable": is_controllable(A, B),
        "observable": is_observable(A, C),
        "eigenvalues": eigenvalues_2x2(A),
        "stable": is_stable(A),
    }
    if t is not None:
        report["state_transition_matrix"] = state_transition_matrix(A, t)
    return report

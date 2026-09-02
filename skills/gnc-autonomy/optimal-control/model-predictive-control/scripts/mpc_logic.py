#!/usr/bin/env python3
"""Model predictive control (MPC) for linear discrete-time systems.

Pure Python 3, standard library only, deterministic. No numpy, no scipy.

Plant: x[k+1] = A x[k] + B u[k] with x in R^n, u in R^m.

Finite-horizon quadratic cost over prediction horizon N with control
horizon Nc <= N and terminal cost Pf:

  J = x_N' Pf x_N + sum_{k=0}^{N-1} (x_k' Q x_k + u_k' R u_k)

with u_k held at u_{Nc-1} for k >= Nc when Nc < N.  Stacking the free
inputs U = [u_0; ...; u_{Nc-1}] in R^{m*Nc} and the predicted states
X = [x_1; ...; x_N] = S x0 + T U (S: nN x n, T: nN x mNc) condenses
the problem to a dense QP in m*Nc variables:

  min_U   0.5 U' H U + f' U
  s.t.    umin <= u_k <= umax        (input bounds, per component)
          xmin <= x_k <= xmax        (state bounds, per component)
          x_N = 0                    (optional terminal equality)

with H = T' Qbar T + Rbar and f = T' Qbar S x0, where Qbar =
blockdiag(Q, ..., Q, Pf) and Rbar = blockdiag(R, ..., (N-Nc+1) R).
The x0' Q x0 constant term is dropped; it cannot change the argmin.

Solver (deterministic, no external QP library):
  * equality-constrained case: the KKT system
        [H  Aeq'] [U ]   [-f ]
        [Aeq  0 ] [lam] = [beq]
    is solved exactly by dense Gaussian elimination with partial
    pivoting (solve_kkt).
  * inequality case (input bounds and/or state bounds): a primal
    active-set method on the KKT system, warm-started from the
    unconstrained solution clipped to the input box. Each iteration
    either adds the most violated inactive constraint or drops the
    active constraint with the most negative multiplier; bounded by
    max_iter, so behavior is fully deterministic.

Receding horizon: solve the N-step problem from the current state,
apply only u0, step the plant, repeat (simulate_closed_loop).

Unit convention: no units are imposed; keep A, B, Q, R, Pf, x0, umin,
umax, xmin, xmax in one consistent SI set (seconds for the discrete
step, radians for angles, N or N m for inputs) so that the running
cost x'Qx + u'Ru is dimensionless.
"""

import math

_TOL = 1e-9
_MAX_QP_ITER = 400
_DEFAULT_TOL = 1e-8


# ----------------------------------------------------------------------
# Dense linear algebra helpers (stdlib only, deterministic)
# ----------------------------------------------------------------------

def _mat_mul(A, B):
    """Matrix product A (n x m) times B (m x p)."""
    n, m, p = len(A), len(B), len(B[0])
    return [[sum(A[i][k] * B[k][j] for k in range(m)) for j in range(p)]
            for i in range(n)]


def _mat_vec(A, x):
    """Matrix-vector product A x."""
    return [sum(row[j] * x[j] for j in range(len(x))) for row in A]


def _mat_transpose(A):
    return [[A[i][j] for i in range(len(A))] for j in range(len(A[0]))]


def _mat_add(A, B):
    return [[A[i][j] + B[i][j] for j in range(len(A[0]))]
            for i in range(len(A))]


def _mat_scale(s, A):
    return [[s * v for v in row] for row in A]


def _vec_add(a, b):
    return [x + y for x, y in zip(a, b)]


def _vec_sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _vec_scale(s, a):
    return [s * x for x in a]


def _vec_dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _vec_norm(a):
    return math.sqrt(sum(x * x for x in a))


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _zeros(n, m):
    return [[0.0] * m for _ in range(n)]


def _block_diag(blocks):
    """Block-diagonal matrix from a list of square blocks."""
    size = sum(len(b) for b in blocks)
    M = _zeros(size, size)
    r = 0
    for b in blocks:
        for i in range(len(b)):
            for j in range(len(b)):
                M[r + i][r + j] = b[i][j]
        r += len(b)
    return M


def _det(M):
    """Determinant by Gaussian elimination with partial pivoting."""
    A = [row[:] for row in M]
    n = len(A)
    d = 1.0
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) <= _TOL:
            return 0.0
        if piv != col:
            A[col], A[piv] = A[piv], A[col]
            d = -d
        d *= A[col][col]
        for r in range(col + 1, n):
            fac = A[r][col] / A[col][col]
            if fac != 0.0:
                for c in range(col, n):
                    A[r][c] -= fac * A[col][c]
    return d


def solve_linear_system(M, b):
    """Solve M x = b (square M) by Gaussian elimination with partial
    pivoting. Raises ValueError on a singular system."""
    n = len(M)
    A = [row[:] for row in M]
    bb = [float(v) for v in b]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        if abs(A[piv][col]) <= _TOL:
            raise ValueError("singular linear system")
        if piv != col:
            A[col], A[piv] = A[piv], A[col]
            bb[col], bb[piv] = bb[piv], bb[col]
        for r in range(col + 1, n):
            fac = A[r][col] / A[col][col]
            if fac != 0.0:
                for c in range(col, n):
                    A[r][c] -= fac * A[col][c]
                bb[r] -= fac * bb[col]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = bb[r] - sum(A[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / A[r][r]
    return x


def solve_kkt(H, f, Aeq, beq):
    """Solve the KKT system of the equality-constrained QP

        min_U 0.5 U' H U + f' U   subject to  Aeq U = beq,

    namely [H Aeq'; Aeq 0] [U; lam] = [-f; beq].  Solved exactly by
    dense Gaussian elimination (deterministic).  Returns (U, lam)."""
    n = len(H)
    p = len(Aeq)
    M = [row[:] + [Aeq[j][i] for j in range(p)] for i, row in enumerate(H)]
    for j in range(p):
        M.append(list(Aeq[j]) + [0.0] * p)
    rhs = [-float(v) for v in f] + [float(v) for v in beq]
    sol = solve_linear_system(M, rhs)
    return sol[:n], sol[n:]


# ----------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------

def _as_matrix(M, name):
    """Coerce M to a 2D list of floats. Raises ValueError otherwise."""
    if not isinstance(M, (list, tuple)) or not M:
        raise ValueError("%s must be a non-empty matrix, got %r" % (name, M))
    rows = []
    for row in M:
        if not isinstance(row, (list, tuple)) or len(row) != len(M[0]):
            raise ValueError("%s must be a rectangular matrix, got %r"
                             % (name, M))
        try:
            rows.append([float(v) for v in row])
        except (TypeError, ValueError):
            raise ValueError("%s entries must be numeric, got %r" % (name, M))
    return rows


def _as_vec(v, name, length=None):
    """Coerce v to a flat list of floats of the given length."""
    if not isinstance(v, (list, tuple)):
        raise ValueError("%s must be a vector, got %r" % (name, v))
    try:
        out = [float(x) for x in v]
    except (TypeError, ValueError):
        raise ValueError("%s entries must be numeric, got %r" % (name, v))
    if length is not None and len(out) != length:
        raise ValueError("%s must have length %d, got %d"
                         % (name, length, len(out)))
    return out


def _check_symmetric(M, name):
    n = len(M)
    for i in range(n):
        for j in range(n):
            if abs(M[i][j] - M[j][i]) > _TOL:
                raise ValueError("%s must be symmetric, got %r" % (name, M))


def _principal_minors(M):
    """All non-empty principal minors of a square matrix (deterministic)."""
    n = len(M)
    minors = []
    for mask in range(1, 1 << n):
        idx = [i for i in range(n) if mask & (1 << i)]
        sub = [[M[i][j] for j in idx] for i in idx]
        minors.append(_det(sub))
    return minors


def _check_psd(M, name):
    """Positive semidefinite: all principal minors >= -tol (n small)."""
    _check_symmetric(M, name)
    if any(m < -_TOL for m in _principal_minors(M)):
        raise ValueError("%s must be positive semidefinite, got %r" % (name, M))


def _check_pd(M, name):
    """Positive definite: all leading principal minors > tol (Sylvester)."""
    _check_symmetric(M, name)
    n = len(M)
    for k in range(1, n + 1):
        lead = [row[:k] for row in M[:k]]
        if _det(lead) <= _TOL:
            raise ValueError("%s must be positive definite, got %r" % (name, M))


def check_problem(A, B, Q, R, N, Nc=None, Pf=None, umin=None, umax=None,
                  xmin=None, xmax=None):
    """Validate the full MPC problem. Raises ValueError on any invalid
    dimension, non-numeric entry, sign violation, or contradictory bound.

    Returns (n, m) after coercion."""
    if not isinstance(N, int) or N < 1:
        raise ValueError("N (prediction horizon) must be an int >= 1, got %r"
                         % (N,))
    A = _as_matrix(A, "A")
    if len(A) != len(A[0]):
        raise ValueError("A must be square, got %d x %d"
                         % (len(A), len(A[0])))
    n = len(A)
    B = _as_matrix(B, "B")
    if len(B) != n:
        raise ValueError("B must have %d rows to match A, got %d"
                         % (n, len(B)))
    m = len(B[0])
    if m < 1:
        raise ValueError("B must have at least one input column")
    Q = _as_matrix(Q, "Q")
    if len(Q) != n or len(Q[0]) != n:
        raise ValueError("Q must be %d x %d to match A, got %d x %d"
                         % (n, n, len(Q), len(Q[0])))
    _check_psd(Q, "Q")
    if isinstance(R, (int, float)):
        if m != 1:
            raise ValueError("scalar R requires a single input (m = 1), "
                             "got m = %d; pass a %d x %d matrix instead"
                             % (m, m, m))
        R = [[float(R)]]
    R = _as_matrix(R, "R")
    if len(R) != m or len(R[0]) != m:
        raise ValueError("R must be %d x %d to match B, got %d x %d"
                         % (m, m, len(R), len(R[0])))
    _check_pd(R, "R")
    if Nc is not None:
        if not isinstance(Nc, int) or Nc < 1 or Nc > N:
            raise ValueError("Nc (control horizon) must be an int in [1, N] "
                             "= [1, %d], got %r" % (N, Nc))
    else:
        Nc = N
    if Pf is not None:
        Pf = _as_matrix(Pf, "Pf")
        if len(Pf) != n or len(Pf[0]) != n:
            raise ValueError("Pf must be %d x %d to match A, got %d x %d"
                             % (n, n, len(Pf), len(Pf[0])))
        _check_psd(Pf, "Pf")
    else:
        Pf = _zeros(n, n)
    if umin is not None:
        umin = _as_vec(umin, "umin", length=m)
    if umax is not None:
        umax = _as_vec(umax, "umax", length=m)
    if umin is not None and umax is not None:
        for i in range(m):
            if umin[i] > umax[i] + _TOL:
                raise ValueError("umin[%d] = %g > umax[%d] = %g: empty input "
                                 "feasible set" % (i, umin[i], i, umax[i]))
    if xmin is not None:
        xmin = _as_vec(xmin, "xmin", length=n)
    if xmax is not None:
        xmax = _as_vec(xmax, "xmax", length=n)
    if xmin is not None and xmax is not None:
        for i in range(n):
            if xmin[i] > xmax[i] + _TOL:
                raise ValueError("xmin[%d] = %g > xmax[%d] = %g: empty state "
                                 "feasible set" % (i, xmin[i], i, xmax[i]))
    return n, m, Nc, Pf, umin, umax, xmin, xmax


def feasible(A, B, Q, R, N, umin=None, umax=None, x0=None, Nc=None,
             Pf=None, xmin=None, xmax=None, terminal_eq=False):
    """Return True when the MPC problem is dimensionally and logically
    feasible, False when a bound set is empty or dimensions clash."""
    try:
        n, m, Nc, Pf, umin, umax, xmin, xmax = check_problem(
            A, B, Q, R, N, Nc=Nc, Pf=Pf, umin=umin, umax=umax,
            xmin=xmin, xmax=xmax)
        if x0 is not None:
            _as_vec(x0, "x0", length=n)
        if terminal_eq and x0 is None:
            _as_vec([0.0] * n, "x0", length=n)
        return True
    except ValueError:
        return False


# ----------------------------------------------------------------------
# Condensed prediction and cost matrices
# ----------------------------------------------------------------------

def _prediction_matrices(A, B, N, Nc):
    """Return (S, T) with X = S x0 + T U.

    S: nN x n (stacked A^1 .. A^N).  T: nN x mNc, block rows k = 1..N,
    block columns j = 0..Nc-1.  For j < Nc-1 the input u_j acts only
    through A^{k-1-j} B when j <= k-1; for j = Nc-1 the held input
    acts through sum_{i=Nc-1}^{k-1} A^{k-1-i} B when k-1 >= Nc-1."""
    n, m = len(A), len(B[0])
    Apow = [_identity(n)]
    for _ in range(N):
        Apow.append(_mat_mul(Apow[-1], A))
    S = []
    for k in range(1, N + 1):
        for row in Apow[k]:
            S.append(row)
    T = _zeros(n * N, m * Nc)
    for k in range(1, N + 1):
        for j in range(Nc):
            if j < Nc - 1:
                C = _mat_mul(Apow[k - 1 - j], B) if j <= k - 1 \
                    else _zeros(n, m)
            else:
                if k - 1 >= Nc - 1:
                    C = _zeros(n, m)
                    for i in range(Nc - 1, k):
                        C = _mat_add(C, _mat_mul(Apow[k - 1 - i], B))
                else:
                    C = _zeros(n, m)
            for i in range(n):
                for l in range(m):
                    T[(k - 1) * n + i][j * m + l] = C[i][l]
    return S, T


def _cost_matrices(Q, R, Pf, N, Nc):
    """Return (Qbar, Rbar): block-diagonal cost matrices.

    Qbar = blockdiag(Q, ..., Q, Pf) with N blocks; Rbar = blockdiag(R,
    ..., (N - Nc + 1) R) with Nc blocks, the last block scaled because
    the held input u_{Nc-1} is charged N - Nc + 1 times."""
    qblocks = [Q] * (N - 1) + [Pf]
    rblocks = [R] * (Nc - 1) + [_mat_scale(N - Nc + 1, R)]
    return _block_diag(qblocks), _block_diag(rblocks)


def build_qp(A, B, Q, R, N, x0, Nc=None, Pf=None, umin=None, umax=None,
             xmin=None, xmax=None, terminal_eq=False):
    """Assemble the condensed QP for the current state x0.

    Returns a dict with:
      H, f       dense QP data (min 0.5 U'H U + f'U)
      rows, bs   inequality rows (row' U <= b): input box first, then
                 state bounds over the prediction
      box_idx    indices into rows of the input-box rows
      Aeq, beq   terminal equality x_N = 0 when terminal_eq
      n, m, N, Nc, S, T, x0
    Deterministic; raises ValueError via check_problem."""
    n, m, Nc, Pf, umin, umax, xmin, xmax = check_problem(
        A, B, Q, R, N, Nc=Nc, Pf=Pf, umin=umin, umax=umax,
        xmin=xmin, xmax=xmax)
    x0 = _as_vec(x0, "x0", length=n)
    A = _as_matrix(A, "A")
    B = _as_matrix(B, "B")
    Q = _as_matrix(Q, "Q")
    if isinstance(R, (int, float)):
        R = [[float(R)]]
    R = _as_matrix(R, "R")

    S, T = _prediction_matrices(A, B, N, Nc)
    Qbar, Rbar = _cost_matrices(Q, R, Pf, N, Nc)
    Tt = _mat_transpose(T)
    H = _mat_add(_mat_mul(Tt, _mat_mul(Qbar, T)), Rbar)
    f = _mat_vec(Tt, _mat_vec(_mat_mul(Qbar, S), x0))

    # Inequality rows: input box first, then state bounds.
    rows, bs, box_idx = [], [], []
    nu = m * Nc
    for j in range(Nc):
        for l in range(m):
            idx = j * m + l
            row = [0.0] * nu
            if umin is not None and umin[l] is not None:
                row[idx] = -1.0          # -u <= -umin  <=>  u >= umin
                rows.append(list(row))
                bs.append(-umin[l])
                box_idx.append(len(rows) - 1)
            if umax is not None and umax[l] is not None:
                row[idx] = 1.0           # u <= umax
                rows.append(list(row))
                bs.append(umax[l])
                box_idx.append(len(rows) - 1)
    if xmin is not None or xmax is not None:
        Sx0 = _mat_vec(S, x0)
        for k in range(1, N + 1):
            Tk = T[(k - 1) * n:k * n]
            sx = Sx0[(k - 1) * n:k * n]
            for i in range(n):
                if xmax is not None:
                    row = [Tk[i][j] for j in range(nu)]   # x_k[i] <= xmax[i]
                    rows.append(row)
                    bs.append(xmax[i] - sx[i])
                if xmin is not None:
                    row = [-Tk[i][j] for j in range(nu)]  # -x_k[i] <= -xmin[i]
                    rows.append(row)
                    bs.append(-xmin[i] + sx[i])

    Aeq, beq = [], []
    if terminal_eq:
        Aeq = [row[:] for row in T[(N - 1) * n:N * n]]
        Sx0N = _mat_vec(S[(N - 1) * n:N * n], x0)
        beq = [-v for v in Sx0N]

    return {"H": H, "f": f, "rows": rows, "bs": bs, "box_idx": box_idx,
            "Aeq": Aeq, "beq": beq, "n": n, "m": m, "N": N, "Nc": Nc,
            "S": S, "T": T, "x0": x0}


# ----------------------------------------------------------------------
# QP solver: primal active-set on the KKT system (deterministic)
# ----------------------------------------------------------------------

def solve_qp(H, f, rows, bs, box_idx=None, max_iter=_MAX_QP_ITER,
             tol=_DEFAULT_TOL):
    """Solve min 0.5 x'H x + f'x subject to rows_i' x <= b_i.

    Deterministic primal active-set method.  The working set is
    warm-started from the unconstrained minimizer clipped to the input
    box rows (box_idx), then each iteration either adds the most
    violated inactive constraint or drops the active constraint with
    the most negative multiplier.  Equality-constrained subproblems
    are solved exactly through the KKT system (solve_kkt).

    Returns (x, info) with info = {iterations, active, multipliers}.
    Raises ValueError if the QP does not converge within max_iter
    (deterministic failure) or a KKT subproblem is singular."""
    n = len(H)
    n_ineq = len(rows)
    box_idx = box_idx or []

    # Warm start: unconstrained minimizer, clipped to the box.
    try:
        x = solve_linear_system(H, [-float(v) for v in f])
    except ValueError:
        x = [0.0] * n
    if box_idx:
        for i in box_idx:
            # row i is +e or -e with bound b; recover the variable index
            nz = [j for j in range(n) if abs(rows[i][j]) > _TOL]
            if len(nz) == 1:
                j = nz[0]
                if rows[i][j] > 0 and x[j] > bs[i]:
                    x[j] = bs[i]
                elif rows[i][j] < 0 and x[j] < -bs[i]:
                    x[j] = -bs[i]

    W = []          # active inequality rows (indices into rows/bs)
    for i in box_idx:
        nz = [j for j in range(n) if abs(rows[i][j]) > _TOL]
        if len(nz) == 1:
            j = nz[0]
            if (rows[i][j] > 0 and abs(x[j] - bs[i]) <= tol) or \
               (rows[i][j] < 0 and abs(x[j] + bs[i]) <= tol):
                W.append(i)
    lam = []

    for it in range(max_iter):
        if W:
            Aeq = [rows[j] for j in W]
            beq = [bs[j] for j in W]
            try:
                x, lam = solve_kkt(H, f, Aeq, beq)
            except ValueError:
                W.pop()              # dependent working set: drop and retry
                continue
        # Step 1: most violated inactive constraint.
        viol_i, viol_val = -1, tol
        for i in range(n_ineq):
            if i in W:
                continue
            v = _vec_dot(rows[i], x) - bs[i]
            if v > viol_val:
                viol_val, viol_i = v, i
        if viol_i >= 0:
            W.append(viol_i)
            continue
        # Step 2: active constraint with the most negative multiplier.
        drop, drop_val = -1, -tol
        for idx, j in enumerate(W):
            if lam[idx] < drop_val:
                drop_val, drop = lam[idx], idx
        if drop >= 0:
            W.pop(drop)
            continue
        # Step 3: KKT conditions satisfied.
        return x, {"iterations": it + 1, "active": list(W),
                   "multipliers": [float(v) for v in lam]}
    raise ValueError("active-set QP did not converge within %d iterations"
                     % max_iter)


# ----------------------------------------------------------------------
# MPC layer
# ----------------------------------------------------------------------

def mpc_solve(A, B, Q, R, N, umin=None, umax=None, x0=None, Nc=None,
              Pf=None, xmin=None, xmax=None, terminal_eq=False,
              tol=_DEFAULT_TOL):
    """Solve the finite-horizon QP from x0; return the full open-loop
    plan (u_seq, x_seq, info).

    u_seq: list of N inputs u_0 .. u_{N-1} (held after Nc-1 when Nc < N).
    x_seq: list of N+1 predicted states x_0 .. x_N.
    info:  dict with solver diagnostics {method, iterations, active,
           multipliers}.

    Equality-constrained case (terminal_eq and no inequality rows):
    the KKT system is solved exactly (method 'kkt').  Inequality case:
    deterministic active set (method 'active-set')."""
    data = build_qp(A, B, Q, R, N, x0, Nc=Nc, Pf=Pf, umin=umin, umax=umax,
                    xmin=xmin, xmax=xmax, terminal_eq=terminal_eq)
    H, f, rows, bs = data["H"], data["f"], data["rows"], data["bs"]
    n, m, Nc = data["n"], data["m"], data["Nc"]
    if terminal_eq:
        Aeq, beq = data["Aeq"], data["beq"]
        U, lam = solve_kkt(H, f, Aeq, beq)
        info = {"method": "kkt", "iterations": 1,
                "active": ["terminal"], "multipliers": [float(v) for v in lam]}
    elif rows:
        U, qpinfo = solve_qp(H, f, rows, bs, box_idx=data["box_idx"],
                             tol=tol)
        info = dict(qpinfo)
        info["method"] = "active-set"
    else:
        U = solve_linear_system(H, [-float(v) for v in f])
        info = {"method": "kkt", "iterations": 1, "active": [],
                "multipliers": []}
    nu = m * Nc
    if len(U) != nu:
        raise ValueError("internal error: QP size mismatch (%d != %d)"
                         % (len(U), nu))
    u_free = [U[j * m:(j + 1) * m] for j in range(Nc)]
    u_seq = u_free + [list(u_free[-1]) for _ in range(N - Nc)]
    x_seq = [list(data["x0"])]
    A = _as_matrix(A, "A")
    B = _as_matrix(B, "B")
    for k in range(N):
        x_seq.append(_vec_add(_mat_vec(A, x_seq[-1]), _mat_vec(B, u_seq[k])))
    return u_seq, x_seq, info


def mpc_controller(A, B, Q, R, N, umin=None, umax=None, x0=None, Nc=None,
                   Pf=None, xmin=None, xmax=None, terminal_eq=False,
                   tol=_DEFAULT_TOL):
    """Return the first control move u0 (list of length m) of the
    receding-horizon solution for the current state x0.

    Deterministic, stdlib only.  Raises ValueError on invalid
    dimensions (bad A/B/Q/R shapes, N < 1, Nc > N, umin > umax,
    xmin > xmax, non-numeric entries) or when the QP fails to
    converge."""
    u_seq, _x_seq, _info = mpc_solve(A, B, Q, R, N, umin=umin, umax=umax,
                                     x0=x0, Nc=Nc, Pf=Pf, xmin=xmin,
                                     xmax=xmax, terminal_eq=terminal_eq,
                                     tol=tol)
    return list(u_seq[0])


# ----------------------------------------------------------------------
# Discrete-time system and closed-loop simulation
# ----------------------------------------------------------------------

class DiscreteSystem:
    """Discrete-time LTI plant x[k+1] = A x[k] + B u[k]."""

    def __init__(self, A, B):
        A = _as_matrix(A, "A")
        if len(A) != len(A[0]):
            raise ValueError("A must be square, got %d x %d"
                             % (len(A), len(A[0])))
        B = _as_matrix(B, "B")
        if len(B) != len(A):
            raise ValueError("B must have %d rows to match A, got %d"
                             % (len(A), len(B)))
        self.A = A
        self.B = B
        self.n = len(A)
        self.m = len(B[0])

    def step(self, x, u):
        """Propagate one step: x_next = A x + B u."""
        x = _as_vec(x, "x", length=self.n)
        u = _as_vec(u, "u", length=self.m)
        return _vec_add(_mat_vec(self.A, x), _mat_vec(self.B, u))


def simulate_closed_loop(system, controller, x0, steps):
    """Run the receding-horizon closed loop for `steps` steps.

    system: DiscreteSystem (or any object with step(x, u) -> x_next).
    controller: callable x -> u (e.g. lambda x: mpc_controller(...,
    x0=x)).  Returns the list of states x_0 .. x_steps (length
    steps + 1).  Deterministic: identical inputs give identical
    trajectories."""
    if not isinstance(steps, int) or steps < 0:
        raise ValueError("steps must be an int >= 0, got %r" % (steps,))
    x = _as_vec(x0, "x0")
    traj = [list(x)]
    for _ in range(steps):
        u = _as_vec(controller(list(x)), "u")
        x = system.step(x, u)
        traj.append(list(x))
    return traj


def kkt_residual(H, f, rows, bs, x, lam_active):
    """Stationarity residual of the box-constrained QP at x.

    For the optimal box-constrained solution the reduced gradient
    (gradient projected onto the free directions) must vanish.  Used
    by the contract test to verify the solver independent of the
    internal active-set bookkeeping."""
    g = [_vec_dot(H[i], x) + f[i] for i in range(len(H))]
    res = 0.0
    for i, gi in enumerate(g):
        lo = hi = None
        for r, b in zip(rows, bs):
            nz = [j for j in range(len(x)) if abs(r[j]) > _TOL]
            if len(nz) == 1 and nz[0] == i:
                if r[i] > 0:
                    hi = b
                else:
                    lo = -b
        if lo is not None and x[i] <= lo + 1e-9:
            res = max(res, -gi)          # pushing into lower bound is OK
        elif hi is not None and x[i] >= hi - 1e-9:
            res = max(res, gi)           # pushing into upper bound is OK
        else:
            res = max(res, abs(gi))
    return res


def terminal_cost_solution(A, B, Q, R, N, x0, Pf=None):
    """Finite-horizon LQR first gain K0 from the Riccati recursion.

    Independent derivation path (dynamic programming) used to
    cross-check the condensed QP: P_N = Pf, then for k = N-1 .. 0:
      K_k = (R + B' P_{k+1} B)^-1 B' P_{k+1} A
      P_k = Q + A' P_{k+1} A - A' P_{k+1} B K_k
    Returns (K0, P0) so the caller can form u0 = -K0 x0."""
    n, m, Nc, Pf, _u, _v, _w, _z = check_problem(A, B, Q, R, N, Pf=Pf)
    A = _as_matrix(A, "A")
    B = _as_matrix(B, "B")
    Q = _as_matrix(Q, "Q")
    if isinstance(R, (int, float)):
        R = [[float(R)]]
    R = _as_matrix(R, "R")
    x0 = _as_vec(x0, "x0", length=n)
    P = [row[:] for row in Pf]
    Bt = _mat_transpose(B)
    At = _mat_transpose(A)
    K = None
    for _k in range(N - 1, -1, -1):
        BtP = _mat_mul(Bt, P)                    # m x n
        M = _mat_add(R, _mat_mul(BtP, B))        # m x m, PD
        Minv = _inverse_via_solve(M)
        K = _mat_mul(Minv, _mat_mul(BtP, A))     # m x n
        P = _mat_add(Q, _mat_sub(_mat_mul(At, _mat_mul(P, A)),
                                 _mat_mul(At, _mat_mul(P, _mat_mul(B, K)))))
    return K, P


def _mat_sub(A, B):
    return [[A[i][j] - B[i][j] for j in range(len(A[0]))]
            for i in range(len(A))]


def _inverse_via_solve(M):
    """Matrix inverse by solving M X = I (deterministic)."""
    n = len(M)
    cols = []
    for j in range(n):
        e = [1.0 if i == j else 0.0 for i in range(n)]
        cols.append(solve_linear_system(M, e))
    return [[cols[j][i] for j in range(n)] for i in range(n)]

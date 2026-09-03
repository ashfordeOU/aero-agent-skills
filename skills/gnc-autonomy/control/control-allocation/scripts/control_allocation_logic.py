"""Static control allocation math for redundant aerospace effectors.

Pure Python stdlib. The commanded moment vector m (n x 1, roll pitch
yaw) is produced by effector deflections u (m x 1) through the control
effectiveness matrix B (n x m, n <= m for redundancy): m = B u.

This module implements the static allocation strategies only: the
minimum-norm pseudoinverse, damped least squares, weighted least
squares, position-limit clipping with residual redistribution over the
unsaturated effectors (redistributed pseudoinverse), rate limiting,
daisy-chain splitting between a primary and a secondary effector group,
direct allocation as box-constrained scaling of the commanded
direction, and the allocation verdict (achieved moment, error norm,
saturated effector list).

Module constants:
- EPSILON: singularity tolerance and regularization for B B^T.
- MAX_ITER: cap on redistribution passes over the residual.
"""

import math

EPSILON = 1e-9
MAX_ITER = 5


def _require_finite_matrix(b):
    for row in b:
        for value in row:
            if not math.isfinite(value):
                raise ValueError("control effectiveness matrix must be finite")


def _require_finite_vector(v, name):
    for value in v:
        if not math.isfinite(value):
            raise ValueError("{} must be finite".format(name))


def _validate_system(b, m):
    """Return (n_rows, n_effectors) after dimension and finiteness checks."""
    if not b or not m:
        raise ValueError("effectiveness matrix and moment command cannot be empty")
    n_rows = len(b)
    n_eff = len(b[0])
    if n_rows == 0 or n_eff == 0:
        raise ValueError("effectiveness matrix must have at least one row and one column")
    for row in b:
        if len(row) != n_eff:
            raise ValueError("effectiveness matrix rows must share one length")
    if len(m) != n_rows:
        raise ValueError("moment command dimension must match the number of effectiveness rows")
    _require_finite_matrix(b)
    _require_finite_vector(m, "moment command")
    if n_rows > n_eff:
        raise ValueError("underactuated system: more moment axes than effectors")
    return n_rows, n_eff


def _validate_limits(u_min, u_max, n_eff):
    if len(u_min) != n_eff or len(u_max) != n_eff:
        raise ValueError("limit vectors must have one entry per effector")
    _require_finite_vector(u_min, "lower limit vector")
    _require_finite_vector(u_max, "upper limit vector")
    for lo, hi in zip(u_min, u_max):
        if lo > hi:
            raise ValueError("lower limit must not exceed the upper limit")


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _solve_linear(a, rhs):
    """Gauss-Jordan solve with partial pivoting; None when singular."""
    n = len(a)
    aug = [a[i][:] + [rhs[i]] for i in range(n)]
    for col in range(n):
        pivot = col
        best = abs(aug[col][col])
        for row in range(col + 1, n):
            candidate = abs(aug[row][col])
            if candidate > best:
                best = candidate
                pivot = row
        if best <= EPSILON:
            return None
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col] / pv
            for entry in range(col, n + 1):
                aug[row][entry] -= factor * aug[col][entry]
    return [aug[i][n] / aug[i][i] for i in range(n)]


def _gram_bbt(b, n_rows):
    n_eff = len(b[0])
    return [
        [sum(b[i][k] * b[j][k] for k in range(n_eff)) for j in range(n_rows)]
        for i in range(n_rows)
    ]


def _pinv_from_gram(b, gram, m, n_rows, n_eff):
    """u = B^T (B B^T)^-1 m with regularization when B B^T is singular."""
    x = _solve_linear(gram, m)
    if x is None:
        reg = [
            [gram[i][j] + (EPSILON if i == j else 0.0) for j in range(n_rows)]
            for i in range(n_rows)
        ]
        x = _solve_linear(reg, m)
    if x is None:
        raise ValueError("effectiveness matrix is rank deficient beyond regularization")
    return [sum(b[i][k] * x[i] for i in range(n_rows)) for k in range(n_eff)]


def pseudoinverse_alloc(b, m):
    """Minimum-norm allocation u = B^+ m with B^+ = B^T (B B^T)^-1.

    Returns the smallest-norm deflection vector that reproduces the
    commanded moment exactly when the system is solvable.
    """
    n_rows, n_eff = _validate_system(b, m)
    gram = _gram_bbt(b, n_rows)
    return _pinv_from_gram(b, gram, m, n_rows, n_eff)


def damped_least_squares_alloc(b, m, lam):
    """u = B^T (B B^T + lam I)^-1 m, the regularized damped least squares.

    lam must be non-negative; lam = 0 delegates to the pseudoinverse.
    """
    n_rows, n_eff = _validate_system(b, m)
    if not math.isfinite(lam) or lam < 0.0:
        raise ValueError("damping term lam must be finite and non-negative")
    gram = _gram_bbt(b, n_rows)
    if lam == 0.0:
        return _pinv_from_gram(b, gram, m, n_rows, n_eff)
    damped = [
        [gram[i][j] + (lam if i == j else 0.0) for j in range(n_rows)]
        for i in range(n_rows)
    ]
    return _pinv_from_gram(b, damped, m, n_rows, n_eff)


def weighted_alloc(b, w_diag, m):
    """Weighted allocation minimizing u^T W u subject to B u = m.

    Closed form u = W^-1 B^T (B W^-1 B^T)^-1 m with W = diag(w_diag).
    w_diag holds the per-effector cost weights; an effector with a
    smaller cost weight (cheaper to deflect) takes a larger share of
    the command, so raising an effector's weight pushes command off it.
    """
    n_rows, n_eff = _validate_system(b, m)
    if len(w_diag) != n_eff:
        raise ValueError("weight vector must have one entry per effector")
    _require_finite_vector(w_diag, "weight vector")
    for w in w_diag:
        if w <= 0.0:
            raise ValueError("weights must be strictly positive")
    winv = [1.0 / w for w in w_diag]
    gram = [
        [sum(b[i][k] * winv[k] * b[j][k] for k in range(n_eff)) for j in range(n_rows)]
        for i in range(n_rows)
    ]
    x = _solve_linear(gram, m)
    if x is None:
        reg = [
            [gram[i][j] + (EPSILON if i == j else 0.0) for j in range(n_rows)]
            for i in range(n_rows)
        ]
        x = _solve_linear(reg, m)
    if x is None:
        raise ValueError("weighted gram matrix is rank deficient beyond regularization")
    return [
        winv[k] * sum(b[i][k] * x[i] for i in range(n_rows)) for k in range(n_eff)
    ]


def clip_to_limits(u, u_min, u_max):
    """Clip u to [u_min, u_max]; returns (u_clipped, saturated_mask).

    An effector is saturated when its requested deflection lies outside
    its position limits by more than EPSILON.
    """
    _require_finite_vector(u, "deflection vector")
    _validate_limits(u_min, u_max, len(u))
    clipped = []
    mask = []
    for value, lo, hi in zip(u, u_min, u_max):
        if value < lo - EPSILON:
            clipped.append(lo)
            mask.append(True)
        elif value > hi + EPSILON:
            clipped.append(hi)
            mask.append(True)
        else:
            clipped.append(value)
            mask.append(False)
    return clipped, mask


def _matvec(b, u):
    return [sum(b[i][k] * u[k] for k in range(len(u))) for i in range(len(b))]


def redistribute_pseudoinverse(b, m, u_min, u_max, max_iter=MAX_ITER):
    """Redistributed pseudoinverse allocation under position limits.

    Scheme: minimum-norm solve, clip to the position limits, then for up
    to max_iter passes solve for the residual moment on the unsaturated
    effector set only (pseudoinverse restricted to the free columns) and
    add the increment. Saturated effectors stay pinned at their limit.
    """
    n_rows, n_eff = _validate_system(b, m)
    _validate_limits(u_min, u_max, n_eff)
    if max_iter < 0:
        raise ValueError("max_iter must be non-negative")
    u0 = pseudoinverse_alloc(b, m)
    u, saturated = clip_to_limits(u0, u_min, u_max)
    for _ in range(max_iter):
        free = [i for i in range(n_eff) if not saturated[i]]
        if not free:
            break
        achieved = _matvec(b, u)
        residual = [m[i] - achieved[i] for i in range(n_rows)]
        if _norm(residual) <= EPSILON:
            break
        b_free = [[b[i][k] for k in free] for i in range(n_rows)]
        increment = pseudoinverse_alloc(b_free, residual)
        progress = False
        for j, index in enumerate(free):
            target = u[index] + increment[j]
            lo = u_min[index]
            hi = u_max[index]
            next_value = min(max(target, lo), hi)
            if abs(next_value - u[index]) > EPSILON:
                progress = True
            u[index] = next_value
            if target < lo - EPSILON or target > hi + EPSILON:
                saturated[index] = True
        if not progress:
            break
    return u


def rate_limit(u, u_prev, dt, rate_max):
    """Limit the per-step deflection change to rate_max.

    u_dot = (u - u_prev) / dt is clipped componentwise to +/-rate_max,
    so the returned command moves at most rate_max * dt per effector.
    rate_max is a scalar or one entry per effector.
    """
    if len(u) != len(u_prev):
        raise ValueError("command and previous command must share one length")
    _require_finite_vector(u, "command")
    _require_finite_vector(u_prev, "previous command")
    if not math.isfinite(dt) or dt <= 0.0:
        raise ValueError("time step dt must be finite and positive")
    if isinstance(rate_max, (int, float)):
        rate = [float(rate_max)] * len(u)
    else:
        rate = list(rate_max)
        if len(rate) != len(u):
            raise ValueError("rate_max must be a scalar or one entry per effector")
    for value in rate:
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("rate_max must be finite and non-negative")
    limited = []
    for cmd, prev, rm in zip(u, u_prev, rate):
        step = rm * dt
        delta = min(max(cmd - prev, -step), step)
        limited.append(prev + delta)
    return limited


def daisy_chain_alloc(b_primary, b_secondary, m, u_min_p, u_max_p, u_min_s, u_max_s):
    """Daisy-chain allocation: primary group first, residual to secondary.

    The primary group (aerodynamic surfaces) is allocated up to its
    position limits with the pseudoinverse; the residual moment is then
    passed to the secondary group (thrust vectoring or RCS). Returns
    (u_primary, u_secondary), both clipped to their own limits.
    """
    n_rows, _ = _validate_system(b_primary, m)
    n_rows_s, n_eff_s = _validate_system(b_secondary, m)
    if n_rows_s != n_rows:
        raise ValueError("both effectiveness groups must act on the same moment axes")
    n_eff_p = len(b_primary[0])
    _validate_limits(u_min_p, u_max_p, n_eff_p)
    _validate_limits(u_min_s, u_max_s, n_eff_s)
    u_primary, _ = clip_to_limits(pseudoinverse_alloc(b_primary, m), u_min_p, u_max_p)
    achieved_p = _matvec(b_primary, u_primary)
    residual = [m[i] - achieved_p[i] for i in range(n_rows)]
    u_secondary, _ = clip_to_limits(
        pseudoinverse_alloc(b_secondary, residual), u_min_s, u_max_s
    )
    return u_primary, u_secondary


def direct_alloc(b, m, u_min, u_max):
    """Direct allocation: largest scaling of the commanded direction in the box.

    The commanded direction m_hat = m / ||m|| is preimaged by the
    minimum-norm solution u_dir = B^+ m_hat. The per-axis position
    limits bound the scale s of s * u_dir linearly, so the largest
    feasible scale inside the actuator box is found in closed form
    (no bisection needed for box constraints). The returned command is
    s * u_dir with s = min(||m||, s_box): the full moment when the box
    contains the minimum-norm preimage, otherwise the box-bound
    saturated command along the commanded direction.
    """
    n_rows, n_eff = _validate_system(b, m)
    _validate_limits(u_min, u_max, n_eff)
    norm_m = _norm(m)
    if norm_m <= EPSILON:
        return [0.0] * n_eff
    m_hat = [value / norm_m for value in m]
    u_dir = pseudoinverse_alloc(b, m_hat)
    lower = 0.0
    upper = float("inf")
    for i in range(n_eff):
        d = u_dir[i]
        if d > EPSILON:
            lower = max(lower, u_min[i] / d)
            upper = min(upper, u_max[i] / d)
        elif d < -EPSILON:
            lower = max(lower, u_max[i] / d)
            upper = min(upper, u_min[i] / d)
    if upper < lower:
        return [0.0] * n_eff
    scale = min(norm_m, upper)
    return [scale * d for d in u_dir]


def allocation_verdict(b, m, u, u_min=None, u_max=None):
    """Allocation verdict dict: achieved moment, error norm, saturation.

    Keys: achieved_moment (B u as a list), error_norm (||m - B u||),
    saturated_effectors (indices pinned at a position limit within
    EPSILON, or [] when no limits are supplied).
    """
    n_rows, n_eff = _validate_system(b, m)
    if len(u) != n_eff:
        raise ValueError("deflection vector must have one entry per effector")
    _require_finite_vector(u, "deflection vector")
    achieved = _matvec(b, u)
    error = _norm([m[i] - achieved[i] for i in range(n_rows)])
    saturated = []
    if u_min is not None and u_max is not None:
        _validate_limits(u_min, u_max, n_eff)
        for i in range(n_eff):
            pinned_hard = u_min[i] >= u_max[i] - EPSILON
            at_lower = u[i] <= u_min[i] + EPSILON
            at_upper = u[i] >= u_max[i] - EPSILON
            if pinned_hard or at_lower or at_upper:
                saturated.append(i)
    return {
        "achieved_moment": achieved,
        "error_norm": error,
        "saturated_effectors": saturated,
    }

"""Discretize continuous white noise into a discrete process-noise covariance.

Pure stdlib (math only), deterministic (no RNG, plain row-by-row matrix
accumulation, no generator-sum float reassociation). Implements the van
Loan closed form for the exact matrix-exponential discretization of a
linear plant driven by continuous white noise:

  dx/dt = F*x + G*w,  E[w(t) w(s)^T] = Qc * delta(t - s)
  W = G*Qc*G^T (continuous noise strength in state space)
  x_k = Phi_d*x_(k-1) + w_d,  Phi_d = exp(F*dt),
  Qd = integral_0^dt Phi(tau) W Phi(tau)^T d tau

van Loan form: with the 2n x 2n augmented matrix
B = [[-F, W],[0, F^T]]*dt and E = exp(B) = [[E11, E12],[0, E22]],
Phi_d = E22^T and Qd = Phi_d*E12.

Public API (7): mat_exp, state_transition_matrix, continuous_noise_map,
van_loan_discretize, discrete_white_noise_acceleration,
random_walk_covariance, ins_velocity_random_walk_covariance.
"""

import math

_TAYLOR_MAX_TERMS = 80          # hard cap on the Taylor series length
_TAYLOR_REL_TOL = 1e-15         # newest-term stopping tolerance (relative)
_SCALE_MAX_ABS = 0.5            # scaling-and-squaring entry bound
_SYM_TOL = 1e-9                 # symmetry tolerance for Qc
_MINOR_TOL = 1e-9               # principal-minor tolerance for PSD test


def _validate_square(a, name):
    """Return the order n of a non-empty square list-of-lists matrix.

    Raise ValueError if a is not a non-empty square matrix (covers empty,
    non-square and ragged inputs)."""
    if not isinstance(a, list) or not a:
        raise ValueError(name + " must be a non-empty square matrix")
    n = len(a)
    for row in a:
        if not isinstance(row, list) or len(row) != n:
            raise ValueError(name + " must be a non-empty square matrix")
    return n


def _identity(n):
    """Return the n x n identity matrix as a list of lists."""
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _matmul(a, b):
    """Plain row-by-row accumulated matrix product a*b (deterministic)."""
    p = len(b)
    m = len(b[0]) if p else 0
    out = []
    for i in range(len(a)):
        row = []
        for j in range(m):
            acc = 0.0
            for k in range(p):
                acc += a[i][k] * b[k][j]
            row.append(acc)
        out.append(row)
    return out


def _transpose(a):
    """Return the transpose of a."""
    return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]


def _maxabs(a):
    """Return the maximum absolute entry of a."""
    best = 0.0
    for row in a:
        for v in row:
            av = abs(v)
            if av > best:
                best = av
    return best


def _det(a):
    """Determinant of a by Laplace expansion along the first row."""
    n = len(a)
    if n == 1:
        return a[0][0]
    if n == 2:
        return a[0][0] * a[1][1] - a[0][1] * a[1][0]
    total = 0.0
    for j in range(n):
        minor = [row[:j] + row[j + 1:] for row in a[1:]]
        term = a[0][j] * _det(minor)
        total += term if j % 2 == 0 else -term
    return total


def _combinations(items, k):
    """All k-element subsets of items, each as a list, index-ordered."""
    result = []
    n = len(items)

    def _rec(start, chosen):
        if len(chosen) == k:
            result.append(list(chosen))
            return
        for i in range(start, n):
            chosen.append(items[i])
            _rec(i + 1, chosen)
            chosen.pop()

    _rec(0, [])
    return result


def _is_psd_symmetric(a):
    """True if a is symmetric within 1e-9 and every principal minor is
    >= -1e-9 (positive semi-definite by the principal-minor criterion)."""
    n = len(a)
    for i in range(n):
        for j in range(n):
            if abs(a[i][j] - a[j][i]) > _SYM_TOL:
                return False
    idx = list(range(n))
    for k in range(1, n + 1):
        for subset in _combinations(idx, k):
            minor = [[a[i][j] for j in subset] for i in subset]
            if _det(minor) < -_MINOR_TOL:
                return False
    return True


def mat_exp(a):
    """Return exp(a) by scaling and squaring plus a Taylor power series.

    Scale a by 2^-s until its maximum absolute entry is <= 0.5, sum the
    Taylor series until the newest term's maximum absolute entry is below
    1e-15 relative to the running total (hard cap 80 terms), then square
    the result s times. The identity matrix for the zero matrix is exact.
    Raise ValueError if a is empty or non-square."""
    n = _validate_square(a, "a")
    s = 0
    scaled = [row[:] for row in a]
    while _maxabs(scaled) > _SCALE_MAX_ABS and s < 64:
        scaled = [[v * 0.5 for v in row] for row in scaled]
        s += 1
    term = _identity(n)
    total = [row[:] for row in term]
    for k in range(1, _TAYLOR_MAX_TERMS + 1):
        term = _matmul(term, scaled)
        term = [[v / k for v in row] for row in term]
        total = [[total[i][j] + term[i][j] for j in range(n)]
                 for i in range(n)]
        if _maxabs(term) <= _TAYLOR_REL_TOL * max(1.0, _maxabs(total)):
            break
    for _ in range(s):
        total = _matmul(total, total)
    return total


def state_transition_matrix(f, dt):
    """Return the discrete state transition matrix Phi_d = exp(f*dt).

    Raise ValueError if f is non-square or dt <= 0."""
    n = _validate_square(f, "f")
    if dt <= 0:
        raise ValueError("dt must be positive")
    scaled = [[v * dt for v in row] for row in f]
    return mat_exp(scaled)


def continuous_noise_map(g, qc):
    """Return the continuous noise strength W = g*qc*g^T (n x n).

    Raise ValueError if g is empty or ragged, qc is empty or non-square,
    the g row length does not match the Qc order, Qc is not symmetric, or
    Qc is not positive semi-definite."""
    if not isinstance(g, list) or not g:
        raise ValueError("g must be a non-empty matrix")
    n = len(g)
    for row in g:
        if not isinstance(row, list) or not row:
            raise ValueError("g must be a non-empty matrix")
    m = len(g[0])
    for row in g:
        if len(row) != m:
            raise ValueError("g must not be ragged")
    _validate_square(qc, "qc")
    if m != len(qc):
        raise ValueError("g row length must match the Qc order")
    if not _is_psd_symmetric(qc):
        raise ValueError("Qc must be symmetric positive semi-definite")
    gqc = _matmul(g, qc)
    return _matmul(gqc, _transpose(g))


def van_loan_discretize(f, g, qc, dt):
    """Return (phi_d, qd) by the van Loan closed form.

    Form the 2n x 2n augmented matrix B = [[-F, W],[0, F^T]]*dt with
    W = G*Qc*G^T, take E = exp(B) = [[E11, E12],[0, E22]], then
    phi_d = E22^T and qd = phi_d*E12, which equals
    integral_0^dt exp(F*tau) W exp(F^T*tau) d tau exactly by
    construction of the matrix exponential. Raise ValueError if f is
    non-square, g row count differs from the f order, qc fails the
    continuous_noise_map checks, or dt <= 0."""
    n = _validate_square(f, "f")
    if dt <= 0:
        raise ValueError("dt must be positive")
    if not isinstance(g, list) or len(g) != n:
        raise ValueError("g row count must match the f order")
    w = continuous_noise_map(g, qc)
    ft = _transpose(f)
    size = 2 * n
    b = []
    for i in range(size):
        row = []
        for j in range(size):
            if i < n and j < n:
                row.append(-f[i][j] * dt)
            elif i < n:
                row.append(w[i][j - n] * dt)
            elif j < n:
                row.append(0.0)
            else:
                row.append(ft[i - n][j - n] * dt)
        b.append(row)
    e = mat_exp(b)
    e12 = [row[n:] for row in e[:n]]
    e22 = [row[n:] for row in e[n:]]
    phi_d = _transpose(e22)
    qd = _matmul(phi_d, e12)
    return phi_d, qd


def discrete_white_noise_acceleration(dt, q):
    """Return the 2 x 2 DWA closed form q*[[dt^3/3, dt^2/2],[dt^2/2, dt]].

    Discrete white noise acceleration model on the position/velocity
    state with F = [[0,1],[0,0]], G = [[0],[1]], Qc = [[q]]. Raise
    ValueError if dt <= 0 or q < 0."""
    if dt <= 0:
        raise ValueError("dt must be positive")
    if q < 0:
        raise ValueError("q must be non-negative")
    dt2 = dt * dt
    dt3 = dt2 * dt
    return [[q * dt3 / 3.0, q * dt2 / 2.0],
            [q * dt2 / 2.0, q * dt]]


def random_walk_covariance(dt, q):
    """Return the scalar random walk discrete covariance q*dt.

    F = 0 scalar case: white noise of PSD q grows the state variance by
    q*dt per step, the exact van Loan integral. Raise ValueError if
    dt <= 0 or q < 0."""
    if dt <= 0:
        raise ValueError("dt must be positive")
    if q < 0:
        raise ValueError("q must be non-negative")
    return q * dt


def ins_velocity_random_walk_covariance(dt, q_accel):
    """Return the per-axis velocity random walk variance q_accel*dt.

    INS velocity error state driven by accelerometer white noise of PSD
    q_accel: the F = 0 scalar special case, the value an error-state
    filter enters per velocity axis each propagation step. Same ValueError
    set as random_walk_covariance."""
    if dt <= 0:
        raise ValueError("dt must be positive")
    if q_accel < 0:
        raise ValueError("q_accel must be non-negative")
    return q_accel * dt


def _main():
    """Standalone smoke check mirroring the spec worked example."""
    phi_rw, qd_rw = van_loan_discretize([[0.0]], [[1.0]], [[0.01]], 0.1)
    phi_dwa, qd_dwa = van_loan_discretize(
        [[0.0, 1.0], [0.0, 0.0]], [[0.0], [1.0]], [[0.25]], 1.0)
    print("random walk: phi=%s qd=%s closed=%.17g" %
          (phi_rw, qd_rw, random_walk_covariance(0.1, 0.01)))
    print("DWA dt=1: phi=%s qd=%s" % (phi_dwa, qd_dwa))
    print("DWA closed form:", discrete_white_noise_acceleration(1.0, 0.25))
    print("INS per-axis:", ins_velocity_random_walk_covariance(0.01, 0.01))


if __name__ == "__main__":
    _main()

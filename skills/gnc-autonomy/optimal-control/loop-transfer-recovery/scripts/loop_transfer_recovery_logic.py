#!/usr/bin/env python3
"""Output-side loop-transfer recovery (LTR) for the canonical two-state plant.

Runs the Doyle-Stein 1981 recovery construction (textbook treatment
Maciejowski, Multivariable Feedback Design, 1989, chapter 5) on the LQG
loop of the canonical scalar-input two-state plant family shared by the
gnc-autonomy optimal-control pack: A = [[0, 1], [0, -a]] with damping
a >= 0, input B = [0, 1] (acceleration-like control on the rate state)
and measured output C = [1, 0] (y = x1, position-like). Unit convention:
x1 in m (or rad), x2 in m/s (or rad/s), u in m/s^2 (or rad/s^2), omega in
rad/s, q dimensionless.

The leaf takes the full-state regulator gain K from the family regulator
algebraic Riccati equation A'P + PA - P B R^-1 B' P + Q = 0 and forms the
full-state target loop L_t(s) = K (sI - A)^-1 B, the loop broken at the
plant output (identical to the input break for this SISO family). It then
searches over the recovery gain q: at every q it inflates the filter
process-noise covariance in the driven-input direction through
Qw(q) = Qw0 + q^2 B B^T, which changes only the (2,2) weight
w2(q) = w2 + q^2 because B B^T = [[0, 0], [0, 1]], re-solves the family
filter algebraic Riccati equation A S + S A' - S C' Rw^-1 C S + Qw = 0 for
the error covariance S(q) and the estimator gain L(q), and evaluates the
recovered output loop L_lqg(s; q) = G(s) K (sI - A + BK + L(q)C)^-1 L(q)
against L_t(s) on a log-spaced frequency grid. The grid-max complex
mismatch M(q) = max_k |L_lqg(j w_k; q) - L_t(j w_k)| / max_k |L_t(j w_k)|
falls monotonically to zero as q grows for the minimum-phase family, and
the recovery gain q* is the first sweep point with M(q*) <= tol.

Produces the full-state target loop samples with the grid-max target
magnitude, the nominal (q = 0) LQG loop mismatch, the recovery trace of
(q, M(q), magnitude-only mismatch Mmag(q), estimator gain L(q)), the
recovery gain q*, the recovered filter covariance S(q*) and estimator
gain L(q*), and the recovery verdict.

Pure stdlib (math only plus the builtin complex type), deterministic, no
RNG, no external processes. Reference note: ARP4754A (standards-map.yaml,
reference-only) frames development assurance for aircraft systems; the
Riccati and recovery mathematics is common control-theory knowledge,
summary only.
"""

import math

# ---------------------------------------------------------------------------
# Module constants (the worked scenario; pin exactly)
# ---------------------------------------------------------------------------
DAMP_A = 0.0          # plant damping a (a = -A[1][1])
Q1 = 1.0              # regulator state weight on x1
Q2 = 1.0              # regulator state weight on x2
R_W = 1.0             # regulator control weight
W1 = 1.0              # nominal filter process-noise weight on x1
W2 = 1.0              # nominal filter process-noise weight on x2
RV = 1.0              # measurement noise covariance
OMEGA_MIN = 0.1       # frequency grid lower bound, rad/s
OMEGA_MAX = 20.0      # frequency grid upper bound, rad/s
N_FREQ = 41           # log-spaced frequency grid points
RECOVERY_TOL = 1e-3   # grid-max mismatch gate
Q_MIN = 10.0          # geometric recovery sweep start
Q_MAX = 1e8           # geometric recovery sweep end
Q_STEP = 10.0         # geometric recovery sweep step
B = [0.0, 1.0]        # input vector of the canonical family

_BISECT_REL_TOL = 1e-15
_MAX_BISECT_ITERS = 200


# ---------------------------------------------------------------------------
# Validation helpers (shared ValueError contract)
# ---------------------------------------------------------------------------

def _require_finite(v, name):
    """Validate a numeric input v and return it as a finite float.

    Any non-numeric or non-finite input raises ValueError. Every public
    numeric parameter passes through here before use.
    """
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, v))
    if not math.isfinite(f):
        raise ValueError("%s must be finite, got %r" % (name, v))
    return f


def _require_length2(v, name):
    """Validate a length-2 numeric vector v and return its two floats."""
    if not (isinstance(v, (list, tuple)) and len(v) == 2):
        raise ValueError("%s must be a length-2 vector, got %r" % (name, v))
    try:
        return float(v[0]), float(v[1])
    except (TypeError, ValueError):
        raise ValueError("%s entries must be numeric, got %r" % (name, v))


def _inv22_adjugate(m):
    """Adjugate inverse of a 2x2 matrix of complex scalars.

    Returns inv = adj(m) / det(m) with adj = [[m11, -m01], [-m10, m00]]
    and det = m00 m11 - m01 m10, evaluated entrywise so the matrix path
    and the family rational closed forms stay comparable.
    """
    det = m[0][0] * m[1][1] - m[0][1] * m[1][0]
    return [[m[1][1] / det, -m[0][1] / det],
            [-m[1][0] / det, m[0][0] / det]]


# ---------------------------------------------------------------------------
# Frequency grid
# ---------------------------------------------------------------------------

def frequency_grid(omega_min=OMEGA_MIN, omega_max=OMEGA_MAX,
                   n_freq=N_FREQ):
    """Return the log-spaced frequency grid as a list of n_freq floats.

    Grid points w_k = omega_min * exp(ln(omega_max / omega_min) * k /
    (n_freq - 1)) for k = 0 .. n_freq - 1, the pinned band of the worked
    scenario [0.1, 20] rad/s with 41 points. ValueError if any endpoint
    is non-finite, omega_min <= 0, omega_max <= omega_min, or n_freq < 2.
    """
    lo = _require_finite(omega_min, "omega_min")
    hi = _require_finite(omega_max, "omega_max")
    if lo <= 0.0:
        raise ValueError("omega_min must be > 0, got %g" % (lo,))
    if hi <= lo:
        raise ValueError("omega_max must be > omega_min, got %g" % (hi,))
    nf = int(_require_finite(n_freq, "n_freq"))
    if nf < 2:
        raise ValueError("n_freq must be >= 2, got %g" % (n_freq,))
    span = math.log(hi / lo)
    grid = []
    for k in range(nf):
        grid.append(lo * math.exp(span * k / (nf - 1)))
    return grid


# ---------------------------------------------------------------------------
# Regulator side: family ARE closed form (the fixed full-state ingredient)
# ---------------------------------------------------------------------------

def regulator_riccati(a, q1, q2, r):
    """Solve the regulator ARE and return (P, K) for the canonical family.

    Exact scalar reduction of A'P + PA - P B R^-1 B' P + Q = 0 used by the
    lqr-design and lqg-design siblings (valid for any a >= 0):
    p2 = sqrt(r q1), p3 = r (-a + sqrt(a^2 + (2 p2 + q2) / r)),
    p1 = a p2 + p2 p3 / r. Returns P = [[p1, p2], [p2, p3]] and the
    full-state gain K = [k1, k2] = [p2 / r, p3 / r] for u = -K x.
    ValueError if a < 0, q1 < 0, q2 < 0, r <= 0, or any input non-finite.
    """
    a = _require_finite(a, "a")
    q1 = _require_finite(q1, "q1")
    q2 = _require_finite(q2, "q2")
    r = _require_finite(r, "r")
    if a < 0.0:
        raise ValueError("damping a must be >= 0, got %g" % (a,))
    if q1 < 0.0:
        raise ValueError("q1 must be >= 0, got %g" % (q1,))
    if q2 < 0.0:
        raise ValueError("q2 must be >= 0, got %g" % (q2,))
    if r <= 0.0:
        raise ValueError("r must be > 0, got %g" % (r,))
    p2 = math.sqrt(r * q1)
    p3 = r * (-a + math.sqrt(a * a + (2.0 * p2 + q2) / r))
    p1 = a * p2 + p2 * p3 / r
    return [[p1, p2], [p2, p3]], [p2 / r, p3 / r]


# ---------------------------------------------------------------------------
# Filter side: dual (Kalman) ARE closed form, the estimator ingredient
# ---------------------------------------------------------------------------

def _filter_s2_residual(u, a, rv, w1, w2):
    """Left side of the monotone scalar filter equation at u >= 0.

    f(u) = u^2 + 2 a^2 rv u + 2 a u sqrt(rv (2 u + w1)) - rv w2, the (2,2)
    entry of the filter ARE written out for the canonical family. Strictly
    increasing in u for u >= 0 when a >= 0, and f(0) = -rv w2 < 0.
    """
    return (u * u + 2.0 * a * a * rv * u
            + 2.0 * a * u * math.sqrt(rv * (2.0 * u + w1)) - rv * w2)


def s2_root(a, w1, w2, rv):
    """Return the filter ARE entry s2 for the canonical family.

    The (2,2) entry of S solves the monotone scalar equation: exactly
    sqrt(rv w2) at a = 0, otherwise the unique root on (0, sqrt(rv w2)]
    found by bisection to 1e-15 relative (the lqg-design family
    machinery). Same ValueErrors as filter_riccati.
    """
    a = _require_finite(a, "a")
    w1 = _require_finite(w1, "w1")
    w2 = _require_finite(w2, "w2")
    rv = _require_finite(rv, "rv")
    if a < 0.0:
        raise ValueError("damping a must be >= 0, got %g" % (a,))
    if w1 < 0.0:
        raise ValueError("w1 must be >= 0, got %g" % (w1,))
    if w2 <= 0.0:
        raise ValueError("w2 must be > 0 (noise on the driven state), got %g"
                         % (w2,))
    if rv <= 0.0:
        raise ValueError("rv must be > 0, got %g" % (rv,))
    if a == 0.0:
        return math.sqrt(rv * w2)
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


def filter_riccati(a, w1, w2, rv):
    """Solve the filter (Kalman) ARE and return (S, L) for the family.

    Dual scalar reduction of A S + S A' - S C' Rw^-1 C S + Qw = 0 with
    C = [1, 0]: s2 from s2_root, s1 = sqrt(rv (2 s2 + w1)),
    s3 = a s2 + s1 s2 / rv. Returns S = [[s1, s2], [s2, s3]] and the
    estimator gain L = [l1, l2] = [s1 / rv, s2 / rv] of
    xhat' = A xhat + B u + L (y - C xhat). ValueError if a < 0, w1 < 0,
    w2 <= 0, rv <= 0, or any input non-finite.
    """
    a = _require_finite(a, "a")
    w1 = _require_finite(w1, "w1")
    w2 = _require_finite(w2, "w2")
    rv = _require_finite(rv, "rv")
    if a < 0.0:
        raise ValueError("damping a must be >= 0, got %g" % (a,))
    if w1 < 0.0:
        raise ValueError("w1 must be >= 0, got %g" % (w1,))
    if w2 <= 0.0:
        raise ValueError("w2 must be > 0 (noise on the driven state), got %g"
                         % (w2,))
    if rv <= 0.0:
        raise ValueError("rv must be > 0, got %g" % (rv,))
    s2 = s2_root(a, w1, w2, rv)
    s1 = math.sqrt(rv * (2.0 * s2 + w1))
    s3 = a * s2 + s1 * s2 / rv
    return [[s1, s2], [s2, s3]], [s1 / rv, s2 / rv]


# ---------------------------------------------------------------------------
# Recovery inflation and loop transfer evaluations
# ---------------------------------------------------------------------------

def inflated_noise_covariance(q):
    """Return the driven-state process-noise weight at recovery gain q.

    Qw(q) = Qw0 + q^2 B B^T touches only the (2,2) entry because
    B B^T = [[0, 0], [0, 1]], so the inflated weight is the module's
    nominal W2 plus q^2; the fictitious noise on the driven state grows
    with the SQUARE of q. ValueError if q non-finite or q < 0.
    """
    q = _require_finite(q, "q")
    if q < 0.0:
        raise ValueError("recovery gain q must be >= 0, got %g" % (q,))
    return W2 + q * q


def target_loop(s, a, K):
    """Return the full-state target loop L_t(s) = K (sI - A)^-1 B.

    Evaluated through the 2x2 adjugate inverse of [[s, -1], [0, s + a]],
    the loop broken at the plant output (SISO-identical to the input
    break for this family; the family closed form is
    (k1 + k2 s) / (s (s + a))). No validation: pure evaluation.
    """
    k1, k2 = _require_length2(K, "K")
    m = [[s, -1.0], [0.0, s + a]]
    inv = _inv22_adjugate(m)
    v0 = inv[0][0] * B[0] + inv[0][1] * B[1]
    v1 = inv[1][0] * B[0] + inv[1][1] * B[1]
    return k1 * v0 + k2 * v1


def _matrix_loop_scalar(s, a, K, L):
    """Return u = K (sI - A + BK + LC)^-1 L through the 2x2 matrix path.

    phi_o is the adjugate inverse of [[s + l1, -1], [k1 + l2, s + a + k2]]
    and u = k1 (phi_o[0][0] l1 + phi_o[0][1] l2) + k2 (phi_o[1][0] l1 +
    phi_o[1][1] l2). The family rational closed form is num / den with
    num = (k1 l1 + k2 l2) s + k1 (a l1 + l2) and
    den = s^2 + (l1 + a + k2) s + (a + k2) l1 + k1 + l2.
    """
    k1, k2 = _require_length2(K, "K")
    l1, l2 = _require_length2(L, "L")
    m = [[s + l1, -1.0], [k1 + l2, s + a + k2]]
    phi = _inv22_adjugate(m)
    return (k1 * (phi[0][0] * l1 + phi[0][1] * l2)
            + k2 * (phi[1][0] * l1 + phi[1][1] * l2))


def recovered_loop(s, a, K, L):
    """Return the recovered output loop L_lqg(s; q) = G(s) u with u above.

    G(s) = 1 / (s (s + a)) is the plant transfer C (sI - A)^-1 B. The
    SISO loop equals G(s) times u in either multiplication order: complex
    scalars commute, so the left-multiplied and right-multiplied forms
    agree bitwise. No validation: pure evaluation.
    """
    g = 1.0 / (s * (s + a))
    return g * _matrix_loop_scalar(s, a, K, L)


# ---------------------------------------------------------------------------
# Mismatch metrics and the recovery sweep
# ---------------------------------------------------------------------------

def _mismatch_metrics(a, K, grid, L):
    """Mismatch of the LQG loop with filter gain L against the target.

    Returns (M, Mmag, max_t) with M = max_k |L_lqg - L_t| / max_t,
    Mmag = max_k ||L_lqg| - |L_t|| / max_t and max_t the grid-max target
    magnitude, accumulated in explicit grid order (no reassociation).
    """
    max_t = 0.0
    for w in grid:
        mag = abs(target_loop(complex(0.0, w), a, K))
        if mag > max_t:
            max_t = mag
    m = 0.0
    mmag = 0.0
    for w in grid:
        sw = complex(0.0, w)
        rec = recovered_loop(sw, a, K, L)
        tgt = target_loop(sw, a, K)
        d = abs(rec - tgt)
        if d > m:
            m = d
        dm = abs(abs(rec) - abs(tgt))
        if dm > mmag:
            mmag = dm
    return m / max_t, mmag / max_t, max_t


def _filter_at_recovery(a, w1, w2, rv, q):
    """Filter ARE solution (S, L) at the inflated weight w2(q) = w2 + q^2."""
    return filter_riccati(a, w1, w2 + q * q, rv)


def _mismatch_at(a, K, grid, w1, w2, rv, q):
    """Full mismatch evaluation at recovery gain q (q >= 0 by contract).

    Returns (M, Mmag, L, S, max_t) for the filter solved at the inflated
    driven-state weight w2(q) = w2 + q^2.
    """
    S, L = _filter_at_recovery(a, w1, w2, rv, q)
    M, Mmag, max_t = _mismatch_metrics(a, K, grid, L)
    return M, Mmag, L, S, max_t


def loop_mismatch(q, a, K, grid):
    """Mismatch metrics of the nominal-recovery LQG loop at gain q.

    Solves the filter ARE at w2(q) = inflated_noise_covariance(q) with
    the module's W1 and RV and returns (M, Mmag, L, S, max_t): the two
    grid-max metrics, the estimator gain, the error covariance and the
    grid-max target magnitude. ValueError if q invalid (delegated to
    inflated_noise_covariance and filter_riccati).
    """
    w2q = inflated_noise_covariance(q)
    S, L = filter_riccati(a, W1, w2q, RV)
    M, Mmag, max_t = _mismatch_metrics(a, K, grid, L)
    return M, Mmag, L, S, max_t


def _sweep(a, K, grid, w1, w2, rv, tol, q_min, q_max, step):
    """Run the geometric recovery sweep and return (trace, q_star).

    trace holds (q, M(q), Mmag(q), l1, l2) per sweep point in sweep
    order and q_star is the first q with M(q) <= tol, else None.
    """
    trace = []
    q_star = None
    q = q_min
    while q <= q_max:
        M, Mmag, L, _S, _mt = _mismatch_at(a, K, grid, w1, w2, rv, q)
        trace.append((q, M, Mmag, L[0], L[1]))
        if q_star is None and M <= tol:
            q_star = q
        q *= step
    return trace, q_star


def recovery_sweep(a, K, grid, tol=RECOVERY_TOL, q_min=Q_MIN,
                   q_max=Q_MAX, step=Q_STEP):
    """Recovery trace over the geometric sweep with the module weights.

    At every q of q_min, q_min * step, ... (inclusive up to q_max) the
    driven-state noise weight is inflated to W2 + q^2, the filter ARE is
    re-solved and the recovered output loop is compared with the target.
    Returns (trace, q_star): trace is the list of (q, M(q), Mmag(q), l1,
    l2) in sweep order and q_star the first trace q with M(q) <= tol or
    None. ValueError if q_min <= 0, q_max < q_min, step <= 1, tol <= 0,
    or any of the sweep bounds non-finite.
    """
    tol = _require_finite(tol, "tol")
    q_min = _require_finite(q_min, "q_min")
    q_max = _require_finite(q_max, "q_max")
    step = _require_finite(step, "step")
    if not grid:
        raise ValueError("grid must be non-empty")
    if q_min <= 0.0:
        raise ValueError("q_min must be > 0, got %g" % (q_min,))
    if q_max < q_min:
        raise ValueError("q_max must be >= q_min, got %g" % (q_max,))
    if step <= 1.0:
        raise ValueError("step must be > 1, got %g" % (step,))
    if tol <= 0.0:
        raise ValueError("tol must be > 0, got %g" % (tol,))
    return _sweep(a, K, grid, W1, W2, RV, tol, q_min, q_max, step)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def recovery_result(a=DAMP_A, q1=Q1, q2=Q2, r=R_W, w1=W1, w2=W2, rv=RV,
                    tol=RECOVERY_TOL, q_min=Q_MIN, q_max=Q_MAX):
    """Run the full LTR analysis and return the result dict.

    Keys: a, q1, q2, r, w1, w2, rv, grid, P, K (full-state regulator
    solution and gain), S0, L0 (nominal filter solution at q = 0),
    max_target (grid-max |L_t|), target_samples (list of (w_k,
    L_t(j w_k))), mismatch_nominal (M at q = 0), trace (the recovery
    sweep trace), q_star (first sweep q with M(q) <= tol or None),
    verdict (bool: q_star is not None), S_star and L_star (filter
    solution at q*, None when q_star is None), m_star, mmag_star and
    improvement_ratio (mismatch_nominal / m_star). ValueError for any
    invalid weight or sweep parameter as listed per function; the driver
    validates q_min <= q_max before sweeping.
    """
    grid = frequency_grid()
    P, K = regulator_riccati(a, q1, q2, r)
    S0, L0 = filter_riccati(a, w1, w2, rv)
    tol = _require_finite(tol, "tol")
    q_min = _require_finite(q_min, "q_min")
    q_max = _require_finite(q_max, "q_max")
    if tol <= 0.0:
        raise ValueError("tol must be > 0, got %g" % (tol,))
    if q_min <= 0.0:
        raise ValueError("q_min must be > 0, got %g" % (q_min,))
    if q_max < q_min:
        raise ValueError("q_max must be >= q_min, got %g" % (q_max,))
    max_target = 0.0
    target_samples = []
    for w in grid:
        t = target_loop(complex(0.0, w), a, K)
        target_samples.append((w, t))
        mag = abs(t)
        if mag > max_target:
            max_target = mag
    m_nom, mmag_nom, _L, _S, _mt = _mismatch_at(a, K, grid, w1, w2, rv, 0.0)
    trace, q_star = _sweep(a, K, grid, w1, w2, rv, tol, q_min, q_max,
                           Q_STEP)
    if q_star is None:
        return {
            "a": a, "q1": q1, "q2": q2, "r": r, "w1": w1, "w2": w2,
            "rv": rv, "grid": grid, "P": P, "K": K, "S0": S0, "L0": L0,
            "max_target": max_target, "target_samples": target_samples,
            "mismatch_nominal": m_nom, "trace": trace, "q_star": None,
            "verdict": False, "S_star": None, "L_star": None,
            "m_star": None, "mmag_star": None, "improvement_ratio": None,
        }
    S_star, L_star = _filter_at_recovery(a, w1, w2, rv, q_star)
    m_star = None
    mmag_star = None
    for entry in trace:
        if entry[0] == q_star:
            m_star = entry[1]
            mmag_star = entry[2]
            break
    return {
        "a": a, "q1": q1, "q2": q2, "r": r, "w1": w1, "w2": w2,
        "rv": rv, "grid": grid, "P": P, "K": K, "S0": S0, "L0": L0,
        "max_target": max_target, "target_samples": target_samples,
        "mismatch_nominal": m_nom, "trace": trace, "q_star": q_star,
        "verdict": True, "S_star": S_star, "L_star": L_star,
        "m_star": m_star, "mmag_star": mmag_star,
        "improvement_ratio": m_nom / m_star,
    }

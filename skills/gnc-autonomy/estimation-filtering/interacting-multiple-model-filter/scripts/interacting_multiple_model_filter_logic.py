"""Interacting multiple model (IMM) filter logic for maneuvering-target tracking.

Two-mode IMM bank over a CV (constant velocity) mode and a CA (constant
acceleration) mode with the standard per-axis planar simplification: each
planar axis (x and y) is filtered independently by its own 2-state (CV) or
3-state (CA) Kalman filter, and both axes share the same Markov
mode-probability vector (equal-axis planar tracker).  All matrix arithmetic
is hand coded on plain Python lists, stdlib only, no numpy.  The filter is
deterministic (no RNG); the scripted maneuvering truth track is generated
analytically.

The IMM cycle per step (Bar-Shalom style): mix the previous mode-conditioned
estimates with the Markov transition probabilities into per-mode priors,
predict each mode filter, update each mode filter with the measurement,
combine the per-axis innovation likelihoods into a joint per-mode likelihood
(independent axes multiply), update the mode probabilities, and form the
combined estimate as the mu-weighted sum of the mode-conditioned estimates.
"""

import math

# ---------------------------------------------------------------------------
# Model constants (module level)
# ---------------------------------------------------------------------------
DT = 1.0  # sample interval, seconds

# CV mode: 2-state transition, state [position, velocity]
F_CV = [[1.0, DT], [0.0, 1.0]]

# CA mode: 3-state transition, state [position, velocity, acceleration]
F_CA = [[1.0, DT, 0.5 * DT ** 2],
        [0.0, 1.0, DT],
        [0.0, 0.0, 1.0]]

Q_CV_SCALAR = 1.0  # m2/s3
Q_CA_SCALAR = 2.0  # m2/s3

Q_CV = [[Q_CV_SCALAR * DT ** 3 / 3.0, Q_CV_SCALAR * DT ** 2 / 2.0],
        [Q_CV_SCALAR * DT ** 2 / 2.0, Q_CV_SCALAR * DT]]

Q_CA = [[Q_CA_SCALAR * DT ** 5 / 20.0, Q_CA_SCALAR * DT ** 4 / 8.0, Q_CA_SCALAR * DT ** 3 / 6.0],
        [Q_CA_SCALAR * DT ** 4 / 8.0, Q_CA_SCALAR * DT ** 3 / 3.0, Q_CA_SCALAR * DT ** 2 / 2.0],
        [Q_CA_SCALAR * DT ** 3 / 6.0, Q_CA_SCALAR * DT ** 2 / 2.0, Q_CA_SCALAR * DT]]

# Position-only measurement models and measurement noise variance
H_CV = [1.0, 0.0]
H_CA = [1.0, 0.0, 0.0]
R = 25.0  # m2, sigma 5 m

# Markov mode-transition matrix Pi[i][j] = P(mode i at k-1 -> mode j at k)
PI = [[0.95, 0.05],
      [0.05, 0.95]]

# Initial conditions used by run_imm_track (anchored on the first position)
MU0 = [0.95, 0.05]  # initial mode probabilities [CV, CA]
INIT_VEL_VAR = 4000.0  # (m/s)^2, generous anchor when velocity is unobserved
INIT_ACC_VAR = 1.0  # (m/s^2)^2
P0_CV = [[R, 0.0], [0.0, INIT_VEL_VAR]]
P0_CA = [[R, 0.0, 0.0],
         [0.0, INIT_VEL_VAR, 0.0],
         [0.0, 0.0, INIT_ACC_VAR]]


# ---------------------------------------------------------------------------
# Small dense-matrix helpers (rows are lists, dims <= 3)
# ---------------------------------------------------------------------------
def _check_square(mat, n, what):
    """Raise ValueError unless mat is an n x n list of lists."""
    if not isinstance(mat, (list, tuple)) or len(mat) != n:
        raise ValueError("%s must be a %dx%d matrix" % (what, n, n))
    for row in mat:
        if not isinstance(row, (list, tuple)) or len(row) != n:
            raise ValueError("%s must be a %dx%d matrix" % (what, n, n))


def _check_vec(vec, n, what):
    """Raise ValueError unless vec is a length-n vector."""
    if not isinstance(vec, (list, tuple)) or len(vec) != n:
        raise ValueError("%s must be a length-%d vector" % (what, n))


def _identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _zeros(n, m):
    return [[0.0] * m for _ in range(n)]


def _mat_mul(a, b):
    """Matrix product a @ b with dimension checking."""
    _check_square(a, len(b), "a") if False else None  # placeholder guard
    if not a or len(a[0]) != len(b):
        raise ValueError("matrix dimensions do not conform for product")
    return [[sum(a[i][k] * b[k][j] for k in range(len(b)))
             for j in range(len(b[0]))] for i in range(len(a))]


def _mat_vec(a, v):
    """Matrix-vector product a @ v."""
    if not a or len(a[0]) != len(v):
        raise ValueError("matrix and vector dimensions do not conform")
    return [sum(a[i][k] * v[k] for k in range(len(v))) for i in range(len(a))]


def _mat_transpose(a):
    return [list(col) for col in zip(*a)]


def _mat_add(a, b):
    if len(a) != len(b) or (a and len(a[0]) != len(b[0])):
        raise ValueError("matrix dimensions do not conform for addition")
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def _outer(d):
    """Outer product d d^T of a vector with itself."""
    return [[d[i] * d[j] for j in range(len(d))] for i in range(len(d))]


def _mat_scale(a, s):
    return [[a[i][j] * s for j in range(len(a[0]))] for i in range(len(a))]


# ---------------------------------------------------------------------------
# Mixing (mode interaction)
# ---------------------------------------------------------------------------
def _interact_into(mu, pi, x_prev, p_prev, target_mode):
    """Mixed prior for one target mode from the two mode-conditioned priors.

    x_prev and p_prev hold the previous mode-conditioned estimates (index 0
    = CV, index 1 = CA) already expressed in the target mode's state
    dimension.  Mixing weights mu_{i|j} = pi[i][j] * mu[i] / c_j with
    c_j = sum_i pi[i][j] * mu[i]; the mixed covariance adds the spread term
    (x_i - x0)(x_i - x0)^T (standard interaction).
    """
    c_j = mu[0] * pi[0][target_mode] + mu[1] * pi[1][target_mode]
    if c_j <= 0.0:
        raise ValueError("transition mixing probability c_j is not positive")
    n = len(x_prev[0])
    w = [pi[i][target_mode] * mu[i] / c_j for i in range(2)]
    x0 = [w[0] * x_prev[0][k] + w[1] * x_prev[1][k] for k in range(n)]
    p0 = _zeros(n, n)
    for i in range(2):
        d = [x_prev[i][k] - x0[k] for k in range(n)]
        sp = _outer(d)
        for a in range(n):
            for b in range(n):
                p0[a][b] += w[i] * (p_prev[i][a][b] + sp[a][b])
    return x0, p0


def _proj_ca_state(x):
    """Project a 3-state CA estimate to the 2-state CV space."""
    return [x[0], x[1]]


def _proj_ca_cov(p):
    """Take the 2x2 position-velocity block of a 3x3 CA covariance."""
    return [[p[0][0], p[0][1]], [p[1][0], p[1][1]]]


def _pad_cv_state(x):
    """Augment a 2-state CV estimate to 3 states with zero acceleration."""
    return [x[0], x[1], 0.0]


def _pad_cv_cov(p):
    """Augment a 2x2 CV covariance to 3x3 with zero acceleration rows."""
    return [[p[0][0], p[0][1], 0.0],
            [p[1][0], p[1][1], 0.0],
            [0.0, 0.0, 0.0]]


def mix_initial(mu, x_ests, p_ests, pi):
    """Interacting mixture of two same-dimension mode-conditioned priors.

    Computes the predicted mode probabilities c_j = sum_i pi[i][j] * mu[i]
    and the mode-conditioned mixing weights mu_{i|j} = pi[i][j] * mu[i] /
    c_j, forms the per-target-mode mixed prior (state = sum_i mu_{i|j} x_i,
    covariance via the standard interaction spread term), and returns the
    predicted-probability blend of the two per-mode mixed priors.  For a
    row-stochastic pi the blend reduces to the plain mu-weighted mixture,
    which is the standard common initial prior used to start the bank.

    Returns (mixed_x, mixed_p).  Pure stdlib, deterministic.
    """
    _check_vec(mu, 2, "mu")
    _check_square(pi, 2, "pi")
    if len(x_ests) != 2 or len(p_ests) != 2:
        raise ValueError("x_ests and p_ests must hold one prior per mode")
    if abs(sum(mu) - 1.0) > 1e-6 or min(mu) < -1e-9 or max(mu) > 1.0 + 1e-9:
        raise ValueError("mode probabilities mu must be in [0, 1] and sum to 1")
    n = len(x_ests[0])
    for i in range(2):
        _check_vec(x_ests[i], n, "x_ests[%d]" % i)
        _check_square(p_ests[i], n, "p_ests[%d]" % i)
    c = [mu[0] * pi[0][j] + mu[1] * pi[1][j] for j in range(2)]
    if min(c) <= 0.0:
        raise ValueError("predicted mode probabilities c_j must be positive")
    blended_x = [0.0] * n
    blended_p = _zeros(n, n)
    for j in range(2):
        x0 = [0.0] * n
        for i in range(2):
            w = pi[i][j] * mu[i] / c[j]
            for k in range(n):
                x0[k] += w * x_ests[i][k]
        p0 = _zeros(n, n)
        for i in range(2):
            w = pi[i][j] * mu[i] / c[j]
            d = [x_ests[i][k] - x0[k] for k in range(n)]
            sp = _outer(d)
            for a in range(n):
                for b in range(n):
                    p0[a][b] += w * (p_ests[i][a][b] + sp[a][b])
        for k in range(n):
            blended_x[k] += c[j] * x0[k]
        for a in range(n):
            for b in range(n):
                blended_p[a][b] += c[j] * p0[a][b]
    return blended_x, blended_p


# ---------------------------------------------------------------------------
# Kalman primitives (mode-conditioned, per axis)
# ---------------------------------------------------------------------------
def kalman_predict(x, p, f, q):
    """Kalman prediction step: x_pred = F x, P_pred = F P F^T + Q."""
    _check_vec(x, len(x), "x")
    n = len(x)
    _check_square(p, n, "p")
    _check_square(f, n, "f")
    _check_square(q, n, "q")
    x_pred = _mat_vec(f, x)
    p_pred = _mat_add(_mat_mul(_mat_mul(f, p), _mat_transpose(f)), q)
    return x_pred, p_pred


def kalman_update(x, p, z, h, r):
    """Kalman update step with a scalar position measurement.

    Returns (x_upd, p_upd, innovation, innovation_cov_s, likelihood) with
    likelihood = exp(-0.5 * innovation^2 / s) / sqrt(2 * pi * s).
    """
    _check_vec(x, len(x), "x")
    n = len(x)
    _check_square(p, n, "p")
    _check_vec(h, n, "h")
    if not isinstance(r, (int, float)) or r <= 0.0:
        raise ValueError("measurement noise r must be positive")
    innovation = z - sum(h[k] * x[k] for k in range(n))
    hp = _mat_vec(p, h)  # P h^T
    s = sum(h[k] * hp[k] for k in range(n)) + r
    if s <= 0.0:
        raise ValueError("innovation covariance s must be positive")
    gain = [hp[k] / s for k in range(n)]
    x_upd = [x[k] + gain[k] * innovation for k in range(n)]
    h_p = [sum(h[k] * p[k][j] for k in range(n)) for j in range(n)]  # h P
    p_upd = [[p[i][j] - gain[i] * h_p[j] for j in range(n)] for i in range(n)]
    likelihood = (math.exp(-0.5 * innovation * innovation / s)
                  / math.sqrt(2.0 * math.pi * s))
    return x_upd, p_upd, innovation, s, likelihood


def mode_update(mu, c, likelihoods):
    """Bayesian mode-probability update.

    mu_new_j = likelihood_j * c_j / sum_k (likelihood_k * c_k), where c is
    the predicted mode-probability vector from the transition mixing and mu
    is the previous mode-probability vector (validated, not used in the
    formula).
    """
    _check_vec(mu, 2, "mu")
    _check_vec(c, 2, "c")
    _check_vec(likelihoods, 2, "likelihoods")
    if abs(sum(mu) - 1.0) > 1e-6 or min(mu) < -1e-9 or max(mu) > 1.0 + 1e-9:
        raise ValueError("mode probabilities mu must be in [0, 1] and sum to 1")
    if min(c) <= 0.0:
        raise ValueError("predicted mode probabilities c must be positive")
    if min(likelihoods) < 0.0:
        raise ValueError("likelihoods must be non-negative")
    total = likelihoods[0] * c[0] + likelihoods[1] * c[1]
    if total <= 0.0:
        raise ValueError("weighted likelihood total is not positive")
    return [likelihoods[j] * c[j] / total for j in range(2)]


# ---------------------------------------------------------------------------
# IMM cycle
# ---------------------------------------------------------------------------
def imm_step(mu, x_cv, p_cv, x_ca, p_ca, z, pi, f_cv, q_cv, f_ca, q_ca, r):
    """One full IMM cycle over both planar axes with a shared mode vector.

    State layout (per axis a, x axis first): x_cv[a] is the 2-state CV
    estimate [position, velocity], x_ca[a] the 3-state CA estimate
    [position, velocity, acceleration], p_cv[a] / p_ca[a] the matching
    covariances, and z = [zx, zy] the 2D position measurement.  mu =
    [mu_cv, mu_ca] is shared by both axes.

    The cycle per axis is: interact (mix the mode-conditioned priors into
    per-mode priors with the Markov weights), predict, update, then the
    per-mode likelihoods from the two axes multiply into a joint likelihood
    (independent axes), mode_update refreshes mu, and the combined estimate
    is x_combined = sum_j mu_j * x_j (CV padded with zero acceleration).

    Returns dict {mu_new, x_cv, p_cv, x_ca, p_ca, x_combined, p_combined}.
    """
    _check_vec(mu, 2, "mu")
    _check_square(pi, 2, "pi")
    if abs(sum(mu) - 1.0) > 1e-6 or min(mu) < -1e-9 or max(mu) > 1.0 + 1e-9:
        raise ValueError("mode probabilities mu must be in [0, 1] and sum to 1")
    for row in pi:
        if abs(sum(row) - 1.0) > 1e-6 or min(row) < -1e-9:
            raise ValueError("pi rows must be stochastic")
    _check_vec(z, 2, "z")
    if len(x_cv) != 2 or len(p_cv) != 2 or len(x_ca) != 2 or len(p_ca) != 2:
        raise ValueError("per-axis filter state lists must hold both axes")
    for a in range(2):
        _check_vec(x_cv[a], 2, "x_cv[%d]" % a)
        _check_square(p_cv[a], 2, "p_cv[%d]" % a)
        _check_vec(x_ca[a], 3, "x_ca[%d]" % a)
        _check_square(p_ca[a], 3, "p_ca[%d]" % a)
    _check_square(f_cv, 2, "f_cv")
    _check_square(q_cv, 2, "q_cv")
    _check_square(f_ca, 3, "f_ca")
    _check_square(q_ca, 3, "q_ca")
    if not isinstance(r, (int, float)) or r <= 0.0:
        raise ValueError("measurement noise r must be positive")

    c = [mu[0] * pi[0][j] + mu[1] * pi[1][j] for j in range(2)]
    axis_lik = [[0.0, 0.0], [0.0, 0.0]]  # axis_lik[axis][mode]
    new_x_cv = []
    new_p_cv = []
    new_x_ca = []
    new_p_ca = []
    for a in range(2):
        # Interact: mixed prior for the CV mode (CA projected to 2 states)
        x0_cv, p0_cv = _interact_into(mu, pi,
                                      [x_cv[a], _proj_ca_state(x_ca[a])],
                                      [p_cv[a], _proj_ca_cov(p_ca[a])], 0)
        # Interact: mixed prior for the CA mode (CV padded to 3 states)
        x0_ca, p0_ca = _interact_into(mu, pi,
                                      [_pad_cv_state(x_cv[a]), x_ca[a]],
                                      [_pad_cv_cov(p_cv[a]), p_ca[a]], 1)
        xp_cv, pp_cv = kalman_predict(x0_cv, p0_cv, f_cv, q_cv)
        xp_ca, pp_ca = kalman_predict(x0_ca, p0_ca, f_ca, q_ca)
        xu_cv, pu_cv, _, _, lik_cv = kalman_update(xp_cv, pp_cv, z[a], H_CV, r)
        xu_ca, pu_ca, _, _, lik_ca = kalman_update(xp_ca, pp_ca, z[a], H_CA, r)
        axis_lik[a] = [lik_cv, lik_ca]
        new_x_cv.append(xu_cv)
        new_p_cv.append(pu_cv)
        new_x_ca.append(xu_ca)
        new_p_ca.append(pu_ca)

    # Joint per-mode likelihood over the two independent axes (product)
    joint = [axis_lik[0][j] * axis_lik[1][j] for j in range(2)]
    mu_new = mode_update(mu, c, joint)

    # Combined estimate per axis: mu-weighted sum, CV padded with zero accel
    x_combined = []
    p_combined = []
    for a in range(2):
        cv3 = _pad_cv_state(new_x_cv[a])
        xc = [mu_new[0] * cv3[k] + mu_new[1] * new_x_ca[a][k] for k in range(3)]
        p_cv3 = _pad_cv_cov(new_p_cv[a])
        pc = _zeros(3, 3)
        for i, (xx, pp, w) in enumerate(
                ((cv3, p_cv3, mu_new[0]), (new_x_ca[a], new_p_ca[a], mu_new[1]))):
            d = [xx[k] - xc[k] for k in range(3)]
            sp = _outer(d)
            for b in range(3):
                for c2 in range(3):
                    pc[b][c2] += w * (pp[b][c2] + sp[b][c2])
        x_combined.append(xc)
        p_combined.append(pc)
    return {"mu_new": mu_new, "x_cv": new_x_cv, "p_cv": new_p_cv,
            "x_ca": new_x_ca, "p_ca": new_p_ca,
            "x_combined": x_combined, "p_combined": p_combined}


# ---------------------------------------------------------------------------
# Scripted truth track and full-track runner
# ---------------------------------------------------------------------------
def make_maneuvering_track():
    """Deterministic 100 s maneuvering track at DT = 1 s (no RNG).

    Position samples t = 0..99 s: px(t) = 100 * t; py(t) = 0 for t <= 50,
    py(t) = 0.5 * 20 * (t - 50)^2 for 50 < t <= 75 (lateral acceleration
    ay = 20 m/s2 applied from t = 50 s for 25 s), py(t) = 0.5 * 20 * 25^2 +
    500 * (t - 75) for t > 75 (velocity 500 m/s after t = 75 s).
    """
    track = []
    for t in range(100):
        px = 100.0 * t
        if t <= 50:
            py = 0.0
        elif t <= 75:
            py = 0.5 * 20.0 * (t - 50.0) ** 2
        else:
            py = 0.5 * 20.0 * 25.0 ** 2 + 500.0 * (t - 75.0)
        track.append([px, py])
    return track


def run_imm_track(truth_positions):
    """Run the two-mode IMM over a scripted planar position track.

    Both axes start anchored on the first measurement with zero velocity
    and acceleration, initial covariance P0_CV / P0_CA and mode
    probabilities MU0 = [0.95, 0.05].  One imm_step per measurement after
    the first.  Returns dict {mu_hist, combined_pos_hist, cv_pos_hist,
    ca_pos_hist} where mu_hist[t] = [mu_cv, mu_ca] at time index t
    (mode_probability_ca = mu_hist[t][1]) and the position histories hold
    [x, y] at each time index.  Deterministic, stdlib only.
    """
    if not truth_positions or len(truth_positions) < 1:
        raise ValueError("truth_positions must hold at least one sample")
    n = len(truth_positions)
    for pt in truth_positions:
        _check_vec(pt, 2, "track sample")
    z0 = [float(truth_positions[0][0]), float(truth_positions[0][1])]

    x_cv = [[z0[0], 0.0], [z0[1], 0.0]]
    p_cv = [[[R, 0.0], [0.0, INIT_VEL_VAR]],
            [[R, 0.0], [0.0, INIT_VEL_VAR]]]
    x_ca = [[z0[0], 0.0, 0.0], [z0[1], 0.0, 0.0]]
    p_ca = [P0_CA, P0_CA]
    mu = list(MU0)

    mu_hist = [list(mu)]
    combined_pos_hist = [list(z0)]
    cv_pos_hist = [list(z0)]
    ca_pos_hist = [list(z0)]

    for k in range(1, n):
        z = [float(truth_positions[k][0]), float(truth_positions[k][1])]
        res = imm_step(mu, x_cv, p_cv, x_ca, p_ca, z, PI, F_CV, Q_CV, F_CA,
                       Q_CA, R)
        mu = res["mu_new"]
        x_cv = res["x_cv"]
        p_cv = res["p_cv"]
        x_ca = res["x_ca"]
        p_ca = res["p_ca"]
        mu_hist.append(list(mu))
        combined_pos_hist.append([res["x_combined"][0][0],
                                  res["x_combined"][1][0]])
        cv_pos_hist.append([x_cv[0][0], x_cv[1][0]])
        ca_pos_hist.append([x_ca[0][0], x_ca[1][0]])

    return {"mu_hist": mu_hist, "combined_pos_hist": combined_pos_hist,
            "cv_pos_hist": cv_pos_hist, "ca_pos_hist": ca_pos_hist}

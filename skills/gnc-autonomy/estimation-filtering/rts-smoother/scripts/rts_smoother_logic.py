"""Fixed-interval Rauch-Tung-Striebel (RTS) smoother over a stored forward
Kalman-filter history for a discrete constant-velocity model.

State x = [position, velocity].  Constant-velocity transition with time
step dt (s): F = [[1, dt], [0, 1]], measurement model H = [[1, 0]].
Continuous acceleration noise intensity q (m2/s3) is discretized as
Q = q * [[dt^4/4, dt^3/2], [dt^3/2, dt^2]]; the measurement noise
variance is r (m2).

forward_kalman runs the linear predict-update recursion over a stored
measurement list and returns one record per step holding the predicted
and filtered means and covariances plus the innovation and its
variance.  rts_smooth then runs the backward recursion with the
smoother gain to produce the fixed-interval smoothed mean and
covariance history, which uses all measurements, past and future.
smoother_reduction compares the smoothed position variance against the
filtered position variance at every step.

Pure Python stdlib, deterministic, no external dependencies.  Raises
ValueError on non-physical inputs and singular matrix inversions.
"""

import copy

# Comparison tolerance used by the covariance verdict helpers.
_TOL = 1e-12

# Keys that every forward_kalman record must carry.
_RECORD_KEYS = (
    "x_pred",
    "P_pred",
    "x_filt",
    "P_filt",
    "innovation",
    "innovation_variance",
)


# ---------------------------------------------------------------------------
# Small 2x2 linear-algebra helpers (pure stdlib, lists of lists).
# ---------------------------------------------------------------------------

def mat_mul(a, b):
    """Multiply two matrices (lists of lists of floats)."""
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])
    if cols_a != rows_b:
        raise ValueError("mat_mul: inner dimensions do not match")
    return [
        [sum(a[i][k] * b[k][j] for k in range(cols_a)) for j in range(cols_b)]
        for i in range(rows_a)
    ]


def mat_add(a, b):
    """Add two same-shape matrices."""
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise ValueError("mat_add: shape mismatch")
    return [
        [a[i][j] + b[i][j] for j in range(len(a[0]))]
        for i in range(len(a))
    ]


def mat_sub(a, b):
    """Subtract b from a, both same-shape matrices."""
    if len(a) != len(b) or len(a[0]) != len(b[0]):
        raise ValueError("mat_sub: shape mismatch")
    return [
        [a[i][j] - b[i][j] for j in range(len(a[0]))]
        for i in range(len(a))
    ]


def mat_scale(a, s):
    """Scale every entry of a matrix by the scalar s."""
    return [[a[i][j] * s for j in range(len(a[0]))] for i in range(len(a))]


def transpose(a):
    """Transpose a matrix."""
    return [[a[i][j] for i in range(len(a))] for j in range(len(a[0]))]


def mat_vec(a, v):
    """Multiply a matrix by a column vector given as a plain list."""
    if len(a[0]) != len(v):
        raise ValueError("mat_vec: inner dimensions do not match")
    return [sum(a[i][j] * v[j] for j in range(len(v))) for i in range(len(a))]


def inv_2x2(a):
    """Invert a 2x2 matrix; raise ValueError if it is singular."""
    det = a[0][0] * a[1][1] - a[0][1] * a[1][0]
    if abs(det) < _TOL:
        raise ValueError("inv_2x2: singular matrix")
    return [
        [a[1][1] / det, -a[0][1] / det],
        [-a[1][0] / det, a[0][0] / det],
    ]


# ---------------------------------------------------------------------------
# Constant-velocity model matrices.
# ---------------------------------------------------------------------------

def _model_matrices(dt, q):
    """Return (F, Q) for the constant-velocity model at step dt."""
    f = [[1.0, dt], [0.0, 1.0]]
    q_disc = [
        [q * dt ** 4 / 4.0, q * dt ** 3 / 2.0],
        [q * dt ** 3 / 2.0, q * dt ** 2],
    ]
    return f, q_disc


def _check_forward_inputs(measurements, dt, q, r, x0, p0):
    """Validate forward_kalman arguments; raise ValueError if non-physical."""
    if dt <= 0:
        raise ValueError("dt must be positive")
    if q < 0:
        raise ValueError("process noise intensity q must be non-negative")
    if r <= 0:
        raise ValueError("measurement variance r must be positive")
    if not isinstance(measurements, (list, tuple)) or len(measurements) < 2:
        raise ValueError("at least two measurements are required")
    if len(x0) != 2:
        raise ValueError("x0 must be a length-2 [position, velocity] state")
    if len(p0) != 2 or len(p0[0]) != 2 or len(p0[1]) != 2:
        raise ValueError("P0 must be a 2x2 covariance matrix")


# ---------------------------------------------------------------------------
# Public API.
# ---------------------------------------------------------------------------

def forward_kalman(measurements, dt, q, r, x0, p0):
    """Run the forward Kalman predict-update recursion over measurements.

    For every measurement k the step predicts x_pred = F x and
    P_pred = F P F^T + Q, then updates with the innovation, its variance
    S = H P_pred H^T + r, the gain K = P_pred H^T / S and the Joseph-form
    filtered covariance.  Each returned record stores x_pred, P_pred,
    x_filt, P_filt, innovation, innovation_variance, plus the step dt so
    the smoother can rebuild F.

    Raises ValueError when dt <= 0, q < 0, r <= 0, fewer than two
    measurements are given, x0 is not length 2, or P0 is not 2x2.
    """
    _check_forward_inputs(measurements, dt, q, r, x0, p0)
    f, q_disc = _model_matrices(dt, q)
    h = [[1.0, 0.0]]
    x = [float(x0[0]), float(x0[1])]
    p = [
        [float(p0[0][0]), float(p0[0][1])],
        [float(p0[1][0]), float(p0[1][1])],
    ]
    records = []
    for z in measurements:
        # Predict step.
        x_pred = mat_vec(f, x)
        p_pred = mat_add(mat_mul(mat_mul(f, p), transpose(f)), q_disc)
        # Update step.
        innovation = float(z) - x_pred[0]
        s = p_pred[0][0] + float(r)
        k_col = [[p_pred[0][0] / s], [p_pred[1][0] / s]]
        kh = [[k_col[0][0], 0.0], [k_col[1][0], 0.0]]
        eye_minus_kh = [
            [1.0 - kh[0][0], -kh[0][1]],
            [-kh[1][0], 1.0 - kh[1][1]],
        ]
        p_filt = mat_add(
            mat_mul(mat_mul(eye_minus_kh, p_pred), transpose(eye_minus_kh)),
            mat_scale(mat_mul(k_col, transpose(k_col)), r),
        )
        x_filt = [
            x_pred[0] + k_col[0][0] * innovation,
            x_pred[1] + k_col[1][0] * innovation,
        ]
        records.append(
            {
                "x_pred": x_pred,
                "P_pred": p_pred,
                "x_filt": x_filt,
                "P_filt": p_filt,
                "innovation": innovation,
                "innovation_variance": s,
                "dt": float(dt),
            }
        )
        x = x_filt
        p = p_filt
    return records


def _check_smooth_inputs(fwd_results):
    """Validate an rts_smooth input; raise ValueError when malformed."""
    if not isinstance(fwd_results, (list, tuple)) or len(fwd_results) < 2:
        raise ValueError("at least two forward records are required")
    for record in fwd_results:
        if not isinstance(record, dict):
            raise ValueError("each forward record must be a dict")
        for key in _RECORD_KEYS:
            if key not in record:
                raise ValueError("forward record is missing key %s" % key)


def rts_smooth(fwd_results):
    """Run the fixed-interval RTS backward recursion over forward records.

    Returns (smoothed_states, smoothed_covs, gains), each a list of
    length n aligned with the forward records.  The last smoothed state
    and covariance equal the last filtered values; for k = n-2 down to
    0 the smoother gain K_k = P_filt[k] F^T (P_pred[k+1])^-1 combines
    the filtered mean with the smoothed-minus-predicted difference.
    gains[k] holds the 2x2 smoother gain leaving step k; the final
    entry is a zero 2x2 placeholder so all three lists have length n.
    """
    _check_smooth_inputs(fwd_results)
    n = len(fwd_results)
    dt = fwd_results[0]["dt"]
    f = [[1.0, dt], [0.0, 1.0]]
    f_t = transpose(f)

    x_s = [None] * n
    p_s = [None] * n
    gains = [None] * n

    last = fwd_results[n - 1]
    x_s[n - 1] = [last["x_filt"][0], last["x_filt"][1]]
    p_s[n - 1] = copy.deepcopy(last["P_filt"])

    for k in range(n - 2, -1, -1):
        fwd = fwd_results[k]
        nxt = fwd_results[k + 1]
        gain = mat_mul(mat_mul(fwd["P_filt"], f_t), inv_2x2(nxt["P_pred"]))
        diff = mat_vec(gain, [x_s[k + 1][0] - nxt["x_pred"][0],
                              x_s[k + 1][1] - nxt["x_pred"][1]])
        x_s[k] = [fwd["x_filt"][0] + diff[0], fwd["x_filt"][1] + diff[1]]
        p_corr = mat_sub(p_s[k + 1], fwd_results[k + 1]["P_pred"])
        p_s[k] = mat_add(fwd["P_filt"], mat_mul(mat_mul(gain, p_corr), transpose(gain)))
        gains[k] = gain

    gains[n - 1] = [[0.0, 0.0], [0.0, 0.0]]
    return x_s, p_s, gains


def smoother_reduction(fwd_results, smoothed_covs):
    """Compare smoothed against filtered position variance step by step.

    Returns a dict with max_reduction (largest relative drop of the
    position variance), all_reduced (every smoothed position variance
    at or below the filtered one within 1e-12) and boundary_matches
    (the last smoothed covariance equals the last filtered covariance
    within 1e-12).
    """
    _check_smooth_inputs(fwd_results)
    if len(smoothed_covs) != len(fwd_results):
        raise ValueError("smoothed_covs must align with the forward records")
    reductions = []
    all_reduced = True
    for k in range(len(fwd_results)):
        p_f = fwd_results[k]["P_filt"][0][0]
        p_s = smoothed_covs[k][0][0]
        reductions.append((p_f - p_s) / p_f)
        if p_s > p_f + _TOL:
            all_reduced = False
    p_f_last = fwd_results[-1]["P_filt"]
    p_s_last = smoothed_covs[-1]
    boundary_matches = all(
        abs(p_s_last[i][j] - p_f_last[i][j]) <= _TOL
        for i in range(2)
        for j in range(2)
    )
    return {
        "max_reduction": max(reductions),
        "all_reduced": all_reduced,
        "boundary_matches": boundary_matches,
    }

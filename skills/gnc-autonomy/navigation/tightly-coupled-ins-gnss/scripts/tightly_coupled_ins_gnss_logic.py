"""Tightly coupled INS/GNSS integration logic (8-state error-state filter).

Pure-stdlib, deterministic module (math only, no RNG anywhere) implementing
the wave-43 leaf gnc-autonomy/navigation/tightly-coupled-ins-gnss: an INS
error-state Kalman filter updated on RAW pseudorange observables in the
simplified fixed 8-state form mandated by the leaf plan.

State vector x = [drx, dry, drz, dvx, dvy, dvz, db, dd] (indices 0-2
position error in m, 3-5 velocity error in m/s, 6 receiver clock bias error
in m, 7 receiver clock drift error in m/s). x is the correction ADDED to the
INS reference solution: corrected position r_hat = r_ref + dr, corrected
velocity v_hat = v_ref + dv, corrected clock bias b_hat = b_ref + db and
corrected clock drift d_hat = d_ref + dd. The INS reference trajectory
(position and velocity per epoch) is a GIVEN input; this leaf never
re-mechanizes the INS. The clock reference defaults to b_ref = d_ref = 0, so
the clock states hold the total bias and drift. The filter is the open-loop
error-state form: the estimated corrections are not fed back into the
reference, and the corrected solution is re-derived as reference + x_hat at
each epoch.

Error dynamics over dt (exact under the constant-velocity-error,
constant-drift model): dr(k+1) = dr(k) + dv(k)*dt with dv constant,
db(k+1) = db(k) + dd(k)*dt with dd constant. No attitude error states, no
accelerometer or gyro bias states, no gravity or Coriolis terms, no
earth-rate coupling, and no INS mechanization. The transition Phi is the
identity with dt on the dr-dv couplings (Phi[i][3+i] = dt for i = 0..2) and
Phi[6][7] = dt. Process noise Q is a per-step diagonal added in the
covariance propagation P_next = Phi*P*Phi^T + diag(q); measurement noise R
is the per-satellite variance list.

Measurement model (metres, clock column exactly 1.0, no speed-of-light
conversion): measured pseudorange rho_i = |r_true - s_i| + b_true + n_i;
predicted pseudorange rho_hat_i = |r_hat - s_i| + b_hat evaluated at the
full propagated estimate; innovation y_i = rho_meas,i - rho_hat_i. Row i of
the 8-column measurement matrix is the negated line of sight on the three
position channels, zero velocity-error and clock-drift columns and the unit
clock column: [-(sx-rx_hat)/rho_i, -(sy-ry_hat)/rho_i, -(sz-rz_hat)/rho_i,
0, 0, 0, 1, 0] with rho_i the geometric range. A single-epoch raw
pseudorange carries no velocity or drift information, so those states are
observed only through the time propagation (stated assumption).

Kalman update: S = H*P*H^T + R (m x m), K = P*H^T*S^-1 solved by Gaussian
elimination with partial pivoting, x_new = x + K*y, P_new = (I - K*H)*P
symmetrized by averaging. The run driver iterates over epochs: the first
epoch is updated from the initial x0, p0 directly (no prior propagation);
every later epoch first propagates the error state and covariance over dt
from the previous epoch posterior, then predicts, then updates. All epochs
of one profile share the satellite count m, with m >= 4 per update epoch
(fewer than four satellites raises ValueError; aiding through a partially
observable set is out of scope).

Does NOT do: the loosely coupled position-domain measurement update on GNSS
position fixes with the psi-angle error model (ins-gnss-integrated-filter);
the snapshot iterated least-squares position fix (gnss-pseudorange-
positioning); carrier-phase smoothing, Hatch recursion, smoothed ranges or
code-carrier divergence monitoring (gnss-carrier-smoothing); velocity or
clock drift from doppler or range-rate observables (gnss-doppler-velocity-
positioning); RAIM fault detection and exclusion (gnss-raim-fde); INS
mechanization or drift-error growth models (inertial-navigation); the
scalar single-axis recursion or tuning rules (kalman-filter-design).
"""

import math

STATE_SIZE = 8

# Pivot floor for the Gaussian elimination solves (a pivot below this
# threshold means the matrix is singular to working precision).
_PIVOT_FLOOR = 1e-300


def _is_finite_number(value):
    """True when value is a real finite number."""
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def _transpose(matrix):
    """Transpose of a rectangular list-of-lists matrix."""
    rows = len(matrix)
    cols = len(matrix[0]) if rows else 0
    return [[matrix[r][c] for r in range(rows)] for c in range(cols)]


def _identity(size):
    """size x size identity matrix as a list of lists."""
    return [[1.0 if r == c else 0.0 for c in range(size)] for r in range(size)]


def _matmul(a, b):
    """Row-by-row accumulated matrix product a*b (a is m x n, b is n x p)."""
    n = len(b)
    p = len(b[0]) if n else 0
    result = []
    for row in a:
        out_row = []
        for c in range(p):
            acc = 0.0
            for k in range(n):
                acc += row[k] * b[k][c]
            out_row.append(acc)
        result.append(out_row)
    return result


def _matvec(matrix, vec):
    """Matrix times vector, plain row-by-row accumulation."""
    return [sum(row[i] * vec[i] for i in range(len(vec))) for row in matrix]


def _symmetrize(matrix):
    """(matrix + matrix^T) / 2 elementwise, row-by-row accumulation."""
    n = len(matrix)
    return [[(matrix[r][c] + matrix[c][r]) / 2.0 for c in range(n)]
            for r in range(n)]


def _solve(a, b):
    """Solve the square linear system a*x = b by Gaussian elimination with
    partial pivoting. a is n x n, b a length-n list. A pivot below 1e-300
    raises ValueError (singular system). Deterministic row-by-row arithmetic.
    """
    n = len(a)
    if len(b) != n:
        raise ValueError("rhs length must match matrix size")
    aug = [list(a[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        pivot_row = col
        best = abs(aug[col][col])
        for r in range(col + 1, n):
            candidate = abs(aug[r][col])
            if candidate > best:
                best = candidate
                pivot_row = r
        if best < _PIVOT_FLOOR:
            raise ValueError("singular linear system")
        if pivot_row != col:
            aug[col], aug[pivot_row] = aug[pivot_row], aug[col]
        pivot = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pivot
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        acc = aug[r][n]
        for c in range(r + 1, n):
            acc -= aug[r][c] * x[c]
        x[r] = acc / aug[r][r]
    return x


def state_transition_matrix(dt):
    """Exact 8x8 transition of the constant-velocity-error, constant-drift
    model over dt: identity with dt on the dr-dv couplings
    (Phi[i][3+i] = dt for i = 0..2) and Phi[6][7] = dt.
    ValueError if dt is non-finite or <= 0.
    """
    if not _is_finite_number(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    phi = _identity(STATE_SIZE)
    for i in range(3):
        phi[i][3 + i] = dt
    phi[6][7] = dt
    return phi


def propagate_state(x, dt):
    """Propagate the length-8 error state over dt: dr += dv*dt on each axis
    and db += dd*dt, with dv and dd constant.
    ValueError if x is not length 8, dt non-finite or <= 0, or any x entry
    non-finite.
    """
    if len(x) != STATE_SIZE:
        raise ValueError("x must be length 8")
    if not _is_finite_number(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    if not all(_is_finite_number(v) for v in x):
        raise ValueError("all x entries must be finite")
    return [x[0] + x[3] * dt, x[1] + x[4] * dt, x[2] + x[5] * dt,
            x[3], x[4], x[5], x[6] + x[7] * dt, x[7]]


def propagate_covariance(p, q, dt):
    """Propagate the 8x8 error covariance: Phi*P*Phi^T + diag(q) with q the
    length-8 process-noise diagonal and Phi from state_transition_matrix.
    ValueError if p is not 8x8, q not length 8, any q entry negative or
    non-finite, or dt non-finite or <= 0.
    """
    if len(p) != STATE_SIZE or any(len(row) != STATE_SIZE for row in p):
        raise ValueError("p must be 8x8")
    if len(q) != STATE_SIZE:
        raise ValueError("q must be length 8")
    if not _is_finite_number(dt) or dt <= 0.0:
        raise ValueError("dt must be finite and positive")
    if not all(_is_finite_number(v) and v >= 0.0 for v in q):
        raise ValueError("all q entries must be finite and non-negative")
    phi = state_transition_matrix(dt)
    phi_t = _transpose(phi)
    inner = _matmul(p, phi_t)
    outer = _matmul(phi, inner)
    return [[outer[r][c] + (q[r] if r == c else 0.0)
             for c in range(STATE_SIZE)] for r in range(STATE_SIZE)]


def predicted_pseudoranges(sat_positions, ref_position, ref_bias):
    """Predicted pseudoranges |r - s_i| + b at the reference position and
    clock bias, in metres (the full propagated estimate is passed in as the
    reference by the caller).
    ValueError on an empty satellite list, non-length-3 position records or
    non-finite entries.
    """
    if len(ref_position) != 3:
        raise ValueError("ref_position must be length 3")
    if not all(_is_finite_number(v) for v in ref_position):
        raise ValueError("ref_position entries must be finite")
    if not _is_finite_number(ref_bias):
        raise ValueError("ref_bias must be finite")
    if not sat_positions:
        raise ValueError("satellite list must not be empty")
    ranges = []
    for sat in sat_positions:
        if len(sat) != 3:
            raise ValueError("each satellite record must be length 3")
        if not all(_is_finite_number(v) for v in sat):
            raise ValueError("satellite entries must be finite")
        dx = sat[0] - ref_position[0]
        dy = sat[1] - ref_position[1]
        dz = sat[2] - ref_position[2]
        ranges.append(math.sqrt(dx * dx + dy * dy + dz * dz) + ref_bias)
    return ranges


def measurement_matrix(sat_positions, ref_position):
    """m x 8 measurement matrix on raw pseudoranges at the reference
    position (the full propagated estimate is passed in as the reference):
    row i is [-(sx-rx_hat)/rho_i, -(sy-ry_hat)/rho_i, -(sz-rz_hat)/rho_i,
    0, 0, 0, 1, 0] with rho_i the geometric range (negated line of sight,
    the gnss-pseudorange-positioning sign convention, extended to 8 columns
    with the unit clock-bias column and zero velocity-error and clock-drift
    columns).
    ValueError if fewer than 4 satellites, ref_position not length 3, or a
    satellite within 1e-3 m of the receiver (zero range).
    """
    if len(ref_position) != 3:
        raise ValueError("ref_position must be length 3")
    if not all(_is_finite_number(v) for v in ref_position):
        raise ValueError("ref_position entries must be finite")
    if len(sat_positions) < 4:
        raise ValueError("at least 4 satellites are required")
    rows = []
    for sat in sat_positions:
        if len(sat) != 3:
            raise ValueError("each satellite record must be length 3")
        if not all(_is_finite_number(v) for v in sat):
            raise ValueError("satellite entries must be finite")
        dx = sat[0] - ref_position[0]
        dy = sat[1] - ref_position[1]
        dz = sat[2] - ref_position[2]
        rho = math.sqrt(dx * dx + dy * dy + dz * dz)
        if rho < 1e-3:
            raise ValueError("satellite within 1e-3 m of the receiver")
        rows.append([-dx / rho, -dy / rho, -dz / rho, 0.0, 0.0, 0.0,
                     1.0, 0.0])
    return rows


def kalman_update(x, p, h, innovations, variances):
    """Kalman update on the pseudorange residuals:
    S = H*P*H^T + R (m x m, R diagonal from variances),
    K = P*H^T*S^-1 solved by Gaussian elimination with partial pivoting,
    x_new = x + K*y, P_new = (I - K*H)*P symmetrized by averaging.
    Returns (x_new, p_new, k).
    ValueError on any shape mismatch (x not 8, p not 8x8, h rows not 8,
    empty h, innovation or variance length != m), a non-positive or
    non-finite variance, a non-finite innovation, or a singular innovation
    covariance S.
    """
    if len(x) != STATE_SIZE:
        raise ValueError("x must be length 8")
    if len(p) != STATE_SIZE or any(len(row) != STATE_SIZE for row in p):
        raise ValueError("p must be 8x8")
    m = len(innovations)
    if m == 0:
        raise ValueError("innovations must not be empty")
    if len(variances) != m:
        raise ValueError("variances must match the innovation count")
    if len(h) != m:
        raise ValueError("h must have one row per innovation")
    if any(len(row) != STATE_SIZE for row in h):
        raise ValueError("each h row must be length 8")
    if not all(_is_finite_number(v) for v in innovations):
        raise ValueError("all innovations must be finite")
    for var in variances:
        if not _is_finite_number(var) or var <= 0.0:
            raise ValueError("variances must be finite and positive")

    h_t = _transpose(h)
    # S = H*P*H^T + R, row-by-row accumulation.
    ph_t = _matmul(p, h_t)          # 8 x m
    hph_t = _matmul(h, ph_t)        # m x m
    s = [[hph_t[r][c] + (variances[r] if r == c else 0.0)
          for c in range(m)] for r in range(m)]
    # K = P*H^T*S^-1: each row j of K solves S * K[j]^T = (P*H^T)[j]^T.
    k = []
    for j in range(STATE_SIZE):
        k.append(_solve(s, list(ph_t[j])))
    # x_new = x + K*y.
    y_vec = list(innovations)
    x_new = [x[i] + sum(k[i][j] * y_vec[j] for j in range(m))
             for i in range(STATE_SIZE)]
    # P_new = (I - K*H)*P, symmetrized by averaging.
    kh = _matmul(k, h)              # 8 x 8
    eye = _identity(STATE_SIZE)
    i_minus_kh = [[eye[r][c] - kh[r][c]
                   for c in range(STATE_SIZE)] for r in range(STATE_SIZE)]
    p_new = _matmul(i_minus_kh, p)
    p_new = _symmetrize(p_new)
    return x_new, p_new, k


def corrected_navigation_state(ref_position, ref_velocity, ref_bias,
                               ref_drift, x):
    """Corrected navigation solution dict with keys x, y, z, vx, vy, vz,
    bias, drift, each the reference component plus the matching error-state
    correction: r_hat = r_ref + dr, v_hat = v_ref + dv,
    b_hat = b_ref + db, d_hat = d_ref + dd.
    ValueError on non-length-3 reference records or x not length 8.
    """
    if len(ref_position) != 3:
        raise ValueError("ref_position must be length 3")
    if len(ref_velocity) != 3:
        raise ValueError("ref_velocity must be length 3")
    if len(x) != STATE_SIZE:
        raise ValueError("x must be length 8")
    return {
        "x": ref_position[0] + x[0],
        "y": ref_position[1] + x[1],
        "z": ref_position[2] + x[2],
        "vx": ref_velocity[0] + x[3],
        "vy": ref_velocity[1] + x[4],
        "vz": ref_velocity[2] + x[5],
        "bias": ref_bias + x[6],
        "drift": ref_drift + x[7],
    }


def run_tightly_coupled_profile(epochs, x0, p0, q, dt, variances):
    """Run the tightly coupled filter over the epoch list and return one
    result dict per epoch. Each epoch dict carries sat_positions (list of
    m ECEF satellite positions), pseudoranges (list of m measured raw code
    pseudoranges), ref_position, ref_velocity, ref_bias and ref_drift (the
    INS reference trajectory inputs and the clock reference, b_ref = d_ref =
    0 in the worked form). The first epoch updates from x0, p0 directly (no
    prior propagation); every later epoch first propagates the error state
    and covariance over dt from the previous epoch posterior, then predicts
    the pseudoranges at the full propagated estimate, builds the measurement
    matrix from the line-of-sight geometry at that estimate and applies the
    Kalman update on the residuals.

    Result dict keys: x_pred, p_pred, innovations, innovation_rms (sqrt of
    the mean squared innovation), x_corr, p_corr and corrected (the
    corrected_navigation_state dict), plus copies of sat_positions,
    pseudoranges, ref_position, ref_velocity, ref_bias and ref_drift.
    ValueError if the epoch list is empty, x0 not length 8, p0 not 8x8,
    q not length 8, the epoch satellite count is below 4, any epoch
    measurement count differs from the first, or variances do not match the
    count.
    """
    if not epochs:
        raise ValueError("epoch list must not be empty")
    if len(x0) != STATE_SIZE:
        raise ValueError("x0 must be length 8")
    if len(p0) != STATE_SIZE or any(len(row) != STATE_SIZE for row in p0):
        raise ValueError("p0 must be 8x8")
    if len(q) != STATE_SIZE:
        raise ValueError("q must be length 8")
    m = len(epochs[0]["pseudoranges"])
    if m < 4:
        raise ValueError("at least 4 satellites are required per epoch")
    if len(variances) != m:
        raise ValueError("variances must match the satellite count")
    if any(len(epoch["pseudoranges"]) != m for epoch in epochs):
        raise ValueError("all epochs must share the satellite count")
    for var in variances:
        if not _is_finite_number(var) or var <= 0.0:
            raise ValueError("variances must be finite and positive")

    state = list(x0)
    cov = [list(row) for row in p0]
    results = []
    for idx, epoch in enumerate(epochs):
        if idx == 0:
            x_pred = list(state)
            p_pred = [list(row) for row in cov]
        else:
            x_pred = propagate_state(state, dt)
            p_pred = propagate_covariance(cov, q, dt)
        ref_pos = epoch["ref_position"]
        ref_vel = epoch["ref_velocity"]
        ref_bias = epoch["ref_bias"]
        ref_drift = epoch["ref_drift"]
        # Full propagated estimate: INS reference plus the propagated
        # corrections (clock reference is a given input, zero in the
        # worked form, so the clock states hold the totals).
        full_pos = [ref_pos[i] + x_pred[i] for i in range(3)]
        full_bias = ref_bias + x_pred[6]
        predicted = predicted_pseudoranges(epoch["sat_positions"], full_pos,
                                           full_bias)
        innovations = [epoch["pseudoranges"][i] - predicted[i]
                       for i in range(m)]
        h = measurement_matrix(epoch["sat_positions"], full_pos)
        x_corr, p_corr, _k = kalman_update(x_pred, p_pred, h, innovations,
                                           variances)
        innovation_rms = math.sqrt(
            sum(y * y for y in innovations) / len(innovations))
        corrected = corrected_navigation_state(ref_pos, ref_vel, ref_bias,
                                               ref_drift, x_corr)
        results.append({
            "x_pred": list(x_pred),
            "p_pred": [list(row) for row in p_pred],
            "innovations": list(innovations),
            "innovation_rms": innovation_rms,
            "x_corr": list(x_corr),
            "p_corr": [list(row) for row in p_corr],
            "corrected": corrected,
            "sat_positions": [list(sat) for sat in epoch["sat_positions"]],
            "pseudoranges": list(epoch["pseudoranges"]),
            "ref_position": list(ref_pos),
            "ref_velocity": list(ref_vel),
            "ref_bias": ref_bias,
            "ref_drift": ref_drift,
        })
        state = x_corr
        cov = p_corr
    return results

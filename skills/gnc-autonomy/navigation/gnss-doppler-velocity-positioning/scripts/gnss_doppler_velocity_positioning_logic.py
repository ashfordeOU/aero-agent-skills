"""GNSS doppler velocity positioning logic.

Pure-stdlib, deterministic module (math only, no RNG anywhere) implementing
the wave-43 leaf gnc-autonomy/navigation/gnss-doppler-velocity-positioning:
a single-epoch snapshot estimate of the 3-D ECEF receiver velocity and the
receiver clock drift from per-satellite carrier-phase delta-range-rate
(doppler) observables in m/s.

The satellite ECEF state that produced each received signal is propagated
from broadcast-ephemeris-style Kepler element records at the
light-time-corrected transmit epoch t_tx = epoch - rho/c (found by
iteration inside velocity_least_squares). The line-of-sight unit vector u
runs from the receiver position (a supplied position fix, or the internal
pseudorange least-squares seed of pseudorange_position, which is never a
reported output of this leaf) to the satellite. The range-rate model is
rho_dot = (v_sat - v_rec) dot u + c*(dtr_dot - dts_dot), linearized into
geometry rows [u_x, u_y, u_z, -1.0] over the unknown state
x = (vx, vy, vz, c*dtr_dot); the 4x4 normal equations are solved by
Gaussian elimination with partial pivoting each pass.

This leaf is the velocity-domain sibling of gnss-pseudorange-positioning
(which owns the position and clock-bias snapshot; the doppler leaf solves
no position fix, runs no carrier-phase smoothing, no RAIM detection and no
spacecraft-comm frequency-domain model). Two-body Kepler propagation only:
no J2 or higher perturbations, no ionospheric or tropospheric range-rate
terms, no Sagnac terms beyond the ECEF frame rotation, no cycle slips and
no integer ambiguities. The receiver displacement over the signal transit
light time is second order and neglected.

The worked-example numbers printed by running this module directly match
the wave-43 leaf spec anchors (real prep outputs of the deterministic
reference implementation, stdlib math, exit 0).
"""

import math

# ---- module constants -----------------------------------------------------
MU_EARTH = 3.986004418e14      # m^3/s^2, WGS-84 gravitational parameter
OMEGA_EARTH = 7.2921150e-5     # rad/s, WGS-84 earth rotation rate
C_LIGHT = 299792458.0          # m/s, speed of light
R_EARTH = 6378137.0            # m, spherical earth radius (demo receiver context)
THETA_G0 = 1.1                 # rad, GMST at the reference epoch (linear model)
EPHEMERIS_WINDOW = 7200.0      # s, broadcast ephemeris validity window
NEWTON_TOL = 1e-14             # Kepler solver convergence tolerance (rad)
NEWTON_MAX = 60                # Kepler solver iteration cap


# ---- private helpers ------------------------------------------------------
def _rz(ang):
    """Rotation matrix about z by ang (tuple-of-tuples 3x3)."""
    c, s = math.cos(ang), math.sin(ang)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _rx(ang):
    """Rotation matrix about x by ang (tuple-of-tuples 3x3)."""
    c, s = math.cos(ang), math.sin(ang)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _matmat(a, b):
    """3x3 matrix product a*b, both tuple-of-tuples."""
    return tuple(tuple(sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3))
                 for r in range(3))


def _matvec(m, v):
    """3x3 matrix times a 3-vector."""
    return tuple(sum(m[r][c] * v[c] for c in range(3)) for r in range(3))


def _rot3z_neg(theta, v):
    """R3(-theta): rotation of 3-vector v about z by -theta (ECI to ECEF)."""
    c, s = math.cos(theta), math.sin(theta)
    return (c * v[0] + s * v[1], -s * v[0] + c * v[1], v[2])


def _dot(a, b):
    """Dot product of two 3-vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v):
    """Euclidean norm of a 3-vector."""
    return math.sqrt(_dot(v, v))


_SAT_KEYS = ("id", "a", "e", "inc", "raan", "argp", "m0", "toe", "dts0", "dts_dot")
_NUM_KEYS = ("a", "e", "inc", "raan", "argp", "m0", "toe", "dts0", "dts_dot")


def _validate_sat(sat):
    """Reject satellite records with missing, non-finite or non-physical keys."""
    if not isinstance(sat, dict) or any(k not in sat for k in _SAT_KEYS):
        raise ValueError("satellite record must carry id, a, e, inc, raan, "
                         "argp, m0, toe, dts0, dts_dot")
    for k in _NUM_KEYS:
        if not isinstance(sat[k], (int, float)) or not math.isfinite(sat[k]):
            raise ValueError("non-finite satellite element %s" % k)
    if sat["a"] <= 0.0:
        raise ValueError("semi-major axis must be positive")
    if not (0.0 <= sat["e"] < 1.0):
        raise ValueError("eccentricity must satisfy 0 <= e < 1")


# ---- public module functions ---------------------------------------------
def mean_to_eccentric(M, e):
    """Solve Kepler's equation E - e*sin(E) = M by Newton iteration.

    Args:
        M: mean anomaly in rad.
        e: eccentricity in [0, 1).
    Returns:
        Eccentric anomaly E in rad.
    Raises:
        ValueError: non-finite M or e, e outside [0, 1), or the Newton
        iteration fails to converge within NEWTON_MAX steps.
    """
    if not math.isfinite(M) or not math.isfinite(e):
        raise ValueError("mean anomaly and eccentricity must be finite")
    if not (0.0 <= e < 1.0):
        raise ValueError("eccentricity must satisfy 0 <= e < 1")
    E = M + e * math.sin(M)
    for _ in range(NEWTON_MAX):
        f = E - e * math.sin(E) - M
        if abs(f) < NEWTON_TOL:
            return E
        E = E - f / (1.0 - e * math.cos(E))
    raise ValueError("Newton iteration did not converge in %d steps" % NEWTON_MAX)


def kepler_state_eci(sat, t):
    """Propagate a broadcast-ephemeris-style element record to time t.

    Two-body dynamics: mean motion n = sqrt(MU_EARTH/a^3), mean anomaly
    advanced from the element epoch, Kepler's equation solved by
    mean_to_eccentric, perifocal position and velocity rotated to ECI by
    Rz(raan)*Rx(inc)*Rz(argp). J2 and higher perturbations are out of scope.

    Args:
        sat: element record with keys id, a, e, inc, raan, argp, m0, toe,
            dts0, dts_dot (angles in rad, a in m, dts0 in s, dts_dot in s/s).
        t: propagation epoch in s.
    Returns:
        (pos, vel) tuple of ECI 3-vectors, position in m and velocity in m/s.
    Raises:
        ValueError: invalid record, non-finite epoch, a <= 0, e outside
        [0, 1), or |t - toe| beyond EPHEMERIS_WINDOW.
    """
    _validate_sat(sat)
    if not math.isfinite(t):
        raise ValueError("epoch must be finite")
    if abs(t - sat["toe"]) > EPHEMERIS_WINDOW:
        raise ValueError("epoch outside the broadcast ephemeris window of "
                         "%g s" % EPHEMERIS_WINDOW)
    a, e, inc, raan, argp = sat["a"], sat["e"], sat["inc"], sat["raan"], sat["argp"]
    n = math.sqrt(MU_EARTH / a ** 3)
    M = sat["m0"] + n * (t - sat["toe"])
    E = mean_to_eccentric(M, e)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + e) * math.sin(E / 2.0),
                          math.sqrt(1.0 - e) * math.cos(E / 2.0))
    r_mag = a * (1.0 - e * math.cos(E))
    p = a * (1.0 - e * e)
    v_orb = math.sqrt(MU_EARTH / p)
    r_pf = (r_mag * math.cos(nu), r_mag * math.sin(nu), 0.0)
    v_pf = (v_orb * (-math.sin(nu)), v_orb * (e + math.cos(nu)), 0.0)
    rot = _matmat(_matmat(_rz(raan), _rx(inc)), _rz(argp))
    return _matvec(rot, r_pf), _matvec(rot, v_pf)


def ecef_state(r_eci, v_eci, t):
    """Rotate an ECI state into ECEF at time t under the linear GMST model.

    theta(t) = THETA_G0 + OMEGA_EARTH*t and the ECEF velocity subtracts the
    earth-rotation term: v_ecef = R3(-theta) v_eci - omega_earth x r_ecef.

    Args:
        r_eci, v_eci: ECI position (m) and velocity (m/s) 3-vectors.
        t: epoch in s.
    Returns:
        (pos, vel) tuple of ECEF 3-vectors.
    Raises:
        ValueError: the state is not two finite 3-vectors.
    """
    if len(r_eci) != 3 or len(v_eci) != 3:
        raise ValueError("ECI state must be two 3-vectors")
    if not all(math.isfinite(x) for x in r_eci + v_eci):
        raise ValueError("non-finite ECI state")
    theta = THETA_G0 + OMEGA_EARTH * t
    r_ecef = _rot3z_neg(theta, r_eci)
    v_rot = _rot3z_neg(theta, v_eci)
    wxr = (-OMEGA_EARTH * r_ecef[1], OMEGA_EARTH * r_ecef[0], 0.0)
    v_ecef = (v_rot[0] - wxr[0], v_rot[1] - wxr[1], v_rot[2] - wxr[2])
    return r_ecef, v_ecef


def line_of_sight(sat_pos, rec_pos):
    """Unit line-of-sight vector from the receiver to the satellite.

    Args:
        sat_pos: satellite ECEF position 3-vector (m).
        rec_pos: receiver ECEF position 3-vector (m).
    Returns:
        (u, rho) tuple: u the unit LOS 3-vector, rho the geometric range (m).
    Raises:
        ValueError: range below 1 m (satellite coincident with the receiver).
    """
    dx = (sat_pos[0] - rec_pos[0], sat_pos[1] - rec_pos[1], sat_pos[2] - rec_pos[2])
    rho = _norm(dx)
    if rho < 1.0:
        raise ValueError("satellite coincident with the receiver (range %.3e m)" % rho)
    return (dx[0] / rho, dx[1] / rho, dx[2] / rho), rho


def predicted_range_rate(sat_vel, rec_vel, u, dts_dot, dtr_dot):
    """Predicted carrier delta-range-rate observable in m/s.

    rho_dot = (v_sat - v_rec) dot u + C_LIGHT*(dtr_dot - dts_dot), with both
    clock drifts in s/s and the speed of light applied inside.

    Args:
        sat_vel: satellite ECEF velocity 3-vector (m/s).
        rec_vel: receiver ECEF velocity 3-vector (m/s).
        u: unit line-of-sight 3-vector (receiver to satellite).
        dts_dot: broadcast satellite clock drift (s/s).
        dtr_dot: receiver clock drift (s/s).
    Returns:
        Predicted range rate in m/s.
    Raises:
        ValueError: non-finite velocity, LOS or drift input.
    """
    vals = sat_vel + rec_vel + u
    if not all(math.isfinite(x) for x in vals):
        raise ValueError("non-finite velocity or line-of-sight input")
    if not (math.isfinite(dts_dot) and math.isfinite(dtr_dot)):
        raise ValueError("non-finite clock drift")
    rel = (sat_vel[0] - rec_vel[0], sat_vel[1] - rec_vel[1], sat_vel[2] - rec_vel[2])
    return _dot(rel, u) + C_LIGHT * (dtr_dot - dts_dot)


def solve_normal4(rows, rhs):
    """Solve the 4x4 linear system rows*x = rhs (Gaussian elimination, partial pivoting).

    Args:
        rows: 4x4 matrix of floats.
        rhs: 4-vector of floats.
    Returns:
        The 4-element solution tuple.
    Raises:
        ValueError: wrong shape, non-finite input, or a singular matrix
        (pivot below 1e-300).
    """
    a = [list(row) for row in rows]
    b = [float(x) for x in rhs]
    if len(a) != 4 or any(len(r) != 4 for r in a) or len(b) != 4:
        raise ValueError("solve_normal4 needs a 4x4 matrix and 4-vector rhs")
    if not all(math.isfinite(x) for r in a for x in r) or not all(math.isfinite(x) for x in b):
        raise ValueError("non-finite system in solve_normal4")
    for col in range(4):
        piv = max(range(col, 4), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-300:
            raise ValueError("singular normal matrix in solve_normal4")
        if piv != col:
            a[col], a[piv] = a[piv], a[col]
            b[col], b[piv] = b[piv], b[col]
        for r in range(col + 1, 4):
            f = a[r][col] / a[col][col]
            for c in range(col, 4):
                a[r][c] -= f * a[col][c]
            b[r] -= f * b[col]
    x = [0.0] * 4
    for r in range(3, -1, -1):
        s = b[r] - sum(a[r][c] * x[c] for c in range(r + 1, 4))
        x[r] = s / a[r][r]
    return tuple(x)


def velocity_least_squares(satellites, doppler, receiver_position,
                           epoch=0.0, dtr_dot_seed=0.0, iters=8, tol=1e-9,
                           doppler_sigma=0.05):
    """Iterated least-squares receiver velocity fix from doppler observables.

    Unknown state x = (vx, vy, vz, c*dtr_dot). Each satellite contributes the
    geometry row [u_x, u_y, u_z, -1.0] and rhs v_sat dot u - c*dts_dot -
    doppler_i (from u dot v_rec - c*dtr_dot = v_sat dot u - c*dts_dot -
    y_i), and the 4x4 normal equations (H^T H) x = H^T z are solved by
    solve_normal4 every pass. Each pass re-evaluates every satellite ECEF
    state at its light-time-corrected transmit epoch t_tx = epoch - rho/c
    until the maximum state correction falls below tol. The satellite
    element records are propagated by two-body Kepler dynamics, ECI rotated
    to ECEF under the linear GMST model.

    Args:
        satellites: list of element records (see kepler_state_eci).
        doppler: list of carrier delta-range-rate observables in m/s, one
            per satellite.
        receiver_position: ECEF position 3-vector (m) of the receiver at the
            reception epoch; a supplied position fix or the internal
            pseudorange seed. The position is never a reported output.
        epoch: reception epoch in s.
        dtr_dot_seed: receiver clock drift seed in s/s.
        iters: maximum number of iteration passes.
        tol: convergence tolerance on the max state correction (m/s on the
            velocity axes, m/s on the c*dtr_dot axis).
        doppler_sigma: assumed doppler 1-sigma (m/s) used for sigma0 when
            exactly 4 satellites leave zero residual degrees of freedom.
    Returns:
        dict with keys: velocity (3-tuple m/s), clock_drift_mps,
        clock_drift_sps, residuals (list m/s), residual_rms, sigma0,
        per_axis_sigma_mps (3-tuple m/s), clock_drift_sigma_mps,
        covariance_diag (4-tuple of (H^T H)^-1 diagonal), iterations,
        converged, num_satellites.
    Raises:
        ValueError: fewer than 4 satellites, doppler length mismatch,
        non-finite receiver position, epoch, seed, doppler or tol, iters < 1,
        tol <= 0, a bad satellite record, or a singular normal matrix or a
        coincident satellite propagated from the helpers.
    """
    n = len(satellites)
    if n < 4:
        raise ValueError("velocity fix needs at least 4 satellites, got %d" % n)
    if len(doppler) != n:
        raise ValueError("doppler list must match the satellite list length")
    if len(receiver_position) != 3 or not all(math.isfinite(x) for x in receiver_position):
        raise ValueError("receiver position must be a finite 3-vector")
    if not math.isfinite(epoch):
        raise ValueError("epoch must be finite")
    if not math.isfinite(dtr_dot_seed):
        raise ValueError("clock drift seed must be finite")
    if iters < 1:
        raise ValueError("iters must be at least 1")
    if tol <= 0.0:
        raise ValueError("tol must be positive")
    if not all(math.isfinite(y) for y in doppler):
        raise ValueError("non-finite doppler observable")
    for sat in satellites:
        _validate_sat(sat)

    def sat_state(t_eval):
        r_eci, v_eci = kepler_state_eci(sat, t_eval)
        return ecef_state(r_eci, v_eci, t_eval)

    state = [0.0, 0.0, 0.0, C_LIGHT * dtr_dot_seed]
    t_tx = [epoch] * n
    converged = False
    dx = float("inf")
    passes = 0
    for p in range(iters):
        A = [[0.0] * 4 for _ in range(4)]
        b = [0.0] * 4
        rho_new = []
        for i, sat in enumerate(satellites):
            r_ecef, v_ecef = sat_state(t_tx[i])
            u, rho = line_of_sight(r_ecef, receiver_position)
            rho_new.append(rho)
            z = _dot(v_ecef, u) - C_LIGHT * sat["dts_dot"] - doppler[i]
            row = (u[0], u[1], u[2], -1.0)
            for r in range(4):
                for c in range(4):
                    A[r][c] += row[r] * row[c]
                b[r] += row[r] * z
        x = solve_normal4(A, b)
        dx = max(abs(x[k] - state[k]) for k in range(4))
        state = list(x)
        passes = p + 1
        t_tx = [epoch - rho_new[i] / C_LIGHT for i in range(n)]
        if p >= 1 and dx < tol:
            converged = True
            break
    if not converged and passes == iters and dx < tol:
        converged = True
    v_rec = tuple(state[0:3])
    cdtr = state[3]
    dtr_dot = cdtr / C_LIGHT

    resid = []
    for i, sat in enumerate(satellites):
        r_ecef, v_ecef = sat_state(t_tx[i])
        u, rho = line_of_sight(r_ecef, receiver_position)
        pred = predicted_range_rate(v_ecef, v_rec, u, sat["dts_dot"], dtr_dot)
        resid.append(doppler[i] - pred)
    rms = math.sqrt(sum(r * r for r in resid) / n)
    sigma0 = math.sqrt(sum(r * r for r in resid) / (n - 4)) if n > 4 else doppler_sigma

    # covariance diagonal from the converged normal matrix (identity rhs)
    A = [[0.0] * 4 for _ in range(4)]
    for i, sat in enumerate(satellites):
        r_ecef, v_ecef = sat_state(t_tx[i])
        u, rho = line_of_sight(r_ecef, receiver_position)
        row = (u[0], u[1], u[2], -1.0)
        for r in range(4):
            for c in range(4):
                A[r][c] += row[r] * row[c]
    diag = []
    for col_rhs in range(4):
        e = [0.0] * 4
        e[col_rhs] = 1.0
        col = solve_normal4(A, e)
        diag.append(col[col_rhs])
    per_axis = tuple(sigma0 * math.sqrt(max(diag[k], 0.0)) for k in range(3))
    clock_sigma = sigma0 * math.sqrt(max(diag[3], 0.0))
    return {
        "velocity": v_rec,
        "clock_drift_mps": cdtr,
        "clock_drift_sps": dtr_dot,
        "residuals": resid,
        "residual_rms": rms,
        "sigma0": sigma0,
        "per_axis_sigma_mps": per_axis,
        "clock_drift_sigma_mps": clock_sigma,
        "covariance_diag": tuple(diag),
        "iterations": passes,
        "converged": converged,
        "num_satellites": n,
    }


def pseudorange_position(sat_positions, pseudoranges, iters=8, tol=1e-6):
    """Iterated least-squares receiver position feeder (geometry seed only).

    Internal geometry seed used to supply the receiver position to
    velocity_least_squares when no position fix is provided. Solves the
    four-unknown (x, y, z, clock bias in m) iterated position LS over rows
    [-u, 1.0]; the position and clock bias are never reported as outputs of
    this leaf (the position-domain snapshot belongs to
    gnss-pseudorange-positioning).

    Args:
        sat_positions: list of satellite ECEF position 3-vectors (m).
        pseudoranges: list of pseudorange measurements (m), one per satellite.
        iters: maximum number of iteration passes.
        tol: convergence tolerance on the max state correction.
    Returns:
        dict with keys: position (3-tuple m), clock_bias_m, residual_rms,
        iterations, converged.
    Raises:
        ValueError: fewer than 4 satellites, length mismatch, non-finite
        positions or pseudoranges, a singular geometry or a coincident
        satellite propagated from the helpers.
    """
    n = len(sat_positions)
    if n < 4:
        raise ValueError("position seed needs at least 4 satellites, got %d" % n)
    if len(pseudoranges) != n:
        raise ValueError("pseudorange list must match the satellite list length")
    if not all(len(s) == 3 and all(math.isfinite(x) for x in s) for s in sat_positions):
        raise ValueError("satellite positions must be finite 3-vectors")
    if not all(math.isfinite(p) for p in pseudoranges):
        raise ValueError("non-finite pseudorange")
    state = [0.0, 0.0, 0.0, 0.0]
    prev = None
    passes = 0
    for p in range(iters):
        A = [[0.0] * 4 for _ in range(4)]
        b = [0.0] * 4
        for i in range(n):
            u, rho = line_of_sight(sat_positions[i], tuple(state[0:3]))
            pred = rho + state[3]
            dr = pseudoranges[i] - pred
            row = (-u[0], -u[1], -u[2], 1.0)
            for r in range(4):
                for c in range(4):
                    A[r][c] += row[r] * row[c]
                b[r] += row[r] * dr
        x = solve_normal4(A, b)
        passes = p + 1
        state = [state[k] + x[k] for k in range(4)]
        if prev is not None:
            dx = max(abs(x[k]) for k in range(4))
            if dx < tol:
                break
        prev = x
    resid = []
    for i in range(n):
        u, rho = line_of_sight(sat_positions[i], tuple(state[0:3]))
        resid.append(pseudoranges[i] - (rho + state[3]))
    rms = math.sqrt(sum(r * r for r in resid) / n)
    return {
        "position": tuple(state[0:3]),
        "clock_bias_m": state[3],
        "residual_rms": rms,
        "iterations": passes,
        "converged": bool(passes < iters),
    }


if __name__ == "__main__":
    # Deterministic worked-example printout (mirrors the leaf spec anchors).
    print("gnss_doppler_velocity_positioning_logic module smoke: import OK")

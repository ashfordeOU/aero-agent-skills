"""GNSS pseudorange single-epoch position fix (pure stdlib).

Solve the four-unknown GNSS navigation equations (receiver ECEF
position x, y, z and receiver clock bias b, all in metres) from
satellite ECEF positions and pseudorange measurements with an iterated
linearized least-squares adjustment. Each iteration rebuilds the
geometry matrix H from the current receiver position and solves the
4x4 normal equations (H^T H) dx = H^T dr with a small Gaussian
elimination solver. No external dependencies, no network, fully
deterministic.

Satellite record: dict with keys x, y, z, pseudorange (all metres),
optional elevation_rad. Receiver state: 3-tuple (x, y, z).
"""

import math

# Spherical Earth radius used only for the approximate geodetic
# conversion (WGS-84 ellipsoid out of scope).
EARTH_RADIUS_SPHERICAL = 6378137.0

MIN_SATELLITES = 4
SATELLITE_KEYS = ("x", "y", "z", "pseudorange")
SOLVE_STATE_KEYS = ("x", "y", "z", "clock_bias", "residuals",
                    "residual_rms", "iterations", "converged")


def _validate_satellite(sat):
    """Raise ValueError when a satellite record is unusable."""
    for key in SATELLITE_KEYS:
        if key not in sat:
            raise ValueError("satellite record missing key: " + key)
        if not math.isfinite(sat[key]):
            raise ValueError("satellite value must be finite: " + key)


def _validate_receiver(recv):
    """Raise ValueError when the receiver position is non-finite."""
    for value in recv:
        if not math.isfinite(value):
            raise ValueError("receiver coordinates must be finite")


def geometric_range(recv, sat):
    """Euclidean range in metres between receiver recv and satellite."""
    _validate_satellite(sat)
    _validate_receiver(recv)
    rx, ry, rz = recv
    dx = sat["x"] - rx
    dy = sat["y"] - ry
    dz = sat["z"] - rz
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def predicted_pseudorange(recv, sat, clock_bias):
    """Predicted pseudorange: geometric range plus receiver clock bias."""
    _validate_satellite(sat)
    _validate_receiver(recv)
    if not math.isfinite(clock_bias):
        raise ValueError("clock bias must be finite")
    return geometric_range(recv, sat) + clock_bias


def residual(recv, sat, clock_bias):
    """Measured pseudorange minus predicted pseudorange, in metres."""
    _validate_satellite(sat)
    _validate_receiver(recv)
    if not math.isfinite(clock_bias):
        raise ValueError("clock bias must be finite")
    return sat["pseudorange"] - predicted_pseudorange(recv, sat, clock_bias)


def geometry_matrix(satellites, recv):
    """Build the n x 4 geometry matrix H for the current receiver.

    Row i is [-(sx-rx)/range, -(sy-ry)/range, -(sz-rz)/range, 1], the
    partials of the i-th pseudorange equation with respect to (x, y, z,
    clock bias).
    """
    _validate_receiver(recv)
    rx, ry, rz = recv
    rows = []
    for sat in satellites:
        _validate_satellite(sat)
        dx = sat["x"] - rx
        dy = sat["y"] - ry
        dz = sat["z"] - rz
        rng = math.sqrt(dx * dx + dy * dy + dz * dz)
        if rng <= 0.0:
            raise ValueError("satellite coincides with the receiver")
        rows.append([-dx / rng, -dy / rng, -dz / rng, 1.0])
    return rows


def solve_4x4(a, b):
    """Solve the 4x4 linear system a x = b by Gaussian elimination.

    Partial pivoting keeps the small system stable; a near-singular
    matrix raises ValueError.
    """
    if len(a) != 4 or any(len(row) != 4 for row in a) or len(b) != 4:
        raise ValueError("solve_4x4 requires a 4x4 matrix and 4-vector")
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    for col in range(4):
        pivot = max(range(col, 4), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) < 1e-300:
            raise ValueError("singular normal matrix, geometry is degenerate")
        m[col], m[pivot] = m[pivot], m[col]
        pv = m[col][col]
        for row in range(col + 1, 4):
            factor = m[row][col] / pv
            if factor == 0.0:
                continue
            for k in range(col, 5):
                m[row][k] -= factor * m[col][k]
    x = [0.0, 0.0, 0.0, 0.0]
    for row in range(3, -1, -1):
        total = m[row][4]
        for col in range(row + 1, 4):
            total -= m[row][col] * x[col]
        x[row] = total / m[row][row]
    return x


def _inverse_4x4(a):
    """Inverse of a 4x4 matrix by four right-hand-side solves."""
    columns = []
    for col in range(4):
        basis = [0.0, 0.0, 0.0, 0.0]
        basis[col] = 1.0
        columns.append(solve_4x4(a, basis))
    return [[columns[col][row] for col in range(4)] for row in range(4)]


def solve_iterated(satellites, iters=8, tol=1e-6,
                   x0=0.0, y0=0.0, z0=0.0, b0=0.0):
    """Iterated linearized least-squares GNSS position fix.

    Starts from the optional initial guess (default origin, zero clock
    bias) and iterates: build H at the current state, form the normal
    equations, solve for the 4x4 correction, update the state, and stop
    when the correction norm drops below tol. Returns a dict with x, y,
    z, clock_bias, residuals, residual_rms, iterations and converged.
    Requires at least four satellites.
    """
    if len(satellites) < MIN_SATELLITES:
        raise ValueError("at least 4 satellites are required for a fix")
    if iters < 1:
        raise ValueError("iters must be at least 1")
    for sat in satellites:
        _validate_satellite(sat)
    start = [x0, y0, z0, b0]
    if not all(math.isfinite(v) for v in start):
        raise ValueError("initial guess must be finite")

    state = [float(v) for v in start]
    converged = False
    iterations_used = 0
    for iteration in range(iters):
        iterations_used = iteration + 1
        recv = tuple(state[:3])
        h = geometry_matrix(satellites, recv)
        dr = [residual(recv, sat, state[3]) for sat in satellites]
        # Normal equations N dx = rhs with N = H^T H, rhs = H^T dr.
        n = [[0.0] * 4 for _ in range(4)]
        rhs = [0.0] * 4
        for i, row in enumerate(h):
            for j in range(4):
                rhs[j] += row[j] * dr[i]
                for k in range(4):
                    n[j][k] += row[j] * row[k]
        correction = solve_4x4(n, rhs)
        for axis in range(4):
            state[axis] += correction[axis]
        norm = math.sqrt(sum(c * c for c in correction))
        if norm < tol:
            converged = True
            break

    recv = tuple(state[:3])
    residuals = [residual(recv, sat, state[3]) for sat in satellites]
    rms = math.sqrt(sum(r * r for r in residuals) / len(residuals))
    return {
        "x": state[0],
        "y": state[1],
        "z": state[2],
        "clock_bias": state[3],
        "residuals": residuals,
        "residual_rms": rms,
        "iterations": iterations_used,
        "converged": converged,
    }


def position_error_estimate(satellites, fix):
    """Post-fit geometry error estimate for a converged fix dict.

    Inverts (H^T H) at the fix position and returns gdop, pdop, the
    user-equivalent range error (fix residual RMS) and the 1-sigma
    position error uere_equiv * pdop. Companion to the
    dilution-of-precision leaf; here the DOP comes from the post-fit
    geometry only.
    """
    for key in ("x", "y", "z", "residual_rms"):
        if key not in fix:
            raise ValueError("fix dict missing key: " + key)
    if len(satellites) < MIN_SATELLITES:
        raise ValueError("at least 4 satellites are required for a fix")
    for sat in satellites:
        _validate_satellite(sat)
    h = geometry_matrix(satellites, (fix["x"], fix["y"], fix["z"]))
    n = [[0.0] * 4 for _ in range(4)]
    for row in h:
        for j in range(4):
            for k in range(4):
                n[j][k] += row[j] * row[k]
    inv = _inverse_4x4(n)
    trace = sum(inv[i][i] for i in range(4))
    trace_xyz = sum(inv[i][i] for i in range(3))
    gdop = math.sqrt(trace)
    pdop = math.sqrt(trace_xyz)
    uere_equiv = fix["residual_rms"]
    return {
        "gdop": gdop,
        "pdop": pdop,
        "uere_equiv": uere_equiv,
        "pos_1sigma": uere_equiv * pdop,
    }


def to_geodetic_approx(x, y, z):
    """Approximate geodetic coordinates on a spherical Earth (WGS-84
    radius) from an ECEF position: lat_rad, lon_rad, alt_m."""
    for value in (x, y, z):
        if not math.isfinite(value):
            raise ValueError("ECEF coordinates must be finite")
    horizontal = math.sqrt(x * x + y * y)
    lat_rad = math.atan2(z, horizontal)
    lon_rad = math.atan2(y, x)
    alt_m = math.sqrt(x * x + y * y + z * z) - EARTH_RADIUS_SPHERICAL
    return {"lat_rad": lat_rad, "lon_rad": lon_rad, "alt_m": alt_m}

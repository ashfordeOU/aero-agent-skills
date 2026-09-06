"""gnss_rtk_positioning_logic.py - differential GNSS carrier-phase
baseline positioning (RTK): rover position relative to a fixed base from
common-view L1 double-difference carrier-phase observables.

Pure stdlib (math only), deterministic, no RNG, no orbit propagation.
The satellite ECEF positions at every epoch are supplied inputs, as a
receiver would receive them from a broadcast or precise ephemeris
service; this module never propagates an orbit.

Model summary (workflow steps of the gnss-rtk-positioning SKILL.md):
1. The per-satellite single difference across the receivers at each
   epoch is SD^j(t) = rover_phase - base_phase in cycles (the broadcast
   satellite clock offset cancels).
2. The double difference of pair j against the reference satellite is
   DD^j(t) = SD^j(t) - SD^0(t), scaled to metres by the L1 wavelength
   LAMBDA_L1: y_j(t) = -(u_j(t) - u_0(t)) . b - LAMBDA_L1 * N_j +
   eps_j(t), with u the unit line of sight from the base position, b the
   baseline rover minus base, and N_j the integer double-difference
   ambiguity of the pair, constant across a slip-free arc (the receiver
   clock difference cancels in the double difference).
3. The float solve stacks the linearized double differences over pairs
   and epochs into the least-squares normal equations (H^T H) x =
   H^T y over x = (b_x, b_y, b_z, A_1 ... A_m) with A_j = LAMBDA_L1*N_j
   in metres and geometry rows [-du_j(t), -e_j].
4. Integer resolution enumerates the rounding candidate sets (integer
   vectors within a Chebyshev radius of the rounded float vector),
   scores each by the float-covariance quadratic form, and applies the
   ratio test on the float covariance.
5. The fixed solution imposes the winning integer set and re-solves the
   baseline-only least squares over the shifted measurements; the fixed
   baseline is reported as the ENU offset at the base position.

Functions exposed (9): line_of_sight, single_difference,
form_double_differences, time_differenced_dd, solve_float_baseline,
resolve_integer_ambiguities, fixed_baseline_solution,
solve_td_baseline, ecef_to_enu.
"""

import math

# Module constants (pinned by the wave-44 engineering spec).
C_LIGHT = 299792458.0          # speed of light, m/s
F_L1 = 1575.42e6               # GPS L1 carrier frequency, Hz
LAMBDA_L1 = C_LIGHT / F_L1     # L1 wavelength, m/cycle (0.190293672798)
R_EARTH = 6378137.0            # spherical-Earth demo context for ENU only
MIN_SATELLITES = 5             # 4 non-reference pairs minimum
MIN_EPOCHS = 2                 # two epochs minimum for an observation arc
PIVOT_MIN = 1e-300             # singularity floor of the Gaussian elimination
DEFAULT_SEARCH_RADIUS = 2      # Chebyshev radius in cycles of the candidate box
DEFAULT_RATIO_MIN = 3.0        # ratio-test threshold on the float covariance


def _finite_vector(values, label):
    """Raise ValueError when values holds a non-finite entry."""
    for v in values:
        if not math.isfinite(float(v)):
            raise ValueError("%s must be finite" % label)


def line_of_sight(sat_pos, recv_pos):
    """Unit vector u from recv_pos to sat_pos and the range rho in m.

    Returns the (u, rho) tuple; u drives the linearized double-difference
    geometry rows of the float solve.
    """
    if len(sat_pos) != 3 or len(recv_pos) != 3:
        raise ValueError("positions must be 3-tuples")
    _finite_vector(sat_pos, "satellite position")
    _finite_vector(recv_pos, "receiver position")
    dx = [sat_pos[i] - recv_pos[i] for i in range(3)]
    rho = math.sqrt(dx[0] * dx[0] + dx[1] * dx[1] + dx[2] * dx[2])
    if rho < 1.0:
        raise ValueError("coincident satellite and receiver (range below 1 m)")
    return (dx[0] / rho, dx[1] / rho, dx[2] / rho), rho


def single_difference(rover_phase, base_phase):
    """Rover minus base carrier phase in cycles for one satellite at one
    epoch (the step-1 single difference across the receivers)."""
    _finite_vector([rover_phase, base_phase], "carrier phase")
    return rover_phase - base_phase


def form_double_differences(sds, reference_index=0):
    """Double differences in cycles of every non-reference satellite
    against the reference satellite: dd[j] = sd[j] - sd[reference]."""
    if len(sds) < 2:
        raise ValueError("fewer than 2 single differences")
    if not (0 <= reference_index < len(sds)):
        raise ValueError("reference index out of range")
    _finite_vector(sds, "single differences")
    return [sds[j] - sds[reference_index] for j in range(len(sds))
            if j != reference_index]


def time_differenced_dd(dd_cycles_later, dd_cycles_earlier):
    """Per-pair cycle difference later minus earlier. The double-
    difference ambiguities are constant across a slip-free arc, so the
    epoch difference is ambiguity-free."""
    if len(dd_cycles_later) != len(dd_cycles_earlier):
        raise ValueError("length mismatch between the two DD sets")
    if len(dd_cycles_later) < 1:
        raise ValueError("fewer than 1 double-difference pair")
    _finite_vector(dd_cycles_later, "later double differences")
    _finite_vector(dd_cycles_earlier, "earlier double differences")
    return [dd_cycles_later[j] - dd_cycles_earlier[j]
            for j in range(len(dd_cycles_later))]


def _gauss_solve(matrix, rhs):
    """Solve the square linear system matrix x = rhs by Gaussian
    elimination with partial pivoting. Raises ValueError when a pivot
    falls below PIVOT_MIN (singular normal matrix)."""
    n = len(matrix)
    a = [list(row) for row in matrix]
    b = list(rhs)
    for col in range(n):
        pivot_row = col
        best = abs(a[col][col]) if col < len(a[col]) else 0.0
        for r in range(col + 1, n):
            mag = abs(a[r][col])
            if mag > best:
                best = mag
                pivot_row = r
        if best < PIVOT_MIN:
            raise ValueError("singular normal matrix (pivot below PIVOT_MIN)")
        if pivot_row != col:
            a[col], a[pivot_row] = a[pivot_row], a[col]
            b[col], b[pivot_row] = b[pivot_row], b[col]
        piv = a[col][col]
        for r in range(col + 1, n):
            factor = a[r][col] / piv
            if factor == 0.0:
                continue
            for c in range(col, n):
                a[r][c] -= factor * a[col][c]
            b[r] -= factor * b[col]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = b[r]
        for c in range(r + 1, n):
            s -= a[r][c] * x[c]
        x[r] = s / a[r][r]
    return x


def _invert_matrix(matrix):
    """Inverse of a square matrix by Gaussian elimination with partial
    pivoting (identity-augmented). Raises ValueError when singular."""
    n = len(matrix)
    a = [list(row) + [1.0 if i == j else 0.0 for j in range(n)]
         for i, row in enumerate(matrix)]
    for col in range(n):
        pivot_row = col
        best = abs(a[col][col])
        for r in range(col + 1, n):
            mag = abs(a[r][col])
            if mag > best:
                best = mag
                pivot_row = r
        if best < PIVOT_MIN:
            raise ValueError("singular normal matrix (pivot below PIVOT_MIN)")
        if pivot_row != col:
            a[col], a[pivot_row] = a[pivot_row], a[col]
        piv = a[col][col]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col] / piv
            for c in range(col, 2 * n):
                a[r][c] -= factor * a[col][c]
        for c in range(col, 2 * n):
            a[col][c] /= piv
    return [tuple(row[n:]) for row in a]


def _dot3(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _validate_epochs(epochs, base_position, reference_index):
    """Structural validation shared by every solver. Returns (S, T).

    ValueErrors: fewer than MIN_SATELLITES satellites or MIN_EPOCHS
    epochs; position/phase length mismatch inside an epoch; inconsistent
    satellite counts across epochs; reference index out of range;
    non-finite positions, phases or base position; a coincident
    satellite (raised by line_of_sight during assembly)."""
    if len(base_position) != 3:
        raise ValueError("base position must be a 3-tuple")
    _finite_vector(base_position, "base position")
    if not isinstance(epochs, list) or len(epochs) < MIN_EPOCHS:
        raise ValueError("fewer than %d epochs" % MIN_EPOCHS)
    T = len(epochs)
    S = None
    for epoch in epochs:
        if not isinstance(epoch, dict):
            raise ValueError("each epoch must be a dict")
        for key in ("positions", "rover_phase", "base_phase"):
            if key not in epoch:
                raise ValueError("epoch missing '%s' key" % key)
        pos = epoch["positions"]
        rover = epoch["rover_phase"]
        base = epoch["base_phase"]
        if not (len(pos) == len(rover) == len(base)):
            raise ValueError("position/phase length mismatch in an epoch")
        if len(pos) < MIN_SATELLITES:
            raise ValueError("fewer than %d satellites" % MIN_SATELLITES)
        if S is None:
            S = len(pos)
        elif len(pos) != S:
            raise ValueError("satellite count changes between epochs")
        for p in pos:
            if len(p) != 3:
                raise ValueError("satellite position must be a 3-tuple")
            _finite_vector(p, "satellite position")
        _finite_vector(rover, "rover phase")
        _finite_vector(base, "base phase")
    if not (0 <= reference_index < S):
        raise ValueError("reference index out of range")
    return S, T


def _assemble_measurements(epochs, base_position, reference_index):
    """Per-epoch single differences, double differences (cycles), the
    metre-scale double-difference observables y and the geometry
    differences du = u_j - u_0. Validation is delegated to
    _validate_epochs plus the line_of_sight coincidence check; the
    double differences are re-derived from the raw phase streams, so
    the receiver clock difference and the satellite clock offsets
    cancel in the data that the solvers see."""
    S, T = _validate_epochs(epochs, base_position, reference_index)
    rows = []          # per epoch: list of (du 3-tuple, y in m)
    for epoch in epochs:
        pos = epoch["positions"]
        sds = [single_difference(epoch["rover_phase"][j],
                                 epoch["base_phase"][j]) for j in range(S)]
        dds = form_double_differences(sds, reference_index)
        u_ref, _ = line_of_sight(pos[reference_index], base_position)
        epoch_rows = []
        k = 0
        for j in range(S):
            if j == reference_index:
                continue
            u_j, _ = line_of_sight(pos[j], base_position)
            du = (u_j[0] - u_ref[0], u_j[1] - u_ref[1],
                  u_j[2] - u_ref[2])
            y = LAMBDA_L1 * dds[k]
            epoch_rows.append((du, y))
            k += 1
        rows.append(epoch_rows)
    return S, T, rows


def _baseline_only_solve(du_rows, obs):
    """Baseline-only least squares: rows du_i, observations obs_i and
    model obs = -du . b + eps, i.e. minimize sum((obs_i + du_i . b)^2).
    Returns (b 3-tuple, residuals list, rss)."""
    n = len(du_rows)
    n11 = n22 = n33 = 0.0
    n12 = n13 = n23 = 0.0
    q1 = q2 = q3 = 0.0
    for du, z in zip(du_rows, obs):
        ux, uy, uz = du
        n11 += ux * ux
        n22 += uy * uy
        n33 += uz * uz
        n12 += ux * uy
        n13 += ux * uz
        n23 += uy * uz
        q1 -= ux * z
        q2 -= uy * z
        q3 -= uz * z
    mat = ((n11, n12, n13), (n12, n22, n23), (n13, n23, n33))
    b = _gauss_solve(mat, (q1, q2, q3))
    res = []
    rss = 0.0
    for du, z in zip(du_rows, obs):
        r = z + _dot3(du, b)
        res.append(r)
        rss += r * r
    return (b[0], b[1], b[2]), res, rss


def _float_core(epochs, base_position, reference_index):
    """Shared float machinery: assemble rows and solve the normal
    equations (H^T H) x = H^T y over x = (b, A_1 ... A_m) with
    A_j = LAMBDA_L1 * N_j in metres, geometry rows [-du, -e_j].

    Returns (S, T, x, inv_normal, sigma0, residual_rms, n_meas,
    n_unknown)."""
    S, T, rows = _assemble_measurements(epochs, base_position,
                                        reference_index)
    m = S - 1
    n_meas = m * T
    n_unknown = 3 + m
    h_rows = []
    rhs = []
    for epoch_rows in rows:
        for k in range(m):
            du, y = epoch_rows[k]
            row = [-du[0], -du[1], -du[2]] + [0.0] * m
            row[3 + k] = -1.0
            h_rows.append(row)
            rhs.append(y)
    ht = [[h_rows[i][j] for i in range(n_meas)] for j in range(n_unknown)]
    normal = [[sum(ht[i][r] * h_rows[r][j] for r in range(n_meas))
               for j in range(n_unknown)] for i in range(n_unknown)]
    hty = [sum(ht[i][r] * rhs[r] for r in range(n_meas))
           for i in range(n_unknown)]
    x = _gauss_solve(normal, hty)
    inv_normal = _invert_matrix(normal)
    rss = 0.0
    for r in range(n_meas):
        pred = sum(h_rows[r][j] * x[j] for j in range(n_unknown))
        e = rhs[r] - pred
        rss += e * e
    dof = n_meas - n_unknown
    sigma0 = math.sqrt(rss / dof)
    residual_rms = math.sqrt(rss / n_meas)
    return (S, T, x, inv_normal, sigma0, residual_rms, n_meas, n_unknown)


def solve_float_baseline(epochs, base_position, reference_index=0):
    """Step-3 float solve: single-pass linear least squares over the
    stacked double differences (measurement rows [-du, -e_j], state
    (b_x, b_y, b_z, A_1 ... A_m) in metres, A_j = LAMBDA_L1 * N_j).

    Returns a dict with baseline_float_ecef, ambiguities_float_m,
    ambiguities_float_cycles, baseline_sigma_ecef,
    per_ambiguity_sigma_cycles, sigma0, residual_rms, covariance_diag,
    num_satellites, num_epochs, num_measurements, num_unknowns."""
    S, T, x, inv_normal, sigma0, rms, n_meas, n_unknown = _float_core(
        epochs, base_position, reference_index)
    m = S - 1
    baseline = tuple(x[0:3])
    amb_m = tuple(x[3 + k] for k in range(m))
    amb_cyc = tuple(amb_m[k] / LAMBDA_L1 for k in range(m))
    cov_diag = tuple(inv_normal[i][i] for i in range(n_unknown))
    base_sigma = tuple(sigma0 * math.sqrt(cov_diag[i]) for i in range(3))
    amb_sigma = tuple(sigma0 * math.sqrt(cov_diag[3 + k]) / LAMBDA_L1
                      for k in range(m))
    return {
        "baseline_float_ecef": baseline,
        "ambiguities_float_m": amb_m,
        "ambiguities_float_cycles": amb_cyc,
        "baseline_sigma_ecef": base_sigma,
        "per_ambiguity_sigma_cycles": amb_sigma,
        "sigma0": sigma0,
        "residual_rms": rms,
        "covariance_diag": cov_diag,
        "num_satellites": S,
        "num_epochs": T,
        "num_measurements": n_meas,
        "num_unknowns": n_unknown,
    }


def resolve_integer_ambiguities(epochs, base_position, reference_index=0,
                                search_radius=DEFAULT_SEARCH_RADIUS,
                                ratio_min=DEFAULT_RATIO_MIN):
    """Step-4 integer resolution: enumerate the rounding candidate sets
    (integer vectors within a Chebyshev radius of the rounded float
    ambiguity vector), score by the float-covariance quadratic form
    q(n) = (n - n_float)^T Q^-1 (n - n_float) with Q the m x m float
    ambiguity covariance block in cycles^2, and apply the ratio test
    q(second-best)/q(best) >= ratio_min. The fixed residual RSS of the
    two best candidates confirms the ranking in the residual domain.

    Returns a dict with best_candidate, second_best, best_q, second_q,
    ratio, resolved, candidates_searched, best_rss, second_rss."""
    if search_radius < 1:
        raise ValueError("search_radius must be >= 1 cycle")
    if ratio_min <= 1.0:
        raise ValueError("ratio_min must be > 1")
    S, T, x, inv_normal, sigma0, rms, n_meas, n_unknown = _float_core(
        epochs, base_position, reference_index)
    m = S - 1
    n_float = [x[3 + k] / LAMBDA_L1 for k in range(m)]
    n_round = [int(round(v)) for v in n_float]
    # Float ambiguity covariance block in cycles^2: the inverse-normal
    # block for the ambiguity state (metres) scaled by 1/LAMBDA_L1^2,
    # per the spec defining relation; the sigma0^2 scale cancels in the
    # ratio test and is omitted from the quadratic-form weight.
    q_mat = [[inv_normal[3 + i][3 + j] /
              (LAMBDA_L1 * LAMBDA_L1) for j in range(m)] for i in range(m)]
    q_inv = _invert_matrix(q_mat)
    width = 2 * search_radius + 1
    total = width ** m
    best_q = None
    second_q = None
    best_cand = None
    second_cand = None
    for code in range(total):
        c = code
        cand = []
        for k in range(m):
            d = c % width
            c //= width
            cand.append(n_round[k] + (d - search_radius))
        delta = [cand[k] - n_float[k] for k in range(m)]
        q = 0.0
        for i in range(m):
            acc = 0.0
            for j in range(m):
                acc += q_inv[i][j] * delta[j]
            q += delta[i] * acc
        if best_q is None or q < best_q:
            second_q, second_cand = best_q, best_cand
            best_q, best_cand = q, tuple(cand)
        elif second_q is None or q < second_q:
            second_q, second_cand = q, tuple(cand)
    # Residual-domain confirmation on the two q-best candidates.
    _, _, rows = _assemble_measurements(epochs, base_position,
                                        reference_index)
    du_all = []
    obs_all = []
    for epoch_rows in rows:
        for k in range(m):
            du, y = epoch_rows[k]
            du_all.append(du)
            obs_all.append(y)
    best_rss = None
    second_rss = None
    for cand, tag in ((best_cand, "best"), (second_cand, "second")):
        z = [obs_all[i] + LAMBDA_L1 * cand[i % m] for i in range(len(obs_all))]
        _, _, rss = _baseline_only_solve(du_all, z)
        if tag == "best":
            best_rss = rss
        else:
            second_rss = rss
    if best_q is not None and second_q is not None and best_q > 0.0:
        ratio = second_q / best_q
    elif best_q is not None and best_q == 0.0 and second_q is not None \
            and second_q > 0.0:
        ratio = float("inf")
    else:
        ratio = 1.0
    resolved = ratio >= ratio_min
    return {
        "best_candidate": best_cand,
        "second_best": second_cand,
        "best_q": best_q,
        "second_q": second_q,
        "ratio": ratio,
        "resolved": resolved,
        "candidates_searched": total,
        "best_rss": best_rss,
        "second_rss": second_rss,
    }


def fixed_baseline_solution(epochs, base_position, integer_ambiguities,
                            reference_index=0):
    """Step-5 fixed solution: impose the winning integer set n (cycles)
    and re-solve the baseline-only least squares over the shifted
    measurements y_j(t) + LAMBDA_L1 * n_j with rows -du_j(t); per-axis
    1-sigma from sigma0 * sqrt(diag((G^T G)^-1)) with sigma0 over
    m*T - 3 degrees of freedom.

    Returns a dict with baseline_ecef, per_axis_sigma_ecef, sigma0,
    residual_rms, num_measurements."""
    S, T, rows = _assemble_measurements(epochs, base_position,
                                        reference_index)
    m = S - 1
    if len(integer_ambiguities) != m:
        raise ValueError("integer_ambiguities length must equal S - 1")
    du_all = []
    obs_all = []
    for epoch_rows in rows:
        for k in range(m):
            du, y = epoch_rows[k]
            du_all.append(du)
            obs_all.append(y + LAMBDA_L1 * integer_ambiguities[k])
    n_meas = len(obs_all)
    b, res, rss = _baseline_only_solve(du_all, obs_all)
    dof = n_meas - 3
    sigma0 = math.sqrt(rss / dof)
    # Normal matrix G^T G with G rows -du: same 3x3 sum as the solve.
    n11 = n22 = n33 = 0.0
    n12 = n13 = n23 = 0.0
    for du in du_all:
        ux, uy, uz = du
        n11 += ux * ux
        n22 += uy * uy
        n33 += uz * uz
        n12 += ux * uy
        n13 += ux * uz
        n23 += uy * uz
    inv_g = _invert_matrix(((n11, n12, n13), (n12, n22, n23),
                            (n13, n23, n33)))
    axis_sigma = tuple(sigma0 * math.sqrt(inv_g[i][i]) for i in range(3))
    return {
        "baseline_ecef": b,
        "per_axis_sigma_ecef": axis_sigma,
        "sigma0": sigma0,
        "residual_rms": math.sqrt(rss / n_meas),
        "num_measurements": n_meas,
    }


def solve_td_baseline(epochs, base_position, reference_index=0):
    """Time-differenced precursor read: baseline-only least squares over
    the ambiguity-free epoch differences of the double differences
    (adjacent epoch pairs, rows -(du(t2) - du(t1))), which carry no
    ambiguity term because the integers are constant across a slip-free
    arc. Returns a dict with baseline_ecef, residual_rms,
    num_equations."""
    S, T, rows = _assemble_measurements(epochs, base_position,
                                        reference_index)
    m = S - 1
    du_diff = []
    obs_diff = []
    for e in range(T - 1):
        for k in range(m):
            du0, y0 = rows[e][k]
            du1, y1 = rows[e + 1][k]
            du_diff.append((du1[0] - du0[0], du1[1] - du0[1],
                            du1[2] - du0[2]))
            obs_diff.append(y1 - y0)
    b, res, rss = _baseline_only_solve(du_diff, obs_diff)
    n_eq = len(obs_diff)
    return {
        "baseline_ecef": b,
        "residual_rms": math.sqrt(rss / n_eq),
        "num_equations": n_eq,
    }


def ecef_to_enu(delta_ecef, base_position):
    """Spherical-Earth local ENU offset (e, n, u) in m of the ECEF
    vector delta_ecef at the base position: latitude/longitude from the
    base ECEF on the sphere of radius R_EARTH, local basis e =
    (-sin lon, cos lon, 0), n = (-sin lat cos lon, -sin lat sin lon,
    cos lat), u = (cos lat cos lon, cos lat sin lon, sin lat). At the
    demo base (lat 0, lon 0) the basis is exactly (y, z, x)."""
    if len(delta_ecef) != 3 or len(base_position) != 3:
        raise ValueError("vectors must be 3-tuples")
    _finite_vector(delta_ecef, "delta_ecef")
    _finite_vector(base_position, "base position")
    bx, by, bz = base_position
    radius = math.sqrt(bx * bx + by * by + bz * bz)
    if radius == 0.0:
        raise ValueError("zero base position")
    lon = math.atan2(by, bx)
    lat = math.asin(bz / radius)
    slon, clon = math.sin(lon), math.cos(lon)
    slat, clat = math.sin(lat), math.cos(lat)
    e_vec = (-slon, clon, 0.0)
    n_vec = (-slat * clon, -slat * slon, clat)
    u_vec = (clat * clon, clat * slon, slat)
    e = _dot3(delta_ecef, e_vec)
    n = _dot3(delta_ecef, n_vec)
    u = _dot3(delta_ecef, u_vec)
    return (e, n, u)

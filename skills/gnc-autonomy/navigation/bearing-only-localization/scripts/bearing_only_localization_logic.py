"""Bearing-only localization of a stationary emitter (pure stdlib, deterministic).

Implements the Stansfield closed-form weighted least squares fix of a
stationary emitter from N passive bearing lines measured at known observer
positions. The module supports the SKILL.md workflow of the
gnc-autonomy/navigation/bearing-only-localization leaf:

1. Assemble the bearing-line measurement set: observer positions (xi, yi),
   measured bearing beta_i per observer and the per-line 1-sigma bearing
   error sigma_i (wls_fix inputs; at least two observers required).
2. Form the linearized bearing equations
   sin(beta_i)*(x - xi) - cos(beta_i)*(y - yi) = 0 per observer, stacked as
   A z = b, and solve the equal-angle first pass with weights
   W_ii = 1/sigma_i^2 (wls_fix pass 1).
3. Run the Stansfield distance-weighted second pass with pass-1 ranges
   r_i and weights W_ii = 1/(sigma_i^2 * r_i^2), returning the final fix
   and the fix covariance C = (A^T W A)^-1 (wls_fix pass 2).
4. Read the 1-sigma error ellipse from the fix covariance (error_ellipse).
5. Compute the per-bearing residual angles and their RMS
   (residual_angles_deg, residual_rms_deg).
6. Assess the observer geometry (geometry_dilution_factor) and read the
   observer-geometry dilution verdict (dilution_verdict).
7. Optionally refine the fix in three dimensions with
   refine_3d_gauss_newton when azimuth and elevation angles are available.

Angles enter and leave in degrees; radians are used inside. Deterministic:
no RNG, no imports beyond math. Angles are wrapped with wrap180_deg into
[-180, 180) degrees and bearings with % 360.0 into [0, 360) degrees.
"""

import math

# Module constants (radians are dimensionless, distances in metres).
DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
_SINGULAR_REL_EPS = 1e-12  # relative determinant floor for a singular normal matrix
_COINCIDENT_M = 1e-9       # observer closer than this to the pass-1 fix is rejected
_GN_MU_FACTOR = 1e-12      # Gauss-Newton damping coefficient factor
_DEFAULT_GN_MAX_ITERS = 30
_DEFAULT_GN_TOL = 1e-9


def wrap180_deg(angle_deg):
    """Wrap an angle in degrees into [-180, 180).

    The wrap is exact by construction for multiples of 360 degrees and is
    used for every per-bearing residual angle in the module.
    """
    return (angle_deg + 180.0) % 360.0 - 180.0


def bearing_deg(ox, oy, tx, ty):
    """Bearing in [0, 360) degrees from observer (ox, oy) toward (tx, ty).

    Bearing is measured from the +x axis toward +y: atan2(ty - oy, tx - ox)
    in radians converted to degrees, reduced modulo 360. Raises ValueError
    when any argument is non-finite.
    """
    if not all(math.isfinite(v) for v in (ox, oy, tx, ty)):
        raise ValueError("bearing_deg requires finite coordinates")
    return math.degrees(math.atan2(ty - oy, tx - ox)) % 360.0


def _unit_normal(beta_deg):
    """Unit line normal g = (sin beta, -cos beta) for a bearing in degrees."""
    beta_rad = beta_deg * DEG2RAD
    return (math.sin(beta_rad), -math.cos(beta_rad))


def _check_observers_2d(observers, bearings_deg, sigma_deg):
    """Validate observer/bearing/sigma lists for the 2-D functions.

    Raises ValueError for fewer than two observers, length mismatches,
    non-finite observer coordinates or bearings, and non-finite or
    non-positive sigma values.
    """
    n = len(observers)
    if n < 2:
        raise ValueError("at least two observers with bearing lines are required")
    if len(bearings_deg) != n:
        raise ValueError("bearing count must match the observer count")
    for (xi, yi) in observers:
        if not (math.isfinite(xi) and math.isfinite(yi)):
            raise ValueError("non-finite observer coordinate")
    for beta in bearings_deg:
        if not math.isfinite(beta):
            raise ValueError("non-finite bearing angle")
    if sigma_deg is not None:
        if len(sigma_deg) != n:
            raise ValueError("sigma count must match the observer count")
        for sigma in sigma_deg:
            if not math.isfinite(sigma) or sigma <= 0.0:
                raise ValueError("sigma must be finite and greater than zero")


def _normal_system(normals, rhs, weights):
    """Build the 2x2 weighted normal matrix N = A^T W A and rhs A^T W b.

    normals holds the unit line normals g_i, rhs the scalars g_i . o_i and
    weights the diagonal of W. Returns (N, c) with N as ((n00, n01),
    (n01, n11)) and c as (c0, c1); the matrix is symmetric by construction.
    """
    n00 = n01 = n11 = 0.0
    c0 = c1 = 0.0
    for (gx, gy), bi, w in zip(normals, rhs, weights):
        n00 += w * gx * gx
        n01 += w * gx * gy
        n11 += w * gy * gy
        c0 += w * gx * bi
        c1 += w * gy * bi
    return ((n00, n01), (n01, n11)), (c0, c1)


def _det2(nmat):
    """Determinant of the symmetric 2x2 matrix ((a, b), (b, c))."""
    return nmat[0][0] * nmat[1][1] - nmat[0][1] * nmat[0][1]


def _check_nonsingular_2x2(nmat, message):
    """Raise ValueError when a 2x2 normal matrix is singular.

    Singularity is a non-positive determinant or a determinant vanishing
    relative to the diagonal product (parallel or coincident bearing lines
    give a rank-one normal matrix).
    """
    det = _det2(nmat)
    diag_prod = nmat[0][0] * nmat[1][1]
    if det <= 0.0 or det <= _SINGULAR_REL_EPS * diag_prod:
        raise ValueError(message)
    return det


def _solve_2x2(nmat, cvec):
    """Solve the 2x2 symmetric system N z = c by the closed-form inverse.

    Caller guarantees a nonsingular matrix; returns (x, y).
    """
    det = _det2(nmat)
    n00, n01, n11 = nmat[0][0], nmat[0][1], nmat[1][1]
    x = (n11 * cvec[0] - n01 * cvec[1]) / det
    y = (n00 * cvec[1] - n01 * cvec[0]) / det
    return (x, y)


def _inv_2x2(nmat, det):
    """Closed-form inverse of the symmetric 2x2 matrix as [[a, b], [b, c]]."""
    n00, n01, n11 = nmat[0][0], nmat[0][1], nmat[1][1]
    return [[n11 / det, -n01 / det], [-n01 / det, n00 / det]]


def wls_fix(observers, bearings_deg, sigma_deg=None):
    """Stansfield weighted least squares fix of the emitter (workflow steps 2-3).

    observers is a list of (xi, yi) observer positions in metres, one entry
    per bearing; bearings_deg holds the measured bearing of each line in
    degrees; sigma_deg optionally holds the per-line 1-sigma bearing error
    in degrees.

    Pass 1 uses equal-angle weights W_ii = 1/sigma_i^2 and gives the first
    estimate z1. Pass 2 uses the classical Stansfield range weights
    W_ii = 1/(sigma_i^2 * r_i^2) at the pass-1 distances r_i and gives the
    final fix z2 plus the fix covariance C = (A^T W A)^-1 in m^2. Without
    sigma_deg the geometry-only unweighted solve (A^T A)^-1 A^T b is
    returned with iterations 1 and ranges_m None.

    Returns a dict with keys x_m, y_m (final fix), pass1_x_m, pass1_y_m,
    covariance, ranges_m and iterations. Raises ValueError for fewer than
    two observers, length mismatches, non-finite inputs, sigma <= 0, a
    singular normal matrix (parallel or coincident bearing lines), or an
    observer within 1e-9 m of the pass-1 fix.
    """
    _check_observers_2d(observers, bearings_deg, sigma_deg)
    normals = [_unit_normal(beta) for beta in bearings_deg]
    rhs = [gx * xi + gy * yi for (gx, gy), (xi, yi) in zip(normals, observers)]
    if sigma_deg is None:
        weights = [1.0] * len(observers)
    else:
        weights = [1.0 / (sigma * DEG2RAD) ** 2 for sigma in sigma_deg]
    n1, c1 = _normal_system(normals, rhs, weights)
    _check_nonsingular_2x2(
        n1, "singular normal matrix: parallel or coincident bearing lines"
    )
    x1, y1 = _solve_2x2(n1, c1)
    if sigma_deg is None:
        cov = _inv_2x2(n1, _det2(n1))
        return {
            "x_m": x1,
            "y_m": y1,
            "pass1_x_m": x1,
            "pass1_y_m": y1,
            "covariance": cov,
            "ranges_m": None,
            "iterations": 1,
        }
    ranges_m = [
        math.hypot(x1 - xi, y1 - yi) for (xi, yi) in observers
    ]
    if any(r <= _COINCIDENT_M for r in ranges_m):
        raise ValueError("observer within 1e-9 m of the pass-1 fix")
    pass2_weights = [
        1.0 / ((sigma * DEG2RAD) ** 2 * r * r)
        for sigma, r in zip(sigma_deg, ranges_m)
    ]
    n2, c2 = _normal_system(normals, rhs, pass2_weights)
    _check_nonsingular_2x2(
        n2, "singular normal matrix: parallel or coincident bearing lines"
    )
    x2, y2 = _solve_2x2(n2, c2)
    cov = _inv_2x2(n2, _det2(n2))
    return {
        "x_m": x2,
        "y_m": y2,
        "pass1_x_m": x1,
        "pass1_y_m": y1,
        "covariance": cov,
        "ranges_m": ranges_m,
        "iterations": 2,
    }


def error_ellipse(cov):
    """1-sigma error ellipse of a 2x2 fix covariance (workflow step 4).

    With eigenvalues lambda_max >= lambda_min >= 0 of the symmetric
    covariance, the semi-axes are a = sqrt(lambda_max) and
    b = sqrt(lambda_min) in m and the major-axis orientation is
    0.5*atan2(2*C01, C00 - C11) wrapped into [-180, 180) degrees. Returns a
    dict with keys semi_major_m, semi_minor_m and orientation_deg. Raises
    ValueError when an eigenvalue is negative (indefinite matrix).
    """
    c00 = cov[0][0]
    c01 = cov[0][1]
    c11 = cov[1][1]
    trace = c00 + c11
    disc = (c00 - c11) ** 2 + 4.0 * c01 * c01
    lam_max = 0.5 * (trace + math.sqrt(disc))
    lam_min = 0.5 * (trace - math.sqrt(disc))
    if lam_min < 0.0 or lam_max < 0.0:
        raise ValueError("indefinite covariance matrix: negative eigenvalue")
    orientation = 0.5 * math.atan2(2.0 * c01, c00 - c11) * RAD2DEG
    return {
        "semi_major_m": math.sqrt(lam_max),
        "semi_minor_m": math.sqrt(lam_min),
        "orientation_deg": wrap180_deg(orientation),
    }


def residual_angles_deg(observers, bearings_deg, x_m, y_m):
    """Per-bearing residual angles at a fix (workflow step 5).

    For every line the predicted bearing at (x_m, y_m) is
    atan2(y_m - yi, x_m - xi) in [0, 360) and the residual is
    wrap180(measured - predicted), the signed angular leftover in degrees.
    Raises ValueError as wls_fix does (length and finiteness checks).
    """
    _check_observers_2d(observers, bearings_deg, None)
    residuals = []
    for (xi, yi), beta in zip(observers, bearings_deg):
        predicted = bearing_deg(xi, yi, x_m, y_m)
        residuals.append(wrap180_deg(beta - predicted))
    return residuals


def residual_rms_deg(observers, bearings_deg, x_m, y_m):
    """RMS of the wrapped per-bearing residual angles in degrees."""
    residuals = residual_angles_deg(observers, bearings_deg, x_m, y_m)
    return math.sqrt(sum(r * r for r in residuals) / len(residuals))


def geometry_dilution_factor(observers, bearings_deg):
    """Observer-geometry dilution of the bearing-line set (workflow step 6).

    With S the Gram matrix of the unit line normals, the dilution factor is
    d = sqrt(lambda_max(S^-1)) = 1/sqrt(lambda_min(S)), dimensionless.
    Raises ValueError for a singular Gram matrix (all bearing lines
    parallel) or fewer than two observers.
    """
    n = len(observers)
    if n < 2:
        raise ValueError("at least two observers with bearing lines are required")
    if len(bearings_deg) != n:
        raise ValueError("bearing count must match the observer count")
    s00 = s01 = s11 = 0.0
    for (xi, yi), beta in zip(observers, bearings_deg):
        if not (math.isfinite(xi) and math.isfinite(yi)):
            raise ValueError("non-finite observer coordinate")
        if not math.isfinite(beta):
            raise ValueError("non-finite bearing angle")
        gx, gy = _unit_normal(beta)
        s00 += gx * gx
        s01 += gx * gy
        s11 += gy * gy
    gram = ((s00, s01), (s01, s11))
    _check_nonsingular_2x2(
        gram, "singular normal Gram matrix: all bearing lines parallel"
    )
    trace = s00 + s11
    disc = trace * trace - 4.0 * _det2(gram)
    lam_min = 0.5 * (trace - math.sqrt(max(disc, 0.0)))
    if lam_min <= 0.0:
        raise ValueError("singular normal Gram matrix: all bearing lines parallel")
    return 1.0 / math.sqrt(lam_min)


def dilution_verdict(d):
    """Observer-geometry dilution verdict for a factor d (workflow step 6).

    d <= 1.05 is good observer spread, d < 2.5 is moderate and d >= 2.5 is
    poor (near-parallel bearing lines). Raises ValueError for a non-finite
    or negative factor.
    """
    if not math.isfinite(d) or d < 0.0:
        raise ValueError("dilution factor must be finite and non-negative")
    if d <= 1.05:
        return "good observer spread"
    if d < 2.5:
        return "moderate"
    return "poor (near-parallel bearing lines)"


def _los_unit(azimuth_deg, elevation_deg):
    """Unit line of sight from azimuth and elevation in degrees."""
    az = azimuth_deg * DEG2RAD
    el = elevation_deg * DEG2RAD
    cos_el = math.cos(el)
    return (cos_el * math.cos(az), cos_el * math.sin(az), math.sin(el))


def _residual_3d(los, observers_xyz, z):
    """Stacked cross-product residuals e_i = u_i x (z - o_i) and their norm."""
    evec = []
    for (ux, uy, uz), (ox, oy, oz) in zip(los, observers_xyz):
        rx = z[0] - ox
        ry = z[1] - oy
        rz = z[2] - oz
        evec.append(uy * rz - uz * ry)
        evec.append(uz * rx - ux * rz)
        evec.append(ux * ry - uy * rx)
    norm = math.sqrt(sum(v * v for v in evec))
    return evec, norm


def _solve_3x3(aug):
    """Solve a 3x3 linear system by Gaussian elimination with partial pivoting.

    aug is the 3x4 augmented matrix. Returns the solution list [x, y, z]
    and raises ValueError on an exactly zero pivot (singular system).
    """
    m = [row[:] for row in aug]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        if abs(m[pivot][col]) == 0.0:
            raise ValueError("singular 3x3 system in Gauss-Newton step")
        m[col], m[pivot] = m[pivot], m[col]
        pv = m[col][col]
        for row in range(col + 1, 3):
            factor = m[row][col] / pv
            for k in range(col, 4):
                m[row][k] -= factor * m[col][k]
    sol = [0.0, 0.0, 0.0]
    for row in range(2, -1, -1):
        acc = m[row][3] - sum(m[row][k] * sol[k] for k in range(row + 1, 3))
        sol[row] = acc / m[row][row]
    return sol


def refine_3d_gauss_newton(
    observers_xyz,
    azimuths_deg,
    elevations_deg,
    x0,
    y0,
    z0,
    max_iters=_DEFAULT_GN_MAX_ITERS,
    tol=_DEFAULT_GN_TOL,
):
    """Optional three-dimensional Gauss-Newton refinement (workflow step 7).

    Observer i at (xi, yi, zi) measures azimuth (degrees from +x toward +y)
    and elevation (degrees above the horizontal) to the emitter; the unit
    line of sight is u_i = (cos el * cos az, cos el * sin az, sin el). The
    residual is e_i = u_i x (z - o_i) with Jacobian block [u_i]_x and the
    damped normal step (J^T J + mu I) dz = -J^T e, mu = 1e-12 * trace(J^T J)
    / 3, is solved by 3x3 Gaussian elimination with partial pivoting.
    Iterates z <- z + dz until |dz| < tol or max_iters.

    Returns a dict with keys x_m, y_m, z_m, iterations and residual_norm.
    Raises ValueError for fewer than 3 observers, length mismatches,
    max_iters below 1, non-finite inputs, an elevation outside [-90, 90], a
    singular 3x3 system, or no convergence within max_iters.
    """
    n = len(observers_xyz)
    if n < 3:
        raise ValueError("at least three observers are required for 3-D refinement")
    if len(azimuths_deg) != n or len(elevations_deg) != n:
        raise ValueError("azimuth and elevation counts must match the observer count")
    if max_iters < 1:
        raise ValueError("max_iters must be at least 1")
    for (xi, yi, zi) in observers_xyz:
        if not (math.isfinite(xi) and math.isfinite(yi) and math.isfinite(zi)):
            raise ValueError("non-finite observer coordinate")
    for az in azimuths_deg:
        if not math.isfinite(az):
            raise ValueError("non-finite azimuth angle")
    for el in elevations_deg:
        if not math.isfinite(el) or el < -90.0 or el > 90.0:
            raise ValueError("elevation must be finite and within [-90, 90] degrees")
    if not all(math.isfinite(v) for v in (x0, y0, z0)):
        raise ValueError("non-finite starting point")
    z = [float(x0), float(y0), float(z0)]
    los = [_los_unit(az, el) for az, el in zip(azimuths_deg, elevations_deg)]
    for it in range(1, max_iters + 1):
        jtj = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        jte = [0.0, 0.0, 0.0]
        for (ux, uy, uz), (ox, oy, oz) in zip(los, observers_xyz):
            rx = z[0] - ox
            ry = z[1] - oy
            rz = z[2] - oz
            e_i = (uy * rz - uz * ry, uz * rx - ux * rz, ux * ry - uy * rx)
            block = ((0.0, -uz, uy), (uz, 0.0, -ux), (-uy, ux, 0.0))
            for row in range(3):
                jte[row] += sum(block[k][row] * e_i[k] for k in range(3))
                for col in range(3):
                    jtj[row][col] += sum(
                        block[k][row] * block[k][col] for k in range(3)
                    )
        trace = jtj[0][0] + jtj[1][1] + jtj[2][2]
        mu = _GN_MU_FACTOR * trace / 3.0
        for row in range(3):
            jtj[row][row] += mu
        aug = [
            [jtj[0][0], jtj[0][1], jtj[0][2], -jte[0]],
            [jtj[1][0], jtj[1][1], jtj[1][2], -jte[1]],
            [jtj[2][0], jtj[2][1], jtj[2][2], -jte[2]],
        ]
        dz = _solve_3x3(aug)
        z = [z[k] + dz[k] for k in range(3)]
        if math.sqrt(sum(d * d for d in dz)) < tol:
            _, residual_norm = _residual_3d(los, observers_xyz, z)
            return {
                "x_m": z[0],
                "y_m": z[1],
                "z_m": z[2],
                "iterations": it,
                "residual_norm": residual_norm,
            }
    raise ValueError(
        "refine_3d_gauss_newton did not converge within max_iters"
    )

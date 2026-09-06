"""Terrain-referenced navigation logic (gnc-autonomy/navigation).

Aids an unaided inertial navigation solution from terrain with no GNSS
available. Workflow mapping for the contract test:

1. Build the DEM strip: build_dem_strip samples the analytic rolling
   terrain of the TERMS table onto the stored elevation grid that the
   correlator reads (terrain_height exists only to build the strip).
2. Convert the radar-altimeter profile: clearance_profile_to_terrain
   turns each INS-barometric-altitude-minus-radar-clearance sample into
   a measured terrain elevation z_i along the INS indicated track.
3. TERCOM grid correlation: tercom_match resamples the stored DEM along
   every candidate-corrected track, correlates the measured profile with
   each DEM profile through profile_metrics (Pearson r and mean squared
   deviation), and returns the correlation surface plus the best-match
   offset that estimates the INS horizontal position error.
4. Fine SITAN point-mass stage: sitan_point_mass keeps a bank of
   candidate corrections with per-mass vertical-bias Kalman states,
   updates the mass weights from the terrain-height likelihood of each
   epoch measurement, takes the weighted centroid, and applies the
   linearized terrain-slope measurement update (slope row [dh/dx, dh/dy]
   with the unit vertical-bias column) that refines the correction epoch
   by epoch and recovers the vertical bias.

Pure stdlib math only, deterministic, no RNG anywhere.
"""

import math

# ---------------------------------------------------------------------
# DEM strip definition (analytic rolling terrain sampled onto a grid)
# ---------------------------------------------------------------------
DEM_X0 = 3800.0      # strip origin, east (m)
DEM_Y0 = -600.0      # strip origin, north (m)
DEM_D = 25.0         # grid spacing, both axes (m)
DEM_NX = 293         # nodes along east
DEM_NY = 113         # nodes along north
DEM_BASE = 420.0     # base elevation (m MSL)
# (amplitude m, ux, uy, wavelength m, phase rad), h += A sin(2 pi (ux x + uy y)/L + p)
TERMS = [
    (62.0, 1.00, 0.00, 2100.0, 0.55),
    (47.0, 0.00, 1.00, 1500.0, 1.25),
    (30.0, 0.75, 0.66, 2900.0, 0.15),
    (16.0, 0.50, -0.87, 760.0, 0.90),
]
TWO_PI = 2.0 * math.pi

# Filter defaults for the fine SITAN point-mass stage
R_MEAS = 2.25       # radar-altimeter plus DEM measurement variance (m^2)
Q_BIAS = 0.02       # vertical-bias random-walk variance per epoch (m^2)
P0_BIAS = 100.0     # initial per-mass vertical-bias variance (m^2)


def _finite(x):
    """True when x is a finite float-like number."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x))


def terrain_height(x, y):
    """Analytic DEM surface h(x, y) of the TERMS formula (m).

    Used only by the strip builder; the stored grid is the only terrain
    information the correlator ever sees. ValueErrors on non-finite x or y.
    """
    if not _finite(x) or not _finite(y):
        raise ValueError("terrain_height requires finite x and y")
    h = DEM_BASE
    for (a, ux, uy, lam, ph) in TERMS:
        h += a * math.sin(TWO_PI * (ux * x + uy * y) / lam + ph)
    return h


def build_dem_strip():
    """Deterministic DEM_NY rows of DEM_NX heights at the grid nodes.

    Node (jx, jy) stores h at east DEM_X0 + jx * DEM_D, north
    DEM_Y0 + jy * DEM_D. No arguments, no RNG.
    """
    vals = []
    for jy in range(DEM_NY):
        row = []
        for jx in range(DEM_NX):
            row.append(terrain_height(DEM_X0 + jx * DEM_D, DEM_Y0 + jy * DEM_D))
        vals.append(row)
    return vals


def _grid_ok(vals):
    """True when vals is a well-formed strip grid of finite heights."""
    if not isinstance(vals, list) or len(vals) != DEM_NY:
        return False
    for row in vals:
        if not isinstance(row, list) or len(row) != DEM_NX:
            return False
        for v in row:
            if not _finite(v):
                return False
    return True


def dem_height(vals, x, y):
    """Bilinear interpolation of the stored strip at (x, y) (m).

    ValueErrors: malformed grid, non-finite x or y, points outside the
    strip. Bilinear reconstruction is exact for node-aligned points.
    """
    if not _grid_ok(vals):
        raise ValueError("malformed DEM grid")
    return _dem_height_fast(vals, x, y)


def _dem_height_fast(vals, x, y):
    """Grid-validated bilinear sample; O(1), no full-grid rescan."""
    if not _finite(x) or not _finite(y):
        raise ValueError("dem_height requires finite x and y")
    fx = (x - DEM_X0) / DEM_D
    fy = (y - DEM_Y0) / DEM_D
    if fx < 0.0 or fy < 0.0 or fx > DEM_NX - 1.0 or fy > DEM_NY - 1.0:
        raise ValueError("dem_height off strip")
    ix = min(int(fx), DEM_NX - 2)
    iy = min(int(fy), DEM_NY - 2)
    ax = fx - ix
    ay = fy - iy
    h00 = vals[iy][ix]
    h10 = vals[iy][ix + 1]
    h01 = vals[iy + 1][ix]
    h11 = vals[iy + 1][ix + 1]
    return (h00 * (1.0 - ax) + h10 * ax) * (1.0 - ay) + \
        (h01 * (1.0 - ax) + h11 * ax) * ay


def dem_gradient(vals, x, y):
    """Centered-difference slope row (gx, gy) at (x, y), from the grid.

    East and north derivatives use (f[j + 1] - f[j - 1]) / (2 * DEM_D) at
    each node of the cell, bilinearly interpolated to (x, y). ValueErrors
    as dem_height.
    """
    if not _grid_ok(vals):
        raise ValueError("malformed DEM grid")
    return _dem_gradient_fast(vals, x, y)


def _dem_gradient_fast(vals, x, y):
    """Grid-validated centered-difference slope row; O(1)."""
    if not _finite(x) or not _finite(y):
        raise ValueError("dem_gradient requires finite x and y")
    fx = (x - DEM_X0) / DEM_D
    fy = (y - DEM_Y0) / DEM_D
    if fx < 0.0 or fy < 0.0 or fx > DEM_NX - 1.0 or fy > DEM_NY - 1.0:
        raise ValueError("dem_gradient off strip")
    ix = min(int(fx), DEM_NX - 2)
    iy = min(int(fy), DEM_NY - 2)
    ax = fx - ix
    ay = fy - iy
    g00 = ((vals[iy][ix + 1] - vals[iy][ix - 1]) / (2.0 * DEM_D),
           (vals[iy + 1][ix] - vals[iy - 1][ix]) / (2.0 * DEM_D))
    g10 = ((vals[iy][ix + 2] - vals[iy][ix]) / (2.0 * DEM_D),
           (vals[iy + 1][ix + 1] - vals[iy - 1][ix + 1]) / (2.0 * DEM_D))
    g01 = ((vals[iy + 1][ix + 1] - vals[iy + 1][ix - 1]) / (2.0 * DEM_D),
           (vals[iy + 2][ix] - vals[iy][ix]) / (2.0 * DEM_D))
    g11 = ((vals[iy + 1][ix + 2] - vals[iy + 1][ix]) / (2.0 * DEM_D),
           (vals[iy + 2][ix + 1] - vals[iy][ix + 1]) / (2.0 * DEM_D))
    gx = (g00[0] * (1.0 - ax) + g10[0] * ax) * (1.0 - ay) + \
        (g01[0] * (1.0 - ax) + g11[0] * ax) * ay
    gy = (g00[1] * (1.0 - ax) + g10[1] * ax) * (1.0 - ay) + \
        (g01[1] * (1.0 - ax) + g11[1] * ax) * ay
    return (gx, gy)


def clearance_profile_to_terrain(altitude_ins, clearances):
    """Convert a radar-altimeter clearance profile to terrain elevations.

    z_i = altitude_ins - c_i with a scalar INS indicated barometric
    altitude broadcast over the profile, or a per-sample altitude
    sequence of the same length. ValueErrors: empty profile, length
    mismatch, non-finite inputs.
    """
    if clearances is None or len(clearances) == 0:
        raise ValueError("clearance profile is empty")
    scalar = _finite(altitude_ins)
    per_sample = isinstance(altitude_ins, (list, tuple))
    if not scalar and not per_sample:
        raise ValueError("altitude_ins must be a finite scalar or a sequence")
    if per_sample and len(altitude_ins) != len(clearances):
        raise ValueError("altitude and clearance profile length mismatch")
    out = []
    for i, c in enumerate(clearances):
        if not _finite(c):
            raise ValueError("clearance profile holds non-finite values")
        a = altitude_ins if scalar else altitude_ins[i]
        if not _finite(a):
            raise ValueError("altitude holds non-finite values")
        out.append(float(a) - float(c))
    return out


def profile_metrics(measured, predicted):
    """Pearson correlation r and mean squared deviation of two profiles.

    r = covariance(z, d) / (sigma_z * sigma_d), MSD = mean((z - d)^2).
    A zero-variance series returns r = 0.0 (flat guard). ValueErrors:
    length mismatch, fewer than 2 samples, non-finite values.
    """
    if len(measured) != len(predicted):
        raise ValueError("profile length mismatch")
    if len(measured) < 2:
        raise ValueError("profile needs at least 2 samples")
    for z, d in zip(measured, predicted):
        if not _finite(z) or not _finite(d):
            raise ValueError("profile holds non-finite values")
    n = len(measured)
    ma = sum(measured) / n
    mb = sum(predicted) / n
    cov = sum((measured[i] - ma) * (predicted[i] - mb) for i in range(n))
    va = sum((measured[i] - ma) ** 2 for i in range(n))
    vb = sum((predicted[i] - mb) ** 2 for i in range(n))
    if va <= 0.0 or vb <= 0.0:
        r = 0.0
    else:
        r = cov / math.sqrt(va * vb)
    msd = sum((measured[i] - predicted[i]) ** 2 for i in range(n)) / n
    return (r, msd)


def tercom_match(vals, measured, x_ind, y_ind, dxs, dys):
    """TERCOM grid correlation of the measured profile against the strip.

    For every candidate offset (dx, dy) the stored DEM is resampled along
    the candidate-corrected INS track (x_ind_i - dx, y_ind_i - dy) and
    correlated with the measured profile by profile_metrics. Returns the
    full correlation surface plus the argmax-r best-match offset that
    estimates the INS horizontal position error e = (e_east, e_north).

    Return keys: dxs, dys, r_rows and msd_rows (one row per dy, one value
    per dx), r_best, dx_best, dy_best, msd_best (MSD at the argmax-r
    cell). ValueErrors: empty dxs or dys, profile length mismatch with
    x_ind/y_ind, non-finite inputs, off-strip sampling propagated from
    dem_height.
    """
    if dxs is None or len(dxs) == 0:
        raise ValueError("dxs candidate grid is empty")
    if dys is None or len(dys) == 0:
        raise ValueError("dys candidate grid is empty")
    if not (len(measured) == len(x_ind) == len(y_ind)):
        raise ValueError("profile length mismatch with the indicated track")
    if not _grid_ok(vals):
        raise ValueError("malformed DEM grid")
    for z in measured:
        if not _finite(z):
            raise ValueError("measured profile holds non-finite values")
    for xv, yv in zip(x_ind, y_ind):
        if not _finite(xv) or not _finite(yv):
            raise ValueError("indicated track holds non-finite values")
    r_rows = []
    msd_rows = []
    for dy in dys:
        r_row = []
        msd_row = []
        for dx in dxs:
            d = [_dem_height_fast(vals, x_ind[i] - dx, y_ind[i] - dy)
                 for i in range(len(x_ind))]
            (r, msd) = profile_metrics(measured, d)
            r_row.append(r)
            msd_row.append(msd)
        r_rows.append(r_row)
        msd_rows.append(msd_row)
    best = None
    for j in range(len(dys)):
        for i in range(len(dxs)):
            if best is None or r_rows[j][i] > best[0]:
                best = (r_rows[j][i], dxs[i], dys[j])
    r_best, dx_best, dy_best = best
    msd_best = None
    for j in range(len(dys)):
        for i in range(len(dxs)):
            if dxs[i] == dx_best and dys[j] == dy_best:
                msd_best = msd_rows[j][i]
    return {
        "dxs": list(dxs),
        "dys": list(dys),
        "r_rows": r_rows,
        "msd_rows": msd_rows,
        "r_best": r_best,
        "dx_best": dx_best,
        "dy_best": dy_best,
        "msd_best": msd_best,
    }


def sitan_point_mass(vals, profile, x_ind, y_ind, dr0, indices,
                     half=6, spacing=10.0, r_meas=R_MEAS,
                     q_bias=Q_BIAS, p0_bias=P0_BIAS):
    """Fine SITAN point-mass stage with the linearized terrain-slope update.

    dr is ADDED to the INS indicated position (p_corrected = p_ind + dr),
    so a hypothesis dr_k evaluates the DEM at (x_ind_i + dr_k_e,
    y_ind_i + dr_k_n). A bank of (2 * half + 1)^2 candidate corrections
    at spacing around dr0 covers the one-grid-step coarse residual. Each
    mass k carries a scalar vertical-bias Kalman state; per epoch the
    mass weights update from the terrain-height likelihood of the epoch
    measurement and the weighted centroid feeds a linearized terrain-
    slope measurement update (H = [dh/dx, dh/dy, 1.0], the slope row from
    central differences of the stored grid with the unit vertical-bias
    column) on the 3 by 3 centroid covariance of (east correction, north
    correction, vertical bias).

    Returns epochs, a list of per-epoch dicts (dr_e, dr_n, bias, sigma_e,
    sigma_n, slope_e, slope_n, innovation, innovation_variance, gain
    (3-tuple), weight_max, weight_entropy), and final (dr_e, dr_n, bias)
    with the covariance diagonal. ValueErrors: empty indices, spacing
    <= 0, half < 0, r_meas <= 0, q_bias < 0, p0_bias <= 0, non-finite
    inputs, off-strip sampling.
    """
    if indices is None or len(indices) == 0:
        raise ValueError("epoch indices are empty")
    if spacing <= 0.0:
        raise ValueError("spacing must be positive")
    if half < 0:
        raise ValueError("half must be non-negative")
    if r_meas <= 0.0:
        raise ValueError("r_meas must be positive")
    if q_bias < 0.0:
        raise ValueError("q_bias must be non-negative")
    if p0_bias <= 0.0:
        raise ValueError("p0_bias must be positive")
    if not isinstance(dr0, (list, tuple)) or len(dr0) != 2:
        raise ValueError("dr0 must be the (east, north) correction pair")
    if not _finite(dr0[0]) or not _finite(dr0[1]):
        raise ValueError("dr0 holds non-finite values")
    n_samples = len(profile)
    if not (n_samples == len(x_ind) == len(y_ind)):
        raise ValueError("profile length mismatch with the indicated track")
    if max(indices) >= n_samples:
        raise ValueError("epoch index outside the profile window")
    if not _grid_ok(vals):
        raise ValueError("malformed DEM grid")
    for z in profile:
        if not _finite(z):
            raise ValueError("profile holds non-finite values")
    for xv, yv in zip(x_ind, y_ind):
        if not _finite(xv) or not _finite(yv):
            raise ValueError("indicated track holds non-finite values")

    bank = []
    for i in range(-half, half + 1):
        for j in range(-half, half + 1):
            bank.append([dr0[0] + spacing * i, dr0[1] + spacing * j])
    nk = len(bank)
    w = [1.0 / nk] * nk
    logw = [0.0] * nk
    bias = [0.0] * nk
    pb = [p0_bias] * nk

    epochs = []
    for epoch in range(len(indices)):
        idx = indices[epoch]
        zi = profile[idx]
        xi = x_ind[idx]
        yi = y_ind[idx]
        # per-mass likelihood update and scalar vertical-bias Kalman state
        for k in range(nk):
            hk = _dem_height_fast(vals, xi + bank[k][0], yi + bank[k][1])
            yk = zi - hk - bias[k]
            sk = pb[k] + r_meas
            kk = pb[k] / sk
            bias[k] += kk * yk
            pb[k] = (1.0 - kk) * pb[k] + q_bias
            logw[k] += -0.5 * (yk * yk / sk + math.log(TWO_PI * sk))
        mw = max(logw)
        wsum = 0.0
        for k in range(nk):
            w[k] = math.exp(logw[k] - mw)
            wsum += w[k]
        for k in range(nk):
            w[k] /= wsum
        # weighted centroid and the 3 by 3 weighted covariance
        ce = sum(w[k] * bank[k][0] for k in range(nk))
        cn = sum(w[k] * bank[k][1] for k in range(nk))
        cb = sum(w[k] * bias[k] for k in range(nk))
        var_e = sum(w[k] * (bank[k][0] - ce) ** 2 for k in range(nk))
        var_n = sum(w[k] * (bank[k][1] - cn) ** 2 for k in range(nk))
        var_b = sum(w[k] * (bias[k] - cb) ** 2 for k in range(nk))
        var_en = sum(w[k] * (bank[k][0] - ce) * (bank[k][1] - cn) for k in range(nk))
        var_eb = sum(w[k] * (bank[k][0] - ce) * (bias[k] - cb) for k in range(nk))
        var_nb = sum(w[k] * (bank[k][1] - cn) * (bias[k] - cb) for k in range(nk))
        # linearized terrain-slope measurement update at the centroid
        px = xi + ce
        py = yi + cn
        h0 = _dem_height_fast(vals, px, py)
        (ge, gn) = _dem_gradient_fast(vals, px, py)
        yc = zi - h0 - cb
        pc = [[var_e, var_en, var_eb],
              [var_en, var_n, var_nb],
              [var_eb, var_nb, var_b]]
        hrow = [ge, gn, 1.0]
        s = (hrow[0] * (pc[0][0] * hrow[0] + pc[0][1] * hrow[1] + pc[0][2] * hrow[2]) +
             hrow[1] * (pc[1][0] * hrow[0] + pc[1][1] * hrow[1] + pc[1][2] * hrow[2]) +
             hrow[2] * (pc[2][0] * hrow[0] + pc[2][1] * hrow[1] + pc[2][2] * hrow[2])) + r_meas
        k3 = [0.0, 0.0, 0.0]
        for r in range(3):
            k3[r] = (pc[r][0] * hrow[0] + pc[r][1] * hrow[1] + pc[r][2] * hrow[2]) / s
        ce += k3[0] * yc
        cn += k3[1] * yc
        cb += k3[2] * yc
        npc = [[0.0] * 3 for _ in range(3)]
        for r in range(3):
            for c in range(3):
                val = pc[r][c]
                for t in range(3):
                    val -= k3[r] * hrow[t] * pc[t][c]
                npc[r][c] = val
        ent = -sum(wk * math.log(wk) for wk in w if wk > 0.0)
        epochs.append({
            "dr_e": ce,
            "dr_n": cn,
            "bias": cb,
            "sigma_e": math.sqrt(max(npc[0][0], 0.0)),
            "sigma_n": math.sqrt(max(npc[1][1], 0.0)),
            "slope_e": ge,
            "slope_n": gn,
            "innovation": yc,
            "innovation_variance": s,
            "gain": (k3[0], k3[1], k3[2]),
            "weight_max": max(w),
            "weight_entropy": ent,
        })
    final = {
        "dr_e": ce,
        "dr_n": cn,
        "bias": cb,
        "sigma_e": math.sqrt(max(npc[0][0], 0.0)),
        "sigma_n": math.sqrt(max(npc[1][1], 0.0)),
        "sigma_bias": math.sqrt(max(npc[2][2], 0.0)),
    }
    return {"epochs": epochs, "final": final}

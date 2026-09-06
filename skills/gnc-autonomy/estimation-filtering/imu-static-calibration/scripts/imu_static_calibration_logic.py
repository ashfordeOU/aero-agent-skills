"""imu_static_calibration_logic.py

Static calibration of an IMU from laboratory test data: the
six-position accelerometer calibration and the rate-table gyro
calibration. Pure stdlib (math and random only), deterministic for a
fixed seed.

Measurement model of a static hold: m_k = b + A*(f_k*G0), where f_k is
the hold direction from the pinned fixture POSITIONS (in g units), b
the bias vector in m/s^2 and A the dimensionless 3x3 sensitivity matrix
whose diagonal entries A_ii = s_i are the scale factors and whose
off-diagonal entries are the cross-axis (misalignment) sensitivities.

Pair reduction per axis i: with plus = means[2*i][i] and minus =
means[2*i+1][i], the +g and -g hold means of channel i, the scale
factor is s_i = (plus - minus)/(2*G0) and the bias b_i = (plus + minus)
/2 in m/s^2.

Least-squares fit over all six positions: for each output channel c the
design rows (f_k[0]*G0, f_k[1]*G0, f_k[2]*G0, 1) over the six holds are
regressed through the normal equations (X^T X) q = X^T y solved by
Gaussian elimination with partial pivoting; the coefficient triple is
row c of A and the fourth coefficient is bias_c.

Rate-table regression per axis: measured_rate = s*commanded_rate + b,
so the ordinary least-squares slope over the commanded rates is the
dimensionless scale factor and the intercept is the gyro bias in deg/s.
"""

import math
import random

# Standard gravity in m/s^2, used to convert the 1 g fixture references
# into specific-force units.
G0 = 9.80665

# Pinned fixture order: the +g hold of axis i sits at index 2*i and the
# -g hold at 2*i+1, in the order +x, -x, +y, -y, +z, -z (g units).
POSITIONS = (
    (1, 0, 0),
    (-1, 0, 0),
    (0, 1, 0),
    (0, -1, 0),
    (0, 0, 1),
    (0, 0, -1),
)


def _check_3vec(v, name):
    """Finite/width guard: v must be a 3-vector of finite numbers."""
    if not isinstance(v, (tuple, list)):
        raise ValueError("%s must be a 3-vector" % name)
    if len(v) != 3:
        raise ValueError("%s must be a 3-vector of length 3" % name)
    out = []
    for x in v:
        if not isinstance(x, (int, float)):
            raise ValueError("%s must hold finite numbers" % name)
        fx = float(x)
        if not math.isfinite(fx):
            raise ValueError("%s must hold finite numbers" % name)
        out.append(fx)
    return tuple(out)


def _check_matrix3(m, name):
    """Finite/width guard: m must be a 3x3 matrix of finite numbers."""
    if not isinstance(m, (tuple, list)) or len(m) != 3:
        raise ValueError("%s must be a 3x3 matrix" % name)
    rows = []
    for row in m:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            raise ValueError("%s must hold 3x3 finite numbers" % name)
        vals = []
        for x in row:
            if not isinstance(x, (int, float)):
                raise ValueError("%s must hold finite numbers" % name)
            fx = float(x)
            if not math.isfinite(fx):
                raise ValueError("%s must hold finite numbers" % name)
            vals.append(fx)
        rows.append(tuple(vals))
    return tuple(rows)


def _check_sigma(sigma):
    """Guard: sigma must be a finite non-negative number."""
    if not isinstance(sigma, (int, float)):
        raise ValueError("sigma must be a finite non-negative number")
    fs = float(sigma)
    if not math.isfinite(fs) or fs < 0.0:
        raise ValueError("sigma must be a finite non-negative number")


def _check_means(means):
    """Guard: exactly six static holds of three finite numbers each."""
    if not isinstance(means, (tuple, list)):
        raise ValueError("means must be exactly 6 holds of 3 finite numbers")
    if len(means) != 6:
        raise ValueError("means must be exactly 6 holds of 3 finite numbers")
    out = []
    for row in means:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            raise ValueError("means must be exactly 6 holds of 3 finite numbers")
        vals = []
        for x in row:
            if not isinstance(x, (int, float)):
                raise ValueError("means must hold finite numbers")
            fx = float(x)
            if not math.isfinite(fx):
                raise ValueError("means must hold finite numbers")
            vals.append(fx)
        out.append(tuple(vals))
    return tuple(out)


def _check_commanded_axes(commanded_by_axis):
    """Guard: three axes, each holding at least 2 finite commanded rates."""
    if not isinstance(commanded_by_axis, (tuple, list)):
        raise ValueError("commanded_by_axis must cover 3 axes")
    if len(commanded_by_axis) != 3:
        raise ValueError("commanded_by_axis must cover 3 axes")
    axes = []
    for axis in commanded_by_axis:
        if not isinstance(axis, (tuple, list)):
            raise ValueError("each axis must hold at least 2 commanded rates")
        if len(axis) < 2:
            raise ValueError("each axis must hold at least 2 commanded rates")
        rates = []
        for r in axis:
            if not isinstance(r, (int, float)) or not math.isfinite(float(r)):
                raise ValueError("commanded rates must be finite")
            rates.append(float(r))
        axes.append(tuple(rates))
    return tuple(axes)


def simulate_six_position_means(bias, scale, misalignment=None, sigma=0.0, seed=7):
    """Simulate the six-position static-hold campaign (workflow step 1).

    Returns the tuple of six hold mean specific forces in m/s^2 in the
    +x, -x, +y, -y, +z, -z fixture order. Each hold channel follows the
    model m_k = b + A*(f_k*G0) plus Gaussian noise of standard
    deviation sigma (m/s^2); A is diag(scale) with the off-diagonal
    truth taken from misalignment. Deterministic and bit-reproducible
    for a fixed seed via random.Random(seed).
    """
    b = _check_3vec(bias, "bias")
    s = _check_3vec(scale, "scale")
    for entry in s:
        if entry <= 0.0:
            raise ValueError("scale factors must all be positive")
    if misalignment is None:
        a_rows = [[0.0, 0.0, 0.0] for _ in range(3)]
    else:
        a_rows = [list(row) for row in _check_matrix3(misalignment, "misalignment")]
    for i in range(3):
        a_rows[i][i] = s[i]
    _check_sigma(sigma)
    rng = random.Random(seed)
    holds = []
    for fk in POSITIONS:
        base = [
            b[c] + a_rows[c][0] * fk[0] * G0 + a_rows[c][1] * fk[1] * G0
            + a_rows[c][2] * fk[2] * G0
            for c in range(3)
        ]
        holds.append(tuple(x + rng.gauss(0.0, sigma) for x in base))
    return tuple(holds)


def fit_accel_pair_bias_scale(means):
    """Pair reduction of the six-position holds (workflow step 2).

    For each axis i the +g hold mean plus = means[2*i][i] and the -g
    hold mean minus = means[2*i+1][i] give the scale factor s_i =
    (plus - minus)/(2*G0) and the bias b_i = (plus + minus)/2 in m/s^2.
    The diagonal model predicts channel i of hold k as b_i +
    s_i*f_k[i]*G0; its residual rms over all 18 measurements carries the
    cross-axis leakage the diagonal model cannot absorb.
    """
    holds = _check_means(means)
    bias = []
    scale = []
    for i in range(3):
        plus = holds[2 * i][i]
        minus = holds[2 * i + 1][i]
        scale.append((plus - minus) / (2.0 * G0))
        bias.append((plus + minus) / 2.0)
    residuals = []
    for k, fk in enumerate(POSITIONS):
        for c in range(3):
            pred = bias[c] + scale[c] * fk[c] * G0
            residuals.append(holds[k][c] - pred)
    rms = math.sqrt(sum(r * r for r in residuals) / len(residuals))
    return {"bias": tuple(bias), "scale": tuple(scale), "rms_residual": rms}


def fit_accel_misalignment_ls(means):
    """Least-squares fit of the scale-plus-misalignment matrix
    (workflow step 3).

    For each output channel c the design rows (f_k[0]*G0, f_k[1]*G0,
    f_k[2]*G0, 1) over the six holds are regressed on the hold means
    through ols_fit; the coefficient triple is row c of the
    dimensionless sensitivity matrix A and the fourth coefficient is
    bias_c in m/s^2. Reports the residual rms over all 18 measurements,
    which drops below the pair-model rms once the off-diagonal terms
    absorb the cross-axis leakage.
    """
    holds = _check_means(means)
    design = [tuple(fk[j] * G0 for j in range(3)) + (1.0,) for fk in POSITIONS]
    matrix_rows = []
    bias = []
    for c in range(3):
        y = [holds[k][c] for k in range(6)]
        q = ols_fit(design, y)
        matrix_rows.append(q[0:3])
        bias.append(q[3])
    residuals = []
    for k, fk in enumerate(POSITIONS):
        for c in range(3):
            pred = bias[c]
            for j in range(3):
                pred += matrix_rows[c][j] * fk[j] * G0
            residuals.append(holds[k][c] - pred)
    rms = math.sqrt(sum(r * r for r in residuals) / len(residuals))
    return {
        "matrix": tuple(tuple(r) for r in matrix_rows),
        "bias": tuple(bias),
        "rms_residual": rms,
    }


def simulate_rate_table(commanded_by_axis, bias, scale, sigma=0.0, seed=7):
    """Simulate the rate-table gyro runs (workflow step 4).

    For each body axis the measured gyro rate (deg/s) at each commanded
    rate follows measured = scale*commanded + bias plus Gaussian noise
    of standard deviation sigma (deg/s). Returns a tuple of three
    measured-rate tuples. Deterministic and bit-reproducible for a
    fixed seed via random.Random(seed).
    """
    cmd = _check_commanded_axes(commanded_by_axis)
    b = _check_3vec(bias, "bias")
    s = _check_3vec(scale, "scale")
    for entry in s:
        if entry <= 0.0:
            raise ValueError("scale factors must all be positive")
    _check_sigma(sigma)
    rng = random.Random(seed)
    measured = []
    for a in range(3):
        row = tuple(s[a] * r + b[a] + rng.gauss(0.0, sigma) for r in cmd[a])
        measured.append(row)
    return tuple(measured)


def fit_gyro_rate_table(measured_by_axis, commanded_by_axis):
    """Rate-table regression of each gyro axis (workflow step 5).

    Ordinary least squares of measured_rate on commanded_rate per axis
    through ols_fit: the slope is the dimensionless scale factor and
    the intercept the gyro bias in deg/s. Reports the per-axis residual
    rms (deg/s) against the fitted line.
    """
    if not isinstance(commanded_by_axis, (tuple, list)) or len(commanded_by_axis) != 3:
        raise ValueError("commanded_by_axis must cover 3 axes")
    if not isinstance(measured_by_axis, (tuple, list)) or len(measured_by_axis) != 3:
        raise ValueError("measured_by_axis must cover 3 axes")
    cmd_rows = []
    meas_rows = []
    for a in range(3):
        ca = commanded_by_axis[a]
        ma = measured_by_axis[a]
        if not isinstance(ca, (tuple, list)) or not isinstance(ma, (tuple, list)):
            raise ValueError("each axis must hold a list of rates")
        if len(ca) != len(ma):
            raise ValueError("measured and commanded lists must agree in length per axis")
        if len(ca) < 2:
            raise ValueError("each axis needs at least 2 samples")
        cr = []
        for r in ca:
            if not isinstance(r, (int, float)) or not math.isfinite(float(r)):
                raise ValueError("commanded rates must be finite")
            cr.append(float(r))
        mr = []
        for v in ma:
            if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
                raise ValueError("measured rates must be finite")
            mr.append(float(v))
        cmd_rows.append(cr)
        meas_rows.append(mr)
    bias = []
    scale = []
    rms_per_axis = []
    for a in range(3):
        design = [(r, 1.0) for r in cmd_rows[a]]
        q = ols_fit(design, meas_rows[a])
        scale.append(q[0])
        bias.append(q[1])
        residuals = [
            meas_rows[a][i] - (q[0] * cmd_rows[a][i] + q[1])
            for i in range(len(cmd_rows[a]))
        ]
        rms_per_axis.append(
            math.sqrt(sum(r * r for r in residuals) / len(residuals))
        )
    return {
        "bias": tuple(bias),
        "scale": tuple(scale),
        "rms_per_axis": tuple(rms_per_axis),
    }


def ols_fit(design_rows, y):
    """Ordinary least squares through the normal equations
    (X^T X) q = X^T y solved by Gaussian elimination with partial
    pivoting. Shared by the misalignment fit and the gyro regression.
    """
    if not isinstance(design_rows, (tuple, list)) or len(design_rows) == 0:
        raise ValueError("design_rows must be a non-empty list of rows")
    if not isinstance(y, (tuple, list)) or len(y) != len(design_rows):
        raise ValueError("design rows and y must have equal length")
    first = design_rows[0]
    if not isinstance(first, (tuple, list)) or len(first) == 0:
        raise ValueError("each design row must be a non-empty vector")
    ncols = len(first)
    for v in first:
        if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            raise ValueError("design entries must be finite")
    for row in design_rows[1:]:
        if not isinstance(row, (tuple, list)) or len(row) == 0:
            raise ValueError("each design row must be a non-empty vector")
        if len(row) != ncols:
            raise ValueError("design row widths must be consistent")
        for v in row:
            if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
                raise ValueError("design entries must be finite")
    for v in y:
        if not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            raise ValueError("y must hold finite numbers")
    xtx = [[0.0] * ncols for _ in range(ncols)]
    xty = [0.0] * ncols
    for k, row in enumerate(design_rows):
        yk = float(y[k])
        for i in range(ncols):
            xi = float(row[i])
            xty[i] += xi * yk
            for j in range(ncols):
                xtx[i][j] += xi * float(row[j])
    return _solve_linear_system(xtx, xty)


def _solve_linear_system(a, y):
    """Solve the square system a x = y by Gaussian elimination with
    partial pivoting; ValueError on a singular matrix."""
    n = len(a)
    if n == 0 or len(a[0]) != n or len(y) != n:
        raise ValueError("a must be a square matrix matching y")
    scale = 1.0
    for i in range(n):
        for j in range(n):
            scale = max(scale, abs(a[i][j]))
    aug = []
    for i in range(n):
        aug.append([float(x) for x in a[i]] + [float(y[i])])
    tol = 1e-12 * scale
    for col in range(n):
        piv = col
        for r in range(col + 1, n):
            if abs(aug[r][col]) > abs(aug[piv][col]):
                piv = r
        if abs(aug[piv][col]) <= tol:
            raise ValueError("normal matrix is singular")
        if piv != col:
            aug[col], aug[piv] = aug[piv], aug[col]
        pv = aug[col][col]
        for r in range(col + 1, n):
            factor = aug[r][col] / pv
            if factor == 0.0:
                continue
            for c in range(col, n + 1):
                aug[r][c] -= factor * aug[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = aug[i][n]
        for j in range(i + 1, n):
            s -= aug[i][j] * x[j]
        x[i] = s / aug[i][i]
    return tuple(x)

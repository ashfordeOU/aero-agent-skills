"""Explicit (Mahony-style) complementary filter on SO(3) for attitude estimation.

Pure stdlib implementation of an explicit complementary filter that fuses a
high-rate rate gyro with low-rate absolute vector measurements (sun sensor,
magnetometer) into a continuous spacecraft or aircraft attitude estimate
with online gyro bias estimation.

Conventions (documented, used consistently everywhere):
- Quaternions are unit norm, scalar first: q = [w, x, y, z].
- q maps reference-frame vectors into body-frame vectors:
  v_body = R(q) * v_ref, with R(q) the active rotation matrix.
- The gyro angular rate omega is expressed in the body frame (rad/s).
- Kinematics: q_dot = 0.5 * q (x) [0, omega], quaternion multiplication
  form of the body-frame rate equation.
- Per vector pair the estimated body vector is v_i = R(q_est) * r_i and
  the measurement error is e_i = m_i x v_i (cross product, small-angle
  attitude error in the body frame). The total error is the sum over all
  pairs present at the step.
- Corrected rate: omega_c = omega_m - b_est + k_p * sum(e_i).
- Bias dynamics: b_dot = -k_i * sum(e_i), integrated explicitly with dt.
- Attitude propagation uses RK4 on the quaternion kinematics with the
  step-correction rate held constant over the step, then renormalizes q.

ValueError is raised for dt <= 0, negative gains, non-finite inputs,
malformed vector or quaternion shapes, and initial quaternions that are
not unit norm beyond the 1e-6 tolerance (within tolerance: normalized).

Mahony, R., Hamel, T., and Pflimlin, J.-M., "Nonlinear Complementary
Filters on the Special Orthogonal Group", IEEE TAC 53(5), 2008, frames
the correction structure; this module implements the standard explicit
form with the engineering constants above. SI units throughout.
"""

import math

# Module constants (engineering defaults, all SI).
KP_DEFAULT = 2.0       # proportional gain, 1/s
KI_DEFAULT = 0.4       # integral gain, 1/s^2 (bias estimate rate gain)
Q0_NORM_TOL = 1e-6     # accepted deviation of a unit initial quaternion
NORM_EPS = 1e-12       # floor to avoid division by a zero norm


def _finite(value, name):
    if not isinstance(value, (int, float)):
        raise ValueError("%s must be a finite number" % name)
    if not math.isfinite(float(value)):
        raise ValueError("%s must be finite" % name)
    return float(value)


def _vec3(v, name):
    try:
        vals = list(v)
    except TypeError:
        raise ValueError("%s must be a 3-vector" % name) from None
    if len(vals) != 3:
        raise ValueError("%s must have length 3, got %d" % (name, len(vals)))
    return [_finite(x, name) for x in vals]


def _quat(q, name="q"):
    try:
        vals = list(q)
    except TypeError:
        raise ValueError("%s must be a quaternion of length 4" % name) from None
    if len(vals) != 4:
        raise ValueError(
            "%s must have length 4, got %d" % (name, len(vals)))
    return [_finite(x, name) for x in vals]


def _as_error_vectors(errors, name="errors"):
    """Return errors as a list of 3-vectors; accept one 3-vector or a list."""
    if errors is None:
        return []
    flat = list(errors)
    if len(flat) == 3 and all(
            isinstance(x, (int, float)) for x in flat):
        return [_vec3(flat, name)]
    out = []
    for entry in flat:
        out.append(_vec3(entry, name))
    return out


def _error_total(errors):
    total = [0.0, 0.0, 0.0]
    for e in _as_error_vectors(errors):
        total[0] += e[0]
        total[1] += e[1]
        total[2] += e[2]
    return total


def _vec3_add(a, b):
    return [a[0] + b[0], a[1] + b[1], a[2] + b[2]]


def _vec3_scale(a, s):
    return [a[0] * s, a[1] * s, a[2] * s]


def _vec3_norm(a):
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def _vec3_cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def quat_normalize(q):
    """Normalize a quaternion to unit norm.

    Raises ValueError on non-finite entries or a zero norm.
    """
    vals = _quat(q)
    norm = math.sqrt(sum(x * x for x in vals))
    if norm <= NORM_EPS:
        raise ValueError("quat_normalize: zero-norm quaternion cannot be normalized")
    return [x / norm for x in vals]


def quat_multiply(q1, q2):
    """Hamilton product q1 (x) q2 of two quaternions (scalar first)."""
    a = _quat(q1, "q1")
    b = _quat(q2, "q2")
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return [w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
            w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2]


def quat_to_rotation_matrix(q):
    """Active rotation matrix R(q) with v_body = R(q) * v_ref.

    The input is normalized first so any unit-length quaternion (or a
    near-unit one) maps to a proper rotation with R R^T = I.
    """
    w, x, y, z = quat_normalize(q)
    return [[1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - w * z),
             2.0 * (x * z + w * y)],
            [2.0 * (x * y + w * z), 1.0 - 2.0 * (x * x + z * z),
             2.0 * (y * z - w * x)],
            [2.0 * (x * z - w * y), 2.0 * (y * z + w * x),
             1.0 - 2.0 * (x * x + y * y)]]


def rotate_reference_vector(q, r):
    """Estimated body-frame vector v = R(q)^T * r for reference vector r.

    R(q) is the active rotation matrix (quat_to_rotation_matrix), so the
    body-frame prediction of a reference-frame vector is obtained with
    the inverse rotation, R(q)^T r (equivalently the conjugate
    quaternion). With q equal to the true attitude this reproduces the
    body measurement exactly, which is the consistency condition of the
    explicit complementary filter.
    """
    rot = quat_to_rotation_matrix(q)
    rv = _vec3(r, "r")
    return [rot[0][0] * rv[0] + rot[1][0] * rv[1] + rot[2][0] * rv[2],
            rot[0][1] * rv[0] + rot[1][1] * rv[1] + rot[2][1] * rv[2],
            rot[0][2] * rv[0] + rot[1][2] * rv[1] + rot[2][2] * rv[2]]


def vector_measurement_error(m, v):
    """Cross-product error e = m x v between a body measurement and the
    estimated body vector (small-angle attitude error, body frame)."""
    mv = _vec3(m, "m")
    vv = _vec3(v, "v")
    return _vec3_cross(mv, vv)


def correction_step(errors, k_p):
    """Proportional rate correction k_p * sum(errors).

    errors may be a single 3-vector or a list of 3-vectors; an empty list
    yields the zero correction (gyro-only propagation).
    """
    gain = _finite(k_p, "k_p")
    if gain < 0.0:
        raise ValueError("correction_step: k_p must be >= 0, got %r" % (k_p,))
    return _vec3_scale(_error_total(errors), gain)


def bias_update(b_est, errors, k_i, dt):
    """One explicit bias step: b_new = b_est - k_i * sum(errors) * dt."""
    b = _vec3(b_est, "b_est")
    gain = _finite(k_i, "k_i")
    if gain < 0.0:
        raise ValueError("bias_update: k_i must be >= 0, got %r" % (k_i,))
    step = _finite(dt, "dt")
    if step <= 0.0:
        raise ValueError("bias_update: dt must be > 0, got %r" % (dt,))
    total = _error_total(errors)
    return [b[i] - gain * total[i] * step for i in range(3)]


def gyro_compensated_rate(omega_m, b_est, k_p, errors):
    """Corrected body rate omega_c = omega_m - b_est + k_p * sum(errors)."""
    om = _vec3(omega_m, "omega_m")
    b = _vec3(b_est, "b_est")
    corr = correction_step(errors, k_p)
    return [om[0] - b[0] + corr[0],
            om[1] - b[1] + corr[1],
            om[2] - b[2] + corr[2]]


def quat_kinematics(q, omega_c):
    """q_dot = 0.5 * q (x) [0, omega_c] with the rate in the body frame."""
    qv = _quat(q)
    w = _vec3(omega_c, "omega_c")
    prod = quat_multiply(qv, [0.0, w[0], w[1], w[2]])
    return [0.5 * x for x in prod]


def propagate_attitude(q, omega_m, b_est, errors, k_p, k_i, dt):
    """One explicit complementary filter step.

    Corrected rate from the current errors and bias, RK4 integration of
    the quaternion kinematics with that rate held over the step,
    renormalization of q, then the explicit bias update.

    Returns (q_new, b_new).
    """
    qv = _quat(q)
    om = _vec3(omega_m, "omega_m")
    b = _vec3(b_est, "b_est")
    gain_p = _finite(k_p, "k_p")
    if gain_p < 0.0:
        raise ValueError("propagate_attitude: k_p must be >= 0, got %r" % (k_p,))
    gain_i = _finite(k_i, "k_i")
    if gain_i < 0.0:
        raise ValueError("propagate_attitude: k_i must be >= 0, got %r" % (k_i,))
    step = _finite(dt, "dt")
    if step <= 0.0:
        raise ValueError("propagate_attitude: dt must be > 0, got %r" % (dt,))
    total = _error_total(errors)
    omega_c = [om[0] - b[0] + gain_p * total[0],
               om[1] - b[1] + gain_p * total[1],
               om[2] - b[2] + gain_p * total[2]]

    def f(state):
        return quat_kinematics(state, omega_c)

    half = 0.5 * step
    k1 = f(qv)
    k2 = f([qv[i] + half * k1[i] for i in range(4)])
    k3 = f([qv[i] + half * k2[i] for i in range(4)])
    k4 = f([qv[i] + step * k3[i] for i in range(4)])
    sixth = step / 6.0
    q_new = [qv[i] + sixth * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])
             for i in range(4)]
    q_new = quat_normalize(q_new)
    b_new = [b[i] - gain_i * total[i] * step for i in range(3)]
    return q_new, b_new


def _normalize_measurement_steps(measurement_samples, n_steps):
    """Turn measurement_samples into one list of vector pairs per step."""
    if measurement_samples is None:
        return [[] for _ in range(n_steps)]
    try:
        steps = list(measurement_samples)
    except TypeError:
        raise ValueError(
            "measurement_samples must be None or a per-step sequence") from None
    if len(steps) != n_steps:
        raise ValueError(
            "measurement_samples has %d entries for %d gyro steps"
            % (len(steps), n_steps))
    out = []
    for entry in steps:
        if entry is None:
            out.append([])
            continue
        try:
            items = list(entry)
        except TypeError:
            raise ValueError(
                "each measurement entry must be None, one (r, m) pair, "
                "or a list of (r, m) pairs") from None
        if len(items) == 0:
            out.append([])
            continue
        single = (len(items) == 2
                  and all(isinstance(x, (list, tuple)) and len(x) == 3
                          for x in items))
        if single:
            pairs = [tuple(items)]
        else:
            pairs = []
            for item in items:
                try:
                    pair = tuple(item)
                except TypeError:
                    raise ValueError(
                        "measurement pair must be (r, m)") from None
                if len(pair) != 2:
                    raise ValueError(
                        "measurement pair must contain reference and "
                        "measured vectors")
                pairs.append(pair)
        checked = []
        for r, m in pairs:
            checked.append((_vec3(r, "r"), _vec3(m, "m")))
        out.append(checked)
    return out


def run_complementary_filter(q0, b0, omega_samples, measurement_samples,
                             k_p, k_i, dt):
    """Run the explicit complementary filter over a sample sequence.

    q0: initial unit quaternion (normalized if within 1e-6 of unit norm,
    ValueError otherwise). b0: initial bias estimate, 3-vector.
    omega_samples: one measured body rate 3-vector per step (gyro runs
    every step). measurement_samples: None for gyro-only propagation, or
    one entry per step: None, a single (r, m) reference/measured pair, or
    a list of such pairs. k_p, k_i: correction gains; dt: fixed step, s.

    Returns (estimates, innovation_norms): estimates[k] = (q, b) after
    step k and innovation_norms[k] = norm of the total cross-product
    error used at step k (0 when no vector measurement was present).
    """
    q = _quat(q0, "q0")
    norm = math.sqrt(sum(x * x for x in q))
    if abs(norm - 1.0) > Q0_NORM_TOL:
        raise ValueError(
            "run_complementary_filter: q0 is not unit norm "
            "(|q0| = %r)" % norm)
    q = [x / norm for x in q]
    b = _vec3(b0, "b0")
    gain_p = _finite(k_p, "k_p")
    if gain_p < 0.0:
        raise ValueError(
            "run_complementary_filter: k_p must be >= 0, got %r" % (k_p,))
    gain_i = _finite(k_i, "k_i")
    if gain_i < 0.0:
        raise ValueError(
            "run_complementary_filter: k_i must be >= 0, got %r" % (k_i,))
    step = _finite(dt, "dt")
    if step <= 0.0:
        raise ValueError(
            "run_complementary_filter: dt must be > 0, got %r" % (dt,))
    try:
        omega_steps = [list(o) for o in omega_samples]
    except TypeError:
        raise ValueError(
            "omega_samples must be a sequence of rate 3-vectors") from None
    if len(omega_steps) == 0:
        raise ValueError("run_complementary_filter: omega_samples is empty")
    rates = [_vec3(o, "omega_samples entry") for o in omega_steps]
    meas_steps = _normalize_measurement_steps(measurement_samples, len(rates))

    estimates = []
    innovation_norms = []
    for om, pairs in zip(rates, meas_steps):
        total = [0.0, 0.0, 0.0]
        for r, m in pairs:
            v = rotate_reference_vector(q, r)
            e = vector_measurement_error(m, v)
            total[0] += e[0]
            total[1] += e[1]
            total[2] += e[2]
        innovation_norms.append(_vec3_norm(total))
        q, b = propagate_attitude(
            q, om, b, total, gain_p, gain_i, step)
        estimates.append((q, b))
    return estimates, innovation_norms


def steady_state_verdict(innovation_norms, tolerance):
    """Convergence verdict for a filter run.

    True when the mean of the last min(10, n) per-step innovation norms
    is below the tolerance (rad), False otherwise. Raises ValueError for
    an empty norm sequence, non-finite norms, or a non-positive
    tolerance.
    """
    try:
        norms = [float(x) for x in innovation_norms]
    except TypeError:
        raise ValueError(
            "steady_state_verdict: innovation_norms must be a sequence "
            "of numbers") from None
    if len(norms) == 0:
        raise ValueError("steady_state_verdict: innovation_norms is empty")
    for x in norms:
        _finite(x, "innovation_norm")
    tol = _finite(tolerance, "tolerance")
    if tol <= 0.0:
        raise ValueError(
            "steady_state_verdict: tolerance must be > 0, got %r"
            % (tolerance,))
    window = norms[-min(10, len(norms)):]
    return sum(window) / len(window) < tol

#!/usr/bin/env python3
"""Control moment gyro (CMG) cluster logic (stdlib only).

Size and analyze a single-gimbal CMG cluster for spacecraft attitude
control: single-CMG torque from the gimbal rate, the torque
amplification against a reaction wheel at equal momentum, the standard
pyramid cluster geometry with gimbal axes at a skew angle above the
base plane, the cluster momentum and its momentum envelope over the
gimbal angle grid, the Jacobian based steering law with pseudoinverse
and null-space term, the singularity measure det(J J^T), and the gimbal
rate clip with the achieved torque and saturation flag. Paraphrase of
the standard CMG steering methodology; ECSS is the pack reference
standard (standards-map.yaml) and this logic is generic control
engineering, not proprietary content.

Conventions
-----------
- All vectors are 3D tuples (x, y, z). Angles are radians.
- Single CMG: rotor momentum vector h (N m s), gimbal axis unit vector
  g perpendicular to h, gimbal rate delta_dot (rad/s). The momentum
  direction rotates about g, so with zero external torque the torque
  exerted on the spacecraft is
      tau = -delta_dot * (g x h)
  For perpendicular geometry |tau| = h * |delta_dot|: a small rotor
  swept at high gimbal rate produces a large torque (the torque
  amplification property that separates CMGs from reaction wheels).
- Pyramid geometry: N units with unit momentum directions h_dirs at
  zero gimbal angle lying radially in the base plane at azimuth
  phi_i = 2*pi*(i-1)/N; the gimbal axis of unit i is the base-plane
  tangent direction tilted up by the skew angle beta:
      g_i = cos(beta) * t_i + sin(beta) * z,  t_i = (-sin phi_i, cos phi_i, 0)
  so the gimbal axis elevation above the base plane is beta. The
  momentum direction at gimbal angle delta_i follows the rotation of
  h_dirs_i about g_i:
      h_i(delta_i) = cos(delta_i) * h_dirs_i + sin(delta_i) * (g_i x h_dirs_i)
  Each unit carries the module rotor momentum CMG_MOMENTUM_NMS, so the
  full momentum vector is CMG_MOMENTUM_NMS * h_i(delta_i).
- Cluster momentum: h_cluster = sum of the full per-unit momentum
  vectors at the current gimbal angles.
- Momentum envelope: the maximum cluster momentum magnitude over the
  gimbal angle scan (coarse full-space scan plus the fine 2D scan of
  the skew-symmetric gimbal plane delta = (a, b, -a, -b), the family
  that preserves the 180 degree cluster symmetry about the base normal;
  the grid maximum is a lower bound on the true envelope, adequate for
  the slew feasibility check that the design slew momentum lies below
  it with margin).
- Jacobian and steering law: the cluster torque obeys tau = J * d_dot
  with J the 3 x N matrix whose columns are -g_i x h_i (full momentum
  vectors). The pseudoinverse steering law
      d_dot = J^T (J J^T)^-1 tau
  is augmented with the null-space term
      null_gain * (I - J^T (J J^T)^-1 J) n0
  which produces internal gimbal motion that leaves the output torque
  unchanged (J applied to the term is zero).
- Singularity measure: S = det(J J^T). S > threshold is nominal,
  0 < S <= threshold is near singularity, S <= 0 is singular. The
  steering law raises ValueError when S <= SINGULAR_DET_TOL (the
  pseudoinverse does not exist there).
- Units are SI throughout: N m, N m s, rad, rad/s, kg m^2.
"""

import math

# Module constants (documented sizing basis of the worked example).
CMG_MOMENTUM_NMS = 50.0            # rotor momentum magnitude per unit
PYRAMID_SKEW_DEGREES = 53.13       # displayed skew angle (atan(4/3))
PYRAMID_SKEW_RADIANS = math.atan(4.0 / 3.0)  # cos = 3/5, sin = 4/5
DEFAULT_NUM_UNITS = 4
DESIGN_SLEW_MOMENTUM_NMS = 100.0   # slew momentum requirement to check
MAX_GIMBAL_RATE_RAD_S = 2.0        # gimbal rate authority for clipping
NULL_GAIN_RAD_S = 0.05             # null-space term gain
NULL_VECTOR = (0.5, -0.5, 0.5, -0.5)  # standard alternating null vector
SINGULARITY_THRESHOLD = 1.0e8      # det(J J^T) nominal band boundary
SINGULAR_DET_TOL = 1.0e-3          # det(J J^T) below this is singular

DEFAULT_ENVELOPE_GRID = 12         # samples per gimbal axis, envelope scan


def _is_finite(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _check_vec(vec, name):
    if len(vec) != 3:
        raise ValueError(name + " must be a 3-vector")
    if not all(_is_finite(v) for v in vec):
        raise ValueError(name + " must be finite")
    return (float(vec[0]), float(vec[1]), float(vec[2]))


def _check_angles(gimbal_angles, num_units, name="gimbal_angles"):
    if len(gimbal_angles) != num_units:
        raise ValueError(name + " must have one entry per CMG unit")
    if not all(_is_finite(a) for a in gimbal_angles):
        raise ValueError(name + " must be finite")
    return tuple(float(a) for a in gimbal_angles)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a):
    return math.sqrt(_dot(a, a))


def _det3(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _solve_3x3(a, b):
    """Solve the 3 x 3 system a x = b by Gauss-Jordan elimination."""
    aug = [[float(a[i][j]) for j in range(3)] + [float(b[i])]
           for i in range(3)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-300:
            raise ValueError("singular linear system")
        if pivot != col:
            aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        aug[col] = [v / pv for v in aug[col]]
        for r in range(3):
            if r != col and aug[r][col] != 0.0:
                factor = aug[r][col]
                aug[r] = [aug[r][j] - factor * aug[col][j]
                          for j in range(4)]
    return (aug[0][3], aug[1][3], aug[2][3])


def cmg_torque(g_axis, h_vector, delta_dot, max_gimbal_rate=None):
    """Torque of a single CMG: tau = -delta_dot * (g x h).

    g_axis is the gimbal axis unit vector, h_vector the rotor momentum
    vector (N m s). Raises ValueError for a zero momentum vector,
    non-finite inputs, or (when max_gimbal_rate is given) a gimbal rate
    magnitude above the limit.
    """
    g = _check_vec(g_axis, "g_axis")
    h = _check_vec(h_vector, "h_vector")
    if not _is_finite(delta_dot):
        raise ValueError("delta_dot must be finite")
    h_mag = _norm(h)
    if h_mag <= 0.0:
        raise ValueError("rotor momentum must be non-zero")
    if max_gimbal_rate is not None:
        if not _is_finite(max_gimbal_rate) or max_gimbal_rate <= 0.0:
            raise ValueError("max_gimbal_rate must be positive and finite")
        if abs(delta_dot) > max_gimbal_rate:
            raise ValueError("gimbal rate above the rate limit")
    return tuple(-delta_dot * c for c in _cross(g, h))


def torque_amplification(cmg_momentum, gimbal_rate,
                         wheel_inertia, wheel_accel):
    """Torque amplification ratio of a CMG over a reaction wheel.

    The CMG delivers cmg_momentum * gimbal_rate; a reaction wheel of
    inertia wheel_inertia under angular acceleration wheel_accel
    delivers wheel_inertia * wheel_accel. At equal momentum the ratio
    compares the CMG torque with the wheel torque.
    """
    for val, name in ((cmg_momentum, "cmg_momentum"),
                      (gimbal_rate, "gimbal_rate"),
                      (wheel_inertia, "wheel_inertia"),
                      (wheel_accel, "wheel_accel")):
        if not _is_finite(val) or val <= 0.0:
            raise ValueError(name + " must be positive and finite")
    return (cmg_momentum * gimbal_rate) / (wheel_inertia * wheel_accel)


def pyramid_geometry(skew_angle, num_units):
    """Gimbal axes and zero-angle momentum directions of a pyramid.

    Returns (gimbal_axes, h_dirs), tuples of num_units unit 3-vectors
    each. skew_angle is the gimbal axis elevation above the base plane
    in radians (strictly between 0 and pi/2), num_units >= 3.
    """
    if not _is_finite(skew_angle):
        raise ValueError("skew_angle must be finite")
    if skew_angle <= 0.0 or skew_angle >= math.pi / 2.0:
        raise ValueError("skew_angle must lie strictly between 0 and pi/2")
    num_units = int(num_units)
    if num_units < 3:
        raise ValueError("a CMG cluster needs at least 3 units")
    cos_beta = math.cos(skew_angle)
    sin_beta = math.sin(skew_angle)
    gimbal_axes = []
    h_dirs = []
    for i in range(num_units):
        phi = 2.0 * math.pi * i / num_units
        radial = (math.cos(phi), math.sin(phi), 0.0)
        tangent = (-math.sin(phi), math.cos(phi), 0.0)
        gimbal_axes.append((cos_beta * tangent[0],
                            cos_beta * tangent[1],
                            sin_beta))
        h_dirs.append(radial)
    return (tuple(gimbal_axes), tuple(h_dirs))


def _unit_momentum(geometry, unit_index, delta):
    """Unit momentum direction of one CMG rotated about its gimbal axis."""
    g_axis = geometry[0][unit_index]
    h0_dir = geometry[1][unit_index]
    cos_d = math.cos(delta)
    sin_d = math.sin(delta)
    gxh = _cross(g_axis, h0_dir)
    return (cos_d * h0_dir[0] + sin_d * gxh[0],
            cos_d * h0_dir[1] + sin_d * gxh[1],
            cos_d * h0_dir[2] + sin_d * gxh[2])


def _full_momentum(geometry, unit_index, delta):
    d = _unit_momentum(geometry, unit_index, delta)
    return (CMG_MOMENTUM_NMS * d[0],
            CMG_MOMENTUM_NMS * d[1],
            CMG_MOMENTUM_NMS * d[2])


def cluster_momentum(gimbal_angles, geometry):
    """Total cluster momentum vector at the given gimbal angles."""
    num_units = len(geometry[0])
    angles = _check_angles(gimbal_angles, num_units)
    total = [0.0, 0.0, 0.0]
    for i in range(num_units):
        h = _full_momentum(geometry, i, angles[i])
        total[0] += h[0]
        total[1] += h[1]
        total[2] += h[2]
    return (total[0], total[1], total[2])


def momentum_envelope(geometry, grid=DEFAULT_ENVELOPE_GRID):
    """Max cluster momentum magnitude over the documented gimbal scans.

    Scans the skew-symmetric plane (a, b, -a, -b) at 2*grid samples per
    axis and, for clusters of at most 4 units, the full gimbal space at
    grid samples per axis; returns the maximum magnitude found.
    """
    num_units = len(geometry[0])
    grid = int(grid)
    if grid < 2:
        raise ValueError("grid must be at least 2 samples per axis")
    if num_units < 3:
        raise ValueError("a CMG cluster needs at least 3 units")
    best = 0.0

    def eval_angles(angles):
        nonlocal best
        mag = _norm(cluster_momentum(angles, geometry))
        if mag > best:
            best = mag

    # Fine 2D scan of the skew-symmetric plane (a, b, -a, -b), the
    # family preserving the 180 degree symmetry about the base normal.
    fine = 2 * grid
    for ia in range(fine):
        a = 2.0 * math.pi * ia / fine
        for ib in range(fine):
            b = 2.0 * math.pi * ib / fine
            if num_units == 4:
                eval_angles((a, b, -a, -b))
            else:
                angles = tuple(a if i % 2 == 0 else b for i in range(num_units))
                eval_angles(angles)

    # Coarse confirmation scan over the full gimbal space for small
    # clusters (grid^N combinations, feasible up to 4 units).
    if num_units <= 4:
        def recurse(partial, depth):
            if depth == num_units:
                eval_angles(tuple(partial))
                return
            for k in range(grid):
                partial.append(2.0 * math.pi * k / grid)
                recurse(partial, depth + 1)
                partial.pop()

        recurse([], 0)
    return best


def jacobian(gimbal_angles, geometry):
    """3 x N Jacobian J with columns -g_i x h_i (full momentum)."""
    num_units = len(geometry[0])
    angles = _check_angles(gimbal_angles, num_units)
    cols = []
    for i in range(num_units):
        g = geometry[0][i]
        h = _full_momentum(geometry, i, angles[i])
        c = _cross(g, h)
        cols.append((-c[0], -c[1], -c[2]))
    return tuple(cols)


def _jac_gram(jac):
    """3 x 3 Gram matrix J J^T of a Jacobian given as N column vectors."""
    gram = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
    for col in jac:
        for r in range(3):
            for c in range(3):
                gram[r][c] += col[r] * col[c]
    return tuple(tuple(row) for row in gram)


def _jac_times(jac, vec):
    """J v for a Jacobian stored as N columns and an N-vector v."""
    result = [0.0, 0.0, 0.0]
    for i, col in enumerate(jac):
        vi = vec[i]
        for r in range(3):
            result[r] += col[r] * vi
    return (result[0], result[1], result[2])


def _null_vector(num_units):
    """Standard alternating unit null vector of the symmetric cluster."""
    scale = 1.0 / math.sqrt(num_units)
    return tuple(scale if i % 2 == 0 else -scale
                 for i in range(num_units))


def singularity_measure(gimbal_angles, geometry):
    """Singularity measure S = det(J J^T) of the gimbal state."""
    jac = jacobian(gimbal_angles, geometry)
    return _det3(_jac_gram(jac))


def singularity_verdict(s_measure, threshold):
    """Classify the gimbal state from its singularity measure.

    Returns "singular" when S <= SINGULAR_DET_TOL (the steering law has
    no solution below this floor), "near singularity" when the measure
    sits between the floor and the threshold, and "nominal" above.
    """
    if not _is_finite(s_measure):
        raise ValueError("s_measure must be finite")
    if not _is_finite(threshold) or threshold <= 0.0:
        raise ValueError("threshold must be positive and finite")
    if s_measure <= SINGULAR_DET_TOL:
        return "singular"
    if s_measure <= threshold:
        return "near singularity"
    return "nominal"


def steering_law(gimbal_angles, tau_cmd, geometry, null_gain=NULL_GAIN_RAD_S):
    """Gimbal rates for a commanded torque with the pseudoinverse law.

    Returns delta_dot = J^T (J J^T)^-1 tau + null_gain * (I - J^T
    (J J^T)^-1 J) n0 with n0 the standard alternating null vector of
    the symmetric cluster. Raises ValueError when the cluster is
    singular (S <= SINGULAR_DET_TOL) or the inputs are non-finite.
    """
    num_units = len(geometry[0])
    angles = _check_angles(gimbal_angles, num_units)
    tau = _check_vec(tau_cmd, "tau_cmd")
    if not _is_finite(null_gain):
        raise ValueError("null_gain must be finite")
    jac = jacobian(angles, geometry)
    gram = _jac_gram(jac)
    if _det3(gram) <= SINGULAR_DET_TOL:
        raise ValueError("cluster is singular, the pseudoinverse steering "
                         "law has no solution")
    x = _solve_3x3(gram, tau)             # x = (J J^T)^-1 tau
    rates = [float(sum(jac[i][r] * x[r] for r in range(3)))
             for i in range(num_units)]   # J^T (J J^T)^-1 tau
    if null_gain != 0.0:
        # Null-space term: null_gain * (I - J^T (J J^T)^-1 J) n0. This
        # term is annihilated by J, so it adds internal gimbal motion
        # without changing the output torque.
        n0 = _null_vector(num_units)
        jn0 = _jac_times(jac, n0)         # J n0
        y = _solve_3x3(gram, jn0)         # (J J^T)^-1 J n0
        for i in range(num_units):
            jtproj = sum(jac[i][r] * y[r] for r in range(3))
            rates[i] += null_gain * (n0[i] - jtproj)
    return tuple(rates)


def cmg_cluster_summary(gimbal_angles, tau_cmd, geometry,
                        max_gimbal_rate=MAX_GIMBAL_RATE_RAD_S,
                        singularity_threshold=SINGULARITY_THRESHOLD,
                        null_gain=NULL_GAIN_RAD_S):
    """Cluster summary dict: rates, achieved torque, verdict, flags.

    Rates are the pseudoinverse steering output clipped to
    +-max_gimbal_rate; saturated reports whether any rate exceeded the
    limit before clipping. achieved_torque is J times the clipped
    rates. Raises ValueError for a singular cluster state.
    """
    num_units = len(geometry[0])
    angles = _check_angles(gimbal_angles, num_units)
    tau = _check_vec(tau_cmd, "tau_cmd")
    if not _is_finite(max_gimbal_rate) or max_gimbal_rate <= 0.0:
        raise ValueError("max_gimbal_rate must be positive and finite")
    if not _is_finite(null_gain):
        raise ValueError("null_gain must be finite")
    jac = jacobian(angles, geometry)
    s_measure = _det3(_jac_gram(jac))
    verdict = singularity_verdict(s_measure, singularity_threshold)
    if s_measure <= SINGULAR_DET_TOL:
        raise ValueError("cluster is singular, no steering solution")
    raw = steering_law(angles, tau, geometry, null_gain=null_gain)
    saturated = any(abs(r) > max_gimbal_rate for r in raw)
    clipped = tuple(max(-max_gimbal_rate, min(max_gimbal_rate, r))
                    for r in raw)
    achieved = _jac_times(jac, clipped)
    return {
        "gimbal_rates": clipped,
        "achieved_torque": achieved,
        "singularity": verdict,
        "saturated": saturated,
        "margin": s_measure / singularity_threshold,
        "s_measure": s_measure,
    }

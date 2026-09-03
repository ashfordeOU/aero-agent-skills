"""Clohessy-Wiltshire linearized relative motion about a circular chief.

Pure stdlib implementation of the CW (Hill) equations for the relative
state of a deputy spacecraft about a chief in a circular orbit. The
relative frame is LVLH with x radial outward, y along-track, z
cross-track (right-handed about the orbit normal). All inputs SI.

Functions
---------
mean_motion(a, mu)
cw_stm(n, tau)
cw_propagate(state0, n, tau)
bounded_orbit_condition(state0, n)
cw_targeting(state0, state_f_desired, n, tau_f)
relative_orbit_geometry_check(r_f, min_separation)
"""

import math

MU_EARTH = 3.986004418e14  # m^3/s^2, standard terrestrial value
EPS = 1e-12  # tolerance for identity and singularity checks


def _require_finite(value, name):
    if value is None or not math.isfinite(float(value)):
        raise ValueError("%s must be finite, got %r" % (name, value))


def _require_state_finite(state):
    if len(state) != 6:
        raise ValueError("relative state must have 6 components [x, y, z, x', y', z']")
    for i, value in enumerate(state):
        _require_finite(value, "state[%d]" % i)


def mean_motion(a, mu=MU_EARTH):
    """Mean motion n = sqrt(mu / a^3) of a chief on a circular orbit.

    Raises ValueError when the semi-major axis a is non-positive or the
    gravitational parameter mu is non-finite.
    """
    if a <= 0.0:
        raise ValueError("semi-major axis a must be positive, got %r" % (a,))
    _require_finite(mu, "mu")
    if mu <= 0.0:
        raise ValueError("mu must be positive, got %r" % (mu,))
    return math.sqrt(mu / a**3)


def cw_stm(n, tau):
    """6x6 Clohessy-Wiltshire state transition matrix over tau seconds.

    Standard closed form (Vallado convention) with C = cos(n*tau),
    S = sin(n*tau), T = n*tau. The state order is
    [x, y, z, x', y', z'] with x radial, y along-track, z cross-track.
    At tau = 0 the matrix is the identity within floating point noise.
    Raises ValueError for n <= 0 or tau < 0 or non-finite inputs.
    """
    if n <= 0.0:
        raise ValueError("mean motion n must be positive, got %r" % (n,))
    if tau < 0.0:
        raise ValueError("propagation time tau must be >= 0, got %r" % (tau,))
    _require_finite(n, "n")
    _require_finite(tau, "tau")
    ang = n * tau
    c = math.cos(ang)
    s = math.sin(ang)
    t = ang
    return [
        [4 - 3 * c, 0.0, 0.0, s / n, 2 * (1 - c) / n, 0.0],
        [6 * (s - t), 1.0, 0.0, -2 * (1 - c) / n, (4 * s - 3 * t) / n, 0.0],
        [0.0, 0.0, c, 0.0, 0.0, s / n],
        [3 * n * s, 0.0, 0.0, c, 2 * s, 0.0],
        [6 * n * (c - 1), 0.0, 0.0, -2 * s, 4 * c - 3, 0.0],
        [0.0, 0.0, -n * s, 0.0, 0.0, c],
    ]


def _mat_vec_6(m, v):
    """Multiply a 6x6 matrix by a 6-vector, return the 6-vector."""
    return [sum(m[i][k] * v[k] for k in range(6)) for i in range(6)]


def cw_propagate(state0, n, tau):
    """Propagate the deputy relative state with the CW STM.

    state0 is [x, y, z, x', y', z'] at time t0; returns the same state
    order at t0 + tau. Raises ValueError on non-positive n, negative
    tau, or any non-finite state component.
    """
    _require_state_finite(state0)
    if n <= 0.0:
        raise ValueError("mean motion n must be positive, got %r" % (n,))
    if tau < 0.0:
        raise ValueError("propagation time tau must be >= 0, got %r" % (tau,))
    _require_finite(n, "n")
    _require_finite(tau, "tau")
    return _mat_vec_6(cw_stm(n, tau), list(state0))


def bounded_orbit_condition(state0, n):
    """Check the bounded (non-drifting) relative orbit condition.

    A natural-motion relative orbit stays bounded when the along-track
    rate obeys y_dot = -2*n*x (x radial offset, n chief mean motion).
    Returns (required_y_dot, flag) where flag is True when the deputy
    state already satisfies the condition within a 1e-6 relative
    tolerance, False when the state will drift along track.
    """
    _require_state_finite(state0)
    if n <= 0.0:
        raise ValueError("mean motion n must be positive, got %r" % (n,))
    required = -2.0 * n * state0[0]
    if abs(state0[0]) < 1e-12:
        flag = abs(state0[4]) < 1e-9
    else:
        flag = abs(state0[4] - required) <= 1e-6 * max(1.0, abs(required))
    return required, flag


def _det3(m):
    """Determinant of a 3x3 matrix given as a list of three rows."""
    return (
        m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
        - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
        + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
    )


def _inv3(m):
    """Inverse of a 3x3 matrix by the cofactor formula, pure stdlib.

    Raises ValueError when the matrix is singular (|det| <= 1e-12),
    which occurs for CW targeting at integer half-orbit times.
    """
    det = _det3(m)
    if abs(det) <= 1e-12:
        raise ValueError("singular 3x3 matrix in targeting (phi_rv rank deficient)")
    inv_det = 1.0 / det
    cof = [
        [
            m[1][1] * m[2][2] - m[1][2] * m[2][1],
            m[0][2] * m[2][1] - m[0][1] * m[2][2],
            m[0][1] * m[1][2] - m[0][2] * m[1][1],
        ],
        [
            m[1][2] * m[2][0] - m[1][0] * m[2][2],
            m[0][0] * m[2][2] - m[0][2] * m[2][0],
            m[0][2] * m[1][0] - m[0][0] * m[1][2],
        ],
        [
            m[1][0] * m[2][1] - m[1][1] * m[2][0],
            m[0][1] * m[2][0] - m[0][0] * m[2][1],
            m[0][0] * m[1][1] - m[0][1] * m[1][0],
        ],
    ]
    return [[inv_det * cof[i][j] for j in range(3)] for i in range(3)]


def _mat_vec_3(m, v):
    """Multiply a 3x3 matrix by a 3-vector."""
    return [sum(m[i][k] * v[k] for k in range(3)) for i in range(3)]


def _phi_partition(n, tau):
    """Return (phi_rr, phi_rv, phi_vr, phi_vv) in-plane 3x3 partitions.

    The cross-track axis (z, z') decouples from the in-plane motion, so
    the full 6x6 STM reduces to 3x3 partitions over the axes x then y
    then z. phi_rv is the position response to an impulsive velocity.
    """
    stm = cw_stm(n, tau)
    idx = [0, 1, 2]
    phi_rr = [[stm[i][j] for j in idx] for i in idx]
    phi_rv = [[stm[i][j + 3] for j in idx] for i in idx]
    phi_vr = [[stm[i + 3][j] for j in idx] for i in idx]
    phi_vv = [[stm[i + 3][j + 3] for j in idx] for i in idx]
    return phi_rr, phi_rv, phi_vr, phi_vv


def cw_targeting(state0, state_f_desired, n, tau_f):
    """Two-impulse CW targeting to a desired relative state at tau_f.

    Uses the STM partition: solve v_0+ = phi_rv^-1 (r_f - phi_rr r_0)
    for the post-first-impulse velocity, then propagate to find v_f-
    and the closing impulse. Returns (dv0, dvf, v0_plus, vf_minus,
    total_dv) with dv vectors over [x, y, z]. Raises ValueError for a
    singular phi_rv, which occurs when tau_f is an integer multiple of
    the half-orbit period (natural-motion return to the same radial
    line, so no free velocity reaches the target). A cross-track nulling
    demand at an integer half-orbit time is also singular: sin(n*tau_f)
    vanishes, so the z column of phi_rv cannot steer z.
    """
    _require_state_finite(state0)
    _require_state_finite(state_f_desired)
    if n <= 0.0:
        raise ValueError("mean motion n must be positive, got %r" % (n,))
    if tau_f <= 0.0:
        raise ValueError("targeting time tau_f must be > 0, got %r" % (tau_f,))
    _require_finite(n, "n")
    _require_finite(tau_f, "tau_f")
    phi_rr, phi_rv, phi_vr, phi_vv = _phi_partition(n, tau_f)
    r0 = list(state0[0:3])
    v0 = list(state0[3:6])
    rf = list(state_f_desired[0:3])
    vf_des = list(state_f_desired[3:6])
    sin_t = math.sin(n * tau_f)
    if abs(sin_t) < 1e-9:
        z_target_needed = rf[2] - phi_rr[2][2] * r0[2]
        if abs(z_target_needed) > 1e-3:
            raise ValueError(
                "phi_rv singular: cross-track channel uncontrollable at an integer "
                "half-orbit time (sin(n*tau_f) ~ 0)"
            )
    phi_rv_inv = _inv3(phi_rv)
    target = [rf[i] - sum(phi_rr[i][k] * r0[k] for k in range(3)) for i in range(3)]
    v0_plus = _mat_vec_3(phi_rv_inv, target)
    vf_minus = [
        sum(phi_vr[i][k] * r0[k] for k in range(3))
        + sum(phi_vv[i][k] * v0_plus[k] for k in range(3))
        for i in range(3)
    ]
    dv0 = [v0_plus[i] - v0[i] for i in range(3)]
    dvf = [vf_des[i] - vf_minus[i] for i in range(3)]
    total_dv = sum(abs(dv0[i]) for i in range(3)) + sum(abs(dvf[i]) for i in range(3))
    return dv0, dvf, v0_plus, vf_minus, total_dv


def _vec_norm(v):
    return math.sqrt(sum(comp**2 for comp in v))


def relative_orbit_geometry_check(r_f, min_separation):
    """Verdict on the propagated relative-position geometry.

    Compares the deputy position r_f (3-vector) at the end of a
    trajectory with min_separation, the safe standoff radius around the
    chief (or the target on its own orbit). Returns a verdict string:
    "ok" when the separation stays clear, "close-approach" when the
    final separation is below min_separation and a collision-radius
    crossing is flagged.
    """
    if len(r_f) != 3:
        raise ValueError("r_f must be a 3-vector [x, y, z]")
    for comp in r_f:
        _require_finite(comp, "r_f component")
    if min_separation <= 0.0:
        raise ValueError("min_separation must be positive, got %r" % (min_separation,))
    sep = _vec_norm(r_f)
    if sep < min_separation:
        return "close-approach"
    return "ok"

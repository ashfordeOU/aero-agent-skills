#!/usr/bin/env python3
"""Two-body Keplerian orbit propagation in time (classical elements to state).

Summary (ecss, standards-map.yaml, summary-only): given the classical
element state (a, e, i, RAAN, argp, nu0) of an unperturbed elliptical
orbit, the mean motion n follows from Kepler's third law, the mean
anomaly advances linearly as M = M0 + n dt, and the Kepler equation
M = E - e sin E is solved for the eccentric anomaly E by Newton
iteration. The true anomaly comes from the branch-safe half-angle
form, the radius from r = a (1 - e cos E), and the inertial position
and velocity follow from the perifocal frame rotated through argp, i
and RAAN.

Units: length in km, time in s, velocity in km/s, mu in km^3/s^2,
angles in rad. Deterministic, offline, stdlib-only (math).
"""

import math

MU_EARTH_DEFAULT = 398600.4418  # Earth gravitational parameter, km^3/s^2
KEPLER_NEWTON_TOL = 1e-12       # Kepler equation residual target, rad
KEPLER_MAX_ITER = 100           # Newton iteration cap
TWO_PI = 2.0 * math.pi


def _to_float(value, name):
    """Convert to finite float or raise ValueError."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (name, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _to_vec3(value, name):
    """Convert to a length-3 list of finite floats or raise ValueError."""
    try:
        items = list(value)
    except TypeError:
        raise ValueError("%s must be a 3-vector, got %r" % (name, value))
    if len(items) != 3:
        raise ValueError("%s must have length 3, got %r" % (name, value))
    return [_to_float(c, name) for c in items]


def _check_mu(mu):
    """Gravitational parameter must be finite and > 0."""
    mu = _to_float(mu, "mu")
    if mu <= 0.0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return mu


def _check_ellipse(semimajor_axis_km, eccentricity):
    """Return (a, e) floats for an elliptical orbit (a > 0, e in [0, 1))."""
    a = _to_float(semimajor_axis_km, "semimajor_axis_km")
    e = _to_float(eccentricity, "eccentricity")
    if a <= 0.0:
        raise ValueError(
            "elliptical orbit needs a > 0, got a = %r" % (semimajor_axis_km,)
        )
    if e < 0.0 or e >= 1.0:
        raise ValueError(
            "elliptical orbit needs e in [0, 1), got e = %r" % (eccentricity,)
        )
    return a, e


def mean_motion(semimajor_axis_km, mu=MU_EARTH_DEFAULT):
    """Mean motion n = sqrt(mu / a^3) in rad/s (Kepler's third law).

    Raises ValueError when a <= 0 or mu <= 0.
    """
    mu = _check_mu(mu)
    a = _to_float(semimajor_axis_km, "semimajor_axis_km")
    if a <= 0.0:
        raise ValueError(
            "mean motion needs a > 0, got a = %r" % (semimajor_axis_km,)
        )
    return math.sqrt(mu / (a * a * a))


def orbital_period(semimajor_axis_km, mu=MU_EARTH_DEFAULT):
    """Orbital period T = 2 pi / n in seconds.

    Raises ValueError when a <= 0 or mu <= 0.
    """
    n = mean_motion(semimajor_axis_km, mu)
    return TWO_PI / n


def kepler_solve(mean_anomaly_rad, eccentricity):
    """Eccentric anomaly E (rad) solving M = E - e sin E.

    Newton iteration E -= (E - e sin E - M) / (1 - e cos E) from the
    start E = M + e sin M, iterated to a KEPLER_NEWTON_TOL residual
    within KEPLER_MAX_ITER steps. For e = 0 the solution is E = M
    exactly. Elliptical orbits only: raises ValueError when e is
    outside [0, 1).
    """
    M = _to_float(mean_anomaly_rad, "mean_anomaly_rad")
    e = _to_float(eccentricity, "eccentricity")
    if e < 0.0 or e >= 1.0:
        raise ValueError(
            "kepler_solve needs e in [0, 1), got e = %r" % (eccentricity,)
        )
    E = M + e * math.sin(M)
    for _ in range(KEPLER_MAX_ITER):
        resid = E - e * math.sin(E) - M
        if abs(resid) < KEPLER_NEWTON_TOL:
            return E
        E -= resid / (1.0 - e * math.cos(E))
    raise ValueError(
        "kepler_solve did not converge in %d iterations for M = %r, "
        "e = %r" % (KEPLER_MAX_ITER, mean_anomaly_rad, eccentricity)
    )


def true_anomaly_from_eccentric(eccentric_anomaly_rad, eccentricity):
    """True anomaly nu (rad) from eccentric anomaly E.

    Branch-safe half-angle form nu = 2 atan2(sqrt(1 + e) sin(E / 2),
    sqrt(1 - e) cos(E / 2)), folded into (-pi, pi]. E = 0 gives
    nu = 0 (periapsis); E = pi gives nu = pi (apoapsis). Raises
    ValueError when e is outside [0, 1).
    """
    E = _to_float(eccentric_anomaly_rad, "eccentric_anomaly_rad")
    e = _to_float(eccentricity, "eccentricity")
    if e < 0.0 or e >= 1.0:
        raise ValueError(
            "true anomaly needs e in [0, 1), got e = %r" % (eccentricity,)
        )
    nu = 2.0 * math.atan2(
        math.sqrt(1.0 + e) * math.sin(0.5 * E),
        math.sqrt(1.0 - e) * math.cos(0.5 * E),
    )
    if nu > math.pi:
        nu -= TWO_PI
    elif nu < -math.pi:
        nu += TWO_PI
    return nu


def eccentric_anomaly_from_true(true_anomaly_rad, eccentricity):
    """Eccentric anomaly E (rad) from true anomaly nu (inverse map).

    E = 2 atan2(sqrt(1 - e) sin(nu / 2), sqrt(1 + e) cos(nu / 2)),
    branch-matched to nu. Raises ValueError when e is outside [0, 1).
    """
    nu = _to_float(true_anomaly_rad, "true_anomaly_rad")
    e = _to_float(eccentricity, "eccentricity")
    if e < 0.0 or e >= 1.0:
        raise ValueError(
            "eccentric anomaly needs e in [0, 1), got e = %r" % (eccentricity,)
        )
    return 2.0 * math.atan2(
        math.sqrt(1.0 - e) * math.sin(0.5 * nu),
        math.sqrt(1.0 + e) * math.cos(0.5 * nu),
    )


def radius_at_anomaly(semimajor_axis_km, eccentricity, true_anomaly_rad):
    """Radius r = a (1 - e^2) / (1 + e cos nu) in km.

    Periapsis (nu = 0) gives a (1 - e); apoapsis (nu = pi) gives
    a (1 + e). Raises ValueError when a <= 0 or e is outside [0, 1).
    """
    a, e = _check_ellipse(semimajor_axis_km, eccentricity)
    nu = _to_float(true_anomaly_rad, "true_anomaly_rad")
    return a * (1.0 - e * e) / (1.0 + e * math.cos(nu))


def time_since_periapsis(true_anomaly_rad, semimajor_axis_km,
                         eccentricity, mu=MU_EARTH_DEFAULT):
    """Time t (s) from periapsis passage to the true anomaly nu.

    Folds nu into [0, 2 pi), maps to E with the inverse half-angle
    form, and evaluates t = (E - e sin E) / n in [0, T). Raises
    ValueError on non-physical inputs (a <= 0, e outside [0, 1),
    mu <= 0).
    """
    nu = _to_float(true_anomaly_rad, "true_anomaly_rad")
    a, e = _check_ellipse(semimajor_axis_km, eccentricity)
    mu = _check_mu(mu)
    n = math.sqrt(mu / (a * a * a))
    E = eccentric_anomaly_from_true(nu % TWO_PI, e)
    return (E - e * math.sin(E)) / n


def _rot1(theta):
    """Classical rotation matrix about the x axis by angle theta."""
    c = math.cos(theta)
    s = math.sin(theta)
    return [[1.0, 0.0, 0.0],
            [0.0, c, s],
            [0.0, -s, c]]


def _rot3(theta):
    """Classical rotation matrix about the z axis by angle theta."""
    c = math.cos(theta)
    s = math.sin(theta)
    return [[c, s, 0.0],
            [-s, c, 0.0],
            [0.0, 0.0, 1.0]]


def _mat_mul3(m1, m2):
    """Product of two 3x3 matrices."""
    return [[sum(m1[i][k] * m2[k][j] for k in range(3)) for j in range(3)]
            for i in range(3)]


def _mat_vec3(m, v):
    """Product of a 3x3 matrix and a 3-vector."""
    return [sum(m[i][j] * v[j] for j in range(3)) for i in range(3)]


def perifocal_to_inertial(r_pf, v_pf, raan_rad, inclination_rad, argp_rad):
    """Rotate perifocal (PQW) position and velocity into the inertial frame.

    Standard 3-rotation M = R3(-RAAN) R1(-i) R3(-argp) with the
    classical rotation matrix forms (active convention matching the
    keplerian-elements leaf; the first column of M is the periapsis
    direction unit vector). Returns the (r, v) inertial pair.
    """
    raan = _to_float(raan_rad, "raan_rad")
    inc = _to_float(inclination_rad, "inclination_rad")
    argp = _to_float(argp_rad, "argp_rad")
    r = _to_vec3(r_pf, "r_pf")
    v = _to_vec3(v_pf, "v_pf")
    m = _mat_mul3(_rot3(-raan), _mat_mul3(_rot1(-inc), _rot3(-argp)))
    return _mat_vec3(m, r), _mat_vec3(m, v)


def propagate_kepler(semimajor_axis_km, eccentricity, inclination_rad,
                     raan_rad, argp_rad, true_anomaly0_rad, dt_s,
                     mu=MU_EARTH_DEFAULT):
    """Propagate a classical-element state by an elapsed time dt.

    E0 from nu0 via the inverse map, M0 = E0 - e sin E0, M = M0 + n dt,
    E = kepler_solve(M), nu from the half-angle form, r = a (1 - e cos E),
    then the perifocal r and v rotated to the inertial frame.

    Returns a dict with keys mean_anomaly_rad, eccentric_anomaly_rad,
    true_anomaly_rad, radius_km, position_km (3-vector), velocity_kms
    (3-vector), period_s. Raises ValueError on non-physical inputs
    (a <= 0, e outside [0, 1), dt < 0, mu <= 0).
    """
    a = _to_float(semimajor_axis_km, "semimajor_axis_km")
    e = _to_float(eccentricity, "eccentricity")
    if a <= 0.0:
        raise ValueError(
            "propagation needs a > 0, got a = %r" % (semimajor_axis_km,)
        )
    if e < 0.0 or e >= 1.0:
        raise ValueError(
            "propagation needs e in [0, 1), got e = %r" % (eccentricity,)
        )
    mu = _check_mu(mu)
    dt = _to_float(dt_s, "dt_s")
    if dt < 0.0:
        raise ValueError("dt must be >= 0, got dt = %r" % (dt_s,))
    nu0 = _to_float(true_anomaly0_rad, "true_anomaly0_rad")
    inc = _to_float(inclination_rad, "inclination_rad")
    raan = _to_float(raan_rad, "raan_rad")
    argp = _to_float(argp_rad, "argp_rad")

    n = math.sqrt(mu / (a * a * a))
    period = TWO_PI / n
    E0 = eccentric_anomaly_from_true(nu0, e)
    M = (E0 - e * math.sin(E0)) + n * dt
    E = kepler_solve(M, e)
    nu = true_anomaly_from_eccentric(E, e)
    rmag = a * (1.0 - e * math.cos(E))

    # Perifocal frame: r along P = (cos nu, sin nu), v via the
    # semi-latus rectum p = a (1 - e^2).
    p = a * (1.0 - e * e)
    vfac = math.sqrt(mu / p)
    r_pf = [rmag * math.cos(nu), rmag * math.sin(nu), 0.0]
    v_pf = [-vfac * math.sin(nu), vfac * (e + math.cos(nu)), 0.0]
    r, v = perifocal_to_inertial(r_pf, v_pf, raan, inc, argp)

    return {
        "mean_anomaly_rad": M,
        "eccentric_anomaly_rad": E,
        "true_anomaly_rad": nu,
        "radius_km": rmag,
        "position_km": r,
        "velocity_kms": v,
        "period_s": period,
    }

#!/usr/bin/env python3
"""Classical (keplerian) orbital elements from position and velocity (rv2coe).

Two-body astrodynamics summary (standards-map.yaml, ecss: free ESA
download, summary-only): the classical element set describes an
unperturbed two-body orbit. The conversion follows the standard vector
formulation (specific angular momentum h, node vector n, eccentricity
vector e, specific energy) with documented conventions for circular
(e ~ 0) and equatorial (i ~ 0) degenerate cases.

Units: position in km, velocity in km/s, mu in km^3/s^2, angles in
radians, period in seconds, radii in km. Deterministic, offline,
stdlib-only (math).
"""

import math

MU = 398600.4418  # Earth gravitational parameter, km^3/s^2

E_TOL = 1e-8      # eccentricity below this counts as circular
EPS_TOL = 1e-10   # specific-energy magnitude below this counts as parabolic
N_REL_TOL = 1e-8  # |n| below this * |h| counts as equatorial


def _check_mu(mu):
    try:
        f = float(mu)
    except (TypeError, ValueError):
        raise ValueError("mu must be a number, got %r" % (mu,))
    if not math.isfinite(f) or f <= 0.0:
        raise ValueError("mu must be finite and > 0, got %r" % (mu,))


def _as_vec(x, name):
    if len(x) != 3:
        raise ValueError("%s must have length 3, got %r" % (name, x))
    out = []
    for c in x:
        try:
            f = float(c)
        except (TypeError, ValueError):
            raise ValueError("%s entries must be numbers, got %r" % (name, x))
        if not math.isfinite(f):
            raise ValueError("%s entries must be finite, got %r" % (name, x))
        out.append(f)
    return out


def dot(a, b):
    """Scalar dot product of two 3-vectors."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    """Vector cross product a x b of two 3-vectors."""
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def norm(v):
    """Euclidean norm of a 3-vector."""
    return math.sqrt(dot(v, v))


def specific_angular_momentum(r, v):
    """h = r x v in km^2/s.

    Raises ValueError when the input vectors are invalid or when the
    trajectory is rectilinear (zero angular momentum).
    """
    r = _as_vec(r, "r")
    v = _as_vec(v, "v")
    h = cross(r, v)
    if norm(h) <= 0.0:
        raise ValueError("zero angular momentum: rectilinear (radial) trajectory")
    return h


def node_vector(h):
    """Node vector n = k x h with k = (0, 0, 1); zero for equatorial orbits."""
    h = _as_vec(h, "h")
    return cross([0.0, 0.0, 1.0], h)


def eccentricity_vector(r, v, mu=MU):
    """e_vec = (v x h)/mu - r/|r|, dimensionless.

    Raises ValueError when |r| is zero or mu is invalid.
    """
    r = _as_vec(r, "r")
    v = _as_vec(v, "v")
    _check_mu(mu)
    rmag = norm(r)
    if rmag <= 0.0:
        raise ValueError("zero position vector: |r| must be > 0")
    vxh = cross(v, cross(r, v))
    return [vxh[i] / mu - r[i] / rmag for i in range(3)]


def specific_energy(r, v, mu=MU):
    """epsilon = v^2/2 - mu/|r| in km^2/s^2.

    Raises ValueError when |r| is zero or mu is invalid.
    """
    r = _as_vec(r, "r")
    v = _as_vec(v, "v")
    _check_mu(mu)
    rmag = norm(r)
    if rmag <= 0.0:
        raise ValueError("zero position vector: |r| must be > 0")
    return dot(v, v) / 2.0 - mu / rmag


def semimajor_axis(r, v, mu=MU):
    """a = -mu / (2 epsilon) in km.

    Raises ValueError for parabolic orbits (specific energy ~ 0).
    Hyperbolic orbits return a negative semimajor axis.
    """
    eps = specific_energy(r, v, mu)
    if abs(eps) <= EPS_TOL:
        raise ValueError(
            "parabolic orbit: specific energy ~ 0, semimajor axis undefined"
        )
    return -mu / (2.0 * eps)


def inclination(h):
    """Inclination i = acos(h_z / |h|) in radians, range [0, pi]."""
    h = _as_vec(h, "h")
    hmag = norm(h)
    if hmag <= 0.0:
        raise ValueError("zero angular momentum")
    return math.acos(h[2] / hmag)


def raan(h):
    """Right ascension of the ascending node Omega = atan2(n_y, n_x).

    Convention: 0.0 for equatorial orbits, where the node vector is
    undefined (n ~ 0). Returns radians in (-pi, pi].
    """
    h = _as_vec(h, "h")
    hmag = norm(h)
    if hmag <= 0.0:
        raise ValueError("zero angular momentum")
    n = node_vector(h)
    nmag = norm(n)
    if nmag <= N_REL_TOL * hmag:
        return 0.0
    return math.atan2(n[1], n[0])


def argument_of_periapsis(h, e_vec):
    """Argument of periapsis omega in radians, range [0, 2 pi).

    General case: omega = acos(n . e_vec / (|n| e)), corrected to
    2 pi - omega when e_z < 0. Equatorial convention (|n| ~ 0):
    omega = atan2(e_y, e_x) measured from the reference x axis, folded
    into [0, 2 pi). Circular convention (e ~ 0): 0.0.
    """
    h = _as_vec(h, "h")
    e_vec = _as_vec(e_vec, "e_vec")
    e = norm(e_vec)
    n = node_vector(h)
    nmag = norm(n)
    hmag = norm(h)
    if e <= E_TOL:
        return 0.0
    if nmag <= N_REL_TOL * hmag:
        w = math.atan2(e_vec[1], e_vec[0])
        return w if w >= 0.0 else w + 2.0 * math.pi
    w = math.acos(max(-1.0, min(1.0, dot(n, e_vec) / (nmag * e))))
    if e_vec[2] < 0.0:
        w = 2.0 * math.pi - w
    return w


def true_anomaly(h, e_vec, r, v):
    """True anomaly nu in radians, range [0, 2 pi).

    General case: nu = acos(e_vec . r / (e |r|)), corrected to
    2 pi - nu when r . v < 0. Circular non-equatorial convention:
    measured from the node vector. Circular equatorial convention:
    nu = atan2(r_y, r_x), folded into [0, 2 pi).
    """
    h = _as_vec(h, "h")
    e_vec = _as_vec(e_vec, "e_vec")
    r = _as_vec(r, "r")
    v = _as_vec(v, "v")
    e = norm(e_vec)
    rmag = norm(r)
    if rmag <= 0.0:
        raise ValueError("zero position vector: |r| must be > 0")
    n = node_vector(h)
    nmag = norm(n)
    hmag = norm(h)
    if e > E_TOL:
        nu = math.acos(max(-1.0, min(1.0, dot(e_vec, r) / (e * rmag))))
    elif nmag > N_REL_TOL * hmag:
        # circular, non-equatorial: measure from the node vector
        nu = math.acos(max(-1.0, min(1.0, dot(n, r) / (nmag * rmag))))
    else:
        # circular, equatorial: measure from the reference x axis
        nu = math.atan2(r[1], r[0])
        if nu < 0.0:
            nu += 2.0 * math.pi
        return nu
    if dot(r, v) < 0.0:
        nu = 2.0 * math.pi - nu
    return nu


def orbital_period(a, mu=MU):
    """Orbital period T = 2 pi sqrt(a^3 / mu) in seconds.

    Raises ValueError for non-elliptical orbits (a <= 0), where the
    period is undefined.
    """
    _check_mu(mu)
    if a <= 0.0:
        raise ValueError(
            "orbital period needs an elliptical orbit (a > 0), got a = %r" % (a,)
        )
    return 2.0 * math.pi * math.sqrt(a * a * a / mu)


def periapsis_apoapsis_radii(a, e):
    """(rp, ra) = (a (1 - e), a (1 + e)) in km.

    Raises ValueError for non-elliptical orbits (a <= 0 or e >= 1).
    """
    if a <= 0.0:
        raise ValueError(
            "periapsis/apoapsis need an elliptical orbit (a > 0), got a = %r" % (a,)
        )
    if e >= 1.0:
        raise ValueError("periapsis/apoapsis need e < 1, got e = %r" % (e,))
    return a * (1.0 - e), a * (1.0 + e)


def keplerian_elements(r, v, mu=MU):
    """Full rv2coe pack: classical orbital elements from a state vector.

    Returns a dict with h, n, e_vec, a (km), e, i, raan, argp, nu
    (radians), period (s), rp and ra (km). Raises ValueError for
    invalid inputs, rectilinear trajectories, and non-elliptical
    (parabolic or hyperbolic) orbits.
    """
    r = _as_vec(r, "r")
    v = _as_vec(v, "v")
    _check_mu(mu)
    h = specific_angular_momentum(r, v)
    e_vec = eccentricity_vector(r, v, mu)
    e = norm(e_vec)
    eps = specific_energy(r, v, mu)
    if eps >= 0.0:
        raise ValueError(
            "non-elliptical orbit: specific energy %r >= 0 (parabolic or "
            "hyperbolic)" % (eps,)
        )
    a = -mu / (2.0 * eps)
    i = inclination(h)
    omega = raan(h)
    argp = argument_of_periapsis(h, e_vec)
    nu = true_anomaly(h, e_vec, r, v)
    period = orbital_period(a, mu)
    rp, ra = periapsis_apoapsis_radii(a, e)
    return {
        "h": h,
        "n": node_vector(h),
        "e_vec": e_vec,
        "a": a,
        "e": e,
        "i": i,
        "raan": omega,
        "argp": argp,
        "nu": nu,
        "period": period,
        "rp": rp,
        "ra": ra,
    }

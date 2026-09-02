"""Lambert transfer math: two-position, time-of-flight orbit transfers.

Deterministic, offline, stdlib-only solver for Lambert's problem: given two
position vectors r1 and r2 and a transfer time tof, find the conic orbit
that connects the two points in that time. Uses the p-iteration method:
for a trial semilatus rectum p the orbit through the two points is fully
determined, the time of flight follows from Kepler's equation through the
eccentric anomalies at both endpoints, and p is iterated (bracketed scan
plus bisection on the time residual) until the computed time matches the
requested time. Returns the velocity vectors at both endpoints, the
transfer delta-v against circular parking orbits, and the transfer orbit
elements (semimajor axis, eccentricity, semilatus rectum, true and
eccentric anomalies).

Branches: direction="short" sweeps the small transfer angle, direction
"long" sweeps the complementary angle. A 180-degree transfer (r2 anti-
parallel to r1) degenerates to the Hohmann transfer and is solved in
closed form as a sanity check. Multi-revolution transfers (tof larger
than the single-arc maximum) are supported through max_revs extra full
revolutions: tof = M * period + arc_time.

Units: distances in km, mu in km^3/s^2, velocities in km/s, times in
seconds, angles in radians. MU_EARTH = 398600.4418 km^3/s^2.

Contract exercised by scripts/test_lambert_transfer.py.
"""

import math

MU_EARTH = 398600.4418  # Earth gravitational parameter, km^3/s^2


def circular_velocity(radius, mu=MU_EARTH):
    """Return the circular orbit speed in km/s at the given radius.

    v = sqrt(mu / r). An orbit at 7000 km radius flies at about 7.546
    km/s.

    Raises ValueError for a non-positive radius or mu.
    """
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return math.sqrt(mu / radius)


def vis_viva_velocity(radius, semimajor_axis, mu=MU_EARTH):
    """Return the vis-viva speed in km/s at the given radius on the orbit.

    v = sqrt(mu * (2 / r - 1 / a)). On the transfer ellipse this gives
    the speed at either endpoint; the squares of the returned endpoint
    velocity magnitudes must match this value (energy consistency).

    Raises ValueError for a non-positive radius, semimajor axis, or mu.
    """
    if radius <= 0:
        raise ValueError("radius must be > 0, got %r" % (radius,))
    if semimajor_axis <= 0:
        raise ValueError("semimajor axis must be > 0, got %r" % (semimajor_axis,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    return math.sqrt(mu * (2.0 / radius - 1.0 / semimajor_axis))


def eccentric_anomaly(nu, e):
    """Return the eccentric anomaly E in radians for true anomaly nu.

    tan(E / 2) = sqrt((1 - e) / (1 + e)) * tan(nu / 2), quadrant-corrected
    with atan2 so E stays continuous in nu (returns in (-2*pi, 2*pi)).
    """
    return 2.0 * math.atan2(
        math.sqrt(1.0 - e) * math.sin(0.5 * nu),
        math.sqrt(1.0 + e) * math.cos(0.5 * nu),
    )


def analytic_time(a, e, nu1, nu2, mu=MU_EARTH):
    """Return the arc time of flight in seconds from nu1 to nu2.

    Kepler's equation on the ellipse with semimajor axis a and
    eccentricity e: t = sqrt(a^3 / mu) * ((E2 - E1) - e (sin E2 - sin E1)),
    with E unwrapped so the arc is the positive sweep nu2 - nu1 in
    (0, 2*pi). Used to build analytic anchors for the Lambert solver.

    Raises ValueError for a non-positive a, an out-of-range e, or a
    non-positive mu.
    """
    if a <= 0:
        raise ValueError("semimajor axis must be > 0, got %r" % (a,))
    if not (0.0 <= e < 1.0):
        raise ValueError("eccentricity must be in [0, 1), got %r" % (e,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    E1 = eccentric_anomaly(nu1, e)
    E2 = eccentric_anomaly(nu2, e)
    while E2 - E1 <= 0.0:
        E2 += 2.0 * math.pi
    return math.sqrt(a ** 3 / mu) * ((E2 - E1) - e * (math.sin(E2) - math.sin(E1)))


def _transfer_geometry(r1, r2):
    """Return (r1m, r2m, delta_geom): the two radii and the geometric
    angle between the position vectors in [0, pi] radians."""
    r1m = math.sqrt(r1[0] * r1[0] + r1[1] * r1[1] + r1[2] * r1[2])
    r2m = math.sqrt(r2[0] * r2[0] + r2[1] * r2[1] + r2[2] * r2[2])
    dot = r1[0] * r2[0] + r1[1] * r2[1] + r1[2] * r2[2]
    cosd = max(-1.0, min(1.0, dot / (r1m * r2m)))
    return r1m, r2m, math.acos(cosd)


def _p_bracket(r1m, r2m, delta):
    """Return the elliptic semilatus rectum range (p_lo, p_hi) for the
    sweep angle delta (radians). The conic through the two points is an
    ellipse exactly when e^2(p) < 1, which brackets p between the two
    roots of e^2(p) = 1 (the parabolic limits)."""
    A = 0.5 * (1.0 / r1m + 1.0 / r2m)
    B = 0.5 * (1.0 / r1m - 1.0 / r2m)
    cd2 = math.cos(0.5 * delta)
    sd2 = math.sin(0.5 * delta)
    alpha = (A / cd2) ** 2 + (B / sd2) ** 2
    beta = -2.0 * A / (cd2 * cd2)
    gamma = 1.0 / (cd2 * cd2) - 1.0
    disc = beta * beta - 4.0 * alpha * gamma
    if disc <= 0.0:
        raise ValueError("no elliptic conic connects the two positions")
    p_lo = (-beta - math.sqrt(disc)) / (2.0 * alpha)
    p_hi = (-beta + math.sqrt(disc)) / (2.0 * alpha)
    return p_lo, p_hi


def _orbit_for_p(p, r1m, r2m, delta, mu):
    """Return (t, a, e, nu1, nu2, E1, E2) for the conic with semilatus
    rectum p, or None when the conic is not elliptic.

    From the conic geometry: e cos(nu_mid) = (A p - 1) / cos(delta/2) and
    e sin(nu_mid) = (B p) / sin(delta/2) with A, B the mean and half-
    difference of the reciprocal radii; then nu1 = nu_mid - delta/2,
    nu2 = nu_mid + delta/2 and the time of flight follows from Kepler's
    equation.
    """
    A = 0.5 * (1.0 / r1m + 1.0 / r2m)
    B = 0.5 * (1.0 / r1m - 1.0 / r2m)
    cd2 = math.cos(0.5 * delta)
    sd2 = math.sin(0.5 * delta)
    ec_m = (A * p - 1.0) / cd2  # e cos(nu_mid)
    es_m = (B * p) / sd2  # e sin(nu_mid)
    e2 = ec_m * ec_m + es_m * es_m
    if e2 >= 1.0:
        return None
    e = math.sqrt(e2)
    a = p / (1.0 - e2)
    nu_mid = math.atan2(es_m, ec_m)
    nu1 = nu_mid - 0.5 * delta
    nu2 = nu_mid + 0.5 * delta
    E1 = eccentric_anomaly(nu1, e)
    E2 = eccentric_anomaly(nu2, e)
    while E2 - E1 <= 0.0:
        E2 += 2.0 * math.pi
    t = math.sqrt(a ** 3 / mu) * ((E2 - E1) - e * (math.sin(E2) - math.sin(E1)))
    return (t, a, e, nu1, nu2, E1, E2)


def _roots(lo, hi, g, n):
    """Return the roots of g(p) over [lo, hi], scanning n samples and
    bisecting every sign change. Deterministic, offline, stdlib-only."""
    roots = []
    step = (hi - lo) / n
    prev_p = lo
    prev_g = g(lo)
    if not math.isfinite(prev_g):
        prev_g = 1e300 if prev_g > 0 else -1e300
    for i in range(1, n + 1):
        p = lo + step * i
        gp = g(p)
        if not math.isfinite(gp):
            gp = 1e300 if gp > 0 else -1e300
        if prev_g == 0.0:
            roots.append(prev_p)
        elif gp == 0.0:
            roots.append(p)
        elif prev_g * gp < 0.0:
            a_lo, a_hi = prev_p, p
            f_lo, f_hi = prev_g, gp
            for _ in range(80):
                mid = 0.5 * (a_lo + a_hi)
                fm = g(mid)
                if not math.isfinite(fm):
                    fm = 1e300 if fm > 0 else -1e300
                if f_lo * fm <= 0.0:
                    a_hi, f_hi = mid, fm
                else:
                    a_lo, f_lo = mid, fm
            roots.append(0.5 * (a_lo + a_hi))
        prev_p, prev_g = p, gp
    return roots


def _solve_p(r1m, r2m, delta, tof, mu, max_revs):
    """Iterate on the semilatus rectum p until the time of flight matches
    tof. Returns (p, revs). When two elliptic solutions exist the
    highest-p solution (periapsis outside the transfer arc) is returned.
    With max_revs > 0 a multi-revolution transfer is preferred: the
    smallest M in 1..max_revs with a solution of t_arc(p) + M*T(p) = tof
    is returned; otherwise the direct single-revolution transfer is
    used."""
    p_lo, p_hi = _p_bracket(r1m, r2m, delta)
    pad = 1e-9
    lo = p_lo + (p_hi - p_lo) * pad
    hi = p_hi - (p_hi - p_lo) * pad

    def orbit(p):
        return _orbit_for_p(p, r1m, r2m, delta, mu)

    def arc_time(p):
        o = orbit(p)
        return o[0] if o is not None else float("inf")

    # Multi-revolution branch (extension): t_arc(p) + M * T(p) = tof.
    if max_revs > 0:
        for revs in range(1, max_revs + 1):
            def residual(p):
                o = orbit(p)
                if o is None:
                    return float("inf")
                t, a = o[0], o[1]
                period = 2.0 * math.pi * math.sqrt(a ** 3 / mu)
                return t + revs * period - tof

            roots = _roots(lo, hi, residual, 400)
            if roots:
                return roots[-1], revs
    # Direct single-revolution transfer: solve t_arc(p) - tof = 0.
    roots = _roots(lo, hi, lambda p: arc_time(p) - tof, 400)
    if roots:
        return roots[-1], 0
    raise ValueError(
        "no elliptic transfer matches the time of flight %.3f s (below the "
        "minimum arc time for this geometry)" % tof
    )


def _velocities(r1, r2, r1m, r2m, delta, direction, a, e, p, nu1, nu2, mu):
    """Return (v1, v2, delta_v): the endpoint velocity vectors in km/s and
    the transfer delta-v against circular parking orbits.

    Radial and transverse components on the conic: v_r = sqrt(mu/p) e sin
    nu and v_theta = sqrt(mu/p) (1 + e cos nu), resolved in the motion
    frame xhat = r1/r1m, mhat = direction of motion. delta_v assumes
    circular parking orbits in the transfer plane whose motion matches
    the transfer direction: dv1 = |v1 - v_circ1| and dv2 = |v2 - v_circ2|
    as vector differences, which reduces to the Hohmann impulses when the
    radial components vanish (the 180-degree case).
    """
    xhat = (r1[0] / r1m, r1[1] / r1m, r1[2] / r1m)
    cx = r1[1] * r2[2] - r1[2] * r2[1]
    cy = r1[2] * r2[0] - r1[0] * r2[2]
    cz = r1[0] * r2[1] - r1[1] * r2[0]
    nm = math.sqrt(cx * cx + cy * cy + cz * cz)
    zhat = (cx / nm, cy / nm, cz / nm)
    yhat = (
        zhat[1] * xhat[2] - zhat[2] * xhat[1],
        zhat[2] * xhat[0] - zhat[0] * xhat[2],
        zhat[0] * xhat[1] - zhat[1] * xhat[0],
    )
    mhat = yhat if direction == "short" else (-yhat[0], -yhat[1], -yhat[2])

    vp = math.sqrt(mu / p)
    vr1 = vp * e * math.sin(nu1)
    vt1 = vp * (1.0 + e * math.cos(nu1))
    vr2 = vp * e * math.sin(nu2)
    vt2 = vp * (1.0 + e * math.cos(nu2))

    cd = math.cos(delta)
    sd = math.sin(delta)
    # Motion-frame components: rhat2 = cos(d) xhat + sin(d) mhat and
    # thathat2 = -sin(d) xhat + cos(d) mhat.
    v2x = vr2 * cd - vt2 * sd
    v2m = vr2 * sd + vt2 * cd
    v1 = (vr1 * xhat[0] + vt1 * mhat[0],
          vr1 * xhat[1] + vt1 * mhat[1],
          vr1 * xhat[2] + vt1 * mhat[2])
    v2 = (v2x * xhat[0] + v2m * mhat[0],
          v2x * xhat[1] + v2m * mhat[1],
          v2x * xhat[2] + v2m * mhat[2])

    vc1 = circular_velocity(r1m, mu)
    vc2 = circular_velocity(r2m, mu)
    dv1 = math.sqrt(vr1 * vr1 + (vt1 - vc1) ** 2)
    dv2 = math.sqrt(vr2 * vr2 + (vt2 - vc2) ** 2)
    return v1, v2, dv1 + dv2


def _hohmann_180(r1, r2, r1m, r2m, mu):
    """180-degree transfer (r2 anti-parallel to r1): the Hohmann case.

    The transfer ellipse has periapsis at the smaller radius and
    apoapsis at the larger, the one-way time is half the ellipse period,
    and the two endpoint speeds follow from vis-viva. For equal radii the
    ellipse degenerates to the original circular orbit and the transfer
    is a half-orbit coast with zero delta-v.
    """
    a = 0.5 * (r1m + r2m)
    e = abs(r2m - r1m) / (r1m + r2m)
    p = a * (1.0 - e * e)
    t = math.pi * math.sqrt(a ** 3 / mu)
    v1 = vis_viva_velocity(r1m, a, mu)
    v2 = vis_viva_velocity(r2m, a, mu)
    outward = r1m <= r2m
    nu1 = 0.0 if outward else math.pi
    nu2 = math.pi if outward else 2.0 * math.pi

    xhat = (r1[0] / r1m, r1[1] / r1m, r1[2] / r1m)
    ref = (0.0, 0.0, 1.0) if abs(xhat[2]) < 0.9 else (0.0, 1.0, 0.0)
    mx = ref[1] * xhat[2] - ref[2] * xhat[1]
    my = ref[2] * xhat[0] - ref[0] * xhat[2]
    mz = ref[0] * xhat[1] - ref[1] * xhat[0]
    nm = math.sqrt(mx * mx + my * my + mz * mz)
    mhat = (mx / nm, my / nm, mz / nm)
    v1v = (v1 * mhat[0], v1 * mhat[1], v1 * mhat[2])
    v2v = (-v2 * mhat[0], -v2 * mhat[1], -v2 * mhat[2])

    vc1 = circular_velocity(r1m, mu)
    vc2 = circular_velocity(r2m, mu)
    dv = abs(v1 - vc1) + abs(v2 - vc2)
    return {
        "p": p,
        "a": a,
        "e": e,
        "nu1": nu1,
        "nu2": nu2,
        "E1": nu1,
        "E2": nu2,
        "t": t,
        "period": 2.0 * math.pi * math.sqrt(a ** 3 / mu),
        "revs": 0,
        "delta": math.pi,
        "delta_geom": math.pi,
        "chord": r1m + r2m,
        "r1m": r1m,
        "r2m": r2m,
        "v1": v1v,
        "v2": v2v,
        "delta_v": dv,
        "epsilon": -mu / (2.0 * a),
        "direction": "short",
    }


def lambert_solve(r1, r2, tof, mu=MU_EARTH, direction="short", max_revs=0):
    """Solve Lambert's problem: the orbit connecting r1 to r2 in time tof.

    r1 and r2 are 3-vectors in km, tof is the transfer time in seconds,
    mu is the gravitational parameter in km^3/s^2, direction is "short"
    or "long", and max_revs allows extra full revolutions (multi-
    revolution transfers). Returns a dict with the orbit elements (p, a,
    e), the endpoint true and eccentric anomalies, the solved time and
    period, the revolution count, the sweep angle, the endpoint velocity
    vectors v1 and v2 (km/s), the transfer delta_v (km/s) against
    circular parking orbits, and the specific orbital energy.

    A 180-degree transfer (r2 = -r1 up to scale) is the degenerate
    Hohmann case and is solved in closed form; collinear position
    vectors, non-positive tof or mu, and infeasible transfer times raise
    ValueError.
    """
    if tof <= 0:
        raise ValueError("tof must be > 0, got %r" % (tof,))
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    if direction not in ("short", "long"):
        raise ValueError("direction must be 'short' or 'long', got %r" % (direction,))
    if not isinstance(max_revs, int) or max_revs < 0:
        raise ValueError("max_revs must be a non-negative integer, got %r" % (max_revs,))
    if len(r1) != 3 or len(r2) != 3:
        raise ValueError("position vectors must be 3D, got lengths %d and %d"
                         % (len(r1), len(r2)))
    r1m = math.sqrt(r1[0] * r1[0] + r1[1] * r1[1] + r1[2] * r1[2])
    r2m = math.sqrt(r2[0] * r2[0] + r2[1] * r2[1] + r2[2] * r2[2])
    if r1m == 0.0:
        raise ValueError("r1 must be a non-zero vector")
    if r2m == 0.0:
        raise ValueError("r2 must be a non-zero vector")

    r1m, r2m, delta_geom = _transfer_geometry(r1, r2)
    if abs(delta_geom - math.pi) < 1e-9:
        # 180-degree transfer: the Hohmann case, closed form.
        return _hohmann_180(r1, r2, r1m, r2m, mu)
    if math.sin(delta_geom) < 1e-9:
        raise ValueError(
            "position vectors are collinear: no unique transfer plane and no "
            "well-defined transfer angle"
        )

    delta = delta_geom if direction == "short" else 2.0 * math.pi - delta_geom
    chord = math.sqrt(
        r1m * r1m + r2m * r2m - 2.0 * r1m * r2m * math.cos(delta_geom)
    )
    p, revs = _solve_p(r1m, r2m, delta, tof, mu, max_revs)
    orbit = _orbit_for_p(p, r1m, r2m, delta, mu)
    if orbit is None:
        raise ValueError("solver converged to a non-elliptic conic; retry")
    t, a, e, nu1, nu2, E1, E2 = orbit
    v1, v2, dv = _velocities(r1, r2, r1m, r2m, delta, direction, a, e, p, nu1, nu2, mu)
    return {
        "p": p,
        "a": a,
        "e": e,
        "nu1": nu1,
        "nu2": nu2,
        "E1": E1,
        "E2": E2,
        "t": t,
        "period": 2.0 * math.pi * math.sqrt(a ** 3 / mu),
        "revs": revs,
        "delta": delta,
        "delta_geom": delta_geom,
        "chord": chord,
        "r1m": r1m,
        "r2m": r2m,
        "v1": v1,
        "v2": v2,
        "delta_v": dv,
        "epsilon": -mu / (2.0 * a),
        "direction": direction,
    }


def demo():
    """Demonstration: run the 180-degree Hohmann sanity checks and one
    generic short-way transfer, printing the key results."""
    print("Lambert transfer demo (mu = %s km^3/s^2)" % MU_EARTH)
    print()
    # 1) 180-degree same-radius case: half a circular orbit coast.
    r1 = (7000.0, 0.0, 0.0)
    r2 = (-7000.0, 0.0, 0.0)
    tof = math.pi * math.sqrt(7000.0 ** 3 / MU_EARTH)
    res = lambert_solve(r1, r2, tof)
    print("Case 1: 180-degree transfer at 7000 km radius (half-orbit coast)")
    print("  time of flight  : %.1f s (half the orbit period %.1f s)"
          % (res["t"], res["period"]))
    print("  delta-v         : %.6f km/s (Hohmann total for equal radii)"
          % res["delta_v"])
    print("  endpoint speed  : %.4f km/s (circular)"
          % math.sqrt(sum(c * c for c in res["v1"])))
    print()
    # 2) 180-degree low-earth to geostationary: the Hohmann transfer.
    r1 = (6878.0, 0.0, 0.0)
    r2 = (-42164.0, 0.0, 0.0)
    a = 0.5 * (6878.0 + 42164.0)
    tof = math.pi * math.sqrt(a ** 3 / MU_EARTH)
    res = lambert_solve(r1, r2, tof)
    print("Case 2: 180-degree LEO-to-GEO transfer (the Hohmann case)")
    print("  semimajor axis  : %.1f km, eccentricity %.5f" % (res["a"], res["e"]))
    print("  time of flight  : %.1f s (about %.2f h)" % (res["t"], res["t"] / 3600.0))
    print("  delta-v         : %.4f km/s (about 3.82 km/s)"
          % res["delta_v"])
    print()
    # 3) Generic short-way transfer: 120-degree arc between two radii.
    a = 20000.0
    e = 0.4
    p = a * (1.0 - e * e)
    nu1 = math.radians(30.0)
    nu2 = math.radians(150.0)
    r1m = p / (1.0 + e * math.cos(nu1))
    r2m = p / (1.0 + e * math.cos(nu2))
    r1 = (r1m * math.cos(nu1), r1m * math.sin(nu1), 0.0)
    r2 = (r2m * math.cos(nu2), r2m * math.sin(nu2), 0.0)
    tof = analytic_time(a, e, nu1, nu2)
    res = lambert_solve(r1, r2, tof, direction="short")
    print("Case 3: short-way 120-degree transfer between radii %.0f and %.0f km"
          % (r1m, r2m))
    print("  semimajor axis  : %.1f km (target 20000), eccentricity %.4f (target 0.4)"
          % (res["a"], res["e"]))
    print("  time of flight  : %.1f s (about %.2f h)" % (res["t"], res["t"] / 3600.0))
    print("  delta-v         : %.4f km/s" % res["delta_v"])
    print("  v1 = (%.4f, %.4f, %.4f) km/s" % res["v1"])
    print("  v2 = (%.4f, %.4f, %.4f) km/s" % res["v2"])


if __name__ == "__main__":
    demo()

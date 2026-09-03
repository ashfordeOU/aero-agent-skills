"""Deterministic three-vector initial orbit determination (pure stdlib).

Implements the classical Gibbs method and the Herrick-Gibbs
finite-difference method for preliminary orbit determination from three
inertial position vectors (ECI J2000 assumed, geocentric), followed by
conversion of the recovered state to classical orbital elements with a
vis-viva energy consistency check.

No propagation, no stochastic estimation, no Lambert targeting. This is
the deterministic three-vector initial orbit determination classic.
"""

import math

MU = 3.986004418e14  # Earth gravitational parameter, m^3/s^2 (ECSS context)
DEFAULT_AREA_THRESHOLD = 1.0e12  # m^2, triangle-area cutoff for method choice


def cross3(u, v):
    """Cross product of two 3-vectors, each a length-3 iterable."""
    return [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    ]


def norm3(v):
    """Euclidean norm of a 3-vector."""
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _check_positions(r1, r2, r3):
    """Validate three position vectors: finite, non-zero norm."""
    for label, r in (("r1", r1), ("r2", r2), ("r3", r3)):
        if len(r) != 3:
            raise ValueError(label + " must have three components")
        for c in r:
            if not math.isfinite(c):
                raise ValueError(label + " contains a non-finite component")
        mag = norm3(r)
        if mag <= 0.0:
            raise ValueError(label + " has a non-positive radius")


def _check_times(t1, t2, t3):
    """Validate time tags: finite and strictly increasing."""
    for label, t in (("t1", t1), ("t2", t2), ("t3", t3)):
        if not math.isfinite(t):
            raise ValueError(label + " must be finite")
    if not (t1 < t2 < t3):
        raise ValueError("time tags must be strictly increasing (repeated tags rejected)")


def gibbs_velocity(r1, r2, r3):
    """Gibbs method: velocity at r2 from three inertial position vectors.

    Vallado classical form. N and D both vanish as the three vectors
    approach collinear geometry, so a near-zero norm raises ValueError.
    Returns the velocity vector at r2, m/s.
    """
    _check_positions(r1, r2, r3)
    n1 = norm3(r1)
    n2 = norm3(r2)
    n3 = norm3(r3)
    c12 = cross3(r1, r2)
    c23 = cross3(r2, r3)
    c31 = cross3(r3, r1)
    n_vec = [n1 * c23[i] + n2 * c31[i] + n3 * c12[i] for i in range(3)]
    d_vec = [c12[i] + c23[i] + c31[i] for i in range(3)]
    s_vec = [
        r1[i] * (n2 - n3) + r2[i] * (n3 - n1) + r3[i] * (n1 - n2)
        for i in range(3)
    ]
    n_mag = norm3(n_vec)
    d_mag = norm3(d_vec)
    if n_mag < 1.0e-6 or d_mag < 1.0e-6:
        raise ValueError("near-collinear observation geometry (N or D vanishes)")
    coef = math.sqrt(MU / (n_mag * d_mag))
    # d x r2 term, then add S
    dr = cross3(d_vec, r2)
    return [coef * (dr[i] / n2 + s_vec[i]) for i in range(3)]


def herrick_gibbs_velocity(r1, r2, r3, t1, t2, t3):
    """Herrick-Gibbs: finite-difference velocity at r2 for close vectors.

    Standard three-vector finite-difference formula (Vallado, Curtis)
    with the mu/12 correction term, valid when the angular separation
    is small. Middle coefficient is (dt23 - dt12), which vanishes for
    equally spaced tags and reduces the formula to the central
    difference limit. NOTE: the draft wave-24r spec printed (dt13 -
    dt12) for the middle term; that form is dimensionally wrong and
    reproduces neither Gibbs nor the classical Herrick-Gibbs result,
    so the standard (dt23 - dt12) coefficient is implemented here.
    """
    _check_positions(r1, r2, r3)
    _check_times(t1, t2, t3)
    dt12 = t2 - t1
    dt23 = t3 - t2
    dt13 = t3 - t1
    c1 = -dt23 * (1.0 / (dt12 * dt13) + MU / (12.0 * norm3(r1) ** 3))
    c2 = (dt23 - dt12) * (1.0 / (dt12 * dt23) + MU / (12.0 * norm3(r2) ** 3))
    c3 = dt12 * (1.0 / (dt13 * dt23) + MU / (12.0 * norm3(r3) ** 3))
    return [c1 * r1[i] + c2 * r2[i] + c3 * r3[i] for i in range(3)]


def choose_method(r1, r2, r3, t1, t2, t3, area_threshold=DEFAULT_AREA_THRESHOLD):
    """Choose 'gibbs' or 'hg' from the triangle area between the vectors.

    The triangle area spanned by the three positions is |(r2-r1) x
    (r3-r1)|/2. Small area means closely spaced (nearly coplanar line)
    vectors, where Herrick-Gibbs is preferred; otherwise Gibbs.
    """
    _check_positions(r1, r2, r3)
    _check_times(t1, t2, t3)
    if area_threshold <= 0.0:
        raise ValueError("area_threshold must be positive")
    a = cross3([r2[i] - r1[i] for i in range(3)],
               [r3[i] - r1[i] for i in range(3)])
    area = 0.5 * norm3(a)
    if area < area_threshold:
        return "hg"
    return "gibbs"


def rv_to_elements(r, v, mu=MU):
    """Classical orbital elements from an inertial state (r, v).

    Returns a dict with a (semi-major axis, m), e, i_deg, raan_deg,
    argp_deg, nu_deg and period_s. Equatorial and circular special
    cases follow the usual conventions: i near 0 gives raan_deg 0,
    circular orbits give argp_deg and nu_deg measured from the node.
    """
    _check_positions(r, (v[0], v[1], v[2]), (1.0, 0.0, 0.0))
    for c in v:
        if not math.isfinite(c):
            raise ValueError("velocity contains a non-finite component")
    rm = norm3(r)
    vm = norm3(v)
    h = cross3(r, v)
    hm = norm3(h)
    if hm < 1.0e-9:
        raise ValueError("state is degenerate: zero angular momentum")
    k_hat = [0.0, 0.0, 1.0]
    n_vec = cross3(k_hat, h)  # ascending node vector
    nm = norm3(n_vec)
    energy = 0.5 * vm * vm - mu / rm
    e_vec = [
        ((vm * vm - mu / rm) * r[i] - (r[0] * v[0] + r[1] * v[1] + r[2] * v[2]) * v[i])
        / mu for i in range(3)
    ]
    e = norm3(e_vec)
    if abs(energy) < 1.0e-12:
        raise ValueError("state is parabolic: energy check undefined")
    a = -mu / (2.0 * energy)
    i_deg = math.degrees(math.acos(max(-1.0, min(1.0, h[2] / hm))))
    if nm < 1.0e-9:  # equatorial orbit: node undefined, convention 0
        raan_deg = 0.0
    else:
        raan = math.acos(max(-1.0, min(1.0, n_vec[0] / nm)))
        raan_deg = math.degrees(raan if n_vec[1] >= 0.0 else 2.0 * math.pi - raan)
    if e < 1.0e-9:  # circular orbit: argp undefined, measure nu from node
        argp_deg = 0.0
        nu_deg = _angle_from(n_vec, r, nm, rm) if nm >= 1.0e-9 else 0.0
    elif nm < 1.0e-9:  # equatorial with e > 0: argp measured from +x axis
        argp_deg = _angle_from([1.0, 0.0, 0.0], e_vec, 1.0, e)
        nu_deg = _angle_from(e_vec, r, e, rm)
    else:
        argp_deg = _angle_from(n_vec, e_vec, nm, e)
        nu_deg = _angle_from(e_vec, r, e, rm)
    period_s = 2.0 * math.pi * math.sqrt(abs(a) ** 3 / mu)
    return {
        "a": a,
        "e": e,
        "i_deg": i_deg,
        "raan_deg": raan_deg,
        "argp_deg": argp_deg,
        "nu_deg": nu_deg,
        "period_s": period_s,
    }


def _angle_from(u, w, um, wm):
    """Angle between vectors u and w (0..360 deg, signed by w's z axis)."""
    dot = (u[0] * w[0] + u[1] * w[1] + u[2] * w[2]) / (um * wm)
    ang = math.acos(max(-1.0, min(1.0, dot)))
    return math.degrees(ang if w[2] >= 0.0 else 2.0 * math.pi - ang)


def orbit_determination(r1, r2, r3, t1, t2, t3,
                        area_threshold=DEFAULT_AREA_THRESHOLD, mu=MU):
    """Full three-vector initial orbit determination summary.

    Chooses the method (Gibbs or Herrick-Gibbs), recovers the velocity
    at the central observation, converts to classical orbital elements,
    checks vis-viva energy consistency and returns a verdict.
    """
    method = choose_method(r1, r2, r3, t1, t2, t3, area_threshold)
    if method == "hg":
        v2 = herrick_gibbs_velocity(r1, r2, r3, t1, t2, t3)
    else:
        v2 = gibbs_velocity(r1, r2, r3)
    elements = rv_to_elements(r2, v2, mu)
    rm = norm3(r2)
    vm = norm3(v2)
    vis_viva = 0.5 * vm * vm - mu / rm
    energy_target = -mu / (2.0 * elements["a"])
    rel_err = abs(vis_viva - energy_target) / abs(energy_target)
    verdict = "consistent" if rel_err < 1.0e-6 else "inconsistent"
    return {
        "method": method,
        "v2": v2,
        "elements": elements,
        "energy_check": vis_viva,
        "energy_target": energy_target,
        "energy_rel_error": rel_err,
        "verdict": verdict,
    }



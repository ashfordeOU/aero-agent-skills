#!/usr/bin/env python3
"""Gust and maneuver load factor analysis per FAR 25.341 and FAR 25.337.

Common-knowledge summary (standards-map.yaml, far-25: gated false, see
references/far-25-loads.md for the paraphrased requirement summary):

Discrete gust model (FAR 25.341): the airplane is subjected to a
1-cosine discrete gust of design velocity U_de at equivalent airspeed
V_e, and the resulting (positive) limit gust load factor is

    n = 1 + (rho0 * V_e * a * K_g * U_de) / (2 * W/S)

with rho0 the sea-level standard density (0.002378 slugs/ft^3), V_e in
ft/s (EAS), a the lift-curve slope per radian, U_de in ft/s (EAS), and
W/S the wing loading in lb/ft^2. With V in knots the same factor reads
n = 1 + (K_g * U_de * V_KEAS * a) / (498 * W/S). The gust alleviation
factor (FAR 25.341(b)(2)) is

    K_g = 0.88 * mu_g / (5.3 + mu_g),
    mu_g = 2 * (W/S) / (rho * cbar * a * g)

where mu_g is the mass ratio evaluated at the flight altitude density
rho (sea level by default), cbar the mean geometric chord in ft, and
g the gravitational acceleration in ft/s^2.

Design gust velocities (FAR 25.341(a), fps EAS): 66 fps between VB and
VC at sea level (linear to 38 fps at 15,000 ft), 50 fps at VC at sea
level (linear to 25 fps at 15,000 ft), 25 fps at VD at sea level (linear
to 12.5 fps at 50,000 ft).

Maneuver loads (FAR 25.337): the positive limit maneuvering load factor
at the design maneuvering speed VA is 2.5 for normal category airplanes
and 3.8 for commuter category and transport category airplanes; it
varies linearly with speed from the VA value down to 0 at VD (FAR
25.333(b)). The negative limit maneuvering load factor is -1.0 at speeds
up to VC, varying linearly to 0 at VD (FAR 25.333(c)).

Units are US customary throughout, consistent with the transport
certification practice the equations come from: speeds in ft/s (or KEAS
where noted), densities in slugs/ft^3, wing loading W/S in lb/ft^2,
chord in ft, lift-curve slope a per radian. Invalid inputs raise
ValueError throughout.
"""

import math

# Sea-level standard air density, slugs/ft^3. FAR 25.341 uses rho0 with
# equivalent airspeed so the gust equation holds at any altitude.
RHO0 = 0.002378

# Standard gravitational acceleration, ft/s^2.
G = 32.174

# FAR 25.341(a) design gust velocities at sea level, fps EAS.
FAR25_GUST_VELOCITY_SEA_LEVEL = {
    "vb-vc": 66.0,  # (a)(6): between VB and VC
    "vc": 50.0,     # (a)(4): at VC
    "vd": 25.0,     # (a)(5): at VD
}

# Design gust velocities at the FAR altitude floors, fps EAS.
FAR25_GUST_VELOCITY_FLOOR = {
    "vb-vc": 38.0,   # at 15,000 ft
    "vc": 25.0,      # at 15,000 ft
    "vd": 12.5,      # at 50,000 ft
}

# Altitude (ft) at which each gust velocity reaches its floor value.
FAR25_GUST_ALTITUDE_FLOOR = {
    "vb-vc": 15000.0,
    "vc": 15000.0,
    "vd": 50000.0,
}

# Positive limit maneuvering load factor at VA by category, FAR
# 25.337(b)(1): 2.5 for normal, 3.8 for commuter and transport.
MANEUVER_LIMIT_VA = {"normal": 2.5, "commuter": 3.8, "transport": 3.8}

# Negative limit maneuvering load factor, FAR 25.337(b)(2).
NEGATIVE_MANEUVER_LIMIT = -1.0

# Largest discrete design gust velocity in the regulation, fps EAS
# (FAR 25.341(a)(6)). Anything beyond it is an invalid gust velocity.
MAX_GUST_VELOCITY = 66.0


def _require_positive(value, name):
    if value is None:
        raise ValueError("%s is required, got None" % (name,))
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    return value


def _require_nonnegative(value, name):
    if value is None:
        raise ValueError("%s is required, got None" % (name,))
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be numeric, got %r" % (name, value))
    if not math.isfinite(value) or value < 0.0:
        raise ValueError("%s must be nonnegative, got %r" % (name, value))
    return value


def _require_gust_velocity(u_de):
    """Validate a discrete gust velocity: nonzero, |u_de| <= 66 fps EAS."""
    if u_de is None:
        raise ValueError("u_de is required, got None")
    try:
        u = float(u_de)
    except (TypeError, ValueError):
        raise ValueError("u_de must be numeric, got %r" % (u_de,))
    if not math.isfinite(u) or u == 0.0:
        raise ValueError(
            "u_de must be a nonzero finite gust velocity, got %r" % (u_de,))
    if abs(u) > MAX_GUST_VELOCITY:
        raise ValueError(
            "u_de magnitude %.3f fps exceeds the FAR 25.341 maximum "
            "design gust velocity of %.1f fps EAS"
            % (abs(u), MAX_GUST_VELOCITY))
    return u


def far25_gust_velocity(speed_region, altitude_ft=0.0):
    """Design discrete gust velocity U_de (fps EAS) per FAR 25.341(a).

    speed_region is one of "vb-vc", "vc", "vd". The sea-level value
    decreases linearly to the altitude floor value (38 fps at 15,000 ft
    for vb-vc, 25 fps at 15,000 ft for vc, 12.5 fps at 50,000 ft for
    vd); above the floor the floor value applies.
    """
    if speed_region not in FAR25_GUST_VELOCITY_SEA_LEVEL:
        raise ValueError(
            "speed_region must be one of %r, got %r"
            % (tuple(FAR25_GUST_VELOCITY_SEA_LEVEL), speed_region))
    altitude_ft = _require_nonnegative(altitude_ft, "altitude_ft")
    v0 = FAR25_GUST_VELOCITY_SEA_LEVEL[speed_region]
    floor_alt = FAR25_GUST_ALTITUDE_FLOOR[speed_region]
    v_floor = FAR25_GUST_VELOCITY_FLOOR[speed_region]
    if altitude_ft >= floor_alt:
        return v_floor
    return v0 - (v0 - v_floor) * (altitude_ft / floor_alt)


def gust_mass_ratio(ws, cbar, a, rho, g=G):
    """Mass ratio mu_g = 2 * (W/S) / (rho * cbar * a * g), FAR 25.341(b)(2)."""
    ws = _require_positive(ws, "ws")
    cbar = _require_positive(cbar, "cbar")
    a = _require_positive(a, "a")
    rho = _require_positive(rho, "rho")
    g = _require_positive(g, "g")
    return 2.0 * ws / (rho * cbar * a * g)


def gust_alleviation_factor(ws, cbar, a, rho, g=G):
    """Gust alleviation factor K_g = 0.88 * mu_g / (5.3 + mu_g).

    ws is the wing loading W/S in lb/ft^2, cbar the mean geometric chord
    in ft, a the lift-curve slope per radian, rho the density at the
    flight altitude in slugs/ft^3 (sea level by default).
    """
    mu_g = gust_mass_ratio(ws, cbar, a, rho, g)
    return 0.88 * mu_g / (5.3 + mu_g)


def gust_load_factor(ve, ws, a, u_de, rho0=RHO0, kg=None,
                     cbar=None, rho=None, g=G):
    """Discrete gust load factor n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S).

    ve is the equivalent airspeed in ft/s, ws the wing loading W/S in
    lb/ft^2, a the lift-curve slope per radian, u_de the design gust
    velocity in ft/s EAS (negative for a down gust). K_g is either
    passed directly as kg or computed from cbar, rho and g via
    gust_alleviation_factor(). rho0 defaults to the sea-level standard
    density 0.002378 slugs/ft^3, which is the FAR 25.341(b) convention
    paired with equivalent airspeed.
    """
    ve = _require_positive(ve, "ve")
    ws = _require_positive(ws, "ws")
    a = _require_positive(a, "a")
    u = _require_gust_velocity(u_de)
    rho0 = _require_positive(rho0, "rho0")
    if kg is None:
        if cbar is None or rho is None:
            raise ValueError(
                "kg or both cbar and rho must be given to compute K_g")
        kg = gust_alleviation_factor(ws, cbar, a, rho, g)
    kg = _require_positive(kg, "kg")
    return 1.0 + (rho0 * ve * a * kg * u) / (2.0 * ws)


def maneuver_limit_load_factor(category="normal", speed=None,
                               va=None, vd=None, negative=False):
    """Limit maneuvering load factor per FAR 25.337.

    With speed=None returns the plateau value: 2.5 (normal) or 3.8
    (commuter/transport) positive, or -1.0 negative. With a speed and
    the plateau-end speed va plus vd given, returns the value on the
    linear segment: full plateau value up to va, linear to 0 at vd, 0
    at and beyond vd (FAR 25.333(b)). For the negative envelope pass
    negative=True and give va as the plateau end (VC per FAR 25.333(c)).
    """
    if negative:
        n_va = NEGATIVE_MANEUVER_LIMIT
    else:
        try:
            n_va = MANEUVER_LIMIT_VA[category]
        except KeyError:
            raise ValueError(
                "unknown category %r, use one of %r"
                % (category, tuple(MANEUVER_LIMIT_VA)))
    if speed is None:
        return n_va
    speed = _require_positive(speed, "speed")
    if va is None or vd is None:
        raise ValueError("va and vd are required when speed is given")
    va = _require_positive(va, "va")
    vd = _require_positive(vd, "vd")
    if va >= vd:
        raise ValueError(
            "va must be less than vd, got va=%.1f vd=%.1f" % (va, vd))
    if speed <= va:
        return n_va
    if speed >= vd:
        return 0.0
    return n_va * (vd - speed) / (vd - va)


def _gust_point(label, v, u_pos, u_neg, ws, a, rho0, kg):
    return {
        "speed": label,
        "v": v,
        "u_de_pos": _require_gust_velocity(u_pos),
        "u_de_neg": _require_gust_velocity(u_neg),
        "n_pos": gust_load_factor(v, ws, a, u_pos, rho0=rho0, kg=kg),
        "n_neg": gust_load_factor(v, ws, a, u_neg, rho0=rho0, kg=kg),
    }


def vn_diagram(ws, vs, vd, a, cbar, rho=RHO0, rho0=RHO0, g=G,
               category="normal", altitude_ft=0.0,
               vb=None, vc=None,
               u_de_bc=None, u_de_c=None, u_de_d=None,
               u_de_neg_bc=None, u_de_neg_c=None, u_de_neg_d=None):
    """Construct the FAR 25 V-n (flight envelope) diagram as a dict.

    Inputs: ws wing loading (lb/ft^2), vs 1g stall speed (ft/s), vd
    design diving speed (ft/s), a lift-curve slope (1/rad), cbar mean
    geometric chord (ft), rho flight-altitude density for the mass
    ratio (slugs/ft^3, sea level default), rho0 sea-level density used
    by the gust equation, category ("normal", "commuter", "transport"),
    and altitude_ft used to scale the FAR 25.341(a) design gust
    velocities (u_de_bc/u_de_c/u_de_d override them).

    Speeds: va = vs * sqrt(n_VA) is the corner speed; vb defaults to
    1.8*vs (or 1.05*va when larger, as for the 3.8g corner) and vc
    defaults to 2.0*vs (or 1.1*vb when larger). Ordering
    vs < va < vb < vc < vd is enforced.

    Returns a dict with the corner, the limit load factors, the
    maneuver envelope polylines (positive: stall line (vs, 1.0) to
    (va, n_VA) then linear to (vd, 0.0); negative: (vs, -1.0) flat to
    (vc, -1.0) then linear to (vd, 0.0)), the gust points at VB, VC,
    and VD with positive and negative load factors, and the gust
    velocities used.
    """
    ws = _require_positive(ws, "ws")
    vs = _require_positive(vs, "vs")
    vd = _require_positive(vd, "vd")
    a = _require_positive(a, "a")
    cbar = _require_positive(cbar, "cbar")
    rho = _require_positive(rho, "rho")
    rho0 = _require_positive(rho0, "rho0")
    g = _require_positive(g, "g")
    altitude_ft = _require_nonnegative(altitude_ft, "altitude_ft")

    n_pos = maneuver_limit_load_factor(category=category)
    n_neg = maneuver_limit_load_factor(negative=True)
    va = vs * math.sqrt(n_pos)
    if vb is None:
        vb = max(1.8 * vs, 1.05 * va)
    if vc is None:
        vc = max(2.0 * vs, 1.1 * vb)
    if not (vs < va < vb < vc < vd):
        raise ValueError(
            "speed ordering violated: need vs < va < vb < vc < vd, got "
            "vs=%.1f va=%.1f vb=%.1f vc=%.1f vd=%.1f" % (vs, va, vb, vc, vd))

    kg = gust_alleviation_factor(ws, cbar, a, rho, g)
    if u_de_bc is None:
        u_de_bc = far25_gust_velocity("vb-vc", altitude_ft)
    if u_de_c is None:
        u_de_c = far25_gust_velocity("vc", altitude_ft)
    if u_de_d is None:
        u_de_d = far25_gust_velocity("vd", altitude_ft)
    if u_de_neg_bc is None:
        u_de_neg_bc = -u_de_bc
    if u_de_neg_c is None:
        u_de_neg_c = -u_de_c
    if u_de_neg_d is None:
        u_de_neg_d = -u_de_d

    gust_points = [
        _gust_point("VB", vb, u_de_bc, u_de_neg_bc, ws, a, rho0, kg),
        _gust_point("VC", vc, u_de_c, u_de_neg_c, ws, a, rho0, kg),
        _gust_point("VD", vd, u_de_d, u_de_neg_d, ws, a, rho0, kg),
    ]

    return {
        "category": category,
        "ws": ws,
        "vs": vs,
        "va": va,
        "vb": vb,
        "vc": vc,
        "vd": vd,
        "n_positive": n_pos,
        "n_negative": n_neg,
        "mu_g": gust_mass_ratio(ws, cbar, a, rho, g),
        "kg": kg,
        "altitude_ft": altitude_ft,
        "maneuver_envelope": {
            "positive": [(vs, 1.0), (va, n_pos), (vd, 0.0)],
            "negative": [(vs, n_neg), (vc, n_neg), (vd, 0.0)],
        },
        "gust_points": gust_points,
        "gust_velocities": {
            "vb-vc": u_de_bc,
            "vc": u_de_c,
            "vd": u_de_d,
        },
    }


def _positive_limit_at(vn, v):
    """Positive envelope limit load factor at speed v."""
    vs, va, vd = vn["vs"], vn["va"], vn["vd"]
    n_pos = vn["n_positive"]
    if v <= va:
        # Below VA the stall boundary n = (v/vs)^2 limits the load
        # factor before the 2.5g (or 3.8g) plateau does.
        return min(n_pos, (v / vs) ** 2)
    if v >= vd:
        return 0.0
    return n_pos * (vd - v) / (vd - va)


def _negative_limit_at(vn, v):
    """Negative envelope limit load factor at speed v."""
    vs, vc, vd = vn["vs"], vn["vc"], vn["vd"]
    n_neg = vn["n_negative"]
    if v <= vc:
        return max(n_neg, -((v / vs) ** 2))
    if v >= vd:
        return 0.0
    return n_neg * (vd - v) / (vd - vc)


def envelope_verdict(vn, v, n):
    """Judge a flight condition (v, n) against the V-n envelope.

    vn is a diagram dict from vn_diagram(). Returns a dict with inside
    (bool), verdict ("PASS"/"FAIL"), the positive and negative envelope
    limits at speed v, and the fractional margin to the limiting side
    (positive margin means headroom remains, negative means the
    condition exceeds the envelope). Speeds outside [VS, VD] fail.
    """
    if not isinstance(vn, dict) or "vs" not in vn or "vd" not in vn:
        raise ValueError("vn must be a V-n diagram dict from vn_diagram()")
    v = _require_positive(v, "v")
    if n is None:
        raise ValueError("n is required, got None")
    try:
        n = float(n)
    except (TypeError, ValueError):
        raise ValueError("n must be numeric, got %r" % (n,))
    vs, vd = vn["vs"], vn["vd"]
    if v < vs or v > vd:
        return {
            "v": v,
            "n": n,
            "inside": False,
            "verdict": "FAIL",
            "reason": "speed %.1f outside [VS %.1f, VD %.1f]" % (v, vs, vd),
            "n_limit_pos": None,
            "n_limit_neg": None,
            "margin": None,
        }
    n_pos_lim = _positive_limit_at(vn, v)
    n_neg_lim = _negative_limit_at(vn, v)
    inside = n_neg_lim <= n <= n_pos_lim
    if n >= 0.0:
        margin = ((n_pos_lim - n) / n_pos_lim if n_pos_lim > 0.0
                  else (n_pos_lim - n))
    else:
        margin = ((n - n_neg_lim) / abs(n_neg_lim) if n_neg_lim < 0.0
                  else (n - n_neg_lim))
    return {
        "v": v,
        "n": n,
        "inside": inside,
        "verdict": "PASS" if inside else "FAIL",
        "reason": None,
        "n_limit_pos": n_pos_lim,
        "n_limit_neg": n_neg_lim,
        "margin": margin,
    }


def envelope_margins(vn):
    """Margin check: each gust line point vs the maneuver envelope.

    For VB, VC, and VD returns the envelope limit at that speed, the
    gust load factor, and the fractional margin (gust_critical_pos is
    True when the positive gust line exceeds the maneuver envelope at
    that speed, meaning the gust condition drives the design).
    """
    if not isinstance(vn, dict) or "gust_points" not in vn:
        raise ValueError("vn must be a V-n diagram dict from vn_diagram()")
    out = {}
    for point in vn["gust_points"]:
        v = point["v"]
        n_env_pos = _positive_limit_at(vn, v)
        n_env_neg = _negative_limit_at(vn, v)
        n_gust_pos = point["n_pos"]
        n_gust_neg = point["n_neg"]
        margin_pos = ((n_env_pos - n_gust_pos) / n_env_pos
                      if n_env_pos > 0.0 else (n_env_pos - n_gust_pos))
        margin_neg = ((n_gust_neg - n_env_neg) / abs(n_env_neg)
                      if n_env_neg < 0.0 else (n_gust_neg - n_env_neg))
        out[point["speed"]] = {
            "v": v,
            "n_envelope_pos": n_env_pos,
            "n_gust_pos": n_gust_pos,
            "margin_pos": margin_pos,
            "gust_critical_pos": margin_pos < 0.0,
            "n_envelope_neg": n_env_neg,
            "n_gust_neg": n_gust_neg,
            "margin_neg": margin_neg,
            "gust_critical_neg": margin_neg < 0.0,
        }
    return out


if __name__ == "__main__":
    # Typical transport at VB, the worked example in SKILL.md:
    # W/S = 100 psf, cbar = 12.5 ft, a = 5.7/rad, rho = rho0 = 0.002378
    # slugs/ft^3, V_e = 300 KEAS = 506.34 ft/s, U_de = 50 fps EAS.
    vn = vn_diagram(ws=100.0, vs=230.0, vd=621.0, a=5.7, cbar=12.5)
    print("mu_g = %.3f, K_g = %.4f" % (vn["mu_g"], vn["kg"]))
    print("VA = %.1f ft/s (corner, n = %.1f)" % (vn["va"], vn["n_positive"]))
    for p in vn["gust_points"]:
        print("gust %s at v = %.1f ft/s: n_pos = %.3f, n_neg = %.3f"
              % (p["speed"], p["v"], p["n_pos"], p["n_neg"]))
    margins = envelope_margins(vn)
    for key in ("VB", "VC", "VD"):
        m = margins[key]
        print("%s: margin_pos = %+.3f (gust_critical = %s)"
              % (key, m["margin_pos"], m["gust_critical_pos"]))

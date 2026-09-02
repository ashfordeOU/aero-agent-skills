#!/usr/bin/env python3
"""Two-body orbital mechanics logic (paraphrase, common knowledge).

Common-knowledge summary (standards-map.yaml, ecss: free download):
the ECSS series covers space engineering and software; the orbital
mechanics here is textbook two-body dynamics. Vis-viva gives speed from
radius and semi-major axis; a Hohmann transfer is the minimum-energy
coplanar transfer between circular orbits (two burns, half-ellipse
transfer arc); the J2 term drives secular nodal-regression drift that
matters for repeat-ground-track and formation planning.
"""

import math

MU_EARTH = 3.986004418e14  # m^3/s^2


def vis_viva_velocity(r, a, mu=MU_EARTH):
    """Speed (m/s) at radius r on an orbit with semi-major axis a."""
    if r <= 0:
        raise ValueError("radius must be > 0, got %r" % (r,))
    if a <= 0:
        raise ValueError("semi-major axis must be > 0, got %r" % (a,))
    return math.sqrt(mu * (2.0 / r - 1.0 / a))


def hohmann_delta_v(r1, r2, mu=MU_EARTH):
    """(dv1, dv2, dv_total) in m/s for a Hohmann transfer between
    coplanar circular orbits at radii r1 (initial) and r2 (target)."""
    if r1 <= 0 or r2 <= 0:
        raise ValueError("radii must be > 0, got %r, %r" % (r1, r2))
    if r1 == r2:
        raise ValueError("Hohmann transfer requires r1 != r2")
    v1 = math.sqrt(mu / r1)
    v2 = math.sqrt(mu / r2)
    dv1 = v1 * (math.sqrt(2.0 * r2 / (r1 + r2)) - 1.0)
    dv2 = v2 * (1.0 - math.sqrt(2.0 * r1 / (r1 + r2)))
    return (dv1, dv2, dv1 + dv2)


def hohmann_transfer_time(r1, r2, mu=MU_EARTH):
    """Transfer time (s): half the period of the transfer ellipse."""
    if r1 <= 0 or r2 <= 0:
        raise ValueError("radii must be > 0, got %r, %r" % (r1, r2))
    return math.pi * math.sqrt((r1 + r2) ** 3 / (8.0 * mu))


def leo_to_geo_sanity(dv_total_mps):
    """True when the total Hohmann delta-v is in the LEO-to-GEO band
    (about 3.9 km/s; 3500-4300 m/s)."""
    return 3500.0 <= dv_total_mps <= 4300.0


def j2_drift_flag(drift_rate_deg_per_day, allowed=0.05):
    """'ok' when the J2 nodal-regression drift rate (deg/day) is within
    the allowed rate, else 'j2-drift check'."""
    if abs(drift_rate_deg_per_day) <= allowed:
        return "ok"
    return "j2-drift check"

"""Plane change maneuver delta-v math for impulsive inclination changes.

Deterministic, offline, stdlib-only helpers for an orbital plane change
maneuver and its combined-transfer variant: the circular-orbit speed at
the maneuver radius, the pure plane change delta-v 2 v sin(di/2), the
speed on an elliptic transfer orbit at the maneuver point from the
vis-viva equation, the combined-burn delta-v from the law of cosines
when the plane change and the transfer circularization are done in one
burn at the apoapsis, the separate two-burn total, and the
maneuver-selection verdict. Units follow the pack convention: radii and
semimajor axes in km, mu in km^3/s^2, speeds and delta-v in km/s,
angles in degrees.

Contract exercised by scripts/test_plane_change_maneuver.py.
"""

import math

MU_EARTH = 398600.4418  # Earth gravitational parameter, km^3/s^2
DI_LOW = -180.0  # open lower bound of the valid inclination change, deg
DI_HIGH = 180.0  # closed upper bound of the valid inclination change, deg


def circular_orbit_speed(mu, radius_km):
    """Return the circular orbit speed in km/s at the given radius.

    v = sqrt(mu / r). A 300 km circular orbit (radius 6678 km) flies at
    7.7258 km/s and a geostationary orbit at radius 42164 km flies at
    3.0747 km/s.

    Raises ValueError for a non-positive radius or mu.
    """
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0, got %r" % (radius_km,))
    return math.sqrt(mu / radius_km)


def plane_change_dv(speed, inclination_change_deg):
    """Return the pure plane change delta-v in km/s.

    dv = 2 * v * sin(di / 2): the two velocity vectors of equal
    magnitude v separated by the inclination change di, combined by the
    vector law of cosines. A 28.5 deg change at the 7.7258 km/s LEO
    speed costs 3.803 km/s, which is why plane changes are done where
    the orbital speed is low.

    Raises ValueError if inclination_change_deg is not in (-180, 180].
    """
    if not DI_LOW < inclination_change_deg <= DI_HIGH:
        raise ValueError(
            "inclination_change_deg must be in (-180, 180], got %r"
            % (inclination_change_deg,)
        )
    return 2.0 * speed * math.sin(math.pi / 180.0 * inclination_change_deg / 2.0)


def transfer_speed_at_radius(mu, radius_km, semimajor_axis_km):
    """Return the vis-viva speed in km/s on the ellipse at the radius.

    v = sqrt(mu * (2/r - 1/a)) is valid at any point of the transfer
    ellipse, periapsis or apoapsis. For the GTO ellipse of semimajor
    axis 24421 km the speed at the 42164 km apogee is 1.6057 km/s.

    Raises ValueError when the point is not on the ellipse: a
    non-positive radius or semimajor axis, or 2*a <= r (every ellipse
    point satisfies r < 2a), or a non-positive mu.
    """
    if mu <= 0:
        raise ValueError("mu must be > 0, got %r" % (mu,))
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0, got %r" % (radius_km,))
    if semimajor_axis_km <= 0:
        raise ValueError(
            "semimajor_axis_km must be > 0, got %r" % (semimajor_axis_km,)
        )
    if 2.0 * semimajor_axis_km <= radius_km:
        raise ValueError(
            "point off the ellipse: need 2*semimajor_axis_km > radius_km, "
            "got a=%r and r=%r" % (semimajor_axis_km, radius_km)
        )
    return math.sqrt(mu * (2.0 / radius_km - 1.0 / semimajor_axis_km))


def combined_burn_dv(v_before, v_after, inclination_change_deg):
    """Return the one-burn combined delta-v in km/s.

    dv = sqrt(v1^2 + v2^2 - 2 v1 v2 cos(di)) from the law of cosines
    over the angle between the velocity vectors: the transfer speed
    before the burn and the circular speed after it, with the plane
    change and the speed change applied by a single impulse. For the
    GTO-to-GEO case the combined burn costs 1.832 km/s against 2.983
    km/s done separately.

    Raises ValueError for a negative speed or an inclination change
    outside (-180, 180].
    """
    if v_before < 0 or v_after < 0:
        raise ValueError(
            "speeds must be non-negative, got v_before=%r and v_after=%r"
            % (v_before, v_after)
        )
    if not DI_LOW < inclination_change_deg <= DI_HIGH:
        raise ValueError(
            "inclination_change_deg must be in (-180, 180], got %r"
            % (inclination_change_deg,)
        )
    return math.sqrt(
        v_before * v_before
        + v_after * v_after
        - 2.0 * v_before * v_after
        * math.cos(math.pi / 180.0 * inclination_change_deg)
    )


def maneuver_verdict(pure_dv_total, combined_dv):
    """Return the maneuver-selection verdict string.

    'combined-cheaper' when the one-burn combined delta-v is below the
    separate total by more than the 1e-9 tolerance, otherwise
    'pure-cheaper-or-equal'. A combined burn gains the full law-of-
    cosines saving only when the plane change and the transfer are done
    at the same point.
    """
    if combined_dv < pure_dv_total - 1e-9:
        return "combined-cheaper"
    return "pure-cheaper-or-equal"


def analyze_plane_change(
    mu,
    radius_km,
    inclination_change_deg,
    transfer_semimajor_axis_km=None,
    target_radius_km=None,
):
    """Return the maneuver analysis dict for the standard two cases.

    (a) Pure-only: with transfer_semimajor_axis_km None the maneuver is
    a pure plane change on the circular orbit at radius_km. Returns
    speed_km_s, pure_plane_change_dv_km_s, combined_dv_km_s None,
    separate_total_km_s None and verdict 'pure-only'.

    (b) Combined: with a transfer semimajor axis and a target radius the
    plane change happens at the apoapsis end of a Hohmann-like transfer
    from radius_km to target_radius_km together with the
    circularization burn. Returns speed_at_maneuver_km_s (the transfer
    speed at the target radius), circular_speed_km_s, the pure plane
    change delta-v at the circular speed, the combined-burn delta-v,
    the separate two-burn total and the verdict from maneuver_verdict.

    ValueErrors from the component checks propagate.
    """
    if transfer_semimajor_axis_km is None:
        v = circular_orbit_speed(mu, radius_km)
        if target_radius_km is not None:
            raise ValueError(
                "target_radius_km requires transfer_semimajor_axis_km, "
                "got target_radius_km=%r only" % (target_radius_km,)
            )
        dv_pure = plane_change_dv(v, inclination_change_deg)
        return {
            "speed_km_s": v,
            "pure_plane_change_dv_km_s": dv_pure,
            "combined_dv_km_s": None,
            "separate_total_km_s": None,
            "verdict": "pure-only",
        }
    if target_radius_km is None:
        raise ValueError(
            "target_radius_km required when transfer_semimajor_axis_km "
            "is given, got None"
        )
    v_before = transfer_speed_at_radius(
        mu, target_radius_km, transfer_semimajor_axis_km
    )
    v_after = circular_orbit_speed(mu, target_radius_km)
    dv_pure = plane_change_dv(v_after, inclination_change_deg)
    dv_combined = combined_burn_dv(v_before, v_after, inclination_change_deg)
    separate_total = (v_after - v_before) + dv_pure
    return {
        "speed_at_maneuver_km_s": v_before,
        "circular_speed_km_s": v_after,
        "pure_plane_change_dv_km_s": dv_pure,
        "combined_dv_km_s": dv_combined,
        "separate_total_km_s": separate_total,
        "verdict": maneuver_verdict(separate_total, dv_combined),
    }

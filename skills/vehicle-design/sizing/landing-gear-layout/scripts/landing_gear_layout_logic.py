"""Tricycle landing gear arrangement geometry (vehicle-design/sizing/landing-gear-layout).

Pure stdlib statics and trigonometry for laying out a tricycle landing
gear against the center-of-gravity envelope: the tipback angle at the
aft CG limit, the tail strike clearance angle at rotation about the main
gear contact, the lateral turnover angle from the wheel track (simplified
main gear pair check and the nose-to-main tricycle diagonal refinement),
and the nose gear static load fraction at the forward and aft CG limits.

Pinned conventions: stations x are metres aft of a fuselage datum, the
ground plane is z = 0 at the tire contacts, rotations are nose-up about
the main gear contact point, and all angles are returned in degrees. The
aircraft is level in the reference attitude with the aft CG limit forward
of the main gear contact. Deterministic scalar returns only: no dicts,
no RNG, stdlib math only.
"""

import math

# Typical nose gear static load fraction band (fraction of the total
# landing weight carried by the nose gear at a given CG station).
NOSE_FRACTION_MIN = 0.05
NOSE_FRACTION_MAX = 0.20
# Typical transport unstick rotation reference in degrees, used for the
# rotation margin print in the worked case.
ROTATION_REF_DEG = 10.0


def tipback_angle(h_cg, x_mg, x_cg_aft):
    """Tipback angle at the aft CG limit, nose-up about the main gear contact.

    Rotating nose-up by theta_tip brings the vertical line through the
    aft CG onto the main gear contact; beyond it gravity rolls the
    aircraft onto its tail. tan(theta_tip) = (x_mg - x_cg_aft) / h_cg,
    so the angle grows with the aft-CG margin and vanishes as the aft CG
    reaches the contact station.

    Args:
        h_cg: CG height above the ground plane, metres (positive).
        x_mg: main gear contact station, metres.
        x_cg_aft: aft CG limit station, metres (forward of x_mg).

    Returns:
        Tipback angle in degrees.

    Raises:
        ValueError: h_cg <= 0 or x_cg_aft >= x_mg (a statically tipped
            arrangement, the aft CG not forward of the main gear contact).
    """
    if h_cg <= 0.0:
        raise ValueError("h_cg must be positive")
    if x_mg <= 0.0:
        raise ValueError("x_mg must be positive")
    if x_cg_aft >= x_mg:
        raise ValueError("aft CG limit must sit forward of the main gear contact")
    margin = x_mg - x_cg_aft
    return math.degrees(math.atan(margin / h_cg))


def tail_strike_clearance_angle(h_tail_contact, x_tail, x_mg):
    """Tail strike clearance angle at rotation about the main gear contact.

    The tail cone lowest point at station x_tail with height
    h_tail_contact descends as z(theta) = h_tail_contact * cos(theta) -
    a * sin(theta) with arm a = x_tail - x_mg, which vanishes at
    tan(theta_ts) = h_tail_contact / a.

    Args:
        h_tail_contact: tail cone lowest point height above the ground,
            metres (positive).
        x_tail: tail cone lowest point station, metres (aft of x_mg).
        x_mg: main gear contact station, metres.

    Returns:
        Tail strike clearance angle in degrees.

    Raises:
        ValueError: h_tail_contact <= 0 or x_tail <= x_mg.
    """
    if h_tail_contact <= 0.0:
        raise ValueError("h_tail_contact must be positive")
    if x_tail <= 0.0:
        raise ValueError("x_tail must be positive")
    if x_mg <= 0.0:
        raise ValueError("x_mg must be positive")
    if x_tail <= x_mg:
        raise ValueError("tail contact station must sit aft of the main gear")
    arm = x_tail - x_mg
    return math.degrees(math.atan(h_tail_contact / arm))


def lateral_turnover_angle(h_cg, track):
    """Simplified lateral turnover angle of the main gear pair.

    Rolls the aircraft about the line joining the two main gear contacts
    with the CG height over the half track arm:
    tan(theta_lat) = 2 * h_cg / track.

    Args:
        h_cg: CG height above the ground plane, metres (positive).
        track: main gear wheel track, metres (positive).

    Returns:
        Lateral turnover angle in degrees.

    Raises:
        ValueError: h_cg <= 0 or track <= 0.
    """
    if h_cg <= 0.0:
        raise ValueError("h_cg must be positive")
    if track <= 0.0:
        raise ValueError("track must be positive")
    return math.degrees(math.atan(2.0 * h_cg / track))


def lateral_turnover_tricycle_angle(h_cg, x_cg, x_mg, x_ng, track):
    """Tricycle lateral turnover angle about the nose-to-main diagonal.

    Rolls about the diagonal joining the nose gear contact and the nearer
    main gear contact. The perpendicular ground-plane distance from the
    CG vertical to that diagonal is d_perp = (x_cg - x_ng) * (track / 2)
    / sqrt(wheelbase**2 + (track / 2)**2) with wheelbase = x_mg - x_ng;
    the diagonal arm is shorter than the half track, so this check binds
    at a forward CG.

    Args:
        h_cg: CG height above the ground plane, metres (positive).
        x_cg: CG station under evaluation, metres (inside the wheelbase).
        x_mg: main gear contact station, metres.
        x_ng: nose gear contact station, metres.
        track: main gear wheel track, metres (positive).

    Returns:
        Tricycle diagonal turnover angle in degrees.

    Raises:
        ValueError: h_cg <= 0, track <= 0, x_mg <= x_ng, or x_cg outside
            the open station pair (x_ng, x_mg).
    """
    if h_cg <= 0.0:
        raise ValueError("h_cg must be positive")
    if track <= 0.0:
        raise ValueError("track must be positive")
    if x_mg <= x_ng:
        raise ValueError("main gear station must sit aft of the nose gear station")
    if x_cg <= x_ng or x_cg >= x_mg:
        raise ValueError("CG station must sit inside the wheelbase station pair")
    wheelbase = x_mg - x_ng
    half_track = track / 2.0
    d_perp = (x_cg - x_ng) * half_track / math.sqrt(
        wheelbase * wheelbase + half_track * half_track
    )
    return math.degrees(math.atan(d_perp / h_cg))


def nose_gear_static_load_fraction(x_cg, x_mg, x_ng):
    """Nose gear static load fraction at a CG station.

    The moment balance about the main gear contact gives
    P_n / W = (x_mg - x_cg) / (x_mg - x_ng); the nose gear carries more
    when the CG is forward, so the aft CG limit gives the lower fraction
    and the forward CG limit the upper one. The fraction is dimensionless
    and layout-level only; strut loads are never computed here.

    Args:
        x_cg: CG station, metres (inside the wheelbase).
        x_mg: main gear contact station, metres.
        x_ng: nose gear contact station, metres.

    Returns:
        Nose gear static load fraction in (0, 1).

    Raises:
        ValueError: x_mg <= x_ng or x_cg outside the open station pair
            (x_ng, x_mg): a CG at or aft of the main gear station drives
            the fraction to zero or negative, one at or forward of the
            nose gear station drives it to one or above.
    """
    if x_mg <= x_ng:
        raise ValueError("main gear station must sit aft of the nose gear station")
    if x_cg <= x_ng or x_cg >= x_mg:
        raise ValueError("CG station must sit inside the wheelbase station pair")
    return (x_mg - x_cg) / (x_mg - x_ng)

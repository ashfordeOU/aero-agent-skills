"""Radius-to-fix (RF) leg lateral path construction (pure stdlib).

Constructs the lateral path geometry of a published radius-to-fix leg for
RNP AR procedures in a local tangent-plane frame with x = east (NM) and
y = north (NM).  Given the entry fix EF, the inbound track at EF (true
degrees clockwise from north), the published radius R (NM) and the turn
direction, the module computes the turning center, checks that the exit
fix XF lies on the radius circle, and derives the swept central angle,
the along-arc length, the exit track and the chord.

Turn geometry conventions
-------------------------
Inbound direction unit vector at EF for inbound track t:

    d      = (sin t, cos t)                 (east, north components)
    n_right = (cos t, -sin t)               unit normal, right of travel
    n_left  = (-cos t, sin t)               unit normal, left of travel

Center: C = EF + R * n (RIGHT uses n_right, LEFT uses n_left).  Example:
EF = (0, 0), inbound 090 (east), RIGHT, R = 15 NM gives C = (0, -15),
the center south of eastbound travel.

Arc conventions
---------------
Radial bearing from the center to a point P is
bearing = atan2(P.x - C.x, P.y - C.y), compass degrees (0..360).
The swept central angle runs from the EF radius to the XF radius along
the turn direction, reported in degrees 0..360.  For EF == XF (radius
vectors identical) the swept angle is 0 deg, a degenerate zero-length
arc that makes the leg invalid.  Full-circle sweeps approaching 360 deg
are represented by an exit fix just short of the entry fix; the modulo
arithmetic never wraps 360 back to 0.  Arc length s = R * radians(sweep).
Exit track: the flight tangent at XF on the turn side, radial bearing
plus 90 deg for RIGHT and minus 90 deg for LEFT, normalized to 0..360.
Chord = |XF - EF|.

All functions raise ValueError on non-finite coordinates, radius <= 0,
or an invalid turn direction.
"""

import math

__all__ = [
    "rf_turn_center",
    "rf_exit_on_arc",
    "rf_arc_angle_deg",
    "rf_arc_length_nm",
    "rf_exit_track_deg",
    "rf_chord_nm",
    "rf_leg_construct",
]

TURN_RIGHT = "RIGHT"
TURN_LEFT = "LEFT"
_VALID_TURNS = (TURN_RIGHT, TURN_LEFT)


def _check_finite(*values):
    """Raise ValueError when any value is not finite."""
    for value in values:
        if not math.isfinite(value):
            raise ValueError("non-finite coordinate or radius value")


def _check_radius(radius_nm):
    """Raise ValueError when the radius is not finite or positive."""
    _check_finite(radius_nm)
    if radius_nm <= 0.0:
        raise ValueError("radius must be greater than zero")


def _check_turn(turn):
    """Raise ValueError when the turn direction is not RIGHT or LEFT."""
    if turn not in _VALID_TURNS:
        raise ValueError("turn direction must be RIGHT or LEFT")


def _compass_bearing_deg(dx, dy):
    """Compass bearing (0..360, clockwise from north) of vector (dx, dy)."""
    bearing = math.degrees(math.atan2(dx, dy))
    return bearing % 360.0


def rf_turn_center(ef, inbound_track_deg, radius_nm, turn):
    """Return the turning center (cx, cy) of an RF leg.

    ef is the entry fix (x_east, y_north) in NM; inbound_track_deg is the
    true course INTO the leg at EF, degrees clockwise from north.  The
    center sits at distance radius_nm from EF on the side given by the
    turn direction: C = EF + R * n_right for RIGHT, C = EF + R * n_left
    for LEFT, with n_right = (cos t, -sin t) and
    n_left = (-cos t, sin t) for t = radians(inbound_track_deg).

    Raises ValueError on radius <= 0, an invalid turn direction, or a
    non-finite EF coordinate.
    """
    _check_radius(radius_nm)
    _check_turn(turn)
    x_ef, y_ef = ef
    _check_finite(x_ef, y_ef)
    t = math.radians(inbound_track_deg)
    if turn == TURN_RIGHT:
        nx, ny = math.cos(t), -math.sin(t)
    else:
        nx, ny = -math.cos(t), math.sin(t)
    return (x_ef + radius_nm * nx, y_ef + radius_nm * ny)


def rf_exit_on_arc(center, xf, radius_nm, tol_nm=1e-6):
    """Return True when XF lies on the radius circle within tol_nm.

    Checks abs(|XF - C| - R) <= tol_nm.  Raises ValueError on radius
    <= 0 or non-finite center/XF coordinates.
    """
    _check_radius(radius_nm)
    cx, cy = center
    x_xf, y_xf = xf
    _check_finite(cx, cy, x_xf, y_xf, tol_nm)
    distance = math.hypot(x_xf - cx, y_xf - cy)
    return abs(distance - radius_nm) <= tol_nm


def rf_arc_angle_deg(center, ef, xf, turn):
    """Return the central angle swept from EF to XF along the turn, 0..360.

    The angle runs from the EF radius vector to the XF radius vector in
    the turn direction.  The counter-clockwise angle between the vectors
    is computed with atan2(cross, dot); a LEFT (counter-clockwise) turn
    sweeps that angle while a RIGHT (clockwise) turn sweeps
    360 - ccw_angle.  EF == XF (identical radius vectors) is handled
    explicitly as a degenerate 0 deg arc; distinct points always yield a
    sweep strictly inside (0, 360) so a full-circle value never wraps to
    0.  Raises ValueError on non-finite coordinates or an invalid turn.
    """
    _check_turn(turn)
    cx, cy = center
    x_ef, y_ef = ef
    x_xf, y_xf = xf
    _check_finite(cx, cy, x_ef, y_ef, x_xf, y_xf)
    v1x, v1y = x_ef - cx, y_ef - cy
    v2x, v2y = x_xf - cx, y_xf - cy
    if v1x == v2x and v1y == v2y:
        # EF and XF coincide on the arc: degenerate zero-length arc.
        return 0.0
    cross = v1x * v2y - v1y * v2x
    dot = v1x * v2x + v1y * v2y
    ccw_deg = math.degrees(math.atan2(cross, dot))
    ccw_deg = ccw_deg % 360.0  # counter-clockwise angle in [0, 360)
    if turn == TURN_RIGHT:
        return 360.0 - ccw_deg
    return ccw_deg


def rf_arc_length_nm(radius_nm, arc_angle_deg):
    """Return the along-arc length s = R * radians(angle), in NM."""
    _check_radius(radius_nm)
    _check_finite(arc_angle_deg)
    if arc_angle_deg < 0.0:
        raise ValueError("arc angle must be non-negative")
    return radius_nm * math.radians(arc_angle_deg)


def rf_exit_track_deg(center, xf, turn):
    """Return the exit track (true degrees 0..360) at XF along the turn.

    The radial bearing from the center to XF is bearing_radial =
    atan2(x_xf - cx, y_xf - cy) in compass degrees.  The flight tangent
    at XF continues the turn: RIGHT adds 90 deg to the radial bearing,
    LEFT subtracts 90 deg.  Raises ValueError on non-finite coordinates
    or an invalid turn.
    """
    _check_turn(turn)
    cx, cy = center
    x_xf, y_xf = xf
    _check_finite(cx, cy, x_xf, y_xf)
    radial = _compass_bearing_deg(x_xf - cx, y_xf - cy)
    if turn == TURN_RIGHT:
        return (radial + 90.0) % 360.0
    return (radial - 90.0) % 360.0


def rf_chord_nm(ef, xf):
    """Return the chord |XF - EF| between the two fixes, in NM."""
    x_ef, y_ef = ef
    x_xf, y_xf = xf
    _check_finite(x_ef, y_ef, x_xf, y_xf)
    return math.hypot(x_xf - x_ef, y_xf - y_ef)


def rf_leg_construct(ef, xf, inbound_track_deg, radius_nm, turn, tol_nm=1e-6):
    """Return the full RF-leg geometry dict for a flyable-arc check.

    Keys: center_nm (turning center), exit_on_arc (bool, XF within
    tol_nm of the radius circle), sweep_deg (central angle along the
    turn), arc_length_nm (R * radians(sweep)), exit_track_deg (tangent
    at XF), chord_nm (|XF - EF|), valid (exit_on_arc and sweep_deg > 0).

    Raises ValueError on radius <= 0, an invalid turn, or non-finite
    EF/XF coordinates.
    """
    _check_radius(radius_nm)
    _check_turn(turn)
    x_ef, y_ef = ef
    x_xf, y_xf = xf
    _check_finite(x_ef, y_ef, x_xf, y_xf, tol_nm)
    center = rf_turn_center(ef, inbound_track_deg, radius_nm, turn)
    exit_on_arc = rf_exit_on_arc(center, xf, radius_nm, tol_nm)
    sweep_deg = rf_arc_angle_deg(center, ef, xf, turn)
    return {
        "center_nm": center,
        "exit_on_arc": exit_on_arc,
        "sweep_deg": sweep_deg,
        "arc_length_nm": rf_arc_length_nm(radius_nm, sweep_deg),
        "exit_track_deg": rf_exit_track_deg(center, xf, turn),
        "chord_nm": rf_chord_nm(ef, xf),
        "valid": exit_on_arc and sweep_deg > 0.0,
    }

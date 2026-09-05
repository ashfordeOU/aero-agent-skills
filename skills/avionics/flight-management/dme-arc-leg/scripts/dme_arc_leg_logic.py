"""DME arc procedure leg lateral geometry (pure stdlib).

Constructs the lateral geometry of a constant-DME arc around a VOR/DME
station: arc length between two radials at the published radius, points
on the arc, the bank angle that holds the arc at a true airspeed, the
turn radius implied by a bank angle, the chord between two arc fixes and
the signed radial intercept for joining or leaving the arc.

Conventions: user-facing angles in degrees (radials measured clockwise
from north), distances in nautical miles; the DME radius is the
published horizontal arc radius, so no slant correction enters this arc
geometry. All functions raise ValueError on non-physical inputs.
"""

import math

# Module constants (SI where noted)
G_MS2 = 9.80665        # standard gravity, m/s^2
KT_TO_MS = 0.514444    # knots to m/s
NM_TO_M = 1852.0       # nautical mile to m
M_TO_NM = 1.0 / 1852.0  # m to nautical mile


def _radial_short_diff_deg(current_deg, target_deg):
    """Signed smaller angular difference (target - current), in (-180, 180]."""
    diff = (target_deg - current_deg) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff


def _check_radius(r_nm):
    """Raise ValueError unless the arc radius is positive."""
    if r_nm is None or not math.isfinite(float(r_nm)) or float(r_nm) <= 0.0:
        raise ValueError("DME radius must be positive, got %r" % (r_nm,))


def _check_radial(radial_deg):
    """Raise ValueError unless the radial lies in the published band."""
    if radial_deg is None or not math.isfinite(float(radial_deg)) or not (0.0 <= float(radial_deg) <= 360.0):
        raise ValueError("Radial must lie in [0, 360] degrees, got %r" % (radial_deg,))


def _check_delta(delta_radial_deg):
    """Raise ValueError unless the radial delta lies in [0, 360]."""
    if delta_radial_deg is None or not math.isfinite(float(delta_radial_deg)) or not (0.0 <= float(delta_radial_deg) <= 360.0):
        raise ValueError("Radial delta must lie in [0, 360] degrees, got %r" % (delta_radial_deg,))


def arc_length_nm(r_nm, delta_radial_deg):
    """Arc length in nm between two radials delta apart at radius r_nm.

    length = r * radians(delta). Non-positive radius or a delta outside
    [0, 360] raises ValueError.
    """
    _check_radius(r_nm)
    _check_delta(delta_radial_deg)
    return float(r_nm) * math.radians(float(delta_radial_deg))


def point_on_arc(r_nm, radial_deg):
    """(x_nm, y_nm) of the point on the arc at the given radial.

    Station at the origin, x east, y north, radial clockwise from north:
    x = r * sin(radial), y = r * cos(radial).
    """
    _check_radius(r_nm)
    _check_radial(radial_deg)
    rad = math.radians(float(radial_deg))
    return (float(r_nm) * math.sin(rad), float(r_nm) * math.cos(rad))


def arc_bank_angle_deg(tas_kt, r_nm):
    """Bank angle in degrees that holds radius r_nm at true airspeed tas.

    bank = atan(V**2 / (g * r)) with V in m/s and r in m. Non-positive
    airspeed or radius raises ValueError.
    """
    if tas_kt is None or not math.isfinite(float(tas_kt)) or float(tas_kt) <= 0.0:
        raise ValueError("True airspeed must be positive, got %r" % (tas_kt,))
    _check_radius(r_nm)
    v_ms = float(tas_kt) * KT_TO_MS
    r_m = float(r_nm) * NM_TO_M
    return math.degrees(math.atan(v_ms * v_ms / (G_MS2 * r_m)))


def arc_turn_radius_nm(tas_kt, bank_deg):
    """Turn radius in nm for true airspeed and bank angle.

    radius = V**2 / (g * tan(bank)) in m, converted to nm. Non-positive
    airspeed or a bank angle outside (0, 90) raises ValueError.
    """
    if tas_kt is None or not math.isfinite(float(tas_kt)) or float(tas_kt) <= 0.0:
        raise ValueError("True airspeed must be positive, got %r" % (tas_kt,))
    if bank_deg is None or not math.isfinite(float(bank_deg)) or not (0.0 < float(bank_deg) < 90.0):
        raise ValueError("Bank angle must lie in (0, 90) degrees, got %r" % (bank_deg,))
    v_ms = float(tas_kt) * KT_TO_MS
    r_m = v_ms * v_ms / (G_MS2 * math.tan(math.radians(float(bank_deg))))
    return r_m * M_TO_NM


def arc_chord_nm(r_nm, delta_radial_deg):
    """Straight-line chord in nm across the arc between two radials.

    chord = 2 * r * sin(radians(delta) / 2). Non-positive radius or a
    delta outside [0, 360] raises ValueError.
    """
    _check_radius(r_nm)
    _check_delta(delta_radial_deg)
    return 2.0 * float(r_nm) * math.sin(math.radians(float(delta_radial_deg)) / 2.0)


def radial_intercept_deg(current_radial_deg, target_radial_deg):
    """Signed smaller angular intercept from current to target radial.

    Positive clockwise, negative counter-clockwise, in (-180, 180].
    """
    _check_radial(current_radial_deg)
    _check_radial(target_radial_deg)
    return _radial_short_diff_deg(float(current_radial_deg), float(target_radial_deg))


def dme_arc_geometry(r_nm, radial_start_deg, radial_end_deg):
    """Full arc geometry dict for the arc between two radials.

    Returns {arc_length_nm, chord_nm, turn_angle_deg, start_point,
    end_point, midpoint_point}. The arc follows the shorter angular
    separation (the way a procedure arc is flown). Midpoint radial is
    the start radial advanced by half the signed turn.
    """
    _check_radius(r_nm)
    _check_radial(radial_start_deg)
    _check_radial(radial_end_deg)
    turn_deg = _radial_short_diff_deg(float(radial_start_deg), float(radial_end_deg))
    turn_mag = abs(turn_deg)
    start_point = point_on_arc(r_nm, radial_start_deg)
    end_point = point_on_arc(r_nm, radial_end_deg)
    mid_radial = (float(radial_start_deg) + turn_deg / 2.0) % 360.0
    midpoint_point = point_on_arc(r_nm, mid_radial)
    return {
        "arc_length_nm": arc_length_nm(r_nm, turn_mag),
        "chord_nm": arc_chord_nm(r_nm, turn_mag),
        "turn_angle_deg": turn_deg,
        "start_point": start_point,
        "end_point": end_point,
        "midpoint_point": midpoint_point,
    }

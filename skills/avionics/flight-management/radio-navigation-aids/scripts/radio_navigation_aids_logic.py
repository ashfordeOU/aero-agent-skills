"""Radio navigation aid geometry for an aircraft navigation solution.

Pure stdlib, deterministic, offline. Computes the receiver level
geometry of conventional radio navaids (VOR/DME/ILS):

- bearing_deg: bearing from the VOR/DME station to the aircraft,
  measured clockwise from north, in degrees.
- radial_deg: the reciprocal VOR radial FROM the station, degrees.
- dme_slant_range_m: DME slant range from the planar ground distance
  and the aircraft altitude.
- loc_deviation_deg: ILS localizer deviation angle from the lateral
  offset and the distance to the runway threshold.
- gs_deviation_deg: ILS glideslope deviation angle from the height
  above the threshold and the distance to the threshold, against the
  nominal glideslope angle.
- analyze: one call returning every quantity above.

Coordinate convention: local tangent plane with x east (m), y north
(m), z up (m). The VOR/DME station is at the origin and the aircraft
is at (x_ac, y_ac, altitude_m).

Validation: non-physical inputs raise ValueError (negative altitude,
non-positive distance to threshold, out-of-range glideslope angle,
negative height above ground). All inputs must be finite.

The planar local tangent geometry is a documented simplification for
short ranges; great-circle corrections are out of scope.
"""

import math

DEFAULT_GS_ANGLE_DEG = 3.0
_FULL_CIRCLE_DEG = 360.0
_HALF_CIRCLE_DEG = 180.0
_RIGHT_ANGLE_DEG = 90.0


def _require_finite(value, name):
    """Raise ValueError when value is not a finite number."""
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (name, value))


def bearing_deg(x_ac, y_ac):
    """Bearing from the station to the aircraft, degrees clockwise from north.

    Uses atan2(x, y) so that due east is 90 deg and due north is 0 deg,
    normalized to [0, 360). At the station itself atan2(0, 0) evaluates
    to 0.0 by convention, documented as the undefined-bearing fallback.
    """
    _require_finite(x_ac, "x_ac")
    _require_finite(y_ac, "y_ac")
    raw = math.degrees(math.atan2(x_ac, y_ac))
    return raw % _FULL_CIRCLE_DEG


def radial_deg(bearing_deg_input):
    """VOR radial FROM the station, the reciprocal of the bearing.

    radial = (bearing + 180) mod 360. Bearing must lie in [0, 360).
    """
    _require_finite(bearing_deg_input, "bearing")
    if bearing_deg_input < 0.0 or bearing_deg_input >= _FULL_CIRCLE_DEG:
        raise ValueError(
            "bearing must be in [0, 360), got %r" % (bearing_deg_input,))
    return (bearing_deg_input + _HALF_CIRCLE_DEG) % _FULL_CIRCLE_DEG


def dme_slant_range_m(x_ac, y_ac, altitude_m):
    """DME slant range in meters: sqrt(x^2 + y^2 + altitude^2).

    The DME measures the straight line from the station at ground
    level to the aircraft at altitude, not the ground distance.
    """
    _require_finite(x_ac, "x_ac")
    _require_finite(y_ac, "y_ac")
    _require_finite(altitude_m, "altitude_m")
    if altitude_m < 0.0:
        raise ValueError("altitude must be non-negative, got %r"
                         % (altitude_m,))
    return math.sqrt(x_ac * x_ac + y_ac * y_ac + altitude_m * altitude_m)


def loc_deviation_deg(lateral_offset_m, distance_to_threshold_m):
    """ILS localizer deviation angle in degrees: deg(atan(offset/distance)).

    A positive lateral offset to the right of the approach course
    gives a positive deviation, i.e. the aircraft is right of the
    localizer centerline. The distance to the threshold must be
    positive; an aircraft exactly on the centerline (zero offset at a
    positive distance) yields zero deviation.
    """
    _require_finite(lateral_offset_m, "lateral_offset_m")
    _require_finite(distance_to_threshold_m, "distance_to_threshold_m")
    if distance_to_threshold_m <= 0.0:
        raise ValueError(
            "distance to threshold must be positive, got %r"
            % (distance_to_threshold_m,))
    return math.degrees(math.atan(lateral_offset_m
                                  / distance_to_threshold_m))


def gs_deviation_deg(height_agl_m, distance_to_threshold_m,
                     gs_angle_deg=DEFAULT_GS_ANGLE_DEG):
    """ILS glideslope deviation in degrees: actual path angle minus nominal.

    actual = deg(atan(height / distance)); deviation = actual minus the
    nominal glideslope angle (default 3.0 deg), positive when the
    aircraft is above the glidepath.
    """
    _require_finite(height_agl_m, "height_agl_m")
    _require_finite(distance_to_threshold_m, "distance_to_threshold_m")
    _require_finite(gs_angle_deg, "gs_angle_deg")
    if height_agl_m < 0.0:
        raise ValueError("height above ground must be non-negative, got %r"
                         % (height_agl_m,))
    if distance_to_threshold_m <= 0.0:
        raise ValueError(
            "distance to threshold must be positive, got %r"
            % (distance_to_threshold_m,))
    if gs_angle_deg <= 0.0 or gs_angle_deg >= _RIGHT_ANGLE_DEG:
        raise ValueError(
            "glideslope angle must be in (0, 90) degrees, got %r"
            % (gs_angle_deg,))
    actual_deg = math.degrees(math.atan(height_agl_m
                                        / distance_to_threshold_m))
    return actual_deg - gs_angle_deg


def analyze(x_ac, y_ac, altitude_m, lateral_offset_m, loc_distance_m,
            height_agl_m, gs_distance_m, gs_angle_deg=DEFAULT_GS_ANGLE_DEG):
    """Full radio navigation geometry solution as a dictionary.

    Combines the VOR/DME quantities from the station coordinates and
    the ILS quantities from the approach geometry into one dict with
    keys: bearing_deg, radial_deg, dme_slant_range_m,
    loc_deviation_deg, gs_deviation_deg. loc_distance_m is the
    distance to the threshold used for the localizer deviation and
    gs_distance_m the one used for the glideslope deviation; they may
    differ when the localizer and glideslope transmitters sit at
    different ranges.
    """
    bearing = bearing_deg(x_ac, y_ac)
    return {
        "bearing_deg": bearing,
        "radial_deg": radial_deg(bearing),
        "dme_slant_range_m": dme_slant_range_m(x_ac, y_ac, altitude_m),
        "loc_deviation_deg": loc_deviation_deg(lateral_offset_m,
                                               loc_distance_m),
        "gs_deviation_deg": gs_deviation_deg(height_agl_m, gs_distance_m,
                                             gs_angle_deg),
    }

#!/usr/bin/env python3
"""ECSS-E-ST-10-04C clause 10.2.2.2/10.2.4 + Annex C meteoroid model
selection and application (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): the
meteoroid environment has a sporadic background component (the
Grun-type interplanetary flux model: cumulative flux as a function of
particle mass, isotropic at 1 AU) and a meteoroid-stream component
(time-limited, direction-concentrated flux enhancements tied to
specific calendar windows). Earth-orbiting missions additionally
reduce the background flux by an Earth-shielding factor -- the
fraction of the sky not blocked by the Earth's disc as seen from the
spacecraft. This module implements model-selection input validation,
the background flux curve, the Earth-shielding geometry, the stream
activity/enhancement logic, and their combination into a total
incident flux; it does not implement the downstream impact-risk
assessment (see the sibling e1004-impact-risk leaf).

The background-flux anchor points and the stream table below are an
illustrative, simplified parameterization chosen to have the right
qualitative shape (monotonically decreasing flux with mass; a
triangular stream-activity profile) for deterministic offline testing.
A certified analysis substitutes the normative Annex C flux data and
stream parameters.
"""

import math
from datetime import date

EARTH_RADIUS_KM = 6371.0

# (log10 mass in grams, log10 cumulative flux in m^-2 s^-1), sorted by
# ascending mass with strictly decreasing flux -- illustrative shape
# only, see module docstring.
GRUN_BACKGROUND_ANCHORS_LOG10 = [
    (-18.0, 4.0),
    (-12.0, 0.0),
    (-9.0, -3.5),
    (-6.0, -6.5),
    (-3.0, -9.0),
    (0.0, -11.5),
    (3.0, -13.5),
    (6.0, -15.0),
]

# start/peak/end day-of-year (1-366) and an illustrative peak
# enhancement factor applied multiplicatively to the background flux
# at the stream's peak.
STREAM_TABLE = {
    "quadrantids": {"start_doy": 1, "peak_doy": 3, "end_doy": 5, "peak_enhancement": 15.0},
    "perseids": {"start_doy": 198, "peak_doy": 224, "end_doy": 236, "peak_enhancement": 25.0},
    "geminids": {"start_doy": 338, "peak_doy": 348, "end_doy": 351, "peak_enhancement": 20.0},
}

VALID_REGIMES = ("interplanetary", "earth_orbit")


def _interpolate(x, points):
    """Piecewise-linear interpolation of y over x for a list of (x, y)
    points sorted by ascending x. Extrapolates beyond either end using
    that end's edge-segment slope."""
    if x <= points[0][0]:
        (x0, y0), (x1, y1) = points[0], points[1]
    elif x >= points[-1][0]:
        (x0, y0), (x1, y1) = points[-2], points[-1]
    else:
        x0 = y0 = x1 = y1 = None
        for i in range(len(points) - 1):
            if points[i][0] <= x <= points[i + 1][0]:
                (x0, y0), (x1, y1) = points[i], points[i + 1]
                break
    slope = (y1 - y0) / (x1 - x0)
    return y0 + slope * (x - x0)


def background_cumulative_flux(mass_kg):
    """Sporadic background cumulative flux (m^-2 s^-1) for particles of
    at least the given mass (kg), from the illustrative Grun-type
    mass-flux curve. Monotonically decreasing in mass. Raises
    ValueError if mass_kg is not positive."""
    if mass_kg is None or mass_kg <= 0:
        raise ValueError("mass_kg must be positive, got %r" % (mass_kg,))
    mass_g = mass_kg * 1000.0
    log10_flux = _interpolate(math.log10(mass_g), GRUN_BACKGROUND_ANCHORS_LOG10)
    return 10.0 ** log10_flux


def earth_shielding_factor(altitude_km):
    """Fraction of the sky not blocked by the Earth's disc as seen from
    an orbit at the given altitude (km) -- 0.5 at the surface, rising
    toward 1.0 far from Earth. Raises ValueError if altitude_km is
    negative."""
    if altitude_km is None or altitude_km < 0:
        raise ValueError("altitude_km must be non-negative, got %r" % (altitude_km,))
    earth_angular_radius = math.asin(EARTH_RADIUS_KM / (EARTH_RADIUS_KM + altitude_km))
    return (1.0 + math.cos(earth_angular_radius)) / 2.0


def day_of_year(date_value):
    """Day-of-year (1-366) for a date. Accepts a datetime.date (or
    datetime.datetime) or a (year, month, day) tuple."""
    if isinstance(date_value, tuple):
        date_value = date(*date_value)
    return date_value.timetuple().tm_yday


def is_stream_active(stream_id, doy):
    """True when the given stream's activity window covers the given
    day-of-year (inclusive of start/end, wraps across the year
    boundary if start_doy > end_doy). Raises KeyError for an unknown
    stream_id."""
    stream = STREAM_TABLE[stream_id]
    start, end = stream["start_doy"], stream["end_doy"]
    if start <= end:
        return start <= doy <= end
    return doy >= start or doy <= end


def stream_enhancement_factor(stream_id, doy):
    """Multiplicative flux enhancement for the given stream at the
    given day-of-year: 1.0 (no enhancement) outside its activity
    window, rising linearly to peak_enhancement at peak_doy and back
    down to 1.0 at start_doy/end_doy (triangular profile). Raises
    KeyError for an unknown stream_id."""
    stream = STREAM_TABLE[stream_id]
    if not is_stream_active(stream_id, doy):
        return 1.0
    start, peak, end = stream["start_doy"], stream["peak_doy"], stream["end_doy"]
    peak_enhancement = stream["peak_enhancement"]
    if doy <= peak:
        span = peak - start
        fraction = (doy - start) / span if span else 1.0
    else:
        span = end - peak
        fraction = (end - doy) / span if span else 1.0
    fraction = max(0.0, min(1.0, fraction))
    return 1.0 + fraction * (peak_enhancement - 1.0)


def active_streams(doy):
    """List of stream ids active on the given day-of-year (empty if
    none are active)."""
    return [stream_id for stream_id in STREAM_TABLE if is_stream_active(stream_id, doy)]


def worst_case_stream_enhancement(doy):
    """(factor, stream_id) for the largest stream enhancement active on
    the given day-of-year, or (1.0, None) if no stream is active."""
    best_factor, best_stream = 1.0, None
    for stream_id in active_streams(doy):
        factor = stream_enhancement_factor(stream_id, doy)
        if factor > best_factor:
            best_factor, best_stream = factor, stream_id
    return best_factor, best_stream


def model_selection_violations(mission):
    """Violation list (empty if compliant) for a mission profile dict
    with keys "regime", "mass_kg", "date", and "altitude_km" (required
    only when regime is "earth_orbit"). Does not mutate the input."""
    violations = []
    regime = mission.get("regime")
    if regime not in VALID_REGIMES:
        violations.append({"issue": "unknown_regime", "regime": regime})
    mass_kg = mission.get("mass_kg")
    if mass_kg is None or mass_kg <= 0:
        violations.append({"issue": "invalid_mass", "mass_kg": mass_kg})
    if mission.get("date") is None:
        violations.append({"issue": "missing_date"})
    if regime == "earth_orbit":
        altitude_km = mission.get("altitude_km")
        if altitude_km is None or altitude_km < 0:
            violations.append({"issue": "missing_or_invalid_altitude", "altitude_km": altitude_km})
    return violations


def total_incident_flux(regime, mass_kg, date_value, altitude_km=None):
    """Total incident meteoroid flux (m^-2 s^-1) combining the
    background flux, Earth-shielding (earth_orbit only), and the
    worst-case active stream enhancement for the given epoch. Returns
    a dict with "background_flux", "shielding_factor",
    "stream_enhancement", "active_stream", "active_streams", and
    "total_flux". Raises ValueError for an unknown regime or a missing
    altitude_km on an earth_orbit case."""
    background = background_cumulative_flux(mass_kg)
    if regime == "earth_orbit":
        if altitude_km is None:
            raise ValueError("altitude_km is required for regime='earth_orbit'")
        shielding = earth_shielding_factor(altitude_km)
    elif regime == "interplanetary":
        shielding = 1.0
    else:
        raise ValueError("unknown regime %r" % (regime,))
    doy = day_of_year(date_value)
    enhancement, stream_id = worst_case_stream_enhancement(doy)
    return {
        "background_flux": background,
        "shielding_factor": shielding,
        "stream_enhancement": enhancement,
        "active_stream": stream_id,
        "active_streams": active_streams(doy),
        "total_flux": background * shielding * enhancement,
    }


def meteoroid_environment_review(mission):
    """Full clause 10.2.2.2/10.2.4 review for one mission profile dict
    (see model_selection_violations for keys). Returns
    {"violations": [...], "result": None} when the inputs are invalid,
    otherwise {"violations": [], "result": <total_incident_flux dict>}."""
    violations = model_selection_violations(mission)
    if violations:
        return {"violations": violations, "result": None}
    result = total_incident_flux(
        mission["regime"], mission["mass_kg"], mission["date"], mission.get("altitude_km")
    )
    return {"violations": [], "result": result}


def is_compliant(review):
    """True when a meteoroid_environment_review result has no
    violations and produced a flux result."""
    return not review["violations"] and review["result"] is not None

"""Verification that a prepared surface is actually ready to receive paint.

Anchor: ECSS-Q-ST-70-31C surface-preparation clause -- the checks made on a
prepared substrate immediately before the first coat: is it clean, is its
profile inside the window the paint system needs, and are the surface and the
air around it dry enough to coat. Paraphrased into an implementable procedure;
no standard text is reproduced.

Procedure implemented here
--------------------------
1. Grade cleanliness from the water-break observation, the non-volatile residue
   figure and the particulate obscuration, each against its own limit.
2. Grade the abrasion profile against a two-sided roughness window: too smooth
   starves the mechanical key, too rough leaves peaks the film cannot cover.
3. Grade dryness from the margin between the substrate temperature and the dew
   point, and from the relative humidity in the coating area.
4. Separate what the surface owes from what the room owes: a surface failure
   means preparing again, an environmental failure means waiting.
5. Close with one disposition and every failing metric named.
"""

import math

__all__ = [
    "MEASUREMENT_TOLERANCE",
    "MIN_WATER_BREAK_DWELL_S",
    "DEFAULT_NVR_LIMIT_MG_PER_M2",
    "DEFAULT_OBSCURATION_LIMIT_PCT",
    "DEFAULT_MIN_DEW_POINT_MARGIN_K",
    "DEFAULT_MAX_RELATIVE_HUMIDITY_PCT",
    "ROUGHNESS_WINDOWS_UM",
    "SURFACE_METRICS",
    "ENVIRONMENT_METRICS",
    "DISPOSITIONS",
    "normalize_key",
    "water_break_verdict",
    "residue_verdict",
    "obscuration_verdict",
    "roughness_window_um",
    "roughness_verdict",
    "dew_point_margin_k",
    "dryness_verdict",
    "humidity_verdict",
    "assess_readiness",
]

# Readings are floats compared against limits they can land exactly on.
MEASUREMENT_TOLERANCE = 1e-9

# A water-break observation is only evidence if the film was watched long enough.
MIN_WATER_BREAK_DWELL_S = 30.0

DEFAULT_NVR_LIMIT_MG_PER_M2 = 2.0
DEFAULT_OBSCURATION_LIMIT_PCT = 0.10
DEFAULT_MIN_DEW_POINT_MARGIN_K = 3.0
DEFAULT_MAX_RELATIVE_HUMIDITY_PCT = 70.0

# Two-sided abrasion profile windows, in micrometres of average roughness.
ROUGHNESS_WINDOWS_UM = {
    "epoxy-primer": (0.8, 3.2),
    "polyurethane-topcoat": (0.4, 2.0),
    "inorganic-silicate": (1.2, 4.0),
    "conductive-paint": (0.8, 2.5),
}

SURFACE_METRICS = ("water-break", "non-volatile-residue", "particulate-obscuration",
                   "surface-roughness")
ENVIRONMENT_METRICS = ("dew-point-margin", "relative-humidity")

DISPOSITIONS = ("ready-to-coat", "conditions-hold", "re-prepare")


def normalize_key(value, label):
    """Return a trimmed lower-case key, or raise for an unusable value."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    key = value.strip().lower()
    if not key:
        raise ValueError("%s must not be empty" % label)
    return key


def _real(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    return v


def _non_negative(value, label):
    v = _real(value, label)
    if v < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, v))
    return v


def _at_or_under(value, limit):
    if value < limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=MEASUREMENT_TOLERANCE)


def _at_or_over(value, limit):
    if value > limit:
        return True
    return math.isclose(value, limit, rel_tol=0.0, abs_tol=MEASUREMENT_TOLERANCE)


def water_break_verdict(film_continuous, dwell_s):
    """Return True when an unbroken water film was held for long enough."""
    if not isinstance(film_continuous, bool):
        raise ValueError("film_continuous must be a boolean")
    dwell = _non_negative(dwell_s, "dwell_s")
    if not _at_or_over(dwell, MIN_WATER_BREAK_DWELL_S):
        raise ValueError(
            "water-break dwell %g s is under the %g s minimum; the observation is not evidence"
            % (dwell, MIN_WATER_BREAK_DWELL_S)
        )
    return film_continuous


def residue_verdict(nvr_mg_per_m2, limit=DEFAULT_NVR_LIMIT_MG_PER_M2):
    """Return True when the non-volatile residue is at or under its limit."""
    value = _non_negative(nvr_mg_per_m2, "nvr_mg_per_m2")
    cap = _non_negative(limit, "limit")
    return _at_or_under(value, cap)


def obscuration_verdict(obscuration_pct, limit=DEFAULT_OBSCURATION_LIMIT_PCT):
    """Return True when the particulate obscuration is at or under its limit."""
    value = _non_negative(obscuration_pct, "obscuration_pct")
    if value > 100.0:
        raise ValueError("obscuration_pct must not exceed 100, got %g" % value)
    cap = _non_negative(limit, "limit")
    return _at_or_under(value, cap)


def roughness_window_um(paint_system):
    """Return the (minimum, maximum) roughness a paint system needs."""
    key = normalize_key(paint_system, "paint system")
    if key not in ROUGHNESS_WINDOWS_UM:
        raise ValueError("paint system '%s' has no roughness window" % key)
    return ROUGHNESS_WINDOWS_UM[key]


def roughness_verdict(ra_um, window):
    """Return 'in-window', 'too-smooth' or 'too-rough' for a measured profile."""
    value = _non_negative(ra_um, "ra_um")
    if not isinstance(window, (list, tuple)) or len(window) != 2:
        raise ValueError("window must be a (minimum, maximum) pair")
    low = _non_negative(window[0], "window minimum")
    high = _non_negative(window[1], "window maximum")
    if low >= high:
        raise ValueError("window minimum %g is not below maximum %g" % (low, high))
    if not _at_or_over(value, low):
        return "too-smooth"
    if not _at_or_under(value, high):
        return "too-rough"
    return "in-window"


def dew_point_margin_k(surface_temperature_c, dew_point_c):
    """Return how many kelvin the substrate sits above the dew point."""
    surface = _real(surface_temperature_c, "surface_temperature_c")
    dew = _real(dew_point_c, "dew_point_c")
    return surface - dew


def dryness_verdict(margin_k, minimum=DEFAULT_MIN_DEW_POINT_MARGIN_K):
    """Return True when the dew-point margin meets its minimum."""
    value = _real(margin_k, "margin_k")
    floor = _non_negative(minimum, "minimum")
    return _at_or_over(value, floor)


def humidity_verdict(relative_humidity_pct, limit=DEFAULT_MAX_RELATIVE_HUMIDITY_PCT):
    """Return True when the coating-area humidity is at or under its ceiling."""
    value = _non_negative(relative_humidity_pct, "relative_humidity_pct")
    if value > 100.0:
        raise ValueError("relative_humidity_pct must not exceed 100, got %g" % value)
    cap = _non_negative(limit, "limit")
    return _at_or_under(value, cap)


def assess_readiness(reading):
    """Return the coat-readiness disposition for one prepared surface."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping")
    required = ("paint_system", "water_film_continuous", "water_break_dwell_s",
                "nvr_mg_per_m2", "obscuration_pct", "ra_um",
                "surface_temperature_c", "dew_point_c", "relative_humidity_pct")
    for key in required:
        if key not in reading:
            raise ValueError("reading missing required key '%s'" % key)
    window = reading.get("roughness_window") or roughness_window_um(reading["paint_system"])
    surface_findings = []
    if not water_break_verdict(reading["water_film_continuous"],
                               reading["water_break_dwell_s"]):
        surface_findings.append("water-break-observed")
    if not residue_verdict(reading["nvr_mg_per_m2"],
                           reading.get("nvr_limit_mg_per_m2", DEFAULT_NVR_LIMIT_MG_PER_M2)):
        surface_findings.append("non-volatile-residue-over-limit")
    if not obscuration_verdict(reading["obscuration_pct"],
                               reading.get("obscuration_limit_pct",
                                           DEFAULT_OBSCURATION_LIMIT_PCT)):
        surface_findings.append("particulate-obscuration-over-limit")
    profile = roughness_verdict(reading["ra_um"], window)
    if profile != "in-window":
        surface_findings.append("surface-roughness-%s" % profile)
    margin = dew_point_margin_k(reading["surface_temperature_c"], reading["dew_point_c"])
    environment_findings = []
    if not dryness_verdict(margin, reading.get("min_dew_point_margin_k",
                                               DEFAULT_MIN_DEW_POINT_MARGIN_K)):
        environment_findings.append("dew-point-margin-under-minimum")
    if not humidity_verdict(reading["relative_humidity_pct"],
                            reading.get("max_relative_humidity_pct",
                                        DEFAULT_MAX_RELATIVE_HUMIDITY_PCT)):
        environment_findings.append("relative-humidity-over-ceiling")
    if surface_findings:
        disposition = "re-prepare"
    elif environment_findings:
        disposition = "conditions-hold"
    else:
        disposition = "ready-to-coat"
    return {
        "disposition": disposition,
        "surface_findings": surface_findings,
        "environment_findings": environment_findings,
        "roughness_verdict": profile,
        "dew_point_margin_k": margin,
    }

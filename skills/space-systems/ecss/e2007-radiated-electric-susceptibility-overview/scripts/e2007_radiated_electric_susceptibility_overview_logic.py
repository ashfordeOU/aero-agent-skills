#!/usr/bin/env python3
"""Radiated electric susceptibility aim, ECSS-E-ST-20-07C clause 5.4.11.1.

Paraphrased procedure, no verbatim standard text. The clause introduces the
method: show that the unit and the cabling running into it both keep working
while a strong electric field is applied over a wide frequency band. This
module turns that aim into a deterministic demonstration:

  method band        -> validated span
  exposure objects   -> enclosure and cabling both present, declared once
  per frequency      -> applied field against required field -> margin -> group
  monitored response -> degradation frequencies -> susceptibility threshold
  coverage           -> band-edge gaps recorded as findings, not silently absorbed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. A field margin is a ratio taken to decibels, so
# an applied field sitting exactly on the required one can land a few units in
# the last place either side of zero. This absorbs representation error only;
# it never relaxes the required field strength.
DB_TOL = 1e-9

# Relative slack allowed at a band edge before a sweep is called short of it.
BAND_EDGE_REL_TOL = 0.01

# Fallback span of the radiated electric susceptibility method, hertz. A
# project that declares its own band passes it in; this is only the default.
DEFAULT_METHOD_BAND_HZ = (14.0e3, 18.0e9)

# The aim is stated over the unit and over what runs into it. They are separate
# exposure objects with their own sweeps, not two views of one measurement.
OBJECT_ENCLOSURE = "unit-enclosure"
OBJECT_CABLING = "interconnecting-cabling"
EXPOSURE_OBJECTS = (OBJECT_ENCLOSURE, OBJECT_CABLING)

CATEGORY_AT_LEVEL = "at-required-level"
CATEGORY_UNDER = "below-required-level"
CATEGORY_ABOVE = "above-required-level"
CATEGORIES = (CATEGORY_AT_LEVEL, CATEGORY_UNDER, CATEGORY_ABOVE)

VERDICT_MET = "aim-demonstrated"
VERDICT_NOT_MET = "aim-not-demonstrated"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def validate_method_band(band=DEFAULT_METHOD_BAND_HZ):
    """Validate the declared method band and return it as a float pair."""
    where = "method_band_hz"
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s: band must be a (low, high) pair" % where)
    low = _scalar(band[0], "%s.low" % where)
    high = _scalar(band[1], "%s.high" % where)
    if low <= 0.0:
        raise ValueError("%s: low edge must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError(
            "%s: high edge %g Hz must exceed low edge %g Hz" % (where, high, low)
        )
    return (low, high)


def normalize_exposure_object(role):
    """Return the recognized exposure object for a raw designation."""
    if not isinstance(role, str):
        raise ValueError("exposure object must be a string, got %r" % (role,))
    key = role.strip().lower()
    if key not in EXPOSURE_OBJECTS:
        raise ValueError(
            "unrecognized exposure object %r; recognized: %s"
            % (role, ", ".join(EXPOSURE_OBJECTS))
        )
    return key


def field_margin_db(field_applied_v_m, field_required_v_m):
    """Decibel margin of the applied field strength over the required one."""
    applied = _scalar(field_applied_v_m, "field_applied_v_m")
    required = _scalar(field_required_v_m, "field_required_v_m")
    if applied <= 0.0:
        raise ValueError("field_applied_v_m must be > 0, got %g" % applied)
    if required <= 0.0:
        raise ValueError("field_required_v_m must be > 0, got %g" % required)
    return 20.0 * math.log10(applied / required)


def categorize_field_point(margin_db):
    """Group one exposure frequency by how the applied field sits on the requirement."""
    margin = _scalar(margin_db, "margin_db")
    if math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=DB_TOL):
        return CATEGORY_AT_LEVEL
    if margin < 0.0:
        return CATEGORY_UNDER
    return CATEGORY_ABOVE


def validate_exposure_sweep(points):
    """Validate one object's exposure sweep and return normalized points.

    Each point needs frequency_hz (positive, strictly increasing),
    field_applied_v_m, field_required_v_m and the boolean
    degradation_observed recorded by the performance monitor.
    """
    where = "exposure_sweep"
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s: points must be a list" % where)
    if len(points) == 0:
        raise ValueError("%s: at least one exposure point is required" % where)
    out = []
    previous = None
    for index, point in enumerate(points):
        tag = "%s[%d]" % (where, index)
        if not isinstance(point, dict):
            raise ValueError("%s: point must be a mapping" % tag)
        frequency = _number(point, "frequency_hz", tag)
        if frequency <= 0.0:
            raise ValueError("%s: frequency_hz must be > 0, got %g" % (tag, frequency))
        if previous is not None and frequency <= previous:
            raise ValueError(
                "%s: frequencies must increase strictly (%g Hz after %g Hz)"
                % (tag, frequency, previous)
            )
        previous = frequency
        applied = _number(point, "field_applied_v_m", tag)
        required = _number(point, "field_required_v_m", tag)
        if applied <= 0.0:
            raise ValueError("%s: field_applied_v_m must be > 0, got %g" % (tag, applied))
        if required <= 0.0:
            raise ValueError(
                "%s: field_required_v_m must be > 0, got %g" % (tag, required)
            )
        margin = field_margin_db(applied, required)
        out.append(
            {
                "frequency_hz": frequency,
                "field_applied_v_m": applied,
                "field_required_v_m": required,
                "margin_db": margin,
                "category": categorize_field_point(margin),
                "degradation_observed": _flag(point, "degradation_observed", tag),
            }
        )
    return out


def sweep_band_coverage(points, band=DEFAULT_METHOD_BAND_HZ, rel_tol=BAND_EDGE_REL_TOL):
    """Report whether one sweep reaches both edges of the declared method band."""
    low, high = validate_method_band(band)
    slack = _scalar(rel_tol, "rel_tol")
    if slack < 0.0:
        raise ValueError("rel_tol must be >= 0, got %g" % slack)
    if not points:
        raise ValueError("sweep_band_coverage: points must not be empty")
    first = points[0]["frequency_hz"]
    last = points[-1]["frequency_hz"]
    reaches_low = first <= low or math.isclose(first, low, rel_tol=slack, abs_tol=0.0)
    reaches_high = last >= high or math.isclose(last, high, rel_tol=slack, abs_tol=0.0)
    shortfalls = []
    if not reaches_low:
        shortfalls.append(
            "sweep starts at %g Hz, above the %g Hz lower edge of the method band"
            % (first, low)
        )
    if not reaches_high:
        shortfalls.append(
            "sweep stops at %g Hz, below the %g Hz upper edge of the method band"
            % (last, high)
        )
    return {
        "first_frequency_hz": first,
        "last_frequency_hz": last,
        "reaches_low_edge": reaches_low,
        "reaches_high_edge": reaches_high,
        "shortfalls": shortfalls,
    }


def degradation_frequencies_hz(points):
    """Frequencies at which the performance monitor recorded a degradation."""
    return [p["frequency_hz"] for p in points if p["degradation_observed"]]


def susceptibility_threshold_hz(points):
    """Lowest frequency at which the object stopped performing, or None."""
    hits = degradation_frequencies_hz(points)
    return min(hits) if hits else None


def governing_point(points):
    """Worst exposure point: least field margin, ties broken on lower frequency."""
    if not points:
        raise ValueError("governing_point: points must not be empty")
    worst = points[0]
    for point in points[1:]:
        if point["margin_db"] < worst["margin_db"] - DB_TOL:
            worst = point
        elif (
            abs(point["margin_db"] - worst["margin_db"]) <= DB_TOL
            and point["frequency_hz"] < worst["frequency_hz"]
        ):
            worst = point
    return worst


def assess_radiated_electric_susceptibility_overview(
    records, band=DEFAULT_METHOD_BAND_HZ, rel_tol=BAND_EDGE_REL_TOL
):
    """Full clause 5.4.11.1 assessment of a radiated electric susceptibility run.

    records: a list of mappings, each with an exposure object designation
    ("object") and its sweep ("points"). Both the unit enclosure and the
    interconnecting cabling must appear, each exactly once.
    """
    where = "susceptibility_records"
    if not isinstance(records, (list, tuple)):
        raise ValueError("%s: records must be a list" % where)
    if len(records) == 0:
        raise ValueError("%s: at least one exposure object is required" % where)
    low, high = validate_method_band(band)

    objects = {}
    for index, record in enumerate(records):
        tag = "%s[%d]" % (where, index)
        if not isinstance(record, dict):
            raise ValueError("%s: record must be a mapping" % tag)
        if "object" not in record:
            raise ValueError("%s: missing required field 'object'" % tag)
        if "points" not in record:
            raise ValueError("%s: missing required field 'points'" % tag)
        role = normalize_exposure_object(record["object"])
        if role in objects:
            raise ValueError("%s: exposure object %r declared twice" % (tag, role))
        objects[role] = validate_exposure_sweep(record["points"])

    findings = []
    limitations = []
    summaries = {}

    absent = [role for role in EXPOSURE_OBJECTS if role not in objects]
    for role in absent:
        findings.append(
            "no exposure sweep is recorded for the %s, so the aim is not "
            "demonstrated over it" % role
        )

    for role in EXPOSURE_OBJECTS:
        if role not in objects:
            continue
        points = objects[role]
        coverage = sweep_band_coverage(points, (low, high), rel_tol)
        under = [p for p in points if p["category"] == CATEGORY_UNDER]
        above = [p for p in points if p["category"] == CATEGORY_ABOVE]
        threshold = susceptibility_threshold_hz(points)
        worst = governing_point(points)
        summaries[role] = {
            "coverage": coverage,
            "under_level_count": len(under),
            "above_level_count": len(above),
            "degradation_frequencies_hz": degradation_frequencies_hz(points),
            "susceptibility_threshold_hz": threshold,
            "governing_point": worst,
            "point_count": len(points),
        }
        for message in coverage["shortfalls"]:
            findings.append("%s: %s" % (role, message))
        for point in under:
            findings.append(
                "%s: at %g Hz the applied field was %g dB under the required %g V/m, "
                "so that frequency was never exposed to the requirement"
                % (role, point["frequency_hz"], -point["margin_db"], point["field_required_v_m"])
            )
        if threshold is not None:
            findings.append(
                "%s: performance degraded from %g Hz upward while the field was applied"
                % (role, threshold)
            )
        for point in above:
            limitations.append(
                "%s: at %g Hz the applied field was %g dB above the requirement, an "
                "overtest rather than a shortfall"
                % (role, point["frequency_hz"], point["margin_db"])
            )

    governing_object = None
    if summaries:
        governing_object = min(
            summaries,
            key=lambda role: (
                summaries[role]["governing_point"]["margin_db"],
                summaries[role]["governing_point"]["frequency_hz"],
                EXPOSURE_OBJECTS.index(role),
            ),
        )

    return {
        "method_band_hz": (low, high),
        "objects_present": sorted(objects),
        "objects_absent": absent,
        "summaries": summaries,
        "governing_object": governing_object,
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_MET if not findings else VERDICT_NOT_MET,
    }

#!/usr/bin/env python3
"""Radiated electric-field emission objective, ECSS-E-ST-20-07C clause 5.4.6.1.

Paraphrased procedure, no verbatim standard text. The clause states the aim of
the method: show that the electric field the unit radiates -- from its own
enclosure and from the interconnecting cabling run with it -- stays inside the
applicable radiated-emission limit everywhere in the method band, with the
field captured in both antenna polarizations. This module turns that aim into
a deterministic demonstration:

  method band   -> validated span
  source x pol  -> scan -> margin per frequency -> category
  per scan      -> worst-case frequency -> governing emitter
  coverage      -> band-edge gaps recorded as findings, not silently absorbed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. A margin is a difference of two float levels,
# so a field strength sitting exactly on its limit can land a few units in the
# last place either side of zero. The tolerance absorbs that representation
# error only; it never relaxes the applicable limit.
DB_TOL = 1e-9

# Default span of the radiated electric-field emission method, hertz. A
# project that declares its own span passes it in; this is only the fallback.
DEFAULT_METHOD_BAND_HZ = (30.0e6, 18.0e9)

# Relative slack allowed at a band edge before a scan is called short of it.
BAND_EDGE_REL_TOL = 0.01

# The aim is stated over what radiates: the unit enclosure itself and the
# interconnecting cabling harnessed to it. They are separate emitters.
EMISSION_SOURCES = ("unit-enclosure", "interconnecting-cabling")

# The field is a vector quantity; a single-polarization scan measures one
# projection of it, so the aim is stated over the polarization pair.
POLARIZATIONS = ("vertical", "horizontal")

CATEGORY_WITHIN = "within-limit"
CATEGORY_AT_LIMIT = "at-limit"
CATEGORY_EXCEEDANCE = "exceedance"
CATEGORIES = (CATEGORY_WITHIN, CATEGORY_AT_LIMIT, CATEGORY_EXCEEDANCE)

VERDICT_MET = "objective-met"
VERDICT_NOT_MET = "objective-not-demonstrated"


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


def validate_method_band(band=DEFAULT_METHOD_BAND_HZ):
    """Validate the declared method band and return it as a float pair."""
    where = "method_band_hz"
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("%s: band must be a (low, high) pair" % where)
    low = _number({"v": band[0]}, "v", "%s.low" % where)
    high = _number({"v": band[1]}, "v", "%s.high" % where)
    if low <= 0.0:
        raise ValueError("%s: low edge must be > 0, got %g" % (where, low))
    if high <= low:
        raise ValueError(
            "%s: high edge %g Hz must exceed low edge %g Hz" % (where, high, low)
        )
    return (low, high)


def normalize_emission_source(source):
    """Return the recognized emitter name for a raw designation."""
    if not isinstance(source, str):
        raise ValueError("emission source must be a string, got %r" % (source,))
    key = source.strip().lower()
    if key not in EMISSION_SOURCES:
        raise ValueError(
            "unrecognized emission source %r; recognized: %s"
            % (source, ", ".join(EMISSION_SOURCES))
        )
    return key


def normalize_polarization(polarization):
    """Return the recognized antenna polarization for a raw designation."""
    if not isinstance(polarization, str):
        raise ValueError("polarization must be a string, got %r" % (polarization,))
    key = polarization.strip().lower()
    if key not in POLARIZATIONS:
        raise ValueError(
            "unrecognized polarization %r; recognized: %s"
            % (polarization, ", ".join(POLARIZATIONS))
        )
    return key


def validate_field_scan(points):
    """Validate one recorded field scan and return its normalized points."""
    where = "field_scan"
    if not isinstance(points, (list, tuple)):
        raise ValueError("%s: points must be a list" % where)
    if len(points) == 0:
        raise ValueError("%s: at least one recorded point is required" % where)
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
        out.append(
            {
                "frequency_hz": frequency,
                "level_dbuv_m": _number(point, "level_dbuv_m", tag),
                "limit_dbuv_m": _number(point, "limit_dbuv_m", tag),
            }
        )
    return out


def scan_band_coverage(points, band=DEFAULT_METHOD_BAND_HZ, rel_tol=BAND_EDGE_REL_TOL):
    """Report whether a scan reaches both edges of the declared method band."""
    low, high = validate_method_band(band)
    tol = _number({"v": rel_tol}, "v", "rel_tol")
    if not 0.0 <= tol < 1.0:
        raise ValueError("rel_tol must lie in [0, 1), got %g" % tol)
    scan = validate_field_scan(points)
    first = scan[0]["frequency_hz"]
    last = scan[-1]["frequency_hz"]
    reaches_low = first <= low or math.isclose(first, low, rel_tol=tol, abs_tol=0.0)
    reaches_high = last >= high or math.isclose(last, high, rel_tol=tol, abs_tol=0.0)
    return {
        "band_hz": (low, high),
        "first_hz": first,
        "last_hz": last,
        "reaches_low_edge": reaches_low,
        "reaches_high_edge": reaches_high,
        "covers_band": reaches_low and reaches_high,
    }


def point_margin_db(point):
    """Margin of a single point: applicable limit minus the recorded field."""
    return point["limit_dbuv_m"] - point["level_dbuv_m"]


def categorize_point(point, tol_db=DB_TOL):
    """Categorize one frequency by where its field sits against the limit."""
    tol = _number({"v": tol_db}, "v", "tol_db")
    if tol < 0.0:
        raise ValueError("tol_db must be >= 0, got %g" % tol)
    margin = point_margin_db(point)
    if math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=tol):
        return CATEGORY_AT_LIMIT
    if margin > 0.0:
        return CATEGORY_WITHIN
    return CATEGORY_EXCEEDANCE


def grade_scan(source, polarization, points, band=DEFAULT_METHOD_BAND_HZ, tol_db=DB_TOL):
    """Grade one source/polarization scan and reduce it to its worst case."""
    emitter = normalize_emission_source(source)
    plane = normalize_polarization(polarization)
    scan = validate_field_scan(points)
    coverage = scan_band_coverage(scan, band)
    graded = []
    counts = dict((category, 0) for category in CATEGORIES)
    for point in scan:
        category = categorize_point(point, tol_db)
        counts[category] += 1
        graded.append(
            {
                "frequency_hz": point["frequency_hz"],
                "level_dbuv_m": point["level_dbuv_m"],
                "limit_dbuv_m": point["limit_dbuv_m"],
                "margin_db": point_margin_db(point),
                "category": category,
            }
        )
    worst = min(graded, key=lambda g: (g["margin_db"], g["frequency_hz"]))
    return {
        "source": emitter,
        "polarization": plane,
        "points": graded,
        "counts": counts,
        "coverage": coverage,
        "worst_case": worst,
        "within_limits": counts[CATEGORY_EXCEEDANCE] == 0,
    }


def governing_emitter(scan_reports):
    """Return the scan report holding the smallest worst-case margin."""
    if not isinstance(scan_reports, (list, tuple)) or len(scan_reports) == 0:
        raise ValueError("governing_emitter: at least one graded scan is required")
    return min(
        scan_reports,
        key=lambda r: (
            r["worst_case"]["margin_db"],
            r["worst_case"]["frequency_hz"],
            r["source"],
            r["polarization"],
        ),
    )


def missing_scan_pairs(scans):
    """Return the source/polarization combinations the record never recorded."""
    if not isinstance(scans, dict):
        raise ValueError("scans: must be a mapping of source -> polarization scans")
    present = set()
    for source in scans:
        emitter = normalize_emission_source(source)
        per_source = scans[source]
        if not isinstance(per_source, dict):
            raise ValueError(
                "scans[%s]: must be a mapping of polarization -> points" % emitter
            )
        for polarization in per_source:
            present.add((emitter, normalize_polarization(polarization)))
    return tuple(
        (emitter, plane)
        for emitter in EMISSION_SOURCES
        for plane in POLARIZATIONS
        if (emitter, plane) not in present
    )


def assess_radiated_emission_objective(
    scans,
    band=DEFAULT_METHOD_BAND_HZ,
    require_full_band=True,
    tol_db=DB_TOL,
):
    """Full clause 5.4.6.1 objective demonstration.

    scans: mapping of emission source -> mapping of polarization -> recorded
    points. The aim is stated over what radiates and over the field as a
    vector, so the unit enclosure and the interconnecting cabling must each
    appear in both polarizations. A record short of that cannot demonstrate
    the aim and is rejected rather than graded.
    """
    if not isinstance(scans, dict):
        raise ValueError("scans: must be a mapping of source -> polarization scans")
    if len(scans) == 0:
        raise ValueError("scans: at least one emission source must be recorded")

    normalized = {}
    for source in scans:
        emitter = normalize_emission_source(source)
        if emitter in normalized:
            raise ValueError("scans: source %r declared more than once" % emitter)
        per_source = scans[source]
        if not isinstance(per_source, dict):
            raise ValueError(
                "scans[%s]: must be a mapping of polarization -> points" % emitter
            )
        planes = {}
        for polarization in per_source:
            plane = normalize_polarization(polarization)
            if plane in planes:
                raise ValueError(
                    "scans[%s]: polarization %r declared more than once"
                    % (emitter, plane)
                )
            planes[plane] = per_source[polarization]
        normalized[emitter] = planes

    missing = missing_scan_pairs(normalized)
    if missing:
        raise ValueError(
            "scans: the objective is stated over both emitters in both "
            "polarizations; missing: %s"
            % ", ".join("%s/%s" % pair for pair in missing)
        )

    span = validate_method_band(band)
    reports = [
        grade_scan(emitter, plane, normalized[emitter][plane], span, tol_db)
        for emitter in EMISSION_SOURCES
        for plane in POLARIZATIONS
    ]

    findings = []
    limitations = []
    for report in reports:
        tag = "%s/%s" % (report["source"], report["polarization"])
        for entry in report["points"]:
            if entry["category"] == CATEGORY_EXCEEDANCE:
                findings.append(
                    "limit exceeded on %s at %g Hz by %.1f dB"
                    % (tag, entry["frequency_hz"], -entry["margin_db"])
                )
            elif entry["category"] == CATEGORY_AT_LIMIT:
                limitations.append(
                    "field sits on the limit on %s at %g Hz"
                    % (tag, entry["frequency_hz"])
                )
        coverage = report["coverage"]
        if not coverage["covers_band"]:
            message = "scan on %s stops short of the method band (%g-%g Hz recorded)" % (
                tag,
                coverage["first_hz"],
                coverage["last_hz"],
            )
            if require_full_band:
                findings.append(message)
            else:
                limitations.append(message)

    governing = governing_emitter(reports)
    return {
        "band_hz": span,
        "scans": reports,
        "governing_source": governing["source"],
        "governing_polarization": governing["polarization"],
        "governing_point": governing["worst_case"],
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_MET if not findings else VERDICT_NOT_MET,
    }

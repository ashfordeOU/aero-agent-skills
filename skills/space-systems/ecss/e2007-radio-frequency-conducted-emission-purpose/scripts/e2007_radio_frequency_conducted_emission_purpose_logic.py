#!/usr/bin/env python3
"""Radio-frequency conducted-emission objective, ECSS-E-ST-20-07C clause 5.4.3.1.

Paraphrased procedure, no verbatim standard text. The clause states the aim of
the method: show that what the unit puts back onto its power-input lead and
onto the matching power-return lead stays inside the applicable
conducted-emission limit across the method band. This module turns that aim
into a deterministic demonstration:

  method band  -> validated span
  lead sweeps  -> margin per frequency -> category
  per lead     -> worst-case frequency -> governing lead
  coverage     -> band-edge gaps recorded as findings, not silently absorbed

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Decibel comparison tolerance. A margin is a difference of two float levels,
# so a level sitting exactly on its limit can land a few units in the last
# place either side of zero. The tolerance absorbs that representation error
# only; it never relaxes the applicable limit.
DB_TOL = 1e-9

# Default span of the higher-band conducted-emission method, hertz. A project
# that declares its own span passes it in; this is only the fallback.
DEFAULT_METHOD_BAND_HZ = (2.0e6, 100.0e6)

# Relative slack allowed at a band edge before the sweep is called short of it.
BAND_EDGE_REL_TOL = 0.01

# The aim names the lead carrying power in and the lead carrying it back.
LEAD_ROLES = ("power-input", "power-return")

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


def normalize_lead_role(role):
    """Return the recognized lead role for a raw designation."""
    if not isinstance(role, str):
        raise ValueError("lead role must be a string, got %r" % (role,))
    key = role.strip().lower()
    if key not in LEAD_ROLES:
        raise ValueError(
            "unrecognized lead role %r; recognized: %s" % (role, ", ".join(LEAD_ROLES))
        )
    return key


def validate_emission_sweep(points):
    """Validate one lead's recorded sweep and return normalized points."""
    where = "emission_sweep"
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
                "level_dbuv": _number(point, "level_dbuv", tag),
                "limit_dbuv": _number(point, "limit_dbuv", tag),
            }
        )
    return out


def sweep_band_coverage(points, band=DEFAULT_METHOD_BAND_HZ, rel_tol=BAND_EDGE_REL_TOL):
    """Report whether a sweep reaches both edges of the declared method band."""
    low, high = validate_method_band(band)
    tol = _number({"v": rel_tol}, "v", "rel_tol")
    if not 0.0 <= tol < 1.0:
        raise ValueError("rel_tol must lie in [0, 1), got %g" % tol)
    sweep = validate_emission_sweep(points)
    first = sweep[0]["frequency_hz"]
    last = sweep[-1]["frequency_hz"]
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
    """Margin of a single point: applicable limit minus the recorded level."""
    return point["limit_dbuv"] - point["level_dbuv"]


def categorize_point(point, tol_db=DB_TOL):
    """Categorize one frequency by where its level sits against the limit."""
    tol = _number({"v": tol_db}, "v", "tol_db")
    if tol < 0.0:
        raise ValueError("tol_db must be >= 0, got %g" % tol)
    margin = point_margin_db(point)
    if math.isclose(margin, 0.0, rel_tol=0.0, abs_tol=tol):
        return CATEGORY_AT_LIMIT
    if margin > 0.0:
        return CATEGORY_WITHIN
    return CATEGORY_EXCEEDANCE


def grade_lead_emission(role, points, band=DEFAULT_METHOD_BAND_HZ, tol_db=DB_TOL):
    """Grade one lead sweep and reduce it to its worst-case frequency."""
    designation = normalize_lead_role(role)
    sweep = validate_emission_sweep(points)
    coverage = sweep_band_coverage(sweep, band)
    graded = []
    counts = dict((category, 0) for category in CATEGORIES)
    for point in sweep:
        category = categorize_point(point, tol_db)
        counts[category] += 1
        graded.append(
            {
                "frequency_hz": point["frequency_hz"],
                "level_dbuv": point["level_dbuv"],
                "limit_dbuv": point["limit_dbuv"],
                "margin_db": point_margin_db(point),
                "category": category,
            }
        )
    worst = min(graded, key=lambda g: (g["margin_db"], g["frequency_hz"]))
    return {
        "lead": designation,
        "points": graded,
        "counts": counts,
        "coverage": coverage,
        "worst_case": worst,
        "within_limits": counts[CATEGORY_EXCEEDANCE] == 0,
    }


def governing_lead(lead_reports):
    """Return the lead report holding the smallest worst-case margin."""
    if not isinstance(lead_reports, (list, tuple)) or len(lead_reports) == 0:
        raise ValueError("governing_lead: at least one graded lead is required")
    return min(
        lead_reports,
        key=lambda r: (r["worst_case"]["margin_db"], r["worst_case"]["frequency_hz"]),
    )


def assess_conducted_emission_objective(
    lead_sweeps,
    band=DEFAULT_METHOD_BAND_HZ,
    require_full_band=True,
    tol_db=DB_TOL,
):
    """Full clause 5.4.3.1 objective demonstration.

    lead_sweeps: mapping of lead role -> list of recorded sweep points. Both
    the power-input lead and its power-return lead must appear; the aim of the
    method is stated over the pair, so a single-lead record cannot demonstrate
    it and is rejected rather than graded.
    """
    if not isinstance(lead_sweeps, dict):
        raise ValueError("lead_sweeps: must be a mapping of lead role -> points")
    if len(lead_sweeps) == 0:
        raise ValueError("lead_sweeps: at least one lead must be recorded")
    normalized = {}
    for role in lead_sweeps:
        key = normalize_lead_role(role)
        if key in normalized:
            raise ValueError("lead_sweeps: lead %r declared more than once" % key)
        normalized[key] = lead_sweeps[role]
    missing = tuple(role for role in LEAD_ROLES if role not in normalized)
    if missing:
        raise ValueError(
            "lead_sweeps: the objective is stated over the input lead and its "
            "return lead; missing: %s" % ", ".join(missing)
        )

    span = validate_method_band(band)
    reports = [
        grade_lead_emission(role, normalized[role], span, tol_db)
        for role in LEAD_ROLES
    ]

    findings = []
    limitations = []
    for report in reports:
        for entry in report["points"]:
            if entry["category"] == CATEGORY_EXCEEDANCE:
                findings.append(
                    "limit exceeded on %s at %g Hz by %.1f dB"
                    % (report["lead"], entry["frequency_hz"], -entry["margin_db"])
                )
            elif entry["category"] == CATEGORY_AT_LIMIT:
                limitations.append(
                    "level sits on the limit on %s at %g Hz"
                    % (report["lead"], entry["frequency_hz"])
                )
        coverage = report["coverage"]
        if not coverage["covers_band"]:
            message = "sweep on %s stops short of the method band (%g-%g Hz recorded)" % (
                report["lead"],
                coverage["first_hz"],
                coverage["last_hz"],
            )
            if require_full_band:
                findings.append(message)
            else:
                limitations.append(message)

    governing = governing_lead(reports)
    return {
        "band_hz": span,
        "leads": reports,
        "governing_lead": governing["lead"],
        "governing_point": governing["worst_case"],
        "findings": findings,
        "limitations": limitations,
        "verdict": VERDICT_MET if not findings else VERDICT_NOT_MET,
    }

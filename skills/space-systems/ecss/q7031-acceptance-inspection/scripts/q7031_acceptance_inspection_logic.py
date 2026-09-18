#!/usr/bin/env python3
"""Acceptance inspection of an applied paint batch or painted area.

Anchor: ECSS-Q-ST-70-31C, the Verification clause on acceptance inspection.
The procedure below is a paraphrased, implementable restatement -- no verbatim
standard text. Offline, deterministic, Python standard library only.

Acceptance is granted per batch and per painted area, not per programme. Each
area owes a sized set of dry-film-thickness readings, an adhesion result, a
cured-state check and an inspection record that names who inspected it, when,
with what instrument and against which calibration. This module sizes the
reading set, reduces the readings, grades them against the specification,
grades the record itself, and issues the batch disposition.
"""

import math

__all__ = [
    "ADHESION_GRADES",
    "REQUIRED_RECORD_FIELDS",
    "DEFAULT_POINTS_PER_M2",
    "MINIMUM_POINTS",
    "parse_day",
    "measurement_points_required",
    "thickness_statistics",
    "thickness_findings",
    "adhesion_findings",
    "calibration_valid_on",
    "record_findings",
    "assess_batch_acceptance",
    "assess_acceptance_campaign",
]

# A reading that lands exactly on a specification bound is inside it. Decimal
# micrometre readings reduced by a mean land a few ULP either side of a decimal
# bound depending on the maths library, so these tolerances absorb that and
# nothing else: the specification limit itself is never widened.
SPEC_REL_TOL = 1e-9
SPEC_ABS_TOL = 1e-12

DEFAULT_POINTS_PER_M2 = 5.0
MINIMUM_POINTS = 5

# Cross-cut adhesion is reported on an ordered scale where the lower number is
# the better result: 0 is a fully intact lattice, 5 is gross detachment.
ADHESION_GRADES = (0, 1, 2, 3, 4, 5)
DEFAULT_MAX_ADHESION_GRADE = 1

REQUIRED_RECORD_FIELDS = (
    "batch_id",
    "unit_id",
    "inspector_id",
    "inspection_day",
    "instrument_id",
    "calibration_due_day",
    "paint_lot_id",
)


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, bound):
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=SPEC_REL_TOL, abs_tol=SPEC_ABS_TOL)


def parse_day(label, text):
    """Parse an ISO calendar day into a (year, month, day) ordinal-comparable tuple.

    Kept deliberately strict: an ambiguous day-first or month-first string is a
    record defect, and a record defect is what this clause is looking for.
    """
    if not isinstance(text, str):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, text))
    parts = text.strip().split("-")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError("%s must be an ISO yyyy-mm-dd string, got %r" % (label, text))
    year, month, day = (int(p) for p in parts)
    if len(parts[0]) != 4:
        raise ValueError("%s needs a four-digit year, got %r" % (label, text))
    if not 1 <= month <= 12:
        raise ValueError("%s has no month %d" % (label, month))
    days_in_month = [31, 29 if _is_leap(year) else 28, 31, 30, 31, 30,
                     31, 31, 30, 31, 30, 31][month - 1]
    if not 1 <= day <= days_in_month:
        raise ValueError("%s has no day %d in month %d of %d" % (label, day, month, year))
    return (year, month, day)


def _is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def measurement_points_required(area_m2, points_per_m2=DEFAULT_POINTS_PER_M2,
                                minimum=MINIMUM_POINTS):
    """Size the dry-film-thickness reading set for one painted area.

    Integer arithmetic throughout: a partial reading does not exist, so the
    per-area draw rounds up and a floor applies so that a small fitting is not
    accepted on one or two points.
    """
    area = _finite_number(area_m2, "area_m2")
    if area <= 0.0:
        raise ValueError("painted area must be strictly positive, got %r" % (area_m2,))
    density = _finite_number(points_per_m2, "points_per_m2")
    if density <= 0.0:
        raise ValueError("points_per_m2 must be strictly positive, got %r" % (points_per_m2,))
    if isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 1:
        raise ValueError("minimum must be a positive integer, got %r" % (minimum,))
    return max(minimum, math.ceil(area * density - SPEC_ABS_TOL))


def thickness_statistics(readings_um):
    """Reduce a set of dry-film-thickness readings to the numbers acceptance uses."""
    if not isinstance(readings_um, (list, tuple)) or not readings_um:
        raise ValueError("at least one thickness reading is required")
    values = []
    for index, reading in enumerate(readings_um):
        value = _finite_number(reading, "reading %d" % index)
        if value <= 0.0:
            raise ValueError("thickness reading %d must be strictly positive" % index)
        values.append(value)
    count = len(values)
    mean = sum(values) / count
    if count > 1:
        variance = sum((v - mean) ** 2 for v in values) / (count - 1)
        deviation = math.sqrt(variance)
    else:
        deviation = 0.0
    return {
        "count": count,
        "mean_um": mean,
        "minimum_um": min(values),
        "maximum_um": max(values),
        "std_dev_um": deviation,
    }


def thickness_findings(stats, spec):
    """Grade the reduced readings against the dry-film-thickness specification.

    Three rules run together: no single point below the floor, no single point
    above the ceiling, and the mean inside the nominal band. A mean inside the
    band does not rescue a point below the floor, because the thin point is
    where the coating fails.
    """
    if not isinstance(spec, dict):
        raise ValueError("thickness spec must be a mapping, got %r" % type(spec))
    minimum = _finite_number(spec.get("minimum_um"), "spec minimum_um")
    maximum = _finite_number(spec.get("maximum_um"), "spec maximum_um")
    if minimum <= 0.0:
        raise ValueError("spec minimum_um must be strictly positive")
    if maximum < minimum:
        raise ValueError("thickness specification is inverted")
    mean_low = _finite_number(spec.get("mean_low_um", minimum), "spec mean_low_um")
    mean_high = _finite_number(spec.get("mean_high_um", maximum), "spec mean_high_um")
    if mean_high < mean_low:
        raise ValueError("mean thickness band is inverted")
    findings = []
    if not _at_or_below(minimum, stats["minimum_um"]):
        findings.append("thickness-point-below-minimum")
    if not _at_or_below(stats["maximum_um"], maximum):
        findings.append("thickness-point-above-maximum")
    if not (_at_or_below(mean_low, stats["mean_um"]) and _at_or_below(stats["mean_um"], mean_high)):
        findings.append("mean-thickness-outside-band")
    required = spec.get("points_required")
    if required is not None:
        if isinstance(required, bool) or not isinstance(required, int) or required < 1:
            raise ValueError("points_required must be a positive integer, got %r" % (required,))
        if stats["count"] < required:
            findings.append("thickness-points-short")
    return sorted(findings)


def adhesion_findings(result, maximum_grade=DEFAULT_MAX_ADHESION_GRADE):
    """Grade the adhesion result attached to the batch.

    An absent adhesion result is a finding rather than a pass: adhesion is the
    one property the thickness gauge cannot see.
    """
    if isinstance(maximum_grade, bool) or maximum_grade not in ADHESION_GRADES:
        raise ValueError("maximum_grade must be one of %s, got %r" % (ADHESION_GRADES, maximum_grade))
    if result is None:
        return ["adhesion-result-absent"]
    if isinstance(result, bool) or result not in ADHESION_GRADES:
        raise ValueError("adhesion grade must be one of %s, got %r" % (ADHESION_GRADES, result))
    return [] if result <= maximum_grade else ["adhesion-grade-exceeded"]


def calibration_valid_on(calibration_due_day, inspection_day):
    """True when the gauge calibration had not lapsed on the inspection day.

    A due day equal to the inspection day is still valid: calibration runs to
    the end of the day it is due.
    """
    due = parse_day("calibration_due_day", calibration_due_day)
    used = parse_day("inspection_day", inspection_day)
    return used <= due


def record_findings(record, required_fields=REQUIRED_RECORD_FIELDS):
    """Findings about the inspection record itself, independent of the readings."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % type(record))
    findings = []
    missing = []
    for field in required_fields:
        value = record.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(field)
            findings.append("record-field-missing:%s" % field)
    if "inspection_day" not in missing and "calibration_due_day" not in missing:
        if not calibration_valid_on(record["calibration_due_day"], record["inspection_day"]):
            findings.append("instrument-calibration-lapsed")
    return sorted(findings)


def assess_batch_acceptance(batch):
    """Grade one painted batch or area and issue its acceptance disposition."""
    if not isinstance(batch, dict):
        raise ValueError("batch must be a mapping, got %r" % type(batch))
    name = batch.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("batch requires a non-empty name")
    required = measurement_points_required(
        batch.get("area_m2"),
        batch.get("points_per_m2", DEFAULT_POINTS_PER_M2),
        batch.get("minimum_points", MINIMUM_POINTS),
    )
    stats = thickness_statistics(batch.get("readings_um"))
    spec = dict(batch.get("thickness_spec") or {})
    spec["points_required"] = required
    findings = list(thickness_findings(stats, spec))
    findings.extend(adhesion_findings(
        batch.get("adhesion_grade"),
        batch.get("maximum_adhesion_grade", DEFAULT_MAX_ADHESION_GRADE),
    ))
    if batch.get("cure_verified") is not True:
        findings.append("cure-not-verified")
    findings.extend(record_findings(batch.get("record", {})))
    findings = sorted(set(findings))
    record_only = all(
        f.startswith("record-field-missing") or f == "instrument-calibration-lapsed"
        for f in findings
    )
    if not findings:
        disposition = "accepted"
    elif record_only:
        disposition = "record-hold"
    else:
        disposition = "rejected"
    return {
        "name": name.strip(),
        "points_required": required,
        "statistics": stats,
        "findings": findings,
        "disposition": disposition,
        "accepted": disposition == "accepted",
    }


def assess_acceptance_campaign(batches):
    """Grade a set of batches; the campaign passes only when every batch does."""
    if not isinstance(batches, (list, tuple)) or not batches:
        raise ValueError("at least one batch is required")
    results = [assess_batch_acceptance(item) for item in batches]
    names = [item["name"] for item in results]
    if len(set(names)) != len(names):
        raise ValueError("batch names must be unique within a campaign")
    open_findings = sorted(
        "%s:%s" % (item["name"], finding)
        for item in results
        for finding in item["findings"]
    )
    return {
        "batches": results,
        "rejected_batches": sorted(i["name"] for i in results if i["disposition"] == "rejected"),
        "held_batches": sorted(i["name"] for i in results if i["disposition"] == "record-hold"),
        "open_findings": open_findings,
        "campaign_accepted": not open_findings,
    }

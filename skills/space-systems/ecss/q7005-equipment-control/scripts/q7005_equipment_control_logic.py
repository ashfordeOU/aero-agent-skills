"""Control of the instruments and consumables an IR contamination analysis uses.

Anchor: ECSS-Q-ST-70-05C, the quality assurance clause covering control
of the spectrometer, the measurement cells and the sampling equipment
(paraphrased into an implementable procedure; no standard text is
reproduced).

Procedure implemented here:

1. A calibration interval is counted in whole calendar months, not in a
   fixed number of days. Adding months to a month end lands on the end
   of the month it reaches, and February moves with the leap year.
2. Currency is a question about the analysis day, not about today. The
   number worth reporting is the days left on the day the sample is run,
   and a certificate that expires inside the analysis campaign was
   already short when the campaign started.
3. Accuracy is a ratio, never a bare number. An instrument is capable
   when the tolerance it has to police is several times larger than the
   uncertainty it carries; the uncertainty alone says nothing.
4. A cell has a geometry as well as a calibration. A pathlength that has
   drifted from nominal scales every concentration taken through that
   cell, so the deviation is graded as a fraction of nominal.
5. Everything the sample touches contributes its own organic background.
   A cell blank or a wipe blank is graded against the quantitation limit
   it will be measured beside: a blank of comparable size does not add
   noise, it consumes the measurement.
6. Sampling consumables are controlled by a precleaning certificate and
   a shelf life, both of which expire, and an expired lot is a blocked
   item rather than a note.

Stdlib only, offline, deterministic.
"""

import calendar
import datetime

KIND_SPECTROMETER = "spectrometer"
KIND_CELL = "measurement-cell"
KIND_SAMPLING = "sampling-equipment"

VALID_ITEM_KINDS = (KIND_SPECTROMETER, KIND_CELL, KIND_SAMPLING)

REQUIRED_FIELDS = {
    KIND_SPECTROMETER: (
        "last_calibration",
        "interval_months",
        "wavenumber_tolerance_per_cm",
        "wavenumber_uncertainty_per_cm",
    ),
    KIND_CELL: (
        "last_calibration",
        "interval_months",
        "nominal_pathlength_um",
        "measured_pathlength_um",
        "blank_level_mg_m2",
        "quantitation_limit_mg_m2",
    ),
    KIND_SAMPLING: (
        "precleaning_certificate",
        "lot_release_date",
        "shelf_life_months",
        "blank_level_mg_m2",
        "quantitation_limit_mg_m2",
    ),
}

CLEARED = "cleared"
CLEARED_WITH_WATCH = "cleared-with-watch"
BLOCKED = "blocked"

DEFAULT_POLICY = {
    "minimum_capability_ratio": 4.0,
    "maximum_blank_fraction": 0.5,
    "pathlength_tolerance_fraction": 0.05,
    "watch_window_days": 30,
}

# Ratios are quotients, so a value that should sit exactly on a floor can
# land a few units in the last place either side of it.
RATIO_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _whole_months(label, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be a whole number of months, got %r"
                         % (label, value))
    if value <= 0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return value


def parse_date(text):
    """Parse an ISO calendar date, raising on anything else."""
    if isinstance(text, datetime.date):
        return text
    if not isinstance(text, str):
        raise ValueError("date must be an ISO yyyy-mm-dd string, got %r" % (text,))
    parts = text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("date %r is not in yyyy-mm-dd form" % (text,))
    try:
        year, month, day = (int(p) for p in parts)
        return datetime.date(year, month, day)
    except ValueError:
        raise ValueError("date %r is not a real calendar date" % (text,))


def add_calendar_months(start, months):
    """Advance a date by whole calendar months, clamping to the month end."""
    begin = parse_date(start)
    count = _whole_months("months", months)
    total = begin.month - 1 + count
    year = begin.year + total // 12
    month = total % 12 + 1
    day = min(begin.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def calibration_due(last_calibration, interval_months):
    """Date a calibration falls due, counted in whole calendar months."""
    return add_calendar_months(last_calibration, interval_months)


def days_remaining(due, on_date):
    """Whole days left on a due date, negative once it has passed."""
    return (parse_date(due) - parse_date(on_date)).days


def capability_ratio(tolerance, uncertainty):
    """Tolerance policed divided by the uncertainty carried."""
    tol = _numeric("tolerance", tolerance, 0.0)
    unc = _numeric("uncertainty", uncertainty, 0.0)
    if unc <= 0.0:
        raise ValueError("uncertainty must be greater than zero")
    return tol / unc


def deviation_fraction(measured, nominal):
    """Absolute deviation from nominal, as a fraction of nominal."""
    meas = _numeric("measured", measured, 0.0)
    nom = _numeric("nominal", nominal, 0.0)
    if nom <= 0.0:
        raise ValueError("nominal must be greater than zero")
    return abs(meas - nom) / nom


def blank_fraction(blank_level, quantitation_limit):
    """Blank contribution as a fraction of the quantitation limit."""
    blank = _numeric("blank_level", blank_level, 0.0)
    limit = _numeric("quantitation_limit", quantitation_limit, 0.0)
    if limit <= 0.0:
        raise ValueError("quantitation_limit must be greater than zero")
    return blank / limit


def resolved_policy(policy=None):
    """Merge a caller policy over the defaults and validate it."""
    merged = dict(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict):
            raise ValueError("policy must be a mapping")
        unknown = sorted(set(policy) - set(DEFAULT_POLICY))
        if unknown:
            raise ValueError("unknown policy keys: %s" % ", ".join(unknown))
        merged.update(policy)
    _numeric("minimum_capability_ratio", merged["minimum_capability_ratio"], 1.0)
    _numeric("maximum_blank_fraction", merged["maximum_blank_fraction"], 0.0, 1.0)
    _numeric(
        "pathlength_tolerance_fraction",
        merged["pathlength_tolerance_fraction"],
        0.0,
        1.0,
    )
    watch = merged["watch_window_days"]
    if not isinstance(watch, int) or isinstance(watch, bool) or watch < 0:
        raise ValueError("watch_window_days must be a non-negative whole number")
    return merged


def validate_item(item):
    """Validate one equipment record and return a normalized copy."""
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping")
    name = item.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("item needs a non-empty string name")
    name = name.strip()
    kind = item.get("kind")
    if kind not in VALID_ITEM_KINDS:
        raise ValueError(
            "%s kind %r must be one of %s"
            % (name, kind, ", ".join(VALID_ITEM_KINDS))
        )
    absent = [f for f in REQUIRED_FIELDS[kind] if item.get(f) is None]
    if absent:
        raise ValueError(
            "%s is missing required fields: %s" % (name, ", ".join(absent))
        )
    normalized = dict(item)
    normalized["name"] = name
    if kind in (KIND_SPECTROMETER, KIND_CELL):
        normalized["last_calibration"] = parse_date(item["last_calibration"])
        normalized["interval_months"] = _whole_months(
            "%s interval_months" % name, item["interval_months"]
        )
    if kind == KIND_SPECTROMETER:
        _numeric("%s wavenumber_tolerance_per_cm" % name,
                 item["wavenumber_tolerance_per_cm"], 0.0)
        _numeric("%s wavenumber_uncertainty_per_cm" % name,
                 item["wavenumber_uncertainty_per_cm"], 0.0)
    if kind == KIND_CELL:
        _numeric("%s nominal_pathlength_um" % name,
                 item["nominal_pathlength_um"], 0.0)
        _numeric("%s measured_pathlength_um" % name,
                 item["measured_pathlength_um"], 0.0)
    if kind == KIND_SAMPLING:
        certificate = item["precleaning_certificate"]
        if not isinstance(certificate, str) or not certificate.strip():
            raise ValueError("%s precleaning_certificate must be a reference" % name)
        normalized["precleaning_certificate"] = certificate.strip()
        normalized["lot_release_date"] = parse_date(item["lot_release_date"])
        normalized["shelf_life_months"] = _whole_months(
            "%s shelf_life_months" % name, item["shelf_life_months"]
        )
    if kind in (KIND_CELL, KIND_SAMPLING):
        _numeric("%s blank_level_mg_m2" % name, item["blank_level_mg_m2"], 0.0)
        _numeric("%s quantitation_limit_mg_m2" % name,
                 item["quantitation_limit_mg_m2"], 0.0)
    return normalized


def audit_item(item, analysis_date, policy=None):
    """Clear, watch or block one item for use on a given analysis day."""
    norm = validate_item(item)
    rules = resolved_policy(policy)
    on_date = parse_date(analysis_date)
    findings = []
    checks = {}

    if norm["kind"] in (KIND_SPECTROMETER, KIND_CELL):
        due = calibration_due(norm["last_calibration"], norm["interval_months"])
        left = days_remaining(due, on_date)
        checks["calibration_due"] = due.isoformat()
        checks["days_remaining"] = left
        if left < 0:
            findings.append("calibration-expired-before-the-analysis-day")
    else:
        due = add_calendar_months(norm["lot_release_date"],
                                  norm["shelf_life_months"])
        left = days_remaining(due, on_date)
        checks["shelf_life_expiry"] = due.isoformat()
        checks["days_remaining"] = left
        if left < 0:
            findings.append("consumable-lot-past-its-shelf-life")

    if norm["kind"] == KIND_SPECTROMETER:
        ratio = capability_ratio(
            norm["wavenumber_tolerance_per_cm"],
            norm["wavenumber_uncertainty_per_cm"],
        )
        checks["capability_ratio"] = ratio
        if ratio + RATIO_TOLERANCE < rules["minimum_capability_ratio"]:
            findings.append("wavenumber-uncertainty-too-large-for-the-tolerance")

    if norm["kind"] == KIND_CELL:
        drift = deviation_fraction(
            norm["measured_pathlength_um"], norm["nominal_pathlength_um"]
        )
        checks["pathlength_deviation_fraction"] = drift
        if drift > rules["pathlength_tolerance_fraction"] + RATIO_TOLERANCE:
            findings.append("cell-pathlength-outside-its-tolerance")

    if norm["kind"] in (KIND_CELL, KIND_SAMPLING):
        share = blank_fraction(
            norm["blank_level_mg_m2"], norm["quantitation_limit_mg_m2"]
        )
        checks["blank_fraction"] = share
        if share > rules["maximum_blank_fraction"] + RATIO_TOLERANCE:
            findings.append("blank-too-large-beside-the-quantitation-limit")

    if findings:
        verdict = BLOCKED
    elif checks["days_remaining"] <= rules["watch_window_days"]:
        verdict = CLEARED_WITH_WATCH
    else:
        verdict = CLEARED

    return {
        "name": norm["name"],
        "kind": norm["kind"],
        "analysis_date": on_date.isoformat(),
        "checks": checks,
        "findings": findings,
        "verdict": verdict,
    }


def audit_equipment_set(items, analysis_date, policy=None):
    """Audit every item a run depends on and group them by verdict."""
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    rules = resolved_policy(policy)
    audited = []
    seen = set()
    for item in items:
        row = audit_item(item, analysis_date, rules)
        if row["name"] in seen:
            raise ValueError("duplicate equipment name %r" % (row["name"],))
        seen.add(row["name"])
        audited.append(row)
    kinds_present = sorted({row["kind"] for row in audited})
    return {
        "analysis_date": parse_date(analysis_date).isoformat(),
        "items": audited,
        "cleared": [r["name"] for r in audited if r["verdict"] == CLEARED],
        "watch": [r["name"] for r in audited if r["verdict"] == CLEARED_WITH_WATCH],
        "blocked": [r["name"] for r in audited if r["verdict"] == BLOCKED],
        "kinds_present": kinds_present,
        "run_may_proceed": all(r["verdict"] != BLOCKED for r in audited),
    }

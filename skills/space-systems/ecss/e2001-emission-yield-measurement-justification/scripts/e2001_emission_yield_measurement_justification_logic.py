#!/usr/bin/env python3
"""Emission-yield measurement justification (ECSS-E-ST-20-01C clause 9.2).

Deterministic, offline, stdlib-only logic that decides whether a held
secondary-electron-emission-yield measurement may be reused for a
multipaction-critical gap, or whether the material / manufacturing route of
that gap moved far enough to demand a fresh sample measurement.

Paraphrased procedure only; the standard and clause are cited as the anchor.
"""

from datetime import date

import math

# --- Attribute model -------------------------------------------------------
# A provenance attribute is either yield-affecting (it changes the emitting
# surface itself) or administrative (it changes the paperwork around it).
YIELD_AFFECTING_ATTRIBUTES = {
    "base_material": "base-material substitution",
    "surface_finish": "surface-finish change",
    "coating_process": "coating-process change",
    "coating_thickness_um": "coating-thickness change",
    "plating_bath": "plating-bath change",
    "cleaning_route": "cleaning-route change",
    "manufacturing_route": "manufacturing-route change",
    "surface_treatment": "surface-treatment change",
}
ADMINISTRATIVE_ATTRIBUTES = {
    "lot_id": "lot identifier",
    "drawing_revision": "drawing revision",
    "operator_id": "operator identifier",
    "supplier_order": "supplier order reference",
}
REQUIRED_PROVENANCE_KEYS = (
    "base_material",
    "surface_finish",
    "coating_process",
    "cleaning_route",
    "manufacturing_route",
)
NUMERIC_ATTRIBUTES = ("coating_thickness_um",)

# --- Engineering constants -------------------------------------------------
# Susceptibility band on the frequency-gap product (GHz.mm) inside which the
# electron transit time can synchronise with the RF period.
FD_BAND_MIN_GHZ_MM = 0.05
FD_BAND_MAX_GHZ_MM = 200.0
DEFAULT_CRITICAL_MARGIN_DB = 6.0
DEFAULT_RECORD_VALIDITY_DAYS = 730
DEFAULT_REQUIRED_ENERGY_SPAN_EV = (10.0, 1000.0)
COATING_THICKNESS_TOL_UM = 0.05
CONDITIONING_STATES = ("as-received", "baked-out", "electron-conditioned")

REL_TOL = 1e-9
ABS_TOL = 1e-9

DECISION_REUSE = "reuse-justified"
DECISION_REMEASURE = "fresh-sample-measurement-required"
DECISION_NOT_TRIGGERED = "clause-not-triggered-non-critical-gap"


# --- Small numeric helpers -------------------------------------------------
def _close(a, b):
    return math.isclose(a, b, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def meets_or_exceeds(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value > limit or _close(value, limit)


def within_limit(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or _close(value, limit)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _require_positive(value, label):
    value = _require_number(value, label)
    if value <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return value


# --- Provenance ------------------------------------------------------------
def categorize_attribute(attribute):
    """Return 'yield-affecting' or 'administrative' for a provenance key."""
    if attribute in YIELD_AFFECTING_ATTRIBUTES:
        return "yield-affecting"
    if attribute in ADMINISTRATIVE_ATTRIBUTES:
        return "administrative"
    raise ValueError("unknown provenance attribute %r" % (attribute,))


def normalize_provenance(record):
    """Validate one sample-provenance record and return a normalised copy.

    Text attributes are lowercased and stripped so that casing or padding is
    never read as a manufacturing change; numeric attributes become floats.
    """
    if not isinstance(record, dict):
        raise ValueError("provenance record must be a mapping")
    normalised = {}
    for key, value in record.items():
        categorize_attribute(key)  # raises on an unrecognised attribute
        if key in NUMERIC_ATTRIBUTES:
            normalised[key] = _require_positive(value, key)
            continue
        if not isinstance(value, str) or not value.strip():
            raise ValueError("provenance attribute %r must be a non-empty string" % (key,))
        normalised[key] = " ".join(value.strip().lower().split())
    missing = [k for k in REQUIRED_PROVENANCE_KEYS if k not in normalised]
    if missing:
        raise ValueError("provenance record missing required attributes: %s"
                         % ", ".join(sorted(missing)))
    return normalised


def _values_differ(attribute, left, right):
    if left is None or right is None:
        return left is not right
    if attribute in NUMERIC_ATTRIBUTES:
        return abs(left - right) > COATING_THICKNESS_TOL_UM and not _close(
            abs(left - right), COATING_THICKNESS_TOL_UM
        )
    return left != right


def compare_provenance(baseline, candidate):
    """Compare two provenance records; return the categorised differences."""
    base = normalize_provenance(baseline)
    cand = normalize_provenance(candidate)
    differences = []
    for attribute in sorted(set(base) | set(cand)):
        left = base.get(attribute)
        right = cand.get(attribute)
        if not _values_differ(attribute, left, right):
            continue
        category = categorize_attribute(attribute)
        table = (YIELD_AFFECTING_ATTRIBUTES if category == "yield-affecting"
                 else ADMINISTRATIVE_ATTRIBUTES)
        differences.append({
            "attribute": attribute,
            "category": category,
            "reason": table[attribute],
            "baseline": left,
            "candidate": right,
        })
    return differences


def yield_affecting_differences(differences):
    return [d for d in differences if d["category"] == "yield-affecting"]


# --- Gap criticality -------------------------------------------------------
def frequency_gap_product(frequency_ghz, gap_mm):
    """Frequency-gap product in GHz.mm for a parallel-surface gap."""
    f = _require_positive(frequency_ghz, "frequency_ghz")
    d = _require_positive(gap_mm, "gap_mm")
    return f * d


def assess_gap_criticality(gap, critical_margin_db=DEFAULT_CRITICAL_MARGIN_DB):
    """Decide whether a gap is multipaction-critical for clause 9.2."""
    if not isinstance(gap, dict):
        raise ValueError("gap record must be a mapping")
    for key in ("frequency_ghz", "gap_mm", "design_margin_db"):
        if key not in gap:
            raise ValueError("gap record missing required key %r" % (key,))
    threshold = _require_number(critical_margin_db, "critical_margin_db")
    if threshold < 0.0:
        raise ValueError("critical_margin_db must not be negative")
    fd = frequency_gap_product(gap["frequency_ghz"], gap["gap_mm"])
    margin = _require_number(gap["design_margin_db"], "design_margin_db")
    declared = gap.get("declared_critical", False)
    if not isinstance(declared, bool):
        raise ValueError("declared_critical must be a boolean")
    in_band = (meets_or_exceeds(fd, FD_BAND_MIN_GHZ_MM)
               and within_limit(fd, FD_BAND_MAX_GHZ_MM))
    margin_met = meets_or_exceeds(margin, threshold)
    critical = bool(declared or (in_band and not margin_met))
    drivers = []
    if declared:
        drivers.append("gap declared multipaction-critical by the project")
    if in_band and not margin_met:
        drivers.append("frequency-gap product %.4g GHz.mm inside the susceptibility "
                       "band with design-margin %.4g dB below %.4g dB"
                       % (fd, margin, threshold))
    if not critical:
        if not in_band:
            drivers.append("frequency-gap product %.4g GHz.mm outside the "
                           "susceptibility band" % fd)
        if margin_met:
            drivers.append("design-margin %.4g dB meets the %.4g dB threshold"
                           % (margin, threshold))
    return {
        "critical": critical,
        "fd_product_ghz_mm": fd,
        "in_susceptibility_band": in_band,
        "design_margin_db": margin,
        "margin_threshold_db": threshold,
        "margin_meets_threshold": margin_met,
        "drivers": drivers,
    }


# --- Held measurement record ----------------------------------------------
def parse_iso_date(text, label="date"):
    """Parse a YYYY-MM-DD date without touching the network or the clock."""
    if isinstance(text, date):
        return text
    if not isinstance(text, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, text))
    parts = text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("%s must be formatted YYYY-MM-DD, got %r" % (label, text))
    try:
        year, month, day = (int(p) for p in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError("%s is not a valid calendar date (%r): %s"
                         % (label, text, exc))


def measurement_record_age_days(measured_on, assessment_on):
    """Whole days between the measurement date and the assessment date."""
    measured = parse_iso_date(measured_on, "measured_on")
    assessed = parse_iso_date(assessment_on, "assessment_on")
    age = (assessed - measured).days
    if age < 0:
        raise ValueError("measurement date %s is after the assessment date %s"
                         % (measured.isoformat(), assessed.isoformat()))
    return age


def validate_measurement_record(record, assessment_on,
                                validity_days=DEFAULT_RECORD_VALIDITY_DAYS,
                                required_energy_span_ev=DEFAULT_REQUIRED_ENERGY_SPAN_EV):
    """Check that a held yield-measurement record can still carry reuse."""
    if not isinstance(record, dict):
        raise ValueError("measurement record must be a mapping")
    validity = _require_positive(validity_days, "validity_days")
    span = tuple(required_energy_span_ev)
    if len(span) != 2:
        raise ValueError("required_energy_span_ev must hold two values")
    need_low = _require_positive(span[0], "required_energy_span_ev[0]")
    need_high = _require_positive(span[1], "required_energy_span_ev[1]")
    if not need_high > need_low:
        raise ValueError("required_energy_span_ev must be increasing")
    findings = []
    for key in ("facility", "instrument", "sample_id"):
        value = record.get(key)
        if not isinstance(value, str) or not value.strip():
            findings.append("record does not identify the %s" % key.replace("_", " "))
    conditioning = record.get("conditioning")
    if conditioning not in CONDITIONING_STATES:
        findings.append("surface conditioning is not one of %s"
                        % ", ".join(CONDITIONING_STATES))
    if "measured_on" not in record:
        raise ValueError("measurement record missing required key 'measured_on'")
    age = measurement_record_age_days(record["measured_on"], assessment_on)
    if not within_limit(float(age), validity):
        findings.append("record age %d days exceeds the %g day validity window"
                        % (age, validity))
    energy_span = record.get("energy_span_ev")
    if energy_span is None:
        findings.append("record states no primary-electron-energy span")
    else:
        pair = tuple(energy_span)
        if len(pair) != 2:
            raise ValueError("energy_span_ev must hold two values")
        low = _require_positive(pair[0], "energy_span_ev[0]")
        high = _require_positive(pair[1], "energy_span_ev[1]")
        if not high > low:
            raise ValueError("energy_span_ev must be increasing")
        if not within_limit(low, need_low) or not meets_or_exceeds(high, need_high):
            findings.append("measured span %g-%g eV does not cover the required "
                            "%g-%g eV" % (low, high, need_low, need_high))
    return {"valid": not findings, "age_days": age, "findings": findings}


# --- Clause 9.2 decision ---------------------------------------------------
def justify_measurement(baseline_provenance, candidate_provenance, gap,
                        measurement_record, assessment_on,
                        critical_margin_db=DEFAULT_CRITICAL_MARGIN_DB,
                        validity_days=DEFAULT_RECORD_VALIDITY_DAYS,
                        required_energy_span_ev=DEFAULT_REQUIRED_ENERGY_SPAN_EV):
    """Run the clause 9.2 reuse-or-remeasure decision for one gap."""
    differences = compare_provenance(baseline_provenance, candidate_provenance)
    criticality = assess_gap_criticality(gap, critical_margin_db)
    record = validate_measurement_record(measurement_record, assessment_on,
                                         validity_days, required_energy_span_ev)
    yield_changes = yield_affecting_differences(differences)
    drivers = []
    if not criticality["critical"]:
        decision = DECISION_NOT_TRIGGERED
        drivers.append("gap is not multipaction-critical; clause 9.2 remeasurement "
                       "trigger does not fire")
        if yield_changes:
            drivers.append("%d yield-affecting difference(s) recorded for traceability"
                           % len(yield_changes))
    else:
        if yield_changes:
            decision = DECISION_REMEASURE
            for change in yield_changes:
                drivers.append("%s on a multipaction-critical gap" % change["reason"])
        if not record["valid"]:
            decision = DECISION_REMEASURE
            for finding in record["findings"]:
                drivers.append("held record defect: %s" % finding)
        if not yield_changes and record["valid"]:
            decision = DECISION_REUSE
            drivers.append("no yield-affecting difference across %d compared "
                           "attribute(s)" % len(REQUIRED_PROVENANCE_KEYS))
            drivers.append("held record valid, age %d days" % record["age_days"])
    admin = [d for d in differences if d["category"] == "administrative"]
    return {
        "decision": decision,
        "drivers": drivers,
        "differences": differences,
        "yield_affecting_count": len(yield_changes),
        "administrative_count": len(admin),
        "criticality": criticality,
        "record": record,
    }


def format_justification(result):
    """Render a decision dict as reviewable text lines."""
    if not isinstance(result, dict) or "decision" not in result:
        raise ValueError("result must be a justification mapping")
    lines = ["ECSS-E-ST-20-01C clause 9.2 emission-yield measurement justification",
             "decision: %s" % result["decision"],
             "gap multipaction-critical: %s (f.d = %.4g GHz.mm)"
             % (result["criticality"]["critical"],
                result["criticality"]["fd_product_ghz_mm"]),
             "differences: %d yield-affecting, %d administrative"
             % (result["yield_affecting_count"], result["administrative_count"])]
    for driver in result["drivers"]:
        lines.append("  driver: %s" % driver)
    for change in result["differences"]:
        lines.append("  diff[%s/%s]: %s -> %s"
                     % (change["attribute"], change["category"],
                        change["baseline"], change["candidate"]))
    return lines

#!/usr/bin/env python3
"""ECSS-E-ST-20-01C clause 9.5.2 -- measurement-facility calibration audit.

Deterministic, offline, stdlib-only implementation of the clause 9.5.2
duty: the facility used for a secondary-electron-emission yield
measurement is calibrated, that calibration is still in force on the day
of the run and traceable to a recognized reference-standard, and the
calibration results are made available to the customer.

The module categorizes instrumented channels, places each measurement run
inside or outside its channel's validity interval, checks the declared
traceability chain, computes relative instrument-drift from pre-run and
post-run check readings, combines per-channel standard uncertainty
contributions in quadrature, expands them with a declared coverage-factor,
and audits the delivery record.

Paraphrase only -- no ECSS text is reproduced. Clause anchor:
ECSS-E-ST-20-01C 9.5.2.
"""

import datetime
import math

# Channels that carry the emission-yield result and must be calibrated.
REQUIRED_CHANNELS = (
    "beam-current",
    "collector-current",
    "beam-energy",
    "base-pressure",
    "sample-temperature",
)

# Recorded but never counted as required.
SUPPLEMENTARY_CHANNELS = (
    "residual-gas-composition",
    "stage-position",
    "chamber-wall-temperature",
)

# Declared chains that resolve to a recognized reference-standard.
ACCEPTED_TRACEABILITY = (
    "national-metrology-institute",
    "accredited-calibration-laboratory",
    "certified-transfer-standard",
)

REQUIRED = "required"
SUPPLEMENTARY = "supplementary"
UNCATEGORIZED = "uncategorized"

IN_VALIDITY = "in-validity"
OUT_OF_VALIDITY = "out-of-validity"

# Absorbs the representation residue of a percentage ratio or a quadrature
# sum sitting exactly on a stated limit. Not an engineering allowance.
COMPARISON_REL_TOL = 1e-9


def normalize_channel_name(raw):
    """Fold a declared channel name onto the canonical hyphenated form."""
    if not isinstance(raw, str):
        raise ValueError("channel name must be a string, got %r" % (raw,))
    name = raw.strip().lower().replace("_", "-")
    name = "-".join(part for part in name.split() if part)
    while "--" in name:
        name = name.replace("--", "-")
    name = name.strip("-")
    if not name:
        raise ValueError("channel name is empty after normalization")
    return name


def categorize_channel(raw):
    """Return (category, canonical_name) for one declared channel."""
    name = normalize_channel_name(raw)
    if name in REQUIRED_CHANNELS:
        return (REQUIRED, name)
    if name in SUPPLEMENTARY_CHANNELS:
        return (SUPPLEMENTARY, name)
    return (UNCATEGORIZED, name)


def parse_iso_date(value):
    """Parse an ISO calendar date; accept a date object unchanged."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.datetime):
        return value.date()
    if not isinstance(value, str) or not value.strip():
        raise ValueError("date must be an ISO string or a date, got %r" % (value,))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError("unparseable ISO date %r: %s" % (value, exc))


def calibration_age_days(calibration_date, measurement_date):
    """Whole days from calibration to measurement; negative is an error."""
    cal = parse_iso_date(calibration_date)
    run = parse_iso_date(measurement_date)
    age = (run - cal).days
    if age < 0:
        raise ValueError(
            "calibration dated %s postdates the measurement on %s" % (cal, run)
        )
    return age


def validity_status(calibration_date, interval_days, measurement_date):
    """Place a run inside or outside the validity interval (inclusive)."""
    if not isinstance(interval_days, int) or isinstance(interval_days, bool):
        raise ValueError("interval_days must be an integer, got %r" % (interval_days,))
    if interval_days <= 0:
        raise ValueError("interval_days must be positive, got %r" % (interval_days,))
    age = calibration_age_days(calibration_date, measurement_date)
    return IN_VALIDITY if age <= interval_days else OUT_OF_VALIDITY


def is_traceable(chain):
    """True when the declared chain resolves to a recognized standard."""
    if chain is None:
        return False
    if not isinstance(chain, str):
        raise ValueError("traceability chain must be a string, got %r" % (chain,))
    return normalize_channel_name(chain) in ACCEPTED_TRACEABILITY


def relative_drift_percent(pre_reading, post_reading):
    """Relative instrument-drift in percent of the pre-run reading."""
    for label, value in (("pre_reading", pre_reading), ("post_reading", post_reading)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be numeric, got %r" % (label, value))
    if pre_reading == 0:
        raise ValueError("pre-run reading is zero; relative drift is undefined")
    return abs(post_reading - pre_reading) / abs(float(pre_reading)) * 100.0


def drift_within_tolerance(drift_percent, tolerance_percent):
    """Compare drift against tolerance, absorbing representation residue."""
    if not isinstance(drift_percent, (int, float)) or isinstance(drift_percent, bool):
        raise ValueError("drift_percent must be numeric, got %r" % (drift_percent,))
    if drift_percent < 0:
        raise ValueError("drift_percent must not be negative, got %r" % (drift_percent,))
    if (
        not isinstance(tolerance_percent, (int, float))
        or isinstance(tolerance_percent, bool)
        or tolerance_percent <= 0
    ):
        raise ValueError(
            "tolerance_percent must be a positive number, got %r" % (tolerance_percent,)
        )
    if drift_percent <= tolerance_percent:
        return True
    return math.isclose(
        drift_percent, tolerance_percent, rel_tol=COMPARISON_REL_TOL, abs_tol=0.0
    )


def combine_uncertainties(components):
    """Combine independent standard contributions in quadrature."""
    if not isinstance(components, (list, tuple)):
        raise ValueError("components must be a list, got %r" % (components,))
    if len(components) == 0:
        raise ValueError("uncertainty component list is empty")
    total = 0.0
    for index, value in enumerate(components):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("component[%d] must be numeric, got %r" % (index, value))
        if value < 0:
            raise ValueError("component[%d] is negative: %r" % (index, value))
        total += float(value) * float(value)
    return math.sqrt(total)


def expanded_uncertainty(combined_standard, coverage_factor):
    """Expand a combined-standard-uncertainty by a declared coverage-factor."""
    if not isinstance(combined_standard, (int, float)) or isinstance(
        combined_standard, bool
    ):
        raise ValueError(
            "combined_standard must be numeric, got %r" % (combined_standard,)
        )
    if combined_standard < 0:
        raise ValueError("combined_standard must not be negative")
    if not isinstance(coverage_factor, (int, float)) or isinstance(
        coverage_factor, bool
    ):
        raise ValueError("coverage_factor must be numeric, got %r" % (coverage_factor,))
    if coverage_factor <= 0:
        raise ValueError("coverage_factor must be positive, got %r" % (coverage_factor,))
    return float(combined_standard) * float(coverage_factor)


def uncertainty_within_budget(combined_standard, budget):
    """Compare a quadrature sum against its budget, absorbing ULP residue."""
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) or budget <= 0:
        raise ValueError("budget must be a positive number, got %r" % (budget,))
    if combined_standard <= budget:
        return True
    return math.isclose(
        combined_standard, budget, rel_tol=COMPARISON_REL_TOL, abs_tol=0.0
    )


def audit_channel(entry, measurement_date):
    """Audit one declared channel; return its status record and findings."""
    if not isinstance(entry, dict):
        raise ValueError("channel entry must be a mapping, got %r" % (entry,))
    category, name = categorize_channel(entry.get("channel"))
    findings = []
    status = validity_status(
        entry.get("calibration_date"),
        entry.get("interval_days"),
        measurement_date,
    )
    if status == OUT_OF_VALIDITY:
        findings.append("channel %s was outside its validity interval at the run" % name)
    if not is_traceable(entry.get("traceable_to")):
        findings.append("channel %s declares no recognized traceability chain" % name)
    pre = entry.get("pre_run_reading")
    post = entry.get("post_run_reading")
    drift = None
    if pre is not None and post is not None:
        drift = relative_drift_percent(pre, post)
        tolerance = entry.get("drift_tolerance_percent")
        if not drift_within_tolerance(drift, tolerance):
            findings.append(
                "channel %s drifted %.4f%% against a %.4f%% tolerance"
                % (name, drift, tolerance)
            )
    return {
        "channel": name,
        "category": category,
        "validity": status,
        "drift_percent": drift,
        "findings": findings,
    }


def check_customer_delivery(delivery, calibration_dates, covered_required):
    """Audit the record that puts the calibration in the customer's hands."""
    if not isinstance(delivery, dict):
        raise ValueError("delivery record must be a mapping, got %r" % (delivery,))
    recipient = delivery.get("recipient")
    if not isinstance(recipient, str) or not recipient.strip():
        raise ValueError("delivery record names no customer recipient")
    issue_date = parse_iso_date(delivery.get("issue_date"))
    findings = []
    if calibration_dates:
        latest = max(parse_iso_date(d) for d in calibration_dates)
        if issue_date < latest:
            findings.append(
                "calibration record issued %s predates the latest calibration %s"
                % (issue_date, latest)
            )
    declared = delivery.get("channels_covered")
    if not isinstance(declared, (list, tuple)) or not declared:
        raise ValueError("delivery record covers no channels")
    covered = {normalize_channel_name(c) for c in declared}
    for name in sorted(covered_required):
        if name not in covered:
            findings.append("delivered record omits required channel %s" % name)
    return findings


def audit_facility_calibration(channels, measurement_date, delivery, budget=None):
    """Run the full clause 9.5.2 audit and return the disposition."""
    if not isinstance(channels, (list, tuple)) or not channels:
        raise ValueError("channel list is empty")
    records = [audit_channel(entry, measurement_date) for entry in channels]
    findings = []
    for record in records:
        findings.extend(record["findings"])
    present_required = {r["channel"] for r in records if r["category"] == REQUIRED}
    missing = sorted(set(REQUIRED_CHANNELS) - present_required)
    for name in missing:
        findings.append("required channel %s has no calibration entry" % name)
    uncategorized = sorted(
        {r["channel"] for r in records if r["category"] == UNCATEGORIZED}
    )
    contributions = [
        entry.get("standard_uncertainty", 0.0)
        for entry in channels
        if isinstance(entry, dict)
    ]
    combined = combine_uncertainties(contributions)
    if budget is not None and not uncertainty_within_budget(combined, budget):
        findings.append(
            "combined-standard-uncertainty %.6f exceeds the budget %.6f"
            % (combined, budget)
        )
    cal_dates = [
        entry.get("calibration_date") for entry in channels if isinstance(entry, dict)
    ]
    findings.extend(check_customer_delivery(delivery, cal_dates, present_required))
    return {
        "channel_records": records,
        "missing_required": missing,
        "uncategorized_channels": uncategorized,
        "combined_standard_uncertainty": combined,
        "findings": findings,
        "compliant": not findings,
    }

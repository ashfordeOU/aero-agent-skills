#!/usr/bin/env python3
"""Two-step multipactor test-bed validation (ECSS-E-ST-20-01C 8.3).

Deterministic, offline, python3 standard library only. The clause intent is
paraphrased into implementable logic; no standard text is reproduced.

Step one (negative control) proves the bed itself does not discharge over the
applied-power sweep and carries a headroom above the maximum applied power.
Step two (positive control) proves the bed detects a certified reference onset
inside a tolerance band, on every required detection channel.
"""

from __future__ import annotations

import datetime
import math

#: Relative tolerance absorbing binary-floating-point representation error on
#: an exact-limit comparison. It never widens an engineering limit.
REL_TOL = 1e-9

#: Absolute tolerance in decibel for an on-the-edge logarithmic comparison.
DB_ABS_TOL = 1e-9

STEP_ONE = "bed-free-reference-through-line"
STEP_TWO = "reference-sample-onset"
REQUIRED_STEP_ORDER = (STEP_ONE, STEP_TWO)


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def _positive_power(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out) or out <= 0.0:
        raise ValueError(
            "%s must be finite and strictly positive, got %r" % (label, value)
        )
    return out


def _parse_date(value, label):
    if not isinstance(value, str):
        raise ValueError("%s must be an ISO date string, got %r" % (label, value))
    try:
        return datetime.date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("%s is not an ISO date (YYYY-MM-DD): %r" % (label, value))


def power_ratio_db(power_w, reference_w):
    """Return the ratio of two powers expressed in decibel.

    Both arguments are powers in watt and must be strictly positive: a ratio
    against zero or a negative power has no logarithmic meaning.
    """
    numerator = _positive_power(power_w, "power_w")
    denominator = _positive_power(reference_w, "reference_w")
    return 10.0 * math.log10(numerator / denominator)


# ----------------------------------------------------------------------------
# Step order
# ----------------------------------------------------------------------------

def check_step_order(steps):
    """Check the record carries the negative step then the positive step."""
    if not isinstance(steps, (list, tuple)):
        raise ValueError("steps must be a list or tuple")
    names = []
    for entry in steps:
        if not isinstance(entry, str) or not entry.strip():
            raise ValueError("each step must be a non-blank string, got %r" % (entry,))
        key = entry.strip().lower()
        if key not in REQUIRED_STEP_ORDER:
            raise ValueError("unrecognized validation step: %r" % (entry,))
        names.append(key)
    if len(names) != len(set(names)):
        raise ValueError("validation steps must not repeat: %r" % (names,))
    if tuple(names) != REQUIRED_STEP_ORDER:
        raise ValueError(
            "validation steps must run %s then %s, got %r"
            % (STEP_ONE, STEP_TWO, names)
        )
    return list(names)


# ----------------------------------------------------------------------------
# Step one: the bed is quiet, and it has headroom
# ----------------------------------------------------------------------------

def scan_sweep_for_events(sweep_points, max_applied_power_w):
    """Return the sweep points at or below the maximum applied power that fired."""
    if not isinstance(sweep_points, (list, tuple)):
        raise ValueError("sweep_points must be a list or tuple")
    if not sweep_points:
        raise ValueError("sweep_points must not be empty: step one needs a sweep")
    ceiling = _positive_power(max_applied_power_w, "max_applied_power_w")

    fired = []
    highest = 0.0
    for point in sweep_points:
        if not isinstance(point, dict):
            raise ValueError("each sweep point must be a mapping, got %r" % (point,))
        level = _positive_power(point.get("power_w"), "sweep point power_w")
        channel = point.get("channel")
        if not isinstance(channel, str) or not channel.strip():
            raise ValueError("sweep point missing a non-blank 'channel'")
        detected = point.get("event_detected")
        if not isinstance(detected, bool):
            raise ValueError(
                "sweep point 'event_detected' must be a boolean, got %r" % (detected,)
            )
        highest = max(highest, level)
        at_or_below = level <= ceiling or math.isclose(level, ceiling, rel_tol=REL_TOL)
        if at_or_below and detected:
            fired.append({"channel": channel.strip(), "power_w": level})
    covered = highest >= ceiling or math.isclose(highest, ceiling, rel_tol=REL_TOL)
    return {
        "fired": fired,
        "highest_swept_power_w": highest,
        "reached_max_applied_power": covered,
    }


def check_bed_headroom(bed_onset_power_w, max_applied_power_w, required_headroom_db):
    """Check the bed onset power sits the required headroom above the maximum."""
    onset = _positive_power(bed_onset_power_w, "bed_onset_power_w")
    ceiling = _positive_power(max_applied_power_w, "max_applied_power_w")
    if not isinstance(required_headroom_db, (int, float)) or isinstance(
        required_headroom_db, bool
    ):
        raise ValueError(
            "required_headroom_db must be a number, got %r" % (required_headroom_db,)
        )
    required = float(required_headroom_db)
    if not math.isfinite(required) or required < 0.0:
        raise ValueError(
            "required_headroom_db must be finite and non-negative, got %r"
            % (required_headroom_db,)
        )
    actual = power_ratio_db(onset, ceiling)
    sufficient = actual >= required or math.isclose(
        actual, required, rel_tol=REL_TOL, abs_tol=DB_ABS_TOL
    )
    findings = []
    if not sufficient:
        findings.append(
            "bed onset headroom %.4f dB below the required %.4f dB" % (actual, required)
        )
    return {
        "headroom_db": actual,
        "required_headroom_db": required,
        "compliant": sufficient,
        "findings": findings,
    }


def validate_step_one(
    sweep_points, max_applied_power_w, bed_onset_power_w, required_headroom_db
):
    """Run the negative control: bed quiet across the sweep, with headroom."""
    scan = scan_sweep_for_events(sweep_points, max_applied_power_w)
    findings = []
    for hit in scan["fired"]:
        findings.append(
            "detection channel %s registered an event at %.4f W, at or below the "
            "maximum applied power" % (hit["channel"], hit["power_w"])
        )
    if not scan["reached_max_applied_power"]:
        findings.append(
            "sweep never reached the maximum applied power; silence proves nothing"
        )
    if bed_onset_power_w is None:
        findings.append("bed onset power not established; headroom cannot be shown")
        headroom = None
    else:
        headroom = check_bed_headroom(
            bed_onset_power_w, max_applied_power_w, required_headroom_db
        )
        findings.extend(headroom["findings"])
    return {
        "step": STEP_ONE,
        "fired": scan["fired"],
        "headroom": headroom,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Step two: the bed sees a certified reference onset
# ----------------------------------------------------------------------------

def reference_deviation_db(measured_onset_w, certified_onset_w):
    """Return the signed deviation of a measured onset from the certified one."""
    return power_ratio_db(measured_onset_w, certified_onset_w)


def check_channel_agreement(registered_channels, required_channels):
    """Check every required detection channel registered the reference event."""
    for name, value in (
        ("registered_channels", registered_channels),
        ("required_channels", required_channels),
    ):
        if not isinstance(value, (list, tuple, set, frozenset)):
            raise ValueError("%s must be a sequence or set" % name)
    required = [str(c).strip() for c in required_channels]
    if not required:
        raise ValueError("required_channels must not be empty")
    registered = {str(c).strip() for c in registered_channels}
    silent = [c for c in required if c not in registered]
    findings = [
        "detection channel %s stayed silent on the certified reference event" % c
        for c in silent
    ]
    return {
        "silent_channels": silent,
        "compliant": not findings,
        "findings": findings,
    }


def validate_step_two(
    measured_onset_w,
    certified_onset_w,
    tolerance_db,
    registered_channels,
    required_channels,
):
    """Run the positive control: onset inside the band, every channel firing."""
    if not isinstance(tolerance_db, (int, float)) or isinstance(tolerance_db, bool):
        raise ValueError("tolerance_db must be a number, got %r" % (tolerance_db,))
    tolerance = float(tolerance_db)
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError(
            "tolerance_db must be finite and strictly positive, got %r" % (tolerance_db,)
        )
    deviation = reference_deviation_db(measured_onset_w, certified_onset_w)
    magnitude = abs(deviation)
    inside = magnitude <= tolerance or math.isclose(
        magnitude, tolerance, rel_tol=REL_TOL, abs_tol=DB_ABS_TOL
    )
    findings = []
    if not inside:
        direction = "late" if deviation > 0.0 else "early"
        findings.append(
            "measured onset deviates %+.4f dB from the certified reference "
            "(%s detection), outside the %.4f dB band"
            % (deviation, direction, tolerance)
        )
    channels = check_channel_agreement(registered_channels, required_channels)
    findings.extend(channels["findings"])
    return {
        "step": STEP_TWO,
        "deviation_db": deviation,
        "tolerance_db": tolerance,
        "inside_band": inside,
        "channels": channels,
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Currency of the validation
# ----------------------------------------------------------------------------

def check_validation_currency(
    validation_date, run_date, validity_days, reconfiguration_dates=()
):
    """Check the validation is inside its window and not superseded by a change."""
    validated = _parse_date(validation_date, "validation_date")
    run = _parse_date(run_date, "run_date")
    if not isinstance(validity_days, int) or isinstance(validity_days, bool):
        raise ValueError("validity_days must be an int, got %r" % (validity_days,))
    if validity_days <= 0:
        raise ValueError("validity_days must be strictly positive, got %r" % (validity_days,))
    if not isinstance(reconfiguration_dates, (list, tuple)):
        raise ValueError("reconfiguration_dates must be a list or tuple")

    age = (run - validated).days
    findings = []
    if age < 0:
        raise ValueError("run date precedes the validation date; record is inconsistent")
    if age > validity_days:
        findings.append(
            "validation is %d day(s) old, beyond the %d day validity window"
            % (age, validity_days)
        )
    superseding = []
    for entry in reconfiguration_dates:
        changed = _parse_date(entry, "reconfiguration date")
        if changed > validated:
            superseding.append(changed.isoformat())
    if superseding:
        findings.append(
            "bed reconfiguration on %s supersedes the validation"
            % ", ".join(sorted(superseding))
        )
    return {
        "age_days": age,
        "validity_days": validity_days,
        "superseding_changes": sorted(superseding),
        "compliant": not findings,
        "findings": findings,
    }


# ----------------------------------------------------------------------------
# Aggregate
# ----------------------------------------------------------------------------

_REQUIRED_KEYS = (
    "steps",
    "sweep_points",
    "max_applied_power_w",
    "bed_onset_power_w",
    "required_headroom_db",
    "measured_onset_w",
    "certified_onset_w",
    "tolerance_db",
    "registered_channels",
    "required_channels",
    "validation_date",
    "run_date",
    "validity_days",
)


def evaluate_bed_validation(record):
    """Run the clause 8.3 two-step validation over one record."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    missing = [key for key in _REQUIRED_KEYS if key not in record]
    if missing:
        raise ValueError("validation record missing keys: %s" % ", ".join(sorted(missing)))

    order = check_step_order(record["steps"])
    step_one = validate_step_one(
        record["sweep_points"],
        record["max_applied_power_w"],
        record["bed_onset_power_w"],
        record["required_headroom_db"],
    )
    step_two = validate_step_two(
        record["measured_onset_w"],
        record["certified_onset_w"],
        record["tolerance_db"],
        record["registered_channels"],
        record["required_channels"],
    )
    currency = check_validation_currency(
        record["validation_date"],
        record["run_date"],
        record["validity_days"],
        record.get("reconfiguration_dates", ()),
    )

    findings = []
    for label, block in (
        ("step-one", step_one),
        ("step-two", step_two),
        ("currency", currency),
    ):
        for item in block["findings"]:
            findings.append("%s: %s" % (label, item))

    return {
        "step_order": order,
        "step_one": step_one,
        "step_two": step_two,
        "currency": currency,
        "compliant": not findings,
        "findings": findings,
        "verdict": "BED-VALIDATED" if not findings else "BED-NOT-VALIDATED",
    }

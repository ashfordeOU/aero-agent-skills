#!/usr/bin/env python3
"""Detection-capability demonstration logic (ECSS-E-ST-20-01C 7.3.1).

Deterministic, offline, stdlib-only helpers that grade the evidence a
testing-entity produces to show that the chosen multipactor-detection
channels really register a discharge:

- normalize each demonstration record (response, measured noise-floor,
  timestamp),
- compute the per-channel signal-to-noise-ratio and hold it against
  the required-registration-ratio at the exact boundary,
- reject evidence recorded after the first campaign-run, and evidence
  older than the demonstration validity-window,
- reconcile the records against the declared channel set,
- derive the minimum-detectable-amplitude the passing channels support.

Anchor: ECSS-E-ST-20-01C clause 7.3.1 (paraphrased procedure only).
"""

import datetime
import math

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"

DEFAULT_REQUIRED_RATIO_DB = 6.0
DEFAULT_VALIDITY_WINDOW_DAYS = 30.0

# A dB signal-to-noise figure is a difference of two floats; an
# exactly-compliant demonstration can evaluate a few ULPs low. The
# tolerance absorbs that representation error only - the required
# registration ratio is never relaxed.
REL_TOL = 1e-9
ABS_TOL = 1e-12

SECONDS_PER_DAY = 86400.0


def _at_least(value, limit):
    """True when value >= limit, absorbing float representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _at_most(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def _as_float(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (field, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (field, value))
    return number


def parse_timestamp(value):
    """Parse an ISO-like 'YYYY-MM-DDTHH:MM:SS' stamp into a datetime.

    Raises ValueError on any other shape - an unparsable stamp cannot
    be ordered against the campaign-run and is not evidence.
    """
    if isinstance(value, datetime.datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("timestamp must be a non-empty string, got %r" % (value,))
    try:
        return datetime.datetime.strptime(value.strip(), TIMESTAMP_FORMAT)
    except ValueError:
        raise ValueError(
            "timestamp %r is not in %s form" % (value, TIMESTAMP_FORMAT)
        )


def signal_to_noise_db(response_dbm, noise_floor_dbm):
    """Signal-to-noise-ratio in dB of a recorded response over its floor."""
    response = _as_float(response_dbm, "response_dbm")
    floor = _as_float(noise_floor_dbm, "noise_floor_dbm")
    return response - floor


def validate_demonstration_record(record):
    """Normalize one capability-demonstration record.

    record keys: channel_id, response_dbm, noise_floor_dbm, timestamp.
    Raises ValueError on any malformed field.
    """
    if not isinstance(record, dict):
        raise ValueError("demonstration record must be a mapping, got %r" % (record,))
    channel_id = record.get("channel_id")
    if not isinstance(channel_id, str) or not channel_id.strip():
        raise ValueError("channel_id must be a non-empty string, got %r" % (channel_id,))
    response = _as_float(record.get("response_dbm"), "response_dbm")
    floor = _as_float(record.get("noise_floor_dbm"), "noise_floor_dbm")
    if response < floor:
        raise ValueError(
            "channel %s records a response below its own measured noise-floor"
            % channel_id.strip()
        )
    stamp = parse_timestamp(record.get("timestamp"))
    reference = record.get("reference_event_dbm")
    if reference is not None:
        reference = _as_float(reference, "reference_event_dbm")
    return {
        "channel_id": channel_id.strip(),
        "response_dbm": response,
        "noise_floor_dbm": floor,
        "timestamp": stamp,
        "reference_event_dbm": reference,
    }


def normalize_record_set(records):
    """Validate a whole record set, rejecting duplicate channel records."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("demonstration record set must be a non-empty list")
    normalized = []
    seen = set()
    for record in records:
        item = validate_demonstration_record(record)
        if item["channel_id"] in seen:
            raise ValueError(
                "duplicate demonstration record for channel %r" % (item["channel_id"],)
            )
        seen.add(item["channel_id"])
        normalized.append(item)
    return normalized


def record_age_days(record, campaign_start):
    """Age of a demonstration record in days at the first campaign-run.

    Negative when the record was taken after the campaign started.
    """
    start = parse_timestamp(campaign_start)
    delta = start - record["timestamp"]
    return delta.total_seconds() / SECONDS_PER_DAY


def evaluate_record(
    record,
    campaign_start,
    required_ratio_db=DEFAULT_REQUIRED_RATIO_DB,
    validity_window_days=DEFAULT_VALIDITY_WINDOW_DAYS,
):
    """Grade one demonstration record: ratio, direction in time, age."""
    required = _as_float(required_ratio_db, "required_ratio_db")
    if required <= 0.0:
        raise ValueError("required_ratio_db must be > 0, got %r" % (required_ratio_db,))
    window = _as_float(validity_window_days, "validity_window_days")
    if window <= 0.0:
        raise ValueError(
            "validity_window_days must be > 0, got %r" % (validity_window_days,)
        )
    ratio = signal_to_noise_db(record["response_dbm"], record["noise_floor_dbm"])
    ratio_ok = _at_least(ratio, required)
    age = record_age_days(record, campaign_start)
    in_order = age >= 0.0 or math.isclose(age, 0.0, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    fresh = in_order and _at_most(age, window)
    reasons = []
    if not ratio_ok:
        reasons.append(
            "signal-to-noise-ratio %.4f dB short of required %.4f dB by %.4f dB"
            % (ratio, required, required - ratio)
        )
    if not in_order:
        reasons.append(
            "demonstration recorded %.4f days after the first campaign-run" % (-age,)
        )
    elif not fresh:
        reasons.append(
            "demonstration is %.4f days old, outside the %.4f day validity-window"
            % (age, window)
        )
    return {
        "channel_id": record["channel_id"],
        "snr_db": ratio,
        "ratio_ok": ratio_ok,
        "age_days": age,
        "in_order": in_order,
        "fresh": fresh,
        "demonstrated": ratio_ok and in_order and fresh,
        "reasons": reasons,
    }


def minimum_detectable_amplitude_dbm(passing_records, required_ratio_db):
    """Amplitude the demonstrated arrangement can claim to register.

    The worst (highest) measured noise-floor among the passing channels
    plus the required-registration-ratio. Raises ValueError when no
    channel passed - the arrangement then has no demonstrated
    capability to quote.
    """
    required = _as_float(required_ratio_db, "required_ratio_db")
    floors = [r["noise_floor_dbm"] for r in passing_records]
    if not floors:
        raise ValueError(
            "no passing channel: minimum-detectable-amplitude is undefined"
        )
    return max(floors) + required


def assess_detection_capability(
    declared_channels,
    records,
    campaign_start,
    required_ratio_db=DEFAULT_REQUIRED_RATIO_DB,
    validity_window_days=DEFAULT_VALIDITY_WINDOW_DAYS,
):
    """Grade a whole clause 7.3.1 capability demonstration.

    Returns a report dict with per-record evaluations, the reconciliation
    against the declared channel set, the arrangement's
    minimum-detectable-amplitude and the findings. verified is True only
    when findings is empty.
    """
    if not isinstance(declared_channels, (list, tuple)) or not declared_channels:
        raise ValueError("declared channel set must be a non-empty list")
    declared = []
    for name in declared_channels:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("declared channel names must be non-empty strings")
        declared.append(name.strip())
    if len(set(declared)) != len(declared):
        raise ValueError("declared channel set contains a duplicate name")
    normalized = normalize_record_set(records)
    evaluations = [
        evaluate_record(item, campaign_start, required_ratio_db, validity_window_days)
        for item in normalized
    ]
    evaluations.sort(key=lambda r: r["channel_id"])
    by_id = {item["channel_id"]: item for item in normalized}
    findings = []
    missing = sorted(set(declared) - set(by_id))
    for name in missing:
        findings.append("declared channel %s has no demonstration record" % name)
    orphans = sorted(set(by_id) - set(declared))
    for name in orphans:
        findings.append("record for %s is not a declared channel" % name)
    for evaluation in evaluations:
        if evaluation["channel_id"] in orphans:
            continue
        if not evaluation["demonstrated"]:
            findings.append(
                "channel %s not demonstrated: %s"
                % (evaluation["channel_id"], "; ".join(evaluation["reasons"]))
            )
    passing = [
        by_id[e["channel_id"]]
        for e in evaluations
        if e["demonstrated"] and e["channel_id"] in set(declared)
    ]
    try:
        floor = minimum_detectable_amplitude_dbm(passing, required_ratio_db)
    except ValueError:
        floor = None
        findings.append("no declared channel passed: capability is undefined")
    return {
        "declared": sorted(declared),
        "evaluations": evaluations,
        "missing_records": missing,
        "orphan_records": orphans,
        "passing_channels": sorted(r["channel_id"] for r in passing),
        "minimum_detectable_amplitude_dbm": floor,
        "required_ratio_db": _as_float(required_ratio_db, "required_ratio_db"),
        "findings": findings,
        "verified": not findings,
    }


def format_capability_report(report):
    """Render a capability assessment as deterministic plain-text lines."""
    floor = report["minimum_detectable_amplitude_dbm"]
    lines = [
        "detection-capability demonstration: %s"
        % ("VERIFIED" if report["verified"] else "NOT VERIFIED"),
        "declared=%d passing=%d minimum-detectable-amplitude=%s"
        % (
            len(report["declared"]),
            len(report["passing_channels"]),
            "undefined" if floor is None else "%.3f dBm" % floor,
        ),
    ]
    for item in report["evaluations"]:
        lines.append(
            "  %s snr=%.3f dB age=%.3f d demonstrated=%s"
            % (
                item["channel_id"],
                item["snr_db"],
                item["age_days"],
                "yes" if item["demonstrated"] else "no",
            )
        )
    for finding in report["findings"]:
        lines.append("  FINDING: %s" % finding)
    return "\n".join(lines)

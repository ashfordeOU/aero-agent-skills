#!/usr/bin/env python3
"""Multipactor detection-method arrangement logic (ECSS-E-ST-20-01C 7.1).

Deterministic, offline, stdlib-only helpers that grade the *set* of
detection channels a multipactor test-campaign declares against the
minimum expectations of clause 7.1:

- every channel is normalized (coverage-scope, observable-family,
  detection-threshold, response-time, calibration state),
- the arrangement carries enough channels,
- it mixes global-coverage and local-coverage,
- it rests on at least two independent observable-families,
- each channel keeps a sensitivity-margin over the expected
  event-signature and responds faster than the shortest credible
  discharge-duration.

Anchor: ECSS-E-ST-20-01C clause 7.1 (paraphrased procedure only).
"""

import math

# --- arrangement constants -------------------------------------------------

MIN_CHANNEL_COUNT = 2
MIN_INDEPENDENT_FAMILIES = 2
DEFAULT_REQUIRED_MARGIN_DB = 3.0

# dB differences and ms comparisons are sums/differences of floats; an
# exactly-compliant boundary case can land a few ULPs on the wrong side.
# The tolerance absorbs the representation error only - it never widens
# the engineering limit.
REL_TOL = 1e-9
ABS_TOL = 1e-9

COVERAGE_SCOPES = {
    "global": "global-coverage",
    "global-coverage": "global-coverage",
    "rf-chain": "global-coverage",
    "chain-wide": "global-coverage",
    "local": "local-coverage",
    "local-coverage": "local-coverage",
    "gap-local": "local-coverage",
    "region": "local-coverage",
}

OBSERVABLE_FAMILIES = {
    "rf-power-balance": "rf-power-balance",
    "power-balance": "rf-power-balance",
    "forward-reflected": "rf-power-balance",
    "spectral-sideband": "spectral-sideband",
    "sideband": "spectral-sideband",
    "close-to-carrier-noise": "spectral-sideband",
    "charged-particle": "charged-particle",
    "electron-probe": "charged-particle",
    "optical-emission": "optical-emission",
    "light-emission": "optical-emission",
    "gas-pressure": "gas-pressure",
    "pressure-rise": "gas-pressure",
    "thermal-rise": "thermal-rise",
    "calorimetric": "thermal-rise",
}

# Families whose sensor sits on one region of the item; a channel that
# declares one of these with global-coverage is physically inconsistent.
INHERENTLY_LOCAL_FAMILIES = frozenset(
    ("charged-particle", "optical-emission", "thermal-rise")
)


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


def normalize_coverage_scope(scope):
    """Map a declared coverage-scope onto its canonical token.

    Raises ValueError for an unrecognized scope: clause 7.1 grading
    depends on the global/local mix, so an unknown scope is never
    silently defaulted.
    """
    if not isinstance(scope, str) or not scope.strip():
        raise ValueError("coverage-scope must be a non-empty string, got %r" % (scope,))
    key = scope.strip().lower()
    if key not in COVERAGE_SCOPES:
        raise ValueError("unrecognized coverage-scope %r" % (scope,))
    return COVERAGE_SCOPES[key]


def normalize_observable_family(family):
    """Map a declared observable-family onto its canonical token.

    Raises ValueError for an unrecognized family: independence is
    counted over families, so an unknown one cannot be admitted.
    """
    if not isinstance(family, str) or not family.strip():
        raise ValueError(
            "observable-family must be a non-empty string, got %r" % (family,)
        )
    key = family.strip().lower()
    if key not in OBSERVABLE_FAMILIES:
        raise ValueError("unrecognized observable-family %r" % (family,))
    return OBSERVABLE_FAMILIES[key]


def validate_detection_channel(entry):
    """Normalize one declared detection channel.

    entry keys: channel_id, coverage_scope, observable_family,
    threshold_dbm, response_time_ms, calibrated (optional, default
    False). Raises ValueError on any malformed field.
    """
    if not isinstance(entry, dict):
        raise ValueError("detection channel must be a mapping, got %r" % (entry,))
    channel_id = entry.get("channel_id")
    if not isinstance(channel_id, str) or not channel_id.strip():
        raise ValueError("channel_id must be a non-empty string, got %r" % (channel_id,))
    scope = normalize_coverage_scope(entry.get("coverage_scope"))
    family = normalize_observable_family(entry.get("observable_family"))
    if scope == "global-coverage" and family in INHERENTLY_LOCAL_FAMILIES:
        raise ValueError(
            "channel %s declares global-coverage with region-bound family %s"
            % (channel_id.strip(), family)
        )
    threshold = _as_float(entry.get("threshold_dbm"), "threshold_dbm")
    response = _as_float(entry.get("response_time_ms"), "response_time_ms")
    if response <= 0.0:
        raise ValueError(
            "response_time_ms must be > 0 for channel %s, got %r"
            % (channel_id.strip(), response)
        )
    calibrated = entry.get("calibrated", False)
    if not isinstance(calibrated, bool):
        raise ValueError(
            "calibrated must be a boolean for channel %s, got %r"
            % (channel_id.strip(), calibrated)
        )
    return {
        "channel_id": channel_id.strip(),
        "coverage_scope": scope,
        "observable_family": family,
        "threshold_dbm": threshold,
        "response_time_ms": response,
        "calibrated": calibrated,
    }


def normalize_channel_set(entries):
    """Validate a whole declared channel set, rejecting duplicate ids."""
    if not isinstance(entries, (list, tuple)) or not entries:
        raise ValueError("channel set must be a non-empty list of mappings")
    normalized = []
    seen = set()
    for entry in entries:
        channel = validate_detection_channel(entry)
        if channel["channel_id"] in seen:
            raise ValueError("duplicate channel_id %r" % (channel["channel_id"],))
        seen.add(channel["channel_id"])
        normalized.append(channel)
    return normalized


def sensitivity_margin_db(signature_dbm, threshold_dbm):
    """Sensitivity-margin in dB: expected event-signature over threshold."""
    signature = _as_float(signature_dbm, "signature_dbm")
    threshold = _as_float(threshold_dbm, "threshold_dbm")
    return signature - threshold


def coverage_summary(channels):
    """Count canonical coverage-scopes over a normalized channel set."""
    summary = {"global-coverage": 0, "local-coverage": 0}
    for channel in channels:
        summary[channel["coverage_scope"]] += 1
    return summary


def independent_families(channels):
    """Sorted distinct observable-families over a normalized channel set."""
    return sorted({channel["observable_family"] for channel in channels})


def duplicated_families(channels):
    """Families declared by more than one channel (redundant, not independent)."""
    counts = {}
    for channel in channels:
        counts[channel["observable_family"]] = (
            counts.get(channel["observable_family"], 0) + 1
        )
    return sorted(name for name, n in counts.items() if n > 1)


def evaluate_channel_registration(
    channel,
    signature_dbm,
    shortest_event_ms,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Decide whether one channel would register the credible discharge.

    Returns a report dict with the margin, the two verdicts and the
    reasons a channel fails. Raises ValueError on a non-positive
    shortest_event_ms or a negative required_margin_db.
    """
    event_ms = _as_float(shortest_event_ms, "shortest_event_ms")
    if event_ms <= 0.0:
        raise ValueError("shortest_event_ms must be > 0, got %r" % (shortest_event_ms,))
    required = _as_float(required_margin_db, "required_margin_db")
    if required < 0.0:
        raise ValueError(
            "required_margin_db must be >= 0, got %r" % (required_margin_db,)
        )
    margin = sensitivity_margin_db(signature_dbm, channel["threshold_dbm"])
    margin_ok = _at_least(margin, required)
    speed_ok = _at_most(channel["response_time_ms"], event_ms)
    reasons = []
    if not margin_ok:
        reasons.append(
            "sensitivity-margin %.3f dB below required %.3f dB" % (margin, required)
        )
    if not speed_ok:
        reasons.append(
            "response-time %.3f ms exceeds shortest discharge-duration %.3f ms"
            % (channel["response_time_ms"], event_ms)
        )
    return {
        "channel_id": channel["channel_id"],
        "coverage_scope": channel["coverage_scope"],
        "observable_family": channel["observable_family"],
        "margin_db": margin,
        "margin_ok": margin_ok,
        "speed_ok": speed_ok,
        "registers": margin_ok and speed_ok,
        "reasons": reasons,
    }


def assess_detection_arrangement(
    entries,
    signature_dbm,
    shortest_event_ms,
    required_margin_db=DEFAULT_REQUIRED_MARGIN_DB,
):
    """Grade a declared detection arrangement against clause 7.1.

    Returns a report dict: normalized channels, per-channel
    registration reports, coverage summary, family independence and the
    findings list. adequate is True only when findings is empty.
    """
    channels = normalize_channel_set(entries)
    reports = [
        evaluate_channel_registration(
            channel, signature_dbm, shortest_event_ms, required_margin_db
        )
        for channel in channels
    ]
    coverage = coverage_summary(channels)
    families = independent_families(channels)
    findings = []
    if len(channels) < MIN_CHANNEL_COUNT:
        findings.append(
            "channel-count %d below minimum arrangement size %d"
            % (len(channels), MIN_CHANNEL_COUNT)
        )
    if coverage["global-coverage"] == 0:
        findings.append("no global-coverage channel declared")
    if coverage["local-coverage"] == 0:
        findings.append("no local-coverage channel declared")
    if len(families) < MIN_INDEPENDENT_FAMILIES:
        findings.append(
            "only %d independent observable-family/families (%s); minimum %d"
            % (len(families), ", ".join(families), MIN_INDEPENDENT_FAMILIES)
        )
    for report in reports:
        if not report["registers"]:
            findings.append(
                "channel %s does not register: %s"
                % (report["channel_id"], "; ".join(report["reasons"]))
            )
    registering_scopes = {r["coverage_scope"] for r in reports if r["registers"]}
    if coverage["global-coverage"] and "global-coverage" not in registering_scopes:
        findings.append("no registering global-coverage channel remains")
    if coverage["local-coverage"] and "local-coverage" not in registering_scopes:
        findings.append("no registering local-coverage channel remains")
    for channel in channels:
        if not channel["calibrated"]:
            findings.append(
                "channel %s declares no calibration traceability"
                % channel["channel_id"]
            )
    return {
        "channels": channels,
        "reports": reports,
        "coverage": coverage,
        "families": families,
        "duplicated_families": duplicated_families(channels),
        "required_margin_db": _as_float(required_margin_db, "required_margin_db"),
        "findings": findings,
        "adequate": not findings,
    }


def format_arrangement_report(report):
    """Render an assessment as deterministic plain-text lines."""
    lines = [
        "multipactor-detection arrangement: %s"
        % ("ADEQUATE" if report["adequate"] else "NOT ADEQUATE"),
        "channels=%d global=%d local=%d families=%s"
        % (
            len(report["channels"]),
            report["coverage"]["global-coverage"],
            report["coverage"]["local-coverage"],
            ",".join(report["families"]),
        ),
    ]
    for item in report["reports"]:
        lines.append(
            "  %s [%s/%s] margin=%.3f dB registers=%s"
            % (
                item["channel_id"],
                item["coverage_scope"],
                item["observable_family"],
                item["margin_db"],
                "yes" if item["registers"] else "no",
            )
        )
    for finding in report["findings"]:
        lines.append("  FINDING: %s" % finding)
    return "\n".join(lines)

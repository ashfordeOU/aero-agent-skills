#!/usr/bin/env python3
"""Status reporting for every on-board functional monitoring definition.

Anchor: ECSS-E-ST-70-41C clause 6.12.4.9. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The companion request reports what the definitions ARE. This one
reports what they are DOING: for each functional monitoring definition
the on-board application holds, whether it is enabled, and what its
current status works out to given the checking status of the parameter
monitoring definitions inside it.

The clause's normative items reduce to five implementable checks:

    1  the report covers every definition held; it takes no identifier
       list and cannot be asked for a subset
    2  each entry carries the definition identifier and its enable
       status
    3  each entry carries the current functional monitoring status,
       derived from the constituents and the failing threshold rather
       than stored as an independent field
    4  a disabled definition reports an unchecked status, and a
       declared status that disagrees with the derived one is a defect
       in the store rather than a reportable state
    5  the report carries a definition count so a receiver can detect
       a truncated transfer

Status derivation, for an enabled definition:

    unchecked   no constituent is currently checking
    failed      the number of constituents outside their limits has
                reached the failing threshold
    running     otherwise; some constituents are checking and the
                group has not reached its threshold

A constituent whose parameter is invalid is not checking and therefore
cannot count towards the threshold. That is the asymmetry the clause
exists to pin down: an invalid parameter must not manufacture a group
failure, and it must not hide one either, so it is counted separately
and reported.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

CONSTITUENT_STATUSES = ("unchecked", "invalid", "within-limits", "out-of-limits")

FUNCTIONAL_STATUSES = ("unchecked", "running", "failed")

CHECKING_STATUSES = ("within-limits", "out-of-limits")

VERDICT_CONSISTENT = "status-report-consistent"
VERDICT_INCONSISTENT = "status-report-inconsistent"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_positive_integer(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %d" % (name, value))
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def validate_constituent_status(record, owner):
    """Normalize the current checking state of one constituent."""
    if not isinstance(record, dict):
        raise ValueError(
            "constituent of %s must be a mapping, got %r" % (owner, record)
        )
    return {
        "parameter_monitoring_id": _require_identifier(
            "constituent parameter_monitoring_id of %s" % owner,
            record.get("parameter_monitoring_id"),
        ),
        "checking_status": _require_choice(
            "constituent checking_status of %s" % owner,
            record.get("checking_status"),
            CONSTITUENT_STATUSES,
        ),
    }


def validate_definition_status(record):
    """Normalize one functional monitoring definition and its constituents."""
    if not isinstance(record, dict):
        raise ValueError("definition must be a mapping, got %r" % (record,))
    definition_id = _require_identifier("definition id", record.get("id"))
    raw = record.get("constituents")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("definition %s constituents must be a list" % definition_id)
    if not raw:
        raise ValueError(
            "definition %s holds no constituent parameter monitoring definitions"
            % definition_id
        )
    constituents = []
    seen = set()
    for item in raw:
        constituent = validate_constituent_status(item, definition_id)
        key = constituent["parameter_monitoring_id"]
        if key in seen:
            raise ValueError(
                "definition %s repeats constituent %r" % (definition_id, key)
            )
        seen.add(key)
        constituents.append(constituent)
    threshold = _require_positive_integer(
        "definition %s failing_threshold" % definition_id,
        record.get("failing_threshold"),
    )
    if threshold > len(constituents):
        raise ValueError(
            "definition %s needs %d failing constituents but holds only %d"
            % (definition_id, threshold, len(constituents))
        )
    normalized = {
        "id": definition_id,
        "enabled": _require_bool(
            "definition %s enabled" % definition_id, record.get("enabled")
        ),
        "constituents": constituents,
        "failing_threshold": threshold,
    }
    declared = record.get("declared_status")
    if declared is not None:
        normalized["declared_status"] = _require_choice(
            "definition %s declared_status" % definition_id,
            declared,
            FUNCTIONAL_STATUSES,
        )
    return normalized


def validate_store(definitions):
    """Normalize the on-board store and reject duplicate identifiers."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    store = []
    seen = set()
    for raw in definitions:
        record = validate_definition_status(raw)
        if record["id"] in seen:
            raise ValueError("duplicate functional monitoring id %r" % record["id"])
        seen.add(record["id"])
        store.append(record)
    return store


def constituent_tally(definition):
    """Count the constituents by what they are currently contributing."""
    record = validate_definition_status(definition)
    tally = {status: 0 for status in CONSTITUENT_STATUSES}
    for constituent in record["constituents"]:
        tally[constituent["checking_status"]] += 1
    tally["checking"] = sum(tally[status] for status in CHECKING_STATUSES)
    tally["total"] = len(record["constituents"])
    return tally


def derive_functional_status(definition):
    """Work out the status a definition is entitled to report."""
    record = validate_definition_status(definition)
    tally = constituent_tally(definition)
    if not record["enabled"]:
        status = "unchecked"
    elif tally["checking"] == 0:
        status = "unchecked"
    elif tally["out-of-limits"] >= record["failing_threshold"]:
        status = "failed"
    else:
        status = "running"
    return {
        "id": record["id"],
        "enabled": record["enabled"],
        "status": status,
        "failing_count": tally["out-of-limits"],
        "failing_threshold": record["failing_threshold"],
        "checking_count": tally["checking"],
        "invalid_count": tally["invalid"],
        "unchecked_count": tally["unchecked"],
        "constituent_count": tally["total"],
    }


def check_status_consistency(definition):
    """Compare a declared status with the one the constituents imply."""
    record = validate_definition_status(definition)
    derived = derive_functional_status(definition)
    findings = []
    declared = record.get("declared_status")
    if declared is not None and declared != derived["status"]:
        findings.append(
            "definition %s declares status %r but its constituents imply %r"
            % (record["id"], declared, derived["status"])
        )
    if not record["enabled"] and derived["failing_count"] > 0:
        findings.append(
            "definition %s is disabled while %d of its constituents are outside "
            "their limits; the group reports unchecked and the failures are not "
            "surfaced by this service"
            % (record["id"], derived["failing_count"])
        )
    if record["enabled"] and derived["invalid_count"] > 0:
        findings.append(
            "definition %s is enabled with %d constituent(s) on an invalid "
            "parameter; those cannot reach the failing threshold"
            % (record["id"], derived["invalid_count"])
        )
    return {
        "id": record["id"],
        "declared_status": declared,
        "derived_status": derived["status"],
        "consistent": not findings,
        "findings": findings,
    }


def status_report_entry(definition):
    """Report entry for one definition: identity, enable state, status."""
    derived = derive_functional_status(definition)
    return {
        "id": derived["id"],
        "enabled": derived["enabled"],
        "status": derived["status"],
        "failing_count": derived["failing_count"],
        "failing_threshold": derived["failing_threshold"],
        "invalid_count": derived["invalid_count"],
        "constituent_count": derived["constituent_count"],
    }


def build_status_report(definitions):
    """Assemble the status report over the whole store, in store order."""
    store = validate_store(definitions)
    entries = [status_report_entry(record) for record in store]
    counts = {status: 0 for status in FUNCTIONAL_STATUSES}
    for entry in entries:
        counts[entry["status"]] += 1
    return {
        "entries": entries,
        "definition_count": len(entries),
        "enabled_count": sum(1 for entry in entries if entry["enabled"]),
        "disabled_count": sum(1 for entry in entries if not entry["enabled"]),
        "status_counts": counts,
    }


def report_is_complete(report):
    """Check a received report's own totals against what it carries."""
    if not isinstance(report, dict):
        raise ValueError("report must be a mapping, got %r" % (report,))
    entries = report.get("entries")
    if not isinstance(entries, (list, tuple)):
        raise ValueError("report entries must be a list")
    declared = report.get("definition_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared < 0:
        raise ValueError("report definition_count must be a non-negative integer")
    findings = []
    if len(entries) != declared:
        findings.append(
            "report declares %d definitions but carries %d" % (declared, len(entries))
        )
    enabled = sum(1 for entry in entries if entry.get("enabled"))
    if report.get("enabled_count") != enabled:
        findings.append(
            "report declares %r enabled definitions but carries %d"
            % (report.get("enabled_count"), enabled)
        )
    return {"complete": not findings, "findings": findings}


def assess_status_report(definitions):
    """Full clause 6.12.4.9 handling: whole-store report plus consistency."""
    store = validate_store(definitions)
    report = build_status_report(definitions)
    consistency = [check_status_consistency(record) for record in store]
    completeness = report_is_complete(report)
    findings = []
    inconsistent = []
    for result in consistency:
        findings.extend(result["findings"])
        if not result["consistent"]:
            inconsistent.append(result["id"])
    findings.extend(completeness["findings"])
    consistent = not inconsistent and completeness["complete"]
    return {
        "report": report,
        "reported_ids": [entry["id"] for entry in report["entries"]],
        "held_count": len(store),
        "covers_whole_store": len(report["entries"]) == len(store),
        "consistency": consistency,
        "inconsistent_ids": inconsistent,
        "complete": completeness["complete"],
        "consistent": consistent,
        "verdict": VERDICT_CONSISTENT if consistent else VERDICT_INCONSISTENT,
        "findings": findings,
    }

#!/usr/bin/env python3
"""Status reporting for every on-board event-action definition.

Anchor: ECSS-E-ST-70-41C clause 6.19.8.5. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The companion request reports what the definitions ARE -- the action
each one carries. This one reports only whether each is armed: for
every event-action definition the on-board application process holds,
the application process identifier, the event definition identifier
and that definition's own enable status.

The clause's normative items reduce to four implementable checks:

    1  the report covers every definition held; it takes no identifier
       list and cannot be asked for a subset
    2  each entry carries the application process identifier, the
       event definition identifier and the enable status of that
       definition
    3  the enable status reported is the definition's own flag; the
       event-action function's enable state is reported alongside it
       and never rewrites it
    4  the report carries a definition count so a receiver can detect
       a truncated transfer

Effective state, from the two flags together:

    disabled    the definition's own flag is clear; nothing happens
                when its event is raised
    inhibited   the definition's flag is set but the event-action
                function of the application process is disabled, so
                nothing happens either -- and the report still says
                enabled, which is correct and is a blind spot
    armed       both flags are set; the action runs when the event is
                raised

Standard library only, offline, deterministic.
"""

from __future__ import annotations

EFFECTIVE_STATES = ("disabled", "inhibited", "armed")

VERDICT_CONSISTENT = "event-action-status-report-consistent"
VERDICT_INCONSISTENT = "event-action-status-report-inconsistent"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


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


def definition_key(record):
    """The pair that identifies one event-action definition."""
    return (record["application_process_id"], record["event_definition_id"])


def validate_event_action_definition(record):
    """Normalize one event-action definition held on board."""
    if not isinstance(record, dict):
        raise ValueError("definition must be a mapping, got %r" % (record,))
    apid = _require_identifier(
        "definition application_process_id", record.get("application_process_id")
    )
    event_id = _require_identifier(
        "definition event_definition_id of %s" % apid,
        record.get("event_definition_id"),
    )
    normalized = {
        "application_process_id": apid,
        "event_definition_id": event_id,
        "enabled": _require_bool(
            "definition %s/%s enabled" % (apid, event_id), record.get("enabled")
        ),
    }
    declared = record.get("declared_effective_state")
    if declared is not None:
        normalized["declared_effective_state"] = _require_choice(
            "definition %s/%s declared_effective_state" % (apid, event_id),
            declared,
            EFFECTIVE_STATES,
        )
    return normalized


def validate_store(definitions):
    """Normalize the on-board store and reject a repeated process/event pair."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    store = []
    seen = set()
    for raw in definitions:
        record = validate_event_action_definition(raw)
        key = definition_key(record)
        if key in seen:
            raise ValueError(
                "duplicate event-action definition for application process %s "
                "and event %s" % key
            )
        seen.add(key)
        store.append(record)
    return store


def validate_function_states(function_states):
    """Normalize the per-application-process event-action function flags."""
    if not isinstance(function_states, dict):
        raise ValueError(
            "function_states must be a mapping of application process id to "
            "boolean, got %r" % (function_states,)
        )
    normalized = {}
    for apid, flag in function_states.items():
        key = _require_identifier("function_states key", apid)
        normalized[key] = _require_bool("function_states[%s]" % key, flag)
    return normalized


def function_enabled(function_states, application_process_id):
    """The event-action function flag for one application process."""
    states = validate_function_states(function_states)
    apid = _require_identifier("application_process_id", application_process_id)
    if apid not in states:
        raise ValueError(
            "no event-action function state declared for application process %s; "
            "an undeclared function state is unknown, not enabled" % apid
        )
    return states[apid]


def derive_effective_state(definition, function_states):
    """Work out what a definition will actually do, from both flags."""
    record = validate_event_action_definition(definition)
    on = function_enabled(function_states, record["application_process_id"])
    if not record["enabled"]:
        state = "disabled"
    elif not on:
        state = "inhibited"
    else:
        state = "armed"
    return {
        "application_process_id": record["application_process_id"],
        "event_definition_id": record["event_definition_id"],
        "enabled": record["enabled"],
        "function_enabled": on,
        "effective_state": state,
    }


def status_report_entry(definition, function_states):
    """Report entry for one definition: identity plus its own enable flag."""
    derived = derive_effective_state(definition, function_states)
    return {
        "application_process_id": derived["application_process_id"],
        "event_definition_id": derived["event_definition_id"],
        "enabled": derived["enabled"],
    }


def check_status_consistency(definition, function_states):
    """Compare a declared effective state with the one the flags imply."""
    record = validate_event_action_definition(definition)
    derived = derive_effective_state(definition, function_states)
    findings = []
    declared = record.get("declared_effective_state")
    if declared is not None and declared != derived["effective_state"]:
        findings.append(
            "definition %s/%s declares effective state %r but its flags imply %r"
            % (
                record["application_process_id"],
                record["event_definition_id"],
                declared,
                derived["effective_state"],
            )
        )
    if derived["effective_state"] == "inhibited":
        findings.append(
            "definition %s/%s reports enabled while the event-action function of "
            "that application process is disabled; the action will not run"
            % (record["application_process_id"], record["event_definition_id"])
        )
    return {
        "application_process_id": record["application_process_id"],
        "event_definition_id": record["event_definition_id"],
        "declared_effective_state": declared,
        "derived_effective_state": derived["effective_state"],
        "consistent": not findings,
        "findings": findings,
    }


def build_status_report(definitions, function_states):
    """Assemble the status report over the whole store, in store order."""
    store = validate_store(definitions)
    states = validate_function_states(function_states)
    entries = [status_report_entry(record, states) for record in store]
    effective_counts = {state: 0 for state in EFFECTIVE_STATES}
    for record in store:
        effective_counts[derive_effective_state(record, states)["effective_state"]] += 1
    return {
        "entries": entries,
        "definition_count": len(entries),
        "enabled_count": sum(1 for entry in entries if entry["enabled"]),
        "disabled_count": sum(1 for entry in entries if not entry["enabled"]),
        "function_states": dict(states),
        "effective_counts": effective_counts,
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


def assess_status_report(definitions, function_states):
    """Full clause 6.19.8.5 handling: whole-store report plus consistency."""
    store = validate_store(definitions)
    states = validate_function_states(function_states)
    report = build_status_report(definitions, states)
    consistency = [check_status_consistency(record, states) for record in store]
    completeness = report_is_complete(report)
    findings = []
    inconsistent = []
    for result in consistency:
        findings.extend(result["findings"])
        if not result["consistent"]:
            inconsistent.append(
                (result["application_process_id"], result["event_definition_id"])
            )
    findings.extend(completeness["findings"])
    consistent = not inconsistent and completeness["complete"]
    return {
        "report": report,
        "reported_keys": [definition_key(record) for record in store],
        "held_count": len(store),
        "covers_whole_store": len(report["entries"]) == len(store),
        "consistency": consistency,
        "inconsistent_keys": inconsistent,
        "inhibited_keys": [
            definition_key(record)
            for record in store
            if derive_effective_state(record, states)["effective_state"] == "inhibited"
        ],
        "complete": completeness["complete"],
        "consistent": consistent,
        "verdict": VERDICT_CONSISTENT if consistent else VERDICT_INCONSISTENT,
        "findings": findings,
    }

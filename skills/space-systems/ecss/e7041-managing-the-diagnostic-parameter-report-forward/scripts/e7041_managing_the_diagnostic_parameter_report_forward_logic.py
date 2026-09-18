"""Diagnostic parameter report forward-control configuration of the
real-time forwarding control service.

Anchor: ECSS-E-ST-70-41C clause 6.14.3.6 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the configuration is. Diagnostic parameter reports are selected
the same way housekeeping reports are -- per application process, one
report structure at a time -- because every diagnostic report of an
application process shares one report type and message subtype and is
told apart only by the structure it came from.

Why the diagnostic side needs its own arithmetic. Diagnostic structures
are the fine-grained ones: they sample at the short intervals used to
chase an anomaly, and several of them forwarded at once can occupy far
more of the real-time downlink than the same number of housekeeping
structures would. So this module carries, beside the add/delete
bookkeeping, the packet rate the current selection produces and grades
it against the rate the real-time forwarding path is allowed to use.

Two further states matter on the diagnostic side. A structure whose
periodic generation is currently disabled can be selected -- there is
nothing wrong with arming a selection ahead of the collection -- but it
contributes no traffic, so it is reported as dormant rather than
counted in the rate. And a selection whose definition has since been
deleted is stale and forwards nothing at all.

Stdlib only, offline, deterministic.
"""

APID_MIN = 0
APID_MAX = 2047
STRUCTURE_ID_MIN = 0
STRUCTURE_ID_MAX = 255

MAX_APPLICATION_PROCESSES = 64
MAX_STRUCTURES_PER_APPLICATION_PROCESS = 48

# A packet rate is a sum of reciprocals of measured intervals, so a
# selection sitting exactly on its budget can land a few units in the
# last place above it. A nanohertz is far below any realisable
# collection interval and absorbs that representation error without
# widening the budget itself.
RATE_TOLERANCE_HZ = 1.0e-9

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_APPLICATION_PROCESS_NOT_CONTROLLED = "application-process-not-controlled"
REASON_STRUCTURE_NOT_DEFINED = "diagnostic-structure-not-defined-for-this-application-process"
REASON_ALREADY_FORWARDED = "structure-already-in-the-configuration"
REASON_SUBSUMED_BY_WILDCARD = "structure-subsumed-by-the-all-structures-wildcard"
REASON_NOT_IN_CONFIGURATION = "structure-absent-from-the-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = "all-structures-wildcard-not-partially-deletable"
REASON_APPLICATION_PROCESS_CAPACITY = "application-process-capacity-exhausted"
REASON_STRUCTURE_CAPACITY = "structure-capacity-exhausted"

FINDING_RATE_OVER_BUDGET = "forwarded-diagnostic-rate-over-real-time-budget"
FINDING_DORMANT_SELECTION = "selection-on-a-structure-whose-collection-is-disabled"
FINDING_STALE_SELECTION = "selection-on-a-structure-definition-that-was-deleted"


def _integer(label, value, low, high):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < low or value > high:
        raise ValueError("%s must be in [%d, %d], got %d" % (label, low, high, value))
    return value


def _positive(label, value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if value <= 0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return float(value)


def validate_definition_catalogue(catalogue):
    """Validate the diagnostic structure catalogue and normalize it.

    Each entry maps an application process to its structures, and each
    structure declares its collection interval in seconds and whether
    its periodic generation is currently enabled.
    """
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of apid to structures")
    out = {}
    for apid, structures in catalogue.items():
        _integer("catalogue application process", apid, APID_MIN, APID_MAX)
        if not isinstance(structures, dict):
            raise ValueError(
                "catalogue entry for application process %d must be a mapping "
                "of structure identifier to definition" % apid
            )
        collected = {}
        for structure_id, definition in structures.items():
            _integer(
                "catalogue structure identifier", structure_id,
                STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
            )
            if not isinstance(definition, dict):
                raise ValueError(
                    "definition of structure %d/%d must be a mapping"
                    % (apid, structure_id)
                )
            interval = _positive(
                "collection interval of structure %d/%d" % (apid, structure_id),
                definition.get("collection_interval_s"),
            )
            enabled = definition.get("collection_enabled", True)
            if not isinstance(enabled, bool):
                raise ValueError(
                    "collection_enabled of structure %d/%d must be a boolean"
                    % (apid, structure_id)
                )
            collected[structure_id] = {
                "collection_interval_s": interval,
                "collection_enabled": enabled,
            }
        out[apid] = collected
    return out


def structure_is_defined(catalogue, apid, structure_id):
    """Is this structure identifier defined under this application process?"""
    known = validate_definition_catalogue(catalogue)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("structure identifier", structure_id, STRUCTURE_ID_MIN, STRUCTURE_ID_MAX)
    return structure_id in known.get(apid, {})


def structure_report_rate_hz(catalogue, apid, structure_id):
    """Packet rate one diagnostic structure produces, in hertz."""
    known = validate_definition_catalogue(catalogue)
    entry = known.get(apid, {}).get(structure_id)
    if entry is None:
        raise ValueError(
            "structure %r is not defined under application process %r"
            % (structure_id, apid)
        )
    if not entry["collection_enabled"]:
        return 0.0
    return 1.0 / entry["collection_interval_s"]


def validate_selection(item):
    """Validate one add/delete item and return it in normalized form."""
    if not isinstance(item, dict):
        raise ValueError("selection item must be a mapping")
    apid = _integer(
        "selection application process", item.get("apid"), APID_MIN, APID_MAX
    )
    structure_id = item.get("structure_id")
    if structure_id is not None:
        structure_id = _integer(
            "selection structure identifier", structure_id,
            STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
        )
    return {"apid": apid, "structure_id": structure_id}


def empty_configuration():
    """A diagnostic forward-control configuration forwarding nothing."""
    return {}


def normalize_configuration(config):
    """Validate a configuration and return an independent normalized copy."""
    if not isinstance(config, dict):
        raise ValueError("configuration must be a mapping")
    out = {}
    for apid, entry in config.items():
        _integer("configuration application process", apid, APID_MIN, APID_MAX)
        if not isinstance(entry, dict):
            raise ValueError("configuration entry for %d must be a mapping" % apid)
        all_structures = entry.get("all_structures", False)
        if not isinstance(all_structures, bool):
            raise ValueError("all_structures for %d must be a boolean" % apid)
        structures = entry.get("structure_ids", [])
        if not isinstance(structures, (list, tuple, set, frozenset)):
            raise ValueError("structure_ids for %d must be a collection" % apid)
        collected = set()
        for structure_id in structures:
            collected.add(
                _integer(
                    "configuration structure identifier", structure_id,
                    STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
                )
            )
        if all_structures and collected:
            raise ValueError(
                "application process %d carries the all-structures wildcard and "
                "explicit structure identifiers at the same time" % apid
            )
        out[apid] = {"all_structures": all_structures, "structure_ids": collected}
    return out


def is_diagnostic_report_forwarded(config, apid, structure_id):
    """Decide whether one diagnostic parameter report is forwarded."""
    working = normalize_configuration(config)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("structure identifier", structure_id, STRUCTURE_ID_MIN, STRUCTURE_ID_MAX)
    entry = working.get(apid)
    if entry is None:
        return False
    if entry["all_structures"]:
        return True
    return structure_id in entry["structure_ids"]


def selected_structures(config, catalogue, apid):
    """Defined structures of one application process the configuration selects."""
    working = normalize_configuration(config)
    known = validate_definition_catalogue(catalogue)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    entry = working.get(apid)
    if entry is None:
        return []
    defined = set(known.get(apid, {}))
    if entry["all_structures"]:
        return sorted(defined)
    return sorted(entry["structure_ids"] & defined)


def forwarded_report_rate_hz(config, catalogue):
    """Total packet rate the current selection puts on the real-time path."""
    working = normalize_configuration(config)
    known = validate_definition_catalogue(catalogue)
    total = 0.0
    for apid in sorted(working):
        for structure_id in selected_structures(working, known, apid):
            total += structure_report_rate_hz(known, apid, structure_id)
    return total


def _normalize_controlled(controlled_apids):
    if not isinstance(controlled_apids, (list, tuple, set, frozenset)):
        raise ValueError("controlled_apids must be a collection")
    controlled = set()
    for item in controlled_apids:
        controlled.add(
            _integer("controlled application process", item, APID_MIN, APID_MAX)
        )
    if not controlled:
        raise ValueError("controlled_apids must not be empty")
    return controlled


def _add_one(working, controlled, known, selection):
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    if apid not in controlled:
        return REJECTED, REASON_APPLICATION_PROCESS_NOT_CONTROLLED
    if structure_id is not None and structure_id not in known.get(apid, {}):
        return REJECTED, REASON_STRUCTURE_NOT_DEFINED
    entry = working.get(apid)
    if entry is None:
        if len(working) >= MAX_APPLICATION_PROCESSES:
            return REJECTED, REASON_APPLICATION_PROCESS_CAPACITY
        entry = {"all_structures": False, "structure_ids": set()}
        working[apid] = entry
    if structure_id is None:
        if entry["all_structures"]:
            return REJECTED, REASON_ALREADY_FORWARDED
        entry["all_structures"] = True
        entry["structure_ids"] = set()
        return ACCEPTED, "all-structures-wildcard-set"
    if entry["all_structures"]:
        return REJECTED, REASON_SUBSUMED_BY_WILDCARD
    if structure_id in entry["structure_ids"]:
        return REJECTED, REASON_ALREADY_FORWARDED
    if len(entry["structure_ids"]) >= MAX_STRUCTURES_PER_APPLICATION_PROCESS:
        return REJECTED, REASON_STRUCTURE_CAPACITY
    entry["structure_ids"].add(structure_id)
    return ACCEPTED, "structure-added"


def _delete_one(working, selection):
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    entry = working.get(apid)
    if entry is None:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    if structure_id is None:
        del working[apid]
        return ACCEPTED, "application-process-entry-deleted"
    if entry["all_structures"]:
        return REJECTED, REASON_WILDCARD_NOT_PARTIALLY_DELETABLE
    if structure_id not in entry["structure_ids"]:
        return REJECTED, REASON_NOT_IN_CONFIGURATION
    entry["structure_ids"].discard(structure_id)
    return ACCEPTED, "structure-deleted"


def _run(config, items, handler):
    working = normalize_configuration(config)
    if not isinstance(items, (list, tuple)):
        raise ValueError("request items must be a list")
    dispositions = []
    for index, raw in enumerate(items):
        selection = validate_selection(raw)
        status, reason = handler(working, selection)
        dispositions.append(
            {
                "index": index,
                "apid": selection["apid"],
                "structure_id": selection["structure_id"],
                "status": status,
                "reason": reason,
            }
        )
    return working, dispositions


def add_diagnostic_selections(config, controlled_apids, catalogue, items):
    """Apply an add request; return the new configuration and per-item outcome."""
    controlled = _normalize_controlled(controlled_apids)
    known = validate_definition_catalogue(catalogue)
    return _run(config, items, lambda w, s: _add_one(w, controlled, known, s))


def delete_diagnostic_selections(config, items):
    """Apply a delete request; return the new configuration and per-item outcome."""
    return _run(config, items, lambda w, s: _delete_one(w, s))


def dormant_selections(config, catalogue):
    """Selections whose structure is defined but not currently collected."""
    working = normalize_configuration(config)
    known = validate_definition_catalogue(catalogue)
    dormant = []
    for apid in sorted(working):
        for structure_id in selected_structures(working, known, apid):
            if not known[apid][structure_id]["collection_enabled"]:
                dormant.append({"apid": apid, "structure_id": structure_id})
    return dormant


def stale_selections(config, catalogue):
    """Selected identifiers the catalogue no longer defines."""
    working = normalize_configuration(config)
    known = validate_definition_catalogue(catalogue)
    stale = []
    for apid in sorted(working):
        entry = working[apid]
        if entry["all_structures"]:
            continue
        defined = set(known.get(apid, {}))
        for structure_id in sorted(entry["structure_ids"] - defined):
            stale.append({"apid": apid, "structure_id": structure_id})
    return stale


def report_configuration(config):
    """Deterministic report of the configuration, sorted at every level."""
    working = normalize_configuration(config)
    entries = []
    for apid in sorted(working):
        entry = working[apid]
        entries.append(
            {
                "apid": apid,
                "all_structures": entry["all_structures"],
                "structure_ids": sorted(entry["structure_ids"]),
            }
        )
    return {
        "application_processes": entries,
        "application_process_count": len(entries),
        "forwards_nothing": not entries,
    }


def grade_rate_budget(config, catalogue, budget_hz):
    """Grade the forwarded diagnostic packet rate against its budget."""
    budget = _positive("budget_hz", budget_hz)
    rate = forwarded_report_rate_hz(config, catalogue)
    over = rate > budget + RATE_TOLERANCE_HZ
    return {
        "forwarded_rate_hz": rate,
        "budget_hz": budget,
        "margin_hz": budget - rate,
        "within_budget": not over,
        "findings": [FINDING_RATE_OVER_BUDGET] if over else [],
    }


def assess_diagnostic_forward_control(
    config, controlled_apids, catalogue, requests, budget_hz
):
    """Run a sequence of add/delete requests and grade the resulting load."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("requests must be a non-empty list")
    working = normalize_configuration(config)
    outcomes = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("request must be a mapping")
        operation = request.get("operation")
        if operation == "add":
            working, dispositions = add_diagnostic_selections(
                working, controlled_apids, catalogue, request.get("items", [])
            )
        elif operation == "delete":
            working, dispositions = delete_diagnostic_selections(
                working, request.get("items", [])
            )
        else:
            raise ValueError("unknown request operation %r" % (operation,))
        outcomes.append(
            {
                "operation": operation,
                "dispositions": dispositions,
                "rejected_count": sum(
                    1 for d in dispositions if d["status"] == REJECTED
                ),
            }
        )
    budget = grade_rate_budget(working, catalogue, budget_hz)
    dormant = dormant_selections(working, catalogue)
    stale = stale_selections(working, catalogue)
    findings = list(budget["findings"])
    if dormant:
        findings.append(FINDING_DORMANT_SELECTION)
    if stale:
        findings.append(FINDING_STALE_SELECTION)
    return {
        "configuration": working,
        "outcomes": outcomes,
        "report": report_configuration(working),
        "budget": budget,
        "dormant_selections": dormant,
        "stale_selections": stale,
        "findings": findings,
        "rejected_total": sum(o["rejected_count"] for o in outcomes),
        "acceptable": not findings,
    }

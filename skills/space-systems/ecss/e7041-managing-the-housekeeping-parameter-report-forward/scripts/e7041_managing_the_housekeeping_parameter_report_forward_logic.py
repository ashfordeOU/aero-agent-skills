"""Housekeeping parameter report forward-control configuration of the
real-time forwarding control service.

Anchor: ECSS-E-ST-70-41C clause 6.14.3.5 (paraphrased into an
implementable procedure; no standard text is reproduced).

What the configuration is. Housekeeping parameter reports are not
selected by subtype alone, because every housekeeping report of an
application process shares one subtype and they differ only by the
report structure they were generated from. So the real-time forwarding
control service holds a second, finer configuration: per application
process, the set of housekeeping parameter report structures whose
reports are forwarded.

Structures are declared, not invented. A structure identifier only
means something inside the application process that defines it, so the
same identifier under two application processes is two different
structures, and an identifier the housekeeping service never defined
cannot be selected.

Wildcards. An application process entry holding no structure
identifiers forwards every housekeeping parameter report of that
application process, including structures defined after the entry was
made. A wildcard and specific identifiers cannot be held together.

Requests execute per item: each identifier is accepted or rejected on
its own and the rest of the request still runs.

Stdlib only, offline, deterministic.
"""

APID_MIN = 0
APID_MAX = 2047
STRUCTURE_ID_MIN = 0
STRUCTURE_ID_MAX = 255

MAX_APPLICATION_PROCESSES = 64
MAX_STRUCTURES_PER_APPLICATION_PROCESS = 48

ACCEPTED = "accepted"
REJECTED = "rejected"

REASON_APPLICATION_PROCESS_NOT_CONTROLLED = "application-process-not-controlled"
REASON_STRUCTURE_NOT_DEFINED = "housekeeping-structure-not-defined-for-this-application-process"
REASON_ALREADY_FORWARDED = "structure-already-in-the-configuration"
REASON_SUBSUMED_BY_WILDCARD = "structure-subsumed-by-the-all-structures-wildcard"
REASON_NOT_IN_CONFIGURATION = "structure-absent-from-the-configuration"
REASON_WILDCARD_NOT_PARTIALLY_DELETABLE = "all-structures-wildcard-not-partially-deletable"
REASON_APPLICATION_PROCESS_CAPACITY = "application-process-capacity-exhausted"
REASON_STRUCTURE_CAPACITY = "structure-capacity-exhausted"


def _integer(label, value, low, high):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < low or value > high:
        raise ValueError("%s must be in [%d, %d], got %d" % (label, low, high, value))
    return value


def validate_definition_catalogue(catalogue):
    """Validate the housekeeping structure catalogue and normalize it."""
    if not isinstance(catalogue, dict) or not catalogue:
        raise ValueError("catalogue must be a non-empty mapping of apid to structures")
    out = {}
    for apid, structures in catalogue.items():
        _integer("catalogue application process", apid, APID_MIN, APID_MAX)
        if not isinstance(structures, (list, tuple, set, frozenset)):
            raise ValueError(
                "catalogue entry for application process %d must be a collection" % apid
            )
        collected = set()
        for structure_id in structures:
            collected.add(
                _integer(
                    "catalogue structure identifier", structure_id,
                    STRUCTURE_ID_MIN, STRUCTURE_ID_MAX,
                )
            )
        out[apid] = collected
    return out


def structure_is_defined(catalogue, apid, structure_id):
    """Is this structure identifier defined under this application process?"""
    known = validate_definition_catalogue(catalogue)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("structure identifier", structure_id, STRUCTURE_ID_MIN, STRUCTURE_ID_MAX)
    return structure_id in known.get(apid, set())


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
    """A housekeeping forward-control configuration forwarding nothing."""
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


def is_housekeeping_report_forwarded(config, apid, structure_id):
    """Decide whether one housekeeping parameter report is forwarded."""
    working = normalize_configuration(config)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    _integer("structure identifier", structure_id, STRUCTURE_ID_MIN, STRUCTURE_ID_MAX)
    entry = working.get(apid)
    if entry is None:
        return False
    if entry["all_structures"]:
        return True
    return structure_id in entry["structure_ids"]


def _add_one(working, controlled, catalogue, selection):
    apid = selection["apid"]
    structure_id = selection["structure_id"]
    if apid not in controlled:
        return REJECTED, REASON_APPLICATION_PROCESS_NOT_CONTROLLED
    if structure_id is not None and not structure_is_defined(catalogue, apid, structure_id):
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


def add_housekeeping_selections(config, controlled_apids, catalogue, items):
    """Apply an add request; return the new configuration and per-item outcome."""
    controlled = _normalize_controlled(controlled_apids)
    known = validate_definition_catalogue(catalogue)
    return _run(config, items, lambda w, s: _add_one(w, controlled, known, s))


def delete_housekeeping_selections(config, items):
    """Apply a delete request; return the new configuration and per-item outcome."""
    return _run(config, items, lambda w, s: _delete_one(w, s))


def forwarded_structures(config, catalogue, apid):
    """Structures of one application process the configuration forwards now."""
    working = normalize_configuration(config)
    known = validate_definition_catalogue(catalogue)
    _integer("application process identifier", apid, APID_MIN, APID_MAX)
    entry = working.get(apid)
    if entry is None:
        return []
    defined = known.get(apid, set())
    if entry["all_structures"]:
        return sorted(defined)
    return sorted(entry["structure_ids"] & defined)


def stale_selections(config, catalogue):
    """Selected structures the catalogue no longer defines."""
    working = normalize_configuration(config)
    known = validate_definition_catalogue(catalogue)
    stale = []
    for apid in sorted(working):
        entry = working[apid]
        if entry["all_structures"]:
            continue
        for structure_id in sorted(entry["structure_ids"] - known.get(apid, set())):
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


def assess_housekeeping_forward_control(config, controlled_apids, catalogue, requests):
    """Run a sequence of add/delete requests and grade the result."""
    if not isinstance(requests, (list, tuple)) or not requests:
        raise ValueError("requests must be a non-empty list")
    working = normalize_configuration(config)
    outcomes = []
    for request in requests:
        if not isinstance(request, dict):
            raise ValueError("request must be a mapping")
        operation = request.get("operation")
        if operation == "add":
            working, dispositions = add_housekeeping_selections(
                working, controlled_apids, catalogue, request.get("items", [])
            )
        elif operation == "delete":
            working, dispositions = delete_housekeeping_selections(
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
    stale = stale_selections(working, catalogue)
    return {
        "configuration": working,
        "outcomes": outcomes,
        "report": report_configuration(working),
        "stale_selections": stale,
        "rejected_total": sum(o["rejected_count"] for o in outcomes),
        "clean": not stale and all(o["rejected_count"] == 0 for o in outcomes),
    }

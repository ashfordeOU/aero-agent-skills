#!/usr/bin/env python3
"""Re-pointing on-board raw memory parameters at different memory windows.

Anchor: ECSS-E-ST-70-41C clause 6.20.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A raw memory parameter holds no value of its own. It is a window onto
memory -- a memory area, a base address inside it and a length -- and
its value is whatever those bytes read as. Changing the definition
moves the window, so nothing about the value can catch a bad change;
only the geometry can, and only before the change lands.

The clause's normative items reduce to seven implementable checks:

    1  the request carries a list of changes, each naming a raw
       memory parameter and the area, base and length to give it
    2  a change naming no known raw memory parameter is refused
    3  a change naming a memory area the memory management service
       does not hold is refused
    4  a region that runs past the end of its area is refused; the
       region covers base .. base + length - 1 and the end may sit
       exactly at the area size
    5  a base that breaks the area's declared access alignment is
       refused, because an unaligned read answers with something that
       is not the parameter
    6  a length that disagrees with the width the parameter's
       representation needs is refused, because a short window
       truncates and a long one reads a neighbour in
    7  the surviving changes are applied independently and the
       outcome carries applied and refused totals that account for
       every distinct change

The four geometry refusals are screened in a fixed order -- unknown
area, bounds, alignment, length -- so the reason reported is the
first thing actually wrong rather than whichever check happened to
run first.

Two definitions that come to address the same bytes are legal and
usually a mistake. They are applied and raised as a hazard, never
refused.

All arithmetic is integer arithmetic on byte counts, so a bound is
exact at every width on every platform.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

REFUSAL_UNKNOWN_PARAMETER = "no-such-raw-memory-parameter"
REFUSAL_UNKNOWN_AREA = "no-such-memory-area"
REFUSAL_OUT_OF_BOUNDS = "region-outside-memory-area"
REFUSAL_MISALIGNED = "base-breaks-area-alignment"
REFUSAL_WRONG_LENGTH = "length-disagrees-with-representation"

REFUSALS = (
    REFUSAL_UNKNOWN_PARAMETER,
    REFUSAL_UNKNOWN_AREA,
    REFUSAL_OUT_OF_BOUNDS,
    REFUSAL_MISALIGNED,
    REFUSAL_WRONG_LENGTH,
)

VERDICT_APPLIED = "raw-memory-definition-change-applied"
VERDICT_PARTIAL = "raw-memory-definition-change-partially-applied"
VERDICT_FAILED_START = "raw-memory-definition-change-failed-start"


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


def _require_offset(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (name, value))
    return value


def validate_memory_area(record):
    """Normalize one memory area: identifier, size and access alignment."""
    if not isinstance(record, dict):
        raise ValueError("memory area must be a mapping, got %r" % (record,))
    area_id = _require_identifier("memory area id", record.get("id"))
    return {
        "id": area_id,
        "size_bytes": _require_positive_integer(
            "memory area %s size_bytes" % area_id, record.get("size_bytes")
        ),
        "alignment_bytes": _require_positive_integer(
            "memory area %s alignment_bytes" % area_id,
            record.get("alignment_bytes", 1),
        ),
    }


def validate_memory_map(areas):
    """Normalize the memory areas the memory management service holds."""
    if not isinstance(areas, (list, tuple)):
        raise ValueError("memory areas must be a list, got %r" % (areas,))
    memory_map = {}
    for raw in areas:
        area = validate_memory_area(raw)
        if area["id"] in memory_map:
            raise ValueError("duplicate memory area %r" % area["id"])
        memory_map[area["id"]] = area
    return memory_map


def validate_raw_memory_parameter(record):
    """Normalize one raw memory parameter definition and its current window."""
    if not isinstance(record, dict):
        raise ValueError("raw memory parameter must be a mapping, got %r" % (record,))
    parameter_id = _require_identifier(
        "raw memory parameter id", record.get("parameter_id")
    )
    return {
        "parameter_id": parameter_id,
        "width_bytes": _require_positive_integer(
            "raw memory parameter %s width_bytes" % parameter_id,
            record.get("width_bytes"),
        ),
        "memory_area_id": _require_identifier(
            "raw memory parameter %s memory_area_id" % parameter_id,
            record.get("memory_area_id"),
        ),
        "base_address": _require_offset(
            "raw memory parameter %s base_address" % parameter_id,
            record.get("base_address"),
        ),
        "length_bytes": _require_positive_integer(
            "raw memory parameter %s length_bytes" % parameter_id,
            record.get("length_bytes"),
        ),
    }


def validate_definition_store(parameters):
    """Normalize the raw memory parameter definitions, rejecting a repeat."""
    if not isinstance(parameters, (list, tuple)):
        raise ValueError("raw memory parameters must be a list, got %r" % (parameters,))
    store = []
    seen = set()
    for raw in parameters:
        record = validate_raw_memory_parameter(raw)
        if record["parameter_id"] in seen:
            raise ValueError(
                "duplicate raw memory parameter %r" % record["parameter_id"]
            )
        seen.add(record["parameter_id"])
        store.append(record)
    return store


def validate_change(record, index):
    """Normalize one requested change: the parameter and its new window."""
    if not isinstance(record, dict):
        raise ValueError("change %d must be a mapping, got %r" % (index, record))
    return {
        "parameter_id": _require_identifier(
            "change %d parameter_id" % index, record.get("parameter_id")
        ),
        "memory_area_id": _require_identifier(
            "change %d memory_area_id" % index, record.get("memory_area_id")
        ),
        "base_address": _require_offset(
            "change %d base_address" % index, record.get("base_address")
        ),
        "length_bytes": _require_positive_integer(
            "change %d length_bytes" % index, record.get("length_bytes")
        ),
    }


def validate_changes(changes):
    """Normalize the change list, last change winning on a repeated parameter."""
    if not isinstance(changes, (list, tuple)):
        raise ValueError("changes must be a list, got %r" % (changes,))
    if not changes:
        raise ValueError(
            "a raw memory definition change request carries at least one change; "
            "an empty request is not a successful no-op"
        )
    normalized = [validate_change(raw, index) for index, raw in enumerate(changes)]
    last = {}
    for item in normalized:
        last[item["parameter_id"]] = item
    ordered = []
    emitted = set()
    for item in normalized:
        key = item["parameter_id"]
        if key in emitted:
            continue
        emitted.add(key)
        ordered.append(last[key])
    repeated = [
        key
        for key in emitted
        if sum(1 for item in normalized if item["parameter_id"] == key) > 1
    ]
    return {
        "changes": ordered,
        "repeated": sorted(repeated),
        "submitted_count": len(normalized),
        "distinct_count": len(ordered),
    }


def region_end(base_address, length_bytes):
    """One past the last byte the window addresses."""
    base = _require_offset("base_address", base_address)
    length = _require_positive_integer("length_bytes", length_bytes)
    return base + length


def regions_overlap(first, second):
    """Whether two windows in the same area address any byte in common."""
    if first["memory_area_id"] != second["memory_area_id"]:
        return False
    first_end = region_end(first["base_address"], first["length_bytes"])
    second_end = region_end(second["base_address"], second["length_bytes"])
    return first["base_address"] < second_end and second["base_address"] < first_end


def screen_change(change, parameter, memory_map):
    """Screen one change's geometry, reporting the first thing actually wrong."""
    if parameter is None:
        return {
            "acceptable": False,
            "refusal": REFUSAL_UNKNOWN_PARAMETER,
            "reason": "no raw memory parameter named %s" % change["parameter_id"],
        }
    area = memory_map.get(change["memory_area_id"])
    if area is None:
        return {
            "acceptable": False,
            "refusal": REFUSAL_UNKNOWN_AREA,
            "reason": "no memory area named %s" % change["memory_area_id"],
        }
    end = region_end(change["base_address"], change["length_bytes"])
    if end > area["size_bytes"]:
        return {
            "acceptable": False,
            "refusal": REFUSAL_OUT_OF_BOUNDS,
            "reason": "region ends at byte %d, past the %d bytes of area %s"
            % (end, area["size_bytes"], area["id"]),
        }
    if change["base_address"] % area["alignment_bytes"]:
        return {
            "acceptable": False,
            "refusal": REFUSAL_MISALIGNED,
            "reason": "base %d is not a multiple of the %d byte alignment of area %s"
            % (change["base_address"], area["alignment_bytes"], area["id"]),
        }
    if change["length_bytes"] != parameter["width_bytes"]:
        return {
            "acceptable": False,
            "refusal": REFUSAL_WRONG_LENGTH,
            "reason": "length %d does not match the %d bytes parameter %s needs"
            % (
                change["length_bytes"],
                parameter["width_bytes"],
                parameter["parameter_id"],
            ),
        }
    return {"acceptable": True, "refusal": None, "reason": None}


def screen_changes(parameters, areas, changes):
    """Screen every requested change, keeping request order."""
    store = validate_definition_store(parameters)
    memory_map = validate_memory_map(areas)
    request = validate_changes(changes)
    index = {record["parameter_id"]: record for record in store}
    acceptable = []
    refused = []
    for change in request["changes"]:
        verdict = screen_change(change, index.get(change["parameter_id"]), memory_map)
        if verdict["acceptable"]:
            acceptable.append(change)
        else:
            refused.append(
                {
                    "parameter_id": change["parameter_id"],
                    "refusal": verdict["refusal"],
                    "reason": verdict["reason"],
                }
            )
    return {
        "acceptable": acceptable,
        "refused": refused,
        "repeated": request["repeated"],
        "submitted_count": request["submitted_count"],
        "distinct_count": request["distinct_count"],
        "memory_map": memory_map,
    }


def overlap_hazards(parameters):
    """Every pair of definitions addressing a byte in common, in store order."""
    store = validate_definition_store(parameters)
    hazards = []
    for i, first in enumerate(store):
        for second in store[i + 1:]:
            if regions_overlap(first, second):
                hazards.append((first["parameter_id"], second["parameter_id"]))
    return hazards


def apply_changes(parameters, areas, changes):
    """Apply what survives screening into a NEW store; never mutate the old."""
    screening = screen_changes(parameters, areas, changes)
    store = validate_definition_store(parameters)
    if not screening["acceptable"]:
        return {
            "applied": False,
            "store": store,
            "changed": [],
            "refused": screening["refused"],
            "screening": screening,
        }
    pending = {change["parameter_id"]: change for change in screening["acceptable"]}
    new_store = []
    changed = []
    for record in store:
        updated = dict(record)
        change = pending.get(record["parameter_id"])
        if change is not None:
            changed.append(
                {
                    "parameter_id": record["parameter_id"],
                    "previous_window": {
                        "memory_area_id": record["memory_area_id"],
                        "base_address": record["base_address"],
                        "length_bytes": record["length_bytes"],
                    },
                    "window": {
                        "memory_area_id": change["memory_area_id"],
                        "base_address": change["base_address"],
                        "length_bytes": change["length_bytes"],
                    },
                }
            )
            updated["memory_area_id"] = change["memory_area_id"]
            updated["base_address"] = change["base_address"]
            updated["length_bytes"] = change["length_bytes"]
        new_store.append(updated)
    order = [change["parameter_id"] for change in screening["acceptable"]]
    changed.sort(key=lambda item: order.index(item["parameter_id"]))
    return {
        "applied": True,
        "store": new_store,
        "changed": changed,
        "refused": screening["refused"],
        "screening": screening,
    }


def outcome_accounts_for_request(outcome):
    """Check the applied and refused totals against the distinct change count."""
    if not isinstance(outcome, dict):
        raise ValueError("outcome must be a mapping, got %r" % (outcome,))
    screening = outcome.get("screening")
    if not isinstance(screening, dict):
        raise ValueError("outcome carries no screening record")
    applied = len(outcome.get("changed") or [])
    refused = len(outcome.get("refused") or [])
    distinct = screening.get("distinct_count")
    findings = []
    if applied + refused != distinct:
        findings.append(
            "outcome accounts for %d of the %d distinct changes"
            % (applied + refused, distinct)
        )
    reasons = {item["refusal"] for item in (outcome.get("refused") or [])}
    unknown_reasons = reasons - set(REFUSALS)
    if unknown_reasons:
        findings.append(
            "outcome carries refusal reasons outside the declared set: %s"
            % ", ".join(sorted(unknown_reasons))
        )
    return {"accounted": not findings, "findings": findings}


def assess_change_request(parameters, areas, changes):
    """Full clause 6.20.5.2 handling: screening, application, hazards."""
    before = overlap_hazards(parameters)
    outcome = apply_changes(parameters, areas, changes)
    screening = outcome["screening"]
    findings = []
    for key in screening["repeated"]:
        findings.append(
            "parameter %s is changed more than once; the last change wins" % key
        )
    for item in outcome["refused"]:
        findings.append(
            "change to %s refused (%s): %s"
            % (item["parameter_id"], item["refusal"], item["reason"])
        )
    after = overlap_hazards(outcome["store"])
    new_hazards = [pair for pair in after if pair not in before]
    for pair in new_hazards:
        findings.append(
            "parameters %s and %s now address the same memory; the change is "
            "applied and the overlap is a hazard" % pair
        )
    accounting = outcome_accounts_for_request(outcome)
    findings.extend(accounting["findings"])
    if not outcome["applied"]:
        findings.append(
            "no change survived screening; the request fails at start and no "
            "definition is altered"
        )
        verdict = VERDICT_FAILED_START
    elif outcome["refused"]:
        verdict = VERDICT_PARTIAL
    else:
        verdict = VERDICT_APPLIED
    return {
        "verdict": verdict,
        "applied": outcome["applied"],
        "store": outcome["store"],
        "changed": outcome["changed"],
        "changed_ids": [item["parameter_id"] for item in outcome["changed"]],
        "refused": outcome["refused"],
        "refused_ids": [item["parameter_id"] for item in outcome["refused"]],
        "applied_count": len(outcome["changed"]),
        "refused_count": len(outcome["refused"]),
        "overlaps_before": before,
        "overlaps_after": after,
        "new_overlaps": new_hazards,
        "accounted": accounting["accounted"],
        "findings": findings,
    }

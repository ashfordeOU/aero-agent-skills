#!/usr/bin/env python3
"""Change of on-board object memory parameter definitions.

Anchor: ECSS-E-ST-70-41C clause 6.20.5.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An object memory parameter definition binds a parameter identifier to a
place in an on-board memory: the memory it lives in, the bit offset it
starts at and the data type that says how wide it is and how it is
decoded. The service lets the ground re-point those bindings while the
mission runs, which is how a parameter follows a patched software image
instead of being abandoned when the image moves underneath it.

The clause's normative items reduce to seven implementable checks:

    1  every instruction names a parameter the definition store holds;
       an unknown identifier fails that instruction and is reported,
       it is not skipped
    2  a request that names the same parameter twice is malformed,
       because the two instructions would race for one binding
    3  the target object memory has to be one the application declares
    4  the new binding has to lie wholly inside that memory: the start
       offset plus the type width may not run past the memory extent
    5  the start offset has to sit on the memory's alignment unit
    6  a parameter whose definition is fixed cannot be re-pointed, and
       a settable parameter cannot be re-pointed into a memory the
       application exposes read-only
    7  the outcome is per instruction -- accepted, partially accepted
       or rejected -- and the changed store is returned only when it
       is still self-consistent, otherwise the store is left untouched

Standard library only, offline, deterministic.
"""

from __future__ import annotations

MEMORY_ACCESS = ("read-only", "read-write")

PARAMETER_TYPE_WIDTHS = {
    "uint8": 8,
    "int8": 8,
    "uint16": 16,
    "int16": 16,
    "uint32": 32,
    "int32": 32,
    "real32": 32,
    "real64": 64,
}

VERDICT_ACCEPTED = "accepted"
VERDICT_PARTIAL = "partially-accepted"
VERDICT_REJECTED = "rejected"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_integer(name, value, minimum=0):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
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


def type_width_bits(type_name):
    """Width in bits of a declared parameter type."""
    if type_name not in PARAMETER_TYPE_WIDTHS:
        raise ValueError(
            "unknown parameter type %r; declared types are %s"
            % (type_name, ", ".join(sorted(PARAMETER_TYPE_WIDTHS)))
        )
    return PARAMETER_TYPE_WIDTHS[type_name]


def validate_memory(record):
    """Normalize one declared object memory."""
    if not isinstance(record, dict):
        raise ValueError("object memory must be a mapping, got %r" % (record,))
    memory_id = _require_identifier("memory id", record.get("id"))
    size_bits = _require_integer("memory %s size_bits" % memory_id, record.get("size_bits"), 1)
    alignment_bits = _require_integer(
        "memory %s alignment_bits" % memory_id, record.get("alignment_bits", 8), 1
    )
    if size_bits % alignment_bits:
        raise ValueError(
            "memory %s extent %d is not a whole number of %d-bit alignment units"
            % (memory_id, size_bits, alignment_bits)
        )
    return {
        "id": memory_id,
        "size_bits": size_bits,
        "alignment_bits": alignment_bits,
        "access": _require_choice(
            "memory %s access" % memory_id, record.get("access", "read-write"), MEMORY_ACCESS
        ),
    }


def validate_memory_map(memories):
    """Normalize the declared object memories and reject duplicate ids."""
    if not isinstance(memories, (list, tuple)):
        raise ValueError("memories must be a list, got %r" % (memories,))
    memory_map = {}
    for raw in memories:
        record = validate_memory(raw)
        if record["id"] in memory_map:
            raise ValueError("duplicate object memory id %r" % record["id"])
        memory_map[record["id"]] = record
    return memory_map


def validate_parameter_definition(record):
    """Normalize one object memory parameter definition."""
    if not isinstance(record, dict):
        raise ValueError("parameter definition must be a mapping, got %r" % (record,))
    parameter_id = _require_identifier("parameter id", record.get("id"))
    type_name = _require_identifier(
        "parameter %s type" % parameter_id, record.get("type")
    )
    width = type_width_bits(type_name)
    return {
        "id": parameter_id,
        "memory_id": _require_identifier(
            "parameter %s memory_id" % parameter_id, record.get("memory_id")
        ),
        "offset_bits": _require_integer(
            "parameter %s offset_bits" % parameter_id, record.get("offset_bits"), 0
        ),
        "type": type_name,
        "width_bits": width,
        "redefinable": _require_bool(
            "parameter %s redefinable" % parameter_id, record.get("redefinable", True)
        ),
        "settable": _require_bool(
            "parameter %s settable" % parameter_id, record.get("settable", False)
        ),
    }


def validate_definition_store(definitions):
    """Normalize the definition store and reject duplicate parameter ids."""
    if not isinstance(definitions, (list, tuple)):
        raise ValueError("definitions must be a list, got %r" % (definitions,))
    store = []
    seen = set()
    for raw in definitions:
        record = validate_parameter_definition(raw)
        if record["id"] in seen:
            raise ValueError("duplicate parameter definition id %r" % record["id"])
        seen.add(record["id"])
        store.append(record)
    return store


def binding_findings(memory, offset_bits, width_bits, owner):
    """Extent and alignment findings for one candidate binding."""
    findings = []
    if offset_bits % memory["alignment_bits"]:
        findings.append(
            "%s starts at bit %d, which is off the %d-bit alignment unit of memory %s"
            % (owner, offset_bits, memory["alignment_bits"], memory["id"])
        )
    if offset_bits + width_bits > memory["size_bits"]:
        findings.append(
            "%s needs bits %d..%d but memory %s ends at bit %d"
            % (
                owner,
                offset_bits,
                offset_bits + width_bits,
                memory["id"],
                memory["size_bits"],
            )
        )
    return findings


def validate_change_instruction(record):
    """Normalize one re-pointing instruction from the change request."""
    if not isinstance(record, dict):
        raise ValueError("change instruction must be a mapping, got %r" % (record,))
    parameter_id = _require_identifier(
        "instruction parameter_id", record.get("parameter_id")
    )
    instruction = {
        "parameter_id": parameter_id,
        "memory_id": _require_identifier(
            "instruction %s memory_id" % parameter_id, record.get("memory_id")
        ),
        "offset_bits": _require_integer(
            "instruction %s offset_bits" % parameter_id, record.get("offset_bits"), 0
        ),
        "type": None,
    }
    if record.get("type") is not None:
        type_name = _require_identifier(
            "instruction %s type" % parameter_id, record.get("type")
        )
        type_width_bits(type_name)
        instruction["type"] = type_name
    return instruction


def validate_change_request(request):
    """Normalize a change request into an ordered instruction list."""
    if isinstance(request, dict):
        request = request.get("instructions")
    if not isinstance(request, (list, tuple)):
        raise ValueError("change request instructions must be a list, got %r" % (request,))
    if not request:
        raise ValueError("a change request has to carry at least one instruction")
    instructions = []
    seen = set()
    for raw in request:
        instruction = validate_change_instruction(raw)
        if instruction["parameter_id"] in seen:
            raise ValueError(
                "change request names parameter %r twice" % instruction["parameter_id"]
            )
        seen.add(instruction["parameter_id"])
        instructions.append(instruction)
    return instructions


def assess_change_instruction(instruction, store_by_id, memory_map):
    """Decide one instruction against the store and the declared memories."""
    parameter_id = instruction["parameter_id"]
    owner = "parameter %s" % parameter_id
    findings = []
    current = store_by_id.get(parameter_id)
    if current is None:
        return {
            "parameter_id": parameter_id,
            "accepted": False,
            "findings": ["%s is not held in the definition store" % owner],
            "definition": None,
        }
    if not current["redefinable"]:
        findings.append("%s carries a fixed definition and cannot be re-pointed" % owner)
    memory = memory_map.get(instruction["memory_id"])
    if memory is None:
        findings.append(
            "%s targets object memory %r, which the application does not declare"
            % (owner, instruction["memory_id"])
        )
    else:
        if current["settable"] and memory["access"] == "read-only":
            findings.append(
                "%s is settable and cannot live in read-only memory %s"
                % (owner, memory["id"])
            )
        type_name = instruction["type"] or current["type"]
        findings.extend(
            binding_findings(
                memory, instruction["offset_bits"], type_width_bits(type_name), owner
            )
        )
    if findings:
        return {
            "parameter_id": parameter_id,
            "accepted": False,
            "findings": findings,
            "definition": None,
        }
    type_name = instruction["type"] or current["type"]
    changed = dict(current)
    changed["memory_id"] = instruction["memory_id"]
    changed["offset_bits"] = instruction["offset_bits"]
    changed["type"] = type_name
    changed["width_bits"] = type_width_bits(type_name)
    return {
        "parameter_id": parameter_id,
        "accepted": True,
        "findings": [],
        "definition": changed,
    }


def store_is_consistent(store, memory_map):
    """Re-check a whole store: unique ids, declared memory, in-extent, aligned."""
    findings = []
    seen = set()
    for record in store:
        if record["id"] in seen:
            findings.append("store holds parameter %r twice" % record["id"])
        seen.add(record["id"])
        memory = memory_map.get(record["memory_id"])
        if memory is None:
            findings.append(
                "parameter %s sits in undeclared memory %r"
                % (record["id"], record["memory_id"])
            )
            continue
        findings.extend(
            binding_findings(
                memory,
                record["offset_bits"],
                record["width_bits"],
                "parameter %s" % record["id"],
            )
        )
    return {"consistent": not findings, "findings": findings}


def apply_definition_change(definitions, memories, request):
    """Full clause 6.20.5.3 handling: verdict plus the resulting store."""
    store = validate_definition_store(definitions)
    memory_map = validate_memory_map(memories)
    baseline = store_is_consistent(store, memory_map)
    if not baseline["consistent"]:
        raise ValueError(
            "the definition store is already inconsistent: %s"
            % "; ".join(baseline["findings"])
        )
    instructions = validate_change_request(request)
    store_by_id = {record["id"]: record for record in store}
    outcomes = [
        assess_change_instruction(instruction, store_by_id, memory_map)
        for instruction in instructions
    ]
    applied = [o["parameter_id"] for o in outcomes if o["accepted"]]
    refused = [o["parameter_id"] for o in outcomes if not o["accepted"]]
    findings = []
    for outcome in outcomes:
        findings.extend(outcome["findings"])
    changed_by_id = {o["parameter_id"]: o["definition"] for o in outcomes if o["accepted"]}
    candidate = [changed_by_id.get(record["id"], record) for record in store]
    consistency = store_is_consistent(candidate, memory_map)
    if not consistency["consistent"]:
        findings.extend(consistency["findings"])
        return {
            "verdict": VERDICT_REJECTED,
            "applied": [],
            "refused": [o["parameter_id"] for o in outcomes],
            "outcomes": outcomes,
            "store": store,
            "store_changed": False,
            "findings": findings,
        }
    if applied and refused:
        verdict = VERDICT_PARTIAL
    elif applied:
        verdict = VERDICT_ACCEPTED
    else:
        verdict = VERDICT_REJECTED
    return {
        "verdict": verdict,
        "applied": applied,
        "refused": refused,
        "outcomes": outcomes,
        "store": candidate if applied else store,
        "store_changed": bool(applied),
        "findings": findings,
    }

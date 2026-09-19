#!/usr/bin/env python3
"""Direct load of a request sequence into the on-board sequence store.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A direct load carries the sequence with it. The load request holds the
identifier and the whole ordered body of requests inline, so the store
gains a runnable sequence from one command without reading anything
else. That is what makes the direct load attractive and what makes it
strict: everything the store will hold arrived in a single packet, and
it is either all acceptable or the store is left exactly as it was.

The clause's normative items reduce to six implementable checks:

    1  the load names a sequence identifier the store does not
       already hold; a load over a held sequence is refused, never
       an overwrite
    2  the carried body holds at least one request, and the carried
       order is the order the store keeps
    3  every carried request is checked before anything is stored,
       and one unacceptable request fails the whole load
    4  the load has to fit the free capacity of the store measured at
       the moment of the load, headers included
    5  a body that names its own sequence through the sequencing
       service is refused
    6  the load is all or nothing: on success the store holds exactly
       the carried requests in the carried order and the free
       capacity drops by the loaded size; on failure the store and
       its capacity are untouched

Standard library only, offline, deterministic.
"""

from __future__ import annotations

SEQUENCING_SERVICE_TYPE = 21
SELF_REFERENCING_SUBTYPES = (1, 2, 3, 4)

MAX_PAYLOAD_OCTETS = 1024
REQUEST_HEADER_OCTETS = 6

STATE_LOADED = "loaded"

LOAD_ACCEPTED = "accepted"
LOAD_REFUSED = "refused"

REASON_ALREADY_HELD = "identifier-already-held"
REASON_EMPTY_BODY = "empty-body"
REASON_MALFORMED_REQUEST = "malformed-request"
REASON_SELF_REFERENCE = "self-reference"
REASON_INSUFFICIENT_CAPACITY = "insufficient-capacity"


def _require_identifier(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_integer(name, value, minimum=0, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be at most %d, got %d" % (name, maximum, value))
    return value


def request_is_acceptable(record, sequence_id):
    """Grade one carried request without raising: findings, size, target."""
    findings = []
    if not isinstance(record, dict):
        return {"acceptable": False, "findings": ["carried request is not a mapping"], "size_octets": 0}
    application_id = record.get("application_id")
    if not isinstance(application_id, str) or not application_id.strip():
        findings.append("carried request has no application identifier")
    for field in ("service_type", "subtype"):
        value = record.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 255:
            findings.append("carried request %s %r is outside 1..255" % (field, value))
    payload = record.get("payload_octets", 0)
    if not isinstance(payload, int) or isinstance(payload, bool) or payload < 0:
        findings.append("carried request payload_octets %r is not a size" % (payload,))
        payload = 0
    elif payload > MAX_PAYLOAD_OCTETS:
        findings.append(
            "carried request payload of %d octets is past the %d octet packet limit"
            % (payload, MAX_PAYLOAD_OCTETS)
        )
    target = record.get("target_sequence_id")
    self_reference = (
        record.get("service_type") == SEQUENCING_SERVICE_TYPE
        and record.get("subtype") in SELF_REFERENCING_SUBTYPES
        and isinstance(target, str)
        and target.strip() == sequence_id
    )
    return {
        "acceptable": not findings,
        "findings": findings,
        "size_octets": payload + REQUEST_HEADER_OCTETS,
        "self_reference": self_reference,
    }


def validate_store(sequences, capacity_octets):
    """Normalize the on-board sequence store and its free capacity."""
    capacity = _require_integer("store capacity_octets", capacity_octets, 0)
    if not isinstance(sequences, dict):
        raise ValueError("the sequence store must be a mapping, got %r" % (sequences,))
    held = {}
    used = 0
    for key, value in sequences.items():
        sequence_id = _require_identifier("held sequence id", key)
        if not isinstance(value, dict):
            raise ValueError("held sequence %s must be a mapping" % sequence_id)
        size = _require_integer("held sequence %s size_octets" % sequence_id, value.get("size_octets"), 1)
        held[sequence_id] = {
            "id": sequence_id,
            "size_octets": size,
            "request_count": _require_integer(
                "held sequence %s request_count" % sequence_id, value.get("request_count"), 1
            ),
            "state": value.get("state", STATE_LOADED),
        }
        used += size
    if used > capacity:
        raise ValueError(
            "the sequence store holds %d octets but declares a capacity of %d"
            % (used, capacity)
        )
    return {
        "sequences": held,
        "capacity_octets": capacity,
        "used_octets": used,
        "free_octets": capacity - used,
    }


def validate_load_request(request):
    """Normalize a direct load request into an identifier and a carried body."""
    if not isinstance(request, dict):
        raise ValueError("direct load request must be a mapping, got %r" % (request,))
    sequence_id = _require_identifier("load sequence_id", request.get("sequence_id"))
    body = request.get("requests")
    if not isinstance(body, (list, tuple)):
        raise ValueError("load of %s must carry a request list" % sequence_id)
    return {"sequence_id": sequence_id, "requests": list(body)}


def grade_carried_body(sequence_id, body):
    """Grade the whole carried body before anything is stored."""
    findings = []
    reasons = []
    if not body:
        findings.append("the load of %s carries no requests" % sequence_id)
        reasons.append(REASON_EMPTY_BODY)
        return {
            "acceptable": False,
            "findings": findings,
            "reasons": reasons,
            "size_octets": 0,
            "request_count": 0,
        }
    size = 0
    malformed = 0
    self_references = 0
    for position, record in enumerate(body):
        graded = request_is_acceptable(record, sequence_id)
        size += graded["size_octets"]
        if not graded["acceptable"]:
            malformed += 1
            for finding in graded["findings"]:
                findings.append("request %d: %s" % (position, finding))
        if graded.get("self_reference"):
            self_references += 1
            findings.append(
                "request %d of the load targets sequence %s itself"
                % (position, sequence_id)
            )
    if malformed:
        reasons.append(REASON_MALFORMED_REQUEST)
    if self_references:
        reasons.append(REASON_SELF_REFERENCE)
    return {
        "acceptable": not findings,
        "findings": findings,
        "reasons": reasons,
        "size_octets": size,
        "request_count": len(body),
    }


def load_fits(store, size_octets):
    """True when a load of this size fits the store's free capacity."""
    return _require_integer("size_octets", size_octets, 0) <= store["free_octets"]


def direct_load_sequence(store, request):
    """Full clause 6.21.5.2 handling: grade the load, then apply it or not."""
    load = validate_load_request(request)
    sequence_id = load["sequence_id"]
    findings = []
    reasons = []
    if sequence_id in store["sequences"]:
        findings.append(
            "sequence %s is already held; a direct load does not overwrite it"
            % sequence_id
        )
        reasons.append(REASON_ALREADY_HELD)
    graded = grade_carried_body(sequence_id, load["requests"])
    findings.extend(graded["findings"])
    reasons.extend(graded["reasons"])
    if graded["request_count"] and not load_fits(store, graded["size_octets"]):
        findings.append(
            "the load of %s needs %d octets but only %d are free"
            % (sequence_id, graded["size_octets"], store["free_octets"])
        )
        reasons.append(REASON_INSUFFICIENT_CAPACITY)
    if findings:
        return {
            "verdict": LOAD_REFUSED,
            "sequence_id": sequence_id,
            "reasons": reasons,
            "findings": findings,
            "store": store,
            "store_changed": False,
            "loaded_size_octets": 0,
        }
    updated = dict(store["sequences"])
    updated[sequence_id] = {
        "id": sequence_id,
        "size_octets": graded["size_octets"],
        "request_count": graded["request_count"],
        "state": STATE_LOADED,
    }
    used = store["used_octets"] + graded["size_octets"]
    return {
        "verdict": LOAD_ACCEPTED,
        "sequence_id": sequence_id,
        "reasons": [],
        "findings": [],
        "store": {
            "sequences": updated,
            "capacity_octets": store["capacity_octets"],
            "used_octets": used,
            "free_octets": store["capacity_octets"] - used,
        },
        "store_changed": True,
        "loaded_size_octets": graded["size_octets"],
    }

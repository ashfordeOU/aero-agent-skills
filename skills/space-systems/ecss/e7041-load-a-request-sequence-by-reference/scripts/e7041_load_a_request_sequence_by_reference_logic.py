#!/usr/bin/env python3
"""Load of a request sequence by reference to on-board held content.

Anchor: ECSS-E-ST-70-41C clause 6.21.5.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A load by reference carries a pointer, not a body. The command names
the sequence to create and a source the on-board system already holds
-- a repository entry uplinked earlier, for instance -- and the
application reads the sequence out of that source itself. The command
is small and the same source can be loaded again after an unload, but
everything the direct load could check on arrival now has to be
checked after the reference resolves.

The clause's normative items reduce to six implementable checks:

    1  the reference has to resolve to a source the system holds and
       can read; a dangling or unreadable reference fails the load
    2  the reference has to resolve to exactly one source; an
       ambiguous reference is refused rather than resolved by a rule
       the ground cannot see
    3  the resolved content is graded exactly as a directly carried
       body would be: at least one request, each one acceptable
       standing alone, and none targeting the sequence being loaded
    4  the sequence identifier must not already be held in the store
    5  the capacity check uses the size of the resolved content, not
       any size declared alongside the reference
    6  the load is all or nothing, and a loaded sequence records the
       source it came from so a later reload can be told apart from
       a direct load

Standard library only, offline, deterministic.
"""

from __future__ import annotations

SEQUENCING_SERVICE_TYPE = 21
SELF_REFERENCING_SUBTYPES = (1, 2, 3, 4)

MAX_PAYLOAD_OCTETS = 1024
REQUEST_HEADER_OCTETS = 6

STATE_LOADED = "loaded"

ORIGIN_BY_REFERENCE = "by-reference"

LOAD_ACCEPTED = "accepted"
LOAD_REFUSED = "refused"

REASON_UNRESOLVED_REFERENCE = "unresolved-reference"
REASON_AMBIGUOUS_REFERENCE = "ambiguous-reference"
REASON_UNREADABLE_SOURCE = "unreadable-source"
REASON_EMPTY_CONTENT = "empty-content"
REASON_MALFORMED_REQUEST = "malformed-request"
REASON_SELF_REFERENCE = "self-reference"
REASON_ALREADY_HELD = "identifier-already-held"
REASON_INSUFFICIENT_CAPACITY = "insufficient-capacity"


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


def validate_repository(entries):
    """Normalize the on-board content repository the reference points into."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("the repository must be a list, got %r" % (entries,))
    sources = []
    for index, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise ValueError("repository entry %d must be a mapping" % index)
        reference = _require_identifier("repository entry %d reference" % index, raw.get("reference"))
        content = raw.get("content")
        if content is not None and not isinstance(content, (list, tuple)):
            raise ValueError("repository entry %s content must be a list" % reference)
        readable = raw.get("readable", True)
        if not isinstance(readable, bool):
            raise ValueError("repository entry %s readable must be a boolean" % reference)
        sources.append(
            {
                "reference": reference,
                "content": list(content) if content is not None else None,
                "readable": readable,
            }
        )
    return sources


def resolve_reference(repository, reference):
    """Resolve a reference to exactly one readable source, or say why not."""
    wanted = _require_identifier("load reference", reference)
    sources = validate_repository(repository)
    matches = [source for source in sources if source["reference"] == wanted]
    if not matches:
        return {
            "resolved": False,
            "reason": REASON_UNRESOLVED_REFERENCE,
            "finding": "reference %r resolves to nothing the system holds" % wanted,
            "source": None,
            "match_count": 0,
        }
    if len(matches) > 1:
        return {
            "resolved": False,
            "reason": REASON_AMBIGUOUS_REFERENCE,
            "finding": "reference %r resolves to %d sources" % (wanted, len(matches)),
            "source": None,
            "match_count": len(matches),
        }
    source = matches[0]
    if not source["readable"] or source["content"] is None:
        return {
            "resolved": False,
            "reason": REASON_UNREADABLE_SOURCE,
            "finding": "source %r cannot be read out" % wanted,
            "source": None,
            "match_count": 1,
        }
    return {
        "resolved": True,
        "reason": None,
        "finding": None,
        "source": source,
        "match_count": 1,
    }


def request_is_acceptable(record, sequence_id):
    """Grade one resolved request without raising: findings, size, target."""
    if not isinstance(record, dict):
        return {
            "acceptable": False,
            "findings": ["resolved request is not a mapping"],
            "size_octets": 0,
            "self_reference": False,
        }
    findings = []
    application_id = record.get("application_id")
    if not isinstance(application_id, str) or not application_id.strip():
        findings.append("resolved request has no application identifier")
    for field in ("service_type", "subtype"):
        value = record.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 255:
            findings.append("resolved request %s %r is outside 1..255" % (field, value))
    payload = record.get("payload_octets", 0)
    if not isinstance(payload, int) or isinstance(payload, bool) or payload < 0:
        findings.append("resolved request payload_octets %r is not a size" % (payload,))
        payload = 0
    elif payload > MAX_PAYLOAD_OCTETS:
        findings.append(
            "resolved request payload of %d octets is past the %d octet packet limit"
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


def grade_resolved_content(sequence_id, content):
    """Grade resolved content exactly as a directly carried body would be."""
    findings = []
    reasons = []
    if not content:
        return {
            "acceptable": False,
            "findings": ["source for %s resolved to no requests" % sequence_id],
            "reasons": [REASON_EMPTY_CONTENT],
            "size_octets": 0,
            "request_count": 0,
        }
    size = 0
    malformed = 0
    self_references = 0
    for position, record in enumerate(content):
        graded = request_is_acceptable(record, sequence_id)
        size += graded["size_octets"]
        if not graded["acceptable"]:
            malformed += 1
            for finding in graded["findings"]:
                findings.append("request %d: %s" % (position, finding))
        if graded["self_reference"]:
            self_references += 1
            findings.append(
                "request %d of the resolved content targets sequence %s itself"
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
        "request_count": len(content),
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
            "origin": value.get("origin"),
            "source_reference": value.get("source_reference"),
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
    """Normalize a load-by-reference request."""
    if not isinstance(request, dict):
        raise ValueError("load request must be a mapping, got %r" % (request,))
    return {
        "sequence_id": _require_identifier("load sequence_id", request.get("sequence_id")),
        "reference": _require_identifier("load reference", request.get("reference")),
        "declared_size_octets": (
            _require_integer("load declared_size_octets", request.get("declared_size_octets"), 0)
            if request.get("declared_size_octets") is not None
            else None
        ),
    }


def load_fits(store, size_octets):
    """True when content of this size fits the store's free capacity."""
    return _require_integer("size_octets", size_octets, 0) <= store["free_octets"]


def load_sequence_by_reference(store, repository, request):
    """Full clause 6.21.5.3 handling: resolve, grade, then apply or not."""
    load = validate_load_request(request)
    sequence_id = load["sequence_id"]
    findings = []
    reasons = []
    if sequence_id in store["sequences"]:
        findings.append(
            "sequence %s is already held; a load by reference does not overwrite it"
            % sequence_id
        )
        reasons.append(REASON_ALREADY_HELD)
    resolution = resolve_reference(repository, load["reference"])
    if not resolution["resolved"]:
        findings.append(resolution["finding"])
        reasons.append(resolution["reason"])
        return {
            "verdict": LOAD_REFUSED,
            "sequence_id": sequence_id,
            "reference": load["reference"],
            "resolved": False,
            "reasons": reasons,
            "findings": findings,
            "store": store,
            "store_changed": False,
            "loaded_size_octets": 0,
        }
    graded = grade_resolved_content(sequence_id, resolution["source"]["content"])
    findings.extend(graded["findings"])
    reasons.extend(graded["reasons"])
    if graded["request_count"] and not load_fits(store, graded["size_octets"]):
        findings.append(
            "the resolved content for %s needs %d octets but only %d are free"
            % (sequence_id, graded["size_octets"], store["free_octets"])
        )
        reasons.append(REASON_INSUFFICIENT_CAPACITY)
    if findings:
        return {
            "verdict": LOAD_REFUSED,
            "sequence_id": sequence_id,
            "reference": load["reference"],
            "resolved": True,
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
        "origin": ORIGIN_BY_REFERENCE,
        "source_reference": load["reference"],
    }
    used = store["used_octets"] + graded["size_octets"]
    return {
        "verdict": LOAD_ACCEPTED,
        "sequence_id": sequence_id,
        "reference": load["reference"],
        "resolved": True,
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

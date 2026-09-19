#!/usr/bin/env python3
"""Checksum one stored request sequence and report the result.

Anchor: ECSS-E-ST-70-41C clause 6.21.7. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A request sequence can sit in the store for months between being
uplinked and being activated, and the store is memory like any other.
This request is how the ground finds out whether the body it uplinked
is still the body that would run. It is worth nothing unless it reads
the stored body, on the stored side, in stored order -- every shortcut
past that turns the check into a check of something already known.

The clause's normative items reduce to seven implementable checks:

    1  the request names a sequence the store holds; an unknown
       identifier is refused rather than checksummed as empty
    2  the checksum is computed over the stored body, in stored
       order, and not over the source the ground still has
    3  an empty sequence or one still under load cannot be
       checksummed; a partial body has no meaningful checksum
    4  the algorithm is one the store declares; an unknown algorithm
       is refused rather than silently substituted
    5  the report carries the identifier, the body length in octets
       and the computed value
    6  a declared checksum that disagrees with the computed one is a
       corruption finding; the declared value is never re-reported as
       though it had been verified
    7  checksumming changes no sequence state, so a sequence that is
       executing can be checksummed while it runs

Two algorithms are implemented here from their definitions: a CCITT
16-bit cyclic redundancy check and an 8-bit modular checksum whose
value completes the octet sum to zero.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

LOAD_STATES = ("empty", "under-load", "loaded")

EXECUTION_STATES = ("inactive", "executing", "aborted", "completed")

ALGORITHM_CRC16 = "crc-16-ccitt"
ALGORITHM_ISO8 = "iso-checksum-8"

ALGORITHMS = (ALGORITHM_CRC16, ALGORITHM_ISO8)

CRC16_POLYNOMIAL = 0x1021
CRC16_SEED = 0xFFFF

REFUSAL_UNKNOWN_SEQUENCE = "unknown-sequence-identifier"
REFUSAL_EMPTY_SEQUENCE = "empty-sequence-body"
REFUSAL_UNDER_LOAD = "sequence-still-under-load"
REFUSAL_UNKNOWN_ALGORITHM = "unknown-checksum-algorithm"

REFUSAL_CODES = (
    REFUSAL_UNKNOWN_SEQUENCE,
    REFUSAL_EMPTY_SEQUENCE,
    REFUSAL_UNDER_LOAD,
    REFUSAL_UNKNOWN_ALGORITHM,
)

VERDICT_INTACT = "sequence-body-intact"
VERDICT_CORRUPT = "sequence-body-corrupt"
VERDICT_UNVERIFIED = "sequence-body-unverified"
VERDICT_REFUSED = "checksum-refused"


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


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def crc16_ccitt(octets, seed=CRC16_SEED):
    """CCITT 16-bit cyclic redundancy check over a run of octets."""
    crc = seed & 0xFFFF
    for octet in octets:
        if not isinstance(octet, int) or isinstance(octet, bool):
            raise ValueError("octet must be an integer, got %r" % (octet,))
        if not 0 <= octet <= 255:
            raise ValueError("octet must be in 0..255, got %d" % octet)
        crc ^= (octet & 0xFF) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ CRC16_POLYNOMIAL) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def iso_checksum_8(octets):
    """8-bit modular checksum: the value that completes the sum to zero."""
    total = 0
    for octet in octets:
        if not isinstance(octet, int) or isinstance(octet, bool):
            raise ValueError("octet must be an integer, got %r" % (octet,))
        if not 0 <= octet <= 255:
            raise ValueError("octet must be in 0..255, got %d" % octet)
        total = (total + octet) & 0xFF
    return (0x100 - total) & 0xFF


def compute_over_octets(octets, algorithm):
    """Run the named algorithm over a run of octets."""
    name = _require_choice("algorithm", algorithm, ALGORITHMS)
    if name == ALGORITHM_CRC16:
        return crc16_ccitt(octets)
    return iso_checksum_8(octets)


def validate_request_record(record, owner, expected_index):
    """Normalize one request inside a stored sequence body."""
    if not isinstance(record, dict):
        raise ValueError("request of %s must be a mapping, got %r" % (owner, record))
    index = _require_positive_integer(
        "request index of %s" % owner, record.get("index")
    )
    if index != expected_index:
        raise ValueError(
            "sequence %s stores request index %d where %d was expected; the "
            "body is not in stored order" % (owner, index, expected_index)
        )
    octets = record.get("octets")
    if not isinstance(octets, (list, tuple)):
        raise ValueError(
            "request %d of %s must carry an octet list" % (index, owner)
        )
    if not octets:
        raise ValueError("request %d of %s carries no octets" % (index, owner))
    cleaned = []
    for octet in octets:
        if not isinstance(octet, int) or isinstance(octet, bool):
            raise ValueError(
                "request %d of %s carries a non-integer octet %r"
                % (index, owner, octet)
            )
        if not 0 <= octet <= 255:
            raise ValueError(
                "request %d of %s carries octet %d outside 0..255"
                % (index, owner, octet)
            )
        cleaned.append(octet)
    return {"index": index, "octets": tuple(cleaned)}


def validate_sequence(record):
    """Normalize one stored request sequence and its body."""
    if not isinstance(record, dict):
        raise ValueError("sequence must be a mapping, got %r" % (record,))
    sequence_id = _require_identifier("sequence id", record.get("id"))
    load_state = _require_choice(
        "sequence %s load_state" % sequence_id, record.get("load_state"), LOAD_STATES
    )
    execution_state = _require_choice(
        "sequence %s execution_state" % sequence_id,
        record.get("execution_state"),
        EXECUTION_STATES,
    )
    raw = record.get("body")
    if not isinstance(raw, (list, tuple)):
        raise ValueError("sequence %s body must be a list" % sequence_id)
    body = []
    for position, item in enumerate(raw):
        body.append(validate_request_record(item, sequence_id, position + 1))
    if load_state == "empty" and body:
        raise ValueError(
            "sequence %s is marked empty but carries %d requests"
            % (sequence_id, len(body))
        )
    if load_state == "loaded" and not body:
        raise ValueError(
            "sequence %s is marked loaded but carries no requests" % sequence_id
        )
    if execution_state == "executing" and load_state != "loaded":
        raise ValueError(
            "sequence %s is executing while its load state is %r"
            % (sequence_id, load_state)
        )
    normalized = {
        "id": sequence_id,
        "load_state": load_state,
        "execution_state": execution_state,
        "body": body,
        "request_count": len(body),
    }
    declared = record.get("declared_checksum")
    if declared is not None:
        if not isinstance(declared, int) or isinstance(declared, bool):
            raise ValueError(
                "sequence %s declared_checksum must be an integer, got %r"
                % (sequence_id, declared)
            )
        if declared < 0:
            raise ValueError(
                "sequence %s declared_checksum must not be negative" % sequence_id
            )
        normalized["declared_checksum"] = declared
    return normalized


def validate_store(sequences):
    """Normalize the sequence store and refuse a duplicate identifier."""
    if not isinstance(sequences, (list, tuple)):
        raise ValueError("sequences must be a list, got %r" % (sequences,))
    store = []
    seen = set()
    for raw in sequences:
        record = validate_sequence(raw)
        if record["id"] in seen:
            raise ValueError("duplicate sequence identifier %r" % record["id"])
        seen.add(record["id"])
        store.append(record)
    return store


def find_sequence(store, sequence_id):
    """Return the normalized sequence with this identifier, or None."""
    wanted = _require_identifier("requested sequence id", sequence_id)
    for record in validate_store(store):
        if record["id"] == wanted:
            return record
    return None


def body_octets(record):
    """The stored body flattened into one run of octets, in stored order."""
    sequence = validate_sequence(record)
    octets = []
    for request in sequence["body"]:
        octets.extend(request["octets"])
    return tuple(octets)


def compute_sequence_checksum(record, algorithm):
    """Checksum the stored body of one sequence with the named algorithm."""
    octets = body_octets(record)
    if not octets:
        raise ValueError(
            "sequence %s carries no octets to checksum" % validate_sequence(record)["id"]
        )
    return compute_over_octets(octets, algorithm)


def checksum_refusals(store, sequence_id, algorithm):
    """Every reason this checksum request must be refused."""
    records = validate_store(store)
    wanted = _require_identifier("requested sequence id", sequence_id)
    refusals = []
    if algorithm not in ALGORITHMS:
        refusals.append(
            {
                "code": REFUSAL_UNKNOWN_ALGORITHM,
                "sequence_id": wanted,
                "detail": "the store declares %s, not %r"
                % (" and ".join(ALGORITHMS), algorithm),
            }
        )
    target = None
    for record in records:
        if record["id"] == wanted:
            target = record
            break
    if target is None:
        refusals.append(
            {
                "code": REFUSAL_UNKNOWN_SEQUENCE,
                "sequence_id": wanted,
                "detail": "the store holds no sequence %r" % wanted,
            }
        )
        return refusals
    if target["load_state"] == "under-load":
        refusals.append(
            {
                "code": REFUSAL_UNDER_LOAD,
                "sequence_id": wanted,
                "detail": "sequence %s is still under load and its body is "
                "incomplete" % wanted,
            }
        )
    elif target["request_count"] == 0:
        refusals.append(
            {
                "code": REFUSAL_EMPTY_SEQUENCE,
                "sequence_id": wanted,
                "detail": "sequence %s carries no requests to checksum" % wanted,
            }
        )
    return refusals


def checksum_report(store, sequence_id, algorithm):
    """The report the ground receives for one accepted checksum request."""
    target = find_sequence(store, sequence_id)
    if target is None:
        raise ValueError("cannot checksum absent sequence %r" % (sequence_id,))
    octets = body_octets(target)
    return {
        "sequence_id": target["id"],
        "algorithm": _require_choice("algorithm", algorithm, ALGORITHMS),
        "request_count": target["request_count"],
        "octet_count": len(octets),
        "checksum": compute_over_octets(octets, algorithm),
    }


def assess_checksum(store, sequence_id, algorithm):
    """Full clause 6.21.7 handling for one checksum request."""
    records = validate_store(store)
    refusals = checksum_refusals(store, sequence_id, algorithm)
    wanted = _require_identifier("requested sequence id", sequence_id)
    result = {
        "sequence_id": wanted,
        "accepted": not refusals,
        "refusals": refusals,
        "refusal_codes": [item["code"] for item in refusals],
        "report": None,
        "notification": None,
        "state_unchanged": True,
        "resulting_store": records,
        "findings": [item["detail"] for item in refusals],
    }
    if refusals:
        result["verdict"] = VERDICT_REFUSED
        result["notification"] = {
            "sequence_id": wanted,
            "codes": [item["code"] for item in refusals],
            "detail": "; ".join(item["detail"] for item in refusals),
        }
        return result
    target = find_sequence(store, wanted)
    report = checksum_report(store, wanted, algorithm)
    result["report"] = report
    declared = target.get("declared_checksum")
    result["declared_checksum"] = declared
    result["computed_checksum"] = report["checksum"]
    if declared is None:
        result["verdict"] = VERDICT_UNVERIFIED
        result["findings"].append(
            "sequence %s carries no declared checksum, so the computed value "
            "records the body rather than verifying it" % wanted
        )
    elif declared != report["checksum"]:
        result["verdict"] = VERDICT_CORRUPT
        result["findings"].append(
            "sequence %s declares checksum %d but its stored body computes %d"
            % (wanted, declared, report["checksum"])
        )
    else:
        result["verdict"] = VERDICT_INTACT
    return result

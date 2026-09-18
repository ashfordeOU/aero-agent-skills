#!/usr/bin/env python3
"""Reserved field of a packet transfer protocol data unit.

Anchor: ECSS-E-ST-50-53C clause 5.3.4. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

One octet sits between the protocol identifier and the user application
field, held back for a later revision of the protocol. A sender has no
freedom here: it writes the reserved pattern, which is all zero bits. A
receiver has a policy choice, and that choice is what this module makes
explicit.

Receiver policies
    strict-discard      a non-reserved octet fails the unit outright
    record-and-accept   the unit is delivered and the deviation logged
    silent-accept       the octet is ignored, nothing is recorded

strict-discard is the safe reading of a reserved field today and the
one that breaks first when a later revision starts using the octet;
record-and-accept keeps a link alive across a revision boundary while
leaving evidence. silent-accept leaves no evidence at all, which is why
it is reported as a policy finding in its own right.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

OCTET_MAX = 255
RESERVED_PATTERN = 0

SENDER = "sender"
RECEIVER = "receiver"
ROLES = (SENDER, RECEIVER)

STRICT_DISCARD = "strict-discard"
RECORD_AND_ACCEPT = "record-and-accept"
SILENT_ACCEPT = "silent-accept"
RECEIVER_POLICIES = (STRICT_DISCARD, RECORD_AND_ACCEPT, SILENT_ACCEPT)

ACCEPT = "accept-unit"
ACCEPT_WITH_RECORD = "accept-unit-and-record"
DISCARD = "discard-unit"
SENDER_DEFECT = "sender-must-rewrite-field"


def _require_octet(name, value):
    """One unsigned octet, rejecting bools and anything out of range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    if value < 0 or value > OCTET_MAX:
        raise ValueError("%s must lie in 0..%d, got %d" % (name, OCTET_MAX, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def reserved_field_offset(path_length):
    """Index of the reserved octet for a unit with this many path bytes."""
    if isinstance(path_length, bool) or not isinstance(path_length, int):
        raise ValueError("path_length must be an integer, got %r" % (path_length,))
    if path_length < 0:
        raise ValueError("path_length must not be negative, got %d" % path_length)
    return path_length + 2


def encode_reserved_field():
    """The single octet a sender writes into the reserved field."""
    return (RESERVED_PATTERN,)


def is_reserved_pattern(value):
    """True where the octet carries the held-back pattern."""
    return _require_octet("reserved octet", value) == RESERVED_PATTERN


def validate_reserved_field(value):
    """Grade one reserved octet without yet applying a disposition."""
    conformant = is_reserved_pattern(value)
    findings = []
    if not conformant:
        findings.append(
            "reserved octet carries %d rather than the held-back pattern %d; "
            "either the sender is non-conformant or the peer already uses a "
            "later revision of the field" % (value, RESERVED_PATTERN)
        )
    return {
        "value": value,
        "conformant": conformant,
        "findings": findings,
    }


def assess_reserved_octet(value, role, policy=STRICT_DISCARD):
    """Decide what a sender or a receiver does with this octet."""
    _require_choice("role", role, ROLES)
    _require_choice("policy", policy, RECEIVER_POLICIES)
    graded = validate_reserved_field(value)
    findings = list(graded["findings"])
    if role == SENDER:
        disposition = ACCEPT if graded["conformant"] else SENDER_DEFECT
        if not graded["conformant"]:
            findings.append(
                "a sender has no freedom in this field; rewrite it to %d "
                "before transmission" % RESERVED_PATTERN
            )
        return {
            "value": value,
            "role": role,
            "policy": policy,
            "conformant": graded["conformant"],
            "disposition": disposition,
            "findings": findings,
        }
    if graded["conformant"]:
        disposition = ACCEPT
    elif policy == STRICT_DISCARD:
        disposition = DISCARD
    elif policy == RECORD_AND_ACCEPT:
        disposition = ACCEPT_WITH_RECORD
    else:
        disposition = ACCEPT
        findings.append(
            "the silent-accept policy leaves no evidence that the field was "
            "non-reserved, so a revision boundary passes unnoticed"
        )
    return {
        "value": value,
        "role": role,
        "policy": policy,
        "conformant": graded["conformant"],
        "disposition": disposition,
        "findings": findings,
    }


def read_reserved_field(octets, path_length):
    """Pull the reserved octet out of a received unit."""
    try:
        data = list(octets)
    except TypeError:
        raise ValueError("octets must be a sequence, got %r" % (octets,))
    offset = reserved_field_offset(path_length)
    if len(data) <= offset:
        raise ValueError(
            "unit of %d octets is too short to hold a reserved field at "
            "offset %d" % (len(data), offset)
        )
    return _require_octet("reserved octet", data[offset])


def scan_reserved_field_log(records, policy=STRICT_DISCARD):
    """Tally a run of received reserved octets under one receiver policy."""
    _require_choice("policy", policy, RECEIVER_POLICIES)
    try:
        values = list(records)
    except TypeError:
        raise ValueError("records must be a sequence, got %r" % (records,))
    if not values:
        raise ValueError("an empty log cannot be graded")
    accepted = 0
    discarded = 0
    recorded = 0
    deviations = []
    for index, value in enumerate(values):
        outcome = assess_reserved_octet(value, RECEIVER, policy)
        if outcome["disposition"] == DISCARD:
            discarded += 1
        else:
            accepted += 1
            if outcome["disposition"] == ACCEPT_WITH_RECORD:
                recorded += 1
        if not outcome["conformant"]:
            deviations.append((index, value))
    total = len(values)
    return {
        "total": total,
        "accepted": accepted,
        "discarded": discarded,
        "recorded": recorded,
        "deviations": tuple(deviations),
        "deviation_rate": len(deviations) / float(total),
        "verdict": "log-clean" if not deviations else "log-has-deviations",
    }

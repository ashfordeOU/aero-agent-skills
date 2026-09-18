#!/usr/bin/env python3
"""Protocol identifier field of a packet transfer protocol data unit.

Anchor: ECSS-E-ST-50-53C clause 5.3.3. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Two things are settled here. Where the identifier sits -- the single
octet immediately after the target logical address, so its offset is
fixed by how many path-address bytes preceded that address -- and what
it carries: the identifier the packet transfer protocol is registered
under, so a receiving node can hand the rest of the unit to the right
protocol handler instead of guessing from the payload.

Identifier octet categories used here
    extended-identifier-escape   the low value that announces a wider
                                 identifier follows rather than naming
                                 a protocol itself
    assigned-protocol-identifier a value the registry already names
    unassigned-protocol-identifier  a value no registry entry claims

Standard library only, offline, deterministic.
"""

from __future__ import annotations

OCTET_MAX = 255
PATH_ADDRESS_MAX = 31

EXTENDED_IDENTIFIER_ESCAPE = 0
PACKET_TRANSFER_PROTOCOL_ID = 2

DEFAULT_IDENTIFIER_REGISTRY = {
    0: "extended-identifier-escape",
    1: "remote-memory-access-protocol",
    2: "packet-transfer-protocol",
}

ESCAPE_CATEGORY = "extended-identifier-escape"
ASSIGNED_CATEGORY = "assigned-protocol-identifier"
UNASSIGNED_CATEGORY = "unassigned-protocol-identifier"

DELIVER = "deliver-to-protocol-handler"
DISCARD_UNKNOWN = "discard-unknown-protocol"
DISCARD_ESCAPE = "discard-extended-identifier"


def _require_octet(name, value):
    """One unsigned octet, rejecting bools and anything out of range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    if value < 0 or value > OCTET_MAX:
        raise ValueError("%s must lie in 0..%d, got %d" % (name, OCTET_MAX, value))
    return value


def _require_path_length(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("path_length must be an integer, got %r" % (value,))
    if value < 0:
        raise ValueError("path_length must not be negative, got %d" % value)
    return value


def identifier_offset(path_length):
    """Index of the identifier octet for a unit with this many path bytes."""
    return _require_path_length(path_length) + 1


def categorize_protocol_identifier(value, registry=None):
    """Say whether the octet escapes, names a known protocol, or neither."""
    _require_octet("protocol identifier", value)
    table = DEFAULT_IDENTIFIER_REGISTRY if registry is None else registry
    if not isinstance(table, dict):
        raise ValueError("registry must be a mapping, got %r" % (table,))
    if value == EXTENDED_IDENTIFIER_ESCAPE:
        return ESCAPE_CATEGORY
    if value in table:
        return ASSIGNED_CATEGORY
    return UNASSIGNED_CATEGORY


def read_protocol_identifier(octets, path_length):
    """Pull the identifier octet out of a received unit."""
    try:
        data = list(octets)
    except TypeError:
        raise ValueError("octets must be a sequence, got %r" % (octets,))
    offset = identifier_offset(path_length)
    if len(data) <= offset:
        raise ValueError(
            "unit of %d octets is too short to hold an identifier at offset %d"
            % (len(data), offset)
        )
    for index in range(offset):
        _require_octet("octet %d" % index, data[index])
    if path_length and any(
        data[index] > PATH_ADDRESS_MAX for index in range(path_length)
    ):
        raise ValueError(
            "a declared path byte holds a logical address; the identifier "
            "offset cannot be trusted"
        )
    return _require_octet("protocol identifier", data[offset])


def validate_protocol_identifier(value, expected=PACKET_TRANSFER_PROTOCOL_ID):
    """Grade one identifier octet against the identifier expected here."""
    _require_octet("expected identifier", expected)
    category = categorize_protocol_identifier(value)
    matches = value == expected
    findings = []
    if category == ESCAPE_CATEGORY:
        findings.append(
            "identifier %d announces a wider identifier rather than naming a "
            "protocol, so this unit is not a packet transfer unit" % value
        )
    elif not matches:
        named = DEFAULT_IDENTIFIER_REGISTRY.get(value, "no registered protocol")
        findings.append(
            "identifier %d names %s, not the expected identifier %d"
            % (value, named, expected)
        )
    return {
        "value": value,
        "category": category,
        "expected": expected,
        "matches": matches,
        "conformant": matches,
        "findings": findings,
    }


def demultiplex_protocol(value, handlers):
    """Decide which handler a received unit belongs to, or that it is dropped."""
    if not isinstance(handlers, dict):
        raise ValueError("handlers must be a mapping, got %r" % (handlers,))
    _require_octet("protocol identifier", value)
    for key in handlers:
        _require_octet("handler key", key)
    if value == EXTENDED_IDENTIFIER_ESCAPE:
        return {
            "disposition": DISCARD_ESCAPE,
            "handler": None,
            "identifier": value,
        }
    if value in handlers:
        return {
            "disposition": DELIVER,
            "handler": handlers[value],
            "identifier": value,
        }
    return {"disposition": DISCARD_UNKNOWN, "handler": None, "identifier": value}


def encode_protocol_identifier_field(identifier=PACKET_TRANSFER_PROTOCOL_ID):
    """The single octet a sender writes for this protocol."""
    _require_octet("identifier", identifier)
    if identifier == EXTENDED_IDENTIFIER_ESCAPE:
        raise ValueError(
            "the escape value cannot be written as a protocol identifier on "
            "its own"
        )
    return (identifier,)


def assess_protocol_identifier_field(case):
    """Full clause 5.3.3 decision for one received unit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    octets = case.get("octets")
    if octets is None:
        raise ValueError("case must carry the received octets")
    path_length = case.get("path_length", 0)
    offset = identifier_offset(path_length)
    identifier = read_protocol_identifier(octets, path_length)
    expected = case.get("expected_identifier", PACKET_TRANSFER_PROTOCOL_ID)
    graded = validate_protocol_identifier(identifier, expected)
    handlers = case.get("handlers", {expected: "packet-transfer-protocol"})
    routed = demultiplex_protocol(identifier, handlers)
    findings = list(graded["findings"])
    if routed["disposition"] == DISCARD_UNKNOWN:
        findings.append(
            "identifier %d has no handler on this node, so the unit is "
            "dropped rather than parsed" % identifier
        )
    return {
        "identifier": identifier,
        "identifier_offset": offset,
        "category": graded["category"],
        "conformant": graded["conformant"],
        "disposition": routed["disposition"],
        "handler": routed["handler"],
        "verdict": (
            "identifier-accepted"
            if graded["conformant"] and routed["disposition"] == DELIVER
            else "identifier-rejected"
        ),
        "findings": findings,
    }

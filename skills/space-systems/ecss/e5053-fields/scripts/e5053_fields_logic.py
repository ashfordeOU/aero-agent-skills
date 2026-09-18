#!/usr/bin/env python3
"""Field set of a packet transfer protocol data unit.

Anchor: ECSS-E-ST-50-53C clause 5.4.1.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The individual field clauses each settle one octet. This clause settles
the set: which fields a unit is made of, and in what order they appear,
so that a sender and a receiver agree on where every boundary falls.

Order, after any path-address bytes the sender prepends

    target-logical-address   one octet, names the destination node
    protocol-identifier      one octet, names the protocol
    reserved                 one octet, held for a later revision
    user-application         one octet, names the user inside the node
    packet                   the rest of the unit, self-delimiting

Nothing here carries a length or a tag, so the structure is positional
from end to end: one wrong or missing octet shifts every field after it
and the unit still parses, into something that was never sent. That is
why this module refuses a short unit and audits a declared field
sequence rather than trusting it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

OCTET_MAX = 255
PATH_ADDRESS_MAX = 31
PRIMARY_HEADER_OCTETS = 6
MINIMUM_PACKET_OCTETS = PRIMARY_HEADER_OCTETS + 1

TARGET_LOGICAL_ADDRESS = "target-logical-address"
PROTOCOL_IDENTIFIER = "protocol-identifier"
RESERVED = "reserved"
USER_APPLICATION = "user-application"
PACKET = "packet"

FIELD_ORDER = (
    TARGET_LOGICAL_ADDRESS,
    PROTOCOL_IDENTIFIER,
    RESERVED,
    USER_APPLICATION,
    PACKET,
)
SINGLE_OCTET_FIELDS = FIELD_ORDER[:-1]

ORDER_OK = "field-order-conformant"
ORDER_BAD = "field-order-non-conformant"
UNIT_OK = "unit-well-formed"
UNIT_SHORT = "unit-too-short"


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


def field_offsets(path_length):
    """Offset of each single-octet field, and where the packet begins."""
    base = _require_path_length(path_length)
    offsets = {}
    for index, name in enumerate(SINGLE_OCTET_FIELDS):
        offsets[name] = base + index
    offsets[PACKET] = base + len(SINGLE_OCTET_FIELDS)
    return offsets


def minimum_unit_octets(path_length):
    """Shortest unit that can carry every field with a smallest packet."""
    base = _require_path_length(path_length)
    return base + len(SINGLE_OCTET_FIELDS) + MINIMUM_PACKET_OCTETS


def audit_field_sequence(declared):
    """Compare a declared field sequence against the order the unit needs."""
    try:
        names = list(declared)
    except TypeError:
        raise ValueError("declared must be a sequence of names, got %r" % (declared,))
    for name in names:
        if not isinstance(name, str) or not name:
            raise ValueError("field names must be non-empty strings, got %r" % (name,))
    if len(set(names)) != len(names):
        seen = set()
        repeated = sorted(set(n for n in names if n in seen or seen.add(n)))
        raise ValueError(
            "a field may appear once only; repeated: %s" % ", ".join(repeated)
        )
    missing = [name for name in FIELD_ORDER if name not in names]
    unexpected = [name for name in names if name not in FIELD_ORDER]
    known = [name for name in names if name in FIELD_ORDER]
    ordered = [name for name in FIELD_ORDER if name in known]
    misordered = known != ordered
    findings = []
    if missing:
        findings.append(
            "the unit is missing %s; the fields after the gap all shift by an "
            "octet" % ", ".join(missing)
        )
    if unexpected:
        findings.append(
            "%s is not a field of this unit and nothing in the structure marks "
            "where it would end" % ", ".join(unexpected)
        )
    if misordered:
        findings.append(
            "the declared order %s does not match the required order %s"
            % (" then ".join(known), " then ".join(ordered))
        )
    return {
        "declared": tuple(names),
        "required": FIELD_ORDER,
        "missing": tuple(missing),
        "unexpected": tuple(unexpected),
        "misordered": misordered,
        "conformant": not (missing or unexpected or misordered),
        "verdict": ORDER_OK if not (missing or unexpected or misordered) else ORDER_BAD,
        "findings": findings,
    }


def encode_unit(parts):
    """Lay the fields out in order and return the octets of the unit."""
    if not isinstance(parts, dict):
        raise ValueError("parts must be a mapping, got %r" % (parts,))
    octets = []
    for index, octet in enumerate(parts.get("path_addresses", ()) or ()):
        _require_octet("path address %d" % index, octet)
        if octet > PATH_ADDRESS_MAX:
            raise ValueError(
                "path address %d is octet %d, which a router keeps rather than "
                "consumes" % (index, octet)
            )
        octets.append(octet)
    for name in SINGLE_OCTET_FIELDS:
        key = name.replace("-", "_")
        if key not in parts:
            raise ValueError("parts is missing the %s field" % name)
        octets.append(_require_octet(name, parts[key]))
    packet = parts.get("packet")
    if packet is None:
        raise ValueError("parts is missing the packet field")
    try:
        packet_octets = list(packet)
    except TypeError:
        raise ValueError("packet must be a sequence of octets, got %r" % (packet,))
    if len(packet_octets) < MINIMUM_PACKET_OCTETS:
        raise ValueError(
            "a packet needs at least %d octets, got %d"
            % (MINIMUM_PACKET_OCTETS, len(packet_octets))
        )
    for index, octet in enumerate(packet_octets):
        _require_octet("packet octet %d" % index, octet)
    octets.extend(packet_octets)
    return tuple(octets)


def decode_unit(octets, path_length=0):
    """Split a received unit into its named fields, in order."""
    try:
        data = list(octets)
    except TypeError:
        raise ValueError("octets must be a sequence, got %r" % (octets,))
    base = _require_path_length(path_length)
    for index, octet in enumerate(data):
        _require_octet("octet %d" % index, octet)
    needed = minimum_unit_octets(base)
    if len(data) < needed:
        raise ValueError(
            "unit of %d octets cannot carry every field; %d are needed with "
            "%d path bytes" % (len(data), needed, base)
        )
    if any(octet > PATH_ADDRESS_MAX for octet in data[:base]):
        raise ValueError(
            "a declared path byte holds a logical address; the field "
            "boundaries cannot be trusted"
        )
    offsets = field_offsets(base)
    decoded = {"path_addresses": tuple(data[:base])}
    for name in SINGLE_OCTET_FIELDS:
        decoded[name.replace("-", "_")] = data[offsets[name]]
    decoded["packet"] = tuple(data[offsets[PACKET]:])
    decoded["field_order"] = FIELD_ORDER
    return decoded


def assess_fields(case):
    """Full clause 5.4.1.1 decision for one unit and its declared layout."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    octets = case.get("octets")
    if octets is None:
        raise ValueError("case must carry the unit octets")
    path_length = case.get("path_length", 0)
    audit = audit_field_sequence(case.get("declared_fields", FIELD_ORDER))
    findings = list(audit["findings"])
    try:
        decoded = decode_unit(octets, path_length)
    except ValueError as exc:
        findings.append(str(exc))
        return {
            "verdict": UNIT_SHORT,
            "well_formed": False,
            "order_verdict": audit["verdict"],
            "offsets": field_offsets(path_length),
            "minimum_octets": minimum_unit_octets(path_length),
            "fields": None,
            "findings": findings,
        }
    return {
        "verdict": UNIT_OK if audit["conformant"] else ORDER_BAD,
        "well_formed": audit["conformant"],
        "order_verdict": audit["verdict"],
        "offsets": field_offsets(path_length),
        "minimum_octets": minimum_unit_octets(path_length),
        "fields": decoded,
        "findings": findings,
    }

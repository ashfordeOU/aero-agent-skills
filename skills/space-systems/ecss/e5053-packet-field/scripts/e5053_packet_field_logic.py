#!/usr/bin/env python3
"""Packet field of a packet transfer protocol data unit.

Anchor: ECSS-E-ST-50-53C clause 5.3.6. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The packet field is the payload of the transfer: it carries the space
packet being moved across the link, and it is the last field of the
unit, so the link's end marker terminates it rather than any length
count written by the transfer protocol.

Three things follow, and they are the whole job of this module.

    one packet          the field carries a single complete packet, not
                        a fragment and not a concatenation
    self-delimiting     the packet's own primary header states how long
                        it is, so the transfer protocol never has to
                        carry a length of its own
    whole or nothing    a field shorter than the header declares is a
                        truncation and a field longer than it declares
                        has trailing octets that belong to nobody

The primary header is six octets: a version, a type bit, a secondary
header flag and an application process identifier in the first pair, the
sequence flags and sequence count in the second, and in the third a
length field that counts the data octets after the header, one less than
their number. Standard library only, offline, deterministic.
"""

from __future__ import annotations

OCTET_MAX = 255
PRIMARY_HEADER_OCTETS = 6
LENGTH_FIELD_BIAS = 1
APID_MASK = 0x07FF

COMPLETE = "packet-complete"
TRUNCATED = "packet-truncated"
OVERRUN = "packet-field-overrun"
OVER_LIMIT = "packet-field-over-limit"


def _require_octet(name, value):
    """One unsigned octet, rejecting bools and anything out of range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    if value < 0 or value > OCTET_MAX:
        raise ValueError("%s must lie in 0..%d, got %d" % (name, OCTET_MAX, value))
    return value


def _require_octets(name, values):
    try:
        data = list(values)
    except TypeError:
        raise ValueError("%s must be a sequence of octets, got %r" % (name, values))
    for index, value in enumerate(data):
        _require_octet("%s octet %d" % (name, index), value)
    return data


def packet_field_offset(path_length):
    """Index at which the packet field starts for this many path bytes."""
    if isinstance(path_length, bool) or not isinstance(path_length, int):
        raise ValueError("path_length must be an integer, got %r" % (path_length,))
    if path_length < 0:
        raise ValueError("path_length must not be negative, got %d" % path_length)
    return path_length + 4


def decode_primary_header(octets):
    """Read the six-octet header that makes the packet self-delimiting."""
    data = _require_octets("primary header", octets)
    if len(data) < PRIMARY_HEADER_OCTETS:
        raise ValueError(
            "a primary header needs %d octets, got %d"
            % (PRIMARY_HEADER_OCTETS, len(data))
        )
    first = (data[0] << 8) | data[1]
    second = (data[2] << 8) | data[3]
    length_field = (data[4] << 8) | data[5]
    return {
        "version": (first >> 13) & 0x07,
        "packet_type": (first >> 12) & 0x01,
        "secondary_header_flag": (first >> 11) & 0x01,
        "application_process_id": first & APID_MASK,
        "sequence_flags": (second >> 14) & 0x03,
        "sequence_count": second & 0x3FFF,
        "data_length_field": length_field,
        "data_octets": length_field + LENGTH_FIELD_BIAS,
    }


def space_packet_length(octets):
    """Total octets the packet declares itself to be."""
    header = decode_primary_header(octets)
    return PRIMARY_HEADER_OCTETS + header["data_octets"]


def encode_primary_header(
    application_process_id,
    sequence_count,
    data_octets,
    packet_type=0,
    secondary_header_flag=0,
    version=0,
    sequence_flags=3,
):
    """Build a six-octet header that declares the stated payload size."""
    for name, value, limit in (
        ("application_process_id", application_process_id, APID_MASK),
        ("sequence_count", sequence_count, 0x3FFF),
        ("packet_type", packet_type, 0x01),
        ("secondary_header_flag", secondary_header_flag, 0x01),
        ("version", version, 0x07),
        ("sequence_flags", sequence_flags, 0x03),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer, got %r" % (name, value))
        if value < 0 or value > limit:
            raise ValueError("%s must lie in 0..%d, got %d" % (name, limit, value))
    if isinstance(data_octets, bool) or not isinstance(data_octets, int):
        raise ValueError("data_octets must be an integer, got %r" % (data_octets,))
    if data_octets < LENGTH_FIELD_BIAS:
        raise ValueError(
            "a packet carries at least %d data octet, got %d"
            % (LENGTH_FIELD_BIAS, data_octets)
        )
    length_field = data_octets - LENGTH_FIELD_BIAS
    if length_field > 0xFFFF:
        raise ValueError(
            "%d data octets overflow the length field" % data_octets
        )
    first = (
        (version << 13)
        | (packet_type << 12)
        | (secondary_header_flag << 11)
        | application_process_id
    )
    second = (sequence_flags << 14) | sequence_count
    return (
        (first >> 8) & 0xFF,
        first & 0xFF,
        (second >> 8) & 0xFF,
        second & 0xFF,
        (length_field >> 8) & 0xFF,
        length_field & 0xFF,
    )


def validate_packet_field(octets, max_field_octets=None):
    """Compare what the field holds with what its own header declares."""
    data = _require_octets("packet field", octets)
    if len(data) < PRIMARY_HEADER_OCTETS:
        return {
            "declared_octets": None,
            "actual_octets": len(data),
            "shortfall": PRIMARY_HEADER_OCTETS - len(data),
            "trailing_octets": 0,
            "verdict": TRUNCATED,
            "findings": [
                "the field holds %d octets, too few to carry even the %d-octet "
                "primary header, so the declared length cannot be read"
                % (len(data), PRIMARY_HEADER_OCTETS)
            ],
        }
    declared = space_packet_length(data)
    actual = len(data)
    findings = []
    if max_field_octets is not None:
        if isinstance(max_field_octets, bool) or not isinstance(max_field_octets, int):
            raise ValueError(
                "max_field_octets must be an integer, got %r" % (max_field_octets,)
            )
        if max_field_octets < PRIMARY_HEADER_OCTETS:
            raise ValueError(
                "max_field_octets must leave room for the primary header, got %d"
                % max_field_octets
            )
    if actual < declared:
        verdict = TRUNCATED
        findings.append(
            "the header declares a %d-octet packet and the field holds %d; "
            "the unit was cut short" % (declared, actual)
        )
    elif actual > declared:
        verdict = OVERRUN
        findings.append(
            "the header declares a %d-octet packet and the field holds %d; "
            "the %d trailing octets belong to no packet"
            % (declared, actual, actual - declared)
        )
    else:
        verdict = COMPLETE
    if max_field_octets is not None and actual > max_field_octets:
        verdict = OVER_LIMIT
        findings.append(
            "the field holds %d octets against a link limit of %d"
            % (actual, max_field_octets)
        )
    return {
        "declared_octets": declared,
        "actual_octets": actual,
        "shortfall": max(0, declared - actual),
        "trailing_octets": max(0, actual - declared),
        "verdict": verdict,
        "findings": findings,
    }


def split_packet_field(octets):
    """Separate the single packet from anything trailing it."""
    graded = validate_packet_field(octets)
    data = _require_octets("packet field", octets)
    if graded["declared_octets"] is None or graded["verdict"] == TRUNCATED:
        raise ValueError(
            "a truncated field holds no complete packet to separate out"
        )
    declared = graded["declared_octets"]
    return {
        "packet": tuple(data[:declared]),
        "trailing": tuple(data[declared:]),
        "header": decode_primary_header(data),
    }


def assess_packet_field(case):
    """Full clause 5.3.6 decision for one received unit."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    octets = case.get("octets")
    if octets is None:
        raise ValueError("case must carry the received octets")
    path_length = case.get("path_length", 0)
    offset = packet_field_offset(path_length)
    data = _require_octets("unit", octets)
    if len(data) <= offset:
        raise ValueError(
            "unit of %d octets is too short to hold a packet field at offset %d"
            % (len(data), offset)
        )
    field = data[offset:]
    graded = validate_packet_field(field, case.get("max_field_octets"))
    header = None
    if graded["declared_octets"] is not None:
        header = decode_primary_header(field)
    return {
        "packet_field_offset": offset,
        "field_octets": len(field),
        "declared_octets": graded["declared_octets"],
        "trailing_octets": graded["trailing_octets"],
        "shortfall": graded["shortfall"],
        "application_process_id": None if header is None
        else header["application_process_id"],
        "verdict": graded["verdict"],
        "deliverable": graded["verdict"] == COMPLETE,
        "findings": list(graded["findings"]),
    }

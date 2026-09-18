#!/usr/bin/env python3
"""Packet length field of a CCSDS packet transfer PDU, ECSS-E-ST-50-53C 5.1.2.

Paraphrased requirement, no verbatim standard text. The clause puts two
obligations on the length field that a SpaceWire node prefixes to a carried
CCSDS packet: the field has to hold the octet count of the packet it
introduces, and a receiving node has to treat the declared count as the
authority on where that packet ends. This module turns both into a
deterministic decision:

  declared value + field width   -> in-capacity or an encoding error
  declared value                 -> a real declaration or the not-declared code
  CCSDS primary header           -> the length the packet claims for itself
  declared vs received octets    -> agreement, short declaration, long declaration
  agreement category             -> deliver the packet or discard it

stdlib only, offline, deterministic. Every quantity is an octet count, so the
comparisons are exact integer comparisons and carry no floating-point
representation error between hosts.
"""

from __future__ import annotations

# Width, in octets, of the length field when a deployment does not state one.
DEFAULT_LENGTH_FIELD_OCTETS = 2

# Widest field this module will encode or decode. Beyond this a length field
# is not a length field, it is a mis-parsed header.
MAX_LENGTH_FIELD_OCTETS = 4

# The encoding that says "this transfer does not declare a length"; the
# receiver then has to take the end of packet marker as the only delimiter.
LENGTH_NOT_DECLARED = 0

# Octets of CCSDS primary header that precede the packet data field.
CCSDS_PRIMARY_HEADER_OCTETS = 6

# Largest value the CCSDS packet data length header field can hold.
CCSDS_DATA_LENGTH_FIELD_MAX = 0xFFFF

AGREES = "agrees"
NOT_DECLARED = "not-declared"
DECLARED_SHORT = "declared-short"
DECLARED_LONG = "declared-long"
AGREEMENT_CATEGORIES = (AGREES, NOT_DECLARED, DECLARED_SHORT, DECLARED_LONG)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet count, got %r" % (name, value))
    return int(value)


def validate_field_width(field_octets=DEFAULT_LENGTH_FIELD_OCTETS):
    """Validate the declared width of the length field, in octets."""
    width = _integer(field_octets, "field_octets")
    if width < 1:
        raise ValueError("field_octets must be at least 1, got %d" % width)
    if width > MAX_LENGTH_FIELD_OCTETS:
        raise ValueError(
            "field_octets %d exceeds the %d octet limit of a length field"
            % (width, MAX_LENGTH_FIELD_OCTETS)
        )
    return width


def field_capacity(field_octets=DEFAULT_LENGTH_FIELD_OCTETS):
    """Largest octet count a length field of this width can express."""
    return (1 << (8 * validate_field_width(field_octets))) - 1


def validate_declared_length(value, field_octets=DEFAULT_LENGTH_FIELD_OCTETS):
    """Validate a declared length against the capacity of its field."""
    width = validate_field_width(field_octets)
    declared = _integer(value, "declared_length")
    if declared < 0:
        raise ValueError("declared_length must not be negative, got %d" % declared)
    capacity = field_capacity(width)
    if declared > capacity:
        raise ValueError(
            "declared_length %d does not fit a %d octet field (capacity %d)"
            % (declared, width, capacity)
        )
    return declared


def length_is_declared(value, field_octets=DEFAULT_LENGTH_FIELD_OCTETS):
    """True when the field carries a real length rather than the reserved code."""
    return validate_declared_length(value, field_octets) != LENGTH_NOT_DECLARED


def encode_length(value, field_octets=DEFAULT_LENGTH_FIELD_OCTETS):
    """Encode a declared length as big-endian octets of the given width."""
    width = validate_field_width(field_octets)
    declared = validate_declared_length(value, width)
    return tuple((declared >> (8 * (width - 1 - i))) & 0xFF for i in range(width))


def decode_length(octets):
    """Recover a declared length from its big-endian octet sequence."""
    if isinstance(octets, (str, bytes, bytearray)):
        sequence = list(bytearray(octets)) if not isinstance(octets, str) else None
        if sequence is None:
            raise ValueError("octets must be a sequence of integers, not text")
    elif isinstance(octets, (list, tuple)):
        sequence = list(octets)
    else:
        raise ValueError("octets must be a sequence of integers, got %r" % (octets,))
    if not sequence:
        raise ValueError("octets must hold at least one octet")
    validate_field_width(len(sequence))
    value = 0
    for index, octet in enumerate(sequence):
        item = _integer(octet, "octets[%d]" % index)
        if item < 0 or item > 0xFF:
            raise ValueError("octets[%d] must lie in 0..255, got %d" % (index, item))
        value = (value << 8) | item
    return value


def ccsds_packet_octets(packet_data_length_field):
    """Octets the carried packet claims for itself from its own header.

    The CCSDS primary header states the packet data field length as one less
    than its octet count, so the whole packet is the header plus that field
    plus one.
    """
    field = _integer(packet_data_length_field, "packet_data_length_field")
    if field < 0:
        raise ValueError(
            "packet_data_length_field must not be negative, got %d" % field
        )
    if field > CCSDS_DATA_LENGTH_FIELD_MAX:
        raise ValueError(
            "packet_data_length_field %d exceeds the header field maximum %d"
            % (field, CCSDS_DATA_LENGTH_FIELD_MAX)
        )
    return CCSDS_PRIMARY_HEADER_OCTETS + field + 1


def received_octet_count(packet):
    """Octets actually received for the carried packet."""
    if isinstance(packet, (bytes, bytearray)):
        return len(packet)
    if isinstance(packet, (list, tuple)):
        for index, octet in enumerate(packet):
            item = _integer(octet, "packet[%d]" % index)
            if item < 0 or item > 0xFF:
                raise ValueError(
                    "packet[%d] must lie in 0..255, got %d" % (index, item)
                )
        return len(packet)
    if isinstance(packet, int) and not isinstance(packet, bool):
        if packet < 0:
            raise ValueError("received octet count must not be negative")
        return int(packet)
    raise ValueError("packet must be octets or an octet count, got %r" % (packet,))


def categorize_length_agreement(
    declared_length, packet, field_octets=DEFAULT_LENGTH_FIELD_OCTETS
):
    """Group the declaration against what was received, as one of four cases."""
    declared = validate_declared_length(declared_length, field_octets)
    received = received_octet_count(packet)
    if declared == LENGTH_NOT_DECLARED:
        return NOT_DECLARED
    if declared == received:
        return AGREES
    if declared < received:
        return DECLARED_SHORT
    return DECLARED_LONG


def deliverable(category):
    """True when a category lets the receiving node hand the packet upward."""
    if category not in AGREEMENT_CATEGORIES:
        raise ValueError("unknown agreement category %r" % (category,))
    return category in (AGREES, NOT_DECLARED)


def assess_packet_length(
    declared_length,
    packet,
    field_octets=DEFAULT_LENGTH_FIELD_OCTETS,
    packet_data_length_field=None,
):
    """Full clause 5.1.2 assessment of one carried packet and its length field."""
    width = validate_field_width(field_octets)
    declared = validate_declared_length(declared_length, width)
    received = received_octet_count(packet)
    category = categorize_length_agreement(declared, received, width)

    header_octets = None
    if packet_data_length_field is not None:
        header_octets = ccsds_packet_octets(packet_data_length_field)

    findings = []
    limitations = []

    if category == DECLARED_SHORT:
        findings.append(
            "length field declares %d octets but %d were received; the trailing "
            "%d octets have no declared home" % (declared, received, received - declared)
        )
    elif category == DECLARED_LONG:
        findings.append(
            "length field declares %d octets but only %d were received; the "
            "packet is %d octets short of its declaration"
            % (declared, received, declared - received)
        )
    elif category == NOT_DECLARED:
        limitations.append(
            "no length declared; the end of packet marker is the only delimiter"
        )

    if header_octets is not None:
        if header_octets != received:
            findings.append(
                "carried packet header claims %d octets, %d were received"
                % (header_octets, received)
            )
        if declared != LENGTH_NOT_DECLARED and header_octets != declared:
            findings.append(
                "carried packet header claims %d octets, the length field "
                "declares %d" % (header_octets, declared)
            )

    accepted = deliverable(category) and not findings
    return {
        "field_octets": width,
        "field_capacity": field_capacity(width),
        "declared_length": declared,
        "declared": declared != LENGTH_NOT_DECLARED,
        "received_octets": received,
        "header_octets": header_octets,
        "category": category,
        "findings": findings,
        "limitations": limitations,
        "verdict": "deliver" if accepted else "discard",
    }

"""Packet-typed parameter: a whole space packet carried inside a field.

Anchor: ECSS-E-ST-70-41C clause 7.3.13 (packet data type, two normative
items). Paraphrased into an implementable procedure; no standard text is
reproduced.

What the clause is for. Some parameters do not carry a number or a
string -- they carry another packet, whole. A packet-store dump report
carries the stored packets. A forwarded telecommand carries the command
it forwards. A report of a rejected request carries the request. In all
of them the parameter's value is a complete space packet, primary
header and all.

The two things that follow:

* nothing is stripped. The contained packet keeps its own primary
  header, which is what makes it a packet rather than a payload -- the
  receiver can route, identify and sequence it exactly as if it had
  arrived on its own;
* its length is not declared alongside it. It is derived from the
  packet-length field inside the contained packet itself. A space
  packet states, in the last two octets of its six-octet primary
  header, the number of octets in its data field minus one; the total
  size is therefore that number plus seven.

Why that second item is the whole point. A container holding several
packets -- a dump report, a retransmission -- has no table of offsets.
The reader finds the second packet by having read the length of the
first out of the first. One packet whose stated length disagrees with
the octets actually present does not corrupt one entry; it desynchronises
everything after it, and the remaining packets are read from the middle
of their predecessors. So a separately declared length is never trusted
over the derived one: it is compared with it, and a disagreement is a
finding before it is a parse.

Stdlib only, offline, deterministic.
"""

__all__ = [
    "PRIMARY_HEADER_OCTETS",
    "LENGTH_FIELD_OFFSET",
    "MIN_PACKET_OCTETS",
    "MAX_PACKET_OCTETS",
    "validate_octets",
    "stated_data_length",
    "contained_packet_octets",
    "extract_contained_packet",
    "split_packet_sequence",
    "reconcile_declared_length",
    "assess_packet_parameter",
]

PRIMARY_HEADER_OCTETS = 6
# The packet-length field occupies the last two octets of the primary header.
LENGTH_FIELD_OFFSET = 4
# A data field holds at least one octet, so the field states at least 0.
MIN_PACKET_OCTETS = PRIMARY_HEADER_OCTETS + 1
MAX_PACKET_OCTETS = PRIMARY_HEADER_OCTETS + 0x10000


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_octets(octets, label="octets"):
    """Return the buffer as a list of octet values, refusing anything else."""
    if isinstance(octets, (bytes, bytearray)):
        return list(octets)
    if not isinstance(octets, (list, tuple)):
        raise ValueError("%s must be a sequence of octet values" % label)
    out = []
    for index, item in enumerate(octets):
        if not _is_int(item) or not 0 <= item <= 0xFF:
            raise ValueError("%s[%d] is not an octet value 0..255: %r" % (label, index, item))
        out.append(item)
    return out


def stated_data_length(octets, offset=0):
    """Return the value the contained packet's length field states."""
    buffer = validate_octets(octets)
    if not _is_int(offset) or offset < 0:
        raise ValueError("offset must be a non-negative integer, got %r" % (offset,))
    if offset + PRIMARY_HEADER_OCTETS > len(buffer):
        raise ValueError(
            "a primary header needs %d octets from offset %d, only %d are present; the "
            "length cannot be read at all"
            % (PRIMARY_HEADER_OCTETS, offset, max(0, len(buffer) - offset))
        )
    high = buffer[offset + LENGTH_FIELD_OFFSET]
    low = buffer[offset + LENGTH_FIELD_OFFSET + 1]
    return (high << 8) | low


def contained_packet_octets(octets, offset=0):
    """Return the total size of the contained packet, derived from its own header."""
    stated = stated_data_length(octets, offset)
    return PRIMARY_HEADER_OCTETS + stated + 1


def extract_contained_packet(octets, offset=0):
    """Return the contained packet and the offset the next one starts at."""
    buffer = validate_octets(octets)
    total = contained_packet_octets(buffer, offset)
    end = offset + total
    if end > len(buffer):
        raise ValueError(
            "the contained packet at offset %d states %d octets but only %d remain; the "
            "field is truncated and nothing after it can be located"
            % (offset, total, len(buffer) - offset)
        )
    return {
        "packet": buffer[offset:end],
        "octets": total,
        "data_field_octets": total - PRIMARY_HEADER_OCTETS,
        "next_offset": end,
    }


def split_packet_sequence(octets, expected_count=None):
    """Split a container of back-to-back packets using each one's own length."""
    buffer = validate_octets(octets)
    if expected_count is not None and (not _is_int(expected_count) or expected_count < 0):
        raise ValueError("expected_count must be a non-negative integer, got %r"
                         % (expected_count,))
    packets = []
    offset = 0
    while offset < len(buffer):
        if len(buffer) - offset < PRIMARY_HEADER_OCTETS:
            raise ValueError(
                "%d trailing octets at offset %d are too few for a primary header; the "
                "container did not end on a packet boundary"
                % (len(buffer) - offset, offset)
            )
        entry = extract_contained_packet(buffer, offset)
        packets.append(entry)
        offset = entry["next_offset"]
        if expected_count is not None and len(packets) > expected_count:
            raise ValueError(
                "the container holds more than the %d packets declared" % expected_count
            )
    if expected_count is not None and len(packets) != expected_count:
        raise ValueError(
            "the container holds %d packets, not the %d declared"
            % (len(packets), expected_count)
        )
    return packets


def reconcile_declared_length(octets, declared_octets, offset=0):
    """Compare a separately declared field length with the derived one."""
    if not _is_int(declared_octets) or declared_octets < 0:
        raise ValueError("declared_octets must be a non-negative integer, got %r"
                         % (declared_octets,))
    derived = contained_packet_octets(octets, offset)
    if declared_octets != derived:
        raise ValueError(
            "the field declares %d octets while the contained packet's own length field "
            "derives %d; the derived length is the one the reader must use, and the "
            "disagreement is a definition defect" % (declared_octets, derived)
        )
    return derived


def assess_packet_parameter(octets, expected_count=None, declared_octets=None):
    """Assess a packet-typed parameter and report every finding at once."""
    findings = []
    try:
        buffer = validate_octets(octets)
    except ValueError as exc:
        raise ValueError("the parameter value is not a buffer of octets: %s" % exc)
    packets = []
    offset = 0
    truncated = False
    while offset < len(buffer):
        remaining = len(buffer) - offset
        if remaining < PRIMARY_HEADER_OCTETS:
            findings.append(
                "%d trailing octets after the last complete packet: the container did not "
                "end on a packet boundary" % remaining
            )
            truncated = True
            break
        total = contained_packet_octets(buffer, offset)
        if offset + total > len(buffer):
            findings.append(
                "the packet at offset %d states %d octets but only %d remain; every packet "
                "after it is lost as well" % (offset, total, remaining)
            )
            truncated = True
            break
        entry = extract_contained_packet(buffer, offset)
        packets.append(entry)
        offset = entry["next_offset"]
    if not packets and not findings:
        findings.append("the parameter carries no packet at all")
    if expected_count is not None:
        if not _is_int(expected_count) or expected_count < 0:
            raise ValueError("expected_count must be a non-negative integer")
        if len(packets) != expected_count:
            findings.append(
                "%d complete packets recovered against the %d declared"
                % (len(packets), expected_count)
            )
    if declared_octets is not None and packets:
        if not _is_int(declared_octets) or declared_octets < 0:
            raise ValueError("declared_octets must be a non-negative integer")
        if declared_octets != packets[0]["octets"]:
            findings.append(
                "the field declares %d octets while the first contained packet derives %d"
                % (declared_octets, packets[0]["octets"])
            )
    for entry in packets:
        if entry["octets"] < MIN_PACKET_OCTETS:
            findings.append(
                "a contained packet of %d octets is shorter than the %d a header plus one "
                "data octet needs" % (entry["octets"], MIN_PACKET_OCTETS)
            )
    return {
        "packets": packets,
        "count": len(packets),
        "total_octets": sum(entry["octets"] for entry in packets),
        "consumed_octets": offset,
        "trailing_octets": len(buffer) - offset,
        "truncated": truncated,
        "findings": findings,
        "readable": not findings,
    }

"""CCSDS packet handling for the SpaceWire packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.1.1 (the CCSDS packet the protocol carries).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise and validate the fields of the six-byte primary header a space
   packet carries: version, application process identifier, the telemetry or
   telecommand direction, the secondary-header flag, the grouping flags, the
   sequence counter and the length of the packet data field.
2. Pack those fields into the header bytes and unpack captured bytes back
   into the same field record, so a capture and a construction agree.
3. Size the packet, and size the frame the transfer protocol wraps it in:
   the routing bytes, the one byte that names the protocol, and the packet
   itself.
4. Split a user datum too large for one packet data field into a grouped
   sequence, assigning the grouping flag and the byte count of each part.
5. Grade the combination of fields a reviewer would question: an idle
   application identifier carrying real data, a grouping flag that
   contradicts the sequence, a counter that does not advance, and a frame
   that overruns the profile's declared maximum.
"""

__all__ = [
    "PRIMARY_HEADER_BYTES",
    "PACKET_VERSION",
    "TYPE_TELEMETRY",
    "TYPE_TELECOMMAND",
    "TYPES",
    "APID_BITS",
    "APID_IDLE",
    "MAX_APID",
    "SEQUENCE_COUNT_BITS",
    "MAX_SEQUENCE_COUNT",
    "GROUPING_CONTINUATION",
    "GROUPING_FIRST",
    "GROUPING_LAST",
    "GROUPING_UNSEGMENTED",
    "GROUPING_FLAGS",
    "MIN_DATA_FIELD_BYTES",
    "MAX_DATA_FIELD_BYTES",
    "PROTOCOL_IDENTIFIER_BYTES",
    "validate_packet_fields",
    "packet_length_field",
    "data_field_bytes_from_length_field",
    "encode_primary_header",
    "decode_primary_header",
    "total_packet_bytes",
    "transfer_frame_bytes",
    "group_user_datum",
    "next_sequence_count",
    "assess_ccsds_packet",
]

PRIMARY_HEADER_BYTES = 6

# The version field of the packets this transfer protocol carries.
PACKET_VERSION = 0

TYPE_TELEMETRY = 0
TYPE_TELECOMMAND = 1
TYPES = (TYPE_TELEMETRY, TYPE_TELECOMMAND)

APID_BITS = 11
MAX_APID = (1 << APID_BITS) - 1
# The application identifier kept for fill traffic.
APID_IDLE = MAX_APID

SEQUENCE_COUNT_BITS = 14
MAX_SEQUENCE_COUNT = (1 << SEQUENCE_COUNT_BITS) - 1

GROUPING_CONTINUATION = 0
GROUPING_FIRST = 1
GROUPING_LAST = 2
GROUPING_UNSEGMENTED = 3
GROUPING_FLAGS = (
    GROUPING_CONTINUATION,
    GROUPING_FIRST,
    GROUPING_LAST,
    GROUPING_UNSEGMENTED,
)

# The length field counts one less than the data field, so an empty data
# field cannot be expressed and the largest is sixty-four kilobytes.
MIN_DATA_FIELD_BYTES = 1
MAX_DATA_FIELD_BYTES = 1 << 16

# One byte in the frame names the protocol carried after the routing bytes.
PROTOCOL_IDENTIFIER_BYTES = 1


def _require_int(value, label, minimum=None, maximum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer" % label)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be at least %d, got %d" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be at most %d, got %d" % (label, maximum, value))
    return value


def validate_packet_fields(fields):
    """Return a normalised primary-header field record."""
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping")
    version = _require_int(fields.get("version", PACKET_VERSION), "version", 0, 7)
    if version != PACKET_VERSION:
        raise ValueError(
            "version %d is not the version this transfer protocol carries" % version)
    packet_type = _require_int(fields.get("type", TYPE_TELEMETRY), "type", 0, 1)
    secondary_header = fields.get("secondary_header", False)
    if not isinstance(secondary_header, bool):
        raise ValueError("secondary_header must be a boolean")
    apid = _require_int(fields.get("apid"), "apid", 0, MAX_APID)
    grouping = _require_int(
        fields.get("grouping", GROUPING_UNSEGMENTED), "grouping", 0, 3)
    sequence_count = _require_int(
        fields.get("sequence_count", 0), "sequence_count", 0, MAX_SEQUENCE_COUNT)
    data_field_bytes = _require_int(
        fields.get("data_field_bytes"), "data_field_bytes",
        MIN_DATA_FIELD_BYTES, MAX_DATA_FIELD_BYTES)
    return {
        "version": version,
        "type": packet_type,
        "secondary_header": secondary_header,
        "apid": apid,
        "grouping": grouping,
        "sequence_count": sequence_count,
        "data_field_bytes": data_field_bytes,
    }


def packet_length_field(data_field_bytes):
    """Return the value the length field carries for a data field."""
    _require_int(data_field_bytes, "data_field_bytes",
                 MIN_DATA_FIELD_BYTES, MAX_DATA_FIELD_BYTES)
    return data_field_bytes - 1


def data_field_bytes_from_length_field(value):
    """Return the data-field size a length-field value stands for."""
    _require_int(value, "length field", 0, MAX_DATA_FIELD_BYTES - 1)
    return value + 1


def encode_primary_header(fields):
    """Return the six header bytes for a field record."""
    norm = validate_packet_fields(fields)
    first_word = (norm["version"] << 13)
    first_word |= (norm["type"] << 12)
    first_word |= ((1 if norm["secondary_header"] else 0) << 11)
    first_word |= norm["apid"]
    second_word = (norm["grouping"] << SEQUENCE_COUNT_BITS) | norm["sequence_count"]
    third_word = packet_length_field(norm["data_field_bytes"])
    return [
        (first_word >> 8) & 0xFF, first_word & 0xFF,
        (second_word >> 8) & 0xFF, second_word & 0xFF,
        (third_word >> 8) & 0xFF, third_word & 0xFF,
    ]


def decode_primary_header(header):
    """Return the field record carried by six captured header bytes."""
    if not isinstance(header, (bytes, bytearray, list, tuple)):
        raise ValueError("header must be a sequence of bytes")
    items = list(header)
    if len(items) != PRIMARY_HEADER_BYTES:
        raise ValueError(
            "primary header is %d bytes, got %d" % (PRIMARY_HEADER_BYTES, len(items)))
    for item in items:
        _require_int(item, "header byte", 0, 255)
    first_word = (items[0] << 8) | items[1]
    second_word = (items[2] << 8) | items[3]
    third_word = (items[4] << 8) | items[5]
    return validate_packet_fields({
        "version": (first_word >> 13) & 0b111,
        "type": (first_word >> 12) & 1,
        "secondary_header": bool((first_word >> 11) & 1),
        "apid": first_word & MAX_APID,
        "grouping": (second_word >> SEQUENCE_COUNT_BITS) & 0b11,
        "sequence_count": second_word & MAX_SEQUENCE_COUNT,
        "data_field_bytes": data_field_bytes_from_length_field(third_word),
    })


def total_packet_bytes(fields):
    """Return the whole packet size, primary header included."""
    norm = validate_packet_fields(fields)
    return PRIMARY_HEADER_BYTES + norm["data_field_bytes"]


def transfer_frame_bytes(fields, routing_bytes=1):
    """Return the frame size: routing bytes, protocol byte and the packet."""
    _require_int(routing_bytes, "routing_bytes", 1, 255)
    return routing_bytes + PROTOCOL_IDENTIFIER_BYTES + total_packet_bytes(fields)


def group_user_datum(total_bytes, max_data_field_bytes):
    """Return the (grouping flag, byte count) parts a user datum is split into."""
    _require_int(total_bytes, "total_bytes", MIN_DATA_FIELD_BYTES)
    _require_int(max_data_field_bytes, "max_data_field_bytes",
                 MIN_DATA_FIELD_BYTES, MAX_DATA_FIELD_BYTES)
    if total_bytes <= max_data_field_bytes:
        return [(GROUPING_UNSEGMENTED, total_bytes)]
    parts = []
    remaining = total_bytes
    while remaining > 0:
        take = min(remaining, max_data_field_bytes)
        parts.append(take)
        remaining -= take
    grouped = []
    for index, take in enumerate(parts):
        if index == 0:
            flag = GROUPING_FIRST
        elif index == len(parts) - 1:
            flag = GROUPING_LAST
        else:
            flag = GROUPING_CONTINUATION
        grouped.append((flag, take))
    return grouped


def next_sequence_count(value):
    """Return the sequence counter value that follows this one."""
    _require_int(value, "sequence_count", 0, MAX_SEQUENCE_COUNT)
    return (value + 1) % (MAX_SEQUENCE_COUNT + 1)


def assess_ccsds_packet(fields, routing_bytes=1, max_frame_bytes=None,
                        previous_sequence_count=None):
    """Grade a packet and the frame it travels in."""
    norm = validate_packet_fields(fields)
    findings = []
    if norm["apid"] == APID_IDLE and norm["grouping"] != GROUPING_UNSEGMENTED:
        findings.append(
            "fill traffic on the idle application identifier is carrying a grouped "
            "sequence")
    if norm["apid"] == APID_IDLE and norm["secondary_header"]:
        findings.append(
            "fill traffic on the idle application identifier declares a secondary header")
    frame = transfer_frame_bytes(norm, routing_bytes)
    if max_frame_bytes is not None:
        _require_int(max_frame_bytes, "max_frame_bytes", 1)
        if frame > max_frame_bytes:
            findings.append(
                "frame of %d bytes exceeds the %d-byte maximum the profile declares"
                % (frame, max_frame_bytes))
    if previous_sequence_count is not None:
        _require_int(previous_sequence_count, "previous_sequence_count",
                     0, MAX_SEQUENCE_COUNT)
        expected = next_sequence_count(previous_sequence_count)
        if norm["sequence_count"] != expected:
            findings.append(
                "sequence counter went from %d to %d where %d was due"
                % (previous_sequence_count, norm["sequence_count"], expected))
    return {
        "fields": norm,
        "primary_header": encode_primary_header(norm),
        "length_field": packet_length_field(norm["data_field_bytes"]),
        "packet_bytes": total_packet_bytes(norm),
        "frame_bytes": frame,
        "findings": findings,
        "acceptable": not findings,
    }

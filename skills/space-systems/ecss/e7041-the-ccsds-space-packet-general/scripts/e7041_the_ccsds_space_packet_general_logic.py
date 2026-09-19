"""The CCSDS space packet as the general container of the interface.

Anchor: ECSS-E-ST-70-41C clause 7.4.2 (the CCSDS space packet, general;
one normative item). Paraphrased into an implementable procedure; no
standard text is reproduced.

What the clause is for. One sentence carries the whole space-to-ground
interface: every telemetry report and every telecommand request crossing
it is a CCSDS space packet. Nothing else is on the wire, so every other
clause in the standard is describing what goes inside this container.

The container. A six-octet primary header followed by a packet data
field of at least one octet. The header divides as:

* packet version number, 3 bits -- zero for the version in use, and the
  first thing to check, because a non-zero value means the octets are
  not a space packet at all and nothing further parsed from them means
  anything;
* packet type, 1 bit -- telemetry in the space-to-ground direction,
  telecommand in the other;
* secondary header flag, 1 bit;
* application process identifier, 11 bits -- which on-board process the
  packet belongs to; the all-ones value is reserved for idle packets,
  which carry no service at all;
* sequence flags, 2 bits -- whether this packet stands alone or is one
  segment of a larger unit;
* packet sequence count or packet name, 14 bits -- a per-process
  counter that wraps, so gaps are detected modulo its span;
* packet data length, 16 bits -- the number of octets in the data field
  minus one.

The minus-one is the part implementations trip over. It exists so the
field can express a full 65536-octet data field, and it is why a
header-only packet has no representation: the smallest space packet is
seven octets.

Two further points this module enforces. The type and the direction
have to agree -- a telemetry-typed packet arriving on the uplink is
mislabelled, not merely unusual. And a packet carrying a service uses
the secondary header, so a service packet with the flag clear has lost
the fields that say which service it is.

Stdlib only, offline, deterministic.
"""

__all__ = [
    "PRIMARY_HEADER_OCTETS",
    "SUPPORTED_VERSION",
    "TYPE_TELEMETRY",
    "TYPE_TELECOMMAND",
    "IDLE_APID",
    "APID_MAX",
    "SEQUENCE_COUNT_MAX",
    "SEQUENCE_FLAG_NAMES",
    "MIN_PACKET_OCTETS",
    "MAX_DATA_FIELD_OCTETS",
    "data_length_field",
    "data_field_octets",
    "total_packet_octets",
    "validate_primary_header",
    "encode_primary_header",
    "decode_primary_header",
    "sequence_gap",
    "assess_space_packet",
]

PRIMARY_HEADER_OCTETS = 6
SUPPORTED_VERSION = 0
TYPE_TELEMETRY = 0
TYPE_TELECOMMAND = 1
APID_MAX = 0x7FF
IDLE_APID = APID_MAX
SEQUENCE_COUNT_MAX = 0x3FFF
SEQUENCE_FLAG_NAMES = {
    0: "continuation-segment",
    1: "first-segment",
    2: "last-segment",
    3: "unsegmented",
}
MIN_PACKET_OCTETS = PRIMARY_HEADER_OCTETS + 1
MAX_DATA_FIELD_OCTETS = 0x10000

_DIRECTIONS = ("space-to-ground", "ground-to-space")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _field(name, value, low, high):
    if not _is_int(value):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if not low <= value <= high:
        raise ValueError("%s must be %d..%d, got %d" % (name, low, high, value))
    return value


def data_length_field(data_octets):
    """Return the value the length field carries for a data field of this size."""
    if not _is_int(data_octets):
        raise ValueError("data_octets must be an integer, got %r" % (data_octets,))
    if data_octets < 1:
        raise ValueError(
            "a packet data field holds at least one octet; a header-only space packet has "
            "no representation"
        )
    if data_octets > MAX_DATA_FIELD_OCTETS:
        raise ValueError(
            "a data field of %d octets exceeds the %d a 16-bit length field reaches"
            % (data_octets, MAX_DATA_FIELD_OCTETS)
        )
    return data_octets - 1


def data_field_octets(length_field_value):
    """Return the data field size a length field value states."""
    value = _field("length_field_value", length_field_value, 0, 0xFFFF)
    return value + 1


def total_packet_octets(data_octets):
    """Return the whole packet size for a data field of this many octets."""
    data_length_field(data_octets)  # refuses a data field the container cannot hold
    return PRIMARY_HEADER_OCTETS + data_octets


def validate_primary_header(fields):
    """Return a normalised, range-checked primary header."""
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping of primary-header field names")
    version = _field("version", fields.get("version", SUPPORTED_VERSION), 0, 7)
    if version != SUPPORTED_VERSION:
        raise ValueError(
            "packet version number %d is not the supported %d; these octets are not a space "
            "packet and nothing parsed further from them means anything"
            % (version, SUPPORTED_VERSION)
        )
    packet_type = _field("packet_type", fields.get("packet_type"), 0, 1)
    secondary_header = _field("secondary_header_flag", fields.get("secondary_header_flag"), 0, 1)
    apid = _field("apid", fields.get("apid"), 0, APID_MAX)
    sequence_flags = _field("sequence_flags", fields.get("sequence_flags"), 0, 3)
    sequence_count = _field("sequence_count", fields.get("sequence_count"), 0,
                            SEQUENCE_COUNT_MAX)
    data_octets = fields.get("data_octets")
    length_value = data_length_field(data_octets)
    return {
        "version": version,
        "packet_type": packet_type,
        "packet_type_name": "telecommand" if packet_type == TYPE_TELECOMMAND else "telemetry",
        "secondary_header_flag": secondary_header,
        "apid": apid,
        "idle": apid == IDLE_APID,
        "sequence_flags": sequence_flags,
        "sequence_flags_name": SEQUENCE_FLAG_NAMES[sequence_flags],
        "sequence_count": sequence_count,
        "data_octets": data_octets,
        "length_field": length_value,
        "total_octets": PRIMARY_HEADER_OCTETS + data_octets,
    }


def encode_primary_header(fields):
    """Encode a primary header into its six octets."""
    header = validate_primary_header(fields)
    word0 = (header["version"] << 13) | (header["packet_type"] << 12) \
        | (header["secondary_header_flag"] << 11) | header["apid"]
    word1 = (header["sequence_flags"] << 14) | header["sequence_count"]
    word2 = header["length_field"]
    return [
        (word0 >> 8) & 0xFF, word0 & 0xFF,
        (word1 >> 8) & 0xFF, word1 & 0xFF,
        (word2 >> 8) & 0xFF, word2 & 0xFF,
    ]


def decode_primary_header(octets):
    """Decode the six header octets into their fields."""
    if isinstance(octets, (bytes, bytearray)):
        buffer = list(octets)
    elif isinstance(octets, (list, tuple)):
        buffer = list(octets)
    else:
        raise ValueError("octets must be a sequence of octet values")
    for index, item in enumerate(buffer):
        if not _is_int(item) or not 0 <= item <= 0xFF:
            raise ValueError("octets[%d] is not an octet value 0..255: %r" % (index, item))
    if len(buffer) < PRIMARY_HEADER_OCTETS:
        raise ValueError(
            "a primary header is %d octets; only %d were supplied"
            % (PRIMARY_HEADER_OCTETS, len(buffer))
        )
    word0 = (buffer[0] << 8) | buffer[1]
    word1 = (buffer[2] << 8) | buffer[3]
    word2 = (buffer[4] << 8) | buffer[5]
    return validate_primary_header({
        "version": (word0 >> 13) & 0x07,
        "packet_type": (word0 >> 12) & 0x01,
        "secondary_header_flag": (word0 >> 11) & 0x01,
        "apid": word0 & APID_MAX,
        "sequence_flags": (word1 >> 14) & 0x03,
        "sequence_count": word1 & SEQUENCE_COUNT_MAX,
        "data_octets": data_field_octets(word2),
    })


def sequence_gap(previous_count, current_count):
    """Return how many counts were skipped, allowing for the counter wrap."""
    previous = _field("previous_count", previous_count, 0, SEQUENCE_COUNT_MAX)
    current = _field("current_count", current_count, 0, SEQUENCE_COUNT_MAX)
    span = SEQUENCE_COUNT_MAX + 1
    return (current - previous - 1) % span


def assess_space_packet(octets, direction="space-to-ground", carries_a_service=True,
                        previous_count=None):
    """Assess one packet against the general container rule and its direction."""
    if direction not in _DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (_DIRECTIONS, direction))
    header = decode_primary_header(octets)
    buffer = list(octets)
    findings = []
    if len(buffer) != header["total_octets"]:
        findings.append(
            "the length field states a %d-octet packet while %d octets are present"
            % (header["total_octets"], len(buffer))
        )
    expected_type = TYPE_TELEMETRY if direction == "space-to-ground" else TYPE_TELECOMMAND
    if header["packet_type"] != expected_type:
        findings.append(
            "a %s packet is travelling %s; the type and the direction disagree"
            % (header["packet_type_name"], direction)
        )
    if header["idle"]:
        if carries_a_service:
            findings.append(
                "the all-ones application process identifier is reserved for idle packets, "
                "which carry no service"
            )
    elif carries_a_service and header["secondary_header_flag"] == 0:
        findings.append(
            "a packet carrying a service has the secondary header flag clear, so the fields "
            "naming the service are absent"
        )
    if header["sequence_flags"] != 3 and header["idle"]:
        findings.append(
            "an idle packet is segmented; idle packets fill a frame and are never one "
            "segment of a larger unit"
        )
    gap = None
    if previous_count is not None:
        gap = sequence_gap(previous_count, header["sequence_count"])
        if gap:
            findings.append(
                "%d packets are missing between sequence count %d and %d on this "
                "application process" % (gap, previous_count, header["sequence_count"])
            )
    return {
        "header": header,
        "data_field": buffer[PRIMARY_HEADER_OCTETS:header["total_octets"]],
        "direction": direction,
        "sequence_gap": gap,
        "findings": findings,
        "conformant": not findings,
    }

"""CCSDS Packet field occupancy logic for the SpaceWire packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.4.1.7 -- the CCSDS Packet field of the
encapsulating SpaceWire packet. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the octet sequence handed over as the CCSDS Packet field: every
   element an integer in 0..255, the field long enough to carry a primary
   header at all.
2. Parse the six-octet space packet primary header: packet version number,
   packet type, secondary header flag, application process identifier,
   sequence flags, sequence count and the packet data length field.
3. Derive the declared total length of the space packet from the data length
   field, which counts the octets of the data field minus one.
4. Compare the declared total length with the octets actually present in the
   field, so a truncated packet (declared longer than present) and a surplus
   tail (declared shorter than present) are separated findings.
5. Walk the whole field packet by packet so a field carrying a second space
   packet, or a fragment of one, is reported rather than silently accepted as
   one oversized packet.
6. Report the occupancy verdict: the field is compliant only when it holds one
   whole space packet and nothing after it.
"""

__all__ = [
    "PRIMARY_HEADER_OCTETS",
    "IDLE_APID",
    "SPACE_PACKET_VERSION_1",
    "MAX_SPACE_PACKET_OCTETS",
    "validate_octets",
    "parse_primary_header",
    "declared_total_length",
    "scan_field",
    "assess_ccsds_packet_field",
]

# A space packet primary header is six octets wide.
PRIMARY_HEADER_OCTETS = 6

# All-ones application process identifier: the idle pattern, never real user
# data, so a transfer carrying one is a finding rather than a payload.
IDLE_APID = 0x7FF

# Packet version number of the space packet format used by this protocol.
SPACE_PACKET_VERSION_1 = 0

# Data length field is 16 bits and counts (data field octets - 1), so the
# largest expressible space packet is header + 65536 octets of data field.
MAX_SPACE_PACKET_OCTETS = PRIMARY_HEADER_OCTETS + 0x10000


def validate_octets(octets, name="field_octets"):
    """Return the octet sequence as a tuple of ints, rejecting anything else."""
    if isinstance(octets, (str, bytes, bytearray)):
        if isinstance(octets, str):
            raise ValueError("%s must be a sequence of octet values, not text" % name)
        values = tuple(int(v) for v in octets)
        return values
    if not isinstance(octets, (list, tuple)):
        raise ValueError("%s must be a list, tuple, bytes or bytearray" % name)
    values = []
    for index, item in enumerate(octets):
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("%s[%d] must be an integer octet value" % (name, index))
        if item < 0 or item > 255:
            raise ValueError("%s[%d] out of octet range 0..255, got %d" % (name, index, item))
        values.append(int(item))
    return tuple(values)


def parse_primary_header(octets, offset=0):
    """Parse the six-octet space packet primary header starting at offset."""
    values = validate_octets(octets, "header_octets")
    if isinstance(offset, bool) or not isinstance(offset, int):
        raise ValueError("offset must be an integer")
    if offset < 0:
        raise ValueError("offset must be non-negative, got %d" % offset)
    if len(values) - offset < PRIMARY_HEADER_OCTETS:
        raise ValueError(
            "primary header needs %d octets from offset %d, only %d available"
            % (PRIMARY_HEADER_OCTETS, offset, max(0, len(values) - offset))
        )
    b0, b1, b2, b3, b4, b5 = values[offset:offset + PRIMARY_HEADER_OCTETS]
    return {
        "version": (b0 >> 5) & 0x07,
        "packet_type": (b0 >> 4) & 0x01,
        "secondary_header_flag": (b0 >> 3) & 0x01,
        "apid": ((b0 & 0x07) << 8) | b1,
        "sequence_flags": (b2 >> 6) & 0x03,
        "sequence_count": ((b2 & 0x3F) << 8) | b3,
        "data_length_field": (b4 << 8) | b5,
    }


def declared_total_length(header):
    """Return the total octet count the primary header declares for its packet."""
    if not isinstance(header, dict):
        raise ValueError("header must be a mapping produced by parse_primary_header")
    if "data_length_field" not in header:
        raise ValueError("header is missing 'data_length_field'")
    field = header["data_length_field"]
    if isinstance(field, bool) or not isinstance(field, int):
        raise ValueError("data_length_field must be an integer")
    if field < 0 or field > 0xFFFF:
        raise ValueError("data_length_field out of range 0..65535, got %d" % field)
    return PRIMARY_HEADER_OCTETS + field + 1


def scan_field(field_octets):
    """Walk the field and return one span record per space packet found."""
    values = validate_octets(field_octets)
    spans = []
    cursor = 0
    total = len(values)
    while cursor < total:
        remaining = total - cursor
        if remaining < PRIMARY_HEADER_OCTETS:
            spans.append({
                "offset": cursor,
                "header": None,
                "declared_length": None,
                "present_length": remaining,
                "complete": False,
            })
            break
        header = parse_primary_header(values, cursor)
        declared = declared_total_length(header)
        present = min(declared, remaining)
        spans.append({
            "offset": cursor,
            "header": header,
            "declared_length": declared,
            "present_length": present,
            "complete": declared <= remaining,
        })
        if declared <= 0:
            raise ValueError("declared packet length must be positive")
        cursor += declared
    return spans


def assess_ccsds_packet_field(field_octets, expect_user_data=True):
    """Assess whether the CCSDS Packet field carries exactly one whole packet.

    Returns a mapping with the parsed header of the leading packet, the
    declared and present octet counts, the packet spans found, a findings list
    and the compliance verdict.
    """
    if not isinstance(expect_user_data, bool):
        raise ValueError("expect_user_data must be a boolean")
    values = validate_octets(field_octets)
    findings = []
    if not values:
        return {
            "header": None,
            "declared_length": None,
            "present_length": 0,
            "surplus_octets": 0,
            "packet_count": 0,
            "spans": [],
            "findings": ["CCSDS Packet field is empty; the transfer carries no space packet"],
            "compliant": False,
        }
    if len(values) < PRIMARY_HEADER_OCTETS:
        return {
            "header": None,
            "declared_length": None,
            "present_length": len(values),
            "surplus_octets": 0,
            "packet_count": 0,
            "spans": scan_field(values),
            "findings": [
                "CCSDS Packet field holds %d octets, short of the %d-octet primary header"
                % (len(values), PRIMARY_HEADER_OCTETS)
            ],
            "compliant": False,
        }
    spans = scan_field(values)
    lead = spans[0]
    header = lead["header"]
    declared = lead["declared_length"]
    present = len(values)
    surplus = present - declared
    if declared > present:
        findings.append(
            "leading space packet declares %d octets but only %d are present; "
            "the packet is truncated" % (declared, present)
        )
    elif surplus > 0:
        findings.append(
            "%d octet(s) follow the leading space packet; the field must end with it"
            % surplus
        )
    if len(spans) > 1:
        findings.append(
            "%d space packets found in one CCSDS Packet field; the field carries one"
            % len(spans)
        )
    if header["version"] != SPACE_PACKET_VERSION_1:
        findings.append(
            "packet version number %d is not the space packet version this protocol carries"
            % header["version"]
        )
    if expect_user_data and header["apid"] == IDLE_APID:
        findings.append("idle application process identifier carried as user data")
    if declared > MAX_SPACE_PACKET_OCTETS:
        findings.append("declared length %d exceeds the expressible maximum" % declared)
    return {
        "header": header,
        "declared_length": declared,
        "present_length": present,
        "surplus_octets": surplus if surplus > 0 else 0,
        "packet_count": len(spans),
        "spans": spans,
        "findings": findings,
        "compliant": not findings,
    }

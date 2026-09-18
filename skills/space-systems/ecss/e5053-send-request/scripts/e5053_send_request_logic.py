"""SEND request validation for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.5.2 -- the send request the user issues to
hand a CCSDS packet to the protocol entity for transmission. Paraphrased into
an implementable procedure; no standard text is reproduced.

Three normative obligations are implemented as three separable checks:
  (a) the request names a destination the entity can actually address, either
      a logical address or a path of output port numbers optionally ending in
      a logical address;
  (b) the request carries exactly one complete CCSDS packet, whose declared
      length agrees with the octets supplied;
  (c) the resulting SpaceWire packet -- address octets, protocol identifier,
      reserved octet and the CCSDS packet -- fits inside the transmit limit
      the local entity was configured with, so an over-long request is refused
      at the interface rather than truncated on the link.
"""

__all__ = [
    "PROTOCOL_IDENTIFIER",
    "RESERVED_OCTET",
    "PRIMARY_HEADER_OCTETS",
    "LOGICAL_ADDRESS_MIN",
    "LOGICAL_ADDRESS_MAX",
    "PATH_PORT_MAX",
    "DEFAULT_MAX_TRANSFER_OCTETS",
    "categorize_destination",
    "encode_destination",
    "validate_ccsds_packet",
    "encode_send_request",
    "assess_send_request",
]

# Protocol identifier the CCSDS packet transfer protocol is carried under.
PROTOCOL_IDENTIFIER = 0x02

# The single reserved octet that follows the protocol identifier.
RESERVED_OCTET = 0x00

PRIMARY_HEADER_OCTETS = 6

# Logical addresses available to destination nodes; the values below this are
# reserved and the top value is the broadcast-style reserved code.
LOGICAL_ADDRESS_MIN = 32
LOGICAL_ADDRESS_MAX = 254

# Output port numbers usable in a path address.
PATH_PORT_MAX = 31

# A conservative default transmit limit for one transfer, in octets.
DEFAULT_MAX_TRANSFER_OCTETS = 65535


def _octet_list(values, name):
    if isinstance(values, (bytes, bytearray)):
        return [int(v) for v in values]
    if isinstance(values, str) or not isinstance(values, (list, tuple)):
        raise ValueError("%s must be a list, tuple, bytes or bytearray of octets" % name)
    out = []
    for index, item in enumerate(values):
        if isinstance(item, bool) or not isinstance(item, int):
            raise ValueError("%s[%d] must be an integer octet value" % (name, index))
        if item < 0 or item > 255:
            raise ValueError("%s[%d] out of octet range 0..255, got %d" % (name, index, item))
        out.append(int(item))
    return out


def categorize_destination(destination):
    """Return ('logical'|'path', octets) for a destination address."""
    if isinstance(destination, bool):
        raise ValueError("destination must be an address, not a boolean")
    if isinstance(destination, int):
        if destination < LOGICAL_ADDRESS_MIN or destination > LOGICAL_ADDRESS_MAX:
            raise ValueError(
                "logical address %d is outside the usable range %d..%d"
                % (destination, LOGICAL_ADDRESS_MIN, LOGICAL_ADDRESS_MAX)
            )
        return ("logical", [destination])
    octets = _octet_list(destination, "destination")
    if not octets:
        raise ValueError("destination path must name at least one output port")
    if len(octets) == 1:
        single = octets[0]
        if LOGICAL_ADDRESS_MIN <= single <= LOGICAL_ADDRESS_MAX:
            return ("logical", [single])
        if 1 <= single <= PATH_PORT_MAX:
            return ("path", [single])
        raise ValueError(
            "single destination octet %d is neither an output port 1..%d nor a "
            "logical address %d..%d"
            % (single, PATH_PORT_MAX, LOGICAL_ADDRESS_MIN, LOGICAL_ADDRESS_MAX)
        )
    for index, octet in enumerate(octets[:-1]):
        if octet < 1 or octet > PATH_PORT_MAX:
            raise ValueError(
                "path element %d is %d; output ports run 1..%d"
                % (index, octet, PATH_PORT_MAX)
            )
    tail = octets[-1]
    tail_is_port = 1 <= tail <= PATH_PORT_MAX
    tail_is_logical = LOGICAL_ADDRESS_MIN <= tail <= LOGICAL_ADDRESS_MAX
    if not (tail_is_port or tail_is_logical):
        raise ValueError(
            "final path element %d is neither an output port nor a logical address"
            % tail
        )
    return ("path", octets)


def encode_destination(destination):
    """Return the leading address octets for a destination."""
    return categorize_destination(destination)[1]


def validate_ccsds_packet(packet_octets):
    """Validate one complete CCSDS packet and return (octets, declared_length)."""
    octets = _octet_list(packet_octets, "ccsds_packet")
    if len(octets) < PRIMARY_HEADER_OCTETS:
        raise ValueError(
            "CCSDS packet holds %d octet(s), short of the %d-octet primary header"
            % (len(octets), PRIMARY_HEADER_OCTETS)
        )
    data_length_field = (octets[4] << 8) | octets[5]
    declared = PRIMARY_HEADER_OCTETS + data_length_field + 1
    if declared != len(octets):
        raise ValueError(
            "CCSDS packet declares %d octet(s) but %d were supplied"
            % (declared, len(octets))
        )
    return (octets, declared)


def encode_send_request(destination, packet_octets):
    """Encode the SpaceWire packet body a send request produces."""
    address = encode_destination(destination)
    packet, _declared = validate_ccsds_packet(packet_octets)
    return address + [PROTOCOL_IDENTIFIER, RESERVED_OCTET] + packet


def assess_send_request(request):
    """Assess one send request against the three clause 5.5.2 obligations.

    request keys: destination, ccsds_packet, optional max_transfer_octets.
    """
    if not isinstance(request, dict):
        raise ValueError("request must be a mapping")
    for key in ("destination", "ccsds_packet"):
        if key not in request:
            raise ValueError("request missing required key '%s'" % key)
    limit = request.get("max_transfer_octets", DEFAULT_MAX_TRANSFER_OCTETS)
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("max_transfer_octets must be an integer")
    if limit <= 0:
        raise ValueError("max_transfer_octets must be positive, got %d" % limit)

    findings = []
    kind = None
    address = []
    try:
        kind, address = categorize_destination(request["destination"])
    except ValueError as exc:
        findings.append("destination rejected: %s" % exc)

    packet = None
    declared = None
    try:
        packet, declared = validate_ccsds_packet(request["ccsds_packet"])
    except ValueError as exc:
        findings.append("CCSDS packet rejected: %s" % exc)

    encoded = None
    total = None
    if not findings:
        encoded = address + [PROTOCOL_IDENTIFIER, RESERVED_OCTET] + packet
        total = len(encoded)
        if total > limit:
            findings.append(
                "encoded transfer is %d octet(s) against a transmit limit of %d; "
                "the request is refused rather than truncated" % (total, limit)
            )
    return {
        "destination_kind": kind,
        "address_octets": address,
        "packet_octets": declared,
        "encoded": encoded,
        "encoded_octets": total,
        "max_transfer_octets": limit,
        "findings": findings,
        "accepted": not findings,
    }

"""Received-transfer delivery logic for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.5.3 -- transferring the CCSDS packet carried
by a received SpaceWire packet up to the user. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Take the SpaceWire packet as the destination node sees it, the terminator
   the link reported, and whether the node was addressed logically (a leading
   logical address octet still present) or by path (routers already consumed
   the address octets).
2. Refuse anything the link did not terminate normally before parsing: an
   abandoned transfer carries a fragment, not a packet.
3. Strip the leading logical address octet when one is present, read the
   protocol identifier and the reserved octet, and keep the remainder as the
   CCSDS packet field.
4. Deliver only a transfer whose protocol identifier is the one assigned to
   this protocol and whose CCSDS Packet field holds exactly one whole packet;
   a transfer under another protocol identifier is not an error -- it belongs
   to a different entity and is handed on, not discarded.
5. Report the delivery decision together with the extracted packet and the
   reason, so an operator can separate a link fault, a mis-addressed transfer
   and a framing defect.
"""

__all__ = [
    "PROTOCOL_IDENTIFIER",
    "EXTENDED_PROTOCOL_MARKER",
    "PRIMARY_HEADER_OCTETS",
    "DELIVER",
    "DISCARD",
    "NOT_OURS",
    "strip_leading_logical_address",
    "read_protocol_fields",
    "packet_field_is_whole",
    "receive_transfer",
]

PROTOCOL_IDENTIFIER = 0x02

# A zero protocol identifier announces an extended identifier in the octets
# that follow, so it is never this protocol.
EXTENDED_PROTOCOL_MARKER = 0x00

PRIMARY_HEADER_OCTETS = 6

DELIVER = "deliver"
DISCARD = "discard"
NOT_OURS = "not-this-protocol"

_GOOD_TERMINATORS = ("EOP", "END_OF_PACKET", "NORMAL")


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


def _terminator_is_normal(terminator):
    if terminator is None:
        return False
    if not isinstance(terminator, str):
        raise ValueError("terminator must be a string or None, got %r" % (terminator,))
    token = terminator.strip().upper().replace(" ", "_").replace("-", "_")
    if not token:
        raise ValueError("terminator must not be blank")
    if token in _GOOD_TERMINATORS:
        return True
    if token in ("EEP", "ERROR_END_OF_PACKET", "ERROR", "NONE", "MISSING"):
        return False
    raise ValueError("unknown terminator %r" % (terminator,))


def strip_leading_logical_address(octets, addressed_logically):
    """Return the transfer body with the leading logical address octet removed."""
    values = _octet_list(octets, "transfer")
    if not isinstance(addressed_logically, bool):
        raise ValueError("addressed_logically must be a boolean")
    if not addressed_logically:
        return values
    if not values:
        raise ValueError("transfer is empty; there is no logical address octet to strip")
    return values[1:]


def read_protocol_fields(body):
    """Return (protocol_identifier, reserved_octet, packet_field) from a transfer body."""
    values = _octet_list(body, "body")
    if len(values) < 2:
        raise ValueError(
            "transfer body holds %d octet(s); the protocol identifier and reserved "
            "octet need 2" % len(values)
        )
    return (values[0], values[1], values[2:])


def packet_field_is_whole(packet_field):
    """Return True when the field holds exactly one complete CCSDS packet."""
    values = _octet_list(packet_field, "packet_field")
    if len(values) < PRIMARY_HEADER_OCTETS:
        return False
    declared = PRIMARY_HEADER_OCTETS + ((values[4] << 8) | values[5]) + 1
    return declared == len(values)


def receive_transfer(octets, terminator="EOP", addressed_logically=True):
    """Decide what to do with one received SpaceWire transfer.

    Returns a mapping carrying the disposition, the extracted CCSDS packet when
    there is one, the protocol identifier read, the reason and any findings.
    """
    result = {
        "disposition": DISCARD,
        "protocol_identifier": None,
        "reserved_octet": None,
        "ccsds_packet": None,
        "reason": "",
        "findings": [],
        "delivered": False,
    }
    if not _terminator_is_normal(terminator):
        result["reason"] = (
            "transfer was not terminated normally; it carries a fragment and is "
            "discarded before parsing"
        )
        result["findings"].append(result["reason"])
        return result
    body = strip_leading_logical_address(octets, addressed_logically)
    try:
        protocol, reserved, packet_field = read_protocol_fields(body)
    except ValueError as exc:
        result["reason"] = "transfer too short to carry the protocol fields: %s" % exc
        result["findings"].append(result["reason"])
        return result
    result["protocol_identifier"] = protocol
    result["reserved_octet"] = reserved
    if protocol != PROTOCOL_IDENTIFIER:
        result["disposition"] = NOT_OURS
        if protocol == EXTENDED_PROTOCOL_MARKER:
            result["reason"] = (
                "protocol identifier announces an extended identifier; the transfer "
                "belongs to another entity"
            )
        else:
            result["reason"] = (
                "protocol identifier %d is not the CCSDS packet transfer protocol; "
                "the transfer belongs to another entity" % protocol
            )
        return result
    if not packet_field_is_whole(packet_field):
        result["reason"] = (
            "CCSDS Packet field does not hold exactly one whole space packet"
        )
        result["findings"].append(result["reason"])
        return result
    result["disposition"] = DELIVER
    result["ccsds_packet"] = packet_field
    result["delivered"] = True
    result["reason"] = "one whole CCSDS packet extracted and transferred to the user"
    if reserved != 0:
        result["findings"].append(
            "reserved octet carried %d rather than zero; the contents are ignored "
            "and delivery proceeds" % reserved
        )
    return result

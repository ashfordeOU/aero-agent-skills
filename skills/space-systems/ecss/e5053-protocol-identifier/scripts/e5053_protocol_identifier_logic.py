"""Protocol identifier field logic for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.5.4.1 -- the protocol identifier field of the
encapsulating SpaceWire packet. Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the field as a single octet.
2. Categorize the value: the identifier assigned to this protocol, the marker
   announcing an extended identifier in the following octets, an identifier
   assigned to a different protocol on the same link, or a value in the range
   held back from assignment.
3. Decide, for a sender, whether the field is set as this protocol requires --
   it is the assigned value and nothing else.
4. Decide, for a receiver, whether the transfer is this entity's to handle,
   keeping "belongs to another entity" apart from "malformed", because the two
   have different consequences on a shared link.
5. Where an extended identifier is announced, report how many further octets
   must be read before any demultiplexing decision can be made.
"""

__all__ = [
    "PROTOCOL_IDENTIFIER",
    "EXTENDED_MARKER",
    "EXTENDED_IDENTIFIER_OCTETS",
    "RESERVED_RANGE",
    "KNOWN_IDENTIFIERS",
    "SENDER",
    "RECEIVER",
    "validate_identifier_octet",
    "categorize_identifier",
    "expected_identifier",
    "assess_protocol_identifier",
    "demultiplex",
]

# The value this protocol's transfers carry.
PROTOCOL_IDENTIFIER = 0x02

# Zero announces an extended identifier carried in the octets that follow.
EXTENDED_MARKER = 0x00

# Octets of extended identifier that follow the marker.
EXTENDED_IDENTIFIER_OCTETS = 3

# Values held back from assignment, inclusive at both ends.
RESERVED_RANGE = (0xF0, 0xFE)

# Identifiers this entity can name when it sees them on the link.
KNOWN_IDENTIFIERS = {
    0x01: "remote memory access protocol",
    0x02: "CCSDS packet transfer protocol",
}

SENDER = "sender"
RECEIVER = "receiver"

# Categories returned by categorize_identifier.
_ASSIGNED_TO_THIS = "assigned-to-this-protocol"
_EXTENDED = "extended-identifier-announced"
_OTHER_KNOWN = "assigned-to-another-protocol"
_RESERVED = "reserved-value"
_UNASSIGNED = "unassigned-value"


def validate_identifier_octet(value, name="protocol_identifier"):
    """Return the identifier as an int, rejecting anything that is not an octet."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet value" % name)
    if value < 0 or value > 255:
        raise ValueError("%s out of octet range 0..255, got %d" % (name, value))
    return int(value)


def categorize_identifier(value):
    """Return the category token for a protocol identifier octet."""
    octet = validate_identifier_octet(value)
    if octet == EXTENDED_MARKER:
        return _EXTENDED
    if octet == PROTOCOL_IDENTIFIER:
        return _ASSIGNED_TO_THIS
    if octet in KNOWN_IDENTIFIERS:
        return _OTHER_KNOWN
    low, high = RESERVED_RANGE
    if low <= octet <= high:
        return _RESERVED
    return _UNASSIGNED


def expected_identifier():
    """Return the identifier a sender of this protocol writes into the field."""
    return PROTOCOL_IDENTIFIER


def assess_protocol_identifier(value, role=SENDER):
    """Assess a protocol identifier octet from the sender's or receiver's side."""
    if not isinstance(role, str):
        raise ValueError("role must be a string")
    role_token = role.strip().lower()
    if role_token not in (SENDER, RECEIVER):
        raise ValueError("role must be %r or %r, got %r" % (SENDER, RECEIVER, role))
    octet = validate_identifier_octet(value)
    category = categorize_identifier(octet)
    findings = []
    extra_octets = 0
    if category == _EXTENDED:
        extra_octets = EXTENDED_IDENTIFIER_OCTETS
    if role_token == SENDER:
        compliant = category == _ASSIGNED_TO_THIS
        if not compliant:
            findings.append(
                "sender wrote %d into the protocol identifier field; this protocol's "
                "transfers carry %d" % (octet, PROTOCOL_IDENTIFIER)
            )
        return {
            "value": octet,
            "role": role_token,
            "category": category,
            "name": KNOWN_IDENTIFIERS.get(octet),
            "extended_octets_to_read": extra_octets,
            "for_this_entity": category == _ASSIGNED_TO_THIS,
            "findings": findings,
            "compliant": compliant,
        }
    for_this_entity = category == _ASSIGNED_TO_THIS
    if category == _RESERVED:
        findings.append(
            "received identifier %d lies in the range held back from assignment; "
            "no entity owns it" % octet
        )
    return {
        "value": octet,
        "role": role_token,
        "category": category,
        "name": KNOWN_IDENTIFIERS.get(octet),
        "extended_octets_to_read": extra_octets,
        "for_this_entity": for_this_entity,
        "findings": findings,
        "compliant": not findings,
    }


def demultiplex(value):
    """Return (for_this_entity, reason) for a received protocol identifier."""
    result = assess_protocol_identifier(value, RECEIVER)
    if result["for_this_entity"]:
        return (True, "identifier is the one assigned to the CCSDS packet transfer protocol")
    if result["category"] == _EXTENDED:
        return (
            False,
            "extended identifier announced; read %d further octet(s) before deciding"
            % EXTENDED_IDENTIFIER_OCTETS,
        )
    if result["category"] == _OTHER_KNOWN:
        return (False, "identifier belongs to the %s" % KNOWN_IDENTIFIERS[result["value"]])
    if result["category"] == _RESERVED:
        return (False, "identifier lies in the range held back from assignment")
    return (False, "identifier %d is not assigned to a protocol on this link" % result["value"])

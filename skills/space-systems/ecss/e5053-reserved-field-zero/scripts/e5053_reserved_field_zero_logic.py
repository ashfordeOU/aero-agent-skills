"""Reserved field logic for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.5.4.2 -- the reserved field that follows the
protocol identifier. Paraphrased into an implementable procedure; no standard
text is reproduced.

Two normative obligations are implemented as two separable rules, because they
fall on different parties and have opposite consequences:
  (a) the sender writes zero into the reserved field -- an equality it has no
      discretion over, and a non-zero value is a sending-side defect;
  (b) the receiver ignores what the field holds -- it neither acts on the
      contents nor refuses delivery over them, so a non-zero value reaching a
      receiver is recorded as an observation about the sender, never as a
      reason to discard the transfer.

Keeping the two apart is the whole job: a receiver that enforces rule (a) as
though it were its own becomes intolerant of senders it is required to accept,
and a sender that leans on rule (b) fills the field with data no future
revision can then use.
"""

__all__ = [
    "RESERVED_VALUE",
    "RESERVED_FIELD_OCTETS",
    "SENDER",
    "RECEIVER",
    "DELIVER",
    "REJECT",
    "encode_reserved_field",
    "validate_reserved_octet",
    "assess_sender_field",
    "assess_receiver_field",
    "assess_reserved_field",
    "audit_transfers",
]

# The value the sender writes.
RESERVED_VALUE = 0x00

# Width of the reserved field, in octets.
RESERVED_FIELD_OCTETS = 1

SENDER = "sender"
RECEIVER = "receiver"

DELIVER = "deliver"
REJECT = "reject"


def encode_reserved_field():
    """Return the reserved field octets a conforming sender emits."""
    return [RESERVED_VALUE] * RESERVED_FIELD_OCTETS


def validate_reserved_octet(value, name="reserved_octet"):
    """Return the reserved field value as an int, rejecting non-octets."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet value" % name)
    if value < 0 or value > 255:
        raise ValueError("%s out of octet range 0..255, got %d" % (name, value))
    return int(value)


def assess_sender_field(value):
    """Assess the reserved field as written by a sender."""
    octet = validate_reserved_octet(value)
    findings = []
    if octet != RESERVED_VALUE:
        findings.append(
            "sender wrote %d into the reserved field; the field is emitted as %d"
            % (octet, RESERVED_VALUE)
        )
    return {
        "value": octet,
        "role": SENDER,
        "findings": findings,
        "compliant": not findings,
    }


def assess_receiver_field(value):
    """Assess the reserved field as seen by a receiver.

    The receiver ignores the contents, so the disposition is always delivery;
    a non-zero value is recorded as an observation about the sender.
    """
    octet = validate_reserved_octet(value)
    observations = []
    if octet != RESERVED_VALUE:
        observations.append(
            "reserved field carried %d rather than %d; contents ignored and the "
            "transfer proceeds" % (octet, RESERVED_VALUE)
        )
    return {
        "value": octet,
        "role": RECEIVER,
        "disposition": DELIVER,
        "observations": observations,
        "sender_conformant": octet == RESERVED_VALUE,
        "compliant": True,
    }


def assess_reserved_field(value, role=SENDER):
    """Assess the reserved field from whichever side the caller is on."""
    if not isinstance(role, str):
        raise ValueError("role must be a string")
    token = role.strip().lower()
    if token == SENDER:
        return assess_sender_field(value)
    if token == RECEIVER:
        return assess_receiver_field(value)
    raise ValueError("role must be %r or %r, got %r" % (SENDER, RECEIVER, role))


def audit_transfers(values, tolerate_non_zero=True):
    """Audit the reserved field across received transfers.

    Counts how many senders wrote something other than zero, and reports the
    disposition a conforming receiver applies -- delivery -- unless the caller
    is deliberately modelling an intolerant receiver, which is a finding in
    itself.
    """
    if isinstance(values, (str, bytes, bytearray)):
        if isinstance(values, str):
            raise ValueError("values must be a sequence of octet values, not text")
        octets = [int(v) for v in values]
    elif isinstance(values, (list, tuple)):
        octets = [validate_reserved_octet(v, "values[%d]" % i) for i, v in enumerate(values)]
    else:
        raise ValueError("values must be a list, tuple, bytes or bytearray")
    if not octets:
        raise ValueError("values must not be empty")
    if not isinstance(tolerate_non_zero, bool):
        raise ValueError("tolerate_non_zero must be a boolean")
    non_zero = [octet for octet in octets if octet != RESERVED_VALUE]
    findings = []
    if non_zero:
        findings.append(
            "%d of %d transfer(s) carried a non-zero reserved field; the senders are "
            "non-conformant" % (len(non_zero), len(octets))
        )
    if not tolerate_non_zero:
        findings.append(
            "receiver is configured to reject on the reserved field; the receiving "
            "side ignores its contents and must not refuse delivery over them"
        )
    return {
        "total": len(octets),
        "non_zero": len(non_zero),
        "distinct_non_zero_values": sorted(set(non_zero)),
        "disposition": DELIVER if tolerate_non_zero else REJECT,
        "findings": findings,
        "receiver_conformant": bool(tolerate_non_zero),
    }

"""Non-zero reserved field handling for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.5.4.3 -- what the receiving entity does with a
transfer whose reserved octet is not the zero a conforming sender writes.
Paraphrased into an implementable procedure; no standard text is reproduced.

Two normative obligations are implemented:
  (a) the transfer is not a conformant transfer of this protocol version, so the
      receiving entity does not hand a CCSDS packet up from it -- the payload is
      not parsed and nothing partial reaches the user;
  (b) the condition is reported, carrying the value that was actually seen, so a
      peer built to a different revision is distinguishable from a link that is
      corrupting octets.

The adjacent clause fixes the SENDING side (write zero). This module is the
receiving side and deliberately does not re-implement that rule: the value seen
here is evidence about a peer, and the verdict it drives is about this transfer.
"""

__all__ = [
    "RESERVED_VALUE",
    "DELIVER",
    "DISCARD",
    "CONFORMANT",
    "PEER_REVISION",
    "CORRUPTION",
    "SPORADIC",
    "validate_reserved_octet",
    "validate_octet_sequence",
    "is_version_conformant",
    "handle_reserved_field",
    "receive_transfer",
    "audit_run",
]

# The only value this revision of the protocol accepts in the reserved field.
RESERVED_VALUE = 0x00

DELIVER = "deliver"
DISCARD = "discard"

CONFORMANT = "conformant"
PEER_REVISION = "peer-revision-mismatch"
CORRUPTION = "corruption-suspected"
SPORADIC = "sporadic-non-zero"

# Fraction of a run that must be non-zero before a single repeated value reads
# as a peer built to another revision rather than as an occasional upset.
_REVISION_SHARE = 0.5


def validate_reserved_octet(value, name="reserved_octet"):
    """Return the reserved field value as an int, rejecting anything not an octet."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet value" % name)
    if value < 0 or value > 255:
        raise ValueError("%s out of octet range 0..255, got %d" % (name, value))
    return int(value)


def validate_octet_sequence(values, name="values"):
    """Return a list of validated octets from a list, tuple, bytes or bytearray."""
    if isinstance(values, str):
        raise ValueError("%s must be a sequence of octet values, not text" % name)
    if isinstance(values, (bytes, bytearray)):
        octets = [int(v) for v in values]
    elif isinstance(values, (list, tuple)):
        octets = [
            validate_reserved_octet(v, "%s[%d]" % (name, i)) for i, v in enumerate(values)
        ]
    else:
        raise ValueError("%s must be a list, tuple, bytes or bytearray" % name)
    if not octets:
        raise ValueError("%s must not be empty" % name)
    return octets


def is_version_conformant(value):
    """Return True when the reserved field carries the value this revision defines."""
    return validate_reserved_octet(value) == RESERVED_VALUE


def handle_reserved_field(value):
    """Decide the disposition of one transfer from its reserved field alone.

    A non-zero field ends the transfer before the payload is looked at, and
    produces a report naming the value seen and the value this revision defines.
    """
    octet = validate_reserved_octet(value)
    if octet == RESERVED_VALUE:
        return {
            "value": octet,
            "version_conformant": True,
            "disposition": DELIVER,
            "payload_parsed": True,
            "report": None,
        }
    return {
        "value": octet,
        "version_conformant": False,
        "disposition": DISCARD,
        "payload_parsed": False,
        "report": (
            "reserved field carried %d rather than %d; the transfer is not a "
            "conformant transfer of this protocol revision and no packet is "
            "delivered from it" % (octet, RESERVED_VALUE)
        ),
    }


def receive_transfer(reserved_octet, packet_octets):
    """Apply the clause to a whole received transfer.

    Returns the packet only when the reserved field permits it; otherwise the
    packet field is None, which is the point -- a partial or foreign-revision
    transfer must not reach the user in any form.
    """
    verdict = handle_reserved_field(reserved_octet)
    payload = validate_octet_sequence(packet_octets, "packet_octets")
    if not verdict["version_conformant"]:
        return {
            "value": verdict["value"],
            "disposition": DISCARD,
            "packet": None,
            "octets_withheld": len(payload),
            "report": verdict["report"],
        }
    return {
        "value": verdict["value"],
        "disposition": DELIVER,
        "packet": list(payload),
        "octets_withheld": 0,
        "report": None,
    }


def audit_run(values):
    """Grade a run of received reserved-field values.

    Counts the discards and names the likely cause: one value repeated across
    most of the run is a peer emitting a different revision, a scatter of values
    is octets being corrupted, and a rare single value is neither yet.
    """
    octets = validate_octet_sequence(values)
    non_zero = [octet for octet in octets if octet != RESERVED_VALUE]
    distinct = sorted(set(non_zero))
    total = len(octets)
    share = float(len(non_zero)) / float(total)
    if not non_zero:
        diagnosis = CONFORMANT
    elif len(distinct) > 1:
        diagnosis = CORRUPTION
    elif share >= _REVISION_SHARE:
        diagnosis = PEER_REVISION
    else:
        diagnosis = SPORADIC
    findings = []
    if non_zero:
        findings.append(
            "%d of %d transfer(s) discarded on a non-zero reserved field"
            % (len(non_zero), total)
        )
    if diagnosis == PEER_REVISION:
        findings.append(
            "one repeated value (%d) dominates the run; the peer is emitting a "
            "revision this entity does not implement" % distinct[0]
        )
    elif diagnosis == CORRUPTION:
        findings.append(
            "%d distinct non-zero values seen; octets are being corrupted rather "
            "than a peer speaking another revision" % len(distinct)
        )
    return {
        "total": total,
        "discarded": len(non_zero),
        "delivered": total - len(non_zero),
        "distinct_non_zero_values": distinct,
        "discard_share": share,
        "diagnosis": diagnosis,
        "findings": findings,
    }

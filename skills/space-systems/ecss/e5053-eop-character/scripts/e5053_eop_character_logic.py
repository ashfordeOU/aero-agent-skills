"""End-of-packet marker disposition for the SpaceWire CCSDS packet transfer protocol.

Anchor: ECSS-E-ST-50-53C clause 5.4.1.8 -- the EOP character terminating the
SpaceWire packet that carries a CCSDS packet. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Normalise the end-of-packet marker reported by the link interface: the
   normal end-of-packet character, the error end-of-packet character, or no
   marker at all when the receiver ran out of buffer or the link disconnected
   mid-packet.
2. Decide the disposition of the transfer from the marker alone: only a normal
   end-of-packet marker makes the contained CCSDS packet deliverable. An error
   marker means the sender or the link abandoned the packet, so what arrived is
   a fragment and is discarded, not repaired.
3. Keep the reason with the disposition so an operator can separate a link
   fault from an absent terminator.
4. Grade a received sequence: count deliverable and discarded transfers, derive
   the discard ratio, and compare it with an acceptable link budget so a link
   that is technically running but shredding packets is visible.
"""

__all__ = [
    "EOP",
    "EEP",
    "NO_MARKER",
    "DELIVER",
    "DISCARD",
    "normalise_marker",
    "marker_disposition",
    "assess_transfer",
    "grade_reception",
]

# The normal end-of-packet character: the packet ended where the sender meant
# it to end.
EOP = "EOP"

# The error end-of-packet character: the packet was abandoned in flight.
EEP = "EEP"

# No terminator was seen at all -- the packet never ended.
NO_MARKER = "NONE"

DELIVER = "deliver"
DISCARD = "discard"

_ALIASES = {
    "EOP": EOP,
    "END_OF_PACKET": EOP,
    "END-OF-PACKET": EOP,
    "NORMAL": EOP,
    "EEP": EEP,
    "ERROR_END_OF_PACKET": EEP,
    "ERROR-END-OF-PACKET": EEP,
    "ERROR": EEP,
    "NONE": NO_MARKER,
    "MISSING": NO_MARKER,
    "TRUNCATED": NO_MARKER,
}


def normalise_marker(marker):
    """Return the canonical marker token for a reported terminator."""
    if marker is None:
        return NO_MARKER
    if not isinstance(marker, str):
        raise ValueError("marker must be a string or None, got %r" % (marker,))
    token = marker.strip().upper().replace(" ", "_")
    if not token:
        raise ValueError("marker must not be blank")
    if token not in _ALIASES:
        raise ValueError(
            "unknown end-of-packet marker %r; expected one of EOP, EEP or NONE"
            % (marker,)
        )
    return _ALIASES[token]


def marker_disposition(marker):
    """Return (disposition, reason) for a reported end-of-packet marker."""
    token = normalise_marker(marker)
    if token == EOP:
        return (DELIVER, "normal end-of-packet marker; the transfer is complete")
    if token == EEP:
        return (
            DISCARD,
            "error end-of-packet marker; the transfer was abandoned in flight and "
            "what arrived is a fragment",
        )
    return (
        DISCARD,
        "no end-of-packet marker; the transfer never terminated and cannot be "
        "treated as a whole packet",
    )


def assess_transfer(marker, payload_octets=None, expected_octets=None):
    """Assess one received transfer against its terminator and, if known, its length."""
    token = normalise_marker(marker)
    disposition, reason = marker_disposition(token)
    findings = []
    if disposition == DISCARD:
        findings.append(reason)
    for label, value in (("payload_octets", payload_octets),
                         ("expected_octets", expected_octets)):
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer or None" % label)
        if value < 0:
            raise ValueError("%s must be non-negative, got %d" % (label, value))
    if payload_octets is not None and expected_octets is not None:
        if payload_octets != expected_octets:
            findings.append(
                "received %d octet(s) against %d expected"
                % (payload_octets, expected_octets)
            )
            if token == EOP:
                findings.append(
                    "a normal end-of-packet marker on a short transfer points at the "
                    "sender's framing, not at the link"
                )
    deliverable = disposition == DELIVER and not findings
    return {
        "marker": token,
        "disposition": DELIVER if deliverable else DISCARD,
        "reason": reason,
        "payload_octets": payload_octets,
        "expected_octets": expected_octets,
        "findings": findings,
        "deliverable": deliverable,
    }


def grade_reception(markers, max_discard_ratio=0.0):
    """Grade a sequence of reported terminators against a discard-ratio budget."""
    if isinstance(markers, str) or not isinstance(markers, (list, tuple)):
        raise ValueError("markers must be a list or tuple of reported terminators")
    if not markers:
        raise ValueError("markers must not be empty")
    if isinstance(max_discard_ratio, bool) or not isinstance(max_discard_ratio, (int, float)):
        raise ValueError("max_discard_ratio must be a real number")
    budget = float(max_discard_ratio)
    if not (0.0 <= budget <= 1.0):
        raise ValueError("max_discard_ratio must lie in 0..1, got %r" % (max_discard_ratio,))
    counts = {EOP: 0, EEP: 0, NO_MARKER: 0}
    delivered = 0
    for marker in markers:
        token = normalise_marker(marker)
        counts[token] += 1
        if marker_disposition(token)[0] == DELIVER:
            delivered += 1
    total = len(markers)
    discarded = total - delivered
    ratio = discarded / float(total)
    findings = []
    if ratio > budget:
        findings.append(
            "discard ratio %.6f exceeds the budget %.6f over %d transfer(s)"
            % (ratio, budget, total)
        )
    if counts[NO_MARKER]:
        findings.append(
            "%d transfer(s) arrived with no terminator at all" % counts[NO_MARKER]
        )
    return {
        "total": total,
        "delivered": delivered,
        "discarded": discarded,
        "counts": counts,
        "discard_ratio": ratio,
        "max_discard_ratio": budget,
        "findings": findings,
        "within_budget": ratio <= budget,
    }

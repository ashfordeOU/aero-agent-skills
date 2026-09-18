#!/usr/bin/env python3
"""CCSDS Packet Transfer Service, ECSS-E-ST-50-53C clause 5.2.1.

Paraphrased requirement, no verbatim standard text. The clause obliges the
protocol to offer the sending user application a service that takes one CCSDS
packet together with the parameters naming its destination, and hands that
same packet, whole and unmodified, to the receiving user application as a
single delivery. This module models the service at the primitive level rather
than at the octet-layout level, and turns the obligation into a deterministic
assessment:

  request parameters            -> a validated service request
  what carriage actually did    -> an indication, or a discard with a reason
  requested vs delivered packet -> unmodified, truncated, extended or altered
  requested vs delivered
  parameters                    -> whether the transfer kept what it was told
  a run of packets              -> whether packet boundaries survived at all

The four ways this service can fail are kept apart on purpose: the packet was
not delivered, it was delivered changed, it was delivered as more or fewer
deliveries than it was given, or it was delivered with different parameters.
Each points somewhere different. stdlib only, offline, deterministic.
"""

from __future__ import annotations

# Octets of CCSDS primary header that must precede any packet data.
CCSDS_PRIMARY_HEADER_OCTETS = 6
MIN_PACKET_OCTETS = CCSDS_PRIMARY_HEADER_OCTETS + 1

# How a SpaceWire transfer ended. Only the normal marker permits delivery.
END_OF_PACKET = "eop"
ERROR_END_OF_PACKET = "eep"
NO_TERMINATOR = "none"
TERMINATORS = (END_OF_PACKET, ERROR_END_OF_PACKET, NO_TERMINATOR)

UNMODIFIED = "unmodified"
TRUNCATED = "truncated"
EXTENDED = "extended"
ALTERED = "altered"
PACKET_CATEGORIES = (UNMODIFIED, TRUNCATED, EXTENDED, ALTERED)

INDICATED = "indicated"
DISCARDED = "discarded"
OUTCOMES = (INDICATED, DISCARDED)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    return int(value)


def validate_packet(packet, name="packet"):
    """Validate a CCSDS packet as a sequence of octets and return it."""
    if isinstance(packet, (bytes, bytearray)):
        octets = tuple(bytearray(packet))
    elif isinstance(packet, (list, tuple)):
        octets = tuple(
            _integer(octet, "%s[%d]" % (name, index))
            for index, octet in enumerate(packet)
        )
    else:
        raise ValueError("%s must be a sequence of octets, got %r" % (name, packet))
    for index, octet in enumerate(octets):
        if octet < 0 or octet > 255:
            raise ValueError(
                "%s[%d] must lie in 0..255, got %d" % (name, index, octet)
            )
    if len(octets) < MIN_PACKET_OCTETS:
        raise ValueError(
            "%s is %d octets; a CCSDS packet needs at least %d"
            % (name, len(octets), MIN_PACKET_OCTETS)
        )
    return octets


def validate_terminator(terminator):
    """Validate how the transfer ended on the link."""
    if terminator not in TERMINATORS:
        raise ValueError(
            "terminator must be one of %s, got %r" % (", ".join(TERMINATORS), terminator)
        )
    return terminator


def build_request(
    packet,
    target_spacewire_address=(),
    target_logical_address=254,
    user_application_value=0,
):
    """Validate the parameters the sending application hands the service."""
    octets = validate_packet(packet)
    if isinstance(target_spacewire_address, (bytes, bytearray)):
        prefix = tuple(bytearray(target_spacewire_address))
    elif isinstance(target_spacewire_address, (list, tuple)):
        prefix = tuple(
            _integer(octet, "target_spacewire_address[%d]" % index)
            for index, octet in enumerate(target_spacewire_address)
        )
    else:
        raise ValueError(
            "target_spacewire_address must be a sequence of octets, got %r"
            % (target_spacewire_address,)
        )
    for index, octet in enumerate(prefix):
        if octet < 0 or octet > 255:
            raise ValueError(
                "target_spacewire_address[%d] must lie in 0..255, got %d"
                % (index, octet)
            )
    logical = _integer(target_logical_address, "target_logical_address")
    if logical < 0 or logical > 255:
        raise ValueError(
            "target_logical_address must lie in 0..255, got %d" % logical
        )
    user_value = _integer(user_application_value, "user_application_value")
    if user_value < 0 or user_value > 255:
        raise ValueError(
            "user_application_value must lie in 0..255, got %d" % user_value
        )
    return {
        "packet": octets,
        "packet_octets": len(octets),
        "target_spacewire_address": prefix,
        "target_logical_address": logical,
        "user_application_value": user_value,
    }


def categorize_packet_delivery(requested, delivered):
    """Group the delivered packet against the one the service was given."""
    sent = validate_packet(requested, "requested")
    got = validate_packet(delivered, "delivered")
    if sent == got:
        return UNMODIFIED
    if len(got) < len(sent) and sent[: len(got)] == got:
        return TRUNCATED
    if len(got) > len(sent) and got[: len(sent)] == sent:
        return EXTENDED
    return ALTERED


def service_indication(request, delivered_packet, terminator, delivered_user_value=None):
    """The indication the receiving application gets, or None on a discard."""
    if not isinstance(request, dict):
        raise ValueError("request must be a validated service request mapping")
    validate_terminator(terminator)
    if terminator != END_OF_PACKET:
        return None
    octets = validate_packet(delivered_packet, "delivered")
    user_value = (
        request["user_application_value"]
        if delivered_user_value is None
        else _integer(delivered_user_value, "delivered_user_value")
    )
    if user_value < 0 or user_value > 255:
        raise ValueError(
            "delivered_user_value must lie in 0..255, got %d" % user_value
        )
    return {
        "packet": octets,
        "packet_octets": len(octets),
        "user_application_value": user_value,
    }


def boundaries_preserved(requested_lengths, delivered_lengths):
    """True when each packet given arrived as exactly one delivery."""
    for name, lengths in (
        ("requested_lengths", requested_lengths),
        ("delivered_lengths", delivered_lengths),
    ):
        if not isinstance(lengths, (list, tuple)):
            raise ValueError("%s must be a list of octet counts" % name)
        for index, length in enumerate(lengths):
            value = _integer(length, "%s[%d]" % (name, index))
            if value < MIN_PACKET_OCTETS:
                raise ValueError(
                    "%s[%d] is %d octets; a CCSDS packet needs at least %d"
                    % (name, index, value, MIN_PACKET_OCTETS)
                )
    if len(requested_lengths) == 0:
        raise ValueError("requested_lengths must hold at least one packet")
    return tuple(requested_lengths) == tuple(delivered_lengths)


def assess_ccsds_packet_transfer_service(
    request,
    delivered_packet=None,
    terminator=END_OF_PACKET,
    delivered_user_value=None,
    delivered_logical_address=None,
):
    """Full clause 5.2.1 assessment of one use of the transfer service."""
    if not isinstance(request, dict):
        raise ValueError("request must be a validated service request mapping")
    validate_terminator(terminator)

    findings = []
    limitations = []
    category = None

    if terminator != END_OF_PACKET:
        outcome = DISCARDED
        if terminator == ERROR_END_OF_PACKET:
            limitations.append(
                "transfer ended on the error marker; the service discards it "
                "and raises no indication"
            )
        else:
            findings.append(
                "transfer ended with no end marker at all; the packet boundary "
                "was never established"
            )
    else:
        if delivered_packet is None:
            outcome = DISCARDED
            findings.append(
                "transfer ended normally yet no packet was delivered upward"
            )
        else:
            outcome = INDICATED
            category = categorize_packet_delivery(request["packet"], delivered_packet)
            if category == TRUNCATED:
                findings.append(
                    "delivered packet is %d octets against the %d given; the "
                    "service did not deliver it whole"
                    % (len(validate_packet(delivered_packet, "delivered")),
                       request["packet_octets"])
                )
            elif category == EXTENDED:
                findings.append(
                    "delivered packet carries %d octets beyond the %d given; "
                    "the service appended data of its own"
                    % (len(validate_packet(delivered_packet, "delivered"))
                       - request["packet_octets"], request["packet_octets"])
                )
            elif category == ALTERED:
                findings.append(
                    "delivered packet differs from the one given; the service "
                    "did not carry it unmodified"
                )

    if delivered_user_value is not None:
        value = _integer(delivered_user_value, "delivered_user_value")
        if value != request["user_application_value"]:
            findings.append(
                "user application value %d was given, %d was delivered"
                % (request["user_application_value"], value)
            )
    if delivered_logical_address is not None:
        logical = _integer(delivered_logical_address, "delivered_logical_address")
        if logical != request["target_logical_address"]:
            findings.append(
                "target logical address %d was given, %d arrived"
                % (request["target_logical_address"], logical)
            )

    return {
        "request": request,
        "terminator": terminator,
        "outcome": outcome,
        "packet_category": category,
        "findings": findings,
        "limitations": limitations,
        "verdict": "service-met" if outcome == INDICATED and not findings else "service-not-met",
    }

#!/usr/bin/env python3
"""Rejection of erroneous telecommands, ECSS-E-ST-50C clause 5.4.3.

Paraphrased requirement, no standard text reproduced. The clause places one
obligation on the on-board telecommand chain: a telecommand found to be
erroneous is rejected rather than executed. Two things follow that are easy
to lose in an implementation — a rejected command must not be executed in
part, and the rejection has to be visible to the ground.

This module implements the acceptance chain as an ordered set of checks, each
of which can stop the command, with the first failure naming the reason:

  octets + trailing check symbol -> integrity, recomputed not trusted
  declared length vs. octets     -> the packet is self-consistent
  application identifier         -> the destination exists on board
  service and subservice         -> the destination implements the request
  parameter values vs. ranges    -> the request is executable as sent

The result carries the verdict, the first failing check, the execution plan
(which is empty whenever the command is rejected) and the fact that a
rejection report is owed to the ground.

Check symbols are computed with a real CRC over integer octets, so every
comparison is an exact integer comparison with no floating-point behaviour
to differ between hosts.

stdlib only, offline, deterministic.
"""

from __future__ import annotations

# CRC-16-CCITT-FALSE: polynomial, initial value, and the width mask.
CRC16_POLYNOMIAL = 0x1021
CRC16_INITIAL = 0xFFFF
CRC16_MASK = 0xFFFF

# Octets of check symbol carried at the end of a telecommand packet.
CHECK_SYMBOL_OCTETS = 2

# Check tokens, in the order the chain applies them. Order is part of the
# contract: an integrity failure makes every later field untrustworthy, so a
# later check must never be reported as the reason.
INTEGRITY = "integrity-check"
LENGTH = "length-consistency-check"
DESTINATION = "application-identifier-check"
SERVICE = "service-support-check"
PARAMETER = "parameter-range-check"
CHECK_ORDER = (INTEGRITY, LENGTH, DESTINATION, SERVICE, PARAMETER)

ACCEPTED = "accepted"
REJECTED = "rejected"


def _integer(value, name):
    """Return value as an int, refusing bools, floats and text."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    return int(value)


def validate_octets(data, name="octets"):
    """Return a tuple of octets, refusing anything that is not one."""
    if isinstance(data, (bytes, bytearray)):
        return tuple(int(octet) for octet in data)
    if not isinstance(data, (list, tuple)):
        raise ValueError("%s must be octets, got %r" % (name, data))
    result = []
    for index, octet in enumerate(data):
        value = _integer(octet, "%s[%d]" % (name, index))
        if value < 0 or value > 255:
            raise ValueError(
                "%s[%d] must lie in 0..255, got %d" % (name, index, value)
            )
        result.append(value)
    return tuple(result)


def crc16_ccitt(data):
    """Check symbol over a telecommand body, recomputed from the octets."""
    octets = validate_octets(data, "data")
    register = CRC16_INITIAL
    for octet in octets:
        register ^= octet << 8
        for _ in range(8):
            if register & 0x8000:
                register = ((register << 1) ^ CRC16_POLYNOMIAL) & CRC16_MASK
            else:
                register = (register << 1) & CRC16_MASK
    return register & CRC16_MASK


def append_check_symbol(body):
    """Return a body with its freshly computed check symbol appended."""
    octets = validate_octets(body, "body")
    symbol = crc16_ccitt(octets)
    return octets + ((symbol >> 8) & 0xFF, symbol & 0xFF)


def split_check_symbol(packet):
    """Separate a received packet into its body and its trailing symbol."""
    octets = validate_octets(packet, "packet")
    if len(octets) <= CHECK_SYMBOL_OCTETS:
        raise ValueError(
            "packet must carry a body as well as its %d octet check symbol"
            % CHECK_SYMBOL_OCTETS
        )
    body = octets[:-CHECK_SYMBOL_OCTETS]
    symbol = 0
    for octet in octets[-CHECK_SYMBOL_OCTETS:]:
        symbol = (symbol << 8) | octet
    return body, symbol


def check_integrity(packet):
    """True when the trailing check symbol matches the body as received."""
    body, symbol = split_check_symbol(packet)
    return crc16_ccitt(body) == symbol


def check_length(packet, declared_body_octets):
    """True when the declared body size matches the octets that arrived."""
    body, _symbol = split_check_symbol(packet)
    declared = _integer(declared_body_octets, "declared_body_octets")
    if declared < 0:
        raise ValueError("declared_body_octets must not be negative, got %d" % declared)
    return declared == len(body)


def check_destination(application_id, known_application_ids):
    """True when the addressed on-board application exists."""
    identifier = _integer(application_id, "application_id")
    if identifier < 0 or identifier > 0x7FF:
        raise ValueError(
            "application_id must lie in 0..2047, got %d" % identifier
        )
    if not isinstance(known_application_ids, (list, tuple, set, frozenset)):
        raise ValueError("known_application_ids must be a collection")
    return identifier in set(known_application_ids)


def check_service(service, subservice, supported_services):
    """True when the destination implements the requested service."""
    requested = _integer(service, "service")
    sub = _integer(subservice, "subservice")
    if requested < 0 or requested > 255:
        raise ValueError("service must lie in 0..255, got %d" % requested)
    if sub < 0 or sub > 255:
        raise ValueError("subservice must lie in 0..255, got %d" % sub)
    if not isinstance(supported_services, dict):
        raise ValueError("supported_services must be a mapping of service to subservices")
    return sub in set(supported_services.get(requested, ()))


def check_parameters(parameters, ranges):
    """Return the parameters that fall outside the range declared for them."""
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping of name to value")
    if not isinstance(ranges, dict):
        raise ValueError("ranges must be a mapping of name to a low, high pair")
    offenders = []
    for name in sorted(parameters):
        if name not in ranges:
            offenders.append(name)
            continue
        bounds = ranges[name]
        if not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
            raise ValueError("range for %r must be a low, high pair" % name)
        low = _integer(bounds[0], "range low for %s" % name)
        high = _integer(bounds[1], "range high for %s" % name)
        if low > high:
            raise ValueError("range for %r is inverted: %d > %d" % (name, low, high))
        value = _integer(parameters[name], "parameter %s" % name)
        if value < low or value > high:
            offenders.append(name)
    return tuple(offenders)


def first_failing_check(
    packet,
    declared_body_octets,
    application_id,
    known_application_ids,
    service,
    subservice,
    supported_services,
    parameters,
    ranges,
):
    """Name the first check the telecommand fails, or None when it passes all."""
    if not check_integrity(packet):
        return INTEGRITY
    if not check_length(packet, declared_body_octets):
        return LENGTH
    if not check_destination(application_id, known_application_ids):
        return DESTINATION
    if not check_service(service, subservice, supported_services):
        return SERVICE
    if check_parameters(parameters, ranges):
        return PARAMETER
    return None


def assess_telecommand(
    packet,
    declared_body_octets,
    application_id,
    known_application_ids,
    service,
    subservice,
    supported_services,
    parameters,
    ranges,
    execution_steps=(),
):
    """Assess one telecommand against clause 5.4.3 and decide its fate."""
    if not isinstance(execution_steps, (list, tuple)):
        raise ValueError("execution_steps must be a sequence")
    reason = first_failing_check(
        packet,
        declared_body_octets,
        application_id,
        known_application_ids,
        service,
        subservice,
        supported_services,
        parameters,
        ranges,
    )
    offenders = ()
    if reason in (None, PARAMETER):
        offenders = check_parameters(parameters, ranges)

    accepted = reason is None
    return {
        "verdict": ACCEPTED if accepted else REJECTED,
        "accepted": accepted,
        "rejection_reason": reason,
        "checks_before_rejection": CHECK_ORDER[: CHECK_ORDER.index(reason)]
        if reason is not None
        else CHECK_ORDER,
        "out_of_range_parameters": offenders,
        "execution_plan": tuple(execution_steps) if accepted else (),
        "partially_executed": False,
        "rejection_report_owed": not accepted,
    }

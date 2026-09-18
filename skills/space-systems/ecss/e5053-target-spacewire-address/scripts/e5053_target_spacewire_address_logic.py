#!/usr/bin/env python3
"""Target SpaceWire address of a CCSDS transfer PDU, ECSS-E-ST-50-53C 5.1.4.

Paraphrased requirement, no verbatim standard text. The clause obliges the
sending node to put the SpaceWire address of the target node in front of the
CCSDS packet transfer protocol data unit. This module turns that into a
deterministic assessment of a proposed address:

  each leading octet        -> configuration port, path, logical or reserved
  the octet sequence        -> the form of the address, and whether it is well
                               formed at all
  leading path octets       -> the number of routers that will consume one
  address + topology facts  -> findings a sending node can act on

The addressing rule this rests on: a low octet selects an output port of the
next router and is deleted by it, a higher octet names a destination
logically and is left in place, the lowest encoding reaches a router's own
configuration port rather than any attached node, and the highest encoding is
held reserved. stdlib only, offline, deterministic; every value is an integer
octet, so the comparisons are exact on every host.
"""

from __future__ import annotations

CONFIGURATION_PORT_OCTET = 0
PATH_OCTET_MIN = 1
PATH_OCTET_MAX = 31
LOGICAL_OCTET_MIN = 32
LOGICAL_OCTET_MAX = 254
RESERVED_OCTET = 255

CONFIGURATION_PORT = "configuration-port"
PATH = "path"
LOGICAL = "logical"
RESERVED = "reserved"
OCTET_CATEGORIES = (CONFIGURATION_PORT, PATH, LOGICAL, RESERVED)

FORM_EMPTY = "empty"
FORM_PATH = "path"
FORM_LOGICAL = "logical"
FORM_PATH_THEN_LOGICAL = "path-then-logical"
ADDRESS_FORMS = (FORM_EMPTY, FORM_PATH, FORM_LOGICAL, FORM_PATH_THEN_LOGICAL)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    return int(value)


def categorize_address_octet(octet):
    """Group one address octet by the role its encoding gives it."""
    value = _integer(octet, "octet")
    if value < 0 or value > RESERVED_OCTET:
        raise ValueError("octet must lie in 0..%d, got %d" % (RESERVED_OCTET, value))
    if value == CONFIGURATION_PORT_OCTET:
        return CONFIGURATION_PORT
    if PATH_OCTET_MIN <= value <= PATH_OCTET_MAX:
        return PATH
    if LOGICAL_OCTET_MIN <= value <= LOGICAL_OCTET_MAX:
        return LOGICAL
    return RESERVED


def validate_target_spacewire_address(address):
    """Validate the leading address octets and return them as a tuple.

    An empty address is legal: it means the target is reached without any
    routing decision, so nothing is prefixed.
    """
    if isinstance(address, (bytes, bytearray)):
        octets = list(bytearray(address))
    elif isinstance(address, (list, tuple)):
        octets = list(address)
    else:
        raise ValueError(
            "address must be a sequence of octets, got %r" % (address,)
        )
    out = []
    for index, octet in enumerate(octets):
        value = _integer(octet, "address[%d]" % index)
        if value < 0 or value > RESERVED_OCTET:
            raise ValueError(
                "address[%d] must lie in 0..%d, got %d"
                % (index, RESERVED_OCTET, value)
            )
        out.append(value)
    return tuple(out)


def is_empty_address(address):
    """True when nothing is prefixed, i.e. the target needs no routing."""
    return len(validate_target_spacewire_address(address)) == 0


def leading_path_octets(address):
    """How many leading octets a chain of routers will each consume."""
    count = 0
    for octet in validate_target_spacewire_address(address):
        if categorize_address_octet(octet) in (PATH, CONFIGURATION_PORT):
            count += 1
        else:
            break
    return count


def address_form(address):
    """Name the shape of a well-formed address; raise when it is malformed."""
    octets = validate_target_spacewire_address(address)
    if not octets:
        return FORM_EMPTY
    lead = leading_path_octets(octets)
    tail = octets[lead:]
    if not tail:
        return FORM_PATH
    head = categorize_address_octet(tail[0])
    if head == RESERVED:
        raise ValueError(
            "address[%d] uses the reserved encoding %d" % (lead, tail[0])
        )
    if len(tail) > 1:
        raise ValueError(
            "address carries %d octets after the logical octet at position %d; "
            "the logical octet terminates the address" % (len(tail) - 1, lead)
        )
    return FORM_LOGICAL if lead == 0 else FORM_PATH_THEN_LOGICAL


def deliver_hop(address):
    """Remove the leading path octet the way the next router would."""
    octets = validate_target_spacewire_address(address)
    if not octets:
        raise ValueError("an empty address has no octet for a router to consume")
    if categorize_address_octet(octets[0]) not in (PATH, CONFIGURATION_PORT):
        raise ValueError(
            "leading octet %d is not a port selector; a router leaves it in place"
            % octets[0]
        )
    return octets[1:]


def route_trace(address, router_count):
    """Address as seen entering each router, and what finally arrives."""
    octets = validate_target_spacewire_address(address)
    hops = _integer(router_count, "router_count")
    if hops < 0:
        raise ValueError("router_count must not be negative, got %d" % hops)
    trace = [octets]
    current = octets
    for _ in range(hops):
        current = deliver_hop(current)
        trace.append(current)
    return trace


def assess_target_spacewire_address(
    address, directly_attached=False, router_count=None
):
    """Full clause 5.1.4 assessment of a proposed target SpaceWire address."""
    octets = validate_target_spacewire_address(address)
    findings = []
    limitations = []

    form = None
    try:
        form = address_form(octets)
    except ValueError as error:
        findings.append(str(error))

    for index, octet in enumerate(octets):
        if categorize_address_octet(octet) == RESERVED:
            if not any("reserved encoding" in f for f in findings):
                findings.append(
                    "address[%d] uses the reserved encoding %d" % (index, octet)
                )
        if categorize_address_octet(octet) == CONFIGURATION_PORT:
            limitations.append(
                "address[%d] selects a router configuration port, not an "
                "attached node" % index
            )

    hops = leading_path_octets(octets)
    if directly_attached and octets:
        findings.append(
            "target is directly attached yet %d address octet(s) are prefixed"
            % len(octets)
        )
    if not directly_attached and not octets:
        findings.append(
            "target is not directly attached yet no address octets are prefixed"
        )
    if router_count is not None:
        declared = _integer(router_count, "router_count")
        if declared < 0:
            raise ValueError("router_count must not be negative, got %d" % declared)
        if declared != hops:
            findings.append(
                "%d leading port selector(s) for a route through %d router(s)"
                % (hops, declared)
            )

    return {
        "address": octets,
        "form": form,
        "octet_categories": tuple(
            categorize_address_octet(octet) for octet in octets
        ),
        "leading_path_octets": hops,
        "empty": len(octets) == 0,
        "findings": findings,
        "limitations": limitations,
        "verdict": "address-usable" if not findings else "address-rejected",
    }

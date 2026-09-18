#!/usr/bin/env python3
"""Target logical address field, ECSS-E-ST-50-53C clause 5.1.5.

Paraphrased requirement, no verbatim standard text. The clause obliges the
sending node to set the target logical address field of a CCSDS packet
transfer protocol data unit to the logical address of the node the transfer
is for, and to use the default encoding when the installation does not use
logical addressing at all. This module turns that into a deterministic
decision:

  installation policy + target node  -> the value the field must carry
  a received field value             -> assigned, default, or an encoding it
                                        may not take
  value + the receiving node's own
  addresses                          -> deliver the transfer or treat it as
                                        misrouted
  value + the routing prefix         -> whether the two statements of the
                                        destination agree

Unlike the routing prefix, this field is not consumed on the way: what the
sender wrote is what the receiver reads, so a disagreement between them is a
real fault and not an artefact of routing. stdlib only, offline,
deterministic, integer-exact.
"""

from __future__ import annotations

# Encodings below this are held for port selection in a routing prefix and
# are therefore not available to name a node logically.
PATH_RESERVED_MAX = 31

# The encoding used when the installation does not use logical addressing.
DEFAULT_LOGICAL_ADDRESS = 254

ASSIGNED_MIN = 32
ASSIGNED_MAX = DEFAULT_LOGICAL_ADDRESS - 1

# The highest encoding is held reserved and names nothing.
RESERVED_LOGICAL_ADDRESS = 255

ASSIGNED = "assigned"
DEFAULT = "default"
PATH_RESERVED = "path-reserved"
RESERVED = "reserved"
LOGICAL_ADDRESS_CATEGORIES = (ASSIGNED, DEFAULT, PATH_RESERVED, RESERVED)

DELIVER = "deliver"
MISROUTED = "misrouted"
REJECT = "reject"
RECEIVER_ACTIONS = (DELIVER, MISROUTED, REJECT)


def _integer(value, name):
    """Return value as an int, refusing bools, floats and anything else."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    return int(value)


def validate_logical_address(value, name="target_logical_address"):
    """Validate that a value fits the one octet the field provides."""
    octet = _integer(value, name)
    if octet < 0 or octet > RESERVED_LOGICAL_ADDRESS:
        raise ValueError(
            "%s must lie in 0..%d, got %d"
            % (name, RESERVED_LOGICAL_ADDRESS, octet)
        )
    return octet


def categorize_target_logical_address(value):
    """Group one encoding of the field by what it is allowed to mean."""
    octet = validate_logical_address(value)
    if octet <= PATH_RESERVED_MAX:
        return PATH_RESERVED
    if octet == DEFAULT_LOGICAL_ADDRESS:
        return DEFAULT
    if octet == RESERVED_LOGICAL_ADDRESS:
        return RESERVED
    return ASSIGNED


def is_default_logical_address(value):
    """True for the encoding that says logical addressing is not in use."""
    return categorize_target_logical_address(value) == DEFAULT


def is_assignable(value):
    """True when an installation may hand this encoding to a node."""
    return categorize_target_logical_address(value) == ASSIGNED


def validate_node_addresses(addresses):
    """Validate the set of logical addresses one receiving node answers to."""
    if isinstance(addresses, (bytes, bytearray)):
        items = list(bytearray(addresses))
    elif isinstance(addresses, (list, tuple, set, frozenset)):
        items = list(addresses)
    else:
        raise ValueError(
            "node_addresses must be a collection of octets, got %r" % (addresses,)
        )
    out = set()
    for index, item in enumerate(sorted(items)):
        octet = validate_logical_address(item, "node_addresses[%d]" % index)
        if not is_assignable(octet):
            raise ValueError(
                "node_addresses[%d] = %d is not an assignable logical address"
                % (index, octet)
            )
        out.add(octet)
    return frozenset(out)


def resolve_target_logical_address(node_logical_address, logical_addressing_in_use=True):
    """The value the sending node must write into the field."""
    if not isinstance(logical_addressing_in_use, bool):
        raise ValueError("logical_addressing_in_use must be a boolean")
    if not logical_addressing_in_use:
        return DEFAULT_LOGICAL_ADDRESS
    octet = validate_logical_address(node_logical_address, "node_logical_address")
    if not is_assignable(octet):
        raise ValueError(
            "node_logical_address %d is not an assignable logical address" % octet
        )
    return octet


def receiver_action(value, node_addresses=(), accept_default=True):
    """What a receiving node does with a transfer carrying this field value."""
    octet = validate_logical_address(value)
    category = categorize_target_logical_address(octet)
    if category in (PATH_RESERVED, RESERVED):
        return REJECT
    if category == DEFAULT:
        return DELIVER if accept_default else REJECT
    return DELIVER if octet in validate_node_addresses(node_addresses) else MISROUTED


def cross_check_with_route_prefix(value, prefix_logical_octet):
    """Compare the field against the logical octet a routing prefix ended on."""
    octet = validate_logical_address(value)
    if prefix_logical_octet is None:
        return None
    prefix = validate_logical_address(prefix_logical_octet, "prefix_logical_octet")
    return octet == prefix


def assess_target_logical_address(
    value,
    node_addresses=(),
    accept_default=True,
    prefix_logical_octet=None,
    logical_addressing_in_use=True,
):
    """Full clause 5.1.5 assessment of a received target logical address."""
    octet = validate_logical_address(value)
    category = categorize_target_logical_address(octet)
    action = receiver_action(octet, node_addresses, accept_default)
    agreement = cross_check_with_route_prefix(octet, prefix_logical_octet)

    findings = []
    limitations = []

    if category == PATH_RESERVED:
        findings.append(
            "field carries %d, an encoding held for routing prefix port "
            "selection and not available to name a node" % octet
        )
    elif category == RESERVED:
        findings.append("field carries the reserved encoding %d" % octet)
    elif category == DEFAULT:
        if logical_addressing_in_use:
            findings.append(
                "field carries the default encoding %d while the installation "
                "uses logical addressing" % (octet,)
            )
        else:
            limitations.append(
                "field carries the default encoding; the transfer names no "
                "particular node"
            )
        if not accept_default:
            findings.append(
                "receiving node does not accept the default encoding %d" % octet
            )
    elif action == MISROUTED:
        findings.append(
            "field names logical address %d, which this node does not answer to"
            % octet
        )

    if agreement is False:
        findings.append(
            "field names logical address %d but the routing prefix ended on %d"
            % (octet, validate_logical_address(prefix_logical_octet))
        )

    return {
        "target_logical_address": octet,
        "category": category,
        "receiver_action": action,
        "prefix_agreement": agreement,
        "findings": findings,
        "limitations": limitations,
        "verdict": "deliver" if action == DELIVER and not findings else "hold",
    }

#!/usr/bin/env python3
"""Target logical address field of a packet transfer protocol data unit.

Anchor: ECSS-E-ST-50-53C clause 5.3.2. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

A protocol data unit handed to the link layer opens with destination
addressing. Everything ahead of the protocol identifier is address: zero
or more path-address octets that the routers consume hop by hop, then a
single target logical address octet that survives to the destination
node and names it.

Address octet space, as this module categorizes it
    path-address        an octet low enough to be eaten by a router port
    assigned-logical    an address a node can be given in the registry
    default-logical     the address a node answers to before one is set
    reserved-logical    the top of the space, not available to a node

The one decision this clause forces is which octet is written there: the
registered address of the destination node, or the default address where
the node has not been given one. Standard library only, offline,
deterministic.
"""

from __future__ import annotations

PATH_ADDRESS_MAX = 31
LOGICAL_ADDRESS_MIN = 32
LOGICAL_ADDRESS_MAX = 254
DEFAULT_LOGICAL_ADDRESS = 254
RESERVED_LOGICAL_ADDRESS = 255
OCTET_MAX = 255

PATH_ADDRESS = "path-address"
ASSIGNED_LOGICAL_ADDRESS = "assigned-logical-address"
DEFAULT_LOGICAL = "default-logical-address"
RESERVED_LOGICAL = "reserved-logical-address"

ADDRESS_CATEGORIES = (
    PATH_ADDRESS,
    ASSIGNED_LOGICAL_ADDRESS,
    DEFAULT_LOGICAL,
    RESERVED_LOGICAL,
)

REGISTRY_SOURCE = "node-registry"
DEFAULT_SOURCE = "default-address-fallback"


def _require_octet(name, value):
    """One unsigned octet, rejecting bools and anything out of range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer octet, got %r" % (name, value))
    if value < 0 or value > OCTET_MAX:
        raise ValueError(
            "%s must lie in 0..%d, got %d" % (name, OCTET_MAX, value)
        )
    return value


def categorize_address(value):
    """Say which part of the address space an octet falls in."""
    _require_octet("address octet", value)
    if value <= PATH_ADDRESS_MAX:
        return PATH_ADDRESS
    if value == RESERVED_LOGICAL_ADDRESS:
        return RESERVED_LOGICAL
    if value == DEFAULT_LOGICAL_ADDRESS:
        return DEFAULT_LOGICAL
    return ASSIGNED_LOGICAL_ADDRESS


def is_logical_address(value):
    """True where the octet can stand as a target logical address."""
    return categorize_address(value) in (
        ASSIGNED_LOGICAL_ADDRESS,
        DEFAULT_LOGICAL,
    )


def validate_target_logical_address(value):
    """Grade one candidate octet for the target logical address field."""
    category = categorize_address(value)
    findings = []
    if category == PATH_ADDRESS:
        findings.append(
            "octet %d sits in the path-address range and is consumed by the "
            "first router it meets, so it never reaches a destination node"
            % value
        )
    elif category == RESERVED_LOGICAL:
        findings.append(
            "octet %d is reserved at the top of the address space and cannot "
            "be given to a node" % value
        )
    elif category == DEFAULT_LOGICAL:
        findings.append(
            "octet %d is the default address, so the unit reaches whichever "
            "node has not been given an address of its own" % value
        )
    return {
        "value": value,
        "category": category,
        "usable": category in (ASSIGNED_LOGICAL_ADDRESS, DEFAULT_LOGICAL),
        "findings": findings,
    }


def resolve_target_logical_address(destination_node, registry, allow_default=True):
    """Pick the octet to write for a named destination node."""
    if not isinstance(registry, dict):
        raise ValueError("registry must be a mapping, got %r" % (registry,))
    if not isinstance(destination_node, str) or not destination_node:
        raise ValueError(
            "destination_node must be a non-empty name, got %r" % (destination_node,)
        )
    if destination_node not in registry:
        raise ValueError(
            "destination node %r is absent from the registry" % destination_node
        )
    declared = registry[destination_node]
    findings = []
    if declared is None:
        if not allow_default:
            raise ValueError(
                "node %r has no registered address and the default address "
                "was not permitted" % destination_node
            )
        findings.append(
            "node %r carries no registered address; the default address %d is "
            "written instead and only one such node may sit on the network"
            % (destination_node, DEFAULT_LOGICAL_ADDRESS)
        )
        return {
            "target_logical_address": DEFAULT_LOGICAL_ADDRESS,
            "source": DEFAULT_SOURCE,
            "findings": findings,
        }
    _require_octet("registered address of %r" % destination_node, declared)
    if not is_logical_address(declared):
        raise ValueError(
            "node %r is registered at octet %d, which is not a logical address"
            % (destination_node, declared)
        )
    return {
        "target_logical_address": declared,
        "source": REGISTRY_SOURCE,
        "findings": findings,
    }


def encode_address_prefix(target_logical_address, path_addresses=()):
    """Build the leading octets: path bytes first, then the target address."""
    try:
        path = list(path_addresses)
    except TypeError:
        raise ValueError(
            "path_addresses must be a sequence, got %r" % (path_addresses,)
        )
    encoded = []
    for index, octet in enumerate(path):
        _require_octet("path address %d" % index, octet)
        if octet > PATH_ADDRESS_MAX:
            raise ValueError(
                "path address %d is octet %d, which a router would keep as a "
                "logical address instead of consuming" % (index, octet)
            )
        encoded.append(octet)
    _require_octet("target_logical_address", target_logical_address)
    if not is_logical_address(target_logical_address):
        raise ValueError(
            "target_logical_address %d is not a logical address"
            % target_logical_address
        )
    encoded.append(target_logical_address)
    return tuple(encoded)


def decode_address_prefix(octets):
    """Split a received unit into its path bytes and its target address."""
    try:
        data = list(octets)
    except TypeError:
        raise ValueError("octets must be a sequence, got %r" % (octets,))
    if not data:
        raise ValueError("an empty unit carries no target logical address")
    path = []
    for index, octet in enumerate(data):
        _require_octet("octet %d" % index, octet)
        if categorize_address(octet) == PATH_ADDRESS:
            path.append(octet)
            continue
        return {
            "path_addresses": tuple(path),
            "target_logical_address": octet,
            "remainder_offset": index + 1,
        }
    raise ValueError(
        "every octet lies in the path-address range; the unit has no target "
        "logical address"
    )


def assess_target_logical_address_field(case):
    """Full clause 5.3.2 decision for one addressing case."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    registry = case.get("registry")
    node = case.get("destination_node")
    resolved = resolve_target_logical_address(
        node, registry, allow_default=case.get("allow_default", True)
    )
    address = resolved["target_logical_address"]
    graded = validate_target_logical_address(address)
    prefix = encode_address_prefix(address, case.get("path_addresses", ()))
    findings = list(resolved["findings"]) + list(graded["findings"])
    return {
        "target_logical_address": address,
        "category": graded["category"],
        "source": resolved["source"],
        "address_prefix": prefix,
        "path_length": len(prefix) - 1,
        "usable": graded["usable"],
        "verdict": "address-field-set" if graded["usable"] else "address-field-invalid",
        "findings": findings,
    }

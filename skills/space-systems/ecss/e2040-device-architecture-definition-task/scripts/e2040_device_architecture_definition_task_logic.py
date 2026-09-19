#!/usr/bin/env python3
"""Device architecture definition task (ECSS-E-ST-20-40C clause 5.3.2).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
The task is to decide the device's internal architecture and write it
down so the rest of the programme can work against it. An architecture
is not a picture: it is blocks, the partitions those blocks are placed
in, the interfaces between them, the requirements allocated onto them
and the resources they consume. The checks worth running are the ones
that cross those five.

* every block sits in a declared partition. A block outside the
  partitioning has no separation argument behind it;
* a partition may carry only one design assurance level unless the
  architecture declares mixed criticality for it explicitly. Mixing by
  accident is the defect that survives to qualification;
* an interface names two blocks that exist, and names two DIFFERENT
  blocks. A dangling endpoint reads as a connection on the diagram and
  is nothing in the design;
* every requirement is allocated to a block that exists, and every
  block carries at least one requirement. A block nothing was allocated
  to is either unjustified hardware or a missing allocation, and both
  are worth surfacing;
* resources roll up per partition and across the device, and the
  rollup is compared against a budget. A rollup that lands exactly on
  its budget is within budget, so the comparison absorbs representation
  error rather than failing on the last bit of a sum.
"""

import math

# Resources the architecture rolls up.
RESOURCES = ("power_w", "mass_g", "area_mm2")

# Design assurance levels, most demanding first.
ASSURANCE_LEVELS = ("A", "B", "C", "D")

_LEVEL_ALIASES = {
    "a": "A",
    "level a": "A",
    "dal a": "A",
    "b": "B",
    "level b": "B",
    "dal b": "B",
    "c": "C",
    "level c": "C",
    "dal c": "C",
    "d": "D",
    "level d": "D",
    "dal d": "D",
}

REL_TOL = 1e-12
ABS_TOL = 1e-15

_ARCH_REQUIRED_KEYS = ("blocks", "interfaces", "allocations")
_ARCH_OPTIONAL_KEYS = ("partitions", "budgets")
_BLOCK_KEYS = ("id", "function", "partition", "assurance", "resources")
_INTERFACE_KEYS = ("id", "endpoints", "protocol", "direction")
_ALLOCATION_KEYS = ("requirement", "block")
_PARTITION_KEYS = ("name", "mixed_criticality", "rationale")

DIRECTIONS = ("unidirectional", "bidirectional")
_DIRECTION_ALIASES = {
    "unidirectional": "unidirectional",
    "one way": "unidirectional",
    "simplex": "unidirectional",
    "bidirectional": "bidirectional",
    "two way": "bidirectional",
    "duplex": "bidirectional",
}


def _text(name, value, allow_empty=False):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    out = value.strip()
    if not out and not allow_empty:
        raise ValueError("%s must be a non-empty string" % name)
    return out


def _key(name, value):
    return " ".join(_text(name, value).lower().replace("_", " ").split())


def _amount(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if out < 0.0:
        raise ValueError("%s cannot be negative, got %g" % (name, out))
    return out


def normalize_assurance(value):
    """Fold a design assurance level onto A, B, C or D."""
    key = _key("assurance", value)
    if key in _LEVEL_ALIASES:
        return _LEVEL_ALIASES[key]
    raise ValueError(
        "unknown assurance level %r; use one of %s"
        % (value, ", ".join(ASSURANCE_LEVELS))
    )


def assurance_rank(value):
    """Ordinal of an assurance level; A is the most demanding, rank 0."""
    return ASSURANCE_LEVELS.index(normalize_assurance(value))


def normalize_direction(value):
    """Fold an interface direction onto unidirectional or bidirectional."""
    key = _key("direction", value)
    if key in _DIRECTION_ALIASES:
        return _DIRECTION_ALIASES[key]
    raise ValueError(
        "unknown interface direction %r; use one of %s" % (value, ", ".join(DIRECTIONS))
    )


def validate_resources(mapping, where="resources"):
    """Check a resource mapping and return every resource, zero-filled."""
    if mapping is None:
        return {name: 0.0 for name in RESOURCES}
    if not isinstance(mapping, dict):
        raise ValueError("%s must be a mapping" % where)
    unknown = sorted(set(mapping) - set(RESOURCES))
    if unknown:
        raise ValueError("%s names unknown resources: %s" % (where, ", ".join(unknown)))
    return {
        name: _amount("%s.%s" % (where, name), mapping.get(name, 0.0))
        for name in RESOURCES
    }


def validate_partitions(entries):
    """Check the declared partitions and return them keyed by name."""
    if entries is None:
        return {}
    if not isinstance(entries, (list, tuple)):
        raise ValueError("partitions must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("partitions[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_PARTITION_KEYS))
        if unknown:
            raise ValueError(
                "partitions[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        if "name" not in entry:
            raise ValueError("partitions[%d] missing key: name" % index)
        name = _text("partitions[%d].name" % index, entry["name"])
        if name in resolved:
            raise ValueError("duplicate partition %r" % name)
        mixed = entry.get("mixed_criticality", False)
        if not isinstance(mixed, bool):
            raise ValueError("partitions[%d].mixed_criticality must be true or false" % index)
        resolved[name] = {
            "name": name,
            "mixed_criticality": mixed,
            "rationale": _text(
                "partitions[%d].rationale" % index,
                entry.get("rationale", ""),
                allow_empty=True,
            ),
        }
    return resolved


def validate_blocks(entries):
    """Check the block list and return it keyed by block identifier."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("blocks must be a list")
    resolved = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("blocks[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_BLOCK_KEYS))
        if unknown:
            raise ValueError("blocks[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
        for key in ("id", "function"):
            if key not in entry:
                raise ValueError("blocks[%d] missing key: %s" % (index, key))
        block_id = _text("blocks[%d].id" % index, entry["id"])
        if block_id in resolved:
            raise ValueError("duplicate block id %r" % block_id)
        assurance = entry.get("assurance")
        resolved[block_id] = {
            "id": block_id,
            "function": _text("blocks[%d].function" % index, entry["function"]),
            "partition": _text(
                "blocks[%d].partition" % index, entry.get("partition", ""), allow_empty=True
            ),
            "assurance": normalize_assurance(assurance) if assurance else "",
            "resources": validate_resources(
                entry.get("resources"), "blocks[%d].resources" % index
            ),
        }
    return resolved


def validate_interfaces(entries):
    """Check the interface list and return it resolved in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("interfaces must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("interfaces[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_INTERFACE_KEYS))
        if unknown:
            raise ValueError(
                "interfaces[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in ("id", "endpoints"):
            if key not in entry:
                raise ValueError("interfaces[%d] missing key: %s" % (index, key))
        iface_id = _text("interfaces[%d].id" % index, entry["id"])
        if iface_id in seen:
            raise ValueError("duplicate interface id %r" % iface_id)
        seen.add(iface_id)
        endpoints = entry["endpoints"]
        if not isinstance(endpoints, (list, tuple)) or len(endpoints) != 2:
            raise ValueError("interfaces[%d].endpoints must name exactly two blocks" % index)
        pair = tuple(
            _text("interfaces[%d].endpoints[%d]" % (index, side), endpoints[side])
            for side in (0, 1)
        )
        if pair[0] == pair[1]:
            raise ValueError(
                "interface %r connects block %r to itself" % (iface_id, pair[0])
            )
        direction = entry.get("direction")
        resolved.append(
            {
                "id": iface_id,
                "endpoints": pair,
                "protocol": _text(
                    "interfaces[%d].protocol" % index,
                    entry.get("protocol", ""),
                    allow_empty=True,
                ),
                "direction": normalize_direction(direction) if direction else "",
            }
        )
    return resolved


def validate_allocations(entries):
    """Check the requirement allocations and return them in declared order."""
    if not isinstance(entries, (list, tuple)):
        raise ValueError("allocations must be a list")
    resolved = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError("allocations[%d] must be a mapping" % index)
        unknown = sorted(set(entry) - set(_ALLOCATION_KEYS))
        if unknown:
            raise ValueError(
                "allocations[%d] has unknown keys: %s" % (index, ", ".join(unknown))
            )
        for key in _ALLOCATION_KEYS:
            if key not in entry:
                raise ValueError("allocations[%d] missing key: %s" % (index, key))
        requirement = _text("allocations[%d].requirement" % index, entry["requirement"])
        block = _text("allocations[%d].block" % index, entry["block"])
        pair = (requirement, block)
        if pair in seen:
            raise ValueError(
                "requirement %r is allocated to block %r twice" % (requirement, block)
            )
        seen.add(pair)
        resolved.append({"requirement": requirement, "block": block})
    return resolved


def partition_membership(blocks):
    """Block identifiers grouped by the partition they sit in."""
    grouped = {}
    for block_id in sorted(blocks):
        name = blocks[block_id]["partition"]
        if name:
            grouped.setdefault(name, []).append(block_id)
    return grouped


def resource_rollup(blocks, block_ids=None):
    """Sum every resource across the named blocks, or across all of them."""
    chosen = sorted(blocks) if block_ids is None else sorted(block_ids)
    totals = {name: 0.0 for name in RESOURCES}
    for block_id in chosen:
        if block_id not in blocks:
            raise ValueError("unknown block %r in rollup" % block_id)
        for name in RESOURCES:
            totals[name] += blocks[block_id]["resources"][name]
    return totals


def within_budget(used, budget):
    """True when a rollup sits at or under its budget, exact landings included."""
    used = _amount("used", used)
    budget = _amount("budget", budget)
    return used < budget or math.isclose(used, budget, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def utilisation(used, budget):
    """Fraction of a budget a rollup consumes."""
    used = _amount("used", used)
    budget = _amount("budget", budget)
    if budget == 0.0:
        raise ValueError("budget must be greater than zero to compute utilisation")
    return used / budget


def define_device_architecture(architecture):
    """Full clause 5.3.2 assessment of one device architecture definition.

    Returns the resolved blocks, partition membership, resource rollup and
    findings, together with the verdict on whether the architecture is
    documented well enough to work against.
    """
    if not isinstance(architecture, dict):
        raise ValueError("architecture must be a mapping of blocks, interfaces and allocations")
    known = set(_ARCH_REQUIRED_KEYS) | set(_ARCH_OPTIONAL_KEYS)
    unknown = sorted(set(architecture) - known)
    if unknown:
        raise ValueError("unknown architecture keys: %s" % ", ".join(unknown))
    missing = [key for key in _ARCH_REQUIRED_KEYS if key not in architecture]
    if missing:
        raise ValueError("architecture missing required keys: %s" % ", ".join(missing))

    blocks = validate_blocks(architecture["blocks"])
    if not blocks:
        raise ValueError("architecture must declare at least one block")
    interfaces = validate_interfaces(architecture["interfaces"])
    allocations = validate_allocations(architecture["allocations"])
    partitions = validate_partitions(architecture.get("partitions"))
    budgets = validate_resources(architecture.get("budgets"), "budgets") if architecture.get(
        "budgets"
    ) else None

    findings = []

    for block_id in sorted(blocks):
        block = blocks[block_id]
        if not block["partition"]:
            findings.append(
                {
                    "code": "block-outside-partitioning",
                    "block": block_id,
                    "detail": "block %s sits in no declared partition, so it carries no "
                    "separation argument" % block_id,
                }
            )
        elif partitions and block["partition"] not in partitions:
            findings.append(
                {
                    "code": "block-in-undeclared-partition",
                    "block": block_id,
                    "partition": block["partition"],
                    "detail": "block %s names partition %r, which the architecture does "
                    "not declare" % (block_id, block["partition"]),
                }
            )

    membership = partition_membership(blocks)
    for name in sorted(membership):
        levels = sorted({blocks[b]["assurance"] for b in membership[name] if blocks[b]["assurance"]})
        if len(levels) > 1:
            declared = partitions.get(name, {}).get("mixed_criticality", False)
            if not declared:
                findings.append(
                    {
                        "code": "partition-mixes-assurance-levels",
                        "partition": name,
                        "levels": levels,
                        "detail": "partition %s carries levels %s with no mixed "
                        "criticality declared for it" % (name, ", ".join(levels)),
                    }
                )

    for interface in interfaces:
        for side in interface["endpoints"]:
            if side not in blocks:
                findings.append(
                    {
                        "code": "interface-endpoint-not-a-block",
                        "interface": interface["id"],
                        "endpoint": side,
                        "detail": "interface %s names %r, which is not a declared block"
                        % (interface["id"], side),
                    }
                )
        if not interface["protocol"]:
            findings.append(
                {
                    "code": "interface-without-protocol",
                    "interface": interface["id"],
                    "detail": "interface %s names no protocol, so it cannot be "
                    "implemented from the architecture alone" % interface["id"],
                }
            )

    connected = set()
    for interface in interfaces:
        connected.update(interface["endpoints"])
    if len(blocks) > 1:
        for block_id in sorted(blocks):
            if block_id not in connected:
                findings.append(
                    {
                        "code": "block-without-interface",
                        "block": block_id,
                        "detail": "block %s connects to nothing in a multi-block device"
                        % block_id,
                    }
                )

    allocated_blocks = {a["block"] for a in allocations}
    for allocation in allocations:
        if allocation["block"] not in blocks:
            findings.append(
                {
                    "code": "allocation-to-unknown-block",
                    "requirement": allocation["requirement"],
                    "block": allocation["block"],
                    "detail": "requirement %s is allocated to %r, which is not a "
                    "declared block" % (allocation["requirement"], allocation["block"]),
                }
            )
    for block_id in sorted(blocks):
        if block_id not in allocated_blocks:
            findings.append(
                {
                    "code": "block-without-allocated-requirement",
                    "block": block_id,
                    "detail": "block %s carries no allocated requirement, so nothing "
                    "justifies it" % block_id,
                }
            )

    rollup = resource_rollup(blocks)
    over_budget = []
    if budgets is not None:
        for name in RESOURCES:
            if budgets[name] > 0.0 and not within_budget(rollup[name], budgets[name]):
                over_budget.append(name)
                findings.append(
                    {
                        "code": "resource-rollup-over-budget",
                        "resource": name,
                        "used": rollup[name],
                        "budget": budgets[name],
                        "detail": "%s rolls up to %g against a %g budget"
                        % (name, rollup[name], budgets[name]),
                    }
                )

    return {
        "blocks": blocks,
        "partition_membership": membership,
        "interface_count": len(interfaces),
        "allocation_count": len(allocations),
        "resource_rollup": rollup,
        "over_budget_resources": over_budget,
        "findings": findings,
        "documented": not findings,
    }

#!/usr/bin/env python3
"""ARP4754A requirements allocation logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4754a): system
requirements are allocated to items and functions so that each design
element owns a defined requirement set. The allocation register maps
every requirement id to one item; review checks coverage (no
unallocated requirements), uniqueness (no requirement on two items),
and groups the register per item for the item development handoff.
"""


class AllocationConflictError(ValueError):
    """A requirement is already allocated to a different item."""


def allocate(register, req_id, item):
    """Record req_id to item; a conflicting allocation raises."""
    prev = register.get(req_id)
    if prev is not None and prev != item:
        raise AllocationConflictError(
            "requirement %r already allocated to %r" % (req_id, prev)
        )
    register[req_id] = item
    return register


def coverage(register, requirement_ids):
    """(allocated_ids, unallocated_ids, ratio) over the requirement set."""
    allocated = [r for r in requirement_ids if r in register]
    unallocated = [r for r in requirement_ids if r not in register]
    ratio = len(allocated) / len(requirement_ids) if requirement_ids else 1.0
    return sorted(allocated), sorted(unallocated), ratio


def unallocated_requirements(register, requirement_ids):
    """Requirement ids with no allocation in the register."""
    return sorted(r for r in requirement_ids if r not in register)


def requirements_by_item(register, item):
    """Requirement ids allocated to one item, sorted."""
    return sorted(req for req, it in register.items() if it == item)


def group_by_item(register):
    """Register grouped per item with sorted requirement id lists."""
    out = {}
    for req, item in register.items():
        out.setdefault(item, []).append(req)
    return {item: sorted(reqs) for item, reqs in out.items()}


def validate_items(register, known_items):
    """Every item in the register must exist in the design breakdown."""
    for item in set(register.values()):
        if item not in known_items:
            raise ValueError("unknown item: %r" % (item,))
    return True

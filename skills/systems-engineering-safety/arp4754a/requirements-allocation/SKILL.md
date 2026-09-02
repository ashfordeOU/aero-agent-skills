---
name: requirements-allocation
description: "Use when you must allocate system requirements to items and functions per ARP4754A development planning: assign each system requirement to a design item or function, check the allocation coverage to find the unallocated requirements, detect a requirement allocated to more than one item, and group the allocated requirements per item for the item development handoff. Produces the allocation register, the unallocated list, and the double allocation verdict that gate the handoff of requirements to item level development. Trigger: requirements allocation, allocation coverage, item allocation, unallocated requirements, allocate system requirements to items."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: arp4754a
  tags: [requirements-allocation, allocation-coverage, item-allocation, unallocated-requirements, allocation-conflict, arp4754a]
  version: 0.1.0
  author: Aero Agent Skills
---

# Requirements Allocation (systems-engineering-safety/arp4754a/requirements-allocation)

Use when the task is ARP4754A requirements allocation: assigning
system requirements to items and functions, checking allocation
coverage, and grouping the register for item level development.

## Domain quick reference

- System requirements are allocated to items and functions so each
  design element owns a defined requirement set.
- The allocation register maps every requirement id to one item.
- Coverage review finds the unallocated requirements and the share of
  the requirement set that is allocated.
- A requirement must map to exactly one item; a second allocation is a
  conflict.
- The grouped register per item supports the item development handoff.

## Workflow

1. Collect the requirement ids and the design items and functions.
2. Allocate each system requirement to one item.
3. Check the allocation coverage and list the unallocated requirements.
4. Detect any requirement allocated to more than one item.
5. Group the register per item and gate the item development handoff.

## Pitfalls

- Allocating the same requirement to two items; the register allows
  only one allocation per requirement.
- Scoring coverage without the full requirement id set; the ratio is
  only valid over the complete list.
- Assigning a requirement to an item that is not in the design
  breakdown; the item must exist.
- Reusing an allocation register across programs without clearing it.

## Behavior contract (gate 3)

The allocation and coverage logic is exercised by the gate 3 contract
test: scripts/test_requirements_allocation.py against
scripts/requirements_allocation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_requirements_allocation.py

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); summary-only per standards-map.yaml. Allocation to items is
  common development methodology.
- compliance: STANDARDS-REF, gated: false.

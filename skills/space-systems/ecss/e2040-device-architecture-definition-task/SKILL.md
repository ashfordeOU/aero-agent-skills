---
name: e2040-device-architecture-definition-task
description: "Define and document the internal architecture and partitioning chosen for a device, the task ECSS-E-ST-20-40C clause 5.3.2 sets: place every block in a declared partition, refuse a partition that mixes assurance levels unless mixed criticality is declared for it, require both interface endpoints to name real and different blocks, allocate every requirement onto a block that exists, and roll resources up against the device budget. Use when a device architecture is first written down, or when a partitioning argument is reviewed before detailed design. Trigger: ecss, e-st-20-electrical-scope, device-architecture-definition-task, device-block-partitioning, partition-assurance-level-mixing, device-interface-endpoint-integrity, device-resource-rollup-budget."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-electrical-scope, e2040-device-architecture-definition-task, device-architecture-definition-task, device-block-partitioning, partition-assurance-level-mixing, device-interface-endpoint-integrity, device-resource-rollup-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Architecture Definition Task (space-systems/ecss/e2040-device-architecture-definition-task)

Use when the task is the design duty of ECSS-E-ST-20-40C clause 5.3.2 --
deciding the device's internal architecture and writing it down well
enough that detailed design, verification and the budgets can all be
worked against it.

## Domain quick reference

- An architecture is five things at once: blocks, the partitions those
  blocks sit in, the interfaces between them, the requirements allocated
  onto them, and the resources they consume. Every check worth running
  crosses two of the five; none of them fires inside one alone.
- A block in no declared partition carries no separation argument. It
  looks complete on the diagram and has nothing behind it at
  qualification.
- A partition carrying two assurance levels is a defect unless mixed
  criticality was declared for that partition deliberately. Mixing by
  accident survives every later review because each block is individually
  reasonable.
- An interface names two blocks that exist and two blocks that differ. A
  dangling endpoint reads as a connection and is nothing; a self-loop is
  an input defect rather than a finding.
- An interface with no protocol cannot be implemented from the
  architecture, so the next team invents one and the two ends disagree.
- A requirement allocated to a block that does not exist is a broken
  trace. A block nothing was allocated to is unjustified hardware or a
  missing allocation, and both are worth surfacing at this point rather
  than at the architecture review.
- Resource rollups are sums of floats. A rollup landing exactly on its
  budget is within budget, so the comparison absorbs representation error
  instead of failing on the last bit of the sum.

## Workflow

1. Resolve blocks by identifier, refusing a repeat or an unknown key, and
   zero-fill any resource a block does not declare.
2. Resolve the declared partitions and report every block sitting in none
   of them, or naming one that was never declared.
3. Group blocks by partition and report a partition carrying more than
   one assurance level without mixed criticality declared for it.
4. Resolve the interfaces, refusing a self-loop or an endpoint list that
   is not exactly two, and report an endpoint naming no declared block
   and an interface naming no protocol.
5. Report any block connected to nothing while the device has more than
   one block.
6. Resolve the allocations, report one pointing at an unknown block, and
   report every block carrying no allocated requirement.
7. Roll resources up across the device and compare each against its
   budget, absorbing representation error at the boundary.

## Pitfalls

- Checking the block list on its own. Blocks are always individually
  sensible; the defects live in the partition they were placed in and the
  interface that names them.
- Letting two assurance levels share a partition because both blocks
  passed their own review. The separation argument is a property of the
  partition, and nothing below it can detect the mixing.
- Accepting an interface endpoint without resolving it against the block
  list. The diagram renders, the trace is broken, and the mismatch
  surfaces when two teams integrate.
- Dropping blocks with no allocated requirement. They are the cheapest
  thing to remove now and the most expensive to justify at qualification.
- Comparing a float rollup against its budget with a strict inequality.
  A 1.5 and a 2.5 summing against a 4.0 budget can land a unit in the
  last place over it and red an architecture that is exactly on budget.

## Behavior contract (gate 3)

The block and partition resolution, assurance-level mixing detection,
interface endpoint integrity, protocol presence, allocation resolution,
unjustified-block detection and the resource rollup against budget are
exercised by the gate 3 contract test:
scripts/test_e2040_device_architecture_definition_task.py against
scripts/e2040_device_architecture_definition_task_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2040_device_architecture_definition_task.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

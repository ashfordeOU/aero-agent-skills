---
name: e2007-system-grounding-diagram
description: "Use when verify that the system-grounding-diagram demanded by ECSS-E-ST-20-07C clause 4.2.10.2 really describes the flight-segment and the ground-support-equipment as one traceable topology: categorize every unit as single-point-grounded, multipoint-grounded or deliberately-isolated, trace each unit back to the declared vehicle-ground-reference, compute the lowest-resistance return path and compare it with the path allowance, detect ground-loops closed by redundant structure-bonds inside a single-point-grounded domain, and confirm the ground-support-equipment reaches the vehicle reference through exactly one designated umbilical-ground-interface instead of a second facility-earth crossing. Trigger: system-grounding-diagram, grounding-architecture, ground-support-equipment-grounding, single-point-grounding, multipoint-grounding, ground-loop-detection, umbilical-ground-interface, vehicle-ground-reference, return-path-resistance."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-system-grounding-diagram, grounding-architecture, ground-support-equipment-grounding, single-point-grounding, ground-loop-detection, umbilical-ground-interface, vehicle-ground-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility -- System Grounding Diagram (space-systems/ecss/e2007-system-grounding-diagram)

Use when the task is the grounding-architecture deliverable of
ECSS-E-ST-20-07C clause 4.2.10.2 -- a single diagram that carries both
the flight-segment grounding topology and the ground-support-equipment
that will be mated to it, checked for traceable return paths, absent
ground-loops and a single designated domain crossing.

## Domain quick reference

- The clause anchors on one artefact, not two: the diagram is only
  complete when the ground-support-equipment appears on it. A diagram
  that stops at the launch-vehicle interface leaves the trolley,
  checkout rack and umbilical outside the analysed topology, which is
  exactly where an unintended second earth path is introduced.
- Every unit carries exactly one grounding category. A
  single-point-grounded unit returns through one deliberate conductor
  to the vehicle-ground-reference. A multipoint-grounded unit is bonded
  to structure at every mounting foot, which is accepted where return
  currents are high-frequency and a single conductor would be
  inductive. A deliberately-isolated unit floats: it is mounted through
  mounting-isolators and referenced only through its interface
  circuits, so a conductive path from it to the reference is a defect,
  not a margin.
- Links carry a category too -- structure-bond,
  dedicated-ground-conductor, shield-return, umbilical-ground-interface
  and mounting-isolator. Only the first four conduct. A
  mounting-isolator is drawn precisely so a reader can see that the
  isolation is intentional rather than a forgotten bond.
- Return-path allowances used at diagram level: 10 milliohm for a
  single-point-grounded unit's return, 2.5 milliohm for a
  multipoint-grounded bond. These bound the summed resistance of the
  lowest-resistance path, not one strap.
- Ground-support-equipment coverage is satisfied when exactly one
  conductive link crosses the flight-segment / ground-support-equipment
  boundary and that link is the designated umbilical-ground-interface.
  A second crossing -- typically a facility-earth strap at the trolley
  in addition to the umbilical -- closes a loop through facility earth
  that no flight-side analysis covers.
- Independent loop count for a set of nodes is edges - nodes +
  connected-components over the conductive subgraph. Inside a
  single-point-grounded domain the compliant count is zero.

## Workflow

1. Build the topology from the node records (identifier, domain,
   grounding category, reference flag) and the link records (endpoints,
   link category, resistance in milliohm). Reject a duplicate
   identifier, a link that names a node not on the diagram, a
   self-link, a negative resistance and an unrecognised category before
   any tracing starts.
2. Resolve the vehicle-ground-reference: exactly one node is flagged.
   Zero designations means the baseline was never fixed and every path
   result would be meaningless; more than one means two baselines are
   in circulation. Both are input defects, not findings.
3. Trace each non-reference unit to the reference over the conductive
   subgraph, taking the lowest-resistance path. A non-isolated unit
   with no path has no return and is a finding; a unit whose path
   resistance exceeds its category allowance is a finding.
4. Check the deliberately-isolated units in the opposite direction: a
   conductive path from an isolated unit to the reference defeats the
   isolation and is a finding even when its resistance looks healthy.
5. Count independent loops over the single-point-grounded domain plus
   the reference. Any non-zero count is a ground-loop finding; report
   the loop count, because two redundant straps and five are different
   repair jobs.
6. Check the domain crossing: at least one ground-support-equipment
   node must exist, exactly one conductive link may cross the boundary,
   and that link must be the umbilical-ground-interface. Report a
   missing ground-support-equipment side, a missing crossing, extra
   crossings and an undesignated crossing category separately.
7. Aggregate. The diagram is compliant only when the unit-return,
   isolation, loop and domain-crossing finding lists are all empty.

## Pitfalls

- Reading a drawn line as a bond. A mounting-isolator is a line on the
  diagram and a break in the circuit; including it in the conductive
  graph makes every floating unit look correctly returned and hides
  the real missing-return findings.
- Declaring the diagram compliant because the flight segment is clean.
  The clause's distinguishing demand is the ground-support-equipment
  side; a topology that never models the trolley cannot show the
  second earth crossing it introduces.
- Treating a healthy lowest-resistance path as proof of a healthy
  topology. The lowest-resistance path says the return exists; the
  loop count says whether a second one exists in parallel. A
  single-point-grounded domain needs both answers.
- Reporting only that a loop exists. The independent-loop count is
  edges - nodes + components, and it tells the reader how many straps
  have to be removed; collapsing it to a boolean throws that away.
- Widening the return allowance because a summed path lands a hair
  above it. A sum of milliohm terms can land a few units in the last
  place over an allowance it physically meets -- absorb that in the
  comparison tolerance, never by raising the allowance.

## Behavior contract (gate 3)

The topology-construction, reference-resolution, return-path,
isolation, ground-loop and domain-crossing logic is exercised by the
gate 3 contract test:
`scripts/test_e2007_system_grounding_diagram.py` against
`scripts/e2007_system_grounding_diagram_logic.py` (stdlib unittest,
offline). Run: python3 scripts/test_e2007_system_grounding_diagram.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7080-support-structure-removal
description: "Assess whether the support structures on an additively manufactured part can be removed without damaging it, and by which method. Use when a support layout is reviewed before release or a removal route has to be planned: reduce each contact footprint to the area an interface style actually fuses, form the force needed to break it against the load the local section can carry, choose break-off, machining or wire cutting from access and those forces, escalate a break-off that would yield the part, and refuse a region inside a closed volume or on a functional surface. Trigger: ecss, q-st-70-80-additive-manufacturing, am-support-structure-removal, am-support-interface-break-force, am-support-witness-allowance, am-internal-support-access, am-support-removal-method."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-support-structure-removal, am-support-structure-removal, am-support-interface-break-force, am-support-witness-allowance, am-internal-support-access, am-support-removal-method]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Support Structure Removal (space-systems/ecss/q7080-support-structure-removal)

Use when the task is the part clause of ECSS-Q-ST-70-80 covering support
structures: designing them so they come off, and taking them off without
leaving damage or witness the part cannot carry.

## Domain quick reference

- A support is designed for its removal, not for the build. The contact
  interface, the access left around it and the surface it lands on are
  all decided while the geometry is still editable, and none of them can
  be improved once the part is built.
- The contact footprint is not the bonded area. A toothed or perforated
  interface fuses over a fraction of its footprint, which is the whole
  point of the tooth pattern, so the break force follows the effective
  area rather than the drawn one.
- Two forces decide whether break-off is safe: the force the interface
  needs and the force the local part section can take. When the part is
  the weaker of the two, breaking the support off is a way of breaking
  the part.
- Escalating to a cutting method is the correct answer to that, not a
  failure. Machining or wire cutting removes the support without loading
  the section, which is why an overloaded break-off becomes a cut rather
  than a rejection.
- Access is a hard property. A support inside a closed internal volume
  cannot be reached by hand, by a cutter or by a wire, so the finding
  belongs to the design and not to the shop.
- Witness is graded against the allowance on the surface it sits on. A
  stub on a face that will be machined later disappears into the cut;
  the same stub on a finished functional face does not.
- Forces are products and quotients of measured quantities, so a break
  load exactly equal to the section allowable can read a few units in
  the last place above it. The comparison absorbs that; the allowable is
  never raised.

## Workflow

1. Validate each support region: the interface style, the access class,
   the surface class it lands on, its contact and local section areas
   and the witness height it leaves. An unknown class is an input error
   rather than a default.
2. Reduce the contact footprint to the effective bonded area for the
   interface style.
3. Form the break force from that area and the interface strength, and
   the allowable load from the local section, its allowable stress and
   the safety factor.
4. Choose the method: nothing at all for a closed internal volume or a
   critical functional surface, break-off for open access inside the
   manual force limit, machining for open access above it or recessed
   access within it, and wire cutting for recessed access above it.
5. Escalate a break-off whose force exceeds the section allowable to a
   cutting method, and record why.
6. Grade the witness height against the machining allowance of the
   surface, skipping a non-critical surface that carries no allowance
   requirement.
7. Give the verdict: redesign required when a region cannot be reached,
   sits on a functional surface or leaves witness beyond its allowance;
   removable with findings when a break-off had to be escalated;
   removable otherwise.

## Pitfalls

- Sizing the break force from the drawn contact area. The tooth pattern
  exists to reduce the fused area, and using the footprint overstates
  the force by a factor of two to four.
- Breaking a support off a thin section because the force felt small in
  the hand. The comparison that matters is against the local section
  allowable, not against what an operator can pull.
- Leaving supports inside a closed channel and planning to flush them
  out. Nothing reaches them, and the part ships with un-removable
  structure inside it.
- Treating witness height as cosmetic. On a surface with no machining
  allowance it is a dimensional non-conformance, and on a fatigue
  surface it is a stress raiser.
- Reading a cutting method as a worse outcome than break-off. It is the
  removal route that does not load the part, and choosing it is the
  correct response to a section that cannot take the break force.

## Behavior contract (gate 3)

The region validation, effective bonded area, break and allowable force
formation, method selection with its escalation, witness allowance grading
and the overall removal verdict are exercised by the gate 3 contract test:
scripts/test_q7080_support_structure_removal.py against
scripts/q7080_support_structure_removal_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7080_support_structure_removal.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

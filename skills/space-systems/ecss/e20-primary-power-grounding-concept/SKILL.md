---
name: e20-primary-power-grounding-concept
description: "Use when assess the primary power grounding concept of a spacecraft under ECSS-E-ST-20C clause 5.8.1: categorize the declared topology as a single-point star reference or a deviation that needs justification, confirm exactly one bond ties the primary power return to structure, size that star strap against the maximum credible fault current and the protection clearing time using the adiabatic conductor rule, compute its direct-current resistance and the structure potential offset the fault drives across it, and confirm every user return stays isolated from structure so no second path forms. Trigger: ecss, e-st-20c-clause-5-8-1, primary-power-grounding-concept, single-point-star-reference, structure-bonding-strap, fault-current-carrying-capability, adiabatic-conductor-sizing, power-return-isolation, ground-loop-prevention."
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
  tags: [ecss, e-st-20-electrical-scope, e20-primary-power-grounding-concept, primary-power-grounding-concept, single-point-star-reference, structure-bonding-strap, fault-current-carrying-capability, adiabatic-conductor-sizing, power-return-isolation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Primary Power Grounding Concept (space-systems/ecss/e20-primary-power-grounding-concept)

Use when the task is the clause 5.8.1 grounding concept of
ECSS-E-ST-20C -- referencing the primary power source to the structure
at one star point, and showing that the strap making that reference
can carry the credible fault current for as long as the protection
needs to clear it without lifting the structure potential.

## Domain quick reference

- The declared topology is categorized once. A single-point star
  reference is the concept the clause asks for; a multipoint
  reference, a floating primary return, a hybrid arrangement or a
  daisy-chained return are deviations. A deviation is a finding in
  itself, and a deviation without a recorded justification is a second
  finding, because the concept then rests on nothing written down.
- Exactly one bond may tie the primary power return to structure. No
  bond leaves the primary side floating, with no defined reference for
  insulation coordination or fault return; more than one bond creates
  a loop in which structure current shares itself between paths, which
  is the failure the single-point concept exists to prevent. A bond
  tying a secondary return to structure is the same defect arriving
  through the user side.
- The star strap is sized by the adiabatic rule: for a short fault the
  conductor heats without losing heat to its surroundings, so the
  minimum cross-section is the fault current times the square root of
  the clearing time, divided by a material constant. Copper carries
  markedly more current per square millimetre than aluminium, and
  stainless steel far less, so the material is part of the sizing, not
  a detail of the drawing.
- Two electrical checks follow from the strap geometry. Its
  direct-current resistance is the material resistivity times the
  length over the cross-section, and it must meet the bonding class
  the project requires. The fault current flowing through that
  resistance lifts the structure potential by their product, and that
  offset must stay inside what the architecture allows, or every
  signal referenced to structure moves with it during the fault.
- Isolation closes the concept. Each user return is checked against a
  minimum isolation resistance to structure, and a unit that bonds its
  own primary return to structure is reported whatever its isolation
  reads, because it has already made the second path.

## Workflow

1. Categorize the declared topology; reject a topology that is not a
   recognised grounding concept, and report a deviation together with
   whether a justification exists.
2. List the mandatory star-point fields and report each one the
   concept sheet does not carry or leaves empty.
3. Walk the bond list and count the ties between the primary power
   return and structure; report none, report more than one, and report
   any secondary return tied directly to structure.
4. Compute the minimum adiabatic cross-section from the maximum
   credible fault current, the protection clearing time and the strap
   material, and report a strap section below it.
5. Compute the strap direct-current resistance from its length,
   section and material, and report a value above the bonding class
   limit.
6. Multiply that resistance by the fault current to get the structure
   potential offset during the fault, and report an offset above what
   the architecture allows.
7. Check every user return against the minimum isolation resistance
   and report a unit that is under it or that bonds its primary return
   to structure.
8. Aggregate the topology, star-point, fault-capability, bonding and
   isolation findings; the concept is acceptable only when all of them
   are empty.

## Pitfalls

- Sizing the star strap for the steady operating current. The strap
  spends its life carrying almost nothing and is sized by the fault it
  must survive until the protection clears, which is a far larger
  current for a far shorter time.
- Dropping the clearing time out of the sizing and using the fault
  current alone. The adiabatic rule scales with the square root of the
  time, so a protection device ten times slower needs a strap over
  three times the section for the same fault.
- Applying one material constant to every strap. A tin-plated copper
  braid and a stainless steel bracket of the same cross-section are
  not interchangeable as fault conductors.
- Reading a low bond resistance as proof the concept is sound. A
  compliant bond resistance still lifts the structure by the product
  of that resistance and the fault current, and it is the offset, not
  the resistance, that the referenced signals see.
- Counting only the bonds drawn on the power schematic. A unit that
  ties its own return to its chassis has added a structure path that
  no grounding diagram shows, and the isolation measurement is the
  only place it appears.
- Treating a floating primary return as the safe default. With no
  reference at all the primary side has an undefined potential
  against structure, so insulation coordination and fault return are
  both unresolved rather than conservative.

## Behavior contract (gate 3)

The topology categorization, star-point field, bond-count, adiabatic
sizing, strap-resistance, structure-offset and return-isolation logic
is exercised by the gate 3 contract test:
scripts/test_e20_primary_power_grounding_concept.py against
scripts/e20_primary_power_grounding_concept_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_primary_power_grounding_concept.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

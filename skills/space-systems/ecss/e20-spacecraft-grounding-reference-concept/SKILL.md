---
name: e20-spacecraft-grounding-reference-concept
description: "Use when define and verify the controlled reference grounding concept of a spacecraft under ECSS-E-ST-20C clause 6.3.8.2: categorize every circuit as primary power, secondary power, sensitive analogue, digital signal, pyrotechnic firing or coaxial radio frequency, categorize every unit as a power source, power user, signal source, signal receiver or pyrotechnic initiator, decide whether the reference topology may remain single-point by comparing the longest return run against the wavelength at the highest circuit frequency, confirm each isolated power domain carries exactly one reference point, check unit-to-structure bonding and secondary-side isolation resistance, and size the common-impedance voltage a shared return path injects into a victim circuit. Trigger: ecss, e-st-20-electrical-scope, spacecraft-grounding-reference-concept, distributed-single-point-ground, structure-return-current, unit-bonding-resistance, common-impedance-coupling, grounding-topology-selection, secondary-side-isolation-resistance."
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
  tags: [ecss, e-st-20-electrical-scope, e20-spacecraft-grounding-reference-concept, spacecraft-grounding-reference-concept, distributed-single-point-ground, structure-return-current, unit-bonding-resistance, common-impedance-coupling, secondary-side-isolation-resistance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Spacecraft Grounding Reference Concept (space-systems/ecss/e20-spacecraft-grounding-reference-concept)

Use when the task is the clause 6.3.8.2 grounding work of ECSS-E-ST-20C
-- agreeing one reference grounding concept for the whole spacecraft,
writing down which circuit categories and which unit categories it
covers, and showing that the topology, the bonding and the isolation
actually hold the concept the project agreed to.

## Domain quick reference

- The concept is a controlled document, not a drawing note. It names
  the reference topology, it assigns every circuit to exactly one
  circuit category (primary power, secondary power, sensitive
  analogue, digital signal, pyrotechnic firing, coaxial radio
  frequency, structure reference) and every unit to exactly one unit
  category (power source, power user, signal source, signal receiver,
  pyrotechnic initiator). A circuit or unit kind that maps to no
  category is a gap in the concept, not a detail to settle in the
  harness drawing.
- The topology choice is physics, not preference. A single reference
  point behaves as one node only while the longest return conductor is
  electrically short at the highest frequency the circuit carries --
  the working threshold is one twentieth of the wavelength in the
  conductor, wavelength being the speed of light times the velocity
  factor divided by frequency. Past that, the return run is a
  distributed element, the single point is a single point only at
  direct current, and a multi-point or hybrid reference is required.
  Declaring multi-point where single-point is valid is also a finding:
  it opens structure loops the concept had no need to open.
- Each isolated power domain carries exactly one reference point.
  Zero leaves the domain floating with no controlled return; more than
  one closes a structure loop between the reference points and lets
  return current divide between the intended conductor and the
  structure.
- Primary power, secondary power, pyrotechnic and sensitive analogue
  returns are dedicated conductors. Structure is a reference, not a
  return path for those categories; digital signal and coaxial radio
  frequency returns are the categories where a structure path is part
  of the intended design.
- Bonding and isolation are the two measurable proofs. Unit-to-
  structure bonding resistance carries a per-category limit, tightest
  for pyrotechnic initiators and radio-frequency referenced units;
  secondary-side isolation resistance to structure carries a minimum
  that keeps the domain genuinely isolated.
- Where a return conductor is shared, common-impedance coupling
  converts the aggressor return current into a voltage in the victim
  circuit: return current times the impedance of the shared path. That
  voltage is compared against the victim's noise budget.

## Workflow

1. Categorize every circuit and every unit in the concept; reject a
   kind that belongs to no category before it reaches the checks.
2. Compute the wavelength at the highest circuit frequency, derive the
   required reference topology from the longest return run, and
   compare it against the declared topology.
3. Confirm the isolated power domain carries exactly one reference
   point; flag a floating domain and a multiply referenced one
   separately, because the repairs differ.
4. Flag every circuit whose category forbids a structure return but
   which is drawn with one.
5. Compare each unit's bonding resistance against the limit for its
   unit category, and the domain isolation resistance against its
   minimum.
6. For each shared return path, compute the common-impedance voltage
   and flag a victim circuit whose noise budget it exceeds.
7. Aggregate the topology, reference-point, structure-return, bonding,
   isolation and coupling findings; the concept is controlled only
   when every list is empty.

## Pitfalls

- Treating a single-point concept as valid at every frequency. The
  concept is agreed once, but the returns it draws stop behaving as
  one node above the electrical-length threshold, and the check is the
  run length against the wavelength, not the schematic.
- Reading a second reference point as harmless redundancy. Two points
  on one isolated domain form a loop through structure, and the
  return current divides between them in a ratio nobody controlled.
- Using structure as the primary power return because the resistance
  measured low. The category rule is about the controlled return path
  and the loop area it defines, not about the resistance of the
  aluminium.
- Applying one bonding limit to every unit. A pyrotechnic initiator
  and a housekeeping heater do not carry the same limit, and a single
  loose number either over-constrains the structure design or leaves
  the initiator under-bonded.
- Treating a shared return as acceptable because each circuit passes
  on its own. Common-impedance coupling is a property of the shared
  path, so it appears only when aggressor current and victim budget
  are evaluated together.

## Behavior contract (gate 3)

The circuit and unit categorization, topology selection,
reference-point, structure-return, bonding, isolation and
common-impedance logic is exercised by the gate 3 contract test:
scripts/test_e20_spacecraft_grounding_reference_concept.py against
scripts/e20_spacecraft_grounding_reference_concept_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_spacecraft_grounding_reference_concept.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

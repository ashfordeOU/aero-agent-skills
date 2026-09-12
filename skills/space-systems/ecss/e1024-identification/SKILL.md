---
name: e1024-identification
description: "Use when identify interfaces for a space system under ECSS-E-ST-10-24C
  §5.2: build the interface tree or list, assign each interface to a category (mechanical,
  electrical, data, thermal, fluid, RF, or optical), and generate unique interface
  identifiers following the standard naming convention. Apply to any system or subsystem
  boundary where the interface type, connecting entities, and sequence position must
  be captured before interface control documentation proceeds. Trigger: ecss, e-st-10-system-scope,
  interface-identification, interface-tree, interface-category, interface-identifier,
  icd, interface-control."
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
  tags: [ecss, e-st-10-system-scope, interface-identification, interface-tree, interface-category, interface-identifier, icd, interface-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Interface Identification (space-systems/ecss/e1024-identification)

Use when the task is identifying and recording interfaces for a space system or
subsystem under ECSS-E-ST-10-24C §5.2 — assigning each interface to a category,
generating its unique identifier, and building the interface tree or list that feeds
downstream interface control documentation.

## Domain quick reference

- §5.2 requires that every interface between system elements be placed in the
  interface tree (or list) before interface control documents (ICDs) are
  drafted. An interface is a boundary across which two entities exchange mass,
  energy, signals, or data; each such boundary must be captured once and given
  a unique identifier.
- Interface categories in the §5.2 taxonomy are: mechanical (structural,
  kinematic, and acoustic connections), electrical (power, grounding, harness),
  data (software, protocol, signal paths), thermal (conduction and radiation
  couplings), fluid (propellant, pressurant, coolant flow), RF (radio-frequency
  and antenna links), and optical (light-path and alignment connections). Every
  interface belongs to exactly one category.
- An interface identifier encodes the two connecting entities and the category,
  e.g. `SC-AOCS-ELC-001` for the first electrical interface between the
  spacecraft (SC) and the AOCS subsystem. The sequence number prevents
  ambiguity when multiple interfaces of the same category exist between the
  same pair of entities.
- An interface tree groups interfaces hierarchically by owning entity; an
  interface list is a flat enumeration. Both representations must be consistent
  — every identifier appearing in the tree must also appear in the list.

## Workflow

1. Enumerate every entity boundary in scope (system-to-subsystem,
   subsystem-to-unit, system-to-external). Each boundary that exchanges
   mass, energy, signals, or data yields at least one interface entry.
   An entity must not be listed as both sides of the same interface
   (self-interfaces are rejected).
2. For each interface, determine its category from the seven-category
   taxonomy (mechanical, electrical, data, thermal, fluid, RF, optical).
   Reject any interface whose type cannot be mapped to one of the seven
   categories before it enters the list.
3. Generate the unique identifier for each interface: concatenate the
   normalized names of the two connecting entities, the two-to-three
   character category code, and a zero-padded three-digit sequence
   number — `{ENTITY_A}-{ENTITY_B}-{CAT_CODE}-{SEQ:03d}`. Sequence
   numbers start at 001 and increment within each entity-pair / category
   group.
4. Check the complete interface list for identifier uniqueness. Duplicate
   identifiers indicate either a sequencing error or a missed distinction
   between physically separate interfaces; resolve before proceeding.
5. Build the interface tree by grouping each interface record under its
   primary owning entity (side A). Verify that the tree and list contain
   the same set of identifiers.
6. Flag any interface entry that is missing a category, has a malformed
   identifier, or lacks a description. An interface list is complete only
   when all entries pass the validation gate.

## Pitfalls

- Treating multi-category boundaries as a single interface — a connector
  that carries both power and data lines represents two separate interfaces
  (one electrical, one data), each with its own identifier and ICD.
- Assigning a category by connector shape rather than by what crosses the
  boundary — a D-sub carrying RS-422 signals is a data interface, not
  electrical, even though it uses an electrical connector.
- Omitting the sequence number when only one interface of a given
  category exists between a pair of entities — the identifier scheme
  requires the numeric suffix regardless, so that future additions never
  collide with an unnumbered entry.
- Accepting a self-interface (same entity on both sides) as valid — a
  self-interface indicates the interface was recorded against the wrong
  decomposition level; escalate to clarify the system breakdown before
  assigning identifiers.

## Behavior contract (gate 3)

The category normalization, identifier generation, interface-record
construction, list validation, tree building, and uniqueness-check logic
are exercised by the gate 3 contract test:
scripts/test_e1024_identification.py against
scripts/e1024_identification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_identification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

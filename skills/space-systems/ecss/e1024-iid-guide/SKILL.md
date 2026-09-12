---
name: e1024-iid-guide
description: "Use when draft an Interface Identification Document (IID) for a space system or equipment item under ECSS-E-ST-10-24C Annex D: inventory every interface of the item, categorize each interface by type (physical, electrical, data, RF, thermal, optical, fluid), assign a maturity level (proposed, agreed, or baselined) to each interface, record the responsible party for each interface side, verify that every interface links to a controlling Interface Control Document, and aggregate completeness gaps before formal baseline. Trigger: ecss, e-st-10-system-scope, iid, interface-identification, interface-register, icd, interface-management, interface-type, maturity-level."
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
  tags: [ecss, e-st-10-system-scope, iid, interface-identification, interface-register, icd, interface-management, interface-type, maturity-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — IID Guide (space-systems/ecss/e1024-iid-guide)

Use when the task is assembling an Interface Identification Document (IID)
per ECSS-E-ST-10-24C Annex D — inventorying every interface of a system
or equipment item, categorizing each interface by type, assigning maturity
levels, recording responsible parties, and verifying that each interface
links to a controlling Interface Control Document.

## Domain quick reference

- ECSS-E-ST-10-24C Annex D proposes the content structure for an IID:
  a header block (document ID, item identity, revision status) followed
  by an interface register in which each row represents one interface and
  carries the interface ID, name, type, maturity level, responsible party
  for each side (A-side and B-side), and a reference to the controlling
  Interface Control Document (ICD).
- Interface types in the register fall into one of seven recognized
  categories: physical (mechanical mating, connectors, mounting),
  electrical (power, grounding, bonding), data (digital communication,
  protocol, bus), RF (radio-frequency signals, waveguides), thermal
  (heat transfer paths, temperature boundaries), optical (light paths,
  field-of-view requirements), and fluid (propellant lines, cooling
  loops). Every interface is categorized into exactly one type before it
  enters the register; an unrecognized type is rejected.
- Maturity levels track the agreement status of each interface:
  proposed (identified but not yet negotiated), agreed (both sides have
  accepted the interface definition), and baselined (formally controlled
  under change management). An interface advances from proposed to agreed
  to baselined; the IID makes maturity visible across all interfaces so
  that gaps are apparent at any review milestone.
- Every interface in the IID must reference a controlling ICD. A TBD or
  empty ICD reference is a completeness gap, not a valid state, because
  the IID is the mapping layer between interface identities and their
  governing documents.

## Workflow

1. Identify the system or equipment item whose interfaces are to be
   documented and collect the item's functional and physical boundary
   description. Confirm the item's identifier and revision level that
   will appear in the IID header.
2. Inventory every candidate interface by enumerating all connection
   points, signal exchanges, physical attachments, and environmental
   boundaries between the item and adjacent systems, subsystems, or the
   external environment.
3. For each candidate interface, categorize it as physical, electrical,
   data, RF, thermal, optical, or fluid. Reject any interface whose type
   cannot be mapped to one of these seven categories and escalate for
   clarification before adding it to the register.
4. Assign an initial maturity level to each interface: proposed if it
   has been identified but not yet negotiated, agreed if both responsible
   parties have accepted the definition, baselined if it is under formal
   change control. Record the basis for the assigned level.
5. Record the responsible party for both the A-side (the item described
   by the IID) and the B-side (the adjacent system or element). An
   interface with an unassigned responsible party on either side is
   incomplete.
6. For each interface, enter the reference identifier of the controlling
   ICD. If no ICD yet exists, record TBD and flag the interface as a
   completeness gap; do not leave the field blank.
7. Run the completeness check: verify that no interface ID appears more
   than once, that no required field is empty, that all maturity levels
   and interface types are valid, and that the ratio of TBD ICD
   references to total interfaces is within the project's accepted gap
   threshold for the current milestone.
8. Collect all completeness gaps and maturity-level summary counts into
   the IID status section for review. The IID is not ready for milestone
   submission until all blocking gaps are resolved.

## Pitfalls

- Leaving the ICD reference field empty rather than entering TBD: an
  empty field makes it impossible to distinguish a deliberately open
  item from a data-entry omission. Always enter TBD explicitly so the
  gap is visible in the completeness check.
- Assigning a type of "mechanical" or "structural" instead of
  "physical": the IID register uses "physical" as the canonical type
  for mechanical and structural interfaces; deviating creates
  inconsistency with other items in the same program's IID set.
- Treating an interface as baselined before both responsible parties
  have agreed: the maturity levels are sequential — an interface cannot
  skip from proposed to baselined without passing through agreed.
- Omitting internal interfaces between subassemblies of the item: the
  IID scope covers all interfaces that require an ICD, including
  internal ones that are controlled across sub-element boundaries.
- Recording only the A-side responsible party and leaving B-side blank
  because "it belongs to another team": both sides must be recorded in
  the IID regardless of organizational boundaries; accountability gaps
  become integration risks.

## Behavior contract (gate 3)

The interface-type categorization, maturity-level assignment, ICD-linkage
check, and collection-level completeness validation logic is exercised by
the gate 3 contract test: scripts/test_e1024_iid_guide.py against
scripts/e1024_iid_guide_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_iid_guide.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

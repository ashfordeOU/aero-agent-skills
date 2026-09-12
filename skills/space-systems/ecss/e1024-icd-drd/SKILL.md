---
name: e1024-icd-drd
description: "Use when generate and validate an Interface Control Document (ICD) against ECSS-E-ST-10-24C Annex B DRD criteria: identify both sides of each interface pair, assign each interface to a recognized type (mechanical, electrical, thermal, data, RF, optical, fluid), confirm all mandatory DRD sections are present (scope, reference documents, interface description, verification requirements), trace every interface requirement to a parent IRD or system-level requirement, and verify that each interface requirement carries an assigned verification method. Flag incomplete identification, unrecognized interface types, missing sections, untraced requirements, and requirements lacking verification coverage. Trigger: ecss, e-st-10-system-scope, interface-control, icd, drd, interface-management, requirements-traceability, verification-coverage."
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
  tags: [ecss, e-st-10-system-scope, interface-control, icd, drd, interface-management, requirements-traceability, verification-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — ICD DRD Compliance (space-systems/ecss/e1024-icd-drd)

Use when the task is to generate or validate an Interface Control Document
against the Data Requirements Document (DRD) defined in ECSS-E-ST-10-24C
Annex B — identifying interface pairs, categorizing interface types,
confirming mandatory section coverage, tracing requirements to parent
documents, and verifying that each interface requirement has an assigned
verification method.

## Domain quick reference

- ECSS-E-ST-10-24C Annex B defines the DRD for the ICD. The ICD describes
  every interface between two items in a space system: both items in the pair
  must be explicitly named, and the document must carry a unique identifier
  and revision mark before any content is considered valid.
- Interface types are drawn from a fixed set: mechanical (structural,
  kinematic connections), electrical (power, grounding, signal), thermal
  (heat exchange, thermal coupling), data (communication protocols, data
  formats), RF (radio-frequency links), optical (light paths, field-of-view
  interactions), and fluid (propellant, coolant lines). Each interface is
  categorized into exactly one type; an unrecognized type is a DRD violation.
- Mandatory DRD sections per Annex B are: scope (purpose and boundaries of
  the interface), reference_documents (IRD, system spec, and other governing
  documents), interface_description (the technical definition of the
  interface), and verification_requirements (the set of requirements that
  must be verified across the interface). An ICD missing any of these sections
  is non-compliant regardless of the quality of the remaining content.
- Every interface requirement stated in the ICD must trace back to a parent
  requirement in the Interface Requirements Document (IRD) or in the
  system-level specification. A requirement without a parent_ref has no
  top-down authority and must be flagged.
- Each interface requirement must also carry an assigned verification method
  from the set: analysis, test, inspection, review_of_design. A requirement
  without a verification method cannot be closed out during verification
  campaigns.

## Workflow

1. Check identification completeness: confirm the ICD carries a non-empty
   icd_id, a revision mark, and an interface_pair with exactly two non-empty
   item names. Reject any ICD missing these fields before proceeding.
2. Categorize each interface type listed in the ICD against the recognized
   type set. Flag any type not in the set; require at least one type to be
   declared.
3. Verify mandatory section coverage: confirm scope, reference_documents,
   interface_description, and verification_requirements sections are all
   present and non-empty. Record a finding for each missing or empty section.
4. Check requirement traceability: for each interface requirement, confirm a
   parent_ref field is present and non-empty. Flag every requirement that
   lacks a parent reference.
5. Verify verification coverage: for each requirement, confirm a verification
   method is assigned and is drawn from the recognized method set. Flag
   requirements with a missing or unrecognized method.
6. Aggregate all findings. An ICD is DRD-compliant only when the aggregated
   finding list is empty. Return the full finding list to allow targeted
   remediation.

## Pitfalls

- Accepting an ICD with a single-sided interface_pair (only one item named)
  as valid — both sides of the interface must be identified; a one-sided entry
  is ambiguous and cannot be controlled as an interface.
- Skipping the parent_ref check on the grounds that requirements are
  "obviously derived" — the traceability link must be explicit and on-record
  in the ICD, not implicit in the engineer's intent.
- Treating an empty mandatory section as present — a section key with no
  content satisfies the key-presence check but not the DRD content
  requirement; both must be verified.
- Allowing a custom verification method not in the recognized set — the
  four ECSS verification methods (analysis, test, inspection,
  review_of_design) are the only methods recognized for ICD verification
  closure; custom entries must be mapped to one of the four.
- Reading an empty findings list from a partial check (e.g., only
  identification checked) as full DRD compliance — all five check steps
  must complete before the ICD can be declared compliant.

## Behavior contract (gate 3)

The identification, interface-type categorization, section-coverage,
requirement-traceability, and verification-coverage logic is exercised by
the gate 3 contract test: scripts/test_e1024_icd_drd.py against
scripts/e1024_icd_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_icd_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

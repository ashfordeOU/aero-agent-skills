---
name: e1024-ird-drd
description: "Use when generate or validate an Interface Requirements Document (IRD) for a space system element pair under ECSS-E-ST-10-24C Annex A: identify both interface parties, categorize each interface requirement by type (mechanical, electrical, thermal, data, rf, environmental, human), assign a unique verifiable identifier to every requirement, confirm each requirement carries a verification method (T/A/I/R/D), check that no duplicate requirement IDs exist, and flag any missing mandatory document-level fields such as project name, issue date, or applicable documents list. Trigger: ecss, e-st-10-system-scope, ird, interface-requirements-document, drd, interface-parties, verification-method, requirement-traceability."
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
  tags: [ecss, e-st-10-system-scope, ird, interface-requirements-document, drd, interface-parties, verification-method, requirement-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Interface Requirements Document per DRD (space-systems/ecss/e1024-ird-drd)

Use when the task is to generate or validate an Interface Requirements
Document (IRD) in accordance with ECSS-E-ST-10-24C Annex A -- identifying
both interface parties, categorizing requirements by interface type, assigning
unique verifiable identifiers, confirming each requirement carries a valid
verification method, and verifying structural completeness before the IRD is
baselined.

## Domain quick reference

- ECSS-E-ST-10-24C Annex A defines the Document Requirements Definition (DRD)
  that every IRD must satisfy. The IRD captures interface requirements between
  two named items (item A and item B) before a controlling ICD is issued; it
  precedes and drives the ICD and must be traceable to it.
- Interface requirements are categorized into one of seven canonical types:
  mechanical (structural loads, alignments, mounting), electrical (power,
  grounding, signal lines), thermal (heat dissipation, temperature limits),
  data (protocols, data formats, timing), rf (RF/EMC compatibility), environmental
  (vibration, shock, radiation, pressure), or human (operator interface,
  ergonomics). Each requirement belongs to exactly one type; an unrecognized
  type is a finding before analysis proceeds.
- Every requirement must carry a unique identifier following the pattern
  ALPHA-WORD-NNN (e.g. IRD-MECH-001) and a verification method from the set
  {T, A, I, R, D} representing Test, Analysis, Inspection, Review of Design,
  and Demonstration. A requirement without a valid verification method is not
  verifiable and cannot be baselined.
- The document level requires: a document identifier, issue date, project name,
  item A name, item B name, and a requirements list containing at least one entry.
  Missing any of these fields is a structural finding.

## Workflow

1. Confirm both interface parties (item A and item B) are named, non-empty, and
   distinct. A document where item A and item B name the same entity does not
   describe an interface and is rejected before requirements are processed.
2. Verify mandatory document-level fields are present: document_id, issue_date,
   project, item_a, item_b, and requirements. Reject the document if any field
   is absent or empty; do not silently default missing fields.
3. For each requirement, confirm all mandatory requirement fields are present:
   id, title, description, interface_type, verification_method. A requirement
   missing any mandatory field is flagged individually and does not block
   evaluation of the remaining requirements.
4. Categorize each requirement's interface_type against the seven canonical
   types. Flag requirements whose type is not recognized; do not attempt to
   infer the intended type from the description.
5. Validate the requirement identifier format. Reject identifiers that do not
   follow the ALPHA-WORD-NNN pattern (uppercase segments separated by hyphens,
   ending with three or more digits).
6. Check for duplicate requirement IDs across the full requirements list. Each
   identifier must be unique within a single IRD.
7. Confirm each requirement carries a valid verification method from {T, A, I,
   R, D}. Requirements with an unrecognized or absent method are flagged as
   unverifiable.
8. Aggregate all findings. An IRD is valid for baselining only when structural
   findings, party findings, and per-requirement findings are all empty.

## Pitfalls

- Treating a missing interface party as a minor omission -- without both named
  parties an IRD describes no interface; the document must be rejected, not
  partially validated.
- Allowing free-text interface types without checking against the canonical set
  -- ambiguous types prevent ICD traceability and must be resolved before the
  IRD is approved.
- Accepting a requirement identifier that passes a casual eye-check but does
  not match the required pattern -- automated ID traceability breaks on
  non-conforming identifiers downstream.
- Reading "no duplicate findings" as "all IDs are unique" without actually
  scanning the full list -- duplicate IDs at different positions in a large
  requirements list are easy to miss manually.
- Treating a requirement that lacks a verification method as "to be assigned
  later" rather than a hard finding -- a requirement that cannot be verified
  cannot be confirmed as satisfied and must be resolved before baselining.

## Behavior contract (gate 3)

The interface party check, document structure validation, requirement
categorization, ID pattern check, duplicate detection, and verifiability
logic are exercised by the gate 3 contract test:
scripts/test_e1024_ird_drd.py against scripts/e1024_ird_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e1024_ird_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

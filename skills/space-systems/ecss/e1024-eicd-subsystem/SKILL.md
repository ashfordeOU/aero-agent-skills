---
name: e1024-eicd-subsystem
description: "Use when produce EICDs at the space segment subsystem level per ECSS-E-ST-10-24C §5.8.2: identify all inter-subsystem interfaces by type (mechanical, electrical, thermal, data, RF, fluid, optical, pyrotechnic), verify each interface record carries every required field, confirm that requirement references trace to the system-level requirement registry, flag records where subsystem identifiers are not distinct, and detect duplicate or contradictory interface definitions for the same subsystem pair. Aggregate document-level, per-interface, traceability, and consistency findings to determine whether the EICD achieves compliance. Trigger: ecss, e-st-10-system-scope, eicd, interface-control-document, subsystem-interface, traceability, verification, consistency-check."
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
  tags: [ecss, e-st-10-system-scope, eicd, interface-control-document, subsystem-interface, traceability, verification, consistency-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Control — EICD at Subsystem Level (space-systems/ecss/e1024-eicd-subsystem)

Use when the task is to produce or verify an Engineering Interface Control
Document (EICD) at the space segment subsystem level under
ECSS-E-ST-10-24C §5.8.2 — identifying every inter-subsystem interface,
checking completeness and consistency of each interface record, confirming
requirement traceability, and detecting conflicting definitions for the
same subsystem pair.

## Domain quick reference

- An EICD at subsystem level documents every physical and functional
  interface between distinct subsystems within the space segment (e.g.
  OBC–ADCS, EPS–payload, structure–thermal control). Each interface is
  categorized by type before it is assessed: recognized types are
  mechanical, electrical_power, electrical_signal, thermal, data, rf,
  fluid, optical, and pyrotechnic. An interface whose type cannot be
  placed in one of these categories must be resolved before the EICD
  can proceed.
- Every interface record must carry: a unique interface_id, the
  interface_type, the two distinct subsystem identifiers (subsystem_a
  and subsystem_b), a description, at least one requirement_id tracing
  to the system-level IRD or SRD, and a verification_method drawn from
  test, analysis, inspection, review_of_design, or similarity. A record
  that is missing any of these fields is incomplete and cannot be
  considered part of a compliant EICD.
- Requirement traceability means every requirement_id cited in an
  interface record resolves to an entry in the project's requirement
  registry. An ID that does not resolve is a traceability gap; the
  interface record is non-compliant until the gap is closed or the
  requirement is registered.
- Bidirectional consistency: the same (subsystem_a, subsystem_b) pair
  with the same interface_type must appear in exactly one record. A
  second record for the same pair and type is a duplicate and flags a
  conflict; the EICD is non-compliant until one record is retired or
  the two are merged.

## Workflow

1. Verify the top-level EICD document contains all required sections:
   document_id, revision, space_segment_id, at least one entry in
   interfaces, and applicable_documents. Flag every missing or empty
   section before proceeding.
2. For each interface record in the EICD, check that all required
   fields are present and non-empty, that subsystem_a and subsystem_b
   are distinct, that the interface_type is a recognized type, and that
   the verification_method is a recognized method. Collect all findings
   per record.
3. For each interface record, resolve every requirement_id against the
   project requirement registry. Record any ID that cannot be resolved
   as a traceability gap against that interface.
4. Scan all interface records for duplicate (subsystem pair, type)
   combinations. Two records covering the same pair with the same type
   are in conflict; record both interface_ids in the consistency
   finding.
5. Aggregate all findings across the four check categories. The EICD
   is compliant only when document_findings, interface_findings,
   traceability_findings, and consistency_findings are all empty.

## Pitfalls

- Treating an interface record as complete when requirement_ids is
  present but empty — an empty list means no system-level requirement
  anchors this interface, which is a traceability gap, not a pass.
- Allowing subsystem_a and subsystem_b to hold the same identifier —
  an interface from a subsystem to itself is not a subsystem-level
  interface and indicates a data entry error.
- Collapsing bidirectional duplicates silently — if the EICD captures
  both directions of the same interface as separate records with the
  same type, one must be retired before the document is compliant.
- Accepting an unrecognized interface type without resolution — novel
  types that do not map to the standard set cannot be assessed for
  completeness or coverage and must be resolved against the project's
  type taxonomy before they enter the EICD.

## Behavior contract (gate 3)

The interface-type validation, record-completeness check, requirement-
traceability check, bidirectional-consistency check, and full-assessment
logic are exercised by the gate 3 contract test:
scripts/test_e1024_eicd_subsystem.py against
scripts/e1024_eicd_subsystem_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_eicd_subsystem.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

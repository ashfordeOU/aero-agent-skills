---
name: e1024-icd-generic
description: "Use when apply generic Interface Control Document (ICD) structure
  and content rules under ECSS-E-ST-10-24C §5.7 for any ICD variant — EICD, MICD,
  or TICD: verify each ICD carries a unique interface identifier, an identification
  block (document number, revision, date, project, interface name, provider,
  requester), an applicable-documents list, an interface-description section, a
  numbered requirements section with bilateral allocation and parent-system
  traceability, a verification-method entry for every requirement, a named
  configuration-control authority, and a revision history. Flag missing sections,
  incomplete identification blocks, untraceable requirements, and absent
  configuration-control records. Trigger: ecss, e-st-10-system-scope, icd, eicd,
  micd, ticd, interface-control-document, icd-structure, interface-requirements,
  configuration-control."
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
  tags: [ecss, e-st-10-system-scope, icd, eicd, micd, ticd, interface-control-document, icd-structure, interface-requirements, configuration-control]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Interface Management — Generic ICD Structure and Content (space-systems/ecss/e1024-icd-generic)

Use when the task is applying the common structure and content rules of
ECSS-E-ST-10-24C §5.7 to any ICD variant (EICD, MICD, or TICD) —
checking that each document is structurally complete, that every
requirement is bilaterally allocated and traceable to a parent system
requirement, and that configuration-control provisions are in place.

## Domain quick reference

- ECSS-E-ST-10-24C §5.7 establishes the common structure and content
  rules that apply to every interface control document regardless of
  variant. An ICD is valid only when all required sections are present
  and populated; a document that omits a section is structurally
  non-conforming even if its individual requirements are well-formed.
- The identification block anchors the document in the project context:
  it must carry a document number, revision mark, issue date, project
  name, interface name, and the identities of both the providing and
  receiving parties. A missing party identity prevents authoritative
  sign-off and is treated as a structural deficiency, not a content
  shortfall.
- Each numbered requirement must be traceable upward to at least one
  parent system-level requirement, must state which deliverable the
  provider is responsible for and which the requester accepts (bilateral
  allocation), and must carry a named verification method (test,
  analysis, inspection, or review of design). A requirement that lacks
  a parent traceability link or an allocated verification method is
  incomplete regardless of the correctness of its technical statement.
- Configuration control must be explicit: a named authority responsible
  for approving changes to the ICD, and a revision history recording
  the evolution of the document. An ICD without a named authority has
  no formal change process and cannot be baselined.

## Workflow

1. Confirm the ICD type (EICD, MICD, TICD, or generic ICD). Reject any
   document that does not identify its type before proceeding.
2. Verify the interface identifier is unique and non-empty. Record the
   identifier as the primary key for this ICD record in the project
   interface register.
3. Check that all six required sections are present: identification,
   applicable documents, interface description, requirements,
   verification, and configuration control. List any missing section as
   a structural finding before examining content.
4. Inspect the identification block for all seven required fields:
   document number, revision, date, project, interface name, provider,
   and requester. A blank or absent field in the identification block is
   a structural finding independent of the requirements content.
5. For each requirement entry, confirm: (a) a non-empty requirement ID,
   (b) a requirement statement, (c) a parent system-level requirement
   reference, (d) an explicit provider allocation, (e) an explicit
   requester allocation, and (f) a recognized verification method (test,
   analysis, inspection, or review of design). Record each missing or
   unrecognized field as a requirement-level finding keyed to the
   requirement ID.
6. Verify that all requirement IDs within the ICD are unique. A
   duplicate ID makes the interface register ambiguous and is flagged
   as a separate finding.
7. Check the configuration-control section for a named change authority
   and a revision history. An ICD with neither field populated cannot
   be formally baselined.
8. Aggregate all findings under four categories: structure findings,
   identification findings, requirement findings, and configuration
   findings. The ICD is conformant under §5.7 only when all four
   categories are empty.

## Pitfalls

- Accepting an ICD that has a requirements section but no parent
  traceability references — the requirements section may be complete in
  form while every requirement floats unanchored above the system
  requirement tree. The traceability check is mandatory per §5.7
  regardless of how well the requirements are written.
- Skipping the section-presence check and proceeding directly to
  content review — a section that is absent generates no content
  findings, creating a false impression of a well-formed document.
  Always verify section presence first.
- Treating a revision history entry with a blank description as
  compliant — revision history requires meaningful content (revision
  mark, date, change description) to serve its configuration-control
  function; a placeholder row satisfies the structure but not the
  intent.
- Conflating the verification section (a section of the ICD) with the
  verification-method field on each requirement — both must be present
  independently: the section provides the overall verification approach,
  and each requirement carries its own method assignment.

## Behavior contract (gate 3)

The ICD-type validation, interface-id check, section-presence check,
identification-block check, requirement-entry check, unique-ID check,
and configuration-control check logic is exercised by the gate 3
contract test: scripts/test_e1024_icd_generic.py against
scripts/e1024_icd_generic_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1024_icd_generic.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

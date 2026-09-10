---
name: e1002-other-planning-docs
description: "Use when determine which other ECSS-E-ST-10-02C verification planning documents (the interface to the AIT plan, the analysis plans) are required for a set of requirements based on the verification method assigned to each one, check every required document against its minimum content fields and against full cross-reference coverage of the requirement identifiers assigned to its method, track each document's draft/in_review/approved status, and roll up an overall other-planning-documents readiness status and compliance flag for the verification programme. Trigger: ecss, e-st-10-02c, verification planning, AIT plan interface, analysis plan, other planning documents, verification method, document completeness, requirement linkage, planning document status roll-up."
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
  tags: [ecss, e-st-10-02c, verification-planning, ait-plan-interface, analysis-plan, other-planning-documents]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Other Planning Documents (space-systems/ecss/e1002-other-planning-docs)

Use when the task is producing or checking the "other" verification
planning documents required by ECSS-E-ST-10-02C clause 5.2.8.3 --
the documents that interface the verification programme to
programme-level activities beyond the main verification plan itself,
namely the interface to the AIT (assembly, integration and test) plan
and the analysis plan(s).

## Domain quick reference

- Clause 5.2.8.3 does not require every other planning document for
  every programme -- each one is triggered by the verification method
  assigned to at least one requirement. A requirement verified by test
  triggers the AIT plan interface document; a requirement verified by
  analysis triggers an analysis plan. Requirements verified by
  inspection or review of design do not trigger a document under this
  leaf's scope (their records are handled elsewhere in the
  verification plan).
- A required document is not complete merely by existing. The AIT plan
  interface must carry a reference to the AIT plan itself, the list of
  requirement identifiers it covers, and the interface points
  (integration/test activities) it ties to. The analysis plan must
  carry its analysis methods, the requirement identifiers it covers,
  and the tools or models used. A document missing any of these fields
  is incomplete regardless of its approval status.
- Completeness of content is separate from completeness of coverage: a
  document can list every required field and still omit a requirement
  identifier that the verification method assignment says it must
  cover. Both gaps are reported independently so neither masks the
  other.
- Each required document carries one status: draft, in_review, or
  approved. The other-planning-documents set as a whole is only as
  ready as its least-complete document -- one draft document holds the
  whole set at draft even if every other required document is
  approved. A programme with no test- or analysis-verified
  requirements has nothing to produce under this leaf and is trivially
  ready.

## Workflow

1. For every requirement in the verification programme, read its
   assigned verification method and reject an unrecognized method
   before it is used to derive document applicability.
2. Derive the required other-planning-document set: the AIT plan
   interface if any requirement is verified by test, the analysis plan
   if any requirement is verified by analysis. Skip document types
   with no triggering requirement.
3. For each required document, confirm it exists at all -- a required
   document with no record on file is itself a finding, not merely an
   incomplete one.
4. For each required document that exists, check its minimum content
   fields for presence and check that every requirement identifier
   assigned to its triggering method is referenced by the document.
5. Record each required document's status (draft, in_review,
   approved) and roll the set up to the single least-complete status
   present, or "approved" if nothing was required.
6. The other-planning-documents set is compliant only when the
   roll-up status is approved and every required document has no
   outstanding content or linkage issues.

## Pitfalls

- Treating "the document exists" as sufficient -- an existing AIT plan
  interface or analysis plan with missing content fields or
  unreferenced requirement identifiers is not complete, and both gap
  types must be reported even when the other is clean.
- Rolling the overall status up from only the documents that happen to
  be on file and ignoring a required document that was never created
  -- a missing required document must dominate the roll-up, not be
  silently skipped.
- Letting one approved document mask a draft one -- the set-level
  status is the least-complete status present, so an approved AIT plan
  interface next to a draft analysis plan still leaves the programme
  at draft.
- Requiring an AIT plan interface or analysis plan for requirements
  verified by inspection or review of design -- those methods do not
  trigger a clause 5.2.8.3 "other" document in this leaf's scope, and
  flagging them as missing is a false finding.

## Behavior contract (gate 3)

The applicability, completeness, requirement-linkage, and status
roll-up logic is exercised by the gate 3 contract test:
scripts/test_e1002_other_planning_docs.py against
scripts/e1002_other_planning_docs_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e1002_other_planning_docs.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

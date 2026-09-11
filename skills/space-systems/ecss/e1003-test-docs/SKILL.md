---
name: e1003-test-docs
description: "Use when producing the test documentation set required by ECSS-E-ST-10C §4.3.3: draft the Assembly, Integration and Test (AIT) plan, the Test Specification (TSPE), the Test Procedure (TPRO), and the Test Report; verify each document carries the mandatory control fields (type, issue number, date, approval status); confirm the TSPE and TPRO trace every item to a recorded test requirement; check that document sequencing is respected (AIT plan approved before TSPE is released, TSPE approved before TPRO is released, TPRO approved before the Test Report is issued); and flag any missing document, broken traceability link, or sequence violation before the test campaign proceeds. Trigger: ecss, e-st-10-system-scope, test-documentation, ait-plan, tspe, tpro, test-report, document-control, traceability."
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
  tags: [ecss, e-st-10-system-scope, test-documentation, ait-plan, tspe, tpro, test-report, document-control, traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS E-ST-10C — Test Documentation Set (space-systems/ecss/e1003-test-docs)

Use when the task is to produce and control the test documentation set
required by ECSS-E-ST-10C §4.3.3 — defining the AIT plan, the Test
Specification (TSPE), the Test Procedure (TPRO), and the Test Report,
and verifying that the set is complete, traceable, and sequenced before
the test campaign begins.

## Domain quick reference

- §4.3.3 mandates four document types for any test campaign: the AIT
  plan (schedules and resources the campaign), the TSPE (specifies what
  to test and the pass/fail criteria), the TPRO (step-by-step execution
  instructions), and the Test Report (records results and dispositions).
  Each document type belongs to exactly one category within the set;
  a set that omits any of the four is incomplete.
- Every document must carry document-control fields: a type identifier,
  an issue number (positive integer), an issue date, and an approval
  status drawn from DRAFT, APPROVED, RELEASED, or SUPERSEDED. A
  document without a valid issue number or date has not entered
  configuration control and cannot gate a test campaign.
- Traceability is required for the TSPE and TPRO: each must reference
  at least one recorded test requirement by identifier. The AIT plan
  and Test Report are not required to carry forward requirement traces,
  but the TSPE must establish them and the TPRO must inherit them.
  A TSPE or TPRO with no trace entries is a traceability gap.
- Document sequencing follows the campaign lifecycle: the AIT plan must
  reach APPROVED status before the TSPE is released; the TSPE must
  reach APPROVED before the TPRO is released; the TPRO must reach
  APPROVED before the Test Report is issued. Releasing a downstream
  document while its predecessor is still in DRAFT is a sequence
  violation, not merely an advisory.

## Workflow

1. Inventory the planned test campaign and confirm which of the four
   document types (AIT_PLAN, TSPE, TPRO, TEST_REPORT) are present in
   the documentation set. Record any type that is absent; the set is
   not ready for the sequence check until all four are accounted for.
2. For each document, verify the document-control fields: confirm the
   type identifier matches a recognized value, the issue number is a
   positive integer, the date is populated, and the status is one of
   DRAFT, APPROVED, RELEASED, or SUPERSEDED. Flag any document that
   fails these checks before proceeding.
3. Check traceability for the TSPE and TPRO: each must list at least
   one requirement identifier, and every listed identifier must appear
   in the approved test-requirements register. Flag a document with an
   empty trace list or with a trace pointing to an unregistered
   identifier.
4. Evaluate document sequencing: confirm the AIT plan is at APPROVED
   or later before the TSPE is at RELEASED or later; confirm the TSPE
   is at APPROVED or later before the TPRO is at RELEASED or later;
   confirm the TPRO is at APPROVED or later before the Test Report is
   at RELEASED or later. Record any predecessor-not-ready violation.
5. Aggregate all findings by document type. A test documentation set
   is compliant only when the missing-document list is empty, every
   document passes its field and traceability checks, and no sequence
   violation is recorded.

## Pitfalls

- Treating an incomplete set as ready because the available documents
  are individually valid — a campaign cannot start without all four
  document types, regardless of the status of those already present.
- Accepting a TSPE or TPRO with trace entries that do not appear in the
  registered test-requirements list — a dangling trace is as problematic
  as no trace because it cannot be verified against a recorded
  requirement.
- Reading "no sequence violation" as compliant when a predecessor
  document is absent entirely — if the AIT plan does not exist, the
  TSPE cannot be sequenced against it, and the absence is itself a
  finding.
- Treating DRAFT status as equivalent to APPROVED for sequencing
  purposes — a predecessor in DRAFT has not been formally reviewed and
  cannot gate the release of a downstream document.

## Behavior contract (gate 3)

The document-completeness, field-validation, traceability, and
sequence-readiness logic is exercised by the gate 3 contract test:
scripts/test_e1003_test_docs.py against
scripts/e1003_test_docs_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1003_test_docs.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

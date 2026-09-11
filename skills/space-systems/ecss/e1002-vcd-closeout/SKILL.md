---
name: e1002-vcd-closeout
description: "Use when closing out the Verification Control Document (VCD) per ECSS-E-ST-10C §5.4.4.1: determine the compliance status of each verifiable requirement as compliant, not compliant, or waived; collect every linked verification record (test report, analysis report, inspection record, review-of-design output); assign compliant when all records are passed or not applicable, not compliant when any record is open or failed and no approved waiver is on file, and waived when a formal approved waiver document reference is recorded against the requirement. Flag rows with no verification evidence, open records blocking closeout, and failed records without an approved waiver reference. Produce a VCD closeout summary with counts by status and a list of all blocking findings. Trigger: ecss, e-st-10-system-scope, vcd-closeout, verification-control-document, compliance-status, waiver, verification-records, requirement-closeout."
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
  tags: [ecss, e-st-10-system-scope, vcd-closeout, verification-control-document, compliance-status, waiver, verification-records, requirement-closeout]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — VCD Closeout (space-systems/ecss/e1002-vcd-closeout)

Use when the task is closing out the Verification Control Document (VCD)
under ECSS-E-ST-10C §5.4.4.1 — assigning a compliance status (compliant,
not compliant, or waived) to each verifiable requirement by reconciling its
linked verification records, recording any accepted waiver references, and
producing a summary of blocking findings that prevent final VCD closure.

## Domain quick reference

- The VCD is a matrix where each row corresponds to one verifiable
  requirement and carries a set of verification records: test reports,
  analysis reports, inspection records, or review-of-design (RoD) outputs.
  Closing out the VCD means every row must carry a settled compliance status
  before the review gate can be passed.
- Three compliance statuses are defined under §5.4.4.1. Compliant: every
  verification record linked to the requirement is closed with a passed
  result, or is marked not applicable with a documented rationale. Not
  compliant: at least one record is still open (pending completion) or has
  a failed result and no accepted waiver is on file. Waived: a formal
  deviation or waiver document has been approved and its reference is
  recorded in the VCD row; the waiver replaces the compliance evidence for
  that requirement.
- A VCD row with no verification records at all is a not-compliant finding:
  the absence of evidence is not evidence of compliance.
- Open records are the most common blocker at a formal review; the closeout
  check must surface each open record ID so the responsible verifier can be
  contacted.

## Workflow

1. Collect every VCD row for the scope under review. Each row must carry a
   requirement identifier, a list of linked verification records (each with
   a unique record identifier and an outcome: passed, failed, open, or
   not_applicable), and optionally an approved waiver document reference.
2. Validate that every record outcome is one of the four recognized values.
   Reject and report any row containing an unrecognized outcome before
   proceeding — an unknown outcome string indicates a data-entry error in
   the VCD that must be corrected at the source.
3. For each row, determine the compliance status in this order:
   a. If an approved waiver reference is recorded (non-empty string), assign
      waived. The waiver has already been reviewed at the appropriate approval
      level; no further record reconciliation is needed for that row.
   b. If the row has no linked verification records, assign not_compliant and
      record a no_verification_records finding.
   c. Collect all records with outcome open (blocking closeout) and all
      records with outcome failed (failed without an approved waiver).
      If either list is non-empty, assign not_compliant and record findings
      for open records and for failed records separately.
   d. Otherwise all records are passed or not_applicable: assign compliant.
4. Aggregate the row results into a VCD closeout summary: count requirements
   by status (compliant, not_compliant, waived) and flatten all per-row
   findings into a single blocking-findings list.
5. The VCD is ready to close only when the not_compliant count is zero. Any
   remaining not_compliant rows must be resolved — either by completing open
   verification activities, approving waivers for accepted failures, or
   correcting data errors — before the gate can be passed.

## Pitfalls

- Treating a row with no verification records as compliant by default:
  an empty records list is itself a not-compliant finding because no
  verification evidence has been captured for the requirement.
- Collapsing open and failed records into a single "incomplete" category:
  they require different resolution actions (a failed record needs a waiver
  or re-test; an open record needs the verifier to complete and close the
  activity) and must be surfaced separately so action owners are clear.
- Accepting a non-empty waiver_ref field without confirming it references an
  approved document: the closeout logic trusts the reference is valid; the
  review board must separately audit that the waiver document exists and
  carries the required approval signatures before accepting the waived status.
- Marking a row compliant when all records are not_applicable without
  at least one passed record: a row where every record is not_applicable
  may indicate that no verification was actually performed. This is not
  caught by the closeout logic itself and should be flagged during the
  review board's walkthrough of waived/not-applicable rows.

## Behavior contract (gate 3)

The compliance-status determination, waiver handling, open-record detection,
failed-record detection, and summary aggregation logic is exercised by the
gate 3 contract test: scripts/test_e1002_vcd_closeout.py against
scripts/e1002_vcd_closeout_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_vcd_closeout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

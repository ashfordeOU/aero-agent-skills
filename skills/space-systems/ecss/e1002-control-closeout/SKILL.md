---
name: e1002-control-closeout
description: "Use when control and close out product verification under ECSS-E-ST-10-02 clause 5.4.1: confirm every verification control document row reached a closed status with evidence cited, confirm each closure taken against a waiver names a waiver the authority actually approved, confirm no nonconformance is still open, and confirm the verification database was delivered machine-readable in the agreed format covering every row the control document holds. Trigger: ecss, e-st-10-02c, verification-closeout, verification-control-document, waiver-approval, nonconformance, verification-database, electronic-delivery."
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
  tags: [ecss, e-st-10-02c, verification-closeout, verification-control-document, waiver-approval, verification-database]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Verification — Control and Close-out (space-systems/ecss/e1002-control-closeout)

Use when the task is to control verification through the verification
control document and finally close it out under ECSS-E-ST-10-02 clause
5.4.1 -- including the delivery of the verification database in
electronic form.

## Domain quick reference

- Close-out is conjunctive. Every requirement closed, every
  nonconformance dispositioned, every invoked waiver approved, and the
  database delivered. A delivered database does not offset an open
  nonconformance, and a clean nonconformance log does not offset a
  partial delivery.
- Closing against a waiver is a real closure, but only when the waiver
  reference names something the granting authority actually approved.
  An unapproved waiver closes nothing -- it records that somebody
  wanted to.
- A missing waiver reference and an unapproved one are different
  findings: one is unrecorded, the other was recorded and refused.
- Every closed row cites evidence, including rows closed with a waiver.
  The waiver explains why the requirement was not met; it does not
  excuse the absence of a record of what was actually found.
- An open row needs no evidence yet. Applying the evidence check to
  unfinished work generates findings against rows that are simply not
  done.
- A nonconformance with no recorded state is open. The default runs
  toward stopping, because an unanswered question must not close a
  programme.
- The database is checked for completeness against the control
  document's own rows. Delivered-but-partial is the characteristic
  failure of this clause: the programme ends, and the evidence trail
  has holes nobody will ever go back and fill.
- Machine-readability is part of delivery, not a nicety. A scanned
  matrix satisfies "delivered" and defeats every later query the
  database exists to answer.

## Workflow

1. Walk the control document rows and list every one not at a closed
   status.
2. For each row closed with a waiver, confirm the reference is present
   and names an approved waiver.
3. Confirm every closed row cites evidence.
4. Confirm no nonconformance remains open, treating an absent state as
   open.
5. Check the database delivery: delivered at all, in the agreed format,
   machine-readable, and carrying every row the control document holds.
6. Declare close-out only when nothing is open and no finding stands.

## Pitfalls

- Closing a programme on a waiver that was raised but never approved,
  which converts an unmet requirement into a closed one by paperwork.
- Accepting a waiver closure with no evidence of what was actually
  found, leaving no record of the departure the waiver permitted.
- Treating an unstated nonconformance state as dispositioned, so an
  unanswered finding disappears at exactly the moment it matters most.
- Checking the database is delivered without checking it is complete.
  Partial delivery passes every presence check and is the failure this
  clause exists to prevent.
- Delivering a non-machine-readable export, which satisfies the word
  "delivered" and defeats the purpose.
- Trading one close-out condition against another -- a strong evidence
  set does not compensate for an undelivered database.

## Behavior contract (gate 3)

The row-status, waiver-approval, closure-evidence, nonconformance and
database-delivery-completeness logic is exercised by the gate 3 contract
test: scripts/test_e1002_control_closeout.py against
scripts/e1002_control_closeout_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1002_control_closeout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

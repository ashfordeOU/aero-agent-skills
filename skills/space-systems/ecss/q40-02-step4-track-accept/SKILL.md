---
name: q40-02-step4-track-accept
description: "Verify the tracking, acceptance and communication of space-system hazards under ECSS-Q-ST-40-02C clause 5.2.4, step 4. Use when the task is driving each hazard report through its hazard-log status states in a legal order, rejecting a jump from open straight to accepted, matching the acceptance authority to the residual severity so a catastrophic residual is never signed at working level, grading the acceptance record for its rationale, evidence reference, named signatory and date, and listing the audiences each status change still owes a notification. Trigger: ecss, q-st-40-02c, hazard-log-status-control, hazard-report-state-transition, residual-risk-acceptance-authority, hazard-acceptance-record, hazard-stakeholder-notification, hazard-report-reopening."
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
  tags: [ecss, q-st-40-02-hazard-analysis-scope, q40-02-step4-track-accept, hazard-log-status-control, hazard-report-state-transition, residual-risk-acceptance-authority, hazard-acceptance-record, hazard-stakeholder-notification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hazard Analysis — Step 4, Track, Communicate, Accept (space-systems/ecss/q40-02-step4-track-accept)

Use when the task is step 4 of the ECSS-Q-ST-40-02C clause 5.2 process —
holding the hazard log's status control, deciding who is allowed to
accept a residual risk, grading the acceptance record, and working out
who has not yet been told.

## Domain quick reference

- The status states exist to separate three different things a reader
  otherwise cannot tell apart: a hazard nobody has worked, a hazard
  whose controls are in place, and a hazard whose residual risk
  somebody has signed for. Open, in-work, controlled, verified,
  accepted and closed are the sequence, and skipping one erases the
  distinction it was carrying.
- Reopening is legal and forward-skipping is not. New information can
  send a report back to in-work from controlled, verified or accepted,
  because that is what a live hazard log is for; a jump from open to
  accepted means the controls were never recorded, whatever the entry
  says.
- Acceptance authority is set by the residual severity, not by who is
  available. A catastrophic residual goes to the customer safety
  review board, a critical one to the project manager, a major one to
  the product assurance manager; a minor one can be signed at working
  level. A signature from a level above the minimum is fine — the
  check is a floor.
- An acceptance record is four things: why the residual is acceptable,
  what evidence supports that, who signed, and when. An acceptance
  missing the rationale is a status change wearing the word accepted,
  and it reads identically in a summary count.
- Every status change has an audience, and the audience widens as the
  report advances. Entering accepted owes the customer a notification;
  entering controlled owes operations engineering, because operations
  is where the control has to be honoured. A change communicated to
  nobody leaves the people acting on the hazard working from the
  previous state.

## Workflow

1. Validate each hazard report: identifier, residual severity, a status
   history that starts at open, an acceptance authority where one is
   claimed, an acceptance record and the audiences already notified.
2. Replay the status history transition by transition and report each
   illegal move by name, rather than reporting only the final state.
   The illegal move is the evidence; the final state looks fine.
3. Where the report has reached accepted or closed, check the
   acceptance authority against the minimum its residual severity
   requires, and treat an unrecorded authority as its own finding
   rather than as a missing field.
4. Grade the acceptance record field by field. A blank string is a
   missing field, not a present one.
5. Work out the outstanding notifications for the report's current
   state and list each audience still owed one.
6. Aggregate across the log: the state distribution, the reports not
   yet accepted, and the reports carrying findings. The log is under
   control only when no report carries one.

## Pitfalls

- Reading the final state and stopping. A report sitting in accepted
  looks identical whether it walked every state or jumped there from
  open, and only the replay tells them apart.
- Blocking a reopening because it looks like a regression. A hazard
  log that cannot go backwards stops reflecting the project the first
  time a control is found to be ineffective.
- Letting the available signatory set the acceptance level. The
  authority floor is a property of the residual severity; a
  catastrophic residual signed at working level is the single defect
  this check exists to catch.
- Counting an acceptance record as present because the object exists.
  Four fields carry it, and a blank rationale is the one that goes
  missing, because it is the one that takes thought to write.
- Treating notification as a courtesy that follows the decision.
  Operations engineering acting on the previous state of a hazard is
  an operational consequence, not an administrative one.

## Behavior contract (gate 3)

The status-transition legality, history replay, acceptance-authority
floor, acceptance-record grading, notification-audience and log
aggregation logic is exercised by the gate 3 contract test:
scripts/test_q40_02_step4_track_accept.py against
scripts/q40_02_step4_track_accept_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q40_02_step4_track_accept.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q1009-internal-meeting
description: "Run the internal nonconformance review board sitting of ECSS-Q-ST-10-09 clause 5.2.2.1. Use when a supplier convenes its own board on internally raised nonconformances and the sitting, its agenda and its minutes all have to stand up to later scrutiny. Judges the roster against the mandatory board functions and against the voting quorum separately, because one shortfall is repaired by a delegate and the other by a reconvene; admits an agenda item only once its review package is complete, deferring the rest rather than deciding on evidence that is not there; and holds every item heard to a decision record naming disposition, rationale, owner and due day. Trigger: ecss, q-st-10-09, internal-nonconformance-review-board, nrb-voting-quorum, ncr-review-package, nrb-agenda-admissibility, nrb-minutes-completeness, internal-disposition-decision-record."
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
  tags: [ecss, q-st-10-09-nonconformance-control-scope, q1009-internal-meeting, internal-nonconformance-review-board, nrb-voting-quorum, ncr-review-package, nrb-agenda-admissibility, internal-disposition-decision-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Nonconformance Control — Internal Review Board Sitting (space-systems/ecss/q1009-internal-meeting)

Use when the task is the internal review-board step of ECSS-Q-ST-10-09
clause 5.2.2.1 — convening the supplier's own nonconformance review
board, deciding which raised nonconformances that board may actually
hear, and turning what it decides into a record that survives audit.

## Domain quick reference

- The board is a standing body with appointed functions, not whoever is
  free that afternoon. Quality chairs it because the departure is a
  quality event; design engineering has to be there because only the
  design authority can say what the item was meant to do; production has
  to be there because only the builder knows what the item actually is.
  A sitting missing any of those three has no basis for a disposition.
- Attendance and voting are two different questions. An advisory member
  — configuration management, supply chain, safety — counts as sitting
  and can close an absent-function gap in expertise, but does not count
  toward the quorum fraction of the appointed voting membership. The two
  shortfalls are therefore reported separately: a missing function is
  repaired by a delegate with the same authority, a missing quorum only
  by reconvening.
- An agenda item is only heard once its review package is complete. The
  package is the nonconformance report itself, the identification of the
  affected item, the effectivity list saying which units carry the
  departure, the description, the cause analysis, the consequence
  assessment and the proposed disposition. An item short of any of these
  is deferred, because a board that decides without them is recording a
  preference rather than a disposition.
- Deferral is a normal outcome of a valid sitting, not a defect in it. A
  properly constituted board that defers three of five items has held a
  valid sitting with an uncleared agenda, and those are separate
  verdicts with separate repairs.
- The record is the deliverable. Each item heard leaves with a
  disposition, the rationale that supports it, a named accountable owner
  and a due day. A disposition without a rationale cannot be reviewed
  later; a disposition without an owner and a due day never closes.

## Workflow

1. Validate the roster: one appointed member per board function, each
   marked present or absent and voting or advisory. A duplicated
   function or a non-boolean attendance flag is an input error.
2. Test the sitting twice — the mandatory board functions actually
   sitting, and the attending share of the appointed voting membership
   against the quorum fraction — and report both verdicts. Absorb the
   representation error of an exactly-at-fraction attendance with a
   named tolerance rather than lowering the appointed fraction.
3. Walk the agenda in order and test each item's review package against
   the required contents. Name the gaps; an item with gaps is
   inadmissible and is deferred.
4. Match decision records to the items actually heard. A record is
   complete only when disposition, rationale, owner and due day are all
   populated; a blank string is a gap, a due day of zero is a value.
5. Report the open minutes — items heard with no record, and records
   missing fields — plus any record attached to a deferred or unknown
   item, which is a record with nothing to attach to.
6. Declare the sitting valid only when quorum holds and the minutes are
   complete, and report the cleared-agenda verdict alongside it.

## Pitfalls

- Counting advisory attendees toward the quorum. They are there for
  expertise, not authority; folding them into the fraction lets a board
  with two voting members present declare a quorum of five.
- Reading a full attendance count as a valid sitting. Five members in
  the room with design engineering absent is a quorum without the design
  authority, which is exactly the sitting that produces a use-as-is that
  the design authority never agreed to.
- Hearing an item whose cause analysis is still open. The board then
  disposes of a departure whose cause it does not know, and the
  disposition has to be reopened when the cause arrives.
- Treating a deferral as a failed meeting. The repair for a deferral is
  the missing package item, not a reconvened board, so merging the two
  verdicts sends the wrong repair.
- Minuting the disposition alone. Without the rationale the decision
  cannot be reviewed, and without an owner and a due day nobody is
  accountable for carrying it out.
- Leaving a decision record attached to an item that was never heard. It
  reads as a closed item in every later count while the underlying
  nonconformance is still open.

## Behavior contract (gate 3)

The roster validation, the mandatory-function and quorum tests, the
review-package admissibility check, the decision-record completeness
check, the minutes reconciliation and the overall sitting verdict are
exercised by the gate 3 contract test:
scripts/test_q1009_internal_meeting.py against
scripts/q1009_internal_meeting_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q1009_internal_meeting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

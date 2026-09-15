---
name: q60-class-1-buy-off-source-inspection
description: "Determine whether a witnessed source buy-off releases a Class 1 EEE lot under ECSS-Q-ST-60C clause 4.3.6: count the whole days of advance notice the procuring entity was given, decide from who was actually in the room whether the session was witnessed, waived under a referenced waiver or simply unwitnessed, check that the activities it sits on top of completed no later than the session itself, and cap the release at the pieces actually presented so unseen pieces stay at the manufacturer. Use when a session held at the supplier has to become a ship-or-hold decision with a quantity attached. Trigger: ecss, q-st-60c-clause-4-3-6, class-1-source-buy-off, buy-off-witness-attendance, witnessing-waiver-reference, buy-off-notice-period, presented-quantity-release-cap."
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
  tags: [ecss, q-st-60c-eee-class-1-scope, q60-class-1-buy-off-source-inspection, class-1-source-buy-off, buy-off-witness-attendance, witnessing-waiver-reference, buy-off-notice-period, presented-quantity-release-cap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts -- Witnessed Source Buy-Off (space-systems/ecss/q60-class-1-buy-off-source-inspection)

Use when the task is the clause 4.3.6 buy-off of ECSS-Q-ST-60C: a Class 1 lot
is finished at the manufacturer, a final acceptance session has been held in
front of a witness, and the question is whether the parts leave the premises
and how many of them do.

## Domain quick reference

- A buy-off is a session, not a signature. It has a date, a room, an
  attendance list and a quantity in front of the witness, and each of those
  four can fail independently of the others.
- Notice is what makes attendance possible. The call is counted in whole days
  from the day it was issued to the day of the session; a session called at
  short notice is not witnessed by a representative who could not get there.
- Witnessing is a question about roles, not headcount. A room full of the
  manufacturer's own quality staff is an unwitnessed session. A written waiver
  carrying its own reference and reason converts that into an admissible
  release; a waiver with no reference does not exist for this purpose.
- The buy-off sits on top of the activities that produced its evidence. One
  finishing after the session is out of sequence whatever the session found,
  because the evidence was not there on the day.
- The release is bounded by what was presented. Pieces the witness never saw
  are withheld rather than carried by the ones that were seen, so a short
  presentation gives a partial release and names the withheld balance.

## Workflow

1. Count the notice given from the call day to the session day and compare it
   with the notice period the contract asks for, refusing a session dated
   before its own call.
2. Read the attendance list for a role entitled to witness on behalf of the
   procuring entity, matching the role without regard to letter case.
3. Where nobody entitled attended, look for a waiver and demand both its
   reference and its reason before admitting it; otherwise the session stands
   unwitnessed.
4. Test every prerequisite activity for completion no later than the session
   day, and treat a required activity absent from the record as a finding of
   its own rather than a silent pass.
5. Cap the requested release at the presented quantity and report the withheld
   balance as a number, not as a note.
6. Release only when the session was admissible, in sequence, properly called
   and carrying no open major nonconformance; otherwise hold at the
   manufacturer and name every gate that failed.

## Pitfalls

- Treating attendance as witnessing. The manufacturer's own staff being in the
  room is the normal case and is not what the clause asks for.
- Admitting an unreferenced waiver. A waiver without a reference cannot be
  traced back to who granted it or why, so it cannot carry a release.
- Reporting only the first failing gate. Short notice, an out-of-sequence
  prerequisite and an open major nonconformance are three separate problems
  and the supplier needs all three, not the earliest one.
- Releasing the offered quantity because the session went well. The release
  follows the pieces presented; the balance stays where it is.
- Accepting a prerequisite that completed the week after the session. The
  session cannot have accepted evidence that did not yet exist.

## Behavior contract (gate 3)

The notice counting, witness and waiver states, prerequisite sequencing,
presented-quantity cap and the ship-or-hold disposition are exercised by the
gate 3 contract test:
scripts/test_q60_class_1_buy_off_source_inspection.py against
scripts/q60_class_1_buy_off_source_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_buy_off_source_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

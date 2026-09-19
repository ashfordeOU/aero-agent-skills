---
name: q2007-qs-reps
description: "Assess a test centre's quality and safety representative appointments under ECSS-Q-ST-20-07C clause 5.3.4. Use when the register has to show each representative really holds stop-test authority and direct access to management rather than a title: grade the appointment form, the authorities the role must carry, and independence from the test-execution reporting line, count the escalation hops to top management, refuse a verbal appointment as cover, and compute the authority-coverage ratio and the per-activity gaps where no sound quality or safety representative stands. Trigger: ecss, q-st-20-07-test-centre, q2007-qs-reps, quality-and-safety-representative-appointment, test-centre-stop-test-authority, direct-management-access-escalation, representative-independence-from-test-execution, test-activity-representative-coverage."
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
  tags: [ecss, q-st-20-07-test-centre, q2007-qs-reps, quality-and-safety-representative-appointment, test-centre-stop-test-authority, direct-management-access-escalation, representative-independence-from-test-execution, test-activity-representative-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test Centre — Quality and Safety Representatives (space-systems/ecss/q2007-qs-reps)

Use when the task is the appointment step of ECSS-Q-ST-20-07C clause 5.3.4 --
naming the quality and safety representatives of a test centre, fixing the
authority each appointment carries, and showing that every test activity in
scope is actually covered by one.

## Domain quick reference

- The appointment is not a courtesy title. Its whole purpose is to put a
  person in the room who can stop a test that is already running and who can
  say so to top management without asking the people running the test for
  permission. An appointment that cannot do those two things has been made
  in name only.
- Three properties decide whether an appointment is sound, and none of them
  substitutes for another. The first is form: an appointment that exists only
  as a shared understanding cannot be pointed at during a test, which is the
  one moment it matters. It has to be recorded in writing.
- The second is authority. The role fixes the set. Both roles must carry
  stop-test authority and direct management access; the quality role must
  additionally be able to raise a nonconformance, because a quality
  representative who can stop a test but cannot record why has stopped it
  for nothing.
- The third is independence. A representative who reports into the line that
  owns the delivery of the test -- the test conductor, the campaign manager,
  the facility operations manager, the schedule owner -- is asking the party
  that carries the cost of the stop to approve the stop.
- Escalation length is graded separately from the reporting line, because the
  two fail independently. A representative can report to the centre director
  and still have two intermediaries standing between them and top management.
  Direct access means no intermediary at all.
- Coverage is per test activity, not per centre. Every activity needs at
  least one quality representative and one safety representative whose
  appointment is itself sound: a deficient appointment does not provide
  cover, because the cover it was supposed to provide is exactly the
  authority it failed to carry.
- The authority-coverage ratio summarises the register in one number for a
  management review, but it is a summary and never a substitute for the gap
  list: a register can score well and still leave one campaign uncovered.

## Workflow

1. Build the register. Give each entry an identifier, the role held, how the
   appointment was made, the authorities it carries, the position it reports
   into, the chain of intermediaries up to top management, and the test
   activities it covers. List the activities in scope separately.
2. Refuse the register before grading it when a role, an appointment form or
   an authority token is unrecognised, when an escalation chain is not a
   sequence of positions, or when an entry identifier repeats.
3. Grade form, authority and independence for each entry. Name every missing
   authority individually rather than reporting one aggregate failure -- the
   remedy differs per authority.
4. Count the escalation hops and flag an indirect chain even when the
   reporting position itself is outside the test-execution line.
5. Cross the sound appointments against the activity scope. Report an
   activity as a gap for each role that has no sound representative on it,
   and reject an entry that claims an activity outside the declared scope.
6. Report the authority-coverage ratio, the stop-test-capable entries, the
   deficient entries and the per-activity gaps. The register is sound only
   when both the deficient list and the gap map are empty.

## Pitfalls

- Accepting a well-understood arrangement as an appointment. The written form
  is what survives the shift handover and the argument at 03:00.
- Reading "reports to the director" as direct management access. The
  reporting line and the escalation chain are different facts and are graded
  separately here for that reason.
- Letting a quality representative with strong authority stand as the safety
  cover for an activity. The roles carry different authority sets and neither
  inherits the other's coverage.
- Counting a deficient appointment as coverage because a name is present in
  the cell. A name without stop-test authority is an uncovered activity that
  looks covered.
- Treating the authority-coverage ratio as the verdict. It is an aggregate;
  the per-activity gap map is the thing a review has to close.
- Appointing a representative into the test-execution line because that is
  where the technical knowledge sits, and expecting the stop to survive the
  schedule pressure that follows.

## Behavior contract (gate 3)

The appointment validation, authority grading, independence and escalation
checks, coverage-gap derivation and register roll-up are exercised by the
gate 3 contract test: scripts/test_q2007_qs_reps.py against
scripts/q2007_qs_reps_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2007_qs_reps.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

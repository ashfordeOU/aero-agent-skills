---
name: q7028-repair-operator-qualification
description: "Assess whether an operator is qualified for the class of board repair in front of them. Use when a repair certification is issued, renewed or audited: it reads the training hours and the practical sample set that class demands, grades the samples actually made against the accept count and reports first-pass yield, applies the near-vision check validity at the assessment date, tests currency since the operator last worked that class, dates the certificate expiry, and names the action still owed — full training, another practical set, or nothing. Trigger: ecss, q-st-70-28c-board-repair, pcb-repair-operator-qualification, pcb-repair-training-hours, pcb-repair-acceptance-samples, pcb-repair-operator-currency, pcb-repair-certificate-expiry."
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
  tags: [ecss, q-st-70-28c-board-repair, q-st-70-28c, q7028-repair-operator-qualification, pcb-repair-operator-qualification, pcb-repair-training-hours, pcb-repair-acceptance-samples, pcb-repair-operator-currency, pcb-repair-certificate-expiry]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Repair Operator Qualification (space-systems/ecss/q7028-repair-operator-qualification)

Use when the task is the personnel clause of ECSS-Q-ST-70-28C: somebody is
about to repair a board, and the question is whether their certification
actually covers this class of repair, today, on the evidence in their record.

## Domain quick reference

- Qualification is per repair class, not per operator. Conductor work, land
  work, plated holes, base material, coating and component replacement each
  carry their own hours and their own sample set, and a certificate in one of
  them says nothing about another.
- The sample set is the real gate; the hours only make it reachable. A class
  states how many practical samples are made and how many of those must be
  accepted, and the two numbers are separate — some classes tolerate a reject,
  the hardest ones do not.
- First-pass yield is worth reporting even when the set passes. An operator
  who scraped the accept count is qualified and is also the one to watch, and
  the ratio is the only place that shows.
- The near-vision check is part of the qualification, not of occupational
  health. Board repair is done under magnification at the limit of what an eye
  resolves, and a check that has lapsed invalidates the certificate as surely
  as a missing sample would.
- Currency and certification are different clocks. A certificate can be years
  from expiry while the operator has not touched the class for long enough
  that the hand is gone, and only the shorter clock catches that.
- Losing currency costs a practical set, not the course. The knowledge is
  still there; the hand is what lapsed, so requalification is proportionate to
  what was actually lost.
- Missing training outranks everything else owed. An operator short of hours
  cannot be brought back with a sample set, so the action reported is the
  larger one even when a smaller one is also true.

## Workflow

1. Resolve the repair class and read its training hours, samples required and
   samples that must be accepted.
2. Compare the recorded training hours against the requirement, and mark full
   training where they fall short.
3. Grade the practical set: enough samples made, enough accepted, and the
   first-pass yield the operator achieved.
4. Test the near-vision check against its validity period at the assessment
   date.
5. Test currency against the date the operator last worked this class, and
   treat no recorded work as a lapse.
6. Date the certificate expiry from its issue and compare it to the assessment
   date.
7. Return the verdict with the action still owed, taking the larger action
   where several apply; qualified only when there are no findings.

## Pitfalls

- Reading one certificate as covering the bench. The operator is qualified for
  conductor work and is handed a plated hole, and the certificate in the file
  makes the assignment look correct.
- Counting samples made and ignoring samples accepted. A full set was produced
  and half of it was rejected, and the operator is qualified on the count.
- Treating the vision check as somebody else's record. It sits with
  occupational health, nobody brings it into the qualification, and it has
  been lapsed for a year.
- Running currency off the certificate date. The certificate is valid for two
  years, the operator has not done the work for eighteen months, and one clock
  cannot see the other.
- Sending a lapsed-currency operator back through the whole course. The
  scarcest skill on the shop floor is taken off the bench for a week to
  relearn what was never lost.
- Reporting the smallest action owed. Both a sample set and missing hours are
  outstanding, the record says "practical samples", and the operator returns
  still short of the training.

## Behavior contract (gate 3)

Per-class training and sample requirements, the made-against-accepted sample
grading with its first-pass yield, near-vision validity, the separate currency
clock, certificate expiry dating and the precedence between full training and
a practical set are exercised by the gate 3 contract test:
scripts/test_q7028_repair_operator_qualification.py against
scripts/q7028_repair_operator_qualification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7028_repair_operator_qualification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

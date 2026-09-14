---
name: q6013-class-1-procurement-overview
description: "Assess whether a purchasing arrangement for class 1 commercial parts discharges every duty behind ECSS-Q-ST-60-13C clause 4.3.1: refuse an undeclared or unrecognized supply channel, raise the manufacturer-traceability and counterfeit-avoidance duties an open-market or independent route adds to the base register, require each duty to name a party from the permitted roles and cite evidence, hold an assigned but unevidenced duty open, report an assignment the register does not carry, and take the discharged share against the declared floor. Use when a purchasing route for the highest assurance parts has to be judged. Trigger: ecss, q-st-60-13c-clause-4-3-1, class-1-procurement-duty-register, commercial-part-supply-channel, open-market-source-extra-duties, procurement-duty-evidence, procurement-duty-coverage-floor."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-procurement-overview, q-st-60-13c-clause-4-3-1, class-1-procurement-duty-register, commercial-part-supply-channel, open-market-source-extra-duties, procurement-duty-evidence, procurement-duty-coverage-floor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Commercial Parts — Procurement Overview (space-systems/ecss/q6013-class-1-procurement-overview)

Use when the task is the purchasing framework of ECSS-Q-ST-60-13C clause 4.3.1
— establishing which duties a purchase of commercial electrical, electronic
and electromechanical parts has to discharge so that what arrives meets the
highest assurance expectations, and who in the arrangement is answerable for
each of them.

## Domain quick reference

- A class 1 purchase is judged on the duties discharged around it, not on the
  parts alone. The base register is the same for every purchase: specify the
  part requirements, flow them down to the supplier, confirm the supplier is
  approved for that supply, verify what is delivered against the requirements,
  and record the traceability.
- The supply channel decides the size of the register. A purchase direct from
  the manufacturer or through its franchised network inherits the
  manufacturer's own chain of custody. A purchase from an independent
  distributor or the open market does not, so that route adds two duties:
  rebuild traceability back to the manufacturer, and screen against
  counterfeit supply. An undeclared channel cannot be graded at all, because
  the register it has to meet is unknown.
- A duty is discharged only when a named party owns it and evidence is cited.
  A duty assigned to nobody, assigned to a party outside the arrangement, or
  assigned with no evidence reference is open — three different reasons that
  are repaired three different ways, so the reason is carried with the duty.
- An assignment naming a duty the register does not carry is a signal in its
  own right: either the channel was recorded wrongly or the arrangement is
  working to a register other than the one declared.
- Coverage is the discharged share of the register. It is a ratio of small
  integers, so an exactly-met floor can land a few units in the last place
  low; that is a representation question absorbed by a named tolerance, not a
  reason to lower the floor.
- Coverage meeting its floor does not close the assessment. An open duty is a
  finding whether or not the remaining duties carry the arrangement over the
  declared share.

## Workflow

1. Validate the declared supply channel and refuse an undeclared or
   unrecognized one; do not default it to the direct route.
2. Build the duty register for that channel: the base duties plus the extra
   duties the channel adds.
3. Validate each assignment: normalize the duty and the owner, require a
   string evidence reference, and reject a duty assigned twice.
4. Grade every duty in the register: discharged, or open carrying the reason —
   unassigned, owner outside the permitted roles, or no evidence cited.
5. Record any assignment naming a duty outside the register as its own
   finding.
6. Take the discharged share of the register and compare with the declared
   coverage floor, absorbing representation error at the boundary with a named
   tolerance.
7. Report the graded register, the open duties, the coverage figure and a
   verdict carrying every finding, not only the first.

## Pitfalls

- Grading an open-market purchase against the direct-purchase register. The
  two extra duties are exactly what the open route removes from the
  manufacturer's side, so omitting them grades the riskiest channel most
  leniently.
- Treating an assignment as a discharge. Naming an owner moves the duty to
  somebody; it does not evidence that the duty was done, and the unevidenced
  case is the one that survives to the delivery review.
- Accepting an owner outside the arrangement. A duty parked on a party with no
  standing in the purchase is unowned in practice, and reads as covered on the
  register.
- Reading a met coverage floor as a clean arrangement. The floor is an
  aggregate; a single open traceability duty can sit under a comfortable
  coverage figure and still be the defect that stops the delivery.
- Defaulting an undeclared channel. The channel is the input that sizes the
  register, so guessing it silently picks which duties will never be asked
  for.
- Stopping at the first open duty. The purchaser needs the whole open list to
  close them in one pass rather than one review round each.

## Behavior contract (gate 3)

The supply-channel validation, register construction per channel, assignment
validation, per-duty grading with its reason, extraneous-assignment detection,
coverage ratio and the overall verdict are exercised by the gate 3 contract
test: scripts/test_q6013_class_1_procurement_overview.py against
scripts/q6013_class_1_procurement_overview_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6013_class_1_procurement_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q60-class-1-incoming-inspection
description: "Use when a goods-in bench has to become a bonded-store or quarantine disposition. Assess whether a Class 1 EEE delivery may enter the bonded store on arrival at the procuring entity under ECSS-Q-ST-60C clause 4.3.7: name every document the evidence pack travelling with the parts is missing, take transit damage out of the accepted quantity instead of leaving it in, judge the shipping seal and the static-protective bag as findings about the pieces inside rather than about the wrapping, and resolve the date code to its build week so a lot that aged past its threshold before it ever arrived owes a solderability re-test. Trigger: ecss, q-st-60c-clause-4-3-7, class-1-arrival-inspection, class-1-evidence-pack-on-arrival, transit-damage-accepted-count, static-protective-bag-arrival-check, date-code-solderability-threshold, bonded-store-entry-disposition."
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
  tags: [ecss, q-st-60c-eee-class-1-scope, q60-class-1-incoming-inspection, class-1-arrival-inspection, class-1-evidence-pack-on-arrival, transit-damage-accepted-count, static-protective-bag-arrival-check, date-code-solderability-threshold, bonded-store-entry-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 EEE Parts -- Arrival Inspection (space-systems/ecss/q60-class-1-incoming-inspection)

Use when the task is the clause 4.3.7 arrival check of ECSS-Q-ST-60C: a Class 1
delivery has reached the premises of the procuring entity and been unpacked on
the goods-in bench, and the question is whether it enters the bonded store, and
with how many pieces.

## Domain quick reference

- Arrival is the first point at which the procuring entity holds the parts and
  the last at which the shipment can be refused as a shipment. What is not
  caught here is caught at kitting, with the build already committed to it.
- The evidence pack travels with the parts. A conformity certificate, the lot
  acceptance report, the buy-off record and the screening data either arrived
  or did not; a document said to be following on has not arrived.
- Transit damage is a quantity question, not only a report. Damaged pieces
  leave the accepted count on the bench, so the store receives the number that
  is really usable rather than the number on the note.
- The seal and the static-protective bag are findings about the pieces they
  contained. A Class 1 part that travelled in an opened bag has an unknown
  handling history, whatever it looks like under the microscope.
- Age on arrival is fixed by the date code, not by the delivery date. The code
  names a build week, and a lot already past the declared threshold when it
  reaches the door owes a solderability re-test before it is drawn.

## Workflow

1. Reconcile the bench count with the delivery note, reporting the difference
   with its sign so a short delivery and an over-delivery are distinguishable.
2. Remove the pieces damaged in transit from the accepted quantity and refuse a
   damage count larger than the pieces actually counted.
3. Read the shipping seal, the static-protective bag and the humidity state,
   raising each as its own finding rather than one packaging verdict.
4. Compare the documents that arrived with the ones the pack requires, matching
   names without regard to letter case, and name each one missing.
5. Resolve the date code to the first day of its build week, refusing a week
   number the calendar year does not have instead of rolling it forward, and
   count the whole months to the receipt day.
6. Put a solderability re-test on a lot past its threshold, size the external
   examination draw from the accepted pieces by integer arithmetic, and accept
   into bonded store only when every check above held.

## Pitfalls

- Counting the delivery note instead of the bench. The note is the supplier's
  statement; the accepted quantity is what was counted less what arrived
  damaged.
- Rolling a week 53 date code into the next year. Some years have no week 53,
  and rolling it forward quietly makes an old lot look younger than it is.
- Taking the delivery date as the age. A part built two years before it shipped
  arrives old, and only the date code says so.
- Reporting one packaging verdict. A broken seal, an open bag and a changed
  humidity indicator are three different histories and the nonconformance needs
  the one that happened.
- Stopping at the first failing check. Goods-in raises everything it found in
  one pass, because the delivery is only unpacked once.

## Behavior contract (gate 3)

The date-code build-week resolution, arrival age, quantity reconciliation,
packaging and evidence-pack findings, examination draw and the bonded-store or
quarantine disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_1_incoming_inspection.py against
scripts/q60_class_1_incoming_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_1_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

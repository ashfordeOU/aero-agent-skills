---
name: q60-class-2-inspection-documentation
description: "Assess whether a class 2 parts programme recorded its inspection and control outcomes reconcilably under ECSS-Q-ST-60C clause 5.7: name every performed activity carrying no record, refuse a recording authority outside the accepted list, reject a record whose inspected count fails to reconcile with its accepted, rejected and deferred counts, require a nonconformance reference behind every rejected quantity, take coverage as the share of activities holding a defect-free record against a floor under a named tolerance, and raise a yield advisory rather than a defect. Use when a class 2 parts inspection file has to become a recording verdict. Trigger: ecss, q-st-60c-clause-5-7, class-2-inspection-outcome-record, inspected-quantity-reconciliation, class-2-recording-authority-check, class-2-outcome-coverage-floor, class-2-acceptance-yield-advisory."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q60-class-2-inspection-documentation, q-st-60c-clause-5-7, class-2-inspection-outcome-record, inspected-quantity-reconciliation, class-2-recording-authority-check, class-2-outcome-coverage-floor, class-2-acceptance-yield-advisory]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Inspection and Control Documentation (space-systems/ecss/q60-class-2-inspection-documentation)

Use when the task is clause 5.7 of ECSS-Q-ST-60C: recording the outcomes of the
inspection and control activities carried out across the class 2 parts
programme. This leaf grades the outcome record set the programme actually
produced against the activities it actually performed.

## Domain quick reference

- An outcome is a set of numbers, not a verdict word. A record that says a lot
  passed and never says how many parts were presented, taken, turned back or
  held records an opinion, and the audit cannot reconstruct the lot from it.
- The four counts have to close. Presented equals taken plus turned back plus
  held; a residual either way means parts left the inspection unaccounted for,
  and the record set cannot say where they went.
- Class 2 widens who may take the outcome down, and that is the whole point of
  checking who did. A delegated inspector, the component manufacturer and the
  procurement agent all hold recording authority here, and anyone outside that
  list records attendance rather than an outcome.
- A rejected quantity without a nonconformance reference is the defect the
  audit is looking for. The parts turned back are the only ones with a decision
  still owing, and a bare count leaves that decision nowhere.
- A held quantity is honest and still open. Deferred parts are real evidence of
  work in progress, and they leave the activity short of a closed outcome.
- Coverage counts activities carrying a defect-free record, never records
  filed. Three unreconciled records against one activity cover nothing, and one
  sound record among them covers it.
- A low acceptance yield is an advisory, never a defect. A programme that
  inspected honestly and turned parts back has recorded its outcome correctly,
  and burying that in the defect list hides the records that are actually wrong.

## Workflow

1. Put the performed activities into audit order and reject any name the
   programme does not recognise.
2. Group the submitted records under the activity each covers, keeping the
   records that name nothing recognisable visible rather than dropping them.
3. Name every performed activity carrying no record at all.
4. Test each record for a recognised activity, a traceable lot identity, an
   accepted recording authority, an evidence reference, four stated counts
   that reconcile, a nonconformance reference behind every rejected quantity
   and no deferred quantity left open. Report every defect a record carries.
5. Take outcome coverage as the share of performed activities covered by at
   least one defect-free record and judge it against the coverage floor under
   the stated tolerance.
6. Pool the counts into a programme acceptance yield and raise an advisory when
   it sits below the advisory floor.
7. Return one disposition: outcomes-recorded, outcomes-partially-recorded, or
   outcomes-not-reconstructable when a performed activity carries no record.

## Pitfalls

- Accepting a verdict word as an outcome. Taken and turned back are counts, and
  a record without them cannot be reconciled against the delivered quantity
  years later when the lot is questioned.
- Letting a residual pass because it is small. A handful of parts that left the
  inspection unaccounted for is exactly the population that reaches flight
  hardware without a decision attached.
- Reading the widened recording authority as no authority. Class 2 lets the
  supplier write the outcome up; it does not let anybody write it up.
- Filing a rejected count and moving on. The rejection is the entry that needs
  a nonconformance behind it, and without one the lot carries an unexplained
  loss.
- Treating deferred parts as a filing detail. Work in progress is honest
  evidence and still leaves the activity open at the review.
- Counting records rather than covered activities. A thick folder against one
  activity and nothing against the next reads as progress and closes neither.
- Promoting a low yield into a defect. The yield is an outcome of the parts, not
  a defect of the record, and mixing the two buries the records that are wrong.

## Behavior contract (gate 3)

The audit ordering, record-to-activity grouping, unrecorded-activity listing,
per-record defect tests, quantity reconciliation, recording-authority check,
coverage floor, pooled acceptance yield, advisories and the recording
disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_2_inspection_documentation.py against
scripts/q60_class_2_inspection_documentation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_inspection_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

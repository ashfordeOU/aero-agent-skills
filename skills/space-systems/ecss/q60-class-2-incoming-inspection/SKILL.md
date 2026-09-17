---
name: q60-class-2-incoming-inspection
description: "Assess whether a Class 2 EEE delivery enters the bonded store on arrival at the procuring entity under ECSS-Q-ST-60C clause 5.3.7: reconcile the pieces counted against the note and take transit damage out of the accepted quantity first, size the draw and its acceptance numbers from the lot that remains, group the defects found by severity so a cosmetic mark and a cracked body are not one tally, and read a breached static-protective bag as evidence about every piece it held. Use when a goods-in bench has to become a bonded-store, screening or quarantine disposition. Trigger: ecss, q-st-60c-clause-5-3-7, class-2-arrival-inspection, class-2-arrival-attribute-sampling-plan, class-2-defect-severity-tally, class-2-critical-defect-quarantine, class-2-bonded-store-entry-disposition."
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
  tags: [ecss, q-st-60c-eee-class-2-scope, q60-class-2-incoming-inspection, class-2-arrival-inspection, class-2-arrival-attribute-sampling-plan, class-2-defect-severity-tally, class-2-critical-defect-quarantine, class-2-bonded-store-entry-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts -- Arrival Inspection (space-systems/ecss/q60-class-2-incoming-inspection)

Use when the task is the clause 5.3.7 arrival check of ECSS-Q-ST-60C: a Class 2
delivery has reached the premises of the procuring entity and been unpacked on
the goods-in bench, and the question is whether it enters the bonded store, how
many pieces of it do, and what the draw that was examined actually licenses.

## Domain quick reference

- The arrival check is a sample, not an examination of every piece. That is the
  whole reason the acceptance numbers matter: the verdict is being extended
  from the pieces looked at to the pieces that were not.
- Lot size fixes both the draw and what the draw may carry. A bigger lot is
  drawn harder in absolute terms and tolerates more defects, and the acceptance
  numbers belong to the tier rather than to the pieces that happened to be
  examined. A lot smaller than its own draw is examined whole.
- Defects are grouped by severity before they are counted. A cosmetic mark and
  a cracked package body are not the same evidence, and one tally across both
  either quarantines good lots or accepts bad ones.
- A critical defect is not an acceptance-number question at all. One is enough:
  a draw that produced a critical defect says nothing reassuring about the
  pieces nobody drew, so the lot goes to quarantine rather than to arithmetic.
- Pieces are reconciled before anything else. Damage found on arrival comes out
  of the accepted quantity rather than being left in and dealt with later, and
  the plan is then sized on the lot that actually remains.
- Packaging is evidence about the contents. A breached static-protective bag
  exposed every piece it held, not only the ones drawn, so it carries critical
  weight; a broken shipping seal is a traceability finding about the transit.
- A delivery can earn more than one disposition. It takes the worst of them.

## Workflow

1. Reconcile the count: the pieces on the note, the pieces actually counted and
   the pieces damaged in transit, and carry the discrepancies as findings.
2. Stop if nothing undamaged remains. There is no draw to take and no plan to
   size, and the delivery is quarantined on the count alone.
3. Size the draw and the acceptance numbers from the accepted quantity, cutting
   the draw to the lot when the lot is the smaller of the two.
4. Group the defects found in the draw by severity, keeping each description so
   the tally can be shown rather than only totalled, and refuse a report that
   claims more defects than there were pieces in the draw.
5. Take the critical route first: a critical defect, or a breached bag, ends the
   question before any acceptance number is consulted.
6. Count majors and minors against their own numbers, and note majors that
   stayed within their number rather than discarding them.
7. Check the arrival paperwork, then settle the disposition as the worst one
   earned and report the pieces that entered the store.

## Pitfalls

- Counting every defect in one tally. Severity is what makes the acceptance
  numbers mean anything; flattening it makes the plan arbitrary.
- Counting a critical defect against an acceptance number. It is not a rate
  question, and letting one critical finding sit inside an allowance of three
  majors accepts a lot the draw just condemned.
- Sizing the plan on the declared quantity. Damage and a short count shrink the
  lot, and a plan sized on the note draws against pieces that are not there.
- Reading the packaging as being about the packaging. The bag is the reason the
  pieces inside are still good; a breach is a finding about all of them.
- Accepting a lot into the bonded store without its traceability record. The
  pieces may be perfect and still be unusable, because nothing connects them to
  the lot they were accepted as.
- Reporting only the final disposition. A delivery that was accepted with three
  majors inside the allowance and a short count is not the same delivery as one
  that arrived clean.

## Behavior contract (gate 3)

The quantity reconciliation, sampling plan tiers, severity tally, packaging and
documentation findings and the worst-earned disposition are exercised by the
gate 3 contract test:
scripts/test_q60_class_2_incoming_inspection.py against
scripts/q60_class_2_incoming_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q60_class_2_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

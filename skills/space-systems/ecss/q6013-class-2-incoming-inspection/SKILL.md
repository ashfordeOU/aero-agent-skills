---
name: q6013-class-2-incoming-inspection
description: "Use when a receipt has to become a store-or-quarantine decision. Evaluate an arriving delivery of intermediate assurance commercial EEE parts under ECSS-Q-ST-60-13C clause 5.3.7: set the inspection level from the supplier's delivery history, let an unfranchised source raise that level whatever the history says, size the sample for the level in integer arithmetic and clamp it to the quantity received, withdraw a declared defect allowance under a tightened level, reconcile part number, date code and quantity as three separate comparisons, check the documents that travel with the parts, and return the dock disposition with the level the next delivery earns. Trigger: ecss, q-st-60-13c-clause-5-3-7, class-two-incoming-inspection, skip-lot-inspection-level, unfranchised-source-tightening, level-scaled-incoming-sample, incoming-accept-number-allowance, next-delivery-inspection-level."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-2-incoming-inspection, class-two-incoming-inspection, skip-lot-inspection-level, unfranchised-source-tightening, level-scaled-incoming-sample, incoming-accept-number-allowance, next-delivery-inspection-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE -- Class 2 Incoming Inspection (space-systems/ecss/q6013-class-2-incoming-inspection)

Use when the task is the clause 5.3.7 receiving inspection of
ECSS-Q-ST-60-13C at the intermediate assurance class: a delivery of
commercial parts has arrived on site, the depth of the check is allowed
to follow the confidence the supplier has earned, and the question is
what depth this delivery gets and what happens to it afterwards.

## Domain quick reference

- The first output of an intermediate class receipt is not a verdict but
  a level. The same delivery from a supplier with twenty clean receipts
  behind it and from one whose last delivery was rejected is inspected
  at two different depths, and the depth is decided before a box is
  opened.
- Confidence is earned in a run, not on average. The count that matters
  is consecutive accepted deliveries since the last rejection, so one
  rejection returns the supplier to the start rather than moving a mean.
- A skip-lot level is a statement about traceability as much as about
  history. Where the chain back to the manufacturer is not evidenced the
  reduction stops at the level below, because the run of clean receipts
  says nothing about parts whose origin cannot be followed.
- Source type outranks history, and only upward. An unfranchised source
  carries substitution risk rather than workmanship risk, and no length
  of clean record speaks to a risk the record never sampled. History can
  never buy a reduction back out of that.
- The sample follows the level and the quantity that actually arrived,
  computed in integer arithmetic. Floating-point square roots round
  differently on different machines, and an auditable sample has to be
  the same number everywhere the receipt is re-run.
- A declared defect allowance is a normal-inspection instrument. Under a
  tightened level the reason the level was raised is exactly the reason
  the allowance is withdrawn, so tightened is accept-on-zero whatever
  was declared.
- A receipt sets the next receipt. The disposition carries a level
  forward: a quarantine tightens, a tolerated defect gives back a
  reduction, and a clean receipt holds where it is.

## Workflow

1. Read the delivery history into a level, then apply the source-type
   override upward and record both reasons rather than only the winner.
2. Size the sample for that level from the quantity received, in integer
   arithmetic, raised to the floor, held at the cap and clamped to the
   lot. A skip-lot level draws no visual sample at all.
3. Resolve the accept number: the declared allowance at every level
   except tightened, which returns to zero.
4. Reconcile the part number, the date code and the quantity separately,
   keeping shortfall and overage as distinct non-negative numbers.
5. List the required delivery documents absent or marked not received.
6. Quarantine on any finding and name them all at once; accept to store
   only when there are none. Report an overage and a skip-lot receipt as
   advisories, separate from the findings.
7. Return the level the next delivery from this supplier is received at.

## Pitfalls

- Letting a long clean record lighten an unfranchised receipt. The
  record was built on deliveries from a different route, and the risk
  the broker adds is one the record has never been exposed to.
- Counting accepted deliveries as a percentage of all deliveries. A
  supplier at nineteen of twenty looks strong and may have been rejected
  last week; the run since the last rejection is the number.
- Sizing the sample from the ordered quantity. The sample is drawn from
  what arrived, so a short delivery is inspected as the smaller lot it
  actually is.
- Honouring a declared allowance under a tightened level. It hands back
  exactly the tolerance the tightening was imposed to remove.
- Treating a skip-lot level as no inspection. Identity and the documents
  that travel with the parts are still checked; what is skipped is the
  visual sample, not the receipt.
- Quarantining on the first finding and stopping. The receiving report
  is the supplier's feedback loop, and a partial list produces a partial
  correction and the same delivery again.

## Behavior contract (gate 3)

The level determination, source-type override, level-scaled sample
sizing, accept-number resolution, order reconciliation, document check,
dock disposition and next-level output are exercised by the gate 3
contract test:
scripts/test_q6013_class_2_incoming_inspection.py against
scripts/q6013_class_2_incoming_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_incoming_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

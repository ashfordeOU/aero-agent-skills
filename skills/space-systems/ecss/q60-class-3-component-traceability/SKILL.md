---
name: q60-class-3-component-traceability
description: "Maintain an unbroken identity trail for class 3 EEE parts from goods receipt through storage and kitting into finished assemblies, under ECSS-Q-ST-60C clause 6.5.4: read the granularity each receipt record actually supports, hold it against the floor the application demands and report the gap in whole identity steps, guard the programme-assigned receipt batch so one identifier never covers two deliveries and no batch is split without a split record, walk each fitted part back to its receipt and take the weakest link, reconcile received against issued and remaining, and catch a record dated after the installation it supplied. Use when a class 3 lot has to be traced into an assembly. Trigger: ecss, q-st-60c-clause-6-5-4, class-3-eee-traceability, class-3-receipt-batch-identity, class-3-custody-chain-break, class-3-identity-granularity-shortfall, class-3-unrecorded-batch-split."
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
  tags: [ecss, q-st-60-eee-scope, q60-class-3-component-traceability, class-3-eee-traceability, class-3-receipt-batch-identity, class-3-custody-chain-break, class-3-identity-granularity-shortfall, class-3-unrecorded-batch-split]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Component Traceability (space-systems/ecss/q60-class-3-component-traceability)

Use when the task is the clause 6.5.4 step of ECSS-Q-ST-60C: a part bought at
the lowest assurance class has to stay identifiable from the moment it is
received, through the store and the kit, into the assembly it ends up in. The
question is never only whether a record exists. It is how finely that record
names the part, and whether the chain from the fitted part back to the
delivery survives every custody transition in between.

## Domain quick reference

- Identity has levels, and the level is what is assessed, not a yes or no.
  A record names a part number, then a date code, then the programme's own
  receipt batch, then a manufacturer lot, then an individual serial. Each
  level needs everything under it: a lot number on a delivery with no date
  code is not lot traceability, it is a part number and a hopeful field.
- A serial list only reaches the serialised level when it actually covers the
  delivered quantity. A short list is a partial marking exercise.
- At this class the programme's own receipt batch identifier is usually the
  finest identity that exists, because the supplier ships no lot identity.
  That makes the identifier itself the control: one identifier may cover one
  delivery of one part on one day, and nothing else.
- A batch that is broken up in the store has to leave a split record behind.
  Without one the sub-batch is a new name for an unknown population, and the
  chain through it can carry nothing finer than the date code.
- The demanded level comes from the application, not from the part. The same
  commercial transistor needs a part number in a development rig, a date code
  in ground support equipment, the receipt batch in flight hardware, and a lot
  identity where the function is critical.
- The achieved level is the weakest link on the chain, not the best record on
  it. A perfect goods-in entry behind a kitting step that lost the batch is a
  date-code trail.
- A chain that never reaches a receipt achieves nothing at all. An assembly
  that consumed parts from a receipt no issue ever sent it is the classic
  break, and it is a record error whichever way it is resolved.
- Quantities have to close. Issued plus scrapped can never exceed received,
  and a ledger that says otherwise is raised rather than reported as a
  negative remainder.
- Time runs one way. An issue or a receipt dated after the installation it
  supplied did not supply it, whatever the paperwork says.

## Workflow

1. Check every receipt record carries the fields a goods-in entry owes, and
   read the identity granularity it actually supports.
2. Read the granularity the application demands and hold the two together as a
   shortfall in whole identity steps.
3. Guard the receipt batch identifier: find any identifier covering more than
   one delivery, and any issue that re-batched parts without a split record.
4. For every fitted part, walk the chain back through the issue that supplied
   it to the receipt that brought it in, and record where it breaks.
5. Take the achieved granularity as the weakest link on that chain, dropping
   it to the date code where an unrecorded re-batch sits on the path.
6. Reconcile each receipt: received against issued, scrapped and remaining.
7. Name every assembly that consumed parts with no issue record behind them,
   and every record dated after the installation it supplied.
8. Report the per-chain verdicts, the ledgers, the traceable share as an exact
   pair and a fraction, and every finding.

## Pitfalls

- Treating the presence of a record as traceability. The assessment is of the
  level the record reaches, and a part number alone is a level.
- Claiming lot traceability from a lot field on a delivery that carries no
  date code and no batch. Identity levels are cumulative.
- Reusing a receipt batch identifier across two deliveries to tidy the store.
  One identifier then names two populations and the identity it existed to
  carry is gone, silently.
- Splitting a batch in the store without a split record and carrying on
  quoting the parent identifier downstream.
- Taking the best record on a chain as the achieved level. The chain delivers
  its weakest link, and the weakest link is usually the kitting step.
- Reading a broken chain as a low-quality trail. A chain that never reaches a
  receipt is not a coarse identity, it is no identity.
- Letting a ledger go negative. Issued plus scrapped exceeding received is a
  record error to be raised, not a stock level to be reported.
- Accepting a record dated after the installation it supplied because the
  quantities happen to match.

## Behavior contract (gate 3)

The receipt field checking, identity granularity reading, demanded-level
lookup and shortfall arithmetic, batch identifier conflict and unrecorded
split detection, custody chain walking, weakest-link granularity, quantity
reconciliation, unsourced consumption detection, date-order checking and
traceable share are exercised by the gate 3 contract test:
scripts/test_q60_class_3_component_traceability.py against
scripts/q60_class_3_component_traceability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_component_traceability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q6012-flight-model-die-lot-procurement
description: "Size the wafer lot a flight-model MMIC die order has to start under ECSS-Q-ST-60-12C clause 4.2: grade the chosen foundry's qualification at wafer start rather than at order date, hold the batch to one wafer lot on one mask set, run the flight die count back up through assembly attrition, the destructive and validation sample draws and every screening yield stage in reverse, then turn the die starts into whole wafers and test them against the largest lot that foundry will run. Refuses a yield outside its range, a free-text date and a delivery before wafer start. Use when flight standard microwave dies are being ordered. Trigger: ecss, q-st-60-12c-clause-4-2, flight-model-die-lot-procurement, mmic-wafer-lot-start-sizing, die-yield-cascade-backcalculation, foundry-qualification-at-wafer-start, destructive-sample-draw-allowance."
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
  tags: [ecss, q-st-60-12-die-mmic-scope, q6012-flight-model-die-lot-procurement, mmic-wafer-lot-start-sizing, die-yield-cascade-backcalculation, foundry-qualification-at-wafer-start, destructive-sample-draw-allowance, single-wafer-lot-traceability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Die-Form MMIC — Flight Model Die Lot Procurement (space-systems/ecss/q6012-flight-model-die-lot-procurement)

Use when the task is the clause 4.2 step of ECSS-Q-ST-60-12C: a foundry
has been chosen and a batch of flight standard microwave dies has to be
obtained from it. The question is not only which foundry but how many
dies have to be started, out of which wafer lot, on which day, so that
the flight build still has its dies once the samples are consumed and
the yields have taken their share.

## Domain quick reference

- A bare die arrives with no package to carry its history, so its
  history is carried by the lot identity instead. One wafer lot on one
  mask set is what makes a die traceable at all; a batch assembled from
  two lots has two histories and one part number over them.
- The foundry's qualification has to hold on the day the wafers start,
  not on the day the purchase order was signed. An order placed inside
  the validity window against a wafer start outside it buys dies from an
  unqualified process, and the paperwork will read as compliant.
- The flight die count is the last number in the chain, not the first.
  Assembly attrition in the receiving equipment, the dies destroyed by
  destructive analysis and the dies consumed by lot validation testing
  all come out of the delivered population, and every screening and
  process yield takes its share before that.
- Back-calculation runs the chain in reverse, dividing by each yield and
  rounding up to whole dies at each stage. Rounding up at every stage,
  rather than once at the end, is what keeps the answer safe: a stage
  cannot start a fraction of a die.
- Wafers are the unit the foundry actually starts. Die starts become
  whole wafers at the dies-per-wafer figure, and the rounding leaves
  spare dies that are worth reporting rather than hiding, because they
  are the margin the build has against a yield coming in low.
- A need larger than the foundry's biggest lot is a finding, not an
  arithmetic detail. Splitting silently across two lots is exactly the
  traceability break the single-lot rule exists to prevent.

## Workflow

1. Grade the foundry qualification against the wafer start date; report
   the margin in days and whether it lapses before delivery.
2. Reduce the wafer lot and mask set identifiers to their distinct
   values and report a batch that spans more than one of either.
3. Raise the flight die count by the assembly attrition the receiving
   equipment will suffer, rounding up to whole dies.
4. Add the destructive analysis sample and the lot validation sample;
   these dies are consumed, not shipped, so they are additive.
5. Walk the yield stages in reverse, dividing by each stage yield and
   rounding up, keeping a per-stage record of dies in, dies out and
   dies lost so the cascade can be audited rather than trusted.
6. Convert die starts to whole wafers and compare against the largest
   lot the foundry runs; report the spare dies the rounding produced.
7. Emit the ordered procurement steps with their gates, dropping the
   steps this case does not owe, and the findings blocking release.

## Pitfalls

- Grading the qualification at order date. The order date is the easy
  date to have on file and the wrong one to grade; the wafers are what
  the qualification covers, so the start date is the date that counts.
- Rounding to whole dies once at the end of the cascade. Each stage
  starts whole dies, so the rounding belongs at each stage; deferring it
  under-buys on a long chain and the shortfall appears at screening.
- Treating the destructive and validation samples as coming out of the
  spares. They are consumed dies and they are additive to the delivered
  need; counting on the wafer-rounding spares to cover them leaves the
  build short whenever the rounding happens to be tight.
- Splitting a need across two wafer lots without saying so. The batch
  then has two process histories, and the traceability that justified
  buying bare die in the first place is gone.
- Accepting a free-text date. A date that has to be guessed at is a date
  that can be guessed wrong in the direction that passes, so the parse
  refuses anything that is not an ISO calendar date.

## Behavior contract (gate 3)

The qualification grading at wafer start, lot and mask set identity
check, tolerant whole-die rounding, reverse yield cascade, wafer
conversion, lot capacity test, step emission and findings are exercised
by the gate 3 contract test:
scripts/test_q6012_flight_model_die_lot_procurement.py against
scripts/q6012_flight_model_die_lot_procurement_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6012_flight_model_die_lot_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

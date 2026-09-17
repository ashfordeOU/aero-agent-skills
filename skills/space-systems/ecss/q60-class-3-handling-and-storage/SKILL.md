---
name: q60-class-3-handling-and-storage
description: "Evaluate whether Class 3 EEE parts have been handled, packaged and stored well enough to be issued, under clause 6.4 of ECSS-Q-ST-60C: fix the open-exposure budget the moisture level entitles the part to, spend it across the exposure log at the rate each environment earns so sealed nitrogen costs nothing and an open bench costs twice a cleanroom, credit a recorded bake only at the temperature and duration that level needs and reset the spend rather than discount it, read the protective chain from the part outwards, and let one severe handling event outrank any accumulated score. Use when a stored lot has to become an issue decision. Trigger: ecss, q-st-60c-clause-6-4, q60-c3-moisture-floor-life-budget, q60-c3-environment-weighted-exposure-log, q60-c3-bake-budget-reset, q60-c3-protective-packaging-chain, q60-c3-handling-event-ledger."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c-clause-6-4, q60-class-3-handling-and-storage, q60-c3-moisture-floor-life-budget, q60-c3-environment-weighted-exposure-log, q60-c3-bake-budget-reset, q60-c3-protective-packaging-chain, q60-c3-handling-event-ledger]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Handling, Packaging and Storage (space-systems/ecss/q60-class-3-handling-and-storage)

Use when the task is clause 6.4 of ECSS-Q-ST-60C: Class 3 parts are in store and
about to be issued, and the question is whether what happened to them between
goods receipt and the kitting bench leaves them fit to build with. The leaf
spends a moisture budget across the exposure record, reads the protective
packaging as a chain, totals the handling ledger and returns one verdict.

## Domain quick reference

- Moisture damage is bought in advance and paid at reflow. A part that absorbed
  moisture on an open bench in March shows nothing until it is soldered, so the
  protection has to be accounted as a budget spent rather than inspected for.
- The budget belongs to the part and the spending rate belongs to the store.
  A moisture level fixes how many open hours the family is entitled to; where
  the part actually sat fixes what each of those hours costs.
- Sealed dry nitrogen is free and a bench is expensive. Charging every hour
  alike turns a lot that lived in a dry cabinet into a lot that lived on the
  bench, which is precisely the distinction the store was built to make.
- A bake resets the spend; it does not discount it. Driving the moisture out
  returns the part to the start of its budget, so a qualifying bake is worth the
  whole exposure and a short or cool one is worth none of it.
- A bake that missed its temperature or its duration is not a partial bake. It
  is a warm shelf, and crediting it is how an over-exposed lot reaches reflow
  with a record that says it was treated.
- Packaging is a chain, not a checklist. A conductive inner carrier, a moisture
  barrier where the level needs one and a cushioned outer only protect in that
  order; the same three layers recorded in the wrong order are a repack.
- Handling events accumulate until one of them does not. Ungrounded handling and
  an unprotected transfer add up toward a limit; a dropped container ends the
  assessment on its own, because the damage it causes is not statistical.
- The verdict has four outcomes, not two. Issue it, bake it first, repack and
  requalify it, or quarantine it — collapsing those to pass and fail either
  scraps recoverable parts or issues parts that owed an oven.

## Workflow

1. Validate the lot record and read the moisture level to a budget, treating a
   level that carries no budget as unconstrained rather than as zero.
2. Walk the exposure log and charge each interval at its environment's rate,
   keeping the arithmetic in integer tenths so the total is exactly reproducible.
3. Test any recorded bake against the temperature floor and the duration the
   level needs; reset the spend to zero when it qualifies and report it when not.
4. Compare the spend with the budget, treating a lot sitting exactly on its
   budget as still inside it.
5. Read the packaging chain: the layers the level owes, present, and innermost
   first.
6. Total the handling ledger and raise the severe flag on any event that ends
   the assessment by itself.
7. Return the verdict, letting a severe event outrank a broken chain, a broken
   chain outrank an over-spend, and an over-spend with no oven become a hold.

## Pitfalls

- Treating the store as uniform. A single "hours out of the bag" figure with no
  environment attached cannot distinguish a dry cabinet from a loading bay.
- Subtracting a bake from the exposure. Partial credit for a bake is how a lot
  that should have been re-baked from zero reaches the line with budget to spare.
- Reading a level 1 part as having a zero budget. It has no budget because it
  needs none, and scoring it as exhausted quarantines parts that were never at
  risk.
- Checking that the packaging layers are present and stopping. Order is what
  makes them work, and an inner cushion with an outer barrier protects nothing.
- Averaging handling events. A drop is not four ungrounded touches; it is the
  event that ends the assessment regardless of what else the ledger holds.
- Quarantining an over-exposed lot that could simply be baked. The oven is the
  intended remedy, and the hold is for the case where there is no oven to use.
- Recording the verdict without the remaining budget. The next team needs to
  know what is left, not only that the lot passed on the day it was looked at.

## Behavior contract (gate 3)

The moisture budget lookup, environment-weighted exposure accounting, bake
qualification and reset, budget comparison, packaging chain reading, handling
ledger totalling, severe-event precedence and the per-lot verdict are exercised
by the gate 3 contract test:
scripts/test_q60_class_3_handling_and_storage.py against
scripts/q60_class_3_handling_and_storage_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q60_class_3_handling_and_storage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

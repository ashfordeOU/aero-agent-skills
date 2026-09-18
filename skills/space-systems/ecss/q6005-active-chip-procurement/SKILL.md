---
name: q6005-active-chip-procurement
description: "Determine whether a purchase of bare semiconductor dice for assembly inside a hybrid package is ready to place under ECSS-Q-ST-60-05C clause 8.3. Use when the task is reading the procurement route a die was bought through, deriving the evidence set that route owes on top of the universal one, checking the traceability chain reaches the wafer lot, grading die-bank age against the limit its storage atmosphere defends, and sizing the order from the good dice needed, the destructive sample consumed and the assembly yield. Trigger: ecss, q-st-60-05c, bare-die-procurement, hybrid-active-chip-purchase, die-procurement-route, wafer-lot-traceability, die-bank-age-limit, die-order-quantity-sizing."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-active-chip-procurement, bare-die-procurement, hybrid-active-chip-purchase, die-procurement-route, wafer-lot-traceability, die-order-quantity-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Active Chip Procurement (space-systems/ecss/q6005-active-chip-procurement)

Use when the task is the bare die purchase of ECSS-Q-ST-60-05C clause
8.3 — deciding what a die bought for assembly inside a hybrid package
owes before the order is placed, and how many dice that order has to
carry.

## Domain quick reference

- A bare die has no package, and the package is where a part normally
  carries its identity. Everything knowable about a delivered die is
  therefore whatever the route it came through was able to establish,
  which makes the route the first thing read and the thing that sets the
  evidence set. A die pulled from a line already qualified for packaged
  parts inherits most of that work; a die from a line qualified for
  nothing has to produce all of it.
- Part of the evidence does not move with the route, because it is about
  the delivered dice rather than the line that made them: the record
  linking them back to a wafer lot, the visual inspection made while the
  die is still visible, the declaration of how they were handled against
  electrostatic discharge, and the record of the atmosphere they sat in.
- Traceability is graded by the depth it reaches, not by its presence. A
  chain that stops at the delivery lot cannot answer a question about
  the wafer, so a failure found two years later cannot be bounded to a
  population and every hybrid built from that purchase is suspect.
- A die bank has an age and the atmosphere it sat in sets how long that
  age is defensible. A sealed dry pack defends less than a nitrogen
  cabinet, and cleanroom ambient defends least; the same dice are
  acceptable or not depending on which one holds them.
- The quantity to order is not the quantity of good dice needed. The
  destructive sample is consumed before assembly starts and the assembly
  yield takes a further share, so both are bought up front. Going back
  for more dice later buys them from a different wafer lot, which
  restarts the evidence rather than topping up the order.

## Workflow

1. Validate each purchase record: identifier, die technology,
   procurement route, storage condition, traceability level, evidence on
   file, die bank age, wafer lots, good dice needed and assembly yield.
   An unknown technology, route, storage condition or traceability level
   is an input error.
2. Derive the evidence the route owes as the union of the universal set
   and the route's own additions, and compare it against what is on
   file; report each gap by the item it names.
3. Keep evidence that is on file but not owed as surplus rather than
   discarding it, so a reviewer can see what the buyer collected.
4. Check the traceability depth: anything shallower than the wafer lot
   is a finding in its own right, independent of the evidence count.
5. Grade the die bank age against the limit its storage atmosphere
   defends, treating an age exactly on the limit as acceptable.
6. Size the order: divide the good dice needed by the assembly yield,
   round up while absorbing the quotient representation error with a
   named epsilon so an exact division does not buy a spare die, and add
   the destructive sample the wafer lots consume.
7. Aggregate the package: ready and blocked purchases listed separately,
   with the total dice to place across the set.

## Pitfalls

- Treating the evidence set as fixed. It is a function of the route, and
  applying a qualified line's short set to a commercial purchase drops
  the construction analysis and the supplier audit that made the
  commercial route usable at all.
- Accepting traceability because a lot number exists. A delivery lot
  number is not a wafer lot number, and only the second one bounds a
  population when something is found later.
- Reading the die bank age against a single limit. The limit belongs to
  the atmosphere, so dice acceptable in a nitrogen cabinet are past
  their defensible age in cleanroom ambient at the same age.
- Ordering the good dice count. The destructive sample is consumed
  before assembly and the yield takes its share afterwards, so an order
  placed at the good count is short before the first lid is sealed.
- Topping up a short order from the next delivery. The additional dice
  come from another wafer lot, and the evidence that covered the first
  purchase does not extend to them.

## Behavior contract (gate 3)

The route evidence derivation, gap and surplus reporting, traceability
depth check, die-bank age grading, order quantity sizing and package
aggregation are exercised by the gate 3 contract test:
scripts/test_q6005_active_chip_procurement.py against
scripts/q6005_active_chip_procurement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_active_chip_procurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

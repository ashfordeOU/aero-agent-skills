---
name: e10-design-budgets
description: "Use when allocate technical budgets (mass, power, data rate, link, pointing, thermal, or any other quantifiable design resource) for a space system under ECSS-E-ST-10C clause 5.4.1.2 and Annex I: determine the minimum required margin for the project's current life-cycle phase, track each item's current best estimate against its allocation and the phase's required margin, verify that sub-item allocations sum within the parent system-level allocation, and check the system-level margin on the summed current best estimates. Trigger: ecss, e-st-10c, technical budget, margin philosophy, budget allocation, current best estimate, mass budget, power budget, margin management, maturity margin."
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
  tags: [ecss, e-st-10-system-scope, technical-budgets, margin-philosophy, budget-allocation, current-best-estimate, maturity-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — Technical Budgets and Margin Policy (space-systems/ecss/e10-design-budgets)

Use when the task is applying the technical budget and margin policy of
ECSS-E-ST-10C clause 5.4.1.2 and Annex I during design -- allocating a
quantifiable technical resource top-down from a system-level total to
its contributing items, tracking each item's current best estimate
(CBE) against its allocation, and protecting the budget with a margin
sized to the project's current design maturity.

## Domain quick reference

- A technical budget (mass, power, data rate, link, pointing, thermal,
  or any other quantifiable resource) is allocated top-down: a
  system-level total is divided among contributing items, and the sum
  of the item allocations must not exceed the system-level total from
  which they were derived. Exceeding it at allocation time is a
  finding independent of how much of the budget has actually been
  consumed.
- Each item's actual consumption is tracked as a current best estimate
  (CBE) -- the best available value at the current point in design,
  refined as the design matures. The current margin on an item is the
  unconsumed fraction of its allocation: (allocated - CBE) / allocated.
- Annex I's margin philosophy ties the minimum required margin to the
  project's life-cycle phase: more design uncertainty early (phase A)
  demands a bigger margin held in reserve; less uncertainty late
  (phase D) permits a smaller margin. The required percentage shrinks
  monotonically from phase A through phase D. A margin appropriate for
  a mature phase D design is not automatically appropriate earlier.
- The same current-margin-versus-required-margin check applies at two
  levels: per item (CBE against its own allocation) and at the system
  level (the sum of every item's CBE against the system-level total).
  A budget is not compliant until the allocation is internally
  consistent and both margin levels satisfy the phase's requirement.

## Workflow

1. Identify the project's current life-cycle phase (A, B, C, or D) and
   look up the minimum required margin percentage for that phase.
   Reject an unrecognized phase before it enters the assessment.
2. For each item in the budget, compare its current best estimate to
   its allocation: if the estimate already exceeds the allocation,
   flag it immediately regardless of margin. Otherwise compute the
   item's current margin and compare it against the phase's required
   margin; flag an item whose current margin falls short.
3. Check top-down allocation consistency: sum every item's allocation
   and compare it against the system-level allocation it was derived
   from; flag an exceedance even if no item has individually exceeded
   its own allocation yet.
4. Sum every item's current best estimate and repeat the margin check
   from step 2 at the system level against the system-level
   allocation and the same phase-derived required margin.
5. Aggregate the item-level, allocation-consistency, and system-level
   findings; the budget is not compliant until all three lists are
   empty.

## Pitfalls

- Applying a fixed margin percentage regardless of project phase --
  the required margin in Annex I's philosophy shrinks as the design
  matures, so a percentage adequate at phase D would be inadequate at
  phase A and unnecessarily conservative if applied uniformly.
- Checking only the current best estimate against the allocation and
  skipping the allocation-consistency step -- a set of item
  allocations can each look individually reasonable while their sum
  already exceeds the system-level total before any item has consumed
  its share.
- Treating the system-level margin as automatically satisfied because
  every item individually meets its own required margin -- the
  system-level check is against the summed current best estimates and
  the system-level allocation, a separate comparison from any single
  item's.
- Reading "no margin violation yet" as a permanent pass -- the current
  best estimate is expected to change as design matures, so the check
  is a point-in-time budget/margin status, not a one-time approval.

## Behavior contract (gate 3)

The required-margin-by-phase lookup, item-level consumption/margin
accounting, allocation-consistency check, and system-level margin
check are exercised by the gate 3 contract test:
scripts/test_e10_design_budgets.py against
scripts/e10_design_budgets_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_design_budgets.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

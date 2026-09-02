---
name: mass-budget
description: "Use when you must build the vehicle mass budget for the conceptual design: allocate the subsystem masses, apply the growth allowance and the contingency margin policy, roll up the total estimated mass, and check the margin-backed total against the MTOW target. Produces the mass breakdown, the total mass with margin, and the within-target or over-target verdict that gate the weight control plan. Trigger: mass budget, growth allowance, contingency margin, MTOW target, mass breakdown."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: mass-properties
  tags: [mass-budget, mass-allocation, growth-allowance, contingency-margin, margin-policy, mtow-target, mass-breakdown]
  version: 0.1.0
  author: Aero Agent Skills
---

# Mass Budget (vehicle-design/mass-properties/mass-budget)

Use when the task is building the vehicle mass budget at the
conceptual level: allocating subsystem masses, applying the growth
allowance and contingency margin policy, rolling up the estimated
total mass, and checking the margin-backed total against the MTOW
target.

## Domain quick reference

- The mass budget is the mass breakdown of the vehicle by subsystem
  (wing, fuselage, empennage, systems, payload, and so on); the rollup
  is the sum of the subsystem masses in kg.
- Growth allowance is the percentage added to an estimated mass to
  cover later design refinement; common practice tightens it as the
  design matures: about 10 percent in the conceptual phase, about 6
  percent in the preliminary phase, and about 3 percent in the
  detailed phase.
- Contingency margin is an extra percentage on top of the
  growth-allowance total to cover estimation uncertainty.
- Margin-backed total mass: estimated total multiplied by
  (1 + growth allowance) and then by (1 + contingency margin).
- The MTOW target check subtracts the margin-backed total from the
  target takeoff mass; a non-negative margin is within target, a
  negative margin is over target, and the margin percent is relative
  to the target.
- Mass budget practice sits in the FAR-25 / CS-25 weight and balance
  context (CG limits and operating weights rely on the budgeted mass).

## Workflow

1. Collect the subsystem mass estimates in kg, one entry per
   subsystem.
2. Roll up the budget with rollup_mass_budget.
3. Select the design phase and get its growth allowance with
   phase_growth_allowance.
4. Apply the growth allowance with apply_growth_allowance and the
   contingency margin with contingency_mass.
5. Check the margin-backed total against the MTOW target with
   mtow_check and read the verdict before gating the weight control
   plan.

## Pitfalls

- Applying the growth allowance and the contingency margin only to
  selected subsystems: both apply to the rolled-up total, not per
  item, unless the item has its own agreed margin.
- Confusing the two margins: growth allowance covers design
  refinement, contingency covers estimation uncertainty; they are
  separate percentages.
- Reporting the raw rollup as the budget total: the margin-backed
  total is what the weight control plan tracks.
- Reading margin percent with the wrong reference: margin percent is
  relative to the target mass, not to the estimated mass.
- Passing an empty subsystems dict or a negative fraction; the module
  raises ValueError instead of guessing.

## Behavior contract (gate 3)

The rollup, growth allowance, contingency margin, and MTOW target
check logic are exercised by the gate 3 contract test:
scripts/test_mass_budget.py against scripts/mass_budget_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_mass_budget.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; growth allowance
  and contingency margin values are common weight engineering
  heuristics, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

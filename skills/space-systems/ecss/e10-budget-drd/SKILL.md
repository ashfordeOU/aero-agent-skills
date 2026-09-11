---
name: e10-budget-drd
description: "Use when produce or review a project technical budget report against the ECSS-E-ST-10C Annex I Document Requirements Definition: place every budget item in a recognized category, inflate its basic value into a current best estimate using the margin its design maturity earns, check each estimate against its allocated maximum, roll the estimates up per category and system-wide, apply the system margin, and decide whether the report satisfies the DRD. Trigger: ecss, e-st-10-system-scope, technical-budget, annex-i-drd, mass-budget, power-budget, margin-philosophy, design-maturity, budget-allocation."
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
  tags: [ecss, e-st-10-system-scope, technical-budget, annex-i-drd, margin-philosophy, design-maturity, budget-allocation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Technical Budget DRD (space-systems/ecss/e10-budget-drd)

Use when the task is to generate or validate a project's technical
budget report against the Document Requirements Definition of
ECSS-E-ST-10C Annex I -- the categories a budget item may occupy, the
maturity-based margin philosophy that turns a basic value into a
current best estimate, and the reporting rules that decide whether the
report is compliant.

## Domain quick reference

- Every budget item belongs to one recognized category (mass, power,
  data rate, link margin, pointing, propellant, thermal). A category
  outside that set is an input error, not a new category -- the DRD
  fixes the reporting structure so that budgets stay comparable across
  reports and across projects.
- An item's current best estimate is its basic value inflated by the
  margin its *design maturity* earns: an off-the-shelf item carries a
  small margin, an item that exists only as an estimate carries a
  large one. The margin expresses how much the basic value may still
  move, so it is a property of maturity, not of the engineer's
  confidence or of the category.
- A DRD record is complete only when the item identifier, category,
  basic value, maturity and allocated value are all present. An
  incomplete item is reported as incomplete and kept out of the
  current-best-estimate total rather than silently assigned a default
  -- an unknown value must not dilute the rolled-up budget.
- An allocated value that has never been captured is itself a finding
  once the item has a nonzero current best estimate. There is no
  implicit infinite allocation.
- The system total carries its own margin on top of the per-item
  margins, and is checked against the system allocated budget. Item
  margins cover per-item growth; the system margin covers what the
  item list does not yet contain.
- Compliance is conjunctive: the report satisfies the DRD only when
  the completeness, per-item allocation and system-level finding lists
  are all empty. Headroom on one item never offsets an overrun on
  another.

## Workflow

1. Check each item against the required DRD fields; record an
   incompleteness finding for each missing field and exclude the item
   from the estimate total.
2. Validate each remaining item's category against the recognized set.
3. Derive each item's margin fraction from its design maturity and
   inflate its basic value into a current best estimate.
4. Compare each current best estimate against that item's allocated
   value; record a finding for an overrun and for an allocation that
   was never captured.
5. Sum the current best estimates per category and across the report,
   apply the system margin fraction to the total, and check it against
   the system allocated budget.
6. Declare the report DRD-compliant only when the completeness,
   allocation and system finding lists are all empty.

## Pitfalls

- Applying one flat margin across the whole budget. The DRD margin
  philosophy is maturity-driven, so two items of the same category and
  the same basic value legitimately carry different margins.
- Comparing the *basic* value against the allocated value. The
  allocation is met by the current best estimate, margin included --
  checking the uninflated value hides exactly the growth the margin
  exists to cover.
- Defaulting a missing basic value or maturity to zero or to the most
  favourable level so the total can be computed. The item is
  incomplete; report it and leave it out of the roll-up.
- Treating a missing allocated value as unlimited headroom. An item
  with a real estimate and no recorded allocation is an unfinished
  budget, and the DRD review must say so.
- Applying the system margin to the sum of already-inflated estimates
  and then also re-applying per-item margins -- the two margins stack
  once, in that order, and double counting inflates the reported total
  beyond what the philosophy intends.
- Declaring the report compliant on the system total alone while an
  individual item is over its allocation; per-item and system checks
  are independent and both must pass.

## Behavior contract (gate 3)

The category validation, maturity margin, current-best-estimate,
record-completeness, per-item allocation, category roll-up and
system-level budget logic is exercised by the gate 3 contract test:
scripts/test_e10_budget_drd.py against scripts/e10_budget_drd_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e10_budget_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: q7028-applicability-and-repair-types
description: "Determine whether a damaged printed-circuit-board assembly falls inside the board repair standard at all, which repair category the damage belongs to, and whether the board may still be repaired or has to go to nonconformance review. Use when triaging a damage report, grouping a proposed change, or deciding scrap against repair: it tests the assembly construction, maps the damage onto a repair category, separates a repair from a design-altering modification, and spends the per-category and per-board repair budgets against the history the board already carries. Trigger: ecss, q-st-70-28c-board-repair, pcb-repair-applicability, pcb-damage-category, pcb-modification-category, pcb-repair-budget, pcb-repairability-verdict."
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
  tags: [ecss, q-st-70-28c-board-repair, q-st-70-28c, q7028-applicability-and-repair-types, pcb-repair-applicability, pcb-damage-category, pcb-modification-category, pcb-repair-budget, pcb-repairability-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Applicability and Repair Types (space-systems/ecss/q7028-applicability-and-repair-types)

Use when the task is the framework clause of ECSS-Q-ST-70-28C: a damaged board
has arrived, somebody wants to fix it, and the first questions are whether this
standard governs the item, whether a repair category exists for that damage,
and whether the board has any repair budget left to spend.

## Domain quick reference

- Scope is decided by the construction, not by the shape of the box. Single-
  and double-sided boards, multilayers, flexibles and rigid-flex assemblies are
  the standard's subject; a hybrid microcircuit, a harness, a solar panel and a
  machined housing are somebody else's, and naming that owner is part of the
  triage rather than an afterthought.
- Damage is only actionable once it has a repair category. Track damage, land
  damage, plated-hole damage, base-material damage, coating damage and
  component replacement each own a family of methods; a damage token that maps
  to nothing is not a small repair, it is an undescribed one.
- Some damage has no repair at all. A carbon path burned through the laminate,
  a hole burned through the board, an open on a buried layer and delamination
  under a populated area are dispositioned in nonconformance review whatever
  the budgets say, because there is no method that restores the property that
  was lost.
- A repair restores the design; a modification changes it. Adding a jumper,
  cutting a track, adding or removing a part and changing a component value
  leave the board different from its drawing, so the drawing set and the
  as-built record move with the hardware and a repair record alone is not
  enough.
- Repair budgets are cumulative over the life of the board, not per event. The
  per-category limit stops one weak feature being rebuilt again and again; the
  per-board limit stops a board that has been rebuilt everywhere from being
  counted as flight hardware on the strength of each individual repair looking
  small.
- Damaged extent is bounded as a fraction of the feature, not in millimetres.
  A fraction lets a wide land and a fine-pitch land be graded by the same rule,
  and a value exactly on the bound is inside it because the number came off a
  measurement.
- An unknown assembly type or an unknown damage token is refused, never
  defaulted. Defaulting is how out-of-scope hardware and undescribed damage get
  a repair category they were never entitled to.

## Workflow

1. Resolve the assembly construction against the in-scope list, and where it is
   not there, report which discipline actually owns the item.
2. Map the reported damage onto a repair category, flagging damage that the
   standard offers no repair for.
3. Grade the damaged extent as a fraction of the feature against the allowed
   maximum, treating a value on the bound as acceptable.
4. Read the board's repair history and spend the per-category and per-board
   budgets, reporting either as exhausted when it is at its limit.
5. Where a change rather than a defect is proposed, group it as a wiring,
   component or finish modification and say whether the drawing and as-built
   records must follow.
6. Return the disposition — repair, nonconformance review or out of scope —
   with every finding that produced it.

## Pitfalls

- Triaging the damage before the scope. A hybrid or a harness gets a board
  repair category, an operator qualified against the wrong standard picks it
  up, and the error is only visible at delivery review.
- Treating an unmapped damage token as a minor repair. Nothing in the method
  catalogue matches it, so the repair that eventually happens is invented at
  the bench and recorded as if it were a listed method.
- Reading the repair budget per event. Four repairs that each looked like the
  first one put the board past a limit nobody ever evaluated, because the
  history was never brought into the decision.
- Recording a modification as a repair. The hardware no longer matches its
  drawing, the as-built set still says it does, and the discrepancy surfaces
  when the next board is compared against this one.
- Grading damaged extent in absolute size. The same two millimetres is trivial
  on a power land and the whole feature on a fine-pitch one, so an absolute
  rule passes damage it should have refused.
- Defaulting an unknown token to the closest known one. The triage then reports
  a category with full confidence for damage nobody has actually described.

## Behavior contract (gate 3)

Scope resolution, damage-to-category mapping, irreparable damage, modification
grouping with its drawing obligation, the per-category and per-board repair
budgets and the damaged-area fraction bound are exercised by the gate 3
contract test:
scripts/test_q7028_applicability_and_repair_types.py against
scripts/q7028_applicability_and_repair_types_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7028_applicability_and_repair_types.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

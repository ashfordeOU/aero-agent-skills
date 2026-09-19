---
name: q7054-ultracleaning-plan
description: "Plan the ultracleaning of a hardware set to ECSS-Q-ST-70-54C: assign one qualified process per item, the gentlest that reaches the level it owes and that its material tolerates, place each process against the assembly and integration sequence, insert a verification point wherever a level is claimed, and return the plan with its coverage findings — an item no process reaches, a claim with nothing measuring it, and a cleaning step a later contaminating operation undoes. Use when writing or reviewing an ultracleaning plan for a build. Trigger: ecss, q-st-70-54c, ultracleaning-plan, ultracleaning-process-assignment, ultracleaning-verification-point, ultracleaning-coverage-gap, cleaning-sequence-placement."
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
  tags: [ecss, q-st-70-54c-ultracleaning-of-flight-hardware, q-st-70-54c, q7054-ultracleaning-plan, ultracleaning-process-assignment, ultracleaning-verification-point, ultracleaning-coverage-gap, cleaning-sequence-placement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Ultracleaning — Ultracleaning Plan (space-systems/ecss/q7054-ultracleaning-plan)

Use when the task is the programme clause of ECSS-Q-ST-70-54C: turning a set of
items that owe an ultraclean state into a plan that says which process each one
gets, where in the build it happens, and what measurement stands behind every
level that is claimed.

## Domain quick reference

- A plan answers three questions at once — which process, when in the build,
  and verified how. Any one of them left open makes the other two worthless: a
  perfect process at the wrong point in the sequence, or a level nobody
  measures, both deliver hardware whose state is unknown at delivery.
- Process assignment is a floor, not a maximum. The gentlest process that
  reaches the level the item owes is the right one, because every step up in
  aggressiveness spends surface life, coating integrity or dimensional margin
  to buy cleanliness the requirement never asked for.
- Material tolerance sits ahead of capability. A process that would reach the
  level but attacks the substrate is not a candidate at all, so the compatible
  set is taken first and the capability comparison runs inside it.
- A process capability is a pair, not a number. A route can be excellent on
  residue and mediocre on particles, so an item is matched on both ladders
  together and a route that clears only one of them does not qualify.
- Timing is part of the plan. Cleanliness is not a property the hardware keeps
  regardless of what happens next, so a cleaning step followed by a
  contaminating operation is a planning defect even when the cleaning itself
  was faultless.
- A claim owes a measurement. Any level tighter than what the routine cleaning
  route already holds is a claim, and a claim with no verification point behind
  it is an assumption with a number attached.
- The plan closes with a verification at delivery, not with the last cleaning
  step. The closing measurement is what the receiving party reads, and it is
  the only point that covers contamination picked up between the last process
  and handover.

## Workflow

1. Validate every item: identity, material, the two required levels and its
   place in the build sequence. Reject a duplicate identity rather than
   silently planning one item twice.
2. For each item take the processes its material tolerates, then keep those
   whose achievable level and achievable residue both meet the requirement,
   treating an exact landing on the requirement as met.
3. Assign the gentlest survivor, breaking a tie on name so the plan is
   reproducible. Where nothing survives, record the item with no process and
   say whether compatibility or capability was the blocker.
4. Derive the verification points from the claims, not from the process: a
   particulate claim beyond the baseline owes a particle count or obscuration
   measurement, a residue claim owes a solvent rinse and weighing.
5. Order the entries by build sequence and check each cleaned item against the
   contaminating operations that follow it; a later contaminating operation is
   a finding against that item, not against the process.
6. Append the closing pre-delivery verification after the last entry of any
   kind, carrying the tightest level in the set.
7. Report the plan with its coverage: items planned, items with a process,
   verification points, findings, and whether the plan closes with none open.

## Pitfalls

- Assigning the most capable process everywhere. Over-cleaning is not free; it
  costs coating life and handling exposure, and a plan that reaches for the
  hardest route by default has stopped reading the requirement.
- Matching a process on one ladder. A route chosen for its residue performance
  can leave the particulate claim unmet, and the plan then reads as complete
  while half the requirement has no process behind it.
- Checking material compatibility after capability. Filtering by capability
  first produces a shortlist that has to be thrown away, and worse, invites the
  argument that an incompatible route is acceptable because it was the only one
  that reached the level.
- Cleaning to the final level before a dirty operation. The sequence decides
  what survives, so a claim made at an early step and never re-verified is a
  claim about hardware that no longer exists in that state.
- Treating the last cleaning step as the closing verification. Everything
  between that step and handover — bagging, transport, storage — is uncovered
  unless a delivery verification sits at the end.
- Planning an item that claims nothing beyond the routine route. It does not
  belong in the ultracleaning plan, and carrying it there dilutes the
  facility time the items that do need it are competing for.

## Behavior contract (gate 3)

The item and operation validation, compatible-set filtering, dual-ladder
capability match, gentlest-process assignment, verification point derivation,
sequence ordering, contaminating-operation findings and the coverage summary
are exercised by the gate 3 contract test:
scripts/test_q7054_ultracleaning_plan.py against
scripts/q7054_ultracleaning_plan_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7054_ultracleaning_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

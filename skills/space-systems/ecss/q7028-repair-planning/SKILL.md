---
name: q7028-repair-planning
description: "Plan an authorized printed-circuit-board repair before the operator starts. Use when the method, the consumables and the risk still have to be settled on paper: it selects the least invasive catalogued method whose damage-extent limit covers the damage, refuses a requested method the damage has outgrown, checks each consumable for shelf life at the planned date and for a process temperature the board construction tolerates, counts the thermal excursions the location has already taken, scores risk from criticality, accessibility and thermal exposure, and calls for a trial coupon where that score lands high. Trigger: ecss, q-st-70-28c-board-repair, pcb-repair-method-selection, pcb-repair-consumable-shelf-life, pcb-repair-process-temperature, pcb-rework-cycle-budget, pcb-repair-risk-band."
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
  tags: [ecss, q-st-70-28c-board-repair, q-st-70-28c, q7028-repair-planning, pcb-repair-method-selection, pcb-repair-consumable-shelf-life, pcb-repair-process-temperature, pcb-rework-cycle-budget, pcb-repair-risk-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Board Repair — Repair Planning (space-systems/ecss/q7028-repair-planning)

Use when the task is the planning clause of ECSS-Q-ST-70-28C: the repair has
been authorized, and the method, the materials and the risk have to be fixed
on paper so the bench executes a plan rather than inventing one with an iron
already hot.

## Domain quick reference

- Each damage category owns a small catalogue, and each method in it covers
  damage only up to a stated fraction of the feature. Selection is therefore a
  bounded search, not a preference: the least invasive method whose limit still
  covers the damage is the one the plan names.
- A requested method is checked against the damage rather than accepted. An
  operator who has always re-bonded a lifted land will request that again on a
  land that has lost most of its area, and the limit is what catches it.
- Damage beyond every catalogued limit produces no method at all. That is a
  real output and belongs in the plan as an empty selection with a finding, not
  as the largest method silently stretched to fit.
- Shelf life is graded at the planned repair date, not at the planning date. A
  material that is in date today and expires before the board reaches the bench
  is already a finding, and only a dated comparison exposes it.
- The process temperature ceiling belongs to the board, not to the material.
  The same adhesive is comfortable on a double-sided board and past the limit
  on a flexible one, so the pair — material and construction — is what is
  graded.
- Thermal excursions accumulate at the location. A land or a barrel survives a
  small number of them whatever the reason, so the prior cycles at that spot
  are added to the ones this plan will spend before the budget is read.
- Risk is a product of drivers, not a label. Criticality of the function, how
  reachable the spot is and how much heat it will see multiply, and it is the
  product that decides whether a coupon is repaired first.

## Workflow

1. Take the damage category and extent, and select the least invasive
   catalogued method whose limit still covers it; honour a requested method
   only when it also covers the damage.
2. Report an empty selection, with its finding, where no method covers the
   damage.
3. Grade each consumable at the planned date for shelf life, and against the
   board construction's ceiling for process temperature.
4. Add the thermal excursions this plan will spend to those the location has
   already taken and read the result against the budget.
5. Multiply the criticality, accessibility and thermal-exposure factors, place
   the score in its band, and require a trial coupon where the band says so.
6. Return the plan — method, candidates, board, date, score, band, coupon —
   with every finding, ready only when there are none.

## Pitfalls

- Selecting the method the operator is best at rather than the one the damage
  admits. The repair is done well by a method that was never applicable, and
  the workmanship of the joint hides that.
- Stretching the largest catalogued method over damage past its limit. The
  plan reads as complete, and the one signal that the board should have gone to
  nonconformance review has been written out of it.
- Grading shelf life on the day the plan is written. The board queues for three
  weeks, the adhesive expires in between, and nothing in the plan flags it.
- Carrying one process-temperature limit for the whole shop. The flexible and
  rigid-flex boards take less heat than the rigid ones, and a single number
  either blocks safe work or permits damaging work.
- Counting rework cycles per repair instead of per location. Three separate
  repairs each spent one excursion on the same land, and the land was spent
  before the last of them started.
- Reading a single risk driver. An accessible spot looks safe until the
  criticality of the function it carries is brought in, and the trial coupon
  that would have caught the method's surprise is never built.

## Behavior contract (gate 3)

Method selection against per-method extent limits, refusal of a requested
method past its limit, the empty selection, dated shelf-life grading, the
per-construction process-temperature ceiling, the per-location rework budget
and the multiplicative risk score with its bands and coupon rule are exercised
by the gate 3 contract test:
scripts/test_q7028_repair_planning.py against
scripts/q7028_repair_planning_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7028_repair_planning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

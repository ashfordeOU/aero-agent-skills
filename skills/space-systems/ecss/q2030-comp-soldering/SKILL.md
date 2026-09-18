---
name: q2030-comp-soldering
description: "Assess a soldered harness termination against the complementary requirements of ECSS-Q-ST-20-30C section 7.3, which sit on top of the IPC soldered-termination and crimp acceptance criteria. Use when the task is grading the additions a solder joint owes: alloy lead content and the whisker mitigation plan a near pure tin alloy needs, flux activation and the cleaning it obliges, iron tip temperature inside its window, a dwell and reheat budget scaled to conductor cross-section, the insulation clearance window at the termination, wetting angle acceptance, owed inspection magnification and operator certification currency. Trigger: ecss, q-st-20-30c, complementary-soldering-delta, solder-alloy-tin-whisker, solder-thermal-exposure-budget, solder-insulation-clearance-window, solder-wetting-angle, operator-certification-currency."
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
  tags: [ecss, q-st-20-30-harness-scope, q2030-comp-soldering, complementary-soldering-delta, solder-alloy-tin-whisker, solder-thermal-exposure-budget, solder-insulation-clearance-window, solder-wetting-angle]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary Soldering (space-systems/ecss/q2030-comp-soldering)

Use when the task is the complementary soldering provision of
ECSS-Q-ST-20-30C section 7.3 — the requirements the standard adds on
top of the soldered-termination and crimp acceptance criteria of its
external basis, covering what the joint is made of, how it was heated,
where the insulation ends, and who inspected it with what.

## Domain quick reference

- The alloy is a reliability input, not a shop preference. A solder
  with too little lead behaves as near pure tin and grows whiskers in
  vacuum over years, which is a short-circuit mechanism no visual
  acceptance criterion catches. It is admissible only behind a declared
  mitigation plan, and the plan is the evidence, not the intention.
- Flux is graded by what it leaves behind. A non-activated or mildly
  activated residue is admissible as it sits; an activated or
  water-soluble residue is corrosive or conductive and obliges a
  cleaning step, so an uncleaned joint made with one is a finding
  however good the fillet looks.
- Heat is a budget, and reheats spend from it. The dwell a joint can
  take scales with conductor cross-section because a heavier conductor
  needs longer to reach temperature; every heat application spends
  another dwell, so the exposure that matters is dwell times the number
  of applications. The tip temperature has a window at both ends: too
  cold gives a joint that never wetted, too hot damages the insulation
  and anneals the conductor.
- The insulation end sits in a window, not at a target. Too close and
  the insulation is heat-damaged and the joint cannot be seen; too far
  and bare conductor is exposed to handling and to its neighbours.
- Wetting angle is the measurement that says whether solder joined the
  conductor. A joint can be full, bright and well-shaped and still show
  an angle that says the solder sat on the surface rather than wetting
  it.
- Inspection magnification is owed by the conductor, not chosen by the
  inspector, and an operator certification that has lapsed makes the
  workmanship record incomplete whatever the joint looks like.

## Workflow

1. Validate the termination record: identifier, alloy composition, flux
   type and cleaning, conductor cross-section, insulation diameter and
   clearance, tip temperature, dwell, reheats, wetting angle,
   inspection magnification and certification age. A composition that
   sums above a hundred percent, a non-positive cross-section or
   diameter, or a fractional reheat count is an input error, not a case
   to normalize away.
2. Grade the alloy: below the lead floor the joint needs a declared
   whisker mitigation plan.
3. Grade the flux: an activated or water-soluble flux with no cleaning
   step recorded is a finding.
4. Compute the allowable dwell and the thermal budget from the
   cross-section, compare the spent exposure against the budget, and
   check the tip temperature against both ends of its window and the
   heat applications against their allowance.
5. Compute the insulation clearance window from the insulation diameter
   and place the as-built clearance inside it.
6. Grade the wetting angle against its acceptance value.
7. Derive the owed inspection magnification from the cross-section,
   check the certification currency, then aggregate the lot with a
   count per finding type, absorbing representation error at each limit
   with a named tolerance rather than by widening it.

## Pitfalls

- Accepting a near pure tin alloy because the joint passes the visual
  criteria. Whiskers grow after acceptance, which is exactly why the
  mitigation plan is the requirement rather than the inspection.
- Reading flux type alone. The finding is the residue, so the flux type
  and the cleaning record have to be read together.
- Budgeting heat per application instead of per joint. Two touch-ups
  each inside the dwell limit can still take the termination past the
  exposure the conductor and insulation can survive.
- Treating the insulation clearance as a minimum only. The window has
  an upper edge, and exposed conductor beyond it is its own defect.
- Letting the inspector pick the magnification. A fine conductor needs
  more than a coarse one, and a joint examined below the owed
  magnification has not been examined to the criteria it was graded
  against.

## Behavior contract (gate 3)

The termination validation, alloy and flux grading, scaled dwell and
thermal-exposure budget, tip-temperature window and heat-application
allowance, insulation clearance window, wetting-angle acceptance, owed
inspection magnification, certification currency and lot aggregation
are exercised by the gate 3 contract test:
scripts/test_q2030_comp_soldering.py against
scripts/q2030_comp_soldering_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_soldering.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

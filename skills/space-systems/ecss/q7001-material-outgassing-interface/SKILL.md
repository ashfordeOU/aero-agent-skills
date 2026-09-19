---
name: q7001-material-outgassing-interface
description: "Evaluate a material against the vacuum outgassing screening of ECSS-Q-ST-70-01C when it sits in view of a contamination sensitive surface, reading the figures the ECSS-Q-ST-70-02C micro-balance method produces: take the recovered mass loss over the total wherever a water vapour regain was measured, tighten the condensable limit for the grade of surface in view, estimate the deposit from exposed mass, view factor and the source to collector temperature difference, compare it with the surface deposition budget, then settle on acceptance, vacuum bakeout and retest, shielding or relocation, or refusal. Use when a materials list is screened for a contamination sensitive assembly. Trigger: ecss, q-st-70-01c, q-st-70-02c, outgassing-screening, collected-volatile-condensable-material, recovered-mass-loss, sensitive-surface-deposition-budget, vacuum-bakeout-and-retest."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-material-outgassing-interface, material-outgassing-screening, collected-volatile-condensable-material, recovered-mass-loss-regain, sensitive-surface-deposition-budget, vacuum-bakeout-and-retest]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness -- Material Outgassing At A Sensitive Interface (space-systems/ecss/q7001-material-outgassing-interface)

Use when the task is the outgassing screening ECSS-Q-ST-70-01C imposes on a
material used near a contamination sensitive surface: a part, material and
process list is being screened, the micro-balance figures of
ECSS-Q-ST-70-02C are in hand, and the question is whether this material may
sit where it sits.

## Domain quick reference

- The micro-balance method returns three numbers, not one. Total mass loss
  is everything the specimen gave up; recovered mass loss is what it gave up
  and did not take back as water vapour; the collected volatile condensable
  fraction is the part that settled on a cooled collector. Only the last of
  the three is what a sensitive surface actually receives, and only the
  second is a fair account of what left the material for good.
- Screening the total mass loss when a regain was measured fails materials
  that are merely damp. A polyimide film at 1.4 percent total with 0.9
  percent regain has lost 0.5 percent permanently, and rejecting it on the
  total is rejecting the storage humidity, not the material.
- The condensable limit is not one number for the whole vehicle. The same
  material sits comfortably beside a structure panel and is refused beside a
  cryogenic detector, because the grade of the surface in view decides how
  much condensate the surface can absorb before it stops doing its job.
- A limit check is not a deposition estimate. What arrives on the surface
  scales with the mass actually exposed, the view factor between the two,
  and the temperature difference driving the transport; a condensable
  fraction inside its limit can still swamp a small cold surface fed by a
  large warm source.
- Transport has a direction. A collector warmer than its source retains
  nothing, so a material that fails every screening limit is a housekeeping
  note rather than a defect once it is out of line of sight of the surface
  or sits colder than it.
- The disposition is not binary. A mass-loss exceedance is a bakeout and
  retest question; a condensable exceedance in view of the surface is not
  recoverable by baking; a budget exceedance with both limits met is an
  exposed-area or a layout question.

## Workflow

1. Validate the micro-balance record: percentages in range, the condensable
   fraction no larger than the total, and the regain consistent with the
   pair when all three are reported.
2. Take the recovered figure as the governing mass loss whenever a regain
   was measured, and the total otherwise.
3. Resolve the surface grade in view, refusing a grade outside the
   recognised set rather than falling back to a structure-grade limit.
4. Grade the material against the mass-loss limit and the grade-tightened
   condensable limit, absorbing an exact-equality case with a named
   tolerance instead of relaxing the limit.
5. Estimate the areal deposit from exposed mass, condensable fraction, view
   factor, the source to collector temperature difference and the surface
   area, and compare it with the surface budget.
6. Return the disposition: accepted, vacuum bakeout and retest, relocate or
   reduce the exposed area, refused in view of the surface, or accepted
   behind a shield.

## Pitfalls

- Screening on total mass loss alone. Where a regain was measured the
  recovered figure is the one the limit belongs to, and using the total
  rejects damp materials while telling you nothing about the condensate.
- Applying one condensable limit across the vehicle. The grade of the
  surface in view is what sets it, and a detector-grade interface will not
  survive a structure-grade screening.
- Stopping at the limit table. Two materials with identical figures deposit
  different amounts once exposed mass, view factor and temperature enter,
  and it is the deposit the surface has a budget for.
- Assuming any hot neighbour contaminates. A collector at or above its
  source temperature retains nothing, and treating geometry as the only
  driver produces findings nobody can close.
- Prescribing a bakeout for a condensable exceedance. Baking removes the
  volatile fraction the total counts; the condensable fraction in view of
  the surface is a material-selection or a shielding decision.

## Behavior contract (gate 3)

The micro-balance record validation, the recovered-over-total rule, the
grade-tightened condensable limit, the condensation direction and span, the
areal deposit estimate against the surface budget and the disposition ladder
are exercised by the gate 3 contract test:
scripts/test_q7001_material_outgassing_interface.py against
scripts/q7001_material_outgassing_interface_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7001_material_outgassing_interface.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

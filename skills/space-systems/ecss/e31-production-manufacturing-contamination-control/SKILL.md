---
name: e31-production-manufacturing-contamination-control
description: "Audit the production, manufacturing and contamination controls a thermal control item owes under ECSS-E-ST-31C clause 4.6. Use when a radiator, MLI outer layer or optical surface moves through procurement, manufacture, cleanliness, integration, marking, the declared heat-treatment operation, storage and repair: turn the molecular and particulate allocation into end-of-life absorptance and emittance, size the radiator area growth that follows, roll the per-stage allocations up against the budget, and raise marking inside an active area, an expired shelf life or a repair closed without re-verification. Trigger: ecss, e-st-31-thermal-control, e31-production-manufacturing-contamination-control, radiator-end-of-life-absorptance-growth, mli-outer-layer-contamination-allocation, optical-surface-obscuration-budget, thermal-hardware-storage-shelf-life, thermal-surface-marking-placement."
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
  tags: [ecss, e-st-31-thermal-control, e31-production-manufacturing-contamination-control, radiator-end-of-life-absorptance-growth, mli-outer-layer-contamination-allocation, optical-surface-obscuration-budget, thermal-hardware-storage-shelf-life, thermal-surface-marking-placement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Production and Contamination Control (space-systems/ecss/e31-production-manufacturing-contamination-control)

Use when the task is the production step of ECSS-E-ST-31C clause 4.6 --
the controls a thermal control item has to pass through between purchase
order and flight: procurement, manufacture, cleanliness, integration,
marking, the declared heat-treatment operation (PHT), storage and repair.

## Domain quick reference

- Contamination is a thermal requirement, not a housekeeping one. A
  molecular film raises the solar absorptance of a radiator and depresses
  its infrared emittance at the same time, and both changes push in the
  direction of a hotter spacecraft.
- Particulate contamination acts through obscuration, which is an area
  fraction. It scales absorptance far more strongly per unit than molecular
  deposit does, which is why the two carry separate coefficients rather
  than one lumped degradation figure.
- The number a thermal engineer acts on is not the absorptance, it is the
  radiator area. Convert both the beginning-of-life and the end-of-life
  optical pair into the area needed to reject the same heat, and report the
  growth ratio; a 0.04 rise in absorptance means nothing until it is square
  metres.
- Net rejection per unit area is the radiated term minus the absorbed solar
  term. When the absorbed term catches the radiated one there is no finite
  area that works, and that has to be refused rather than returned as a
  very large number.
- The allocation is per stage -- manufacture, integration, storage,
  transport, launch, on-orbit -- and it is the stage attribution that drives
  the corrective action. A total that fits the budget with nothing left for
  on-orbit is a plan that fails in year one.
- Marking is a contamination source placed by hand. Two questions decide
  it: is it inside the optically active area, and is the marking medium
  outgassing-qualified. A compliant marking scheme can still fail on where
  it was put.
- Storage and repair are where controlled hardware quietly leaves control.
  Shelf life is a date, the purge is a condition, and a repair is only
  closed when the thermo-optical properties have been re-verified, not when
  the operator signed.
- Areas and optical properties are quotients and sums of floats. A value
  landing exactly on its limit is absorbed by a named tolerance far below
  any reflectometer's resolution.

## Workflow

1. List the thermal surfaces. For each, record type, beginning-of-life
   absorptance and emittance, the molecular deposit and obscuration
   allocated to it, the three degradation coefficients, and the heat load,
   temperatures, solar flux and view factor it is sized against.
2. Compute the end-of-life absorptance and emittance; refuse an allocation
   that drives emittance to zero rather than clamping it.
3. Size the beginning-of-life and end-of-life radiator areas and take the
   growth ratio against the declared limit.
4. Roll the per-stage allocations up, report the dominant stage and the
   unallocated remainder, and flag an overspend.
5. Grade every production stage against the controls it owes, and report a
   stage with no declaration at all separately from a stage missing one
   control.
6. Apply the three hand-operation checks: marking placement and medium,
   storage duration against shelf life with the purge condition, and repair
   procedure with post-repair re-verification.
7. Roll the set up: controlled fraction, and the surface with the largest
   area growth as the driving item.

## Pitfalls

- Reporting contamination as a mass per unit area and stopping. The
  programme decision is the radiator area it costs, not the milligrams.
- Lumping molecular and particulate contamination into one degradation
  figure. They scale differently, and the corrective actions -- bakeout
  versus cleanroom discipline -- are different actions.
- Raising absorptance and leaving emittance alone. The same film does both,
  and ignoring the emittance loss understates the area growth.
- Clamping an emittance that the allocation drove to zero. That returns a
  finite area for a surface that no longer radiates; the allocation is the
  thing that is wrong.
- Allocating the whole budget to ground stages because they are the ones
  being measured, leaving on-orbit degradation nothing.
- Treating marking as an identification question. Where the mark sits and
  what it is made of are both contamination questions on a thermal surface.
- Closing a repair on the operator's signature. Until the thermo-optical
  properties are re-verified the surface has unknown properties.
- Using a strict comparison at the growth limit or the allocation budget.
  Both are float arithmetic, and a value on the boundary must read the same
  on every platform.

## Behavior contract (gate 3)

The absorptance and emittance degradation with their separate coefficients
and the refusal of a zero-emittance allocation, the net-rejection and
radiator-area sizing including the no-finite-area refusal, the growth
ratio against its limit, the per-stage allocation roll-up with its dominant
stage and unallocated remainder, the per-stage control declarations, and
the marking, storage and repair checks are exercised by the gate 3 contract
test: scripts/test_e31_production_manufacturing_contamination_control.py
against
scripts/e31_production_manufacturing_contamination_control_logic.py
(stdlib unittest, offline). The rejection term is graded against an
independently written closed form rather than a second copy of the
expression, and boundary cases use assertAlmostEqual.
Run: python3 scripts/test_e31_production_manufacturing_contamination_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

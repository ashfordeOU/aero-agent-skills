---
name: e3301-holding-torque-force-dimensioning
description: "Size the holding function of a spacecraft mechanism for its latched and braked states under ECSS-E-ST-33-01 clause 4.7.5.3.3. Use when a latch preload, a magnetic detent, a powered or unpowered brake or self-locking gearing has to hold against the disturbance of that state, with the minimum uncertainty factors applied in both directions at once so the capability is knocked down while the disturbance is raised, a powered hold refused credit in an unpowered state, and the holding margin reported per state rather than once for the whole mechanism. Trigger: ecss, e-st-33-01-mechanisms, mechanism-holding-margin, latch-preload-capability, unpowered-brake-holding-torque, holding-uncertainty-factor-pair, held-state-disturbing-torque."
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
  tags: [ecss, e-st-33-01-mechanisms, e3301-holding-torque-force-dimensioning, mechanism-holding-margin, latch-preload-capability, unpowered-brake-holding-torque, holding-uncertainty-factor-pair, held-state-disturbing-torque]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Holding Torque and Force Dimensioning (space-systems/ecss/e3301-holding-torque-force-dimensioning)

Use when the task is the holding side of ECSS-E-ST-33-01 clause
4.7.5.3.3 -- showing that each state in which a mechanism is supposed
to stay put actually stays put, with the uncertainty the clause
requires on both the holding capability and the disturbance.

## Domain quick reference

- Holding is assessed per state, not per mechanism. The same hinge can
  be latched after deployment, held on a powered brake during a slew,
  held on an unpowered brake after a bus undervoltage and held by
  self-locking gearing at rest. Capability and disturbance are
  different in each, so a single holding margin hides the weakest one.
- The uncertainty is applied twice, in opposite directions. The
  declared holding capability is knocked down to the share the state
  kind is credited with, and the declared disturbing torque or force is
  raised by that kind's minimum uplift. Applying only one is half the
  intended conservatism.
- The state kind sets the floor. A positive mechanical latch keeps most
  of its declared capability and faces the lightest uplift; a magnetic
  detent, a brake and self-locking gearing sit in the middle; a
  friction clamp keeps least and faces the most, because its capability
  is a friction coefficient in disguise.
- The knowledge basis bites from both sides. A capability measured on
  flight-standard hardware is knocked down by nothing extra; one
  estimated from heritage is knocked down further and its disturbance
  is raised by the same severity.
- A declared factor is accepted only when it is at least as severe as
  the floor. A more conservative declaration is kept; a lighter one is
  replaced by the floor and reported, so tailoring happens where
  tailoring belongs.
- A powered hold is not available in an unpowered state. Crediting a
  powered brake after a power loss is not an optimistic factor, it is a
  capability that is simply not there, so the effective capability is
  zero and the state is reported as unheld.

## Workflow

1. Declare the mechanism: identifier, torque or force units and the
   life points every held state has to be assessed at.
2. Enter each held state with its kind, its knowledge basis, the
   declared holding capability, the disturbing load in that state,
   whether power is available, and any declared factors.
3. Resolve the minimum capability retention and the minimum disturbance
   uplift from the kind and the basis, and hold any declared factor to
   the more severe of the declaration and the floor.
4. Compute the effective capability and the factored disturbance, then
   the holding margin as their quotient minus one. Set the effective
   capability to zero where a powered hold is credited without power.
5. Grade each margin, treating a margin that lands exactly on zero as
   the no-reserve condition rather than as a random sign, and record a
   state that skipped a required life point.
6. Report the governing state, every state with a finding and every
   state that is not actually held.

## Pitfalls

- Applying the uncertainty to only one side. Knocking the latch preload
  down while leaving the disturbance at its declared value produces a
  margin roughly twice what the clause asks for.
- Treating a friction clamp like a positive latch. A clamp holds by a
  coefficient that falls with contamination, wear and vacuum dwell,
  which is why it carries the harshest pair of factors in the table.
- Crediting the powered brake in the safe-mode case. The disturbance
  that matters most often arrives with the power loss that removed the
  brake, and the two cannot be assessed independently.
- Assessing the latched state at begin of life only. Preload relaxes,
  interfaces bed in and lubricants migrate, so the end-of-life
  capability is the one that decides whether the state survives.
- Reporting one holding margin for the mechanism. The mechanism is only
  as held as its weakest state, and an average across states makes a
  marginal detent invisible behind a strong latch.
- Comparing a declared factor with its floor, or a margin with zero, by
  bare arithmetic. Both are products and quotients of floats, so a
  value written exactly to its bound can land either side of it; the
  comparisons absorb that representation error.

## Behavior contract (gate 3)

The per-kind retention and uplift tables, the basis severity acting on
both sides, the declared-factor floor in both directions, the
unpowered-hold rule, the holding margin and its grouping, life-point
coverage and the mechanism-level governing state are exercised by the
gate 3 contract test:
scripts/test_e3301_holding_torque_force_dimensioning.py against
scripts/e3301_holding_torque_force_dimensioning_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_holding_torque_force_dimensioning.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

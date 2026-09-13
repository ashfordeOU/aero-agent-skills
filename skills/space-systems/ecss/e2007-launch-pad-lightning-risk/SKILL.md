---
name: e2007-launch-pad-lightning-risk
description: "Use when assess the launch-pad lightning risk demanded by ECSS-E-ST-20-07C clause 4.2.3.2: categorize every threat component as direct-attachment, indirect-magnetic-coupling or conducted-umbilical-transient, place the vehicle against the rolling-sphere protected volume built by the pad lightning-masts for the declared protection-level, compute the loop-induced voltage from a nearby-stroke current-derivative and the shield-transfer voltage driven along an umbilical, compare both against the equipment transient-withstand level, and grade the residual risk on a likelihood-severity matrix before the vehicle is cleared to stand on the pad. Trigger: ecss, e-st-20-07c, e-st-20-electrical-scope, launch-pad-lightning, rolling-sphere-protection, direct-attachment-threat, indirect-lightning-coupling, umbilical-transient, transient-withstand-level, residual-risk-matrix."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-launch-pad-lightning-risk, launch-pad-lightning, rolling-sphere-protection, direct-attachment-threat, indirect-lightning-coupling, umbilical-transient, transient-withstand-level]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Launch-Pad Lightning Risk (space-systems/ecss/e2007-launch-pad-lightning-risk)

Use when the task is the pad-phase lightning risk assessment of
ECSS-E-ST-20-07C clause 4.2.3.2 -- covering both the direct effects of
an attachment to the vehicle or its pad structure and the indirect
effects coupled into vehicle circuits by a nearby stroke, for the whole
period the assembled system stands on the pad.

## Domain quick reference

- Three threat components are assessed, and none substitutes for
  another. Direct-attachment is the stroke terminating on the vehicle
  or on the pad structure carrying it. Indirect-magnetic-coupling is
  the voltage driven into vehicle wiring loops by the rapidly changing
  magnetic field of a stroke that terminates nearby. The
  conducted-umbilical-transient is the voltage developed along the
  ground-support umbilical when part of the stroke current flows on its
  shield. An unrecognised threat type is rejected rather than folded
  into one of the three.
- Direct-attachment protection is judged geometrically with the
  rolling-sphere construction: a sphere whose radius follows the
  declared protection-level (the more demanding the level, the smaller
  the sphere) is rolled over the pad lightning-masts, and whatever the
  sphere cannot touch is inside the protected volume. For a mast no
  taller than the sphere radius the protected radius at a given height
  is the difference of two chord terms; for a mast taller than the
  sphere radius the sphere can rest against the mast flank, the
  protected radius shrinks to nothing at the height of the radius, and
  anything higher is exposed to a side strike. That second branch is
  why tall vehicles are protected by catenary systems rather than by
  bare masts.
- Indirect coupling is driven by the current-derivative, not by the
  peak current alone: a fast-rising stroke of moderate amplitude can
  induce more loop voltage than a slow high-amplitude one. The induced
  loop voltage scales with the enclosed loop-area and the
  current-derivative, and falls with the distance to the stroke
  channel.
- The umbilical path scales with the share of stroke current taken by
  the shield, with the shield transfer-impedance per unit length and
  with the exposed run length; it is the path that survives an
  otherwise perfect rolling-sphere result, because the umbilical
  connects the protected vehicle to unprotected ground equipment.
- Each computed stress is compared against the equipment
  transient-withstand level, and what remains is graded on a
  likelihood-severity matrix so that a residual risk can be accepted,
  reduced or refused by name rather than by impression.

## Workflow

1. Normalize the stroke parameters (peak current, rise time, distance
   to the stroke channel) and reject a non-positive peak current, a
   non-positive rise time or a non-positive distance before any
   coupling is computed.
2. Categorize every declared threat component into the three
   recognised kinds, resolving the accepted aliases and rejecting
   anything else. Record which of the three the assessment actually
   covers.
3. Select the rolling-sphere radius from the declared protection-level
   and compute the protected radius at the vehicle height for each pad
   mast, taking the tall-mast branch when the mast exceeds the sphere
   radius. The vehicle is protected against direct attachment when at
   least one mast covers its horizontal offset.
4. Compute the loop-induced voltage from the current-derivative, the
   enclosed loop-area and the distance to the channel, and compare it
   against the equipment transient-withstand level with an explicit
   floating-point tolerance.
5. Compute the umbilical shield-transfer voltage from the shared stroke
   current, the transfer-impedance per unit length and the exposed run
   length, and compare it against the umbilical-side withstand level.
6. Derive a likelihood and a severity for each component from the
   computed stress ratio and the protection result, grade each on the
   risk matrix, and take the residual risk as the worst component.
7. Report a finding for every uncovered threat component, for a vehicle
   outside the protected volume, and for every stress above its
   withstand level; the pad configuration is acceptable only when the
   finding list is empty.

## Pitfalls

- Declaring the vehicle protected because a mast is taller than it:
  once the mast exceeds the rolling-sphere radius, the protected radius
  collapses above that radius, so mast height alone proves nothing.
- Grading the indirect threat from peak current alone: the induced loop
  voltage follows the current-derivative, so halving the rise time
  doubles the stress at unchanged amplitude.
- Assessing direct attachment only and closing the clause: the
  umbilical path bypasses the rolling-sphere result entirely and is
  frequently the driving case, which is why an uncovered threat
  component is a finding in its own right.
- Treating a stress exactly at the withstand level as a failure because
  the comparison was written with a bare inequality: the induced
  voltage is a product and quotient of physical constants, so an
  exactly compliant case can land a few units in the last place above
  the level. Absorb that representation error in the comparison, never
  by raising the withstand level.
- Taking the average of the component risks as the residual risk: the
  residual risk is the worst surviving component, because the pad is
  cleared or not as a whole.

## Behavior contract (gate 3)

The threat categorization, rolling-sphere protected-volume,
current-derivative, induced-loop-voltage, umbilical shield-transfer,
withstand-comparison and risk-matrix logic is exercised by the gate 3
contract test: `scripts/test_e2007_launch_pad_lightning_risk.py`
against `scripts/e2007_launch_pad_lightning_risk_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_launch_pad_lightning_risk.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

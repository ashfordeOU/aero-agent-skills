---
name: residual-strength
description: "Use when you must compute the residual strength of a cracked structure for a damage tolerance assessment: derive the residual strength from fracture toughness and crack length, find the critical crack length at which the applied stress reaches Kc, and evaluate the margin of the residual strength against the limit load. Produces the residual strength, the critical crack length, and the limit-load margin verdict that size inspection intervals and repair decisions. Trigger: residual strength, critical crack, fracture toughness, limit load, stress intensity, damage tolerance."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: damage-tolerance
  tags: [residual-strength, critical-crack-length, fracture-toughness, limit-load, stress-intensity, damage-tolerance, crack-length]
  version: 0.1.0
  author: AeroSkills
---

# Residual Strength (structures/damage-tolerance/residual-strength)

Use when the task is the residual strength of a cracked structure for a
damage tolerance assessment: residual strength from fracture toughness,
critical crack length, and the margin against the limit load.

## Domain quick reference

- Residual strength is the highest stress a cracked structure carries
  before fracture; FAR 25.571 damage tolerance practice requires it to
  stay above the limit load at the assumed damage size.
- The mode I stress intensity factor K = beta * sigma * sqrt(pi * a)
  scales the crack-tip stress field; beta is the geometry factor (1.0
  for a central through-crack in a wide plate).
- Fracture occurs when K reaches the material fracture toughness Kc; the
  crack length at which the applied stress drives K to Kc is the
  critical crack length.
- Residual strength falls with the inverse square root of the crack
  length, so a short crack barely reduces strength while a long crack
  drops it sharply.
- Units convention (single, consistent in the logic module): sigma in
  MPa, crack lengths in meters, K and Kc in MPa*sqrt(m).

## Workflow

1. Establish the material fracture toughness Kc, the geometry factor
   beta, and the current crack length; compute the residual strength
   with residual_strength.
2. Get the applied stress level; find the critical crack length with
   critical_crack_length.
3. Compare residual strength with the limit load using residual_margin;
   a margin below 1.0 means the cracked structure fails the limit load
   requirement.
4. Check the applied stress directly against Kc with crack_ok.
5. Feed the critical crack length and margin into the inspection
   interval and repair decision.

## Pitfalls

- Mixing units in K = beta * sigma * sqrt(pi * a): passing sigma in Pa
  with Kc in MPa*sqrt(m) shifts the result by 1e6. Keep sigma in MPa,
  crack lengths in meters, and K and Kc in MPa*sqrt(m).
- Using the total crack length 2a instead of the half-length a for the
  through-crack formula.
- Comparing K with Kc at a stale crack size: the critical crack length
  changes with the applied stress level.
- Treating the margin as a fixed property: it falls as the crack grows,
  so re-evaluate it at each assumed inspection size.
- Omitting the geometry factor beta, or applying the infinite-plate
  value to a finite panel or an edge crack.

## Behavior contract (gate 3)

The residual strength, critical crack length, and margin logic is
exercised by the gate 3 contract test: scripts/test_residual_strength_logic.py
against scripts/residual_strength_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_residual_strength_logic.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); residual strength methodology is common
  fracture-mechanics knowledge, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

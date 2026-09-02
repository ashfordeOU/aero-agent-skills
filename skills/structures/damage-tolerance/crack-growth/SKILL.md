---
name: crack-growth
description: "Use when you must calculate fatigue crack growth for damage-tolerant structure: estimate the mode I stress intensity factor at a crack, apply the Paris law crack growth rate, and project the cycles to grow the crack from the initial detectable size to the critical size. Produces the stress intensity factor, the Paris da/dN rate, the crack extension per cycle, and the cycles-to-critical estimate that feed residual strength and inspection interval assessments. Trigger: crack growth, stress intensity, paris law, damage tolerance, fatigue crack, da/dn."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: damage-tolerance
  tags: [crack-growth, paris-law, stress-intensity, damage-tolerance, fatigue-crack, fracture-mechanics]
  version: 0.1.0
  author: Aero Agent Skills
---

# Fatigue Crack Growth (structures/damage-tolerance/crack-growth)

Use when the task is fatigue crack growth evaluation for
damage-tolerant structure: stress intensity, Paris law rates, and
cycles-to-critical projections.

## Domain quick reference

- The mode I stress intensity factor K = Y * sigma * sqrt(pi * a)
  scales the crack-tip stress field; Y is the geometry factor (1.12
  for a small edge crack in a wide plate).
- The Paris law da/dN = C * (dK)^m relates the crack growth rate to
  the stress intensity range; C and m are material constants fitted
  from da/dN testing.
- Crack growth life runs from the initial detectable crack size to
  the critical size where residual strength drops below limit load;
  inspection intervals are derived from that life.
- Crack growth practice sits in the FAR-25.571 damage tolerance
  context for transport aeroplanes.
- Units (single convention, consistent across the logic module):
  sigma and dK in MPa / MPa*sqrt(m), crack sizes in meters, Paris
  C in (m/cycle)*(MPa*sqrt(m))^-m, da/dN in m/cycle. Anchor:
  C=1e-11, m=3, dK=20 gives da/dN = 8e-8 m/cycle; 1000 cycles
  extends the crack 8e-5 m; a 0.009 m extension takes 112,500
  cycles.

## Workflow

1. Establish the applied stress and crack size; compute the stress
   intensity factor with stress_intensity.
2. Get the material Paris constants C and m; compute the per-cycle
   rate with paris_dadN.
3. Project the extension over the cycle block with
   crack_growth_per_cycle.
4. Estimate the crack growth life with cycles_to_grow.
5. Feed the cycles-to-critical result into the residual strength and
   inspection interval assessment.

## Pitfalls

- Mixing units in the Paris law: passing dK in Pa while C is in
  (m/cycle)*(MPa*sqrt(m))^-m (or the reverse) shifts the rate by
  (1e6)^m. Keep sigma and dK in MPa with C in
  (m/cycle)*(MPa*sqrt(m))^-m and crack sizes in meters.
- Using the total stress instead of the stress range dK in the Paris
  law.
- Treating the stress intensity factor as constant while the crack
  grows.
- Growing a crack from a size at or beyond the critical size.
- Omitting the geometry factor Y or defaulting it for the wrong crack
  configuration.

## Behavior contract (gate 3)

The stress intensity, Paris rate, and growth life logic is exercised
by the gate 3 contract test: scripts/test_crack_growth.py against
scripts/crack_growth_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_crack_growth.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; crack growth
  methodology is common fracture-mechanics knowledge, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

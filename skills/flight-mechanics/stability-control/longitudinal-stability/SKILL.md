---
name: longitudinal-stability
description: "Use when you must assess static longitudinal stability of an aircraft: compute the neutral point from the wing aerodynamic center, the tail volume coefficient, the lift slope ratio, and the downwash gradient; derive the static margin at the current center of gravity; and determine whether the aircraft is longitudinally stable for pitch stability. Produces the neutral point location, the static margin, and the stability verdict that gate the longitudinal stability analysis. Trigger: static margin, neutral point, longitudinal stability, pitch stability, center of gravity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: stability-control
  tags: [longitudinal-stability, neutral-point, static-margin, pitch-stability, center-of-gravity, tail-volume]
  version: 0.1.0
  author: AeroSkills
---

# Static Longitudinal Stability (flight-mechanics/stability-control/longitudinal-stability)

Use when the task is static longitudinal stability analysis: neutral
point, static margin, and the pitch stability verdict at a given
center of gravity.

## Domain quick reference

- The neutral point is the aerodynamic center of the whole aircraft
  (wing plus tail); all positions are fractions of the mean
  aerodynamic chord, dimensionless.
- Neutral point: h_np = h_ac_w + V_h * (a_t / a_w) * (1 - depsilon/
  dalpha), where h_ac_w is the wing aerodynamic center, V_h is the
  tail volume coefficient, a_t/a_w is the lift slope ratio, and
  depsilon/dalpha is the downwash gradient.
- The tail volume coefficient is dimensionless; the lift slope ratio
  and downwash gradient are dimensionless too.
- Static margin = neutral point - center of gravity; positive static
  margin means a stable configuration.
- Longitudinally stable when the static margin meets the minimum
  margin (default 0.05).

## Workflow

1. Collect the wing aerodynamic center, tail volume coefficient,
   lift slope ratio, and downwash gradient.
2. Compute the neutral point with neutral_point.
3. Take the center of gravity position and derive the static margin
   with static_margin.
4. Check the margin with longitudinally_stable.
5. Gate the pitch stability assessment on the verdict.

## Pitfalls

- Reversing the static margin sign: positive margin (neutral point
  aft of the center of gravity) is stable, not unstable.
- Confusing the neutral point with the wing aerodynamic center: the
  neutral point includes the tail contribution, the aerodynamic
  center of the wing alone does not.
- Zero tail volume coefficient: a configuration with no stabilizing
  tail surface cannot produce a meaningful neutral point offset.
- Downwash gradient at or above 1.0: physically invalid for this
  model.

## Behavior contract (gate 3)

The neutral point, static margin, and stability logic is exercised by
the gate 3 contract test: scripts/test_longitudinal_stability.py
against scripts/longitudinal_stability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_longitudinal_stability.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 require
  positive static longitudinal stability for transport aeroplanes;
  the neutral point and static margin method is common flight
  mechanics methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

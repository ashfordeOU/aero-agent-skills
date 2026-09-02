---
name: envelope-expansion
description: "Use when you must plan flight test envelope expansion: compute the corner speed (maneuvering speed VA) from the stall speed and the limit load factor, classify airspeeds into the flight test speed categories, and size the expansion steps against the load factor envelope. Produces the corner speed, the airspeed classification per test point, the per-step speed increment, and the load factor limit verdict that gate the expansion program. Trigger: envelope expansion, corner speed, airspeed classification, load factor, flight test, expansion step, maneuver envelope."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-test-operations
pack: flight-test-operations
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: envelope
  tags: [envelope-expansion, corner-speed, airspeed-classification, load-factor, expansion-step, flight-test]
  version: 0.1.0
  author: Aero Agent Skills
---

# Envelope Expansion (flight-test-operations/envelope/envelope-expansion)

Use when the task is flight test envelope expansion: corner speed,
airspeed classification, and expansion step planning against the load
factor envelope.

## Domain quick reference

- Corner speed (maneuvering speed) VA = VS * sqrt(n_max), where VS is
  the reference stall speed and n_max the limit load factor.
- Units: speeds in m/s (convert knots or km/h before use); load factor
  n is dimensionless.
- Airspeed categories: VFE (flaps extended limit), VA (maneuvering),
  VNO (normal operating limit), VNE (never exceed).
- Expansion steps move the test speed from the current point toward a
  target in equal increments, with the load factor checked against the
  limit at every point.

## Workflow

1. Compute the corner speed with corner_speed(vs_ms, n_max).
2. Classify each test speed with classify_airspeed(v_ms, vfe, va, vno, vne).
3. Size the increments with expansion_step_size(target_v, current_v, n_steps).
4. Check every point with load_factor_within_limit(n, n_max).
5. Gate the expansion program on the classification and limit verdicts.

## Pitfalls

- Expanding past VA without stall checks: at VA the limit load factor
  can stall the wing, so test near VA only with stall protection active.
- Classification boundary handling: boundaries are half-open; a speed
  equal to VFE belongs to vfe-to-va, equal to VA to va-to-vno, and so
  on. Use the documented comparisons, not hand-adjusted bands.
- Steps <= 0: a non-positive step count or a target below the current
  speed raises ValueError instead of producing a nonsense increment.
- Mixed units: convert every speed to m/s before computing VA.

## Behavior contract (gate 3)

The corner speed, classification, step, and load factor logic is
exercised by the gate 3 contract test: scripts/test_envelope_expansion.py
against scripts/envelope_expansion_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_envelope_expansion.py

## Compliance

- Standards referenced, not reproduced: FAR-25.335 and CS-25.335 design
  airspeeds set the maneuvering speed context; flight test envelope
  expansion methodology is common knowledge, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

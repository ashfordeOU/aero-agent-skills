---
name: v-speeds
description: "Use when you must compute the v-speeds set for a flight test: derive the vref reference landing speed as 1.3 times the vs0 stalling speed in landing configuration, the v2 takeoff safety speed as 1.2 times the vs1 stalling speed in takeoff configuration, and the vr rotation speed as 1.1 times vs1, then validate the speed ordering and check the vno normal operating limit and the vne never exceed speed. Produces the vref, v2, and vr speeds, a validated v-speeds dict, and the vne guard verdict with the margin in m/s that gate the flight test speed assessment. Trigger: vref, v2, vr, vs0, vs1, vno, vne."
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
  tags: [v-speeds, vref, v2, vr, vs0, vs1, vno, vne, stall-speed, rotation-speed, takeoff-safety-speed, reference-landing-speed, never-exceed]
  version: 0.1.0
  author: AeroSkills
---

# V-Speeds (flight-test-operations/envelope/v-speeds)

Use when the task is v-speeds determination for a flight test:
reference landing speed, takeoff safety speed, rotation speed, and
the vno/vne guard.

## Domain quick reference

- V-speeds from stall speeds with the standard certification
  factors (FAR-25.107/25.125 context; the factors are common
  certification practice, the exact basis comes from the flight
  test program):
  - vref = 1.3 * vs0, with vs0 the stalling speed in the landing
    configuration, in m/s.
  - v2 = 1.2 * vs1, with vs1 the stalling speed in the takeoff
    configuration, in m/s.
  - vr = 1.1 * vs1.
- All speeds are in m/s; convert knots or km/h before use.
- Speed ordering for a valid configuration set: vs1 >= vs (the
  takeoff configuration stalls at or above the clean
  configuration) and vs0 <= vs1 (the landing configuration stalls
  below the takeoff configuration); every speed must be positive.
- vno_vne_guard: margin_mps = vne - operating_speed; a positive
  margin means the operating speed stays below the never exceed
  speed.

## Workflow

1. Collect the stalling speeds vs (clean), vs0 (landing
   configuration), and vs1 (takeoff configuration) in m/s.
2. Derive the reference landing speed with
   reference_landing_speed(vs0).
3. Derive the takeoff safety speed with takeoff_safety_speed(vs1).
4. Derive the rotation speed with rotation_speed(vs1).
5. Assemble and validate the set with v_speeds(vs, vs0, vs1);
   invalid orderings raise ValueError.
6. Check the operating speed against the limit with
   vno_vne_guard(operating_speed, vne).
7. Gate the flight test speed assessment on the validated dict and
   the guard verdict.

## Pitfalls

- Mixing configurations: vs0 is the landing configuration stall
  and vs1 the takeoff configuration stall; swapping them flips the
  ordering checks and the resulting vref and v2 values.
- Applying the factors to the wrong base speed: vref uses vs0,
  while v2 and vr both use vs1.
- Trusting an unvalidated set: vs1 below vs (takeoff stall below
  clean stall) or vs0 above vs1 is a physically impossible
  configuration and raises ValueError, not a soft warning.
- Using a non-positive vne: the guard raises ValueError instead of
  reporting a negative margin.
- Unit drift: every speed must be in m/s; a knots value fed
  straight in produces vref, v2, and vr off by the conversion
  factor.

## Behavior contract (gate 3)

The reference landing speed, takeoff safety speed, rotation speed,
validation, and vno/vne guard logic is exercised by the gate 3
contract test: scripts/test_v_speeds.py against
scripts/v_speeds_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_v_speeds.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government
  work (public domain) and CS-25 is a free EASA download; the
  1.3/1.2/1.1 certification factors and the vno/vne limits sit in
  the FAR-25.107/25.125 context as common certification practice,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

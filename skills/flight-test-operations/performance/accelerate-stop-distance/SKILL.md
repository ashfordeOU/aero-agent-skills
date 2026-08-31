---
name: accelerate-stop-distance
description: "Use when you must compute the rejected takeoff accelerate stop distance for a flight test: accelerate the airplane to the decision speed V1, stop it with the braking deceleration, and check the total against the available runway length. Produces the accelerate distance, the stop distance, and the runway fits verdict that gate the rejected takeoff field length assessment. Trigger: rejected takeoff, V1 decision speed, braking deceleration, accelerate stop distance, runway length, balanced field length."
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
  subdomain: performance
  tags: [v1, braking, deceleration, runway, rejected-takeoff, balanced-field-length]
  version: 0.1.0
  author: AeroSkills
---

# Accelerate Stop Distance (flight-test-operations/performance/accelerate-stop-distance)

Use when the task is rejected takeoff performance for a flight test:
accelerate-stop distance from the decision speed V1, the braking
deceleration, and the runway length verdict.

## Domain quick reference

- Speeds in m/s, accelerations in m/s^2, distances in m. The braking
  deceleration is the friction coefficient times g, 9.80665 m/s^2.
- accelerate_distance: s_acc = v1^2 / (2 * a_acc), the accelerate
  leg from rest to the decision speed V1.
- stop_distance: s_stop = v1^2 / (2 * a_brake), the stop leg from
  V1 with full braking and no reverse thrust.
- accelerate_stop_distance: total = s_acc + s_stop; the balanced
  field length V1 is None in this simplified constant-acceleration
  model (no reaction time, no engine-out asymmetry).
- runway_verdict: margin = runway_m - required_m; verdict is fits
  when margin >= 0, else too short.
- Analytic check: v1 = 70 m/s, a_acc = 2.5 m/s^2 gives s_acc = 980 m;
  mu_b = 0.45 gives a_brake = 4.4130 m/s^2, s_stop = 555.17 m,
  total = 1535.17 m (2 dp).

## Workflow

1. Collect the decision speed V1, the acceleration to V1, and the
   braking friction coefficient.
2. Derive the braking deceleration with brake_deceleration.
3. Compute the accelerate leg with accelerate_distance and the stop
   leg with stop_distance.
4. Combine both legs with accelerate_stop_distance.
5. Check the total against the available runway with runway_verdict
   and gate the rejected takeoff on the verdict.

## Pitfalls

- Using the accelerate distance as the total: the rejected takeoff
  field length is the accelerate leg plus the stop leg.
- Forgetting that V1 is the decision speed in both legs: the stop
  leg starts at V1, not at the liftoff speed.
- Mixing units: v1 in m/s with a_acc in m/s^2 gives distances in m;
  knots or ft/s need conversion first.
- Reading a negative margin as an error: runway_verdict returns too
  short, which is a real, reportable rejected takeoff outcome.
- Treating balanced_v1 as a computed value: this model returns None
  by design; balanced field length needs a full engine-out model.

## Behavior contract (gate 3)

The accelerate-stop distance logic is exercised by the gate 3
contract test: scripts/test_accelerate_stop.py against
scripts/accelerate_stop_logic.py (stdlib unittest, offline). Run:
`python3 scripts/test_accelerate_stop.py`

## Compliance

- Standards referenced, not reproduced: FAR-25 (14 CFR Part 25) is
  US government work (public domain) and CS-25 is a free EASA
  download; the rejected takeoff accelerate-stop method is common
  flight-test methodology in the FAR 25.109 context, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

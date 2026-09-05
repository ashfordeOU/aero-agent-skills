---
name: balanced-field-length
description: "Use when you must compute the balanced field length and V1 decision speed of a multi-engine transport: derate the total thrust to the remaining engines, derive the constant ground accelerations and the braking deceleration, trace the accelerate-stop distance (roll on all engines to V1, react, brake to a stop) and the accelerate-go distance (roll to V1, continue on the remaining engines to lift-off, rotate, and climb over the 35-ft obstacle on the engine-out climb gradient), solve the quadratic balance for the V1 where the two distances are equal, and read the balanced field length. Produces the engine-out thrust, the accelerations, the accelerate-stop and accelerate-go distance curves, the balanced V1, and the balanced field length that gate the runway-length and engine-out certification assessment. Trigger: balanced field length, V1 decision speed, accelerate-stop distance, accelerate-go distance, engine-out field length, balanced V1."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [balanced-field-length, v1-decision-speed, accelerate-go-distance, accelerate-stop-distance, engine-out-field-length]
  version: 0.1.0
  author: AeroSkills
---

# Balanced Field Length (flight-mechanics/performance/balanced-field-length)

Use when the task is the engine-out field length of a multi-engine
transport with a V1 decision-speed balance. This leaf computes the
balanced field length: accelerate on all engines to a V1 decision
speed, then compare the accelerate-stop distance (brake to a full
stop after a reaction time) with the accelerate-go distance (continue
on the remaining engines, rotate, and climb over the 35-ft obstacle on
the engine-out climb gradient) and find the balanced V1 where the two
are equal. It pairs with takeoff-performance (the all-engine ground
roll estimate feeds the accelerate legs, but that leaf stops at
lift-off with no engine failure) and with oei-climb-gradient (which
scores the engine-out climb gradient against the FAR-25.121 minima but
integrates no distance; here the gradient is an input). Out of scope:
stall speed, lift-off speed, and the all-engine ground roll from wing
loading (takeoff-performance); climb gradient estimation and minima
comparison (oei-climb-gradient); measured-distance determination from
flight test data; and the inverse sizing of thrust or wing loading
from a required field length (vehicle-design/conceptual/
constraint-analysis).

## Domain quick reference

- Engine-out thrust: T_OEI = T_all * (engine_count - 1) /
  engine_count, with at least two engines.
- Ground-roll acceleration (constant, no aerodynamic drag or lift
  relief): a = g0 * (T - mu_roll * W) / W, rolling friction opposing
  the thrust.
- Braking deceleration magnitude: a_brake = g0 * mu_brake.
- Accelerate-stop distance: ASD(V1) = V1^2 / (2 a_all) +
  V1 * t_reaction + V1^2 / (2 a_brake).
- Accelerate-go distance: AGD(V1) = V1^2 / (2 a_all) +
  (V_LOF^2 - V1^2) / (2 a_oei) + V_LOF * t_rotation + h_obs /
  gradient, the air segment climbing the obstacle on the engine-out
  gradient.
- Balance quadratic from ASD(V1) = AGD(V1): A V1^2 + B V1 + C = 0
  with A = 1 / (2 a_brake) + 1 / (2 a_oei), B = t_reaction, and
  C = -(V_LOF^2 / (2 a_oei) + V_LOF * t_rotation + h_obs / gradient);
  A > 0 and C < 0 give one positive root.
- Balanced field length: BFL = ASD(V1_balanced) = AGD(V1_balanced).
- Module constants: g0 = 9.80665 m/s^2, reaction time 1.0 s, rotation
  time 1.0 s, obstacle height 10.668 m (35 ft, the FAR-25.113
  obstacle, paraphrased). SI throughout: forces in N, speeds in m/s.

## Workflow

1. Collect the takeoff case: all-engine thrust, engine count, weight,
   rolling friction, brake friction, lift-off speed, engine-out climb
   gradient, obstacle height, reaction time, and rotation time (the
   last three default to 35 ft, 1 s, and 1 s).
2. Split the thrust on the remaining engines with oei_thrust:
   T_OEI = T_all * (engine_count - 1) / engine_count.
3. Compute the constant accelerations: ground_acceleration for the
   all-engine thrust and for the engine-out thrust, and
   braking_deceleration from the brake friction; every call rejects
   non-physical inputs with ValueError.
4. Trace the accelerate-stop distance curve with
   accelerate_stop_distance: roll to V1 on all engines, coast for the
   reaction time, brake to a full stop. ASD(0) = 0 for a decision at
   rest.
5. Trace the accelerate-go distance curve with
   accelerate_go_distance: all-engine roll to V1, engine-out roll from
   V1 to lift-off, rotation at V_LOF, then the small-angle climb over
   the 35-ft obstacle on the engine-out gradient (obstacle height
   divided by the gradient).
6. Solve the V1 balance with balanced_v1: the quadratic root of
   ASD(V1) = AGD(V1); a root inside [0, V_LOF] is the balanced
   decision speed, and a root outside the bracket raises ValueError so
   the caller can disclose that no balanced decision exists for the
   case.
7. Read the balanced field length with balanced_field_length at the
   balanced V1: the common distance where the accelerate-stop distance
   equals the accelerate-go distance.
8. Sanity-check the bracket: ASD rises and AGD falls with V1, so the
   crossing is unique inside [0, V_LOF]; a steeper engine-out climb
   gradient shortens the accelerate-go distance and lowers the
   balanced V1, while stronger brakes shorten the accelerate-stop
   distance and raise the balanced V1.

## Worked example

Twin-engine transport, W = 600000 N, total installed thrust 150000 N,
V_LOF = 80 m/s, mu_roll = 0.03, mu_brake = 0.45, engine-out climb
gradient 0.024, 35-ft obstacle, 1 s reaction and rotation times
(scripts/balanced_field_length_logic.py real outputs):

- oei_thrust = 75000 N.
- a_all = 2.15746 m/s^2, a_oei = 0.931632 m/s^2,
  a_brake = 4.41299 m/s^2; air segment 10.668 / 0.024 = 444.5 m.
- Balanced V1 = 77.2815 m/s, 0.966 of V_LOF.
- ASD(V1) = AGD(V1) = balanced field length = 2138.10 m.
- Bracket: ASD(0) = 0 < AGD(0) = 3959.33 m; ASD(80) = 2288.36 m >
  AGD(80) = 2007.72 m, so the balanced root is unique inside the
  bracket.

## Pitfalls

- Passing a decision speed at or beyond lift-off as a balance: a V1
  past V_LOF is rejected, and balanced_v1 raises when the quadratic
  root falls outside [0, V_LOF] (no balanced decision exists for that
  case, for example very weak brakes).
- Mixing the all-engine acceleration into the engine-out leg: after
  V1 the accelerate-go leg runs on a_oei from the remaining-engine
  thrust, which is weaker, not on a_all.
- Dropping a segment: the accelerate-stop distance includes the
  reaction-time coast before braking, and the accelerate-go distance
  includes the rotation at V_LOF plus the obstacle height over the
  gradient; each omission shortens the field length.
- Forgetting the friction checks: a thrust at or below mu_roll * W
  cannot accelerate the aircraft and raises ValueError; brake
  friction must lie strictly inside (0, 1).

## Verification

Deterministic, offline checks (scripts/test_balanced_field_length.py):
worked-example anchors above within the stated tolerances; ASD(0) = 0
and the bracket monotonicity ASD(0) < ASD(40) < ASD(80) with
AGD(0) > AGD(40) > AGD(80); ASD == AGD at the balanced V1 to machine
precision; the minimax property that no other decision speed needs
less runway than the balanced field length; sensitivity directions
(gradient 0.03 lowers the balanced V1 and the field length, brake
friction 0.55 raises the balanced V1 and lowers the field length);
ValueError rejection of non-physical inputs (engine_count 1, zero or
negative gradient, decision speed beyond lift-off, mu_roll outside
[0, 1), mu_brake at 0 or 1, non-positive weight or thrust, negative
reaction time); and repeated-call determinism.

## Related leaves

- flight-mechanics/performance/takeoff-performance
- flight-mechanics/performance/oei-climb-gradient
- flight-mechanics/performance/landing-performance
- vehicle-design/conceptual/constraint-analysis

## Behavior contract (gate 3)

The engine-out field length logic is exercised by the gate 3 contract
test: scripts/test_balanced_field_length.py against
scripts/balanced_field_length_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_balanced_field_length.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain); the balanced field length method with the V1
  decision-speed balance, the 35-ft obstacle, and the engine-out
  climb are common flight-mechanics methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

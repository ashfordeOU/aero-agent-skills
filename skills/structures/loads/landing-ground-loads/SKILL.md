---
name: landing-ground-loads
description: "Use when you must compute the ground loads on an aircraft structure for the certification landing and ground-handling conditions: the static nose and main gear reactions from the weight and CG position over the wheelbase, the level-landing reactions at a limit vertical inertia load factor, the braked-roll deceleration and brake force from the main gear friction, the tail-down-condition reaction with the nose gear unloaded, and the one-wheel-load reaction from the lateral CG offset over the track. Produces gear reactions, the braking deceleration and the critical per-station condition that gates a landing loads check. Trigger: landing-ground-loads, ground-reactions, level-landing, tail-down-condition, one-wheel-load, braked-roll."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: loads
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: loads
  tags: [landing-ground-loads, ground-reactions, level-landing, tail-down-condition, one-wheel-load, braked-roll]
  version: 0.1.0
  author: Aero Agent Skills
---

# Landing Ground Loads (structures/loads/landing-ground-loads)

Use when the static reaction sets of the certification landing and
ground handling conditions must be resolved for an aircraft structure:
the parked and level-landing split between the nose and main gear, the
braked-roll deceleration with all brakes on the main gear, the
tail-down condition with the nose gear unloaded, and the one-wheel
asymmetric level landing. This leaf implements the reaction statics in
pure Python, stdlib only, and reports the critical condition for each
gear station that gates a landing loads check. The limit vertical
inertia load factor is an input chosen from the certification basis; the
in-flight air load conditions of the same load survey live in the
companion loads-pack leaf and are not computed here. It pairs with
vehicle-design/sizing/landing-gear-sizing, which carries these reaction
loads into the gear component sizing.

## Domain quick reference

- Geometry: a is the distance from the nose gear to the CG, b the
  distance from the CG to the main gear, wheelbase = a + b. Static
  reactions R_nose = W * b / (a + b) and R_main = W * a / (a + b);
  the two reactions sum to the weight W (round-trip identity).
- Weight: W = m * g0 with g0 = 9.80665 m/s^2 (G0). A mass in kg enters
  through weight_force; every other function takes the weight W in N.
- Level landing: the static reactions scaled by the limit vertical
  inertia load factor LF: nose = LF * W * b / (a + b), main = LF * W *
  a / (a + b), total = LF * W. N_LEVEL_DEFAULT = 2.5 is the typical
  input value; the certification value is a caller choice.
- Braked roll: all brakes act on the main gear. The main reaction is
  evaluated at the ground-roll load factor (default 1.0):
  F_brake = friction * R_main and deceleration_g = F_brake / W =
  friction * a / (a + b) in g units, a pure number. At the worked
  example 0.8 * 0.8 = 0.64 exactly.
- Tail-down condition: nose gear unloaded, the entire vertical
  reaction sits on the main gear: R = W * LF.
- One-wheel condition: asymmetric level landing from a lateral CG
  offset y over the track t: loaded side reaction R = W * LF * (0.5 +
  y / t), valid for y in [0, t/2]; a CG outside the track half width
  is non-physical for this condition.
- Friction is a dimensionless braking coefficient in [0, 1]; the load
  factor, distances and track are SI (N, m), deceleration is in g.
- FAR 25.471 to 25.511 style ground conditions frame the reaction
  statics above; summary-only, reference-only per standards-map.yaml.

## Workflow

1. Convert the mass to a weight force with weight_force, or take the
   weight W directly.
2. Split the parked load with static_reactions (nose and main gear).
3. Scale to the limit condition with level_landing_reactions at the
   chosen limit vertical inertia load factor.
4. Evaluate the braked roll with braked_roll using the braking
   friction coefficient (main gear reaction, brake force, deceleration
   in g).
5. Take the tail-down reaction with tail_down_reaction when the nose
   gear is unloaded.
6. Take the asymmetric case with one_wheel_reaction at the lateral CG
   offset and the track.
7. Call landing_loads_summary for the full per-station set; the
   critical main reaction is the maximum of the main gear values
   (level landing, braked roll, tail down, one wheel) and the critical
   nose reaction the maximum of the nose values.
8. Confirm the deterministic checks with the contract test
   scripts/test_landing_ground_loads.py.

## Worked example

Transport: mass 60 000 kg (W = 588 399 N), nose gear to CG a = 8 m, CG
to main gear b = 2 m, limit load factor 2.5, braking friction 0.8,
lateral offset 0.1 m, track 5.0 m.

- Static: R_nose = 588 399 * 2 / 10 = 117 679.8 N, R_main = 588 399 *
  8 / 10 = 470 719.2 N; the pair sums to 588 399 N exactly.
- Level landing at 2.5: nose = 294 199.5 N, main = 1 176 798.0 N
  (inside the 1.10e6 to 1.25e6 N bound), total = 1 470 997.5 N.
- Braked roll (load factor 1.0): main reaction 470 719.2 N, brake
  force 0.8 * 470 719.2 = 376 575.4 N, deceleration 0.64 g; the
  identity deceleration_g = friction * a / (a + b) = 0.8 * 0.8 holds
  to float precision.
- Tail down: R = 588 399 * 2.5 = 1 470 997.5 N on the main gear.
- One wheel: R = 588 399 * 2.5 * (0.5 + 0.1 / 5) = 764 918.7 N (inside
  the 0.72e6 to 0.81e6 N bound).
- Summary with lateral_offset 0.1 m: static nose 117 679.8 N, static
  main 470 719.2 N, level nose 294 199.5 N, level main 1 176 798.0 N,
  brake force 376 575.4 N, deceleration 0.64 g, tail down main
  1 470 997.5 N, one wheel main 764 918.7 N. Critical main is the
  tail-down value 1 470 997.5 N and critical nose the level nose value
  294 199.5 N.


## Pitfalls

- Feeding mass where weight is expected: every function past
  weight_force takes the weight W in N (m * g0); passing kilograms
  divides every reaction by gravity.
- Swapping the CG arms: a is nose-gear-to-CG and b is CG-to-main-
  gear, so the nose reaction W * b / (a + b) uses the FAR arm and
  the main reaction W * a / (a + b) the near arm; swapping them
  puts the parked load on the wrong gear.
- Using the static reaction for a dynamic condition: the level
  landing, tail-down and one-wheel cases scale by the limit vertical
  inertia load factor, and the certification value is a caller
  choice (2.5 typical), not a module constant.
- Forgetting the braked-roll identity: with all brakes on the main
  gear the deceleration is friction * a / (a + b) (0.64 g in the
  worked example), so a friction value near 1 does not mean a 1 g
  stop.
- Placing the CG outside the track half width: the one-wheel
  condition is only valid for a lateral offset y in [0, t/2]; a CG
  beyond that is non-physical and raises ValueError.
- Sizing one station only: the critical main reaction is the maximum
  over level landing, braked roll, tail down and one wheel (the
  tail-down 1 470 997.5 N in the worked example), so the summary's
  per-station max, not any single condition, gates the gear check.
## Verification

- Confirm static_reactions(588399.0, 8, 2) returns nose 117 679.8 N
  and main 470 719.2 N and that the sum equals the weight (1e-6
  relative checks).
- Confirm level_landing_reactions scales the static set by the load
  factor and that the total equals W * load_factor.
- Confirm braked_roll deceleration equals friction * a / (a + b)
  (1e-9 relative) and the brake force equals friction times the main
  reaction.
- Confirm one_wheel_reaction at lateral offset 0 returns W * LF * 0.5
  exactly and that the worked example value 764 918.7 N lies in
  0.72e6 to 0.81e6 N.
- Confirm the summary picks the tail-down value as critical main and
  the level nose as critical nose.
- Confirm every non-positive weight, a, b, load factor and track, and
  every friction outside [0, 1] or lateral offset outside [0, track/2]
  raises ValueError.
- Run the contract test offline: python3
  scripts/test_landing_ground_loads.py (32 tests, deterministic).

## Related leaves

- structures/loads/random-vibration-analysis: dynamic response methods
  for the vibration qualification of the same structure, the dynamic
  complement to this static reaction set.
- structures/loads/shock-response-spectrum: transient response spectra
  used for shock qualification cases around the ground conditions.
- vehicle-design/sizing/landing-gear-sizing: gear component sizing
  counterpart that carries these reaction loads into the structure
  design.
- vehicle-design/sizing/brake-energy-sizing: braking energy sizing for
  the rejected takeoff case that pairs with the braked-roll check.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_landing_ground_loads.py

The test covers the worked example contract (static 117 679.8 N /
470 719.2 N, level main 1 176 798 N inside 1.10e6 to 1.25e6 N, brake
force 376 575.36 N, deceleration 0.64 g, tail down 1 470 997.5 N, one
wheel 764 918.7 N inside 0.72e6 to 0.81e6 N), the exact identities
(static W*b/(a+b) and W*a/(a+b), reaction sum equals weight, decel =
friction*a/(a+b), one-wheel offset 0 equals W*LF*0.5), boundary cases
(friction 0 and 1, offset at track half), ValueError rejection of every
non-physical input, and determinism.

## Compliance

- Standards referenced, not reproduced: the FAR 25.471 to 25.511 style
  ground conditions are summarized as standard reaction statics above
  (summary-only, reference-only per standards-map.yaml); the limit
  load factor is an input, never asserted as a regulation quote.
- compliance: STANDARDS-REF, gated: false.

# Wave-30 leaf spec: landing-ground-loads (structures, loads pack)

- Path: skills/structures/loads/landing-ground-loads/
- Pack: loads (siblings: gust-maneuver-loads, random-vibration-analysis,
  shock-response-spectrum).
- Standards ids: far-25 (reference-only). Ledger Standard: far-25.
- Family: structures

## Claim

Compute the ground loads on an aircraft structure for the certification
landing and ground-handling conditions: the static nose and main gear
reactions from the weight and the CG position over the wheelbase, the level
landing reactions at a limit vertical inertia load factor, the braked-roll
deceleration and horizontal ground reaction from the braking friction on the
main gear, the tail-down condition reaction with the nose gear unloaded, and
the one-wheel asymmetric reaction from the lateral CG offset and the track.
Produces the gear reactions, the braking deceleration, and the critical
condition for each gear station that gate a landing loads check.

Does NOT do: compute gust or maneuver AIR loads in flight (gust-maneuver-loads
owns the FAR 25.337/25.341 discrete gust and maneuvering envelope load
factors); size the landing gear struts, shock absorber stroke, tires, or
wheelbase (vehicle-design landing-gear-sizing owns strut load split, sink
speed stroke sizing, and tire rating); model dynamic drop-test energy
absorption (FAR 25.723 drop test energy belongs to dynamic analysis, not this
static reaction set); analyze braking system energy (vehicle-design
brake-energy-sizing owns RTO brake energy). This leaf resolves the STATIC
reaction sets of the FAR 25.471-25.511-style ground conditions; the limit load
factor is an input chosen from the certification basis.

## Model (implement exactly)

Module constants:
- G0 = 9.80665.
- N_LEVEL_DEFAULT = 2.5 (typical limit vertical inertia load factor input
  used when a caller does not supply one; the certification value is an
  input, never asserted as a regulation quote).

Functions (pure stdlib; weights in N or kg->N through weight_force):
- weight_force(mass_kg) -> mass_kg * G0 (pure helper).
- static_reactions(weight, dist_nose_to_cg, dist_cg_to_main) -> dict:
  {nose_N, main_N} with wheelbase = a + b; R_nose = W * b / (a + b);
  R_main = W * a / (a + b). ValueError if weight <= 0 or a <= 0 or b <= 0.
- level_landing_reactions(weight, dist_nose_to_cg, dist_cg_to_main,
  load_factor=N_LEVEL_DEFAULT) -> dict: static reactions scaled by the limit
  load factor ({nose_N, main_N, total_N}). ValueError if load_factor <= 0.
- braked_roll(weight, dist_nose_to_cg, dist_cg_to_main, friction,
  load_factor=1.0) -> dict: main reaction at the given load factor (all
  brakes on main gear): F_brake = friction * R_main; decel_g = F_brake /
  weight (g units, pure number); returns {main_reaction_N, brake_force_N,
  deceleration_g}. ValueError if friction < 0 or > 1 or load_factor <= 0.
- tail_down_reaction(weight, load_factor=N_LEVEL_DEFAULT) -> float:
  nose gear unloaded, entire vertical reaction on the main gear:
  R = weight * load_factor. ValueError if load_factor <= 0.
- one_wheel_reaction(weight, load_factor, lateral_offset, track) -> float:
  asymmetric level landing: R = weight * load_factor * (0.5 +
  lateral_offset / track) on the loaded side. ValueError if track <= 0,
  lateral_offset < 0 or lateral_offset > track / 2 (CG outside the track
  half-width is non-physical for this condition), load_factor <= 0.
- landing_loads_summary(weight, dist_nose_to_cg, dist_cg_to_main,
  load_factor=N_LEVEL_DEFAULT, friction=0.8, lateral_offset=0.0,
  track=5.0) -> dict: {static_nose_N, static_main_N, level_nose_N,
  level_main_N, brake_force_N, deceleration_g, tail_down_main_N,
  one_wheel_main_N, critical_main_N (max of the main-gear values),
  critical_nose_N}. ValueErrors propagate.

## Worked example

Transport: mass 60 000 kg (W = 588 399 N), distance nose gear to CG a = 8 m,
CG to main gear b = 2 m, limit load factor 2.5, braking friction 0.8, lateral
offset 0.1 m, track 5.0 m.

Deterministic anchors (module outputs as assert targets; bounds):
- static nose = 117 680 N, static main = 470 719 N (EXACT identities:
  W*b/10 and W*a/10; assert within 1e-6 relative).
- level landing main = 1 176 798 N (bound 1.10e6-1.25e6 N); nose = 294 199 N.
- brake force at load factor 1.0 = 0.8 * 470 719 = 376 575 N; deceleration
  0.64 g (EXACT ratio check: decel_g = friction * a/(a+b) = 0.8 * 0.8 =
  0.64; assert within 1e-9 relative).
- tail down main = W * 2.5 = 1 470 997 N (EXACT).
- one wheel = W * 2.5 * (0.5 + 0.1/5) = 588 399 * 2.5 * 0.52 = 764 919 N
  (bound 0.72e6-0.81e6 N).
- critical main is the tail-down value (max) and critical nose is the level
  nose value. Verify the summary picks those.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: weight <= 0, a or b <= 0, load_factor <= 0, friction < 0 or > 1,
  track <= 0, lateral_offset < 0 or > track/2.
- one_wheel_reaction with lateral_offset 0 == weight * load_factor * 0.5
  (exact identity).
- Static reaction sum == weight (round-trip identity).
- Determinism.

## Corpus fragment (eval/hit1-wave30-landing-ground-loads.yaml)

Forbidden tokens (siblings): gust, maneuver, load-factor-envelope, v-n
(gust-maneuver-loads + FTO envelope); strut-stroke, sink-speed, tire,
wheelbase sizing (landing-gear-sizing); rto-brake-energy (brake-energy).
Distinctive tokens ONLY: landing-ground-loads, ground-reactions, level-
landing, tail-down-condition, one-wheel-load, braked-roll.

Query 1: "Compute landing-ground-loads gear reactions for a 60000 kg
transport: level-landing at limit load factor 2.5 with CG 8 m aft of the nose
gear" (id w30-landing-ground-loads-1).
Query 2: "Check the tail-down-condition and one-wheel-load reactions and the
braked-roll deceleration of the main gear" (id w30-landing-ground-loads-2).
intent: "structures; landing and ground handling reaction loads".

## Description/tag guidance

Description opens "Use when you must compute the ground loads on an aircraft
structure for the certification landing and ground-handling conditions:" and
lists the outputs in the Claim. First tag: landing-ground-loads. Additional
tags: ground-reactions, level-landing, tail-down-condition, one-wheel-load,
braked-roll. No generic single words. 50-150 words, <=1000 chars, no em dash,
no "classified".

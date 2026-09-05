# Wave-40 leaf spec: balanced-field-length (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/balanced-field-length/
- Pack: performance. Closest siblings: takeoff-performance (its logic
  module computes stall speed, lift-off speed and the all-engine ground
  roll distance S_g = 1.44 W^2 / (g rho S Cl_max (T - mu W)); its SKILL
  body limits the claim to the all-engine field-length estimate: no V1
  decision speed, no engine-failure segments, no 35-ft air distance),
  oei-climb-gradient (computes the OEI climb gradient in percent and
  rate of climb from excess thrust over drag and compares against the
  FAR-25.121 minima; it converts gradient to a clearance verdict, it
  does NOT integrate any distance), accelerate-stop-distance and
  engine-failure-takeoff-flight-test and takeoff-distance-determination
  (all in flight-test-operations: flight-test data-reduction leaves,
  not design estimates), vehicle-design/conceptual/constraint-analysis
  (the inverse sizing constraint: given a required takeoff distance it
  returns the required T/W). Whole-tree greps at prep: "V1", "balanced
  field", "accelerate-go", "accelerate-stop" = 0 hits in skills/
  flight-mechanics/. GENUINE FM gap (fresh probe): the tree routes the
  balanced-field-length question to takeoff-performance, which cannot
  compute a V1 decision or an engine-out field length.
- Standards id: far-25 (reference-only). Ledger Standard: far-25.
- Family: flight-mechanics

## Claim

Compute the balanced field length of a multi-engine transport with a
V1 decision-speed balance: accelerate all engines from rest to the V1
decision speed, then compare the accelerate-stop distance (brake to a
full stop after a reaction time) with the accelerate-go distance
(continue on the remaining engines, rotate and climb over the 35-ft
obstacle on the OEI gradient), and find the balanced V1 where the two
distances are equal. Produces the all-engine and OEI ground-roll
accelerations, the braking deceleration, the accelerate-stop and
accelerate-go distance curves, the balanced V1, and the balanced field
length that gate the runway-length and engine-out certification
assessment. Does NOT do: stall speed, lift-off speed or the all-engine
ground roll from wing loading (takeoff-performance); OEI climb
gradient computation or FAR-25.121 minima comparison
(oei-climb-gradient); flight-test distance determination from measured
data (flight-test-operations accelerate-stop-distance and related);
T/W or W/S sizing from a required field length
(vehicle-design/conceptual/constraint-analysis).

## Model (implement exactly)

Functions (pure stdlib; SI: newtons, metres, seconds, m/s^2; module
constant G0 = 9.80665):
- oei_thrust(thrust_all_n, engine_count) -> float
  T_OEI = T_all * (engine_count - 1) / engine_count; ValueError if
  thrust_all_n <= 0 or engine_count < 2 (an OEI case needs at least two
  engines).
- ground_acceleration(thrust_n, weight_n, mu_roll, g0=G0) -> float
  a = g0 * (T - mu * W) / W, the constant ground-roll acceleration with
  rolling friction opposing the thrust (mirrors the takeoff-performance
  net-force convention, no aerodynamic drag or lift relief in the
  ground roll). ValueError if weight_n <= 0, thrust_n <= 0, mu_roll
  outside [0, 1), or thrust_n <= mu_roll * weight_n (cannot
  accelerate).
- braking_deceleration(mu_brake, g0=G0) -> float magnitude
  a_brake = g0 * mu_brake; ValueError if mu_brake outside (0, 1).
- accelerate_distance(v_from_ms, v_to_ms, accel_m_s2) -> float
  s = (v_to^2 - v_from^2) / (2 a); ValueError if v_from_ms < 0, v_to_ms
  <= v_from_ms (the segment must accelerate) or accel_m_s2 <= 0.
- stop_distance(v_ms, decel_m_s2) -> float
  s = v^2 / (2 decel); ValueError if v_ms < 0 or decel_m_s2 <= 0.
- accelerate_stop_distance(v1_ms, thrust_all_n, weight_n, mu_roll,
  mu_brake, reaction_time_s, g0=G0) -> float
  ASD = s_all(0 to V1) + V1 * t_reaction + stop_distance(V1);
  reaction_time_s default 1.0 (module constant REACTION_TIME_S = 1.0,
  the standard pilot recognition plus brake application allowance,
  paraphrased); ValueError if reaction_time_s < 0.
- accelerate_go_distance(v1_ms, thrust_all_n, engine_count, weight_n,
  mu_roll, v_lof_ms, oei_climb_gradient, obstacle_height_m=35_FT,
  rotation_time_s=ROTATION_TIME_S, g0=G0) -> float
  AGD = s_all(0 to V1) + s_oei(V1 to V_LOF) + V_LOF * t_rotation +
  s_air, with s_air = obstacle_height_m / oei_climb_gradient (small-
  angle climb over the obstacle on the OEI gradient) and module
  constants OBSTACLE_HEIGHT_M = 10.668 (35 ft, the FAR-25.113 obstacle
  height, paraphrased) and ROTATION_TIME_S = 1.0. ValueErrors: engine
  count, gradient <= 0, v_lof_ms <= v1_ms (a V1 at or beyond lift-off
  is not a balanced decision), v1_ms < 0.
- balanced_v1(thrust_all_n, engine_count, weight_n, mu_roll, mu_brake,
  v_lof_ms, oei_climb_gradient, reaction_time_s=REACTION_TIME_S,
  obstacle_height_m=OBSTACLE_HEIGHT_M, rotation_time_s=ROTATION_TIME_S,
  g0=G0) -> float
  solves ASD(V1) = AGD(V1) exactly as the positive root of the
  quadratic A V1^2 + B V1 + C = 0 with
  A = 1/(2 a_brake) + 1/(2 a_oei),
  B = reaction_time_s,
  C = -(V_LOF^2/(2 a_oei) + V_LOF * rotation_time_s +
  obstacle_height_m / gradient),
  V1 = (-B + sqrt(B^2 - 4 A C)) / (2 A); the positive root exists and
  is unique because A > 0 and C < 0 (the discriminant exceeds B^2).
  ValueError if the root falls outside [0, V_LOF] (no balanced decision
  in the physical range; disclose by the caller).
- balanced_field_length(v1_ms, thrust_all_n, engine_count, weight_n,
  mu_roll, mu_brake, v_lof_ms, oei_climb_gradient,
  reaction_time_s=REACTION_TIME_S, obstacle_height_m=OBSTACLE_HEIGHT_M,
  rotation_time_s=ROTATION_TIME_S, g0=G0) -> float
  the balanced field length, equal to ASD(V1) = AGD(V1) at the balanced
  speed; implement as ASD(V1) and assert the caller passes the balanced
  V1 (the identity ASD == AGD at balance is tested in the contract
  test).
Module constants: G0 = 9.80665, REACTION_TIME_S = 1.0,
ROTATION_TIME_S = 1.0, OBSTACLE_HEIGHT_M = 10.668.

Identity to test: ASD(0) = 0; AGD is strictly decreasing in V1 and ASD
strictly increasing in V1 over the bracket (verified by evaluation at
V1 = 0 and V1 = V_LOF); at the balanced V1, ASD == AGD to machine
precision; balanced field length >= both ASD(V1) and AGD(V1) at any
other V1; a higher OEI climb gradient shortens AGD and lowers the
balanced V1; stronger brakes shorten ASD and raise the balanced V1.

## Worked example

Twin-engine transport, W = 600000 N, total installed thrust 150000 N,
V_LOF = 80 m/s, mu_roll = 0.03, mu_brake = 0.45, OEI climb gradient
0.024 (2.4 percent, the FAR-25.121 second-segment twin minimum,
paraphrased), 35-ft obstacle, 1 s reaction and 1 s rotation:
- oei_thrust = 75000 N.
- a_all = 2.15746 m/s^2, a_oei = 0.931632 m/s^2,
  a_brake = 4.41299 m/s^2.
- s_air = 10.668 / 0.024 = 444.5 m.
- quadratic A = 0.649995, B = 1.0, C = -3959.33, discriminant
  10295.2.
- V1_balanced = 77.2815 m/s (0.966 of V_LOF).
- ASD(V1) = AGD(V1) = balanced field length = 2138.10 m.
- Bracket sanity: ASD(0) = 0 < AGD(0) = 3959.33; ASD(V_LOF) = 2288.36
  > AGD(V_LOF) = 2007.72, so the balanced root is unique inside the
  bracket.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w40spec/anchors_bfl.py (prep-verified by stdlib
math).

## Validation list (contract test must include)

- oei_thrust(150000, 2) = 75000; oei_thrust(150000, 3) = 100000;
  oei_thrust(150000, 4) = 112500; ValueError at engine_count 1 and at
  thrust 0.
- ground_acceleration on the worked example = 2.15746 within 1e-4;
  ValueError at mu_roll 1.0, thrust below mu*W.
- braking_deceleration(0.45) = 4.41299 within 1e-4; ValueError at
  mu_brake 0 and 1.
- accelerate_distance: (0 to 80, 2.157463) = 1483.28 m (check by
  running); ValueError at v_to < v_from.
- stop_distance(77.2815, 4.41299) = 676.75 m within 0.05 (check by
  running); ValueError at negative speed.
- accelerate_stop_distance at V1 = 77.2815 = 2138.10 within 0.1.
- accelerate_go_distance at V1 = 77.2815 = 2138.10 within 0.1 (the
  balance identity).
- balanced_v1 on the worked example = 77.2815 within 0.01; the root is
  inside [0, V_LOF].
- balanced_field_length on the worked example = 2138.10 within 0.1.
- Monotonicity: ASD(0) < ASD(40) < ASD(80); AGD(0) > AGD(40) >
  AGD(80).
- Sensitivity: raising the gradient to 0.03 lowers balanced V1 and the
  balanced length; raising mu_brake to 0.55 raises balanced V1 and
  lowers the balanced length (assert direction).
- ValueErrors: engine_count 1, gradient 0 or negative, v_lof <= v1,
  mu_roll outside [0,1), non-positive weight/thrust, negative reaction
  time.
- Determinism; repeated calls return identical values.

## Corpus fragment (eval/hit1-wave40-balanced-field-length.yaml)

Query 1 (copy verbatim):
  "compute the balanced-field-length of the twin with the v1-decision-speed balance between the accelerate-stop-distance and the accelerate-go-distance over the 35-foot obstacle"
  intent: "flight-mechanics; balanced field length with V1 decision speed"
  expected_skill: "flight-mechanics/performance/balanced-field-length"
Query 2 (copy verbatim):
  "run the accelerate-go-distance and the accelerate-stop-distance balance to find the balanced V1 and the engine-out field length for the runway certification case"
  intent: "flight-mechanics; accelerate-go versus accelerate-stop distance balance"
  expected_skill: "flight-mechanics/performance/balanced-field-length"
Task ids: w40-balanced-field-length-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the balanced field
length and V1 decision speed of a multi-engine transport:" and include
the outputs in the Claim. First tag: balanced-field-length. Additional
tags ONLY: v1-decision-speed, accelerate-go-distance,
accelerate-stop-distance, engine-out-field-length. NEVER single generic
words (takeoff, field, length, distance, runway, engine, speed,
climb). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): stall-speed, lift-off-speed,
wing-loading, ground-roll-distance (takeoff-performance); oei-climb-
gradient, second-segment, approach-climb, landing-climb, rate-of-climb
(oei-climb-gradient); test-point, data-reduction, flight-test
(flight-test-operations); required-thrust-to-weight, constraint
(vehicle-design/conceptual/constraint-analysis).

# Wave-28 leaf spec: vmc-determination (flight-test-operations, envelope pack)

- Path: skills/flight-test-operations/envelope/vmc-determination/
- Pack: envelope (existing siblings: v-speeds, envelope-expansion,
  load-factor-envelope, stall-characteristics-testing, spin-testing,
  high-angle-of-attack-testing, icing-flight-test, flight-loads-survey,
  structural-coupling-test)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: flight-test-operations

## Claim

Predict and check the minimum control speed Vmc of a multi-engine
airplane in the spirit of the FAR/CS 25.149 minimum-control-speed
method: identify the critical engine from the engine-out yawing-moment
geometry, build the asymmetric yawing moment (operating-engine thrust
at the failed-engine lateral arm plus the failed-engine windmilling
drag contribution), compute the rudder deflection required to balance
it at each airspeed, solve for the authority-limited speed where the
required deflection reaches the rudder limit, evaluate the rudder
pedal-force criterion at that speed with the boost factor, apply the
stall-protection guard against the reference stall speed, and produce
the predicted Vmc, the governing-limit label (rudder authority, pedal
force, or stall guard) and the flight-test go verdict. Produces the
critical-engine label, the asymmetric moment model, the predicted Vmc
in m/s and knots, the governing limit, and the verdicts that gate the
engine-inoperative flight test.

Does NOT do: compute the one-engine-inoperative climb gradient or
second-segment clearance (flight-mechanics oei-climb-gradient owns the
climb performance); derive the general V-speed set Vref/V2/Vr
(flight-test-operations v-speeds); size the rudder area from the yaw
moment requirement (vehicle-design control-surface-sizing); compute
elevator hinge moments or stick force (flight-mechanics
control-surface-effectiveness); plan spin or stall tests
(stall-characteristics-testing, spin-testing).

## Model (implement exactly)

Module constants:
- RHO_SL = 1.225, G0 = 9.80665.
- F_LIM_N = 667.0 (150 lbf pedal-force limit expressed in newtons,
  from the FAR/CS 25.149 test condition, paraphrased not copied).
- STALL_GUARD = 1.05 (default stall-protection guard factor applied to
  the reference stall speed; an engineering check value).
- D2R = 0.017453292519943295.

Inputs:
- engines (list of dicts, one per engine: {thrust_N, y_m} where y_m is
  the lateral distance from the airplane CG to the engine centerline;
  sign matters: engines on the right have positive y),
- failed_engine_index (int, index of the failed engine in engines; the
  leaf confirms it is the critical engine or picks the critical one),
- windmilling_drag_area_m2 (float, S_f*Cd of the failed engine at
  speed; 0.0 allowed),
- vertical_tail_area_m2 (S_v), tail_arm_m (l_v, CG to fin aerodynamic
  center),
- rudder_effectiveness_per_rad (C_Lv_delta_r, effective fin lift slope
  per rudder deflection, includes the rudder-to-fin area ratio),
- rudder_deflection_max_deg (delta_r_max),
- rudder_area_m2 (S_r), rudder_chord_m (c_r),
- hinge_moment_coefficient_per_rad (C_h_delta_r, negative for a
  restoring hinge; magnitude used),
- pedal_arm_m (x, effective pedal-to-hinge linkage arm),
- boost_factor (float in (0, 1]; 1.0 manual, smaller values for
  power-boosted rudder: felt_pedal_force = hinge_moment *
  boost_factor / pedal_arm_m),
- v_s1g (float, reference stall speed m/s),
- pedal_force_limit_N (float, default F_LIM_N),
- stall_guard (float, default STALL_GUARD).

Functions:
- critical_engine_index(engines) -> int: engine with the largest
  |thrust*y| product (largest adverse yawing moment when failed);
  ties resolved to the lower index. ValueError on empty engines or any
  thrust_N <= 0.
- asymmetric_yaw_moment_Nm(V, engines, failed_index,
  windmilling_drag_area_m2) -> float:
  T_op = sum(thrust of the engines that are NOT failed) (the
  operating engines at maximum available takeoff thrust; for a twin
  one engine); y_fail = y of the failed engine; N_asym =
  T_op*y_fail + 0.5*RHO_SL*V^2*windmilling_drag_area_m2*y_fail.
  (The operating-engine thrust acts at the failed engine arm about the
  CG in the adverse direction for the failed-engine case; for engines
  on the same side as the failed one, sign handled by y_fail sign.
  Implement with y_fail magnitude and the adverse sign convention that
  the required rudder deflection opposes it.)
- rudder_deflection_required_rad(N_asym, V, inputs) -> float:
  q = 0.5*RHO_SL*V^2; delta = N_asym / (q * S_v * l_v *
  rudder_effectiveness_per_rad).
- authority_limited_speed(inputs) -> float:
  solve q* such that rudder_deflection_required equals
  delta_r_max (rad): q* = (T_op*y_fail) / (S_v*l_v*
  rudder_effectiveness_per_rad*delta_r_max_rad -
  windmilling_drag_area_m2*y_fail). Return V = sqrt(2*q*/RHO_SL).
  If the denominator <= 0, return None (never authority limited).
  ValueError if T_op*y_fail <= 0.
- pedal_force_at_speed_N(V, inputs) -> float:
  delta_req = rudder_deflection_required_rad(...) capped at
  delta_r_max_rad for the force evaluation at speeds below the
  authority limit; F = q*S_r*c_r*|C_h_delta_r|*min(delta_req,
  delta_r_max_rad)*boost_factor/pedal_arm_m.
- vmc_predict(inputs) -> dict:
  compute critical engine, T_op*y_fail, the authority-limited speed
  V_auth, the pedal-force-limited speed V_force from the quadratic
  F(V) = pedal_force_limit_N with delta at the limit (solve
  q_F*S_r*c_r*|C_h_delta_r|*delta_r_max_rad*boost_factor/pedal_arm_m =
  F_lim -> q_F = F_lim*pedal_arm_m/(S_r*c_r*|C_h_delta_r|*
  delta_r_max_rad*boost_factor); V_force = sqrt(2*q_F/RHO_SL));
  vmc = max(V_auth (or 0 if None), V_force);
  stall_guard_speed = stall_guard*v_s1g;
  governing = "rudder-authority" if V_auth >= V_force else
  "pedal-force"; if vmc < stall_guard_speed: governing =
  "stall-guard" and vmc_final = stall_guard_speed? NO: report vmc as
  the control limit and set guard_verdict
  "stall-guard-governs" when vmc < stall_guard_speed (the flight test
  must demonstrate above the guard; keep vmc unchanged, flag the
  verdict). Return {critical_engine, asymmetric_moment_at_vmc,
  vmc_m_s, vmc_kt (vmc*1.94384), v_auth_m_s, v_force_m_s,
  stall_guard_speed_m_s, governing, force_at_vmc_N, force_ok (bool),
  guard_verdict (str: "stall-guard-governs" or "stall-guard-ok"),
  flight_test_go (bool: force_ok AND guard ok AND vmc > 0)}.
ValueError on: engines empty, any thrust_N <= 0, v_s1g <= 0,
S_v <= 0, l_v <= 0, rudder_effectiveness_per_rad <= 0,
rudder_deflection_max_deg <= 0 or > 60, S_r <= 0, c_r <= 0,
pedal_arm_m <= 0, boost_factor <= 0 or > 1,
windmilling_drag_area_m2 < 0.

## Worked example

Twin jet: engines = [{thrust_N: 65000, y_m: 8.0}, {thrust_N: 65000,
y_m: -8.0}], failed_engine_index 0 (right engine fails; y_fail =
+8.0). S_v = 25.0, l_v = 16.0, rudder_effectiveness_per_rad = 0.8,
delta_r_max = 30 deg (0.52360 rad), S_r = 8.5, c_r = 1.3,
C_h_delta_r = -0.045, pedal_arm_m = 0.35, boost_factor = 0.15
(power-boosted), v_s1g = 66.0, windmilling_drag_area_m2 = 0.0
(neglected in the worked case).

- critical_engine_index = 0 (tie, lower index). Assert.
- T_op*y_fail = 65000*8.0 = 520000 N m.
- V_auth = sqrt(2*q*/RHO_SL), q* = 520000/(25*16*0.8*0.52360) =
  520000/167.552 = 3103.5 Pa -> V_auth = sqrt(2*3103.5/1.225) =
  sqrt(5067.0) = 71.18 m/s. Assert within 0.05.
- V_force: q_F = 667.0*0.35/(8.5*1.3*0.045*0.52360*0.15) =
  233.45/0.039045 = 5979.0? Compute denominator: 8.5*1.3 = 11.05;
  *0.045 = 0.49725; *0.52360 = 0.26036; *0.15 = 0.039054. q_F =
  233.45/0.039054 = 5977.6 Pa -> V_force = sqrt(2*5977.6/1.225) =
  sqrt(9759.4) = 98.79 m/s. The pedal-force limit binds at 98.8 m/s.
- vmc = max(71.18, 98.79) = 98.79 m/s; governing = "pedal-force".
- force_at_vmc_N = pedal force at V = 98.79: delta_req =
  520000/(q*25*16*0.8) with q = 5977.6: delta = 520000/(5977.6*320) =
  520000/1912832 = 0.2718 rad (below max) -> F =
  5977.6*8.5*1.3*0.045*0.2718*0.15/0.35 = 5977.6*11.05*0.045 =
  2972.1? compute step: q*S_r*c_r = 5977.6*11.05 = 66052;
  *0.045 = 2972.3; *0.2718 = 807.9; *0.15/0.35 = 346.2 N. Assert
  force_at_vmc within 2 N of 346.2 and force_ok True (<= 667).
- guard: stall_guard_speed = 1.05*66 = 69.3 m/s <= vmc -> 
  guard_verdict "stall-guard-ok".
- flight_test_go True. vmc_kt = 98.79*1.94384 = 192.0 kt. Assert
  within 0.2.
- Manual-rudder case (boost_factor = 1.0): force at V_auth 71.18:
  delta at limit = 0.5236 -> F = 3103.5*11.05*0.045*0.5236/0.35 =
  3103.5*11.05 = 34294; *0.045 = 1543.2; *0.5236 = 808.0; /0.35 =
  2308.6 N > 667 -> force_ok False; V_force with boost 1.0: q_F =
  233.45/0.26036 = 896.6 -> V_force = 38.26 m/s < V_auth -> vmc =
  V_auth 71.18, governing "rudder-authority", but force_ok False ->
  flight_test_go False (verdict reflects the 150 lbf criterion cannot
  be met without boost). Assert.
- Windmilling variant: windmilling_drag_area_m2 = 1.5 -> check the
  module runs and V_auth increases (denominator reduced):
  q* = 520000/(167.552 - 1.5*8.0) = 520000/155.552 = 3343.0 ->
  V_auth = sqrt(2*3343.0/1.225) = 73.87 m/s (assert within 0.1 and
  above the no-windmilling 71.18).
- ValueErrors on thrust 0, S_v 0, boost_factor 1.5, delta_r_max 90,
  v_s1g 0, empty engines.
Keep at least 20 test methods: critical engine tie and asymmetric case
(3-engine with an outboard), asymmetric moment values, deflection
required at two speeds, V_auth closed form, V_force closed form, vmc
and governing label, force values and ok flags, stall guard verdicts,
knots conversion, manual-rudder fail case, windmilling shift,
ValueErrors.

## Corpus tasks (ids w28-vmc-determination-1/2)

Distinctive tokens: minimum control speed, Vmc determination, critical
engine, rudder pedal force, asymmetric yawing moment, engine
inoperative flight test, 150 lbf pedal limit. Avoid: OEI climb
gradient, second segment, approach climb (flight-mechanics
oei-climb-gradient); Vref, V2, Vr speeds (v-speeds); rudder area
sizing, control power (vehicle-design control-surface-sizing); elevator
hinge moment, stick force (control-surface-effectiveness).

1. "predict the minimum control speed Vmc for the twin after the
   critical engine failure: balance the asymmetric yawing moment
   against the rudder authority and check the pedal force limit"
2. "determine whether the engine inoperative flight test can clear the
   Vmc demonstration: compute the authority limited and pedal force
   limited speeds and the stall speed guard"

## SKILL body notes

Pair with v-speeds (Vmc sits beside the V-speed set), oei-climb-gradient
(the engine-out performance sibling) and control-surface-sizing (the
rudder sizing sibling). State the model simplifications: first-order
yaw balance without sideslip coupling, sea-level density for the
dynamic pressure, operating engines at maximum takeoff thrust. FAR/CS
25.149 referenced by name and paraphrase only, no verbatim text.

# Wave-33 leaf spec: rotorcraft-blade-element-hover-performance (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-blade-element-hover-performance/
- Pack: performance. Rotorcraft siblings: rotorcraft-hover-performance
  (momentum-theory POWER leaf: disk area, induced velocity, ideal power,
  profile power, total power, power_from_figure_of_merit, figure_of_merit,
  disk_loading, hover_performance - takes thrust as input, momentum only),
  rotorcraft-hover-ground-effect, rotorcraft-forward-flight-performance,
  rotorcraft-vertical-climb-performance, rotorcraft-tail-rotor-sizing,
  rotorcraft-blade-flapping-dynamics (Lock no./coning/flap freq only),
  rotorcraft-autorotative-descent.
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the hovering rotor thrust coefficient C_T, inflow ratio lambda,
and torque coefficient C_Q (induced plus profile split) from a
blade-element integral over the pitch schedule, recover the collective
pitch required to hover at a target C_T / disk loading (with the Betz
tip-loss factor B), and return the rotor torque Q = C_Q rho A Vtip^2 R
and figure of merit from coefficients. This is the pitch-to-coefficients
chain (theta0 -> C_T/C_Q -> torque/FM) that no sibling owns: the hover
leaf takes thrust as input and is momentum-only (no C_T, C_Q, theta0,
lift-curve slope, twist, tip-loss factor anywhere in its logic module);
blade-flapping uses theta0 only as an input to coning, never to thrust
or torque.

Does NOT do: design-point momentum hover power / induced velocity with
thrust input (rotorcraft-hover-performance owns the FM ratio quantity at
the design point; this leaf's FM-from-coefficients is the SAME ratio
computed from the coefficient polar - the cross-leaf identity must hold
at B = 1); forward-flight power and inflow (rotorcraft-forward-flight-
performance); vertical climb (rotorcraft-vertical-climb-performance);
tail rotor anti-torque sizing (rotorcraft-tail-rotor-sizing); blade
flapping/coning/Lock number (rotorcraft-blade-flapping-dynamics);
autorotative descent (rotorcraft-autorotative-descent).

## Model (implement exactly)

Module constants:
- RHO_SL = 1.225 (kg/m3).
- G = 9.80665 (m/s2).
- A_LIFT_DEFAULT = 5.73 (1/rad).
- PI = math.pi.

Conventions: rotor radius R (m), disk area A = pi R^2, tip speed
Vtip = Omega R (m/s), solidity sigma, blade drag coefficient Cd0,
thrust T (N), inflow ratio lambda = v_i / Vtip.

Functions (pure stdlib):

- thrust_coefficient(collective_rad, solidity, lift_slope, lambda,
  tip_loss) -> C_T = (sigma a / 2) (theta0 B^3 / 3 - lambda B^2 / 2).
  B in (0, 1]; ValueErrors on non-positive solidity/lift_slope, B <= 0
  or B > 1, theta0 < 0, lambda < 0.
- inflow_ratio_from_ct(c_t) -> lambda = sqrt(c_t / 2) (uniform momentum
  hover closure). ValueError on c_t < 0.
- collective_for_thrust_coefficient(c_t, solidity, lift_slope, tip_loss)
  -> theta0 = (3 / B^3) (2 C_T / (sigma a) + lambda B^2 / 2) with
  lambda = sqrt(c_t / 2). Closed-form hover pitch for a target
  coefficient. ValueErrors as above; B in (0,1].
- torque_coefficient(c_t, inflow_ratio, solidity, drag_coefficient) ->
  C_Q = lambda C_T + sigma Cd0 / 8 (induced plus profile). ValueErrors
  on non-positive solidity/drag coefficient, c_t < 0.
- rotor_torque(c_q, rho, area, tip_speed, radius) -> Q =
  C_Q rho A Vtip^2 R. ValueErrors on non-positive inputs.
- rotor_power_from_torque(c_q, rho, area, tip_speed, radius) ->
  P = Q Omega = C_Q rho A Vtip^3. (Same inputs.)
- figure_of_merit_from_coefficients(c_t, c_q) -> FM = C_T^1.5 /
  (sqrt(2) C_Q). ValueErrors on c_t <= 0 or c_q <= 0.
- hover_blade_element_summary(thrust_N, radius_m, rho, solidity,
  lift_slope, drag_coefficient, tip_speed, tip_loss, collective_rad) ->
  dict {thrust_coefficient, inflow_ratio, torque_coefficient_induced,
  torque_coefficient_profile, torque_coefficient_total, rotor_torque_Nm,
  rotor_power_W, figure_of_merit}. Uses the worked-example ordering:
  C_T from thrust, lambda closure, C_Q split, torque/power, FM.
- collective_pitch_polar(collectives_rad, ...) -> list of dicts (one per
  collective) with the SAME keys plus the collective; closes lambda by
  fixed-point lambda = sqrt(C_T/2) (iterate to 1e-10, max 200 iters).
  ValueErrors propagate.

The blade-element hover identity to test at B = 1: with sigma, a, Cd0
matching a momentum hover leaf rotor, total power from torque must equal
P_ideal + P_profile of the momentum model to float tolerance, and FM
from coefficients must equal FM from the momentum power ratio.

## Worked example

Reference rotor (identical to the cross-check hover-leaf example):
R = 5.0 m, m = 2200 kg (T = m g), rho = 1.225 kg/m3, sigma = 0.08,
Cd0 = 0.012, Vtip = 220 m/s, a = 5.73 /rad.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- C_T = T / (rho A Vtip^2) about 0.00463.
- inflow_ratio_from_ct -> lambda about 0.0481.
- collective_for_thrust_coefficient at B = 1: theta0 about 0.1328 rad,
  7.6 deg (published hover collectives 5-10 deg).
- torque_coefficient split: induced lambda*C_T about 2.23e-4, profile
  sigma Cd0/8 = 1.20e-4 exactly, total about 3.43e-4.
- rotor_torque Q about 7986 N m; rotor_power about 351383 W, which must
  equal the momentum hover P_ideal + P_profile (about 228448 + 122935 =
  351383 W) to float tolerance.
- figure_of_merit_from_coefficients about 0.650, equal to the momentum
  FM ratio.
- Betz tip loss B = 0.97 raises the required collective by about 6%:
  theta0 about 0.1409 rad (8.1 deg).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive mass/radius/rho/solidity/lift slope/drag
  coefficient/tip speed; tip_loss <= 0 or > 1; collective < 0;
  c_t < 0; c_q <= 0.
- inflow closure: inflow_ratio_from_ct of the worked C_T is about
  0.0481 (hand compute sqrt(C_T/2)).
- collective identity: feeding the recovered theta0 back through
  thrust_coefficient returns the target C_T to 1e-9 (round trip).
- torque split: induced + profile equals total to 1e-12; profile term
  equals sigma*Cd0/8 exactly.
- Cross-leaf identity at B = 1: power from torque equals the momentum
  P_ideal + P_profile from the reference rotor within 1e-6 relative;
  FM from coefficients equals the momentum FM within 1e-9.
- Tip-loss monotonicity: B = 0.97 requires a higher collective than
  B = 1.0; higher B gives higher C_T at fixed collective.
- Figure of merit bounds: FM in (0, 1) for the worked case; ideal
  limit check FM <= 1.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave33-rotorcraft-blade-element-hover-performance.yaml)

Query 1 (copy verbatim):
  "estimate the blade-element hover thrust coefficient and the required collective pitch of a hovering rotor from the rotor solidity, the lift curve slope and the tip loss factor"
  intent: "flight-mechanics; blade-element hover C_T and required collective from solidity, lift slope, tip loss"
  expected_skill: "flight-mechanics/performance/rotorcraft-blade-element-hover-performance"
Query 2 (copy verbatim):
  "compute the torque coefficient induced plus profile split and the rotor shaft torque from the pitch schedule coefficients of a hovering helicopter rotor"
  intent: "flight-mechanics; hover torque coefficient C_Q induced-profile split and rotor torque from pitch coefficients"
  expected_skill: "flight-mechanics/performance/rotorcraft-blade-element-hover-performance"
Task ids: w33-rotorcraft-blade-element-hover-performance-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine the blade-element
hover performance of a helicopter main rotor:" and include the outputs
in the Claim. First tag: rotorcraft-blade-element-hover-performance.
Additional tags ONLY: blade-element-theory, thrust-coefficient,
torque-coefficient, collective-pitch, tip-loss-factor, hover-figure-of-
merit. NEVER single generic words (blade, element, hover, thrust,
torque, pitch, rotor, performance). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): induced velocity, ideal power,
profile power alone as outputs (momentum hover leaf owns the power
quantities; this leaf's profile/induced appear only inside C_Q split),
momentum theory, disk loading as a standalone sizing quantity
(rotorcraft-hover-performance), coning, Lock number, flap frequency
(blade-flapping), forward flight, Glauert, parasite power
(forward-flight leaf), tail rotor, anti-torque (tail-rotor-sizing),
climb, autorotation, descent. The words "thrust coefficient", "torque
coefficient", "collective", "tip loss", "blade element" are this leaf's
own.

Tags: [rotorcraft-blade-element-hover-performance, blade-element-theory,
thrust-coefficient, torque-coefficient, collective-pitch,
tip-loss-factor, hover-figure-of-merit]

Sibling-citation lines for Related leaves:
flight-mechanics/performance/rotorcraft-hover-performance (the
momentum-theory power leaf; the B = 1 cross-leaf identity ties the two
models),
flight-mechanics/performance/rotorcraft-blade-flapping-dynamics (blade
dynamics sibling that also consumes theta0),
flight-mechanics/performance/rotorcraft-tail-rotor-sizing.

Ledger Standard: far-29.

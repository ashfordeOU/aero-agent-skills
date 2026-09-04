# Wave-31 leaf spec: rotorcraft-tail-rotor-sizing (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-tail-rotor-sizing/
- Pack: performance. Rotorcraft siblings: rotorcraft-hover-performance (main
  rotor hover power OGE), rotorcraft-forward-flight-performance (main rotor
  forward flight power), rotorcraft-vertical-climb-performance,
  rotorcraft-hover-ground-effect (this wave). No leaf anywhere in the library
  computes the anti-torque requirement or sizes a tail rotor: this leaf is the
  rotor-torque / anti-torque member of the rotorcraft subdomain.
- Standards ids: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Size the tail rotor (anti-torque rotor) of a single-main-rotor rotorcraft
from the main rotor torque balance: the main rotor shaft torque from the main
rotor power and the rotor speed, the tail rotor thrust required to balance the
main rotor torque about the tail arm, the tail rotor disk area and radius for
a chosen maximum disk loading, the tail rotor ideal induced velocity and ideal
power from momentum theory, and the tail rotor total power estimate with the
induced-power factor and a tail-rotor profile power. Produces the main rotor
torque, the anti-torque thrust, the tail rotor radius, disk loading, induced
power, profile power, and total power that gate a rotorcraft anti-torque sizing
check.

Does NOT do: main rotor hover power required from weight and geometry
(rotorcraft-hover-performance owns the main-rotor OGE power; the main rotor
power here is an INPUT to the torque balance); forward-flight power breakdown
(rotorcraft-forward-flight-performance); vertical climb (rotorcraft-vertical-
climb-performance); ground effect (rotorcraft-hover-ground-effect); blade
element tail-rotor section loads or detailed tail-rotor dynamics (momentum
theory only); fin/vertical surface aerodynamic anti-torque contributions
(this leaf sizes the rotor only; the fin contribution is an input offset if
any). The tail rotor thrust is assumed perpendicular to the tail arm; the tail
rotor must also provide yaw control margin, modeled here as an input margin
factor on the required thrust.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- RHO_SL = 1.225 (kg/m3).
- K_DEFAULT = 1.15 (induced power factor).
- SIGMA_TR_DEFAULT = 0.10 (tail rotor solidity default for the profile power
  estimate).
- CD_TR_DEFAULT = 0.012 (tail rotor blade drag coefficient default).
- PI = math.pi.

Functions (pure stdlib):
- main_rotor_torque(power_w, omega_rad_s) -> float: Q = power / omega.
  ValueError if power_w < 0 or omega_rad_s <= 0.
- tail_rotor_thrust(torque_nm, tail_arm_m, margin_factor=1.0) -> float:
  T_tr = margin_factor * torque / tail_arm. ValueError if torque < 0,
  tail_arm <= 0, margin_factor <= 0.
- tail_rotor_area(thrust, max_disk_loading) -> float: A = thrust /
  max_disk_loading. ValueError if thrust < 0 or max_disk_loading <= 0.
- tail_rotor_radius(area) -> float: R = sqrt(area / PI). ValueError if
  area <= 0.
- tail_rotor_disk_loading(thrust, area) -> float: DL = thrust / area.
  ValueError if area <= 0 or thrust < 0.
- tail_rotor_induced_velocity(thrust, area, rho=RHO_SL) -> float:
  v_i = sqrt(thrust / (2 * rho * area)). ValueErrors on non-positive inputs.
- tail_rotor_ideal_power(thrust, induced_velocity) -> float:
  P_ideal = thrust * induced_velocity. ValueError if thrust < 0 or
  induced_velocity < 0.
- tail_rotor_profile_power(rho, area, solidity=SIGMA_TR_DEFAULT,
  drag_coefficient=CD_TR_DEFAULT, tip_speed=200.0) -> float:
  P_profile = (1/8) * rho * solidity * drag_coefficient * area * tip_speed**3.
  ValueError if any of rho, area, solidity, drag_coefficient, tip_speed <= 0.
- tail_rotor_total_power(ideal_power, profile_power, k=K_DEFAULT) -> float:
  P_total = k * ideal_power + profile_power. ValueError if ideal_power < 0 or
  profile_power < 0 or k <= 0.
- tail_rotor_sizing(main_power_w, omega_rad_s, tail_arm_m,
  max_disk_loading=300.0, rho=RHO_SL, margin_factor=1.0,
  solidity=SIGMA_TR_DEFAULT, drag_coefficient=CD_TR_DEFAULT,
  tip_speed=200.0, k=K_DEFAULT) -> dict: convenience chain returning
  {main_rotor_torque_nm, tail_rotor_thrust_N, tail_rotor_area_m2,
  tail_rotor_radius_m, tail_rotor_disk_loading_Pa, tail_rotor_induced_velocity,
  tail_rotor_ideal_power_W, tail_rotor_profile_power_W,
  tail_rotor_total_power_W}. ValueErrors propagate.

## Worked example

Main rotor power 400 000 W at rotor speed 27 rad/s, tail arm 8.0 m,
max disk loading 300 Pa, rho = 1.225 kg/m3, margin factor 1.0, tail rotor
solidity 0.10, Cd 0.012, tail tip speed 200 m/s, k = 1.15.

Deterministic anchors (run your module, take the printed values as the assert
targets to 4 significant figures, then CHECK the magnitude bounds):
- main rotor torque in 13 000-17 000 Nm (about 14 815).
- tail rotor thrust in 1500-2200 N (about 1852).
- tail rotor area in 5.0-7.5 m2 (about 6.17).
- tail rotor radius in 1.2-1.6 m (about 1.40).
- tail rotor disk loading at 300 Pa ceiling (about 300).
- tail rotor induced velocity in 9-13 m/s (about 11.1).
- tail rotor ideal power in 15 000-26 000 W (about 20 500).
- tail rotor total power in 22 000-36 000 W (about 25 700, dominated by the
  induced power factor and the profile estimate).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: power < 0, omega <= 0, tail_arm <= 0, margin_factor <= 0,
  max_disk_loading <= 0, rho <= 0, solidity <= 0, Cd <= 0, tip_speed <= 0,
  area <= 0, k <= 0.
- Round-trip: tail_rotor_thrust(Q, arm) times arm equals Q (margin 1.0).
- Tail rotor radius from area gives back the area within tolerance
  (PI * radius**2).
- Disk loading stays at or below the ceiling when sized with the ceiling.
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-rotorcraft-tail-rotor-sizing.yaml)

Query 1 (copy verbatim):
  "size the anti-torque-rotor of a single-main-rotor helicopter: tail-rotor-thrust from the main-rotor-torque divided by the tail arm and tail rotor radius from a maximum disk loading"
  intent: "flight-mechanics; rotorcraft tail-rotor anti-torque sizing"
  expected_skill: "flight-mechanics/performance/rotorcraft-tail-rotor-sizing"
Query 2 (copy verbatim):
  "compute the tail-rotor-power of a rotorcraft from the main-rotor-torque balance, induced power factor and tail rotor profile power"
  intent: "flight-mechanics; rotorcraft anti-torque tail rotor power estimate"
  expected_skill: "flight-mechanics/performance/rotorcraft-tail-rotor-sizing"
Task ids: w31-rotorcraft-tail-rotor-sizing-1 and -2.

Forbidden tokens that belong to siblings: do NOT use hover power, figure of
merit, disk loading of the MAIN rotor, forward flight, climb, ground effect,
autorotation, tail rotor dynamics or blade element terms. The main rotor power
is an input: never claim to compute it from weight and radius.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the anti-torque tail rotor of a
single-main-rotor rotorcraft from the main rotor torque balance:" and include
the outputs listed in the Claim. First tag: rotorcraft-tail-rotor-sizing.
Additional tags only: anti-torque-rotor, tail-rotor-thrust, main-rotor-torque,
tail-rotor-power. NEVER single generic words (rotor, torque, power, sizing,
helicopter). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

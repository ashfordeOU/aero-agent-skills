# Wave-30 leaf spec: rotorcraft-hover-performance (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-hover-performance/
- Pack: performance (fixed-wing siblings: breguet-endurance, breguet-range,
  climb-performance, descent-performance, energy-height, glide-performance,
  landing-performance, oei-climb-gradient, specific-range, speed-stability,
  takeoff-performance, thrust-required, turn-performance, wind-effects,
  windshear-analysis). This is the FIRST rotorcraft leaf in the library; the
  flight-mechanics fixed-wing topics are saturated per the wave-29 receipt, but
  rotorcraft vertical-flight performance is an uncovered domain (no sibling
  computes rotor induced power, hover power, or figure of merit).
- Standards ids: far-29 (reference-only; NEW id added to standards-map.yaml at
  wave-30 prep). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the hovering performance of a rotorcraft rotor with momentum theory:
ideal induced velocity through the rotor disk, ideal hover power, profile
power from blade solidity and tip speed, the total hover power through an
induced-power factor and through the figure of merit, the figure of merit
itself, and the disk loading. Produces the induced velocity, ideal power,
profile power, total power, figure of merit, and disk loading that gate a
hover performance check at a chosen density altitude.

Does NOT do: analyze fixed-wing climb or cruise performance (climb-performance,
breguet leaves own those); compute forward-flight rotor power breakdown
(sibling rotorcraft-forward-flight-performance owns induced, profile, and
parasite power versus speed); model blade-element section loads or airfoil
polars (this leaf stays at momentum-theory level); size blades or the rotor
planform (no rotor sizing leaf exists; geometry is an input here); simulate
transient vertical dynamics or autorotation (out of scope, flight-mechanics
point-mass and six-dof simulation leaves own time integration). Momentum
theory only: uniform inflow, no ground effect (ground-effect lives in
aerodynamics), no recirculation.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- RHO_SL = 1.225 (kg/m3, sea-level density used only as a default).
- K_DEFAULT = 1.15 (induced power factor).
- PI = math.pi.

Functions (pure stdlib):
- disk_area(radius) -> float: A = PI * radius**2. ValueError if radius <= 0.
- induced_velocity(thrust, area, rho=RHO_SL) -> float:
  v_i = sqrt(thrust / (2 * rho * area)). ValueError on thrust <= 0,
  area <= 0, rho <= 0.
- ideal_power(thrust, induced_velocity) -> float: P_ideal = thrust * v_i.
  ValueError if thrust < 0 or induced_velocity < 0.
- profile_power(rho, area, solidity, drag_coefficient, tip_speed) -> float:
  P_profile = (1/8) * rho * solidity * drag_coefficient * area * tip_speed**3
  (average section drag model). ValueError if any of rho, area, solidity,
  drag_coefficient, tip_speed <= 0.
- total_power(ideal_power, induced_velocity, thrust, profile_power,
  k=K_DEFAULT) -> float: P_total = k * thrust * induced_velocity + profile_power
  (induced power factor model). ValueError if ideal_power < 0 or
  profile_power < 0 or k <= 0. (thrust*v_i is used so the k factor applies to
  the ideal induced power.)
- power_from_figure_of_merit(ideal_power, figure_of_merit) -> float:
  P = ideal_power / figure_of_merit. ValueError if figure_of_merit <= 0 or
  figure_of_merit > 1.0 or ideal_power < 0.
- figure_of_merit(ideal_power, total_power) -> float:
  FM = ideal_power / total_power. ValueError if total_power <= 0 or
  ideal_power < 0 or ideal_power > total_power (a >1 FM is non-physical;
  allow equality).
- disk_loading(thrust, area) -> float: DL = thrust / area. ValueError if
  area <= 0 or thrust < 0.
- hover_performance(weight_kg, radius, rho=RHO_SL, solidity=0.08,
  drag_coefficient=0.012, tip_speed=220.0, k=K_DEFAULT) -> dict: convenience
  chain returning {thrust_N, area_m2, induced_velocity, ideal_power_W,
  profile_power_W, total_power_W, figure_of_merit, disk_loading_Pa}.
  thrust = weight_kg * G0. ValueErrors propagate.

## Worked example

Rotor radius R = 5.0 m, helicopter mass 2200 kg (weight 21574.63 N),
rho = 1.225 kg/m3, solidity 0.08, Cd0 = 0.012, tip speed 220 m/s, k = 1.15.

Deterministic anchors (run your module, take the printed values as the
assert targets to 4 significant figures, then CHECK the magnitude bounds):
- induced velocity in 9.5-11.5 m/s (hand estimate ~10.6 m/s).
- ideal power in 200 000-260 000 W.
- profile power in 100 000-150 000 W.
- total power in 350 000-430 000 W.
- figure of merit in 0.50-0.70 (typical rotor FOM range with losses).
- disk loading in 260-290 Pa.
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: radius <= 0 (disk_area, induced_velocity via area), thrust <= 0,
  rho <= 0, solidity <= 0, Cd0 <= 0, tip_speed <= 0, figure_of_merit <= 0 or
  > 1 (power_from_figure_of_merit), k <= 0, ideal_power < 0.
- figure_of_merit rejects ideal_power > total_power (returns ValueError).
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Idempotence helper checks on the convenience dict keys.

## Corpus fragment (eval/hit1-wave30-rotorcraft-hover-performance.yaml)

Two tasks; mirror fixed-wing FM performance phrasing but carry rotorcraft
tokens. Forbidden tokens that belong to siblings: do NOT use time-to-climb,
range, endurance, takeoff, landing, thrust-required, wind triangle, gliding,
energy-height. DO NOT use tokens owned by rotorcraft-forward-flight
(speed sweep, forward-flight power).

Query 1 tokens: rotorcraft hover performance, induced velocity, figure of
merit, momentum theory (task id w30-rotorcraft-hover-performance-1).
Query 2 tokens: helicopter hover power, profile power, disk loading, solidity
(task id w30-rotorcraft-hover-performance-2).
intent values: "flight-mechanics; rotorcraft hover momentum-theory power
analysis".

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the hovering performance of a
rotorcraft rotor with momentum theory:" and include the outputs listed in the
Claim. First tag: rotorcraft-hover-performance. Additional tags only:
rotor-induced-velocity, hover-power, figure-of-merit, rotor-disk-loading,
rotor-solidity. NEVER single generic words (power, performance, helicopter).
50-150 words, <=1000 chars, no em dash, no "classified", action verb present.

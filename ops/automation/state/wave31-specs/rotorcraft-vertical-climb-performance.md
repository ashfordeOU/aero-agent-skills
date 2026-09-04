# Wave-31 leaf spec: rotorcraft-vertical-climb-performance (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-vertical-climb-performance/
- Pack: performance. Rotorcraft siblings in the pack: rotorcraft-hover-performance
  (hover momentum theory, wave-30), rotorcraft-forward-flight-performance (Glauert
  inflow power breakdown, wave-30), rotorcraft-hover-ground-effect and
  rotorcraft-tail-rotor-sizing (this wave, sibling specs). Fixed-wing performance
  siblings (climb-performance, breguet-range, etc.) are saturated and are NOT in
  this leaf's claim.
- Standards ids: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the vertical climb performance of a rotorcraft with axial momentum
theory: the climb-induced velocity from the hover induced velocity and the
climb rate, the induced power with an induced-power factor, the total rotor
power required in a vertical climb (induced plus profile), and the maximum
vertical rate of climb for an available shaft power. Produces the induced
velocity in climb, the climb power required, the climb power margin, and the
maximum vertical rate of climb that gate a rotorcraft climb check at a chosen
density altitude.

Does NOT do: hover power at zero climb rate (rotorcraft-hover-performance owns
hover induced velocity, profile power, figure of merit); forward-flight power
versus airspeed (rotorcraft-forward-flight-performance owns the Glauert
speed-dependent breakdown); fixed-wing climb or ceilings from excess thrust
(climb-performance owns the airplane case; the rotorcraft climb here is the
vertical-axis momentum-theory case only); OEI climb gradient
(oei-climb-gradient owns the one-engine-inoperative gradient); time-to-climb
integration or mission segment modeling (not in this leaf). Momentum theory
only: uniform inflow, no ground effect, no vortex-ring-state modeling in
descent (this leaf is climb-only; Vc >= 0).

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- RHO_SL = 1.225 (kg/m3, sea-level default density).
- K_DEFAULT = 1.15 (induced power factor, consistent with the hover sibling).
- PI = math.pi.

Functions (pure stdlib):
- disk_area(radius) -> float: A = PI * radius**2. ValueError if radius <= 0.
- hover_induced_velocity(thrust, area, rho=RHO_SL) -> float:
  v_h = sqrt(thrust / (2 * rho * area)). ValueError on thrust <= 0,
  area <= 0, rho <= 0.
- climb_induced_velocity(thrust, area, climb_rate, rho=RHO_SL) -> float:
  v_i = -climb_rate/2 + sqrt((climb_rate/2)**2 + v_h**2), where v_h is the
  hover induced velocity. Momentum-theory result for vertical climb; the
  induced velocity decreases as climb rate grows. ValueError if climb_rate < 0
  (descent is out of scope), thrust <= 0, area <= 0, rho <= 0.
- profile_power(rho, area, solidity, drag_coefficient, tip_speed) -> float:
  P_profile = (1/8) * rho * solidity * drag_coefficient * area * tip_speed**3
  (average section drag model, identical form to the hover sibling).
  ValueError if any of rho, area, solidity, drag_coefficient, tip_speed <= 0.
- climb_power(thrust, climb_rate, induced_velocity, profile_power,
  k=K_DEFAULT) -> float: P = k * thrust * (climb_rate + induced_velocity) +
  profile_power. ValueError if climb_rate < 0, induced_velocity < 0,
  profile_power < 0, k <= 0.
- climb_power_margin(available_power, required_power) -> float:
  margin = available_power - required_power. ValueError if
  available_power < 0 or required_power < 0.
- max_vertical_climb_rate(thrust, area, rho, available_power, profile_power,
  k=K_DEFAULT) -> float: solve climb_power(Vc) = available_power for Vc by
  bisection on [0, 200] m/s (climb power is strictly increasing in Vc because
  d(climb_power)/dVc = k*T*(1 + d(v_i)/dVc) > 0 with d(v_i)/dVc in (-1/2, 0)).
  ValueError if available_power < hover power at Vc=0
  (k*thrust*v_h + profile_power): a rotorcraft cannot climb vertically when
  the available power cannot even sustain hover. Return the rate in m/s.
  If the equation does not cross (available power exceeds the power at the
  upper bracket), return the upper bracket value and let the caller treat it
  as an excess-power case (do not raise).
- vertical_climb_performance(weight_kg, radius, rho=RHO_SL,
  solidity=0.08, drag_coefficient=0.012, tip_speed=220.0, k=K_DEFAULT,
  climb_rate=5.0, available_power=None) -> dict: convenience chain returning
  {thrust_N, area_m2, hover_induced_velocity, climb_induced_velocity,
  profile_power_W, climb_power_W, climb_power_margin_W (None when
  available_power is None), max_vertical_climb_rate}. thrust =
  weight_kg * G0. ValueErrors propagate.

## Worked example

Rotor radius R = 5.0 m, helicopter mass 2200 kg (weight 21574.63 N),
rho = 1.225 kg/m3, solidity 0.08, Cd0 = 0.012, tip speed 220 m/s, k = 1.15,
climb rate 5 m/s, available power 600 kW.

Deterministic anchors (run your module, take the printed values as the assert
targets to 4 significant figures, then CHECK the magnitude bounds):
- hover induced velocity in 9.5-11.5 m/s (about 10.59).
- climb induced velocity at 5 m/s climb in 7.5-9.5 m/s (about 8.38).
- profile power in 100 000-150 000 W (about 122 935).
- climb power required at 5 m/s in 420 000-490 000 W (about 454 900).
- max vertical climb rate at 600 kW available in 11-16 m/s (about 13.4).
- hover total power (Vc=0) in 350 000-430 000 W (about 385 650).
If a value falls OUTSIDE its bound, your implementation has a bug: find it
before writing tests. In the SKILL.md worked example show your module's real
outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: radius <= 0, thrust <= 0, rho <= 0, solidity <= 0, Cd0 <= 0,
  tip_speed <= 0, climb_rate < 0 (climb_induced_velocity and climb_power),
  profile_power < 0, k <= 0.
- max_vertical_climb_rate raises ValueError when available_power is below the
  hover power (e.g. available_power = 300 kW with the worked-example rotor).
- max_vertical_climb_rate returns the bracket upper bound for huge available
  power (e.g. 5 MW returns 200.0).
- Monotonicity: climb_induced_velocity decreases as climb_rate increases
  (v_i at 2 m/s > v_i at 10 m/s).
- Determinism: no RNG anywhere. Run-to-run identical floats.
- Round-trip: climb_power(0, v_h, ...) equals the hover total power
  k*T*v_h + P_profile to float tolerance.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave31-rotorcraft-vertical-climb-performance.yaml)

Query 1 (copy verbatim):
  "compute the vertical climb performance of a helicopter with momentum theory: climb induced velocity and climb power required for a 5 m/s vertical climb at sea level"
  intent: "flight-mechanics; rotorcraft vertical-climb momentum-theory power analysis"
  expected_skill: "flight-mechanics/performance/rotorcraft-vertical-climb-performance"
Query 2 (copy verbatim):
  "determine the maximum vertical rate of climb of a rotorcraft from the available shaft power minus the hover power, using axial momentum theory"
  intent: "flight-mechanics; rotorcraft max vertical rate of climb from excess power"
  expected_skill: "flight-mechanics/performance/rotorcraft-vertical-climb-performance"
Task ids: w31-rotorcraft-vertical-climb-performance-1 and -2.

Forbidden tokens that belong to siblings: do NOT use time-to-climb,
rate-of-climb (fixed-wing excess-thrust sense), service ceiling, climb
gradient, forward-flight, speed sweep, autorotation, descent, induced-power
factor phrase that implies hover power only, figure of merit, disk loading,
OGE hover ceiling.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the vertical climb
performance of a rotorcraft rotor with axial momentum theory:" and include
the outputs listed in the Claim. First tag: rotorcraft-vertical-climb-performance.
Additional tags only: rotorcraft-climb-power, climb-induced-velocity,
vertical-rate-of-climb, vertical-climb-momentum-theory. NEVER single generic
words (power, performance, climb, helicopter, rotor). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

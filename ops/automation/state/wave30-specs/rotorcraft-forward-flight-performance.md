# Wave-30 leaf spec: rotorcraft-forward-flight-performance (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-forward-flight-performance/
- Pack: performance (see rotorcraft-hover-performance spec for the pack
  context; this leaf is the forward-flight companion to that hover leaf).
- Standards ids: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the forward-flight power required of a rotorcraft rotor with
momentum-theory inflow: the Glauert induced velocity at a given flight speed,
the induced power, the parasite power from the equivalent flat-plate drag
area, the profile power (rotor blade drag), and the total power, then find the
speed of minimum total power (best endurance speed) and the speed that
minimizes power per unit speed (best range speed proxy) over a speed sweep.
Produces the forward induced velocity, the three power components, the total
power curve, and the two characteristic speeds that gate a rotorcraft cruise
performance assessment.

Does NOT do: hover power (rotorcraft-hover-performance owns hover induced
velocity, figure of merit, disk loading); fixed-wing cruise/endurance/range
methods (breguet-range, breguet-endurance, cruise-performance-flight-test own
fixed-wing cruise); estimate parasite drag of a configuration (drag-polars
parasite-drag and the vehicle-design drag leaves own drag buildup; here the
equivalent flat-plate area f is an input); model autorotation or vertical
climb (out of scope). Uniform inflow momentum theory: no reverse-flow region,
no blade-element section polars, no compressibility.

## Model (implement exactly)

Module constants:
- G0 = 9.80665, RHO_SL = 1.225, PI = math.pi.
- K_DEFAULT = 1.15 (induced power factor), matching the hover leaf.
- CD0_DEFAULT = 0.012 (average rotor blade drag coefficient).
- MAX_ITER = 60, TOL = 1e-9 (Glauert fixed-point tolerance).

Functions (pure stdlib):
- hover_induced_velocity(thrust, area, rho=RHO_SL) -> float:
  v_h = sqrt(thrust / (2 * rho * area)). ValueErrors as hover leaf.
- glauert_induced_velocity(thrust, area, rho, speed, max_iter=MAX_ITER,
  tol=TOL) -> float: fixed-point iteration of the Glauert inflow equation
  v = thrust / (2 * rho * area * sqrt(speed**2 + v**2)); start v0 = v_h, stop
  when |v_new - v| < tol, raise RuntimeError if max_iter exceeded (loop the
  clean way: while i < max_iter). ValueError if speed < 0 (speed == 0 allowed,
  returns the hover value by the same fixed point or directly v_h), thrust<=0,
  area<=0, rho<=0.
- induced_power(thrust, induced_velocity) -> float: P_i = thrust * v.
- parasite_power(rho, speed, flat_plate_area) -> float:
  P_par = 0.5 * rho * speed**3 * flat_plate_area. ValueError on speed < 0,
  flat_plate_area < 0, rho <= 0.
- profile_power(rho, area, solidity, drag_coefficient=CD0_DEFAULT,
  tip_speed) -> float: same (1/8) formula as the hover leaf. ValueErrors.
- total_power(thrust, induced_velocity, profile_power, parasite_power,
  k=K_DEFAULT) -> float: P_total = k * thrust * v + profile_power +
  parasite_power.
- power_sweep(thrust, area, rho, flat_plate_area, solidity,
  drag_coefficient=CD0_DEFAULT, tip_speed=220.0, speeds=None, k=K_DEFAULT)
  -> list of (speed, total_power): speeds default = 5.0 m/s to 100.0 m/s in
  1.0 m/s steps (range(5, 101) as floats); returns pairs.
- best_endurance_speed(...) -> speed of minimum total power over the sweep
  (argmin; if two speeds tie to 1e-9 take the lower).
- best_range_speed(...) -> speed minimizing total_power / speed over the
  sweep (skip speed 0; argmin of P/V). Returns (speed, power_per_speed).
  Both accept the same kwargs as power_sweep and internally call it.

## Worked example

Same rotor as the hover leaf: R = 5.0 m (A = 78.5398 m2), m = 2200 kg
(T = 21574.63 N), rho = 1.225, solidity 0.08, Cd0 0.012, tip speed 220 m/s,
f = 2.2 m2, V = 60 m/s.

Deterministic anchors (module outputs are the assert targets to 4 s.f., then
check bounds):
- Glauert induced velocity at 60 m/s in 1.5-2.3 m/s (hand estimate ~1.87 m/s,
  far below the hover value ~10.6 m/s).
- induced power at 60 m/s in 35 000-50 000 W.
- parasite power at 60 m/s in 270 000-320 000 W.
- profile power 100 000-150 000 W (same as hover leaf).
- total power at 60 m/s in 420 000-500 000 W.
- best endurance speed in 25-45 m/s; best range speed in 50-90 m/s and
  strictly ABOVE the best endurance speed (physics check).
If a value is outside its bound, debug before writing tests. Show the real
module outputs in the SKILL.md worked example (a small table of the power
components at 60 m/s and the two characteristic speeds is ideal).

## Validation list (contract test must include)

- ValueError cases: speed < 0, thrust <= 0, area <= 0, rho <= 0, f < 0,
  solidity <= 0, Cd0 <= 0, tip_speed <= 0, k <= 0.
- glauert_induced_velocity with speed == 0 returns the hover value within
  1e-6 (identity).
- best_range_speed > best_endurance_speed on the worked rotor.
- Power monotonic sanity: at 20 m/s parasite power < at 80 m/s parasite power.
- RuntimeError path if a caller forces max_iter=2 on glauert (verify the
  failure mode exists; implement the loop to raise after max_iter).

## Corpus fragment (eval/hit1-wave30-rotorcraft-forward-flight-performance.yaml)

Forbidden tokens (siblings): hover-power, figure-of-merit, disk-loading,
induced-velocity at hover (owned by rotorcraft-hover-performance), cruise
range/endurance fuel fractions (breguet), rate-of-climb (climb-performance),
takeoff distance. Distinctive hyphenated tokens ONLY: rotorcraft-forward-flight,
glauert-inflow, parasite-power, equivalent-flat-plate-area, best-endurance-speed,
best-range-speed.

Query 1: "Estimate the power required for helicopter forward flight at 60 m/s
with a glauert-inflow induced power model and an equivalent-flat-plate-area
parasite drag of 2.2 m2" (id w30-rotorcraft-forward-flight-performance-1).
Query 2: "Find the best-endurance-speed and best-range-speed for a rotorcraft
power sweep with parasite-power and rotor profile drag" (id
w30-rotorcraft-forward-flight-performance-2).
intent: "flight-mechanics; rotorcraft forward-flight power analysis".

## Description/tag guidance

Description opens "Use when you must compute the forward-flight power required
of a rotorcraft rotor with momentum-theory inflow:" and lists the outputs from
the Claim. First tag: rotorcraft-forward-flight-performance. Additional tags:
glauert-inflow, parasite-power, best-endurance-speed, best-range-speed,
equivalent-flat-plate-area. No generic single words. 50-150 words, <=1000
chars, no em dash, no "classified".

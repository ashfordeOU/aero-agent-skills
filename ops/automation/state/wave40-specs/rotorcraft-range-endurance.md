# Wave-40 leaf spec: rotorcraft-range-endurance (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-range-endurance/
- Pack: performance. Closest siblings: breguet-endurance (fixed-wing
  Breguet loiter: fixed L/D, TSFC or PSFC branches; its body is explicit
  that the fixed-L/D Breguet form is a fixed-wing model), breguet-range
  (fixed-wing cruise Breguet with L/D), rotorcraft-hover-performance
  (hover power physics: induced velocity, ideal power, figure of merit;
  it computes POWER, not fuel closure), rotorcraft-forward-flight-
  performance (forward-flight power required curve and the best
  range/endurance SPEED selection from the curve; it does not close a
  fuel budget into distance or time). Whole-tree greps at prep:
  "hover endurance", "rotorcraft range", "fuel closure" = 0 hits in
  skills/flight-mechanics/. GENUINE FM gap (fresh probe): the tree can
  compute rotorcraft power and best speeds but no leaf turns fuel into
  hover time or cruise distance/time.
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Close the fuel budget of a rotorcraft into hover endurance and cruise
range and endurance: compute the hover power from the weight, rotor
disk area and figure of merit, integrate the fuel burn over the weight
decay to a closed-form hover endurance, and for cruise take an input
power-required curve (computed by the forward-flight sibling), scale
the power with the average weight, and produce the range and endurance
over the fuel load at a chosen speed together with the best-range and
best-endurance speeds from the curve. Produces the hover power and
endurance, the cruise range and endurance, the fuel-flow rates and the
best-speed selection that gate the rotorcraft mission fuel check. Does
NOT do: hover induced velocity, ideal power, profile power or figure
of merit from rotor geometry (rotorcraft-hover-performance); the
forward-flight power-required curve from blade-element or momentum
theory and its best-speed search over the physical curve
(rotorcraft-forward-flight-performance); fixed-wing Breguet range or
endurance with a fixed L/D (breguet-range, breguet-endurance).

## Model (implement exactly)

Functions (pure stdlib; SI: weight in N, power in W, rotor radius in
m, density kg/m^3, fuel in kg, time in s, distance in m; module
constant G0 = 9.80665, RHO_SL = 1.225):
- disk_area(radius) -> float pi * r^2; ValueError if radius <= 0.
- hover_power_constant(radius, rho=RHO_SL, figure_of_merit=0.75) ->
  float k_h = 1 / (FM * sqrt(2 * rho * A)); ValueError if radius <= 0,
  rho <= 0, figure_of_merit <= 0 or > 1.
- hover_power(weight_n, radius, rho=RHO_SL, figure_of_merit=0.75) ->
  float P = k_h * W^1.5 (the momentum-theory hover power with the
  figure of merit; mirrors rotorcraft-hover-performance's
  power_from_figure_of_merit convention); ValueErrors as above plus
  weight_n <= 0.
- hover_endurance(weight_initial_n, fuel_mass_kg, radius,
  rho=RHO_SL, figure_of_merit=0.75, c_specific=1.0e-7, g0=G0) -> float
  t = (2 / (g0 * c_specific * k_h)) * (1/sqrt(W1) - 1/sqrt(W0)) with
  W1 = W0 - g0 * fuel_mass (the exact integral of dW/dt = -g0 * c * P
  with P = k_h W^1.5; c_specific is the engine specific fuel
  consumption in kg/(s W), default 1.0e-7 ~ 0.36 kg/kWh, paraphrased);
  ValueError if fuel_mass_kg < 0 or W1 <= 0 (fuel mass must leave
  positive weight), weight_initial_n <= 0, c_specific <= 0.
- fuel_flow(weight_n, radius, rho=RHO_SL, figure_of_merit=0.75,
  c_specific=1.0e-7) -> float mdot = c_specific * P(weight) kg/s.
- specific_range(v_ms, power_w, c_specific=1.0e-7, g0=G0) -> float
  V / (g0 * c * P), metres of range per kg of fuel at the point;
  ValueError if v_ms <= 0, power_w <= 0 or c_specific <= 0.
- best_range_speed(power_curve) -> float v maximizing specific_range
  over the curve, where power_curve is a list of (v_ms, power_w) pairs
  (deterministic scan; ValueError if empty or any non-positive pair).
- best_endurance_speed(power_curve) -> float v minimizing power over
  the curve (deterministic scan; ValueErrors as above).
- cruise_range(v_ms, weight_initial_n, fuel_mass_kg, power_at_ref_w,
  weight_ref_n, c_specific=1.0e-7, g0=G0) -> float
  R = v * (W0 - W1) / (g0 * c * P_avg) with
  P_avg = power_at_ref_w * (W_avg / W_ref)^1.5 and W_avg = (W0 + W1)/2,
  the average-weight power-scaling method (induced-dominated rotor
  power scales as W^1.5; the average-weight approximation mirrors the
  climb-performance average-ROC house convention); ValueErrors if
  v_ms <= 0, fuel_mass_kg < 0, W1 <= 0, power_at_ref_w <= 0,
  weight_ref_n <= 0.
- cruise_endurance(v_ms, weight_initial_n, fuel_mass_kg,
  power_at_ref_w, weight_ref_n, c_specific=1.0e-7, g0=G0) -> float
  E = (W0 - W1) / (g0 * c * P_avg), same convention; ValueErrors as
  cruise_range.
Module constants: G0 = 9.80665, RHO_SL = 1.225, C_SPEC_DEFAULT =
1.0e-7, FM_DEFAULT = 0.75.

Identity to test: hover_endurance goes to 0 as fuel_mass goes to 0;
hover_endurance grows as fuel mass grows and as figure of merit grows;
fuel_flow equals c_specific * hover_power; specific_range is
monotone in V at fixed power; best_range_speed returns the argmax of
specific_range over the curve and best_endurance_speed the argmin of
power; cruise_range scales linearly with speed at fixed P_avg; adding
the weight-scaling (W_avg/W_ref)^1.5 to power is a strict reduction
below the reference weight (range longer than the no-scaling estimate).

## Worked example

Six-tonne class helicopter, W0 = 60000 N, fuel 1500 kg, rotor radius
8 m, rho 1.225, FM 0.75, c = 1.0e-7 kg/(s W):
- disk_area = 201.062 m^2.
- hover_power_constant k_h = 0.0600746, hover_power(W0) = 882912 W.
- fuel_flow at W0 = 0.0882912 kg/s.
- W1 = 45290.0 N; hover_endurance = 20927.3 s = 5.81 h.
- Power curve at W_ref = 60000 N (V m/s, P W): (40, 620000),
  (50, 560000), (60, 540000), (70, 555000), (80, 600000).
- best_range_speed = 80 m/s, best_endurance_speed = 60 m/s.
- cruise_range at 80 m/s with P_ref 600000 W = 2433442 m = 2433 km.
- cruise_endurance at 60 m/s with P_ref 540000 W = 33797.8 s = 9.39 h.
- specific_range at 60 m/s, 540000 W = 113.302 m per kg of fuel.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w40spec/anchors_rotor.py (prep-verified by stdlib
math).

## Validation list (contract test must include)

- disk_area(8.0) = 201.062 within 0.01; ValueError at radius 0.
- hover_power_constant(8.0) = 0.0600746 within 1e-5.
- hover_power(60000, 8.0) = 882912 within 10; ValueError at weight 0
  and at FM 0 or 1.5.
- fuel_flow(60000, 8.0) = 0.0882912 within 1e-5.
- hover_endurance(60000, 1500, 8.0) = 20927.3 within 1.0; with fuel 0
  returns 0.0; ValueError at fuel that zeroes the weight and at
  negative fuel.
- specific_range(60, 540000) = 113.302 within 0.01; ValueErrors at
  v 0 and P 0.
- best_range_speed over the worked curve = 80.0; best_endurance_speed
  = 60.0; ValueError on an empty curve.
- cruise_range(80, 60000, 1500, 600000, 60000) = 2433442 within 100;
  cruise_endurance(60, 60000, 1500, 540000, 60000) = 33797.8 within
  10.
- Scaling identity: cruise_range with W_ref equal to W0 and no weight
  decay returns the no-scaling value; range at a lower reference power
  is shorter.
- Determinism; repeated calls identical; monotone endurance with FM.

## Corpus fragment (eval/hit1-wave40-rotorcraft-range-endurance.yaml)

Query 1 (copy verbatim):
  "compute the rotorcraft-range-endurance hover endurance of the helicopter from the rotor disk area and figure of merit and the fuel mass with the weight-decay power integration"
  intent: "flight-mechanics; rotorcraft hover endurance fuel closure"
  expected_skill: "flight-mechanics/performance/rotorcraft-range-endurance"
Query 2 (copy verbatim):
  "close the rotorcraft cruise fuel budget into the cruise-range and cruise-endurance over the power-required curve with the average-weight power scaling and the best-range-speed pick"
  intent: "flight-mechanics; rotorcraft cruise range and endurance fuel closure"
  expected_skill: "flight-mechanics/performance/rotorcraft-range-endurance"
Task ids: w40-rotorcraft-range-endurance-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must close the rotorcraft fuel
budget into hover endurance and cruise range and endurance:" and
include the outputs in the Claim. First tag:
rotorcraft-range-endurance. Additional tags ONLY: hover-endurance,
cruise-endurance, power-required-fuel-closure, average-weight-power.
NEVER single generic words (range, endurance, fuel, hover, rotor,
power, weight, speed). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): breguet, lift-to-drag, tsfc,
psfc (breguet-range, breguet-endurance); induced-velocity, ideal-power,
profile-power, figure-of-merit-from-geometry, rotor-solidity
(rotorcraft-hover-performance); blade-element, momentum-theory,
power-required-curve-physics, best-range-speed-search-over-physics
(rotorcraft-forward-flight-performance).

---
name: rotorcraft-range-endurance
description: "Use when you must determine the rotorcraft fuel closure into hover endurance and cruise range and endurance: the hover power from the weight, the rotor disk area and the figure of merit, the exact weight-decay integration of the fuel burn into a closed-form hover endurance, and the cruise range and endurance at a chosen speed from an input power-required curve scaled with the average weight, together with the best-range and best-endurance speed picks. Produces the hover power and endurance, the cruise range and endurance, the fuel-flow rates, the specific range and the best-speed selection that gate the rotorcraft mission fuel check. Trigger: rotorcraft range endurance, hover endurance closure, cruise range closure, cruise endurance closure, rotorcraft fuel budget closure, specific range, best range speed, best endurance speed, average weight power scaling."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [rotorcraft-range-endurance, hover-endurance, cruise-endurance, power-required-fuel-closure, average-weight-power]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Range and Endurance (flight-mechanics/performance/rotorcraft-range-endurance)

Use when you must close the fuel budget of a rotorcraft into hover
endurance and cruise range and endurance. This leaf turns fuel into
time and distance: the hover power from the weight, the rotor disk
area and the figure of merit; the exact weight-decay integral that
turns the fuel mass into hover time; and, at a chosen cruise speed, the
range and endurance over the same fuel load from an input
power-required curve scaled with the average weight. It is the fuel
closure member of the rotorcraft performance pair: it pairs with
flight-mechanics/performance/rotorcraft-hover-performance (the rotor
power physics: induced velocity, ideal power and figure of merit at a
single weight, no fuel budget) and with flight-mechanics/performance/
rotorcraft-forward-flight-performance (the power-required curve and its
best-speed search, which this leaf consumes as its cruise power input).
The cruise power-required curve is an input here, not recomputed.

## Domain quick reference

All quantities are SI. The fuel burn rate follows the weight decay
dW/dt = -g0 * c * P, with g0 = 9.80665 m/s^2, c the specific fuel
consumption in kg/(s W), and P the power required at the current
weight.

- Disk area: A = PI * R^2, R the rotor radius in m.
- Hover power at a weight W (induced-dominated rotor, figure of merit
  FM as the hover efficiency input): P = k_h * W^1.5 with k_h = 1 /
  (FM * sqrt(2 * rho * A)), FM in (0, 1], default rho = 1.225 kg/m^3
  at sea level.
- Weight at fuel burnout: W1 = W0 - g0 * m_f, with W0 the takeoff
  weight and m_f the fuel mass in kg; the fuel load must leave W1 > 0.
- Hover endurance (exact integral of the weight decay): t = (2 / (g0 *
  c * k_h)) * (1/sqrt(W1) - 1/sqrt(W0)), seconds.
- Fuel flow at a weight: mdot = c * P(W), kg/s.
- Specific range at a cruise point: SR = V / (g0 * c * P), metres of
  range per kg of fuel.
- Best range speed over the curve: V maximizing SR; best endurance
  speed: V minimizing P. Deterministic scans over the (V, P) pairs.
- Cruise fuel closure with the average-weight power scaling: P_avg =
  P_ref * (W_avg / W_ref)^1.5 with W_avg = (W0 + W1) / 2, then R = V *
  (W0 - W1) / (g0 * c * P_avg) and E = (W0 - W1) / (g0 * c * P_avg).
  The W^1.5 power scaling reflects the induced-dominated rotor power;
  the average-weight approximation follows the house average-ROC
  convention of the climb-performance leaves.
- Default specific fuel consumption c = 1.0e-7 kg/(s W) (about 0.36
  kg/kWh); pass the engine value when known.
- FAR 29 frames the rotorcraft certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: takeoff weight W0 in N, fuel load m_f in
   kg, rotor radius R in m, density rho at the operating altitude,
   rotor figure of merit FM and specific fuel consumption c.
2. Get the rotor disk area with disk_area(radius).
3. Compute the hover power constant with hover_power_constant(radius,
   rho, figure_of_merit) and the hover power at the takeoff weight with
   hover_power(weight_n, radius, rho, figure_of_merit).
4. Close the hover endurance fuel budget with hover_endurance(
   weight_initial_n, fuel_mass_kg, radius, rho, figure_of_merit,
   c_specific): the weight-decay power integration into hover time.
5. Get the fuel flow at the operating weights with fuel_flow(weight_n,
   radius, rho, figure_of_merit, c_specific).
6. For cruise, take the power-required curve at the reference weight
   from the forward-flight sibling. Evaluate the specific range at a
   candidate speed with specific_range(v_ms, power_w), and pick the
   best range speed with best_range_speed(power_curve) and the best
   endurance speed with best_endurance_speed(power_curve) over the
   (V, P) pairs.
7. Close the cruise fuel budget at the chosen speed with
   cruise_range(v_ms, weight_initial_n, fuel_mass_kg, power_at_ref_w,
   weight_ref_n, c_specific) and cruise_endurance(v_ms, ...), which
   apply the average-weight power scaling to the reference power.
8. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_range_endurance.py.

## Worked example

Six-tonne class helicopter, W0 = 60000 N, fuel 1500 kg, rotor radius
8 m, sea level (rho = 1.225), FM 0.75, c = 1.0e-7 kg/(s W). Running
the module functions:

- disk_area(8.0) = 201.062 m^2.
- hover_power_constant(8.0) = 0.0600746 (SI).
- hover_power(60000, 8.0) = 882912 W (about 883 kW).
- fuel_flow(60000, 8.0) = 0.0882912 kg/s.
- W1 = 60000 - 9.80665 * 1500 = 45290.0 N; hover_endurance(60000,
  1500, 8.0) = 20927.3 s = 5.81 h.
- Power-required curve at the reference weight W_ref = 60000 N,
  (V m/s, P W): (40, 620000), (50, 560000), (60, 540000), (70, 555000),
  (80, 600000). best_range_speed = 80 m/s, best_endurance_speed =
  60 m/s.
- specific_range(60, 540000) = 113.302 m per kg of fuel.
- cruise_range(80, 60000, 1500, 600000, 60000) = 2433442 m = 2433 km.
- cruise_endurance(60, 60000, 1500, 540000, 60000) = 33797.8 s =
  9.39 h.

## Verification

- Confirm disk_area(8.0) = 201.062 m^2 (within 0.01) and that a zero
  or negative radius raises ValueError.
- Confirm hover_power_constant(8.0) = 0.0600746 (within 1e-5) and that
  non-positive density or a figure of merit outside (0, 1] raises
  ValueError.
- Confirm hover_power(60000, 8.0) = 882912 W (within 10), with
  ValueErrors at zero weight, at FM 0 and at FM 1.5.
- Confirm fuel_flow(60000, 8.0) = 0.0882912 kg/s (within 1e-5) and the
  identity fuel_flow = c * hover_power at any weight.
- Confirm hover_endurance(60000, 1500, 8.0) = 20927.3 s (within 1.0),
  returns exactly 0.0 s with zero fuel, grows with fuel mass and with
  figure of merit, and raises ValueError for fuel that zeroes the
  weight and for negative fuel.
- Confirm specific_range(60, 540000) = 113.302 m/kg (within 0.01),
  ValueErrors at zero speed and zero power, and monotone growth with
  speed at a fixed power.
- Confirm best_range_speed and best_endurance_speed over the worked
  curve return 80.0 and 60.0 m/s, reject an empty curve and any
  non-positive pair, and match the argmax of specific range and the
  argmin of power computed independently.
- Confirm cruise_range(80, 60000, 1500, 600000, 60000) = 2433442 m
  (within 100) and cruise_endurance(60, 60000, 1500, 540000, 60000) =
  33797.8 s (within 10). At a fixed cruise speed the reference power
  sits in the denominator, so a lower reference power closes a longer
  range (the fuel burns more slowly); across the worked curve the
  lower-power lower-speed point closes a shorter range than the
  best-range point, and the weight-scaling (W_avg/W_ref)^1.5 is a
  strict reduction below the reference weight, so the scaled range is
  longer than the no-scaling estimate.
- Confirm determinism: repeated runs return identical floats (no RNG,
  stdlib only).

## Pitfalls

- Feeding the hover-power figure of merit into a from-geometry rotor
  build: this leaf takes FM (and the disk area) as inputs and computes
  power and fuel closure only; the rotor power physics and geometry
  terms live in the hover-performance and forward-flight siblings.
- Treating the cruise power as constant over the whole fuel burn:
  induced-dominated rotor power decays with weight, so the closure
  must scale the reference power with (W_avg/W_ref)^1.5; using the
  takeoff power under-predicts the cruise range.
- Burning the fuel load below positive weight: the weight at burnout
  W1 = W0 - g0 * m_f must stay above zero, and the module raises
  ValueError when the fuel mass violates that.
- Confusing the two best-speed picks: best range speed maximizes the
  specific range (speed per fuel flow), best endurance speed minimizes
  the power; on the worked curve they sit at 80 m/s and 60 m/s.
- Mixing units: weight must be in N (mass in kg times g0), not in kgf,
  and the specific fuel consumption is in kg/(s W), not kg/(kW h);
  pass c = 1.0e-7 default only when the engine value is unknown.

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the rotor
  power physics at a single weight (induced velocity, ideal power,
  profile power, figure of merit) that this leaf consumes as its hover
  power input.
- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the power-required curve and its best-speed search over the physical
  curve, which this leaf takes as the cruise power input; the two
  leaves together gate a rotorcraft mission performance check.
- flight-mechanics/performance/breguet-range and
  flight-mechanics/performance/breguet-endurance: the fixed-wing
  cruise fuel-closure leaves with a fixed lift-to-drag factor; this
  leaf owns the rotorcraft fuel closure with average-weight power
  scaling instead.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  the rotorcraft vertical flight closure that consumes the same hover
  power law in climb checks.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/flight-mechanics/performance/rotorcraft-range-endurance/scripts/test_rotorcraft_range_endurance.py

The test covers the worked example against the spec anchors (disk area
201.062 m^2, hover power constant 0.0600746, hover power 882912 W,
fuel flow 0.0882912 kg/s, hover endurance 20927.3 s, cruise range
2433442 m, cruise endurance 33797.8 s, specific range 113.302 m/kg),
the zero-fuel and burnout bounds, the weight-scaling identities of the
cruise closure, the best-speed argmax and argmin identities over the
power-required curve, the fuel-flow equals c times hover power
identity, run-to-run determinism, absence of random or external
imports, and ValueError rejection of every non-physical input in the
verification list.

## Compliance

- Standards referenced, not reproduced: FAR 29 (rotorcraft
  airworthiness, certification context only). The fuel-closure
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

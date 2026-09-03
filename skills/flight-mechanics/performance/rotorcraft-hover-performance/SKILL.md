---
name: rotorcraft-hover-performance
description: "Use when you must compute the hovering performance of a rotorcraft rotor with momentum theory: the ideal induced velocity through the rotor disk, the ideal hover power, the profile power from blade solidity and tip speed, the total hover power through an induced-power factor or through the figure of merit, and the disk loading. Produces the induced velocity, ideal power, profile power, total power, figure of merit, and disk loading that gate a hover performance check at a chosen density altitude. Momentum theory only: uniform inflow, no ground effect. Trigger: rotorcraft hover performance, induced velocity, figure of merit, momentum theory, hover power, disk loading, blade solidity."
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
  tags: [rotorcraft-hover-performance, rotor-induced-velocity, hover-power, figure-of-merit, rotor-disk-loading, rotor-solidity]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Hover Performance (flight-mechanics/performance/rotorcraft-hover-performance)

Use when you must compute the hovering performance of a rotorcraft rotor
with momentum theory: the ideal induced velocity through the rotor disk,
the ideal hover power, the profile power from blade solidity and tip
speed, the total hover power through an induced-power factor or through
the figure of merit, and the disk loading. This is the first rotorcraft
vertical-flight member of the flight-mechanics performance pack: it
pairs with flight-mechanics/performance/rotorcraft-forward-flight-
performance for the speed-dependent power breakdown and with
aerodynamics/ground-effects/ground-effect for hover in ground effect.
Momentum theory only: uniform inflow, no ground effect, no
recirculation. Geometry (radius, solidity, blade drag coefficient, tip
speed) is an input; this leaf does not size the rotor.

## Domain quick reference

All quantities are SI. The rotor thrust equals the rotorcraft weight in
hover: T = m * g0, g0 = 9.80665 m/s^2.

- Disk area: A = PI * R^2.
- Ideal induced velocity (momentum theory, uniform inflow): v_i =
  sqrt(T / (2 * rho * A)).
- Ideal hover power: P_ideal = T * v_i.
- Profile power (average section drag model): P_profile = (1/8) * rho *
  sigma * Cd0 * A * Vtip^3, with sigma the rotor solidity, Cd0 the mean
  blade drag coefficient and Vtip the tip speed.
- Total hover power with the induced power factor k: P_total = k * T *
  v_i + P_profile, where k scales the ideal induced power for wake and
  tip losses (default k = 1.15).
- Total hover power from the figure of merit: P_total = P_ideal / FM,
  FM in (0, 1].
- Figure of merit: FM = P_ideal / P_total (real rotors sit near
  0.5-0.7 with losses).
- Disk loading: DL = T / A in Pa.
- Default density rho = 1.225 kg/m^3 is sea level; pass the density at
  the chosen density altitude to re-evaluate the hover check there.
- FAR 29 frames the rotorcraft certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: rotor radius R, rotorcraft mass m, density
   rho at the density altitude, solidity sigma, mean blade drag
   coefficient Cd0, tip speed Vtip and induced power factor k.
2. Get the disk area with disk_area(radius) and the thrust
   T = m * G0 (hover thrust equals weight).
3. Compute the ideal induced velocity with induced_velocity(thrust,
   area, rho).
4. Compute the ideal hover power with ideal_power(thrust, v_i).
5. Compute the profile power with profile_power(rho, area, solidity,
   drag_coefficient, tip_speed).
6. Combine with total_power(ideal_power, v_i, thrust, profile_power, k)
   or, if the rotor figure of merit is the input instead, with
   power_from_figure_of_merit(ideal_power, figure_of_merit).
7. Compute the figure of merit with figure_of_merit(ideal_power,
   total_power) and the disk loading with disk_loading(thrust, area).
8. For a single-call verdict run hover_performance(weight_kg, radius,
   rho, solidity, drag_coefficient, tip_speed, k), which returns the
   full dict and propagates every ValueError from the primitives.
9. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_hover_performance.py.

## Worked example

A helicopter at 2200 kg mass with a 5.0 m radius rotor at sea level:
rho = 1.225 kg/m^3, solidity 0.08, Cd0 = 0.012, tip speed 220 m/s,
k = 1.15. Running hover_performance(2200.0, 5.0, 1.225, 0.08, 0.012,
220.0, 1.15):

- Thrust: 2200 * 9.80665 = 21574.63 N.
- Disk area: PI * 5.0^2 = 78.54 m^2.
- Induced velocity: v_i = 10.59 m/s (hand estimate about 10.6 m/s,
  within the 9.5-11.5 m/s band).
- Ideal power: P_ideal = 228448 W (within 200000-260000 W).
- Profile power: P_profile = 122935 W (within 100000-150000 W).
- Total power: P_total = 1.15 * 21574.63 * 10.589 + 122935 = 385650 W
  (within 350000-430000 W).
- Figure of merit: FM = 228448 / 385650 = 0.592 (within 0.50-0.70, the
  typical rotor FOM band with losses).
- Disk loading: DL = 21574.63 / 78.54 = 274.7 Pa (within 260-290 Pa).

At a density altitude where rho drops to 1.06 kg/m^3 the same rotor
needs a higher induced velocity (about 11.4 m/s), so the hover check
must be re-run at the chosen density.

## Verification

- Confirm hover_performance(2200.0, 5.0) with sea-level defaults returns
  induced_velocity 10.59 m/s, ideal_power_W 228448, profile_power_W
  122935, total_power_W 385650, figure_of_merit 0.592 and
  disk_loading_Pa 274.7.
- Confirm the momentum-theory closed form: induced_velocity equals
  sqrt(T / (2 * rho * A)) and total power equals k * T * v_i +
  P_profile for the same inputs.
- Confirm the figure-of-merit round trip:
  power_from_figure_of_merit(ideal_power, FM) recovers the total power
  used to compute FM.
- Confirm every non-positive radius, thrust, area, density, solidity,
  drag coefficient, tip speed and induced power factor, every negative
  power, and every figure of merit outside (0, 1] raises ValueError,
  and that figure_of_merit rejects ideal_power > total_power.
- Confirm determinism: repeated runs return identical floats (no RNG,
  stdlib only).
- Run the contract test offline: python3
  scripts/test_rotorcraft_hover_performance.py (33 tests,
  deterministic).

## Related leaves

- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the sibling rotor leaf for the cruise power split (induced, profile
  and parasite power versus airspeed) that extends this hover model.
- aerodynamics/ground-effects/ground-effect: hover in ground effect,
  which this momentum-theory model deliberately excludes.
- flight-mechanics/performance/oei-climb-gradient: the one-engine-
  inoperative climb verdict for multi-engine rotorcraft, adjacent to
  the hover power check in a rotorcraft performance pass.
- flight-mechanics/performance/climb-performance and
  flight-mechanics/performance/glide-performance: fixed-wing vertical
  performance leaves; this leaf owns the rotorcraft hover case only.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_hover_performance.py

The test covers the worked example with the spec magnitude bounds
(induced velocity 9.5-11.5 m/s, ideal power 200000-260000 W, profile
power 100000-150000 W, total power 350000-430000 W, figure of merit
0.50-0.70, disk loading 260-290 Pa), the momentum-theory closed form,
the induced power factor model and its default constant, the cubic tip
speed scaling of profile power, the figure-of-merit round trip, exact
dict keys and primitive consistency of hover_performance, run-to-run
determinism, absence of random or external imports, and ValueError
rejection of every non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: FAR 29 (rotorcraft
  airworthiness, certification context only). The momentum-theory
  hover relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

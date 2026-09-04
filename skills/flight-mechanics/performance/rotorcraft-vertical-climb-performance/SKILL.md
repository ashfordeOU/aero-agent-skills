---
name: rotorcraft-vertical-climb-performance
description: "Use when you must compute the vertical climb performance of a rotorcraft rotor with axial momentum theory: the climb induced velocity from the hover induced velocity and the climb rate, the induced power through an induced power factor, the total rotor power required in a vertical climb as induced plus profile power, and the maximum vertical rate of climb for an available shaft power. Produces the induced velocity in climb, the climb power required, the climb power margin and the maximum vertical rate of climb that gate a rotorcraft climb check at a chosen density altitude. Momentum theory only: uniform inflow, no ground effect, climb only. Trigger: rotorcraft vertical climb performance, axial momentum theory, climb induced velocity, rotorcraft climb power, vertical rate of climb, available shaft power, climb power margin."
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
  tags: [rotorcraft-vertical-climb-performance, rotorcraft-climb-power, climb-induced-velocity, vertical-rate-of-climb, vertical-climb-momentum-theory]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Vertical Climb Performance (flight-mechanics/performance/rotorcraft-vertical-climb-performance)

Use when you must compute the vertical climb performance of a rotorcraft
rotor with axial momentum theory: the climb induced velocity falls below
the hover induced velocity as the climb rate grows, and the power needed
to climb is the induced power through the induced power factor k plus the
profile power. This leaf pairs with
flight-mechanics/performance/rotorcraft-hover-performance (the hover
state at zero climb rate, which owns the hover power terms) and with
flight-mechanics/performance/rotorcraft-forward-flight-performance (the
speed-dependent power split in level flight). Axial momentum theory only:
uniform inflow, no ground effect, vertical climb only with climb rates
zero or positive, and no wake distortion modeling in descending flight
(the model rejects negative climb rates).

## Domain quick reference

All quantities are SI. The rotor thrust equals the rotorcraft weight in
the climb check: T = m * g0, g0 = 9.80665 m/s^2. Default density
rho = 1.225 kg/m^3 is sea level; pass the density at the chosen density
altitude to re-run the climb check there.

- Disk area: A = PI * R^2.
- Hover induced velocity (momentum theory): v_h = sqrt(T / (2 * rho *
  A)).
- Climb induced velocity at vertical climb rate Vc: v_i = -Vc/2 +
  sqrt((Vc/2)^2 + v_h^2). The induced velocity decreases as the climb
  rate grows, and v_i < v_h for any positive Vc.
- Profile power (average section drag model): P_profile = (1/8) * rho *
  sigma * Cd0 * A * Vtip^3, with sigma the rotor solidity, Cd0 the mean
  blade drag coefficient and Vtip the tip speed.
- Total climb power: P = k * T * (Vc + v_i) + P_profile, where k is the
  induced power factor (default 1.15) applied to the climb induced power
  for wake and tip losses. At Vc = 0 this reduces to the hover total
  power k * T * v_h + P_profile.
- Climb power margin: margin = P_available - P_required.
- Maximum vertical rate of climb: solve P(Vc) = P_available for Vc.
  Climb power is strictly increasing in Vc because dP/dVc = k*T*(1 +
  d(v_i)/dVc) > 0 with d(v_i)/dVc in (-1/2, 0), so a bisection on [0,
  200] m/s finds the root. A vertical climb is impossible when the
  available power sits below the hover total power at Vc = 0; that case
  raises ValueError. When the available power exceeds the power required
  at the 200 m/s upper bracket, the bracket value is returned as an
  excess-power case.
- FAR 29 frames the rotorcraft certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: rotor radius R, rotorcraft mass m, density
   rho at the density altitude, solidity sigma, mean blade drag
   coefficient Cd0, tip speed Vtip, induced power factor k, the vertical
   climb rate Vc and the available shaft power.
2. Get the disk area with disk_area(radius) and the climb thrust
   T = m * G0 (thrust equals weight).
3. Compute the hover induced velocity with hover_induced_velocity(thrust,
   area, rho), the baseline for the climb inflow.
4. Compute the climb induced velocity with climb_induced_velocity(thrust,
   area, climb_rate, rho); verify it sits below the hover value.
5. Compute the profile power with profile_power(rho, area, solidity,
   drag_coefficient, tip_speed).
6. Combine with climb_power(thrust, climb_rate, induced_velocity,
   profile_power, k) for the total rotor power required in the climb.
7. Compare against the shaft power with climb_power_margin(available,
   required); a negative margin means the climb cannot be sustained.
8. For the climb limit, call max_vertical_climb_rate(thrust, area, rho,
   available_power, profile_power, k) to get the maximum vertical rate
   of climb from the excess shaft power.
9. For a single-call verdict run vertical_climb_performance(weight_kg,
   radius, rho, solidity, drag_coefficient, tip_speed, k, climb_rate,
   available_power), which returns the full dict and propagates every
   ValueError from the primitives.
10. Confirm the deterministic checks with the contract test
    scripts/test_rotorcraft_vertical_climb_performance.py.

## Worked example

A helicopter at 2200 kg mass with a 5.0 m radius rotor climbing
vertically at 5 m/s at sea level: rho = 1.225 kg/m^3, solidity 0.08,
Cd0 = 0.012, tip speed 220 m/s, k = 1.15, available power 600 kW.
Running vertical_climb_performance(2200.0, 5.0, 1.225, 0.08, 0.012,
220.0, 1.15, 5.0, 600000.0):

- Thrust: 2200 * 9.80665 = 21574.63 N.
- Disk area: PI * 5.0^2 = 78.54 m^2.
- Hover induced velocity: v_h = 10.59 m/s (within the 9.5-11.5 m/s
  band).
- Climb induced velocity at 5 m/s: v_i = 8.380 m/s (within 7.5-9.5 m/s,
  below the hover value as momentum theory requires).
- Profile power: P_profile = 122935 W (within 100000-150000 W).
- Climb power at 5 m/s: P = 1.15 * 21574.63 * (5 + 8.380) + 122935 =
  454900 W (within 420000-490000 W).
- Climb power margin at 600 kW: 600000 - 454900 = 145100 W.
- Maximum vertical rate of climb at 600 kW: 13.40 m/s (within 11-16
  m/s), found by bisection on the power balance.
- Hover total power (Vc = 0): k * T * v_h + P_profile = 385650 W
  (within 350000-430000 W); the 600 kW case clears it with room to
  climb.

At a density altitude where rho drops to 1.06 kg/m^3 the induced
velocities rise and the climb power check must be re-run at the chosen
density.

## Verification

- Confirm vertical_climb_performance(2200.0, 5.0, available_power =
  600000.0) with the sea-level defaults returns hover_induced_velocity
  10.59 m/s, climb_induced_velocity 8.380 m/s, profile_power_W 122935,
  climb_power_W 454900, climb_power_margin_W 145100 and
  max_vertical_climb_rate 13.40.
- Confirm the hover round trip: climb_power(thrust, 0.0, v_h,
  profile_power) equals k * T * v_h + P_profile, the hover total power.
- Confirm monotonicity: the climb induced velocity at 2 m/s exceeds the
  value at 10 m/s, and the climb power strictly increases with the climb
  rate.
- Confirm max_vertical_climb_rate raises ValueError when the available
  power sits below the hover total power (300 kW with this rotor), and
  returns the 200.0 m/s upper bracket when the available power exceeds
  the power required at 200 m/s (about 5.10 MW for this rotor, so 6 MW
  returns 200.0).
- Confirm every non-positive radius, thrust, area, density, solidity,
  drag coefficient, tip speed and induced power factor, and every
  negative climb rate, induced velocity, profile power and available or
  required power raises ValueError.
- Confirm determinism: repeated runs return identical floats (no RNG,
  stdlib only).
- Run the contract test offline: python3
  scripts/test_rotorcraft_vertical_climb_performance.py (35 tests,
  deterministic).

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the hover
  state at Vc = 0, which owns the hover induced velocity, hover power
  terms and disk loading context that seed this climb model.
- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the sibling rotor leaf for the speed-dependent power split in level
  flight, adjacent in the rotorcraft performance pass.
- flight-mechanics/performance/oei-climb-gradient: the one-engine-
  inoperative climb gradient for multi-engine rotorcraft, the
  longitudinal companion to this vertical-axis check.
- flight-mechanics/performance/climb-performance: the fixed-wing
  excess-thrust climb case; this leaf owns the rotorcraft vertical
  momentum-theory climb only.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_vertical_climb_performance.py

The test covers the worked example with the spec magnitude bounds (hover
induced velocity 9.5-11.5 m/s, climb induced velocity 7.5-9.5 m/s,
profile power 100000-150000 W, climb power 420000-490000 W, hover total
power 350000-430000 W, max climb rate 11-16 m/s), the momentum-theory
closed forms, the climb induced velocity decrease with climb rate, the
hover round trip, the induced power factor model and its default
constant, the cubic tip speed scaling of profile power, the
max_vertical_climb_rate bisection with the below-hover-power ValueError
and the excess-power upper bracket, the climb power margin sign, exact
dict keys and primitive consistency of vertical_climb_performance,
run-to-run determinism, absence of random or third-party imports, and
ValueError rejection of every non-physical input in the validation list.

## Compliance

- Standards referenced, not reproduced: FAR 29 (rotorcraft
  airworthiness, certification context only). The axial momentum theory
  climb relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

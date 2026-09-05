---
name: rotorcraft-turn-performance
description: 'Use when you must determine the banked-turn power of a helicopter rotor from momentum theory: the turning-flight inflow solved for the n-times-weight thrust of the banked level turn, the banked-turn-power breakdown into induced, profile and parasite terms, the sustained-load-factor an available power supports at the turn speed, the power-limited bank angle, and the turn rate and radius of the sustained maneuver. Produces the turn induced velocity, the turn power breakdown, the sustained-load-factor, bank angle, turn rate and turn radius that gate a rotorcraft maneuvering-power check at a chosen density. Momentum theory for level turns above one g only, not the fixed-wing method, level-flight power curve, hover, climb or autorotation. Trigger: helicopter banked turn, turning-flight inflow, rotorcraft turn power, sustained load factor, power-limited bank angle.'
license: Apache-2.0
compliance: STANDARDS-REF
standards:
- id: far-29
  reference-only: true
gated: false
domain: flight-mechanics
pack: performance
compatibility: agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags:
  - rotorcraft-turn-performance
  - turning-flight-inflow
  - banked-turn-power
  - sustained-load-factor
  - power-limited-bank-angle
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Turn Performance (flight-mechanics/performance/rotorcraft-turn-performance)

Use when the task is the banked-turn performance of a helicopter rotor
at load factors above one: the uniform-inflow momentum theory of a
steady coordinated level turn, where the disk banks so the thrust axis
carries the resultant n times the weight, the turning induced velocity
at that raised thrust, the turn power breakdown into induced, profile
and parasite terms, and the sustained-load-factor an available power
supports at the turn speed. This leaf implements the momentum-theory
solve in pure Python, stdlib only, with the disk-plane free-stream
convention of the level-flight Glauert model. It pairs with
flight-mechanics/performance/rotorcraft-forward-flight-performance,
which supplies the n = 1 power conventions and worked rotor this leaf
reuses, and with flight-mechanics/performance/rotorcraft-hover-
performance, whose v_h reference is the V = 0 identity of the turning
inflow.

## Domain quick reference

- Turn thrust: the rotor thrust in the banked level turn is the load
  factor times the weight, T = n * W with W = m * g0. At n = 1 the
  disk carries the level-flight weight; above one the rotor carries
  more than the aircraft weight.
- Turning inflow (momentum theory, uniform inflow): the generalized
  induced velocity v_i of the turn solves
  n * W = 2 * rho * A * v_i * sqrt(V**2 + v_i**2), v_i >= 0, with
  A = pi * R**2 the disk area. The left side is strictly increasing on
  v_i >= 0, so the root is unique; a FIXED-COUNT bisection on
  [0.0, sqrt(n * W / (2 * rho * A))] (BISECT_ITER = 120 iterations, no
  tolerance early exit) returns it. At n = 1 the value reproduces the
  level-flight Glauert inflow; at V = 0 it is sqrt(n * W / (2 * rho *
  A)) = sqrt(n) * v_h.
- Induced power: P_i = k * n * W * v_i with the induced power factor
  k = K_DEFAULT = 1.15, the hover and forward-flight convention.
- Profile power: P_prof = (1/8) * rho * sigma * Cd0 * A * V_tip**3,
  the average-section-drag model shared with the hover and forward-
  flight leaves; the turn keeps the rotor speed fixed, so the profile
  power of the turn equals the level-flight value.
- Parasite power: P_par = 0.5 * rho * V**3 * f with f the equivalent
  flat-plate drag area; the V**3 term makes the parasite power grow
  fast with the turn speed.
- Total turn power: P_total = k * n * W * v_i + P_prof + P_par,
  strictly increasing in the load factor because both n * W and v_i
  rise with n.
- Sustained maneuver: the power-sustained-load-factor n_s is the
  largest n whose turn power the available power covers, found by a
  FIXED-COUNT bisection on [1.0, N_CEILING]; bank angle phi =
  acos(1 / n_s), turn rate omega = G0 * sqrt(n**2 - 1) / V and turn
  radius R_t = V**2 / (G0 * sqrt(n**2 - 1)) close the maneuver with
  G0 = 9.80665 m/s2.
- Units are SI throughout: N, W, m/s, m2, kg/m3, rad. Angles are in
  rad; radians convert to degrees by 180 / pi.
- 14 CFR Part 29 (far-29) frames the rotorcraft context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the turn state and the rotor: load factor n >= 1, true airspeed
   V, rotor radius R (disk area A = pi * R**2), rotorcraft mass m
   (weight W = m * g0), density rho, solidity sigma, blade drag
   coefficient Cd0, tip speed, flat-plate drag area f and induced
   power factor k. Record the hover reference v_h = sqrt(W / (2 * rho
   * A)).
2. Raise the thrust to the load factor: thrust_for_turn returns
   T = n * W and rejects load factors below 1 with ValueError.
3. Solve the turning-flight-inflow: generalized_induced_velocity
   bisects on [0.0, sqrt(n * W / (2 * rho * A))] for v_i at the
   n-times-weight thrust. Check the identities: speed zero returns
   sqrt(n) * v_h, and at fixed n the inflow falls as the speed grows.
4. Break down the banked-turn-power: turn_power returns the dict
   {load_factor, thrust, induced_velocity, induced_power,
   profile_power, parasite_power, total_power} through induced_power,
   profile_power and parasite_power in the fixed order above. Confirm
   the n = 1 total equals the level-flight total of the forward-flight
   leaf at the same speed.
5. Invert for the power-sustained-load-factor: sustained_load_factor
   bisects h(n) = total power at n minus available power on
   [1.0, N_CEILING] and returns the sustained-load-factor with its
   bank_angle, the turning induced velocity, the power terms and a
   note of "power-limited" or "power-excess above ceiling". Get the
   same bank angle in one solve with max_bank_from_power.
6. Close the maneuver kinematics: bank_from_load_factor gives the
   power-limited-bank-angle acos(1 / n); turn_rate and turn_radius
   give omega and R_t at the sustained point. Verify omega * R_t = V
   and cos(bank) = 1 / n.
7. Confirm determinism: repeated calls return bit-identical values and
   the note strings are fixed, then run the contract test
   scripts/test_rotorcraft_turn_performance.py.

## Worked example

Shared worked rotor (identical to the hover and forward-flight worked
rotors): R = 5.0 m (A = 78.5398 m2), m = 2200 kg so W = m * g0 =
21574.63 N, rho = 1.225 kg/m3, solidity sigma = 0.08, Cd0 = 0.012,
tip speed 220 m/s, f = 2.2 m2, k = 1.15. Sea level.

- Hover reference at V = 0: v_h = sqrt(W / (2 * rho * A)) = 10.5887
  m/s at n = 1; at n = 2 the turn inflow is sqrt(2) * v_h =
  14.9747 m/s.
- Banked turn at n = 2.0, V = 60 m/s (module outputs): thrust
  T = 43149.3 N, turning induced velocity 3.73017 m/s, induced power
  185097 W, profile power 122935 W, parasite power 291060 W, total
  turn power 599092 W; bank angle acos(1/2) = 1.0472 rad (60 deg),
  turn rate 0.283094 rad/s, turn radius 211.944 m. The induced
  velocity at n = 2 is about twice the level-flight value 1.86778 m/s
  at the same speed, and the level-flight total power of 460336 W
  (the n = 1 identity, matching the forward-flight leaf worked
  example) grows by about 138 kW to sustain the 2 g turn at 60 m/s.
- Second state, n = 1.5 at V = 40 m/s: induced velocity 4.18175 m/s,
  induced power 155629 W, total 364804 W. Third inflow probe, n = 3.0
  at V = 60 m/s: induced velocity 5.58195 m/s.
- Power-sustained maneuver: available power 600000 W at V = 60 m/s
  gives sustained-load-factor 2.00491, bank angle 1.04861 rad
  (60.081 deg), turning induced velocity 3.73929 m/s, induced power
  186005 W, total power at the sustained point 600000 W, turn rate
  0.28402 rad/s and turn radius 211.253 m; max_bank_from_power
  returns 1.04861 rad.
- With available power 450000 W at V = 40 m/s the sustained-load-
  factor falls to 1.86867 (rate 0.387015 rad/s, radius 103.355 m),
  and at the same power and V = 50 m/s it falls further to 1.69094
  (rate 0.267439 rad/s, radius 186.959 m): the parasite V**3 growth
  cuts the sustained-load-factor as the speed rises at fixed power.

## Verification

- Confirm generalized_induced_velocity(2.0, 21574.63, 78.5398, 1.225,
  60.0) returns 3.73017 m/s and that the n = 1, V = 0 and n = 2, V =
  0 calls return 10.5887 and 14.9747 m/s (sqrt(2) times v_h).
- Confirm turn_power at n = 2, V = 60 m/s totals 599092 W and that the
  n = 1 total at 60 m/s is 460336 W, equal to the forward-flight leaf
  worked total at that speed.
- Confirm sustained_load_factor(600000.0, 21574.63, 78.5398, 1.225,
  60.0, 0.08, 0.012, 220.0, 2.2) returns load_factor 2.00491 with note
  "power-limited" and that turn_power at the returned load factor
  reproduces the available power (round trip).
- Confirm every non-physical input raises ValueError: load factor
  below 1, non-positive weight, area, rho, solidity, drag
  coefficient, tip speed, k or available power, negative speed, a
  ceiling at or below 1, and available power below the n = 1 total at
  the speed (level flight not sustainable).
- Run the contract test offline: python3
  scripts/test_rotorcraft_turn_performance.py (34 tests,
  deterministic).

## Related leaves

- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the level-flight Glauert inflow and power conventions this leaf
  reuses at n = 1; its worked rotor and total power are identical.
- flight-mechanics/performance/rotorcraft-hover-performance: the hover
  v_h reference and V = 0 limit of the turning inflow.
- flight-mechanics/performance/turn-performance: the fixed-wing
  level-turn kinematics (omega, R_t, load factor from bank) for
  aircraft without a rotor inflow model.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  the bracket convention of the "power-excess above ceiling" note and
  its climb power solves.
- flight-mechanics/performance/rotorcraft-range-endurance: fuel
  closure on the level power curve, downstream of the turn power
  estimate.

## Pitfalls

- Reusing the level-flight induced velocity in the turn: at n = 2 the
  turning inflow is 3.73017 m/s against 1.86778 m/s level at 60 m/s,
  so the power must be built on the n-times-weight thrust or the turn
  is understated by a factor near n in the induced term.
- Forgetting the induced power factor: the induced term is k * n * W *
  v_i with k = 1.15, not the ideal n * W * v_i; dropping k
  understates P_i by 15 percent (185097 W against 160954 W at n = 2,
  60 m/s).
- Feeding n into the profile or parasite power: the turn keeps the
  rotor speed fixed and the free stream in the disk plane, so
  profile_power and parasite_power do not depend on n; only the
  induced term carries the load factor.
- Reading the excess case as a bisection result: when the total power
  at n = N_CEILING stays below the available power, the sustained
  solve returns load_factor = N_CEILING with note "power-excess above
  ceiling"; the bracket convention does not extrapolate beyond the
  ceiling.
- Ignoring the level-flight floor: an available power below the n = 1
  total at the turn speed (460336 W at 60 m/s on the worked rotor)
  raises ValueError, because no banked turn exists at a speed whose
  level flight the power cannot sustain.
- Writing the compound terms with spaces: sustained-load-factor and
  power-limited-bank-angle are the leaf's routing tokens; keep them
  hyphenated in the description so they do not tokenize into generic
  words owned by the fixed-wing turn leaf.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_turn_performance.py

It covers the turning-flight-inflow anchors at n = 1, 1.5, 2 and 3
against the level-flight Glauert and sqrt(n) * v_h identities, the
banked-turn-power breakdown anchors (induced 185097 W, profile
122935 W, parasite 291060 W, total 599092 W at n = 2, 60 m/s), the
n = 1 total power identity with the forward-flight leaf, the monotone
power and inflow behaviors, the sustained-load-factor solves with
their power round trips and fixed note strings, the kinematics
anchors with the omega * R_t = V and cos(bank) = 1 / n identities,
determinism of repeated calls, and ValueError rejection of every
non-physical input class in the spec validation list.

## Behavior contract (gate 3)

The leaf is deterministic: pure stdlib math, FIXED-COUNT bisection
schedules (BISECT_ITER = 120), no RNG, no network, no external
processes. The contract test above must pass in full before the leaf
is rated; its 34 test methods exercise every workflow step of this
SKILL.md and every validation item of the wave-41 spec.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 29 (far-29) is US
  government work in the public domain; the momentum-theory relations
  above are standard engineering methodology, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

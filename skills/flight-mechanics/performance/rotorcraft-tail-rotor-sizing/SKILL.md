---
name: rotorcraft-tail-rotor-sizing
description: "Use when you must size the anti-torque tail rotor of a single-main-rotor rotorcraft from the main rotor torque balance: main rotor shaft torque from the main rotor power input and rotor speed, tail rotor thrust to balance that torque about the tail arm with a yaw margin factor, tail rotor disk area and radius for a chosen maximum disk loading, ideal induced velocity and ideal power from momentum theory, and tail rotor total power from the induced-power factor and a tail-rotor profile power estimate. Produces the main rotor torque, anti-torque thrust, tail rotor radius, disk loading, induced power, profile power and total power that gate an anti-torque sizing check. Trigger: tail-rotor-sizing, anti-torque-rotor, tail-rotor-thrust, main-rotor-torque, tail-rotor-power."
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
  tags: [rotorcraft-tail-rotor-sizing, anti-torque-rotor, tail-rotor-thrust, main-rotor-torque, tail-rotor-power]
  version: 0.1.0
  author: Aero Agent Skills
---

# Tail Rotor Sizing (flight-mechanics/performance/rotorcraft-tail-rotor-sizing)

Use when you must size the anti-torque tail rotor of a single-main-rotor
rotorcraft from the main rotor torque balance: the main rotor power at the
rotor speed sets the shaft torque, the anti-torque thrust follows from the
torque over the tail arm, and a maximum disk loading sets the tail rotor disk
area and radius. The induced velocity and ideal power come from momentum
theory, and the total power adds the induced-power factor and a tail-rotor
profile power estimate. The main rotor power is an INPUT to this leaf: it is
never computed from weight and geometry here. Pure Python, stdlib only. It
pairs with flight-mechanics/performance/rotorcraft-hover-performance, which
owns the main rotor hover power, and with the forward flight, climb and
ground effect rotorcraft leaves for the other flight states.

## Domain quick reference

- Main rotor shaft torque: Q = P / omega, from the main rotor power P and
  the rotor angular speed omega.
- Anti-torque thrust: T_tr = margin_factor * Q / l_arm, with l_arm the tail
  arm and margin_factor the yaw control margin on the required thrust
  (default 1.0).
- Tail rotor disk area at the ceiling: A = T_tr / DL_max, with DL_max the
  maximum disk loading (default 300 Pa).
- Tail rotor radius: R = sqrt(A / PI).
- Disk loading: DL = T_tr / A, at or below DL_max when sized with it.
- Ideal induced velocity (momentum theory): v_i = sqrt(T_tr / (2 * rho * A)),
  rho = 1.225 kg/m3 at sea level.
- Ideal power: P_ideal = T_tr * v_i.
- Profile power estimate: P_profile = (1/8) * rho * sigma * Cd * A *
  V_tip^3, with solidity sigma = 0.10, Cd = 0.012 and tip speed
  V_tip = 200 m/s defaults.
- Total power: P_total = k * P_ideal + P_profile, with induced-power factor
  k = 1.15.
- SI units throughout: W, rad/s, N m, N, m, m2, Pa, m/s.
- FAR-29 frames transport rotorcraft certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: main rotor power input P, rotor speed omega and
   tail arm l_arm (main_rotor_torque, tail_rotor_thrust).
2. Choose the yaw margin factor on the required thrust (default 1.0) and the
   maximum disk loading ceiling.
3. Size the disk: tail_rotor_area at the ceiling, then tail_rotor_radius and
   confirm the achieved tail_rotor_disk_loading.
4. Compute the momentum theory induced velocity with
   tail_rotor_induced_velocity and the ideal power with
   tail_rotor_ideal_power.
5. Estimate the profile power with tail_rotor_profile_power (solidity, Cd,
   tip speed defaults) and combine with tail_rotor_total_power.
6. For the full chain in one call, run tail_rotor_sizing with all inputs and
   read the nine documented outputs.
7. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_tail_rotor_sizing.py.

## Worked example

Main rotor power 400 000 W at 27 rad/s, tail arm 8.0 m, max disk loading
300 Pa, rho = 1.225 kg/m3, margin factor 1.0, solidity 0.10, Cd 0.012,
tip speed 200 m/s, k = 1.15. Module outputs:

- Main rotor torque: Q = 400000 / 27 = 14 814.8 N m.
- Anti-torque thrust: T_tr = 14814.8 / 8.0 = 1851.9 N.
- Disk area: A = 1851.9 / 300 = 6.1728 m2.
- Tail rotor radius: R = sqrt(6.1728 / PI) = 1.4017 m.
- Disk loading: 300.0 Pa, exactly the ceiling.
- Induced velocity: v_i = sqrt(1851.9 / (2 * 1.225 * 6.1728)) = 11.066 m/s.
- Ideal power: P_ideal = 1851.9 * 11.066 = 20 492.0 W.
- Profile power: P_profile = (1/8) * 1.225 * 0.10 * 0.012 * 6.1728 *
  200^3 = 9074.1 W.
- Total power: P_total = 1.15 * 20492.0 + 9074.1 = 32 639.8 W.

All values sit inside the spec magnitude bounds (torque 13 000-17 000 N m,
thrust 1500-2200 N, area 5.0-7.5 m2, radius 1.2-1.6 m, induced velocity
9-13 m/s, ideal power 15 000-26 000 W, total power 22 000-36 000 W).

## Verification

- Confirm tail_rotor_sizing(400000.0, 27.0, 8.0) returns the worked example
  values above at the default ceiling, rho and factor settings.
- Confirm the torque balance identity: tail_rotor_thrust(Q, arm) * arm
  equals Q at margin factor 1.0.
- Confirm the radius round-trip: PI * tail_rotor_radius(A)**2 recovers A.
- Confirm the disk loading never exceeds the ceiling when the disk is sized
  with that ceiling, even with a margin factor above 1.0.
- Confirm the total power identity P_total = k * P_ideal + P_profile.
- Confirm every non-positive power, torque, arm, disk loading, rho,
  solidity, drag coefficient, tip speed, area and induced-power factor
  raises ValueError.
- No RNG anywhere: repeated runs give identical floats.
- Run the contract test offline: python3
  scripts/test_rotorcraft_tail_rotor_sizing.py (47 tests, deterministic).

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the main rotor
  OGE hover power that is the torque-balance input for this leaf.
- flight-mechanics/performance/rotorcraft-forward-flight-performance: main
  rotor power in forward flight, the other power state feeding the torque
  balance.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  climb power states for the same main rotor.
- flight-mechanics/performance/rotorcraft-hover-ground-effect: ground effect
  on the main rotor power input near the ground.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_tail_rotor_sizing.py

The test covers the worked example anchors at 4 significant figures and the
spec magnitude bounds, every function against its defining equation, the
torque-balance round trip, the area-radius round trip, disk loading at or
below the ceiling with a yaw margin, the exact key set of the convenience
dict, run-to-run determinism, and ValueError rejection of every
non-physical input class.

## Compliance

- Standards referenced, not reproduced: FAR-29 is a regulatory standard;
  the tail rotor sizing relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

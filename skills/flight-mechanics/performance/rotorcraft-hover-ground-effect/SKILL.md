---
name: rotorcraft-hover-ground-effect
description: "Use when you must compute the hover-in-ground-effect performance of a rotorcraft rotor: the Cheeseman-style ground-effect reduction factor for the rotor induced power from the height above the ground and the rotor radius, the in-ground-effect induced power, the in-ground-effect total hover power from the induced-power factor and the unchanged profile power, the power margin against an available power, and the maximum rotor height at which the rotorcraft can still hover with that available power. Produces the ground-effect factor, the IGE induced and total hover power, the IGE power margin and the maximum hover height that gate a rotorcraft hover check in ground effect. Trigger: rotorcraft-hover-ground-effect, hover-in-ground-effect, ige-power-reduction, ground-effect-factor, ige-hover-ceiling, rotor-height-ratio."
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
  tags: [rotorcraft-hover-ground-effect, hover-in-ground-effect, ige-power-reduction, ground-effect-factor, ige-hover-ceiling, rotor-height-ratio]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Hover in Ground Effect (flight-mechanics/performance/rotorcraft-hover-ground-effect)

Use when you must compute the hover-in-ground-effect performance of a
rotorcraft rotor hovering over a flat ground plane: the induced-power
reduction from the rotor height above the ground and the rotor radius,
the IGE induced power, the IGE total hover power, the power margin
against an available power, and the largest rotor height at which the
rotorcraft can hover with that power. This leaf fills the rotorcraft
gap in the library: the out-of-ground-effect hover sibling
(flight-mechanics/performance/rotorcraft-hover-performance) explicitly
defers hover in ground effect, and the ground-effect leaf in the
aerodynamics family covers the fixed-wing wing-in-ground-effect
configuration, a different physical problem with different outputs.
The rotor model here applies the classic Cheeseman-style height
correction to the induced power only; profile power is unchanged in
ground effect. No recirculation, no partial ground contact, no vertical
climb and no forward flight: those belong to sibling leaves.

## Domain quick reference

All quantities are SI. Rotor thrust equals the rotorcraft weight in
hover: T = m * g0, g0 = 9.80665 m/s^2.

- Disk area: A = PI * R^2.
- Ideal induced velocity (momentum theory, uniform inflow): v_h =
  sqrt(T / (2 * rho * A)).
- Ideal induced power: P_ideal = T * v_h.
- Profile power (average section drag model): P_profile = (1/8) * rho *
  sigma * Cd0 * A * Vtip^3, with sigma the rotor solidity, Cd0 the mean
  blade drag coefficient and Vtip the tip speed. The profile power does
  not change in ground effect.
- Ground-effect factor (Cheeseman-style height correction on the
  induced velocity, and therefore on the induced power at constant
  thrust): k_ige = 1 - (R / (4*z))^2, with z the rotor height above the
  ground. Valid for z / R >= 0.5; below that the point model diverges.
  At z = R the factor is 0.9375; at z = 0.5*R it is exactly 0.75; it
  increases toward 1 as the rotor climbs.
- IGE induced power: P_i_ige = P_ideal * k_ige.
- IGE total hover power: P_total_ige = k * P_ideal * k_ige +
  P_profile, with k the induced power factor (default 1.15, same
  convention as the hover sibling).
- OGE total hover power: P_total_oge = k * P_ideal + P_profile. If the
  available power covers P_total_oge the rotorcraft can hover at any
  height; otherwise ground effect sets a hover ceiling.
- Power margin: margin = P_available - P_total_ige.
- Maximum hover height: the largest z (z / R >= 0.5) where P_total_ige
  equals the available power. The IGE total power grows with z and
  asymptotes to the OGE value, so the root is unique; the logic bisects
  z over [0.5*R, 50*R].
- Default density rho = 1.225 kg/m^3 is sea level; pass the density at
  the chosen altitude to re-evaluate the check there.
- FAR 29 frames the rotorcraft certification context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: rotor radius R, rotorcraft mass m, height z
   above the ground, density rho, solidity sigma, mean blade drag
   coefficient Cd0, tip speed Vtip, induced power factor k and the
   available power.
2. Get the disk area with disk_area(radius) and the thrust T = m * G0
   (hover thrust equals weight).
3. Compute the ideal induced velocity with hover_induced_velocity(thrust,
   area, rho) and the ideal induced power P_ideal = thrust * v_h.
4. Compute the ground-effect factor with ground_effect_factor(height,
   radius); it raises ValueError when z / R falls below the 0.5 floor.
5. Combine with ige_induced_power(P_ideal, factor) and
   ige_total_power(P_ideal, profile_power, factor, k) for the IGE power
   terms, and with oge_total_power(P_ideal, profile_power, k) for the
   OGE reference. The profile power input comes from the same section
   drag model used by the hover sibling.
6. Compare against the available power with power_margin(available,
   required).
7. If the available power is below the OGE total, find the IGE hover
   ceiling with max_hover_height(weight_kg, radius, available_power,
   ...); it returns None when OGE hover is possible and raises
   ValueError when the power is too low even in full ground effect.
8. For a one-call verdict run hover_ground_effect(weight_kg, radius,
   height, ...), which returns the full result dict and propagates
   every ValueError from the primitives.
9. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_hover_ground_effect.py.

## Worked example

A helicopter at 2200 kg mass with a 5.0 m radius rotor at sea level,
hovering at z = 5.0 m (z / R = 1.0): rho = 1.225 kg/m^3, solidity 0.08,
Cd0 = 0.012, tip speed 220 m/s, k = 1.15. Running
hover_ground_effect(2200.0, 5.0, 5.0, available_power = 360000.0):

- Thrust: 2200 * 9.80665 = 21574.63 N.
- Disk area: PI * 5.0^2 = 78.54 m^2.
- Hover induced velocity: v_h = 10.589 m/s (hand estimate about 10.6
  m/s, within the 9.5-11.5 m/s band).
- Ideal induced power: 228448 W (within 200000-260000 W).
- Profile power: 122935 W (within 100000-150000 W).
- Ground-effect factor: k_ige = 0.9375 at z / R = 1.0 (within
  0.90-0.97); 0.9844 at z / R = 2.0 and exactly 0.75 at z / R = 0.5.
- IGE induced power: 214170 W, the ideal power times the factor.
- IGE total power: 1.15 * 228448 * 0.9375 + 122935 = 369230 W (within
  350000-390000 W).
- OGE total power: 1.15 * 228448 + 122935 = 385650 W (within
  350000-430000 W), the ceiling the IGE curve approaches as z grows.
- Power margin at 360000 W available: 360000 - 369230 = -9230 W, so
  the rotorcraft cannot hover at z = 5.0 m with 360 kW.
- Maximum hover height at 360000 W: max_hover_height returns 4.000 m
  (within 3.0-5.0 m): the rotorcraft can hover in ground effect only
  below about 4 m with that power.
- At 400000 W available (above the 385650 W OGE total) max_hover_height
  returns None: hover is possible at any height.

## Verification

- Confirm ground_effect_factor(5.0, 5.0) equals 0.9375 exactly and
  ground_effect_factor(2.5, 5.0) equals 0.75 exactly (z / R = 0.5).
- Confirm ige_induced_power equals the ideal power times the factor and
  ige_total_power equals k * P_ideal * factor + P_profile for the same
  inputs.
- Confirm the factor increases toward 1 as the height grows, and that
  the IGE total power is always below the OGE total for a factor under
  1, recovering it exactly at factor 1.
- Confirm max_hover_height returns about 4.0 m at 360 kW, returns None
  at and above the OGE total power, and rejects available powers below
  the IGE total at the lowest valid height.
- Confirm the bisected ceiling is a true root: the IGE total power at
  the returned height equals the available power to within 1 W.
- Confirm determinism: repeated runs return identical floats (no RNG,
  stdlib only, no external imports).
- Confirm every non-positive radius, thrust, density, solidity, drag
  coefficient, tip speed and induced power factor, every negative
  power, every factor outside (0, 1], and every z / R below 0.5 raises
  ValueError.
- Run the contract test offline: python3
  scripts/test_rotorcraft_hover_ground_effect.py (32 tests,
  deterministic).

## Pitfalls

- Calling the ground-effect factor below the validity floor: the
  Cheeseman-style point model diverges for z/R < 0.5 and
  ground_effect_factor raises ValueError there; z/R = 0.5 is exactly 0.75
  and z/R = 1 is 0.9375.
- Reading max_hover_height None as an error: None means the available power
  covers the OGE total, so the rotorcraft can hover at any height; a
  ValueError (not None) is raised only when the power is too low even in
  full ground effect.
- Applying the factor to profile power: ground effect modifies the induced
  power only; P_profile is unchanged, and the IGE total is k*P_ideal*factor
  + P_profile.
- Treating the IGE ceiling as exact without the root check: the returned
  height is a bisection root where IGE total power equals the available
  power to within 1 W; verify that equality before quoting the hover
  ceiling.
- Factor outside (0, 1] or non-positive radius, thrust, density, solidity,
  drag coefficient, tip speed or induced power factor raises ValueError.

## Related leaves

- flight-mechanics/performance/rotorcraft-hover-performance: the
  out-of-ground-effect hover sibling (momentum-theory induced velocity,
  ideal and profile power, total power with the induced power factor)
  that this leaf extends into ground effect. Its body defers hover in
  ground effect here.
- aerodynamics/ground-effects/ground-effect: the fixed-wing
  wing-in-ground-effect leaf (induced drag and lift change for a wing
  from height to span ratio and image vortices), a different physical
  configuration with different outputs. This leaf owns the rotor-disk
  hover-in-ground-effect induced-power reduction only.
- flight-mechanics/performance/rotorcraft-forward-flight-performance:
  the sibling rotor leaf for the speed-dependent power breakdown used
  after the hover check.
- flight-mechanics/performance/rotorcraft-vertical-climb-performance:
  the rotorcraft vertical climb sibling, adjacent to the hover power
  check in a rotorcraft performance pass.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rotorcraft_hover_ground_effect.py

The test covers the worked example with the spec magnitude bounds
(induced velocity 9.5-11.5 m/s, ideal power 200000-260000 W, profile
power 100000-150000 W, IGE total 350000-390000 W, OGE total
350000-430000 W, ceiling 3.0-5.0 m), the exact factor anchors (0.9375
at z / R = 1, 0.75 at z / R = 0.5, 0.984375 at z / R = 2), the
Cheeseman closed form and its monotonicity, the induced-power-factor
model and its default constant, the OGE-IGE ordering and unit-factor
recovery, the ceiling root consistency and None return above the OGE
total, the convenience dict exact keys and primitive consistency,
run-to-run determinism, absence of random or third-party imports, and
ValueError rejection of every non-physical input in the validation
list.

## Compliance

- Standards referenced, not reproduced: FAR 29 (rotorcraft
  airworthiness, certification context only). The Cheeseman-style
  ground-effect relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

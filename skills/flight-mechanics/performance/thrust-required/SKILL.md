---
name: thrust-required
description: "Use when you must compute the thrust required and power required curves for level unaccelerated flight from the drag polar: derive the total drag coefficient from the zero lift drag coefficient and the induced drag factor, compute the thrust required and the power required at a given equivalent airspeed, weight, wing area, and air density (for example the sea level density 1.225 kg/m^3), and locate the characteristic points: the minimum drag speed where the parasite drag equals the induced drag, the minimum power speed, and the minimum thrust at the maximum lift to drag ratio. Produces the thrust required curve, the power required curve, the minimum drag speed, the minimum power speed, and the minimum thrust that gate the level flight performance assessment. Trigger: thrust required, power required, minimum drag speed, minimum power speed, drag polar, level flight."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: flight-mechanics
pack: flight-mechanics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: performance
  tags: [thrust-required, power-required, minimum-drag-speed, minimum-power-speed, level-flight, drag-polar, induced-drag-factor, zero-lift-drag, lift-to-drag]
  version: 0.1.0
  author: Aero Agent Skills
---

# Thrust Required (flight-mechanics/performance/thrust-required)

Use when the task is the level flight performance analysis: the thrust
required and power required curves versus airspeed, the minimum drag
speed, the minimum power speed, and the minimum thrust.

## Domain quick reference

- For level unaccelerated flight the lift equals the weight and the
  thrust required equals the drag. With the parabolic drag polar,
  CD = cd0 + k CL^2, and CL = 2 W / (rho V^2 S), the thrust required is
  T_req = 0.5 rho V^2 S cd0 + 2 k W^2 / (rho V^2 S), with weight W in
  newtons, wing area S in m^2, air density rho in kg/m^3, and speed V in
  m/s equivalent airspeed (EAS). The power required is P_req = T_req V.
  Compressibility is ignored; this is the usual low speed assumption.
- Minimum drag speed: V_md = sqrt((2 W / (rho S)) sqrt(k / cd0)), the
  speed where the parasite drag equals the induced drag. Worked: W =
  650000 N, S = 122 m^2, rho = 1.225 kg/m^3 at sea level, cd0 = 0.02,
  k = 0.042 gives about 112.3 m/s EAS, with a thrust required of about
  37.7 kN.
- Minimum power speed: V_mp = sqrt((2 W / (rho S)) sqrt(k / (3 cd0))),
  about 85.3 m/s EAS for the same case, where the induced drag is three
  times the parasite drag. V_mp = V_md / 3^(1/4).
- Maximum lift to drag ratio: (L/D)_max = 1 / (2 sqrt(cd0 k)), about
  17.25 for the worked case, and the minimum thrust is
  T_min = W / (L/D)_max = 2 W sqrt(cd0 k), about 37.7 kN, which equals
  the thrust required at the minimum drag speed.
- Curve shape: the thrust required curve is U shaped. At 60 m/s the
  worked case needs about 71.3 kN (induced drag dominated), at 112.3
  m/s about 37.7 kN, and at 140 m/s about 41.4 kN (parasite drag
  dominated).
- The curve is only flyable at or above the stall speed: below the
  stall the required lift coefficient exceeds CL_max and the points are
  not physical.

## Workflow

1. Collect the aircraft level flight inputs: the weight W in newtons,
   the wing area S in m^2, the air density rho in kg/m^3, and the full
   aircraft drag polar coefficients cd0 and k.
2. Compute the characteristic points with minimum_drag_speed(...) and
   minimum_power_speed(...); the minimum drag speed is the reference
   for the curve.
3. Sweep the speed range from the stall speed up to the desired cruise
   speed and evaluate lift_coefficient(...), drag_coefficient(...),
   thrust_required(...), and power_required(...) at each speed.
4. Confirm the curve minimum: the thrust required at the minimum drag
   speed equals minimum_thrust(...), and the power required minimum
   sits at the minimum power speed.
5. Report the curve and the characteristic values with
   maximum_lift_to_drag(...) as the efficiency reference.

## Pitfalls

- Routing polar fitting here: estimating cd0 and k from measured points
  and the Oswald span efficiency belong to
  aerodynamics/drag-polars/drag-polar; this leaf consumes the polar
  coefficients, it does not fit them.
- Routing excess thrust here: rate of climb and excess power belong to
  climb-performance; this leaf stops at the thrust required curve and
  never subtracts the available thrust.
- Routing fuel here: specific air range, fuel flow, and sector fuel
  burn belong to specific-range; this leaf returns forces and power,
  not fuel.
- Routing energy here: energy height and specific excess power belong
  to energy-height.
- Routing installed thrust here: sea level static thrust, thrust lapse,
  and the thrust margin against the cruise drag belong to
  vehicle-design/sizing/engine-sizing; this leaf computes what the
  aircraft needs, not what the engine delivers.
- Routing the envelope here: the load factor envelope, stall speed
  boundary, and corner point belong to
  flight-test-operations/envelope/load-factor-envelope; that analysis
  lives in the n-V plane, this one in the T-V plane.
- Using mass where weight belongs: W in the formulas is the weight in
  newtons (mass times gravity); feeding mass in kg scales the thrust
  required by g.
- Mixing EAS and TAS: the speeds are equivalent airspeeds at the given
  density; at altitude convert the true airspeed to EAS with the
  density ratio before evaluating the curve.
- Using a wing-only polar: cd0 and k must cover the whole aircraft
  (fuselage, nacelles, interference), otherwise the thrust required is
  understated.
- Reading the curve below the stall: the parabolic polar points below
  the stall speed are not achievable in level flight; start the sweep
  at the stall speed.
- Ignoring the minimum power speed: for propeller driven aircraft the
  range and endurance speeds come from the power required curve, not
  the thrust required curve.

## Behavior contract (gate 3)

The thrust required and power required logic is exercised by the gate 3
contract test: scripts/test_thrust_required.py against
scripts/thrust_required_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_thrust_required.py

## Compliance

- Standards referenced, not reproduced: FAR-25 and CS-25 performance
  requirements frame the level flight analysis for transport
  aeroplanes; the parabolic polar thrust and power required method is
  common performance methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

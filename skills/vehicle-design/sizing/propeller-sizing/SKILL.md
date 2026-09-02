---
name: propeller-sizing
description: "Use when you must size the propeller geometry and set its operating point at the conceptual design point: derive the propeller diameter from the blade-tip constraint and the ground clearance, select the blade count and the blade chord from the solidity and the activity factor, compute the disk loading of the selected disk, and locate the operating point with the advance ratio from the forward motion, the revolutions per second, and the propeller diameter. Produces the propeller diameter, blade count, chord, solidity, activity factor, disk loading, and advance ratio that feed the propeller installation and the matching leaves. Trigger: propeller sizing, propeller diameter, blade count, solidity, activity factor, disk loading, advance ratio, ground clearance, blade-tip constraint."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: vehicle-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [propeller-sizing, propeller-diameter, blade-count, blade-number, activity-factor, solidity, disk-loading, ground-clearance, advance-ratio]
  version: 0.1.0
  author: Aero Agent Skills
---

# Propeller Sizing (vehicle-design/sizing/propeller-sizing)

Use when the task is sizing the geometric propeller for a given
design point: the propeller diameter from the blade-tip constraint
and the ground clearance, the blade count and chord from the
solidity and the activity factor, the disk loading of the selected
disk, and the operating point from the advance ratio. The output is
the propeller geometry and its loading, not the evaluation of the
engine that drives it.

## Domain quick reference

- Units: forces in N, shaft power in W, speeds in m/s, rpm in
  revolutions per minute, densities in kg/m^3, lengths in m, disk
  area in m^2, angles in radians, Mach numbers and efficiencies
  unitless.
- Advance ratio: J = V / (n * D) with n = rpm / 60. Anchor:
  70 m/s at 2200 rpm and 2.0 m diameter give J = 0.9545. The static
  point (V = 0) gives J = 0.
- Blade-tip constraint: the blade tip must stay below the local
  Mach limit. Anchor: 2200 rpm and 2.0 m diameter give 230.38 m/s
  at the tip, Mach 0.677 at a = 340.3 m/s, inside the common 0.85
  limit with 0.173 margin.
- Diameter from the blade-tip bound: D = V_limit / (pi * n). Anchor:
  2200 rpm with a 250 m/s bound gives 2.1703 m.
- Disk loading: T / A with A = pi * D^2 / 4. Anchor: 4000 N over a
  2.0 m disk gives 1273.24 N/m^2.
- Static thrust (actuator disk momentum theory, loss-free):
  T = (2 * rho * A * P^2)^(1/3). Anchor: 150 kW over a 2.0 m disk at
  rho = 1.225 kg/m^3 gives 5573.99 N; the inverse relation returns
  the 150000 W.
- Solidity: sigma = B * c / (pi * D). Anchor: 3 blades of 0.25 m
  chord on a 2.0 m diameter give 0.11937.
- Activity factor (constant-chord summary of the blade loading
  integral): AF = B * (100000 / 16) * (c / D) * (1 - x_hub^4) / 4.
  Anchor: 3 blades, 0.25 m chord, 2.0 m diameter, hub fraction
  0.15 give 585.64.
- Efficiency versus advance ratio (parabolic model):
  eta = eta_max * (1 - ((J - J_design) / J_design)^2) for J in
  [0, 2 * J_design], and 0 outside. Anchor: J_design = 0.9 and
  eta_max = 0.85 give 0.85 at the design point, 0.6375 at
  J = 0.45, and 0 at the static point.
- Ground clearance: the tip sits hub_height - D / 2 above the
  ground. Anchor: 2.0 m diameter at 1.6 m hub height gives 0.6 m of
  clearance, ok against a 0.2 m minimum; 3.0 m diameter gives 0.1 m,
  below the minimum.
- P-factor (first-order estimate): N_p = T * (D / 4) * sin(alpha).
  Anchor: 4000 N at 10 degrees angle of attack on a 2.0 m diameter
  gives 347.30 N m.
- In-flight thrust from the propulsive power: T = eta * P / V.
  Anchor: 150 kW at 70 m/s with eta = 0.8 gives 1714.29 N, below
  the 5573.99 N static thrust from the same power at the same
  diameter.
- FAR-25 (14 CFR Part 25) and CS-25 set the certification context
  for transport-category propeller installations (reference-only);
  the relations above are common conceptual sizing practice.

## Workflow

1. Set the operating point: forward motion V, rpm, shaft power P,
   and the Mach limit at the cruise altitude.
2. Compute the advance ratio with advance_ratio to locate the
   operating point on the efficiency curve.
3. Size the diameter with diameter_from_tip_speed_limit against the
   blade-tip bound, then check the tip condition with
   tip_mach_check using the local speed of sound; reduce the rpm or
   the diameter until within_limit is True.
4. Check the ground clearance with ground_clearance_check; the tip
   must clear the ground in the static and takeoff attitudes.
5. Estimate the static thrust with static_thrust_estimate from the
   shaft power and the disk area, or invert the target with
   power_for_static_thrust when the requirement fixes the power.
6. Select the blade count and chord with solidity and
   activity_factor: more blades or more chord raise the loading
   capability at the cost of efficiency at the cruise point.
7. Evaluate the disk loading; a larger diameter lowers it and
   raises the propulsive efficiency, within the blade-tip bound and
   the ground clearance.
8. Estimate the P-factor yawing moment with p_factor_moment for the
   takeoff and climb attitudes, and the in-flight thrust with
   thrust_from_power_in_flight for the cruise point.
9. Hand the diameter, blade count, advance ratio, static thrust, and
   tip Mach margin to the sibling leaves: engine-sizing (shaft power
   matching), the turboprop cycle analysis (powerplant assessment),
   and the performance leaves (climb and takeoff distance).

## Pitfalls

- Confusing this leaf with turboprop-cycle: turboprop-cycle evaluates
  the powerplant cycle and converts the shaft power into thrust and
  efficiency; propeller-sizing selects the geometric propeller
  (diameter, blade count, chord) against the blade-tip bound, the
  ground clearance, and the disk loading. The geometry sizing comes
  first, the cycle evaluation second.
- Confusing this leaf with engine-sizing: engine-sizing sizes the
  engine set and lapses its output with altitude; propeller-sizing
  converts the shaft power into propeller thrust. Do not size the
  gas generator here.
- Confusing this leaf with wing-planform-sizing: wing-planform-sizing
  sizes the wing geometry from the wing loading and the aspect
  ratio; the propeller constraints (blade-tip bound, ground
  clearance) apply to the propeller installation, not the wing. A
  wing geometry question belongs to the wing leaf.
- Treating the static thrust estimate as exact: actuator disk
  momentum theory ignores induced, profile, and installation losses;
  a real static thrust runs below the loss-free value, so size with
  margin.
- Ignoring the blade-tip bound at altitude: the speed of sound falls
  with altitude and temperature, so a tip condition that is safe at
  sea level may exceed the limit at cruise; check with the local
  speed of sound, not the sea level value.
- Sizing the diameter without the ground clearance: a large diameter
  that meets the blade-tip bound can still strike the ground in the
  takeoff attitude; run ground_clearance_check before fixing the
  diameter.
- Forgetting the static point: at J = 0 the propeller does no useful
  work and the efficiency is zero; the static thrust is the maximum
  available and drives the takeoff acceleration.
- Mixing units: rpm must be converted to revolutions per second
  before computing the advance ratio and the tip condition, and
  powers must be in W, not kW, in the actuator disk relations.
- Using the parabolic efficiency model outside its range: the model
  is a summary of the efficiency curve near the design point and
  returns zero beyond twice the design advance ratio; a blade element
  analysis supersedes it for detailed work.

## Behavior contract (gate 3)

The advance ratio, tip condition and Mach check, disk loading, static
thrust estimate and its power inverse, diameter from the blade-tip
bound, solidity and activity factor, efficiency versus advance ratio,
ground clearance check, P-factor moment, and in-flight thrust are
exercised by the gate 3 contract test:
scripts/test_propeller_sizing.py against
scripts/propeller_sizing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_propeller_sizing.py

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the propeller
  sizing relations are common conceptual sizing methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

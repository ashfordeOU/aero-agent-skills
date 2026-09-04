---
name: fuel-feed-system-sizing
description: "Use when you must size the aircraft fuel feed system between the tank and the engine: the per-engine feed flow from the takeoff fuel flow demand, the feed line velocity and Reynolds number, the line pressure loss from the Darcy friction factor (laminar 64/Re, turbulent Blasius) with the major loss over the line length and the minor losses from the fitting loss coefficient, the static head gain from tank to pump, and the net positive suction head available at the engine-driven pump inlet against the required NPSH with the boost pump pressure rise added at cruise altitude. Produces the feed flow, the line pressure loss, the NPSH available with and without the boost pump, the feed PASS/FAIL verdict, and the boost pump hydraulic power that gate the fuel feed system layout. Trigger: fuel feed system sizing, boost pump sizing, feed line pressure loss, engine feed NPSH, fuel pump power."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [fuel-feed-system-sizing, boost-pump-sizing, feed-line-pressure-loss, engine-feed-npsh, fuel-pump-power]
  version: 0.1.0
  author: AeroSkills
---

# Fuel Feed System Sizing (vehicle-design/sizing/fuel-feed-system-sizing)

Use when the task is sizing the aircraft fuel feed system between the
tank outlet and the engine at the conceptual level: converting the
per-engine engine fuel flow demand into the feed line velocity and
Reynolds number, computing the line pressure loss from the Darcy
friction factor with the major loss over the line length and the minor
losses from the fitting loss coefficient, adding the static head gain
from the tank to the engine-driven pump, and checking the net positive
suction head available at the pump inlet against the required NPSH with
the boost pump pressure rise added at cruise altitude. This leaf
implements the model in pure Python, stdlib only, in
scripts/fuel_feed_system_sizing_logic.py. It pairs with
vehicle-design/sizing/fuel-tank-sizing as the storage side (fuel mass
to tank volume, ullage and capacity fit, which this leaf's feed starts
from) and vehicle-design/sizing/engine-sizing as the demand side (the
engine fuel flow this leaf's line must carry).

## Domain quick reference

- Feed flow: the per-engine feed mass flow m_dot follows the engine
  fuel flow demand at takeoff; the volumetric feed flow is
  Q = m_dot / rho.
- Line velocity: V = m_dot / (rho * A) with A = pi D^2 / 4 for the
  representative feed line of diameter D from the tank outlet to the
  engine-driven pump inlet.
- Reynolds number: Re = V D rho / mu, with mu the fuel dynamic
  viscosity; Re below 2300 is laminar, above it turbulent.
- Darcy friction factor: f = 64/Re for Re < 2300, else the Blasius
  correlation f = 0.3164 Re^-0.25.
- Major line loss: dP_major = f (L/D) rho V^2 / 2 over the line
  length L; it scales linearly with length and with the square of
  velocity.
- Minor loss: dP_minor = K rho V^2 / 2 from the fitting loss
  coefficient sum K (elbows, valves, couplings, filter and flow
  meter); K = 0 gives no minor loss.
- Static head: dP_static = rho g h, the tank outlet height h above
  the pump inlet; a pump above the tank makes h negative and reduces
  the available head.
- NPSH available: NPSHa = (p_source + dP_static - dP_line -
  p_vapor) / (rho g) in metres of fuel column, with p_source the tank
  vent pressure at the operating altitude and dP_line the total major
  plus minor loss. The signed value is returned; negative NPSHa means
  the pump inlet cannot be fed.
- Feed verdict: PASS when NPSHa >= NPSHr (the pump required NPSH),
  else FAIL; the margin is NPSHa - NPSHr. With a boost pump the rise
  dp_boost adds to the source pressure before the NPSH check.
- Boost pump power: P = Q dp_boost / eta from the volumetric feed
  flow, the pressure rise (15 psi class for Jet A at cruise) and the
  pump efficiency.
- Units are SI throughout (kg/s, m, Pa, kg/m3, Pa s); PSI_TO_PA =
  6894.757 converts a boost pump rating.
- FAR 25.955 (fuel flow) and 25.975 (fuel feed context) frame the
  transport category fuel system requirement; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the feed operating point: per-engine feed mass flow m_dot from
   the engine fuel flow demand, fuel density rho, line diameter D and
   length L, viscosity mu and the fitting loss coefficient K.
2. Get the line velocity and area with line_velocity; doubling the
   flow doubles the velocity at fixed diameter.
3. Compute the Reynolds number with reynolds_number and pick the
   friction branch with friction_factor (64/Re laminar, Blasius
   turbulent).
4. Compute the major loss with major_loss_pa and the minor loss with
   minor_loss_pa; the total line loss is their sum.
5. Convert the tank height above the pump with static_head_pa and
   evaluate the NPSH available with npsh_available from the vent
   pressure, static head, line loss and vapor pressure.
6. Check the feed with feed_verdict against the pump required NPSH:
   PASS or FAIL with the margin in metres.
7. For a boost pump at cruise altitude, convert the pressure rise to
   Pa with PSI_TO_PA and get the hydraulic power with boost_pump_power
   from the volumetric feed flow over the efficiency.
8. Run the whole chain in one call with feed_system_summary for the
   complete sizing dict (15 keys: velocity_m_s, area_m2, reynolds,
   friction_factor, major_loss_pa, minor_loss_pa, total_line_loss_pa,
   static_head_pa, npsh_available_m, npsh_required_m, margin_m,
   verdict, npsh_with_boost_m, boost_pressure_rise_pa, boost_power_w),
   then confirm the deterministic checks with the contract test
   scripts/test_fuel_feed_system_sizing.py.

## Worked example

Reference feed line: per-engine flow 0.45 kg/s, Jet A density 800
kg/m3, line diameter 0.05 m, length 12 m, viscosity 2.4e-3 Pa s,
minor loss coefficient 3.0, tank 1.5 m above the pump inlet, tank vent
pressure 24.3 kPa at 40,000 ft, fuel vapor pressure 1.0 kPa, required
NPSH 3.0 m, boost pump rise 15 psi at 0.60 efficiency. Real module
outputs:

- line_velocity(0.45, 800.0, 0.05): velocity_m_s = 0.28648
  (spec anchor 0.2865 m/s), area_m2 = 0.0019635.
- reynolds_number: 4774.65 (turbulent, anchor 4775).
- friction_factor(4774.65): 0.038063 (Blasius, anchor 0.0381).
- major_loss_pa: 299.89 Pa (anchor 299.9); minor_loss_pa(3.0, ...):
  98.48 Pa (anchor 98.5); total_line_loss_pa = 398.37 (anchor 398.4).
- static_head_pa(800.0, 1.5): 11767.98 Pa (anchor 11768.0).
- npsh_available: (24300 + 11767.98 - 398.37 - 1000) / 7845.32 =
  4.4191 m (anchor 4.42 m) against 3.0 m required -> feed_verdict
  PASS, margin 1.4191 m (anchor 1.42 m).
- With the 15 psi boost rise (103421.36 Pa): npsh_available =
  17.6017 m (anchor 17.60 m), margin 14.60 m.
- boost_pump_power(5.625e-4, 103421.36, 0.60): power_w = 96.96 W
  (anchor 97 W); the volumetric feed flow is 0.45/800 = 5.625e-4
  m3/s.
- feed_system_summary(...) returns all 15 keys in one dict with
  verdict PASS.


## Pitfalls

- Confusing the friction branches: Re below 2300 is laminar
  (f = 64/Re exactly) while turbulent flow uses the Blasius
  correlation f = 0.3164 Re^-0.25, with the Blasius branch applying
  at Re = 2300 exactly; the wrong branch changes the loss by
  several times.
- Signing the static head backwards: dP_static = rho g h uses the
  tank height ABOVE the pump inlet, so a pump above the tank makes h
  negative and REDUCES the available head (a pump 1.0 m above the
  tank costs 2.5 m of NPSH against the 1.5 m tank case).
- Quoting NPSH without the boost pump context: the boost pump rise
  adds to the source pressure at cruise altitude (4.42 m plain
  versus 17.60 m with the 15 psi rise in the worked example); the
  verdict must name which configuration it applies to.
- Treating a negative NPSH available as a rounding artifact: the
  signed value is returned on purpose - negative NPSHa means the
  pump inlet cannot be fed at all.
- Ignoring the velocity-squared losses: both major and minor losses
  scale with V^2 (doubling the velocity quadruples them), so a feed
  line sized at cruise flow can starve the pump at the takeoff flow.
- Forgetting the losses live between the tank and the pump: the NPSH
  check subtracts the line losses from the source pressure at the
  engine-driven pump inlet; feed system losses downstream of the
  pump do not belong in NPSHa.
## Verification

- Confirm line_velocity(0.45, 800.0, 0.05) returns velocity 0.28648
  m/s and that doubling the mass flow doubles the velocity.
- Confirm friction_factor(1000.0) equals 64/1000 exactly (laminar)
  and friction_factor(4775.0) equals the Blasius value 0.0381 within
  1e-4; at Re = 2300 exactly the Blasius branch applies.
- Confirm the loss scaling identities: doubling the line length
  doubles the major loss at fixed velocity, and doubling the velocity
  quadruples both the major and the minor loss; minor_loss_pa with
  K = 0 returns 0.0 Pa.
- Confirm npsh_available on the worked case returns 4.4191 m (within
  1e-2 of 4.42 m), that required 5.0 m gives FAIL with margin -0.58 m,
  that the boost case returns 17.60 m within 1e-2, and that a zero
  boost rise leaves the NPSH unchanged.
- Confirm the static head sign: a pump 1.0 m above the tank
  (height -1.0 m) reduces the available NPSH by 2.5 m against the
  1.5 m tank case.
- Confirm boost_pump_power(5.625e-4, 103421.36, 0.60) returns 96.96 W
  within 1e-1, that efficiency 1.0 gives the Q dp product exactly and
  efficiency 0.5 doubles the power.
- Confirm feed_system_summary returns exactly the 15 documented keys
  and that identical inputs give identical dicts (determinism).
- Confirm every non-positive mass flow, density, diameter, length,
  viscosity and friction factor, K below 0, negative source or vapor
  pressure, negative required NPSH, a flow or pressure rise of zero in
  boost_pump_power, efficiency outside (0, 1] and a negative boost
  rise all raise ValueError.
- Run the contract test offline: python3
  scripts/test_fuel_feed_system_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/fuel-tank-sizing: the storage side, fuel mass
  to tank volume with ullage and capacity fit ahead of the feed line.
- vehicle-design/sizing/engine-sizing: thrust and engine fuel flow
  demand that set the per-engine feed flow.
- vehicle-design/sizing/hydraulic-system-sizing: hydraulic, not fuel,
  pump mechanics for the aircraft systems.
- space-systems/subsystems/propellant-tank-sizing: spacecraft
  propellant tank and pressurant sizing, the space analogue.
- propulsion/turbomachinery/rocket-turbopump: rocket LOX and kerosene
  turbopump design, not aircraft feed pumps.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_fuel_feed_system_sizing.py

The test covers the reference feed line contract (velocity 0.2865
m/s, Reynolds 4775, friction 0.0381, major loss 299.9 Pa, minor loss
98.5 Pa, static head 11768.0 Pa, NPSH available 4.42 m PASS with
margin 1.42 m, boost case 17.60 m and boost power 96.96 W), the exact
laminar friction branch and the Blasius bound at Re 4775, the
length-linear and velocity-squared loss identities, the static head
sign, the zero boost rise and zero K minor loss cases, the exact 15
key summary dict, determinism, and ValueError rejection of every
non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR 25.955 and 25.975 are
  regulatory text; the sizing relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

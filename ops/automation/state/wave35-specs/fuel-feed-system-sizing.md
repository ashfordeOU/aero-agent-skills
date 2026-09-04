# Wave-35 leaf spec: fuel-feed-system-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/fuel-feed-system-sizing/
- Pack: sizing. Closest siblings: fuel-tank-sizing (fuel mass to
  volume, ullage, tank capacity fit - the STORAGE side and stops
  there), engine-sizing (thrust and engine SFC fuel flow demand at
  the engine), hydraulic-system-sizing (hydraulic, not fuel, pump
  mechanics), space-systems/subsystems/propellant-tank-sizing
  (spacecraft propellant tank + pressurant), propulsion/turbomachinery/
  rocket-turbopump (rocket LOX/kerosene pumps). Repo-wide grep
  proves ZERO owners for aircraft fuel boost pump, feed line
  pressure loss, engine feed NPSH; the only pump hits are rocket
  turbopump and incidental test context.
- Standards id: far-25 (reference-only; 25.955 fuel flow, 25.975
  feed context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the aircraft fuel feed system between the tank and the engine
at the conceptual level: the per-engine feed mass flow from the
engine fuel flow demand at takeoff, the feed line velocity and
Reynolds number, the line pressure loss from the Darcy friction
factor (laminar 64/Re or turbulent Blasius) with the major loss over
the line length and the minor losses from the fitting loss
coefficient, the static head gain from the tank to the pump, the net
positive suction head available at the engine-driven pump inlet
against the pump required NPSH with the boost pump pressure rise
added at cruise altitude, and the boost pump hydraulic power.
Produces the feed flow, the line pressure loss, the NPSH available
with and without the boost pump, the feed PASS/FAIL verdict, and the
boost pump power that gate the fuel feed system layout.

Does NOT do: tank volume, ullage, tank capacity fit (fuel-tank-
sizing); engine SFC/thrust sizing (engine-sizing); fuel quantity
indication and unusable fuel certification detail; rocket pump
suction-specific-speed and turbopump design (rocket-turbopump);
spacecraft tank pressurant and blowdown (space-systems
propellant-tank-sizing); crossfeed scheduling.

## Model (implement exactly)

Module constants:
- GRAVITY = 9.80665 (m/s2).
- LAMINAR_RE_LIMIT = 2300.0.
- BLASIUS_COEFF = 0.3164.
- K_LAMINAR = 64.0 (f = 64/Re).
- PSI_TO_PA = 6894.757.

Conventions: SI inputs (kg/s, m, Pa, kg/m3, Pa s). The feed line is
a single representative line of length L and diameter D from the
tank outlet to the engine-driven pump inlet. NPSH available is
expressed in metres of fuel column: (p_source + p_static -
p_line - p_vapor) / (rho * g). The source pressure is the tank
vent/ullage pressure at the operating altitude.

Functions (pure stdlib):
- line_velocity(mass_flow_kg_s, density_kg_m3, diameter_m) -> dict
  {velocity_m_s, area_m2} = m_dot / (rho * A), A = pi D^2 / 4.
  ValueErrors on non-positive inputs.
- reynolds_number(velocity_m_s, diameter_m, density_kg_m3,
  viscosity_pa_s) -> Re = V D rho / mu. ValueErrors: velocity < 0,
  D <= 0, rho <= 0, mu <= 0.
- friction_factor(reynolds) -> 64/Re when Re < 2300 else
  0.3164 Re^-0.25. ValueError: Re <= 0.
- major_loss_pa(friction, length_m, diameter_m, density_kg_m3,
  velocity_m_s) -> f (L/D) rho V^2 / 2. ValueErrors on non-positive
  inputs.
- minor_loss_pa(loss_coefficient_k, density_kg_m3, velocity_m_s)
  -> K rho V^2 / 2. ValueErrors: K < 0, density <= 0, velocity < 0.
- static_head_pa(density_kg_m3, height_m) -> rho g h. ValueErrors
  on non-positive density; height may be negative (pump above tank).
- npsh_available(source_pressure_pa, static_head_pa, line_loss_pa,
  vapor_pressure_pa, density_kg_m3) -> (p_src + p_stat - p_line -
  p_vap) / (rho g). ValueErrors: source < 0, line_loss < 0, vapor <
  0, density <= 0. NPSH may be negative (returns the signed value;
  callers treat negative as FAIL).
- feed_verdict(npsh_available_m, npsh_required_m) -> dict
  {margin_m, verdict} = PASS when available >= required else FAIL.
  ValueError: required < 0.
- boost_pump_power(flow_m3_s, pressure_rise_pa, efficiency) -> dict
  {power_w, pressure_rise_pa} = Q dp / eta. ValueErrors: flow <= 0,
  pressure_rise <= 0, efficiency <= 0 or > 1.
- feed_system_summary(mass_flow_kg_s, density_kg_m3, diameter_m,
  length_m, viscosity_pa_s, loss_coefficient_k, tank_height_m,
  source_pressure_pa, vapor_pressure_pa, npsh_required_m,
  boost_pressure_rise_pa, boost_efficiency) -> dict with all keys
  above plus total_line_loss_pa and npsh_with_boost_m.

Identity to test: for Re below 2300 the friction factor equals
64/Re exactly; major loss scales linearly with length and with the
square of velocity.

## Worked example

Reference feed line: per-engine flow 0.45 kg/s, Jet A density 800
kg/m3, line diameter 0.05 m, length 12 m, viscosity 2.4e-3 Pa s,
minor loss coefficient 3.0, tank 1.5 m above the pump inlet, tank
vent pressure 24.3 kPa at 40,000 ft, fuel vapor pressure 1.0 kPa,
required NPSH 3.0 m, boost pump pressure rise 15 psi at 0.60
efficiency.

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- line_velocity: 0.45 / (800 * pi * 0.05^2 / 4) = 0.2865 m/s.
- reynolds: 0.2865 * 0.05 * 800 / 2.4e-3 = 4775 (turbulent).
- friction_factor: 0.3164 * 4775^-0.25 = 0.0381.
- major_loss: 0.0381 * (12/0.05) * 800 * 0.2865^2 / 2 = 299.9 Pa.
- minor_loss: 3.0 * 800 * 0.2865^2 / 2 = 98.5 Pa.
- total line loss = 398.4 Pa.
- static_head: 800 * 9.80665 * 1.5 = 11768.0 Pa.
- npsh_available: (24300 + 11768 - 398.4 - 1000) / (800 * 9.80665)
  = 34669.6 / 7845.32 = 4.42 m; vs 3.0 required -> PASS, margin
  1.42 m.
- With 15 psi boost (103421 Pa): (24300 + 11768 - 398.4 - 1000 +
  103421) / 7845.32 = 138090.6 / 7845.32 = 17.60 m; margin 14.60 m.
- boost_pump_power: Q = 0.45/800 = 5.625e-4 m3/s; 5.625e-4 *
  103421 / 0.60 = 96.96 W (97 W).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: zero/negative diameter, length, density, viscosity,
  flow, K < 0, source/vapor negative, efficiency outside (0,1].
- Laminar branch: Re = 1000 -> f = 0.064 exactly; Re = 4775 ->
  Blasius value 0.0381 within 1e-4.
- Major loss: doubling length doubles the loss at fixed velocity;
  doubling velocity quadruples the major and minor losses.
- Minor loss: K = 0 gives 0.0 Pa.
- NPSH: worked case 4.42 m within 1e-2; required 5.0 m with the
  same line -> FAIL (margin -0.58 m); boost case 17.60 m within
  1e-2; boost pressure rise of 0 -> unchanged NPSH.
- Static head sign: pump 1.0 m above the tank (height -1.0) reduces
  the available NPSH.
- Boost power: worked case 96.96 W within 1e-1; efficiency 1.0
  gives Q dp exactly; efficiency 0.5 doubles power.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-fuel-feed-system-sizing.yaml)

Query 1 (copy verbatim):
  "size the aircraft fuel boost pump and the feed line pressure loss for the engine feed flow at cruise altitude"
  intent: "vehicle-design; fuel boost pump and feed line pressure loss sizing"
  expected_skill: "vehicle-design/sizing/fuel-feed-system-sizing"
Query 2 (copy verbatim):
  "compute the net positive suction head available at the engine driven fuel pump inlet with the tank vent pressure and static head"
  intent: "vehicle-design; engine fuel pump inlet NPSH check"
  expected_skill: "vehicle-design/sizing/fuel-feed-system-sizing"
Task ids: w35-fuel-feed-system-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the aircraft fuel feed
system between the tank and the engine:" and include the outputs in
the Claim. First tag: fuel-feed-system-sizing. Additional tags ONLY:
boost-pump-sizing, feed-line-pressure-loss, engine-feed-npsh,
fuel-pump-power. NEVER single generic words (fuel, feed, pump, line,
pressure, flow, loss, tank). 50-150 words, <=1000 chars, no em dash,
no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): ullage, usable fuel, tank
capacity, wing box volume, fit verdict (fuel-tank-sizing); specific
fuel consumption, thrust lapse (engine-sizing); pressurant mass,
blowdown, tank ullage fraction (space propellant-tank-sizing);
suction specific speed, turbopump, inducer (rocket-turbopump);
actuator flow, accumulator (hydraulic-system-sizing).

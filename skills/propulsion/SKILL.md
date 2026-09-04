---
name: propulsion
description: "Use when a task concerns aircraft or rocket propulsion: guide the router to the propulsion pack: gas-turbine-cycle Brayton, regenerative-cycle regenerator efficiency, real-cycle-effects component losses, turbofan-cycle turbofan parameters, bypass-ratio-trade bypass design, turbofan-off-design part-power behavior, free-turbine power turbine matching, turbine-stage stage velocity triangles, axial-compressor-stage compressor stage, compressor-map operating maps, multi-stage-compressor stacked stages, rocket-sizing rocket sizing, nozzle-design nozzles, propellant-selection propellant trade, ramjet-cycle ideal ramjet performance, ramjet-inlet supersonic inlet starting. Trigger: propulsion, gas turbine, Brayton cycle, regenerator, turbofan, bypass ratio, rocket equation, delta-v, rocket nozzle, area ratio, propellant, axial compressor, compressor map, multi-stage compressor, off-design turbofan, real cycle, free turbine, power turbine, turboshaft, ramjet, ramjet inlet, Kantrowitz, specific thrust, specific impulse."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; router/entry point for the propulsion domain pack"
metadata:
  domain: propulsion
  tags: []
  version: 0.1.0
  author: Aero Agent Skills
---

# Propulsion domain pack (router)

Route here when the task is engine cycle analysis, turbofan
performance parameters, rocket sizing, rocket nozzles, rocket
propellant selection, or axial compressor maps and stages.

## Domain

Propulsion: gas turbine and turbofan thermodynamic cycle analysis
(simple and regenerative Brayton), turbofan bypass design trades,
launch-vehicle rocket sizing with the rocket equation and staging,
rocket nozzle design, rocket propellant selection, and axial
compressor stage and operating-map analysis.

## Sub-skills in this pack

| Path | Skill | When to route to it |
|---|---|---|
| propulsion/gas-turbine-cycle/gas-turbine-cycle | Gas turbine cycle | Brayton thermal efficiency, compressor/turbine exit temperatures, pressure ratio |
| propulsion/gas-turbine-cycle/regenerative-cycle | Regenerative cycle | regenerator effectiveness, regenerative cycle efficiency, optimum pressure ratio, efficiency gain |
| propulsion/gas-turbine-cycle/real-cycle-effects | Real cycle effects | component efficiency, isentropic efficiency, pressure loss, actual exit temperatures, real SFC |
| propulsion/gas-turbine-cycle/combustor-design | Combustor design | stoichiometric fuel-air-ratio, operating fuel-air-ratio, combustion efficiency, heat release, temperature rise, adiabatic flame temperature |
| propulsion/gas-turbine-cycle/afterburner-cycle | Afterburner cycle | afterburner cycle, reheat fuel air ratio, thrust augmentation ratio, reheat temperature rise, dry versus reheat thrust, reheat specific fuel consumption, afterburner nozzle exit velocity |
| propulsion/turbofan/turbofan-cycle | Turbofan cycle | bypass ratio, propulsive efficiency, specific thrust, fan/core mass flow |
| propulsion/turbofan/bypass-ratio-trade | Bypass ratio trade | BPR vs TSFC, thrust split, specific thrust, fan pressure ratio |
| propulsion/turbofan/turbofan-off-design | Turbofan off-design | corrected mass flow, corrected spool speed, altitude thrust, ram drag, cruise SFC, throttle setting |
| propulsion/turboprop/free-turbine | Free turbine | power turbine exit temperature, shaft power, torque, gear ratio, flow function, spool matching |
| propulsion/turboprop/turboprop-cycle | Turboprop cycle | propeller efficiency, static thrust, equivalent shaft power, advance ratio, power and thrust coefficients, SFC on shaft power |
| propulsion/axial-compressor/axial-compressor-stage | Axial compressor stage | velocity triangle, specific work, flow coefficient, degree of reaction, stage pressure ratio, blade loading |
| propulsion/axial-compressor/compressor-map | Compressor map | surge line and margin, operating line, speed lines, corrected flow and speed, choke |
| propulsion/axial-compressor/multi-stage-compressor | Multi-stage compressor | overall pressure ratio, stage count, stage matching, reheat factor, annulus area, corrected speed |
| propulsion/axial-compressor/turbine-stage | Turbine stage | stage loading, flow coefficient, reaction, blade row losses, total-to-total efficiency, velocity triangles |
| propulsion/axial-compressor/turbine-blade-cooling | Turbine blade cooling | turbine blade cooling, cooling effectiveness, coolant flow fraction, film cooling, allowable metal temperature, coolant supply temperature, bleed limit, hot section cooling |
| propulsion/rocket/rocket-sizing | Rocket sizing | rocket equation delta-v, mass ratio, propellant mass, staging |
| propulsion/rocket/rocket-staging | Rocket staging | stage mass ratio allocation, payload fraction, structural index, stage count optimization, per-stage delta-v |
| propulsion/rocket/nozzle-design | Rocket nozzle design | area ratio, exit Mach, mass flow, ideal thrust, expansion |
| propulsion/rocket/propellant-selection | Propellant selection | propellant families, density impulse, mixture ratio, storability, mass fraction |
| propulsion/ramjet/ramjet-cycle | Ramjet cycle | ideal ramjet, fuel air ratio, total temperature ratio, specific thrust, specific impulse |
| propulsion/ramjet/ramjet-inlet | Ramjet inlet | supersonic inlet, Kantrowitz starting, normal shock pressure recovery, diffuser, contraction ratio |
| propulsion/engine-airframe/engine-airframe-integration | Engine-airframe integration | installed thrust, intake momentum drag, nozzle gross thrust, nacelle drag, pylon drag, bleed extraction, thrust-drag bookkeeping |
| propulsion/rocket/thrust-vector-control | Thrust vector control | gimbal deflection, side force, control torque, axial thrust loss, actuator authority, TVC |
| propulsion/rocket/combustion-chamber-design | Combustion chamber design | characteristic velocity, c-star, chamber pressure, throat area, chamber volume, residence time |
| propulsion/turbomachinery/centrifugal-compressor | Centrifugal compressor | impeller tip speed, slip factor, Wiesner, work input coefficient, stage pressure ratio, isentropic efficiency |
| propulsion/combustion/cea-rocket-combustion | Rocket combustion thermochemistry | rocket combustion, adiabatic flame temperature, characteristic velocity, specific impulse, mixture ratio, frozen flow, chamber pressure, thermochemistry, c-star, propellant selection |
| propulsion/rocket/solid-rocket-motor | Solid rocket motor | solid rocket motor, burn rate, chamber pressure, grain geometry, mass flow, thrust, total impulse, c star |
| propulsion/electric/hall-thruster | Hall Thruster | hall thruster, electric propulsion, specific impulse, thrust-to-power, beam current, discharge power, xenon, krypton, propellant mass, delta-v. |
| propulsion/electric/gridded-ion-thruster | Gridded ion thruster | gridded ion thruster, Kaufman thruster, accelerator grid, perveance limit, beam extraction, ion optics |
| propulsion/electric/electrothermal-thruster | Electrothermal thruster | electrothermal thruster, resistojet, arcjet, heated propellant, power to thrust |
| propulsion/rocket/rocket-engine-cycle | Rocket engine cycle | rocket engine cycle, feed cycle, gas-generator cycle, staged combustion, expander cycle, pressure-fed, pump-fed, pump power, turbine power |
| propulsion/rocket/hybrid-rocket-motor | Hybrid rocket motor | hybrid rocket motor, regression rate, oxidizer mass flux, solid fuel grain, oxidizer to fuel ratio, O/F shift, port area, HTPB, hybrid grain |
| propulsion/rocket/cold-gas-thruster | Cold gas thruster | cold gas thruster, nitrogen RCS, choked mass flow, plenum blowdown, total impulse, reaction control thruster sizing, isothermal blowdown time constant |
| propulsion/turbomachinery/rocket-turbopump | Rocket turbopump | rocket turbopump, pump specific speed, suction specific speed, net positive suction head, impeller tip speed, LOX pump sizing, cavitation margin |
| propulsion/rocket/thrust-chamber-cooling | Thrust chamber cooling | thrust chamber cooling, regenerative cooling, Bartz heat transfer, throat heat flux, coolant channel sizing, copper wall limit, film cooling rocket |
| propulsion/rocket/injector-design | Injector design | injector design, unlike doublet, impinging jet atomization, injector pressure drop, momentum flux ratio, orifice flow count |
| propulsion/gas-turbine-cycle/propelling-nozzle | Propelling nozzle | propelling nozzle, convergent jet nozzle, nozzle throat area, choked nozzle regime, gross thrust pressure term |


## Routing guidance

- Brayton/gas-turbine thermodynamics route to the gas-turbine-cycle
  sub-skill; regenerator and recuperator cycle questions route to the
  regenerative-cycle sub-skill.
- Turbofan bypass and efficiency questions route - Hall thruster questions route to the electric hall-thruster sub-skill.
to turbofan-cycle;
  BPR vs TSFC design-trade questions route to bypass-ratio-trade;
  off-design and altitude behavior questions route to
  turbofan-off-design.
- Free-turbine and power-turbine matching questions (shaft power,
  gear ratio, flow function) route to the free-turbine sub-skill;
  propeller-side cycle questions (propeller efficiency, static
  thrust, equivalent shaft power, advance ratio, power and thrust
  coefficients) route to the turboprop-cycle sub-skill.
- Rocket equation, delta-v, staging, and propellant mass questions
  route to the rocket-sizing sub-skill; rocket nozzle questions (area
  ratio, exit Mach, thrust, expansion) route to nozzle-design;
  propellant family, density impulse, and mixture ratio questions
  route to propellant-selection.
- Multi-stage rocket staging questions (per-stage delta-v, stage mass
  ratio and payload fraction allocation, structural index, stage count
  optimization for a target total delta-v) route to the rocket-staging
  sub-skill.
- Axial compressor stage questions (velocity triangles, degree of
  reaction, stage pressure ratio) route to the
  axial-compressor-stage sub-skill; turbine stage questions (stage
  loading, reaction, blade row losses, efficiency) route to the
  turbine-stage sub-skill.
- Compressor map questions (surge margin, operating line, speed
  lines, corrected flow and speed) route to the compressor-map
  sub-skill; multi-stage compressor questions (overall pressure
  ratio, stage count, stage matching, reheat factor, annulus area)
  route to the multi-stage-compressor sub-skill.
- Non-ideal cycle questions (component efficiencies, pressure loss,
  real SFC) route to the real-cycle-effects sub-skill.
- Combustor design questions (stoichiometric and operating
  fuel-air-ratio, combustion efficiency, heat release, temperature
  rise across the combustor, adiabatic flame temperature) route to
  the combustor-design sub-skill.
- Airframe, stability, and certification questions route to their
  domain packs (flight-mechanics, avionics).

- Ideal ramjet, fuel air ratio, and specific impulse questions route to the ramjet ramjet-cycle sub-skill.
- Supersonic inlet starting, Kantrowitz criterion, and diffuser pressure recovery questions route to the ramjet ramjet-inlet sub-skill.
- Installed thrust, intake momentum drag, nacelle and pylon drag, bleed extraction, and thrust-drag bookkeeping questions route to the engine-airframe engine-airframe-integration sub-skill.
- Gimbal deflection, side force, control torque, axial thrust loss, and actuator authority sizing questions route to the rocket thrust-vector-control sub-skill.
- Rocket combustion chamber sizing, characteristic velocity c-star, chamber pressure and throat area, and residence time questions route to the rocket combustion-chamber-design sub-skill.
- Centrifugal compressor impeller tip speed, slip factor, work input, stage pressure ratio, and isentropic efficiency questions route to the turbomachinery centrifugal-compressor sub-skill.
- Rocket combustion thermochemistry, adiabatic flame temperature, characteristic velocity, and ideal specific impulse from propellant and mixture ratio route to the combustion cea-rocket-combustion sub-skill.
- Solid rocket motor ballistics, burn-rate law, chamber pressure equilibrium, grain geometry, mass flow, thrust, and total impulse questions route to the rocket solid-rocket-motor sub-skill.
- Hybrid rocket motor regression rate, oxidizer mass flux, O/F shift, port area, and chamber pressure ballistics questions route to the rocket hybrid-rocket-motor sub-skill.
- Cold gas thruster choked flow, plenum blowdown, and total impulse questions route to the rocket cold-gas-thruster sub-skill.
- Rocket turbopump specific speed, suction performance, and cavitation questions route to the turbomachinery rocket-turbopump sub-skill.

- Rocket thrust chamber regenerative cooling questions (Bartz hot gas coefficient, coolant side convection, wall heat flux and temperature, coolant mass flux for the wall limit, film cooling handoff) route to the rocket thrust-chamber-cooling sub-skill.

- Rocket engine injector element design questions (orifice discharge flow, injection velocity, unlike-doublet momentum flux ratio, fuel and oxidizer orifice counts, per-element flow balance) route to the rocket injector-design sub-skill.

## Install

To install only this pack, copy or symlink each leaf folder above into
your host's skills directory (see README Install for per-host commands).
- Gridded ion thruster and ion-optics perveance questions route to the electric gridded-ion-thruster sub-skill.
- Resistojet and arcjet operating-point and power-to-thrust questions route to the electric electrothermal-thruster sub-skill.
- Liquid engine feed-cycle selection and pump-turbine power balance questions route to the rocket rocket-engine-cycle sub-skill.
- Afterburner reheat fuel-air ratio, dry versus reheat thrust, and augmentation ratio questions route to the gas-turbine-cycle afterburner-cycle sub-skill.
- Turbine blade cooling effectiveness, coolant flow fraction, and film-cooling metal temperature questions route to the axial-compressor turbine-blade-cooling sub-skill.
- Air-breathing propelling nozzle questions (choked or unchoked regime, throat area from design mass flow, gross thrust with the pressure term) route to the gas-turbine-cycle propelling-nozzle sub-skill.

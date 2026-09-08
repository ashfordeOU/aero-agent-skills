---
name: piston-engine-cycle
description: "Use when you must compute the operating point of a reciprocating four-stroke aircraft powerplant for general-aviation propulsion: the air-standard Otto cycle thermal efficiency from the compression ratio and the specific-heat ratio, the four-stroke indicated power from the indicated mean effective pressure, the displacement and the crankshaft speed, the brake power at the mechanical efficiency, and the brake specific fuel consumption from the fuel flow and the brake power. Produces the single-point summary dict with the ideal cycle efficiency, indicated and brake power, BSFC in both reporting units, thermal efficiencies, volumetric fuel flow and the reference-only general-aviation band verdict in one call, the published bands reported and never enforced. Trigger: piston-engine-cycle, air-standard-otto-cycle, compression ratio Otto efficiency, four-stroke engine, mean effective pressure, indicated power, brake power, mechanical efficiency, brake specific fuel consumption, BSFC."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: reciprocating
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: reciprocating
  tags: [piston-engine-cycle, air-standard-otto-cycle, mean-effective-pressure, brake-specific-fuel-consumption, reciprocating-engine-powerplant, four-stroke-powerplant]
  version: 0.1.0
  author: AeroSkills
---

# Piston Engine Cycle (propulsion/reciprocating/piston-engine-cycle)

Use when the task is a reciprocating four-stroke aircraft powerplant
operating-point analysis for general-aviation propulsion: the
air-standard Otto cycle thermal efficiency, the four-stroke indicated
and brake power from the mean effective pressure bookkeeping, and the
brake specific fuel consumption and thermal efficiencies from the fuel
flow. This leaf implements the standard textbook air-standard Otto cycle
and PLAN indicated-power method in pure Python, stdlib only. It pairs
with propulsion/turboprop/free-turbine and
propulsion/turboprop/turboprop-cycle for the other aircraft prime-mover
classes and with propulsion/engine-airframe for installed-behavior
bookkeeping once the powerplant side is fixed.

## Domain quick reference

- Air-standard Otto thermal efficiency: eta = 1 - 1/r^(gamma-1), with r
  the compression ratio (r > 1) and gamma the specific-heat ratio
  (gamma > 1, air-standard default 1.4). This is the ideal efficiency
  ceiling of the spark-ignition cycle, not a real-cycle prediction.
- Isentropic compression temperature ratio: T2/T1 = r^(gamma-1); the
  efficiency identity eta = 1 - 1/(T2/T1) holds exactly.
- Four-stroke indicated power (SI): P_i = IMEP * V_d * (rpm/60)/2, with
  IMEP in Pa and V_d in m3. One power stroke occurs per two crankshaft
  revolutions, so the revolution rate halves in the bookkeeping; the
  bar/L convention gives the identical value.
- Brake power: P_b = P_i * eta_m, with eta_m the mechanical efficiency
  in (0, 1]; eta_m = 1.0 returns the indicated power exactly.
- Brake specific fuel consumption (family shaft-power convention): BSFC
  = m_dot_fuel * 3600 * 1000 / P_b in kg/(kW h), also reported in
  lb/(hp h) through the exact unit bridge
  KG_PER_KWH_PER_LB_PER_HP_HR.
- Thermal efficiencies on the fuel lower heating value: eta_i =
  P_i / (m_dot_fuel * LHV); eta_b = P_b / (m_dot_fuel * LHV) =
  eta_m * eta_i. The air-standard eta_otto is the ideal ceiling and sits
  above eta_b for any real point.
- Volumetric fuel flow: V_dot = m_dot_fuel / rho_fuel, reported in
  m3/s, L/h and US gal/h.
- Reference-only general-aviation band verdict: brake thermal
  efficiency against 0.25 to 0.30 and BSFC against 0.40 to 0.55
  lb/(hp h), published bands for carbureted and fuel injected
  four-stroke aircraft engines. The verdict reports the point's
  position and never enforces it.
- Units are SI throughout except the two reporting conversions (hp,
  lb/(hp h), L/h, US gal/h) that the module carries as named outputs.

## Workflow

1. Fix the operating point: compression ratio and gamma, then compute
   the air-standard Otto cycle thermal efficiency with otto_efficiency
   and the isentropic compression temperature ratio with
   isentropic_temperature_ratio.
2. Compute the four-stroke indicated power from the indicated mean
   effective pressure, the displacement and the crankshaft speed with
   indicated_power.
3. Compute the brake power at the mechanical efficiency with
   brake_power.
4. Compute the brake specific fuel consumption with
   brake_specific_fuel_consumption, convert it to lb/(hp h) with
   bsfc_lb_per_hp_hr, and round-trip back to the fuel flow with
   fuel_flow_from_bsfc when checking a reported BSFC.
5. Compute the indicated and brake thermal efficiencies on the fuel
   lower heating value with indicated_thermal_efficiency and
   brake_thermal_efficiency.
6. Compute the volumetric fuel flow in m3/s, L/h and US gal/h with
   volumetric_fuel_flow.
7. Get the reference-only general-aviation band verdict with
   ga_band_verdict, reporting the point's position without enforcing
   it, or call piston_engine_cycle once for the full single-point
   summary dict that chains steps 1 through 7.
8. Confirm the deterministic checks with the contract test
   scripts/test_piston_engine_cycle.py.

## Worked example

Lycoming O-320 class general-aviation four-stroke flat-four at a cruise
rating: compression ratio r = 8.5, gamma = 1.4 (air standard), IMEP =
9.5e5 Pa (9.5 bar), displacement V_d = 5.4e-3 m3 (5.4 L), crankshaft
speed 2700 rpm, mechanical efficiency eta_m = 0.85, fuel flow m_dot =
7.6e-3 kg/s avgas at the reference density 720 kg/m3 and LHV 43.5 MJ/kg.

- Ideal cycle: eta_otto = 1 - 1/8.5^0.4 = 0.5751531234, within 0.1
  percent of the published 0.575 anchor; the isentropic compression
  temperature ratio is T2/T1 = 8.5^0.4 = 2.3537892242, and
  eta = 1 - 1/(T2/T1) holds exactly.
- Indicated power: P_i = 9.5e5 * 5.4e-3 * (2700/60)/2 = 115425.0 W =
  154.7875 hp.
- Brake power: P_b = 115425.0 * 0.85 = 98111.25 W = 131.5694 hp, about
  82 percent of a 160 hp class rating at the cruise point.
- BSFC: 7.6e-3 * 3600 * 1000 / 98111.25 = 0.2788671024 kg/(kW h) =
  0.4584538370 lb/(hp h), inside the published 0.40 to 0.55 lb/(hp h)
  band.
- Thermal efficiencies on LHV: eta_i = 115425.0/(7.6e-3 * 43.5e6) =
  0.3491379310; eta_b = 98111.25/(7.6e-3 * 43.5e6) = 0.2967672414 =
  eta_i * eta_m exactly, inside the published 0.25 to 0.30 GA
  brake-thermal-efficiency band and below the ideal eta_otto
  (0.2968 < 0.5752), as it must be.
- Volumetric fuel flow: V_dot = 7.6e-3/720 = 1.0555555556e-05 m3/s =
  38.0 L/h = 10.0385 US gal/h, a realistic avgas cruise burn for this
  power class.
- Band verdict: eta_b_position "inside" and bsfc_position "inside" with
  enforced False.

## Verification

- Confirm otto_efficiency(8.5, 1.4) returns 0.5751531234287552, within
  0.1 percent of the published 0.575 anchor.
- Confirm indicated_power(900e3, 4.0e-3, 2700.0) returns 81000.0 W and
  brake_power(81000.0, 0.85) returns 68850.0 W.
- Confirm the isentropic identity: 1 - 1/isentropic_temperature_ratio(
  8.5, 1.4) equals otto_efficiency(8.5, 1.4).
- Confirm fuel_flow_from_bsfc round-trips the fuel flow used to build a
  BSFC value to better than 1e-15 kg/s.
- Confirm every non-positive or non-finite IMEP, displacement, rpm,
  power, fuel flow, density or LHV raises ValueError, and every
  mechanical efficiency at or below 0 or above 1 raises ValueError.
- Confirm ga_band_verdict never raises for an out-of-band point; it
  only rejects non-finite or non-positive inputs.
- Run the contract test offline: python3
  scripts/test_piston_engine_cycle.py (35 tests, deterministic).

## Related leaves

- propulsion/turboprop/free-turbine: the turboshaft power-turbine
  prime-mover slot, the shaft-power alternative to this reciprocating
  engine.
- propulsion/turboprop/turboprop-cycle: propeller (Froude) efficiency
  and shaft-power-to-thrust bookkeeping once a prime mover, turbine or
  reciprocating, delivers shaft power.
- propulsion/engine-airframe: installed thrust and drag bookkeeping for
  the airframe integration once the powerplant operating point is
  fixed.

## Pitfalls

- Reading the air-standard Otto efficiency as the achievable brake
  thermal efficiency: eta_otto (0.5752 in the worked example) is the
  ideal cycle ceiling; the real point's eta_b (0.2968) sits well below
  it because of heat transfer, combustion, pumping and mechanical
  losses the air-standard cycle does not model.
- Forgetting the two-revolutions-per-power-stroke factor: the four-stroke
  indicated power formula divides by two after the rpm/60 conversion
  (one power stroke per two crankshaft turns); omitting it doubles the
  indicated power.
- Treating the BSFC bands as a pass/fail gate: ga_band_verdict and
  piston_engine_cycle carry enforced: False and never raise for an
  out-of-band point; the bands are a published reference range for
  carbureted and fuel injected engines, not a certification limit.
- Mixing the BSFC reporting units: the module's native BSFC is
  kg/(kW h); the lb/(hp h) figure is a separate conversion through
  KG_PER_KWH_PER_LB_PER_HP_HR, not a unit-label swap on the same
  number.
- Applying this leaf to gas-turbine, turboshaft or turboprop
  powerplants: the Otto cycle, IMEP bookkeeping and BSFC bands here are
  specific to reciprocating four-stroke engines; shaft-power turbine
  cycles belong to propulsion/turboprop/free-turbine and
  propulsion/gas-turbine-cycle.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_piston_engine_cycle.py

The test covers the air-standard Otto cycle efficiency and isentropic
temperature ratio at the worked-example compression ratio, the limits
as compression ratio and gamma approach one, the four-stroke indicated
power receipt target and its linear scaling with rpm and displacement,
the brake power receipt and worked-example targets, the brake specific
fuel consumption and its lb/(hp h) conversion with the round trip back
to fuel flow, the indicated and brake thermal efficiencies and their
ordering against the ideal Otto efficiency, the volumetric fuel flow in
three reporting units, the reference-only band verdict at an inside and
an artificial out-of-band point, the full piston_engine_cycle
single-point summary dict and its determinism, and ValueError rejection
of every non-physical input.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 33 (far-33,
  Airworthiness Standards for Aircraft Engines) historically covers
  reciprocating and turbine aircraft engines; the relations above are
  standard air-standard-cycle and PLAN-bookkeeping engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

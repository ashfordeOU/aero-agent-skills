---
name: diesel-cycle
description: "Use when you must compute the operating point of a reciprocating compression-ignition aircraft powerplant: the air-standard Diesel cycle thermal efficiency from the compression ratio, the specific-heat ratio and the cutoff ratio of the constant-pressure heat-addition model, the isentropic compression temperature ratio and state temperatures, the four-stroke indicated power from the indicated mean effective pressure, displacement and crankshaft speed, the brake power at the mechanical efficiency, and the brake specific fuel consumption from the fuel flow and the brake power on Jet-A. Produces the single-point summary dict with the ideal Diesel cycle efficiency, the state temperatures, indicated and brake power, BSFC in both units, thermal efficiencies, volumetric fuel flow and the reference-only compression-ignition band verdict, the bands reported and never enforced. Trigger: diesel-cycle, air-standard-diesel-cycle, compression-ignition, cutoff ratio, jet-a-fuel-cycle."
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
  tags: [diesel-cycle, air-standard-diesel-cycle, compression-ignition, cutoff-ratio, constant-pressure-heat-addition, jet-a-fuel-cycle]
  version: 0.1.0
  author: AeroSkills
---

# Diesel Cycle (propulsion/reciprocating/diesel-cycle)

Use when the task is a reciprocating compression-ignition aircraft
powerplant operating-point analysis, an aircraft diesel: the
air-standard Diesel cycle thermal efficiency under the constant-pressure
heat-addition model, the four-state temperature bookkeeping and heat
addition, the four-stroke indicated and brake power from the mean
effective pressure bookkeeping, and the brake specific fuel consumption
and thermal efficiencies on Jet-A. This leaf implements the standard
textbook air-standard Diesel cycle and PLAN indicated-power method in
pure Python, stdlib only. It pairs with
propulsion/reciprocating/piston-engine-cycle for the spark-ignition
Otto cycle prime mover, with propulsion/turboprop/free-turbine and
propulsion/turboprop/turboprop-cycle for the other aircraft prime-mover
classes, and with propulsion/engine-airframe for installed-behavior
bookkeeping once the powerplant side is fixed.

## Domain quick reference

- Air-standard Diesel thermal efficiency (constant-pressure heat
  addition): eta = 1 - (1/r^(gamma-1)) * ((rc^gamma - 1)/(gamma *
  (rc - 1))), with r the compression ratio (r > 1), gamma the
  specific-heat ratio (gamma > 1, air-standard default 1.4) and rc the
  cutoff ratio (1 < rc <= r; heat addition must end before bottom dead
  center). This is the ideal efficiency ceiling of the
  compression-ignition cycle, not a real-cycle prediction.
- Isentropic compression temperature ratio: T2/T1 = r^(gamma-1); the
  state bookkeeping continues T3 = T2 * rc (constant-pressure heat
  addition 2 to 3) and T4 = T1 * rc^gamma (isentropic expansion 3 to 4
  to V4 = V1, closed form). The temperature-form identity eta =
  1 - (T4 - T1)/(gamma * (T3 - T2)) holds exactly.
- Constant-pressure heat addition per kg of air: q_in = cp * T2 *
  (rc - 1); the cutoff-ratio identity rc = 1 + q_in/(cp * T2) is the
  exact inverse.
- As rc approaches 1 the Diesel efficiency approaches the same-r
  constant-volume Otto ceiling 1 - 1/r^(gamma-1), showing the two
  air-standard cycles share a common limit; for any rc above 1 the
  Diesel efficiency sits below that ceiling.
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
- Thermal efficiencies on the Jet-A lower heating value: eta_i =
  P_i / (m_dot_fuel * LHV); eta_b = P_b / (m_dot_fuel * LHV) =
  eta_m * eta_i. The air-standard eta_diesel is the ideal ceiling and
  sits above eta_b for any real point.
- Volumetric fuel flow: V_dot = m_dot_fuel / rho_fuel, reported in
  m3/s, L/h and US gal/h.
- Reference-only compression-ignition band verdict: brake thermal
  efficiency against 0.3262 to 0.3806 and BSFC against 0.35 to 0.42
  lb/(hp h), published bands for compression-ignition aircraft engines
  of the Centurion/AE300 class. The verdict reports the point's
  position and never enforces it.
- Units are SI throughout except the reporting conversions (hp,
  lb/(hp h), L/h, US gal/h) that the module carries as named outputs.

## Workflow

1. Fix the compression-ignition operating point: compression ratio,
   cutoff ratio and gamma, then compute the air-standard Diesel cycle
   thermal efficiency with diesel_efficiency and the isentropic
   compression temperature ratio with isentropic_temperature_ratio.
2. Compute the four-state temperature bookkeeping with
   cycle_state_temperatures (or the individual
   compression_temperature, cutoff_temperature and
   expansion_temperature steps) and the constant-pressure heat
   addition with heat_addition_j_per_kg, round-tripping to the cutoff
   ratio with cutoff_ratio_from_heat_addition when checking a reported
   heat addition.
3. Compute the four-stroke indicated power from the indicated mean
   effective pressure, the displacement and the crankshaft speed with
   indicated_power.
4. Compute the brake power at the mechanical efficiency with
   brake_power.
5. Compute the brake specific fuel consumption with
   brake_specific_fuel_consumption, convert it to lb/(hp h) with
   bsfc_lb_per_hp_hr, and round-trip back to the fuel flow with
   fuel_flow_from_bsfc when checking a reported BSFC.
6. Compute the indicated and brake thermal efficiencies on the Jet-A
   lower heating value with indicated_thermal_efficiency and
   brake_thermal_efficiency.
7. Compute the volumetric fuel flow in m3/s, L/h and US gal/h with
   volumetric_fuel_flow.
8. Get the reference-only compression-ignition band verdict with
   ci_band_verdict, reporting the point's position without enforcing
   it, or call diesel_cycle once for the full single-point summary
   dict that chains steps 1 through 8.
9. Confirm the deterministic checks with the contract test
   scripts/test_diesel_cycle.py.

## Worked example

Centurion/AE300-class compression-ignition aircraft diesel at a cruise
rating: compression ratio r = 17, cutoff ratio rc = 2.2, gamma = 1.4
(air standard), inlet temperature T1 = 288.15 K, IMEP = 1.8e6 Pa (18
bar), displacement V_d = 2.0e-3 m3 (2.0 L), crankshaft speed 2300 rpm,
mechanical efficiency eta_m = 0.86, fuel flow m_dot = 3.9e-3 kg/s
Jet-A at the reference density 800 kg/m3 and LHV 43.2 MJ/kg.

- Ideal cycle: eta_diesel = 1 - (1/17^0.4) * ((2.2^1.4 - 1)/(1.4 *
  1.2)) = 0.6136842121239982; the isentropic compression temperature
  ratio is T2/T1 = 17^0.4 = 3.1058435015977315.
- State bookkeeping from T1 = 288.15 K: T2 = 894.9488049853862 K, T3 =
  T2 * 2.2 = 1968.8873709678498 K, T4 = T1 * 2.2^1.4 =
  868.9811925471146 K, and the constant-pressure heat addition q_in =
  1005 * T2 * (2.2 - 1) = 1079308.258812376 J/kg (about 1.08 MJ per kg
  of air); the temperature-form identity 1 - (T4 - T1)/(1.4 *
  (T3 - T2)) reproduces eta_diesel exactly, and the cutoff-ratio
  identity rc = 1 + q_in/(cp * T2) round-trips to 2.2 exactly.
- Cutoff-ratio sensitivity at this compression ratio: rc = 2.0 gives
  0.6230571224158052 and rc = 2.5 gives 0.600330985397127, so a longer
  constant-pressure heat addition costs efficiency at fixed r, the
  compression-ignition signature. As rc approaches 1 the efficiency
  approaches 0.6780262755, the same-r constant-volume ceiling.
- Indicated power: P_i = 1.8e6 * 2.0e-3 * (2300/60)/2 = 69000.0 W =
  92.53052418205692 hp.
- Brake power: P_b = 69000.0 * 0.86 = 59340.0 W = 79.57625079656896
  hp.
- BSFC: 3.9e-3 * 3600 * 1000 / 59340.0 = 0.23660262891809908 kg/(kW h)
  = 0.3889716002062689 lb/(hp h), inside the published 0.35 to 0.42
  lb/(hp h) compression-ignition band.
- Thermal efficiencies on LHV: eta_i = 69000.0/(3.9e-3 * 43.2e6) =
  0.40954415954415957; eta_b = 59340.0/(3.9e-3 * 43.2e6) =
  0.3522079772079772 = eta_i * eta_m exactly, inside the published CI
  brake-thermal-efficiency window 0.3261878583333333 to
  0.3805525013888889 and below the ideal eta_diesel (0.35221 <
  0.61368), as it must be.
- Volumetric fuel flow: V_dot = 3.9e-3/800 = 4.875e-06 m3/s = 17.55
  L/h = 4.636219518885506 US gal/h.
- Band verdict: eta_b_position "inside" and bsfc_position "inside"
  with enforced False.

## Verification

- Confirm diesel_efficiency(17.0, 2.2, 1.4) returns
  0.6136842121239982, and that efficiency falls as the cutoff ratio
  grows at fixed compression ratio (0.6230571224 at rc 2.0, 0.6003309854
  at rc 2.5).
- Confirm isentropic_temperature_ratio(17.0, 1.4) returns
  3.1058435015977315 and compression_temperature(288.15, 17.0, 1.4)
  returns 894.9488049853862 K.
- Confirm heat_addition_j_per_kg and cutoff_ratio_from_heat_addition
  round-trip the cutoff ratio to better than 1e-13 relative.
- Confirm indicated_power(1.8e6, 2.0e-3, 2300.0) returns 69000.0 W and
  brake_power(69000.0, 0.86) returns 59340.0 W.
- Confirm fuel_flow_from_bsfc round-trips the fuel flow used to build
  a BSFC value to better than 1e-15 kg/s.
- Confirm every non-positive or non-finite compression ratio, cutoff
  ratio, gamma, temperature, IMEP, displacement, rpm, power, fuel
  flow, density or LHV raises ValueError, that every mechanical
  efficiency at or below 0 or above 1 raises ValueError, and that a
  cutoff ratio above the compression ratio raises ValueError.
- Confirm ci_band_verdict never raises for an out-of-band point; it
  only rejects non-finite or non-positive inputs.
- Run the contract test offline: python3
  scripts/test_diesel_cycle.py (deterministic, no network).

## Related leaves

- propulsion/reciprocating/piston-engine-cycle: the spark-ignition
  Otto cycle reciprocating prime mover, the constant-volume
  heat-addition sibling of this constant-pressure Diesel cycle at the
  same station.
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

- Reading the air-standard Diesel efficiency as the achievable brake
  thermal efficiency: eta_diesel (0.6137 in the worked example) is the
  ideal cycle ceiling; the real point's eta_b (0.3522) sits well below
  it because of heat transfer, combustion, pumping and mechanical
  losses the air-standard cycle does not model.
- Confusing the cutoff ratio with the compression ratio: rc = V3/V2 =
  T3/T2 describes the constant-pressure heat-addition stroke and must
  satisfy 1 < rc <= r; passing a cutoff ratio above the compression
  ratio raises ValueError because the heat addition cannot outlast the
  power stroke back to bottom dead center.
- Forgetting the two-revolutions-per-power-stroke factor: the
  four-stroke indicated power formula divides by two after the
  rpm/60 conversion (one power stroke per two crankshaft turns);
  omitting it doubles the indicated power.
- Treating the BSFC and brake-thermal-efficiency bands as a pass/fail
  gate: ci_band_verdict and diesel_cycle carry enforced: False and
  never raise for an out-of-band point; the bands are a published
  reference range for compression-ignition aircraft engines, not a
  certification limit.
- Mixing the BSFC reporting units: the module's native BSFC is
  kg/(kW h); the lb/(hp h) figure is a separate conversion through
  KG_PER_KWH_PER_LB_PER_HP_HR, not a unit-label swap on the same
  number.
- Applying this leaf to spark-ignition, gas-turbine, turboshaft or
  turboprop powerplants: the constant-pressure Diesel cycle, IMEP
  bookkeeping and CI bands here are specific to compression-ignition
  reciprocating engines; the Otto cycle belongs to
  propulsion/reciprocating/piston-engine-cycle and shaft-power turbine
  cycles belong to propulsion/turboprop/free-turbine and
  propulsion/gas-turbine-cycle.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_diesel_cycle.py

The test covers the air-standard Diesel cycle efficiency at the
worked-example compression and cutoff ratios, the cutoff-ratio
sensitivity ordering and the limits as the cutoff ratio approaches the
same-r Otto ceiling and as gamma or compression ratio approach one,
the four-state temperature bookkeeping and the temperature-form and
heat-rejection-form efficiency identities, the constant-pressure heat
addition and its cutoff-ratio round trip, the four-stroke indicated
power receipt target and its linear scaling with rpm and displacement,
the brake power receipt and worked-example targets, the brake specific
fuel consumption and its lb/(hp h) conversion with the round trip back
to fuel flow, the indicated and brake thermal efficiencies and their
ordering against the ideal Diesel efficiency, the volumetric fuel flow
in three reporting units, the reference-only band verdict at an inside
and an artificial out-of-band point, the full diesel_cycle
single-point summary dict and its determinism, and ValueError
rejection of every non-physical input including a cutoff ratio above
the compression ratio.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 33 (far-33,
  Airworthiness Standards for Aircraft Engines) historically covers
  reciprocating and turbine aircraft engines, including certified
  compression-ignition aircraft diesels; the relations above are
  standard air-standard-cycle and PLAN-bookkeeping engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

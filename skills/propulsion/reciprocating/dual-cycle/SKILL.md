---
name: dual-cycle
description: "Use when you must compute the operating point of a reciprocating high-speed compression-ignition aircraft powerplant: the air-standard dual-cycle thermal efficiency from the compression ratio, the specific-heat ratio, the pressure ratio of the constant-volume heat-addition phase and the cutoff ratio of the constant-pressure phase, the isentropic compression temperature ratio and state temperatures, the four-stroke indicated and brake power from the indicated mean effective pressure, displacement, crankshaft speed and mechanical efficiency, and the brake specific fuel consumption on Jet-A. Produces the single-point summary dict with the dual-cycle efficiency, heat additions, mean effective pressure, BSFC in both units, thermal efficiencies, volumetric fuel flow and the reference-only compression-ignition band verdict, reported and never enforced. Trigger: dual-cycle, air-standard-dual-cycle, sabathe-cycle, limited-pressure-cycle, mixed-heat-addition, pressure-ratio-of-heat-addition."
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
  tags: [dual-cycle, air-standard-dual-cycle, sabathe-cycle, limited-pressure-cycle, mixed-heat-addition, pressure-ratio-of-heat-addition]
  version: 0.1.0
  author: AeroSkills
---

# Dual Cycle (propulsion/reciprocating/dual-cycle)

Use when the task is a reciprocating high-speed compression-ignition
aircraft powerplant operating-point analysis, an aircraft diesel of the
direct-injection class: the air-standard dual (Sabathe / limited-pressure)
cycle thermal efficiency under the mixed constant-volume-then-constant-
pressure heat-addition model, the five-state temperature bookkeeping and
both heat additions, the ideal-cycle mean effective pressure, the
four-stroke indicated and brake power from the mean effective pressure
bookkeeping, and the brake specific fuel consumption and thermal
efficiencies on Jet-A. This leaf implements the standard textbook
air-standard dual cycle and PLAN indicated-power method in pure Python,
stdlib only. It pairs with propulsion/reciprocating/piston-engine-cycle for
the spark-ignition Otto cycle prime mover (the rho to 1 limit of this
model), with propulsion/reciprocating/diesel-cycle for the pure
constant-pressure Diesel cycle prime mover (the alpha to 1 limit of this
model), with propulsion/turboprop/free-turbine and
propulsion/turboprop/turboprop-cycle for the other aircraft prime-mover
classes, and with propulsion/engine-airframe for installed-behavior
bookkeeping once the powerplant side is fixed.

## Domain quick reference

- Air-standard dual thermal efficiency (mixed heat addition): eta = 1 -
  (1/r^(gamma-1)) * ((alpha*rho^gamma - 1)/((alpha - 1) + gamma*alpha*
  (rho - 1))), with r the compression ratio (r > 1), gamma the
  specific-heat ratio (gamma > 1, air-standard default 1.4), alpha the
  pressure ratio of the constant-volume heat-addition phase (alpha >= 1,
  alpha = P3/P2) and rho the cutoff ratio of the constant-pressure phase
  (rho = V4/V3 = T4/T3, 1 < rho <= r; heat addition must end before bottom
  dead center). This is the ideal efficiency ceiling of the mixed
  heat-addition cycle, not a real-cycle prediction.
- Limit identities: alpha to 1 recovers the air-standard Diesel closed form
  owned by propulsion/reciprocating/diesel-cycle exactly, and rho to 1
  recovers the air-standard Otto closed form owned by
  propulsion/reciprocating/piston-engine-cycle exactly, so the dual ceiling
  interpolates between the two landed siblings' ceilings at the same
  compression ratio.
- Isentropic compression temperature ratio: T2/T1 = r^(gamma-1); the state
  bookkeeping continues T3 = T2 * alpha (constant-volume heat addition 2 to
  3), T4 = T3 * rho (constant-pressure heat addition 3 to 4) and T5 = T1 *
  alpha * rho^gamma (isentropic expansion 4 to 5 to V5 = V1, closed form).
  The temperature-form identity eta = 1 - q_out/q_in holds exactly.
- Mixed heat addition per kg of air: q23 = (cp/gamma) * T2 * (alpha - 1)
  across the constant-volume phase, q34 = cp * T2 * alpha * (rho - 1)
  across the constant-pressure phase, q_in = q23 + q34; the alpha and rho
  round trips 1 + q23/(cv * T2) and 1 + q34/(cp * T3) are the exact
  inverses.
- Constant-volume heat rejection 5 to 1: q_out = (cp/gamma) * (T5 - T1).
- Ideal-cycle mean effective pressure: MEP = eta * q_in/(v1 - v2), with v1
  = R * T1/p1, returned in Pa; MEP is exactly linear in the state-1
  pressure p1.
- Four-stroke indicated power (SI): P_i = IMEP * V_d * (rpm/60)/2, with
  IMEP in Pa and V_d in m3. One power stroke occurs per two crankshaft
  revolutions, so the revolution rate halves in the bookkeeping; the
  bar/L convention gives the identical value.
- Brake power: P_b = P_i * eta_m, with eta_m the mechanical efficiency in
  (0, 1]; eta_m = 1.0 returns the indicated power exactly.
- Brake specific fuel consumption (family shaft-power convention): BSFC =
  m_dot_fuel * 3600 * 1000 / P_b in kg/(kW h), also reported in lb/(hp h)
  through the exact unit bridge KG_PER_KWH_PER_LB_PER_HP_HR.
- Thermal efficiencies on the Jet-A lower heating value: eta_i =
  P_i / (m_dot_fuel * LHV); eta_b = P_b / (m_dot_fuel * LHV) = eta_m *
  eta_i. The air-standard eta_dual is the ideal ceiling and sits above
  eta_b for any real point.
- Volumetric fuel flow: V_dot = m_dot_fuel / rho_fuel, reported in m3/s,
  L/h and US gal/h.
- Reference-only compression-ignition band verdict: brake thermal
  efficiency against 0.3262 to 0.3806 and BSFC against 0.35 to 0.42
  lb/(hp h), the same published band class the diesel sibling's worked
  example reports for a compression-ignition aircraft engine of the
  Centurion/AE300 class. The verdict reports the point's position and
  never enforces it.
- Units are SI throughout except the reporting conversions (hp, lb/(hp h),
  L/h, US gal/h) that the module carries as named outputs.

## Workflow

1. Fix the high-speed compression-ignition operating point: compression
   ratio, pressure ratio of the constant-volume phase, cutoff ratio of the
   constant-pressure phase and gamma, then compute the air-standard
   dual-cycle thermal efficiency with dual_efficiency and the isentropic
   compression temperature ratio with isentropic_temperature_ratio.
2. Compute the five-state temperature bookkeeping with
   cycle_state_temperatures (or the individual compression_temperature,
   cv_phase_temperature, cp_phase_temperature and expansion_temperature
   steps), the constant-volume heat addition with
   cv_heat_addition_j_per_kg, the constant-pressure heat addition with
   cp_heat_addition_j_per_kg, the total mixed heat addition with
   heat_addition_j_per_kg, and the constant-volume heat rejection with
   heat_rejection_j_per_kg.
3. Compute the ideal-cycle mean effective pressure from the state-1
   pressure and temperature with mean_effective_pressure.
4. Compute the four-stroke indicated power from the indicated mean
   effective pressure, the displacement and the crankshaft speed with
   indicated_power.
5. Compute the brake power at the mechanical efficiency with
   brake_power.
6. Compute the brake specific fuel consumption with
   brake_specific_fuel_consumption, convert it to lb/(hp h) with
   bsfc_lb_per_hp_hr, and round-trip back to the fuel flow with
   fuel_flow_from_bsfc when checking a reported BSFC.
7. Compute the indicated and brake thermal efficiencies on the Jet-A
   lower heating value with indicated_thermal_efficiency and
   brake_thermal_efficiency.
8. Compute the volumetric fuel flow in m3/s, L/h and US gal/h with
   volumetric_fuel_flow.
9. Get the reference-only compression-ignition band verdict with
   ci_band_verdict, reporting the point's position without enforcing it,
   or call dual_cycle once for the full single-point summary dict that
   chains steps 1 through 9.
10. Confirm the deterministic checks with the contract test
    scripts/test_dual_cycle.py.

## Worked example

High-speed direct-injection compression-ignition aircraft diesel at a
cruise rating: compression ratio r = 16, pressure ratio of the
constant-volume phase alpha = 1.35, cutoff ratio of the constant-pressure
phase rho = 2.0, gamma = 1.4 (air standard), inlet temperature T1 = 288.15
K, state-1 pressure p1 = 1.5e5 Pa, IMEP = 1.8e6 Pa (18 bar), displacement
V_d = 2.0e-3 m3 (2.0 L), crankshaft speed 2300 rpm, mechanical efficiency
eta_m = 0.86, fuel flow m_dot = 3.9e-3 kg/s Jet-A at the reference density
800 kg/m3 and LHV 43.2 MJ/kg.

- Ideal cycle: eta_dual = 1 - (1/16^0.4) * ((1.35 * 2.0^1.4 - 1)/((1.35 -
  1) + 1.4 * 1.35 * (2.0 - 1))) = 0.622604338055, sitting between the
  same-r bounds 0.613804581712 (Diesel closed form at cutoff 2.0, the pure
  constant-pressure limit alpha = 1) and 0.670123022307 (the constant-
  volume ceiling 1 - 1/16^0.4), the interpolation identity; the isentropic
  compression temperature ratio is T2/T1 = 16^0.4 = 3.03143313302.
- State bookkeeping from T1 = 288.15 K: T2 = 873.50745728 K, T3 = T2 *
  1.35 = 1179.23506733 K (end of the constant-volume phase), T4 = T3 *
  2.0 = 2358.47013466 K (end of the constant-pressure phase), T5 = T1 *
  1.35 * 2.0^1.4 = 1026.58375212 K (end of the isentropic expansion back
  to V5 = V1), and the mixed heat addition q23 = 219468.748642 J/kg across
  the constant-volume phase plus q34 = 1185131.24266 J/kg across the
  constant-pressure phase gives q_in = 1404599.99131 J/kg (about 1.40 MJ
  per kg of air); the temperature-form identity 1 - q_out/q_in with q_out
  = 530089.943487 J/kg reproduces eta_dual to 1e-12 relative, and the
  alpha and rho round trips return 1.35 and 2.0 to 1e-15 relative.
- Mean effective pressure: MEP = eta_dual * q_in/(v1 - v2) =
  1691937.3034 Pa (about 16.9 bar) at the 1.5 bar state-1 pressure, the
  order of magnitude of the 18 bar IMEP documented input; doubling the
  state-1 pressure doubles the MEP to 3383874.60681 Pa, verified to
  1e-12 relative (MEP is exactly linear in p1).
- Pressure-ratio sensitivity at r = 17, rho = 2.2 (the receipt magnitudes):
  alpha 1.2 gives 0.619491257553 and alpha 2.0 gives 0.628441566104, so a
  longer constant-volume phase raises efficiency toward the constant-
  volume ceiling at fixed r and rho, the dual-cycle signature that
  separates this leaf from the pure constant-pressure sibling.
- Cutoff-ratio sensitivity at the worked point: rho 1.8 gives
  0.632550215211 and rho 2.2 gives 0.613014625635, so a longer
  constant-pressure phase costs efficiency at fixed r and alpha, the
  compression-ignition signature.
- Indicated power: P_i = 1.8e6 * 2.0e-3 * (2300/60)/2 = 69000.0 W =
  92.5305241821 hp.
- Brake power: P_b = 69000.0 * 0.86 = 59340.0 W = 79.5762507966 hp.
- BSFC: m_dot * 3600 * 1000 / P_b = 0.236602628918 kg/(kW h) =
  0.388971600206 lb/(hp h), inside the published 0.35 to 0.42 lb/(hp h)
  compression-ignition band.
- Thermal efficiencies on LHV: eta_i = 69000.0/(3.9e-3 * 43.2e6) =
  0.409544159544; eta_b = 59340.0/(3.9e-3 * 43.2e6) = 0.352207977208 =
  eta_i * eta_m exactly, inside the published CI brake-thermal-efficiency
  window 0.3261878583333333 to 0.3805525013888889 and below the ideal
  eta_dual (0.35221 < 0.62260), as it must be.
- Volumetric fuel flow: V_dot = 3.9e-3/800 = 4.875e-06 m3/s = 17.55 L/h =
  4.63621951889 US gal/h.
- Band verdict: eta_b_position "inside" and bsfc_position "inside" with
  enforced False.

## Verification

- Confirm dual_efficiency(16.0, 1.35, 2.0, 1.4) returns 0.622604338055,
  and that efficiency rises as the pressure ratio grows at fixed r and
  rho (r = 17, rho = 2.2: 0.619491257553 at alpha 1.2, 0.628441566104 at
  alpha 2.0) while it falls as the cutoff ratio grows at fixed r and
  alpha (r = 16, alpha = 1.35: 0.632550215211 at rho 1.8, 0.613014625635
  at rho 2.2).
- Confirm the alpha to 1 limit reproduces the Diesel closed form
  0.613684212124 at r = 17, rho = 2.2, and the rho to 1 limit reproduces
  the constant-volume Otto ceiling 0.678026275475 at the same r, so the
  dual ceiling sits strictly between the two landed sibling ceilings at
  every interior alpha and rho.
- Confirm isentropic_temperature_ratio(16.0, 1.4) returns 3.03143313302
  and compression_temperature(288.15, 16.0, 1.4) returns 873.50745728 K.
- Confirm cv_heat_addition_j_per_kg and cp_heat_addition_j_per_kg round
  trip the pressure ratio and cutoff ratio to better than 1e-9 relative,
  and that the temperature-form identity 1 - q_out/q_in reproduces
  dual_efficiency to 1e-10 relative.
- Confirm mean_effective_pressure(288.15, 1.5e5, 16.0, 1.35, 2.0) returns
  1691937.3034 Pa and doubling the state-1 pressure doubles the MEP.
- Confirm indicated_power(1.8e6, 2.0e-3, 2300.0) returns 69000.0 W and
  brake_power(69000.0, 0.86) returns 59340.0 W.
- Confirm fuel_flow_from_bsfc round-trips the fuel flow used to build a
  BSFC value to better than 1e-15 kg/s.
- Confirm every non-positive or non-finite compression ratio, pressure
  ratio, cutoff ratio, gamma, temperature, pressure, IMEP, displacement,
  rpm, power, fuel flow, density or LHV raises ValueError, that every
  mechanical efficiency at or below 0 or above 1 raises ValueError, and
  that a cutoff ratio above the compression ratio raises ValueError.
- Confirm ci_band_verdict never raises for an out-of-band point; it only
  rejects non-finite or non-positive inputs.
- Run the contract test offline: python3 scripts/test_dual_cycle.py
  (deterministic, no network).

## Related leaves

- propulsion/reciprocating/piston-engine-cycle: the spark-ignition Otto
  cycle reciprocating prime mover, the pure constant-volume heat-addition
  sibling that this leaf's rho to 1 limit recovers exactly.
- propulsion/reciprocating/diesel-cycle: the compression-ignition Diesel
  cycle reciprocating prime mover, the pure constant-pressure
  heat-addition sibling that this leaf's alpha to 1 limit recovers
  exactly.
- propulsion/turboprop/free-turbine: the turboshaft power-turbine
  prime-mover slot, the shaft-power alternative to this reciprocating
  engine.
- propulsion/turboprop/turboprop-cycle: propeller (Froude) efficiency and
  shaft-power-to-thrust bookkeeping once a prime mover, turbine or
  reciprocating, delivers shaft power.
- propulsion/engine-airframe: installed thrust and drag bookkeeping for
  the airframe integration once the powerplant operating point is fixed.

## Pitfalls

- Reading the air-standard dual efficiency as the achievable brake
  thermal efficiency: eta_dual (0.6226 in the worked example) is the
  ideal cycle ceiling; the real point's eta_b (0.3522) sits well below it
  because of heat transfer, combustion, pumping and mechanical losses the
  air-standard cycle does not model.
- Confusing the pressure ratio alpha with the cutoff ratio rho: alpha =
  P3/P2 = T3/T2 describes the constant-volume heat-addition phase
  (alpha >= 1) and rho = V4/V3 = T4/T3 describes the constant-pressure
  heat-addition phase (1 < rho <= r); passing a cutoff ratio above the
  compression ratio raises ValueError because the heat addition cannot
  outlast the power stroke back to bottom dead center.
- Treating the alpha = 1 or rho = 1 boundary as a claimed operating mode:
  those exact limits are test bounds that reproduce the Diesel and Otto
  sibling ceilings; this leaf's own claim is the interior mixed
  heat-addition case, alpha > 1 and rho > 1.
- Forgetting the two-revolutions-per-power-stroke factor: the four-stroke
  indicated power formula divides by two after the rpm/60 conversion (one
  power stroke per two crankshaft turns); omitting it doubles the
  indicated power.
- Treating the BSFC and brake-thermal-efficiency bands as a pass/fail
  gate: ci_band_verdict and dual_cycle carry enforced: False and never
  raise for an out-of-band point; the bands are a published reference
  range for compression-ignition aircraft engines, not a certification
  limit.
- Mixing the BSFC reporting units: the module's native BSFC is kg/(kW h);
  the lb/(hp h) figure is a separate conversion through
  KG_PER_KWH_PER_LB_PER_HP_HR, not a unit-label swap on the same number.
- Applying this leaf to spark-ignition, pure constant-pressure Diesel,
  gas-turbine, turboshaft or turboprop powerplants: the mixed
  heat-addition dual cycle, IMEP bookkeeping and CI bands here are
  specific to high-speed direct-injection compression-ignition
  reciprocating engines; the pure Otto cycle belongs to
  propulsion/reciprocating/piston-engine-cycle, the pure Diesel cycle
  belongs to propulsion/reciprocating/diesel-cycle, and shaft-power
  turbine cycles belong to propulsion/turboprop/free-turbine and
  propulsion/gas-turbine-cycle.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_dual_cycle.py

The test covers the air-standard dual-cycle efficiency at the
worked-example and receipt compression, pressure and cutoff ratios, the
pressure-ratio and cutoff-ratio sensitivity orderings, the alpha to 1 and
rho to 1 limits that recover the Diesel and Otto sibling ceilings and the
gamma to 1 limit that approaches zero, the five-state temperature
bookkeeping and the temperature-form efficiency identity, the constant-
volume and constant-pressure heat additions with their round trips and the
constant-volume heat rejection, the ideal-cycle mean effective pressure
and its linear scaling with the state-1 pressure, the four-stroke
indicated power receipt target and its linear scaling with rpm and
displacement, the brake power receipt and worked-example targets, the
brake specific fuel consumption and its lb/(hp h) conversion with the
round trip back to fuel flow, the indicated and brake thermal efficiencies
and their ordering against the ideal dual efficiency, the volumetric fuel
flow in three reporting units, the reference-only band verdict at an
inside and an artificial out-of-band point, the full dual_cycle
single-point summary dict and its determinism, and ValueError rejection of
every non-physical input including a cutoff ratio above the compression
ratio and a pressure ratio below 1.

## Compliance

- Standards referenced, not reproduced: 14 CFR Part 33 (far-33,
  Airworthiness Standards for Aircraft Engines) historically covers
  reciprocating and turbine aircraft engines, including certified
  compression-ignition aircraft diesels of the high-speed
  direct-injection class; the relations above are standard
  air-standard-cycle and PLAN-bookkeeping engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

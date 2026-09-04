# Wave-36 leaf spec: cabin-outflow-valve-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/cabin-outflow-valve-sizing/
- Pack: sizing. Closest siblings: environmental-control-sizing (owns the
  pressurization SCHEDULE: cabin altitude regimes, differential pressure
  clamp, pack mass flow at cruise; its worked outputs m_pack =
  3.156617 kg/s, p_cab = 75262 Pa, p_amb(39000 ft) = 19677 Pa are INPUTS
  here; "outflow valve"/"pressure relief"/"valve area" have zero hits in
  its description and repo-wide), avionics-bay-cooling-sizing (equipment
  cooling, unrelated). Whole-tree grep: no leaf sizes the outflow /
  pressure-relief valve flow area. ZERO owners for the hardware sizing
  step.
- Standards id: far-25 (reference-only; 25.841 pressurization cabin
  context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the cabin outflow and pressure-relief valve effective area at the
conceptual level from the choked-flow mass-flux relation G = p
sqrt(gamma/(R T)) (2/(gamma+1))^((gamma+1)/(2(gamma-1))): size the
outflow valve effective area to pass the governing pack inflow at the
cruise cabin pressure (A = m_dot / G), and size the pressure-relief
valve effective area to dump the same pack flow at the differential
pressure clamp ceiling. Produces the choked-flow mass flux, the effective
area and equivalent diameter for the outflow and relief cases, and a fit
verdict against a nominal valve diameter limit.

Does NOT do: cabin heat load and pack flow demand (environmental-control-
sizing computes m_pack); the pressurization schedule and cabin altitude
regimes (environmental-control-sizing); valve actuator control laws
(out of scope).

## Model (implement exactly)

Module constants:
- GAMMA_AIR = 1.4.
- R_AIR = 287.0 (J/kg K).
- T_CABIN_DEFAULT = 288.0 (K, cabin temperature at the sizing point).
- P_AMB_39000FT = 19677.0 (Pa, ISA ambient at 39,000 ft; input anchor).
- P_AMB_50000FT = 11597.0 (Pa, ISA ambient at 50,000 ft; relief anchor).
- DP_CLAMP_DEFAULT = 61363.0 (Pa, 8.9 psi differential pressure clamp).
- CRITICAL_RATIO = (2/(gamma+1))^(gamma/(gamma-1)) = 0.528282
  (0.528, choked-flow threshold).

Conventions: choked flow only (pressure ratio p_amb/p_cab < 0.528);
effective area in m2; mass flow in kg/s.

Functions (pure stdlib):
- choked_mass_flux(p_cab_pa, t_cabin_k = T_CABIN_DEFAULT) -> float
  kg/(m2 s) = p * sqrt(gamma/(R T)) * (2/(gamma+1))^((gamma+1)/
  (2(gamma-1))). ValueErrors: p <= 0; t <= 0.
- is_choked(p_cab_pa, p_amb_pa) -> bool (p_amb/p_cab < CRITICAL_RATIO).
  ValueErrors: p_cab <= 0; p_amb < 0.
- valve_area(m_dot_kg_s, p_cab_pa, t_cabin_k = T_CABIN_DEFAULT) ->
  dict {area_m2, diameter_m} = m_dot / G; D = sqrt(4A/pi). ValueErrors:
  m_dot <= 0; p_cab <= 0; t <= 0.
- outflow_valve_sizing(m_pack_kg_s, p_cab_pa, p_amb_pa,
  max_valve_diameter_m, t_cabin_k = T_CABIN_DEFAULT) -> dict with
  choked flag (ValueError if not choked), mass flux, area, diameter,
  fit verdict (PASS when diameter <= max).
- relief_valve_sizing(m_pack_kg_s, p_amb_pa, dp_clamp_pa =
  DP_CLAMP_DEFAULT, max_valve_diameter_m, t_cabin_k = T_CABIN_DEFAULT)
  -> dict with p_cab = p_amb + dp_clamp, choked check vs the clamp
  ceiling, flux, area, diameter, fit verdict.

Identity to test: the choked-flow flux formula with gamma 1.4 matches
the closed form G/(p sqrt(gamma/(R T))) == 0.578704 within 1e-6;
area round trip through D == pi D^2/4.

## Worked example

Reference installation: cruise at 39,000 ft with p_cab = 75262 Pa
(8000 ft cabin), pack inflow 3.156617 kg/s; relief case at 50,000 ft
with the 8.9 psi (61363 Pa) differential clamp; nominal valve diameter
limit 0.16 m.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- cruise pressure ratio 19677/75262 = 0.2614 < 0.528 -> choked.
- flux = 75262 * 0.0041155 * 0.578704 = 179.2499 kg/(m2 s); area =
  3.156617/179.2499 = 0.017610 m2; diameter = 0.1497 m (149.7 mm);
  fit verdict vs 0.16 m: PASS.
- relief p_cab = 11597 + 61363 = 72960 Pa; ratio 11597/72960 = 0.1590
  < 0.528 -> choked; flux = 72960*0.0041155*0.578704 = 173.7672;
  area = 3.156617/173.7672 = 0.018166 m2; diameter = 0.1521 m.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: m_dot <= 0; p_cab <= 0; unchoked outflow case (e.g. p_amb/
  p_cab 0.7) raises; t <= 0.
- is_choked truth table: 0.2614 -> True; 0.7 -> False; 0.528 -> False
  (threshold strict).
- Flux identity: flux/(p*sqrt(gamma/(R T))) == 0.578704 within 1e-6.
- Outflow area 0.017610 within 1e-5; diameter 0.1497 within 1e-3;
  verdict PASS vs 0.16 and FAIL vs 0.14.
- Relief area 0.018166 within 1e-5; diameter 0.1521 within 1e-3.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-cabin-outflow-valve-sizing.yaml)

Query 1 (copy verbatim):
  "size the cabin outflow valve effective area to pass the pack inflow at the cruise cabin pressure"
  intent: "vehicle-design; outflow valve choked flow area at cruise differential"
  expected_skill: "vehicle-design/sizing/cabin-outflow-valve-sizing"
Query 2 (copy verbatim):
  "compute the pressure relief valve area that dumps pack flow at the 8.9 psi cabin differential pressure clamp"
  intent: "vehicle-design; pressure relief valve choked area at the differential clamp"
  expected_skill: "vehicle-design/sizing/cabin-outflow-valve-sizing"
Task ids: w36-cabin-outflow-valve-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the cabin outflow valve:"
and include the outputs in the Claim. First tag:
cabin-outflow-valve-sizing. Additional tags ONLY: outflow-valve-area,
pressure-relief-valve-sizing, cabin-choked-flow, pressurization-valve,
differential-pressure-clamp. NEVER single generic words (valve, outflow,
pressure, relief, cabin, flow, area, pressurization). 50-150 words,
<=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): cabin altitude schedule, pack
cooling airflow, cabin heat load, ventilation (environmental-control-
sizing); bay cooling, lru (avionics-bay-cooling-sizing); ullage,
inerting (fuel-tank-inerting-sizing).

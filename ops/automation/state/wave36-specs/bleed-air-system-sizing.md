# Wave-36 leaf spec: bleed-air-system-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/bleed-air-system-sizing/
- Pack: sizing. Closest siblings: environmental-control-sizing (owns pack
  flow DEMAND, pressurization schedule), ice-protection-sizing (owns the
  anti-ice consumer bleed demand, e.g. its 0.0179 kg/s worked value),
  engine-sizing (main-engine thrust SFC), propulsion/engine-airframe-
  integration (bleed as a thrust-loss term only), aircraft-electrical-
  load-analysis (electrical, unrelated to pneumatic). Whole-tree grep:
  "pneumatic" hits only ice-protection; no leaf sizes the bleed manifold
  or ducting. ZERO owners for bleed offtake rollup / bleed duct sizing.
- Standards id: far-25 (reference-only; 25.863 bleed/flammable-fluid
  plumbing context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the aircraft pneumatic bleed distribution system downstream of the
engine offtakes at the conceptual level: roll up the total bleed offtake
mass flow from the fixed consumer demands (ECS pack flows, wing anti-ice
flow, pressurization trim flow), split the offtake per engine, compute the
bleed thermal budget the precooler/conditioning system must reject from
the bleed supply temperature to the consumer supply temperature, and size
each engine bleed duct diameter from compressible pipe flow at a fixed
design Mach number. Produces the total and per-engine offtake mass flow,
the thermal budget per engine and total, the duct flow area and diameter,
and a fit verdict against a nominal duct diameter limit.

Does NOT do: ECS pack flow demand and cabin heat load (environmental-
control-sizing); anti-ice heat flux and required bleed mass flow (ice-
protection-sizing, its flow is an INPUT here); pressurization schedule
(environmental-control-sizing); main-engine thrust loss from bleed
(propulsion engine-airframe-integration); APU load and fuel burn
(apu-fuel-burn-sizing sibling).

## Model (implement exactly)

Module constants:
- CP_AIR = 1005.0 (J/kg K, air specific heat at constant pressure).
- R_AIR = 287.0 (J/kg K, air gas constant).
- GAMMA_AIR = 1.4 (air ratio of specific heats).
- M_DUCT = 0.30 (design duct Mach number, fixed).
- T_SUPPLY_DEFAULT = 288.0 (K, consumer supply temperature, sea level
  standard day).
- P_DUCT_DEFAULT = 350000.0 (Pa, nominal bleed duct static pressure).

Conventions: bleed mass flow in kg/s per consumer; the anti-ice flow and
each pack flow are FIXED INPUTS (consumer demand values computed by the
sibling leaves are not recomputed here). T_bleed is the engine offtake
total temperature input (K).

Functions (pure stdlib):
- total_bleed_offtake(pack_flows_kg_s, anti_ice_kg_s, trim_kg_s) -> dict
  {total_kg_s, per_engine_kg_s} with per_engine = total / 2. ValueErrors:
  any flow < 0; anti_ice_kg_s < 0; trim_kg_s < 0.
- bleed_thermal_budget(mass_kg_s, t_bleed_k, t_supply_k =
  T_SUPPLY_DEFAULT) -> dict {q_w, mass_kg_s, t_bleed_k, t_supply_k}
  q = m * CP_AIR * (t_bleed - t_supply). ValueErrors: m <= 0;
  t_bleed <= t_supply.
- bleed_duct_diameter(mass_kg_s, t_bleed_k, p_duct_pa = P_DUCT_DEFAULT,
  mach = M_DUCT) -> dict {area_m2, diameter_m, velocity_m_s, density_kg_m3}
  using rho = p/(R_AIR T); a = sqrt(GAMMA R T); V = M a; A = m/(rho V);
  D = sqrt(4A/pi). ValueErrors: m <= 0; t_bleed <= 0; p_duct <= 0;
  mach <= 0 or mach >= 1.
- bleed_system_summary(pack_flows_kg_s, anti_ice_kg_s, trim_kg_s,
  t_bleed_k, max_duct_diameter_m, t_supply_k = T_SUPPLY_DEFAULT,
  p_duct_pa = P_DUCT_DEFAULT, mach = M_DUCT) -> dict with total/per-engine
  offtake, per-engine and total thermal budget, duct diameter, and a fit
  verdict (PASS when diameter <= max_duct_diameter_m).

Identity to test: total offtake = 2 * per-engine; duct diameter from area
round-trips through A = pi D^2 / 4; thermal budget doubles when mass flow
doubles at fixed temperatures.

## Worked example

Reference installation: twin-engine transport; two ECS packs at 0.80 kg/s
each, wing anti-ice 0.0179 kg/s (ice-protection-sizing anchor value),
pressurization trim 0.05 kg/s; bleed supply 450 K; duct pressure 350 kPa;
duct Mach 0.30; nominal duct diameter limit 0.06 m.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- total offtake = 2*0.80 + 0.0179 + 0.05 = 1.6679 kg/s; per engine =
  0.83395 kg/s.
- per-engine thermal budget = 0.83395 * 1005 * (450 - 288) = 135775 W
  (135.8 kW); total = 1.6679 * 1005 * 162 = 271551 W (271.6 kW).
- duct: rho = 350000/(287*450) = 2.7100 kg/m3; a = sqrt(1.4*287*450) =
  425.22 m/s; V = 127.57 m/s; A = 0.83395/(2.7100*127.57) = 0.002412 m2;
  D = 0.0554 m (55.4 mm). Fit verdict vs 0.06 m limit: PASS.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: negative consumer flow; m <= 0 in thermal budget; t_bleed
  <= t_supply; m <= 0 / t_bleed <= 0 / p_duct <= 0 / mach out of (0,1)
  in duct sizing.
- Of ftake identity: 2 * per_engine == total within 1e-9.
- Thermal budget: budget(1.6679, 450) == 271551 within 1e-1; doubling m
  doubles q.
- Duct: D = 0.0554 m within 1e-3; area round trip A == pi D^2/4 within
  1e-9.
- Summary fit verdict PASS at limit 0.06, FAIL at limit 0.05.
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-bleed-air-system-sizing.yaml)

Query 1 (copy verbatim):
  "size the bleed air offtake mass flow per engine from the ecs pack flows and anti-ice demand and compute the bleed duct diameter"
  intent: "vehicle-design; bleed offtake rollup and bleed duct sizing"
  expected_skill: "vehicle-design/sizing/bleed-air-system-sizing"
Query 2 (copy verbatim):
  "compute the pneumatic bleed thermal budget the precooler must reject at the bleed supply temperature"
  intent: "vehicle-design; bleed thermal budget to consumer supply temperature"
  expected_skill: "vehicle-design/sizing/bleed-air-system-sizing"
Task ids: w36-bleed-air-system-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the aircraft bleed air
system:" and include the outputs in the Claim. First tag:
bleed-air-system-sizing. Additional tags ONLY: bleed-offtake-mass-flow,
bleed-duct-diameter, bleed-thermal-budget, pneumatic-bleed-manifold,
precooler-heat-load. NEVER single generic words (bleed, air, duct,
pneumatic, flow, thermal, offtake, manifold). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): pack cooling flow, cabin heat
load, ventilation (environmental-control-sizing); anti-ice heat flux,
running wet, evaporative, catch efficiency (ice-protection-sizing);
thrust lapse, sfc, sea level static thrust (engine-sizing); apu fuel
burn (apu-fuel-burn-sizing); pressurization schedule.

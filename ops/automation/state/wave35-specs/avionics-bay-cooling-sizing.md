# Wave-35 leaf spec: avionics-bay-cooling-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/avionics-bay-cooling-sizing/
- Pack: sizing. Closest siblings: environmental-control-sizing (the
  CABIN conditioning leaf: cabin ventilation fresh air, cabin heat
  load rollup from occupants/solar/equipment/skin, pack cooling
  airflow, pressurization schedule; its "equipment" heat item is a
  line inside the CABIN load, and it stops at the pack airflow - it
  does NOT size bay airflow or LRU case temperatures),
  ice-protection-sizing (surface thermal anti-icing),
  avionics/do160/environmental-qualification (test SPECIFICATION for
  LRU temperature qualification, not airflow sizing). Repo-wide
  grep proves ZERO owners for avionics bay cooling airflow, LRU
  inlet air limit, LRU case temperature check; environmental-control
  sizing never mentions bay/LRU/case.
- Standards id: far-25 (reference-only; 25.1309 equipment
  installation context). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the cooling airflow for the avionics and equipment bay: roll up
the bay heat load from the LRU dissipations, size the bay cooling
airflow from the allowable cooling air temperature rise so the bay
exhaust temperature stays at or below the LRU inlet-air temperature
limit, convert the mass flow to the volumetric flow and to cubic
feet per minute, and check each LRU case temperature against its
case limit from the dissipated power and the case-to-air
conductance. Produces the bay heat load, the required cooling mass
flow and CFM, the exhaust temperature, the per-LRU case temperature
verdicts, and the bay cooling PASS/FAIL verdict that gate the bay
ventilation layout.

Does NOT do: cabin ventilation fresh air, cabin heat load rollup,
pack cooling airflow, pressurization schedule and cabin altitude
(environmental-control-sizing owns the cabin); surface anti-icing
heat flux (ice-protection-sizing); DO-160 temperature qualification
test planning (avionics environmental-qualification); avionics LRU
functional design.

## Model (implement exactly)

Module constants:
- AIR_CP = 1005.0 (J/(kg K), dry air).
- DEFAULT_AIR_DENSITY = 1.2 (kg/m3, near-sea-level air used for the
  volumetric conversion).
- CFM_PER_M3S = 2118.88 (ft3/min per m3/s).

Conventions: LRU dissipations in W; temperatures in deg C; the bay
airflow enters at supply temperature and leaves at the exhaust
temperature; the exhaust temperature is sized to equal the LRU
inlet-air temperature limit (maximum cooling benefit without
exceeding the LRU inlet limit).

Functions (pure stdlib):
- bay_heat_load(lru_dissipations_w) -> dict {total_w,
  per_lru_w} = sum of the LRU powers. ValueErrors: empty dict, any
  negative power.
- cooling_mass_flow(total_heat_w, supply_temp_c, exhaust_limit_c,
  cp = AIR_CP) -> dict {mass_flow_kg_s, exhaust_temp_c} = Q /
  (cp * (T_limit - T_supply)). ValueErrors: heat < 0; temperature
  difference <= 0.
- volumetric_flow(mass_flow_kg_s, density = DEFAULT_AIR_DENSITY)
  -> dict {flow_m3_s, flow_cfm} = m / rho and m3/s * 2118.88.
  ValueErrors: mass flow < 0, density <= 0.
- lru_case_temperature(power_w, conductance_w_k, inlet_air_temp_c)
  -> dict {case_temp_c, rise_k} = T_inlet + P / (h A). ValueErrors:
  power < 0, conductance <= 0.
- case_verdict(case_temp_c, case_limit_c) -> dict {verdict,
  margin_k} = PASS when case_temp <= limit else FAIL.
  ValueError: limit <= 0? no: limit any finite; case temp can be
  any finite. Non-physical: raise when case_limit_c < -273.15.
- bay_cooling_summary(lru_dissipations_w, supply_temp_c,
  exhaust_limit_c, lru_case_limits_c, density =
  DEFAULT_AIR_DENSITY) -> dict with total_w, mass_flow_kg_s,
  flow_m3_s, flow_cfm, exhaust_temp_c, per-lru case temp dict,
  case verdicts, bay verdict (FAIL when any LRU case exceeds its
  limit or the mass flow is 0 with positive heat).

Identity to test: doubling the allowable temperature rise halves
the required mass flow; an LRU with zero dissipation sits at the
inlet air temperature.

## Worked example

Reference bay: six LRUs dissipating (W): 400, 350, 300, 550, 450,
450 = 2500 W total. Supply air 25 C, LRU inlet-air limit 55 C,
density 1.2 kg/m3. Case check: 300 W LRU with case-to-air
conductance 12 W/K, inlet 25 C, case limit 60 C. Others assumed
within limit with the same conductance model per LRU power list and
case limits given as [60, 60, 60, 65, 60, 60].

Run your module and take the real outputs as assert targets, then
check the magnitude bounds (independently verified at prep):
- bay_heat_load: 400 + 350 + 300 + 550 + 450 + 450 = 2500.0 W.
- cooling_mass_flow: 2500 / (1005 * (55 - 25)) = 0.08292 kg/s.
- volumetric_flow: 0.08292 / 1.2 = 0.06910 m3/s; 0.06910 *
  2118.88 = 146.4 CFM.
- exhaust_temp_c = 55.0 C (limit).
- 300 W LRU: rise 300 / 12 = 25.0 K; case = 25 + 25 = 50.0 C vs 60
  C limit -> PASS margin 10.0 K.
- 550 W LRU at 12 W/K: rise 45.83 K; case 70.83 C vs 65 C limit ->
  FAIL margin -5.83 K (drives a bay verdict FAIL; shows the check
  catches an undersized LRU heat path).

If a value falls outside its bound, your implementation has a bug:
find it before writing tests. In the SKILL.md worked example show
your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty LRU dict; negative power; temperature
  difference <= 0 (limit <= supply); density <= 0; conductance <= 0.
- Flow scaling: halving the temperature rise doubles the mass flow
  at fixed heat; doubling heat doubles the flow.
- Zero heat: cooling_mass_flow(0, 25, 55) -> 0.0 kg/s.
- Volumetric: 1 kg/s at 1.2 kg/m3 -> 0.8333 m3/s and 1765.7 CFM.
- Case temp: zero-power LRU case = inlet temp; doubling conductance
  halves the rise.
- Verdicts: worked 300 W LRU PASS margin 10 K; 550 W FAIL; bay
  verdict FAIL when any LRU fails; bay verdict PASS when all pass
  (use a reduced 550 W case set).
- Determinism: identical inputs -> identical outputs.
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave35-avionics-bay-cooling-sizing.yaml)

Query 1 (copy verbatim):
  "size the avionics bay cooling airflow from the LRU heat dissipation and the allowable cooling air temperature rise"
  intent: "vehicle-design; avionics bay cooling airflow from LRU heat load"
  expected_skill: "vehicle-design/sizing/avionics-bay-cooling-sizing"
Query 2 (copy verbatim):
  "check the avionics LRU case temperature against its limit from the dissipated power and the case to air conductance"
  intent: "vehicle-design; LRU case temperature check in the equipment bay"
  expected_skill: "vehicle-design/sizing/avionics-bay-cooling-sizing"
Task ids: w35-avionics-bay-cooling-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the cooling airflow for
the avionics and equipment bay:" and include the outputs in the
Claim. First tag: avionics-bay-cooling-sizing. Additional tags ONLY:
equipment-bay-cooling, lru-heat-dissipation, cooling-airflow-sizing,
lru-case-temperature. NEVER single generic words (bay, cooling,
airflow, avionics, heat, LRU, temperature). 50-150 words, <=1000
chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): cabin ventilation, fresh air
flow, cabin heat load, pack airflow, pressurization schedule, cabin
altitude (environmental-control-sizing); anti-icing, evaporative,
freezing fraction, bleed air (ice-protection-sizing); DO-160 test
category, qualification test (avionics environmental-qualification);
solar heat, occupants, skin heat (cabin load line items).

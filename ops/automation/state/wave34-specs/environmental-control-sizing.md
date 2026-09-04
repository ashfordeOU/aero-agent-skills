# Wave-34 leaf spec: environmental-control-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/environmental-control-sizing/
- Pack: sizing. Closest siblings: ice-protection-sizing (the only other
  aircraft-subsystem leaf in the pack: heats anti-icing surfaces,
  protected area, catch efficiency, anti-icing bleed flow; never touches
  cabin conditioning), battery-sizing (electric power), brake-energy-
  sizing (wheel system). Whole-tree grep (470 leaves, 12 families)
  proves ZERO owners for cabin cooling/ECS outputs, ventilation flow,
  pack cooling flow and the pressurization schedule.
- Standards id: far-25 (reference-only). Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Size the transport-aircraft environmental control system (ECS): cabin
ventilation fresh-air flow from the occupant count, the cabin heat load
rollup (occupants, solar, equipment, skin) with margin, the pack cooling
airflow from heat load and supply temperature rise, the pack airflow
verdict (max of fresh and cooling), and the cabin pressurization
schedule (cabin pressure altitude held at the design cabin altitude
until the design differential pressure binds, then constant-differential
flight). Produces fresh-air flow, cabin heat load, pack airflow, the
cabin differential at cruise and the cabin altitude under both the
held-altitude and differential-limited regimes.

Does NOT do: anti-icing surface heating and bleed-air ice protection
(ice-protection-sizing); air cycle machine thermodynamics or
refrigeration cycle detail; structural pressure loads (structures
pressure-bulkhead / vehicle-design fuselage-skin-stringer own structure,
not the cabin schedule); the ISA atmosphere itself as a deliverable
(cross-cutting isa-atmosphere owns the public atmosphere leaf; this
leaf embeds the same two-layer ISA relation as an internal helper only).

## Model (implement exactly)

Module constants:
- P0 = 101325.0 Pa; L = 0.0065 K/m; T0 = 288.15 K; G = 9.80665;
  R = 287.05; H_TROP = 11000.0 m; T_STRAT = 216.65 K.
- PSI = 6894.757 Pa/psi; FT = 0.3048 m/ft.
- DEFAULT_RATE_PER_OCCUPANT_KGMIN = 0.25 (0.55 lb/min practice).
- DEFAULT_CP = 1.005 kJ/(kg K); DEFAULT_DT_SUPPLY_K = 20.0.
- DEFAULT_CABIN_ALT_FT = 8000.0; DEFAULT_DP_MAX_PSI = 8.9.
- DEFAULT_MARGIN = 1.1.

Internal two-layer ISA (private helpers, do not expose as the leaf's
deliverable; the public ISA leaf is cross-cutting/isa-atmosphere):
- _p_isa(h_m): troposphere p = P0 (1 - L h/T0)^(G/(L R)) for h <=
  H_TROP; stratosphere p = p_trop exp(-G (h - H_TROP)/(R T_STRAT)).
- _h_isa_from_p(p): exact inverse of the two-layer relation.

Functions (pure stdlib):
- fresh_air_flow(occupants, rate_per_occupant =
  DEFAULT_RATE_PER_OCCUPANT_KGMIN) -> dict {flow_kgmin, flow_kgs}.
  ValueError on occupants <= 0, rate <= 0.
- cabin_heat_load(occupants, q_occupant_kw, solar_kw, equipment_kw,
  skin_kw, margin = DEFAULT_MARGIN) -> dict {occupant_heat_kw,
  total_heat_kw, design_heat_kw}. ValueError on any negative input,
  occupants <= 0, margin <= 1.
- pack_airflow(design_heat_kw, cp = DEFAULT_CP, dT_supply_k =
  DEFAULT_DT_SUPPLY_K, fresh_flow_kgs = 0.0) -> dict {cooling_flow_kgs,
  pack_flow_kgs, cooling_dominates} where cooling_flow_kgs =
  design_heat_kw / (cp * dT_supply_k) and pack_flow_kgs = max(fresh,
  cooling). ValueError on design_heat_kw <= 0, cp <= 0, dT_supply_k
  <= 0, fresh_flow_kgs < 0.
- pressurization_schedule(cruise_alt_ft, cabin_alt_design_ft =
  DEFAULT_CABIN_ALT_FT, dP_max_psi = DEFAULT_DP_MAX_PSI) -> dict
  {cabin_pressure_pa, ambient_pressure_pa, differential_psi,
  differential_limited (bool), cabin_altitude_ft, cabin_altitude_held
  (bool)}. Rule: p_amb = _p_isa(cruise), p_cab = _p_isa(cabin_alt_
  design); dP = p_cab - p_amb. If dP <= dP_max: hold cabin altitude at
  the design value. Else clamp: p_cab = p_amb + dP_max * PSI and the
  resulting cabin altitude rises per the inverse ISA. ValueError on
  cruise_alt_ft < 0, cabin_alt_design_ft < 0, dP_max_psi <= 0.
- ecs_summary(occupants, rate_per_occupant, q_occupant_kw, solar_kw,
  equipment_kw, skin_kw, cruise_alt_ft, margin, cp, dT_supply_k,
  cabin_alt_design_ft, dP_max_psi) -> dict combining all outputs above.

The pressurization identity to test: at altitudes where the schedule
holds, cabin_altitude_ft equals cabin_alt_design_ft exactly; in the
differential-limited regime the cabin pressure equals ambient plus the
design differential, and the reported cabin altitude is higher than the
design value.

## Worked example

Reference transport: 189 occupants, 0.25 kg/min per occupant, 0.12
kW/occupant, solar 15 kW, equipment 12 kW, skin 8 kW, margin 1.1, cp
1.005 kJ/(kg K), dT_supply 20 K, design cabin altitude 8000 ft, design
differential 8.9 psi, cruise 39000 ft then 50000 ft.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep with the two-layer
ISA, matching the isa-atmosphere convention):
- fresh_air_flow: flow_kgmin = 47.25 kg/min; flow_kgs = 0.7875 kg/s.
- cabin_heat_load: occupant 22.68 kW; total 57.68 kW; design 63.448 kW.
- pack_airflow: cooling_flow_kgs = 63.448 / (1.005 * 20) =
  3.156617 kg/s; pack_flow_kgs = 3.156617 kg/s (cooling dominates);
  cooling_dominates True.
- pressurization at 39000 ft: p_amb = 19.6770 kPa; p_cab = 75.2621 kPa
  (8000 ft cabin); differential = 8.0619 psi <= 8.9 so the schedule
  HOLDS: cabin_altitude_ft = 8000.0, differential_limited False.
- pressurization at 50000 ft: p_amb = 11.5970 kPa; required
  differential to hold 8000 ft = 9.2338 psi > 8.9 so the clamp binds:
  differential_limited True, cabin pressure = p_amb + 8.9 psi =
  72.9605 kPa, cabin_altitude_ft = 8809.9 ft (above the 8000 ft design
  value, inside the differential-limited regime).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: occupants <= 0; rate <= 0; margin <= 1; any negative heat
  input; design_heat_kw <= 0; cp <= 0; dT_supply_k <= 0; fresh < 0;
  cruise_alt_ft < 0; cabin_alt_design_ft < 0; dP_max_psi <= 0.
- Fresh flow: 189 occupants at 0.25 kg/min gives 47.25 kg/min and
  0.7875 kg/s; linearity in occupant count.
- Heat rollup: occupant + solar + equipment + skin equals total; design
  = total * 1.1 exactly for the worked inputs; margin 1.5 scales
  design_heat_kw by 1.5/1.1.
- Pack airflow: cooling_flow_kgs for the worked design heat equals
  3.156617 kg/s to 1e-6; when fresh_flow_kgs exceeds the cooling flow
  (e.g. fresh 5 kg/s), pack_flow_kgs = fresh (fresh dominates).
- Pressurization hold: at 39000 ft the schedule holds 8000 ft exactly
  and differential_limited is False; differential = (p_cab - p_amb)
  / PSI within 1e-4 psi of 8.0619.
- Pressurization clamp: at 50000 ft differential_limited True; cabin
  pressure equals ambient + 8.9 * PSI within 1e-3 Pa; cabin altitude in
  (8800, 8820) ft; cabin altitude strictly above the design value.
- Regime boundary: find the altitude where the hold just binds (the
  crossing altitude); below it cabin_altitude_ft == design, above it
  cabin_altitude_ft > design (monotonic).
- Internal ISA consistency: _p_isa(H_TROP) equals the troposphere
  formula at the tropopause and the stratosphere formula at the
  tropopause (continuous); _h_isa_from_p(_p_isa(h)) == h to 1e-6 m for
  a troposphere point and a stratosphere point.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-environmental-control-sizing.yaml)

Query 1 (copy verbatim):
  "size the environmental control system cabin ventilation fresh air flow and pack cooling airflow from the occupant count, cabin heat load and supply air temperature rise"
  intent: "vehicle-design; ECS fresh air and pack cooling airflow sizing from occupants and heat load"
  expected_skill: "vehicle-design/sizing/environmental-control-sizing"
Query 2 (copy verbatim):
  "compute the cabin pressurization schedule, the cabin pressure altitude at cruise and the differential limit clamp for a transport aircraft"
  intent: "vehicle-design; cabin pressurization schedule, cabin altitude and differential limit"
  expected_skill: "vehicle-design/sizing/environmental-control-sizing"
Task ids: w34-environmental-control-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must size the environmental control
system of a transport aircraft:" and include the outputs in the Claim.
First tag: environmental-control-sizing. Additional tags ONLY:
ecs-sizing, cabin-air-conditioning, cabin-heat-load, ventilation-flow,
pack-cooling-flow, pressurization-schedule, cabin-altitude-limit.
NEVER single generic words (environmental, control, cabin, air,
cooling, pressurization, sizing). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): ice protection, anti-icing,
bleed-air surface heating, catch efficiency (ice-protection-sizing);
air cycle machine, bootstrap cycle, refrigerant (no A/C thermodynamics
leaf exists, but do not claim those outputs either); structure,
pressure bulkhead load (structures pressure-bulkhead); ISA atmosphere,
standard atmosphere tables (cross-cutting isa-atmosphere owns the
public leaf; this leaf's internal helper is not named as a deliverable).
The words "cabin", "ventilation", "pressurization", "pack airflow",
"heat load" are this leaf's own in the sizing context.

Tags: [environmental-control-sizing, ecs-sizing, cabin-air-conditioning,
cabin-heat-load, ventilation-flow, pack-cooling-flow,
pressurization-schedule, cabin-altitude-limit]

Sibling-citation lines for Related leaves:
vehicle-design/sizing/ice-protection-sizing (sibling aircraft-subsystem
sizing leaf; boundary: surface anti-icing vs cabin conditioning),
vehicle-design/sizing/battery-sizing (electric power subsystem sizing),
cross-cutting/units-atmos/isa-atmosphere (the public atmosphere leaf
whose two-layer relation this leaf embeds internally).

Ledger Standard: far-25.

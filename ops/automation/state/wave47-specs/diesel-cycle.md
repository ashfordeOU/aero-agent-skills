# Wave-47 leaf spec: diesel-cycle (propulsion, reciprocating pack)

- Path: skills/propulsion/reciprocating/diesel-cycle/
- Pack: reciprocating (existing wave-46 pack, no NEW-pack flag: the directory
  exists at spec prep with piston-engine-cycle as its first and only leaf; the
  router group row and guidance line for the compression-ignition sibling are
  added at close by the ops manager, the router file is not edited by this
  spec).
- Claim fences (quoted from the sibling piston-engine-cycle frontmatter/body
  and the family router at spec prep, re-verified fresh at the repo HEAD this
  session; the receipt quotes the same lines at its probe HEAD and the greps
  below were re-run at this session's HEAD with identical results):
  - piston-engine-cycle description (skills/propulsion/reciprocating/
    piston-engine-cycle/SKILL.md frontmatter, quoted): "Use when you must
    compute the operating point of a reciprocating four-stroke aircraft
    powerplant for general-aviation propulsion: the air-standard Otto cycle
    thermal efficiency from the compression ratio and the specific-heat
    ratio, the four-stroke indicated power from the indicated mean effective
    pressure, the displacement and the crankshaft speed, the brake power at
    the mechanical efficiency, and the brake specific fuel consumption from
    the fuel flow and the brake power." Otto is the only cycle in the model;
    the trigger list leads with piston-engine-cycle and air-standard-otto-
    cycle, and no Diesel, compression-ignition, cutoff-ratio or
    constant-pressure heat-addition wording appears anywhere on the leaf.
  - piston-engine-cycle Domain quick reference (quoted): "This is the ideal
    efficiency ceiling of the spark-ignition cycle, not a real-cycle
    prediction." The leaf self-identifies as spark-ignition cycle math; its
    only efficiency relation is eta = 1 - 1/r^(gamma-1) (constant-volume
    heat addition).
  - piston-engine-cycle fuel constants and function list (verified fresh in
    scripts/piston_engine_cycle_logic.py at spec prep): the fuel constants
    are avgas only, AVGAS_DENSITY_KG_PER_M3 = 720.0 and AVGAS_LHV_J_PER_KG =
    43.5e6, with no Jet-A constant anywhere in the leaf; the function list
    otto_efficiency, isentropic_temperature_ratio, indicated_power,
    brake_power, brake_specific_fuel_consumption, bsfc_lb_per_hp_hr,
    fuel_flow_from_bsfc, indicated_thermal_efficiency,
    brake_thermal_efficiency, volumetric_fuel_flow, ga_band_verdict,
    piston_engine_cycle contains no constant-pressure heat-addition, no
    cutoff-ratio and no compression-ignition function.
  - Family router row 93 (skills/propulsion/SKILL.md, quoted): "|
    propulsion/reciprocating/piston-engine-cycle | Piston Engine Cycle |
    piston-engine-cycle, air-standard-otto-cycle, mean-effective-pressure,
    brake-specific-fuel-consumption, reciprocating-engine-powerplant,
    four-stroke-powerplant |" No CI wording on the row; the Otto trigger set
    owns the spark-ignition/constant-volume routing.
  - Family router guidance line 150 (quoted): "- Reciprocating aircraft
    powerplant questions (air-standard Otto cycle efficiency at the
    compression ratio, four-stroke indicated power from mean effective
    pressure and displacement, brake power at mechanical efficiency, brake
    specific fuel consumption) route to the reciprocating piston-engine-cycle
    sub-skill; gas-turbine and turboshaft shaft-power questions stay with the
    turbine packs." Otto-only wording, no compression-ignition wording
    anywhere in the family routing guidance.
  - Piston leaf boundary (lines 144-149, quoted): "propulsion/turboprop/
    free-turbine: the turboshaft power-turbine prime-mover slot, the
    shaft-power alternative to this reciprocating engine." and
    "propulsion/turboprop/turboprop-cycle: propeller (Froude) efficiency and
    shaft-power-to-thrust bookkeeping once a prime mover, turbine or
    reciprocating, delivers shaft power." The pack's prime-mover station is
    the piston leaf; the compression-ignition slot is its unowned sibling
    seam.
  Whole-tree greps at spec prep (receipt gate (a), re-run fresh at the repo
  HEAD this session): diesel 0 files, compression-ignition 0 files,
  cutoff-ratio 0 files, whole-word jet-a 0 files across skills/ and eval/
  (the single case-insensitive jet-a hit is the rocket tag
  impinging-jet-atomization in skills/propulsion/rocket/injector-design/
  SKILL.md, a substring inside an injector-atomization token, a different
  station, not a fuel claim). GENUINE propulsion gap (receipt task-2 GO-1):
  the compression-ignition aircraft prime-mover slot inside the wave-46
  reciprocating pack, unmentioned in every ops/automation state file from
  wave-39..46 and never adjudicated before wave-47.
- Standards id: far-33 (grep-verified at spec prep: standards-map.yaml line
  193 "  - id: far-33", "14 CFR Part 33: Airworthiness Standards for Aircraft
  Engines", the same reference id the family router and the reciprocating
  sibling carry; 14 CFR Part 33 historically covered reciprocating and
  turbine aircraft engines, including certified compression-ignition aircraft
  diesels of the Centurion/AE300 class; reference-only, cited and paraphrased
  never reproduced). Ledger Standard: far-33.
- Family: propulsion

## Claim

Compute the single operating point of a compression-ignition reciprocating
aircraft powerplant (an aircraft diesel), station math only: the air-standard
Diesel cycle thermal efficiency eta = 1 - (1/r^(gamma-1)) * ((rc^gamma - 1) /
(gamma * (rc - 1))) from the compression ratio r, the cutoff ratio rc of the
constant-pressure heat-addition model (heat addition 2 to 3 at constant
pressure) and the specific-heat ratio gamma, the isentropic compression
temperature ratio T2/T1 = r^(gamma-1), the four-state temperature bookkeeping
T2 = T1 * r^(gamma-1), T3 = T2 * rc and T4 = T1 * rc^gamma with the
constant-pressure heat addition q_in = cp * T2 * (rc - 1) and its closed-form
cutoff-ratio identity rc = 1 + q_in/(cp * T2), then the same four-stroke
indicated and brake power and specific-fuel-consumption bookkeeping as the
wave-46 piston-engine-cycle leaf: four-stroke indicated power P_i = IMEP *
V_d * (rpm/60)/2 from the indicated mean effective pressure, the displacement
and the crankshaft speed (one power stroke per two crankshaft revolutions,
the classic PLAN bookkeeping), brake power P_b = P_i * eta_m at the
mechanical efficiency, brake specific fuel consumption BSFC = m_dot_fuel /
P_b in kg/(kW h) and lb/(hp h), indicated and brake thermal efficiencies on
the Jet-A lower heating value, and volumetric fuel flow from the fuel flow
and the Jet-A density, closed by a documented reference-only
compression-ignition band verdict (BSFC 0.35 to 0.42 lb/(hp h) and the
brake-thermal-efficiency window 0.3262 to 0.3806, published bands for
compression-ignition aircraft engines) that reports the point's position and
NEVER enforces it. Produces the single-point summary dict with the ideal
Diesel cycle efficiency, the compression temperature ratio, the state
temperatures and heat addition, indicated and brake power in watts and
horsepower, BSFC in both reporting units, thermal efficiencies, volumetric
fuel flow and the band verdict in one call. Does NOT do: Otto-cycle,
spark-ignition, ignition-timing or avgas content of any kind
(piston-engine-cycle owns the air-standard-otto-cycle model and its 0.5752
ceiling at 8.5 to 1, on Jet-A no less than on avgas; this leaf's 17 to 1
Diesel ceiling 0.6137 differs from the same-compression-ratio constant-volume
ceiling 0.6780, so the two models are genuinely different and this leaf never
computes the sibling's relation); fuel-air cycle, variable-gamma, real-gas
dissociation or any real-cycle correction; two-stroke, port-timing,
scavenging, supercharger or turbocharger charging content (declined seams of
the wave-47 probe); volumetric-efficiency or MBT empirics (declined); gas
turbine or turbofan cycle analysis, Brayton efficiency, regenerator,
real-cycle component losses or turbine SFC (gas-turbine-cycle leaves);
free-turbine, power-turbine matching, turboshaft or turboprop shaft power
with a propeller side (free-turbine, turboprop-cycle); propeller efficiency,
static thrust, equivalent shaft power or advance-ratio bookkeeping
(turboprop-cycle); installed thrust and drag bookkeeping or bleed extraction
(engine-airframe-integration); compressor or turbine stages, pressure-ratio
maps or corrected flow (axial-compressor leaves); rocket sizing, nozzle,
propellant, feed-cycle or injector content (rocket leaves); altitude or
density-ratio power lapse; any empirical engine map. IMEP, mechanical
efficiency, fuel flow and the Jet-A density and LHV are documented inputs in
the piston-engine-cycle documented-input convention; there is no empirical
engine map anywhere. The bands are reported reference-only and never
enforced: an out-of-band point is not an error and the verdict function never
raises on one.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants (values
verified by the spec-prep anchor run):
- GAMMA_AIR = 1.4 (air-standard specific-heat ratio default, overridable).
- CP_AIR = 1005.0 (air-standard constant-pressure specific heat in J/(kg K),
  the 1.005 kJ/(kg K) class value, overridable; cv = cp/gamma internally).
- T1_REF_K = 288.15 (reference inlet temperature in K, the ISA sea-level
  standard value used by the receipt anchor, overridable).
- HOUR_S = 3600.0 (s per hour); KG_PER_LB = 0.45359237 (exact); W_PER_HP =
  745.6998715822702 (550 ft lbf/s in W, exact); M3_PER_L = 1.0e-3;
  L_PER_M3 = 1.0e3; US_GAL_PER_M3 = 264.17205235814845.
- KG_PER_KWH_PER_LB_PER_HP_HR = KG_PER_LB/(W_PER_HP*1.0e-3) =
  0.6082773878417611 (kg/(kW h) per lb/(hp h); the BSFC unit bridge).
- JET_A_LHV_J_PER_KG = 43.2e6 (Jet-A/kerosene net heating value,
  reference-only default, overridable); JET_A_DENSITY_KG_PER_M3 = 800.0
  (Jet-A class density, the 0.80 kg/L class value inside the ASTM D1655
  775-840 kg/m3 band, reference-only default, overridable).
- Reference-only compression-ignition bands, never enforced:
  BSFC_BAND_LB_PER_HP_HR = (0.35, 0.42);
  BSFC_BAND_KG_PER_KWH = (0.2128970857446164, 0.2554765028935397) derived by
  the same unit bridge; ETA_B_BAND = (0.3261878583333333,
  0.3805525013888889), the CI brake-thermal-efficiency window the receipt
  derives with its band-endpoint formula eta_b = 3.6e6/(b * LHV) evaluated at
  b = 0.42 and b = 0.36 lb/(hp h) (the receipt quotes the 0.3262 to 0.3806
  window).

Defining relations (pin these exactly; every function derives from them):
- Air-standard Diesel thermal efficiency (constant-pressure heat addition):
  eta = 1 - (1/r^(gamma-1)) * ((rc^gamma - 1)/(gamma * (rc - 1))), with r the
  compression ratio (r > 1), gamma the specific-heat ratio (gamma > 1) and rc
  the cutoff ratio, rc = V3/V2 = T3/T2 with 1 < rc <= r (heat addition must
  end before bottom dead center, so the cutoff ratio never exceeds the
  compression ratio).
- Isentropic compression temperature ratio: T2/T1 = r^(gamma-1).
- State-point bookkeeping: T2 = T1 * r^(gamma-1); T3 = T2 * rc (constant-
  pressure heat addition 2 to 3); T4 = T1 * rc^gamma (isentropic expansion
  3 to 4 to V4 = V1, closed form). The temperature-form efficiency identity
  eta = 1 - (T4 - T1)/(gamma * (T3 - T2)) holds exactly.
- Constant-pressure heat addition per kg of air: q_in = cp * (T3 - T2) =
  cp * T2 * (rc - 1); the cutoff-ratio identity rc = 1 + q_in/(cp * T2)
  (the receipt's closed form) is the exact inverse.
- Four-stroke indicated power (SI): P_i = IMEP * V_d * (rpm/60)/2, IMEP in
  Pa, V_d in m3, rpm in rev/min; one power stroke per two crankshaft turns,
  so the revolution rate halves. The bar/L convention gives the identical
  value (1 bar x 1 L carries the 100 J factor).
- Brake power: P_b = P_i * eta_m with eta_m the mechanical efficiency in
  (0, 1]. eta_m = 1.0 returns P_i exactly.
- BSFC (family shaft-power convention, kg/(kW h)): BSFC = m_dot_fuel * 3600 *
  1000 / P_b; report lb/(hp h) by dividing by
  KG_PER_KWH_PER_LB_PER_HP_HR.
- Thermal efficiencies on the Jet-A lower heating value: eta_i = P_i /
  (m_dot_fuel * LHV); eta_b = P_b / (m_dot_fuel * LHV) = eta_m * eta_i. The
  air-standard Diesel eta is the ideal ceiling and sits above eta_b for any
  real point.
- Volumetric fuel flow: V_dot = m_dot_fuel / rho_fuel (m3/s), reported also
  in L/h and US gal/h.
- Band verdict: reference-only; each metric's position is 'below', 'inside'
  or 'above' against ETA_B_BAND and BSFC_BAND_LB_PER_HP_HR; the verdict dict
  carries enforced: False and NEVER raises for an out-of-band point.

Functions (signatures and ValueError rejections; no imports beyond math):
- diesel_efficiency(compression_ratio, cutoff_ratio, gamma=GAMMA_AIR) -> eta
  (dimensionless). ValueError if inputs non-finite, compression_ratio <= 1,
  gamma <= 1, cutoff_ratio <= 1, or cutoff_ratio > compression_ratio.
- isentropic_temperature_ratio(compression_ratio, gamma=GAMMA_AIR) -> T2/T1 =
  compression_ratio**(gamma-1). Same compression_ratio/gamma ValueErrors as
  diesel_efficiency.
- compression_temperature(t1_k, compression_ratio, gamma=GAMMA_AIR) -> T2 (K)
  = t1_k * isentropic_temperature_ratio(...). ValueError if t1_k non-finite
  or <= 0, plus the ratio's ValueErrors.
- cutoff_temperature(t2_k, cutoff_ratio) -> T3 (K) = t2_k * cutoff_ratio.
  ValueError if t2_k non-finite or <= 0, cutoff_ratio non-finite or <= 1.
- expansion_temperature(t1_k, cutoff_ratio, gamma=GAMMA_AIR) -> T4 (K) =
  t1_k * cutoff_ratio**gamma. ValueError if t1_k non-finite or <= 0,
  cutoff_ratio non-finite or <= 1, gamma non-finite or <= 1.
- cycle_state_temperatures(t1_k, compression_ratio, cutoff_ratio,
  gamma=GAMMA_AIR) -> dict {t1_k, t2_k, t3_k, t4_k} from the state relations
  above. Same ValueErrors as diesel_efficiency plus t1_k <= 0.
- heat_addition_j_per_kg(t2_k, cutoff_ratio, cp_j_per_kg_k=CP_AIR) -> q_in
  (J per kg air) = cp_j_per_kg_k * t2_k * (cutoff_ratio - 1). ValueError if
  t2_k non-finite or <= 0, cutoff_ratio non-finite or <= 1, cp non-finite or
  <= 0.
- cutoff_ratio_from_heat_addition(q_in_j_per_kg, t2_k,
  cp_j_per_kg_k=CP_AIR) -> rc = 1 + q_in_j_per_kg/(cp_j_per_kg_k * t2_k).
  ValueError if any input non-finite or <= 0.
- indicated_power(imep_pa, displacement_m3, rpm) -> P_i (W) =
  imep_pa * displacement_m3 * (rpm/60.0)/2.0. ValueError if inputs
  non-finite, imep_pa <= 0, displacement_m3 <= 0, or rpm <= 0.
- brake_power(indicated_power_w, mechanical_efficiency) -> P_b (W) =
  indicated_power_w * mechanical_efficiency. ValueError if inputs non-finite,
  indicated_power_w <= 0, mechanical_efficiency <= 0, or
  mechanical_efficiency > 1.
- brake_specific_fuel_consumption(fuel_flow_kg_per_s, brake_power_w) -> BSFC
  in kg/(kW h) = fuel_flow_kg_per_s * 3600.0 * 1000.0 / brake_power_w.
  ValueError if inputs non-finite, fuel_flow_kg_per_s <= 0, or
  brake_power_w <= 0.
- bsfc_lb_per_hp_hr(bsfc_kg_per_kwh) -> lb/(hp h) = bsfc_kg_per_kwh /
  KG_PER_KWH_PER_LB_PER_HP_HR. ValueError if non-finite or bsfc_kg_per_kwh
  <= 0.
- fuel_flow_from_bsfc(bsfc_kg_per_kwh, brake_power_w) -> kg/s (the exact
  inverse of brake_specific_fuel_consumption). ValueError if inputs
  non-finite, bsfc_kg_per_kwh <= 0, or brake_power_w <= 0.
- indicated_thermal_efficiency(indicated_power_w, fuel_flow_kg_per_s,
  lhv_j_per_kg=JET_A_LHV_J_PER_KG) -> eta_i = indicated_power_w /
  (fuel_flow_kg_per_s * lhv_j_per_kg). ValueError if inputs non-finite,
  indicated_power_w <= 0, fuel_flow_kg_per_s <= 0, or lhv_j_per_kg <= 0.
- brake_thermal_efficiency(brake_power_w, fuel_flow_kg_per_s,
  lhv_j_per_kg=JET_A_LHV_J_PER_KG) -> eta_b = brake_power_w /
  (fuel_flow_kg_per_s * lhv_j_per_kg). Same ValueErrors as the indicated
  form.
- volumetric_fuel_flow(fuel_flow_kg_per_s,
  fuel_density_kg_per_m3=JET_A_DENSITY_KG_PER_M3) -> m3/s =
  fuel_flow_kg_per_s / fuel_density_kg_per_m3. ValueError if inputs
  non-finite, fuel_flow_kg_per_s <= 0, or fuel_density_kg_per_m3 <= 0.
- ci_band_verdict(brake_thermal_eff, bsfc_lb_per_hp_hr_value) -> dict with
  eta_b_band, eta_b_position, bsfc_band_lb_per_hp_hr, bsfc_position (each
  position in {'below', 'inside', 'above'}) and enforced: False. ValueError
  only for non-finite, zero or negative inputs; NEVER for an out-of-band
  position.
- diesel_cycle(compression_ratio, cutoff_ratio, imep_pa, displacement_m3,
  rpm, mechanical_efficiency, fuel_flow_kg_per_s, t1_k=T1_REF_K,
  gamma=GAMMA_AIR, cp_j_per_kg_k=CP_AIR, lhv_j_per_kg=JET_A_LHV_J_PER_KG,
  fuel_density_kg_per_m3=JET_A_DENSITY_KG_PER_M3) -> dict with keys:
  compression_ratio, cutoff_ratio, gamma, t1_k, eta_diesel,
  temperature_ratio, t2_k, t3_k, t4_k, heat_addition_j_per_kg, imep_pa,
  displacement_m3, rpm, indicated_power_w, indicated_power_hp,
  mechanical_efficiency, brake_power_w, brake_power_hp, fuel_flow_kg_per_s,
  bsfc_kg_per_kwh, bsfc_lb_per_hp_hr, indicated_thermal_efficiency,
  brake_thermal_efficiency, volumetric_fuel_flow_m3_per_s,
  volumetric_fuel_flow_l_per_h, volumetric_fuel_flow_us_gal_per_h,
  band_verdict (nested dict). ValueErrors propagate from the chained
  functions.

Identities to test (closed form, from the real anchor outputs):
- Receipt closed-form anchor: diesel_efficiency(17.0, 2.2, 1.4) =
  0.6136842121239982, reproducing the receipt's 0.6136842121 within 1e-9
  relative (the anchor run's own isclose gate).
- Cutoff-ratio sensitivity at r = 17: diesel_efficiency(17.0, 2.0, 1.4) =
  0.6230571224158052 and diesel_efficiency(17.0, 2.5, 1.4) =
  0.600330985397127, so eta falls as rc grows (0.6231 > 0.6137 > 0.6003),
  the constant-pressure-addition signature the receipt pins.
- Limit rc -> 1: diesel_efficiency(17.0, 1.0 + 1e-9, 1.4) =
  0.6780262755, equal to 1 - 1/17^0.4 within 1e-6 relative, the same-r
  constant-volume ceiling the sibling leaf owns (the receipt's Otto ceiling
  at 17 to 1); the same ceiling at 8.5 to 1 is 0.5751531234, the sibling's
  own worked-example anchor. The Diesel value 0.6137 sits below the 17 to 1
  ceiling 0.6780, proving the models are genuinely different.
- Limit gamma -> 1: diesel_efficiency(17.0, 2.2, 1.0 + 1e-9) below 1e-8,
  eta -> 0 as the specific-heat ratio approaches 1.
- Limit r -> 1 with rc <= r: diesel_efficiency(1.0 + 1e-9, 1.0 + 1e-9, 1.4)
  approaches 0; r <= 1 raises, and rc > r raises (diesel_efficiency(2.0,
  2.2, 1.4) raises ValueError).
- Isentropic relation: isentropic_temperature_ratio(17.0, 1.4) =
  3.1058435015977315 = 17^0.4 and compression_temperature(288.15, 17.0,
  1.4) = 894.9488049853862 K (the receipt's T2 = 894.95 K is this value
  rounded to two decimals).
- State identities at the anchor: t3 = t2 * rc and t4 = t1 * rc^gamma hold
  exactly; heat_addition_j_per_kg(t2, rc) = 1079308.258812376 J/kg =
  cp * t2 * (rc - 1) exactly, and
  cutoff_ratio_from_heat_addition(q_in, t2) returns rc to 1e-15 relative
  (the round trip of the cutoff-ratio identity rc = 1 + q_in/(cp * T2)).
- Temperature-form efficiency identity: 1 - (t4 - t1)/(gamma * (t3 - t2))
  equals diesel_efficiency(...) to 1e-12 relative at the anchor, and the
  heat-rejection form eta = 1 - q_out/q_in with q_out = (cp/gamma) *
  (t4 - t1) holds to 1e-12 relative.
- Unit-convention consistency: indicated_power with IMEP in Pa and V_d in m3
  equals the bar/L convention exactly, and indicated_power(1.8e6, 2.0e-3,
  2300.0) = 69000.0 W exactly; brake_power(69000.0, 0.86) = 59340.0 W
  exactly, reproducing the receipt's four-stroke bookkeeping targets.
- Linear scalings: P_i doubles when rpm doubles at fixed IMEP and V_d, and
  doubles when V_d doubles at fixed IMEP and rpm; P_b = P_i exactly at
  eta_m = 1.0.
- Round trips: fuel_flow_from_bsfc(bsfc, P_b) recovers the input fuel flow to
  better than 1e-15 kg/s; eta_b = eta_i * eta_m exactly at the anchor.
- Physical ordering: brake_thermal_efficiency < eta_diesel and brake_power <
  indicated_power at any mechanical efficiency below 1 (anchor point: 0.35221
  < 0.61368); eta_i > eta_b at any eta_m below 1 (0.40954 > 0.35221).
- Conversion bridge: KG_PER_KWH_PER_LB_PER_HP_HR = 0.6082773878417611; the
  worked point converts 0.23660262891809908 kg/(kW h) to
  0.3889716002062689 lb/(hp h).
- Determinism: no imports beyond math; constants fixed; repeated runs
  byte-identical under BOTH interpreters (verified at spec prep).

## Worked example

Centurion/AE300-class compression-ignition aircraft diesel at a cruise
rating: compression ratio r = 17, cutoff ratio rc = 2.2, gamma = 1.4 (air
standard), inlet temperature T1 = 288.15 K, IMEP = 1.8e6 Pa (18 bar),
displacement V_d = 2.0e-3 m3 (2.0 L), crankshaft speed 2300 rpm, mechanical
efficiency eta_m = 0.86, fuel flow m_dot = 3.9e-3 kg/s Jet-A at the reference
density 800 kg/m3 and LHV 43.2 MJ/kg, cp 1005 J/(kg K). All values below are
REAL outputs of the spec-prep anchor script anchor_diesel_cycle.py (stdlib
math, closed form; ALL CHECKS PASS on the run, byte-identical under both
interpreters).
- Ideal cycle: eta_diesel = 1 - (1/17^0.4) * ((2.2^1.4 - 1)/(1.4 * 1.2)) =
  0.6136842121239982, reproducing the receipt's 0.6136842121 anchor within
  1e-9 relative; the isentropic compression temperature ratio is T2/T1 =
  17^0.4 = 3.1058435015977315.
- State bookkeeping from T1 = 288.15 K: T2 = 894.9488049853862 K (the
  receipt's 894.95 K, rounded to two decimals), T3 = T2 * 2.2 =
  1968.8873709678498 K, T4 = T1 * 2.2^1.4 = 868.9811925471146 K, and the
  constant-pressure heat addition q_in = 1005 * T2 * (2.2 - 1) =
  1079308.258812376 J/kg (about 1.08 MJ per kg of air); the temperature-form
  identity 1 - (T4 - T1)/(1.4 * (T3 - T2)) reproduces eta_diesel exactly.
  The cutoff-ratio identity rc = 1 + q_in/(cp * T2) round-trips to 2.2
  exactly.
- rc sensitivity at this compression ratio: rc = 2.0 gives
  0.6230571224158052 and rc = 2.5 gives 0.600330985397127, so a longer
  constant-pressure heat addition costs efficiency at fixed r, the
  compression-ignition signature.
- Indicated power: P_i = 1.8e6 * 2.0e-3 * (2300/60)/2 = 69000.0 W =
  92.53052418205692 hp, reproducing the receipt's 92.53 hp target.
- Brake power: P_b = 69000.0 * 0.86 = 59340.0 W = 79.57625079656896 hp,
  reproducing the receipt's 79.58 hp target.
- BSFC: m_dot * 3600 * 1000 / P_b = 0.23660262891809908 kg/(kW h) =
  0.3889716002062689 lb/(hp h), inside the published 0.35 to 0.42 lb/(hp h)
  compression-ignition band and the equivalent 0.2128970857446164 to
  0.2554765028935397 kg/(kW h) band, reproducing the receipt's 0.2366 and
  0.38897 figures.
- Thermal efficiencies on LHV: eta_i = 69000.0/(3.9e-3 * 43.2e6) =
  0.40954415954415957; eta_b = 59340.0/(3.9e-3 * 43.2e6) =
  0.3522079772079772 = eta_i * eta_m exactly, inside the published CI
  brake-thermal-efficiency window 0.3261878583333333 to 0.3805525013888889
  (the receipt's 0.3262 to 0.3806) and below the ideal eta_diesel (0.35221 <
  0.61368), as it must be. The CI window itself sits above the sibling's
  published 0.25 to 0.30 general-aviation window, a different published band
  for a different prime mover.
- Volumetric fuel flow: V_dot = 3.9e-3/800 = 4.875e-06 m3/s = 17.55 L/h =
  4.636219518885506 US gal/h.
- Band verdict: eta_b_position 'inside' and bsfc_position 'inside' with
  enforced False (both metrics land in the published CI bands at this point;
  the verdict reports and never enforces).

## Validation list (deterministic checks the contract test must run)

1. Module import + constants match the spec values: GAMMA_AIR 1.4, CP_AIR
   1005.0, T1_REF_K 288.15, HOUR_S 3600.0, KG_PER_LB 0.45359237, W_PER_HP
   745.6998715822702, US_GAL_PER_M3 264.17205235814845,
   KG_PER_KWH_PER_LB_PER_HP_HR 0.6082773878417611, JET_A_LHV_J_PER_KG 43.2e6,
   JET_A_DENSITY_KG_PER_M3 800.0, band tuples as pinned (isclose, never
   exact-float equality on derived constants): BSFC_BAND_LB_PER_HP_HR (0.35,
   0.42), BSFC_BAND_KG_PER_KWH (0.2128970857446164, 0.2554765028935397),
   ETA_B_BAND (0.3261878583333333, 0.3805525013888889).
2. Worked-example values within 1e-6 relative of the anchor outputs:
   eta_diesel 0.6136842121239982, temperature_ratio 3.1058435015977315, t2_k
   894.9488049853862, t3_k 1968.8873709678498, t4_k 868.9811925471146,
   heat_addition_j_per_kg 1079308.258812376, indicated power 69000.0 W, brake
   power 59340.0 W, BSFC 0.23660262891809908 kg/(kW h) and
   0.3889716002062689 lb/(hp h), eta_i 0.40954415954415957, eta_b
   0.3522079772079772, volumetric fuel flow 4.875e-06 m3/s, 17.55 L/h and
   4.636219518885506 US gal/h.
3. Receipt targets: eta_diesel(17.0, 2.2, 1.4) within 1e-6 relative of
   0.6136842121; eta_diesel(17.0, 2.0, 1.4) within 1e-6 relative of
   0.6230571224 and eta_diesel(17.0, 2.5, 1.4) within 1e-6 relative of
   0.6003309854; isentropic_temperature_ratio(17.0, 1.4) within 1e-6
   relative of 3.1058435016; compression_temperature(288.15, 17.0, 1.4)
   within 1e-5 relative of 894.95 K (receipt value rounded to two decimals);
   indicated_power_hp within 2e-4 relative of 92.53 and brake_power_hp
   within 2e-4 relative of 79.58 (receipt values rounded); BSFC within 2e-4
   relative of 0.2366 kg/(kW h) and 0.38897 lb/(hp h), eta_i within 2e-4 of
   0.4095 and eta_b within 2e-4 of 0.3522 (receipt values rounded to 4 to 5
   significant figures).
4. Limits: diesel_efficiency(17.0, 1.0 + 1e-9, 1.4) within 1e-6 relative of
   0.6780262755 (the constant-volume ceiling 1 - 1/17^0.4 the sibling owns);
   diesel_efficiency(17.0, 2.2, 1.0 + 1e-9) below 1e-8; diesel_efficiency(
   1.0 + 1e-9, 1.0 + 1e-9, 1.4) below 1e-8.
5. Cutoff-ratio domain: efficiency falls as rc grows at fixed r (0.6230571224
   > 0.6136842121 > 0.6003309854); diesel_efficiency(17.0, 1.0, 1.4) raises
   ValueError (rc <= 1); diesel_efficiency(2.0, 2.2, 1.4) raises ValueError
   (rc above r).
6. State identities: t3 equals t2 * rc and t4 equals t1 * rc^gamma at the
   anchor within 1e-12 relative; heat_addition_j_per_kg equals cp * t2 *
   (rc - 1) within 1e-12; cutoff_ratio_from_heat_addition(q_in, t2) equals
   rc within 1e-15; the temperature-form identity 1 - (t4 - t1)/(gamma *
   (t3 - t2)) equals eta_diesel within 1e-12.
7. Round trips: fuel_flow_from_bsfc(bsfc, 59340.0) recovers 0.0039 kg/s
   within 1e-15; eta_b == eta_i * eta_m at the anchor within 1e-15; the
   bar/L convention equals the Pa/m3 convention.
8. Band semantics: at the anchor point both positions are 'inside' with
   enforced False; an artificial out-of-band point (eta_b 0.45, BSFC 0.30
   lb/(hp h)) returns 'above' and 'below' without raising; enforced stays
   False.
9. Physical ordering: eta_b < eta_diesel and P_b < P_i at eta_m 0.86; eta_i
   > eta_b; eta_b in the CI window (0.3262, 0.3806); BSFC in (0.35, 0.42)
   lb/(hp h) and in (0.2129, 0.2555) kg/(kW h).
10. All ValueErrors listed under Model fire: diesel_efficiency at r 1.0, rc
    1.0, rc 2.2 with r 2.0, gamma 1.0 and nan; isentropic_temperature_ratio
    at r 1.0; compression_temperature at t1_k 0; cutoff_temperature at rc
    1.0; expansion_temperature at rc 0.5; heat_addition_j_per_kg at t2_k
    negative and rc 1.0; cutoff_ratio_from_heat_addition at t2_k 0;
    indicated_power at IMEP 0 and rpm negative; brake_power at eta_m 0 and
    eta_m 1.1; brake_specific_fuel_consumption at m_dot 0;
    bsfc_lb_per_hp_hr at inf; fuel_flow_from_bsfc at negative brake power;
    indicated_thermal_efficiency at negative LHV; brake_thermal_efficiency
    at P_b 0; volumetric_fuel_flow at density 0; ci_band_verdict at eta_b 0
    and BSFC 0; diesel_cycle at t1_k <= 0 through the chain.
11. Determinism: two identical runs return byte-identical outputs (verified
    at spec prep under both interpreters).
12. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for eval/hit1-wave47-diesel-cycle.yaml)

1. "run the air-standard-diesel-cycle for the compression-ignition aircraft
   engine at the 17 to 1 compression ratio: the diesel-cycle efficiency from
   the cutoff-ratio constant-pressure heat-addition model and the
   compression temperature ratio, then the brake-horsepower from the
   mean-effective-pressure and the displacement and the specific fuel
   consumption of the jet-a-fueled diesel powerplant at the cruise rating
   with the published compression-ignition band check"
2. "compare the compression-ignition diesel-cycle ideal efficiency against
   the spark-ignition otto ceiling at the same 16 to 1 compression ratio:
   the air-standard-diesel-cycle cutoff-ratio sensitivity from 2 to 2.5 and
   the jet-a-fuel brake specific fuel consumption band for the
   compression-ignition aircraft powerplant"
intent lines: "propulsion; compression-ignition reciprocating aircraft
powerplant station bookkeeping: air-standard Diesel cycle efficiency from the
compression ratio, the cutoff ratio and the specific-heat ratio, the
compression temperature ratio, indicated power from the indicated mean
effective pressure, displacement and crankshaft speed, brake power at
mechanical efficiency, and brake specific fuel consumption on Jet-A with the
reference-only compression-ignition band check" and "propulsion;
compression-ignition diesel-cycle assessment: ideal Diesel efficiency from
the cutoff-ratio model against the same-compression-ratio constant-volume
ceiling, cutoff-ratio sensitivity, and the Jet-A brake specific fuel
consumption band for the compression-ignition aircraft powerplant". The
queries are the receipt gate (e) texts verbatim. The distinctive
hyphenated tokens (air-standard-diesel-cycle, diesel-cycle,
compression-ignition, cutoff-ratio, jet-a-fueled, jet-a-fuel) sit on no
router row and in no corpus task today, so Hit@1 is clean. The sibling's
owned lead triggers (air-standard-otto-cycle, piston-engine-cycle as a lead,
four-stroke-powerplant, avgas) are kept out of the lead position; in query 2
the spark-ignition otto wording is the comparison ceiling only, never the
model this leaf computes, and the query routes on the diesel-cycle and
cutoff-ratio lead tokens.

## Description/tag guidance for the builder

- Description: "Use when you must compute the operating point of a
  reciprocating compression-ignition aircraft powerplant: the air-standard
  Diesel cycle thermal efficiency from the compression ratio, the
  specific-heat ratio and the cutoff ratio of the constant-pressure
  heat-addition model, the isentropic compression temperature ratio and
  state temperatures, the four-stroke indicated power from the indicated
  mean effective pressure, displacement and crankshaft speed, the brake
  power at the mechanical efficiency, and the brake specific fuel
  consumption from the fuel flow and the brake power on Jet-A. Produces the
  single-point summary dict with the ideal Diesel cycle efficiency, the
  state temperatures, indicated and brake power, BSFC in both units,
  thermal efficiencies, volumetric fuel flow and the reference-only
  compression-ignition band verdict, the bands reported and never enforced.
  Trigger: diesel-cycle, air-standard-diesel-cycle, compression-ignition,
  cutoff ratio, jet-a-fuel-cycle." (action verb compute; 127 words and 983
  characters verified at spec prep, within the <=148 word and <=1000 char
  limits.)
- metadata tags (EXACTLY as the receipt gate (f) lists them):
  [diesel-cycle, air-standard-diesel-cycle, compression-ignition,
  cutoff-ratio, constant-pressure-heat-addition, jet-a-fuel-cycle]
- FORBIDDEN tokens (sibling claims and token discipline): any Otto,
  spark-ignition or avgas claim in the description or tags
  (air-standard-otto-cycle, otto-cycle, otto, spark-ignition as an own
  claim, ignition timing, MBT, avgas, four-stroke-powerplant as a
  standalone compound; plain four-stroke appears only inside the shared
  power-bookkeeping prose above, never as a tag or lead trigger);
  fuel-air cycle, variable-gamma, real-gas dissociation or real-cycle
  corrections; volumetric efficiency, MBT timing, two-stroke, scavenging,
  port-timing, supercharger, turbocharger, altitude or density-ratio power
  lapse claims (declined probe seams); mean-effective-pressure and
  indicated-mean-effective-pressure only inside the four-stroke power
  bookkeeping as a documented input, never as standalone tags or lead
  phrases, and no bmep; turbine-family vocabulary: gas turbine, turbofan,
  turbojet, turboshaft, free turbine, power turbine, Brayton, regenerator,
  real cycle, turbine SFC or bare specific-fuel-consumption as a lead,
  propeller efficiency, static thrust, equivalent shaft power, advance
  ratio, compressor or turbine stage, pressure ratio, corrected flow;
  rocket vocabulary: rocket equation, nozzle, propellant, feed cycle,
  specific impulse, injector; the Lighthill piston surface-pressure analogy
  tokens of hypersonic-piston-theory and the actuator piston-area tokens of
  hydraulic-actuator-sizing (piston is only ever the engine prime mover
  here, inside the leaf's own distinctive compounds); engine-airframe
  installed thrust and drag bookkeeping; jet-fuel and kerosene used only
  inside the jet-a-fuel-cycle and Jet-A-named content, never as standalone
  tags. No generic single-word tags (no bare engine, power, fuel, cycle,
  ignition, diesel, jet-a, ratio, compression-ratio, cutoff, temperature,
  efficiency, aircraft, kerosene) and no reuse of the sibling's owned
  tokens (air-standard-otto-cycle, four-stroke-powerplant, avgas) or
  turbine SFC tags; compression-ratio appears only inside longer
  distinctive tokens to avoid pressure-ratio ambiguity with axial-compressor
  rows, and cutoff-ratio, constant-pressure-heat-addition and
  compression-ignition never stand alone as generic words, only as the
  hyphenated compounds above.
- ZERO em dashes in every file; never the word that the spec-engineer kit's
  reserved-word ban names (it is a gate-scanned token, do not print it
  anywhere).
- Standards reference-only: far-33 (14 CFR Part 33, aircraft-engine
  airworthiness, which historically covered reciprocating and turbine
  aircraft engines including certified compression-ignition aircraft
  diesels) named + paraphrased, never reproduced verbatim.

## Routing note for the ops manager (not acted on by the builder)

This leaf fills the compression-ignition slot inside the existing wave-46
propulsion/reciprocating pack; no NEW-pack flag applies. At close the ops
manager adds the propulsion/reciprocating/diesel-cycle router group row
(Path propulsion/reciprocating/diesel-cycle, Skill Diesel cycle, routing
text over the air-standard Diesel cycle, cutoff ratio,
compression-ignition and Jet-A tokens, keeping the Otto leaf's
air-standard-otto-cycle and four-stroke-powerplant triggers on the existing
piston-engine-cycle row) and extends the reciprocating routing guidance line
150 of skills/propulsion/SKILL.md with a compression-ignition sentence. The
spec does not edit the router; the builder touches only
skills/propulsion/reciprocating/diesel-cycle/ and its eval and test files.

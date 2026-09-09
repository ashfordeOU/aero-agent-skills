# Wave-48 leaf spec: dual-cycle (propulsion, reciprocating pack)

- Path: skills/propulsion/reciprocating/dual-cycle/
- Pack: reciprocating (existing pack, no NEW-pack flag: at spec prep the
  directory tree holds piston-engine-cycle from wave-46 and diesel-cycle from
  wave-47 as the pack's two leaves; the router group row and the routing
  guidance extension for this dual sibling are added at close by the ops
  manager, the router file is not edited by this spec).
- Claim fences (quoted verbatim from the two landed siblings and the family
  router at the repo HEAD b03e6ff1 this session, re-verified fresh; the
  receipt quotes the same lines at its probe HEAD and the greps below were
  re-run at this session's HEAD with identical results):
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
    cycle and the leaf self-identifies as spark-ignition math end to end.
  - piston-engine-cycle Domain quick reference (quoted): "Air-standard Otto
    thermal efficiency: eta = 1 - 1/r^(gamma-1), with r the compression ratio
    (r > 1) and gamma the specific-heat ratio (gamma > 1, air-standard
    default 1.4). This is the ideal efficiency ceiling of the spark-ignition
    cycle, not a real-cycle prediction." The Otto leaf's only heat-addition
    law is constant-volume; no pressure-ratio and no cutoff-ratio input
    exists anywhere in scripts/piston_engine_cycle_logic.py (function list
    re-read this session: otto_efficiency, isentropic_temperature_ratio,
    indicated_power, brake_power, brake_specific_fuel_consumption,
    bsfc_lb_per_hp_hr, fuel_flow_from_bsfc, indicated_thermal_efficiency,
    brake_thermal_efficiency, volumetric_fuel_flow, ga_band_verdict,
    piston_engine_cycle; no alpha-like parameter and no mixed heat
    addition).
  - diesel-cycle description (skills/propulsion/reciprocating/diesel-cycle/
    SKILL.md frontmatter, quoted): "Use when you must compute the operating
    point of a reciprocating compression-ignition aircraft powerplant: the
    air-standard Diesel cycle thermal efficiency from the compression ratio,
    the specific-heat ratio and the cutoff ratio of the constant-pressure
    heat-addition model, the isentropic compression temperature ratio and
    state temperatures, the four-stroke indicated power from the indicated
    mean effective pressure, displacement and crankshaft speed, the brake
    power at the mechanical efficiency, and the brake specific fuel
    consumption from the fuel flow and the brake power on Jet-A." The Diesel
    leaf models ONE heat-addition law only, constant pressure; its trigger
    list leads with diesel-cycle, air-standard-diesel-cycle and
    compression-ignition, none of which describe a mixed heat addition.
  - diesel-cycle Domain quick reference (quoted): "Air-standard Diesel
    thermal efficiency (constant-pressure heat addition): eta = 1 -
    (1/r^(gamma-1)) * ((rc^gamma - 1)/(gamma * (rc - 1))), with r the
    compression ratio (r > 1), gamma the specific-heat ratio (gamma > 1,
    air-standard default 1.4) and rc the cutoff ratio (1 < rc <= r; heat
    addition must end before bottom dead center). This is the ideal
    efficiency ceiling of the compression-ignition cycle, not a real-cycle
    prediction."
  - diesel-cycle verification text (quoted): "As rc approaches 1 the Diesel
    efficiency approaches the same-r constant-volume Otto ceiling
    1 - 1/r^(gamma-1), showing the two air-standard cycles share a common
    limit; for any rc above 1 the Diesel efficiency sits below that
    ceiling." The
    landed Diesel leaf counts exactly two air-standard cycles in its limit
    note (Otto and Diesel) and carries no mixed or dual model anywhere.
  - diesel-cycle function list (re-read this session in scripts/
    diesel_cycle_logic.py): diesel_efficiency, isentropic_temperature_ratio,
    compression_temperature, cutoff_temperature, expansion_temperature,
    cycle_state_temperatures, heat_addition_j_per_kg,
    cutoff_ratio_from_heat_addition, indicated_power, brake_power,
    brake_specific_fuel_consumption, bsfc_lb_per_hp_hr, fuel_flow_from_bsfc,
    indicated_thermal_efficiency, brake_thermal_efficiency,
    volumetric_fuel_flow, ci_band_verdict, diesel_cycle. No pressure-ratio
    (alpha) parameter exists anywhere in the module (grep for alpha, dual,
    sabathe and limited-pressure over the file returns nothing, rc=1); the
    mixed constant-volume-then-constant-pressure heat addition cannot be
    produced by either landed sibling.
  - Family router rows 93 and 94 (skills/propulsion/SKILL.md, quoted): "|
    propulsion/reciprocating/piston-engine-cycle | Piston Engine Cycle |
    piston-engine-cycle, air-standard-otto-cycle, mean-effective-pressure,
    brake-specific-fuel-consumption, reciprocating-engine-powerplant,
    four-stroke-powerplant |" and "| propulsion/reciprocating/diesel-cycle |
    Diesel Cycle | diesel-cycle, compression-ignition-cycle,
    air-standard-diesel-cycle, cutoff-ratio, diesel-cycle-efficiency,
    compression-ignition-powerplant |". Neither row routes on dual, sabathe,
    limited-pressure or mixed-heat-addition wording.
  - Family router guidance lines 151 and 152 (quoted): "Reciprocating
    aircraft powerplant questions (air-standard Otto cycle efficiency at the
    compression ratio, four-stroke indicated power from mean effective
    pressure and displacement, brake power at mechanical efficiency, brake
    specific fuel consumption) route to the reciprocating piston-engine-cycle
    sub-skill; gas-turbine and turboshaft shaft-power questions stay with the
    turbine packs." and "Compression-ignition powerplant questions
    (air-standard Diesel cycle efficiency at the compression ratio and cutoff
    ratio, diesel state points, brake specific fuel consumption of a
    compression-ignition engine) route to the reciprocating diesel-cycle
    sub-skill; spark-ignition Otto-cycle questions stay with
    piston-engine-cycle." Only the two landed cycles are routed; no
    limited-pressure, dual or mixed wording appears on any router row or
    guidance line.
  - Whole-tree greps re-run at this session's HEAD (receipt gate (a), real
    output, all zero): grep -rliE 'dual[- ]cycle' skills/ eval/ -> 0 files
    (rc=1); grep -rliE 'sabathe' skills/ eval/ -> 0 files (rc=1); grep
    -rliE 'limited[- ]pressure' skills/ eval/ -> 0 files (rc=1); grep
    -rliE 'air-standard-dual-cycle|mixed-heat-addition|
    pressure-ratio-of-heat-addition' skills/ eval/ -> 0 files (rc=1);
    grep -icE 'dual-cycle|sabathe|limited-pressure|mixed-heat-addition'
    eval/hit1-corpus.yaml -> 0 (rc=1). Adjudication history per the receipt's
    own probe: the dual-cycle seam was never proposed, declined or planned in
    any wave-39..48 brief, receipt, leaf plan or builder kit; the sole ops/
    history hit is an unrelated "limited pressure ratio" phrase inside a
    wave-24 rocket spec, a false positive read and set aside by the receipt.
    GENUINE propulsion gap (receipt GO-1): the mixed heat-addition slot
    inside the reciprocating pack, the third member of the air-standard
    cycle triad the two landed leaves already map.
- Standards id: far-33 (grep-verified at spec prep: standards-map.yaml line
  193 "  - id: far-33", "14 CFR Part 33: Airworthiness Standards for Aircraft
  Engines", the same reference id the family router and both reciprocating
  siblings carry; 14 CFR Part 33 historically covered reciprocating and
  turbine aircraft engines, including certified compression-ignition aircraft
  diesels of the high-speed direct-injection class; reference-only, cited
  and paraphrased never reproduced). Ledger Standard: far-33.
- Family: propulsion

## Claim

Compute the single operating point of a reciprocating high-speed
compression-ignition aircraft powerplant (an aircraft diesel of the
direct-injection class, the Centurion/AE300 lineage the diesel sibling
already cites where the pure constant-pressure Diesel idealization is the
slow-speed limit), station math only: the air-standard dual (Sabathe /
limited-pressure / mixed heat-addition) cycle thermal efficiency eta = 1 -
(1/r^(gamma-1)) * ((alpha*rho^gamma - 1)/((alpha - 1) + gamma*alpha*(rho -
1))) from the compression ratio r, the pressure ratio alpha of the
constant-volume heat-addition phase (alpha = P3/P2), the cutoff ratio rho of
the constant-pressure heat-addition phase (rho = V4/V3 = T4/T3) and the
specific-heat ratio gamma, the isentropic compression temperature ratio T2/T1
= r^(gamma-1) and the five-state temperature bookkeeping T2 = T1 *
r^(gamma-1), T3 = T2 * alpha (constant-volume phase), T4 = T3 * rho
(constant-pressure phase) and T5 = T1 * alpha * rho^gamma (isentropic
expansion 4 to 5 back to V5 = V1, closed form), the per-state pressure and
volume closed forms p2 = p1
* r^gamma, p3 = alpha * p2, p4 = p3, p5 = p1 * alpha * rho^gamma, v2 = v1/r,
v3 = v2, v4 = rho * v2, v5 = v1 with v1 = R * T1/p1, the mixed heat addition
q_in = cv * T2 * (alpha - 1) + cp * T2 * alpha * (rho - 1) with cv = cp/gamma
and the ideal-cycle mean effective pressure MEP = eta * q_in/(v1 - v2) from
the state-1 pressure and temperature, then the same four-stroke indicated and
brake power and specific-fuel-consumption bookkeeping as the two pack
siblings: four-stroke indicated power P_i = IMEP * V_d * (rpm/60)/2 from the
indicated mean effective pressure, the displacement and the crankshaft speed
(one power stroke per two crankshaft revolutions, the classic PLAN
bookkeeping), brake power P_b = P_i * eta_m at the mechanical efficiency,
brake specific fuel consumption BSFC = m_dot_fuel/P_b in kg/(kW h) and
lb/(hp h) through the exact unit bridge, indicated and brake thermal
efficiencies on the Jet-A lower heating value, and volumetric fuel flow from
the fuel flow and the Jet-A density, closed by a documented reference-only
compression-ignition band verdict (BSFC 0.35 to 0.42 lb/(hp h) and the
brake-thermal-efficiency window 0.3262 to 0.3806, the same published
compression-ignition band class the diesel leaf's worked example reports)
that reports the point's position and NEVER enforces it. Produces the
single-point summary dict with the ideal dual-cycle efficiency, the
compression temperature ratio, the five state temperatures, both heat
additions and the heat rejection, the ideal-cycle mean effective pressure,
indicated and brake power in watts and horsepower, BSFC in both reporting
units, thermal efficiencies, volumetric fuel flow and the band verdict in one
call. Does NOT do: the pure constant-pressure Diesel efficiency or Diesel
state-point bookkeeping (the diesel-cycle leaf owns the air-standard-diesel-
cycle model and its 0.613684212124 ceiling at 17 to 1 and cutoff 2.2; this
leaf's mixed-addition formula differs from the sibling's for every alpha
above 1, and the alpha-equals-1 limit is a test bound, never a computed
operating mode this leaf claims); the pure constant-volume Otto efficiency
(the piston-engine-cycle leaf owns eta = 1 - 1/r^(gamma-1) and its 0.678026275475
ceiling at 17 to 1; the sibling ceilings appear in this leaf's tests only as
limit and comparison bounds, never as own outputs); fuel-air cycle,
variable-gamma, real-gas dissociation or any real-cycle correction;
two-stroke, port-timing, scavenging, supercharger or turbocharger charging
content (declined seams of the wave-47/48 probes); volumetric-efficiency or
MBT empirics; gas turbine or turbofan cycle analysis, Brayton efficiency,
regenerator, real-cycle component losses or turbine SFC (gas-turbine-cycle
leaves); free-turbine, power-turbine matching, turboshaft or turboprop shaft
power with a propeller side (free-turbine, turboprop-cycle); propeller
efficiency, static thrust, equivalent shaft power or advance-ratio
bookkeeping (turboprop-cycle); installed thrust and drag bookkeeping or bleed
extraction (engine-airframe-integration); compressor or turbine stages,
pressure-ratio maps or corrected flow (axial-compressor leaves); rocket
sizing, nozzle, propellant, feed-cycle or injector content (rocket leaves);
altitude or density-ratio power lapse; any empirical engine map. IMEP,
mechanical efficiency, fuel flow, the Jet-A density and LHV and the state-1
pressure are documented inputs in the piston-engine-cycle documented-input
convention; there is no empirical engine map anywhere. The bands are reported
reference-only and never enforced: an out-of-band point is not an error and
the verdict function never raises on one.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants (values
verified by the spec-prep anchor run):
- GAMMA_AIR = 1.4 (air-standard specific-heat ratio default, overridable).
- CP_AIR = 1005.0 (air-standard constant-pressure specific heat in J/(kg K),
  the 1.005 kJ/(kg K) class value, overridable; cv = cp/gamma internally).
- T1_REF_K = 288.15 (reference inlet temperature in K, the ISA sea-level
  standard value, overridable).
- P1_REF_PA = 150000.0 (reference state-1 pressure in Pa, about 1.5 bar
  absolute at the boosted direct-injection inlet, overridable; the pressure
  datum of the ideal-cycle MEP closed form).
- R_AIR_J_PER_KG_K = 287.0 (dry-air gas constant in J/(kg K), the v1 = R*T1/p1
  datum of the MEP closed form, overridable).
- HOUR_S = 3600.0 (s per hour); KG_PER_LB = 0.45359237 (exact); W_PER_HP =
  745.6998715822702 (550 ft lbf/s in W, exact); M3_PER_L = 1.0e-3;
  L_PER_M3 = 1.0e3; US_GAL_PER_M3 = 264.17205235814845.
- KG_PER_KWH_PER_LB_PER_HP_HR = KG_PER_LB/(W_PER_HP*1.0e-3) =
  0.6082773878417611 (kg/(kW h) per lb/(hp h); the BSFC unit bridge).
- JET_A_LHV_J_PER_KG = 43.2e6 (Jet-A/kerosene net heating value,
  reference-only default, overridable); JET_A_DENSITY_KG_PER_M3 = 800.0
  (Jet-A class density, the 0.80 kg/L class value inside the ASTM D1655
  775-840 kg/m3 band, reference-only default, overridable).
- Reference-only compression-ignition bands, never enforced (the same
  published band class as the diesel sibling's worked example):
  BSFC_BAND_LB_PER_HP_HR = (0.35, 0.42);
  BSFC_BAND_KG_PER_KWH = (0.2128970857446164, 0.2554765028935397) derived by
  the same unit bridge; ETA_B_BAND = (0.3261878583333333,
  0.3805525013888889), the CI brake-thermal-efficiency window from the
  band-endpoint formula eta_b = 3.6e6/(b * LHV) evaluated at the kg/(kW h)
  equivalents of b = 0.42 and b = 0.36 lb/(hp h) (the receipt's 0.3262 to
  0.3806 window).

Defining relations (pin these exactly; every function derives from them):
- Air-standard dual (Sabathe / limited-pressure) thermal efficiency (mixed
  heat addition): eta = 1 - (1/r^(gamma-1)) * ((alpha*rho^gamma - 1)/((alpha
  - 1) + gamma*alpha*(rho - 1))), with r the compression ratio (r > 1), gamma
  the specific-heat ratio (gamma > 1), alpha the pressure ratio of the
  constant-volume heat-addition phase (alpha >= 1, alpha = P3/P2) and rho the
  cutoff ratio of the constant-pressure phase (rho = V4/V3 = T4/T3 with 1 <
  rho <= r; heat addition must end before bottom dead center, so the cutoff
  ratio never exceeds the compression ratio).
- Limit identities of the formula: alpha -> 1 recovers the Diesel closed
  form exactly and rho -> 1 recovers the Otto closed form exactly, so the
  dual ceiling interpolates between the two landed siblings' ceilings at the
  same compression ratio.
- Isentropic compression temperature ratio: T2/T1 = r^(gamma-1).
- State-point temperature bookkeeping: T2 = T1 * r^(gamma-1); T3 = T2 *
  alpha (constant-volume heat addition 2 to 3); T4 = T3 * rho (constant-
  pressure heat addition 3 to 4); T5 = T1 * alpha * rho^gamma (isentropic
  expansion 4 to 5 to V5 = V1, closed form).
- State-point pressure bookkeeping: p2 = p1 * r^gamma; p3 = alpha * p2; p4 =
  p3; p5 = p1 * alpha * rho^gamma. Volume bookkeeping per kg of air: v1 = R *
  T1/p1; v2 = v1/r; v3 = v2; v4 = rho * v2; v5 = v1. Every state satisfies p
  * v = R * T (ideal gas), a closed-form identity of the relations.
- Mixed heat addition per kg of air: q23 = cv * (T3 - T2) = (cp/gamma) * T2 *
  (alpha - 1) across the constant-volume phase, q34 = cp * (T4 - T3) = cp *
  T2 * alpha * (rho - 1) across the constant-pressure phase, q_in = q23 +
  q34, cv = cp/gamma. The inverse identities alpha = 1 + q23/(cv * T2) and
  rho = 1 + q34/(cp * T3) are the exact round trips.
- Constant-volume heat rejection 5 to 1: q_out = cv * (T5 - T1) = (cp/gamma)
  * T1 * (alpha * rho^gamma - 1). The temperature-form efficiency identity
  eta = 1 - q_out/q_in = 1 - (T5 - T1)/((T3 - T2) + gamma * (T4 - T3)) holds
  exactly.
- Ideal-cycle mean effective pressure: MEP = eta * q_in/(v1 - v2) = eta *
  q_in/(v1 * (1 - 1/r)) with v1 = R * T1/p1, returned in Pa. MEP is exactly
  linear in the state-1 pressure p1.
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
  air-standard dual eta is the ideal ceiling and sits above eta_b for any
  real point.
- Volumetric fuel flow: V_dot = m_dot_fuel / rho_fuel (m3/s), reported also
  in L/h and US gal/h.
- Band verdict: reference-only; each metric's position is 'below', 'inside'
  or 'above' against ETA_B_BAND and BSFC_BAND_LB_PER_HP_HR; the verdict dict
  carries enforced: False and NEVER raises for an out-of-band point.

Functions (signatures and ValueError rejections; no imports beyond math):
- dual_efficiency(compression_ratio, pressure_ratio, cutoff_ratio,
  gamma=GAMMA_AIR) -> eta (dimensionless). ValueError if inputs non-finite,
  compression_ratio <= 1, gamma <= 1, pressure_ratio < 1, cutoff_ratio <= 1,
  or cutoff_ratio > compression_ratio.
- isentropic_temperature_ratio(compression_ratio, gamma=GAMMA_AIR) -> T2/T1 =
  compression_ratio**(gamma-1). Same compression_ratio/gamma ValueErrors as
  dual_efficiency.
- compression_temperature(t1_k, compression_ratio, gamma=GAMMA_AIR) -> T2 (K)
  = t1_k * isentropic_temperature_ratio(...). ValueError if t1_k non-finite
  or <= 0, plus the ratio's ValueErrors.
- cv_phase_temperature(t2_k, pressure_ratio) -> T3 (K) = t2_k *
  pressure_ratio. ValueError if t2_k non-finite or <= 0, pressure_ratio
  non-finite or < 1.
- cp_phase_temperature(t3_k, cutoff_ratio) -> T4 (K) = t3_k * cutoff_ratio.
  ValueError if t3_k non-finite or <= 0, cutoff_ratio non-finite or <= 1.
- expansion_temperature(t1_k, pressure_ratio, cutoff_ratio,
  gamma=GAMMA_AIR) -> T5 (K) = t1_k * pressure_ratio * cutoff_ratio**gamma.
  ValueError if t1_k non-finite or <= 0, pressure_ratio non-finite or < 1,
  cutoff_ratio non-finite or <= 1, gamma non-finite or <= 1.
- cycle_state_temperatures(t1_k, compression_ratio, pressure_ratio,
  cutoff_ratio, gamma=GAMMA_AIR) -> dict {t1_k, t2_k, t3_k, t4_k, t5_k} from
  the state relations above. Same ValueErrors as dual_efficiency plus
  t1_k <= 0.
- cv_heat_addition_j_per_kg(t2_k, pressure_ratio, gamma=GAMMA_AIR,
  cp_j_per_kg_k=CP_AIR) -> q23 (J per kg air) = (cp_j_per_kg_k/gamma) *
  t2_k * (pressure_ratio - 1). ValueError if t2_k non-finite or <= 0,
  pressure_ratio non-finite or < 1, gamma non-finite or <= 1, cp non-finite
  or <= 0.
- cp_heat_addition_j_per_kg(t2_k, pressure_ratio, cutoff_ratio,
  cp_j_per_kg_k=CP_AIR) -> q34 (J per kg air) = cp_j_per_kg_k * t2_k *
  pressure_ratio * (cutoff_ratio - 1). ValueError if t2_k non-finite or <= 0,
  pressure_ratio non-finite or < 1, cutoff_ratio non-finite or <= 1, cp
  non-finite or <= 0.
- heat_addition_j_per_kg(t2_k, pressure_ratio, cutoff_ratio,
  gamma=GAMMA_AIR, cp_j_per_kg_k=CP_AIR) -> q_in = q23 + q34 (J per kg air).
  Same ValueErrors as the two phase functions.
- heat_rejection_j_per_kg(t1_k, t5_k, gamma=GAMMA_AIR,
  cp_j_per_kg_k=CP_AIR) -> q_out (J per kg air) = (cp_j_per_kg_k/gamma) *
  (t5_k - t1_k). ValueError if t1_k or t5_k non-finite or <= 0, t5_k <= t1_k,
  gamma non-finite or <= 1, cp non-finite or <= 0.
- mean_effective_pressure(t1_k, p1_pa, compression_ratio, pressure_ratio,
  cutoff_ratio, gamma=GAMMA_AIR, cp_j_per_kg_k=CP_AIR,
  r_air_j_per_kg_k=R_AIR_J_PER_KG_K) -> MEP in Pa from the relation above.
  ValueError if any input non-finite, t1_k <= 0, p1_pa <= 0, plus the
  dual_efficiency domain errors and cp/r_air <= 0.
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
- dual_cycle(compression_ratio, pressure_ratio, cutoff_ratio, imep_pa,
  displacement_m3, rpm, mechanical_efficiency, fuel_flow_kg_per_s,
  t1_k=T1_REF_K, p1_pa=P1_REF_PA, gamma=GAMMA_AIR,
  cp_j_per_kg_k=CP_AIR, lhv_j_per_kg=JET_A_LHV_J_PER_KG,
  fuel_density_kg_per_m3=JET_A_DENSITY_KG_PER_M3,
  r_air_j_per_kg_k=R_AIR_J_PER_KG_K) -> dict with keys: compression_ratio,
  pressure_ratio, cutoff_ratio, gamma, t1_k, p1_pa, eta_dual,
  temperature_ratio, t2_k, t3_k, t4_k, t5_k, cv_heat_addition_j_per_kg,
  cp_heat_addition_j_per_kg, heat_addition_j_per_kg,
  heat_rejection_j_per_kg, mean_effective_pressure_pa, imep_pa,
  displacement_m3, rpm, indicated_power_w, indicated_power_hp,
  mechanical_efficiency, brake_power_w, brake_power_hp, fuel_flow_kg_per_s,
  bsfc_kg_per_kwh, bsfc_lb_per_hp_hr, indicated_thermal_efficiency,
  brake_thermal_efficiency, volumetric_fuel_flow_m3_per_s,
  volumetric_fuel_flow_l_per_h, volumetric_fuel_flow_us_gal_per_h,
  band_verdict (nested dict). ValueErrors propagate from the chained
  functions; t1_k <= 0 and p1_pa <= 0 raise through the chain.

Identities to test (closed form, from the real anchor outputs):
- Receipt closed-form anchors at r = 17, gamma = 1.4: dual_efficiency(17.0,
  1.2, 2.2, 1.4) = 0.619491257553, reproducing the receipt's 0.6194912576
  within 1e-9 relative (the anchor run's own isclose gate); dual_efficiency(
  17.0, 1.5, 2.2, 1.4) = 0.624336871619 against the receipt's 0.6243368716;
  dual_efficiency(17.0, 2.0, 2.2, 1.4) = 0.628441566104 against the receipt's
  0.6284415661; dual_efficiency(17.0, 1.35, 2.0, 1.4) = 0.631646052581
  against the receipt's 0.6316460526.
- Interpolation ordering at r = 17: 0.613684212124 (Diesel bound at cutoff
  2.2, the sibling's own anchor) < 0.619491257553 (dual alpha 1.2, rho 2.2) <
  0.678026275475 (the same-r constant-volume ceiling), the mixed-addition
  ceiling interpolating between the two landed siblings' ceilings.
- Limit alpha -> 1: dual_efficiency(17.0, 1.0 + 1e-9, 2.2, 1.4) equals the
  Diesel closed form 0.613684212124 within 1e-9 relative, and
  dual_efficiency(17.0, 1.0, 2.2, 1.4) equals it within 1e-15 relative (the
  exact alpha = 1 point is the Diesel limit, a test bound, never a claimed
  operating mode).
- Limit rho -> 1: dual_efficiency(17.0, 1.2, 1.0 + 1e-9, 1.4) equals the
  constant-volume ceiling 0.678026275475 within 1e-9 relative, the same-r
  Otto ceiling the piston sibling owns.
- Pressure-ratio sensitivity at fixed r and rho (r = 17, rho = 2.2): alpha
  1.2 -> 0.619491257553 < alpha 1.5 -> 0.624336871619 < alpha 2.0 ->
  0.628441566104, so eta rises as the constant-volume phase lengthens, the
  approach toward the constant-volume ceiling.
- Cutoff-ratio sensitivity at fixed r and alpha (r = 16, alpha = 1.35): rho
  1.8 -> 0.632550215211 > rho 2.0 -> 0.622604338055 > rho 2.2 ->
  0.613014625635, so eta falls as the constant-pressure phase lengthens, the
  compression-ignition signature.
- Limit gamma -> 1: dual_efficiency(16.0, 1.35, 2.0, 1.0 + 1e-9) =
  2.4658257658e-09, below 1e-8, eta -> 0 as the specific-heat ratio
  approaches 1.
- Between-bounds identity at the worked compression ratio r = 16: the diesel
  bound at the same cutoff 0.613804581712 < dual 0.622604338055 < the Otto
  bound 0.670123022307, the physically sane interpolation the worked point
  must exhibit.
- Isentropic relation: isentropic_temperature_ratio(16.0, 1.4) =
  3.03143313302 = 16^0.4 and compression_temperature(288.15, 16.0, 1.4) =
  873.50745728 K.
- State identities at the worked point: t3 = alpha * t2, t4 = rho * t3 and
  t5 = t1 * alpha * rho^gamma hold to 1e-12 relative; q23 = 219468.748642
  J/kg and q34 = 1185131.24266 J/kg with q_in = 1404599.99131 J/kg exactly
  additive; the alpha round trip 1 + q23/(cv * t2) and the rho round trip
  1 + q34/(cp * t3) recover alpha and rho to 1e-15 relative.
- Temperature-form identity: 1 - q_out/q_in with q_out = 530089.943487 J/kg
  equals dual_efficiency(...) to 1e-12 relative at the worked point, and
  q_out = (cp/gamma) * (t5 - t1) holds to 1e-12 relative.
- Mean effective pressure: mean_effective_pressure(288.15, 1.5e5, 16.0, 1.35,
  2.0) = 1691937.3034 Pa (about 16.9 bar) and doubling the state-1 pressure
  doubles the MEP to 3383874.60681 Pa to 1e-12 relative (MEP exactly linear
  in p1); the ideal-gas closed forms p * v = R * T hold at states 2, 3 and 5
  to 1e-9 relative (p2 = 7275439.51925 Pa, p3 = 9821843.35099 Pa, p5 =
  534400.703863 Pa, v1 = 0.551327 m3/kg, v2 = 0.0344579375 m3/kg, v4 =
  0.068915875 m3/kg with R = 287.0).
- Unit-convention consistency: indicated_power(1.8e6, 2.0e-3, 2300.0) =
  69000.0 W exactly and brake_power(69000.0, 0.86) = 59340.0 W exactly, the
  receipt's four-stroke bookkeeping targets; the bar/L convention equals the
  Pa/m3 convention.
- Linear scalings: P_i doubles when rpm doubles at fixed IMEP and V_d, and
  doubles when V_d doubles at fixed IMEP and rpm; P_b = P_i exactly at
  eta_m = 1.0.
- Round trips: fuel_flow_from_bsfc(bsfc, P_b) recovers the input fuel flow to
  better than 1e-15 kg/s; eta_b = eta_i * eta_m exactly at the anchor.
- Physical ordering: brake_thermal_efficiency < eta_dual and brake_power <
  indicated_power at any mechanical efficiency below 1 (worked point 0.35221
  < 0.62260); eta_i > eta_b at any eta_m below 1 (0.40954 > 0.35221).
- Conversion bridge: KG_PER_KWH_PER_LB_PER_HP_HR = 0.6082773878417611; the
  worked point converts 0.236602628918 kg/(kW h) to 0.388971600206 lb/(hp h).
- Determinism: no imports beyond math; constants fixed; repeated runs
  byte-identical under BOTH interpreters (verified at spec prep).

## Worked example

High-speed direct-injection compression-ignition aircraft diesel at a cruise
rating, the dual-cycle leaf's worked point: compression ratio r = 16 (inside
the parent-required 8 to 16 window and the direct-injection CI class), alpha
= 1.35 (pressure ratio of the constant-volume heat-addition phase), rho = 2.0
(cutoff ratio of the constant-pressure phase), gamma = 1.4 (air standard),
inlet temperature T1 = 288.15 K, state-1 pressure p1 = 1.5e5 Pa, IMEP =
1.8e6 Pa (18 bar), displacement V_d = 2.0e-3 m3 (2.0 L), crankshaft speed
2300 rpm, mechanical efficiency eta_m = 0.86, fuel flow m_dot = 3.9e-3 kg/s
Jet-A at the reference density 800 kg/m3 and LHV 43.2 MJ/kg, cp 1005 J/(kg
K), R = 287.0 J/(kg K). All values below are REAL outputs of the spec-prep
anchor script anchor_dual_cycle.py (stdlib math, closed form; ALL CHECKS PASS
on the run, byte-identical under both interpreters, 36 checks).
- Ideal cycle: eta_dual = 1 - (1/16^0.4) * ((1.35 * 2.0^1.4 - 1)/((1.35 - 1)
  + 1.4 * 1.35 * (2.0 - 1))) = 0.622604338055, sitting between the same-r
  bounds 0.613804581712 (Diesel closed form at cutoff 2.0, the pure
  constant-pressure limit alpha = 1) and 0.670123022307 (the constant-volume
  ceiling 1 - 1/16^0.4), the interpolation identity; the isentropic
  compression temperature ratio is T2/T1 = 16^0.4 = 3.03143313302.
- State bookkeeping from T1 = 288.15 K: T2 = 873.50745728 K, T3 = T2 * 1.35
  = 1179.23506733 K (end of the constant-volume phase), T4 = T3 * 2.0 =
  2358.47013466 K (end of the constant-pressure phase), T5 = T1 * 1.35 *
  2.0^1.4 = 1026.58375212 K (end of the isentropic expansion back to V5 =
  V1), and the mixed heat addition q23 = 219468.748642 J/kg across the
  constant-volume phase plus q34 = 1185131.24266 J/kg across the
  constant-pressure phase gives q_in = 1404599.99131 J/kg (about 1.40 MJ per
  kg of air; the constant-volume phase q23 is the dual cycle's distinguishing
  heat input on top of the constant-pressure-addition-only model the alpha =
  1 limit would carry); the
  temperature-form identity 1 - q_out/q_in with q_out = 530089.943487 J/kg
  reproduces eta_dual to 1e-12 relative, and the alpha and rho round trips
  1 + q23/(cv * T2) and 1 + q34/(cp * T3) return 1.35 and 2.0 to 1e-15
  relative.
- Per-state pressures and volumes: v1 = R * T1/p1 = 0.551327 m3/kg, v2 =
  0.0344579375 m3/kg, v4 = 0.068915875 m3/kg; p2 = p1 * 16^1.4 =
  7275439.51925 Pa, p3 = alpha * p2 = 9821843.35099 Pa, p5 = p1 * alpha *
  2.0^1.4 = 534400.703863 Pa, with p * v = R * T verified at states 2, 3 and
  5 to 1e-9 relative.
- Mean effective pressure: the net work per kg of air is w_net = eta_dual *
  q_in = 874510.047819 J/kg, and MEP = w_net/(v1 - v2) = 1691937.3034 Pa
  (about 16.9 bar) at the 1.5 bar state-1 pressure, the order of magnitude
  of the 18 bar IMEP documented input, the physical-consistency check the
  worked point must exhibit; MEP scales exactly with p1 (at 3.0e5 Pa it
  doubles to 3383874.60681 Pa, verified to 1e-12 relative).
- Pressure-ratio sensitivity at r = 17, rho = 2.2 (the receipt magnitudes):
  alpha 1.2 gives 0.619491257553 and alpha 2.0 gives 0.628441566104, so a
  longer constant-volume phase raises efficiency toward the constant-volume
  ceiling at fixed r and rho, the dual-cycle signature that separates this
  leaf from the pure constant-pressure sibling.
- Cutoff-ratio sensitivity at the worked point: rho 1.8 gives 0.632550215211
  and rho 2.2 gives 0.613014625635, so a longer constant-pressure phase costs
  efficiency at fixed r and alpha.
- Indicated power: P_i = 1.8e6 * 2.0e-3 * (2300/60)/2 = 69000.0 W =
  92.5305241821 hp, the pack's four-stroke bookkeeping target (IMEP is a
  documented input, so the station shell reproduces the siblings' worked
  numbers exactly; the ideal eta_dual is reported alongside and never
  imposed on the power chain).
- Brake power: P_b = 69000.0 * 0.86 = 59340.0 W = 79.5762507966 hp.
- BSFC: m_dot * 3600 * 1000 / P_b = 0.236602628918 kg/(kW h) =
  0.388971600206 lb/(hp h), inside the published 0.35 to 0.42 lb/(hp h)
  compression-ignition band and the equivalent 0.2128970857446164 to
  0.2554765028935397 kg/(kW h) band.
- Thermal efficiencies on LHV: eta_i = 69000.0/(3.9e-3 * 43.2e6) =
  0.409544159544; eta_b = 59340.0/(3.9e-3 * 43.2e6) = 0.352207977208 =
  eta_i * eta_m exactly, inside the published CI brake-thermal-efficiency
  window 0.3261878583333333 to 0.3805525013888889 (the receipt's 0.3262 to
  0.3806) and below the ideal eta_dual (0.35221 < 0.62260), as it must be.
  The CI window itself sits above the piston sibling's published 0.25 to
  0.30 general-aviation window, a different published band for a different
  prime mover.
- Volumetric fuel flow: V_dot = 3.9e-3/800 = 4.875e-06 m3/s = 17.55 L/h =
  4.63621951889 US gal/h.
- Band verdict: eta_b_position 'inside' and bsfc_position 'inside' with
  enforced False (both metrics land in the published CI bands at this point;
  the verdict reports and never enforces).

## Validation list (deterministic checks the contract test must run)

1. Module import + constants match the spec values: GAMMA_AIR 1.4, CP_AIR
   1005.0, T1_REF_K 288.15, P1_REF_PA 150000.0, R_AIR_J_PER_KG_K 287.0,
   HOUR_S 3600.0, KG_PER_LB 0.45359237, W_PER_HP 745.6998715822702,
   US_GAL_PER_M3 264.17205235814845,
   KG_PER_KWH_PER_LB_PER_HP_HR 0.6082773878417611, JET_A_LHV_J_PER_KG 43.2e6,
   JET_A_DENSITY_KG_PER_M3 800.0, band tuples as pinned (isclose, never
   exact-float equality on derived constants): BSFC_BAND_LB_PER_HP_HR (0.35,
   0.42), BSFC_BAND_KG_PER_KWH (0.2128970857446164, 0.2554765028935397),
   ETA_B_BAND (0.3261878583333333, 0.3805525013888889).
2. Worked-example values within 1e-6 relative of the anchor outputs:
   eta_dual 0.622604338055, temperature_ratio 3.03143313302, t2_k
   873.50745728, t3_k 1179.23506733, t4_k 2358.47013466, t5_k
   1026.58375212, q23 219468.748642, q34 1185131.24266,
   heat_addition_j_per_kg 1404599.99131, heat_rejection_j_per_kg
   530089.943487, mean_effective_pressure_pa 1691937.3034, v1 0.551327,
   v2 0.0344579375, v4 0.068915875, p2 7275439.51925, p3 9821843.35099, p5
   534400.703863, indicated power 69000.0 W, brake power 59340.0 W, BSFC
   0.236602628918 kg/(kW h) and 0.388971600206 lb/(hp h), eta_i
   0.409544159544, eta_b 0.352207977208, volumetric fuel flow 4.875e-06
   m3/s, 17.55 L/h and 4.63621951889 US gal/h.
3. Receipt targets (r = 17) within 1e-6 relative: dual_efficiency(17.0, 1.2,
   2.2, 1.4) within 1e-6 relative of 0.6194912576 (anchor reproduces it to
   1e-9 relative); alpha 1.5 within 1e-6 relative of 0.6243368716; alpha 2.0
   within 1e-6 relative of 0.6284415661; alpha 1.35, rho 2.0 within 1e-6
   relative of 0.6316460526.
4. Limits: dual_efficiency(17.0, 1.0 + 1e-9, 2.2, 1.4) within 1e-6 relative
   of the Diesel closed form 0.613684212124; dual_efficiency(17.0, 1.0, 2.2,
   1.4) within 1e-12 relative of it; dual_efficiency(17.0, 1.2, 1.0 + 1e-9,
   1.4) within 1e-6 relative of the constant-volume ceiling 0.678026275475;
   dual_efficiency(16.0, 1.35, 2.0, 1.0 + 1e-9) below 1e-8.
5. Domain: efficiency rises as alpha grows at fixed (17.0, 2.2):
   0.619491257553 < 0.624336871619 < 0.628441566104; efficiency falls as rho
   grows at fixed (16.0, 1.35): 0.632550215211 > 0.622604338055 >
   0.613014625635; dual_efficiency(17.0, 1.35, 1.0, 1.4) raises ValueError
   (rho <= 1); dual_efficiency(2.0, 1.35, 2.2, 1.4) raises ValueError (rho
   above r); dual_efficiency(16.0, 0.9, 2.0, 1.4) raises ValueError (alpha
   below 1); the interpolation ordering holds at r = 16 (0.613804581712 <
   0.622604338055 < 0.670123022307) and at r = 17 (0.613684212124 <
   0.619491257553 < 0.678026275475).
6. State identities: t3 equals alpha * t2, t4 equals rho * t3 and t5 equals
   t1 * alpha * rho^gamma at the anchor within 1e-12 relative; q_in equals
   q23 + q34 within 1e-15 relative; the alpha round trip recovers 1.35
   within 1e-15 and the rho round trip recovers 2.0 within 1e-15; the
   temperature-form identity 1 - q_out/q_in equals eta_dual within 1e-12;
   q_out equals (cp/gamma) * (t5 - t1) within 1e-12; p * v = R * T holds at
   states 2, 3 and 5 within 1e-9 relative.
7. MEP: mean_effective_pressure(288.15, 1.5e5, 16.0, 1.35, 2.0) within 1e-6
   relative of 1691937.3034 Pa; doubling p1 doubles the MEP (3383874.60681
   Pa) within 1e-12 relative.
8. Round trips: fuel_flow_from_bsfc(bsfc, 59340.0) recovers 0.0039 kg/s
   within 1e-15; eta_b equals eta_i * eta_m at the anchor within 1e-15; the
   bar/L convention equals the Pa/m3 convention.
9. Band semantics: at the anchor point both positions are 'inside' with
   enforced False; an artificial out-of-band point (eta_b 0.45, BSFC 0.30
   lb/(hp h)) returns 'above' and 'below' without raising; enforced stays
   False.
10. Physical ordering: eta_b < eta_dual and P_b < P_i at eta_m 0.86; eta_i >
    eta_b; eta_b in the CI window (0.3262, 0.3806); BSFC in (0.35, 0.42)
    lb/(hp h) and in (0.2129, 0.2555) kg/(kW h).
11. All ValueErrors listed under Model fire: dual_efficiency at r 1.0, alpha
    0.9, rho 1.0, rho 2.2 with r 2.0, gamma 1.0 and nan; cv_phase_temperature
    at alpha 0.5; cp_phase_temperature at rho 1.0; expansion_temperature at
    rho 0.5; heat_rejection_j_per_kg at t5_k below t1_k; mean_effective_
    pressure at p1_pa 0; indicated_power at IMEP 0 and rpm negative;
    brake_power at eta_m 0 and eta_m 1.1; brake_specific_fuel_consumption at
    m_dot 0; bsfc_lb_per_hp_hr at inf; fuel_flow_from_bsfc at negative brake
    power; indicated_thermal_efficiency at negative LHV;
    brake_thermal_efficiency at P_b 0; volumetric_fuel_flow at density 0;
    ci_band_verdict at eta_b 0 and BSFC 0; dual_cycle at t1_k 0 and p1_pa 0
    through the chain.
12. Determinism: two identical runs return byte-identical outputs (verified
    at spec prep under both interpreters).
13. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for the build-time corpus file eval/hit1-wave48-dual-cycle.yaml)

1. "run the air-standard-dual-cycle for the high-speed compression-ignition
   aircraft powerplant at the 17 to 1 compression ratio: the dual-cycle
   thermal efficiency from the pressure-ratio-of-heat-addition across the
   constant-volume phase and the cutoff-ratio of the constant-pressure phase
   of the sabathe limited-pressure-cycle, then the indicated power from the
   mean-effective-pressure and the displacement and the brake power at the
   mechanical efficiency on the jet-a fuel"
2. "analyze the sabathe-cycle limited-pressure-cycle operating point of the
   high-speed compression-ignition aircraft engine: the air-standard-dual-
   cycle thermal efficiency from the pressure-ratio-of-heat-addition across
   the constant-volume phase and the cutoff-ratio across the constant-
   pressure phase of the mixed heat-addition model, and the jet-a fuel
   brake-specific-fuel-consumption band check for the dual-cycle powerplant"

The queries are the receipt gate (e) texts verbatim. The receipt's router
sim (exact replication of scripts/router_eval.py scoring over the real
657-SKILL.md index plus this hypothetical leaf) scored query 1 Hit@1
propulsion/reciprocating/dual-cycle at 40.0 with runner-up diesel-cycle at
31.5 (margin 8.5) and query 2 at 41.5 with runner-up diesel-cycle at 27.0
(margin 14.5); the zero-theft audit over all 1306 corpus tasks passed with 0
flips, and the leaf's two spec-time corpus tasks supply its 2-task parity at
build time (the wave-47 diesel precedent). The distinctive hyphenated tokens
(air-standard-dual-cycle, dual-cycle, sabathe-cycle, limited-pressure-cycle,
mixed-heat-addition, pressure-ratio-of-heat-addition, jet-a fuel) sit on no
router row and in no corpus task today, so Hit@1 is clean. The siblings'
owned lead triggers (air-standard-otto-cycle, piston-engine-cycle as a lead,
four-stroke-powerplant, air-standard-diesel-cycle, diesel-cycle-efficiency,
compression-ignition-powerplant, jet-a-fuel-cycle) are kept out of the lead
position; the diesel-cycle and cutoff-ratio wording appears only mid-query as
comparison and phase vocabulary, never as the lead tokens the query routes
on, and the dual-cycle and sabathe-cycle tokens lead both queries.

## Description/tag guidance for the builder

- Description: "Use when you must compute the operating point of a
  reciprocating high-speed compression-ignition aircraft powerplant: the
  air-standard dual-cycle thermal efficiency from the compression ratio, the
  specific-heat ratio, the pressure ratio of the constant-volume heat-
  addition phase and the cutoff ratio of the constant-pressure phase, the
  isentropic compression temperature ratio and state temperatures, the
  four-stroke indicated and brake power from the indicated mean effective
  pressure, displacement, crankshaft speed and mechanical efficiency, and
  the brake specific fuel consumption on Jet-A. Produces the single-point
  summary dict with the dual-cycle efficiency, heat additions, mean
  effective pressure, BSFC in both units, thermal efficiencies, volumetric
  fuel flow and the reference-only compression-ignition band verdict,
  reported and never enforced. Trigger: dual-cycle, air-standard-dual-cycle,
  sabathe-cycle, limited-pressure-cycle, mixed-heat-addition,
  pressure-ratio-of-heat-addition." (action verb compute; 117 words and 996
  characters verified at spec prep, within the <=148 word and <=1000 char
  limits.)
- metadata tags (EXACTLY as the receipt gate (f) lists them):
  [dual-cycle, air-standard-dual-cycle, sabathe-cycle, limited-pressure-
  cycle, mixed-heat-addition, pressure-ratio-of-heat-addition]
- FORBIDDEN tokens (sibling claims and token discipline): any Otto,
  spark-ignition or avgas claim in the description or tags
  (air-standard-otto-cycle, otto-cycle, otto as an own claim,
  spark-ignition as an own claim, ignition timing, MBT, avgas,
  four-stroke-powerplant as a standalone compound; plain four-stroke appears
  only inside the shared power-bookkeeping prose above, never as a tag or
  lead trigger); any Diesel-only model claim (air-standard-diesel-cycle,
  diesel-cycle as an own lead, diesel-cycle-efficiency,
  compression-ignition-powerplant, jet-a-fuel-cycle as a tag or lead;
  cutoff-ratio as a lead trigger, allowed only mid-phrase inside the model
  prose as in the receipt's own sim-verified queries; the alpha-equals-1
  Diesel limit appears only as a test bound, never in the description);
  turbine-family vocabulary: gas turbine, turbofan, turbojet, turboshaft,
  free turbine, power turbine, Brayton, regenerator, real cycle, turbine
  SFC, propeller efficiency, static thrust, equivalent shaft power, advance
  ratio, compressor or turbine stage, corrected flow; rocket vocabulary:
  rocket equation, nozzle, propellant, feed cycle, specific impulse,
  injector; engine-airframe installed thrust and drag bookkeeping; altitude
  or density-ratio power lapse; jet-fuel and kerosene used only inside
  Jet-A-named content, never as standalone tags. No generic single-word tags
  (no bare engine, power, fuel, cycle, heat, addition, ignition, dual,
  sabathe, pressure, ratio, ignition, compression-ratio, cutoff, cutoff-
  ratio, temperature, efficiency, aircraft) and no reuse of the siblings'
  owned tokens; mean-effective-pressure appears only inside the shared
  power-bookkeeping prose as a documented input, never as a standalone tag
  or lead trigger, and compression-ignition appears only inside the
  high-speed compression-ignition class prose, never as a standalone
  compound or tag.
- ZERO em dashes in every file; never the reserved gate-scanned word the
  spec-engineer kit bans (do not print it anywhere, in any spelling).
- Standards reference-only: far-33 (14 CFR Part 33, aircraft-engine
  airworthiness, which historically covered reciprocating and turbine
  aircraft engines including certified compression-ignition aircraft
  diesels) named + paraphrased, never reproduced verbatim.

## Routing note for the ops manager (not acted on by the builder)

This leaf fills the mixed heat-addition slot inside the existing wave-46/47
reciprocating pack, the third member of the air-standard cycle triad whose
first two members piston-engine-cycle (Otto) and diesel-cycle (Diesel) own;
no NEW-pack flag applies. At close the ops manager adds the
propulsion/reciprocating/dual-cycle router group row (Path
propulsion/reciprocating/dual-cycle, Skill Dual cycle, routing text over the
air-standard dual / Sabathe / limited-pressure / mixed heat-addition tokens,
keeping the Otto leaf's air-standard-otto-cycle and four-stroke-powerplant
triggers on the piston-engine-cycle row and the Diesel leaf's air-standard-
diesel-cycle, cutoff-ratio, compression-ignition and jet-a-fuel-cycle
triggers on the diesel-cycle row) and extends the reciprocating routing
guidance line 152 of skills/propulsion/SKILL.md with a mixed heat-addition /
high-speed compression-ignition sentence. The spec does not edit the router;
the builder touches only skills/propulsion/reciprocating/dual-cycle/ and its
eval and test files. After this leaf lands, the planner should declare the
reciprocating air-standard cycle triad COMPLETE (Otto, Diesel, dual) so later
waves do not keep re-mining the reciprocating textbook-cycle map; the
remaining reciprocating seams close on empirics or scope as tabled in the
receipt.

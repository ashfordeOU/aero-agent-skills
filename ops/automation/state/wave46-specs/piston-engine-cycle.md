# Wave-46 leaf spec: piston-engine-cycle (propulsion, reciprocating pack)

- Path: skills/propulsion/reciprocating/piston-engine-cycle/
- Pack: reciprocating (NEW pack, first leaf: the directory does not exist at
  spec prep, verified by whole-tree search; the router group row and guidance
  line for propulsion/reciprocating are added at close by the ops manager, the
  router file is not edited by this spec).
- Claim fences (quoted from the sibling frontmatter/body at spec prep; the
  family router Domain paragraph enumerates every engine class it routes and
  none is reciprocating):
  - family router skills/propulsion/SKILL.md (whole Domain paragraph, quoted):
    "Propulsion: gas turbine and turbofan thermodynamic cycle analysis (simple
    and regenerative Brayton), turbofan bypass design trades, launch-vehicle
    rocket sizing with the rocket equation and staging, rocket nozzle design,
    rocket propellant selection, and axial compressor stage and operating-map
    analysis." No reciprocating content: the enumerated classes are turbine,
    rocket, ramjet and electric only.
  - free-turbine (skills/propulsion/turboprop/free-turbine, quoted): "Use when
    the task is free-turbine sizing, power-turbine matching, turboprop shaft
    power, or turboshaft cycle estimates." This is the shaft-power turbine
    slot; a piston engine is not a turbine and is not claimed.
  - turboprop-cycle (skills/propulsion/turboprop/turboprop-cycle, quoted):
    "Use when you must analyze the turboprop powerplant cycle and propeller
    performance: compute the propeller (Froude) efficiency from the flight
    velocity and the slipstream velocity, the thrust delivered from the shaft
    power at the flight speed..." Its shaft power is an input that arrives
    from the turbine side; the propeller powerplant slot is not the
    reciprocating prime mover.
  - hypersonic-piston-theory (skills/aerodynamics/high-speed/, quoted): "a
    surface element moving into the gas compresses it like a piston pushing
    down a tube, so the local pressure ratio follows the closed form..." The
    word piston there is the Lighthill surface-pressure analogy, not an
    engine; no overlap with this leaf.
  - hydraulic-actuator-sizing (vehicle-design sizing, quoted): "the piston
    area and bore diameter from the actuator load and system pressure with
    the pressure-margin factor and mechanical efficiency". The piston-area
    token belongs to actuator sizing, not to an engine powerplant.
  - engine-airframe-integration (same family, quoted in the receipt): the
    installed-behavior bookkeeping "installed thrust from uninstalled gross
    thrust minus intake momentum (ram) drag, nacelle and pylon drag, and bleed
    and accessory power extraction losses" for turbine engines; no
    prime-mover thermodynamics.
  Whole-tree greps at spec prep (receipt gate (a), family-level): reciprocat 0
  files, whole-word otto 0 files, bsfc / brake-specific 0 files,
  mean-effective / imep / bmep 0 SKILL.md files across skills/ and eval/.
  GENUINE propulsion gap (receipt task-5 GO-2): the aircraft-engine
  prime-mover slot that no turbine, rocket, ramjet or electric leaf claims.
- Standards id: far-33 (grep-verified at spec prep: standards-map.yaml line
  193 "  - id: far-33", "14 CFR Part 33: Airworthiness Standards for Aircraft
  Engines", family regulation, FAA US government, public domain; the same
  reference id the family router and the two turboprop shaft-power siblings
  already carry; reference-only, cited and paraphrased never reproduced).
  Ledger Standard: far-33.
- Family: propulsion

## Claim

Compute the single operating point of a reciprocating four-stroke aircraft
powerplant for general-aviation propulsion, station math only: the
air-standard Otto cycle thermal efficiency eta = 1 - 1/r^(gamma-1) from the
compression ratio r and the specific-heat ratio gamma (the ideal efficiency
ceiling of the spark-ignition cycle, textbook air-standard method), the
four-stroke indicated power P_i = IMEP * V_d * (rpm/60)/2 from the indicated
mean effective pressure, the displacement and the crankshaft speed (one power
stroke per two crankshaft revolutions, the classic PLAN bookkeeping of
aircraft powerplant texts), the brake power P_b = P_i * eta_m at the
mechanical efficiency, the brake specific fuel consumption BSFC =
m_dot_fuel / P_b from the fuel mass flow and the brake power, the indicated
and brake thermal efficiencies on the fuel lower heating value, and the
volumetric fuel flow from the fuel mass flow and density, closed by a
documented reference-only GA band verdict (brake thermal efficiency 0.25-0.30
and BSFC 0.40-0.55 lb/(hp h), published bands for carbureted and fuel
injected four-stroke aircraft engines) that reports the point's position and
NEVER enforces it. Produces the single-point summary dict with the ideal cycle
efficiency, temperature ratio, indicated and brake power in watts and
horsepower, BSFC in both reporting units, thermal efficiencies, volumetric
fuel flow and the band verdict in one call. Does NOT do: gas-turbine or
turbofan cycle analysis, Brayton efficiency, regenerator, real-cycle
component losses or turbine SFC (gas-turbine-cycle leaves); free-turbine,
power-turbine matching, turboshaft or turboprop shaft power with a propeller
side (free-turbine, turboprop-cycle); propeller efficiency, static thrust,
equivalent shaft power or advance-ratio bookkeeping (turboprop-cycle);
installed thrust and drag bookkeeping or bleed extraction
(engine-airframe-integration); compressor or turbine stages, pressure-ratio
maps or corrected flow (axial-compressor leaves); rocket sizing, nozzle,
propellant or feed-cycle content (rocket leaves); the Lighthill piston
surface-pressure analogy (hypersonic-piston-theory); actuator piston-area
sizing (hydraulic-actuator-sizing); altitude or density-ratio power lapse
(off-design density-ratio tokens stay with turbofan-off-design; the corpus
query wording routes on the reciprocating-engine and four-stroke tokens
only); any empirical engine map. IMEP, mechanical efficiency, fuel flow and
density are documented inputs in the electrothermal/hydrazine documented-input
convention; there is no empirical engine map anywhere. The bands are reported
reference-only and never enforced: an out-of-band point is not an error and
the verdict function never raises on one.

## Model (implement exactly)

Pure stdlib, math only, deterministic, no RNG. Module constants (values
verified by the spec-prep anchor run):
- GAMMA_AIR = 1.4 (air-standard specific-heat ratio default, overridable).
- HOUR_S = 3600.0 (s per hour); KG_PER_LB = 0.45359237 (exact); W_PER_HP =
  745.6998715822702 (550 ft lbf/s in W, exact); M3_PER_L = 1.0e-3;
  L_PER_M3 = 1.0e3; US_GAL_PER_M3 = 264.17205235814845.
- KG_PER_KWH_PER_LB_PER_HP_HR = KG_PER_LB/(W_PER_HP*1.0e-3) = 0.6082773878417611
  (kg/(kW h) per lb/(hp h); the BSFC unit bridge).
- AVGAS_DENSITY_KG_PER_M3 = 720.0 (avgas class density, reference-only
  default, overridable); AVGAS_LHV_J_PER_KG = 43.5e6 (avgas net heating
  value, reference-only default, overridable).
- Reference-only GA bands, never enforced: ETA_B_BAND = (0.25, 0.30);
  BSFC_BAND_LB_PER_HP_HR = (0.40, 0.55);
  BSFC_BAND_KG_PER_KWH = (0.24331095513670445, 0.3345525633129686) derived by
  the same unit bridge.

Defining relations (pin these exactly; every function derives from them):
- Air-standard Otto thermal efficiency: eta = 1 - 1/r^(gamma-1), with r the
  compression ratio (r > 1) and gamma the specific-heat ratio (gamma > 1).
- Isentropic compression temperature ratio (the isentropic-process check):
  T2/T1 = r^(gamma-1); the efficiency identity eta = 1 - 1/(T2/T1) must hold.
- Four-stroke indicated power (SI): P_i = IMEP * V_d * (rpm/60)/2, IMEP in
  Pa, V_d in m3, rpm in rev/min; one power stroke per two crankshaft turns,
  so the revolution rate halves. Equivalent forms: P_i = IMEP * V_d * rpm /
  120, and the bar/L convention (IMEP in bar, V_d in L) gives the same value.
- Brake power: P_b = P_i * eta_m with eta_m the mechanical efficiency in
  (0, 1]. eta_m = 1.0 returns P_i exactly.
- BSFC (family shaft-power convention, kg/(kW h)): BSFC = m_dot_fuel * 3600 *
  1000 / P_b; report lb/(hp h) by dividing by
  KG_PER_KWH_PER_LB_PER_HP_HR.
- Thermal efficiencies on the fuel lower heating value: eta_i = P_i /
  (m_dot_fuel * LHV); eta_b = P_b / (m_dot_fuel * LHV) = eta_m * eta_i. The
  air-standard eta is the ideal ceiling and sits above eta_b for any real
  point.
- Volumetric fuel flow: V_dot = m_dot_fuel / rho_fuel (m3/s), reported also
  in L/h and US gal/h.
- Band verdict: reference-only; each metric's position is 'below', 'inside'
  or 'above' against ETA_B_BAND and BSFC_BAND_LB_PER_HP_HR; the verdict dict
  carries enforced: False and NEVER raises for an out-of-band point.

Functions (signatures and ValueError rejections; no imports beyond math):
- otto_efficiency(compression_ratio, gamma=GAMMA_AIR) -> eta (dimensionless).
  ValueError if inputs non-finite, compression_ratio <= 1, or gamma <= 1.
- isentropic_temperature_ratio(compression_ratio, gamma=GAMMA_AIR) -> T2/T1 =
  compression_ratio**(gamma-1). Same ValueErrors as otto_efficiency.
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
  inverse of brake_specific_fuel_consumption): bsfc_kg_per_kwh *
  brake_power_w / (3600.0 * 1000.0). ValueError if inputs non-finite,
  bsfc_kg_per_kwh <= 0, or brake_power_w <= 0.
- brake_thermal_efficiency(brake_power_w, fuel_flow_kg_per_s,
  lhv_j_per_kg=AVGAS_LHV_J_PER_KG) -> eta_b = brake_power_w /
  (fuel_flow_kg_per_s * lhv_j_per_kg). ValueError if inputs non-finite,
  brake_power_w <= 0, fuel_flow_kg_per_s <= 0, or lhv_j_per_kg <= 0.
- volumetric_fuel_flow(fuel_flow_kg_per_s,
  fuel_density_kg_per_m3=AVGAS_DENSITY_KG_PER_M3) -> m3/s =
  fuel_flow_kg_per_s / fuel_density_kg_per_m3. ValueError if inputs
  non-finite, fuel_flow_kg_per_s <= 0, or fuel_density_kg_per_m3 <= 0.
- ga_band_verdict(brake_thermal_eff, bsfc_lb_per_hp_hr_value) -> dict with
  eta_b_band, eta_b_position, bsfc_band_lb_per_hp_hr, bsfc_position (each
  position in {'below', 'inside', 'above'}) and enforced: False. ValueError
  only for non-finite, zero or negative inputs; NEVER for an out-of-band
  position.
- piston_engine_cycle(compression_ratio, imep_pa, displacement_m3, rpm,
  mechanical_efficiency, fuel_flow_kg_per_s, gamma=GAMMA_AIR,
  lhv_j_per_kg=AVGAS_LHV_J_PER_KG,
  fuel_density_kg_per_m3=AVGAS_DENSITY_KG_PER_M3) -> dict with keys:
  compression_ratio, gamma, eta_otto, temperature_ratio, imep_pa,
  displacement_m3, rpm, indicated_power_w, indicated_power_hp,
  mechanical_efficiency, brake_power_w, brake_power_hp, fuel_flow_kg_per_s,
  bsfc_kg_per_kwh, bsfc_lb_per_hp_hr, indicated_thermal_efficiency,
  brake_thermal_efficiency, volumetric_fuel_flow_m3_per_s,
  volumetric_fuel_flow_l_per_h, volumetric_fuel_flow_us_gal_per_h,
  band_verdict (nested dict). ValueErrors propagate from the chained
  functions.

Identities to test (closed form, from the real anchor outputs):
- Receipt closed-form anchor: otto_efficiency(8.5, 1.4) =
  0.5751531234287552, within 0.1 percent of the receipt's published 0.575
  (absolute difference 1.531234e-4, about 0.027 percent).
- Limit r -> 1: otto_efficiency(1.0 + 1e-9, 1.4) = 4.000000330961484e-10,
  so eta -> 0 as the compression ratio approaches 1; r <= 1 raises.
- Limit gamma -> 1: otto_efficiency(8.5, 1.0 + 1e-9) = 2.1400663463566616e-09,
  so eta -> 0 as the specific-heat ratio approaches 1; gamma <= 1 raises.
- Isentropic relation: isentropic_temperature_ratio(8.5, 1.4) =
  2.353789224180173 and 1 - 1/temperature_ratio equals eta_otto exactly
  (float equality holds at the anchor).
- Unit-convention consistency: indicated_power with IMEP in Pa and V_d in m3
  equals the bar/L convention (IMEP 9.5 bar, V_d 5.4 L) exactly, and
  indicated_power(900e3, 4.0e-3, 2700.0) = 81000.0 W exactly, reproducing the
  receipt's "about 81 kW indicated" bookkeeping target; brake_power(81000.0,
  0.85) = 68850.0 W reproduces the receipt's "about 69 kW brake".
- Linear scalings: P_i doubles when rpm doubles at fixed IMEP and V_d, and
  doubles when V_d doubles at fixed IMEP and rpm; P_b = P_i exactly at
  eta_m = 1.0.
- Round trips: fuel_flow_from_bsfc(bsfc, P_b) recovers the input fuel flow to
  better than 1e-15 kg/s; eta_b = eta_i * eta_m exactly at the anchor.
- Physical ordering: brake_thermal_efficiency < eta_otto and brake_power <
  indicated_power at any mechanical efficiency below 1 (anchor point: 0.29677
  < 0.57515).
- Conversion bridge: KG_PER_KWH_PER_LB_PER_HP_HR = 0.6082773878417611; the
  worked point converts 0.2788671023965142 kg/(kW h) to
  0.4584538369673203 lb/(hp h).
- Determinism: no imports beyond math; constants fixed; repeated runs
  byte-identical under BOTH interpreters (verified at spec prep).

## Worked example

Lycoming O-320 class general-aviation four-stroke flat-four at a cruise
rating: compression ratio r = 8.5, gamma = 1.4 (air standard), IMEP =
9.5e5 Pa (9.5 bar), displacement V_d = 5.4e-3 m3 (5.4 L), crankshaft speed
2700 rpm, mechanical efficiency eta_m = 0.85, fuel flow m_dot = 7.6e-3 kg/s
avgas at the reference density 720 kg/m3 and LHV 43.5 MJ/kg. All values below
are REAL outputs of the spec-prep anchor script anchor_piston_engine_cycle.py
(stdlib math, closed form; ALL CHECKS PASS on the run, byte-identical under
both interpreters).
- Ideal cycle: eta_otto = 1 - 1/8.5^0.4 = 0.5751531234287552, reproducing the
  receipt's 0.575 anchor within 0.1 percent (about 0.027 percent high); the
  isentropic compression temperature ratio is T2/T1 = 8.5^0.4 =
  2.353789224180173, and eta = 1 - 1/(T2/T1) holds exactly. The ideal
  efficiency sits in the published 0.57-0.58 class for this compression
  ratio.
- Indicated power: P_i = 9.5e5 * 5.4e-3 * (2700/60)/2 = 115425.0 W =
  154.7874746915061 hp.
- Brake power: P_b = 115425.0 * 0.85 = 98111.25 W = 131.56935348778018 hp
  (about 82 percent of the 160 hp class rating at the cruise point).
- BSFC: m_dot * 3600 * 1000 / P_b = 0.2788671023965142 kg/(kW h) =
  0.4584538369673203 lb/(hp h), inside the published 0.40-0.55 lb/(hp h) band
  and the equivalent 0.24331-0.33455 kg/(kW h) band.
- Thermal efficiencies on LHV: eta_i = 115425.0/(7.6e-3 * 43.5e6) =
  0.34913793103448276; eta_b = 98111.25/(7.6e-3 * 43.5e6) =
  0.2967672413793103 = eta_i * eta_m exactly, inside the published 0.25-0.30
  GA brake-thermal-efficiency band and below the ideal eta_otto (0.29677 <
  0.57515), as it must be.
- Volumetric fuel flow: V_dot = 7.6e-3/720 = 1.0555555555555555e-05 m3/s =
  38.0 L/h = 10.03853798960964 US gal/h, a realistic avgas cruise burn for
  this power class.
- Band verdict: eta_b_position 'inside' and bsfc_position 'inside' with
  enforced False (both metrics land in the published GA bands at this point;
  the verdict reports and never enforces).

## Validation list (deterministic checks the contract test must run)

1. Module import + constants match the spec values: GAMMA_AIR 1.4, HOUR_S
   3600.0, KG_PER_LB 0.45359237, W_PER_HP 745.6998715822702, US_GAL_PER_M3
   264.17205235814845, KG_PER_KWH_PER_LB_PER_HP_HR 0.6082773878417611,
   AVGAS_DENSITY_KG_PER_M3 720.0, AVGAS_LHV_J_PER_KG 43.5e6, band tuples as
   pinned (isclose, never exact-float equality on derived constants).
2. Worked-example values within 1e-6 relative of the anchor outputs: eta_otto
   0.5751531234287552, temperature_ratio 2.353789224180173, indicated power
   115425.0 W, brake power 98111.25 W, BSFC 0.2788671023965142 kg/(kW h) and
   0.4584538369673203 lb/(hp h), eta_i 0.34913793103448276, eta_b
   0.2967672413793103, volumetric fuel flow 1.0555555555555555e-05 m3/s,
   38.0 L/h and 10.03853798960964 US gal/h.
3. Receipt targets: eta_otto(8.5, 1.4) within 0.1 percent of 0.575;
   indicated_power(900e3, 4.0e-3, 2700.0) == 81000.0 W within 1e-6 relative
   of the receipt's 81 kW figure; brake_power at eta_m 0.85 == 68850.0 W
   within 1e-6 relative of the receipt's 69 kW figure.
4. Limits: eta_otto(1.0 + 1e-9, 1.4) below 1e-8; eta_otto(8.5, 1.0 + 1e-9)
   below 1e-8; both approach 0 as required.
5. Isentropic identity: 1 - 1/isentropic_temperature_ratio(8.5, 1.4) equals
   otto_efficiency(8.5, 1.4); temperature ratio equals 8.5**0.4.
6. Unit-convention consistency: bar/L and Pa/m3 conventions give the identical
   P_i; P_i doubles with rpm and with displacement at fixed other inputs;
   P_b == P_i at eta_m = 1.0.
7. Round trips: fuel_flow_from_bsfc(bsfc(0.0076, 98111.25), 98111.25)
   recovers 0.0076 kg/s within 1e-15; eta_b == eta_i * eta_m at the anchor
   within 1e-15.
8. Band semantics: at the anchor point both positions are 'inside' with
   enforced False; an artificial out-of-band point (eta_b 0.35, BSFC 0.6)
   returns 'above' for both without raising; enforced stays False.
9. Physical ordering: eta_b < eta_otto and P_b < P_i at eta_m 0.85; eta_b in
   (0.25, 0.30); BSFC in (0.40, 0.55) lb/(hp h) and in (0.24, 0.30) kg/(kW
   h).
10. All ValueErrors listed under Identities fire: otto_efficiency at r 1.0,
    gamma 1.0 and nan; isentropic_temperature_ratio at r 1.0;
    indicated_power at IMEP 0, V_d negative and rpm 0 and inf;
    brake_power at eta_m 0, eta_m 1.01 and P_i negative;
    brake_specific_fuel_consumption at m_dot 0 and P_b negative;
    fuel_flow_from_bsfc at bsfc 0; brake_thermal_efficiency at P_b 0 and LHV
    negative; volumetric_fuel_flow at density 0; ga_band_verdict at eta_b 0;
    piston_engine_cycle at r 1.0.
11. Determinism: two identical runs return byte-identical outputs (verified
    at spec prep under both interpreters).
12. Test passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3). No exact-float equality on
    computed sums; use assertAlmostEqual/math.isclose everywhere.

## Corpus fragment (2 verbatim queries for eval/hit1-wave46-piston-engine-cycle.yaml)

1. "size the piston-engine-cycle for the 180 horsepower four-stroke aircraft
   powerplant at 2700 rpm: the air-standard-otto-cycle thermal efficiency at
   the 8.5 to 1 compression ratio, indicated power from the
   mean-effective-pressure and the displacement, brake power at the 0.85
   mechanical efficiency, and the brake-specific-fuel-consumption at the
   cruise rating" (routes on piston-engine-cycle, air-standard-otto-cycle,
   mean-effective-pressure, brake-specific-fuel-consumption,
   reciprocating-engine, four-stroke tokens)
2. "analyze the reciprocating-engine powerplant altitude bookkeeping for the
   general-aviation aircraft: otto-cycle efficiency from the compression
   ratio, brake-horsepower at altitude from the sea-level rating with the
   density-ratio power lapse, and the specific-fuel-consumption band check
   for the four-stroke piston engine" (routes on reciprocating-engine,
   otto-cycle, brake-horsepower, four-stroke, piston-engine tokens)
intent lines: "propulsion; reciprocating four-stroke aircraft powerplant
station bookkeeping: air-standard Otto cycle efficiency, indicated power from
mean effective pressure, displacement and crankshaft speed, brake power at
mechanical efficiency, and brake specific fuel consumption" and "propulsion;
reciprocating-engine powerplant cycle assessment: Otto efficiency from the
compression ratio, indicated and brake power bookkeeping, and the
reference-only GA BSFC band check for the four-stroke piston engine". The
second query's altitude-lapse wording routes on the reciprocating-engine and
four-stroke tokens only; the density-ratio power lapse itself is not modeled
by this leaf (see Claim).

## Description/tag guidance for the builder

- Description: "Use when you must compute the operating point of a
  reciprocating four-stroke aircraft powerplant for general-aviation
  propulsion: the air-standard Otto cycle thermal efficiency from the
  compression ratio and the specific-heat ratio, the four-stroke indicated
  power from the indicated mean effective pressure, the displacement and the
  crankshaft speed, the brake power at the mechanical efficiency, and the
  brake specific fuel consumption from the fuel flow and the brake power.
  Produces the single-point summary dict with the ideal cycle efficiency,
  indicated and brake power, BSFC in both reporting units, thermal
  efficiencies, volumetric fuel flow and the reference-only general-aviation
  band verdict in one call, the published bands reported and never enforced.
  Trigger: piston-engine-cycle, air-standard-otto-cycle, compression ratio
  Otto efficiency, four-stroke engine, mean effective pressure, indicated
  power, brake power, mechanical efficiency, brake specific fuel
  consumption, BSFC." (action verb compute; 131 words and 991 characters
  verified at spec prep, within the <=148 word and <=1000 char limits.)
- metadata tags (EXACTLY as the receipt gate (f) lists them):
  [piston-engine-cycle, air-standard-otto-cycle, mean-effective-pressure,
  brake-specific-fuel-consumption, reciprocating-engine-powerplant,
  four-stroke-powerplant]
- FORBIDDEN tokens (sibling claims and token discipline): turbine-family
  vocabulary anywhere in the description or tags: gas turbine, turbofan,
  turbojet, turboshaft, free turbine, power turbine, Brayton, regenerator,
  real cycle, SFC or bare specific-fuel-consumption, propeller efficiency,
  static thrust, equivalent shaft power, advance ratio, compressor or
  turbine stage, pressure ratio, corrected flow; rocket vocabulary: rocket
  equation, nozzle, propellant, feed cycle, specific impulse; the Lighthill
  piston surface-pressure analogy tokens of hypersonic-piston-theory and the
  actuator piston-area tokens of hydraulic-actuator-sizing (piston is only
  ever the engine prime mover here, inside piston-engine-cycle and
  four-stroke-powerplant compounds); engine-airframe installed thrust and
  drag bookkeeping; density-ratio power lapse and altitude-lapse modeling
  claims. No generic single-word tags (no bare engine, power, fuel,
  efficiency, ratio, compression-ratio, otto, stroke, aircraft, avgas) and
  no reuse of turboprop or turbofan SFC tokens; compression-ratio appears
  only inside the longer distinctive tokens, never as a standalone tag, to
  avoid pressure-ratio ambiguity with axial-compressor rows.
- ZERO em dashes in every file; never the word that the spec-engineer kit's
  reserved-word ban names (it is a gate-scanned token, do not print it
  anywhere).
- Standards reference-only: far-33 (14 CFR Part 33, aircraft-engine
  airworthiness, which historically covered reciprocating and turbine
  aircraft engines) named + paraphrased, never reproduced verbatim.

## Routing note for the ops manager (not acted on by the builder)

This leaf creates the new pack directory propulsion/reciprocating/ as its
first leaf. At close the ops manager adds the propulsion/reciprocating router
group row (Path propulsion/reciprocating/piston-engine-cycle, Skill Piston
engine cycle, routing text over the Otto cycle, mean effective pressure,
indicated and brake power and BSFC tokens) and a routing guidance line to
skills/propulsion/SKILL.md. The spec does not edit the router; the builder
touches only skills/propulsion/reciprocating/piston-engine-cycle/ and its
eval and test files.

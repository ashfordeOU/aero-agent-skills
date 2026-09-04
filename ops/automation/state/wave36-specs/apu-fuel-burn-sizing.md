# Wave-36 leaf spec: apu-fuel-burn-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/apu-fuel-burn-sizing/
- Pack: sizing. Closest siblings: aircraft-electrical-load-analysis (the
  generator electrical kW is an INPUT here, never recomputed; the ELA
  leaf's wave-35 duplication concern is avoided by keeping the load
  rollup there and the APU fuel burn here), engine-sizing (main-engine
  thrust SFC; APU is a zero-thrust shaft/bleed powerplant), bleed-air-
  system-sizing (sizes the engine bleed manifold and thermal budget; APU
  fuel burn for a bleed load is computed HERE because the APU is a
  separate shaft/bleed power source), hydraulic-system-sizing (unrelated
  pumps). Whole-tree grep: "APU" hits are fire-protection zones, FHA
  functions, and one electrical consumer test only; zero leaf computes
  APU fuel burn. ZERO owners.
- Standards id: far-25 (reference-only; 25.903 powerplant/APU context).
  Ledger Standard: far-25.
- Family: vehicle-design

## Claim

Compute the auxiliary power unit fuel burn at a fixed electrical and
bleed load at the conceptual level: convert the generator electrical
output to the required generator shaft power through the generator
efficiency, convert the bleed load to its pumping-power equivalent with
the adiabatic compressor work relation at the stated compressor pressure
ratio and inlet temperature, sum the shaft and bleed loads into the total
equivalent shaft load, and convert to fuel flow through the thermal
efficiency and fuel lower heating value. Produces the generator shaft
power, the bleed pumping-power equivalent, the total equivalent shaft
load, and the fuel flow in kg/s and kg/h.

Does NOT do: the electrical load rollup and generator sizing (aircraft-
electrical-load-analysis owns generator kW as its output, input here);
main-engine thrust fuel flow (engine-sizing SFC); bleed manifold and
thermal budget (bleed-air-system-sizing); APU fire protection
(fire-protection-sizing).

## Model (implement exactly)

Module constants:
- CP_AIR = 1005.0 (J/kg K).
- GAMMA_AIR = 1.4.
- ETA_GEN_DEFAULT = 0.85 (generator efficiency).
- ETA_COMP_DEFAULT = 0.75 (APU load compressor efficiency).
- ETA_TH_DEFAULT = 0.18 (APU thermal efficiency at the load point).
- LHV_DEFAULT = 43.2e6 (J/kg, jet fuel lower heating value).
- T_INLET_DEFAULT = 288.0 (K, compressor inlet temperature).

Conventions: electrical load in W; bleed in kg/s at a stated pressure
ratio (absolute total-pressure ratio across the load compressor);
adiabatic work per kg: cp * T_in * (PR^((gamma-1)/gamma) - 1).

Functions (pure stdlib):
- generator_shaft_power(p_elec_w, eta_gen = ETA_GEN_DEFAULT) -> float W.
  ValueErrors: p_elec < 0; eta_gen <= 0 or > 1.
- bleed_pumping_power(m_bleed_kg_s, pressure_ratio, t_inlet_k =
  T_INLET_DEFAULT, eta_comp = ETA_COMP_DEFAULT) -> float W using
  cp*T_in*(PR^((gamma-1)/gamma)-1)*m/eta_comp. ValueErrors: m <= 0;
  pressure_ratio <= 1; t_inlet <= 0; eta_comp <= 0 or > 1.
- total_shaft_load(p_elec_w, m_bleed_kg_s, pressure_ratio, eta_gen =
  ETA_GEN_DEFAULT, eta_comp = ETA_COMP_DEFAULT, t_inlet_k =
  T_INLET_DEFAULT) -> dict {generator_shaft_w, bleed_pumping_w,
  total_shaft_w}.
- apu_fuel_burn(total_shaft_w, eta_th = ETA_TH_DEFAULT, lhv_j_kg =
  LHV_DEFAULT) -> dict {fuel_kg_s, fuel_kg_h} = W/(eta_th*LHV) and *3600.
  ValueErrors: total_shaft_w <= 0; eta_th <= 0 or > 1; lhv <= 0.
- apu_summary(p_elec_w, m_bleed_kg_s, pressure_ratio, eta_gen =
  ETA_GEN_DEFAULT, eta_comp = ETA_COMP_DEFAULT, eta_th =
  ETA_TH_DEFAULT) -> dict with the four outputs above plus the fuel burn
  kg/h.

Identity to test: generator shaft power = p_elec / eta_gen exactly;
fuel kg/h = fuel kg/s * 3600; doubling total load doubles fuel flow.

## Worked example

Reference APU load point: 30 kW electrical output at 0.85 generator
efficiency; 0.40 kg/s bleed at pressure ratio 3.5 from 288 K inlet with
0.75 compressor efficiency.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- generator shaft = 30000/0.85 = 35294.1 W (35.3 kW).
- ratio term = 3.5^0.2857 = 1.4304; bleed pumping = 0.40*1005*288*
  (1.4304-1)/0.75 = 66435.2 W (66.4 kW).
- total shaft load = 35294.1 + 66435.2 = 101729.3 W (101.7 kW).
- fuel flow = 101729.3/(0.18*43.2e6) = 0.013082 kg/s = 47.10 kg/h.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: p_elec < 0; eta out of (0,1]; m_bleed <= 0; pressure_ratio
  <= 1; t_inlet <= 0; lhv <= 0; total_shaft_load <= 0.
- Generator: 30000/0.85 = 35294.1 within 1e-1.
- Bleed pumping: 66435.2 within 1e-1; pressure ratio 1 gives 0 W.
- Total: 101729.3 within 1e-1.
- Fuel: 0.013082 kg/s within 1e-6; 47.10 kg/h within 1e-2; kg/h ==
  kg/s*3600 within 1e-9.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-apu-fuel-burn-sizing.yaml)

Query 1 (copy verbatim):
  "compute the apu fuel burn for a generator electrical load of 30 kw with a 0.4 kg per second bleed load at pressure ratio 3.5"
  intent: "vehicle-design; APU fuel burn from shaft and bleed load"
  expected_skill: "vehicle-design/sizing/apu-fuel-burn-sizing"
Query 2 (copy verbatim):
  "estimate the auxiliary power unit fuel flow in kg per hour at a fixed electrical and bleed load point"
  intent: "vehicle-design; APU load compressor pumping power and fuel flow"
  expected_skill: "vehicle-design/sizing/apu-fuel-burn-sizing"
Task ids: w36-apu-fuel-burn-sizing-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the APU fuel burn:" and
include the outputs in the Claim. First tag: apu-fuel-burn-sizing.
Additional tags ONLY: apu-load-compressor, auxiliary-power-unit-fuel,
apu-generator-shaft-power, bleed-pumping-power, apu-fuel-flow-rate.
NEVER single generic words (apu, fuel, burn, generator, bleed, shaft,
power, load). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): duty cycle, generator rating,
essential load (aircraft-electrical-load-analysis); thrust, sfc, takeoff
thrust (engine-sizing); duct diameter, precooler (bleed-air-system-
sizing); fire zone, extinguishing (fire-protection-sizing).

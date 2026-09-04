---
name: apu-fuel-burn-sizing
description: "Use when you must compute the APU fuel burn: take the generator electrical output and the bleed mass flow at a fixed load point for a conceptual aircraft or rotorcraft auxiliary power unit, convert the electrical output into generator shaft power through the generator efficiency, convert the bleed mass flow into its load-compressor pumping-power equivalent with the adiabatic compressor work relation at the stated pressure ratio, sum both into the total equivalent shaft load, and convert that load into fuel flow through the APU thermal efficiency and the fuel lower heating value. Produces the generator shaft power, the bleed pumping-power equivalent, the total equivalent shaft load, and the fuel flow in kg/s and kg/h. Trigger: apu fuel burn, auxiliary power unit fuel flow, apu load compressor, bleed pumping power, apu generator shaft power, apu fuel flow rate."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [apu-fuel-burn-sizing, apu-load-compressor, auxiliary-power-unit-fuel, apu-generator-shaft-power, bleed-pumping-power, apu-fuel-flow-rate]
  version: 0.1.0
  author: AeroSkills
---

# APU Fuel Burn Sizing (vehicle-design/sizing/apu-fuel-burn-sizing)

Use when you must compute the fuel burn of the auxiliary power unit
(APU) at a fixed electrical and bleed load point on a conceptual
aircraft or rotorcraft. The APU is a small shaft and bleed powerplant
that produces no propulsive force: it drives a generator and a load
compressor, so its fuel flow follows from the electrical output
converted back through the generator efficiency plus the bleed mass
flow priced as adiabatic compression work, all divided by the APU
thermal efficiency and the fuel lower heating value. This leaf
implements that model in pure Python, stdlib only. It pairs with
vehicle-design/sizing/aircraft-electrical-load-analysis, which owns the
electrical load rollup and supplies the generator electrical output as
the input here; the main-engine fuel flow analog lives in
vehicle-design/sizing/engine-sizing.

## Domain quick reference

- Generator shaft power: P_gen = P_elec / eta_gen, with the default
  generator efficiency eta_gen = 0.85. The electrical output is the
  AFTER generator efficiency, so the shaft side always carries more.
- Adiabatic compression work per kg of bleed: w = cp * T_in *
  (PR^((gamma-1)/gamma) - 1), with cp = 1005 J/kg K and gamma = 1.4.
  PR is the absolute total-pressure ratio across the APU load
  compressor and T_in the compressor inlet temperature (288 K default).
- Bleed pumping-power equivalent: P_bleed = m_dot_bleed * w /
  eta_comp, with the default load compressor efficiency eta_comp =
  0.75. Bleed is priced in kg/s, never in kW.
- Total equivalent shaft load: P_total = P_gen + P_bleed. The APU must
  deliver this shaft power to hold the fixed load point.
- Fuel flow: m_dot_fuel = P_total / (eta_th * LHV), with the default
  thermal efficiency eta_th = 0.18 and jet fuel LHV = 43.2 MJ/kg; the
  hourly rate is exactly 3600 times the kg/s rate.
- Valid inputs: pressure ratio must exceed 1, every efficiency lies in
  (0, 1], bleed flow and inlet temperature and LHV are positive, and
  the electrical load is non-negative. All other values raise
  ValueError.
- FAR 25.903 frames the powerplant installation context for the APU
  and its controls; the relations above are standard engineering
  methodology, summary-only.

## Workflow

1. Take the generator electrical output P_elec (W) from the electrical
   load analysis and the bleed demand m_dot_bleed (kg/s) at the load
   compressor pressure ratio PR from the bleed system context.
2. Convert the electrical output to the required generator shaft power
   with generator_shaft_power(p_elec_w, eta_gen).
3. Convert the bleed flow to its pumping-power equivalent with
   bleed_pumping_power(m_bleed_kg_s, pressure_ratio, t_inlet_k,
   eta_comp).
4. Sum both loads into one record with
   total_shaft_load(p_elec_w, m_bleed_kg_s, pressure_ratio): the dict
   carries generator_shaft_w, bleed_pumping_w and total_shaft_w.
5. Convert the total equivalent shaft load to the fuel flow with
   apu_fuel_burn(total_shaft_w, eta_th, lhv_j_kg): the dict carries
   fuel_kg_s and fuel_kg_h.
6. For a one-call result at the default 288 K inlet, run
   apu_summary(p_elec_w, m_bleed_kg_s, pressure_ratio), which returns
   all five outputs.
7. Confirm the deterministic checks with the contract test
   scripts/test_apu_fuel_burn_sizing.py.

## Worked example

Reference APU load point: 30 kW electrical output at 0.85 generator
efficiency, 0.40 kg/s bleed at pressure ratio 3.5 from a 288 K inlet
with 0.75 compressor efficiency, thermal efficiency 0.18 and
LHV 43.2 MJ/kg. Module outputs:

- Generator shaft power: 30000 / 0.85 = 35294.1 W (35.3 kW).
- Ratio term: 3.5^((1.4-1)/1.4) - 1 = 0.4304; bleed pumping power:
  0.40 * 1005 * 288 * 0.4304 / 0.75 = 66435.2 W (66.4 kW).
- Total equivalent shaft load: 35294.1 + 66435.2 = 101729.3 W
  (101.7 kW).
- Fuel flow: 101729.3 / (0.18 * 43.2e6) = 0.013082 kg/s, which is
  47.10 kg/h; the module reports 47.0969 kg/h and the kg/h rate is
  3600 * 0.013082 to float precision.
- The bleed side dominates: the 66.4 kW pumping burden is nearly twice
  the 35.3 kW generator shaft load at this point.

## Verification

- Confirm generator_shaft_power(30000) returns 35294.1 W, within 0.1
  of 30000 / 0.85.
- Confirm bleed_pumping_power(0.40, 3.5) returns 66435.2 W, within 0.1
  of the adiabatic-work hand value, and that the pressure ratio term
  vanishes as PR approaches 1 (the continuous zero-work limit; PR of
  exactly 1 is rejected).
- Confirm total_shaft_load(30000, 0.40, 3.5) totals 101729.3 W, the
  exact sum of its two parts.
- Confirm apu_fuel_burn gives 0.013082 kg/s within 1e-6 and
  47.10 kg/h within 1e-2, with fuel_kg_h equal to 3600 * fuel_kg_s
  within 1e-9.
- Confirm doubling the total shaft load doubles the fuel flow, and
  that the dict keys are exactly generator_shaft_w, bleed_pumping_w,
  total_shaft_w, fuel_kg_s, fuel_kg_h in the documented order.
- Confirm ValueError rejection of a negative electrical load, bleed
  flow at or below zero, pressure ratio at or below 1, inlet
  temperature at or below zero, shaft load at or below zero, LHV at or
  below zero, and any efficiency outside (0, 1].
- Run the contract test offline: python3
  scripts/test_apu_fuel_burn_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/aircraft-electrical-load-analysis: the load
  rollup and generator sizing that produce the electrical output used
  as the input here.
- vehicle-design/sizing/engine-sizing: the main-engine fuel flow and
  sizing analog for the propulsion powerplant.
- vehicle-design/sizing/fire-protection-sizing: the APU compartment
  fire protection that is specified there, not here.

## Pitfalls

- Treating the generator electrical output as shaft power: the shaft
  side is P_elec / eta_gen (35294 W for a 30 kW output at 0.85), so
  sizing the fuel burn on 30 kW alone understates the load by about
  18%.
- Pricing the bleed in kg/s as if it were power: the pumping burden
  only appears after the adiabatic work relation at the stated
  pressure ratio (66.4 kW for 0.40 kg/s at PR 3.5), so a bare bleed
  flow number has no fuel-flow meaning.
- Accepting a pressure ratio of 1 or below: a load compressor must
  raise the total pressure, so the guard rejects PR <= 1 and the
  zero-work point only exists as the continuous limit from above.
- Reporting the kg/s fuel rate when the hourly rate is wanted: the
  two differ by a factor of 3600 (0.013 kg/s versus 47.1 kg/h).
- Recomputing the electrical load rollup here: the generator kW is the
  output of the electrical-load-analysis leaf and an input to this
  one, so duplicating the rollup would drift the two leaves apart.
- Borrowing the main-engine fuel flow relation: the APU is a shaft and
  bleed powerplant with no propulsive output, so engine-sizing owns
  the main-engine relation and this leaf prices only the shaft and
  bleed burden.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_apu_fuel_burn_sizing.py

The test covers the reference load point (30 kW electrical, 0.40 kg/s
bleed at pressure ratio 3.5) against the spec magnitude bounds, the
generator identity P_elec / eta_gen, the zero-work continuous limit of
the pressure ratio term, linear scaling of the pumping power with mass
flow, the kg/h = 3600 * kg/s identity, the doubling-load doubling-fuel
identity, exact dict key contracts for the three dict functions,
determinism, and ValueError rejection of every non-physical input in
the validation list.

## Compliance

- Standards referenced, not reproduced: FAR 25.903 is the
  powerplant installation and APU context for this sizing (25.903
  powerplant/APU per standards-map.yaml); the thermodynamic relations
  above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

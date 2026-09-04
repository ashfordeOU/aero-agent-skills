---
name: afterburner-cycle
description: "Use when you must analyze an afterburning gas turbine cycle with reheat: compute the afterburner fuel-air ratio from the duct energy balance across the turbine exit and the afterburner exit total temperatures with a combustion efficiency, the reheat fuel flow for the core mass flow, the dry and reheat nozzle exit velocities from a fully expanded ideal isentropic nozzle, the dry and reheat gross thrust, the thrust augmentation ratio, and the specific fuel consumption with and without reheat. Produces the reheat fuel flow, augmentation ratio, and dry versus reheat SFC values that gate an afterburner cycle assessment in the FAR-33 engine context. Trigger: afterburner cycle, reheat fuel air ratio, thrust augmentation ratio, reheat temperature rise, dry versus reheat thrust, reheat specific fuel consumption, afterburner nozzle exit velocity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: gas-turbine-cycle
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [afterburner-cycle, reheat-fuel-air-ratio, thrust-augmentation-ratio, reheat-temperature-rise, dry-versus-reheat-thrust, reheat-specific-fuel-consumption, afterburner-nozzle-exit-velocity]
  version: 0.1.0
  author: AeroSkills
---

# Afterburner (Reheat) Cycle (propulsion/gas-turbine-cycle/afterburner-cycle)

Use when the task is the afterburning (reheat) topping block of a gas
turbine: reheat fuel is burned in the duct between the turbine exit and
the nozzle to raise the gas temperature, which lifts the nozzle exit
velocity and thrust at the cost of specific fuel consumption. This leaf
implements the standard model in pure Python, stdlib only: the reheat
fuel-air ratio from the duct energy balance, the reheat fuel flow, the
dry and reheat nozzle exit velocities from a fully expanded ideal
isentropic nozzle, the dry and reheat gross thrust, the thrust
augmentation ratio, and the specific fuel consumption with and without
reheat. It pairs with the gas-turbine-cycle and real-cycle-effects
leaves, which supply the core upstream (the turbine exit state t04, p04
comes from the core analysis), and with combustor-design for the main
combustor context. The fully expanded ideal nozzle is a documented
simplification: real nozzles add a thrust coefficient below one.

## Domain quick reference

- Reheat fuel-air ratio from the duct energy balance:
  f_ab = (1 + f_core) * CP * (t05 - t04) / (ETA_AB * LHV). The heat to
  raise the turbine exit products (air plus core fuel, 1 + f_core kg per
  kg of air) from t04 to t05 is divided by the useful heat released per
  kg of reheat fuel, ETA_AB * LHV.
- Reheat fuel flow: mdot_f_ab = f_ab * mdot_core.
- Nozzle static temperature after isentropic expansion:
  Te = Tt * (p_amb / p_total)^((GAMMA - 1) / GAMMA), GAMMA = 1.33.
- Fully expanded ideal nozzle exit velocity: v = sqrt(2 * CP *
  (Tt - Te)), CP = 1150 J/(kg K). Fully expanded means the exit pressure
  equals ambient, so the pressure thrust term is zero and the CP form
  carries the velocity; R = 287 J/(kg K) is documented but not used.
- Dry gross thrust: F_dry = mdot_core * (1 + f_core) * v_dry, with the
  nozzle entry at the turbine exit temperature t04.
- Reheat gross thrust: F_reheat = mdot_core * (1 + f_core + f_ab) *
  v_reheat, with the nozzle entry at the afterburner exit temperature
  t05.
- Thrust augmentation ratio: F_reheat / F_dry, about 1.4 for a typical
  augmented turbofan at full reheat.
- Specific fuel consumption: sfc = mdot_fuel / F in kg/(N s); multiply
  by 1e6 for mg/(N s).
- Module constants: CP = 1150.0 J/(kg K), LHV = 43.0e6 J/kg kerosene,
  ETA_AB = 0.97, GAMMA = 1.33, R = 287.0 J/(kg K). Units are SI
  throughout: K, Pa, kg/s, m/s, N, kg/(N s).
- FAR-33 frames the engine certification context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the operating point: the turbine exit total temperature t04_k and
   total pressure p04_pa (take them from the gas-turbine-cycle or
   real-cycle-effects core analysis), the core fuel-air ratio f_core,
   the core air mass flow mdot_core_kg_s, the chosen afterburner exit
   total temperature t05_k, and the ambient pressure p_amb_pa.
2. Compute the reheat fuel-air ratio with afterburner_far; the function
   rejects t05 <= t04 because an afterburner must add temperature.
3. Convert it to a reheat fuel flow with afterburner_fuel_flow.
4. Get the dry and reheat nozzle exit velocities with
   nozzle_exit_velocity, evaluated at t04 and at t05 with the same
   pressure ratio; the function requires p_total > p_amb for the fully
   expanded model.
5. Compute the dry gross thrust with thrust_dry and the reheat gross
   thrust with thrust_reheat (pass the f_ab from step 2).
6. Form the thrust augmentation ratio with augmentation_ratio.
7. Compute the specific fuel consumption with sfc for each mode: the
   core fuel flow f_core * mdot_core over the dry thrust, and the total
   fuel flow (f_core + f_ab) * mdot_core over the reheat thrust.
8. Run the whole operating point with analyze for the complete summary
   dict with all nine SI values.
9. Confirm the deterministic checks with the contract test
   scripts/test_afterburner_cycle.py.

## Worked example

Augmented turbofan at full reheat: turbine exit 900 K, f_core 0.02,
core flow 100 kg/s, afterburner exit 1700 K (an 800 K reheat
temperature rise), p04 3.0e5 Pa, ambient 1.01325e5 Pa.

- f_ab = 1.02 * 1150 * 800 / (0.97 * 43e6) = 0.022498.
- mdot_f_ab = 0.022498 * 100 = 2.2498 kg/s.
- Dry nozzle: Te = 900 * (1.01325 / 3)^(0.33 / 1.33) = 687.6 K;
  v_dry = sqrt(2 * 1150 * (900 - 687.6)) = 699.1 m/s.
- Reheat nozzle: Te = 1298.7 K; v_reheat = 960.8 m/s.
- F_dry = 102 * 699.1 = 71,308 N (spec anchor 71,307 N, within 50 N).
- F_reheat = 104.2498 * 960.8 = 100,165 N (spec anchor 100,162 N,
  within 50 N).
- Augmentation ratio = 100,165 / 71,308 = 1.405.
- sfc_dry = 2.0 / 71,308 = 2.805e-5 kg/(N s) = 28.05 mg/(N s);
  sfc_reheat = 4.2498 / 100,165 = 4.243e-5 kg/(N s) = 42.43 mg/(N s),
  spec anchor 42.42 mg/(N s) within 2%. Reheat adds about 40% thrust
  but roughly doubles the specific fuel consumption, which is why
  military augmented engines use reheat only for dash and takeoff.

## Verification

- Confirm afterburner_far(900, 1700, 0.02) returns 0.022498 within
  1e-6, and that afterburner_fuel_flow gives 2.2498 kg/s within 1e-3.
- Confirm nozzle_exit_velocity returns 699.1 m/s at 900 K and 960.8 m/s
  at 1700 K, each within 1.0 m/s.
- Confirm thrust_dry returns 71,308 N within 50 N of the 71,307 N anchor
  and thrust_reheat returns 100,165 N within 50 N of the 100,162 N
  anchor.
- Confirm augmentation_ratio 1.405 within 0.005 and the identity
  F_reheat / F_dry from analyze equals the standalone ratio.
- Confirm sfc values are within 2% of the 28.05 and 42.42 mg/(N s)
  anchors, and that reheat SFC exceeds dry SFC.
- Confirm every invalid input raises ValueError: t05 <= t04, t04 <= 0,
  f_core < 0, non-positive mass flow, p04 <= p_amb, p_amb <= 0, zero
  fuel flow or negative fuel flow in sfc, non-positive dry thrust in
  augmentation_ratio.
- Run the contract test offline: python3
  scripts/test_afterburner_cycle.py (35 tests, deterministic).

## Related leaves

- propulsion/gas-turbine-cycle/gas-turbine-cycle: the ideal Brayton core
  upstream of the reheat duct; supplies t04 for the dry nozzle.
- propulsion/gas-turbine-cycle/real-cycle-effects: the non-ideal core
  with component efficiencies, the realistic source of t04 and p04.
- propulsion/gas-turbine-cycle/regenerative-cycle: the recuperated cycle
  alternative, which trades exhaust heat instead of burning reheat fuel.
- propulsion/gas-turbine-cycle/combustor-design: the main combustor
  fuel-air chemistry, distinct from the reheat duct topping block.
- propulsion/ramjet/ramjet-cycle: the continuous supersonic combustion
  cycle, the alternative high-speed propulsion path.
- propulsion/turbofan/turbofan-cycle: the turbofan core context of the
  augmented military engine.

## Pitfalls

- Feeding an afterburner exit temperature at or below the turbine exit:
  t05 must exceed t04 or the duct energy balance is unphysical — the
  function rejects t05 <= t04 with ValueError, so the 800 K reheat rise
  in the worked example is the intended input shape.
- Ignoring the core fuel in the duct mass balance: the energy balance
  heats (1 + f_core) kg of gas per kg of air, and the reheat thrust
  carries (1 + f_core + f_ab) mdot_core, so dropping f_core (0.02 in
  the example) shifts both the fuel-air ratio and the thrust.
- Using the ideal-nozzle velocity for a real nozzle: the fully expanded
  ideal isentropic nozzle is a documented simplification with no
  pressure thrust term; real nozzles add a thrust coefficient below
  one, so the model overstates v and F.
- Evaluating the nozzle below the choked condition: nozzle_exit_velocity
  requires p_total > p_amb for the fully expanded model; feeding an
  unchoked or inverted pressure ratio raises ValueError rather than
  returning a partial-expansion velocity.
- Selling reheat as an efficiency measure: the worked example adds about
  40% thrust (augmentation 1.405) but roughly doubles the specific fuel
  consumption (28.05 to 42.43 mg/(N s)) — the augmentation ratio alone
  hides the SFC cost.
- Reading the wrong SFC mode: sfc_dry divides only the core fuel flow
  f_core * mdot_core by the dry thrust while sfc_reheat divides the
  total fuel flow (f_core + f_ab) * mdot_core by the reheat thrust;
  swapping the denominators inverts the comparison.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_afterburner_cycle.py

The test covers the worked-example anchors (reheat fuel-air ratio,
reheat fuel flow, dry and reheat nozzle exit velocities, dry and reheat
gross thrust, augmentation ratio, both SFC values), scaling trends with
temperature rise, mass flow and pressure ratio, the augmentation
identity at equal thrusts, the v = F / mdot_gas round trip inside
analyze, and ValueError rejection of every non-physical input in the
validation list.

## Compliance

- Standards referenced, not reproduced: FAR-33 (Airworthiness Standards:
  Aircraft Engines) frames the engine certification context of the
  afterburner cycle assessment; the relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-27 leaf spec: afterburner-cycle (propulsion, gas-turbine-cycle pack)

- Path: skills/propulsion/gas-turbine-cycle/afterburner-cycle/
- Pack: gas-turbine-cycle (existing siblings: gas-turbine-cycle,
  real-cycle-effects, regenerative-cycle, combustor-design)
- Standards ids: far-33  (Ledger Standard: far-33)
- Family: propulsion

## Claim

Analyze an afterburning (reheat) gas turbine cycle: given the turbine
exit total temperature and the chosen afterburner exit temperature,
compute the afterburner fuel-to-air ratio from the energy balance with
a combustion efficiency, the afterburner fuel flow for the core mass
flow, the dry and reheat nozzle exit velocities with a fully expanded
ideal nozzle, the dry and reheat gross thrust, the thrust augmentation
ratio, and the specific fuel consumption with and without reheat.
Produces the reheat fuel flow, augmentation ratio, and SFC values that
gate an afterburner cycle assessment in the FAR-33 engine context.

Does NOT do: compute the core real-cycle gas turbine performance with
component efficiencies and combustor pressure loss (real-cycle-effects
owns the non-ideal Brayton core); analyze a regenerative cycle with a
recuperator (regenerative-cycle); design the combustor or afterburner
hardware geometry (combustor-design owns the main combustor); or
resolve ramjet combustion (ramjet-cycle). This leaf is the core
topping cycle only: reheat fuel addition between the turbine exit and
the nozzle.

## Model (implement exactly)

Module constants (documented typicals):
- CP = 1150.0 J/(kg K) (constant specific heat, reheat duct),
- LHV = 43.0e6 J/kg (kerosene lower heating value),
- ETA_AB = 0.97 (afterburner combustion efficiency),
- GAMMA = 1.33, R = 287.0 J/(kg K) (for the isentropic nozzle
  expansion exponent only; exit velocity uses CP*deltaT).

Inputs:
- t04_k (float, turbine exit total temperature),
- f_core (float, core fuel-to-air ratio, e.g. 0.02),
- mdot_core_kg_s (float, core air mass flow),
- t05_k (float, afterburner exit (nozzle entry) total temperature),
- p04_pa (float, nozzle entry total pressure, used for the expansion
  ratio),
- p_amb_pa (float, ambient pressure).

Functions:
- afterburner_far(t04_k, t05_k, f_core) -> float:
  f_ab = (1 + f_core) * CP * (t05_k - t04_k) / (ETA_AB * LHV).
  ValueError when t05 <= t04 or t04 <= 0 or f_core < 0.
- afterburner_fuel_flow(f_ab, mdot_core_kg_s) -> float f_ab *
  mdot_core.
- nozzle_exit_velocity(t_total_k, p_total_pa, p_amb_pa) -> float:
  Te = Tt * (p_amb/p_total)^((GAMMA-1)/GAMMA);
  v = sqrt(max(0, 2 * CP * (Tt - Te))).  ValueError when p_total <=
  p_amb (underexpansion not modeled; require p_total > p_amb) or
  Tt <= 0.
- thrust_dry(t04_k, p04_pa, p_amb_pa, mdot_core_kg_s, f_core) ->
  float: mdot_gas = mdot_core * (1 + f_core); F = mdot_gas * v_dry
  (fully expanded, pressure term zero).
- thrust_reheat(...) -> float: mdot_gas = mdot_core * (1 + f_core +
  f_ab); F = mdot_gas * v_reheat.
- augmentation_ratio(F_reheat, F_dry) -> float F_rh / F_dry.
- sfc(fuel_flow_kg_s, thrust_N) -> float kg/(N s).
- analyze(...) -> dict {f_ab, mdot_f_ab, v_dry, v_reheat, F_dry,
  F_reheat, augmentation_ratio, sfc_dry, sfc_reheat} all SI.

ValueError on non-positive mass flow, t04 <= 0, t05 <= t04, p04 <=
p_amb, p_amb <= 0.

## Worked example

Turbine exit 900 K, f_core 0.02, core flow 100 kg/s, afterburner exit
1700 K, p04 3.0e5 Pa, ambient 1.01325e5 Pa.
- f_ab = (1.02)*1150*800/(0.97*43e6) = 0.0225 (assert module value
  within 1e-6 of 0.022498 computed above: 1.02*1150*800 = 938400;
  /41.71e6 = 0.022498).
- mdot_f_ab = 2.2498 kg/s (assert within 1e-3).
- Te_dry = 900*(1.01325/3)^(0.33/1.33) = 900*0.33775^0.24812 =
  687.55 K; v_dry = sqrt(2*1150*(900-687.55)) = 699.1 m/s (assert
  within 1.0).
- v_reheat at 1700 K: Te_rh = 1298.7 K; v = sqrt(2*1150*(1700-1298.7))
  = 960.8 m/s (assert within 1.0).
- F_dry = 102 * 699.1 = 71307 N (assert within 50).
- F_reheat = (102+2.2498) * 960.8 = 104.25*960.8 = 100162 N (assert
  within 50).
- augmentation_ratio = 100162/71307 = 1.405 (assert within 0.005).
- sfc_dry = 2.0/71307 = 2.805e-5 kg/(N s) = 28.05 mg/(N s) (assert
  within 2%); sfc_reheat = (2.0+2.2498)/100162 = 4.242e-5 kg/(N s) =
  42.42 mg/(N s) (assert within 2%).
- ValueErrors: t05 == t04, p04 == p_amb, mdot 0.
Keep at least 16 test methods (far, fuel flow, exit velocities, dry
and reheat thrust, augmentation, both SFCs, ValueErrors).

## Corpus tasks (ids w27-afterburner-cycle-1/2)

Distinctive tokens: afterburner cycle, reheat fuel air ratio, thrust
augmentation ratio, reheat temperature rise, dry versus reheat thrust,
reheat specific fuel consumption, afterburner nozzle exit velocity.
Avoid: compressor reheat factor (multi-stage-compressor), recuperator
effectiveness (regenerative-cycle), combustor pressure loss
(real-cycle-effects), ramjet fuel (ramjet-cycle).

1. "compute the afterburner fuel air ratio and fuel flow for the
   turbofan with turbine exit at 900 K and a 1700 K reheat temperature,
   then find the thrust augmentation ratio against the dry nozzle"
2. "compare the dry and reheat specific fuel consumption for the
   afterburning engine: 100 kg/s core flow at 0.02 core fuel air ratio
   with the 800 K afterburner temperature rise"

## SKILL body notes

Pair with gas-turbine-cycle and real-cycle-effects (core upstream),
combustor-design (main combustor sibling), and rocket no? none: also
note the military/augmented-turbofan context and that the fully
expanded ideal nozzle is a documented simplification (real nozzles
add a thrust coefficient). Standards referenced (FAR-33 engine
certification context) not reproduced.

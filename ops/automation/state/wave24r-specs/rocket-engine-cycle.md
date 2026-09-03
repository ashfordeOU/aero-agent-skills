# Wave-24R leaf spec: rocket-engine-cycle (propulsion)

- Path: skills/propulsion/rocket/rocket-engine-cycle/
- Pack: rocket (existing: combustion-chamber-design, nozzle-design,
  propellant-selection, rocket-sizing, rocket-staging,
  solid-rocket-motor, thrust-vector-control)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: propulsion

## Claim

Liquid rocket engine feed-cycle selection and preliminary cycle
analysis: compare pressure-fed and pump-fed (gas-generator,
staged-combustion, expander) cycles for a required chamber pressure,
thrust, and propellant combination; compute the pump discharge pressure,
the required pump power, the turbine drive power, and the cycle
efficiency/performance penalty. Produces the feasible cycle set, the
pump and turbine power balance, and a recommendation verdict with the
mass/performance trade.

Does NOT do: chamber geometry (combustion-chamber-design), nozzle
contour (nozzle-design), propellant choice (propellant-selection),
vehicle staging (rocket-staging, rocket-sizing), solid motors
(solid-rocket-motor), TVC. This leaf is the liquid engine FEED SYSTEM
cycle.

## Model (implement exactly)

Given: chamber pressure p_c (Pa), thrust F (N), vacuum Isp_target or
the propellant pair, sea-level ambient p_a (default 0 for vacuum), and
engine cycle type.

Simplified engine balance (SI; module constants: rho_ox, rho_fuel from a
small propellant table for LOX/RP-1, LOX/LH2, N2O4/MMH, monoprop
hydrazine; g0 = 9.80665; mu no need).
- Mass flow from thrust and Isp: mdot = F / (Isp * g0) (Isp input,
  default from a small table per propellant pair, e.g. LOX/RP-1 300 s
  vacuum, LOX/LH2 430 s vacuum, N2O4/MMH 320 s vacuum; reference-only
  typical values).
- Oxidizer/fuel split by mixture ratio r_m (input per pair, default
  LOX/RP-1 2.56, LOX/LH2 5.5, N2O4/MMH 1.9): mdot_ox =
  mdot * r_m/(1+r_m); mdot_f = mdot/(1+r_m).

Feed pressure requirements:
- Pump-fed: pump discharge pressure p_pump = p_c + p_losses (p_losses
  default 2.0e6 Pa total injector+line loss, input).
- Pressure-fed: tank pressure p_tank = p_c + p_losses; required tank
  mass penalty scales with p_tank (simple: tank_wall_mass ~ p_tank *
  volume * rho_wall / (2*sigma_wall), with module constants for a
  titanium tank; this is the mass trade the verdict reports).
Pump power per propellant: P_pump = mdot_prop * (p_pump - p_tank_inlet)
/ (rho_prop * eta_pump) with p_tank_inlet ~ p_c for the pump-fed case
the pump sees the tank pressure at its inlet (assume 0.3 MPa inlet
pressure default for pump-fed; document), eta_pump default 0.7.
Total pump power P_pump_tot = sum over both propellants.

Turbine drive:
- Gas-generator cycle: a fraction of the propellant (default 3% of the
  total mdot) is burned in the gas generator at p_gg (default 0.8 *
  p_c) and expanded through the turbine; turbine power
  P_turb = mdot_gg * cp_gg * T_gg * eta_turb * (1 - (p_exit/p_gg)^((g-1)/g))
  with defaults cp_gg = 2000 J/(kg K), T_gg = 1200 K, gamma_gg = 1.2,
  eta_turb = 0.6, p_exit = p_a + 0.1 MPa? use p_exit = 0.2 MPa default
  (document); the turbine must cover P_pump_tot: check the power balance
  and report the deficit/surplus.
- Staged-combustion: the turbine drive gas is at full chamber pressure
  (p_turb_inlet = p_c * 1.5 preburner, default), so the turbine pressure
  ratio is much higher and ALL propellant passes through the preburner;
  model as the same turbine equation with the full mdot and a higher
  inlet pressure, plus a note that staged combustion gives no
  performance loss from the drive gas.
- Expander cycle: the fuel is heated in the cooling jacket and drives
  the turbine; only feasible for fuels with good heat capacity (LH2
  primary); model requires the fuel flow and a limited pressure ratio
  (p_c <= ~10 MPa feasibility bound, documented reference-only).
Feasibility verdicts:
- Expander: feasible only for LH2-fueled engines below the p_c bound.
- Pressure-fed: feasible for low p_c (<= ~3 MPa typical for small
  storable systems; documented bound as a module constant + assumption).
- Gas-generator and staged-combustion feasible across the range.

Functions:
- propellant_pair_properties(pair_name) -> (rho_ox, rho_fuel, r_m,
  isp_vac) or ValueError
- mass_flow_split(f, isp, g0, r_m) -> (mdot, mdot_ox, mdot_f)
- pump_discharge_pressure(p_c, p_losses)
- pump_power(mdot_prop, p_discharge, p_inlet, rho_prop, eta_pump)
- turbine_power(mdot_gas, cp, t_inlet, eta_turb, gamma, p_inlet,
  p_exit)
- cycle_feasibility(cycle, propellant, p_c) -> (bool, reason)
- pressure_fed_tank_mass(p_tank, propellant_volume, ...) -> kg
- engine_cycle_analysis(cycle, f, p_c, propellant, ...) -> summary dict
  (feasible, pump_power_total, turbine_power, power_balance,
  drive_mass_fraction, tank_mass_penalty, verdict)
ValueError on: non-positive thrust/pressure/mass flow, unknown
propellant/cycle, eta outside (0,1], non-finite inputs.

## Worked example

LOX/RP-1 gas-generator engine: F = 1.0e6 N, Isp = 300 s, r_m = 2.56,
p_c = 10 MPa, p_losses = 2 MPa, eta_pump = 0.7, gg fraction 3%.
Anchors (from your module):
- mdot ~= 340 kg/s; mdot_ox ~= 244 kg/s, mdot_f ~= 96 kg/s.
- p_pump ~= 12 MPa; P_pump_ox ~= 244*(12e6-0.3e6)/(1140*0.7) ~= 3.6 MW;
  P_pump_f ~= 96*(12e6-0.3e6)/(820*0.7) ~= 1.95 MW; total ~ 5.5 MW
  (assert your computed values within 10% of these ballparks, then quote
  exact values).
- mdot_gg ~= 10.2 kg/s; P_turb with the defaults ~=
  10.2*2000*1200*0.6*(1-(0.2e6/(0.8*10e6))^((1.2-1)/1.2)) ~= 9.5 MW:
  the power balance is positive (assert surplus > 0).
- Expander with LOX/RP-1 at 10 MPa is infeasible; pressure-fed at
  10 MPa is flagged heavy (tank mass penalty large vs pump-fed).
Test identities: power scales linearly with mdot; pump power falls as
pump efficiency rises; feasibility matrix per cycle/propellant/p_c is
deterministic; ValueError rejections.

## Corpus tasks (2 tasks, ids w24r-rocket-engine-cycle-1/2)

Distinctive tokens: rocket-engine-cycle, feed-cycle, gas-generator
cycle, staged-combustion, expander-cycle, pressure-fed, pump-fed,
pump-power, turbine-power. Avoid: "chamber geometry", "nozzle area
ratio", "staging", "thrust vector", "solid motor" (siblings).

1. "compare liquid rocket feed cycles for the 1 MN upper stage engine:
   assess pressure-fed, gas-generator, staged-combustion and expander
   cycles at the 10 MPa chamber pressure and compute the pump discharge
   pressure, pump power, and turbine power balance for the feasible
   pump-fed options"
2. "run the engine cycle analysis for the small pressure-fed storable
   propulsion system: size the tank pressure from the chamber pressure
   and losses, compute the tank mass penalty, and give the feasibility
   verdict against the pump-fed alternative"

## SKILL body notes

Pair with combustion-chamber-design, nozzle-design,
propellant-selection, rocket-staging. Worked example uses the values
above; state all typical-value constants as reference-only with the
documented assumption. Compliance: ECSS standards referenced by name.

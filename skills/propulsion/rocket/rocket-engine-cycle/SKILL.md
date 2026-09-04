---
name: rocket-engine-cycle
description: "Use when you must assess liquid rocket engine feed cycles at a fixed thrust, chamber pressure, and propellant pair: compare pressure-fed against the pump-fed gas-generator, staged-combustion, and expander cycles, compute the pump discharge pressure, the oxidizer and fuel pump powers, the turbine drive power and the cycle power balance, and size the pressure-fed feed-tank mass penalty. Produces the feasible cycle set, pump and turbine power balance, drive mass fraction, tank mass penalty, and a cycle selection verdict. Trigger: rocket-engine-cycle, feed-cycle, gas-generator cycle, staged-combustion, expander-cycle, pressure-fed, pump-fed, pump-power, turbine-power."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [rocket-engine-cycle, feed-cycle, gas-generator-cycle, staged-combustion, expander-cycle, pressure-fed, pump-fed, pump-power, turbine-power]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rocket Engine Cycle (propulsion/rocket/rocket-engine-cycle)

Use when the task is liquid rocket engine feed-system cycle selection and
preliminary cycle analysis: trading pressure-fed against pump-fed
gas-generator, staged-combustion, and expander architectures for a
required thrust, chamber pressure, and propellant pair, then computing
the pump discharge pressure, pump powers, turbine drive power, and the
cycle power balance. This leaf implements a simplified SI engine balance
in pure Python, stdlib only, with a small reference propellant table
(LOX/RP-1, LOX/LH2, N2O4/MMH, monopropellant hydrazine). It covers the
feed system only: pair it with propulsion/rocket/combustion-chamber-design
for the chamber, propulsion/rocket/nozzle-design for the expansion
hardware, and propulsion/rocket/propellant-selection for the propellant
families trade.

## Domain quick reference

- Total mass flow from thrust and specific impulse: mdot = F / (Isp *
  g0), g0 = 9.80665 m/s^2. Table isp_vac is a default, overridable.
- Oxidizer/fuel split at mixture ratio r_m: mdot_ox = mdot * r_m /
  (1 + r_m), mdot_f = mdot / (1 + r_m). A monopropellant (r_m None)
  keeps one stream.
- Pump discharge pressure: p_pump = p_c + p_losses (2.0 MPa default
  injector plus line loss). The pump inlet sees the low-pressure feed
  tank, 0.3 MPa default.
- Pump power per propellant: P_pump = mdot_prop * (p_pump - p_inlet) /
  (rho_prop * eta_pump), eta_pump 0.7 default. Total is the sum over the
  oxidizer and fuel legs; LH2 pumps dominate because of the low density.
- Turbine drive power (isentropic expansion model):
  P_turb = mdot_gas * cp * T_in * eta_turb * (1 - (p_exit/p_in)^((g-1)/g)).
  Gas-generator defaults: 3% of total flow, cp 2000 J/(kg K), T 1200 K,
  g 1.2, p_gg = 0.8 * p_c, p_exit 0.2 MPa, eta_turb 0.6, all
  reference-only. Staged combustion expands the full flow from a
  1.5 * p_c preburner discharge. The expander drives the turbine with
  jacket-heated LH2 fuel from a small ratio near p_c (simplified model,
  reference-only).
- Feed-tank mass penalty (thin-wall estimate):
  m_tank = p_tank * V_prop * rho_wall / (2 * sigma_wall), titanium
  constants, propellant volume from the mass flow over a 60 s reference
  burn.
- Feasibility bounds (documented, reference-only): pressure-fed up to
  p_c = 3 MPa for storable-class systems; expander only for the LH2
  fuel below p_c = 10 MPa; gas-generator and staged-combustion feasible
  across the range for bipropellant pairs. ECSS E-ST-35 frames the
  space propulsion context; the relations above are standard
  engineering methodology, summary-only.
- Units are SI throughout: N, Pa, kg/s, W, kg/m3.

## Workflow

1. Fix the operating point: thrust F, chamber pressure p_c, propellant
   pair, and cycle (pressure-fed, gas-generator, staged-combustion,
   expander). Read pair properties with propellant_pair_properties.
2. Get the total and per-leg mass flow with mass_flow_split (Isp input
   or the table vacuum default).
3. Check the cycle against the documented bounds with
   cycle_feasibility; it returns (feasible, reason).
4. Compute the pump discharge pressure with pump_discharge_pressure and
   each pump leg with pump_power; the fuel leg is often the driver.
5. Compute the turbine drive with turbine_power using the cycle drive
   gas model (gas-generator bleed, staged full flow, expander fuel).
6. Size the feed tank with pressure_fed_tank_mass when a pressure-fed
   option is on the table.
7. Run the full balance with engine_cycle_analysis: it returns the
   summary dict (feasible, pump_power_total, turbine_power,
   power_balance, drive_mass_fraction, tank_mass_penalty, verdict).
8. Confirm the deterministic checks with the contract test
   scripts/test_rocket_engine_cycle.py.

## Worked example

LOX/RP-1 gas-generator upper stage engine: F = 1.0e6 N, Isp = 300 s,
r_m = 2.56, p_c = 10 MPa, p_losses = 2 MPa, eta_pump = 0.7, 3% gas
generator.

- Mass flow: mdot = 1.0e6 / (300 * 9.80665) = 339.905 kg/s, split to
  mdot_ox = 244.426 kg/s and mdot_f = 95.479 kg/s.
- Pump discharge pressure: p_pump = 10 + 2 = 12 MPa.
- Pump powers: oxidizer 244.426 * (12e6 - 0.3e6) / (1140 * 0.7) =
  3.584 MW; fuel 95.479 * (12e6 - 0.3e6) / (820 * 0.7) = 1.946 MW;
  total 5.530 MW, within 1% of the 5.5 MW ballpark.
- Drive gas: mdot_gg = 0.03 * 339.905 = 10.197 kg/s at p_gg = 8 MPa.
  P_turb = 10.197 * 2000 * 1200 * 0.6 * (1 - (0.2/8)^(1/6)) = 6.744 MW
  (exact formula value; the power balance is positive).
- Power balance: 6.744 - 5.530 = +1.214 MW surplus, so the
  gas-generator cycle closes with margin. The pressure-fed alternative
  at this p_c is rejected: the 12 MPa feed tank costs 599.6 kg against
  15.0 kg for the 0.3 MPa pump-fed tank on the same 60 s propellant
  basis.
- Expander with LOX/RP-1 at 10 MPa is infeasible: the drive needs the
  high heat-capacity LH2 fuel, so only LOX/LH2 below the 10 MPa bound
  qualifies.
- Small storable contrast: N2O4/MMH pressure-fed at p_c = 2 MPa needs a
  4 MPa tank and carries a 162.4 kg penalty at 1 MN for 60 s, a
  reasonable mass for a small system with no turbomachinery.

## Verification

- Confirm mass_flow_split(1.0e6, 300, g0, 2.56) returns
  (339.905, 244.426, 95.479) kg/s to within 1e-6.
- Confirm the pump powers fall within 10% of the 3.6 MW and 1.95 MW
  ballparks, total 5.5 MW.
- Confirm the gas-generator analysis returns power_balance =
  turbine_power - pump_power_total greater than 0 with the 3% drive
  mass fraction, and the staged-combustion balance is positive too.
- Confirm the feasibility matrix is deterministic across every
  cycle, propellant, and pressure combination, and that the expander
  bound and the pressure-fed bound reject LOX/RP-1 at 10 MPa.
- Confirm every non-positive thrust, pressure, or mass flow, every
  unknown propellant or cycle, every efficiency outside (0, 1], and
  every non-finite input raises ValueError.
- Run the contract test offline: python3
  scripts/test_rocket_engine_cycle.py (30 tests, deterministic).

## Related leaves

- propulsion/rocket/combustion-chamber-design: the chamber the feed
  system must supply.
- propulsion/rocket/nozzle-design: the expansion hardware downstream of
  the chamber.
- propulsion/rocket/propellant-selection: propellant families and their
  impulse and density properties.
- propulsion/rocket/rocket-staging: the stage architecture the engine
  cycle serves.

## Pitfalls

- Selecting a cycle outside its feasibility bounds: pressure-fed is only
  for storable-class systems up to about p_c = 3 MPa and the expander
  only for the LH2 fuel below p_c = 10 MPa - the worked example's
  LOX/RP-1 expander at 10 MPa is rejected by cycle_feasibility, not
  rescued by a bigger turbine.
- Reading the power balance as the whole story: the +1.214 MW surplus
  closes the gas-generator cycle, but the pump-fed tank penalty (15.0
  kg) versus the pressure-fed tank (599.6 kg at 12 MPa) is what decides
  between feed architectures at this chamber pressure.
- Forgetting that the fuel leg often drives the pumps: LH2 pumps
  dominate because of the low density, and in the worked example the
  RP-1 fuel leg still consumes 1.946 MW of the 5.530 MW total - sizing
  pumps from the oxidizer leg alone understates the balance.
- Feeding an efficiency outside (0, 1]: eta_pump and eta_turb outside
  the open interval raise ValueError, as do non-positive thrust,
  pressure or mass flow, unknown propellants or cycles and non-finite
  inputs.
- Trusting the reference defaults as flight values: the table Isp, the
  2.0 MPa default injector-plus-line loss and the 3% gas-generator
  drive are reference-only defaults - the Isp is overridable and the
  loss and bleed must be set from the actual engine design.
- Treating the cycle analysis as a chamber or nozzle design: this leaf
  covers the feed system only; pair it with combustion-chamber-design
  and nozzle-design before judging the engine.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_rocket_engine_cycle.py

The test covers the propellant reference table and its ValueError on
unknown pairs, the worked-example mass flows and split identities
including the monopropellant case, pump discharge pressure, the pump
power anchors (oxidizer, fuel, total), pump power scaling with mass
flow and its fall with efficiency, the gas-generator turbine formula
value, cycle feasibility bounds and the deterministic matrix, the
feed-tank mass scaling, the full engine_cycle_analysis anchors (power
balance identity, drive mass fraction, verdict text), Isp override,
and ValueError rejection of non-physical inputs throughout.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35 is named as the
  space propulsion context per standards-map.yaml; the feed-cycle
  relations above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.

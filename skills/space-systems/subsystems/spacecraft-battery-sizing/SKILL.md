---
name: spacecraft-battery-sizing
description: "Use when you must size the spacecraft battery energy storage for an Earth-orbiting power subsystem: compute the eclipse energy from the eclipse load and the eclipse duration, convert it into the required nameplate capacity with the depth of discharge limit and the discharge efficiency, convert to ampere hours at the bus voltage, lay out the series and parallel Li-ion cell counts for the regulated bus, check the discharge C-rate against the cell limit, and estimate the pack mass from the pack specific energy. Produces the eclipse energy, required capacity, cell layout, installed capacity and mass estimate that gate the spacecraft power sizing. Trigger: spacecraft battery sizing, eclipse energy, depth of discharge, orbit battery capacity, series parallel cell layout, bus voltage cell count, LEO power storage."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: subsystems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: subsystems
  tags: [spacecraft-battery-sizing, eclipse-energy, orbit-battery-capacity, depth-of-discharge, series-parallel-cell-layout, bus-voltage-cell-count, leo-power-storage, li-ion-cell, discharge-efficiency, pack-energy-density]
  version: 0.1.0
  author: AeroSkills
---

# Spacecraft Battery Sizing (space-systems/subsystems/spacecraft-battery-sizing)

Use when sizing the energy storage battery of an Earth-orbiting spacecraft
power subsystem. The battery covers the spacecraft load during the orbit
eclipse, when the solar array produces no power; this leaf sizes that
battery: the energy it must deliver in the eclipse, the required nameplate
capacity from the depth of discharge (DOD) limit and the discharge
efficiency, the capacity in ampere hours at the regulated bus voltage, the
series and parallel Li-ion cell layout, the discharge C-rate check against
the cell limit, and the pack mass from the pack specific energy. It
implements the standard ECSS-style sizing chain in pure Python, stdlib
only, deterministic and offline. It pairs with
space-systems/subsystems/solar-array-sizing (the charge source this battery
complements), space-systems/subsystems/power-thermal-budget (the orbit
average power balance the battery covers), space-systems/orbit-mechanics/
eclipse-time (the eclipse duration input) and space-systems/subsystems/
thermal-design (battery temperature control). The array sizing, the thermal
loop, the eclipse geometry and electric aircraft traction packs are outside
this leaf.

## Domain quick reference

- Eclipse energy: E = P_eclipse * t_eclipse / 3600, with the eclipse load
  P_eclipse in W and the eclipse duration t_eclipse in s giving Wh.
- Required nameplate capacity: C = E / (DOD * eta_discharge), where DOD is
  the depth of discharge limit in (0, 1] and eta_discharge is the discharge
  efficiency, module constant EFF_DISCHARGE = 0.95. The nameplate capacity
  must exceed the eclipse energy because only the DOD fraction of it is
  usable and the discharge leg loses the efficiency fraction.
- Capacity at the bus voltage: Ah = C / V_bus.
- Series cells: n_series = ceil(V_bus / V_cell); the pack nominal voltage
  n_series * V_cell must reach at least the regulated bus voltage.
- Parallel strings: n_parallel = ceil(Ah / Ah_cell); the installed capacity
  n_parallel * Ah_cell must reach at least the required ampere hours.
- Discharge C-rate: I = P_orbit / V_bus and C-rate = I / Ah_installed,
  checked against the cell maximum C-rate (within limit when
  c_rate <= cell_max_c_rate).
- Pack mass: m = C / e_spec, with the pack specific energy module constant
  SPEC_ENERGY_WH_KG = 150.0 Wh/kg.
- Module constants: CELL_VOLTAGE = 3.7 V and CELL_AMPHOUR = 50.0 Ah are the
  nominal Li-ion cell defaults. Units are SI throughout: W, s, Wh, Ah, V,
  A, kg.
- ECSS frames the spacecraft power context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the eclipse duty point: the eclipse load P_eclipse (W) and the
   eclipse duration t_eclipse (s, from space-systems/orbit-mechanics/
   eclipse-time), then run eclipse_energy_wh.
2. Apply the depth of discharge limit and the discharge efficiency with
   required_capacity_wh to get the required nameplate capacity; the
   efficiency argument defaults to EFF_DISCHARGE.
3. Convert the capacity to the bus with capacity_ah at the regulated bus
   voltage.
4. Lay out the cells with cell_layout at the bus voltage, the cell nominal
   voltage and the cell ampere hours; read n_series, n_parallel,
   total_cells, pack_nominal_voltage and installed_capacity_ah.
5. Check the discharge rate with discharge_rate_check against the orbit
   load, the installed capacity and the cell maximum C-rate, and read the
   within_limit verdict.
6. Estimate the pack mass with battery_mass_kg from the required capacity
   and the pack specific energy (default SPEC_ENERGY_WH_KG).
7. For the full summary, run size_battery once and read the dict
   (eclipse_energy_wh, required_capacity_wh, capacity_ah, n_series,
   n_parallel, total_cells, mass_kg, discharge_verdict).
8. Confirm the deterministic checks with the contract test
   scripts/test_spacecraft_battery_sizing.py.

## Worked example

A LEO spacecraft with a 1200 W eclipse load and a 35 min (2100 s) eclipse,
DOD limit 0.40, 95 percent discharge efficiency, 28 V bus and 3.7 V /
50 Ah Li-ion cells with a 1.0 cell maximum C-rate.

- Eclipse energy: eclipse_energy_wh(1200, 2100) = 1200 * 2100 / 3600 =
  700.0 Wh.
- Required capacity: required_capacity_wh(700, 0.40, 0.95) = 700 / (0.40 *
  0.95) = 1842.1 Wh.
- Capacity at the bus: capacity_ah(1842.1, 28) = 65.8 Ah.
- Cell layout: cell_layout(1842.1, 28, 3.7, 50) gives n_series =
  ceil(28 / 3.7) = ceil(7.57) = 8, n_parallel = ceil(65.8 / 50) =
  ceil(1.32) = 2, total_cells = 16, pack_nominal_voltage = 29.6 V and
  installed_capacity_ah = 100 Ah.
- Discharge rate: discharge_rate_check(1200, 28, 100, 1.0) gives
  current_A = 42.86 A, c_rate = 0.429, within_limit True.
- Mass: battery_mass_kg(1842.1, 150) = 12.28 kg.
- size_battery(1200, 2100, 0.40, 28) returns the summary with
  discharge_verdict "within-cell-limit".
- Second case, a 90 min LEO with a 35 min eclipse at 800 W: eclipse energy
  466.7 Wh and required capacity 1228.1 Wh.


## Pitfalls

- Sizing against the raw eclipse energy: the nameplate capacity
  must divide by both the DOD limit and the discharge efficiency
  (700 Wh of eclipse energy needs 1842.1 Wh of nameplate at 40% DOD
  and 95% efficiency), so quoting E / DOD alone under-sizes the
  battery.
- Forgetting the hour conversion: the eclipse energy formula divides
  W * s by 3600, and the 35 min eclipse enters as 2100 s, not 35;
  a minutes-as-hours slip changes the capacity by 60x.
- Taking the round-up for granted in both axes: n_series = ceil(V /
  V_cell) and n_parallel = ceil(Ah / Ah_cell) round up independently,
  so an exact multiple must NOT round up (the contract test pins the
  exact-multiple behavior) and the installed 100 Ah always over-shoots
  the required 65.8 Ah.
- Checking the C-rate against the wrong current: the discharge check
  uses the ORBIT load (1200 W), not the eclipse load, divided by the
  bus voltage and the INSTALLED capacity; a bank that fits the
  eclipse energy can still exceed the cell C-rate limit under a high
  draw (2000 W on 50 Ah gives 1.43 C).
- Confusing this leaf with the electric aircraft battery: the
  spacecraft bus battery is the eclipse-storage chain above; the
  traction pack sizing for aircraft and eVTOL lives in
  vehicle-design/sizing/battery-sizing.
- Using a pack specific energy outside the module model: the mass
  estimate divides the required capacity by the pack specific energy
  (150 Wh/kg default); a zero or negative specific energy raises
  ValueError and a datasheet value must be passed explicitly.
## Verification

- Confirm eclipse_energy_wh(1200, 2100) returns 700.0 Wh and
  required_capacity_wh(700, 0.40, 0.95) returns 1842.1 Wh (tolerance 0.1).
- Confirm capacity_ah(1842.1, 28) returns 65.8 Ah and the round trip
  capacity_ah(C, V_bus) * V_bus recovers C.
- Confirm cell_layout(1842.1, 28, 3.7, 50) returns 8 series, 2 parallel,
  16 total, 29.6 V pack and 100 Ah installed, with ceil rounding verified
  on both axes (a 30 V bus gives 9 series cells; a 4000 Wh requirement
  gives 3 parallel strings).
- Confirm discharge_rate_check(1200, 28, 100, 1.0) reports 0.429 C-rate
  within the 1.0 limit, that 800 W on a 50 Ah bank gives 0.57 C-rate
  within limit, and that 2000 W on the same bank gives 1.43 C-rate and
  exceeds the limit; size_battery with a 0.4 C-rate limit reports
  "exceeds-cell-limit".
- Confirm battery_mass_kg(1842.1, 150) returns 12.28 kg.
- Confirm every non-physical input raises ValueError: negative eclipse
  load, eclipse duration 0 or negative, DOD 0 or above 1, discharge
  efficiency outside (0, 1], bus voltage 0 or negative, cell voltage or
  cell capacity 0, cell max C-rate 0, negative energies and zero or
  negative specific energy.
- Run the contract test offline: python3
  scripts/test_spacecraft_battery_sizing.py (33 tests, deterministic,
  under 20 s).

## Related leaves

- space-systems/subsystems/solar-array-sizing: the charge source that
  recharges this battery in daylight.
- space-systems/subsystems/power-thermal-budget: the orbit average power
  balance that the eclipse storage covers.
- space-systems/subsystems/thermal-design: radiator and heater sizing for
  the battery temperature control.
- space-systems/orbit-mechanics/eclipse-time: the eclipse duration input
  from the orbit geometry.
- space-systems/subsystems/command-data-handling and
  space-systems/subsystems/communication-link-budget: the payload loads
  that set the eclipse draw.
- vehicle-design/sizing/battery-sizing: the electric aircraft and eVTOL
  traction pack counterpart, not a spacecraft bus battery.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_spacecraft_battery_sizing.py

The test covers the LEO worked example (700.0 Wh eclipse energy, 1842.1 Wh
required capacity, 65.8 Ah, series 8 / parallel 2 / total 16 cells, 29.6 V
pack, 100 Ah installed, 0.429 C-rate within limit, 12.28 kg mass), the
800 W second case (466.7 Wh, 1228.1 Wh), the discharge rate pass and
exceed verdicts (0.57 and 1.43 C-rate on a 50 Ah bank), ceil rounding on
both layout axes, exact-multiple no-round-up behavior, the round-trip
identities and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA standards set
  (ecss.nl/standards); the sizing relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

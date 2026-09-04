---
name: battery-sizing
description: "Use when you must size the traction battery pack of an electric aircraft or eVTOL from the mission energy and power requirements: convert the mission draw into the required pack energy with the depth of discharge limit and discharge efficiency, add the reserve, lay out the series and parallel cell counts for the target pack voltage, check the discharge C-rate against the cell limit, verify the minimum cell voltage under peak load against the cutoff with the cell internal resistance, and estimate pack mass and volume from typical cell and pack energy densities. Produces series and parallel cell counts, pack energy, the C-rate and voltage drop verdicts, and mass and volume estimates that gate vehicle energy storage sizing. Trigger: battery pack sizing, electric aircraft battery, eVTOL energy storage, traction battery, C-rate check, depth of discharge, series parallel cell count, pack voltage, discharge voltage drop."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [battery-sizing, traction-battery-sizing, battery-pack-sizing, electric-aircraft-battery, evtol-energy-storage, c-rate-check, depth-of-discharge, series-parallel-cell-count, pack-voltage, discharge-voltage-drop]
  version: 0.1.0
  author: Aero Agent Skills
---

# Battery Sizing (vehicle-design/sizing/battery-sizing)

Use when the task is sizing the traction battery pack of an electric
aircraft or eVTOL at the conceptual level: converting the mission
energy draw into a required pack energy through the depth of discharge
and the discharge efficiency, adding the reserve, laying out the series
and parallel cell arrangement for the target pack voltage, checking the
discharge C-rate against the cell capability, verifying the minimum
cell voltage under the peak load against the cutoff with the cell
internal resistance, and estimating the pack mass and volume from
typical cell and pack energy densities. This leaf implements the model
in pure Python, stdlib only, in
scripts/battery_sizing_logic.py. It pairs with
vehicle-design/sizing/fuel-tank-sizing as the energy storage
counterpart for conventionally fueled aircraft and with
vehicle-design/sizing/weight-estimation for carrying the pack mass into
the vehicle mass budget; the mission energy itself comes from
vehicle-design/conceptual/sizing-mission-profile.

## Domain quick reference

- Required pack energy: E_pack_req = E_mission * (1 + reserve) /
  (DOD_MAX * EFF_DISCHARGE). The depth of discharge limit keeps the pack
  inside the cycle-life window and the discharge efficiency converts
  stored energy into energy delivered to the load.
- Series cells: n_s = round(V_target / V_nom), the integer series count
  that reaches the nominal pack voltage target.
- Parallel cells: n_p = ceil(E_pack_req * 1000 / (n_s * V_nom * C_ah)),
  the integer number of parallel strings that covers the required
  energy with the cell energy per string.
- Installed pack energy: E_pack = n_s * n_p * V_nom * C_ah / 1000 (kWh),
  the as-built energy after the count rounding.
- Energy margin: E_usable = E_pack * DOD_MAX * EFF_DISCHARGE against
  E_required = E_mission * (1 + reserve); pass when usable covers the
  required energy.
- Discharge C-rate: C = P_max / E_pack against the cell max C-rate;
  pass when C <= C_max.
- Voltage drop under load: I_total = P_max * 1000 / V_pack,
  I_branch = I_total / n_p, drop = I_branch * R_internal,
  V_min = V_nom - drop; pass when V_min >= V_cutoff.
- Mass and volume: cell mass = E_pack / gravimetric cell density,
  pack mass = E_pack / gravimetric pack density, and the same split
  with the volumetric densities for volume. The density constants are
  documented typicals for NMC lithium-ion cells; actual cells vary and
  the estimates must be re-run with supplier data.
- Discharge heat (simple check only): Q = THERMAL_LOSS_FRACTION *
  P_max * t. Thermal management system design is out of scope.
- FAR 25 and CS 25 frame the energy storage and electrical system
  certification context for transport category airplanes; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the design mission: mission energy E_mission (kWh), reserve
   fraction (for example 0.20 for 20 percent), peak discharge power
   P_max (kW), and the target nominal pack voltage V_target (V).
2. Define the cell: nominal voltage V_nom, capacity C_ah, internal
   resistance R_internal, cutoff voltage V_cutoff, and max C-rate.
3. Convert the mission draw to the required pack energy with
   required_pack_energy; the reserve rides on top of the mission draw
   before the depth of discharge and efficiency division.
4. Lay out the pack: series_cells for the series count at the target
   voltage, then parallel_cells for the strings that cover the required
   energy, then pack_energy_kwh for the as-built installed energy.
5. Check the energy margin with energy_margin (usable against required
   including the reserve).
6. Check the discharge C-rate with c_rate_check against the cell limit.
7. Verify the minimum cell voltage under the peak load with
   voltage_drop_check against the cutoff.
8. Estimate the pack mass and volume with mass_estimate and
   volume_estimate for the vehicle mass budget and installation
   envelope, and run thermal_estimate for the discharge-loss heat
   check when the load duration is known.
9. Run size_battery for the full sizing dict and the overall verdict,
   which FAILs with its reasons when any of the three checks fails.
10. Confirm the deterministic checks with the contract test
    scripts/test_battery_sizing.py.

## Worked example

eVTOL design mission: E_mission = 50 kWh, reserve 0.20, P_max = 400 kW,
V_target = 400 V. Cell: V_nom 3.7 V, 5 Ah, 0.002 ohm internal
resistance, 3.0 V cutoff, 4 C max.

- Required pack energy: E_pack_req = 50 * 1.2 / (0.8 * 0.95) =
  78.947 kWh.
- Series cells: n_s = round(400 / 3.7) = 108 (108 * 3.7 = 399.6 V).
- Parallel cells: n_p = ceil(78947 / (108 * 3.7 * 5)) = ceil(39.51) = 40.
- Installed pack energy: 108 * 40 * 3.7 * 5 / 1000 = 79.92 kWh.
- Energy margin: usable 79.92 * 0.8 * 0.95 = 60.74 kWh against the
  required 50 * 1.2 = 60 kWh, margin 0.74 kWh, pass.
- C-rate at 400 kW: 400 / 79.92 = 5.01 C against the 4 C limit, FAIL.
  At 300 kW the C-rate is 300 / 79.92 = 3.75 C, pass.
- Voltage drop: I_total = 400000 / 399.6 = 1001 A, I_branch = 1001 / 40
  = 25.0 A, drop = 25.0 * 0.002 = 0.05 V, V_min = 3.65 V against the
  3.0 V cutoff, pass.
- Mass: cell level 79.92 / 0.25 = 319.7 kg, pack level 79.92 / 0.18 =
  444.0 kg. Volume: cell level 145.3 L, pack level 266.4 L.
- Overall verdict for the 400 kW case: FAIL with the C-rate reason; the
  300 kW case passes all checks.


## Pitfalls

- Sizing energy without the reserve and the DOD chain: the required
  pack energy is E_mission * (1 + reserve) / (DOD_MAX *
  EFF_DISCHARGE), so a pack sized on raw mission energy alone is
  roughly a factor DOD * efficiency too small (50 kWh mission needs
  78.95 kWh in the worked example).
- Checking only the energy margin: size_battery FAILs when ANY of
  the three checks fails - the worked 400 kW case has a passing
  energy margin and voltage drop yet fails on the 5.01 C discharge
  rate against the 4 C cell limit.
- Forgetting the count rounding on the energy: n_s rounds while n_p
  ceils, and the installed pack energy (79.92 kWh) comes from the
  rounded counts, not from the required value; the usable-versus-
  required margin is checked against the as-built pack.
- Ignoring the branch current in the voltage drop: the drop uses the
  per-string current I_total / n_p times the internal resistance
  (25.0 A * 0.002 ohm = 0.05 V in the worked example), so a
  parallel-count slip changes the minimum cell voltage under load.
- Quoting the density estimates as datasheet values: the mass and
  volume constants are documented NMC lithium-ion typicals (0.25 and
  0.18 kg/kWh cell and pack levels) and must be re-run with supplier
  data for a real cell.
- Confusing this traction pack with spacecraft storage: this leaf
  covers aircraft and eVTOL traction batteries; the spacecraft
  eclipse battery chain belongs to space-systems/subsystems/
  spacecraft-battery-sizing.
## Verification

- Confirm required_pack_energy(50, 0.2) returns 78.947 kWh within 1e-6.
- Confirm series_cells(400, cell) returns 108 and parallel_cells on the
  required energy returns 40, with the installed pack energy 79.92 kWh.
- Confirm the energy margin dict reports usable 60.74 kWh at least the
  required 60 kWh and passes.
- Confirm c_rate_check(400, 79.92, cell) rounds to 5.01 C and fails the
  4 C limit, while the 300 kW case rounds to 3.75 C and passes.
- Confirm voltage_drop_check reports about 0.05 V drop and a 3.65 V
  minimum cell voltage, passing the 3.0 V cutoff.
- Confirm mass_estimate returns 319.7 kg cell level and 444.0 kg pack
  level for the 79.92 kWh pack.
- Confirm size_battery gives the overall FAIL verdict with the C-rate
  reason at 400 kW and PASS at 300 kW.
- Confirm every non-positive mission energy, power, voltage and cell
  value, every negative reserve, and every missing or unknown cell key
  raises ValueError.
- Run the contract test offline: python3
  scripts/test_battery_sizing.py (31 tests, deterministic).

## Related leaves

- vehicle-design/sizing/fuel-tank-sizing: liquid fuel energy storage
  counterpart for conventionally fueled aircraft.
- vehicle-design/sizing/weight-estimation: carries the pack mass into
  the vehicle weight and balance budget.
- vehicle-design/conceptual/sizing-mission-profile: the source of the
  mission energy and power requirements.
- vehicle-design/sizing/engine-sizing: propulsion power sizing
  boundary; the pack is sized from the resulting power draw, not the
  engine or motor itself.
- space-systems/subsystems/power-thermal-budget and
  space-systems/subsystems/solar-array-sizing: the spacecraft electrical
  power system side owns eclipse batteries and solar arrays; this leaf
  covers aircraft and eVTOL traction storage only.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_battery_sizing.py

The test covers the worked-example sizing contract (required pack
energy 78.947 kWh, 108 series and 40 parallel cells, 79.92 kWh pack,
usable 60.74 kWh against 60 kWh required, C-rate fail at 400 kW and
pass at 300 kW, voltage drop 0.05 V with a 3.65 V minimum against the
3.0 V cutoff, 319.7 kg cell and 444.0 kg pack mass), the energy margin
branches, C-rate and voltage drop boundaries, mass, volume and thermal
estimates, the overall verdict for both power cases, and ValueError
rejection of non-positive mission energy, power, voltage and cell
values, negative reserve, and missing or unknown cell keys.

## Compliance

- Standards referenced, not reproduced: FAR 25 and CS 25 frame the
  transport category energy storage context; the sizing relations above
  are standard engineering methodology, summary-only per
  standards-map.yaml. The battery energy density constants are
  documented typical values (NMC lithium-ion); actual cells vary.
- compliance: STANDARDS-REF, gated: false.

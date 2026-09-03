# Wave-26 leaf spec: battery-sizing (vehicle-design, sizing pack)

- Path: skills/vehicle-design/sizing/battery-sizing/
- Pack: sizing (existing siblings: engine-sizing, fuel-tank-sizing,
  ice-protection-sizing, control-surface-sizing, propeller-sizing,
  tail-sizing, landing-gear-sizing, tire-sizing, nacelle-sizing,
  fuselage-sizing, wing-planform-sizing, spoiler-sizing, weight-
  estimation, ws-tw-trade)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: vehicle-design

## Claim

Size the traction battery pack of an electric aircraft or eVTOL from
the mission energy and power requirements: convert the mission draw
into a required pack energy through the depth of discharge and the
discharge efficiency, add the reserve, lay out the series and parallel
cell arrangement for the target pack voltage, check the discharge
C-rate against the cell capability, verify the minimum cell voltage
under load against the cutoff with the internal resistance, and
estimate the pack mass and volume from typical cell and pack energy
densities. Produces the series and parallel cell counts, the pack
energy, the C-rate and voltage-drop verdicts, and the mass and volume
estimates that gate the vehicle energy storage sizing.

Does NOT do: size a spacecraft electrical power system with eclipse
battery and solar array (space-systems subsystems power-thermal-budget
and solar-array-sizing own the spacecraft EPS), size liquid fuel tanks
with ullage (fuel-tank-sizing), size the propulsion motor or
inverter, or design the battery thermal management hardware. The
thermal check is limited to a discharge-loss heat estimate; thermal
system design is out of scope.

## Model (implement exactly)

Inputs:
- mission_energy_kwh (net energy drawn from the pack over the design
  mission, float),
- reserve_fraction (float, e.g. 0.20 for a 20% reserve above the
  mission draw),
- max_power_kw (float, peak discharge power),
- target_voltage_v (float, nominal pack voltage target),
- cell: dict {voltage_nom_v (float), capacity_ah (float),
  r_internal_ohm (float, per cell), v_cutoff_min_v (float),
  max_c_rate (float)}.
Module constants (documented typical values; the SKILL body labels
them typicals):
- DOD_MAX = 0.80 (typical depth of discharge limit for cycle life),
- EFF_DISCHARGE = 0.95 (typical discharge efficiency to the load),
- CELL_GRAV_WH_KG = 250.0 (typical NMC lithium-ion cell gravimetric
  density, Wh/kg at cell level),
- PACK_GRAV_WH_KG = 180.0 (typical pack-level gravimetric density),
- CELL_VOL_WH_L = 550.0 (typical cell volumetric density Wh/L),
- PACK_VOL_WH_L = 300.0 (typical pack volumetric density),
- THERMAL_LOSS_FRACTION = 0.05 (discharge loss heat fraction).
Functions:
- required_pack_energy(mission_energy_kwh, reserve_fraction) ->
  E_pack_req = mission_energy_kwh * (1 + reserve_fraction) /
  (DOD_MAX * EFF_DISCHARGE); ValueError on negative inputs and on
  reserve_fraction < 0.
- series_cells(target_voltage_v, cell) -> int round(target / v_nom);
  ValueError on v_nom <= 0.
- parallel_cells(E_pack_req_kwh, n_series, cell) -> int
  ceil(E_pack_req * 1000 / (n_series * v_nom * capacity_ah)).
- pack_energy_kwh(n_series, n_parallel, cell) -> float
  n_s * n_p * v_nom * capacity_ah / 1000.
- energy_margin(pack_kwh, mission_energy_kwh, reserve_fraction) ->
  dict {usable_kwh (pack * DOD_MAX * EFF_DISCHARGE),
  required_kwh (mission * (1 + reserve)), margin_kwh, pass (bool)}.
- c_rate_check(max_power_kw, pack_kwh, cell) -> dict {c_rate,
  limit (cell max_c_rate), pass (bool)}.
- voltage_drop_check(max_power_kw, n_series, n_parallel, cell,
  nominal_pack_v) -> dict {i_total_a, i_branch_a, drop_v,
  v_min_cell_v, pass (bool)}: i_total = max_power_kw * 1000 /
  nominal_pack_v; i_branch = i_total / n_parallel; drop = i_branch *
  cell r_internal; v_min = v_nom - drop; pass when v_min >= cutoff.
- mass_estimate(pack_kwh) -> dict {cell_mass_kg, pack_mass_kg} using
  the two gravimetric constants.
- volume_estimate(pack_kwh) -> dict {cell_volume_L, pack_volume_L}.
- thermal_estimate(max_power_kw, duration_h) -> heat_kwh =
  THERMAL_LOSS_FRACTION * max_power_kw * duration_h (discharge heat
  only, documented as the simple check).
- size_battery(mission_energy_kwh, reserve_fraction, max_power_kw,
  target_voltage_v, cell) -> dict with all outputs and the overall
  verdict {pass (bool), reasons}: FAIL when the energy margin, C-rate,
  or voltage-drop checks fail; else PASS.
ValueError on: non-positive mission energy, power, voltage, or cell
values; negative reserve; capacity_ah <= 0; unknown cell keys.

## Worked example

eVTOL design mission: mission_energy 50 kWh, reserve 0.20, max power
400 kW, target pack voltage 400 V. Cell: v_nom 3.7 V, capacity 5 Ah,
r_internal 0.002 ohm, v_cutoff 3.0 V, max C-rate 4.
- E_pack_req = 50 * 1.2 / (0.8 * 0.95) = 78.947 kWh (assert the
  module value within 1e-6).
- n_series = round(400 / 3.7) = 108 (108 * 3.7 = 399.6 V).
- n_parallel = ceil(78947 / (108 * 3.7 * 5)) = ceil(78947 / 1998) =
  ceil(39.51) = 40.
- pack energy = 108 * 40 * 3.7 * 5 / 1000 = 79.92 kWh.
- usable = 79.92 * 0.8 * 0.95 = 60.74 kWh >= required 60 kWh ->
  margin 0.74 kWh pass.
- C-rate = 400 / 79.92 = 5.01 -> FAIL against the 4 C cell limit
  (the example intentionally shows the C-rate failure; a second case
  at max_power 300 kW gives 3.75 C -> pass).
- voltage drop: i_total = 400000 / 399.6 = 1001 A; i_branch = 1001 /
  40 = 25.0 A; drop = 25.0 * 0.002 = 0.05 V; v_min = 3.65 V >= 3.0
  -> pass (assert the module values within tolerance).
- mass: cell-level 79.92 / 0.25 = 319.7 kg; pack-level 79.92 / 0.18
  = 444.0 kg.
- size_battery overall verdict FAIL with the C-rate reason for the
  400 kW case; PASS for the 300 kW case.
- ValueError on mission energy 0 and on a missing cell key.
Keep at least 18 test methods (required energy, series/parallel math,
energy margin, C-rate branches, voltage drop, mass and volume
estimates, overall verdicts, ValueErrors).

## Corpus tasks (ids w26-battery-sizing-1/2)

Distinctive tokens: battery pack sizing, electric aircraft battery,
eVTOL energy storage, traction battery, C-rate check, depth of
discharge, series parallel cell count, pack voltage, cell energy
density, discharge voltage drop. Avoid: fuel tank / ullage (fuel-tank-
sizing), solar array / eclipse battery / spacecraft EPS (space-systems
power-thermal-budget), engine sizing (engine-sizing).

1. "size the traction battery pack for the eVTOL: 50 kWh mission
   energy with 20 percent reserve and 400 kW peak power, lay out the
   series and parallel cells for the 400 volt pack, and check the
   discharge C-rate against the cell limit"
2. "compute the required pack energy for the electric aircraft mission
   with the depth of discharge and discharge efficiency, then verify
   the minimum cell voltage under the peak load against the 3.0 volt
   cutoff and estimate the pack mass"

## SKILL body notes

Pair with fuel-tank-sizing (energy storage counterpart), weight-
estimation (pack mass into the mass budget), sizing-mission-profile
(mission energy source), and cite the space-systems EPS leaves as the
spacecraft-side boundary. Cell and pack density values are documented
typical module constants (NMC chemistry); actual cells vary and the
SKILL body must say so. Standards referenced not reproduced.

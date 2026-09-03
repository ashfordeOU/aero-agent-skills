# Wave-29 leaf spec: spacecraft-battery-sizing (space-systems, subsystems pack)

- Path: skills/space-systems/subsystems/spacecraft-battery-sizing/
- Pack: subsystems (existing siblings: command-data-handling,
  communication-link-budget, power-thermal-budget,
  propellant-tank-sizing, solar-array-sizing, thermal-design)
- Standards ids: ecss (reference-only; the space-systems convention).
  Ledger Standard: ecss.
- Family: space-systems

## Claim

Size the battery energy storage of an Earth-orbiting spacecraft power
subsystem: compute the energy the battery must deliver during the
orbit eclipse from the eclipse load and the eclipse duration, convert
it to a required nameplate capacity with the depth-of-discharge limit
and the discharge efficiency, lay out the series and parallel cell
counts for the regulated bus voltage, check the discharge rate against
the cell limit, and estimate the pack mass from the cell energy
density. Produces the eclipse energy, required capacity, cell layout,
and mass estimate that gate the power subsystem sizing.

Does NOT do: size the solar array or balance the full orbit power
budget (solar-array-sizing and power-thermal-budget own array sizing
and the orbital average power balance); compute the eclipse time from
orbit geometry (orbit-mechanics eclipse-time owns eclipse duration);
size an electric aircraft traction pack (vehicle-design battery-sizing
owns the eVTOL/aircraft traction battery with C-rate and voltage-drop
checks); design the thermal control of the battery (thermal-design
owns radiator and heater sizing). This leaf sizes the spacecraft
battery: eclipse energy, depth of discharge, cell layout, mass.

## Model (implement exactly)

Module constants:
- EFF_DISCHARGE = 0.95 (discharge efficiency, module constant).
- SPEC_ENERGY_WH_KG = 150.0 (pack-level energy density Wh/kg, module
  constant for the mass estimate).
- CELL_VOLTAGE = 3.7 (V nominal per Li-ion cell, module constant).
- CELL_AMPHOUR = 50.0 (Ah per cell, module constant for the worked
  layout; passed as an argument in the general function).

Functions (pure stdlib, floats):
- eclipse_energy_wh(eclipse_load_w, eclipse_duration_s) -> float:
  E = eclipse_load_w * eclipse_duration_s / 3600.0. ValueError on
  negative inputs or duration <= 0.
- required_capacity_wh(eclipse_energy_wh_value, dod_limit,
  discharge_efficiency=EFF_DISCHARGE) -> float:
  C = E / (dod_limit * discharge_efficiency). ValueError if dod_limit
  not in (0, 1] or discharge_efficiency not in (0, 1].
- capacity_ah(capacity_wh, bus_voltage) -> float:
  Ah = capacity_wh / bus_voltage. ValueError on bus_voltage <= 0.
- cell_layout(required_capacity_wh, bus_voltage, cell_voltage,
  cell_ah) -> dict: n_series = ceil(bus_voltage / cell_voltage);
  n_parallel = ceil(capacity_ah(required_capacity_wh, bus_voltage) /
  cell_ah); returns {n_series, n_parallel, total_cells,
  pack_nominal_voltage: n_series * cell_voltage, installed_capacity_ah:
  n_parallel * cell_ah}. ValueError on non-positive inputs.
- discharge_rate_check(orbit_load_w, bus_voltage, installed_capacity_ah,
  cell_max_c_rate) -> dict: I = orbit_load_w / bus_voltage (A);
  c_rate = I / installed_capacity_ah; returns {current_A: I,
  c_rate, within_limit: c_rate <= cell_max_c_rate}. ValueError on
  non-positive inputs.
- battery_mass_kg(required_capacity_wh,
  spec_energy_wh_kg=SPEC_ENERGY_WH_KG) -> float:
  m = required_capacity_wh / spec_energy_wh_kg. ValueError if
  spec_energy_wh_kg <= 0.
- size_battery(eclipse_load_w, eclipse_duration_s, dod_limit,
  bus_voltage, cell_voltage=CELL_VOLTAGE, cell_ah=CELL_AMPHOUR,
  cell_max_c_rate=1.0) -> dict: convenience chain returning
  {eclipse_energy_wh, required_capacity_wh, capacity_ah,
  n_series, n_parallel, total_cells, mass_kg, discharge_verdict:
  "within-cell-limit" | "exceeds-cell-limit"}. ValueErrors propagate.

## Worked example

LEO spacecraft: eclipse load 1200 W, eclipse duration 35 min (2100 s),
DOD limit 40%, bus voltage 28 V, cell 3.7 V / 50 Ah, cell max C-rate
1.0.

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- eclipse_energy_wh(1200, 2100) = 700.0 Wh (within 0.1).
- required_capacity_wh(700, 0.40, 0.95) = 1842.1 Wh (within 0.1).
- capacity_ah(1842.1, 28) = 65.8 Ah (within 0.1).
- cell_layout(1842.1, 28, 3.7, 50): n_series = 8 (28/3.7 = 7.57),
  n_parallel = 2 (65.8/50 = 1.32), total_cells = 16,
  pack_nominal_voltage = 29.6 V, installed_capacity_ah = 100 Ah.
- discharge_rate_check(1200, 28, 100, 1.0): current 42.86 A (within
  0.01), c_rate 0.429 (within 0.001), within_limit True.
- battery_mass_kg(1842.1, 150) = 12.28 kg (within 0.01).
- A second case: 90 min LEO with 35 min eclipse at 800 W:
  eclipse energy 466.7 Wh, required 1228.1 Wh (compute exact, assert
  within 0.1).
- ValueErrors: duration 0, dod 0 or > 1, bus voltage 0, cell max
  C-rate 0, negative loads.

Keep at least 16 test methods: eclipse energy, capacity with DOD and
efficiency, Ah conversion, series/parallel layout (ceil behavior both
sides), pack voltage, installed Ah, discharge C-rate check pass and
fail (800 W eclipse load at 28 V over a 50 Ah cell bank gives 0.57
C-rate; a 2000 W load gives 1.43 C-rate and exceeds a 1.0 limit),
mass anchor, second case, ValueErrors. Runs offline in under 20 s.

## Corpus tasks (ids w29-spacecraft-battery-sizing-1/2)

Distinctive tokens: spacecraft battery sizing, eclipse energy, depth
of discharge, orbit battery capacity, series parallel cell layout,
bus voltage cell count, LEO power storage. Avoid: traction battery,
eVTOL energy storage, C-rate of an electric aircraft pack,
discharge voltage drop (vehicle-design battery-sizing); solar array,
orbital average power balance (solar-array-sizing, power-thermal-
budget); eclipse time from orbit geometry (orbit-mechanics
eclipse-time).

1. "size the spacecraft battery for a LEO eclipse: 1200 W for 35
   minutes at 40 percent depth of discharge with 95 percent discharge
   efficiency, cell layout for a 28 V bus and pack mass"
2. "lay out the series and parallel Li-ion cell count and check the
   discharge C-rate for an orbit battery on a 28 V spacecraft bus"

## SKILL body notes

Pair with solar-array-sizing (the charge source), power-thermal-budget
(the orbit-average balance the battery covers), eclipse-time (where
the eclipse duration comes from), thermal-design (battery temperature
control). State the boundary: this leaf covers the battery proper, not
the array, the thermal loop, or an aircraft traction pack; eclipse
energy and DOD tokens are the distinctive routing surface. ecss is
reference-only. Mirror the subsystems pack SKILL body style (SI units,
stdlib only, deterministic offline).

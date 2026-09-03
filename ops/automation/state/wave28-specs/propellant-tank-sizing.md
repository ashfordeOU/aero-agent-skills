# Wave-28 leaf spec: propellant-tank-sizing (space-systems, subsystems pack)

- Path: skills/space-systems/subsystems/propellant-tank-sizing/
- Pack: subsystems (existing siblings: command-data-handling,
  communication-link-budget, power-thermal-budget, solar-array-sizing,
  thermal-design)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: space-systems

## Claim

Size a spacecraft propellant tank from the propellant mass budget:
convert the propellant mass into the liquid volume with the propellant
density, add the ullage volume for the required ullage fraction,
compute the total tank volume and the sphere tank radius, size the
membrane wall thickness from the burst pressure and the material
allowable, estimate the tank shell mass, size the pressurant gas mass
for the regulated or blowdown pressurization scheme, and compute the
blowdown ratio and pressure range. Produces the propellant volume, the
ullage volume, the tank volume and radius, the wall thickness, the
shell mass, the pressurant mass, and the tank-mass fraction that gate
the spacecraft propulsion bus design.

Does NOT do: convert the mission delta-v into the propellant mass
(space-systems mission-design mission-delta-v-budget owns the delta-v
to propellant conversion); size launch-vehicle propellant tanks or
staging (propulsion rocket-sizing and rocket-staging own the launch
vehicle); size the aircraft fuel volume (vehicle-design fuel-tank-
sizing owns wing and fuselage fuel tanks); compute the thermal balance
(thermal-design).

## Model (implement exactly)

Module constants:
- G0 = 9.80665.
- DEFAULT_ULLAGE_FRACTION = 0.06 (ullage as a fraction of the TOTAL
  tank volume; documented typical),
- DEFAULT_BOSS_FACTOR = 1.10 (shell mass increase for bosses and
  welds; documented typical),
- GAS_CONSTANT_HE = 2077.0 (J/(kg K) for helium).

Inputs:
- propellant_mass_kg (float),
- propellant_density_kg_m3 (float),
- ullage_fraction (float, default DEFAULT_ULLAGE_FRACTION, fraction of
  the total volume left empty),
- pressurization (str in {"regulated", "blowdown"}),
- meop_pa (float, maximum expected operating pressure),
- burst_factor (float, default 2.0; burst pressure = factor*MEOP),
- material_ultimate_pa (float, e.g. 900e6 for Ti-6Al-4V),
- material_density_kg_m3 (float, default 4430.0),
- boss_factor (float, default DEFAULT_BOSS_FACTOR),
- pressurant_temperature_K (float, default 293.0),
- gas_constant (float, default GAS_CONSTANT_HE),
- blowdown_ratio (float or None; required for blowdown, e.g. 2.5).

Functions:
- propellant_volume_m3(mass_kg, density_kg_m3) -> float:
  mass/density. ValueError on mass <= 0 or density <= 0.
- ullage_volume_m3(prop_vol, ullage_fraction) -> float:
  prop_vol*ullage_fraction/(1 - ullage_fraction). ValueError on
  ullage_fraction outside (0, 1).
- tank_volume_m3(prop_vol, ullage_fraction) -> float:
  prop_vol/(1 - ullage_fraction).
- sphere_radius_m(volume_m3) -> float: (3*V/(4*pi))^(1/3).
  ValueError on V <= 0.
- burst_pressure_pa(meop_pa, burst_factor) -> float: factor*MEOP.
  ValueErrors on meop <= 0, factor <= 1.
- wall_thickness_m(burst_pa, radius_m, material_ultimate_pa) ->
  float: burst*radius/(2*material_ultimate) (thin-walled sphere
  membrane). ValueErrors on any non-positive input.
- shell_mass_kg(radius_m, thickness_m, material_density_kg_m3,
  boss_factor) -> float: 4*pi*r^2*t*rho*boss_factor.
- pressurant_mass_kg(pressure_pa, ullage_vol_m3,
  temperature_K, gas_constant) -> float: P*V/(R*T) (ideal gas at the
  operating pressure; for blowdown use the initial pressure).
- blowdown_pressure_range(meop_pa, blowdown_ratio) -> dict:
  {p_initial_pa: meop, p_final_pa: meop/ratio}. ValueError on ratio
  <= 1.
- analyze(inputs) -> dict: propellant volume, ullage volume, tank
  volume, radius, burst pressure, wall thickness, shell mass, tank
  mass fraction = shell_mass/propellant_mass, pressurant mass, and
  for blowdown the pressure range, verdict "tank-sizing-pass" when the
  tank mass fraction <= 0.20 (typical budget sanity check; documented
  typical) else "tank-sizing-fail".
ValueError on: propellant_mass <= 0, density <= 0, meop_pa <= 0,
material_ultimate_pa <= 0, pressurant_temperature_K <= 0,
pressurization not in the set, blowdown without blowdown_ratio.

## Worked example

Hydrazine monopropellant: mass 100 kg, density 1008 kg/m3, ullage
fraction 0.06, MEOP 2.0 MPa, burst factor 2.0, Ti-6Al-4V ultimate
900 MPa, rho_material 4430, helium pressurant at 293 K, regulated
scheme at the MEOP.
- propellant volume = 100/1008 = 0.099206 m3 (assert within 1e-5).
- ullage volume = 0.099206*0.06/0.94 = 0.0063323 m3 (assert).
- tank volume = 0.099206/0.94 = 0.105539 m3 (assert within 1e-4).
- sphere radius = (3*0.105539/(4*pi))^(1/3) = (0.025196)^(1/3) =
  0.29319 m (assert within 1e-4).
- burst pressure = 4.0 MPa; wall thickness = 4e6*0.29319/(2*900e6) =
  1,172,760/1.8e9 = 6.5153e-4 m = 0.6515 mm (assert within 1e-6).
- shell mass = 4*pi*0.29319^2*6.5153e-4*4430*1.10: 0.29319^2 =
  0.085960; 4*pi*0.085960 = 1.08021; *6.5153e-4 = 7.0380e-4; *4430 =
  3.1178; *1.10 = 3.4296 kg (assert within 0.01).
- tank mass fraction = 3.4296/100 = 0.0343 -> "tank-sizing-pass"
  (assert).
- pressurant mass (regulated at MEOP) = 2e6*0.0063323/(2077*293) =
  12664.6/608,561 = 0.020811 kg (assert within 1e-4).
- Blowdown case: ratio 2.5 at MEOP 2.0 MPa: p_initial 2.0 MPa,
  p_final 0.8 MPa (assert); pressurant at the initial pressure for
  blowdown (same 0.020811 kg with these inputs; body explains a
  blowdown system needs the gas mass computed at the initial
  pressure).
- Fail case: propellant_mass 400 kg in the same 0.24 m radius? keep
  the sanity check explicit: pass a check input with an absurd shell:
  material_ultimate 100 MPa -> thickness 1.17 mm -> shell ~ 5x? The
  verdict stays pass unless fraction > 0.2; assert the verdict flips
  only when the mass fraction exceeds 0.2 (construct by density
  30000 kg/m3 -> shell 23.2 kg? compute 4*pi*0.085960*6.5153e-4*30000
  = 21.1 kg*1.1 = 23.2 -> fraction 0.232 > 0.2 -> fail). Assert.
- ValueErrors on mass 0, density 0, meop 0, burst_factor 1.0,
  temperature 0, pressurization "self-pressurized", blowdown without
  ratio.
Keep at least 18 test methods: volumes, ullage fraction edge, radius,
burst pressure, wall thickness, shell mass, boss factor effect, mass
fraction and verdict, pressurant mass regulated and blowdown, blowdown
pressure range, fail verdict construction, ValueErrors.

## Corpus tasks (ids w28-propellant-tank-sizing-1/2)

Distinctive tokens: propellant tank sizing, propellant volume, tank
ullage fraction, pressurant mass, blowdown pressure range, sphere tank
wall thickness, spacecraft propulsion bus. Avoid: delta-v budget,
propellant mass from delta-v (mission-delta-v-budget); rocket equation
mass ratio (propulsion rocket-sizing); aircraft fuel volume, wing
tank capacity (vehicle-design fuel-tank-sizing); radiator area
(thermal-design).

1. "size the spacecraft propellant tank for the monopropellant bus:
   convert the propellant mass to volume, add the ullage fraction, and
   compute the sphere tank wall thickness and shell mass"
2. "check the pressurization for the propellant tank: size the helium
   pressurant mass and compute the blowdown pressure range for the
   regulated and blowdown schemes"

## SKILL body notes

Pair with mission-delta-v-budget (upstream: propellant mass comes from
the delta-v budget) and thermal-design (the other bus-sizing sibling).
Ullage fraction, burst factor, and boss factor are documented typical
values; the body must say they are program inputs. ECSS cited
reference-only for the spacecraft engineering context.

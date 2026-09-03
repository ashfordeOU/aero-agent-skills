# Wave-29 leaf spec: cold-gas-thruster (propulsion, rocket pack)

- Path: skills/propulsion/rocket/cold-gas-thruster/
- Pack: rocket (existing siblings: combustion-chamber-design,
  hybrid-rocket-motor, nozzle-design, propellant-selection,
  rocket-engine-cycle, rocket-sizing, rocket-staging,
  solid-rocket-motor, thrust-vector-control)
- Standards ids: ecss (reference-only; the propulsion rocket and
  electric leaves carry this id). Ledger Standard: ecss.
- Family: propulsion

## Claim

Size and assess a cold-gas reaction control thruster for spacecraft
attitude control: compute the choked mass flow through the nozzle
throat from the plenum pressure and temperature, the thrust from the
mass flow and specific impulse, the tank gas mass from the plenum
volume and pressure, the isothermal blowdown time constant and the
pressure history, the burn time to a minimum usable pressure, and the
total impulse available between the initial and final pressures.
Produces the thrust, mass flow, tank mass, blowdown time constant,
pressure at a requested time, operating time, and total impulse that
gate a cold-gas RCS sizing.

Does NOT do: analyze rocket engine feed cycles with turbopumps or
pressure-fed liquids (rocket-engine-cycle owns pump-fed and
pressure-fed cycles); design combustion chambers or solid/hybrid
motors (combustion-chamber-design, solid-rocket-motor,
hybrid-rocket-motor own those); size the propellant tank structure
(space-systems propellant-tank-sizing owns tank volume and wall
sizing); design electric thrusters (propulsion electric pack owns
Hall, ion, electrothermal thrusters); control the spacecraft
attitude with the thruster (space-systems adcs leaves own control
laws). This leaf covers the gas thruster itself: choked flow,
blowdown, impulse.

## Model (implement exactly)

Module constants:
- G0 = 9.80665 (m/s2).
- GAMMA_N2 = 1.4, R_N2 = 296.8 (J/kg/K) for nitrogen.
- CF_CONST = sqrt(GAMMA/R * (2/(GAMMA+1))^((GAMMA+1)/(GAMMA-1)))
  computed from the two constants above; for N2 the value is
  0.039746 (1/s * sqrt(K)? see the formula: m_dot = P A* CF_CONST /
  sqrt(T)).

Functions (pure stdlib, floats):
- choked_mass_flow(pressure, temperature, throat_area,
  gamma=GAMMA_N2, gas_const=R_N2) -> float:
  m_dot = pressure * throat_area / sqrt(temperature) *
  sqrt(gamma/gas_const * (2/(gamma+1))**((gamma+1)/(gamma-1))).
  ValueError on pressure <= 0, temperature <= 0, throat_area <= 0.
- thrust(mass_flow, isp) -> float: F = mass_flow * isp * G0.
  ValueError on mass_flow < 0 or isp <= 0.
- tank_gas_mass(pressure, volume, temperature, gas_const=R_N2) ->
  float: m = pressure * volume / (gas_const * temperature). ValueError
  on pressure <= 0, volume <= 0, temperature <= 0.
- blowdown_time_constant(tank_mass, mass_flow0) -> float:
  tau = tank_mass / mass_flow0. ValueError if mass_flow0 <= 0.
- pressure_at_time(p0, t, tau) -> float: p = p0 * exp(-t / tau)
  (isothermal blowdown model). ValueError on tau <= 0 or t < 0.
- operating_time(p0, p_min, tau) -> float:
  t = tau * ln(p0 / p_min). ValueError if p_min >= p0 or p_min <= 0.
- total_impulse(isp, tank_mass0, tank_mass_final) -> float:
  I = isp * G0 * (tank_mass0 - tank_mass_final). ValueError if the
  final mass is above the initial mass.
- size_thruster(plenum_pressure, plenum_volume, temperature,
  throat_diameter, isp, p_min, t_query=30.0) -> dict: convenience
  chain returning {throat_area, mass_flow0, thrust_N, tank_mass_kg,
  time_constant_s, pressure_at_tquery, operating_time_s,
  total_impulse_Ns, mass_at_pmin}. All inputs SI (pascals, m3, K, m,
  s). ValueErrors propagate.

## Worked example

Nitrogen plenum: P0 = 25 MPa, V = 0.03 m3, T = 293 K, throat diameter
0.5 mm, Isp = 65 s, P_min = 2 MPa.

Deterministic anchors (compute with the exact formulas; assert within
the stated tolerances):
- throat_area = pi/4 * (0.5e-3)^2 = 1.9635e-7 m2 (within 1e-12).
- choked_mass_flow(25e6, 293, 1.9635e-7) = 0.011398 kg/s (within
  1e-5).
- thrust(0.011398, 65) = 7.265 N (within 0.01).
- tank_gas_mass(25e6, 0.03, 293) = 8.6244 kg (within 0.001).
- blowdown_time_constant(8.6244, 0.011398) = 756.7 s (within 0.5).
- pressure_at_time(25e6, 30, 756.7) = 24.028 MPa (within 0.01 MPa).
- operating_time(25e6, 2e6, 756.7) = 1911.1 s (within 1.0).
- total_impulse(65, 8.6244, tank_gas_mass(2e6, 0.03, 293)) =
  tank_gas_mass at 2 MPa = 0.68995 kg; I = 65*9.80665*(8.6244 -
  0.68995) = 5057.7 Ns (within 1.0).
- Mass flow and thrust at P_min scale with pressure: m_dot_min =
  0.000912 kg/s, F_min = 0.581 N (within 1e-5 / 0.01).
- ValueErrors: pressure 0, temperature 0, isp 0, mass_flow0 0, p_min
  above p0, negative t_query.

Keep at least 16 test methods: choked flow anchor, thrust anchor,
tank mass anchor, time constant anchor, pressure history anchor,
operating time anchor, total impulse anchor, linear scaling of
m_dot with pressure (round-trip), isothermal pressure decay shape,
ValueErrors. Runs offline in under 20 s.

## Corpus tasks (ids w29-cold-gas-thruster-1/2)

Distinctive tokens: cold gas thruster, nitrogen RCS, choked mass flow,
plenum blowdown, total impulse, reaction control thruster sizing,
isothermal blowdown time constant. Avoid: turbopump, pump-fed,
gas-generator cycle, staged combustion (rocket-engine-cycle);
combustion chamber, solid propellant, hybrid grain (combustion-
chamber-design, solid-rocket-motor, hybrid-rocket-motor); tank wall
sizing, tank volume (space-systems propellant-tank-sizing).

1. "size a nitrogen cold gas thruster for spacecraft RCS: choked mass
   flow through a 0.5 mm throat at 25 MPa plenum, thrust at 65 s Isp,
   and total impulse over the isothermal blowdown to 2 MPa"
2. "compute the blowdown pressure history and operating time of a
   cold gas reaction control system with a 0.03 m3 plenum starting at
   25 MPa"

## SKILL body notes

Pair with rocket-engine-cycle (the pressure-fed and pump-fed context
this thruster class replaces for small spacecraft), nozzle-design
(throat and expansion geometry), thrust-vector-control (larger engines
steered mechanically), and space-systems propellant-tank-sizing (the
plenum tank that holds the gas). State the boundary: this leaf is the
gas thruster flow and blowdown model, not a tank structural sizer and
not an attitude control law. ecss is reference-only for spacecraft
propulsion engineering context. Mirror the rocket pack SKILL body style
(SI units, stdlib only, deterministic offline).

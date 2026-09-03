# Wave-25 leaf spec: hybrid-rocket-motor (propulsion, rocket pack)

- Path: skills/propulsion/rocket/hybrid-rocket-motor/
- Pack: rocket (existing siblings: rocket-engine-cycle, solid-rocket-
  motor, rocket-staging, rocket-sizing, combustion-chamber-design,
  nozzle-design, propellant-selection, thrust-vector-control)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: propulsion

## Claim

Size and analyze a hybrid rocket motor with a solid fuel grain and a
liquid or gaseous oxidizer: compute the fuel regression rate from the
oxidizer mass flux with the classic regression law, solve the oxidizer
to fuel ratio from the fuel production and the oxidizer flow, compute
the chamber pressure equilibrium between the fuel production and the
choked nozzle discharge, derive the mass flow, thrust, and total
impulse, and judge the O/F shift over the burn as the port opens.
Produces the motor ballistics summary with the O/F ratio, chamber
pressure, burn time, thrust, and impulse, and the O/F shift trend.

Does NOT do: solid-propellant ballistics with the Vieille pressure
exponent burn rate and grain neutrality classification (solid-rocket-
motor owns the all-solid grain), liquid engine feed cycles and turbopump
power (rocket-engine-cycle), staged combustion chemistry or c* for
equilibrium liquids (cea-rocket-combustion). This leaf is the hybrid
(solid fuel + fluid oxidizer) motor model.

## Model (implement exactly)

- Regression rate (classic hybrid law): r_dot = a * G_o^n * L^m where
  G_o is the oxidizer mass flux (kg/m2/s) through the port and a, n, m
  are fuel-specific constants; provide module constants for a typical
  HTPB fuel with N2O or LOX (reference-only typicals: e.g. HTPB/N2O
  a ~ 0.1-0.2 mm/s per (kg/m2/s)^n with n ~ 0.5-0.7; state the exact
  constants you use and label them reference-only typicals).
- Oxidizer mass flux: G_o = m_dot_o / A_port where A_port is the port
  cross-section area (assume circular port for the initial and burn-
  average geometry; provide the initial port radius input).
- Fuel mass flow: m_dot_f = rho_f * r_dot * A_burn where A_burn is the
  burn area (cylindrical port: A_burn = pi * D_port * L_grain).
- O/F ratio: OF = m_dot_o / m_dot_f.
- Total mass flow: m_dot = m_dot_o + m_dot_f.
- Chamber pressure equilibrium: p_c * A_t / c* = m_dot (mass
  conservation through the choked throat) with A_t the throat area and
  c* the characteristic velocity (input or module typical for the fuel/
  oxidizer pair; state it). Solve p_c iteratively or directly given
  that m_dot_f depends on G_o (which depends on m_dot_o and A_port) and
  m_dot_o is set by the feed system input; implement a deterministic
  fixed-point or analytic solve with the documented assumptions and
  assert the mass balance.
- Thrust: F = c_f * p_c * A_t with the thrust coefficient c_f from the
  nozzle (input or computed from the nozzle area ratio and the pressure
  ratio using the standard c_f relation; module constant option).
  Provide the total impulse I_tot = integral F dt over the burn time.
- Burn time: from the fuel mass consumed (web burned: port radius
  growth r_final - r_initial at the regression rate, integrated simply
  with the burn-average flux or a step scheme; document the scheme).
- O/F shift: compare OF at the beginning (small port, high flux) and end
  (large port, lower flux) of the burn and report the shift direction
  and magnitude.
Functions:
- regression_rate(g_o, fuel) -> m/s
- oxidizer_mass_flux(m_dot_o, port_area) -> kg/m2/s
- fuel_mass_flow(rho_f, r_dot, burn_area) -> kg/s
- of_ratio(m_dot_o, m_dot_f) -> -
- chamber_pressure(m_dot, c_star, area_throat) -> Pa (with mass balance)
- thrust(thrust_coeff, p_c, area_throat) -> N
- burn_time(web, r_dot_avg) -> s
- of_shift(...) -> dict (of_initial, of_final, shift)
- hybrid_motor_summary(...) -> dict (ballistics summary)
ValueError on: negative flows, zero port or throat area, unknown fuel,
n outside (0,1), m_dot_o <= 0, rho_f <= 0.

## Worked example

Typical lab-scale HTPB/N2O hybrid: oxidizer flow 0.3 kg/s, initial port
diameter 40 mm, grain length 600 mm, rho_f ~ 920 kg/m3, A_t sized for
the target pressure. Compute the regression rate, O/F, chamber pressure,
thrust, burn time, and the O/F shift; quote the real numbers from your
module in the SKILL and assert them.

## Corpus tasks (ids w25-hybrid-rocket-motor-1/2)

Distinctive tokens: hybrid rocket motor, regression rate, oxidizer mass
flux, solid fuel grain, oxidizer to fuel ratio, O/F shift, port area,
HTPB, hybrid grain. Avoid: Vieille burn rate, web thickness, AP/HTPB
composite propellant, pressure exponent, staged combustion, turbopump
(owned by solid-rocket-motor / rocket-engine-cycle).

1. "size the hybrid rocket motor with the HTPB grain and the nitrous
   oxidizer: compute the regression rate from the oxidizer mass flux,
   the O/F ratio, and the chamber pressure at the equilibrium burn"
2. "estimate the O/F shift over the hybrid grain burn as the port opens
   and produce the thrust and total impulse for the motor"

## SKILL body notes

Pair with solid-rocket-motor (all-solid counterpart), rocket-engine-
cycle, nozzle-design (throat sizing), propellant-selection. Worked
example uses module constants and real outputs. Compliance: ECSS
propulsion design practice referenced by name; regression constants are
reference-only typicals, no reproduced tables.

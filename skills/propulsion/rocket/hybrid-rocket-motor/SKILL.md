---
name: hybrid-rocket-motor
description: "Use when you must size and analyze a hybrid rocket motor burning a solid fuel grain with a fluid oxidizer: compute the fuel regression rate from the oxidizer mass flux, solve the oxidizer to fuel ratio, find the chamber pressure equilibrium with the choked nozzle discharge, derive the mass flow, thrust and total impulse, and judge the O/F shift as the port opens. Reference-only typical HTPB grain constants cover the nitrous oxide and liquid oxygen oxidizers. Produces the ballistics summary with the O/F ratio, chamber pressure, burn time, thrust, impulse and the O/F shift trend. Trigger: hybrid rocket motor, regression rate, solid fuel grain, oxidizer to fuel ratio, O/F shift, HTPB, hybrid grain."
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
  tags: [hybrid-rocket-motor, regression-rate, oxidizer-mass-flux, solid-fuel-grain, oxidizer-to-fuel-ratio, of-shift, port-area, hybrid-grain]
  version: 0.1.0
  author: Aero Agent Skills
---

# Hybrid Rocket Motor (propulsion/rocket/hybrid-rocket-motor)

Use when the task is hybrid rocket motor design and ballistics for a
motor that burns a solid fuel grain with a liquid or gaseous oxidizer:
the fuel regression rate driven by the oxidizer mass flux through the
port, the oxidizer to fuel ratio, the chamber pressure equilibrium
against the choked nozzle discharge, thrust, total impulse, burn time,
and the O/F shift as the port opens. This leaf is the hybrid counterpart
of the all-solid grain ballistics in propulsion/rocket/solid-rocket-motor
and pairs with propulsion/rocket/rocket-engine-cycle for the oxidizer
feed, propulsion/rocket/nozzle-design for throat sizing, and
propulsion/rocket/propellant-selection for the propellant families. The
model is pure Python, stdlib only, with reference-only typical HTPB grain
constants for N2O and LOX oxidizers.

## Domain quick reference

- Regression law (classic hybrid): r_dot = a * G_o^n * (L_grain /
  L_ref)^m, with G_o the oxidizer mass flux through the port, a, n, m
  fuel-specific constants and L_ref the reference grain length of the
  correlation. Reference-only typicals: HTPB/N2O a = 1.2e-4 m/s per
  (kg/m2/s)^0.55 (0.12 mm/s), n = 0.55, m = -0.20; HTPB/LOX a = 1.8e-4,
  n = 0.50, m = -0.15; L_ref = 0.6 m for both. The fuel flow scales as
  r^(1 - 2n) with the port radius, so a 0.5 exponent holds the fuel flow
  flat as the port opens.
- Oxidizer mass flux: G_o = m_dot_o / A_port, with A_port = pi * r^2 for
  a circular port of radius r.
- Fuel mass flow: m_dot_f = rho_f * r_dot * A_burn, with the cylindrical
  port burn area A_burn = pi * D_port * L_grain and HTPB density rho_f
  near 920 kg/m3.
- O/F ratio: OF = m_dot_o / m_dot_f; total flow m_dot = m_dot_o +
  m_dot_f. The hybrid O/F shifts over the burn because the fuel side
  responds to the flux while the oxidizer side is feed-limited.
- Chamber pressure equilibrium: p_c * A_t / c* = m_dot (mass
  conservation through the choked throat), so p_c = m_dot * c* / A_t.
  With the feed-limited oxidizer flow the equilibrium is direct; the
  burn rate is flux-driven, not pressure-driven, unlike the all-solid
  grain. Reference-only typical characteristic velocities: HTPB/N2O c*
  near 1500 m/s, HTPB/LOX near 1750 m/s.
- Thrust: F = c_f * p_c * A_t, with thrust coefficient c_f from the
  nozzle (module default 1.4, reference-only typical).
- Burn time: t_b = web / r_dot_avg, with the web r_final - r_initial
  burned normal to the port and the rate taken at the mid-burn geometry
  (burn-average flux scheme).
- Total impulse: I_tot = F_mid * t_b, the mid-burn thrust held over the
  burn time; cross-checked against the fuel consumed.
- O/F shift: the port radius grows, G_o decays, and OF = m_dot_o /
  m_dot_f moves. For HTPB/N2O (n = 0.55) the O/F rises a few percent
  over a 10 mm web; direction and magnitude come from of_shift.
- Units are SI throughout: Pa, m, m^2, kg/s, m/s, N, N*s.
- ECSS space-systems standards frame the rocket propulsion context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the motor: oxidizer mass flow m_dot_o (feed-limited input), the
   fuel pair (fuel), the initial port radius r_initial, the burned web
   r_final - r_initial, and the grain length L_grain.
2. Size the throat: iterate hybrid_motor_summary over area_throat until
   the initial station chamber pressure sits at the target (about
   2.346e-4 m2 for the 3.0 MPa example below).
3. Get the regression side: oxidizer_mass_flux from m_dot_o and
   port_area_circular, then regression_rate (reference length) or
   regression_rate_at_length for the actual grain length.
4. Get the fuel production: burn_area_cylindrical for the port surface,
   then fuel_mass_flow with the grain density.
5. Combine: of_ratio for the mixture and the total m_dot_o + m_dot_f.
6. Get the equilibrium: chamber_pressure(m_dot, c_star, area_throat),
   then thrust with the nozzle thrust coefficient.
7. Judge the burn: burn_time from the web and the mid-burn rate, and
   of_shift for the mixture trend as the port opens.
8. Pull the full picture from hybrid_motor_summary: the ballistics
   summary dict with the initial, mid and final stations, burn time,
   total impulse, fuel consumed, mass balance error and verdict.
9. Confirm the deterministic checks with the contract test
   scripts/test_hybrid_rocket_motor.py.

## Worked example

A lab-scale HTPB/N2O hybrid: m_dot_o = 0.3 kg/s of nitrous oxide,
initial port diameter 40 mm (r = 0.02 m), grain length 600 mm,
rho_f = 920 kg/m3, c* = 1500 m/s, and a throat sized for 3.0 MPa at
ignition, A_t = 2.346e-4 m2 (about 17.3 mm throat diameter):

- Initial flux and rate: G_o = 0.3 / (pi * 0.02^2) = 238.7 kg/m2/s;
  r_dot = 1.2e-4 * 238.7^0.55 = 2.438e-3 m/s (about 2.44 mm/s).
- Fuel production: A_burn = pi * 0.04 * 0.6 = 0.07540 m2, so
  m_dot_f = 920 * 2.438e-3 * 0.07540 = 0.1691 kg/s.
- O/F ratio: OF = 0.3 / 0.1691 = 1.774; total flow
  m_dot = 0.4691 kg/s.
- Equilibrium: p_c = 0.4691 * 1500 / 2.346e-4 = 3.00 MPa (the sized
  condition); thrust F = 1.4 * 3.00e6 * 2.346e-4 = 985 N.
- End of burn at r = 0.03 m: G_o = 106.1 kg/m2/s, r_dot = 1.56 mm/s,
  OF = 1.847; the port growth holds the fuel flow nearly constant, so
  the pressure settles only to 2.96 MPa and the thrust to 971 N.
- O/F shift: +0.073 over the burn, 1.774 rising to 1.847, the classic
  mixture drift of a flux-driven fuel toward oxidizer-rich.
- Burn and impulse: mid-burn rate 1.91 mm/s over a 10 mm web gives
  t_b = 5.24 s; mid-burn thrust 977 N gives I_tot = 5124 N*s.
- Mass balance: mid-burn fuel flow times the burn time,
  0.1654 * 5.24 = 0.867 kg, equals the fuel consumed from the port
  growth rho_f * pi * (0.03^2 - 0.02^2) * 0.6 = 0.867 kg exactly; the
  summary mass balance error is zero.

## Verification

- Confirm regression_rate(238.73, "HTPB-N2O") returns 2.438e-3 m/s and
  regression_rate_at_length at the 0.6 m reference length matches it.
- Confirm the chamber pressure at the sized throat returns 3.00 MPa and
  the thrust 985.1 N (within tolerance).
- Confirm of_shift returns of_initial 1.774, of_final 1.847, shift
  +0.0734 and direction "increases".
- Confirm the flux compensation: for HTPB/LOX (n = 0.50) the fuel flow
  scales as r^(1 - 2n) = r^0, so the O/F holds flat as the port opens.
- Confirm hybrid_motor_summary reports burn_time 5.2429 s, total impulse
  5123.9 N*s, fuel consumed 0.8671 kg and mass_balance_error 0.0.
- Confirm every non-positive flow, zero or negative port and throat
  area, non-positive density and characteristic velocity, unknown fuel,
  and a final radius not above the initial radius raises ValueError.
- Run the contract test offline: python3
  scripts/test_hybrid_rocket_motor.py (35 tests, deterministic).

## Related leaves

- propulsion/rocket/solid-rocket-motor: the all-solid counterpart; the
  pressure-driven grain ballistics of a fully solid charge live there,
  not in this flux-driven hybrid model.
- propulsion/rocket/rocket-engine-cycle: oxidizer feed-system cycles and
  feed pressure for the fluid side of the hybrid.
- propulsion/rocket/nozzle-design: throat sizing and the thrust
  coefficient used downstream of the chamber equilibrium.
- propulsion/rocket/propellant-selection: oxidizer and fuel families
  for the hybrid pair.

## Pitfalls

- Treating the hybrid chamber pressure like an all-solid equilibrium:
  the burn rate is flux-driven (r_dot = a * G_o^n), not
  pressure-driven, so p_c = m_dot * c* / A_t follows the feed-limited
  oxidizer flow directly - the pressure-driven grain ballistics of
  solid-rocket-motor do not apply.
- Ignoring the O/F shift over the burn: the port grows, G_o decays and
  the mixture drifts oxidizer-rich (+0.073 in the worked example,
  1.774 to 1.847); reporting the ignition O/F as the motor O/F misses
  the classic hybrid drift.
- Expecting the fuel flow to stay flat for every pair: the fuel flow
  scales as r^(1 - 2n), so only a 0.5 flux exponent (HTPB/LOX n =
  0.50) holds the flow flat as the port opens; the HTPB/N2O n = 0.55
  case shifts a few percent over the web.
- Feeding a fuel outside the reference table: regression_rate raises
  ValueError on unknown fuels, and the a, n, m constants and L_ref =
  0.6 m are reference-only typicals - a real grain needs its own
  correlation, not the table defaults.
- Reading the mass balance without the fuel-consumed cross-check: the
  summary reports mass_balance_error 0.0 only when the mid-burn fuel
  flow over the burn time (0.1654 * 5.24 = 0.867 kg) equals the fuel
  consumed from the port growth rho_f * pi * (0.03^2 - 0.02^2) * 0.6 -
  a non-zero error means an input inconsistency.
- Oversizing the throat at the initial station: the throat is sized so
  the initial chamber pressure sits at the target (3.0 MPa with A_t =
  2.346e-4 m2); the end-of-burn pressure settles lower (2.96 MPa) as
  the port opens, so the sized condition is ignition, not the average
  burn.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hybrid_rocket_motor.py

The test covers the regression law and its power and length scaling, the
reference-only fuel table, oxidizer flux and port and burn areas, fuel
mass flow, the O/F ratio and its identities, the chamber pressure
equilibrium and thrust, burn time, the impulse and fuel-consumed mass
balance, the O/F shift trend with the n = 0.5 flux-compensation limit,
the full summary contract on the worked example, and ValueError
rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA download
  (ecss.nl/standards); hybrid regression ballistics is standard
  engineering methodology and the regression constants are reference-only
  typicals, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

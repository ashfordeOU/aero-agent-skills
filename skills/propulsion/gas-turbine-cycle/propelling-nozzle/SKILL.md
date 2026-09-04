---
name: propelling-nozzle
description: "Use when you must size the gas turbine propelling nozzle: decide the choked or unchoked regime from the nozzle pressure ratio against the critical ratio 1.851, size the throat area from the design mass flow and total conditions under the choked flow relation, and return the choked exit temperature, velocity and static pressure plus the gross thrust with the pressure term, or for an unchoked off-design point the exit Mach number and the actual mass flow the throat passes. Produces the regime flag, throat area, exit velocity, exit static pressure, gross thrust and expansion verdict. Trigger: propelling nozzle, convergent jet nozzle, nozzle throat area, choked nozzle regime, gross thrust pressure term, air breathing nozzle."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-33
    reference-only: true
gated: false
domain: propulsion
pack: gas-turbine-cycle
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: gas-turbine-cycle
  tags: [propelling-nozzle, convergent-jet-nozzle, nozzle-throat-area, choked-nozzle-regime, gross-thrust-pressure-term, air-breathing-nozzle]
  version: 0.1.0
  author: Aero Agent Skills
---

# Propelling Nozzle (propulsion/gas-turbine-cycle/propelling-nozzle)

Use when you must size the convergent propelling nozzle of an
air-breathing gas turbine at the conceptual level: deciding the choked
or unchoked regime from the nozzle pressure ratio against the critical
ratio, sizing the throat area from the design mass flow and total
conditions under the choked relation, and returning either the choked
exit state, exit velocity and gross thrust with the pressure term, or
for an unchoked off-design point the exit Mach number and the actual
mass flow the same throat passes. This leaf implements the standard
convergent nozzle model in pure Python, stdlib only. It pairs with
propulsion/gas-turbine-cycle/gas-turbine-cycle for the cycle context,
propulsion/turbofan/turbofan-cycle which consumes the jet velocity as
an input, and propulsion/rocket/nozzle-design which handles the
chamber-anchored choked rocket nozzle. Propulsion afterburner and
regenerative cycles set the nozzle entry conditions this leaf turns
into thrust.

## Domain quick reference

- Regime: the nozzle pressure ratio NPR = P0/Pa compares the total
  pressure upstream of the nozzle with ambient. The critical ratio is
  ((gamma+1)/2)^(gamma/(gamma-1)) = 1.851 at gamma = 1.33; a convergent
  nozzle chokes (sonic throat, Me = 1) when NPR >= critical, and runs
  subsonic unchoked below it.
- Choked throat sizing: m_dot = P0*At/sqrt(T0) * sqrt(gamma/R) *
  (2/(gamma+1))^((gamma+1)/(2*(gamma-1))). Rearranged it gives the
  throat area that passes a design mass flow at total conditions
  (P0, T0).
- Choked exit state at the throat: Te = T0*2/(gamma+1),
  Pe = P0*(2/(gamma+1))^(gamma/(gamma-1)), Ve = sqrt(gamma*R*Te), with
  mach = 1.0.
- Gross thrust: Fg = m_dot*Ve + (Pe - Pa)*At. The second term is the
  nozzle pressure thrust; it is active whenever the exit static
  pressure Pe exceeds ambient Pa (an imperfectly expanded nozzle) and
  vanishes when the nozzle is fully expanded (Pe = Pa).
- Unchoked exit: NPR = (1 + (gamma-1)/2*Me^2)^(gamma/(gamma-1)) solved
  for Me, then Te = T0/(1 + (gamma-1)/2*Me^2) and
  Ve = Me*sqrt(gamma*R*Te).
- Unchoked mass flow through a fixed throat:
  m_dot = P0*At/sqrt(T0) * sqrt(gamma/R) * Me *
  (1 + (gamma-1)/2*Me^2)^(-(gamma+1)/(2*(gamma-1))).
- Constants: GAMMA = 1.33 (air-breathing nozzle products convention,
  matching the afterburner-cycle anchor), R_GAS = 287.0 J/(kg K),
  P_AMB_DEFAULT = 101325.0 Pa. Units are SI throughout: Pa, K, kg/s,
  m2, m/s, N.
- FAR-33 frames the airworthiness context; the relations above are
  standard engineering methodology, summary-only per standards-map.yaml.

## Workflow

1. Fix the operating point: total pressure p0_pa, total temperature
   t0_k, ambient pressure p_amb_pa and the mass flow mdot_kg_s
   (nozzle_regime decides the regime from the nozzle pressure ratio
   against the critical ratio).
2. Confirm the design point is choked, then size the throat with
   throat_area from the design mass flow, P0 and T0; the choked
   relation is the sizing law for a convergent nozzle.
3. Get the choked exit state with choked_exit_state: Te, Ve, Pe, mach
   = 1.0 at the throat.
4. Form the gross thrust with gross_thrust from mdot, Ve, Pe, Pa and
   the throat area; the pressure term (Pe - Pa)*At rides on top of the
   momentum thrust mdot*Ve.
5. Run the full design pass with nozzle_sizing, which returns the
   regime, throat area, choked exit state, gross thrust and the
   expansion verdict (FULLY_EXPANDED or PRESSURE_TERM_ACTIVE).
6. For an off-design point on the fixed throat, run off_design_nozzle:
   when the lower P0 keeps NPR below the critical ratio it returns the
   subsonic exit Mach number, exit velocity and the actual mass flow
   the throat passes; the unchoked_exit_state and unchoked_mass_flow
   helpers expose the same quantities standalone.
7. Check non-physical inputs: every function raises ValueError for
   non-positive pressures, temperatures, areas or mass flows, for a
   nozzle pressure ratio at or below one, and when the unchoked
   relations are called at a choked regime.
8. Confirm the deterministic checks with the contract test
   scripts/test_propelling_nozzle.py.

## Worked example

Reference design point: P0 = 300 kPa, T0 = 900 K, mdot = 70 kg/s,
Pa = 101.325 kPa; off-design at P0 = 140 kPa on the same throat.

- Regime: NPR = 2.961 >= critical 1.851, so the design point is
  CHOKED (nozzle_regime).
- Throat area: At = 70*sqrt(900)/(300000*sqrt(1.33/287)*0.5833) =
  0.176305 m2 (throat_area).
- Choked exit: Te = 900*2/2.33 = 772.5 K, Ve = 543.0 m/s,
  Pe = 300000*(2/2.33)^(1.33/0.33) = 162109 Pa (162.1 kPa), mach 1.0
  (choked_exit_state).
- Gross thrust: Fg = 70*543.03 + (162109 - 101325)*0.176305 =
  48728.7 N, about 48.7 kN; verdict PRESSURE_TERM_ACTIVE because
  Pe > Pa (nozzle_sizing).
- Off-design unchoked: NPR = 1.382 < 1.851; Me = 0.7115,
  Ve = 400.6 m/s, and the same 0.176305 m2 throat passes 30.02 kg/s
  (off_design_nozzle).
- Continuity check: the unchoked flow evaluated just below the
  critical ratio equals the choked flow at the same total pressure
  within 1e-3 relative, so the two relations join smoothly at the
  choke boundary.

## Verification

- Confirm nozzle_sizing(70, 300000, 900, 101325) returns regime
  choked, throat area 0.176305 m2, Te 772.5 K, Ve 543.0 m/s,
  Pe 162109 Pa, gross thrust 48728.7 N and verdict
  PRESSURE_TERM_ACTIVE.
- Confirm off_design_nozzle(0.176305, 140000, 900, 101325) returns
  Me 0.7115, Ve 400.6 m/s and an actual mass flow of 30.02 kg/s.
- Confirm the choked exit identities: Te = T0*2/(gamma+1) and
  Ve = sqrt(gamma*R*Te) hold exactly; with Pe = Pa the gross thrust
  reduces to mdot*Ve.
- Confirm the unchoked flow at the critical ratio matches the choked
  flow within 1e-3 relative (continuity at the choke boundary).
- Confirm every non-positive pressure, temperature, area or mass flow,
  a nozzle pressure ratio at or below one, and every call of the
  unchoked relations at a choked regime raises ValueError.
- Run the contract test offline: python3
  scripts/test_propelling_nozzle.py (34 tests, deterministic).

## Related leaves

- propulsion/gas-turbine-cycle/gas-turbine-cycle: the cycle analysis
  that sets nozzle entry total conditions.
- propulsion/gas-turbine-cycle/afterburner-cycle: heat addition
  upstream of the nozzle and the fully expanded ideal jet velocity.
- propulsion/gas-turbine-cycle/regenerative-cycle and
  real-cycle-effects: alternative cycle layouts and loss effects that
  change the nozzle entry state.
- propulsion/gas-turbine-cycle/combustor-design: the combustion
  chamber that delivers the entry gas.
- propulsion/turbofan/turbofan-cycle: consumes the jet velocity
  produced here as an input to the net thrust loop.
- propulsion/engine-airframe/engine-airframe-integration: installation
  drag and aircraft-level nozzle trade context.
- propulsion/rocket/nozzle-design: the rocket nozzle counterpart,
  chamber-anchored, always choked, with its own gas property model.

## Pitfalls

- Sizing the throat with the unchoked relation: the throat area law
  above is the choked sizing relation and only applies when the design
  point is choked; feeding an unchoked design point to nozzle_sizing
  raises ValueError rather than returning a misleading area.
- Dropping the pressure term: at the worked example the momentum term
  is 70*543.03 = 38.0 kN while the pressure term (Pe - Pa)*At adds
  about 10.7 kN, so gross thrust is 48.7 kN; quoting mdot*Ve alone
  understates the nozzle by more than 20 percent.
- Applying choked exit relations below the critical ratio: an unchoked
  nozzle has a subsonic exit with Pe = Pa and its flow follows the
  isentropic Mach relation; forcing Me = 1 inflates both velocity and
  thrust.
- Borrowing rocket nozzle logic: rocket nozzle-design is anchored to
  chamber conditions with combustion gas properties and always chokes;
  the air-breathing propelling nozzle sees total conditions from the
  engine cycle, can run unchoked over much of the flight envelope, and
  needs the pressure term whenever it is not fully expanded.
- Confusing total and static state: the nozzle works on total P0, T0
  delivered by the cycle, but the exit static pressure Pe (not P0) is
  what appears in the pressure thrust term against ambient.
- Mismatching gamma: this leaf uses the 1.33 nozzle products
  convention that matches the afterburner-cycle anchor; using 1.4 cold
  air values shifts the critical ratio to about 1.893 and changes both
  the choke decision and the sized area.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_propelling_nozzle.py

The test covers the choked design point sizing (throat area 0.176305
m2, Te 772.5 K, Ve 543.0 m/s, Pe 162109 Pa, gross thrust 48728.7 N,
verdict PRESSURE_TERM_ACTIVE), the unchoked off-design point (Me
0.7115, Ve 400.6 m/s, actual flow 30.02 kg/s), regime decisions at NPR
2.961 and 1.382 against the critical ratio 1.851, the choked exit
identities Te = T0*2/(gamma+1) and Ve = sqrt(gamma*R*Te), the
fully-expanded identity Fg = mdot*Ve at Pe = Pa, continuity of the
unchoked and choked flow relations at the critical ratio, dict key
sets, determinism, and ValueError rejection of non-positive pressures,
temperatures, areas and mass flows, nozzle pressure ratios at or below
one, and unchoked relations called at a choked regime.

## Compliance

- Standards referenced, not reproduced: FAR-33 is named as the
  airworthiness frame for engine installation; the convergent nozzle
  relations above are standard engineering methodology, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

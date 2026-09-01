---
name: combustion-chamber-design
description: "Use when you must size and assess the combustion chamber of a rocket engine: compute the characteristic velocity (c-star) from the chamber pressure, the throat area, and the propellant mass flow, estimate the theoretical c-star from the chamber temperature, the molecular weight, and the specific heat ratio, size the throat area from the propellant flow and the chamber pressure, compute the thrust coefficient and the thrust from the chamber pressure and the throat area, and derive the chamber volume from L-star, the contraction ratio from the chamber area and the throat, and the vacuum specific impulse from the thrust and the mass flow. Produces the chamber sizing dict that feeds the nozzle-design and the engine balance. Trigger: rocket combustion chamber, characteristic velocity, c-star, thrust coefficient, contraction ratio, chamber pressure, chamber volume, L-star, throat area."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [combustion-chamber-design, rocket-combustion-chamber, characteristic-velocity, c-star, thrust-coefficient, contraction-ratio, chamber-pressure, chamber-volume, l-star, throat-area, mass-flow, vacuum-specific-impulse]
  version: 0.1.0
  author: AeroSkills
---

# Combustion Chamber Design (propulsion/rocket/combustion-chamber-design)

Use when the task is rocket combustion chamber design: the
characteristic velocity, the throat area, the thrust coefficient, the
contraction ratio, the chamber volume from L-star, and the vacuum
specific impulse of the chamber upstream of the nozzle throat.

## Domain quick reference

- Characteristic velocity (defining relation): c-star = Pc * At / mdot
  with Pc the chamber pressure in Pa, At the throat area in m^2, and
  mdot the propellant mass flow in kg/s; c-star has units of m/s and
  measures the combustion quality of the chamber. Worked: LOX/RP-1 at
  7.0 MPa, throat area 0.02 m^2, and 80 kg/s gives c-star =
  7e6 * 0.02 / 80 = 1750 m/s, a typical delivered value.
- Theoretical c-star from gas properties:
  c-star = sqrt(gamma * R * Tc) / (gamma * sqrt((2 / (gamma + 1))^((gamma + 1) / (gamma - 1))))
  with R = 8314 / Mw the gas constant from the molecular weight Mw in
  kg/kmol and Tc the chamber temperature in K. Worked: LOX/RP-1 at
  Tc = 3670 K, Mw = 23, gamma = 1.20 gives about 1776 m/s. The ratio
  of delivered to theoretical c-star is the c-star efficiency, 0.92 to
  0.98; 1750 / 1776 = 0.985 in the worked case.
- Throat area from the propellant flow: At = mdot * c-star / Pc.
  Worked: 80 * 1750 / 7e6 = 0.02 m^2, closing the loop with the
  defining relation.
- Thrust coefficient: Cf = F / (Pc * At) with F the thrust in N; Cf is
  about 1.4 to 1.6 at sea level and 1.8 to 2.0 in vacuum depending on
  the expansion. Worked: 252 kN over 7.0 MPa and 0.02 m^2 gives
  Cf = 252000 / 140000 = 1.8, a vacuum-class value. Thrust from the
  coefficient: F = Cf * Pc * At.
- Vacuum specific impulse: Isp = F / (mdot * g0) with g0 = 9.80665
  m/s^2. Worked: 252000 / (80 * 9.80665) = 321.2 s, consistent with
  LOX/RP-1 vacuum performance.
- Contraction ratio: epsilon_c = Ac / At with Ac the chamber cross
  section area, typically 2 to 5 for liquid engines. Worked: Ac =
  0.07 m^2 over At = 0.02 m^2 gives epsilon_c = 3.5.
- Chamber volume from L-star: Vc = L-star * At with L-star the
  characteristic chamber length in m, typically 0.5 to 1.5 m for
  liquid propellants; L-star sets the residence time for complete
  combustion. Worked: L-star = 0.9 m gives Vc = 0.018 m^3.
- Throat radius: for a circular throat, r = sqrt(At / pi). Worked:
  At = 0.02 m^2 gives r = 0.0798 m, about 80 mm.
- Theoretical c-star depends only on the gas (Tc, Mw, gamma), not on
  the chamber pressure; raising Pc raises the achievable thrust at
  fixed throat area but not the ideal c-star.

## Workflow

1. Fix the design point: chamber pressure Pc, propellant mass flow
   mdot, and the propellant gas properties Tc, Mw, gamma.
2. Compute the theoretical c-star with theoretical_cstar and the
   delivered c-star with characteristic_velocity once the throat area
   is known; the ratio gives the c-star efficiency.
3. Size the throat area with throat_area_from_flow(mdot, c-star, Pc);
   this At is the interface to the nozzle downstream.
4. Compute the thrust coefficient with thrust_coefficient, or the
   thrust with thrust_from_cf, and the vacuum specific impulse with
   vacuum_specific_impulse.
5. Select the chamber cross section and compute the contraction ratio
   with contraction_ratio and the chamber volume with
   chamber_volume(L-star, At).
6. Check the throat radius with nozzle_throat_radius for the
   mechanical layout, then pass At, Pc, and the gas properties to the
   nozzle-design leaf for the expansion downstream of the throat.

## Pitfalls

- Routing the nozzle downstream of the throat here: area ratio, exit
  Mach, expansion, and the diverging section belong to the
  nozzle-design leaf; this leaf stops at the throat and hands over At.
- Routing propellant choice here: mixture ratio, density impulse, and
  storability belong to propellant-selection; this leaf consumes the
  chosen propellant's Tc, Mw, and gamma.
- Routing the rocket equation here: delta-v, mass ratio, and staging
  belong to rocket-sizing and rocket-staging; the Isp from this leaf
  feeds those leaves.
- Routing gas turbine combustor questions here: stoichiometric
  fuel-air-ratio and adiabatic flame temperature for continuous-flow
  jet engine combustors belong to combustor-design; a rocket chamber
  is a different device with c-star bookkeeping.
- Confusing the two c-star values: c-star = Pc * At / mdot is the
  measured defining value; the gas-property formula is the ideal
  ceiling, and their ratio is the c-star efficiency, 0.92 to 0.98.
- Using psi instead of Pa or bar: c-star, Cf, and At sizing are only
  consistent in Pa, m^2, kg/s, and N; a pressure in bar silently
  shifts every result by 1e5.
- Forgetting g0 in the specific impulse: Isp = F / (mdot * g0), so a
  252000 N thrust at 80 kg/s gives 321 s, not 3150 s.
- Accepting a contraction ratio at or below 1: the chamber must
  converge into the throat, so Ac must exceed At and contraction_ratio
  raises ValueError otherwise.
- Sizing the volume without L-star: Vc = L-star * At, so a small
  throat at fixed L-star gives a small chamber and a short residence
  time, which lowers the c-star efficiency.

## Behavior contract (gate 3)

The combustion chamber sizing logic is exercised by the gate 3
contract test: scripts/test_combustion_chamber_design.py against
scripts/combustion_chamber_design_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_combustion_chamber_design.py

## Compliance

- ECSS is cited as reference only for the space systems propulsion
  context; the characteristic velocity, thrust coefficient, L-star,
  and contraction ratio relations are standard rocket propulsion
  methodology, paraphrased here. No proprietary or copyrighted text is
  reproduced.
- compliance: STANDARDS-REF, gated: false.

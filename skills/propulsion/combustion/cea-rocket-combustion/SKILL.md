---
name: cea-rocket-combustion
description: "Use when you must predict the thermochemistry and performance of a rocket propellant combination in the spirit of NASA CEA: compute the adiabatic flame temperature and the chamber conditions from the propellant choice, the mixture ratio, and the chamber pressure with a simplified frozen-flow equilibrium over representative species, derive the characteristic velocity (c-star) and the ideal vacuum and sea-level specific impulse, run a mixture ratio trade, and estimate gamma, the molecular weight of the combustion products, the c-star efficiency, and the sensitivity of Isp to the mixture ratio. Produces the chamber temperature, the equilibrium composition, the c-star, the ideal Isp values, and the trade table, in SI units. Trigger: adiabatic flame temperature, characteristic velocity, c-star, vacuum specific impulse, mixture ratio trade, frozen flow, combustion thermochemistry."
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
  subdomain: combustion
  tags: [rocket-combustion, adiabatic-flame-temperature, characteristic-velocity, specific-impulse, mixture-ratio, frozen-flow, chamber-pressure, thermochemistry, c-star, propellant-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# Rocket Combustion Thermochemistry (propulsion/combustion/cea-rocket-combustion)

Use when the task is rocket combustion thermochemistry in the spirit of
NASA CEA: the adiabatic flame temperature, the chamber conditions
(composition, molecular weight, gamma, characteristic velocity c-star)
and the ideal vacuum and sea-level specific impulse from the propellant
choice, the mixture ratio, and the chamber pressure, using a simplified
frozen-flow equilibrium model over representative species.

## Domain quick reference

- Adiabatic flame temperature Tc: the temperature at which the product
  enthalpy equals the reactant enthalpy, with the equilibrium composition
  solved at the same temperature (combustion enthalpy balance). Worked:
  LOX/RP-1 at O/F 2.56 and 7.0 MPa gives Tc = 3672 K, matching the
  representative published value of about 3670 K.
- Simplified equilibrium chemistry: representative species CO2, H2O, CO,
  H2, O2, OH, H, O plus inert N2, with the water-gas shift and H2O, H2
  and O2 dissociation equilibria derived from species Gibbs functions
  (quadratic heat capacity fits through 298, 1500 and 3500 K). The
  species data is representative, so the results reproduce representative
  published chamber conditions within a few percent.
- Characteristic velocity: c-star = sqrt(gamma R Tc) / (gamma
  sqrt((2/(gamma+1))^((gamma+1)/(gamma-1)))) with R = 8314.462 / Mw in
  J/(kg K). Worked: LOX/RP-1 at Tc = 3672 K, Mw = 22.1, gamma = 1.24
  gives c-star = 1791 m/s (published representative value about 1798).
- Ideal vacuum specific impulse (Pe = 0):
  Isp = sqrt(2 gamma/(gamma-1) R Tc) / g0 with g0 = 9.80665 m/s^2.
  Worked: LOX/LH2 at O/F 6.0 and 10 MPa gives Isp = 510 s.
- Ideal sea-level specific impulse: the same exhaust velocity formula
  with the exit pressure equal to the ambient pressure, Pe = 101325 Pa.
  Worked: LOX/LH2 at 10 MPa gives Isp = 386 s.
- Reference chamber states: LOX/RP-1 at O/F 2.56 and 7.0 MPa gives
  Tc = 3672 K, Mw = 22.1, gamma = 1.24, c-star = 1791 m/s, Isp_vac =
  386 s; LOX/LH2 at O/F 6.0 and 10 MPa gives Tc = 3666 K, Mw = 13.2,
  c-star = 2328 m/s, Isp_vac = 510 s; NTO/MMH at O/F 2.0 and 2 MPa
  gives Tc = 3340 K, c-star = 1726 m/s, Isp_vac = 368 s.
- Stoichiometric O/F ratios: LOX/RP-1 3.48, LOX/LH2 7.94, LOX/CH4 3.99,
  NTO/MMH 2.50. The maximum flame temperature sits near the design point
  slightly fuel-rich of stoichiometric.
- The reported Isp values are ideal-gas frozen-flow ceilings: real
  engines deliver roughly 80 to 95 percent of them because of finite
  expansion ratio, nozzle divergence, boundary layers and combustion
  losses. The c-star efficiency (0.92 to 0.98) and the Isp efficiency
  (0.8 to 0.95) bridge from the ideal ceilings to delivered values.
- Isp sensitivity to the mixture ratio: the fractional change of the
  ideal vacuum Isp per unit of O/F. Positive on the fuel-rich side of
  the model optimum, negative past it.

## Workflow

1. Name the propellant pair and fix the design point: mixture ratio and
   chamber pressure in Pa. Propellant families are cryogenic (LOX/RP-1,
   LOX/LH2, LOX/CH4) or hypergolic (NTO/MMH).
2. Compute the chamber state with chamber_conditions(name, ratio, pc):
   flame temperature, molecular weight, gamma, c-star, ideal vacuum and
   sea-level Isp, mole fractions and the energy balance closure error.
3. Run a mixture ratio trade with mixture_ratio_trade(name, pc, r_min,
   r_max, steps) and pick the design point from the flame temperature and
   Isp trend.
4. Check the sensitivity with isp_mixture_ratio_sensitivity(name, ratio,
   pc) to see which side of the optimum the design sits on.
5. Convert the ideal values to delivered estimates with
   cstar_with_efficiency and isp_with_efficiency, using representative
   efficiencies for the engine class.
6. Hand the chamber gas properties (Tc, Mw, gamma, c-star) to the
   combustion-chamber-design leaf for the throat sizing and to the
   nozzle-design leaf for the expansion downstream of the throat.

## Pitfalls

- Routing chamber geometry here: throat area, contraction ratio, L-star
  and chamber volume belong to combustion-chamber-design; this leaf
  produces the gas state (Tc, Mw, gamma, c-star) that feeds it.
- Routing propellant choice here: family classification, density impulse
  and storability belong to propellant-selection; this leaf consumes the
  chosen pair and produces its thermochemistry.
- Routing nozzle geometry here: area ratio, exit Mach and expansion
  belong to nozzle-design; this leaf only provides the ideal Isp from
  the chamber gas, not a nozzle design.
- Routing gas turbine combustor questions here: fuel-air-ratio and flame
  temperature for continuous-flow jet engine combustors belong to
  combustor-design; a rocket chamber is a different device with c-star
  bookkeeping.
- Reading the ideal Isp as a delivered prediction: the values are
  ideal-gas frozen-flow ceilings, 10 to 20 percent above real engines.
  Apply the efficiency helpers for quick-look delivered estimates.
- Expecting exact CEA agreement: the species set is representative
  (eight reactive species, no minor radicals), so molecular weight can
  differ by up to about 20 percent for LOX/LH2 while Tc and c-star stay
  within a few percent of representative published values.
- Using psi or bar instead of Pa: c-star and Isp are only consistent in
  Pa, kg, kmol and m/s; a pressure in bar silently shifts every result
  by 1e5.
- Confusing the mixture ratio with the rocket equation mass ratio:
  O/F is the oxidizer-to-fuel mass ratio in the chamber; m0/mf is the
  vehicle mass ratio in rocket-sizing.
- Expecting the flame temperature to rise forever with O/F: past the
  design point the excess oxidizer dilutes the products and Tc falls.
- Treating the frozen Isp optimum as the real one: the frozen-flow
  optimum sits fuel-rich of the equilibrium CEA optimum, so read the
  sensitivity sign as indicative near the model optimum.

## Behavior contract (gate 3)

The equilibrium thermochemistry, flame temperature, c-star and Isp logic
is exercised by the gate 3 contract test:
scripts/test_cea_rocket_combustion.py against
scripts/cea_rocket_combustion_logic.py (stdlib unittest, offline,
deterministic). Run:
python3 scripts/test_cea_rocket_combustion.py

## Compliance

- ECSS is cited as reference only for the space systems propulsion
  context; the equilibrium thermochemistry, characteristic velocity and
  specific impulse relations are standard rocket propulsion methodology,
  paraphrased here. No proprietary or copyrighted text is reproduced.
- compliance: STANDARDS-REF, gated: false.

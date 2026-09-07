---
name: hydrazine-monopropellant-thruster
description: "Use when you must size and assess a hydrazine monopropellant thruster for spacecraft reaction control: compute the catalytic decomposition products and net decomposition heat release of hydrazine at a documented ammonia dissociation fraction, the adiabatic decomposition temperature from the hydrazine decomposition energy balance, and the frozen composition isentropic nozzle expansion of the decomposed gas mixture to the vacuum exhaust velocity, the vacuum specific impulse and the propellant mass flow at the required thrust, with the advisory catalyst-bed temperature band check. Produces the decomposed mixture composition, decomposition temperature, mixture gas constant, isentropic exponent, exhaust velocity, vacuum specific impulse, propellant mass flow and the catalyst-bed band verdict that size a monopropellant RCS thruster. Trigger: hydrazine-monopropellant-thruster, catalytic-decomposition, ammonia-dissociation-fraction, monopropellant-rcs, decomposition-temperature."
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
  tags: [hydrazine-monopropellant-thruster, catalytic-decomposition, ammonia-dissociation-fraction, monopropellant-rcs, decomposition-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# Hydrazine Monopropellant Thruster (propulsion/rocket/hydrazine-monopropellant-thruster)

Use when the task is sizing and assessing a hydrazine monopropellant
thruster for spacecraft reaction control: liquid hydrazine decomposes
catalytically over a catalyst bed and the hot product gas expands through a
nozzle to produce a small thrust for attitude control. This leaf implements
the hydrazine station model in pure Python, stdlib only: the catalytic
decomposition products and the net decomposition heat release at a
documented ammonia dissociation fraction, the adiabatic decomposition
(chamber) temperature from the Hess-law energy balance, and the
frozen-composition isentropic expansion of the decomposed gas mixture to
the vacuum exhaust velocity, the vacuum specific impulse and the
propellant mass flow at the thrust point, plus an advisory catalyst-bed
temperature band verdict. It pairs with propulsion/rocket/cold-gas-thruster
for the inert-gas RCS alternative this thruster class replaces on small
spacecraft, and with propulsion/rocket/rocket-engine-cycle for the feed
system that supplies the hydrazine. The boundary is strict: this leaf is
the decomposition station math, not a feed cycle model, not a nozzle
hardware sizer, not a tank sizer and not an attitude control law.

## Domain quick reference

- Primary decomposition: N2H4(l) -> (4/3) NH3 + (1/3) N2, releasing Q_BASE
  = 111.8833 kJ per mole of hydrazine fed. A documented fraction x of the
  ammonia formed then dissociates endothermically, NH3 -> (1/2) N2 +
  (3/2) H2, absorbing 45.94 kJ per mole of NH3. Products per mole N2H4:
  n_NH3 = (4/3)(1 - x), n_N2 = 1/3 + (2/3)x, n_H2 = 2x; total moles
  n_tot = 5/3 + (4/3)x (1.6667 frozen, 3.0 fully dissociated). Product mass
  closes on 32.04516 g at every x.
- Net heat release (Hess-law balance at 298.15 K): Q(x) = Q_BASE - (4/3) x
  * 45.94e3 J/mol, linear and decreasing in x: 111.8833 kJ/mol at x = 0,
  50.6300 kJ/mol at x = 1 (the N2H4(l) -> N2 + 2 H2 limit).
- Heat capacities: quadratic fits cp(T) = a + bT + cT^2 in J/(mol K)
  through reference points (298.15, 1000, 2000 K): NH3 (35.59, 51.10,
  62.60), N2 (29.12, 32.70, 36.03), H2 (28.84, 30.20, 33.00).
- Adiabatic decomposition temperature T_c: the root of product sensible
  heat from T_REF to T_c equaling Q(x), where the sensible heat integrates
  the mixture heat capacity; monotone left side makes the bisection on
  [298.15, 2600] K close the unique root.
- Mixture gas: M_mix = 32.04516 / n_tot g/mol, R_mix = 8314.462618 / M_mix
  J/(kg K), and the isentropic exponent gamma = cp_mix / (cp_mix - R_univ)
  with cp_mix the mole-fraction-weighted frozen mixture heat capacity,
  evaluated at the chamber state.
- Vacuum expansion (fully expanded, p_e = 0): v_e = sqrt(2 gamma/(gamma -
  1) R_mix T_c), vacuum specific impulse Isp = v_e / g0 with g0 = 9.80665
  m/s^2, and propellant mass flow at the thrust point mdot = F / v_e (the
  vacuum thrust F = mdot * v_e carries no exit-pressure term).
- Catalyst-bed continuous operating band (reference-only, advisory):
  1073.15 to 1423.15 K (800 to 1150 C class), reported from published
  hydrazine thruster catalyst-bed design monographs, never enforced.
- Units are SI throughout: K, J/mol, g/mol, J/(kg K), m/s, s, N, kg/s.
- ECSS frames the spacecraft propulsion context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the duty point: the required vacuum thrust F in N and the ammonia
   dissociation fraction x in [0, 1] (0 is the frozen limit, 1 the fully
   dissociated limit N2H4 -> N2 + 2 H2).
2. Decompose: decomposition_products(x) gives the moles of NH3, N2 and H2
   per mole of N2H4 fed and total_product_moles(x) the mixture total.
3. Energy release: decomposition_heat_released(x) gives the net
   decomposition heat release at the reference state, J per mole N2H4.
4. Chamber temperature: decomposition_temperature(x) solves the hydrazine
   decomposition energy balance by bisection for the adiabatic
   decomposition temperature T_c in K; product_heat_capacity(x, t_k)
   samples the mixture heat capacity at any temperature.
5. Mixture gas: mixture_molar_mass(x), mixture_gas_constant(x), and
   mixture_gamma(x, T_c) give the frozen-composition isentropic exponent at
   the chamber state.
6. Expand to vacuum: vacuum_exhaust_velocity(x) gives v_e, then
   vacuum_specific_impulse(x, g0) the vacuum specific impulse and
   propellant_mass_flow(F, x) the hydrazine flow at the thrust point.
7. Advisory check: within_catalyst_bed_band(T_c) reports whether the
   decomposition temperature sits inside the documented catalyst-bed band.
8. Confirm the deterministic checks and the domain guards with the contract
   test scripts/test_hydrazine_monopropellant_thruster.py.

## Worked example

A 5 N RCS thruster at ammonia dissociation fraction x = 0.4 and a 22 N RCS
thruster at x = 0.6, the two reaction control design points.

- 5 N point, x = 0.4: products per mole N2H4 fed are 0.8 NH3 + 0.6 N2 +
  0.8 H2 (2.2 mol total, mole fractions 0.3636 NH3, 0.2727 N2, 0.3636 H2);
  net heat release Q = 87382.0 J/mol; mixture molar mass 14.5660 g/mol with
  R_mix = 570.814 J/(kg K); decomposition temperature T_c = 1377.055 K;
  gamma at the chamber state 1.25176; vacuum exhaust velocity v_e =
  2795.808 m/s; vacuum specific impulse Isp = 285.093 s; propellant mass
  flow at 5 N: mdot = 5 / 2795.808 = 0.0017884 kg/s (1.788 g/s);
  catalyst-bed band verdict True (1377.055 K inside the reported band).
- 22 N point, x = 0.6: products 0.5333 NH3 + 0.7333 N2 + 1.2 H2 (2.4667
  mol total); Q = 75131.333 J/mol; M_mix = 12.9913 g/mol, R_mix = 640.003
  J/(kg K); T_c = 1201.560 K; gamma 1.29328; v_e = 2604.253 m/s;
  Isp = 265.560 s; mdot at 22 N = 0.0084477 kg/s (8.448 g/s); verdict True.
- Decomposition band endpoints: the frozen limit x = 0 gives T_c =
  1733.583 K with Isp = 323.093 s and verdict False (above the reported
  continuous bed band); the fully dissociated limit x = 1.0 gives
  T_c = 864.825 K with Isp = 227.095 s and verdict False (below it). The
  computed span 864.8 to 1733.6 K brackets the published decomposition-
  temperature band class of roughly 900 to 1700 K, and the fully
  dissociated ideal vacuum impulse 227.1 s sits at the low edge of the
  published real-engine vacuum impulse class of roughly 230 s.
- Read-off: the ideal-model impulses sit above the published real-engine
  class because real thrusters carry nozzle efficiency and finite-expansion
  losses that this leaf's fully expanded ideal vacuum form does not model;
  the gap is the loss account and the published class stays reference-only.
  The sweep shows the physics trade: pushing the dissociation fraction up
  cools the chamber (heat sunk into ammonia dissociation) and lightens the
  exhaust, but the temperature fall dominates, so Isp falls monotonically
  from 323.09 s (frozen) to 227.10 s (fully dissociated).

## Verification

- Confirm decomposition_products(0.4) returns (0.8, 0.6, 0.8),
  decomposition_heat_released(0.4) returns 87382.0 J/mol and
  decomposition_temperature(0.4) returns 1377.055 K.
- Confirm mixture_molar_mass(0.4) returns 14.5660 g/mol,
  mixture_gas_constant(0.4) returns 570.814 J/(kg K), and
  mixture_gamma(0.4, 1377.055) returns 1.25176.
- Confirm vacuum_exhaust_velocity(0.4) returns 2795.808 m/s,
  vacuum_specific_impulse(0.4) returns 285.093 s, and
  propellant_mass_flow(5.0, 0.4) returns 0.0017884 kg/s.
- Confirm the product masses close on 32.04516 g per mole N2H4 at every x
  (rel err 2.2e-16), the sensible-heat residual at each solved T_c is below
  1e-9 J, and decomposition_temperature(0.4) is bit-identical on repeated
  calls (deterministic, no RNG).
- Confirm every x outside [0, 1] or not finite, every non-positive sample
  temperature, g0 and thrust, and every non-finite band temperature raises
  ValueError, and that the endpoints T_c(0.0) = 1733.583 K and
  T_c(1.0) = 864.825 K plus the advisory band verdicts reproduce the
  published band class without enforcing it.
- Run the contract test offline: python3
  scripts/test_hydrazine_monopropellant_thruster.py (34 tests,
  deterministic).

## Related leaves

- propulsion/rocket/cold-gas-thruster: the inert gas RCS alternative;
  hydrazine appears there only as a deferred option, never as a reactant.
- propulsion/rocket/rocket-engine-cycle: the feed cycle that supplies the
  hydrazine; its monopropellant row is a feed-analysis table entry only.
- propulsion/rocket/nozzle-design and the nozzle leaves: the expansion
  hardware, throat area solve and exit pressure terms this leaf does not do.
- propulsion/electric/electrothermal-thruster: the electrically heated
  propellant alternative (NH3, N2, H2, He), a different energy source.
- space-systems/subsystems/propellant-tank-sizing: the hydrazine tank,
  sized from density and volume (its density example stays there).
- propulsion/rocket/thrust-vector-control: larger engines steered
  mechanically, the alternative to small RCS thrusters for attitude
  control.

## Pitfalls

- Solving for the ammonia dissociation fraction: x is a documented input,
  never solved; this model performs no chemical-equilibrium composition
  iteration.
- Treating the mixture as a constant-gamma gas: gamma is evaluated at the
  chamber state from the mole-fraction-weighted frozen composition heat
  capacity and rises from 1.1756 (NH3-rich frozen mix) to 1.3726 (fully
  dissociated N2 + 2 H2).
- Adding an exit-pressure thrust term: the exhaust velocity here is the
  fully expanded vacuum form of the decomposed gas only; nozzle sizing,
  area ratio and any (Pe - Pa) * Ae term belong to the nozzle leaves.
- Quoting the ideal impulse as a real engine performance: real thrusters
  run near 230 s vacuum because of nozzle efficiency and finite-expansion
  losses; the ideal frozen values (227 to 323 s across x) are the loss-free
  account and the published class stays reference-only.
- Treating the catalyst-bed band as an enforced limit: the band verdict is
  an advisory boolean report; a frozen-composition firing at 1733.6 K sits
  above the reported continuous band, which the mission must then manage.
- Using the model beyond its boundary: this leaf is the hydrazine
  decomposition station model, not a cold gas blowdown, not a feed-cycle
  power balance, not a tank sizer and not a nozzle hardware sizer.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hydrazine_monopropellant_thruster.py

The test covers the worked-example contract (products, heat release,
decomposition temperature 1377.055 K at x = 0.4 and 1201.560 K at x = 0.6,
mixture gas constant, isentropic exponent, exhaust velocity 2795.808 m/s,
vacuum specific impulse 285.093 s, mass flow 0.0017884 kg/s at 5 N), the
mass-closure and mole-sum identities, the monotone seven-point dissociation
sweep, the Hess-law energy-balance residual closure, the term-by-term
exhaust-velocity identity, the band-verdict semantics at the worked points
and closed boundaries, determinism, the 12-function public API with no
sibling-leaf outputs, and ValueError rejection of non-physical
dissociation fractions, temperatures, gravity and thrust values. The suite
passes identically under /usr/bin/python3 and the pyenv 3.13.12
interpreter (no exact-float equality asserts on computed sums).

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35 is a free ESA
  download (ecss.nl/standards); the hydrazine decomposition relations above
  are standard engineering methodology with published reference data,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

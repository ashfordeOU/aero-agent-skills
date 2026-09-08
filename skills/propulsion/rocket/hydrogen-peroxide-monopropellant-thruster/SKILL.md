---
name: hydrogen-peroxide-monopropellant-thruster
description: "Use when you must size and assess a hydrogen peroxide monopropellant thruster for spacecraft reaction control: compute the decomposition heat release of H2O2 at a documented concentration with the water dilution, the adiabatic decomposition temperature from the peroxide decomposition energy balance, and the frozen composition isentropic nozzle expansion of the steam-oxygen product mixture to the vacuum exhaust velocity, the vacuum specific impulse and the propellant mass flow at the required thrust, with the advisory silver-catalyst-bed band check. Produces the steam-oxygen mixture composition and mass fractions, decomposition temperature, mixture gas constant, isentropic exponent, exhaust velocity, vacuum specific impulse, propellant mass flow and the silver-catalyst-bed band verdict that size a monopropellant RCS thruster. Trigger: hydrogen-peroxide-monopropellant-thruster, peroxide-decomposition, steam-oxygen-mixture, silver-catalyst-bed, concentration-limited-decomposition."
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
  tags: [hydrogen-peroxide-monopropellant-thruster, peroxide-decomposition, steam-oxygen-mixture, silver-catalyst-bed, concentration-limited-decomposition]
  version: 0.1.0
  author: AeroSkills
---

# Hydrogen Peroxide Monopropellant Thruster (propulsion/rocket/hydrogen-peroxide-monopropellant-thruster)

Use when the task is sizing and assessing a hydrogen peroxide monopropellant
thruster for spacecraft reaction control: high-test hydrogen peroxide (HTP)
decomposes catalytically over a silver catalyst bed and the hot steam-oxygen
product gas expands through a nozzle to produce a small thrust for attitude
control. This leaf implements the peroxide station model in pure Python,
stdlib only: the decomposition products and the net decomposition heat
release at a documented peroxide concentration w with the water dilution,
the adiabatic decomposition (chamber) temperature from the Hess-law energy
balance, and the frozen-composition isentropic expansion of the
steam-oxygen product mixture to the vacuum exhaust velocity, the vacuum
specific impulse and the propellant mass flow at the thrust point, plus an
advisory silver-catalyst-bed band verdict. It pairs with
propulsion/rocket/hydrazine-monopropellant-thruster as the other catalytic
station model in the pack and with propulsion/rocket/rocket-engine-cycle
for the feed system that supplies the peroxide. The boundary is strict:
this leaf is the decomposition station math, not a feed cycle model, not a
nozzle hardware sizer, not a tank sizer and not an attitude control law.

## Domain quick reference

- Decomposition: 2 H2O2(l) -> 2 H2O(g) + O2(g), exothermic. At peroxide mass
  concentration w (H2O2 fraction in water), the dilution water carried in
  the feed vaporizes into the products: n_w = (1-w)/w * M_H2O2/M_H2O moles
  of liquid dilution water per mole of H2O2 fed; products n_h2o = 1 + n_w
  and n_o2 = 0.5, total moles n_tot = 1.5 + n_w. Product mass closes on the
  feed mass at every w.
- Net heat release (Hess-law balance at 298.15 K, products all vapor):
  Q(w) = Q_BASE - n_w * DELTA_H_VAP_H2O_298, with Q_BASE = 54046.4 J/mol the
  gas-product decomposition release. Linear and strictly increasing in w:
  44814.925553 J/mol at w = 0.90, 54046.4 J/mol (Q_BASE exactly) at w = 1.0.
- Heat capacities: quadratic fits cp(T) = a + bT + cT^2 in J/(mol K) through
  reference points (298.15, 1000, 2000 K): H2O(g) (33.59, 41.27, 51.20),
  O2(g) (29.38, 34.86, 37.75).
- Adiabatic decomposition temperature T_c: the root of product sensible
  heat from T_REF to T_c equaling Q(w), where the sensible heat integrates
  the mixture heat capacity; the monotone left side makes the bisection on
  [298.15, 2600] K close the unique root.
- Mixture gas: M_mix = feed mass per mole H2O2 / n_tot, R_mix =
  8314.462618 / M_mix J/(kg K), and the isentropic exponent gamma =
  cp_mix / (cp_mix - R_univ) with cp_mix the mole-fraction-weighted frozen
  mixture heat capacity, evaluated at the chamber state.
- Vacuum expansion (fully expanded, p_e = 0): v_e = sqrt(2 gamma/(gamma -
  1) R_mix T_c), vacuum specific impulse Isp = v_e / g0 with g0 = 9.80665
  m/s^2, and propellant mass flow at the thrust point mdot = F / v_e (the
  vacuum thrust F = mdot * v_e carries no exit-pressure term).
- Concentration domain (documented, enforced): w in [0.85, 1.0], the
  published silver-catalyst HTP monopropellant service range (85 to 98
  percent by weight); below 0.85 the dilution-water vaporization load
  dominates the release and the model refuses.
- Silver-catalyst-bed operating band (reference-only, advisory): 823.15 to
  1234.93 K (550 C to the 961.78 C silver melting point), published
  reference data, never enforced.
- Units are SI throughout: K, J/mol, g/mol, J/(kg K), m/s, s, N, kg/s.
- ECSS frames the spacecraft propulsion context; the relations above are
  standard engineering methodology, summary-only.

## Workflow

1. Fix the duty point: the required vacuum thrust F in N and the peroxide
   concentration w in [0.85, 1.0] (the water dilution).
2. Decompose: dilution_water_moles(w) gives the dilution water,
   product_mole_numbers(w) the steam-oxygen product moles and
   total_product_moles(w) the mixture total.
3. Energy release: decomposition_heat_released(w) gives the net
   decomposition heat release at the reference state, J per mole H2O2 fed.
4. Chamber temperature: decomposition_temperature(w) solves the peroxide
   decomposition energy balance by bisection for the adiabatic
   decomposition temperature T_c in K; product_heat_capacity(w, t_k) and
   product_sensible_heat(w, t_k) sample the mixture heat capacity and
   sensible heat at any temperature.
5. Composition: product_mole_fractions(w) and product_mass_fractions(w)
   give the steam-oxygen mixture composition.
6. Mixture gas: mixture_molar_mass(w), mixture_gas_constant(w), and
   mixture_gamma(w, T_c) give the frozen-composition isentropic exponent at
   the chamber state.
7. Expand to vacuum: vacuum_exhaust_velocity(w) gives v_e, then
   vacuum_specific_impulse(w, g0) the vacuum specific impulse and
   propellant_mass_flow(F, w) the peroxide flow at the thrust point.
8. Advisory check: within_silver_catalyst_bed_band(T_c) reports whether the
   decomposition temperature sits inside the documented silver-catalyst-bed
   band.
9. Confirm the deterministic checks and the domain guards with the contract
   test scripts/test_hydrogen_peroxide_monopropellant_thruster.py.

## Worked example

A 1 N RCS thruster at peroxide concentration w = 0.90, the same design at
22 N, and the query-2 concentration-limit points at w = 0.85 and w = 0.98.

- 1 N point, w = 0.90: per mole of H2O2 fed, dilution water n_w =
  0.209789072881 mol; products 1.209789072881 mol H2O + 0.5 mol O2
  (n_tot = 1.709789072881 mol; mole fractions 0.707566267717 H2O and
  0.292433732283 O2; mass fractions 0.576669249865 H2O and 0.423330750135
  O2); net heat release Q = 44814.925553 J/mol; mixture molar mass
  22.1045329441 g/mol with R_mix = 376.1428770760 J/(kg K); decomposition
  temperature T_c = 1024.2354582656 K; gamma at the chamber state
  1.2656230167; vacuum exhaust velocity v_e = 1916.0668272739 m/s; vacuum
  specific impulse Isp = 195.3844408920 s; propellant mass flow at 1 N
  mdot = 0.000521902465 kg/s (0.521902465 g/s); silver-catalyst-bed band
  verdict True.
- 22 N point, w = 0.90: identical station numbers (n_w, products, Q, M_mix,
  R_mix, T_c, gamma, v_e, Isp, verdict), with propellant mass flow
  mdot = 22 / 1916.0668272739 = 0.011481854227 kg/s (11.481854227 g/s).
- Concentration-limit points at 22 N: w = 0.85 gives T_c = 901.7013222428 K,
  v_e = 1785.8078417405 m/s, Isp = 182.1017209486 s and mdot =
  0.012319354572 kg/s, verdict True; w = 0.98 gives T_c = 1221.3719212069 K,
  v_e = 2109.8144943685 m/s, Isp = 215.1412046283 s and mdot =
  0.010427457039 kg/s, verdict True. The 98 percent point leaves about
  13.6 K of margin below the silver melting ceiling.
- Pure-peroxide heating-only bound, w = 1.0: no dilution water; Q(1.0) =
  54046.400000 J/mol equals Q_BASE exactly; T_c = 1271.0022500679 K,
  v_e = 2155.7580276312 m/s, Isp = 219.8261412033 s, and the band verdict
  is False (above the silver melting ceiling, which is why service
  concentration on silver beds is capped near 98 percent).
- Read-off: the 1 N duty needs 0.521902465 g/s of 90 percent HTP at an
  ideal vacuum Isp of 195.3844408920 s with a 1024.235 K decomposition
  temperature inside the reported silver-bed band; the sweep shows T_c and
  Isp rising monotonically from 901.7 K / 182.1 s at 85 percent to the
  pure-peroxide bound 1271.0 K / 219.8 s at 100 percent, with the chamber
  gamma falling mildly from 1.2745 to 1.2509 as the mixture dries. The
  ideal-model impulses sit at or above the published real-engine vacuum
  class of roughly 150 to 190 s because real thrusters carry nozzle
  efficiency and finite-expansion losses this leaf's fully expanded ideal
  vacuum form does not model; the published class stays reference-only.

## Verification

- Confirm dilution_water_moles(0.90) returns 0.209789072881,
  decomposition_heat_released(0.90) returns 44814.925553 J/mol and
  decomposition_temperature(0.90) returns 1024.2354582656 K.
- Confirm mixture_molar_mass(0.90) returns 22.1045329441 g/mol,
  mixture_gas_constant(0.90) returns 376.1428770760 J/(kg K), and
  mixture_gamma(0.90, 1024.2354582656) returns 1.2656230167.
- Confirm vacuum_exhaust_velocity(0.90) returns 1916.0668272739 m/s,
  vacuum_specific_impulse(0.90) returns 195.3844408920 s, and
  propellant_mass_flow(1.0, 0.90) returns 0.000521902465 kg/s.
- Confirm the product mass closes on the feed mass at every w (rel err at
  or below 2.047e-16), the sensible-heat residual at each solved T_c is
  below 1e-9 J, and decomposition_temperature(0.90) is bit-identical on
  repeated calls (deterministic, no RNG).
- Confirm every w outside [0.85, 1.0] or not finite, every non-positive
  sample temperature, g0 and thrust, and every non-finite band temperature
  raises ValueError, and that the endpoints T_c(0.85) = 901.701 K and
  T_c(1.0) = 1271.002 K plus the advisory band verdicts reproduce the
  published class without enforcing it.
- Run the contract test offline: python3
  scripts/test_hydrogen_peroxide_monopropellant_thruster.py (30 tests,
  deterministic).

## Related leaves

- propulsion/rocket/hydrazine-monopropellant-thruster: the other catalytic
  decomposition station in the pack, N2H4-specific end to end with a
  different energy balance and product mixture.
- propulsion/rocket/rocket-engine-cycle: the feed cycle that supplies the
  peroxide; its monopropellant row is a hydrazine feed-table entry only.
- propulsion/rocket/nozzle-design and the nozzle leaves: the expansion
  hardware, throat area solve and exit pressure terms this leaf does not
  do.
- propulsion/rocket/cold-gas-thruster: the inert gas RCS alternative, no
  catalytic chemistry.
- propulsion/electric/electrothermal-thruster: the electrically heated
  propellant alternative (NH3, N2, H2, He), a different energy source.
- propulsion/rocket/propellant-selection: the propellant-family
  classification that lists H2O2 as a storable bipropellant oxidizer, a
  different context from this decomposition station model.

## Pitfalls

- Solving for the peroxide concentration: w is a documented input, never
  solved; this model performs no chemical-equilibrium composition
  iteration.
- Treating the mixture as a constant-gamma gas: gamma is evaluated at the
  chamber state from the mole-fraction-weighted frozen composition heat
  capacity and falls mildly from 1.2745 (water-rich, w = 0.85) to 1.2509
  (pure peroxide, w = 1.0).
- Adding an exit-pressure thrust term: the exhaust velocity here is the
  fully expanded vacuum form of the decomposed steam-oxygen gas only;
  nozzle sizing, area ratio and any (Pe - Pa) * Ae term belong to the
  nozzle leaves.
- Quoting the ideal impulse as a real engine performance: real thrusters
  run near 150 to 190 s vacuum because of nozzle efficiency and
  finite-expansion losses; the ideal frozen values (182 to 220 s across w)
  are the loss-free account and the published class stays reference-only.
- Treating the silver-catalyst-bed band as an enforced limit: the band
  verdict is an advisory boolean report; the pure-peroxide point at
  1271.002 K sits above the reported silver melting ceiling, which is
  exactly why service concentration on silver beds is capped near 98
  percent.
- Using the model beyond its boundary: this leaf is the peroxide
  decomposition station model, not a feed-cycle power balance, not a tank
  sizer and not a nozzle hardware sizer.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_hydrogen_peroxide_monopropellant_thruster.py

The test covers the worked-example contract (dilution, products, heat
release, decomposition temperature 1024.235 K at w = 0.90 and 901.701 K at
w = 0.85, mixture gas constant, isentropic exponent, exhaust velocity
1916.067 m/s, vacuum specific impulse 195.384 s, mass flow 0.000521902 kg/s
at 1 N), the mass-closure and mole/mass-fraction-sum identities, the
monotone five-point concentration sweep, the Hess-law energy-balance
residual closure, the term-by-term exhaust-velocity identity and the
finite-pressure isentropic form against the vacuum limit, the frozen
mass-flow linearity, the band-verdict semantics at the worked points and
closed boundaries, determinism, the 16-function public API with no
sibling-leaf outputs, and ValueError rejection of non-physical
concentrations, temperatures, gravity and thrust values. The suite passes
under the stdlib-only interpreter with no exact-float equality asserts on
computed sums.

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-35 is a free ESA
  download (ecss.nl/standards); the peroxide decomposition relations above
  are standard engineering methodology with published reference data,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

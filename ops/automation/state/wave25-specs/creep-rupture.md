# Wave-25 leaf spec: creep-rupture (structures, materials pack)

- Path: skills/structures/materials/creep-rupture/
- Pack: materials (existing siblings: mmpsd-allowables, fracture-
  toughness, material-selection, ramberg-osgood)
- Standards ids: mmpsd, far-25  (Ledger Standard: mmpsd, far-25)
- Family: structures

## Claim

Assess high-temperature creep and rupture life of aerospace metallic
materials with the classic parametric methods: compute the steady-state
creep strain rate with the Norton power law, estimate the rupture life
with the Larson-Miller parameter from the stress and temperature, fit or
apply the Monkman-Grant relation between the creep rate and the rupture
life, compute the creep strain accumulated over a service time, and
check the creep strain and rupture life against the design allowables
with the margin of safety. Produces the creep rate, the rupture life,
the accumulated creep strain, and the margin verdict for the elevated
temperature component.

Does NOT do: fatigue life under cyclic loading (fatigue pack leaves:
stress-life, strain-life, miner-damage, goodman-diagram own cyclic
methods), thermal stress from constrained expansion (thermal-stress-
analysis owns alpha*dT and thermal buckling), room-temperature tensile
design allowables (mmpsd-allowables), elastic-plastic stress strain
curves (ramberg-osgood). This leaf is the time-dependent creep and
stress rupture method.

## Model (implement exactly)

- Norton steady creep rate: eps_dot_c = A * sigma^n * exp(-Q/(R*T))
  where A (1/s per Pa^n), n (stress exponent), Q (activation energy
  J/mol), R = 8.314 J/mol/K, T in K. Provide module constants for a
  representative aerospace material (e.g. a nickel superalloy or
  titanium at elevated temperature; state reference-only typicals, e.g.
  Ti-6Al-4V ~ 300 C or Inconel 718 ~ 650 C with internally consistent
  A, n, Q that make clean test numbers). Allow user input of all four
  constants with the module defaults as the representative alloy.
- Larson-Miller parameter: LMP = T * (C + log10(t_r)) where t_r is the
  rupture life (hours), T in K (or R; state the unit convention), C a
  material constant (~20 typical). Provide the stress-LMP master curve
  as a module function lmp_from_stress(sigma) (e.g. linear in log10
  sigma with material constants: LMP = a - b*log10(sigma)); then
  rupture_life(sigma, T) from the LMP. Allow direct input of the master
  curve constants with module defaults.
- Monkman-Grant: log10(t_r) + m * log10(eps_dot_min) = C_mg with m, C_mg
  material constants; compute the rupture life from the minimum creep
  rate and compare with the LMP estimate.
- Accumulated creep strain over time: eps_c(t) = eps_dot_c * t
  (steady-state only; state the assumption; optionally include the
  primary strain as a module constant fraction or ignore with the
  documented assumption).
- Design check: the time to 1% creep strain t_1pct = 0.01/eps_dot_c and
  the rupture life at the operating stress and temperature; margins:
  margin_rupture = t_r / t_required - 1; margin_creep = t_1pct /
  t_required - 1; report both and the governing (lower) margin.
Functions:
- norton_creep_rate(sigma, temp_k, material) -> 1/s
- larson_miller_parameter(sigma, material) -> LMP
- rupture_life_hours(sigma, temp_k, material) -> hours
- rupture_life_from_lmp(lmp, temp_k, c_const) -> hours
- monkman_grant_life(eps_dot_min, material) -> hours
- creep_strain_accumulated(eps_dot, time_s) -> -
- time_to_creep_strain(target_strain, eps_dot) -> s
- creep_margin(time_required_s, sigma, temp_k, material) -> dict
  (rupture life, t_1pct, margin_rupture, margin_creep, verdict)
ValueError on: non-positive stress/temperature/time, unknown material,
n < 0, sigma <= 0, temp <= 0.

## Worked example

Representative alloy at elevated temperature (your module constants):
- sigma = 300 MPa, T = 600 C (873 K): compute the Norton creep rate,
  the LMP, the rupture life in hours, and the time to 1% strain. Assert
  the real numbers from your module.
- Monotonicity: rupture life falls as stress rises (assert over 5
  points); creep rate rises with stress and temperature.
- Margin check: with a 1000 h required life, report both margins and the
  governing verdict.
- ValueErrors.
Keep at least 18 test methods.

## Corpus tasks (ids w25-creep-rupture-1/2)

Distinctive tokens: creep, creep rate, Norton law, Larson-Miller,
rupture life, stress rupture, Monkman-Grant, accumulated creep strain,
time to 1 percent creep, elevated temperature. Avoid: S-N curve, fatigue
life, thermal expansion, alpha dT, tensile allowable, A basis (owned by
fatigue/thermal/mmpsd siblings).

1. "estimate the rupture life of the turbine disk material at 650 C and
   300 MPa with the Larson-Miller parameter and check the 1000 hour
   design life margin"
2. "compute the Norton steady state creep rate and the accumulated creep
   strain over the service time at the elevated temperature operating
   point"

## SKILL body notes

Pair with ramberg-osgood (elastic-plastic stress strain), fracture-
toughness, material-selection (temperature limits), thermal-stress-
analysis. Worked example uses module constants and real outputs.
Compliance: MMPDS creep/rupture design practice referenced by name;
material constants are reference-only typicals, no reproduced tables.

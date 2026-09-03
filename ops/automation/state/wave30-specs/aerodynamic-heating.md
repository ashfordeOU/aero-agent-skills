# Wave-30 leaf spec: aerodynamic-heating (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/aerodynamic-heating/
- Pack: high-speed (siblings: hypersonic-flow, normal-shock, oblique-shock,
  prandtl-meyer, shock-expansion-airfoil, supercritical-airfoil,
  swept-wing-aerodynamics, transonic-similarity, wave-drag-area-rule).
- Standards ids: naca-tr-824 (reference-only; aerodynamics family convention).
  Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Claim

Estimate the aerodynamic heating at the stagnation point of a hypersonic
body: compute the stagnation-point convective heat flux with the Sutton-Graves
correlation from freestream density, flight velocity, and nose radius, convert
the flux to a radiation-equilibrium wall temperature with the Stefan-Boltzmann
balance at a chosen surface emissivity, and scale the flux with nose radius to
compare blunt and sharp geometries. Produces the stagnation heat flux, the
radiation-equilibrium temperature, and the bluntness trade that gate a thermal
protection material choice.

Does NOT do: compute hypersonic shock shapes, pressures, or forces with
modified Newtonian theory (hypersonic-flow owns Rayleigh pitot, Newtonian
impact theory); model shock waves or expansion fans (normal-shock,
oblique-shock, prandtl-meyer, shock-expansion-airfoil own those); analyze
conductive thermal stress in a structure (structures thermal-stress-analysis
owns mechanical thermal stress); size entry trajectories or heat loads for a
spacecraft mission (space-systems entry-descent-landing owns the entry
corridor and ballistic coefficient); compute radiation heating of the gas or
ablator response chemistry. Correlation-level convective heating at the
stagnation point only.

## Model (implement exactly)

Module constants:
- C_SG = 1.83e-4 (Sutton-Graves correlation constant for air, SI units
  arranged so q = C_SG * sqrt(rho / R_n) * V**3 gives W/m2).
- SIGMA_SB = 5.670374419e-8 (W/m2/K4).
- EPSILON_DEFAULT = 0.85 (typical TPS surface emissivity).

Functions (pure stdlib):
- stagnation_heat_flux(rho, velocity, nose_radius, c_sg=C_SG) -> float:
  q_s = c_sg * sqrt(rho / nose_radius) * velocity**3. ValueError if rho <= 0,
  velocity <= 0, nose_radius <= 0.
- radiation_equilibrium_temp(heat_flux, emissivity=EPSILON_DEFAULT,
  sigma=SIGMA_SB) -> float: T_w = (heat_flux / (emissivity * sigma))**0.25.
  ValueError if heat_flux < 0, emissivity <= 0 or > 1.
- radius_scaling(heat_flux_reference, radius_reference, radius_new) -> float:
  q_new = heat_flux_reference * sqrt(radius_reference / radius_new)
  (sqrt(1/R_n) scaling). ValueError if any argument <= 0.
- heating_assessment(rho, velocity, nose_radius, emissivity=EPSILON_DEFAULT)
  -> dict: {heat_flux_W_m2, radiation_temp_K, flux_doubled_nose_radius
  (same rho, V, radius*2 flux), flux_halved_nose_radius (radius/2)}. ValueErrors
  propagate.

## Worked example

Heating peak: rho = 0.001 kg/m3, V = 7200 m/s, R_n = 0.5 m, emissivity 0.85.

Deterministic anchors (module outputs as assert targets to 4 s.f. plus bounds):
- heat flux in 2.5e6-4.0e6 W/m2 (hand estimate ~3.1e6 W/m2).
- radiation equilibrium temperature in 2600-3100 K (hand estimate ~2800 K).
- R_n doubled (1.0 m) flux = reference / sqrt(2) within 1e-9 relative (exact
  identity: sqrt(0.5/1.0) = 0.7071...).
- R_n halved (0.25 m) flux = reference * sqrt(2) within 1e-9 relative.
- Monotonicity: q increases with V (test two velocities) and with rho.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: rho/velocity/nose_radius <= 0; emissivity <= 0 or > 1;
  heat_flux < 0.
- Exact radius-scaling identities above.
- Bounds above.
- Determinism (no RNG).

## Corpus fragment (eval/hit1-wave30-aerodynamic-heating.yaml)

Forbidden tokens (siblings): newtonian, pitot, shock, prandtl-meyer, wave
drag, area rule, supercritical, sweep correction (all high-speed sibling
claims), thermal stress (structures), entry corridor (space EDL). Distinctive
tokens ONLY: aerodynamic-heating, stagnation-point-heating, sutton-graves,
radiation-equilibrium-temperature, nose-radius.

Query 1: "Estimate stagnation-point-heating on a reentry body with the
sutton-graves correlation at rho 0.001 kg/m3 and 7200 m/s with a 0.5 m
nose-radius" (id w30-aerodynamic-heating-1).
Query 2: "Compute the radiation-equilibrium-temperature of a TPS surface for
an aerodynamic-heating heat flux of 3 MW/m2 at emissivity 0.85" (id
w30-aerodynamic-heating-2).
intent: "aerodynamics; hypersonic stagnation heating correlation".

## Description/tag guidance

Description opens "Use when you must estimate the aerodynamic heating at the
stagnation point of a hypersonic body:" and lists the outputs in the Claim.
First tag: aerodynamic-heating. Additional tags: stagnation-point-heating,
sutton-graves, radiation-equilibrium-temperature, nose-radius-bluntness.
No generic single words. 50-150 words, <=1000 chars, no em dash, no
"classified".

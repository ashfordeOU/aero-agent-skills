---
name: aerodynamic-heating
description: "Use when you must estimate the aerodynamic heating at the stagnation point of a hypersonic body: stagnation-point convective heat flux from the Sutton-Graves correlation using freestream density, flight velocity and nose radius, radiation-equilibrium wall temperature from the Stefan-Boltzmann balance at a chosen surface emissivity, and the nose-radius bluntness trade that scales the flux for blunt versus sharp geometries. Produces the stagnation heat flux, the radiation-equilibrium temperature and the bluntness comparison that gate a thermal protection material choice. Trigger: aerodynamic heating, stagnation-point-heating, sutton-graves, radiation-equilibrium-temperature, nose-radius-bluntness, reentry heating, thermal protection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: aerodynamics
pack: high-speed
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: aerodynamics
  subdomain: high-speed
  tags: [aerodynamic-heating, stagnation-point-heating, sutton-graves, radiation-equilibrium-temperature, nose-radius-bluntness]
  version: 0.1.0
  author: AeroSkills
---

# Aerodynamic Heating (aerodynamics/high-speed/aerodynamic-heating)

Use when you must estimate the aerodynamic heating at the stagnation point
of a hypersonic body: correlation-level convective heating from the
Sutton-Graves model, the radiation-equilibrium wall temperature it implies,
and the nose-radius bluntness trade that drives thermal protection material
selection. This leaf implements the Sutton-Graves stagnation-point
correlation and the Stefan-Boltzmann radiation balance in pure Python,
stdlib only, for flight at a fixed point (constant freestream density and
velocity). It pairs with aerodynamics/high-speed/hypersonic-flow for the
hypersonic flight environment context and with
structures/thermal-structures/thermal-stress-analysis when the wall
temperature feeds a structural thermal analysis.

## Domain quick reference

- Sutton-Graves stagnation heat flux: q_s = C_SG * sqrt(rho / R_n) * V**3,
  with C_SG = 1.83e-4 (air correlation constant, SI units arranged so q_s
  is in W/m2), rho the freestream density in kg/m3, R_n the nose radius in
  m and V the flight velocity in m/s. The correlation captures the
  convective heating of the thin shock layer ahead of a blunt body at
  hypersonic speed.
- Radiation-equilibrium wall temperature: T_w = (q / (eps * sigma))**0.25,
  from the steady balance q = eps * sigma * T_w**4 with sigma =
  5.670374419e-8 W/m2/K4 (Stefan-Boltzmann) and eps the surface
  emissivity, default 0.85 for typical thermal protection surfaces.
- Nose-radius scaling: q scales as sqrt(1 / R_n) at fixed rho and V, so
  doubling the nose radius divides the flux by sqrt(2) (factor 0.7071)
  and halving it multiplies the flux by sqrt(2) (factor 1.4142). Blunter
  bodies run cooler at the stagnation point.
- Scaling laws at fixed radius: q grows with V**3 and with sqrt(rho), so
  the peak heating on a reentry trajectory sits at the point where the
  density-velocity product is largest, not at peak velocity.
- Units are SI throughout: W/m2, K, kg/m3, m/s, m.
- NACA TR-824 frames the compressible-flow context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Fix the flight point: freestream density rho (kg/m3), velocity V (m/s)
   and nose radius R_n (m).
2. Compute the stagnation heat flux with stagnation_heat_flux(rho, V,
   R_n); the module constant C_SG applies by default.
3. Convert the flux to a wall temperature with
   radiation_equilibrium_temp(heat_flux, emissivity); supply the surface
   emissivity or accept EPSILON_DEFAULT = 0.85.
4. Trade nose bluntness with radius_scaling(flux_ref, R_ref, R_new): the
   flux at the new nose radius at the same rho and V.
5. Run the full assessment with heating_assessment(rho, V, R_n,
   emissivity): it returns the flux, the temperature and the fluxes at
   doubled and halved nose radius in one dict.
6. Judge the thermal protection implication: a wall temperature near or
   above the material limit motivates a blunter nose or a higher
   emissivity coating.
7. Confirm the deterministic checks with the contract test
   scripts/test_aerodynamic_heating.py.

## Worked example

Heating peak on a reentry body: rho = 0.001 kg/m3, V = 7200 m/s, R_n =
0.5 m, emissivity 0.85.

- Stagnation heat flux: q_s = 1.83e-4 * sqrt(0.001 / 0.5) * 7200**3 =
  3.0547e6 W/m2 (spec bound 2.5e6 to 4.0e6 W/m2; hand estimate ~3.1e6).
- Radiation-equilibrium temperature: T_w = (3.0547e6 / (0.85 *
  5.670374419e-8))**0.25 = 2821.5 K (spec bound 2600 to 3100 K; hand
  estimate ~2800 K). This exceeds the usable range of most metallic
  thermal protection, pointing to an ablator or ceramic tile class.
- Bluntness trade at the same rho and V: R_n = 1.0 m gives 2.1600e6 W/m2,
  exactly the reference flux divided by sqrt(2); R_n = 0.25 m gives
  4.3199e6 W/m2, exactly the reference flux times sqrt(2). Halving the
  nose radius raises the flux by about 41% and the wall temperature
  toward 3000 K.

## Verification

- stagnation_heat_flux raises ValueError when rho, velocity or
  nose_radius is not positive; radiation_equilibrium_temp raises
  ValueError for negative heat flux and for emissivity outside (0, 1];
  radius_scaling raises ValueError for any non-positive argument;
  heating_assessment propagates those errors.
- Exact scaling identities hold to machine precision: doubling R_n gives
  flux_ref / sqrt(2), halving gives flux_ref * sqrt(2); radius_scaling
  matches a direct Sutton-Graves evaluation at the new radius.
- Worked example outputs fall inside the spec magnitude bounds: flux in
  2.5e6 to 4.0e6 W/m2 and temperature in 2600 to 3100 K.
- Monotonicity: the flux increases with velocity (V**3 law) and with
  density (sqrt law), and decreases as the nose radius grows.
- Radiation round trip: eps * sigma * T_w**4 recovers the input heat
  flux; all results are deterministic (no RNG).
- Run the contract test offline: python3
  scripts/test_aerodynamic_heating.py (33 tests, deterministic).

## Related leaves

- aerodynamics/high-speed/hypersonic-flow: the hypersonic flight
  environment, Rayleigh pitot pressure and Newtonian impact theory.
- aerodynamics/high-speed/normal-shock and
  aerodynamics/high-speed/oblique-shock: the flowfield jumps that set
  the post-shock conditions ahead of the heating estimate.
- aerodynamics/high-speed/prandtl-meyer and
  aerodynamics/high-speed/shock-expansion-airfoil: expansion fan and
  surface pressure models on the cold side of the energy balance.
- structures/thermal-structures/thermal-stress-analysis: the wall
  temperature from this leaf as a load for mechanical thermal stress.

## Pitfalls

- Searching for peak heating at peak velocity: q grows as V**3 but only
  as sqrt(rho), so the worst point on a reentry trajectory is where the
  density-velocity product is largest, not the fastest point.
- Expecting the wall temperature to fall as fast as the flux: doubling
  the nose radius divides the flux by sqrt(2), but T_w scales as the
  fourth root, so the temperature drop is far smaller than the flux
  drop.
- Trading nose radius across different flight states: radius_scaling is
  only valid at fixed rho and V; re-run the full assessment when the
  flight point changes.
- Judging thermal protection from flux alone: in the worked example the
  2821 K radiation-equilibrium temperature, not the 3.05e6 W/m2 flux,
  is what exceeds metallic limits and forces an ablator or ceramic tile
  class.
- Passing emissivity at the boundary: emissivity must lie in (0, 1];
  zero or negative emissivity raises ValueError, as do non-positive
  density, velocity, radius and heat flux.
- Forgetting the correlation's scope: Sutton-Graves is a
  stagnation-point, blunt-body, thin-shock-layer estimate; it is not a
  general surface-heating method for sharp or three-dimensional
  geometries away from the stagnation point.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_aerodynamic_heating.py

The test covers the worked-example magnitude bounds (flux 2.5e6 to
4.0e6 W/m2, temperature 2600 to 3100 K), the Sutton-Graves flux value and
its V**3 and sqrt(rho) scaling laws, the exact sqrt(1/R_n) radius-scaling
identities and the direct correlation cross-check, the
radiation-equilibrium round trip and emissivity dependence, assessment
dict consistency, determinism, and ValueError rejection of every
non-physical input (non-positive density, velocity, radius, heat flux and
emissivity outside (0, 1]).

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named as the
  compressible-flow context standard; the Sutton-Graves correlation and
  Stefan-Boltzmann balance above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

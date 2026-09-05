---
name: flat-plate-skin-friction-heating
description: "Use when you must estimate the surface skin friction heating on a flat plate or vehicle skin at high Mach: it computes the recovery factor, adiabatic wall temperature, Eckert reference temperature, Sutherland viscosity, local skin friction coefficient and Reynolds-analogy heat transfer coefficient, then the cold-wall heat flux for a laminar or turbulent boundary layer. Produces the non-stagnation heating report with r, T_aw, T_star, Re_star, Cf, h_c and q_cold_wall in SI units for a thermal protection check. Trigger: recovery-factor, adiabatic-wall-temperature, cold-wall-heat-flux, reference-temperature-method, reynolds-analogy-factor, skin-friction-coefficient, turbulent-plate-heating, flat-plate-heating."
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
  tags: [flat-plate-skin-friction-heating, recovery-factor, adiabatic-wall-temperature, cold-wall-heat-flux, reference-temperature-method, reynolds-analogy-factor, non-stagnation-heating]
  version: 0.1.0
  author: AeroSkills
---

# Flat Plate Skin Friction Heating (aerodynamics/high-speed/flat-plate-skin-friction-heating)

Use when the task is estimating the convective skin friction heating on
a flat plate or vehicle skin away from the leading edge at high Mach:
recovery factor, adiabatic wall temperature, Eckert reference
temperature, Sutherland viscosity, local skin friction coefficient and
cold-wall heat flux for laminar or turbulent boundary layers. This leaf
implements the classical compressible boundary-layer model in pure
Python, stdlib only, with the module constants from the leaf spec
(GAMMA = 1.4, R = 287.0, CP = 1005.0, PR = 0.71, MU_REF = 1.716e-5,
T_REF = 273.15, SUTH_S = 110.4). It pairs with
aerodynamics/high-speed/aerodynamic-heating for the leading-edge
counterpart and with the inviscid shock leaves for the flow-field
context around the boundary layer.

## Domain quick reference

- Recovery factor: laminar r = sqrt(PR) about 0.8426, turbulent
  r = PR**(1/3) about 0.8921 for air. The factor converts kinetic
  heating into the driving temperature for heat transfer.
- Adiabatic wall temperature: T_aw = T_inf * (1 + r * (GAMMA - 1) / 2 *
  M**2). This is the wall temperature at which the net convective flux
  is zero; it is the correct reference for the flux, not T_inf.
- Eckert reference temperature: T_star = T_inf * (1 + 0.032 * M**2 +
  0.58 * (T_wall / T_inf - 1)), the compressibility-corrected
  temperature for evaluating the local properties.
- Sutherland viscosity: mu = MU_REF * (T / T_REF)**1.5 * (T_REF +
  SUTH_S) / (T + SUTH_S), Pa s.
- Edge velocity: U_e = M * sqrt(GAMMA * R * T_inf). Density at the
  reference state: rho_star = p_inf / (R * T_star).
- Reynolds number at the reference state: Re_star = rho_star * U_e * x
  / mu_star, with x the running length from the leading edge.
- Local skin friction: laminar Cf = 0.664 / sqrt(Re_star); turbulent
  Cf = 0.0592 / Re_star**0.2 (1/7-power law form).
- Heat transfer coefficient, Reynolds-analogy style:
  h_c = 0.5 * Cf * rho_star * U_e * CP, W/(m2 K).
- Cold-wall heat flux: q_cold_wall = h_c * (T_aw - T_wall), W/m2.
  Positive into a cold wall, negative when the wall is hotter than the
  adiabatic wall temperature (wall heating).
- Units are SI throughout: K, Pa, kg/m3, m/s, W/m2.
- NACA-TR-824 frames the classical boundary-layer context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Fix the flight point: Mach M, static temperature T_inf, static
   pressure p_inf, the running length x and the regime ("laminar" or
   "turbulent"). The model takes freestream or local edge conditions.
2. Choose the regime recovery factor with recovery_factor(regime) and
   confirm r against the PR powers (0.8426 laminar, 0.8921 turbulent).
3. Get the driving temperature: adiabatic_wall_temperature(M, T_inf,
   regime). At M = 0 this returns T_inf (zero-speed identity).
4. Compute the compressibility-corrected property state:
   reference_temperature(M, T_inf, T_wall) and
   sutherland_viscosity(T_star).
5. Evaluate the boundary layer: skin_friction_coefficient(M, T_inf,
   p_inf, T_wall, x, regime) returns the dict {T_star, rho_star,
   mu_star, Re_star, Cf} at the reference state.
6. Convert friction to heat transfer with
   heat_transfer_coefficient(cf, rho_star, u_e) using the
   Reynolds-analogy factor 0.5.
7. Report the heating: cold_wall_heat_flux(M, T_inf, p_inf, T_wall, x,
   regime) chains all of the above into {r, T_aw, T_star, Re_star, Cf,
   h_c, q_cold_wall}. Run it for both regimes when the transition
   location is unknown and take the envelope.
8. Confirm the deterministic checks with the contract test
   scripts/test_flat_plate_skin_friction_heating.py.

## Worked example

Mach 3 cruise point: M = 3.0, T_inf = 223.0 K, p_inf = 10000.0 Pa,
T_wall = 500.0 K (heated wall), x = 0.5 m.

- Turbulent: r = 0.89211, T_aw = 581.09 K, T_star = 447.88 K,
  rho_star = 0.077795 kg/m3, mu_star = 2.4753e-5 Pa s,
  Re_star = 1.4111e6, Cf = 0.003487, h_c = 122.40 W/(m2 K),
  q_cold_wall = 9925.7 W/m2.
- Laminar at the same point: r = 0.84261, T_aw = 561.23 K,
  Re_star = 1.4111e6 (identical T_star), Cf = 5.590e-4,
  h_c = 19.62 W/(m2 K), q_cold_wall = 1201.4 W/m2.
- The turbulent flux is about 8.3 times the laminar value at the same
  Reynolds number, so calling the regime wrong changes the thermal
  protection answer by an order of magnitude.
- At the adiabatic condition T_wall = T_aw = 581.09 K the flux returns
  to zero; raising the wall above T_aw (for example to 1200 K) makes
  q_cold_wall negative, which is wall heating back into the flow.

## Verification

- Confirm cold_wall_heat_flux(3.0, 223.0, 10000.0, 500.0, 0.5,
  "turbulent")["q_cold_wall"] = 9925.7 W/m2 and the laminar run gives
  1201.4 W/m2, each within 1 percent of the prep-verified anchors.
- Confirm recovery_factor("laminar") = 0.84261 and
  recovery_factor("turbulent") = 0.89211 match sqrt(PR) and PR**(1/3).
- Confirm adiabatic_wall_temperature(0.0, T_inf, regime) equals T_inf
  and that T_star lies between T_inf and T_wall for the heated-wall
  example.
- Confirm sutherland_viscosity(273.15) equals MU_REF within 1e-3
  relative.
- Confirm the sign flip: T_wall > T_aw gives negative q_cold_wall.
- Confirm every non-physical input raises ValueError: M <= 0 or >= 20
  (flight functions), T_inf <= 0, p_inf <= 0, x <= 0, T_wall <= 0, and
  any regime string other than "laminar" or "turbulent". The module
  admits M = 0 only inside adiabatic_wall_temperature so the zero-speed
  identity T_aw = T_inf is testable; every function that needs an edge
  velocity requires 0 < M < 20.
- Run the contract test offline: python3
  scripts/test_flat_plate_skin_friction_heating.py (34 tests,
  deterministic).

## Related leaves

- aerodynamics/high-speed/aerodynamic-heating: the leading-edge
  stagnation convective heating counterpart of this surface skin
  heating model.
- aerodynamics/high-speed/hypersonic-flow: the regime map that decides
  when real-gas and strong-shock effects matter for the edge state.
- aerodynamics/high-speed/normal-shock: post-shock conditions that
  provide the boundary-layer edge state behind a shock.
- aerodynamics/high-speed/oblique-shock: the inviscid flow turning that
  sets the edge Mach number for swept or wedge-type surfaces.
- aerodynamics/high-speed/shock-expansion-airfoil: edge conditions
  along an airfoil surface for panel-by-panel heating runs.

## Pitfalls

- Using the stagnation-point correlation for surface locations: the
  stagnation convective heating correlation peaks at the leading edge
  and is not valid down the surface; this leaf owns the non-stagnation
  skin heating with local edge conditions and running length x.
- Driving the flux with T_inf instead of T_aw: at M = 3 the recovery
  temperature is 581.09 K against 223.0 K static, so a flux computed
  from T_inf badly understates the driving potential (T_aw - T_wall).
- Calling the regime wrong: the turbulent flux is about 8.3 times the
  laminar value at the same Reynolds number in the worked example, so
  an assumed transition point changes the thermal protection margin by
  an order of magnitude.
- Evaluating properties at freestream instead of reference conditions:
  at M = 3 even a cold wall gives T_star above T_inf (244.9 K at a
  150 K wall), and density computed from T_inf overstates rho_star and
  the Reynolds number, shifting Cf.
- Mixing the recovery-factor powers: laminar uses sqrt(PR) (0.8426)
  and turbulent uses PR**(1/3) (0.8921); swapping them changes T_aw by
  almost 20 K in the example.
- Reading q_cold_wall as the structural heat load: it assumes the wall
  holds at T_wall; conduction through the skin and re-radiation to the
  surroundings rebalance it in a real thermal protection check.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_flat_plate_skin_friction_heating.py

The test covers the module constants, the recovery factor for both
regimes against the PR powers and its ValueError on bad regime strings,
the adiabatic wall temperature anchors and the M = 0 identity, the
Eckert reference temperature anchor with the between-static-and-wall
bound, the Sutherland law at the reference temperature, the worked
example anchors within 1 percent (Re_star 1.41e6, Cf 0.003487,
q_cold_wall 9926 W/m2 turbulent; q_cold_wall 1201 W/m2 and T_aw 561 K
laminar), the laminar Blasius closed form, the turbulent-over-laminar
Cf order, the Reynolds-number scaling with length, the wall-heating
sign flip, the zero-flux adiabatic wall round trip, the
Reynolds-analogy heat transfer coefficient, determinism of the full
chain, and ValueError rejection of every non-physical input class.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 provides the
  classical boundary-layer context for the skin friction and recovery
  factor correlations; the relations above are standard engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

# Wave-38 leaf spec: flat-plate-skin-friction-heating (aerodynamics, high-speed pack)

- Path: skills/aerodynamics/high-speed/flat-plate-skin-friction-heating/
- Pack: high-speed. Closest siblings: aerodynamic-heating (stagnation-
  point convective heating by the Sutton-Graves correlation, radiation-
  equilibrium wall temperature and nose bluntness - the STAGNATION point
  only; verified its SKILL.md has no recovery-factor, adiabatic-wall or
  cold-wall function), hypersonic-flow (regime map), normal-shock /
  oblique-shock / prandtl-meyer / shock-expansion-airfoil (inviscid shock
  machinery). Whole-tree grep: "recovery factor", "adiabatic wall
  temperature", "cold wall heat flux", "reference temperature method",
  "Reynolds analogy factor" = ZERO owning hits in any leaf (aerodynamic-
  heating matches only radiation-equilibrium wall temperature at the
  stagnation point; vehicle-design ice-protection-sizing uses total
  temperature for anti-ice flux credit; propulsion thrust-chamber-cooling
  and turbofan-off-design use engine-side cooling correlations). ZERO
  owners of the surface (non-stagnation) skin heating function. GENUINE
  AERO gap (fresh probe).
- Standards id: naca-tr-824 (reference-only; family spine - the classical
  boundary-layer skin-friction correlations and recovery-factor relations
  live in the NACA classical aero context). Ledger Standard: naca-tr-824.
- Family: aerodynamics

## Model (implement exactly)

Conventions: SI units (Pa, K, kg/m3, m/s, W/m2). Freestream or local
boundary-layer edge conditions: M (Mach), T_inf (static temperature, K),
p_inf (static pressure, Pa), T_wall (wall temperature, K), x (running
length from the leading edge, m), regime ("laminar" or "turbulent").

Module constants: GAMMA = 1.4, R = 287.0 J/(kg K), CP = 1005.0 J/(kg K),
PR = 0.71, MU_REF = 1.716e-5 Pa s, T_REF = 273.15 K, SUTH_S = 110.4 K.

Functions (pure stdlib):
- recovery_factor(regime) -> float: laminar sqrt(PR) (0.8426), turbulent
  PR**(1/3) (0.8921). ValueError: regime not in ("laminar","turbulent").
- adiabatic_wall_temperature(M, T_inf, regime) -> float:
  T_inf * (1 + r * (GAMMA - 1) / 2 * M**2).
- reference_temperature(M, T_inf, T_wall) -> float (Eckert reference
  temperature): T_inf * (1 + 0.032 * M**2 + 0.58 * (T_wall / T_inf - 1)).
- sutherland_viscosity(T) -> float: MU_REF * (T / T_REF)**1.5 *
  (T_REF + SUTH_S) / (T + SUTH_S).
- skin_friction_coefficient(M, T_inf, p_inf, T_wall, x, regime) -> dict
  {T_star, rho_star, mu_star, Re_star, Cf}: density rho_star =
  p_inf / (R * T_star), Re_star = rho_star * U_e * x / mu_star with
  U_e = M * sqrt(GAMMA * R * T_inf); laminar Cf = 0.664 / sqrt(Re_star),
  turbulent Cf = 0.0592 / Re_star**0.2.
- heat_transfer_coefficient(...) -> h_c = 0.5 * Cf * rho_star * U_e * CP
  (Reynolds-analogy style, factor 0.5).
- cold_wall_heat_flux(M, T_inf, p_inf, T_wall, x, regime) -> dict
  {r, T_aw, T_star, Re_star, Cf, h_c, q_cold_wall} with q_cold_wall =
  h_c * (T_aw - T_wall).
ValueErrors: M <= 0 or >= 20 guard, T_inf <= 0, p_inf <= 0, x <= 0,
T_wall <= 0.

Identity to test: recovery factor of air is between sqrt(PR) and
PR**(1/3); adiabatic wall temperature equals T_inf when M = 0; q_cold_wall
is positive when T_wall < T_aw and negative when T_wall > T_aw (wall
heating); turbulent Cf exceeds laminar Cf at the same Re (order check on a
few Re values).

## Worked example

Verified at prep: M = 3.0, T_inf = 223.0 K, p_inf = 10000.0 Pa,
T_wall = 500.0 K, x = 0.5 m, turbulent:
- r = 0.89211; T_aw = 581.09 K; T_star = 447.88 K; rho_star =
  0.077795 kg/m3; mu_star = 2.4753e-5 Pa s; Re_star = 1.4111e6;
  Cf = 0.003487; h_c = 122.40 W/(m2 K); q_cold_wall = 9925.7 W/m2.
- Laminar at the same conditions: r = 0.84261, T_aw = 561.23 K
  (computed from the formula), Re_star identical (same T_star), Cf =
  0.664 / sqrt(Re_star) = 5.590e-4, h_c = 19.62 W/(m2 K),
  q_cold_wall = 1201.4 W/m2.
Run your module and take the real outputs as assert targets; these are
prep-verified bounds from the closed-form correlations (independently
evaluated by the anchor script at prep).

## Validation list (contract test must include)

- recovery_factor for laminar and turbulent exactly matches the two
  constants; ValueError on a bad regime string.
- adiabatic_wall_temperature at M = 0 equals T_inf.
- Reference-temperature method: T_star between T_inf and T_wall for a
  heated wall in the example.
- Sutherland viscosity at 273.15 K equals MU_REF within 1e-3 relative.
- Worked-example anchor checks within 1 percent (Re_star 1.41e6, Cf
  0.00349, q 9926 W/m2 turbulent; q 1201 W/m2 laminar, T_aw 561 K
  laminar).
- Wall-heating sign flip: T_wall > T_aw gives negative q (wall heating).
- ValueErrors for non-physical inputs.
- Determinism.

## Corpus fragment (eval/hit1-wave38-flat-plate-skin-friction-heating.yaml)

Query 1 (copy verbatim):
  "compute the flat-plate adiabatic-wall-temperature and cold-wall-heat-flux with the recovery-factor and reference-temperature-method skin friction"
  intent: "aerodynamics; non-stagnation surface convective heating on a flat plate"
  expected_skill: "aerodynamics/high-speed/flat-plate-skin-friction-heating"
Query 2 (copy verbatim):
  "estimate the turbulent flat-plate skin-friction-heating away from the stagnation point at mach 3 for a thermal protection check"
  intent: "aerodynamics; turbulent flat plate skin heating with recovery factor"
  expected_skill: "aerodynamics/high-speed/flat-plate-skin-friction-heating"
Task ids: w38-flat-plate-skin-friction-heating-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the surface skin
friction heating on a flat plate or vehicle skin:" and include the outputs
in the Claim. First tag: flat-plate-skin-friction-heating. Additional tags
ONLY: recovery-factor, adiabatic-wall-temperature, cold-wall-heat-flux,
reference-temperature-method, reynolds-analogy-factor, non-stagnation-
heating. NEVER single generic words (heating, heat, plate, skin,
temperature, flux, wall). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): stagnation point, Sutton-Graves,
nose radius, radiation-equilibrium (aerodynamic-heating); shock relations,
Mach wave, Prandtl-Meyer (normal-shock / oblique-shock / prandtl-meyer);
anti-ice flux credit, catch efficiency (vehicle-design ice-protection-
sizing).

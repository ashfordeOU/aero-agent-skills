# Wave-30 leaf spec: thermal-buckling (structures, thermal-structures pack)

- Path: skills/structures/thermal-structures/thermal-buckling/
- Pack: thermal-structures (sibling: thermal-stress-analysis only).
- Standards ids: far-25 (reference-only). Ledger Standard: far-25.
- Family: structures

## Claim

Compute the thermal buckling of restrained aerospace structure from a
temperature rise: the elastic buckling stress of a flat plate under uniform
compression, the in-plane thermal compressive stress from a constrained
temperature change (uniaxial and biaxial restraint), the critical temperature
rise that drives a skin panel to its buckling stress, and the critical
temperature rise of an Euler column between rigid supports. Produces the
buckling stress, thermal stress at a given temperature rise, critical
temperature rise, and the margin that gate a thermal-stability check of a
hot structure.

Does NOT do: compute thermal stress and free thermal strain of a fully
constrained or bimetallic member without buckling (thermal-stress-analysis
owns constrained thermal stress, bimetallic curvature, and critical
temperature rise for a bimetallic strip); calculate plate buckling under
applied mechanical compression or shear with edge-condition coefficients
(plate-buckling owns the k-coefficient compression/shear plate analysis);
solve nonlinear post-buckling or large-deflection behavior (linear elastic
buckling only). The plate and column here buckle because a RESTRAINED
temperature rise builds the compressive load, not because an external load is
applied.

## Model (implement exactly)

Module constants:
- (no material constants; E, nu, alpha, geometry are explicit inputs).

Functions (pure stdlib):
- plate_buckling_stress(elastic_modulus, poisson, thickness, width,
  k_coefficient=4.0) -> float: sigma_cr = k_coefficient * pi**2 *
  flexural_rigidity / (width**2 * thickness) with flexural_rigidity
  D = E * t**3 / (12 * (1 - nu**2)). ValueError if E <= 0, thickness <= 0,
  width <= 0, k_coefficient <= 0, poisson outside (-1, 0.5).
- thermal_stress_uniaxial(elastic_modulus, alpha, temp_rise) -> float:
  sigma = E * alpha * dT. ValueErrors on E <= 0, alpha < 0, dT < 0.
- thermal_stress_biaxial(elastic_modulus, poisson, alpha, temp_rise) ->
  float: sigma = E * alpha * dT / (1 - nu). ValueErrors.
- critical_temp_plate(elastic_modulus, poisson, alpha, thickness, width,
  k_coefficient=4.0, restraint="uniaxial") -> float: set the thermal stress
  equal to sigma_cr and solve for dT: dT = sigma_cr / (E * alpha) for
  uniaxial, dT = sigma_cr * (1 - nu) / (E * alpha) for biaxial. ValueError on
  restraint not in ("uniaxial", "biaxial"), alpha <= 0, others propagate.
- column_critical_temp(elastic_modulus, alpha, effective_length, radius_of_
  gyration) -> float: Euler thermal column between rigid supports:
  axial thermal load P = alpha * E * A * dT; buckling at P_cr = pi**2 * E * I
  / L_eff**2; with I = A * r**2 -> dT_cr = pi**2 * r**2 / (alpha *
  L_eff**2). Signature uses effective_length and radius_of_gyration only
  (area cancels). ValueErrors on E <= 0, alpha <= 0, lengths <= 0.
- thermal_buckling_assessment(elastic_modulus, poisson, alpha, thickness,
  width, temp_rise, k_coefficient=4.0, restraint="uniaxial") -> dict:
  {buckling_stress_Pa, thermal_stress_Pa, critical_temp_rise_K, margin
  (buckling_stress / thermal_stress - 1)}. ValueErrors propagate.

## Worked example

Aluminum skin panel: E = 72 GPa, nu = 0.33, alpha = 23e-6 /K, t = 1.6 mm,
b = 150 mm, k = 4.0, uniaxial restraint.

Deterministic anchors (module outputs as assert targets to 4 s.f. plus bounds):
- plate buckling stress in 25-40 MPa (hand estimate ~30 MPa).
- thermal stress at dT = 10 K uniaxial: 72e9 * 23e-6 * 10 = 16.56 MPa
  (EXACT: 16 560 000 Pa; assert 1.656e7 within 1e-6 relative).
- critical temperature rise uniaxial in 15-25 K (buckling stress / (E alpha)
  = 30.2e6 / 1.656e6 = 18.2 K).
- biaxial critical temp rise = uniaxial value * (1 - nu) = * 0.67 (lower;
  assert the ratio 0.67 within 1e-9 relative between the two restraint calls
  on the same panel).
- column: steel? Use alpha 12e-6, r = 25 mm, L_eff = 2.0 m:
  dT_cr = pi**2 * 0.025**2 / (12e-6 * 4.0) = 9.8696 * 6.25e-4 / 4.8e-5 =
  6.1685e-3 / 4.8e-5 = 128.5 K (bound 110-150 K).
- Margin sign: dT 10 K on the panel -> margin = 30.2/16.56 - 1 = +0.82
  positive; dT 30 K -> negative. Include both in the contract test.
If a value is outside its bound, debug before writing tests. Show real module
outputs in the SKILL.md worked example.

## Validation list (contract test must include)

- ValueError: poisson outside (-1, 0.5), alpha <= 0, dT < 0, restraint not in
  the two allowed strings, k_coefficient <= 0, zero/negative E/thickness/
  width/lengths.
- Uniaxial-to-biaxial ratio identity above.
- Margin sign cases above.
- Determinism.

## Corpus fragment (eval/hit1-wave30-thermal-buckling.yaml)

Forbidden tokens (siblings): thermal-stress alone, bimetallic, free-thermal-
strain, constrained-expansion (thermal-stress-analysis); buckling-coefficient
k edge condition tables, shear buckling, panel-aspect-ratio (plate-buckling);
applied-compression. Distinctive tokens ONLY: thermal-buckling,
critical-temperature-rise, restrained-temperature, thermal-buckling-margin.

Query 1: "Find the critical-temperature-rise that thermally buckles a
restrained 1.6 mm aluminum skin panel 150 mm wide with k 4.0" (id
w30-thermal-buckling-1).
Query 2: "Check the thermal-buckling margin of a hot structure panel at a
30 K restrained temperature rise with uniaxial restraint" (id
w30-thermal-buckling-2).
intent: "structures; buckling from restrained thermal expansion".

## Description/tag guidance

Description opens "Use when you must compute the thermal buckling of
restrained aerospace structure from a temperature rise:" and lists the outputs
in the Claim. First tag: thermal-buckling. Additional tags:
critical-temperature-rise, restrained-thermal-expansion, thermal-buckling-
margin. No generic single words. 50-150 words, <=1000 chars, no em dash, no
"classified".

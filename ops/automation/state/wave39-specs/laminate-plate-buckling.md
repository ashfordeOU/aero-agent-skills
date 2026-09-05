# Wave-39 leaf spec: laminate-plate-buckling (structures, composites pack)

- Path: skills/structures/composites/laminate-plate-buckling/
- Pack: composites. Closest siblings: plate-buckling (fem pack; computes
  sigma_cr = k * pi^2 * E / (12 * (1 - nu^2)) * (t/b)^2 and the shear
  analog from E, nu, t, b with the buckling coefficient from edge
  conditions and effective width - ISOTROPIC material only, no D-matrix
  path), laminate-stiffness (computes ply_stiffness, rotated_ply_stiffness
  and the laminate A-matrix only - no bending D-matrix buckling content),
  sandwich-panels (face wrinkling into the core, a different failure mode),
  failure-criteria (lamina failure indices). Whole-tree greps at prep:
  "orthotropic buckling" and "laminate buckling" = 0 owning hits anywhere;
  the isotropic plate-buckling leaf's logic takes E and nu only. GENUINE
  STRUCT gap (fresh probe).
- Standards id: cmh-17 (reference-only). Ledger Standard: cmh-17.
- Family: structures

## Claim

Compute the elastic buckling load of an orthotropic or laminated flat plate
under uniaxial in-plane compression from the classical laminated-plate
theory bending stiffnesses: evaluate the energy-method critical load
N_x_cr(m, n) = pi^2 * [D11*(m/a)^2 + 2*(D12 + 2*D66)*(n/b)^2 +
D22*n^4*a^2/(m^2*b^4)] for integer half-wave counts m and n, minimize over
the mode counts, and return the critical load per unit width and the margin
against an applied in-plane load. Produces the critical load, the buckling
mode (m, n) and the margin that gate composite panel stability checks. Does
NOT do: isotropic plate buckling with a single buckling coefficient
(plate-buckling); laminate A-matrix stiffness synthesis (laminate-
stiffness); sandwich face wrinkling (sandwich-panels); lamina failure
indices (failure-criteria).

## Model (implement exactly)

Conventions: a simply supported orthotropic plate of length a (load
direction) and width b, bending stiffnesses D11, D22, D12, D66 in N m. The
critical load per unit width for mode (m, n):

N_x_cr(m, n) = pi^2 * (D11 * (m/a)^2 + 2 * (D12 + 2*D66) * (n/b)^2 +
D22 * n^4 * a^2 / (m^2 * b^4))

Functions (pure stdlib):
- critical_load(d11, d22, d12, d66, a, b, m, n) -> float N/m for the mode;
  ValueError on non-positive D values or dimensions, m or n not positive
  integers.
- buckling_mode(d11, d22, d12, d66, a, b, m_max=20, n_max=20) -> tuple
  (N_x_cr_min, m, n): the minimum over m in 1..m_max and n in 1..n_max,
  ties resolved to the smallest (m, n) lexicographically for determinism.
- buckling_margin(d11, d22, d12, d66, a, b, applied_load, m_max=20,
  n_max=20) -> float N_x_cr / applied_load; ValueError if applied_load <= 0.
Module constants: DEFAULT_M_MAX = 20, DEFAULT_N_MAX = 20.

Identity to test (isotropic reduction): with D11 = D22 = D and D12 +
2*D66 = D (isotropic plate relations), the mode minimization over a long
plate reproduces the classic k = 4 simply supported result: sigma_cr =
4 * pi^2 * D / (b^2 * t). Prep check with E = 70 GPa, nu = 0.3, t = 2 mm,
b = 250 mm gives D = E*t^3/(12*(1-nu^2)) = 51.28 N m and sigma_cr =
16.20 MPa.

## Worked example

a = 0.5 m (load direction), b = 0.25 m, D11 = 200 N m, D22 = 120 N m,
D12 = 25 N m, D66 = 45 N m (representative CFRP layup):
- Mode (2, 1): N_x_cr = pi^2 * (200*(2/0.5)^2 + 2*(25+90)*(1/0.25)^2 +
  120*1*0.25/(4*0.25^4)) = 86.85 kN/m at m = 2, n = 1.
- Applied 40 kN/m -> margin 2.17.
- Isotropic reduction check: E = 70 GPa, nu = 0.3, t = 2 mm, b = 250 mm
  -> sigma_cr = 16.20 MPa (k = 4 classic).
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds (independently evaluated at prep).

## Validation list (contract test must include)

- critical_load at the worked-example mode (2, 1) = 86.85 kN/m within
  0.1 kN/m; buckling_mode returns (86850ish, 2, 1).
- Margin 2.17 within 0.01 at 40 kN/m applied.
- Isotropic reduction anchor: 16.20 MPa within 0.05 MPa (convert N/m to
  stress by dividing by t = 0.002 m).
- Monotonicity: critical load rises with D11 and with narrower width b.
- Mode count sweep: m_max and n_max of 2 still capture the (2, 1) mode on
  the worked example; m_max 1 forces m = 1 and gives a higher load.
- ValueErrors: zero or negative D, zero or negative a or b, m or n zero,
  applied load 0.
- Determinism; tie resolution to the smallest (m, n).

## Corpus fragment (eval/hit1-wave39-laminate-plate-buckling.yaml)

Query 1 (copy verbatim):
  "compute the laminate-plate-buckling critical compression load of the composite skin panel from the clt d-matrix with half-wave mode minimization"
  intent: "structures; orthotropic laminate plate buckling from the D-matrix"
  expected_skill: "structures/composites/laminate-plate-buckling"
Query 2 (copy verbatim):
  "orthotropic-plate-buckling margin check for the composite fuselage panel under the in-plane compression load"
  intent: "structures; composite panel buckling margin"
  expected_skill: "structures/composites/laminate-plate-buckling"
Task ids: w39-laminate-plate-buckling-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the elastic buckling load
of an orthotropic or laminated flat plate:" and include the outputs in the
Claim. First tag: laminate-plate-buckling. Additional tags ONLY: laminate-
buckling, orthotropic-plate-buckling, d-matrix, buckling-mode-minimization,
composite-panel-stability, compression-buckling. NEVER single generic words
(buckling, plate, laminate, composite, panel, compression, load). 50-150
words, <=1000 chars, no em dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): buckling-coefficient, edge-
condition, effective-width, flat-plate, skin-panel (plate-buckling);
face-wrinkling, core-shear (sandwich-panels); failure-index (failure-
criteria); a-matrix, laminate-stiffness synthesis (laminate-stiffness).

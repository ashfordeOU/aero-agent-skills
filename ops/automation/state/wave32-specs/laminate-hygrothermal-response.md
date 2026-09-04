# Wave-32 leaf spec: laminate-hygrothermal-response (structures, composites pack)

- Path: skills/structures/composites/laminate-hygrothermal-response/
- Pack: composites. Siblings: laminate-stiffness (mechanical CLT/ABD
  only - zero thermal/moisture content), thermal-stress-analysis
  (isotropic constrained-member alpha*dT and bimetallic strips),
  cmh17-allowables (hot/wet statistical strength knockdown),
  sandwich-panels, failure-criteria, delamination-growth.
- Standards id: far-25 (reference-only; design load context). Ledger
  Standard: far-25.
- Family: structures

## Claim

Compute the hygrothermal response of a composite laminate: the
equilibrium moisture content from the ambient relative humidity with a
linear isotherm, the stiffness-weighted laminate coefficients of
thermal and moisture expansion assembled by classical lamination theory
from the ply-level properties, the hygrothermal laminate strain from a
temperature change and a moisture change, and the residual strain from
the cure-cooldown temperature drop. Produces the moisture content, the
laminate CTE and CME, the hygrothermal strain and the cure-cooldown
strain that gate a laminate hygrothermal assessment.

Does NOT do: the mechanical laminate ABD matrix (laminate-stiffness
owns the elastic CLT/ABD); isotropic thermal stress of homogeneous
members (thermal-stress-analysis owns alpha*dT stress and bimetallic
strips); statistical allowables with environmental knockdown
(cmh17-allowables owns hot/wet strength knockdown factors - this leaf
computes EXPANSION strain, not strength); moisture as a honeycomb core
selection caveat (sandwich-panels).

## Model (implement exactly)

Module constants:
- M_SAT_DEFAULT = 0.015 (mass-fraction saturation moisture content
  input default; published CFRP saturation magnitudes 0.01-0.02).
- RHO etc. not needed.

Ply property inputs: E1, E2 (Pa), nu12 (unitless), G12 (Pa), ply
angle theta_deg, ply thickness t_k (m), ply alpha_1 and alpha_2
(1/K), ply beta_1 and beta_2 (per unit moisture mass fraction).
Material properties are INPUTS with documented typical bounds; the
code path is exact CLT arithmetic, no empirical fits inside.

Functions (pure stdlib):

- equilibrium_moisture_content(rh_fraction, m_sat =
  M_SAT_DEFAULT) -> M = m_sat * rh_fraction. ValueError if rh outside
  [0,1] or m_sat <= 0.
- plane_stress_q(e1, e2, nu12, g12) -> dict {q11, q22, q12, q66}:
  q11 = e1/(1 - nu12*nu21), q22 = e2/(1 - nu12*nu21),
  q12 = nu12*e2/(1 - nu12*nu21) = nu21*e1/(1 - nu12*nu21), q66 = g12,
  with nu21 = nu12*e2/e1.  ValueErrors on non-positive moduli or
  nu12 outside [-0.5, 0.5]-ish (use nu12*nu21 < 1 check).
- qbar(q, theta_deg) -> dict {qbar11, qbar22, qbar12, qbar16, qbar26,
  qbar66} by the standard cos/sin power transforms (m = cos(theta),
  n = sin(theta)):
  qbar11 = q11*m^4 + 2*(q12 + 2*q66)*m^2*n^2 + q22*n^4
  qbar22 = q11*n^4 + 2*(q12 + 2*q66)*m^2*n^2 + q22*m^4
  qbar12 = (q11 + q22 - 4*q66)*m^2*n^2 + q12*(m^4 + n^4)
  qbar66 = (q11 + q22 - 2*q12 - 2*q66)*m^2*n^2 + q66*(m^4 + n^4)
  qbar16 = (q11 - q12 - 2*q66)*m^3*n + (q12 - q22 + 2*q66)*m*n^3
  qbar26 = (q11 - q12 - 2*q66)*m*n^3 + (q12 - q22 + 2*q66)*m^3*n
- laminate_cte_cme(plies) -> dict {alpha_x, alpha_y, beta_x, beta_y}
  by the exact CLT free-expansion solution for a symmetric laminate:
  build the 2x2 in-plane stiffness A = sum_k Qbar_k * t_k (rows
  [qbar11, qbar12; qbar12, qbar22], shear row dropped for the balanced
  case) and the thermal force resultant per unit temperature
  Nth = sum_k Qbar_k * [alpha_x_k, alpha_y_k]^T * t_k, then solve
  A * [alpha_x, alpha_y]^T = Nth (2x2 solve by determinant).  The
  moisture vector uses [beta_x_k, beta_y_k] the same way.  This exact
  inversion is REQUIRED: the simplified stiffness-weighted ratio fails
  the unidirectional identity test (a 0-deg unidirectional laminate
  must return alpha_1 exactly, which only the full inversion does).
  ValueErrors: empty ply list, non-positive thickness, angles outside
  [-90, 90], singular A.
- hygrothermal_strain(alpha_x, beta_x, delta_t_k, delta_m) ->
  eps = alpha_x*delta_t + beta_x*delta_m (and the y-component when
  requested).  No ValueError beyond non-finite guards.
- cure_cooldown_strain(alpha_x, t_cure_c, t_rt_c = 21.0) ->
  delta_t = t_rt - t_cure (negative for a cooldown) and strain =
  alpha_x*delta_t.
- cte_ppm(alpha) -> alpha * 1e6 (reporting helper; alpha in raw 1/K).
- laminate_hygrothermal_response(plies, rh_fraction, delta_t_k,
  delta_m = None, m_sat = M_SAT_DEFAULT, t_cure_c = None) -> dict
  {equilibrium_moisture_content, alpha_x, alpha_y, beta_x, beta_y,
  hygrothermal_strain_x, hygrothermal_strain_y,
  cure_strain_x (None when t_cure_c None)}.  delta_m defaults to the
  equilibrium moisture content when not given.  All coefficients are
  stored raw SI (alpha in 1/K, beta per unit moisture fraction);
  cte_ppm(alpha) = alpha*1e6 is the reporting helper.  ValueErrors
  propagate.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Symmetric balanced [0/90]s carbon/epoxy laminate (T300/5208-style ply
properties as INPUT): ply t = 0.125e-3 m each, E1 = 181e9, E2 = 10.3e9,
G12 = 7.17e9, nu12 = 0.28, alpha_1 = -0.3e-6, alpha_2 = 28.1e-6,
beta_1 = 0.0, beta_2 = 0.6 per unit moisture fraction.  Ambient RH =
0.6, m_sat = 0.015, cure temperature 177 C, room temperature 21 C.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds:
- equilibrium_moisture_content 0.009 (0.015*0.6).
- plane_stress_q: q11 about 181.8e9, q22 about 10.35e9.
- laminate alpha_x about 1.60e-6/K (1.55-1.70 ppm; exact CLT inversion
  of the [0/90]s; the simplified q11-only ratio gives a WRONG 1.65 ppm
  and must not be used); alpha_y about the same 1.60e-6/K for the
  [0/90]s (square symmetric layup).
- cure-cooldown strain x = alpha_x*(-156 K) about -2.50e-4.
- moisture branch: delta_m = 0.009 with beta_x about 0.040 (the CLT
  moisture solution; beta_1 = 0, beta_2 = 0.6 inputs) ->
  hygrothermal strain about 3.6e-4.  Document beta as material input;
  published CFRP swelling strain at saturation is roughly 0.1-0.7%
  when beta_2 ~ 0.1-0.6 and M_sat ~ 1-2%.
- A unidirectional 0-deg layup returns alpha_x == alpha_1 (-0.3e-6/K)
  to float precision (the exact-inversion identity test).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: RH outside [0,1]; m_sat <= 0; non-positive moduli;
  nu12*nu21 >= 1; empty ply list; non-positive ply thickness; angle
  outside [-90, 90].
- equilibrium moisture: RH = 0 -> 0; RH = 1 -> m_sat.
- 0-deg unidirectional layup returns alpha_1/beta_1 to float precision.
- Symmetric cross-ply: the stiffness-weighted average formula matches
  a direct sum for the [0/90]s (assert the worked value ~1.23e-6/K in
  the 0-5 ppm band).
- cure strain sign: cooling (delta_t < 0) with positive alpha gives
  negative strain (shrinkage).
- Determinism: no RNG, identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-laminate-hygrothermal-response.yaml)

Query 1 (copy verbatim):
  "compute the stiffness-weighted thermal expansion coefficients and moisture swelling coefficients of a symmetric composite laminate by classical lamination theory"
  intent: "structures; laminate CTE and moisture expansion from CLT"
  expected_skill: "structures/composites/laminate-hygrothermal-response"
Query 2 (copy verbatim):
  "determine the equilibrium moisture content and the hygrothermal strain of a carbon epoxy laminate from the relative humidity and the cure cooldown temperature drop"
  intent: "structures; laminate hygrothermal and cure-cooldown strain"
  expected_skill: "structures/composites/laminate-hygrothermal-response"
Task ids: w32-laminate-hygrothermal-response-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the hygrothermal
response of a composite laminate:" and include the outputs in the
Claim. First tag: laminate-hygrothermal-response. Additional tags
ONLY: hygrothermal-response, laminate-cte, moisture-swell-strain,
cure-cooldown-strain, hygral-strain, laminate-moisture-content. NEVER
single generic words (laminate, moisture, thermal, strain, composite,
temperature). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): ABD matrix, laminate stiffness,
elastic modulus matrix, mechanical load (laminate-stiffness); thermal
stress, constrained expansion, bimetallic strip, E*alpha*dT stress
(thermal-stress-analysis); knockdown, B-basis, A-basis, environmental
strength (cmh17-allowables); honeycomb core (sandwich-panels).

Tags: [laminate-hygrothermal-response, hygrothermal-response,
laminate-cte, moisture-swell-strain, cure-cooldown-strain,
hygral-strain, laminate-moisture-content]

Sibling-citation lines for Related leaves:
structures/composites/laminate-stiffness (mechanical ABD sibling whose
Qbar assembly this leaf reuses for the thermal/moisture weighting),
structures/composites/cmh17-allowables,
structures/thermal-structures/thermal-stress-analysis,
structures/composites/sandwich-panels.

Ledger Standard: far-25.

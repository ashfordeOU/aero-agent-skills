# Wave-32 leaf spec: cylindrical-shell-buckling (structures, fem pack)

- Path: skills/structures/fem/cylindrical-shell-buckling/
- Pack: fem. Siblings: buckling-analysis (Euler columns),
  plate-buckling (flat plates), thermal-buckling (flat restrained
  panel), beam-frame-analysis, truss-analysis, modal-analysis.
- Standards id: far-25 (reference-only; airframe loads context).
  Ledger Standard: far-25.
- Family: structures

## Claim

Compute the buckling of curved, unstiffened circular cylindrical
shells (fuselage barrels, pressure-vessel and tank shells, ducts) with
the NASA SP-8007 empirical knockdown method: the axial-compression
knockdown factor from the shell radius and thickness, the axial
critical stress, the bending knockdown factor, the bending critical
moment, the cross-section ovalization collapse moment, and the
plasticity correction factor. Produces the knockdown factors, the
critical stress and moment, and the governing verdict that gate a
curved-shell stability check. The coefficients are pinned
public-domain NASA SP-8007 values.

Does NOT do: Euler column buckling (buckling-analysis owns Pcr =
pi^2*E*I/(K*L)^2 for slender columns); flat plate buckling
(plate-buckling owns the plate coefficient k and sigma_cr =
k*pi^2*E/(12*(1-nu^2))*(t/b)^2 - the curved case is explicitly deferred
by that leaf); thermal buckling of flat panels (thermal-buckling);
stiffened-panel fuselage sizing with flat-panel + stringer-column
models (vehicle-design/structures-integration/fuselage-skin-stringer
owns the stiffened pressurized fuselage model); composite strength
knockdown factors (structures/composites/cmh17-allowables).

## Model (implement exactly)

Module constants (NASA SP-8007, "Buckling of Thin-Walled Circular
Cylinders", 1968 original / 2023 NTRS revision 20205011530; verified
from the public-domain PDF; reference-only paraphrase in the body):
- K_AXIAL_A = 0.901 (axial knockdown coefficient).
- K_AXIAL_B = 0.605 (axial classical coefficient = 1/sqrt(3*(1-nu^2))
  at nu = 0.3).
- K_BEND_A = 0.731 (bending knockdown coefficient).
- K_OVAL = 0.987 (ovalization collapse coefficient).
- PHI_FACTOR = 1/16 (knockdown exponent factor phi = (1/16)*sqrt(r/t)).
- NU_DEFAULT = 0.3.
- R_T_LIMIT = 1500 (validity guard: SP-8007 empirical knockdowns are
  for r/t below about 1500).

Functions (pure stdlib):

- curvature_parameter(radius_m, thickness_m) -> phi =
  (1/16)*sqrt(radius_m/thickness_m). ValueError if radius <= 0 or
  thickness <= 0 or radius/thickness >= R_T_LIMIT.
- knockdown_axial(radius_m, thickness_m) -> gamma_a = 1 -
  K_AXIAL_A*(1 - exp(-phi)).  Monotonic decreasing in r/t; in (0,1).
- knockdown_bending(radius_m, thickness_m) -> gamma_b = 1 -
  K_BEND_A*(1 - exp(-phi)).
- axial_critical_stress(e_mod_pa, thickness_m, radius_m, gamma =
  None) -> sigma_cr = K_AXIAL_B * gamma * E * t / r; when gamma is
  None compute knockdown_axial(r, t).  ValueErrors on non-positive
  inputs; r/t >= R_T_LIMIT guard.
- bending_critical_moment(e_mod_pa, thickness_m, radius_m, gamma =
  None) -> M_cr = PI * K_AXIAL_B * gamma * E * t**2 * r.
  Derivation: the axial critical stress sigma_cr = 0.605*gamma*E*t/r
  acts over the full wall section (area pi*r*t) at the extreme fiber
  arm r, giving M = sigma_cr * (pi*r*t) * r = pi*0.605*gamma*E*t**2*r.
  When gamma is None compute knockdown_bending(r, t) internally.
  ValueErrors on non-positive inputs; r/t >= R_T_LIMIT guard.
- ovalization_collapse_moment(e_mod_pa, thickness_m, radius_m, nu =
  NU_DEFAULT) -> M_ov = K_OVAL * E * r * t**2 / sqrt(1 - nu**2).
- plasticity_correction(e_sec_pa, e_tan_pa, e_mod_pa) -> eta =
  sqrt(e_sec * e_tan) / E.
- shell_buckling_assessment(e_mod_pa, thickness_m, radius_m, nu =
  NU_DEFAULT, e_sec_pa = None, e_tan_pa = None) -> dict
  {radius_to_thickness, curvature_parameter, gamma_axial,
  gamma_bending, sigma_cr_axial_pa, m_cr_bending_Nm,
  m_cr_ovalization_Nm, governing ("bifurcation" when
  m_cr_bending < m_cr_ovalization else "ovalization"),
  eta_plasticity (None when e_sec or e_tan None)}.  ValueErrors
  propagate.

ALL functions deterministic, no RNG, stdlib only.  Note: SP-8007
stresses are elastic; the plasticity correction eta is reported
separately and applied by the user when the material is beyond the
proportional limit (document this).

## Worked example

Aluminum barrel: E = 70e9 Pa, radius r = 1.5 m, thickness t = 0.005 m
(r/t = 300), nu = 0.3.  Run your module and take the real outputs as
assert targets, then check the magnitude bounds:
- curvature_parameter phi about 1.0825 (sqrt(300)/16).
- gamma_axial about 0.404 (1 - 0.901*(1 - exp(-1.0825))); in (0.35,
  0.45).
- sigma_cr_axial about 57.1e6 Pa (57 MPa; in 50-65 MPa).
- gamma_bending about 0.517 (in 0.45-0.60).
- m_cr_bending about 2.58e6 N*m (in 2.2e6-3.0e6).
- m_cr_ovalization about 2.72e6 N*m (in 2.4e6-3.1e6).
- governing "bifurcation" (bending bifurcation moment below the
  ovalization collapse, consistent with the SP-8007 note that
  bifurcation precedes collapse).
- r/t = 100: gamma_axial about 0.581; r/t = 1600 raises ValueError.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: radius <= 0, thickness <= 0, E <= 0, r/t >= 1500.
- gamma bounds: knockdown_axial and knockdown_bending in (0,1);
  gamma decreases as r/t increases (monotonic).
- gamma_axial at r/t = 100 about 0.581 (1 - 0.901*(1 - exp(-0.625)));
  gamma_bending at r/t = 100 about 0.660 (1 - 0.731*(1-exp(-0.625))).
- sigma_cr_axial = 0.605*gamma*E*t/r identity for the worked case.
- M_cr_ovalization formula exact: 0.987*E*r*t^2/sqrt(1-nu^2).
- plasticity_correction: e_sec = e_tan = E gives eta = 1.0.
- Determinism: no RNG, identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-cylindrical-shell-buckling.yaml)

Query 1 (copy verbatim):
  "compute the NASA SP-8007 knockdown factors and axial critical buckling stress of an unstiffened circular cylindrical shell from the radius and thickness"
  intent: "structures; cylindrical shell axial buckling with SP-8007 knockdown"
  expected_skill: "structures/fem/cylindrical-shell-buckling"
Query 2 (copy verbatim):
  "determine the bending critical moment and the ovalization collapse moment of a thin-walled cylinder and judge the governing stability mode"
  intent: "structures; cylindrical shell bending buckling versus ovalization collapse"
  expected_skill: "structures/fem/cylindrical-shell-buckling"
Task ids: w32-cylindrical-shell-buckling-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the buckling of a
curved unstiffened circular cylindrical shell with the NASA SP-8007
knockdown method:" and include the outputs in the Claim. First tag:
cylindrical-shell-buckling. Additional tags ONLY: sp-8007-knockdown,
shell-axial-compression, external-shell-bending,
cross-section-ovalization, shell-plasticity-correction. NEVER single
generic words (buckling, shell, cylinder, stress, moment, knockdown).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): Euler, slenderness, column
(buckling-analysis); plate buckling coefficient, flat panel, k*pi^2
(plate-buckling); thermal buckling (thermal-buckling); stringer, frame
pitch, hoop stress, pressurized fuselage (vehicle-design/
structures-integration/fuselage-skin-stringer); composite, B-basis,
knockdown of strength allowables (cmh17-allowables).  The word
"knockdown" is this leaf's own in the SP-8007 context.

Tags: [cylindrical-shell-buckling, sp-8007-knockdown,
shell-axial-compression, external-shell-bending,
cross-section-ovalization, shell-plasticity-correction]

Sibling-citation lines for Related leaves: structures/fem/
buckling-analysis, structures/fem/plate-buckling (which defers the
curved case here), structures/fem/thermal-buckling,
vehicle-design/structures-integration/fuselage-skin-stringer (the
stiffened fuselage model - this leaf covers the UNSTIFFENED curved
barrel), structures/composites/cmh17-allowables.  Reference: NASA
SP-8007 (public domain) named in the body with the coefficients and
the validity band; never reproduce the handbook text verbatim.

Ledger Standard: far-25.

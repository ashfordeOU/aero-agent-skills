# Wave-33 leaf spec: laminate-first-ply-failure (structures, composites pack)

- Path: skills/structures/composites/laminate-first-ply-failure/
- Pack: composites. Siblings: laminate-stiffness (ABD matrix assembly
  only - no loads, no strain recovery, no allowables),
  failure-criteria (Tsai-Wu/Tsai-Hill/max-stress indices from
  USER-SUPPLIED lamina stresses, no laminate, no N/M resultants),
  laminate-hygrothermal-response (Delta-T/Delta-M strain response),
  delamination-growth (energy-based, explicitly disclaims stress-based
  ply failure). This leaf chains: A^-1 mid-plane strain recovery ->
  per-ply stress transformation -> per-ply Tsai-Wu index -> first-ply
  failure load scale factor.
- Standards id: cmh-17 (reference-only) + far-25 (reference-only).
  Ledger Standard: cmh-17.
- Family: structures

## Claim

Compute the first-ply-failure load and the critical ply of a symmetric
balanced composite laminate under in-plane load resultants: recover the
mid-plane strains from the A-matrix inverse, transform the strains to
each ply's material axes, compute per-ply stresses, evaluate the
Tsai-Wu failure index in every ply, and return the first-ply-failure
load scale factor k* = 1 / max(FI) with the critical ply and the
reserve factor. Produces the mid-plane strains, the per-ply failure
indices, the critical ply, and the FPF load resultant.

Does NOT do: ABD assembly (laminate-stiffness); single-lamina failure
indices from given stresses (failure-criteria); hygrothermal strain
response (laminate-hygrothermal-response); delamination growth
(energy-based); allowables tables (references CMH-17 / MMPDS data by
name, never reproduces tables).

## Model (implement exactly)

Conventions: balanced symmetric laminate under in-plane resultants
{N} = {Nx, Ny, Nxy} (N/mm). Mid-plane strains from {eps} = [A]^-1 {N};
balanced symmetric => shear decoupled (gamma_xy = a66 Nxy). Ply k at
angle theta_k: transform laminate strains to material axes
{eps1, eps2, gamma12} = [T(theta)] {eps_x, eps_y, gamma_xy}, stresses
{sigma1, sigma2, tau12} = [Q] {eps1, eps2, gamma12} (material-axis
2D stiffness). Tsai-Wu: FI = F1 s1 + F2 s2 + F11 s1^2 + F22 s2^2 +
F66 t12^2 + 2 F12 s1 s2 with F1 = 1/Xt - 1/Xc, F2 = 1/Yt - 1/Yc,
F11 = 1/(Xt Xc), F22 = 1/(Yt Yc), F66 = 1/S^2,
F12 = -0.5 sqrt(F11 F22). FPF load = k* N with k* = 1 / max_k FI_k.

Functions (pure stdlib):

- midplane_strains(a11, a12, a22, a66, nx, ny, nxy) -> (ex, ey, gxy)
  with ex = a11 nx + a12 ny, ey = a12 nx + a22 ny, gxy = a66 nxy
  (a_ij are the A-inverse compliance entries, N/mm units consistent).
- ply_material_strains(ex, ey, gxy, theta_deg) -> (e1, e2, g12):
  e1 = ex c^2 + ey s^2 + gxy c s, e2 = ex s^2 + ey c^2 - gxy c s,
  g12 = 2 (ey - ex) c s + gxy (c^2 - s^2) with c = cos(theta),
  s = sin(theta).
- ply_material_stresses(e1, e2, g12, q11, q12, q22, q66) ->
  (s1, s2, t12) = (q11 e1 + q12 e2, q12 e1 + q22 e2, q66 g12).
- tsai_wu_index(s1, s2, t12, xt, xc, yt, yc, s_uv) -> FI (formula
  above). ValueErrors on non-positive allowables.
- ply_failure_indices(plies_deg, q_components, allowables, nx, ny,
  nxy, a_components) -> list of per-ply FI (index order matches the
  plies list). Internally calls midplane_strains, the per-ply
  transforms and tsai_wu_index.
- first_ply_failure(plies_deg, q_components, allowables, nx, ny, nxy,
  a_components) -> dict {max_fi, critical_ply_index, critical_ply_deg,
  fpf_scale_k, fpf_load_nx, reserve_factor}. fpf_load_nx = k* nx for
  the uniaxial case; reserve_factor = k*.
- first_ply_failure_load(...) same as first_ply_failure (alias kept for
  discoverability); pick ONE canonical name for the SKILL body and the
  contract test.

Provide a small helper to build [Q] from the four engineering constants
(e1, e2, nu12, g12) -> (q11, q12, q22, q66) so builders do not need to
import the laminate-stiffness module: q11 = E1/(1 - nu12 nu21),
q22 = E2/(1 - nu12 nu21), q12 = nu12 E2/(1 - nu12 nu21), q66 = G12
with nu21 = nu12 E2 / E1. ValueErrors on non-positive inputs.

## Worked example

T300/5208: E1 = 181 GPa, E2 = 10.3 GPa, G12 = 7.17 GPa, nu12 = 0.28;
Xt = Xc = 1500 MPa, Yt = 40 MPa, Yc = 246 MPa, S = 68 MPa. Laminate
[0/90/45/-45]s, ply thickness 0.125 mm (8 plies). Applied Nx =
100 N/mm.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- A11 about 76368 N/mm, A12 about 22607 N/mm, A22 about 76368 N/mm,
  A66 about 26880 N/mm (verify against your own A-matrix assembly or
  hard-code the reference A from the plies).
- ex about 1.435e-3, ey about -4.25e-4 (gamma_xy = 0 for uniaxial on a
  balanced symmetric laminate).
- Max Tsai-Wu FI about 0.3130 in the 90-degree ply (transverse
  sigma2 about 13.6 MPa dominates via the F2 linear term) ->
  FPF Nx about 319.5 N/mm, reserve factor about 3.195.
- 0-degree ply sigma1 = E1 ex about 259.7 MPa (sanity: below Xt).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive allowables; non-positive engineering
  constants; non-positive a_ij.
- Worked-case identity: FI in the 90-degree ply is the max; the
  critical ply index points at a 90-degree ply; FPF load about 319.5
  N/mm.
- Unidirectional identity: a [0]8 laminate under Nx fails in the fiber
  direction at k* = Xt / sigma1 (closed-form check with Xt 1500 MPa).
- Round-trip: the 0-ply stress from the strain recovery equals E1 ex
  for the [0]8 case.
- Symmetry: [0/90/45/-45]s and its mirror give the same FPF (list order
  reversed) - the A matrix and FPF are order-independent for symmetric
  balanced stacking.
- Determinism: identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-laminate-first-ply-failure.yaml)

Query 1 (copy verbatim):
  "compute the first ply failure load and the critical ply of a quasi isotropic composite laminate under in plane load resultants recovered from the mid plane strain"
  intent: "structures; laminate first-ply-failure FPF load and critical ply from mid-plane strain recovery"
  expected_skill: "structures/composites/laminate-first-ply-failure"
Query 2 (copy verbatim):
  "find the per ply tsai wu failure index and reserve factor of the symmetric balanced laminate under the applied in plane load resultants before first ply failure"
  intent: "structures; per-ply Tsai-Wu failure index, reserve factor, first-ply-failure of a laminate"
  expected_skill: "structures/composites/laminate-first-ply-failure"
Task ids: w33-laminate-first-ply-failure-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the first-ply-failure
load of a composite laminate:" and include the outputs in the Claim.
First tag: laminate-first-ply-failure. Additional tags ONLY:
tsai-wu-failure-index, first-ply-failure-load, critical-ply,
reserve-factor, midplane-strain-recovery, laminate-failure-envelope.
NEVER single generic words (laminate, failure, ply, composite, stress,
load). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): ABD matrix, ply stiffness,
laminate stiffness matrix assembly (laminate-stiffness); hygrothermal,
moisture, coefficient of thermal expansion (laminate-hygrothermal-
response); delamination, strain energy release rate (delamination-
growth); single-ply failure from given stresses (failure-criteria);
thermal stress (thermal-stress-analysis). The tokens "first ply
failure", "critical ply", "reserve factor", "failure index" are this
leaf's own (failure-criteria owns the index formula at lamina level;
this leaf owns the laminate-level FPF search).

Tags: [laminate-first-ply-failure, tsai-wu-failure-index,
first-ply-failure-load, critical-ply, reserve-factor,
midplane-strain-recovery, laminate-failure-envelope]

Sibling-citation lines for Related leaves:
structures/composites/laminate-stiffness (ABD assembly, the strain
recovery start point),
structures/composites/failure-criteria (lamina-level index),
structures/composites/laminate-hygrothermal-response,
structures/composites/delamination-growth.

Ledger Standard: cmh-17.

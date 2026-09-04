---
name: laminate-first-ply-failure
description: "Use when you must compute the first-ply-failure load of a composite laminate: recover the mid-plane strains of a symmetric balanced laminate from its in-plane compliance under applied load resultants, transform the strains to each ply material axis, compute the per-ply Tsai-Wu failure index, and return the critical ply. Produces the mid-plane strains, the per-ply failure indices, the critical ply, the first-ply-failure load scale factor, the FPF load resultant, and the reserve factor. Trigger: first-ply-failure load, first ply failure, critical ply, tsai-wu failure index, reserve factor, mid-plane strain recovery, in-plane load resultant, symmetric balanced laminate, quasi-isotropic laminate, laminate failure envelope, FPF load, per-ply failure index, composite laminate strength."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: cmh-17
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [laminate-first-ply-failure, tsai-wu-failure-index, first-ply-failure-load, critical-ply, reserve-factor, midplane-strain-recovery, laminate-failure-envelope]
  version: 0.1.0
  author: AeroSkills
---

# First-Ply-Failure of a Composite Laminate (structures/composites/laminate-first-ply-failure)

Use when the task is laminate-level first-ply-failure (FPF) strength:
finding the load at which the first ply of a symmetric balanced
composite laminate fails under in-plane load resultants. This leaf
implements the strength chain in pure Python, stdlib only: mid-plane
strain recovery from the A-matrix inverse compliance, per-ply strain
transformation to the material axes, per-ply stress recovery with the
material 2D stiffness, the Tsai-Wu failure index in every ply, and the
FPF load scale factor k* = 1 / max(FI) with the critical ply and the
reserve factor. It pairs with structures/composites/laminate-stiffness,
which assembles the stiffness this leaf inverts, and
structures/composites/failure-criteria, which owns the lamina-level
index formula for user-supplied stresses.

## Domain quick reference

- Loads: in-plane resultants {Nx, Ny, Nxy} in N/mm act on the laminate;
  the leaf works in units of N/mm, MPa and dimensionless strain.
- Mid-plane strains: {ex, ey, gxy} = [A]^-1 {N}. A balanced symmetric
  laminate decouples shear, so ex = a11 Nx + a12 Ny, ey = a12 Nx +
  a22 Ny and gxy = a66 Nxy, where a_ij are the A-inverse compliance
  entries in mm/N.
- Ply k at angle theta: material-axis strains {e1, e2, g12} come from
  the rotation e1 = ex c^2 + ey s^2 + gxy c s, e2 = ex s^2 + ey c^2 -
  gxy c s, g12 = 2 (ey - ex) c s + gxy (c^2 - s^2), with c = cos(theta),
  s = sin(theta).
- Material-axis stresses: {s1, s2, t12} = [Q] {e1, e2, g12} with the
  plane-stress stiffness q11 = E1/(1 - nu12 nu21), q22 = E2/(1 - nu12
  nu21), q12 = nu12 E2/(1 - nu12 nu21), q66 = G12 and nu21 = nu12 E2/E1.
- Tsai-Wu index: FI = F1 s1 + F2 s2 + F11 s1^2 + F22 s2^2 + F66 t12^2 +
  2 F12 s1 s2 with F1 = 1/Xt - 1/Xc, F2 = 1/Yt - 1/Yc, F11 = 1/(Xt Xc),
  F22 = 1/(Yt Yc), F66 = 1/S^2 and F12 = -0.5 sqrt(F11 F22). FI >= 1.0
  marks ply failure.
- First ply failure: the ply with the largest index is critical; the
  FPF scale factor is k* = 1 / max(FI) and the FPF load resultant for
  the uniaxial case is k* Nx, with the reserve factor equal to k*. The
  index is quadratic in stress, so k* = 1 / FI is a linearized reserve
  factor; it is exact at the failure boundary itself and is the
  convention of this leaf.
- CMH-17 frames the ply allowables and lamina data context; the
  relations above are standard mechanics, summary-only.

## Workflow

1. Fix the material: engineering constants E1, E2, nu12, G12 and the
   allowables Xt, Xc, Yt, Yc, S in MPa (q_matrix_from_constants builds
   [Q] without importing the laminate-stiffness module).
2. Get the laminate in-plane compliance: assemble the A block with
   a_matrix_from_plies (angles in degrees, ply thickness in mm) and
   invert it with a_inverse_compliance into (a11, a12, a22, a66); or
   take the compliance directly from the laminate-stiffness leaf.
3. Recover the mid-plane strains with midplane_strains from the applied
   resultants (Nx, Ny, Nxy in N/mm).
4. Per ply, transform the strains with ply_material_strains and recover
   the material stresses with ply_material_stresses; ply_failure_indices
   runs the whole per-ply loop and returns the index list in ply order.
5. Evaluate the laminate: first_ply_failure returns the dict with
   max_fi, critical_ply_index, critical_ply_deg, fpf_scale_k,
   fpf_load_nx and reserve_factor (first_ply_failure_load is an alias).
6. Confirm the deterministic checks with the contract test
   scripts/test_laminate_first_ply_failure.py.

## Worked example

T300/5208: E1 = 181 GPa, E2 = 10.3 GPa, G12 = 7.17 GPa, nu12 = 0.28;
Xt = Xc = 1500 MPa, Yt = 40 MPa, Yc = 246 MPa, S = 68 MPa. Laminate
[0/90/45/-45]s, ply thickness 0.125 mm (8 plies), Nx = 100 N/mm. Real
module outputs:

- Material stiffness: q11 = 181811.1 MPa, q12 = 2896.9 MPa,
  q22 = 10346.2 MPa, q66 = 7170.0 MPa.
- Laminate A block: A11 = A22 = 76368.2 N/mm, A12 = 22607.4 N/mm,
  A66 = 26880.4 N/mm; compliance a11 = a22 = 1.4352e-5 mm/N,
  a12 = -4.2487e-6 mm/N, a66 = 3.7202e-5 mm/N.
- Mid-plane strains: ex = 1.4352e-3, ey = -4.2487e-4, gxy = 0
  (uniaxial load on a balanced symmetric laminate).
- Per-ply failure indices: [0.0254, 0.3130, 0.1827, 0.1827, 0.1827,
  0.1827, 0.3130, 0.0254]; the 90-degree plies are critical. The
  90-degree transverse stress s2 = 13.62 MPa dominates its index through
  the F2 linear term; the 0-degree fiber stress s1 = 259.7 MPa stays far
  below Xt.
- FPF summary: max_fi = 0.313007, critical_ply_index = 1 (90 degrees),
  fpf_scale_k = 3.1948, FPF load Nx = 319.5 N/mm, reserve factor 3.195.

## Verification

- Confirm first_ply_failure on the worked laminate returns max_fi about
  0.3130 with the critical ply at 90 degrees and FPF Nx about 319.5 N/mm.
- Unidirectional identity: a [0]8 laminate under Nx fails in the fiber
  direction; with sigma1 = Nx/t and Xt = Xc the index is (sigma1/Xt)^2,
  so at sigma1 = Xt the index is 1.0 and k* = Xt/sigma1 = 1. The 0-ply
  stress recovered from the strain equals E1 ex exactly.
- Mirror symmetry: reversing the ply list order leaves the A block and
  the FPF result unchanged for the same set of ply angles.
- Determinism: identical inputs give bit-identical floats run to run.
- ValueError rejection of non-physical inputs: non-positive allowables,
  non-positive engineering constants, a singular Poisson product, empty
  ply lists, non-positive ply thickness, and non-positive diagonal
  compliance terms all raise.
- Run the contract test offline: python3
  scripts/test_laminate_first_ply_failure.py (34 tests, deterministic).

## Related leaves

- structures/composites/laminate-stiffness: ABD assembly, the strain
  recovery start point.
- structures/composites/failure-criteria: lamina-level index from given
  stresses.
- structures/composites/laminate-hygrothermal-response: thermal and
  moisture strain response before the mechanical load step.
- structures/composites/delamination-growth: energy-based growth, not
  stress-based ply failure.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_laminate_first_ply_failure.py

The test covers the T300/5208 worked example (A block about
76368/22607/26880 N/mm, ex about 1.435e-3, ey about -4.25e-4, max
Tsai-Wu index about 0.3130 in the 90-degree ply, FPF load about
319.5 N/mm, reserve factor about 3.195), the [Q] builder from
engineering constants including its isotropic reduction, the [0]8
unidirectional closed forms (fiber-direction failure at sigma1 = Xt and
the quadratic index scaling), the stress-strain round trip, mirror
symmetry under reversed ply order, determinism, the exact result-dict
keys, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: CMH-17 (Composite Materials
  Handbook, SAE) and FAR-25 (14 CFR Part 25) frame the ply data and
  airframe certification context; the lamination-theory relations are
  common mechanics, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

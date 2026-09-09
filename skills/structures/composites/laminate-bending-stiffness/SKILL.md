---
name: laminate-bending-stiffness
description: "Use when you must assemble the full classical lamination theory stiffness of a composite laminate stack for the bending and coupling response: compute the bending-extension coupling matrix B and the bending matrix D by the z-squared and z-cubed thickness integrals over the ply z coordinates, the full ABD stiffness matrices for symmetric and unsymmetric laminates, the D11 D22 D12 and D66 bending terms the laminate plate buckling analysis takes as given inputs, the exact zero-coupling identity for symmetric stacks, the coupling magnitude of unsymmetric stacks, and the equivalent flexural engineering constants of symmetric stacks with vanishing D16 and D26. Produces the coupling and bending matrices, the four bending terms and the flexural constants in SI units. Trigger: laminate bending stiffness, bending-extension coupling, laminate d matrix, abd matrices, unsymmetric laminate analysis, d11 d22 d12 d66, equivalent laminate bending stiffness."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: composites
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [laminate-bending-stiffness, clt-abd-matrices, laminate-d-matrix, bending-extension-coupling, unsymmetric-laminate-analysis, laminate-bending-response, d11-d22-d12-d66, equivalent-laminate-bending-stiffness]
  version: 0.1.0
  author: AeroSkills
---

# Laminate Bending Stiffness (structures/composites/laminate-bending-stiffness)

Use when the task is the bending side of classical lamination theory:
the bending-extension coupling matrix B and the bending matrix D of a
composite laminate stack, together with the full ABD assembly for
symmetric and unsymmetric layups. It pairs with
structures/composites/laminate-stiffness, which owns the in-plane
symmetric-laminate A-matrix synthesis, and feeds
structures/composites/laminate-plate-buckling, which consumes the
D11, D22, D12 and D66 bending terms as given inputs to its critical
load analysis.

## Domain quick reference

- A ply has orthotropic stiffness Q11, Q12, Q22, Q66 in material axes
  from the engineering constants E1, E2, nu12, G12; rotation to the
  laminate axes gives the Qbar terms, the integrand of every integral
  below.
- The stack is a bottom-to-top list of (theta_deg, thickness_m) plies;
  the interface z coordinates put the mid-plane at z = 0.
- A_ij = sum_k Qbar_ij,k (z_k - z_k-1), the in-plane extensional
  stiffness (N/m).
- B_ij = (1/2) sum_k Qbar_ij,k (z_k^2 - z_k-1^2), the bending-extension
  coupling matrix (N). B is identically zero to machine precision for
  a mirror-symmetric stack and real, nonzero for an unsymmetric stack.
- D_ij = (1/3) sum_k Qbar_ij,k (z_k^3 - z_k-1^3), the bending matrix
  (N m). A balanced symmetric angle-ply has A16 = A26 = 0 but D16 and
  D26 are NOT zero, so the D terms must come from the z-cubed integral
  and cannot be read off the in-plane A pattern.
- A single isotropic layer gives D11 = E h^3 / (12 (1 - nu^2)), the
  classic plate result and a closed-form check on the model.
- Equivalent flexural constants of a symmetric stack with D16 = D26 =
  0: E_bx = 12 (D11 D22 - D12^2) / (D22 h^3), E_by analogous,
  nu_bxy = D12 / D22, G_bxy = 12 D66 / h^3.
- FAR-25 and CS-25 frame the transport-aeroplane composite airframe
  certification context; the CLT math is common mechanics,
  summary-only.

## Workflow

1. Collect the ply engineering constants E1, E2, nu12, G12 and the
   bottom-to-top ply stack as (theta_deg, thickness_m) tuples.
2. Rotate each ply to the laminate axes with ply_rotated_stiffness,
   the integrand of the z-moment integrals.
3. Assemble the bending-extension coupling matrix with
   b_coupling_matrix over the z-squared thickness integral.
4. Assemble the bending matrix with d_bending_matrix over the
   z-cubed thickness integral.
5. Get the full ABD assembly, including the A sub-block, with
   abd_stiffness_matrices for symmetric or unsymmetric stacks.
6. Pull the four bending terms D11, D22, D12, D66 with
   laminate_bending_terms in the order the laminate plate buckling
   analysis fixes as its given inputs.
7. Recover the equivalent flexural engineering constants with
   equivalent_flexural_constants for symmetric stacks with vanishing
   D16 and D26.
8. Or run the one-shot laminate_bending_report for the full a, b, d
   dict plus the scalar bending terms and the b_max_abs coupling
   magnitude.
9. Confirm the deterministic checks with the contract test
   scripts/test_laminate_bending_stiffness.py.

## Worked example

AS4/3501-6 carbon/epoxy: E1 = 181.0 GPa, E2 = 10.3 GPa,
G12 = 7.17 GPa, nu12 = 0.28, ply thickness t = 0.125 mm.

- Symmetric [0/90]s, plies (0, 90, 90, 0) x 0.125 mm, h = 0.5 mm:
  A11 = 48.0393243936 MN/m, A22 = 48.0393243936 MN/m,
  A12 = 1.44846222217 MN/m, A66 = 3.585 MN/m. B is zero to machine
  precision, max |B_ij| = 8.52651282912e-14 N m. D11 = 1.67060433677,
  D22 = 0.331034179627, D12 = 0.0301762962953, D66 = 0.0746875 (N m),
  the four terms laminate_bending_terms returns for the buckling
  hand-off; D16 and D26 vanish below 1e-9 N m. Equivalent flexural
  constants (D16 = D26 = 0): E_bx = 160.113939519 GPa,
  E_by = 31.7269538028 GPa, G_bxy = 7.17 GPa, nu_bxy = 0.0911576451995.
- Unsymmetric [0/90]2T, plies (0, 90, 0, 90) x 0.125 mm: the A block
  matches the [0/90]s case exactly (same ply set), but
  B11 = -2679.14031429 N m and B22 = +2679.14031429 N m, three orders
  above the D scale, a real bending-extension coupling no symmetric
  stack can produce. D11 = D22 = 1.0008192582 N m, softer than the
  [0/90]s stack because the stiff 0-degree plies are not at the faces.
- Symmetric balanced angle-ply [+45/-45]s: A16 = A26 = 0 exactly
  (balance removes the in-plane coupling) while max |B_ij| =
  2.27373675443e-13 N m (the B == 0 identity holds again) and D16 =
  D26 = 0.334892539286 N m, NONZERO: balance removes the A coupling
  but not the D coupling, the reason the z-cubed integral is required.
- Isotropic reduction, E = 70 GPa, nu = 0.3, h = 2 mm: D11 =
  51.2820512821 N m, matching E h^3 / (12 (1 - nu^2)) within 1e-9
  relative; equivalent_flexural_constants recovers E_bx = 70 GPa,
  G_bxy = 26.9230769231 GPa and nu_bxy = 0.3 within 1e-9 relative.

## Verification

- Confirm abd_stiffness_matrices on the [0/90]s stack reproduces the
  D11, D22, D12, D66 and A11, A22, A12, A66 values above within 1e-6
  relative.
- Confirm max |b_coupling_matrix| is below 1e-9 N m for the [0/90]s
  and [+45/-45]s stacks (the symmetric B == 0 identity, never asserted
  as exact equality to zero) and near 2679.14 N m for the unsymmetric
  [0/90]2T stack.
- Confirm the leading principal minors of the symmetric 3x3 D matrix
  are all positive for the [0/90]s, [0/90]2T and [+45/-45]s stacks.
- Confirm the isotropic reduction and the equivalent flexural constant
  recovery within 1e-9 relative.
- Confirm every non-positive or boolean modulus, thickness or nu12
  outside [0, 1), an empty ply list, and a non-positive-definite D
  pair each raise ValueError.
- Run the contract test offline: python3
  scripts/test_laminate_bending_stiffness.py (31 tests, deterministic).

## Related leaves

- structures/composites/laminate-stiffness: the in-plane symmetric
  laminate A-matrix synthesis; this leaf's A sub-block is produced
  only inside the full ABD assembly and matches that synthesis for
  symmetric stacks.
- structures/composites/laminate-plate-buckling: the consumer that
  takes the D11, D22, D12 and D66 terms this leaf produces as its
  workflow step 1 inputs for the critical buckling load.
- structures/composites/laminate-first-ply-failure: mid-plane strain
  recovery of a symmetric balanced laminate from its in-plane
  compliance, a separate in-plane failure surface.
- structures/composites/unidirectional-lamina-micromechanics: the
  constituent-to-lamina prediction of E1, E2, nu12 and G12 that feed
  this leaf as inputs.

## Pitfalls

- Reading the D16 and D26 terms off the in-plane A pattern: a balanced
  angle-ply has A16 = A26 = 0 exactly but D16 = D26 = 0.334892539286
  N m nonzero in the worked [+45/-45]s example, so the bending
  coupling must be computed by the z-cubed integral, never inferred.
- Asserting B == 0 as exact float equality: the symmetric-stack
  residue is a floating-point cancellation artifact (8.5265e-14 and
  2.2737e-13 N m in the worked examples), not a literal zero; use an
  absolute tolerance.
- Treating the stacking order as free for the B and D matrices: the A
  block only depends on the ply set, but [0/90]s and [0/90]2T share
  the same A block while their B and D matrices differ completely
  (B == 0 against B11 = -2679.14 N m).
- Feeding the equivalent flexural constants a stack with nonzero D16
  or D26: the function assumes a cross-ply or specially orthotropic
  symmetric stack; report the full D matrix instead for a balanced
  angle-ply.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_laminate_bending_stiffness.py

The test covers the [0/90]s worked example (A, B, D blocks and the
four bending terms), the symmetric B == 0 identity on the [0/90]s and
[+45/-45]s stacks, the unsymmetric B coupling and D terms of the
[0/90]2T stack, positive definiteness of the D matrix on all three
worked stacks, the balanced-stack A16/A26 zero versus D16/D26 nonzero
split, the A-consistency of the ABD assembly against the closed form
re-derived in-test, the isotropic reduction and equivalent flexural
constant recovery, the one-shot report keys and determinism, and
ValueError rejection of every non-physical input.

## Compliance

- Standards referenced, not reproduced: FAR-25 is US government work
  (public domain) and CS-25 is a free EASA download; the CLT math is
  common mechanics, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

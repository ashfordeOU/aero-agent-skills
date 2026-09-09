# Wave-48 leaf spec: laminate-bending-stiffness (structures, composites pack)

- Path: skills/structures/composites/laminate-bending-stiffness/
- Pack: structures/composites (13 leaves present at this HEAD:
  adhesive-bonded-joints, cmh17-allowables, composite-bolted-joints,
  composite-repair, delamination-growth, failure-criteria,
  laminate-first-ply-failure, laminate-hygrothermal-response,
  laminate-plate-buckling, laminate-stiffness, peel-stress-bonded-joints,
  sandwich-panels, unidirectional-lamina-micromechanics (wave-47)).
  Wave-48 probe receipt task-5 rank-2 GO (CONDITIONAL); 0 owners
  verified whole-tree at prep and re-verified at spec time: `grep -rl
  "D66" skills/ --include=SKILL.md` returns ONLY
  skills/structures/composites/laminate-plate-buckling/SKILL.md (the
  consumer, no leaf computes D66), and `grep -rilE
  "bending-extension|coupling-stiffness|z-cubed|unsymmetric-laminate"`
  returns ZERO files; the wave-41..47 recon and leaf-plan history has no
  B/D or D-matrix adjudication (the only hits anywhere are this wave-48
  GO's own papers: task-5 receipt, task-3 "D11-feedthrough" which is gnc
  control theory, and this wave's leaf plan).
- Claim fences (quoted from the sibling frontmatter and bodies at this
  HEAD; the CONDITIONAL flag exists because the wave-47 micromechanics
  spec FORBIDDEN TOKENS list assigns abd-matrix and
  classical-lamination-theory vocabulary to laminate-stiffness, so a
  strict reviewer may hold the vein line and decline this as same-vein
  or order an extend-laminate-stiffness. The fences below are the
  pre-emption, point by point):
  - The wave-47 unidirectional-lamina-micromechanics spec, FORBIDDEN
    TOKENS paragraph (wave47-specs file lines 494-499, verbatim at this
    HEAD): "FORBIDDEN TOKENS (belong to siblings): ply-stiffness,
    ply-stiffness-matrix, q11, q12, q22, q66, qbar,
    rotated-ply-stiffness, laminate-a-matrix, laminate-stiffness-matrix,
    abd-matrix, classical-lamination-theory and any claim that computes
    the ply or laminate stiffness from the constants
    (laminate-stiffness owns the
    stiffness assembly; here E1, E2, nu12 and G12 are OUTPUTS produced
    from constituents, never inputs collected)". That assignment was
    written for the micromechanics leaf's description surface, where E1,
    E2, nu12 and G12 ARE the outputs. Read as a global rule it outruns
    the built leaf: laminate-stiffness as BUILT at this HEAD cannot
    express the B and D it is said to own.
  - laminate-stiffness frontmatter description (line 3, verbatim):
    "Use when you must compute the stiffness of a composite laminate
    with classical lamination theory: build the ply stiffness from the
    material constants, rotate it to the ply angle, and assemble the A
    matrix for a symmetric laminate. Produces the ply stiffness, the
    rotated stiffness with coupling terms, and the laminate A matrix
    used in strength and stability analyses." Its workflow (body lines
    42-47) implements only ply_stiffness, rotated_ply_stiffness and
    laminate_a_matrix; its on-disk logic module
    (scripts/laminate_stiffness_logic.py at this HEAD, read in full) has
    exactly those three public functions and its module docstring stops
    at "the symmetric laminate A-matrix sums Q-bar times ply thickness".
    There is NO B function and NO D function anywhere in the leaf, and
    no z-coordinate machinery at all; its tags pin the contract:
    laminate-a-matrix, symmetric-laminate. A symmetric-laminate A-only
    leaf cannot be extended to B/D without changing its contract.
  - laminate-plate-buckling (the consumer that motivates this leaf)
    workflow step 1, body line: "1. Fix the panel inputs: the
    load-direction length a, the width b, and the CLT bending stiffness
    terms D11, D22, D12 and D66 (N m) of the laminate." and its body
    lines: "...with structures/composites/laminate-stiffness for the
    laminate stiffness synthesis that feeds the D terms...", repeated
    in its Related leaves: "structures/composites/laminate-stiffness:
    the in-plane laminate stiffness synthesis that precedes the bending
    terms used here." The consumer fixes the four D terms as GIVEN
    workflow-step-1 INPUTS and ATTRIBUTES their synthesis to
    laminate-stiffness, an expectation the built leaf cannot satisfy:
    the implicit hand-off (the wave-46 GO-2 / wave-47 GO-1 producer
    pattern) that this leaf closes. Nothing in the corpus computes a B
    or D matrix: `grep -inE "d-matrix|D11|ABD" eval/hit1-corpus.yaml`
    returns one block, line 4901: "compute the laminate-plate-buckling
    critical compression load of the composite skin panel from the clt
    d-matrix with half-wave mode minimization", where the d-matrix is a
    given input.
  - laminate-first-ply-failure (symmetric balanced in-plane only, per
    its desc: "recover the mid-plane strains of a symmetric balanced
    laminate from its in-plane compliance") and
    laminate-hygrothermal-response (in-plane CTE/CME vein) neither need
    nor own B or D; neither is touched.
  - Conditional precedent: the wave-47 creep-stress-relaxation leaf was
    flagged CONDITIONAL on a same-vein-suspicion (its constant-stress
    sibling creep-rupture could not express relaxation), the spec fenced
    the seam precisely, and it landed at build. This leaf is the mirror:
    the flagged vein belongs to a sibling that cannot express the seam.
  - Claim restriction that makes the fence hold: this leaf claims the B
    (bending-extension coupling) and D (bending) matrices plus the FULL
    ABD assembly for symmetric AND unsymmetric laminates; it never
    offers a public A-only function, it never claims the symmetric
    laminate A synthesis, and its A sub-block is produced only as the
    top-left block of the full ABD assembly, mathematically identical to
    the sibling's A for the symmetric case by construction (verified
    bitwise against the sibling's own logic module in the anchor below).
- Standards id: far-25 (line 16) and cs-25 (line 27), both present in
  standards-map.yaml (grep-verified at spec time), reference-only: the
  exact pair the in-pack stiffness sibling laminate-stiffness carries at
  this HEAD; cmh-17 (line 281) is also present, the id the D-consumer
  laminate-plate-buckling carries; all STANDARDS-REF, gated false. No
  new id invented. Ledger Standard: far-25 (primary), cs-25 (secondary).
- Family: structures

## Claim

Assemble the full classical-lamination-theory stiffness of a laminate
ply stack and report the bending side the in-pack consumers actually
consume: the bending-extension coupling matrix
B_ij = (1/2) sum_k Qbar_ij,k (z_k^2 - z_{k-1}^2) and the bending matrix
D_ij = (1/3) sum_k Qbar_ij,k (z_k^3 - z_{k-1}^3) over the ply z
coordinates, for symmetric AND unsymmetric laminates, together with the
full ABD block of which they are part
(A_ij = sum_k Qbar_ij,k (z_k - z_{k-1})). Given the ply engineering
constants E1, E2, nu12, G12 and the stack as a bottom-to-top list of
(theta_deg, thickness_m) plies,
each ply is rotated to the laminate axes by the standard closed-form
transformation (the same arithmetic the sibling
structures/composites/laminate-stiffness uses for its rotation) and the
three matrices follow by the exact z, z-squared and z-cubed thickness
integrals with the mid-plane at z = 0. Produces, as the deliverables
this leaf exists for: the B and D matrices of any stack (symmetric or
not); the four bending terms D11, D22, D12 and D66 in N m in the exact
order and notation the consumer structures/composites/
laminate-plate-buckling collects at its workflow step 1, closing the
hand-off that leaf mis-attributes to laminate-stiffness; the B == 0
identity check for mirror-symmetric stacks (the coupling matrix is
identically zero there, to machine precision, because every mirrored
ply pair cancels in the z-squared integral); the coupling magnitude of
unsymmetric stacks (real, nonzero B, e.g. B11 = -2679.14 N m for the
worked [0/90]2T stack); and the equivalent flexural engineering
constants of symmetric stacks with vanishing D16 and D26 (cross-ply and
specially orthotropic), E_bx = 12 (D11 D22 - D12^2) / (D22 h^3) and
analogs, whose isotropic reduction is exact and reproduces D = E
h^3/(12 (1 - nu^2)), the convention laminate-plate-buckling uses in its
own sanity check. The model is deterministic closed-form arithmetic in
SI units on the stack geometry; it is the same identity class as the A
assembly the sibling implements, extended to the z-moment integrals no
leaf implements. Does NOT do: the symmetric-laminate A matrix as a
standalone product, the ply stiffness and rotated stiffness as claimed
products, and any "laminate stiffness synthesis" phrasing
(structures/composites/laminate-stiffness owns the symmetric-laminate
A-only assembly under exactly that desc; this leaf's A sub-block exists
only inside the full ABD assembly and this leaf never exposes an A-only
function); the critical buckling load, half-wave mode minimization and
stability margin of a plate (structures/composites/
laminate-plate-buckling consumes the four D terms this leaf produces);
first-ply failure indices and mid-plane strain recovery of a symmetric
balanced laminate (laminate-first-ply-failure); moisture content, CTE,
CME and hygrothermal strain (laminate-hygrothermal-response); lamina
engineering constants from fiber and matrix constituents, rule of
mixtures, Halpin-Tsai and bound bands
(unidirectional-lamina-micromechanics, wave-47); strength allowables,
coupon statistics,
failure criteria, bolted/adhesive/sandwich/delamination/repair content
(the rest of the pack); material property VALUES and design-value
tables (structures/materials/material-selection, mmpsd-allowables;
properties are inputs, never looked up); and honeycomb-core prediction
(structures/composites/honeycomb-core-micromechanics, wave-48 GO-1).
The per-ply rotated stiffness appears only as the integrand of the
z-moment integrals, never as a claimed output surface; lamina
properties are inputs; no empirical content, no tables, no test data.

## Model (implement exactly)

Pure stdlib (math only), closed form, deterministic, no RNG, no tables.
Module constants: none. Every relation is the published CLT closed form
(Jones, Mechanics of Composite Materials, 2nd ed., ch. 2; Herakovich,
Mechanics of Fibrous Composites, ch. 5) on the given stack. SI units
throughout: E1, E2, G12 in Pa, ply thickness in m, A in N/m, B in N,
D in N m, matching the laminate-stiffness SI convention.

Defining relations (pin these exactly; every function derives from
them):
- Ply stiffness in material axes from the engineering constants:
  nu21 = nu12 * E2 / E1, denom = 1 - nu12 * nu21,
  Q11 = E1 / denom, Q22 = E2 / denom, Q12 = nu12 * E2 / denom,
  Q66 = G12. (Same closed form the sibling's ply_stiffness implements;
  here it is internal arithmetic, never a public product.)
- Rotation to the laminate axes for a ply at theta_deg: with
  c = cos(theta), s = sin(theta), c2 = c^2, s2 = s^2, c4 = c2^2,
  s4 = s2^2, s2c2 = s2 * c2:
  Qbar11 = Q11 c4 + 2 (Q12 + 2 Q66) s2c2 + Q22 s4
  Qbar22 = Q11 s4 + 2 (Q12 + 2 Q66) s2c2 + Q22 c4
  Qbar12 = (Q11 + Q22 - 4 Q66) s2c2 + Q12 (c4 + s4)
  Qbar66 = (Q11 + Q22 - 2 Q12 - 2 Q66) s2c2 + Q66 (c4 + s4)
  Qbar16 = ((Q11 - Q12 - 2 Q66) c2 - (Q22 - Q12 - 2 Q66) s2) c s
  Qbar26 = ((Q11 - Q12 - 2 Q66) s2 - (Q22 - Q12 - 2 Q66) c2) c s
  written in the arithmetic order of the sibling's
  rotated_ply_stiffness so cross-module results are bit-comparable.
- Stack geometry: plies are listed bottom to top as (theta_deg,
  thickness_m); total thickness h = sum of the ply thicknesses; the
  interface coordinates z_0 = -h/2, z_k = z_{k-1} + t_k put the
  mid-plane at z = 0 and ply k occupies [z_{k-1}, z_k].
- The ABD z-moment integrals over the stack (the receipt's published
  anchor):
  A_ij = sum_k Qbar_ij,k (z_k - z_{k-1})
  B_ij = (1/2) sum_k Qbar_ij,k (z_k^2 - z_{k-1}^2)
  D_ij = (1/3) sum_k Qbar_ij,k (z_k^3 - z_{k-1}^3)
  Six-component tuples in the in-pack index order (11, 12, 16, 22, 26,
  66), the order the sibling's rotated_ply_stiffness and
  laminate_a_matrix return.
- Symmetric-stack identity: when the ply sequence is mirror-symmetric
  about the mid-plane (angles and thicknesses), every ply pairs with a
  mirror ply of equal Qbar whose z-squared integral cancels it, so
  B_ij = 0 identically in exact arithmetic; in floating point the
  residue is machine precision (real anchor: max |B_ij| = 8.5265e-14 N m
  for the [0/90]s stack whose D11 is 1.67 N m, and 2.2737e-13 N m for
  the [+45/-45]s stack).
- Balanced-stack identity: balance (every +theta ply mirrored by a
  -theta ply) removes A16 and A26 but NOT D16 and D26; a balanced
  symmetric angle-ply has A16 = A26 = 0 (real anchor: exactly 0.0) while
  D16 = D26 = 0.3349 N m (real anchor) for the [+45/-45]s stack. This
  is why the D terms cannot be read off the symmetric-A pattern and must
  be computed by the z-cubed integral.
- Isotropic reduction: a single isotropic layer of E, nu, thickness h
  gives D11 = E h^3 / (12 (1 - nu^2)), D12 = nu D11, D66 = G h^3 / 12,
  the convention laminate-plate-buckling uses in its sanity check (its
  worked example: E = 70 GPa, nu = 0.3, h = 2 mm gives D = 51.28 N m;
  real anchor D11 = 51.2820512821 N m below).
- Equivalent flexural (bending) engineering constants of a symmetric
  stack with D16 = D26 = 0 (cross-ply and specially orthotropic stacks;
  documented scope boundary, the balanced angle-ply with its nonzero
  D16/D26 is reported as its full D matrix instead):
  E_bx = 12 (D11 D22 - D12^2) / (D22 h^3),
  E_by = 12 (D11 D22 - D12^2) / (D11 h^3),
  nu_bxy = D12 / D22, G_bxy = 12 D66 / h^3, with h the total thickness.
  The isotropic reduction is exact: a single isotropic layer returns
  E_bx = E and G_bxy = G = E / (2 (1 + nu)) (real anchor: 70.0 GPa and
  26.9231 GPa recovered within 1e-9 relative).

Functions (every public function validates its inputs identically;
ValueError, never assert; real message prefixes quoted in the Worked
example):
- ply_rotated_stiffness(e1, e2, nu12, g12, theta_deg) ->
  (Qbar11, Qbar12, Qbar16, Qbar22, Qbar26, Qbar66): the per-ply rotated
  stiffness, the integrand of the integrals below. ValueErrors: e1, e2
  or g12 not a positive number ("modulus E1 must be a positive number,
  got ..."), nu12 not in [0, 1) ("poisson ratio nu12 must be in [0, 1),
  got ..."), any boolean argument.
- b_coupling_matrix(plies, e1, e2, nu12, g12) ->
  (B11, B12, B16, B22, B26, B66): the bending-extension coupling
  matrix. ValueErrors of every input as above plus an empty ply list
  ("laminate must have at least one ply") and any ply thickness at or
  below zero or boolean ("ply thickness must be a positive number, got
  ...").
- d_bending_matrix(plies, e1, e2, nu12, g12) ->
  (D11, D12, D16, D22, D26, D66): the bending matrix. Same ValueErrors.
- abd_stiffness_matrices(plies, e1, e2, nu12, g12) ->
  {"a": (A11, A12, A16, A22, A26, A66), "b": (...), "d": (...)}: the
  full ABD assembly for symmetric AND unsymmetric laminates. The A block
  is returned ONLY here, as part of the full assembly; there is no
  public A-only function in this module. Same ValueErrors.
- laminate_bending_terms(plies, e1, e2, nu12, g12) ->
  (D11, D22, D12, D66) in N m: the four bending terms in the order and
  notation the consumer laminate-plate-buckling fixes at its workflow
  step 1. Same ValueErrors.
- equivalent_flexural_constants(d11, d22, d12, d66, t_total) ->
  (E_bx, E_by, G_bxy, nu_bxy): the equivalent flexural constants above.
  ValueErrors: any of d11, d22, d66 not a positive number ("bending
  stiffness D11 must be a positive number, got ..."), t_total not a
  positive number ("total thickness must be a positive number, got
  ..."), and a non-positive-definite pair with d11 * d22 - d12^2 at or
  below zero ("the bending stiffness terms are not positive definite,
  got D11 ..., D22 ..., D12 ..."). Documented scope: D16 = D26 = 0
  stacks; the function takes only the four terms and cannot itself
  detect D16/D26.
- laminate_bending_report(plies, e1, e2, nu12, g12) -> dict: the
  one-shot report. Keys: "a", "b", "d" (the three six-tuples), "d11",
  "d22", "d12", "d66" (scalars), "t_total" (m), "b_max_abs"
  (max |B_ij|, N m, the coupling magnitude). Same ValueErrors.

Identities to test (closed form, checkable without the builder
module):
- B == 0 identically (to machine precision) for every mirror-symmetric
  stack: [0/90]s and [+45/-45]s anchors give max |B_ij| of 8.5265e-14
  and 2.2737e-13 N m respectively; assert below 1e-9 N m absolute (the
  strongest fence: the symmetric-laminate identity the sibling's A-only
  world cannot even state).
- B nonzero for unsymmetric stacks: the [0/90]2T anchor gives
  max |B_ij| = 2679.14031429 N m with B11 = -B22, coupling that no
  symmetric-A assembly can represent.
- D positive definite for every sane layup: the leading principal
  minors of the symmetric 3x3 D matrix are all positive for the [0/90]s,
  [0/90]2T and [+45/-45]s anchors, the last with D16 = D26 = 0.3349 N m
  nonzero.
- A-consistency with the sibling for the symmetric case: the A block of
  abd_stiffness_matrices on the [0/90]s stack equals (a) the sibling's
  own laminate_a_matrix output applied to the same stack and constants,
  imported at anchor time: real max relative difference 0.0 (bitwise
  identical), and (b) the closed form A_ij = sum_k Qbar_ij,k t_k, which
  the sibling's function implements, within 1e-9 relative.
- A16 = A26 = 0 exactly for the balanced symmetric [0/90]s and
  [+45/-45]s stacks while D16/D26 vanish only for the cross-ply and are
  nonzero for the balanced angle-ply (real anchors: exactly 0.0 for A16
  and A26, D16 = 5.4940e-19 vs 0.334892539286 N m).
- Isotropic reduction: single isotropic layer, D11 equals
  E h^3 / (12 (1 - nu^2)) within 1e-9 relative (real anchor relative
  difference 1.3856e-16), and equivalent_flexural_constants recovers E,
  G and nu within 1e-9 relative.
- Determinism: identical outputs run to run, identical under both
  interpreters; no randomness; no imports beyond math.

## Worked example

AS4/3501-6 class carbon/epoxy ply constants (the textbook carbon/epoxy
of Jones and Herakovich): E1 = 181.0 GPa, E2 = 10.3 GPa,
G12 = 7.17 GPa, nu12 = 0.28, ply thickness t = 0.000125 m (0.125 mm).

All values below are REAL outputs of the prep anchor
/tmp/w48spec/anchor_laminate_bending.py (pure stdlib, math only,
closed form, exit 0, no RNG), run once and quoted as printed, then
re-verified byte-identical under /usr/bin/python3 3.9.6 and the 3.13.12
interpreter. The anchor imports the sibling logic module from ~/AeroSkills
at run time for the A-consistency cross-check; all internal identity
asserts pass.

- Symmetric [0/90]s, plies (0, 90, 90, 0) x 0.125 mm, h = 0.5 mm:
  A1 = (48039324.3936, 1448462.22217, 1.054844272e-10, 48039324.3936,
  2.51931606109e-09, 3585000) N/m. A11 = 48.0393243936 MN/m: the two
  0-degree plies carry Q11 = 181.811e9 Pa class stiffness and the two
  90-degree plies the transverse stiffness, summed over h.
  B1 = (0, 0, 0, 8.52651282912e-14, 0, 0) N m, max |B1_ij| =
  8.52651282912e-14 N m: the B == 0 identity holds to machine
  precision, fourteen orders of magnitude below the D scale (the only
  nonzero component, B22, is a floating-point cancellation residue of
  the z-squared integral, never an exact-float equality target).
  D1 = (1.67060433677, 0.0301762962953, 5.49398058332e-19,
  0.331034179627, 1.31214378182e-17, 0.0746875) N m; D16 and D26 vanish
  (5.4940e-19 and 1.3121e-17 N m). laminate_bending_terms =
  (1.67060433677, 0.331034179627, 0.0301762962953, 0.0746875) N m:
  D11 = 1.67060433677, D22 = 0.331034179627, D12 = 0.0301762962953,
  D66 = 0.0746875, the four terms laminate-plate-buckling takes as given
  at its step 1. D1 positive definite: True.
  Equivalent flexural constants (D16 = D26 = 0): E_bx = 160.113939519
  GPa, E_by = 31.7269538028 GPa, G_bxy = 7.17 GPa,
  nu_bxy = 0.0911576451995: the 0.5 mm cross-ply bends like a
  160.1 GPa homogeneous plate along the 0-degree direction and a
  31.7 GPa plate across it, with the shear modulus recovered exactly
  (12 D66 / h^3 = 7.17 GPa = G12, because 0/90 plies carry no Qbar16
  shear coupling).
  A-consistency vs the sibling: the sibling's laminate_a_matrix applied
  to the same stack and constants returns the same A1 tuple with max
  relative difference 0.0 (bitwise identical to float precision; the
  A block is the same closed form the sibling owns, here produced only
  inside the full assembly).
- Unsymmetric [0/90]2T, plies (0, 90, 0, 90) x 0.125 mm, h = 0.5 mm:
  A2 = A1 exactly (the A block depends only on the ply set, not the
  stacking order). B2 = (-2679.14031429, 0, 6.59277669998e-15,
  2679.14031429, 1.57457253818e-13, 0) N m: B11 = -2679.14031429 N m
  and B22 = +2679.14031429 N m, the real bending-extension coupling of
  the unsymmetric stack (max |B2_ij| = 2679.14031429 N m, three orders
  above the D scale: a bending load on this stack produces real in-plane
  strain, the physical effect no symmetric-laminate A can describe).
  D2 = (1.0008192582, 0.0301762962953, 2.19759223333e-18,
  1.0008192582, 5.24857512727e-17, 0.0746875) N m; the [0/90]2T bends
  softer than the [0/90]s (D11 = 1.0008192582 vs 1.67060433677 N m)
  because the symmetric stack puts the stiff 0-degree plies at the
  faces. D2 positive definite: True.
- Symmetric balanced angle-ply [+45/-45]s, plies (+45, -45, -45, +45)
  x 0.125 mm, h = 0.5 mm:
  A3 = (28328893.3079, 21158893.3079, 0, 28328893.3079, 0, 23295431.0857)
  N/m with A16 = A26 = 0 exactly: balance removes the in-plane coupling.
  B3 max |B3_ij| = 2.27373675443e-13 N m: the B == 0 identity holds
  again for this symmetric stack. D3 = (0.590185277247,
  0.440810277247, 0.334892539286, 0.590185277247, 0.334892539286,
  0.485321480952) N m with D16 = D26 = 0.334892539286 N m NONZERO:
  balance does not remove the bending coupling, so the D terms of an
  angle-ply cannot be inferred from its symmetric-A pattern; this is the
  exact reason the z-cubed integral is computed here. D3 positive
  definite 3x3 with D16 != 0: True.
- Isotropic reduction, E = 70 GPa, nu = 0.3, h = 0.002 m, theta = 0:
  A4 = (153846153.846, 46153846.1538, 0, 153846153.846, 0,
  53846153.8462) N/m; D4 = (51.2820512821, 15.3846153846, 0,
  51.2820512821, 0, 17.9487179487) N m. Classic D = E h^3 /
  (12 (1 - nu^2)) = 51.2820512821 N m; relative difference vs D11 =
  1.38555833473e-16, matching the 51.28 N m value of the
  laminate-plate-buckling sanity check for the same E, nu and
  thickness.
  equivalent_flexural_constants recovers E_bx = 70 GPa,
  G_bxy = 26.9230769231 GPa and nu_bxy = 0.3 exactly (within 1e-9
  relative).
- Real ValueError messages (module output, quoted as raised): a
  negative ply thickness raises "ply thickness must be a positive
  number, got -0.000125"; a zero ply thickness raises "... got 0.0"; a
  boolean ply thickness raises "ply thickness must be a positive number,
  got True"; a zero E1 raises "modulus E1 must be a positive number, got
  0.0"; nu12 = 1.5 raises "poisson ratio nu12 must be in [0, 1), got
  1.5"; an empty stack raises "laminate must have at least one ply"; a
  zero total thickness raises "total thickness must be a positive
  number, got 0.0"; a non-positive-definite D pair raises "the bending
  stiffness terms are not positive definite, got D11 1.0, D22 1.0, D12
  2.0".
- The anchor's internal asserts (the B == 0 identities within 1e-9 N m
  absolute, the nonzero unsymmetric coupling, all three
  positive-definiteness checks including the 3x3 with D16 nonzero, the
  isotropic reduction within 1e-9 relative, the flexural recovery, the
  vanish of A16/A26, the A-consistency with the sibling within 1e-9
  relative, the report determinism, every ValueError) all pass and the
  anchor exits 0, byte-identical under both interpreters.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
/tmp/w48spec/anchor_laminate_bending.py (stdlib math, closed form, exit
0, no randomness, identical under both interpreters).

## Validation list (contract test must include)

1. Worked example asserts within 1e-6 relative on the [0/90]s stack:
   abd_stiffness_matrices([(0.0, 0.000125), (90.0, 0.000125), (90.0,
   0.000125), (0.0, 0.000125)], 181.0e9, 10.3e9, 0.28, 7.17e9)["d"]
   gives D11 = 1.67060433677, D22 = 0.331034179627, D12 =
   0.0301762962953, D66 = 0.0746875 (N m), and ["a"] gives A11 =
   48039324.3936, A22 = 48039324.3936, A12 = 1448462.22217, A66 =
   3585000 (N/m); laminate_bending_terms returns (1.67060433677,
   0.331034179627, 0.0301762962953, 0.0746875).
2. Symmetric B == 0 identity within an absolute 1e-9 N m tolerance (not
   exact-float equality; the residue is a machine cancellation):
   max |b_coupling_matrix| <= 1e-9 for the [0/90]s stack (real anchor
   8.52651282912e-14) and for the [+45/-45]s stack (real anchor
   2.27373675443e-13). This identity is the strongest fence of the
   CONDITIONAL claim: a symmetric stack couples nothing, a claim the
   A-only sibling cannot state.
3. Unsymmetric coupling: on [0/90]2T, max |B_ij| = 2679.14031429 N m
   within 1e-6 relative, B11 = -B22 within 1e-6 relative of each other
   in magnitude, and D11 = D22 = 1.0008192582 N m within 1e-6 relative.
4. Positive definiteness: the leading principal minors of the symmetric
   3x3 D matrix are all positive for the [0/90]s, [0/90]2T and
   [+45/-45]s worked stacks, including the 3x3 case with D16 = D26 =
   0.334892539286 N m nonzero (real anchor: True in all three).
5. Balanced angle-ply coupling split: on [+45/-45]s, A16 and A26 are
   0.0 exactly (bitwise, the balanced cancellation) while D16 and D26
   equal 0.334892539286 N m within 1e-6 relative; on [0/90]s, D16 and
   D26 are below 1e-9 N m absolute.
6. A-consistency with laminate-stiffness for the symmetric case: the A
   block of the full assembly equals the closed form A_ij = sum_k
   Qbar_ij,k t_k (the sibling's laminate_a_matrix formula) within 1e-9
   relative at the worked [0/90]s inputs, recomputed in-test with
   ply_rotated_stiffness; at anchor time the sibling's actual module was
   imported and returned max relative difference 0.0 (bitwise
   identical). The contract test never imports across leaves; it
   re-derives the sibling's closed form in-test.
7. Isotropic reduction: a single ply (0.0, 0.002) with E1 = E2 = 70.0e9,
   nu12 = 0.3, G12 = 70.0e9 / (2 (1 + 0.3)) gives D11 =
   51.2820512821 N m within 1e-9 relative of
   70.0e9 * 0.002^3 / (12 (1 - 0.3^2)), and
   equivalent_flexural_constants(D11, D11, 0.3 * D11, D66, 0.002)
   returns E_bx = 70.0e9, G_bxy = 26923076923.076923 and nu_bxy = 0.3
   within 1e-9 relative.
8. Equivalent flexural constants on [0/90]s: E_bx = 160.113939519e9,
   E_by = 31.7269538028e9, G_bxy = 7.17e9, nu_bxy = 0.0911576451995
   within 1e-6 relative; the one-shot laminate_bending_report on the
   same stack reports "b_max_abs" = 8.52651282912e-14 and the key set
   {"a", "b", "d", "d11", "d22", "d12", "d66", "t_total",
   "b_max_abs"}.
9. ValueErrors raise from the named public function with the real
   message prefixes quoted in the Worked example: a negative, zero or
   boolean ply thickness ("ply thickness must be a positive number, got
   ..."), a zero or boolean modulus ("modulus E1 must be a positive
   number, got ..."), nu12 outside [0, 1) ("poisson ratio nu12 must be
   in [0, 1), got ..."), an empty stack ("laminate must have at least
   one ply"), a non-positive t_total ("total thickness must be a
   positive number, got ..."), and a non-positive-definite D pair ("the
   bending stiffness terms are not positive definite, got ...").
10. Determinism: two consecutive one-shot calls return identical dicts;
    no randomness anywhere; no imports beyond math; the module has no
    constants beyond the published closed forms.
11. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere, with the B == 0 identity
    asserted as an absolute tolerance, never as equality to 0.0 (the
    real residue 8.52651282912e-14 is a cancellation artifact). Test
    passes under BOTH interpreters (/usr/bin/python3 3.9.6 and
    ~/.pyenv/versions/3.13.12/bin/python3).
12. Run the deterministic contract test offline (no network); it exits
    0. All worked-example numbers above were verified byte-identical
    under both interpreters before spec time.

## Corpus fragment (eval/hit1-wave48-laminate-bending-stiffness.yaml)

Query 1 (copy verbatim from the probe receipt gate (e)):
  "compute the laminate d-matrix bending stiffnesses D11 D22 D12 and
  D66 of the 8-ply carbon-epoxy stack from the rotated ply stiffnesses
  and the ply z-coordinate z-cubed thickness integrals by classical
  lamination theory, the laminate-bending-stiffness inputs the laminate
  plate buckling analysis takes as given"
  -> top1 laminate-bending-stiffness 37.0, top2 laminate-plate-buckling
  24.0, margin 13.0 (strong)
  intent: "structures/composites; laminate-bending-stiffness: the D11,
  D22, D12 and D66 bending terms of the 8-ply carbon-epoxy stack by the
  z-cubed thickness integrals of the rotated ply stiffnesses over the
  ply z coordinates, producing exactly the bending terms the laminate
  plate buckling analysis fixes as its given inputs"
  expected_skill: "structures/composites/laminate-bending-stiffness"
Query 2 (copy verbatim from the probe receipt gate (e)):
  "assemble the full clt stiffness of the unsymmetric laminate stack:
  the in-plane a-matrix, the bending-extension coupling b-matrix and
  the bending d-matrix from the ply stack geometry, and the equivalent
  laminate bending stiffness of the symmetric angle-ply for the
  laminate-bending-response check"
  -> top1 laminate-bending-stiffness 24.0, top2 sandwich-panels 11.0,
  margin 13.0 (strong)
  intent: "structures/composites; laminate-bending-stiffness: the full
  ABD assembly of the unsymmetric stack with the bending-extension
  coupling B and bending D matrices from the ply stack geometry, and
  the equivalent flexural (bending) engineering constants of the
  symmetric balanced stack for the bending-response check"
  expected_skill: "structures/composites/laminate-bending-stiffness"
Task ids: w48-laminate-bending-stiffness-1 and -2. Prep greps (re-run
fresh at spec time): `grep -rl "D66" skills/ --include=SKILL.md`
returns only laminate-plate-buckling, `grep -rilE
"bending-extension|coupling-stiffness|z-cubed|unsymmetric-laminate"`
returns zero files, and the only d-matrix corpus block (line 4901)
treats the d-matrix as a given input, so the queries are
collision-free; the existing laminate corpus tasks route on the
symmetric-A and buckling vocabulary of the sibling leaves and do not
overlap this B/D surface. Add one routing bullet at build time to
laminate-plate-buckling's Related leaves, whose current line
("laminate-stiffness: the in-plane laminate stiffness synthesis that
precedes the bending terms used here") mis-attributes the D synthesis
to laminate-stiffness: name this leaf as the producer of the B/D/ABD
terms and laminate-stiffness as the in-plane symmetric-A synthesis
(wave-45 routing-line precedent).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must assemble the full classical
lamination theory stiffness of a composite laminate stack for the
bending and coupling response:" and include the outputs in the Claim
order (the bending-extension coupling matrix B by the z-squared integral
and the bending matrix D by the z-cubed integral over the ply stack
z coordinates, the full ABD stiffness matrices for symmetric and
unsymmetric laminates, the D11 D22 D12 and D66 bending terms the
laminate plate buckling analysis takes as given inputs, the exact
zero-coupling identity for symmetric stacks, the coupling magnitude of
unsymmetric stacks, and the equivalent flexural engineering constants
of symmetric stacks with vanishing D16 and D26), then close with the
Trigger list. Never claim the symmetric-laminate A assembly, the phrase
"laminate A matrix" as a product, or "laminate stiffness" as a generic
product noun (laminate-stiffness owns the in-plane symmetric-A
synthesis under that name); the per-ply rotated stiffness is the
integrand of the z-moment integrals, never a claimed output. First tag:
laminate-bending-stiffness. Metadata tags EXACTLY as the probe receipt
gate (f) lists them, nothing else: clt-abd-matrices, laminate-d-matrix,
bending-extension-coupling, unsymmetric-laminate-analysis,
laminate-bending-response, d11-d22-d12-d66,
equivalent-laminate-bending-stiffness. 50-150 words, <=1000 chars, no
em dash, no content-policy sweep term, action verb present. Recommended
wording (138 words, 954 chars, verified at spec time):

"Use when you must assemble the full classical lamination theory
stiffness of a composite laminate stack for the bending and coupling
response: compute the bending-extension coupling matrix B and the
bending matrix D by the z-squared and z-cubed thickness integrals over
the ply z coordinates, the full ABD stiffness matrices for symmetric
and unsymmetric laminates, the D11 D22 D12 and D66 bending terms the
laminate plate buckling analysis takes as given inputs, the exact
zero-coupling identity for symmetric stacks, the coupling magnitude of
unsymmetric stacks, and the equivalent flexural engineering constants
of symmetric stacks with vanishing D16 and D26. Produces the coupling
and bending matrices, the four bending terms and the flexural constants
in SI units. Trigger: laminate bending stiffness, bending-extension
coupling, laminate d matrix, abd matrices, unsymmetric laminate
analysis, d11 d22 d12 d66, equivalent laminate bending stiffness."

FORBIDDEN TOKENS (belong to siblings): the symmetric-laminate A-only
assembly, "laminate A matrix" as a produced output, "laminate
stiffness" as a generic product noun, ply-stiffness,
rotated-ply-stiffness, q11, q12, q22, q66, qbar and any claim that
produces the ply stiffness or the rotated stiffness as a deliverable
or assembles the A matrix of a symmetric laminate as a standalone
product (laminate-stiffness owns the in-plane symmetric-A synthesis;
here the per-ply rotation is internal integrand arithmetic only and
the A sub-block appears solely inside the full ABD assembly);
buckling, critical-load, plate-buckling, buckling-mode
(laminate-plate-buckling consumes D11,
D22, D12, D66 as given inputs and owns the critical load verdict);
first-ply-failure, failure-index, tsai-wu, tsai-hill, max-stress
(failure-criteria, laminate-first-ply-failure); moisture-content, cte,
cme, hygrothermal-strain (laminate-hygrothermal-response); halpin-tsai,
rule-of-mixtures, fiber-volume-fraction, bound-band and any
constituent-to-lamina prediction (unidirectional-lamina-micromechanics,
wave-47); honeycomb, core-shear, face-wrinkling, sandwich
(honeycomb-core-micromechanics, wave-48 GO-1, and sandwich-panels);
bearing, bypass, bolt, adhesive, peel, delamination, repair (the
remaining pack leaves); a-basis, b-basis, allowables, coupon statistics
and design-value tables (cmh17-allowables,
structures/materials/material-selection, mmpsd-allowables); and the
bare single words a-matrix, b-matrix, d-matrix, laminate, stiffness,
coupling, bending, ply, stack, symmetric, unsymmetric as standalone
metadata tags (use only the hyphenated compounds listed above). The
symmetric-stack B == 0 result and the unsymmetric B coupling are this
leaf's own identity products, fenced in the Claim above; FAR-25 and
CS-25 frame the certification context only, never reproduced verbatim.

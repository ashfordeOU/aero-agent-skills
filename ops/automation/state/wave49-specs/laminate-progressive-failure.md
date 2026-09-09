# Wave-49 leaf spec: laminate-progressive-failure (structures, composites pack)

- Path: skills/structures/composites/laminate-progressive-failure/
- Pack: structures/composites (15 leaves present at this HEAD:
  adhesive-bonded-joints, cmh17-allowables, composite-bolted-joints,
  composite-repair, delamination-growth, failure-criteria,
  honeycomb-core-micromechanics (wave-48), laminate-bending-stiffness
  (wave-48), laminate-first-ply-failure, laminate-hygrothermal-response,
  laminate-plate-buckling, laminate-stiffness, peel-stress-bonded-joints,
  sandwich-panels, unidirectional-lamina-micromechanics (wave-47)).
  Wave-49 probe receipt task-2 rank-1 GO (STRONG), never adjudicated in
  any wave-41..48 structures-side receipt; 0 owners verified whole-tree
  at prep and re-verified at spec time: `grep -rilE
  "progressive.{0,30}fail|ply.discount|last.ply" skills/
  --include=SKILL.md` returns ZERO files at this HEAD (1577d0ff), the
  only wider-token hit (`post.?fpf`) being the sibling
  laminate-first-ply-failure's own disclaimer line 132 ("post-FPF load
  redistribution and delamination growth are different leaves"), and
  `grep -icE "progressive.{0,30}fail|ply.discount|last.ply|post.?fpf"
  eval/hit1-corpus.yaml` returns 0 of 1326 task blocks while the
  owned first-ply slice counts 9. The adjudication-history scan over ALL
  of ops/automation/state (every wave4*-specs and wave4*-leaf-plan)
  returns ZERO hits for the progressive / ply-discount / last-ply /
  post-FPF vocabulary: the multi-event march past first-ply failure has
  no owner anywhere.
- Claim fences (quoted verbatim from the sibling frontmatter and bodies
  at this HEAD; the seam this leaf closes is named by the nearest
  sibling's own Pitfalls, and the wave-33 FPF spec's FORBIDDEN TOKENS
  list assigns the post-FPF vocabulary to nobody):
  - laminate-first-ply-failure frontmatter description (line 3,
    verbatim): "Use when you must compute the first-ply-failure load of
    a composite laminate: recover the mid-plane strains of a symmetric
    balanced laminate from its in-plane compliance under applied load
    resultants, transform the strains to each ply material axis,
    compute the per-ply Tsai-Wu failure index, and return the critical
    ply. Produces the mid-plane strains, the per-ply failure indices,
    the critical ply, the first-ply-failure load scale factor, the FPF
    load resultant, and the reserve factor. Trigger: first-ply-failure
    load, first ply failure, critical ply, tsai-wu failure index,
    reserve factor, mid-plane strain recovery, in-plane load resultant,
    symmetric balanced laminate, quasi-isotropic laminate, laminate
    failure envelope, FPF load, per-ply failure index, composite
    laminate strength." Its metadata tags (line 18, verbatim):
    [laminate-first-ply-failure, tsai-wu-failure-index,
    first-ply-failure-load, critical-ply, reserve-factor,
    midplane-strain-recovery, laminate-failure-envelope]. Its Domain
    quick reference pins the linearized convention that fences this
    leaf's event definition (lines 59-62, verbatim): "First ply
    failure: the ply with the largest index is critical; the FPF scale
    factor is k* = 1 / max(FI) and the FPF load resultant for the
    uniaxial case is k* Nx, with the reserve factor equal to k*. The
    index is quadratic in stress, so k* = 1 / FI is a linearized
    reserve factor; it is exact at the failure boundary itself and is
    the convention of this leaf." Its Pitfalls (lines 131-133,
    verbatim): "Treating FPF as ultimate laminate failure: first-ply
    failure is the first ply event under the Tsai-Wu convention;
    post-FPF load redistribution and delamination growth are different
    leaves." The sibling's Verification (lines 138-141) supplies the
    unidirectional identity this leaf reuses: "a [0]8 laminate under Nx
    fails in the fiber direction; with sigma1 = Nx/t and Xt = Xc the
    index is (sigma1/Xt)^2, so at sigma1 = Xt the index is 1.0 and k* =
    Xt/sigma1 = 1. The 0-ply stress recovered from the strain equals E1
    ex exactly."
  - delamination-growth Pitfalls (lines 114-118, verbatim):
    "Comparing ply-level stress indices to a fracture criterion: this
    leaf assesses delamination onset by energy release rate at the
    laminate level; stress-based ply failure (Tsai-Wu, max stress)
    belongs to failure-criteria, and metallic Paris-law growth to
    damage-tolerance/crack-growth." The energy-based identity is a
    different failure class; the stress-based multi-event march is this
    leaf's.
  - failure-criteria frontmatter description (line 3, verbatim): "Use
    when you must evaluate a composite lamina against strength failure
    criteria: compute the Tsai-Wu, Tsai-Hill, and max-stress failure
    indices from the in-plane stresses and the ply allowables, and
    return the failure verdict. Produces each criterion index, the
    governing criterion, and the pass or fail verdict for the ply
    stress state. Trigger: lamina failure, tsai wu, tsai hill, max
    stress, failure index, composite ply strength, in plane stress."
    Its tags (line 16, verbatim): [failure-criteria, tsai-wu,
    tsai-hill, max-stress, failure-index, lamina, ply-allowables,
    composite-lamina]. Single-ply index from GIVEN stresses only; no
    laminate assembly, no stiffness evolution.
  - The wave-33 laminate-first-ply-failure spec, FORBIDDEN TOKENS
    paragraph (wave33-specs file lines 141-149, verbatim at this
    HEAD): "FORBIDDEN TOKENS (belong to siblings): ABD matrix, ply
    stiffness, laminate stiffness matrix assembly (laminate-stiffness);
    hygrothermal, moisture, coefficient of thermal expansion
    (laminate-hygrothermal-response); delamination, strain energy
    release rate (delamination-growth); single-ply failure from given
    stresses (failure-criteria); thermal stress
    (thermal-stress-analysis). The tokens "first ply failure",
    "critical ply", "reserve factor", "failure index" are this leaf's
    own (failure-criteria owns the index formula at lamina level; this
    leaf owns the laminate-level FPF search)." The progressive /
    post-FPF / last-ply / ply-discount vocabulary is assigned to
    NOBODY by that fence, which is the open seam this leaf closes.
  - laminate-stiffness and laminate-bending-stiffness (wave-48)
    assemble the in-plane A and the B/D bending blocks only; neither
    carries any strength or stiffness-evolution content (the wave-48
    laminate-bending-stiffness spec pins its Claim to the ABD
    z-moment integrals and nothing past them).
  - Fence that makes the seam hold: this leaf computes the multi-event
    march AFTER the first event. The first event itself (the critical
    ply, the per-ply Tsai-Wu indices and the FPF load) is computed with
    the sibling's exact index machinery (same closed form, same
    A-inverse strain recovery) but under this leaf's event convention:
    an event is the load scale at which a ply index ACTUALLY reaches
    unity, which is the positive root of the quadratic
    FI(lambda) = 1, not the sibling's documented linearized scale
    k* = 1 / max(FI). The difference is real and measurable (real
    anchor, T300/5208 QI stack: sibling linearized FPF load 319.4818
    N/mm vs this leaf's quadratic-exact first event 276.1190 N/mm, a
    factor 1.15704) and is fenced below under Claim and Model. This
    leaf never offers the linearized reserve-factor reporting, never
    claims the FPF load by k* as a product, and never reproduces the
    sibling's mid-plane-strain-recovery surface as a deliverable.
- Standards id: cmh-17 (line 281) and far-25 (line 16), both present in
  standards-map.yaml (grep-verified at spec time), reference-only: the
  exact pair the in-pack strength sibling laminate-first-ply-failure
  carries at this HEAD (its frontmatter standards block lists cmh-17
  and far-25, STANDARDS-REF, gated false); cmh-17 is the natural
  primary id (CMH-17 vol. 3 laminate-strength methodology conventions),
  far-25 the certification framing. No new id invented. Ledger
  Standard: cmh-17 (primary), far-25 (secondary).
- Family: structures

## Claim

Compute the progressive failure of a symmetric balanced composite
laminate past its first-ply failure by the ply-discount method: given
the ply stack, the ply engineering constants E1, E2, nu12, G12, the
Tsai-Wu allowables (Xt, Xc, Yt, Yc, S) and the applied in-plane load
resultant direction, recover the mid-plane strains from the A-inverse
compliance, transform to each ply material axis, compute the per-ply
Tsai-Wu index (the sibling's exact closed form) and march the load
event by event: at each event the ply group whose index reaches unity
fails, its stiffness is discounted (matrix-mode failure zeroes E2, G12
and nu12 of that ply while E1 is retained, so the failed ply keeps
carrying fiber-direction load as a tape and can later fail again in
fiber mode; fiber-mode failure zeroes E1 as well), the in-plane
laminate stiffness is reassembled from the degraded plies, the load
resultant is reapplied and the march continues until the last-ply
failure, at which no load-bearing stiffness remains and the laminate
cannot carry further load. Produces the failure sequence (each event's
load, failed plies and matrix or fiber modes), the degraded laminate
stiffness (A block, N/mm) after each event, the first-ply-failure load
as the first event of the march (index at unity, the convention this
leaf pins below), the ultimate-laminate-load (the last-ply-failure
event load), the post-FPF reserve factor (ultimate / FPF) of the
load-redistributed march, and an optional strain-limit termination
(maximum active-ply fiber strain) for marches that terminate before a
ply event. The model is deterministic closed-form arithmetic in the
MPa / N-mm / mm unit convention of the sibling first-ply-failure leaf,
pure stdlib, no test-data fitting. It is the same identity class as the
sibling's first-ply search (CLT strain recovery, per-ply Tsai-Wu
index), extended to the stiffness-evolution march no leaf implements.
Does NOT do: the first-ply-failure search as a standalone product with
the critical-ply, reserve-factor and laminate-failure-envelope
reporting under the sibling's linearized k* = 1 / max(FI) convention
(laminate-first-ply-failure owns the first event under that documented
convention; here the first event is reported only as the first step of
the march at index unity, never by the linearized scale); the lamina
failure-index formula evaluated from given stresses, the Tsai-Hill or
max-stress criteria and the pass or fail verdict of a single ply
(failure-criteria owns the lamina-level criteria contract, tags
composite-lamina); the ply stiffness and laminate A assembly as claimed
products and any "laminate stiffness synthesis" phrasing
(laminate-stiffness owns the symmetric-laminate A synthesis); the B/D
bending and coupling matrices of a stack (laminate-bending-stiffness,
wave-48); delamination onset and growth by strain energy release rate
and the B-K law (delamination-growth); moisture content, CTE, CME and
hygrothermal strain (laminate-hygrothermal-response); plate buckling
and stability verdicts (laminate-plate-buckling); honeycomb core and
sandwich content (honeycomb-core-micromechanics, sandwich-panels);
lamina constants from fiber and matrix constituents
(unidirectional-lamina-micromechanics); strength allowables, coupon
statistics and design-value tables (cmh17-allowables,
structures/materials/material-selection, mmpsd-allowables; allowables
are inputs, never looked up); bearing, bypass, bolted, adhesive, peel
and repair content (the rest of the pack); Hashin, Puck or any
mode-decomposition failure CRITERION index (the probe declined those as
same-vein extend-failure-criteria; "matrix mode" and "fiber mode" here
name the ply-discount reduction applied to a Tsai-Wu event, decided by
the fiber-direction stress at the event boundary, not by a separate
criterion); and deflection, bending or stiffness-loss content of any
kind (this leaf is the in-plane A-block march; bending response is the
wave-48 leaf's identity). Lamina properties and allowables are inputs;
no empirical content, no tables, no test data.

## Model (implement exactly)

Pure stdlib (math, os, sys), closed form, deterministic, no RNG, no
tables. Units follow the sibling first-ply-failure convention
throughout: stresses, moduli and allowables in MPa, resultants in
N/mm, ply thickness in mm, strains dimensionless, A-block entries in
N/mm. This is a deliberate unit-system choice for the pack cross-checks
(the sibling logic module is imported at anchor time as an oracle), and
it differs from the wave-48 SI convention of the bending leaf; the
contract test and every worked-example number below are in these units.

Module constants (every fixed number used by the worked example; the
leaf convention is that material properties and allowables are given
inputs, so these are the anchor's pinned worked-example inputs):
- QI_ANGLES = [0.0, 90.0, 45.0, -45.0, -45.0, 45.0, 90.0, 0.0] (the
  [0/90/45/-45]s quasi-isotropic stack)
- PLY_T_MM = 0.125 (mm, uniform ply thickness, total h = 1.0 mm)
- HC_E1 = 181000.0, HC_E2 = 10300.0, HC_G12 = 7170.0, HC_NU12 = 0.28
  (MPa; the T300/5208-class engineering constants shared with the
  sibling leaf)
- HC_XT = 2700.0, HC_XC = 2000.0, HC_YT = 40.0, HC_YC = 246.0,
  HC_S = 68.0 (MPa; the "high-strength carbon/epoxy" design allowables
  of the worked example, a T800H-class fiber tension allowable on the
  T300-class elastic constants)
- UD8_ANGLES = [0.0] * 8 (the [0]8 unidirectional stack)
- T300_E1..T300_S: 181000.0, 10300.0, 7170.0, 0.28, 1500.0, 1500.0,
  40.0, 246.0, 68.0 (the sibling's own module constants for the
  oracle reprise)

Defining relations (pin these exactly; every function derives from
them; all are the standard published closed forms of the pack, Jones,
Mechanics of Composite Materials, 2nd ed., ch. 2, and the sibling's
laminate_first_ply_failure_logic.py, read in full at spec time):
- Plane-stress ply stiffness from engineering constants:
  nu21 = nu12 * E2 / E1, denom = 1 - nu12 * nu21,
  q11 = E1 / denom, q22 = E2 / denom, q12 = nu12 * E2 / denom,
  q66 = G12. Identical arithmetic order to the sibling's
  q_matrix_from_constants so cross-module results are bit-comparable.
- Rotation to the laminate axes at theta_deg, with c = cos(theta),
  s = sin(theta), c2 = c^2, s2 = s^2, c4 = c2^2, s4 = s2^2,
  s2c2 = s2 * c2, cs = c * s:
  Qbar11 = Q11 c4 + 2 (Q12 + 2 Q66) s2c2 + Q22 s4
  Qbar22 = Q11 s4 + 2 (Q12 + 2 Q66) s2c2 + Q22 c4
  Qbar12 = (Q11 + Q22 - 4 Q66) s2c2 + Q12 (c4 + s4)
  Qbar66 = (Q11 + Q22 - 2 Q12 - 2 Q66) s2c2 + Q66 (c4 + s4)
  Qbar16 = ((Q11 - Q12 - 2 Q66) c2 - (Q22 - Q12 - 2 Q66) s2) c s
  Qbar26 = ((Q11 - Q12 - 2 Q66) s2 - (Q22 - Q12 - 2 Q66) c2) c s
  The full in-plane 6-tuple order is (Qb11, Qb12, Qb16, Qb22, Qb26,
  Qb66). The four-term sub-block matches the sibling's
  rotated_ply_stiffness bit for bit; Qbar16 and Qbar26 use the same
  arithmetic order the wave-48 laminate-bending-stiffness spec pins.
- In-plane laminate block: A_ij = sum over plies of Qbar_ij(theta_k)
  times t_k, over the plies' CURRENT degraded engineering constants.
- Full 3x3 inversion of the symmetric in-plane block (exact closed
  form, never a numerical solver): with determinant
  det = A11 (A22 A66 - A26^2) - A12 (A12 A66 - A26 A16)
        + A16 (A12 A26 - A22 A16),
  i11 = (A22 A66 - A26^2) / det, i12 = -(A12 A66 - A26 A16) / det,
  i16 = (A12 A26 - A22 A16) / det,
  i22 = (A11 A66 - A16^2) / det, i26 = -(A11 A26 - A12 A16) / det,
  i66 = (A11 A22 - A12^2) / det, and
  ex = i11 Nx + i12 Ny + i16 Nxy, ey = i12 Nx + i22 Ny + i26 Nxy,
  gxy = i16 Nx + i26 Ny + i66 Nxy. For a balanced symmetric intact
  stack this reduces exactly to the sibling's a11 = A22 / (A11 A22 -
  A12^2), a12 = -A12 / (A11 A22 - A12^2), a66 = 1 / A66.
- Material-axis strain transform (sibling closed form): e1 = ex c^2 +
  ey s^2 + gxy c s, e2 = ex s^2 + ey c^2 - gxy c s,
  g12 = 2 (ey - ex) c s + gxy (c^2 - s^2).
- Material-axis stresses: s1 = q11 e1 + q12 e2, s2 = q12 e1 + q22 e2,
  t12 = q66 g12, with the ply's CURRENT (possibly degraded) stiffness.
- Tsai-Wu index (sibling closed form): FI = F1 s1 + F2 s2 + F11 s1^2 +
  F22 s2^2 + F66 t12^2 + 2 F12 s1 s2 with F1 = 1/Xt - 1/Xc,
  F2 = 1/Yt - 1/Yc, F11 = 1/(Xt Xc), F22 = 1/(Yt Yc), F66 = 1/S^2 and
  F12 = -0.5 sqrt(F11 F22). FI >= 1.0 marks failure.
- Ply-discount reductions (receipt, gate d): matrix-mode failure sets
  E2, G12 and nu12 of the failed ply to 0.0 with E1 retained; a
  fiber-mode failure sets E1 to 0.0 as well (all four constants 0.0,
  the ply carries nothing further). A matrix-failed ply keeps a legal
  plane-stress state (nu21 = nu12 E2 / E1 = 0, denom = 1, q11 = E1,
  q12 = q22 = q66 = 0): it is a unidirectional tape and remains an
  active load path that can fail again, always in fiber mode, because
  for a tape FI = F1 s1 + F11 s1^2 factors exactly as
  (s1 - Xt)(s1 + Xc) / (Xt Xc), whose unity roots sit at s1 = Xt and
  s1 = -Xc.
- Mode discrimination (this leaf's pin): at an event stress state,
  fiber mode iff s1 >= Xt or s1 <= -Xc (with a 1e-9 relative slack so
  an event exactly on the fiber boundary classifies fiber in floating
  point), else matrix mode. A state guard forces fiber mode when a
  "matrix" discount would not change the ply (already a tape), which
  the factoring identity above shows happens only at the fiber
  boundary; progress is monotone in all cases.
- Event convention (this leaf's pin, the fence against the sibling):
  within a load segment the stresses of every active ply are linear in
  the total load scale lambda, so the per-ply index is quadratic in
  lambda, FI_k(lambda) = a_k lambda^2 + b_k lambda with a_k the
  quadratic stress terms (F11 s1^2 + F22 s2^2 + F66 t12^2 +
  2 F12 s1 s2 at unit resultants) and b_k the linear terms (F1 s1 +
  F2 s2). A ply event is the smallest positive root of
  FI_k(lambda) = 1, i.e. of a_k lambda^2 + b_k lambda - 1 = 0
  (closed-form quadratic, no bisection). The sibling's k* = 1/max(FI)
  is its documented LINEARIZED reserve convention (quoted in the Claim
  fences above) and is never used here.
- Cascade handling: the march is load controlled. When a discount
  leaves an active ply with FI >= 1 already at the current load, that
  ply fails immediately at the same load (grouped cascade event),
  which is the physically required behavior of the load-controlled
  ply-discount model (real anchor: the worked QI march's final event is
  such a cascade).
- Termination: reason "last-ply-failure" when, after an event, no
  ply retains stiffness or the reassembled in-plane block is not
  positive definite (the last recorded event load is the ultimate
  load); reason "strain-limit" when the optional maximum active-ply
  fiber strain is reached before the next event; reason
  "no-further-ply-failure" when no active ply has a positive unity
  root in a segment with positive definite A (the load direction never
  drives that laminate to failure).

Functions (every public function validates its inputs identically;
ValueError, never assert; real message prefixes quoted in the Worked
example):
- q_matrix_from_constants(e1, e2, nu12, g12) -> (q11, q12, q22, q66):
  the plane-stress stiffness above. ValueErrors: e1, e2, g12 or nu12
  not a positive number ("engineering constants E1, E2, G12, nu12 must
  be positive"), nu12 * nu21 >= 1 ("nu12 nu21 >= 1 makes the
  plane-stress stiffness singular").
- laminate_a_matrix(plies_deg, ply_thickness_mm, e1, e2, nu12, g12) ->
  (A11, A12, A16, A22, A26, A66): the intact-laminate in-plane block
  in N/mm (the balanced-symmetric 4-tuple (A11, A12, A22, A66) is its
  sub-block, identical to the sibling's a_matrix_from_plies). Same
  ValueErrors as q_matrix_from_constants plus an empty ply list
  ("plies_deg must contain at least one ply angle") and a non-positive
  ply thickness ("ply thickness must be a positive number, got ...").
- midplane_strains(a_components, nx, ny, nxy) -> (ex, ey, gxy): the
  full 3x3-inverse strain recovery. ValueError for a non-positive-
  definite block ("the laminate A block is not positive definite").
- per_ply_failure_indices(plies_deg, a_components, e1, e2, nu12, g12,
  allowables, nx, ny, nxy) -> list of per-ply Tsai-Wu indices on the
  INTACT laminate at the given resultants (the sibling-parity surface
  used for the oracle cross-checks). Same ValueErrors.
- ply_discount_mode(s1, s2, t12, xt, xc) -> "fiber" or "matrix": the
  mode rule above.
- progressive_failure_march(plies_deg, ply_thickness_mm, e1, e2, nu12,
  g12, allowables, nx, ny, nxy, strain_limit=None) -> report dict: the
  one-shot march. ValueErrors of every input above plus an all-zero
  reference resultant ("the reference resultant (Nx, Ny, Nxy) must be
  nonzero") and a non-positive strain limit ("strain limit must be a
  positive number, got ...").
Report dict keys (the contract test asserts this exact key set):
  "ply_angles_deg", "ply_thickness_mm", "nx_ref", "ny_ref", "nxy_ref",
  "a_initial" (the intact 6-tuple, N/mm), "events" (list of dicts with
  keys "event" (1-based), "load_multiplier", "load_nx" (N/mm),
  "failed_plies" (0-based indices), "failed_angles_deg", "modes",
  "a_after" (the degraded 6-tuple after the discount, N/mm)),
  "fpf_event_index", "fpf_load_nx", "fpf_plies", "fpf_modes",
  "ultimate_event_index", "ultimate_load_nx",
  "post_fpf_reserve_factor" (ultimate / FPF; None when no ply event
  precedes termination), "termination_reason".

Identities to test (closed form, checkable without the builder module):
- [0]8 unidirectional reduction (receipt, gate d): a [0]8 stack under
  Nx carries s1 = Nx/t exactly (the Poisson cross terms cancel in the
  ply stress recovery regardless of nu12), and with s2 = t12 = 0 the
  Tsai-Wu index is F1 s1 + F11 s1^2, which reaches unity exactly at
  s1 = Xt (tension) or s1 = -Xc (compression). The march therefore
  produces a single fiber event at Nx = Xt * h and FPF = last-ply =
  ultimate with post-FPF reserve factor 1.0: the leaf reduces to the
  FPF identity (real anchor: 2700.0 N/mm at Xt = 2700 MPa, h = 1 mm).
- Strain-limit branch: on [0]8 the fiber strain is e1 = Nx / (E1 h),
  so a strain limit of Xt / (2 E1) terminates the march at
  Nx = Xt h / 2 with no ply event (real anchor: 1350.0 N/mm, reason
  "strain-limit").
- Sibling-parity: on the intact QI stack at any load, this leaf's
  per-ply indices equal the sibling logic module's
  ply_failure_indices (real anchor: max relative difference 0.0 at the
  T300/5208 reprise); and the sibling's own index function evaluated
  at this leaf's quadratic-exact first-event load returns max index
  1.0 (real anchor: exactly 1), i.e. the march FPF event is where the
  sibling's index machinery actually reaches unity.
- Convention seam (documented, never asserted equal): the sibling's
  linearized FPF load k* Nx = 319.48175582 N/mm vs this leaf's
  quadratic-exact first event 276.119022337 N/mm on the same T300/5208
  QI stack, ratio 1.15704362965.
- Degraded-stiffness monotonicity: across a uniaxial march, each of
  A11, A22 and A66 is non-increasing event to event (each is a sum of
  non-negative rotated-ply terms and every discount zeroes one ply's
  terms) (real anchor: ok across all four QI events).
- Balanced symmetric intact coupling: A16 and A26 vanish to machine
  precision on the [0/90/45/-45]s stack (real anchor: 5.27e-14 and
  2.17e-12 N/mm).
- Determinism: two consecutive marches return identical dicts; no
  randomness; no imports beyond math, os, sys.

## Worked example

High-strength carbon/epoxy (the worked material of this leaf):
E1 = 181.0 GPa, E2 = 10.3 GPa, G12 = 7.17 GPa, nu12 = 0.28, with the
T800H-class design allowables Xt = 2700 MPa, Xc = 2000 MPa, Yt = 40
MPa, Yc = 246 MPa, S = 68 MPa; QI stack [0/90/45/-45]s, 8 plies at
0.125 mm, h = 1.0 mm; uniaxial resultant Nx only.

All values below are REAL outputs of the prep anchor
ops/automation/state/wave49-specs/anchors/anchor_laminate-progressive-failure.py
(pure stdlib, closed form, exit 0, no RNG), run once at spec time as
cd ~/AeroSkills && python3
ops/automation/state/wave49-specs/anchors/anchor_laminate-progressive-failure.py
and re-verified byte-identical under /usr/bin/python3 3.11.16 and
~/.pyenv/versions/3.13.12/bin/python3 (only the printed version banner
line differs; every numeric output agrees to all printed digits). The
anchor imports the on-disk sibling logic module
skills/structures/composites/laminate-first-ply-failure/scripts/
laminate_first_ply_failure_logic.py at run time (path derived from the
anchor's own repo-relative location, never a machine path) for the
oracle cross-checks; all internal identity asserts pass.

- Intact [0/90/45/-45]s assembly: q = (181811.13884441793,
  2896.9244443497314, 10346.158729820467, 7170.0) MPa; A =
  (76368.21770142684, 22607.3555300421, 5.274221359982868e-14,
  76368.21770142682, 2.169152732318139e-12, 26880.431085692366) N/mm,
  so A11 = A22 = 76368.2177014268 N/mm, A12 = 22607.3555300421 N/mm,
  A66 = 26880.4310856924 N/mm and the balanced symmetric coupling
  terms A16 and A26 vanish to machine precision (5.27e-14 and
  2.17e-12 N/mm). Mid-plane strains at Nx = 100 N/mm: ex =
  0.00143521975776, ey = -0.00042486945884, gxy = 3.14693643788e-20,
  matching the sibling's published worked example of the same stack
  and constants to all printed digits.
- Progressive-failure march (the headline run): termination_reason =
  "last-ply-failure". Event 1 (the FPF event) at Nx =
  276.697868003 N/mm, plies [1, 6] (the two 90-degree plies), modes
  ["matrix", "matrix"]: the transverse stress s2 in the 90-degree
  plies reaches the Tsai-Wu unity boundary first (Yt = 40 MPa class
  transverse failure), E2, G12 and nu12 are zeroed, the plies remain
  E1 tapes. Degraded A after event 1 = (73781.67801897172,
  21883.124418954663, 5.1943493615022827e-45, 76165.43299032236,
  3.2043710950812996e-12, 25087.931085692366) N/mm: the laminate lost
  the 90-degree transverse stiffness (A11 down from 76368.2177), the
  90-degree fibers still stiffen A22. Event 2 at Nx = 347.807280322
  N/mm, plies [2, 3, 4, 5] (the four +/-45-degree plies), modes
  ["matrix", "matrix", "matrix", "matrix"]: the angle plies fail in
  the matrix mode under their combined transverse and shear stress,
  joining the tapes. Degraded A after event 2 = (68077.7847111045,
  23349.231111087433, 5.1943493615022827e-45, 70461.53968245511,
  3.2043710950812996e-12, 24417.5) N/mm. Event 3 at Nx =
  925.680039438 N/mm, plies [0, 7] (the two 0-degree plies), modes
  ["fiber", "fiber"]: the 0-degree fiber stress s1 = Xt = 2700 MPa,
  E1 zeroed; this is the last-ply event that sets the ultimate load.
  Degraded A after event 3 = (22625.00000000001, 22625.0,
  5.1943493615022827e-45, 67875.0, 3.2043710950812996e-12, 22625.0)
  N/mm: only the retained-E1 tapes still carry. Event 4 at the SAME
  applied load Nx = 925.680039438 N/mm, plies [1, 2, 3, 4, 5, 6] (the
  six tapes), modes ["fiber", "fiber", "fiber", "fiber", "fiber",
  "fiber"]: the load-controlled cascade, the 90-degree tapes now in
  fiber compression (s1 = -Xc) and the 45-degree tapes in fiber
  tension (s1 = Xt) fail instantly at the unchanged applied load,
  zeroing the laminate: degraded A after event 4 = (0.0, 0.0, 0.0,
  0.0, 0.0, 0.0) N/mm. Summary: fpf_load_nx = 276.697868003 N/mm,
  ultimate_load_nx = 925.680039438 N/mm, post_fpf_reserve_factor =
  3.34545418119, fpf/ultimate ratio = 0.298913076025. The 90-ply
  matrix event (FPF) sits at 0.299 of the 0-ply fiber-failure ultimate
  load, within the receipt's "roughly a third to a fifth" magnitude
  band (the QI laminate survives to 3.35 times its first-ply-failure
  load before the 0-degree fibers break).
- [0]8 reduction identity: the march on the [0]8 stack (Xt = 2700 MPa,
  h = 1.0 mm) produces exactly ONE event at Nx = 2700.0 N/mm with all
  eight plies in fiber mode, ultimate_load_nx = 2700.0 N/mm, post-FPF
  reserve factor 1.0, termination "last-ply-failure": FPF = last-ply =
  ultimate at sigma1 = Nx/t = Xt, the leaf reduced to the FPF
  identity. Strain-limit branch on the same stack with
  strain_limit = 0.00745856353591 (= Xt / (2 E1)): zero ply events,
  ultimate_load_nx = 1350.0 N/mm, termination "strain-limit": the
  fiber strain e1 = Nx / (E1 h) reaches the limit at exactly half the
  fiber-failure load.
- T300/5208 reprise and sibling-oracle parity (Xt = Xc = 1500 MPa,
  Yt = 40, Yc = 246, S = 68, same QI stack): intact A identical to
  above (same engineering constants). Per-ply indices at Nx = 100
  N/mm = [0.025414833832501437, 0.31300691879363685,
  0.1827462378567907, 0.1827462378567907, 0.1827462378567907,
  0.1827462378567907, 0.31300691879363685, 0.025414833832501437], max
  index 0.313006918794 in the 90-degree ply (index 1), the sibling's
  published worked example reproduced. This leaf's march on the same
  material: fpf_load_nx = 276.119022337 N/mm (90s, matrix),
  ultimate_load_nx = 511.812522286 N/mm (the 0-degree fiber event at
  s1 = Xt = 1500 MPa), fpf/ultimate ratio = 0.539492510077. The
  imported sibling oracle returns max_fi = 0.313006918794, critical
  ply 1, fpf_scale_k = 3.1948175582 and its linearized fpf_load_nx =
  319.48175582 N/mm (its SKILL.md rounds this to 319.5 N/mm); the
  oracle's own index function evaluated at THIS leaf's quadratic-exact
  first-event load 276.119022337 N/mm returns max index = 1 (within
  1e-9): the sibling's index machinery reaches unity exactly where
  this leaf places the FPF event. Convention note printed by the
  anchor: sibling linearized k* load 319.48175582 N/mm vs this leaf
  quadratic-exact event 276.119022337 N/mm, ratio 1.15704362965 (the
  documented linearized-vs-exact seam, fenced in Claim and Model).
- Real ValueError messages (module output, quoted as raised): a zero
  E1 raises "engineering constants E1, E2, G12, nu12 must be
  positive"; a negative ply thickness raises "ply thickness must be a
  positive number, got -0.125"; an empty stack raises "plies_deg must
  contain at least one ply angle"; a singular Poisson product (E2 =
  1e12, nu12 = 0.9) raises "nu12 nu21 >= 1 makes the plane-stress
  stiffness singular"; a zero transverse allowable raises "allowables
  Xt, Xc, Yt, Yc, S must be positive"; an all-zero reference resultant
  raises "the reference resultant (Nx, Ny, Nxy) must be nonzero"; a
  zero strain limit raises "strain limit must be a positive number,
  got 0.0".
- The anchor's internal asserts (the [0]8 single-fiber-event identity
  at 2700.0 N/mm within 1e-6 relative, the strain-limit half-load
  identity, the QI magnitude band 0.20 <= fpf/ultimate <= 0.35, the
  90-ply matrix FPF at plies [1, 6], the 0-ply fiber last event at
  plies [0, 7] with the same-load tape cascade and all-zero final A,
  the degraded-stiffness monotonicity, the sibling worked-example
  reproduction within 0.1 N/mm and 1e-4 on max_fi, the sibling index
  oracle reaching 1.0 within 1e-6 at the march FPF load, every
  ValueError, and the determinism double-run) all pass and the anchor
  exits 0, byte-identical under both interpreters.

Run your module and take the real outputs as assert targets; the
anchors above are real prep outputs of
ops/automation/state/wave49-specs/anchors/anchor_laminate-progressive-failure.py
(stdlib math, closed form, exit 0, no randomness, identical under both
interpreters).

## Validation list (contract test must include)

1. Worked-example asserts within 1e-6 relative on the QI stack
   [0.0, 90.0, 45.0, -45.0, -45.0, 45.0, 90.0, 0.0] at t = 0.125 mm
   with e1 = 181000.0, e2 = 10300.0, nu12 = 0.28, g12 = 7170.0 and
   allowables (2700.0, 2000.0, 40.0, 246.0, 68.0) under (nx, ny, nxy)
   = (1.0, 0.0, 0.0):
   progressive_failure_march returns fpf_load_nx = 276.697868003,
   ultimate_load_nx = 925.680039438 (N/mm), post_fpf_reserve_factor =
   3.34545418119, termination "last-ply-failure", four events at load
   276.697868003 (plies [1, 6], modes ["matrix", "matrix"]),
   347.807280322 (plies [2, 3, 4, 5], matrix), 925.680039438 (plies
   [0, 7], fiber) and 925.680039438 (plies [1, 2, 3, 4, 5, 6], fiber,
   the same-load cascade), and laminate_a_matrix returns a_initial =
   (76368.2177014268, 22607.3555300421, ~0, 76368.2177014268, ~0,
   26880.4310856924).
2. QI magnitude gate (receipt, gate d): 0.20 <= fpf_load_nx /
   ultimate_load_nx <= 0.35 (real anchor 0.298913076025): the FPF
   matrix event sits at roughly a third of the 0-ply fiber-failure
   ultimate load.
3. [0]8 reduction identity: progressive_failure_march([0.0]*8, 0.125,
   181000.0, 10300.0, 0.28, 7170.0, allowables, 1.0, 0.0, 0.0) returns
   exactly one event at 2700.0 N/mm within 1e-6 relative with eight
   fiber modes, ultimate_load_nx = 2700.0 = Xt * h, fpf = ultimate,
   post_fpf_reserve_factor = 1.0 within 1e-9, termination
   "last-ply-failure".
4. Strain-limit branch: the same [0]8 call with
   strain_limit = 0.00745856353591 returns zero ply events,
   ultimate_load_nx = 1350.0 N/mm within 1e-6 relative and
   termination "strain-limit"; without a limit the same inputs give
   the full fiber event (the limit parameter is honored only when it
   binds).
5. Event convention fence: on the T300/5208 QI reprise (Xt = Xc =
   1500.0), the march's first event load 276.119022337 N/mm is NOT
   the sibling's linearized k* load 319.48175582 N/mm (the ratio
   319.48175582 / 276.119022337 = 1.15704362965 is documented, never
   asserted to be 1); instead assert the index-oracle equivalence:
   recomputing the per-ply Tsai-Wu indices of the intact laminate at
   the march FPF load gives max index 1.0 within 1e-6 relative (the
   event is where the index reaches unity). The contract test never
   imports across leaves; it re-derives the sibling closed form
   in-test (q11..q66, the rotation, the strain recovery, the index).
6. Ply-discount semantics: after a matrix event the failed plies
   still contribute their E1 tape stiffness: the event-1 degraded A of
   the worked QI run has A11 = 73781.6780189717 and A22 =
   76165.4329903224 N/mm (the 90-degree tapes still stiffen the
   transverse direction), while after the fiber events of event 4 the
   A block is (0.0, 0.0, 0.0, 0.0, 0.0, 0.0). Assert the exact
   per-event a_after tuples within 1e-6 relative on the nonzero
   entries.
7. Mode discrimination: fiber mode iff s1 >= Xt or s1 <= -Xc:
   ply_discount_mode(2700.0, 0.0, 0.0, 2700.0, 2000.0) is "fiber",
   ply_discount_mode(-2000.0, 0.0, 0.0, 2700.0, 2000.0) is "fiber",
   ply_discount_mode(-73.0, 13.6, 0.0, 2700.0, 2000.0) is "matrix".
8. Degraded-stiffness monotonicity: across the worked QI march each of
   A11, A22 and A66 is non-increasing event to event (assert each
   a_after diagonal entry <= the previous segment's within 1e-9
   relative + 1e-9 absolute).
9. Balanced symmetric coupling: laminate_a_matrix on the intact QI
   stack returns A16 and A26 below 1e-6 N/mm absolute (real anchor
   5.27e-14 and 2.17e-12).
10. ValueErrors raise from the named public function with the real
    message prefixes quoted in the Worked example: a non-positive
    engineering constant ("engineering constants E1, E2, G12, nu12
    must be positive"), a singular Poisson product ("nu12 nu21 >= 1
    makes the plane-stress stiffness singular"), an empty stack
    ("plies_deg must contain at least one ply angle"), a non-positive
    ply thickness ("ply thickness must be a positive number, got ..."),
    a non-positive allowable ("allowables Xt, Xc, Yt, Yc, S must be
    positive"), an all-zero reference resultant ("the reference
    resultant (Nx, Ny, Nxy) must be nonzero"), a non-positive strain
    limit ("strain limit must be a positive number, got ...").
11. Report key set: progressive_failure_march returns exactly the
    documented dict keys ("ply_angles_deg", "ply_thickness_mm",
    "nx_ref", "ny_ref", "nxy_ref", "a_initial", "events",
    "fpf_event_index", "fpf_load_nx", "fpf_plies", "fpf_modes",
    "ultimate_event_index", "ultimate_load_nx",
    "post_fpf_reserve_factor", "termination_reason"), and each event
    dict exactly ("event", "load_multiplier", "load_nx",
    "failed_plies", "failed_angles_deg", "modes", "a_after").
12. Determinism: two consecutive progressive_failure_march calls on
    the worked QI inputs return identical dicts; no randomness
    anywhere; no imports beyond math, os, sys.
13. No exact-float equality on computed sums; use
    assertAlmostEqual/math.isclose everywhere (the A16/A26 vanish
    checks and the event-group equality are asserted as absolute or
    relative tolerances, never as equality to 0.0: the real residues
    5.27e-14 and 2.17e-12 N/mm are cancellation artifacts). Test
    passes under BOTH interpreters (/usr/bin/python3 3.11.16 and
    ~/.pyenv/versions/3.13.12/bin/python3); the anchor's numeric
    output is byte-identical under both except the version banner.
14. Run the deterministic contract test offline (no network); it exits
    0. All worked-example numbers above were verified byte-identical
    under both interpreters before spec time.

## Corpus fragment (eval/hit1-wave49-laminate-progressive-failure.yaml)

Query 1 (copy verbatim from the probe receipt gate (e)):
  "compute the laminate-progressive-failure ultimate load of the
  quasi-isotropic carbon-epoxy stack by the ply-discount-method: at
  the first-ply-failure event degrade the stiffness of the failed ply,
  reassemble the laminate a-matrix, march the load to the next
  sequential-ply-failure event and repeat to the last-ply-failure, and
  report the ultimate-laminate-load and the degraded-laminate-stiffness
  of the post-fpf-load-redistribution analysis"
  -> top1 laminate-progressive-failure 47.0, top2
  laminate-first-ply-failure 10.5, margin 36.5 (strong)
  intent: "structures/composites; laminate-progressive-failure: the
  ply-discount march of the quasi-isotropic carbon-epoxy stack past
  first-ply failure, degrading the failed-ply stiffness, reassembling
  the laminate A matrix and reapplying the load to the last-ply
  failure, reporting the ultimate laminate load and the degraded
  laminate stiffness of the post-FPF load-redistribution analysis"
  expected_skill: "structures/composites/laminate-progressive-failure"
Query 2 (copy verbatim from the probe receipt gate (e)):
  "find the last-ply-failure load of the cross-ply laminate with the
  ply-discount-method: discount the failed-ply stiffness after each
  ply event, re-assemble the in-plane laminate stiffness and re-apply
  the load resultant until the laminate-progressive-failure march
  reaches the ultimate-laminate-load, and give the per-event failure
  sequence for the progressive-failure-analysis"
  -> top1 laminate-progressive-failure 43.0, top2
  laminate-first-ply-failure 11.5, margin 31.5 (strong)
  intent: "structures/composites; laminate-progressive-failure: the
  last-ply-failure load of a laminate by the ply-discount method with
  the per-event failure sequence, the failed-ply stiffness discount,
  the in-plane laminate stiffness reassembly and the reapplied load
  resultant to the ultimate laminate load of the
  progressive-failure-analysis"
  expected_skill: "structures/composites/laminate-progressive-failure"
Task ids: w49-laminate-progressive-failure-1 and -2. Prep greps
(re-run fresh at spec time): `grep -rilE
"progressive.{0,30}fail|ply.discount|last.ply" skills/ --include=SKILL.md`
returns zero files (the only wider-token hit is the sibling's own
disclaimer line 132), `grep -icE
"progressive.{0,30}fail|ply.discount|last.ply|post.?fpf"
eval/hit1-corpus.yaml` returns 0 of 1326 task blocks and the
first-ply slice counts 9 (all routed to the sibling), so the queries
are collision-free; the existing laminate corpus tasks route on the
first-event and stiffness vocabulary of the sibling leaves and do not
overlap this multi-event surface. Build-time fence note (receipt, gate
f): add one routing row to laminate-first-ply-failure's Related leaves
pointing multi-event / post-FPF / stiffness-degradation questions at
this leaf (its own Pitfalls line 131-133 already names the split),
plus one related-leaves row in this leaf pointing back at the
first-event sibling.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the progressive
failure of a composite laminate past first-ply failure by the
ply-discount method:" and include the outputs in the Claim order (the
per-event failure sequence with matrix and fiber modes, the degraded
laminate stiffness after each event, the first-ply-failure load of the
Tsai-Wu index at unity, the last-ply-failure ultimate laminate load
and the post-FPF reserve factor), then close with the Trigger list.
Never claim the linearized k* = 1/max(FI) reserve convention or the
critical-ply / laminate-failure-envelope first-event reporting
(laminate-first-ply-failure owns the first event under its documented
linearized convention); never claim the ply stiffness or the A matrix
as produced deliverables (laminate-stiffness owns the assembly); never
claim a Hashin/Puck mode-decomposition criterion (the mode words here
name the discount reduction, decided at the fiber stress boundary).
First tag: laminate-progressive-failure. Metadata tags EXACTLY as the
probe receipt gate (f) lists them, nothing else:
laminate-progressive-failure, ply-discount-method, last-ply-failure,
ultimate-laminate-load, degraded-laminate-stiffness,
post-fpf-load-redistribution, sequential-ply-failure,
progressive-failure-analysis. 50-150 words, <=1000 chars, no em dash,
no content-policy sweep term, action verb present. Recommended wording
(verified at spec time by character and word count):

"Use when you must compute the progressive failure of a composite
laminate past first-ply failure by the ply-discount method: degrade
the stiffness of the failed ply at each ply event, reassemble the
in-plane laminate stiffness, reapply the load resultant and march to
the last-ply-failure ultimate load. Produces the sequential-ply-failure
event loads with the matrix and fiber modes, the degraded laminate
stiffness after each event, the first-ply-failure load from the
per-ply Tsai-Wu index at unity, the ultimate laminate load and the
post-FPF reserve factor of the post-fpf-load-redistribution analysis.
Trigger: laminate progressive failure, ply discount method, last ply
failure, ultimate laminate load, degraded laminate stiffness,
sequential ply failure, progressive failure analysis."

FORBIDDEN TOKENS (belong to siblings): first-ply-failure-load,
critical-ply, reserve-factor, tsai-wu-failure-index,
midplane-strain-recovery, laminate-failure-envelope and any claim that
reports the first event under the linearized k* = 1 / max(FI)
convention or offers the mid-plane strain recovery or the FPF search
as a standalone product (laminate-first-ply-failure owns the
first-event analysis; this leaf reports the FPF event only as the
first step of its march, at index unity); ply-stiffness,
ply-stiffness-matrix, q11, q12, q22, q66, qbar, laminate-a-matrix,
laminate-stiffness-matrix, abd-matrix, "laminate stiffness synthesis"
and any claim that produces the ply stiffness or assembles the
laminate stiffness as a deliverable (laminate-stiffness);
clt-abd-matrices, laminate-d-matrix, bending-extension-coupling,
unsymmetric-laminate-analysis, laminate-bending-response,
d11-d22-d12-d66, equivalent-laminate-bending-stiffness
(laminate-bending-stiffness, wave-48); delamination, strain energy
release rate, dcb, enf, B-K law (delamination-growth); tsai-hill,
max-stress and any failure verdict from given single-ply stresses
(failure-criteria owns the lamina criteria contract); hashin, puck and
any mode-decomposition criterion index (declined same-vein at the
probe: an extend-failure-criteria change, not a new-leaf seam);
hygrothermal, moisture, coefficient of thermal expansion, cte, cme
(laminate-hygrothermal-response); buckling, critical-load,
plate-buckling, half-wave (laminate-plate-buckling); honeycomb, core,
sandwich, face-wrinkling (honeycomb-core-micromechanics,
sandwich-panels); halpin-tsai, rule-of-mixtures, fiber-volume-fraction
and any constituent-to-lamina prediction
(unidirectional-lamina-micromechanics, wave-47); bearing, bypass,
bolt, adhesive, peel, repair (the remaining pack leaves); a-basis,
b-basis, allowables, coupon statistics and design-value tables
(cmh17-allowables, structures/materials/material-selection,
mmpsd-allowables); and the bare single words progressive, failure,
laminate, ply, stiffness, load, matrix, fiber, event, march as
standalone metadata tags (use only the hyphenated compounds listed
above). "Matrix mode" and "fiber mode" are this leaf's ply-discount
reduction vocabulary, fenced in Claim and Model above; CMH-17 and
FAR-25 frame the methodology and certification context only, never
reproduced verbatim.

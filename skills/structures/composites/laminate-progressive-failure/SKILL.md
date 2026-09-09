---
name: laminate-progressive-failure
description: "Use when you must compute the progressive failure of a composite laminate past first-ply failure by the ply-discount method: degrade the stiffness of the failed ply at each ply event, reassemble the in-plane laminate stiffness, reapply the load resultant and march to the last-ply-failure ultimate load. Produces the sequential-ply-failure event loads with the matrix and fiber modes, the degraded laminate stiffness after each event, the first-ply-failure load from the per-ply Tsai-Wu index at unity, the ultimate laminate load and the post-FPF reserve factor of the post-fpf-load-redistribution analysis. Trigger: laminate progressive failure, ply discount method, last ply failure, ultimate laminate load, degraded laminate stiffness, sequential ply failure, progressive failure analysis."
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
  tags: [laminate-progressive-failure, ply-discount-method, last-ply-failure, ultimate-laminate-load, degraded-laminate-stiffness, post-fpf-load-redistribution, sequential-ply-failure, progressive-failure-analysis]
  version: 0.1.0
  author: AeroSkills
---

# Progressive Failure of a Composite Laminate (structures/composites/laminate-progressive-failure)

Use when the task is the multi-event march of a symmetric balanced
composite laminate past first-ply failure to last-ply failure by the
ply-discount method: at each ply event, degrade the stiffness of the
failed ply, reassemble the in-plane laminate stiffness, reapply the
load resultant and continue until no load-bearing stiffness remains.
This leaf implements the strength-and-stiffness-evolution chain in
pure Python, stdlib only. It pairs with
structures/composites/laminate-first-ply-failure, which owns the
first-event analysis under its own linearized reserve-factor
convention, and reuses the sibling's exact Tsai-Wu index closed form
for the per-event indices.

## Domain quick reference

- Loads: in-plane resultants (Nx, Ny, Nxy) in N/mm; stresses, moduli
  and allowables in MPa; ply thickness in mm; strains dimensionless;
  A-block entries in N/mm.
- Plane-stress ply stiffness: q11 = E1/(1 - nu12 nu21), q22 =
  E2/(1 - nu12 nu21), q12 = nu12 E2/(1 - nu12 nu21), q66 = G12, with
  nu21 = nu12 E2/E1.
- In-plane laminate block: A_ij = sum over plies of Qbar_ij(theta_k)
  t_k, over the plies' CURRENT (possibly degraded) constants, with
  Qbar the standard fourth-power rotation of the ply stiffness. The
  full 3x3 block (A11, A12, A16, A22, A26, A66) is inverted in closed
  form for the mid-plane strains {eps} = [A]^-1 {N}.
  laminate_a_matrix and midplane_strains carry this step.
- Tsai-Wu index: FI = F1 s1 + F2 s2 + F11 s1^2 + F22 s2^2 + F66 t12^2
  + 2 F12 s1 s2 with F1 = 1/Xt - 1/Xc, F2 = 1/Yt - 1/Yc,
  F11 = 1/(Xt Xc), F22 = 1/(Yt Yc), F66 = 1/S^2, F12 =
  -0.5 sqrt(F11 F22). FI >= 1.0 marks ply failure.
  per_ply_failure_indices evaluates it on the intact laminate.
- Event convention: within a load segment every active ply's index is
  quadratic in the load scale lambda. A ply event is the smallest
  positive root of FI_k(lambda) = 1, the exact quadratic root, never
  the sibling's linearized reserve scale k* = 1/max(FI).
- Ply-discount reduction: a matrix-mode failure zeroes E2, G12 and
  nu12 (E1 retained, the ply becomes a unidirectional tape and can
  later fail again in fiber mode); a fiber-mode failure zeroes E1 as
  well. Mode discrimination: fiber mode iff the fiber stress s1 >= Xt
  or s1 <= -Xc at the event, else matrix mode.
  ply_discount_mode carries this rule.
- Termination: last-ply-failure when no ply retains stiffness or the
  reassembled A block loses positive definiteness; strain-limit when
  an optional maximum active-ply fiber strain binds first;
  no-further-ply-failure when the load direction never drives the
  laminate to failure.
- CMH-17 frames the ply allowables and lamina data context, FAR-25 the
  certification framing; the relations above are standard mechanics,
  summary-only.

## Workflow

1. Fix the material and stack: engineering constants E1, E2, nu12, G12
   and the Tsai-Wu allowables Xt, Xc, Yt, Yc, S in MPa, the ply angles
   and thickness in mm. Build the intact laminate block with
   laminate_a_matrix.
2. Recover the mid-plane strains and the per-ply Tsai-Wu indices of the
   intact laminate with per_ply_failure_indices (the sibling-parity
   oracle surface, used to confirm the event convention against the
   sibling's own index machinery).
3. Run the ply-discount march with progressive_failure_march at the
   chosen reference resultant (Nx, Ny, Nxy); internally it re-derives
   the quadratic event root at every active ply each segment and
   classifies each failing ply's mode with ply_discount_mode.
4. Read the failure sequence from the report dict: each event's load,
   failed plies and modes, the degraded laminate stiffness a_after,
   the first-ply-failure event (fpf_load_nx, fpf_plies, fpf_modes),
   the ultimate (last-ply-failure) load and the post-FPF reserve
   factor (ultimate / FPF).
5. For the unidirectional reduction check or a strain-governed design,
   run the march on a [0]n stack, with or without an optional
   strain_limit; the march collapses to the sibling's FPF identity
   when the stack is unidirectional.
6. Confirm the deterministic checks with the contract test
   scripts/test_laminate_progressive_failure.py.

## Worked example

High-strength carbon/epoxy: E1 = 181 GPa, E2 = 10.3 GPa, G12 =
7.17 GPa, nu12 = 0.28, with T800H-class design allowables Xt =
2700 MPa, Xc = 2000 MPa, Yt = 40 MPa, Yc = 246 MPa, S = 68 MPa. QI
stack [0/90/45/-45]s, 8 plies at 0.125 mm (h = 1.0 mm), uniaxial
resultant Nx only. Real module outputs:

- Intact assembly: A11 = A22 = 76368.2177 N/mm, A12 = 22607.3555 N/mm,
  A66 = 26880.4311 N/mm, with A16 and A26 vanishing to machine
  precision (5.27e-14 and 2.17e-12 N/mm).
- Event 1 (the FPF event) at Nx = 276.6979 N/mm, plies [1, 6] (the two
  90-degree plies), modes matrix, matrix: the transverse stress
  reaches the Tsai-Wu unity boundary first (a Yt-class transverse
  failure). Degraded A11 falls to 73781.6780 N/mm while A22 stays near
  76165.4330 N/mm, the 90-degree fibers still stiffening the
  transverse direction as a tape.
- Event 2 at Nx = 347.8073 N/mm, plies [2, 3, 4, 5] (the four
  +/-45-degree plies), all matrix mode: the angle plies fail under
  their combined transverse and shear stress, joining the tapes.
- Event 3 at Nx = 925.6800 N/mm, plies [0, 7] (the two 0-degree
  plies), both fiber mode at s1 = Xt = 2700 MPa: this sets the
  ultimate load, since only the retained-E1 tapes carry past it.
- Event 4 at the SAME load Nx = 925.6800 N/mm, plies [1, 2, 3, 4, 5, 6]
  (the six tapes), all fiber mode: a load-controlled cascade, the
  90-degree tapes in fiber compression and the 45-degree tapes in
  fiber tension fail instantly, zeroing the laminate stiffness.
- Summary: fpf_load_nx = 276.6979 N/mm, ultimate_load_nx =
  925.6800 N/mm, post_fpf_reserve_factor = 3.3455, fpf/ultimate ratio
  0.2989: the QI laminate survives to 3.35 times its first-ply-failure
  load before the 0-degree fibers break.
- [0]8 reduction identity: a single fiber event at Nx = Xt h =
  2700.0 N/mm, FPF = last-ply = ultimate, post-FPF reserve factor 1.0.
  With strain_limit = Xt/(2 E1) = 0.0074586, the march halts at
  Nx = 1350.0 N/mm with zero ply events, reason "strain-limit".
- Event-convention fence (T300/5208 QI reprise, Xt = Xc = 1500 MPa):
  this leaf's exact first event sits at 276.1190 N/mm, not the
  sibling's linearized k* load of 319.4818 N/mm (ratio 1.1570); the
  sibling's own index function, re-evaluated at this leaf's event
  load, returns max index 1.0, confirming the index-oracle equivalence
  fence.

## Verification

- Confirm the QI march (allowables above) returns fpf_load_nx about
  276.70 N/mm, ultimate_load_nx about 925.68 N/mm, post_fpf_reserve_
  factor about 3.3455 and termination "last-ply-failure" with the four
  events above.
- Confirm the QI magnitude gate: 0.20 <= fpf_load_nx / ultimate_load_nx
  <= 0.35 (real value 0.2989).
- Confirm the [0]8 reduction identity (single fiber event at Xt h,
  post-FPF reserve factor 1.0) and the strain-limit branch (halts at
  half that load with zero events when the limit binds).
- Confirm the degraded A11, A22 and A66 are non-increasing event to
  event, and that A16, A26 stay below 1e-6 N/mm absolute on the intact
  balanced symmetric stack.
- Confirm ply_discount_mode classifies fiber mode at and beyond the Xt
  or -Xc boundary, matrix mode otherwise.
- Confirm every non-physical input (non-positive engineering constant,
  singular Poisson product, empty ply stack, non-positive thickness,
  non-positive allowable, all-zero reference resultant, non-positive
  strain limit) raises ValueError.
- Run the contract test offline: python3
  scripts/test_laminate_progressive_failure.py (29 tests, deterministic).

## Related leaves

- structures/composites/laminate-first-ply-failure: the first-event
  analysis under the linearized k* = 1/max(FI) reserve convention;
  this leaf reports the same first event only as the first step of its
  march, at index unity.
- structures/composites/failure-criteria: the single-ply strength
  criteria verdict from given stresses, no laminate assembly or
  stiffness evolution.
- structures/composites/delamination-growth: energy-based delamination
  onset and growth, a different failure class from this leaf's
  stress-based ply-discount march.
- structures/composites/laminate-stiffness: the symmetric-laminate A
  synthesis this leaf reassembles after every discount, without any
  strength content of its own.

## Pitfalls

- Reporting the linearized k* load as the march's first event: the
  sibling's k* = 1/max(FI) is a linearized reserve factor, exact only
  at the failure boundary; this leaf's event is the exact quadratic
  root of FI(lambda) = 1, and the two loads differ by a real,
  measurable factor (1.1570 in the T300/5208 worked case).
- Discounting a matrix failure to zero: a matrix-mode event retains
  E1, so the failed ply keeps carrying fiber-direction load as a tape
  and still stiffens the laminate (A11 stays near 73781.68 N/mm after
  event 1, not zero); only a later fiber-mode event zeroes it
  completely.
- Treating same-load events as one event: events 3 and 4 of the worked
  example share the applied load (925.68 N/mm) but are two distinct
  events, the 0-degree fiber failure followed by the load-controlled
  cascade of the remaining tapes at the unchanged load.
- Feeding an unbalanced or unsymmetric stack: the full 3x3 in-plane
  block handles general coupling, but the worked identities (A16, A26
  vanishing, the [0]8 reduction) assume a balanced symmetric layup;
  the report still returns a well-posed march for other stacks as long
  as the reassembled A block stays positive definite.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_laminate_progressive_failure.py

The test covers the QI worked example (intact A block, the four
sequential-ply-failure events with their loads, failed plies and
modes, the degraded laminate stiffness after each event, the
first-ply-failure load, the ultimate laminate load and the post-FPF
reserve factor), the QI magnitude gate, the [0]8 reduction identity
and its strain-limit branch, the sibling-oracle per-ply index parity
and the event-convention fence, mode discrimination at the fiber
boundary, degraded-stiffness monotonicity, the exact report and event
key sets, determinism, and ValueError rejection of non-physical
inputs.

## Compliance

- Standards referenced, not reproduced: CMH-17 (Composite Materials
  Handbook, SAE) frames the ply allowables and lamina data context;
  FAR-25 (14 CFR Part 25) frames the airframe certification context;
  the ply-discount march is standard mechanics, summary-only per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

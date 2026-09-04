---
name: beam-frame-analysis
description: "Use when you must solve a two-dimensional rigid-jointed frame with the Euler Bernoulli beam element: build the local beam element stiffness from the axial and bending contributions, rotate it into the global frame with the member orientation, assemble the global stiffness matrix, apply the fixed support conditions, solve for the nodal displacements and rotations with a compact elimination solver, and recover the support reactions and the member end actions. Produces the nodal displacement and rotation vector, the support reactions, the member end bending moments and shears, and equilibrium checks for a hand-calc or stdlib-only frame analysis. Units are SI. Trigger: beam frame analysis, rigid jointed frame, Euler Bernoulli beam element, rotation degree of freedom, bending moment recovery, portal frame."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: fem
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fem
  tags: [beam-frame-analysis, rigid-jointed-frame, euler-bernoulli-beam-element, rotation-degree-of-freedom, bending-moment-recovery, portal-frame]
  version: 0.1.0
  author: AeroSkills
---

# Beam and Frame Analysis (structures/fem/beam-frame-analysis)

Use when the task is a two-dimensional rigid-jointed frame solve with the
Euler-Bernoulli beam element: members carry axial force, shear and
bending moment together, and every joint keeps its rotation degree of
freedom. The logic module builds the local 6x6 beam element stiffness
from the axial bar terms and the bending block, rotates it into the
global frame with the member orientation, assembles the global stiffness
matrix, eliminates the fixed degrees of freedom, solves the free nodal
displacements and rotations with a compact elimination solver with
partial pivoting, and recovers the support reactions and the member end
actions. Pure Python standard library, no numpy, no FEA software. It
pairs with the axial-only sibling leaf (same pack) that solves
pin-jointed bar models without rotation degrees of freedom; this leaf
adds bending and rotation degrees of freedom for rigid frames.

## Domain quick reference

- Local element stiffness over (u1, v1, theta1, u2, v2, theta2): the
  axial block E*A/L on (u1, u2) plus the Euler-Bernoulli bending block
  on (v1, theta1, v2, theta2),

      k = (E I / L^3) * [[ 12, -6L, -12, -6L],
                         [-6L,  4L^2,  6L,  2L^2],
                         [-12,  6L,  12,  6L],
                         [-6L,  2L^2,  6L,  4L^2]]

  with 12 E I / L^3, 6 E I / L^2, 4 E I / L and 2 E I / L terms. The
  sign convention is the textbook fixed-end action one: a cantilever
  with a downward tip load P returns end actions (V1, M1) = (+P, -P L)
  at the fixed end, so the module reproduces the spec anchors
  (tip |v| = P L^3/(3 E I), tip |theta| = P L^2/(2 E I), reactions
  R_v = +P and R_m = -P L).
- Orientation: for a member from node i to node j the axis angle is
  alpha = atan2(yj - yi, xj - xi); with c = cos(alpha), s = sin(alpha)
  the block transformation T = diag(lambda, lambda), lambda =
  [[c, s, 0], [-s, c, 0], [0, 0, 1]] maps global to local
  displacements and k_global = T^T k_local T. The scalar rotation dof
  is invariant under this proper rotation, so one T works for every
  member.
- Support conditions: the fixed dofs are eliminated and the reduced
  system is solved by gaussian_elimination(A, b) with partial pivoting;
  the full displacement vector is mapped back with fixed entries zero.
- Reaction at a fixed dof d: R_d = sum_j K[d][j] u[j] minus the applied
  load at d, the action the support exerts on the structure.
- Member end actions: q = k_local * d_local per element in the local
  frame, returned as {n1, v1, m1, n2, v2, m2}; at a joint the end
  actions of the meeting members plus the applied loads balance to
  zero.
- Cantilever closed forms: tip |v| = P L^3 / (3 E I) and
  tip |theta| = P L^2 / (2 E I) for a tip load P.
- Simply supported beam closed form: midspan |v| = P L^3 / (48 E I)
  for a central load P over span L.

## Workflow

1. List the nodes as (x, y) in m; the list position is the 0-based node
   index. Each node carries the dofs (u, v, theta).
2. List the elements as {i, j, E, A, I} with 0-based indices, Young's
   modulus in Pa, area in m^2 and second moment of area in m^4.
3. List the supports as (node_index, dof_names), fixing e.g. ("u", "v",
   "theta") for a fixed foot, ("u", "v") for a pin and ("v",) for a
   roller; rotations stay free unless fixed.
4. List the point loads as {(node_index, dof_name): value} in N or N m,
   positive along +x, +y and the rotation scalar.
5. Solve the whole model with solve_frame(nodes, elements, supports,
   loads), which returns displacements, reactions, member_actions and
   equilibrium_ok in one dict.
6. Or step through the method: element_stiffness_local(E, A, I, L),
   rotation_matrix(angle_rad), element_stiffness_global(E, A, I, L,
   angle_rad), assemble(nodes, elements), solve_free(K, free_dofs,
   loads), reactions(K, u, fixed_dofs, loads) and
   recover_member_actions(element, u, dof_map).
7. Confirm equilibrium_ok is True: the support reactions must balance
   the applied load resultant in both directions within 1e-6 N.
8. Cross-check member end actions at a joint: the end actions of the
   elements meeting there plus any applied joint load sum to zero.
9. Run the deterministic contract test before reporting a result.

## Worked example

1) Cantilever: node 0 at (0, 0) fixed in u, v and theta, node 1 at
   (2.0, 0), E = 70 GPa, A = 0.01 m^2, I = 4e-6 m^4, downward tip load
   of 1000 N (load {(1, "v"): -1000}). The module returns tip
   v = -0.0095238 m (P L^3/(3 E I) = 0.0095238, exact at the node for
   the Euler-Bernoulli element), tip theta = +0.0071429 rad
   (P L^2/(2 E I) = 0.0071429), and reactions R_v = +1000 N with
   R_m = -2000 N m at the root. Member end actions at the root are
   v1 = +1000 N and m1 = -2000 N m, equal to the reactions.
2) Simply supported beam: two elements over nodes (0, 0) pin (u, v
   fixed), (1.5, 0) free and (3.0, 0) roller (v fixed), E = 70 GPa,
   A = 0.01, I = 4e-6, central load of 2000 N downward. The module
   returns midspan v = -0.0040179 m (P L^3/(48 E I) = 0.0040179) and
   reactions of +1000 N at each support; the pin and roller keep their
   rotation free, so the support rotations come out at
   +/- P L^2/(16 E I).
3) Portal frame with rigid joints: columns h = 3 m at x = 0 and
   x = 4 m, beam across the top at y = 3 m, feet fixed, E = 200 GPa,
   A = 0.02, I = 8e-5, lateral load +5000 N at the top-left corner.
   The module returns a top-left horizontal displacement of
   5.4528e-4 m (positive, below 0.05 m), horizontal reactions summing
   to -5000 N, vertical reactions summing to zero, and
   equilibrium_ok True. Raising the beam second moment of area tenfold
   reduces the top displacement to 3.7675e-4 m.


## Pitfalls

- Confusing this solver with the truss sibling: this leaf keeps the
  rotation degree of freedom at every rigid joint (u, v, theta per
  node); pin-jointed bar models with two dofs per node belong to
  truss-analysis.
- Mis-specifying the support conditions: a fixed foot fixes
  ("u", "v", "theta"), a pin fixes ("u", "v") and a roller fixes
  only ("v",); leaving a rotation free that the structure needs
  constrained, or over-constraining a roller, changes the reaction
  path and the deflection.
- Forgetting the sign convention: end actions follow the textbook
  fixed-end convention (a downward tip load gives V1 = +P and
  M1 = -P L at the fixed end), so reading member actions against the
  load direction flips the bending moment sign.
- Building an unstable model silently: an unconstrained or
  mechanism structure makes the reduced system singular and the
  solver raises ValueError with "singular structure"; the model
  must be stable before displacements mean anything.
- Checking only displacements, not equilibrium: equilibrium_ok must
  be True (reactions balance the applied load resultant within
  1e-6 N) and member end actions must sum with any joint load to
  zero, or the assembly has an error.
- Using non-SI or inconsistent member data: E in Pa, A in m^2, I in
  m^4 and loads in N / N m; mixing mm or kN into the input stack
  shifts every displacement by the unit ratio.
## Verification

- Confirm the cantilever tip values match P L^3/(3 E I) and
  P L^2/(2 E I) within 1e-9 and the reactions R_v = +1000 N,
  R_m = -2000 N m within 1e-6.
- Confirm the simply supported beam midspan value matches
  P L^3/(48 E I) within 1e-9 with reactions of 1000 N each.
- Confirm the portal horizontal reactions balance the applied 5000 N,
  the vertical reactions sum to zero and equilibrium_ok is True.
- Confirm member end actions balance at free joints and equal the
  reactions at the supports.
- Confirm every non-positive E, A, I or L, every unknown node index or
  dof name, and every singular reduced system (an unstably supported
  structure) raises ValueError, with the message "singular structure"
  for the unstable case.
- Run the contract test offline: python3
  scripts/test_beam_frame_analysis.py (35 tests, deterministic).

## Related leaves

- skills/structures/fem/truss-analysis: the axial-only sibling; solves
  pin-jointed bar models with two dofs per node, no bending.
- skills/structures/fem/modal-analysis: natural frequencies and mode
  shapes of 2-DOF mass-spring systems, not static frame solves.
- skills/structures/fem/buckling-analysis and
  skills/structures/fem/plate-buckling: Euler column and flat plate
  buckling closed forms.
- skills/structures/fem/calculix-linear and
  skills/structures/fem/calculix-nonlinear: continuum FEA driven in
  CalculiX (ccx), the software alternative to this hand-scale solver.
- skills/structures/fem/contact-analysis: contact problems, outside
  this leaf.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_beam_frame_analysis.py

The test covers the element stiffness symmetry and the 12 E I / L^3
term, rotation matrix orthogonality and block form, the rotated axial
contribution in the EA/L * [[c^2, cs], [cs, s^2]] truss form, the
cantilever and simply supported beam closed forms to 1e-9, the
cantilever reactions and member end actions, portal frame equilibrium,
joint and support member action balance, determinism across repeated
solves, the stiffer-beam displacement reduction, the elimination solver
with and without row swaps, and ValueError rejection of non-physical
inputs, unknown nodes, duplicate dofs and singular structures.

## Compliance

- FAR-25 is referenced, not reproduced: standards-map.yaml marks it
  gated: false and reference-only: true; the beam element matrices and
  closed forms above are standard textbook engineering methodology,
  summary-only.
- compliance: STANDARDS-REF, gated: false.

# Wave-28 leaf spec: beam-frame-analysis (structures, fem pack)

- Path: skills/structures/fem/beam-frame-analysis/
- Pack: fem (existing siblings: truss-analysis, modal-analysis,
  buckling-analysis, plate-buckling, contact-analysis,
  calculix-linear, calculix-nonlinear)
- Standards ids: far-25  (Ledger Standard: far-25)
- Family: structures

## Claim

Solve a two-dimensional rigid-jointed frame (beams that carry axial
force, shear, and bending moment) with the Euler-Bernoulli beam
element: build the local 6x6 beam element stiffness from the axial
and bending contributions, rotate it into the global frame with the
element orientation, assemble the global stiffness matrix, apply the
support conditions by eliminating the fixed degrees of freedom, solve
for the free nodal displacements and rotations with a compact
Gaussian-elimination solver, and recover the support reactions and the
member end actions. Produces the nodal displacement and rotation
vector, the support reactions, the member end forces, and equilibrium
checks that gate a hand-calc or stdlib-only frame analysis.

Does NOT do: solve pin-jointed trusses with axial-only members
(truss-analysis owns 2D pin-jointed trusses); run modal analysis of
mass-spring systems (modal-analysis); Euler column or flat plate
buckling closed forms (buckling-analysis, plate-buckling); drive the
CalculiX solver (calculix-linear, calculix-nonlinear); solve contact
problems (contact-analysis). This leaf is the bending-capable frame
solver (rigid joints, rotation degrees of freedom).

## Model (implement exactly)

Units SI. 2D only. Node ordering: each node has DOFs (u, v, theta).

Element (local frame, x along the member):
- axial: k_a = E*A/L, matrix [[k_a, -k_a],[-k_a, k_a]] on (u1, u2).
- bending (Euler-Bernoulli): with the standard 4x4 beam matrix on
  (v1, theta1, v2, theta2) using 12*E*I/L^3, 6*E*I/L^2, 4*E*I/L,
  2*E*I/L terms (sign conventions per the standard textbook beam
  element: k11 = 12EI/L^3, k12 = 6EI/L^2, k14 = -12EI/L^3, k13 =
  6EI/L^2; etc. Implement the conventional matrix exactly).
- Assemble the 6x6 local matrix with ordering (u1, v1, theta1, u2,
  v2, theta2).
- Rotation: lambda = [[cos, sin, 0], [-sin, cos, 0], [0, 0, 1]] per
  node; global element matrix = T^T * k_local * T with the 6x6 block
  transformation T = [[lambda, 0],[0, lambda]] where lambda maps local
  to global displacements (u_global = lambda^T u_local or the
  conventional rotation; pick one convention, document it in the
  docstring, and keep it consistent - the beam element rotation matrix
  with the axial DOF along the member direction: c = cos(angle from
  global X to the member axis), s = sin(angle); the standard form
  k_global = T^T k_local T with
  T = [[c, s, 0, 0, 0, 0], [-s, c, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
  [0, 0, 0, c, s, 0], [0, 0, 0, -s, c, 0], [0, 0, 0, 0, 0, 1]]).
- Nodal loads: point loads in global coordinates on free DOFs.

Functions:
- element_stiffness_local(E, A, I, L) -> 6x6 list of lists.
  ValueError on E <= 0, A <= 0, I <= 0, L <= 0.
- rotation_matrix(angle_rad) -> 6x6 (block diagonal lambda).
- element_stiffness_global(E, A, I, L, angle_rad) -> 6x6: T^T k T.
- assemble(nodes, elements, dof_map) -> dict: K (global matrix),
  dof_map (node index, dof name -> global dof index). nodes is a list
  of (x, y); elements is a list of dicts {i, j, E, A, I}. ValueError
  on unknown node index or duplicate dof.
- solve_free(K_full, free_dofs, loads) -> dict: extract the reduced
  system, solve with gaussian_elimination(A, b) (partial pivoting,
  local implementation ~20 lines), map back to the full displacement
  vector. Raises ValueError "singular structure" when the reduced
  matrix is singular (pivot near zero).
- gaussian_elimination(A, b) -> list: solve A x = b with partial
  pivoting. ValueError on singular matrix.
- reactions(K_full, u_full, fixed_dofs, loads) -> dict: R_dof =
  sum_j K[dof][j]*u[j] - applied_load[dof] for each fixed dof.
- recover_member_actions(element, u_full, dof_map) -> dict: local end
  actions (axial force at each end, shear, moment) from the local
  displacement vector times the local stiffness matrix; return in the
  local frame: {n1, v1, m1, n2, v2, m2} with the conventional signs.
- solve_frame(nodes, elements, supports, loads) -> dict: supports is
  a list of (node_index, [fixed dof names]) e.g. ("u","v","theta");
  loads is a dict {(node_index, dof_name): value}. Returns
  {displacements, reactions, member_actions, equilibrium_ok} where
  equilibrium_ok checks sum of reaction forces equals the applied
  load resultant within 1e-6.

## Worked example

1) Cantilever beam, one element: node 0 at (0,0) fixed (u, v, theta);
node 1 at (2.0, 0). E = 70e9, A = 0.01, I = 4e-6, L = 2.0. Load P =
-1000 N (v direction) at node 1.
- Tip deflection must equal P*L^3/(3*E*I) = 1000*8/(3*70e9*4e-6) =
  8000/840000 = 0.0095238 m (assert within 1e-9; the Euler-Bernoulli
  element is exact at the nodes for a tip load).
- Tip rotation = P*L^2/(2*E*I) = 1000*4/(2*70e9*4e-6) = 4000/560000 =
  0.0071429 rad (assert within 1e-9).
- Reaction at node 0: vertical +1000 N, moment -2000 N m (assert
  within 1e-6).
2) Simply supported beam, two elements: nodes (0,0) pin (u, v
  fixed), (1.5, 0) free, (3.0, 0) roller (v fixed). E = 70e9, A =
  0.01, I = 4e-6. Central load -2000 N at node 1.
- Midspan deflection = P*L^3/(48*E*I) = 2000*27/(48*70e9*4e-6) =
  54000/13440000 = 0.0040179 m (assert within 1e-9).
- Reactions 1000 N each (assert).
3) Portal frame, rigid joints: two columns h = 3.0 m at x = 0 and
  x = 4.0, a beam across the top at y = 3.0. Feet fixed (u, v,
  theta). E = 200e9, columns and beam A = 0.02, I = 8e-5. Lateral
  load +5000 N (u direction) at the top-left corner node.
- Compute with the module; assert: the total horizontal reaction
  equals 5000 N (equilibrium), the vertical reactions sum to zero,
  equilibrium_ok True, and the top-left horizontal displacement is
  positive and less than 0.05 m (record the exact module value in the
  test header and assert determinism across two calls to 1e-12).
- Sanity: applying the same portal load with the beam moment of
  inertia 10x larger reduces the top displacement (assert
  displacement_2 < displacement_1).
- ValueErrors on E 0, I 0, L -1, singular structure (a single
  node with no supports), unknown node index.
Keep at least 20 test methods: local stiffness symmetry and known 12
EI/L^3 term, rotation matrix orthogonality, global stiffness of an
axial-only member matches k_a*[[c^2, cs],[cs, s^2]] form, cantilever
exact values, SS beam exact values, frame equilibrium, reactions,
member end actions sum on a joint, determinism, ValueErrors,
singularity.

## Corpus tasks (ids w28-beam-frame-analysis-1/2)

Distinctive tokens: beam frame analysis, rigid jointed frame, Euler
Bernoulli beam element, rotation degree of freedom, bending moment
recovery, portal frame. Avoid: pin jointed truss, axial only member,
member axial forces (truss-analysis); natural frequency, mode shape
(modal-analysis); CalculiX, ccx (calculix-linear); plate buckling
coefficient (plate-buckling).

1. "solve the rigid jointed portal frame with beam elements: assemble
   the bending and axial element stiffness, apply the fixed supports,
   and recover the nodal rotations and support reactions"
2. "compute the deflected shape of the cantilever and the simply
   supported beam with the Euler Bernoulli beam element and recover
   the member end bending moments"

## SKILL body notes

Pair with truss-analysis (axial-only sibling; this leaf adds bending
and rotation DOFs for rigid frames). The beam element matrices are
standard Euler-Bernoulli results (textbook formulas, not reproduced
from a proprietary source). FAR-25 referenced reference-only for the
structures-analysis context.

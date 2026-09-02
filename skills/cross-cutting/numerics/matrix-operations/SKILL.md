---
name: matrix-operations
description: "Compute and verify dense square-matrix operations with only the Python standard library: solve the linear system Ax=b by Gaussian elimination with partial pivoting, compute the determinant, invert the matrix, and detect singularity. Use when the task is a direct-method dense matrix problem: a linear system solve, a determinant evaluation, a matrix inverse, a singular-matrix check, or a residual verification of a solution, and numpy or other numerical libraries are unavailable. Produces the solution vector, the determinant value, the inverse matrix, and a singularity verdict with the residual check that gates the solve. Trigger: gaussian elimination, partial pivoting, linear system solve, Ax equals b, determinant, matrix inverse, singular matrix, pivot."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: cross-cutting
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [matrix-operations, linear-solve, gaussian-elimination, partial-pivoting, determinant, matrix-inverse, singular-matrix]
  version: 0.1.0
  author: Aero Agent Skills
---
# Matrix Operations (cross-cutting/numerics/matrix-operations)

Use when the task is a direct-method dense matrix calculation: solve
the square linear system Ax = b, compute a determinant, invert a
matrix, or decide whether a matrix is singular, with the Python
standard library only (no numpy). The leaf covers Gaussian elimination
with partial pivoting, Gauss-Jordan inversion, singularity detection,
and the residual check that verifies a solve.

## Domain quick reference

- Solve Ax = b by Gaussian elimination with partial pivoting. At
  column k pick the largest-magnitude entry at or below the diagonal,
  swap it into the pivot position, eliminate below, then back
  substitute. Pivoting avoids dividing by zero entries and keeps the
  elimination stable. Worked anchor: A = [[2, 1, -1], [-3, -1, 2],
  [-2, 1, 2]] with b = [8, -11, -3] gives x = [2, 3, -1] (each row
  checks exactly); the residual ||Ax - b||_inf is 8.9e-16.
- Pivoting rescue: A = [[0, 1], [1, 0]] has a zero diagonal entry.
  Without a pivot search the first step divides by zero; with partial
  pivoting the rows swap and solve(A, [1, 2]) returns x = [2, 1] and
  the determinant is -1.0 (one swap flips the sign).
- Determinant from the elimination: det = product of the pivots times
  (-1) to the power of the number of row swaps. Worked anchor:
  A = [[1, 2, 3], [0, 1, 4], [5, 6, 0]] gives det = 1.0: the pivot
  product is 5 * 1 * -0.2 = -1 and one swap makes it +1. The 2x2 rule
  det = ad - bc: [[4, 7], [2, 6]] gives 4*6 - 7*2 = 10.0.
- Matrix inverse by Gauss-Jordan elimination on the augmented block
  [A | I]: reduce the left block to the identity and read the inverse
  off the right block. Worked anchor: [[4, 7], [2, 6]]^-1 =
  [[0.6, -0.7], [-0.2, 0.4]] and A * A^-1 is the identity to machine
  precision.
- Singularity detection: a matrix is treated as singular when a pivot
  falls at or below the tolerance (1e-12 times the largest entry
  magnitude). [[1, 2], [2, 4]] has proportional rows: determinant 0.0,
  no inverse, solve raises ValueError. [[1, 2], [3, 4]] has det = -2.0
  and is invertible.
- Residual check: ||Ax - b||_inf = max over rows of
  |sum_j a_ij * x_j - b_i|. Worked anchor: x = [2, 3, -1] on the 3x3
  anchor system gives 0.0; the zero vector gives 11.0. A residual at
  machine epsilon confirms the solve; a small residual does not
  guarantee an accurate x for ill-conditioned systems.
- Cost: each operation is O(n^3) for an n x n matrix; for large or
  sparse systems this leaf is the wrong tool.

## Workflow

1. Confirm the matrix is square and the right-hand side b has one
   entry per row; the logic validates this and raises ValueError.
2. Solve the system with solve(A, b) -> x.
3. Gate the solve with residual_norm(A, b, x): the result must be at
   machine-epsilon scale for a well-conditioned system.
4. If the determinant is needed, call determinant(A); 0.0 is the
   singularity signal (no exception).
5. If the inverse is needed, call inverse(A); it raises ValueError on
   a singular matrix.
6. When the verdict itself is the deliverable, call is_singular(A)
   first; pass a custom tol only when the scale-aware default is not
   what the analysis needs.
7. Report x, det, or the inverse together with the residual or the
   singularity verdict so the result is checkable.

## Pitfalls

- Confusion with least-squares-regression: the normal equations
  A^T A x = A^T b are matrices, but that leaf fits a line y = a + bx
  to paired measurements by minimizing residuals. Tasks that say fit,
  regression, slope, or intercept route to least-squares-regression;
  tasks that say solve the linear system or invert the matrix route
  here.
- Confusion with ode-solvers: time marching an initial value problem
  is not a linear solve. Only an implicit stepping method would need
  one inner solve; route dy/dt = f(t, y) tasks to the ode-solvers
  leaf.
- Skipping the pivot search: elimination that divides by the diagonal
  entry as-is fails on zero diagonals and is unstable on small ones.
  Always swap the largest-magnitude entry into the pivot position.
- Singular is not the same as no solution: a singular matrix has no
  unique solution. determinant returns 0.0, is_singular returns True,
  and solve and inverse raise ValueError; catch the exception or check
  is_singular first.
- Near-singular systems: a pivot barely above the tolerance means the
  solution is extremely sensitive to rounding in the inputs. The
  residual can be small while x is far from the true solution; report
  the conditioning concern instead of trusting x.
- Scale-aware tolerance: the default singular tolerance scales with
  the largest entry (1e-12 * max abs entry). An absolute custom tol
  changes the verdict, so only pass one deliberately.
- Non-square or ragged input: A must be square and b must have length
  n; bool entries and non-numeric entries are rejected. Validate
  before calling rather than relying on downstream errors.
- Stdlib-only contract: the logic module must stay free of numpy and
  other third-party imports; the gate 3 contract test enforces
  stdlib-only imports.

## Behavior contract (gate 3)

The solve, determinant, inverse, singularity, and residual logic is
exercised by the gate 3 contract test:
scripts/test_matrix_operations.py against
scripts/matrix_operations_logic.py (stdlib unittest, offline). Run:

python3 scripts/test_matrix_operations.py

Anchors: the 3x3 system above solves to [2, 3, -1] with zero residual;
det [[1, 2, 3], [0, 1, 4], [5, 6, 0]] = 1.0; det [[4, 7], [2, 6]] =
10.0; inverse [[4, 7], [2, 6]] = [[0.6, -0.7], [-0.2, 0.4]];
[[1, 2], [2, 4]] is singular (det 0.0, solve and inverse raise);
[[0, 1], [1, 0]] is rescued by partial pivoting. Trend properties:
row swaps flip the determinant sign, doubling a row doubles the
determinant, and the inverse of the inverse returns the matrix.

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. Gaussian elimination with partial
  pivoting, the pivot-product determinant, and Gauss-Jordan inversion
  are generic textbook numerical methodology, not RTCA, SAE, or IAQG
  content; summary and formulas only.
- compliance: STANDARDS-REF, gated: false.

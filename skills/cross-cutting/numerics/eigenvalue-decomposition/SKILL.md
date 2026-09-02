---
name: eigenvalue-decomposition
description: "Compute eigenvalues and eigenvectors of square matrices with only the Python standard library: the power iteration returns the dominant eigenvalue-eigenvector pair of a general square matrix, deflation exposes the next pairs, and the Jacobi eigenvalue algorithm returns the full spectrum of a real symmetric matrix. Use when the task is an eigen-decomposition: spectral analysis, dominant eigenvalue, modal frequencies, covariance or stiffness matrix diagonalization, stability of a linear system, or verifying a pair with the residual A v minus lambda v, and numpy or other numerical libraries are unavailable. Produces the eigenvalue-eigenvector pairs in descending order, unit-norm eigenvectors, and the residual that gates each pair. Trigger: eigenvalue, eigenvector, spectral decomposition, jacobi, power iteration, dominant eigenvalue, deflation, diagonalization, rayleigh quotient."
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
  tags: [eigenvalue-decomposition, eigenvalues, eigenvectors, jacobi, power-iteration, deflation, rayleigh-quotient, symmetric-matrix, spectral-decomposition]
  version: 0.1.0
  author: Aero Agent Skills
---
# Eigenvalue Decomposition (cross-cutting/numerics/eigenvalue-decomposition)

Use when the task is computing eigenvalues and eigenvectors of a
square matrix with the Python standard library only (no numpy). The
leaf covers the power iteration for the dominant eigenvalue-
eigenvector pair of a general square matrix, deflation for the next
pairs, the Jacobi eigenvalue algorithm for the full spectrum of a
real symmetric matrix, the convergence criteria of both methods, and
the residual A v - lambda v that verifies every returned pair.

## Domain quick reference

- Power iteration finds the dominant pair. Start from a unit vector
  v, multiply by A, normalize to unit 2-norm, repeat; the Rayleigh
  quotient lam = v^T A v estimates the eigenvalue at each iterate.
  Converges when the pair residual ||A v - lam v||_inf falls at or
  below the tolerance. Worked anchor: A = [[2, 0], [0, 1]] converges
  to lam = 2.0 with v = [1, 0]; the quotient sequence 1.5, 1.8,
  1.95, ... settles on 2.0.
- Convergence criteria: power iteration stops on the pair residual
  (the Rayleigh quotient change between iterates is the monitor,
  but the quotient converges quadratically while the eigenvector
  converges only linearly, so a quotient-change-only stop returns a
  vector accurate to only about sqrt(tol)). Jacobi stops when the
  off-norm, the square root of the sum of squared off-diagonal
  entries, falls at or below the sweep tolerance.
- Deflation exposes the next eigenvalue. Subtract the found pair
  with the rank-one update A - lam * v v^T (v unit norm); the
  remaining eigenvalues and eigenvectors are unchanged, so power
  iteration on the deflated matrix yields the next dominant pair.
  Worked anchor: deflating [[2, 0], [0, 1]] by (2.0, [1, 0]) gives
  [[0, 0], [0, 1]], whose dominant eigenvalue 1.0 is the second
  eigenvalue of A. Call power_spectrum(A, count) to get the count
  largest pairs with the deflation built in.
- Jacobi diagonalizes a real symmetric matrix. Each sweep visits
  every off-diagonal pair (p, q) and applies the plane rotation that
  zeroes A[p][q]; rotations accumulate in the eigenvector matrix.
  Worked anchor: [[2, 1], [1, 2]] gives eigenvalues 3.0 and 1.0
  with unit-norm eigenvectors [0.707, 0.707] and [0.707, -0.707],
  and the residual A v - lam v is zero to machine precision.
  A = [[4, 1, 1], [1, 4, 1], [1, 1, 4]] gives 6.0, 3.0, 3.0
  (6.0 belongs to the all-ones vector).
- Normalization conventions: eigenvectors are returned with unit
  2-norm, eigenvalues sorted in descending order (largest first).
  The sign of an eigenvector is arbitrary: v and -v are the same
  eigenvector, so compare results with the residual, not with a
  memorized sign.
- Residual verification: residual_norm(A, v, lam) = max_i
  |sum_j A[i][j] * v[j] - lam * v[i]|, the natural check that
  (lam, v) is a true pair. For a unit-norm v it is the absolute
  defect; a value at machine-epsilon scale confirms the pair.
  Worked anchor: [[2, 0], [0, 1]] with (2.0, [1, 0]) gives 0.0;
  with (1.0, [1, 0]) it gives 1.0.
- Domain fit: symmetric matrices arise as covariance, stiffness,
  and graph Laplacian matrices; the Jacobi path fits them. General
  square matrices (including non-symmetric ones) use the power
  iteration path, which returns only the count largest pairs, not
  the full spectrum. Cost: power iteration is O(n^2) per iterate;
  Jacobi is O(n^3) per sweep; both are dense-matrix tools.

## Workflow

1. Confirm the matrix is square, numeric, and non-empty; the logic
   validates this and raises ValueError.
2. Pick the method by the matrix and the need: a symmetric matrix
   needing its full spectrum goes to jacobi_eigen(A); a general
   square matrix needing the dominant pair or a few top pairs goes
   to power_iteration(A) or power_spectrum(A, count).
3. For the single dominant pair, call power_iteration(A) ->
   (lam, v); pass v0 when the default all-ones start is orthogonal
   to the dominant eigenspace.
4. For the count largest pairs of a general matrix, call
   power_spectrum(A, count) -> [(lam, v), ...]; the module deflates
   between pairs with a deterministic mixed start vector.
5. For the full spectrum of a symmetric matrix, call
   jacobi_eigen(A) -> (eigenvalues, eigenvectors) with eigenvalues
   descending and unit-norm eigenvector columns.
6. Verify every returned pair with residual_norm(A, v, lam); a
   residual at machine-epsilon scale confirms the pair, a larger
   residual means the iteration did not converge, the wrong method
   was used, or the tolerance was too loose.
7. Report the eigenvalues, the eigenvectors, the convergence
   criterion used, and the residuals so the result is checkable.

## Pitfalls

- Confusion with matrix-operations: solving Ax = b, the determinant,
  and the inverse are different objects from the spectrum. An
  eigenvalue pair satisfies A v = lam v; a solve returns x for one
  right-hand side b. A zero eigenvalue means A is singular (det 0,
  no inverse), which is the only overlap: read it off the spectrum,
  but route "solve the linear system, determinant, inverse" tasks to
  matrix-operations and "eigenvalues, eigenvectors, spectrum" tasks
  here.
- Confusion with convergence-verification: that leaf checks whether
  a CFD or structural mesh sequence has converged with Richardson
  extrapolation and the grid convergence index. This leaf's
  "convergence" is the internal stopping criterion of the iterative
  algorithms (pair residual, off-diagonal sum). Route "grid
  convergence index, refinement study, discretization error" tasks
  there.
- Confusion with finite-difference-derivatives: differentiating a
  function at a point estimates a derivative, not an eigenvalue.
  A Jacobian matrix of partial derivatives is a matrix you might
  later decompose, but "compute the Jacobian" tasks route to
  finite-difference-derivatives; "eigenvalues of the linearized
  system" tasks route here.
- Confusion with ode-solvers: time marching dy/dt = f(t, y) steps
  the state forward; it does not decompose a matrix. Eigenvalue
  analysis of the linearized system matrix is a stability and
  analysis task, not an integration. Route integration tasks to
  ode-solvers; route spectrum-of-the-state-matrix tasks here.
- Jacobi is only for symmetric matrices: feeding a non-symmetric
  matrix to jacobi_eigen raises ValueError. A non-symmetric matrix
  (or one that just needs a few top pairs) takes the power iteration
  path.
- Power iteration finds only the dominant pair: the sequence
  converges to the largest-magnitude eigenvalue. Additional pairs
  need deflation (power_spectrum) or Jacobi; equal-magnitude
  eigenvalues (for example 3.0 and -3.0) converge slowly or mix.
- Start vector orthogonality: a v0 lying exactly in another
  eigenspace returns that pair instead, because the iteration cannot
  leave the eigenspace. The all-ones default can hit this on
  deflated matrices; power_spectrum avoids it with a mixed start,
  and a direct power_iteration call should pass a custom v0 and
  re-verify with the residual.
- Rayleigh quotient vs eigenvector accuracy: the quotient converges
  quadratically while the eigenvector converges linearly, so a stop
  based only on quotient change can return an eigenvector accurate
  to only about sqrt(tol). The residual-based stop in the logic
  module avoids this; keep the residual check in your report.
- Loose tolerance: a large tol stops the iteration early and the
  pair has a small-but-nonzero residual. Tighten tol until the
  residual is at machine-epsilon scale for the analysis.
- Sign and scale: eigenvectors are defined up to sign and scale;
  this leaf returns unit 2-norm vectors. Compare pairs via the
  residual, never via a memorized sign.
- Non-square or ragged input: both routines validate and raise
  ValueError; validate before calling rather than relying on
  downstream errors.
- Stdlib-only contract: the logic module must stay free of numpy
  and other third-party imports; the gate 3 contract test enforces
  stdlib-only imports.

## Behavior contract (gate 3)

The Jacobi, power iteration, deflation, and residual logic is
exercised by the gate 3 contract test:
scripts/test_eigenvalue_logic.py against scripts/eigenvalue_logic.py
(stdlib unittest, offline). Run:

python3 scripts/test_eigenvalue_logic.py

Anchors: jacobi_eigen([[2, 1], [1, 2]]) returns eigenvalues 3.0 and
1.0 with unit-norm eigenvectors satisfying A v = lam v to 1e-8;
[[4, 1, 1], [1, 4, 1], [1, 1, 4]] returns 6.0, 3.0, 3.0;
power_iteration([[2, 0], [0, 1]]) returns 2.0 with v = [1, 0];
after deflation the second eigenvalue is 1.0; power_spectrum
matches jacobi_eigen on the 2x2 anchor. Trend properties: Jacobi
eigenvectors are orthonormal, eigenvalues sort descending, and
residual_norm is 0.0 for an exact pair. ValueError on non-square,
ragged, non-numeric, or bool input, and on non-symmetric input to
the Jacobi routine.

## Compliance

- NACA Report 824 is US government work (public domain); the pack
  anchor per standards-map.yaml. Jacobi's method (1846) and the
  power iteration are classical numerical linear algebra, generic
  textbook methodology, not RTCA, SAE, or IAQG content; summary and
  formulas only.
- compliance: STANDARDS-REF, gated: false.

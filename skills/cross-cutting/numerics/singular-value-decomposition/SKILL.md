---
name: singular-value-decomposition
description: "Use when you must compute the singular value decomposition of a general real rectangular matrix into its singular value factors: the economy U diag(s) Vh form with orthonormal factors from deterministic one-sided Jacobi rotations, singular values in descending order, the 2-norm condition number, the numerical rank at a relative tolerance and the Moore-Penrose inverse. Pure Python standard library, offline. Produces the SVD factors, the condition assessment and the pseudoinverse that control-allocation leaves consume. Trigger: singular value decomposition, SVD, one-sided Jacobi, singular values, condition number, numerical rank, Moore-Penrose inverse, matrix factorization, rectangular matrix."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [singular-value-decomposition, one-sided-jacobi-svd, numerical-rank, condition-number-estimation, moore-penrose-inverse]
  version: 0.1.0
  author: AeroSkills
---

# Singular Value Decomposition (cross-cutting/numerics/singular-value-decomposition)

Use when a task needs the singular value decomposition of a general real
rectangular matrix: orthonormal factors U and V, singular values,
2-norm condition number, numerical rank and Moore-Penrose inverse. This
leaf implements the deterministic one-sided Jacobi SVD in pure Python,
stdlib only, for tall, square and wide matrices in economy form
A = U diag(s) Vh. It pairs with cross-cutting/numerics/matrix-operations
(square solves and determinants) and cross-cutting/numerics/eigenvalue-
decomposition (square symmetric spectra), and it supplies the
pseudoinverse that gnc control-allocation leaves consume but never
compute.

## Domain quick reference

- One-sided Jacobi: work on the columns of B = A (m >= n assumed). For
  every pair p < q compute alpha = sum_i B[i][p]^2, beta =
  sum_i B[i][q]^2, gamma = sum_i B[i][p] B[i][q]. When |gamma| > tol *
  sqrt(alpha * beta), rotate the pair with zeta = (beta - alpha) /
  (2 gamma), t = sign(zeta) / (|zeta| + sqrt(1 + zeta^2)), c = 1 /
  sqrt(1 + t^2), s = c t. The stable t = 1 is used when zeta is zero.
- Accumulation: each rotation right-multiplies the working matrix and
  the identity-start right factor V (column p <- c p - s q, column
  q <- s p + c q). Sweeps repeat until no pair exceeds tol (SVD_TOL =
  1e-14) or max_sweeps (SVD_MAX_SWEEPS = 60) is reached.
- Factors: singular values s_j are the final column norms, U columns
  the normalized final columns, Vh = V^T, with s sorted descending and
  U and Vh columns reordered consistently. Economy form: U m x r, s
  length r = min(m, n), Vh r x n. For m < n the problem is transposed
  and the factors swapped back (assumption: wide case solved on A^T).
- Reconstruction check: |A - U diag(s) Vh|_F is returned as
  reconstruction_residual and stays below 1e-12 on the tests.
- Condition number: s_max / s_min in the 2-norm; returns inf when the
  smallest singular value is zero.
- Numerical rank: count of singular values above rel_tol * s_max
  (RANK_REL_TOL = 1e-12 default).
- Moore-Penrose inverse: pinv = V diag(1/s_j) U^T, taking 1/s_j only
  for s_j above rel_tol * s_max and zero elsewhere.
- NACA-TR-824 frames the numerical-methods context; the relations above
  are standard engineering methodology, summary-only.

## Workflow

1. Validate the matrix: svd_jacobi raises ValueError for empty, ragged
   or non-numeric input before any arithmetic.
2. Decompose with svd_jacobi(A) to get the dict {u, s, vh,
   reconstruction_residual} in economy form.
3. Assess conditioning with condition_number(s): inf flags an exactly
   zero smallest singular value.
4. Count the effective rank with numerical_rank(s) or at a custom
   rel_tol for near-rank-deficient cases.
5. When a linear solve of a rectangular system is needed, form the
   Moore-Penrose inverse with moore_penrose_inverse(A).
6. Collect every output in one call with svd_report(A, tol,
   max_sweeps, rel_tol).
7. Confirm the deterministic anchors with the contract test
   scripts/test_singular_value_decomposition.py.

## Worked example

- A1 = [[3, 1], [1, 3]] (symmetric 2x2): s = [4.000000000000,
  2.000000000000] (the absolute eigenvalues 4 and 2), condition 2.0,
  reconstruction residual 1.3e-15.
- A2 = [[1, 1], [0, 0], [1, 0]] (3x2): s = [1.618033988750,
  0.618033988750] (phi and 1/phi from A^T A eigenvalues (3 +- sqrt(5))
  / 2), condition 2.618033988750, reconstruction residual 4.6e-16;
  |A pinv A - A|_F = 4.9e-16 for moore_penrose_inverse(A2).
- A3 = [[1, 2], [2, 4], [3, 6]] (rank-1 3x2): s = [8.366600265341,
  0.000000000000] with the nonzero value sqrt(70) exactly, numerical
  rank 1, condition inf, reconstruction residual 0.0.

## Pitfalls

- Reading the singular values of a symmetric matrix as signed
  eigenvalues: for A1 = [[3, 1], [1, 3]] the singular values are the
  absolute eigenvalues 4 and 2, so sign information does not survive in
  s.
- Treating a near-zero singular value as exactly zero: A3 returns s =
  [sqrt(70), 0.000000000000] with numerical rank 1, and the condition
  number is inf — rank and conditioning claims rest on the tolerance,
  not on the printed zero.
- Checking only one matrix orientation: the pseudoinverse is verified
  on the 3x2 case and its 2x3 transpose, and the reconstruction check
  covers square, tall, and wide matrices; a single orientation misses
  the transpose behavior.
- Confusing the condition number with reconstruction accuracy: A2 has
  condition 2.618 and residual 4.6e-16 — conditioning describes
  sensitivity, the residual describes factorization error.
- Feeding empty, ragged, or non-numeric matrices, or empty/negative
  singular value lists: all raise ValueError instead of returning a
  degraded factorization.
- Reaching for the SVD where a square solve belongs: matrix-operations
  owns the Gaussian solve sibling, and eigenvalue-decomposition owns
  square symmetric spectra; this leaf owns general rectangular
  factors.

## Verification

- Confirm svd_jacobi(A1) reports s [4, 2], condition 2.0 and residual
  about 1.3e-15; A2 reports phi and 1/phi with residual about 4.6e-16;
  A3 reports sqrt(70) and 0.0 with numerical rank 1.
- Confirm U diag(s) Vh rebuilt from the returned factors matches A to
  1e-12, on square, tall (m > n) and wide (m < n) matrices.
- Confirm moore_penrose_inverse satisfies |A pinv A - A| and
  |pinv A pinv - pinv| below 1e-10 on the 3x2 case and its 2x3
  transpose.
- Confirm ValueError rejection of empty, ragged and non-numeric
  matrices, empty singular value lists and negative singular values.
- Confirm identical outputs across repeated runs (no RNG).
- Run the contract test offline: python3
  scripts/test_singular_value_decomposition.py (29 tests,
  deterministic).

## Related leaves

- cross-cutting/numerics/matrix-operations: Gaussian solve sibling;
  boundary is square solves versus general SVD.
- cross-cutting/numerics/eigenvalue-decomposition: square symmetric
  spectra sibling; this leaf owns general rectangular factors.
- gnc-autonomy/control/control-allocation: consumer of a pseudoinverse
  that this leaf computes.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_singular_value_decomposition.py

The test covers the economy SVD shapes on square, tall and wide
matrices, the worked-example anchors A1, A2 and A3 (singular values,
condition, reconstruction residual, rank), the Moore-Penrose identities
on tall and wide cases, rank threshold behavior on identity, zero and
rank-1 matrices, 1x1 and fixed rectangular round trips, run-to-run
determinism and ValueError rejection of empty, ragged and non-numeric
input.

## Compliance

- Standards referenced, not reproduced: NACA-TR-824 frames the
  numerical-methods context; the SVD relations above are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

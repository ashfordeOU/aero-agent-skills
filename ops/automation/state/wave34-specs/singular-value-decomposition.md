# Wave-34 leaf spec: singular-value-decomposition (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/singular-value-decomposition/
- Pack: numerics. Closest siblings: matrix-operations (solves Ax=b,
  determinant, inverse by Gaussian elimination with partial pivoting,
  is_singular by pivot tolerance), eigenvalue-decomposition (power
  iteration and Jacobi spectra of square symmetric matrices). This leaf
  owns the SVD of GENERAL RECTANGULAR matrices by one-sided Jacobi:
  orthonormal U and V factors, singular values, 2-norm condition
  number, numerical rank, Moore-Penrose inverse. No function overlap.
- Standards id: naca-tr-824 (numerics pack convention; reference-only).
  Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Compute the singular value decomposition of a general real rectangular
matrix by one-sided Jacobi: iterate Jacobi rotations on the columns of
the working matrix to orthogonalize them, accumulating the right
factor, and return the left factor U, the singular values and the Vh
factor with A = U diag(s) Vh. Produce the 2-norm condition number, the
numerical rank at a relative tolerance, and the Moore-Penrose inverse.
Produces the SVD factors, the condition assessment and the
pseudoinverse that control-allocation and control-moment-gyro leaves
consume but never compute.

Does NOT do: Gaussian elimination solves/determinant/inverse of square
matrices (matrix-operations owns Ax=b and is_singular); power
iteration and Jacobi eigenvalue spectra of square SYMMETRIC matrices
(eigenvalue-decomposition); pseudoinverse REDISTRIBUTION control
allocation (gnc control-allocation consumes a pinv).

## Model (implement exactly)

One-sided Jacobi SVD (deterministic, stdlib only):
- Working matrix B = A (m x n, m >= n assumed; for m < n transpose
  the problem and swap U/V at the end - state this in the SKILL body
  and test the m x n and n x m cases).
- Repeat sweeps: for each column pair p < q, compute alpha =
  sum_i B[i][p]^2, beta = sum_i B[i][q]^2, gamma = sum_i B[i][p]
  B[i][q]. If |gamma| > tol * sqrt(alpha * beta), rotate columns p and
  q by the Jacobi angle zeta = (beta - alpha)/(2 gamma),
  t = sign(zeta)/(|zeta| + sqrt(1 + zeta^2)), c = 1/sqrt(1 + t^2),
  s = c t; update B columns and accumulate the right rotation V.
- Stop when the largest off-diagonal column-pair correlation is below
  tol (default 1e-14) or after max_sweeps (default 60).
- Singular values s_j = column norms of the final B; U columns are
  the normalized final B columns (unit); Vh = V^T with the accumulated
  rotations. Order s descending and reorder U/Vh columns consistently.
- Reconstruction residual |A - U diag(s) Vh|_F < 1e-12 on tests.

Constants:
- SVD_TOL = 1e-14; SVD_MAX_SWEEPS = 60.
- RANK_REL_TOL = 1e-12 (numerical rank default).

Functions (pure stdlib):
- svd_jacobi(A, tol = SVD_TOL, max_sweeps = SVD_MAX_SWEEPS) -> dict
  {u (m x n or m x m?), s (list length r = min(m,n)), vh (n x n),
  reconstruction_residual}. For the square/wide convention keep U as
  the full left factor with the same shape as A rows x min(m,n)... use
  the ECONOMY form consistent with the worked examples below: U m x r,
  s length r, Vh r x n where r = min(m, n) (state it clearly).
  ValueErrors: empty matrix, ragged rows, non-numeric entries.
- condition_number(s) -> s_max / s_min (2-norm condition).
  ValueError on empty s or any s < 0; s_min == 0 raises? No: return
  inf when the smallest singular value is 0 (state it), ValueError
  only on empty/negative.
- numerical_rank(s, rel_tol = RANK_REL_TOL) -> count of singular
  values > rel_tol * s_max. ValueError on empty s.
- moore_penrose_inverse(A, rel_tol = RANK_REL_TOL) -> pinv = V diag(
  1/s_j for s_j > rel_tol * s_max, else 0) U^T, computed from the SVD.
  ValueErrors on empty/ragged A.
- svd_report(A, tol, max_sweeps, rel_tol) -> dict with all outputs.

SVD identity to test: for a symmetric matrix the singular values equal
the absolute eigenvalues; A = U diag(s) Vh reconstructs A to 1e-12;
pinv satisfies the Moore-Penrose identities |A pinv A - A| small and
|pinv A pinv - pinv| small.

## Worked example

Reference matrices (independently verified at prep):
- A1 = [[3, 1], [1, 3]] (symmetric 2x2): singular values [2, 4]
  (absolute eigenvalues 2 and 4), condition 2.0, reconstruction
  residual about 1.3e-15.
- A2 = [[1, 1], [0, 0], [1, 0]] (3x2): A^T A = [[2, 1], [1, 1]]
  with eigenvalues (3 +- sqrt(5))/2 = 2.618034 and 0.381966, so
  singular values sqrt = [1.61803398875, 0.61803398875] (phi and
  1/phi), condition 2.618034, reconstruction residual about 4.6e-16,
  pinv identity |A pinv A - A| about 4.9e-16.
- A3 = [[1, 2], [2, 4], [3, 6]] (rank-1 3x2): singular values
  [0.0, 8.366600265341] = sqrt(14) sqrt(5) exactly (norm of the
  column [1,2,3] times [1,2]? verify: nonzero s = ||col1|| *
  ||col2||/||col1||? state as sqrt(1+4+9)*sqrt(1+4) = sqrt(70) =
  8.3666), numerical rank = 1.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds above. If a value falls outside its bound, your
implementation has a bug: find it before writing tests. In the SKILL.md
worked example show your module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: empty matrix; ragged rows; non-numeric entries; empty s;
  negative s.
- A1: singular values [2, 4] within 1e-9, condition 2.0,
  reconstruction residual < 1e-12.
- A2: singular values [1.61803398875, 0.61803398875] within 1e-9,
  condition 2.618034, residual < 1e-12, pinv identity < 1e-10.
- A3: singular values [0, 8.366600265341] within 1e-9, numerical rank
  1.
- Rank behavior: identity matrix rank = n; zero matrix rank = 0;
  numerical_rank counts only singular values above rel_tol * s_max.
- Moore-Penrose identities on a 2x3 wide matrix (transposed A2 case).
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-singular-value-decomposition.yaml)

Query 1 (copy verbatim):
  "compute the singular value decomposition of a rectangular matrix by one sided Jacobi rotations and return the singular values and condition number"
  intent: "cross-cutting; SVD by one-sided Jacobi, singular values and condition number"
  expected_skill: "cross-cutting/numerics/singular-value-decomposition"
Query 2 (copy verbatim):
  "compute the numerical rank and the Moore Penrose pseudoinverse of a matrix from its singular values"
  intent: "cross-cutting; numerical rank and Moore-Penrose pseudoinverse from SVD"
  expected_skill: "cross-cutting/numerics/singular-value-decomposition"
Task ids: w34-singular-value-decomposition-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must decompose a general real
rectangular matrix into its singular value factors:" and include the
outputs in the Claim. First tag: singular-value-decomposition.
Additional tags ONLY: one-sided-jacobi-svd, numerical-rank,
condition-number-estimation, moore-penrose-inverse. NEVER single
generic words (matrix, singular, value, decomposition, rank, inverse).
50-150 words, <=1000 chars, no em dash, no "classified", action verb
present.

FORBIDDEN TOKENS (belong to siblings): Gaussian elimination, Ax=b
solve, determinant, pivot (matrix-operations); eigenvalue, power
iteration, Jacobi spectra of symmetric matrices (eigenvalue-
decomposition owns the square symmetric spectrum). The words "singular
value decomposition", "numerical rank", "condition number", "Moore-
Penrose inverse" are this leaf's own. NOTE for the corpus queries: the
token pseudoinverse appears in gnc control-allocation corpus tasks
(w25-control-allocation-1/2) and MUST keep routing there; this leaf's
description is SVD-first with a single pseudoinverse mention.

Tags: [singular-value-decomposition, one-sided-jacobi-svd,
numerical-rank, condition-number-estimation, moore-penrose-inverse]

Sibling-citation lines for Related leaves:
cross-cutting/numerics/matrix-operations (Gaussian solve sibling;
boundary: square solves vs general SVD),
cross-cutting/numerics/eigenvalue-decomposition (square symmetric
spectra sibling),
gnc-autonomy/control/control-allocation (consumer of a pseudoinverse
that this leaf computes).

Ledger Standard: naca-tr-824.

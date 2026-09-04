# Wave-32 leaf spec: attitude-determination-quest (space-systems, adcs pack)

- Path: skills/space-systems/adcs/attitude-determination-quest/
- Pack: adcs. Sibling: attitude-determination-triad (exactly two
  vectors; its body explicitly defers N>2 Wahba/QUEST content:
  "Wahba solvers such as QUEST or the q-method generalize it to many
  observations").
- Standards id: ecss (reference-only; pack convention). Ledger
  Standard: ecss.
- Family: space-systems

## Claim

Determine the optimal spacecraft attitude from N >= 2 weighted vector
observations by minimizing Wahba's cost with the Davenport q-method
(QUEST-style): form the attitude-profile matrix B from the weighted
observation and reference pairs, assemble the symmetric 4x4 K matrix,
find the unit eigenvector of K for the largest eigenvalue with a
deterministic fixed-sweep Jacobi iteration, and return the optimal
attitude quaternion, the attitude matrix, the observation residuals
and the Wahba-cost minimality verdict. Produces the optimal quaternion,
the attitude matrix, the residuals and the consistency verdict that
gate a multi-vector attitude determination.

Does NOT do: two-vector attitude determination
(attitude-determination-triad owns the TRIAD solution for exactly two
nonparallel observations); quaternion algebra kernels
(cross-cutting/numerics/quaternion-algebra owns quaternion products and
conversions); attitude control or quaternion-error feedback
(reaction-wheel-control owns control); sensor-specific models
(star-tracker, sun-pointing own their measurement geometry).

## Model (implement exactly)

Convention (state in the SKILL body): observations b_i (unit vectors in
the BODY frame) relate to the reference vectors r_i (unit vectors in
the REFERENCE frame) by b_i = A(q) r_i with the ACTIVE rotation
convention A(q) v = q * (0, v) * q_conj under the Hamilton quaternion
product (q = (w, x, y, z) with w the scalar). Wahba's cost J(q) =
sum_i w_i * |b_i - A(q) r_i|^2 is minimized by the unit eigenvector of
K for the LARGEST eigenvalue. The construction below was verified to
recover the generating quaternion to 1e-9 on noise-free synthetic
observations; follow the z-vector sign and the scalar-last eigenvector
read exactly.

Constants:
- JACOBI_MAX_SWEEPS = 60, JACOBI_TOL = 1e-13.
- MIN_OBSERVATIONS = 2.

Functions (pure stdlib, deterministic):

- quat_product(q, r) -> Hamilton product (w, x, y, z):
  w = q0*r0 - q1*r1 - q2*r2 - q3*r3
  x = q0*r1 + q1*r0 + q2*r3 - q3*r2
  y = q0*r2 - q1*r3 + q2*r0 + q3*r1
  z = q0*r3 + q1*r2 - q2*r1 + q3*r0
- rotate_vector(q, v) -> A(q) v = quat_product(quat_product(q,
  (0, vx, vy, vz)), conjugate(q))[1:] with conjugate(q) = (w, -x,
  -y, -z).
- attitude_profile(observations, references, weights = None) -> 3x3
  B = sum_i w_i * b_i * r_i^T (list of lists).  ValueErrors: fewer
  than MIN_OBSERVATIONS observations, length mismatch, non-unit
  observation or reference vectors (norm outside 1 +- 1e-6), weights
  mismatch, weight <= 0.
- davenport_k_matrix(B) -> (K 4x4, sigma, z): sigma = trace(B);
  S = B + B^T; z = (B[2][1] - B[1][2], B[0][2] - B[2][0], B[1][0] -
  B[0][1]); K = [[S - sigma*I3, z], [z^T, sigma]]:
  K[i][j] = S[i][j] - (sigma if i == j else 0) for i,j in 0..2;
  K[i][3] = z[i], K[3][i] = z[i] for i in 0..2; K[3][3] = sigma.
  NOTE the z sign: this is the sign verified to recover the generating
  quaternion with the active A(q)v = q v q* convention.  If you flip
  the sign you recover the INVERSE rotation - keep it as written.
- jacobi_eigen_sym4(K) -> (eigenvalues, eigenvectors) by the
  fixed-sweep Jacobi rotation: repeatedly zero the largest off-diagonal
  entry with the rotation angle theta where tan(2*theta) = 2*K[p][q] /
  (K[q][q] - K[p][p]) (use atan2; theta = pi/4 when the diagonal
  entries are equal); accumulate V = V * J (columns are eigenvectors);
  stop when the largest off-diagonal magnitude < JACOBI_TOL or after
  JACOBI_MAX_SWEEPS.  Return eigenvalues (diagonal) and V.
  (Symmetric 4x4 input guaranteed by construction.)
- quest_solution(observations, references, weights = None) -> dict
  {q_optimal (w,x,y,z), lambda_max, attitude_matrix (3x3 from
  rotate_vector of the reference axes), residuals (list of
  |b_i - A(q) r_i| per observation), wahba_cost, identity_ok}
  where: B = attitude_profile(...); (K, sigma, z) =
  davenport_k_matrix(B); (eigs, V) = jacobi_eigen_sym4(K); lambda_max
  = max(eigs); the optimal quaternion is the eigenvector column of V
  for the largest eigenvalue read SCALAR-LAST: q = (V[3][imax],
  V[0][imax], V[1][imax], V[2][imax]); normalize q; attitude_matrix
  rows are rotate_vector(q, e_i) for the three reference axes e_1,
  e_2, e_3; residuals per observation; wahba_cost = sum_i w_i *
  |b_i - A(q) r_i|^2; identity_ok = max residual < 1e-6 (used by the
  contract test on noise-free data).  ValueErrors propagate.
- wahba_cost(q, observations, references, weights) -> float (the cost
  of an arbitrary quaternion; used for the minimality check).
- attitude_matrix_from_quaternion(q) -> 3x3 rows rotate_vector(q,
  (1,0,0)), rotate_vector(q, (0,1,0)), rotate_vector(q, (0,0,1)).

ALL functions deterministic, no RNG, stdlib only (math.sqrt etc.).

## Worked example

Three noise-free synthetic observations generated from a KNOWN attitude
q_true = 90-degree rotation about the body z axis: q_true = (cos(pi/4),
0, 0, sin(pi/4)) = (0.70710678, 0, 0, 0.70710678).  Reference vectors
r = [(1,0,0), (0,1,0), (0,0,1)]; observations b_i = rotate_vector
(q_true, r_i) = [(0,1,0), (-1,0,0), (0,0,1)].  All weights 1.0.

Run your module and take the real outputs as assert targets, then check
the bounds:
- q_optimal recovers q_true to 1e-9 (up to the global sign: q and -q
  are the same rotation, so compare max(|q-q_true|, |q+q_true|) <
  1e-9).
- lambda_max about 3.0 (trace of B with three unit-weight
  observations of a pure rotation).
- identity_ok True (max residual < 1e-6).
- wahba_cost of q_optimal ~ 0 (within 1e-9); a perturbed quaternion
  has strictly larger cost: wahba_cost(q_perturbed) > wahba_cost(q) +
  1e-9.
- attitude_matrix_from_quaternion(q_optimal) rows are the observed
  body axes: row 0 = (0,1,0), row 1 = (-1,0,0), row 2 = (0,0,1)
  (within 1e-9).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: fewer than 2 observations; length mismatch; non-unit
  vectors (norm outside 1 +- 1e-6); weight <= 0; weights length
  mismatch.
- Recovery: the worked example recovers q_true to 1e-9 (sign-aware
  comparison).
- A second worked case: q_true = 45-degree rotation about the (1,1,1)/
  sqrt(3) axis, six reference vectors [(1,0,0),(0,1,0),(0,0,1),
  (1,1,0),(1,-1,0),(0,1,1)] (normalize the non-unit ones) - recovers
  to 1e-9 (this non-symmetric case catches z-vector sign slips).
- Minimality: a perturbed quaternion has strictly larger Wahba cost.
- Consistency: A(q) r_i == b_i to 1e-9 on the noise-free example.
- Determinism: two runs return identical floats (no RNG).
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave32-attitude-determination-quest.yaml)

Query 1 (copy verbatim):
  "determine the optimal spacecraft attitude quaternion from multiple weighted vector observations by minimizing the Wahba cost with the Davenport q method"
  intent: "space-systems; optimal attitude determination from many observations"
  expected_skill: "space-systems/adcs/attitude-determination-quest"
Query 2 (copy verbatim):
  "run the quest attitude determination algorithm to compute the attitude matrix and the observation residuals from three reference and body vector pairs"
  intent: "space-systems; QUEST attitude matrix and residuals"
  expected_skill: "space-systems/adcs/attitude-determination-quest"
Task ids: w32-attitude-determination-quest-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must determine the optimal attitude
of a spacecraft from multiple vector observations by the Davenport
q-method:" and include the outputs in the Claim. First tag:
attitude-determination-quest. Additional tags ONLY: wahba-problem,
davenport-q-method, optimal-attitude-quaternion,
multi-vector-observation, observation-weighting,
attitude-determination-consistency, quaternion-cost-minimization.
NEVER single generic words (attitude, quaternion, determination,
vector, observation). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): TRIAD, two observations, two
vector (attitude-determination-triad); quaternion algebra, spherical
linear interpolation, quaternion product kernel
(cross-cutting/numerics/quaternion-algebra); reaction wheel, control
law, quaternion error feedback (reaction-wheel-control); star
identification (star-tracker); sun vector (sun-pointing).

Tags: [attitude-determination-quest, wahba-problem,
davenport-q-method, optimal-attitude-quaternion,
multi-vector-observation, observation-weighting,
attitude-determination-consistency, quaternion-cost-minimization]

Sibling-citation lines for Related leaves:
space-systems/adcs/attitude-determination-triad (two-vector sibling
that defers N>2 content here), space-systems/adcs/star-tracker,
cross-cutting/numerics/quaternion-algebra, gnc-autonomy/space/
attitude-dynamics.

Ledger Standard: ecss.

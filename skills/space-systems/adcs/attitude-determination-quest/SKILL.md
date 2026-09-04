---
name: attitude-determination-quest
description: "Use when you must determine the optimal attitude of a spacecraft from multiple vector observations by the Davenport q-method: minimize the Wahba cost over N >= 2 weighted body and reference direction pairs, form the attitude profile matrix B, assemble the symmetric 4x4 Davenport K matrix, and extract the largest eigenvalue eigenvector with a deterministic fixed-sweep Jacobi iteration. Produces the optimal attitude quaternion, the 3x3 attitude matrix, the per-observation residuals, the achieved Wahba cost and the consistency verdict that gate a multi-vector attitude determination. Trigger: wahba problem, davenport q method, quest, optimal attitude quaternion, attitude matrix, observation residuals, body vector, reference vector, multi-vector attitude determination."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: adcs
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: adcs
  tags: [attitude-determination-quest, wahba-problem, davenport-q-method, optimal-attitude-quaternion, multi-vector-observation, observation-weighting, attitude-determination-consistency, quaternion-cost-minimization]
  version: 0.1.0
  author: Aero Agent Skills
---

# Attitude Determination by the Davenport q-Method (space-systems/adcs/attitude-determination-quest)

Use when the task is optimal spacecraft attitude determination from
multiple weighted vector observations: fitting one rotation to N >= 2
body and reference direction pairs by minimizing Wahba's cost with the
Davenport q-method (QUEST-style), and gating the result on the
observation residuals and the consistency verdict. This leaf implements
the full pipeline in pure Python (stdlib only, deterministic): the
attitude profile matrix, the symmetric 4x4 K matrix, the fixed-sweep
Jacobi eigen-solution, and the scalar-last eigenvector read. It is the
N > 2 complement of the pair-based sibling leaf attitude-determination-triad,
and it consumes quaternion products through rotate_vector internally so
the numerics stay self-contained. Star-tracker and sun-pointing supply
the sensor directions this method consumes.

Convention: observations b_i (unit vectors in the BODY frame) relate to
the reference vectors r_i (unit vectors in the REFERENCE frame) by
b_i = A(q) r_i with the ACTIVE rotation convention A(q) v = q * (0, v) *
q_conj under the Hamilton quaternion product, q = (w, x, y, z) with w
the scalar.

## Domain quick reference

- Wahba's cost: J(q) = sum_i w_i * |b_i - A(q) r_i|^2, with w_i the
  positive weight of observation i. The optimal attitude is the unit
  eigenvector of K for the LARGEST eigenvalue; the remaining
  eigenvalues bound the attainable cost.
- Attitude profile matrix: B = sum_i w_i * b_i * r_i^T (3x3). Its trace
  sigma = trace(B) feeds the K construction.
- Davenport K matrix: S = B + B^T; z = (B[2][1]-B[1][2], B[0][2]-B[2][0],
  B[1][0]-B[0][1]); K = [[S - sigma*I3, z], [z^T, sigma]]. K is symmetric
  4x4 by construction. The z-vector sign shown here is the one verified
  to recover the generating quaternion under the active rotation
  convention; flipping it recovers the inverse rotation instead.
- Eigen-solution: fixed-sweep Jacobi rotations zero the largest
  off-diagonal entry, theta = 0.5 * atan2(2*K[p][q], K[q][q]-K[p][p])
  (theta = pi/4 when the diagonal entries are equal), stopping when the
  largest off-diagonal magnitude drops below JACOBI_TOL = 1e-13 or after
  JACOBI_MAX_SWEEPS = 60 sweeps.
- Eigenvector read SCALAR-LAST: the optimal quaternion is q =
  (V[3][imax], V[0][imax], V[1][imax], V[2][imax]) for the column imax of
  the largest eigenvalue, normalized to unit length. q and -q denote the
  same rotation.
- Consistency verdict: identity_ok = (max residual < 1e-6), where the
  residual of observation i is |b_i - A(q) r_i|.
- Outputs: the optimal quaternion, lambda_max, the 3x3 attitude matrix
  whose rows are A(q) applied to the reference axes, the residuals, the
  achieved Wahba cost, and identity_ok.

## Workflow

1. Collect the measured unit directions in the body frame and the
   matching unit directions in the reference frame (star tracker or sun
   sensor outputs against an ephemeris or star catalog).
2. Check the vectors are unit length: attitude_profile raises ValueError
   for non-unit vectors, fewer than MIN_OBSERVATIONS = 2 observations,
   count mismatches, weight mismatches and non-positive weights.
3. Build B = attitude_profile(observations, references, weights) with
   the per-observation confidence weights (optional, default all ones).
4. Assemble the Davenport matrix with davenport_k_matrix(B), returning
   (K, sigma, z); keep the z sign as returned.
5. Solve the eigen-problem with jacobi_eigen_sym4(K), pick the largest
   eigenvalue lambda_max and its eigenvector column.
6. Read the quaternion scalar-last and normalize; recover the attitude
   matrix with attitude_matrix_from_quaternion.
7. Get the full verdict from quest_solution(observations, references,
   weights): q_optimal, lambda_max, attitude_matrix, residuals,
   wahba_cost and identity_ok.
8. Check minimality with wahba_cost on a perturbed quaternion: the
   optimal attitude must sit strictly below every neighbor in cost.
9. Confirm the deterministic behavior with the contract test
   scripts/test_attitude_determination_quest.py.

## Worked example

Three noise-free synthetic observations generated from a KNOWN attitude
q_true = 90-degree rotation about the body z axis: q_true =
(cos(pi/4), 0, 0, sin(pi/4)) = (0.70710678, 0, 0, 0.70710678).
Reference vectors r = [(1,0,0), (0,1,0), (0,0,1)]; observations
b_i = A(q_true) r_i = [(0,1,0), (-1,0,0), (0,0,1)]. All weights 1.0.

quest_solution on this data returns the real module outputs:

- q_optimal = (0.70710678, 0.0, 0.0, 0.70710678), recovering q_true to
  a sign-aware error of 1.1e-16 (spec bound 1e-9).
- lambda_max = 3.0000000000000004, about 3.0 as expected for three
  unit-weight observations of a pure rotation.
- wahba_cost = 1.2e-31 (spec bound 1e-9); identity_ok True; residuals
  per observation [2.5e-16, 2.5e-16, 0.0].
- attitude_matrix rows are the observed body axes (0,1,0), (-1,0,0),
  (0,0,1) to 3.3e-16.
- A quaternion perturbed by an extra 5.7-degree rotation about z has
  Wahba cost 0.01998, strictly larger than the optimum plus 1e-9, so
  the minimality verdict holds.

A second non-symmetric case, 45 degrees about the (1,1,1)/sqrt(3) axis
with six reference vectors [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,-1,0),
(0,1,1)] (the last three normalized), recovers q_true =
(0.92387953, 0.22094238, 0.22094238, 0.22094238) to 1.1e-16; this case
catches z-vector sign slips, since a flipped sign recovers the inverse
rotation and fails the 1e-9 consistency check on A(q) r_i = b_i.


## Pitfalls

- Feeding unnormalized or mis-sized inputs: attitude_profile raises
  ValueError for non-unit vectors (norm outside 1 +- 1e-6), fewer than
  MIN_OBSERVATIONS = 2 observations, count mismatches, weight
  mismatches, and non-positive weights.
- Flipping the z-vector sign when assembling K: the sign documented in
  this leaf is the one verified to recover the generating quaternion
  under the active rotation convention; a flipped sign recovers the
  inverse rotation and fails the A(q) r_i = b_i consistency check.
- Reading the eigenvector in the wrong layout: the optimal quaternion
  is read SCALAR-LAST from the Jacobi eigen-solution, and q and -q
  denote the same rotation, so sign-aware comparison (min over q and
  -q) is required when validating against a known truth.
- Trusting the optimum without the minimality check: confirm the
  achieved Wahba cost sits strictly below a perturbed neighbor plus
  1e-9 before gating the attitude reference.
- Confusing this leaf with its pair-based sibling: QUEST/Davenport is
  the N > 2 complement of attitude-determination-triad; a single pair
  of directions belongs to the triad leaf.
- Replacing the fixed-sweep Jacobi solver with an RNG-based one: this
  pipeline is deterministic by contract, and two consecutive runs must
  return byte-identical floats.
## Verification

- Confirm quest_solution recovers both generating quaternions above to
  1e-9 with the sign-aware comparison min over q and -q.
- Confirm lambda_max is about 3.0 and identity_ok is True on the
  noise-free worked example.
- Confirm the perturbed-quaternion Wahba cost is strictly larger than
  the optimal cost plus 1e-9.
- Confirm A(q) r_i equals b_i to 1e-9 on both worked cases (active
  rotation convention consistency).
- Confirm two consecutive runs return byte-identical floats (no RNG).
- Confirm ValueError rejection: fewer than 2 observations, count
  mismatch, non-unit vectors (norm outside 1 +- 1e-6), non-positive
  weights, weight length mismatch.
- Confirm the solution dict exposes exactly the six documented keys.
- Run the offline contract test: python3
  scripts/test_attitude_determination_quest.py (34 tests, deterministic).

## Related leaves

- space-systems/adcs/attitude-determination-triad: the pack sibling for
  the pair-of-directions case, whose body defers the N > 2 Wahba content
  to this leaf.
- space-systems/adcs/star-tracker: supplies the measured body-frame
  directions this method consumes.
- cross-cutting/numerics/quaternion-algebra: quaternion products and
  conversions for downstream quaternion use; this leaf keeps its own
  internal product kernels so the pipeline is self-contained.
- gnc-autonomy/space/attitude-dynamics: the dynamics context around the
  attitude estimate this leaf produces.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_attitude_determination_quest.py

The test covers quaternion product identities and closed-form values,
the active rotation convention, the 90-degree z worked example
(recovery to 1e-9, lambda_max about 3.0, near-zero Wahba cost, matrix
rows equal to the observed axes, exact documented keys), minimality
under perturbation, the second 45-degree (1,1,1)/sqrt(3) six-observation
case with per-observation consistency, ValueError rejection of all
non-physical inputs, the Jacobi reconstruction identity on K,
determinism across runs, and weighted recovery.

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-60 frames attitude
  determination for European missions; the Davenport q-method and the
  Wahba cost are open attitude-determination literature, summary-only
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

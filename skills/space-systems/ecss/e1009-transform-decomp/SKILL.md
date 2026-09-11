---
name: e1009-transform-decomp
description: "Use when decompose a spacecraft coordinate transformation chain per ECSS-E-ST-10-09C §5.4.8: validate each rotation matrix for orthogonality and proper orientation (determinant +1), determine the ordering of translation and rotation primitives in the chain, resolve a composed rotation into its Euler angle sequence, compose a series of elementary transforms into a single homogeneous matrix, and verify roundtrip consistency. Apply at any stage of mission reference frame analysis where transformation chains must be broken into auditable primitive steps. Trigger: ecss, e-st-10-09c, e-st-10-system-scope, reference-frames, transformation-chain, rotation-matrix, euler-angles, homogeneous-transform."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-10-09c, e-st-10-system-scope, reference-frames, transformation-chain, rotation-matrix, euler-angles, homogeneous-transform]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Reference Frames — Transformation Chain Decomposition (space-systems/ecss/e1009-transform-decomp)

Use when the task is decomposing a coordinate transformation chain under
ECSS-E-ST-10-09C §5.4.8 — identifying and ordering the elementary rotation
and translation primitives that make up a composite frame change, validating
each primitive, and verifying that the composed chain matches the mission
reference frame convention.

## Domain quick reference

- A transformation chain is a sequence of coordinate frame changes expressed
  as a product of elementary matrices. Each link is either a pure rotation
  (3×3 proper rotation matrix) or a pure translation (3-vector offset), or
  both encoded as a 4×4 homogeneous matrix.
- A rotation matrix R is proper when R^T R = I (orthogonal) and det(R) = +1.
  A matrix with det = −1 is an improper rotation (reflection); it is not a
  valid frame rotation and must be rejected before entering the chain.
- Euler angle sequences express a composed rotation as three successive
  elementary rotations about coordinate axes. Twelve sequences are valid
  (six Tait-Bryan: 1-2-3, 1-3-2, 2-1-3, 2-3-1, 3-1-2, 3-2-1; and six
  proper Euler: 1-2-1, 1-3-1, 2-1-2, 2-3-2, 3-1-3, 3-2-3). The 3-2-1
  (ZYX) sequence is conventional for spacecraft attitude; 3-1-3 (ZXZ) is
  common for orbital mechanics.
- A homogeneous matrix combines a rotation and a translation in a single
  4×4 block: top-left 3×3 is the rotation R, top-right 3×1 column is the
  translation t, bottom row is [0 0 0 1]. Chaining homogeneous matrices by
  matrix multiplication correctly propagates both rotation and translation.
- Translation and rotation do not commute: rotate-then-translate and
  translate-then-rotate produce different physical results. The order must
  be made explicit in the chain and must match the reference frame definition.
- The 3-2-1 Euler sequence is singular when the middle (pitch) angle reaches
  ±90°. Near that singularity the yaw and roll angles are not independently
  recoverable — flag the singularity and do not attempt extraction.

## Workflow

1. List every step in the transformation chain and assign each step a type:
   rotation (supply a 3×3 matrix or an Euler axis sequence with angles) or
   translation (supply a 3-vector offset). Reject any step whose type is
   unrecognized before it enters the chain.
2. For every rotation step, validate the rotation matrix: check R^T R = I
   within a tolerance of 1 × 10^−6 and check det(R) = +1. Report the
   specific element that first violates orthogonality and the actual
   determinant value. Do not proceed past a failing matrix.
3. Record the intended application order for each chain link. The order is
   a design choice derived from the reference frame definition; it must be
   stated explicitly. Build each step's 4×4 homogeneous matrix from its
   rotation and translation components.
4. Compose the chain by left-multiplying the homogeneous matrices in order
   (index 0 leftmost in the product, applied last to an input vector; index
   n−1 rightmost, applied first). The composite matrix is a valid homogeneous
   transform if its top-left 3×3 block is a proper rotation matrix.
5. If an Euler angle sequence is specified, verify the sequence is one of the
   12 valid sequences. Check for gimbal lock (the 3-2-1 sequence is singular
   at |sin θ| > 1 − 10^−8). Decompose the composed rotation into the
   designated Euler angles and verify the roundtrip: recompose from the
   extracted angles and compare to the original matrix element-by-element.
6. Report any failures: non-orthogonal matrix, improper rotation, wrong chain
   ordering, invalid Euler sequence, gimbal lock, or roundtrip error beyond
   tolerance. A chain is not decomposition-complete until all steps pass.

## Pitfalls

- Treating translation and rotation as commutative in a chain. They are not;
  swapping the two in a chain changes the physical frame relationship.
- Accepting an improper rotation (det = −1) without detecting it. The
  resulting frame has a handed inversion that corrupts all downstream
  coordinate computations.
- Attempting Euler angle extraction near the 3-2-1 gimbal-lock singularity
  (pitch near ±90°). The cos(θ) denominator in the yaw/roll formulas tends
  to zero, and the extracted angles are numerically meaningless.
- Carrying roundtrip tolerance above 10^−6 for a single rotation. Numerical
  error accumulates in long chains; a per-step tolerance budget must be
  stated and checked explicitly.
- Treating a valid Euler sequence as interchangeable with another sequence
  bearing the same angles. The same three angles under the 3-2-1 and 3-1-3
  sequences produce entirely different rotations.

## Behavior contract (gate 3)

The rotation validation, Euler composition and decomposition, homogeneous
transform composition, and chain validation logic is exercised by the gate 3
contract test: scripts/test_e1009_transform_decomp.py against
scripts/e1009_transform_decomp_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_transform_decomp.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

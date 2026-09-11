---
name: e1009-notation
description: "Use when verify that all frames, coordinate systems, and transformation data in exchanged engineering products comply with the ECSS-E-ST-10C §5.3.2 standard notation: confirm each frame identifier is an uppercase alphanumeric label, confirm each rotation matrix is orthogonal with determinant +1, confirm each quaternion carries unit norm, confirm each Euler-angle representation declares an explicit 3-digit axis-sequence code with no two adjacent axes identical, confirm every annotated vector carries a frame label, confirm transformation chains are gap-free between consecutive steps, and flag any exchange record that omits a mandatory notation field. Trigger: ecss, e-st-10-system-scope, notation, coordinate-frame, rotation-matrix, quaternion, euler-angles, frame-annotation, transformation, interface-data."
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
  tags: [ecss, e-st-10-system-scope, notation, coordinate-frame, rotation-matrix, quaternion, euler-angles, frame-annotation, transformation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Systems Engineering — Standard Notation (space-systems/ecss/e1009-notation)

Use when the task is to verify that frames, coordinate systems, and
transformation data in all exchanged engineering products follow the
standard notation required by ECSS-E-ST-10C §5.3.2 — checking frame
labels, rotation matrices, quaternions, Euler-angle sequences, annotated
vectors, and exchange record completeness.

## Domain quick reference

- Every coordinate frame used in an interface data product must carry
  an identifier that is an uppercase alphanumeric label (letters A–Z,
  digits 0–9, underscore), starting with a letter. Examples of
  well-formed labels: ECI, ECEF, LVLH, RTN, BODY, SOLAR_ARRAY_1.
  Mixed-case or hyphenated labels do not conform.
- Rotation matrices representing a frame transformation must be proper
  rotation matrices: the matrix R must satisfy R^T · R = I (orthogonality)
  and det(R) = +1. A matrix with det = −1 is a reflection, not a rotation,
  and must be rejected. Numerical tolerance of 1 × 10⁻⁶ applies to both
  checks.
- Quaternions must be unit-normalised: the Euclidean norm of the
  four-component vector must equal 1.0 within 1 × 10⁻⁶. Both
  scalar-first [w, x, y, z] and scalar-last [x, y, z, w] conventions
  are accepted; the norm check is convention-agnostic.
- Euler-angle parameterisations must declare an explicit three-digit axis
  sequence code (e.g., "313", "321"). Each digit must be 1, 2, or 3
  (the three orthogonal body axes). No two consecutive digits may be
  identical; adjacent identical axes degenerate the representation.
- Any vector quantity in a data exchange product must carry an explicit
  frame annotation — a "frame" field naming the coordinate frame in
  which the components are expressed. An un-annotated vector cannot be
  unambiguously interpreted by a receiving system.
- A transformation chain connecting frame A to frame C through
  intermediate frame B must be gap-free: the to_frame of each step
  must equal the from_frame of the next step. A chain with a mismatch
  cannot be composed into a single transformation without an undefined
  segment.

## Workflow

1. Collect every frame identifier appearing in the exchange data product
   and validate each one: uppercase alphanumeric starting with a letter,
   no hyphens or spaces. Reject and report any non-conforming label
   before proceeding.
2. For each rotation matrix in the product, run the two-part check:
   orthogonality (R^T · R ≈ I) and proper-rotation (det(R) ≈ +1).
   Record the specific failing element or determinant value in the
   finding; do not collapse both checks into a single boolean.
3. For each quaternion, compute the squared norm and compare it to 1.0
   within tolerance. A quaternion with norm significantly above 1.0 is
   unnormalised; one significantly below 1.0 is corrupt. Report both
   cases with the actual norm value.
4. For each Euler-angle set, verify the declared sequence code: three
   digits, each in {1, 2, 3}, no adjacent pair identical. Flag a
   missing sequence code and a malformed one separately — an absent
   code means the interpretation is ambiguous, a malformed code means
   it was present but invalid.
5. For each vector field in the exchange product, confirm a "frame"
   annotation is present and that the named frame passed step 1.
   Flag missing annotations and references to undefined frames
   separately.
6. For each declared transformation chain, walk the steps in order and
   confirm the to_frame of step i matches the from_frame of step i + 1.
   Report the index and the mismatched frame labels for each gap found.
7. Validate each exchange record for mandatory fields: "frame",
   "representation" (must be one of: matrix, quaternion, euler_angles),
   and "payload". Records using "euler_angles" additionally require
   "euler_sequence". Report each missing or invalid field individually.
8. A data product is notation-compliant only when all seven checks
   produce empty finding lists. Partial passes are not compliant.

## Pitfalls

- Accepting a rotation matrix on the basis of visual inspection alone —
  floating-point rounding in rotation composition can accumulate errors
  that break orthogonality; the numerical check is mandatory.
- Treating det = −1 as "close enough" to +1 — a reflection composed
  with a rotation silently flips handedness in derived products, which
  is a systematic error, not a rounding artifact.
- Omitting the axis-sequence code when Euler angles are used on the
  grounds that the receiving system "knows the convention" — a
  downstream system that infers the convention incorrectly applies the
  wrong rotation, with no detectable error at the interface boundary.
- Assuming a vector is in the spacecraft body frame because that is the
  dominant frame in the document — an explicit frame annotation is
  required regardless of the surrounding context.
- Validating each transformation in isolation without checking chain
  continuity — a gap in the chain means the composed transformation is
  undefined even if every individual matrix is a valid rotation matrix.

## Behavior contract (gate 3)

The frame-label, rotation-matrix, quaternion, Euler-sequence, vector-
annotation, exchange-record, and transformation-chain logic is exercised
by the gate 3 contract test: scripts/test_e1009_notation.py against
scripts/e1009_notation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_notation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

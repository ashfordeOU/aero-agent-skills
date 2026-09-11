---
name: e1009-transform-def
description: "Use when define each coordinate transformation in a spacecraft or system
  model under ECSS-E-ST-10-09C §5.4.9: specify every transform with a verbal statement,
  a rotation-matrix equation, and a figure reference; express each matrix relative to
  its parent frame using a declared row-column convention; and verify that numerical
  precision is consistent across all entries in the model. Check orthogonality
  (R^T R = I, determinant +1) for each rotation matrix, confirm the parent frame is
  in the defined frame set, and flag any transform missing its verbal description,
  figure reference, or declared convention. Trigger: ecss, e-st-10-system-scope,
  coordinate-transformation, rotation-matrix, parent-frame, row-column-convention,
  precision-consistency, frame-definition."
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
  tags: [ecss, e-st-10-system-scope, coordinate-transformation, rotation-matrix, parent-frame, row-column-convention, precision-consistency, frame-definition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coordinate Transformations — Definition and Convention (space-systems/ecss/e1009-transform-def)

Use when the task is to document every coordinate transformation in a spacecraft
or system model per ECSS-E-ST-10-09C §5.4.9 — pairing a verbal description and a
rotation-matrix equation with a figure reference for each transform, enforcing a
declared row-column convention across the whole model, and checking that numerical
precision is uniform throughout.

## Domain quick reference

- §5.4.9 requires that each transformation be expressed in three complementary
  forms: a verbal statement naming the origin and destination frames, a
  mathematical 3×3 rotation matrix written relative to the parent frame, and a
  graphical illustration (figure or drawing) that makes the angular relationship
  unambiguous.
- All rotation matrices in the model must follow one declared row-column
  convention — typically the Direction Cosine Matrix (DCM) convention where
  rows are the child-frame unit vectors expressed in the parent frame, or an
  alternative active/passive sign convention. Mixing conventions within one
  model is a root cause of sign errors; the convention is an attribute of the
  model, not of individual transforms.
- A valid rotation matrix is orthogonal: the product of its transpose with
  itself equals the identity matrix (R^T R = I) and its determinant equals +1.
  A determinant of -1 signals an improper rotation (reflection); both conditions
  are checked as part of the definition audit.
- Precision consistency means all transforms in the set carry the same number
  of significant decimal places. An entry defined to two decimal places while
  others carry fifteen-digit floating-point values introduces a hidden error
  budget that the model does not account for.
- Each matrix is referenced to its parent frame — the frame from which the
  rotation is measured. That parent frame must appear in the model's defined
  frame set; an undefined parent frame breaks the transformation chain.

## Workflow

1. List every coordinate transformation in the model and confirm that each one
   names a parent frame and a child frame. Reject any entry that is missing
   either frame name before continuing.
2. For each transform, check that a verbal description is on record and that it
   references the parent frame by name. A description that says "rotation about
   Z" without naming the parent frame is incomplete.
3. Verify that a figure reference is on record for each transform (drawing
   number, figure label, or equivalent). Flag any entry without a graphical
   reference as incomplete per §5.4.9.
4. Declare the model-wide row-column convention (DCM, active, or passive).
   Check that every transform entry carries the same declared convention; flag
   any that deviate.
5. For each rotation matrix, verify orthogonality: compute R^T R and compare to
   the 3×3 identity matrix within a tolerance (default 1 × 10^-6 Frobenius
   norm). Also check that the determinant equals +1 within the same tolerance.
   Flag non-orthogonal matrices and matrices with determinant ≠ +1 separately.
6. Confirm that every parent frame named in the transform set is present in the
   model's defined frame list. Flag transforms whose parent frame has no
   definition on record.
7. Check numerical precision consistency across all matrices: compute the
   maximum number of significant decimal places used in each matrix, assign
   each a precision level (low ≤ 2 dp, medium 3–6 dp, high ≥ 7 dp), and flag
   any entry whose precision level differs from the set's highest level.
8. Aggregate findings by transform entry; a transform is compliant when it has
   a verbal description, a figure reference, an orthogonal matrix with
   determinant +1, a parent frame on record, the model-wide convention, and
   precision consistent with the rest of the model.

## Pitfalls

- Defining the rotation matrix relative to the child frame instead of the
  parent frame — §5.4.9 requires the parent-frame reference; inverting the
  relation without documenting it is a common source of cascading sign errors
  in the transformation chain.
- Omitting the graphical representation on the grounds that the matrix is
  sufficient — the figure is not optional; it is the one artifact that makes
  the angular sense unambiguous to reviewers who did not build the model.
- Leaving the row-column convention undeclared and trusting that all engineers
  share the same assumption — when the convention is implicit, the first
  engineer to hand the model to a new team member inherits an integration risk.
- Treating orthogonality as guaranteed because the matrix was generated by a
  library — accumulated floating-point error in long transformation chains can
  push R^T R away from identity; the check is a safeguard, not a formality.
- Defining some transforms at full floating-point precision and others to two
  or three rounded places — the lower-precision entries dominate the total
  angular error budget and the inconsistency is invisible until the model is
  compared end-to-end.

## Behavior contract (gate 3)

The transform-completeness, orthogonality, parent-frame, convention, and
precision-consistency logic is exercised by the gate 3 contract test:
scripts/test_e1009_transform_def.py against
scripts/e1009_transform_def_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_transform_def.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

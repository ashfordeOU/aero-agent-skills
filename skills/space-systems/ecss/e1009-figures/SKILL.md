---
name: e1009-figures
description: "Use when verify that coordinate-frame relationship diagrams conform
  to ECSS-E-ST-10-09C §5.3.3 figure conventions: confirm each diagram carries a
  complete annotation set (figure ID, title, origin description, all three axis labels,
  and frame name), validate the three axes form a right-handed orthogonal triad,
  check that any Euler-angle rotation sequence is a valid proper-Euler or Tait-Bryan
  form (three characters, no two consecutive identical axes), and confirm the frame
  type falls within the recognized ECSS categories (body, orbital, sensor, structural,
  inertial). Applies to coordinate-system diagrams entering a system data package or
  design review under ECSS-E-ST-10C. Trigger: ecss, e-st-10-system-scope,
  coordinate-frame, figure-convention, right-hand-rule, euler-sequence, axis-labeling,
  frame-diagram, coordinate-relationship."
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
  tags: [ecss, e-st-10-system-scope, coordinate-frame, figure-convention, right-hand-rule, euler-sequence, axis-labeling, frame-diagram, coordinate-relationship]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Engineering — Coordinate-Frame Figure Conventions (space-systems/ecss/e1009-figures)

Use when the task is to verify that coordinate-frame relationship diagrams in a
space-system data package conform to the figure conventions of ECSS-E-ST-10-09C
§5.3.3 — checking annotation completeness, axis handedness, rotation-sequence
format, and frame-type categorization before the diagram enters a design review
or deliverable document.

## Domain quick reference

- §5.3.3 requires that every coordinate-frame diagram in an ECSS deliverable
  carry four mandatory annotations: a unique figure identifier, a descriptive
  title, an explicit origin description (physical point or reference body fixed
  to which the frame is attached), and labels for all three axes.
- Each frame must belong to one of five ECSS-defined categories — body, orbital,
  sensor, structural, or inertial — which controls how it participates in the
  coordinate-transformation chain documented in the system-level axis
  relationship tree.
- The three axes of any coordinate frame must form a right-handed orthogonal
  triad: axis x, axis y, and axis z such that z = x cross y. This convention
  is mandatory across all ECSS coordinate diagrams; left-handed systems are
  never used.
- When a figure depicts the angular orientation of one frame relative to another,
  the rotation must be parameterized by an Euler-angle sequence. The sequence
  must be three axis designators (digits 1–3 or letters x/y/z), and no two
  consecutive designators may be identical; this distinguishes valid proper-Euler
  (e.g. 3-1-3) and Tait-Bryan (e.g. 3-2-1) sequences from degenerate forms.
- Figures showing a frame relationship must also identify the parent reference
  frame from which the rotation is applied.

## Workflow

1. Collect all coordinate-frame diagrams in the data package and assign each a
   FigureSpec record: figure ID, title, frame type, origin description, axis
   vectors, and optionally a reference frame and Euler-sequence with angles.
2. Run `check_figure_completeness` on each FigureSpec. This confirms the four
   mandatory annotations are present and non-blank and that all three axis labels
   appear. Flag every missing annotation as a finding before proceeding.
3. Run `validate_frame_type` to confirm the frame's category is one of the five
   ECSS-recognized types. A frame with an unrecognized type cannot be placed in
   the coordinate-transformation chain and must be re-categorized or documented
   with an explicit justification.
4. Run `validate_right_hand_rule` on the three axis vectors. If the dot product
   of x and y exceeds the orthogonality threshold, or if z does not align with
   x cross y, the triad fails and the figure must be corrected before release.
5. If the figure specifies an Euler-sequence, run `validate_euler_sequence`.
   Confirm the sequence string is exactly three characters, all characters are
   valid axis designators, and no two consecutive designators are identical.
   If angle values are provided without a sequence, flag the inconsistency.
6. Run `validate_figure_spec` as the aggregated gate check. This combines all of
   the above checks into a single pass/fail result. Only a FigureSpec with no
   findings is compliant with §5.3.3 and may be released.
7. Collect all findings across all figures. Any figure with findings is a
   non-conformance against ECSS-E-ST-10-09C §5.3.3 and must be corrected and
   re-checked before the data package is delivered.

## Pitfalls

- Checking right-handedness visually without numerical verification. A 45-degree
  rotation or a non-unit axis vector can make a left-handed frame appear correct
  to the eye. Always compute the dot product of x cross y against z.
- Treating a scaled axis vector as valid without normalization. The right-hand
  check requires normalized vectors; scaling a single axis can falsely reduce the
  cross-product alignment and produce a spurious failure. The logic normalizes
  before checking, so raw component magnitudes do not matter.
- Omitting the origin description because it is "obvious from context." The
  standard requires it explicitly on the figure; a missing annotation is a
  non-conformance regardless of how well the origin is described in accompanying
  text.
- Providing Euler angles without specifying the sequence. Angles alone are
  ambiguous; the rotation-sequence designator is mandatory when angle values
  appear on the figure.
- Using a frame type that is descriptive but not one of the five recognized ECSS
  categories (for example, "launch" or "antenna"). Any such label must be mapped
  to the closest ECSS category or justified in the interface control document.

## Behavior contract (gate 3)

The annotation-completeness, frame-type, right-hand-rule, and Euler-sequence
logic is exercised by the gate 3 contract test:
scripts/test_e1009_figures.py against scripts/e1009_figures_logic.py
(stdlib unittest, offline). Run:

```
python3 scripts/test_e1009_figures.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

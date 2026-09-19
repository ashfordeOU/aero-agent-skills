---
name: q7045-test-piece-requirements
description: "Evaluate a proposed metallic test-piece drawing against the geometry, machining and preparation rules of ECSS-Q-ST-70-45C: compute the original cross-section from the declared shape, derive the proportional gauge length from it, check the parallel length, transition radius, gripped-end allowance and dimensional tolerances that follow, then grade the machined surface finish, the residual-stress-removing final cut and the orientation marking the piece must carry before it leaves the shop. Use when reviewing a test-piece drawing, accepting machined blanks from a supplier or diagnosing a break that fell outside the gauge length. Trigger: ecss, q-st-70-45c, metallic-test-piece-geometry, proportional-gauge-length, test-piece-parallel-length, test-piece-transition-radius, test-piece-machining-finish."
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
  tags: [ecss, q-st-70-45c-metallic-mechanical-testing, q-st-70-45c, q7045-test-piece-requirements, metallic-test-piece-geometry, proportional-gauge-length, test-piece-parallel-length, test-piece-transition-radius, test-piece-machining-finish]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Test Piece Requirements (space-systems/ecss/q7045-test-piece-requirements)

Use when the task is the test-piece clause of ECSS-Q-ST-70-45C: what shape a
mechanical test piece has to be, how its gauge length follows from its
cross-section, and what the machining and preparation have to deliver before
the piece is fit to be pulled.

## Domain quick reference

- The gauge length is not a free dimension. For a proportional test piece it
  follows from the original cross-sectional area as a fixed coefficient times
  the square root of that area, which is what makes an elongation figure
  comparable between a round bar and a flat strip of different size.
- A non-proportional piece is legitimate but it is a different animal. Its
  elongation cannot be compared with a proportional result, so the gauge
  length has to be reported alongside the number rather than assumed.
- The parallel length is longer than the gauge length, and by a margin that
  depends on the section. Too short and the transition fillet is inside the
  measured region; the stress concentration there decides where the piece
  breaks, and the break lands outside the gauge marks.
- The transition radius is a geometry requirement, not a finishing detail. A
  tight fillet raises the local stress enough to move the failure out of the
  parallel length, which invalidates the piece however well the rest of it was
  made.
- Surface finish in the parallel length is part of the specimen. Machining
  marks running across the axis are crack starters, so the roughness limit is
  tighter there than on the gripped ends, and a piece is finished with light
  cuts that leave no heat-affected or cold-worked skin.
- Tolerance on the section dimension is what turns a load into a stress. A
  diameter measured to the nearest tenth of a millimetre on a small round
  piece is a percent-level error in every strength figure the test returns.
- Orientation and identity are machined in, not written on afterwards. A piece
  that loses its orientation mark during preparation has lost the property it
  was cut to measure, because a longitudinal and a short-transverse result
  from the same plate are different numbers.

## Workflow

1. Read the declared shape and dimensions and compute the original
   cross-sectional area: circular from the diameter, rectangular from
   thickness and width. Refuse a non-positive or non-finite dimension.
2. Derive the proportional gauge length from that area with the declared
   coefficient, and compare it with the gauge length on the drawing.
3. Check the parallel length against the gauge length plus the section-derived
   allowance, and report a shortfall as a geometry defect rather than a
   tolerance question.
4. Check the transition radius against the section minimum, and the
   gripped-end length against the grip the machine actually has.
5. Grade the dimensional tolerance on the section dimension as a percentage of
   the dimension itself, not as an absolute figure, so small sections are held
   to the accuracy the stress calculation needs.
6. Grade the parallel-length surface roughness against its own limit, separate
   from the gripped-end limit, and check that a final light cut is declared for
   a material sensitive to a cold-worked skin.
7. Confirm the piece carries an identity and an orientation mark placed outside
   the parallel length, and close with the findings that would invalidate a
   result obtained from this piece.

## Pitfalls

- Copying a gauge length from another drawing. It only transfers when the
  cross-section transfers; a different diameter is a different proportional
  gauge length, and reusing the old one silently changes the elongation basis.
- Treating a short parallel length as a tolerance issue. It puts the fillet
  inside the measured region and the break outside the gauge marks, which is a
  geometry defect that no measurement care recovers.
- Grading the section dimension against an absolute tolerance. The same
  hundredth of a millimetre is negligible on a wide flat and a percent of the
  stress on a small round piece.
- Applying the parallel-length roughness limit to the whole piece, or the
  gripped-end limit to the parallel length. They are different limits for
  different reasons, and merging them either over-machines the grips or lets a
  crack starter into the measured length.
- Marking orientation on a surface that the parallel length or the grips will
  consume. The mark has to survive preparation and testing to be worth
  anything.
- Widening a radius or roughness limit to accept a batch of blanks already
  machined. The limits stay as specified; the pieces are re-made or the
  results carry the deviation explicitly.

## Behavior contract (gate 3)

The cross-section computation, proportional gauge-length derivation, parallel
length, transition radius and gripped-end checks, the relative dimensional
tolerance rule, the split roughness limits and the identity and orientation
marking rule are exercised by the gate 3 contract test:
scripts/test_q7045_test_piece_requirements.py against
scripts/q7045_test_piece_requirements_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_test_piece_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

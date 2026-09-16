---
name: e2008-marking-visual-inspection
description: "Use when a coupon's markings have been examined and presence, adhesion and location need dispositioning together. Assess the identification markings of ECSS-E-ST-20-08C clause 5.5.3.2.18: settle presence first by reconciling the markings the assembly drawing calls out against those observed, turn the lifted footprint and the lifted edge into two adhesion fractions, take the larger axis error as the governing deviation inside the rectangular placement box, check the face against the drawing and character height against the legibility minimum, and return accept, rework or reject per marking with a coupon verdict and the missing or unlisted ones named apart. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-18, coupon-identification-marking-check, marking-adhesion-lifted-area-fraction, marking-location-tolerance-box, missing-identification-marking."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-marking-visual-inspection, coupon-identification-marking-check, marking-adhesion-lifted-area-fraction, marking-location-tolerance-box, missing-identification-marking, marking-legibility-character-height]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Marking Visual Inspection (space-systems/ecss/e2008-marking-visual-inspection)

Use when the task is the marking examination of ECSS-E-ST-20-08C
clause 5.5.3.2.18 -- confirming that the identification markings a
coupon should carry are present, well adhered and placed where the
assembly drawing says, and turning that into a disposition a rework or
a scrap decision can rest on.

## Domain quick reference

- The clause asks three things and a marking has to answer all of
  them. Present but peeling will not survive the programme; adhered
  but misplaced identifies the wrong feature; both, and unreadable,
  identifies nothing at all. The marking disposition is the worst leg.
- Presence is settled before any measurement is taken. Reconciling the
  drawing list against the observed list splits the population into
  markings that can be graded and markings that cannot, and a marking
  that is not on the part has no lifted area to measure.
- Adhesion is two figures, not one. The lifted share of the footprint
  says how much has let go; the lifted share of the perimeter says
  whether an edge has started to peel. A label can hold ninety-nine
  per cent of its area with one whole edge free, and averaging the two
  hides exactly the finding that predicts the rest coming off.
- Placement is a rectangular question. A marking is applied inside a
  tolerance box, so the deviation that governs is the larger of the
  two axis errors. A root-sum-square reports a diagonal distance the
  drawing never toleranced and condemns a marking inside its box.
- The face is a separate question from the in-plane deviation. A
  marking on the face the drawing did not nominate is not a large
  offset that a wider tolerance could absorb; it is a different
  position, and no tolerance reaches it.
- Legibility is a minimum character height and it fails downward,
  which is the opposite direction to every allowance in the screen. It
  is never scaled by the surface factor, because a factor below one
  would demand less legibility exactly where it matters more.
- Where a marking sits changes its allowances. The cell stack face
  carries tightened deviation and area limits, because a smear or a
  displaced label there sits on the active surface.
- A marking found with no matching entry on the drawing holds the
  coupon open just as a missing one does. An unexplained identifier is
  a configuration question, not a cosmetic one.

## Workflow

1. Open the coupon record against a coupon identifier and take the
   list of markings the assembly drawing calls out.
2. Reconcile that list against the markings observed. Report the
   missing and the unlisted apart; they are not graded.
3. For each observed marking, check the face it was found on against
   the face the drawing nominates before measuring anything in plane.
4. Take the lifted footprint and the lifted edge as two fractions and
   disposition adhesion on the worse of them.
5. Take the two axis errors against the drawing spot, keep the larger
   as the governing deviation, and disposition it against the
   surface-scaled accept and rework boxes.
6. Take the character height against the legibility minimum and the
   rework floor. Do not scale a minimum by the surface factor.
7. Categorize any further indication by kind and surface, routing the
   not-tolerated kinds to a presence decision and the graded ones to
   the surface-scaled area limits.
8. Close with the coupon verdict, the missing, unlisted and
   not-tolerated markings listed apart, and the re-inspection duty a
   rework creates.

## Pitfalls

- Grading a marking that is not there. A missing identifier has no
  adhesion and no position, so it belongs in the reconciliation, not
  in the measured population, and it holds the coupon open.
- Rolling the lifted area and the lifted edge into one number. The two
  describe different failures and the average of a sound footprint and
  a free edge reads as a healthy marking.
- Taking the placement deviation as a root-sum-square. The tolerance
  is a box, not a circle, and the diagonal of a box is longer than
  either side; a marking well inside its box can fail a radial test.
- Treating a wrong face as a large offset. Widening the in-plane
  tolerance never reaches it, and a marking on the wrong face is a
  different position entirely.
- Scaling the character height minimum by the surface factor. A factor
  below one tightens an allowance but loosens a minimum, so applying
  it accepts smaller characters exactly where the surface was meant to
  demand better.
- Ignoring a marking the drawing never called out. An unexplained
  identifier on a coupon is a configuration finding and it holds the
  record open the same way a missing one does.
- Comparing a measurement with a scaled limit by bare arithmetic. The
  limit is a product of a criteria value and a surface factor, so a
  measurement exactly on the limit can evaluate a few units in the
  last place above it; the comparison absorbs that representation
  error while the limit stays untouched.

## Behavior contract (gate 3)

The drawing-to-part reconciliation, the two adhesion fractions, the
rectangular governing deviation, the face check, the legibility
minimum, the surface-scaled allowances and the coupon rollup are
exercised by the gate 3 contract test:
scripts/test_e2008_marking_visual_inspection.py against
scripts/e2008_marking_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_marking_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

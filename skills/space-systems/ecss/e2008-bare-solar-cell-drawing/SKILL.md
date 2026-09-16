---
name: e2008-bare-solar-cell-drawing
description: "Use when a bare cell drawing is offered for release and its numbers have to be limits. Verify the source control drawing describing a bare solar cell carries the content Annex C of ECSS-E-ST-20-08C calls for: every stated characteristic needs a unit, a limit rather than a bare nominal, and for an electrical one the spectrum, intensity and temperature it was measured at; a band whose ends coincide is a point, not a limit; and the annex names a floor, so a weak characteristic beyond the required set is an open item and not a stoppage. Trigger: ecss, e-st-20-08c, bare-solar-cell-drawing-content-audit, bare-solar-cell-characteristic-limit-form, bare-solar-cell-measurement-condition-attachment, bare-solar-cell-degenerate-band-detection, bare-solar-cell-controlled-characteristic-share."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-bare-solar-cell-drawing, bare-solar-cell-drawing-content-audit, bare-solar-cell-characteristic-limit-form, bare-solar-cell-measurement-condition-attachment, bare-solar-cell-degenerate-band-detection, bare-solar-cell-controlled-characteristic-share, bare-solar-cell-drawing-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Solar Cell Source Control Drawing (space-systems/ecss/e2008-bare-solar-cell-drawing)

Use when the task is the content rule of ECSS-E-ST-20-08C Annex C -- what the
source control drawing describing a bare solar cell has to state, and which of
the numbers it states are limits anybody could reject a cell against.

## Domain quick reference

- The drawing is a list of characteristics, and a characteristic earns its
  place only when it carries a unit, a limit, and -- if it is electrical --
  the conditions the number was measured at. Missing any one of the three,
  the line looks like a specification and binds nobody.
- A unit is not decoration. A thickness of 150 reads as micrometres to one
  engineer and as thousandths of an inch to another, and both readings are
  reasonable until the drawing says which.
- A limit is a minimum, a maximum, a range, or a nominal with a band. A
  nominal on its own is what the supplier intends today; nothing about it
  lets anyone reject a cell tomorrow.
- A band whose two ends coincide is the same failure written differently. A
  range from 2.5 to 2.5, or a nominal with a zero tolerance, names a point no
  real cell lands on, so it rejects the whole population rather than the bad
  part of it.
- Electrical numbers are conditional numbers. An open-circuit voltage without
  the spectrum, the intensity and the temperature behind it came from an
  unnamed measurement, and two suppliers can both satisfy it while shipping
  different cells.
- The annex names a floor, not a ceiling. Characteristics beyond the required
  set are welcome and are graded the same way, but a weak one among them is an
  open item on a drawing whose required set is sound -- not a reason to stop
  the release.
- A required characteristic stated as the wrong kind -- a current written up
  as a physical property with no measurement conditions -- is how a
  conditional number escapes the condition check, so the kind is graded
  against the annex rather than taken from the drawing.
- Characteristics do not weigh the same. The three dimensions and the three
  electrical outputs carry the cell; the coating and the mass matter less.
  Completeness weighted by what each pins down is the honest number.

## Workflow

1. Take the drawing as its number and the characteristics it states.
2. Resolve each stated limit into bounds: a minimum or a maximum leaves one
   end open, a range and a nominal-with-tolerance close both, a bare nominal
   closes neither.
3. Mark as degenerate any band whose ends coincide, comparing them with a
   tolerance rather than with equality.
4. For every electrical characteristic, check the spectrum, the intensity and
   the temperature are all named.
5. Grade each characteristic as controlled, open or uncontrolled, and split
   the uncontrolled ones into those the annex requires and those beyond it.
6. Name every required characteristic the drawing never states, and every one
   it states under the wrong kind.
7. Weight the controlled required characteristics by what each pins down and
   compare the share with the threshold the drawing is released against.
8. Disposition the drawing: a missing, uncontrolled or mis-kinded required
   characteristic, or a share under the threshold, stops the release; a
   degenerate band or a weak extra characteristic releases it against open
   items.

## Pitfalls

- Reading a precise-looking number as a controlled one. Digits after the
  decimal point are not a limit.
- Accepting a nominal because a tolerance is "standard shop practice". The
  practice is not on the drawing and the drawing is what the supplier signs.
- Writing a zero tolerance to mean exact. It rejects every cell that can
  physically be made.
- Comparing the two ends of a band with equality. They are computed numbers,
  a band meant to be degenerate can miss by a few units in the last place, and
  the check quietly passes the thing it exists to catch.
- Quoting an electrical output with no spectrum, intensity or temperature.
  The number is from an unnamed experiment and cannot be reproduced or
  disputed.
- Naming two of the three measurement conditions and calling the third
  obvious. Obvious to the reader is not stated on the drawing.
- Letting an electrical characteristic ride as a physical one. The condition
  check never runs, and the number keeps looking complete.
- Treating a weak characteristic outside the required set as a stoppage. The
  annex sets a floor, and grading the extras harder than the required set
  inverts the standard.
- Counting characteristics instead of weighting them. Eight of nine stated
  says nothing when the missing one is a cell dimension.
- Comparing a weighted control share with its threshold by bare arithmetic.
  Both are quotients of weights and a drawing exactly on the threshold can
  evaluate a few units in the last place under it; the comparison absorbs that
  while the threshold stays as written.

## Behavior contract (gate 3)

The limit-form resolution into bounds, degenerate band detection, measurement
condition attachment for electrical characteristics, characteristic grading
into controlled, open and uncontrolled, required-versus-extra separation,
kind checking, weighted control share and the release disposition are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_solar_cell_drawing.py against
scripts/e2008_bare_solar_cell_drawing_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_bare_solar_cell_drawing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

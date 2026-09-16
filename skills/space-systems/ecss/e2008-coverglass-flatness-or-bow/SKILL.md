---
name: e2008-coverglass-flatness-or-bow
description: "Use when a coverglass bow figure is quoted from a grid nobody checked for reach or resolution. Derive the maximum deflection of a coverglass resting unclamped on an optically flat reference per ECSS-E-ST-20-08C clause 8.7.8 and disposition it: turn an interference fringe count into a gap height, fit and remove the setup tilt from the probe grid, separate a bow from alternating waviness by the radial profile of what is left, normalise the departure over the measured span, and refuse a run whose grid never reached the rim or whose datum and probe cannot resolve what they report. Trigger: ecss, e-st-20-08c-clause-8-7-8, coverglass-flatness-and-bow-measurement, coverglass-optical-flat-datum, coverglass-interferometric-fringe-deflection, coverglass-bow-span-ratio, coverglass-departure-grid-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-flatness-or-bow, coverglass-flatness-and-bow-measurement, coverglass-optical-flat-datum, coverglass-interferometric-fringe-deflection, coverglass-bow-span-ratio, coverglass-departure-grid-coverage, coverglass-bonding-conformance-risk]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Flatness or Bow (space-systems/ecss/e2008-coverglass-flatness-or-bow)

Use when the task is clause 8.7.8 of ECSS-E-ST-20-08C -- the maximum
deflection of a coverglass laid on an optically flat reference surface.
The measurement is deliberately plain, and everything that makes the
number defensible sits around it rather than in it: the article is an
unclamped thin plate, the datum has to be flat by a margin against what
it is measuring, the instrument has to resolve the departure by a margin
as well, and the grid has to reach the rim where the departure is
largest. A coverglass that is bowed does not sit down on the cell, so
this figure is what says whether the adhesive bond line will be uniform
or whether the glass will be pulled flat and left in tension.

## Domain quick reference

- The article rests. It is not held. A thin plate clamped to a datum
  reports the fixture's deflection, and a clamped run can produce a
  smaller and much more repeatable number than the free article ever
  had.
- In reflected light against an optical flat, each whole interference
  fringe is half a wavelength of gap. A fringe count is a height only
  once the illumination wavelength is stated beside it.
- The article sits tilted on the datum, and tilt is a setup artefact.
  Removing a least-squares plane takes it out and leaves the shape of
  the glass, which is the part that matters for the bond line.
- Sign alone does not separate bow from waviness. Once the plane is
  removed a dished or domed article necessarily sits on both sides of
  zero, so a mixed-sign residual map is not evidence of waviness. What
  separates them is the radial profile: a bow rises or falls once as
  the radius grows, waviness turns back on itself.
- The two shapes behave differently under bonding even at the same
  peak-to-valley, so the reduction reports the shape beside the maximum
  rather than collapsing both into one number.
- A departure only a few times the probe resolution is mostly
  instrument, and a datum whose own departure approaches the article's
  is not a datum. Both are ratio checks against the article, not
  absolute instrument specifications.
- A bow is largest at the rim. A grid whose bounding box covers the
  middle of the coverglass returns a small, true, and thoroughly
  misleading number.

## Workflow

1. Establish that the coverglass rested free on the reference. A
   clamped run is a finding, not an input to be corrected.
2. If the record is a fringe count, convert it to a gap height through
   the stated illumination wavelength before anything is compared.
3. Check the departure map has enough points and that its bounding box
   reaches across the article on both axes, since a grid that never
   went to the rim cannot report a rim-dominated quantity.
4. Take the maximum gap and the peak-to-valley from the raw heights,
   because the drawing limit is written against the gap under the
   resting glass rather than against a residual.
5. Fit and remove the least-squares plane, then read the radial profile
   of the residual to categorize the departure as a bow, as waviness,
   or as within noise.
6. Hold the departure against the probe resolution and against the
   reference flat's own departure as ratios, normalise it over the
   span, compare it with the drawing limit, and close with a verdict
   that stays open while any finding stands.

## Pitfalls

- Holding the glass down to get a steady reading. The reading does get
  steadier, and it stops being the article's deflection.
- Quoting a fringe count as a deflection. Without the wavelength the
  count is a number of fringes, and two benches on different lamps
  report different micrometres from the same article.
- Reporting the residual peak-to-valley as the maximum deflection. The
  drawing limit sits on the gap under the resting glass; removing the
  plane first understates it by the tilt.
- Calling a mixed-sign residual map waviness. Plane removal guarantees
  both signs on any bowed article, so sign counting categorizes almost
  every real coverglass as wavy.
- Sampling the middle of the coverglass. The grid is cheaper, the
  arithmetic is identical, and the rim where the bow actually lives was
  never measured.
- Taking a departure a few times the probe resolution at face value.
  The ratio, not the absolute number, says whether an instrument
  measured an article or measured itself.
- Comparing a derived ratio or a normalised deflection against a limit
  by bare arithmetic. Heights arrive in micrometres and spans in
  millimetres, so a value meant to land on a limit can miss it by a few
  units in the last place; the comparison absorbs that while the limit
  itself is never relaxed.

## Behavior contract (gate 3)

The fringe-to-height conversion, grid validation, bounding-box reach,
minimum grid population, maximum deflection and peak-to-valley,
least-squares plane fit with its collinear refusal, radial bow and
waviness separation, span-normalised departure, probe-resolution and
reference-flat ratio checks, unclamped-rest requirement and drawing
limit comparison are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_flatness_or_bow.py against
scripts/e2008_coverglass_flatness_or_bow_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_coverglass_flatness_or_bow.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

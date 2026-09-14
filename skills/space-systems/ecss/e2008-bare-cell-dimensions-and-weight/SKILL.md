---
name: e2008-bare-cell-dimensions-and-weight
description: "Verify a bare solar cell against the outline, thickness, mass, contact geometry and interconnector position requirements of ECSS-E-ST-20-08C clause 7.5.2: place each measurement inside its plus and minus band and name the state, combine the two axis offsets of every attachment point into one radial true-position deviation, raise an out-of-band feature into a review band before refusing it because a bare cell cannot be machined back, and cross-check the measured areal density against the density the drawing implies before any band is believed. Use when a bare cell measurement sheet has to be judged against the purchase drawing. Trigger: ecss, e-st-20-08c, clause-7-5-2, bare-cell-outline-tolerance-check, bare-cell-thickness-band, bare-cell-mass-budget, interconnector-pad-true-position, bare-cell-areal-density-crosscheck."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-dimensions-and-weight, bare-cell-outline-tolerance-check, bare-cell-thickness-band, bare-cell-mass-budget, interconnector-pad-true-position, bare-cell-areal-density-crosscheck]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bare Cell Dimensions and Weight (space-systems/ecss/e2008-bare-cell-dimensions-and-weight)

Use when the task is the bare cell conformity check of ECSS-E-ST-20-08C
clause 7.5.2 -- outline, thickness, mass, contact geometry and
interconnector attachment positions measured against the purchase
drawing -- turned into a per-feature state, a cross-check the
individual bands cannot do for themselves, and a cell verdict.

## Domain quick reference

- A bare cell is bought to a drawing, so the question is conformity,
  not defect grading. Each family of measurement fails in its own way:
  an oversize outline breaks the string pitch, an undersize one leaves
  a gap the coverglass overhangs, thickness drives handling breakage
  and the bond line, and mass is an array budget where a few per cent
  per cell becomes kilograms across a wing.
- A measurement has a state before it has a disposition. Within
  tolerance, above the upper limit and below the lower limit are three
  different engineering situations, and collapsing them into pass and
  fail loses the direction the deviation went in.
- A position is not two numbers. Two axis offsets that each sit inside
  a tolerance can still put the attachment point outside it once they
  combine, so the check is the radial true-position deviation against
  one tolerance, never an x test and a y test run separately.
- There is no rework on a bare cell. Nothing can be machined back into
  tolerance, so the middle disposition is a review band: a deviation
  outside the drawing band but inside a declared multiple of it is
  raised as a non-conformance and submitted for a use-as-is decision,
  and past that multiple the cell is refused.
- Mass and outline are not independent. Their ratio is the areal
  density, and a measured density that departs from the density the
  nominal drawing implies says one of the two measurements is wrong --
  a cracked cell weighed with a fragment missing, or an outline read
  off the wrong datum. That cross-check runs before the individual
  bands are believed.
- An unmeasured feature is unknown, not conforming. A contact the
  drawing declares and the sheet omits, or an attachment point with no
  measurement, is refused rather than defaulted to acceptable.
- A feature on the sheet that the drawing does not declare is a
  drawing mismatch, not a deviation. There is nothing to judge it
  against, and inventing a band for it hides the mismatch.

## Workflow

1. Validate the specification first: every required band present, each
   with a nominal and a tolerance that leaves a real window, and a
   true-position tolerance wherever attachment points are declared.
2. Open the measurement sheet against a cell identifier. A sheet with
   no traceable identifier cannot be dispositioned.
3. Place the outline, thickness and mass measurements inside their
   bands, recording the state and the margin to the nearest limit, not
   just a pass or a fail.
4. Check every declared contact feature against its own band, and
   refuse the sheet if a declared contact is unmeasured or an
   undeclared one appears.
5. Combine each attachment point's axis offsets into one radial
   deviation and test it against the true-position tolerance and its
   review multiple.
6. Take the measured areal density from the mass and the outline,
   compare it with the density the nominal drawing implies, and raise
   the mutual-inconsistency finding before trusting either number.
7. Close with the cell verdict, the out-of-band feature names, the
   worst position deviation and the non-conformance a review verdict
   raises.

## Pitfalls

- Testing an attachment point on x and on y. Two offsets inside
  tolerance combine into a radial deviation that is not, and the
  separate tests pass a pad the drawing would refuse.
- Treating an out-of-band measurement as a scrap call. A bare cell
  cannot be reworked, but it can be submitted for use as is, and the
  review band is what separates that from a refusal.
- Believing a band before the cross-check. A measured mass and a
  measured outline that imply the wrong areal density are telling you
  the sheet is wrong, and every band read off that sheet inherits the
  error.
- Reading an unmeasured feature as conforming. Silence on a declared
  contact is missing evidence, not a pass.
- Folding an undeclared feature into the check. It has no band, so any
  verdict on it is invented and the real finding -- the mismatch
  between the sheet and the drawing -- goes unreported.
- Reporting only a verdict. A cell above its upper limit and a cell
  below its lower limit read the same on a summary line and lead to
  opposite recovery decisions.
- Comparing a measurement with a limit by bare arithmetic. A limit is
  a nominal plus a tolerance and a review limit multiplies that
  tolerance again, so a measurement meant to sit exactly on a limit
  can evaluate a few units in the last place to either side; the
  comparison absorbs that representation error while the limit stays
  untouched.

## Behavior contract (gate 3)

The band placement and state naming, the review band that stands in
for rework, the radial true-position check, the areal density
cross-check and the cell rollup are exercised by the gate 3 contract
test: scripts/test_e2008_bare_cell_dimensions_and_weight.py against
scripts/e2008_bare_cell_dimensions_and_weight_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_bare_cell_dimensions_and_weight.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

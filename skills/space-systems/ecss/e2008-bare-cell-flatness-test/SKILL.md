---
name: e2008-bare-cell-flatness-test
description: "Use when bare-cell surface height readings have to become a flatness verdict. Evaluate how flat an unmounted bare solar cell stays across its whole face under ECSS-E-ST-20-08C clause 7.5.19: refuse a height grid that only reached part of the cell, fit a least-squares reference plane so fixture tilt leaves the number before any deviation is read, take peak-to-valley and RMS residuals against that datum, name the bow convex, concave or irregular, and report the margin left against the tighter of the absolute and diagonal-share allowances. Trigger: ecss, bare-cell-flatness-limit, bare-cell-surface-height-grid, bare-cell-best-fit-reference-plane, bare-cell-peak-to-valley-deviation, bare-cell-bow-direction, bare-cell-flatness-grid-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-flatness-test, e-st-20-08c-clause-7-5-19, bare-cell-flatness-limit, bare-cell-surface-height-grid, bare-cell-best-fit-reference-plane, bare-cell-peak-to-valley-deviation, bare-cell-bow-direction, bare-cell-flatness-grid-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Bare Cell Flatness Test (space-systems/ecss/e2008-bare-cell-flatness-test)

Use when the task is clause 7.5.19 of ECSS-E-ST-20-08C: how flat the
surface of an unmounted bare solar cell remains over its full area. This
leaf reads one cell outline and the height grid measured on it, and
returns the deviation from a fitted datum, the shape that deviation
takes, and the verdict against the governing allowance.

## Domain quick reference

- Coverage is decided before flatness, because a grid that sampled the
  middle of the cell has measured the middle of the cell. Anything it
  reports is a lower bound on the real departure, and a lower bound
  presented as a result is the quietest way this measurement goes wrong.
  Span in both directions and a reading in every quadrant are what makes
  the number a full-area number.
- The datum is fitted, not assumed. A perfectly flat cell resting at a
  slight angle in its fixture reads as a sloped surface, and judged
  against the bench it fails on tilt that belongs to the setup. The
  least-squares plane through the readings themselves removes exactly
  that and nothing else.
- Tilt is still worth reporting once it is removed. A large fitted
  gradient says the cell was not seated the way the method intended,
  which is a comment on the measurement rather than on the cell, and it
  is unrecoverable from the deviation alone.
- Peak-to-valley and RMS answer different questions. Peak-to-valley is
  the worst gap the cell has to close against its substrate; RMS says
  whether that gap is one local feature or the whole face.
- Shape is not a refinement of size. A domed cell touches its substrate
  in the middle and lifts at the corners; a dished one does the opposite
  and traps adhesive; a buckled one does neither predictably. Two cells
  with the same peak-to-valley behave differently on bonding, so the
  centre of the face is compared against its perimeter.
- The allowance has two statements and the tighter one governs. An
  absolute figure written for a small cell would quietly loosen on a
  larger one if the diagonal share were not applied beside it, and the
  reverse on a small cell, so the limit is derived per outline.
- The sense is a ceiling -- less departure is better -- so a cell landing
  exactly on the allowance is admissible, and the comparison tolerance
  exists to absorb representation error rather than to widen the limit.
- A cell is thin and free here. It is unmounted precisely so the wafer's
  own shape is what gets measured, so the support arrangement and the
  method belong with the result; a flatness figure with no method
  recorded cannot be compared with the next lot's.

## Workflow

1. Validate the criteria set first: the absolute allowance, the diagonal
   share, the review factor, the marginal band, and what the grid must
   do to count as full-area. A share above one, or a review factor below
   one, is refused rather than used.
2. Resolve the cell outline and derive the diagonal and face area from
   it. The governing allowance comes from that diagonal, not from a
   figure typed in beside it.
3. Read the height grid back: every station on the cell, no station
   measured twice, every height finite. An empty grid is refused rather
   than reported as a flat cell.
4. Take coverage: station count, span in both directions as a share of
   the outline, and a reading in each of the four quadrants. A gap here
   closes the assessment on flatness not established, before any
   arithmetic that would look like an answer.
5. Fit the least-squares reference plane, refusing a collinear station
   set that determines no plane, and report the gradient it absorbed as
   the fixture tilt across the diagonal.
6. Profile the residuals: peak-to-valley, the one-sided extremes and
   RMS, then name the shape from the centre stations against the outer
   ones, leaving it unnamed when the difference is inside the signature
   band.
7. Compare the peak-to-valley against the governing allowance with a tie
   admissible, escalate through the review band, and close on one
   verdict: flatness not established, within limit, referred for review,
   or exceeds the limit. Report the margin and raise an advisory for an
   accepted cell inside the marginal band.

## Pitfalls

- Measuring a convenient patch and calling it flatness. The clause asks
  about the full area, and an unsampled quadrant cannot be reported flat.
- Judging the readings against the bench. A tilted seat makes a flat cell
  fail and no amount of care in the probe recovers it; the datum has to
  come from the readings.
- Throwing the fitted tilt away after removing it. It is the evidence
  that the cell was seated as the method intended, and it is gone from
  the deviation by construction.
- Reporting peak-to-valley alone. The same figure describes a dome, a
  dish and a local bump, and those three do different things when the
  cell is bonded down.
- Carrying one absolute allowance across cell sizes. A limit written for
  a small cell is loose on a large one, which is why the diagonal share
  sits beside it and the tighter of the two governs.
- Comparing a reading against a derived allowance by bare arithmetic. The
  limit is a product of a share and a measured dimension, so a reading
  exactly on it can evaluate a few units in the last place above it; the
  comparison absorbs that while the allowance stays untouched.
- Recording a flatness figure with no method beside it. The support
  arrangement changes what a free wafer does, so the number is not
  comparable with the next lot's without it.

## Behavior contract (gate 3)

The criteria validation, the outline and diagonal derivation, the height
grid read-back, the full-area coverage test, the least-squares reference
plane with its degenerate-grid refusal, the fixture tilt report, the
peak-to-valley, one-sided and RMS residual profile, the convex, concave
and irregular shape call, the governing allowance selection and the
flatness verdict with its margin and marginal advisory are exercised by
the gate 3 contract test:
scripts/test_e2008_bare_cell_flatness_test.py against
scripts/e2008_bare_cell_flatness_test_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_flatness_test.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

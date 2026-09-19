---
name: q7050-vacuum-and-rinse-methods
description: "Compute the surface loading a vacuum-probe or solvent-rinse cleanliness sample actually reports under ECSS-Q-ST-70-50C. Use when hardware surfaces have been sampled for monitoring, each sample carries a witness blank and a sampled area, and the record is either an evaporated rinsate aliquot or a probe stroke pattern. Scales the aliquot back to the whole collected volume, subtracts the blank, divides out the collection recovery of the method, turns a stroke pattern into the area it truly swept rather than the area it covered, holds a net the balance cannot resolve to a bounded statement, and grades the method detection limit against the reporting limit. Trigger: ecss, q-st-70-50, surface-particulate-sampling, solvent-rinse-nvr, vacuum-probe-stroke-coverage, witness-blank-subtraction, sampling-recovery-fraction, nvr-area-density."
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
  tags: [ecss, q-st-70-cleanliness-monitoring-scope, q7050-vacuum-and-rinse-methods, surface-particulate-sampling, solvent-rinse-nvr, vacuum-probe-stroke-coverage, witness-blank-subtraction, sampling-recovery-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness Monitoring — Vacuum and Rinse Sampling (space-systems/ecss/q7050-vacuum-and-rinse-methods)

Use when the task is the surface-sampling step of ECSS-Q-ST-70-50C
cleanliness monitoring — taking a vacuum-probe or solvent-rinse record
off a piece of hardware and turning it into a loading per unit area that
a contamination budget can be built on.

## Domain quick reference

- A sampling result is a mass or a count divided by an area, and the
  area is the half of that ratio most often wrong. A rinse samples the
  wetted area, which is not the projected area of the part; a probe
  samples the area its strokes swept, which is less than the area the
  pattern covered because adjacent strokes are deliberately overlapped
  so no lane is missed.
- A rinse rarely evaporates the whole rinsate. One aliquot is taken to
  a tared dish, so the weighed residue belongs to that aliquot and has
  to be scaled by the collected volume over the aliquot volume before it
  belongs to the surface.
- The witness blank is the solvent, the glassware and the handling, run
  through the same path with no hardware in it. Subtracting it is not
  optional: on a clean surface the blank can be the larger of the two
  numbers, and a sample under its own blank past the weighing noise says
  the rinsate was contaminated, not that the surface was.
- Neither method lifts everything. The recovery fraction of the method
  on that surface finish divides into the collected mass to give the
  surface loading; leaving it out reports the sampler's efficiency as if
  it were the hardware's cleanliness.
- The detection limit is a property of the sample, not of the balance
  alone: the same readability over a smaller area, or behind a larger
  dilution, cannot reach the same reporting limit. A sample whose floor
  sits above the programme's reporting limit answers nothing, however
  clean the result looks.

## Workflow

1. Decide the method the surface can carry — accessibility, solvent
   compatibility, whether rinsate can be collected, whether the surface
   tolerates a probe — and refuse a surface that supports neither rather
   than forcing a sample it cannot give.
2. Establish the area: the wetted area for a rinse; for a probe, the
   swept area computed from stroke count, probe width, stroke length and
   the overlap fraction between strokes.
3. Subtract the witness blank from the weighed residue and categorize
   the net as quantified, sub-floor, or blank-dominated against the
   balance floor.
4. Scale a rinse residue from the aliquot to the whole collected volume.
5. Divide by the collection recovery of the method so the figure is
   surface loading, not collected loading.
6. Express the result per unit area and compute the detection limit the
   same area, recovery and dilution imply.
7. Report each sample with its status, its loading and its floor, and
   raise a finding for a blank-dominated sample, a loading above the
   reporting limit, or a floor that cannot reach that limit.

## Pitfalls

- Reporting the aliquot residue as the sample mass. A 100 mL aliquot of
  a 500 mL rinsate understates the surface by a factor of five, and the
  result still looks like a plausible number.
- Counting the probe pattern area instead of the swept area. Ten
  strokes at half overlap sweep barely more than half the lanes their
  pattern spans, so the density comes out low by nearly a factor of two.
- Dropping the witness blank because it was small. It is small compared
  with a dirty surface and comparable with a clean one, which is exactly
  the region where the monitoring decision is being made.
- Treating a sub-floor net as a measurement. The balance cannot separate
  it from zero, so it is a bound; carried into a budget as a small
  positive number it gives the budget false precision.
- Accepting a sample whose detection limit sits above the reporting
  limit. A non-detect there is not a clean surface, it is an unanswered
  question, and enlarging the area or reducing the dilution is the fix.

## Behavior contract (gate 3)

The method selection, swept-area geometry, aliquot scaling, blank
subtraction, recovery correction, area-density conversion and
detection-limit grading are exercised by the gate 3 contract test:
scripts/test_q7050_vacuum_and_rinse_methods.py against
scripts/q7050_vacuum_and_rinse_methods_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7050_vacuum_and_rinse_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

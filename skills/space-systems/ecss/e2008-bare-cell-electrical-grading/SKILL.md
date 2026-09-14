---
name: e2008-bare-cell-electrical-grading
description: "Allocate accepted bare solar cells to delivery grades from the test current ECSS-E-ST-20-08C clause 7.3.2.2.4 sorts on: check the band ladder rises, closes and leaves no gap before any cell is placed on it, put each measured current in its band, hold a cell sitting inside the measurement guard band of an edge instead of inventing the side it fell on, separate a cell below the lowest band from one above the highest, and report the grade populations and yields a string build consumes. Use when measured bare-cell currents are about to become delivery grades. Trigger: ecss, e-st-20-08c-clause-7-3-2-2-4, bare-solar-cell-performance-grading, bare-cell-test-current-band-ladder, bare-cell-grading-boundary-guard-band, bare-cell-grade-population-yield."
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
  tags: [ecss, e-st-20-08-bare-solar-cell-scope, e2008-bare-cell-electrical-grading, e-st-20-08c-clause-7-3-2-2-4, bare-solar-cell-performance-grading, bare-cell-test-current-band-ladder, bare-cell-grading-boundary-guard-band, bare-cell-grade-population-yield]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Bare Solar Cells -- Electrical Grading (space-systems/ecss/e2008-bare-cell-electrical-grading)

Use when the task is clause 7.3.2.2.4 of ECSS-E-ST-20-08C -- taking the
cells that already passed acceptance and placing them into performance
grades on the current measured at the acceptance test condition.
Acceptance and grading answer different questions. Acceptance asks
whether a cell may be delivered at all; grading asks which cells behave
closely enough alike to sit in the same string. This leaf reads the
grade ladder, places each accepted cell on it, and names the cells the
measurement could not place.

## Domain quick reference

- The ladder is a deliverable definition, so it is checked before any
  cell touches it. A ladder that overlaps places a cell in two grades, a
  ladder with a gap drops a cell out of the delivery silently, and both
  faults are invisible once the populations have been counted.
- Only the top band may be left open. Every band below it closes,
  because an open band in the middle of a ladder swallows everything
  above its lower edge and the grades above it never receive a cell.
- Current is the sorting quantity, not a pass or fail limit. The cell
  already passed; the placement decides which string it can join, and
  the grade that string is built at is the one the array power budget
  was written against.
- A measurement near a band edge did not resolve which band the cell is
  in. Current measurement on an illuminated cell is good to around a per
  cent, so a cell within a per cent of an edge is pushed to one side by
  the arithmetic and not by the evidence.
- A cell below the lowest band contradicts the step before it. Something
  accepted a cell the delivery ladder does not reach, and that is a
  finding about the acceptance limit rather than about the cell.
- A cell above the highest band is a different situation entirely. The
  ladder simply does not describe it, and the answer is to extend the
  ladder or to confirm the top band was meant to stay open.
- Grade yield is what the next step consumes. Two lots with the same
  acceptance rate can build very different arrays if one of them puts
  most of its cells in the bottom grade, and the yield per grade is the
  number a string layout is planned from.

## Workflow

1. Read the grade ladder: reject a repeated grade name, a band that
   closes at or below where it opens, a band narrower than policy
   allows, an overlap, a gap, and an open band anywhere but the top.
2. Read each cell and refuse one that was not accepted, because grading
   applies to the accepted population only.
3. Size the guard band for each cell from its own measured current and
   the declared measurement uncertainty.
4. Hold a cell whose current sits inside that guard band of any ladder
   edge, naming both grades it could belong to, so the placement is a
   decision somebody takes rather than one the arithmetic took.
5. Place every remaining cell: a cell on a lower edge takes the upper
   band, a cell below the ladder floor and a cell above the ladder
   ceiling are reported as separate outcomes.
6. Group the placed cells into grade populations, compute the yield per
   grade, and return a lot verdict that is open whenever the placed
   share falls short or any cell measured below the lowest grade.

## Pitfalls

- Grading the delivered population instead of the accepted one. A cell
  that failed acceptance carries a measurement, and nothing in a band
  comparison stops it from landing in a grade.
- Pushing an edge cell to a side to keep the yield tidy. The guard band
  is not a rounding rule, it is the statement that the measurement never
  said which side the cell was on.
- Reading a cell below the lowest band as a grading failure. Grading did
  what it could; the acceptance limit and the ladder floor disagree, and
  that is the thing to go and fix.
- Leaving a band open in the middle of the ladder. It reads as
  generosity and behaves as a ceiling, because every higher grade is
  emptied into it.
- Reporting only the count per grade. The share per grade is what a
  string layout consumes, and two lots with equal counts and unequal
  totals are not the same delivery.
- Treating the ladder as fixed data that needs no check. A ladder is
  edited between programmes, and a gap introduced by an edit removes
  cells from the delivery without producing a single finding.

## Behavior contract (gate 3)

The ladder check, the guard band sizing, the boundary hold, the
lower-edge placement rule, the below-floor and above-ceiling outcomes,
the grade populations, the grade yields and the lot verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_electrical_grading.py against
scripts/e2008_bare_cell_electrical_grading_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_electrical_grading.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

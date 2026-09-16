---
name: e2008-bare-cell-chip-and-nick-limits
description: "Use when a bare cell edge and face inspection needs a per-defect disposition. Evaluate chips and surface nicks on a bare solar cell against clause 7.5.1.4.1 of ECSS-E-ST-20-08C: place each chip on the outline to decide whether it takes a corner or sits along an edge, derive the reach it has left from the declared inactive border rather than from a typed-in absolute, bound its run against the edge it sits on, grade each face nick on depth against the wafer thickness and on clearance from the contacts, and add the accepted defects up against the cumulative perimeter, area, count and separation allowances. Trigger: ecss, e-st-20-08c, bare-cell-chip-limits, bare-cell-corner-chip-allowance, bare-cell-edge-chip-reach, bare-cell-surface-nick-depth, bare-cell-cumulative-chip-allowance."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-chip-and-nick-limits, e-st-20-08c, bare-cell-chip-limits, bare-cell-corner-chip-allowance, bare-cell-edge-chip-reach, bare-cell-surface-nick-depth, bare-cell-cumulative-chip-allowance, bare-solar-cell-edge-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bare Cell Chip and Nick Limits (space-systems/ecss/e2008-bare-cell-chip-and-nick-limits)

Use when the task is clause 7.5.1.4.1 of ECSS-E-ST-20-08C: the positions
and sizes allowed for chips at the edges and corners of a bare solar
cell, and for nicks on its face. This leaf reads one cell outline and the
defects observed on it, and returns a disposition per defect plus the
accumulation rollup that decides the cell.

## Domain quick reference

- Position is decided before size, because position changes the limit and
  not only the verdict. A chip that takes a corner has the diagonal of
  the inactive border to work through before it opens the junction; a
  chip mid-edge has only the straight border width. The same lost
  millimetre is therefore benign at a corner and marginal along an edge.
- A chip is a corner chip when its span along the edge reaches either end
  of that edge, not when it merely looks close to one. That is a
  geometric test on the declared span, and it is the test that decides
  which allowance applies.
- The reach allowance is derived, never typed in. It is a share of the
  border the drawing actually gives this cell, so a cell laid out with a
  narrower inactive margin tightens its own chip limits without anyone
  editing a table.
- Reach and run are separate measurements of one chip. Reach is inward,
  toward the junction, and decides whether the cell is still sealed; run
  is along the edge, and decides how much of the edge is now a stress
  raiser. A chip can pass one and fail the other.
- The run allowance scales with the edge it sits on. A two millimetre
  chip is a small mark on a long edge and a substantial loss on a short
  one, so the limit is a share of that edge rather than one number for
  the cell.
- A face nick fails differently. It is graded on depth as a share of the
  wafer thickness, because a nick an appreciable way into a brittle wafer
  is a fracture origin under launch and thermal load, and on its
  clearance from the contacts, because material lost beside a busbar
  undercuts the pad an interconnect is later welded to.
- Small accepted defects still accumulate. Cumulative perimeter loss,
  cumulative face area, a count per edge and a count of nicks per cell
  catch the cell that passed every individual limit and is nevertheless
  chewed around its outline.
- Two chips near each other are worse than their sum. The ligament
  between them carries the load both of them shed, so a pair closer than
  the separation rule is referred even when each one is inside its own
  allowance.

## Workflow

1. Resolve the outline: cell length and width, wafer thickness and the
   inactive border, and derive the perimeter, the cell area and the
   active area from them. Reject a border that leaves no active area.
2. Place each chip on its edge from its start position and its run.
   Reject a span that does not fit the edge, then decide corner or edge
   from whether the span reaches an end.
3. Derive the reach available at that position, straight border width
   mid-edge and the border diagonal at a corner, and disposition the
   reach against it.
4. Bound the run: a share of the edge for an edge chip, the longer of the
   two legs for a corner chip, each with its own review band.
5. Disposition each nick on depth against the wafer thickness, on
   diameter, and on clearance from the contacts.
6. Accumulate: perimeter loss, chip area on the face, chips per edge,
   nicks per cell, and pairs of chips sitting inside the separation rule.
7. Take the worst disposition, escalate on any accumulation finding, and
   return the cell verdict with the defects that are not accepted named.

## Pitfalls

- Judging every chip against one millimetre figure. The number that
  matters is the reach the border offers where that chip sits, and a
  corner offers more of it than an edge does.
- Calling a chip a corner chip because it is near a corner. Nearness is
  not the test; whether the span reaches the end of the edge is, and the
  two answers pick different allowances.
- Grading a chip on run alone. A short chip that reaches past the border
  has already opened the junction, which no length limit reports.
- Grading a nick on diameter alone. Depth against the wafer thickness is
  what makes a nick a fracture origin, and the same depth is benign in a
  thick wafer and serious in a thin one.
- Ignoring where a nick sits relative to the contacts. A nick that
  undercuts a pad is a future interconnect failure, whatever its size.
- Accepting a cell because every defect passed. The cumulative perimeter,
  area and count allowances exist for exactly that case.
- Screening chips one at a time and never comparing their positions. Two
  chips separated by a thin ligament are a single weak section of edge.
- Comparing a measurement with a derived allowance by bare arithmetic.
  Every allowance here is a product of a criteria share and a measured
  dimension, so a measurement exactly on it can evaluate a few units in
  the last place above it; the comparison absorbs that representation
  error while the allowance stays untouched.

## Behavior contract (gate 3)

The outline resolution, the corner-or-edge placement test, the derived
reach allowance with its border diagonal at a corner, the run and corner
leg bands, the nick depth, diameter and contact clearance screens, the
cumulative perimeter, area, count and separation rollups and the cell
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_chip_and_nick_limits.py against
scripts/e2008_bare_cell_chip_and_nick_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_chip_and_nick_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

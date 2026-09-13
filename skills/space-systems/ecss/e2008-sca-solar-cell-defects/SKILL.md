---
name: e2008-sca-solar-cell-defects
description: "Evaluate the chips and nicks recorded on a solar cell body against the position and size allowances of ECSS-E-ST-20-08C clause 6.4.3.1.4: resolve a corner break onto the axis it eats into, measure every break against the inactive border between the cell edge and the active area, tighten the position allowance where the break goes through the wafer, grade the footprint against the single-defect and cumulative area allowances, count the breaks per edge, and return accept, refer-for-review or reject with any active-area encroachment named apart. Use when a cell body has been examined and the chip record needs a disposition, remembering that silicon cannot be put back. Trigger: ecss, e-st-20-08c, clause-6-4-3-1-4, sca-cell-body-chip-position, cell-edge-chip-ingress-allowance, cell-active-area-encroachment, corner-chip-diagonal-reach, cell-chip-cumulative-area."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-sca-solar-cell-defects, e-st-20-08c, sca-cell-body-chip-position, cell-edge-chip-ingress-allowance, cell-active-area-encroachment, corner-chip-diagonal-reach, cell-chip-cumulative-area]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cell Assemblies — Solar Cell Defects (space-systems/ecss/e2008-sca-solar-cell-defects)

Use when the task is clause 6.4.3.1.4 of ECSS-E-ST-20-08C: where a chip or a
nick is allowed to sit on the body of a cell, and how large it is allowed to
be. The two halves are separate questions and a screen that runs only one of
them passes cells it should not.

## Domain quick reference

- Position is decided against the inactive border the cell carries between
  its physical edge and the start of its active area. A break that stays
  inside that border has taken nothing the cell was generating with. A break
  that reaches past it has removed generating area and may have severed a
  grid finger on the way in.
- Size is decided twice: once per break against a single-defect allowance,
  and again over the whole cell. Many small breaks are a handling problem
  upstream even when each one of them passes on its own, and only the
  cumulative view sees that.
- A corner break is measured on the diagonal, and the diagonal resolved back
  onto either axis is shorter than the number written down. So a corner
  tolerates a longer measurement before it touches the active border -- and
  it carries a tighter area allowance anyway, because the corner is where
  handling cracks start.
- Depth is not a size, it is a position modifier. A break that goes the whole
  way through the wafer is a crack starter under thermal cycling rather than
  a deeper scallop, so the distance it is allowed to come in is tightened
  before the measurement is compared against it.
- A flake off the face is not connected to an edge, so it is declared by its
  stand-off and its inward extent, and its reach is the far side of the
  flake. Its footprint is the whole outline; a broken-out edge scallop is
  taken at half its bounding box.
- Nothing here is reworkable. The dispositions are accept, refer-for-review
  and reject, and a rework verdict would invite an operation the article does
  not allow.
- Four edges, four records. An edge nobody looked at is not an edge with no
  breaks, so the cell stays open rather than passing.

## Workflow

1. Derive the cell geometry: the cell area, the active area and the inactive
   border. Refuse a border that leaves no active area at all.
2. Take the examined edge list. Hold the cell open when an edge carries no
   record, and refuse a break recorded on an edge the record says was never
   looked at.
3. Per break, resolve the reach: straight in for an edge break or a nick,
   diagonal resolved onto the axis for a corner, stand-off plus extent for a
   face flake.
4. Set the permitted reach from the border, tightened when the break goes
   through the wafer, and compare the reach against it.
5. Reject anything that crossed into the active area, and report how much
   area it took; refer a break that is past the allowance but still clear.
6. Take the footprint and grade it against the single-defect allowance and
   its review multiple, using the tightened corner allowance at a corner.
7. Close with the cell verdict, the cumulative area fraction, the per-edge
   counts, the identifiers that reached the active area, and the edges that
   carry no record.

## Pitfalls

- Comparing a corner measurement against the edge allowance. The diagonal is
  not the perpendicular, and a corner break scrapped on that comparison was
  inside the border the whole time.
- Judging a break on its ingress alone. A shallow scallop 30 mm long has
  taken far more of the cell than a deep notch 1 mm long, and only the
  footprint sees it.
- Grading a corner break against the flat-edge area allowance. The corner is
  the crack initiation site, and the allowance there is deliberately smaller.
- Treating depth as a size term. It does not enter the footprint; it moves
  the position allowance, and a through break that would pass on area can
  still be past the distance it is allowed to come in.
- Accepting a cell because every break passed. The cumulative fraction and
  the per-edge count exist for exactly that case.
- Offering a rework. There is no operation that puts silicon back, so a
  rework line on a cell body record means the disposition was never made.
- Reading a silent edge as a clean edge. The record says nothing about it,
  which is not the same as saying it is clean.
- Comparing a measurement with a derived limit by bare arithmetic. The limits
  are products of a criteria fraction and a measured dimension and the corner
  reach is resolved through an irrational factor, so a measurement exactly on
  a limit can evaluate a few units in the last place above it; the comparison
  absorbs that representation error while the limit stays untouched.

## Behavior contract (gate 3)

The reach resolution, the through-wafer tightening, the active-area
encroachment rule, the single-defect and corner area allowances, the
cumulative fraction, the per-edge crowding check and the examined-edge
completeness rollup are exercised by the gate 3 contract test:
scripts/test_e2008_sca_solar_cell_defects.py against
scripts/e2008_sca_solar_cell_defects_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_sca_solar_cell_defects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

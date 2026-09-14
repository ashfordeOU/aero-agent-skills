---
name: e2008-bare-cell-bus-bar-grids
description: "Verify that the front bus bars and grid lines of a bare solar cell run through unbroken under ECSS-E-ST-20-08C clause 7.5.1.5.3: separate a full interruption, which the continuity requirement refuses on presence alone, from a narrowing that still conducts, turn each narrowing into the width fraction that survived and the current density the surviving metal now carries, size each break by the share of the collection strip it orphans from a bus bar, and return accept, review or reject with the broken lines named apart. Use when a bare cell front metallization survey needs a disposition a scrap decision can rest on. Trigger: ecss, e-st-20-08c, clause-7-5-1-5-3, bare-cell-front-bus-bar-continuity, solar-cell-grid-line-break-screen, grid-finger-constriction-width-check, orphaned-cell-collection-area, front-metallization-current-density."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-bus-bar-grids, bare-cell-front-bus-bar-continuity, solar-cell-grid-line-break-screen, grid-finger-constriction-width-check, orphaned-cell-collection-area, front-metallization-current-density]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bare Cell Bus Bar and Grid Continuity (space-systems/ecss/e2008-bare-cell-bus-bar-grids)

Use when the task is the front metallization requirement of
ECSS-E-ST-20-08C clause 7.5.1.5.3 -- the bus bars and the grid lines of
a bare cell have to run through without a break -- turned into a
survey that separates what is refused on presence from what is
measured, and closes with a disposition.

## Domain quick reference

- The front grid is the cell's current collector. Fingers gather from
  the illuminated surface and deliver into the bus bars; the bus bars
  carry the whole cell out to the interconnectors. A requirement that
  the lines run through is a requirement about that path, not about
  cosmetic appearance.
- The survey has two halves and they must not be run with the same
  rule. A full interruption or a fracture that separates the metal is
  decided by presence: there is no width below which a break passes,
  because what is gone is the path. A narrowing, an edge nick or a
  void inside the line footprint leaves metal behind and is decided by
  measurement.
- A narrowing is graded on what survived, not on what was lost. The
  residual width fraction is the narrowest surviving width over the
  nominal line width, so two lines of different nominal width with the
  same absolute loss are correctly different findings.
- A bus bar is held tighter than a finger. Everything the cell
  collects passes through the bus bar, while a finger carries only its
  own strip, so the same residual fraction is an accept on one and a
  non-conformance on the other.
- Width is not the whole screen. Metal that survived still has to
  carry the line current, so the second axis is the current density in
  the surviving cross section. A narrowing can sit inside the width
  band and still drive the density past its limit, and a survey that
  measures only width will not see it.
- A break is sized as well as refused. The orphaned collection share
  is the part of a line's strip cut off from any bus bar: everything
  past the break on a line fed from one end, and nothing at all on a
  line fed from both, because the far end still delivers. That number
  tells a reviewer what the cell lost. It never turns the break into
  an accept.
- A bare cell front grid is not reworkable the way a solder joint is,
  so the middle disposition holds the cell for a non-conformance
  decision rather than promising a repair.
- A clean front still produces a record. The survey is the evidence,
  and an absent record is not the same as an absent break.

## Workflow

1. Open the survey against a cell identifier. A record with no
   traceable identifier cannot be dispositioned, because the
   non-conformance has nothing to attach to.
2. Categorize every indication by kind and by the line it sits on.
   Reject an unrecognized kind or line rather than defaulting it to a
   neighbouring one and inheriting a limit that does not apply.
3. Route each indication to the half that governs it: presence for a
   break or a crack through, measurement for a narrowing, an edge nick
   or a void.
4. For a break, take the line length, the break position and the
   number of ends fed from a bus bar, and report the orphaned
   collection share alongside the refusal.
5. For a narrowing, take the narrowest surviving width against the
   nominal and disposition on the residual width fraction for that
   line kind.
6. Where the line current and the metal thickness are both recorded,
   take the current density in the surviving cross section and let the
   worse of the two axes govern. Refuse a half-recorded pair rather
   than dropping the second axis in silence.
7. Close with the cell verdict, the broken lines listed apart, the
   worst orphaned share, and the non-conformance a review verdict
   raises.

## Pitfalls

- Grading a break by how wide it is. The finding is the loss of the
  path; a narrow break is still a break and no fraction reaches it.
- Reading a zero orphaned share as a reprieve. A line fed from both
  ends loses no collection to a single break, and the break is still
  refused because the second break has nowhere left to go.
- Grading a narrowing on absolute metal lost. The same loss on a wide
  bus bar and a fine finger are different findings, and only the
  residual fraction separates them.
- Applying the finger limit to a bus bar. The bus bar carries the
  whole cell, and the limit that governs it is the tightened one.
- Measuring width and stopping. A narrowing inside the width band can
  still put the surviving cross section past its current density, and
  a width-only survey passes it.
- Recording a line current with no metal thickness. The pair produces
  the density; one without the other silently drops half the screen,
  so it is refused instead.
- Comparing a residual fraction with its limit by bare arithmetic. The
  fraction is a quotient and the density is a quotient of a quotient,
  so a measurement meant to sit exactly on a limit can evaluate a few
  units in the last place to either side; the comparison absorbs that
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The presence-versus-measurement split, the residual width fraction,
the orphaned collection share, the surviving-cross-section current
density and the cell rollup are exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_bus_bar_grids.py against
scripts/e2008_bare_cell_bus_bar_grids_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_bus_bar_grids.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

---
name: e2008-coverglass-edge-chips
description: "Use when a coverglass edge inspection needs a per-chip disposition and a glass verdict. Evaluate an edge chip on a solar cell coverglass against clause 8.7.1.3.4 of ECSS-E-ST-20-08C: place the chip on its edge, confirm from the span that it is an edge chip and not a corner chip, grade how far it projects inward across the glass face against the quarter millimetre ceiling, test that projection against the overhang the glass is laid over the cell with rather than a typed-in absolute, bound the run along the edge separately, and roll the accepted chips up against cumulative face area, perimeter, count and separation allowances. Trigger: ecss, e-st-20-08c, coverglass-edge-chip-projection, coverglass-edge-chip-limits, coverglass-chip-face-ingress, coverglass-aperture-encroachment, solar-cell-coverglass-edge-inspection."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-edge-chips, e-st-20-08c, coverglass-edge-chip-projection, coverglass-edge-chip-limits, coverglass-chip-face-ingress, coverglass-aperture-encroachment, solar-cell-coverglass-edge-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Edge Chips (space-systems/ecss/e2008-coverglass-edge-chips)

Use when the task is clause 8.7.1.3.4 of ECSS-E-ST-20-08C: how far a chip
on the edge of a coverglass may project inward across the face of the
glass. This leaf reads one coverglass outline and the edge chips observed
on it, and returns a disposition per chip plus the accumulation rollup
that decides the glass.

## Domain quick reference

- Inward projection is the graded dimension, not length along the edge. A
  quarter of a millimetre is the ceiling, and it is a ceiling on reach
  across the face because that is the direction in which a chip takes
  cover off the cell.
- The overhang is the second, harder bound and it is read from the
  drawing rather than typed in. A coverglass sits over its cell with a
  small margin, so the first fraction of a millimetre of projection eats
  overhang and nothing else. A glass laid out with less overhang tightens
  its own limit without anyone editing a table.
- Past the overhang the chip is standing over the illuminated aperture.
  That is a different failure from an oversized chip: the cell is shaded,
  the adhesive bond line is open to ultraviolet, and the junction is
  without the radiation cover the glass exists to provide.
- Run along the edge is bounded separately and more loosely. It decides
  how much of the sealing edge is now a stress raiser, not how much cover
  is gone, so it is a share of the edge the chip sits on rather than one
  number for the glass.
- The run allowance scales with that edge. A three millimetre chip is a
  small mark on a long edge and a substantial loss on a short one.
- A chip whose span reaches either end of its edge takes a corner and is
  not this clause's work. It is routed on, because the corner allowance
  is written on the hypotenuse across the corner and grading it here
  would apply the wrong limit to it.
- Small accepted chips still accumulate. Cumulative face area, cumulative
  run against the perimeter, a count per edge and a count per glass catch
  the coverglass that passed every individual limit and is nevertheless
  chewed around its outline.
- Two chips near each other are worse than their sum, because the
  ligament between them carries the load both of them shed.

## Workflow

1. Resolve the outline: glass length and width, thickness and the
   overhang, and derive the perimeter, the face area and the illuminated
   aperture from them. Reject an overhang that leaves no aperture.
2. Place each chip on its edge from its start position and its run.
   Reject a span that does not fit the edge, then decide from whether the
   span reaches an end whether the chip takes a corner.
3. Route a corner-taking chip to the corner clause instead of grading its
   projection against an edge allowance.
4. Grade inward projection against the quarter millimetre ceiling, then
   against the overhang, so a chip past the ceiling but still inside the
   overhang is referred and one over the aperture is rejected.
5. Bound the run as a share of the edge it sits on, with its own review
   band above that share.
6. Accumulate: face area lost, run against the perimeter, chips per edge,
   chips per glass, and pairs of chips inside the separation rule.
7. Take the worst disposition, escalate on any accumulation finding, and
   return the glass verdict with the chips that are not accepted named.

## Pitfalls

- Grading the chip on how long it runs along the edge. Length along the
  edge is the visible dimension and the wrong one; the clause is written
  on reach across the face.
- Treating a quarter of a millimetre as the only bound. On a glass with a
  thin overhang a chip inside the ceiling can already be standing over
  the aperture, and only the derived bound reports that.
- Typing the overhang in as a constant. It is a property of this layout,
  and a narrower one has to tighten the limit by itself.
- Grading a corner-taking chip here. Its allowance is written on the
  hypotenuse across the corner, so an edge projection test passes chips
  the corner clause would not.
- Accepting a glass because every chip passed. The cumulative area, run,
  count and separation allowances exist for exactly that case.
- Screening chips one at a time and never comparing their positions. Two
  chips separated by a thin ligament are one weak section of edge.
- Measuring the area of a chip as a rectangle. A conchoidal bite tapers
  to nothing where it meets sound glass, and a rectangle roughly doubles
  the accumulated area.
- Comparing a measurement with a derived allowance by bare arithmetic.
  Several allowances here are a product of a criteria share and a
  measured dimension, so a measurement exactly on one can evaluate a few
  units in the last place above it; the comparison absorbs that
  representation error while the allowance stays untouched.

## Behavior contract (gate 3)

The outline resolution, the corner-taking span test and its routing, the
quarter millimetre projection ceiling, the derived overhang bound and the
aperture encroachment it yields, the run band against the edge, the
triangular face area model and the cumulative area, perimeter, count and
separation rollups with the glass verdict are exercised by the gate 3
contract test: scripts/test_e2008_coverglass_edge_chips.py against
scripts/e2008_coverglass_edge_chips_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_coverglass_edge_chips.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

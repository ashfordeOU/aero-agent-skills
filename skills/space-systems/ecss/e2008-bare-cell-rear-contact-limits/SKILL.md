---
name: e2008-bare-cell-rear-contact-limits
description: "Use when a rear contact survey needs a disposition rather than a defect list. Evaluate the drops and spatter found outside the rear welding zone of a bare solar cell against the size ceilings of ECSS-E-ST-20-08C clause 7.5.1.5.4: place each deposit inside or outside the welding rectangle, measure how far it sits from the zone and from the cell perimeter, tighten its diameter ceiling inside the edge exclusion band, refuse anything standing proud of the declared bond line whatever its width, and add the surviving footprints into a whole-face area and count budget before returning accept, rework or reject. Trigger: ecss, e-st-20-08c, clause-7-5-1-5-4, bare-cell-rear-contact-deposit-limits, rear-welding-zone-spatter-ceiling, solder-drop-diameter-screen, cell-edge-exclusion-band, rear-contact-protrusion-height."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-rear-contact-limits, bare-cell-rear-contact-deposit-limits, rear-welding-zone-spatter-ceiling, solder-drop-diameter-screen, cell-edge-exclusion-band, rear-contact-protrusion-height]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bare Cell Rear Contact Deposit Limits (space-systems/ecss/e2008-bare-cell-rear-contact-limits)

Use when the task is the rear contact requirement of ECSS-E-ST-20-08C
clause 7.5.1.5.4 -- the size a drop of solder or a particle of spatter
is allowed to reach once it has landed outside the welding zone --
turned into a geometric screen and a disposition a rework decision can
rest on.

## Domain quick reference

- The welding zone is the area on the rear contact the interconnector
  is joined in. Molten metal there is the process, not a finding, so
  no size ceiling reaches it. Everything the clause is about landed
  somewhere else.
- In or out is a geometry question before it is a disposition. The
  distance a deposit sits outside the zone is the straight-line
  distance to the nearest point of the zone rectangle, which is zero
  on the boundary and grows diagonally past a corner. A deposit judged
  by which quadrant it looks closest to is judged wrong.
- A deposit is graded across and up, and the two are independent. The
  footprint diameter decides whether there is too much metal to dress
  back; the protrusion height decides whether the cell can still seat.
  A tiny bead standing past the bond line is refused while a wide flat
  smear of the same volume is reworkable.
- Where it landed changes the ceiling. Near the perimeter the junction
  comes close to the rear surface, so a deposit inside the edge
  exclusion band is held to a tightened diameter ceiling and the same
  bead that passes mid-face fails there.
- A deposit past the bond line thickness is refused whatever its
  diameter, because the failure is not the metal, it is the cell
  standing off the substrate and the bond line it never closes.
- The rear carries a budget as well as ceilings. Enough individually
  acceptable deposits still add to a total footprint area and a count
  that the assembly cannot carry, and a survey that dispositions one
  deposit at a time never sees that.
- A clear rear still produces a record. The survey is the evidence,
  and an absent record is not the same as an absent deposit.

## Workflow

1. Open the survey against a cell identifier, the rear outline and the
   welding zone rectangle. A record with no traceable identifier
   cannot be dispositioned, because the rework record has nothing to
   attach to.
2. Categorize every deposit by kind and take its position, footprint
   diameter and protrusion height. Reject an unrecognized kind rather
   than defaulting it to a neighbouring one.
3. Place each deposit against the welding zone. A deposit on or inside
   the rectangle is the joint and carries no ceiling; for the rest,
   record the distance it sits outside.
4. Take the shortest distance to the cell perimeter and apply the
   tightened ceilings to any deposit inside the edge exclusion band.
5. Disposition the diameter against the accept and rework ceilings,
   and the height against the accept height and the bond line, then
   let the worse of the two govern.
6. Add the footprints of every deposit outside the zone and test the
   total area and the count against the whole-face budget.
7. Close with the cell verdict, the deposits that sat in the edge
   band, the totals, and the re-inspection duty a rework creates.

## Pitfalls

- Applying a size ceiling to metal inside the welding zone. That is
  the joint; refusing it turns a good weld into a non-conformance.
- Measuring the distance outside the zone along one axis. Past a
  corner the true distance is diagonal, and an axis-only measurement
  reports a deposit as further out than it is.
- Grading on diameter alone. A small bead standing past the bond line
  holds the cell off the substrate and no diameter allowance reaches
  that.
- Using the mid-face ceiling near the perimeter. The edge exclusion
  band exists because the junction is close to the rear surface there,
  and the ceiling that governs inside it is the tightened one.
- Dispositioning one deposit at a time. Every deposit can pass its own
  ceiling and the face can still be over its total area or count
  budget.
- Counting in-zone metal toward the outside budget. The budget is
  about what landed where it should not have; folding the joint into
  it condemns a clean cell.
- Comparing a diameter with its ceiling by bare arithmetic. The
  ceiling is a product of a criteria value and an edge factor, and a
  footprint area comes out of a squared diameter, so a measurement
  meant to sit exactly on a limit can evaluate a few units in the last
  place above it; the comparison absorbs that representation error
  while the limit stays untouched.

## Behavior contract (gate 3)

The in-zone and out-of-zone split, the rectangle and perimeter
distances, the edge-band ceiling tightening, the independent diameter
and protrusion calls and the whole-face area and count budget are
exercised by the gate 3 contract test:
scripts/test_e2008_bare_cell_rear_contact_limits.py against
scripts/e2008_bare_cell_rear_contact_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_rear_contact_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

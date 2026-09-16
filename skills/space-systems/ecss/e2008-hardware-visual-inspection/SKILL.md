---
name: e2008-hardware-visual-inspection
description: "Use when fitted coupon hardware has been surveyed and its placement needs a disposition. Evaluate the terminal boards and other hardware of ECSS-E-ST-20-08C clause 5.5.3.2.19: reconcile the items the coupon assembly drawing requires against those fitted, take each measured centre as a true-position offset and each measured rotation wrapped the shorter way round, turn the installed fasteners into a retention completeness fraction, take the gap to the nearest stay-out boundary as a margin where zero or less is interference, and return accept, rework or reject per item with a coupon verdict and the missing, undrawn and interfering hardware named apart. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-19, terminal-board-placement-check, coupon-hardware-angular-deviation, hardware-retention-completeness, hardware-stay-out-clearance-margin."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-hardware-visual-inspection, terminal-board-placement-check, coupon-hardware-angular-deviation, hardware-retention-completeness, hardware-stay-out-clearance-margin, undrawn-coupon-hardware-screen]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Hardware Visual Inspection (space-systems/ecss/e2008-hardware-visual-inspection)

Use when the task is the hardware examination of ECSS-E-ST-20-08C
clause 5.5.3.2.19 -- confirming that the terminal boards and the other
fittings on a coupon are positioned the way the coupon assembly drawing
requires, and turning that into a disposition a rework or a scrap
decision can rest on.

## Domain quick reference

- Positioned is four measurements, not one. An item can be on its
  centre and rotated off its terminals; on its centre and rotated
  right but held by three of four fasteners; all of that and still
  crowding a boundary the drawing protects. The item disposition is
  the worst of the four legs, and each leg is reported.
- Placement is a true-position question. The tolerance is a diameter
  around the drawing centre, so the offset is the root-sum-square of
  the two axis errors.
- Orientation is measured on a circle and has to be wrapped. A board
  drawn at 359 degrees and fitted at 1 degree is two degrees out, not
  358; a screen that subtracts raw angles turns the smallest possible
  error into the largest one and rejects a part that is square.
- Retention is a completeness fraction, not a defect count. Three
  fasteners of four is a fraction of the load path the drawing
  designed, and the same three missing fasteners mean something
  different on a four-hole board and a sixteen-hole one.
- Clearance has a floor and a wall. Under the protected minimum the
  item can be shifted back; at or past zero it is interference, which
  is decided by presence and which no zone factor and no widened
  tolerance reaches.
- Retention and clearance are minimums and the zone factor never
  touches them. A factor below one tightens an allowance but loosens a
  minimum, so scaling those two would demand less retention and less
  clearance exactly where the zone was meant to demand more.
- Presence is settled before anything is measured. An item the drawing
  calls out and the coupon does not carry has no position to take, and
  an item fitted with nothing drawn for it is a configuration finding
  that holds the record open just as hard.

## Workflow

1. Open the coupon record against a coupon identifier and take the
   list of hardware the assembly drawing requires.
2. Reconcile that list against the items actually fitted. Report the
   missing and the undrawn apart; they are not graded.
3. For each fitted item, take the measured centre against the drawing
   centre as a true-position offset and disposition it against the
   zone-scaled accept and rework limits.
4. Take the measured rotation against the drawing orientation, wrapped
   into a half turn and returned as a magnitude, and disposition it
   against the zone-scaled angular limits.
5. Take the installed fasteners over the drawing fastener count as a
   completeness fraction and disposition it against the accept
   fraction and the rework floor. Do not scale a minimum.
6. Take the gap to the nearest stay-out boundary. Zero or less is
   interference and is decided by presence; otherwise disposition it
   against the protected minimum and the rework floor.
7. Categorize any further indication by kind and zone, routing the
   not-tolerated kinds to a presence decision and the graded ones to
   the zone-scaled area limits.
8. Close with the coupon verdict, the missing, undrawn, interfering
   and not-tolerated items listed apart, and the re-inspection duty a
   rework creates.

## Pitfalls

- Subtracting raw orientations. Angles live on a circle; without
  wrapping, a two-degree error across the zero crossing reads as 358
  degrees and a square board is condemned.
- Grading retention as a count of missing fasteners. One missing
  fastener of four and one of sixteen are the same count and entirely
  different load paths; the fraction is what the limit is written
  against.
- Treating interference as a tight clearance. A gap of zero or less is
  not the bottom of a scale, it is a different finding, and widening
  the tolerance or picking a looser zone never reaches it.
- Scaling the retention or clearance minimums by the zone factor. A
  factor below one tightens an allowance but loosens a minimum,
  quietly accepting less of both exactly where the zone was meant to
  demand more.
- Reading an accepted placement as an accepted item. The centre is one
  leg of four, and a board on its centre can still be rotated,
  under-fastened or crowding a boundary.
- Measuring an item the drawing never called for instead of raising
  it. An undrawn fitting is a configuration question and no tolerance
  answers it.
- Comparing a measurement with a scaled limit by bare arithmetic. The
  limit is a product of a criteria value and a zone factor and the
  measurement is a root-sum-square or a wrapped angle, so a value
  exactly on the limit can evaluate a few units in the last place
  above it; the comparison absorbs that representation error while the
  limit stays untouched.

## Behavior contract (gate 3)

The drawing-to-coupon reconciliation, the true-position offset, the
wrapped angular deviation, the retention completeness fraction, the
clearance margin and its interference wall, the zone-scaled allowances
and the coupon rollup are exercised by the gate 3 contract test:
scripts/test_e2008_hardware_visual_inspection.py against
scripts/e2008_hardware_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_hardware_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

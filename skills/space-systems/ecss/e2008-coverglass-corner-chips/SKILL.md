---
name: e2008-coverglass-corner-chips
description: "Use when a coverglass corner inspection needs a per-chip disposition. Evaluate a corner chip on a solar cell coverglass against clause 8.7.1.3.5 of ECSS-E-ST-20-08C: derive the chord across the corner from the two measured legs, reconcile it with any directly measured chord and refuse one that breaks the triangle inequality, grade the chord against the three quarter millimetre ceiling, derive the perpendicular reach the bite makes toward the cell and bound it with the overhang diagonal, route a lopsided bite to the edge clause, and roll the four corners up against area and count allowances. Trigger: ecss, e-st-20-08c, coverglass-corner-chip-hypotenuse, coverglass-corner-chip-limits, coverglass-corner-chip-legs, coverglass-corner-reach-to-aperture, solar-cell-coverglass-corner-inspection."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-corner-chips, e-st-20-08c, coverglass-corner-chip-hypotenuse, coverglass-corner-chip-limits, coverglass-corner-chip-legs, coverglass-corner-reach-to-aperture, solar-cell-coverglass-corner-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Corner Chips (space-systems/ecss/e2008-coverglass-corner-chips)

Use when the task is clause 8.7.1.3.5 of ECSS-E-ST-20-08C: the size
allowed for a chip that takes a corner out of a coverglass. This leaf
reads one coverglass outline and the corner bites observed on it, and
returns a disposition per bite plus the rollup that decides the glass.

## Domain quick reference

- The chord across the corner is the graded dimension. Three quarters of
  a millimetre is the ceiling, and it sits on the chord rather than on a
  leg because the chord bounds the whole bite in one number.
- A leg on its own says nothing. A bite taking a tenth of a millimetre
  off one edge and seven tenths off the other has a leg that would fail a
  limit the corner geometry never meant to catch, and a chord that is
  comfortably inside it.
- That lopsided bite is a gouge running along one edge wearing a corner's
  name. The leg ratio is what exposes it, and it belongs to the edge chip
  clause, so it is routed on rather than quietly accepted.
- The chord is derived from the two measured legs, never taken on trust.
  A directly measured chord is a cross-check: outside the triangle
  inequality it cannot belong to these legs and is refused as input,
  inside it but disagreeing it is referred, because one of the two
  readings is wrong and no disposition from either is worth anything yet.
- Reach is not size. The perpendicular from the corner to the chord is
  how far the bite actually penetrates toward the cell, and it is shorter
  than either leg and much shorter than the chord. Grading on a leg
  overstates it; grading on the chord alone never reports it.
- At a corner the glass has the diagonal of its overhang to give up
  before the bite stands over the illuminated aperture, which is longer
  than the straight overhang an edge chip has to work through.
- That bound is derived from the declared overhang, so a glass laid out
  with less of it tightens its own corner limit without a table edit, and
  a chord inside the ceiling can still be rejected on reach.
- A corner carries one bite. Two readings at one corner are a records
  problem to reconcile before any disposition, not two chips to add up.
- Small accepted bites still accumulate across the four corners, in face
  area and in how many corners are no longer square.

## Workflow

1. Resolve the outline: glass length and width, thickness and the
   overhang, and derive the face area, the illuminated aperture and the
   corner reach the overhang diagonal offers.
2. Read each bite: its corner, its two legs, and any directly measured
   chord. Refuse a chord outside the triangle inequality for those legs.
3. Derive the chord, the leg ratio, the perpendicular reach and the
   triangular area the bite takes off the face.
4. Grade the chord against the three quarter millimetre ceiling, with a
   review band above it before outright rejection.
5. Bound the reach with the overhang diagonal; past it the bite stands
   over the aperture and the glass is rejected whatever the chord said.
6. Route a bite whose legs are too unequal to the edge chip clause, and
   refer a measured chord that disagrees with the legs.
7. Accumulate corner area and the count of chipped corners, take the
   worst disposition, and return the glass verdict with the bites that
   are not accepted named.

## Pitfalls

- Grading the bite on its longest leg. The clause is written on the chord
  and a leg limit rejects symmetric bites the chord accepts.
- Reading a measured chord straight into the disposition. It is a second
  reading of the same feature, and its job is to agree with the legs.
- Accepting a chord that is shorter than the longest leg. Such a chord
  cannot close those legs, so the record, not the glass, is the problem.
- Treating the chord as the reach. The perpendicular to it is roughly
  half a symmetric bite's leg, so a chord-only screen says nothing about
  how close the damage came to the cell.
- Giving a corner the straight overhang as its reach allowance. A corner
  offers the diagonal of it, which is the longer distance, and using the
  straight value rejects bites the geometry allows.
- Typing the overhang in as a constant instead of reading the layout.
- Letting a lopsided bite pass as a corner chip. Its chord is small
  precisely because one leg is small; the edge clause is what grades it.
- Adding two readings at one corner together as two chips.
- Comparing a measurement with a derived allowance by bare arithmetic.
  The chord is a square root of a sum of squares, so a bite sitting
  exactly on the ceiling can evaluate a few units in the last place above
  it; the comparison absorbs that representation error while the
  allowance stays untouched.

## Behavior contract (gate 3)

The outline resolution and its derived corner reach, the chord derived
from the legs, the triangle inequality refusal and the agreement check on
a measured chord, the three quarter millimetre ceiling with its review
band, the perpendicular reach against the overhang diagonal, the leg
ratio routing to the edge clause and the corner area and count rollups
with the glass verdict are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_corner_chips.py against
scripts/e2008_coverglass_corner_chips_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_coverglass_corner_chips.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

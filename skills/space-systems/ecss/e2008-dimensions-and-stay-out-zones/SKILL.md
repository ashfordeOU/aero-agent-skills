---
name: e2008-dimensions-and-stay-out-zones
description: "Compute the dimensional, keep-out and standoff checks that ECSS-E-ST-20-08C clause 5.5.3.2.4 folds into the visual inspection of a photovoltaic assembly coupon: place every measured dimension inside its plus and minus drawing band and name the one that governs, build the border bands a reserved edge margin creates, test each placed feature against every stay-out zone for shared area, intrusion depth and shortest clearance, then check each standoff feature reaches its called-out height and keeps its footprint clear of the zones. Use when a coupon layout has to be judged against the drawing rather than against a defect list. Trigger: ecss, e-st-20-08c, coupon-dimensional-tolerance-check, solar-array-stay-out-zone, keep-out-area-intrusion, standoff-feature-height-check, coupon-edge-margin-band, feature-zone-clearance."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-dimensions-and-stay-out-zones, coupon-dimensional-tolerance-check, solar-array-stay-out-zone, keep-out-area-intrusion, standoff-feature-height-check, coupon-edge-margin-band]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Dimensions and Stay-Out Zones (space-systems/ecss/e2008-dimensions-and-stay-out-zones)

Use when the task is the geometric part of ECSS-E-ST-20-08C clause
5.5.3.2.4 -- the coupon dimensions, the keep-out areas and the standoff
features that a visual inspection of a photovoltaic assembly has to
check alongside the defect examination.

## Domain quick reference

- This part of the inspection is not about defects. It asks whether the
  coupon is the size the drawing calls out, whether the reserved areas
  are still empty, and whether the standoff features stand where and how
  high they were meant to.
- A dimension is a band, not a target. Each one carries its own plus and
  minus allowance, and the useful output is not a pass mark but the
  fraction of the allowance each measurement consumed, because the
  dimension that consumed the most is the one that will fail first on
  the next unit.
- Keep-out areas are ordinary rectangles in the coupon frame: harness
  routing corridors, hold-down footprints, connector swing volumes, and
  the border band a reserved edge margin creates on all four sides. An
  edge margin is one number on the drawing and four zones in the check.
- A feature and a zone stand in one of three relations, and they are
  measured differently. They overlap, and the answer is a shared area
  and the shortest distance that would move the feature out. They touch,
  and the shared area is zero while the clearance is also zero. They are
  apart, and the answer is the shortest distance between them, which on
  a diagonal offset is a corner-to-corner distance and not an axis gap.
- Zero clearance is not automatically a failure. It fails when the
  layout declares a minimum clearance above zero, which is the usual
  case once thermal cycling and harness movement are allowed for.
- A standoff carries two independent checks. Its height sits in a
  tolerance band exactly like a coupon dimension, and its footprint is a
  placed feature that the stay-out zones apply to like any other.

## Workflow

1. Validate the drawing spec and the measurement set against each other:
   every called-out dimension measured, no measurement without a drawing
   entry, positive nominals, non-negative allowances with at least one
   side open, and a lower limit that is still a physical dimension.
2. For each dimension compute the deviation, the fraction of the
   allowance on the side the deviation falls on, and the verdict.
   Absorb representation error exactly on a limit with a named tolerance
   rather than by widening the band.
3. Roll the dimensions up: which are out of tolerance, and which
   consumed the most allowance. Break a tie on the dimension name so the
   governing dimension is reproducible.
4. Assemble the stay-out zones: those declared explicitly, plus the four
   border bands from any reserved edge margin. Refuse a margin that
   leaves no usable area, and refuse duplicate zone identifiers.
5. Test every placed feature against every zone for shared area,
   intrusion depth and shortest clearance, and compare the clearance
   with the declared minimum.
6. Check each standoff height against its band, then feed the standoff
   footprints back through the same zone test.
7. Return the coupon verdict with the dimension, zone and standoff
   findings kept separate, so a rejection names what actually failed.

## Pitfalls

- Judging a dimension by its deviation alone. A deviation of a tenth of
  a millimetre is comfortable on one dimension and the whole allowance
  on another; only the consumed fraction compares across a coupon.
- Treating a reserved edge margin as a single zone. It is four bands,
  and a feature that hangs over one corner sits in two of them; building
  only one band leaves three edges unchecked.
- Measuring clearance as an axis gap. Two rectangles offset on both axes
  are separated by the corner-to-corner distance, and quoting the larger
  axis gap overstates the clearance on exactly the diagonal case that
  matters.
- Reading a touching feature as an intrusion. Shared area is zero when
  edges coincide; what makes it a finding is a declared minimum
  clearance above zero, not the contact itself.
- Checking a standoff height and forgetting its footprint. The height is
  a dimension and the footprint is a placed feature, and a standoff at
  exactly the right height planted in a harness corridor is still a
  reject.
- Asserting a strict inequality on a clearance that is meant to sit
  exactly on the declared minimum. Coordinates are built by addition and
  the clearance can land a few units in the last place either side of
  the bound; compare with a tolerance and assert the verdict instead.

## Behavior contract (gate 3)

The tolerance banding, governing-dimension roll-up, rectangle overlap,
intrusion depth, clearance distance, edge-margin band construction,
standoff height check and coupon verdict are exercised by the gate 3
contract test: scripts/test_e2008_dimensions_and_stay_out_zones.py
against scripts/e2008_dimensions_and_stay_out_zones_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_dimensions_and_stay_out_zones.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.

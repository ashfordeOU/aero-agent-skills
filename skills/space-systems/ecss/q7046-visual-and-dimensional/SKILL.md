---
name: q7046-visual-and-dimensional
description: "Assess the visual and dimensional inspection of a procured threaded fastener lot against the criteria that lot owes. Use when fasteners are on the bench and someone must say whether a seam, lap, tool mark, pit or plating void is allowable and whether every measured feature sits inside its band: derive the basic thread height from the pitch, take the depth allowance for the zone the indication sits in, allow nothing at all in the thread root, head-to-shank fillet or bearing surface, reject a crack at any depth anywhere, judge each dimension with its signed deviation and margin to the nearer limit, then group the bench run by what actually drove the rejects. Trigger: ecss, q-st-70-46-fasteners, fastener-visual-inspection-zones, fastener-discontinuity-depth-limit, fastener-dimensional-tolerance-check, fastener-bench-run-rollup."
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
  tags: [ecss, q-st-70-46-fasteners, q7046-visual-and-dimensional, fastener-visual-inspection-zones, fastener-discontinuity-depth-limit, fastener-dimensional-tolerance-check, fastener-bench-run-rollup]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Threaded Fasteners — Visual and Dimensional Inspection (space-systems/ecss/q7046-visual-and-dimensional)

Use when the task is the inspection clause of ECSS-Q-ST-70-46: deciding
what a surface indication on a procured fastener means, and whether the
measured geometry of that fastener is inside the band the drawing gives
it.

## Domain quick reference

- A discontinuity is judged by where it sits before it is judged by how
  deep it is. The thread root, the head-to-shank fillet and the bearing
  surface are where the load line turns and the stress concentrates, so
  no seam, lap, mark, pit or void is allowed in them at any depth.
- Outside those zones the allowance is a fraction of the basic thread
  height, not a fixed number of millimetres. Tying it to the pitch
  means one rule covers an M4 and an M20 without a second table, and a
  coarse thread is not held to a fine thread's allowance.
- A crack and a forging fold are rejectable wherever they are found and
  however shallow they look. Depth is not the variable there; the
  presence of a plane of separation in a hardened part is.
- A burr and a plating void are surface conditions rather than
  separations, so they carry a wider allowance than a seam or a lap
  even in the same zone.
- Every measured feature owes its own nominal and its own signed
  tolerance band. Reading a single symmetric band off the drawing title
  block loses the one-sided bands that thread and fillet features
  usually carry.
- The margin to the nearer limit is worth reporting alongside the
  verdict. A feature inside the band but walking towards a limit across
  successive lots is a process drifting, and it is visible one lot
  before it becomes a reject.
- A fastener with no visual result and no dimensional result is not a
  passed fastener. An empty inspection record and an accept are
  different things, and only one of them is defensible later.

## Workflow

1. Take the pitch and derive the basic thread height, which sets every
   depth allowance on the part. Reject a zero or negative pitch rather
   than defaulting it.
2. For each recorded indication, take its zone and kind. A crack or
   forging fold rejects immediately; a stress-concentrating zone rejects
   immediately; otherwise compare the depth against the fraction of the
   basic thread height allowed for that kind.
3. For each measured feature, build the band from the nominal and the
   two tolerance magnitudes, compute the signed deviation and the margin
   to the nearer limit, and judge the measurement inside or outside.
   Refuse a zero-width band rather than failing every part against it.
4. Roll the indications and the measurements into one verdict per
   fastener and name each finding in the terms the bench used, so the
   reject can be argued without re-measuring.
5. Group the run: how many were inspected, how many rejected, the reject
   rate, and which zone-and-kind pairs or which features produced the
   rejects. That grouping, not the count, is what goes to the supplier.
6. Compare depths and measurements with a small absolute slack so a
   value landing exactly on its own computed limit reads the same on
   every machine that runs the check.

## Pitfalls

- Applying one depth allowance to every thread size. The allowance
  scales with the basic thread height, so a number set on an M10 is
  simultaneously too tight on an M20 and too generous on an M4.
- Treating a shallow lap in the thread root as acceptable because it is
  shallow. The root is where the fatigue crack starts, and a
  measurement of the indication is not a measurement of the notch it
  becomes under load.
- Reading one symmetric tolerance for every feature. Thread diameters
  and fillet radii usually carry one-sided bands, and a symmetric read
  silently accepts material on the side the drawing forbids.
- Reporting the verdict without the margin. A lot that passed with
  every feature sitting on the same limit is a different lot from one
  that passed centred, and only the margin distinguishes them.
- Recording a fastener with no measurements and no visual result and
  letting it count as inspected. An empty record inflates the accepted
  count with parts nobody looked at.
- Comparing a depth against a limit the code just computed with a bare
  strict inequality. The value lands exactly on the limit for the most
  common case, so the comparison carries a small absolute slack instead.

## Behavior contract (gate 3)

The basic thread height, the zone allowances, the always-rejectable
kinds, the dimensional band with its signed deviation and margin, the
per-fastener rollup and the grouped run summary are exercised by the
gate 3 contract test:
scripts/test_q7046_visual_and_dimensional.py against
scripts/q7046_visual_and_dimensional_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7046_visual_and_dimensional.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
